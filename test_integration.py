#!/usr/bin/env python3
"""
Integration test for Cape code execution layer.

Tests the complete workflow:
1. EnhancedSkillImporter imports a skill with scripts
2. EnhancedCodeExecutor executes the skill code
"""

import asyncio
import sys
import tempfile
import shutil
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from cape.importers import import_skill_enhanced
from cape.runtime.sandbox import (
    EnhancedCodeExecutor,
    SandboxType,
    ExecutionRequest,
)


def create_test_skill(base_dir: Path) -> Path:
    """Create a test skill with scripts for integration testing."""
    skill_dir = base_dir / "test-calculator"
    skill_dir.mkdir(parents=True)

    # Create SKILL.md
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text("""---
name: test-calculator
description: A test calculator skill for integration testing
version: 1.0.0
tags:
  - test
  - calculator
---

# Test Calculator

A simple calculator skill for testing the code execution layer.

## Usage

Provide numbers and an operation to calculate the result.

## Guidelines

- Supports add, subtract, multiply, divide operations
- Returns result in JSON format
""")

    # Create scripts directory
    scripts_dir = skill_dir / "scripts"
    scripts_dir.mkdir()

    # Create main.py
    main_script = scripts_dir / "main.py"
    main_script.write_text("""#!/usr/bin/env python3
\"\"\"Test calculator main script.\"\"\"

import json
from pathlib import Path

def calculate(a: float, b: float, operation: str) -> float:
    \"\"\"Perform calculation.\"\"\"
    operations = {
        "add": lambda x, y: x + y,
        "subtract": lambda x, y: x - y,
        "multiply": lambda x, y: x * y,
        "divide": lambda x, y: x / y if y != 0 else float('inf'),
    }

    if operation not in operations:
        raise ValueError(f"Unknown operation: {operation}")

    return operations[operation](a, b)


def main():
    \"\"\"Main entry point.\"\"\"
    # Get args from execution context
    a = args.get("a", 0)
    b = args.get("b", 0)
    operation = args.get("operation", "add")

    result = calculate(a, b, operation)

    # Write output file
    output = {
        "a": a,
        "b": b,
        "operation": operation,
        "result": result,
    }

    Path("output.json").write_text(json.dumps(output, indent=2))

    return output


# Execute and set result
result = main()
""")

    # Create helper module
    helper_script = scripts_dir / "helpers.py"
    helper_script.write_text("""#!/usr/bin/env python3
\"\"\"Helper utilities for test calculator.\"\"\"

def format_number(n: float, decimals: int = 2) -> str:
    \"\"\"Format number with specified decimal places.\"\"\"
    return f"{n:.{decimals}f}"


def validate_input(value, expected_type):
    \"\"\"Validate input type.\"\"\"
    if not isinstance(value, expected_type):
        raise TypeError(f"Expected {expected_type}, got {type(value)}")
    return value
""")

    return skill_dir


