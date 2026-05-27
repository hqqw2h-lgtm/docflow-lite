from __future__ import annotations

import hashlib
import math
import mimetypes
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from time import perf_counter
from typing import Any
from xml.etree import ElementTree

from pypdf import PdfReader

from .database import new_id
from .models import (
    ContextPackageTrace,
    DocumentAssetTrace,
    DocumentChunkTrace,
    ExtractionTrace,
    NormalizedDocumentTrace,
    ProcessingPolicy,
)
from .schema_utils import SchemaInfo, field_names, schema_contract


class ContextBudgetExceeded(ValueError):
    def __init__(self, message: str, issue: dict[str, str]) -> None:
        super().__init__(message)
        self.issue = issue


@dataclass(frozen=True)
class WorkspaceProcessingContext:
    workspace_id: str
    schema_type: str
    workspace_description: str
    purpose: str


@dataclass(frozen=True)
class NormalizedBlock:
    source_range: str
    block_type: str
    markdown: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NormalizedDocument:
    id: str
    markdown: str
    text: str
    normalizer: str
    normalizer_version: str
    blocks: list[NormalizedBlock]
    tables: list[dict[str, Any]]
    assets: list[dict[str, Any]]
    warnings: list[dict[str, str]]
    duration_ms: int

    def to_trace(self) -> NormalizedDocumentTrace:
        return NormalizedDocumentTrace(
            id=self.id,
            normalizer=self.normalizer,
            normalizer_version=self.normalizer_version,
            markdown_preview=self.markdown[:1200],
            block_count=len(self.blocks),
            table_count=len(self.tables),
            asset_count=len(self.assets),
            warnings=self.warnings,
            duration_ms=self.duration_ms,
        )


@dataclass(frozen=True)
class ParsedSegment:
    source_range: str
    content: str
    chunk_type: str


@dataclass(frozen=True)
class ParsedDocument:
    text: str
    page_count: int
    segments: list[ParsedSegment]


@dataclass(frozen=True)
class ContextPreparation:
    asset: DocumentAssetTrace
    normalized: NormalizedDocument
    parsed: ParsedDocument
    chunks: list[DocumentChunkTrace]
    context_package: ContextPackageTrace
    prompt: str

    def to_trace(self) -> ExtractionTrace:
        return ExtractionTrace(
            asset=self.asset,
            normalized_document=self.normalized.to_trace(),
            chunks=self.chunks,
            context_package=self.context_package,
        )


class ApproximateTokenCounter:
    def count(self, value: str) -> int:
        if not value.strip():
            return 0
        return max(1, math.ceil(len(value) / 4))


class LargeDocumentPolicy:
    def __init__(self, policy: ProcessingPolicy) -> None:
        self.policy = policy

    def preflight(self, path: Path, file_name: str, content_type: str | None) -> DocumentAssetTrace:
        size_bytes = path.stat().st_size
        page_count = _count_pdf_pages(path)
        sheet_count = _count_spreadsheet_sheets(path)
        issues: list[dict[str, str]] = []

        if size_bytes > self.policy.async_max_bytes:
            issues.append(
                {
                    "code": "file_too_large",
                    "path": "document.size_bytes",
                    "message": "File exceeds the configured maximum async processing size.",
                }
            )
        if page_count > self.policy.max_pages:
            issues.append(
                {
                    "code": "too_many_pages",
                    "path": "document.page_count",
                    "message": "Document exceeds the configured maximum page count.",
                }
            )

        if issues:
            processing_mode = "rejected_by_policy"
            preflight_status = "rejected"
        elif size_bytes > self.policy.sync_max_bytes or page_count > self.policy.sync_max_pages:
            processing_mode = "async_required"
            preflight_status = "async_required"
            issues.append(
                {
                    "code": "async_required",
                    "path": "document.processing_mode",
                    "message": "File is accepted but should be handled by the async large-document pipeline.",
                }
            )
        else:
            processing_mode = "sync_allowed"
            preflight_status = "accepted"

        mime_type = content_type or mimetypes.guess_type(file_name)[0] or "application/octet-stream"
        return DocumentAssetTrace(
            id=new_id(),
            file_name=file_name,
            mime_type=mime_type,
            size_bytes=size_bytes,
            sha256=_sha256(path),
            page_count=page_count,
            sheet_count=sheet_count,
            processing_mode=processing_mode,
            preflight_status=preflight_status,
            preflight_issues=issues,
        )


