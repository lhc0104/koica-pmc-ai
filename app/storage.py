"""목차별 데이터 저장소 — pmc/ 폴더가 '원본', SQLite는 검색·집계용 '캐시'.

  pmc/0_공통 · 1_대쉬보드 · 2_사업개요 · 3_사업일정 · 4_사업관리 · 5_성과관리 · 6_AI사업비서 · 7_문제보고

· 화면에서 저장 → DB 반영 + 해당 목차 폴더의 CSV 갱신
· 폴더의 CSV를 엑셀로 고치거나 클라우드 동기화로 파일이 바뀜 → 다음 화면 갱신 때 자동으로 DB에 반영
· 파일 입출력은 모두 이 모듈을 거치므로, 클라우드 저장소(S3 등)로 바꿀 때 이 파일만 고치면 된다.
"""
import json
import re
import shutil
import sqlite3
from datetime import date, datetime
from pathlib import Path
import pandas as pd
from .db import ROOT, connect, data_dir, schema_text

FOLDERS = ["0_공통", "1_대쉬보드", "2_사업개요", "3_사업일정", "4_사업관리", "5_성과관리", "6_AI사업비서", "7_문제보고"]

# 테이블 → (목차 폴더, 파일명, 화면 표시명)
TABLES = {
    "users":            ("0_공통",      "사용자.csv",         "사용자"),
    "outputs":          ("2_사업개요",  "사업산출물.csv",     "사업산출물 (6개)"),
    "centers":          ("2_사업개요",  "대상센터.csv",       "대상 센터"),
    "experts":          ("2_사업개요",  "전문가투입계획.csv", "전문가 투입계획(M/D)"),
    "activities":       ("3_사업일정",  "활동일정.csv",       "활동별 일정(분기) — 전체 일정표의 원천"),
    "milestones":       ("3_사업일정",  "마일스톤.csv",       "마일스톤"),
    "meetings":         ("4_사업관리",  "회의록.csv",         "회의록"),
    "action_items":     ("4_사업관리",  "후속조치.csv",       "회의 후속조치"),
    "stakeholders":     ("4_사업관리",  "이해관계자.csv",     "이해관계자"),
    "weekly_entries":   ("4_사업관리",  "주간업무보고_주차별.csv", "주간업무보고(주차별 · PM/PAO/현지직원/국내활동)"),
    "risks":            ("4_사업관리",  "위험관리대장.csv",   "위험관리대장"),
    "sub_outputs":      ("5_성과관리",  "보조산출물.csv",     "보조산출물"),
    "management_docs":  ("5_성과관리",  "관리문서.csv",       "관리문서"),
    "pdm_indicators":   ("5_성과관리",  "PDM지표.csv",        "PDM 지표"),
    "indicator_targets": ("5_성과관리", "지표연간목표.csv",   "지표 연간 목표치(성과점검표)"),
    "indicator_values": ("5_성과관리",  "지표실적값.csv",     "지표 실적값(연도별)"),
    "center_monthly":   ("5_성과관리",  "센터별월별실적.csv", "센터별 월별 실적"),
    "pdm_matrix":       ("5_성과관리",  "사업논리모형_PDM.csv", "사업논리모형(PDM)"),
    "change_model":     ("5_성과관리",  "사업변화모델.csv",   "사업변화모델"),
    "pdm_versions":     ("5_성과관리",  "PDM버전.csv",        "PDM 버전 이력"),
    "pdm_evidence":     ("5_성과관리",  "PDM근거자료.csv",    "PDM 버전 근거자료"),
    "pms_meta":         ("5_성과관리",  "성과점검표_기본정보.csv", "성과점검표 기본정보(사업명·작성일)"),
    "chat_log":         ("6_AI사업비서", "질의응답기록.csv",  "질의응답 기록"),
    "ai_questions":     ("6_AI사업비서", "AI점검질문.csv",    "AI 점검 질문"),
    "issue_reports":    ("7_문제보고",  "문제보고.csv",       "문제보고 메모"),
}
DATE_COLS = {"due_date", "next_due", "meeting_date", "week_start", "valid_from", "valid_to", "doc_date", "submitted_at"}
STATE = ROOT / "data" / ".sync_state.json"

# 회의록 분류 (v0.5) — 대분류: activity(과업 Activity 이름) / 중분류: meeting_type / 소분류: stakeholder_org(이해관계기관)
MEETING_TYPES = ["내부회의", "외부회의"]
MEETING_COLS = ["meeting_id", "meeting_date", "meeting_time", "title", "activity", "meeting_type", "stakeholder_org", "location",
                "participants", "agenda", "summary", "follow_up", "author", "file_path", "doc_id"]


# ───────── 경로 ─────────
def folder(name: str) -> Path:
    p = data_dir() / name
    p.mkdir(parents=True, exist_ok=True)
    return p


def csv_path(table: str) -> Path:
    f, fn, _ = TABLES[table]
    return folder(f) / fn


def docs_dir() -> Path:
    p = folder("4_사업관리") / "문서"
    p.mkdir(exist_ok=True)
    return p


def minutes_dir() -> Path:
    """회의록 파일(자동 생성 .md + 첨부 원본) — 문서 폴더 안이므로 AI 사업비서 검색에 자동 색인된다"""
    p = docs_dir() / "회의록"
    p.mkdir(exist_ok=True)
    return p


