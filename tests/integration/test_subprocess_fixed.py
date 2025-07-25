#!/usr/bin/env python3
"""Test subprocess orchestration with proper Task tool disabling."""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.orchestration.subprocess_orchestrator import SubprocessOrchestrator
from claude_mpm.core.claude_launcher import ClaudeLauncher, LaunchMode

def main():
    print("🚀 Testing Subprocess Orchestration (with modified launcher)")
    print("=" * 80)
    
    # Clean logs
    claude_mpm_dir = Path.cwd() / ".claude-mpm"
    if claude_mpm_dir.exists():
        import shutil
        shutil.rmtree(claude_mpm_dir)
    
    # Create custom orchestrator that modifies the command
    class CustomSubprocessOrchestrator(SubprocessOrchestrator):
        def run_non_interactive(self, user_input: str):
            # Store original method
            original_build = self.launcher.build_command
            
            # Override build_command to add --disable-tools Task
            def build_with_disabled_task(*args, **kwargs):
                cmd = original_build(*args, **kwargs)
                # Insert --disable-tools Task before other args
                if 'claude' in cmd[0]:
                    cmd.extend(['--disable-tools', 'Task'])
                return cmd
            
            self.launcher.build_command = build_with_disabled_task
            
            # Call parent method
            super().run_non_interactive(user_input)
            
            # Restore original
            self.launcher.build_command = original_build
    
    # Create orchestrator
    orchestrator = CustomSubprocessOrchestrator(log_level="DEBUG")
    
    # Test prompt that should trigger delegations
    test_prompt = """As the Project Manager, I need you to coordinate the following project:

Create a Python fibonacci module with these requirements:
1. Implement both recursive and iterative versions
2. Add proper error handling for negative numbers
3. Write comprehensive unit tests
4. Create documentation

Please delegate these tasks to the appropriate agents using the format:
**[Agent Name]**: [Specific task description]"""
    
    print(f"Test prompt:\n{'-'*80}\n{test_prompt}\n{'-'*80}\n")
    print("\nNote: Task tool is disabled via --disable-tools Task")
    print("PM should output delegation instructions in the specified format\n")
    
    # Run orchestration
    print("Running orchestration...\n")
    try:
        orchestrator.run_non_interactive(test_prompt)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    # Check results
    print("\n" + "=" * 80)
    print("📊 ANALYSIS")
    print("=" * 80)
    
    # Check PM response in delegations log
    session_dirs = list((claude_mpm_dir / "logs" / "sessions").iterdir())
    if session_dirs:
        latest_session = sorted(session_dirs)[-1]
        delegation_log = latest_session / "delegations.jsonl"
        if delegation_log.exists():
            print("\n✅ Delegations were detected!")
            with open(delegation_log, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        print(f"\nDelegation count: {entry['delegation_count']}")
                        for i, d in enumerate(entry['delegations'], 1):
                            print(f"\n{i}. {d['agent']} Agent:")
                            print(f"   Task: {d['task']}")
                            print(f"   Format: {d.get('format', 'unknown')}")
                        
                        if 'pm_response' in entry:
                            print("\nPM Response preview:")
                            print("-" * 40)
                            print(entry['pm_response'][:500] + "..." if len(entry['pm_response']) > 500 else entry['pm_response'])
                    except Exception as e:
                        print(f"Error parsing delegation: {e}")
        else:
            print("\n❌ No delegations were detected")
    
    # Check if subprocesses ran
    agent_log_dir = claude_mpm_dir / "logs" / "agents"
    if agent_log_dir.exists() and any(agent_log_dir.iterdir()):
        print("\n✅ Agent subprocesses executed:")
        total_agent_calls = 0
        for agent_dir in agent_log_dir.iterdir():
            if agent_dir.is_dir():
                agent_log = agent_dir / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
                if agent_log.exists():
                    with open(agent_log, 'r') as f:
                        lines = f.readlines()
                        total_agent_calls += len(lines)
                        print(f"\n  {agent_dir.name} agent: {len(lines)} execution(s)")
                        for line in lines:
                            try:
                                entry = json.loads(line)
                                print(f"    - Task: {entry['task'][:60]}...")
                                print(f"      Success: {entry['success']}, Time: {entry['execution_time']:.1f}s, Tokens: {entry['tokens']}")
                            except:
                                pass
        print(f"\nTotal agent subprocess calls: {total_agent_calls}")
    else:
        print("\n❌ No agent subprocesses were executed")
        print("   This means delegations were not detected in PM's response")

if __name__ == "__main__":
    main()