#!/usr/bin/env python3
"""Debug research agent version parsing."""

import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.deployment import AgentDeploymentService

def main():
    """Debug version parsing for research agent."""
    research_path = Path("src/claude_mpm/agents/templates/research.json")
    
    print(f"Reading: {research_path}")
    
    # Read the JSON
    with open(research_path) as f:
        data = json.load(f)
    
    print(f"Schema version: {data.get('schema_version')}")
    print(f"Agent version field: {data.get('agent_version')}")
    print(f"Version field: {data.get('version')}")
    
    # Test parsing
    service = AgentDeploymentService()
    version_value = data.get('agent_version') or data.get('version', 0)
    print(f"\nVersion value to parse: {version_value}")
    
    parsed = service._parse_version(version_value)
    print(f"Parsed version tuple: {parsed}")
    
    formatted = service._format_version_display(parsed)
    print(f"Formatted version: {formatted}")
    
    # Check if research is using new schema
    if 'configuration' in data:
        print("\nResearch agent is using NEW schema format")
        print(f"Configuration fields: {list(data.get('configuration', {}).keys())}")
    elif 'configuration_fields' in data:
        print("\nResearch agent is using OLD schema format")
        print(f"Configuration fields: {list(data.get('configuration_fields', {}).keys())}")

if __name__ == "__main__":
    main()