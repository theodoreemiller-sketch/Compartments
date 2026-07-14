#!/usr/bin/env python3
"""
Glen Ellyn Fire Department — Shift Rig Check PDF Generator
===========================================================
Parses the apparatus study guide HTML and generates a separate
printable rig check PDF for each vehicle.

Usage:
    python3 generate_rig_check_pdfs.py

Output:
    One PDF per vehicle in the same folder as this script, e.g.:
        Engine_61_Rig_Check.pdf
        Engine_60_Rig_Check.pdf
        Engine_63_Rig_Check.pdf
        Utility_61_Rig_Check.pdf
        Utility_62_Rig_Check.pdf

Requirements:
    pip install reportlab beautifulsoup4 --break-system-packages
"""

import os
import re
from pathlib import Path
from bs4 import BeautifulSoup

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether
)
from reportlab.pdfgen import canvas as pdfcanvas

# ── Configuration ─────────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
HTML_FILE  = SCRIPT_DIR / "index.html"
OUTPUT_DIR = SCRIPT_DIR / "Rig Check PDFs"

# Checklist sections to extract: (html_id, display_name, accent_hex)
VEHICLES = [
    ("e61-checklist", "Engine 61",  "#C8202D"),
    ("e60-checklist", "Engine 60",  "#C8202D"),
    ("e63-checklist", "Engine 63",  "#1A7A40"),
    ("u61-checklist", "Utility 61", "#1A4B8C"),
    ("u62-checklist", "Utility 62", "#7A3A8A"),
]

# ── Colors ────────────────────────────────────────────────────────────────────

DARK_SLATE  = HexColor("#1F1C18")
CREAM       = HexColor("#F5F0E8")
LIGHT_RULE  = HexColor("#C8BFB0")
MUTED_TEXT  = HexColor("#5A5248")
WHITE       = white
BLACK       = black

# ── Helpers ───────────────────────────────────────────────────────────────────

def clean(text: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">") \
               .replace("&#39;", "'").replace("&quot;", '"') \
               .replace("–", "-").replace("—", "—") \
               .replace("²", "²").replace("³", "³") \
               .replace("’", "'").replace("‘", "'") \
               .replace("½", "½")
    return re.sub(r"\s+", " ", text).strip()


def parse_checklists(html_path: Path) -> dict:
    """
    Returns dict keyed by html_id:
        {
          "title": "Engine 61 Shift Rig Check — Checklist",
          "sections": [
              {"name": "Driver's Side — Cabin & Hose Bed", "items": ["item1", ...]},
              ...
          ]
        }
    """
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    results = {}

    for vid, _, _ in VEHICLES:
        section = soup.find("section", id=vid)
        if not section:
            print(f"  WARNING: section id='{vid}' not found — skipping")
            continue

        # Title from h2 inside the section header
        h2 = section.find("h2")
        title = clean(h2.get_text()) if h2 else vid

        sections = []
        for card in section.find_all("div", class_="equip-card"):
            # Card title = compartment name
            title_div = card.find("div", class_="card-title")
            if not title_div:
                continue
            comp_name = clean(title_div.get_text())

            # All <li> items in this card
            items = []
            for li in card.find_all("li"):
                text = clean(li.get_text())
                if text:
                    # Strip leading ⭐ / emoji markers but keep the text
                    text = text.strip()
                    items.append(text)

            if items:
                sections.append({"name": comp_name, "items": items})

        results[vid] = {"title": title, "sections": sections}

    return results


# ── PDF page template (header + footer on every page) ────────────────────────

