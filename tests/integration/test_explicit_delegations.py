#!/usr/bin/env python3
"""Test subprocess orchestration with explicit delegation request."""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.orchestration.subprocess_orchestrator import SubprocessOrchestrator

def main():
    print("🚀 Testing Subprocess Orchestration with Explicit Delegations")
    print("=" * 80)
    
    # Clean logs
    claude_mpm_dir = Path.cwd() / ".claude-mpm"
    if claude_mpm_dir.exists():
        import shutil
        shutil.rmtree(claude_mpm_dir)
    
    # Create orchestrator
    orchestrator = SubprocessOrchestrator(log_level="DEBUG")
    
    # Test prompt that explicitly requests delegations
    test_prompt = """As the Project Manager, please delegate the following tasks to the appropriate agents using the delegation format:

1. Create a Python module for calculating prime numbers
2. Write comprehensive unit tests for the module
3. Create documentation for the module

Use this format for each delegation:
**[Agent Name]**: [Task description]"""
    
    print(f"Test prompt:\n{'-'*80}\n{test_prompt}\n{'-'*80}\n")
    
    # Run orchestration
    print("Running orchestration...\n")
    orchestrator.run_non_interactive(test_prompt)
    
    # Check logs
    print("\n" + "=" * 80)
    print("📊 CHECKING LOGS")
    print("=" * 80)
    
    # System logs
    system_log = claude_mpm_dir / "logs" / "system" / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
    if system_log.exists():
        print("\n📁 System Log:")
        with open(system_log, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    print(f"  [{entry['timestamp'][-12:]}] {entry['message'][:80]}...")
                except:
                    pass
    
    # Delegation logs
    session_dirs = list((claude_mpm_dir / "logs" / "sessions").iterdir())
    if session_dirs:
        latest_session = sorted(session_dirs)[-1]
        delegation_log = latest_session / "delegations.jsonl"
        if delegation_log.exists():
            print("\n📁 Delegations:")
            with open(delegation_log, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        print(f"  PM Task: {entry['pm_task'][:60]}...")
                        print(f"  Delegations: {entry['delegation_count']}")
                        for d in entry['delegations']:
                            print(f"    - {d['agent']}: {d['task'][:50]}...")
                    except:
                        pass
    
    # Agent logs
    agent_log_dir = claude_mpm_dir / "logs" / "agents"
    if agent_log_dir.exists() and any(agent_log_dir.iterdir()):
        print("\n📁 Agent Executions:")
        for agent_dir in agent_log_dir.iterdir():
            if agent_dir.is_dir():
                agent_log = agent_dir / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
                if agent_log.exists():
                    print(f"\n  {agent_dir.name}:")
                    with open(agent_log, 'r') as f:
                        for line in f:
                            try:
                                entry = json.loads(line)
                                status = "✓" if entry['success'] else "✗"
                                print(f"    {status} Task: {entry['task'][:50]}...")
                                print(f"      Tokens: {entry['tokens']}, Time: {entry['execution_time']:.1f}s")
                            except:
                                pass
    
    # Stats
    stats_file = claude_mpm_dir / "stats" / "agent_stats.json"
    if stats_file.exists():
        print("\n📁 Statistics:")
        with open(stats_file, 'r') as f:
            stats = json.load(f)
            today = datetime.now().strftime("%Y-%m-%d")
            if today in stats:
                today_stats = stats[today]
                print(f"  Total subprocess calls: {today_stats.get('total_calls', 0)}")
                if today_stats.get('by_agent'):
                    print("  Agents used:")
                    for agent, data in today_stats['by_agent'].items():
                        print(f"    - {agent}: {data['calls']} calls")

if __name__ == "__main__":
    main()