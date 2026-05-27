from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from .enums import (
    FileType,
    InvocationSource,
    InvocationStatus,
    SampleStatus,
    SchemaSpaceStatus,
    VersionStatus,
)


class SchemaSpaceDefaults(BaseModel):
    """SchemaSpace-level defaults for every pipeline component.
    A Version may override any of these; if both are empty the system
    default kicks in. Resolved via ``services.component_resolver``."""

    model_provider: str = Field(default="", max_length=80)
    model_name: str = Field(default="", max_length=120)
    system_prompt: str = Field(default="", max_length=8000)
    extraction_instruction: str = Field(default="", max_length=8000)
    processing_policy: dict[str, Any] = Field(default_factory=dict)


class SchemaSpaceCreate(BaseModel):
    tenant_id: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=1000)
    input_file_types: list[FileType] = Field(min_length=1)
    normalizer_overrides: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Per-file-type normalizer override: keys are FileType values "
            "(e.g. 'pdf'), values are registered Normalizer names "
            "(e.g. 'pdf.marker', 'pdf.pypdf'). Empty map = use defaults."
        ),
    )
    defaults: SchemaSpaceDefaults = Field(default_factory=SchemaSpaceDefaults)

    @field_validator("name")
    @classmethod
    def _trim(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("name must not be empty")
        return v


class SchemaSpaceUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    description: str | None = Field(default=None, max_length=1000)
    input_file_types: list[FileType] | None = None
    normalizer_overrides: dict[str, str] | None = None
    defaults: SchemaSpaceDefaults | None = None
    status: SchemaSpaceStatus | None = None


class SchemaSpace(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: str
    input_file_types: list[FileType]
    normalizer_overrides: dict[str, str] = Field(default_factory=dict)
    defaults: SchemaSpaceDefaults = Field(default_factory=SchemaSpaceDefaults)
    status: SchemaSpaceStatus
    created_at: datetime
    updated_at: datetime


class VersionCreate(BaseModel):
    schema_space_id: str = Field(min_length=1)
    name: str = Field(default="", max_length=80)
    schema_info: dict[str, Any] | list[dict[str, Any]] = Field(default_factory=lambda: {"outputType": "json", "children": []})
    parent_version_id: str = ""


class VersionUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    schema_info: dict[str, Any] | list[dict[str, Any]] | None = None
    processing_policy: dict[str, Any] | None = None
    system_prompt: str | None = None
    extraction_instruction: str | None = None
    model_provider: str | None = None
    model_name: str | None = None


class SchemaSpaceVersion(BaseModel):
    id: str
    schema_space_id: str
    version: int
    name: str
    status: VersionStatus
    schema_info: dict[str, Any] | list[dict[str, Any]]
    processing_policy: dict[str, Any]
    system_prompt: str
    extraction_instruction: str
    model_provider: str
    model_name: str
    parent_version_id: str
    sample_count: int = 0
    published_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SampleCreate(BaseModel):
    document_context: str = Field(default="", max_length=4000)
    expected_output: dict[str, Any] | list[dict[str, Any]] | None = None


class Sample(BaseModel):
    id: str
    version_id: str
    file_name: str
    mime_type: str
    file_type: FileType
    size_bytes: int
    sha256: str
    document_context: str
    status: SampleStatus
    expected_output: dict[str, Any] | list[dict[str, Any]] | None
    model_output: dict[str, Any] | list[dict[str, Any]] | None
    corrected_output: dict[str, Any] | list[dict[str, Any]] | None
    correction_notes: list[dict[str, Any]]
    invocation_id: str
    created_at: datetime
    updated_at: datetime


class InvokeRequest(BaseModel):
    document_context: str = Field(default="", max_length=4000)


class Invocation(BaseModel):
    id: str
    schema_space_id: str
    version_id: str
    source: InvocationSource
    status: InvocationStatus
    file_name: str
    mime_type: str
    file_type: FileType | None
    size_bytes: int
    sha256: str
    document_context: str
    model_provider: str
    model_name: str
    final_output: dict[str, Any] | list[dict[str, Any]] | None
    validation_issues: list[dict[str, Any]]
    error_code: str
    error_message: str
    parent_invocation_id: str
    duration_ms: int
    started_at: datetime
    ended_at: datetime | None


class TraceSpan(BaseModel):
    type: str
    started_at: datetime
    ended_at: datetime
    duration_ms: int
    status: str
    input_summary: dict[str, Any] = Field(default_factory=dict)
    output_summary: dict[str, Any] = Field(default_factory=dict)
    error: str = ""


class Trace(BaseModel):
    id: str
    invocation_id: str
    spans: list[TraceSpan]
    model_provider: str
    model_name: str
    schema_space_id: str
    version_id: str
    created_at: datetime
