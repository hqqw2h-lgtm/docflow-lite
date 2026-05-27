"""Sample upload, confirm, reject, delete. Samples belong to a draft version.

When a sample is uploaded, the extraction pipeline runs automatically so the
user can immediately see the model_output and decide whether to confirm or
correct it.
"""
from __future__ import annotations

import hashlib
import json as _json
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile

from ..database import UPLOAD_DIR, encode_json, get_session, new_id, utc_now
from ..db.records import SampleRecord
from ..domain import (
    FileType,
    InvocationSource,
    Sample,
    SampleStatus,
    VersionStatus,
)
from ..repositories import SampleRepo, SchemaSpaceRepo, VersionRepo
from .mappers import sample_from_record, schema_space_from_record


class SampleService:
    def __init__(self) -> None:
        self.space_repo = SchemaSpaceRepo()
        self.version_repo = VersionRepo()
        self.sample_repo = SampleRepo()

    def list(self, version_id: str) -> list[Sample]:
        with get_session() as session:
            if self.version_repo.get(session, version_id) is None:
                raise HTTPException(status_code=404, detail="Version not found")
            return [sample_from_record(r) for r in self.sample_repo.list_by_version(session, version_id)]

    def get(self, sample_id: str) -> Sample:
        with get_session() as session:
            record = self.sample_repo.get(session, sample_id)
            if record is None:
                raise HTTPException(status_code=404, detail="Sample not found")
            return sample_from_record(record)

    async def upload(
        self,
        version_id: str,
        file: UploadFile,
        document_context: str,
        expected_output: dict | list | None,
    ) -> Sample:
        with get_session() as session:
            version = self.version_repo.get(session, version_id)
            if version is None:
                raise HTTPException(status_code=404, detail="Version not found")
            if version.status != VersionStatus.DRAFT.value:
                raise HTTPException(
                    status_code=409,
                    detail="Samples can only be uploaded to draft versions. Clone the version first.",
                )
            space = self.space_repo.get(session, version.schema_space_id)
            if space is None:
                raise HTTPException(status_code=404, detail="SchemaSpace not found")
            try:
                raw_types = _json.loads(space.input_file_types or "[]")
            except _json.JSONDecodeError:
                raw_types = []
            allowed = {FileType(t) for t in raw_types if t in {ft.value for ft in FileType}}

            file_name = Path(file.filename or "sample").name
            detected = FileType.from_filename(file_name)
            if detected is None:
                raise HTTPException(status_code=400, detail=f"Unsupported file extension for '{file_name}'.")
            if detected not in allowed:
                allowed_str = ", ".join(sorted(t.value for t in allowed)) or "(none configured)"
                raise HTTPException(
                    status_code=400,
                    detail=f"SchemaSpace accepts only: {allowed_str}. Got: {detected.value}",
                )

            content = await file.read()
            sha = hashlib.sha256(content).hexdigest()
            UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            target = UPLOAD_DIR / f"{new_id()}-{file_name}"
            target.write_bytes(content)

            now = utc_now()
            record = SampleRecord(
                id=new_id(),
                version_id=version_id,
                file_name=file_name,
                mime_type=file.content_type or "",
                file_type=detected.value,
                size_bytes=len(content),
                sha256=sha,
                document_context=document_context,
                status=SampleStatus.UPLOADED.value,
                expected_output=encode_json(expected_output) if expected_output is not None else "{}",
                model_output="{}",
                corrected_output="{}",
                correction_notes="[]",
                invocation_id="",
                created_at=now,
                updated_at=now,
            )
            self.sample_repo.add(session, record)
            session.flush()
            record.correction_notes = encode_json([{"stored_path": str(target)}])
            sample_id = record.id
            space_id = version.schema_space_id

        # Run extraction pipeline automatically on upload
        await self._run_extraction(sample_id, space_id, version_id, target, file_name, document_context, content)

        with get_session() as session:
            record = self.sample_repo.get(session, sample_id)
            return sample_from_record(record)  # type: ignore[arg-type]

    async def _run_extraction(
        self,
        sample_id: str,
        space_id: str,
        version_id: str,
        stored_path: Path,
        file_name: str,
        document_context: str,
        content: bytes,
    ) -> None:
        """Run the invocation pipeline and store model_output on the sample."""
        from io import BytesIO
        from ..services.invocation_service import InvocationService

        class _FakeUploadFile:
            """Minimal UploadFile-compatible object for internal pipeline call."""
            def __init__(self, name: str, data: bytes, content_type: str):
                self.filename = name
                self.content_type = content_type
                self._data = data

            async def read(self) -> bytes:
                return self._data

        svc = InvocationService()
        try:
            fake_file = _FakeUploadFile(file_name, content, "application/octet-stream")
            invocation = await svc.invoke_upload(
                version_id=version_id,
                file=fake_file,  # type: ignore[arg-type]
                document_context=document_context,
                source=InvocationSource.SAMPLE,
            )
            # Update sample with model output and invocation link
            with get_session() as session:
                record = self.sample_repo.get(session, sample_id)
                if record is not None:
                    record.model_output = encode_json(invocation.final_output)
                    record.invocation_id = invocation.id
                    if invocation.validation_issues:
                        record.status = SampleStatus.NEEDS_REVIEW.value
                    else:
                        record.status = SampleStatus.EXTRACTED.value
                    record.updated_at = utc_now()
        except Exception:
            # Extraction failure should not block sample upload
            with get_session() as session:
                record = self.sample_repo.get(session, sample_id)
                if record is not None:
                    record.status = SampleStatus.NEEDS_REVIEW.value
                    record.updated_at = utc_now()

    def confirm(self, sample_id: str, corrected_output: Any | None) -> Sample:
        return self._set_status(sample_id, SampleStatus.CONFIRMED, corrected_output)

    def reject(self, sample_id: str) -> Sample:
        return self._set_status(sample_id, SampleStatus.REJECTED, None)

    def delete(self, sample_id: str) -> None:
        """Delete a sample from a draft version."""
        with get_session() as session:
            record = self.sample_repo.get(session, sample_id)
            if record is None:
                raise HTTPException(status_code=404, detail="Sample not found")
            version = self.version_repo.get(session, record.version_id)
            if version is not None and version.status != VersionStatus.DRAFT.value:
                raise HTTPException(status_code=409, detail="Can only delete samples from draft versions.")
            # Remove stored file
            notes = _json.loads(record.correction_notes or "[]")
            for note in notes:
                if isinstance(note, dict) and "stored_path" in note:
                    p = Path(note["stored_path"])
                    if p.exists():
                        p.unlink(missing_ok=True)
            session.delete(record)

    def _set_status(self, sample_id: str, status: SampleStatus, corrected_output: Any | None) -> Sample:
        with get_session() as session:
            record = self.sample_repo.get(session, sample_id)
            if record is None:
                raise HTTPException(status_code=404, detail="Sample not found")
            record.status = status.value
            if corrected_output is not None:
                record.corrected_output = encode_json(corrected_output)
            record.updated_at = utc_now()
            return sample_from_record(record)
