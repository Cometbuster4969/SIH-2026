"""Generate frozen synthetic demo GeoTIFFs under data/demo/.

Spectral-consistent (vegetation = high NIR, water = low NIR/red, built-up =
low NIR + higher red) so the declared heuristic tools behave sensibly on stage.
These are NOT satellite data — the demo cache (config/demo_cache.json) carries
the canned trained-model answers for the land-cover tool, and the on-stage
honesty line says exactly which part is real.

    python scripts/make_demo_scenes.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

OUT = Path(__file__).resolve().parent.parent / "data" / "demo"
SIZE = 120


def _optical(kind: str, seed: int) -> tuple[np.ndarray, list[str]]:
    rng = np.random.default_rng(seed)
    bands = ["B02", "B03", "B04", "B08"]
    layers = {b: rng.uniform(0.05, 0.18, (SIZE, SIZE)).astype(np.float32)
              for b in bands}
    layers["B08"] = rng.uniform(0.35, 0.6, (SIZE, SIZE)).astype(np.float32)
    layers["B03"] = rng.uniform(0.08, 0.2, (SIZE, SIZE)).astype(np.float32)
    if kind == "rural":
        layers["B08"][80:110, 60:95] = 0.02      # water
        layers["B04"][80:110, 60:95] = 0.03
        layers["B02"][80:110, 60:95] = 0.06
    else:  # urban fringe
        layers["B08"][20:60, 20:70] = 0.12       # built-up
        layers["B04"][20:60, 20:70] = 0.22
    return np.stack([layers[b] for b in bands]), bands


def _sar(seed: int) -> tuple[np.ndarray, list[str]]:
    rng = np.random.default_rng(seed)
    # dB values: smooth surfaces (water) very dark, rough/built bright.
    vv = rng.normal(-12, 2.5, (SIZE, SIZE)).astype(np.float32)
    vh = rng.normal(-18, 2.5, (SIZE, SIZE)).astype(np.float32)
    vv[80:110, 60:95] = -22      # water-like specular
    vh[80:110, 60:95] = -27
    return np.stack([vv, vh]), ["VV", "VH"]


def _write(path: Path, arr: np.ndarray, bands: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    transform = from_origin(500000, 5000000, 10, 10)   # 10 m, UTM-ish
    with rasterio.open(path, "w", driver="GTiff", height=SIZE, width=SIZE,
                       count=len(bands), dtype="float32",
                       crs="EPSG:32633", transform=transform) as ds:
        ds.write(arr)
        for i, b in enumerate(bands, start=1):
            ds.set_band_description(i, b)


def main():
    scenes = [
        ("optical_scene1_rural.tif", _optical("rural", 7)),
        ("optical_scene2_urban.tif", _optical("urban", 11)),
        ("sar_scene1.tif", _sar(7)),
    ]
    for name, (arr, bands) in scenes:
        _write(OUT / name, arr, bands)
        print(f"wrote {OUT / name} {arr.shape} bands={bands}")


if __name__ == "__main__":
    main()
