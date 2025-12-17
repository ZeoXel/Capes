"""Tests for Skill importer."""

import pytest
from pathlib import Path
import tempfile
import os

from cape.importers.skill import SkillImporter
from cape.core.models import ExecutionType, SourceType


class TestSkillImporter:
    """Tests for SkillImporter."""

    @pytest.fixture
    def importer(self):
        """Create SkillImporter instance."""
        return SkillImporter()

    @pytest.fixture
    def sample_skill_md(self):
        """Sample SKILL.md content."""
        return '''---
name: code-review
description: >
  Perform code review for pull requests, analyze code quality, identify bugs,
  and suggest improvements. Use when user asks to "review code" or "check PR".
license: MIT
allowed-tools:
  - Read
  - Grep
---

# Code Review Skill

When reviewing code, follow these steps:

1. **Understand the Context**
   - Read the PR description
   - Understand the purpose of the changes

2. **Check Code Quality**
   - Look for bugs and edge cases
   - Check error handling
   - Verify naming conventions

3. **Provide Feedback**
   - Be constructive and specific
   - Suggest improvements with examples
'''

    @pytest.fixture
    def skill_with_scripts(self):
        """Sample SKILL.md with scripts."""
        return '''---
name: pdf-processing
description: >
  Extract text, tables, and metadata from PDF files. When Claude needs to
  process PDF documents, fill forms, or extract data from .pdf files.
allowed-tools:
  - Read
  - Bash
---

# PDF Processing

Use the scripts in the scripts/ directory to process PDFs.

## Available Operations

- Extract text: `scripts/extract_text.py`
- Extract tables: `scripts/extract_tables.py`
'''

    def test_parse_skill_md(self, importer, sample_skill_md):
        """Test parsing SKILL.md content."""
        metadata, body = importer._parse_skill_md(sample_skill_md)

        assert metadata["name"] == "code-review"
        assert "code review" in metadata["description"].lower()
        assert metadata["license"] == "MIT"
        assert "Read" in metadata["allowed-tools"]
        assert "# Code Review Skill" in body

    def test_extract_intents(self, importer):
        """Test extracting intents from description."""
        description = '''
        Perform code review for pull requests. When user asks to
        "review code", "check PR", or "analyze quality". Use for
        code analysis and improvement suggestions.
        '''
        intents = importer._extract_intents(description)

        assert len(intents) > 0
        # Should extract quoted phrases
        assert any("review code" in i.lower() for i in intents)

    def test_extract_file_types(self, importer):
        """Test extracting file types from description."""
        description = "Process .pdf, .docx, and .xlsx files"
        file_types = importer._extract_file_types(description)

        assert ".pdf" in file_types
        assert ".docx" in file_types
        assert ".xlsx" in file_types

    def test_extract_actions(self, importer):
        """Test extracting action verbs."""
        description = "Extract text, analyze content, and generate reports"
        actions = importer._extract_actions(description)

        assert "extract" in actions
        assert "analyze" in actions
        assert "generate" in actions

    def test_import_skill_basic(self, importer, sample_skill_md):
        """Test importing a basic skill."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "code-review"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(sample_skill_md)

            cape = importer.import_skill(skill_dir)

            assert cape.id == "code-review"
            assert cape.metadata.source == SourceType.SKILL
            assert "review" in cape.description.lower()
            assert cape.execution.type == ExecutionType.LLM
            # Check Claude adapter has the skill body
            assert cape.model_adapters is not None
            assert "claude" in cape.model_adapters
            assert "system_prompt" in cape.model_adapters["claude"]

    def test_import_skill_with_scripts(self, importer, skill_with_scripts):
        """Test importing a skill with scripts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "pdf-processing"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(skill_with_scripts)

            # Create scripts directory
            scripts_dir = skill_dir / "scripts"
            scripts_dir.mkdir()
            (scripts_dir / "extract_text.py").write_text("# Extract text")
            (scripts_dir / "extract_tables.py").write_text("# Extract tables")

            cape = importer.import_skill(skill_dir)

            assert cape.id == "pdf-processing"
            # Should detect as HYBRID due to scripts
            assert cape.execution.type in [ExecutionType.LLM, ExecutionType.HYBRID]
            assert ".pdf" in cape.metadata.tags

    def test_import_all(self, importer, sample_skill_md, skill_with_scripts):
        """Test importing all skills from directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skills_dir = Path(tmpdir)

            # Create code-review skill
            review_dir = skills_dir / "code-review"
            review_dir.mkdir()
            (review_dir / "SKILL.md").write_text(sample_skill_md)

            # Create pdf-processing skill
            pdf_dir = skills_dir / "pdf-processing"
            pdf_dir.mkdir()
            (pdf_dir / "SKILL.md").write_text(skill_with_scripts)

            capes = importer.import_all(skills_dir)

            assert len(capes) == 2
            ids = [c.id for c in capes]
            assert "code-review" in ids
            assert "pdf-processing" in ids

    def test_import_nonexistent_skill(self, importer):
        """Test importing non-existent skill."""
        cape = importer.import_skill(Path("/nonexistent/path"))
        assert cape is None

    def test_import_invalid_skill(self, importer):
        """Test importing invalid skill (no SKILL.md)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "invalid-skill"
            skill_dir.mkdir()
            # No SKILL.md file

            cape = importer.import_skill(skill_dir)
            assert cape is None

    def test_metadata_preservation(self, importer, sample_skill_md):
        """Test that skill metadata is preserved in Cape."""
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "code-review"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(sample_skill_md)

            cape = importer.import_skill(skill_dir)

            # License should be preserved
            assert cape.metadata.license == "MIT"
            # Allowed tools should be in metadata
            assert "code" in cape.metadata.tags or "review" in cape.metadata.tags

    def test_intent_extraction_quality(self, importer):
        """Test quality of intent extraction."""
        description = '''
        Comprehensive PDF manipulation toolkit for extracting text and tables,
        creating new PDFs, merging/splitting documents, and handling forms.
        When Claude needs to fill in a PDF form or programmatically process,
        generate, or analyze PDF documents at scale.
        '''
        intents = importer._extract_intents(description)

        # Should extract meaningful intents
        assert len(intents) > 0
        # Should include action phrases
        intent_text = " ".join(intents).lower()
        assert any(word in intent_text for word in ["pdf", "extract", "process"])


class TestSkillImporterEdgeCases:
    """Edge case tests for SkillImporter."""

    @pytest.fixture
    def importer(self):
        return SkillImporter()

    def test_empty_description(self, importer):
        """Test handling empty description."""
        skill_md = '''---
name: empty-desc
description: ""
---

# Empty Description Skill
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "empty-desc"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(skill_md)

            cape = importer.import_skill(skill_dir)
            assert cape is not None
            assert cape.id == "empty-desc"

    def test_missing_name(self, importer):
        """Test handling missing name in frontmatter."""
        skill_md = '''---
description: A skill without a name
---

# Unnamed Skill
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "unnamed"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(skill_md)

            cape = importer.import_skill(skill_dir)
            # Should use directory name as fallback
            assert cape is not None
            assert cape.id == "unnamed"

    def test_unicode_content(self, importer):
        """Test handling unicode content."""
        skill_md = '''---
name: unicode-skill
description: 处理中文内容的技能，支持日本語和한국어
---

# Unicode Skill

支持多语言内容处理。
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            skill_dir = Path(tmpdir) / "unicode-skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")

            cape = importer.import_skill(skill_dir)
            assert cape is not None
            assert "中文" in cape.description
