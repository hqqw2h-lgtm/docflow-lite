# AGENTS.md

## Cursor Cloud specific instructions

### Architecture overview

DocFlow Lite is a document-processing workspace app with two layers:
- **Backend**: Python FastAPI + SQLAlchemy ORM + SQLite at `backend/`
- **Frontend**: React 19 + TypeScript + Vite + Ant Design at `frontend/`

The active frontend is in `frontend/src/v2/` (hash-router based SchemaSpace UI). Legacy code exists in `frontend/src/App.tsx` and `frontend/src/features/` but is not wired.

### Running services

- **Backend**: `cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000`
- **Frontend**: `cd frontend && npm run dev` (Vite on port 5173, proxies `/api` to backend)
- **Database**: SQLite at `data/docflow.sqlite3` (auto-created on startup)
- **Model provider**: Defaults to Ollama (localhost:11434). For testing without Ollama, set the SchemaSpace defaults or version model_provider to `"mock"`.

### Testing

- Backend tests: `cd backend && source .venv/bin/activate && python -m pytest tests/ -v`
- Frontend type-check: `cd frontend && npx tsc -b`
- Frontend build: `cd frontend && npx vite build`
- No ESLint or other linters are configured.

### Key gotchas

1. The `python3.12-venv` package must be installed (`sudo apt-get install python3.12-venv`) before creating the backend venv.
2. Two of the three existing backend tests fail due to referencing a non-existent `main.generate_json_with_model` attribute — this is a pre-existing issue.
3. The SchemaSpace component resolver follows precedence: version → space.defaults → system defaults. When testing, set model_provider on the **space defaults** (not just the version) to ensure the mock provider is used.
4. Sample upload automatically triggers the extraction pipeline. If Ollama isn't running, sample extraction will fail but the sample itself is still saved.
5. File uploads are stored in `uploads/` directory (auto-created). Admin replay uses SHA256 matching to find stored files.
