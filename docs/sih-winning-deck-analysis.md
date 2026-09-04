# Winning-team SIH idea decks — what they do, and how our deck applies it

**Reference deck analysed:** [`1788146398555.pdf`](../1788146398555.pdf) — SIH 2025 idea submission, PS `SIH25273`,
Team *Algo Sapiens*, "TELHAN SATHI". 6 pages, 1440 × 810 pt (16:9), built on the same official template as
[`SIH2026-IDEA-Presentation-Format.pptx`](../SIH2026-IDEA-Presentation-Format.pptx).
**Deck this feeds:** [`SatQuery-AI-SIH2026-Idea-Deck-v2.pptx`](../SatQuery-AI-SIH2026-Idea-Deck-v2.pptx) ·
[`.pdf`](../SatQuery-AI-SIH2026-Idea-Deck-v2.pdf) (the PDF is the artefact we upload).

## 1. Rules that decide the layout before any design does

| Rule (from the template's instruction slide + SIH 2026 rules) | Consequence |
|---|---|
| Max **6 slides including the title page**; instructions slide may be deleted | Exactly one slide per template pointer — no "extra" architecture or roadmap slide |
| "Use only the provided template … without changing the idea-detail pointers" | Section titles and the italic pointer line stay verbatim; only the canvas inside them is ours |
| Upload as **PDF** (PPT/DOC not accepted) | Every graphic must survive a print-to-PDF: real text, embedded fonts, no reliance on animation or hyperlinks |
| Round 1 = 15-min pitch + 5-min Q&A, scored on problem understanding, innovation, feasibility, impact, presentation quality | One idea per slide, in the order the rubric asks for it, readable at projector size |

## 2. Seven patterns the winner uses

| # | Pattern in the winning deck | Why it scores | What we do instead / likewise |
|---|---|---|---|
| 1 | Persistent chrome: team badge top-left, bold serif centred section title, SIH logo top-right, blue footer bar with page number | Judges can re-orient in one second when scrolling 6 PDFs | Same, generated from the template (badge = `x64`, page numbers 2–6) |
| 2 | Every slide opens with **one boxed statement of the claim**, then points — never a paragraph | Rubric line "problem understanding" is proven by structure, not prose | S2 `PROPOSED SOLUTION / APPROACH` panel: 5 bolded leads + italic "how it addresses the problem" |
| 3 | A **numbered end-to-end workflow** down the right half of S2 with arrows between steps | Shows a *system*, not a model demo | S2 right panel: 1 Query + imagery → 5 Fuse · answer · report, each step naming the PS clause it satisfies (P6, P9–P10, P11, P14) |
| 4 | Architecture drawn as **bordered zones with cards inside**, one colour per zone | Reads as engineering, not buzzwords | S3: 4 zones (inputs/validation · web frontend · agentic backend · intelligence layer) + a technology chip band + three proof panels |
| 5 | Risks written as **risk → mitigation pairs** on the same line | "Practical impact" includes having thought about failure | S4: five rows, red risk card ⇢ green strategy card, mirrored numbering 01–05 |
| 6 | Impact shown as a **hub-and-spoke audience map** + social/economic/environmental cards | Converts a tech idea into beneficiaries and numbers | S5: SatQuery AI hub (one question / one trace / six user groups) → 6 audience cards → 3 benefit cards → claim ribbon + pilot path |
| 7 | S6 leads with **their own** reading/measurements, then datasets, benchmarks, models and links | Evidence of work done, which is what the idea round actually grades | S6: "OUR PRIMARY RESEARCH" first (15 clauses mapped, 5 gaps logged, verified row counts/sizes/licences, 48 passing tests), then benchmark table, then references, then a mandate-coverage strip |

**Also copied from the winner:** pale-tint rounded panels with 1 pt borders instead of solid colour blocks; one
accent colour per semantic role (blue = product, purple = agentic, green = evidence/proof, orange = honest caveats);
numbers in every panel (dataset rows, mAP, latency, test count) so no claim is unquantified.

## 3. Anti-patterns that cost marks (checked against our deck)

* Text-heavy slides, paragraphs that a judge must read instead of the team speaking → our longest text block is 5 lines.
* No numbers anywhere → ours carries 5/5 queries, 15/15 clauses, 9.55 M rows, 467 MB, mAP 0.711, 48 tests, 10/8/20/20 s.
* Vague promises ("we will use AI and cloud") → every future item is dated inside the 15-day path strip on S4 and tied to a free/pretrained fallback.
* Buzzword architecture with no data provenance → S3 names each checkpoint and S6 names the licence (CDLA-Permissive-1.0 / BE v2.0 terms).
* Ignoring PS constraints (host hardware, mandatory baseline, offline evaluation set) → P11/P12/P14/P15 are quoted where they bind the design.
* "The AI generated it" answers in Q&A → every slide claim traces to [`ps-26167.md`](../ps-26167.md),
  [`checkpoints.md`](../checkpoints.md), [`architecture.md`](../architecture.md) or `prototype/`, so any line can be defended.

## 4. Slide-by-slide map (what to say in the 15 minutes)

| Slide | Template pointer | Core claim | Hard numbers on the page |
|---|---|---|---|
| 1 | TITLE PAGE | problem statement identity + team | 5/5 demo queries, 15 clauses, 3 models by 20 Sep, ₹0 licence |
| 2 | IDEA TITLE | an assistant that *plans over specialist tools* and proves it | 5 verbatim PS queries with their routes; 5-step workflow; 5 innovations |
| 3 | TECHNICAL APPROACH | 4-zone system, frozen tool contracts, real UI | 10 chips of stack; 4 models × their data; 48 tests; SAR-not-RGB panel |
| 4 | FEASIBILITY AND VIABILITY | fits 15 days and 6 GB VRAM; failure-proofed | 15-day path; 3 proof panels; 5 risk ⇢ strategy pairs |
| 5 | IMPACT AND BENEFITS | six user groups, three benefit classes, scales by registry entry | 6 audiences, 3 benefit cards, pilot path SAC → ISRO nodes → state cells |
| 6 | RESEARCH AND REFERENCES | we did the research and measured it ourselves | 6 primary-research bullets; benchmark/metric table; 7 references; 6 mandate-coverage ticks |

## 5. Before uploading

1. Fill **Team ID** on slide 1 (currently `_____________ (from portal)`) — the portal-generated ID, not the repo name.
2. If any text is edited in PowerPoint, keep the template's fonts (Arial body / Times New Roman headings) and re-export:
   **6 pages, 13.333 × 7.5 in, no element crossing the blue footer bar**.
3. Name the PDF for the portal slot (Idea submission → PDF only); the `.pptx` stays in the repo as the editable master.
4. Rehearse against the pointers: each slide must be explainable in ≤ 2 min 30 s using only what is on it.
