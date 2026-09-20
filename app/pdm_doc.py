"""사업논리모형(PDM) 한 버전 → Excel(.xlsx) / Word(.docx) / PDF 파일 (v0.5)

· 화면의 [5. 성과관리 › 사업산출물 › 사업논리모형(PDM)]에서 선택한 버전(기본: 최종 버전)을 PDM 원문 양식으로 내려받는다.
· Excel: 'PDM' 시트(양식 표) + '버전이력' + '근거자료' 시트.  Word/PDF: 가로(A4 landscape) 표.
"""
import html
import io
from datetime import datetime

from .minutes_doc import PROJECT, _pdf_fonts, _s

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
HEAD = [("Narrative Summary\n(요약)", "summary"), ("Objectively Verifiable Indicators\n(객관적 검증지표)", "indicators"),
        ("Means of Verification\n(검증수단)", "mov"), ("Important Assumptions\n(중요가정)", "assumptions"), ("검증지표 추가제안", "proposal")]
SECTIONS = [("영향(Impact)", "Impacts (영향)"), ("성과(Outcome)", "Outcomes (성과)"), ("산출물(Output)", "Outputs (산출물)")]


def _groups(rows: list[dict]) -> dict:
    g = {"info": [], "act": [], "inp": [], "pre": []}
    for r in rows:
        lv = _s(r.get("level"))
        if lv == "기본정보":
            g["info"].append(r)
        elif lv.startswith("활동"):
            g["act"].append(r)
        elif lv.startswith("투입물"):
            g["inp"].append(r)
        elif lv.startswith("선행조건"):
            g["pre"].append(r)
    return g


def _summary_cell(r: dict) -> str:
    code = _s(r.get("code"))
    return (f"{code}. " if code else "") + _s(r.get("summary"))


def file_stem(version: int, meta: dict) -> str:
    return f"사업논리모형_PDM_v{version}_{_s(meta.get('status')) or '초안'}"


