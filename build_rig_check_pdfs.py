"""
Glen Ellyn FD — Shift Rig Check PDF Generator
Builds one PDF per vehicle. Run with: python3 build_rig_checks.py [vehicle_key]
Or no argument to build all.
"""
import sys, os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                 Table, TableStyle, PageBreak, HRFlowable)
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT

OUT_DIR = "/Users/ted.miller/Documents/Claude/Projects/UNOFFICIAL APPARATUS STUDY GUIDES"

RED    = colors.HexColor('#C8202D')
GOLD   = colors.HexColor('#D4A017')
DARK   = colors.HexColor('#1A1714')
LGRAY  = colors.HexColor('#F2F0ED')
MGRAY  = colors.HexColor('#D0CBC4')
WHITE  = colors.white
BLACK  = colors.black

# ── Page numbering canvas ─────────────────────────────────────────────────────
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []
        self._vehicle_label = ""

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_footer(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_footer(self, page_count):
        self.saveState()
        self.setFont('Helvetica', 7)
        self.setFillColor(colors.HexColor('#888880'))
        label = getattr(self, '_vehicle_label', 'SHIFT RIG CHECK')
        text = f"{label}  ·  FOR TRAINING PURPOSES ONLY  ·  Page {self._pageNumber} of {page_count}"
        self.drawCentredString(letter[0]/2, 0.35*inch, text)
        self.restoreState()

# ── Helpers ───────────────────────────────────────────────────────────────────
def make_styles():
    styles = getSampleStyleSheet()
    return {
        'section': ParagraphStyle('section',
            fontName='Helvetica-Bold', fontSize=9, textColor=WHITE,
            spaceAfter=0, spaceBefore=0, leading=12),
        'item': ParagraphStyle('item',
            fontName='Helvetica', fontSize=8.5, textColor=BLACK,
            spaceAfter=1, spaceBefore=1, leading=11, leftIndent=4),
        'header_title': ParagraphStyle('header_title',
            fontName='Helvetica-Bold', fontSize=22, textColor=RED,
            alignment=TA_CENTER, spaceAfter=2),
        'header_sub': ParagraphStyle('header_sub',
            fontName='Helvetica', fontSize=10, textColor=colors.HexColor('#555550'),
            alignment=TA_CENTER, spaceAfter=6),
        'field_label': ParagraphStyle('field_label',
            fontName='Helvetica-Bold', fontSize=8, textColor=BLACK),
        'note': ParagraphStyle('note',
            fontName='Helvetica', fontSize=8, textColor=colors.HexColor('#555550'),
            leading=11),
    }

def header_block(vehicle_name, subtitle=""):
    """Vehicle title header for top of first page."""
    story = []
    S = make_styles()
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(vehicle_name.upper(), S['header_title']))
    story.append(Paragraph("SHIFT RIG CHECK", ParagraphStyle('src',
        fontName='Helvetica-Bold', fontSize=13, textColor=DARK,
        alignment=TA_CENTER, spaceAfter=2)))
    if subtitle:
        story.append(Paragraph(subtitle, S['header_sub']))
    story.append(HRFlowable(width="100%", thickness=2, color=RED, spaceAfter=8))

    # Date / Shift / Engineer fields
    field_style = ParagraphStyle('fl', fontName='Helvetica-Bold', fontSize=8,
                                  textColor=BLACK, leading=10)
    line_style  = TableStyle([
        ('LINEBELOW', (1,0),(1,0), 0.5, MGRAY),
        ('LINEBELOW', (3,0),(3,0), 0.5, MGRAY),
        ('LINEBELOW', (5,0),(5,0), 0.5, MGRAY),
        ('VALIGN', (0,0),(-1,-1), 'BOTTOM'),
        ('FONTNAME', (0,0),(0,0), 'Helvetica-Bold'),
        ('FONTNAME', (2,0),(2,0), 'Helvetica-Bold'),
        ('FONTNAME', (4,0),(4,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0),(-1,-1), 8),
        ('BOTTOMPADDING',(0,0),(-1,-1), 2),
        ('TOPPADDING',(0,0),(-1,-1), 2),
    ])
    fields = Table(
        [['DATE:', '', 'SHIFT:', '', 'ENGINEER:', '']],
        colWidths=[0.7*inch, 1.8*inch, 0.55*inch, 1.3*inch, 0.8*inch, 1.85*inch]
    )
    fields.setStyle(line_style)
    story.append(fields)
    story.append(Spacer(1, 0.12*inch))
    return story

def section_row(title):
    """Red section header row for a table."""
    return ([Paragraph(f"  {title.upper()}", make_styles()['section']),
             Paragraph("", make_styles()['section'])],
            [('BACKGROUND',(0,0),(-1,0), RED),
             ('SPAN',(0,0),(-1,0)),
             ('TOPPADDING',(0,0),(-1,0),4),
             ('BOTTOMPADDING',(0,0),(-1,0),4),
             ('LEFTPADDING',(0,0),(-1,0),6)])

def build_checklist(compartments):
    """
    compartments: list of (section_title, [item, item, ...])
    Returns a list of reportlab flowables.
    """
    S = make_styles()
    story = []

    # Collect all rows for the two-column table
    all_items = []
    for sec_title, items in compartments:
        all_items.append(('SECTION', sec_title))
        for item in items:
            all_items.append(('ITEM', item))

    # Build table rows: 2 columns of checkboxes
    rows = []
    styles_cmds = [
        ('GRID', (0,0),(-1,-1), 0.3, MGRAY),
        ('VALIGN', (0,0),(-1,-1), 'TOP'),
        ('TOPPADDING', (0,0),(-1,-1), 3),
        ('BOTTOMPADDING', (0,0),(-1,-1), 3),
        ('LEFTPADDING', (0,0),(-1,-1), 4),
        ('RIGHTPADDING', (0,0),(-1,-1), 4),
    ]
    row_idx = 0

    def item_cell(text):
        return Paragraph(f"□  {text}", S['item'])

    i = 0
    while i < len(all_items):
        kind, val = all_items[i]
        if kind == 'SECTION':
            # Full-width section header
            cell = Paragraph(f"  {val.upper()}", S['section'])
            rows.append([cell, ''])
            styles_cmds += [
                ('BACKGROUND', (0,row_idx),(-1,row_idx), RED),
                ('SPAN',       (0,row_idx),(-1,row_idx)),
                ('TOPPADDING', (0,row_idx),(-1,row_idx), 4),
                ('BOTTOMPADDING',(0,row_idx),(-1,row_idx),4),
                ('LEFTPADDING',(0,row_idx),(-1,row_idx), 8),
            ]
            row_idx += 1
            i += 1
        else:
            # Pair items side by side
            left = item_cell(val)
            i += 1
            if i < len(all_items) and all_items[i][0] == 'ITEM':
                right = item_cell(all_items[i][1])
                i += 1
            else:
                right = Paragraph('', S['item'])
            rows.append([left, right])
            if row_idx % 2 == 0:
                styles_cmds.append(('BACKGROUND',(0,row_idx),(-1,row_idx), LGRAY))
            row_idx += 1

    col_w = (letter[0] - 1.4*inch) / 2
    tbl = Table(rows, colWidths=[col_w, col_w], repeatRows=0)
    tbl.setStyle(TableStyle(styles_cmds))
    story.append(tbl)
    return story

