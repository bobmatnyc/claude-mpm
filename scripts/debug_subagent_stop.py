#!/usr/bin/env python3
"""Debug SubagentStop events and understand why agent_type is unknown."""

import os
import sys
import subprocess
import json
import time
from pathlib import Path

def test_subagent_stop_events():
    """Generate SubagentStop events and analyze the data."""
    print("🔍 Debugging SubagentStop Events")
    print("=" * 60)
    
    # Enable debug mode for hooks
    os.environ['CLAUDE_MPM_HOOK_DEBUG'] = 'true'
    os.environ['CLAUDE_MPM_NO_BROWSER'] = '1'
    
    print("\n1. Testing various agent delegations...")
    
    # Test different agent types
    test_prompts = [
        ("Research the codebase structure", "research"),
        ("Implement a new feature", "engineer"),
        ("Write documentation for the API", "documentation"),
        ("Run tests on the system", "qa"),
        ("Check security vulnerabilities", "security"),
        ("Deploy the application", "ops"),
        ("Manage project tasks", "pm"),
        ("Analyze data patterns", "data_engineer"),
        ("Handle version control", "version_control")
    ]
    
    for prompt, expected_agent in test_prompts:
        print(f"\n📝 Testing: {prompt}")
        print(f"   Expected agent: {expected_agent}")
        
        cmd = [
            sys.executable, "-m", "claude_mpm", "run",
            "-i", prompt,
            "--non-interactive",
            "--monitor"
        ]
        
        # Capture stderr to see debug output
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            timeout=45
        )
        
        # Look for SubagentStop in stderr (debug output)
        if "SubagentStop" in result.stderr:
            print("   ✅ SubagentStop event found in debug output")
            # Extract the raw event data
            for line in result.stderr.split('\n'):
                if "SubagentStop raw event data:" in line:
                    print(f"   📋 {line}")
        else:
            print("   ⚠️ No SubagentStop event found")
        
        time.sleep(1)
    
    print("\n2. Analyzing the issue...")
    print("\nPossible reasons for 'unknown' agent_type:")
    print("- Claude Code might not pass agent information in SubagentStop events")
    print("- The event structure might be different than expected")
    print("- We need to extract agent info from the Task tool invocation")
    print("- Agent templates might need additional metadata")
    
    print("\n3. Checking hook handler code...")
    hook_handler = Path(__file__).parent.parent / "src/claude_mpm/hooks/claude_hooks/hook_handler.py"
    
    with open(hook_handler, 'r') as f:
        content = f.read()
        
    # Find the SubagentStop handling
    if "_handle_subagent_stop_fast" in content:
        print("✅ SubagentStop handler found")
        print("\nThe handler tries to extract agent_type from:")
        print("1. event.get('agent_type')")
        print("2. event.get('subagent_type')")
        print("3. Falls back to 'unknown'")
        print("\nThen it tries to infer from task description")
    
    print("\n4. Recommendations:")
    print("- Store agent type when Task tool is invoked")
    print("- Use a mapping of task ID to agent type")
    print("- Enhance the event data with agent information")
    print("- Consider using the pre_tool event data to enrich subagent_stop")

def check_task_tool_correlation():
    """Check if we can correlate Task tool calls with SubagentStop events."""
    print("\n\n🔗 Checking Task Tool Correlation")
    print("=" * 60)
    
    print("\nGenerating a simple task delegation...")
    
    cmd = [
        sys.executable, "-m", "claude_mpm", "run",
        "-i", "Ask the research agent to analyze the main function",
        "--non-interactive",
        "--monitor"
    ]
    
    result = subprocess.run(
        cmd,
        cwd=Path(__file__).parent.parent,
        capture_output=True,
        text=True,
        timeout=30
    )
    
    print("\nLooking for correlation between:")
    print("- PreToolUse event with tool_name='Task'")
    print("- SubagentStop event")
    print("\nThese should have matching session IDs or task identifiers")
    
    # Parse debug output
    pre_tool_events = []
    subagent_stop_events = []
    
    for line in result.stderr.split('\n'):
        if "PreToolUse" in line and "Task" in line:
            pre_tool_events.append(line)
        elif "SubagentStop" in line:
            subagent_stop_events.append(line)
    
    print(f"\nFound {len(pre_tool_events)} Task tool invocations")
    print(f"Found {len(subagent_stop_events)} SubagentStop events")
    
    if pre_tool_events and subagent_stop_events:
        print("\n✅ Events found! We can potentially correlate them")
        print("Solution: Store agent type from Task tool params and use it in SubagentStop")

def main():
    """Run debug analysis."""
    print("🐛 SubagentStop Event Debugger")
    print("This will help understand why agent_type is 'unknown'\n")
    
    # Run tests
    test_subagent_stop_events()
    check_task_tool_correlation()
    
    print("\n\n📊 Summary")
    print("=" * 60)
    print("The issue is that Claude Code's SubagentStop events don't include")
    print("the agent type information. We need to:")
    print("\n1. Track Task tool invocations (which have subagent_type)")
    print("2. Store a mapping of task/session to agent type")
    print("3. Use this mapping when handling SubagentStop events")
    print("4. This requires coordination between pre_tool and subagent_stop handlers")

if __name__ == "__main__":
    main()