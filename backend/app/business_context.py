from __future__ import annotations

from .models import ModelSettings
from .ollama_client import generate_text_with_model

MAX_BACKGROUND_CHARS = 18_000


async def summarize_background(
    workspace_name: str,
    current_description: str,
    file_name: str,
    normalized_markdown: str,
    settings: ModelSettings,
) -> str:
    prompt = (
        "Summarize the business context for a document extraction workspace.\n"
        "Return a concise business description in 2-4 sentences. "
        "Mention the business scenario, document purpose, key entities, and extraction goal. "
        "Do not mention implementation details.\n\n"
        f"Workspace name: {workspace_name}\n"
        f"Existing description: {current_description or 'N/A'}\n"
        f"Background file: {file_name}\n"
        f"Normalized background Markdown:\n{normalized_markdown[:MAX_BACKGROUND_CHARS]}"
    )
    summary = await generate_text_with_model(prompt, settings)
    return _normalize_summary(summary, workspace_name, normalized_markdown)


def _normalize_summary(summary: str, workspace_name: str, extracted_text: str) -> str:
    cleaned = " ".join(summary.strip().split())
    if cleaned:
        return cleaned[:1000]
    fallback = " ".join(extracted_text.strip().split())[:600]
    if fallback:
        return f"{workspace_name} handles documents related to: {fallback}"
    return f"{workspace_name} handles business document extraction based on uploaded background materials."
