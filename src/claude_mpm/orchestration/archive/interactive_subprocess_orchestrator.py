"""
Interactive Subprocess Orchestrator using pexpect for Claude CLI control.

This orchestrator creates controlled subprocesses for agent delegations,
monitoring their execution and resource usage while maintaining interactive
control through pexpect.
"""

import os
import pexpect
import subprocess
import concurrent.futures
import json
import time
import logging
import psutil
import threading
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import re

try:
    from ..core.logger import get_logger, setup_logging
    # TicketExtractor removed from project
    from ..core.framework_loader import FrameworkLoader
    from .agent_delegator import AgentDelegator
except ImportError:
    from core.logger import get_logger, setup_logging
    # TicketExtractor removed from project
    from core.framework_loader import FrameworkLoader
    from orchestration.agent_delegator import AgentDelegator


# ==============================================================================
# Data Structures
# ==============================================================================

@dataclass
class AgentExecutionResult:
    """Result of an agent subprocess execution."""
    success: bool
    agent_type: str
    task_description: str
    stdout: str
    stderr: str
    exit_code: int
    execution_time: float
    memory_usage: Dict[str, int]
    tickets_created: List[str]
    error: Optional[str] = None
    process_id: Optional[str] = None


class ProcessStatus(Enum):
    """Status of a subprocess execution."""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    MEMORY_EXCEEDED = "memory_exceeded"


# ==============================================================================
# Memory Monitor
# ==============================================================================

class MemoryMonitor:
    """Monitor memory usage of subprocesses."""
    
    def __init__(self, warning_threshold_mb: int = 512, 
                 critical_threshold_mb: int = 1024, 
                 hard_limit_mb: int = 2048):
        """
        Initialize memory monitor.
        
        Args:
            warning_threshold_mb: Memory usage warning threshold in MB
            critical_threshold_mb: Critical memory usage threshold in MB
            hard_limit_mb: Hard limit that triggers process termination in MB
        """
        self.warning_threshold = warning_threshold_mb * 1024 * 1024
        self.critical_threshold = critical_threshold_mb * 1024 * 1024
        self.hard_limit = hard_limit_mb * 1024 * 1024
        self.monitoring = False
        self.logger = get_logger("memory_monitor")
        
    def start_monitoring(self, process_pid: int) -> threading.Thread:
        """Start memory monitoring in separate thread."""
        self.monitoring = True
        
        def monitor():
            try:
                ps_process = psutil.Process(process_pid)
                while self.monitoring:
                    try:
                        memory_info = ps_process.memory_info()
                        rss = memory_info.rss
                        
                        if rss > self.hard_limit:
                            self.logger.critical(
                                f"Process {process_pid} exceeded hard limit "
                                f"({rss/1024/1024:.1f}MB > {self.hard_limit/1024/1024:.1f}MB)"
                            )
                            ps_process.terminate()
                            break
                        elif rss > self.critical_threshold:
                            self.logger.warning(
                                f"Process {process_pid} critical memory usage: "
                                f"{rss/1024/1024:.1f}MB"
                            )
                        elif rss > self.warning_threshold:
                            self.logger.info(
                                f"Process {process_pid} high memory usage: "
                                f"{rss/1024/1024:.1f}MB"
                            )
                        
                        time.sleep(2)  # Check every 2 seconds
                    except psutil.NoSuchProcess:
                        break
            except Exception as e:
                self.logger.error(f"Memory monitoring error: {e}")
                
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        return thread
        
    def stop_monitoring(self):
        """Stop memory monitoring."""
        self.monitoring = False
        
    def get_memory_usage(self, process_pid: int) -> Dict[str, int]:
        """Get current memory usage statistics."""
        try:
            ps_process = psutil.Process(process_pid)
            memory_info = ps_process.memory_info()
            return {
                "rss_mb": memory_info.rss // (1024 * 1024),
                "vms_mb": memory_info.vms // (1024 * 1024),
                "percent": ps_process.memory_percent()
            }
        except psutil.NoSuchProcess:
            return {"rss_mb": 0, "vms_mb": 0, "percent": 0.0}


