# SatQuery AI — Design (UI / UX, API, Data Schemas, Report)

**Version:** 1.0 — 3 Sep 2026
**Companion docs:** `architecture.md` · `checkpoints.md` · `satquery-ai-architecture.md`

---

## 1. Users & scenarios

| Persona | Need | Drives |
|---|---|---|
| P1 Non-expert analyst (agri/disaster/urban) | plain-language Q&A with visible evidence | UX language, overlays, confidence badges |
| P2 Benchmark evaluator | headless runs of prescribed test subsets | stable API contract, `eval/` harness, JSON export |
| P3 Judge | 5-minute walkthrough, visible agent behavior | trace panel, demo chips, PDF report |

**UX principles**
1. Every answer ships with evidence (overlay, crop, or computed number).
2. The agent is always visible: plan + trace one click away, open by default.
3. Plain-language progress ("Reading images…", "Comparing the two dates…", "Drawing the change map…").
4. No bare errors: every failure = reason + suggested fix.
5. Non-expert vocabulary in UI ("satellite picture", "date", "area changed %").

## 2. Main screen layout (≥1280 px)

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│  SatQuery AI        [History ▾]   [Demo mode]   [Docs]   [⚙]                    │
├──────────────────┬──────────────────────────────────────┬────────────────────────┤
│ UPLOAD & INVENTORY│  CHAT                                │  TRACE + REPORT       │
│ ┌──────────────┐ │  ┌────────────────────────────────┐  │ ┌────────────────────┐ │
│ │ + add image  │ │  │ USER: What changed between     │  │ │ Task: CHANGE_VQA   │ │
│ │   (max 2)    │ │  │ these two dates, and where?    │  │ │ planner: qwen2.5-7b│ │
│ └──────────────┘ │  └────────────────────────────────┘  │ │ fallback: no       │ │
│ ┌──────────────┐ │  ┌────────────────────────────────┐  │ │ ┌────────────────┐ │ │
│ │ [t1] 2018-05 │ │  │ SATQUERY: Between 2018-05 and  │  │ │ │ 1 change_map   │ │ │
│ │ optical · 1m │ │  │ 2021-03 built-up grew +8.1%    │  │ │ │   BiT v1.0     │ │ │
│ │ 512×512 · 4t │ │  │ mainly along the northern road │  │ │ │   thr=0.5      │ │ │
│ └──────────────┘ │  │ corridor. [1][2]               │  │ │ │ 4.1s · conf .87│ │ │
│ ┌──────────────┐ │  │ ▣ change map  ▣ areas  ⚠ none  │  │ │ │ 2 change_vqa   │ │ │
│ │ [t2] 2021-03 │ │  │ confidence  ●●●○ 0.82  [trace] │  │ │ │   M1-2img      │ │ │
│ │ optical · 1m │ │  └────────────────────────────────┘  │ │ │ 3.4s · conf .81│ │ │
│ └──────────────┘ │  ┌────────────────────────────────┐  │ │ │ 3 integrate    │ │ │
│ PAIR: ✓ bi-temporal│ │ > Has the built-up area in-  [>] │  │ │   2.1s · conf .82│ │ │
│ offset 0.4px · Δt │  └────────────────────────────────┘  │ │ └────────────────┘ │ │ │
│ 1032d             │  (suggested chips: 5 PS queries)     │ │ total 11.4s        │ │
├──────────────────┴──────────────────────────────────────┴──┤ [Download report]  │
│ IMAGE STAGE — full image, zoom/pan, layer toggles:         │  [Trace as JSON]   │
│  [x change map] [x areas] [ ] attention    legend, geo tip │                     │
└────────────────────────────────────────────────────────────┴─────────────────────┘
```

## 3. Screens & states

| Screen | Content |
|---|---|
| S1 Empty | drop zone (1–2 files), **"Load demo data"** (curated: 1 optical, 1 SAR, 1 bi-temporal pair, 1 opt+SAR pair), 5 representative-PS-query chips |
| S2 Loaded | inventory cards per image (name, modality, CRS, extent, res, date, tile count); **pair banner**: green ✓ compatible / amber auto-cropped or re-registered / red ✗ not compatible + reason |
| S3 Working | streaming step list (spinner per step, elapsed s, cancellable) |
| S4 Done | answer card (§5) on stage + overlays rendered |
| S5 Rejected | reason card: what failed + fix (e.g., "PNG accepted only for benchmark datasets") |

**Request state machine**
```
INGESTED → PLANNING → RUNNING(step i/n) → INTEGRATING → DONE
             │            │
             └─(plan invalid)─► RULE_PLAN ─► RUNNING (fallback_used=true)
