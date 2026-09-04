"""Web GUI integration tests — the /api/v1 contract the judged web app uses."""
import pytest

from satquery.web_server import app

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="module")
def c():
    return TestClient(app)


def test_index_and_static_served(c):
    assert c.get("/").status_code == 200
    assert c.get("/web/static/app.js").status_code == 200
    assert c.get("/web/static/styles.css").status_code == 200


def test_health_and_tools(c):
    h = c.get("/api/v1/health").json()
    assert h["status"] == "ok" and "landcover_trained_available" in h
    tools = c.get("/api/v1/tools").json()["tools"]
    assert len(tools) >= 8


def test_demo_single_and_preview(c):
    d = c.post("/api/v1/demo?set=single").json()
    assert d["request_id"] and len(d["inventory"]) == 1
    url = d["inventory"][0]["preview_url"]
    r = c.get(url)
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"


def test_demo_cross_modal_pair_banner(c):
    d = c.post("/api/v1/demo?set=cross_modal").json()
    assert len(d["inventory"]) == 2
    assert d["pair"]["type"] == "cross_modal"
    assert d["pair"]["banner"] in ("green", "amber")


def test_demo_landcover_cached_is_trained(c):
    d = c.post("/api/v1/demo?set=single").json()
    r = c.post("/api/v1/query", json={
        "request_id": d["request_id"],
        "query": "What land cover types are in this image?",
        "demo": True}).json()
    assert r["task"] == "landcover" and r["trained"] is True
    assert "trace" in r and [e["step"] for e in r["trace"]["events"]]


def test_grounding_returns_bbox_overlay(c):
    d = c.post("/api/v1/demo?set=single").json()
    r = c.post("/api/v1/query", json={
        "request_id": d["request_id"], "query": "Locate the water body.",
        "demo": True}).json()
    assert r["task"] == "ground"
    assert r["result"]["bbox"] is not None
    kinds = [L["kind"] for L in r["layers"]]
    assert "bbox" in kinds
    assert c.get(r["layers"][0]["url"]).status_code == 200


def test_ingest_rejects_unsupported(c):
    # .txt is outside the format allow-list
    r = c.post("/api/v1/ingest",
               files=[("files", ("notes.txt", b"not a raster", "text/plain"))])
    assert r.status_code == 422
    assert "rejected" in r.json()


def test_query_unknown_session_404(c):
    r = c.post("/api/v1/query", json={"request_id": "nope", "query": "hi"})
    assert r.status_code == 404
