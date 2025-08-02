#!/usr/bin/env python3
"""Comprehensive test of all agents with hello world requests."""

import subprocess
import time
import webbrowser
from pathlib import Path
import sys
import json

def main():
    print("🤖 Comprehensive Agent Testing with Hello World")
    print("=" * 60)
    
    # All available agent types from the codebase
    agents = [
        ("general-purpose", "general assistant for various tasks"),
        ("security", "security analysis and vulnerability assessment"),
        ("documentation", "documentation creation and technical writing"),
        ("engineer", "software engineering and implementation"),
        ("research", "codebase analysis and investigation"),
        ("qa", "quality assurance and testing"),
        ("version_control", "git operations and version management"),
        ("data_engineer", "data processing and API integration"),
        ("ops", "deployment and infrastructure operations"),
        ("test-agent", "simple test agent for validation"),
        ("pm", "project management and coordination")  # Added PM agent
    ]
    
    # Open the dashboard
    dashboard_path = Path(__file__).parent / "claude_mpm_socketio_dashboard.html"
    dashboard_url = f"file://{dashboard_path}?autoconnect=true&port=8765"
    
    print(f"\n1. Opening monitoring dashboard...")
    print(f"   URL: {dashboard_url}")
    webbrowser.open(dashboard_url)
    time.sleep(3)
    
    print("\n2. Starting comprehensive agent tests...")
    print("   Each test will show:")
    print("   - Agent delegation in PreToolUse hook")
    print("   - SubagentStop event when agent completes")
    print("   - Agent's unique response style")
    print("\n" + "-" * 60)
    
    results = []
    
    for agent_type, description in agents:
        print(f"\n🤖 Testing {agent_type} agent")
        print(f"   Description: {description}")
        print("-" * 40)
        
        # Create specific prompts for each agent to demonstrate their capabilities
        if agent_type == "security":
            prompt = f'Use the Task tool to ask the {agent_type} agent to say hello and briefly mention what security means to them'
        elif agent_type == "documentation":
            prompt = f'Use the Task tool to ask the {agent_type} agent to say hello and describe their documentation philosophy in one sentence'
        elif agent_type == "engineer":
            prompt = f'Use the Task tool to ask the {agent_type} agent to say hello world as a code comment'
        elif agent_type == "qa":
            prompt = f'Use the Task tool to ask the {agent_type} agent to say hello and what makes a good test'
        elif agent_type == "research":
            prompt = f'Use the Task tool to ask the {agent_type} agent to say hello and their research approach in brief'
        elif agent_type == "version_control":
            prompt = f'Use the Task tool to ask the {agent_type} agent to say hello in a git commit message style'
        elif agent_type == "data_engineer":
            prompt = f'Use the Task tool to ask the {agent_type} agent to say hello and mention their favorite data format'
        elif agent_type == "ops":
            prompt = f'Use the Task tool to ask the {agent_type} agent to say hello from the operations center'
        elif agent_type == "pm":
            prompt = f'Use the Task tool to ask the {agent_type} agent to say hello and share a brief project management tip'
        else:
            prompt = f'Use the Task tool to ask the {agent_type} agent to respond with "hello world" in their own unique style'
        
        print(f"📝 Prompt: {prompt[:80]}...")
        
        # Run Claude with the agent delegation prompt
        cmd = [
            sys.executable, "-m", "claude_mpm", "run",
            "-i", prompt,
            "--non-interactive",
            "--monitor"  # Ensure WebSocket is enabled
        ]
        
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=Path(__file__).parent.parent,
                capture_output=True,
                text=True,
                timeout=45  # Increased timeout for complex agents
            )
            duration = time.time() - start_time
            
            if result.returncode == 0:
                print(f"✅ Success (took {duration:.1f}s)")
                # Extract the response
                output_lines = result.stdout.strip().split('\n')
                
                # Look for the agent's actual response
                agent_response = None
                for i, line in enumerate(output_lines):
                    if "hello" in line.lower() or "greet" in line.lower():
                        agent_response = line.strip()
                        # Try to get a few more lines for context
                        for j in range(i+1, min(i+3, len(output_lines))):
                            if output_lines[j].strip():
                                agent_response += " " + output_lines[j].strip()
                        break
                
                if agent_response:
                    print(f"🗨️  Response: {agent_response[:150]}...")
                else:
                    print(f"📄 Output: {output_lines[-1][:100]}..." if output_lines else "No output")
                
                results.append({
                    "agent": agent_type,
                    "status": "success",
                    "duration": duration,
                    "response": agent_response or output_lines[-1] if output_lines else ""
                })
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                print(f"❌ Error: {error_msg[:100]}...")
                results.append({
                    "agent": agent_type,
                    "status": "error",
                    "duration": duration,
                    "error": error_msg
                })
                
        except subprocess.TimeoutExpired:
            print(f"⏱️  Timeout after 45 seconds")
            results.append({
                "agent": agent_type,
                "status": "timeout",
                "duration": 45.0
            })
        except Exception as e:
            print(f"💥 Exception: {str(e)}")
            results.append({
                "agent": agent_type,
                "status": "exception",
                "error": str(e)
            })
        
        # Brief pause between agents
        time.sleep(2)
    
    # Summary report
    print("\n" + "=" * 60)
    print("📊 AGENT TEST SUMMARY")
    print("=" * 60)
    
    successful = [r for r in results if r["status"] == "success"]
    failed = [r for r in results if r["status"] != "success"]
    
    print(f"\n✅ Successful: {len(successful)}/{len(results)}")
    for r in successful:
        print(f"   - {r['agent']}: {r['duration']:.1f}s")
    
    if failed:
        print(f"\n❌ Failed: {len(failed)}")
        for r in failed:
            error = r.get('error', 'No error details')[:50]
            print(f"   - {r['agent']}: {r['status']} - {error}")
    
    # Dashboard guidance
    print("\n" + "=" * 60)
    print("📊 DASHBOARD ANALYSIS GUIDE")
    print("=" * 60)
    print("\n1. In the dashboard, look for these event patterns:")
    print("   🎯 UserPromptSubmit - Your initial request")
    print("   🔧 PreToolUse (tool='Task') - Agent delegation")
    print("   📝 Check 'subagent_type' field for the agent being called")
    print("   🏁 SubagentStop - Agent completed their task")
    
    print("\n2. Event flow for each test:")
    print("   1️⃣  UserPromptSubmit → Your request to use Task tool")
    print("   2️⃣  PreToolUse → Task tool invoked with agent type")
    print("   3️⃣  (Agent processes the request)")
    print("   4️⃣  SubagentStop → Agent completes")
    print("   5️⃣  PostToolUse → Task tool returns result")
    print("   6️⃣  Stop → Session ends")
    
    print("\n3. Click on events to see details:")
    print("   - Agent type in 'subagent_type' field")
    print("   - Full prompt sent to agent")
    print("   - Agent's response in result field")
    
    print("\n4. Use filters to focus:")
    print("   🔍 Filter: 'Task' - See only agent delegations")
    print("   🔍 Filter: 'subagent' - See agent completions")
    print("   🔍 Search for specific agent names")
    
    # Save results to file
    results_file = Path(__file__).parent / "agent_test_results.json"
    with open(results_file, 'w') as f:
        json.dump({
            "test_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_agents": len(agents),
            "successful": len(successful),
            "failed": len(failed),
            "results": results
        }, f, indent=2)
    
    print(f"\n💾 Results saved to: {results_file}")
    print("\n✨ All tests completed! Check the dashboard for detailed event analysis.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()