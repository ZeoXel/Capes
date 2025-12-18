#!/usr/bin/env python3
"""
Test Document Pack loading and functionality.

Validates that the document-pack (xlsx, docx, pptx, pdf) can be loaded
and all capes have required fields.
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from cape.registry.registry import CapeRegistry


def test_document_pack():
    """Test document-pack loading."""
    print("=" * 60)
    print("Testing Document Pack")
    print("=" * 60)

    # Create registry
    base_dir = Path(__file__).parent
    registry = CapeRegistry(
        capes_dir=base_dir / "capes",
        packs_dir=base_dir / "packs",
        skills_dir=base_dir / "skills",
        auto_load=True,
        use_embeddings=False,
    )

    # Test 1: Check pack is loaded
    print("\n=== Test 1: Pack Loading ===")
    packs = registry.get_packs()
    pack_names = [p["name"] for p in packs]
    print(f"  Loaded packs: {pack_names}")

    assert "document-pack" in pack_names, "document-pack should be loaded"
    print("  ✓ document-pack is loaded")

    # Test 2: Check document-pack capes
    print("\n=== Test 2: Document Pack Capes ===")
    doc_capes = registry.filter_by_pack("document-pack")
    cape_ids = [c.id for c in doc_capes]
    print(f"  Loaded capes: {cape_ids}")

    expected_capes = ["xlsx", "docx", "pptx", "pdf"]
    for cape_id in expected_capes:
        assert cape_id in cape_ids, f"document-pack should have {cape_id}"
        print(f"    ✓ {cape_id}")

    print(f"  ✓ All {len(expected_capes)} capes loaded")

    # Test 3: Validate cape structure
    print("\n=== Test 3: Cape Structure Validation ===")
    for cape in doc_capes:
        print(f"\n  Validating {cape.id}...")
        assert cape.id, "Cape missing id"
        print(f"    ID: {cape.id}")
        assert cape.name, "Cape missing name"
        print(f"    Name: {cape.name}")
        assert cape.description, "Cape missing description"
        print(f"    Description: {cape.description[:50]}...")

        # Check model adapters
        assert len(cape.model_adapters) > 0, "Cape has no model adapters"
        adapter_names = list(cape.model_adapters.keys())
        print(f"    Model Adapters: {adapter_names}")

        # Check has Claude adapter
        assert "claude" in cape.model_adapters, "Cape missing claude adapter"
        print(f"    ✓ Has Claude adapter")

        # Check has system prompt
        claude_adapter = cape.model_adapters["claude"]
        assert "system_prompt" in claude_adapter, "Claude adapter missing system_prompt"
        prompt_len = len(claude_adapter["system_prompt"])
        print(f"    ✓ Has system_prompt ({prompt_len} chars)")

    print("\n  ✓ All capes have valid structure")

    # Test 4: Intent matching
    print("\n=== Test 4: Intent Matching ===")
    test_queries = [
        ("创建一个Excel表格", "xlsx"),
        ("编辑Word文档", "docx"),
        ("制作PPT演示文稿", "pptx"),
        ("合并PDF文件", "pdf"),
    ]

    for query, expected_cape in test_queries:
        results = registry.match(query, top_k=3)
        if results:
            cape_ids = [r["cape"].id for r in results]
            matched = expected_cape in cape_ids
            status = "✓" if matched else "✗"
            top_match = results[0]["cape"].id
            print(f"  {status} '{query}' -> top: {top_match}, expected: {expected_cape}")
        else:
            print(f"  ✗ '{query}' -> No match")

    # Test 5: Registry summary
    print("\n=== Test 5: Registry Summary ===")
    summary = registry.summary()
    print(f"  Total Capes: {summary['total']}")
    print(f"  Total Packs: {summary['total_packs']}")
    print(f"  Pack Names: {summary['pack_names']}")
    print(f"  By Pack: {summary['by_pack']}")

    assert "document-pack" in summary["pack_names"]
    assert summary["by_pack"].get("document-pack", 0) >= 4
    print("  ✓ Summary includes document-pack")

    # All tests passed
    print("\n" + "=" * 60)
    print("ALL DOCUMENT PACK TESTS PASSED!")
    print("=" * 60)


def main():
    """Run document pack tests."""
    try:
        test_document_pack()
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
