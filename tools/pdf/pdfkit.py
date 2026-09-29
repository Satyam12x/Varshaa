"""Shared styles, page templates and diagram helpers for the SAMANVAY proposal PDF."""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Paragraph, Spacer, Table, TableStyle, KeepTogether, Flowable)
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
from reportlab.platypus.tableofcontents import TableOfContents

F = "C:/Windows/Fonts/"
pdfmetrics.registerFont(TTFont("UI", F + "segoeui.ttf"))
pdfmetrics.registerFont(TTFont("UI-B", F + "segoeuib.ttf"))
pdfmetrics.registerFont(TTFont("UI-I", F + "segoeuii.ttf"))
pdfmetrics.registerFont(TTFont("UI-BI", F + "segoeuiz.ttf"))
pdfmetrics.registerFont(TTFont("UI-L", F + "segoeuil.ttf"))
from reportlab.pdfbase.pdfmetrics import registerFontFamily
registerFontFamily("UI", normal="UI", bold="UI-B", italic="UI-I", boldItalic="UI-BI")

NAVY = colors.HexColor("#0d2b4e"); BLUE = colors.HexColor("#2a78d6"); ORANGE = colors.HexColor("#eb6834")
INK = colors.HexColor("#1b1b1a"); MUTED = colors.HexColor("#52514e"); LINE = colors.HexColor("#d9d8d2")
PANEL = colors.HexColor("#f1f5fb"); PANEL2 = colors.HexColor("#fdf1eb"); GREEN = colors.HexColor("#1b7f4c")
WHITE = colors.white
PAGE_W, PAGE_H = A4
MARGIN = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

ST = {
    "body": ParagraphStyle("body", fontName="UI", fontSize=9.6, leading=14, textColor=INK, alignment=TA_JUSTIFY, spaceAfter=6),
    "bodyL": ParagraphStyle("bodyL", fontName="UI", fontSize=9.6, leading=14, textColor=INK, alignment=TA_LEFT, spaceAfter=6),
    "h1": ParagraphStyle("h1", keepWithNext=1, fontName="UI-B", fontSize=17, leading=21, textColor=NAVY, spaceBefore=4, spaceAfter=10),
    "h2": ParagraphStyle("h2", keepWithNext=1, fontName="UI-B", fontSize=12, leading=15, textColor=NAVY, spaceBefore=10, spaceAfter=5),
    "h3": ParagraphStyle("h3", keepWithNext=1, fontName="UI-B", fontSize=10, leading=13, textColor=BLUE, spaceBefore=6, spaceAfter=3),
    "bullet": ParagraphStyle("bullet", fontName="UI", fontSize=9.6, leading=13.6, textColor=INK, leftIndent=14,
                             bulletIndent=3, spaceAfter=3, alignment=TA_LEFT),
    "cell": ParagraphStyle("cell", fontName="UI", fontSize=8.3, leading=11, textColor=INK),
    "cellB": ParagraphStyle("cellB", fontName="UI-B", fontSize=8.3, leading=11, textColor=INK),
    "cellH": ParagraphStyle("cellH", fontName="UI-B", fontSize=8.3, leading=11, textColor=WHITE),
    "caption": ParagraphStyle("caption", fontName="UI-I", fontSize=8.2, leading=11, textColor=MUTED, spaceBefore=3, spaceAfter=10),
    "callout": ParagraphStyle("callout", fontName="UI", fontSize=9.4, leading=13.5, textColor=INK),
    "kpiN": ParagraphStyle("kpiN", fontName="UI-B", fontSize=19, leading=22, textColor=BLUE, alignment=TA_CENTER),
    "kpiL": ParagraphStyle("kpiL", fontName="UI", fontSize=7.8, leading=10, textColor=MUTED, alignment=TA_CENTER),
    "eq": ParagraphStyle("eq", fontName="UI", fontSize=9.6, leading=14, textColor=INK, alignment=TA_CENTER,
                         spaceBefore=2, spaceAfter=8),
    "toc1": ParagraphStyle("toc1", fontName="UI-B", fontSize=10, leading=13.5, spaceBefore=2, textColor=NAVY),
    "toc2": ParagraphStyle("toc2", fontName="UI", fontSize=8.6, leading=10.6, leftIndent=16, textColor=INK),
}


