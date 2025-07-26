"""Simplified Claude runner replacing the complex orchestrator system."""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from claude_mpm.services.agent_deployment import AgentDeploymentService
    from claude_mpm.services.ticket_manager import TicketManager
    from claude_mpm.core.logger import get_logger, get_project_logger, ProjectLogger
except ImportError:
    from claude_mpm.services.agent_deployment import AgentDeploymentService
    from claude_mpm.services.ticket_manager import TicketManager
    from claude_mpm.core.logger import get_logger, get_project_logger, ProjectLogger


class SimpleClaudeRunner:
    """
    Simplified Claude runner that replaces the entire orchestrator system.
    
    This does exactly what we need:
    1. Deploy native agents to .claude/agents/
    2. Run Claude CLI with basic subprocess calls
    3. Extract tickets if needed
    4. Handle both interactive and non-interactive modes
    """
    
    def __init__(
        self,
        enable_tickets: bool = True,
        log_level: str = "OFF",
        claude_args: Optional[list] = None
    ):
        """Initialize the simple runner."""
        self.enable_tickets = enable_tickets
        self.log_level = log_level
        self.logger = get_logger("simple_runner")
        self.claude_args = claude_args or []
        
        # Initialize project logger for session logging
        self.project_logger = None
        if log_level != "OFF":
            try:
                self.project_logger = get_project_logger(log_level)
                self.project_logger.log_system(
                    "Initializing SimpleClaudeRunner",
                    level="INFO",
                    component="runner"
                )
            except Exception as e:
                self.logger.warning(f"Failed to initialize project logger: {e}")
        
        # Initialize services
        self.deployment_service = AgentDeploymentService()
        if enable_tickets:
            try:
                self.ticket_manager = TicketManager()
            except (ImportError, TypeError, Exception) as e:
                self.logger.warning(f"Ticket manager not available: {e}")
                self.ticket_manager = None
                self.enable_tickets = False
        
        # Load system instructions
        self.system_instructions = self._load_system_instructions()
        
        # Track if we need to create session logs
        self.session_log_file = None
        if self.project_logger and log_level != "OFF":
            try:
                # Create a system.jsonl file in the session directory
                self.session_log_file = self.project_logger.session_dir / "system.jsonl"
                self._log_session_event({
                    "event": "session_start",
                    "runner": "SimpleClaudeRunner",
                    "enable_tickets": enable_tickets,
                    "log_level": log_level
                })
            except Exception as e:
                self.logger.debug(f"Failed to create session log file: {e}")
    
    def setup_agents(self) -> bool:
        """Deploy native agents to .claude/agents/."""
        try:
            if self.project_logger:
                self.project_logger.log_system(
                    "Starting agent deployment",
                    level="INFO",
                    component="deployment"
                )
            
            results = self.deployment_service.deploy_agents()
            
            if results["deployed"] or results.get("updated", []):
                deployed_count = len(results['deployed'])
                updated_count = len(results.get('updated', []))
                
                if deployed_count > 0:
                    print(f"✓ Deployed {deployed_count} native agents")
                if updated_count > 0:
                    print(f"✓ Updated {updated_count} agents")
                
                if self.project_logger:
                    self.project_logger.log_system(
                        f"Agent deployment successful: {deployed_count} deployed, {updated_count} updated",
                        level="INFO",
                        component="deployment"
                    )
                    
                # Set Claude environment
                self.deployment_service.set_claude_environment()
                return True
            else:
                self.logger.info("All agents already up to date")
                if self.project_logger:
                    self.project_logger.log_system(
                        "All agents already up to date",
                        level="INFO",
                        component="deployment"
                    )
                return True
                
        except Exception as e:
            self.logger.error(f"Agent deployment failed: {e}")
            print(f"⚠️  Agent deployment failed: {e}")
            if self.project_logger:
                self.project_logger.log_system(
                    f"Agent deployment failed: {e}",
                    level="ERROR",
                    component="deployment"
                )
            return False
    
    def run_interactive(self, initial_context: Optional[str] = None):
        """Run Claude in interactive mode."""
        # Get version
        try:
            from claude_mpm import __version__
            version_str = f"v{__version__}"
        except:
            version_str = "v0.0.0"
        
        # Print styled welcome box
        print("\033[32m╭───────────────────────────────────────────────────╮\033[0m")
        print("\033[32m│\033[0m ✻ Claude MPM - Interactive Session                \033[32m│\033[0m")
        print(f"\033[32m│\033[0m   Version {version_str:<40}\033[32m│\033[0m")
        print("\033[32m│                                                   │\033[0m")
        print("\033[32m│\033[0m   Type '/agents' to see available agents          \033[32m│\033[0m")
        print("\033[32m╰───────────────────────────────────────────────────╯\033[0m")
        print("")  # Add blank line after box
        
        if self.project_logger:
            self.project_logger.log_system(
                "Starting interactive session",
                level="INFO",
                component="session"
            )
        
        # Setup agents
        if not self.setup_agents():
            print("Continuing without native agents...")
        
        # Build command with system instructions
        cmd = [
            "claude",
            "--model", "opus", 
            "--dangerously-skip-permissions"
        ]
        
        # Add any custom Claude arguments
        if self.claude_args:
            cmd.extend(self.claude_args)
        
        # Add system instructions if available
        system_prompt = self._create_system_prompt()
        if system_prompt and system_prompt != create_simple_context():
            cmd.extend(["--append-system-prompt", system_prompt])
        
        # Run interactive Claude directly
        try:
            # Use execvp to replace the current process with Claude
            # This should avoid any subprocess issues
            
            # Clean environment
            clean_env = os.environ.copy()
            claude_vars_to_remove = [
                'CLAUDE_CODE_ENTRYPOINT', 'CLAUDECODE', 'CLAUDE_CONFIG_DIR',
                'CLAUDE_MAX_PARALLEL_SUBAGENTS', 'CLAUDE_TIMEOUT'
            ]
            for var in claude_vars_to_remove:
                clean_env.pop(var, None)
            
            print("Launching Claude...")
            
            if self.project_logger:
                self.project_logger.log_system(
                    "Launching Claude interactive mode",
                    level="INFO",
                    component="session"
                )
                self._log_session_event({
                    "event": "launching_claude_interactive",
                    "command": " ".join(cmd)
                })
            
            # Replace current process with Claude
            os.execvpe(cmd[0], cmd, clean_env)
            
        except Exception as e:
            print(f"Failed to launch Claude: {e}")
            if self.project_logger:
                self.project_logger.log_system(
                    f"Failed to launch Claude: {e}",
                    level="ERROR",
                    component="session"
                )
                self._log_session_event({
                    "event": "interactive_launch_failed",
                    "error": str(e),
                    "exception_type": type(e).__name__
                })
            # Fallback to subprocess
            try:
                subprocess.run(cmd, stdin=None, stdout=None, stderr=None)
                if self.project_logger:
                    self.project_logger.log_system(
                        "Interactive session completed (subprocess fallback)",
                        level="INFO",
                        component="session"
                    )
                    self._log_session_event({
                        "event": "interactive_session_complete",
                        "fallback": True
                    })
            except Exception as fallback_error:
                print(f"Fallback also failed: {fallback_error}")
                if self.project_logger:
                    self.project_logger.log_system(
                        f"Fallback launch failed: {fallback_error}",
                        level="ERROR",
                        component="session"
                    )
                    self._log_session_event({
                        "event": "interactive_fallback_failed",
                        "error": str(fallback_error),
                        "exception_type": type(fallback_error).__name__
                    })
    
    def run_oneshot(self, prompt: str, context: Optional[str] = None) -> bool:
        """Run Claude with a single prompt and return success status."""
        start_time = time.time()
        
        if self.project_logger:
            self.project_logger.log_system(
                f"Starting non-interactive session with prompt: {prompt[:100]}",
                level="INFO",
                component="session"
            )
        
        # Setup agents
        if not self.setup_agents():
            print("Continuing without native agents...")
        
        # Combine context and prompt
        full_prompt = prompt
        if context:
            full_prompt = f"{context}\n\n{prompt}"
        
        # Build command with system instructions
        cmd = [
            "claude",
            "--model", "opus",
            "--dangerously-skip-permissions"
        ]
        
        # Add any custom Claude arguments
        if self.claude_args:
            cmd.extend(self.claude_args)
        
        # Add print and prompt
        cmd.extend(["--print", full_prompt])
        
        # Add system instructions if available
        system_prompt = self._create_system_prompt()
        if system_prompt and system_prompt != create_simple_context():
            # Insert system prompt before the user prompt
            cmd.insert(-2, "--append-system-prompt")
            cmd.insert(-2, system_prompt)
        
        try:
            # Run Claude
            if self.project_logger:
                self.project_logger.log_system(
                    "Executing Claude subprocess",
                    level="INFO",
                    component="session"
                )
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            execution_time = time.time() - start_time
            
            if result.returncode == 0:
                response = result.stdout.strip()
                print(response)
                
                if self.project_logger:
                    # Log successful completion
                    self.project_logger.log_system(
                        f"Non-interactive session completed successfully in {execution_time:.2f}s",
                        level="INFO",
                        component="session"
                    )
                    
                    # Log session event
                    self._log_session_event({
                        "event": "session_complete",
                        "success": True,
                        "execution_time": execution_time,
                        "response_length": len(response)
                    })
                    
                    # Log agent invocation if we detect delegation patterns
                    if self._contains_delegation(response):
                        self.project_logger.log_system(
                            "Detected potential agent delegation in response",
                            level="INFO",
                            component="delegation"
                        )
                        self._log_session_event({
                            "event": "delegation_detected",
                            "prompt": prompt[:200],
                            "indicators": [p for p in ["Task(", "subagent_type=", "engineer agent", "qa agent"] 
                                          if p.lower() in response.lower()]
                        })
                
                # Extract tickets if enabled
                if self.enable_tickets and self.ticket_manager and response:
                    self._extract_tickets(response)
                
                return True
            else:
                error_msg = result.stderr or "Unknown error"
                print(f"Error: {error_msg}")
                
                if self.project_logger:
                    self.project_logger.log_system(
                        f"Non-interactive session failed: {error_msg}",
                        level="ERROR",
                        component="session"
                    )
                    self._log_session_event({
                        "event": "session_failed",
                        "success": False,
                        "error": error_msg,
                        "return_code": result.returncode
                    })
                
                return False
                
        except Exception as e:
            print(f"Error: {e}")
            
            if self.project_logger:
                self.project_logger.log_system(
                    f"Exception during non-interactive session: {e}",
                    level="ERROR",
                    component="session"
                )
                self._log_session_event({
                    "event": "session_exception",
                    "success": False,
                    "exception": str(e),
                    "exception_type": type(e).__name__
                })
            
            return False
        finally:
            # Ensure logs are flushed
            if self.project_logger:
                try:
                    # Log session summary
                    summary = self.project_logger.get_session_summary()
                    self.project_logger.log_system(
                        f"Session {summary['session_id']} completed",
                        level="INFO",
                        component="session"
                    )
                except Exception as e:
                    self.logger.debug(f"Failed to log session summary: {e}")
    
    def _extract_tickets(self, text: str):
        """Extract tickets from Claude's response."""
        if not self.ticket_manager:
            return
            
        try:
            # Use the ticket manager's extraction logic if available
            if hasattr(self.ticket_manager, 'extract_tickets_from_text'):
                tickets = self.ticket_manager.extract_tickets_from_text(text)
                if tickets:
                    print(f"\n📋 Extracted {len(tickets)} tickets")
                    for ticket in tickets[:3]:  # Show first 3
                        print(f"  - [{ticket.get('id', 'N/A')}] {ticket.get('title', 'No title')}")
                    if len(tickets) > 3:
                        print(f"  ... and {len(tickets) - 3} more")
            else:
                self.logger.debug("Ticket extraction method not available")
        except Exception as e:
            self.logger.debug(f"Ticket extraction failed: {e}")

    def _load_system_instructions(self) -> Optional[str]:
        """Load system instructions from agents/INSTRUCTIONS.md."""
        try:
            # Find the INSTRUCTIONS.md file
            module_path = Path(__file__).parent.parent
            instructions_path = module_path / "agents" / "INSTRUCTIONS.md"
            
            if not instructions_path.exists():
                self.logger.warning(f"System instructions not found: {instructions_path}")
                return None
            
            instructions = instructions_path.read_text()
            self.logger.info("Loaded PM framework system instructions")
            return instructions
            
        except Exception as e:
            self.logger.error(f"Failed to load system instructions: {e}")
            return None

    def _create_system_prompt(self) -> str:
        """Create the complete system prompt including instructions."""
        if self.system_instructions:
            return self.system_instructions
        else:
            # Fallback to basic context
            return create_simple_context()
    
    def _contains_delegation(self, text: str) -> bool:
        """Check if text contains signs of agent delegation."""
        # Look for common delegation patterns
        delegation_patterns = [
            "Task(",
            "subagent_type=",
            "delegating to",
            "asking the",
            "engineer agent",
            "qa agent",
            "documentation agent",
            "research agent",
            "security agent",
            "ops agent",
            "version_control agent",
            "data_engineer agent"
        ]
        
        text_lower = text.lower()
        return any(pattern.lower() in text_lower for pattern in delegation_patterns)
    
    def _log_session_event(self, event_data: dict):
        """Log an event to the session log file."""
        if self.session_log_file:
            try:
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    **event_data
                }
                
                with open(self.session_log_file, 'a') as f:
                    f.write(json.dumps(log_entry) + '\n')
            except Exception as e:
                self.logger.debug(f"Failed to log session event: {e}")


def create_simple_context() -> str:
    """Create basic context for Claude."""
    return """You are Claude Code running in Claude MPM (Multi-Agent Project Manager).

You have access to native subagents via the Task tool with subagent_type parameter:
- engineer: For coding, implementation, and technical tasks
- qa: For testing, validation, and quality assurance  
- documentation: For docs, guides, and explanations
- research: For investigation and analysis
- security: For security-related tasks
- ops: For deployment and infrastructure
- version-control: For git and version management
- data-engineer: For data processing and APIs

Use these agents by calling: Task(description="task description", subagent_type="agent_name")

Work efficiently and delegate appropriately to subagents when needed."""


# Convenience functions for backward compatibility
def run_claude_interactive(context: Optional[str] = None):
    """Run Claude interactively with optional context."""
    runner = SimpleClaudeRunner()
    if context is None:
        context = create_simple_context()
    runner.run_interactive(context)


def run_claude_oneshot(prompt: str, context: Optional[str] = None) -> bool:
    """Run Claude with a single prompt."""
    runner = SimpleClaudeRunner()
    if context is None:
        context = create_simple_context()
    return runner.run_oneshot(prompt, context)