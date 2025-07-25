#!/usr/bin/env python3
"""Test subprocess orchestration with Task tool forbidden."""

import sys
import os
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.orchestration.subprocess_orchestrator import SubprocessOrchestrator
from claude_mpm.core.claude_launcher import ClaudeLauncher, LaunchMode

def main():
    print("🚀 Testing Subprocess Orchestration with Task Tool Forbidden")
    print("=" * 80)
    
    # Clean up
    claude_mpm_dir = Path.cwd() / ".claude-mpm"
    if claude_mpm_dir.exists():
        import shutil
        shutil.rmtree(claude_mpm_dir)
    
    # Clean TODO directory
    todo_dir = Path.home() / ".claude" / "todos"
    if todo_dir.exists():
        import shutil
        shutil.rmtree(todo_dir)
        todo_dir.mkdir(parents=True)
    print("✓ Cleaned up old TODO files")
    
    # Create custom orchestrator that forbids Task tool
    class ForbiddenTaskOrchestrator(SubprocessOrchestrator):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Override the launcher's build_command method
            original_build = self.launcher.build_command
            
            def build_with_forbidden_task(*args, **kwargs):
                cmd = original_build(*args, **kwargs)
                # Add --disallowedTools Task after claude command
                if 'claude' in cmd[0]:
                    # Find where to insert (after model specification)
                    insert_idx = 1
                    for i, arg in enumerate(cmd):
                        if arg in ['--model', '-m']:
                            insert_idx = i + 2
                            break
                    cmd.insert(insert_idx, '--disallowedTools')
                    cmd.insert(insert_idx + 1, 'Task')
                return cmd
            
            self.launcher.build_command = build_with_forbidden_task
    
    # Create orchestrator with TODO hijacking
    orchestrator = ForbiddenTaskOrchestrator(
        log_level="DEBUG",
        enable_todo_hijacking=True
    )
    
    print("✓ Task tool FORBIDDEN via --disallowedTools")
    print("✓ TODO hijacking ENABLED")
    print("✓ TODO directory cleaned\n")
    
    # Test prompt that should force delegation format output
    test_prompt = """As Project Manager, I need to coordinate creating a Python math utilities module.

Requirements:
1. Create a module with factorial and fibonacci functions
2. Add input validation and error handling
3. Write comprehensive unit tests
4. Create usage documentation

Since you cannot use the Task tool, please output clear delegation instructions using this format:
**[Agent Name]**: [Specific task description]

After listing delegations, you may also use TodoWrite to track the tasks."""
    
    print(f"Test prompt:\n{'-'*80}\n{test_prompt}\n{'-'*80}\n")
    print("Running orchestration (Task tool forbidden)...\n")
    
    # Extend timeout
    original_launch = orchestrator.launcher.launch_oneshot
    def launch_with_timeout(*args, **kwargs):
        kwargs['timeout'] = 120
        return original_launch(*args, **kwargs)
    orchestrator.launcher.launch_oneshot = launch_with_timeout
    
    orchestrator.run_non_interactive(test_prompt)
    
    # Analysis
    print("\n" + "=" * 80)
    print("📊 ANALYSIS")
    print("=" * 80)
    
    # Check PM response
    delegations_found = False
    todo_delegations = False
    agent_executions = 0
    
    # Check delegation logs
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
                        print(f"\n✅ Found {entry['delegation_count']} delegations in PM response")
                        for d in entry['delegations']:
                            print(f"   - {d['agent']}: {d['task'][:60]}...")
                            if d.get('format') == 'markdown':
                                print(f"     (Detected from markdown format)")
    
    # Check agent executions
    agent_log_dir = claude_mpm_dir / "logs" / "agents"
    if agent_log_dir.exists():
        for agent_dir in agent_log_dir.iterdir():
            if agent_dir.is_dir():
                agent_log = agent_dir / f"{datetime.now().strftime('%Y%m%d')}.jsonl"
                if agent_log.exists() and agent_log.stat().st_size > 0:
                    with open(agent_log, 'r') as f:
                        lines = f.readlines()
                        agent_executions += len(lines)
                        print(f"\n✅ {agent_dir.name} agent: {len(lines)} subprocess execution(s)")
    
    # Check TODO files created
    todo_files = list(todo_dir.glob("*.json"))
    if todo_files:
        print(f"\n✅ Found {len(todo_files)} TODO file(s) created")
        todo_delegations = True
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY:")
    if delegations_found and agent_executions > 0:
        print("🎉 SUCCESS: Task tool was forbidden, PM output delegations, and subprocesses ran!")
    elif delegations_found:
        print("✅ PARTIAL: PM output delegations (Task forbidden worked) but no subprocesses ran")
    elif todo_delegations:
        print("⚠️  TODO files created but not converted to delegations")
    else:
        print("❌ FAILED: No delegations detected")
    
    print(f"\nStats:")
    print(f"  - Delegations in PM response: {'Yes' if delegations_found else 'No'}")
    print(f"  - Agent subprocesses executed: {agent_executions}")
    print(f"  - TODO files created: {len(todo_files)}")
    
    # Show command that was used
    test_cmd = ['claude', '--model', 'opus', '--disallowedTools', 'Task', '--print', 'test']
    print(f"\nCommand format used: {' '.join(test_cmd[:6])}...")

if __name__ == "__main__":
    main()