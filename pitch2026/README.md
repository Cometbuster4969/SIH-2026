# SatQuery AI — SIH 2026 Round-1 Idea Deck (PS 26167, ISRO)

Deliverables (repo root):

| File | Purpose |
|---|---|
| `SatQuery-AI-SIH2026-Idea-Deck.pptx` | Editable deck, built **on the official `SIH2026-IDEA-Presentation-Format.pptx` template** (masters, footer bar, SIH-2026 logo and title-slide art kept; the "Important instructions" slide removed as the template itself permits). |
| `SatQuery-AI-SIH2026-Idea-Deck.pdf` | **Upload this on the SIH portal** (the portal accepts PDF only). Rendered at identical geometry to the PPTX. |

Six slides, exactly the SIH-2026 section order:
1. Title page (PS ID / title / theme / category / team fields)
2. Idea title — proposed solution, how it addresses the problem, innovation & uniqueness
3. Technical approach — architecture, implementation process, technology stack
4. Feasibility & viability — feasibility/viability/practicality + risks ↔ strategies
5. Impact & benefits — stakeholder hub + social/economic/environmental
6. Research & references — PS-named datasets, models, our groundwork, benchmark gates

## How the two outputs stay identical

`build_deck.py` holds **one layout spec** (inch coordinates, shapes, rich-text
paragraphs, images) and renders it twice:

* `render_pptx()` — python-pptx on top of the official template (native, editable text).
* `render_pdf()` — PyMuPDF vector/text rendering (no LibreOffice in this environment;
  Spire's free converter drops text and caps at 3 slides, so it was rejected).

`diagrams.py` regenerates the three matplotlib infographics in `assets/`
(`fig_workflow.png`, `fig_arch.png`, `fig_impact.png`).
`assets/sih_logo.png` / `sih_bulb.png` are extracted from the template package
(the 2026 logo, and the bulb art = template `image1.png` cropped at 59.916 % exactly
like the template's `srcRect`).

### Rebuild

```bash
pip install --break-system-packages python-pptx pymupdf matplotlib pillow
# fonts used for PDF rendering (metric-compatible with the template faces):
#   Arial→Arimo, Times New Roman→Tinos, Calibri→Carlito  (installed under
#   /usr/share/fonts/truetype in the build sandbox)
python3 diagrams.py
python3 build_deck.py
```

Visual QA loop: render the PDF pages to PNG (`pymupdf`) and inspect; every element
position lives in `build_deck.py` slide functions (`slide1()…slide6()`).

## Before submitting — fill these in

* **Team Name**: set to `x64`. **Team ID**: still `[ to be filled ]` on slide 1 — edit in
  `build_deck.py` (slide1 fields + `chrome_for`/`_apply_slide_texts` badge)
  (`slide1()` fields, `chrome_for()` badge, `_apply_slide_texts()` badge + fields)
  and re-run, or edit the PPTX directly and re-export only if you also update the PDF.
* Honesty line for the stage (from `proposedidea.md` §4): the overlays on slide 2 are
  **real outputs of the thin Window-A prototype**; say "specialist models are
  fine-tuned for the 20 Sep submission".

## Source material

Content is distilled from `ps-26167.md` (clauses P1–P15), `architecture.md`,
`proposedidea.md`, `checkpoints.md` and the working prototype archived in
`workspace-01a0662*.zip` (overlay screenshots on slide 2 come from its `runs/`).
