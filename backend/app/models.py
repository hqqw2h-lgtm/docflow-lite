from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


SchemaType = Literal["PURCHASE_ORDER", "DELIVERY_NOTE", "INVOICE", "CUSTOM"]
SchemaInfo = dict[str, Any] | list[dict[str, Any]]
OutputFieldType = Literal["string", "number", "boolean", "date", "json", "jsonArray"]
WorkspaceStatus = Literal["active", "inactive"]
IntegrationStatus = Literal["draft", "active"]
TrainingExampleStatus = Literal[
    "uploaded",
    "extracted",
    "correction_required",
    "accepted",
    "rejected",
    "analyzed",
    "processing_error",
]
PromptProfileStatus = Literal["draft", "active", "retired"]
CorrectionDecision = Literal["pending", "confirmed", "rejected"]
ExtractionStatus = Literal[
    "uploaded",
    "preflighted",
    "parsed",
    "chunked",
    "indexed",
    "extracting",
    "merging",
    "to_review",
    "completed",
    "analyzed",
    "correction_required",
    "processing_error",
    "failed",
]
VariableType = Literal["string", "dict"]
ProcessingMode = Literal["sync_allowed", "async_required", "rejected_by_policy"]


class TrainingExampleSetStatus(str, Enum):
    DRAFT = "draft"
    FROZEN = "frozen"


class SchemaTypeInfo(BaseModel):
    id: str
    name: SchemaType
    title: str
    description: str


class TenantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str = Field(default="", max_length=200)


class Tenant(BaseModel):
    id: str
    name: str
    description: str
    status: Literal["active", "archived"] = "active"
    created_at: datetime
    updated_at: datetime


