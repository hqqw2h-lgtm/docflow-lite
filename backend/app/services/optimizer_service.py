"""Optimizer: automatically find the best pipeline configuration for a version.

Goal
----
Before a version is published, the user provides several confirmed samples
(file + expected_output). The optimizer runs every legal combination of
pluggable components (currently: per-file-type normalizer) through every
sample, scores each model output against the expected output, and ranks the
combinations. The winning combination is persisted into
``SchemaSpace.normalizer_overrides`` so that subsequent invocations on the
published version use it automatically — no user picking required.

Why only normalizers right now?
-------------------------------
Model provider / model name are typically a tenant- or space-level policy
(cost, governance), not a per-version tuning knob. System prompt and
extraction instruction are part of the version's design intent. Normalizer
choice is the one component where the "best" answer is genuinely
data-dependent (e.g. for some PDFs marker-pdf wins, for others pypdf is
faster and just as accurate). So we automate that, leaving the others as
declarative SchemaSpace defaults.

The search is intentionally exhaustive — small candidate set, small sample
set, so combinatorial blow-up is not a concern in practice.
"""
from __future__ import annotations

import itertools
import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from ..database import encode_json, get_session, utc_now
from ..domain import FileType, SchemaSpace, SchemaSpaceVersion, VersionStatus
from ..processing.normalizers import (
    build_llm_payload,
    list_normalizers_for_file_type,
)
from ..repositories import SampleRepo, SchemaSpaceRepo, VersionRepo
from ..schema_utils import schema_contract
from .component_resolver import resolve_components, resolve_model_provider
from .mappers import schema_space_from_record, version_from_record
from .scoring import ScoreResult, score_outputs


# --------------------------------------------------------------------------- #
# Public dataclasses (returned by API)
# --------------------------------------------------------------------------- #


@dataclass
class SampleTrialOutcome:
    sample_id: str
    file_name: str
    file_type: str
    score: float
    matched_fields: int
    total_fields: int
    error: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "file_name": self.file_name,
            "file_type": self.file_type,
            "score": round(self.score, 4),
            "matched_fields": self.matched_fields,
            "total_fields": self.total_fields,
            "error": self.error,
        }


@dataclass
class CombinationTrial:
    """One pipeline configuration evaluated against the sample set."""

    normalizer_overrides: dict[str, str]
    avg_score: float
    sample_outcomes: list[SampleTrialOutcome]
    error_count: int
    duration_ms: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "normalizer_overrides": self.normalizer_overrides,
            "avg_score": round(self.avg_score, 4),
            "error_count": self.error_count,
            "duration_ms": self.duration_ms,
            "sample_outcomes": [s.as_dict() for s in self.sample_outcomes],
        }


@dataclass
class OptimizationReport:
    schema_space_id: str
    version_id: str
    sample_count: int
    candidate_count: int
    trials: list[CombinationTrial]
    best: CombinationTrial | None
    applied: bool
    duration_ms: int
    started_at: str
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_space_id": self.schema_space_id,
            "version_id": self.version_id,
            "sample_count": self.sample_count,
            "candidate_count": self.candidate_count,
            "best": self.best.as_dict() if self.best else None,
            "applied": self.applied,
            "duration_ms": self.duration_ms,
            "started_at": self.started_at,
            "notes": self.notes,
            "trials": [t.as_dict() for t in self.trials],
        }


# --------------------------------------------------------------------------- #
# Service
# --------------------------------------------------------------------------- #


