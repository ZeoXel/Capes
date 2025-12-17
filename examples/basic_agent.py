#!/usr/bin/env python3
"""
Basic example of using the LangChain Skills system.

This example shows how to:
1. Create a skill-enabled agent
2. Route requests to appropriate skills
3. Execute skills with user input
"""

import os
from pathlib import Path

# Ensure OPENAI_API_KEY is set
if not os.getenv("OPENAI_API_KEY"):
    print("Please set OPENAI_API_KEY environment variable")
    print("export OPENAI_API_KEY='your-key-here'")
    exit(1)


def main():
    """Run basic agent example."""
    from langchain_skills import create_skills_agent

    # Get skills directory (relative to this file)
    skills_dir = Path(__file__).parent.parent / "skills"

    print(f"Loading skills from: {skills_dir}")
    print("-" * 50)

    # Create the agent
    agent = create_skills_agent(
        skills_dir=skills_dir,
        verbose=True,  # Show agent reasoning
    )

    # Example queries
    queries = [
        "Review this Python code: def add(a,b): return a+b",
        "What are Python best practices for error handling?",
        "How do I extract text from a PDF file?",
    ]

    for query in queries:
        print(f"\n{'='*50}")
        print(f"Query: {query}")
        print("=" * 50)

        result = agent.invoke({"input": query})
        print(f"\nResponse:\n{result['output']}")


def demo_orchestrator():
    """Demo using the orchestrator directly."""
    from langchain_skills import SkillOrchestrator

    skills_dir = Path(__file__).parent.parent / "skills"

    # Create orchestrator
    orchestrator = SkillOrchestrator(
        skills_dir=skills_dir,
        use_embeddings=True,
    )

    # List available skills
    print("Available Skills:")
    for skill in orchestrator.list_skills():
        print(f"  - {skill['name']} ({skill['type']})")
        print(f"    {skill['description']}")
        print()

    # Find matching skills
    query = "review my Python code for best practices"
    print(f"Query: {query}")
    print("-" * 30)

    results = orchestrator.find_skills(query, top_k=3)
    for result in results:
        print(f"  {result.skill.name}: {result.score:.3f} ({result.match_type})")


def demo_matcher():
    """Demo the intent matcher."""
    from langchain_skills import SkillLoader, IntentMatcher

    skills_dir = Path(__file__).parent.parent / "skills"

    # Load skills
    loader = SkillLoader(skills_dir)
    skills = loader.load_all()

    print(f"Loaded {len(skills)} skills")

    # Create matcher
    matcher = IntentMatcher(use_embeddings=True)
    matcher.index_skills(skills)

    # Test queries
    test_queries = [
        "analyze this code",
        "extract text from document.pdf",
        "what is the singleton pattern in Python",
        "help me with type hints",
    ]

    for query in test_queries:
        print(f"\nQuery: '{query}'")
        results = matcher.match(query, skills, top_k=2)
        for r in results:
            print(f"  → {r.skill.name}: {r.score:.3f}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "orchestrator":
            demo_orchestrator()
        elif sys.argv[1] == "matcher":
            demo_matcher()
        else:
            print(f"Unknown command: {sys.argv[1]}")
            print("Usage: python basic_agent.py [orchestrator|matcher]")
    else:
        main()
