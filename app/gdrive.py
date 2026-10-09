"""6. 문서관리 › Google 드라이브 — 드라이브 전체를 둘러보고, 사업 문서함과 파일을 주고받기 (v0.7)

연결 방법 두 가지 (둘 다 없으면 화면에 안내만 보인다)
  1. 내 Google 계정으로 로그인 (PC에서 쓸 때 권장 — 내 드라이브·공유 문서함 전체가 보인다)
     config/google_oauth_client.json  ← Google Cloud Console › API 및 서비스 › 사용자 인증 정보 › OAuth 클라이언트(데스크톱 앱) JSON
     [Google 계정으로 연결] 을 누르면 브라우저가 열리고, 로그인하면 data/google_token.json 에 토큰이 저장된다.
  2. 서비스 계정 (Streamlit Cloud 등 서버에서 쓸 때)
     .env 의 GOOGLE_SERVICE_ACCOUNT_JSON(파일 경로 또는 JSON 문자열) + GOOGLE_DRIVE_FOLDER_ID
     서비스 계정은 '공유받은 폴더'만 보이므로, 사업 폴더를 서비스 계정 이메일에 공유해 두어야 한다.

이 파일의 함수는 모두 googleapiclient 를 늦게 불러오므로 패키지가 없어도 앱은 뜬다.
"""
import io
import json
import os
from pathlib import Path

from app import storage
from app.db import ROOT

SCOPES = ["https://www.googleapis.com/auth/drive"]
OAUTH_CLIENT = ROOT / "config" / "google_oauth_client.json"
TOKEN_FILE = ROOT / "data" / "google_token.json"
FOLDER_MIME = "application/vnd.google-apps.folder"
EXPORT = {  # Google 문서 형식 → 내려받을 때 바꿀 형식
    "application/vnd.google-apps.document": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", ".docx"),
    "application/vnd.google-apps.spreadsheet": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", ".xlsx"),
    "application/vnd.google-apps.presentation": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", ".pptx"),
    "application/vnd.google-apps.drawing": ("image/png", ".png"),
}
KIND = {"application/vnd.google-apps.folder": "폴더", "application/vnd.google-apps.document": "Google 문서", "application/vnd.google-apps.spreadsheet": "Google 시트",
        "application/vnd.google-apps.presentation": "Google 슬라이드", "application/pdf": "PDF", "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "Word",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "Excel", "application/vnd.openxmlformats-officedocument.presentationml.presentation": "PPT",
        "application/x-hwp": "한글", "application/haansofthwp": "한글", "application/vnd.hancom.hwpx": "한글", "image/jpeg": "사진", "image/png": "사진", "text/plain": "텍스트",
        "text/csv": "CSV", "application/zip": "압축", "video/mp4": "영상", "audio/mpeg": "음성"}
FIELDS = "id,name,mimeType,size,modifiedTime,webViewLink,iconLink,parents,owners(displayName,emailAddress),shared"
_service = None
_mode = None


# ───────────────────────── 연결 ─────────────────────────
def available() -> bool:
    try:
        import googleapiclient  # noqa: F401
        import google.oauth2  # noqa: F401
        return True
    except ImportError:
        return False


def project_folder_id() -> str:
    return (os.getenv("GOOGLE_DRIVE_FOLDER_ID") or "").strip()


