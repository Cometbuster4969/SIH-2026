# SatQuery AI — Zero-Budget Build & Deploy Plan

**Constraint:** ₹0. No paid GPU, no paid hosting, no paid storage, no credit card.
**Status:** binding. Where this file conflicts with `architecture.md` §9 (2×24 GB GPUs, vLLM,
Docker Compose), **this file wins for the 5 Sep and 20 Sep deliverables.** The GPU-rich design
stays in the docs as the production target.

> **The good news:** PS 26167 is unusually zero-budget-friendly. It never requires cloud
> deployment, scale, or uptime. Deliverables are *"an interactive GUI or web application"* +
> *"codes and models including test and demonstration"* — all satisfiable from a laptop, a
> free notebook GPU, and a free static host. Nothing below is a compromise the judges can see.

---

## 1. What money would have bought, and the free substitute

| Need | Paid default | Free substitute | Real cost |
|---|---|---|---|
| Training GPU | A100 rental | **Kaggle Notebooks** — ~30 GPU-h/week, P100 16 GB or T4×2, 9–12 h/session, no card | ₹0 |
| Overflow GPU | — | **Google Colab free** — T4 16 GB, ~15–30 h/week, pre-emptible | ₹0 |
| Model hosting | GPU inference server | **Nothing.** Demo runs locally on the presenting laptop | ₹0 |
| Web hosting | VPS | **Hugging Face Spaces** (free CPU tier) for a public link; local for the real demo | ₹0 |
| Weights storage | S3 | **HF Hub** — free, unlimited public model repos, LFS included | ₹0 |
| Dataset storage | 1.5–3 TB disk | **Subsets only** — a few GB (§3) | ₹0 |
| Trace DB | Postgres | **SQLite** (already the design) | ₹0 |
| Container registry | Docker Hub paid | Plain `Dockerfile` in-repo; judges build locally | ₹0 |

**Total: ₹0.** Verify Kaggle/Colab quotas before relying on them — free tiers change without
notice (`checkpoints.md` §0.3).

---

## 2. The hard rule: separate TRAINING from SERVING

This is the single decision that makes a zero-budget build work.

```
TRAINING  →  Kaggle/Colab GPU  →  push adapters to HF Hub   (heavy, offline, one-time)
SERVING   →  presenter's laptop, CPU  →  pull adapters from HF (light, must be reliable)
```

Never try to serve from a free notebook. Sessions die, URLs rotate, and a dead tunnel mid-demo
is a lost round. **The 5 Sep and 20 Sep demos run on your own laptop, offline.**

---

## 3. Dataset strategy — subsets, never full downloads

Full sizes (verified): **BigEarthNet v2 = 118 GB** (S1 54.4 + S2 63.3 + reference maps 0.28).
BigEarthNet.txt is larger again. **You will not download these.** Neither do you need to.

| Dataset | Full | Take | How |
|---|---|---|---|
| BigEarthNet.txt | 100s of GB | **~20–40 k pairs** | HF `datasets` **streaming mode** — `load_dataset(..., streaming=True)`, filter, save only what you keep |
| BigEarthNet v2 imagery | 118 GB | **~5–8 k patches** | Stream/partial-extract; needed for M7 + fusion |
| BE v2 Reference_Maps | 282 MB | **all of it** | Small — take it whole (this is the per-pixel label source, arch §7.2) |
| VRSBench | ~10 GB | **train subset + full test split** | Test split is mandatory for §F |
| RSVQA | few GB | **subset + full test split** | |
| CDVQA | ~2 GB | **all** | Small; the whole change benchmark |
| LEVIR-CD / WHU-CD | ~2 GB | **LEVIR-CD only** | Enough to train M4 |

**Rules**
1. **Stream, filter, then persist.** Never `wget` a 54 GB tarball.
2. **Datasets live on Kaggle/Colab, not your laptop.** Attach as a Kaggle Dataset (free, 100+ GB
   quota) so it persists across sessions without re-downloading.
