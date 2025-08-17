#!/usr/bin/env python3
"""Test script to verify agent ID mapping fix for PM instructions."""

import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader

def test_agent_id_mapping():
    """Test that agent IDs are correctly extracted from YAML frontmatter."""
    
    print("Testing Agent ID Mapping Fix")
    print("=" * 50)
    
    # Initialize the framework loader
    loader = FrameworkLoader()
    
    # Generate the agent capabilities section
    capabilities = loader._generate_agent_capabilities_section()
    
    print("\nGenerated Agent Capabilities Section:")
    print("-" * 50)
    print(capabilities)
    print("-" * 50)
    
    # Check for expected agent IDs
    expected_ids = [
        'research-agent',
        'qa-agent', 
        'documentation-agent',
        'security-agent',
        'data-engineer',
        'ops-agent',
        'version-control'
    ]
    
    print("\nVerifying expected agent IDs are present:")
    for agent_id in expected_ids:
        if f"`{agent_id}`" in capabilities:
            print(f"✓ Found: {agent_id}")
        else:
            print(f"✗ Missing: {agent_id}")
    
    # Check that old IDs are NOT present (except 'engineer' which keeps its name)
    old_ids = ['research', 'qa', 'documentation', 'security', 'data_engineer', 'ops', 'version_control']
    
    print("\nVerifying old IDs are replaced:")
    for old_id in old_ids:
        # Check if old ID appears as an agent ID (in backticks)
        if f"`{old_id}`" in capabilities:
            print(f"✗ Old ID still present: {old_id}")
        else:
            print(f"✓ Old ID replaced: {old_id}")
    
    print("\n" + "=" * 50)
    print("Test complete!")

if __name__ == "__main__":
    test_agent_id_mapping()