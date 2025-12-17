"""
Execution Context - Runtime context for Cape execution.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from cape.core.models import Cape


@dataclass
class ExecutionContext:
    """
    Runtime context for Cape execution.

    Contains all information needed during execution:
    - Identity (trace_id, user, session)
    - State (variables, history)
    - Resources (adapters, tools)
    - Configuration (timeout, limits)
    """

    # Identity
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    session_id: Optional[str] = None

    # Timing
    started_at: datetime = field(default_factory=datetime.now)
    timeout_seconds: int = 30

    # State
    variables: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)

    # Resources
    available_tools: List[str] = field(default_factory=list)
    model_adapter: Optional[str] = None

    # Metrics
    tokens_used: int = 0
    cost_usd: float = 0.0
    steps_executed: List[str] = field(default_factory=list)

    # Parent context (for nested execution)
    parent_context: Optional["ExecutionContext"] = None

    def get(self, key: str, default: Any = None) -> Any:
        """Get variable from context."""
        return self.variables.get(key, default)

    def set(self, key: str, value: Any):
        """Set variable in context."""
        self.variables[key] = value

    def add_to_history(self, event: str, data: Dict[str, Any]):
        """Add event to history."""
        self.history.append({
            "timestamp": datetime.now().isoformat(),
            "event": event,
            "data": data,
        })

    def record_step(self, step_id: str):
        """Record executed step."""
        self.steps_executed.append(step_id)

    def add_tokens(self, count: int):
        """Add to token count."""
        self.tokens_used += count

    def add_cost(self, amount: float):
        """Add to cost."""
        self.cost_usd += amount

    def fork(self) -> "ExecutionContext":
        """Create a child context for nested execution."""
        return ExecutionContext(
            trace_id=self.trace_id,
            user_id=self.user_id,
            session_id=self.session_id,
            timeout_seconds=self.timeout_seconds,
            variables=self.variables.copy(),
            available_tools=self.available_tools.copy(),
            model_adapter=self.model_adapter,
            parent_context=self,
        )

    def elapsed_seconds(self) -> float:
        """Get elapsed time since start."""
        return (datetime.now() - self.started_at).total_seconds()

    def is_timeout(self) -> bool:
        """Check if execution has timed out."""
        return self.elapsed_seconds() > self.timeout_seconds

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "started_at": self.started_at.isoformat(),
            "elapsed_seconds": self.elapsed_seconds(),
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
            "steps_executed": self.steps_executed,
            "variables_count": len(self.variables),
        }


@dataclass
class ExecutionResult:
    """Result of a single execution step."""
    success: bool
    output: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
