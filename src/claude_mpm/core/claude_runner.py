"""Claude runner with both exec and subprocess launch methods."""

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
import uuid

try:
    from claude_mpm.services.agent_deployment import AgentDeploymentService
    from claude_mpm.services.ticket_manager import TicketManager
    from claude_mpm.services.hook_service import HookService
    from claude_mpm.core.config import Config
    from claude_mpm.core.logger import get_logger, get_project_logger, ProjectLogger
except ImportError:
    from claude_mpm.services.agent_deployment import AgentDeploymentService
    from claude_mpm.services.ticket_manager import TicketManager
    from claude_mpm.services.hook_service import HookService
    from claude_mpm.core.config import Config
    from claude_mpm.core.logger import get_logger, get_project_logger, ProjectLogger


class ClaudeRunner:
    """
    Claude runner that replaces the entire orchestrator system.
    
    This does exactly what we need:
    1. Deploy native agents to .claude/agents/
    2. Run Claude CLI with either exec or subprocess
    3. Extract tickets if needed
    4. Handle both interactive and non-interactive modes
    
    Supports two launch methods:
    - exec: Replace current process (default for backward compatibility)
    - subprocess: Launch as child process for more control
    """
    
    def __init__(
        self,
        enable_tickets: bool = True,
        log_level: str = "OFF",
        claude_args: Optional[list] = None,
        launch_method: str = "exec",  # "exec" or "subprocess"
        enable_websocket: bool = False,
        websocket_port: int = 8765
    ):
        """Initialize the Claude runner."""
        self.enable_tickets = enable_tickets
        self.log_level = log_level
        self.logger = get_logger("claude_runner")
        self.claude_args = claude_args or []
        self.launch_method = launch_method
        self.enable_websocket = enable_websocket
        self.websocket_port = websocket_port
        
        # Initialize project logger for session logging
        self.project_logger = None
        if log_level != "OFF":
            try:
                self.project_logger = get_project_logger(log_level)
                self.project_logger.log_system(
                    f"Initializing ClaudeRunner with {launch_method} launcher",
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
        
        # Initialize hook service and register memory hooks
        self.config = Config()
        self.hook_service = HookService(self.config)
        self._register_memory_hooks()
        
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
                    "runner": "ClaudeRunner",
                    "enable_tickets": enable_tickets,
                    "log_level": log_level,
                    "launch_method": launch_method
                })
            except Exception as e:
                self.logger.debug(f"Failed to create session log file: {e}")
        
        # Initialize Socket.IO server reference
        self.websocket_server = None
    
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
        # Connect to Socket.IO server if enabled
        if self.enable_websocket:
            try:
                # Use Socket.IO client proxy to connect to monitoring server
                from claude_mpm.services.socketio_server import SocketIOClientProxy
                self.websocket_server = SocketIOClientProxy(port=self.websocket_port)
                self.websocket_server.start()
                self.logger.info("Connected to Socket.IO monitoring server")
                
                # Generate session ID
                session_id = str(uuid.uuid4())
                working_dir = os.getcwd()
                
                # Notify session start
                self.websocket_server.session_started(
                    session_id=session_id,
                    launch_method=self.launch_method,
                    working_dir=working_dir
                )
            except Exception as e:
                self.logger.warning(f"Failed to connect to Socket.IO server: {e}")
                self.websocket_server = None
        
        # Get version with robust fallback mechanisms
        version_str = self._get_version()
        
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
            
            # Set the correct working directory for Claude Code
            # If CLAUDE_MPM_USER_PWD is set, use that as the working directory
            if 'CLAUDE_MPM_USER_PWD' in clean_env:
                user_pwd = clean_env['CLAUDE_MPM_USER_PWD']
                clean_env['CLAUDE_WORKSPACE'] = user_pwd
                # Also change to that directory before launching Claude
                try:
                    os.chdir(user_pwd)
                    self.logger.info(f"Changed working directory to: {user_pwd}")
                except Exception as e:
                    self.logger.warning(f"Could not change to user directory {user_pwd}: {e}")
            
            print("Launching Claude...")
            
            if self.project_logger:
                self.project_logger.log_system(
                    f"Launching Claude interactive mode with {self.launch_method}",
                    level="INFO",
                    component="session"
                )
                self._log_session_event({
                    "event": "launching_claude_interactive",
                    "command": " ".join(cmd),
                    "method": self.launch_method
                })
            
            # Notify WebSocket clients
            if self.websocket_server:
                self.websocket_server.claude_status_changed(
                    status="starting",
                    message="Launching Claude interactive session"
                )
            
            # Launch using selected method
            if self.launch_method == "subprocess":
                self._launch_subprocess_interactive(cmd, clean_env)
            else:
                # Default to exec for backward compatibility
                if self.websocket_server:
                    # Notify before exec (we won't be able to after)
                    self.websocket_server.claude_status_changed(
                        status="running",
                        message="Claude process started (exec mode)"
                    )
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
            
            # Notify WebSocket clients of error
            if self.websocket_server:
                self.websocket_server.claude_status_changed(
                    status="error",
                    message=f"Failed to launch Claude: {e}"
                )
            # Fallback to subprocess
            try:
                # Use the same clean_env we prepared earlier
                subprocess.run(cmd, stdin=None, stdout=None, stderr=None, env=clean_env)
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
        
        # Connect to Socket.IO server if enabled
        if self.enable_websocket:
            try:
                # Use Socket.IO client proxy to connect to monitoring server
                from claude_mpm.services.socketio_server import SocketIOClientProxy
                self.websocket_server = SocketIOClientProxy(port=self.websocket_port)
                self.websocket_server.start()
                self.logger.info("Connected to Socket.IO monitoring server")
                
                # Generate session ID
                session_id = str(uuid.uuid4())
                working_dir = os.getcwd()
                
                # Notify session start
                self.websocket_server.session_started(
                    session_id=session_id,
                    launch_method="oneshot",
                    working_dir=working_dir
                )
            except Exception as e:
                self.logger.warning(f"Failed to connect to Socket.IO server: {e}")
                self.websocket_server = None
        
        # Check for /mpm: commands
        if prompt.strip().startswith("/mpm:"):
            return self._handle_mpm_command(prompt.strip())
        
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
            # Set up environment with correct working directory
            env = os.environ.copy()
            
            # Set the correct working directory for Claude Code
            if 'CLAUDE_MPM_USER_PWD' in env:
                user_pwd = env['CLAUDE_MPM_USER_PWD']
                env['CLAUDE_WORKSPACE'] = user_pwd
                # Change to that directory before running Claude
                try:
                    original_cwd = os.getcwd()
                    os.chdir(user_pwd)
                    self.logger.info(f"Changed working directory to: {user_pwd}")
                except Exception as e:
                    self.logger.warning(f"Could not change to user directory {user_pwd}: {e}")
                    original_cwd = None
            else:
                original_cwd = None
            
            # Run Claude
            if self.project_logger:
                self.project_logger.log_system(
                    "Executing Claude subprocess",
                    level="INFO",
                    component="session"
                )
            
            # Notify WebSocket clients
            if self.websocket_server:
                self.websocket_server.claude_status_changed(
                    status="running",
                    message="Executing Claude oneshot command"
                )
            
            result = subprocess.run(cmd, capture_output=True, text=True, env=env)
            
            # Restore original directory if we changed it
            if original_cwd:
                try:
                    os.chdir(original_cwd)
                except Exception:
                    pass
            execution_time = time.time() - start_time
            
            if result.returncode == 0:
                response = result.stdout.strip()
                print(response)
                
                # Broadcast output to WebSocket clients
                if self.websocket_server and response:
                    self.websocket_server.claude_output(response, "stdout")
                
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
                        
                        # Notify WebSocket clients about delegation
                        if self.websocket_server:
                            # Try to extract agent name
                            agent_name = self._extract_agent_from_response(response)
                            if agent_name:
                                self.websocket_server.agent_delegated(
                                    agent=agent_name,
                                    task=prompt[:100],
                                    status="detected"
                                )
                
                # Extract tickets if enabled
                if self.enable_tickets and self.ticket_manager and response:
                    self._extract_tickets(response)
                
                return True
            else:
                error_msg = result.stderr or "Unknown error"
                print(f"Error: {error_msg}")
                
                # Broadcast error to WebSocket clients
                if self.websocket_server:
                    self.websocket_server.claude_output(error_msg, "stderr")
                    self.websocket_server.claude_status_changed(
                        status="error",
                        message=f"Command failed with code {result.returncode}"
                    )
                
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
            
            # End WebSocket session
            if self.websocket_server:
                self.websocket_server.claude_status_changed(
                    status="stopped",
                    message="Session completed"
                )
                self.websocket_server.session_ended()
    
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
        """Load and process system instructions from agents/INSTRUCTIONS.md.
        
        WHY: Process template variables like {{capabilities-list}} to include
        dynamic agent capabilities in the PM's system instructions.
        """
        try:
            # Find the INSTRUCTIONS.md file
            module_path = Path(__file__).parent.parent
            instructions_path = module_path / "agents" / "INSTRUCTIONS.md"
            
            if not instructions_path.exists():
                self.logger.warning(f"System instructions not found: {instructions_path}")
                return None
            
            # Read raw instructions
            raw_instructions = instructions_path.read_text()
            
            # Process template variables if ContentAssembler is available
            try:
                from claude_mpm.services.framework_claude_md_generator.content_assembler import ContentAssembler
                assembler = ContentAssembler()
                processed_instructions = assembler.apply_template_variables(raw_instructions)
                self.logger.info("Loaded and processed PM framework system instructions with dynamic capabilities")
                return processed_instructions
            except ImportError:
                self.logger.warning("ContentAssembler not available, using raw instructions")
                return raw_instructions
            except Exception as e:
                self.logger.warning(f"Failed to process template variables: {e}, using raw instructions")
                return raw_instructions
            
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
    
    def _extract_agent_from_response(self, text: str) -> Optional[str]:
        """Try to extract agent name from delegation response."""
        # Look for common patterns
        import re
        
        # Pattern 1: subagent_type="agent_name"
        match = re.search(r'subagent_type=["\']([^"\']*)["\'\)]', text)
        if match:
            return match.group(1)
        
        # Pattern 2: "engineer agent" etc
        agent_names = [
            "engineer", "qa", "documentation", "research", 
            "security", "ops", "version_control", "data_engineer"
        ]
        text_lower = text.lower()
        for agent in agent_names:
            if f"{agent} agent" in text_lower or f"agent: {agent}" in text_lower:
                return agent
        
        return None
    
    def _handle_mpm_command(self, prompt: str) -> bool:
        """Handle /mpm: commands directly without going to Claude."""
        try:
            # Extract command and arguments
            command_line = prompt[5:].strip()  # Remove "/mpm:"
            parts = command_line.split()
            
            if not parts:
                print("No command specified. Available commands: test")
                return True
            
            command = parts[0]
            args = parts[1:]
            
            # Handle commands
            if command == "test":
                print("Hello World")
                if self.project_logger:
                    self.project_logger.log_system(
                        "Executed /mpm:test command",
                        level="INFO",
                        component="command"
                    )
                return True
            elif command == "agents":
                # Handle agents command - display deployed agent versions
                # WHY: This provides users with a quick way to check deployed agent versions
                # directly from within Claude Code, maintaining consistency with CLI behavior
                try:
                    from claude_mpm.cli import _get_agent_versions_display
                    agent_versions = _get_agent_versions_display()
                    if agent_versions:
                        print(agent_versions)
                    else:
                        print("No deployed agents found")
                        print("\nTo deploy agents, run: claude-mpm --mpm:agents deploy")
                    
                    if self.project_logger:
                        self.project_logger.log_system(
                            "Executed /mpm:agents command",
                            level="INFO",
                            component="command"
                        )
                    return True
                except Exception as e:
                    print(f"Error getting agent versions: {e}")
                    return False
            else:
                print(f"Unknown command: {command}")
                print("Available commands: test, agents")
                return True
                
        except Exception as e:
            print(f"Error executing command: {e}")
            if self.project_logger:
                self.project_logger.log_system(
                    f"Failed to execute /mpm: command: {e}",
                    level="ERROR",
                    component="command"
                )
            return False
    
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
    
    def _get_version(self) -> str:
        """
        Robust version determination with multiple fallback mechanisms.
        
        WHY: The version display is critical for debugging and user experience.
        This implementation ensures we always show the correct version rather than 
        defaulting to v0.0.0, even in edge cases where imports might fail.
        
        DESIGN DECISION: We try multiple methods in order of preference:
        1. Package import (__version__) - fastest for normal installations
        2. importlib.metadata - standard for installed packages  
        3. VERSION file reading - fallback for development environments
        4. Only then default to v0.0.0 with detailed error logging
        
        Returns version string formatted as "vX.Y.Z"
        """
        version = "0.0.0"
        method_used = "default"
        
        # Method 1: Try package import (fastest, most common)
        try:
            from claude_mpm import __version__
            version = __version__
            method_used = "package_import"
            self.logger.debug(f"Version obtained via package import: {version}")
        except ImportError as e:
            self.logger.debug(f"Package import failed: {e}")
        except Exception as e:
            self.logger.warning(f"Unexpected error in package import: {e}")
        
        # Method 2: Try importlib.metadata (standard for installed packages)
        if version == "0.0.0":
            try:
                import importlib.metadata
                version = importlib.metadata.version('claude-mpm')
                method_used = "importlib_metadata"
                self.logger.debug(f"Version obtained via importlib.metadata: {version}")
            except importlib.metadata.PackageNotFoundError:
                self.logger.debug("Package not found in importlib.metadata (likely development install)")
            except ImportError:
                self.logger.debug("importlib.metadata not available (Python < 3.8)")
            except Exception as e:
                self.logger.warning(f"Unexpected error in importlib.metadata: {e}")
        
        # Method 3: Try reading VERSION file directly (development fallback)
        if version == "0.0.0":
            try:
                # Calculate path relative to this file
                version_file = Path(__file__).parent.parent.parent.parent / "VERSION"
                if version_file.exists():
                    version = version_file.read_text().strip()
                    method_used = "version_file"
                    self.logger.debug(f"Version obtained via VERSION file: {version}")
                else:
                    self.logger.debug(f"VERSION file not found at: {version_file}")
            except Exception as e:
                self.logger.warning(f"Failed to read VERSION file: {e}")
        
        # Log final result
        if version == "0.0.0":
            self.logger.error(
                "All version detection methods failed. This indicates a packaging or installation issue."
            )
        else:
            self.logger.debug(f"Final version: {version} (method: {method_used})")
        
        return f"v{version}"
    
    def _register_memory_hooks(self):
        """Register memory integration hooks with the hook service.
        
        WHY: This activates the memory system by registering hooks that automatically
        inject agent memory before delegation and extract learnings after delegation.
        This is the critical connection point between the memory system and the CLI.
        
        DESIGN DECISION: We register hooks here instead of in __init__ to ensure
        all services are initialized first. Hooks are only registered if the memory
        system is enabled in configuration.
        """
        try:
            # Only register if memory system is enabled
            if not self.config.get('memory.enabled', True):
                self.logger.debug("Memory system disabled - skipping hook registration")
                return
            
            # Import hook classes (lazy import to avoid circular dependencies)
            from claude_mpm.hooks.memory_integration_hook import (
                MemoryPreDelegationHook,
                MemoryPostDelegationHook
            )
            
            # Register pre-delegation hook for memory injection
            pre_hook = MemoryPreDelegationHook(self.config)
            success = self.hook_service.register_hook(pre_hook)
            if success:
                self.logger.info(f"✅ Registered memory pre-delegation hook (priority: {pre_hook.priority})")
            else:
                self.logger.warning("❌ Failed to register memory pre-delegation hook")
            
            # Register post-delegation hook if auto-learning is enabled
            if self.config.get('memory.auto_learning', True):  # Default to True now
                post_hook = MemoryPostDelegationHook(self.config)
                success = self.hook_service.register_hook(post_hook)
                if success:
                    self.logger.info(f"✅ Registered memory post-delegation hook (priority: {post_hook.priority})")
                else:
                    self.logger.warning("❌ Failed to register memory post-delegation hook")
            else:
                self.logger.info("ℹ️  Auto-learning disabled - skipping post-delegation hook")
            
            # Log summary of registered hooks
            hooks = self.hook_service.list_hooks()
            pre_count = len(hooks.get('pre_delegation', []))
            post_count = len(hooks.get('post_delegation', []))
            self.logger.info(f"📋 Hook Service initialized: {pre_count} pre-delegation, {post_count} post-delegation hooks")
            
        except Exception as e:
            self.logger.error(f"❌ Failed to register memory hooks: {e}")
            # Don't fail the entire initialization - memory system is optional
    
    def _launch_subprocess_interactive(self, cmd: list, env: dict):
        """Launch Claude as a subprocess with PTY for interactive mode."""
        import pty
        import select
        import termios
        import tty
        import signal
        
        # Save original terminal settings
        original_tty = None
        if sys.stdin.isatty():
            original_tty = termios.tcgetattr(sys.stdin)
        
        # Create PTY
        master_fd, slave_fd = pty.openpty()
        
        try:
            # Start Claude process
            process = subprocess.Popen(
                cmd,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                env=env
            )
            
            # Close slave in parent
            os.close(slave_fd)
            
            if self.project_logger:
                self.project_logger.log_system(
                    f"Claude subprocess started with PID {process.pid}",
                    level="INFO",
                    component="subprocess"
                )
            
            # Notify WebSocket clients
            if self.websocket_server:
                self.websocket_server.claude_status_changed(
                    status="running",
                    pid=process.pid,
                    message="Claude subprocess started"
                )
            
            # Set terminal to raw mode for proper interaction
            if sys.stdin.isatty():
                tty.setraw(sys.stdin)
            
            # Handle Ctrl+C gracefully
            def signal_handler(signum, frame):
                if process.poll() is None:
                    process.terminate()
                raise KeyboardInterrupt()
            
            signal.signal(signal.SIGINT, signal_handler)
            
            # I/O loop
            while True:
                # Check if process is still running
                if process.poll() is not None:
                    break
                
                # Check for data from Claude or stdin
                r, _, _ = select.select([master_fd, sys.stdin], [], [], 0)
                
                if master_fd in r:
                    try:
                        data = os.read(master_fd, 4096)
                        if data:
                            os.write(sys.stdout.fileno(), data)
                            # Broadcast output to WebSocket clients
                            if self.websocket_server:
                                try:
                                    # Decode and send
                                    output = data.decode('utf-8', errors='replace')
                                    self.websocket_server.claude_output(output, "stdout")
                                except Exception as e:
                                    self.logger.debug(f"Failed to broadcast output: {e}")
                        else:
                            break  # EOF
                    except OSError:
                        break
                
                if sys.stdin in r:
                    try:
                        data = os.read(sys.stdin.fileno(), 4096)
                        if data:
                            os.write(master_fd, data)
                    except OSError:
                        break
            
            # Wait for process to complete
            process.wait()
            
            if self.project_logger:
                self.project_logger.log_system(
                    f"Claude subprocess exited with code {process.returncode}",
                    level="INFO",
                    component="subprocess"
                )
            
            # Notify WebSocket clients
            if self.websocket_server:
                self.websocket_server.claude_status_changed(
                    status="stopped",
                    message=f"Claude subprocess exited with code {process.returncode}"
                )
            
        finally:
            # Restore terminal
            if original_tty and sys.stdin.isatty():
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, original_tty)
            
            # Close PTY
            try:
                os.close(master_fd)
            except:
                pass
            
            # Ensure process is terminated
            if 'process' in locals() and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            
            # End WebSocket session if in subprocess mode
            if self.websocket_server:
                self.websocket_server.session_ended()


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

IMPORTANT: The Task tool accepts both naming formats:
- Capitalized format: "Research", "Engineer", "QA", "Version Control", "Data Engineer"
- Lowercase format: "research", "engineer", "qa", "version-control", "data-engineer"

Both formats work correctly. When you see capitalized names (matching TodoWrite prefixes), 
automatically normalize them to lowercase-hyphenated format for the Task tool.

Work efficiently and delegate appropriately to subagents when needed."""


# Backward compatibility alias
SimpleClaudeRunner = ClaudeRunner


# Convenience functions for backward compatibility
def run_claude_interactive(context: Optional[str] = None):
    """Run Claude interactively with optional context."""
    runner = ClaudeRunner()
    if context is None:
        context = create_simple_context()
    runner.run_interactive(context)


def run_claude_oneshot(prompt: str, context: Optional[str] = None) -> bool:
    """Run Claude with a single prompt."""
    runner = ClaudeRunner()
    if context is None:
        context = create_simple_context()
    return runner.run_oneshot(prompt, context)