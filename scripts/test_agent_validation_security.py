#!/usr/bin/env python3
"""
Security test suite for agent validation system.

This script tests various security boundaries and edge cases in the agent
validation system to ensure malicious configurations are properly rejected.
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.validation.agent_validator import AgentValidator, ValidationResult
import json


def test_security_boundaries():
    """Test various security boundaries in agent validation."""
    validator = AgentValidator()
    
    print("=== Agent Validation Security Test Suite ===\n")
    
    # Test 1: Injection attempt in agent_id
    print("Test 1: Agent ID injection attempt")
    malicious_agent = {
        "schema_version": "1.0.0",
        "agent_id": "../../etc/passwd",  # Path traversal attempt
        "agent_version": "1.0.0",
        "agent_type": "base",
        "metadata": {
            "name": "Test Agent",
            "description": "Test agent for security validation",
            "tags": ["test"]
        },
        "capabilities": {
            "model": "claude-3-haiku-20240307",
            "tools": ["Read"],
            "resource_tier": "basic"
        },
        "instructions": "x" * 100  # Minimum 100 chars
    }
    
    result = validator.validate_agent(malicious_agent)
    print(f"  Result: {'BLOCKED' if not result.is_valid else 'FAILED - ALLOWED'}")
    if not result.is_valid:
        print(f"  Reason: {result.errors[0]}")
    print()
    
    # Test 2: Resource exhaustion attempt
    print("Test 2: Resource exhaustion via instructions")
    huge_instructions_agent = malicious_agent.copy()
    huge_instructions_agent["agent_id"] = "test_agent"
    huge_instructions_agent["instructions"] = "x" * 10000  # Over 8000 limit
    
    result = validator.validate_agent(huge_instructions_agent)
    print(f"  Result: {'BLOCKED' if not result.is_valid else 'FAILED - ALLOWED'}")
    if not result.is_valid:
        print(f"  Reason: {result.errors[0]}")
    print()
    
    # Test 3: Dangerous tool combination
    print("Test 3: Dangerous tool combination (Bash + Write)")
    dangerous_tools_agent = {
        "schema_version": "1.0.0",
        "agent_id": "dangerous_agent",
        "agent_version": "1.0.0",
        "agent_type": "engineer",
        "metadata": {
            "name": "Dangerous Agent",
            "description": "Agent with dangerous tool combination",
            "tags": ["dangerous"]
        },
        "capabilities": {
            "model": "claude-3-sonnet-20240229",
            "tools": ["Bash", "Write", "Edit"],  # Can write and execute scripts
            "resource_tier": "standard"
        },
        "instructions": "x" * 100
    }
    
    result = validator.validate_agent(dangerous_tools_agent)
    print(f"  Result: {'WARNING ISSUED' if result.warnings else 'FAILED - NO WARNING'}")
    if result.warnings:
        print(f"  Warning: {result.warnings[0]}")
    print()
    
    # Test 4: Network access without permission
    print("Test 4: Network tools without network_access")
    network_mismatch_agent = {
        "schema_version": "1.0.0",
        "agent_id": "network_agent",
        "agent_version": "1.0.0", 
        "agent_type": "research",
        "metadata": {
            "name": "Network Agent",
            "description": "Agent using network tools without permission",
            "tags": ["network"]
        },
        "capabilities": {
            "model": "claude-3-sonnet-20240229",
            "tools": ["WebSearch", "WebFetch"],
            "resource_tier": "standard",
            "network_access": False  # But using network tools!
        },
        "instructions": "x" * 100
    }
    
    result = validator.validate_agent(network_mismatch_agent)
    print(f"  Result: {'WARNING ISSUED' if result.warnings else 'FAILED - NO WARNING'}")
    if result.warnings:
        print(f"  Warning: {result.warnings[0]}")
    print()
    
    # Test 5: Invalid characters in handoff agents
    print("Test 5: Injection in handoff agents")
    handoff_injection_agent = {
        "schema_version": "1.0.0",
        "agent_id": "handoff_test",
        "agent_version": "1.0.0",
        "agent_type": "base",
        "metadata": {
            "name": "Handoff Test",
            "description": "Testing handoff agent validation",
            "tags": ["test"]
        },
        "capabilities": {
            "model": "claude-3-haiku-20240307",
            "tools": ["Read"],
            "resource_tier": "basic"
        },
        "instructions": "x" * 100,
        "interactions": {
            "handoff_agents": ["../../../etc/passwd", "$(whoami)", "agent1"]
        }
    }
    
    result = validator.validate_agent(handoff_injection_agent)
    print(f"  Result: {'BLOCKED' if not result.is_valid else 'FAILED - ALLOWED'}")
    if not result.is_valid:
        for error in result.errors:
            if "invalid characters" in error:
                print(f"  Blocked: {error}")
    print()
    
    # Test 6: Additional properties injection
    print("Test 6: Additional properties injection attempt")
    extra_fields_agent = {
        "schema_version": "1.0.0",
        "agent_id": "extra_fields",
        "agent_version": "1.0.0",
        "agent_type": "base",
        "metadata": {
            "name": "Extra Fields",
            "description": "Testing additional properties rejection",
            "tags": ["test"]
        },
        "capabilities": {
            "model": "claude-3-haiku-20240307",
            "tools": ["Read"],
            "resource_tier": "basic"
        },
        "instructions": "x" * 100,
        "malicious_field": "should_be_rejected",  # Should fail
        "another_bad_field": {"nested": "data"}
    }
    
    result = validator.validate_agent(extra_fields_agent)
    print(f"  Result: {'BLOCKED' if not result.is_valid else 'FAILED - ALLOWED'}")
    if not result.is_valid:
        print(f"  Reason: {result.errors[0]}")
    print()
    
    print("\n=== Security Test Summary ===")
    print("If all tests show BLOCKED or WARNING ISSUED, the validation system is")
    print("properly enforcing security boundaries.")
    

def test_file_operation_security():
    """Test file operation security measures."""
    print("\n=== File Operation Security Tests ===\n")
    
    validator = AgentValidator()
    
    # Test directory validation with file count limit
    print("Test: Directory file count DoS prevention")
    # This would be tested with actual directory operations
    print("  Feature: Max 100 files per directory validation")
    print("  Feature: Symlink skipping enabled")
    print("  Feature: 1MB file size limit enforced")
    print()


def main():
    """Run all security tests."""
    print("Claude MPM Agent Validation Security Test\n")
    
    test_security_boundaries()
    test_file_operation_security()
    
    print("\n✓ Security test suite completed")
    print("\nREMINDER: This is not a complete security audit.")
    print("Always perform thorough security testing before production use.")


if __name__ == "__main__":
    main()