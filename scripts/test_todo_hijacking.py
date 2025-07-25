#!/usr/bin/env python3
"""Test TODO hijacking to capture delegations."""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.orchestration.subprocess_orchestrator import SubprocessOrchestrator

def main():
    print("🚀 Testing TODO Hijacking for Delegation Capture")
    print("=" * 80)
    
    # Clean up
    claude_mpm_dir = Path.cwd() / ".claude-mpm"
    if claude_mpm_dir.exists():
        import shutil
        shutil.rmtree(claude_mpm_dir)
    
    # Create orchestrator with TODO hijacking enabled
    orchestrator = SubprocessOrchestrator(
        log_level="DEBUG",
        enable_todo_hijacking=True  # This is the key!
    )
    
    print("✓ TODO hijacking ENABLED")
    print("  This will monitor TodoWrite usage and convert to delegations\n")
    
    # Test prompt that encourages TODO usage
    test_prompt = """Please help me create a Python calculator module. I need:

1. Basic arithmetic functions (add, subtract, multiply, divide)
2. Error handling for division by zero
3. Unit tests for all functions
4. Documentation

Please use the TodoWrite tool to track these tasks and delegate them appropriately."""
    
    print(f"Test prompt:\n{'-'*80}\n{test_prompt}\n{'-'*80}\n")
    print("\nRunning orchestration with TODO monitoring...\n")
    
    # Run with extended timeout
    original_launch = orchestrator.launcher.launch_oneshot
    def launch_with_timeout(*args, **kwargs):
        kwargs['timeout'] = 120
        return original_launch(*args, **kwargs)
    orchestrator.launcher.launch_oneshot = launch_with_timeout
    
    orchestrator.run_non_interactive(test_prompt)
    
    # Analysis
    print("\n" + "=" * 80)
    print("📊 TODO HIJACKING ANALYSIS")
    print("=" * 80)
    
    # Check if TODO delegations were processed
    todo_delegations_found = False
    
    # Check logs for TODO activity
    system_log = claude_mpm_dir / "logs" / "system" / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
    if system_log.exists():
        print("\n📁 System activity:")
        with open(system_log, 'r') as f:
            for line in f:
                entry = json.loads(line)
                msg = entry['message']
                if 'TODO' in msg or 'todo' in msg.lower():
                    print(f"  {msg}")
                    if 'delegation' in msg.lower():
                        todo_delegations_found = True
    
    # Check agent logs to see if TODO-based delegations ran
    agent_log_dir = claude_mpm_dir / "logs" / "agents"
    agent_executions = 0
    if agent_log_dir.exists():
        print("\n📁 Agent executions:")
        for agent_dir in agent_log_dir.iterdir():
            if agent_dir.is_dir():
                agent_log = agent_dir / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
                if agent_log.exists() and agent_log.stat().st_size > 0:
                    with open(agent_log, 'r') as f:
                        lines = f.readlines()
                        agent_executions += len(lines)
                        print(f"\n  {agent_dir.name}: {len(lines)} execution(s)")
                        for line in lines:
                            entry = json.loads(line)
                            print(f"    Task: {entry['task'][:60]}...")
                            # Check metadata for TODO origin
                            if 'metadata' in entry and entry['metadata'].get('source') == 'todo':
                                print(f"    ✓ This was from TODO hijacking!")
                                todo_delegations_found = True
    
    # Check delegation logs
    session_dirs = list((claude_mpm_dir / "logs" / "sessions").iterdir())
    if session_dirs:
        latest_session = sorted(session_dirs)[-1]
        delegation_log = latest_session / "delegations.jsonl"
        if delegation_log.exists():
            print("\n📁 Delegations logged:")
            with open(delegation_log, 'r') as f:
                for line in f:
                    entry = json.loads(line)
                    if entry.get('source') == 'todo':
                        print(f"  ✓ TODO-based delegation with {entry['delegation_count']} tasks")
                        todo_delegations_found = True
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY")
    print("=" * 80)
    
    if todo_delegations_found and agent_executions > 0:
        print("✅ SUCCESS: TODO hijacking worked! TODOs were converted to agent delegations")
        print(f"   {agent_executions} agent subprocess(es) were executed")
    elif agent_executions > 0:
        print("⚠️  PARTIAL: Agent subprocesses ran but TODO origin unclear")
    else:
        print("❌ FAILED: No TODO-based delegations were captured")
        print("\nPossible reasons:")
        print("- PM didn't use TodoWrite tool")
        print("- TODO hijacking didn't detect the TODO file writes")
        print("- Claude might be preventing TodoWrite in subprocess mode")
    
    # Check if TODO files exist
    print("\n📁 Checking for TODO files:")
    todo_patterns = ["**/TODO*.md", "**/todo*.md", "**/*todo*.txt"]
    todo_files_found = False
    for pattern in todo_patterns:
        import glob
        files = glob.glob(pattern, recursive=True)
        for f in files:
            print(f"  Found: {f}")
            todo_files_found = True
    
    if not todo_files_found:
        print("  No TODO files found in project")

if __name__ == "__main__":
    main()