class WorkspaceCreate(BaseModel):
    tenant_id: str = Field(default="local-tenant", min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=50)
    description: str = Field(default="", max_length=1000)
    schema_type: SchemaType = "CUSTOM"

    @field_validator("name")
    @classmethod
    def trim_required_name(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Field must not be blank")
        return trimmed

    @field_validator("description")
    @classmethod
    def trim_description(cls, value: str) -> str:
        return value.strip()


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    description: str | None = Field(default=None, min_length=1, max_length=1000)
    active_status: bool | None = None
    initialization_status: WorkspaceStatus | None = None
    prompt_template: str | None = None
    schema_info: SchemaInfo | None = None

    @field_validator("name", "description")
    @classmethod
    def trim_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Field must not be blank")
        return trimmed


class Workspace(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: str
    schema_type: SchemaType
    active_status: bool
    initialization_status: WorkspaceStatus
    extracted: bool
    active_schema_version_id: str = ""
    active_prompt_profile_id: str = ""
    created_at: datetime
    updated_at: datetime
    schema_info: SchemaInfo
    prompt_template: str


class SchemaDefinition(BaseModel):
    id: str
    workspace_id: str
    version: int
    status: Literal["active", "retired"]
    schema_info: SchemaInfo
    created_at: datetime


class ExtractionResult(BaseModel):
    id: str
    workspace_id: str
    normalized_document_id: str = ""
    file_name: str
    model: str
    raw_text: str
    extracted_data: Any
    corrected_data: Any
    status: ExtractionStatus
    created_at: datetime
    trace: "ExtractionTrace | None" = None


class ExtractionUpdate(BaseModel):
    corrected_data: Any | None = None
    status: ExtractionStatus | None = None


class WorkspaceAnalysis(BaseModel):
    prompt_template: str
    initialization_status: WorkspaceStatus
    prompt_profile_id: str = ""
    prompt_profile_version: int = 0
    sample_count: int = 0


class FieldRuleSuggestionRequest(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    field_type: OutputFieldType = "string"


class FieldRuleSuggestion(BaseModel):
    regexPattern: str = ""
    constraints: dict[str, Any] = Field(default_factory=dict)
    explanation: str = ""


class ModelSettings(BaseModel):
    provider: Literal["ollama", "mock"] = "ollama"
    base_url: str = "http://localhost:11434"
    model: str = "llama3.1"


class ProcessingPolicy(BaseModel):
    sync_max_bytes: int = Field(default=2_000_000, ge=1)
    async_max_bytes: int = Field(default=80_000_000, ge=1)
    sync_max_pages: int = Field(default=25, ge=1)
    max_pages: int = Field(default=500, ge=1)
    chunk_token_limit: int = Field(default=900, ge=100)
    chunk_overlap_tokens: int = Field(default=80, ge=0)
    max_candidate_chunks: int = Field(default=8, ge=1)
    context_token_budget: int = Field(default=6000, ge=1000)
    reserved_output_tokens: int = Field(default=1200, ge=100)
    raw_text_preview_chars: int = Field(default=12000, ge=1000)


class DocumentAssetTrace(BaseModel):
    id: str
    file_name: str
    mime_type: str
    size_bytes: int
    sha256: str
    page_count: int = 0
    sheet_count: int = 0
    processing_mode: ProcessingMode
    preflight_status: Literal["accepted", "async_required", "rejected"]
    preflight_issues: list[dict[str, str]] = Field(default_factory=list)


class DocumentChunkTrace(BaseModel):
    id: str
    chunk_index: int
    chunk_type: str
    source_range: str
    token_count: int
    preview: str


class ContextPackageTrace(BaseModel):
    id: str
    chunk_ids: list[str]
    token_budget: int
    estimated_input_tokens: int
    reserved_output_tokens: int
    assembly_strategy: str
    target_fields: list[str] = Field(default_factory=list)


class ModelInvocationTrace(BaseModel):
    id: str
    context_package_id: str
    provider: str
    model_name: str
    estimated_input_tokens: int
    estimated_output_tokens: int
    duration_ms: int
    status: Literal["completed", "failed"]
    error_message: str = ""


class NormalizedDocumentTrace(BaseModel):
    id: str
    normalizer: str
    normalizer_version: str
    markdown_preview: str
    block_count: int
    table_count: int = 0
    asset_count: int = 0
    warnings: list[dict[str, str]] = Field(default_factory=list)
    duration_ms: int


class ExtractionTrace(BaseModel):
    asset: DocumentAssetTrace
    normalized_document: NormalizedDocumentTrace | None = None
    chunks: list[DocumentChunkTrace]
    context_package: ContextPackageTrace
    invocations: list[ModelInvocationTrace] = Field(default_factory=list)
    merge_issues: list[dict[str, Any]] = Field(default_factory=list)


class TrainingExample(BaseModel):
    id: str
    workspace_id: str
    extraction_result_id: str
    expected_output: Any
    model_output: Any
    corrected_output: Any
    status: TrainingExampleStatus
    correction_notes: list[dict[str, str]] = Field(default_factory=list)
    prompt_profile_id: str = ""
    created_at: datetime
    updated_at: datetime


class TrainingExampleSet(BaseModel):
    id: str
    workspace_id: str
    version: int
    name: str
    status: TrainingExampleSetStatus
    prompt_profile_id: str = ""
    examples: list[TrainingExample] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class CorrectionSession(BaseModel):
    id: str
    training_example_id: str
    extraction_result_id: str
    corrected_output: Any
    notes: list[dict[str, str]] = Field(default_factory=list)
    decision: CorrectionDecision
    created_at: datetime


class PromptProfile(BaseModel):
    id: str
    workspace_id: str
    version: int
    status: PromptProfileStatus
    system_prompt: str
    extraction_instruction: str
    output_contract: SchemaInfo
    few_shot_examples: list[dict[str, Any]] = Field(default_factory=list)
    field_rules: list[dict[str, Any]] = Field(default_factory=list)
    validation_rules: list[dict[str, Any]] = Field(default_factory=list)
    model_provider: str
    model_name: str
    created_at: datetime


class WorkspaceBackgroundFile(BaseModel):
    id: str
    workspace_id: str
    file_name: str
    mime_type: str
    size_bytes: int
    extracted_text: str = ""
    ai_summary: str = ""
    created_at: datetime


class WorkspaceBackgroundSummary(BaseModel):
    file: WorkspaceBackgroundFile
    workspace: Workspace
    suggested_description: str


class FileEntranceConfig(BaseModel):
    source_type: Literal["manual_upload", "outlook", "api", "shared_folder"] = "manual_upload"
    account: str = ""
    folder: str = ""
    mailbox: str = ""
    subject_contains: str = ""
    sender_contains: str = ""
    attachment_formats: list[str] = Field(default_factory=lambda: ["pdf", "msg", "docx", "xlsx"])
    time_range_start: str = ""
    time_range_end: str = ""
    attachment_required: bool = True


class SchedulerConfig(BaseModel):
    mode: Literal["manual", "once", "recurring"] = "manual"
    timezone: str = "UTC"
    start_date: str = ""
    end_date: str = ""
    run_at: str = ""
    repeat_frequency: Literal["daily", "weekly", "monthly"] = "daily"
    execution_mode: Literal["specific_times", "time_window"] = "specific_times"
    specific_times: list[str] = Field(default_factory=list)
    window_start: str = ""
    window_end: str = ""
    interval_minutes: int = 60


class MappingConfig(BaseModel):
    source_schema: dict[str, Any] = Field(default_factory=dict)
    target_schema: dict[str, Any] = Field(default_factory=dict)
    field_mappings: list[dict[str, str]] = Field(default_factory=list)
    transformations: dict[str, str] = Field(default_factory=dict)
    output_preview: dict[str, Any] = Field(default_factory=dict)


class DestinationConfig(BaseModel):
    name: str = ""
    description: str = ""
    method: Literal["POST", "PUT", "PATCH"] = "POST"
    url: str = ""
    authentication: Literal["none", "basic", "bearer", "oauth2"] = "oauth2"
    headers: dict[str, str] = Field(default_factory=dict)
    connection_timeout_seconds: int = 180
    read_timeout_seconds: int = 180
    client_id: str = ""
    client_secret: str = ""
    token_service_url: str = ""


class IntegrationConfig(BaseModel):
    file_entrance: FileEntranceConfig = Field(default_factory=FileEntranceConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    mapping: MappingConfig = Field(default_factory=MappingConfig)
    destination: DestinationConfig = Field(default_factory=DestinationConfig)
    variables: list["WorkflowVariable"] = Field(default_factory=list)


class WorkflowVariable(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    type: VariableType = "string"
    value: str = ""
    entries: dict[str, str] = Field(default_factory=dict)


class IntegrationWorkflow(BaseModel):
    id: str
    workspace_id: str
    name: str
    status: IntegrationStatus
    config: IntegrationConfig
    created_at: datetime
    updated_at: datetime


class IntegrationCreate(BaseModel):
    workspace_id: str
    name: str = Field(min_length=1, max_length=80)
    config: IntegrationConfig = Field(default_factory=IntegrationConfig)


class IntegrationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    status: IntegrationStatus | None = None
    config: IntegrationConfig | None = None
