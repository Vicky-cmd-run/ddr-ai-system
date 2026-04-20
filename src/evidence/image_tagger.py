from __future__ import annotations

from collections import defaultdict
from typing import Any


def tag_images(payload: dict[str, Any]) -> dict[str, Any]:
    findings = payload.get("findings", [])
    images = payload.get("images", [])

    linked_by_image: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for finding in findings:
        for image_id in finding.get("images", []):
            linked_by_image[image_id].append(finding)

    for image in images:
        linked_findings = linked_by_image.get(image["image_id"], [])
        if not linked_findings:
            image["tags"] = ["unassigned"]
            continue

        primary = linked_findings[0]
        section = (
            "area-wise-observations"
            if primary["source_type"].startswith("inspection")
            else "additional-notes"
        )
        image["tags"] = [
            f"section:{section}",
            f"area:{primary['area']}",
            f"finding:{primary['finding_id']}",
        ]

    payload["images"] = images
    return payload