async def test_skill_import():
    """Test EnhancedSkillImporter."""
    print("\n=== Testing EnhancedSkillImporter ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = create_test_skill(Path(tmpdir))

        # Import skill
        print("  Test 1: Import skill with scripts...", end=" ")
        cape = import_skill_enhanced(skill_dir)

        assert cape is not None, "Import returned None"
        assert cape.id == "test-calculator", f"Wrong ID: {cape.id}"
        assert cape.description, "Missing description"
        print("✓")

        # Check execution config
        print("  Test 2: Check execution configuration...", end=" ")
        assert cape.execution is not None, "No execution config"
        assert cape.execution.entrypoint == "scripts/main.py", f"Wrong entrypoint: {cape.execution.entrypoint}"
        print("✓")

        # Check code adapter
        print("  Test 3: Check code adapter...", end=" ")
        assert "code" in cape.model_adapters, "No code adapter"
        code_adapter = cape.model_adapters["code"]
        assert "scripts/main.py" in code_adapter["scripts"], "main.py not in scripts"
        assert "scripts/helpers.py" in code_adapter["scripts"], "helpers.py not in scripts"
        assert code_adapter["runtime"] == "python", "Wrong runtime"
        print("✓")

        # Check model adapters
        print("  Test 4: Check model adapters...", end=" ")
        assert "claude" in cape.model_adapters, "No claude adapter"
        assert "openai" in cape.model_adapters, "No openai adapter"
        assert "generic" in cape.model_adapters, "No generic adapter"
        print("✓")

        print("  EnhancedSkillImporter: All tests passed!")
        return cape, skill_dir


async def test_code_executor():
    """Test EnhancedCodeExecutor with imported skill."""
    print("\n=== Testing Direct Sandbox Execution ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = create_test_skill(Path(tmpdir))
        cape = import_skill_enhanced(skill_dir)

        # Create sandbox directly for testing
        from cape.runtime.sandbox import ProcessSandbox, SandboxConfig

        print("  Test 1: Create ProcessSandbox...", end=" ")
        config = SandboxConfig(type=SandboxType.PROCESS, timeout_seconds=30)
        sandbox = ProcessSandbox(config)
        await sandbox.setup()
        print("✓")

        try:
            # Read the main script
            main_script = skill_dir / "scripts" / "main.py"
            code = main_script.read_text()

            # Execute with arguments
            print("  Test 2: Execute calculation (add)...", end=" ")
            response = await sandbox.execute(ExecutionRequest(
                code=code,
                args={"a": 10, "b": 5, "operation": "add"},
            ))

            assert response.success, f"Execution failed: {response.error}\nstderr: {response.stderr}"
            assert response.output["result"] == 15, f"Wrong result: {response.output}"
            print("✓")

            # Test multiply
            print("  Test 3: Execute calculation (multiply)...", end=" ")
            response = await sandbox.execute(ExecutionRequest(
                code=code,
                args={"a": 7, "b": 8, "operation": "multiply"},
            ))

            assert response.success, f"Execution failed: {response.error}"
            assert response.output["result"] == 56, f"Wrong result: {response.output}"
            print("✓")

            # Test divide
            print("  Test 4: Execute calculation (divide)...", end=" ")
            response = await sandbox.execute(ExecutionRequest(
                code=code,
                args={"a": 100, "b": 4, "operation": "divide"},
            ))

            assert response.success, f"Execution failed: {response.error}"
            assert response.output["result"] == 25, f"Wrong result: {response.output}"
            print("✓")

            # Check file output
            print("  Test 5: Check file output...", end=" ")
            assert "output.json" in response.files_created, "output.json not created"
            import json
            output_data = json.loads(response.files_created["output.json"])
            assert output_data["result"] == 25, f"Wrong file output: {output_data}"
            print("✓")

            print("  Direct Sandbox Execution: All tests passed!")

        finally:
            await sandbox.cleanup()


async def test_error_handling():
    """Test error handling in code execution."""
    print("\n=== Testing Error Handling ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        skill_dir = create_test_skill(Path(tmpdir))

        from cape.runtime.sandbox import ProcessSandbox, SandboxConfig
        config = SandboxConfig(type=SandboxType.PROCESS, timeout_seconds=30)
        sandbox = ProcessSandbox(config)
        await sandbox.setup()

        try:
            # Test invalid operation
            print("  Test 1: Invalid operation handling...", end=" ")

            main_script = skill_dir / "scripts" / "main.py"
            code = main_script.read_text()

            response = await sandbox.execute(ExecutionRequest(
                code=code,
                args={"a": 10, "b": 5, "operation": "invalid_op"},
            ))

            # Should fail with ValueError
            assert not response.success, "Should have failed with invalid operation"
            assert "ValueError" in response.stderr or "Unknown operation" in str(response.error)
            print("✓")

            # Test division by zero
            print("  Test 2: Division by zero...", end=" ")
            response = await sandbox.execute(ExecutionRequest(
                code=code,
                args={"a": 10, "b": 0, "operation": "divide"},
            ))

            # Should succeed but return infinity
            assert response.success, f"Failed: {response.error}"
            assert response.output["result"] == float('inf'), f"Expected inf, got {response.output}"
            print("✓")

            print("  Error Handling: All tests passed!")

        finally:
            await sandbox.cleanup()


async def test_full_workflow():
    """Test complete import-to-execution workflow."""
    print("\n=== Testing Full Workflow ===")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Step 1: Create skill
        print("  Step 1: Create test skill...", end=" ")
        skill_dir = create_test_skill(Path(tmpdir))
        print("✓")

        # Step 2: Import skill
        print("  Step 2: Import with EnhancedSkillImporter...", end=" ")
        cape = import_skill_enhanced(skill_dir)
        print("✓")

        # Step 3: Create sandbox from cape config
        print("  Step 3: Create sandbox from cape config...", end=" ")
        from cape.runtime.sandbox import ProcessSandbox, SandboxConfig
        config = SandboxConfig(
            type=SandboxType.PROCESS,
            timeout_seconds=cape.execution.timeout_seconds,
        )
        sandbox = ProcessSandbox(config)
        await sandbox.setup()
        print("✓")

        try:
            # Step 4: Load and execute main script
            print("  Step 4: Execute cape script...", end=" ")

            main_script_path = skill_dir / cape.execution.entrypoint
            code = main_script_path.read_text()

            response = await sandbox.execute(ExecutionRequest(
                code=code,
                args={"a": 100, "b": 25, "operation": "subtract"},
            ))

            assert response.success, f"Execution failed: {response.error}"
            assert response.output["result"] == 75, f"Wrong result: {response.output}"
            print("✓")

            # Step 5: Verify output
            print("  Step 5: Verify output structure...", end=" ")
            assert "a" in response.output
            assert "b" in response.output
            assert "operation" in response.output
            assert "result" in response.output
            print("✓")

            print("  Full Workflow: All tests passed!")

        finally:
            await sandbox.cleanup()


async def main():
    """Run all integration tests."""
    print("=" * 50)
    print("Cape Code Execution Layer - Integration Tests")
    print("=" * 50)

    try:
        await test_skill_import()
        await test_code_executor()
        await test_error_handling()
        await test_full_workflow()

        print("\n" + "=" * 50)
        print("ALL INTEGRATION TESTS PASSED!")
        print("=" * 50)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
