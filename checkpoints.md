# SatQuery AI — Checkpoints & Master Checklist (PS 26167)

**Purpose:** nothing slips. Update statuses daily; owner + date on every change.
**Legend:** ☐ open · ◐ in progress · ☑ done · ✗ blocked (write why) · ➖ N/A
**Companions:** `ps-26167.md` (**official PS — source of truth**) · `budget.md` (**₹0 constraint**) · `architecture.md` · `design.md` · `satquery-ai-architecture.md`

> Today: **3 Sep 2026**.
>
> **Two deadlines, two graded artifacts — do not conflate them:**
>
> | Window | Ends | Graded | Prototype |
> |---|---|---|---|
> | **A** | **5 Sep, 10:00** | **PPT** | bonus points only |
> | **B** | **20 Sep** | **PPT + code + models** | mandatory |
>
> Window A ≈ 46 h. Window B = 15 days. See §G for the split schedule and
> `architecture.md` §7.1 for the binding model triage (3 trained models, not 7).

---

## 0. Facts to confirm (do in week 1, official SIH/ISRO channels)

| # | Question | Why it matters | Status |
|---|---|---|---|
| 0.1 | ~~What "20 Sep 2026" means~~ — **RESOLVED: 5 Sep 10:00 = Round-1 PPT pitch (prototype = bonus); 20 Sep = final submission of PPT + code + models.** | schedules everything | ☑ |
| 0.2 | Evaluation-criteria table — **CONFIRMED as a placeholder in the official PS itself** ("Add 'Evaluation/Judging Criteria' table here"). Metric names + weights are genuinely unpublished, not just missing from our copy. Watch for an amendment; do not block on it. | eval harness targets | ◐ |
| 0.3 | Hardware at venue — **assume none provided.** ₹0 budget: we bring our own laptop, CPU inference. Confirm Kaggle/Colab free-tier quotas are still live (they change without notice). | `budget.md` §4–§5 | ◐ |
| 0.4 | Internet at judging/eval time? | assume **none**; verify | ☐ |
| 0.5 | How is the web app judged — our machine, their infra, or submitted build? | Docker packaging + port binding | ☐ |
| 0.6 | How are benchmark test subsets run — our script on our hardware, or theirs on ours? | `eval/` CLI contract | ☐ |
| 0.7 | Any model-size/latency limits stated in full PS? | M1 2B vs 7B decision | ☐ |
| 0.8 | Is a recorded video an accepted demo backup? | kill-switch plan | ☐ |
| 0.9 | RSVQA + VRSBench exact splits — **the official PS Dataset Link text is itself truncated mid-sentence ("VRSBench — for")**. Links are incomplete in the source, not our copy. Use the papers' canonical splits and document the choice. | data prep | ◐ |
| 0.10 | ~~BigEarthNet.txt layout/license~~ — **RESOLVED:** single `BigEarthNet.txt.parquet` (467 MB, 9.55M rows), license **CDLA-Permissive-1.0** (not CC-BY), `split` column carries train/val/test, official `ben_txt_datamodule.py` loader shipped in-repo. Remaining: check for released InternVL adapters. | M1 training | ◐ |
| 0.11 | **BIFOLD-BigEarthNetv2-0 pretrained weights — 30 checkpoints** (10 architectures × S1-only / S2-only / S1+S2), HF org `BIFOLD-BigEarthNetv2-0`. Reference `resnet50-all-v0.2.0`: mAP macro **0.7107** / micro **0.8593**, 23.6 M params, safetensors. Four uses, zero GPU cost: (1) the S1/S2/S1+S2 trio **is** the optical/SAR/fused ablation with real numbers — panel unblocked for 5 Sep without training; (2) one genuinely trained 19-class land-cover tool in the Window A prototype; (3) RS-pretrained S1+S2 encoder init for M7 (replaces ImageNet init in the M7 row below); (4) co-registered dual-modality encoder already trained. **Constraints:** band order is version-critical — v0.2.0 = `[VV, VH, B02, B03, B04, B05, B06, B07, B08, B8A, B11, B12]`; v0.1.1 order differs and is incompatible (wrong order = confident garbage, no error) → pin v0.2.0 and assert order in ingestion. Patch-level multi-label, **not** segmentation. Not plain `AutoModel` — needs `pip install configilm` + the `reben_publication` model code from `git.tu-berlin.de/rsim/reben-training-scripts`. Trained at 120×120 px @ 10 m Sentinel; hidden set ~1 m Cartosat → C7 domain gap unchanged. **Compliance caution (PS A1.1):** third-party pretrained weights are a backbone, not adaptation *by us* — M1 LoRA stays the compliance artifact; state on the slide that these are an accelerator underneath our adaptation. **TODO: verify each weight repo's license before submission** (dataset is CDLA-Permissive-1.0; the 30 model repos are licensed separately and must be checked one by one). | ablation, prototype, M7 init | ◐ |

