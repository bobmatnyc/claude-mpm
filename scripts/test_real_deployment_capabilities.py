#!/usr/bin/env python3
"""Test dynamic capabilities with real deployment flow."""

import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agent_deployment import AgentDeploymentService
from claude_mpm.services.deployed_agent_discovery import DeployedAgentDiscovery
from claude_mpm.services.agent_capabilities_generator import AgentCapabilitiesGenerator
from claude_mpm.services.framework_claude_md_generator.content_assembler import ContentAssembler


def test_real_deployment_flow():
    """Test the complete flow with real deployed agents."""
    print("Testing Dynamic Capabilities with Real Deployment")
    print("=" * 80)
    
    # Step 1: Check current deployed agents
    print("\n1. Discovering deployed agents...")
    discovery = DeployedAgentDiscovery()
    agents = discovery.discover_deployed_agents()
    print(f"   Found {len(agents)} agents")
    for agent in agents[:3]:  # Show first 3
        print(f"   - {agent['id']}: {agent['name']}")
    
    # Step 2: Generate capabilities content
    print("\n2. Generating capabilities content...")
    generator = AgentCapabilitiesGenerator()
    capabilities = generator.generate_capabilities_section(agents)
    print("   Generated content preview:")
    print("   " + "-" * 60)
    lines = capabilities.split('\n')[:10]  # First 10 lines
    for line in lines:
        print(f"   {line}")
    print("   ...")
    
    # Step 3: Test content assembly with real template
    print("\n3. Testing content assembly...")
    assembler = ContentAssembler()
    
    # Load real INSTRUCTIONS.md template
    template_path = Path(__file__).parent.parent / "src/claude_mpm/agents/INSTRUCTIONS.md"
    if template_path.exists():
        with open(template_path, 'r') as f:
            template_content = f.read()
        
        # Check for placeholder
        if "{{capabilities-list}}" in template_content:
            print("   ✓ Template contains placeholder")
            
            # Process template
            processed = assembler.apply_template_variables(template_content)
            
            # Verify replacement
            if "{{capabilities-list}}" not in processed:
                print("   ✓ Placeholder successfully replaced")
                if "**Core Agents**:" in processed:
                    print("   ✓ Dynamic content inserted")
                else:
                    print("   ✗ Dynamic content not found")
            else:
                print("   ✗ Placeholder not replaced")
        else:
            print("   ✗ Template missing placeholder")
    else:
        print("   ✗ Template file not found")
    
    # Step 4: Test with deployment service
    print("\n4. Testing with deployment service...")
    deployment_service = AgentDeploymentService()
    
    # Get deployment stats to verify agents are available
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        result = deployment_service.deploy_agents(str(temp_path))
        print(f"   Deployment test: {result['deployed']} deployed, {result['skipped']} skipped")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY:")
    print(f"  - Agents discovered: {len(agents)}")
    print(f"  - Capabilities generated: {'Yes' if capabilities else 'No'}")
    print(f"  - Template processing: {'Working' if template_path.exists() else 'Template not found'}")
    

def test_edge_cases():
    """Test edge cases for dynamic capabilities."""
    print("\n\nTesting Edge Cases")
    print("=" * 80)
    
    # Test 1: Empty agent list
    print("\n1. Testing with empty agent list...")
    generator = AgentCapabilitiesGenerator()
    empty_content = generator.generate_capabilities_section([])
    if "*Generated from 0 deployed agents*" in empty_content:
        print("   ✓ Handles empty agent list gracefully")
    else:
        print("   ✗ Empty agent list not handled properly")
    
    # Test 2: Agent with minimal info
    print("\n2. Testing with minimal agent info...")
    minimal_agent = {
        'id': 'test',
        'name': 'Test Agent',
        'description': '',
        'specializations': [],
        'capabilities': {},
        'source_tier': 'system',
        'tools': []
    }
    content = generator.generate_capabilities_section([minimal_agent])
    if "**Test Agent**:" in content:
        print("   ✓ Handles minimal agent info")
    else:
        print("   ✗ Minimal agent not rendered properly")
    
    # Test 3: Mixed tier agents
    print("\n3. Testing with mixed tier agents...")
    mixed_agents = [
        {
            'id': 'sys1',
            'name': 'System Agent',
            'description': 'System tier',
            'specializations': ['system'],
            'source_tier': 'system',
            'capabilities': {},
            'tools': []
        },
        {
            'id': 'proj1',
            'name': 'Project Agent',
            'description': 'Project tier',
            'specializations': ['project'],
            'source_tier': 'project',
            'capabilities': {},
            'tools': []
        }
    ]
    content = generator.generate_capabilities_section(mixed_agents)
    if "### Project-Specific Agents" in content and "**Project Agent**" in content:
        print("   ✓ Project agents shown in separate section")
    else:
        print("   ✗ Project agents not properly separated")


def test_performance():
    """Test performance requirements."""
    print("\n\nTesting Performance")
    print("=" * 80)
    
    import time
    
    # Test full cycle performance
    print("\n1. Testing full generation cycle...")
    
    start = time.time()
    discovery = DeployedAgentDiscovery()
    agents = discovery.discover_deployed_agents()
    discovery_time = time.time() - start
    
    start = time.time()
    generator = AgentCapabilitiesGenerator()
    content = generator.generate_capabilities_section(agents)
    generation_time = time.time() - start
    
    start = time.time()
    assembler = ContentAssembler()
    test_content = "Test {{capabilities-list}} content"
    processed = assembler.apply_template_variables(test_content)
    assembly_time = time.time() - start
    
    total_time = discovery_time + generation_time + assembly_time
    
    print(f"   Discovery: {discovery_time*1000:.1f}ms")
    print(f"   Generation: {generation_time*1000:.1f}ms")
    print(f"   Assembly: {assembly_time*1000:.1f}ms")
    print(f"   Total: {total_time*1000:.1f}ms")
    
    if total_time < 0.200:  # 200ms
        print(f"   ✓ Performance requirement met ({total_time*1000:.1f}ms < 200ms)")
    else:
        print(f"   ✗ Performance too slow ({total_time*1000:.1f}ms > 200ms)")


if __name__ == "__main__":
    test_real_deployment_flow()
    test_edge_cases()
    test_performance()