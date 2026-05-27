"""Optimizer API: auto-find best pipeline config before publishing a version."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException

from ..database import get_session
from ..repositories import VersionRepo
from ..services import OptimizerService
from .deps import optimizer_service

router = APIRouter(
    prefix="/api/schema-spaces/{space_id}/versions/{version_id}",
    tags=["optimizer"],
)


@router.post("/optimize")
async def optimize_version(
    space_id: str,
    version_id: str,
    apply: bool = True,
    svc: OptimizerService = Depends(optimizer_service),
) -> dict:
    """Run the grid search and (by default) persist the winning combination.

    Pass ``apply=false`` to preview the report without mutating the SchemaSpace.
    """
    report = await svc.optimize(version_id, apply_best=apply)
    return report.as_dict()


@router.get("/optimize/last")
def get_last_optimization(
    space_id: str,
    version_id: str,
) -> dict:
    """Return the most recent optimization report stored on the version."""
    with get_session() as session:
        rec = VersionRepo().get(session, version_id)
        if rec is None:
            raise HTTPException(status_code=404, detail="Version not found")
        raw = rec.last_optimization or ""
        if not raw:
            return {"version_id": version_id, "report": None}
        try:
            return {"version_id": version_id, "report": json.loads(raw)}
        except json.JSONDecodeError:
            return {"version_id": version_id, "report": None}
