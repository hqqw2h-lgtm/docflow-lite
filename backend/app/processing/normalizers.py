"""Normalizer plugin registry.

A Normalizer converts a raw source file into a ``NormalizedDocument`` — the
single intermediate representation all downstream pipeline steps consume
(chunking → context assembly → model call → validation).

Adding a new file type means writing one ``Normalizer`` subclass and
registering it. Nothing else in the pipeline changes.
"""
from __future__ import annotations

import threading
from abc import ABC, abstractmethod
from pathlib import Path

from pypdf import PdfReader

from ..domain import (
    FileType,
    LLMImage,
    LLMPayload,
    NormalizedAsset,
    NormalizedBlock,
    NormalizedDocument,
    NormalizedTable,
)


class Normalizer(ABC):
    """Strategy that turns a raw file into a unified ``NormalizedDocument``."""

    name: str = ""
    version: str = "1"
    supported_types: tuple[FileType, ...] = ()

    @abstractmethod
    def normalize(self, path: Path, *, file_name: str, file_type: FileType) -> NormalizedDocument: ...


# --------------------------------------------------------------------------- #
# Built-in normalizers
# --------------------------------------------------------------------------- #


class _PypdfFallbackNormalizer:
    """Used both as a standalone fallback and inside MarkerPdfNormalizer."""

    name = "pdf.pypdf"
    version = "1"

    def normalize(self, path: Path, *, file_name: str, file_type: FileType) -> NormalizedDocument:
        warnings: list[str] = []
        blocks: list[NormalizedBlock] = []
        markdown_parts: list[str] = []
        text_parts: list[str] = []
        page_count = 0

        try:
            reader = PdfReader(str(path))
            page_count = len(reader.pages)
            for index, page in enumerate(reader.pages, start=1):
                page_text = (page.extract_text() or "").strip()
                if not page_text:
                    warnings.append(f"page {index} produced no extractable text")
                    continue
                text_parts.append(page_text)
                markdown_parts.append(f"## Page {index}\n\n{page_text}")
                blocks.append(NormalizedBlock(
                    type="paragraph",
                    text=page_text,
                    page=index,
                    section=f"Page {index}",
                ))
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"pdf parse failed: {exc}")

        return NormalizedDocument(
            source_file_name=file_name,
            source_file_type=file_type,
            normalizer=self.name,
            normalizer_version=self.version,
            markdown="\n\n".join(markdown_parts),
            text="\n\n".join(text_parts),
            blocks=blocks,
            page_count=page_count,
            warnings=warnings,
        )


class PdfNormalizer(Normalizer):
    """PDF → markdown via the `marker` deep-learning framework.

    Marker produces far higher-quality markdown than naive pdf-text extraction:
    it preserves headings, tables, lists, code blocks, equations, and emits
    embedded images. Because the model dictionary is expensive to construct
    (several GB of weights), the converter is loaded **lazily** and cached as
    a process-wide singleton. The first PDF in a process pays the model-load
    cost; every subsequent PDF reuses it.

    If marker is not installed or fails (e.g. CUDA missing, OOM, corrupt PDF),
    we fall back to the pypdf text extractor so the pipeline keeps working.
    """

    name = "pdf.marker"
    version = "1"
    supported_types = (FileType.PDF,)

    _converter = None  # lazily-initialised marker PdfConverter
    _converter_lock = threading.Lock()
    _converter_unavailable_reason: str = ""
    _fallback = _PypdfFallbackNormalizer()

    @classmethod
    def _get_converter(cls):
        """Return a cached marker PdfConverter, or ``None`` if unavailable."""
        if cls._converter is not None:
            return cls._converter
        if cls._converter_unavailable_reason:
            return None
        with cls._converter_lock:
            if cls._converter is not None:
                return cls._converter
            if cls._converter_unavailable_reason:
                return None
            try:
                from marker.converters.pdf import PdfConverter  # type: ignore
                from marker.models import create_model_dict  # type: ignore
                cls._converter = PdfConverter(artifact_dict=create_model_dict())
            except Exception as exc:  # noqa: BLE001
                cls._converter_unavailable_reason = f"{type(exc).__name__}: {exc}"
                cls._converter = None
            return cls._converter

    def normalize(self, path: Path, *, file_name: str, file_type: FileType) -> NormalizedDocument:
        converter = self._get_converter()
        if converter is None:
            doc = self._fallback.normalize(path, file_name=file_name, file_type=file_type)
            reason = self._converter_unavailable_reason or "marker unavailable"
            doc.warnings.insert(0, f"marker unavailable, used pypdf fallback ({reason})")
            return doc

        warnings: list[str] = []
        markdown = ""
        assets: list[NormalizedAsset] = []
        page_count = 0
        metadata: dict = {}

        try:
            from marker.output import text_from_rendered  # type: ignore
            rendered = converter(str(path))
            markdown, _ext, images = text_from_rendered(rendered)
            for image_name in (images or {}).keys():
                assets.append(NormalizedAsset(kind="image", name=str(image_name)))
            meta = getattr(rendered, "metadata", None) or {}
            if isinstance(meta, dict):
                metadata = meta
                page_count = int(meta.get("page_count") or meta.get("pages") or 0)
        except Exception as exc:  # noqa: BLE001
            # Marker loaded but conversion failed → fall back to pypdf for this file.
            doc = self._fallback.normalize(path, file_name=file_name, file_type=file_type)
            doc.warnings.insert(0, f"marker conversion failed, used pypdf fallback: {exc}")
            return doc

        if not markdown.strip():
            warnings.append("marker produced empty markdown")

        return NormalizedDocument(
            source_file_name=file_name,
            source_file_type=file_type,
            normalizer=self.name,
            normalizer_version=self.version,
            markdown=markdown,
            text=markdown,
            assets=assets,
            page_count=page_count,
            metadata=metadata,
            warnings=warnings,
        )


