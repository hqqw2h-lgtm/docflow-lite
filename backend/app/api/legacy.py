"""Legacy Workspace-era endpoints.

These endpoints predate the SchemaSpace rewrite but the existing frontend
still depends on them. They are grouped into a single APIRouter so that
``main.py`` stays minimal while behaviour is preserved verbatim.

Do not add new functionality here - extend the SchemaSpace API surface
instead. This module is intentionally treated as a frozen compatibility
layer that will be removed once the frontend migrates.
"""
from __future__ import annotations

from time import perf_counter
from datetime import datetime
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..business_context import MAX_BACKGROUND_CHARS, summarize_background
from ..database import (
    CorrectionSessionRecord,
    ExtractionResultRecord,
    IntegrationRecord,
    NormalizedDocumentRecord,
    PromptProfileRecord,
    SchemaDefinitionRecord,
    SettingsRecord,
    TenantRecord,
    TrainingExampleSetItemRecord,
    TrainingExampleSetRecord,
    TrainingExampleRecord,
    WorkspaceBackgroundFileRecord,
    WorkspaceRecord,
    decode_json,
    encode_json,
    get_session,
    new_id,
    utc_now,
)
from ..document_processing import (
    ContextBudgetExceeded,
    DocumentProcessingService,
    WorkspaceProcessingContext,
    normalized_blocks_to_payload,
)
from ..extraction import save_upload
from ..learning import PromptProfileService, TrainingExampleService, training_example_from_record
from ..models import (
    ContextPackageTrace,
    ExtractionResult,
    ExtractionUpdate,
    ExtractionTrace,
    FieldRuleSuggestion,
    FieldRuleSuggestionRequest,
    IntegrationCreate,
    IntegrationConfig,
    IntegrationUpdate,
    IntegrationWorkflow,
    ModelInvocationTrace,
    ModelSettings,
    ProcessingPolicy,
    PromptProfile,
    SchemaDefinition,
    SchemaTypeInfo,
    Tenant,
    TenantCreate,
    TrainingExample,
    TrainingExampleSet,
    TrainingExampleSetStatus,
    Workspace,
    WorkspaceAnalysis,
    WorkspaceBackgroundFile,
    WorkspaceBackgroundSummary,
    WorkspaceCreate,
    WorkspaceUpdate,
)
from ..ollama_client import generate_json_with_model, list_ollama_models
from ..schema_utils import SchemaInfo, normalize_schema_info, validate_output
from ..validation import ActivationContext, IntegrationActivationValidator

router = APIRouter()

SCHEMA_TYPES = [
    SchemaTypeInfo(
        id="purchase-order",
        name="PURCHASE_ORDER",
        title="Purchase Order",
        description="Manage order details, quantities, and delivery terms.",
    ),
    SchemaTypeInfo(
        id="delivery-note",
        name="DELIVERY_NOTE",
        title="Delivery Note",
        description="Track shipments and fulfillment confirmations.",
    ),
    SchemaTypeInfo(
        id="invoice",
        name="INVOICE",
        title="Invoice",
        description="Extract vendor, payment, and line-item information.",
    ),
    SchemaTypeInfo(
        id="custom",
        name="CUSTOM",
        title="Custom",
        description="Define your own document schema.",
    ),
]

DEFAULT_SCHEMA: dict[str, Any] = {
    "outputType": "json",
    "children": [],
}




@router.get("/api/schema-types", response_model=list[SchemaTypeInfo])
def schema_types() -> list[SchemaTypeInfo]:
    return SCHEMA_TYPES


@router.post("/api/field-rule-suggestions", response_model=FieldRuleSuggestion)
async def suggest_field_rule(payload: FieldRuleSuggestionRequest) -> FieldRuleSuggestion:
    description = payload.description.strip()
    if not description:
        raise HTTPException(status_code=400, detail="Rule description is required.")
    settings = get_model_settings()
    if settings.provider == "mock":
        raise HTTPException(status_code=400, detail="Field rule suggestions require a real model provider such as Ollama.")
    suggestion_schema: dict[str, Any] = {
        "outputType": "json",
        "children": [
            {"fieldName": "regexPattern", "type": "string", "isRequired": False},
            {
                "fieldName": "constraints",
                "type": "json",
                "isRequired": False,
                "children": [
                    {"fieldName": "min", "type": "number", "isRequired": False},
                    {"fieldName": "max", "type": "number", "isRequired": False},
                    {"fieldName": "minLength", "type": "number", "isRequired": False},
                    {"fieldName": "maxLength", "type": "number", "isRequired": False},
                    {"fieldName": "exactLength", "type": "number", "isRequired": False},
                    {"fieldName": "pattern", "type": "string", "isRequired": False},
                ],
            },
            {"fieldName": "explanation", "type": "string", "isRequired": False},
        ],
    }
    prompt = (
        "You convert a business user's natural-language field validation rule into a JSON rule suggestion.\n"
        "Return JSON only. Do not include markdown or comments.\n\n"
        "Supported output shape:\n"
        '{ "regexPattern": string, "constraints": object, "explanation": string }\n\n'
        "Supported constraints object keys:\n"
        "- min: number; for numeric lower bound.\n"
        "- max: number; for numeric upper bound.\n"
        "- minLength: number; for minimum string/date length. Only use for string/date fields.\n"
        "- maxLength: number; for maximum string/date length. Only use for string/date fields.\n"
        "- exactLength: number; for exact string/date length. Only use for string/date fields.\n"
        "- pattern: string; hard validation regex that must fully match the final value.\n"
        "Rules:\n"
        "- Use regexPattern when it helps the UI show the user a regex suggestion.\n"
        "- Use constraints only for hard validation requirements that must be checked after model output.\n"
        "- Omit keys you cannot infer from the user description; do not invent defaults.\n"
        "- Keep explanation short and business-readable.\n\n"
        f"Field type: {payload.field_type}\n"
        f"User rule description: {description}"
    )
    try:
        generated = await generate_json_with_model(prompt, suggestion_schema, settings)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=f"Model rule suggestion failed: {exc}") from exc
    if not isinstance(generated, dict):
        raise HTTPException(status_code=502, detail="Model rule suggestion did not return a JSON object.")
    return _clean_field_rule_suggestion(generated)


