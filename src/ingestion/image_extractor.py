from __future__ import annotations

from io import BytesIO
from pathlib import Path

from PIL import Image
from pypdf import PdfReader

from src.utils.schemas import ExtractedImage


def extract_images(
    reader: PdfReader,
    doc_type: str,
    output_dir: Path,
    min_dimension: int = 50,
) -> list[ExtractedImage]:
    images: list[ExtractedImage] = []
    doc_output = output_dir / doc_type
    doc_output.mkdir(parents=True, exist_ok=True)

    for page_index, page in enumerate(reader.pages, start=1):
        page_images = list(page.images)
        for image_index, image_file in enumerate(page_images, start=1):
            try:
                pil_image = Image.open(BytesIO(image_file.data))
                width, height = pil_image.size
                image_format = (pil_image.format or "PNG").lower()
            except Exception:
                continue

            if min(width, height) < min_dimension:
                continue

            aspect_ratio = max(width / max(height, 1), height / max(width, 1))
            if aspect_ratio > 4.5:
                continue

            extension = image_format if image_format != "jpeg" else "jpg"
            image_id = f"{doc_type.upper()}-IMG-P{page_index:02d}-{image_index:02d}"
            filename = f"{image_id}.{extension}"
            image_path = doc_output / filename
            pil_image.save(image_path)

            images.append(
                ExtractedImage(
                    image_id=image_id,
                    doc_type=doc_type,
                    page=page_index,
                    path=str(image_path),
                    caption=getattr(image_file, "name", filename),
                )
            )

    return images
