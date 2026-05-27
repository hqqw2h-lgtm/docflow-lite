"""Repository layer: pure ORM CRUD. No business rules.

Repositories take a Session (from contextmanager in caller) and operate on records.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db.records import (
    InvocationRecord,
    SampleRecord,
    SchemaSpaceRecord,
    SchemaSpaceVersionRecord,
    TraceRecord,
)


class SchemaSpaceRepo:
    def get(self, session: Session, space_id: str) -> SchemaSpaceRecord | None:
        return session.get(SchemaSpaceRecord, space_id)

    def list_by_tenant(self, session: Session, tenant_id: str) -> list[SchemaSpaceRecord]:
        return list(session.scalars(
            select(SchemaSpaceRecord)
            .where(SchemaSpaceRecord.tenant_id == tenant_id)
            .order_by(SchemaSpaceRecord.updated_at.desc())
        ).all())

    def add(self, session: Session, record: SchemaSpaceRecord) -> None:
        session.add(record)


class VersionRepo:
    def get(self, session: Session, version_id: str) -> SchemaSpaceVersionRecord | None:
        return session.get(SchemaSpaceVersionRecord, version_id)

    def list_by_space(self, session: Session, space_id: str) -> list[SchemaSpaceVersionRecord]:
        return list(session.scalars(
            select(SchemaSpaceVersionRecord)
            .where(SchemaSpaceVersionRecord.schema_space_id == space_id)
            .order_by(SchemaSpaceVersionRecord.version.desc())
        ).all())

    def list_published(self, session: Session, space_id: str) -> list[SchemaSpaceVersionRecord]:
        return list(session.scalars(
            select(SchemaSpaceVersionRecord)
            .where(
                SchemaSpaceVersionRecord.schema_space_id == space_id,
                SchemaSpaceVersionRecord.status == "published",
            )
            .order_by(SchemaSpaceVersionRecord.version.desc())
        ).all())

    def next_version_number(self, session: Session, space_id: str) -> int:
        current = session.scalar(
            select(func.coalesce(func.max(SchemaSpaceVersionRecord.version), 0))
            .where(SchemaSpaceVersionRecord.schema_space_id == space_id)
        )
        return int(current or 0) + 1

    def add(self, session: Session, record: SchemaSpaceVersionRecord) -> None:
        session.add(record)


class SampleRepo:
    def list_by_version(self, session: Session, version_id: str) -> list[SampleRecord]:
        return list(session.scalars(
            select(SampleRecord)
            .where(SampleRecord.version_id == version_id)
            .order_by(SampleRecord.created_at.desc())
        ).all())

    def get(self, session: Session, sample_id: str) -> SampleRecord | None:
        return session.get(SampleRecord, sample_id)

    def add(self, session: Session, record: SampleRecord) -> None:
        session.add(record)

    def count_confirmed(self, session: Session, version_id: str) -> int:
        return int(session.scalar(
            select(func.count(SampleRecord.id))
            .where(SampleRecord.version_id == version_id, SampleRecord.status == "confirmed")
        ) or 0)


class InvocationRepo:
    def get(self, session: Session, invocation_id: str) -> InvocationRecord | None:
        return session.get(InvocationRecord, invocation_id)

    def list_by_space(
        self,
        session: Session,
        space_id: str,
        *,
        version_id: str = "",
        source: str = "",
        status: str = "",
        limit: int = 100,
    ) -> list[InvocationRecord]:
        stmt = select(InvocationRecord).where(InvocationRecord.schema_space_id == space_id)
        if version_id:
            stmt = stmt.where(InvocationRecord.version_id == version_id)
        if source:
            stmt = stmt.where(InvocationRecord.source == source)
        if status:
            stmt = stmt.where(InvocationRecord.status == status)
        stmt = stmt.order_by(InvocationRecord.started_at.desc()).limit(limit)
        return list(session.scalars(stmt).all())

    def search(
        self,
        session: Session,
        *,
        space_id: str = "",
        version_id: str = "",
        status: str = "",
        source: str = "",
        file_name_contains: str = "",
        limit: int = 200,
    ) -> list[InvocationRecord]:
        stmt = select(InvocationRecord)
        if space_id:
            stmt = stmt.where(InvocationRecord.schema_space_id == space_id)
        if version_id:
            stmt = stmt.where(InvocationRecord.version_id == version_id)
        if status:
            stmt = stmt.where(InvocationRecord.status == status)
        if source:
            stmt = stmt.where(InvocationRecord.source == source)
        if file_name_contains:
            stmt = stmt.where(InvocationRecord.file_name.contains(file_name_contains))
        stmt = stmt.order_by(InvocationRecord.started_at.desc()).limit(limit)
        return list(session.scalars(stmt).all())

    def add(self, session: Session, record: InvocationRecord) -> None:
        session.add(record)


class TraceRepo:
    def get_by_invocation(self, session: Session, invocation_id: str) -> TraceRecord | None:
        return session.scalar(
            select(TraceRecord).where(TraceRecord.invocation_id == invocation_id)
        )

    def add(self, session: Session, record: TraceRecord) -> None:
        session.add(record)
