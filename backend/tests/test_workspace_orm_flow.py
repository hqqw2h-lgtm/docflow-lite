from __future__ import annotations

import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app import database  # noqa: E402


class WorkspaceOrmFlowTest(TestCase):
    def setUp(self) -> None:
        database.DB_PATH = database.DATA_DIR / "docflow.sqlite3"
        if database._ENGINE is not None:
            database._ENGINE.dispose()
        database._ENGINE = None
        database._ENGINE_PATH = None

    def configure_temp_database(self, temp_dir: str) -> None:
        database.DB_PATH = Path(temp_dir) / "test.db"
        if database._ENGINE is not None:
            database._ENGINE.dispose()
        database._ENGINE = None
        database._ENGINE_PATH = None

    def test_workspace_context_prompt_versions_and_background_files(self) -> None:
        with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            self.configure_temp_database(temp_dir)

            from app.main import app

            with TestClient(app) as client:
                settings_response = client.put(
                    "/api/settings/model",
                    json={"provider": "mock", "base_url": "", "model": "mock-extractor"},
                )
                self.assertEqual(settings_response.status_code, 200, settings_response.text)

                tenant_response = client.post(
                    "/api/tenants",
                    json={"name": "Ops tenant", "description": "Operations"},
                )
                self.assertEqual(tenant_response.status_code, 200, tenant_response.text)

                workspace_response = client.post(
                    "/api/workspaces",
                    json={"tenant_id": tenant_response.json()["id"], "name": "AP invoice flow"},
                )
                self.assertEqual(workspace_response.status_code, 200, workspace_response.text)
                workspace = workspace_response.json()
                self.assertEqual(workspace["description"], "")
                self.assertTrue(workspace["active_schema_version_id"])

                blocked_response = client.post(f"/api/workspaces/{workspace['id']}/analyze")
                self.assertEqual(blocked_response.status_code, 400, blocked_response.text)

                upload_response = client.post(
                    f"/api/workspaces/{workspace['id']}/background-files",
                    files={
                        "file": (
                            "business.txt",
                            b"Supplier invoice approval, vendor, payment term, purchase order matching.",
                            "text/plain",
                        )
                    },
                )
                self.assertEqual(upload_response.status_code, 200, upload_response.text)
                self.assertTrue(upload_response.json()["workspace"]["description"])
                self.assertIn("# business.txt", upload_response.json()["file"]["extracted_text"])
                self.assertIn("```txt", upload_response.json()["file"]["extracted_text"])

                expected_output = {
                    "outputType": "jsonArray",
                    "children": [
                        {
                            "fieldName": "invoice",
                            "type": "json",
                            "isRequired": True,
                            "children": [
                                {"fieldName": "invoiceNo", "type": "string", "isRequired": True},
                                {"fieldName": "amount", "type": "number", "isRequired": False},
                            ],
                        }
                    ],
                }
                schema_response = client.patch(
                    f"/api/workspaces/{workspace['id']}",
                    json={"schema_info": expected_output},
                )
                self.assertEqual(schema_response.status_code, 200, schema_response.text)
                self.assertEqual(schema_response.json()["schema_info"]["outputType"], "jsonArray")

                extraction_response = client.post(
                    f"/api/workspaces/{workspace['id']}/extract",
                    files={"file": ("invoice.txt", b"Invoice INV-1 amount 42", "text/plain")},
                )
                self.assertEqual(extraction_response.status_code, 200, extraction_response.text)
                self.assertIsInstance(extraction_response.json()["extracted_data"], list)
                self.assertTrue(extraction_response.json()["normalized_document_id"])
                self.assertIn("native_markdown", extraction_response.json()["trace"]["normalized_document"]["normalizer"])
                self.assertIn("Invoice INV-1 amount 42", extraction_response.json()["trace"]["normalized_document"]["markdown_preview"])
                confirm_response = client.patch(
                    f"/api/results/{extraction_response.json()['id']}",
                    json={"corrected_data": extraction_response.json()["extracted_data"], "status": "completed"},
                )
                self.assertEqual(confirm_response.status_code, 200, confirm_response.text)

                example_sets = client.get(f"/api/workspaces/{workspace['id']}/example-sets").json()
                self.assertEqual(example_sets[0]["status"], "draft")
                self.assertEqual(len(example_sets[0]["examples"]), 1)

                first_analysis = client.post(
                    f"/api/workspaces/{workspace['id']}/example-sets/{example_sets[0]['id']}/freeze"
                )
                self.assertEqual(first_analysis.status_code, 200, first_analysis.text)

                frozen_sets = client.get(f"/api/workspaces/{workspace['id']}/example-sets").json()
                self.assertEqual(frozen_sets[0]["status"], "frozen")
                upload_to_frozen_response = client.post(
                    f"/api/workspaces/{workspace['id']}/extract",
                    files={"file": ("second.txt", b"Invoice INV-2 amount 99", "text/plain")},
                )
                self.assertEqual(upload_to_frozen_response.status_code, 400, upload_to_frozen_response.text)
                clone_response = client.post(
                    f"/api/workspaces/{workspace['id']}/example-sets/{frozen_sets[0]['id']}/clone"
                )
                self.assertEqual(clone_response.status_code, 200, clone_response.text)
                self.assertEqual(clone_response.json()["status"], "draft")

                profiles = client.get(f"/api/workspaces/{workspace['id']}/prompt-profiles").json()
                self.assertEqual(len(profiles), 1)
                retired_profile = profiles[0]

                activate_response = client.post(
                    f"/api/workspaces/{workspace['id']}/prompt-profiles/{retired_profile['id']}/activate"
                )
                self.assertEqual(activate_response.status_code, 200, activate_response.text)
                self.assertEqual(activate_response.json()["active_prompt_profile_id"], retired_profile["id"])

                background_files = client.get(f"/api/workspaces/{workspace['id']}/background-files").json()
                self.assertEqual(background_files[0]["file_name"], "business.txt")
                self.assertIn("# business.txt", background_files[0]["extracted_text"])

    def test_extract_uses_document_context_and_repair_on_constraint_failure(self) -> None:
        with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            self.configure_temp_database(temp_dir)

            from app import main

            prompts: list[str] = []
            original_generate = main.generate_json_with_model

            async def fake_generate_json_with_model(prompt, schema_info, settings):  # type: ignore[no-untyped-def]
                prompts.append(prompt)
                return {"amount": 0}

            main.generate_json_with_model = fake_generate_json_with_model
            try:
                with TestClient(main.app) as client:
                    settings_response = client.put(
                        "/api/settings/model",
                        json={"provider": "mock", "base_url": "", "model": "mock-extractor"},
                    )
                    self.assertEqual(settings_response.status_code, 200, settings_response.text)

                    tenant_response = client.post(
                        "/api/tenants",
                        json={"name": "Finance tenant", "description": "Finance"},
                    )
                    self.assertEqual(tenant_response.status_code, 200, tenant_response.text)

                    workspace_response = client.post(
                        "/api/workspaces",
                        json={
                            "tenant_id": tenant_response.json()["id"],
                            "name": "Invoice controls",
                            "description": "AP invoices must be validated against business limits.",
                        },
                    )
                    self.assertEqual(workspace_response.status_code, 200, workspace_response.text)
                    workspace = workspace_response.json()

                    schema_response = client.patch(
                        f"/api/workspaces/{workspace['id']}",
                        json={
                            "schema_info": {
                                "outputType": "json",
                                "children": [
                                    {
                                        "fieldName": "amount",
                                        "type": "number",
                                        "isRequired": True,
                                        "constraints": {"min": 100},
                                    }
                                ],
                            }
                        },
                    )
                    self.assertEqual(schema_response.status_code, 200, schema_response.text)

                    extraction_response = client.post(
                        f"/api/workspaces/{workspace['id']}/extract",
                        data={"document_context": "This file uses EUR invoice totals."},
                        files={"file": ("invoice.txt", b"Invoice total is 42 EUR", "text/plain")},
                    )
                    self.assertEqual(extraction_response.status_code, 200, extraction_response.text)
                    payload = extraction_response.json()
                    self.assertEqual(payload["status"], "correction_required")
                    self.assertGreaterEqual(len(prompts), 2)
                    self.assertIn("Document-specific context", prompts[0])
                    self.assertIn("Normalized Markdown chunks", prompts[0])
                    self.assertIn("This file uses EUR invoice totals.", prompts[0])
                    self.assertIn("Validation errors", prompts[1])
                    self.assertIn("actualValue", prompts[1])
                    self.assertIn("repairHint", prompts[1])
                    self.assertEqual(payload["trace"]["merge_issues"][0]["code"], "min_value")
                    self.assertEqual(payload["trace"]["merge_issues"][0]["actualValue"], 0)
                    self.assertEqual(payload["trace"]["merge_issues"][0]["rule"]["constraint"], "min")
                    self.assertIn("repairHint", payload["trace"]["merge_issues"][0])
            finally:
                main.generate_json_with_model = original_generate

    def test_field_rule_suggestion_uses_model_contract(self) -> None:
        with TemporaryDirectory(ignore_cleanup_errors=True) as temp_dir:
            self.configure_temp_database(temp_dir)

            from app import main

            calls: list[tuple[str, dict]] = []
            original_generate = main.generate_json_with_model

            async def fake_generate_json_with_model(prompt, schema_info, settings):  # type: ignore[no-untyped-def]
                calls.append((prompt, schema_info))
                return {
                    "regexPattern": r"^[A-Z0-9]{10}$",
                    "constraints": {"exactLength": 10},
                    "explanation": "Use a 10-character uppercase letter or digit code.",
                }

            main.generate_json_with_model = fake_generate_json_with_model
            try:
                with TestClient(main.app) as client:
                    settings_response = client.put(
                        "/api/settings/model",
                        json={"provider": "ollama", "base_url": "http://localhost:11434", "model": "local-rule-model"},
                    )
                    self.assertEqual(settings_response.status_code, 200, settings_response.text)

                    response = client.post(
                        "/api/field-rule-suggestions",
                        json={"description": "料号是10位，只能大写字母或数字", "field_type": "string"},
                    )
                    self.assertEqual(response.status_code, 200, response.text)
                    payload = response.json()
                    self.assertEqual(payload["regexPattern"], r"^[A-Z0-9]{10}$")
                    self.assertEqual(payload["constraints"], {"exactLength": 10})
                    self.assertEqual(len(calls), 1)
                    self.assertIn("Supported constraints object keys", calls[0][0])
                    self.assertIn("User rule description: 料号是10位，只能大写字母或数字", calls[0][0])
                    self.assertEqual(calls[0][1]["children"][1]["fieldName"], "constraints")
            finally:
                main.generate_json_with_model = original_generate
