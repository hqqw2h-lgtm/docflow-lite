from __future__ import annotations

import re
from typing import Any

SchemaInfo = dict[str, Any] | list[dict[str, Any]]
ValidationIssue = dict[str, Any]
_MISSING = object()

BASE_TYPES = {"string", "number", "boolean", "date"}
COMPLEX_TYPES = {"json", "jsonArray"}


def normalize_schema_info(schema_info: SchemaInfo) -> dict[str, Any]:
    if isinstance(schema_info, dict):
        output_type = schema_info.get("outputType")
        normalized = {
            "outputType": output_type if output_type in {"json", "jsonArray"} else "json",
            "children": _normalize_children(schema_info.get("children", [])),
        }
        return normalized

    children: list[dict[str, Any]] = []
    for group in schema_info:
        group_children = _normalize_children(group.get("children", []))
        if group.get("flag") == "table":
            children.append(
                {
                    "fieldName": group.get("title") or "items",
                    "type": "jsonArray",
                    "isRequired": False,
                    "children": group_children,
                }
            )
        else:
            children.extend(group_children)
    normalized = {"outputType": "json", "children": children}
    return normalized


def field_names(schema_info: SchemaInfo) -> list[str]:
    normalized = normalize_schema_info(schema_info)
    return [
        path
        for path, field in _walk_fields(normalized.get("children", []))
        if field.get("type") not in COMPLEX_TYPES
    ]


def schema_contract(schema_info: SchemaInfo) -> str:
    normalized = normalize_schema_info(schema_info)
    root_kind = "JSON array" if normalized.get("outputType") == "jsonArray" else "JSON object"
    lines = [f"Root output: {root_kind}"]
    for path, field in _walk_fields(normalized.get("children", [])):
        required = "required" if field.get("isRequired") else "optional"
        regex = f", regex: {field.get('regexPattern')}" if field.get("regexPattern") else ""
        constraints = _constraint_text(field.get("constraints", {}))
        constraint_text = f", constraints: {constraints}" if constraints else ""
        lines.append(f"- {path}: {field.get('type', 'string')} ({required}{regex}{constraint_text})")
    return "\n".join(lines)


def validate_output(schema_info: SchemaInfo, output: Any) -> list[ValidationIssue]:
    normalized = normalize_schema_info(schema_info)
    if normalized.get("outputType") == "jsonArray":
        if not isinstance(output, list):
            return [
                _issue(
                    "root_type_mismatch",
                    "$",
                    "Expected root output to be a JSON array.",
                    actual_value=output,
                    expected_type="jsonArray",
                    repair_hint="Return the root value as a JSON array and keep each item aligned with the Expected Output fields.",
                )
            ]
        issues: list[ValidationIssue] = []
        for index, item in enumerate(output):
            issues.extend(_validate_object(normalized.get("children", []), item, f"$[{index}]"))
        return issues
    if not isinstance(output, dict):
        return [
            _issue(
                "root_type_mismatch",
                "$",
                "Expected root output to be a JSON object.",
                actual_value=output,
                expected_type="json",
                repair_hint="Return the root value as a JSON object and keep all keys aligned with the Expected Output fields.",
            )
        ]
    return _validate_object(normalized.get("children", []), output, "$")


def mock_output(schema_info: SchemaInfo) -> dict[str, Any] | list[dict[str, Any]]:
    normalized = normalize_schema_info(schema_info)
    value = _mock_object(normalized.get("children", []))
    if normalized.get("outputType") == "jsonArray":
        return [value]
    return value


