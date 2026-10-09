"""Streamlit Community Cloud 진입점 (app/ui.py 를 그대로 실행)

· Cloud 에는 .env 가 없으므로 Secrets(설정 › Secrets)에 적은 값을 환경변수로 옮긴다:
    ANTHROPIC_API_KEY, AIKME_ADMIN_ID, AIKME_ADMIN_PW, GOOGLE_SERVICE_ACCOUNT_JSON, GOOGLE_DRIVE_FOLDER_ID, PMC_PDF_FONT
· Cloud 의 파일 시스템은 다시 배포될 때 초기화된다 — 저장소(git)에 들어 있는 pmc/ 내용으로 되돌아간다.
"""
import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()
try:
    for k, v in st.secrets.items():               # secrets.toml 이 없으면 StreamlitSecretNotFoundError
        if isinstance(v, (str, int, float)) and k not in os.environ:
            os.environ[k] = str(v)
except Exception:
    pass

exec(compile((Path(__file__).parent / "app" / "ui.py").read_text(encoding="utf-8"), "app/ui.py", "exec"))
