"""6. 문서관리 — 사업 문서함 (pmc/6_문서관리) 파일·폴더 다루기 (v0.7)

· 폴더 = 분류. 기본 분류(01_계약·행정 … 99_기타)는 처음 한 번만 만들어 주고, 그 뒤로는 사용자가 마음대로 만들고 지운다.
· 여기 넣은 .hwpx .docx .pdf .md .txt 는 AI 사업비서 검색에 자동으로 색인된다 (storage.doc_roots).
· Google 드라이브와 주고받는 기능은 gdrive.py 에 있다.
"""
import re
import shutil
from datetime import datetime
from pathlib import Path

from app import storage

KIND = {".pdf": "PDF", ".docx": "Word", ".doc": "Word", ".hwpx": "한글", ".hwp": "한글", ".xlsx": "Excel", ".xls": "Excel", ".csv": "CSV",
        ".pptx": "PPT", ".ppt": "PPT", ".md": "텍스트", ".txt": "텍스트", ".jpg": "사진", ".jpeg": "사진", ".png": "사진", ".gif": "사진",
        ".zip": "압축", ".mp3": "음성", ".m4a": "음성", ".wav": "음성", ".mp4": "영상"}
INDEXED = storage.DOC_EXTS


def root() -> Path:
    return storage.docs_mgmt_dir()


def safe_name(name: str) -> str:
    """파일·폴더 이름에서 경로 문자와 금지 문자를 뺀다"""
    n = re.sub(r'[\\/:*?"<>|\r\n\t]+', " ", str(name or "")).strip().strip(".")
    return n[:120]


def resolve(rel: str) -> Path:
    """문서함 안의 상대 경로 → 실제 경로. 문서함 밖으로 나가면 문서함 루트"""
    p = (root() / rel).resolve() if rel else root().resolve()
    try:
        p.relative_to(root().resolve())
    except ValueError:
        return root()
    return p


def rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(root().resolve())).replace("\\", "/")
    except ValueError:
        return ""


def listing(rel_path: str = "") -> tuple[list[dict], list[dict]]:
    """(하위 폴더들, 파일들) — 이름순. 파일: name, rel, kind, size, mtime, indexed"""
    d = resolve(rel_path)
    folders, files = [], []
    if not d.is_dir():
        return folders, files
    for p in sorted(d.iterdir(), key=lambda x: x.name.lower()):
        if p.name.startswith(".") or p.name == "README.md":
            continue
        if p.is_dir():
            n_files = sum(1 for x in p.rglob("*") if x.is_file() and not x.name.startswith("."))
            folders.append({"name": p.name, "rel": rel(p), "count": n_files})
        else:
            st = p.stat()
            files.append({"name": p.name, "rel": rel(p), "kind": KIND.get(p.suffix.lower(), p.suffix.lstrip(".").upper() or "파일"),
                          "size": st.st_size, "mtime": datetime.fromtimestamp(st.st_mtime), "indexed": p.suffix.lower() in INDEXED, "path": p})
    return folders, files


def count_all() -> tuple[int, int]:
    n_f = sum(1 for x in root().rglob("*") if x.is_file() and not x.name.startswith("."))
    n_d = sum(1 for x in root().rglob("*") if x.is_dir())
    return n_f, n_d


def search(q: str) -> list[dict]:
    """파일 이름으로 문서함 전체 찾기"""
    ql = (q or "").strip().lower()
    if not ql:
        return []
    out = []
    for p in sorted(root().rglob("*")):
        if p.is_file() and ql in p.name.lower() and not p.name.startswith("."):
            st = p.stat()
            out.append({"name": p.name, "rel": rel(p), "folder": rel(p.parent) or "(문서함)", "kind": KIND.get(p.suffix.lower(), p.suffix.lstrip(".").upper() or "파일"),
                        "size": st.st_size, "mtime": datetime.fromtimestamp(st.st_mtime), "indexed": p.suffix.lower() in INDEXED, "path": p})
    return out[:200]


def fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}GB"


def save_files(rel_path: str, files: list[tuple[str, bytes]]) -> tuple[int, list[str]]:
    """올린 파일 저장. 같은 이름이 있으면 '이름 (2).ext' 로"""
    storage.check_edit()
    d = resolve(rel_path)
    d.mkdir(parents=True, exist_ok=True)
    saved = []
    for name, data in files:
        name = safe_name(name) or "파일"
        p = d / name
        k = 2
        while p.exists():
            p = d / f"{Path(name).stem} ({k}){Path(name).suffix}"
            k += 1
        p.write_bytes(data)
        saved.append(p.name)
    storage.sync_docs(force=True)
    return len(saved), saved


def make_folder(rel_path: str, name: str) -> tuple[bool, str]:
    storage.check_edit()
    name = safe_name(name)
    if not name:
        return False, "폴더 이름을 적어 주세요."
    p = resolve(rel_path) / name
    if p.exists():
        return False, f"'{name}' 폴더가 이미 있습니다."
    p.mkdir(parents=True)
    return True, f"'{name}' 폴더를 만들었습니다."


def rename(rel_path: str, new_name: str) -> tuple[bool, str]:
    storage.check_edit()
    p = resolve(rel_path)
    if p == root():
        return False, "문서함 자체의 이름은 바꿀 수 없습니다."
    new_name = safe_name(new_name)
    if not new_name:
        return False, "새 이름을 적어 주세요."
    if p.is_file() and not Path(new_name).suffix:
        new_name += p.suffix
    q = p.with_name(new_name)
    if q.exists():
        return False, f"'{new_name}' 이(가) 이미 있습니다."
    p.rename(q)
    storage.sync_docs(force=True)
    return True, f"'{p.name}' → '{new_name}'"


def delete(rel_path: str) -> tuple[bool, str]:
    """파일은 바로 지우고, 폴더는 pmc/_휴지통 으로 옮긴다 (실수 대비)"""
    storage.check_edit()
    p = resolve(rel_path)
    if p == root() or not p.exists():
        return False, "지울 수 없습니다."
    trash = storage.data_dir() / "_휴지통"
    trash.mkdir(exist_ok=True)
    dest = trash / f"{datetime.now():%Y%m%d_%H%M%S}_{p.name}"
    shutil.move(str(p), str(dest))
    storage.sync_docs(force=True)
    return True, f"'{p.name}' 을(를) pmc/_휴지통 으로 옮겼습니다. 필요하면 탐색기에서 되돌릴 수 있습니다."


def move(rel_path: str, to_folder_rel: str) -> tuple[bool, str]:
    storage.check_edit()
    p, d = resolve(rel_path), resolve(to_folder_rel)
    if p == root() or not p.exists() or not d.is_dir():
        return False, "옮길 수 없습니다."
    if p.is_dir() and d.resolve().is_relative_to(p.resolve()):
        return False, "폴더를 자기 안으로 옮길 수 없습니다."
    q = d / p.name
    if q.exists():
        return False, f"옮길 곳에 '{p.name}' 이(가) 이미 있습니다."
    shutil.move(str(p), str(q))
    storage.sync_docs(force=True)
    return True, f"'{p.name}' → {to_folder_rel or '(문서함)'}"


def all_folders() -> list[str]:
    """옮길 곳 선택용 — 문서함 안 모든 폴더의 상대 경로"""
    return [""] + sorted(rel(p) for p in root().rglob("*") if p.is_dir() and not p.name.startswith("."))
