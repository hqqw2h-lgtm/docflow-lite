"""Version lifecycle: create draft / publish / clone / archive.

Crucial rule: a SchemaSpace may have multiple PUBLISHED versions concurrently.
Publishing one version does NOT auto-archive others.
"""
from __future__ import annotations

from fastapi import HTTPException

from ..database import encode_json, get_session, new_id, utc_now
from ..db.records import SchemaSpaceVersionRecord
from ..domain import (
    SchemaSpaceVersion,
    VersionCreate,
    VersionStatus,
    VersionUpdate,
)
from ..repositories import SampleRepo, SchemaSpaceRepo, VersionRepo
from .mappers import version_from_record


class VersionLifecycleService:
    def __init__(self) -> None:
        self.space_repo = SchemaSpaceRepo()
        self.version_repo = VersionRepo()
        self.sample_repo = SampleRepo()

    def list(self, space_id: str) -> list[SchemaSpaceVersion]:
        with get_session() as session:
            if self.space_repo.get(session, space_id) is None:
                raise HTTPException(status_code=404, detail="SchemaSpace not found")
            records = self.version_repo.list_by_space(session, space_id)
            return [
                version_from_record(r, sample_count=self.sample_repo.count_confirmed(session, r.id))
                for r in records
            ]

    def get(self, version_id: str) -> SchemaSpaceVersion:
        with get_session() as session:
            record = self.version_repo.get(session, version_id)
            if record is None:
                raise HTTPException(status_code=404, detail="Version not found")
            return version_from_record(record, sample_count=self.sample_repo.count_confirmed(session, record.id))

    def create_draft(self, payload: VersionCreate) -> SchemaSpaceVersion:
        with get_session() as session:
            space = self.space_repo.get(session, payload.schema_space_id)
            if space is None:
                raise HTTPException(status_code=404, detail="SchemaSpace not found")
            now = utc_now()
            number = self.version_repo.next_version_number(session, payload.schema_space_id)
            # Inherit schema_info from SchemaSpace if not explicitly provided
            import json as _json
            schema_info = payload.schema_info
            default_empty = {"outputType": "json", "children": []}
            if schema_info == default_empty:
                space_schema = _json.loads(getattr(space, "schema_info", "") or '{"outputType":"json","children":[]}')
                if space_schema and space_schema != default_empty:
                    schema_info = space_schema
            record = SchemaSpaceVersionRecord(
                id=new_id(),
                schema_space_id=payload.schema_space_id,
                version=number,
                name=payload.name or f"v{number}",
                status=VersionStatus.DRAFT.value,
                schema_info=encode_json(schema_info),
                processing_policy=encode_json({}),
                system_prompt="",
                extraction_instruction="",
                model_provider="",
                model_name="",
                parent_version_id=payload.parent_version_id,
                published_at="",
                created_at=now,
                updated_at=now,
            )
            self.version_repo.add(session, record)
            session.flush()
            return version_from_record(record)

    def update_draft(self, version_id: str, payload: VersionUpdate) -> SchemaSpaceVersion:
        with get_session() as session:
            record = self.version_repo.get(session, version_id)
            if record is None:
                raise HTTPException(status_code=404, detail="Version not found")
            if record.status != VersionStatus.DRAFT.value:
                raise HTTPException(
                    status_code=409,
                    detail="Only draft versions are editable. Clone a published version to make changes.",
                )
            if payload.name is not None:
                record.name = payload.name
            if payload.schema_info is not None:
                record.schema_info = encode_json(payload.schema_info)
            if payload.processing_policy is not None:
                record.processing_policy = encode_json(payload.processing_policy)
            if payload.system_prompt is not None:
                record.system_prompt = payload.system_prompt
            if payload.extraction_instruction is not None:
                record.extraction_instruction = payload.extraction_instruction
            if payload.model_provider is not None:
                record.model_provider = payload.model_provider
            if payload.model_name is not None:
                record.model_name = payload.model_name
            record.updated_at = utc_now()
            return version_from_record(record)

    def publish(self, version_id: str) -> SchemaSpaceVersion:
        with get_session() as session:
            record = self.version_repo.get(session, version_id)
            if record is None:
                raise HTTPException(status_code=404, detail="Version not found")
            if record.status == VersionStatus.PUBLISHED.value:
                raise HTTPException(status_code=409, detail="Version is already published.")
            if record.status == VersionStatus.ARCHIVED.value:
                raise HTTPException(status_code=409, detail="Cannot publish an archived version.")
            confirmed = self.sample_repo.count_confirmed(session, record.id)
            if confirmed == 0:
                raise HTTPException(
                    status_code=422,
                    detail="At least one confirmed sample is required before publishing.",
                )
            now = utc_now()
            record.status = VersionStatus.PUBLISHED.value
            record.published_at = now
            record.updated_at = now
            return version_from_record(record, sample_count=confirmed)

    def clone(self, version_id: str) -> SchemaSpaceVersion:
        with get_session() as session:
            source = self.version_repo.get(session, version_id)
            if source is None:
                raise HTTPException(status_code=404, detail="Version not found")
            now = utc_now()
            number = self.version_repo.next_version_number(session, source.schema_space_id)
            cloned = SchemaSpaceVersionRecord(
                id=new_id(),
                schema_space_id=source.schema_space_id,
                version=number,
                name=f"v{number} (from v{source.version})",
                status=VersionStatus.DRAFT.value,
                schema_info=source.schema_info,
                processing_policy=source.processing_policy,
                system_prompt=source.system_prompt,
                extraction_instruction=source.extraction_instruction,
                model_provider=source.model_provider,
                model_name=source.model_name,
                parent_version_id=source.id,
                published_at="",
                created_at=now,
                updated_at=now,
            )
            self.version_repo.add(session, cloned)
            session.flush()
            return version_from_record(cloned)

    def archive(self, version_id: str) -> SchemaSpaceVersion:
        with get_session() as session:
            record = self.version_repo.get(session, version_id)
            if record is None:
                raise HTTPException(status_code=404, detail="Version not found")
            record.status = VersionStatus.ARCHIVED.value
            record.updated_at = utc_now()
            return version_from_record(record, sample_count=self.sample_repo.count_confirmed(session, record.id))
