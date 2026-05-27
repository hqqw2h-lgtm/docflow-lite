"""New ORM records for SchemaSpace world.

These coexist with legacy WorkspaceRecord / SchemaDefinitionRecord / PromptProfileRecord
during migration. Eventually the legacy ones get retired.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...database import Base


class SchemaSpaceRecord(Base):
    __tablename__ = "schema_spaces"

    id: Mapped[str] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    input_file_types: Mapped[str] = mapped_column(nullable=False, default='["pdf"]', server_default='["pdf"]')
    normalizer_overrides: Mapped[str] = mapped_column(nullable=False, default="{}", server_default="{}")
    defaults: Mapped[str] = mapped_column(nullable=False, default="{}", server_default="{}")
    status: Mapped[str] = mapped_column(nullable=False, default="draft", server_default="draft")
    legacy_workspace_id: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    created_at: Mapped[str] = mapped_column(nullable=False)
    updated_at: Mapped[str] = mapped_column(nullable=False)

    versions: Mapped[list["SchemaSpaceVersionRecord"]] = relationship(back_populates="schema_space")


class SchemaSpaceVersionRecord(Base):
    __tablename__ = "schema_space_versions"

    id: Mapped[str] = mapped_column(primary_key=True)
    schema_space_id: Mapped[str] = mapped_column(ForeignKey("schema_spaces.id"), nullable=False)
    version: Mapped[int] = mapped_column(nullable=False)
    name: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    status: Mapped[str] = mapped_column(nullable=False, default="draft", server_default="draft")
    schema_info: Mapped[str] = mapped_column(nullable=False, default='{"outputType":"json","children":[]}')
    processing_policy: Mapped[str] = mapped_column(nullable=False, default="{}", server_default="{}")
    system_prompt: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    extraction_instruction: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    model_provider: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    model_name: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    parent_version_id: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    published_at: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    last_optimization: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    created_at: Mapped[str] = mapped_column(nullable=False)
    updated_at: Mapped[str] = mapped_column(nullable=False)

    schema_space: Mapped[SchemaSpaceRecord] = relationship(back_populates="versions")
    samples: Mapped[list["SampleRecord"]] = relationship(back_populates="version")


class SampleRecord(Base):
    __tablename__ = "samples"

    id: Mapped[str] = mapped_column(primary_key=True)
    version_id: Mapped[str] = mapped_column(ForeignKey("schema_space_versions.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(nullable=False)
    mime_type: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    file_type: Mapped[str] = mapped_column(nullable=False, default="text", server_default="text")
    size_bytes: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    sha256: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    document_context: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    status: Mapped[str] = mapped_column(nullable=False, default="uploaded", server_default="uploaded")
    expected_output: Mapped[str] = mapped_column(nullable=False, default="{}", server_default="{}")
    model_output: Mapped[str] = mapped_column(nullable=False, default="{}", server_default="{}")
    corrected_output: Mapped[str] = mapped_column(nullable=False, default="{}", server_default="{}")
    correction_notes: Mapped[str] = mapped_column(nullable=False, default="[]", server_default="[]")
    invocation_id: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    created_at: Mapped[str] = mapped_column(nullable=False)
    updated_at: Mapped[str] = mapped_column(nullable=False)

    version: Mapped[SchemaSpaceVersionRecord] = relationship(back_populates="samples")


class InvocationRecord(Base):
    __tablename__ = "invocations"

    id: Mapped[str] = mapped_column(primary_key=True)
    schema_space_id: Mapped[str] = mapped_column(ForeignKey("schema_spaces.id"), nullable=False)
    version_id: Mapped[str] = mapped_column(ForeignKey("schema_space_versions.id"), nullable=False)
    source: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(nullable=False, default="queued", server_default="queued")
    file_name: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    mime_type: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    file_type: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    size_bytes: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    sha256: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    document_context: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    model_provider: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    model_name: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    final_output: Mapped[str] = mapped_column(nullable=False, default="{}", server_default="{}")
    validation_issues: Mapped[str] = mapped_column(nullable=False, default="[]", server_default="[]")
    error_code: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    error_message: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    parent_invocation_id: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    duration_ms: Mapped[int] = mapped_column(nullable=False, default=0, server_default="0")
    started_at: Mapped[str] = mapped_column(nullable=False)
    ended_at: Mapped[str] = mapped_column(nullable=False, default="", server_default="")


class TraceRecord(Base):
    __tablename__ = "traces"

    id: Mapped[str] = mapped_column(primary_key=True)
    invocation_id: Mapped[str] = mapped_column(ForeignKey("invocations.id"), nullable=False)
    schema_space_id: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    version_id: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    model_provider: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    model_name: Mapped[str] = mapped_column(nullable=False, default="", server_default="")
    spans: Mapped[str] = mapped_column(nullable=False, default="[]", server_default="[]")
    created_at: Mapped[str] = mapped_column(nullable=False)
