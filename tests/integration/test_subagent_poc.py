#!/usr/bin/env python3
"""POC: Test Claude Code Native Subagent YAML Loading

This script validates that Claude will read agent configurations from 
a custom directory when CLAUDE_CONFIG_DIR is set.
"""

import os
import sys
import json
import yaml
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.core.claude_launcher import ClaudeLauncher

def create_test_agent_yaml(agent_dir: Path, agent_name: str, description: str, tools: list):
    """Create a test agent YAML configuration."""
    
    agent_config = {
        'name': agent_name,
        'description': description,
        'version': '1.0.0',
        'author': 'claude-mpm-poc',
        'tags': ['test', 'poc'],
        'tools': tools,
        'priority': 'medium',
        'timeout': 300,
        'max_tokens': 4096,
        'source': 'claude-mpm-poc',
        'created': datetime.now().isoformat()
    }
    
    system_prompt = f"""You are the {agent_name.title()} Agent created for POC testing.

Your role is to demonstrate that Claude can load and use custom agent configurations
from the directory: {agent_dir}

When asked to perform a task, always:
1. Confirm your identity as the {agent_name.title()} Agent
2. Mention that you were loaded from a custom YAML configuration
3. Complete the requested task
4. Report your agent metadata (name: {agent_name}, version: 1.0.0)"""
    
    # Create agent file with YAML frontmatter
    agent_file = agent_dir / f"{agent_name}.md"
    
    with open(agent_file, 'w') as f:
        f.write("---\n")
        yaml.dump(agent_config, f, default_flow_style=False)
        f.write("---\n\n")
        f.write(system_prompt)
    
    print(f"✓ Created agent: {agent_file}")
    return agent_file

def main():
    print("🚀 Claude Native Subagent POC Test")
    print("=" * 80)
    
    # Setup test directory
    test_dir = Path.cwd() / ".claude-mpm"
    agent_dir = test_dir / "agents"
    
    # Clean and create directory
    if agent_dir.exists():
        shutil.rmtree(agent_dir)
    agent_dir.mkdir(parents=True)
    
    print(f"\n📁 Test Configuration:")
    print(f"  Agent Directory: {agent_dir}")
    print(f"  Working Directory: {Path.cwd()}")
    
    # Create test agents
    print("\n📝 Creating Test Agents:")
    
    agents = [
        {
            'name': 'poc-engineer',
            'description': 'POC test engineer for implementation tasks',
            'tools': ['Read', 'Write', 'Edit', 'Bash']
        },
        {
            'name': 'poc-qa',
            'description': 'POC test QA specialist for testing',
            'tools': ['Read', 'Grep', 'Bash']
        },
        {
            'name': 'poc-researcher',
            'description': 'POC test researcher for analysis',
            'tools': ['Read', 'WebSearch', 'Grep']
        }
    ]
    
    for agent in agents:
        create_test_agent_yaml(agent_dir, agent['name'], agent['description'], agent['tools'])
    
    # Test 1: Verify Claude can see agents with CLAUDE_CONFIG_DIR
    print("\n🧪 Test 1: Agent Discovery with CLAUDE_CONFIG_DIR")
    print("-" * 80)
    
    # Set environment variable
    env = os.environ.copy()
    env['CLAUDE_CONFIG_DIR'] = str(test_dir)
    
    # Create test prompt
    test_prompt = """Please list all available subagents you can delegate to.

Then demonstrate delegation by:
1. Use TodoWrite to track a task for poc-engineer to create a hello.py file
2. Use TodoWrite to track a task for poc-qa to verify the file exists

Report which agents you found and whether you could track tasks for them."""
    
    print(f"Environment: CLAUDE_CONFIG_DIR={test_dir}")
    print(f"\nTest prompt:\n{test_prompt}\n")
    
    # Launch Claude with custom config
    launcher = ClaudeLauncher(model="opus", skip_permissions=True)
    
    # Modify launcher to use our environment
    original_launch = launcher.launch
    def launch_with_env(*args, **kwargs):
        kwargs['env'] = env
        return original_launch(*args, **kwargs)
    launcher.launch = launch_with_env
    
    print("Launching Claude with custom agent directory...")
    
    try:
        stdout, stderr, returncode = launcher.launch_oneshot(
            message=test_prompt,
            use_stdin=True,
            timeout=60
        )
        
        print(f"\nReturn code: {returncode}")
        print(f"\nResponse:\n{'-'*80}")
        print(stdout)
        print('-'*80)
        
        if stderr:
            print(f"\nErrors:\n{stderr}")
        
        # Check if response mentions our custom agents
        if 'poc-engineer' in stdout or 'poc-qa' in stdout or 'poc-researcher' in stdout:
            print("\n✅ SUCCESS: Claude recognized custom agents!")
        else:
            print("\n⚠️  WARNING: Custom agents not mentioned in response")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return 1
    
    # Test 2: Direct subagent invocation
    print("\n\n🧪 Test 2: Direct Subagent Task Delegation")
    print("-" * 80)
    
    delegation_prompt = """You are the Project Manager. Please delegate these tasks:

**poc-engineer**: Create a simple Python function that returns "POC Success!"
**poc-qa**: Verify the function works correctly
**poc-researcher**: Research whether this POC approach is viable

Use Task tool to delegate if available, otherwise use TodoWrite."""
    
    print(f"Delegation prompt:\n{delegation_prompt}\n")
    
    try:
        stdout, stderr, returncode = launcher.launch_oneshot(
            message=delegation_prompt,
            use_stdin=True,
            timeout=60
        )
        
        print(f"\nResponse:\n{'-'*80}")
        print(stdout)
        print('-'*80)
        
        # Check TODO files
        todo_dir = Path.home() / ".claude" / "todos"
        if todo_dir.exists():
            todo_files = list(todo_dir.glob("*.json"))
            if todo_files:
                print(f"\n✅ Found {len(todo_files)} TODO files created")
                for tf in todo_files[-3:]:  # Show last 3
                    print(f"  - {tf.name}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 POC Test Summary")
    print("=" * 80)
    
    print("\nKey Findings:")
    print("1. Agent Directory:", agent_dir)
    print("2. Environment Variable: CLAUDE_CONFIG_DIR =", test_dir)
    print("3. Agents Created:", len(agents))
    
    print("\nNext Steps:")
    print("- If agents were recognized: Proceed with YAML generator implementation")
    print("- If not recognized: Try alternative directory locations")
    print("- Check if .claude/agents/ in project root works better")
    print("- Test with --agent-dir flag if available")

if __name__ == "__main__":
    sys.exit(main())