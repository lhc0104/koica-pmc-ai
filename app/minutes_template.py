"""회의록 양식지(Word) 만들기 + 채워진 양식지 읽어 들이기 (v0.7)

쓰는 흐름
  1. [회의록 양식지 다운로드] → 회의록_양식지.docx
  2. 회의를 녹음해 AI로 받아 적은 글을 "이 양식에 맞춰 정리해 줘" 하고 Word 파일로 받는다.
  3. [회의록 추가] › [양식 업로드 (자동 채우기)] 에 그 Word 파일을 올리면 입력 칸이 채워진다.

양식의 규칙은 하나뿐이다: 표의 왼쪽 칸이 항목 이름, 오른쪽 칸이 내용.
그래서 항목 순서가 바뀌거나 줄이 늘어나도, 이 앱이 [Word로 다운받기]로 만든 회의록(4칸 표)을 다시 올려도 읽힌다.
"""
import io
import re
from datetime import date
from pathlib import Path

from app.db import ROOT

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
TEMPLATE_NAME = "회의록_양식지.docx"
PROJECT = "KOICA 필리핀 루존지역 부카스센터 긴급 외래 진료 및 진단검사 역량강화 사업 — PMC"
MEETING_TYPES = ["내부회의", "외부회의"]

# 항목 이름(별칭) → 회의록 열.  별칭은 공백·기호를 뺀 뒤 '앞부분이 같으면' 맞는 것으로 본다.
ALIASES = {
    "title": ["회의명", "회의제목", "제목"],
    "_when": ["일시"],
    "meeting_date": ["회의일", "회의일자", "일자", "날짜"],
    "meeting_time": ["시각", "시간", "회의시간"],
    "location": ["장소", "회의장소"],
    "activity": ["대분류", "activity", "과업"],
    "meeting_type": ["중분류", "구분", "회의구분"],
    "stakeholder_org": ["소분류", "이해관계기관", "기관", "상대기관"],
    "participants": ["참석자", "참석"],
    "author": ["작성자", "기록자"],
    "agenda": ["회의주요안건", "주요안건", "안건"],
    "summary": ["회의결과요약", "결과요약", "회의결과", "회의내용"],
    "follow_up": ["후속조치사항", "후속조치", "조치사항"],
}
TEXT_FIELDS = ["agenda", "summary", "follow_up"]
ACTION_HEAD = ("조치", "담당")          # 후속조치 표의 머리글에 이 두 낱말이 있으면 후속조치 표로 본다
STOP_HEADINGS = ["작성안내", "작성방법", "안내"]   # 이 제목 아래 글은 읽지 않는다


def _s(v) -> str:
    return "" if v is None else str(v).replace("\xa0", " ").strip()


def _norm_label(text: str) -> str:
    """'1. 회의 주요 안건 *' → '회의주요안건'.  첫 줄만 보고, 번호·기호·공백·괄호 안 설명을 뺀다."""
    t = _s(text).splitlines()[0] if _s(text) else ""
    t = re.sub(r"^[\s\d.\-)①-⑳(]*", "", t)
    t = re.sub(r"\(.*?\)", "", t)
    return re.sub(r"[\s:：*※·.\-_/]+", "", t).lower()


def _field_of(label: str) -> str | None:
    n = _norm_label(label)
    if not n or len(n) > 24:                       # 긴 글은 항목 이름이 아니라 내용이다
        return None
    for col, names in ALIASES.items():
        for a in names:
            a = a.lower()
            if n == a or (len(a) > 2 and n.startswith(a) and len(n) - len(a) <= 6):   # 두 글자 별칭(안건·장소…)은 똑같을 때만
                return col
    return None


def norm_date(v: str) -> str:
    """'2026.10.15' '2026/10/15' '2026년 10월 15일' '10월 15일(2026)' → '2026-10-15'.  못 읽으면 ''."""
    v = _s(v)
    m = re.search(r"(\d{4})\s*[-./년]\s*(\d{1,2})\s*[-./월]\s*(\d{1,2})", v)
    if not m:
        return ""
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
    except ValueError:
        return ""


def norm_time(v: str) -> str:
    v = _s(v)
    m = re.search(r"(오전|오후|am|pm)?\s*(\d{1,2})\s*[:시]\s*(\d{1,2})?", v, re.I)
    if not m:
        return ""
    h, mi = int(m.group(2)), int(m.group(3) or 0)
    ap = (m.group(1) or "").lower()
    if ap in ("오후", "pm") and h < 12:
        h += 12
    if ap in ("오전", "am") and h == 12:
        h = 0
    return f"{h:02d}:{mi:02d}" if h < 24 and mi < 60 else ""


