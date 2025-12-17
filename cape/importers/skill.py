"""
Skill Importer - Import Claude Skills as Capes.

This module allows seamless import of Claude SKILL.md files,
converting them into Cape format while preserving the original
skill prompt as a Claude adapter.

Mapping:
    Claude Skill          -> Cape
    ─────────────────────────────────────────
    name                  -> metadata.id, metadata.name
    description           -> metadata.description, metadata.intents
    usage_prompt (body)   -> model_adapters.claude.system_prompt
    allowed-tools         -> execution.tools_allowed
    constraints           -> interface.preconditions
    scripts/              -> execution (if present)
    references/           -> composition.provides
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from cape.core.models import (
    Cape,
    CapeExecution,
    CapeInterface,
    CapeMetadata,
    CapeSafety,
    ExecutionType,
    InputSchema,
    OutputSchema,
    RiskLevel,
    SourceType,
)

logger = logging.getLogger(__name__)


class SkillImporter:
    """
    Import Claude Skills as Capes.

    Preserves the original skill content as a Claude adapter while
    extracting structured information for the Cape definition.

    Usage:
        importer = SkillImporter()

        # Import single skill
        cape = importer.import_skill(Path("./skills/code-review"))

        # Import all skills from directory
        capes = importer.import_all(Path("./skills"))
    """

    def __init__(self):
        # Keywords that indicate file types
        self.file_type_patterns = [
            r"\.\w{2,5}\b",  # .pdf, .docx, etc.
        ]

        # Keywords that indicate actions
        self.action_keywords = [
            "analyze", "extract", "process", "convert", "generate", "create",
            "parse", "read", "write", "edit", "modify", "transform", "validate",
            "review", "check", "optimize", "debug", "test", "build", "deploy",
        ]

        # Keywords that indicate intents
        self.intent_patterns = [
            r"use when (.*?)(?:\.|$)",
            r"use this (?:skill |)when (.*?)(?:\.|$)",
            r"when (?:you |user |)(?:need|want|ask)s? to (.*?)(?:\.|$)",
        ]

    def import_skill(self, skill_path: Path) -> Cape:
        """
        Import a single Claude Skill as Cape.

        Args:
            skill_path: Path to skill directory (containing SKILL.md)

        Returns:
            Cape object
        """
        skill_path = Path(skill_path)
        skill_md = skill_path / "SKILL.md"

        if not skill_md.exists():
            raise FileNotFoundError(f"SKILL.md not found in {skill_path}")

        # Parse SKILL.md
        content = skill_md.read_text(encoding="utf-8")
        frontmatter, body = self._parse_frontmatter(content)

        # Build Cape
        return self._build_cape(skill_path, frontmatter, body)

    def import_all(self, skills_dir: Path) -> List[Cape]:
        """
        Import all skills from a directory.

        Args:
            skills_dir: Directory containing skill folders

        Returns:
            List of Cape objects
        """
        capes = []
        skills_dir = Path(skills_dir)

        for skill_path in skills_dir.iterdir():
            if not skill_path.is_dir():
                continue

            skill_md = skill_path / "SKILL.md"
            if not skill_md.exists():
                continue

            try:
                cape = self.import_skill(skill_path)
                capes.append(cape)
                logger.info(f"Imported skill: {cape.id}")
            except Exception as e:
                logger.error(f"Failed to import {skill_path}: {e}")

        return capes

    def _parse_frontmatter(self, content: str) -> tuple[Dict[str, Any], str]:
        """Parse YAML frontmatter from SKILL.md."""
        pattern = r"^---\n(.*?)\n---\n?(.*)"
        match = re.match(pattern, content, re.DOTALL)

        if not match:
            raise ValueError("Invalid SKILL.md format: missing frontmatter")

        frontmatter = yaml.safe_load(match.group(1))
        body = match.group(2).strip()

        return frontmatter, body

    def _build_cape(
        self,
        skill_path: Path,
        frontmatter: Dict[str, Any],
        body: str,
    ) -> Cape:
        """Build Cape from skill components."""

        # Extract name and description
        name = frontmatter.get("name", skill_path.name)
        description = frontmatter.get("description", "")

        # Extract intents from description
        intents = self._extract_intents(description)

        # Extract file types and actions
        file_types = self._extract_file_types(description)
        actions = self._extract_actions(description)

        # Infer execution type
        exec_type = self._infer_execution_type(skill_path)

        # Build ID
        cape_id = name.lower().replace("_", "-").replace(" ", "-")

        # Build metadata
        metadata = CapeMetadata(
            version="1.0.0",
            tags=frontmatter.get("metadata", {}).get("tags", []) + file_types,
            intents=intents,
            source=SourceType.SKILL,
            source_ref=str(skill_path),
            license=frontmatter.get("license"),
        )

        # Build interface
        interface = CapeInterface(
            input_schema=self._infer_input_schema(description, actions),
            output_schema=OutputSchema(type="string"),
            preconditions=frontmatter.get("constraints", []),
        )

        # Build execution
        execution = CapeExecution(
            type=exec_type,
            tools_allowed=frontmatter.get("allowed-tools", []),
            timeout_seconds=30,
        )

        # If has scripts, set entrypoint
        scripts_dir = skill_path / "scripts"
        if scripts_dir.exists():
            scripts = list(scripts_dir.glob("*.py"))
            if scripts:
                execution.entrypoint = f"scripts/{scripts[0].name}"

        # Build safety
        safety = CapeSafety(
            risk_level=self._infer_risk_level(frontmatter, description),
        )

        # Build model adapters
        model_adapters = {
            "claude": {
                "system_prompt": body,
                "usage_hints": description,
                "original_skill": True,
            }
        }

        # Build Cape
        return Cape(
            id=cape_id,
            name=name,
            version="1.0.0",
            description=description,
            metadata=metadata,
            interface=interface,
            execution=execution,
            safety=safety,
            model_adapters=model_adapters,
            _path=skill_path,
        )

    def _extract_intents(self, description: str) -> List[str]:
        """Extract intent patterns from description."""
        intents = []
        desc_lower = description.lower()

        for pattern in self.intent_patterns:
            matches = re.findall(pattern, desc_lower, re.IGNORECASE)
            intents.extend(matches)

        return intents

    def _extract_file_types(self, description: str) -> List[str]:
        """Extract file types from description."""
        file_types = []

        for pattern in self.file_type_patterns:
            matches = re.findall(pattern, description.lower())
            file_types.extend(matches)

        return list(set(file_types))

    def _extract_actions(self, description: str) -> List[str]:
        """Extract action keywords from description."""
        actions = []
        desc_lower = description.lower()

        for action in self.action_keywords:
            if action in desc_lower:
                actions.append(action)

        return actions

    def _infer_execution_type(self, skill_path: Path) -> ExecutionType:
        """Infer execution type from skill structure."""
        has_scripts = (skill_path / "scripts").exists()
        has_refs = (skill_path / "references").exists()

        if has_scripts and has_refs:
            return ExecutionType.HYBRID
        elif has_scripts:
            return ExecutionType.CODE
        elif has_refs:
            return ExecutionType.LLM
        else:
            return ExecutionType.LLM

    def _infer_input_schema(
        self,
        description: str,
        actions: List[str],
    ) -> InputSchema:
        """Infer input schema from description and actions."""
        properties = {}
        required = []

        # Common input patterns
        if any(a in actions for a in ["read", "parse", "extract", "analyze"]):
            properties["content"] = {
                "type": "string",
                "description": "Content to process",
            }
            required.append("content")

        if any(a in actions for a in ["convert", "transform"]):
            properties["format"] = {
                "type": "string",
                "description": "Target format",
            }

        # Default: accept any input
        if not properties:
            properties["input"] = {
                "type": "string",
                "description": "Input for the capability",
            }
            required.append("input")

        return InputSchema(
            type="object",
            properties=properties,
            required=required,
        )

    def _infer_risk_level(
        self,
        frontmatter: Dict[str, Any],
        description: str,
    ) -> RiskLevel:
        """Infer risk level from skill content."""
        desc_lower = description.lower()

        # High risk indicators
        high_risk_keywords = ["delete", "remove", "execute", "run", "deploy", "publish"]
        if any(kw in desc_lower for kw in high_risk_keywords):
            return RiskLevel.HIGH

        # Medium risk indicators
        medium_risk_keywords = ["write", "modify", "update", "create", "send"]
        if any(kw in desc_lower for kw in medium_risk_keywords):
            return RiskLevel.MEDIUM

        # Default to low
        return RiskLevel.LOW


def import_skill(skill_path: Path) -> Cape:
    """Convenience function to import a single skill."""
    return SkillImporter().import_skill(skill_path)


def import_skills(skills_dir: Path) -> List[Cape]:
    """Convenience function to import all skills."""
    return SkillImporter().import_all(skills_dir)
