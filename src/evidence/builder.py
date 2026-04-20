from __future__ import annotations

import re
from dataclasses import asdict
from typing import Any, Iterable

from src.ingestion.text_extractor import extract_thermal_records
from src.utils.schemas import EvidenceFinding, ExtractedImage, ExtractedPage, SourceRef


AREA_HINTS = [
    "hall",
    "common bedroom",
    "master bedroom",
    "bedroom",
    "kitchen",
    "parking",
    "common bathroom",
    "bathroom",
    "external wall",
    "balcony",
    "terrace",
    "staircase",
    "ceiling",
    "passage",
]


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _infer_area(text: str) -> str:
    lowered = text.lower()
    for hint in AREA_HINTS:
        if hint in lowered:
            return hint.title()
    return "Not Available"


def _make_finding(
    finding_id: str,
    area: str,
    observation: str,
    source_type: str,
    page: int,
    doc_type: str,
    raw_attributes: dict | None = None,
) -> EvidenceFinding:
    return EvidenceFinding(
        finding_id=finding_id,
        area=area or "Not Available",
        observation=observation,
        source_type=source_type,
        source_refs=[
            SourceRef(
                doc_type=doc_type,
                page=page,
                snippet=observation[:500],
            )
        ],
        raw_attributes=raw_attributes or {},
    )


def build_evidence_payload(
    inspection_pages: list[ExtractedPage],
    thermal_pages: list[ExtractedPage],
    images: list[ExtractedImage],
) -> dict:
    inspection_findings = _build_inspection_findings(inspection_pages)
    thermal_records = extract_thermal_records(thermal_pages)
    thermal_findings = _build_thermal_findings(thermal_records)
    findings = inspection_findings + thermal_findings

    return {
        "pages": [asdict(page) for page in [*inspection_pages, *thermal_pages]],
        "thermal_records": thermal_records,
        "images": [asdict(image) for image in images],
        "findings": [asdict(finding) for finding in findings],
        "summary": {
            "inspection_pages": len(inspection_pages),
            "thermal_pages": len(thermal_pages),
            "thermal_records": len(thermal_records),
            "findings_count": len(findings),
            "images_count": len(images),
        },
    }


def _build_inspection_findings(pages: Iterable[ExtractedPage]) -> list[EvidenceFinding]:
    findings: list[EvidenceFinding] = []
    seen: set[str] = set()
    counter = 1

    for page in pages:
        text = page.text
        summary_matches = re.findall(r"(Observed\s+.+?)(?=\n|$)", text, flags=re.IGNORECASE)
        for match in summary_matches:
            observation = _compact(match)
            key = observation.lower()
            if len(observation) < 20 or key in seen:
                continue
            seen.add(key)
            findings.append(
                _make_finding(
                    finding_id=f"INS-{counter:03d}",
                    area=_infer_area(observation),
                    observation=observation,
                    source_type="inspection_summary",
                    page=page.page,
                    doc_type=page.doc_type,
                )
            )
            counter += 1

        page_text = _compact(text)
        for label, source_type in (
            ("Negative side Description", "inspection_negative"),
            ("Positive side Description", "inspection_positive"),
        ):
            pattern = re.compile(
                rf"{re.escape(label)}\s+(.*?)\s+(?:Negative side photographs|Positive side photographs|Impacted Area|Checklist:|$)",
                flags=re.IGNORECASE,
            )
            for match in pattern.findall(page_text):
                observation = _compact(match)
                if len(observation) < 8:
                    continue
                key = f"{source_type}:{observation.lower()}"
                if key in seen:
                    continue
                seen.add(key)
                findings.append(
                    _make_finding(
                        finding_id=f"INS-{counter:03d}",
                        area=_infer_area(observation),
                        observation=observation,
                        source_type=source_type,
                        page=page.page,
                        doc_type=page.doc_type,
                    )
                )
                counter += 1

    return findings


def _build_thermal_findings(records: Iterable[dict[str, Any]]) -> list[EvidenceFinding]:
    findings: list[EvidenceFinding] = []
    counter = 1

    for record in records:
        metadata = record.get("metadata", {})
        image_name = str(metadata.get("thermal_image_name", "Not Available"))
        hotspot = metadata.get("hotspot_c", "Not Available")
        coldspot = metadata.get("coldspot_c", "Not Available")
        delta = metadata.get("delta_c", "Not Available")

        if image_name == "Not Available" and hotspot == "Not Available" and coldspot == "Not Available":
            continue

        observation = (
            f"Thermal scan {image_name} recorded hotspot {hotspot}°C, "
            f"coldspot {coldspot}°C, delta {delta}°C."
        )
        findings.append(
            EvidenceFinding(
                finding_id=f"THM-{counter:03d}",
                area=_infer_area(record.get("text", "")),
                observation=observation,
                source_type="thermal_scan",
                source_refs=[
                    SourceRef(
                        doc_type="thermal",
                        page=page_number,
                        snippet=observation[:500],
                    )
                    for page_number in record.get("pages", [])
                ],
                raw_attributes={
                    **metadata,
                    "start_page": record.get("start_page"),
                    "thermal_record_pages": record.get("pages", []),
                    "thermal_record_index": counter,
                },
            )
        )
        findings[-1].temperature_readings = {
            "hotspot_c": hotspot,
            "coldspot_c": coldspot,
            "delta_c": delta,
            "thermal_image_name": image_name,
        }
        counter += 1

    return findings
