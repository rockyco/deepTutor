"""
Vector graphics extraction from PDFs using PyMuPDF.

This module provides utilities to extract rectangular regions from PDFs
as SVG (vector) or high-quality PNG (raster) images. SVG extraction
preserves vector sharpness at any zoom level.
"""

import pymupdf
from pathlib import Path
from typing import Union, Optional


class VectorExtractor:
    """Extract vector graphics from PDFs using PyMuPDF."""

    def __init__(self, pdf_path: Union[str, Path]):
        """
        Initialize extractor with a PDF file.

        Args:
            pdf_path: Path to the PDF file
        """
        self.pdf_path = Path(pdf_path)
        self._doc: Optional[pymupdf.Document] = None

    def __enter__(self):
        self._doc = pymupdf.open(self.pdf_path)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._doc:
            self._doc.close()
            self._doc = None

    @property
    def doc(self) -> pymupdf.Document:
        if self._doc is None:
            raise RuntimeError("VectorExtractor must be used as context manager")
        return self._doc

    @property
    def page_count(self) -> int:
        return len(self.doc)

    def get_page(self, page_num: int) -> pymupdf.Page:
        """Get a page by index (0-based)."""
        return self.doc[page_num]

    def extract_region_as_svg(
        self,
        page_num: int,
        bbox: tuple[float, float, float, float],
        text_as_path: bool = True,
    ) -> str:
        """
        Extract a rectangular region from a PDF page as SVG.

        Uses PyMuPDF's show_pdf_page() to render a clipped region
        onto a new page, then exports as SVG.

        Args:
            page_num: Page index (0-based)
            bbox: Bounding box as (x0, y0, x1, y1) in PDF coordinates
            text_as_path: Convert text to paths for consistent rendering

        Returns:
            SVG content as string
        """
        x0, y0, x1, y1 = bbox
        clip_rect = pymupdf.Rect(x0, y0, x1, y1)

        # Create a new document with a single page sized to the clip region
        new_doc = pymupdf.open()
        new_page = new_doc.new_page(width=clip_rect.width, height=clip_rect.height)

        # Render the clipped region from source onto the new page
        new_page.show_pdf_page(
            new_page.rect,
            self.doc,
            page_num,
            clip=clip_rect,
        )

        # Export as SVG
        svg_content = new_page.get_svg_image(text_as_path=text_as_path)
        new_doc.close()

        return svg_content

    def extract_region_as_png(
        self,
        page_num: int,
        bbox: tuple[float, float, float, float],
        dpi: int = 600,
    ) -> bytes:
        """
        Extract a rectangular region as high-quality PNG.

        Primary method for PDF extraction - produces clean output without
        the font definitions and text artifacts that SVG extraction includes.

        Args:
            page_num: Page index (0-based)
            bbox: Bounding box as (x0, y0, x1, y1) in PDF coordinates
            dpi: Resolution in dots per inch

        Returns:
            PNG image data as bytes
        """
        x0, y0, x1, y1 = bbox
        clip_rect = pymupdf.Rect(x0, y0, x1, y1)

        page = self.doc[page_num]
        # Calculate zoom factor from DPI (72 is PDF default)
        zoom = dpi / 72.0
        mat = pymupdf.Matrix(zoom, zoom)

        # Render with clipping
        pix = page.get_pixmap(matrix=mat, clip=clip_rect)
        return pix.tobytes("png")

    def extract_words(self, page_num: int) -> list[dict]:
        """
        Extract words with their bounding boxes from a page.

        Provides similar functionality to pdfplumber's extract_words()
        for compatibility.

        Args:
            page_num: Page index (0-based)

        Returns:
            List of word dicts with 'text', 'x0', 'y0', 'x1', 'y1', 'top', 'bottom'
        """
        page = self.doc[page_num]
        words = []

        for block in page.get_text("dict")["blocks"]:
            if block["type"] != 0:  # Skip non-text blocks
                continue
            for line in block["lines"]:
                for span in line["spans"]:
                    bbox = span["bbox"]
                    words.append({
                        "text": span["text"].strip(),
                        "x0": bbox[0],
                        "y0": bbox[1],
                        "x1": bbox[2],
                        "y1": bbox[3],
                        "top": bbox[1],
                        "bottom": bbox[3],
                    })

        return words

    def extract_text(self, page_num: int) -> str:
        """Extract all text from a page."""
        return self.doc[page_num].get_text()

    def get_page_dimensions(self, page_num: int) -> tuple[float, float]:
        """Get page width and height."""
        page = self.doc[page_num]
        return page.rect.width, page.rect.height

    def extract_drawings(self, page_num: int) -> list[dict]:
        """
        Extract vector drawing paths from a page.

        Returns raw path data that can be converted to SVG manually
        if needed for more granular control.

        Args:
            page_num: Page index (0-based)

        Returns:
            List of drawing dictionaries with path commands
        """
        page = self.doc[page_num]
        return page.get_drawings()


def save_svg(content: str, path: Union[str, Path]) -> None:
    """Save SVG content to file."""
    Path(path).write_text(content, encoding="utf-8")


def save_png(data: bytes, path: Union[str, Path]) -> None:
    """Save PNG data to file."""
    Path(path).write_bytes(data)