class RigCheckCanvas(pdfcanvas.Canvas):
    """Draws the running header and footer on every page."""

    def __init__(self, *args, vehicle_name="", accent_color=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.vehicle_name  = vehicle_name
        self.accent_color  = accent_color or HexColor("#C8202D")
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        page_count = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_page(page_count)
            pdfcanvas.Canvas.showPage(self)
        pdfcanvas.Canvas.save(self)

    def _draw_page(self, page_count):
        W, H = letter

        # ── Top banner ──
        self.setFillColor(DARK_SLATE)
        self.rect(0, H - 0.65*inch, W, 0.65*inch, fill=1, stroke=0)

        # Accent bar
        self.setFillColor(self.accent_color)
        self.rect(0, H - 0.65*inch - 4, W, 4, fill=1, stroke=0)

        # Vehicle name
        self.setFont("Helvetica-Bold", 14)
        self.setFillColor(WHITE)
        self.drawString(0.45*inch, H - 0.44*inch, self.vehicle_name.upper())

        # "SHIFT RIG CHECK" label
        self.setFont("Helvetica", 9)
        self.setFillColor(LIGHT_RULE)
        self.drawString(0.45*inch, H - 0.58*inch, "SHIFT RIG CHECK  ·  GLEN ELLYN FIRE DEPARTMENT")

        # Page number top-right
        self.setFont("Helvetica", 8)
        self.setFillColor(LIGHT_RULE)
        page_num = self._pageNumber
        self.drawRightString(W - 0.45*inch, H - 0.44*inch,
                             f"Page {page_num} of {page_count}")

        # ── Bottom footer ──
        self.setFillColor(LIGHT_RULE)
        self.rect(0.45*inch, 0.35*inch, W - 0.9*inch, 0.5, fill=1, stroke=0)

        self.setFont("Helvetica", 7)
        self.setFillColor(MUTED_TEXT)
        self.drawString(0.45*inch, 0.22*inch,
                        "Unofficial study guide — always verify against the actual rig · "
                        "Glen Ellyn FD Unofficial Apparatus Study Guides")
        self.drawRightString(W - 0.45*inch, 0.22*inch,
                             "Generated by generate_rig_check_pdfs.py")


class RigCheckDocBuilder:
    """Builds one rig-check PDF for a single vehicle."""

    def __init__(self, vehicle_name: str, accent_hex: str, data: dict, out_path: Path):
        self.vehicle_name = vehicle_name
        self.accent       = HexColor(accent_hex)
        self.data         = data          # {"title": ..., "sections": [...]}
        self.out_path     = out_path

    # ── Styles ────────────────────────────────────────────────────────────────

    def _styles(self):
        section_label = ParagraphStyle(
            "SectionLabel",
            fontName="Helvetica-Bold",
            fontSize=9,
            textColor=WHITE,
            leading=13,
            leftIndent=6,
        )
        item_style = ParagraphStyle(
            "Item",
            fontName="Helvetica",
            fontSize=8.5,
            textColor=BLACK,
            leading=12,
            leftIndent=4,
        )
        field_label = ParagraphStyle(
            "FieldLabel",
            fontName="Helvetica",
            fontSize=7.5,
            textColor=MUTED_TEXT,
            leading=10,
        )
        notes_label = ParagraphStyle(
            "NotesLabel",
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=MUTED_TEXT,
            leading=11,
        )
        return section_label, item_style, field_label, notes_label

    # ── Header info row ───────────────────────────────────────────────────────

    def _header_fields(self, field_label):
        """Date / Shift / Station / Officer / Crew fields row."""
        fields = ["Date:", "Shift:", "Station:", "Officer:", "Crew:"]
        cells  = []
        for f in fields:
            cells.append([
                Paragraph(f, field_label),
                Spacer(1, 0.18*inch),
                HRFlowable(width="100%", thickness=0.5, color=DARK_SLATE),
            ])

        tbl = Table(
            [cells],
            colWidths=[1.37*inch] * 5,
            rowHeights=None,
        )
        tbl.setStyle(TableStyle([
            ("VALIGN",      (0, 0), (-1, -1), "BOTTOM"),
            ("LEFTPADDING",  (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING",   (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
            ("BOX",          (0, 0), (-1, -1), 0.5, LIGHT_RULE),
            ("INNERGRID",    (0, 0), (-1, -1), 0.5, LIGHT_RULE),
            ("BACKGROUND",   (0, 0), (-1, -1), CREAM),
        ]))
        return tbl

    # ── Compartment section block ─────────────────────────────────────────────

    def _comp_section(self, comp: dict, section_label, item_style):
        """Returns a KeepTogether block for one compartment."""
        name  = comp["name"]
        items = comp["items"]

        # Section header row
        hdr_data = [[Paragraph(name, section_label)]]
        hdr_tbl  = Table(hdr_data, colWidths=[7.1*inch])
        hdr_tbl.setStyle(TableStyle([
            ("BACKGROUND",   (0, 0), (-1, -1), self.accent),
            ("TOPPADDING",   (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
            ("LEFTPADDING",  (0, 0), (-1, -1), 8),
        ]))

        # Two-column checklist
        # Split items into left / right columns
        mid    = (len(items) + 1) // 2
        left   = items[:mid]
        right  = items[mid:]

        def checkbox_row(text):
            return [Paragraph("☐", item_style), Paragraph(text, item_style)]

        left_rows  = [checkbox_row(t) for t in left]
        right_rows = [checkbox_row(t) for t in right]

        # Pad shorter column
        while len(right_rows) < len(left_rows):
            right_rows.append(["", ""])

        # Interleave: left_cb | left_text | spacer | right_cb | right_text
        combined_rows = []
        for l_row, r_row in zip(left_rows, right_rows):
            combined_rows.append(l_row + [Spacer(6, 1)] + r_row)

        items_tbl = Table(
            combined_rows,
            colWidths=[0.22*inch, 3.12*inch, 0.1*inch, 0.22*inch, 3.44*inch],
        )
        items_tbl.setStyle(TableStyle([
            ("VALIGN",       (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",   (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 3),
            ("LEFTPADDING",  (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, CREAM]),
            ("BOX",           (0, 0), (-1, -1), 0.3, LIGHT_RULE),
        ]))

        return KeepTogether([hdr_tbl, items_tbl, Spacer(1, 0.12*inch)])

    # ── Notes + signature block ───────────────────────────────────────────────

    def _footer_block(self, notes_label, field_label):
        flowables = []
        flowables.append(Spacer(1, 0.15*inch))
        flowables.append(HRFlowable(width="100%", thickness=1, color=self.accent))
        flowables.append(Spacer(1, 0.08*inch))

        # Notes box
        notes_data = [
            [Paragraph("NOTES / DEFICIENCIES FOUND THIS SHIFT:", notes_label)],
            [Spacer(1, 0.8*inch)],
        ]
        notes_tbl = Table(notes_data, colWidths=[7.1*inch])
        notes_tbl.setStyle(TableStyle([
            ("BOX",          (0, 0), (-1, -1), 0.5, LIGHT_RULE),
            ("LEFTPADDING",  (0, 0), (-1, -1), 8),
            ("TOPPADDING",   (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 6),
        ]))
        flowables.append(notes_tbl)
        flowables.append(Spacer(1, 0.18*inch))

        # Signature row
        sig_fields = ["Checked by (print):", "Signature:", "Date:", "Time:"]
        sig_cells  = []
        for f in sig_fields:
            sig_cells.append([
                Paragraph(f, field_label),
                Spacer(1, 0.22*inch),
                HRFlowable(width="100%", thickness=0.5, color=DARK_SLATE),
            ])

        widths = [2.0*inch, 2.6*inch, 1.2*inch, 1.3*inch]
        sig_tbl = Table([sig_cells], colWidths=widths)
        sig_tbl.setStyle(TableStyle([
            ("VALIGN",       (0, 0), (-1, -1), "BOTTOM"),
            ("LEFTPADDING",  (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING",   (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
            ("BOX",          (0, 0), (-1, -1), 0.5, LIGHT_RULE),
            ("INNERGRID",    (0, 0), (-1, -1), 0.5, LIGHT_RULE),
            ("BACKGROUND",   (0, 0), (-1, -1), CREAM),
        ]))
        flowables.append(sig_tbl)
        return flowables

    # ── Main build ────────────────────────────────────────────────────────────

    def build(self):
        section_label, item_style, field_label, notes_label = self._styles()

        doc = SimpleDocTemplate(
            str(self.out_path),
            pagesize=letter,
            leftMargin=0.45*inch,
            rightMargin=0.45*inch,
            topMargin=0.85*inch,
            bottomMargin=0.6*inch,
        )

        story = []

        # Header fields
        story.append(self._header_fields(field_label))
        story.append(Spacer(1, 0.18*inch))

        # Compartment sections
        for comp in self.data["sections"]:
            story.append(self._comp_section(comp, section_label, item_style))

        # Notes + signature
        story.extend(self._footer_block(notes_label, field_label))

        def make_canvas(filename, **kwargs):
            return RigCheckCanvas(
                filename,
                vehicle_name=self.vehicle_name,
                accent_color=self.accent,
                **kwargs,
            )

        doc.build(story, canvasmaker=make_canvas)
        print(f"  ✓  {self.out_path.name}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if not HTML_FILE.exists():
        print(f"ERROR: HTML file not found at {HTML_FILE}")
        print("Make sure this script is in the same folder as index.html.")
        return

    OUTPUT_DIR.mkdir(exist_ok=True)
    print(f"Parsing {HTML_FILE.name} ...")
    checklists = parse_checklists(HTML_FILE)

    print(f"\nGenerating PDFs → {OUTPUT_DIR}\n")
    for vid, display_name, accent_hex in VEHICLES:
        if vid not in checklists:
            print(f"  SKIP  {display_name} (no checklist section found)")
            continue

        data     = checklists[vid]
        filename = display_name.replace(" ", "_") + "_Rig_Check.pdf"
        out_path = OUTPUT_DIR / filename

        builder = RigCheckDocBuilder(
            vehicle_name=display_name,
            accent_hex=accent_hex,
            data=data,
            out_path=out_path,
        )
        builder.build()

    print(f"\nDone. PDFs saved to:\n  {OUTPUT_DIR}\n")


if __name__ == "__main__":
    main()
