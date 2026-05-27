"""Admin observability: cross-space trace explorer + replay."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..database import get_session
from ..domain import Invocation, InvocationSource, Trace
from ..repositories import InvocationRepo
from ..services import InvocationService
from .deps import invocation_service
from .deps import sample_service  # noqa: F401  (reserved for future replay-from-sample)
from ..services.mappers import invocation_from_record

router = APIRouter(prefix="/api/admin", tags=["admin"])
_invocation_repo = InvocationRepo()


@router.get("/invocations", response_model=list[Invocation])
def admin_search_invocations(
    space_id: str = Query(""),
    version_id: str = Query(""),
    source: str = Query(""),
    status: str = Query(""),
    file_name_contains: str = Query(""),
    limit: int = Query(200, ge=1, le=1000),
) -> list[Invocation]:
    with get_session() as session:
        records = _invocation_repo.search(
            session,
            space_id=space_id,
            version_id=version_id,
            status=status,
            source=source,
            file_name_contains=file_name_contains,
            limit=limit,
        )
        return [invocation_from_record(r) for r in records]


@router.get("/invocations/{invocation_id}/trace", response_model=Trace)
def admin_get_trace(
    invocation_id: str,
    svc: InvocationService = Depends(invocation_service),
) -> Trace:
    return svc.get_trace(invocation_id)


@router.post("/invocations/{invocation_id}/replay", response_model=Invocation)
async def admin_replay(
    invocation_id: str,
    svc: InvocationService = Depends(invocation_service),
) -> Invocation:
    # Minimal replay stub: replay requires the original file payload, which is
    # not preserved in this build. Return 501 so the UI can surface a clear
    # message until file persistence per-invocation is implemented.
    raise HTTPException(
        status_code=501,
        detail="Replay is not yet implemented in this build. Re-upload the document via the version invoke endpoint.",
    )