3. **Full test splits are non-negotiable** — subsetting the *test* set invalidates §F and the
   PS says evaluation uses "prescribed public benchmark test subsets."
4. Stratify training subsets by class so a 20 k sample isn't 90 % forest.

**Consequence for the deck (state it honestly):** *"Trained on a stratified N-sample subset due
to compute constraints; evaluated on the full prescribed test splits."* That is a normal,
defensible research disclosure — not a weakness.

---

## 4. Model plan under a 16 GB free GPU

`architecture.md` §7.1 already triages to **M1, M4, M3** (+M7). All four fit. Adjustments:

| Model | Change from the GPU-rich plan | Fits |
|---|---|---|
| **M1** Qwen2-VL-2B | **QLoRA (4-bit) instead of bf16 LoRA.** r=32 (not 64), grad-checkpointing, batch 1 + grad-accum 8, 512 px tiles. ~10–12 GB peak | ✅ P100/T4 16 GB |
| **M2** planner | **Do not run a 7B locally.** Use **RuleRouter as the primary router** — PS P10 says only the observable trace is graded, so this costs *nothing* in score. Optional: Qwen2.5-**1.5B**-Instruct 4-bit if you want an LLM planner on the slide | ✅ CPU-viable |
| **M3** Grounding-DINO-T | Light fine-tune, ~4 GB | ✅ |
| **M4** BiT change | Small ViT-B, LEVIR-CD, ~6 GB | ✅ |
| **M7** UNet++ | Small; trains in 1–2 h | ✅ |
| **M6** fusion | **Cut.** Cross-modal is served by M1 2-image + M7 + ablation (arch §7.1) | — |

**Session discipline (Kaggle 9–12 h cap):**
- Checkpoint **every 15 minutes** to `/kaggle/working` and push to HF Hub each epoch. An
  un-pushed checkpoint at session death is hours of your 30 h/week quota gone.
- Resume-from-checkpoint in the train script from day one. Not an afterthought.
- Log to a CSV in the repo, not to a paid experiment tracker.

**Weekly budget:** ~30 h Kaggle + ~20 h Colab ≈ **50 GPU-h/week**, ~100 h across the 15 days.
M1 QLoRA on 20–40 k samples ≈ 8–14 h. M3/M4/M7 ≈ 2–4 h each. **Comfortable — the binding
constraint is your time, not the quota.** Do not let anyone start a 40 h run.

---

## 5. Serving on a laptop with no GPU

CPU inference is the default assumption. Make it fast enough to demo.

**Tier 1 — CPU-only (assume this).**
- Export M3/M4/M7 to **ONNX Runtime** — 2–4× faster than PyTorch eager on CPU.
- M1 (the VLM) is the slow one: **~20–60 s/answer on CPU.** Two mitigations:
  - **Precompute the demo answers.** For the 5 scripted PS queries on 5 demo scenes, run them
    once and cache. Live-run everything else. This is the `checkpoints.md` §H kill-switch,
    promoted to default behaviour on a CPU laptop.
  - Set the UI expectation: a streaming progress panel makes 30 s feel intentional. The trace
    panel filling in step-by-step *is* the demo.
- **Tile budget:** cap at 512 px, 4 tiles for demo scenes. Do not tile a 20 k px raster live.

**Tier 2 — if any team member has a gaming laptop (GTX 1650 4 GB+).**
- Run M3/M4/M7 on GPU, M1 4-bit on CPU. Everything under 10 s. Designate that laptop the
  **demo machine** on day one and rehearse on it.

**Non-negotiable:** the demo laptop is chosen and rehearsed on by **D13 (17 Sep)**, not the
night before.

---

## 6. Deployment — what to actually ship

The PS asks for *"an interactive GUI or web application."* It does **not** ask for a public URL.

### 6.1 Primary: local web app (this is the graded artifact)
```bash
git clone <repo> && cd satquery
pip install -r requirements.txt
python -m scripts.fetch_weights          # pulls adapters from HF Hub
streamlit run app.py                     # or: uvicorn backend.api:app
```
Runs offline after the first weight fetch. **This is what you demo and what judges reproduce.**

