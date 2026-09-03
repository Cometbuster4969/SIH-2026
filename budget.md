# SatQuery AI — Zero-Budget Build & Deploy Plan

**Constraint:** ₹0 cash. **Assets already owned:** 5 TB cloud storage + a laptop with
**i5-13500H (12C/16T) + RTX 4050 Laptop 6 GB VRAM + (assumed) 16 GB RAM**.
**Status:** binding. Where this file conflicts with `architecture.md` §9 (2×24 GB GPUs, vLLM,
Docker Compose), **this file wins for the 5 Sep and 20 Sep deliverables.** The GPU-rich design
stays in the docs as the production target.

> **The good news:** PS 26167 is unusually zero-budget-friendly. It never requires cloud
> deployment, scale, or uptime. Deliverables are *"an interactive GUI or web application"* +
> *"codes and models including test and demonstration"* — all satisfiable from a laptop, a
> free notebook GPU, and a free static host. Nothing below is a compromise the judges can see.

---

## 1. What money would have bought, and the free substitute

| Need | Paid default | What you use | Real cost |
|---|---|---|---|
| Training GPU | A100 rental | **Kaggle** (~30 GPU-h/wk, P100/T4 **16 GB**) + **Colab free** (T4). Stagger across 5 accounts ~150 h/wk | Rs 0 |
| Local GPU | - | **RTX 4050 6 GB** - dev, debugging, M4/M7 training, and **live demo inference** | owned |
| Model hosting | GPU inference server | **None.** Demo runs on your own laptop | Rs 0 |
| Web hosting | VPS | **HF Spaces** (free CPU) for a clickable link; local for the real demo | Rs 0 |
| Weights storage | S3 | **HF Hub** (free, versioned, LFS) | Rs 0 |
| Dataset storage | disk array | **Your 5 TB cloud** - full datasets now viable (section 3) | owned |
| Trace DB | Postgres | **SQLite** | Rs 0 |

**Total: Rs 0.** Verify Kaggle/Colab quotas before relying on them - free tiers change without
notice (`checkpoints.md` section 0.3).

### 1.1 What the hardware changes vs. the pure-zero-budget plan

| Previously assumed | With your kit | Consequence |
|---|---|---|
| Subset datasets to a few GB | **5 TB cloud** | Can host **full BE v2 (118 GB)** + all benchmarks. Subsetting is now a *time* decision, not a storage one. |
| CPU-only inference, ~20-60 s/answer | **4050 6 GB** | Live GPU inference, **~3-8 s/answer**. Precomputed answers demote from default to kill-switch. |
| Demo machine unknown | **This laptop, decided** | Rehearse on it from day one. |
| 16 GB training only | 16 GB (cloud) **+ 6 GB local** | Small models (M4, M7, M3) train locally; only M1 needs Kaggle. |

**The 6 GB VRAM ceiling is the one real limit.** It is enough to *serve* everything and to
*train* the small models - it is **not** enough to train M1 (Qwen2-VL-2B) even in 4-bit with
headroom. M1 training stays on Kaggle/Colab 16 GB. Do not fight this.

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

## 3. Dataset strategy - 5 TB changes this

Full sizes (verified): **BigEarthNet v2 = 118 GB** (S1 54.4 + S2 63.3 + reference maps 0.28 GB).
With 5 TB you can hold everything. **But storage was never the only constraint - transfer time
and training time still are.**

| Dataset | Full size | Take | Where it lives |
|---|---|---|---|
| BigEarthNet.txt | 100s of GB | **Full annotations + 50-100k image pairs** | 5 TB cloud (archive) -> Kaggle Dataset (working set) |
| BigEarthNet v2 imagery | 118 GB | **Full** if bandwidth allows, else 30-50 GB stratified | 5 TB cloud |
| BE v2 Reference_Maps | 282 MB | **All** - this is M7's pixel-label source | everywhere, it's tiny |
| VRSBench | ~10 GB | **Full** (train + test) | 5 TB cloud |
| RSVQA | few GB | **Full** | 5 TB cloud |
| CDVQA | ~2 GB | **Full** | local laptop too |
| LEVIR-CD / WHU-CD | ~2 GB | **Both** | local laptop too |

