# SatQuery AI (SIH 2026, PS 26167 — ISRO)
## Problem Statement Rating + Reference Architecture

---

# PART 1 — Rating of the Problem Statement

**Overall: 7.5 / 10** — a strong, well-scoped, demo-able problem with modern data. It is
judgeable and hard to fake, but it has one concrete defect (missing evaluation table) and
several unstated constraints that teams must plan around.

| Dimension | Score | Note |
|---|---|---|
| Clarity & completeness of scope | 8.5/10 | Input scope, mandatory tasks, representative queries, deliverables are all explicit and testable |
| Technical feasibility | 7.5/10 | Heavy but achievable; public datasets + open base models make it realistic |
| Evaluation fairness/definability | 6/10 | Evaluation-criteria table is a **placeholder** ("Add table here"); metric names/weights unknown; hidden ISRO set |
| Data availability | 9/10 | All datasets are open (verified), but BigEarthNet.txt is brand-new (Mar 2026) and large |
| Novelty fit for SIH / judging | 9/10 | Agentic orchestration is explicitly the graded novelty; execution trace is directly observable |
| Constraints definition | 6/10 | No GPU budget, latency SLA, internet policy, or deployment/submission protocol specified |

### What's genuinely good
1. **Explicit mandatory scope** — single-image VQA (mandatory) + one of {captioning, grounding}; bi-temporal change understanding (mandatory); optical–SAR pair analysis (mandatory); agentic routing (mandatory). You know exactly what to build before writing a line of code.
2. **The data choice is excellent and current.** *BigEarthNet.txt* (arXiv 2603.29630, Herzog et al., TU Berlin/BIFOLD, Mar 2026) = **464,044 co-registered Sentinel-1 SAR + Sentinel-2 multispectral pairs with ~9.6M text annotations** (geographically-anchored captions, binary + MCQ VQA, referring-expression/grounding instructions; 15 tasks, 4 categories; splits 229K/118K/117K train/val/test; a manually-verified benchmark split of 1,082 pairs). It is downloadable from Hugging Face (`BIFOLD-BigEarthNetv2-0/BigEarthNet.txt`, CC-BY 4.0). This is *exactly* the cross-modal adaptation data the problem demands — the PS was clearly written around this dataset.
3. **Benchmarks are real and public**: VRSBench (NeurIPS 2024 D&B: 29,614 images, 29,614 human-verified captions, 52,472 object references, 123,221 QA pairs — captioning/grounding/VQA), RSVQA, CDVQA (Yuan et al., TGRS 2022: 2,968 bi-temporal 512×512 pairs, 122K+ QA pairs, pixel-level semantic change maps).
4. **Anti-cherry-picking evaluation**: prescribed public test splits + undisclosed ISRO/SAC set (Cartosat-2S optical + RISAT SAR pairs, co-registered). Teams cannot overfit to what they see; they must build general pipelines.
5. **Graded novelty is observable**: "only the observable execution trace — selected task, models/tools, permitted parameters, outputs — will be evaluated." That means a visible agent trace is a scoring surface, not decoration.
6. **Representative queries are given** → you can build your demo script before the event.

