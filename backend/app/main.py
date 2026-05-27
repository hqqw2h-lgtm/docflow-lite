"""FastAPI application entrypoint.

Only wiring lives here: app construction, CORS, lifespan, the trivial
health check, and router registration. All business endpoints are in
``app.api.*`` submodules.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .db.records import schema_space as _schema_space_records  # noqa: F401  (register tables)

from .api.schema_spaces import router as schema_spaces_router
from .api.versions import router as versions_router
from .api.samples import router as samples_router
from .api.invocations import router as invocations_router
from .api.admin_traces import router as admin_traces_router
from .api.normalizers import router as normalizers_router
from .api.optimizer import router as optimizer_router
from .api.legacy import router as legacy_router

app = FastAPI(title="DocFlow Lite API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


_ROUTERS = (
    schema_spaces_router,
    versions_router,
    samples_router,
    invocations_router,
    admin_traces_router,
    normalizers_router,
    optimizer_router,
    legacy_router,
)
for _router in _ROUTERS:
    app.include_router(_router)
