#!/usr/bin/env python3
"""Debug script to understand agent name normalization behavior."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from claude_mpm.core.agent_name_normalizer import AgentNameNormalizer

# Test cases
test_todos = [
    "Research best practices for testing",
    "Implement new feature",
    "Test the API endpoints",
    "Document the process",
    "[Engineer] Fix bug",
    "[QA] Run tests",
]

print("Testing Agent Name Normalization")
print("-" * 50)

for todo in test_todos:
    # Check if todo already has a prefix
    import re

    has_prefix = bool(re.match(r"^\[[^\]]+\]", todo))

    if has_prefix:
        print(f"Todo: '{todo}'")
        print(f"  Already has prefix: Yes")
    else:
        # Try to determine agent based on keywords
        todo_lower = todo.lower()
        agent = "Engineer"  # default

        if "research" in todo_lower or "analyze" in todo_lower:
            agent = "Research"
        elif "test" in todo_lower or "qa" in todo_lower:
            agent = "QA"
        elif "document" in todo_lower:
            agent = "Documentation"
        elif "deploy" in todo_lower:
            agent = "Ops"
        elif "security" in todo_lower or "audit" in todo_lower:
            agent = "Security"

        prefix = AgentNameNormalizer.to_todo_prefix(agent)
        new_todo = f"{prefix} {todo}"

        print(f"Todo: '{todo}'")
        print(f"  Detected agent: {agent}")
        print(f"  With prefix: '{new_todo}'")

    print()

print("\nAgent Name Normalization Examples:")
print("-" * 50)
test_names = ["research", "ENGINEER", "qa", "Version Control", "data-engineer"]
for name in test_names:
    normalized = AgentNameNormalizer.normalize(name)
    key = AgentNameNormalizer.to_key(name)
    prefix = AgentNameNormalizer.to_todo_prefix(name)
    print(f"Input: '{name}'")
    print(f"  Normalized: {normalized}")
    print(f"  Key: {key}")
    print(f"  Prefix: {prefix}")
    print()
