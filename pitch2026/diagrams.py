"""Generate the infographic diagrams used by the SIH-2026 idea deck.

Outputs (PNG, white background, crisp 220 dpi):
  assets/fig_workflow.png   end-to-end agent workflow (slide 2)
  assets/fig_arch.png       4-zone system architecture   (slide 3)
  assets/fig_impact.png     impact hub & spokes skeleton (slide 5)
"""
import os
import math
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import FancyBboxPatch, Wedge, Circle, FancyArrowPatch

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
os.makedirs(ASSETS, exist_ok=True)

F = "/usr/share/fonts/truetype/"
for f in ("Arimo-Regular.ttf", "Arimo-Bold.ttf", "Arimo-Italic.ttf"):
    fm.fontManager.addfont(F + f)
plt.rcParams["font.family"] = "Arimo"

BLUE, DBLUE = "#0070C0", "#1F497D"
ORANGE, GREEN, RED, TEAL, PURPLE = "#E87722", "#2E9E5B", "#D93025", "#12B5A5", "#7030A0"
GREY, INK = "#58606A", "#101418"


class Canvas:
    """inch-aware helper: data coords + figure inches so text can be auto-fit."""

    def __init__(self, w, h, xlim, ylim):
        self.w, self.h = w, h
        self.xlim, self.ylim = xlim, ylim
        self.fig, self.ax = plt.subplots(figsize=(w, h), dpi=220)
        self.ax.set_xlim(*xlim)
        self.ax.set_ylim(*ylim)
        self.ax.axis("off")
        self.sx = w / (xlim[1] - xlim[0])   # inches per x-unit
        self.sy = h / (ylim[1] - ylim[0])   # inches per y-unit

    def _fit(self, lines, bw_in, bh_in, fs0, bold):
        fs = fs0
        while fs > 4.5:
            cw = fs * (0.600 if bold else 0.560) / 72.0     # inches per char
            lh = fs * 1.32 / 72.0                            # line height inches
            if all(len(t) * cw <= bw_in for t in lines) and len(lines) * lh <= bh_in:
                return fs
            fs -= 0.25
        return 4.5

    def box(self, x, y, w, h, text, fc, ec, tc="white", fs=9.0, bold=True, lw=1.2,
            italic=False, radius=0.5):
        self.ax.add_patch(FancyBboxPatch(
            (x, y), w, h, boxstyle=f"round,pad=0.0,rounding_size={radius}",
            fc=fc, ec=ec, lw=lw, zorder=3))
        lines = text.split("\n")
        fs = self._fit(lines, w * self.sx * 0.92, h * self.sy * 0.86, fs, bold)
        self.ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
                     color=tc, weight="bold" if bold else "normal",
                     style="italic" if italic else "normal", zorder=4, linespacing=1.3)

    def arrow(self, p0, p1, color=GREY, lw=1.4, ls="-", ms=10, rad=0.0):
        self.ax.add_patch(FancyArrowPatch(
            p0, p1, arrowstyle="-|>", mutation_scale=ms, color=color, lw=lw,
            linestyle=ls, zorder=2,
            connectionstyle=f"arc3,rad={rad}" if rad else "arc3"))

    def title(self, x, y, text, fs=9.0, color=DBLUE, ha="center"):
        self.ax.text(x, y, text, ha=ha, va="center", fontsize=fs, weight="bold", color=color)

    def save(self, name):
        self.fig.savefig(os.path.join(ASSETS, name), bbox_inches="tight",
                         pad_inches=0.03, facecolor="white")
        plt.close(self.fig)