### 3.1 The three-tier storage pattern

```
5 TB cloud      = cold archive. Full datasets, raw downloads, checkpoints history.
Kaggle Dataset  = hot working set. <=100 GB, what training actually reads.
Laptop SSD      = demo scenes + small benchmarks (CDVQA, LEVIR-CD) + weights.
```

**Critical:** Kaggle notebooks **cannot read your cloud drive at speed**. Whatever M1 trains on
must be uploaded as a **Kaggle Dataset** (free, persists across sessions, ~100 GB quota). So:

1. Download full data to 5 TB cloud (slow, once, in the background).
2. Build a stratified **30-60 GB working subset** locally.
3. Upload that once as a Kaggle Dataset. Train from it all week.

The 5 TB is your safety net and your archive - it is **not** the thing Kaggle reads.

### 3.2 Time budget, not storage budget

Downloading 118 GB on a typical Indian home connection (~50 Mbps) is **~5.5 hours**; at 20 Mbps
it is ~13 hours. Start the BE v2 + BE.txt pulls **tonight, in the background**, before you need
them. That is the single highest-value thing you can do today that costs nothing.

**Still stratify the training subset.** 50k well-balanced samples beats 500k unbalanced ones at
a 15-day deadline. Storage is free now; your GPU hours are not.

---

## 4. Model plan: 16 GB cloud for M1, 6 GB local for everything else

`architecture.md` section 7.1 triages to **M1, M4, M3** (+M7). Split by where each trains:

| Model | Trains on | Config | VRAM |
|---|---|---|---|
| **M1** Qwen2-VL-2B | **Kaggle/Colab 16 GB** | QLoRA 4-bit, r=32, grad-ckpt, batch 1 + accum 8, 512 px | ~10-12 GB - **will not fit your 6 GB** |
| **M3** Grounding-DINO-T | **Local 4050** or Kaggle | fine-tune, batch 2, 512 px, AMP | ~5 GB - fits, tight |
| **M4** BiT change | **Local 4050** | ViT-B, batch 4, 256 px crops, AMP | ~4-5 GB - comfortable |
| **M7** UNet++ | **Local 4050** | batch 4-8, 256 px, AMP | ~4 GB - comfortable |
| **M2** planner | not trained | **RuleRouter primary** (PS P10: only the trace is graded, so this costs zero points). Optional Qwen2.5-1.5B 4-bit on the 4050 for an LLM-planner slide | ~2 GB |
| **M6** fusion | **cut** | cross-modal served by M1 2-image + M7 + ablation | - |

**This is a genuinely better split than pure-cloud.** M4/M7/M3 train locally overnight without
touching your Kaggle quota, which means **your ~150 h/week of free quota goes almost entirely
to M1** - the model that actually needs it and the one that satisfies the PS adaptation clause.

**6 GB training discipline (for M3/M4/M7):**
- AMP/`bf16` always; `torch.backends.cudnn.benchmark=True`
- Gradient checkpointing on M3
- `batch_size` small + gradient accumulation - accumulate, do not enlarge the batch
- Close Chrome. A 4050 laptop GPU shares VRAM with the display; budget ~5.2 GB usable of 6.
- Watch thermals: a 13500H + 4050 in a laptop chassis throttles on long runs. Plug in, cooling
  pad if you have one, and prefer 2-4 h runs over 10 h ones.

**Session discipline (Kaggle 9-12 h cap) - unchanged and still critical:**
- Checkpoint every 15 min to `/kaggle/working`, push to HF Hub each epoch
- Resume-from-checkpoint from day one
- Quota tracker in the team channel

---

## 5. Serving: live GPU inference on the 4050

The 6 GB card comfortably **serves** the whole stack. This is a real upgrade - the demo is now
live, not canned.