def split_when(v: str) -> tuple[str, str]:
    d = norm_date(v)
    rest = re.sub(r"\d{4}\s*[-./년]\s*\d{1,2}\s*[-./월]\s*\d{1,2}\s*일?", " ", v) if d else v
    return d, norm_time(rest)


def norm_type(v: str) -> str:
    v = _s(v)
    inn, out = "내부" in v, "외부" in v
    if inn and not out:
        return "내부회의"
    if out and not inn:
        return "외부회의"
    return v if v in MEETING_TYPES else ""


# ───────────────────────── 양식지 만들기 ─────────────────────────
def build_template() -> bytes:
    from docx import Document
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor

    doc = Document()
    for sec in doc.sections:
        sec.left_margin = sec.right_margin = Cm(2.2)
        sec.top_margin = sec.bottom_margin = Cm(2.0)
    st = doc.styles["Normal"]
    st.font.name, st.font.size = "맑은 고딕", Pt(11)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "맑은 고딕")

    def _font(run, size=None, bold=None, color=None):
        run.font.name = "맑은 고딕"
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "맑은 고딕")
        if size:
            run.font.size = Pt(size)
        if bold is not None:
            run.font.bold = bold
        if color:
            run.font.color.rgb = RGBColor.from_string(color)

    def _shade(cell, hex_color):
        tcPr = cell._element.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hex_color)
        tcPr.append(shd)

    def _pad(cell, before=3, after=3):
        pf = cell.paragraphs[0].paragraph_format
        pf.space_before, pf.space_after = Pt(before), Pt(after)

    def _label(cell, name, hint=""):
        _shade(cell, "EEF2F9"); _pad(cell)
        _font(cell.paragraphs[0].add_run(name), 10, True)
        if hint:
            hp = cell.add_paragraph()
            hp.paragraph_format.space_after = Pt(2)
            _font(hp.add_run(hint), 8, False, "8A97A8")

    def _widths(tbl, cms):
        """Word·LibreOffice 모두에서 칸 너비가 먹도록 표 열과 칸에 같이 적는다"""
        tbl.autofit = False
        for col, w in zip(tbl.columns, cms):
            col.width = Cm(w)
        for r in tbl.rows:
            for c, w in zip(r.cells, cms):
                c.width = Cm(w)

    def _tall(cell, lines=6):
        _pad(cell)
        for _ in range(lines - 1):
            cell.add_paragraph()

    p = doc.add_paragraph()
    _font(p.add_run(PROJECT), 9, color="5B6675")
    h = doc.add_paragraph()
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _font(h.add_run("회 의 록"), 20, True, "1F4E9C")
    h.paragraph_format.space_after = Pt(10)

    rows = [("회의명", "", 1), ("회의일", "예: 2026-10-15", 1), ("시각", "예: 14:00", 1), ("장소", "", 1),
            ("대분류 (Activity)", "활동 번호 또는 이름. 예: 1.1.1 또는 부카스센터 기자재 지원", 1),
            ("중분류 (구분)", "내부회의 또는 외부회의", 1), ("소분류 (이해관계기관)", "외부회의일 때 상대 기관. 예: DOH KMITS", 1),
            ("참석자", "이름(소속)을 쉼표로 구분", 1), ("작성자", "", 1),
            ("회의 주요 안건", "한 줄에 하나씩", 7), ("회의 결과 요약", "결정 사항과 논의 결과를 한 줄에 하나씩", 10)]
    t = doc.add_table(rows=0, cols=2)
    t.style, t.alignment = "Table Grid", WD_TABLE_ALIGNMENT.CENTER
    for name, hint, lines in rows:
        k, v = t.add_row().cells
        _label(k, name, hint)
        _tall(v, lines)
    _widths(t, (4.2, 12.4))

    hp = doc.add_paragraph()
    hp.paragraph_format.space_before, hp.paragraph_format.space_after = Pt(14), Pt(4)
    _font(hp.add_run("후속조치사항"), 13, True, "1F4E9C")
    cp = doc.add_paragraph()
    cp.paragraph_format.space_after = Pt(4)
    _font(cp.add_run("※ 한 줄에 조치 하나. 기한은 2026-10-31 처럼 적으면 대쉬보드가 챙깁니다. 줄은 더 늘려도 됩니다."), 9, color="8A97A8")
    at = doc.add_table(rows=1, cols=3)
    at.style = "Table Grid"
    for c, k in zip(at.rows[0].cells, ["조치 내용", "담당", "기한"]):
        _shade(c, "EEF2F9"); _pad(c); _font(c.paragraphs[0].add_run(k), 10, True)
    for _ in range(6):
        for c in at.add_row().cells:
            _pad(c, 4, 4)
    _widths(at, (10.0, 3.6, 3.0))

    gp = doc.add_paragraph()
    gp.paragraph_format.space_before = Pt(18)
    _font(gp.add_run("작성 안내 (이 부분은 지워도 됩니다)"), 10, True, "5B6675")
    for line in ["녹음을 글로 옮긴 뒤 AI에게 \"이 양식의 각 칸에 맞춰 정리해 줘\" 하고 Word 파일로 받으면 됩니다.",
                 "표의 왼쪽 칸(항목 이름)은 그대로 두고 오른쪽 칸만 채웁니다. 항목 순서가 바뀌어도, 줄이 늘어나도 읽힙니다.",
                 "채운 파일을 KOICA AI 성과관리 › 4. 사업관리 › 회의록·후속조치 › [회의록 추가] › [양식 업로드 (자동 채우기)] 에 올리세요."]:
        bp = doc.add_paragraph()
        bp.paragraph_format.space_after = Pt(1)
        _font(bp.add_run("· " + line), 9, color="5B6675")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def template_path() -> Path:
    """pmc/4_사업관리/양식/회의록_양식지.docx (문서 폴더 밖이라 AI 검색에 섞이지 않는다)"""
    from app import storage
    p = storage.folder("4_사업관리") / "양식" / TEMPLATE_NAME
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def template_bytes(write: bool = True) -> bytes:
    """양식지 bytes — 코드가 바뀌면 양식도 바뀌므로 늘 새로 만들고, 같은 내용을 pmc 폴더에도 적어 둔다"""
    data = build_template()
    if write:
        try:
            template_path().write_bytes(data)
        except Exception:
            pass
    return data


