from __future__ import annotations

import os
from pathlib import Path
from unittest import TestCase


# 你可以直接改这里，或者设置环境变量 DOCFLOW_TEST_PDF
TEST_PDF_PATH = Path(
    os.getenv(
        "DOCFLOW_TEST_PDF",
        r"C:\Users\haw5wx\Desktop\26327000000639395306.pdf",
    )
)


class DoclingPdfToMarkdownTest(TestCase):
    def test_convert_pdf_to_markdown(self) -> None:
        try:
            from docling.document_converter import DocumentConverter
        except Exception as exc:  # noqa: BLE001
            self.skipTest(f"docling is not installed or unavailable: {exc}")
            return

        if not TEST_PDF_PATH.exists():
            self.skipTest(
                "Test PDF not found. Set DOCFLOW_TEST_PDF env or edit TEST_PDF_PATH "
                f"(current: {TEST_PDF_PATH})"
            )
            return

        converter = DocumentConverter()
        result = converter.convert(str(TEST_PDF_PATH))
        markdown = result.document.export_to_markdown()

        self.assertIsInstance(markdown, str)
        self.assertTrue(markdown.strip(), "Docling returned empty markdown")
        has_text_char = any(ch.isalnum() for ch in markdown)
        self.assertTrue(has_text_char, "Docling markdown has no readable text content")