DOC_EXTS = {".md", ".txt", ".hwpx", ".docx", ".pdf"}


def doc_roots() -> list[Path]:
    """검색 색인 대상 폴더: 4_사업관리/문서 + 5_성과관리/PDM근거 + pmc 바로 아래 '99'로 시작하는 참고자료 폴더(예: '99. pre')"""
    ev = data_dir() / "5_성과관리" / "PDM근거"
    return [docs_dir()] + ([ev] if ev.is_dir() else []) + sorted(p for p in data_dir().glob("99*") if p.is_dir())


def doc_files() -> list[Path]:
    return [f for root in doc_roots() for f in sorted(root.rglob("*"))
            if f.is_file() and f.suffix.lower() in DOC_EXTS and f.name != "README.md"]


def overview_path() -> Path:
    return folder("2_사업개요") / "사업개요.yaml"


def tables_for(folder_name: str) -> list[str]:
    return [t for t, (f, _, _) in TABLES.items() if f == folder_name]


def rel(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT))
    except ValueError:
        return str(p)


# ───────── 동기화 상태(이 PC에서 마지막으로 맞춘 파일 시각) ─────────
def _state() -> dict:
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _remember(key: str, value) -> None:
    s = _state()
    s[key] = value
    STATE.parent.mkdir(exist_ok=True)
    STATE.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")


# ───────── 테이블 정보 ─────────
def _cols(con, table: str) -> list[sqlite3.Row]:
    return con.execute(f"PRAGMA table_info({table})").fetchall()


def _count(con, table: str) -> int:
    return con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


# ───────── DB → 파일 ─────────
def export_table(table: str) -> bool:
    """DB 내용을 해당 목차 폴더의 CSV로 저장. 엑셀에서 파일을 열어 둔 경우 False."""
    with connect(readonly=True) as con:
        df = pd.read_sql_query(f"SELECT * FROM {table}", con)
    p = csv_path(table)
    try:
        df.to_csv(p, index=False, encoding="utf-8-sig")
    except PermissionError:
        return False
    _remember(table, p.stat().st_mtime)
    return True


# ───────── 파일 → DB ─────────
def _backup(table: str, keep: int = 20) -> None:
    """바뀐 파일을 불러오기 직전에 현재 DB 내용을 pmc/_백업 에 남긴다(동기화 충돌·덜 저장된 파일 대비)"""
    d = data_dir() / "_백업"
    d.mkdir(parents=True, exist_ok=True)
    with connect(readonly=True) as con:
        df = pd.read_sql_query(f"SELECT * FROM {table}", con)
    stem = TABLES[table][1][:-4]
    df.to_csv(d / f"{stem}_{datetime.now():%Y%m%d_%H%M%S}.csv", index=False, encoding="utf-8-sig")
    for old in sorted(d.glob(f"{stem}_*.csv"))[:-keep]:
        old.unlink()


def _read_csv(p: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "cp949"):  # 한글 엑셀에서 'CSV'로 저장하면 cp949가 된다
        try:
            return pd.read_csv(p, dtype=str, keep_default_na=False, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"{p.name}: 인코딩을 읽을 수 없습니다 (UTF-8 또는 CP949로 저장해 주세요)")


def _norm_date(v: str) -> str:
    v = (v or "").strip()
    if not v or re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        return v
    try:
        return pd.to_datetime(v).strftime("%Y-%m-%d")
    except Exception:
        return v


def _write_rows(table: str, df: pd.DataFrame) -> None:
    """테이블 내용을 df로 통째로 교체(한 트랜잭션 — 실패하면 기존 내용 유지)"""
    con = connect()
    try:
        info = _cols(con, table)
        names = [c["name"] for c in info if c["name"] in df.columns]
        numeric = {c["name"] for c in info if c["type"].upper() in ("REAL", "INTEGER")}
        rows = []
        for rec in df[names].to_dict("records"):
            row = []
            for n in names:
                v = rec[n]
                v = None if v is None or (isinstance(v, float) and pd.isna(v)) else v
                if isinstance(v, str):
                    v = v.strip()
                if n in DATE_COLS and isinstance(v, str):
                    v = _norm_date(v)
                if n in numeric:
                    v = None if v in ("", None) else float(v) if "." in str(v) else int(float(v))
                elif v is None:
                    v = ""
                row.append(v)
            rows.append(row)
        con.execute("BEGIN")
        con.execute(f"DELETE FROM {table}")
        con.executemany(f"INSERT INTO {table}({','.join(names)}) VALUES ({','.join('?' * len(names))})", rows)
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def _normalize_meetings(df: pd.DataFrame) -> pd.DataFrame:
    """이전 버전 회의록(meeting_type 에 'DOH', 'PSC' 같은 기관명이 들어 있던 형식)을 v0.5 분류로 맞춘다.
    중분류는 내부회의/외부회의 두 가지만 두고, 기관명은 소분류(stakeholder_org)로 옮긴다."""
    df = df.copy()
    for c in MEETING_COLS:
        if c not in df.columns:
            df[c] = ""
    mt = df["meeting_type"].fillna("").astype(str).str.strip()
    org = df["stakeholder_org"].fillna("").astype(str).str.strip()
    legacy = ~mt.isin(MEETING_TYPES)
    df.loc[legacy & (org == "") & ~mt.str.contains("내부") & (mt != ""), "stakeholder_org"] = mt[legacy & (org == "") & ~mt.str.contains("내부") & (mt != "")]
    df.loc[legacy, "meeting_type"] = mt[legacy].map(lambda v: "내부회의" if "내부" in v else "외부회의")
    return df


