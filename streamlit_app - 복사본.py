import streamlit as st
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# Google Drive 초기화를 위한 임포트
try:
    from app.drive_sync import get_drive_sync
    drive_sync = get_drive_sync()
    st.sidebar.success("✅ Google Drive 연결됨")
except Exception as e:
    st.sidebar.warning(f"⚠️ Google Drive 연결 실패: {str(e)}")

# app/ui.py 실행
import app.ui