| Model | Serving config | VRAM | Latency (est.) |
|---|---|---|---|
| M1 Qwen2-VL-2B | **4-bit (bitsandbytes/GGUF)** | ~2.5-3 GB | 3-8 s / answer |
| M3 Grounding-DINO-T | fp16 | ~1.5 GB | 1-2 s |
| M4 BiT | fp16 | ~0.8 GB | 2-3 s |
| M7 UNet++ | fp16 | ~0.4 GB | <1 s |

**They do not all fit resident at once (6 GB total).** Use **lazy load + evict**: keep M1
resident (it is in almost every plan), load M3/M4/M7 on demand and free after the step. The
executor already runs steps sequentially, so this costs a ~1-2 s load per tool - acceptable, and
it is honest to show in the trace as latency.

**Do not use vLLM.** It targets server GPUs and pre-allocates aggressively. Use plain
**HF Transformers + bitsandbytes 4-bit**, or **llama.cpp/GGUF** if you want the lowest footprint.

**Realistic end-to-end targets on this laptop** (replaces `architecture.md` section 10's 4090 budgets):

| Flow | Target |
|---|---|
| Single-image VQA / caption | **<= 10 s** |
| Grounding | **<= 8 s** |
| Bi-temporal change | **<= 20 s** |
| Optical-SAR cross-modal | **<= 20 s** |

Slower than the 4090 table, entirely fine for a demo, and *real*. A streaming trace panel makes
15 s feel deliberate rather than broken.

**Keep the kill-switch, demote it.** Precomputed answers for the 5 scripted PS queries stay
implemented, but as a **failure fallback**, not the default path. Live is the default now.

**16 GB system RAM caveat:** 4-bit M1 + rasterio on a large GeoTIFF can pressure system RAM.
Cap demo scenes at 2048x2048, tile at 512. If you have a spare SODIMM slot, going to 32 GB is
the single best ~Rs 3-4k upgrade - but it is **not required**.

---

## 6. Deployment — what to actually ship

The PS asks for *"an interactive GUI or web application."* It does **not** ask for a public URL.

### 6.1 Primary: local web app on the 4050 laptop (this is the graded artifact)
```bash
git clone <repo> && cd satquery
pip install -r requirements.txt
python -m scripts.fetch_weights          # pulls adapters from HF Hub
streamlit run app.py                     # or: uvicorn backend.api:app
```
Runs offline after the first weight fetch, **with live GPU inference on the 4050**. This is what
you demo and what judges reproduce. Provide a `--device cpu` flag so a judge without a GPU can
still run it (slower, but reproducible - this matters for the "codes and models" deliverable).

### 6.2 Secondary: Hugging Face Space (free, public link — nice-to-have)
- Free CPU tier: 2 vCPU / 16 GB RAM, sleeps when idle, **no GPU**.
- Deploy the **light path only**: ingestion + validation + registry + RuleRouter + trace +
  precomputed demo scenes. Put M1 behind a "runs locally, see repo" note.
- Value: a link in the PPT that a judge can click. Do not make it load-bearing for the demo.
- Alternative if HF Spaces is unavailable: **GitHub Pages** with a static walkthrough of
  captured screenshots + a trace JSON viewer. Zero compute, still clickable.

### 6.3 Docker
Keep the `Dockerfile` (PS deliverable expectation, `checkpoints.md` section I). Ship **two
targets**: a CUDA one matching your laptop, and a **CPU-only fallback** so it builds anywhere.
Judges build locally; you never push to a registry.

### 6.4 Weights distribution
Public **HF Hub model repo** per adapter (`M1-qlora`, `M3`, `M4`, `M7`) + `MODEL_CARDS.md` with
SHA-256. Free, versioned, satisfies the "models" deliverable. Keep a **full mirror on the 5 TB
cloud** (weights + optimizer states + run logs) - HF is the distribution channel, the 5 TB is
the backup. Losing a trained adapter at D14 with no backup would be unrecoverable.

---

## 7. Zero-budget risk register

| Risk | Mitigation |
|---|---|
| Kaggle quota exhausted mid-week | Quota resets weekly; stagger across **team members' accounts** (each gets 30 h — 5 people = 150 h/week). Coordinate so two people don't train the same model. |
| Colab pre-empts a long run | Checkpoint every 15 min + push to HF each epoch. Never rely on a >6 h uninterrupted run. |
| Free tier changes/disappears | Two providers already (Kaggle + Colab). Fallback: CPU-train only M4/M7 (small), ship M1 zero-shot + document it. Degraded, not dead. |
| Demo laptop too slow | 4050 gives live 3-8 s inference; precomputed answers for the 5 scripted queries remain as fallback (section 5) + recorded video. |
| **4050 thermal throttle / OOM mid-demo** | Plug in, close everything, cap scenes at 2048 px, lazy-load-and-evict. Rehearse the exact demo on this laptop from D13. If VRAM spikes, kill-switch to cached answers. |
| **16 GB system RAM pressure** | Cap demo raster size; stream tiles rather than loading whole GeoTIFFs. |
| **Cloud->Kaggle transfer forgotten** | Kaggle cannot read your cloud drive at speed. Working subset must be uploaded as a Kaggle Dataset by D3 or M1 training slips (section 3.1). |
| No internet at venue | Everything offline after weight fetch. Pre-pull weights, **verify airplane-mode** at D17. |
| 118 GB download attempted by accident | Streaming-only rule (§3). Put a guard in the download script that refuses >20 GB. |
| Someone burns quota on M6 | M6 is **cut** (§4). Do not train it. |

---

## 8. Zero-budget checklist

**Setup (do today)**
- [ ] **Start the BE v2 + BE.txt download to the 5 TB cloud tonight, in the background** (5-13 h)
- [ ] All 5 members have Kaggle + Colab accounts, GPU enabled, quota confirmed
- [ ] HF account + org created; empty model repos for M1/M3/M4/M7
- [ ] Demo laptop = **the 4050 machine**; CUDA + PyTorch verified, `nvidia-smi` clean
- [ ] Confirm laptop RAM (16 or 32 GB) - drives the raster size cap

**Data (D1-D4)**
- [ ] Full datasets landing in 5 TB cloud (background)
- [ ] **Stratified 30-60 GB working subset built and uploaded as a Kaggle Dataset by D3**
- [ ] Full test splits fetched (VRSBench, RSVQA, CDVQA) - never subset these
- [ ] BE v2 `Reference_Maps.tar.zst` (282 MB) + matched S1/S2 subset for M7, **on the laptop**

**Training (D4-D12)**
- [ ] M1 QLoRA dry-run (50 steps) on Kaggle confirms <16 GB before the long run
- [ ] **M4 + M7 training locally on the 4050** (overnight, zero quota cost)
- [ ] M3 locally if it fits in ~5.2 GB, else Kaggle
- [ ] Checkpoint-every-15-min + resume + HF push implemented and tested
- [ ] Quota tracker: who's training what, hours left

**Serving (D13-D15)**
- [ ] Lazy-load-and-evict verified: no OOM across all 6 demo flows back-to-back
- [ ] Measured latency per flow recorded (replaces the 4090 estimates)
- [ ] 5 scripted queries precomputed as the **fallback** path
- [ ] `--device cpu` path verified (for judges without a GPU)
- [ ] Offline (airplane-mode) run verified on the 4050 laptop
- [ ] HF Space live with the light path (optional)
- [ ] Weights on HF Hub **+ mirrored to 5 TB cloud** + `MODEL_CARDS.md` hashes

---

## 9. What to say if a judge asks about compute

> *"The vision-language model was fine-tuned with 4-bit QLoRA on free-tier 16 GB notebook GPUs;
> the change-detection and segmentation models were trained locally on a 6 GB RTX 4050. We
> evaluated on the full prescribed test splits. Everything you're seeing runs live on this
> laptop, offline, on that same 6 GB GPU."*

That last sentence is a genuine strength: **the whole system demonstrably runs on consumer
hardware**, which matters for an operational remote-sensing tool.

Say it plainly. Working within a real constraint and being explicit about it reads as
engineering maturity. What loses points is an unexplained gap between a claimed 229 k-sample
training run and a model that can't answer a question on stage.
