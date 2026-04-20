from __future__ import annotations

import os
import unittest
from pathlib import Path

from src.pipeline import DDRPipeline
from src.processing.conflict_detector import detect_conflicts_and_gaps


class PipelineTests(unittest.TestCase):
    def test_pipeline_runs_and_generates_outputs(self) -> None:
        os.environ.setdefault("OPENAI_ENABLED", "false")
        summary = DDRPipeline().run()
        self.assertGreater(summary["merged_findings"], 0)
        self.assertTrue(Path(summary["html_report"]).exists())
        self.assertTrue(Path(summary["pdf_report"]).exists())
        self.assertTrue(Path(summary["explainability_json"]).exists())
        self.assertTrue(Path(summary["trace_view_json"]).exists())

    def test_conflict_detector_flags_known_severity_mismatch(self) -> None:
        findings = [
            {
                "finding_id": "INS-TEST-001",
                "normalized_area": "Roof Section B",
                "observation": "Observed mild dampness at the skirting level.",
                "source_refs": [
                    {"doc_type": "inspection", "page": 1, "snippet": "Observed mild dampness at the skirting level."}
                ],
                "temperature_readings": {"items": []},
                "missing_information": [],
                "conflicts": [],
                "source_area_labels": [{"doc_type": "inspection", "label": "Roof Section B"}],
            },
            {
                "finding_id": "THM-TEST-001",
                "normalized_area": "Roof Section B",
                "observation": "Thermal scan recorded hotspot 30.1C, coldspot 24.4C, delta 5.7C.",
                "source_refs": [
                    {"doc_type": "thermal", "page": 2, "snippet": "Thermal scan recorded hotspot 30.1C, coldspot 24.4C, delta 5.7C."}
                ],
                "temperature_readings": {"items": [{"delta_c": 5.7}]},
                "missing_information": [],
                "conflicts": [],
                "source_area_labels": [{"doc_type": "thermal", "label": "Section B"}],
            },
        ]

        updated = detect_conflicts_and_gaps(findings)
        conflicts = [message for finding in updated for message in finding.get("conflicts", [])]
        self.assertTrue(any("Manual review recommended." in message for message in conflicts))
        self.assertTrue(any("Treated as the same area for this report." in message for message in conflicts))


if __name__ == "__main__":
    unittest.main()
