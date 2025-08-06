#!/usr/bin/env python3
"""Test the dynamic agent capabilities generation.

This script tests Phase 2 implementation:
1. ContentAssembler integration
2. Template placeholder substitution
3. Deployment with fresh generation
"""

import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.deployed_agent_discovery import DeployedAgentDiscovery
from claude_mpm.services.agent_capabilities_generator import AgentCapabilitiesGenerator
from claude_mpm.services.framework_claude_md_generator.content_assembler import ContentAssembler

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_agent_discovery():
    """Test the deployed agent discovery service."""
    print("\n=== Testing Agent Discovery ===")
    discovery = DeployedAgentDiscovery()
    agents = discovery.discover_deployed_agents()
    
    print(f"Found {len(agents)} deployed agents:")
    for agent in agents:
        print(f"  - {agent['id']} ({agent['name']}): {agent['description'][:50]}...")
    
    return agents


def test_capabilities_generator(agents):
    """Test the capabilities content generator."""
    print("\n=== Testing Capabilities Generator ===")
    generator = AgentCapabilitiesGenerator()
    content = generator.generate_capabilities_section(agents)
    
    print("Generated content:")
    print("-" * 80)
    print(content)
    print("-" * 80)
    
    return content


def test_content_assembler():
    """Test the ContentAssembler with template substitution."""
    print("\n=== Testing Content Assembler ===")
    assembler = ContentAssembler()
    
    # Test content with placeholder
    test_content = """
# Test Document

## Static Section
This is static content.

{{capabilities-list}}

## Another Static Section
More static content.
"""
    
    # Apply template substitution
    processed_content = assembler.apply_template_variables(test_content)
    
    print("Processed content:")
    print("-" * 80)
    print(processed_content)
    print("-" * 80)
    
    # Verify placeholder was replaced
    if "{{capabilities-list}}" in processed_content:
        print("ERROR: Placeholder was not replaced!")
        return False
    else:
        print("SUCCESS: Placeholder was replaced with dynamic content")
        return True


def test_full_integration():
    """Test the full integration with INSTRUCTIONS.md template."""
    print("\n=== Testing Full Integration ===")
    
    # Read the actual INSTRUCTIONS.md template
    template_path = Path(__file__).parent.parent / "src/claude_mpm/agents/INSTRUCTIONS.md"
    if not template_path.exists():
        print(f"ERROR: Template not found at {template_path}")
        return False
    
    with open(template_path, 'r') as f:
        template_content = f.read()
    
    # Check if placeholder exists
    if "{{capabilities-list}}" not in template_content:
        print("ERROR: Template does not contain {{capabilities-list}} placeholder")
        return False
    
    print("SUCCESS: Template contains placeholder")
    
    # Process with ContentAssembler
    assembler = ContentAssembler()
    processed_content = assembler.apply_template_variables(template_content)
    
    # Verify processing
    if "{{capabilities-list}}" in processed_content:
        print("ERROR: Integration failed - placeholder not replaced")
        return False
    
    if "**Core Agents**:" in processed_content:
        print("SUCCESS: Dynamic capabilities were generated and inserted")
        return True
    else:
        print("ERROR: Dynamic content not found in processed template")
        return False


def main():
    """Run all tests."""
    print("Testing Dynamic Agent Capabilities Implementation")
    print("=" * 80)
    
    # Test individual components
    agents = test_agent_discovery()
    if not agents:
        print("\nWARNING: No agents discovered, but continuing with test")
    
    if agents:
        test_capabilities_generator(agents)
    
    # Test integration
    assembler_success = test_content_assembler()
    integration_success = test_full_integration()
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY:")
    print(f"  - Agent Discovery: {'PASS' if agents else 'WARN (no agents found)'}")
    print(f"  - Content Assembler: {'PASS' if assembler_success else 'FAIL'}")
    print(f"  - Full Integration: {'PASS' if integration_success else 'FAIL'}")
    
    overall_success = assembler_success and integration_success
    print(f"\nOVERALL: {'PASS' if overall_success else 'FAIL'}")
    
    return 0 if overall_success else 1


if __name__ == "__main__":
    sys.exit(main())