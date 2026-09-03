"""SatQuery AI — interactive web application (FastAPI + static frontend).

Design reference: ../design.md §2 (3-pane layout), §5 (overlay palette),
§6 (trace panel), §9 (/api/v1 contract), §11 (edge-case copy), §12 (offline,
no CDN, dark + cyan). The frontend in web/ is plain HTML/CSS/JS with no build
step and no external network calls (offline-friendly, NFR).

Flow:  POST /api/v1/ingest (or /demo) -> request_id + inventory + base previews
       POST /api/v1/query -> answer card + overlay layers + full trace
       all rendered rasters/overlays served as PNG from the session dir.

Run:   uvicorn satquery.web_server:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import io
import json
import shutil
import time
import uuid
from pathlib import Path

import numpy as np

from . import __version__
from .ingestion import IngestionError, from_array, load_raster
from .orchestrator import Orchestrator
from .registry import tools_summary
from .schemas import Modality
from .trace import TraceStore
from .webapp import write_base_preview, render_result_layers

ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = ROOT / "web"
SESS_DIR = ROOT / "web_data" / "sessions"
SESS_DIR.mkdir(parents=True, exist_ok=True)

try:
    from fastapi import FastAPI, File, HTTPException, UploadFile
    from fastapi.responses import FileResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles
    _FASTAPI = True
except ImportError:  # pragma: no cover
    _FASTAPI = False


# --- in-memory session store -------------------------------------------------

class Session:
    def __init__(self, sid: str):
        self.id = sid
        self.dir = SESS_DIR / sid
        self.art = self.dir / "artifacts"
        self.art.mkdir(parents=True, exist_ok=True)
        self.images = []          # RasterImage objects
        self.inventory = []       # dicts for the UI
        self.pair = None

    def base_url(self, name: str) -> str:
        return f"/web/sessions/{self.id}/artifacts/{name}"


_SESSIONS: dict[str, Session] = {}

# One global orchestrator (lazy tools, shared trace DB). Artifact dir is
# overridden per-request to the session dir so tools save masks/overlays where
# the static route can serve them.
_ORCH = Orchestrator(trace_store=TraceStore(ROOT / "web_data" / "trace.db"),
                     artifact_dir=SESS_DIR)


# --- synthetic demo scenes (spectral-consistent, like scripts/make_demo...) --

def _synth_optical(kind: str, seed: int, size: int = 120):
    rng = np.random.default_rng(seed)
    bands = ["B02", "B03", "B04", "B08"]
    arr = rng.uniform(0.05, 0.2, (4, size, size)).astype(np.float32)
    arr[3] = rng.uniform(0.35, 0.6, (size, size)).astype(np.float32)   # NIR veg
    if kind == "rural":
        arr[3, 80:110, 60:95] = 0.02      # water
        arr[2, 80:110, 60:95] = 0.03
    else:  # urban fringe
        arr[3, 20:60, 20:70] = 0.12       # built-up
        arr[2, 20:60, 20:70] = 0.22
    return from_array(arr, bands, crs="EPSG:32633"), "optical", f"{kind} (Sentinel-2 like, 10 m)"


def _synth_sar(seed: int, size: int = 120):
    rng = np.random.default_rng(seed)
    vv = rng.normal(-12, 2.5, (size, size)).astype(np.float32)
    vh = rng.normal(-18, 2.5, (size, size)).astype(np.float32)
    vv[80:110, 60:95] = -22      # specular water
    vh[80:110, 60:95] = -27
    return from_array(np.stack([vv, vh]), ["VV", "VH"], crs="EPSG:32633"), "sar", "Sentinel-1 like, VV/VH dB"


def _add_image(sess: Session, img, label: str, name: str):
    sess.images.append(img)
    url = write_base_preview(img, sess.art, f"img{len(sess.images)}")
    sess.inventory.append({
        "name": name,
        "modality": img.modality.value,
        "bands": img.bands,
        "crs": img.crs,
        "size_px": [img.width, img.height],
        "label": label,
        "preview_url": url,
    })


def _pair_check(sess: Session) -> dict:
    imgs = sess.images
    if len(imgs) < 2:
        return {"type": "single", "offset_px": None, "compatible": True,
                "banner": "green", "message": f"{len(imgs)} image loaded."}
    from .ingestion import check_coregistration
    a, b = imgs[0], imgs[1]
    mods = {a.modality.value, b.modality.value}
    is_xmodal = ("sar" in mods and "optical" in mods) or a.modality.value == "pair"
    ok, off, shift = check_coregistration(a, b)
    ptype = "cross_modal" if is_xmodal else "bi_temporal"
    if ok:
        msg = (f"✓ {'co-registered optical+SAR pair' if is_xmodal else 'bi-temporal pair'}"
               f" — offset {off:.1f} px")
        banner = "green"
    else:
        msg = f"⚠ offset ~{off:.1f} px — auto re-registration would run before fusion"
        banner = "amber"
    pair = {"type": ptype, "offset_px": round(off, 2), "compatible": ok,
            "banner": banner, "message": msg}
    sess.pair = pair
    return pair


# --- app ---------------------------------------------------------------------

if _FASTAPI:
    app = FastAPI(title="SatQuery AI web", version=__version__)
    app.mount("/web/static", StaticFiles(directory=str(WEB_DIR)), name="static")

    @app.get("/")
    def index():
        return FileResponse(str(WEB_DIR / "index.html"))

    @app.get("/api/v1/health")
    def health():
        return {"status": "ok", "version": __version__,
                "landcover_trained_available": _ORCH._landcover.available()}

    @app.get("/api/v1/tools")
    def tools():
        return {"version": "0.1.0", "tools": tools_summary()}

    @app.get("/web/sessions/{sid}/artifacts/{fname}")
    def artifact(sid: str, fname: str):
        p = (SESS_DIR / sid / "artifacts" / fname).resolve()
        if not str(p).startswith(str(SESS_DIR.resolve())) or not p.exists():
            raise HTTPException(404, "artifact not found")
        return FileResponse(str(p))

    @app.post("/api/v1/demo")
    def demo(set: str = "bi_temporal"):
        sid = uuid.uuid4().hex[:12]
        sess = Session(sid)
        _SESSIONS[sid] = sess
        if set == "cross_modal":
            _add_image(sess, _synth_optical("rural", 7)[0],
                       "optical · rural · cloudy west", "demo_optical.tif")
            _add_image(sess, _synth_sar(7)[0], "SAR · VV/VH", "demo_sar.tif")
        elif set == "single":
            _add_image(sess, _synth_optical("rural", 7)[0],
                       "optical · rural + water", "demo_optical.tif")
        else:  # bi_temporal
            a, *_ = _synth_optical("rural", 7)
            b, *_ = _synth_optical("urban", 11)
            _add_image(sess, a, "t1 · 2018-05 · optical", "demo_t1.tif")
            _add_image(sess, b, "t2 · 2021-03 · optical", "demo_t2.tif")
        return {"request_id": sid, "inventory": sess.inventory,
                "pair": _pair_check(sess), "demo": True}

    @app.post("/api/v1/ingest")
    async def ingest(files: list[UploadFile] = File(...)):
        sid = uuid.uuid4().hex[:12]
        sess = Session(sid)
        _SESSIONS[sid] = sess
        errors = []
        for up in files[:2]:
            data = await up.read()
            suffix = Path(up.filename).suffix.lower()
            tmp = sess.dir / up.filename
            tmp.write_bytes(data)
            try:
                img = load_raster(tmp)
                _add_image(sess, img, img.modality.value, up.filename)
            except IngestionError as e:
                errors.append({"file": up.filename, "code": "E_FORMAT",
                               "message": str(e),
                               "fix": "Upload a GeoTIFF/TIFF; PNG/JPEG are accepted "
                                      "only for benchmark datasets (VRSBench/RSVQA/CDVQA)."})
        if not sess.images:
            return JSONResponse(status_code=422, content={"rejected": errors})
        return {"request_id": sid, "inventory": sess.inventory,
                "pair": _pair_check(sess), "warnings": errors}

    @app.post("/api/v1/query")
    async def query(body: dict):
        sid = body.get("request_id")
        sess = _SESSIONS.get(sid)
        if sess is None:
            raise HTTPException(404, "unknown request_id — ingest or load demo first")
        q = (body.get("query") or "").strip()
        if not q:
            raise HTTPException(422, "empty query")
        is_demo = bool(body.get("demo"))

        t0 = time.time()
        params = {"demo": True} if is_demo else {}
        if body.get("scene_id"):
            params["scene_id"] = body["scene_id"]
        _ORCH.artifact_dir = sess.art    # tools write overlays into this session
        resp = _ORCH.answer(q, images=list(sess.images), params=params)
        elapsed = time.time() - t0

        # Normalize numpy scalars in bbox/labels for JSON serialization.
        if resp.result and resp.result.bbox:
            resp.result.bbox = [float(v) for v in resp.result.bbox]
        if resp.result:
            for lbl in resp.result.labels:
                if isinstance(lbl.get("score"), (np.floating, np.integer)):
                    lbl["score"] = float(lbl["score"])

        # Overlay layers rendered from the (first) image + tool result.
        layers = []
        if sess.images and resp.result is not None:
            layers = render_result_layers(sess.images[0], resp.result,
                                          sess.art, f"q{sess.id[:6]}")
        trace = resp.trace.model_dump(mode="json")
        return {
            "request_id": sid,
            "query": q,
            "task": resp.task.value if resp.task else None,
            "tool": resp.tool,
            "status": resp.status,
            "trained": resp.trained,
            "abstain": resp.abstain,
            "fallback_used": resp.fallback_used,
            "answer": resp.answer,
            "confidence": resp.confidence,
            "elapsed_s": round(elapsed, 2),
            "warnings": resp.warnings,
            "layers": layers,
            "result": resp.result.model_dump(mode="json") if resp.result else None,
            "trace": trace,
            "inventory": sess.inventory,
            "pair": sess.pair,
        }
