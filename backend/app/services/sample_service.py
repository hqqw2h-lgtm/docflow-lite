"""Sample upload, confirm, reject. Samples belong to a draft version."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException, UploadFile

from ..database import UPLOAD_DIR, encode_json, get_session, new_id, utc_now
from ..db.records import SampleRecord
from ..domain import (
    FileType,
    InvocationSource,
    InvocationStatus,
    Sample,
    SampleStatus,
    VersionStatus,
)
from ..repositories import SampleRepo, SchemaSpaceRepo, VersionRepo
from .invocation_service import InvocationService
from .mappers import sample_from_record


class SampleService:
    def __init__(self) -> None:
        self.space_repo = SchemaSpaceRepo()
        self.version_repo = VersionRepo()
        self.sample_repo = SampleRepo()
        self.invocation_service = InvocationService()

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
        file_name = Path(file.filename or "sample").name
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
                raw_types = json.loads(space.input_file_types or "[]")
            except json.JSONDecodeError:
                raw_types = []
            allowed = {FileType(t) for t in raw_types if t in {ft.value for ft in FileType}}

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

        with get_session() as session:
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
            record.correction_notes = encode_json([
                {"stored_path": str(target)},
                {"analysis_state": "queued"},
            ])
            return sample_from_record(record)

    async def analyze_uploaded_sample(self, sample_id: str) -> None:
        with get_session() as session:
            sample = self.sample_repo.get(session, sample_id)
            if sample is None:
                return
            version = self.version_repo.get(session, sample.version_id)
            if version is None:
                sample.status = SampleStatus.NEEDS_REVIEW.value
                sample.correction_notes = encode_json([
                    {"analysis_state": "failed"},
                    {"analysis_error": "version not found"},
                ])
                sample.updated_at = utc_now()
                return

            try:
                notes = json.loads(sample.correction_notes or "[]")
            except json.JSONDecodeError:
                notes = []
            stored_path = ""
            for note in notes:
                if isinstance(note, dict) and "stored_path" in note:
                    stored_path = str(note["stored_path"])
                    break

            if not stored_path:
                sample.status = SampleStatus.NEEDS_REVIEW.value
                sample.correction_notes = encode_json([
                    {"analysis_state": "failed"},
                    {"analysis_error": "stored file path missing"},
                ])
                sample.updated_at = utc_now()
                return

            path = Path(stored_path)
            if not path.exists():
                sample.status = SampleStatus.NEEDS_REVIEW.value
                sample.correction_notes = encode_json([
                    {"analysis_state": "failed"},
                    {"analysis_error": f"stored file not found: {stored_path}"},
                ])
                sample.updated_at = utc_now()
                return

            sample.correction_notes = encode_json([
                {"stored_path": stored_path},
                {"analysis_state": "running"},
            ])
            sample.updated_at = utc_now()
            version_id = sample.version_id
            document_context = sample.document_context
            file_name = sample.file_name

        content = path.read_bytes()
        analysis_upload = UploadFile(
            file=io.BytesIO(content),
            filename=file_name,
            headers=None,
        )

        try:
            invocation = await self.invocation_service.invoke_upload(
                version_id=version_id,
                file=analysis_upload,
                document_context=document_context,
                source=InvocationSource.SAMPLE,
                current_sample_id=sample_id,
            )
            status = (
                SampleStatus.EXTRACTED.value
                if invocation.status == InvocationStatus.COMPLETED
                else SampleStatus.NEEDS_REVIEW.value
            )
            notes = [
                {"stored_path": stored_path},
                {"analysis_state": "done"},
                {"invocation_status": invocation.status.value},
                {"invocation_error": invocation.error_message},
            ]
            model_output = encode_json(invocation.final_output or {})
            invocation_id = invocation.id
        except Exception as exc:  # noqa: BLE001
            status = SampleStatus.NEEDS_REVIEW.value
            notes = [
                {"stored_path": stored_path},
                {"analysis_state": "failed"},
                {"analysis_error": str(exc)},
            ]
            model_output = "{}"
            invocation_id = ""

        with get_session() as session:
            sample = self.sample_repo.get(session, sample_id)
            if sample is None:
                return
            sample.status = status
            sample.model_output = model_output
            sample.invocation_id = invocation_id
            sample.correction_notes = encode_json(notes)
            sample.updated_at = utc_now()

    def confirm(self, sample_id: str, corrected_output: Any | None) -> Sample:
        return self._set_status(sample_id, SampleStatus.CONFIRMED, corrected_output)

    def reject(self, sample_id: str) -> Sample:
        return self._set_status(sample_id, SampleStatus.REJECTED, None)

    def update_expected(self, sample_id: str, expected_output: Any) -> Sample:
        with get_session() as session:
            record = self.sample_repo.get(session, sample_id)
            if record is None:
                raise HTTPException(status_code=404, detail="Sample not found")
            record.expected_output = encode_json(expected_output)
            record.updated_at = utc_now()
            return sample_from_record(record)

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
