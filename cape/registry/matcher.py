"""
Cape Matcher - Intent matching for capability discovery.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from cape.core.models import Cape

logger = logging.getLogger(__name__)


class CapeMatcher:
    """
    Match user intents to Capes.

    Supports multiple matching strategies:
    1. Exact ID match
    2. Intent pattern match
    3. Tag/keyword match
    4. Semantic similarity (optional)

    Usage:
        matcher = CapeMatcher(use_embeddings=True)
        matcher.index(capes)
        results = matcher.match("process this PDF", capes)
    """

    def __init__(self, use_embeddings: bool = True):
        """
        Initialize matcher.

        Args:
            use_embeddings: Whether to use semantic embeddings
        """
        self.use_embeddings = use_embeddings
        self._model = None
        self._embeddings: Dict[str, Any] = {}

    def index(self, capes: List[Cape]):
        """
        Build index for Capes.

        Args:
            capes: Capes to index
        """
        if not self.use_embeddings:
            return

        try:
            from sentence_transformers import SentenceTransformer
            import numpy as np

            if self._model is None:
                logger.info("Loading embedding model...")
                self._model = SentenceTransformer("all-MiniLM-L6-v2")

            # Build embeddings
            for cape in capes:
                # Combine description and intents for embedding
                text = f"{cape.description} " + " ".join(cape.metadata.intents)
                embedding = self._model.encode(text)
                self._embeddings[cape.id] = embedding

            logger.info(f"Indexed {len(capes)} Capes for semantic matching")

        except ImportError:
            logger.warning("sentence-transformers not available, using keyword matching only")
            self.use_embeddings = False

    def match(
        self,
        query: str,
        capes: List[Cape],
        top_k: int = 5,
        threshold: float = 0.3,
    ) -> List[Dict[str, Any]]:
        """
        Match query to Capes.

        Args:
            query: User's query
            capes: Capes to match against
            top_k: Maximum results
            threshold: Minimum score

        Returns:
            List of {cape, score, match_type} dicts
        """
        results = []
        query_lower = query.lower()

        for cape in capes:
            # 1. Exact ID match
            if cape.id in query_lower:
                results.append({
                    "cape": cape,
                    "score": 1.0,
                    "match_type": "exact",
                })
                continue

            # Calculate scores
            intent_score = self._match_intents(query_lower, cape)
            keyword_score = self._match_keywords(query_lower, cape)
            semantic_score = self._match_semantic(query, cape) if self.use_embeddings else 0.0

            # Weighted combination
            total_score = (
                0.4 * semantic_score +
                0.35 * intent_score +
                0.25 * keyword_score
            )

            if total_score >= threshold:
                match_type = "semantic" if semantic_score > intent_score else "intent"
                results.append({
                    "cape": cape,
                    "score": total_score,
                    "match_type": match_type,
                    "details": {
                        "intent_score": intent_score,
                        "keyword_score": keyword_score,
                        "semantic_score": semantic_score,
                    },
                })

        # Sort by score
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def _match_intents(self, query: str, cape: Cape) -> float:
        """Match against Cape's intent patterns."""
        if not cape.metadata.intents:
            return 0.0

        best_match = 0.0
        for intent in cape.metadata.intents:
            intent_lower = intent.lower()
            score = 0.0

            # 1. Exact phrase match (highest priority)
            if intent_lower in query or query in intent_lower:
                score = 1.0
            # 2. Chinese character overlap matching
            elif self._has_chinese(intent_lower):
                char_overlap = self._chinese_char_overlap(query, intent_lower)
                if char_overlap >= 0.6:  # At least 60% key characters match
                    score = char_overlap
            # 3. Word overlap (for English)
            else:
                intent_words = set(intent_lower.split())
                query_words = set(query.split())
                overlap = len(intent_words & query_words)
                if overlap >= 2:
                    score = 0.5 + (overlap / len(intent_words)) * 0.5

            best_match = max(best_match, score)

        return best_match

    def _has_chinese(self, text: str) -> bool:
        """Check if text contains Chinese characters."""
        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                return True
        return False

    def _chinese_char_overlap(self, query: str, intent: str) -> float:
        """Calculate character overlap ratio for Chinese text."""
        # Remove common characters that don't carry meaning
        common_chars = set('的是了在有和与或者为被给把被让使能会要可以这那些个人我你他她它们')

        # Get meaningful characters from intent
        intent_chars = set(char for char in intent if '\u4e00' <= char <= '\u9fff')
        intent_chars -= common_chars

        if not intent_chars:
            return 0.0

        # Count how many intent characters appear in query
        matches = sum(1 for char in intent_chars if char in query)
        return matches / len(intent_chars)

    def _match_keywords(self, query: str, cape: Cape) -> float:
        """Match against tags and description keywords."""
        score = 0.0

        # Tag matching
        query_words = set(query.split())
        tags = set(t.lower() for t in cape.metadata.tags)
        tag_overlap = len(query_words & tags)
        score += tag_overlap * 0.3

        # Description keyword matching
        desc_words = set(re.findall(r"\b\w{3,}\b", cape.description.lower()))
        desc_overlap = len(query_words & desc_words)
        score += min(desc_overlap * 0.1, 0.5)

        # File type matching
        file_types = [t for t in cape.metadata.tags if t.startswith(".")]
        for ft in file_types:
            if ft in query:
                score += 0.4

        return min(1.0, score)

    def _match_semantic(self, query: str, cape: Cape) -> float:
        """Semantic similarity matching."""
        if not self.use_embeddings or cape.id not in self._embeddings:
            return 0.0

        try:
            import numpy as np

            query_embedding = self._model.encode(query)
            cape_embedding = self._embeddings[cape.id]

            # Cosine similarity
            similarity = np.dot(query_embedding, cape_embedding) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(cape_embedding)
            )

            # Normalize to 0-1
            return float(max(0.0, (similarity + 1) / 2))

        except Exception as e:
            logger.warning(f"Semantic matching failed: {e}")
            return 0.0

    def explain_match(self, result: Dict[str, Any]) -> str:
        """Generate explanation for a match result."""
        cape = result["cape"]
        score = result["score"]
        match_type = result["match_type"]

        lines = [
            f"Cape: {cape.id}",
            f"Score: {score:.3f} (type: {match_type})",
            f"Description: {cape.description[:100]}...",
        ]

        if "details" in result:
            lines.append("\nScore breakdown:")
            for key, value in result["details"].items():
                lines.append(f"  - {key}: {value:.3f}")

        return "\n".join(lines)
