"""Tests for Cape core models."""

import pytest
from pathlib import Path

from cape.core.models import (
    Cape,
    CapeMetadata,
    CapeInterface,
    CapeExecution,
    CapeOrchestration,
    CapeSafety,
    CapeResult,
    InputSchema,
    OutputSchema,
    StepDefinition,
    ExecutionType,
    RiskLevel,
    SourceType,
)


class TestCapeMetadata:
    """Tests for CapeMetadata model."""

    def test_basic_metadata(self):
        """Test basic metadata creation."""
        metadata = CapeMetadata(
            author="test",
            license="MIT",
            source=SourceType.NATIVE,
            tags=["json", "data"],
            intents=["process json"],
        )
        assert metadata.author == "test"
        assert metadata.license == "MIT"
        assert metadata.source == SourceType.NATIVE
        assert "json" in metadata.tags
        assert "process json" in metadata.intents

    def test_default_values(self):
        """Test default metadata values."""
        metadata = CapeMetadata()
        assert metadata.source == SourceType.NATIVE
        assert metadata.tags == []
        assert metadata.intents == []

    def test_source_type_skill(self):
        """Test SKILL source type."""
        metadata = CapeMetadata(source=SourceType.SKILL)
        assert metadata.source == SourceType.SKILL


class TestCapeInterface:
    """Tests for CapeInterface model."""

    def test_interface_with_inputs_outputs(self):
        """Test interface with inputs and outputs."""
        interface = CapeInterface(
            inputs=[
                InputSchema(name="data", type="string", required=True),
                InputSchema(name="format", type="string", default="json"),
            ],
            outputs=[
                OutputSchema(name="result", type="object"),
            ],
        )
        assert len(interface.inputs) == 2
        assert len(interface.outputs) == 1
        assert interface.inputs[0].required is True
        assert interface.inputs[1].default == "json"

    def test_empty_interface(self):
        """Test empty interface."""
        interface = CapeInterface()
        assert interface.inputs == []
        assert interface.outputs == []


class TestCapeExecution:
    """Tests for CapeExecution model."""

    def test_tool_execution(self):
        """Test tool execution config."""
        execution = CapeExecution(
            type=ExecutionType.TOOL,
            tool_name="json_processor",
            tool_config={"max_size": 10},
        )
        assert execution.type == ExecutionType.TOOL
        assert execution.tool_name == "json_processor"
        assert execution.tool_config["max_size"] == 10

    def test_workflow_execution(self):
        """Test workflow execution config."""
        steps = [
            StepDefinition(
                id="step1",
                name="Parse",
                type="tool",
                tool_name="parser",
            ),
            StepDefinition(
                id="step2",
                name="Transform",
                type="code",
                depends_on=["step1"],
            ),
        ]
        execution = CapeExecution(
            type=ExecutionType.WORKFLOW,
            steps=steps,
        )
        assert execution.type == ExecutionType.WORKFLOW
        assert len(execution.steps) == 2
        assert execution.steps[1].depends_on == ["step1"]

    def test_llm_execution(self):
        """Test LLM execution config."""
        execution = CapeExecution(
            type=ExecutionType.LLM,
            model="gpt-4",
            prompt_template="Process: {{input}}",
        )
        assert execution.type == ExecutionType.LLM
        assert execution.model == "gpt-4"


class TestCapeSafety:
    """Tests for CapeSafety model."""

    def test_safety_config(self):
        """Test safety configuration."""
        safety = CapeSafety(
            risk_level=RiskLevel.MEDIUM,
            sandboxed=True,
            allowed_operations=["read", "write"],
            max_input_size=1024,
            max_output_size=2048,
        )
        assert safety.risk_level == RiskLevel.MEDIUM
        assert safety.sandboxed is True
        assert "read" in safety.allowed_operations
        assert safety.max_input_size == 1024

    def test_default_safety(self):
        """Test default safety values."""
        safety = CapeSafety()
        assert safety.risk_level == RiskLevel.LOW
        assert safety.sandboxed is True