def notes_block():
    S = make_styles()
    story = [Spacer(1, 0.2*inch)]
    story.append(HRFlowable(width="100%", thickness=1, color=MGRAY))
    story.append(Spacer(1, 0.05*inch))
    story.append(Paragraph("NOTES / DISCREPANCIES", ParagraphStyle('nl',
        fontName='Helvetica-Bold', fontSize=8, textColor=RED)))
    story.append(Spacer(1, 0.06*inch))
    for _ in range(4):
        story.append(HRFlowable(width="100%", thickness=0.5, color=MGRAY, spaceAfter=12))
    story.append(Spacer(1, 0.1*inch))
    # Sign-off line
    sign = Table([['ENGINEER SIGNATURE:', '', 'DATE / TIME:', '']],
                  colWidths=[1.3*inch, 2.5*inch, 1.0*inch, 1.5*inch])
    sign.setStyle(TableStyle([
        ('LINEBELOW',(1,0),(1,0),0.5,MGRAY),
        ('LINEBELOW',(3,0),(3,0),0.5,MGRAY),
        ('FONTNAME',(0,0),(0,0),'Helvetica-Bold'),
        ('FONTNAME',(2,0),(2,0),'Helvetica-Bold'),
        ('FONTSIZE',(0,0),(-1,-1),8),
        ('VALIGN',(0,0),(-1,-1),'BOTTOM'),
        ('BOTTOMPADDING',(0,0),(-1,-1),2),
    ]))
    story.append(sign)
    return story

# ── Vehicle data ──────────────────────────────────────────────────────────────

VEHICLES = {}

# ── ENGINE 61 ─────────────────────────────────────────────────────────────────
VEHICLES['e61'] = {
    'name': 'Engine 61',
    'filename': 'Engine_61_Shift_Rig_Check.pdf',
    'label': 'ENGINE 61 SHIFT RIG CHECK',
    'compartments': [
        ("Front of Engine", [
            "Trash Line — 100ft (Preconnected)",
            "30' of 5\" Hose",
            "Storz to Steamer Connector",
            "Hydrant Wrench",
        ]),
        ("Side / Middle Hose Bay — Cross Lays", [
            "1¾\" Crosslay #1 — 200ft w/Fog Nozzle (Preconnected)",
            "1¾\" Crosslay #2 — 200ft w/Fog Nozzle (Preconnected)",
            "2½\" Crosslay — 200ft w/Smooth Bore Nozzle (Preconnected)",
        ]),
        ("Rear of Engine — Hose Beds", [
            "Left Bay — 600' 3\" + Skid Load 2½\" 150'",
            "Middle Bay — 1000' 5\"",
            "Right Bay — 600' 3\" + Skid Load 1¾\" 150'",
            "Blitz Fire — 300' 3\" (Preconnected)",
            "High-Rise Pack — 150' 1¾\", Fog Nozzle, Gated Wye",
            "High-Rise Bag (2½\" section, 90° connector, T w/gauge, Wye, Vise Grips)",
            "2 Backboards",
        ]),
        ("Comp 1 — Engineer's Compartment (Top Shelf)", [
            "1\" Garden Hose",
            "2 Storz Connectors (1 reducer, 30°)",
            "Deck Gun / Blitzfire Nozzle",
            "Small Utility Flags",
            "Black Tool Box (Grease, Screwdrivers, Pliers, Carb Cleaner, Silicone, Heat Gun, Lube Stick)",
            "Airpack",
        ]),
        ("Comp 1 — Engineer's Compartment (Middle Shelf)", [
            "2 Double Ended Spanners",
            "2 Small Hose Spanners w/Gas Notch",
            "2 Gated Wye Ball Valves (2½\" to 1½\")",
            "2 Fog Nozzles",
            "2 Small Reducers",
            "Reducer 1¾\" to 1\"",
            "Steamer to Storz",
            "Smooth Bore Nozzle",
            "Yellow Tip Fog Nozzle",
            "6× 2½\" Connectors (2 F2F, 2 M2M, 2 CFD)",
            "6× 1¾\" Connectors (2 F2F, 2 M2M, 2 CFD)",
            "4 Reducers 2½\"F to 1¾\"M",
            "Cap for 1¾\"",
        ]),
        ("Comp 1 — Engineer's Compartment (Bottom Shelf)", [
            "Hydrant Bag (2 Wrenches, 2 Storz-Steamer, 2 Spanners, 2 Wedges, 1¾\" Gate Valve, Storz-1¾\"F, 3 Double Spanners, Mallet, Pipe Wrench, Rope)",
            "25' of 5\" Hose",
        ]),
        ("Comp 2 — Driver Side Middle", [
            "Closet Pike Pole (D Handle)",
            "Maul",
            "Halligan",
            "Flat Head Axe",
            "Medium Bolt Cutter w/Barbed Wire Hook",
            "Large Bolt Cutter",
            "Captain's Tool / Pry Axe (Driver Side Over Wheel — E61 specific)",
            "Manhole Cover Remover",
            "K Tool in Leather Case",
            "3 Air Tanks (Over Tire)",
        ]),
        ("Comp 3 — Driver Side Rear", [
            "Top: Cellar Nozzle on Cellar Pipe",
            "Middle: 2 Battery-Powered Portable Work Lights",
            "Bottom: Small Step Ladder",
            "Bottom: Ventilation Fan (confirm plugged in)",
            "Bottom: Yellow Box w/Air Bag Controls",
            "Bottom: 3 Air Bags",
            "Bottom: Plastic Cribbing",
            "Bottom: Transformer Nozzles",
        ]),
        ("Rear of Truck — Left Side", [
            "2 New York Hooks (6ft, 8ft)",
            "Attic Ladder 10ft",
        ]),
        ("Rear of Truck — Middle", [
            "Upper: 6 Batteries",
            "Upper: Battery-to-AC Connector",
            "Mid: Hydraulic Ram",
            "Mid: Quick Kick Ram Support",
            "Mid: Reciprocating Saw",
            "Mid: 2 Double Ended Spanners",
            "Mid: Window Punch",
            "Bottom: Hurst Rescue Cutter",
            "Bottom: Hurst Rescue Spreader",
        ]),
        ("Comp 5 — Passenger Side Rear", [
            "Top: Flat Head Axe",
            "Top: Halligan",
            "Top: Crowbar (E61 specific)",
            "Top: Pick Head Axe / Fire Axe",
            "Mid: 100' Utility Rope",
            "Mid: Pig Drain Cover",
            "Mid: RASP 200' Search Rope",
            "Bottom: Red Bag (4 PFDs, 1 Throw Preserver)",
            "Bottom: W-Tool",
            "Bottom: Tool Box (Screwdrivers, Socket Wrench, Hacksaw, Pliers, etc.)",
        ]),
        ("Comp 6 — Passenger Side Middle", [
            "Water Helmet",
            "PFD",
            "Mustang Suit",
            "Rope Throw Bag",
            "Life Safety Ring",
            "Strap w/3 Carabiners",
            "Ice Spikes (for hands)",
            "Ice Cleats",
            "Under Comp: 4 Air Bottles (2 per side)",
        ]),
        ("Comp 7 — Passenger Side Front", [
            "Silver Bullet (Pressurized Water)",
            "ABC Dry Chemical Extinguisher",
            "CO2 Extinguisher",
            "K Extinguisher",
            "Oil Dry / Kitty Litter",
            "Fire Blanket (Electric Vehicles)",
        ]),
        ("Above Compartments", [
            "2 Pike Poles (6ft, 8ft)",
            "Extension Ladder 24ft",
            "Roof Ladder 14ft",
        ]),
        ("Inside Cab — Top Shelf", [
            "Binoculars",
            "LOTO Bag",
            "Pet O2 Mask",
            "2 Extra SCBA Masks",
            "After-Fire Survey Clipboard",
            "Patient Clipboard",
            "Fire Tape",
            "Caution Tape",
            "Red Bio Hazard Bags",
            "Camera",
            "FIU Investigation Box",
            "PR Box / Stickers",
        ]),
        ("Inside Cab — Middle Shelf", [
            "Red Jump Bag (First In)",
            "Green Airway Bag",
            "Dark Blue Collar Bag",
            "Orange Suction Bag",
            "AED",
        ]),
        ("Inside Cab — Third Shelf", [
            "CO Meter (4-Gas: O2, CO, H2S, Combustible Gas)",
            "Methane Meter / Gas Trac",
            "HCN Meter",
            "CO2 Meter",
            "Hot Stick",
            "Contractor Bags",
            "Fire Wipes",
        ]),
        ("Inside Cab — Bottom Shelf", [
            "Flood Light",
            "Wipes",
            "Hot Feet",
            "Blankets",
            "Contractor Bags",
        ]),
        ("Inside Cab — Also", [
            "Vests (under seats)",
            "Water",
            "4 Radios",
            "Elevator Key",
            "Knoxbox Key",
            "ERG",
            "Accountability Velcro Name Board",
        ]),
        ("Top of Engine", [
            "Snow Shovel",
            "1\" Garden Hose",
            "Traffic Cones",
            "Fire Swatter / Paddle",
            "Manifold for Fire Gun",
            "Dawn Soap & Brush in Bucket",
        ]),
    ]
}