class ExcelNormalizer(Normalizer):
    name = "excel.openpyxl"
    supported_types = (FileType.EXCEL,)

    def normalize(self, path: Path, *, file_name: str, file_type: FileType) -> NormalizedDocument:
        warnings: list[str] = []
        tables: list[NormalizedTable] = []
        markdown_parts: list[str] = []
        text_parts: list[str] = []

        try:
            from openpyxl import load_workbook  # type: ignore[import-not-found]
        except ImportError:
            warnings.append("openpyxl not installed; falling back to plain text read")
            return _plain_text_document(path, file_name, file_type, warnings)

        try:
            wb = load_workbook(filename=str(path), data_only=True, read_only=True)
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                rows = [
                    ["" if cell is None else str(cell) for cell in row]
                    for row in ws.iter_rows(values_only=True)
                ]
                if not rows:
                    continue
                headers = rows[0]
                data_rows = rows[1:]
                table_md = _render_table_markdown(headers, data_rows)
                tables.append(NormalizedTable(
                    name=sheet_name,
                    headers=headers,
                    rows=data_rows,
                    markdown=table_md,
                ))
                markdown_parts.append(f"## Sheet: {sheet_name}\n\n{table_md}")
                text_parts.append(
                    f"Sheet: {sheet_name}\n"
                    + "\n".join("\t".join(r) for r in rows)
                )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"excel parse failed: {exc}")

        return NormalizedDocument(
            source_file_name=file_name,
            source_file_type=file_type,
            normalizer=self.name,
            normalizer_version=self.version,
            markdown="\n\n".join(markdown_parts),
            text="\n\n".join(text_parts),
            tables=tables,
            warnings=warnings,
            metadata={"sheet_count": len(tables)},
        )


class CsvNormalizer(Normalizer):
    name = "csv.builtin"
    supported_types = (FileType.CSV,)

    def normalize(self, path: Path, *, file_name: str, file_type: FileType) -> NormalizedDocument:
        import csv

        warnings: list[str] = []
        rows: list[list[str]] = []
        try:
            with path.open("r", encoding="utf-8", errors="ignore", newline="") as fh:
                rows = [list(r) for r in csv.reader(fh)]
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"csv parse failed: {exc}")

        headers = rows[0] if rows else []
        data_rows = rows[1:] if len(rows) > 1 else []
        table_md = _render_table_markdown(headers, data_rows)
        table = NormalizedTable(name=path.stem, headers=headers, rows=data_rows, markdown=table_md)
        text = "\n".join(",".join(r) for r in rows)
        return NormalizedDocument(
            source_file_name=file_name,
            source_file_type=file_type,
            normalizer=self.name,
            normalizer_version=self.version,
            markdown=table_md,
            text=text,
            tables=[table] if rows else [],
            warnings=warnings,
            metadata={"row_count": len(data_rows)},
        )


class PlainTextNormalizer(Normalizer):
    """Handles TEXT / JSON / MARKDOWN — keep markdown when the source already is markdown."""

    name = "text.builtin"
    supported_types = (FileType.TEXT, FileType.JSON, FileType.MARKDOWN)

    def normalize(self, path: Path, *, file_name: str, file_type: FileType) -> NormalizedDocument:
        return _plain_text_document(path, file_name, file_type, [])


class ImageNormalizer(Normalizer):
    """Placeholder for images — emits an asset entry and a warning.

    Real OCR can be plugged in later by registering a replacement for FileType.IMAGE.
    """

    name = "image.placeholder"
    supported_types = (FileType.IMAGE,)

    def normalize(self, path: Path, *, file_name: str, file_type: FileType) -> NormalizedDocument:
        warning = "image OCR is not enabled in this build; only file metadata is captured."
        return NormalizedDocument(
            source_file_name=file_name,
            source_file_type=file_type,
            normalizer=self.name,
            normalizer_version=self.version,
            markdown=f"![{file_name}]({file_name})",
            text="",
            assets=[NormalizedAsset(kind="image", name=file_name, metadata={"path": str(path)})],
            warnings=[warning],
        )