---

## A. Problem-statement compliance matrix (the graded contract)

Every PS "shall/must" → where handled → evidence artifact → status.

> **PS priority (verbatim):** *"Single-image understanding is a mandatory **baseline**, while the
> **principal focus** is joint reasoning over paired cross-modal and multitemporal imagery."*
> A1.4 and A1.6 therefore carry more weight than A1.2/A1.3. Budget accordingly.

### A.1 Mandatory functional scope
| # | PS requirement | Handled by | Evidence | Status |
|---|---|---|---|---|
| A1.1 | ≥1 visual/VL component fine-tuned/adapted on BigEarthNet.txt or open RS data — **must be OUR weights on OUR GPU; a hosted generic API (OpenRouter/HF Inference) fails PS P12** (`budget.md` §6.2b) | M1 (also M3,M4,M7) LoRA | training logs + **zero-shot vs adapted** benchmark table + adapter hashes in report | ☐ |
| A1.2 | Single-image **VQA mandatory** | `vqa` (M1) | demo Q2 + VRSBench/RSVQA test numbers | ☐ |
| A1.3 | + captioning **or** grounding (we do both) | `caption` (M1), `ground` (M3) | demo Q1, Q3 + numbers | ☐ |
| A1.4 | Bi-temporal change description **or** change-VQA mandatory | `change_map`+`change_vqa` (M4,M5) | demo Q5 + CDVQA test numbers | ☐ |
| A1.5 | Spatial change map where reference masks available | M4 mask overlay + facts | overlay in UI + PDF | ☐ |
| A1.6 | Cross-modal optical–SAR: extract **complementary** information from a co-registered pair | `xmodal_*` via **M1 2-image mode + M7 masks + §7.3 ablation** (M6 = optional upgrade) | demo Q4 + BE.txt benchmark-split numbers + **ablation proving SAR contributes** | ☐ |
| A1.7 | Agentic orchestration: select/sequence/execute specialist models per query + inputs | Planner+Registry+Executor | **compound demo Q6** (multi-step) + trace | ☐ |

### A.2 Agent controller duties (PS bullet list)
| # | Duty | Handled by | Evidence | Status |
|---|---|---|---|---|
| A2.1 | Interpret query, classify task | M2 planner, taxonomy in plan JSON | `task` field in every trace | ☐ |
| A2.2 | Check number/modality/format/metadata/compatibility of inputs | Ingestion service | reject-card demos (2 cases) + inventory JSON | ☐ |
| A2.3 | Select models/tools **from a predefined registry** | `registry.yaml` + `GET /tools` | registry file + endpoint | ☐ |
| A2.4 | Configure **only permitted** task parameters, execute workflow | param whitelist in guardrail | params logged per step in trace | ☐ |
| A2.5 | Combine textual + spatial outputs, estimate confidence, return visual evidence | integrator + T5 + overlays | answer card + PDF | ☐ |
| A2.6 | Auditable execution summary: task, model/tool names, key parameters | trace panel + PDF §4 + `trace.json` | every DONE request | ☐ |

