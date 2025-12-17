"""
API Schemas - Pydantic models for request/response.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================
# Cape Schemas
# ============================================================

class CapeResponse(BaseModel):
    """Cape response model for API."""
    id: str
    name: str
    version: str
    description: str
    execution_type: str
    risk_level: str
    source: str
    tags: List[str]
    intent_patterns: List[str]
    model_adapters: List[str]
    estimated_cost: Optional[float] = None
    timeout_seconds: int = 30
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    @classmethod
    def from_cape(cls, cape) -> "CapeResponse":
        """Create from Cape model."""
        return cls(
            id=cape.id,
            name=cape.name,
            version=cape.version if hasattr(cape, 'version') else cape.metadata.version,
            description=cape.description,
            execution_type=cape.execution.type.value,
            risk_level=cape.safety.risk_level.value,
            source=cape.metadata.source.value,
            tags=cape.metadata.tags,
            intent_patterns=cape.metadata.intents,
            model_adapters=list(cape.model_adapters.keys()),
            estimated_cost=cape.safety.estimated_cost_usd,
            timeout_seconds=cape.execution.timeout_seconds,
            created_at=cape.metadata.created_at.isoformat() if cape.metadata.created_at else None,
            updated_at=cape.metadata.updated_at.isoformat() if cape.metadata.updated_at else None,
        )


class CapeDetailResponse(CapeResponse):
    """Detailed Cape response with full configuration."""
    interface: Dict[str, Any] = Field(default_factory=dict)
    execution_config: Dict[str, Any] = Field(default_factory=dict)
    safety_config: Dict[str, Any] = Field(default_factory=dict)


# ============================================================
# Chat Schemas
# ============================================================

class ChatRequest(BaseModel):
    """Chat request model."""
    message: str = Field(..., description="User message")
    model: str = Field(default="gemini-2.5-flash", description="Model to use")
    enabled_capes: Optional[List[str]] = Field(default=None, description="Enabled cape IDs")
    stream: bool = Field(default=True, description="Stream response")


class ChatMessage(BaseModel):
    """Chat message model."""
    role: str  # user | assistant
    content: str
    cape_execution: Optional[Dict[str, Any]] = None


class ChatResponse(BaseModel):
    """Non-streaming chat response."""
    message: ChatMessage
    matched_cape: Optional[str] = None
    execution_time_ms: float = 0
    tokens_used: int = 0
    cost_usd: float = 0


# ============================================================
# Match Schemas
# ============================================================

class MatchRequest(BaseModel):
    """Intent match request."""
    query: str = Field(..., description="Query to match")
    top_k: int = Field(default=5, ge=1, le=20)
    threshold: float = Field(default=0.3, ge=0, le=1)


class MatchResult(BaseModel):
    """Match result model."""
    cape_id: str
    cape_name: str
    score: float
    tags: List[str] = Field(default_factory=list)


class MatchResponse(BaseModel):
    """Match response model."""
    results: List[MatchResult]
    query: str
    total_capes: int


# ============================================================
# Model Schemas
# ============================================================

class ModelInfo(BaseModel):
    """Model information."""
    id: str
    name: str
    provider: str  # openai | google | anthropic
    speed: str  # fast | medium | slow
    cost_tier: str  # low | medium | high
    supports_tools: bool = True
    default: bool = False


class ModelsResponse(BaseModel):
    """Available models response."""
    models: List[ModelInfo]
    default_model: str


# ============================================================
# Stats Schemas
# ============================================================

class StatsResponse(BaseModel):
    """System statistics response."""
    total_capes: int
    total_executions: int
    success_rate: float
    avg_execution_time_ms: float
    total_tokens: int
    total_cost_usd: float
    by_source: Dict[str, int] = Field(default_factory=dict)
    by_type: Dict[str, int] = Field(default_factory=dict)
