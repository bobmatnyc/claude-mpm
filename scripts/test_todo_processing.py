#!/usr/bin/env python3
"""Test TODO processing with manual trigger."""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.orchestration.subprocess_orchestrator import SubprocessOrchestrator

def main():
    print("🚀 Testing TODO Processing")
    print("=" * 80)
    
    # Check existing TODO file
    todo_dir = Path.home() / ".claude" / "todos"
    todo_files = list(todo_dir.glob("*.json"))
    
    if todo_files:
        print(f"✓ Found {len(todo_files)} TODO file(s)")
        for tf in todo_files:
            print(f"  - {tf.name}")
            with open(tf, 'r') as f:
                todos = json.load(f)
                print(f"    Contains {len(todos)} todos")
                for todo in todos[:2]:  # Show first 2
                    print(f"      • {todo['content'][:60]}...")
    
    # Clean logs
    claude_mpm_dir = Path.cwd() / ".claude-mpm"
    if claude_mpm_dir.exists():
        import shutil
        shutil.rmtree(claude_mpm_dir)
    
    # Create orchestrator with TODO hijacking
    orchestrator = SubprocessOrchestrator(
        log_level="DEBUG",
        enable_todo_hijacking=True
    )
    
    print("\n✓ TODO hijacker initialized")
    print("✓ Monitoring directory:", todo_dir)
    
    # Process pending TODO delegations manually
    print("\nProcessing TODO delegations...")
    
    # Give the hijacker time to process existing files
    time.sleep(2)
    
    # Check if delegations were queued
    if orchestrator._pending_todo_delegations:
        print(f"\n✅ Found {len(orchestrator._pending_todo_delegations)} pending delegations")
        for d in orchestrator._pending_todo_delegations:
            print(f"  - {d['agent']}: {d['task'][:60]}...")
        
        # Process them
        print("\nRunning delegated tasks as subprocesses...")
        results = orchestrator._process_pending_todo_delegations()
        
        print(f"\n✅ Processed {len(results)} delegations")
        for r in results:
            status = "✓" if r['status'] == 'completed' else "✗"
            print(f"  {status} {r['agent']}: {r['execution_time']:.1f}s, {r['tokens']} tokens")
    else:
        print("\n❌ No pending TODO delegations found")
        print("\nPossible issues:")
        print("- TODO file format not recognized")
        print("- TODO hijacker didn't process the file")
        print("- Delegations weren't created from TODOs")
    
    # Check logs
    agent_log_dir = claude_mpm_dir / "logs" / "agents"
    if agent_log_dir.exists() and any(agent_log_dir.iterdir()):
        print("\n✅ Agent logs created:")
        for agent_dir in agent_log_dir.iterdir():
            if agent_dir.is_dir():
                agent_log = agent_dir / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
                if agent_log.exists():
                    size = agent_log.stat().st_size
                    print(f"  - {agent_dir.name}: {size} bytes")

if __name__ == "__main__":
    main()