from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from sqlalchemy import ForeignKey, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
UPLOAD_DIR = ROOT_DIR / "uploads"
DB_PATH = DATA_DIR / "docflow.sqlite3"
DEFAULT_TENANT_ID = "local-tenant"
_ENGINE: Engine | None = None
_ENGINE_PATH: Path | None = None


class Base(DeclarativeBase):
    pass


class TenantRecord(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False, default="active")
    created_at: Mapped[str] = mapped_column(nullable=False)
    updated_at: Mapped[str] = mapped_column(nullable=False)
    workspaces: Mapped[list["WorkspaceRecord"]] = relationship(back_populates="tenant")


class WorkspaceRecord(Base):
    __tablename__ = "workspaces"

    id: Mapped[str] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False, default=DEFAULT_TENANT_ID, server_default=DEFAULT_TENANT_ID)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False)
    schema_type: Mapped[str] = mapped_column(nullable=False, default="CUSTOM", server_default="CUSTOM")
    active_status: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    initialization_status: Mapped[str] = mapped_column(nullable=False, default="inactive", server_default="inactive")
    active_schema_version_id: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    active_prompt_profile_id: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    prompt_template: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    extracted: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    schema_info: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[str] = mapped_column(nullable=False)
    updated_at: Mapped[str] = mapped_column(nullable=False)
    tenant: Mapped[TenantRecord] = relationship(back_populates="workspaces")
    schema_definitions: Mapped[list["SchemaDefinitionRecord"]] = relationship(back_populates="workspace")
    prompt_profiles: Mapped[list["PromptProfileRecord"]] = relationship(back_populates="workspace")
    background_files: Mapped[list["WorkspaceBackgroundFileRecord"]] = relationship(back_populates="workspace")
    normalized_documents: Mapped[list["NormalizedDocumentRecord"]] = relationship(back_populates="workspace")
    extraction_results: Mapped[list["ExtractionResultRecord"]] = relationship(back_populates="workspace")
    training_examples: Mapped[list["TrainingExampleRecord"]] = relationship(back_populates="workspace")
    training_example_sets: Mapped[list["TrainingExampleSetRecord"]] = relationship(back_populates="workspace")
    integrations: Mapped[list["IntegrationRecord"]] = relationship(back_populates="workspace")


class SchemaDefinitionRecord(Base):
    __tablename__ = "schema_definitions"

    id: Mapped[str] = mapped_column(primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    version: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)
    schema_info: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[str] = mapped_column(nullable=False)
    workspace: Mapped[WorkspaceRecord] = relationship(back_populates="schema_definitions")


class PromptProfileRecord(Base):
    __tablename__ = "prompt_profiles"

    id: Mapped[str] = mapped_column(primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    version: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)
    system_prompt: Mapped[str] = mapped_column(nullable=False)
    extraction_instruction: Mapped[str] = mapped_column(nullable=False)
    output_contract: Mapped[str] = mapped_column(nullable=False)
    few_shot_examples: Mapped[str] = mapped_column(nullable=False, default="[]")
    field_rules: Mapped[str] = mapped_column(nullable=False, default="[]")
    validation_rules: Mapped[str] = mapped_column(nullable=False, default="[]")
    model_provider: Mapped[str] = mapped_column(nullable=False)
    model_name: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[str] = mapped_column(nullable=False)
    workspace: Mapped[WorkspaceRecord] = relationship(back_populates="prompt_profiles")


