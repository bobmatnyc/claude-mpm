#!/usr/bin/env python3
"""Test all available agents with a simple 'hello world' request."""

import subprocess
import time
import webbrowser
from pathlib import Path
import sys

def main():
    print("🤖 Testing All Agents with Hello World")
    print("=" * 50)
    
    # List of all available agents based on the templates directory
    agents = [
        "general-purpose",
        "security", 
        "documentation",
        "engineer",
        "research",
        "qa",
        "version_control",
        "data_engineer",
        "ops",
        "test-agent"
    ]
    
    # Open the dashboard first
    dashboard_path = Path(__file__).parent / "claude_mpm_socketio_dashboard.html"
    dashboard_url = f"file://{dashboard_path}?autoconnect=true&port=8765"
    
    print(f"\n1. Opening monitoring dashboard...")
    webbrowser.open(dashboard_url)
    time.sleep(3)
    
    print("\n2. Testing each agent with 'hello world' request...")
    print("   Watch the dashboard for agent delegation events!\n")
    
    for agent in agents:
        print(f"\n🤖 Testing {agent} agent...")
        print("-" * 40)
        
        # Create a prompt that explicitly uses the Task tool to delegate to each agent
        prompt = f'Use the Task tool to ask the {agent} agent to respond with "hello world" in their own style'
        
        print(f"Prompt: {prompt}")
        
        # Run Claude with the agent delegation prompt
        cmd = [
            sys.executable, "-m", "claude_mpm", "run",
            "-i", prompt,
            "--non-interactive"
        ]
        
        start_time = time.time()
        result = subprocess.run(
            cmd,
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            timeout=30  # 30 second timeout per agent
        )
        duration = time.time() - start_time
        
        if result.returncode == 0:
            print(f"✅ Success (took {duration:.1f}s)")
            # Show a preview of the output
            output_lines = result.stdout.strip().split('\n')
            if output_lines:
                print(f"Output preview: {output_lines[-1][:100]}...")
        else:
            print(f"❌ Error: {result.stderr[:100]}")
        
        # Brief pause between agents
        time.sleep(2)
    
    print("\n" + "=" * 50)
    print("✅ All agents tested!")
    
    print("\n3. Check the dashboard for:")
    print("   📊 Filter by 'Hook' events to see agent delegations")
    print("   🔍 Look for 'hook.pre_tool' events with tool_name='Task'")
    print("   📝 Each event should show:")
    print("      - subagent_type: The agent that was called")
    print("      - prompt: The 'hello world' request sent to the agent")
    print("      - delegation_details: Additional information")
    print("\n   🏁 Look for 'hook.subagent_stop' events showing completion")
    
    print("\n4. Expected agent responses:")
    print("   - general-purpose: Standard hello world response")
    print("   - security: Security-focused greeting")
    print("   - documentation: Well-documented hello")
    print("   - engineer: Technical hello world")
    print("   - research: Analytical greeting")
    print("   - qa: Test-oriented hello")
    print("   - version_control: Git-style greeting")
    print("   - data_engineer: Data-focused hello")
    print("   - ops: Operations greeting")
    print("   - test-agent: Simple test response")
    
    print("\n💡 Tip: Click on any event in the dashboard to see full details!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\n\nError: {e}")