def _normalize_children(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [_normalize_field(item) for item in value if isinstance(item, dict)]


def _normalize_field(field: dict[str, Any]) -> dict[str, Any]:
    field_type = field.get("type")
    normalized_type = field_type if field_type in BASE_TYPES | COMPLEX_TYPES else "string"
    normalized: dict[str, Any] = {
        "fieldName": field.get("fieldName") or "field",
        "type": normalized_type,
        "isRequired": bool(field.get("isRequired")),
        "regexPattern": field.get("regexPattern", ""),
        "ignored": bool(field.get("ignored", False)),
        "constraints": field.get("constraints", {}) if isinstance(field.get("constraints"), dict) else {},
    }
    if normalized_type in COMPLEX_TYPES:
        normalized["children"] = _normalize_children(field.get("children", []))
    return normalized


def _walk_fields(fields: list[dict[str, Any]], prefix: str = "") -> list[tuple[str, dict[str, Any]]]:
    walked: list[tuple[str, dict[str, Any]]] = []
    for field in fields:
        if field.get("ignored"):
            continue
        name = str(field.get("fieldName") or "field")
        path = f"{prefix}.{name}" if prefix else name
        walked.append((path, field))
        if field.get("type") in COMPLEX_TYPES:
            walked.extend(_walk_fields(field.get("children", []), path))
    return walked


def _mock_object(fields: list[dict[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field in fields:
        if field.get("ignored"):
            continue
        name = field.get("fieldName") or "field"
        field_type = field.get("type", "string")
        if field_type == "json":
            result[name] = _mock_object(field.get("children", []))
        elif field_type == "jsonArray":
            result[name] = [_mock_object(field.get("children", []))]
        elif field_type == "number":
            result[name] = 0
        elif field_type == "boolean":
            result[name] = False
        else:
            result[name] = ""
    return result


def _validate_object(fields: list[dict[str, Any]], value: Any, prefix: str) -> list[ValidationIssue]:
    if not isinstance(value, dict):
        return [
            _issue(
                "type_mismatch",
                prefix,
                "Expected a JSON object.",
                actual_value=value,
                expected_type="json",
                repair_hint=f"Replace {prefix} with a JSON object that contains the configured child fields.",
            )
        ]
    issues: list[ValidationIssue] = []
    for field in fields:
        if field.get("ignored"):
            continue
        name = str(field.get("fieldName") or "field")
        path = f"{prefix}.{name}"
        field_value = value.get(name)
        if field_value in (None, ""):
            if field.get("isRequired"):
                issues.append(
                    _issue(
                        "required_missing",
                        path,
                        "Required field is missing.",
                        actual_value=field_value,
                        expected_type=str(field.get("type", "string")),
                        rule={"required": True},
                        repair_hint=f"Find the source value for {path} and include this required field in the repaired JSON.",
                    )
                )
            continue
        field_type = field.get("type", "string")
        if field_type == "json":
            issues.extend(_validate_object(field.get("children", []), field_value, path))
            continue
        if field_type == "jsonArray":
            if not isinstance(field_value, list):
                issues.append(
                    _issue(
                        "type_mismatch",
                        path,
                        "Expected a JSON array.",
                        actual_value=field_value,
                        expected_type="jsonArray",
                        repair_hint=f"Return {path} as an array. Preserve table rows as array items when the source contains repeated rows.",
                    )
                )
                continue
            for index, item in enumerate(field_value):
                issues.extend(_validate_object(field.get("children", []), item, f"{path}[{index}]"))
            continue
        issues.extend(_validate_scalar(field, field_value, path))
    return issues


def _validate_scalar(field: dict[str, Any], value: Any, path: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    field_type = field.get("type", "string")
    if field_type == "number" and (not isinstance(value, (int, float)) or isinstance(value, bool)):
        issues.append(
            _issue(
                "type_mismatch",
                path,
                "Expected a number.",
                actual_value=value,
                expected_type="number",
                repair_hint=f"Return {path} as a numeric JSON value without currency symbols or thousands separators.",
            )
        )
    if field_type == "boolean" and not isinstance(value, bool):
        issues.append(
            _issue(
                "type_mismatch",
                path,
                "Expected a boolean.",
                actual_value=value,
                expected_type="boolean",
                repair_hint=f"Return {path} as true or false, not as a quoted string.",
            )
        )
    if field_type in {"string", "date"} and not isinstance(value, str):
        issues.append(
            _issue(
                "type_mismatch",
                path,
                f"Expected a {field_type}.",
                actual_value=value,
                expected_type=field_type,
                repair_hint=f"Return {path} as a JSON string.",
            )
        )

    text = str(value)
    pattern = field.get("regexPattern")
    if pattern and not re.fullmatch(str(pattern), text):
        issues.append(
            _issue(
                "regex_mismatch",
                path,
                f"Value does not match regex: {pattern}",
                actual_value=value,
                expected_type=str(field_type),
                rule={"regexPattern": pattern},
                repair_hint=f"Re-read the source and return a value for {path} that fully matches this regex.",
            )
        )

    constraints = field.get("constraints", {})
    if not isinstance(constraints, dict):
        return issues
    if "minLength" in constraints and len(text) < int(constraints["minLength"]):
        issues.append(
            _issue(
                "min_length",
                path,
                f"Value length must be at least {constraints['minLength']}.",
                actual_value=value,
                expected_type=str(field_type),
                rule={"constraint": "minLength", "expected": constraints["minLength"], "actualLength": len(text)},
                repair_hint=f"Return a longer complete value for {path}; do not truncate the source value.",
            )
        )
    if "maxLength" in constraints and len(text) > int(constraints["maxLength"]):
        issues.append(
            _issue(
                "max_length",
                path,
                f"Value length must be at most {constraints['maxLength']}.",
                actual_value=value,
                expected_type=str(field_type),
                rule={"constraint": "maxLength", "expected": constraints["maxLength"], "actualLength": len(text)},
                repair_hint=f"Return a shorter normalized value for {path} that still preserves the business meaning.",
            )
        )
    if "exactLength" in constraints and len(text) != int(constraints["exactLength"]):
        issues.append(
            _issue(
                "exact_length",
                path,
                f"Value length must be exactly {constraints['exactLength']}.",
                actual_value=value,
                expected_type=str(field_type),
                rule={"constraint": "exactLength", "expected": constraints["exactLength"], "actualLength": len(text)},
                repair_hint=f"Return the exact source identifier for {path} with the configured length.",
            )
        )
    if "pattern" in constraints and not re.fullmatch(str(constraints["pattern"]), text):
        issues.append(
            _issue(
                "constraint_pattern_mismatch",
                path,
                f"Value does not match constraint pattern: {constraints['pattern']}",
                actual_value=value,
                expected_type=str(field_type),
                rule={"constraint": "pattern", "expected": constraints["pattern"]},
                repair_hint=f"Return a value for {path} that fully matches the configured constraint pattern.",
            )
        )
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "min" in constraints and value < float(constraints["min"]):
            issues.append(
                _issue(
                    "min_value",
                    path,
                    f"Value must be greater than or equal to {constraints['min']}.",
                    actual_value=value,
                    expected_type="number",
                    rule={"constraint": "min", "expected": constraints["min"]},
                    repair_hint=f"Re-read the source and return the correct numeric value for {path}; it must be at least {constraints['min']}.",
                )
            )
        if "max" in constraints and value > float(constraints["max"]):
            issues.append(
                _issue(
                    "max_value",
                    path,
                    f"Value must be less than or equal to {constraints['max']}.",
                    actual_value=value,
                    expected_type="number",
                    rule={"constraint": "max", "expected": constraints["max"]},
                    repair_hint=f"Re-read the source and return the correct numeric value for {path}; it must be at most {constraints['max']}.",
                )
            )
    return issues


def _constraint_text(constraints: Any) -> str:
    if not isinstance(constraints, dict) or not constraints:
        return ""
    return ", ".join(f"{key}={value}" for key, value in constraints.items())


def _issue(
    code: str,
    path: str,
    message: str,
    *,
    actual_value: Any = _MISSING,
    expected_type: str = "",
    rule: dict[str, Any] | None = None,
    repair_hint: str = "",
) -> ValidationIssue:
    issue: ValidationIssue = {"code": code, "path": path, "message": message}
    if expected_type:
        issue["expectedType"] = expected_type
    if actual_value is not _MISSING:
        issue["actualType"] = _json_type(actual_value)
        issue["actualValue"] = actual_value
    if rule:
        issue["rule"] = rule
    if repair_hint:
        issue["repairHint"] = repair_hint
    return issue


def _json_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__