# ------------------------------------------------------------------ workflow
def workflow():
    c = Canvas(7.02, 2.30, (0, 100), (0, 38))
    c.title(50, 36.9, "SATQUERY AI — end-to-end agentic workflow  (every step logged to trace.json)", 8.4)
    # row A
    c.box(1, 22, 24, 8, "User input\nnatural-language query +\noptical / SAR imagery", "#EAF3FB", BLUE, tc=INK, fs=7.6, bold=False)
    c.box(1, 29.8, 40, 4.4, "“What changed between these two dates, and where did the change occur?” — PS query 3",
          "#FFF4E8", ORANGE, tc=INK, fs=7.0, bold=False, italic=True)
    c.arrow((13, 30.4), (13, 30.2), lw=0.0, ms=0)          # invisible (spacing)
    c.arrow((21, 29.8), (33, 30.1), lw=1.1)
    c.box(28, 22, 14, 8, "Ingest &\ncompatibility gate\n(GDAL / rasterio)", BLUE, BLUE, fs=7.6)
    c.box(45, 22, 14, 8, "Planner\ntask id +\ntool plan", DBLUE, DBLUE, fs=7.8)
    c.box(62, 22, 16, 8, "Guardrail\nregistry scope +\nparam whitelist", PURPLE, PURPLE, fs=7.6)
    c.box(81, 22, 18, 8, "Deterministic\nfallback router\n(never crashes)", "#8064A2", "#8064A2", fs=7.4)
    c.arrow((25.2, 26), (27.8, 26))
    c.arrow((42.2, 26), (44.8, 26))
    c.arrow((59.2, 26), (61.8, 26))
    c.arrow((78.2, 26), (80.8, 26), ls=(0, (3, 2)))
    # row B
    c.box(45, 8, 54, 9, "Executor — specialist tools from registry.yaml\nM1 RS-VLM (VQA · caption · 2-image)   ·   M4 change   ·   M3 grounding   ·   M7 patch-clf",
          GREEN, GREEN, fs=7.8)
    c.box(1, 8, 19, 9, "Auditable trace\ntask · tools · params\nhashes · latency · conf", ORANGE, ORANGE, fs=7.6)
    c.box(22, 8, 10, 9, "Evidence\noverlays +\nconfidence", TEAL, TEAL, fs=7.4)
    c.box(34, 8, 9, 9, "PDF/HTML\naudit\nreport", RED, RED, fs=7.4)
    c.arrow((90, 22), (86, 17.4), ls=(0, (3, 2)))
    c.arrow((52, 22), (56, 17.4))
    c.arrow((45, 12.5), (43.2, 12.5))
    c.arrow((32, 12.5), (20.2, 12.5))
    c.arrow((22, 10.2), (14, 6.2), lw=0.0, ms=0)          # spacer
    c.ax.annotate("", xy=(20.2, 10.6), xytext=(26, 8.0),
                  arrowprops=dict(arrowstyle="-|>", color=GREY, lw=1.2, ls=(0, (3, 2))))
    c.save("fig_workflow.png")


