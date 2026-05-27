"""Admin observability: cross-space trace explorer + replay."""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from ..database import UPLOAD_DIR, get_session
from ..domain import Invocation, InvocationSource, Trace
from ..repositories import InvocationRepo
from ..services import InvocationService, SampleService
from .deps import invocation_service, sample_service
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
    """Replay an invocation using the original file (found via UPLOAD_DIR + sha256/filename)."""
    original = svc.get(invocation_id)

    # Find the stored file by scanning uploads for matching sha256
    stored_file: Path | None = None
    if UPLOAD_DIR.exists():
        for candidate in UPLOAD_DIR.iterdir():
            if candidate.name.endswith(f"-{original.file_name}"):
                import hashlib
                content = candidate.read_bytes()
                if hashlib.sha256(content).hexdigest() == original.sha256:
                    stored_file = candidate
                    break

    if stored_file is None:
        raise HTTPException(
            status_code=404,
            detail=f"Original file '{original.file_name}' (sha256={original.sha256[:12]}...) not found in uploads. Re-upload via the invoke endpoint.",
        )

    class _ReplayFile:
        def __init__(self, path: Path, name: str, mime: str):
            self.filename = name
            self.content_type = mime
            self._data = path.read_bytes()

        async def read(self) -> bytes:
            return self._data

    replay_file = _ReplayFile(stored_file, original.file_name, original.mime_type)
    return await svc.invoke_upload(
        version_id=original.version_id,
        file=replay_file,  # type: ignore[arg-type]
        document_context=original.document_context,
        source=InvocationSource.REPLAY,
        parent_invocation_id=invocation_id,
    )
