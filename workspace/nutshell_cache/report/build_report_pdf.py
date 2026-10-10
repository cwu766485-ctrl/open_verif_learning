#!/usr/bin/env python3
"""Build the concise Chinese NutShell Cache verification report PDF."""

from pathlib import Path
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "nutshell_cache_report_demo.pdf"
NAVY = colors.HexColor("#17324D")
ORANGE = colors.HexColor("#F28C28")
PALE = colors.HexColor("#F2F5F8")
GRID = colors.HexColor("#D9E0E6")
INK = colors.HexColor("#24313D")
MUTED = colors.HexColor("#5F6F7D")


def register_cjk_font() -> str:
    configured = os.environ.get("NUTSHELL_CJK_FONT")
    candidates = [
        Path(configured) if configured else None,
        Path("/mnt/c/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
    ]
    font_path = next((path for path in candidates if path and path.is_file()), None)
    if font_path is None:
        raise FileNotFoundError(
            "Microsoft YaHei or Noto Sans CJK font not found; set NUTSHELL_CJK_FONT"
        )
    pdfmetrics.registerFont(TTFont("CacheCJK", str(font_path), subfontIndex=0))
    pdfmetrics.registerFontFamily(
        "CacheCJK", normal="CacheCJK", bold="CacheCJK", italic="CacheCJK", boldItalic="CacheCJK"
    )
    return "CacheCJK"


def build_styles(font: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "CacheTitle", parent=base["Title"], fontName=font, fontSize=22,
            leading=29, textColor=NAVY, alignment=TA_LEFT, spaceAfter=3 * mm,
        ),
        "subtitle": ParagraphStyle(
            "CacheSubtitle", parent=base["Normal"], fontName=font, fontSize=9,
            leading=14, textColor=MUTED, spaceAfter=5 * mm,
        ),
        "h2": ParagraphStyle(
            "CacheH2", parent=base["Heading2"], fontName=font, fontSize=13,
            leading=18, textColor=NAVY, spaceBefore=3 * mm, spaceAfter=2 * mm,
        ),
        "body": ParagraphStyle(
            "CacheBody", parent=base["BodyText"], fontName=font, fontSize=9,
            leading=14, textColor=INK, spaceAfter=2 * mm,
        ),
        "small": ParagraphStyle(
            "CacheSmall", parent=base["BodyText"], fontName=font, fontSize=8,
            leading=11, textColor=INK,
        ),
        "cell_head": ParagraphStyle(
            "CacheCellHead", parent=base["BodyText"], fontName=font, fontSize=8.5,
            leading=12, textColor=colors.white,
        ),
        "center": ParagraphStyle(
            "CacheCenter", parent=base["BodyText"], fontName=font, fontSize=9,
            leading=13, textColor=INK, alignment=TA_CENTER,
        ),
    }


def paragraph(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def make_table(rows, widths, header=True, font_size=8.5):
    table = Table(rows, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.45, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("FONTSIZE", (0, 0), (-1, -1), font_size),
    ]
    if header:
        commands.extend([
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ])
        if len(rows) > 1:
            commands.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE]))
    table.setStyle(TableStyle(commands))
    return table


