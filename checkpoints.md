# SatQuery AI — Checkpoints & Master Checklist (PS 26167)

**Purpose:** nothing slips. Update statuses daily; owner + date on every change.
**Legend:** ☐ open · ◐ in progress · ☑ done · ✗ blocked (write why) · ➖ N/A
**Companions:** `architecture.md` · `design.md` · `satquery-ai-architecture.md`

> Today: **3 Sep 2026**. PS header date: **20 Sep 2026** (assume = registration/event date — **confirm**, see §0).

---

## 0. Facts to confirm (do in week 1, official SIH/ISRO channels)

| # | Question | Why it matters | Status |
|---|---|---|---|
| 0.1 | Exact on-site/competition date; what "20 Sep 2026" means in the PS header | schedules training runs | ☐ |
| 0.2 | Full PS PDF — the evaluation table is a placeholder in the circulated text; exact benchmark test splits + metric names/weights | eval harness targets | ☐ |
| 0.3 | Hardware at venue: GPU available? Can we bring own laptop+GPU? | serving config (1× vs 2×24 GB) | ☐ |
| 0.4 | Internet at judging/eval time? | assume **none**; verify | ☐ |
| 0.5 | How is the web app judged — our machine, their infra, or submitted build? | Docker packaging + port binding | ☐ |
| 0.6 | How are benchmark test subsets run — our script on our hardware, or theirs on ours? | `eval/` CLI contract | ☐ |
| 0.7 | Any model-size/latency limits stated in full PS? | M1 2B vs 7B decision | ☐ |
| 0.8 | Is a recorded video an accepted demo backup? | kill-switch plan | ☐ |
| 0.9 | RSVQA exact split + file layout (official link in PS is cut in our copy) | data prep | ☐ |
| 0.10 | BigEarthNet.txt: confirm HF `BIFOLD-BigEarthNetv2-0/BigEarthNet.txt` layout, split files, license (CC-BY 4.0), and whether InternVL adapter code is released | M1/M6 training | ☐ |

---

## A. Problem-statement compliance matrix (the graded contract)

Every PS "shall/must" → where handled → evidence artifact → status.

### A.1 Mandatory functional scope
| # | PS requirement | Handled by | Evidence | Status |
|---|---|---|---|---|
| A1.1 | ≥1 visual/VL component fine-tuned/adapted on BigEarthNet.txt or open RS data | M1 (also M3,M4,M6,M7) LoRA | training logs + **zero-shot vs adapted** benchmark table + adapter hashes in report | ☐ |
| A1.2 | Single-image **VQA mandatory** | `vqa` (M1) | demo Q2 + VRSBench/RSVQA test numbers | ☐ |
| A1.3 | + captioning **or** grounding (we do both) | `caption` (M1), `ground` (M3) | demo Q1, Q3 + numbers | ☐ |
| A1.4 | Bi-temporal change description **or** change-VQA mandatory | `change_map`+`change_vqa` (M4,M5) | demo Q5 + CDVQA test numbers | ☐ |
| A1.5 | Spatial change map where reference masks available | M4 mask overlay + facts | overlay in UI + PDF | ☐ |
| A1.6 | Cross-modal optical–SAR pair analysis | `xmodal_*` (M6,M7) | demo Q4 + BE.txt benchmark-split numbers | ☐ |
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
| A5.1 | single-image VQA | "What objects are visible?" (VQA) | ☐ |
| A5.2 | additional single-image task (caption + grounding) | "Describe the land-cover and major objects…" / "Highlight the water body…" | ☐ |
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
| A6.4 | Tests (pytest unit + integration + test matrix §E) | ☐ |
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
| **BigEarthNet.txt** (PRIMARY) | HF `BIFOLD-BigEarthNetv2-0/BigEarthNet.txt` | 229,114 train pairs (~9.6M ann. total); stratified **100K subset** for SIH timeline | ☐ | CC-BY 4.0 ☐ | ☐ | ☐ | ☐ |
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
- ☐ Disk budget reserved (≈1.5–3 TB); checksums `manifest.json` written at download
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
| M7 Dual UNet++ | xmodal_mask | scratch | BE v2 LULC maps | built-up/water mIoU ≥ 0.80 on holdout | ☐ |

- ☐ M1: confirm whether BE.txt authors released InternVL adapter/code — if yes, rerun gate with InternVL2.5-2B and pick winner
- ☐ All adapters recorded with SHA-256 in `models/MODEL_CARDS.md`

---

## D. System checkpoints

