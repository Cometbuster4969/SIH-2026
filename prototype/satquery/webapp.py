"""Server-side rendering for the web GUI.

The UI never projects or interprets rasters (design §5: "all coords pre-projected
to stage by backend"). This module turns RasterImages and tool outputs into PNGs
the browser can show as layers:

  * base preview  — true-colour composite (optical), grayscale dB (SAR)
  * mask overlay  — transparent PNG tinted by mask semantics (design §5 colors)
  * bbox overlay  — cyan rectangle + label

Pure numpy + Pillow; offline, no external fonts/CDN.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from .ingestion import RasterImage, IngestionError, ndbi, ndvi

# Overlay palette (design §5)
COLOR_CHANGE_ADDED = (229, 57, 53)      # red    — bi-temporal change / added
COLOR_CHANGE_REMOVED = (253, 216, 53)   # yellow — removed
COLOR_BUILT_UP = (251, 140, 0)          # grey-orange
COLOR_WATER = (30, 136, 229)            # blue
COLOR_BBOX = (0, 229, 255)              # cyan — grounding boxes
COLOR_HEAT = (140, 80, 255)             # viridis-ish evidence heatmap


def _norm(ch: np.ndarray, lo: float | None = None, hi: float | None = None) -> np.ndarray:
    ch = ch.astype(np.float32)
    if lo is None:
        lo, hi = np.nanpercentile(ch, 2), np.nanpercentile(ch, 98)
    if hi == lo:
        hi = lo + 1e-6
    return np.clip((ch - lo) / (hi - lo), 0, 1)


def base_preview(img: RasterImage, size: int = 512) -> Image.Image:
    """Return an RGB PIL image preview of the raster."""
    h, w = img.array.shape[1:]

    def _ch(name: str) -> np.ndarray | None:
        return img.band(name) if name in img.bands else None

    r = g = b = None
    if img.modality.value in ("optical", "pair"):
        red, green, blue = _ch("B04"), _ch("B03"), _ch("B02")
        if red is not None and green is not None and blue is not None:
            r, g, b = _norm(red), _norm(green), _norm(blue)
    if r is None:  # SAR or missing RGB: VV as grayscale (dB mapped sensibly)
        vv = _ch("VV")
        if vv is None:
            vv = img.array[0]
        gray = _norm(vv, lo=float(np.nanpercentile(vv, 5)),
                     hi=float(np.nanpercentile(vv, 95)))
        r = g = b = gray
    rgb = np.dstack([r, g, b])
    pil = Image.fromarray((rgb * 255).astype(np.uint8), "RGB")
    if max(h, w) != size:
        pil = pil.resize((size, size), Image.BILINEAR)
    return pil


def mask_overlay(mask: np.ndarray, color: tuple[int, int, int],
                 alpha: int = 150, size: int = 512) -> Image.Image:
    """Transparent RGBA overlay for a binary (h, w) mask."""
    m = (mask > 0).astype(np.uint8)
    rgba = np.zeros((m.shape[0], m.shape[1], 4), dtype=np.uint8)
    rgba[..., 0] = color[0] * m
    rgba[..., 1] = color[1] * m
    rgba[..., 2] = color[2] * m
    rgba[..., 3] = alpha * m
    pil = Image.fromarray(rgba, "RGBA")
    if m.shape != (size, size):
        pil = pil.resize((size, size), Image.NEAREST)
    return pil


def bbox_overlay(bbox: list[float], label: str, shape: tuple[int, int],
                 size: int = 512) -> Image.Image:
    """Transparent RGBA overlay with a cyan box + label. bbox in source pixels."""
    h, w = shape
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    x0, y0, x1, y1 = [float(v) for v in bbox]
    draw.rectangle([x0, y0, x1, y1], outline=COLOR_BBOX + (255,), width=max(2, w // 120))
    draw.text((x0 + 3, max(0, y0 - 14)), label, fill=COLOR_BBOX + (255,))
    if (h, w) != (size, size):
        overlay = overlay.resize((size, size), Image.NEAREST)
    return overlay


def heatmap_overlay(score: np.ndarray, size: int = 512) -> Image.Image:
    """Viridis-like 50% blend heatmap from a real-valued (h,w) evidence plane."""
    s = _norm(score)
    # cheap viridis approximation
    r = np.clip(np.sin(s * np.pi) * 0.6 + s * 0.25, 0, 1)
    g = np.clip(np.sin(s * np.pi * 0.8) * 0.7, 0, 1)
    b = np.clip(0.35 + 0.65 * np.cos(s * np.pi * 0.9), 0, 1)
    rgba = np.dstack([(r * 255).astype(np.uint8), (g * 255).astype(np.uint8),
                      (b * 255).astype(np.uint8), (s * 128).astype(np.uint8)])
    pil = Image.fromarray(rgba, "RGBA")
    if score.shape != (size, size):
        pil = pil.resize((size, size), Image.BILINEAR)
    return pil


def render_result_layers(img: RasterImage, result, out_dir: Path,
                         stem: str) -> list[dict]:
    """Given a ToolResult, produce overlay layer descriptors for the frontend.

    Returns a list of {name, kind, url, color, legend} dicts. Heuristic tools save
    masks/bboxes; this re-renders them as web-friendly transparent PNGs so the
    stage layer toggles work uniformly.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    layers: list[dict] = []
    size = 512

    def _save(pil: Image.Image, name: str) -> str:
        p = out_dir / f"{stem}_{name}.png"
        pil.save(p)
        sid = out_dir.parent.name     # out_dir is SESS_DIR/<sid>/artifacts
        return f"/web/sessions/{sid}/artifacts/{p.name}"

    # Recompute planes from the image when the tool's mask artifact exists, else
    # derive from semantics so the demo shows honest heuristic evidence.
    task = result.task.value if hasattr(result.task, "value") else str(result.task)
    try:
        if task in ("change",) :
            # NDVI differencing plane isn't kept on the result; show change heatmap
            # from the saved mask artifact if present
            for art in result.artifacts:
                if art.kind == "mask" and Path(art.path).exists():
                    m = np.load(art.path)
                    layers.append({
                        "name": "change map (heuristic)", "kind": "mask",
                        "url": _save(mask_overlay(m, COLOR_CHANGE_ADDED), "change"),
                        "color": "#E53935", "legend": "changed pixels (NDVI/NDBI Δ>0.25)"})
                    break
        elif task == "ground" and result.bbox:
            layers.append({
                "name": "grounded region (heuristic)", "kind": "bbox",
                "url": _save(bbox_overlay(result.bbox, "target",
                                          img.array.shape[1:]), "bbox"),
                "color": "#00E5FF", "legend": "bounding box (pixel coords)"})
        elif task == "xmodal_mask":
            target = (result.extra or {}).get("target", "water")
            color = COLOR_WATER if "water" in target else COLOR_BUILT_UP
            try:
                plane = (ndvi(img) < -0.1) if "water" in target else (ndbi(img) > 0.1)
            except IngestionError:
                plane = None
            if plane is not None:
                layers.append({
                    "name": f"{target} mask (heuristic)", "kind": "mask",
                    "url": _save(mask_overlay(plane.astype(np.uint8), color), "mask"),
                    "color": "#1E88E5" if "water" in target else "#FB8C00",
                    "legend": f"per-pixel {target} (threshold heuristic)"})
        elif task == "vqa":
            # evidence heatmap from NDVI for water/vegetation questions
            try:
                plane = ndvi(img)
                layers.append({
                    "name": "evidence (NDVI)", "kind": "heatmap",
                    "url": _save(heatmap_overlay(plane), "heat"),
                    "color": "#8C50FF", "legend": "NDVI evidence plane"})
            except IngestionError:
                pass
    except Exception:
        # Rendering overlays must never break an answer.
        pass
    return layers


def write_base_preview(img: RasterImage, out_dir: Path, stem: str) -> str:
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"{stem}_base.png"
    base_preview(img).save(p)
    sid = out_dir.parent.name         # out_dir is SESS_DIR/<sid>/artifacts
    return f"/web/sessions/{sid}/artifacts/{p.name}"
