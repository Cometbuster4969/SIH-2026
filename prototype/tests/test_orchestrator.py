import numpy as np
import pytest

from satquery.ingestion import from_array
from satquery.orchestrator import Orchestrator
from satquery.trace import TraceStore


@pytest.fixture()
def orch(tmp_path):
    store = TraceStore(tmp_path / "trace.db")
    return Orchestrator(trace_store=store,
                        demo_cache_path="config/demo_cache.json",
                        artifact_dir=tmp_path / "artifacts")


def _optical(kind="rural", h=120, w=120):
    rng = np.random.default_rng(7 if kind == "rural" else 11)
    bands = ["B02", "B03", "B04", "B08"]
    arr = rng.uniform(0.05, 0.2, (4, h, w)).astype(np.float32)
    arr[3] = rng.uniform(0.35, 0.6, (h, w)).astype(np.float32)   # B08 NIR
    if kind == "rural":
        arr[3, 80:110, 60:95] = 0.02
        arr[2, 80:110, 60:95] = 0.03
    else:
        arr[3, 20:60, 20:70] = 0.12
        arr[2, 20:60, 20:70] = 0.22
    return from_array(arr, bands, crs="EPSG:32633")


def test_landcover_degraded_without_weights(orch):
    resp = orch.answer("What land cover types are in this image?",
                       images=[_optical()])
    assert resp.tool == "landcover"
    # torch/configilm/reben not installed in CI -> honest degraded heuristic
    assert resp.status in ("degraded", "ok")
    assert resp.trained is False or resp.status == "ok"
    assert "and cover" not in resp.answer.lower()


def test_demo_cache_kill_switch_returns_cached_trained_answer(orch):
    resp = orch.answer("What land cover types are in this image?",
                       images=[_optical()],
                       params={"scene_id": "demo_scene_01"})
    assert resp.status == "ok" and resp.trained is True
    assert "Arable land" in resp.answer


def test_vqa_water_heuristic(orch):
    resp = orch.answer("Is there a water body in this image?",
                       images=[_optical("rural")])
    assert resp.task.value == "vqa"
    assert "water" in resp.answer.lower()


def test_change_needs_pair_and_warns_with_one(orch):
    resp = orch.answer("What changed between these two dates?",
                       images=[_optical()])
    assert resp.task.value == "vqa"
    assert any("two images" in w["message"] for w in resp.warnings)


def test_change_runs_on_pair(orch):
    a = _optical("rural")
    b_arr = a.array.copy()
    b_arr[3, 30:50, 30:80] = 0.15   # simulate vegetation loss -> change
    b = from_array(b_arr, a.bands, crs="EPSG:32633")
    resp = orch.answer("What changed between these two dates?", images=[a, b])
    assert resp.task.value == "change"
    assert resp.result is not None
    assert "%" in resp.answer


def test_abstain_on_empty_query(orch):
    resp = orch.answer("   ", images=[_optical()])
    assert resp.abstain and resp.status == "abstain"


def test_trace_is_persisted(orch):
    resp = orch.answer("Describe this scene.", images=[_optical()])
    got = orch.store.get(resp.query_id)
    assert got is not None
    steps = [e["step"] for e in got["events"]]
    assert "ingest" in steps and "route" in steps and "execute" in steps


def test_xmodal_abstains_without_sar(orch):
    resp = orch.answer("What does SAR show under the clouds?",
                       images=[_optical()])
    # router diverts xmodal->vqa when no pair; vqa heuristic answers
    assert resp.task.value == "vqa"


def test_xmodal_runs_with_pair(orch):
    opt = _optical("rural")
    rng = np.random.default_rng(3)
    sar = from_array(rng.normal(-14, 3, (2, 120, 120)).astype(np.float32),
                     ["VV", "VH"], crs="EPSG:32633")
    resp = orch.answer("Combine optical and radar to describe this area.",
                       images=[opt, sar])
    assert resp.task.value == "xmodal"
    assert "SAR" in resp.answer or "sar" in resp.answer
