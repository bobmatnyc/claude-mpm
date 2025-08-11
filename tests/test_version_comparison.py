#!/usr/bin/env python3
"""Test version comparison for agent updates."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.deployment import AgentDeploymentService

def main():
    """Test version comparison logic."""
    service = AgentDeploymentService()
    
    # Test the check_agent_needs_update method
    deployed_file = Path.home() / ".claude/agents/research.md"
    template_file = Path("src/claude_mpm/agents/templates/research.json")
    
    # Get current base version
    base_agent_path = Path("src/claude_mpm/agents/base_agent.json")
    if base_agent_path.exists():
        import json
        base_data = json.loads(base_agent_path.read_text())
        base_version = service._parse_version(base_data.get('base_version') or base_data.get('version', 0))
    else:
        base_version = (0, 2, 0)  # Default
    
    print(f"Checking if research agent needs update:")
    print(f"  Deployed file: {deployed_file}")
    print(f"  Template file: {template_file}")
    print(f"  Base version: {service._format_version_display(base_version)}")
    
    if deployed_file.exists() and template_file.exists():
        needs_update, reason = service._check_agent_needs_update(
            deployed_file, template_file, base_version
        )
        print(f"\n  Needs update: {needs_update}")
        print(f"  Reason: {reason}")
    else:
        print("\n  Error: Files not found")

if __name__ == "__main__":
    main()