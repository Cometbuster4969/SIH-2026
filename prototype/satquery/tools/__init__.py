"""Tools — the agent-callable specialists.

Window A status (honest, mirrors registry.yaml):
  landcover      : trained weights (BIFOLD BE v2.0 resnet50-all-v0.2.0) if the
                   weights+deps are present; spectral-index heuristic otherwise,
                   reported as degraded.
  change/ground  : declared heuristics on the frozen demo scenes.
  vqa/caption/
  xmodal*        : heuristics + composition of landcover labels.
Window B swaps implementations behind the SAME ToolResult contract.
"""
from __future__ import annotations

from ..schemas import ToolInput, ToolResult


class Tool:
    name: str = "base"

    def available(self) -> bool:
        return True

    def run(self, tin: ToolInput) -> ToolResult:  # pragma: no cover - interface
        raise NotImplementedError


from .landcover import LandcoverTool
from .heuristics import (ChangeTool, GroundTool, VQATool, CaptionTool,
                         XModalReasonTool, XModalSegmentTool)

TOOL_CLASSES = {
    "landcover": LandcoverTool,
    "vqa_single": VQATool,
    "caption_scene": CaptionTool,
    "ground_object": GroundTool,
    "change_detect": ChangeTool,
    "change_vqa": ChangeTool,        # same tool, answers question from mask
    "xmodal_reason": XModalReasonTool,
    "xmodal_segment": XModalSegmentTool,
}


def build_tool(name: str, demo_cache: dict | None = None) -> Tool:
    cls = TOOL_CLASSES[name]
    return cls(demo_cache=demo_cache) if "demo_cache" in cls.__init__.__code__.co_varnames else cls()