# ───────────────────────── Excel ─────────────────────────
def build_xlsx(version: int, rows: list[dict], meta: dict, versions: list[dict], evidence: list[dict]) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws = wb.active
    ws.title = f"PDM v{version}"
    thin = Side(style="thin", color="B8C2D3")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    wrap = Alignment(wrap_text=True, vertical="top")
    head_fill, sec_fill, prop_fill, key_fill = PatternFill("solid", fgColor="1F4E9C"), PatternFill("solid", fgColor="EEF2F9"), PatternFill("solid", fgColor="FFFBEB"), PatternFill("solid", fgColor="F3F6FB")
    bold = Font(name="맑은 고딕", bold=True, size=10)
    normal = Font(name="맑은 고딕", size=10)
    g = _groups(rows)

    ws["A1"] = "PDM (Project Design Matrix)"
    ws["A1"].font = Font(name="맑은 고딕", bold=True, size=14, color="1F4E9C")
    ws.merge_cells("A1:E1")
    r = 2
    info = [(_s(x.get("code")), _s(x.get("summary")) + (f"  ({_s(x.get('note'))})" if _s(x.get("note")) else "")) for x in g["info"]]
    info += [("버전", f"v{version} · {_s(meta.get('status')) or '초안'}"), ("생성일 / 작성자", f"{_s(meta.get('created_at'))} / {_s(meta.get('author'))}"),
             ("승인일", _s(meta.get("approved_at"))), ("변경 사유", _s(meta.get("reason")))]
    for k, v in info:
        ws.cell(r, 1, k).font = bold
        ws.cell(r, 1).fill = key_fill
        ws.cell(r, 2, v).font = normal
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=5)
        for c in range(1, 6):
            ws.cell(r, c).border = border
            ws.cell(r, c).alignment = wrap
        r += 1
    r += 1
    for c, (h, _) in enumerate(HEAD, 1):
        cell = ws.cell(r, c, h)
        cell.font = Font(name="맑은 고딕", bold=True, size=10, color="FFFFFF")
        cell.fill = head_fill
        cell.alignment = Alignment(wrap_text=True, horizontal="center", vertical="center")
        cell.border = border
    ws.row_dimensions[r].height = 34
    r += 1
    for lv, title in SECTIONS:
        sec = [x for x in rows if _s(x.get("level")) == lv]
        if not sec:
            continue
        ws.cell(r, 1, title).font = Font(name="맑은 고딕", bold=True, size=10, color="1F4E9C")
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
        for c in range(1, 6):
            ws.cell(r, c).fill = sec_fill
            ws.cell(r, c).border = border
        r += 1
        for x in sec:
            vals = [_summary_cell(x), _s(x.get("indicators")), _s(x.get("mov")), _s(x.get("assumptions")), _s(x.get("proposal"))]
            for c, v in enumerate(vals, 1):
                cell = ws.cell(r, c, v)
                cell.font = normal
                cell.alignment = wrap
                cell.border = border
                if c == 5:
                    cell.fill = prop_fill
            lines = max(max(len(v.splitlines()) or 1, len(v) // 28 + 1) for v in vals)
            ws.row_dimensions[r].height = min(15 * lines + 6, 300)
            r += 1
    if g["act"] or g["inp"] or g["pre"]:
        for c, h in enumerate(["Activities (활동)", "Inputs (투입물)", "", "Pre-conditions (선행조건)", "검증지표 추가제안"], 1):
            cell = ws.cell(r, c, h)
            cell.font = Font(name="맑은 고딕", bold=True, size=10, color="1F4E9C")
            cell.fill = sec_fill
            cell.border = border
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=3)
        r += 1
        a = "\n".join(_summary_cell(x) for x in g["act"])
        i = "\n".join(f"[{_s(x.get('code'))}]\n{_s(x.get('summary'))}" for x in g["inp"])
        pr = "\n".join(_s(x.get("summary")) for x in g["pre"])
        pp = "\n".join(_s(x.get("proposal")) for x in g["act"] + g["inp"] + g["pre"] if _s(x.get("proposal")))
        for c, v in ((1, a), (2, i), (4, pr), (5, pp)):
            cell = ws.cell(r, c, v)
            cell.font = normal
            cell.alignment = wrap
        for c in range(1, 6):
            ws.cell(r, c).border = border
        ws.cell(r, 5).fill = prop_fill
        ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=3)
        ws.row_dimensions[r].height = min(15 * max(len(a.splitlines()), len(i.splitlines()), len(pr.splitlines()), 1) + 6, 400)
        r += 2
    ws.cell(r, 1, f"출력 {datetime.now():%Y-%m-%d %H:%M} · KOICA AI 성과관리 · {PROJECT}").font = Font(name="맑은 고딕", size=8, color="8A97A8")
    for c, w in zip("ABCDE", (38, 40, 26, 34, 30)):
        ws.column_dimensions[c].width = w
    ws.freeze_panes = None
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True

    ws2 = wb.create_sheet("원본표(편집용)")                  # 화면 편집표와 같은 열 — 다시 불러오기 쉽게
    cols = ["seq", "level", "code", "summary", "indicators", "mov", "assumptions", "proposal", "note"]
    labels = ["순서", "구분", "코드/항목", "요약", "객관적 검증지표", "검증수단", "중요가정", "검증지표 추가제안", "비고"]
    for c, h in enumerate(labels, 1):
        cell = ws2.cell(1, c, h)
        cell.font = Font(name="맑은 고딕", bold=True, size=10, color="FFFFFF")
        cell.fill = head_fill
        cell.border = border
    for rr, x in enumerate(rows, 2):
        for c, k in enumerate(cols, 1):
            v = x.get(k)
            cell = ws2.cell(rr, c, "" if v is None else v)
            cell.font = normal
            cell.alignment = wrap
            cell.border = border
    for c, w in zip(range(1, 10), (7, 16, 14, 40, 40, 26, 34, 30, 20)):
        ws2.column_dimensions[get_column_letter(c)].width = w

    ws3 = wb.create_sheet("버전이력")
    for c, h in enumerate(["버전", "생성일", "작성자", "변경 사유", "상태", "승인일", "비고"], 1):
        cell = ws3.cell(1, c, h)
        cell.font = Font(name="맑은 고딕", bold=True, size=10, color="FFFFFF")
        cell.fill = head_fill
    for rr, v in enumerate(versions, 2):
        for c, k in enumerate(["version", "created_at", "author", "reason", "status", "approved_at", "note"], 1):
            ws3.cell(rr, c, v.get(k, "")).font = normal
    for c, w in zip("ABCDEFG", (7, 12, 16, 50, 9, 12, 20)):
        ws3.column_dimensions[c].width = w

    ws4 = wb.create_sheet("근거자료")
    for c, h in enumerate(["버전", "파일명", "설명", "올린 날짜", "저장 위치"], 1):
        cell = ws4.cell(1, c, h)
        cell.font = Font(name="맑은 고딕", bold=True, size=10, color="FFFFFF")
        cell.fill = head_fill
    for rr, e in enumerate(evidence, 2):
        for c, k in enumerate(["version", "file_name", "note", "uploaded_at", "file_path"], 1):
            ws4.cell(rr, c, e.get(k, "")).font = normal
    for c, w in zip("ABCDE", (7, 36, 40, 17, 50)):
        ws4.column_dimensions[c].width = w

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ───────────────────────── Word ─────────────────────────
def build_docx(version: int, rows: list[dict], meta: dict) -> bytes:
    from docx import Document
    from docx.enum.section import WD_ORIENT
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Cm, Pt, RGBColor

    doc = Document()
    sec = doc.sections[0]
    sec.orientation = WD_ORIENT.LANDSCAPE
    sec.page_width, sec.page_height = Cm(29.7), Cm(21.0)
    sec.left_margin = sec.right_margin = Cm(1.6)
    sec.top_margin = sec.bottom_margin = Cm(1.5)
    st = doc.styles["Normal"]
    st.font.name, st.font.size = "맑은 고딕", Pt(9)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "맑은 고딕")

    def _font(run, size=None, bold=None, color=None):
        run.font.name = "맑은 고딕"
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "맑은 고딕")
        if size:
            run.font.size = Pt(size)
        if bold is not None:
            run.font.bold = bold
        if color:
            run.font.color.rgb = RGBColor.from_string(color)

    def _shade(cell, hex_color):
        tcPr = cell._element.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hex_color)
        tcPr.append(shd)

    def _text(cell, text, size=9, bold=False, color=None):
        lines = (text or "").splitlines() or [""]
        p0 = cell.paragraphs[0]
        p0.paragraph_format.space_before = p0.paragraph_format.space_after = Pt(2)
        _font(p0.add_run(lines[0]), size, bold, color)
        for ln in lines[1:]:
            p = cell.add_paragraph()
            p.paragraph_format.space_after = Pt(2)
            _font(p.add_run(ln if ln.strip() else " "), size, bold, color)

    p = doc.add_paragraph()
    _font(p.add_run(PROJECT), 8.5, color="5B6675")
    h = doc.add_paragraph()
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _font(h.add_run("PDM (Project Design Matrix)"), 16, True, "1F4E9C")
    g = _groups(rows)
    info = [(_s(x.get("code")), _s(x.get("summary"))) for x in g["info"]]
    info += [("버전", f"v{version} · {_s(meta.get('status')) or '초안'}"), ("생성일 / 작성자", f"{_s(meta.get('created_at'))} / {_s(meta.get('author'))}"),
             ("승인일", _s(meta.get("approved_at"))), ("변경 사유", _s(meta.get("reason")))]
    it = doc.add_table(rows=0, cols=4)
    it.style, it.alignment = "Table Grid", WD_TABLE_ALIGNMENT.CENTER
    for i in range(0, len(info), 2):
        cells = it.add_row().cells
        for j, (k, v) in enumerate(info[i:i + 2]):
            _shade(cells[j * 2], "F3F6FB")
            _text(cells[j * 2], k, 9, True)
            _text(cells[j * 2 + 1], v, 9)
    for row in it.rows:
        for c, w in zip(row.cells, (3.6, 9.6, 3.6, 9.6)):
            c.width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)

    t = doc.add_table(rows=1, cols=5)
    t.style, t.alignment = "Table Grid", WD_TABLE_ALIGNMENT.CENTER
    for c, (hd, _) in zip(t.rows[0].cells, HEAD):
        _shade(c, "1F4E9C")
        _text(c, hd, 9, True, "FFFFFF")
        c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for lv, title in SECTIONS:
        secr = [x for x in rows if _s(x.get("level")) == lv]
        if not secr:
            continue
        cells = t.add_row().cells
        m = cells[0].merge(cells[4])
        _shade(m, "EEF2F9")
        _text(m, title, 9, True, "1F4E9C")
        for x in secr:
            cells = t.add_row().cells
            vals = [_summary_cell(x), _s(x.get("indicators")), _s(x.get("mov")), _s(x.get("assumptions")), _s(x.get("proposal"))]
            for c, v in zip(cells, vals):
                _text(c, v, 9)
            _shade(cells[4], "FFFBEB")
    if g["act"] or g["inp"] or g["pre"]:
        cells = t.add_row().cells
        heads = ["Activities (활동)", "Inputs (투입물)", "", "Pre-conditions (선행조건)", "검증지표 추가제안"]
        for c, hd in zip(cells, heads):
            _shade(c, "EEF2F9")
            _text(c, hd, 9, True, "1F4E9C")
        cells[1].merge(cells[2])
        cells = t.add_row().cells
        _text(cells[0], "\n".join(_summary_cell(x) for x in g["act"]), 9)
        _text(cells[1], "\n".join(f"[{_s(x.get('code'))}]\n{_s(x.get('summary'))}" for x in g["inp"]), 9)
        _text(cells[3], "\n".join(_s(x.get("summary")) for x in g["pre"]), 9)
        _text(cells[4], "\n".join(_s(x.get("proposal")) for x in g["act"] + g["inp"] + g["pre"] if _s(x.get("proposal"))), 9)
        _shade(cells[4], "FFFBEB")
        cells[1].merge(cells[2])
    for row in t.rows:
        for c, w in zip(row.cells, (6.6, 6.6, 4.4, 5.0, 4.0)):
            c.width = Cm(w)
    f = doc.add_paragraph()
    f.paragraph_format.space_before = Pt(10)
    _font(f.add_run(f"PDM v{version} · 출력 {datetime.now():%Y-%m-%d %H:%M} · KOICA AI 성과관리"), 8, color="8A97A8")
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ───────────────────────── PDF ─────────────────────────
def _para(text: str) -> str:
    return html.escape(text or "").replace("\n", "<br/>")