# ==============================================================================
# Process Manager
# ==============================================================================

class ProcessManager:
    """Manage subprocess lifecycles and resource usage."""
    
    def __init__(self):
        """Initialize process manager."""
        self.active_processes: Dict[str, pexpect.spawn] = {}
        self.memory_monitors: Dict[str, MemoryMonitor] = {}
        self.process_metadata: Dict[str, Dict[str, Any]] = {}
        self.logger = get_logger("process_manager")
        
    def create_interactive_process(self, command: List[str], env: Dict[str, str], 
                                 memory_limit_mb: int = 1024, 
                                 timeout: int = 300) -> Tuple[str, pexpect.spawn]:
        """
        Create and return managed interactive subprocess using pexpect.
        
        Args:
            command: Command and arguments to execute
            env: Environment variables
            memory_limit_mb: Memory limit in MB
            timeout: Timeout in seconds
            
        Returns:
            Tuple of (process_id, pexpect.spawn instance)
        """
        process_id = str(uuid.uuid4())
        
        try:
            # Create pexpect spawn instance
            process = pexpect.spawn(
                command[0],
                command[1:],
                encoding='utf-8',
                timeout=timeout,
                env=env,
                dimensions=(24, 80)
            )
            
            # Start memory monitoring
            memory_monitor = MemoryMonitor(
                warning_threshold_mb=memory_limit_mb // 2,
                critical_threshold_mb=int(memory_limit_mb * 0.8),
                hard_limit_mb=memory_limit_mb
            )
            
            self.active_processes[process_id] = process
            self.memory_monitors[process_id] = memory_monitor
            self.process_metadata[process_id] = {
                "command": command,
                "start_time": datetime.now(),
                "memory_limit_mb": memory_limit_mb,
                "timeout": timeout
            }
            
            # Start monitoring after process is registered
            memory_monitor.start_monitoring(process.pid)
            
            self.logger.info(f"Created interactive process {process_id} (PID: {process.pid})")
            return process_id, process
            
        except Exception as e:
            self.logger.error(f"Failed to create process: {e}")
            raise RuntimeError(f"Failed to create process: {e}")
    
    def send_to_process(self, process_id: str, input_data: str) -> bool:
        """
        Send input to an interactive process.
        
        Args:
            process_id: Process identifier
            input_data: Data to send
            
        Returns:
            True if successful, False otherwise
        """
        if process_id not in self.active_processes:
            self.logger.error(f"Process {process_id} not found")
            return False
            
        try:
            process = self.active_processes[process_id]
            process.sendline(input_data)
            return True
        except Exception as e:
            self.logger.error(f"Failed to send to process {process_id}: {e}")
            return False
    
    def read_from_process(self, process_id: str, pattern: str = None, 
                         timeout: int = 30) -> Optional[str]:
        """
        Read output from an interactive process.
        
        Args:
            process_id: Process identifier
            pattern: Pattern to expect (default: Claude's '>' prompt)
            timeout: Read timeout in seconds
            
        Returns:
            Output string or None if failed
        """
        if process_id not in self.active_processes:
            self.logger.error(f"Process {process_id} not found")
            return None
            
        try:
            process = self.active_processes[process_id]
            
            if pattern:
                process.expect(pattern, timeout=timeout)
            else:
                # Default to Claude's prompt
                process.expect('>', timeout=timeout)
                
            return process.before
        except pexpect.TIMEOUT:
            self.logger.warning(f"Timeout reading from process {process_id}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to read from process {process_id}: {e}")
            return None
    
    def terminate_process(self, process_id: str) -> Dict[str, Any]:
        """
        Terminate a process and return its final statistics.
        
        Args:
            process_id: Process identifier
            
        Returns:
            Dictionary with process statistics
        """
        if process_id not in self.active_processes:
            return {"error": f"Process {process_id} not found"}
            
        process = self.active_processes[process_id]
        memory_monitor = self.memory_monitors.get(process_id)
        metadata = self.process_metadata.get(process_id, {})
        
        # Get final memory usage
        memory_usage = {"rss_mb": 0, "vms_mb": 0, "percent": 0.0}
        if memory_monitor and process.pid:
            memory_usage = memory_monitor.get_memory_usage(process.pid)
            memory_monitor.stop_monitoring()
        
        # Calculate execution time
        start_time = metadata.get("start_time", datetime.now())
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Terminate process
        try:
            process.close()
            exit_code = process.exitstatus or -1
        except Exception as e:
            self.logger.error(f"Error terminating process {process_id}: {e}")
            exit_code = -1
        
        # Clean up
        if process_id in self.active_processes:
            del self.active_processes[process_id]
        if process_id in self.memory_monitors:
            del self.memory_monitors[process_id]
        if process_id in self.process_metadata:
            del self.process_metadata[process_id]
        
        return {
            "process_id": process_id,
            "exit_code": exit_code,
            "execution_time": execution_time,
            "memory_usage": memory_usage
        }
    
    def get_active_processes(self) -> List[Dict[str, Any]]:
        """Get list of active processes with their metadata."""
        active = []
        for process_id, process in self.active_processes.items():
            metadata = self.process_metadata.get(process_id, {})
            memory_usage = {"rss_mb": 0, "vms_mb": 0, "percent": 0.0}
            
            if process.pid:
                monitor = self.memory_monitors.get(process_id)
                if monitor:
                    memory_usage = monitor.get_memory_usage(process.pid)
            
            active.append({
                "process_id": process_id,
                "pid": process.pid,
                "command": metadata.get("command", []),
                "start_time": metadata.get("start_time", "").isoformat() if metadata.get("start_time") else "",
                "memory_usage": memory_usage,
                "memory_limit_mb": metadata.get("memory_limit_mb", 0)
            })
            
        return active


