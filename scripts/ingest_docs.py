"""문서 색인: pmc/4_사업관리/문서 + pmc/99*(참고자료, 하위폴더 포함)의 .md .txt .hwpx .docx .pdf
사용: python scripts/ingest_docs.py"""
import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import yaml
from app import storage
from app.db import connect, data_dir, settings
from app.extract import read_text


def _chunks(body: str, size: int):
    """제목(#, Ⅰ., 1., 가. 등) 앞에서 끊고, 길면 size 글자 단위로 다시 자름"""
    heading, buf, n = "", [], 0
    head = re.compile(r"^(#{1,4} |[ⅠⅡⅢⅣⅤ]+[.\s]|\d{1,2}\\?\. |[가-하]\. |ㅇ ?\(활동|\[별지|\[붙임)")

    def flush():
        text = "\n".join(buf).strip()
        for i in range(0, len(text), size):
            yield heading, text[i:i + size]
    for line in body.splitlines():
        if head.match(line.strip()) and n > size // 2:
            yield from flush()
            heading, buf, n = line.strip().lstrip("# ")[:80], [], 0
        elif head.match(line.strip()) and not buf:
            heading = line.strip().lstrip("# ")[:80]
        buf.append(line)
        n += len(line)
    yield from flush()


def _doc_type(f: Path) -> str:
    p = str(f).upper()
    return "기준문서" if any(k in p for k in ("RFP", "PDM", "POD", "제안요청", "R_D", "R&D")) else "회의록" if "회의" in p else "기타"


def ingest_all() -> int:
    size = settings()["search"]["chunk_chars"]
    n, skipped = 0, []
    with connect() as con:
        con.execute("DELETE FROM doc_chunks")           # 폴더가 원본: 지워진 파일은 색인에서도 빠진다
        con.execute("DELETE FROM documents")
        for f in storage.doc_files():
            raw = read_text(f)
            if raw.startswith("__ERROR__") or len(raw.strip()) < 30:
                skipped.append(f.name)
                continue
            meta, body = {}, raw
            m = re.match(r"(?s)^---\r?\n(.*?)\r?\n---\r?\n(.*)$", raw)
            if m:
                meta, body = yaml.safe_load(m.group(1)) or {}, m.group(2)
            relp = f.relative_to(data_dir()).as_posix()
            doc_id = str(meta.get("doc_id") or re.sub(r"[^0-9A-Za-z가-힣]+", "_", f.stem)[:40])
            con.execute("INSERT OR REPLACE INTO documents(doc_id,title,doc_type,language,doc_date,source_org,file_path) VALUES (?,?,?,?,?,?,?)",
                        (doc_id, meta.get("title", f.stem), meta.get("doc_type", _doc_type(f)), meta.get("language", "ko"),
                         str(meta.get("doc_date", "")), meta.get("source_org", ""), relp))
            for seq, (h, c) in enumerate(_chunks(body, size)):
                con.execute("INSERT INTO doc_chunks(doc_id,seq,heading,content) VALUES (?,?,?,?)", (doc_id, seq, h, c))
            n += 1
    ingest_all.skipped = skipped
    return n


ingest_all.skipped = []

if __name__ == "__main__":
    storage.bootstrap()
    print(f"문서 {storage.sync_docs(force=True)}건 색인 완료")
    for r in storage.doc_roots():
        print("  대상 폴더:", r)
    if ingest_all.skipped:
        print("  글자를 읽지 못해 건너뜀(그림 PDF 등):", ", ".join(ingest_all.skipped))