class TestCape:
    """Tests for Cape model."""

    def test_cape_creation(self):
        """Test Cape creation with all fields."""
        cape = Cape(
            id="test-cape",
            name="Test Cape",
            version="1.0.0",
            description="A test cape",
            metadata=CapeMetadata(
                author="test",
                tags=["test"],
            ),
            execution=CapeExecution(
                type=ExecutionType.TOOL,
            ),
        )
        assert cape.id == "test-cape"
        assert cape.name == "Test Cape"
        assert cape.metadata.author == "test"
        assert cape.execution.type == ExecutionType.TOOL

    def test_cape_from_dict(self):
        """Test Cape creation from dictionary."""
        data = {
            "id": "json-processor",
            "name": "JSON Processor",
            "version": "1.0.0",
            "description": "Process JSON data",
            "metadata": {
                "author": "test",
                "tags": ["json", "data"],
                "intents": ["process json"],
            },
            "execution": {
                "type": "tool",
            },
        }
        cape = Cape.from_dict(data)
        assert cape.id == "json-processor"
        assert cape.metadata.author == "test"
        assert cape.execution.type == ExecutionType.TOOL

    def test_cape_to_dict(self):
        """Test Cape serialization to dictionary."""
        cape = Cape(
            id="test-cape",
            name="Test Cape",
            version="1.0.0",
            description="Test",
            execution=CapeExecution(type=ExecutionType.LLM),
        )
        data = cape.to_dict()
        assert data["id"] == "test-cape"
        assert data["execution"]["type"] == "llm"

    def test_cape_to_yaml(self):
        """Test Cape serialization to YAML."""
        cape = Cape(
            id="test-cape",
            name="Test Cape",
            version="1.0.0",
            description="Test",
            execution=CapeExecution(type=ExecutionType.TOOL),
        )
        yaml_str = cape.to_yaml()
        assert "id: test-cape" in yaml_str
        assert "name: Test Cape" in yaml_str


class TestCapeResult:
    """Tests for CapeResult model."""

    def test_success_result(self):
        """Test successful result."""
        result = CapeResult(
            cape_id="test-cape",
            success=True,
            output={"data": "processed"},
            execution_time=1.5,
        )
        assert result.success is True
        assert result.output["data"] == "processed"
        assert result.error is None

    def test_error_result(self):
        """Test error result."""
        result = CapeResult(
            cape_id="test-cape",
            success=False,
            error="Processing failed",
        )
        assert result.success is False
        assert result.error == "Processing failed"
        assert result.output is None

    def test_result_with_metadata(self):
        """Test result with metadata."""
        result = CapeResult(
            cape_id="test-cape",
            success=True,
            output="result",
            metadata={
                "tokens_used": 100,
                "model": "gpt-4",
            },
        )
        assert result.metadata["tokens_used"] == 100


class TestStepDefinition:
    """Tests for StepDefinition model."""

    def test_tool_step(self):
        """Test tool step definition."""
        step = StepDefinition(
            id="parse",
            name="Parse Data",
            type="tool",
            tool_name="parser",
            inputs={"data": "{{inputs.data}}"},
        )
        assert step.id == "parse"
        assert step.type == "tool"
        assert step.tool_name == "parser"

    def test_code_step(self):
        """Test code step definition."""
        step = StepDefinition(
            id="transform",
            name="Transform",
            type="code",
            language="python",
            code="def transform(data): return data",
        )
        assert step.type == "code"
        assert step.language == "python"

    def test_step_with_dependencies(self):
        """Test step with dependencies."""
        step = StepDefinition(
            id="step2",
            name="Step 2",
            type="llm",
            depends_on=["step1"],
            condition="{{steps.step1.success}}",
        )
        assert step.depends_on == ["step1"]
        assert "step1.success" in step.condition