def build_pdf(version: int, rows: list[dict], meta: dict) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    reg, bold = _pdf_fonts()
    S = {"proj": ParagraphStyle("proj", fontName=reg, fontSize=8, textColor=colors.HexColor("#5B6675"), leading=11),
         "title": ParagraphStyle("title", fontName=bold, fontSize=16, textColor=colors.HexColor("#1F4E9C"), alignment=1, leading=22, spaceAfter=6),
         "h": ParagraphStyle("h", fontName=bold, fontSize=8.5, textColor=colors.white, alignment=1, leading=11),
         "sec": ParagraphStyle("sec", fontName=bold, fontSize=8.5, textColor=colors.HexColor("#1F4E9C"), leading=11),
         "k": ParagraphStyle("k", fontName=bold, fontSize=8.5, leading=11),
         "v": ParagraphStyle("v", fontName=reg, fontSize=8.5, leading=12),
         "foot": ParagraphStyle("foot", fontName=reg, fontSize=7.5, textColor=colors.HexColor("#8A97A8"), leading=10, spaceBefore=8)}
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=14 * mm, rightMargin=14 * mm, topMargin=12 * mm, bottomMargin=12 * mm,
                            title=f"PDM v{version}", author="KOICA AI 성과관리")
    g = _groups(rows)
    story = [Paragraph(_para(PROJECT), S["proj"]), Paragraph("PDM (Project Design Matrix)", S["title"])]
    info = [(_s(x.get("code")), _s(x.get("summary"))) for x in g["info"]]
    info += [("버전", f"v{version} · {_s(meta.get('status')) or '초안'}"), ("생성일 / 작성자", f"{_s(meta.get('created_at'))} / {_s(meta.get('author'))}"),
             ("승인일", _s(meta.get("approved_at"))), ("변경 사유", _s(meta.get("reason")))]
    idata = []
    for i in range(0, len(info), 2):
        pair = info[i:i + 2]
        row = []
        for k, v in pair:
            row += [Paragraph(_para(k), S["k"]), Paragraph(_para(v), S["v"])]
        row += [""] * (4 - len(row))
        idata.append(row)
    it = Table(idata, colWidths=[34 * mm, 100 * mm, 34 * mm, 100 * mm])
    it.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B8C2D3")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F3F6FB")), ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#F3F6FB")),
                            ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    story += [it, Spacer(1, 5)]

    data = [[Paragraph(_para(h), S["h"]) for h, _ in HEAD]]
    style = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#B8C2D3")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E9C")), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    for lv, title in SECTIONS:
        secr = [x for x in rows if _s(x.get("level")) == lv]
        if not secr:
            continue
        data.append([Paragraph(_para(title), S["sec"]), "", "", "", ""])
        n = len(data) - 1
        style += [("SPAN", (0, n), (-1, n)), ("BACKGROUND", (0, n), (-1, n), colors.HexColor("#EEF2F9"))]
        for x in secr:
            data.append([Paragraph(_para(_summary_cell(x)), S["v"]), Paragraph(_para(_s(x.get("indicators"))), S["v"]), Paragraph(_para(_s(x.get("mov"))), S["v"]),
                         Paragraph(_para(_s(x.get("assumptions"))), S["v"]), Paragraph(_para(_s(x.get("proposal"))), S["v"])])
            style.append(("BACKGROUND", (4, len(data) - 1), (4, len(data) - 1), colors.HexColor("#FFFBEB")))
    if g["act"] or g["inp"] or g["pre"]:
        data.append([Paragraph("Activities (활동)", S["sec"]), Paragraph("Inputs (투입물)", S["sec"]), "", Paragraph("Pre-conditions (선행조건)", S["sec"]), Paragraph("검증지표 추가제안", S["sec"])])
        n = len(data) - 1
        style += [("SPAN", (1, n), (2, n)), ("BACKGROUND", (0, n), (-1, n), colors.HexColor("#EEF2F9"))]
        data.append([Paragraph(_para("\n".join(_summary_cell(x) for x in g["act"])), S["v"]),
                     Paragraph(_para("\n".join(f"[{_s(x.get('code'))}]\n{_s(x.get('summary'))}" for x in g["inp"])), S["v"]), "",
                     Paragraph(_para("\n".join(_s(x.get("summary")) for x in g["pre"])), S["v"]),
                     Paragraph(_para("\n".join(_s(x.get("proposal")) for x in g["act"] + g["inp"] + g["pre"] if _s(x.get("proposal")))), S["v"])])
        n = len(data) - 1
        style += [("SPAN", (1, n), (2, n)), ("BACKGROUND", (4, n), (4, n), colors.HexColor("#FFFBEB"))]
    tbl = Table(data, colWidths=[66 * mm, 66 * mm, 44 * mm, 52 * mm, 40 * mm], repeatRows=1)
    tbl.setStyle(TableStyle(style))
    story += [tbl, Paragraph(_para(f"PDM v{version} · 출력 {datetime.now():%Y-%m-%d %H:%M} · KOICA AI 성과관리"), S["foot"])]
    doc.build(story)
    return buf.getvalue()
