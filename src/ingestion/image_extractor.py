from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

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
    rendered_pages: set[int] = set()
    source_path = getattr(reader, "source_path", None)

    for page_index, page in enumerate(reader.pages, start=1):
        page_images = list(page.images)
        extracted_page_images: list[ExtractedImage] = []
        deferred_small_assets: list[tuple[Image.Image, str, str]] = []
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

            if doc_type == "inspection" and max(width, height) < 140:
                extension = image_format if image_format != "jpeg" else "jpg"
                image_id = f"{doc_type.upper()}-IMG-P{page_index:02d}-{image_index:02d}"
                filename = f"{image_id}.{extension}"
                deferred_small_assets.append((pil_image.copy(), extension, filename))
                continue

            extension = image_format if image_format != "jpeg" else "jpg"
            image_id = f"{doc_type.upper()}-IMG-P{page_index:02d}-{image_index:02d}"
            filename = f"{image_id}.{extension}"
            image_path = doc_output / filename
            pil_image.save(image_path)

            extracted_page_images.append(
                ExtractedImage(
                    image_id=image_id,
                    doc_type=doc_type,
                    page=page_index,
                    path=str(image_path),
                    caption=getattr(image_file, "name", filename),
                )
            )
        images.extend(extracted_page_images)

        needs_render_fallback = (
            doc_type == "inspection"
            and source_path is not None
            and page_index not in rendered_pages
            and (
                not page_images and not extracted_page_images
            )
        )
        if needs_render_fallback:
            rendered = _render_page_fallback(
                source_path=source_path,
                doc_type=doc_type,
                output_dir=doc_output,
                page_index=page_index,
            )
            if rendered is not None:
                images.append(rendered)
                rendered_pages.add(page_index)
                continue

        if doc_type == "inspection" and deferred_small_assets:
            for image_index, (pil_image, extension, filename) in enumerate(deferred_small_assets, start=1):
                image_id = f"{doc_type.upper()}-IMG-P{page_index:02d}-{image_index:02d}"
                image_path = doc_output / filename
                upscaled = _upscale_thumbnail(pil_image)
                upscaled.save(image_path)
                images.append(
                    ExtractedImage(
                        image_id=image_id,
                        doc_type=doc_type,
                        page=page_index,
                        path=str(image_path),
                        caption=filename,
                    )
                )  # Visual fix: inspection pages now prefer upscaled photo thumbnails over full-page snapshots, so the report shows the actual image evidence instead of the entire PDF page.

    return images


def _render_page_fallback(
    source_path: str,
    doc_type: str,
    output_dir: Path,
    page_index: int,
) -> ExtractedImage | None:
    page_image = _render_pdf_page(source_path=source_path, page_index=page_index)
    if page_image is None:
        return None

    image_id = f"{doc_type.upper()}-PAGE-P{page_index:02d}"
    image_path = output_dir / f"{image_id}.png"
    page_image.save(image_path)
    return ExtractedImage(
        image_id=image_id,
        doc_type=doc_type,
        page=page_index,
        path=str(image_path),
        caption=f"Rendered page fallback for {doc_type} page {page_index}",
    )


def _render_pdf_page(source_path: str, page_index: int) -> Image.Image | None:
    page_image = _render_with_pypdfium2(source_path, page_index)
    if page_image is not None:
        return page_image
    page_image = _render_with_pymupdf(source_path, page_index)
    if page_image is not None:
        return page_image
    page_image = _render_with_pdf2image(source_path, page_index)
    if page_image is not None:
        return page_image
    return None


def _render_with_pypdfium2(source_path: str, page_index: int) -> Image.Image | None:
    try:
        import pypdfium2 as pdfium  # type: ignore
    except Exception:
        return None

    try:
        pdf = pdfium.PdfDocument(source_path)
        page = pdf.get_page(page_index - 1)
        bitmap = page.render(scale=2.5)
        pil_image = bitmap.to_pil()
        page.close()
        pdf.close()
        return pil_image.convert("RGB")
    except Exception:
        return None


def _render_with_pymupdf(source_path: str, page_index: int) -> Image.Image | None:
    try:
        import fitz  # type: ignore
    except Exception:
        return None

    try:
        document = fitz.open(source_path)
        page = document.load_page(page_index - 1)
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2.5, 2.5), alpha=False)
        image = Image.open(BytesIO(pixmap.tobytes("png"))).convert("RGB")
        document.close()
        return image
    except Exception:
        return None


def _render_with_pdf2image(source_path: str, page_index: int) -> Image.Image | None:
    try:
        from pdf2image import convert_from_path  # type: ignore
    except Exception:
        return None

    try:
        pages = convert_from_path(
            source_path,
            first_page=page_index,
            last_page=page_index,
            dpi=220,
            fmt="png",
        )
        if not pages:
            return None
        return pages[0].convert("RGB")
    except Exception:
        return None


def _upscale_thumbnail(image: Image.Image, target_long_side: int = 220) -> Image.Image:
    width, height = image.size
    long_side = max(width, height)
    if long_side <= 0:
        return image
    scale = max(target_long_side / long_side, 1.0)
    new_size = (max(int(width * scale), 1), max(int(height * scale), 1))
    return image.resize(new_size, Image.Resampling.LANCZOS).convert("RGB")  # Extraction fix: enlarge tiny embedded inspection photos before saving so the client report shows usable image evidence without needing a full-page fallback.
