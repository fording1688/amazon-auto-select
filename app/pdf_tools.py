from __future__ import annotations

import io

from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas


def _draw_made_in_china_grid(page_width: float, page_height: float, text: str) -> bytes:
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_width, page_height))

    cols = 3
    rows = 9
    margin_x = page_width * 0.055
    margin_y = page_height * 0.035
    usable_width = page_width - margin_x * 2
    usable_height = page_height - margin_y * 2
    cell_width = usable_width / cols
    cell_height = usable_height / rows

    font_size = max(6, min(9, cell_height * 0.16))
    c.setFont("Helvetica", font_size)
    c.setFillColorRGB(0, 0, 0)

    for row in range(rows):
        for col in range(cols):
            x = margin_x + col * cell_width + cell_width * 0.06
            y = page_height - margin_y - (row + 1) * cell_height + cell_height * 0.12
            c.drawString(x, y, text)

    c.save()
    return packet.getvalue()


def add_made_in_china_to_27up_pdf(content: bytes, text: str = "Made in China") -> bytes:
    reader = PdfReader(io.BytesIO(content))
    writer = PdfWriter()

    for page in reader.pages:
        page_width = float(page.mediabox.width)
        page_height = float(page.mediabox.height)
        overlay_reader = PdfReader(io.BytesIO(_draw_made_in_china_grid(page_width, page_height, text)))
        page.merge_page(overlay_reader.pages[0])
        writer.add_page(page)

    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()