# ── ENGINE 62 ─────────────────────────────────────────────────────────────────
VEHICLES['e62'] = {
    'name': 'Engine 62',
    'filename': 'Engine_62_Shift_Rig_Check.pdf',
    'label': 'ENGINE 62 SHIFT RIG CHECK',
    'compartments': [
        ("Front of Engine", [
            "Trash Line — 100ft (Preconnected)",
            "5\" Hose — 30ft",
            "Gate Valve",
            "Storz to Steamer Connector",
            "Hydrant Wrench",
        ]),
        ("Side / Middle Hose Bay — Cross Lays", [
            "1¾\" Crosslay #1 — 200ft w/Fog Nozzle (Preconnected)",
            "1¾\" Crosslay #2 — 200ft w/Fog Nozzle (Preconnected)",
            "2½\" Crosslay — 200ft w/Smooth Bore Nozzle (Preconnected)",
        ]),
        ("Rear of Engine — Hose Beds", [
            "Left Bay — 600' 3\" + Skid Load 2½\" 150'",
            "Middle Bay — 1000' 5\"",
            "Right Bay — 600' 3\" + Skid Load 1¾\" 150'",
            "Blitz Fire — 300' 3\" (Preconnected)",
            "High-Rise Pack 150' 1¾\" w/Gated Wye",
            "High-Rise Bag (2½\" section, 90° connector, T w/gauge, Vise Grips)",
            "2 Backboards",
        ]),
        ("Comp 1 — Engineer's Compartment (Top Shelf)", [
            "1\" Garden Hose",
            "2 Storz Connectors (1 reducer, 30°)",
            "Deck Gun / Blitzfire Nozzle",
            "Small Utility Flags",
            "Black Tool Box (Grease, Screwdrivers, Pliers, Carb Cleaner, Silicone, Heat Gun, Lube Stick)",
            "Airpack",
        ]),
        ("Comp 1 — Engineer's Compartment (Middle Shelf)", [
            "2 Double Ended Spanners (Storz and Hose)",
            "2 Small Hose Spanners w/Gas Notch",
            "2 Gated Wye Ball Valves (2½\" to 1½\")",
            "2 Fog Nozzles",
            "2 Small Reducers",
            "Reducer 1¾\" to 1\"",
            "Steamer to Storz",
            "Smooth Bore Nozzle",
            "Yellow Tip Fog Nozzle",
            "6× 2½\" Connectors (2 F2F, 2 M2M, 2 CFD)",
            "6× 1¾\" Connectors (2 F2F, 2 M2M, 2 CFD)",
            "4 Reducers 2½\"F to 1¾\"M",
            "Cap for 1¾\"",
        ]),
        ("Comp 1 — Engineer's Compartment (Bottom Shelf)", [
            "Hydrant Bag (2 Wrenches, 2 Storz-Steamer, 2 Spanners, 2 Wedges, 1¾\" Gate Valve, 3 Double Spanners, Mallet, Pipe Wrench, Rope)",
            "25' of 5\" Hose",
        ]),
        ("Comp 2 — Driver Side Middle", [
            "Closet Pike Pole (D Handle)",
            "Maul",
            "Halligan",
            "Flat Head Axe",
            "Medium Bolt Cutter w/Barbed Wire Hook",
            "Large Bolt Cutter",
            "Air Bag (sometimes both here)",
            "Manhole Cover Remover",
            "K Tool in Leather Case",
            "3 Air Tanks (Over Tire — E62 specific)",
        ]),
        ("Comp 3 — Driver Side Rear", [
            "Top: RIT Pack (6ft Hose, Extra SCBA, UCA/Buddy Connectors, 60min 4500 psi)",
            "Mid: 2 Portable Work Lights",
            "Mid: Cellar Nozzle on Cellar Pipe",
            "Bottom: Small Step Ladder",
            "Bottom: Ventilation Fan (confirm plugged in / charging)",
            "Bottom: Orange Box w/Air Bag Controls",
            "Bottom: 2 Air Bags (max 118 PSI)",
            "Bottom: Plastic Cribbing",
            "Bottom: Transformer Nozzles",
        ]),
        ("Rear of Truck — Left Side", [
            "2 New York Hooks (6ft, 8ft)",
            "Attic Ladder 10ft",
        ]),
        ("Rear of Truck — Middle", [
            "Upper: 6 Batteries",
            "Upper: Battery-to-AC Connector",
            "Mid: Hydraulic Ram",
            "Mid: Quick Kick Ram Support",
            "Mid: Battery-Powered Reciprocating Saw",
            "Mid: 2 Double Ended Spanners",
            "Mid: Window Punch",
            "Bottom: Hurst Rescue Cutter",
            "Bottom: Hurst Rescue Spreader",
        ]),
        ("Comp 5 — Officer Side Rear", [
            "Top: Flat Head Axe",
            "Top: Halligan",
            "Top: Pig Axe",
            "Top: Pick Head Axe / Fire Axe",
            "Mid: 100' Utility Rope",
            "Mid: Pig Drain Cover",
            "Mid: RASP 200' Search Rope",
            "Bottom: Red Bag (4 PFDs, 1 Throw Preserver)",
            "Bottom: W-Tool",
            "Bottom: Tool Box (Screwdrivers, Socket Wrench, Duct Tape, Pliers, etc.)",
        ]),
        ("Comp 6 — Officer Side Middle", [
            "Water Helmet",
            "PFD",
            "Mustang Suit",
            "Rope Throw Bag",
            "Life Safety Ring",
            "Strap w/3 Carabiners",
            "Under Comp: 4 Air Bottles",
        ]),
        ("Comp 7 — Officer Side Front", [
            "Silver Bullet (Pressurized Water)",
            "ABC Dry Chemical Extinguisher",
            "CO2 Extinguisher",
            "K Extinguisher",
            "Oil Dry / Kitty Litter",
            "Fire Blanket (Electric Vehicles)",
        ]),
        ("Above Compartments", [
            "2 Pike Poles (6ft, 8ft)",
            "Extension Ladder 24ft",
            "Roof Ladder 14ft",
        ]),
        ("Inside Cab — Top Shelf", [
            "Binoculars",
            "LOTO Bag",
            "Pet O2 Mask",
            "2 Extra SCBA Masks",
            "After-Fire Survey Clipboard",
            "Patient Clipboard",
            "Fire Tape",
            "Caution Tape",
            "Red Bio Hazard Bags",
        ]),
        ("Inside Cab — Middle Shelf", [
            "Red Jump Bag (First In)",
            "Green Airway Bag",
            "Dark Blue Collar Bag",
            "Orange Suction Bag",
            "Yellow AED",
        ]),
        ("Inside Cab — Third Shelf", [
            "CO Meter (4-Gas: O2, CO, H2S, Combustible Gas)",
            "Methane Meter / Gas Trac",
            "HCN Meter",
            "CO2 Meter",
            "Hot Stick",
            "Contractor Bags",
            "Fire Wipes",
        ]),
        ("Inside Cab — Bottom Shelf", [
            "Flood Light",
            "Wipes",
            "Hot Feet",
            "Blankets",
            "Contractor Bags",
        ]),
        ("Inside Cab — Also", [
            "Vests (under seats)",
            "Water",
            "4 Radios",
            "Elevator Key",
            "Knoxbox Key",
            "ERG",
            "Accountability Velcro Name Board",
        ]),
        ("Top of Engine", [
            "Snow Shovel",
            "1\" Garden Hose",
            "Traffic Cones",
            "Fire Paddle",
            "Manifold for Fire Gun",
            "Dawn Soap & Brush in Bucket",
        ]),
    ]
}

