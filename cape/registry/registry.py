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
    - Load Capes from Packs (organized capability packages)
    - Register Capes programmatically
    - Match user intents to Capes
    - Manage Cape lifecycle (add, remove, update)

    Usage:
        registry = CapeRegistry(capes_dir="./capes", packs_dir="./packs")

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
        packs_dir: Optional[Path] = None,
        auto_load: bool = True,
        use_embeddings: bool = True,
    ):
        """
        Initialize registry.

        Args:
            capes_dir: Directory containing Cape definitions (cape.yaml)
            skills_dir: Directory containing Claude Skills (SKILL.md) to import
            packs_dir: Directory containing Cape Packs (pack.yaml + capes/)
            auto_load: Whether to automatically load on init
            use_embeddings: Whether to use semantic matching
        """
        self.capes_dir = Path(capes_dir) if capes_dir else None
        self.skills_dir = Path(skills_dir) if skills_dir else None
        self.packs_dir = Path(packs_dir) if packs_dir else None

        # Registry storage
        self._capes: Dict[str, Cape] = {}
        self._packs: Dict[str, Dict] = {}  # Pack metadata storage

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

        # Load Cape Packs
        if self.packs_dir and self.packs_dir.exists():
            self._load_packs_dir(self.packs_dir)

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

    def _load_packs_dir(self, packs_dir: Path):
        """Load Cape Packs from directory."""
        for pack_path in packs_dir.iterdir():
            if not pack_path.is_dir():
                continue

            pack_file = pack_path / "pack.yaml"
            if not pack_file.exists():
                pack_file = pack_path / "pack.yml"

            if pack_file.exists():
                try:
                    self._load_pack(pack_path, pack_file)
                except Exception as e:
                    logger.error(f"Failed to load Pack from {pack_path}: {e}")

    def _load_pack(self, pack_path: Path, pack_file: Path):
        """Load a single Pack and its Capes."""
        # Load pack metadata
        content = pack_file.read_text(encoding="utf-8")
        pack_data = yaml.safe_load(content)
        pack_name = pack_data.get("name", pack_path.name)

        # Store pack metadata
        self._packs[pack_name] = {
            "path": pack_path,
            "metadata": pack_data,
        }

        logger.info(f"Loading Pack: {pack_name}")

        # Load capes from pack's capes directory
        capes_dir = pack_path / "capes"
        if capes_dir.exists():
            for cape_file in capes_dir.glob("*.yaml"):
                try:
                    cape = self._load_cape_file(cape_file)
                    # Tag cape with pack source
                    if "pack" not in cape.metadata.tags:
                        cape.metadata.tags.append(f"pack:{pack_name}")
                    self.register(cape)
                except Exception as e:
                    logger.error(f"Failed to load Cape from {cape_file}: {e}")

            # Also try .yml extension
            for cape_file in capes_dir.glob("*.yml"):
                try:
                    cape = self._load_cape_file(cape_file)
                    if "pack" not in cape.metadata.tags:
                        cape.metadata.tags.append(f"pack:{pack_name}")
                    self.register(cape)
                except Exception as e:
                    logger.error(f"Failed to load Cape from {cape_file}: {e}")

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

    def filter_by_pack(self, pack_name: str) -> List[Cape]:
        """Get Capes from a specific Pack."""
        tag = f"pack:{pack_name}"
        return [c for c in self._capes.values() if tag in c.metadata.tags]

    # ==================== Pack Operations ====================

    def get_packs(self) -> List[Dict[str, Any]]:
        """Get all loaded Packs with their metadata."""
        return [
            {
                "name": name,
                "display_name": data["metadata"].get("display_name", name),
                "description": data["metadata"].get("description", ""),
                "version": data["metadata"].get("version", "1.0.0"),
                "capes": data["metadata"].get("capes", []),
                "target_users": data["metadata"].get("target_users", []),
            }
            for name, data in self._packs.items()
        ]

    def get_pack(self, pack_name: str) -> Optional[Dict[str, Any]]:
        """Get a specific Pack's metadata."""
        pack_data = self._packs.get(pack_name)
        if not pack_data:
            return None
        return {
            "name": pack_name,
            "metadata": pack_data["metadata"],
            "capes": self.filter_by_pack(pack_name),
        }

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
        by_pack = {}

        for cape in self._capes.values():
            source = cape.metadata.source.value
            by_source[source] = by_source.get(source, 0) + 1

            exec_type = cape.execution.type.value
            by_type[exec_type] = by_type.get(exec_type, 0) + 1

            # Count by pack
            for tag in cape.metadata.tags:
                if tag.startswith("pack:"):
                    pack_name = tag.replace("pack:", "")
                    by_pack[pack_name] = by_pack.get(pack_name, 0) + 1

        return {
            "total": len(self._capes),
            "total_packs": len(self._packs),
            "by_source": by_source,
            "by_type": by_type,
            "by_pack": by_pack,
            "cape_ids": self.list_ids(),
            "pack_names": list(self._packs.keys()),
        }

    def __contains__(self, cape_id: str) -> bool:
        return cape_id in self._capes

    def __len__(self) -> int:
        return len(self._capes)

    def __iter__(self):
        return iter(self._capes.values())
