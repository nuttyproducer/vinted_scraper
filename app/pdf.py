"""Build the export PDF (summary table + per-item cards)."""

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from age import format_listed_age
from models import ItemDTO


def _price_str(item: ItemDTO) -> str:
    if item.price is None:
        return ""
    amount = f"{item.price:g}"
    return f"{amount} {item.currency}".strip() if item.currency else amount


def _summary_rows(items: list[ItemDTO]) -> list[list[str]]:
    header = ["Brand", "Title", "Price", "Condition", "Listed"]
    ordered = sorted(items, key=lambda i: (i.price is None, i.price or 0))
    rows = [
        [
            item.brand or "",
            item.title or "",
            _price_str(item),
            item.condition or "",
            format_listed_age(item.listed_days_ago),
        ]
        for item in ordered
    ]
    return [header] + rows


def build_pdf(items: list[ItemDTO], photos: dict[int, bytes]) -> bytes:
    """Render a summary table and one card per item into PDF bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title="Vinted Price Research")
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph("Vinted Price Research", styles["Title"]))
    story.append(Spacer(1, 6 * mm))

    table = Table(_summary_rows(items))
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8E8E8")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(table)

    for item in items:
        story.append(Spacer(1, 10 * mm))
        story.append(Paragraph(item.title or f"Item {item.id}", styles["Heading2"]))

        photo = photos.get(item.id)
        if photo:
            story.append(
                Image(ImageReader(io.BytesIO(photo)), width=80 * mm, height=80 * mm)
            )
        else:
            story.append(Paragraph("(no image)", styles["Italic"]))

        fields = [
            ("Price", _price_str(item)),
            ("Brand", item.brand),
            ("Size", item.size),
            ("Condition", item.condition),
            ("Listed", format_listed_age(item.listed_days_ago)),
            ("Description", item.description),
            ("Link", item.url),
        ]
        for label, value in fields:
            if value:
                story.append(Paragraph(f"<b>{label}:</b> {value}", styles["Normal"]))

    doc.build(story)
    return buf.getvalue()
