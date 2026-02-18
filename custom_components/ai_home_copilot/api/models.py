"""Pydantic models for API request/response validation in AI Home CoPilot.

This module provides type-safe models for validating API requests and responses
between the HA integration and the Core Add-on.

API Endpoints covered:
- /api/v1/status - System status
- /api/v1/neurons - Neural system state
- /api/v1/neurons/mood - Current mood
- /api/v1/neurons/evaluate - Evaluate neurons (POST)
- /api/v1/capabilities - Core capabilities
- /api/v1/search - Search entities
- /api/v1/search/entities - Filter entities
- /api/v1/search/index - Update search index (POST)
- /api/v1/search/stats - Search statistics
- /habitus/dashboard_cards - Dashboard cards
- /health - Health check
- /version - Version info
- /api/v1/candidates - Pipeline candidates
- /api/v1/habitus/status - Habitus status
- /api/v1/graph/state - Graph state

v1.0.0 - Initial implementation
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, ConfigDict


# ==================== Enums ====================


class NeuronType(str, Enum):
    """Types of neurons in the neural system."""
    MOOD = "mood"
    CONTEXT = "context"
    PATTERN = "pattern"
    HABIT = "habit"
    PRESENCE = "presence"
    TIME = "time"
    WEATHER = "weather"


class MoodType(str, Enum):
    """Types of moods."""
    RELAXED = "relaxed"
    ACTIVE = "active"
    FOCUSED = "focused"
    ENTERTAINING = "entertaining"
    AWAY = "away"
    SLEEPING = "sleeping"
    UNKNOWN = "unknown"


class SearchEntityType(str, Enum):
    """Types of entities for search."""
    AUTOMATION = "automation"
    SCRIPT = "script"
    SCENE = "scene"
    SENSOR = "sensor"
    LIGHT = "light"
    SWITCH = "switch"
    MEDIA_PLAYER = "media_player"


# ==================== Request Models ====================


class NeuronEvaluateRequest(BaseModel):
    """Request model for neuron evaluation."""
    model_config = ConfigDict(populate_by_name=True)
    
    states: dict[str, Any] = Field(default_factory=dict, description="HA entity states")
    time: dict[str, Any] = Field(default_factory=dict, description="Time context")
    weather: dict[str, Any] = Field(default_factory=dict, description="Weather context")
    presence: dict[str, Any] = Field(default_factory=dict, description="Presence context")


class SearchIndexRequest(BaseModel):
    """Request model for search index update."""
    model_config = ConfigDict(populate_by_name=True)
    
    entities: dict[str, Any] = Field(default_factory=dict, description="HA entities")
    automations: dict[str, Any] = Field(default_factory=dict, description="Automations")
    scripts: dict[str, Any] = Field(default_factory=dict, description="Scripts")
    scenes: dict[str, Any] = Field(default_factory=dict, description="Scenes")


class SearchQueryRequest(BaseModel):
    """Request model for search query."""
    model_config = ConfigDict(populate_by_name=True)
    
    q: str = Field(..., description="Search query")
    limit: int = Field(default=20, ge=1, le=100, description="Max results")
    types: Optional[str] = Field(default=None, description="Comma-separated entity types")


class EntityFilterRequest(BaseModel):
    """Request model for entity filtering."""
    model_config = ConfigDict(populate_by_name=True)
    
    domain: Optional[str] = Field(default=None, description="Entity domain")
    state: Optional[str] = Field(default=None, description="Entity state")
    area: Optional[str] = Field(default=None, description="Entity area")
    limit: int = Field(default=50, ge=1, le=500, description="Max results")


# ==================== Response Models ====================


class StatusResponse(BaseModel):
    """Response model for /api/v1/status endpoint."""
    model_config = ConfigDict(populate_by_name=True)
    
    ok: bool = Field(default=True, description="Status OK flag")
    version: Optional[str] = Field(default=None, description="Core version")
    timestamp: Optional[str] = Field(default=None, description="Server timestamp")


class HealthResponse(BaseModel):
    """Response model for /health endpoint."""
    model_config = ConfigDict(populate_by_name=True)
    
    ok: Optional[bool] = Field(default=None, description="Health OK flag")


class VersionResponse(BaseModel):
    """Response model for /version endpoint."""
    model_config = ConfigDict(populate_by_name=True)
    
    version: Optional[str] = Field(default=None, description="Version string")
    data: Optional[dict[str, Any]] = Field(default=None, description="Wrapped data")


class NeuronState(BaseModel):
    """Model for individual neuron state."""
    model_config = ConfigDict(populate_by_name=True)
    
    id: str = Field(..., description="Neuron ID")
    type: NeuronType = Field(..., description="Neuron type")
    value: float = Field(default=0.0, description="Neuron activation value")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence score")
    last_update: Optional[str] = Field(default=None, description="Last update ISO timestamp")


class NeuronsResponse(BaseModel):
    """Response model for /api/v1/neurons endpoint."""
    model_config = ConfigDict(populate_by_name=True)
    
    neurons: dict[str, NeuronState] = Field(default_factory=dict, description="Neuron states")
    success: Optional[bool] = Field(default=True, description="Success flag")
    data: Optional[dict[str, Any]] = Field(default=None, description="Raw data wrapper")


class MoodResponse(BaseModel):
    """Response model for /api/v1/neurons/mood endpoint."""
    model_config = ConfigDict(populate_by_name=True)
    
    mood: MoodType = Field(default=MoodType.UNKNOWN, description="Current mood")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Mood confidence")
    factors: dict[str, float] = Field(default_factory=dict, description="Mood factors")
    timestamp: Optional[str] = Field(default=None, description="Mood timestamp")
    success: Optional[bool] = Field(default=True, description="Success flag")
    data: Optional[dict[str, Any]] = Field(default=None, description="Raw data wrapper")


class NeuronEvaluateResponse(BaseModel):
    """Response model for /api/v1/neurons/evaluate endpoint."""
    model_config = ConfigDict(populate_by_name=True)
    
    neurons: dict[str, Any] = Field(default_factory=dict, description="Evaluated neurons")
    suggestions: list[dict[str, Any]] = Field(default_factory=list, description="Suggestions")
    predictions: list[dict[str, Any]] = Field(default_factory=list, description="Predictions")
    success: Optional[bool] = Field(default=True, description="Success flag")
    data: Optional[dict[str, Any]] = Field(default=None, description="Raw data wrapper")


class CapabilitiesResponse(BaseModel):
    """Response model for /api/v1/capabilities endpoint."""
    model_config = ConfigDict(populate_by_name=True)
    
    features: list[str] = Field(default_factory=list, description="Supported features")
    version: Optional[str] = Field(default=None, description="API version")
    endpoints: dict[str, bool] = Field(default_factory=dict, description="Endpoint availability")


class SearchResultItem(BaseModel):
    """Model for individual search result."""
    model_config = ConfigDict(populate_by_name=True)
    
    entity_id: str = Field(..., description="Entity ID")
    entity_type: str = Field(..., description="Entity type")
    label: Optional[str] = Field(default=None, description="Display label")
    domain: Optional[str] = Field(default=None, description="Entity domain")
    state: Optional[str] = Field(default=None, description="Current state")
    score: float = Field(default=0.0, description="Relevance score")
    attributes: dict[str, Any] = Field(default_factory=dict, description="Entity attributes")


class SearchResponse(BaseModel):
    """Response model for search endpoints."""
    model_config = ConfigDict(populate_by_name=True)
    
    results: list[SearchResultItem] = Field(default_factory=list, description="Search results")
    total: int = Field(default=0, description="Total results")
    query: Optional[str] = Field(default=None, description="Executed query")
    success: Optional[bool] = Field(default=True, description="Success flag")
    data: Optional[dict[str, Any]] = Field(default=None, description="Raw data wrapper")


class EntityFilterResponse(BaseModel):
    """Response model for entity filter endpoint."""
    model_config = ConfigDict(populate_by_name=True)
    
    results: list[SearchResultItem] = Field(default_factory=list, description="Filtered entities")
    total: int = Field(default=0, description="Total results")
    success: Optional[bool] = Field(default=True, description="Success flag")
    data: Optional[dict[str, Any]] = Field(default=None, description="Raw data wrapper")


class SearchStatsResponse(BaseModel):
    """Response model for search stats endpoint."""
    model_config = ConfigDict(populate_by_name=True)
    
    total_entities: int = Field(default=0, description="Total indexed entities")
    total_automations: int = Field(default=0, description="Total automations")
    total_scripts: int = Field(default=0, description="Total scripts")
    total_scenes: int = Field(default=0, description="Total scenes")
    last_indexed: Optional[str] = Field(default=None, description="Last indexing timestamp")
    success: Optional[bool] = Field(default=True, description="Success flag")
    data: Optional[dict[str, Any]] = Field(default=None, description="Raw data wrapper")


class SearchIndexResponse(BaseModel):
    """Response model for search index update."""
    model_config = ConfigDict(populate_by_name=True)
    
    indexed_count: int = Field(default=0, description="Number of entities indexed")
    success: Optional[bool] = Field(default=True, description="Success flag")
    data: Optional[dict[str, Any]] = Field(default=None, description="Raw data wrapper")


class DashboardCardsRequest(BaseModel):
    """Request model for dashboard cards."""
    model_config = ConfigDict(populate_by_name=True)
    
    pattern_type: str = Field(default="all", description="Pattern type filter")
    format: str = Field(default="json", description="Output format")


class DashboardCard(BaseModel):
    """Model for a single dashboard card."""
    model_config = ConfigDict(populate_by_name=True)
    
    id: str = Field(..., description="Card ID")
    type: str = Field(..., description="Card type")
    title: Optional[str] = Field(default=None, description="Card title")
    data: dict[str, Any] = Field(default_factory=dict, description="Card data")
    priority: int = Field(default=0, description="Card priority")


class DashboardCardsResponse(BaseModel):
    """Response model for dashboard cards."""
    model_config = ConfigDict(populate_by_name=True)
    
    cards: list[DashboardCard] = Field(default_factory=list, description="Dashboard cards")
    success: Optional[bool] = Field(default=True, description="Success flag")
    data: Optional[dict[str, Any]] = Field(default=None, description="Raw data wrapper")


class CandidateItem(BaseModel):
    """Model for a pipeline candidate."""
    model_config = ConfigDict(populate_by_name=True)
    
    id: str = Field(..., description="Candidate ID")
    type: str = Field(..., description="Candidate type")
    entity_id: Optional[str] = Field(default=None, description="Related entity")
    status: str = Field(default="pending", description="Candidate status")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Confidence")
    created_at: Optional[str] = Field(default=None, description="Creation timestamp")
    data: dict[str, Any] = Field(default_factory=dict, description="Candidate data")


class CandidatesResponse(BaseModel):
    """Response model for /api/v1/candidates endpoint."""
    model_config = ConfigDict(populate_by_name=True)
    
    candidates: list[CandidateItem] = Field(default_factory=list, description="Candidates")
    total: int = Field(default=0, description="Total candidates")
    success: Optional[bool] = Field(default=True, description="Success flag")


class CandidateResponse(BaseModel):
    """Response model for single candidate endpoint."""
    model_config = ConfigDict(populate_by_name=True)
    
    candidate: Optional[CandidateItem] = Field(default=None, description="Candidate")
    success: Optional[bool] = Field(default=True, description="Success flag")


class HabitusStatusResponse(BaseModel):
    """Response model for /api/v1/habitus/status endpoint."""
    model_config = ConfigDict(populate_by_name=True)
    
    zones: dict[str, Any] = Field(default_factory=dict, description="Zone states")
    patterns: dict[str, Any] = Field(default_factory=dict, description="Detected patterns")
    last_update: Optional[str] = Field(default=None, description="Last update timestamp")
    success: Optional[bool] = Field(default=True, description="Success flag")
    data: Optional[dict[str, Any]] = Field(default=None, description="Raw data wrapper")


class GraphStateResponse(BaseModel):
    """Response model for /api/v1/graph/state endpoint."""
    model_config = ConfigDict(populate_by_name=True)
    
    nodes: int = Field(default=0, description="Number of nodes")
    edges: int = Field(default=0, description="Number of edges")
    last_update: Optional[str] = Field(default=None, description="Last update timestamp")
    success: Optional[bool] = Field(default=True, description="Success flag")
    data: Optional[dict[str, Any]] = Field(default=None, description="Raw data wrapper")


class DevLogEntry(BaseModel):
    """Model for a development log entry."""
    model_config = ConfigDict(populate_by_name=True)
    
    timestamp: str = Field(..., description="Log timestamp")
    level: str = Field(default="INFO", description="Log level")
    message: str = Field(..., description="Log message")
    source: Optional[str] = Field(default=None, description="Log source")


class DevLogsResponse(BaseModel):
    """Response model for dev logs endpoint."""
    model_config = ConfigDict(populate_by_name=True)
    
    logs: list[DevLogEntry] = Field(default_factory=list, description="Log entries")
    total: int = Field(default=0, description="Total logs")
    success: Optional[bool] = Field(default=True, description="Success flag")
    data: Optional[dict[str, Any]] = Field(default=None, description="Raw data wrapper")


# ==================== Generic API Response Wrapper ====================


class ApiResponse(BaseModel):
    """Generic API response wrapper."""
    model_config = ConfigDict(populate_by_name=True)
    
    ok: bool = Field(default=True, description="Success flag")
    error: Optional[str] = Field(default=None, description="Error message")
    data: Optional[dict[str, Any]] = Field(default=None, description="Response data")


__all__ = [
    # Enums
    "NeuronType",
    "MoodType", 
    "SearchEntityType",
    # Request Models
    "NeuronEvaluateRequest",
    "SearchIndexRequest",
    "SearchQueryRequest",
    "EntityFilterRequest",
    "DashboardCardsRequest",
    # Response Models
    "StatusResponse",
    "HealthResponse",
    "VersionResponse",
    "NeuronState",
    "NeuronsResponse",
    "MoodResponse",
    "NeuronEvaluateResponse",
    "CapabilitiesResponse",
    "SearchResultItem",
    "SearchResponse",
    "EntityFilterResponse",
    "SearchStatsResponse",
    "SearchIndexResponse",
    "DashboardCard",
    "DashboardCardsResponse",
    "CandidateItem",
    "CandidatesResponse",
    "CandidateResponse",
    "HabitusStatusResponse",
    "GraphStateResponse",
    "DevLogEntry",
    "DevLogsResponse",
    "ApiResponse",
]
