"""Mappers between ORM records and domain models."""
from __future__ import annotations

import json
from datetime import datetime

from ..db.records import (
    InvocationRecord,
    SampleRecord,
    SchemaSpaceRecord,
    SchemaSpaceVersionRecord,
    TraceRecord,
)
from ..domain import (
    FileType,
    Invocation,
    InvocationSource,
    InvocationStatus,
    Sample,
    SampleStatus,
    SchemaSpace,
    SchemaSpaceDefaults,
    SchemaSpaceStatus,
    SchemaSpaceVersion,
    Trace,
    TraceSpan,
    VersionStatus,
)


def _parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _decode(value: str, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def schema_space_from_record(record: SchemaSpaceRecord) -> SchemaSpace:
    file_types_raw = _decode(record.input_file_types, [])
    file_types = []
    for raw in file_types_raw:
        try:
            file_types.append(FileType(raw))
        except ValueError:
            continue
    overrides_raw = _decode(getattr(record, "normalizer_overrides", "") or "", {})
    overrides = (
        {str(k): str(v) for k, v in overrides_raw.items()}
        if isinstance(overrides_raw, dict) else {}
    )
    defaults_raw = _decode(getattr(record, "defaults", "") or "", {})
    if not isinstance(defaults_raw, dict):
        defaults_raw = {}
    try:
        defaults = SchemaSpaceDefaults(**defaults_raw)
    except (TypeError, ValueError):
        defaults = SchemaSpaceDefaults()
    schema_info_raw = _decode(getattr(record, "schema_info", "") or "", {"outputType": "json", "children": []})
    return SchemaSpace(
        id=record.id,
        tenant_id=record.tenant_id,
        name=record.name,
        description=record.description,
        input_file_types=file_types,
        normalizer_overrides=overrides,
        schema_info=schema_info_raw,
        defaults=defaults,
        status=SchemaSpaceStatus(record.status),
        created_at=_parse_dt(record.created_at) or datetime.utcnow(),
        updated_at=_parse_dt(record.updated_at) or datetime.utcnow(),
    )


def version_from_record(record: SchemaSpaceVersionRecord, *, sample_count: int = 0) -> SchemaSpaceVersion:
    return SchemaSpaceVersion(
        id=record.id,
        schema_space_id=record.schema_space_id,
        version=record.version,
        name=record.name,
        status=VersionStatus(record.status),
        schema_info=_decode(record.schema_info, {"outputType": "json", "children": []}),
        processing_policy=_decode(record.processing_policy, {}),
        system_prompt=record.system_prompt,
        extraction_instruction=record.extraction_instruction,
        model_provider=record.model_provider,
        model_name=record.model_name,
        parent_version_id=record.parent_version_id,
        sample_count=sample_count,
        published_at=_parse_dt(record.published_at),
        created_at=_parse_dt(record.created_at) or datetime.utcnow(),
        updated_at=_parse_dt(record.updated_at) or datetime.utcnow(),
    )


def sample_from_record(record: SampleRecord) -> Sample:
    return Sample(
        id=record.id,
        version_id=record.version_id,
        file_name=record.file_name,
        mime_type=record.mime_type,
        file_type=FileType(record.file_type) if record.file_type else FileType.TEXT,
        size_bytes=record.size_bytes,
        sha256=record.sha256,
        document_context=record.document_context,
        status=SampleStatus(record.status),
        expected_output=_decode(record.expected_output, None),
        model_output=_decode(record.model_output, None),
        corrected_output=_decode(record.corrected_output, None),
        correction_notes=_decode(record.correction_notes, []),
        invocation_id=record.invocation_id,
        created_at=_parse_dt(record.created_at) or datetime.utcnow(),
        updated_at=_parse_dt(record.updated_at) or datetime.utcnow(),
    )


def invocation_from_record(record: InvocationRecord) -> Invocation:
    file_type = None
    if record.file_type:
        try:
            file_type = FileType(record.file_type)
        except ValueError:
            file_type = None
    return Invocation(
        id=record.id,
        schema_space_id=record.schema_space_id,
        version_id=record.version_id,
        source=InvocationSource(record.source),
        status=InvocationStatus(record.status),
        file_name=record.file_name,
        mime_type=record.mime_type,
        file_type=file_type,
        size_bytes=record.size_bytes,
        sha256=record.sha256,
        document_context=record.document_context,
        model_provider=record.model_provider,
        model_name=record.model_name,
        final_output=_decode(record.final_output, None),
        validation_issues=_decode(record.validation_issues, []),
        error_code=record.error_code,
        error_message=record.error_message,
        parent_invocation_id=record.parent_invocation_id,
        duration_ms=record.duration_ms,
        started_at=_parse_dt(record.started_at) or datetime.utcnow(),
        ended_at=_parse_dt(record.ended_at),
    )


def trace_from_record(record: TraceRecord) -> Trace:
    spans_raw = _decode(record.spans, [])
    spans: list[TraceSpan] = []
    for raw in spans_raw:
        if not isinstance(raw, dict):
            continue
        started = _parse_dt(raw.get("started_at", "")) or datetime.utcnow()
        ended = _parse_dt(raw.get("ended_at", "")) or started
        spans.append(TraceSpan(
            type=str(raw.get("type", "")),
            started_at=started,
            ended_at=ended,
            duration_ms=int(raw.get("duration_ms", 0) or 0),
            status=str(raw.get("status", "")),
            input_summary=raw.get("input_summary") or {},
            output_summary=raw.get("output_summary") or {},
            error=str(raw.get("error", "")),
        ))
    return Trace(
        id=record.id,
        invocation_id=record.invocation_id,
        spans=spans,
        model_provider=record.model_provider,
        model_name=record.model_name,
        schema_space_id=record.schema_space_id,
        version_id=record.version_id,
        created_at=_parse_dt(record.created_at) or datetime.utcnow(),
    )
