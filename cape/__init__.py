"""
Cape - Capability Package

Model-agnostic capability abstraction for AI agents.

Core Concepts:
- Cape: A complete capability definition (metadata + interface + execution + orchestration)
- Runtime: Execution backend for running capabilities
- Adapter: Model-specific translation layer
- Registry: Capability discovery and management

Usage:
    from cape import Cape, CapeRegistry, CapeRuntime

    # Load capabilities
    registry = CapeRegistry(capes_dir="./capes")

    # Create runtime
    runtime = CapeRuntime(registry)

    # Execute capability
    result = await runtime.execute("json-processor", {"data": '{"key": "value"}'})
"""

from cape.core.models import (
    Cape,
    CapeMetadata,
    CapeInterface,
    CapeExecution,
    CapeOrchestration,
    CapeSafety,
    ExecutionType,
    RiskLevel,
)
from cape.registry.registry import CapeRegistry
from cape.runtime.runtime import CapeRuntime
from cape.adapters.base import BaseAdapter

__version__ = "0.1.0"

__all__ = [
    # Core models
    "Cape",
    "CapeMetadata",
    "CapeInterface",
    "CapeExecution",
    "CapeOrchestration",
    "CapeSafety",
    "ExecutionType",
    "RiskLevel",
    # Registry
    "CapeRegistry",
    # Runtime
    "CapeRuntime",
    # Adapters
    "BaseAdapter",
]
