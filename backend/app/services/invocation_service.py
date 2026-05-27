"""Invocation pipeline: orchestrates normalize → context → model → validate → trace.

Every invocation (UI extraction, API call, sample re-run, replay) goes through
this single entry point so every run produces a complete Trace record for
admin observability.
"""
from __future__ import annotations

import hashlib
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile

from ..database import UPLOAD_DIR, encode_json, get_session, new_id, utc_now
from ..db.records import InvocationRecord, TraceRecord
from ..domain import (
    FileType,
    Invocation,
    InvocationSource,
    InvocationStatus,
    LLMPayload,
    NormalizedDocument,
    Trace,
    TraceSpan,
    TraceSpanType,
    VersionStatus,
)
from ..repositories import InvocationRepo, SchemaSpaceRepo, TraceRepo, VersionRepo
from ..schema_utils import schema_contract, validate_output
from .component_resolver import build_llm_payload_for_space, resolve_components, resolve_model_provider
from .mappers import invocation_from_record, schema_space_from_record, trace_from_record, version_from_record


class _SpanRecorder:
    """Tiny helper that captures span timing + summaries during a pipeline run."""

    def __init__(self) -> None:
        self.spans: list[TraceSpan] = []

    def record(
        self,
        span_type: TraceSpanType | str,
        *,
        status: str,
        input_summary: dict[str, Any] | None = None,
        output_summary: dict[str, Any] | None = None,
        duration_ms: int = 0,
        started_at: datetime | None = None,
        ended_at: datetime | None = None,
        error: str = "",
    ) -> None:
        started = started_at or datetime.utcnow()
        ended = ended_at or started
        self.spans.append(TraceSpan(
            type=span_type.value if isinstance(span_type, TraceSpanType) else span_type,
            started_at=started,
            ended_at=ended,
            duration_ms=duration_ms,
            status=status,
            input_summary=input_summary or {},
            output_summary=output_summary or {},
            error=error,
        ))


