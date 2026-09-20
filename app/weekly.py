"""[4. 사업관리 › 주간업무보고] — 주차 계산 + 주차별·구분별 활동 내용 저장 (v0.5)

주차 규칙: 월~금 한 주. 그 주의 **목요일이 속한 달**을 기준으로 'N월 M주차'로 부른다.
  예) 2026-08-31(월)~09-04(금) → 목요일 9/3 → '9월 1주차'   (한 주의 5일 중 4일이 9월)
저장: DB weekly_entries + pmc/4_사업관리/주간업무보고_주차별.csv,  주차별 검색용 문서 pmc/4_사업관리/문서/주간업무보고/*.md
"""
import re
from datetime import date, datetime, timedelta
from . import storage
from .db import connect, settings

DEFAULT_COLUMNS = ["PM", "PAO", "현지직원1", "현지직원2", "현지직원3", "국내활동"]
WEEKDAY = "월화수목금토일"


def cfg() -> dict:
    w = settings().get("weekly") or {}
    y = w.get("years") or [2026, 2031]
    return {"years": (int(y[0]), int(y[-1])), "start": date.fromisoformat(str(w.get("start") or "2026-08-31")),
            "columns": [str(c) for c in (w.get("columns") or DEFAULT_COLUMNS)]}


def years() -> list[int]:
    a, b = cfg()["years"]
    return list(range(a, b + 1))


# ───────── 주차 계산 ─────────
def monday_of(d: date) -> date:
    return d - timedelta(days=d.weekday())


def week_key(monday: date) -> tuple[int, int, int]:
    """(연도, 월, 주차) — 목요일 기준"""
    thu = monday + timedelta(days=3)
    return thu.year, thu.month, (thu.day - 1) // 7 + 1


def label(monday: date, with_year: bool = False) -> str:
    y, m, n = week_key(monday)
    return f"{y}년 {m}월 {n}주차" if with_year else f"{m}월 {n}주차"


def range_text(monday: date) -> str:
    fri = monday + timedelta(days=4)
    return f"{monday.month}월{monday.day}일({WEEKDAY[monday.weekday()]})~{fri.month}월{fri.day}일({WEEKDAY[fri.weekday()]})"


def weeks_of_year(year: int) -> list[date]:
    """그 연도에 속한 주(목요일 기준)의 월요일 목록. 첫 해는 settings 의 start 부터."""
    start = monday_of(cfg()["start"])
    m = monday_of(date(year, 1, 1))
    if week_key(m)[0] < year:
        m += timedelta(days=7)
    m = max(m, start)
    out = []
    while week_key(m)[0] == year:
        out.append(m)
        m += timedelta(days=7)
    return out


# ───────── 저장·조회 ─────────
def entries(monday: date) -> dict[str, dict]:
    """{구분: 행} — 그 주에 입력된 것만"""
    with connect(readonly=True) as con:
        return {r["role"]: dict(r) for r in con.execute("SELECT * FROM weekly_entries WHERE week_start=?", (monday.isoformat(),))}


def entries_by_week(year: int) -> dict[str, dict[str, dict]]:
    """{주 시작일: {구분: 행}} — 한 해 전체 (화면에서 칸 색을 정할 때 한 번에 읽는다)"""
    out: dict[str, dict[str, dict]] = {}
    with connect(readonly=True) as con:
        for r in con.execute("SELECT * FROM weekly_entries WHERE week_start BETWEEN ? AND ?", (f"{year - 1}-12-25", f"{year + 1}-01-07")):
            out.setdefault(r["week_start"], {})[r["role"]] = dict(r)
    return out


def get_entry(monday: date, role: str) -> dict | None:
    return entries(monday).get(role)


def save_entry(monday: date, role: str, author: str, position: str, content: str) -> str:
    """저장(같은 주·구분이 있으면 덮어씀). 내용이 비면 삭제. 반환: 안내문"""
    author, position, content = (author or "").strip(), (position or "").strip(), (content or "").strip()
    ws = monday.isoformat()
    with connect() as con:
        if not content:
            con.execute("DELETE FROM weekly_entries WHERE week_start=? AND role=?", (ws, role))
        else:
            con.execute("INSERT INTO weekly_entries(week_start, role, author, position, content, updated_at) VALUES (?,?,?,?,?,?) "
                        "ON CONFLICT(week_start, role) DO UPDATE SET author=excluded.author, position=excluded.position, "
                        "content=excluded.content, updated_at=excluded.updated_at",
                        (ws, role, author, position, content, datetime.now().strftime("%Y-%m-%d %H:%M")))
        con.commit()
    ok = storage.export_table("weekly_entries")
    _write_week_doc(monday)
    msg = f"{label(monday, True)} {role} 칸을 " + ("지웠습니다." if not content else "저장했습니다.")
    return msg + ("" if ok else " (CSV 파일이 엑셀에서 열려 있어 파일 갱신은 다음 저장 때 반영됩니다)")


def delete_entry(monday: date, role: str) -> str:
    return save_entry(monday, role, "", "", "")


# ───────── 주차 리포트(검색용 문서·Word·PDF 공통 데이터) ─────────
def report_rows(monday: date) -> list[dict]:
    """settings 의 열 순서대로 [구분, 작성자, 직책, 활동내용] — 입력 안 된 칸은 빈칸"""
    e = entries(monday)
    rows = [{"role": c, **{k: (e.get(c) or {}).get(k, "") for k in ("author", "position", "content", "updated_at")}} for c in cfg()["columns"]]
    for r in sorted(set(e) - set(cfg()["columns"])):          # 열 이름이 바뀐 뒤에도 옛 칸의 내용은 보이게
        rows.append({"role": r, **{k: e[r].get(k, "") for k in ("author", "position", "content", "updated_at")}})
    return rows


def report_title(monday: date) -> str:
    return f"주간업무보고 — {label(monday, True)} ({range_text(monday)})"


def docs_dir():
    p = storage.docs_dir() / "주간업무보고"
    p.mkdir(exist_ok=True)
    return p


def _write_week_doc(monday: date) -> None:
    """그 주의 모든 칸을 한 문서로 — AI 사업비서 검색용(.md, 문서 폴더라 자동 색인)"""
    y, m, n = week_key(monday)
    p = docs_dir() / f"주간업무보고_{y}-{m:02d}-{n}주차_{monday.isoformat()}.md"
    rows = [r for r in report_rows(monday) if r["content"]]
    if not rows:
        p.unlink(missing_ok=True)
        return
    body = ["---", f"doc_id: WK_{monday.isoformat()}", f'title: "{report_title(monday)}"', "doc_type: 주간보고", f"doc_date: {monday.isoformat()}",
            "source_org: PMC", "---", "", f"# {report_title(monday)}", ""]
    for r in rows:
        who = " · ".join(x for x in (r["author"], r["position"]) if x)
        body += [f"## {r['role']}" + (f" ({who})" if who else ""), "", r["content"], ""]
    p.write_text("\n".join(body), encoding="utf-8")


def file_stem(monday: date) -> str:
    y, m, n = week_key(monday)
    return re.sub(r"[\\/:*?\"<>|]", "", f"주간업무보고_{y}년{m}월{n}주차")
