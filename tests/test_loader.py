"""
Tests for the skill loader.
"""

import tempfile
from pathlib import Path

import pytest

from langchain_skills.core.loader import SkillLoader
from langchain_skills.core.skill import LoadLevel, SkillType


@pytest.fixture
def temp_skills_dir():
    """Create a temporary skills directory with test skills."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir)

        # Create a simple instruction skill
        instruction_skill = skills_dir / "test-instruction"
        instruction_skill.mkdir()
        (instruction_skill / "SKILL.md").write_text('''---
name: test-instruction
description: A test instruction skill for unit testing. Use when testing the skill loader.
---

# Test Instruction Skill

This is a test skill body.
''')

        # Create a tool skill with scripts
        tool_skill = skills_dir / "test-tool"
        tool_skill.mkdir()
        (tool_skill / "scripts").mkdir()
        (tool_skill / "SKILL.md").write_text('''---
name: test-tool
description: A test tool skill with scripts. Processes .txt files.
allowed-tools:
  - python-executor
---

# Test Tool Skill

Use the scripts in this skill.
''')
        (tool_skill / "scripts" / "process.py").write_text('print("hello")')

        # Create a knowledge skill with references
        knowledge_skill = skills_dir / "test-knowledge"
        knowledge_skill.mkdir()
        (knowledge_skill / "references").mkdir()
        (knowledge_skill / "SKILL.md").write_text('''---
name: test-knowledge
description: A test knowledge skill with reference documents.
---

# Test Knowledge Skill

Refer to the documentation.
''')
        (knowledge_skill / "references" / "guide.md").write_text("# Guide\n\nSome content.")

        yield skills_dir


class TestSkillLoader:
    """Tests for SkillLoader."""

    def test_load_all(self, temp_skills_dir):
        """Test loading all skills."""
        loader = SkillLoader(temp_skills_dir)
        skills = loader.load_all()

        assert len(skills) == 3
        names = {s.name for s in skills}
        assert names == {"test-instruction", "test-tool", "test-knowledge"}

    def test_load_skill_by_name(self, temp_skills_dir):
        """Test loading a specific skill."""
        loader = SkillLoader(temp_skills_dir)
        skill = loader.load_skill("test-instruction")

        assert skill is not None
        assert skill.name == "test-instruction"
        assert skill.loaded_level == LoadLevel.METADATA

    def test_load_skill_body(self, temp_skills_dir):
        """Test loading skill body content."""
        loader = SkillLoader(temp_skills_dir)
        skill = loader.load_skill("test-instruction")

        assert skill.body_content is None

        loader.load_body(skill)

        assert skill.body_content is not None
        assert "Test Instruction Skill" in skill.body_content
        assert skill.loaded_level == LoadLevel.BODY

    def test_load_skill_resources(self, temp_skills_dir):
        """Test loading skill resources."""
        loader = SkillLoader(temp_skills_dir)
        skill = loader.load_skill("test-tool")

        loader.load_resources(skill)

        assert "process.py" in skill.scripts
        assert skill.loaded_level == LoadLevel.RESOURCES

    def test_skill_type_inference(self, temp_skills_dir):
        """Test that skill types are correctly inferred."""
        loader = SkillLoader(temp_skills_dir)
        skills = loader.load_all()

        skill_types = {s.name: s.skill_type for s in skills}

        assert skill_types["test-instruction"] == SkillType.INSTRUCTION
        assert skill_types["test-tool"] == SkillType.TOOL
        assert skill_types["test-knowledge"] == SkillType.KNOWLEDGE

    def test_trigger_keyword_extraction(self, temp_skills_dir):
        """Test that trigger keywords are extracted from description."""
        loader = SkillLoader(temp_skills_dir)
        skill = loader.load_skill("test-instruction")

        # Should have extracted some keywords
        assert len(skill.metadata.trigger_keywords) > 0
        assert "test" in skill.metadata.trigger_keywords

    def test_file_type_extraction(self, temp_skills_dir):
        """Test that file types are extracted from description."""
        loader = SkillLoader(temp_skills_dir)
        skill = loader.load_skill("test-tool")

        assert ".txt" in skill.metadata.file_types

    def test_load_nonexistent_skill(self, temp_skills_dir):
        """Test loading a skill that doesn't exist."""
        loader = SkillLoader(temp_skills_dir)
        skill = loader.load_skill("nonexistent")

        assert skill is None

    def test_read_script(self, temp_skills_dir):
        """Test reading a script file."""
        loader = SkillLoader(temp_skills_dir)
        skill = loader.load_skill("test-tool")

        content = loader.read_script(skill, "process.py")

        assert content is not None
        assert "print" in content

    def test_read_reference(self, temp_skills_dir):
        """Test reading a reference file."""
        loader = SkillLoader(temp_skills_dir)
        skill = loader.load_skill("test-knowledge")

        content = loader.read_reference(skill, "guide.md")

        assert content is not None
        assert "Guide" in content
