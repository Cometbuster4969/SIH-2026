"""Orchestrator — the agent loop the judges see.

    request -> validate/ingest -> guardrail -> RuleRouter -> executor
            -> tool(s) -> integrator -> trace (SQLite) -> answer card

Real in Window A: ingestion, validation, registry, routing, execution, trace.
The LLM planner is intentionally absent — RuleRouter IS the path (PS P10 makes
it score-neutral; Window B adds the LLM on top with this as fallback).
No internal reasoning text is ever surfaced or stored.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from .ingestion import (IngestionError, RasterImage, check_coregistration,
                        load_raster)
from .registry import get_tool
from .router import route
from .schemas import (Modality, SatQueryResponse, Severity, ToolInput, Trace,
                      TraceEvent)
from .trace import TraceStore
from .tools import build_tool
from .tools.heuristics import (CaptionTool, XModalReasonTool)
from .tools.landcover import LandcoverTool


class Orchestrator:
    def __init__(self, trace_store: TraceStore | None = None,
                 demo_cache_path: str | Path = "config/demo_cache.json",
                 artifact_dir: str | Path = "artifacts",
                 strict_ingest: bool = False):
        self.store = trace_store or TraceStore()
        self.artifact_dir = Path(artifact_dir)
        self.demo_cache = self._load_demo_cache(demo_cache_path)
        self.strict_ingest = strict_ingest
        # Tools are instantiated lazily and evicted on the 6 GB laptop (budget
        # §5). Landcover is shared with caption/xmodal composition.
        self._landcover = LandcoverTool(demo_cache=self.demo_cache,
                                        artifact_dir=self.artifact_dir)
        self._tools: dict[str, object] = {}

    @staticmethod
    def _load_demo_cache(path) -> dict:
        p = Path(path)
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _tool(self, name: str):
        if name == "landcover":
            return self._landcover
        if name not in self._tools:
            if name == "caption_scene":
                self._tools[name] = CaptionTool(self.demo_cache,
                                                self.artifact_dir, self._landcover)
            elif name == "xmodal_reason":
                self._tools[name] = XModalReasonTool(self.demo_cache,
                                                     self.artifact_dir, self._landcover)
            else:
                self._tools[name] = build_tool(name, demo_cache=self.demo_cache)
        return self._tools[name]

    # -- entry point ---------------------------------------------------------

    def answer(self, query: str, image_paths: list[str] | None = None,
               images: list[RasterImage] | None = None,
               params: dict | None = None) -> SatQueryResponse:
        trace = Trace(query=query)
        t0 = time.time()
        params = params or {}

        # 1) Ingestion + validation -----------------------------------------
        rasters: list[RasterImage] = list(images or [])
        for p in (image_paths or []):
            try:
                rasters.append(load_raster(p))
            except IngestionError as e:
                self._warn(trace, Severity.ERROR, "ingestion", str(e))
                if self.strict_ingest:
                    return self._finish(trace, None, t0, "error",
                                        answer=f"Image rejected: {e}")

        for r in rasters:
            trace.images.append(r.meta())
            for note in r.notes:
                self._warn(trace, Severity.WARNING, "ingestion", note)
        self.store.add_event(trace, "ingest", "ok",
                             message=f"{len(rasters)} image(s) validated")

        # Pair co-registration check (PS cross-modal mandate).
        modalities = [r.modality for r in rasters]
        if len(rasters) == 2:
            ok, off, shift = check_coregistration(rasters[0], rasters[1])
            if not ok:
                self._warn(trace, Severity.WARNING, "coregistration",
                           f"pair offset ~{off:.1f}px shift {shift}; auto-register before fusing")
            for r in rasters[:2]:
                r.notes.append(f"coreg ok={ok} offset={off:.2f}px")
            trace.images[0].coreg_ok = ok
            trace.images[1].coreg_ok = ok
            self.store.add_event(trace, "coreg_check", "ok" if ok else "warning",
                                 message=f"offset={off:.2f}px")

        # 2) Guardrail: empty / over-long query ------------------------------
        q = query.strip()
        if not q:
            self._warn(trace, Severity.ABSTAIN, "guardrail", "empty query")
            return self._finish(trace, None, t0, "abstain",
                                answer="Please ask a question about the image(s).")
        if len(q) > 2000:
            self._warn(trace, Severity.ABSTAIN, "guardrail", "query too long")
            return self._finish(trace, None, t0, "abstain",
                                answer="Query is too long; please shorten it.")

        # 3) RuleRouter -------------------------------------------------------
        plan = route(q, modalities, query_id=trace.query_id)
        trace.route = plan
        self.store.add_event(trace, "route", "ok", tool=plan.tool,
                             message=f"task={plan.task.value} via {plan.planner}",
                             data={"keywords": plan.keywords, "notes": plan.notes})
        if plan.notes:
            self._warn(trace, Severity.WARNING, "router", plan.notes)

        # 4) Executor ---------------------------------------------------------
        spec = get_tool(plan.tool)
        # Params whitelist: only keys in the registry schema are passed (PS A2.4).
        allowed = set((spec.param_schema.get("properties") or {}).keys())
        clean_params = {k: v for k, v in params.items() if k in allowed or k == "scene_id"}
        tin = ToolInput(query=q, images=rasters, params=clean_params)
        tin.query_id = trace.query_id  # used for artifact filenames

        t1 = time.time()
        try:
            result = self._tool(plan.tool).run(tin)
        except Exception as e:  # one tool dies -> graceful degraded answer, no crash
            result = None
            self._warn(trace, Severity.ERROR, plan.tool,
                       f"tool raised {type(e).__name__}: {e}")
        result_latency = time.time() - t1
        self.store.add_event(
            trace, "execute", result.status if result else "error",
            tool=plan.tool,
            message=(result.degraded_reason or result.answer[:120]) if result else "tool failed",
            data={"latency_s": round(result_latency, 3),
                  "model_version": result.model_version if result else None,
                  "trained": result.trained if result else False})

        if result is None:
            return self._finish(trace, None, t0, "error",
                                answer="The specialist tool failed; please retry or rephrase.")

        # 5) Integrator -------------------------------------------------------
        self.store.add_event(trace, "integrate", "ok",
                             message="answer card + trace assembled")
        result.latency_s = round(result_latency, 3)
        abstain = result.status == "abstain"
        resp = SatQueryResponse(
            query_id=trace.query_id, query=q, answer=result.answer,
            confidence=result.confidence, task=plan.task, tool=plan.tool,
            status=result.status, trained=result.trained, abstain=abstain,
            fallback_used=plan.fallback_used,
            warnings=trace.warnings, result=result, trace=trace)
        self.store.save(trace, result.status)
        return resp

    # -- helpers -------------------------------------------------------------

    def _warn(self, trace: Trace, sev: Severity, step: str, msg: str) -> None:
        trace.warnings.append({"severity": sev.value, "step": step, "message": msg})
        self.store.add_event(trace, step, "warning" if sev != Severity.ERROR else "error",
                             message=msg)

    def _finish(self, trace: Trace, result, t0: float, status: str,
                answer: str) -> SatQueryResponse:
        self.store.add_event(trace, "integrate", status, message=answer[:120])
        self.store.save(trace, status)
        return SatQueryResponse(
            query_id=trace.query_id, query=trace.query, answer=answer,
            confidence=None,
            task=trace.route.task if trace.route else None,
            tool=trace.route.tool if trace.route else "",
            status=status, trained=False, abstain=(status == "abstain"),
            fallback_used=True, warnings=trace.warnings, result=result, trace=trace)
