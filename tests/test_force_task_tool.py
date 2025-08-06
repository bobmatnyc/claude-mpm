#!/usr/bin/env python3
"""Force Task tool usage to test Agents tab."""

import os
import subprocess
import time
import webbrowser
from pathlib import Path
import sys

def main():
    print("🎯 Forcing Task Tool Usage for Agents Tab")
    print("=" * 60)
    
    # Open dashboard
    dashboard_path = Path(__file__).parent / "claude_mpm_socketio_dashboard.html"
    dashboard_url = f"file://{dashboard_path}?autoconnect=true&port=8765"
    
    print(f"\n📊 Opening dashboard: {dashboard_url}")
    webbrowser.open(dashboard_url)
    time.sleep(2)
    
    # Suppress browser for tests
    os.environ['CLAUDE_MPM_NO_BROWSER'] = '1'
    
    print("\n🔧 Using prompts that should force Task tool usage...")
    
    # Very explicit prompts that should trigger Task tool
    force_task_prompts = [
        """I need you to delegate the following task to the research agent using the Task tool:
        
Task for research agent: Analyze the structure and organization of the claude_mpm codebase, focusing on the agent system and how agents are configured and loaded.

Please use the Task tool with subagent_type="research" to delegate this.""",

        """Please use the Task tool to delegate this to the engineer agent:

Create a simple Python function that logs messages to a file with timestamps.

Use Task(description="Create logging function", subagent_type="engineer", prompt="Create a Python function that logs messages to a file with timestamps")""",

        """I want you to invoke the Task tool for the documentation agent.

Task details:
- subagent_type: "documentation"  
- description: "Explain the hook system"
- prompt: "Write a clear explanation of how the Claude MPM hook system works"

Please execute this Task tool call.""",

        """Delegate to QA agent via Task tool:
Test the monitoring dashboard by checking if events are displayed correctly.
subagent_type should be "qa"."""
    ]
    
    for i, prompt in enumerate(force_task_prompts, 1):
        print(f"\n{i}. Testing explicit Task tool request")
        print(f"   Prompt preview: {prompt[:100]}...")
        
        cmd = [
            sys.executable, "-m", "claude_mpm", "run",
            "-i", prompt,
            "--non-interactive",
            "--monitor"
        ]
        
        print("   Running command...")
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0:
            print("   ✅ Command completed")
            
            # Look for Task tool usage
            if "Task" in result.stdout:
                print("   ✅ Task tool mentioned in output")
            if "delegat" in result.stdout.lower():
                print("   ✅ Delegation mentioned")
            if any(agent in result.stdout.lower() for agent in ["research", "engineer", "documentation", "qa"]):
                print("   ✅ Agent type mentioned")
        else:
            print(f"   ❌ Command failed: {result.stderr[:100]}")
        
        time.sleep(2)
    
    print("\n" + "=" * 60)
    print("✅ Tests complete!")
    print("\n📊 Check the Dashboard Now:")
    print("\n1. Go to 'Agents' tab")
    print("   - Should now show agent delegations")
    print("   - Each card shows agent type, timestamp, and task preview")
    print("\n2. Click on an agent card")
    print("   - Should show delegation details in module viewer")
    print("   - Check if agent_type is correct (not 'unknown')")
    print("\n3. If still no agents showing:")
    print("   - Check Events tab for 'hook.pre_tool' events")
    print("   - Look for events with tool_name='Task'")
    print("   - Click to see the full event structure")
    print("\n💡 The fix applied:")
    print("- Dashboard now checks multiple locations for agent data")
    print("- Looks in delegation_details, tool_parameters, and params")
    print("- Should handle different event structures")

if __name__ == "__main__":
    main()