**Ingestion**
- ☐ Unit tests: every supported format; modality detector ≥98 % on 50-image test set
- ☐ Coreg offset: synthetic shift 0/1/3/8 px → detected & (auto) re-registered correctly
- ☐ Tiling round-trip: stitched mask == original (pixel-exact), bbox geo-mapping exact
- ☐ PNG/JPEG allow-list gate (benchmark dirs pass, others reject with `E_FORMAT`)

**Agent**
- ☐ Registry: 9 tools + schemas + examples; `GET /tools` matches `registry.yaml`
- ☐ Planner suite: 200 queries (40/task incl. multi-step & invalid) → accuracy + schema-validity logged
- ☐ Guardrail: 50 crafted invalid plans all rejected
- ☐ Fallback router: same 200 queries → 100 % coverage, `fallback_used` recorded
- ☐ Executor: per-step timeout 30 s + 1 retry; one tool killed ⇒ graceful degraded answer + flag
- ☐ Param whitelist enforced (PS A2.4) — attempt out-of-whitelist param in test

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
- ☐ 1×24 GB fallback config works (time-sliced B-tools)

---

## E. Test matrix (pytest + manual; each row = one integration test)

| # | Input | Query | Expected | Status |
|---|---|---|---|---|
| E1 | 1 optical GeoTIFF | "Describe the land-cover and major objects…" | caption + facts; trace ok | ☐ |
| E2 | 1 optical GeoTIFF | VQA ("What is the dominant cover?") | constrained answer + conf | ☐ |
| E3 | 1 optical | "Highlight the water body…" | bbox overlay + label | ☐ |
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
| Cross-modal | BE.txt benchmark split (1,082 pairs) | 15-task suite + built-up/water mIoU | | | ☐ |

- ☐ Eval CLI reproduces all rows: `python -m eval.run --split <name> --out eval/results/`
- ☐ Results tables rendered into report + final submission doc

---

## G. Schedule (3 Sep → 20 Sep; adjust per §0.1)

**Week 1 (3–9 Sep): data + skeleton**
- ☐ D1: downloads started (BE.txt first — largest); §0 questions raised
- ☐ D2: repo scaffold (arch §12) + Docker skeleton; ingest service + unit tests
- ☐ D3: converters for BE.txt / VRSBench / RSVQA / CDVQA; QC render checks
- ☐ D4: eval harness + **zero-shot baselines** for M1/M3 on VRSBench/RSVQA
- ☐ D5: tiling + coreg + modality detection done; tool-schemas + registry.yaml
- ☐ D6: planner suite (200 queries) + guardrail + fallback router (rule-only ok)
- ☐ D7: buffer / fix list

**Week 2 (10–16 Sep): models (the heavy week)**
- ☐ D8: **M1 LoRA run starts** (100K BE.txt subset; 2–3 epochs; nightly eval on holdout)
- ☐ D9: M4 (BiT on QAG-360K+CDVQA) + M7 (UNet++ on BE v2) runs
- ☐ D10: M3 (G-DINO fine-tune) + M6 (fusion on BE.txt S1–S2 + TAMMI)
- ☐ D11: M5 (M1 2-image head on CDVQA+QAG-360K+ChangeChat) — needs M1 stage-1 ckpt
- ☐ D12: eval gates (§C) → iterate worst model (one more epoch max, else accept)
- ☐ D13: tool wrappers (all 9) + confidence utilities (T5) + trace store
- ☐ D14: integration: agent + tools end-to-end on all E-matrix rows

**Week 3 (17–20 Sep): system + demo readiness**
- ☐ D15: frontend (stage + overlays + trace + metadata cards)
- ☐ D16: PDF report + edge-case cards + demo mode
- ☐ D17: full test matrix §E green; offline check; latency check; Docker cold-start <10 min
- ☐ D18: **prescribed benchmark runs** (§F) + demo rehearsal #1 + video recording
- ☐ D19–20: buffer; submission package (per §I); demo rehearsal #2

*(If on-site is later than 20 Sep: use the extra weeks for full-data M1 epochs, M6 second round, and eval hardening.)*

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
| J2 | GPU shortage | <2×24 GB by D8 | 4-bit everywhere; M1 2B only; subset → 60K; queue single-request | ☐ |
| J3 | M1 underperforms gate | D12 numbers < target | more epochs on BE.txt VQA slice; check template-caption bias; raise RSVQA weight | ☐ |
| J4 | Planner unstable in demo | fallback rate >5 % on suite | simplify plan JSON (tool+params only); raise rule-router share | ☐ |
| J5 | Hidden set 1 m Cartosat / L-band RISAT surprises | §A7.1 test fails on proxies | tiling already; add band-config presets; re-test on real samples ASAP | ☐ |
| J6 | Demo-day GPU failure | any crash during demo | cached answers + video (H. kill-switch) | ☐ |
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
