"""
Tests for Cape Sandbox Module.

Tests ProcessSandbox and InProcessSandbox implementations.
"""

import asyncio
import pytest
from pathlib import Path

from cape.runtime.sandbox import (
    SandboxManager,
    SandboxConfig,
    SandboxType,
    ExecutionRequest,
    ProcessSandbox,
    InProcessSandbox,
)


# ============================================================
# ProcessSandbox Tests
# ============================================================

class TestProcessSandbox:
    """Tests for ProcessSandbox."""

    @pytest.fixture
    async def sandbox(self):
        """Create a ProcessSandbox for testing."""
        config = SandboxConfig(
            type=SandboxType.PROCESS,
            timeout_seconds=10,
        )
        sandbox = ProcessSandbox(config)
        await sandbox.setup()
        yield sandbox
        await sandbox.cleanup()

    @pytest.mark.asyncio
    async def test_simple_code_execution(self, sandbox):
        """Test basic code execution."""
        response = await sandbox.execute(ExecutionRequest(
            code="result = 1 + 1"
        ))

        assert response.success
        assert response.output == 2
        assert response.exit_code == 0

    @pytest.mark.asyncio
    async def test_code_with_args(self, sandbox):
        """Test code execution with arguments."""
        response = await sandbox.execute(ExecutionRequest(
            code="result = args['a'] + args['b']",
            args={"a": 10, "b": 20},
        ))

        assert response.success
        assert response.output == 30

    @pytest.mark.asyncio
    async def test_code_with_imports(self, sandbox):
        """Test code with standard library imports."""
        response = await sandbox.execute(ExecutionRequest(
            code="""
import json
data = {"name": "test", "value": 42}
result = json.dumps(data)
"""
        ))

        assert response.success
        assert "test" in response.output
        assert "42" in response.output

    @pytest.mark.asyncio
    async def test_code_error_handling(self, sandbox):
        """Test error handling in code execution."""
        response = await sandbox.execute(ExecutionRequest(
            code="result = 1 / 0"  # ZeroDivisionError
        ))

        assert not response.success
        assert response.exit_code != 0
        assert "ZeroDivisionError" in response.stderr or "division" in str(response.error).lower()

    @pytest.mark.asyncio
    async def test_file_output(self, sandbox):
        """Test file creation during execution."""
        response = await sandbox.execute(ExecutionRequest(
            code="""
from pathlib import Path
Path("output.txt").write_text("Hello, World!")
result = "File created"
"""
        ))

        assert response.success
        assert "output.txt" in response.files_created
        assert response.files_created["output.txt"] == b"Hello, World!"

    @pytest.mark.asyncio
    async def test_file_input(self, sandbox):
        """Test file input handling."""
        response = await sandbox.execute(ExecutionRequest(
            code="""
from pathlib import Path
content = Path("input.txt").read_text()
result = len(content)
""",
            files={"input.txt": b"Hello, World!"},
        ))

        assert response.success
        assert response.output == 13

    @pytest.mark.asyncio
    async def test_timeout(self, sandbox):
        """Test timeout handling."""
        # Create sandbox with short timeout
        config = SandboxConfig(type=SandboxType.PROCESS, timeout_seconds=1)
        short_sandbox = ProcessSandbox(config)
        await short_sandbox.setup()

        try:
            response = await short_sandbox.execute(ExecutionRequest(
                code="""
import time
time.sleep(10)
result = "Should not reach here"
"""
            ))

            assert not response.success
            assert "timeout" in response.error.lower()
        finally:
            await short_sandbox.cleanup()

    @pytest.mark.asyncio
    async def test_stdout_capture(self, sandbox):
        """Test stdout capture."""
        response = await sandbox.execute(ExecutionRequest(
            code="""
print("Hello from stdout")
result = "Done"
"""
        ))

        assert response.success
        assert "Hello from stdout" in response.stdout

    @pytest.mark.asyncio
    async def test_stderr_capture(self, sandbox):
        """Test stderr capture."""
        response = await sandbox.execute(ExecutionRequest(
            code="""
import sys
print("Error message", file=sys.stderr)
result = "Done"
"""
        ))

        assert response.success
        assert "Error message" in response.stderr


# ============================================================
# InProcessSandbox Tests
# ============================================================