class NormalizedDocumentRecord(Base):
    __tablename__ = "normalized_documents"

    id: Mapped[str] = mapped_column(primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    extraction_result_id: Mapped[str] = mapped_column(ForeignKey("extraction_results.id"), nullable=False, unique=True)
    file_name: Mapped[str] = mapped_column(nullable=False)
    mime_type: Mapped[str] = mapped_column(nullable=False)
    source_sha256: Mapped[str] = mapped_column(nullable=False)
    normalizer: Mapped[str] = mapped_column(nullable=False)
    normalizer_version: Mapped[str] = mapped_column(nullable=False)
    markdown: Mapped[str] = mapped_column(nullable=False)
    text_content: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    blocks: Mapped[str] = mapped_column(nullable=False, default="[]", server_default="[]")
    tables: Mapped[str] = mapped_column(nullable=False, default="[]", server_default="[]")
    assets: Mapped[str] = mapped_column(nullable=False, default="[]", server_default="[]")
    trace: Mapped[str] = mapped_column(nullable=False, default="{}", server_default="{}")
    created_at: Mapped[str] = mapped_column(nullable=False)
    workspace: Mapped[WorkspaceRecord] = relationship(back_populates="normalized_documents")
    extraction_result: Mapped["ExtractionResultRecord"] = relationship(back_populates="normalized_document")


class ExtractionResultRecord(Base):
    __tablename__ = "extraction_results"

    id: Mapped[str] = mapped_column(primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(nullable=False)
    model: Mapped[str] = mapped_column(nullable=False)
    raw_text: Mapped[str] = mapped_column(nullable=False)
    extracted_data: Mapped[str] = mapped_column(nullable=False)
    corrected_data: Mapped[str] = mapped_column(nullable=False, default="{}", server_default="{}")
    status: Mapped[str] = mapped_column(nullable=False, default="to_review", server_default="to_review")
    trace: Mapped[str] = mapped_column(nullable=False, default="{}", server_default="{}")
    created_at: Mapped[str] = mapped_column(nullable=False)
    workspace: Mapped[WorkspaceRecord] = relationship(back_populates="extraction_results")
    normalized_document: Mapped[NormalizedDocumentRecord | None] = relationship(back_populates="extraction_result", uselist=False)
    training_example: Mapped["TrainingExampleRecord | None"] = relationship(back_populates="extraction_result")


class TrainingExampleRecord(Base):
    __tablename__ = "training_examples"

    id: Mapped[str] = mapped_column(primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    extraction_result_id: Mapped[str] = mapped_column(ForeignKey("extraction_results.id"), nullable=False)
    expected_output: Mapped[str] = mapped_column(nullable=False, default="{}", server_default="{}")
    model_output: Mapped[str] = mapped_column(nullable=False, default="{}", server_default="{}")
    corrected_output: Mapped[str] = mapped_column(nullable=False, default="{}", server_default="{}")
    status: Mapped[str] = mapped_column(nullable=False)
    correction_notes: Mapped[str] = mapped_column(nullable=False, default="[]", server_default="[]")
    prompt_profile_id: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    created_at: Mapped[str] = mapped_column(nullable=False)
    updated_at: Mapped[str] = mapped_column(nullable=False)
    workspace: Mapped[WorkspaceRecord] = relationship(back_populates="training_examples")
    extraction_result: Mapped[ExtractionResultRecord] = relationship(back_populates="training_example")
    correction_sessions: Mapped[list["CorrectionSessionRecord"]] = relationship(back_populates="training_example")
    set_items: Mapped[list["TrainingExampleSetItemRecord"]] = relationship(back_populates="training_example")


class TrainingExampleSetRecord(Base):
    __tablename__ = "training_example_sets"

    id: Mapped[str] = mapped_column(primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    version: Mapped[int] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False, default="draft", server_default="draft")
    prompt_profile_id: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    created_at: Mapped[str] = mapped_column(nullable=False)
    updated_at: Mapped[str] = mapped_column(nullable=False)
    workspace: Mapped[WorkspaceRecord] = relationship(back_populates="training_example_sets")
    items: Mapped[list["TrainingExampleSetItemRecord"]] = relationship(back_populates="example_set")


class TrainingExampleSetItemRecord(Base):
    __tablename__ = "training_example_set_items"

    id: Mapped[str] = mapped_column(primary_key=True)
    example_set_id: Mapped[str] = mapped_column(ForeignKey("training_example_sets.id"), nullable=False)
    training_example_id: Mapped[str] = mapped_column(ForeignKey("training_examples.id"), nullable=False)
    created_at: Mapped[str] = mapped_column(nullable=False)
    example_set: Mapped[TrainingExampleSetRecord] = relationship(back_populates="items")
    training_example: Mapped[TrainingExampleRecord] = relationship(back_populates="set_items")


class CorrectionSessionRecord(Base):
    __tablename__ = "correction_sessions"

    id: Mapped[str] = mapped_column(primary_key=True)
    training_example_id: Mapped[str] = mapped_column(ForeignKey("training_examples.id"), nullable=False)
    extraction_result_id: Mapped[str] = mapped_column(ForeignKey("extraction_results.id"), nullable=False)
    corrected_output: Mapped[str] = mapped_column(nullable=False, default="{}", server_default="{}")
    notes: Mapped[str] = mapped_column(nullable=False, default="[]", server_default="[]")
    decision: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[str] = mapped_column(nullable=False)
    training_example: Mapped[TrainingExampleRecord] = relationship(back_populates="correction_sessions")


class WorkspaceBackgroundFileRecord(Base):
    __tablename__ = "workspace_background_files"

    id: Mapped[str] = mapped_column(primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(nullable=False)
    mime_type: Mapped[str] = mapped_column(nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    extracted_text: Mapped[str] = mapped_column(nullable=False, default="")
    ai_summary: Mapped[str] = mapped_column(nullable=False, default="")
    created_at: Mapped[str] = mapped_column(nullable=False)
    workspace: Mapped[WorkspaceRecord] = relationship(back_populates="background_files")


class SettingsRecord(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[str] = mapped_column(nullable=False)


class IntegrationRecord(Base):
    __tablename__ = "integrations"

    id: Mapped[str] = mapped_column(primary_key=True)
    workspace_id: Mapped[str] = mapped_column(ForeignKey("workspaces.id"), nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False)
    config: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[str] = mapped_column(nullable=False)
    updated_at: Mapped[str] = mapped_column(nullable=False)
    workspace: Mapped[WorkspaceRecord] = relationship(back_populates="integrations")


def utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


def new_id() -> str:
    return uuid4().hex


def encode_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def decode_json(value: str | None, default: Any) -> Any:
    if not value:
        return default
    return json.loads(value)


def get_engine() -> Engine:
    global _ENGINE, _ENGINE_PATH
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    if _ENGINE is None or _ENGINE_PATH != DB_PATH:
        _ENGINE = create_engine(
            f"sqlite:///{DB_PATH}",
            future=True,
            connect_args={"check_same_thread": False},
        )
        _ENGINE_PATH = DB_PATH
    return _ENGINE


@contextmanager
def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        with session.begin():
            yield session


def _ensure_column(engine, table: str, column: str, ddl: str) -> None:
    """Add a column to an existing SQLite table if missing (lightweight migration)."""
    from sqlalchemy import text as _text
    with engine.begin() as conn:
        rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
        existing = {r[1] for r in rows}
        if column not in existing:
            conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def init_db() -> None:
    engine = get_engine()
    Base.metadata.create_all(engine)
    _ensure_column(engine, "schema_space_versions", "last_optimization", "TEXT NOT NULL DEFAULT ''")
    _ensure_column(engine, "schema_spaces", "schema_info", "TEXT NOT NULL DEFAULT '{\"outputType\":\"json\",\"children\":[]}'")

    with get_session() as session:
        if session.get(TenantRecord, DEFAULT_TENANT_ID) is None:
            now = utc_now()
            session.add(
                TenantRecord(
                    id=DEFAULT_TENANT_ID,
                    name="Local Tenant",
                    description="Default local tenant for personal document automation.",
                    status="active",
                    created_at=now,
                    updated_at=now,
                )
            )
        if session.get(SettingsRecord, "model") is None:
            session.add(
                SettingsRecord(
                    key="model",
                    value=encode_json(
                        {
                            "provider": "ollama",
                            "base_url": "http://localhost:11434",
                            "model": "llama3.1",
                        }
                    ),
                )
            )
