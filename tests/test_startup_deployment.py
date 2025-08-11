#!/usr/bin/env python3
"""
Test that the project deployment works on startup.
This simulates what happens when claude-mpm starts in a project directory.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.claude_runner import ClaudeRunner


def test_startup_deployment():
    """Test the ensure_project_agents method."""
    print("Testing project agent deployment on startup...")
    print("-" * 50)
    
    # Initialize runner (simulates what happens in run_session)
    runner = ClaudeRunner(
        enable_tickets=False,
        log_level="OFF"
    )
    
    # Check if we're in a project (we are - claude-mpm itself)
    project_markers = ['.git', 'pyproject.toml', 'package.json', 'requirements.txt']
    cwd = Path.cwd()
    is_project = any((cwd / marker).exists() for marker in project_markers)
    
    print(f"Current directory: {cwd}")
    print(f"Is project directory: {is_project}")
    
    if is_project:
        print("\nCalling ensure_project_agents()...")
        success = runner.ensure_project_agents()
        
        if success:
            print("✓ Successfully ensured project agents")
            
            # Check what agents were deployed
            agents_dir = cwd / ".claude-mpm" / "agents"
            if agents_dir.exists():
                agent_files = list(agents_dir.glob("*.md"))
                print(f"✓ Found {len(agent_files)} agent files in {agents_dir}")
                
                # List system agents that were deployed
                system_agents = []
                for agent_file in agent_files:
                    with open(agent_file, 'r') as f:
                        content = f.read()
                        if "author: claude-mpm" in content:
                            system_agents.append(agent_file.stem)
                
                if system_agents:
                    print(f"✓ System agents available: {', '.join(sorted(system_agents))}")
            else:
                print("❌ Agents directory doesn't exist")
                return False
        else:
            print("❌ ensure_project_agents failed")
            return False
    else:
        print("Not in a project directory")
        return False
    
    print("-" * 50)
    print("✅ Test completed successfully!")
    return True


if __name__ == "__main__":
    success = test_startup_deployment()
    sys.exit(0 if success else 1)