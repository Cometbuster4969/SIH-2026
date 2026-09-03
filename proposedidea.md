# SatQuery AI — Proposed Idea & Change of Plan

**Correction note:** This document supersedes the planning assumption in
`architecture.md` / `checkpoints.md` / `satquery-ai-architecture.md`. It captures
**why the plan changed** and **what the new plan is**.

**PS:** SIH 2026 — Problem Statement **26167** (ISRO) · Agentic Remote-Sensing
Question-Answering over optical + SAR imagery
**Submission deadline:** **5 Sep, 10:00** (Round-1 pitch)
**Competition/full-build target:** retains the 20 Sep / post-selection window.

---

## 1. The trigger — what changed

The original documents were written around a **~20-day build window** (3 → 20 Sep,
per `checkpoints.md §G`, and a "5–6 weeks before on-site" horizon per
`satquery-ai-architecture.md §2.8`). They describe a **full implementation plan**:
fine-tuning 6+ models (M1–M7), preparing 6+ datasets, and standing up a complete
dockerized system.

The submission reality is now confirmed:

- **5 Sep, 10:00** is a **SIH Round-1 pitch** — the **graded deliverable is the
  presentation/PPT.**
- A working **prototype earns bonus/extra points**, but is **not** the primary
  graded artifact.
- The **20 Sep** build window (and the 5–6 week planning horizon) is **round-2 /
  post-selection** work.

**Conclusion:** Our *planning documents* are still the right long-term architecture,
but they are the **wrong scope for a 1.5-day pitch.** Continuing to treat a
full model-training build as the 5 Sep deliverable is a schedule risk that
cannot be met — and, more importantly, it optimizes for the wrong thing.

---

## 2. Reason for the change in plan

1. **Wrong deliverable prioritized.** The original plan optimizes for a *finished
   product* (trained models + evaluations). Round-1 grades the *idea, approach and
   communication* — a prototype is only a bonus.
2. **Not feasible in the remaining window.** M1–M7 fine-tuning, 6-dataset prep and
   the 20 Sep schedule simply cannot be compressed into ~1.5 days. Attempting a
   half-trained real change-detection/VLM model would be slower, heavier and *less*
   convincing than a clean demonstration of the core idea.
3. **The graded novelty is NOT the heavy models.** Per the PS, the observable
   execution trace — selected task, models/tools, permitted parameters, outputs,
   confidence, evidence — is the evaluated surface. That is exactly the part that
   can be built cheap, fast and reliably (shell + rule-based orchestrator +
   registry + trace + overlays + report), and it is precisely what a judge can
   *see* in a 5-minute pitch.
4. **An honest, working thin prototype beats a broken deep one.** For round-1, an
   end-to-end demonstration of "agent selects tools from a registry → executes →
   produces an auditable trace + visual evidence + confidence + downloadable
   report" is far more persuasive than a fragile partial model that might crash
   on stage.

---

## 3. The proposed idea (solution)

**One sentence:** *SatQuery AI — a guardrailed, agentic remote-sensing assistant that
plans over a predefined registry of specialist tools, executes them, and returns every
answer with an auditable execution trace, calibrated confidence, visual evidence and a
downloadable report.*

Keep the **full architecture** as the long-term plan (post-selection), but for the
**5 Sep pitch** deliver a **thin end-to-end prototype** that demonstrates —
with lightweight/heuristic model outputs rather than trained networks — exactly the
graded novelty.

### What the prototype must show (the pitch surface)
| # | Capability | Built with |
|---|---|---|
| 1 | Upload + compatibility checking (format/CRS/modality/coreg/tiling) | real (GDAL / rasterio) |
| 2 | Agent selects/specialist tools **from a predefined registry** | `registry.yaml` + `GET /tools` (no ML) |
| 3 | Planner → guardrail → **rule-based fallback router** → executor | deterministic (no ML) |
| 4 | **Observable execution trace** (task, tools, params, inputs-hash, output, conf, latency) | JSON store (no ML) |
| 5 | Visual evidence: change mask + grounding/bbox overlays on a demo scene | heuristic/canned mask + precomputed boxes |
| 6 | Confidence + badging + optical/SAR disagreement rule | calibrated heuristic (no ML) |
| 7 | Downloadable PDF/HTML report | weasyprint / templated |
| 8 | Simple UI (stream trace panel + overlays) | Streamlit or Gradio |

### What is deliberately de-scoped to phase 2 (post-selection)
- Real fine-tuned RS-VLM (M1), grounding (M3), change (M4/M5), fusion (M6), UNet++ (M7).
- Full dataset prep (BE.txt, VRSBench, RSVQA, CDVQA, QAG-360K, TAMMI, ChangeChat-105k…).
- Benchmark zero-shot → adapted evaluation tables.
- GPU serving, Docker weights tarball, latency budget tuning.

**Rebalanced priority for the remaining time (3–5 Sep):**
1. **Today (3 Sep):** build the thin prototype skeleton; nail the pitch narrative.
2. **4 Sep:** polish the deck; make the demo bulletproof (cached-answer kill-switch).
3. **5 Sep 09:00:** dry run; **10:00** submit/present.

---

## 4. Honesty on stage (recommended phrasing)

Present the prototype as: *"Architecture demonstrated end-to-end; specialist models
are fine-tuned post-selection."* Do **not** claim the heuristic vision outputs are
trained results. This reads as a strength (honest, well-scoped, feasible) and protects
us in the Q&A.

---

## 5. Key decisions this change forces

- **M7 (dual UNet++) data/claim mismatch (real bug):** BigEarthNet v2 labels are
  **patch-level**, not per-pixel masks, so a "per-pixel built-up/water mIoU ≥ 0.80"
  gate is unsupported. **Fix:** reframe M7 as a **patch-level built-up/water presence
  classifier** (labels fit, no new data) and render spatial evidence from grounds
  boxes instead of a pixel mask — OR adopt a real dense-segmentation dataset if
  pixel masks are truly required. Recommended: the patch-classifier + box-overlay.
- **M6 (dual-tower fusion) demoted to stretch:** satisfy mandatory cross-modal
  (A1.6) with **M1 in 2-image mode** (optical + SAR as two images) trained on
  TAMMI + BE.txt S1–S2–text. M6 remains an optional upgrade, not a critical-path item.
- **Timeline contradiction:** the "5–6 weeks before on-site" and "20 Sep" windows
  are **phase 2**; re-frame (not re-number) docs to mark the 5 Sep pitch as a
  distinct, smaller deliverable.

---

## 6. Things deliberately unchanged (do not churn)

- 512 px tiles / 64 px overlap, resolution-agnostic design.
- Registry-object tools + deterministic guardrail/fallback (correct for graded trace).
- Confidence aggregation (weighted geometric mean + badges + disagreement rule).
- Latency budgets and the existing deployment model — all phase-2.
- No scope added; the answer at this stage is to *cut*, not to add.
