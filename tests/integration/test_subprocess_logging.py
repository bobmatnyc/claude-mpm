#!/usr/bin/env python3
"""Test subprocess orchestration with logging - simple test case."""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.orchestration.subprocess_orchestrator import SubprocessOrchestrator

def main():
    print("🚀 Testing Subprocess Orchestration with Logging")
    print("=" * 80)
    
    # Clean logs
    claude_mpm_dir = Path.cwd() / ".claude-mpm"
    if claude_mpm_dir.exists():
        import shutil
        shutil.rmtree(claude_mpm_dir)
    
    # Create orchestrator
    print("Creating orchestrator...")
    orchestrator = SubprocessOrchestrator(log_level="DEBUG")
    
    # Simple test prompt
    test_prompt = "Create a simple hello world function in Python and write a test for it"
    
    print(f"\nTest prompt: {test_prompt}")
    print("\nRunning orchestration...\n")
    
    # Run orchestration
    try:
        orchestrator.run_non_interactive(test_prompt)
    except Exception as e:
        print(f"Error during orchestration: {e}")
    
    # Check logs
    print("\n" + "=" * 80)
    print("📊 CHECKING LOGS")
    print("=" * 80)
    
    # System logs
    system_log = claude_mpm_dir / "logs" / "system" / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
    if system_log.exists():
        print("\n📁 System Log Entries:")
        with open(system_log, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    print(f"  [{entry['level']}] {entry['component']}: {entry['message'][:80]}...")
                except:
                    pass
    
    # Agent logs
    agent_log_dir = claude_mpm_dir / "logs" / "agents"
    if agent_log_dir.exists():
        print("\n📁 Agent Logs:")
        for agent_dir in agent_log_dir.iterdir():
            if agent_dir.is_dir():
                print(f"\n  Agent: {agent_dir.name}")
                agent_log = agent_dir / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
                if agent_log.exists():
                    with open(agent_log, 'r') as f:
                        for line in f:
                            try:
                                entry = json.loads(line)
                                print(f"    Task: {entry['task'][:60]}...")
                                print(f"    Success: {entry['success']}, Tokens: {entry['tokens']}, Time: {entry['execution_time']:.1f}s")
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
                print(f"  Total calls: {today_stats.get('total_calls', 0)}")
                print(f"  Total tokens: {today_stats.get('total_tokens', 0)}")
                print(f"  Total time: {today_stats.get('total_time_seconds', 0):.1f}s")
    
    # List all log files
    print("\n📁 All Log Files:")
    for root, dirs, files in os.walk(claude_mpm_dir / "logs"):
        for file in files:
            if file.endswith('.jsonl'):
                file_path = Path(root) / file
                print(f"  {file_path.relative_to(claude_mpm_dir)}")

if __name__ == "__main__":
    main()