def import_table(table: str, path: Path | None = None) -> int:
    df = _read_csv(path or csv_path(table))
    if table == "meetings":
        df = _normalize_meetings(df)
    _write_rows(table, df)
    return len(df)


# ───────── 화면에서 편집한 표 저장 ─────────
def save_table(table: str, df: pd.DataFrame) -> tuple[bool, str]:
    df = df.copy()
    df = df[~df.apply(lambda r: all(v is None or str(v).strip() in ("", "nan", "None") for v in r), axis=1)]
    if table == "meetings":
        df = _normalize_meetings(df)
    with connect(readonly=True) as con:
        info = _cols(con, table)
    for c in info:
        n = c["name"]
        if n not in df.columns:
            continue
        auto_id = c["pk"] and c["type"].upper() == "INTEGER"
        blank = df[n].isna() | (df[n].astype(str).str.strip() == "")
        if (c["notnull"] or c["pk"]) and not auto_id and blank.any():
            return False, f"'{n}' 칸이 비어 있는 행이 있습니다."
        if c["pk"] and not auto_id and df[n].astype(str).duplicated().any():
            return False, f"'{n}' 값이 중복된 행이 있습니다."
        if n in DATE_COLS:
            bad = [v for v in df[n].dropna().astype(str).map(_norm_date) if v and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v)]
            if bad:
                return False, f"'{n}' 날짜 형식을 확인해 주세요 (예: 2026-10-05). 문제 값: {bad[0]}"
    try:
        _write_rows(table, df)
    except (sqlite3.IntegrityError, ValueError) as e:
        return False, f"저장하지 못했습니다: {e}"
    if not export_table(table):
        return True, f"DB에는 저장했지만 {TABLES[table][1]} 파일이 엑셀에서 열려 있어 파일은 갱신하지 못했습니다. 엑셀을 닫고 다시 저장해 주세요."
    return True, f"저장했습니다 → {rel(csv_path(table))}"


# ───────── 문서 폴더 색인 ─────────
def _docs_signature() -> str:
    return "|".join(f"{f.name}:{f.stat().st_mtime:.0f}:{f.stat().st_size}" for f in doc_files())


def sync_docs(force: bool = False) -> int | None:
    sig = _docs_signature()
    if not force and _state().get("__docs__") == sig:
        return None
    from scripts.ingest_docs import ingest_all
    n = ingest_all()
    _remember("__docs__", sig)
    return n


NEW_COLS = {"outputs": ["outcome", "implementer", "deliverable"], "sub_outputs": ["due_rule"], "management_docs": ["due_rule", "contents"],
            "pdm_indicators": ["target_basis", "collector", "origin", "remark"], "milestones": ["due_rule"],
            "meetings": ["meeting_time", "activity", "stakeholder_org", "location", "agenda", "follow_up", "author", "file_path"],
            "pdm_matrix": ["version INTEGER DEFAULT 1"]}      # 열 이름 뒤에 타입을 적으면 그대로 사용(없으면 TEXT)


def _migrate(con) -> set[str]:
    """이전 버전에서 만든 DB에 새 열을 추가(CREATE TABLE IF NOT EXISTS 로는 기존 표가 바뀌지 않으므로). 반환: 열이 추가된 테이블"""
    changed = set()
    for t, cols in NEW_COLS.items():
        have = {c["name"] for c in _cols(con, t)}
        for c in cols:
            name = c.split()[0]
            if name not in have:
                con.execute(f"ALTER TABLE {t} ADD COLUMN {c if ' ' in c else c + ' TEXT'}")
                changed.add(t)
    if "meetings" in changed:                      # v0.4 이전 회의록: 기관명 → 소분류, 중분류는 내부/외부회의로
        con.execute("UPDATE meetings SET stakeholder_org = meeting_type WHERE IFNULL(stakeholder_org,'')='' "
                    "AND meeting_type NOT IN ('내부회의','외부회의') AND meeting_type NOT LIKE '%내부%' AND IFNULL(meeting_type,'')<>''")
        con.execute("UPDATE meetings SET meeting_type = CASE WHEN meeting_type LIKE '%내부%' THEN '내부회의' ELSE '외부회의' END "
                    "WHERE IFNULL(meeting_type,'') NOT IN ('내부회의','외부회의')")
        con.commit()
    return changed


# ───────── 회의록 추가 (v0.5) ─────────
def next_meeting_id() -> str:
    with connect(readonly=True) as con:
        ids = [r[0] for r in con.execute("SELECT meeting_id FROM meetings")]
    nums = [int(m.group(1)) for i in ids for m in [re.search(r"(\d+)\s*$", str(i))] if m]
    return f"MT-{(max(nums) + 1 if nums else 1):03d}"


