# SatQuery AI — Window A prototype

The runnable skeleton for the 5 Sep demo and the codebase Window B builds on.
Real where it counts; heuristic where declared — the answer card and trace never
confuse the two. See `../checkpoints.md` §0.11 and `../architecture.md` for the
binding decisions.

## What is real vs heuristic (Window A)

| Component | Status |
|---|---|
| Raster ingestion — format allow-list, CRS/bands, modality detection, **v0.2.0 band-order assertion**, pair co-reg check, tiling | **REAL** (`satquery/ingestion.py`) |
| Tool registry — `config/registry.yaml`, `GET /tools`, param whitelist (PS A2.4) | **REAL** (`satquery/registry.py`) |
| RuleRouter — deterministic task routing + modality gating; score-neutral vs LLM planner (PS P10) | **REAL** (`satquery/router.py`) |
| SQLite execution trace — every step persisted, no internal reasoning (PS A2.6/P10) | **REAL** (`satquery/trace.py`) |
| Orchestrator — ingest → guardrail → route → execute → integrate, tool failure never crashes the demo | **REAL** (`satquery/orchestrator.py`) |
| Land-cover tool — BIFOLD `resnet50-all-v0.2.0` (23.6 M, mAP macro 0.7107) | **TRAINED WEIGHTS** when torch+configilm+reben present; spectral-index heuristic, reported `degraded`, otherwise (`satquery/tools/landcover.py`) |
| VQA / caption / grounding / change / x-modal / segmentation | declared **heuristics** (`satquery/tools/heuristics.py`) — M1/M3/M4/M7 slot into the same contract in Window B |
| Demo kill switch — `config/demo_cache.json` returns frozen answers per `scene_id` | **REAL** (cached land-cover answer is clearly labelled "cached demo") |

## Run it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt          # core: numpy pyyaml pydantic rasterio
pytest                                    # 33 tests, no GPU/weights needed

# Frozen demo GeoTIFFs (synthetic, spectral-consistent — not satellite data):
python scripts/make_demo_scenes.py

# CLI:
python -m satquery.cli --tools
python -m satquery.cli "What land cover types are in this image?" \
    --image data/demo/optical_scene1_rural.tif --scene-id demo_scene_01

# *********************************************************************
# INTERACTIVE WEB APP — the judged GUI (FastAPI + browser UI, offline)
# *********************************************************************
pip install -r requirements-serve.txt
uvicorn satquery.web_server:app --host 0.0.0.0 --port 8000
# open http://localhost:8000  — upload/demo -> ask -> answer card +
# overlay toggles + execution trace. No CDN, no build step (design §12).
#   REST: /api/v1/health  /tools  /demo  /ingest(multipart)  /query
#         artifacts served from /web/sessions/<id>/artifacts/

# Alt minimal JSON API (no browser UI):
uvicorn satquery.server:app --host 0.0.0.0 --port 8001
#   GET /health  GET /tools  POST /query  GET /trace/{id}  GET /traces

# Alt Streamlit UI (internal):
streamlit run app.py
```

### Web app features (vs design.md)

3-pane layout (inventory · chat · trace) + image stage (design §2): upload 1–2
rasters or load a curated demo set (single / bi-temporal / optical+SAR); answer
cards carry task/trained/heuristic badges + confidence dots (§7); overlay layers
rendered server-side with the §5 palette and visibility toggles (cyan bbox, red
change mask, blue water mask, viridis heatmap); pair banner green/amber/red from
the real co-registration offset; trace panel open with per-step latency and JSON
export; one-click "Full walkthrough"; format rejection returns a fix card (S5).

## Enabling the genuinely trained land-cover model

```bash
pip install torch torchvision configilm safetensors huggingface-hub pillow
git clone https://git.tu-berlin.de/rsim/reben-training-scripts /opt/reben
export PYTHONPATH=/opt/reben:$PYTHONPATH     # provides `reben_publication`
# weights auto-download: BIFOLD-BigEarthNetv2-0/resnet50-all-v0.2.0 (~95 MB)
```
`GET /health` reports `landcover_trained_available: true` when live.
The v0.2.0 band order `[VV, VH, B02..B12]` is asserted in ingestion — a
mismatched stack is refused, not silently mis-scored. For single-modality
patches, prefer the `-s1-` / `-s2-` checkpoints (set `SATQUERY_LANDCOVER_MODEL`).

## Window B swap-in points

The `ToolResult` contract is frozen. Trained models replace heuristic classes
in `satquery/tools/` and flip `trained: true` in `config/registry.yaml` — the
orchestrator, trace, API and UI do not change:

- `vqa_single` / `caption_scene` → **M1** Qwen2-VL-2B QLoRA (PS A1.1 artifact)
- `ground_object` → **M3** Grounding-DINO-T
- `change_detect` / `change_vqa` → **M4** BiT (M5 = M1 two-image mode)
- `xmodal_segment` → **M7** dual UNet++, BIFOLD S1+S2 encoder init
- RuleRouter stays as the guardrail under the LLM planner (D9–D12)

## On-stage honesty line

> "The orchestration you're seeing is real — ingestion, validation, the tool
> registry, routing and the execution trace all run live. The land-cover model
> is BigEarthNet-pretrained. The remaining specialist models are heuristics
> today; they're fine-tuned for the 20 September submission."
