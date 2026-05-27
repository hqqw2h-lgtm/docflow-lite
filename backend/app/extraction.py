from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile
from pypdf import PdfReader

from .database import UPLOAD_DIR, new_id


async def save_upload(file: UploadFile) -> Path:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = Path(file.filename or "document").name
    target = UPLOAD_DIR / f"{new_id()}-{safe_name}"
    content = await file.read()
    target.write_bytes(content)
    return target


def read_document_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    if suffix in {".txt", ".md", ".json", ".csv", ".xml", ".html"}:
        return path.read_text(encoding="utf-8", errors="ignore")
    return path.read_bytes()[:20000].decode("utf-8", errors="ignore")