class DocumentNormalizerRegistry:
    def __init__(self, normalizers: list["DocumentNormalizer"] | None = None) -> None:
        self.normalizers = normalizers or [
            SpreadsheetMarkdownNormalizer(),
            NativeMarkdownNormalizer(),
        ]

    def normalize(
        self,
        context: WorkspaceProcessingContext,
        path: Path,
        file_name: str,
        content_type: str | None,
        asset: DocumentAssetTrace,
    ) -> NormalizedDocument:
        return self.select(context, path, file_name, content_type, asset).normalize(context, path, file_name, content_type, asset)

    def select(
        self,
        context: WorkspaceProcessingContext,
        path: Path,
        file_name: str,
        content_type: str | None,
        asset: DocumentAssetTrace,
    ) -> "DocumentNormalizer":
        for normalizer in self.normalizers:
            if normalizer.supports(context, path, file_name, content_type, asset):
                return normalizer
        raise ContextBudgetExceeded(
            "No document normalizer is registered for this workspace and file type.",
            {
                "code": "normalizer_not_found",
                "path": "document.normalizer",
                "message": "No document normalizer is registered for this workspace and file type.",
            },
        )


class DocumentNormalizer:
    name = "document_normalizer"
    version = "1"

    def supports(
        self,
        context: WorkspaceProcessingContext,
        path: Path,
        file_name: str,
        content_type: str | None,
        asset: DocumentAssetTrace,
    ) -> bool:
        raise NotImplementedError

    def normalize(
        self,
        context: WorkspaceProcessingContext,
        path: Path,
        file_name: str,
        content_type: str | None,
        asset: DocumentAssetTrace,
    ) -> NormalizedDocument:
        raise NotImplementedError


class NativeMarkdownNormalizer(DocumentNormalizer):
    name = "native_markdown"
    version = "1"

    def supports(
        self,
        context: WorkspaceProcessingContext,
        path: Path,
        file_name: str,
        content_type: str | None,
        asset: DocumentAssetTrace,
    ) -> bool:
        return True

    def normalize(
        self,
        context: WorkspaceProcessingContext,
        path: Path,
        file_name: str,
        content_type: str | None,
        asset: DocumentAssetTrace,
    ) -> NormalizedDocument:
        started_at = perf_counter()
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            blocks, text, warnings = self._normalize_pdf(path)
        else:
            blocks, text, warnings = self._normalize_text_like(path, file_name, content_type, asset)
        markdown = _join_markdown_blocks(blocks)
        return NormalizedDocument(
            id=new_id(),
            markdown=markdown,
            text=text,
            normalizer=self.name,
            normalizer_version=self.version,
            blocks=blocks,
            tables=[],
            assets=[
                {
                    "file_name": file_name,
                    "mime_type": asset.mime_type,
                    "sha256": asset.sha256,
                    "page_count": asset.page_count,
                }
            ],
            warnings=warnings,
            duration_ms=int((perf_counter() - started_at) * 1000),
        )

    def _normalize_pdf(self, path: Path) -> tuple[list[NormalizedBlock], str, list[dict[str, str]]]:
        reader = PdfReader(str(path))
        blocks: list[NormalizedBlock] = []
        warnings: list[dict[str, str]] = []
        text_parts: list[str] = []
        for index, page in enumerate(reader.pages):
            page_number = index + 1
            page_text = (page.extract_text() or "").strip()
            if not page_text:
                warnings.append(
                    {
                        "code": "empty_pdf_page_text",
                        "path": f"page:{page_number}",
                        "message": "No embedded text was extracted. This page may require rasterization and OCR.",
                    }
                )
            markdown = f"## Page {page_number}\n\n{page_text}".strip()
            blocks.append(
                NormalizedBlock(
                    source_range=f"page:{page_number}",
                    block_type="pdf_page_markdown",
                    markdown=markdown,
                    metadata={"page": page_number, "normalization_path": "digital_pdf_text"},
                )
            )
            text_parts.append(page_text)
        return blocks, "\n".join(text_parts), warnings

    def _normalize_text_like(
        self,
        path: Path,
        file_name: str,
        content_type: str | None,
        asset: DocumentAssetTrace,
    ) -> tuple[list[NormalizedBlock], str, list[dict[str, str]]]:
        suffix = path.suffix.lower().lstrip(".") or "text"
        mime_type = content_type or asset.mime_type
        warnings: list[dict[str, str]] = []
        if mime_type.startswith("image/"):
            text = (
                f"Image document: {file_name}. OCR is not configured for this local normalizer. "
                "Use the file name, workspace context, and any user-provided document context."
            )
            markdown = f"# {file_name}\n\n![{file_name}](asset:{asset.sha256})\n\n{text}"
            warnings.append(
                {
                    "code": "image_ocr_not_configured",
                    "path": "document.normalizer",
                    "message": "Image was converted to Markdown asset metadata, but OCR text is not available.",
                }
            )
        else:
            text = path.read_bytes().decode("utf-8", errors="ignore").strip()
            markdown = text if suffix == "md" else f"# {file_name}\n\n```{suffix}\n{text}\n```"
        if not text:
            warnings.append(
                {
                    "code": "empty_text_content",
                    "path": "file",
                    "message": "The file produced no readable text during normalization.",
                }
            )
        block = NormalizedBlock(
            source_range="file",
            block_type="file_markdown",
            markdown=markdown,
            metadata={"mime_type": content_type or "", "normalization_path": "text_fast_path"},
        )
        return [block], text, warnings


