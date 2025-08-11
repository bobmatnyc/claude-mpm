#!/usr/bin/env python3
"""Verify that agent deployment is working correctly with author field."""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.agents.deployment import AgentDeploymentService


def verify_deployment():
    """Verify agents are properly deployed with author field."""
    
    print("Verifying agent deployment fix...")
    print("=" * 50)
    
    # Check current project agents
    agents_dir = Path(".claude/agents")
    
    if not agents_dir.exists():
        print("❌ No .claude/agents directory found")
        return False
    
    agent_files = list(agents_dir.glob("*.md"))
    print(f"Found {len(agent_files)} deployed agents")
    
    all_valid = True
    missing_author = []
    has_author = []
    
    for agent_file in agent_files:
        content = agent_file.read_text()
        if "author: claude-mpm" in content:
            has_author.append(agent_file.name)
        else:
            missing_author.append(agent_file.name)
            all_valid = False
    
    if has_author:
        print(f"\n✅ Agents with author field ({len(has_author)}):")
        for name in sorted(has_author):
            print(f"   - {name}")
    
    if missing_author:
        print(f"\n❌ Agents missing author field ({len(missing_author)}):")
        for name in sorted(missing_author):
            print(f"   - {name}")
    
    print("\n" + "=" * 50)
    
    if all_valid:
        print("✅ SUCCESS: All agents have 'author: claude-mpm' field")
        print("\nThis means:")
        print("1. System agents are properly identified")
        print("2. Agents will be correctly deployed to projects")
        print("3. The deployment issue has been fixed")
    else:
        print("❌ Some agents are missing the author field")
        print("\nTo fix, run: ./claude-mpm agents force-deploy")
    
    return all_valid


if __name__ == "__main__":
    success = verify_deployment()
    sys.exit(0 if success else 1)