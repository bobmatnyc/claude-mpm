"""Unified subprocess orchestrator supporting both interactive and non-interactive modes."""

import concurrent.futures
import json
import time
import subprocess
import pexpect
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
import re

try:
    from ..core.logger import get_project_logger
    from ..core.claude_launcher import ClaudeLauncher, LaunchMode
    from ..utils.subprocess_runner import SubprocessRunner
    from .base_orchestrator import BaseOrchestrator
    from .todo_hijacker import TodoHijacker
except ImportError:
    from core.logger import get_project_logger
    from core.claude_launcher import ClaudeLauncher, LaunchMode
    from utils.subprocess_runner import SubprocessRunner
    from orchestration.base_orchestrator import BaseOrchestrator
    from orchestration.todo_hijacker import TodoHijacker


class SessionMode(Enum):
    """Session modes for the orchestrator."""
    INTERACTIVE = "interactive"
    NON_INTERACTIVE = "non_interactive"
    INTERACTIVE_SUBPROCESS = "interactive_subprocess"  # With pexpect control


class SubprocessOrchestrator(BaseOrchestrator):
    """
    Unified orchestrator using ClaudeLauncher for subprocess management.
    
    Features:
    - Supports interactive and non-interactive modes
    - Agent delegation with real subprocesses
    - TODO hijacking capability
    - Hook service integration
    - Unified through ClaudeLauncher
    """
    
    def __init__(
        self,
        framework_path: Optional[Path] = None,
        agents_dir: Optional[Path] = None,
        log_level: str = "OFF",
        log_dir: Optional[Path] = None,
        hook_manager=None,
        enable_todo_hijacking: bool = False,
        session_mode: SessionMode = SessionMode.NON_INTERACTIVE,
    ):
        """
        Initialize the subprocess orchestrator.
        
        Args:
            framework_path: Path to framework directory
            agents_dir: Custom agents directory
            log_level: Logging level (OFF, INFO, DEBUG)
            log_dir: Custom log directory
            hook_manager: Hook service manager instance
            enable_todo_hijacking: Enable TODO hijacking
            session_mode: Session mode (interactive/non-interactive)
        """
        # Initialize base class
        super().__init__(framework_path, agents_dir, log_level, log_dir, hook_manager)
        
        # Session configuration
        self.session_mode = session_mode
        self.enable_todo_hijacking = enable_todo_hijacking
        
        # Initialize unified Claude launcher
        self.launcher = ClaudeLauncher(model="opus", skip_permissions=True, log_level=log_level)
        
        # Initialize TODO hijacker if enabled
        self.todo_hijacker = None
        if enable_todo_hijacking:
            self.todo_hijacker = TodoHijacker(
                log_level=log_level,
                on_delegation=self._handle_todo_delegation
            )
            self.logger.info("TODO hijacking enabled")
        
        # State for delegations
        self._pending_todo_delegations = []
        
        # Initialize subprocess runner for utility operations
        self.subprocess_runner = SubprocessRunner(logger=self.logger)
        
        # Initialize project logger
        self.project_logger = get_project_logger(log_level)
        self.project_logger.log_system(
            f"Initialized SubprocessOrchestrator (mode={session_mode.value})",
            level="INFO",
            component="orchestrator"
        )
        
        # Pexpect process for interactive subprocess mode
        self.pexpect_process = None
    
    def run_interactive(self):
        """Run an interactive session."""
        if self.session_mode == SessionMode.INTERACTIVE_SUBPROCESS:
            self._run_interactive_subprocess()
        else:
            self._run_standard_interactive()
    
    def _run_standard_interactive(self):
        """Run standard interactive session using Claude's print mode."""
        try:
            from claude_mpm._version import __version__
            print(f"Claude MPM v{__version__} - Interactive Session")
        except ImportError:
            print("Claude MPM Interactive Session")
        
        print("Type 'exit' or 'quit' to end session")
        print("-" * 50)
        
        conversation_file = None
        first_interaction = True
        
        while True:
            try:
                user_input = input("\nYou: ").strip()
                if user_input.lower() in ['exit', 'quit']:
                    break
                
                if user_input:
                    # Prepare message with framework on first interaction
                    if first_interaction:
                        framework = self.get_framework_instructions()
                        full_message = framework + "\n\nUser: " + user_input
                        first_interaction = False
                    else:
                        full_message = user_input
                    
                    # Log interaction
                    self.log_interaction("input", user_input)
                    
                    # Build command
                    cmd = [
                        "claude",
                        "--model", "opus",
                        "--dangerously-skip-permissions",
                        "--print",
                        full_message
                    ]
                    
                    # Continue conversation if we have a file
                    if conversation_file:
                        cmd.extend(["--continue", str(conversation_file)])
                    
                    # Run Claude
                    print("\nClaude: ", end='', flush=True)
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        response = result.stdout
                        print(response)
                        
                        # Log output
                        self.log_interaction("output", response)
                        
                        # Process output for tickets and delegations
                        self.process_output_line(response)
                        
                        # Extract conversation file from stderr
                        if "conversation saved to" in result.stderr.lower():
                            import re
                            match = re.search(r'conversation saved to[:\s]+(.+)', result.stderr, re.I)
                            if match:
                                conversation_file = Path(match.group(1).strip())
                    else:
                        print(f"Error: {result.stderr}")
                        
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"\nError: {e}")
                break
        
        print("\nSession ended")
        self.cleanup()
    
    def _run_interactive_subprocess(self):
        """Run interactive session with pexpect for subprocess control."""
        try:
            from claude_mpm._version import __version__
            print(f"Claude MPM v{__version__} - Interactive Subprocess Session")
        except ImportError:
            print("Claude MPM Interactive Subprocess Session")
        
        print("Starting Claude with subprocess control...")
        print("-" * 50)
        
        try:
            # Start Claude with pexpect
            cmd = "claude --model opus --dangerously-skip-permissions"
            self.pexpect_process = pexpect.spawn(cmd)
            self.pexpect_process.setecho(False)
            
            # Wait for Claude to be ready
            self.pexpect_process.expect(['Human:', pexpect.TIMEOUT], timeout=5)
            
            # Send framework on first interaction
            framework = self.get_framework_instructions()
            self.pexpect_process.sendline(framework)
            
            # Interactive loop
            while True:
                try:
                    # Get user input
                    user_input = input("\nYou: ").strip()
                    if user_input.lower() in ['exit', 'quit']:
                        break
                    
                    if user_input:
                        # Send to Claude
                        self.pexpect_process.sendline(user_input)
                        self.log_interaction("input", user_input)
                        
                        # Collect response
                        response_lines = []
                        while True:
                            i = self.pexpect_process.expect(['Human:', pexpect.TIMEOUT], timeout=1)
                            if i == 0:  # Found next prompt
                                break
                            before = self.pexpect_process.before
                            if before:
                                response_lines.append(before.decode('utf-8', errors='ignore'))
                        
                        response = ''.join(response_lines).strip()
                        if response:
                            print(f"\nClaude: {response}")
                            self.log_interaction("output", response)
                            
                            # Process for delegations
                            delegations = self.detect_delegations(response)
                            if delegations:
                                print(f"\nDetected {len(delegations)} delegation(s)")
                                self._process_delegations(delegations)
                        
                except pexpect.TIMEOUT:
                    print("\n[Timeout waiting for response]")
                except Exception as e:
                    print(f"\nError: {e}")
                    
        except Exception as e:
            print(f"Failed to start Claude: {e}")
        finally:
            if self.pexpect_process:
                self.pexpect_process.close()
            self.cleanup()
    
    def run_non_interactive(self, user_input: str):
        """Run non-interactive session with subprocess orchestration."""
        try:
            # Log session start
            self.project_logger.log_system(
                f"Starting non-interactive session",
                level="INFO",
                component="orchestrator"
            )
            
            # Start TODO monitoring if enabled
            if self.todo_hijacker:
                self.todo_hijacker.start_monitoring()
            
            # Create PM prompt with framework
            framework = self.get_framework_instructions()
            pm_prompt = f"{framework}\n\nUser Request: {user_input}"
            
            # Run PM subprocess
            print("Running Project Manager...")
            stdout, stderr, returncode = self.launcher.launch_oneshot(
                message=pm_prompt,
                use_stdin=True,
                timeout=120
            )
            
            if returncode == 0:
                pm_response = stdout.strip()
                print("\nProject Manager Response:")
                print("-" * 50)
                print(pm_response)
                print("-" * 50)
                
                # Log PM response
                self.log_interaction("pm_response", pm_response)
                
                # Process output for tickets
                self.process_output_line(pm_response)
                
                # Detect delegations
                delegations = self.detect_delegations(pm_response)
                
                # Process TODO-based delegations if any
                if self.todo_hijacker:
                    self.todo_hijacker.stop_monitoring()
                    todo_delegations = self._pending_todo_delegations
                    if todo_delegations:
                        print(f"\nDetected {len(todo_delegations)} TODO-based delegations")
                        delegations.extend(todo_delegations)
                
                # Process all delegations
                if delegations:
                    print(f"\nProcessing {len(delegations)} delegation(s)...")
                    self._process_delegations(delegations)
            else:
                print(f"PM Error: {stderr}")
                
        finally:
            if self.todo_hijacker:
                self.todo_hijacker.stop_monitoring()
            self.cleanup()
    
    def detect_delegations(self, response: str) -> List[Dict[str, str]]:
        """Detect delegation requests in response."""
        delegations = []
        
        # Pattern 1: **Agent Name**: task
        pattern1 = r'\*\*([^*]+)(?:\s+Agent)?\*\*:\s*(.+?)(?=\n\n|\n\*\*|$)'
        for match in re.finditer(pattern1, response, re.MULTILINE | re.DOTALL):
            agent = match.group(1).strip()
            task = match.group(2).strip()
            delegations.append({
                'agent': agent,
                'task': task,
                'format': 'markdown'
            })
        
        # Pattern 2: Task(description)
        pattern2 = r'Task\(([^)]+)\)'
        for match in re.finditer(pattern2, response):
            task_desc = match.group(1).strip()
            agent = self._extract_agent_from_task(task_desc)
            delegations.append({
                'agent': agent,
                'task': task_desc,
                'format': 'task_tool'
            })
        
        self.logger.info(f"Detected {len(delegations)} delegations")
        return delegations
    
    def _extract_agent_from_task(self, task: str) -> str:
        """Extract agent name from task description."""
        task_lower = task.lower()
        
        # Check for explicit agent names
        agents = ['engineer', 'qa', 'documentation', 'research',
                  'security', 'ops', 'version control', 'data engineer']
        
        for agent in agents:
            if agent in task_lower:
                return agent.title()
        
        # Use agent delegator to suggest
        suggested = self.agent_delegator.suggest_agent_for_task(task)
        return suggested or "Engineer"
    
    def _handle_todo_delegation(self, todo_item: Dict[str, Any]):
        """Handle TODO-based delegation from hijacker."""
        self.logger.info(f"TODO delegation: {todo_item.get('content', '')[:50]}...")
        
        # Extract agent from TODO content
        content = todo_item.get('content', '')
        agent = self._extract_agent_from_task(content)
        
        delegation = {
            'agent': agent,
            'task': content,
            'format': 'todo',
            'priority': todo_item.get('priority', 'medium')
        }
        
        self._pending_todo_delegations.append(delegation)
    
    def _process_delegations(self, delegations: List[Dict[str, str]]):
        """Process delegations by creating subprocesses."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            future_to_delegation = {
                executor.submit(self._run_agent_subprocess, d['agent'], d['task']): d
                for d in delegations
            }
            
            for future in concurrent.futures.as_completed(future_to_delegation):
                delegation = future_to_delegation[future]
                try:
                    response, exec_time, tokens = future.result()
                    print(f"\n{'='*60}")
                    print(f"{delegation['agent']} Agent Response:")
                    print(f"{'='*60}")
                    print(response)
                    print(f"{'='*60}")
                    print(f"Execution time: {exec_time:.2f}s, Tokens: ~{tokens}")
                    
                    # Log agent response
                    self.log_interaction(
                        f"{delegation['agent']}_response",
                        response
                    )
                except Exception as e:
                    print(f"\nError running {delegation['agent']} agent: {e}")
    
    def _run_agent_subprocess(self, agent: str, task: str) -> Tuple[str, float, int]:
        """Run a single agent subprocess."""
        start_time = time.time()
        
        # Pre-delegation hook
        if self.hook_client:
            try:
                hook_results = self.hook_client.execute_pre_delegation_hook(
                    prompt=task,
                    agent_type=agent.lower(),
                    context={"task": task}
                )
                # Check for modifications
                for result in hook_results:
                    if result.get('modified_prompt'):
                        task = result['modified_prompt']
                        break
            except Exception as e:
                self.logger.warning(f"Pre-delegation hook error: {e}")
        
        # Create agent prompt
        prompt = self._create_agent_prompt(agent, task)
        
        # Log the invocation
        self.project_logger.log_system(
            f"Invoking {agent} agent",
            level="INFO",
            component="orchestrator"
        )
        
        try:
            # Use launcher for one-shot execution
            stdout, stderr, returncode = self.launcher.launch_oneshot(
                message=prompt,
                use_stdin=True,
                timeout=60
            )
            
            execution_time = time.time() - start_time
            
            if returncode == 0:
                response = stdout.strip()
                total_tokens = len(prompt + response) // 4  # Rough estimate
                
                # Post-delegation hook
                if self.hook_client:
                    try:
                        hook_results = self.hook_client.execute_post_delegation_hook(
                            agent_type=agent.lower(),
                            result=response,
                            execution_time=execution_time,
                            context={"task": task, "tokens": total_tokens}
                        )
                    except Exception as e:
                        self.logger.warning(f"Post-delegation hook error: {e}")
                
                return response, execution_time, total_tokens
            else:
                error_msg = f"Agent failed with code {returncode}: {stderr}"
                self.logger.error(error_msg)
                return error_msg, execution_time, 0
                
        except Exception as e:
            error_msg = f"Exception running agent: {str(e)}"
            self.logger.error(error_msg)
            return error_msg, time.time() - start_time, 0
    
    def _create_agent_prompt(self, agent: str, task: str) -> str:
        """Create a prompt for an agent subprocess."""
        # Get agent-specific content
        agent_content = ""
        agent_key = agent.lower().replace(' ', '_') + '_agent'
        
        if agent_key in self.framework_loader.framework_content.get('agents', {}):
            agent_content = self.framework_loader.framework_content['agents'][agent_key]
        
        # Build agent prompt
        prompt = f"""You are the {agent} Agent in the Claude PM Framework.

{agent_content}

## Current Task
{task}

## Response Format
Provide a clear, structured response that:
1. Confirms your role as {agent} Agent
2. Completes the requested task
3. Reports any issues or blockers
4. Summarizes deliverables

Remember: You are an autonomous agent. Complete the task independently and report results."""
        
        return prompt