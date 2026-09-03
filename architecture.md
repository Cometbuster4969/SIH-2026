# SatQuery AI — Architecture (PS 26167, ISRO, SIH 2026)

**Version:** 1.0 — 3 Sep 2026
**Companion docs:** `design.md` (UI/API/report design) · `checkpoints.md` (compliance + execution checklist) · `satquery-ai-architecture.md` (PS rating + verified dataset facts)

---

## 1. Goals & hard constraints

| # | Constraint | Source | Consequence |
|---|---|---|---|
| C1 | Single-image VQA mandatory + captioning/grounding | PS mandatory scope | T1+T2 must be demo-ready |
| C2 | Bi-temporal change understanding mandatory | PS | T3 pipeline (mask + change-VQA) |
| C3 | Optical–SAR pair analysis mandatory | PS | T4 fusion + dual UNet |
| C4 | Agentic orchestration, observable trace | PS | Planner + registry + guardrails + trace store |
| C5 | ≥1 component fine-tuned/adapted on BigEarthNet.txt or open RS data | PS | M1 (and M3–M7) LoRA fine-tunes |
| C6 | Formats: GeoTIFF/TIFF (PNG/JPEG only for benchmark paths) | PS input scope | Ingest gate with explicit benchmark allow-list |
| C7 | Hidden eval set: co-registered Cartosat-2S (~1 m) + RISAT (L-band) | PS evaluation | Tile-based, resolution-agnostic, sensor-agnostic design |
| C8 | Downloadable report + confidence + visual evidence | PS expected solution | Report service + overlay layers + confidence model |
| C9 | Interactive GUI/web app + code + models + tests + demo | PS deliverables | React app, Docker, weights tarball, pytest, video |

## 2. Design principles

1. **Tile-based & resolution-agnostic.** Everything processes 512×512 tiles (64 px overlap) with explicit tile→geo transforms. Same pipeline for 20 m Sentinel and 1 m Cartosat.
2. **Tools are registry objects.** Every specialist is a registered tool with a JSON input/output schema, a version, and a confidence contract. The agent only ever plans over the registry — never calls models directly. This is what makes the execution trace auditable (a graded artifact).
3. **Numbers from CV, prose from LLM.** Areas, counts, deltas are computed by masks/detectors. The LLM narrates from structured tool outputs only (integrator prompt forbids invention).
4. **Guardrailed agent.** LLM planner → deterministic schema/scope validation → deterministic fallback router. The demo never crashes on a plan failure.
5. **Trace everything.** Every request persists: query, input inventory, task, plan, per-step tool+params+inputs(hash)+output+confidence+latency, final answer.
6. **Offline-first.** All weights vendored; zero external calls at run time.

## 3. System overview

```
┌──────────────────────────── FRONTEND (React + Vite) ─────────────────────────────┐
│ Chat │ Upload(1–2) │ Image stage + overlay canvas │ Trace panel │ Report (PDF)   │
└──────────────────────────────────┬───────────────────────────────────────────────┘
                     REST /api/v1 + WebSocket /ws/{request_id}
┌─────────────────────────────── BACKEND (FastAPI) ────────────────────────────────┐
│  Ingestion & Validation   │   Agent Orchestrator    │   Evidence & Report Svc    │
│  formats/CRS/bands/modal- │   Planner → Guardrail   │   overlays, confidence,    │
│  ity/co-reg/tiling →      │   Validator → Executor  │   PDF, SQLite trace store  │
│  Input Inventory JSON     │   → Integrator; Fallback│                           │
└──┬───────────┬────────────┬─┴──────────┬────────────┴──────────┬────────────────┘
   │           │            │            │                       │
┌──▼───────┐ ┌▼─────────┐ ┌─▼──────────┐ ┌──────────────────────▼────────────────┐
│ T1 vqa / │ │ T2 ground│ │ T3 change_ │ │ T4 xmodal_caption / xmodal_vqa /      │
│ T1 caption│ │          │ │ map +      │ │ xmodal_mask  (M6 fusion + M7 UNet++)  │
│ (M1)     │ │ (M3)     │ │ change_vqa │ │                                       │
└──────────┘ └──────────┘ │ (M4 + M5)  │ └───────────────────────────────────────┘
                          └────────────┘
   Shared: T5 evidence utilities (Grad-CAM crops, calibrated confidence, overlay
   encoding) · Integrator (LSP-7B-4bit) · Trace store (SQLite)
```

## 4. Request lifecycle (canonical sequence)

Example: bi-temporal pair, *"What changed between these two dates, and where?"*

