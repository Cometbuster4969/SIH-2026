"""Raster ingestion — REAL in Window A.

Format/CRS/band validation, modality detection, band-order assertion,
co-registration check for pairs, and sliding-window tiling. rasterio is a hard
dependency for GeoTIFF reads; a numpy-array constructor is provided so tests
and demo scenes run without files on disk.

v0.2.0 BIFOLD band order (version-critical — asserted here):
    [VV, VH, B02, B03, B04, B05, B06, B07, B08, B8A, B11, B12]
v0.1.1 used a different order and is incompatible; wrong order yields
confident garbage with no error, so we refuse rather than mis-feed the model.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .schemas import Modality, RasterMeta

# v0.2.0 band order — THE contract for the BIFOLD checkpoints.
BIFOLD_V020_BANDS = ["VV", "VH", "B02", "B03", "B04", "B05", "B06",
                     "B07", "B08", "B8A", "B11", "B12"]
SAR_BANDS = {"VV", "VH"}
OPTICAL_BANDS = {"B01", "B02", "B03", "B04", "B05", "B06", "B07", "B08",
                 "B8A", "B09", "B11", "B12"}

ALLOWED_EXTS = {".tif", ".tiff", ".vrt", ".png", ".jpg", ".jpeg"}


class IngestionError(ValueError):
    """E_FORMAT / E_CRS / E_BANDS style rejection (PS A2.3 guardrail)."""


@dataclass
class RasterImage:
    """A loaded raster. array shape = (bands, height, width)."""
    array: np.ndarray
    modality: Modality
    bands: list[str]
    crs: str | None = None
    transform: tuple | None = None
    path: str | None = None
    notes: list[str] = field(default_factory=list)

    @property
    def height(self) -> int:
        return self.array.shape[1]

    @property
    def width(self) -> int:
        return self.array.shape[2]

    def meta(self) -> RasterMeta:
        return RasterMeta(
            path=self.path or "<in-memory>",
            modality=self.modality,
            bands=list(self.bands),
            crs=self.crs,
            width=self.width,
            height=self.height,
            transform=list(self.transform) if self.transform else None,
            dtype=str(self.array.dtype),
            notes=list(self.notes),
        )

    def band_index(self, name: str) -> int:
        try:
            return self.bands.index(name)
        except ValueError as e:
            raise IngestionError(f"band {name} not present (have {self.bands})") from e

    def band(self, name: str) -> np.ndarray:
        return self.array[self.band_index(name)].astype(np.float32)


def detect_modality(bands: list[str]) -> Modality:
    sar = [b for b in bands if b.upper() in SAR_BANDS]
    opt = [b for b in bands if b.upper() in OPTICAL_BANDS]
    if sar and opt:
        return Modality.PAIR
    if sar:
        return Modality.SAR
    if opt:
        return Modality.OPTICAL
    return Modality.UNKNOWN


def assert_bifold_band_order(bands: list[str]) -> None:
    """Refuse a 12-band stack whose order does not match v0.2.0 exactly.

    The land-cover checkpoint was trained on that order; a permuted stack is
    silently mis-scored, so this is a hard gate (see handoff / checkpoints 0.11).
    """
    up = [b.upper() for b in bands]
    if len(up) == 12 and set(up) == set(BIFOLD_V020_BANDS) and up != BIFOLD_V020_BANDS:
        raise IngestionError(
            "12-band S1+S2 stack present but band order is not the v0.2.0 order "
            f"{BIFOLD_V020_BANDS}; got {up}. v0.1.1 order is incompatible — "
            "reorder upstream or pass bands= explicitly in v0.2.0 order."
        )


def load_raster(path: str | Path, bands: list[str] | None = None) -> RasterImage:
    """Load a GeoTIFF/other raster via rasterio and validate it."""
    try:
        import rasterio
    except ImportError as e:  # pragma: no cover
        raise IngestionError("rasterio is required to load raster files") from e

    p = Path(path)
    if p.suffix.lower() not in ALLOWED_EXTS:
        raise IngestionError(
            f"E_FORMAT: '{p.suffix}' not in allow-list {sorted(ALLOWED_EXTS)}"
        )
    with rasterio.open(p) as ds:
        arr = ds.read().astype(np.float32)          # (bands, h, w)
        crs = str(ds.crs) if ds.crs else None
        transform = tuple(ds.transform)[:6] if ds.transform else None
        # rasterio band descriptions live on ds.descriptions (may be all None).
        desc = list(ds.descriptions)
    names = [b for b in (bands or desc) if b] or [f"B{i+1}" for i in range(arr.shape[0])]
    if len(names) != arr.shape[0]:
        names = [f"B{i+1}" for i in range(arr.shape[0])]
    names = [b.upper() for b in names]
    modality = detect_modality(names)
    assert_bifold_band_order(names)
    notes: list[str] = []
    if crs is None:
        notes.append("no CRS — geo-referencing absent; pixel coords only")
    img = RasterImage(array=arr, modality=modality, bands=names,
                      crs=crs, transform=transform, path=str(p), notes=notes)
    return img


def from_array(arr: np.ndarray, bands: list[str], crs: str | None = None,
               transform: tuple | None = None) -> RasterImage:
    """Build a RasterImage from an in-memory (bands, h, w) array (tests/demos)."""
    arr = np.asarray(arr, dtype=np.float32)
    if arr.ndim != 3:
        raise IngestionError(f"expected (bands, h, w), got shape {arr.shape}")
    names = [b.upper() for b in bands]
    if len(names) != arr.shape[0]:
        raise IngestionError(f"{len(names)} band names for {arr.shape[0]} bands")
    modality = detect_modality(names)
    assert_bifold_band_order(names)
    return RasterImage(array=arr, modality=modality, bands=names,
                       crs=crs, transform=transform)


def check_coregistration(a: RasterImage, b: RasterImage,
                         tol_px: float = 2.0) -> tuple[bool, float, tuple[int, int]]:
    """Cheap co-registration check for a pair.

    With geo-transforms we compare the upper-left corner offset in pixels;
    without transforms we require identical shapes and estimate the integer
    shift that maximises cross-correlation on a shared band proxy. Returns
    (ok, offset_px, (dy, dx)).
    """
    if a.transform and b.transform and a.crs and b.crs and a.crs == b.crs:
        dx = (b.transform[0] - a.transform[0]) / (a.transform[0] or 1)
        dy = (b.transform[3] - a.transform[3]) / (abs(a.transform[4]) or 1)
        off = float(np.hypot(dx, dy))
        return off <= tol_px, off, (int(round(dy)), int(round(dx)))

    if a.array.shape[1:] != b.array.shape[1:]:
        return False, float("inf"), (0, 0)

    # Template-match a downscaled mean band to estimate shift.
    def _probe(img: RasterImage) -> np.ndarray:
        x = img.array.mean(axis=0)
        return (x - x.mean()) / (x.std() + 1e-8)

    pa, pb = _probe(a), _probe(b)
    best, best_shift = -1.0, (0, 0)
    h, w = pa.shape
    rng = range(-min(8, h // 4), min(9, h // 4 + 1))
    for dy in rng:
        for dx in rng:
            ya0, ya1 = max(0, dy), min(h, h + dy)
            yb0, yb1 = max(0, -dy), min(h, h - dy)
            xa0, xa1 = max(0, dx), min(w, w + dx)
            xb0, xb1 = max(0, -dx), min(w, w - dx)
            if ya1 <= ya0 or xa1 <= xa0:
                continue
            corr = float(np.mean(pa[ya0:ya1, xa0:xa1] * pb[yb0:yb1, xb0:xb1]))
            if corr > best:
                best, best_shift = corr, (dy, dx)
    off = float(np.hypot(*best_shift))
    return off <= tol_px, off, best_shift


def tiles(img: RasterImage, size: int = 120, overlap: int = 0):
    """Sliding-window tiles over a raster. Yields (tile_array, row, col).

    Tiling round-trip is pixel-exact when overlap == 0 and dimensions are
    multiples of size (system checkpoint D); edge tiles are clipped.
    """
    if overlap >= size:
        raise ValueError("overlap must be smaller than tile size")
    _, h, w = img.array.shape
    step = size - overlap
    for y in range(0, h, step):
        for x in range(0, w, step):
            y1, x1 = min(y + size, h), min(x + size, w)
            yield img.array[:, y:y1, x:x1], y, x


# --- Spectral indices used by the declared heuristics ------------------------

def ndvi(img: RasterImage) -> np.ndarray:
    """(NIR - Red)/(NIR + Red). Prefers B08/B04; falls back to B07/B05."""
    try:
        nir, red = img.band("B08"), img.band("B04")
    except IngestionError:
        nir, red = img.band("B07"), img.band("B05")
    return (nir - red) / (nir + red + 1e-8)


def ndbi(img: RasterImage) -> np.ndarray:
    """(SWIR - NIR)/(SWIR + NIR) using B11/B08 — built-up proxy."""
    swir, nir = img.band("B11"), img.band("B08")
    return (swir - nir) / (swir + nir + 1e-8)
