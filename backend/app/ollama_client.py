from __future__ import annotations

import json
from typing import Any

import httpx

from .models import ModelSettings
from .schema_utils import SchemaInfo, mock_output, schema_contract


async def list_ollama_models(settings: ModelSettings) -> list[str]:
    if settings.provider == "mock":
        return ["mock-extractor"]
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{settings.base_url.rstrip('/')}/api/tags")
            response.raise_for_status()
            data = response.json()
            return [item["name"] for item in data.get("models", [])]
    except httpx.HTTPError:
        return []


async def extract_with_model(
    text: str,
    schema_info: SchemaInfo,
    settings: ModelSettings,
) -> dict[str, Any]:
    return await generate_json_with_model(build_prompt(text, schema_info), schema_info, settings)


async def generate_json_with_model(
    prompt: str,
    schema_info: SchemaInfo,
    settings: ModelSettings,
) -> dict[str, Any] | list[dict[str, Any]]:
    if settings.provider == "mock":
        return mock_extract(prompt, schema_info)

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{settings.base_url.rstrip('/')}/api/generate",
                json={
                    "model": settings.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
            )
            response.raise_for_status()
            payload = response.json()
            content = payload.get("response", "{}")
            return json.loads(content)
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"model_extraction_failed: {exc}") from exc


async def generate_text_with_model(prompt: str, settings: ModelSettings) -> str:
    if settings.provider == "mock":
        return mock_summarize(prompt)

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{settings.base_url.rstrip('/')}/api/generate",
                json={
                    "model": settings.model,
                    "prompt": prompt,
                    "stream": False,
                },
            )
            response.raise_for_status()
            payload = response.json()
            return str(payload.get("response", "")).strip()
    except httpx.HTTPError as exc:
        raise RuntimeError(f"model_text_generation_failed: {exc}") from exc


def build_prompt(text: str, schema_info: SchemaInfo) -> str:
    return (
        "Extract structured data from the document text.\n"
        "Return JSON only. Use the provided expected output structure and field names.\n\n"
        f"Expected output structure:\n{schema_contract(schema_info)}\n\n"
        f"Document text:\n{text}"
    )


def mock_extract(text: str, schema_info: SchemaInfo) -> dict[str, Any] | list[dict[str, Any]]:
    output = mock_output(schema_info)
    if isinstance(output, list):
        if output:
            output[0]["summary"] = text[:500]
        return output
    output["summary"] = text[:500]
    return output


def mock_summarize(prompt: str) -> str:
    marker = "Normalized background Markdown:"
    text = prompt.split(marker, 1)[-1] if marker in prompt else prompt
    compact = " ".join(text.strip().split())
    return (
        "This workspace processes business documents using uploaded background materials. "
        f"Key context: {compact[:500]}"
    )