# --------------------------------------------------------------------------- #
# Registry — normalizers are addressable by name (primary) and by file_type
# (default-resolution fallback). A SchemaSpace can pin a specific normalizer
# name per file_type via its ``normalizer_overrides`` map, otherwise the
# default registered for that file_type is used.
# --------------------------------------------------------------------------- #


_REGISTRY_BY_NAME: dict[str, Normalizer] = {}
_DEFAULT_BY_TYPE: dict[FileType, str] = {}  # file_type → default normalizer name


def register(normalizer: Normalizer, *, make_default: bool = True) -> None:
    """Register a normalizer.

    ``make_default=True`` (the default) also sets this normalizer as the default
    for each of its ``supported_types`` when no other default is set yet, or
    unconditionally overrides existing defaults if you re-register. Pass
    ``False`` to register a normalizer as an *alternative* without changing
    the per-type default.
    """
    if not normalizer.name:
        raise ValueError("Normalizer.name must be set")
    _REGISTRY_BY_NAME[normalizer.name] = normalizer
    if make_default:
        for ft in normalizer.supported_types:
            _DEFAULT_BY_TYPE[ft] = normalizer.name


def get_normalizer_by_name(name: str) -> Normalizer:
    if name not in _REGISTRY_BY_NAME:
        raise ValueError(f"No normalizer registered with name: {name}")
    return _REGISTRY_BY_NAME[name]


def get_normalizer(file_type: FileType) -> Normalizer:
    """Resolve the default normalizer for a file type."""
    name = _DEFAULT_BY_TYPE.get(file_type)
    if name is None:
        raise ValueError(f"No normalizer registered for file type: {file_type.value}")
    return _REGISTRY_BY_NAME[name]


def resolve_normalizer(file_type: FileType, override_name: str = "") -> Normalizer:
    """Pick the normalizer for ``file_type``, honouring an optional override.

    ``override_name`` is typically sourced from ``SchemaSpace.normalizer_overrides``.
    If the named normalizer is not registered or does not support ``file_type``,
    a ``ValueError`` is raised so the caller can surface a clear error.
    """
    if override_name:
        normalizer = get_normalizer_by_name(override_name)
        if file_type not in normalizer.supported_types:
            raise ValueError(
                f"Normalizer '{override_name}' does not support file_type '{file_type.value}'. "
                f"Supported: {[ft.value for ft in normalizer.supported_types]}"
            )
        return normalizer
    return get_normalizer(file_type)


def list_normalizers() -> list[dict]:
    """Catalog of registered normalizers — used by the UI to populate the per-SchemaSpace override picker."""
    items: list[dict] = []
    for name, normalizer in sorted(_REGISTRY_BY_NAME.items()):
        items.append({
            "name": name,
            "version": normalizer.version,
            "supported_types": [ft.value for ft in normalizer.supported_types],
            "is_default_for": [
                ft.value for ft, default_name in _DEFAULT_BY_TYPE.items() if default_name == name
            ],
        })
    return items


def list_normalizers_for_file_type(file_type: FileType) -> list[str]:
    """All registered normalizer names that declare support for ``file_type``.

    Used by the optimizer to enumerate candidate normalizers per file_type.
    Returned in deterministic order with the registry default first so the
    optimizer evaluates the current default before alternatives.
    """
    matches = [
        name for name, n in _REGISTRY_BY_NAME.items() if file_type in n.supported_types
    ]
    default = _DEFAULT_BY_TYPE.get(file_type)
    if default and default in matches:
        matches.remove(default)
        matches.insert(0, default)
    return matches


def normalize(path: Path, *, file_name: str, file_type: FileType, normalizer_name: str = "") -> NormalizedDocument:
    """Run a normalizer for the given file_type, optionally overridden by name."""
    return resolve_normalizer(file_type, normalizer_name).normalize(
        path, file_name=file_name, file_type=file_type,
    )


# --------------------------------------------------------------------------- #
# LLM payload builder
# --------------------------------------------------------------------------- #

# File types the LLM consumes verbatim — no normalization step required.
TEXT_NATIVE_TYPES: frozenset[FileType] = frozenset({
    FileType.TEXT,
    FileType.MARKDOWN,
    FileType.JSON,
    FileType.CSV,
})

# File types the LLM treats as images (multimodal input).
IMAGE_NATIVE_TYPES: frozenset[FileType] = frozenset({FileType.IMAGE})


