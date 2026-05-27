from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .database import (
    CorrectionSessionRecord,
    PromptProfileRecord,
    TrainingExampleSetItemRecord,
    TrainingExampleSetRecord,
    TrainingExampleRecord,
    WorkspaceRecord,
    decode_json,
    encode_json,
    new_id,
    utc_now,
)
from .models import (
    CorrectionSession,
    ExtractionStatus,
    ModelSettings,
    PromptProfile,
    TrainingExample,
    Workspace,
    WorkspaceAnalysis,
)
from .schema_utils import field_names, schema_contract


class TrainingExampleService:
    def create_from_extraction(
        self,
        session: Session,
        workspace_id: str,
        extraction_result_id: str,
        model_output: Any,
        extraction_status: ExtractionStatus,
        now: str,
        example_set_id: str = "",
    ) -> TrainingExample:
        status = "processing_error" if extraction_status == "processing_error" else "extracted"
        record = TrainingExampleRecord(
            id=new_id(),
            workspace_id=workspace_id,
            extraction_result_id=extraction_result_id,
            expected_output="{}",
            model_output=encode_json(model_output),
            corrected_output="{}",
            status=status,
            correction_notes="[]",
            prompt_profile_id="",
            created_at=now,
            updated_at=now,
        )
        session.add(record)
        session.flush()
        if example_set_id:
            session.add(
                TrainingExampleSetItemRecord(
                    id=new_id(),
                    example_set_id=example_set_id,
                    training_example_id=record.id,
                    created_at=now,
                )
            )
            parent_set = session.get(TrainingExampleSetRecord, example_set_id)
            if parent_set is not None:
                parent_set.updated_at = now
        return training_example_from_record(record)

    def list_by_workspace(self, session: Session, workspace_id: str) -> list[TrainingExample]:
        records = session.scalars(
            select(TrainingExampleRecord)
            .where(TrainingExampleRecord.workspace_id == workspace_id)
            .order_by(TrainingExampleRecord.updated_at.desc())
        ).all()
        return [training_example_from_record(record) for record in records]

    def mark_from_correction(
        self,
        session: Session,
        extraction_result_id: str,
        corrected_output: Any,
        status: ExtractionStatus,
    ) -> CorrectionSession | None:
        record = session.scalar(
            select(TrainingExampleRecord).where(TrainingExampleRecord.extraction_result_id == extraction_result_id)
        )
        if record is None:
            return None

        decision = "confirmed" if status == "completed" else "pending"
        example_status = "accepted" if status == "completed" else "correction_required"
        now = utc_now()
        record.corrected_output = encode_json(corrected_output)
        record.status = example_status
        record.updated_at = now

        session_record = CorrectionSessionRecord(
            id=new_id(),
            training_example_id=record.id,
            extraction_result_id=extraction_result_id,
            corrected_output=encode_json(corrected_output),
            notes="[]",
            decision=decision,
            created_at=now,
        )
        session.add(session_record)
        session.flush()
        return correction_session_from_record(session_record)

    def get_by_id(self, session: Session, example_id: str) -> TrainingExample:
        record = session.get(TrainingExampleRecord, example_id)
        if record is None:
            raise ValueError(f"Training example not found: {example_id}")
        return training_example_from_record(record)


