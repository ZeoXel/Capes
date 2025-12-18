"""
Test Cape Packs loading and functionality.
"""

import pytest
from pathlib import Path

from cape.registry.registry import CapeRegistry


@pytest.fixture
def registry():
    """Create registry with packs loaded."""
    base_dir = Path(__file__).parent.parent
    return CapeRegistry(
        capes_dir=base_dir / "capes",
        packs_dir=base_dir / "packs",
        skills_dir=base_dir / "skills",
        auto_load=True,
        use_embeddings=False,  # Disable for faster tests
    )


class TestPacksLoading:
    """Test that Packs are loaded correctly."""

    def test_packs_loaded(self, registry):
        """Test that packs are loaded."""
        packs = registry.get_packs()
        assert len(packs) >= 2, "Should have at least 2 packs (office, creator)"

        pack_names = [p["name"] for p in packs]
        assert "office-pack" in pack_names
        assert "creator-pack" in pack_names

    def test_office_pack_capes(self, registry):
        """Test Office Pack capes are loaded."""
        office_capes = registry.filter_by_pack("office-pack")
        cape_ids = [c.id for c in office_capes]

        expected_capes = [
            "doc-writer",
            "slide-maker",
            "email-composer",
            "sheet-analyst",
            "meeting-assistant",
        ]

        for cape_id in expected_capes:
            assert cape_id in cape_ids, f"Office Pack should have {cape_id}"

    def test_creator_pack_capes(self, registry):
        """Test Creator Pack capes are loaded."""
        creator_capes = registry.filter_by_pack("creator-pack")
        cape_ids = [c.id for c in creator_capes]

        expected_capes = [
            "content-writer",
            "title-generator",
            "copywriter",
            "content-repurposer",
            "seo-optimizer",
        ]

        for cape_id in expected_capes:
            assert cape_id in cape_ids, f"Creator Pack should have {cape_id}"


class TestCapeIntentMatching:
    """Test intent matching for Pack capes."""

    def test_doc_writer_intents(self, registry):
        """Test doc-writer intent matching."""
        results = registry.match("帮我写一份报告", top_k=3)
        assert len(results) > 0
        cape_ids = [r["cape"].id for r in results]
        assert "doc-writer" in cape_ids, "Should match doc-writer for '写报告'"

    def test_slide_maker_intents(self, registry):
        """Test slide-maker intent matching."""
        results = registry.match("做一个PPT", top_k=3)
        assert len(results) > 0
        cape_ids = [r["cape"].id for r in results]
        assert "slide-maker" in cape_ids, "Should match slide-maker for 'PPT'"

    def test_content_writer_intents(self, registry):
        """Test content-writer intent matching."""
        results = registry.match("写一篇小红书笔记", top_k=3)
        assert len(results) > 0
        cape_ids = [r["cape"].id for r in results]
        assert "content-writer" in cape_ids, "Should match content-writer"

    def test_title_generator_intents(self, registry):
        """Test title-generator intent matching."""
        results = registry.match("帮我起个爆款标题", top_k=3)
        assert len(results) > 0
        cape_ids = [r["cape"].id for r in results]
        assert "title-generator" in cape_ids, "Should match title-generator"

    def test_email_composer_intents(self, registry):
        """Test email-composer intent matching."""
        results = registry.match("写一封邮件", top_k=3)
        assert len(results) > 0
        cape_ids = [r["cape"].id for r in results]
        assert "email-composer" in cape_ids, "Should match email-composer"


class TestCapeStructure:
    """Test Cape YAML structure is valid."""

    def test_cape_has_required_fields(self, registry):
        """Test all capes have required fields."""
        for cape in registry.all():
            assert cape.id, f"Cape missing id"
            assert cape.name, f"Cape {cape.id} missing name"
            assert cape.description, f"Cape {cape.id} missing description"

    def test_cape_has_intents(self, registry):
        """Test capes have intents for matching."""
        pack_capes = []
        pack_capes.extend(registry.filter_by_pack("office-pack"))
        pack_capes.extend(registry.filter_by_pack("creator-pack"))

        for cape in pack_capes:
            assert len(cape.metadata.intents) > 0, f"Cape {cape.id} has no intents"

    def test_cape_has_model_adapters(self, registry):
        """Test capes have model adapters configured."""
        pack_capes = []
        pack_capes.extend(registry.filter_by_pack("office-pack"))
        pack_capes.extend(registry.filter_by_pack("creator-pack"))

        for cape in pack_capes:
            assert len(cape.model_adapters) > 0, f"Cape {cape.id} has no model adapters"


class TestRegistrySummary:
    """Test registry summary includes pack info."""

    def test_summary_includes_packs(self, registry):
        """Test summary includes pack information."""
        summary = registry.summary()

        assert "total_packs" in summary
        assert summary["total_packs"] >= 2

        assert "by_pack" in summary
        assert "office-pack" in summary["by_pack"]
        assert "creator-pack" in summary["by_pack"]

        assert "pack_names" in summary
        assert "office-pack" in summary["pack_names"]
        assert "creator-pack" in summary["pack_names"]


if __name__ == "__main__":
    # Quick test run
    base_dir = Path(__file__).parent.parent
    registry = CapeRegistry(
        capes_dir=base_dir / "capes",
        packs_dir=base_dir / "packs",
        skills_dir=base_dir / "skills",
        auto_load=True,
        use_embeddings=False,
    )

    print("=" * 60)
    print("Registry Summary")
    print("=" * 60)
    summary = registry.summary()
    print(f"Total Capes: {summary['total']}")
    print(f"Total Packs: {summary['total_packs']}")
    print(f"Pack Names: {summary['pack_names']}")
    print(f"By Pack: {summary['by_pack']}")
    print()

    print("=" * 60)
    print("All Capes")
    print("=" * 60)
    for cape in registry.all():
        print(f"  - {cape.id}: {cape.name}")
    print()

    print("=" * 60)
    print("Intent Matching Tests")
    print("=" * 60)
    test_queries = [
        "帮我写一份报告",
        "做一个PPT",
        "写一篇小红书笔记",
        "帮我起个标题",
        "写封邮件",
        "分析这份数据",
        "整理会议纪要",
        "写个广告文案",
    ]

    for query in test_queries:
        results = registry.match(query, top_k=2)
        if results:
            matches = ", ".join([f"{r['cape'].id}({r['score']:.2f})" for r in results])
            print(f"  '{query}' -> {matches}")
        else:
            print(f"  '{query}' -> No match")
