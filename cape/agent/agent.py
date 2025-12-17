"""
Cape Agent - High-level agent for capability execution.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from cape.core.models import Cape, CapeResult
from cape.registry.registry import CapeRegistry
from cape.runtime.runtime import CapeRuntime
from cape.runtime.context import ExecutionContext
from cape.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)


class CapeAgent:
    """
    High-level agent for Cape-based capability execution.

    The CapeAgent provides a simple interface for:
    - Automatic capability matching from user input
    - Executing capabilities with the best matching model
    - Managing execution context and history

    Usage:
        agent = CapeAgent(
            capes_dir="./capes",
            skills_dir="./skills",
        )

        # Auto-match and execute
        result = await agent.run("process this PDF and extract tables")

        # Or explicit execution
        result = await agent.execute("pdf-processor", {"file": "doc.pdf"})
    """

    def __init__(
        self,
        capes_dir: Optional[Path] = None,
        skills_dir: Optional[Path] = None,
        default_model: str = "openai",
        adapter_factory: Optional[Callable[[str], BaseAdapter]] = None,
    ):
        """
        Initialize agent.

        Args:
            capes_dir: Directory with Cape definitions
            skills_dir: Directory with Claude Skills to import
            default_model: Default model adapter
            adapter_factory: Factory for creating model adapters
        """
        # Create registry
        self.registry = CapeRegistry(
            capes_dir=capes_dir,
            skills_dir=skills_dir,
            auto_load=True,
        )

        # Create runtime
        self.runtime = CapeRuntime(
            registry=self.registry,
            default_model=default_model,
            adapter_factory=adapter_factory,
        )

        # Conversation history
        self.history: List[Dict[str, Any]] = []

        # Configuration
        self.auto_match_threshold = 0.4
        self.verbose = False

    # ==================== Main Interface ====================

    async def run(
        self,
        user_input: str,
        context: Optional[ExecutionContext] = None,
        model: Optional[str] = None,
    ) -> CapeResult:
        """
        Process user input by matching and executing best Cape.

        Args:
            user_input: User's request
            context: Optional execution context
            model: Optional model override

        Returns:
            CapeResult from execution
        """
        # Match Cape
        match = self.registry.match_best(user_input, threshold=self.auto_match_threshold)

        if not match:
            return CapeResult(
                cape_id="none",
                success=False,
                error=f"No capability found for: {user_input}",
            )

        if self.verbose:
            logger.info(f"Matched Cape: {match.id}")

        # Execute
        result = await self.execute(
            cape_id=match.id,
            inputs={"input": user_input},
            context=context,
            model=model,
        )

        # Record history
        self.history.append({
            "input": user_input,
            "cape_id": match.id,
            "success": result.success,
            "output": result.output if result.success else result.error,
        })

        return result

    async def execute(
        self,
        cape_id: str,
        inputs: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
        model: Optional[str] = None,
    ) -> CapeResult:
        """
        Execute a specific Cape.

        Args:
            cape_id: Cape to execute
            inputs: Input parameters
            context: Optional execution context
            model: Optional model override

        Returns:
            CapeResult from execution
        """
        return await self.runtime.execute(
            cape_id=cape_id,
            inputs=inputs,
            context=context,
            model=model,
        )

    def run_sync(
        self,
        user_input: str,
        context: Optional[ExecutionContext] = None,
        model: Optional[str] = None,
    ) -> CapeResult:
        """Synchronous version of run()."""
        return asyncio.run(self.run(user_input, context, model))

    def execute_sync(
        self,
        cape_id: str,
        inputs: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
        model: Optional[str] = None,
    ) -> CapeResult:
        """Synchronous version of execute()."""
        return asyncio.run(self.execute(cape_id, inputs, context, model))

    # ==================== Tool Registration ====================

    def register_tool(self, name: str, func: Callable):
        """Register a tool function."""
        self.runtime.register_tool(name, func)

    def register_tools(self, tools: Dict[str, Callable]):
        """Register multiple tools."""
        self.runtime.register_tools(tools)

    # ==================== Utility ====================

    def list_capabilities(self) -> List[Dict[str, Any]]:
        """List all available capabilities."""
        return [
            {
                "id": cape.id,
                "name": cape.name,
                "description": cape.description[:100] + "..." if len(cape.description) > 100 else cape.description,
                "type": cape.execution.type.value,
                "source": cape.metadata.source.value,
            }
            for cape in self.registry.all()
        ]

    def suggest_capabilities(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Suggest capabilities for a query."""
        results = self.registry.match(query, top_k=top_k)
        return [
            {
                "id": r["cape"].id,
                "name": r["cape"].name,
                "score": r["score"],
                "match_type": r["match_type"],
            }
            for r in results
        ]

    def get_capability(self, cape_id: str) -> Optional[Cape]:
        """Get capability by ID."""
        return self.registry.get(cape_id)

    def clear_history(self):
        """Clear conversation history."""
        self.history.clear()

    def get_status(self) -> Dict[str, Any]:
        """Get agent status."""
        return {
            "capabilities": self.registry.count(),
            "history_length": len(self.history),
            "runtime_metrics": self.runtime.get_metrics(),
            "registry_summary": self.registry.summary(),
        }


def create_agent(
    capes_dir: Optional[str] = None,
    skills_dir: Optional[str] = None,
    **kwargs,
) -> CapeAgent:
    """
    Convenience function to create a CapeAgent.

    Args:
        capes_dir: Path to capes directory
        skills_dir: Path to skills directory
        **kwargs: Additional agent options

    Returns:
        Configured CapeAgent
    """
    return CapeAgent(
        capes_dir=Path(capes_dir) if capes_dir else None,
        skills_dir=Path(skills_dir) if skills_dir else None,
        **kwargs,
    )
