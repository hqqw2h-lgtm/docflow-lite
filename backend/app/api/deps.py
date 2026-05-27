"""Shared API dependencies / singletons."""
from __future__ import annotations

from ..services import (
    InvocationService,
    OptimizerService,
    SampleService,
    SchemaSpaceService,
    VersionLifecycleService,
)

_schema_space_service = SchemaSpaceService()
_version_service = VersionLifecycleService()
_sample_service = SampleService()
_invocation_service = InvocationService()
_optimizer_service = OptimizerService()


def schema_space_service() -> SchemaSpaceService:
    return _schema_space_service


def version_service() -> VersionLifecycleService:
    return _version_service


def sample_service() -> SampleService:
    return _sample_service


def invocation_service() -> InvocationService:
    return _invocation_service


def optimizer_service() -> OptimizerService:
    return _optimizer_service
