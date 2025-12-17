"""Tests for Cape registry and matcher."""

import pytest
from pathlib import Path
import tempfile

from cape.registry.registry import CapeRegistry
from cape.registry.matcher import CapeMatcher
from cape.core.models import Cape, CapeExecution, CapeMetadata, ExecutionType, SourceType


class TestCapeMatcher:
    """Tests for CapeMatcher."""

    @pytest.fixture
    def matcher(self):
        """Create matcher without embeddings for faster tests."""
        return CapeMatcher(use_embeddings=False)

    @pytest.fixture
    def sample_capes(self):
        """Create sample Capes for testing."""
        return [
            Cape(
                id="json-processor",
                name="JSON Processor",
                version="1.0.0",
                description="Process and transform JSON data, validate schemas",
                metadata=CapeMetadata(
                    tags=["json", "data", ".json"],
                    intents=["process json", "validate json schema", "transform json"],
                ),
                execution=CapeExecution(type=ExecutionType.TOOL),
            ),
            Cape(
                id="pdf-processor",
                name="PDF Processor",
                version="1.0.0",
                description="Extract text and tables from PDF documents",
                metadata=CapeMetadata(
                    tags=["pdf", "document", ".pdf"],
                    intents=["extract pdf text", "process pdf", "read pdf"],
                ),
                execution=CapeExecution(type=ExecutionType.TOOL),
            ),
            Cape(
                id="code-analyzer",
                name="Code Analyzer",
                version="1.0.0",
                description="Analyze code quality and find bugs",
                metadata=CapeMetadata(
                    tags=["code", "analysis", "quality"],
                    intents=["review code", "analyze code", "find bugs"],
                ),
                execution=CapeExecution(type=ExecutionType.HYBRID),
            ),
        ]

    def test_exact_id_match(self, matcher, sample_capes):
        """Test exact ID matching."""
        results = matcher.match("use json-processor", sample_capes)

        assert len(results) > 0
        assert results[0]["cape"].id == "json-processor"
        assert results[0]["match_type"] == "exact"
        assert results[0]["score"] == 1.0

    def test_intent_match(self, matcher, sample_capes):
        """Test intent-based matching."""
        results = matcher.match("I need to process json data", sample_capes)

        assert len(results) > 0
        # JSON processor should be top match
        assert results[0]["cape"].id == "json-processor"

    def test_keyword_match(self, matcher, sample_capes):
        """Test keyword-based matching."""
        results = matcher.match("I have a .pdf file to read", sample_capes)

        assert len(results) > 0
        # PDF processor should match
        pdf_match = next((r for r in results if r["cape"].id == "pdf-processor"), None)
        assert pdf_match is not None

    def test_threshold_filtering(self, matcher, sample_capes):
        """Test threshold filtering."""
        # Very high threshold should filter out weak matches
        results = matcher.match("random unrelated query", sample_capes, threshold=0.9)
        # Might be empty or very few results
        assert all(r["score"] >= 0.9 for r in results)

    def test_top_k_limit(self, matcher, sample_capes):
        """Test top_k result limiting."""
        results = matcher.match("process data", sample_capes, top_k=2)
        assert len(results) <= 2

    def test_explain_match(self, matcher, sample_capes):
        """Test match explanation."""
        results = matcher.match("process json", sample_capes)

        if results:
            explanation = matcher.explain_match(results[0])
            assert "Cape:" in explanation
            assert "Score:" in explanation


