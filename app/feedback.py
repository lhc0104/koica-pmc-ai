"""[문제보고] 메모 — 본 DB의 issue_reports 테이블 + pmc/7_문제보고/문제보고.csv"""
from . import storage
from .db import connect

STATUSES = ["접수", "처리중", "완료"]


def add(author: str, menu: str, kind: str, content: str) -> None:
    with connect() as con:
        con.execute("INSERT INTO issue_reports(author,menu,kind,content) VALUES (?,?,?,?)", (author, menu, kind, content))
    storage.export_table("issue_reports")


def all_reports() -> list[dict]:
    with connect(readonly=True) as con:
        return [dict(r) for r in con.execute("SELECT * FROM issue_reports ORDER BY id DESC")]


def set_status(rid: int, status: str) -> None:
    with connect() as con:
        con.execute("UPDATE issue_reports SET status=? WHERE id=?", (status, rid))
    storage.export_table("issue_reports")