def parse_follow_up(text: str) -> list[dict]:
    """후속조치사항 텍스트 → 후속조치(action_items) 행.  한 줄에 하나, '조치 내용 / 담당 / 기한' 순서(담당·기한은 선택)"""
    out = []
    for line in (text or "").splitlines():
        line = line.strip().lstrip("-•·*○ㅇ ").strip()
        if not line:
            continue
        parts = [p.strip() for p in re.split(r"\s*[/|]\s*", line)]
        desc, owner, due = parts[0], "", ""
        for p in parts[1:]:
            d = _norm_date(p)
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
                due = d
            elif p and not owner:
                owner = p
        if desc:
            out.append({"description": desc, "owner": owner, "due_date": due})
    return out


def _safe_name(s: str, n: int = 60) -> str:
    return re.sub(r'[\\/:*?"<>|\r\n\t]+', " ", str(s or "")).strip()[:n] or "회의록"


def add_meeting(rec: dict, attachment: tuple[str, bytes] | None = None, add_org: bool = True) -> tuple[str, str]:
    """회의록 1건 저장: DB + pmc/4_사업관리/회의록.csv, 후속조치 등록, 첨부·검색용 회의록 파일 저장. 반환: (meeting_id, 안내문)"""
    from .minutes_doc import to_markdown
    mid = str(rec.get("meeting_id") or "").strip() or next_meeting_id()
    rec = {c: str(rec.get(c) or "").strip() for c in MEETING_COLS}
    rec["meeting_id"], rec["meeting_date"] = mid, _norm_date(rec["meeting_date"])
    if rec["meeting_type"] not in MEETING_TYPES:
        rec["meeting_type"] = "내부회의" if "내부" in rec["meeting_type"] else "외부회의"
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", rec["meeting_date"]):
        raise ValueError("회의일 형식을 확인해 주세요 (예: 2026-10-05).")
    d = minutes_dir()
    stem = f"{mid}_{rec['meeting_date']}_{_safe_name(rec['title'])}"
    if attachment and attachment[0]:
        p = d / f"{stem}_첨부_{_safe_name(Path(attachment[0]).name, 80)}"
        p.write_bytes(attachment[1])
        rec["file_path"] = rel(p)
    actions = parse_follow_up(rec["follow_up"])
    rec["doc_id"] = rec["doc_id"] or f"MTG_{mid}"
    (d / f"{stem}.md").write_text(to_markdown(rec, actions), encoding="utf-8")   # AI 사업비서 검색용(문서 폴더 → 자동 색인)
    with connect() as con:
        if con.execute("SELECT 1 FROM meetings WHERE meeting_id=?", (mid,)).fetchone():
            raise ValueError(f"회의ID {mid}가 이미 있습니다.")
        con.execute(f"INSERT INTO meetings({','.join(MEETING_COLS)}) VALUES ({','.join('?' * len(MEETING_COLS))})",
                    [rec[c] for c in MEETING_COLS])
        con.executemany("INSERT INTO action_items(meeting_id, description, owner, due_date, status) VALUES (?,?,?,?,'미이행')",
                        [(mid, a["description"], a["owner"], a["due_date"]) for a in actions])
        org = rec["stakeholder_org"]
        if add_org and org and not con.execute("SELECT 1 FROM stakeholders WHERE org=? OR (org || ' ' || IFNULL(dept,''))=?", (org, org)).fetchone():
            n = con.execute("SELECT COUNT(*) FROM stakeholders").fetchone()[0]
            con.execute("INSERT INTO stakeholders(stakeholder_id, org, dept, category, valid_from) VALUES (?,?,?,?,?)",
                        (f"SH-{n + 1:02d}", org, "", "회의록에서 추가", date.today().isoformat()))
            con.commit()
            export_table("stakeholders")
        con.commit()
    ok = export_table("meetings") and export_table("action_items")
    msg = f"회의록 {mid}을(를) 저장했습니다 → {rel(csv_path('meetings'))}" + (f" · 후속조치 {len(actions)}건 등록" if actions else "")
    if not ok:
        msg += " (CSV 파일이 엑셀에서 열려 있어 파일 갱신은 다음 저장 때 반영됩니다)"
    return mid, msg


def meeting_actions(mid: str) -> list[dict]:
    with connect(readonly=True) as con:
        return [dict(r) for r in con.execute("SELECT * FROM action_items WHERE meeting_id=? ORDER BY due_date, action_id", (mid,))]


