from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from ..domain import Invocation, InvocationSource, Trace
from ..services import InvocationService
from .deps import invocation_service

router = APIRouter(tags=["invocations"])


@router.post(
    "/api/schema-spaces/{space_id}/versions/{version_id}/invoke",
    response_model=Invocation,
    status_code=201,
)
async def invoke_version(
    space_id: str,
    version_id: str,
    file: UploadFile = File(...),
    document_context: str = Form(""),
    source: str = Form("ui"),
    svc: InvocationService = Depends(invocation_service),
) -> Invocation:
    try:
        src = InvocationSource(source)
    except ValueError:
        src = InvocationSource.UI
    return await svc.invoke_upload(
        version_id=version_id,
        file=file,
        document_context=document_context,
        source=src,
    )


@router.get("/api/invocations", response_model=list[Invocation])
def list_invocations(
    space_id: str = Query(""),
    version_id: str = Query(""),
    source: str = Query(""),
    status: str = Query(""),
    limit: int = Query(100, ge=1, le=500),
    svc: InvocationService = Depends(invocation_service),
) -> list[Invocation]:
    return svc.list(space_id=space_id, version_id=version_id, source=source, status=status, limit=limit)


@router.get("/api/invocations/{invocation_id}", response_model=Invocation)
def get_invocation(
    invocation_id: str,
    svc: InvocationService = Depends(invocation_service),
) -> Invocation:
    return svc.get(invocation_id)


@router.get("/api/invocations/{invocation_id}/trace", response_model=Trace)
def get_invocation_trace(
    invocation_id: str,
    svc: InvocationService = Depends(invocation_service),
) -> Trace:
    return svc.get_trace(invocation_id)
