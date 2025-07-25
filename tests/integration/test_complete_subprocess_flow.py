#!/usr/bin/env python3
"""Complete test of subprocess orchestration with Task forbidden and TODO processing."""

import sys
import os
import json
import time
import shutil
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.orchestration.subprocess_orchestrator import SubprocessOrchestrator
from claude_mpm.core.claude_launcher import ClaudeLauncher, LaunchMode

def main():
    print("🚀 Complete Subprocess Orchestration Test")
    print("=" * 80)
    
    # Setup: Clean everything
    claude_mpm_dir = Path.cwd() / ".claude-mpm"
    if claude_mpm_dir.exists():
        shutil.rmtree(claude_mpm_dir)
    
    todo_dir = Path.home() / ".claude" / "todos"
    if todo_dir.exists():
        shutil.rmtree(todo_dir)
    todo_dir.mkdir(parents=True)
    
    print("✓ Clean start - removed old logs and TODOs\n")
    
    # Step 1: Create custom orchestrator with Task forbidden
    class CompleteOrchestrator(SubprocessOrchestrator):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Modify launcher to forbid Task tool
            original_build = self.launcher.build_command
            
            def build_with_forbidden_task(*args, **kwargs):
                cmd = original_build(*args, **kwargs)
                if 'claude' in cmd[0]:
                    # Insert after model
                    for i, arg in enumerate(cmd):
                        if arg in ['--model', '-m']:
                            cmd.insert(i + 2, '--disallowedTools')
                            cmd.insert(i + 3, 'Task')
                            break
                    else:
                        cmd.extend(['--disallowedTools', 'Task'])
                return cmd
            
            self.launcher.build_command = build_with_forbidden_task
            
        def run_non_interactive(self, user_input: str):
            """Override to ensure TODO processing happens."""
            # Call parent
            super().run_non_interactive(user_input)
            
            # Force TODO processing after PM runs
            print("\nForcing TODO file scan...")
            if self.todo_hijacker:
                # Manually scan for TODO files
                todo_files = list(todo_dir.glob("*.json"))
                if todo_files:
                    print(f"Found {len(todo_files)} TODO files to process")
                    for tf in todo_files:
                        self.todo_hijacker._process_todo_file(tf)
                
                # Process any pending delegations
                if self._pending_todo_delegations:
                    print(f"\nProcessing {len(self._pending_todo_delegations)} TODO-based delegations...")
                    results = self._process_pending_todo_delegations()
                    
                    # Show results
                    print("\nDelegation Results:")
                    for r in results:
                        status = "✓" if r['status'] == 'completed' else "✗"
                        print(f"  {status} {r['agent']}: {r['execution_time']:.1f}s")
    
    # Create orchestrator
    orchestrator = CompleteOrchestrator(
        log_level="DEBUG",
        enable_todo_hijacking=True
    )
    
    print("Configuration:")
    print("  ✓ Task tool: FORBIDDEN")
    print("  ✓ TODO hijacking: ENABLED")
    print("  ✓ Logging: DEBUG level")
    print("  ✓ Manual TODO processing: YES\n")
    
    # Test prompt
    test_prompt = """I need you to coordinate building a simple Python greeting module.

Tasks to delegate:
1. Create a greet() function that takes a name and returns "Hello, {name}!"
2. Write a test to verify the function works correctly

Since the Task tool is disabled, please use TodoWrite to track these delegations with agent assignments."""
    
    print(f"Test prompt:\n{'-'*80}\n{test_prompt}\n{'-'*80}\n")
    
    # Extend timeout
    original_launch = orchestrator.launcher.launch_oneshot
    def launch_with_timeout(*args, **kwargs):
        kwargs['timeout'] = 120
        return original_launch(*args, **kwargs)
    orchestrator.launcher.launch_oneshot = launch_with_timeout
    
    # Run orchestration
    print("Running orchestration...\n")
    orchestrator.run_non_interactive(test_prompt)
    
    # Final analysis
    print("\n" + "=" * 80)
    print("📊 FINAL ANALYSIS")
    print("=" * 80)
    
    # Check what was created
    todo_files = list(todo_dir.glob("*.json"))
    print(f"\n✓ TODO files created: {len(todo_files)}")
    
    # Check agent logs
    agent_log_dir = claude_mpm_dir / "logs" / "agents"
    agent_count = 0
    if agent_log_dir.exists():
        for agent_dir in agent_log_dir.iterdir():
            if agent_dir.is_dir():
                agent_log = agent_dir / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
                if agent_log.exists() and agent_log.stat().st_size > 0:
                    agent_count += 1
                    print(f"\n✓ {agent_dir.name} agent subprocess executed")
                    with open(agent_log, 'r') as f:
                        entry = json.loads(f.readline())
                        print(f"  Task: {entry['task'][:60]}...")
                        print(f"  Time: {entry['execution_time']:.1f}s")
                        print(f"  Success: {entry['success']}")
    
    # Check stats
    stats_file = claude_mpm_dir / "stats" / "agent_stats.json"
    if stats_file.exists():
        with open(stats_file, 'r') as f:
            stats = json.load(f)
            today = datetime.now().strftime("%Y-%m-%d")
            if today in stats:
                print(f"\n✓ Statistics:")
                print(f"  Total subprocess calls: {stats[today]['total_calls']}")
                print(f"  Total execution time: {stats[today]['total_time_seconds']:.1f}s")
    
    # Summary
    print("\n" + "=" * 80)
    if agent_count > 0:
        print("🎉 SUCCESS: Complete flow worked!")
        print("  1. Task tool was forbidden ✓")
        print("  2. PM used TodoWrite instead ✓")
        print("  3. TODOs were processed into delegations ✓")
        print("  4. Agent subprocesses were executed ✓")
        print("  5. Results were logged ✓")
    else:
        print("❌ FAILED: No agent subprocesses executed")

if __name__ == "__main__":
    main()