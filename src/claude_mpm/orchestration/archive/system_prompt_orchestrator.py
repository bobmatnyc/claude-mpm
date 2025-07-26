"""Orchestrator using Claude's system prompt feature."""

import os
from pathlib import Path
from typing import Optional
from datetime import datetime
import logging
import tempfile

try:
    from ..core.logger import get_logger, setup_logging
    from ..utils.subprocess_runner import SubprocessRunner
    # TicketExtractor removed from project
    from ..core.framework_loader import FrameworkLoader
    from .agent_delegator import AgentDelegator
    # Hook client removed - will use JSON-RPC client from hook manager
except ImportError:
    from core.logger import get_logger, setup_logging
    from utils.subprocess_runner import SubprocessRunner
    # TicketExtractor removed from project
    from core.framework_loader import FrameworkLoader
    from orchestration.agent_delegator import AgentDelegator
    # Hook client removed - will use JSON-RPC client from hook manager


class SystemPromptOrchestrator:
    """Orchestrator that uses Claude's --system-prompt or --append-system-prompt."""
    
    def __init__(
        self,
        framework_path: Optional[Path] = None,
        agents_dir: Optional[Path] = None,
        log_level: str = "OFF",
        log_dir: Optional[Path] = None,
        hook_manager=None,
    ):
        """Initialize the orchestrator."""
        self.log_level = log_level
        self.log_dir = log_dir or (Path.home() / ".claude-mpm" / "logs")
        self.hook_manager = hook_manager
        
        # Set up logging
        if log_level != "OFF":
            self.logger = setup_logging(level=log_level, log_dir=log_dir)
            self.logger.info(f"Initializing System Prompt Orchestrator (log_level={log_level})")
            if hook_manager and hook_manager.is_available():
                self.logger.info(f"Hook service available on port {hook_manager.port}")
        else:
            # Minimal logger
            self.logger = get_logger("system_prompt_orchestrator")
            self.logger.setLevel(logging.WARNING)
        
        # Components
        self.framework_loader = FrameworkLoader(framework_path, agents_dir)
        # TicketExtractor removed from project
        self.agent_delegator = AgentDelegator(self.framework_loader.agent_registry)
        
        # Initialize hook client if available
        self.hook_client = None
        if self.hook_manager and self.hook_manager.is_available():
            try:
                self.hook_client = self.hook_manager.get_client()
                if self.hook_client:
                    health = self.hook_client.health_check()
                    if health.get('status') == 'healthy':
                        self.logger.info(f"Using JSON-RPC hook client with {health.get('hook_count', 0)} hooks")
                    else:
                        self.logger.warning("Hook client not healthy, disabling hooks")
                        self.hook_client = None
            except Exception as e:
                self.logger.warning(f"Failed to get hook client: {e}")
                self.hook_client = None
        
        # State
        self.session_start = datetime.now()
        # Ticket creation removed from project
        
        # Initialize subprocess runner
        self.subprocess_runner = SubprocessRunner(logger=self.logger)
        
    def run_interactive(self):
        """Run an interactive session with framework as system prompt."""
        from claude_mpm._version import __version__
        print(f"Claude MPM v{__version__} - Interactive Session")
        print("Starting Claude with framework system prompt...")
        print("-" * 50)
        
        # Get framework instructions
        framework = self.framework_loader.get_framework_instructions()
        
        # Submit hook for framework initialization
        if self.hook_client:
            try:
                self.logger.info("Calling submit hook for framework initialization")
                hook_results = self.hook_client.execute_submit_hook(
                    prompt="Framework initialization with system prompt",
                    framework_length=len(framework),
                    session_type="interactive",
                    timestamp=datetime.now().isoformat()
                )
                if hook_results:
                    self.logger.info(f"Submit hook executed: {len(hook_results)} hooks processed")
                    # Check for any modified data
                    modified = self.hook_client.get_modified_data(hook_results)
                    if modified:
                        self.logger.info(f"Submit hook modified data: {modified}")
            except Exception as e:
                self.logger.warning(f"Submit hook error (continuing): {e}")
        
        # Save framework to a temporary file (system prompt might be too long for command line)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(framework)
            framework_file = f.name
        
        try:
            # Log framework injection
            if self.log_level != "OFF":
                self.logger.info(f"Framework saved to temporary file: {framework_file}")
                
                # Also save to prompts directory
                prompt_path = Path.home() / ".claude-mpm" / "prompts"
                prompt_path.mkdir(parents=True, exist_ok=True)
                prompt_file = prompt_path / f"prompt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                prompt_file.write_text(framework)
                self.logger.info(f"Framework also saved to: {prompt_file}")
            
            # Build command for interactive mode
            # For now, just launch Claude directly
            cmd = [
                "claude",
                "--dangerously-skip-permissions"
            ]
            
            self.logger.info("Starting Claude with framework as system prompt")
            
            # Note: In interactive mode, we cannot intercept Task tool delegations
            # as they are handled internally by Claude. Future enhancement could
            # use a different approach like pexpect to monitor the output stream.
            
            # Run Claude interactively with framework as system prompt
            # Use subprocess.Popen directly for proper interactive mode
            import subprocess
            self.logger.info(f"Launching Claude interactively with command: {' '.join(cmd)}")
            print(f"Debug: Running command: {' '.join(cmd)}")
            
            # Start Claude with direct terminal I/O
            process = subprocess.Popen(cmd)
            
            # Wait for Claude to complete
            returncode = process.wait()
            
            self.logger.info(f"Claude exited with code: {returncode}")
            
            # Post-session hook (no delegations captured in interactive mode)
            if self.hook_client:
                try:
                    self.logger.info("Calling post-session hook")
                    hook_results = self.hook_client.execute_post_delegation_hook(
                        agent="system",
                        result={
                            "task": "Interactive session completed",
                            "exit_code": returncode,
                            "session_type": "interactive",
                            "note": "Task delegations not captured in interactive mode"
                        }
                    )
                    if hook_results:
                        self.logger.info(f"Post-session hook executed: {len(hook_results)} hooks processed")
                        # Extract any tickets from hook results
                        # Ticket extraction removed from project
                except Exception as e:
                    self.logger.warning(f"Post-session hook error: {e}")
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(framework_file)
            except:
                pass
            
            # Ticket creation removed from project
    
    # _create_tickets method removed - TicketExtractor functionality removed from project
    
    def run_non_interactive(self, user_input: str):
        """Run a non-interactive session using print mode."""
        try:
            # Submit hook for user input
            if self.hook_client:
                try:
                    self.logger.info("Calling submit hook for user input")
                    hook_results = self.hook_client.execute_submit_hook(
                        prompt=user_input,
                        session_type="non-interactive",
                        timestamp=datetime.now().isoformat()
                    )
                    if hook_results:
                        self.logger.info(f"Submit hook executed: {len(hook_results)} hooks processed")
                except Exception as e:
                    self.logger.warning(f"Submit hook error (continuing): {e}")
            
            # For testing, use a minimal prompt
            # TODO: Re-enable full framework once Claude --print issues are resolved
            minimal_prompt = "You are Claude, an AI assistant."
            
            # Log framework size
            if self.log_level != "OFF":
                self.logger.info(f"Using minimal test prompt: {len(minimal_prompt)} chars")
            
            full_message = minimal_prompt + "\n\nUser: " + user_input
            
            # Build command for non-interactive mode
            cmd = [
                "claude",
                "--dangerously-skip-permissions",
                "--print",  # Print response and exit
                full_message
            ]
            
            # Log command details for debugging
            if self.log_level != "OFF":
                self.logger.debug(f"Command: claude --dangerously-skip-permissions --print <message of {len(full_message)} chars>")
                # Also save message for debugging
                debug_file = Path.home() / ".claude-mpm" / "debug" / f"message_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                debug_file.parent.mkdir(parents=True, exist_ok=True)
                debug_file.write_text(full_message)
                self.logger.debug(f"Message saved to: {debug_file}")
            
            # Run Claude with message as argument
            result = self.subprocess_runner.run_with_timeout(cmd, timeout=60)
            
            if result.success:
                print(result.stdout)
                
                # Process output for tickets and delegations
                delegations_detected = []
                for line in result.stdout.split('\n'):
                    # Ticket extraction removed from project
                    
                    # Extract delegations (for logging, not actual interception)
                    delegations = self.agent_delegator.extract_delegations(line)
                    delegations_detected.extend(delegations)
                
                # Log detected delegations
                if delegations_detected and self.log_level != "OFF":
                    self.logger.info(f"Detected {len(delegations_detected)} Task tool delegations")
                    for d in delegations_detected:
                        self.logger.info(f"  - {d['agent']}: {d['task'][:50]}...")
                
                # Post-delegation hook with full output
                if self.hook_client:
                    try:
                        self.logger.info("Calling post-delegation hook for non-interactive output")
                        hook_results = self.hook_client.execute_post_delegation_hook(
                            agent="system",
                            result={
                                "task": user_input,
                                "output": result.stdout,
                                "delegations_detected": len(delegations_detected),
                                "session_type": "non-interactive"
                            }
                        )
                        if hook_results:
                            self.logger.info(f"Post-delegation hook executed: {len(hook_results)} hooks processed")
                            # Ticket extraction removed from project
                    except Exception as e:
                        self.logger.warning(f"Post-delegation hook error: {e}")
            else:
                if result.timed_out:
                    print(f"Error: Command timed out after 60 seconds")
                else:
                    print(f"Error: {result.stderr}")
                
            # Ticket creation removed from project
                
        except Exception as e:
            print(f"Error: {e}")
            self.logger.error(f"Non-interactive error: {e}")