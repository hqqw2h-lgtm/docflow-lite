from __future__ import annotations

import json

from fastapi import APIRouter, Depends, File, Form, UploadFile

from ..domain import Sample
from ..services import SampleService
from .deps import sample_service

router = APIRouter(prefix="/api/schema-spaces/{space_id}/versions/{version_id}/samples", tags=["samples"])


@router.get("", response_model=list[Sample])
def list_samples(
    space_id: str,
    version_id: str,
    svc: SampleService = Depends(sample_service),
) -> list[Sample]:
    return svc.list(version_id)


@router.post("", response_model=Sample, status_code=201)
async def upload_sample(
    space_id: str,
    version_id: str,
    file: UploadFile = File(...),
    document_context: str = Form(""),
    expected_output: str = Form(""),
    svc: SampleService = Depends(sample_service),
) -> Sample:
    parsed_expected = None
    if expected_output:
        try:
            parsed_expected = json.loads(expected_output)
        except json.JSONDecodeError:
            parsed_expected = None
    return await svc.upload(version_id, file, document_context, parsed_expected)


@router.post("/{sample_id}/confirm", response_model=Sample)
async def confirm_sample(
    space_id: str,
    version_id: str,
    sample_id: str,
    payload: dict | None = None,
    svc: SampleService = Depends(sample_service),
) -> Sample:
    corrected = (payload or {}).get("corrected_output")
    return svc.confirm(sample_id, corrected)


@router.post("/{sample_id}/reject", response_model=Sample)
def reject_sample(
    space_id: str,
    version_id: str,
    sample_id: str,
    svc: SampleService = Depends(sample_service),
) -> Sample:
    return svc.reject(sample_id)