def _service_account_info() -> dict | None:
    raw = (os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON") or "").strip()
    if not raw:
        return None
    try:
        if os.path.isfile(raw):
            return json.loads(Path(raw).read_text(encoding="utf-8"))
        return json.loads(raw)
    except (OSError, ValueError):
        return None


def _oauth_creds(interactive: bool = False):
    """저장된 토큰이 있으면 그걸로, 없고 interactive 면 브라우저 로그인"""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    creds = None
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except ValueError:
            creds = None
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        except Exception:
            creds = None
    if (not creds or not creds.valid) and interactive and OAUTH_CLIENT.exists():
        from google_auth_oauthlib.flow import InstalledAppFlow
        flow = InstalledAppFlow.from_client_secrets_file(str(OAUTH_CLIENT), SCOPES)
        creds = flow.run_local_server(port=0, open_browser=True, authorization_prompt_message="")
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return creds if creds and creds.valid else None


def connect(interactive: bool = False):
    """(service, mode) — mode: 'oauth' | 'service' | None.  한 번 만든 service 는 재사용"""
    global _service, _mode
    if _service is not None:
        return _service, _mode
    if not available():
        return None, None
    from googleapiclient.discovery import build
    creds = None
    try:
        creds = _oauth_creds(interactive)
        mode = "oauth" if creds else None
    except Exception:
        creds, mode = None, None
    if creds is None:
        info = _service_account_info()
        if info:
            from google.oauth2.service_account import Credentials
            try:
                creds, mode = Credentials.from_service_account_info(info, scopes=SCOPES), "service"
            except Exception:
                creds, mode = None, None
    if creds is None:
        return None, None
    _service, _mode = build("drive", "v3", credentials=creds, cache_discovery=False), mode
    return _service, _mode


def disconnect() -> None:
    global _service, _mode
    _service = _mode = None
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()


def status() -> dict:
    """화면 상태 카드용 — 절대 예외를 내지 않는다"""
    s = {"installed": available(), "oauth_client": OAUTH_CLIENT.exists(), "token": TOKEN_FILE.exists(),
         "service_account": _service_account_info() is not None, "project_folder": project_folder_id(), "connected": False, "mode": None,
         "user": "", "email": "", "error": ""}
    if not s["installed"]:
        s["error"] = "google-api-python-client 패키지가 없습니다. AI_ME_v1.bat 을 다시 실행하면 설치됩니다."
        return s
    try:
        svc, mode = connect(False)
        if svc is None:
            return s
        about = svc.about().get(fields="user(displayName,emailAddress)").execute()
        s.update(connected=True, mode=mode, user=about.get("user", {}).get("displayName", ""), email=about.get("user", {}).get("emailAddress", ""))
    except Exception as e:
        s["error"] = f"연결 확인 중 오류: {e}"
    return s


# ───────────────────────── 둘러보기 ─────────────────────────
def _norm(f: dict) -> dict:
    mt = f.get("mimeType", "")
    return {"id": f.get("id"), "name": f.get("name", ""), "mime": mt, "is_folder": mt == FOLDER_MIME,
            "kind": KIND.get(mt, "Google 파일" if mt.startswith("application/vnd.google-apps") else (mt.split("/")[-1].upper()[:8] if mt else "파일")),
            "size": int(f.get("size") or 0), "modified": (f.get("modifiedTime") or "")[:16].replace("T", " "), "link": f.get("webViewLink", ""),
            "owner": (f.get("owners") or [{}])[0].get("displayName", ""), "parents": f.get("parents") or [], "shared": f.get("shared", False)}


def _list(q: str, order: str = "folder,name", page_size: int = 200, drive_id: str | None = None) -> list[dict]:
    svc, _ = connect()
    if svc is None:
        return []
    kw = {"q": q, "fields": f"nextPageToken, files({FIELDS})", "pageSize": page_size, "orderBy": order, "supportsAllDrives": True, "includeItemsFromAllDrives": True}
    if drive_id:
        kw.update(corpora="drive", driveId=drive_id)
    out, token = [], None
    while True:
        res = svc.files().list(pageToken=token, **kw).execute()
        out += [_norm(f) for f in res.get("files", [])]
        token = res.get("nextPageToken")
        if not token or len(out) >= 600:
            break
    return out


def children(folder_id: str) -> list[dict]:
    """폴더 안 항목 — 폴더 먼저, 이름순"""
    items = _list(f"'{folder_id}' in parents and trashed=false")
    return sorted(items, key=lambda x: (not x["is_folder"], x["name"].lower()))


def recent(n: int = 30) -> list[dict]:
    return _list("trashed=false and mimeType!='application/vnd.google-apps.folder'", order="modifiedTime desc", page_size=n)[:n]


def shared_with_me(n: int = 100) -> list[dict]:
    return _list("sharedWithMe=true and trashed=false", order="modifiedTime desc", page_size=n)[:n]


def search(text: str, n: int = 100) -> list[dict]:
    t = (text or "").replace("\\", "\\\\").replace("'", "\\'").strip()
    if not t:
        return []
    return _list(f"name contains '{t}' and trashed=false", order="modifiedTime desc", page_size=n)[:n]


def shared_drives() -> list[dict]:
    svc, _ = connect()
    if svc is None:
        return []
    try:
        res = svc.drives().list(pageSize=100, fields="drives(id,name)").execute()
        return [{"id": d["id"], "name": d["name"]} for d in res.get("drives", [])]
    except Exception:
        return []


def get(file_id: str) -> dict | None:
    svc, _ = connect()
    if svc is None:
        return None
    try:
        return _norm(svc.files().get(fileId=file_id, fields=FIELDS, supportsAllDrives=True).execute())
    except Exception:
        return None


def breadcrumb(folder_id: str, stop_ids: set[str] | None = None, limit: int = 8) -> list[dict]:
    """[{id,name}] 루트→현재.  'root' 는 내 드라이브"""
    out, cur, stop = [], folder_id, set(stop_ids or ())
    while cur and len(out) < limit:
        if cur == "root":
            out.append({"id": "root", "name": "내 드라이브"})
            break
        f = get(cur)
        if not f:
            break
        out.append({"id": f["id"], "name": f["name"]})
        if cur in stop or not f["parents"]:
            break
        cur = f["parents"][0]
    return list(reversed(out))


# ───────────────────────── 주고받기 ─────────────────────────
def download(file: dict) -> tuple[str, bytes]:
    """(파일 이름, 내용) — Google 문서는 Word/Excel/PPT 로 바꿔 받는다"""
    from googleapiclient.http import MediaIoBaseDownload
    svc, _ = connect()
    if svc is None:
        raise RuntimeError("Google 드라이브에 연결되어 있지 않습니다.")
    name, mime = file["name"], file["mime"]
    if mime in EXPORT:
        exp_mime, ext = EXPORT[mime]
        req = svc.files().export_media(fileId=file["id"], mimeType=exp_mime)
        if not name.lower().endswith(ext):
            name += ext
    elif mime.startswith("application/vnd.google-apps"):
        req = svc.files().export_media(fileId=file["id"], mimeType="application/pdf")
        name += ".pdf"
    else:
        req = svc.files().get_media(fileId=file["id"], supportsAllDrives=True)
    buf = io.BytesIO()
    dl = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        _, done = dl.next_chunk()
    return name, buf.getvalue()


def upload(folder_id: str, name: str, data: bytes, mime: str = "application/octet-stream") -> dict:
    storage.check_edit()
    from googleapiclient.http import MediaIoBaseUpload
    svc, _ = connect()
    if svc is None:
        raise RuntimeError("Google 드라이브에 연결되어 있지 않습니다.")
    media = MediaIoBaseUpload(io.BytesIO(data), mimetype=mime or "application/octet-stream", resumable=len(data) > 5 * 1024 * 1024)
    body = {"name": name, "parents": [folder_id]} if folder_id and folder_id != "root" else {"name": name}
    return _norm(svc.files().create(body=body, media_body=media, fields=FIELDS, supportsAllDrives=True).execute())


def make_folder(parent_id: str, name: str) -> dict:
    storage.check_edit()
    svc, _ = connect()
    if svc is None:
        raise RuntimeError("Google 드라이브에 연결되어 있지 않습니다.")
    body = {"name": name, "mimeType": FOLDER_MIME}
    if parent_id and parent_id != "root":
        body["parents"] = [parent_id]
    return _norm(svc.files().create(body=body, fields=FIELDS, supportsAllDrives=True).execute())


def fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}GB"