@router.get("/api/tenants", response_model=list[Tenant])
def list_tenants() -> list[Tenant]:
    with get_session() as session:
        records = session.scalars(select(TenantRecord).order_by(TenantRecord.updated_at.desc())).all()
        return [tenant_from_record(record) for record in records]


@router.post("/api/tenants", response_model=Tenant)
def create_tenant(payload: TenantCreate) -> Tenant:
    now = utc_now()
    with get_session() as session:
        record = TenantRecord(
            id=new_id(),
            name=payload.name,
            description=payload.description,
            status="active",
            created_at=now,
            updated_at=now,
        )
        session.add(record)
        return tenant_from_record(record)


@router.get("/api/workspaces", response_model=list[Workspace])
def list_workspaces(
    tenant_id: str = "",
    query: str = "",
    schema_type: str = "",
    active: bool | None = None,
) -> list[Workspace]:
    statement = select(WorkspaceRecord)
    if tenant_id:
        statement = statement.where(WorkspaceRecord.tenant_id == tenant_id)
    if query:
        like_query = f"%{query.lower()}%"
        statement = statement.where(
            or_(
                func.lower(WorkspaceRecord.name).like(like_query),
                func.lower(WorkspaceRecord.description).like(like_query),
            )
        )
    if schema_type:
        statement = statement.where(WorkspaceRecord.schema_type == schema_type)
    if active is not None:
        statement = statement.where(WorkspaceRecord.active_status == (1 if active else 0))
    statement = statement.order_by(WorkspaceRecord.updated_at.desc())
    with get_session() as session:
        records = session.scalars(statement).all()
        return [workspace_from_record(record) for record in records]


@router.post("/api/workspaces", response_model=Workspace)
def create_workspace(payload: WorkspaceCreate) -> Workspace:
    load_tenant(payload.tenant_id)
    now = utc_now()
    with get_session() as session:
        record = WorkspaceRecord(
            id=new_id(),
            tenant_id=payload.tenant_id,
            name=payload.name,
            description=payload.description,
            schema_type=payload.schema_type,
            active_status=0,
            initialization_status="inactive",
            active_schema_version_id="",
            active_prompt_profile_id="",
            prompt_template="",
            extracted=0,
            schema_info=encode_json(DEFAULT_SCHEMA),
            created_at=now,
            updated_at=now,
        )
        session.add(record)
        session.flush()
        create_schema_version(session, record, DEFAULT_SCHEMA, now)
        create_example_set(session, workspace_id=record.id, source_set=None, now=now)
        return workspace_from_record(record)


@router.get("/api/workspaces/{workspace_id}", response_model=Workspace)
def get_workspace(workspace_id: str) -> Workspace:
    return load_workspace(workspace_id)