class SpreadsheetMarkdownNormalizer(DocumentNormalizer):
    name = "spreadsheet_markdown"
    version = "1"

    def supports(
        self,
        context: WorkspaceProcessingContext,
        path: Path,
        file_name: str,
        content_type: str | None,
        asset: DocumentAssetTrace,
    ) -> bool:
        return path.suffix.lower() in {".xlsx", ".xlsm"}

    def normalize(
        self,
        context: WorkspaceProcessingContext,
        path: Path,
        file_name: str,
        content_type: str | None,
        asset: DocumentAssetTrace,
    ) -> NormalizedDocument:
        started_at = perf_counter()
        blocks: list[NormalizedBlock] = []
        tables: list[dict[str, Any]] = []
        warnings: list[dict[str, str]] = []
        text_parts: list[str] = []
        with zipfile.ZipFile(path) as workbook:
            shared_strings = _read_shared_strings(workbook)
            sheet_names = sorted(name for name in workbook.namelist() if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"))
            for sheet_index, sheet_name in enumerate(sheet_names[:8], start=1):
                rows = _read_sheet_rows(workbook, sheet_name, shared_strings, max_rows=400)
                if not rows:
                    continue
                markdown = _rows_to_markdown_table(rows, title=f"Sheet {sheet_index}")
                blocks.append(
                    NormalizedBlock(
                        source_range=f"sheet:{sheet_index}",
                        block_type="spreadsheet_table_markdown",
                        markdown=markdown,
                        metadata={
                            "sheet_index": sheet_index,
                            "source": sheet_name,
                            "normalization_path": "xlsx_xml_table",
                            "workspace_schema_type": context.schema_type,
                        },
                    )
                )
                tables.append(
                    {
                        "sheet_index": sheet_index,
                        "source": sheet_name,
                        "row_count": len(rows),
                        "column_count": max(len(row) for row in rows),
                        "markdown": markdown,
                    }
                )
                text_parts.extend(" | ".join(cell for cell in row if cell) for row in rows)
            if len(sheet_names) > 8:
                warnings.append(
                    {
                        "code": "spreadsheet_sheet_limit",
                        "path": "document.sheets",
                        "message": "Only the first 8 sheets were normalized for local processing.",
                    }
                )
        markdown = _join_markdown_blocks(blocks)
        text = "\n".join(text_parts) or markdown
        if not blocks:
            warnings.append(
                {
                    "code": "empty_spreadsheet_content",
                    "path": "document.sheets",
                    "message": "No readable spreadsheet rows were found during normalization.",
                }
            )
        return NormalizedDocument(
            id=new_id(),
            markdown=markdown,
            text=text,
            normalizer=self.name,
            normalizer_version=self.version,
            blocks=blocks,
            tables=tables,
            assets=[
                {
                    "file_name": file_name,
                    "mime_type": asset.mime_type,
                    "sha256": asset.sha256,
                    "sheet_count": len(tables),
                }
            ],
            warnings=warnings,
            duration_ms=int((perf_counter() - started_at) * 1000),
        )


class MarkdownChunkingStrategy:
    def __init__(self, token_counter: ApproximateTokenCounter) -> None:
        self.token_counter = token_counter

    def chunk(self, parsed: ParsedDocument, policy: ProcessingPolicy) -> list[DocumentChunkTrace]:
        chunks: list[DocumentChunkTrace] = []
        max_chars = policy.chunk_token_limit * 4
        overlap_chars = policy.chunk_overlap_tokens * 4
        for segment in parsed.segments:
            content = segment.content.strip()
            if not content:
                continue
            start = 0
            while start < len(content):
                end = min(len(content), start + max_chars)
                chunk_content = content[start:end]
                chunks.append(
                    DocumentChunkTrace(
                        id=new_id(),
                        chunk_index=len(chunks),
                        chunk_type=segment.chunk_type,
                        source_range=f"{segment.source_range}:chars:{start}-{end}",
                        token_count=self.token_counter.count(chunk_content),
                        preview=chunk_content[:900],
                    )
                )
                if end == len(content):
                    break
                start = max(end - overlap_chars, start + 1)
        if chunks:
            return chunks
        return [
            DocumentChunkTrace(
                id=new_id(),
                chunk_index=0,
                chunk_type="empty",
                source_range="file",
                token_count=0,
                preview="",
            )
        ]


class ContextEngineeringService:
    def __init__(self, token_counter: ApproximateTokenCounter) -> None:
        self.token_counter = token_counter

    def assemble(
        self,
        schema_info: SchemaInfo,
        chunks: list[DocumentChunkTrace],
        policy: ProcessingPolicy,
        workspace_description: str,
    ) -> tuple[ContextPackageTrace, str]:
        target_fields = field_names(schema_info)
        selected_chunks = self._rank_chunks(chunks, target_fields)[: policy.max_candidate_chunks]
        schema_text = schema_contract(schema_info)
        business_context = workspace_description.strip()
        fixed_prompt = (
            "You are a deterministic document extraction engine.\n"
            "Return JSON only. Do not include markdown.\n"
            "Use only the provided canonical normalized Markdown chunks and preserve table rows as arrays.\n\n"
            f"Business context:\n{business_context}\n\n"
            f"Target schema:\n{schema_text}\n\n"
            f"Target fields:\n{', '.join(target_fields) or 'custom schema'}\n\n"
        )
        fixed_tokens = self.token_counter.count(fixed_prompt)
        available_chunk_tokens = policy.context_token_budget - policy.reserved_output_tokens - fixed_tokens
        if available_chunk_tokens <= 0:
            raise ContextBudgetExceeded(
                "Schema and prompt exceed the configured context budget.",
                {
                    "code": "context_budget_exceeded",
                    "path": "processing.context_token_budget",
                    "message": "Prompt contract leaves no budget for document chunks.",
                },
            )

        accepted: list[DocumentChunkTrace] = []
        used_tokens = fixed_tokens
        for chunk in selected_chunks:
            if chunk.token_count <= available_chunk_tokens:
                accepted.append(chunk)
                available_chunk_tokens -= chunk.token_count
                used_tokens += chunk.token_count

        if not accepted and any(chunk.preview for chunk in chunks):
            raise ContextBudgetExceeded(
                "No document chunk fits the configured context budget.",
                {
                    "code": "chunk_budget_exceeded",
                    "path": "processing.chunk_token_limit",
                    "message": "No candidate chunk can fit into the remaining model context budget.",
                },
            )

        chunk_text = "\n\n".join(
            f"[chunk:{chunk.id} source:{chunk.source_range}]\n{chunk.preview}"
            for chunk in accepted
        )
        prompt = f"{fixed_prompt}Normalized Markdown chunks:\n{chunk_text}\n"
        package = ContextPackageTrace(
            id=new_id(),
            chunk_ids=[chunk.id for chunk in accepted],
            token_budget=policy.context_token_budget,
            estimated_input_tokens=used_tokens,
            reserved_output_tokens=policy.reserved_output_tokens,
            assembly_strategy="balanced_markdown_chunk_budget",
            target_fields=target_fields,
        )
        return package, prompt

    def _rank_chunks(
        self,
        chunks: list[DocumentChunkTrace],
        target_fields: list[str],
    ) -> list[DocumentChunkTrace]:
        normalized_fields = [field.lower() for field in target_fields]

        def score(chunk: DocumentChunkTrace) -> tuple[int, int]:
            text = chunk.preview.lower()
            matches = sum(1 for field in normalized_fields if field and field in text)
            return (-matches, chunk.chunk_index)

        return sorted(chunks, key=score)


class DocumentProcessingService:
    def __init__(self, policy: ProcessingPolicy) -> None:
        self.policy = policy
        self.token_counter = ApproximateTokenCounter()
        self.large_document_policy = LargeDocumentPolicy(policy)
        self.normalizer_registry = DocumentNormalizerRegistry()
        self.chunking_strategy = MarkdownChunkingStrategy(self.token_counter)
        self.context_service = ContextEngineeringService(self.token_counter)

    def prepare(
        self,
        path: Path,
        file_name: str,
        content_type: str | None,
        schema_info: SchemaInfo,
        workspace_description: str,
        workspace_context: WorkspaceProcessingContext,
    ) -> ContextPreparation:
        asset, normalized = self.normalize_asset(path, file_name, content_type, workspace_context)
        parsed = ParsedDocument(
            text=normalized.text,
            page_count=asset.page_count,
            segments=[
                ParsedSegment(
                    source_range=block.source_range,
                    content=block.markdown,
                    chunk_type=block.block_type,
                )
                for block in normalized.blocks
            ],
        )
        chunks = self.chunking_strategy.chunk(parsed, self.policy)
        context_package, prompt = self.context_service.assemble(
            schema_info,
            chunks,
            self.policy,
            workspace_description,
        )
        return ContextPreparation(
            asset=asset,
            normalized=normalized,
            parsed=parsed,
            chunks=chunks,
            context_package=context_package,
            prompt=prompt,
        )

    def normalize_asset(
        self,
        path: Path,
        file_name: str,
        content_type: str | None,
        workspace_context: WorkspaceProcessingContext,
    ) -> tuple[DocumentAssetTrace, NormalizedDocument]:
        asset = self.large_document_policy.preflight(path, file_name, content_type)
        if asset.processing_mode == "rejected_by_policy":
            raise ContextBudgetExceeded(
                "Document rejected by processing policy.",
                asset.preflight_issues[0],
            )
        normalized = self.normalizer_registry.normalize(workspace_context, path, file_name, content_type, asset)
        return asset, normalized


def normalized_blocks_to_payload(blocks: list[NormalizedBlock]) -> list[dict[str, Any]]:
    return [
        {
            "source_range": block.source_range,
            "block_type": block.block_type,
            "markdown": block.markdown,
            "metadata": block.metadata,
        }
        for block in blocks
    ]


def _join_markdown_blocks(blocks: list[NormalizedBlock]) -> str:
    return "\n\n".join(block.markdown.strip() for block in blocks if block.markdown.strip())


def _count_pdf_pages(path: Path) -> int:
    if path.suffix.lower() != ".pdf":
        return 0
    try:
        return len(PdfReader(str(path)).pages)
    except Exception:
        return 0


def _count_spreadsheet_sheets(path: Path) -> int:
    if path.suffix.lower() not in {".xlsx", ".xlsm"}:
        return 0
    try:
        with zipfile.ZipFile(path) as workbook:
            return sum(1 for name in workbook.namelist() if name.startswith("xl/worksheets/sheet") and name.endswith(".xml"))
    except Exception:
        return 0


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_shared_strings(workbook: zipfile.ZipFile) -> list[str]:
    if "xl/sharedStrings.xml" not in workbook.namelist():
        return []
    root = ElementTree.fromstring(workbook.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in root.iter(_xlsx_tag("si")):
        fragments = [node.text or "" for node in item.iter(_xlsx_tag("t"))]
        values.append("".join(fragments))
    return values


def _read_sheet_rows(
    workbook: zipfile.ZipFile,
    sheet_name: str,
    shared_strings: list[str],
    max_rows: int,
) -> list[list[str]]:
    root = ElementTree.fromstring(workbook.read(sheet_name))
    rows: list[list[str]] = []
    for row in root.iter(_xlsx_tag("row")):
        values = [_cell_value(cell, shared_strings) for cell in row.iter(_xlsx_tag("c"))]
        if any(value for value in values):
            rows.append(values)
        if len(rows) >= max_rows:
            break
    return rows


def _cell_value(cell: ElementTree.Element, shared_strings: list[str]) -> str:
    value_node = cell.find(_xlsx_tag("v"))
    if value_node is None or value_node.text is None:
        return ""
    raw_value = value_node.text
    if cell.attrib.get("t") == "s":
        index = int(raw_value)
        return shared_strings[index] if 0 <= index < len(shared_strings) else ""
    return raw_value


def _rows_to_markdown_table(rows: list[list[str]], title: str) -> str:
    width = max(len(row) for row in rows)
    padded = [row + [""] * (width - len(row)) for row in rows]
    if len(padded) == 1:
        headers = [f"Column {index + 1}" for index in range(width)]
        body_rows = padded
    else:
        headers = [cell or f"Column {index + 1}" for index, cell in enumerate(padded[0])]
        body_rows = padded[1:]
    header = "| " + " | ".join(_escape_markdown_cell(cell) for cell in headers) + " |"
    divider = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(_escape_markdown_cell(cell) for cell in row) + " |" for row in body_rows]
    return "\n".join([f"## {title}", "", header, divider, *body])


def _escape_markdown_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ").strip()


def _xlsx_tag(name: str) -> str:
    return f"{{http://schemas.openxmlformats.org/spreadsheetml/2006/main}}{name}"