def draw_page(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(ORANGE)
    canvas.setLineWidth(2)
    canvas.line(doc.leftMargin, height - 14 * mm, width - doc.rightMargin, height - 14 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(doc.leftMargin, 10 * mm, "NutShell L1 DCache | Open-source DV")
    canvas.drawRightString(width - doc.rightMargin, 10 * mm, f"{doc.page}")
    canvas.restoreState()


def build():
    font = register_cjk_font()
    styles = build_styles(font)
    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=A4, rightMargin=17 * mm, leftMargin=17 * mm,
        topMargin=21 * mm, bottomMargin=17 * mm,
        title="NutShell L1 DCache 开源验证报告",
        author="NutShell Cache DV Project",
    )
    story = []
    story.append(paragraph("NutShell L1 DCache 验证报告", styles["title"]))
    story.append(paragraph(
        "开源 Python DV 环境 | 更新日期 2026-10-10 | SimpleBus 模块级验证",
        styles["subtitle"],
    ))
    story.append(paragraph(
        "面向嵌入式与边缘 RISC-V 工作负载，构建可复现、无需商业仿真器的 Cache 验证流程。"
        "当前回归通过 <b>39/39</b> 个 pytest cases，命中 <b>37/37</b> 个功能覆盖目标。",
        styles["body"],
    ))

    story.append(paragraph("DUT 与环境", styles["h2"]))
    dut_rows = [
        [paragraph("项目", styles["cell_head"]), paragraph("配置 / 工具", styles["cell_head"])],
        [paragraph("Cache", styles["small"]), paragraph("32-KiB, 4-way set-associative, 128 sets", styles["small"])],
        [paragraph("Line / datapath", styles["small"]), paragraph("64-byte cache line, 64-bit datapath", styles["small"])],
        [paragraph("开源工具链", styles["small"]), paragraph("Python, Toffee, Picker, Verilator, pytest, Yosys, SymbiYosys", styles["small"])],
    ]
    story.append(make_table(dut_rows, [42 * mm, 132 * mm]))

    story.append(paragraph("验证架构", styles["h2"]))
    architecture = Table(
        [[paragraph("Sequences / directed + random", styles["center"])],
         [paragraph("CPU, memory, MMIO, coherence agents + monitors", styles["center"])],
         [paragraph("Independent memory + tag/valid/dirty/LFSR Refm", styles["center"])],
         [paragraph("In-order scoreboard + protocol / ready-valid checkers", styles["center"])],
         [paragraph("Functional coverage closure + Verilator line coverage", styles["center"]) ]],
        colWidths=[174 * mm], hAlign="LEFT",
    )
    architecture.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE), ("BOX", (0, 0), (-1, -1), 0.5, GRID),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, GRID), ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(architecture)
    story.append(Spacer(1, 2 * mm))
    story.append(paragraph(
        "Tag model 独立预测 hit/miss、invalid-first refill way 和精确 LFSR victim way；"
        "scoreboard 核对 dirty victim 地址及 writeback 的八个 data beat。",
        styles["small"],
    ))

    story.append(paragraph("回归与覆盖率", styles["h2"]))
    metric_rows = [
        [paragraph("Metric", styles["cell_head"]), paragraph("Result", styles["cell_head"]), paragraph("Scope", styles["cell_head"])],
        [paragraph("pytest", styles["small"]), paragraph("39/39 pass", styles["small"]), paragraph("Directed + randomized regression", styles["small"])],
        [paragraph("Functional coverage", styles["small"]), paragraph("37/37 (100%)", styles["small"]), paragraph("All planned closure goals hit", styles["small"])],
        [paragraph("Maintained RTL line", styles["small"]), paragraph("98.0% (845/862)", styles["small"]), paragraph("Raw; 100% (845/845) after reviewed waivers", styles["small"])],
        [paragraph("All-source line", styles["small"]), paragraph("95.1% (1423/1496)", styles["small"]), paragraph("Includes generated DUT/wrapper", styles["small"])],
        [paragraph("Fault injection", styles["small"]), paragraph("4/4 caught", styles["small"]), paragraph("Representative tag, writeback, ready-valid, response faults", styles["small"])],
    ]
    story.append(make_table(metric_rows, [41 * mm, 40 * mm, 93 * mm]))
    story.append(Spacer(1, 2 * mm))
    story.append(paragraph(
        "随机回归：本地 6 个固定 seed x 64 笔 = 384 笔操作；干净环境 CI 使用 8 个固定 seed = 512 笔操作。",
        styles["small"],
    ))

    story.append(paragraph("关键场景", styles["h2"]))
    scenarios = [
        "命中/缺失、partial byte write、same-word forwarding、跨 line 访问和 MMIO bypass",
        "set occupancy、4-way 冲突替换、clean/dirty victim、8-beat refill/writeback",
        "CPU 与 memory backpressure、排队 miss、coherence probe/release、reset 中止与恢复",
    ]
    for item in scenarios:
        story.append(paragraph(f"- {item}", styles["body"]))

    story.append(PageBreak())
    story.append(paragraph("形式验证与边界", styles["title"]))
    story.append(paragraph(
        "make formal 执行三个 SymbiYosys gate，并以 Yosys SAT 对 Stage3 做 8-cycle bounded safety check。",
        styles["body"],
    ))
    formal_rows = [
        [paragraph("Gate", styles["cell_head"]), paragraph("检查范围", styles["cell_head"]), paragraph("边界 / 假设", styles["cell_head"])],
        [paragraph("Replacement selector", styles["small"]), paragraph("LFSR recurrence, nonzero reset state", styles["small"]), paragraph("SymbiYosys proof", styles["small"])],
        [paragraph("Cache way selector", styles["small"]), paragraph("Replacement/refill one-hot selection", styles["small"]), paragraph("Unique-tag invariant", styles["small"])],
        [paragraph("Cache Stage2", styles["small"]), paragraph("Request payload stable during backpressure", styles["small"]), paragraph("SymbiYosys proof", styles["small"])],
        [paragraph("Cache Stage3", styles["small"]), paragraph("Response provenance/duplicate retirement, reset cancellation, stalled valid/command stability", styles["small"]), paragraph("8 cycles, data arrays abstracted; bounded only", styles["small"])],
    ]
    story.append(make_table(formal_rows, [39 * mm, 78 * mm, 57 * mm]))

    story.append(paragraph("解释与限制", styles["h2"]))
    limitations = [
        "Stage3 的 bounded SAT 不是无界端到端响应生命周期证明；full-cache reset proof 仍是后续工作。",
        "完整 response data-payload 稳定由仿真 checker 检查；formal harness 使用稳定至完成的单拍 READ/WRITE 及 MMIO 合约。",
        "原始维护 RTL 覆盖率仍为 98.0%；waiver 调整值单独报告，waiver 不替代 raw coverage。",
        "本项目是开源工具链下的模块级 sign-off-style regression，不声称 commercial sign-off 或 SoC 级验证。",
    ]
    for item in limitations:
        story.append(paragraph(f"- {item}", styles["body"]))

    story.append(paragraph("复现与 CI", styles["h2"]))
    commands = Table(
        [[paragraph("cd workspace/nutshell_cache<br/>source scripts/env.sh<br/>make gen_dut<br/>make formal<br/>make report", styles["small"]) ]],
        colWidths=[174 * mm],
    )
    commands.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE), ("BOX", (0, 0), (-1, -1), 0.5, GRID),
        ("LEFTPADDING", (0, 0), (-1, -1), 9), ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.append(commands)
    story.append(Spacer(1, 3 * mm))
    story.append(paragraph(
        "GitHub Actions 在干净 Ubuntu runner 上安装开源工具链并运行上述 formal、8-seed 回归及覆盖率 gate。"
        "运行记录：github.com/cwu766485-ctrl/open_verif_learning/actions/workflows/nutshell-cache-dv.yml",
        styles["small"],
    ))

    doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page)
    print(OUTPUT)


if __name__ == "__main__":
    build()
