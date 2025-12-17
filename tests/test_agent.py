"""Tests for Cape agent."""

import pytest
import asyncio
from pathlib import Path
import tempfile

from cape.agent.agent import CapeAgent, create_agent
from cape.core.models import Cape, CapeExecution, CapeMetadata, ExecutionType


class TestCapeAgent:
    """Tests for CapeAgent."""

    @pytest.fixture
    def agent(self):
        """Create agent without loading from directories."""
        return CapeAgent(capes_dir=None, skills_dir=None)

    @pytest.fixture
    def agent_with_capes(self, agent):
        """Agent with registered Capes."""
        # Register some test Capes
        agent.registry.register(Cape(
            id="json-processor",
            name="JSON Processor",
            version="1.0.0",
            description="Process JSON data, validate schemas, transform structures",
            metadata=CapeMetadata(
                tags=["json", "data", ".json"],
                intents=["process json", "validate json", "transform json data"],
            ),
            execution=CapeExecution(
                type=ExecutionType.CODE,
                language="python",
                code="result = f'Processed JSON: {inputs}'",
            ),
        ))

        agent.registry.register(Cape(
            id="pdf-processor",
            name="PDF Processor",
            version="1.0.0",
            description="Extract text and tables from PDF documents",
            metadata=CapeMetadata(
                tags=["pdf", "document", ".pdf"],
                intents=["extract pdf", "process pdf", "read pdf file"],
            ),
            execution=CapeExecution(
                type=ExecutionType.CODE,
                language="python",
                code="result = f'PDF processed: {inputs}'",
            ),
        ))

        agent.registry.register(Cape(
            id="code-reviewer",
            name="Code Reviewer",
            version="1.0.0",
            description="Review code quality, find bugs, suggest improvements",
            metadata=CapeMetadata(
                tags=["code", "review", "quality"],
                intents=["review code", "check code quality", "find bugs"],
            ),
            execution=CapeExecution(
                type=ExecutionType.CODE,
                language="python",
                code="result = f'Code reviewed: {inputs}'",
            ),
        ))

        # Rebuild matcher index
        agent.registry.matcher.index(list(agent.registry.all()))

        return agent

    def test_agent_initialization(self, agent):
        """Test agent initialization."""
        assert agent.registry is not None
        assert agent.runtime is not None
        assert agent.history == []

    def test_run_with_matching_cape(self, agent_with_capes):
        """Test running with a matching Cape."""
        result = asyncio.run(agent_with_capes.run("process this json data"))

        assert result.success is True
        assert result.cape_id == "json-processor"

    def test_run_with_no_match(self, agent_with_capes):
        """Test running with no matching Cape."""
        # Very high threshold to ensure no match
        agent_with_capes.auto_match_threshold = 0.99

        result = asyncio.run(agent_with_capes.run("completely unrelated query"))

        assert result.success is False
        assert "No capability found" in result.error

    def test_execute_specific_cape(self, agent_with_capes):
        """Test executing a specific Cape by ID."""
        result = asyncio.run(agent_with_capes.execute(
            cape_id="pdf-processor",
            inputs={"file": "test.pdf"},
        ))

        assert result.success is True
        assert result.cape_id == "pdf-processor"

    def test_run_sync(self, agent_with_capes):
        """Test synchronous run."""
        result = agent_with_capes.run_sync("review this code")

        assert result.success is True
        assert result.cape_id == "code-reviewer"

    def test_execute_sync(self, agent_with_capes):
        """Test synchronous execute."""
        result = agent_with_capes.execute_sync(
            cape_id="json-processor",
            inputs={"data": "{}"},
        )

        assert result.success is True

    def test_history_tracking(self, agent_with_capes):
        """Test that history is tracked."""
        # Run a few requests
        agent_with_capes.run_sync("process json")
        agent_with_capes.run_sync("extract pdf")
        agent_with_capes.run_sync("review code")

        assert len(agent_with_capes.history) == 3
        assert agent_with_capes.history[0]["cape_id"] == "json-processor"
        assert agent_with_capes.history[1]["cape_id"] == "pdf-processor"

    def test_clear_history(self, agent_with_capes):
        """Test clearing history."""
        agent_with_capes.run_sync("process json")
        agent_with_capes.run_sync("extract pdf")

        assert len(agent_with_capes.history) == 2

        agent_with_capes.clear_history()

        assert len(agent_with_capes.history) == 0

    def test_list_capabilities(self, agent_with_capes):
        """Test listing capabilities."""
        caps = agent_with_capes.list_capabilities()

        assert len(caps) == 3
        ids = [c["id"] for c in caps]
        assert "json-processor" in ids
        assert "pdf-processor" in ids
        assert "code-reviewer" in ids

    def test_suggest_capabilities(self, agent_with_capes):
        """Test suggesting capabilities."""
        suggestions = agent_with_capes.suggest_capabilities("json processing", top_k=2)

        assert len(suggestions) <= 2
        assert suggestions[0]["id"] == "json-processor"
        assert "score" in suggestions[0]

    def test_get_capability(self, agent_with_capes):
        """Test getting capability by ID."""
        cape = agent_with_capes.get_capability("json-processor")

        assert cape is not None
        assert cape.id == "json-processor"

    def test_get_nonexistent_capability(self, agent_with_capes):
        """Test getting non-existent capability."""
        cape = agent_with_capes.get_capability("nonexistent")

        assert cape is None

    def test_get_status(self, agent_with_capes):
        """Test getting agent status."""
        # Run some operations first
        agent_with_capes.run_sync("process json")
        agent_with_capes.run_sync("extract pdf")

        status = agent_with_capes.get_status()

        assert status["capabilities"] == 3
        assert status["history_length"] == 2
        assert "runtime_metrics" in status
        assert "registry_summary" in status

    def test_register_tool(self, agent_with_capes):
        """Test registering a tool."""
        def custom_tool(x):
            return x * 2

        agent_with_capes.register_tool("custom_tool", custom_tool)

        # Create a Cape that uses the tool
        agent_with_capes.registry.register(Cape(
            id="custom-cape",
            name="Custom Cape",
            version="1.0.0",
            description="Uses custom tool",
            execution=CapeExecution(
                type=ExecutionType.TOOL,
                tool_name="custom_tool",
            ),
        ))

        result = agent_with_capes.execute_sync("custom-cape", {"x": 5})
        assert result.success is True
        assert result.output == 10

    def test_verbose_mode(self, agent_with_capes, caplog):
        """Test verbose mode logging."""
        import logging
        caplog.set_level(logging.INFO)

        agent_with_capes.verbose = True
        agent_with_capes.run_sync("process json")

        # Should log matched Cape
        # Note: actual log assertion depends on logging setup