@router.patch("/api/workspaces/{workspace_id}", response_model=Workspace)
def update_workspace(workspace_id: str, payload: WorkspaceUpdate) -> Workspace:
    data = payload.model_dump(exclude_unset=True)
    with get_session() as session:
        record = session.get(WorkspaceRecord, workspace_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Workspace not found")
        if "name" in data:
            record.name = data["name"]
        if "description" in data:
            record.description = data["description"]
        if "active_status" in data:
            record.active_status = 1 if data["active_status"] else 0
        if "initialization_status" in data:
            record.initialization_status = data["initialization_status"]
        if "prompt_template" in data:
            record.prompt_template = data["prompt_template"]
        if "schema_info" in data:
            schema_info = normalize_schema_info(data["schema_info"])
            record.schema_info = encode_json(schema_info)
            create_schema_version(session, record, schema_info, utc_now())
        record.updated_at = utc_now()
        return workspace_from_record(record)


@router.get("/api/workspaces/{workspace_id}/schema-versions", response_model=list[SchemaDefinition])
def list_schema_versions(workspace_id: str) -> list[SchemaDefinition]:
    load_workspace(workspace_id)
    with get_session() as session:
        records = session.scalars(
            select(SchemaDefinitionRecord)
            .where(SchemaDefinitionRecord.workspace_id == workspace_id)
            .order_by(SchemaDefinitionRecord.version.desc())
        ).all()
        return [schema_definition_from_record(record) for record in records]


@router.post("/api/workspaces/{workspace_id}/extract", response_model=ExtractionResult)
async def extract_document(
    workspace_id: str,
    file: UploadFile = File(...),
    document_context: str = Form(default=""),
) -> ExtractionResult:
    workspace = load_workspace(workspace_id)
    require_workspace_description(workspace)
    draft_set_id = writable_example_set_id(workspace_id)
    settings = get_model_settings()
    policy = get_processing_policy()
    path = await save_upload(file)
    trace: ExtractionTrace | None = None
    raw_text = ""
    preparation = None
    status = "to_review"
    try:
        preparation = DocumentProcessingService(policy).prepare(
            path=path,
            file_name=file.filename or path.name,
            content_type=file.content_type,
            schema_info=workspace.schema_info,
            workspace_description=_merge_document_context(workspace.description, document_context),
            workspace_context=workspace_processing_context(workspace, "extraction"),
        )
        raw_text = preparation.normalized.markdown[: policy.raw_text_preview_chars]
        trace = preparation.to_trace()
        started_at = perf_counter()
        extracted = await generate_json_with_model(
            preparation.prompt,
            workspace.schema_info,
            settings,
        )
        validation_issues = validate_output(workspace.schema_info, extracted)
        if validation_issues:
            repair_prompt = _build_repair_prompt(
                original_prompt=preparation.prompt,
                extracted=extracted,
                validation_issues=validation_issues,
            )
            extracted = await generate_json_with_model(repair_prompt, workspace.schema_info, settings)
            repaired_issues = validate_output(workspace.schema_info, extracted)
            if repaired_issues:
                status = "correction_required"
                trace.merge_issues.extend(repaired_issues)
        duration_ms = int((perf_counter() - started_at) * 1000)
        trace.invocations.append(
            ModelInvocationTrace(
                id=new_id(),
                context_package_id=preparation.context_package.id,
                provider=settings.provider,
                model_name=settings.model,
                estimated_input_tokens=preparation.context_package.estimated_input_tokens,
                estimated_output_tokens=0,
                duration_ms=duration_ms,
                status="completed",
            )
        )
    except ContextBudgetExceeded as exc:
        extracted = {"error": exc.issue["code"], "message": exc.issue["message"]}
        status = "processing_error"
        trace = _error_trace(
            path=path,
            file_name=file.filename or path.name,
            content_type=file.content_type,
            policy=policy,
            issue=exc.issue,
        )
    except RuntimeError as exc:
        extracted = {"error": "model_extraction_failed", "message": str(exc)}
        status = "processing_error"
        trace = _error_trace(
            path=path,
            file_name=file.filename or path.name,
            content_type=file.content_type,
            policy=policy,
            issue={
                "code": "model_extraction_failed",
                "path": "model.invocation",
                "message": str(exc),
            },
        )
    result_id = new_id()
    now = utc_now()
    with get_session() as session:
        result_record = ExtractionResultRecord(
            id=result_id,
            workspace_id=workspace_id,
            file_name=file.filename or path.name,
            model=settings.model,
            raw_text=raw_text,
            extracted_data=encode_json(extracted),
            corrected_data="{}",
            status=status,
            trace=encode_json(trace.model_dump() if trace else {}),
            created_at=now,
        )
        session.add(result_record)
        if preparation is not None:
            normalized_record = NormalizedDocumentRecord(
                id=preparation.normalized.id,
                workspace_id=workspace_id,
                extraction_result_id=result_id,
                file_name=file.filename or path.name,
                mime_type=preparation.asset.mime_type,
                source_sha256=preparation.asset.sha256,
                normalizer=preparation.normalized.normalizer,
                normalizer_version=preparation.normalized.normalizer_version,
                markdown=preparation.normalized.markdown,
                text_content=preparation.normalized.text,
                blocks=encode_json(normalized_blocks_to_payload(preparation.normalized.blocks)),
                tables=encode_json(preparation.normalized.tables),
                assets=encode_json(preparation.normalized.assets),
                trace=encode_json(preparation.normalized.to_trace().model_dump()),
                created_at=now,
            )
            result_record.normalized_document = normalized_record
            session.add(normalized_record)
        workspace_record = session.get(WorkspaceRecord, workspace_id)
        if workspace_record is not None:
            workspace_record.extracted = 1
            workspace_record.updated_at = now
        TrainingExampleService().create_from_extraction(
            session=session,
            workspace_id=workspace_id,
            extraction_result_id=result_id,
            model_output=extracted,
            extraction_status=status,
            now=now,
            example_set_id=draft_set_id,
        )
        return extraction_from_record(result_record)


@router.get("/api/workspaces/{workspace_id}/results", response_model=list[ExtractionResult])
def list_results(workspace_id: str) -> list[ExtractionResult]:
    with get_session() as session:
        records = session.scalars(
            select(ExtractionResultRecord)
            .where(ExtractionResultRecord.workspace_id == workspace_id)
            .order_by(ExtractionResultRecord.created_at.desc())
        ).all()
        return [extraction_from_record(record) for record in records]


@router.get("/api/workspaces/{workspace_id}/training-examples", response_model=list[TrainingExample])
def list_training_examples(workspace_id: str) -> list[TrainingExample]:
    load_workspace(workspace_id)
    with get_session() as session:
        return TrainingExampleService().list_by_workspace(session, workspace_id)


@router.get("/api/workspaces/{workspace_id}/example-sets", response_model=list[TrainingExampleSet])
def list_training_example_sets(workspace_id: str) -> list[TrainingExampleSet]:
    load_workspace(workspace_id)
    with get_session() as session:
        ensure_initial_example_set(session, workspace_id)
        records = session.scalars(
            select(TrainingExampleSetRecord)
            .where(TrainingExampleSetRecord.workspace_id == workspace_id)
            .order_by(TrainingExampleSetRecord.version.desc())
        ).all()
        return [training_example_set_from_record(record) for record in records]


@router.post("/api/workspaces/{workspace_id}/example-sets/{example_set_id}/freeze", response_model=WorkspaceAnalysis)
def freeze_training_example_set(workspace_id: str, example_set_id: str) -> WorkspaceAnalysis:
    workspace = load_workspace(workspace_id)
    require_workspace_description(workspace)
    settings = get_model_settings()
    with get_session() as session:
        record = load_example_set_record(session, workspace_id, example_set_id)
        if record.status != TrainingExampleSetStatus.DRAFT.value:
            raise HTTPException(status_code=400, detail="Only draft example versions can be frozen.")
        try:
            result = PromptProfileService().generate_from_example_set(session, workspace, settings, record)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        record.status = TrainingExampleSetStatus.FROZEN.value
        record.prompt_profile_id = result.prompt_profile_id
        record.updated_at = utc_now()
        return result


@router.post("/api/workspaces/{workspace_id}/example-sets/{example_set_id}/clone", response_model=TrainingExampleSet)
def clone_training_example_set(workspace_id: str, example_set_id: str) -> TrainingExampleSet:
    load_workspace(workspace_id)
    now = utc_now()
    with get_session() as session:
        source = load_example_set_record(session, workspace_id, example_set_id)
        cloned = create_example_set(session, workspace_id=workspace_id, source_set=source, now=now)
        return training_example_set_from_record(cloned)


@router.delete("/api/workspaces/{workspace_id}/example-sets/{example_set_id}/examples/{example_id}", response_model=TrainingExampleSet)
def remove_training_example_from_set(workspace_id: str, example_set_id: str, example_id: str) -> TrainingExampleSet:
    load_workspace(workspace_id)
    with get_session() as session:
        record = load_example_set_record(session, workspace_id, example_set_id)
        if record.status != TrainingExampleSetStatus.DRAFT.value:
            raise HTTPException(status_code=400, detail="Frozen example versions cannot be changed. Clone it first.")
        item = session.scalar(
            select(TrainingExampleSetItemRecord).where(
                TrainingExampleSetItemRecord.example_set_id == example_set_id,
                TrainingExampleSetItemRecord.training_example_id == example_id,
            )
        )
        if item is None:
            raise HTTPException(status_code=404, detail="Training example is not in this version")
        session.delete(item)
        record.updated_at = utc_now()
        session.flush()
        return training_example_set_from_record(record)


@router.get("/api/workspaces/{workspace_id}/prompt-profiles", response_model=list[PromptProfile])
def list_prompt_profiles(workspace_id: str) -> list[PromptProfile]:
    load_workspace(workspace_id)
    with get_session() as session:
        records = session.scalars(
            select(PromptProfileRecord)
            .where(PromptProfileRecord.workspace_id == workspace_id)
            .order_by(PromptProfileRecord.version.desc())
        ).all()
        return [prompt_profile_from_record(record) for record in records]


@router.post("/api/workspaces/{workspace_id}/prompt-profiles/{profile_id}/activate", response_model=Workspace)
def activate_prompt_profile(workspace_id: str, profile_id: str) -> Workspace:
    with get_session() as session:
        workspace_record = session.get(WorkspaceRecord, workspace_id)
        if workspace_record is None:
            raise HTTPException(status_code=404, detail="Workspace not found")
        profile_record = session.get(PromptProfileRecord, profile_id)
        if profile_record is None or profile_record.workspace_id != workspace_id:
            raise HTTPException(status_code=404, detail="Prompt profile not found")
        for record in workspace_record.prompt_profiles:
            record.status = "active" if record.id == profile_id else "retired"
        workspace_record.active_prompt_profile_id = profile_id
        workspace_record.prompt_template = profile_record.extraction_instruction
        workspace_record.initialization_status = "active"
        workspace_record.active_status = 1
        workspace_record.updated_at = utc_now()
        return workspace_from_record(workspace_record)


@router.get("/api/workspaces/{workspace_id}/background-files", response_model=list[WorkspaceBackgroundFile])
def list_workspace_background_files(workspace_id: str) -> list[WorkspaceBackgroundFile]:
    load_workspace(workspace_id)
    with get_session() as session:
        records = (
            session.query(WorkspaceBackgroundFileRecord)
            .filter(WorkspaceBackgroundFileRecord.workspace_id == workspace_id)
            .order_by(WorkspaceBackgroundFileRecord.created_at.desc())
            .all()
        )
        return [background_file_from_record(record) for record in records]


@router.post("/api/workspaces/{workspace_id}/background-files", response_model=WorkspaceBackgroundSummary)
async def upload_workspace_background_file(workspace_id: str, file: UploadFile = File(...)) -> WorkspaceBackgroundSummary:
    workspace = load_workspace(workspace_id)
    settings = get_model_settings()
    policy = get_processing_policy()
    path = await save_upload(file)
    service = DocumentProcessingService(policy)
    asset, normalized = service.normalize_asset(
        path=path,
        file_name=file.filename or path.name,
        content_type=file.content_type,
        workspace_context=workspace_processing_context(workspace, "background"),
    )
    normalized_markdown = normalized.markdown[:MAX_BACKGROUND_CHARS]
    summary = await summarize_background(
        workspace_name=workspace.name,
        current_description=workspace.description,
        file_name=file.filename or path.name,
        normalized_markdown=normalized_markdown,
        settings=settings,
    )
    now = utc_now()
    with get_session() as session:
        record = WorkspaceBackgroundFileRecord(
            id=new_id(),
            workspace_id=workspace_id,
            file_name=file.filename or path.name,
            mime_type=asset.mime_type,
            size_bytes=path.stat().st_size,
            extracted_text=normalized_markdown,
            ai_summary=summary,
            created_at=now,
        )
        workspace_record = session.get(WorkspaceRecord, workspace_id)
        if workspace_record is None:
            raise HTTPException(status_code=404, detail="Workspace not found")
        workspace_record.description = summary
        workspace_record.updated_at = now
        session.add(record)
        return WorkspaceBackgroundSummary(
            file=background_file_from_record(record),
            workspace=workspace_from_record(workspace_record),
            suggested_description=summary,
        )


@router.patch("/api/results/{result_id}", response_model=ExtractionResult)
def update_result(result_id: str, payload: ExtractionUpdate) -> ExtractionResult:
    with get_session() as session:
        record = session.get(ExtractionResultRecord, result_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Extraction result not found")
        current = extraction_from_record(record)
        updated = current.model_copy(update=payload.model_dump(exclude_unset=True))
        record.corrected_data = encode_json(updated.corrected_data)
        record.status = updated.status
        if updated.corrected_data is not None and updated.status is not None:
            TrainingExampleService().mark_from_correction(
                session=session,
                extraction_result_id=result_id,
                corrected_output=updated.corrected_data,
                status=updated.status,
            )
        return extraction_from_record(record)


@router.post("/api/workspaces/{workspace_id}/analyze", response_model=WorkspaceAnalysis)
def analyze_workspace(workspace_id: str) -> WorkspaceAnalysis:
    workspace = load_workspace(workspace_id)
    require_workspace_description(workspace)
    settings = get_model_settings()
    with get_session() as session:
        ensure_initial_example_set(session, workspace_id)
        draft_set = session.scalar(
            select(TrainingExampleSetRecord)
            .where(
                TrainingExampleSetRecord.workspace_id == workspace_id,
                TrainingExampleSetRecord.status == TrainingExampleSetStatus.DRAFT.value,
            )
            .order_by(TrainingExampleSetRecord.version.desc())
        )
        if draft_set is None:
            raise HTTPException(status_code=400, detail="Clone a frozen example version before generating a new prompt.")
        try:
            result = PromptProfileService().generate_from_example_set(session, workspace, settings, draft_set)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        draft_set.status = TrainingExampleSetStatus.FROZEN.value
        draft_set.prompt_profile_id = result.prompt_profile_id
        draft_set.updated_at = utc_now()
        for record in session.scalars(
            select(ExtractionResultRecord).where(
                ExtractionResultRecord.workspace_id == workspace_id,
                ExtractionResultRecord.status == "completed",
            )
        ):
            record.status = "analyzed"
        return result


@router.get("/api/settings/model", response_model=ModelSettings)
def get_model_settings() -> ModelSettings:
    with get_session() as session:
        record = session.get(SettingsRecord, "model")
        if record is None:
            return ModelSettings()
        return ModelSettings.model_validate(decode_json(record.value, {}))


@router.put("/api/settings/model", response_model=ModelSettings)
def save_model_settings(settings: ModelSettings) -> ModelSettings:
    with get_session() as session:
        record = session.get(SettingsRecord, "model")
        if record is None:
            session.add(SettingsRecord(key="model", value=encode_json(settings.model_dump())))
        else:
            record.value = encode_json(settings.model_dump())
    return settings


@router.get("/api/settings/processing", response_model=ProcessingPolicy)
def get_processing_policy() -> ProcessingPolicy:
    with get_session() as session:
        record = session.get(SettingsRecord, "processing")
        if record is None:
            return ProcessingPolicy()
        return ProcessingPolicy.model_validate(decode_json(record.value, {}))


@router.put("/api/settings/processing", response_model=ProcessingPolicy)
def save_processing_policy(policy: ProcessingPolicy) -> ProcessingPolicy:
    if policy.sync_max_bytes > policy.async_max_bytes:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Processing policy is invalid",
                "issues": [
                    {
                        "code": "sync_threshold_exceeds_async_threshold",
                        "path": "sync_max_bytes",
                        "message": "Sync max bytes cannot be greater than async max bytes.",
                    }
                ],
            },
        )
    with get_session() as session:
        record = session.get(SettingsRecord, "processing")
        if record is None:
            session.add(SettingsRecord(key="processing", value=encode_json(policy.model_dump())))
        else:
            record.value = encode_json(policy.model_dump())
    return policy


