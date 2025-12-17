"""
Cape Runtime - Main execution engine.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

from cape.core.models import Cape, CapeResult, ExecutionType
from cape.runtime.context import ExecutionContext
from cape.runtime.executors import (
    BaseExecutor,
    CodeExecutor,
    HybridExecutor,
    LLMExecutor,
    ToolExecutor,
    WorkflowExecutor,
)

if TYPE_CHECKING:
    from cape.registry.registry import CapeRegistry
    from cape.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)


class CapeRuntime:
    """
    Cape Runtime - Execution engine for capabilities.

    The runtime is responsible for:
    - Resolving Cape definitions from registry
    - Managing execution context
    - Dispatching to appropriate executors
    - Collecting metrics and traces
    - Enforcing safety constraints

    Usage:
        registry = CapeRegistry(capes_dir="./capes")
        runtime = CapeRuntime(registry)

        result = await runtime.execute("json-processor", {"data": '{"key": "value"}'})
    """

    def __init__(
        self,
        registry: Optional["CapeRegistry"] = None,
        default_model: str = "openai",
        adapter_factory: Optional[Callable[[str], "BaseAdapter"]] = None,
    ):
        """
        Initialize runtime.

        Args:
            registry: Cape registry for resolving capabilities
            default_model: Default model adapter to use
            adapter_factory: Factory for creating model adapters
        """
        self.registry = registry
        self.default_model = default_model
        self.adapter_factory = adapter_factory

        # Executors
        self._tool_registry: Dict[str, Callable] = {}
        self._executors: Dict[ExecutionType, BaseExecutor] = {}
        self._init_executors()

        # Metrics
        self._execution_count = 0
        self._total_tokens = 0
        self._total_cost = 0.0

    def _init_executors(self):
        """Initialize executors."""
        tool_executor = ToolExecutor(self._tool_registry)
        code_executor = CodeExecutor()
        llm_executor = LLMExecutor(self.adapter_factory)
        workflow_executor = WorkflowExecutor(self)

        self._executors = {
            ExecutionType.TOOL: tool_executor,
            ExecutionType.CODE: code_executor,
            ExecutionType.LLM: llm_executor,
            ExecutionType.WORKFLOW: workflow_executor,
            ExecutionType.HYBRID: HybridExecutor(
                code_executor=code_executor,
                tool_executor=tool_executor,
                llm_executor=llm_executor,
                workflow_executor=workflow_executor,
            ),
        }

    # ==================== Tool Registration ====================

    def register_tool(self, name: str, func: Callable):
        """Register a tool function."""
        self._tool_registry[name] = func
        # Update tool executor
        if ExecutionType.TOOL in self._executors:
            self._executors[ExecutionType.TOOL].tools[name] = func

    def register_tools(self, tools: Dict[str, Callable]):
        """Register multiple tools."""
        for name, func in tools.items():
            self.register_tool(name, func)

    # ==================== Execution ====================

    async def execute(
        self,
        cape_id: str,
        inputs: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
        model: Optional[str] = None,
    ) -> CapeResult:
        """
        Execute a Cape by ID.

        Args:
            cape_id: ID of the Cape to execute
            inputs: Input parameters
            context: Execution context (created if not provided)
            model: Model adapter to use (defaults to default_model)

        Returns:
            CapeResult with output or error
        """
        # Resolve Cape
        cape = self._resolve_cape(cape_id)
        if not cape:
            return CapeResult(
                cape_id=cape_id,
                success=False,
                error=f"Cape not found: {cape_id}",
            )

        return await self.execute_cape(cape, inputs, context, model)

    async def execute_cape(
        self,
        cape: Cape,
        inputs: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
        model: Optional[str] = None,
    ) -> CapeResult:
        """
        Execute a Cape object.

        Args:
            cape: Cape to execute
            inputs: Input parameters
            context: Execution context (created if not provided)
            model: Model adapter to use

        Returns:
            CapeResult with output or error
        """
        # Create context if not provided
        if context is None:
            context = ExecutionContext(
                timeout_seconds=cape.execution.timeout_seconds,
                available_tools=list(self._tool_registry.keys()),
                model_adapter=model or self.default_model,
            )
        else:
            context.model_adapter = model or context.model_adapter or self.default_model

        # Validate inputs
        executor = self._get_executor(cape)
        validation_error = executor.validate_inputs(cape, inputs)
        if validation_error:
            return CapeResult(
                cape_id=cape.id,
                success=False,
                error=validation_error,
            )

        # Check preconditions
        precond_error = self._check_preconditions(cape, context)
        if precond_error:
            return CapeResult(
                cape_id=cape.id,
                success=False,
                error=precond_error,
            )

        # Check safety constraints
        safety_error = self._check_safety(cape, context)
        if safety_error:
            return CapeResult(
                cape_id=cape.id,
                success=False,
                error=safety_error,
            )

        # Execute
        context.add_to_history("execution_start", {"cape_id": cape.id, "inputs": inputs})

        try:
            result = await executor.execute(cape, inputs, context)

            # Build result
            cape_result = CapeResult(
                cape_id=cape.id,
                success=result.success,
                output=result.output,
                error=result.error,
                execution_time_ms=result.execution_time_ms,
                tokens_used=context.tokens_used,
                cost_usd=context.cost_usd,
                trace_id=context.trace_id,
                steps_executed=context.steps_executed,
            )

            # Update metrics
            self._execution_count += 1
            self._total_tokens += context.tokens_used
            self._total_cost += context.cost_usd

            context.add_to_history("execution_end", {
                "success": result.success,
                "execution_time_ms": result.execution_time_ms,
            })

            return cape_result

        except Exception as e:
            logger.error(f"Execution failed for {cape.id}: {e}")
            return CapeResult(
                cape_id=cape.id,
                success=False,
                error=str(e),
                trace_id=context.trace_id,
            )

    def execute_sync(
        self,
        cape_id: str,
        inputs: Dict[str, Any],
        context: Optional[ExecutionContext] = None,
        model: Optional[str] = None,
    ) -> CapeResult:
        """Synchronous execution wrapper."""
        return asyncio.run(self.execute(cape_id, inputs, context, model))

    # ==================== Helpers ====================

    def _resolve_cape(self, cape_id: str) -> Optional[Cape]:
        """Resolve Cape from registry or ID."""
        if self.registry:
            return self.registry.get(cape_id)
        return None

    def _get_executor(self, cape: Cape) -> BaseExecutor:
        """Get appropriate executor for Cape."""
        exec_type = cape.execution.type
        return self._executors.get(exec_type, self._executors[ExecutionType.HYBRID])

    def _check_preconditions(
        self,
        cape: Cape,
        context: ExecutionContext,
    ) -> Optional[str]:
        """Check preconditions. Returns error message if failed."""
        # Check required context
        for required in cape.interface.required_context:
            if required == "user_id" and not context.user_id:
                return f"Missing required context: {required}"
            if required == "session_id" and not context.session_id:
                return f"Missing required context: {required}"

        # Check required tools
        for tool in cape.execution.tools_required:
            if tool not in context.available_tools:
                return f"Required tool not available: {tool}"

        return None

    def _check_safety(
        self,
        cape: Cape,
        context: ExecutionContext,
    ) -> Optional[str]:
        """Check safety constraints. Returns error message if failed."""
        safety = cape.safety

        # Check if approval required
        if safety.requires_approval:
            # TODO: Implement approval flow
            pass

        # Check cost limit
        if cape.execution.max_cost_usd:
            if context.cost_usd > cape.execution.max_cost_usd:
                return f"Cost limit exceeded: {context.cost_usd} > {cape.execution.max_cost_usd}"

        return None

    # ==================== Metrics ====================

    def get_metrics(self) -> Dict[str, Any]:
        """Get runtime metrics."""
        return {
            "execution_count": self._execution_count,
            "total_tokens": self._total_tokens,
            "total_cost_usd": self._total_cost,
            "registered_tools": len(self._tool_registry),
        }

    def reset_metrics(self):
        """Reset metrics."""
        self._execution_count = 0
        self._total_tokens = 0
        self._total_cost = 0.0