class OptimizerService:
    def __init__(self) -> None:
        self.space_repo = SchemaSpaceRepo()
        self.version_repo = VersionRepo()
        self.sample_repo = SampleRepo()

    async def optimize(
        self,
        version_id: str,
        *,
        apply_best: bool = True,
    ) -> OptimizationReport:
        """Run the full grid search and (optionally) persist the best combination."""
        started_perf = time.perf_counter()
        started_at = utc_now()

        with get_session() as session:
            v_rec = self.version_repo.get(session, version_id)
            if v_rec is None:
                raise HTTPException(status_code=404, detail="Version not found")
            if v_rec.status == VersionStatus.ARCHIVED.value:
                raise HTTPException(status_code=409, detail="Cannot optimize an archived version")
            s_rec = self.space_repo.get(session, v_rec.schema_space_id)
            if s_rec is None:
                raise HTTPException(status_code=404, detail="SchemaSpace not found")

            space = schema_space_from_record(s_rec)
            version = version_from_record(v_rec)

            sample_records = self.sample_repo.list_by_version(session, version_id)
            usable_samples = []
            notes: list[str] = []
            for sr in sample_records:
                try:
                    expected = json.loads(sr.expected_output or "{}")
                except json.JSONDecodeError:
                    notes.append(f"sample {sr.id}: expected_output is not valid JSON, skipped")
                    continue
                if not expected:
                    notes.append(f"sample {sr.id}: no expected_output, skipped")
                    continue
                stored_path = _extract_stored_path(sr.correction_notes)
                if not stored_path:
                    notes.append(f"sample {sr.id}: stored file path missing, skipped")
                    continue
                if not stored_path.exists():
                    notes.append(f"sample {sr.id}: stored file no longer on disk ({stored_path}), skipped")
                    continue
                try:
                    file_type = FileType(sr.file_type)
                except ValueError:
                    notes.append(f"sample {sr.id}: unknown file_type '{sr.file_type}', skipped")
                    continue
                usable_samples.append((sr, file_type, stored_path, expected))

            if not usable_samples:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Optimizer needs at least one confirmed sample with an expected_output. "
                        f"Diagnostics: {notes}"
                    ),
                )

            # File-types actually exercised by the sample set.
            sample_file_types = sorted({ft.value for _, ft, _, _ in usable_samples})

            # Build per-file-type candidate lists. We only enumerate over
            # file_types that actually appear in samples — combinations for
            # other types would not change any sample's outcome.
            candidates_by_type: dict[str, list[str]] = {}
            for ft_val in sample_file_types:
                ft = FileType(ft_val)
                names = list_normalizers_for_file_type(ft)
                # "" sentinel means "use registry default" (which == no override).
                # We include "" first so the trial with no overrides is always run.
                candidates_by_type[ft_val] = [""] + [n for n in names]

            combos = _cartesian(candidates_by_type)
            # De-duplicate logically equivalent override maps.
            seen: set[str] = set()
            unique_combos: list[dict[str, str]] = []
            for combo in combos:
                trimmed = {k: v for k, v in combo.items() if v}
                key = json.dumps(trimmed, sort_keys=True)
                if key in seen:
                    continue
                seen.add(key)
                unique_combos.append(trimmed)

            # Build effective prompt config once — model & prompts don't change
            # across trials (we're only varying the normalizer).
            effective = resolve_components(space, version)
            schema_info = version.schema_info or {"outputType": "json", "children": []}
            contract = schema_contract(schema_info)
            provider, provider_name, model_name = resolve_model_provider(space, version)

            trials: list[CombinationTrial] = []
            for combo_overrides in unique_combos:
                t_start = time.perf_counter()
                outcomes: list[SampleTrialOutcome] = []
                errors = 0
                for sr, file_type, stored_path, expected in usable_samples:
                    override_for_this_file = combo_overrides.get(file_type.value, "")
                    try:
                        parsed, err = await _run_single_trial(
                            stored_path=stored_path,
                            file_name=sr.file_name,
                            file_type=file_type,
                            normalizer_override=override_for_this_file,
                            effective=effective,
                            contract=contract,
                            document_context=sr.document_context,
                            provider=provider,
                            model_name=model_name,
                        )
                    except Exception as exc:  # noqa: BLE001
                        outcomes.append(SampleTrialOutcome(
                            sample_id=sr.id,
                            file_name=sr.file_name,
                            file_type=file_type.value,
                            score=0.0,
                            matched_fields=0,
                            total_fields=0,
                            error=f"pipeline exception: {exc}",
                        ))
                        errors += 1
                        continue

                    if err or parsed is None:
                        outcomes.append(SampleTrialOutcome(
                            sample_id=sr.id,
                            file_name=sr.file_name,
                            file_type=file_type.value,
                            score=0.0,
                            matched_fields=0,
                            total_fields=0,
                            error=err or "model returned no parseable JSON",
                        ))
                        errors += 1
                        continue

                    score: ScoreResult = score_outputs(expected, parsed)
                    outcomes.append(SampleTrialOutcome(
                        sample_id=sr.id,
                        file_name=sr.file_name,
                        file_type=file_type.value,
                        score=score.score,
                        matched_fields=score.matched_fields,
                        total_fields=score.total_fields,
                    ))

                avg = sum(o.score for o in outcomes) / max(len(outcomes), 1)
                trials.append(CombinationTrial(
                    normalizer_overrides=combo_overrides,
                    avg_score=avg,
                    sample_outcomes=outcomes,
                    error_count=errors,
                    duration_ms=int((time.perf_counter() - t_start) * 1000),
                ))

            # Pick best: highest avg_score, then fewest errors, then fewest
            # overrides (prefer simplest config on ties).
            trials.sort(key=lambda t: (-t.avg_score, t.error_count, len(t.normalizer_overrides)))
            best = trials[0] if trials else None

            applied = False
            if apply_best and best is not None and best.avg_score > 0:
                s_rec.normalizer_overrides = encode_json(best.normalizer_overrides)
                s_rec.updated_at = utc_now()
                applied = True

            report = OptimizationReport(
                schema_space_id=space.id,
                version_id=version.id,
                sample_count=len(usable_samples),
                candidate_count=len(trials),
                trials=trials,
                best=best,
                applied=applied,
                duration_ms=int((time.perf_counter() - started_perf) * 1000),
                started_at=started_at,
                notes=notes,
            )

            # Persist the latest report on the version for replay / audit.
            v_rec.last_optimization = encode_json(report.as_dict())
            v_rec.updated_at = utc_now()

            return report


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _extract_stored_path(correction_notes_json: str) -> Path | None:
    try:
        notes = json.loads(correction_notes_json or "[]")
    except json.JSONDecodeError:
        return None
    for entry in notes:
        if isinstance(entry, dict) and "stored_path" in entry:
            return Path(str(entry["stored_path"]))
    return None


