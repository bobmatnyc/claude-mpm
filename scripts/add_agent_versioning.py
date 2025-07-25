#!/usr/bin/env python3
"""Add versioning to all agent templates."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Agent templates directory
templates_dir = Path(__file__).parent.parent / "src" / "claude_mpm" / "agents" / "templates"

# Process each agent template (skip README.md)
agent_files = [f for f in templates_dir.glob("*_agent.md")]

for agent_file in agent_files:
    content = agent_file.read_text()
    
    # Check if already has versioning
    if "<!-- AGENT_VERSION:" in content:
        print(f"✓ {agent_file.name} already has versioning")
        continue
    
    # Add version after the title
    lines = content.split('\n')
    new_lines = []
    title_found = False
    
    for line in lines:
        new_lines.append(line)
        if line.startswith('# ') and not title_found:
            # Add version after title
            new_lines.append('')
            new_lines.append('<!-- AGENT_VERSION: 1 -->')
            title_found = True
    
    # Write back
    agent_file.write_text('\n'.join(new_lines))
    print(f"✅ Added versioning to {agent_file.name}")

print("\nDone!")