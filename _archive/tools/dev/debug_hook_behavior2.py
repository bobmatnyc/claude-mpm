#!/usr/bin/env python3
"""Debug script #2 for agent name normalization behavior."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from claude_mpm.core.agent_name_normalizer import AgentNameNormalizer

# This script has been updated to use AgentNameNormalizer
# instead of the deprecated TodoAgentPrefixHook

print("Agent Name Normalization Debug #2")
print("=" * 50)

# Test all canonical names
print("\nCanonical Agent Names:")
for key, name in AgentNameNormalizer.CANONICAL_NAMES.items():
    prefix = AgentNameNormalizer.to_todo_prefix(name)
    print(f"  {key:20} -> {name:20} -> {prefix}")

# Test aliases
print("\nAgent Aliases:")
test_aliases = [
    "researcher",
    "dev",
    "developer",
    "quality",
    "sec",
    "docs",
    "devops",
    "vcs",
    "data",
    "arch",
    "project_manager",
]
for alias in test_aliases:
    normalized = AgentNameNormalizer.normalize(alias)
    prefix = AgentNameNormalizer.to_todo_prefix(alias)
    print(f"  {alias:20} -> {normalized:20} -> {prefix}")

# Test edge cases
print("\nEdge Cases:")
edge_cases = ["", None, "unknown", "random_agent", "UPPERCASE", "MiXeD-CaSe"]
for case in edge_cases:
    try:
        normalized = AgentNameNormalizer.normalize(case or "")
        prefix = AgentNameNormalizer.to_todo_prefix(case or "")
        print(f"  {case!s:20} -> {normalized:20} -> {prefix}")
    except Exception as e:
        print(f"  {case!s:20} -> Error: {e}")

print("\nDebug complete!")
