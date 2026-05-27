"""Expose the normalizer registry so the UI can populate override dropdowns."""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ..processing.normalizers import list_normalizers

router = APIRouter(prefix="/api/normalizers", tags=["normalizers"])


class NormalizerInfo(BaseModel):
    name: str
    version: str = ""
    supported_types: list[str]
    is_default_for: list[str]


@router.get("", response_model=list[NormalizerInfo])
def list_available_normalizers() -> list[NormalizerInfo]:
    return [NormalizerInfo(**entry) for entry in list_normalizers()]
