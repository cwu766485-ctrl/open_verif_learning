#!/usr/bin/env python3
"""Render the current Markdown verification report as a Chinese-capable PDF."""

from html import escape
import os
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).with_name("nutshell_cache_verification_report.md")
OUTPUT = SOURCE.with_suffix(".pdf")
NAVY = colors.HexColor("#17324D")
PALE = colors.HexColor("#F2F5F8")
GRID = colors.HexColor("#D9E0E6")
INK = colors.HexColor("#24313D")


def register_font():
    configured = os.environ.get("NUTSHELL_CJK_FONT")
    candidates = [Path(configured)] if configured else []
    candidates += [
        Path("/mnt/c/Windows/Fonts/msyh.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    ]
    path = next((item for item in candidates if item.is_file()), None)
    if path is None:
        raise FileNotFoundError("Set NUTSHELL_CJK_FONT to a CJK TrueType font")
    pdfmetrics.registerFont(TTFont("CacheCJK", str(path), subfontIndex=0))
    pdfmetrics.registerFontFamily("CacheCJK", normal="CacheCJK", bold="CacheCJK",
                                 italic="CacheCJK", boldItalic="CacheCJK")


def inline(text):
    text = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", text)
    text = escape(text, quote=False)
    text = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    return text


def table_rows(lines):
    return [[Paragraph(inline(cell.strip()), STYLES["table"]) for cell in line.strip().strip("|").split("|")]
            for line in lines]


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#F28C28"))
    canvas.setLineWidth(1.5)
    canvas.line(doc.leftMargin, A4[1] - 13 * mm, A4[0] - doc.rightMargin, A4[1] - 13 * mm)
    canvas.setFont("CacheCJK", 7)
    canvas.setFillColor(colors.HexColor("#5F6F7D"))
    canvas.drawString(doc.leftMargin, 9 * mm, "NutShell MESI Cache v1.0 | 综合技术与验证报告")
    canvas.drawRightString(A4[0] - doc.rightMargin, 9 * mm, str(doc.page))
    canvas.restoreState()


def build():
    register_font()
    sample = getSampleStyleSheet()
    global STYLES
    STYLES = {
        "title": ParagraphStyle("TitleCJK", parent=sample["Title"], fontName="CacheCJK",
                                fontSize=20, leading=26, textColor=NAVY, alignment=TA_CENTER,
                                spaceAfter=5 * mm),
        "h1": ParagraphStyle("H1CJK", parent=sample["Heading1"], fontName="CacheCJK",
                              fontSize=15, leading=20, textColor=NAVY, spaceBefore=4 * mm,
                              spaceAfter=2 * mm),
        "h2": ParagraphStyle("H2CJK", parent=sample["Heading2"], fontName="CacheCJK",
                              fontSize=11, leading=15, textColor=NAVY, spaceBefore=3 * mm,
                              spaceAfter=1.5 * mm),
        "body": ParagraphStyle("BodyCJK", parent=sample["BodyText"], fontName="CacheCJK",
                               fontSize=8.4, leading=12, textColor=INK, spaceAfter=1.6 * mm),
        "bullet": ParagraphStyle("BulletCJK", parent=sample["BodyText"], fontName="CacheCJK",
                                 fontSize=8.2, leading=11, leftIndent=12, firstLineIndent=-8,
                                 textColor=INK, spaceAfter=1 * mm),
        "table": ParagraphStyle("TableCJK", parent=sample["BodyText"], fontName="CacheCJK",
                                fontSize=7.2, leading=9.5, textColor=INK),
        "table_head": ParagraphStyle("TableHeadCJK", parent=sample["BodyText"],
                                     fontName="CacheCJK", fontSize=7.2, leading=9.5,
                                     textColor=colors.white),
        "code": ParagraphStyle("CodeCJK", parent=sample["Code"], fontName="Courier",
                               fontSize=7.2, leading=9, backColor=PALE, leftIndent=6,
                               rightIndent=6, borderPadding=5),
        "subtitle": ParagraphStyle("SubtitleCJK", parent=sample["Normal"], fontName="CacheCJK",
                                   fontSize=8, leading=11, textColor=colors.HexColor("#5F6F7D"),
                                   alignment=TA_CENTER, spaceAfter=5 * mm),
    }
    doc = SimpleDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=16*mm, leftMargin=16*mm,
                            topMargin=20*mm, bottomMargin=16*mm,
                            title="NutShell MESI Cache v1.0 综合技术与验证报告",
                            author="NutShell Cache DV Project")
    lines = SOURCE.read_text(encoding="utf-8").splitlines()
    story = []
    i = 0
    in_code = False
    code = []
    paragraph_lines = []

    def flush_paragraph():
        if paragraph_lines:
            story.append(Paragraph(inline(" ".join(paragraph_lines)), STYLES["body"]))
            paragraph_lines.clear()

    while i < len(lines):
        line = lines[i]
        if line.startswith("```"):
            flush_paragraph()
            if in_code:
                story.append(Preformatted("\n".join(code), STYLES["code"]))
                code.clear()
                in_code = False
            else:
                in_code = True
            i += 1
            continue
        if in_code:
            code.append(line)
            i += 1
            continue
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"\s*\|?\s*:?-{3,}", lines[i+1]):
            flush_paragraph()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                if not re.match(r"\s*\|?\s*:?-{3,}", lines[i]):
                    rows.append([cell.strip() for cell in lines[i].strip().strip("|").split("|")])
                i += 1
            data = [[Paragraph(inline(cell), STYLES["table_head"] if row_index == 0 else STYLES["table"])
                     for cell in row] for row_index, row in enumerate(rows)]
            widths = [doc.width / max(len(data[0]), 1)] * len(data[0])
            table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0,0), (-1,0), NAVY), ("GRID", (0,0), (-1,-1), .35, GRID),
                ("VALIGN", (0,0), (-1,-1), "TOP"), ("LEFTPADDING", (0,0), (-1,-1), 5),
                ("RIGHTPADDING", (0,0), (-1,-1), 5), ("TOPPADDING", (0,0), (-1,-1), 4),
                ("BOTTOMPADDING", (0,0), (-1,-1), 4),
                ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, PALE]),
            ]))
            story.extend([table, Spacer(1, 2*mm)])
            continue
        if not line.strip():
            flush_paragraph()
            i += 1
            continue
        if line.startswith("# "):
            flush_paragraph()
            story.append(Paragraph(inline(line[2:]), STYLES["title"]))
        elif line.startswith("## "):
            flush_paragraph()
            story.append(Paragraph(inline(line[3:]), STYLES["h1"]))
        elif line.startswith("### "):
            flush_paragraph()
            story.append(Paragraph(inline(line[4:]), STYLES["h2"]))
        elif line.startswith("- "):
            flush_paragraph()
            story.append(Paragraph("• " + inline(line[2:]), STYLES["bullet"]))
        else:
            paragraph_lines.append(line.strip())
        i += 1
    flush_paragraph()
    if in_code and code:
        story.append(Preformatted("\n".join(code), STYLES["code"]))
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    build()
