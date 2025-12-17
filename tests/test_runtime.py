"""Tests for Cape runtime."""

import pytest
import asyncio
from pathlib import Path

from cape.runtime.runtime import CapeRuntime
from cape.runtime.context import ExecutionContext, ExecutionResult
from cape.runtime.executors import CodeExecutor, ToolExecutor
from cape.registry.registry import CapeRegistry
from cape.core.models import Cape, CapeExecution, CapeMetadata, ExecutionType


class TestExecutionContext:
    """Tests for ExecutionContext."""

    def test_context_creation(self):
        """Test context creation with auto-generated trace_id."""
        ctx = ExecutionContext()
        assert ctx.trace_id is not None
        assert len(ctx.trace_id) > 0
        assert ctx.state == {}
        assert ctx.metrics == {}

    def test_context_with_custom_trace_id(self):
        """Test context with custom trace_id."""
        ctx = ExecutionContext(trace_id="custom-123")
        assert ctx.trace_id == "custom-123"

    def test_context_state_management(self):
        """Test context state management."""
        ctx = ExecutionContext()
        ctx.state["key1"] = "value1"
        ctx.state["key2"] = {"nested": "data"}

        assert ctx.state["key1"] == "value1"
        assert ctx.state["key2"]["nested"] == "data"

    def test_context_metrics(self):
        """Test context metrics tracking."""
        ctx = ExecutionContext()
        ctx.metrics["tokens_used"] = 100
        ctx.metrics["execution_time"] = 1.5

        assert ctx.metrics["tokens_used"] == 100
        assert ctx.metrics["execution_time"] == 1.5


class TestExecutionResult:
    """Tests for ExecutionResult."""

    def test_success_result(self):
        """Test successful execution result."""
        result = ExecutionResult(
            success=True,
            output={"data": "processed"},
            execution_time=0.5,
        )
        assert result.success is True
        assert result.output["data"] == "processed"
        assert result.error is None

    def test_error_result(self):
        """Test error execution result."""
        result = ExecutionResult(
            success=False,
            error="Execution failed",
        )
        assert result.success is False
        assert result.error == "Execution failed"


class TestCodeExecutor:
    """Tests for CodeExecutor."""

    @pytest.fixture
    def executor(self):
        return CodeExecutor()

    def test_execute_simple_code(self, executor):
        """Test executing simple Python code."""
        cape = Cape(
            id="test-code",
            name="Test Code",
            version="1.0.0",
            description="Test",
            execution=CapeExecution(
                type=ExecutionType.CODE,
                language="python",
                code="result = inputs.get('x', 0) * 2",
            ),
        )
        ctx = ExecutionContext()

        result = asyncio.run(executor.execute(cape, {"x": 5}, ctx))

        assert result.success is True
        assert result.output == 10

    def test_execute_code_with_error(self, executor):
        """Test code execution with error."""
        cape = Cape(
            id="test-error",
            name="Test Error",
            version="1.0.0",
            description="Test",
            execution=CapeExecution(
                type=ExecutionType.CODE,
                language="python",
                code="result = 1 / 0",  # Division by zero
            ),
        )
        ctx = ExecutionContext()

        result = asyncio.run(executor.execute(cape, {}, ctx))

        assert result.success is False
        assert "division" in result.error.lower() or "zero" in result.error.lower()


class TestToolExecutor:
    """Tests for ToolExecutor."""

    @pytest.fixture
    def executor(self):
        return ToolExecutor()

    def test_execute_registered_tool(self, executor):
        """Test executing a registered tool."""
        # Register a simple tool
        def add_numbers(a: int, b: int) -> int:
            return a + b

        executor.register_tool("add_numbers", add_numbers)

        cape = Cape(
            id="test-tool",
            name="Test Tool",
            version="1.0.0",
            description="Test",
            execution=CapeExecution(
                type=ExecutionType.TOOL,
                tool_name="add_numbers",
            ),
        )
        ctx = ExecutionContext()

        result = asyncio.run(executor.execute(cape, {"a": 3, "b": 4}, ctx))

        assert result.success is True
        assert result.output == 7

    def test_execute_missing_tool(self, executor):
        """Test executing non-existent tool."""
        cape = Cape(
            id="test-missing",
            name="Test Missing",
            version="1.0.0",
            description="Test",
            execution=CapeExecution(
                type=ExecutionType.TOOL,
                tool_name="nonexistent_tool",
            ),
        )
        ctx = ExecutionContext()

        result = asyncio.run(executor.execute(cape, {}, ctx))

        assert result.success is False
        assert "not found" in result.error.lower() or "not registered" in result.error.lower()