@router.get("/api/models", response_model=list[str])
async def models() -> list[str]:
    settings = get_model_settings()
    return await list_ollama_models(settings)


@router.get("/api/integrations", response_model=list[IntegrationWorkflow])
def list_integrations(workspace_id: str = "") -> list[IntegrationWorkflow]:
    statement = select(IntegrationRecord)
    if workspace_id:
        statement = statement.where(IntegrationRecord.workspace_id == workspace_id)
    statement = statement.order_by(IntegrationRecord.updated_at.desc())
    with get_session() as session:
        records = session.scalars(statement).all()
        return [integration_from_record(record) for record in records]


@router.post("/api/integrations", response_model=IntegrationWorkflow)
def create_integration(payload: IntegrationCreate) -> IntegrationWorkflow:
    load_workspace(payload.workspace_id)
    now = utc_now()
    with get_session() as session:
        record = IntegrationRecord(
            id=new_id(),
            workspace_id=payload.workspace_id,
            name=payload.name,
            status="draft",
            config=encode_json(payload.config.model_dump()),
            created_at=now,
            updated_at=now,
        )
        session.add(record)
        return integration_from_record(record)


@router.patch("/api/integrations/{integration_id}", response_model=IntegrationWorkflow)
def update_integration(integration_id: str, payload: IntegrationUpdate) -> IntegrationWorkflow:
    data = payload.model_dump(exclude_unset=True)
    with get_session() as session:
        record = session.get(IntegrationRecord, integration_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Integration not found")
        if "name" in data:
            record.name = data["name"]
        if "status" in data:
            record.status = data["status"]
        if "config" in data:
            record.config = encode_json(IntegrationConfig.model_validate(data["config"]).model_dump())
        record.updated_at = utc_now()
        return integration_from_record(record)


@router.post("/api/integrations/{integration_id}/activate", response_model=IntegrationWorkflow)
def activate_integration(integration_id: str) -> IntegrationWorkflow:
    integration = load_integration(integration_id)
    workspace = load_workspace(integration.workspace_id)
    validator = IntegrationActivationValidator()
    result = validator.validate(
        ActivationContext(workspace=workspace, config=integration.config)
    )
    if not result.valid:
        raise HTTPException(
            status_code=400,
            detail=result.to_error_detail(),
        )
    return update_integration(integration_id, IntegrationUpdate(status="active"))


def create_schema_version(
    session: Session,
    workspace_record: WorkspaceRecord,
    schema_info: SchemaInfo,
    now: str,
) -> SchemaDefinitionRecord:
    max_version = session.scalar(
        select(func.coalesce(func.max(SchemaDefinitionRecord.version), 0)).where(
            SchemaDefinitionRecord.workspace_id == workspace_record.id
        )
    )
    for record in session.scalars(
        select(SchemaDefinitionRecord).where(
            SchemaDefinitionRecord.workspace_id == workspace_record.id,
            SchemaDefinitionRecord.status == "active",
        )
    ):
        record.status = "retired"
    schema_record = SchemaDefinitionRecord(
        id=new_id(),
        workspace_id=workspace_record.id,
        version=int(max_version or 0) + 1,
        status="active",
        schema_info=encode_json(schema_info),
        created_at=now,
    )
    session.add(schema_record)
    session.flush()
    workspace_record.active_schema_version_id = schema_record.id
    workspace_record.updated_at = now
    return schema_record


def writable_example_set_id(workspace_id: str) -> str:
    with get_session() as session:
        ensure_initial_example_set(session, workspace_id)
        draft = session.scalar(
            select(TrainingExampleSetRecord)
            .where(
                TrainingExampleSetRecord.workspace_id == workspace_id,
                TrainingExampleSetRecord.status == TrainingExampleSetStatus.DRAFT.value,
            )
            .order_by(TrainingExampleSetRecord.version.desc())
        )
        if draft is None:
            raise HTTPException(
                status_code=400,
                detail="The current training example version is frozen. Clone a frozen version before uploading or changing samples.",
            )
        return draft.id


def ensure_initial_example_set(session: Session, workspace_id: str) -> TrainingExampleSetRecord:
    existing = session.scalar(
        select(TrainingExampleSetRecord)
        .where(TrainingExampleSetRecord.workspace_id == workspace_id)
        .order_by(TrainingExampleSetRecord.version.desc())
    )
    if existing is not None:
        return existing
    now = utc_now()
    created = create_example_set(session, workspace_id=workspace_id, source_set=None, now=now)
    for example in session.scalars(
        select(TrainingExampleRecord)
        .where(TrainingExampleRecord.workspace_id == workspace_id)
        .order_by(TrainingExampleRecord.created_at.asc())
    ):
        session.add(
            TrainingExampleSetItemRecord(
                id=new_id(),
                example_set_id=created.id,
                training_example_id=example.id,
                created_at=now,
            )
        )
    return created


def create_example_set(
    session: Session,
    workspace_id: str,
    source_set: TrainingExampleSetRecord | None,
    now: str,
) -> TrainingExampleSetRecord:
    max_version = session.scalar(
        select(func.coalesce(func.max(TrainingExampleSetRecord.version), 0)).where(
            TrainingExampleSetRecord.workspace_id == workspace_id
        )
    )
    version = int(max_version or 0) + 1
    record = TrainingExampleSetRecord(
        id=new_id(),
        workspace_id=workspace_id,
        version=version,
        name=f"Example Set v{version}",
        status=TrainingExampleSetStatus.DRAFT.value,
        prompt_profile_id="",
        created_at=now,
        updated_at=now,
    )
    session.add(record)
    session.flush()
    if source_set is not None:
        for item in sorted(source_set.items, key=lambda entry: entry.created_at):
            session.add(
                TrainingExampleSetItemRecord(
                    id=new_id(),
                    example_set_id=record.id,
                    training_example_id=item.training_example_id,
                    created_at=now,
                )
            )
    session.flush()
    return record


def load_example_set_record(session: Session, workspace_id: str, example_set_id: str) -> TrainingExampleSetRecord:
    record = session.get(TrainingExampleSetRecord, example_set_id)
    if record is None or record.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Training example version not found")
    return record


def load_workspace(workspace_id: str) -> Workspace:
    with get_session() as session:
        record = session.get(WorkspaceRecord, workspace_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Workspace not found")
        return workspace_from_record(record)


def require_workspace_description(workspace: Workspace) -> None:
    if not workspace.description.strip():
        raise HTTPException(
            status_code=400,
            detail="Workspace business description is required before model processing.",
        )


def workspace_processing_context(workspace: Workspace, purpose: str) -> WorkspaceProcessingContext:
    return WorkspaceProcessingContext(
        workspace_id=workspace.id,
        schema_type=workspace.schema_type,
        workspace_description=workspace.description,
        purpose=purpose,
    )


def load_tenant(tenant_id: str) -> Tenant:
    with get_session() as session:
        record = session.get(TenantRecord, tenant_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Tenant not found")
        return tenant_from_record(record)


def tenant_from_record(record: TenantRecord) -> Tenant:
    return Tenant(
        id=record.id,
        name=record.name,
        description=record.description,
        status=record.status,
        created_at=datetime.fromisoformat(record.created_at),
        updated_at=datetime.fromisoformat(record.updated_at),
    )


def workspace_from_record(record: WorkspaceRecord) -> Workspace:
    return Workspace(
        id=record.id,
        tenant_id=record.tenant_id,
        name=record.name,
        description=record.description,
        schema_type=record.schema_type,
        active_status=bool(record.active_status),
        initialization_status=record.initialization_status,
        extracted=bool(record.extracted),
        active_schema_version_id=record.active_schema_version_id,
        active_prompt_profile_id=record.active_prompt_profile_id,
        schema_info=normalize_schema_info(decode_json(record.schema_info, DEFAULT_SCHEMA)),
        prompt_template=record.prompt_template,
        created_at=datetime.fromisoformat(record.created_at),
        updated_at=datetime.fromisoformat(record.updated_at),
    )


def schema_definition_from_record(record: SchemaDefinitionRecord) -> SchemaDefinition:
    return SchemaDefinition(
        id=record.id,
        workspace_id=record.workspace_id,
        version=record.version,
        status=record.status,
        schema_info=normalize_schema_info(decode_json(record.schema_info, DEFAULT_SCHEMA)),
        created_at=datetime.fromisoformat(record.created_at),
    )


def prompt_profile_from_record(record: PromptProfileRecord) -> PromptProfile:
    return PromptProfile(
        id=record.id,
        workspace_id=record.workspace_id,
        version=record.version,
        status=record.status,
        system_prompt=record.system_prompt,
        extraction_instruction=record.extraction_instruction,
        output_contract=normalize_schema_info(decode_json(record.output_contract, DEFAULT_SCHEMA)),
        few_shot_examples=decode_json(record.few_shot_examples, []),
        field_rules=decode_json(record.field_rules, []),
        validation_rules=decode_json(record.validation_rules, []),
        model_provider=record.model_provider,
        model_name=record.model_name,
        created_at=datetime.fromisoformat(record.created_at),
    )


def background_file_from_record(record: WorkspaceBackgroundFileRecord) -> WorkspaceBackgroundFile:
    return WorkspaceBackgroundFile(
        id=record.id,
        workspace_id=record.workspace_id,
        file_name=record.file_name,
        mime_type=record.mime_type,
        size_bytes=record.size_bytes,
        extracted_text=record.extracted_text,
        ai_summary=record.ai_summary,
        created_at=datetime.fromisoformat(record.created_at),
    )


def training_example_set_from_record(record: TrainingExampleSetRecord) -> TrainingExampleSet:
    examples = [
        training_example_from_record(item.training_example)
        for item in sorted(record.items, key=lambda entry: entry.created_at)
    ]
    return TrainingExampleSet(
        id=record.id,
        workspace_id=record.workspace_id,
        version=record.version,
        name=record.name,
        status=record.status,
        prompt_profile_id=record.prompt_profile_id,
        examples=examples,
        created_at=datetime.fromisoformat(record.created_at),
        updated_at=datetime.fromisoformat(record.updated_at),
    )


def load_integration(integration_id: str) -> IntegrationWorkflow:
    with get_session() as session:
        record = session.get(IntegrationRecord, integration_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Integration not found")
        return integration_from_record(record)


def extraction_from_record(record: ExtractionResultRecord) -> ExtractionResult:
    trace_payload = decode_json(record.trace, {})
    return ExtractionResult(
        id=record.id,
        workspace_id=record.workspace_id,
        normalized_document_id=record.normalized_document.id if record.normalized_document else "",
        file_name=record.file_name,
        model=record.model,
        raw_text=record.raw_text,
        extracted_data=decode_json(record.extracted_data, {}),
        corrected_data=decode_json(record.corrected_data, {}),
        status=record.status,
        created_at=datetime.fromisoformat(record.created_at),
        trace=ExtractionTrace.model_validate(trace_payload) if trace_payload else None,
    )


def integration_from_record(record: IntegrationRecord) -> IntegrationWorkflow:
    return IntegrationWorkflow(
        id=record.id,
        workspace_id=record.workspace_id,
        name=record.name,
        status=record.status,
        config=IntegrationConfig.model_validate(decode_json(record.config, {})),
        created_at=datetime.fromisoformat(record.created_at),
        updated_at=datetime.fromisoformat(record.updated_at),
    )


def _merge_document_context(workspace_description: str, document_context: str) -> str:
    context = document_context.strip()
    if not context:
        return workspace_description
    return f"{workspace_description.strip()}\n\nDocument-specific context:\n{context}"


def _build_repair_prompt(
    original_prompt: str,
    extracted: Any,
    validation_issues: list[dict[str, Any]],
) -> str:
    return (
        f"{original_prompt}\n\n"
        "The previous JSON output failed hard field validation.\n"
        "Fix the JSON only by re-reading the provided document chunks and validation errors.\n"
        "Each validation error includes path, expectedType, actualValue, rule, and repairHint when available. "
        "Use the path to update the exact invalid field, and use repairHint/rule as the hard constraint.\n"
        "Return JSON only. Do not include markdown.\n\n"
        f"Previous output:\n{encode_json(extracted)}\n\n"
        f"Validation errors:\n{encode_json(validation_issues)}\n"
    )


def _clean_field_rule_suggestion(generated: dict[str, Any]) -> FieldRuleSuggestion:
    regex_pattern = str(generated.get("regexPattern") or "").strip()
    raw_constraints = generated.get("constraints")
    constraints = _clean_constraints(raw_constraints if isinstance(raw_constraints, dict) else {})
    explanation = str(generated.get("explanation") or "Generated from the rule description.").strip()
    return FieldRuleSuggestion(regexPattern=regex_pattern, constraints=constraints, explanation=explanation)


def _clean_constraints(raw_constraints: dict[str, Any]) -> dict[str, Any]:
    constraints: dict[str, Any] = {}
    for key in ("min", "max", "minLength", "maxLength", "exactLength"):
        value = raw_constraints.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            constraints[key] = value
    for key in ("pattern",):
        value = raw_constraints.get(key)
        if isinstance(value, str) and value.strip():
            constraints[key] = value.strip()
    return constraints


def _error_trace(
    path: Any,
    file_name: str,
    content_type: str | None,
    policy: ProcessingPolicy,
    issue: dict[str, Any],
) -> ExtractionTrace:
    service = DocumentProcessingService(policy)
    asset = service.large_document_policy.preflight(path, file_name, content_type)
    if issue not in asset.preflight_issues:
        asset.preflight_issues.append(issue)
    return ExtractionTrace(
        asset=asset,
        chunks=[],
        context_package=ContextPackageTrace(
            id=new_id(),
            chunk_ids=[],
            token_budget=policy.context_token_budget,
            estimated_input_tokens=0,
            reserved_output_tokens=policy.reserved_output_tokens,
            assembly_strategy="failed_before_context",
        ),
        merge_issues=[issue],
    )


