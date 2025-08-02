#!/usr/bin/env python3
"""Test Task tool events specifically to debug Agents tab."""

import os
import subprocess
import time
import webbrowser
from pathlib import Path
import sys

def main():
    print("🔧 Testing Task Tool Events for Agents Tab")
    print("=" * 60)
    
    # Open dashboard
    dashboard_path = Path(__file__).parent / "claude_mpm_socketio_dashboard.html"
    dashboard_url = f"file://{dashboard_path}?autoconnect=true&port=8765"
    
    print(f"\n📊 Opening dashboard: {dashboard_url}")
    webbrowser.open(dashboard_url)
    time.sleep(2)
    
    # Suppress browser for tests
    os.environ['CLAUDE_MPM_NO_BROWSER'] = '1'
    
    print("\n📝 Testing various prompts that should trigger Task tool...")
    
    # Different prompt styles that might trigger Task tool
    test_scenarios = [
        {
            "prompt": "I need the research agent to analyze the structure of the hooks system in this codebase",
            "expected": "Should delegate to research agent"
        },
        {
            "prompt": "Can you get an engineer to implement a new feature for logging user actions?",
            "expected": "Should delegate to engineer agent"
        },
        {
            "prompt": "Ask documentation agent to write a guide about the monitoring system",
            "expected": "Should delegate to documentation agent"
        },
        {
            "prompt": "Please analyze the security of the authentication system",
            "expected": "Might delegate to security agent"
        },
        {
            "prompt": "Research: investigate the websocket implementation",
            "expected": "Research prefix might trigger delegation"
        },
        {
            "prompt": "QA: test the monitoring dashboard functionality",
            "expected": "QA prefix might trigger delegation"
        }
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"\n{i}. {scenario['expected']}")
        print(f"   Prompt: '{scenario['prompt']}'")
        
        cmd = [
            sys.executable, "-m", "claude_mpm", "run",
            "-i", scenario['prompt'],
            "--non-interactive",
            "--monitor"
        ]
        
        print("   Running...")
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Check for Task tool indicators
        task_indicators = [
            "Task(",
            "task tool",
            "Task tool",
            "delegating",
            "delegation",
            "subagent_type",
            "I'll ask the",
            "I'll delegate"
        ]
        
        found_indicators = []
        for indicator in task_indicators:
            if indicator.lower() in result.stdout.lower():
                found_indicators.append(indicator)
        
        if found_indicators:
            print(f"   ✅ Found delegation indicators: {', '.join(found_indicators)}")
        else:
            print("   ⚠️ No clear delegation indicators found")
        
        # Check stderr for hook events (if debug is on)
        if "pre_tool" in result.stderr and "Task" in result.stderr:
            print("   ✅ Task tool event detected in debug output")
        
        time.sleep(1)
    
    print("\n" + "=" * 60)
    print("📊 Dashboard Check Instructions:")
    print("\n1. Switch to the 'Agents' tab")
    print("   - If empty, no Task tool events were captured")
    print("   - If populated, you should see agent delegations")
    
    print("\n2. Switch to 'Events' tab")
    print("   - Look for 'hook.pre_tool' events")
    print("   - Click on them to see if any have tool_name='Task'")
    print("   - This will confirm if Task tool is being used")
    
    print("\n3. Check 'Tools' tab")
    print("   - Should show all tool usage")
    print("   - Look for 'Task' entries")
    
    print("\n💡 Common Issues:")
    print("- Claude Code might handle some requests directly without Task tool")
    print("- Simple requests might not trigger agent delegation")
    print("- The Task tool is only used for complex multi-step tasks")
    
    print("\n🔧 Workarounds:")
    print("1. Use more complex, multi-step requests")
    print("2. Explicitly mention 'delegate' or 'ask [agent] to'")
    print("3. Use agent prefixes like 'Research:', 'QA:', etc.")
    print("4. Request tasks that clearly need specialized agents")

if __name__ == "__main__":
    main()