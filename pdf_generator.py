"""
PDF Generator for VoiceEstimate
Drop-in replacement for Flux's existing /pdf route.
Requires: reportlab

Usage in Flask:
    from pdf_generator import generate_pdf
    
    @app.route('/pdf')
    def pdf():
        items = json.loads(request.args.get('items', '[]'))
        data = {
            'contractor': request.args.get('contractor', ''),
            'phone': request.args.get('phone', ''),
            'customer_name': request.args.get('customer_name', ''),
            'customer_address': request.args.get('customer_address', ''),
            'materials': float(request.args.get('materials', 0)),
            'estimate_num': request.args.get('estimate_num', 'EST-001'),
            'date': request.args.get('date', ''),
        }
        pdf_bytes = generate_pdf(items, data)
        return Response(pdf_bytes, mimetype='application/pdf',
                       headers={'Content-Disposition': f'attachment; filename="{data["estimate_num"]}.pdf"'})
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT, TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from io import BytesIO

# Brand colors
ORANGE = colors.HexColor('#f97316')
DARK = colors.HexColor('#0a0a0a')
GRAY_LIGHT = colors.HexColor('#f5f5f5')
GRAY_MID = colors.HexColor('#e5e5e5')
GRAY_TEXT = colors.HexColor('#666666')
WHITE = colors.white
BLACK = colors.HexColor('#1a1a1a')


def generate_pdf(items, data):
    """
    items: list of dicts with keys: name, qty, unit, unit_price, total
    data: dict with contractor, phone, customer_name, customer_address,
          materials, estimate_num, date
    Returns: bytes
    """
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.65 * inch,
        rightMargin=0.65 * inch,
        topMargin=0.65 * inch,
        bottomMargin=0.65 * inch,
    )

    styles = getSampleStyleSheet()
    story = []

    # ─── HEADER ───────────────────────────────────────────────────────────────
    contractor_name = data.get('contractor') or 'Contractor'
    contractor_phone = data.get('phone') or ''
    estimate_num = data.get('estimate_num') or 'EST-001'
    estimate_date = data.get('date') or ''

    header_data = [[
        # Left: contractor info
        Paragraph(
            f'<font size="16" color="#1a1a1a"><b>{contractor_name}</b></font><br/>'
            f'<font size="10" color="#666666">{contractor_phone}</font>',
            ParagraphStyle('contractor', fontName='Helvetica', leading=20)
        ),
        # Right: ESTIMATE label + number + date
        Paragraph(
            f'<font size="22" color="#f97316"><b>ESTIMATE</b></font><br/>'
            f'<font size="10" color="#666666">{estimate_num}</font><br/>'
            f'<font size="10" color="#666666">{estimate_date}</font>',
            ParagraphStyle('estimate_label', fontName='Helvetica', alignment=TA_RIGHT, leading=22)
        ),
    ]]

    header_table = Table(header_data, colWidths=[3.5 * inch, 3.5 * inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(header_table)

    # Orange divider
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width='100%', thickness=2, color=ORANGE, spaceAfter=12))

    # ─── CUSTOMER BLOCK ───────────────────────────────────────────────────────
    customer_name = data.get('customer_name', '').strip()
    customer_address = data.get('customer_address', '').strip()

    if customer_name or customer_address:
        customer_data = [[
            Paragraph(
                f'<font size="8" color="#888888"><b>PREPARED FOR</b></font><br/>'
                f'<font size="11" color="#1a1a1a"><b>{customer_name}</b></font><br/>'
                f'<font size="10" color="#666666">{customer_address}</font>',
                ParagraphStyle('customer', fontName='Helvetica', leading=16)
            ),
            '',
        ]]
        customer_table = Table(customer_data, colWidths=[3.5 * inch, 3.5 * inch])
        customer_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(customer_table)
        story.append(Spacer(1, 14))

    # ─── LINE ITEMS TABLE ─────────────────────────────────────────────────────
    col_headers = ['Description', 'Qty', 'Unit', 'Unit Price', 'Total']
    col_widths = [2.8 * inch, 0.6 * inch, 0.8 * inch, 1.0 * inch, 1.1 * inch]

    table_data = [col_headers]

    labor_total = 0
    for i, item in enumerate(items):
        total = float(item.get('total', 0))
        labor_total += total
        row = [
            item.get('name', ''),
            str(item.get('qty', '')),
            str(item.get('unit', '')),
            f"${float(item.get('unit_price', 0)):,.2f}",
            f"${total:,.2f}",
        ]
        table_data.append(row)

    materials = float(data.get('materials', 0))
    grand_total = labor_total + materials

    # Build table styles
    table_style = [
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), DARK),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        ('ALIGN', (1, 0), (-1, 0), 'RIGHT'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),

        # Data rows
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('TEXTCOLOR', (0, 1), (-1, -1), BLACK),
        ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('TOPPADDING', (0, 1), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 7),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, GRAY_MID),

        # Grid lines
        ('LINEBELOW', (0, 0), (-1, -2), 0.3, GRAY_MID),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]

    # Alternating row colors
    for i in range(1, len(table_data)):
        if i % 2 == 0:
            table_style.append(('BACKGROUND', (0, i), (-1, i), GRAY_LIGHT))

    line_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    line_table.setStyle(TableStyle(table_style))
    story.append(line_table)
    story.append(Spacer(1, 16))

    # ─── TOTALS BLOCK ─────────────────────────────────────────────────────────
    totals_data = [
        ['Labor Total', f'${labor_total:,.2f}'],
    ]
    if materials > 0:
        totals_data.append(['Building Materials', f'${materials:,.2f}'])

    totals_table = Table(totals_data, colWidths=[5.5 * inch, 1.8 * inch])
    totals_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (-1, -1), GRAY_TEXT),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (1, 0), (1, -1), 8),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 6))

    # Grand total row — orange background
    grand_data = [['GRAND TOTAL', f'${grand_total:,.2f}']]
    grand_table = Table(grand_data, colWidths=[5.5 * inch, 1.8 * inch])
    grand_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), ORANGE),
        ('TEXTCOLOR', (0, 0), (-1, -1), WHITE),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
    ]))
    story.append(grand_table)

    # ─── FOOTER ───────────────────────────────────────────────────────────────
    story.append(Spacer(1, 24))
    story.append(HRFlowable(width='100%', thickness=0.5, color=GRAY_MID, spaceAfter=8))
    story.append(Paragraph(
        '<font size="8" color="#aaaaaa">Generated by VoiceEstimate · voiceestimate.ngrok.app</font>',
        ParagraphStyle('footer', fontName='Helvetica', alignment=TA_CENTER)
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
