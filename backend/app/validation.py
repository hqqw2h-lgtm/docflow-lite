from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .models import IntegrationConfig, Workspace


@dataclass(frozen=True)
class ActivationContext:
    workspace: Workspace
    config: IntegrationConfig


@dataclass(frozen=True)
class ActivationValidationIssue:
    code: str
    path: str
    message: str


@dataclass(frozen=True)
class ActivationValidationRule:
    code: str
    path: str
    message: str
    is_satisfied: Callable[[ActivationContext], bool]

    def evaluate(self, context: ActivationContext) -> ActivationValidationIssue | None:
        if self.is_satisfied(context):
            return None
        return ActivationValidationIssue(
            code=self.code,
            path=self.path,
            message=self.message,
        )


@dataclass(frozen=True)
class ActivationValidationResult:
    issues: list[ActivationValidationIssue]

    @property
    def valid(self) -> bool:
        return not self.issues

    @property
    def missing_paths(self) -> list[str]:
        return [issue.path for issue in self.issues]

    def to_error_detail(self) -> dict[str, object]:
        return {
            "message": "Integration is incomplete",
            "missing": self.missing_paths,
            "issues": [
                {
                    "code": issue.code,
                    "path": issue.path,
                    "message": issue.message,
                }
                for issue in self.issues
            ],
        }


class IntegrationActivationValidator:
    def __init__(self) -> None:
        self._rules = [
            ActivationValidationRule(
                code="workspace_initialization_inactive",
                path="workspace.initialization_status",
                message="Workspace initialization must be active before integration activation.",
                is_satisfied=lambda context: context.workspace.initialization_status == "active",
            ),
            ActivationValidationRule(
                code="file_entrance_missing_source",
                path="config.file_entrance.source_type",
                message="File Entrance source type is required.",
                is_satisfied=lambda context: bool(context.config.file_entrance.source_type),
            ),
            ActivationValidationRule(
                code="scheduler_missing_start_date",
                path="config.scheduler.start_date",
                message="Scheduled workflows require a start date.",
                is_satisfied=lambda context: (
                    context.config.scheduler.mode == "manual"
                    or bool(context.config.scheduler.start_date)
                ),
            ),
            ActivationValidationRule(
                code="mapping_missing_target_schema",
                path="config.mapping.target_schema",
                message="Mapping target JSON schema is required.",
                is_satisfied=lambda context: bool(context.config.mapping.target_schema),
            ),
            ActivationValidationRule(
                code="destination_missing_name",
                path="config.destination.name",
                message="Destination name is required.",
                is_satisfied=lambda context: bool(context.config.destination.name),
            ),
            ActivationValidationRule(
                code="destination_missing_url",
                path="config.destination.url",
                message="Destination URL is required.",
                is_satisfied=lambda context: bool(context.config.destination.url),
            ),
            ActivationValidationRule(
                code="oauth_missing_client_id",
                path="config.destination.client_id",
                message="OAuth client ID is required when OAuth authentication is selected.",
                is_satisfied=lambda context: (
                    context.config.destination.authentication != "oauth2"
                    or bool(context.config.destination.client_id)
                ),
            ),
            ActivationValidationRule(
                code="oauth_missing_client_secret",
                path="config.destination.client_secret",
                message="OAuth client secret is required when OAuth authentication is selected.",
                is_satisfied=lambda context: (
                    context.config.destination.authentication != "oauth2"
                    or bool(context.config.destination.client_secret)
                ),
            ),
            ActivationValidationRule(
                code="oauth_missing_token_url",
                path="config.destination.token_service_url",
                message="OAuth token service URL is required when OAuth authentication is selected.",
                is_satisfied=lambda context: (
                    context.config.destination.authentication != "oauth2"
                    or bool(context.config.destination.token_service_url)
                ),
            ),
        ]

    def validate(self, context: ActivationContext) -> ActivationValidationResult:
        issues = [
            issue
            for rule in self._rules
            if (issue := rule.evaluate(context)) is not None
        ]
        return ActivationValidationResult(issues=issues)