# ───────────────────────── 채워진 양식지 읽기 ─────────────────────────
def _cell_text(cell) -> str:
    return re.sub(r"\n\s*\n+", "\n", "\n".join(_s(p.text) for p in cell.paragraphs)).strip()


def _uniq_cells(row):
    """합쳐진 칸은 같은 칸이 여러 번 나오므로 하나로"""
    out, seen = [], set()
    for c in row.cells:
        if id(c._tc) not in seen:
            seen.add(id(c._tc)); out.append(c)
    return out


def _action_table(tbl) -> list[dict] | None:
    """머리글에 '조치'와 '담당'이 있는 표 → [{description, owner, due_date}]"""
    rows = list(tbl.rows)
    if not rows:
        return None
    head = [_norm_label(_cell_text(c)) for c in _uniq_cells(rows[0])]
    if not all(any(k in h for h in head) for k in ACTION_HEAD):
        return None
    idx = {}
    for i, h in enumerate(head):
        if "조치" in h or "내용" in h:
            idx.setdefault("description", i)
        elif "담당" in h:
            idx.setdefault("owner", i)
        elif "기한" in h or "일자" in h or "날짜" in h:
            idx.setdefault("due_date", i)
    out = []
    for r in rows[1:]:
        cells = [_cell_text(c) for c in _uniq_cells(r)]
        get = lambda k: cells[idx[k]] if k in idx and idx[k] < len(cells) else ""
        desc = get("description").replace("\n", " ").strip()
        if desc:
            out.append({"description": desc, "owner": get("owner").replace("\n", " ").strip(), "due_date": norm_date(get("due_date")) or _s(get("due_date"))})
    return out


def actions_to_text(actions: list[dict]) -> str:
    lines = []
    for a in actions:
        parts = [a["description"]] + [x for x in (a.get("owner", ""), a.get("due_date", "")) if x]
        lines.append(" / ".join(parts))
    return "\n".join(lines)


def _apply(found: dict, col: str, value: str):
    value = _s(value)
    if not value:
        return
    if col == "_when":
        d, tm = split_when(value)
        if d:
            found.setdefault("meeting_date", d)
        if tm:
            found.setdefault("meeting_time", tm)
    elif col == "meeting_date":
        d = norm_date(value)
        if d:
            found["meeting_date"] = d
    elif col == "meeting_time":
        tm = norm_time(value)
        if tm:
            found["meeting_time"] = tm
    elif col == "meeting_type":
        t = norm_type(value)
        if t:
            found["meeting_type"] = t
    elif col in TEXT_FIELDS:
        found[col] = (found[col] + "\n" + value).strip() if found.get(col) else value
    else:
        found[col] = value.replace("\n", " ").strip()


