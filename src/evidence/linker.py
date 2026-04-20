from __future__ import annotations

import re
from collections import defaultdict
from io import BytesIO
from typing import Any

import numpy as np
from PIL import Image


def link_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    findings = payload.get("findings", [])
    images = payload.get("images", [])
    pages = payload.get("pages", [])

    page_lookup = {(page["doc_type"], page["page"]): page for page in pages}
    image_index: dict[tuple[str, int], list[dict[str, Any]]] = defaultdict(list)
    for image in images:
        image_index[(image["doc_type"], image["page"])].append(image)

    inspection_allocations = _allocate_inspection_images(findings, page_lookup, image_index)

    for finding in findings:
        image_refs = _resolve_finding_images(finding, image_index, inspection_allocations)
        finding["images"] = image_refs
        for source_ref in finding.get("source_refs", []):
            source_ref["image_refs"] = [
                image["image_id"]
                for image in image_index.get((source_ref["doc_type"], source_ref["page"]), [])
            ]

    _apply_visual_similarity_mapping(findings, images)
    _apply_sequence_fallback(findings)

    payload["findings"] = findings
    payload["images"] = images
    return payload


def _resolve_finding_images(
    finding: dict[str, Any],
    image_index: dict[tuple[str, int], list[dict[str, Any]]],
    inspection_allocations: dict[str, list[str]],
) -> list[str]:
    if finding["source_type"].startswith("inspection"):
        allocated = inspection_allocations.get(finding["finding_id"])
        if allocated:
            return allocated

    if finding["source_type"] == "thermal_scan":
        start_page = finding.get("raw_attributes", {}).get("start_page")
        if start_page is not None:
            return [
                image["image_id"]
                for image in image_index.get(("thermal", int(start_page)), [])
            ]

    images = []
    for source_ref in finding.get("source_refs", []):
        images.extend(
            image["image_id"]
            for image in image_index.get((source_ref["doc_type"], source_ref["page"]), [])
        )
    return sorted(set(images))


def _allocate_inspection_images(
    findings: list[dict[str, Any]],
    page_lookup: dict[tuple[str, int], dict[str, Any]],
    image_index: dict[tuple[str, int], list[dict[str, Any]]],
) -> dict[str, list[str]]:
    allocations: dict[str, list[str]] = {}
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)

    for finding in findings:
        if finding["source_type"].startswith("inspection") and finding.get("source_refs"):
            grouped[finding["source_refs"][0]["page"]].append(finding)

    for page_number, page_findings in grouped.items():
        page_images = image_index.get(("inspection", page_number), [])
        if not page_images:
            continue

        weights = _derive_page_weights(
            page_lookup.get(("inspection", page_number), {}).get("text", ""),
            page_findings,
        )
        chunks = _distribute_images([image["image_id"] for image in page_images], weights)
        for finding, image_ids in zip(page_findings, chunks):
            allocations[finding["finding_id"]] = image_ids

    return allocations


def _derive_page_weights(page_text: str, page_findings: list[dict[str, Any]]) -> list[int]:
    blocks = _extract_photo_blocks(page_text)
    weights: list[int] = []
    used: set[int] = set()

    for finding in page_findings:
        observation = " ".join(finding.get("observation", "").lower().split())
        weight = 1
        for index, block in enumerate(blocks):
            if index in used:
                continue
            description = " ".join(block["description"].lower().split())
            if observation in description or description in observation:
                weight = max(block["photo_count"], 1)
                used.add(index)
                break
        weights.append(max(weight, 1))

    return weights or [1] * len(page_findings)


def _extract_photo_blocks(page_text: str) -> list[dict[str, Any]]:
    pattern = re.compile(
        r"(Negative side Description|Positive side Description)\s+(.*?)\s+"
        r"(Negative side photographs|Positive side photographs)\s+(.*?)"
        r"(?=(?:Negative side Description|Positive side Description|Impacted Area \d+|Checklist:|$))",
        flags=re.IGNORECASE | re.DOTALL,
    )
    blocks = []
    for match in pattern.finditer(page_text):
        description = " ".join(match.group(2).split())
        photo_count = len(re.findall(r"Photo\s+\d+", match.group(4), flags=re.IGNORECASE))
        blocks.append({"description": description, "photo_count": photo_count})
    return blocks


