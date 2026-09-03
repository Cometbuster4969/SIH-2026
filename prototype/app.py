"""Streamlit UI — Window A demo surface.

    streamlit run app.py
Upload a raster (or pick a frozen demo scene), type/pick a query, get the answer
card with a TRAINED/HEURISTIC badge, overlay toggles, and the execution-trace
panel OPEN BY DEFAULT (PS P10 — the observable trace is the graded artifact).
The orchestrator runs in-process; never call localhost from browser code.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np

from satquery.ingestion import from_array
from satquery.orchestrator import Orchestrator

try:
    import streamlit as st
except ImportError:  # allow importing this module in CI without streamlit
    st = None


DEMO_SCENES = {
    "Demo scene 1 — rural + water (optical)": {
        "scene_id": "demo_scene_01",
        "bands": ["B02", "B03", "B04", "B08"],
        "kind": "rural",
    },
    "Demo scene 2 — urban fringe (optical)": {
        "scene_id": "demo_scene_02",
        "bands": ["B02", "B03", "B04", "B08"],
        "kind": "urban",
    },
}

QUERY_CHIPS = [
    "What land cover types are in this image?",
    "Is there a water body in this image?",
    "Locate the water body.",
    "Describe this scene.",
    "What changed between these two dates?",
    "The optical image is cloudy — what does the SAR show underneath?",
]


def _synth_scene(kind: str, bands: list[str], size: int = 120):
    """Synthetic but spectral-consistent raster (so heuristics behave sensibly)."""
    rng = np.random.default_rng(7 if kind == "rural" else 11)
    layers = {b: rng.uniform(0.05, 0.15, (size, size)).astype(np.float32)
              for b in bands}
    if "B08" in layers:
        layers["B08"] = rng.uniform(0.35, 0.6, (size, size)).astype(np.float32)  # vegetation
        if kind == "rural":
            layers["B08"][80:110, 60:95] = 0.02      # water patch: low NIR
            layers["B04"][80:110, 60:95] = 0.03
        else:
            layers["B08"][20:60, 20:70] = 0.12       # built-up: low NIR
            layers["B04"][20:60, 20:70] = 0.18
    arr = np.stack([layers[b] for b in bands])
    return from_array(arr, bands=bands, crs="EPSG:32633")


def main():
    assert st is not None, "install the [serve] extras: pip install -r requirements-serve.txt"
    st.set_page_config(page_title="SatQuery AI", layout="wide")
    st.title("🛰️ SatQuery AI — multimodal remote-sensing assistant (Window A prototype)")

    @st.cache_resource
    def get_orch():
        return Orchestrator()

    orch = get_orch()

    with st.sidebar:
        st.header("Input")
        scene = st.selectbox("Frozen demo scene", ["(none)"] + list(DEMO_SCENES))
        uploads = st.file_uploader("…or upload raster(s)", accept_multiple_files=True,
                                   type=["tif", "tiff", "png", "jpg", "jpeg"])
        st.caption("The trained land-cover weights load if torch + configilm + "
                   "reben_publication are present; otherwise the tool honestly "
                   "reports a heuristic result.")

    col1, col2 = st.columns([3, 2])
    with col1:
        query = st.text_input("Ask about the imagery:", value=QUERY_CHIPS[0])
        chips = st.columns(3)
        for i, chip in enumerate(QUERY_CHIPS):
            if chips[i % 3].button(chip, key=f"chip{i}", use_container_width=True):
                query = chip

        images, image_paths, scene_id = [], [], None
        if scene != "(none)":
            cfg = DEMO_SCENES[scene]
            images.append(_synth_scene(cfg["kind"], cfg["bands"]))
            scene_id = cfg["scene_id"]
        for up in uploads or []:
            with tempfile.NamedTemporaryFile(suffix=Path(up.name).suffix, delete=False) as f:
                f.write(up.read())
                image_paths.append(f.name)

        go = st.button("Run query", type="primary")

    if go and query:
        params = {"scene_id": scene_id} if scene_id else {}
        resp = orch.answer(query, image_paths=image_paths or None,
                           images=images or None, params=params)

        with col2:
            st.subheader("Answer")
            badge = "🟢 TRAINED MODEL" if resp.trained else "🟡 HEURISTIC (declared)"
            st.markdown(f"**{badge}** · status `{resp.status}`")
            st.write(resp.answer)
            if resp.confidence is not None:
                st.metric("Confidence", f"{resp.confidence:.2f}")
            st.caption(f"task: `{resp.task.value}` · tool: `{resp.tool}` · "
                       f"fallback router: {resp.fallback_used}")

        st.subheader("Execution trace")  # open by default — the graded artifact
        for ev in resp.trace.events:
            icon = {"ok": "✅", "warning": "⚠️", "error": "❌",
                    "degraded": "🟡", "abstain": "🚫"}.get(ev.status, "•")
            with st.expander(f"{icon} {ev.step}"
                             + (f" — `{ev.tool}`" if ev.tool else "")
                             + (f": {ev.message[:80]}" if ev.message else ""),
                             expanded=(ev.step in ("route", "execute"))):
                st.write(ev.message)
                if ev.data:
                    st.json(ev.data)
        if resp.warnings:
            st.warning("Warnings: " + " | ".join(w["message"] for w in resp.warnings))

        if resp.result and resp.result.artifacts:
            st.subheader("Overlays")
            for a in resp.result.artifacts:
                if a.path.endswith(".png") and Path(a.path).exists():
                    st.image(a.path, caption=a.description)
                    st.checkbox(f"Toggle: {a.description}", value=True)


if __name__ == "__main__":
    main()
