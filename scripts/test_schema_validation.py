#!/usr/bin/env python3
"""Quick test script for schema validation."""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.validation.agent_validator import AgentValidator, validate_all_agents

def main():
    """Run schema validation tests."""
    print("=== Agent Schema Validation Test ===\n")
    
    # Test 1: Load and validate schema
    print("1. Testing schema file...")
    validator = AgentValidator()
    schema_info = validator.get_schema_info()
    print(f"   Schema loaded from: {schema_info['schema_path']}")
    print(f"   Title: {schema_info['schema_title']}")
    print(f"   Required fields: {', '.join(schema_info['required_fields'])}")
    print(f"   Total properties: {len(schema_info['properties'])}")
    
    # Test 2: Validate all agents
    print("\n2. Validating all agent templates...")
    agents_dir = Path(__file__).parent.parent / "src/claude_mpm/agents/templates"
    valid_count, invalid_count, errors = validate_all_agents(agents_dir)
    
    print(f"   Valid agents: {valid_count}")
    print(f"   Invalid agents: {invalid_count}")
    
    if errors:
        print("\n   Errors found:")
        for error in errors:
            print(f"   - {error}")
    
    # Test 3: Check specific agents
    print("\n3. Checking specific agent formats...")
    agent_files = ["engineer.json", "qa.json", "research.json", "documentation.json"]
    
    for agent_file in agent_files:
        agent_path = agents_dir / agent_file
        if agent_path.exists():
            with open(agent_path) as f:
                agent_data = json.load(f)
            
            agent_id = agent_data.get("id", "unknown")
            model = agent_data.get("capabilities", {}).get("model", "unknown")
            tier = agent_data.get("capabilities", {}).get("resource_tier", "unknown")
            instructions_len = len(agent_data.get("instructions", ""))
            
            print(f"\n   {agent_file}:")
            print(f"     - ID: {agent_id} (clean: {'✓' if not agent_id.endswith('_agent') else '✗'})")
            print(f"     - Model: {model}")
            print(f"     - Resource tier: {tier}")
            print(f"     - Instructions length: {instructions_len} chars")
            
            # Validate
            result = validator.validate_agent(agent_data)
            if result.is_valid:
                print(f"     - Validation: ✓ PASSED")
            else:
                print(f"     - Validation: ✗ FAILED")
                for error in result.errors:
                    print(f"       Error: {error}")
    
    # Test 4: Test invalid agent
    print("\n4. Testing invalid agent rejection...")
    invalid_agent = {
        "id": "test-invalid",  # Invalid ID format
        "name": "Test",
        "instructions": "x" * 9000  # Too long
    }
    
    result = validator.validate_agent(invalid_agent)
    if not result.is_valid:
        print("   ✓ Invalid agent correctly rejected")
        print(f"   Errors: {len(result.errors)}")
    else:
        print("   ✗ Invalid agent was not rejected!")
    
    # Summary
    print("\n=== Summary ===")
    if invalid_count == 0 and valid_count >= 8:
        print("✓ All tests PASSED - Schema validation is working correctly")
        return 0
    else:
        print("✗ Some tests FAILED - Please check the errors above")
        return 1

if __name__ == "__main__":
    sys.exit(main())