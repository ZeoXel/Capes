"""
Cape Executors - Different execution strategies for capabilities.
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, TYPE_CHECKING

from cape.runtime.context import ExecutionContext, ExecutionResult

if TYPE_CHECKING:
    from cape.core.models import Cape

logger = logging.getLogger(__name__)


class BaseExecutor(ABC):
    """Base class for Cape executors."""

    @abstractmethod
    async def execute(
        self,
        cape: "Cape",
        inputs: Dict[str, Any],
        context: ExecutionContext,
    ) -> ExecutionResult:
        """Execute the Cape and return result."""
        pass

    def validate_inputs(
        self,
        cape: "Cape",
        inputs: Dict[str, Any],
    ) -> Optional[str]:
        """
        Validate inputs against schema.
        Returns error message if invalid, None if valid.
        """
        schema = cape.interface.input_schema
        required = schema.required

        for field in required:
            if field not in inputs:
                return f"Missing required field: {field}"

        return None


class CodeExecutor(BaseExecutor):
    """Execute Python code."""

    def __init__(self, sandbox: bool = True):
        self.sandbox = sandbox

    async def execute(
        self,
        cape: "Cape",
        inputs: Dict[str, Any],
        context: ExecutionContext,
    ) -> ExecutionResult:
        """Execute code from Cape."""
        start_time = time.time()

        try:
            code = cape.execution.code
            if not code and cape.execution.entrypoint:
                # Load code from entrypoint
                code = self._load_entrypoint(cape)

            if not code:
                return ExecutionResult(
                    success=False,
                    error="No code or entrypoint specified",
                )

            # Execute code
            local_vars = {"inputs": inputs, "context": context}
            exec(code, {"__builtins__": __builtins__}, local_vars)

            output = local_vars.get("result", local_vars.get("output"))

            return ExecutionResult(
                success=True,
                output=output,
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            logger.error(f"Code execution failed: {e}")
            return ExecutionResult(
                success=False,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000,
            )

    def _load_entrypoint(self, cape: "Cape") -> Optional[str]:
        """Load code from entrypoint file."""
        # TODO: Implement file loading
        return None


class ToolExecutor(BaseExecutor):
    """Execute using registered tools."""

    def __init__(self, tool_registry: Optional[Dict[str, Callable]] = None):
        self.tools = tool_registry or {}

    def register_tool(self, name: str, func: Callable):
        """Register a tool function."""
        self.tools[name] = func

    async def execute(
        self,
        cape: "Cape",
        inputs: Dict[str, Any],
        context: ExecutionContext,
    ) -> ExecutionResult:
        """Execute using tools."""
        start_time = time.time()

        try:
            # Get entrypoint tool
            entrypoint = cape.execution.entrypoint
            if not entrypoint:
                return ExecutionResult(
                    success=False,
                    error="No entrypoint specified for tool execution",
                )

            tool = self.tools.get(entrypoint)
            if not tool:
                return ExecutionResult(
                    success=False,
                    error=f"Tool not found: {entrypoint}",
                )

            # Execute tool
            if asyncio.iscoroutinefunction(tool):
                output = await tool(**inputs)
            else:
                output = tool(**inputs)

            return ExecutionResult(
                success=True,
                output=output,
                execution_time_ms=(time.time() - start_time) * 1000,
            )

        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return ExecutionResult(
                success=False,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000,
            )


class LLMExecutor(BaseExecutor):
    """Execute using Language Model."""

    def __init__(self, adapter_factory: Optional[Callable] = None):
        self.adapter_factory = adapter_factory

    async def execute(
        self,
        cape: "Cape",
        inputs: Dict[str, Any],
        context: ExecutionContext,
    ) -> ExecutionResult:
        """Execute using LLM via adapter."""
        start_time = time.time()

        try:
            # Get adapter
            model = context.model_adapter or "openai"
            adapter_config = cape.get_adapter(model)

            if not adapter_config and not self.adapter_factory:
                return ExecutionResult(
                    success=False,
                    error=f"No adapter configured for model: {model}",
                )

            # Build prompt from adapter config
            prompt = self._build_prompt(cape, adapter_config, inputs)

            # Execute via adapter factory (injected dependency)
            if self.adapter_factory:
                adapter = self.adapter_factory(model)
                if not adapter:
                    return ExecutionResult(
                        success=False,
                        error=f"Failed to create adapter for model: {model}",
                    )

                response = await adapter.execute(prompt, context)

                # Handle AdapterResponse object or dict
                if hasattr(response, 'content'):
                    # AdapterResponse object
                    content = response.content
                    tokens = response.tokens
                    cost = response.cost
                else:
                    # Dict response
                    content = response.get("content")
                    tokens = response.get("tokens", 0)
                    cost = response.get("cost", 0)

                context.add_tokens(tokens)
                context.add_cost(cost)

                return ExecutionResult(
                    success=True,
                    output=content,
                    execution_time_ms=(time.time() - start_time) * 1000,
                    metadata={"model": model, "tokens": tokens},
                )
            else:
                return ExecutionResult(
                    success=False,
                    error="No adapter factory configured",
                )

        except Exception as e:
            logger.error(f"LLM execution failed: {e}")
            return ExecutionResult(
                success=False,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000,
            )

    def _build_prompt(
        self,
        cape: "Cape",
        adapter_config: Optional[Dict[str, Any]],
        inputs: Dict[str, Any],
    ) -> str:
        """Build prompt from Cape and adapter config."""
        if adapter_config and "system_prompt" in adapter_config:
            system = adapter_config["system_prompt"]
        else:
            system = f"You are executing the capability: {cape.name}\n\n{cape.description}"

        # Format inputs
        inputs_str = "\n".join(f"- {k}: {v}" for k, v in inputs.items())

        return f"{system}\n\n## Inputs\n{inputs_str}\n\n## Task\nExecute the capability and provide the result."


class WorkflowExecutor(BaseExecutor):
    """Execute multi-step workflows."""

    def __init__(self, runtime: Optional[Any] = None):
        self.runtime = runtime

    async def execute(
        self,
        cape: "Cape",
        inputs: Dict[str, Any],
        context: ExecutionContext,
    ) -> ExecutionResult:
        """Execute workflow steps."""
        start_time = time.time()

        if not cape.orchestration or not cape.orchestration.steps:
            return ExecutionResult(
                success=False,
                error="No workflow steps defined",
            )

        try:
            orchestration = cape.orchestration
            state = inputs.copy()
            results = {}

            # Find entry step
            current_step = orchestration.entry_step
            if not current_step and orchestration.steps:
                current_step = orchestration.steps[0].id

            # Execute steps
            while current_step:
                step_def = self._get_step(orchestration.steps, current_step)
                if not step_def:
                    break

                context.record_step(step_def.id)

                # Check condition
                if step_def.condition:
                    if not self._eval_condition(step_def.condition, state):
                        current_step = step_def.on_failure
                        continue

                # Execute step
                step_result = await self._execute_step(step_def, state, context)
                results[step_def.id] = step_result

                if step_result.success:
                    # Update state with output
                    if isinstance(step_result.output, dict):
                        state.update(step_result.output)
                    else:
                        state[f"{step_def.id}_output"] = step_result.output

                    current_step = step_def.on_success
                else:
                    current_step = step_def.on_failure

                # Check for exit
                if current_step in orchestration.exit_steps:
                    break

            return ExecutionResult(
                success=all(r.success for r in results.values()),
                output=state,
                execution_time_ms=(time.time() - start_time) * 1000,
                metadata={"steps": list(results.keys())},
            )

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            return ExecutionResult(
                success=False,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000,
            )

    def _get_step(self, steps, step_id):
        """Get step definition by ID."""
        for step in steps:
            if step.id == step_id:
                return step
        return None

    def _eval_condition(self, condition: str, state: Dict[str, Any]) -> bool:
        """Evaluate step condition."""
        try:
            return bool(eval(condition, {"__builtins__": {}}, state))
        except:
            return False

    async def _execute_step(self, step_def, state, context):
        """Execute a single step."""
        # Resolve inputs
        step_inputs = {}
        for key, value in step_def.inputs.items():
            if isinstance(value, str) and value.startswith("$"):
                # Reference to state variable
                var_name = value[1:]
                step_inputs[key] = state.get(var_name)
            else:
                step_inputs[key] = value

        # Execute via runtime (if available) or inline
        if self.runtime:
            return await self.runtime.execute(step_def.action, step_inputs, context)
        else:
            # Inline execution placeholder
            return ExecutionResult(
                success=True,
                output={"action": step_def.action, "inputs": step_inputs},
            )


class HybridExecutor(BaseExecutor):
    """Combine multiple execution strategies."""

    def __init__(
        self,
        code_executor: Optional[CodeExecutor] = None,
        tool_executor: Optional[ToolExecutor] = None,
        llm_executor: Optional[LLMExecutor] = None,
        workflow_executor: Optional[WorkflowExecutor] = None,
    ):
        self.code_executor = code_executor or CodeExecutor()
        self.tool_executor = tool_executor or ToolExecutor()
        self.llm_executor = llm_executor or LLMExecutor()
        self.workflow_executor = workflow_executor or WorkflowExecutor()

    async def execute(
        self,
        cape: "Cape",
        inputs: Dict[str, Any],
        context: ExecutionContext,
    ) -> ExecutionResult:
        """Execute using appropriate strategy based on Cape type."""
        exec_type = cape.execution.type

        if exec_type.value == "code":
            return await self.code_executor.execute(cape, inputs, context)
        elif exec_type.value == "tool":
            return await self.tool_executor.execute(cape, inputs, context)
        elif exec_type.value == "llm":
            return await self.llm_executor.execute(cape, inputs, context)
        elif exec_type.value == "workflow":
            return await self.workflow_executor.execute(cape, inputs, context)
        else:  # hybrid
            # Try in order: tool -> code -> llm
            if cape.execution.entrypoint and cape.execution.entrypoint in self.tool_executor.tools:
                return await self.tool_executor.execute(cape, inputs, context)
            elif cape.execution.code or cape.execution.entrypoint:
                return await self.code_executor.execute(cape, inputs, context)
            else:
                return await self.llm_executor.execute(cape, inputs, context)