### A.3 Input scope
| # | Requirement | Status |
|---|---|---|
| A3.1 | Single optical/multispectral image (GeoTIFF/TIFF) | ☐ |
| A3.2 | Single SAR image (GeoTIFF/TIFF) | ☐ |
| A3.3 | Co-registered optical–SAR pair | ☐ |
| A3.4 | Bi-temporal pair (spatially corresponding) | ☐ |
| A3.5 | PNG/JPEG **only** for prescribed benchmark datasets (allow-list gate) | ☐ |

### A.4 "Solution should include"
| # | Item | Status |
|---|---|---|
| A4.1 | Input upload + compatibility checking | ☐ |
| A4.2 | RS-adapted vision-language component | ☐ |
| A4.3 | Specialist tools: VQA, captioning/grounding, change understanding, optical–SAR | ☐ |
| A4.4 | Agentic controller: task routing, tool execution, output integration | ☐ |
| A4.5 | Visual evidence + confidence + execution summaries + downloadable report | ☐ |

### A.5 Mandatory demonstrations (demo script = these, verbatim PS queries)
| # | Demo | PS query | Status |
|---|---|---|---|
| A5.1 | single-image VQA **(mandatory baseline)** | PS gives no verbatim single-image VQA query — use a benchmark-style one, e.g. "Is there a water body in this image?" / "What is the dominant land-cover type?" | ☐ |
| A5.2 | additional single-image task (caption + grounding) | "Describe the land-cover and major objects…" / "Highlight the water body referred to in the query." | ☐ |
| A5.3 | multitemporal change understanding | "What changed between these two dates, and where did the change occur?" | ☐ |
| A5.4 | optical–SAR pair analysis | "Use the optical and SAR images together to identify built-up and water-covered regions." | ☐ |
| A5.5 | agentic orchestration (compound, multi-step) | "Describe both scenes, tell me what changed, and highlight the new built-up areas." | ☐ |
| A5.6 | trend query (mask-computed number + VLM narration) | "Has the built-up area increased, decreased, or remained unchanged?" | ☐ |

### A.6 Deliverables
| # | Item | Status |
|---|---|---|
| A6.1 | Interactive GUI/web app + agentic RS-AI backend | ☐ |
| A6.2 | Code (repo, README, 1-command run) | ☐ |
| A6.3 | Models (weights + cards + hashes) | ☐ |
| A6.4 | Tests — **PS deliverable names "test" explicitly**: pytest unit + integration + test matrix §E, with a runnable command and committed output | ☐ |
| A6.5 | Demonstration (live + ≤5 min video backup) | ☐ |
| A6.6 | Eval runs on prescribed public benchmark test subsets (logs + tables) | ☐ |

### A.7 Evaluation-readiness
| # | Item | Status |
|---|---|---|
| A7.1 | Works on **pre-georeferenced, co-registered Cartosat-2S + RISAT** pairs (hidden set) | ☐ (test on public samples / proxies: 1 m VHR optical + L-band SAR) |
| A7.2 | Resolution-agnostic (1 m ↔ 20 m) via tiling | ☐ |
| A7.3 | Works offline, vendored weights | ☐ |
| A7.4 | Report + trace present for every evaluated request | ☐ |

---

## B. Data checkpoints

