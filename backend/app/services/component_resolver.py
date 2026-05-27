"""Component resolver — the single entry point for selecting any pipeline
component for a given SchemaSpace + Version.

Design principle:
    **Every component selection must take SchemaSpace context as input.**

Resolution precedence (lowest → highest priority):
    1. system default (hardcoded fallback)
    2. SchemaSpace.defaults.* / SchemaSpace.normalizer_overrides
    3. SchemaSpaceVersion.* (non-empty wins)
    4. explicit per-call override (rare, e.g. admin replay)

All resolvers return a fully-materialised value — no further lookup needed
downstream. This keeps :class:`InvocationService` thin: it just asks the
resolver "give me my model" and is never allowed to peek inside the
space/version objects directly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..domain import (
    FileType,
    LLMPayload,
    NormalizedDocument,
    SchemaSpace,
    SchemaSpaceVersion,
)
from ..processing.normalizers import (
    Normalizer,
    build_llm_payload as _build_llm_payload_raw,
    resolve_normalizer,
)
from ..providers import ModelProvider, get_provider, list_providers

# ----- system defaults (last-resort fallback) ----- #
_DEFAULT_MODEL_PROVIDER = "ollama"
_DEFAULT_MODEL_NAME = "llama3.1"
_DEFAULT_SYSTEM_PROMPT = "You extract structured JSON from documents."
_DEFAULT_EXTRACTION_INSTRUCTION = "Return ONLY valid JSON matching the contract."
_DEFAULT_PROCESSING_POLICY: dict[str, Any] = {
    "max_chars": 20000,
    "truncate_marker": "[truncated]",
}


@dataclass(frozen=True)
class EffectiveComponents:
    """Fully resolved pipeline configuration for one (space, version)."""

    schema_space_id: str
    version_id: str
    model_provider: str
    model_name: str
    model_provider_source: str  # "version" | "space" | "system"
    model_name_source: str
    system_prompt: str
    system_prompt_source: str
    extraction_instruction: str
    extraction_instruction_source: str
    processing_policy: dict[str, Any] = field(default_factory=dict)
    processing_policy_source: str = "system"
    normalizer_overrides: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_space_id": self.schema_space_id,
            "version_id": self.version_id,
            "model_provider": {"value": self.model_provider, "source": self.model_provider_source},
            "model_name": {"value": self.model_name, "source": self.model_name_source},
            "system_prompt": {"value": self.system_prompt, "source": self.system_prompt_source},
            "extraction_instruction": {
                "value": self.extraction_instruction,
                "source": self.extraction_instruction_source,
            },
            "processing_policy": {
                "value": self.processing_policy,
                "source": self.processing_policy_source,
            },
            "normalizer_overrides": self.normalizer_overrides,
        }


def _pick(version_value: str, space_value: str, system_default: str) -> tuple[str, str]:
    """Return (value, source) for a string field following resolution order."""
    if version_value:
        return version_value, "version"
    if space_value:
        return space_value, "space"
    return system_default, "system"


def _pick_dict(
    version_value: dict[str, Any] | None,
    space_value: dict[str, Any] | None,
    system_default: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    if version_value:
        return dict(version_value), "version"
    if space_value:
        return dict(space_value), "space"
    return dict(system_default), "system"


def resolve_components(
    space: SchemaSpace,
    version: SchemaSpaceVersion | None,
) -> EffectiveComponents:
    """Compute the effective pipeline configuration.

    ``version`` may be ``None`` (e.g. inspect a SchemaSpace before any version
    exists), in which case only space + system defaults are considered.
    """
    if version is not None and version.schema_space_id != space.id:
        raise ValueError(
            f"Version {version.id} belongs to SchemaSpace {version.schema_space_id}, "
            f"not {space.id}"
        )

    v_provider = version.model_provider if version else ""
    v_model = version.model_name if version else ""
    v_sys = version.system_prompt if version else ""
    v_ext = version.extraction_instruction if version else ""
    v_policy = version.processing_policy if version else None

    provider, provider_src = _pick(v_provider, space.defaults.model_provider, _DEFAULT_MODEL_PROVIDER)
    model, model_src = _pick(v_model, space.defaults.model_name, _DEFAULT_MODEL_NAME)
    system_prompt, sys_src = _pick(v_sys, space.defaults.system_prompt, _DEFAULT_SYSTEM_PROMPT)
    extraction, ext_src = _pick(
        v_ext, space.defaults.extraction_instruction, _DEFAULT_EXTRACTION_INSTRUCTION,
    )
    policy, policy_src = _pick_dict(v_policy, space.defaults.processing_policy, _DEFAULT_PROCESSING_POLICY)

    return EffectiveComponents(
        schema_space_id=space.id,
        version_id=version.id if version else "",
        model_provider=provider,
        model_name=model,
        model_provider_source=provider_src,
        model_name_source=model_src,
        system_prompt=system_prompt,
        system_prompt_source=sys_src,
        extraction_instruction=extraction,
        extraction_instruction_source=ext_src,
        processing_policy=policy,
        processing_policy_source=policy_src,
        normalizer_overrides=dict(space.normalizer_overrides),
    )


# --------------------------------------------------------------------------- #
# Per-component resolvers — all take SchemaSpace context as first argument.
# --------------------------------------------------------------------------- #

def resolve_model_provider(
    space: SchemaSpace,
    version: SchemaSpaceVersion | None,
    *,
    fallback_to_mock_on_unknown: bool = True,
) -> tuple[ModelProvider, str, str]:
    """Return ``(provider_instance, provider_name, model_name)`` for this run.

    When the resolved provider name is not registered and
    ``fallback_to_mock_on_unknown`` is True, falls back to the mock provider so
    a dev with no Ollama still gets a response. Production should set this to
    False to surface the misconfiguration loudly.
    """
    effective = resolve_components(space, version)
    try:
        provider = get_provider(effective.model_provider)
        return provider, effective.model_provider, effective.model_name
    except ValueError:
        if not fallback_to_mock_on_unknown:
            raise
        return get_provider("mock"), "mock", effective.model_name


def resolve_normalizer_for_file(
    space: SchemaSpace,
    version: SchemaSpaceVersion | None,  # reserved for future per-version overrides
    file_type: FileType,
) -> tuple[Normalizer, str]:
    """Return ``(normalizer, override_name_or_empty)`` for this file_type.

    ``override_name_or_empty`` is the SchemaSpace-pinned name (or "" if the
    default was used). Trace spans use this to record routing decisions.
    """
    override = str(space.normalizer_overrides.get(file_type.value, ""))
    return resolve_normalizer(file_type, override), override


def build_llm_payload_for_space(
    space: SchemaSpace,
    version: SchemaSpaceVersion | None,  # reserved for future per-version overrides
    path: Path,
    *,
    file_name: str,
    file_type: FileType,
) -> tuple[LLMPayload, NormalizedDocument | None, str]:
    """SchemaSpace-aware wrapper around :func:`build_llm_payload`.

    Returns ``(payload, normalized_doc_or_none, override_name)``. The override
    name is also surfaced so the InvocationService can record it in the trace.
    """
    override = str(space.normalizer_overrides.get(file_type.value, ""))
    payload, normalized = _build_llm_payload_raw(
        path,
        file_name=file_name,
        file_type=file_type,
        normalizer_override=override,
    )
    return payload, normalized, override


def list_registered_providers() -> list[str]:
    """Pass-through so the API layer doesn't import providers directly."""
    return list_providers()
