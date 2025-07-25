#!/usr/bin/env python3
"""Test subprocess orchestration with Task tool disabled."""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.orchestration.subprocess_orchestrator import SubprocessOrchestrator
from claude_mpm.core.claude_launcher import ClaudeLauncher

def main():
    print("🚀 Testing Subprocess Orchestration (Task tool disabled)")
    print("=" * 80)
    
    # Clean logs
    claude_mpm_dir = Path.cwd() / ".claude-mpm"
    if claude_mpm_dir.exists():
        import shutil
        shutil.rmtree(claude_mpm_dir)
    
    # Create orchestrator - we'll need to modify it to disable Task tool
    orchestrator = SubprocessOrchestrator(log_level="DEBUG")
    
    # Override the launcher to add --disable-tools Task
    original_launch = orchestrator.launcher.launch_oneshot
    def launch_with_disabled_task(*args, **kwargs):
        # Add extra args to disable Task tool
        if 'extra_args' not in kwargs:
            kwargs['extra_args'] = []
        kwargs['extra_args'].extend(['--disable-tools', 'Task'])
        return original_launch(*args, **kwargs)
    
    orchestrator.launcher.launch_oneshot = launch_with_disabled_task
    
    # Test prompt
    test_prompt = """Create a Python module for calculating fibonacci numbers with:
1. Both recursive and iterative implementations
2. Unit tests for both implementations
3. Documentation

Please delegate these tasks to the appropriate agents."""
    
    print(f"Test prompt:\n{'-'*80}\n{test_prompt}\n{'-'*80}\n")
    print("\nNote: Task tool is disabled, so PM must use delegation format")
    print("Expected format: **[Agent Name]**: [Task description]\n")
    
    # Run orchestration
    print("Running orchestration...\n")
    orchestrator.run_non_interactive(test_prompt)
    
    # Check results
    print("\n" + "=" * 80)
    print("📊 RESULTS")
    print("=" * 80)
    
    # Check delegations
    session_dirs = list((claude_mpm_dir / "logs" / "sessions").iterdir())
    if session_dirs:
        latest_session = sorted(session_dirs)[-1]
        delegation_log = latest_session / "delegations.jsonl"
        if delegation_log.exists():
            print("\n✓ Delegations detected and logged:")
            with open(delegation_log, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        print(f"\n  Total delegations: {entry['delegation_count']}")
                        for d in entry['delegations']:
                            print(f"  - {d['agent']}: {d['task'][:60]}...")
                    except:
                        pass
    
    # Check agent logs
    agent_log_dir = claude_mpm_dir / "logs" / "agents"
    if agent_log_dir.exists() and any(agent_log_dir.iterdir()):
        print("\n✓ Agent subprocesses executed:")
        for agent_dir in agent_log_dir.iterdir():
            if agent_dir.is_dir():
                agent_log = agent_dir / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
                if agent_log.exists():
                    with open(agent_log, 'r') as f:
                        for line in f:
                            try:
                                entry = json.loads(line)
                                status = "✓" if entry['success'] else "✗"
                                print(f"\n  {agent_dir.name} agent:")
                                print(f"    {status} Task: {entry['task'][:50]}...")
                                print(f"    Execution time: {entry['execution_time']:.1f}s")
                                print(f"    Tokens used: {entry['tokens']}")
                                if 'prompt' in entry:  # DEBUG mode includes prompts
                                    print(f"    Prompt preview: {entry['prompt'][:100]}...")
                                if 'response' in entry:
                                    print(f"    Response preview: {entry['response'][:100]}...")
                            except:
                                pass
    else:
        print("\n✗ No agent subprocesses were executed")
    
    # Show statistics
    stats_file = claude_mpm_dir / "stats" / "agent_stats.json"
    if stats_file.exists():
        with open(stats_file, 'r') as f:
            stats = json.load(f)
            today = datetime.now().strftime("%Y-%m-%d")
            if today in stats and stats[today].get('total_calls', 0) > 0:
                print(f"\n✓ Statistics:")
                print(f"  Total subprocess calls: {stats[today]['total_calls']}")
                print(f"  Total tokens used: {stats[today]['total_tokens']:,}")
                print(f"  Total execution time: {stats[today]['total_time_seconds']:.1f}s")
    
    # List all log files
    print("\n📁 All log files created:")
    for root, dirs, files in os.walk(claude_mpm_dir / "logs"):
        for file in files:
            if file.endswith('.jsonl'):
                file_path = Path(root) / file
                size = file_path.stat().st_size
                print(f"  {file_path.relative_to(claude_mpm_dir)} ({size:,} bytes)")

if __name__ == "__main__":
    main()