"""Land-cover tool — the one genuinely trained RS tool in Window A.

Weights: BIFOLD-BigEarthNetv2-0/resnet50-all-v0.2.0 (TU Berlin/reBEN),
23.6 M params, mAP macro 0.7107 / micro 0.8593 on the BE v2.0 test split.
Loading follows the official model card:

    from reben_publication.BigEarthNetv2_0_ImageClassifier
        import BigEarthNetv2_0_ImageClassifier
    model = BigEarthNetv2_0_ImageClassifier.from_pretrained(
        "BIFOLD-BigEarthNetv2-0/resnet50-all-v0.2.0")

Requirements (pip): torch, torchvision, configilm, safetensors, huggingface-hub
PLUS the reBEN code: git clone https://git.tu-berlin.de/rsim/reben-training-scripts
(importable as `reben_publication`). It is NOT plain AutoModel.

If any of that is missing, the tool runs a declared spectral-index heuristic
and reports status="degraded" — the demo never crashes, and the answer card
never pretends the heuristic is the trained model (on-stage honesty line).

Band order v0.2.0 (asserted upstream in ingestion):
    [VV, VH, B02, B03, B04, B05, B06, B07, B08, B8A, B11, B12]
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np

from ..ingestion import (BIFOLD_V020_BANDS, IngestionError, RasterImage, ndvi)
from ..schemas import Artifact, TaskType, ToolInput, ToolResult

MODEL_ID = os.environ.get("SATQUERY_LANDCOVER_MODEL",
                          "BIFOLD-BigEarthNetv2-0/resnet50-all-v0.2.0")
MODEL_VERSION = "resnet50-all-v0.2.0"
INPUT_SIZE = 120          # trained at 120x120 px @ 10 m Sentinel

# Fallback labels ONLY when the model cannot report its own class list.
# BigEarthNet v1 19-class CLC legend; v2.0 uses the refined reBEN label set —
# the real class names are read from the loaded model at runtime.
# TODO(checkpoints 0.11): confirm exact v2.0 class names/order from
# reben_publication and pin them here.
FALLBACK_LABELS = [
    "Agro-forestry areas", "Arable land", "Beaches, dunes, sands",
    "Broad-leaved forest", "Coastal wetlands", "Coniferous forest",
    "Industrial or commercial units", "Inland waters",
    "Mixed forest", "Moors and heathland", "Natural grassland",
    "Pastures", "Permanently irrigated land", "Rice fields",
    "Salt marshes", "Sclerophyllous vegetation", "Sea and ocean",
    "Transitional woodland/shrub", "Urban fabric",
]


class LandcoverTool:
    name = "landcover"
    task = TaskType.LANDCOVER

    def __init__(self, demo_cache: dict | None = None, artifact_dir: str | Path = "artifacts"):
        self.demo_cache = demo_cache or {}
        self.artifact_dir = Path(artifact_dir)
        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        self._model = None
        self._model_classes: list[str] | None = None
        self._unavailable_reason: str | None = None

    # -- model lifecycle -----------------------------------------------------

    def available(self) -> bool:
        """True only if the genuinely trained weights can run."""
        return self._try_load(silent=True)

    def _try_load(self, silent: bool = False) -> bool:
        if self._model is not None:
            return True
        try:
            import torch  # noqa: F401
            from reben_publication.BigEarthNetv2_0_ImageClassifier import (
                BigEarthNetv2_0_ImageClassifier,
            )
        except Exception as e:  # torch/configilm/reben code missing
            self._unavailable_reason = (
                f"trained weights unavailable ({type(e).__name__}: {e}); "
                "need torch + configilm + reben_publication code — see tools/landcover.py"
            )
            if not silent:
                print(f"[landcover] {self._unavailable_reason}")
            return False
        try:
            self._model = BigEarthNetv2_0_ImageClassifier.from_pretrained(MODEL_ID)
            self._model.eval()
            self._model_classes = (
                getattr(self._model, "classes", None)
                or getattr(getattr(self._model, "config", None), "id2label", None)
                and [v for _, v in sorted(self._model.config.id2label.items())]
            ) or FALLBACK_LABELS
            return True
        except Exception as e:  # weights download failed, offline, etc.
            self._unavailable_reason = f"model load failed: {type(e).__name__}: {e}"
            if not silent:
                print(f"[landcover] {self._unavailable_reason}")
            return False

    # -- run -----------------------------------------------------------------

    def run(self, tin: ToolInput) -> ToolResult:
        if not tin.images:
            return self._abstain("no image supplied for land-cover classification")

        # Cached-answer kill switch: frozen demo answers never depend on the GPU.
        cache_key = tin.params.get("scene_id")
        cache = self.demo_cache.get("landcover", {})
        cached = cache.get(cache_key) if cache_key else None
        if cached is None and tin.params.get("demo") and cache:
            cached = next(iter(cache.values()))   # curated demo answer (labelled)
        if cached is not None:
            return ToolResult(
                tool=self.name, task=self.task, status="ok",
                answer=cached["answer"], confidence=cached.get("confidence"),
                trained=True, model_version=MODEL_VERSION + " (cached demo)",
                labels=cached.get("labels", []),
                extra={"cached": True},
            )

        if not self._try_load():
            return self._heuristic(tin)

        return self._infer(tin)

    def _infer(self, tin: ToolInput) -> ToolResult:
        import torch
        from PIL import Image

        img: RasterImage = tin.images[0]
        threshold = float(tin.params.get("threshold", 0.5))

        # Build the 12-channel v0.2.0 input. Optical-only/SAR-only checkpoints
        # exist too; the '-all' checkpoint wants the full stack — missing bands
        # are zero-filled and flagged (better: use the matching -s1-/-s2- ckpt).
        stack = np.zeros((12, INPUT_SIZE, INPUT_SIZE), dtype=np.float32)
        present = set()
        for i, band in enumerate(BIFOLD_V020_BANDS):
            if band in img.bands:
                ch = img.band(band)
                ch = _square_resize(ch, INPUT_SIZE)
                stack[i] = ch
                present.add(band)
        if present != set(BIFOLD_V020_BANDS):
            missing = [b for b in BIFOLD_V020_BANDS if b not in present]
            img.notes.append(f"landcover: zero-filled missing bands {missing}; "
                             "prefer the -s1-/-s2- checkpoint for single modality")

        with torch.no_grad():
            logits = self._model(torch.from_numpy(stack).unsqueeze(0))
            probs = torch.sigmoid(logits).squeeze(0).cpu().numpy()

        labels = [
            {"label": cls, "score": float(p)}
            for cls, p in zip(self._model_classes or FALLBACK_LABELS, probs)
        ]
        labels.sort(key=lambda d: d["score"], reverse=True)
        active = [l for l in labels if l["score"] >= threshold] or labels[:3]
        names = [l["label"] for l in active]
        answer = "Land cover: " + ", ".join(names) + (
            f" (top score {labels[0]['score']:.2f})." if labels else "")
        return ToolResult(
            tool=self.name, task=self.task, status="ok", answer=answer,
            confidence=float(labels[0]["score"]) if labels else None,
            trained=True, model_version=MODEL_VERSION, labels=labels,
            extra={"n_bands_present": len(present)},
        )

    # -- declared heuristic fallback ----------------------------------------

    def _heuristic(self, tin: ToolInput) -> ToolResult:
        """Spectral-index placeholder. DECLARED heuristic — status=degraded."""
        img: RasterImage = tin.images[0]
        labels: list[dict] = []
        try:
            veg = float(np.clip((ndvi(img).mean() + 1) / 2, 0, 1))
            labels.append({"label": "vegetation index (heuristic)", "score": veg})
        except IngestionError:
            veg = None
        if img.modality.value == "sar":
            labels.append({"label": "SAR-only patch (heuristic, structural texture)",
                           "score": 0.5})
        answer = ("Heuristic land-cover estimate (trained weights not loaded): "
                  + "; ".join(f"{l['label']} {l['score']:.2f}" for l in labels))
        return ToolResult(
            tool=self.name, task=self.task, status="degraded", answer=answer,
            confidence=None, trained=False,
            degraded_reason=self._unavailable_reason or "weights unavailable",
            labels=labels, model_version=None,
        )

    def _abstain(self, why: str) -> ToolResult:
        return ToolResult(tool=self.name, task=self.task, status="abstain",
                          answer="I cannot classify land cover without an image.",
                          trained=False, degraded_reason=why)


def _square_resize(ch: np.ndarray, size: int) -> np.ndarray:
    """Bilinear-ish resize of a 2-D band to size x size without PIL/torch."""
    if ch.shape == (size, size):
        return ch
    h, w = ch.shape
    ys = np.linspace(0, h - 1, size)
    xs = np.linspace(0, w - 1, size)
    y0 = np.floor(ys).astype(int); y1 = np.clip(y0 + 1, 0, h - 1)
    x0 = np.floor(xs).astype(int); x1 = np.clip(x0 + 1, 0, w - 1)
    wy = (ys - y0)[:, None]; wx = (xs - x0)[None, :]
    top = ch[y0][:, x0] * (1 - wx) + ch[y0][:, x1] * wx
    bot = ch[y1][:, x0] * (1 - wx) + ch[y1][:, x1] * wx
    return top * (1 - wy) + bot * wy
