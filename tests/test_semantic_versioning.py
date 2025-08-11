#!/usr/bin/env python3
"""Test semantic versioning implementation in agent deployment service."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.deployment import AgentDeploymentService

def test_version_parsing():
    """Test version parsing functionality."""
    service = AgentDeploymentService()
    
    test_cases = [
        # (input, expected_tuple)
        (5, (0, 5, 0)),
        ("5", (0, 5, 0)),
        ("2.1.0", (2, 1, 0)),
        ("v2.1.0", (2, 1, 0)),
        ("invalid", (0, 0, 0)),
        (None, (0, 0, 0)),
    ]
    
    print("Testing version parsing:")
    for input_val, expected in test_cases:
        result = service._parse_version(input_val)
        status = "✓" if result == expected else "✗"
        print(f"  {status} Input: {input_val!r} -> {result} (expected {expected})")
    
def test_version_display():
    """Test version display formatting."""
    service = AgentDeploymentService()
    
    test_cases = [
        # (input_tuple, expected_string)
        ((2, 1, 0), "2.1.0"),
        ((0, 5, 0), "0.5.0"),
        ((1, 0, 0), "1.0.0"),
        ((10, 20, 30), "10.20.30"),
    ]
    
    print("\nTesting version display:")
    for input_tuple, expected in test_cases:
        result = service._format_version_display(input_tuple)
        status = "✓" if result == expected else "✗"
        print(f"  {status} Input: {input_tuple} -> {result!r} (expected {expected!r})")

def test_version_comparison():
    """Test semantic version comparison logic."""
    
    def compare_versions(v1: tuple, v2: tuple) -> int:
        """Compare two version tuples. Returns -1 if v1 < v2, 0 if equal, 1 if v1 > v2."""
        for a, b in zip(v1, v2):
            if a < b:
                return -1
            elif a > b:
                return 1
        return 0
    
    test_cases = [
        # (v1, v2, expected_result)
        ((2, 1, 0), (2, 0, 0), 1),  # 2.1.0 > 2.0.0
        ((2, 1, 0), (1, 9, 9), 1),  # 2.1.0 > 1.9.9
        ((2, 1, 0), (2, 1, 0), 0),  # 2.1.0 == 2.1.0
        ((2, 1, 0), (2, 1, 1), -1), # 2.1.0 < 2.1.1
        ((0, 5, 0), (2, 1, 0), -1), # 0.5.0 < 2.1.0
    ]
    
    print("\nTesting version comparison:")
    for v1, v2, expected in test_cases:
        result = compare_versions(v1, v2)
        status = "✓" if result == expected else "✗"
        op = ">" if result > 0 else "==" if result == 0 else "<"
        print(f"  {status} {v1} {op} {v2} (expected {'>' if expected > 0 else '==' if expected == 0 else '<'})")

if __name__ == "__main__":
    test_version_parsing()
    test_version_display()
    test_version_comparison()
    print("\nSemantic versioning tests completed!")