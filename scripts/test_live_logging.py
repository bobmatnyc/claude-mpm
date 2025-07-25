#!/usr/bin/env python3
"""Test SubprocessOrchestrator with live log monitoring."""

import sys
import os
import json
import time
import threading
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from claude_mpm.orchestration.subprocess_orchestrator import SubprocessOrchestrator

def monitor_logs(stop_event):
    """Monitor logs in real-time."""
    log_dir = Path.cwd() / ".claude-mpm" / "logs"
    system_log = log_dir / "system" / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
    session_dir = log_dir / "sessions"
    
    last_positions = {}
    
    print("\n📊 LOG MONITOR STARTED")
    print("=" * 80)
    
    while not stop_event.is_set():
        # Monitor system log
        if system_log.exists():
            current_pos = last_positions.get(str(system_log), 0)
            try:
                with open(system_log, 'r') as f:
                    f.seek(current_pos)
                    new_lines = f.readlines()
                    if new_lines:
                        for line in new_lines:
                            try:
                                entry = json.loads(line)
                                print(f"[SYSTEM] {entry['timestamp'][-12:]} | {entry['level']:5} | {entry['component']:12} | {entry['message'][:60]}")
                            except:
                                pass
                    last_positions[str(system_log)] = f.tell()
            except:
                pass
        
        # Monitor agent logs
        agent_log_dir = log_dir / "agents"
        if agent_log_dir.exists():
            for agent_dir in agent_log_dir.iterdir():
                if agent_dir.is_dir():
                    agent_log = agent_dir / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
                    if agent_log.exists():
                        current_pos = last_positions.get(str(agent_log), 0)
                        try:
                            with open(agent_log, 'r') as f:
                                f.seek(current_pos)
                                new_lines = f.readlines()
                                if new_lines:
                                    for line in new_lines:
                                        try:
                                            entry = json.loads(line)
                                            status = "✓" if entry['success'] else "✗"
                                            print(f"[AGENT ] {entry['timestamp'][-12:]} | {status} | {entry['agent']:12} | Task: {entry['task'][:40]}... | {entry['tokens']} tokens | {entry['execution_time']:.1f}s")
                                        except:
                                            pass
                                last_positions[str(agent_log)] = f.tell()
                        except:
                            pass
        
        time.sleep(0.5)

def main():
    print("🚀 Claude MPM Subprocess Orchestration Test")
    print("=" * 80)
    
    # Clean up previous logs
    claude_mpm_dir = Path.cwd() / ".claude-mpm"
    if claude_mpm_dir.exists():
        import shutil
        shutil.rmtree(claude_mpm_dir)
        print("✓ Cleaned up previous logs")
    
    # Start log monitor in background
    stop_event = threading.Event()
    monitor_thread = threading.Thread(target=monitor_logs, args=(stop_event,))
    monitor_thread.daemon = True
    monitor_thread.start()
    
    # Create orchestrator
    print("✓ Creating SubprocessOrchestrator with DEBUG logging...")
    orchestrator = SubprocessOrchestrator(log_level="DEBUG")
    
    # Test prompt that will trigger delegations
    test_prompt = """Create a Python module for calculating fibonacci numbers with the following requirements:
    1. Implement both recursive and iterative versions
    2. Add memoization to the recursive version
    3. Include proper error handling
    4. Write comprehensive unit tests
    5. Add documentation"""
    
    print(f"\n📝 Test Prompt:")
    print("-" * 80)
    print(test_prompt)
    print("-" * 80)
    
    print("\n🔄 Running orchestration (this will create real subprocesses)...\n")
    
    # Run the orchestration
    orchestrator.run_non_interactive(test_prompt)
    
    # Give logs time to finish writing
    time.sleep(2)
    
    # Stop monitoring
    stop_event.set()
    monitor_thread.join()
    
    # Show final statistics
    print("\n📈 FINAL STATISTICS")
    print("=" * 80)
    
    stats_file = claude_mpm_dir / "stats" / "agent_stats.json"
    if stats_file.exists():
        with open(stats_file, 'r') as f:
            stats = json.load(f)
            today = datetime.now().strftime("%Y-%m-%d")
            if today in stats:
                today_stats = stats[today]
                print(f"Total Calls: {today_stats['total_calls']}")
                print(f"Total Tokens: {today_stats['total_tokens']:,}")
                print(f"Total Time: {today_stats['total_time_seconds']:.1f}s")
                print("\nBy Agent:")
                for agent, agent_stats in today_stats['by_agent'].items():
                    print(f"  {agent}:")
                    print(f"    Calls: {agent_stats['calls']}")
                    print(f"    Tokens: {agent_stats['tokens']:,}")
                    print(f"    Success Rate: {agent_stats['success_rate']:.0%}")
    
    # Show log file locations
    print("\n📁 LOG FILES CREATED")
    print("=" * 80)
    
    for root, dirs, files in os.walk(claude_mpm_dir / "logs"):
        for file in files:
            if file.endswith('.jsonl'):
                file_path = Path(root) / file
                size = file_path.stat().st_size
                print(f"  {file_path.relative_to(claude_mpm_dir)} ({size} bytes)")

if __name__ == "__main__":
    main()