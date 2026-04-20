from __future__ import annotations

from typing import Any


def build_trace_view(findings: list[dict[str, Any]]) -> dict[str, Any]:
    trace_items = []
    for finding in findings:
        trace_items.append(
            {
                "finding_id": finding.get("finding_id"),
                "area": finding.get("normalized_area"),
                "confidence": finding.get("confidence"),
                "trace": [
                    {
                        "doc_type": source.get("doc_type"),
                        "page": source.get("page"),
                        "snippet": source.get("snippet"),
                        "image_refs": source.get("image_refs", []),
                    }
                    for source in finding.get("source_refs", [])
                ],
            }
        )
    return {"trace_view": trace_items}
