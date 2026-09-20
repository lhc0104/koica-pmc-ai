"""문서에서 글자 뽑기 — .md/.txt/.hwpx/.docx/.pdf  (추가 설치 없이 동작, PDF만 pypdf 사용)
그림으로만 된 PDF(스캔본·이미지 저장본)는 글자가 없어 색인되지 않는다 → 빈 문자열 반환."""
import re
import zipfile
from html import unescape
from pathlib import Path


def _xml_text(xml: str, para_tag: str, text_tag: str) -> str:
    out = []
    for para in re.split(rf"</{para_tag}>", xml):
        t = "".join(re.findall(rf"<{text_tag}(?:\s[^>]*)?>([^<]*)</{text_tag}>", para))
        t = unescape(t).strip()
        if t:
            out.append(t)
    return "\n".join(out)


def read_text(path: Path) -> str:
    ext = path.suffix.lower()
    try:
        if ext in (".md", ".txt"):
            try:
                return path.read_text(encoding="utf-8-sig")
            except UnicodeDecodeError:
                return path.read_text(encoding="cp949", errors="replace")
        if ext == ".hwpx":                                  # 한글(HWPX) = zip + XML
            with zipfile.ZipFile(path) as z:
                names = sorted(n for n in z.namelist() if re.fullmatch(r"Contents/section\d+\.xml", n))
                return "\n".join(_xml_text(z.read(n).decode("utf-8", "replace"), "hp:p", "hp:t") for n in names)
        if ext == ".docx":
            with zipfile.ZipFile(path) as z:
                return _xml_text(z.read("word/document.xml").decode("utf-8", "replace"), "w:p", "w:t")
        if ext == ".pdf":
            from pypdf import PdfReader
            return "\n".join((pg.extract_text() or "") for pg in PdfReader(str(path)).pages)
    except Exception as e:  # 깨진 파일·암호 걸린 파일 등은 건너뛴다
        return f"__ERROR__ {e}"
    return ""