# ── ENGINE 60 ─────────────────────────────────────────────────────────────────
VEHICLES['e60'] = {
    'name': 'Engine 60',
    'filename': 'Engine_60_Shift_Rig_Check.pdf',
    'label': 'ENGINE 60 SHIFT RIG CHECK',
    'compartments': [
        ("Front of Engine", [
            "100' 1¾\" Trash Line",
            "No Intake",
        ]),
        ("Engineer's Compartment (Left Top Shelf)", [
            "Towels",
            "30° Storz",
            "Pickup Tubes for Foam/Gel",
            "Reducers",
            "Duct Tape",
        ]),
        ("Engineer's Compartment (Top Right Shelf)", [
            "SCBA",
            "Extra Air Bottle",
        ]),
        ("Engineer's Compartment (Middle Shelf)", [
            "Foam Nozzle 125 GPM (Orange)",
            "Gated Wye",
            "2 Fog Nozzles",
            "Rope to Move Charged 5\" Hose",
            "Adaptors (M2M, F2F, CFD, 2½\"-1¾\")",
        ]),
        ("Engineer's Compartment (Bottom Shelf)", [
            "Eye Protection",
            "Chief Eductor",
            "Hydrant Bag",
            "Gate Valve",
            "25' of 5\"",
            "Smooth Bore Nozzles",
        ]),
        ("Middle Compartment — Driver Side", [
            "3 Air Tanks",
            "Fire Tape",
            "Deck Gun Ground Mount",
            "Fan Hanger",
            "Piercing Nozzle",
            "Halligan",
            "Pickhead / Fire Axe",
            "Flat Head Axe",
            "Deck Gun Nozzle",
            "Halligan with Roof Ring",
            "Red Pickhead Axe",
            "Sledge Hammer",
            "Officers Tool / Pry Axe",
            "K Tool",
            "Cellar Nozzle",
            "Quartz Light (on side of engine — verify present)",
        ]),
        ("Rear Compartment — Driver Side", [
            "200' Roll Electrical Cord",
            "10KW Generator",
            "B Post Cover",
            "Plug-in Lights",
            "Duct Tape",
            "Sawzall",
            "Extension Cord",
            "Cribbing",
            "Small Step Ladder",
            "Ventilation Fan",
            "Plug Adaptors (110V)",
        ]),
        ("First Compartment — Passenger Side (Top Shelf)", [
            "Akron Coping Tool / Hose Hoist",
            "2× 150' Utility Rope Bags",
            "Spare Battery",
        ]),
        ("First Compartment — Passenger Side (Middle Shelf)", [
            "Cynch Collar Life Vest / Horse Collar",
            "Mustang Suit",
            "Water Helmet",
            "Water Rescue Rope",
        ]),
        ("First Compartment — Passenger Side (Bottom Shelf)", [
            "Manual Pump Can",
            "Gel Foam",
            "Oil Dry",
            "Traffic Cones",
            "Life Vests",
            "50' of 5\"",
        ]),
        ("Middle Compartment — Passenger Side", [
            "Small Bolt Cutter",
            "Pig Axe Tool",
            "Sledge Hammer",
            "Pick Head / Fire Axe",
            "Halligan",
            "Flat Head Axe",
        ]),
        ("Rear Compartment — Passenger Side", [
            "Tarps",
            "Blanket",
            "High-Rise Pack 150' w/Fog Nozzle and Gated Wye",
            "Silver Bullet",
            "ABC Extinguisher",
            "CO2 Extinguisher",
            "High-Rise Bag",
            "Tool Box",
            "Oil Dry / Kitty Litter",
            "2 Shovels",
            "Decontamination Buckets and Soap",
        ]),
        ("Rear of Engine — Middle Compartment", [
            "10ft Folding Ladder",
            "24ft Extension Ladder",
            "14ft Roof Ladder",
            "2 Backboards",
            "Pry Tool",
            "Pry Bar",
            "Hurst Combi Tool (cuts and spreads)",
            "Ram Jam / Support Brace",
            "2 Shovels (Scoop + Pointed)",
            "Braces for Ram Tool",
        ]),
        ("Top of Ladder Compartment", [
            "6' Pike Pole",
            "6' Pike Pole",
        ]),
        ("Rear Hose Bays", [
            "1000' 5\" LDH",
            "150' 2½\" Skid Load w/Smooth Bore Nozzle (connected to 400' of 3\")",
            "150' 1¾\" Skid Load w/Breakaway Fog Nozzle (connected to 550' of 3\")",
        ]),
        ("Middle Cross Lays", [
            "1¾\" Crosslay #1 — 200ft (Preconnected)",
            "1¾\" Crosslay #2 — 200ft (Preconnected)",
        ]),
        ("Cab Compartment", [
            "AED",
            "4-Gas Meter",
            "Gas Trac",
            "Water Bottles",
            "OB Kit",
            "Caution Tape",
            "Fire Wipes",
            "Vests",
            "Extra Gloves",
            "Hot Stick",
            "Knox Box Key",
            "Medic Bag",
            "Battery Chargers",
            "TIC",
            "2 Face Pieces (L and M)",
        ]),
    ]
}