# ==============================================================================
# Interactive Subprocess Orchestrator
# ==============================================================================

class InteractiveSubprocessOrchestrator:
    """
    Orchestrator that creates controlled subprocesses for agent delegations
    using pexpect for interactive control.
    """
    
    def __init__(
        self,
        framework_path: Optional[Path] = None,
        agents_dir: Optional[Path] = None,
        log_level: str = "INFO",
        log_dir: Optional[Path] = None,
        hook_manager=None,
    ):
        """
        Initialize the interactive subprocess orchestrator.
        
        Args:
            framework_path: Path to framework directory
            agents_dir: Path to agents directory
            log_level: Logging level
            log_dir: Directory for log files
            hook_manager: Hook service manager instance
        """
        self.log_level = log_level
        self.log_dir = log_dir or (Path.home() / ".claude-mpm" / "logs")
        self.hook_manager = hook_manager
        
        # Set up logging
        self.logger = setup_logging(level=log_level, log_dir=log_dir)
        self.logger.info(f"Initializing Interactive Subprocess Orchestrator (log_level={log_level})")
        if hook_manager and hook_manager.is_available():
            self.logger.info(f"Hook service available on port {hook_manager.port}")
        
        # Components
        self.framework_loader = FrameworkLoader(framework_path, agents_dir)
        # TicketExtractor removed from project
        self.agent_delegator = AgentDelegator(self.framework_loader.agent_registry)
        self.process_manager = ProcessManager()
        
        # State
        self.session_start = datetime.now()
        # Ticket creation removed from project
        self.parallel_execution_enabled = True
        self.max_parallel_processes = 8
        
    def detect_delegations(self, response: str) -> List[Dict[str, str]]:
        """
        Detect delegation requests in PM response.
        
        Looks for patterns like:
        - **Engineer Agent**: Create a function...
        - **QA**: Write tests...
        - Task Tool → Documentation Agent: Generate changelog
        
        Args:
            response: PM response text
            
        Returns:
            List of delegations with agent and task
        """
        delegations = []
        
        # Pattern 1: **Agent Name**: task
        pattern1 = r'\*\*([^*]+?)(?:\s+Agent)?\*\*:\s*(.+?)(?=\n\n|\n\*\*|$)'
        for match in re.finditer(pattern1, response, re.MULTILINE | re.DOTALL):
            agent = match.group(1).strip()
            task = match.group(2).strip()
            delegations.append({
                'agent': agent,
                'task': task,
                'format': 'markdown'
            })
        
        # Pattern 2: Task Tool → Agent: task
        pattern2 = r'Task Tool\s*→\s*([^:]+):\s*(.+?)(?=\n\n|\nTask Tool|$)'
        for match in re.finditer(pattern2, response, re.MULTILINE | re.DOTALL):
            agent = match.group(1).strip().replace(' Agent', '')
            task = match.group(2).strip()
            delegations.append({
                'agent': agent,
                'task': task,
                'format': 'task_tool'
            })
        
        self.logger.info(f"Detected {len(delegations)} delegations")
        for d in delegations:
            self.logger.debug(f"  {d['agent']}: {d['task'][:50]}...")
        
        return delegations
    
    def create_agent_prompt(self, agent: str, task: str, context: Dict[str, Any] = None) -> str:
        """
        Create a prompt for an agent subprocess.
        
        Args:
            agent: Agent name
            task: Task description
            context: Additional context for the agent
            
        Returns:
            Complete prompt including agent-specific framework
        """
        # Get agent-specific content
        agent_content = ""
        agent_key = agent.lower().replace(' ', '_') + '_agent'
        
        if agent_key in self.framework_loader.framework_content.get('agents', {}):
            agent_content = self.framework_loader.framework_content['agents'][agent_key]
        
        # Add temporal context
        temporal_context = f"Today is {datetime.now().strftime('%Y-%m-%d')}."
        
        # Build focused agent prompt
        prompt = f"""You are the {agent} Agent in the Claude PM Framework.

{agent_content}

TEMPORAL CONTEXT: {temporal_context}

## Current Task
{task}

## Context
{json.dumps(context, indent=2) if context else 'No additional context provided.'}

## Response Format
Provide a clear, structured response that:
1. Confirms your role as {agent} Agent
2. Completes the requested task
3. Reports any issues or blockers
4. Summarizes deliverables

Remember: You are an autonomous agent. Complete the task independently and report results."""
        
        return prompt
    
    def run_agent_subprocess(self, agent: str, task: str, 
                           context: Dict[str, Any] = None,
                           timeout: int = 300,
                           memory_limit_mb: int = 1024) -> AgentExecutionResult:
        """
        Run a single agent subprocess with interactive control.
        
        Args:
            agent: Agent name
            task: Task description
            context: Additional context
            timeout: Execution timeout in seconds
            memory_limit_mb: Memory limit in MB
            
        Returns:
            AgentExecutionResult with execution details
        """
        start_time = time.time()
        
        # Create agent prompt
        prompt = self.create_agent_prompt(agent, task, context)
        
        # Prepare environment
        env = os.environ.copy()
        env.update({
            'CLAUDE_PM_ORCHESTRATED': 'true',
            'CLAUDE_PM_AGENT': agent,
            'CLAUDE_PM_SESSION_ID': str(uuid.uuid4()),
            'CLAUDE_PM_FRAMEWORK_VERSION': '1.4.0'
        })
        
        try:
            # Create interactive subprocess
            command = ["claude", "--model", "opus", "--dangerously-skip-permissions"]
            process_id, process = self.process_manager.create_interactive_process(
                command, env, memory_limit_mb, timeout
            )
            
            self.logger.info(f"Started subprocess {process_id} for {agent}")
            
            # Wait for initial prompt
            initial_output = self.process_manager.read_from_process(process_id, '>', timeout=10)
            if initial_output is None:
                raise RuntimeError("Failed to get initial prompt from Claude")
            
            # Send agent prompt
            if not self.process_manager.send_to_process(process_id, prompt):
                raise RuntimeError("Failed to send prompt to subprocess")
            
            # Read response
            response = self.process_manager.read_from_process(process_id, '>', timeout=timeout)
            if response is None:
                raise RuntimeError("Failed to read response from subprocess")
            
            # Get process statistics
            stats = self.process_manager.terminate_process(process_id)
            
            execution_time = time.time() - start_time
            
            # Ticket extraction removed from project
            ticket_ids = []
            
            return AgentExecutionResult(
                success=True,
                agent_type=agent,
                task_description=task,
                stdout=response,
                stderr="",
                exit_code=stats.get("exit_code", 0),
                execution_time=execution_time,
                memory_usage=stats.get("memory_usage", {}),
                tickets_created=ticket_ids,
                process_id=process_id
            )
            
        except Exception as e:
            self.logger.error(f"Subprocess execution failed for {agent}: {e}")
            
            # Clean up if process exists
            if 'process_id' in locals():
                stats = self.process_manager.terminate_process(process_id)
            
            execution_time = time.time() - start_time
            
            return AgentExecutionResult(
                success=False,
                agent_type=agent,
                task_description=task,
                stdout="",
                stderr=str(e),
                exit_code=-1,
                execution_time=execution_time,
                memory_usage={},
                tickets_created=[],
                error=str(e)
            )
    
    def run_parallel_delegations(self, delegations: List[Dict[str, str]]) -> List[AgentExecutionResult]:
        """
        Run multiple agent delegations in parallel.
        
        Args:
            delegations: List of delegation dicts with 'agent' and 'task'
            
        Returns:
            List of AgentExecutionResult objects
        """
        results = []
        
        if not self.parallel_execution_enabled:
            # Run sequentially
            for delegation in delegations:
                result = self.run_agent_subprocess(
                    delegation['agent'],
                    delegation['task']
                )
                results.append(result)
        else:
            # Run in parallel with ThreadPoolExecutor
            with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_parallel_processes) as executor:
                # Submit all tasks
                future_to_delegation = {}
                for delegation in delegations:
                    future = executor.submit(
                        self.run_agent_subprocess,
                        delegation['agent'],
                        delegation['task']
                    )
                    future_to_delegation[future] = delegation
                
                # Collect results as they complete
                for future in concurrent.futures.as_completed(future_to_delegation):
                    delegation = future_to_delegation[future]
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        # Create error result
                        results.append(AgentExecutionResult(
                            success=False,
                            agent_type=delegation['agent'],
                            task_description=delegation['task'],
                            stdout="",
                            stderr=str(e),
                            exit_code=-1,
                            execution_time=0,
                            memory_usage={},
                            tickets_created=[],
                            error=str(e)
                        ))
        
        return results
    
    def format_execution_results(self, results: List[AgentExecutionResult]) -> str:
        """
        Format execution results in a readable format.
        
        Args:
            results: List of AgentExecutionResult objects
            
        Returns:
            Formatted string output
        """
        output = []
        
        # Summary
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        total_time = sum(r.execution_time for r in results)
        
        output.append("## Subprocess Execution Summary")
        output.append(f"- Total delegations: {len(results)}")
        output.append(f"- Successful: {successful}")
        output.append(f"- Failed: {failed}")
        output.append(f"- Total execution time: {total_time:.1f}s")
        output.append("")
        
        # Process list
        output.append("## Execution Details")
        for i, result in enumerate(results, 1):
            status = "✓" if result.success else "✗"
            mem_usage = result.memory_usage.get("rss_mb", 0)
            
            output.append(f"{i}. [{status}] {result.agent_type}: {result.task_description[:50]}...")
            output.append(f"   - Execution time: {result.execution_time:.1f}s")
            output.append(f"   - Memory usage: {mem_usage}MB")
            output.append(f"   - Exit code: {result.exit_code}")
            if result.tickets_created:
                output.append(f"   - Tickets created: {len(result.tickets_created)}")
            if result.error:
                output.append(f"   - Error: {result.error}")
            output.append("")
        
        # Detailed responses
        output.append("## Agent Responses")
        for result in results:
            output.append(f"\n### {result.agent_type} Agent")
            output.append("-" * 50)
            if result.success:
                output.append(result.stdout)
            else:
                output.append(f"ERROR: {result.error}")
                if result.stderr:
                    output.append(f"STDERR: {result.stderr}")
            output.append("")
        
        return "\n".join(output)
    
    def run_orchestrated_session(self, initial_prompt: str):
        """
        Run an orchestrated session with subprocess delegation.
        
        Args:
            initial_prompt: Initial user prompt to send to PM
        """
        self.logger.info("Starting orchestrated session")
        
        try:
            # Create PM subprocess
            env = os.environ.copy()
            command = ["claude", "--model", "opus", "--dangerously-skip-permissions"]
            
            process_id, pm_process = self.process_manager.create_interactive_process(
                command, env, memory_limit_mb=2048, timeout=600
            )
            
            self.logger.info(f"Started PM subprocess {process_id}")
            
            # Wait for initial prompt
            initial_output = self.process_manager.read_from_process(process_id, '>', timeout=10)
            if initial_output is None:
                raise RuntimeError("Failed to get initial prompt from PM")
            
            # Send framework instructions
            framework = self.framework_loader.get_framework_instructions()
            if not self.process_manager.send_to_process(process_id, framework):
                raise RuntimeError("Failed to send framework to PM")
            
            # Read framework acknowledgment
            framework_response = self.process_manager.read_from_process(process_id, '>', timeout=60)
            if framework_response is None:
                raise RuntimeError("Failed to get framework acknowledgment")
            
            # Send user prompt
            if not self.process_manager.send_to_process(process_id, initial_prompt):
                raise RuntimeError("Failed to send user prompt to PM")
            
            # Read PM response
            pm_response = self.process_manager.read_from_process(process_id, '>', timeout=120)
            if pm_response is None:
                raise RuntimeError("Failed to get PM response")
            
            print("\n=== PM Response ===")
            print(pm_response)
            print("==================\n")
            
            # Detect delegations
            delegations = self.detect_delegations(pm_response)
            
            if delegations:
                print(f"\nDetected {len(delegations)} delegations. Running subprocesses...\n")
                
                # Run delegations
                results = self.run_parallel_delegations(delegations)
                
                # Format and display results
                formatted_results = self.format_execution_results(results)
                print(formatted_results)
                
                # Store tickets
                all_tickets = []
                for result in results:
                    if result.tickets_created:
                        for ticket_id in result.tickets_created:
                            all_tickets.append({
                                'id': ticket_id,
                                'agent': result.agent_type,
                                'created_at': datetime.now().isoformat()
                            })
                
                if all_tickets:
                    print(f"\nTotal tickets created: {len(all_tickets)}")
            else:
                print("\nNo delegations detected in PM response.")
            
            # Terminate PM process
            self.process_manager.terminate_process(process_id)
            
        except Exception as e:
            self.logger.error(f"Orchestrated session error: {e}")
            print(f"\nError during orchestrated session: {e}")
            
            # Clean up any active processes
            for process_info in self.process_manager.get_active_processes():
                self.process_manager.terminate_process(process_info['process_id'])
    
    def get_status(self) -> Dict[str, Any]:
        """Get current orchestrator status."""
        return {
            "session_start": self.session_start.isoformat(),
            "active_processes": self.process_manager.get_active_processes(),
            "parallel_execution_enabled": self.parallel_execution_enabled,
            "max_parallel_processes": self.max_parallel_processes,
            # Ticket extraction removed from project
        }


# ==============================================================================
# CLI Integration
# ==============================================================================

def main():
    """Main entry point for testing."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Interactive Subprocess Orchestrator")
    parser.add_argument("prompt", help="Initial prompt to send to PM")
    parser.add_argument("--log-level", default="INFO", help="Logging level")
    parser.add_argument("--no-parallel", action="store_true", help="Disable parallel execution")
    
    args = parser.parse_args()
    
    # Create orchestrator
    orchestrator = InteractiveSubprocessOrchestrator(log_level=args.log_level)
    
    if args.no_parallel:
        orchestrator.parallel_execution_enabled = False
    
    # Run orchestrated session
    orchestrator.run_orchestrated_session(args.prompt)
    
    # Display final status
    print("\n=== Session Status ===")
    print(json.dumps(orchestrator.get_status(), indent=2))


if __name__ == "__main__":
    main()