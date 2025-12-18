#!/usr/bin/env python3
"""
Quick test script for sandbox module.
Run directly without pytest.
"""

import asyncio
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from cape.runtime.sandbox import (
    SandboxManager,
    SandboxConfig,
    SandboxType,
    ExecutionRequest,
    ProcessSandbox,
    InProcessSandbox,
)


async def test_inprocess_sandbox():
    """Test InProcessSandbox."""
    print("\n=== Testing InProcessSandbox ===")

    config = SandboxConfig(type=SandboxType.INPROCESS)
    sandbox = InProcessSandbox(config)
    await sandbox.setup()

    try:
        # Test 1: Simple execution
        print("  Test 1: Simple execution...", end=" ")
        response = await sandbox.execute(ExecutionRequest(
            code="result = 1 + 1"
        ))
        assert response.success, f"Failed: {response.error}"
        assert response.output == 2, f"Expected 2, got {response.output}"
        print("✓")

        # Test 2: With arguments
        print("  Test 2: With arguments...", end=" ")
        response = await sandbox.execute(ExecutionRequest(
            code="result = args['x'] * args['y']",
            args={"x": 3, "y": 4},
        ))
        assert response.success, f"Failed: {response.error}"
        assert response.output == 12, f"Expected 12, got {response.output}"
        print("✓")

        # Test 3: Error handling
        print("  Test 3: Error handling...", end=" ")
        response = await sandbox.execute(ExecutionRequest(
            code="result = 1 / 0"
        ))
        assert not response.success, "Should have failed"
        assert response.error is not None
        print("✓")

        print("  InProcessSandbox: All tests passed!")

    finally:
        await sandbox.cleanup()


async def test_process_sandbox():
    """Test ProcessSandbox."""
    print("\n=== Testing ProcessSandbox ===")

    config = SandboxConfig(
        type=SandboxType.PROCESS,
        timeout_seconds=10,
    )
    sandbox = ProcessSandbox(config)
    await sandbox.setup()

    try:
        # Test 1: Simple execution
        print("  Test 1: Simple execution...", end=" ")
        response = await sandbox.execute(ExecutionRequest(
            code="result = 2 + 2"
        ))
        assert response.success, f"Failed: {response.error}\nstderr: {response.stderr}"
        assert response.output == 4, f"Expected 4, got {response.output}"
        print("✓")

        # Test 2: With arguments
        print("  Test 2: With arguments...", end=" ")
        response = await sandbox.execute(ExecutionRequest(
            code="result = args['a'] + args['b']",
            args={"a": 10, "b": 20},
        ))
        assert response.success, f"Failed: {response.error}\nstderr: {response.stderr}"
        assert response.output == 30, f"Expected 30, got {response.output}"
        print("✓")

        # Test 3: With imports
        print("  Test 3: With imports...", end=" ")
        response = await sandbox.execute(ExecutionRequest(
            code="""
import json
data = {"key": "value"}
result = json.dumps(data)
"""
        ))
        assert response.success, f"Failed: {response.error}\nstderr: {response.stderr}"
        assert "key" in response.output, f"Expected JSON string, got {response.output}"
        print("✓")

        # Test 4: File creation
        print("  Test 4: File creation...", end=" ")
        response = await sandbox.execute(ExecutionRequest(
            code="""
from pathlib import Path
Path("test.txt").write_text("Hello!")
result = "done"
"""
        ))
        assert response.success, f"Failed: {response.error}"
        assert "test.txt" in response.files_created, f"File not created: {response.files_created.keys()}"
        assert response.files_created["test.txt"] == b"Hello!"
        print("✓")

        # Test 5: File input
        print("  Test 5: File input...", end=" ")
        response = await sandbox.execute(ExecutionRequest(
            code="""
from pathlib import Path
content = Path("input.txt").read_text()
result = len(content)
""",
            files={"input.txt": b"Hello World"},
        ))
        assert response.success, f"Failed: {response.error}"
        assert response.output == 11, f"Expected 11, got {response.output}"
        print("✓")

        # Test 6: Stdout capture
        print("  Test 6: Stdout capture...", end=" ")
        response = await sandbox.execute(ExecutionRequest(
            code="""
print("Hello from subprocess!")
result = "done"
"""
        ))
        assert response.success, f"Failed: {response.error}"
        assert "Hello from subprocess!" in response.stdout
        print("✓")

        # Test 7: Error handling
        print("  Test 7: Error handling...", end=" ")
        response = await sandbox.execute(ExecutionRequest(
            code="result = undefined_variable"
        ))
        assert not response.success, "Should have failed"
        print("✓")

        print("  ProcessSandbox: All tests passed!")

    finally:
        await sandbox.cleanup()


async def test_sandbox_manager():
    """Test SandboxManager."""
    print("\n=== Testing SandboxManager ===")

    manager = SandboxManager(SandboxConfig(type=SandboxType.PROCESS))

    try:
        # Test 1: Create sandbox
        print("  Test 1: Create sandbox...", end=" ")
        sandbox = await manager.get_sandbox("test-1")
        assert sandbox is not None
        assert manager.get_sandbox_count() == 1
        print("✓")

        # Test 2: Reuse sandbox
        print("  Test 2: Reuse sandbox...", end=" ")
        sandbox2 = await manager.get_sandbox("test-1")
        assert sandbox is sandbox2
        assert manager.get_sandbox_count() == 1
        print("✓")

        # Test 3: Multiple sandboxes
        print("  Test 3: Multiple sandboxes...", end=" ")
        sandbox3 = await manager.get_sandbox("test-2")
        assert sandbox3 is not sandbox
        assert manager.get_sandbox_count() == 2
        print("✓")

        # Test 4: Execute in managed sandbox
        print("  Test 4: Execute in sandbox...", end=" ")
        response = await sandbox.execute(ExecutionRequest(
            code="result = 'Hello from managed sandbox'"
        ))
        assert response.success
        assert "managed sandbox" in response.output
        print("✓")

        print("  SandboxManager: All tests passed!")

    finally:
        await manager.release_all()
        assert manager.get_sandbox_count() == 0


async def test_timeout():
    """Test timeout handling."""
    print("\n=== Testing Timeout ===")

    config = SandboxConfig(
        type=SandboxType.PROCESS,
        timeout_seconds=2,
    )
    sandbox = ProcessSandbox(config)
    await sandbox.setup()

    try:
        print("  Test: Timeout handling (may take 2s)...", end=" ")
        response = await sandbox.execute(ExecutionRequest(
            code="""
import time
time.sleep(10)
result = "Should not reach"
"""
        ))
        assert not response.success, "Should have timed out"
        assert "timeout" in response.error.lower()
        print("✓")

        print("  Timeout: Test passed!")

    finally:
        await sandbox.cleanup()


async def main():
    """Run all tests."""
    print("=" * 50)
    print("Cape Sandbox Module Tests")
    print("=" * 50)

    try:
        await test_inprocess_sandbox()
        await test_process_sandbox()
        await test_sandbox_manager()
        await test_timeout()

        print("\n" + "=" * 50)
        print("ALL TESTS PASSED!")
        print("=" * 50)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