class TestCapeRegistry:
    """Tests for CapeRegistry."""

    @pytest.fixture
    def cape_yaml_content(self):
        """Sample cape.yaml content."""
        return '''
id: test-cape
name: Test Cape
version: "1.0.0"
description: A test capability

metadata:
  author: test
  tags:
    - test
    - demo
  intents:
    - run test
    - execute demo

execution:
  type: tool
  tool_name: test_tool
'''

    @pytest.fixture
    def skill_md_content(self):
        """Sample SKILL.md content."""
        return '''---
name: test-skill
description: A test skill for reviewing code
---

# Test Skill

Instructions for the skill.
'''

    def test_register_cape(self):
        """Test manual Cape registration."""
        registry = CapeRegistry(auto_load=False)
        cape = Cape(
            id="manual-cape",
            name="Manual Cape",
            version="1.0.0",
            description="Manually registered",
            execution=CapeExecution(type=ExecutionType.LLM),
        )

        registry.register(cape)

        assert "manual-cape" in registry
        assert registry.get("manual-cape") is not None

    def test_unregister_cape(self):
        """Test Cape unregistration."""
        registry = CapeRegistry(auto_load=False)
        cape = Cape(
            id="temp-cape",
            name="Temp",
            version="1.0.0",
            description="Temporary",
            execution=CapeExecution(type=ExecutionType.LLM),
        )

        registry.register(cape)
        removed = registry.unregister("temp-cape")

        assert removed is not None
        assert "temp-cape" not in registry

    def test_load_from_capes_dir(self, cape_yaml_content):
        """Test loading Capes from directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            capes_dir = Path(tmpdir) / "capes"
            capes_dir.mkdir()

            cape_dir = capes_dir / "test-cape"
            cape_dir.mkdir()
            (cape_dir / "cape.yaml").write_text(cape_yaml_content)

            registry = CapeRegistry(capes_dir=capes_dir, auto_load=True, use_embeddings=False)

            assert "test-cape" in registry
            cape = registry.get("test-cape")
            assert cape.name == "Test Cape"

    def test_import_skills(self, skill_md_content):
        """Test importing Skills as Capes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir) / "skills"
            skills_dir.mkdir()

            skill_dir = skills_dir / "test-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(skill_md_content)

            registry = CapeRegistry(skills_dir=skills_dir, auto_load=True, use_embeddings=False)

            assert "test-skill" in registry
            cape = registry.get("test-skill")
            assert cape.metadata.source == SourceType.SKILL

    def test_match_query(self, cape_yaml_content):
        """Test query matching."""
        with tempfile.TemporaryDirectory() as tmpdir:
            capes_dir = Path(tmpdir) / "capes"
            capes_dir.mkdir()

            cape_dir = capes_dir / "test-cape"
            cape_dir.mkdir()
            (cape_dir / "cape.yaml").write_text(cape_yaml_content)

            registry = CapeRegistry(capes_dir=capes_dir, auto_load=True, use_embeddings=False)

            results = registry.match("run test")
            assert len(results) > 0

    def test_match_best(self, cape_yaml_content):
        """Test best match query."""
        with tempfile.TemporaryDirectory() as tmpdir:
            capes_dir = Path(tmpdir) / "capes"
            capes_dir.mkdir()

            cape_dir = capes_dir / "test-cape"
            cape_dir.mkdir()
            (cape_dir / "cape.yaml").write_text(cape_yaml_content)

            registry = CapeRegistry(capes_dir=capes_dir, auto_load=True, use_embeddings=False)

            best = registry.match_best("run test")
            assert best is not None
            assert best.id == "test-cape"

    def test_filter_by_tag(self):
        """Test filtering by tag."""
        registry = CapeRegistry(auto_load=False)

        registry.register(Cape(
            id="cape1",
            name="Cape 1",
            version="1.0.0",
            description="First",
            metadata=CapeMetadata(tags=["json", "data"]),
            execution=CapeExecution(type=ExecutionType.TOOL),
        ))
        registry.register(Cape(
            id="cape2",
            name="Cape 2",
            version="1.0.0",
            description="Second",
            metadata=CapeMetadata(tags=["pdf", "document"]),
            execution=CapeExecution(type=ExecutionType.TOOL),
        ))

        json_capes = registry.filter_by_tag("json")
        assert len(json_capes) == 1
        assert json_capes[0].id == "cape1"

    def test_filter_by_source(self):
        """Test filtering by source."""
        registry = CapeRegistry(auto_load=False)

        registry.register(Cape(
            id="native-cape",
            name="Native",
            version="1.0.0",
            description="Native cape",
            metadata=CapeMetadata(source=SourceType.NATIVE),
            execution=CapeExecution(type=ExecutionType.TOOL),
        ))
        registry.register(Cape(
            id="skill-cape",
            name="Skill",
            version="1.0.0",
            description="Imported skill",
            metadata=CapeMetadata(source=SourceType.SKILL),
            execution=CapeExecution(type=ExecutionType.LLM),
        ))

        native_capes = registry.filter_by_source(SourceType.NATIVE)
        assert len(native_capes) == 1
        assert native_capes[0].id == "native-cape"

    def test_summary(self):
        """Test registry summary."""
        registry = CapeRegistry(auto_load=False)

        registry.register(Cape(
            id="cape1",
            name="Cape 1",
            version="1.0.0",
            description="First",
            metadata=CapeMetadata(source=SourceType.NATIVE),
            execution=CapeExecution(type=ExecutionType.TOOL),
        ))
        registry.register(Cape(
            id="cape2",
            name="Cape 2",
            version="1.0.0",
            description="Second",
            metadata=CapeMetadata(source=SourceType.SKILL),
            execution=CapeExecution(type=ExecutionType.LLM),
        ))

        summary = registry.summary()

        assert summary["total"] == 2
        assert summary["by_source"]["native"] == 1
        assert summary["by_source"]["skill"] == 1
        assert summary["by_type"]["tool"] == 1
        assert summary["by_type"]["llm"] == 1

    def test_reload(self, cape_yaml_content):
        """Test registry reload."""
        with tempfile.TemporaryDirectory() as tmpdir:
            capes_dir = Path(tmpdir) / "capes"
            capes_dir.mkdir()

            cape_dir = capes_dir / "test-cape"
            cape_dir.mkdir()
            (cape_dir / "cape.yaml").write_text(cape_yaml_content)

            registry = CapeRegistry(capes_dir=capes_dir, auto_load=True, use_embeddings=False)
            initial_count = registry.count()

            # Add another cape
            cape_dir2 = capes_dir / "test-cape-2"
            cape_dir2.mkdir()
            (cape_dir2 / "cape.yaml").write_text(cape_yaml_content.replace("test-cape", "test-cape-2"))

            registry.reload()

            assert registry.count() == initial_count + 1

    def test_iteration(self):
        """Test registry iteration."""
        registry = CapeRegistry(auto_load=False)

        for i in range(3):
            registry.register(Cape(
                id=f"cape-{i}",
                name=f"Cape {i}",
                version="1.0.0",
                description=f"Cape number {i}",
                execution=CapeExecution(type=ExecutionType.TOOL),
            ))

        ids = [cape.id for cape in registry]
        assert len(ids) == 3
        assert "cape-0" in ids
