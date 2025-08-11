#!/usr/bin/env python3
"""Test script for AgentNameNormalizer todo prefix functionality."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.agent_name_normalizer import AgentNameNormalizer


def test_todo_prefix():
    """Test the AgentNameNormalizer todo prefix functionality with various inputs."""
    
    print(f"Testing AgentNameNormalizer Todo Prefix")
    print("-" * 50)
    
    # Test cases for agent name normalization and todo prefix generation
    test_cases = [
        # Standard agent names
        ("research", "[Research]"),
        ("engineer", "[Engineer]"),
        ("qa", "[QA]"),
        ("security", "[Security]"),
        ("documentation", "[Documentation]"),
        ("ops", "[Ops]"),
        ("version_control", "[Version Control]"),
        ("data_engineer", "[Data Engineer]"),
        ("architect", "[Architect]"),
        ("pm", "[PM]"),
        
        # Case variations
        ("Research", "[Research]"),
        ("ENGINEER", "[Engineer]"),
        ("Qa", "[QA]"),
        
        # Aliases
        ("researcher", "[Research]"),
        ("dev", "[Engineer]"),
        ("developer", "[Engineer]"),
        ("quality", "[QA]"),
        ("sec", "[Security]"),
        ("docs", "[Documentation]"),
        ("doc", "[Documentation]"),
        ("devops", "[Ops]"),
        ("vcs", "[Version Control]"),
        ("data", "[Data Engineer]"),
        ("arch", "[Architect]"),
        ("project_manager", "[PM]"),
        
        # Unknown/default
        ("unknown_agent", "[Engineer]"),
        ("", "[Engineer]"),
        (None, "[Engineer]"),
    ]
    
    print("\nTesting agent name to todo prefix conversion:")
    for agent_name, expected_prefix in test_cases:
        actual_prefix = AgentNameNormalizer.to_todo_prefix(agent_name or "")
        status = "✓" if actual_prefix == expected_prefix else "✗"
        print(f"  {status} {str(agent_name):20s} -> {actual_prefix:20s} (expected: {expected_prefix})")
        if actual_prefix != expected_prefix:
            print(f"    ERROR: Expected '{expected_prefix}' but got '{actual_prefix}'")
    
    # Test normalization
    print("\nTesting agent name normalization:")
    normalize_tests = [
        ("research", "Research"),
        ("ENGINEER", "Engineer"),
        ("qa", "QA"),
        ("project_manager", "PM"),
        ("unknown", "Engineer"),
    ]
    
    for input_name, expected_name in normalize_tests:
        actual_name = AgentNameNormalizer.normalize(input_name)
        status = "✓" if actual_name == expected_name else "✗"
        print(f"  {status} {input_name:20s} -> {actual_name:20s} (expected: {expected_name})")
    
    # Test key conversion
    print("\nTesting agent name to key conversion:")
    key_tests = [
        ("Research", "research"),
        ("Version Control", "version_control"),
        ("Data Engineer", "data_engineer"),
        ("PM", "pm"),
    ]
    
    for input_name, expected_key in key_tests:
        actual_key = AgentNameNormalizer.to_key(input_name)
        status = "✓" if actual_key == expected_key else "✗"
        print(f"  {status} {input_name:20s} -> {actual_key:20s} (expected: {expected_key})")
    
    print("\nTest complete!")


if __name__ == "__main__":
    test_todo_prefix()