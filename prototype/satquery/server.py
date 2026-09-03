"""FastAPI app — binds 0.0.0.0 so the Arena preview / venue laptop can reach it.

Endpoints:
  GET  /health
  GET  /tools            -> registry contents (PS A2.2)
  POST /query            -> {query, image_paths?, scene_id?} -> SatQueryResponse
  GET  /trace/{query_id} -> persisted trace JSON
  GET  /traces           -> recent runs

Run: uvicorn satquery.server:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

from pathlib import Path

from .orchestrator import Orchestrator
from .registry import tools_summary

try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    _FASTAPI = True
except ImportError:  # server extras not installed
    _FASTAPI = False

if _FASTAPI:

    class QueryRequest(BaseModel):
        query: str
        image_paths: list[str] | None = None
        scene_id: str | None = None
        params: dict | None = None

    app = FastAPI(title="SatQuery AI — Window A prototype", version="0.1.0")
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
        allow_headers=["*"],
    )
    orch = Orchestrator()

    @app.get("/health")
    def health():
        return {"status": "ok", "landcover_trained_available": orch._landcover.available()}

    @app.get("/tools")
    def tools():
        return {"version": "0.1.0", "tools": tools_summary()}

    @app.post("/query")
    def query(req: QueryRequest):
        params = dict(req.params or {})
        if req.scene_id:
            params["scene_id"] = req.scene_id
        paths = [p for p in (req.image_paths or []) if Path(p).exists()]
        resp = orch.answer(req.query, image_paths=paths or None, params=params)
        return resp.model_dump(mode="json")

    @app.get("/trace/{query_id}")
    def trace(query_id: str):
        t = orch.store.get(query_id)
        if t is None:
            raise HTTPException(404, "unknown query_id")
        return t

    @app.get("/traces")
    def traces(limit: int = 20):
        return orch.store.recent(limit)
