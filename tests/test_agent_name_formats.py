#!/usr/bin/env python3
"""Test script to verify agent name normalization functionality."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.core.agent_name_normalizer import AgentNameNormalizer

def test_agent_name_formats():
    """Test various agent name format conversions."""
    normalizer = AgentNameNormalizer()
    
    print("Testing Agent Name Format Conversions")
    print("=" * 50)
    
    # Test cases mapping TodoWrite format to Task format
    test_cases = [
        ("Research", "research"),
        ("Engineer", "engineer"),
        ("QA", "qa"),
        ("Documentation", "documentation"),
        ("Security", "security"),
        ("Ops", "ops"),
        ("Version Control", "version-control"),
        ("Data Engineer", "data-engineer"),
        # Also test lowercase inputs
        ("research", "research"),
        ("version-control", "version-control"),
        ("data-engineer", "data-engineer"),
    ]
    
    print("\nTodoWrite Format → Task Format:")
    print("-" * 50)
    
    all_passed = True
    for todo_format, expected_task_format in test_cases:
        actual = normalizer.to_task_format(todo_format)
        status = "✓" if actual == expected_task_format else "✗"
        
        if actual != expected_task_format:
            all_passed = False
            
        print(f"{status} '{todo_format}' → '{actual}' (expected: '{expected_task_format}')")
    
    print("\n" + "-" * 50)
    
    # Test reverse conversion
    print("\nTask Format → TodoWrite Format:")
    print("-" * 50)
    
    reverse_test_cases = [
        ("research", "Research"),
        ("engineer", "Engineer"),
        ("qa", "QA"),
        ("documentation", "Documentation"),
        ("security", "Security"),
        ("ops", "Ops"),
        ("version-control", "Version Control"),
        ("data-engineer", "Data Engineer"),
    ]
    
    for task_format, expected_todo_format in reverse_test_cases:
        actual = normalizer.from_task_format(task_format)
        status = "✓" if actual == expected_todo_format else "✗"
        
        if actual != expected_todo_format:
            all_passed = False
            
        print(f"{status} '{task_format}' → '{actual}' (expected: '{expected_todo_format}')")
    
    print("\n" + "=" * 50)
    
    if all_passed:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(test_agent_name_formats())