class PromptProfileService:
    def generate_from_accepted_examples(
        self,
        session: Session,
        workspace: Workspace,
        settings: ModelSettings,
    ) -> WorkspaceAnalysis:
        examples = session.scalars(
            select(TrainingExampleRecord)
            .where(TrainingExampleRecord.workspace_id == workspace.id, TrainingExampleRecord.status == "accepted")
            .order_by(TrainingExampleRecord.updated_at.desc())
            .limit(10)
        ).all()
        return self.generate_from_example_records(session, workspace, settings, examples)

    def generate_from_example_set(
        self,
        session: Session,
        workspace: Workspace,
        settings: ModelSettings,
        example_set: TrainingExampleSetRecord,
    ) -> WorkspaceAnalysis:
        examples = [
            item.training_example
            for item in sorted(example_set.items, key=lambda item: item.created_at)
            if item.training_example.status == "accepted"
        ]
        return self.generate_from_example_records(session, workspace, settings, examples)

    def generate_from_example_records(
        self,
        session: Session,
        workspace: Workspace,
        settings: ModelSettings,
        examples: list[TrainingExampleRecord],
    ) -> WorkspaceAnalysis:
        sample_count = len(examples)
        if sample_count == 0:
            raise ValueError("At least one confirmed training example is required before prompt analysis.")
        target_fields = field_names(workspace.schema_info)
        if not target_fields:
            raise ValueError("Expected Output must contain at least one field before prompt analysis.")
        business_context = workspace.description.strip()
        prompt = (
            f"Business context: {business_context}. "
            "Extract the configured business fields from source documents. "
            "Return JSON only and follow the Expected Output contract exactly. "
            "Use arrays only for fields explicitly defined as JSON arrays. "
            f"Expected Output:\n{schema_contract(workspace.schema_info)}\n"
            f"Fields: {', '.join(target_fields)}. "
            f"Learned from {sample_count} confirmed sample(s)."
        )
        version = self._next_version(session, workspace.id)
        now = utc_now()
        for active_record in session.scalars(
            select(PromptProfileRecord).where(
                PromptProfileRecord.workspace_id == workspace.id,
                PromptProfileRecord.status == "active",
            )
        ):
            active_record.status = "retired"
        profile_record = PromptProfileRecord(
            id=new_id(),
            workspace_id=workspace.id,
            version=version,
            status="active",
            system_prompt="You are a deterministic document extraction engine.",
            extraction_instruction=prompt,
            output_contract=encode_json(workspace.schema_info),
            few_shot_examples=encode_json([training_example_from_record(record).model_dump(mode="json") for record in examples]),
            field_rules="[]",
            validation_rules="[]",
            model_provider=settings.provider,
            model_name=settings.model,
            created_at=now,
        )
        session.add(profile_record)
        for example in examples:
            example.prompt_profile_id = profile_record.id
            example.updated_at = now
        workspace_record = session.get(WorkspaceRecord, workspace.id)
        if workspace_record is not None:
            workspace_record.initialization_status = "active"
            workspace_record.active_status = 1
            workspace_record.active_prompt_profile_id = profile_record.id
            workspace_record.prompt_template = prompt
            workspace_record.updated_at = now
        return WorkspaceAnalysis(
            prompt_template=prompt,
            initialization_status="active",
            prompt_profile_id=profile_record.id,
            prompt_profile_version=version,
            sample_count=sample_count,
        )

    def list_by_workspace(self, session: Session, workspace_id: str) -> list[PromptProfile]:
        records = session.scalars(
            select(PromptProfileRecord)
            .where(PromptProfileRecord.workspace_id == workspace_id)
            .order_by(PromptProfileRecord.version.desc())
        ).all()
        return [prompt_profile_from_record(record) for record in records]

    def _next_version(self, session: Session, workspace_id: str) -> int:
        max_version = session.scalar(
            select(func.coalesce(func.max(PromptProfileRecord.version), 0)).where(
                PromptProfileRecord.workspace_id == workspace_id
            )
        )
        return int(max_version or 0) + 1


def training_example_from_record(record: TrainingExampleRecord) -> TrainingExample:
    return TrainingExample(
        id=record.id,
        workspace_id=record.workspace_id,
        extraction_result_id=record.extraction_result_id,
        expected_output=decode_json(record.expected_output, {}),
        model_output=decode_json(record.model_output, {}),
        corrected_output=decode_json(record.corrected_output, {}),
        status=record.status,
        correction_notes=decode_json(record.correction_notes, []),
        prompt_profile_id=record.prompt_profile_id,
        created_at=datetime.fromisoformat(record.created_at),
        updated_at=datetime.fromisoformat(record.updated_at),
    )


def correction_session_from_record(record: CorrectionSessionRecord) -> CorrectionSession:
    return CorrectionSession(
        id=record.id,
        training_example_id=record.training_example_id,
        extraction_result_id=record.extraction_result_id,
        corrected_output=decode_json(record.corrected_output, {}),
        notes=decode_json(record.notes, []),
        decision=record.decision,
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
        output_contract=decode_json(record.output_contract, []),
        few_shot_examples=decode_json(record.few_shot_examples, []),
        field_rules=decode_json(record.field_rules, []),
        validation_rules=decode_json(record.validation_rules, []),
        model_provider=record.model_provider,
        model_name=record.model_name,
        created_at=datetime.fromisoformat(record.created_at),
    )
