#!/usr/bin/env python3
"""Monitor subprocess orchestration in real-time."""

import sys
import os
import json
import time
import threading
import subprocess
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.orchestration.subprocess_orchestrator import SubprocessOrchestrator

def monitor_processes(stop_event):
    """Monitor for claude processes."""
    print("\n📊 PROCESS MONITOR")
    print("=" * 80)
    
    seen_pids = set()
    
    while not stop_event.is_set():
        try:
            # Check for claude processes
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True
            )
            
            claude_processes = []
            for line in result.stdout.split('\n'):
                if 'claude' in line and 'python' not in line:
                    parts = line.split()
                    if len(parts) > 1:
                        pid = parts[1]
                        if pid not in seen_pids:
                            seen_pids.add(pid)
                            cmd = ' '.join(parts[10:])[:80]
                            print(f"[NEW PROCESS] PID: {pid} | CMD: {cmd}...")
            
        except:
            pass
        
        time.sleep(0.5)

def main():
    print("🚀 Testing Subprocess Orchestration with Process Monitoring")
    print("=" * 80)
    
    # Clean logs
    claude_mpm_dir = Path.cwd() / ".claude-mpm"
    if claude_mpm_dir.exists():
        import shutil
        shutil.rmtree(claude_mpm_dir)
    
    # Start process monitor
    stop_event = threading.Event()
    monitor_thread = threading.Thread(target=monitor_processes, args=(stop_event,))
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # Create orchestrator
    orchestrator = SubprocessOrchestrator(log_level="DEBUG")
    
    # Test with a prompt that should work well with the PM role
    test_prompt = """I need to create a comprehensive Python package for mathematical operations. 

The package should include:
1. A module for basic arithmetic (add, subtract, multiply, divide)
2. Error handling for division by zero
3. Unit tests for all functions
4. Package documentation

As the Project Manager, please analyze this request and delegate the implementation tasks to the appropriate specialist agents. Use clear delegation format with **Agent Name**: task description."""
    
    print(f"Test prompt:\n{'-'*80}\n{test_prompt}\n{'-'*80}\n")
    
    # Run orchestration
    print("\nRunning orchestration (watching for subprocesses)...\n")
    
    start_time = time.time()
    orchestrator.run_non_interactive(test_prompt)
    duration = time.time() - start_time
    
    # Stop monitoring
    stop_event.set()
    monitor_thread.join()
    
    print(f"\nOrchestration completed in {duration:.1f} seconds")
    
    # Detailed analysis
    print("\n" + "=" * 80)
    print("📊 DETAILED ANALYSIS")
    print("=" * 80)
    
    # Check what happened
    session_dirs = list((claude_mpm_dir / "logs" / "sessions").iterdir())
    if session_dirs:
        latest_session = sorted(session_dirs)[-1]
        
        # Check delegations
        delegation_log = latest_session / "delegations.jsonl"
        if delegation_log.exists():
            print("\n✅ Delegations detected:")
            with open(delegation_log, 'r') as f:
                for line in f:
                    entry = json.loads(line)
                    print(f"  Count: {entry['delegation_count']}")
                    for d in entry['delegations']:
                        print(f"  - {d['agent']}: {d['task'][:60]}...")
        
        # Check system log for subprocess launches
        system_log = latest_session / "system.jsonl"
        if system_log.exists():
            print("\n📁 System activity:")
            with open(system_log, 'r') as f:
                for line in f:
                    entry = json.loads(line)
                    if "Invoking" in entry['message'] or "subprocess" in entry['message']:
                        print(f"  {entry['message']}")
    
    # Check agent logs
    agent_log_dir = claude_mpm_dir / "logs" / "agents"
    if agent_log_dir.exists() and any(agent_log_dir.iterdir()):
        print("\n✅ Agent executions logged:")
        for agent_dir in agent_log_dir.iterdir():
            if agent_dir.is_dir():
                agent_log = agent_dir / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
                if agent_log.exists():
                    count = len(open(agent_log).readlines())
                    print(f"  {agent_dir.name}: {count} execution(s)")
    
    # Show all created files
    print("\n📁 All files created:")
    for root, dirs, files in os.walk(claude_mpm_dir):
        level = root.replace(str(claude_mpm_dir), '').count(os.sep)
        if level < 3:  # Limit depth
            indent = '  ' * level
            print(f"{indent}{os.path.basename(root)}/")
            for file in files[:3]:  # Show first 3 files
                print(f"{indent}  {file}")

if __name__ == "__main__":
    main()