# ───────── 시작할 때 한 번 + 화면 갱신 때마다 가볍게 ─────────
def bootstrap(from_seed: bool = False) -> list[str]:
    """폴더·스키마 준비, 예전 버전 데이터 이전, 파일↔DB 맞추기. 반환: 사용자에게 알릴 메시지"""
    msgs = []
    for f in FOLDERS:
        folder(f)
    with connect() as con:
        first_pms = not con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='pms_meta'").fetchone()   # v0.5 성과점검표 양식 첫 적용?
        had_ind = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='pdm_indicators'").fetchone()
        con.executescript(schema_text())
        migrated = _migrate(con)
    minutes_dir()

    legacy = ROOT / "data" / "issue_reports.db"          # v0.2의 별도 메모 파일 → 본 DB로 이전
    if legacy.exists():
        with connect() as con:
            if _count(con, "issue_reports") == 0:
                old = sqlite3.connect(legacy)
                rows = old.execute("SELECT id,created_at,author,menu,kind,content,status FROM issue_reports").fetchall()
                old.close()
                con.executemany("INSERT INTO issue_reports(id,created_at,author,menu,kind,content,status) VALUES (?,?,?,?,?,?,?)", rows)
                if rows:
                    msgs.append(f"이전 버전의 문제보고 메모 {len(rows)}건을 옮겼습니다.")
        legacy.rename(legacy.with_suffix(".db.migrated"))

    if not overview_path().exists():
        shutil.copy(ROOT / "config" / "overview.yaml", overview_path())
    if not any(docs_dir().glob("*.md")) and not any(docs_dir().glob("*.txt")):
        for f in (ROOT / "data" / "documents").glob("*"):
            if f.suffix in (".md", ".txt") and f.name != "README.md":
                shutil.copy(f, docs_dir() / f.name)

    state = _state()
    for t in TABLES:
        p, seed = csv_path(t), ROOT / "data" / "seed" / f"{t}.csv"
        with connect() as con:
            n_db = _count(con, t)
        try:
            if from_seed and seed.exists():
                import_table(t, seed); export_table(t)
            elif p.exists() and (n_db == 0 or state.get(t) != p.stat().st_mtime):
                if n_db:
                    _backup(t)
                n = import_table(t)                       # 파일이 원본: 엑셀 수정·클라우드 동기화 반영
                _remember(t, p.stat().st_mtime)
                if n_db and state.get(t) is not None:
                    msgs.append(f"{TABLES[t][1]} 파일이 바뀌어 다시 불러왔습니다 ({n}행).")
            elif not p.exists():
                if n_db == 0 and seed.exists():
                    import_table(t, seed)
                export_table(t)
        except Exception as e:
            _remember(t, p.stat().st_mtime if p.exists() else None)
            msgs.append(f"⚠️ {TABLES[t][1]} 불러오기 실패 — {e}")
    for t in migrated:                                   # 새 열이 생긴 표는 CSV 파일도 새 형식으로 다시 써 둔다
        if t in TABLES and export_table(t):
            msgs.append(f"{TABLES[t][1]} 파일에 새 항목(열)을 추가했습니다.")
    if first_pms and had_ind and not from_seed:          # KOICA 성과관리양식 v3.2 첫 적용: 지표 정의·연간 목표치를 양식 기준으로 한 번 갱신(이전 표는 _백업에)
        for t in ("pdm_indicators", "indicator_targets"):
            seed = ROOT / "data" / "seed" / f"{t}.csv"
            if seed.exists():
                _backup(t)
                import_table(t, seed)
                export_table(t)
        msgs.append("성과점검표를 KOICA 성과관리양식 v3.2 기준으로 갱신했습니다 (이전 지표·목표치 표는 pmc/_백업 에 있습니다).")
    n = sync_docs()
    if n is not None and state.get("__docs__") is not None:
        msgs.append(f"문서 폴더가 바뀌어 다시 색인했습니다 ({n}건).")
    return msgs


# ───────── 1. 대쉬보드 점검 결과 스냅샷 ─────────
def save_alert_snapshot(alerts: dict, today: date | None = None) -> Path | None:
    today = today or date.today()
    rows = []
    for r in alerts["기한"]:
        rows.append(["기한", r["ref"], f"[{r['구분']}] {r['항목']}", r["기한"], r["담당"], f"{r['상태']} / {r['경보']}"])
    for r in alerts["기초선누락"]:
        rows.append(["지표 미확정", r["indicator_id"], r["name"], "", "", f"{r['missing']} 미확정 / 자료원: {r['data_source']}"])
    for r in alerts["이상치"]:
        rows.append(["이상치", r["center_id"], f"{r['name']} {r['month']} {r['metric']}", "", "", f"{r['prev']:.0f}→{r['value']:.0f} ({r['change_pct']}%)"])
    for r in alerts["후속조치"]:
        rows.append(["후속조치", f"action-{r['action_id']}", r["description"], r["due_date"], r["owner"], r["status"] + (" / 기한경과" if r["overdue"] else "")])
    p = folder("1_대쉬보드") / f"점검결과_{today.isoformat()}.csv"
    try:
        pd.DataFrame(rows, columns=["점검유형", "대상", "내용", "기한", "담당", "상태"]).to_csv(p, index=False, encoding="utf-8-sig")
    except PermissionError:
        return None
    return p


def save_conversation(view: list[tuple[str, str]]) -> Path:
    d = folder("6_AI사업비서") / "대화기록"
    d.mkdir(exist_ok=True)
    p = d / f"대화_{datetime.now():%Y%m%d_%H%M%S}.md"
    who = {"user": "질문", "assistant": "AI 사업비서"}
    p.write_text(f"# AI 사업비서 대화 기록 ({datetime.now():%Y-%m-%d %H:%M})\n\n" +
                 "\n\n".join(f"## {who.get(r, r)}\n\n{t}" for r, t in view), encoding="utf-8")
    return p


