from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


class ProjectCreate(BaseModel):
    name: str
    query: str
    geography: Optional[Dict[str, Any]] = None
    languages: Optional[List[str]] = None
    audience: Optional[List[str]] = None
    intent: Optional[List[str]] = None
    source_types: Optional[List[str]] = None
    scoring_profile: str = "lead_generation"
    max_discovery_depth: int = 3
    max_sources: int = 500


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    query: Optional[str] = None
    geography: Optional[Dict[str, Any]] = None
    languages: Optional[List[str]] = None
    audience: Optional[List[str]] = None
    intent: Optional[List[str]] = None
    source_types: Optional[List[str]] = None
    scoring_profile: Optional[str] = None
    max_discovery_depth: Optional[int] = None
    max_sources: Optional[int] = None
    status: Optional[str] = None


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    query: str
    query_model: Optional[Dict[str, Any]] = None
    geography: Optional[Dict[str, Any]] = None
    languages: Optional[List[str]] = None
    audience: Optional[List[str]] = None
    intent: Optional[List[str]] = None
    source_types: Optional[List[str]] = None
    scoring_profile: str
    max_discovery_depth: int
    max_sources: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DiscoveryRunResponse(BaseModel):
    id: UUID
    project_id: UUID
    status: str
    current_stage: Optional[str] = None
    progress: float
    stats: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SourceResponse(BaseModel):
    id: UUID
    telegram_id: Optional[int] = None
    username: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    source_type: Optional[str] = None
    member_count: Optional[int] = None
    status: str
    topic_analysis: Optional[Dict[str, Any]] = None
    language_analysis: Optional[Dict[str, Any]] = None
    geography_analysis: Optional[Dict[str, Any]] = None
    audience_analysis: Optional[Dict[str, Any]] = None
    intent_analysis: Optional[Dict[str, Any]] = None
    activity_analysis: Optional[Dict[str, Any]] = None
    first_seen_at: datetime
    last_analyzed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SourceScoreResponse(BaseModel):
    id: UUID
    source_id: UUID
    project_id: UUID
    total_score: float
    breakdown: Dict[str, float]
    scoring_profile: str
    scored_at: datetime

    class Config:
        from_attributes = True


class SourceReviewCreate(BaseModel):
    action: str = Field(..., pattern="^(approve|reject|skip)$")
    reason: Optional[str] = None


class SourceReviewResponse(BaseModel):
    id: UUID
    source_id: UUID
    project_id: UUID
    action: str
    reason: Optional[str] = None
    reviewed_at: datetime

    class Config:
        from_attributes = True


class ScoringProfileResponse(BaseModel):
    id: UUID
    name: str
    weights: Dict[str, float]
    description: Optional[str] = None
    is_default: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ScoringProfileCreate(BaseModel):
    name: str
    weights: Dict[str, float]
    description: Optional[str] = None
    is_default: bool = False


class DiscoveryEventResponse(BaseModel):
    id: UUID
    discovery_run_id: UUID
    event_type: str
    payload: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class GraphNode(BaseModel):
    id: str
    label: str
    size: int
    color: str
    score: Optional[float] = None


class GraphEdge(BaseModel):
    source: str
    target: str
    edge_type: str
    confidence: float


class GraphData(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


class ExportFormat(BaseModel):
    format: str = Field("json", pattern="^(csv|json)$")
    source_ids: Optional[List[UUID]] = None


class StatsResponse(BaseModel):
    total_sources: int
    total_projects: int
    total_runs: int
    sources_by_status: Dict[str, int]
    avg_score: Optional[float] = None
