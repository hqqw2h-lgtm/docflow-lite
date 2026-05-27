# DocFlow Lite

DocFlow Lite is a personal document-processing workspace app.

It provides workspace management, schema setup, file upload, extraction with a selectable AI model, and lightweight integration workflows.

## Stack

- Frontend: React + TypeScript + Vite
- Backend: Python + FastAPI + SQLite
- Default model provider: local Ollama

## Design first

The project documentation is under `docs/`:

- `01-requirements.md` - product scope and functional requirements
- `02-module-design.md` - module boundaries and domain objects
- `03-implementation-plan.md` - phased delivery plan

## Quick start

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

## Ollama

Start Ollama locally and pull a model, for example:

```bash
ollama pull llama3.1
ollama serve
```

The app defaults to `llama3.1`, but the model can be changed from the Settings page.
