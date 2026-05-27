"""Centralized enums shared across domain modules.

All status / source / mode strings used by the new SchemaSpace world live here.
This replaces the Literal sprinkled across legacy models.py.
"""
from __future__ import annotations

from enum import Enum


class SchemaSpaceStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class FileType(str, Enum):
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    TEXT = "text"
    JSON = "json"
    IMAGE = "image"
    MARKDOWN = "markdown"

    @classmethod
    def from_filename(cls, file_name: str) -> "FileType | None":
        suffix = file_name.lower().rsplit(".", 1)[-1] if "." in file_name else ""
        mapping = {
            "pdf": cls.PDF,
            "xlsx": cls.EXCEL, "xls": cls.EXCEL, "xlsm": cls.EXCEL,
            "csv": cls.CSV,
            "txt": cls.TEXT, "log": cls.TEXT,
            "json": cls.JSON,
            "png": cls.IMAGE, "jpg": cls.IMAGE, "jpeg": cls.IMAGE, "tif": cls.IMAGE, "tiff": cls.IMAGE,
            "md": cls.MARKDOWN, "markdown": cls.MARKDOWN,
        }
        return mapping.get(suffix)


class VersionStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class InvocationSource(str, Enum):
    UI = "ui"
    API_SYNC = "api_sync"
    API_ASYNC = "api_async"
    SAMPLE = "sample"
    REPLAY = "replay"


class InvocationStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    NEEDS_REVIEW = "needs_review"
    FAILED = "failed"


class SampleStatus(str, Enum):
    UPLOADED = "uploaded"
    EXTRACTED = "extracted"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


class TraceSpanType(str, Enum):
    PREFLIGHT = "preflight"
    NORMALIZE = "normalize"
    CHUNK = "chunk"
    CONTEXT_ASSEMBLY = "context_assembly"
    MODEL_CALL = "model_call"
    VALIDATE = "validate"
    REPAIR = "repair"
    MERGE = "merge"
    PERSIST = "persist"
