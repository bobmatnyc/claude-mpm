"""Orchestrator using Claude's system prompt feature."""

import subprocess
import os
from pathlib import Path
from typing import Optional
from datetime import datetime
import logging
import tempfile

try:
    from ..utils.logger import get_logger, setup_logging
    from .ticket_extractor import TicketExtractor
    from ..core.framework_loader import FrameworkLoader
    from .agent_delegator import AgentDelegator
    from ..hooks.hook_client import HookServiceClient
except ImportError:
    from utils.logger import get_logger, setup_logging
    from orchestration.ticket_extractor import TicketExtractor
    from core.framework_loader import FrameworkLoader
    from orchestration.agent_delegator import AgentDelegator
    try:
        from hooks.hook_client import HookServiceClient
    except ImportError:
        HookServiceClient = None


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
        self.ticket_extractor = TicketExtractor()
        self.agent_delegator = AgentDelegator(self.framework_loader.agent_registry)
        
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
            
            # Build command with system prompt
            cmd = [
                "claude",
                "--model", "opus",
                "--dangerously-skip-permissions",
                "--append-system-prompt", framework  # Append to default system prompt
            ]
            
            self.logger.info("Starting Claude with framework as system prompt")
            
            # Note: In interactive mode, we cannot intercept Task tool delegations
            # as they are handled internally by Claude. Future enhancement could
            # use a different approach like pexpect to monitor the output stream.
            
            # Run Claude interactively with framework as system prompt
            result = subprocess.run(cmd)
            
            self.logger.info(f"Claude exited with code: {result.returncode}")
            
            # Post-session hook (no delegations captured in interactive mode)
            if self.hook_client:
                try:
                    self.logger.info("Calling post-session hook")
                    hook_results = self.hook_client.execute_post_delegation_hook(
                        agent="system",
                        result={
                            "task": "Interactive session completed",
                            "exit_code": result.returncode,
                            "session_type": "interactive",
                            "note": "Task delegations not captured in interactive mode"
                        }
                    )
                    if hook_results:
                        self.logger.info(f"Post-session hook executed: {len(hook_results)} hooks processed")
                        # Extract any tickets from hook results
                        tickets = self.hook_client.get_extracted_tickets(hook_results)
                        if tickets:
                            self.logger.info(f"Extracted {len(tickets)} tickets from hooks")
                            for ticket in tickets:
                                self.ticket_extractor.add_ticket(ticket)
                except Exception as e:
                    self.logger.warning(f"Post-session hook error: {e}")
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(framework_file)
            except:
                pass
            
            # Create tickets from any logged interactions
            self._create_tickets()
    
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
            
            # Use minimal framework for non-interactive mode
            try:
                from ..core.minimal_framework_loader import MinimalFrameworkLoader
            except ImportError:
                from core.minimal_framework_loader import MinimalFrameworkLoader
            
            minimal_loader = MinimalFrameworkLoader(self.framework_loader.framework_path)
            framework = minimal_loader.get_framework_instructions()
            
            # Log framework size
            if self.log_level != "OFF":
                self.logger.info(f"Using minimal framework: {len(framework)} chars")
            
            full_message = framework + "\n\nUser: " + user_input
            
            # Build command
            cmd = [
                "claude",
                "--model", "opus",
                "--dangerously-skip-permissions",
                "--print"  # Print mode
            ]
            
            # Run Claude with message as stdin (increased timeout for larger prompts)
            result = subprocess.run(cmd, input=full_message, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                print(result.stdout)
                
                # Process output for tickets and delegations
                delegations_detected = []
                for line in result.stdout.split('\n'):
                    # Extract tickets
                    tickets = self.ticket_extractor.extract_from_line(line)
                    for ticket in tickets:
                        if self.log_level != "OFF":
                            self.logger.info(f"Extracted ticket: {ticket['type']} - {ticket['title']}")
                    
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
                            # Extract any tickets from hook results
                            tickets = self.hook_client.get_extracted_tickets(hook_results)
                            if tickets:
                                self.logger.info(f"Extracted {len(tickets)} tickets from hooks")
                                for ticket in tickets:
                                    self.ticket_extractor.add_ticket(ticket)
                    except Exception as e:
                        self.logger.warning(f"Post-delegation hook error: {e}")
            else:
                print(f"Error: {result.stderr}")
                
            # Create tickets
            self._create_tickets()
                
        except Exception as e:
            print(f"Error: {e}")
            self.logger.error(f"Non-interactive error: {e}")