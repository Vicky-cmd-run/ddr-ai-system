from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def load_pdf(path: Path) -> PdfReader:
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")
    reader = PdfReader(str(path))
    reader.source_path = str(path)  # Image extraction uses the original PDF path when it needs page rendering instead of low-resolution embedded assets.
    return reader