def _cartesian(by_type: dict[str, list[str]]) -> list[dict[str, str]]:
    if not by_type:
        return [{}]
    keys = list(by_type.keys())
    out: list[dict[str, str]] = []
    for combo in itertools.product(*(by_type[k] for k in keys)):
        out.append({k: v for k, v in zip(keys, combo)})
    return out


async def _run_single_trial(
    *,
    stored_path: Path,
    file_name: str,
    file_type: FileType,
    normalizer_override: str,
    effective,
    contract: str,
    document_context: str,
    provider,
    model_name: str,
) -> tuple[Any, str]:
    """Run the pipeline core (normalize → prompt → model) without DB writes."""
    try:
        payload, _normalized = build_llm_payload(
            stored_path,
            file_name=file_name,
            file_type=file_type,
            normalizer_override=normalizer_override,
        )
    except Exception as exc:  # noqa: BLE001
        return None, f"normalize_failed: {exc}"

    body = payload.text
    max_chars = int(effective.processing_policy.get("max_chars", 20000) or 20000)
    truncate_marker = str(effective.processing_policy.get("truncate_marker", "[truncated]"))
    if len(body) > max_chars:
        body = body[:max_chars] + f"\n\n{truncate_marker}"

    if payload.images and not body:
        document_section = (
            f"## Document\n[{len(payload.images)} image(s) attached — file_type={file_type.value}]\n"
        )
    else:
        document_section = f"## Document ({file_type.value})\n{body}\n"

    prompt = (
        f"{effective.system_prompt}\n\n"
        f"## Output Contract\n{contract}\n\n"
        f"## Extraction Instruction\n{effective.extraction_instruction}\n\n"
        f"## User Context\n{document_context or '(none)'}\n\n"
        f"{document_section}"
    )
    result = await provider.generate_json(prompt, model_name)
    return result.parsed_json, result.error or ""
