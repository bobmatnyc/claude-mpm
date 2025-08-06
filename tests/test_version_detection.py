#!/usr/bin/env python3
"""Test version format detection logic."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agent_deployment import AgentDeploymentService

def test_version_detection():
    """Test the version format detection logic."""
    service = AgentDeploymentService()
    
    test_cases = [
        # (version_string, expected_is_old_format, description)
        ("0002-0005", True, "Serial format"),
        ("1234-5678", True, "Serial format with larger numbers"),
        ("2.1.0", False, "Semantic version"),
        ("v2.1.0", False, "Semantic version with v prefix"),
        ("1.0.0", False, "Simple semantic version"),
        ("", True, "Empty version string"),
        (None, True, "None/missing version"),
        ("5", True, "Single number"),
        ("version 5", True, "Text with number"),
    ]
    
    print("Testing version format detection:\n")
    
    all_passed = True
    for version_str, expected_is_old, description in test_cases:
        # Handle None case
        if version_str is None:
            result = True  # None is always old format
        else:
            result = service._is_old_version_format(version_str)
        
        status = "✓ PASS" if result == expected_is_old else "✗ FAIL"
        print(f"{status} '{version_str}' -> is_old={result} ({description})")
        
        if result != expected_is_old:
            all_passed = False
            print(f"     Expected: {expected_is_old}, Got: {result}")
    
    print(f"\n{'✅ All tests passed!' if all_passed else '❌ Some tests failed!'}")
    
    # Test version parsing
    print("\n\nTesting version parsing:\n")
    
    parse_cases = [
        # (version_value, expected_tuple, description)
        (5, (0, 5, 0), "Integer version"),
        ("5", (0, 5, 0), "String integer"),
        ("2.1.0", (2, 1, 0), "Semantic version"),
        ("v2.1.0", (2, 1, 0), "Semantic with v prefix"),
        ("0002-0005", (0, 2, 0), "Serial format (takes first number)"),
        ("", (0, 0, 0), "Empty string"),
        (None, (0, 0, 0), "None value"),
    ]
    
    for version_val, expected_tuple, description in parse_cases:
        result = service._parse_version(version_val)
        status = "✓ PASS" if result == expected_tuple else "✗ FAIL"
        print(f"{status} {version_val} -> {result} ({description})")
        
        if result != expected_tuple:
            print(f"     Expected: {expected_tuple}")

if __name__ == "__main__":
    test_version_detection()