# ───────── 성과점검표(모니터링 매트릭스) 편집용: 지표 + 연간 목표치를 한 표로 (v0.5) ─────────
YEARS = list(range(2026, 2033))


def indicator_sheet() -> pd.DataFrame:
    """pdm_indicators 에 연간 목표치 열(y2026~y2032)을 붙인 편집용 표"""
    with connect(readonly=True) as con:
        ind = pd.read_sql_query("SELECT * FROM pdm_indicators ORDER BY CASE level WHEN 'Impact' THEN 0 WHEN 'Outcome' THEN 1 ELSE 2 END, indicator_id", con)
        tg = pd.read_sql_query("SELECT indicator_id, year, target FROM indicator_targets", con)
    for y in YEARS:
        m = dict(zip(tg[tg["year"] == y]["indicator_id"], tg[tg["year"] == y]["target"]))
        ind[f"y{y}"] = ind["indicator_id"].map(m)
    return ind


def save_indicator_sheet(df: pd.DataFrame) -> tuple[bool, str]:
    """편집한 표를 pdm_indicators + indicator_targets 로 나누어 저장"""
    df = df.copy()
    ycols = [f"y{y}" for y in YEARS if f"y{y}" in df.columns]
    ok, msg = save_table("pdm_indicators", df.drop(columns=ycols))
    if not ok:
        return ok, msg
    with connect(readonly=True) as con:
        notes = {(r["indicator_id"], int(r["year"])): r["note"] for r in con.execute("SELECT indicator_id, year, note FROM indicator_targets")}
    rows = []
    for r in df.to_dict("records"):
        iid = str(r["indicator_id"]).strip()
        for y in YEARS:
            v = r.get(f"y{y}")
            blank = v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == ""
            note = notes.get((iid, y), "")
            if blank and not note:
                continue                                   # 값도 비고도 없는 칸은 행을 만들지 않는다 (TBD 비고가 있는 칸은 유지)
            rows.append({"indicator_id": iid, "year": y, "target": "" if blank else v, "note": note})
    ok2, msg2 = save_table("indicator_targets", pd.DataFrame(rows, columns=["indicator_id", "year", "target", "note"]))
    return ok2, (f"{msg} · 연간 목표치 {len(rows)}칸 저장 → {rel(csv_path('indicator_targets'))}" if ok2 else msg2)


def pdm_source_files() -> list[Path]:
    """pmc/99. pre/2. PDM 폴더의 원문 파일(PDM·성과점검표·사업변화모델·제안 양식)"""
    d = data_dir() / "99. pre" / "2. PDM"
    return sorted(f for f in d.glob("*") if f.is_file()) if d.exists() else []


# ───────── 사업논리모형(PDM) 버전 관리 (v0.5) ─────────
PDM_STATUS = ["초안", "검토중", "확정"]


def pdm_versions() -> list[dict]:
    """버전 이력(오름차순). 표에는 있는데 이력이 없는 버전은 자동으로 채운다."""
    with connect() as con:
        have = {r[0] for r in con.execute("SELECT version FROM pdm_versions")}
        used = {int(r[0]) for r in con.execute("SELECT DISTINCT IFNULL(version,1) FROM pdm_matrix")}
        for v in sorted(used - have):
            con.execute("INSERT INTO pdm_versions(version, created_at, status, reason) VALUES (?,?,?,?)",
                        (v, date.today().isoformat(), "확정" if v == 1 else "초안", "RFP 첨부 PDM 원본" if v == 1 else ""))
        con.commit()
        rows = [dict(r) for r in con.execute("SELECT * FROM pdm_versions ORDER BY version")]
    if used - have:
        export_table("pdm_versions")
    return rows


def pdm_rows(version: int) -> pd.DataFrame:
    with connect(readonly=True) as con:
        return pd.read_sql_query("SELECT * FROM pdm_matrix WHERE IFNULL(version,1)=? ORDER BY seq, id", con, params=(int(version),))


def pdm_evidence_dir(version: int) -> Path:
    p = folder("5_성과관리") / "PDM근거" / f"v{int(version)}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _pdm_write_doc(version: int) -> None:
    """버전별 PDM 내용을 검색용 문서로 — AI 사업비서가 'v2에서 무엇이 바뀌었나' 같은 질문에 답할 수 있게"""
    rows = pdm_rows(version).fillna("").to_dict("records")
    meta = next((m for m in pdm_versions() if m["version"] == int(version)), {})
    lines = ["---", f"doc_id: PDM_v{version}", f'title: "사업논리모형(PDM) v{version}"', "doc_type: 기준문서", f"doc_date: {meta.get('created_at') or ''}", "source_org: PMC", "---", "",
             f"# 사업논리모형(PDM) v{version} — {meta.get('status') or ''}", "", f"- 생성일: {meta.get('created_at') or ''} · 작성자: {meta.get('author') or ''} · 승인일: {meta.get('approved_at') or ''}",
             f"- 변경 사유: {meta.get('reason') or ''}", ""]
    for r in rows:
        lines += [f"## [{r['level']}] {r['code']} {r['summary']}".strip(), ""]
        for k, lab in (("indicators", "객관적 검증지표"), ("mov", "검증수단"), ("assumptions", "중요가정"), ("proposal", "검증지표 추가제안"), ("note", "비고")):
            if str(r.get(k) or "").strip():
                lines += [f"- {lab}: {r[k]}"]
        lines.append("")
    (pdm_evidence_dir(version) / f"PDM_v{version}.md").write_text("\n".join(lines), encoding="utf-8")


