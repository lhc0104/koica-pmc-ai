"""로그인 · 계정 · 권한 (v0.8)

· 계정은 accounts 표(pmc/0_공통/계정.csv)에 두고, 비밀번호는 PBKDF2-SHA256(20만 회, 계정마다 다른 salt) 해시로만 저장한다.
· 권한은 둘: 관리자(모든 수정·추가·삭제) / 일반(열람만). 수정 권한은 storage.permission_check 로 저장 계층에서도 막는다.
· 최상위 관리자는 표가 비어 있을 때 자동으로 만들어진다. ID/비밀번호는 환경변수 AIKME_ADMIN_ID / AIKME_ADMIN_PW 로 바꿀 수 있다
  (Streamlit Cloud 에서는 Secrets 에 넣으면 streamlit_app.py 가 환경변수로 옮겨 준다).
"""
import hashlib
import os
import re
import secrets
from datetime import datetime

from app import storage
from app.db import connect

TABLE = "accounts"
ROLES = ["관리자", "일반"]
ADMIN, VIEWER = ROLES
ITER = 200_000
DEFAULT_ADMIN_ID = "lhc0104"
# 기본 관리자 비밀번호의 해시 (평문은 코드에 두지 않는다). 첫 로그인 뒤 [내 계정]에서 바꾸는 것을 권한다.
DEFAULT_ADMIN_SALT = "7a939e6314d7681a1d9f31a9e6d5967f"
DEFAULT_ADMIN_HASH = "4e95b2e7b5ba6f2f39676623c2544dba208c5db7434502ad0bf66c02502f033f"


def _hash(pw: str, salt_hex: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), bytes.fromhex(salt_hex), ITER).hex()


def valid_id(login_id: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z0-9._-]{3,32}", login_id or ""))


def _rows(sql: str, params: tuple = ()) -> list[dict]:
    with connect(readonly=True) as con:
        return [dict(r) for r in con.execute(sql, params).fetchall()]


def ensure_admin() -> bool:
    """계정이 하나도 없으면 최상위 관리자를 만든다. 반환: 새로 만들었는지"""
    with connect() as con:
        if con.execute(f"SELECT 1 FROM {TABLE} LIMIT 1").fetchone():
            return False
        login_id = (os.getenv("AIKME_ADMIN_ID") or DEFAULT_ADMIN_ID).strip()
        pw = os.getenv("AIKME_ADMIN_PW")
        if pw:
            salt = secrets.token_hex(16)
            h = _hash(pw, salt)
        else:
            salt, h = DEFAULT_ADMIN_SALT, DEFAULT_ADMIN_HASH
        con.execute(f"INSERT INTO {TABLE}(login_id,name,role,salt,pw_hash,created_at,note) VALUES (?,?,?,?,?,?,?)",
                    (login_id, "최상위 관리자", ADMIN, salt, h, datetime.now().strftime("%Y-%m-%d %H:%M"), "자동 생성"))
        con.commit()
    storage.export_table(TABLE)
    return True


def verify(login_id: str, pw: str) -> dict | None:
    """맞으면 계정 dict(비밀번호 해시 제외), 아니면 None. 마지막 로그인 시각을 적는다"""
    login_id = (login_id or "").strip()
    rows = _rows(f"SELECT * FROM {TABLE} WHERE login_id = ?", (login_id,))
    if not rows or not pw:
        _hash(pw or "x", DEFAULT_ADMIN_SALT)              # 계정 유무와 상관없이 같은 시간이 걸리게
        return None
    r = rows[0]
    if not secrets.compare_digest(_hash(pw, r["salt"]), r["pw_hash"]):
        return None
    with connect() as con:
        con.execute(f"UPDATE {TABLE} SET last_login = ? WHERE login_id = ?", (datetime.now().strftime("%Y-%m-%d %H:%M"), login_id))
        con.commit()
    storage.export_table(TABLE)
    return {k: v for k, v in r.items() if k not in ("salt", "pw_hash")}


def list_accounts() -> list[dict]:
    return [{k: ("" if v is None else v) for k, v in r.items() if k not in ("salt", "pw_hash")}
            for r in _rows(f"SELECT * FROM {TABLE} ORDER BY role, login_id")]


