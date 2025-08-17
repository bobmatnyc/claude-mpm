#!/usr/bin/env python3
"""Remove ticketing references from all agent templates."""

import re
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Templates directory
templates_dir = Path(__file__).parent.parent / "src" / "claude_mpm" / "agents" / "templates"

def remove_ticketing_references(content):
    """Remove ticketing references from content."""
    
    # Remove Ticket Reference lines
    content = re.sub(r'\*\*Ticket Reference\*\*: \[ISS-XXXX if applicable\]\n', '', content)
    content = re.sub(r'\*\*Ticket Reference\*\*: ISS-\d+\n', '', content)
    content = re.sub(r'\*\*Ticket Reference\*\*: TSK-\d+\n', '', content)
    content = re.sub(r'\*\*Ticket Reference\*\*: EP-\d+\n', '', content)
    
    # Remove entire Ticketing Guidelines sections
    content = re.sub(r'## Ticketing Guidelines\n\n.*?(?=##|\Z)', '', content, flags=re.DOTALL)
    
    # Remove ticket references from delegation templates
    content = re.sub(r'- Always include ticket reference in delegation:.*\n', '', content)
    content = re.sub(r'- Use ticket ID in branch names.*\n', '', content)
    content = re.sub(r'- Comment code with ticket references.*\n', '', content)
    content = re.sub(r'- Track.*per ticket.*\n', '', content)
    content = re.sub(r'- Tag.*with ticket.*\n', '', content)
    content = re.sub(r'- Link.*to ticket.*\n', '', content)
    content = re.sub(r'- Report.*against.*ticket.*\n', '', content)
    content = re.sub(r'- Flag when.*ticket.*\n', '', content)
    content = re.sub(r'- Map.*to.*ticket.*\n', '', content)
    content = re.sub(r'- Track.*with ticket references.*\n', '', content)
    content = re.sub(r'- Document.*in ticket context.*\n', '', content)
    content = re.sub(r'- Identify need for new tickets.*\n', '', content)
    
    # Remove ticket-specific patterns and examples
    content = re.sub(r'📝 Code Review Summary for ISS-\d+:.*?```', '', content, flags=re.DOTALL)
    content = re.sub(r'🐛 Bug Fix Complete for ISS-\d+:.*?```', '', content, flags=re.DOTALL)
    content = re.sub(r'📦 Deployment Summary for ISS-\d+:.*?```', '', content, flags=re.DOTALL)
    content = re.sub(r'🔄 Migration Summary for ISS-\d+:.*?```', '', content, flags=re.DOTALL)
    content = re.sub(r'🔌 API Integration Complete for ISS-\d+:.*?```', '', content, flags=re.DOTALL)
    content = re.sub(r'🔒 Security Finding for ISS-\d+:.*?```', '', content, flags=re.DOTALL)
    content = re.sub(r'📋 Compliance Status for ISS-\d+:.*?```', '', content, flags=re.DOTALL)
    content = re.sub(r'📋 Research Summary for Ticket ISS-\d+:.*?```', '', content, flags=re.DOTALL)
    content = re.sub(r'🐛 Bug Found - Needs Ticket:.*?```', '', content, flags=re.DOTALL)
    
    # Remove aitrackdown references
    content = re.sub(r'.*aitrackdown.*\n', '', content)
    
    # Clean up excessive newlines
    content = re.sub(r'\n{4,}', '\n\n\n', content)
    
    return content

# Process each agent template (except ticketing_agent.md which we'll delete)
for agent_file in templates_dir.glob("*_agent.md"):
    if agent_file.name == "ticketing_agent.md":
        # Delete the ticketing agent entirely
        agent_file.unlink()
        print(f"✗ Deleted {agent_file.name}")
        continue
    
    content = agent_file.read_text()
    original_len = len(content)
    
    # Remove ticketing references
    content = remove_ticketing_references(content)
    
    # Write back
    agent_file.write_text(content)
    
    new_len = len(content)
    if new_len < original_len:
        print(f"✓ Cleaned {agent_file.name} (removed {original_len - new_len} chars)")
    else:
        print(f"  {agent_file.name} (no changes)")

print("\nDone!")