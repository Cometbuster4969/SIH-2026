"""RuleRouter — deterministic task router.

PS P10: "only the observable execution trace ... will be evaluated. Internal
reasoning text is neither required nor evaluated." A deterministic router scores
identically to an LLM planner on the trace and cannot crash the demo; the LLM
planner lands ON TOP in Window B (D9-D12), this stays as the guardrail fallback.

Routing = keyword match (ordered, most specific first) + modality gating.
Anything unmatched -> vqa_single (the mandatory baseline) rather than an error.
"""
from __future__ import annotations

import re

from .registry import tool_for_task
from .schemas import Modality, RoutePlan, TaskType

# Ordered rules: (task, keyword regexes). First match wins; order matters —
# change_vqa/change must be tested before bare vqa, xmodal_mask before xmodal,
# caption before landcover (PS query 1 "Describe the land-cover ..." is a caption).
_RULES: list[tuple[TaskType, list[str]]] = [
    (TaskType.CHANGE_VQA, [
        r"\b(changed?|change|changes)\b.*\b(build|construct|urban|grown?|destroy|flood|new)\b",
        r"\b(build|construct|grown?|destroy|flood)\b.*\b(between|over time|since|before|after)\b",
        r"\bwas there\b.*\b(between|before|after|over)\b",
        # PS query 5: "Has the built-up area increased, decreased, or remained unchanged?"
        r"\b(increas|decreas|expand|shrink|grow|reduc)\w*\b",
        r"\bremain\w*\s+(unchanged|the same)\b",
    ]),
    (TaskType.CHANGE, [
        r"\bwhat changed\b", r"\bchange detection\b", r"\bdetect change\b",
        r"\bchanges? (between|over|across)\b", r"\b(before|after|bi-?temporal)\b.*\b(image|scene)\b",
        r"\bdiffer\w*\b", r"\bchange map\b",
    ]),
    (TaskType.XMODAL_MASK, [
        r"\bsegment\b", r"\bmask\b", r"\bpixel\b", r"\bboundar\w+\b",
        r"\bdelineate\b",
    ]),
    (TaskType.XMODAL, [
        r"\bsar\b", r"\bradar\b", r"\bsentinel-?1\b", r"\boptical\b.*\bsar\b",
        r"\bcross[- ]modal\b", r"\bcloud\w*\b.*\b(sar|radar|under|beneath|through)\b",
        r"\b(sar|radar)\b.*\b(show|reveal|penetrat)\w*\b", r"\bfuse\b.*\b(optical|sar|radar)\b",
        r"\bboth (optical|sensor|modalit)\w*\b", r"\bjoint\b.*\b(optical|sar|image)\b",
    ]),
    (TaskType.GROUND, [
        r"\blocate\b", r"\blocalize\b", r"\bwhere (is|are)\b", r"\bbounding box\b",
        r"\bbox\b", r"\bground\b", r"\bfind the\b", r"\bhighlight the\b",
        r"\bpoint to\b", r"\bmark the\b",
    ]),
    (TaskType.CAPTION, [
        r"\bdescribe\b", r"\bcaption\b", r"\bsummary\b", r"\bsummari[sz]e\b",
        r"\bwhat (do|does) (this|the) (image|scene) show\b", r"\boverview\b",
    ]),
    (TaskType.LANDCOVER, [
        r"\bland[ -]?cover\b", r"\bland use\b", r"\bclassif\w+\b",
        r"\b(what|which) (kind|type|class) of (land|area|terrain|surface)\b",
        r"\bagricultur\w*|urban|forest\b.*\b(area|land|region)\b",
    ]),
    (TaskType.VQA, [
        r"\?",  # any remaining question -> mandatory single-image baseline
    ]),
]

# Modality requirements per task (the hard gate).
_NEEDS_PAIR = {TaskType.CHANGE, TaskType.CHANGE_VQA}
_NEEDS_XMODAL = {TaskType.XMODAL, TaskType.XMODAL_MASK}


def detect_modalities(modalities: list[Modality]) -> set[Modality]:
    present = set(modalities)
    if Modality.PAIR in present or (Modality.OPTICAL in present and Modality.SAR in present):
        present.add(Modality.PAIR)
    return present


def route(query: str, modalities: list[Modality] | None = None,
          query_id: str | None = None) -> RoutePlan:
    q = query.lower().strip()
    modalities = modalities or []
    present = detect_modalities(modalities)

    matched: tuple[TaskType, list[str]] | None = None
    hit_keywords: list[str] = []
    for task, patterns in _RULES:
        for pat in patterns:
            if re.search(pat, q):
                matched = (task, [pat])
                hit_keywords = [pat]
                break
        if matched:
            break

    notes: list[str] = []
    if matched is None:
        task = TaskType.VQA
        notes.append("no keyword rule matched; defaulting to single-image VQA baseline")
    else:
        task = matched[0]

    # Modality gating — degrade/divert rather than crash:
    needs_pair = task in _NEEDS_PAIR
    needs_xmodal = task in _NEEDS_XMODAL
    if needs_xmodal and Modality.PAIR not in present:
        # x-modal task requested without a co-registered pair: answer from the
        # single image but flag it (guardrail honesty over refusal-crash).
        notes.append("cross-modal task requested but no co-registered optical+SAR pair provided; "
                     "routing to single-image path with a warning")
        task = TaskType.VQA
        needs_xmodal = False
    if needs_pair and len(modalities) < 2:
        notes.append("change task requires two images; only one present — answering about the single image")
        task = TaskType.VQA
        needs_pair = False

    tool = tool_for_task(task).name
    return RoutePlan(
        query_id=query_id or "",
        task=task,
        tool=tool,
        needs_pair=needs_pair,
        needs_xmodal=needs_xmodal,
        keywords=hit_keywords,
        fallback_used=True,
        planner="RuleRouter",
        notes="; ".join(notes),
    )
