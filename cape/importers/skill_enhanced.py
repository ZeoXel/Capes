"""
Enhanced Skill Importer - Import Claude Skills with full script support.

Extends the base SkillImporter with:
- Complete scripts/ directory handling
- Automatic dependency detection
- Code adapter configuration
- Multiple model adapter generation
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from cape.core.models import (
    Cape,
    CapeExecution,
    ExecutionType,
)
from cape.importers.skill import SkillImporter

logger = logging.getLogger(__name__)


# Package name mapping for common imports
IMPORT_TO_PACKAGE = {
    "openpyxl": "openpyxl",
    "pandas": "pandas",
    "numpy": "numpy",
    "docx": "python-docx",
    "pptx": "python-pptx",
    "pdfplumber": "pdfplumber",
    "reportlab": "reportlab",
    "PyPDF2": "PyPDF2",
    "PIL": "pillow",
    "cv2": "opencv-python",
    "requests": "requests",
    "bs4": "beautifulsoup4",
    "yaml": "pyyaml",
    "lxml": "lxml",
    "xlrd": "xlrd",
    "xlwt": "xlwt",
    "csv": None,  # Built-in
    "json": None,  # Built-in
    "os": None,    # Built-in
    "sys": None,   # Built-in
    "pathlib": None,  # Built-in
}


class EnhancedSkillImporter(SkillImporter):
    """
    Enhanced Skill Importer with full code execution support.

    Features:
    - Detects and lists all scripts in scripts/ directory
    - Automatically detects Python dependencies from imports
    - Creates code adapter configuration
    - Generates adapters for multiple models (Claude, OpenAI, generic)

    Usage:
        importer = EnhancedSkillImporter()
        cape = importer.import_skill(Path("./skills/xlsx"))

        # Cape now has:
        # - execution.entrypoint pointing to main script
        # - model_adapters.code with scripts list and dependencies
        # - model_adapters for claude, openai, generic
    """

    def _build_cape(
        self,
        skill_path: Path,
        frontmatter: Dict[str, Any],
        body: str,
    ) -> Cape:
        """Build Cape with enhanced code support."""

        # Call base implementation first
        cape = super()._build_cape(skill_path, frontmatter, body)

        # Enhance with scripts support
        scripts_dir = skill_path / "scripts"
        if scripts_dir.exists():
            scripts = list(scripts_dir.glob("*.py"))

            if scripts:
                # Update execution type
                cape.execution.type = ExecutionType.HYBRID

                # Find main entry point
                main_script = self._find_main_script(scripts)
                cape.execution.entrypoint = f"scripts/{main_script.name}"

                # Detect dependencies
                dependencies = self._detect_dependencies(scripts)

                # Add code adapter
                cape.model_adapters["code"] = {
                    "scripts": [f"scripts/{s.name}" for s in scripts],
                    "main_script": f"scripts/{main_script.name}",
                    "dependencies": dependencies,
                    "runtime": "python",
                }

                logger.info(
                    f"Skill {cape.id}: found {len(scripts)} scripts, "
                    f"{len(dependencies)} dependencies"
                )

        # Enhance model adapters
        self._enhance_model_adapters(cape, body)

        return cape

    def _find_main_script(self, scripts: List[Path]) -> Path:
        """
        Find the main entry point script.

        Priority:
        1. main.py
        2. run.py
        3. execute.py
        4. __init__.py
        5. First alphabetically
        """
        priority_names = ["main.py", "run.py", "execute.py", "__init__.py"]

        for name in priority_names:
            for script in scripts:
                if script.name == name:
                    return script

        # Default to first script alphabetically
        return sorted(scripts, key=lambda p: p.name)[0]

    def _detect_dependencies(self, scripts: List[Path]) -> List[str]:
        """
        Detect Python dependencies from import statements.

        Analyzes all scripts and extracts package dependencies.
        """
        dependencies: Set[str] = set()

        for script in scripts:
            try:
                content = script.read_text(encoding="utf-8")
                deps = self._extract_imports(content)
                dependencies.update(deps)
            except Exception as e:
                logger.warning(f"Failed to analyze {script}: {e}")

        return sorted(dependencies)

    def _extract_imports(self, code: str) -> Set[str]:
        """
        Extract package dependencies from Python code.

        Handles:
        - import package
        - from package import module
        - from package.submodule import item
        """
        packages: Set[str] = set()

        # Pattern for import statements
        import_pattern = r'^(?:from|import)\s+([a-zA-Z_][a-zA-Z0-9_]*)'

        for match in re.finditer(import_pattern, code, re.MULTILINE):
            module = match.group(1)

            # Look up package name
            if module in IMPORT_TO_PACKAGE:
                package = IMPORT_TO_PACKAGE[module]
                if package:  # Skip built-ins (None)
                    packages.add(package)
            elif not module.startswith("_"):
                # Unknown package, assume same name
                # Skip if looks like local module
                if not self._is_likely_local_module(module, code):
                    packages.add(module)

        return packages

    def _is_likely_local_module(self, module: str, code: str) -> bool:
        """Check if module is likely a local module definition."""
        # Check for class/function definitions that might be the module
        patterns = [
            rf"^class\s+{module}\b",
            rf"^def\s+{module}\b",
            rf"^{module}\s*=",
        ]

        for pattern in patterns:
            if re.search(pattern, code, re.MULTILINE):
                return True

        return False

    def _enhance_model_adapters(self, cape: Cape, body: str) -> None:
        """
        Add adapters for multiple models.

        Creates consistent adapters for Claude, OpenAI, and generic models.
        """
        description = cape.description

        # Claude adapter (already exists, enhance it)
        if "claude" in cape.model_adapters:
            cape.model_adapters["claude"]["model_hint"] = "claude-3-sonnet"

        # OpenAI adapter
        cape.model_adapters["openai"] = {
            "system_prompt": self._convert_prompt_for_openai(body),
            "usage_hints": description,
            "model_hint": "gpt-4o",
        }

        # Generic adapter (model-agnostic)
        cape.model_adapters["generic"] = {
            "system_prompt": self._create_generic_prompt(body, description),
            "usage_hints": description,
        }

    def _convert_prompt_for_openai(self, claude_prompt: str) -> str:
        """
        Convert Claude-style prompt to OpenAI format.

        Adjusts formatting and removes Claude-specific conventions.
        """
        # Remove Claude-specific XML tags if present
        prompt = re.sub(r'<[^>]+>', '', claude_prompt)

        # Normalize whitespace
        prompt = re.sub(r'\n{3,}', '\n\n', prompt)

        return prompt.strip()

    def _create_generic_prompt(self, body: str, description: str) -> str:
        """
        Create model-agnostic prompt.

        Simplifies the prompt for maximum compatibility.
        """
        # Extract key sections
        sections = []

        # Add description
        sections.append(f"## Task\n{description}")

        # Extract guidelines if present
        guidelines_match = re.search(
            r'(?:##?\s*Guidelines?|##?\s*Instructions?)(.*?)(?=##|$)',
            body,
            re.DOTALL | re.IGNORECASE
        )
        if guidelines_match:
            sections.append(f"## Guidelines\n{guidelines_match.group(1).strip()}")

        # Extract examples if present
        examples_match = re.search(
            r'(?:##?\s*Examples?)(.*?)(?=##|$)',
            body,
            re.DOTALL | re.IGNORECASE
        )
        if examples_match:
            sections.append(f"## Examples\n{examples_match.group(1).strip()}")

        return "\n\n".join(sections)


def import_skill_enhanced(skill_path: Path) -> Cape:
    """Convenience function to import a single skill with enhancements."""
    return EnhancedSkillImporter().import_skill(skill_path)


def import_skills_enhanced(skills_dir: Path) -> List[Cape]:
    """Convenience function to import all skills with enhancements."""
    return EnhancedSkillImporter().import_all(skills_dir)
