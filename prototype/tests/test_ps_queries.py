"""The five verbatim representative queries from PS 26167 (ps-26167.md §2),
plus the benchmark-style VQA baseline the PS leaves implicit. If any of these
routes to the wrong tool, the on-stage demo is wrong — keep this table in sync
with the PS, never with the router.
"""
import pytest

from satquery.router import route
from satquery.schemas import Modality as M
from satquery.schemas import TaskType

PS_QUERIES = [
    # (PS #, verbatim query, modalities, expected task, expected tool)
    (1, "Describe the land-cover and major objects visible in this image.",
     [M.OPTICAL], TaskType.CAPTION, "caption_scene"),
    (2, "Highlight the water body referred to in the query.",
     [M.OPTICAL], TaskType.GROUND, "ground_object"),
    (3, "What changed between these two dates, and where did the change occur?",
     [M.OPTICAL, M.OPTICAL], TaskType.CHANGE, "change_detect"),
    (4, "Use the optical and SAR images together to identify built-up and water-covered regions.",
     [M.PAIR], TaskType.XMODAL, "xmodal_reason"),
    (5, "Has the built-up area increased, decreased, or remained unchanged?",
     [M.OPTICAL, M.OPTICAL], TaskType.CHANGE_VQA, "change_vqa"),
    # Not in the PS — our own benchmark-style question for the mandatory baseline (P3).
    (0, "Is there a water body in this image?",
     [M.OPTICAL], TaskType.VQA, "vqa_single"),
]


@pytest.mark.parametrize("num,query,mods,task,tool", PS_QUERIES,
                         ids=[f"ps{n}" if n else "vqa-baseline" for n, *_ in PS_QUERIES])
def test_verbatim_ps_query_routes_to_expected_tool(num, query, mods, task, tool):
    plan = route(query, mods)
    assert plan.task == task, f"PS query {num} routed to {plan.task}, expected {task}"
    assert plan.tool == tool


def test_ps_query_5_with_single_image_falls_back_to_vqa_with_note():
    plan = route(PS_QUERIES[4][1], [M.OPTICAL])
    assert plan.task == TaskType.VQA
    assert "two images" in plan.notes