| Dataset | Source | Scale | Download | License | QC (format, splits, sample render) | Converter → unified JSONL | Stored @ /data/datasets |
|---|---|---|---|---|---|---|---|
| **BigEarthNet.txt** (PRIMARY) | HF `BIFOLD-BigEarthNetv2-0/BigEarthNet.txt` — **single 467 MB parquet, 9.55M rows, text only** | take **all rows**; join to a stratified ~40K-patch imagery subset via `patch_id` | ☐ | CC-BY 4.0 ☐ | ☐ | ☐ | ☐ |
| VRSBench | github.com/lx709/VRSBench | 29,614 img, 123,221 QA, 52,472 refs | ☐ | ☐ | ☐ (verify official train/test split assignment) | ☐ | ☐ |
| RSVQA | PS link / official repo | ~20K QA | ☐ | ☐ | ☐ | ☐ | ☐ |
| CDVQA | github.com/YZHJessica/CDVQA | 2,968 pairs (512²), 122K QA | ☐ | ☐ | ☐ | ☐ | ☐ |
| QAG-360K | VisTA repo (arXiv 2410.23828) | 6,810 pairs, 360K {Q,A,mask} | ☐ | ☐ | ☐ | ☐ | ☐ |
| ChangeChat-105k | its repo (2025) | 105K bi-temporal pairs | ☐ | ☐ | ☐ (optional — cut if time) | ☐ | ☐ |
| TAMMI | tammi.sylvainlobry.com | VHR+MS+SAR VQA triplets | ☐ | ☐ | ☐ | ☐ | ☐ |
| ADE20K-GS | (slice) | grounding aux | ☐ | ☐ | ☐ | ☐ | ☐ |
| LEVIR-CD / WHU-CD | open | change pretrain | ☐ | ☐ | ☐ | ☐ | ☐ |
| Domain-gap test set: Cartosat-2S samples + RISAT samples (or proxies: ISPRS Vaihingen ~0.3 m, Daudt/SAR-GSB) | ISRO/RESRDA + open sources | ~20 pairs | ☐ | ☐ | ☐ | — | ☐ |

Data rules:
- ☐ Disk: **5 TB available**, but **the 118 GB pull is now optional** — BE.txt is a 467 MB parquet; profile it with DuckDB, select patch_ids, fetch only ~10–15 GB of imagery (`budget.md` §3.0). Working set to a Kaggle Dataset by D3.
- ☐ Benchmark **test splits never enter training** (track file lists in `eval/splits.json`)
- ☐ `docs/datasets.md` written: per-dataset license + usage + citation (required for submission)

---

## C. Model checkpoints (fill numbers at eval-gate)

Per model: base weights ☐ · adapter/weights path ☐ · training config committed ☐ · run log ☐ · **eval gate passed** ☐ · model card (version, hash, data, metrics) ☐

| Model | Role | Base | Train data | Eval gate (zero-shot → target) | Gate passed |
|---|---|---|---|---|---|
| M1 RS-VLM | vqa/caption/2-image heads | Qwen2-VL-2B + LoRA(r64) | BE.txt 100K subset + VRSBench + RSVQA + TAMMI | VRSBench-VQA EM +≥5 vs zero-shot; CIDEr +≥10; BE.txt bench-split ≥ paper tuned baseline where comparable | ☐ |
| M2 Planner/Integrator | plan, integrate | Qwen2.5-7B-4bit | 200-query suite | plan schema-valid ≥98%; task accuracy ≥95%; fallback rate ≤2% | ☐ |
| M3 Grounding | ground | Grounding-DINO-T | VRSBench refs + BE.txt referring + ADE20K-GS | VRSBench-refs IoU≥0.5 acc ≥ published baseline | ☐ |
| M4 Change backbone | change_map | BiT (ViT-B) | QAG-360K + CDVQA + LEVIR-CD | CDVQA change-map IoU ≥ baseline (VisTA 17.7 mIoU ref) | ☐ |
| M5 Change-VQA | change_vqa | M1 2-image | CDVQA + QAG-360K + ChangeChat-105k | CDVQA-test EM ≥ VisTA-text-level ref (62.5) | ☐ |
| M6 Fusion | xmodal | dual ViT + Q-Former | BE.txt S1–S2–text + TAMMI | BE.txt bench-split avg ≥ best single-modality; TAMMI VQA +≥5 vs optical-only | ☐ |
| M7 Dual UNet++ | xmodal_mask | **BIFOLD `resnet50-all-v0.2.0` S1+S2 encoder init** (was ImageNet; see 0.11) | BE v2 **pixel-level reference maps** (CLC2018) + S1/S2 | built-up/water **mIoU ≥ 0.60 pass / ≥ 0.70 good** (the old ≥0.80 gate was unjustified; report per-class IoU — see arch §7.2) | ☐ |