def _parse_docx(data: bytes) -> tuple[dict, list[dict]]:
    from docx import Document
    doc = Document(io.BytesIO(data))
    found: dict = {}
    actions: list[dict] = []
    for tbl in doc.tables:
        acts = _action_table(tbl)
        if acts is not None:
            actions += acts
            continue
        for row in tbl.rows:
            cells = _uniq_cells(row)
            i = 0
            while i < len(cells):
                col = _field_of(_cell_text(cells[i]))
                if col and i + 1 < len(cells):
                    _apply(found, col, _cell_text(cells[i + 1]))
                    i += 2
                else:
                    i += 1
    # 표 밖의 글: '1. 회의 주요 안건' 같은 제목 아래 줄들을 모은다 (이 앱이 만든 Word 회의록이 이 모양)
    cur, buf = None, []

    def _flush():
        if cur and buf:
            text = "\n".join(buf).strip()
            if text and text != "(없음)" and not found.get(cur):
                found[cur] = text

    for p in doc.paragraphs:
        txt = _s(p.text)
        n = _norm_label(txt)
        if n and (any(n.startswith(s) for s in STOP_HEADINGS) or n.startswith("회의id")):   # 작성 안내 · 꼬리말부터는 읽지 않는다
            _flush(); cur, buf = None, []
            break
        col = _field_of(txt) if len(txt) <= 30 else None
        if col in TEXT_FIELDS and not re.search(r"[:：]\s*\S", txt):
            _flush(); cur, buf = col, []
            continue
        if n.startswith("등록된후속조치"):
            _flush(); cur, buf = None, []
            continue
        if txt.startswith("※"):                                   # 양식지의 안내 문구
            continue
        if cur:
            if txt:
                buf.append(txt)
        elif ":" in txt or "：" in txt:                          # '회의명: …' 같은 한 줄 항목
            k, v = re.split(r"[:：]", txt, 1)
            c = _field_of(k)
            if c and c not in TEXT_FIELDS:
                _apply(found, c, v)
    _flush()
    return found, actions


def _parse_text(text: str) -> tuple[dict, list[dict]]:
    """.txt/.md — '항목: 내용' 줄과 '## 회의 주요 안건' 같은 제목 아래 줄"""
    found: dict = {}
    cur, buf = None, []

    def _flush():
        if cur and buf:
            t = "\n".join(buf).strip()
            if t and not found.get(cur):
                found[cur] = t

    for raw in text.splitlines():
        line = raw.strip()
        head = re.sub(r"^#+\s*", "", line)
        if head and len(head) <= 30:
            col = _field_of(head)
            if col in TEXT_FIELDS and not re.search(r"[:：]\s*\S", head):      # '## 회의 주요 안건'
                _flush(); cur, buf = col, []
                continue
        if not line or line.startswith("※"):
            continue
        if ":" in line or "：" in line:                                          # '회의명: …'  /  '회의 결과 요약: …'
            k, v = re.split(r"[:：]", line, 1)
            c = _field_of(k)
            if c and c not in TEXT_FIELDS:
                _flush(); cur, buf = None, []
                _apply(found, c, v)
                continue
            if c in TEXT_FIELDS:
                _flush(); cur, buf = c, ([v.strip()] if v.strip() else [])
                continue
        if cur:
            buf.append(line.lstrip("-•·* "))
    _flush()
    return found, []


def parse(name: str, data: bytes) -> dict:
    """올린 파일 → {열: 값}.  후속조치 표가 있으면 '조치 / 담당 / 기한' 줄로 바꿔 follow_up 에 넣는다."""
    ext = Path(name or "").suffix.lower()
    if ext == ".docx":
        found, actions = _parse_docx(data)
    elif ext in (".txt", ".md"):
        found, actions = _parse_text(data.decode("utf-8-sig", errors="replace"))
    else:
        raise ValueError("Word(.docx) 파일을 올려 주세요. (.txt/.md 도 됩니다)")
    if actions:
        found["follow_up"] = actions_to_text(actions)
    return {k: v for k, v in found.items() if _s(v)}
