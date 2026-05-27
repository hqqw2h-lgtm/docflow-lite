"""Unified intermediate representation produced by all normalizers.

After normalization the downstream pipeline (chunking → context assembly →
model call → validation) only consumes ``NormalizedDocument``. Adding support
for a new file type means writing a Normalizer that fills this shape — nothing
else in the pipeline changes.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from .enums import FileType


class NormalizedBlock(BaseModel):
    """A logical block in the document (heading, paragraph, list item, table ref, image ref).

    ``type`` is intentionally free-form (``heading`` / ``paragraph`` / ``list`` /
    ``table`` / ``image`` / ``code`` / ``other``) so new normalizers can introduce
    custom block kinds without changing the schema.
    """

    type: str
    text: str = ""
    level: int = 0  # heading level / list depth
    page: int = 0  # 1-based source page when applicable; 0 = unknown
    section: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class NormalizedTable(BaseModel):
    name: str = ""
    page: int = 0
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    markdown: str = ""  # rendered representation for prompt context


class NormalizedAsset(BaseModel):
    """Non-textual asset reference (image, attachment) for traceability."""

    kind: str  # "image" / "chart" / "attachment"
    name: str
    page: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class NormalizedDocument(BaseModel):
    """Canonical intermediate representation.

    All downstream processing depends only on this shape.
    """

    source_file_name: str
    source_file_type: FileType
    normalizer: str  # e.g. "pdf.pypdf", "excel.openpyxl"
    normalizer_version: str = "1"

    # Primary text views — downstream code prefers ``markdown`` for prompts,
    # falls back to ``text`` when markdown rendering is not meaningful.
    markdown: str = ""
    text: str = ""

    blocks: list[NormalizedBlock] = Field(default_factory=list)
    tables: list[NormalizedTable] = Field(default_factory=list)
    assets: list[NormalizedAsset] = Field(default_factory=list)

    page_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def preview(self, max_chars: int = 2000) -> str:
        """Best representation for a short preview / log."""
        body = self.markdown or self.text
        if len(body) <= max_chars:
            return body
        return body[:max_chars] + f"\n\n…[truncated, total {len(body)} chars]"


class LLMImage(BaseModel):
    """An image attachment sent to a multimodal model."""

    name: str = ""
    mime_type: str = "image/png"
    # Either an on-disk path (preferred for local providers) or base64 inline data.
    path: str = ""
    base64: str = ""
    page: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMPayload(BaseModel):
    """Final shape sent to the LLM.

    The LLM only understands two modalities: ``text`` and ``images``. Every
    pipeline path — whether it goes through a heavy normalizer (PDF/Excel) or
    short-circuits a raw text file — converges on this shape before the model
    call. ``source`` documents how the payload was produced so the trace can
    distinguish ``direct`` (no normalization) from ``normalizer:<name>``.
    """

    text: str = ""
    images: list[LLMImage] = Field(default_factory=list)
    source: str = "direct"
    warnings: list[str] = Field(default_factory=list)

    @property
    def has_content(self) -> bool:
        return bool(self.text) or bool(self.images)