- ☐ M1: confirm whether BE.txt authors released InternVL adapter/code — if yes, rerun gate with InternVL2.5-2B and pick winner
- ☐ All adapters recorded with SHA-256 in `models/MODEL_CARDS.md`

---

## D. System checkpoints

**Ingestion**
- ☑ Ingestion scaffolded + unit-tested in `prototype/` (4 Sep): rasterio load, format allow-list (`E_FORMAT`), modality detector, **v0.2.0 band-order hard assertion**, tiling pixel-exact coverage test, synthetic coreg shift detection test. Remaining: modality detector ≥98 % on the 50-image real test set; auto re-registration (currently detects + warns).
- ☑ Coreg offset detection: synthetic 0/6 px shift test passes (`test_ingestion.py`); auto-register action pending
- ☑ Tiling round-trip: pixel-exact coverage asserted in tests (no-overlap case)
- ☑ PNG/JPEG/TIFF allow-list gate implemented in `ingestion.load_raster`

**Agent**
- ☑ Registry: **8 tools** + schemas + examples in `prototype/config/registry.yaml`; `GET /tools` serves it; tested (`test_registry.py`). (M5 = M1 2-image mode, not a 9th tool.)
- ☐ Planner suite: 200 queries (40/task incl. multi-step & invalid) → accuracy + schema-validity logged — RuleRouter keyword suite exists; expand to 200
- ◐ Guardrail: empty/over-long query + format rejection live; 50 crafted invalid plans suite pending
- ☑ Fallback router: RuleRouter covers all tasks with 100 % routing (unmatched → VQA baseline) + modality gating diverts xmodal/change safely; `fallback_used` recorded in every trace
- ◐ Executor: tool exceptions ⇒ graceful degraded answer (tested); per-step 30 s timeout + 1 retry pending
- ☑ Param whitelist enforced (PS A2.4) — orchestrator strips non-schema params

**Trace & report**
- ☐ Every DONE request ⇒ complete trace (A2.6 fields) + `trace.json` + PDF ≤3 MB
- ☐ PDF contains: query, metadata, answer+confidence, overlays, auditable step table, model versions

**Frontend**
- ☐ All overlay layer types render (bbox/masks/heatmap/annotations) with legend + toggles
- ☐ Trace panel (expandable rows, JSON export), metadata cards, pair banner (green/amber/red)
- ☐ Demo mode: sample data + 5 query chips + "Run full walkthrough"
- ☐ Edge-case cards per design.md §11 (8 cases)

**Deployment**
- ☐ `docker compose up` cold start <10 min; `/warmup` loads all weights
- ☐ Offline verified: egress blocked → full run works, zero external calls
- ☐ Latency budgets (arch §10): single ≤8 s, change ≤15 s, xmodal ≤15 s (median, p95 logged)
- ☐ **RTX 4050 6 GB run works** (`budget.md` §5) — lazy-load-and-evict, no OOM across all 6 demo flows back-to-back; `--device cpu` path also verified for judges without a GPU

---

## E. Test matrix (pytest + manual; each row = one integration test)