class InvocationService:
    def __init__(self) -> None:
        self.space_repo = SchemaSpaceRepo()
        self.version_repo = VersionRepo()
        self.invocation_repo = InvocationRepo()
        self.trace_repo = TraceRepo()

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #

    def list(self, *, space_id: str = "", version_id: str = "", source: str = "", status: str = "", limit: int = 100) -> list[Invocation]:
        with get_session() as session:
            if space_id:
                records = self.invocation_repo.list_by_space(
                    session, space_id, version_id=version_id, source=source, status=status, limit=limit,
                )
            else:
                records = self.invocation_repo.search(
                    session, version_id=version_id, source=source, status=status, limit=limit,
                )
            return [invocation_from_record(r) for r in records]

    def get(self, invocation_id: str) -> Invocation:
        with get_session() as session:
            record = self.invocation_repo.get(session, invocation_id)
            if record is None:
                raise HTTPException(status_code=404, detail="Invocation not found")
            return invocation_from_record(record)

    def get_trace(self, invocation_id: str) -> Trace:
        with get_session() as session:
            record = self.trace_repo.get_by_invocation(session, invocation_id)
            if record is None:
                raise HTTPException(status_code=404, detail="Trace not found")
            return trace_from_record(record)

    async def invoke_upload(
        self,
        *,
        version_id: str,
        file: UploadFile,
        document_context: str,
        source: InvocationSource,
        parent_invocation_id: str = "",
    ) -> Invocation:
        with get_session() as session:
            version_record = self.version_repo.get(session, version_id)
            if version_record is None:
                raise HTTPException(status_code=404, detail="Version not found")
            if version_record.status != VersionStatus.PUBLISHED.value and source != InvocationSource.SAMPLE:
                raise HTTPException(
                    status_code=409,
                    detail="Only published versions can be invoked.",
                )
            space_record = self.space_repo.get(session, version_record.schema_space_id)
            if space_record is None:
                raise HTTPException(status_code=404, detail="SchemaSpace not found")

            # Hydrate domain objects — from here on everything goes through
            # the SchemaSpace-aware component resolver. The pipeline never
            # reads space/version fields directly.
            space = schema_space_from_record(space_record)
            version = version_from_record(version_record)
            effective = resolve_components(space, version)

            file_name = Path(file.filename or "input").name
            file_type = self._assert_file_type_allowed(space, file_name)

            content = await file.read()
            sha = hashlib.sha256(content).hexdigest()
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            stored_path = UPLOAD_DIR / f"{new_id()}-{file_name}"
            stored_path.write_bytes(content)

            schema_info = version.schema_info
            if not schema_info or schema_info == {"outputType": "json", "children": []}:
                schema_info = space.schema_info or {"outputType": "json", "children": []}

            invocation_id = new_id()
            started_at_str = utc_now()
            started_perf = time.perf_counter()
            recorder = _SpanRecorder()

            # ----- preflight ----- #
            preflight_start = datetime.utcnow()
            recorder.record(
                TraceSpanType.PREFLIGHT,
                status="ok",
                input_summary={
                    "file_name": file_name,
                    "size_bytes": len(content),
                    "sha256": sha,
                    "schema_space_id": space.id,
                    "version_id": version.id,
                },
                output_summary={"detected_type": file_type.value},
                started_at=preflight_start,
                ended_at=datetime.utcnow(),
            )

            # ----- normalize (optional) ----- #
            # Routed entirely by SchemaSpace context via the resolver. When
            # ``override`` is empty and the file is text/image-native, the
            # resolver short-circuits and the span is recorded as ``skipped``.
            norm_start = datetime.utcnow()
            normalize_error = ""
            normalized: NormalizedDocument | None = None
            payload: LLMPayload
            normalizer_override = ""
            try:
                payload, normalized, normalizer_override = build_llm_payload_for_space(
                    space, version, stored_path,
                    file_name=file_name, file_type=file_type,
                )
            except Exception as exc:  # noqa: BLE001
                normalize_error = str(exc)
                payload = LLMPayload(text="", source="error", warnings=[normalize_error])
            norm_end = datetime.utcnow()
            if normalize_error:
                norm_status = "error"
            elif normalized is None:
                norm_status = "skipped"
            else:
                norm_status = "ok"
            recorder.record(
                TraceSpanType.NORMALIZE,
                status=norm_status,
                input_summary={
                    "file_type": file_type.value,
                    "needs_normalizer": normalized is not None or bool(normalize_error),
                    "override": normalizer_override,
                    "schema_space_id": space.id,
                },
                output_summary={
                    "payload_source": payload.source,
                    "text_chars": len(payload.text),
                    "image_count": len(payload.images),
                    "normalizer": normalized.normalizer if normalized else "",
                    "block_count": len(normalized.blocks) if normalized else 0,
                    "table_count": len(normalized.tables) if normalized else 0,
                    "warnings": payload.warnings,
                },
                duration_ms=int((norm_end - norm_start).total_seconds() * 1000),
                started_at=norm_start,
                ended_at=norm_end,
                error=normalize_error,
            )

            # ----- context assembly ----- #
            ctx_start = datetime.utcnow()
            body = payload.text
            max_chars = int(effective.processing_policy.get("max_chars", 20000) or 20000)
            truncate_marker = str(effective.processing_policy.get("truncate_marker", "[truncated]"))
            truncated = len(body) > max_chars
            if truncated:
                body = body[:max_chars] + f"\n\n{truncate_marker}"
            contract = schema_contract(schema_info)
            if payload.images and not body:
                document_section = f"## Document\n[{len(payload.images)} image(s) attached — file_type={file_type.value}]\n"
            else:
                document_section = f"## Document ({file_type.value})\n{body}\n"
            prompt = (
                f"{effective.system_prompt}\n\n"
                f"## Output Contract\n{contract}\n\n"
                f"## Extraction Instruction\n{effective.extraction_instruction}\n\n"
                f"## User Context\n{document_context or '(none)'}\n\n"
                f"{document_section}"
            )
            ctx_end = datetime.utcnow()
            recorder.record(
                TraceSpanType.CONTEXT_ASSEMBLY,
                status="ok",
                input_summary={
                    "contract_chars": len(contract),
                    "context_chars": len(document_context),
                    "payload_source": payload.source,
                    "has_images": bool(payload.images),
                    "max_chars": max_chars,
                    "processing_policy_source": effective.processing_policy_source,
                    "system_prompt_source": effective.system_prompt_source,
                    "extraction_instruction_source": effective.extraction_instruction_source,
                },
                output_summary={"prompt_chars": len(prompt), "truncated": truncated},
                duration_ms=int((ctx_end - ctx_start).total_seconds() * 1000),
                started_at=ctx_start,
                ended_at=ctx_end,
            )

            # ----- model call ----- #
            model_start = datetime.utcnow()
            provider, provider_name, model_name = resolve_model_provider(space, version)
            invocation_result = await provider.generate_json(prompt, model_name)
            model_end = datetime.utcnow()
            recorder.record(
                TraceSpanType.MODEL_CALL,
                status="error" if invocation_result.error else "ok",
                input_summary={
                    "provider": provider_name,
                    "model": model_name,
                    "prompt_chars": len(prompt),
                    "provider_source": effective.model_provider_source,
                    "model_source": effective.model_name_source,
                },
                output_summary={
                    "raw_chars": len(invocation_result.raw_response or ""),
                    "parsed_ok": invocation_result.parsed_json is not None,
                    "duration_ms": invocation_result.duration_ms,
                },
                duration_ms=invocation_result.duration_ms,
                started_at=model_start,
                ended_at=model_end,
                error=invocation_result.error,
            )

            # ----- validate ----- #
            val_start = datetime.utcnow()
            parsed = invocation_result.parsed_json
            issues = validate_output(schema_info, parsed) if parsed is not None else [
                {"code": "model_no_output", "path": "$", "message": "Model returned no parseable JSON"}
            ]
            val_end = datetime.utcnow()
            recorder.record(
                TraceSpanType.VALIDATE,
                status="ok" if not issues else "fail",
                input_summary={"has_output": parsed is not None},
                output_summary={"issue_count": len(issues), "issues": issues[:10]},
                duration_ms=int((val_end - val_start).total_seconds() * 1000),
                started_at=val_start,
                ended_at=val_end,
            )

            # ----- final status ----- #
            if invocation_result.error:
                final_status = InvocationStatus.FAILED
                error_code = "model_error"
                error_message = invocation_result.error
            elif issues:
                final_status = InvocationStatus.NEEDS_REVIEW
                error_code = "validation_failed"
                error_message = f"{len(issues)} validation issue(s)"
            else:
                final_status = InvocationStatus.COMPLETED
                error_code = ""
                error_message = ""

            ended_at_str = utc_now()
            total_ms = int((time.perf_counter() - started_perf) * 1000)

            inv_record = InvocationRecord(
                id=invocation_id,
                schema_space_id=version.schema_space_id,
                version_id=version.id,
                source=source.value,
                status=final_status.value,
                file_name=file_name,
                mime_type=file.content_type or "",
                file_type=file_type.value,
                size_bytes=len(content),
                sha256=sha,
                document_context=document_context,
                model_provider=provider_name,
                model_name=model_name,
                final_output=encode_json(parsed) if parsed is not None else "{}",
                validation_issues=encode_json(issues),
                error_code=error_code,
                error_message=error_message,
                parent_invocation_id=parent_invocation_id,
                duration_ms=total_ms,
                started_at=started_at_str,
                ended_at=ended_at_str,
            )
            self.invocation_repo.add(session, inv_record)
            session.flush()

            trace_record = TraceRecord(
                id=new_id(),
                invocation_id=invocation_id,
                schema_space_id=version.schema_space_id,
                version_id=version.id,
                model_provider=provider_name,
                model_name=model_name,
                spans=encode_json([_span_to_dict(s) for s in recorder.spans]),
                created_at=utc_now(),
            )
            self.trace_repo.add(session, trace_record)

            return invocation_from_record(inv_record)

    def _assert_file_type_allowed(self, space, file_name: str) -> FileType:
        detected = FileType.from_filename(file_name)
        if detected is None:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file extension for '{file_name}'.",
            )
        if detected not in space.input_file_types:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"This SchemaSpace accepts: "
                    f"{sorted(ft.value for ft in space.input_file_types)}. "
                    f"Got: {detected.value}"
                ),
            )
        return detected


def _span_to_dict(span: TraceSpan) -> dict[str, Any]:
    return {
        "type": span.type,
        "started_at": span.started_at.isoformat(timespec="milliseconds"),
        "ended_at": span.ended_at.isoformat(timespec="milliseconds"),
        "duration_ms": span.duration_ms,
        "status": span.status,
        "input_summary": span.input_summary,
        "output_summary": span.output_summary,
        "error": span.error,
    }
