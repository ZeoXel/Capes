#!/usr/bin/env python3
"""
Test importing Claude's document-skills into Cape system.

Tests:
1. EnhancedSkillImporter can import xlsx, docx, pptx, pdf skills
2. Verify all metadata is correctly extracted
3. Check scripts detection and dependency analysis
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from cape.importers import import_skill_enhanced, EnhancedSkillImporter

# Path to Claude Skills repository
SKILLS_REPO = Path("/Users/g/Desktop/探索/Claude skills/skills")
DOCUMENT_SKILLS_PATH = SKILLS_REPO / "document-skills"


def test_import_xlsx():
    """Test importing xlsx skill."""
    print("\n=== Testing xlsx Skill Import ===")

    skill_path = DOCUMENT_SKILLS_PATH / "xlsx"
    print(f"  Path: {skill_path}")

    cape = import_skill_enhanced(skill_path)

    print(f"  ID: {cape.id}")
    print(f"  Name: {cape.name}")
    print(f"  Description: {cape.description[:80]}...")
    print(f"  Tags: {cape.metadata.tags}")

    # Check model adapters
    print(f"  Model Adapters: {list(cape.model_adapters.keys())}")

    # Check for code adapter
    if "code" in cape.model_adapters:
        code = cape.model_adapters["code"]
        print(f"  Scripts: {code.get('scripts', [])}")
        print(f"  Dependencies: {code.get('dependencies', [])}")
        print(f"  Runtime: {code.get('runtime')}")

    assert cape.id == "xlsx", f"Expected id 'xlsx', got '{cape.id}'"
    assert cape.description, "Missing description"
    print("  ✓ xlsx import successful!")
    return cape


def test_import_docx():
    """Test importing docx skill."""
    print("\n=== Testing docx Skill Import ===")

    skill_path = DOCUMENT_SKILLS_PATH / "docx"
    print(f"  Path: {skill_path}")

    cape = import_skill_enhanced(skill_path)

    print(f"  ID: {cape.id}")
    print(f"  Name: {cape.name}")
    print(f"  Description: {cape.description[:80]}...")

    if "code" in cape.model_adapters:
        code = cape.model_adapters["code"]
        print(f"  Scripts: {code.get('scripts', [])}")
        print(f"  Dependencies: {code.get('dependencies', [])}")

    assert cape.id == "docx", f"Expected id 'docx', got '{cape.id}'"
    print("  ✓ docx import successful!")
    return cape


def test_import_pptx():
    """Test importing pptx skill."""
    print("\n=== Testing pptx Skill Import ===")

    skill_path = DOCUMENT_SKILLS_PATH / "pptx"
    print(f"  Path: {skill_path}")

    cape = import_skill_enhanced(skill_path)

    print(f"  ID: {cape.id}")
    print(f"  Name: {cape.name}")
    print(f"  Description: {cape.description[:80]}...")

    if "code" in cape.model_adapters:
        code = cape.model_adapters["code"]
        print(f"  Scripts: {code.get('scripts', [])}")
        print(f"  Dependencies: {code.get('dependencies', [])}")

    assert cape.id == "pptx", f"Expected id 'pptx', got '{cape.id}'"
    print("  ✓ pptx import successful!")
    return cape


def test_import_pdf():
    """Test importing pdf skill."""
    print("\n=== Testing pdf Skill Import ===")

    skill_path = DOCUMENT_SKILLS_PATH / "pdf"
    print(f"  Path: {skill_path}")

    cape = import_skill_enhanced(skill_path)

    print(f"  ID: {cape.id}")
    print(f"  Name: {cape.name}")
    print(f"  Description: {cape.description[:80]}...")

    if "code" in cape.model_adapters:
        code = cape.model_adapters["code"]
        print(f"  Scripts: {code.get('scripts', [])}")
        print(f"  Dependencies: {code.get('dependencies', [])}")

    assert cape.id == "pdf", f"Expected id 'pdf', got '{cape.id}'"
    print("  ✓ pdf import successful!")
    return cape


def test_import_all():
    """Test importing all document skills at once."""
    print("\n=== Testing Batch Import ===")

    importer = EnhancedSkillImporter()
    capes = importer.import_all(DOCUMENT_SKILLS_PATH)

    print(f"  Imported {len(capes)} skills")
    for cape in capes:
        print(f"    - {cape.id}: {cape.name}")

    assert len(capes) == 4, f"Expected 4 skills, got {len(capes)}"
    print("  ✓ Batch import successful!")
    return capes


def print_cape_summary(cape):
    """Print detailed summary of a Cape."""
    print(f"\n{'='*60}")
    print(f"Cape: {cape.id}")
    print(f"{'='*60}")
    print(f"Name: {cape.name}")
    print(f"Version: {cape.version}")
    print(f"Description: {cape.description}")
    print(f"Tags: {cape.metadata.tags}")
    print(f"\nExecution:")
    print(f"  Type: {cape.execution.type}")
    print(f"  Entrypoint: {cape.execution.entrypoint}")
    print(f"  Timeout: {cape.execution.timeout_seconds}s")
    print(f"\nModel Adapters: {list(cape.model_adapters.keys())}")
    if "code" in cape.model_adapters:
        code = cape.model_adapters["code"]
        print(f"\nCode Adapter:")
        print(f"  Scripts: {code.get('scripts', [])}")
        print(f"  Dependencies: {code.get('dependencies', [])}")
        print(f"  Runtime: {code.get('runtime')}")


def main():
    """Run all import tests."""
    print("=" * 60)
    print("Cape Document Skills Import Test")
    print("=" * 60)
    print(f"Skills Repository: {SKILLS_REPO}")
    print(f"Document Skills: {DOCUMENT_SKILLS_PATH}")

    if not DOCUMENT_SKILLS_PATH.exists():
        print(f"\n❌ ERROR: Path not found: {DOCUMENT_SKILLS_PATH}")
        sys.exit(1)

    try:
        # Test individual imports
        xlsx_cape = test_import_xlsx()
        docx_cape = test_import_docx()
        pptx_cape = test_import_pptx()
        pdf_cape = test_import_pdf()

        # Test batch import
        all_capes = test_import_all()

        # Print detailed summary
        print("\n" + "=" * 60)
        print("DETAILED SUMMARIES")
        print("=" * 60)
        for cape in [xlsx_cape, docx_cape, pptx_cape, pdf_cape]:
            print_cape_summary(cape)

        print("\n" + "=" * 60)
        print("ALL DOCUMENT SKILLS IMPORTED SUCCESSFULLY!")
        print("=" * 60)

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
