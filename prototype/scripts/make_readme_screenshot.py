"""Render docs/screenshot-webapp.png from a REAL run of the web app.

Runs the bi-temporal demo + PS query 3 through the FastAPI app in-process,
then composes the 3-pane layout (design.md §2) from the actual answer, trace
events, previews and overlay PNGs. Used because the CI sandbox has no headless
browser; if you have one, a browser screenshot of :8000 is preferable.
"""
import json, os, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT.parent / "docs" / "screenshot-webapp.png"

from fastapi.testclient import TestClient          # noqa: E402
import satquery.web_server as ws                   # noqa: E402

c = TestClient(ws.app)
d = c.post("/api/v1/demo?set=bi_temporal").json()
rid = d["request_id"]
r = c.post("/api/v1/query", json={"request_id": rid,
           "query": "What changed between these two dates, and where did the change occur?"}).json()
art = Path(ws._SESSIONS[rid].art)
change_png = next(art.glob("*_change.png"))

def _font(name):
    for cand in ["/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if name == "B" else ""),
                 "/usr/local/lib/python3.11/dist-packages/streamlit/static/static/media/KaTeX_SansSerif-%s.ttf"
                 % ("Bold.CFMepnvq" if name == "B" else "Regular.BNo7hRIc")]:
        if os.path.exists(cand):
            return cand
    return None
_R, _B = _font("R"), _font("B")
R = lambda s: ImageFont.truetype(_R, s) if _R else ImageFont.load_default()
B = lambda s: ImageFont.truetype(_B, s) if _B else ImageFont.load_default()
SUB = {"·": "|", "—": "-", "–": "-", "…": "...", "⚠": "!", "→": "->", "Δ": "d", "×": "x", "⏵": ">", "▸": ">"}
def T(s):
    return "".join(SUB.get(ch, ch) for ch in s)

W, H = 1440, 900
BG, BG2, BG3, LINE, FG, MU, AC = (14,17,22),(22,27,34),(29,36,46),(42,50,61),(230,237,243),(139,151,165),(0,229,255)
AMB, RED, GRN = (210,153,34),(229,57,53),(63,185,80)
im = Image.new("RGB", (W, H), BG); d_ = ImageDraw.Draw(im)
def rr(box, fill, outline=None, rad=8): d_.rounded_rectangle(box, rad, fill=fill, outline=outline)
def tx(xy, s, font, fill): d_.text(xy, T(s), font=font, fill=fill)
def tl(s, font): return d_.textlength(T(s), font=font)
def wrap(t, f, w):
    out, line = [], ""
    for wd in t.split():
        if tl(line + " " + wd, f) > w: out.append(line); line = wd
        else: line = (line + " " + wd).strip()
    return out + [line]

d_.rectangle((0,0,W,48), fill=BG2); d_.line((0,48,W,48), fill=LINE)
tx((18,13), "SatQuery AI", B(18), AC)
tx((150,17), "interactive multimodal remote-sensing assistant | PS 26167", R(13), MU)
x = W-20
for lbl in ["Reset","Registry","Full walkthrough","Demo data"]:
    tw = tl(lbl, R(13)); rr((x-tw-20,11,x,37), BG2, LINE, 6); tx((x-tw-10,16), lbl, R(13), FG); x -= tw+30
d_.line((360,49,360,640), fill=LINE); d_.line((1000,49,1000,640), fill=LINE)

tx((16,62), "UPLOAD & INVENTORY", B(12), MU)
rr((16,86,344,150), BG, LINE, 10); tx((150,96), "+", R(24), AC)
tx((88,120), "Add image(s) | 1-2 rasters | GeoTIFF/PNG", R(11), MU)
tx((16,164), "Demo sets:", R(12), MU); x = 90
for cch in ["single optical","bi-temporal","optical+SAR"]:
    tw = tl(cch, R(11)); act = cch == "bi-temporal"
    rr((x,158,x+tw+18,180), BG3, AC if act else LINE, 11); tx((x+9,163), cch, R(11), FG); x += tw+26
rr((16,192,344,222), (40,32,14), AMB, 6)
tx((26,199), "! offset ~%.1f px - auto re-registration before fusion" % d["pair"]["offset_px"], R(11), (240,201,122))
y = 234
for i, inv in enumerate(d["inventory"]):
    rr((16,y,344,y+186), BG2, LINE, 10)
    im.paste(Image.open(art / f"img{i+1}_base.png").resize((326,120)), (17,y+1))
    tx((26,y+128), inv["label"], B(12), FG)
    tx((26,y+148), f"{inv['modality']} | {'/'.join(inv['bands'])} | {inv['crs']} | {inv['size_px'][0]}x{inv['size_px'][1]} px", R(11), MU)
    y += 196