# ── ENGINE 63 ─────────────────────────────────────────────────────────────────
VEHICLES['e63'] = {
    'name': 'Engine 63',
    'filename': 'Engine_63_Shift_Rig_Check.pdf',
    'label': 'ENGINE 63 SHIFT RIG CHECK',
    'compartments': [
        ("Front of Engine", [
            "50' of 5\" Hose (different from other engines)",
            "Gate Valve (attached to top of bumper)",
            "Hydrant Wrench (attached to top of bumper)",
            "Storz to Steamer Connector",
        ]),
        ("Comp 1 — Engineer's Compartment (Top Shelf)", [
            "Eye Protection",
            "Fog Nozzle",
            "Deck Gun Nozzle",
            "Double Ended Spanners",
            "Gated Wye Valve",
            "M2M, F2F, CFD, Reducer Adaptors",
        ]),
        ("Comp 1 — Engineer's Compartment (Middle Shelf)", [
            "Storz to Steamer",
            "Storz to 1½\"",
            "30° Elbow Storz (anti-kink)",
            "Hydrant Bag (Gate Valve, Hydrant Wrench, Pipe Wrench, Rope/Hook, 2 Small Spanners, 2 Double Spanners, Storz-Steam Connectors, Storz Reducer, CFD Coupler, Rubber Mallet)",
        ]),
        ("Comp 1 — Engineer's Compartment (Bottom Shelf)", [
            "Chief Eductor 125 GPM",
            "2-Person Hose Roller (to remove air from 5\" hose)",
            "5\" LDH 30'",
        ]),
        ("Middle Compartment — Driver Side", [
            "Pick Axe",
            "Flat Head Axe",
            "Sledge Hammer",
            "Halligan",
            "K Tool",
            "Officers Tool",
        ]),
        ("Rear Compartment — Driver Side", [
            "Halligan",
            "Flat Head Axe",
            "Sledge Hammer",
            "Pick Axe",
            "Silver Bullet (Pressurized Water Can)",
            "Manual Pump Can",
            "ABC Extinguisher",
            "Small Step Ladder",
        ]),
        ("Front Compartment — Passenger Side", [
            "Akron Brass Hose Hoist / Coping Tool",
            "High-Rise Bag (6\" 2½\" Hose, 90° Coupling, Pressure Gauge, Vise Grips, Spanner)",
            "50' of 5\"",
        ]),
        ("Middle Compartment — Passenger Side", [
            "High-Rise Pack w/Gated Wye — 150' of 1¾\"",
            "Bolt Cutters",
        ]),
        ("Rear Compartment — Passenger Side", [
            "Tool Box",
            "Traffic Cones",
            "Tarps",
            "Blanket",
            "Fan Hanger",
        ]),
        ("Rear of Engine — Middle Compartment", [
            "Bucket w/Dawn Soap & Brush (Decontamination)",
            "Garden Hose",
            "Hurst Combi Tool (cuts and spreads)",
            "2 Shovels (Scoop + Pointed)",
        ]),
        ("Rear — Right Side", [
            "6' Pike Pole",
            "8' New York Hook",
            "10' New York Hook",
        ]),
        ("Rear — Left Side", [
            "6' Pike Pole",
            "8' Pike Pole",
            "10' Pike Pole",
        ]),
        ("Rear Hose Bays", [
            "1000' 5\" Hose",
            "150' 2½\" Skid Load w/Smooth Bore Nozzle (connected to 400' of 3\")",
            "150' 1¾\" Skid Load w/Breakaway Fog Nozzle (connected to 500' of 3\")",
        ]),
        ("Middle Cross Lays", [
            "1¾\" Crosslay #1 — 200ft",
            "1¾\" Crosslay #2 — 200ft",
        ]),
        ("Middle Compartments — Foam/Gel", [
            "95 GPM Nozzle",
            "95 GPM Eductor",
            "5× 5-Gal Eco Gel Buckets",
            "Eductor w/Pickup Tube",
            "Foam Aeration Tube",
            "Pickup Tube for Chief Eductor",
            "Foam Nozzle (75 PSI, 125 GPM)",
            "Oil Dry / Kitty Litter",
        ]),
        ("Top of Engine — Ladders", [
            "28' Extension Ladder",
            "16' Roof Ladder",
            "10' Folding / Attic Ladder",
        ]),
        ("Cab Compartment", [
            "AED",
            "4-Gas Meter",
            "Gas Trac",
            "HCN Meter",
            "Water Bottles",
            "SCBA Air Pack",
            "Knox Box Key",
        ]),
        ("Top of Engine", [
            "Foam / Gel",
            "Manifold",
        ]),
    ]
}

# ── UTILITY 61 ────────────────────────────────────────────────────────────────
VEHICLES['u61'] = {
    'name': 'Utility 61',
    'filename': 'Utility_61_Shift_Rig_Check.pdf',
    'label': 'UTILITY 61 SHIFT RIG CHECK',
    'compartments': [
        ("Glove Compartment", [
            "Maps",
            "Truck Loading Instruction Paper",
            "Patient Prepare Reports (Blank)",
            "Vehicle Name Laminate",
            "Spare Tire Lock Key (in bag)",
            "Road Flares (2×)",
            "Tag Velcro / Passport Accountability System",
        ]),
        ("Front Passenger Door", [
            "Tape Measure",
        ]),
        ("Driver's Door", [
            "Roadway Vest (×1)",
        ]),
        ("Front Seat Bench Compartment", [
            "MDT (Mobile Data Terminal)",
            "2 Map Binders (including apartments folder)",
            "Maintenance QR Code",
            "Insurance QR Code",
            "Fuel Key",
            "Prairie Path Key",
            "Knox Box Key (on wooden stick)",
            "Key Tags (blank)",
            "Gas Filling Instructions",
            "Nitrile Gloves",
            "Do Not Cross Tape",
            "Fire Tape",
            "Vehicle Owner's Manual",
        ]),
        ("Back Seat", [
            "2 Portable Officer Radios in Holsters (Green)",
            "AED w/Pocket Mask (screen should show Green)",
            "FIU Tub (Tape Measure, Folders)",
            "Standing Medical Orders Binder",
            "Glen Ellyn FD Med Log Binder",
            "Grey Clipboard (Patient Notes)",
            "Box Light (Orange)",
            "Nitrile Gloves",
            "OB Bag (Obstetrics)",
            "Snow Brush",
        ]),
        ("Back Left Door", [
            "Duct Tape (2 rolls)",
            "Post-It Notes",
        ]),
        ("Truck Bed — Tools", [
            "Halligan (Adze, Pick, Fork)",
            "Flat Head Axe",
            "Closet Pike Pole (D Handle)",
            "AC Hot Stick",
            "3 Umbrellas",
            "Shovel",
            "Jumper Cables (Red +, Black −)",
            "Measuring Wheel",
            "PPE Masks",
            "SuppressAll Unit / Gas Grenade",
            "Hydrant Wrench",
            "Blanket",
            "ABC Extinguisher",
        ]),
        ("Truck Bed — Medical Packs", [
            "Red Jump Pack (First In / Trauma: Shears, Glucose, Narcan, BP Cuff, Splints, Tourniquet, PPE)",
            "Green Airway Pack (O2 Tank, AMBU Mask, BVM, Intubation Tubes, Suction, Nasal Cannula)",
            "Red Bag w/Black Zipper (Throw Rope, Life Preserver Vest)",
            "Black MSA Case (SCBA, Air Bottle, Face Piece)",
            "ABC Dry Chem Extinguisher",
            "Blue Cervical-Collar Bag (Neck Braces, Foam Head-Locks, Triage Bag, Traction Straps)",
        ]),
        ("ERG Book", [
            "Emergency Response Guidebook (verify current edition)",
        ]),
    ]
}

# ── UTILITY 62 ────────────────────────────────────────────────────────────────
VEHICLES['u62'] = {
    'name': 'Utility 62',
    'filename': 'Utility_62_Shift_Rig_Check.pdf',
    'label': 'UTILITY 62 SHIFT RIG CHECK',
    'compartments': [
        ("Glove Compartment", [
            "Maps",
            "Truck Loading Instruction Paper",
            "Patient Prepare Reports (Blank)",
            "Vehicle Name Laminate",
            "Spare Tire Lock Key (in bag)",
            "Road Flares (2×)",
            "Passport Accountability System",
            "ERG / Emergency Response Handbook",
        ]),
        ("Front Passenger Side", [
            "Roadway Vest (×1)",
        ]),
        ("Back Seat", [
            "Sterile Gloves and Masks",
            "2 Radios",
            "Vests",
            "Ice Scraper",
        ]),
        ("Truck Bed — MSA Case", [
            "Air Bottle",
            "SCBA",
            "SCBA Face Piece Size M",
        ]),
        ("Truck Bed — Milk Crate", [
            "Jumper Cables",
            "Wheel Chocks",
            "Caution Tape",
            "Receiver and Hitch Ball",
        ]),
        ("Truck Bed — Gray Bin (Black Top)", [
            "4 Waders",
            "14\" Inner Tube",
            "100 lb Lift Bag (Underwater Recovery)",
            "250 lb Lift Bag (Underwater Recovery)",
            "PFD",
        ]),
        ("Truck Bed — Other", [
            "Orange Square Bag (Blanket)",
            "Black Bag (Flood Light, Flood Light Stand, Dewalt Battery)",
            "Orange/Red Bag w/White Trim (1 PFD, Throw Bag)",
            "Rope Spool — 600'",
            "ABC Fire Extinguisher",
            "Sked (Foldable Stretcher)",
        ]),
        ("Truck Bed — Tools", [
            "2 Pike Poles",
            "Halligan",
            "Flat Head Axe",
            "Umbrella",
            "Snow Scraper",
        ]),
        ("Truck Bed — Misc", [
            "Water Bottles",
            "Spare Dewalt Batteries",
        ]),
    ]
}

