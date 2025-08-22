#!/usr/bin/env python3
"""Quick diagnostic script for agent deployment issues."""

import sys
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

def check_agents():
    """Check agent status."""
    print("="*60)
    print("AGENT DIAGNOSTIC CHECK")
    print("="*60)
    
    # Check deployed agents
    project_agents_dir = Path.cwd() / ".claude" / "agents"
    if project_agents_dir.exists():
        deployed = list(project_agents_dir.glob("*.md"))
        print(f"\n✅ Found {len(deployed)} deployed agents in {project_agents_dir}")
        for agent_file in deployed[:5]:
            print(f"   - {agent_file.stem}")
        if len(deployed) > 5:
            print(f"   ... and {len(deployed) - 5} more")
    else:
        print(f"\n❌ No agents directory at {project_agents_dir}")
    
    # Check templates
    from claude_mpm.config.paths import paths
    templates_dir = paths.agents_dir / "templates"
    if templates_dir.exists():
        templates = list(templates_dir.glob("*.json"))
        print(f"\n✅ Found {len(templates)} templates in {templates_dir}")
        for template_file in templates[:5]:
            print(f"   - {template_file.stem}")
        if len(templates) > 5:
            print(f"   ... and {len(templates) - 5} more")
    else:
        print(f"\n❌ No templates directory at {templates_dir}")
    
    # Check if agents match templates
    if project_agents_dir.exists() and templates_dir.exists():
        deployed_names = {f.stem for f in deployed}
        template_names = {f.stem for f in templates}
        
        print(f"\n📊 Agent/Template Comparison:")
        print(f"   Deployed agents: {len(deployed_names)}")
        print(f"   Available templates: {len(template_names)}")
        
        # Find orphaned agents (deployed but no template)
        orphaned = deployed_names - template_names
        if orphaned:
            print(f"\n⚠️  {len(orphaned)} orphaned agent(s) (deployed without template):")
            for name in list(orphaned)[:5]:
                print(f"   - {name}")
            if len(orphaned) > 5:
                print(f"   ... and {len(orphaned) - 5} more")
        
        # Find missing agents (template but not deployed)
        missing = template_names - deployed_names
        if missing:
            print(f"\n⚠️  {len(missing)} missing agent(s) (template but not deployed):")
            for name in list(missing)[:5]:
                print(f"   - {name}")
            if len(missing) > 5:
                print(f"   ... and {len(missing) - 5} more")
        
        # Find matching agents
        matching = deployed_names & template_names
        if matching:
            print(f"\n✅ {len(matching)} agent(s) have matching templates")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    check_agents()