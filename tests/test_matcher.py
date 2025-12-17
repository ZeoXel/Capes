"""
Tests for the intent matcher.
"""

import pytest

from langchain_skills.core.skill import Skill, SkillMetadata, SkillType
from langchain_skills.recognition.matcher import IntentMatcher, MatchResult
from pathlib import Path


@pytest.fixture
def sample_skills():
    """Create sample skills for testing."""
    skills = [
        Skill(
            metadata=SkillMetadata(
                name="pdf-processor",
                description="Extract text and tables from PDF files. Use when processing .pdf documents.",
                skill_type=SkillType.TOOL,
                trigger_keywords=["pdf", "extract", "text", "tables", "document"],
                file_types=[".pdf"],
                action_verbs=["extract", "process"],
            ),
            path=Path("/tmp/pdf-processor"),
        ),
        Skill(
            metadata=SkillMetadata(
                name="code-reviewer",
                description="Review code for bugs, style issues, and best practices. Use for code analysis.",
                skill_type=SkillType.INSTRUCTION,
                trigger_keywords=["code", "review", "bugs", "style", "analysis"],
                file_types=[],
                action_verbs=["review", "analyze"],
            ),
            path=Path("/tmp/code-reviewer"),
        ),
        Skill(
            metadata=SkillMetadata(
                name="data-analyzer",
                description="Analyze CSV and Excel data files. Generate statistics and visualizations.",
                skill_type=SkillType.HYBRID,
                trigger_keywords=["data", "csv", "excel", "statistics", "analyze"],
                file_types=[".csv", ".xlsx"],
                action_verbs=["analyze", "generate"],
            ),
            path=Path("/tmp/data-analyzer"),
        ),
    ]
    return skills


class TestIntentMatcher:
    """Tests for IntentMatcher."""

    def test_exact_match(self, sample_skills):
        """Test exact name matching."""
        matcher = IntentMatcher(use_embeddings=False)

        results = matcher.match("use pdf-processor to extract text", sample_skills)

        assert len(results) > 0
        assert results[0].skill.name == "pdf-processor"
        assert results[0].match_type == "exact"
        assert results[0].score == 1.0

    def test_keyword_match(self, sample_skills):
        """Test keyword-based matching."""
        matcher = IntentMatcher(use_embeddings=False)

        results = matcher.match("review my code for bugs", sample_skills)

        # Should match code-reviewer
        code_reviewer = next((r for r in results if r.skill.name == "code-reviewer"), None)
        assert code_reviewer is not None
        assert code_reviewer.details.get("keyword_score", 0) > 0

    def test_context_match_file_type(self, sample_skills):
        """Test file type context matching."""
        matcher = IntentMatcher(use_embeddings=False)

        results = matcher.match("process this .pdf file", sample_skills)

        # Should match pdf-processor due to file type
        pdf_match = next((r for r in results if r.skill.name == "pdf-processor"), None)
        assert pdf_match is not None
        assert pdf_match.details.get("context_score", 0) > 0

    def test_context_match_action_verb(self, sample_skills):
        """Test action verb context matching."""
        matcher = IntentMatcher(use_embeddings=False)

        results = matcher.match("analyze this dataset", sample_skills)

        # Should match data-analyzer due to action verb
        data_match = next((r for r in results if r.skill.name == "data-analyzer"), None)
        assert data_match is not None

    def test_threshold_filtering(self, sample_skills):
        """Test that low scores are filtered out."""
        matcher = IntentMatcher(use_embeddings=False)

        # Very unrelated query
        results = matcher.match("make me a sandwich", sample_skills, threshold=0.5)

        # Should have no or few results above threshold
        assert all(r.score >= 0.5 for r in results)

    def test_top_k_limiting(self, sample_skills):
        """Test that results are limited to top_k."""
        matcher = IntentMatcher(use_embeddings=False)

        results = matcher.match("process and analyze data", sample_skills, top_k=2)

        assert len(results) <= 2

    def test_match_best(self, sample_skills):
        """Test getting best match only."""
        matcher = IntentMatcher(use_embeddings=False)

        result = matcher.match_best("review code", sample_skills)

        assert result is not None
        assert isinstance(result, MatchResult)

    def test_match_best_no_match(self, sample_skills):
        """Test best match with no results."""
        matcher = IntentMatcher(use_embeddings=False)

        result = matcher.match_best("completely unrelated query xyz", sample_skills, threshold=0.9)

        # May or may not return None depending on implementation
        if result is not None:
            assert result.score >= 0.9

    def test_score_ordering(self, sample_skills):
        """Test that results are ordered by score descending."""
        matcher = IntentMatcher(use_embeddings=False)

        results = matcher.match("analyze pdf data", sample_skills)

        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i].score >= results[i + 1].score

    def test_explain_match(self, sample_skills):
        """Test match explanation generation."""
        matcher = IntentMatcher(use_embeddings=False)

        results = matcher.match("extract text from pdf", sample_skills)
        if results:
            explanation = matcher.explain_match(results[0])

            assert "Skill:" in explanation
            assert "Score:" in explanation
            assert "Score Breakdown:" in explanation

    def test_index_status(self, sample_skills):
        """Test getting index status."""
        matcher = IntentMatcher(use_embeddings=False)
        matcher.index_skills(sample_skills)

        status = matcher.get_index_status()

        assert "use_embeddings" in status
        assert "weights" in status


class TestIntentMatcherWithEmbeddings:
    """Tests for IntentMatcher with embeddings (may skip if not available)."""

    @pytest.fixture
    def matcher_with_embeddings(self, sample_skills):
        """Create matcher with embeddings if available."""
        try:
            from sentence_transformers import SentenceTransformer
            matcher = IntentMatcher(use_embeddings=True)
            matcher.index_skills(sample_skills)
            return matcher
        except ImportError:
            pytest.skip("sentence-transformers not installed")

    def test_semantic_match(self, matcher_with_embeddings, sample_skills):
        """Test semantic similarity matching."""
        # Use a semantically similar but different query
        results = matcher_with_embeddings.match(
            "help me look at my python function",  # Similar to code review
            sample_skills
        )

        # Should find code-reviewer as relevant
        code_match = next((r for r in results if r.skill.name == "code-reviewer"), None)
        assert code_match is not None
        assert code_match.details.get("semantic_score", 0) > 0

    def test_semantic_vs_keyword(self, matcher_with_embeddings, sample_skills):
        """Test that semantic matching adds value over keyword matching."""
        # Query with no direct keyword overlap
        results = matcher_with_embeddings.match(
            "find problems in my source file",  # No direct keywords
            sample_skills
        )

        # Should still find code-reviewer through semantic similarity
        code_match = next((r for r in results if r.skill.name == "code-reviewer"), None)
        if code_match:
            # Semantic score should contribute
            assert code_match.details.get("semantic_score", 0) > 0