# ── BRUSHTRUCK 62 ─────────────────────────────────────────────────────────────
VEHICLES['bt62'] = {
    'name': 'Brushtruck 62',
    'filename': 'Brushtruck_62_Shift_Rig_Check.pdf',
    'label': 'BRUSHTRUCK 62 SHIFT RIG CHECK',
    'compartments': [
        ("Front Seat", [
            "Radio (confirm charged and on correct channel)",
        ]),
        ("Glove Box", [
            "ERG Book (verify current edition)",
            "Bug Spray",
            "Fuel Key",
            "Water Guides / Water Source Maps",
        ]),
        ("Back Seat", [
            "PFD (Personal Flotation Device) — inspect for integrity",
            "Hot Stick",
            "Box Light / Big Flashlight (confirm charged)",
            "Hose Bag with Garden Hose",
        ]),
        ("Container — Back Seat", [
            "Small 1\" Hose Section",
            "Utility Strap",
            "Towel",
            "Safety Vest (Hi-Viz)",
            "Maps",
            "Duct Tape",
            "Caution Tape",
            "Garbage Bags",
            "Public Education Materials / Stickers",
        ]),
        ("Rear — Water System", [
            "250-Gallon Water Tank (confirm full)",
            "200' 1\" Hose on Reel (inspect reel wind)",
            "Hose Reel Handle",
            "Hard Suction Hose — 2× 12' sections",
            "Metal Strainer / Filter for Suction",
            "Metal Wheel Chock",
            "Plastic Gas Tank (confirm fuel level)",
            "2½\" Hose — 50' Section",
            "1½\" Hose — 150' Roll (Cross Lay)",
            "Fog Nozzle",
        ]),
        ("Rear — Hand Tools", [
            "Brush Paddles — 3 total",
            "Pike Poles — 2 total",
            "New York Pole",
            "Bolt Cutters",
            "Halligan Bar",
            "Plastic Funnel",
        ]),
        ("Water Pump", [
            "Portable Gas Pump (2½\" Inlet / 1½\" Outlet)",
            "Fuel level checked",
            "Oil level checked",
        ]),
        ("Hydrant Bag", [
            "Gate Valve",
            "1\" Garden Hose",
            "Hydrant Wrench",
            "Small Spanner Wrench (1¾\")",
            "Large Spanner Wrench (5\" LDH)",
            "Black Electrical Tape",
            "Steamer-to-Storz Adaptor",
            "2½\" Storz Adaptors (Male and Female)",
            "Pipe Wrench",
        ]),
    ]
}

# ── SQUAD 61 ─────────────────────────────────────────────────────────────────
VEHICLES['sq61'] = {
    'name': 'Squad 61',
    'filename': 'Squad_61_Shift_Rig_Check.pdf',
    'label': 'SQUAD 61 SHIFT RIG CHECK',
    'compartments': [
        ("Driver Side Front Compartment", [
            "Light Tower Controller",
            "Fire Investigation Box",
            "Wet Vac",
            "Dust/Particulate Face Mask",
        ]),
        ("Driver Side Traverse — Bottom Shelf", [
            "Winch",
            "Remote for Winch",
            "Steering Wheel Cutter",
        ]),
        ("Driver Side Comp 3 — Over Wheel (Top Shelf)", [
            "Circular Saw",
            "K12 Saw",
            "Chainsaw",
            "Chain Oil",
        ]),
        ("Driver Side Comp 3 — Over Wheel (Bottom Shelf)", [
            "\u00bd\" Impact Wrench",
            "\u00bc\" Impact Wrench with Bits",
            "Angle Grinder",
            "Reciprocating Saw (Metal and Wood Blades)",
            "Blades",
            "Charger",
            "Bits",
        ]),
        ("Driver Side Rear Cabinet — Air Cascade", [
            "Cascade Controls",
            "Adaptors (Air Reel, Scuba, Boom Fill)",
            "Towel",
            "Quick Connect for SCBA",
            "O-Rings",
            "Air Hose for SCBA Filling",
            "Power Cord (from Generator)",
        ]),
        ("Officer Front Compartments", [
            "Little Giant Ladder",
            "Tarps",
            "Step Cribbing / Chocks",
            "Cribbing Platforms",
            "Oil Dry",
            "Garbage Container",
        ]),
        ("Transverse — Officer Side Shelf", [
            "Hurst Ram Tool",
            "Hurst Cutter",
            "Hurst Spreader",
            "B-Post Tool",
        ]),
        ("Transverse — Long Shelf", [
            "2 Akron Lights",
            "2 High Lift Jacks / Farmer Jacks",
            "4 Traffic Cones",
            "4 Res-Q-Jacks",
            "2 Scissor Jacks",
            "Air Chisel",
            "2 Buckets (Tow Hooks and Chain)",
            "RIT Airpack",
            "Window Punch",
            "Dayton Submersible Pump",
            "Road Salt",
            "2 Bolt Cutters (1 Large, 1 Small)",
            "2 Life Safety Rope Bags — 200' (Red & Blue)",
        ]),
        ("Officer Side — Over Wheel (Front)", [
            "Flat Head Axe",
            "Halligan",
            "Sledgehammer",
            "2 Closet Pikes",
            "Pick Axe",
        ]),
        ("Officer Side — Over Wheel (Rear)", [
            "Rigging Kit",
            "Arizona Vortex (Blue Bag)",
            "Air Bag Controller",
        ]),
        ("Officer Side Rear — Top Shelf", [
            "Plasma Torch Face Shield",
            "Welding Gloves",
            "Plasma Torch IR/UV Safety Glasses",
            "Rescue Blanket",
            "Wool Blanket",
            "Metric and Standard Open End Wrenches",
        ]),
        ("Officer Side Rear — Right Side", [
            "More Cribbing and Wedges",
            "Ratchet Straps",
        ]),
        ("Officer Side Rear — Left Side", [
            "Toolbox with SAE & Metric Wrenches",
            "Standard Toolbox",
            "Socket Sets",
        ]),
        ("Rear Compartment — Top Shelf", [
            "Stokes Basket",
            "Fire Investigation Rake",
            "2x 8\' New York Hooks",
            "6\' New York Hook",
            "6\' Pike Pole",
            "Umbrella",
        ]),
        ("Rear Compartment — Second Shelf", [
            "3 Multi-Lift Air Bags (1 Small, 2 Medium)",
        ]),
        ("Rear Compartment — Left Vertical Shelf", [
            "ABC Fire Extinguisher",
            "CO2 Fire Extinguisher",
            "Silver Bullet (Pressurized Water)",
            "Towel",
            "B-Post Covers",
        ]),
        ("Rear Compartment — Middle Vertical Shelf", [
            "2 Large Multi-Lift Air Bags",
        ]),
        ("Rear Compartment — Right Vertical Shelf", [
            "2 Battery-Powered Smoke Ejectors",
        ]),
        ("Rear Compartment — Bottom Shelf", [
            "Air Bag Controller in Dewalt Bag",
            "Multi-Force Air Bag (Snowman)",
            "6-Pack Dewalt Batteries",
        ]),
        ("Officer Coffin Compartment — Top (Spill)", [
            "Absorbent Pads",
            "Oil Dry",
            "Spill Kit",
            "Oil Pan",
            "Shovels",
        ]),
        ("Driver Coffin Compartment — Top (Water Rescue)", [
            "2 Mustang Suits",
            "2 Horse Collars with Water Rescue Rope",
            "2 Helmets",
            "2 Throw Bags",
            "4 PFDs",
            "Box with Pipe Plugs",
        ]),
        ("Cab — Rear", [
            "3 Dewalt Battery Chargers",
            "3 Hurst Battery Chargers",
            "Hotstick",
            "Gas Trac",
            "4-Gas and Wand (Detector)",
            "AED",
            "2 SCBA Masks (1 Medium, 1 Small)",
            "2 Fire Hoods",
            "Caution Tape",
            "Fire Tape",
            "4 Box Lights",
            "Safety Vests",
            "Fire Wipes",
            "Knox Box",
        ]),
        ("Cab — Front", [
            "Passport System",
            "Box Light",
            "TIC (Thermal Imaging Camera)",
            "Fuel Keys",
            "Safety Flares",
        ]),
    ]
}