### Weaknesses / risks you must plan for
1. **Missing evaluation table (biggest flaw).** "Scores will be normalised before combining different metrics" but no metric names, thresholds, or weights. Assume standard metrics (below) and make your *report* self-evidently good, since human judges will see it.
2. **Domain gap, not discussed in the PS**: you train on Sentinel (S2 ~10–20 m, S1 C-band ~5 m) but the hidden set is **Cartosat-2S (~0.5–1 m VHR) + RISAT (L-band ~3 m)**. Your models must be resolution- and sensor-agnostic → tile-based processing + strong fine-tuning is the answer; hard-coding patch sizes/assumptions will fail.
3. **BigEarthNet.txt is 4 months old at event time.** Tooling/docs may be rough, download is large (hundreds of GB for S1+S2 pairs), and its captions are template+LLM generated (the paper admits hallucination risk; that's why they made a manually-verified split). QC your data prep early; keep a fallback (reBEN / Sentinel2Cap / BigEarthNet v2 + self-generated text).
4. **No compute/deployment constraints stated** — no GPU budget, latency limit, or internet policy for judging. Assume: local weights only, 1–2 mid-range GPUs, single-user. Offline-capable from day one.
5. **"Confidence" is required but undefined** — how it's judged is unclear. Provide calibrated probabilities + visual evidence + an auditable trace; make confidence *visible and reasonable*, not just a number.
6. **Fine-tuning bar is soft** ("fine-tuned or *otherwise adapted*"), but "a generic LLM/VLM without RS adaptation will not satisfy the requirements" → at least one component must have trained RS weights. LoRA on a VLM satisfies this cleanly — document the before/after benchmark numbers as proof.
7. The pasted PS text is cut off at "VRSBench — for" — read the full official PDF for exact split assignments before building your eval harness.

### Strategic takeaways
- The winning pattern is: **one RS-adapted VLM backbone (Qwen2-VL or InternVL) fine-tuned on BigEarthNet.txt** + specialist heads (grounding, change, SAR fusion) + a **rock-solid rule-guarded agent** that produces a beautiful auditable trace.
- Benchmark your own stack against VRSBench/RSVQA/CDVQA *before* the hackathon; the delta after adaptation is your "we satisfy the fine-tuning requirement" slide.
- Design everything tile-based and sensor-agnostic so the hidden Cartosat/RISAT set just works.

---

# PART 2 — Reference Architecture

## 2.1 High-level view

```
┌──────────────────────────── FRONTEND (React + Vite) ─────────────────────────────┐
│  Chat panel (natural-language queries)   │  Upload panel (1 or 2 images)         │
│  Image viewer + overlay canvas (boxes / change masks / heatmaps, toggleable)     │
│  Execution-trace panel (task, tools, params, confidence, latency)                │
│  Download report (PDF)                                                           │
└───────────────────────────────────────────┬──────────────────────────────────────┘
                              REST + WebSocket (streamed progress)
┌────────────────────────────── BACKEND (FastAPI) ─────────────────────────────────┐
│  1. Ingestion & Validation Service                                               │
│     format/CRS/bands/extent, modality detection (optical vs SAR),                │
│     pair co-registration check, tiling, "input inventory" JSON                   │
│  2. Agent Orchestrator                                                           │
│     Planner (LLM, structured JSON plan) → Guardrail Validator                    │
│     → Executor (DAG over registered tools) → Evidence Integrator (LLM)           │
│     deterministic fallback router if planning/validation fails                   │
│  3. Evidence & Report Service (confidence, overlays, PDF, SQLite trace store)    │
└──┬──────────────┬─────────────────┬──────────────────────┬───────────────────────┘
   │              │                 │                      │
┌──▼─────────┐ ┌──▼──────────┐ ┌────▼───────────┐ ┌────────▼──────────────┐
│ T1 RS-VLM  │ │ T2 Grounding│ │ T3 Change      │ │ T4 Optical–SAR Fusion │
│ Qwen2-VL-2B│ │ Grounding-  │ │ ChangeMask:    │ │ dual-tower S1/S2      │
│ LoRA on    │ │ DINO-T      │ │ BiT/ChangeForm-│ │ encoders + Q-Former    │
│ BE.txt +   │ │ fine-tuned  │ │ er on QAG-360K │ │ → LLM adapter         │
│ RSVQA +    │ │ on VRSBench │ │ + LEVIR-CD;    │ │ + dual patch-classif. │
│ VRSBench + │ │ + BE.txt    │ │ ChangeVQA:     │ │   (built-up/water     │
│ TAMMI      │ │ refs        │ │ RS-VLM 2-image │ │   mask)               │
│ (caption,  │ │             │ │ head on CDVQA+ │ │ (joint caption/VQA/   │
│ VQA, bbox, │ │             │ │ QAG-360K +     │ │  grounding on pairs)  │
│ 2-image)   │ │             │ │ ChangeChat-105k│ │                       │
└────────────┘ └─────────────┘ └────────────────┘ └───────────────────────┘
        All tools speak one contract: structured JSON in/out + confidence + evidence ref
```

**Core design principle:** every specialist is a *registered tool* with a JSON-schema input/
output contract and a confidence field. The agent never calls models directly; it emits a
validated plan over the registry. This is what makes the execution trace auditable (a
mandatory graded artifact) and the demo bulletproof.

## 2.2 Ingestion & Validation (non-negotiable foundation)

- **Formats**: GeoTIFF/TIFF primary; PNG/JPEG accepted only when the file matches a
  benchmark path (PS rule). Validate with GDAL: CRS, geotransform, extent, pixel size,
  band count/dtypes.
- **Modality detection**: band count ≥3 → optical/multispectral (map S2 band order
  B2,B3,B4,B8…; Cartosat RGB/NIR); 1–2 bands + SAR file-signature or speckle statistics →
  SAR (take amplitude band; expose optional gamma speckle-filter).
- **Pair compatibility check** (runs for both pair types, with different logic):
  - extent overlap ratio (require ≥ 0.9 else auto-crop to common extent),
  - co-registration offset estimate: downsample both to grayscale, normalized
    cross-correlation peak → offset (px); if > 2 px, re-register with `gdalwarp`/
    `warp_affine` and log it (ISRO set is pre-registered, but hidden sets can surprise),
  - bi-temporal: extract dates from metadata/filename; compute Δt;
  - cross-modal: same extent/resolution, optical + SAR confirmed.
- **Tiling**: split large rasters into fixed **512×512 tiles (64 px overlap)** in *image
  space*, track tile→global geotransforms. This is what makes the whole stack work at both
  20 m Sentinel *and* 1 m Cartosat without retraining. All spatial outputs (boxes, masks,
  heatmaps) are stitched back to the full-image frame.
- **Input inventory** (JSON, passed to the agent): `[{file, format, crs, extent, res,
  bands, modality, date, tiles, sha256}]` + pair relation record.

## 2.3 Specialist models (the tool registry)

### T1 — RS-VLM (the mandatory adaptation component) ★
- **Base model: Qwen2-VL-2B-Instruct** (open weights). Why:
  - *native multi-image input* → the same backbone serves single-image, bi-temporal pairs,
    and optical–SAR pairs (up to N images) — one model family for most tasks;
  - *dynamic resolution* → tile-friendly, resolution-agnostic (Cartosat-safe);
  - 2B is LoRA-trainable on **one 24 GB GPU** (bf16, r=64, all-linear, freeze ViT or LoRA
    last 4 ViT blocks); 7B is a stretch upgrade with 4-bit base + LoRA on 2×24 GB;
  - bbox/grounding output formats are well-supported; served efficiently by **vLLM**.
  - *Alternative: InternVL2.5-2B* — the BigEarthNet.txt authors adapted InternVL for
    multi-sensor RS input; check the HF dataset repo for released adapters/configs and reuse
    their recipes if available (closest-to-intended use of the dataset).
- **Training mix (all open source, all PS-sanctioned):**
  | Data | Role | Scale |
  |---|---|---|
  | **BigEarthNet.txt** (train split) | primary RS adaptation: captions, binary/MCQ VQA, referring-expression (bbox) instructions; *also the S1+S2 triplets for cross-modal* | 229,114 pairs, ~4.7M annotations |
  | **VRSBench** (train split) | captioning, grounding, VQA on natural-language RS imagery | 29.6K images, 123K QA |
  | **RSVQA** | additional VQA volume | ~20K QA |
  | **TAMMI** (2025, open) | VQA over co-located **VHR RGB + multispectral + SAR** triplets — best public multi-modal VQA data; strengthens cross-modal reasoning beyond S1/S2 | 3-modality |
  | **CDVQA + QAG-360K + ChangeChat-105k** | bi-temporal head (see T3) | 2.9K pairs/122K QA; 6.8K pairs/360K triplets; 105K pairs |
- **Serves tasks**: CAPTION, VQA, GROUND (single image), CHANGE_DESC / CHANGE_VQA (2 images), CROSSMODAL_DESC / CROSSMODAL_VQA (2 images).
- **Outputs**: free text; constrained answers (yes/no, MCQ, class lists) with token-probability extraction; bbox coordinates for grounding-format prompts.
- **Proof of adaptation**: run zero-shot vs LoRA-tuned on the VRSBench/RSVQA/CDVQA test
  splits and ship that table in your report.

### T2 — Grounding (text-guided region grounding)
- **Base: Grounding-DINO-T**, fine-tuned on: VRSBench object references (52,472 refs),
  BigEarthNet.txt referring-expression instructions, + ADE20K-GS slice for natural-scene
  robustness.
- Prompt pattern: detect `"water body"` etc. → boxes + scores per tile → NMS + stitch to
  full-image coordinates → overlay. (Query phrasing → phrase normalization via the planner.)
- Optional upgrade if time permits: **FERoT** (unified EO detection/segmentation foundation
  model) — but Grounding-DINO is the pragmatic, well-trodden choice.

### T3 — Change pipeline (bi-temporal; mandatory)
Two cooperating tools:
1. **ChangeMask** — change-detection backbone (**BiT** or ChangeFormer/FC-EF) fine-tuned on
   **QAG-360K** (masks for 10 LULC classes) + **CDVQA** (semantic change maps) +
   LEVIR-CD/WHU-CD for volume. Outputs per-pixel change map (+optional per-class transition
   map). This is the "spatial change map where reference masks are available" requirement.
2. **ChangeVQA** — the RS-VLM in 2-image mode, fine-tuned on CDVQA (122K QA) + QAG-360K
   {Q,A,mask} triplets + ChangeChat-105k (6 interaction types incl. captioning &
   quantification — great for "increased/decreased/unchanged" style questions).
- **Workflow for "what changed and where"**: ChangeMask → aggregate structured summary
  (changed-area px/%, dominant class transitions, top change polygons with centroids in
  geo-coordinates) → feed {img_t1, img_t2, summary} to ChangeVLM → natural-language answer
  *with locations*; overlay change map in UI. For "Has built-up increased?": mask-based
  area diff per class gives the numeric answer, VLM narrates it (answers grounded in the
  mask, not hallucinated).

### T4 — Optical–SAR cross-modal (mandatory)
1. **Fusion encoder → LLM adapter** (BLIP-2-style Q-Former):
   - optical tower: ViT pretrained on S2/EO data (or DINOv2 features for RGB subsets);
   - SAR tower: ViT pretrained on SAR (SEN2SAR / SARImageNet / Daudt weights) or scratch —
     SAR needs its own encoder; late-concatenation alone is weak for joint reasoning;
   - cross-attention fusion block → 64–256 visual tokens → LLM (shared with T1's decoder).
   - **Train on BigEarthNet.txt S1–S2–text triplets (229K pairs!) + TAMMI.** This is the
     cleanest possible training signal in the entire problem statement.
   - Serves: joint captions ("built-up on optical + strong backscatter on SAR in the NE"),
     cross-modal VQA, cross-modal grounding.
2. **Dual-input patch classifier** (optical + SAR, dB-normalized) trained on BigEarthNet v2
   **patch-level** LULC labels → per-tile built-up/water **presence scores**. Answers the
   representative query "Use the optical and SAR images together to identify built-up and
   water-covered regions" with a tile-presence heat layer plus grounding boxes.
   > **Corrected (v1.1):** the earlier "per-pixel joint masks / mIoU ≥ 0.80" claim is
   > **unsupported** — BigEarthNet v2 ships patch-level multi-labels, not per-pixel masks.
   > Metric is patch F1/mAP. See `architecture.md` §7.2. A true dense mask would require a
   > dense-segmentation dataset (LoveDA / OpenEarthMap) and is out of scope for 20 Sep.
3. Confidence synergy (nice judging point): when optical and SAR evidence agree (e.g., both
   indicate water / both indicate built-up backscatter) → boost reported confidence;
   disagreement → flag it explicitly in the answer ("SAR shows flooded surface while
   optical shows open water — likely recent inundation").

### T5 — Evidence & confidence utilities
- **Visual evidence**: Grad-CAM/attention-rollback crops around each claim; grounding boxes;
  change masks; fusion attention maps. Stored as overlay layers per request.
- **Confidence** (per tool → aggregated):
  - detector/segmentation: box score / mean pixel-probability margin;
  - VQA: token-level probability of the answer span (high for constrained answers;
    verbalized + calibrated on a held-out set for open answers);
  - change: mask probability margin + area stability;
  - cross-modal: agreement factor between the two modalities' per-class outputs;
  - final: conservative aggregation (e.g., weighted geometric mean) + a 3-level badge
    (high/medium/low) in the UI.

## 2.4 Agent Orchestrator (the graded novelty — build it for reliability first)

**Planner**
- Model: **Qwen2.5-7B-Instruct (4-bit)** — or reuse the RS-VLM itself (it already does
  tool-call JSON well after fine-tuning). Prompt contains:
  - the *tool registry* (name, capability tags, JSON schemas, 1–2 examples each),
  - the *input inventory* from the validation service,
  - the *task taxonomy*: `CAPTION | VQA | GROUND | CHANGE_DESC | CHANGE_VQA | CHANGE_MAP |
    CROSSMODAL_DESC | CROSSMODAL_VQA | CROSSMODAL_MASK | MULTI_STEP`,
  - output = JSON plan: `[{step, tool, params, depends_on, expected_output}]`.
- Multi-step plans are first-class: e.g., *"Describe this area and highlight the water
  body"* → `[CAPTION(T1), GROUND(T2, phrase="water body"), INTEGRATE]`.

**Guardrails (deterministic — this is what saves your demo)**
1. Input-scope pre-check (hard constraints):
   - 1 optical → allowed tasks: CAPTION/VQA/GROUND;
   - 1 SAR → same; 2 same-modality (dates differ) → CHANGE_*;
   - optical + SAR (same extent) → CROSSMODAL_* (+ joint VQA/caption/grounding);
   - mismatched pair → the agent must return a *polite incompatibility report*, not crash.
2. Plan JSON-schema validation; parameter whitelist (only permitted task parameters, per PS).
3. **Fallback router**: if the LLM plan fails validation (or times out), a keyword+scope
   rule table deterministically picks a plan. The user never sees a failure.
4. Every parameter, input hash, output, and latency is written to the trace.

**Executor** — sequential/parallel DAG over registered tools; per-step timeout + 1 retry;
structured outputs only; tool outputs kept as JSON (the integrator never re-runs models).

**Integrator** — LLM call, strict prompt: "answer ONLY from the provided tool outputs +
images; cite which tool produced each claim; state confidence; do not invent details."
Produces final answer + evidence citations + confidence badge.

**Auditable execution trace** (per PS: "selected task, model/tool names, and key
parameters") — rendered in a dedicated UI panel and embedded in the PDF report:

```
Task: CHANGE_VQA        Planner: qwen2.5-7b (ok, 1.2s)
S1 change-mask     BiT-v2       tile=512, thr=0.5        → 12.4% area, built-up +8.1%  (conf 0.87)
S2 change-vqa      RS-VLM-2B    mode=2img, temp=0.3       → answer text                    (conf 0.81)
S3 integrate       qwen2.5-7b   context=2 tools           → final answer                   (conf 0.82)
Total: 14.8s   Evidence: 2 overlays + 1 change map
```

## 2.5 Frontend

- **Stack**: React + Vite + Tailwind; **Konva** for overlays (boxes/masks/heatmaps with
  toggles and per-layer confidence). (Streamlit is a faster fallback if the team is small —
  acceptable, but a real web app scores better on "interactive GUI or web application".)
- Flow: upload (1 or 2) → **metadata cards** auto-populate (detected modality, extent,
  resolution, date, co-registration status, tile count) → chat → answer card
  (text + overlay toggles + confidence badge) → expandable execution trace → **Download
  PDF report** (images with overlays, trace table, confidence, model versions).
- WebSocket stream: "planning… → running tool 2/3… → integrating…" (shows the agent alive).

## 2.6 Backend & deployment

- **Python 3.11, FastAPI, Pydantic v2, SQLite** (trace store — small and auditable),
  GDAL/rasterio, vLLM (T1 + planner), HF Transformers (others).
- **Serving options**:
  - *Minimum (1× RTX 4090 24 GB)*: lazy-load + model offload; serve T1 via vLLM with
    `--gpu-memory-utilization 0.7`, swap in T2/T3/T4 sequentially. Works; slower.
  - *Recommended (2× 24 GB)*: GPU-A = vLLM (RS-VLM + planner); GPU-B = grounding + change
    + fusion/UNet (small models, fast).
- **Docker Compose**: `frontend`, `api`, `models` (volume with weights) — fully offline;
  all weights vendored as a tarball (this is also your submission artifact).
- **Latency targets** (4090, tiling, 1024×1024 image): single VQA < 8 s; caption < 6 s;
  grounding < 8 s; change pipeline < 15 s; cross-modal < 15 s.

## 2.7 Internal benchmark harness (build in week 1)

Mirror the evaluation the judges will run, so you can iterate with numbers:

| Task | Benchmark | Metrics |
|---|---|---|
| Captioning | VRSBench test | CIDEr, BLEU-4, METEOR, ROUGE-L |
| Grounding | VRSBench refs | box IoU ≥ 0.5 accuracy, COCO AP |
| Single VQA | VRSBench + RSVQA test | exact match, soft accuracy (constrained) |
| Change VQA | CDVQA test (+ QAG-360K holdout) | exact match over answer categories |
| Change map | CDVQA/QAG-360K | IoU, F1, mIoU |
| Cross-modal | BigEarthNet.txt benchmark split (1,082 pairs) | their 15-task suite + built-up/water patch F1 + optical/SAR/fused ablation |

Report **zero-shot → adapted** deltas per task — that table *is* your compliance proof for
"remote-sensing fine-tuning or domain adaptation".

## 2.8 Work plan — SUPERSEDED

> **This 6-week plan does not apply.** The real calendar is **5 Sep pitch (PPT) → 20 Sep final
> (PPT + code + models)** — 15 days of build, not 6 weeks. The binding schedule is
> `checkpoints.md` §G, with the model triage in `architecture.md` §7.1 (**three trained models:
> M1, M4, M3** — not seven). The table below is retained only as a shape reference for what a
> full-length run *would* look like.

### (retained for reference — do not schedule from this)

| Week | Deliverable |
|---|---|
| 1 | Data pipelines: download BigEarthNet.txt (HF), VRSBench, RSVQA, CDVQA, QAG-360K, ChangeChat-105k, TAMMI; convert to chat/JSONL formats; QC sample; eval harness skeleton with metrics |
| 2 | T1 RS-VLM LoRA (BE.txt + VRSBench + RSVQA + TAMMI) — the biggest job; baseline numbers before/after |
| 3 | T2 grounding fine-tune; T3 change (BiT fine-tune + 2-image VLM head on CDVQA/QAG-360K/ChangeChat); T4 fusion + UNet (BE.txt S1-S2 + TAMMI) |
| 4 | Agent: registry, planner, guardrails, fallback router, executor, integrator, trace store; FastAPI wiring; PDF report |
| 5 | Frontend (overlays, trace panel, metadata cards); end-to-end on all 5 representative queries; stress on Cartosat-2S + RISAT-1 public samples (test the resolution/SAR domain gap!) |
| 6 | Polish, Docker, demo script, benchmark table, docs; dry runs on a borrowed GPU |

**On-site (36–48 h)**: integration fixes, demo rehearsals, live-data testing with the
evaluator, report generation, submission packaging.

## 2.9 Demo script (the 5 graded capabilities, verbatim PS queries)

1. Single optical (or SAR): *"Describe the land-cover and major objects visible in this
   image."* → T1 caption (+ T2 bonus boxes).
2. *"Highlight the water body referred to in the query."* → T2 grounding overlay.
3. Bi-temporal pair: *"What changed between these two dates, and where did the change
   occur?"* → T3 mask + ChangeVQA answer with coordinates.
4. Optical + SAR pair: *"Use the optical and SAR images together to identify built-up and
   water-covered regions."* → T4 dual-UNet masks + joint caption.
5. Bi-temporal: *"Has the built-up area increased, decreased, or remained unchanged?"* →
   mask area-diff number + VQA answer.
6. **Closer (compound, shows the agent)**: *"Describe both scenes, tell me what changed,
   and highlight the new built-up areas."* → 4-step plan executed with visible trace.
   Always keep the execution-trace panel open during the demo — it is the graded novelty.

## 2.10 Risks & mitigations

| Risk | Mitigation |
|---|---|
| Metrics/weights unknown (PS table placeholder) | Standard metrics + self-explaining report; make every answer carry visible confidence + evidence |
| Hidden set is ~1 m Cartosat + L-band RISAT (domain gap vs Sentinel training) | Tile-based, resolution-agnostic design; test on public Cartosat-2S/RISAT samples in week 5; SAR tower handles L-band amplitude fine (pretrain on mixed SAR) |
| BigEarthNet.txt pipeline immature / huge download | Start download day 1; QC templates early; fallback data ready (reBEN, Sentinel2Cap, BE v2 + generated text) |
| GPU unavailable/limited at SIH | 2B VLM + 4-bit planner fits 1×24 GB; vendored weights tarball; quantized fallbacks |
| Agent fails mid-demo | Deterministic fallback router; schema-validated plans; rehearsed exact queries; "incompatibility report" path instead of crash |
| Pair not perfectly co-registered in hidden set | Offset estimator + auto re-registration step, logged in trace (turns a risk into a feature) |
| VLM hallucination in answers | Integrator restricted to tool outputs; numeric answers (areas, counts) always computed from masks/detectors, never generated |

---

## Appendix A — Verified dataset facts (as of 3 Sep 2026)

- **BigEarthNet.txt** — Herzog et al., arXiv:2603.29630 (31 Mar 2026), TU Berlin/BIFOLD.
  464,044 co-registered S1 (Sentinel-1 SAR) + S2 (Sentinel-2 MS) pairs; ~9.6M text
  annotations; 15 tasks / 4 categories (captioning, binary VQA, MCQ VQA, referring-
  expression detection); splits 229,114 / 118,095 / 116,835 pairs; manually-verified
  benchmark split = 1,082 pairs, 15,029 annotations (970 captions, 6,927 binary, 5,550 MCQ,
  1,582 referring). CC-BY 4.0. Download: huggingface.co/datasets/BIFOLD-BigEarthNetv2-0/BigEarthNet.txt
  Paper adapts **InternVL** to multi-sensor RS input → check their repo for released recipes.
- **VRSBench** — Li, Ding, Elhoseiny, NeurIPS 2024 Datasets & Benchmarks, arXiv:2406.12384.
  29,614 images; 29,614 human-verified captions; 52,472 object references; 123,221 QA pairs.
  Captioning + visual grounding + VQA. Code: github.com/lx709/VRSBench
- **CDVQA** — Yuan et al., TGRS 2022, arXiv:2112.06343. 2,968 bi-temporal pairs (SECOND,
  512×512), 122K+ generated QA pairs, pixel-level semantic change maps.
  Code/data: github.com/YZHJessica/CDVQA
- **RSVQA** — the classical remote-sensing VQA dataset (Wang et al.); PS-named benchmark.
  Newer public additions worth training on: **RSVLM-QA** (13,820 images, 162,373 QA, 2025)
  and **TAMMI** (co-located VHR RGB + multispectral + SAR VQA, 2025 — ideal for optical–SAR).
- **Auxiliary (PS-allowed "any open source training data")**: QAG-360K (6,810 pairs,
  360K {Q,A,mask}, 10 LULC classes), ChangeChat-105k (105,107 bi-temporal pairs, 6
  interaction types, masks), LEVIR-CD, WHU-CD, ADE20K-GS, Sentinel2Cap (human S1+S2
  captions), reBEN.
