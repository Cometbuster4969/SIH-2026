import numpy as np
import pytest

from satquery.ingestion import (BIFOLD_V020_BANDS, IngestionError,
                                assert_bifold_band_order, check_coregistration,
                                detect_modality, from_array, ndvi, tiles)
from satquery.schemas import Modality


def _optical(h=120, w=120, seed=0):
    rng = np.random.default_rng(seed)
    bands = ["B02", "B03", "B04", "B08"]
    arr = rng.uniform(0, 0.5, (4, h, w)).astype(np.float32)
    return from_array(arr, bands)


def test_modality_detection():
    assert detect_modality(["B04", "B08"]) == Modality.OPTICAL
    assert detect_modality(["VV", "VH"]) == Modality.SAR
    assert detect_modality(["VV", "B04", "B08"]) == Modality.PAIR
    assert detect_modality(["X"]) == Modality.UNKNOWN


def test_wrong_band_order_refused():
    bad = ["B02", "B03", "B04", "VV", "VH", "B05", "B06",
           "B07", "B08", "B8A", "B11", "B12"]
    with pytest.raises(IngestionError, match="v0.2.0"):
        assert_bifold_band_order(bad)


def test_correct_band_order_passes():
    assert_bifold_band_order(BIFOLD_V020_BANDS)  # no raise


def test_from_array_shape_check():
    with pytest.raises(IngestionError):
        from_array(np.zeros((120, 120), np.float32), ["B04"])


def test_ndvi_range():
    img = _optical()
    v = ndvi(img)
    assert v.shape == (120, 120)
    assert np.all(v > -1.01) and np.all(v < 1.01)


def test_tiling_coverage_no_overlap():
    img = _optical(h=240, w=240)
    covered = np.zeros((240, 240), dtype=np.int32)
    n = 0
    for tile, y, x in tiles(img, size=120):
        covered[y:y + tile.shape[1], x:x + tile.shape[2]] += 1
        n += 1
    assert n == 4
    assert np.all(covered == 1)   # pixel-exact, no double coverage


def test_coreg_identical_images_ok():
    a = _optical(seed=1)
    b = _optical(seed=1)
    ok, off, shift = check_coregistration(a, b)
    assert ok and off == 0.0 and shift == (0, 0)


def test_coreg_shifted_image_detected():
    a = _optical(seed=2)
    shifted = np.roll(a.array, 6, axis=2)
    b = from_array(shifted, a.bands)
    ok, off, shift = check_coregistration(a, b, tol_px=2.0)
    assert not ok
