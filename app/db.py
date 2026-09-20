"""DB 연결·설정·경로 공통 모듈"""
import os
import sqlite3
from pathlib import Path
import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def settings() -> dict:
    return yaml.safe_load((ROOT / "config" / "settings.yaml").read_text(encoding="utf-8"))


def db_path() -> Path:
    """검색·집계용 SQLite(로컬 캐시). 원본 데이터는 data_dir()의 파일들이다."""
    p = Path(settings()["project"]["db_path"])
    return p if p.is_absolute() else ROOT / p


def data_dir() -> Path:
    """목차별 데이터 저장 폴더(기본: 프로젝트 안의 pmc).
    클라우드 동기화 폴더로 옮기려면 .env 의 PMC_DATA_DIR 또는 settings.yaml 의 project.data_dir 에 경로를 적는다."""
    p = Path(os.getenv("PMC_DATA_DIR") or settings()["project"].get("data_dir", "pmc"))
    return p if p.is_absolute() else ROOT / p


def connect(readonly: bool = False) -> sqlite3.Connection:
    if readonly:  # LLM이 실행하는 SQL은 읽기 전용 연결로만
        con = sqlite3.connect(f"file:{db_path()}?mode=ro", uri=True)
    else:
        db_path().parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(db_path())
    con.row_factory = sqlite3.Row
    return con


def schema_text() -> str:
    return (ROOT / "db" / "schema.sql").read_text(encoding="utf-8")
