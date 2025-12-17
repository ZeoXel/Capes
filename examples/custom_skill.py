#!/usr/bin/env python3
"""
Example of creating and using a custom skill.

This example shows how to:
1. Create a new skill from scratch
2. Register it with the orchestrator
3. Use it with the agent
"""

from pathlib import Path
import tempfile


def create_custom_skill():
    """Create a custom skill programmatically."""

    skill_content = '''---
name: json-formatter
description: >
  Format, validate, and transform JSON data. Use when user asks to
  "format JSON", "validate JSON", "pretty print JSON", "minify JSON",
  or any JSON manipulation tasks.
metadata:
  file_types:
    - .json
---

# JSON Formatter Skill

Format and validate JSON data.

## Capabilities

1. **Pretty Print** - Format JSON with proper indentation
2. **Minify** - Compress JSON by removing whitespace
3. **Validate** - Check if JSON is valid
4. **Transform** - Convert between formats

## Usage

### Pretty Print

```python
import json

data = '{"name":"John","age":30}'
formatted = json.dumps(json.loads(data), indent=2)
print(formatted)
```

### Validate JSON

```python
import json

def is_valid_json(text):
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        return False
```

## Output Format

When formatting JSON, use 2-space indentation:

```json
{
  "name": "John",
  "age": 30,
  "address": {
    "city": "New York"
  }
}
```
'''

    # Create a temporary skill directory
    skill_dir = Path(tempfile.mkdtemp()) / "json-formatter"
    skill_dir.mkdir(parents=True)

    # Write the skill file
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(skill_content)

    print(f"Created custom skill at: {skill_dir}")
    return skill_dir.parent


def demo_custom_skill():
    """Demonstrate using a custom skill."""
    from langchain_skills import SkillOrchestrator, SkillLoader

    # Create the custom skill
    custom_skills_dir = create_custom_skill()

    # Create orchestrator with custom skills
    orchestrator = SkillOrchestrator(
        skills_dir=custom_skills_dir,
        use_embeddings=False,  # Skip embeddings for demo
    )

    # List skills
    print("\nRegistered Skills:")
    for skill in orchestrator.list_skills():
        print(f"  - {skill['name']}")

    # Test matching
    query = "format this JSON: {'name':'test'}"
    results = orchestrator.find_skills(query)

    print(f"\nQuery: {query}")
    print("Matches:")
    for r in results:
        print(f"  - {r.skill.name}: {r.score:.3f}")


def demo_dynamic_skill():
    """Demonstrate adding a skill dynamically."""
    from langchain_skills import SkillOrchestrator, Skill, SkillMetadata, SkillType
    from pathlib import Path

    # Create orchestrator with existing skills
    skills_dir = Path(__file__).parent.parent / "skills"
    orchestrator = SkillOrchestrator(skills_dir=skills_dir)

    print(f"Initial skills: {len(orchestrator.registry)}")

    # Create a dynamic skill (in-memory)
    metadata = SkillMetadata(
        name="greeting-skill",
        description="Generate friendly greetings. Use when user wants a greeting or welcome message.",
        skill_type=SkillType.INSTRUCTION,
        trigger_keywords=["greeting", "hello", "welcome", "hi"],
    )

    skill = Skill(
        metadata=metadata,
        path=Path("/tmp/greeting-skill"),  # Doesn't need to exist for instruction skills
        body_content="""
# Greeting Skill

Generate warm, friendly greetings.

## Instructions

When greeting someone:
1. Be warm and welcoming
2. Use their name if provided
3. Keep it concise but friendly

## Examples

- "Hello! Welcome aboard!"
- "Hi [Name]! Great to see you!"
- "Welcome! How can I help you today?"
""",
    )

    # Add to orchestrator
    orchestrator.add_skill(skill)
    print(f"After adding: {len(orchestrator.registry)} skills")

    # Test matching
    results = orchestrator.find_skills("say hello to me")
    print("\nMatching 'say hello to me':")
    for r in results:
        print(f"  - {r.skill.name}: {r.score:.3f}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "dynamic":
        demo_dynamic_skill()
    else:
        demo_custom_skill()
