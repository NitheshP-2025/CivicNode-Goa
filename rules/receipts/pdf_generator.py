
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


def generate_receipt_pdf(receipt: dict) -> bytes:
    """
    Generate a PDF document from a built receipt.
    Returns the PDF as bytes.
    """

    required_fields = [
        "receipt_id",
        "claim_id",
        "scheme",
        "incident_date",
        "rule_pack",
        "calculation",
    ]

    missing = [
        field for field in required_fields
        if field not in receipt
    ]

    if missing:
        raise ValueError(
            f"Receipt is missing required fields: {missing}"
        )

    rule_pack = receipt["rule_pack"]
    calculation = receipt["calculation"]

    if not isinstance(rule_pack, dict):
        raise ValueError("rule_pack must be a dictionary")

    if not isinstance(calculation, dict):
        raise ValueError("calculation must be a dictionary")

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReceiptTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=20,
        spaceAfter=8,
    )

    subtitle_style = ParagraphStyle(
        "ReceiptSubtitle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=10,
        textColor=colors.grey,
    )

    heading_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontSize=12,
        spaceBefore=12,
        spaceAfter=6,
    )

    body_style = styles["BodyText"]

    story = []

    story.append(
        Paragraph("CIVICNODE-GOA", title_style)
    )

    story.append(
        Paragraph(
            "Compensation Calculation Receipt",
            subtitle_style,
        )
    )

    story.append(Spacer(1, 15))

    details = [
        ["Receipt ID", str(receipt["receipt_id"])],
        ["Claim ID", str(receipt["claim_id"])],
        ["Scheme", str(receipt["scheme"])],
        ["Incident Date", str(receipt["incident_date"])],
        ["Rule Pack Version", str(rule_pack.get("version", "N/A"))],
        ["Rule Pack Status", str(rule_pack.get("status", "N/A"))],
        ["Decision Status", str(receipt.get(
            "decision_status", "N/A"
        ))],
    ]

    details_table = Table(
        details,
        colWidths=[50 * mm, 110 * mm],
    )

    details_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EAF0F6")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))

    story.append(
        Paragraph("Claim Details", heading_style)
    )
    story.append(details_table)

    story.append(
        Paragraph("Calculation Summary", heading_style)
    )

    summary = [
        ["Field", "Value"],
        ["Formula", str(calculation.get("formula", "N/A"))],
        ["Total Amount", str(calculation.get("total", "N/A"))],
        ["Currency", str(calculation.get("currency", "INR"))],
        ["Rounding", str(calculation.get("rounding", "N/A"))],
    ]

    summary_table = Table(
        summary,
        colWidths=[50 * mm, 110 * mm],
    )

    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F3A5F")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 8),
    ]))

    story.append(summary_table)

    story.append(
        Paragraph("Notices and Disclaimers", heading_style)
    )

    notices = receipt.get("notices", [])

    for notice in notices:
        story.append(
            Paragraph(
                f"• {escape(str(notice))}",
                body_style,
            )
        )
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 15))

    story.append(
        Paragraph(
            "<b>IMPORTANT:</b> This is a synthetic demonstration "
            "receipt. It is not an official Government of Goa "
            "compensation order or proof of payment. The calculation "
            "requires authorised officer review.",
            body_style,
        )
    )

    document.build(story)

    return buffer.getvalue()