```
UI ──POST /ingest (t1.tiff, t2.tiff)──▶ API
API → Ingest: format ✓, crs ✓, modality=optical×2, extent overlap 1.0,
      coreg offset 0.4px, dt=1032d → 512² tiles (t1: 4, t2: 4)
UI ◀──201 {request_id, inventory, pair:{type:"bi_temporal", …}}
UI ──POST /query {request_id, "What changed…"}──▶ API
API → Planner (Qwen2.5-7B-4bit, registry+inventory+query)
      → plan {task:"CHANGE_VQA", steps:[change_map, change_vqa, integrate]}
API → Guardrail: scope=bi_temporal ⇒ tasks⊆{CHANGE_*} ✓ ; params⊆whitelist ✓
      (fail ⇒ RuleRouter fallback plan, trace.fallback_used=true)
API → Executor (WS events streamed per step):
  step1 change_map (M4/BiT)  → mask + facts{area_pct:12.4, builtup:+8.1%}  conf 0.87
  step2 change_vqa (M5/M1 2img, t1+t2+facts) → answer text              conf 0.81
  step3 integrate (LSP)      → final answer + citations + conf 0.82
UI ◀── done: answer + overlays (change map, areas) + trace + report_url
```

## 5. Ingestion & Validation service

| Check | Rule | Failure action |
|---|---|---|
| Format | GeoTIFF/TIFF always; PNG/JPEG **only** if path/filename matches benchmark allow-list (VRSBench/RSVQA/CDVQA dirs) | `E_FORMAT` reject card |
| CRS/geotransform | readable; extent + pixel size extracted | `E_CRS` reject |
| Modality | bands≥3 → optical/multispectral (S2 band-order map B2,B3,B4,B8,…; Cartosat RGB/NIR); 1–2 bands + SAR signature/speckle → SAR (amplitude band; optional γ-filter) | `E_BANDS` reject |
| Size | ≤ 65k px per side; else tile plan with time estimate | warn + tile |
| Pair: same-area | extent overlap ≥ 0.9 else auto-crop to common extent | auto-crop, logged |
| Pair: co-registration | normalized cross-correlation on downsampled grayscale → offset px | >2 px ⇒ auto re-register (`warp`), logged in trace |
| Pair: type | 2 optical + dates differ → `bi_temporal`; optical + SAR → `cross_modal`; identical single modality+date → `invalid` | `E_PAIR_MISMATCH` reject card with reason |
| Metadata | dates from sidecar/filename/metadata; missing ⇒ assume file order, flag direction ambiguity (lowers confidence on directional claims) | warn |

Output: **Input Inventory** JSON (canonical schema in `design.md` §11) + tile index (tile id, geo bounds, pixel box, overlap mask).

## 6. Tool registry (contracts)

Registry lives in `backend/agent/registry.yaml` + JSON schemas in `backend/agent/schemas/`.
`GET /api/v1/tools` exposes it (satisfies "predefined registry" visibility).

| Tool | Model | Inputs | Outputs |
|---|---|---|---|
| `vqa` | M1 RS-VLM | image, question | answer, answer_type, confidence |
| `caption` | M1 RS-VLM | image | caption, facts{landcover, objects[]}, confidence |
| `ground` | M3 Grounding-DINO-T | image, phrase | boxes[{xywh, score, label}], confidence |
| `change_map` | M4 BiT | img_t1, img_t2, thr | mask, facts{area_pct, class_deltas{top5}, polygons[{centroid_geo, area_ha}]}, confidence |
| `change_vqa` | M5 (M1 2-image head) | img_t1, img_t2, question?, change_facts? | answer, confidence |
| `xmodal_caption` | M6 fusion | optical, sar | joint caption, per-modality findings, confidence |
| `xmodal_vqa` | M6 fusion | optical, sar, question | answer, confidence |
| `xmodal_mask` | M7 dual UNet++ | optical, sar | masks{built_up, water}, per-class IoU-conf, confidence |
| `integrate` | LSP 7B-4bit | tool outputs (JSON), images | final answer + claim→tool citations + overall confidence |

Tool contract (all tools):

```json
{
  "tool": "change_map", "version": "bit-v1.0-lora", "status": "ok",
  "answer": null,
  "masks": ["overlay://change/t1_t2.png"],
  "facts": {"area_pct": 12.4, "class_deltas": {"built_up": 8.1}},
  "confidence": 0.87, "latency_ms": 4100,
  "evidence": ["crop://t1/0.41,0.52,0.3,0.3"]
}
```

Canonical plans (fallback router = this table, keyed by scope × task intent):

