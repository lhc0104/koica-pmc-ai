"""문서 검색 — 1단계: 키워드 점수 방식(한국어 부분일치). 2단계에서 벡터 검색으로 교체·병행."""
import re
from .db import connect, settings


def search_documents(query: str, doc_type: str | None = None, top_k: int | None = None) -> list[dict]:
    top_k = top_k or settings()["search"]["top_k"]
    terms = [t for t in re.split(r"[\s,·/()]+", query) if len(t) >= 2]
    if not terms:
        return []
    sql = ("SELECT c.chunk_id, c.heading, c.content, d.doc_id, d.title, d.doc_type, d.doc_date "
           "FROM doc_chunks c JOIN documents d USING(doc_id)")
    args: list = []
    if doc_type:
        sql += " WHERE d.doc_type = ?"
        args.append(doc_type)
    scored = []
    with connect(readonly=True) as con:
        for r in con.execute(sql, args):
            text = f"{r['title']} {r['heading'] or ''} {r['content']}".lower()
            score = sum(text.count(t.lower()) for t in terms)
            if score:
                scored.append((score, dict(r)))
    scored.sort(key=lambda x: -x[0])
    return [{"score": s, **r} for s, r in scored[:top_k]]
