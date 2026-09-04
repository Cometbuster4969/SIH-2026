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
#
# Structured (not pure noise) so the stage looks like real 10 m optical / SAR:
# field blocks, a reservoir, a drainage channel, speckled dB backscatter.
# Geometry is frozen on purpose — the kill-switch cache (config/demo_cache.json)
# and the demo grounding box reference these coordinates:
#   reservoir  ~ rows 80:110, cols 60:95  (south-east lobe)
#   new built-up (t2 only) ~ rows 20:50, cols 64:94  (north-east quadrant)

def _vnoise(rng, h: int, w: int, cell: int) -> np.ndarray:
    """Smooth low-frequency value noise in [0, 1]."""
    gh, gw = max(2, h // cell + 2), max(2, w // cell + 2)
    g = rng.random((gh, gw)).astype(np.float32)
    ys = np.linspace(0, gh - 1, h); xs = np.linspace(0, gw - 1, w)
    y0 = np.floor(ys).astype(int); y1 = np.clip(y0 + 1, 0, gh - 1)
    x0 = np.floor(xs).astype(int); x1 = np.clip(x0 + 1, 0, gw - 1)
    wy = (ys - y0)[:, None]; wx = (xs - x0)[None, :]
    top = g[y0][:, x0] * (1 - wx) + g[y0][:, x1] * wx
    bot = g[y1][:, x0] * (1 - wx) + g[y1][:, x1] * wx
    return top * (1 - wy) + bot * wy


def _reservoir_mask(h: int, w: int) -> np.ndarray:
    yy, xx = np.mgrid[0:h, 0:w]
    return ((yy - 95.0) / 15.0) ** 2 + ((xx - 77.0) / 17.0) ** 2 <= 1.0


def _drainage_mask(h: int, w: int, seed: int) -> np.ndarray:
    """Meandering ~2 px channel from the top-left towards the reservoir."""
    rng = np.random.default_rng(seed)
    xx = np.arange(w)
    path = 12.0 + 80.0 * (xx / max(w - 1, 1)) ** 1.25 \
        + 3.0 * np.sin(xx * 0.09 + rng.random() * 6.0)
    yy, xxg = np.mgrid[0:h, 0:w]
    m = np.abs(yy - path[None, :]) <= 0.9
    m[88:94, 58:64] = True          # tie the channel into the reservoir rim
    return m


def _smooth5(a: np.ndarray) -> np.ndarray:
    """5-point box average (centre + 4-neighbours) — softens per-pixel speckle."""
    p = np.pad(a, 1, mode="edge")
    return (p[:-2, 1:-1] + p[1:-1, :-2] + p[1:-1, 1:-1] + p[1:-1, 2:] + p[2:, 1:-1]) / 5.0


def _smooth9(a: np.ndarray) -> np.ndarray:
    """3x3 box average."""
    p = np.pad(a, 1, mode="edge")
    s = np.zeros_like(a)
    for dy in range(3):
        for dx in range(3):
            s += p[dy:dy + a.shape[0], dx:dx + a.shape[1]]
    return s / 9.0


def _field_blocks(seed: int, h: int, w: int):
    """Shared field-block geometry (ids per pixel) for the optical and SAR
    stand-ins — the pair is co-registered BY CONSTRUCTION, and the SAR gets its
    per-block backscatter variation from the same layout (surface type drives
    both reflectance and dB)."""
    rng = np.random.default_rng(seed * 1000 + 1)
    def _splits(n, lo, hi):
        edges = [0]
        while edges[-1] < n:
            edges.append(min(n, edges[-1] + int(rng.integers(lo, hi))))
        return edges
    er, ec = _splits(h, 12, 26), _splits(w, 12, 26)
    ids = np.zeros((h, w), dtype=np.int32)
    k = 0
    for i in range(len(er) - 1):
        for j in range(len(ec) - 1):
            ids[er[i]:er[i + 1], ec[j]:ec[j + 1]] = k
            k += 1
    return er, ec, ids


def _rural_scene(seed: int, size: int = 120):
    """Sentinel-2-like rural scene: field blocks + texture + water bodies."""
    rng = np.random.default_rng(seed)
    h = w = size
    bands = np.zeros((4, h, w), dtype=np.float32)
    B02, B03, B04, B08 = (b.copy() for b in bands)
    er, ec, ids = _field_blocks(seed, h, w)
    nblk = int(ids.max()) + 1
    kind = rng.random(nblk)
    nir = np.where(kind < 0.55, rng.uniform(0.44, 0.56, nblk),
           np.where(kind < 0.82, rng.uniform(0.38, 0.46, nblk),
                    rng.uniform(0.26, 0.30, nblk)))
    red = np.where(kind < 0.55, rng.uniform(0.11, 0.16, nblk),
           np.where(kind < 0.82, rng.uniform(0.16, 0.21, nblk),
                    rng.uniform(0.23, 0.27, nblk)))
    gmul = rng.uniform(0.75, 1.0, nblk); bmul = rng.uniform(0.4, 0.62, nblk)
    B08[:] = nir[ids]; B04[:] = red[ids]
    B03[:] = red[ids] * gmul[ids]; B02[:] = red[ids] * bmul[ids]
    ys = er[1:-1] + [h - 1]                        # field boundaries read dark
    xs = ec[1:-1] + [w - 1]
    for y in ys:
        B08[y, :] *= 0.62; B04[y, :] *= 0.72; B03[y, :] *= 0.78; B02[y, :] *= 0.72
    for x in xs:
        B08[:, x] *= 0.62; B04[:, x] *= 0.72; B03[:, x] *= 0.78; B02[:, x] *= 0.72

    for band, amp in ((B02, 0.006), (B03, 0.008), (B04, 0.010), (B08, 0.020)):
        band += (rng.random((h, w)) - 0.5) * 2 * amp
        band += (_vnoise(rng, h, w, 6) - 0.5) * 4 * amp

    water = _reservoir_mask(h, w) | _drainage_mask(h, w, seed)
    # Clear water: dark, but blue-dominant (reads blue, not black, after
    # per-band percentile normalization in the preview).
    B08[water] = 0.024; B04[water] = 0.032; B03[water] = 0.05; B02[water] = 0.082
    for band in (B02, B03, B04, B08):
        np.clip(band, 0.0, 1.0, out=band)
    return from_array(np.stack([B02, B03, B04, B08]),
                      ["B02", "B03", "B04", "B08"], crs="EPSG:32633")


def _add_builtup(img, seed: int, y0: int = 20, y1: int = 50, x0: int = 64, x1: int = 94):
    """t2 scene: new built-up footprint in the north-east quadrant + roads."""
    rng = np.random.default_rng(seed)
    arr = img.array.copy()
    B02, B03, B04, B08 = (b.copy() for b in arr)
    B08[y0:y1, x0:x1] = rng.uniform(0.10, 0.14, (y1 - y0, x1 - x0)).astype(np.float32)
    B04[y0:y1, x0:x1] = rng.uniform(0.19, 0.25, (y1 - y0, x1 - x0)).astype(np.float32)
    B03[y0:y1, x0:x1] = B04[y0:y1, x0:x1] * 0.85
    B02[y0:y1, x0:x1] = B04[y0:y1, x0:x1] * 0.75
    for by in range(y0, y1, 10):                       # building blocks
        for bx in range(x0, x1, 10):
            f = rng.uniform(0.88, 1.14)
            B08[by:by + 10, bx:bx + 10] = np.clip(B08[by:by + 10, bx:bx + 10] * f, 0.09, 0.16)
            B04[by:by + 10, bx:bx + 10] = np.clip(B04[by:by + 10, bx:bx + 10] * f, 0.17, 0.28)
    for yy in (y0 + 9, y0 + 21):                       # access roads
        B08[yy:yy + 2, x0:x1] = 0.05; B04[yy:yy + 2, x0:x1] = 0.07
        B03[yy:yy + 2, x0:x1] = 0.06; B02[yy:yy + 2, x0:x1] = 0.05
    for xx in (x0 + 9, x0 + 21):
        B08[y0:y1, xx:xx + 2] = 0.05; B04[y0:y1, xx:xx + 2] = 0.07
        B03[y0:y1, xx:xx + 2] = 0.06; B02[y0:y1, xx:xx + 2] = 0.05
    return from_array(np.stack([B02, B03, B04, B08]), img.bands, crs=img.crs)


def _add_cloud(img, seed: int, width: int = 52):
    """Puffy cloud deck over the western third (matches the cached cross-modal
    answer). Two noise scales -> lobes; east edge fades out smoothly."""
    rng = np.random.default_rng(seed)
    h, w = img.array.shape[1:]
    v1 = _vnoise(rng, h, w, 16)                        # lobe scale
    v2 = _vnoise(rng, h, w, 5)                         # bump scale
    body = np.clip(0.62 * v1 + 0.38 * v2 - 0.30, 0, 1) ** 1.5
    col = np.clip((width - np.arange(w)) / width, 0, 1.0)[None, :]
    op = np.clip(body * (0.30 + 0.70 * col), 0, 1).astype(np.float32)
    arr = np.stack([b * (1 - op) + 0.62 * op for b in img.array])
    return from_array(arr, img.bands, crs=img.crs)


def _sar_scene(seed: int, size: int = 120):
    """Sentinel-1-like dB backscatter: smooth terrain, per-field variation
    (same block geometry as the optical stand-in), speckle, dark water."""
    rng = np.random.default_rng(seed)
    h = w = size
    _, _, ids = _field_blocks(seed, h, w)
    nblk = int(ids.max()) + 1
    base = -10.5 + 3.0 * (_vnoise(rng, h, w, 7) - 0.5)
    base = base + rng.normal(0.0, 1.1, nblk)[ids]     # surface type -> dB
    base[_reservoir_mask(h, w)] = -21.0
    # Wet, smooth channel = specular dark (same sign as in optical — keeps the
    # co-registration cross-correlation honest for the A3.3 demo pair).
    base[_drainage_mask(h, w, seed)] = -18.0
    # Multiplicative speckle, softened to ~1 resolution cell so it reads as
    # SAR texture at 4x upscale instead of TV static.
    speck = _smooth9(_smooth9(np.exp(rng.normal(0.0, 0.5, (h, w))).astype(np.float32)))
    speck = speck / speck.mean()
    vv = (base * speck).astype(np.float32)
    vh = (base - 6.0 + rng.normal(0.0, 0.8, (h, w)) * _smooth9(speck)).astype(np.float32)
    return from_array(np.stack([vv, vh]), ["VV", "VH"], crs="EPSG:32633")


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


def _demo_change_layers(sess: Session, stem: str) -> list:
    """Declared-heuristic change map for the cached (kill-switch) demo answer."""
    try:
        from .ingestion import ndvi
        from .webapp import COLOR_CHANGE_ADDED, mask_overlay
        a, b = sess.images[0], sess.images[1]
        if a.array.shape[1:] != b.array.shape[1:]:
            return []
        m = (np.abs(ndvi(a) - ndvi(b)) > 0.25).astype(np.uint8)
        if not m.any():
            return []
        p = sess.art / f"{stem}_change.png"
        mask_overlay(m, COLOR_CHANGE_ADDED).save(p)
        return [{"name": "change map (heuristic)", "kind": "mask",
                 "url": f"/web/sessions/{sess.id}/artifacts/{p.name}",
                 "color": "#E53935",
                 "legend": "changed pixels (NDVI/NDBI Δ>0.25)"}]
    except Exception:
        return []


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
            _add_image(sess, _add_cloud(_rural_scene(7), 31),
                       "optical · rural · cloud over west", "demo_optical.tif")
            _add_image(sess, _sar_scene(7),
                       "SAR · VV/VH · drainage channel", "demo_sar.tif")
        elif set == "single":
            _add_image(sess, _rural_scene(7),
                       "optical · rural + reservoir", "demo_optical.tif")
        else:  # bi_temporal — co-registered; t2 adds the NE built-up footprint
            _add_image(sess, _rural_scene(7),
                       "t1 · 2018-05 · optical", "demo_t1.tif")
            _add_image(sess, _add_builtup(_rural_scene(7), 21),
                       "t2 · 2021-03 · optical", "demo_t2.tif")
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
        # The kill-switch (cached) change answer ships no mask artifact — render
        # the evidence from the pair itself so the stage always shows it.
        if not layers and is_demo and len(sess.images) >= 2 \
                and resp.task is not None and resp.task.value == "change":
            layers = _demo_change_layers(sess, f"q{sid[:6]}")
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