| Scope \ Intent | describe | ask | highlight/where | classify built-up/water | trend (↑/↓/same) |
|---|---|---|---|---|---|
| 1 optical / 1 SAR | `caption` | `vqa` | `ground` | — | — |
| bi-temporal | `change_map→change_vqa` | `change_map→change_vqa` | `change_map` (+`ground` on t2) | `change_map` | `change_map` (area diff) → `change_vqa` constrained |
| optical+SAR | `xmodal_caption`(+`xmodal_mask`) | `xmodal_vqa` | `xmodal_vqa`+`ground` | `xmodal_mask` | — |

All plans end with `integrate`. Multi-step user queries ⇒ planner may emit longer DAGs (`depends_on` supported).

## 7. Specialist models

| ID | Component | Base | Fine-tune data (all open) | Serves |
|---|---|---|---|---|
| **M1** | RS-VLM (★ adaptation proof) | **Qwen2-VL-2B-Instruct** (alt: InternVL2.5-2B if BE.txt authors release adapters) | BigEarthNet.txt (229K pairs: captions, binary/MCQ VQA, referring-expr) + VRSBench + RSVQA + TAMMI | vqa, caption, 2-image change/xmodal heads |
| **M2** | Planner + Integrator LLM | **Qwen2.5-7B-Instruct** (4-bit, no RS fine-tune needed) | prompt-engineered; 200-query classification suite for QA | plan, integrate |
| **M3** | Grounding | Grounding-DINO-T | VRSBench 52,472 refs + BE.txt referring-expr + ADE20K-GS slice | ground |
| **M4** | Change backbone | BiT (or ChangeFormer) | QAG-360K (masks) + CDVQA (semantic change maps) + LEVIR-CD/WHU-CD | change_map |
| **M5** | Change-VQA head | M1 (2-image mode) | CDVQA (122K QA) + QAG-360K triplets + ChangeChat-105k | change_vqa |
| **M6** | Optical–SAR fusion | dual ViT towers (S2-pretrained optical, SAR-pretrained: SEN2SAR/SARImageNet) + Q-Former → M1 decoder | **BE.txt S1–S2–text triplets (229K)** + TAMMI (VHR+MS+SAR VQA) | xmodal_caption, xmodal_vqa |
| **M7** | Dual-input UNet++ | scratch, ImageNet init | BigEarthNet v2 LULC reference maps (S2+S1 aligned) | xmodal_mask (built_up, water) |
| **T5** | Evidence utilities | Grad-CAM/attention rollback; token-probability extraction; temperature calibration on held-out set | — | confidence + evidence crops |

**Why Qwen2-VL-2B:** native multi-image input (one backbone for single + bi-temporal + optical–SAR), dynamic resolution (tile-friendly, C7-safe), LoRA-trainable on one 24 GB GPU, vLLM-served, strong bbox-format support.

### Training setup (M1 example)
- LoRA r=64, α=128, all-linear (+ViT last-4 blocks), freeze rest; bf16; grad-ckpt
- lr 1e-4 cosine, 2–3 epochs; dynamic res 512–1024; mixed-task batching (caption:VQA:ground ≈ 4:4:2)
- **SIH-time reality check:** full 229K BE.txt in 2 weeks on 1–2 GPUs is not guaranteed → stratified **100K subset** (balanced by LULC × task) is the baseline plan; full data if GPUs allow. M5/M6/M7 similarly staged.
- Per-model **eval gate** before integration: must beat zero-shot on internal holdout by the margin in `checkpoints.md` §F, else iterate.

## 8. Agent orchestrator

```
query + inventory
   │
   ▼
Planner (M2, structured prompt: registry + inventory + taxonomy + plan JSON schema)
   │   taxonomy: CAPTION|VQA|GROUND|CHANGE_DESC|CHANGE_VQA|CHANGE_MAP|
   │             XMODAL_CAPTION|XMODAL_VQA|XMODAL_MASK|COMPAT_REPORT|MULTI_STEP
   ▼
Guardrail Validator (deterministic)
   1. scope check: input-scope ⇒ allowed tasks (hard)
   2. plan JSON-schema valid; tools ∈ registry
   3. params ⊆ per-tool whitelist (PS: "only permitted task parameters")
   4. no cycles; depends_on resolvable
   fail ⇒ RuleRouter (canonical table §6) — plan rebuilt, trace.fallback_used=true
   ▼
Executor — DAG run; per-step timeout (30 s) + 1 retry; structured outputs only;
          partial failure ⇒ degrade: drop step, continue, flag in answer
   ▼
Integrator (M2) — prompt: "answer ONLY from tool outputs + images; cite tools;
          state confidence; never invent numbers" ⇒ final answer + citations + confidence
   ▼
Trace persisted (SQLite) → UI + PDF
```