# ── TOWER 62 ─────────────────────────────────────────────────────────────────
VEHICLES['t62'] = {
    'name': 'Tower 62',
    'filename': 'Tower_62_Shift_Rig_Check.pdf',
    'label': 'TOWER 62 SHIFT RIG CHECK',
    'compartments': [
        ("Driver Side Front Compartment", [
            "25' of 5\" LDH",
            "Duct Tape",
            "Caution Tape",
        ]),
        ("Cross Lays", [
            "Center Crosslay — 1¾\" 200' w/Fog Nozzle (Preconnected)",
            "Rear Crosslay — 1¾\" 200' w/Fog Nozzle (Preconnected)",
            "Front Crosslay — 2½\" 200' w/Smooth Bore Nozzle (Preconnected)",
        ]),
        ("Driver Side Front Middle Compartment", [
            "Gated Wye",
            "Storz Connectors",
            "Female/Female Adaptors",
            "Male-to-Male Adaptor",
            "Storz Reducer",
            "Intake Cap with Chain",
            "Angled Connectors",
            "High-Rise Pack (150' 1¾\" Hose, Gated Wye, Shoulder Carry Pack)",
            "High-Rise Bag (Short 2½\", Pressure Meter T, Elbow Connector, Vise Grips)",
            "2 Fog Nozzles",
            "Hydrant Bag (Wrench, Spanners, Mallet, Gate Valve, Storz Connectors, LDH Rope)",
            "K-12 Blades",
        ]),
        ("Driver Side Rear Middle Compartment", [
            "Dewalt Sawzall",
            "Angle Grinder",
            "Chainsaw with Roof Guide",
            "K12 Rotary Saw",
            "Chain Lube",
            "Fuel for K12 / Chainsaw",
            "Tool Kit for Chainsaw",
            "Small Spanners",
            "Hydrant Wrench",
            "O-Rings for Hose Swivel",
        ]),
        ("Driver Side Rear Compartment — SCBAs", [
            "3 SCBAs",
            "RIT Pack",
            "RASP Rope Line",
        ]),
        ("Driver Side Rear Compartment — Generator", [
            "30 Amp Generator",
            "200' Electrical Cable",
            "Extension Cords",
            "Plug Adaptors",
            "Fan",
            "Road Salt",
            "Safety Harness for Tower Climbing",
        ]),
        ("Rear Engine Compartment", [
            "3\" 350' Hose",
            "5\" 250' Hose",
            "2× 35' 2-Section Extension Ladders",
            "28' 2-Section Extension Ladder",
            "2× 20' Roof Ladders",
            "16' Roof Ladder",
            "12' Pike Pole",
            "10' Pike Pole",
            "2× 8' Pike Poles",
            "2× 6' Pike Poles",
            "10' Folding Ladder",
            "12' Folding Ladder",
            "5 New York Hooks",
            "2 Dry Wall Hooks",
        ]),
        ("Officer Side Rear Compartment", [
            "Road Sand",
            "Fan with Cord (Smoke Ejector)",
            "30 Amp Generator",
            "200' Power Cord",
            "Extension Cords",
            "Plug Adaptors",
        ]),
        ("Officer Side Rear Middle Compartment", [
            "Dewalt Powered Fan",
            "2× 150' Utility Rope",
            "130' Utility Rope",
        ]),
        ("Officer Side Middle Compartment", [
            "2× Flat Head Axes",
            "2× Haligans",
            "2× Pick Axes",
            "2× Sledge Hammers",
            "4× Shovels",
            "K Tool",
            "Bolt Cutters",
        ]),
        ("Officer Side Front Middle Compartment", [
            "2× Closet Pike (D Handle)",
            "Fire Maul",
            "Pig Axe",
            "Pry Bar",
            "Long Pry Bar",
            "Large Bolt Cutters",
            "Large Scene Light",
        ]),
        ("Officer Side Front 2 Middle Compartment", [
            "Tarps",
            "Wet Vac",
            "Portable Lights",
            "Tool Box",
            "Submersible Pump",
        ]),
        ("Officer Side Front Compartment", [
            "Hose Hoist",
            "Silver Bullet (Pressurized Water Extinguisher)",
            "Pump Can",
            "CO2 Extinguisher",
            "ABC Extinguisher",
        ]),
        ("Inside Cab", [
            "Caution Tape",
            "Spare Batteries",
            "Water Bottles",
            "AED",
            "Clear Plastic Box (Sterile Gloves, N95, Eye Protection, Gowns, Bio Bags)",
            "Extra SCBA Mask Size M",
            "TIC (Thermal Imaging Camera — in Officer's Seat)",
        ]),
        ("Top of Tower", [
            "New York Hook",
            "Roofing Ladder (hooks on both ends)",
        ]),
        ("Coffin Compartment", [
            "Stokes Basket",
        ]),
        ("Bucket Contents", [
            "Pick Axe",
            "Master Stream Nozzle",
            "Halligan",
        ]),
        ("Bucket Compartment", [
            "2× 50' 1¾\" Hoses",
            "5' 1¾\" Hose",
            "Fog Nozzle",
            "Brackets to Attach Ladder to Bucket",
            "Air Hoses (Direct Connection to Tower Air Supply)",
        ]),
        ("Pivot Compartment", [
            "Chainsaw",
            "K-12",
        ]),
    ]
}


