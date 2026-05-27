"""Output similarity scoring for the optimizer.

The optimizer needs a single scalar (0.0–1.0) to rank pipeline configurations
against a confirmed sample's expected_output. We use a field-level recursive
match: dicts score per-key, lists score per-index plus length penalty, scalars
score exact-match. JSON-comparable values only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FieldDiff:
    path: str
    expected: Any
    actual: Any
    matched: bool


@dataclass
class ScoreResult:
    score: float                       # 0.0 – 1.0
    matched_fields: int = 0
    total_fields: int = 0
    diffs: list[FieldDiff] = field(default_factory=list)

    @property
    def is_perfect(self) -> bool:
        return self.score >= 0.9999


def _score(expected: Any, actual: Any, *, path: str, diffs: list[FieldDiff]) -> tuple[int, int]:
    """Return ``(matched_leaf_count, total_leaf_count)`` for one value pair."""
    if isinstance(expected, dict):
        # Treat missing actual as empty dict so every expected key counts as a miss.
        actual_dict = actual if isinstance(actual, dict) else {}
        if not expected:
            # Expected an empty object — give full credit only if actual is also empty.
            ok = isinstance(actual, dict) and not actual
            diffs.append(FieldDiff(path=path or "$", expected=expected, actual=actual, matched=ok))
            return (1 if ok else 0), 1
        matched = total = 0
        for k in expected:
            m, t = _score(expected[k], actual_dict.get(k), path=f"{path}.{k}" if path else k, diffs=diffs)
            matched += m
            total += t
        return matched, total

    if isinstance(expected, list):
        actual_list = actual if isinstance(actual, list) else []
        if not expected:
            ok = isinstance(actual, list) and not actual
            diffs.append(FieldDiff(path=path or "$", expected=expected, actual=actual, matched=ok))
            return (1 if ok else 0), 1
        max_len = max(len(expected), len(actual_list))
        matched = total = 0
        for i in range(max_len):
            e = expected[i] if i < len(expected) else None
            a = actual_list[i] if i < len(actual_list) else None
            m, t = _score(e, a, path=f"{path}[{i}]", diffs=diffs)
            matched += m
            total += t
        return matched, total

    # scalar (or None)
    ok = expected == actual
    diffs.append(FieldDiff(path=path or "$", expected=expected, actual=actual, matched=ok))
    return (1 if ok else 0), 1


def score_outputs(expected: Any, actual: Any) -> ScoreResult:
    """Compare ``actual`` against ``expected`` and return a normalized score."""
    diffs: list[FieldDiff] = []
    if expected is None:
        # No ground truth — cannot score; treat as neutral 0.
        return ScoreResult(score=0.0, matched_fields=0, total_fields=0, diffs=diffs)
    matched, total = _score(expected, actual, path="", diffs=diffs)
    score = (matched / total) if total else 0.0
    return ScoreResult(score=score, matched_fields=matched, total_fields=total, diffs=diffs)