| # | Input | Query | Expected | Status |
|---|---|---|---|---|
| E1 | 1 optical GeoTIFF | "Describe the land-cover and major objects…" | caption + facts; trace ok | ☐ |
| E2 | 1 optical GeoTIFF | VQA ("What is the dominant cover?") | constrained answer + conf | ☐ |
| E3 | 1 optical | "Highlight the water body referred to in the query." | bbox overlay + label | ☐ |
| E4 | 1 SAR GeoTIFF | "Describe this image." | caption; modality=SAR stated | ☐ |
| E5 | 2 optical, Δt=1032 d | "What changed… and where?" | change map + answer with locations | ☐ |
| E6 | 2 optical, Δt>0 | "Has built-up increased, decreased, or remained unchanged?" | mask-computed number + narration | ☐ |
| E7 | optical + SAR co-reg | "…identify built-up and water-covered regions." | dual masks + joint caption | ☐ |
| E8 | optical + SAR disjoint | any | REJECTED card `E_PAIR_MISMATCH` | ☐ |
| E9 | PNG (VRSBench dir) / PNG (elsewhere) | any | accept / `E_FORMAT` | ☐ |
| E10 | 20k px raster | any | tiling notice; stitched overlay exact | ☐ |
| E11 | bi-temporal, no dates | change query | works + direction-uncertainty note | ☐ |
| E12 | pair, 3 px offset | any | auto re-register + trace entry | ☐ |
| E13 | injected invalid plan | any | fallback_used=true, still answers | ☐ |
| E14 | M3 killed | grounding query | degraded answer + flag, no crash | ☐ |
| E15 | 2 concurrent requests | any | queued, no GPU OOM | ☐ |

---

## F. Benchmark evidence (fill before submission)

| Task | Benchmark (prescribed test split) | Metric | Zero-shot | Adapted | Target met |
|---|---|---|---|---|---|
| Captioning | VRSBench test | CIDEr / BLEU-4 / METEOR | | | ☐ |
| Grounding | VRSBench refs | IoU≥0.5 acc / COCO AP | | | ☐ |
| Single VQA | VRSBench + RSVQA test | exact match / soft | | | ☐ |
| Change VQA | CDVQA test | exact match | | | ☐ |
| Change map | CDVQA / QAG-360K holdout | IoU / F1 / mIoU | | | ☐ |
| Cross-modal | BE.txt benchmark split (1,082 pairs) | 15-task suite + built-up/water mIoU + **optical/SAR/fused ablation** (arch §7.3) | | | ☐ |

- ☐ Eval CLI reproduces all rows: `python -m eval.run --split <name> --out eval/results/`
- ☐ Results tables rendered into report + final submission doc

---

## G. Schedule — two windows

### WINDOW A — now → 5 Sep 10:00 (~46 h). Graded artifact = **the PPT**.

**Split the team. Do not let all five people touch the deck.**

**Deck squad (3 people)** — the deck is graded and needs ~30 collective hours, not 6:
- ☐ PS 26167 → six mandatory capabilities, one slide each, no filler
- ☐ `architecture.md` §3 system diagram — full slide, your strongest asset
- ☐ M1–M7 model × dataset table — the proof you are not a GPT wrapper
- ☐ **Execution-trace mockup slide** — the graded novelty; show it literally
- ☐ SAR-is-not-RGB slide (`architecture.md` §5.1) — differentiator vs other teams
- ☐ Honest 5 → 20 Sep plan slide with the 3-model triage. Judges reward a credible
      15-day schedule over a claim that it is already finished.
- ☐ Q&A prep: "which base model / what data / what if the planner fails / how is SAR handled"

**Prototype squad (2 people)** — thin, but *real where it counts*; this is Window B's skeleton:
- ☐ REAL: rasterio ingestion — format/CRS/bands/modality/co-reg/tiling → Input Inventory
- ☐ REAL: `registry.yaml` + `GET /tools`
- ☐ REAL: **RuleRouter only** (canonical table, arch §6) — *skip the LLM planner entirely*
- ☐ REAL: SQLite trace store + trace panel
- ☐ REAL: Streamlit/Gradio UI — upload, answer card, overlay toggles, trace open by default
- ☐ HEURISTIC (declare it): change mask via NDVI/NDBI delta + threshold; precomputed
      grounding boxes on 3–5 demo scenes; canned confidence
- ☐ Cached-answer **kill switch** — non-negotiable
- ☐ On-stage line: *"the orchestration layer is real; specialist models are fine-tuned by 20 Sep"*

**4 Sep:** deck polish + demo hardening. **5 Sep 09:00:** dry run. **10:00:** present.

---

