#!/usr/bin/env python3
"""
Test script for the new agent schema system.
Validates that all components work correctly after migration.
"""

import sys
import json
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.validation.agent_validator import AgentValidator, validate_all_agents
from claude_mpm.agents.agent_loader import (
    list_available_agents, 
    get_agent_prompt,
    validate_agent_files,
    reload_agents
)

def print_section(title: str):
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"{title}")
    print(f"{'=' * 60}")

def test_schema_validation():
    """Test schema validation functionality."""
    print_section("Testing Schema Validation")
    
    templates_dir = Path(__file__).parent.parent / "src" / "claude_mpm" / "agents" / "templates"
    valid_count, invalid_count, errors = validate_all_agents(templates_dir)
    
    print(f"✓ Valid agents: {valid_count}")
    print(f"{'✗' if invalid_count > 0 else '✓'} Invalid agents: {invalid_count}")
    
    if errors:
        print(f"\nValidation errors:")
        for error in errors:
            print(f"  - {error}")
    
    return invalid_count == 0

def test_agent_loading():
    """Test agent loading functionality."""
    print_section("Testing Agent Loading")
    
    # Force reload agents
    reload_agents()
    
    # List available agents
    agents = list_available_agents()
    
    print(f"\nFound {len(agents)} agents:")
    for agent_id, info in sorted(agents.items()):
        print(f"  - {agent_id:<20} {info['name']:<30} "
              f"[{info['category']}] {info['resource_tier']}")
    
    # Test loading each agent
    print(f"\nTesting agent prompt loading:")
    success_count = 0
    for agent_id in agents:
        try:
            prompt = get_agent_prompt(agent_id)
            if prompt:
                print(f"  ✓ {agent_id}: Loaded successfully ({len(prompt)} chars)")
                success_count += 1
            else:
                print(f"  ✗ {agent_id}: Failed to load prompt")
        except Exception as e:
            print(f"  ✗ {agent_id}: Error - {str(e)}")
    
    return success_count == len(agents)

def test_agent_metadata():
    """Test agent metadata and capabilities."""
    print_section("Testing Agent Metadata")
    
    agents = list_available_agents()
    
    # Check a few agents in detail
    test_agents = ["research", "engineer", "qa"]
    
    for agent_id in test_agents:
        if agent_id not in agents:
            print(f"✗ Agent '{agent_id}' not found")
            continue
        
        info = agents[agent_id]
        print(f"\n{agent_id} agent:")
        print(f"  Name: {info['name']}")
        print(f"  Model: {info['model']}")
        print(f"  Resource Tier: {info['resource_tier']}")
        print(f"  Tools: {', '.join(info['tools'][:5])}{'...' if len(info['tools']) > 5 else ''}")

def test_validation_rules():
    """Test specific validation rules."""
    print_section("Testing Validation Rules")
    
    validator = AgentValidator()
    
    # Test invalid agent (missing required fields)
    print(f"\nTesting invalid agent:")
    invalid_agent = {
        "id": "test",
        "version": "1.0.0"
        # Missing required fields
    }
    
    result = validator.validate_agent(invalid_agent)
    print(f"  Valid: {result.is_valid}")
    if result.errors:
        print(f"  Errors: {result.errors[0]}")
    
    # Test agent with too long instructions
    print(f"\nTesting instruction length limit:")
    long_agent = {
        "id": "test",
        "version": "1.0.0",
        "metadata": {
            "name": "Test Agent",
            "description": "Test agent for validation",
            "category": "engineering",
            "tags": ["test"]
        },
        "capabilities": {
            "model": "claude-sonnet-4-20250514",
            "tools": ["Read"],
            "resource_tier": "standard"
        },
        "instructions": "x" * 8001  # Exceeds 8000 char limit
    }
    
    result = validator.validate_agent(long_agent)
    print(f"  Valid: {result.is_valid}")
    if result.errors:
        print(f"  Error: {result.errors[0]}")

def test_backward_compatibility():
    """Test backward compatibility functions."""
    print_section("Testing Backward Compatibility")
    
    # Import backward-compatible functions
    from claude_mpm.agents.agent_loader import (
        get_research_agent_prompt,
        get_engineer_agent_prompt,
        get_qa_agent_prompt
    )
    
    functions = [
        ("get_research_agent_prompt", get_research_agent_prompt),
        ("get_engineer_agent_prompt", get_engineer_agent_prompt),
        ("get_qa_agent_prompt", get_qa_agent_prompt)
    ]
    
    for func_name, func in functions:
        try:
            prompt = func()
            print(f"  ✓ {func_name}: Works ({len(prompt)} chars)")
        except Exception as e:
            print(f"  ✗ {func_name}: Failed - {str(e)}")

def main():
    """Run all tests."""
    print(f"{'=' * 60}")
    print(f"Agent Schema System Test Suite")
    print(f"{'=' * 60}")
    
    all_passed = True
    
    # Run tests
    all_passed &= test_schema_validation()
    all_passed &= test_agent_loading()
    test_agent_metadata()
    test_validation_rules()
    test_backward_compatibility()
    
    # Summary
    print_section("Test Summary")
    if all_passed:
        print(f"✓ All critical tests passed!")
        print(f"✓ Agent schema system is working correctly")
    else:
        print(f"✗ Some tests failed")
        print(f"✗ Please check the errors above")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())