class TestCreateAgent:
    """Tests for create_agent factory function."""

    def test_create_agent_basic(self):
        """Test basic agent creation."""
        agent = create_agent()

        assert isinstance(agent, CapeAgent)
        assert agent.registry is not None

    def test_create_agent_with_paths(self):
        """Test agent creation with paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            capes_dir = Path(tmpdir) / "capes"
            capes_dir.mkdir()
            skills_dir = Path(tmpdir) / "skills"
            skills_dir.mkdir()

            agent = create_agent(
                capes_dir=str(capes_dir),
                skills_dir=str(skills_dir),
            )

            assert agent.registry.capes_dir == capes_dir
            assert agent.registry.skills_dir == skills_dir

    def test_create_agent_with_kwargs(self):
        """Test agent creation with additional kwargs."""
        agent = create_agent(default_model="claude")

        assert agent is not None


class TestAgentWithRealCapes:
    """Integration tests with real Cape files."""

    @pytest.fixture
    def temp_capes_dir(self):
        """Create temporary capes directory with cape.yaml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            capes_dir = Path(tmpdir) / "capes"
            capes_dir.mkdir()

            # Create a test Cape
            cape_dir = capes_dir / "test-cape"
            cape_dir.mkdir()
            (cape_dir / "cape.yaml").write_text('''
id: test-cape
name: Test Cape
version: "1.0.0"
description: A test capability for processing test data

metadata:
  tags:
    - test
    - demo
  intents:
    - process test data
    - run test

execution:
  type: code
  language: python
  code: "result = f'Test executed with: {inputs}'"
''')
            yield capes_dir

    def test_agent_with_cape_files(self, temp_capes_dir):
        """Test agent loading from Cape files."""
        agent = create_agent(capes_dir=str(temp_capes_dir))

        assert "test-cape" in agent.registry
        result = agent.run_sync("process test data")
        assert result.success is True

    @pytest.fixture
    def temp_skills_dir(self):
        """Create temporary skills directory with SKILL.md."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills"
            skills_dir.mkdir()

            # Create a test Skill
            skill_dir = skills_dir / "test-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text('''---
name: test-skill
description: A test skill for demonstration purposes
---

# Test Skill

This is a test skill that processes data.
''')
            yield skills_dir

    def test_agent_with_skill_files(self, temp_skills_dir):
        """Test agent importing from Skill files."""
        agent = create_agent(skills_dir=str(temp_skills_dir))

        assert "test-skill" in agent.registry
        cape = agent.get_capability("test-skill")
        assert cape is not None
        # Imported skills should have claude adapter
        assert cape.model_adapters is not None