def count_admins() -> int:
    return _rows(f"SELECT COUNT(*) AS n FROM {TABLE} WHERE role = ?", (ADMIN,))[0]["n"]


def create(login_id: str, name: str, pw: str, role: str, note: str = "") -> tuple[bool, str]:
    login_id = (login_id or "").strip()
    if not valid_id(login_id):
        return False, "ID는 영문·숫자·._- 로 3~32자여야 합니다."
    if len(pw or "") < 4:
        return False, "비밀번호는 4자 이상으로 정해 주세요."
    if role not in ROLES:
        return False, "권한은 관리자 또는 일반이어야 합니다."
    if _rows(f"SELECT 1 FROM {TABLE} WHERE lower(login_id) = lower(?)", (login_id,)):
        return False, f"'{login_id}' 계정이 이미 있습니다."
    salt = secrets.token_hex(16)
    with connect() as con:
        con.execute(f"INSERT INTO {TABLE}(login_id,name,role,salt,pw_hash,created_at,note) VALUES (?,?,?,?,?,?,?)",
                    (login_id, (name or "").strip(), role, salt, _hash(pw, salt), datetime.now().strftime("%Y-%m-%d %H:%M"), (note or "").strip()))
        con.commit()
    storage.export_table(TABLE)
    return True, f"'{login_id}' 계정을 만들었습니다 ({role})."


def set_password(login_id: str, pw: str, old_pw: str | None = None) -> tuple[bool, str]:
    """old_pw 를 주면(본인 변경) 현재 비밀번호를 확인한다. 관리자가 재설정할 때는 None"""
    if len(pw or "") < 4:
        return False, "새 비밀번호는 4자 이상으로 정해 주세요."
    rows = _rows(f"SELECT * FROM {TABLE} WHERE login_id = ?", (login_id,))
    if not rows:
        return False, "계정이 없습니다."
    if old_pw is not None and not secrets.compare_digest(_hash(old_pw, rows[0]["salt"]), rows[0]["pw_hash"]):
        return False, "현재 비밀번호가 맞지 않습니다."
    salt = secrets.token_hex(16)
    with connect() as con:
        con.execute(f"UPDATE {TABLE} SET salt = ?, pw_hash = ? WHERE login_id = ?", (salt, _hash(pw, salt), login_id))
        con.commit()
    storage.export_table(TABLE)
    return True, "비밀번호를 바꿨습니다."


def set_role(login_id: str, role: str, by: str) -> tuple[bool, str]:
    if role not in ROLES:
        return False, "권한 값이 잘못되었습니다."
    rows = _rows(f"SELECT role FROM {TABLE} WHERE login_id = ?", (login_id,))
    if not rows:
        return False, "계정이 없습니다."
    if rows[0]["role"] == ADMIN and role != ADMIN and count_admins() <= 1:
        return False, "마지막 관리자의 권한은 내릴 수 없습니다."
    if login_id == by and role != ADMIN:
        return False, "자기 자신의 관리자 권한은 내릴 수 없습니다."
    with connect() as con:
        con.execute(f"UPDATE {TABLE} SET role = ? WHERE login_id = ?", (role, login_id))
        con.commit()
    storage.export_table(TABLE)
    return True, f"'{login_id}' 권한을 {role}(으)로 바꿨습니다."


def set_name(login_id: str, name: str, note: str = "") -> tuple[bool, str]:
    with connect() as con:
        con.execute(f"UPDATE {TABLE} SET name = ?, note = ? WHERE login_id = ?", ((name or "").strip(), (note or "").strip(), login_id))
        con.commit()
    storage.export_table(TABLE)
    return True, "저장했습니다."


def delete(login_id: str, by: str) -> tuple[bool, str]:
    if login_id == by:
        return False, "로그인한 자기 계정은 지울 수 없습니다."
    rows = _rows(f"SELECT role FROM {TABLE} WHERE login_id = ?", (login_id,))
    if not rows:
        return False, "계정이 없습니다."
    if rows[0]["role"] == ADMIN and count_admins() <= 1:
        return False, "마지막 관리자는 지울 수 없습니다."
    with connect() as con:
        con.execute(f"DELETE FROM {TABLE} WHERE login_id = ?", (login_id,))
        con.commit()
    storage.export_table(TABLE)
    return True, f"'{login_id}' 계정을 지웠습니다."