# ------------------------------------------------------------------ architecture
def arch():
    c = Canvas(9.55, 4.55, (0, 100), (0, 47.5))
    zones = [(0.5, "ZONE 1", "Users & inputs", "#EAF3FB"),
             (25.5, "ZONE 2", "Frontend (Streamlit)", "#E9F7EE"),
             (50.5, "ZONE 3", "Agentic backend (FastAPI)", "#F3EEFA"),
             (75.5, "ZONE 4", "Intelligence layer", "#FFF4E8")]
    for x, t1, t2, col in zones:
        c.ax.add_patch(FancyBboxPatch((x, 1.0), 24.0, 41.5,
                                      boxstyle="round,pad=0.0,rounding_size=0.8",
                                      fc=col, ec="#B9C4D0", lw=0.9, zorder=0))
        c.title(x + 12, 40.4, t1, 8.0, GREY)
        c.title(x + 12, 37.8, t2, 9.4, INK)
    # zone 1
    c.box(2.5, 28.5, 20, 7, "Analyst / officer\nnatural-language query", "white", BLUE, tc=INK, fs=7.8, bold=False)
    c.box(2.5, 19.5, 20, 7, "Co-registered pair\nCartosat-2S + RISAT SAR\n(or Sentinel proxy)", "white", BLUE, tc=INK, fs=7.2, bold=False)
    c.box(2.5, 10.5, 20, 7, "Benchmark allow-list\nPNG/JPEG only for public\ndatasets (P11)", "white", BLUE, tc=INK, fs=7.0, bold=False)
    # zone 2
    c.box(27.5, 28.5, 20, 7, "Query console +\nupload & compatibility view", "white", GREEN, tc=INK, fs=7.4, bold=False)
    c.box(27.5, 20.0, 20, 6.5, "Live trace panel\ntask · tools · params · conf", "white", GREEN, tc=INK, fs=7.2, bold=False)
    c.box(27.5, 12.0, 20, 6.5, "Overlay viewer\nchange mask · boxes · caption", "white", GREEN, tc=INK, fs=7.2, bold=False)
    c.box(27.5, 4.0, 20, 6.5, "Report download\nPDF / HTML audit pack", "white", GREEN, tc=INK, fs=7.2, bold=False)
    # zone 3
    c.box(52.5, 30.5, 20, 5.5, "API gateway · auth · job queue", DBLUE, DBLUE, fs=7.8)
    c.box(52.5, 23.5, 9.4, 5.6, "Planner\n(task id)", PURPLE, PURPLE, fs=7.2)
    c.box(63.1, 23.5, 9.4, 5.6, "Guardrail\nschema + params", PURPLE, PURPLE, fs=6.8)
    c.box(52.5, 16.5, 9.4, 5.6, "Rule router\ndeterministic", "#8064A2", "#8064A2", fs=6.8)
    c.box(63.1, 16.5, 9.4, 5.6, "Executor\ntool contracts", GREEN, GREEN, fs=7.0)
    c.box(52.5, 9.0, 20, 6, "Trace store (SQLite)\ntrace.json · hashes · latency", ORANGE, ORANGE, fs=7.2)
    c.box(52.5, 2.0, 20, 5.6, "Confidence calibrator\nbadges + optical↔SAR\ndisagreement rule", TEAL, TEAL, fs=6.8)
    # zone 4
    c.box(77.5, 30.5, 20, 5.5, "registry.yaml + GET /tools\npredefined registry (P7)", RED, RED, fs=7.4)
    c.box(77.5, 23.5, 20, 5.6, "M1 · Qwen2-VL-2B QLoRA\nRS-VLM: VQA · caption ·\ngrounding · 2-image (S1+S2)", "white", ORANGE, tc=INK, fs=6.8, bold=False)
    c.box(77.5, 16.5, 9.4, 5.6, "M4 · BiT\nchange map +\nchange-VQA", "white", ORANGE, tc=INK, fs=6.4, bold=False)
    c.box(88.1, 16.5, 9.4, 5.6, "M3 · Ground.\nDINO-T\ntext → box", "white", ORANGE, tc=INK, fs=6.4, bold=False)
    c.box(77.5, 9.0, 20, 5.6, "M7 · UNet++ patch classifier\nbuilt-up / water (BE v2)", "white", ORANGE, tc=INK, fs=6.8, bold=False)
    c.box(77.5, 2.0, 20, 5.6, "Fine-tuned on BigEarthNet.txt\nS1–S2–text triplets (P2, P5)", "#FDE3CF", ORANGE, tc=INK, fs=7.0, bold=False)
    # arrows
    for y in (32.0, 23.0, 14.0):
        c.arrow((22.7, y), (27.3, y), lw=1.1)
    for y in (32.0, 23.2, 15.2, 7.2):
        c.arrow((47.7, y), (52.3, y), lw=1.1)
    c.arrow((57.2, 23.5), (57.2, 30.3), lw=1.0)
    c.arrow((67.8, 23.5), (67.8, 30.3), lw=1.0)
    c.arrow((57.2, 16.5), (57.2, 23.3), lw=1.0)
    c.arrow((67.8, 16.5), (67.8, 23.3), lw=1.0)
    c.arrow((62.5, 16.3), (62.5, 15.2), lw=1.0)
    c.arrow((72.7, 19.3), (77.3, 26.3), lw=1.1)
    c.arrow((72.7, 11.8), (77.3, 19.3), lw=1.1)
    c.arrow((72.7, 4.8), (77.3, 11.8), lw=1.1)
    c.arrow((77.3, 33.2), (72.7, 33.2), lw=1.1)
    c.title(50, 45.6, "System architecture — sensor-agnostic 512 px tiles / 64 px overlap, end-to-end", 9.0)
    c.save("fig_arch.png")


# ------------------------------------------------------------------ impact hub
def impact():
    c = Canvas(7.30, 4.35, (0, 100), (0, 60))
    cx, cy, r = 50, 30, 12.0
    c.ax.add_patch(Circle((cx, cy), r + 4.4, fc="none", ec=GREY, lw=1.0, ls=(0, (2, 2.4)), zorder=1))
    for a0, a1, col in [(90, 210, ORANGE), (210, 330, TEAL), (330, 450, BLUE)]:
        c.ax.add_patch(Wedge((cx, cy), r, a0, a1, width=4.4, fc=col, ec="white", lw=1.4, zorder=2))
    c.title(cx, cy + 2.6, "Potential impact", 9.4, INK)
    c.title(cx, cy - 2.8, "on targeted audience", 8.4, DBLUE)
    for (px, py) in [(50, 58.6), (15.0, 46.0), (85.0, 46.0), (15.0, 12.5), (85.0, 12.5)]:
        dx, dy = px - cx, py - cy
        n = math.hypot(dx, dy)
        sx, sy = cx + dx / n * (r + 4.4), cy + dy / n * (r + 4.4)
        c.ax.plot([sx, px], [sy, py], color=INK, lw=1.2, zorder=1)
        c.ax.add_patch(Circle((px, py), 1.5, fc="white", ec=BLUE, lw=1.6, zorder=3))
    c.save("fig_impact.png")


if __name__ == "__main__":
    workflow(); arch(); impact()
    for f in sorted(os.listdir(ASSETS)):
        print(f, os.path.getsize(os.path.join(ASSETS, f)))