def _distribute_images(image_ids: list[str], weights: list[int]) -> list[list[str]]:
    if not weights:
        return []
    if len(weights) == 1:
        return [image_ids]

    total_weight = sum(weights)
    quotas = [len(image_ids) * weight / total_weight for weight in weights]
    counts = [int(quota) for quota in quotas]

    remainder = len(image_ids) - sum(counts)
    ranked = sorted(
        range(len(weights)),
        key=lambda index: (quotas[index] - counts[index], weights[index]),
        reverse=True,
    )
    for index in ranked[:remainder]:
        counts[index] += 1

    if image_ids and all(count == 0 for count in counts):
        counts[0] = len(image_ids)

    chunks: list[list[str]] = []
    cursor = 0
    for count in counts:
        chunks.append(image_ids[cursor : cursor + count])
        cursor += count
    if cursor < len(image_ids):
        chunks[-1].extend(image_ids[cursor:])
    return chunks


def _apply_visual_similarity_mapping(findings: list[dict[str, Any]], images: list[dict[str, Any]]) -> None:
    image_lookup = {image["image_id"]: image for image in images}
    inspection_images = [image for image in images if image["doc_type"] == "inspection"]
    if not inspection_images:
        return

    inspection_image_area = {}
    for finding in findings:
        if not finding["source_type"].startswith("inspection"):
            continue
        for image_id in finding.get("images", []):
            inspection_image_area.setdefault(
                image_id,
                {
                    "area": finding.get("area", "Not Available"),
                    "finding_id": finding.get("finding_id"),
                },
            )

    inspection_hashes = {
        image["image_id"]: _dhash(image_lookup[image["image_id"]]["path"])
        for image in inspection_images
    }

    for finding in findings:
        if finding["source_type"] != "thermal_scan":
            continue

        visual_images = [
            image_lookup[image_id]
            for image_id in finding.get("images", [])
            if image_id in image_lookup and _is_visual_photo(image_lookup[image_id]["path"])
        ]
        best_match = None
        for thermal_image in visual_images:
            thermal_hash = _dhash(thermal_image["path"])
            for inspection_image_id, inspection_hash in inspection_hashes.items():
                distance = int(np.count_nonzero(thermal_hash != inspection_hash))
                if best_match is None or distance < best_match["distance"]:
                    best_match = {
                        "thermal_image_id": thermal_image["image_id"],
                        "inspection_image_id": inspection_image_id,
                        "distance": distance,
                    }

        if best_match and best_match["distance"] <= 16:
            matched = inspection_image_area.get(best_match["inspection_image_id"])
            if matched:
                finding["area"] = matched["area"]
                finding.setdefault("raw_attributes", {})["area_link_method"] = "visual_similarity_match"
                finding["raw_attributes"]["matched_inspection_image"] = best_match["inspection_image_id"]
                finding["raw_attributes"]["matched_thermal_image"] = best_match["thermal_image_id"]
                finding["raw_attributes"]["image_match_distance"] = best_match["distance"]


def _apply_sequence_fallback(findings: list[dict[str, Any]]) -> None:
    inspection_areas = [
        finding["area"]
        for finding in findings
        if finding["source_type"] == "inspection_summary" and finding["area"] != "Not Available"
    ]
    if not inspection_areas:
        inspection_areas = [
            finding["area"]
            for finding in findings
            if finding["source_type"].startswith("inspection") and finding["area"] != "Not Available"
        ]

    thermal_findings = [finding for finding in findings if finding["source_type"] == "thermal_scan"]
    for index, finding in enumerate(thermal_findings):
        method = finding.get("raw_attributes", {}).get("area_link_method")
        if method == "visual_similarity_match":
            continue
        if finding.get("area") != "Not Available":
            continue
        if inspection_areas:
            mapped_index = min(
                int(index * len(inspection_areas) / max(len(thermal_findings), 1)),
                len(inspection_areas) - 1,
            )
            finding["area"] = inspection_areas[mapped_index]
            finding.setdefault("raw_attributes", {})["area_link_method"] = "sequence_fallback"


def _is_visual_photo(path: str) -> bool:
    image = Image.open(path).convert("RGB").resize((64, 64))
    arr = np.array(image, dtype=np.int16)
    saturation = ((arr.max(axis=2) - arr.min(axis=2)) / 255.0).mean()
    return saturation < 0.35


def _dhash(path: str, size: int = 8) -> np.ndarray:
    image = Image.open(path).convert("L").resize((size + 1, size))
    arr = np.array(image)
    return arr[:, 1:] > arr[:, :-1]