any → REJECTED (compatibility) | FAILED (retryable, message + retry button)
```

## 4. Answer card anatomy (S4)

- **Header:** task badge (color per task), overall confidence badge (§7), total time
- **Body:** answer text; inline citations `[1] [2]` → map to trace rows (click → scroll/expand)
- **Facts chips:** computed numbers as clickable chips — `built-up +8.1%`, `changed 12.4%`, `water 340 ha` — each links to the tool that produced it
- **Evidence row:** thumbnails (change map, masks, attention crops) → click focuses stage layer
- **Confidence block:** per-tool bars + disagreement flag (`⚠ optical & SAR disagree in SW quadrant`)
- **Footer:** `Run trace ▾` · `Copy answer` · `Download report (PDF)`

## 5. Overlay layer design (stage)

| Layer | Semantics | Color |
|---|---|---|
| `bbox` | grounding boxes | cyan `#00E5FF`, label + score |
| `mask.change.added` / `.removed` | bi-temporal change | red `#E53935` / yellow `#FDD835` |
| `mask.built_up` / `mask.water` | xmodal joint seg | grey-orange `#FB8C00` / blue `#1E88E5` |
| `heatmap` | attention/evidence | viridis, 50 % blend |
| `annotations` | "where did change occur" centroids + labels | white dot + text halo |

Per layer: name, source tool+version, confidence, opacity slider, visibility toggle.
Legend auto-built. Tooltip: geo lat/lon + area (ha). Export: PNG of stage w/ active layers (used in report).
Konva canvas; all coords pre-projected to stage by backend (UI never re-projects).

## 6. Execution trace panel

Table: `# | step | tool (version) | key params | inputs (hash) | output summary | conf | time`
- Row expand: full output JSON + evidence thumbnails
- Footer: planner model, `fallback_used`, total latency, request id
- `Trace as JSON` → copy/download (evaluator-friendly)
- **Always rendered in the PDF report** (PS: auditable execution summary = selected task, model/tool names, key parameters)

## 7. Confidence design

- Per-tool numeric ∈ [0,1] (T5: token-prob for VLM answers, box/mask prob margins, calibrated on holdout)
- Final = weighted geometric mean → badge: **High ≥0.75** (green) · **Med 0.50–0.75** (amber) · **Low <0.50** (red + "evidence limited — show weaker tools")
- Disagreement rule (optical vs SAR conf diff > 0.3 on shared claim) → ⚠ surfaced in answer, trace, report
- Visible in: answer card, trace rows, report §2 — (PS: "confidence information")

## 8. PDF report (downloadable — mandatory deliverable element)

Generated server-side (weasyprint), 5–10 pp, ≤3 MB:

1. **Cover** — query, image thumbs, auto metadata (modality, extent, res, dates), request id, date
2. **Answer** — final text, confidence badge, per-claim tool citations, facts chips
3. **Evidence** — rendered overlays (one per layer) + attention crops + per-tool numeric outputs
4. **Execution summary (auditable)** — task, planner, plan, per-step table: tool name+version, params, input hashes, output summary, confidence, latency, total
5. **Appendix** — model versions + adapter hashes, environment, dataset licenses, disclaimers

## 9. API design

Base `/api/v1` · JSON · multipart for uploads

