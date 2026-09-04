"""Declared heuristic tools for Window A.

Every tool here reports trained=False and (where appropriate) status="degraded".
They implement the SAME ToolResult contract as the future trained models, so
Window B swaps implementations without touching the orchestrator, trace, UI,
or registry. Demo answers come from a frozen cache when a scene_id is given
(the "kill switch" — the live demo never depends on GPU availability).

Artifacts: masks/boxes are saved as .npy (always) and .png (only if PIL is
installed, for the UI overlay toggles).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from ..ingestion import (IngestionError, RasterImage, ndbi, ndvi)
from ..schemas import Artifact, Modality, TaskType, ToolInput, ToolResult


def _save_mask(mask: np.ndarray, artifact_dir: Path, name: str) -> list[Artifact]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    npy_path = artifact_dir / f"{name}.npy"
    np.save(npy_path, mask.astype(np.uint8))
    arts = [Artifact(kind="mask", path=str(npy_path),
                     description=f"{name} change mask (heuristic)")]
    try:
        from PIL import Image
        png_path = artifact_dir / f"{name}.png"
        Image.fromarray((mask * 255).astype(np.uint8)).save(png_path)
        arts.append(Artifact(kind="overlay", path=str(png_path),
                             description="change overlay"))
    except Exception:
        pass
    return arts


class _Base:
    name = "base"
    task: TaskType

    def __init__(self, demo_cache: dict | None = None, artifact_dir: str | Path = "artifacts"):
        self.demo_cache = demo_cache or {}
        self.artifact_dir = Path(artifact_dir)

    def available(self) -> bool:
        return True

    def _cached(self, tin: ToolInput, task_key: str) -> ToolResult | None:
        sid = tin.params.get("scene_id")
        cache = self.demo_cache.get(task_key, {})
        hit = cache.get(sid) if sid else None
        # Demo mode with no specific scene: serve the curated cached answer for
        # this task (demo-day kill switch; answer is labelled cached/heuristic).
        if hit is None and tin.params.get("demo") and cache:
            c = next(iter(cache.values()))
        elif hit is None:
            return None
        else:
            c = hit
        return ToolResult(
            tool=self.name, task=self.task, status="ok",
            answer=c["answer"], confidence=c.get("confidence"),
            trained=False, bbox=c.get("bbox"),
            labels=c.get("labels", []),
            extra={"cached": True, **c.get("extra", {})},
        )

    def _no_image(self) -> ToolResult:
        return ToolResult(tool=self.name, task=self.task, status="abstain",
                          answer="Please supply an image for this query.",
                          trained=False)


class ChangeTool(_Base):
    name = "change_detect"
    task = TaskType.CHANGE

    def run(self, tin: ToolInput) -> ToolResult:
        cached = self._cached(tin, "change")
        if cached:
            return cached
        imgs = tin.images
        if len(imgs) < 2:
            return ToolResult(
                tool=self.name, task=self.task, status="abstain",
                answer="Change detection needs two images from different dates; "
                       "only one was provided.", trained=False)

        a, b = imgs[0], imgs[1]
        if a.array.shape[1:] != b.array.shape[1:]:
            return ToolResult(
                tool=self.name, task=self.task, status="error",
                answer="The two images have different dimensions; co-register before "
                       "change detection.", trained=False)

        method = tin.params.get("method", "ndvi_diff")
        try:
            if method == "ndbi_diff":
                ia, ib = ndbi(a), ndbi(b)
                label = "built-up index (NDBI)"
            else:
                ia, ib = ndvi(a), ndvi(b)
                label = "vegetation index (NDVI)"
        except IngestionError:
            return ToolResult(
                tool=self.name, task=self.task, status="degraded",
                answer="Heuristic change needs optical NIR/red bands; this pair lacks "
                       "them. The trained BiT change model (M4) handles this in Window B.",
                trained=False, degraded_reason="missing bands for index differencing")

        diff = np.abs(ia - ib)
        mask = (diff > 0.25).astype(np.uint8)
        pct = float(mask.mean()) * 100
        arts = _save_mask(mask, self.artifact_dir, f"change_{tin.query_id}") \
            if hasattr(tin, "query_id") else []
        answer = (f"Heuristic {label} differencing: {pct:.1f}% of pixels changed "
                  f"between the two dates (|Δindex| > 0.25). The trained BiT model "
                  f"(M4) replaces this for the 20 Sep submission.")
        return ToolResult(
            tool=self.name, task=self.task, status="degraded", answer=answer,
            confidence=None, trained=False,
            degraded_reason="declared heuristic — NDVI/NDBI differencing, not M4",
            artifacts=arts, extra={"change_pct": round(pct, 2), "method": method})


class GroundTool(_Base):
    name = "ground_object"
    task = TaskType.GROUND

    def run(self, tin: ToolInput) -> ToolResult:
        cached = self._cached(tin, "ground_object")
        if cached:
            return cached
        if not tin.images:
            return self._no_image()
        img: RasterImage = tin.images[0]
        expr = tin.params.get("expression", tin.query)
        # Declared heuristic: centre-box on a spectral hot-spot. Water -> dark
        # NDVI; built-up -> high NDBI; else image centre. No trained localisation.
        h, w = img.array.shape[1:]
        try:
            if any(k in expr.lower() for k in ("water", "river", "lake", "pond")):
                score = -ndvi(img)
            elif any(k in expr.lower() for k in ("build", "urban", "road", "construction")):
                score = ndbi(img)
            else:
                score = np.abs(ndvi(img) - ndvi(img).mean())
            cy, cx = np.unravel_index(np.argmax(score), score.shape)
        except IngestionError:
            cy, cx = h // 2, w // 2
        r = max(4, min(h, w) // 8)
        bbox = [int(max(0, cx - r)), int(max(0, cy - r)),
                int(min(w, cx + r)), int(min(h, cy + r))]
        answer = (f"Heuristic location for '{expr}': box {bbox} (pixel coords). "
                  f"Grounding-DINO-T (M3) fine-tune replaces this in Window B.")
        return ToolResult(
            tool=self.name, task=self.task, status="degraded", answer=answer,
            trained=False, degraded_reason="declared heuristic — no M3 weights",
            bbox=[float(v) for v in bbox])


class VQATool(_Base):
    name = "vqa_single"
    task = TaskType.VQA

    def run(self, tin: ToolInput) -> ToolResult:
        cached = self._cached(tin, "vqa")
        if cached:
            return cached
        if not tin.images:
            return self._no_image()
        img: RasterImage = tin.images[0]
        q = tin.query.lower()
        try:
            v = ndvi(img)
            water_frac = float((v < -0.1).mean())
            veg_frac = float((v > 0.3).mean())
        except IngestionError:
            return ToolResult(
                tool=self.name, task=self.task, status="degraded",
                answer="This single-image question needs optical bands the patch lacks; "
                       "the fine-tuned RS-VLM (M1) answers it in Window B.",
                trained=False, degraded_reason="no optical bands for index heuristic; M1 pending")

        if any(k in q for k in ("water", "river", "lake", "pond", "flood")):
            yes = water_frac > 0.05
            ans = (f"{'Yes' if yes else 'No'} — heuristic NDVI suggests "
                   f"~{water_frac*100:.0f}% water-like pixels.")
        elif any(k in q for k in ("vegetat", "forest", "crop", "green", "plant")):
            yes = veg_frac > 0.2
            ans = (f"{'Yes' if yes else 'No'} — ~{veg_frac*100:.0f}% of pixels are "
                   f"vegetation-like (NDVI > 0.3, heuristic).")
        else:
            ans = ("Heuristic band-index answer only; the fine-tuned RS-VLM (M1, "
                   "Qwen2-VL-2B QLoRA) answers open questions in Window B.")
        return ToolResult(
            tool=self.name, task=self.task, status="degraded", answer=ans,
            trained=False, degraded_reason="declared heuristic — M1 QLoRA pending")


class CaptionTool(_Base):
    name = "caption_scene"
    task = TaskType.CAPTION

    def __init__(self, demo_cache=None, artifact_dir="artifacts", landcover=None):
        super().__init__(demo_cache, artifact_dir)
        self._landcover = landcover

    def run(self, tin: ToolInput) -> ToolResult:
        cached = self._cached(tin, "caption")
        if cached:
            return cached
        if not tin.images:
            return self._no_image()
        img: RasterImage = tin.images[0]
        mods = {im.modality.value for im in tin.images}
        bits = [f"a {'+'.join(sorted(mods))} remote-sensing scene"]
        # Compose with the (possibly trained) land-cover tool — honest reuse.
        if self._landcover is not None:
            lc = self._landcover.run(tin)
            top = ", ".join(l["label"] for l in lc.labels[:3]) if lc.labels else ""
            if top:
                bits.append(f"dominant cover: {top}")
            trained_part = lc.trained
        else:
            trained_part = False
        try:
            v = ndvi(img)
            bits.append(f"mean NDVI {float(v.mean()):.2f}")
        except IngestionError:
            pass
        answer = ("Scene caption (heuristic composition): " + "; ".join(bits) + ".")
        return ToolResult(
            tool=self.name, task=self.task,
            status="ok" if trained_part else "degraded", answer=answer,
            trained=trained_part,
            degraded_reason=None if trained_part else "template caption; M1 caption head pending")


class XModalReasonTool(_Base):
    name = "xmodal_reason"
    task = TaskType.XMODAL

    def __init__(self, demo_cache=None, artifact_dir="artifacts", landcover=None):
        super().__init__(demo_cache, artifact_dir)
        self._landcover = landcover

    def run(self, tin: ToolInput) -> ToolResult:
        cached = self._cached(tin, "xmodal")
        if cached:
            return cached
        pair = [im for im in tin.images if im.modality in
                (Modality.SAR, Modality.OPTICAL, Modality.PAIR)]
        sar = [im for im in pair if im.modality in (Modality.SAR, Modality.PAIR)]
        opt = [im for im in pair if im.modality in (Modality.OPTICAL, Modality.PAIR)]
        if not sar or not opt:
            return ToolResult(
                tool=self.name, task=self.task, status="abstain",
                answer="Cross-modal reasoning needs co-registered optical AND SAR; "
                       "one modality is missing.", trained=False)
        # SAR texture (dB variance = structure/roughness) — declared heuristic.
        s = sar[0]
        sar_var = float(np.nanvar(s.array))
        trained_part = False
        cover = ""
        if self._landcover is not None:
            lc = self._landcover.run(tin)
            trained_part = lc.trained
            cover = ", ".join(l["label"] for l in lc.labels[:3])
        answer = (
            f"Cross-modal read (heuristic SAR texture{' + trained land-cover labels' if trained_part else ''}): "
            f"SAR backscatter variance {sar_var:.2f} indicates "
            f"{'high structural roughness (built/rocky)' if sar_var > 0.25 else 'smoother terrain'}; "
            f"optical side reports: {cover or 'unavailable'}. "
            f"Fusion via M1 two-image mode + M7 lands in Window B.")
        return ToolResult(
            tool=self.name, task=self.task,
            status="ok" if trained_part else "degraded", answer=answer,
            trained=trained_part,
            degraded_reason=None if trained_part else "SAR texture heuristic; M1/M7 pending")


class XModalSegmentTool(_Base):
    name = "xmodal_segment"
    task = TaskType.XMODAL_MASK

    def run(self, tin: ToolInput) -> ToolResult:
        cached = self._cached(tin, "xmodal_mask")
        if cached:
            return cached
        if not tin.images:
            return self._no_image()
        target = str(tin.params.get("target_class", "water")).lower()
        img: RasterImage = tin.images[0]
        try:
            if target in ("water", "sea", "lake", "river"):
                mask = (ndvi(img) < -0.1).astype(np.uint8)
                why = "NDVI < -0.1 (water heuristic)"
            else:
                mask = (ndbi(img) > 0.1).astype(np.uint8)
                why = "NDBI > 0.1 (built-up heuristic)"
        except IngestionError:
            return ToolResult(
                tool=self.name, task=self.task, status="degraded",
                answer="Per-pixel segmentation needs optical bands here; M7 dual UNet++ "
                       "(BIFOLD S1+S2 pretrained encoder) covers SAR-only in Window B.",
                trained=False, degraded_reason="missing bands; M7 pending")
        arts = _save_mask(mask, self.artifact_dir, f"seg_{target}_{tin.query_id}") \
            if hasattr(tin, "query_id") else []
        answer = (f"Heuristic {target} mask: {float(mask.mean())*100:.1f}% of pixels "
                  f"({why}). M7 dual UNet++ with BIFOLD pretrained encoder replaces "
                  f"this for 20 Sep.")
        return ToolResult(
            tool=self.name, task=self.task, status="degraded", answer=answer,
            trained=False, degraded_reason="threshold heuristic; M7 pending",
            artifacts=arts, extra={"target": target})
