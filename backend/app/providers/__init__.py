"""ModelProvider abstraction. Business code must not import httpx/ollama directly."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class ModelInvocation:
    provider: str
    model: str
    raw_response: str
    parsed_json: Any
    duration_ms: int
    error: str = ""


class ModelProvider(ABC):
    name: str = ""

    @abstractmethod
    async def generate_json(self, prompt: str, model: str, options: dict[str, Any] | None = None) -> ModelInvocation: ...

    @abstractmethod
    async def generate_text(self, prompt: str, model: str, options: dict[str, Any] | None = None) -> ModelInvocation: ...

    @abstractmethod
    async def list_models(self) -> list[str]: ...


class OllamaProvider(ModelProvider):
    name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434") -> None:
        self.base_url = base_url.rstrip("/")

    async def generate_json(self, prompt: str, model: str, options: dict[str, Any] | None = None) -> ModelInvocation:
        import time
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={"model": model, "prompt": prompt, "stream": False, "format": "json", **(options or {})},
                )
                response.raise_for_status()
                payload = response.json()
                content = payload.get("response", "{}")
                parsed = json.loads(content)
                return ModelInvocation(self.name, model, content, parsed, int((time.perf_counter() - start) * 1000))
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            return ModelInvocation(self.name, model, "", None, int((time.perf_counter() - start) * 1000), error=str(exc))

    async def generate_text(self, prompt: str, model: str, options: dict[str, Any] | None = None) -> ModelInvocation:
        import time
        start = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={"model": model, "prompt": prompt, "stream": False, **(options or {})},
                )
                response.raise_for_status()
                payload = response.json()
                return ModelInvocation(self.name, model, str(payload.get("response", "")).strip(), None, int((time.perf_counter() - start) * 1000))
        except httpx.HTTPError as exc:
            return ModelInvocation(self.name, model, "", None, int((time.perf_counter() - start) * 1000), error=str(exc))

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
                return [item["name"] for item in response.json().get("models", [])]
        except httpx.HTTPError:
            return []


class MockProvider(ModelProvider):
    name = "mock"

    async def generate_json(self, prompt: str, model: str, options: dict[str, Any] | None = None) -> ModelInvocation:
        return ModelInvocation(self.name, model, "{}", {"_mock": True, "prompt_preview": prompt[:200]}, 1)

    async def generate_text(self, prompt: str, model: str, options: dict[str, Any] | None = None) -> ModelInvocation:
        return ModelInvocation(self.name, model, "mock summary", None, 1)

    async def list_models(self) -> list[str]:
        return ["mock-extractor"]


_REGISTRY: dict[str, ModelProvider] = {
    "ollama": OllamaProvider(),
    "mock": MockProvider(),
}


def list_providers() -> list[str]:
    return sorted(_REGISTRY.keys())


def get_provider(name: str) -> ModelProvider:
    if name not in _REGISTRY:
        raise ValueError(f"Unknown model provider: {name}. Available: {list(_REGISTRY)}")
    return _REGISTRY[name]


def register_provider(name: str, provider: ModelProvider) -> None:
    _REGISTRY[name] = provider


def configure_ollama_base_url(base_url: str) -> None:
    _REGISTRY["ollama"] = OllamaProvider(base_url=base_url)
