"""SchemaSpace CRUD service. Pure business rules on top of repositories."""
from __future__ import annotations

from fastapi import HTTPException

from ..database import TenantRecord, encode_json, get_session, new_id, utc_now
from ..db.records import SchemaSpaceRecord
from ..domain import (
    FileType,
    SchemaSpace,
    SchemaSpaceCreate,
    SchemaSpaceDefaults,
    SchemaSpaceStatus,
    SchemaSpaceUpdate,
)
from ..processing.normalizers import get_normalizer_by_name
from ..providers import get_provider, list_providers
from ..repositories import SchemaSpaceRepo, VersionRepo
from .component_resolver import resolve_components
from .mappers import schema_space_from_record, version_from_record


class SchemaSpaceService:
    def __init__(self) -> None:
        self.repo = SchemaSpaceRepo()
        self.version_repo = VersionRepo()

    def effective_config(self, space_id: str, version_id: str | None = None) -> dict:
        with get_session() as session:
            space_rec = self.repo.get(session, space_id)
            if space_rec is None:
                raise HTTPException(status_code=404, detail="SchemaSpace not found")
            space = schema_space_from_record(space_rec)
            version = None
            if version_id:
                v_rec = self.version_repo.get(session, version_id)
                if v_rec is None:
                    raise HTTPException(status_code=404, detail="Version not found")
                if v_rec.schema_space_id != space_id:
                    raise HTTPException(
                        status_code=400,
                        detail="Version does not belong to this SchemaSpace",
                    )
                version = version_from_record(v_rec)
            return resolve_components(space, version).as_dict()

    def list(self, tenant_id: str) -> list[SchemaSpace]:
        with get_session() as session:
            records = self.repo.list_by_tenant(session, tenant_id)
            return [schema_space_from_record(r) for r in records]

    def get(self, space_id: str) -> SchemaSpace:
        with get_session() as session:
            record = self.repo.get(session, space_id)
            if record is None:
                raise HTTPException(status_code=404, detail="SchemaSpace not found")
            return schema_space_from_record(record)

    def create(self, payload: SchemaSpaceCreate) -> SchemaSpace:
        if not payload.input_file_types:
            raise HTTPException(status_code=400, detail="input_file_types must contain at least one entry")
        self._validate_overrides(payload.normalizer_overrides, payload.input_file_types)
        self._validate_defaults(payload.defaults)
        with get_session() as session:
            if session.get(TenantRecord, payload.tenant_id) is None:
                raise HTTPException(status_code=404, detail=f"Tenant not found: {payload.tenant_id}")
            now = utc_now()
            record = SchemaSpaceRecord(
                id=new_id(),
                tenant_id=payload.tenant_id,
                name=payload.name,
                description=payload.description,
                input_file_types=encode_json([ft.value for ft in payload.input_file_types]),
                normalizer_overrides=encode_json(payload.normalizer_overrides),
                defaults=encode_json(payload.defaults.model_dump()),
                status=SchemaSpaceStatus.DRAFT.value,
                created_at=now,
                updated_at=now,
            )
            self.repo.add(session, record)
            session.flush()
            return schema_space_from_record(record)

    def update(self, space_id: str, payload: SchemaSpaceUpdate) -> SchemaSpace:
        with get_session() as session:
            record = self.repo.get(session, space_id)
            if record is None:
                raise HTTPException(status_code=404, detail="SchemaSpace not found")
            if payload.name is not None:
                trimmed = payload.name.strip()
                if not trimmed:
                    raise HTTPException(status_code=400, detail="name must not be empty")
                record.name = trimmed
            if payload.description is not None:
                record.description = payload.description
            if payload.input_file_types is not None:
                if not payload.input_file_types:
                    raise HTTPException(status_code=400, detail="input_file_types must contain at least one entry")
                record.input_file_types = encode_json([ft.value for ft in payload.input_file_types])
            if payload.normalizer_overrides is not None:
                current_space = schema_space_from_record(record)
                self._validate_overrides(payload.normalizer_overrides, current_space.input_file_types)
                record.normalizer_overrides = encode_json(payload.normalizer_overrides)
            if payload.schema_info is not None:
                record.schema_info = encode_json(payload.schema_info)
            if payload.defaults is not None:
                self._validate_defaults(payload.defaults)
                record.defaults = encode_json(payload.defaults.model_dump())
            if payload.status is not None:
                record.status = payload.status.value
            record.updated_at = utc_now()
            return schema_space_from_record(record)

    def assert_file_type_allowed(self, space: SchemaSpace, file_name: str) -> FileType:
        detected = FileType.from_filename(file_name)
        if detected is None:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file extension for '{file_name}'.",
            )
        if detected not in space.input_file_types:
            allowed = ", ".join(ft.value for ft in space.input_file_types)
            raise HTTPException(
                status_code=400,
                detail=f"SchemaSpace '{space.name}' only accepts: {allowed}. Got: {detected.value}",
            )
        return detected

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _validate_overrides(
        self,
        overrides: dict[str, str],
        input_file_types: list[FileType],
    ) -> None:
        """Each override key must be a configured file_type and value must be a
        registered normalizer that supports that file_type."""
        allowed_values = {ft.value for ft in input_file_types}
        for ft_value, normalizer_name in overrides.items():
            if ft_value not in allowed_values:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"normalizer_overrides references file_type '{ft_value}' "
                        f"which is not in input_file_types {sorted(allowed_values)}"
                    ),
                )
            try:
                normalizer = get_normalizer_by_name(normalizer_name)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            try:
                file_type = FileType(ft_value)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=f"Unknown file_type: {ft_value}") from exc
            if file_type not in normalizer.supported_types:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Normalizer '{normalizer_name}' does not support file_type "
                        f"'{ft_value}'. Supported: "
                        f"{[t.value for t in normalizer.supported_types]}"
                    ),
                )

    def _validate_defaults(self, defaults: SchemaSpaceDefaults) -> None:
        """Ensure SchemaSpace.defaults reference known providers."""
        if defaults.model_provider:
            try:
                get_provider(defaults.model_provider)
            except ValueError as exc:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"defaults.model_provider '{defaults.model_provider}' is not registered. "
                        f"Available: {list_providers()}"
                    ),
                ) from exc
        # model_name is provider-specific and free-form; we don't validate it here.
        # processing_policy / system_prompt / extraction_instruction are also free-form.

