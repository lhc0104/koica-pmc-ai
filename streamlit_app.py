import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()

# Google Drive 연결 초기화
try:
    from app.drive_sync import get_drive_sync
    drive_sync = get_drive_sync()
    st.sidebar.success("✅ Google Drive 연결됨")
except Exception as e:
    st.sidebar.warning(f"⚠️ Google Drive 연결 실패: {str(e)}")

# Streamlit이 app/ui.py를 직접 실행하도록 설정
# (아래 한 줄만 있으면 됨)
exec(open("app/ui.py").read())