| Endpoint | Method | Purpose |
|---|---|---|
| `/ingest` | POST | multipart `files[1..2]` → `201 {request_id, inventory, pair_check, tiles}` |
| `/query` | POST | `{request_id, query}` → `202 {request_id, ws_url}` |
| `/ws/{request_id}` | WS | events: `planning · step_start · step_done · integrating · done · error · cancel_ack` |
| `/requests/{id}` | GET | full result: `{answer, confidence, overlays[], trace[], facts{}, report_url}` |
| `/requests/{id}/report.pdf` | GET | PDF |
| `/requests/{id}/trace.json` | GET | auditable trace (PS artifact) |
| `/tools` | GET | registry dump (proves "predefined registry") |
| `/warmup` | POST | load all weights (demo-day use) |
| `/health` `/version` | GET | ops |

**Error model** `{code, message, fix, details}`:
`E_FORMAT · E_BANDS · E_CRS · E_TOO_LARGE · E_PAIR_MISMATCH · E_COREG_HIGH (warn) ·
E_TASK_UNSUPPORTED (e.g., "trend" on cross-modal) · E_TOOL_TIMEOUT · E_FALLBACK_USED (warn)`
Each code has a user-facing message + suggested fix (S5 card).

## 10. Canonical data schemas

```jsonc
// InputInventory (ingest output; feeds planner + trace)
{
  "files": [{
    "name": "t1.tif", "format": "GeoTIFF", "crs": "EPSG:32644",
    "extent": [x1,y1,x2,y2], "res_m": 1.0, "size_px": [2048,2048],
    "bands": ["B4","B3","B2"], "band_roles": ["R","G","B"],
    "modality": "optical", "date": "2018-05-12",
    "tiles": 16, "sha256": "…"
  }],
  "pair": {"type": "bi_temporal", "overlap": 1.0, "offset_px": 0.4,
           "dt_days": 1032, "actions": []}   // or ["auto_crop","auto_reregister"]
}

// Plan
{"task": "CHANGE_VQA",
 "steps": [{"id":1,"tool":"change_map","params":{"tile":512,"thr":0.5},"depends_on":[]},
           {"id":2,"tool":"change_vqa","params":{"temp":0.3},"depends_on":[1]},
           {"id":3,"tool":"integrate","params":{},"depends_on":[2]}],
 "planner": {"model":"qwen2.5-7b-4bit","fallback_used":false,"latency_ms":1200}}

// ToolOutput (uniform contract — see architecture.md §6)
// TraceRow: {seq, tool, version, params, inputs, output_summary, confidence,
//             latency_ms, status}
```

## 11. Edge-case UX (must-handle, with copy)

| Case | Behavior |
|---|---|
| Single SAR image | works; caption/answer explicitly says "SAR image"; modality card shows `SAR (amplitude)` |
| Pair with disjoint extents | red banner + S5 card: "These pictures don't cover the same area — upload two views of one location." |
| >10k px raster | tiling notice: "Large image: 214 tiles, ≈ 40 s" |
| Bi-temporal without dates | works; "Dates not found — assuming upload order; direction of change may be uncertain." (directional confidence lowered) |
| Coreg offset > 2 px | auto re-register; amber banner "Auto-aligned (offset 3.1 px)" + trace entry |
| Low confidence answer | red badge + "limited evidence" + which tool was weak |
| Unsupported task for scope | S5 card: e.g. "trend (increased/decreased) needs two dates of the same place" |
| PNG outside benchmark allow-list | S5 card: "PNG/JPEG accepted only for benchmark datasets (VRSBench/RSVQA/CDVQA)." |

## 12. Visual style (kept deliberately cheap)

- Neutral dark UI, one accent (cyan), system font stack, inline-SVG icons only
- Fixed overlay palette (§5); badges per §7
- No custom illustrations, no external fonts/CDN (offline, §NFR)
- Target resolution 1280–1600 px (judge laptops)

## 13. Demo mode

- Toggle in header: loads curated sample scenes + shows the 5 representative-PS query chips
- Default = **live** execution; hidden kill-switch (settings → "cached answers") for GPU failure on demo day — never visible to judges
- One-click "Run full walkthrough" (queries 1→6 sequentially, trace panel open)
