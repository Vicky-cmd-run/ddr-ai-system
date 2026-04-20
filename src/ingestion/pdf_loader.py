from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def load_pdf(path: Path) -> PdfReader:
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")
    return PdfReader(str(path))