### WINDOW B — 5 Sep → 20 Sep (15 days). Graded artifact = **PPT + code + models**.

Model scope is fixed by `architecture.md` §7.1: **train M1, M4, M3. Reuse M1 for M5. Prompt-only
M2. M6 stretch. M7 patch-level.**

**D1–D4 (5–8 Sep) — data + M1 launch**
- ☐ **BE.txt download starts hour one** (hundreds of GB — this is the critical path)
- ☐ Repo scaffold (arch §12); swap the Window-A prototype's stubs behind the real contract
- ☐ Converters: BE.txt / VRSBench / RSVQA / CDVQA → unified JSONL; QC render
- ☐ Eval harness + **zero-shot baselines** (this is half of your C5 compliance table)
- ☐ **M1 LoRA run starts by D4** on the stratified 100K subset

**D5–D8 (9–12 Sep) — M3, M4, and live swap-in**
- ☐ M4 BiT on LEVIR-CD/WHU-CD + CDVQA
- ☐ M3 Grounding-DINO-T light fine-tune on VRSBench refs
- ☐ M7 patch classifier (cheap, runs alongside)
- ☐ Real tools replace heuristics in the registry, one at a time, contract unchanged
- ☐ M1 nightly holdout eval; iterate if the gate (§C) misses

**D9–D12 (13–16 Sep) — agent, ablation, report**
- ☐ LLM planner (M2) layered *on top of* RuleRouter; fallback rate measured on the 200-query suite
- ☐ M5 = M1 2-image mode wired for change-VQA
- ☐ **Optical/SAR/fused ablation view** (arch §7.3) — real numbers only, else hide the panel
- ☐ Abstention path: low confidence / below min-area → "insufficient evidence", not a guess
- ☐ PDF report + edge-case cards + full E-matrix
- ☐ M6 dual-tower **only if** GPU days remain

**D13–D15 (17–19 Sep) — evidence, freeze, package**
- ☐ Prescribed benchmark runs → §F **zero-shot → adapted** table (this *is* the C5 proof)
- ☐ Offline check, latency check, `docker compose up` cold start < 10 min on a clean machine
- ☐ Demo video ≤ 5 min; model cards + hashes; freeze versions
- ☐ Update the deck with real numbers

**20 Sep — submit with a day of slack. Do not schedule work into this day.**

---

## G.1 Team division (5 people)

Ownership is per-person so nothing is orphaned. Window A roles in brackets.

| Role | Owns | Window A |
|---|---|---|
| **RS/ML lead** | M1 RS-VLM (LoRA, BE.txt subset), VQA + captioning, adaptation evidence table | [deck: model & dataset slides] |
| **Change/fusion engineer** | M4 change detection, M5 (M1 2-image), M6 stretch, M7 patch classifier, ablation view | [prototype: heuristic change mask] |
| **Data/GIS engineer** | GeoTIFF ingestion, CRS, modality detection, **SAR dB/speckle/pol pipeline (arch §5.1)**, co-registration, tiling, overlay geo-mapping | [prototype: real rasterio ingestion] |
| **Backend/orchestration** | FastAPI, `registry.yaml`, planner + guardrail + RuleRouter, executor, trace store, PDF report | [prototype: registry + RuleRouter + trace] |
| **Frontend/eval lead** | UI, overlays, trace panel, benchmark harness + §F tables, demo video, deck | [deck owner + demo script] |

Cross-cutting: the **eval lead owns §F** and blocks submission until the zero-shot → adapted
table is filled with reproduced logs.

---

## H. Demo-day checklist

**T-24 h**
- ☐ Full walkthrough dry run (A5.1–A5.6) with live models; PDF outputs correct
- ☐ Weights loaded & verified (hashes vs MODEL_CARDS)
- ☐ Demo data scenes staged (single optical, single SAR, bi-temporal, opt+SAR)
- ☐ Backup video (<5 min) on 2 devices
- ☐ `docker compose down && up` clean restart test

