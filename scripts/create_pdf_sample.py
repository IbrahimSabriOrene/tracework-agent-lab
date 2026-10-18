"""Create one synthetic raster-only PDF for exercising actual OCR, not text extraction."""

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def main():
    root = Path(__file__).resolve().parent.parent
    output = root / "web/samples/atlas-scan.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    font_path = next(
        path
        for path in [
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ]
        if path.is_file()
    )
    image = Image.new("RGB", (1654, 2339), "white")
    draw = ImageDraw.Draw(image)
    heading, body, small = [ImageFont.truetype(str(font_path), size) for size in (68, 37, 28)]
    draw.text((130, 140), "Tracework / Synthetic document", font=small, fill="#176d70")
    draw.text((130, 235), "Atlas launch brief", font=heading, fill="#183447")
    draw.line((130, 350, 1524, 350), fill="#cbd8df", width=3)
    lines = [
        "The Atlas microsite introduces a fictional community workshop.",
        "Launch date: 18 November 2026.",
        "Content owner: TBD.",
        "The design review happens next Friday.",
        "Dependency: venue confirmation is pending.",
        "The project lead will approve the final review report.",
    ]
    for index, line in enumerate(lines):
        draw.text((130, 445 + index * 112), line, font=body, fill="#183447")
    draw.line((130, 2050, 1524, 2050), fill="#cbd8df", width=3)
    draw.text(
        (130, 2110), "Synthetic sample. No customer or personal data.", font=small, fill="#627783"
    )
    draw.text(
        (130, 2160),
        "Raster-only PDF: OCR is required to read this page.",
        font=small,
        fill="#627783",
    )
    draw.text((1455, 2160), "1", font=small, fill="#627783")
    raster = io.BytesIO()
    image.save(raster, format="PNG")
    pdf = canvas.Canvas(str(output), pagesize=(595.28, 841.89), invariant=1)
    pdf.setTitle("Tracework synthetic scanned Atlas brief")
    pdf.drawImage(ImageReader(raster), 0, 0, width=595.28, height=841.89)
    pdf.save()
    print(output)


if __name__ == "__main__":
    main()
