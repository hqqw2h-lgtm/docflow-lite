from __future__ import annotations

from fastapi import APIRouter, Depends

from ..domain import SchemaSpaceVersion, VersionCreate, VersionUpdate
from ..services import VersionLifecycleService
from .deps import version_service

router = APIRouter(prefix="/api/schema-spaces/{space_id}/versions", tags=["versions"])


@router.get("", response_model=list[SchemaSpaceVersion])
def list_versions(
    space_id: str,
    svc: VersionLifecycleService = Depends(version_service),
) -> list[SchemaSpaceVersion]:
    return svc.list(space_id)


@router.post("", response_model=SchemaSpaceVersion, status_code=201)
def create_version(
    space_id: str,
    payload: VersionCreate,
    svc: VersionLifecycleService = Depends(version_service),
) -> SchemaSpaceVersion:
    # Force path id into payload (path is the source of truth).
    body = payload.model_copy(update={"schema_space_id": space_id})
    return svc.create_draft(body)


@router.get("/{version_id}", response_model=SchemaSpaceVersion)
def get_version(
    space_id: str,
    version_id: str,
    svc: VersionLifecycleService = Depends(version_service),
) -> SchemaSpaceVersion:
    return svc.get(version_id)


@router.patch("/{version_id}", response_model=SchemaSpaceVersion)
def update_version(
    space_id: str,
    version_id: str,
    payload: VersionUpdate,
    svc: VersionLifecycleService = Depends(version_service),
) -> SchemaSpaceVersion:
    return svc.update_draft(version_id, payload)


@router.post("/{version_id}/publish", response_model=SchemaSpaceVersion)
def publish_version(
    space_id: str,
    version_id: str,
    svc: VersionLifecycleService = Depends(version_service),
) -> SchemaSpaceVersion:
    return svc.publish(version_id)


@router.post("/{version_id}/clone", response_model=SchemaSpaceVersion, status_code=201)
def clone_version(
    space_id: str,
    version_id: str,
    svc: VersionLifecycleService = Depends(version_service),
) -> SchemaSpaceVersion:
    return svc.clone(version_id)


@router.post("/{version_id}/archive", response_model=SchemaSpaceVersion)
def archive_version(
    space_id: str,
    version_id: str,
    svc: VersionLifecycleService = Depends(version_service),
) -> SchemaSpaceVersion:
    return svc.archive(version_id)
