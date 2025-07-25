#!/usr/bin/env python3
"""Simple subprocess test with increased timeout."""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.orchestration.subprocess_orchestrator import SubprocessOrchestrator

def main():
    print("🚀 Simple Subprocess Orchestration Test")
    print("=" * 80)
    
    # Clean logs
    claude_mpm_dir = Path.cwd() / ".claude-mpm"
    if claude_mpm_dir.exists():
        import shutil
        shutil.rmtree(claude_mpm_dir)
    
    # Create custom orchestrator with longer timeout
    class CustomOrchestrator(SubprocessOrchestrator):
        def run_non_interactive(self, user_input: str):
            # Increase timeout
            original_timeout = 30
            
            # Override the PM launch call
            original_launch = self.launcher.launch_oneshot
            def launch_with_timeout(*args, **kwargs):
                kwargs['timeout'] = 120  # 2 minutes instead of 30 seconds
                return original_launch(*args, **kwargs)
            
            self.launcher.launch_oneshot = launch_with_timeout
            
            # Call parent
            super().run_non_interactive(user_input)
    
    orchestrator = CustomOrchestrator(log_level="DEBUG")
    
    # Very simple prompt that should be quick to process
    test_prompt = """Please delegate these two simple tasks:
1. Create a hello world Python function
2. Write a test for the hello world function

Delegate using format: **Agent Name**: task"""
    
    print(f"Test prompt:\n{'-'*80}\n{test_prompt}\n{'-'*80}\n")
    print("\nTimeout increased to 120 seconds")
    print("Running orchestration...\n")
    
    orchestrator.run_non_interactive(test_prompt)
    
    # Check results
    print("\n" + "=" * 80)
    print("📊 RESULTS")
    print("=" * 80)
    
    # Check for delegations
    delegations_found = False
    agents_ran = False
    
    session_dirs = list((claude_mpm_dir / "logs" / "sessions").iterdir())
    if session_dirs:
        latest_session = sorted(session_dirs)[-1]
        delegation_log = latest_session / "delegations.jsonl"
        
        if delegation_log.exists():
            with open(delegation_log, 'r') as f:
                for line in f:
                    entry = json.loads(line)
                    if entry['delegation_count'] > 0:
                        delegations_found = True
                        print(f"\n✅ Found {entry['delegation_count']} delegations")
                        for d in entry['delegations']:
                            print(f"   - {d['agent']}: {d['task']}")
    
    # Check agent logs
    agent_log_dir = claude_mpm_dir / "logs" / "agents"
    if agent_log_dir.exists():
        for agent_dir in agent_log_dir.iterdir():
            if agent_dir.is_dir():
                agent_log = agent_dir / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
                if agent_log.exists() and agent_log.stat().st_size > 0:
                    agents_ran = True
                    print(f"\n✅ {agent_dir.name} agent subprocess ran")
                    with open(agent_log, 'r') as f:
                        for line in f:
                            entry = json.loads(line)
                            print(f"   Task: {entry['task'][:60]}...")
                            print(f"   Time: {entry['execution_time']:.1f}s, Tokens: {entry['tokens']}")
    
    if delegations_found and agents_ran:
        print("\n🎉 SUCCESS: PM delegated tasks and agent subprocesses executed!")
    elif delegations_found:
        print("\n⚠️  PARTIAL: Delegations detected but no agent subprocesses ran")
    else:
        print("\n❌ FAILED: No delegations detected")
    
    # Show stats
    stats_file = claude_mpm_dir / "stats" / "agent_stats.json"
    if stats_file.exists():
        with open(stats_file, 'r') as f:
            stats = json.load(f)
            today = datetime.now().strftime("%Y-%m-%d")
            if today in stats and stats[today]['total_calls'] > 0:
                print(f"\n📊 Total subprocess calls: {stats[today]['total_calls']}")
                print(f"   Total execution time: {stats[today]['total_time_seconds']:.1f}s")

if __name__ == "__main__":
    main()