def P(t, s="body"):
    return Paragraph(t, ST[s])


def bullets(items, s="bullet"):
    return [Paragraph(i, ST[s], bulletText="•") for i in items]


def table(rows, widths, header=True, zebra=True, head_bg=NAVY, font_size=None, valign="TOP"):
    data = []
    for r_i, r in enumerate(rows):
        row = []
        for c in r:
            if isinstance(c, str):
                style = "cellH" if (header and r_i == 0) else "cell"
                row.append(Paragraph(c, ST[style]))
            else:
                row.append(c)
        data.append(row)
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    cmds = [("VALIGN", (0, 0), (-1, -1), valign), ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4), ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("LINEBELOW", (0, 0), (-1, -1), 0.4, LINE)]
    if header:
        cmds += [("BACKGROUND", (0, 0), (-1, 0), head_bg)]
    if zebra:
        for i in range(1 if header else 0, len(rows)):
            if i % 2 == 0:
                cmds.append(("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f7f7f5")))
    t.setStyle(TableStyle(cmds))
    return t


def callout(flow, bg=PANEL, bar=BLUE, title=None):
    inner = []
    if title:
        inner.append(Paragraph(title, ParagraphStyle("ct", parent=ST["h3"], textColor=bar, spaceBefore=0)))
    inner += flow if isinstance(flow, list) else [flow]
    t = Table([[inner]], colWidths=[CONTENT_W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), bg), ("LINEBEFORE", (0, 0), (0, -1), 3, bar),
                           ("LEFTPADDING", (0, 0), (-1, -1), 11), ("RIGHTPADDING", (0, 0), (-1, -1), 11),
                           ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    return t


def kpis(items):
    """items: list of (number, label)."""
    w = CONTENT_W / len(items)
    cells = [[Paragraph(n, ST["kpiN"]), Paragraph(l, ST["kpiL"])] for n, l in items]
    t = Table([[c for c in cells]], colWidths=[w] * len(items))
    t = Table([[Table([[a], [b]], colWidths=[w - 8]) for a, b in cells]], colWidths=[w] * len(items))
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), PANEL), ("LINEAFTER", (0, 0), (-2, -1), 2, WHITE),
                           ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 8),
                           ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    return t


class Heading(Paragraph):
    """Paragraph that registers itself in the TOC."""
    def __init__(self, text, style, level):
        super().__init__(text, ST[style]); self.toc_level = level; self.toc_text = text


# ---------------- diagrams ----------------
def dbox(d, x, y, w, h, lines, fill=PANEL, stroke=BLUE, tc=INK, size=7.6, bold_first=True, r=4):
    d.add(Rect(x, y, w, h, rx=r, ry=r, fillColor=fill, strokeColor=stroke, strokeWidth=0.9))
    n = len(lines); lh = size + 2.6
    y0 = y + h / 2 + (n - 1) * lh / 2 - size * 0.35
    for i, t in enumerate(lines):
        d.add(String(x + w / 2, y0 - i * lh, t, fontName="UI-B" if (i == 0 and bold_first) else "UI",
                     fontSize=size, fillColor=tc, textAnchor="middle"))


def arrow(d, x1, y1, x2, y2, c=MUTED, w=1.1):
    import math
    d.add(Line(x1, y1, x2, y2, strokeColor=c, strokeWidth=w))
    a = math.atan2(y2 - y1, x2 - x1); L = 5.5
    p1 = (x2 - L * math.cos(a - 0.4), y2 - L * math.sin(a - 0.4))
    p2 = (x2 - L * math.cos(a + 0.4), y2 - L * math.sin(a + 0.4))
    d.add(Polygon([x2, y2, p1[0], p1[1], p2[0], p2[1]], fillColor=c, strokeColor=c, strokeWidth=0.5))


def label(d, x, y, t, size=7.2, c=MUTED, anchor="middle", font="UI"):
    d.add(String(x, y, t, fontName=font, fontSize=size, fillColor=c, textAnchor=anchor))
