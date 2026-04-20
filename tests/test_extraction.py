from __future__ import annotations

import unittest

from src.ingestion.image_extractor import extract_images
from src.ingestion.pdf_loader import load_pdf
from src.ingestion.text_extractor import extract_pages
from src.utils.config import get_settings


class ExtractionTests(unittest.TestCase):
    def test_extract_pages_from_both_documents(self) -> None:
        settings = get_settings()
        inspection_pages = extract_pages(load_pdf(settings.inspection_pdf), "inspection")
        thermal_pages = extract_pages(load_pdf(settings.thermal_pdf), "thermal")

        self.assertGreater(len(inspection_pages), 0)
        self.assertGreater(len(thermal_pages), 0)
        self.assertIn("Inspection", inspection_pages[0].text)

    def test_extract_images(self) -> None:
        settings = get_settings()
        inspection_images = extract_images(
            load_pdf(settings.inspection_pdf),
            "inspection",
            settings.extracted_images_dir,
        )
        thermal_images = extract_images(
            load_pdf(settings.thermal_pdf),
            "thermal",
            settings.extracted_images_dir,
        )

        self.assertGreater(len(inspection_images), 0)
        self.assertGreater(len(thermal_images), 0)


if __name__ == "__main__":
    unittest.main()
