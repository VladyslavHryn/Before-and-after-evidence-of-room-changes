from pydantic import BaseModel
from typing import Optional, List, Dict
from enum import Enum

class ChangeStatus(str, Enum):
    unchanged = "unchanged"
    moved = "moved"
    added = "added"
    removed = "removed"
    not_verifiable = "not_verifiable"

class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"

class BoundingBox(BaseModel):
    x_pct: float
    y_pct: float
    w_pct: float
    h_pct: float

class DetectedObject(BaseModel):
    name: str
    bbox_before: Optional[BoundingBox] = None
    bbox_after: Optional[BoundingBox] = None
    status: ChangeStatus
    confidence: Confidence
    evidence_note: str

class SceneAssessment(BaseModel):
    lighting_change: str
    viewpoint_change: str
    coverage_comparison: str

class UncertainMatch(BaseModel):
    object_name: str
    reason: str
    suggested_action: str
    bbox_before: Optional[BoundingBox] = None

class AnalysisResult(BaseModel):
    scene: SceneAssessment
    confirmed_changes: List[DetectedObject]
    unchanged_objects: List[DetectedObject]
    uncertain_matches: List[UncertainMatch]
    processing_time_seconds: float
    token_usage: Dict[str, int]
    estimated_cost_usd: float
    warnings: List[str]