class TestInProcessSandbox:
    """Tests for InProcessSandbox."""

    @pytest.fixture
    async def sandbox(self):
        """Create an InProcessSandbox for testing."""
        config = SandboxConfig(type=SandboxType.INPROCESS)
        sandbox = InProcessSandbox(config)
        await sandbox.setup()
        yield sandbox
        await sandbox.cleanup()

    @pytest.mark.asyncio
    async def test_simple_execution(self, sandbox):
        """Test basic code execution."""
        response = await sandbox.execute(ExecutionRequest(
            code="result = 2 * 3"
        ))

        assert response.success
        assert response.output == 6

    @pytest.mark.asyncio
    async def test_with_args(self, sandbox):
        """Test code with arguments."""
        response = await sandbox.execute(ExecutionRequest(
            code="result = args['x'] ** 2",
            args={"x": 5},
        ))

        assert response.success
        assert response.output == 25

    @pytest.mark.asyncio
    async def test_error_handling(self, sandbox):
        """Test error handling."""
        response = await sandbox.execute(ExecutionRequest(
            code="result = undefined_variable"
        ))

        assert not response.success
        assert response.error is not None


# ============================================================
# SandboxManager Tests
# ============================================================

class TestSandboxManager:
    """Tests for SandboxManager."""

    @pytest.mark.asyncio
    async def test_create_process_sandbox(self):
        """Test creating ProcessSandbox via manager."""
        manager = SandboxManager(SandboxConfig(type=SandboxType.PROCESS))

        sandbox = await manager.get_sandbox("test-1")

        assert sandbox is not None
        assert isinstance(sandbox, ProcessSandbox)
        assert manager.get_sandbox_count() == 1

        await manager.release_all()
        assert manager.get_sandbox_count() == 0

    @pytest.mark.asyncio
    async def test_create_inprocess_sandbox(self):
        """Test creating InProcessSandbox via manager."""
        manager = SandboxManager(SandboxConfig(type=SandboxType.INPROCESS))

        sandbox = await manager.get_sandbox("test-1")

        assert sandbox is not None
        assert isinstance(sandbox, InProcessSandbox)

        await manager.release_all()

    @pytest.mark.asyncio
    async def test_sandbox_reuse(self):
        """Test that same sandbox ID returns same instance."""
        manager = SandboxManager()

        sandbox1 = await manager.get_sandbox("test-1")
        sandbox2 = await manager.get_sandbox("test-1")

        assert sandbox1 is sandbox2
        assert manager.get_sandbox_count() == 1

        await manager.release_all()

    @pytest.mark.asyncio
    async def test_multiple_sandboxes(self):
        """Test managing multiple sandboxes."""
        manager = SandboxManager()

        sandbox1 = await manager.get_sandbox("test-1")
        sandbox2 = await manager.get_sandbox("test-2")

        assert sandbox1 is not sandbox2
        assert manager.get_sandbox_count() == 2
        assert set(manager.list_sandboxes()) == {"test-1", "test-2"}

        await manager.release_sandbox("test-1")
        assert manager.get_sandbox_count() == 1

        await manager.release_all()


# ============================================================
# Integration Tests
# ============================================================

class TestSandboxIntegration:
    """Integration tests for sandbox functionality."""

    @pytest.mark.asyncio
    async def test_data_processing_workflow(self):
        """Test a realistic data processing workflow."""
        manager = SandboxManager(SandboxConfig(type=SandboxType.PROCESS))
        sandbox = await manager.get_sandbox("data-proc")

        try:
            # Step 1: Create data
            response = await sandbox.execute(ExecutionRequest(
                code="""
import json
data = [{"name": "Alice", "score": 85}, {"name": "Bob", "score": 92}]
with open("data.json", "w") as f:
    json.dump(data, f)
result = "Data created"
"""
            ))
            assert response.success

            # Step 2: Process data (new execution in same sandbox context)
            response2 = await sandbox.execute(ExecutionRequest(
                code="""
import json
with open("data.json") as f:
    data = json.load(f)
avg_score = sum(d["score"] for d in data) / len(data)
result = {"average_score": avg_score, "count": len(data)}
""",
                files={"data.json": response.files_created.get("data.json", b"[]")},
            ))

            assert response2.success
            assert response2.output["average_score"] == 88.5
            assert response2.output["count"] == 2

        finally:
            await manager.release_all()

    @pytest.mark.asyncio
    async def test_script_with_function(self):
        """Test executing a script with function calls."""
        manager = SandboxManager(SandboxConfig(type=SandboxType.PROCESS))
        sandbox = await manager.get_sandbox("func-test")

        try:
            response = await sandbox.execute(ExecutionRequest(
                code="""
def calculate_sum(numbers):
    return sum(numbers)

def calculate_average(numbers):
    if not numbers:
        return 0
    return calculate_sum(numbers) / len(numbers)

numbers = args.get("numbers", [])
result = {
    "sum": calculate_sum(numbers),
    "average": calculate_average(numbers),
    "count": len(numbers),
}
""",
                args={"numbers": [10, 20, 30, 40, 50]},
            ))

            assert response.success
            assert response.output["sum"] == 150
            assert response.output["average"] == 30.0
            assert response.output["count"] == 5

        finally:
            await manager.release_all()


# ============================================================
# Run tests
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