def pdm_add_version(author: str = "", reason: str = "") -> int:
    """마지막 버전의 행을 모두 복사해 새 버전을 만든다. 반환: 새 버전 번호"""
    vers = pdm_versions()
    last = vers[-1]["version"] if vers else 1
    new = int(last) + 1
    src = pdm_rows(last).drop(columns=["id"])
    src["version"] = new
    with connect() as con:
        cols = list(src.columns)
        con.executemany(f"INSERT INTO pdm_matrix({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                        [tuple(None if (isinstance(v, float) and pd.isna(v)) else v for v in row) for row in src.itertuples(index=False)])
        con.execute("INSERT INTO pdm_versions(version, created_at, author, reason, status) VALUES (?,?,?,?,'초안')",
                    (new, date.today().isoformat(), author, reason or f"v{last} 복사본 — 수정 내용을 적어 주세요"))
        con.commit()
    export_table("pdm_matrix"); export_table("pdm_versions")
    _pdm_write_doc(new)
    return new


def pdm_save_version(version: int, df: pd.DataFrame, meta: dict | None = None) -> tuple[bool, str]:
    """선택한 버전의 행만 바꿔 저장(다른 버전은 그대로). meta 로 버전 정보(사유·상태·작성자·승인일)도 함께 갱신"""
    df = df.copy()
    df["version"] = int(version)
    with connect(readonly=True) as con:
        others = pd.read_sql_query("SELECT * FROM pdm_matrix WHERE IFNULL(version,1)<>?", con, params=(int(version),))
    merged = pd.concat([others, df], ignore_index=True)
    if "id" in merged.columns:
        merged = merged.drop(columns=["id"])                     # 번호는 다시 매긴다
    ok, msg = save_table("pdm_matrix", merged)
    if not ok:
        return ok, msg
    if meta:
        with connect() as con:
            con.execute("UPDATE pdm_versions SET author=?, reason=?, status=?, approved_at=?, note=? WHERE version=?",
                        (meta.get("author", ""), meta.get("reason", ""), meta.get("status") or "초안", meta.get("approved_at", ""), meta.get("note", ""), int(version)))
            con.commit()
        export_table("pdm_versions")
    _pdm_write_doc(version)
    return True, f"v{version} 저장했습니다 → {rel(csv_path('pdm_matrix'))}"


def pdm_delete_version(version: int) -> tuple[bool, str]:
    """마지막 버전(v1 제외)만 지울 수 있다. 근거 파일은 폴더에 남긴다."""
    vers = pdm_versions()
    if int(version) == 1 or int(version) != vers[-1]["version"]:
        return False, "v1과 중간 버전은 지울 수 없습니다(마지막 버전만 삭제 가능)."
    with connect() as con:
        con.execute("DELETE FROM pdm_matrix WHERE version=?", (int(version),))
        con.execute("DELETE FROM pdm_versions WHERE version=?", (int(version),))
        con.execute("DELETE FROM pdm_evidence WHERE version=?", (int(version),))
        con.commit()
    for t in ("pdm_matrix", "pdm_versions", "pdm_evidence"):
        export_table(t)
    (pdm_evidence_dir(version) / f"PDM_v{version}.md").unlink(missing_ok=True)
    return True, f"v{version}을(를) 지웠습니다. 근거 파일이 있었다면 {rel(pdm_evidence_dir(version))} 에 남아 있습니다."


def pdm_add_evidence(version: int, files: list[tuple[str, bytes]], note: str = "") -> int:
    d = pdm_evidence_dir(version)
    n = 0
    with connect() as con:
        for name, data in files:
            safe = re.sub(r'[\\/:*?"<>|\r\n\t]+', " ", Path(name).name).strip() or "file"
            p = d / safe
            i = 1
            while p.exists():                                 # 같은 이름이면 (2), (3) …
                p = d / f"{Path(safe).stem} ({i}){Path(safe).suffix}"
                i += 1
            p.write_bytes(data)
            con.execute("INSERT INTO pdm_evidence(version, file_name, file_path, note, uploaded_at) VALUES (?,?,?,?,?)",
                        (int(version), p.name, rel(p), note, datetime.now().strftime("%Y-%m-%d %H:%M")))
            n += 1
        con.commit()
    export_table("pdm_evidence")
    return n


def pdm_evidence(version: int) -> list[dict]:
    with connect(readonly=True) as con:
        return [dict(r) for r in con.execute("SELECT * FROM pdm_evidence WHERE version=? ORDER BY id DESC", (int(version),))]


def pdm_delete_evidence(eid: int) -> None:
    with connect() as con:
        r = con.execute("SELECT file_path FROM pdm_evidence WHERE id=?", (int(eid),)).fetchone()
        con.execute("DELETE FROM pdm_evidence WHERE id=?", (int(eid),))
        con.commit()
    if r and r[0]:
        (ROOT / r[0]).unlink(missing_ok=True)
    export_table("pdm_evidence")


# ───────── 성과점검표 (KOICA 성과관리양식 v3.2 배치) ─────────
PMS_META_KEYS = ["사업명(기간/예산)"] + [f"{i}차년도 작성일" for i in range(1, 8)]


def pms_meta() -> dict:
    with connect(readonly=True) as con:
        d = {r[0]: r[1] or "" for r in con.execute("SELECT key, value FROM pms_meta")}
    return {k: d.get(k, "") for k in PMS_META_KEYS} | {k: v for k, v in d.items() if k not in PMS_META_KEYS}


def save_pms_meta(d: dict) -> None:
    with connect() as con:
        con.executemany("INSERT INTO pms_meta(key, value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                        [(k, (v or "").strip()) for k, v in d.items()])
        con.commit()
    export_table("pms_meta")


def pms_groups() -> dict:
    """성과점검표 B열 이름: 영향 문장, 성과 번호→이름, 산출물 코드→이름 (사업논리모형 최신 버전 + outputs 표)"""
    vers = pdm_versions()
    rows = pdm_rows(vers[-1]["version"]).fillna("").to_dict("records") if vers else []
    impact = next((r["summary"] for r in rows if r["level"] == "영향(Impact)"), "")
    outcomes = {str(r["code"]).strip(): r["summary"] for r in rows if r["level"] == "성과(Outcome)"}
    with connect(readonly=True) as con:
        outputs = {r[0]: r[1] for r in con.execute("SELECT output_id, name FROM outputs")}
    return {"impact": impact, "outcomes": outcomes, "outputs": outputs}


def indicator_years_long() -> pd.DataFrame:
    """연간 성과점검표 편집용(긴 형식): 지표 × 구분(연간 목표치/연간 실적치) 행, 2026~2032 열"""
    with connect(readonly=True) as con:
        ind = pd.read_sql_query("SELECT indicator_id, name FROM pdm_indicators ORDER BY CASE level WHEN 'Impact' THEN 0 WHEN 'Outcome' THEN 1 ELSE 2 END, indicator_id", con)
        tg = {(r["indicator_id"], int(r["year"])): r["target"] for r in con.execute("SELECT indicator_id, year, target FROM indicator_targets")}
        av = {(r["indicator_id"], int(r["period"])): r["value"] for r in con.execute("SELECT indicator_id, period, value FROM indicator_values") if re.fullmatch(r"\d{4}", str(r["period"]))}
    out = []
    for r in ind.to_dict("records"):
        for kind, src in (("연간 목표치", tg), ("연간 실적치", av)):
            out.append({"indicator_id": r["indicator_id"], "name": r["name"], "kind": kind, **{f"y{y}": src.get((r["indicator_id"], y)) for y in YEARS}})
    return pd.DataFrame(out)


def save_indicator_years(df: pd.DataFrame) -> tuple[bool, str]:
    """긴 형식 편집표 → indicator_targets(비고 유지) + indicator_values(검증자·근거문서 유지)"""
    def _num(v, iid, y):
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        s = str(v).strip().replace(",", "").replace("%", "")
        if s == "" or s.upper() in ("TBD", "N/A", "NA", "NULL", "-"):
            return None
        try:
            return float(s)
        except ValueError:
            raise ValueError(f"숫자가 아닌 값이 있습니다: 지표 {iid} · {y}년 칸 '{v}' (빈칸·TBD·N/A만 허용)")
    with connect() as con:
        notes = {(r[0], int(r[1])): r[2] for r in con.execute("SELECT indicator_id, year, note FROM indicator_targets")}
        keep = {(r[0], str(r[1])): (r[2], r[3]) for r in con.execute("SELECT indicator_id, period, verified_by, source_doc_id FROM indicator_values")}
        try:
            t_rows, v_rows = [], []
            for r in df.to_dict("records"):
                iid = str(r["indicator_id"]).strip()
                for y in YEARS:
                    v = _num(r.get(f"y{y}"), iid, y)
                    if r["kind"] == "연간 목표치":
                        note = notes.get((iid, y), "")
                        if v is not None or note:
                            t_rows.append((iid, y, v, note))
                    elif v is not None:
                        vb, sd = keep.get((iid, str(y)), ("", ""))
                        v_rows.append((iid, str(y), v, vb, sd))
        except ValueError as e:
            return False, str(e)
        con.execute("BEGIN")
        con.execute("DELETE FROM indicator_targets")
        con.executemany("INSERT INTO indicator_targets(indicator_id, year, target, note) VALUES (?,?,?,?)", t_rows)
        con.execute("DELETE FROM indicator_values WHERE period GLOB '[0-9][0-9][0-9][0-9]'")      # 연도 단위 값만 교체(분기·월 단위 기록은 그대로)
        con.executemany("INSERT INTO indicator_values(indicator_id, period, value, verified_by, source_doc_id) VALUES (?,?,?,?,?)", v_rows)
        con.commit()
    ok = export_table("indicator_targets") and export_table("indicator_values")
    return True, f"연간 목표치 {len(t_rows)}칸 · 연간 실적치 {len(v_rows)}칸 저장" + ("" if ok else " (CSV 파일이 엑셀에서 열려 있어 파일 갱신은 다음 저장 때)")