### 6.2 Secondary: Hugging Face Space (free, public link — nice-to-have)
- Free CPU tier: 2 vCPU / 16 GB RAM, sleeps when idle, **no GPU**.
- Deploy the **light path only**: ingestion + validation + registry + RuleRouter + trace +
  precomputed demo scenes. Put M1 behind a "runs locally, see repo" note.
- Value: a link in the PPT that a judge can click. Do not make it load-bearing for the demo.
- Alternative if HF Spaces is unavailable: **GitHub Pages** with a static walkthrough of
  captured screenshots + a trace JSON viewer. Zero compute, still clickable.

### 6.3 Docker
Keep the `Dockerfile` (PS deliverable expectation, `checkpoints.md` §I) but **CPU-only base
image**, no CUDA layers. Judges build it locally; you never push to a registry.

### 6.4 Weights distribution
Public **HF Hub model repo** per adapter (`M1-qlora`, `M3`, `M4`, `M7`) + `MODEL_CARDS.md` with
SHA-256. Free, versioned, and it satisfies the "models" deliverable without a tarball you have
nowhere to host.

---

## 7. Zero-budget risk register

| Risk | Mitigation |
|---|---|
| Kaggle quota exhausted mid-week | Quota resets weekly; stagger across **team members' accounts** (each gets 30 h — 5 people = 150 h/week). Coordinate so two people don't train the same model. |
| Colab pre-empts a long run | Checkpoint every 15 min + push to HF each epoch. Never rely on a >6 h uninterrupted run. |
| Free tier changes/disappears | Two providers already (Kaggle + Colab). Fallback: CPU-train only M4/M7 (small), ship M1 zero-shot + document it. Degraded, not dead. |
| Demo laptop too slow | Precomputed answers for the 5 scripted queries (§5) + recorded video backup. |
| No internet at venue | Everything offline after weight fetch. Pre-pull weights, **verify airplane-mode** at D17. |
| 118 GB download attempted by accident | Streaming-only rule (§3). Put a guard in the download script that refuses >20 GB. |
| Someone burns quota on M6 | M6 is **cut** (§4). Do not train it. |

---

## 8. Zero-budget checklist

**Setup (do today)**
- ☐ All 5 members have Kaggle + Colab accounts, GPU enabled, quota confirmed
- ☐ HF account + org created; empty model repos for M1/M3/M4/M7
- ☐ Demo laptop designated (best GPU available, else best CPU)
- ☐ Download guard script (refuses >20 GB) committed

**Data (D1–D4)**
- ☐ Streaming subset scripts for BE.txt / VRSBench / RSVQA — persisted as Kaggle Datasets
- ☐ Full test splits fetched (VRSBench, RSVQA, CDVQA) — never subset these
- ☐ BE v2 `Reference_Maps.tar.zst` (282 MB) + matched S1/S2 subset for M7

**Training (D4–D12)**
- ☐ QLoRA config verified to fit in 16 GB *before* the long run (dry-run 50 steps)
- ☐ Checkpoint-every-15-min + resume + HF push implemented and tested
- ☐ Quota tracker in the team channel: who's training what, hours left

**Serving (D13–D15)**
- ☐ ONNX export for M3/M4/M7; CPU latency measured and recorded
- ☐ 5 scripted queries precomputed and cached
- ☐ `pip install && run` verified on a clean machine with no GPU
- ☐ Offline (airplane-mode) run verified
- ☐ HF Space live with the light path (optional)
- ☐ Weights on HF Hub + `MODEL_CARDS.md` hashes

---

## 9. What to say if a judge asks about compute

> *"We trained on free-tier notebook GPUs — 16 GB, roughly 100 GPU-hours total — using 4-bit
> QLoRA and stratified dataset subsets. We evaluated on the full prescribed test splits.
> Inference runs on CPU on this laptop, fully offline."*

Say it plainly. Working within a real constraint and being explicit about it reads as
engineering maturity. What loses points is an unexplained gap between a claimed 229 k-sample
training run and a model that can't answer a question on stage.