# ── SNORKEL 61 ────────────────────────────────────────────────────────────────
VEHICLES['sn61'] = {
    'name': 'Snorkel 61',
    'filename': 'Snorkel_61_Shift_Rig_Check.pdf',
    'label': 'SNORKEL 61 SHIFT RIG CHECK',
    'compartments': [
        ("Rig Specifications", [
            "75' Aerial",
            "2000 GPM Pump",
            "1000 GPM Waterway",
            "NO Booster Tank",
            "10kW Generator",
            "8 Floodlights",
            "6 Spotlights",
            "5 Driver Side Compartments",
        ]),
        ("Crosslay Hoses", [
            "2× 200' of 1¾\" Hose w/Fog Nozzle",
        ]),
        ("Driver Side Pumping Area", [
            "20 Amp Service",
            "250' of Cord",
        ]),
        ("Driver Side Generator Compartment", [
            "10kW Generator",
        ]),
        ("Driver Side Engineers Compartment", [
            "100' x 2½\" High-Rise Pack w/Smooth Bore Nozzle",
            "150' x 1¾\" High-Rise Pack w/Gated Wye and 150/75 GPM Fog Nozzle",
            "High-Rise Tool Bag",
            "Fog Nozzle (general)",
            "Gated Wye 2½\" to 1½\"",
            "Siamese Adapter 2½\" Female to 5\" Storz",
            "Engineer's Card",
            "Oil Dry",
            "Dry Silicone Spray",
            "Duct Tape",
            "2 Spare Air Bottles",
            "1½\" 60-200 GPM Fog Nozzle",
            "Various Adapters (M-M, F-F, CFD, Garden Hose)",
            "1000 GPM Fog Nozzle for Basket Turret (MISSING per doc)",
            "Steamer to Storz",
            "Steamer to Storz Elbow",
            "Hydrant Bag",
            "Hose Rope",
            "Spanner Wrenches",
            "50' of 5\" Donut Roll",
            "Chair",
        ]),
        ("Driver Side Over The Wheel Compartment", [
            "Flathead Axe",
            "Halligan",
            "Pick Axe",
            "Closet Pike Pole",
            "Sledge Hammer",
            "K-Tool",
        ]),
        ("Driver Side Behind The Wheel Compartment", [
            "Tool Box",
            "Fuel for Chainsaw and K12",
            "2× K12 (1 Metal Blade, 1 Composite Blade)",
            "Chainsaw",
        ]),
        ("Driver Side Second to Last Compartment", [
            "Plastic Tarp",
            "Spare Blade",
            "Black Box with Eye Protection Equipment",
        ]),
        ("Driver Side Rear Compartment", [
            "Climbing Belt for Basket",
            "ABC Fire Extinguisher",
            "Pump Can Extinguisher",
            "Silver Bullet (Pressurized Water)",
            "CO2 Extinguisher",
            "Breather Lines for Basket",
        ]),
        ("Driver Side Ladders", [
            "2× 28' Extension Ladders",
            "2× 16' Roof Ladders (1 stowed in the aerial ladder)",
        ]),
        ("Back of Snorkel — Left (Driver) Side", [
            "1× 5' Pry Bar",
            "1× 5' Pike Pole",
            "1× 8' New York Hook",
            "2× 12' Pike Poles",
            "10' Attic Ladder",
            "2 Scoop Shovels",
        ]),
        ("Back of Snorkel — Right (Officer) Side", [
            "400' of 5\" Hose (Hose Bed)",
            "8' Pike Pole",
            "6' Pike Pole",
            "8' New York Hook",
        ]),
        ("Officers Side Rear", [
            "Smoke Ejector",
            "Electric Adapter",
        ]),
        ("Officers Side Second to Rear", [
            "3× Bags of 150' Utility Rope (NOT rescue-rated)",
        ]),
        ("Officers Side Behind Wheel", [
            "135' of Electrical Cord",
            "Smoke Ejector",
            "3 Air Bottles",
            "Duct Tape",
        ]),
        ("Officers Side Over Wheel — Top Shelf", [
            "Medium Boltcutters",
            "Large Boltcutters",
        ]),
        ("Officers Side Over Wheel — Bottom Shelf", [
            "Flathead Axe",
            "Halligan",
            "Pick Axe",
            "Sledge Hammer",
            "Silver Pick Axe",
            "Roof Shovel",
            "Closet Pike",
            "RASP Rope Bag",
        ]),
        ("Officers Side In Front of Tire", [
            "3 Plug-in Lights",
            "Traffic Cones (9)",
            "Road Salt",
            "Road Sand",
            "Hose Hoist",
        ]),
        ("Officers Side Front Compartment", [
            "2 Canvas Tarps",
        ]),
        ("Cab Compartment", [
            "Safety Vest",
            "Hot Stick",
            "RIT Pack",
            "Sawzall",
            "4-Gas Meter",
            "Gas Trac",
            "Box Lights",
            "Caution Tape",
            "Fire Wipes",
            "Master Stream Control Unit",
            "2 MSA Masks",
            "Surgical Face Masks",
        ]),
        ("On Top / In The Basket", [
            "100' of 1¾\" Hose",
            "Pick Axe",
            "Pike Pole",
            "Roof Ladder",
            "2× 28' Extension Ladders",
            "16' Roof Ladder",
            "In Box — 50' of 1¾\" Hose w/Fog Nozzle",
        ]),
    ]
}



# ── MEDIC 62 ─────────────────────────────────────────────────────────────────
VEHICLES['m62'] = {
    'name': 'Medic 62',
    'filename': 'Medic_62_Shift_Rig_Check.pdf',
    'label': 'MEDIC 62 SHIFT RIG CHECK',
    'compartments': [
        ("Driver Side Front Compartment", [
            "Stair Chair",
            "Oxygen Tank",
        ]),
        ("Middle Cabinet", [
            "Hydrant Bag",
            "Kevlar Vests",
        ]),
        ("Driver Side Rear Cabinet", [
            "Turnout Coat",
            "Turnout Pants",
            "Turnout Boots",
            "Helmet",
        ]),
        ("Officer Side Rear Compartment", [
            "Backboards",
            "Scoop Stretcher",
            "Head Beds",
            "C-Collar Bag",
            "Spider Straps",
            "KED (Kendrick Extrication Device)",
            "Short Boards for Splinting Limbs",
        ]),
        ("Officer Side Front Cabinet", [
            "LUCAS Device (Mechanical CPR)",
        ]),
        ("Inside the Cab", [
            "Verify contents with officer during rig check",
        ]),
        ("Inside the Ambulance — Overhead", [
            "Breathing Bag",
            "Access to LUCAS Device",
        ]),
        ("Inside — Trauma & First Aid Supplies", [
            "Trauma Dressing (Bulk Gauze, ACE Wraps)",
            "Tourniquets",
            "Arm Splints & Slings",
            "Ice/Warm Packs",
            "Saline",
            "Bulb Syringe",
        ]),
        ("Inside Left Front — Airway Cabinet", [
            "CPAP (Continuous Positive Airway Pressure)",
            "NRB (Non-Rebreather Mask)",
            "Capnography",
            "Nasopharyngeal/Oropharyngeal Airways",
            "BVM (Bag Valve Mask)",
            "ET Tubes (Endotracheal Tube)",
            "I-Gel Airways",
            "Nebulizer",
            "Nasal Cannula",
            "Cricothyrotomy Kit",
        ]),
        ("Inside Right Door — Clear Cabinet", [
            "IV Fluid Warmer",
            "Portable Suction",
            "Masks & Gloves",
            "Top Drawer — Syringes, IVs, Band-Aids, IV Tubing",
            "Bottom Drawer — IV Fluids, Mag, Dopamine, IV Tubing, Med Boxes",
        ]),
        ("Inside Right Bench", [
            "Triage Bag",
            "Vacuum Splints",
            "Extra Splints",
            "Blankets (also stored overhead)",
        ]),
        ("Left Side Under Seat", [
            "ACR (Ambulance Child Restraint, Weight-Coded)",
            "Restraints (Psych)",
            "OB Pack (Obstetrical)",
        ]),
        ("Inside Left — Infectious Waste", [
            "Infectious Waste Bin",
            "Sharps Container",
        ]),
        ("Ambulance Cot", [
            "Portable Oxygen Tank (Under Head of Cot)",
            "Airway Equipment (Under Head of Cot)",
            "Cardiac Monitor & Pads (Side Bags)",
        ]),
        ("Behind Passenger Seat", [
            "Extra Portable Oxygen Tanks",
            "ABC Dry Chem Extinguisher",
            "Pediatric Bag (Floor, Adjacent)",
        ]),
    ]
}



# ── PDF builder ───────────────────────────────────────────────────────────────
def build_vehicle_pdf(vehicle_key):
    v = VEHICLES[vehicle_key]
    out_path = os.path.join(OUT_DIR, v['filename'])

    doc = SimpleDocTemplate(
        out_path,
        pagesize=letter,
        leftMargin=0.7*inch,
        rightMargin=0.7*inch,
        topMargin=0.6*inch,
        bottomMargin=0.7*inch,
    )

    story = []
    story += header_block(v['name'])
    story += build_checklist(v['compartments'])
    story += notes_block()

    def make_canvas(fn, **kwargs):
        c = NumberedCanvas(fn, **kwargs)
        c._vehicle_label = v['label']
        return c

    doc.build(story, canvasmaker=make_canvas)
    print(f"  Built: {v['filename']}")
    return out_path

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    KEY_MAP = {
        'e61': 'e61', 'e62': 'e62', 'e60': 'e60', 'e63': 'e63',
        'u61': 'u61', 'u62': 'u62', 'bt62': 'bt62', 'sq61': 'sq61', 't62': 't62', 'sn61': 'sn61', 'm62': 'm62',
    }
    if len(sys.argv) > 1:
        key = sys.argv[1].lower()
        if key in KEY_MAP:
            build_vehicle_pdf(KEY_MAP[key])
        else:
            print(f"Unknown key '{key}'. Valid: {list(KEY_MAP.keys())}")
    else:
        print("Building all rig check PDFs...")
        for key in KEY_MAP:
            build_vehicle_pdf(key)
        print("Done.")
