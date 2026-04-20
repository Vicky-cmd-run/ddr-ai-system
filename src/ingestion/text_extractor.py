from __future__ import annotations

import re
from typing import Any, Iterable

from pypdf import PdfReader

from src.utils.schemas import ExtractedPage


def _clean_line(line: str) -> str:
    line = line.replace("\u00a0", " ")
    line = re.sub(r"\s+", " ", line)
    return line.strip()


def normalize_text_block(text: str) -> str:
    lines = [_clean_line(line) for line in text.splitlines()]
    compact_lines = [line for line in lines if line]
    return "\n".join(compact_lines)


def extract_pages(reader: PdfReader, doc_type: str) -> list[ExtractedPage]:
    pages: list[ExtractedPage] = []
    for index, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        cleaned = normalize_text_block(raw_text)
        metadata = {}
        if doc_type == "thermal":
            metadata.update(extract_thermal_metadata(cleaned))
        pages.append(
            ExtractedPage(
                doc_type=doc_type,
                page=index,
                text=cleaned,
                metadata=metadata,
            )
        )
    return pages


def extract_thermal_records(pages: list[ExtractedPage]) -> list[dict[str, Any]]:
    """
    Group thermal pages into scan records.

    The thermal PDF often splits a single scan across page boundaries. We treat
    each `Thermal image:` occurrence as the beginning of a new record and append
    only meaningful tail text from the following page when it contains the scan's
    remaining readings.
    """

    records: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for page in pages:
        text = page.text
        parts = re.split(r"(?=Thermal\s*image\s*:)", text, flags=re.IGNORECASE)

        if len(parts) == 1:
            if current is not None and _looks_like_thermal_tail(text):
                current["pages"].append(page.page)
                current["text"] += "\n" + text
            continue

        prefix = parts[0].strip()
        if current is not None and _looks_like_thermal_tail(prefix):
            current["pages"].append(page.page)
            current["text"] += "\n" + prefix

        if current is not None:
            records.append(_finalize_thermal_record(current))
            current = None

        for index, segment in enumerate(parts[1:], start=1):
            current = {
                "start_page": page.page,
                "pages": [page.page],
                "text": segment,
            }
            if index < len(parts) - 1:
                records.append(_finalize_thermal_record(current))
                current = None

    if current is not None:
        records.append(_finalize_thermal_record(current))

    return records


def stitch_document_text(pages: Iterable[ExtractedPage]) -> str:
    stitched = []
    for page in pages:
        stitched.append(f"--- PAGE {page.page} ---")
        stitched.append(page.text)
    return "\n".join(stitched)


def extract_thermal_metadata(text: str) -> dict[str, str | float]:
    def search(pattern: str) -> str:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        return match.group(1).strip() if match else "Not Available"

    def search_float(pattern: str) -> float | str:
        value = search(pattern)
        if value == "Not Available":
            return value
        try:
            return float(value)
        except ValueError:
            return value

    hotspot = search_float(r"Hotspot\s*:\s*([0-9.]+)")
    coldspot = search_float(r"Coldspot\s*:\s*([0-9.]+)")
    image_name = search(r"Thermal\s*image\s*:\s*([A-Za-z0-9._-]+)")
    date = search(r"([0-9]{2}/[0-9]{2}/[0-9]{2})")

    delta: float | str = "Not Available"
    if isinstance(hotspot, float) and isinstance(coldspot, float):
        delta = round(hotspot - coldspot, 2)

    return {
        "thermal_image_name": image_name,
        "hotspot_c": hotspot,
        "coldspot_c": coldspot,
        "delta_c": delta,
        "scan_date": date,
    }


def _looks_like_thermal_tail(text: str) -> bool:
    compact = " ".join(text.split())
    if not compact:
        return False
    if re.fullmatch(r"\d+", compact):
        return False
    keywords = ("hotspot", "coldspot", "emissivity", "temperature", "°c")
    return any(keyword in compact.lower() for keyword in keywords)


def _finalize_thermal_record(record: dict[str, Any]) -> dict[str, Any]:
    metadata = extract_thermal_metadata(" ".join(record["text"].split()))
    return {
        "start_page": record["start_page"],
        "pages": record["pages"],
        "text": normalize_text_block(record["text"]),
        "metadata": metadata,
    }
