#!/usr/bin/env python3
"""Demonstrate the agent ID fix by showing before/after comparison."""

import yaml
from pathlib import Path

def show_agent_id_mapping():
    """Show how agent IDs are mapped from files to PM instructions."""
    
    print("Agent ID Mapping Demonstration")
    print("=" * 60)
    
    agents_dir = Path("/Users/masa/Projects/claude-mpm/.claude/agents")
    
    if not agents_dir.exists():
        print("No deployed agents found")
        return
    
    print("\n📁 File → 🏷️ YAML Name → ✅ PM Instruction ID")
    print("-" * 60)
    
    for agent_file in sorted(agents_dir.glob("*.md")):
        if agent_file.name.startswith('.'):
            continue
            
        filename_stem = agent_file.stem
        yaml_name = filename_stem  # Default
        
        # Read YAML frontmatter to get actual name
        try:
            with open(agent_file, 'r') as f:
                content = f.read()
                if content.startswith('---'):
                    end_marker = content.find('---', 3)
                    if end_marker > 0:
                        frontmatter = content[3:end_marker]
                        metadata = yaml.safe_load(frontmatter)
                        if metadata and 'name' in metadata:
                            yaml_name = metadata['name']
        except:
            pass
        
        # Show the mapping
        print(f"📁 {filename_stem:20} → 🏷️ {yaml_name:20} → ✅ `{yaml_name}`")
    
    print("\n" + "=" * 60)
    print("\n🔴 BEFORE FIX: PM would use filename (e.g., `research`)")
    print("   ❌ Claude Code expects YAML name (e.g., `research-agent`)")
    print("   Result: Task delegation would fail\n")
    
    print("✅ AFTER FIX: PM uses YAML name from frontmatter")
    print("   ✅ Claude Code gets expected agent ID")
    print("   Result: Task delegation works correctly!")

if __name__ == "__main__":
    show_agent_id_mapping()