def build_llm_payload(
    path: Path,
    *,
    file_name: str,
    file_type: FileType,
    normalizer_override: str = "",
) -> tuple[LLMPayload, NormalizedDocument | None]:
    """Produce the payload sent to the LLM, skipping normalization when possible.

    Returns ``(payload, normalized_document_or_None)``.

    * ``normalized_document is None`` → normalization was **skipped** because the
      input is already in a shape the LLM consumes natively (plain text or image)
      AND no explicit ``normalizer_override`` forced one.
    * ``normalized_document is not None`` → a normalizer ran and its
      ``NormalizedDocument`` was reduced into the payload.

    ``normalizer_override`` lets a SchemaSpace pin a specific normalizer per
    file_type (looked up by name in the registry). When set, normalization is
    NOT skipped even for text-native types — the SchemaSpace explicitly opted in
    to a custom processing step.
    """
    # Explicit override always runs the named normalizer, regardless of file_type
    # being text-native — the SchemaSpace deliberately opted in.
    if normalizer_override:
        normalized = normalize(
            path, file_name=file_name, file_type=file_type, normalizer_name=normalizer_override,
        )
        payload = LLMPayload(
            text=normalized.markdown or normalized.text,
            source=f"normalizer:{normalized.normalizer}",
            warnings=list(normalized.warnings),
        )
        return payload, normalized

    # 1. Text-native: read directly, no normalizer call.
    if file_type in TEXT_NATIVE_TYPES:
        try:
            body = path.read_text(encoding="utf-8", errors="ignore")
            warnings: list[str] = []
        except Exception as exc:  # noqa: BLE001
            body = ""
            warnings = [f"text read failed: {exc}"]
        return LLMPayload(text=body, source="direct", warnings=warnings), None

    # 2. Image-native: hand straight to a multimodal model.
    if file_type in IMAGE_NATIVE_TYPES:
        mime = _guess_image_mime(file_name)
        image = LLMImage(name=file_name, mime_type=mime, path=str(path))
        return LLMPayload(images=[image], source="direct"), None

    # 3. Binary / structured formats — run the default registered normalizer.
    normalized = normalize(path, file_name=file_name, file_type=file_type)
    payload = LLMPayload(
        text=normalized.markdown or normalized.text,
        source=f"normalizer:{normalized.normalizer}",
        warnings=list(normalized.warnings),
    )
    return payload, normalized


def _guess_image_mime(file_name: str) -> str:
    suffix = file_name.lower().rsplit(".", 1)[-1] if "." in file_name else ""
    return {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "tif": "image/tiff",
        "tiff": "image/tiff",
    }.get(suffix, "application/octet-stream")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _plain_text_document(
    path: Path, file_name: str, file_type: FileType, warnings: list[str]
) -> NormalizedDocument:
    try:
        body = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:  # noqa: BLE001
        warnings = [*warnings, f"text read failed: {exc}"]
        body = ""
    markdown = body if file_type == FileType.MARKDOWN else f"```\n{body}\n```"
    if file_type == FileType.JSON:
        markdown = f"```json\n{body}\n```"
    return NormalizedDocument(
        source_file_name=file_name,
        source_file_type=file_type,
        normalizer=PlainTextNormalizer.name,
        normalizer_version=PlainTextNormalizer.version,
        markdown=markdown,
        text=body,
        warnings=warnings,
    )


def _render_table_markdown(headers: list[str], rows: list[list[str]]) -> str:
    if not headers and not rows:
        return ""
    width = max(len(headers), max((len(r) for r in rows), default=0))
    headers = headers + [""] * (width - len(headers))
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * width) + " |"]
    for row in rows:
        padded = row + [""] * (width - len(row))
        lines.append("| " + " | ".join(padded) + " |")
    return "\n".join(lines)


class PypdfNormalizer(Normalizer):
    """Lightweight pure-Python PDF normalizer (no model weights).

    Registered as an **alternative** to ``PdfNormalizer`` (marker). A
    SchemaSpace can pin this in ``normalizer_overrides`` when marker is too
    expensive for its data or unavailable.
    """

    name = "pdf.pypdf"
    version = "1"
    supported_types = (FileType.PDF,)

    _impl = _PypdfFallbackNormalizer()

    def normalize(self, path: Path, *, file_name: str, file_type: FileType) -> NormalizedDocument:
        return self._impl.normalize(path, file_name=file_name, file_type=file_type)


# Register built-ins on import. Defaults are set in registration order — the
# marker-backed PdfNormalizer wins for FileType.PDF; PypdfNormalizer is also
# discoverable by name as an alternative.
for _normalizer in (
    PdfNormalizer(),
    ExcelNormalizer(),
    CsvNormalizer(),
    PlainTextNormalizer(),
    ImageNormalizer(),
):
    register(_normalizer)

register(PypdfNormalizer(), make_default=False)