**T-1 h**
- ☐ `docker compose up` + `POST /warmup` (all models loaded)
- ☐ GPU free, WS streaming works, trace panel renders
- ☐ Network policy set (offline mode if required)
- ☐ Kill-switch (cached answers) known location — OFF

**During (timebox: ≤ 25 min total)**
- ☐ Trace panel OPEN at all times (graded novelty)
- ☐ Q1 caption → Q2 VQA → Q3 grounding → Q4 opt+SAR masks → Q5 change → Q6 compound
- ☐ Show one REJECT case (pair mismatch) — proves A2.2
- ☐ Show confidence badges + one ⚠ disagreement (if demo data produces it)
- ☐ Download one PDF report live at the end
- ☐ If live GPU fails → cached answers + video, do not improvise

**After**
- ☐ Capture: screen recording, `traces.db` export, logs, report PDFs
- ☐ Update §I statuses; submit

---

## I. Submission package checklist

- ☐ Repo (git) with README: 1-command run, hardware spec, dataset licenses, architecture summary
- ☐ Weights tarball (M1–M7 + planner) + `models/MODEL_CARDS.md` (versions, SHA-256, training data, metrics)
- ☐ Eval scripts + run logs on prescribed test subsets (§F tables)
- ☐ Test evidence: pytest report + §E matrix results
- ☐ Demo video ≤5 min (covers A5.1–A5.6)
- ☐ Sample PDF report showing all A2.6 fields
- ☐ `docs/datasets.md` (licenses + citations) + `architecture.md` + `design.md`
- ☐ Submission form fields: team, contact, hardware used, PS number 26167, models list
- ☐ All ☐ in §A marked ☑ (or documented deviation with reason)

---

## J. Risk register (top 10 — trigger → action)

| # | Risk | Trigger | Action | Owner |
|---|---|---|---|---|
| J1 | BE.txt download slow/corrupt | D3 not fully down | partial 50K subset first; fallback: reBEN/Sentinel2Cap + BE v2 with generated text | ☐ |
| J2 | GPU limits — **baseline, not a risk: 6 GB local + free 16 GB notebooks** | always | M1 QLoRA on Kaggle (won't fit 6 GB); M3/M4/M7 local on 4050; M6 cut; stagger 5 Kaggle accounts (`budget.md` §4, §7) | ☐ |
| J3 | M1 underperforms gate | D12 numbers < target | more epochs on BE.txt VQA slice; check template-caption bias; raise RSVQA weight | ☐ |
| J4 | Planner unstable in demo | fallback rate >5 % on suite | simplify plan JSON (tool+params only); raise rule-router share | ☐ |
| J5 | Hidden set 1 m Cartosat / L-band RISAT surprises | §A7.1 test fails on proxies | tiling already; add band-config presets; re-test on real samples ASAP | ☐ |
| J6 | Demo-day GPU failure / 4050 OOM or thermal throttle | any crash during demo | lazy-load-evict; plug in + close all apps; cached answers + video (H. kill-switch) | ☐ |
| J7 | Co-registration surprises in hidden set | offset > 2 px on eval samples | auto-warp already; else polite COMPAT_REPORT (never crash) | ☐ |
| J8 | Time overrun | G schedule slips >2 d | cut: ChangeChat-105k, ADE20K-GS, M7 second class; keep M1/M4/M5/M6 | ☐ |
| J9 | Metrics/weights unknown (PS table missing) | still unknown at D18 | standard metrics + self-evident report; ask §0.2 | ☐ |
| J10 | PS ambiguity (splits, RSVQA layout) | §0 answers unresolved | official forum; worst case: use paper splits + document choice | ☐ |

---

## K. Definition of "ready to submit"

1. All §A rows ☑ (or documented deviation)
2. §E matrix 15/15 green
3. §F tables filled with reproduced logs
4. §H rehearsal passed live, once, without kill-switch
5. §I package complete; §J risks all have owners
6. `docker compose up` → full walkthrough on a clean machine in ≤ 30 min
