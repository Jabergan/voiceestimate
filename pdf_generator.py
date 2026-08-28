"""
pdf_generator.py — VoiceEstimate Hackyard 2026
Generates professional contractor estimate PDFs using ReportLab.
Written from scratch during Hackyard 2026, Aug 28.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
import io


# ── Brand colors ──────────────────────────────────────────────────────────────
ORANGE      = colors.HexColor('#f97316')
DARK_BG     = colors.HexColor('#1a1a1a')
LIGHT_GRAY  = colors.HexColor('#f5f5f5')
MID_GRAY    = colors.HexColor('#e0e0e0')
TEXT_DARK   = colors.HexColor('#1a1a1a')
TEXT_MUTED  = colors.HexColor('#666666')
WHITE       = colors.white


def generate_pdf(items: list, data: dict) -> bytes:
    """
    Generate a contractor estimate PDF and return raw bytes.

    items: list of dicts with keys: name, qty, unit, unit_price, total
    data:  dict with keys: contractor, phone, customer, address,
                           materials, estimate_num, date
    """
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf,
        pagesize=letter,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
    )

    # ── Styles ────────────────────────────────────────────────────────────────
    style_company = ParagraphStyle('company', fontSize=20, fontName='Helvetica-Bold',
                                   textColor=TEXT_DARK, leading=24)
    style_tagline  = ParagraphStyle('tagline', fontSize=9, fontName='Helvetica',
                                    textColor=TEXT_MUTED, leading=13)
    style_label    = ParagraphStyle('label', fontSize=8, fontName='Helvetica-Bold',
                                    textColor=TEXT_MUTED, leading=11)
    style_value    = ParagraphStyle('value', fontSize=10, fontName='Helvetica',
                                    textColor=TEXT_DARK, leading=14)
    style_est_num  = ParagraphStyle('estnum', fontSize=9, fontName='Helvetica-Bold',
                                    textColor=ORANGE, leading=12, alignment=TA_RIGHT)
    style_total_label = ParagraphStyle('totlabel', fontSize=11, fontName='Helvetica-Bold',
                                       textColor=TEXT_DARK, leading=14, alignment=TA_RIGHT)
    style_total_val   = ParagraphStyle('totval', fontSize=18, fontName='Helvetica-Bold',
                                       textColor=ORANGE, leading=22, alignment=TA_RIGHT)

    elements = []

    # ── Header: company left, estimate info right ─────────────────────────────
    contractor   = data.get('contractor', '')
    phone        = data.get('phone', '')
    customer     = data.get('customer', data.get('customer_name', ''))
    address      = data.get('address', data.get('customer_address', ''))
    estimate_num = data.get('estimate_num', 'EST-001')
    date_str     = data.get('date', '')
    materials    = float(data.get('materials', 0) or 0)

    header_left = [
        [Paragraph(contractor or 'Contractor', style_company)],
        [Paragraph(phone or '', style_tagline)],
        [Spacer(1, 4)],
        [Paragraph('PREPARED FOR', style_label)],
        [Paragraph(customer or '—', style_value)],
        [Paragraph(address or '', style_tagline)],
    ]

    header_right = [
        [Paragraph('ESTIMATE', style_est_num)],
        [Paragraph(estimate_num, ParagraphStyle('en2', fontSize=16, fontName='Helvetica-Bold',
                                                textColor=ORANGE, leading=20, alignment=TA_RIGHT))],
        [Spacer(1, 8)],
        [Paragraph('DATE', style_label)],  # placeholder row
        [Paragraph(date_str, ParagraphStyle('dr', fontSize=10, fontName='Helvetica',
                                            textColor=TEXT_DARK, leading=14, alignment=TA_RIGHT))],
    ]

    # Build two-column header table
    left_table  = Table(header_left,  colWidths=[3.5 * inch])
    right_table = Table(header_right, colWidths=[3.5 * inch])
    right_table.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'RIGHT')]))

    header_row = Table([[left_table, right_table]], colWidths=[3.5 * inch, 3.5 * inch])
    header_row.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING',  (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(header_row)
    elements.append(Spacer(1, 14))
    elements.append(HRFlowable(width='100%', thickness=2, color=ORANGE, spaceAfter=14))

    # ── Line items table ──────────────────────────────────────────────────────
    col_widths = [2.8 * inch, 0.7 * inch, 0.8 * inch, 1.0 * inch, 1.1 * inch]

    th_style = ParagraphStyle('th', fontSize=8, fontName='Helvetica-Bold',
                               textColor=WHITE, leading=11)
    td_style = ParagraphStyle('td', fontSize=9, fontName='Helvetica',
                               textColor=TEXT_DARK, leading=12)
    td_right = ParagraphStyle('tdr', fontSize=9, fontName='Helvetica',
                               textColor=TEXT_DARK, leading=12, alignment=TA_RIGHT)
    td_name  = ParagraphStyle('tdn', fontSize=9, fontName='Helvetica-Bold',
                               textColor=TEXT_DARK, leading=12)

    table_data = [[
        Paragraph('DESCRIPTION',  th_style),
        Paragraph('QTY',          th_style),
        Paragraph('UNIT',         th_style),
        Paragraph('UNIT PRICE',   th_style),
        Paragraph('TOTAL',        th_style),
    ]]

    labor_total = 0.0
    for i, item in enumerate(items):
        qty        = float(item.get('qty', 0))
        unit_price = float(item.get('unit_price', 0))
        total      = float(item.get('total', qty * unit_price))
        labor_total += total

        bg = LIGHT_GRAY if i % 2 == 0 else WHITE
        table_data.append([
            Paragraph(item.get('name', ''), td_name),
            Paragraph(f"{qty:,.1f}",         td_right),
            Paragraph(item.get('unit', ''),  td_style),
            Paragraph(f"${unit_price:,.2f}", td_right),
            Paragraph(f"${total:,.2f}",      td_right),
        ])

    line_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    line_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND',    (0, 0), (-1, 0), DARK_BG),
        ('TOPPADDING',    (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('LEFTPADDING',   (0, 0), (-1, 0), 8),
        ('RIGHTPADDING',  (0, 0), (-1, 0), 8),
        # Data rows
        ('TOPPADDING',    (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        ('LEFTPADDING',   (0, 1), (-1, -1), 8),
        ('RIGHTPADDING',  (0, 1), (-1, -1), 8),
        ('ALIGN',         (1, 1), (-1, -1), 'RIGHT'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [LIGHT_GRAY, WHITE]),
        ('GRID',          (0, 0), (-1, -1), 0.5, MID_GRAY),
        ('LINEBELOW',     (0, 0), (-1, 0), 1, ORANGE),
    ]))
    elements.append(line_table)
    elements.append(Spacer(1, 16))

    # ── Totals block ──────────────────────────────────────────────────────────
    grand_total = labor_total + materials

    totals_data = []
    totals_data.append(['Labor & Installation:', f'${labor_total:,.2f}'])
    if materials > 0:
        totals_data.append(['Materials Allowance:', f'${materials:,.2f}'])
    totals_data.append(['GRAND TOTAL:', f'${grand_total:,.2f}'])

    sub_style  = ParagraphStyle('sub',  fontSize=10, fontName='Helvetica',
                                textColor=TEXT_MUTED, alignment=TA_RIGHT)
    sub_val    = ParagraphStyle('subv', fontSize=10, fontName='Helvetica',
                                textColor=TEXT_DARK,  alignment=TA_RIGHT)
    grand_lbl  = ParagraphStyle('gl',   fontSize=12, fontName='Helvetica-Bold',
                                textColor=TEXT_DARK,  alignment=TA_RIGHT)
    grand_val  = ParagraphStyle('gv',   fontSize=16, fontName='Helvetica-Bold',
                                textColor=ORANGE,     alignment=TA_RIGHT)

    totals_rows = []
    for idx, (lbl, val) in enumerate(totals_data):
        if idx == len(totals_data) - 1:
            totals_rows.append([Paragraph(lbl, grand_lbl), Paragraph(val, grand_val)])
        else:
            totals_rows.append([Paragraph(lbl, sub_style), Paragraph(val, sub_val)])

    totals_table = Table(totals_rows, colWidths=[5.5 * inch, 1.5 * inch])
    totals_table.setStyle(TableStyle([
        ('ALIGN',         (0, 0), (-1, -1), 'RIGHT'),
        ('TOPPADDING',    (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LINEABOVE',     (0, -1), (-1, -1), 1.5, ORANGE),
        ('TOPPADDING',    (0, -1), (-1, -1), 8),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 24))

    # ── Footer ────────────────────────────────────────────────────────────────
    elements.append(HRFlowable(width='100%', thickness=0.5, color=MID_GRAY, spaceAfter=8))
    footer_style = ParagraphStyle('footer', fontSize=8, fontName='Helvetica',
                                  textColor=TEXT_MUTED, alignment=TA_CENTER, leading=12)
    elements.append(Paragraph(
        f'This estimate is valid for 30 days from {date_str}. '
        'Generated by VoiceEstimate — voiceestimate.ngrok.app',
        footer_style
    ))

    doc.build(elements)
    return buf.getvalue()
