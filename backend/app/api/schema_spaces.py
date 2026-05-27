from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..domain import SchemaSpace, SchemaSpaceCreate, SchemaSpaceUpdate
from ..services import SchemaSpaceService
from .deps import schema_space_service

router = APIRouter(prefix="/api/schema-spaces", tags=["schema-spaces"])


@router.get("", response_model=list[SchemaSpace])
def list_schema_spaces(
    tenant_id: str = Query("local-tenant"),
    svc: SchemaSpaceService = Depends(schema_space_service),
) -> list[SchemaSpace]:
    return svc.list(tenant_id)


@router.post("", response_model=SchemaSpace, status_code=201)
def create_schema_space(
    payload: SchemaSpaceCreate,
    svc: SchemaSpaceService = Depends(schema_space_service),
) -> SchemaSpace:
    return svc.create(payload)


@router.get("/{space_id}", response_model=SchemaSpace)
def get_schema_space(
    space_id: str,
    svc: SchemaSpaceService = Depends(schema_space_service),
) -> SchemaSpace:
    return svc.get(space_id)


@router.patch("/{space_id}", response_model=SchemaSpace)
def update_schema_space(
    space_id: str,
    payload: SchemaSpaceUpdate,
    svc: SchemaSpaceService = Depends(schema_space_service),
) -> SchemaSpace:
    return svc.update(space_id, payload)


@router.get("/{space_id}/effective-config")
def get_effective_config(
    space_id: str,
    version_id: str | None = Query(None),
    svc: SchemaSpaceService = Depends(schema_space_service),
) -> dict:
    """Return the fully resolved pipeline components for this SchemaSpace
    (optionally narrowed to a specific version). Shows precedence sources so
    operators can see whether each component came from version, space, or
    system defaults.
    """
    return svc.effective_config(space_id, version_id)
