"""Pydantic schemas — the tool contract and trace data model.

The Tool contract is frozen for Window B: trained models replace the heuristic
implementations without changing any of these shapes (PS A2 — agent calls tools
through declared interfaces only).
"""
from __future__ import annotations

import enum
import time
import uuid
from typing import Any

from pydantic import BaseModel, Field


class Modality(str, enum.Enum):
    OPTICAL = "optical"        # Sentinel-2 / Cartosat-like, reflectance bands
    SAR = "sar"                # Sentinel-1, dB values (VV/VH)
    PAIR = "pair"              # co-registered optical + SAR
    UNKNOWN = "unknown"


class TaskType(str, enum.Enum):
    VQA = "vqa"                          # single-image question answering
    CAPTION = "caption"                  # scene description
    GROUND = "ground"                    # refer-expression grounding -> bbox
    CHANGE = "change"                    # bi-temporal change detection
    CHANGE_VQA = "change_vqa"            # questions about a bi-temporal pair
    XMODAL = "xmodal"                    # optical+SAR joint reasoning
    XMODAL_MASK = "xmodal_mask"          # cross-modal segmentation mask
    LANDCOVER = "landcover"              # patch multi-label classification


class Severity(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    ABSTAIN = "abstain"


# Tool registry ----------------------------------------------------------------

class ToolSpec(BaseModel):
    name: str
    task: TaskType
    modality_required: list[Modality]
    description: str
    param_schema: dict[str, Any]
    examples: list[str] = Field(default_factory=list)
    trained: bool = False          # True = our weights / genuinely trained model
    vendor: str | None = None      # provenance, e.g. "BIFOLD BE v2.0 resnet50"
    latency_budget_s: float = 10.0


class RegistryFile(BaseModel):
    version: str
    tools: list[ToolSpec]


# Routing ----------------------------------------------------------------------

class RoutePlan(BaseModel):
    query_id: str
    task: TaskType
    tool: str
    needs_pair: bool = False
    needs_xmodal: bool = False
    keywords: list[str] = Field(default_factory=list)
    fallback_used: bool = True     # RuleRouter IS the deterministic fallback (PS P10)
    planner: str = "RuleRouter"
    notes: str = ""


# Rasters ----------------------------------------------------------------------

class RasterMeta(BaseModel):
    path: str
    modality: Modality
    bands: list[str]
    crs: str | None = None
    width: int
    height: int
    transform: list[float] | None = None      # 6-tuple affine, rasterio order
    dtype: str
    coreg_ok: bool | None = None              # pair offset within tolerance
    notes: list[str] = Field(default_factory=list)


# Trace ------------------------------------------------------------------------

class TraceEvent(BaseModel):
    t: float = Field(default_factory=time.time)
    step: str
    tool: str | None = None
    status: str                                # ok | degraded | error | abstain
    message: str = ""
    data: dict[str, Any] = Field(default_factory=dict)


class Trace(BaseModel):
    query_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    query: str
    started_at: float = Field(default_factory=time.time)
    route: RoutePlan | None = None
    images: list[RasterMeta] = Field(default_factory=list)
    events: list[TraceEvent] = Field(default_factory=list)
    warnings: list[dict[str, Any]] = Field(default_factory=list)


# Tool I/O ---------------------------------------------------------------------

class ToolInput(BaseModel):
    model_config = {"extra": "allow"}   # orchestrator attaches query_id for artifact names
    query: str
    images: list[Any] = Field(default_factory=list)   # RasterImage objects (not validated)
    params: dict[str, Any] = Field(default_factory=dict)


class Artifact(BaseModel):
    kind: str                     # mask | bbox | overlay | json
    path: str
    description: str = ""


class ToolResult(BaseModel):
    tool: str
    task: TaskType
    status: str                   # ok | degraded | unavailable | abstain | error
    answer: str
    confidence: float | None = None
    trained: bool = False
    degraded_reason: str | None = None
    labels: list[dict[str, Any]] = Field(default_factory=list)
    bbox: list[float] | None = None      # [x0, y0, x1, y1] pixel coords
    artifacts: list[Artifact] = Field(default_factory=list)
    model_version: str | None = None
    latency_s: float | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class SatQueryResponse(BaseModel):
    query_id: str
    query: str
    answer: str
    confidence: float | None = None
    task: TaskType | None = None
    tool: str
    status: str
    trained: bool
    abstain: bool = False
    fallback_used: bool = True
    warnings: list[dict[str, Any]] = Field(default_factory=list)
    result: ToolResult | None = None
    trace: Trace
