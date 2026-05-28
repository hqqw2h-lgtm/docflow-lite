from __future__ import annotations

import json

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from ..domain import Sample
from ..services import SampleService
from .deps import sample_service

router = APIRouter(prefix="/api/schema-spaces/{space_id}/versions/{version_id}/samples", tags=["samples"])


class UpdateExpectedPayload(BaseModel):
    expected_output_text: str | None = None
    expected_output: dict | list | None = None


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
    background_tasks: BackgroundTasks,
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
    sample = await svc.upload(version_id, file, document_context, parsed_expected)
    background_tasks.add_task(svc.analyze_uploaded_sample, sample.id)
    return sample


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


@router.post("/{sample_id}/expected", response_model=Sample)
def update_sample_expected(
    space_id: str,
    version_id: str,
    sample_id: str,
    payload: UpdateExpectedPayload,
    svc: SampleService = Depends(sample_service),
) -> Sample:
    sample = svc.get(sample_id)
    if sample.version_id != version_id:
        raise HTTPException(status_code=400, detail="Sample/version mismatch")
    if payload.expected_output_text is not None:
        text = payload.expected_output_text.strip()
        if not text:
            expected = {}
        else:
            try:
                expected = json.loads(text)
            except json.JSONDecodeError as exc:
                raise HTTPException(status_code=400, detail=f"Invalid expected JSON: {exc.msg}") from exc
    else:
        expected = payload.expected_output or {}
    return svc.update_expected(sample_id, expected)


@router.post("/{sample_id}/analyze", response_model=Sample)
async def analyze_sample(
    space_id: str,
    version_id: str,
    sample_id: str,
    background_tasks: BackgroundTasks,
    svc: SampleService = Depends(sample_service),
) -> Sample:
    sample = svc.get(sample_id)
    if sample.version_id != version_id:
        raise HTTPException(status_code=400, detail="Sample/version mismatch")
    background_tasks.add_task(svc.analyze_uploaded_sample, sample_id)
    return sample
