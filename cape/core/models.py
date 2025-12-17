"""
Cape Core Models - Capability Package data structures.

A Cape (Capability Package) is a model-agnostic definition of what an agent can do.
Unlike Skills (which are prompts for a specific model), Capes define:
- What the capability IS (metadata)
- What it NEEDS and PRODUCES (interface)
- HOW it executes (execution)
- How it COMPOSES with others (orchestration)
- WHO can adapt it (model_adapters)
- SAFETY constraints (safety)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator


# ============================================================
# Enums
# ============================================================

class ExecutionType(str, Enum):
    """How the capability executes."""
    TOOL = "tool"           # Direct tool/function call
    WORKFLOW = "workflow"   # Multi-step orchestrated flow
    CODE = "code"           # Execute code (Python, etc.)
    LLM = "llm"             # Pure LLM generation
    HYBRID = "hybrid"       # Combination of above


class RiskLevel(str, Enum):
    """Safety risk classification."""
    LOW = "low"             # Read-only, no side effects
    MEDIUM = "medium"       # Limited side effects, reversible
    HIGH = "high"           # Significant side effects
    CRITICAL = "critical"   # Irreversible or dangerous


class SourceType(str, Enum):
    """Where this Cape came from."""
    NATIVE = "native"           # Built natively for Cape
    SKILL = "skill"             # Imported from Claude Skill
    CLAUDE_SKILL = "skill"      # Alias for backward compatibility
    OPENAI_FUNC = "openai_func" # Imported from OpenAI function
    MCP_TOOL = "mcp_tool"       # Imported from MCP tool
    CUSTOM = "custom"           # User-defined


# ============================================================
# Interface Definitions
# ============================================================

class InputSchema(BaseModel):
    """Schema for capability input."""
    type: str = "object"
    properties: Dict[str, Any] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)
    description: Optional[str] = None

    @classmethod
    def from_json_schema(cls, schema: Dict[str, Any]) -> "InputSchema":
        """Create from JSON Schema."""
        return cls(**schema)

    def to_json_schema(self) -> Dict[str, Any]:
        """Convert to JSON Schema format."""
        schema = {"type": self.type}
        if self.properties:
            schema["properties"] = self.properties
        if self.required:
            schema["required"] = self.required
        if self.description:
            schema["description"] = self.description
        return schema


class OutputSchema(BaseModel):
    """Schema for capability output."""
    type: str = "object"
    properties: Dict[str, Any] = Field(default_factory=dict)
    description: Optional[str] = None

    def to_json_schema(self) -> Dict[str, Any]:
        """Convert to JSON Schema format."""
        schema = {"type": self.type}
        if self.properties:
            schema["properties"] = self.properties
        if self.description:
            schema["description"] = self.description
        return schema


class CapeInterface(BaseModel):
    """
    Capability interface definition.

    Defines what the capability needs (input) and produces (output),
    plus any preconditions and postconditions.
    """
    input_schema: InputSchema = Field(default_factory=InputSchema)
    output_schema: OutputSchema = Field(default_factory=OutputSchema)

    # Conditions
    preconditions: List[str] = Field(
        default_factory=list,
        description="Conditions that must be true before execution"
    )
    postconditions: List[str] = Field(
        default_factory=list,
        description="Conditions guaranteed after successful execution"
    )

    # Runtime context requirements
    required_context: List[str] = Field(
        default_factory=list,
        description="Required runtime context (e.g., user_id, session)"
    )
    optional_context: List[str] = Field(
        default_factory=list,
        description="Optional runtime context"
    )


# ============================================================
# Execution Definition
# ============================================================

class CapeExecution(BaseModel):
    """
    How the capability executes.

    This is the core differentiator from Skills - Cape defines
    actual execution semantics, not just prompts.
    """
    type: ExecutionType = ExecutionType.HYBRID

    # Entry point
    entrypoint: Optional[str] = Field(
        None,
        description="Function/module to execute (e.g., 'handlers.process')"
    )
    code: Optional[str] = Field(
        None,
        description="Inline code to execute"
    )

    # Tool configuration
    tools_allowed: List[str] = Field(
        default_factory=list,
        description="Tools this capability can use"
    )
    tools_required: List[str] = Field(
        default_factory=list,
        description="Tools that must be available"
    )

    # Execution constraints
    timeout_seconds: int = Field(30, ge=1, le=3600)
    max_retries: int = Field(0, ge=0, le=10)
    retry_delay_seconds: float = Field(1.0, ge=0)

    # Rollback
    rollback_on_failure: bool = False
    rollback_handler: Optional[str] = None

    # Resource limits
    max_tokens: Optional[int] = None
    max_cost_usd: Optional[float] = None


# ============================================================
# Orchestration Definition
# ============================================================

class StepDefinition(BaseModel):
    """A single step in a workflow."""
    id: str
    name: str
    description: Optional[str] = None

    # What to do
    action: str = Field(description="Cape ID or inline action")
    inputs: Dict[str, Any] = Field(
        default_factory=dict,
        description="Input mapping (can reference previous step outputs)"
    )

    # Flow control
    condition: Optional[str] = Field(
        None,
        description="Condition expression for conditional execution"
    )
    on_success: Optional[str] = Field(None, description="Next step on success")
    on_failure: Optional[str] = Field(None, description="Step to run on failure")

    # Parallel execution
    parallel_with: List[str] = Field(
        default_factory=list,
        description="Steps that can run in parallel with this one"
    )


class CapeOrchestration(BaseModel):
    """
    Multi-step workflow orchestration.

    For capabilities that involve multiple steps, state transitions,
    or complex control flow.
    """
    steps: List[StepDefinition] = Field(default_factory=list)

    # Entry/exit
    entry_step: Optional[str] = None
    exit_steps: List[str] = Field(default_factory=list)

    # State management
    state_schema: Optional[Dict[str, Any]] = Field(
        None,
        description="Schema for workflow state"
    )
    persist_state: bool = False

    # Parallelism
    max_parallel: int = Field(1, ge=1, le=100)
    allow_branching: bool = True


# ============================================================
# Safety & Cost
# ============================================================

class CapeSafety(BaseModel):
    """Safety and cost controls."""
    risk_level: RiskLevel = RiskLevel.MEDIUM

    # Cost estimation
    estimated_cost_usd: Optional[float] = None
    cost_per_call_usd: Optional[float] = None

    # Audit
    audit_log: bool = True
    log_inputs: bool = False  # May contain sensitive data
    log_outputs: bool = True

    # Rate limiting
    max_calls_per_minute: Optional[int] = None
    max_calls_per_day: Optional[int] = None

    # Approval
    requires_approval: bool = False
    approval_roles: List[str] = Field(default_factory=list)


# ============================================================
# Composition
# ============================================================

class CapeComposition(BaseModel):
    """How this Cape composes with others."""

    # Dependencies
    dependencies: List[str] = Field(
        default_factory=list,
        description="Cape IDs this depends on"
    )
    optional_dependencies: List[str] = Field(default_factory=list)

    # Composition rules
    can_be_chained: bool = True
    can_run_parallel: bool = True
    conflicts_with: List[str] = Field(
        default_factory=list,
        description="Cape IDs that conflict with this one"
    )

    # Provides/Requires (for capability matching)
    provides: List[str] = Field(
        default_factory=list,
        description="Capabilities this provides (e.g., 'file_read', 'json_parse')"
    )
    requires: List[str] = Field(
        default_factory=list,
        description="Capabilities required from environment"
    )


# ============================================================
# Observability
# ============================================================

class CapeObservability(BaseModel):
    """Observability configuration."""
    metrics: List[str] = Field(
        default_factory=lambda: ["latency", "success_rate"],
        description="Metrics to collect"
    )
    tracing: bool = True
    log_level: Literal["debug", "info", "warning", "error"] = "info"

    # Custom events
    custom_events: List[str] = Field(
        default_factory=list,
        description="Custom events to emit"
    )


# ============================================================
# Metadata
# ============================================================

class CapeMetadata(BaseModel):
    """
    Cape metadata for identification and discovery.
    """
    # Classification
    version: str = "1.0.0"
    tags: List[str] = Field(default_factory=list)
    intents: List[str] = Field(
        default_factory=list,
        description="Intent patterns that trigger this Cape"
    )

    # Source
    source: SourceType = SourceType.NATIVE
    source_ref: Optional[str] = Field(
        None,
        description="Reference to original source (e.g., skill file path)"
    )

    # Ownership
    author: Optional[str] = None
    maintainer: Optional[str] = None
    license: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


# ============================================================
# Model Adapters (stored separately but referenced here)
# ============================================================

class ModelAdapterRef(BaseModel):
    """Reference to a model-specific adapter."""
    model: str  # "claude", "openai", "local", etc.
    adapter_type: str  # "prompt", "function", "tool"
    config: Dict[str, Any] = Field(default_factory=dict)


# ============================================================
# Main Cape Model
# ============================================================

class Cape(BaseModel):
    """
    Capability Package - The complete capability definition.

    A Cape defines everything needed to:
    - Identify the capability (metadata)
    - Understand what it needs/produces (interface)
    - Execute it (execution)
    - Orchestrate complex flows (orchestration)
    - Adapt to different models (model_adapters)
    - Control safety/cost (safety)
    """

    # Core identification (top-level for convenience)
    id: str = Field(description="Unique identifier (e.g., 'json-processor')")
    name: str = Field(description="Human-readable name")
    version: str = "1.0.0"
    description: str = Field(default="", description="What this capability does + when to use it")

    # Extended metadata (optional)
    metadata: CapeMetadata = Field(default_factory=CapeMetadata)

    # Core definition
    interface: CapeInterface = Field(default_factory=CapeInterface)
    execution: CapeExecution = Field(default_factory=CapeExecution)

    # Optional advanced features
    orchestration: Optional[CapeOrchestration] = None
    composition: CapeComposition = Field(default_factory=CapeComposition)
    safety: CapeSafety = Field(default_factory=CapeSafety)
    observability: CapeObservability = Field(default_factory=CapeObservability)

    # Model-specific adapters (model_name -> adapter config)
    model_adapters: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    # File path (for loaded Capes)
    _path: Optional[Path] = None

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str:
        """Ensure ID is lowercase with hyphens."""
        return v.lower().replace("_", "-").replace(" ", "-")

    @property
    def is_workflow(self) -> bool:
        """Check if this Cape is a multi-step workflow."""
        return (
            self.orchestration is not None
            and len(self.orchestration.steps) > 0
        )

    @property
    def execution_type(self) -> ExecutionType:
        return self.execution.type

    # ==================== Methods ====================

    def get_adapter(self, model: str) -> Optional[Dict[str, Any]]:
        """Get adapter config for a specific model."""
        return self.model_adapters.get(model)

    def has_adapter(self, model: str) -> bool:
        """Check if adapter exists for model."""
        return model in self.model_adapters

    def add_adapter(self, model: str, config: Dict[str, Any]):
        """Add or update adapter for model."""
        self.model_adapters[model] = config

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return self.model_dump(exclude_none=True)

    def to_yaml(self) -> str:
        """Convert to YAML string."""
        import yaml
        return yaml.dump(self.to_dict(), default_flow_style=False, allow_unicode=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Cape":
        """Create from dictionary."""
        return cls(**data)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "Cape":
        """Create from YAML string."""
        import yaml
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)

    def __repr__(self) -> str:
        return f"Cape(id='{self.id}', type={self.execution_type.value})"


# ============================================================
# Execution Result
# ============================================================

class CapeResult(BaseModel):
    """Result of Cape execution."""
    cape_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None

    # Execution metadata
    execution_time_ms: float = 0
    tokens_used: int = 0
    cost_usd: float = 0

    # Tracing
    trace_id: Optional[str] = None
    steps_executed: List[str] = Field(default_factory=list)

    # State (for workflows)
    final_state: Optional[Dict[str, Any]] = None
