"""Subprocess orchestrator that mimics Claude's Task tool for non-interactive mode."""

import subprocess
import concurrent.futures
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import re

try:
    from ..utils.logger import get_logger, setup_logging
    from .ticket_extractor import TicketExtractor
    from ..core.framework_loader import FrameworkLoader
    from ..core.claude_launcher import ClaudeLauncher, LaunchMode
    from .agent_delegator import AgentDelegator
    from ..hooks.hook_client import HookServiceClient
    from .todo_hijacker import TodoHijacker
except ImportError:
    from utils.logger import get_logger, setup_logging
    from orchestration.ticket_extractor import TicketExtractor
    from core.framework_loader import FrameworkLoader
    from core.claude_launcher import ClaudeLauncher, LaunchMode
    from orchestration.agent_delegator import AgentDelegator
    from orchestration.todo_hijacker import TodoHijacker
    try:
        from hooks.hook_client import HookServiceClient
    except ImportError:
        HookServiceClient = None


class SubprocessOrchestrator:
    """
    Orchestrator that creates real subprocesses for agent delegations.
    Mimics Claude's built-in Task tool behavior for non-interactive mode.
    """
    
    def __init__(
        self,
        framework_path: Optional[Path] = None,
        agents_dir: Optional[Path] = None,
        log_level: str = "OFF",
        log_dir: Optional[Path] = None,
        hook_manager=None,
        enable_todo_hijacking: bool = False,
    ):
        """Initialize the subprocess orchestrator."""
        self.log_level = log_level
        self.log_dir = log_dir or (Path.home() / ".claude-mpm" / "logs")
        self.hook_manager = hook_manager
        
        # Initialize unified Claude launcher
        self.launcher = ClaudeLauncher(model="opus", skip_permissions=True, log_level=log_level)
        self.enable_todo_hijacking = enable_todo_hijacking
        
        # Set up logging
        if log_level != "OFF":
            self.logger = setup_logging(level=log_level, log_dir=log_dir)
            self.logger.info(f"Initializing Subprocess Orchestrator (log_level={log_level})")
            if hook_manager and hook_manager.is_available():
                self.logger.info(f"Hook service available on port {hook_manager.port}")
        else:
            self.logger = get_logger("subprocess_orchestrator")
            self.logger.setLevel(logging.WARNING)
        
        # Components
        self.framework_loader = FrameworkLoader(framework_path, agents_dir)
        self.ticket_extractor = TicketExtractor()
        self.agent_delegator = AgentDelegator(self.framework_loader.agent_registry)
        
        # Initialize TODO hijacker if enabled
        self.todo_hijacker = None
        if enable_todo_hijacking:
            self.todo_hijacker = TodoHijacker(
                log_level=log_level,
                on_delegation=self._handle_todo_delegation
            )
            self.logger.info("TODO hijacking enabled")
        
        # Initialize hook client if available
        self.hook_client = None
        if self.hook_manager and self.hook_manager.is_available() and HookServiceClient:
            try:
                hook_info = self.hook_manager.get_service_info()
                self.hook_client = HookServiceClient(base_url=hook_info['url'])
                # Test connection
                health = self.hook_client.health_check()
                if health.get('status') == 'healthy':
                    self.logger.info(f"Connected to hook service with {health.get('hooks_count', 0)} hooks")
                else:
                    self.logger.warning("Hook service not healthy, disabling hooks")
                    self.hook_client = None
            except Exception as e:
                self.logger.warning(f"Failed to initialize hook client: {e}")
                self.hook_client = None
        
        # State
        self.session_start = datetime.now()
        self.ticket_creation_enabled = True
        self._pending_todo_delegations = []
        
    def detect_delegations(self, response: str) -> List[Dict[str, str]]:
        """
        Detect delegation requests in PM response.
        
        Looks for patterns like:
        - **Engineer Agent**: Create a function...
        - Task(Engineer role summary)
        - Delegate to Engineer: implement...
        
        Returns:
            List of delegations with agent and task
        """
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
            # Try to extract agent from task description
            agent = self._extract_agent_from_task(task_desc)
            delegations.append({
                'agent': agent,
                'task': task_desc,
                'format': 'task_tool'
            })
        
        if self.log_level != "OFF":
            self.logger.info(f"Detected {len(delegations)} delegations")
            for d in delegations:
                self.logger.debug(f"  {d['agent']}: {d['task'][:50]}...")
        
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
        
        # Use agent delegator to suggest based on task
        suggested = self.agent_delegator.suggest_agent_for_task(task)
        return suggested or "Engineer"
    
    def create_agent_prompt(self, agent: str, task: str) -> str:
        """
        Create a prompt for an agent subprocess.
        
        Args:
            agent: Agent name
            task: Task description
            
        Returns:
            Complete prompt including agent-specific framework
        """
        # Get agent-specific content
        agent_content = ""
        agent_key = agent.lower().replace(' ', '_') + '_agent'
        
        if agent_key in self.framework_loader.framework_content.get('agents', {}):
            agent_content = self.framework_loader.framework_content['agents'][agent_key]
        
        # Build focused agent prompt
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
    
    def run_subprocess(self, agent: str, task: str) -> Tuple[str, float, int]:
        """
        Run a single agent subprocess.
        
        Args:
            agent: Agent name
            task: Task description
            
        Returns:
            Tuple of (response, execution_time, token_count)
        """
        start_time = time.time()
        
        # Pre-delegation hook
        if self.hook_client:
            try:
                self.logger.info(f"Calling pre-delegation hook for {agent}")
                hook_results = self.hook_client.execute_pre_delegation_hook(
                    agent=agent,
                    context={"task": task}
                )
                if hook_results:
                    self.logger.info(f"Pre-delegation hook executed: {len(hook_results)} hooks")
                    # Check for any modifications
                    modified = self.hook_client.get_modified_data(hook_results)
                    if modified and 'task' in modified:
                        task = modified['task']
                        self.logger.info(f"Task modified by hook: {task[:50]}...")
            except Exception as e:
                self.logger.warning(f"Pre-delegation hook error: {e}")
        
        # Create agent prompt
        prompt = self.create_agent_prompt(agent, task)
        
        # Log prompt size
        token_estimate = len(prompt) // 4  # Rough estimate
        if self.log_level != "OFF":
            self.logger.info(f"Running subprocess for {agent} ({token_estimate} est. tokens)")
        
        try:
            # Use unified launcher for one-shot execution
            stdout, stderr, returncode = self.launcher.launch_oneshot(
                message=prompt,
                use_stdin=True,
                timeout=60
            )
            
            execution_time = time.time() - start_time
            
            if returncode == 0:
                response = stdout.strip()
                # Estimate response tokens
                total_tokens = len(prompt + response) // 4
                
                # Post-delegation hook
                if self.hook_client:
                    try:
                        self.logger.info(f"Calling post-delegation hook for {agent}")
                        hook_results = self.hook_client.execute_post_delegation_hook(
                            agent=agent,
                            result={
                                "task": task,
                                "response": response,
                                "execution_time": execution_time,
                                "tokens": total_tokens
                            }
                        )
                        if hook_results:
                            self.logger.info(f"Post-delegation hook executed: {len(hook_results)} hooks")
                            # Extract any tickets from hooks
                            hook_tickets = self.hook_client.get_extracted_tickets(hook_results)
                            if hook_tickets:
                                self.logger.info(f"Extracted {len(hook_tickets)} tickets from hooks")
                                for ticket in hook_tickets:
                                    self.ticket_extractor.add_ticket(ticket)
                    except Exception as e:
                        self.logger.warning(f"Post-delegation hook error: {e}")
                
                return response, execution_time, total_tokens
            else:
                error_msg = f"Subprocess failed: {stderr}"
                if self.log_level != "OFF":
                    self.logger.error(f"{agent} subprocess error: {error_msg}")
                return error_msg, execution_time, token_estimate
                
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            error_msg = f"Subprocess timed out after {execution_time:.1f}s"
            if self.log_level != "OFF":
                self.logger.error(f"{agent} {error_msg}")
            return error_msg, execution_time, token_estimate
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Subprocess error: {str(e)}"
            if self.log_level != "OFF":
                self.logger.error(f"{agent} {error_msg}")
            return error_msg, execution_time, token_estimate
    
    def _handle_todo_delegation(self, delegation: Dict[str, Any]):
        """
        Handle a delegation created from a TODO.
        
        Args:
            delegation: Delegation dict from TodoHijacker
        """
        self.logger.info(f"TODO delegation received: {delegation['agent']} - {delegation['task'][:50]}...")
        self._pending_todo_delegations.append(delegation)
    
    def _process_pending_todo_delegations(self) -> List[Dict[str, Any]]:
        """
        Process any pending TODO delegations.
        
        Returns:
            List of results from running the delegations
        """
        if not self._pending_todo_delegations:
            return []
        
        self.logger.info(f"Processing {len(self._pending_todo_delegations)} TODO delegations")
        
        # Run the delegations
        results = self.run_parallel_tasks(self._pending_todo_delegations)
        
        # Clear pending list
        self._pending_todo_delegations.clear()
        
        return results
    
    def run_parallel_tasks(self, delegations: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Run multiple agent tasks in parallel.
        
        Args:
            delegations: List of delegation dicts with 'agent' and 'task'
            
        Returns:
            List of results with agent, response, timing, and tokens
        """
        results = []
        
        # Use ThreadPoolExecutor for parallel execution
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            # Submit all tasks
            future_to_delegation = {}
            for delegation in delegations:
                future = executor.submit(
                    self.run_subprocess,
                    delegation['agent'],
                    delegation['task']
                )
                future_to_delegation[future] = delegation
            
            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_delegation):
                delegation = future_to_delegation[future]
                try:
                    response, exec_time, tokens = future.result()
                    results.append({
                        'agent': delegation['agent'],
                        'task': delegation['task'],
                        'response': response,
                        'execution_time': exec_time,
                        'tokens': tokens,
                        'status': 'completed'
                    })
                except Exception as e:
                    results.append({
                        'agent': delegation['agent'],
                        'task': delegation['task'],
                        'response': str(e),
                        'execution_time': 0,
                        'tokens': 0,
                        'status': 'failed'
                    })
        
        return results
    
    def format_results(self, results: List[Dict[str, Any]]) -> str:
        """
        Format subprocess results in Claude Task tool style.
        
        Args:
            results: List of result dicts
            
        Returns:
            Formatted output mimicking Claude's Task tool
        """
        output = []
        
        # Show task executions
        for result in results:
            status_icon = "⏺" if result['status'] == 'completed' else "❌"
            tokens_k = result['tokens'] / 1000
            
            output.append(f"{status_icon} Task({result['task'][:50]}...)")
            output.append(f"  ⎿  Done (0 tool uses · {tokens_k:.1f}k tokens · {result['execution_time']:.1f}s)")
            output.append("")
        
        # Aggregate responses
        output.append("## Agent Responses\n")
        
        for result in results:
            output.append(f"### {result['agent']} Agent")
            output.append(result['response'])
            output.append("")
        
        return "\n".join(output)
    
    def run_non_interactive(self, user_input: str):
        """
        Run non-interactive session with subprocess orchestration.
        
        This method:
        1. Runs PM with user input
        2. Detects delegations in PM response
        3. Creates subprocesses for each delegation
        4. Aggregates and displays results
        5. Processes any TODO-based delegations if hijacking is enabled
        """
        try:
            # Start TODO monitoring if enabled
            if self.todo_hijacker:
                self.todo_hijacker.start_monitoring()
            # Submit hook for user input
            if self.hook_client:
                try:
                    self.logger.info("Calling submit hook for user input")
                    hook_results = self.hook_client.execute_submit_hook(
                        prompt=user_input,
                        session_type="subprocess"
                    )
                    if hook_results:
                        self.logger.info(f"Submit hook executed: {len(hook_results)} hooks")
                except Exception as e:
                    self.logger.warning(f"Submit hook error: {e}")
            # Prepare PM prompt with minimal framework
            try:
                from ..core.minimal_framework_loader import MinimalFrameworkLoader
            except ImportError:
                from core.minimal_framework_loader import MinimalFrameworkLoader
            
            minimal_loader = MinimalFrameworkLoader(self.framework_loader.framework_path)
            framework = minimal_loader.get_framework_instructions()
            
            # Add instruction to use delegation format
            framework += """
## Delegation Format
When delegating tasks, use this exact format:
**[Agent Name]**: [Task description]

Example:
**Engineer**: Create a function that calculates factorial
**QA**: Write tests for the factorial function
"""
            
            full_message = framework + "\n\nUser: " + user_input
            
            if self.log_level != "OFF":
                self.logger.info("Running PM with user input")
            
            # Use unified launcher for PM execution
            stdout, stderr, returncode = self.launcher.launch_oneshot(
                message=full_message,
                use_stdin=True,
                timeout=30
            )
            
            if returncode != 0:
                print(f"Error: {stderr}")
                return
            
            pm_response = stdout
            print("PM Response:")
            print("-" * 50)
            print(pm_response)
            print("-" * 50)
            
            # Detect delegations
            delegations = self.detect_delegations(pm_response)
            
            if delegations:
                print(f"\nDetected {len(delegations)} delegations. Running subprocesses...\n")
                
                # Run delegations in parallel
                results = self.run_parallel_tasks(delegations)
                
                # Format and display results
                formatted_results = self.format_results(results)
                print(formatted_results)
                
                # Extract tickets from all responses
                all_responses = pm_response + "\n".join([r['response'] for r in results])
                for line in all_responses.split('\n'):
                    tickets = self.ticket_extractor.extract_from_line(line)
                    for ticket in tickets:
                        if self.log_level != "OFF":
                            self.logger.info(f"Extracted ticket: {ticket['type']} - {ticket['title']}")
            else:
                print("\nNo delegations detected in PM response.")
            
            # Process any TODO-based delegations
            if self.todo_hijacker:
                # Give a moment for TODO files to be written
                time.sleep(0.5)
                
                # Process pending TODO delegations
                todo_results = self._process_pending_todo_delegations()
                if todo_results:
                    print(f"\nProcessed {len(todo_results)} TODO-based delegations:")
                    formatted_todo_results = self.format_results(todo_results)
                    print(formatted_todo_results)
                
            # Create tickets
            self._create_tickets()
                
        except Exception as e:
            print(f"Error: {e}")
            if self.log_level != "OFF":
                self.logger.error(f"Non-interactive error: {e}")
        finally:
            # Stop TODO monitoring
            if self.todo_hijacker:
                self.todo_hijacker.stop_monitoring()
    
    def run_interactive(self):
        """Run an interactive session with subprocess orchestration."""
        try:
            from .._version import __version__
        except ImportError:
            from claude_mpm._version import __version__
            
        print(f"Claude MPM v{__version__} - Interactive Session (Subprocess Mode)")
        print("Starting Claude with subprocess orchestration...")
        print("-" * 50)
        
        # Get framework instructions
        framework = self.framework_loader.get_framework_instructions()
        
        # Submit hook for framework initialization if available
        if self.hook_client:
            hook_response = self.hook_client.execute_submit_hook(
                "Starting interactive subprocess session",
                hook_type='framework_init',
                framework=framework,
                session_mode='interactive_subprocess'
            )
            if hook_response and 'framework' in hook_response:
                framework = hook_response['framework']
        
        # Run Claude in interactive mode
        if self.log_level != "OFF":
            self.logger.info("Starting interactive Claude session with subprocess orchestration")
            self.logger.info("Note: In interactive mode, the subprocess orchestrator monitors for delegations")
        
        # For now, we'll just run Claude normally and explain the limitation
        print("\nNote: The subprocess orchestrator in interactive mode currently runs Claude")
        print("without the framework as system prompt. Delegation detection will be added soon.")
        print("For full subprocess control, use: claude-mpm --subprocess -i 'your prompt'")
        print("-" * 50)
        
        try:
            # Use unified launcher for interactive mode
            process = self.launcher.launch_interactive()
            # Wait for process to complete
            process.wait()
            
            # After session ends, extract and create tickets
            # Note: In interactive mode, we can't capture output directly
            # so ticket extraction would need to be handled differently
            
        except KeyboardInterrupt:
            print("\nSession interrupted by user")
            if self.log_level != "OFF":
                self.logger.info("Interactive session interrupted")
        except Exception as e:
            print(f"Error running Claude: {e}")
            if self.log_level != "OFF":
                self.logger.error(f"Interactive error: {e}")
    
    def _create_tickets(self):
        """Create tickets using ai-trackdown-pytools."""
        if not self.ticket_creation_enabled:
            self.logger.info("Ticket creation disabled")
            return
            
        tickets = self.ticket_extractor.get_all_tickets()
        if not tickets:
            self.logger.info("No tickets to create")
            return
        
        try:
            try:
                from ..services.ticket_manager import TicketManager
            except ImportError:
                from services.ticket_manager import TicketManager
            ticket_manager = TicketManager()
            
            created_count = 0
            for ticket in tickets:
                try:
                    ticket_id = ticket_manager.create_ticket(
                        title=ticket['title'],
                        ticket_type=ticket['type'],
                        description=ticket.get('description', ''),
                        source='claude-mpm'
                    )
                    created_count += 1
                    if self.log_level != "OFF":
                        self.logger.info(f"Created ticket: {ticket_id} - {ticket['title']}")
                except Exception as e:
                    self.logger.error(f"Failed to create ticket '{ticket['title']}': {e}")
            
            if self.log_level != "OFF":
                self.logger.info(f"Created {created_count}/{len(tickets)} tickets")
                
        except ImportError:
            self.logger.warning("TicketManager not available, skipping ticket creation")
        except Exception as e:
            self.logger.error(f"Error creating tickets: {e}")