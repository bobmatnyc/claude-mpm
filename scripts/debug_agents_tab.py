#!/usr/bin/env python3
"""Debug why agents aren't showing in the Agents tab."""

import os
import subprocess
import time
import sys
from pathlib import Path

def test_direct_agent_delegation():
    """Test direct agent delegation to ensure Task events are generated."""
    print("🔍 Debugging Agents Tab")
    print("=" * 60)
    
    # Suppress browser
    os.environ['CLAUDE_MPM_NO_BROWSER'] = '1'
    
    print("\n1. Testing explicit agent delegation...")
    
    # Very explicit agent delegations
    test_prompts = [
        "Use the Task tool to delegate to the research agent to analyze the main function",
        "I need you to use the Task tool with subagent_type='engineer' to implement a feature",
        "Please invoke the Task tool to ask the documentation agent to explain hooks",
        "Call the Task tool with subagent_type='qa' to test the system"
    ]
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"\n{i}. Testing: {prompt}")
        
        cmd = [
            sys.executable, "-m", "claude_mpm", "run",
            "-i", prompt,
            "--non-interactive",
            "--monitor"
        ]
        
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            timeout=45
        )
        
        # Check output for Task tool usage
        if "Task" in result.stdout or "task" in result.stdout.lower():
            print("   ✅ Task tool mentioned in output")
        else:
            print("   ⚠️ No Task tool usage detected")
            
        time.sleep(1)
    
    print("\n2. Checking what events are generated...")
    print("   The Agents tab filters for: hook.pre_tool events where tool_name='Task'")
    print("   Make sure:")
    print("   - The Task tool is actually being invoked")
    print("   - Events are being sent to the Socket.IO server")
    print("   - The dashboard is connected to the correct port")

def test_manual_task_invocation():
    """Test manual Task tool invocation."""
    print("\n\n3. Testing manual Task tool invocation...")
    
    # Try a more direct approach
    prompt = """Please analyze the following request and delegate it appropriately:

"I need comprehensive research on the codebase structure"

Use the Task tool with:
- subagent_type: "research"
- description: "Analyze codebase structure"
- prompt: "Please analyze the overall structure and organization of this codebase"
"""
    
    print(f"Prompt:\n{prompt}")
    
    cmd = [
        sys.executable, "-m", "claude_mpm", "run",
        "-i", prompt,
        "--non-interactive",
        "--monitor"
    ]
    
    print("\nRunning command...")
    result = subprocess.run(
        cmd,
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
        timeout=60
    )
    
    if result.returncode == 0:
        print("✅ Command completed successfully")
        
        # Look for specific indicators
        indicators = ["Task", "research", "subagent_type", "delegation"]
        for indicator in indicators:
            if indicator in result.stdout:
                print(f"   ✅ Found '{indicator}' in output")
    else:
        print("❌ Command failed")
        print(f"Error: {result.stderr[:200]}")

def check_dashboard_code():
    """Check the dashboard code for agent filtering."""
    print("\n\n4. Checking dashboard code...")
    
    dashboard_path = Path(__file__).parent / "claude_mpm_socketio_dashboard.html"
    
    with open(dashboard_path, 'r') as f:
        content = f.read()
    
    # Check renderAgents function
    if "renderAgents" in content:
        print("✅ renderAgents function exists")
        
        # Check the filter
        if "e.type === 'hook.pre_tool'" in content:
            print("✅ Filtering for hook.pre_tool events")
        
        if "e.data?.tool_name === 'Task'" in content:
            print("✅ Filtering for Task tool")
        
        if "subagent_type" in content:
            print("✅ Looking for subagent_type parameter")
    
    print("\n5. Possible issues:")
    print("- Claude might not be using the Task tool for delegations")
    print("- Events might not be reaching the Socket.IO server")
    print("- The event structure might be different than expected")
    print("- Socket.IO connection might not be established")

def suggest_fixes():
    """Suggest potential fixes."""
    print("\n\n💡 Troubleshooting Steps:")
    print("=" * 60)
    
    print("\n1. Verify Socket.IO connection:")
    print("   - Check if port 8765 is in use")
    print("   - Look for 'Connected' status in dashboard header")
    print("   - Check browser console for connection errors")
    
    print("\n2. Check event flow:")
    print("   - Open browser DevTools console")
    print("   - Look for 'Received event:' logs")
    print("   - Check if any hook.pre_tool events arrive")
    
    print("\n3. Test with simple prompts:")
    print("   - 'Research the main function'")
    print("   - 'Ask the engineer agent to help'")
    print("   - 'Delegate this to the research agent'")
    
    print("\n4. Enable debug mode:")
    print("   export CLAUDE_MPM_HOOK_DEBUG=true")
    print("   export CLAUDE_MPM_LOG_LEVEL=DEBUG")
    
    print("\n5. Check the Events tab:")
    print("   - Look for ANY hook.pre_tool events")
    print("   - Click on them to see tool_name")
    print("   - Verify if Task tool is being used at all")

def main():
    """Run debugging steps."""
    print("🐛 Agents Tab Debugging")
    print("This will help identify why agents aren't showing up\n")
    
    # Run tests
    test_direct_agent_delegation()
    test_manual_task_invocation()
    check_dashboard_code()
    suggest_fixes()
    
    print("\n\n📋 Next Steps:")
    print("1. Open the dashboard and check the Events tab")
    print("2. Look for 'hook.pre_tool' events")
    print("3. If you see them, check if any have tool_name='Task'")
    print("4. If not, Claude might not be delegating via Task tool")
    print("5. Try more explicit delegation prompts")

if __name__ == "__main__":
    main()