**Confidence aggregation** (T5): per-tool numeric conf → final = weighted geometric mean (weights by task criticality); disagreement rule: if optical vs SAR per-class conf differ >0.3 on a shared claim → surface ⚠ in answer/trace/report. Badges: High ≥0.75, Med 0.50–0.75, Low <0.50.

## 9. Inference serving & deployment

| Model | Memory (serving) | Runner | GPU |
|---|---|---|---|
| M1 Qwen2-VL-2B (bf16+LoRA) | ~6 GB | vLLM (multi-image) | A |
| M2 Qwen2.5-7B-4bit | ~4.5 GB | vLLM (same instance) | A |
| M3 Grounding-DINO-T | ~1.5 GB | HF worker | B (or A time-sliced) |
| M4 BiT (ViT-B) | ~0.8 GB | HF worker | B |
| M5 (M1 head) | — (shared M1) | vLLM | A |
| M6 fusion+Q-Former | ~2 GB | HF worker | B |
| M7 UNet++ | ~0.4 GB | HF worker | B |

- **Min viable: 1× RTX 4090 24 GB** — one vLLM instance (`gpu-mem-util 0.85`) for M1+M2, B-tools time-sliced via queue. **Recommended: 2× 24 GB** per table.
- **Docker Compose:** `frontend` (nginx static), `api` (FastAPI, port 8000, binds 0.0.0.0), `models` (vLLM + workers); volume `/models` with vendored weights; SQLite at `/data/traces.db`.
- **`POST /api/v1/warmup`** loads all weights; cold start target <10 min.
- **Offline guarantee:** no pip/CDN/telemetry calls at runtime; verified with egress block (checklist §D).
- Concurrency: 1 request at a time (queue, 2nd user sees position) — matches single-user judging.

## 10. Latency budgets (1024² image, 4090, median)

| Stage | Target |
|---|---|
| Ingest + tile (1024²) | 1–3 s |
| Plan (LLM) | 1–2 s |
| caption / vqa (M1) | 3–6 s |
| ground (M3) | 2–4 s |
| change_map (M4) | 4–8 s |
| change_vqa (M5) | 3–5 s |
| xmodal_* (M6/M7) | 3–6 s |
| integrate | 2–4 s |
| **End-to-end targets** | **single ≤ 8 s · change ≤ 15 s · cross-modal ≤ 15 s** |

## 11. Storage

```sql
requests(id TEXT PK, created_at, query, inventory_json, task,
         plan_json, planner_model, fallback_used INT,
         final_answer, confidence REAL, total_ms INT, report_path)
request_steps(id TEXT PK, request_id FK, seq INT, tool TEXT, version TEXT,
              params_json, inputs_json, output_summary_json, confidence REAL,
              latency_ms INT, status TEXT)
artifacts(id TEXT PK, request_id FK, kind TEXT, path TEXT, meta_json)  -- overlays/crops
```

## 12. Repository layout

```
satquery/
├── frontend/                 # React+Vite app (chat, stage, trace, report button)
├── backend/
│   ├── api/                  # FastAPI routes, ws events, warmup, /tools
│   ├── ingestion/            # gdal validation, modality, coreg, tiling
│   ├── agent/                # registry.yaml, schemas/, planner, guardrail,
│   │                         # rulerouter, executor, integrator
│   ├── tools/                # m1_vlm/ m3_ground/ m4_change/ m6_fusion/
│   │                         # m7_unet/ t5_evidence/
│   ├── reporting/            # weasyprint PDF
│   └── store/                # sqlite
├── training/                 # per-model: data prep, configs, launch scripts,
│   │                         # eval-gate scripts, run logs
├── eval/                     # benchmark harness (VRSBench/RSVQA/CDVQA/BE.txt
│                             # benchmark split) + metric calcs + result tables
├── tests/                    # pytest: unit + integration + test matrix
├── demo/                     # sample data (5 demo scenes), demo script, video
├── models/                   # weights (git-ignored; submission tarball)
├── docker/                   # Dockerfiles + compose
└── docs/                     # this doc + design.md + checkpoints.md
```

## 13. Non-functional requirements

- NFR-1 Offline-capable, single-command start (`docker compose up`)
- NFR-2 Any GeoTIFF size ≤65k px (tiling) — Cartosat/RISAT safe (C7)
- NFR-3 Every DONE request ⇒ complete trace + PDF report (C8)
- NFR-4 No hard failures on invalid plans/inputs ⇒ reject card or fallback (demo-safe)
- NFR-5 Deterministic reproducibility: seeds fixed, model versions + adapter hashes recorded in every trace
- NFR-6 All datasets licenses recorded in `docs/datasets.md` (all CC-BY / open)
