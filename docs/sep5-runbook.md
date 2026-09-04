# Sep 5 Runbook — Window A (graded artifact = the PPT)

> 5 Sep, 10:00 is the Round-1 PPT pitch. The working prototype is **bonus points** —
> this runbook protects the deck first, then the demo. Owners per `checkpoints.md` §G.1.

## T-24 h → now (4 Sep, evening)

| # | Step | Owner | Done |
|---|---|---|---|
| 1 | **Deck: all 12 slides in final order**, weak slides cut. Order: problem → insight → one-liner → architecture (full slide) → agentic layer → **execution-trace mockup (the graded novelty)** → models×datasets table → SAR-is-not-RGB → ablation (real BE v2 numbers) → prototype screenshots → honest 5→20 Sep plan → compliance matrix | Deck squad (3) | ☐ |
| 2 | **Prototype hardening pass (done in repo):** upgraded UI (SIH branding + PS imagery + structured demo scenes), demo pairs co-registered by construction (banner green, 0.0 px), change/ground overlays render even on the cached kill-switch answers, all 6 walkthrough queries verified live | Frontend/eval | ☑ |
| 3 | **Run the full walkthrough 3× on the 4050** back-to-back: land cover → VQA → grounding → change → cross-modal → caption + one REJECT case (upload a `.txt` → E_FORMAT card). No crash, no OOM, thermal watch. | Prototype squad (2) | ☐ |
| 4 | **Kill switch armed:** `config/demo_cache.json` drives every demo answer — verify by running the app **with GPU busy / torch unimportable**. Answers must be identical, badges still say TRAINED/HEURISTIC honestly. | Backend | ☐ |
| 5 | **Offline check:** disable egress (or run in airplane mode) → full walkthrough works, zero external calls. | Backend | ☐ |
| 6 | **Backup video ≤ 5 min** recorded from the live walkthrough, saved on **2 devices** (USB + phone). | Frontend/eval | ☐ |
| 7 | **Speaker notes + Q&A one-liners** on slides 7, 8, 11 (base model / not-a-GPT-wrapper / planner-fails / SAR / compute). Use the handoff Q&A block verbatim. | Deck squad | ☐ |
| 8 | Freeze the deck: **no edits after this checklist is green.** Export PPTX + PDF both. | Deck squad | ☐ |

## 5 Sep, 00:00 → 10:00

| Time | Step |
|---|---|
| 00:00–02:00 | Deck squad: sleep. Nothing new gets merged into the deck. |
| 08:00 | Full team 15-min sync: deck order confirmed, presenter + backup presenter named, who carries the laptop. |
| 08:30 | Prototype squad: `uvicorn satquery.web_server:app --host 0.0.0.0 --port 8000` on the **presenting laptop**, plugged in, Chrome closed. Click **⏵ Full walkthrough** once, end to end, no intervention. |
| 09:00 | **Dry run on the actual presenting laptop, plugged in**, with the PPT on the same screen flow: deck → switch to app → one query → trace panel visible → PDF/trace JSON → back to deck. Timebox ≤ 25 min total. |
| 09:30 | Confirm: video backup accessible, traces.db exportable, **kill switch OFF decision** known (default: cached answers ON for the demo), venue Wi-Fi irrelevant (offline mode works). |
| 09:45 | Presenter: eat, hydrate, phone on silent. Backup presenter has the PPTX on phone/cloud. |
| 10:00 | **Present.** Trace panel open at all times. If the live GPU hiccups: cached answers + video, do not improvise. |

## On-stage honesty line (say it, don't hide it)

> "The orchestration layer you're seeing is real — ingestion, validation, the tool
> registry, routing and the execution trace all run live. The land-cover model is
> BigEarthNet-pretrained. The remaining specialist models are heuristics today;
> they're fine-tuned for the 20 September submission."

## 10:30 → (start Window B)

1. Capture: screen recording, `traces.db` export, logs, report PDFs.
2. Update `checkpoints.md` §I/§H statuses with the demo-day evidence.
3. Window B D1 kicks in the same day: **BE.txt working set → Kaggle Dataset by D3**
   (critical path, see `checkpoints.md` §G, D1–D4).