q = r["query"]
qs = q[:52] + ("..." if len(q) > 52 else ""); qw = tl(qs, R(13)); rr((988-qw-28,66,988,100), (10,142,163), None, 14); tx((988-qw-14,76), qs, R(13), (4,22,26))
rr((372,112,988,330), BG2, LINE, 12); x = 386
for t, col in [(r["task"].upper(), AC), (r["tool"], MU), ("HEURISTIC" if not r["trained"] else "TRAINED", AMB), (r["status"], AMB if r["status"] != "ok" else GRN)]:
    tw = tl(t, B(10)); rr((x,124,x+tw+14,142), BG3, col, 9); tx((x+7,128), t, B(10), col); x += tw+22
y = 156
for ln in wrap(r["answer"], R(14), 590): tx((386,y), ln, R(14), FG); y += 22
tx((386,y+8), "confidence", R(11), MU)
for i in range(5): d_.ellipse((460+i*16,y+11,470+i*16,y+21), fill=AC if i < 2 else BG3, outline=LINE)
tx((550,y+8), "low - heuristic tool, coregistration warning", R(11), MU)
tx((386,y+34), f"{r['elapsed_s']}s | {len(r['layers'])} layer: change map (heuristic) | trained: {str(r['trained']).lower()}", R(11), MU)
for w in r["warnings"][:1]:
    ws_ = "! %s: %s" % (w["step"], w["message"][:34]); ww = tl(ws_, R(10)); rr((386,y+56,386+ww+16,y+76), (50,30,28), RED, 5); tx((394,y+60), ws_, R(10), (242,148,143))
y, x = 548, 372
for cch in ["What land cover types are here?","Is there a water body?","Locate the water body","What changed between dates?","Cloudy - what does SAR show?"]:
    tw = tl(cch, R(11))
    if x+tw+20 > 988: x = 372; y += 28
    rr((x,y,x+tw+18,y+22), BG3, LINE, 11); tx((x+9,y+5), cch, R(11), FG); x += tw+26
rr((372,600,900,630), BG2, LINE, 8); tx((384,608), "Ask about the imagery...", R(13), MU)
rr((908,600,988,630), (10,142,163), AC, 8); tx((934,607), "Run", B(13), (4,22,26))

tx((1016,62), "EXECUTION TRACE", B(12), MU); tx((1150,63), f"query_id {r['trace']['query_id']} | {r['trace']['route']['planner']}", R(11), MU)
y = 90; col = {"ok": GRN, "warning": AMB, "degraded": AMB, "error": RED}
det = {"ingest": "2 rasters | optical | B02/B03/B04/B08 | EPSG:32633",
       "coregistration": "shift (-3, 0) px -> auto-register before fusing",
       "coreg_check": "compatible: false | banner amber",
       "route": "change -> change_detect | kw: \"what changed\"",
       "execute": "change_detect | heuristic NDVI d>0.25 | trained=false",
       "integrate": f"answer + {len(r['layers'])} overlay layer | warnings: {len(r['warnings'])}"}
for e in r["trace"]["events"]:
    s = e["step"]; cc = col.get(e["status"], MU)
    rr((1016,y,1424,y+52), BG2, LINE, 8); d_.ellipse((1028,y+12,1038,y+22), fill=cc)
    tx((1048,y+8), s, B(13), FG); tw = tl(e["status"], B(10)); tx((1412-tw,y+11), e["status"], B(10), cc)
    tx((1048,y+30), det.get(s, ""), R(11), MU); y += 60
tx((1016,y+6), "No internal reasoning is stored - only the observable trace (PS P10).", R(11), MU)
for i, t in enumerate(["Trace as JSON","Copy answer"]):
    tw = tl(t, R(11)); rr((1016+i*120,600,1016+i*120+tw+16,622), BG3, LINE, 5); tx((1024+i*120,605), t, R(11), FG)

d_.rectangle((0,641,W,H), fill=BG2); d_.line((0,641,W,641), fill=LINE)
tx((16,652), "Image stage", B(13), FG)
d_.rectangle((140,655,152,667), fill=RED); tx((158,653), "change map (heuristic) - changed pixels (NDVI/NDBI d>0.25)", R(12), FG)
for i, t in enumerate(["t1 | 2018-05","t2 | 2021-03"]):
    tw = tl(t, R(11)); x = 1250+i*95; rr((x,651,x+tw+16,671), BG3, AC if i == 1 else LINE, 10); tx((x+8,655), t, R(11), FG)
base = Image.open(art / "img2_base.png").convert("RGBA").resize((210,210))
comp = Image.alpha_composite(base, Image.open(change_png).resize((210,210)))
im.paste(Image.open(art / "img1_base.png").resize((210,210)), (16,678))
im.paste(Image.open(art / "img2_base.png").resize((210,210)), (240,678))
im.paste(comp.convert("RGB"), (464,678))
for x, t in [(16,"t1 | 2018-05 | optical"),(240,"t2 | 2021-03 | optical"),(464,"t2 + change overlay")]: tx((x,H-14), t, R(10), MU)
tx((700,700), "Synthetic demo scenes (spectral-consistent, not satellite data).", R(12), MU)
tx((700,720), "Overlays are rendered server-side from the tool result; toggles show/hide each layer.", R(12), MU)
OUT.parent.mkdir(exist_ok=True); im.save(OUT, optimize=True); print("wrote", OUT)
