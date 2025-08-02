#!/usr/bin/env python3
"""Test the agent type tracking fix for SubagentStop events."""

import os
import subprocess
import time
import webbrowser
from pathlib import Path
import sys

def main():
    print("🧪 Testing Agent Type Tracking Fix")
    print("=" * 60)
    
    # Open the dashboard first
    dashboard_path = Path(__file__).parent / "claude_mpm_socketio_dashboard.html"
    dashboard_url = f"file://{dashboard_path}?autoconnect=true&port=8765"
    
    print(f"\n📊 Opening dashboard: {dashboard_url}")
    webbrowser.open(dashboard_url)
    time.sleep(2)
    
    # Suppress automatic browser opening for tests
    os.environ['CLAUDE_MPM_NO_BROWSER'] = '1'
    
    print("\n🔧 Testing agent delegations with tracking fix...")
    
    # Test cases with different agent types
    test_cases = [
        {
            "prompt": "Ask the research agent to analyze the hook handler code",
            "expected_agent": "research",
            "description": "Research agent delegation"
        },
        {
            "prompt": "Delegate to the engineer agent to implement a logging feature",
            "expected_agent": "engineer", 
            "description": "Engineer agent delegation"
        },
        {
            "prompt": "Have the documentation agent explain how hooks work",
            "expected_agent": "documentation",
            "description": "Documentation agent delegation"
        },
        {
            "prompt": "Get the QA agent to test the monitoring system",
            "expected_agent": "qa",
            "description": "QA agent delegation"
        },
        {
            "prompt": "Ask the security agent to review authentication",
            "expected_agent": "security",
            "description": "Security agent delegation"
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. {test['description']}")
        print(f"   Prompt: {test['prompt']}")
        print(f"   Expected agent: {test['expected_agent']}")
        
        cmd = [
            sys.executable, "-m", "claude_mpm", "run",
            "-i", test['prompt'],
            "--non-interactive",
            "--monitor"
        ]
        
        print("   Running command...")
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            timeout=45
        )
        
        if result.returncode == 0:
            print("   ✅ Command completed")
        else:
            print(f"   ⚠️ Command failed: {result.stderr[:100]}")
        
        time.sleep(2)
    
    print("\n" + "=" * 60)
    print("✅ Test complete!")
    print("\n🔍 Check the dashboard:")
    print("1. Go to the 'Agents' tab")
    print("   - Should show all delegated agents with correct types")
    print("   - Click on each to see delegation details")
    print("\n2. Look for SubagentStop events in 'Events' tab")
    print("   - Should now show correct agent_type (not 'unknown')")
    print("   - agent_id should match the agent type")
    print("\n3. Click on SubagentStop events")
    print("   - Event Analysis should show the correct agent type")
    print("   - Full Event JSON should confirm the fix")
    print("\n💡 Success indicators:")
    print("- No more 'unknown' agent types in SubagentStop events")
    print("- Agent types match the delegated agents (research, engineer, etc.)")
    print("- Tracking persists across the delegation lifecycle")

if __name__ == "__main__":
    main()