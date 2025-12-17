"""
Cape Registry - Central registry for capability management.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml

from cape.core.models import Cape, SourceType
from cape.importers.skill import SkillImporter
from cape.registry.matcher import CapeMatcher

logger = logging.getLogger(__name__)


class CapeRegistry:
    """
    Central registry for Cape management.

    Responsibilities:
    - Load Capes from files (native and imported)
    - Register Capes programmatically
    - Match user intents to Capes
    - Manage Cape lifecycle (add, remove, update)

    Usage:
        registry = CapeRegistry(capes_dir="./capes")

        # Get Cape by ID
        cape = registry.get("json-processor")

        # Match by intent
        results = registry.match("I need to process a PDF file")

        # List all
        for cape in registry.all():
            print(cape.id)
    """

    def __init__(
        self,
        capes_dir: Optional[Path] = None,
        skills_dir: Optional[Path] = None,
        auto_load: bool = True,
        use_embeddings: bool = True,
    ):
        """
        Initialize registry.

        Args:
            capes_dir: Directory containing Cape definitions (cape.yaml)
            skills_dir: Directory containing Claude Skills (SKILL.md) to import
            auto_load: Whether to automatically load on init
            use_embeddings: Whether to use semantic matching
        """
        self.capes_dir = Path(capes_dir) if capes_dir else None
        self.skills_dir = Path(skills_dir) if skills_dir else None

        # Registry storage
        self._capes: Dict[str, Cape] = {}

        # Matcher for intent-based lookup
        self.matcher = CapeMatcher(use_embeddings=use_embeddings)

        # Importer for skills
        self.skill_importer = SkillImporter()

        # Load if requested
        if auto_load:
            self._load_all()

    def _load_all(self):
        """Load all Capes from configured directories."""
        # Load native Capes
        if self.capes_dir and self.capes_dir.exists():
            self._load_capes_dir(self.capes_dir)

        # Import Skills as Capes
        if self.skills_dir and self.skills_dir.exists():
            self._import_skills_dir(self.skills_dir)

        # Build matcher index
        self.matcher.index(list(self._capes.values()))

    def _load_capes_dir(self, capes_dir: Path):
        """Load Capes from directory."""
        for cape_path in capes_dir.iterdir():
            if not cape_path.is_dir():
                continue

            cape_file = cape_path / "cape.yaml"
            if not cape_file.exists():
                cape_file = cape_path / "cape.yml"

            if cape_file.exists():
                try:
                    cape = self._load_cape_file(cape_file)
                    self.register(cape)
                except Exception as e:
                    logger.error(f"Failed to load Cape from {cape_path}: {e}")

    def _load_cape_file(self, cape_file: Path) -> Cape:
        """Load Cape from YAML file."""
        content = cape_file.read_text(encoding="utf-8")
        data = yaml.safe_load(content)
        cape = Cape.from_dict(data)
        cape._path = cape_file.parent
        return cape

    def _import_skills_dir(self, skills_dir: Path):
        """Import Skills as Capes."""
        capes = self.skill_importer.import_all(skills_dir)
        for cape in capes:
            self.register(cape)

    # ==================== Core Operations ====================

    def register(self, cape: Cape):
        """
        Register a Cape.

        Args:
            cape: Cape to register
        """
        self._capes[cape.id] = cape
        logger.debug(f"Registered Cape: {cape.id}")

    def unregister(self, cape_id: str) -> Optional[Cape]:
        """
        Unregister a Cape.

        Args:
            cape_id: ID of Cape to remove

        Returns:
            Removed Cape or None
        """
        return self._capes.pop(cape_id, None)

    def get(self, cape_id: str) -> Optional[Cape]:
        """
        Get Cape by ID.

        Args:
            cape_id: Cape ID

        Returns:
            Cape or None
        """
        return self._capes.get(cape_id)

    def all(self) -> List[Cape]:
        """Get all registered Capes."""
        return list(self._capes.values())

    def count(self) -> int:
        """Get number of registered Capes."""
        return len(self._capes)

    # ==================== Matching ====================

    def match(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Match user query to Capes.

        Args:
            query: User's query/intent
            top_k: Maximum results to return
            threshold: Minimum score threshold

        Returns:
            List of match results with cape and score
        """
        return self.matcher.match(query, list(self._capes.values()), top_k, threshold)

    def match_best(
        self,
        query: str,
        threshold: float = 0.3,
    ) -> Optional[Cape]:
        """
        Get best matching Cape.

        Args:
            query: User's query/intent
            threshold: Minimum score threshold

        Returns:
            Best matching Cape or None
        """
        results = self.match(query, top_k=1, threshold=threshold)
        return results[0]["cape"] if results else None

    # ==================== Filtering ====================

    def filter_by_tag(self, tag: str) -> List[Cape]:
        """Get Capes with specific tag."""
        return [c for c in self._capes.values() if tag in c.metadata.tags]

    def filter_by_source(self, source: SourceType) -> List[Cape]:
        """Get Capes from specific source."""
        return [c for c in self._capes.values() if c.metadata.source == source]

    def filter_by_type(self, exec_type: str) -> List[Cape]:
        """Get Capes with specific execution type."""
        return [c for c in self._capes.values() if c.execution.type.value == exec_type]

    # ==================== Utility ====================

    def reload(self):
        """Reload all Capes from disk."""
        self._capes.clear()
        self._load_all()

    def export(self, cape_id: str, output_path: Path):
        """Export Cape to YAML file."""
        cape = self.get(cape_id)
        if not cape:
            raise ValueError(f"Cape not found: {cape_id}")

        output_path.write_text(cape.to_yaml(), encoding="utf-8")

    def list_ids(self) -> List[str]:
        """List all Cape IDs."""
        return list(self._capes.keys())

    def summary(self) -> Dict[str, Any]:
        """Get registry summary."""
        by_source = {}
        by_type = {}

        for cape in self._capes.values():
            source = cape.metadata.source.value
            by_source[source] = by_source.get(source, 0) + 1

            exec_type = cape.execution.type.value
            by_type[exec_type] = by_type.get(exec_type, 0) + 1

        return {
            "total": len(self._capes),
            "by_source": by_source,
            "by_type": by_type,
            "cape_ids": self.list_ids(),
        }

    def __contains__(self, cape_id: str) -> bool:
        return cape_id in self._capes

    def __len__(self) -> int:
        return len(self._capes)

    def __iter__(self):
        return iter(self._capes.values())