class TestCapeRuntime:
    """Tests for CapeRuntime."""

    @pytest.fixture
    def runtime(self):
        """Create runtime with empty registry."""
        registry = CapeRegistry(auto_load=False, use_embeddings=False)
        return CapeRuntime(registry=registry)

    @pytest.fixture
    def runtime_with_cape(self, runtime):
        """Runtime with a registered Cape."""
        cape = Cape(
            id="simple-cape",
            name="Simple Cape",
            version="1.0.0",
            description="A simple test cape",
            execution=CapeExecution(
                type=ExecutionType.CODE,
                language="python",
                code="result = f'Hello, {inputs.get(\"name\", \"World\")}!'",
            ),
        )
        runtime.registry.register(cape)
        return runtime

    def test_execute_cape(self, runtime_with_cape):
        """Test executing a Cape."""
        result = asyncio.run(runtime_with_cape.execute(
            cape_id="simple-cape",
            inputs={"name": "Test"},
        ))

        assert result.success is True
        assert "Hello, Test!" in str(result.output)

    def test_execute_sync(self, runtime_with_cape):
        """Test synchronous execution."""
        result = runtime_with_cape.execute_sync(
            cape_id="simple-cape",
            inputs={"name": "Sync"},
        )

        assert result.success is True
        assert "Sync" in str(result.output)

    def test_execute_nonexistent_cape(self, runtime):
        """Test executing non-existent Cape."""
        result = asyncio.run(runtime.execute(
            cape_id="nonexistent",
            inputs={},
        ))

        assert result.success is False
        assert "not found" in result.error.lower()

    def test_register_tool(self, runtime):
        """Test tool registration."""
        def my_tool(x):
            return x * 2

        runtime.register_tool("my_tool", my_tool)

        # Register a Cape that uses the tool
        cape = Cape(
            id="tool-cape",
            name="Tool Cape",
            version="1.0.0",
            description="Uses a tool",
            execution=CapeExecution(
                type=ExecutionType.TOOL,
                tool_name="my_tool",
            ),
        )
        runtime.registry.register(cape)

        result = asyncio.run(runtime.execute("tool-cape", {"x": 5}))
        assert result.success is True
        assert result.output == 10

    def test_register_multiple_tools(self, runtime):
        """Test registering multiple tools."""
        tools = {
            "add": lambda a, b: a + b,
            "multiply": lambda a, b: a * b,
        }
        runtime.register_tools(tools)

        # Both tools should be available
        cape_add = Cape(
            id="add-cape",
            name="Add",
            version="1.0.0",
            description="Add",
            execution=CapeExecution(type=ExecutionType.TOOL, tool_name="add"),
        )
        cape_mul = Cape(
            id="mul-cape",
            name="Multiply",
            version="1.0.0",
            description="Multiply",
            execution=CapeExecution(type=ExecutionType.TOOL, tool_name="multiply"),
        )
        runtime.registry.register(cape_add)
        runtime.registry.register(cape_mul)

        result_add = asyncio.run(runtime.execute("add-cape", {"a": 2, "b": 3}))
        result_mul = asyncio.run(runtime.execute("mul-cape", {"a": 2, "b": 3}))

        assert result_add.output == 5
        assert result_mul.output == 6

    def test_execution_with_context(self, runtime_with_cape):
        """Test execution with custom context."""
        ctx = ExecutionContext(trace_id="test-trace-123")
        ctx.state["custom_key"] = "custom_value"

        result = asyncio.run(runtime_with_cape.execute(
            cape_id="simple-cape",
            inputs={"name": "Context"},
            context=ctx,
        ))

        assert result.success is True
        # Context should be preserved
        assert ctx.trace_id == "test-trace-123"

    def test_get_metrics(self, runtime_with_cape):
        """Test getting runtime metrics."""
        # Execute a few times
        for i in range(3):
            asyncio.run(runtime_with_cape.execute(
                cape_id="simple-cape",
                inputs={"name": f"Test{i}"},
            ))

        metrics = runtime_with_cape.get_metrics()

        assert "total_executions" in metrics
        assert metrics["total_executions"] >= 3
