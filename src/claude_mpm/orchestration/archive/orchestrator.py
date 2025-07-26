"""Core orchestrator for Claude MPM."""

import subprocess
import threading
import queue
import os
import sys
import logging
import select
import fcntl
from pathlib import Path
from typing import Optional, List, Dict, Any, IO
from datetime import datetime

try:
    # Try relative imports first
    from ..core.logger import get_logger, setup_logging
    from ..utils.subprocess_runner import SubprocessRunner
    # TicketExtractor removed from project
    from ..core.framework_loader import FrameworkLoader
    from .agent_delegator import AgentDelegator
except ImportError:
    # Fall back to absolute imports
    from core.logger import get_logger, setup_logging
    from utils.subprocess_runner import SubprocessRunner
    # TicketExtractor removed from project
    from core.framework_loader import FrameworkLoader
    from orchestration.agent_delegator import AgentDelegator


class MPMOrchestrator:
    """
    Orchestrates Claude as a subprocess with framework injection and ticket extraction.
    
    This is the core component that:
    1. Launches Claude as a child process
    2. Injects framework instructions
    3. Intercepts I/O for ticket extraction
    4. Manages the session lifecycle
    """
    
    def __init__(
        self,
        framework_path: Optional[Path] = None,
        agents_dir: Optional[Path] = None,
        log_level: str = "OFF",
        log_dir: Optional[Path] = None,
    ):
        """
        Initialize the orchestrator.
        
        Args:
            framework_path: Path to framework directory
            agents_dir: Custom agents directory
            log_level: Logging level (OFF, INFO, DEBUG)
            log_dir: Custom log directory
        """
        self.log_level = log_level
        self.log_dir = log_dir or (Path.home() / ".claude-mpm" / "logs")
        
        # Set up logging
        if log_level != "OFF":
            self.logger = setup_logging(level=log_level, log_dir=log_dir)
            self.logger.info(f"Initializing MPM Orchestrator (log_level={log_level})")
        else:
            # Minimal logger
            self.logger = get_logger("orchestrator")
            self.logger.setLevel(logging.WARNING)
        
        # Components
        self.framework_loader = FrameworkLoader(framework_path, agents_dir)
        # TicketExtractor removed from project
        self.agent_delegator = AgentDelegator(self.framework_loader.agent_registry)
        
        # Process management
        self.process: Optional[subprocess.Popen] = None
        self.output_queue = queue.Queue()
        self.input_queue = queue.Queue()
        
        # State
        self.first_interaction = True
        self.session_start = datetime.now()
        self.session_log = []
        # Ticket creation removed from project
        
        # Threading
        self.output_thread: Optional[threading.Thread] = None
        self.input_thread: Optional[threading.Thread] = None
        self.running = False
        
    def start(self) -> bool:
        """
        Start the orchestrated Claude session.
        
        Returns:
            True if successfully started, False otherwise
        """
        try:
            # Find Claude executable
            claude_cmd = self._find_claude_executable()
            if not claude_cmd:
                self.logger.error("Claude executable not found")
                return False
            
            # Build command
            cmd = [claude_cmd]
            
            # Add model and permissions flags if needed
            if "--model" not in claude_cmd:
                cmd.extend(["--model", "opus"])
            if "--dangerously-skip-permissions" not in claude_cmd:
                cmd.append("--dangerously-skip-permissions")
            
            # For non-interactive mode, we can pass the prompt directly
            if hasattr(self, '_initial_prompt'):
                cmd.extend(["--print", self._initial_prompt])
            
            self.logger.info(f"Starting Claude subprocess: {' '.join(cmd)}")
            
            # Start subprocess without PTY for now
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0,  # Unbuffered
                universal_newlines=True,
            )
            self.use_pty = False
            
            self.logger.info(f"Claude subprocess started with PID: {self.process.pid}")
            
            # Start I/O threads
            self.running = True
            self.output_thread = threading.Thread(target=self._output_reader, daemon=True)
            self.error_thread = threading.Thread(target=self._error_reader, daemon=True)
            self.input_thread = threading.Thread(target=self._input_writer, daemon=True)
            
            self.output_thread.start()
            self.error_thread.start()
            self.input_thread.start()
            
            # Give Claude a moment to start up
            import time
            time.sleep(0.5)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start Claude: {e}")
            return False
    
    def _find_claude_executable(self) -> Optional[str]:
        """Find the Claude executable."""
        # Check common locations
        candidates = ["claude", "claude-cli", "/usr/local/bin/claude"]
        
        for candidate in candidates:
            if self._is_executable(candidate):
                return candidate
        
        # Check PATH
        import shutil
        claude_path = shutil.which("claude")
        if claude_path:
            return claude_path
            
        return None
    
    def _is_executable(self, path: str) -> bool:
        """Check if a path is an executable file."""
        try:
            return os.path.isfile(path) and os.access(path, os.X_OK)
        except:
            return False
    
    def _output_reader(self):
        """Read output from Claude subprocess."""
        response_buffer = []
        try:
            while self.running and self.process and self.process.poll() is None:
                line = self.process.stdout.readline()
                if line:
                    line = line.rstrip()
                    if self.log_level == "DEBUG":
                        self.logger.debug(f"Claude output: {line}")
                    response_buffer.append(line)
                    self._process_output_line(line)
                    
        except Exception as e:
            if self.log_level != "OFF":
                self.logger.error(f"Output reader error: {e}")
        finally:
            # Save complete response in DEBUG mode
            if self.log_level == "DEBUG" and response_buffer:
                session_path = Path.home() / ".claude-mpm" / "session"
                session_path.mkdir(parents=True, exist_ok=True)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
                response_file = session_path / f"response_{timestamp}.txt"
                response_file.write_text('\n'.join(response_buffer))
                self.logger.debug(f"Response saved to: {response_file}")
            
            if self.log_level == "DEBUG":
                self.logger.debug("Output reader thread ending")
    
    def _error_reader(self):
        """Read error output from Claude subprocess."""
        if self.use_pty:
            # In PTY mode, stderr goes to the same terminal
            return
            
        try:
            while self.running and self.process and self.process.poll() is None:
                line = self.process.stderr.readline()
                if line:
                    line = line.rstrip()
                    if self.log_level != "OFF":
                        self.logger.error(f"Claude stderr: {line}")
                    # Also display errors to user
                    print(f"Error: {line}")
        except Exception as e:
            if self.log_level != "OFF":
                self.logger.error(f"Error reader error: {e}")
    
    def _input_writer(self):
        """Write input to Claude subprocess."""
        try:
            while self.running and self.process:
                try:
                    user_input = self.input_queue.get(timeout=0.1)
                    
                    # Inject framework on first interaction
                    if self.first_interaction:
                        if self.log_level != "OFF":
                            self.logger.info("Injecting framework instructions")
                        framework = self.framework_loader.get_framework_instructions()
                        
                        # Log framework details for debugging
                        if self.log_level == "DEBUG":
                            self.logger.debug(f"Framework length: {len(framework)} characters")
                            self.logger.debug(f"Framework preview: {framework[:200]}...")
                        
                        full_input = framework + "\n\nUser Input: " + user_input
                        
                        # Save prompt to session directory when debugging
                        if self.log_level == "DEBUG":
                            session_path = Path.home() / ".claude-mpm" / "session"
                            session_path.mkdir(parents=True, exist_ok=True)
                            
                            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
                            prompt_file = session_path / f"prompt_{timestamp}.txt"
                            prompt_file.write_text(full_input)
                            self.logger.debug(f"Full prompt saved to: {prompt_file}")
                            
                            # Also save user input separately
                            user_input_file = session_path / f"user_input_{timestamp}.txt"
                            user_input_file.write_text(user_input)
                            
                        # Keep backward compatibility with prompts directory
                        prompt_log_path = Path.home() / ".claude-mpm" / "prompts"
                        prompt_log_path.mkdir(parents=True, exist_ok=True)
                        prompt_file = prompt_log_path / f"prompt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                        prompt_file.write_text(full_input)
                        
                        self.first_interaction = False
                    else:
                        full_input = user_input
                    
                    # Send to Claude
                    if self.log_level == "DEBUG":
                        self.logger.debug(f"Writing to stdin: {len(full_input)} characters")
                    
                    if self.use_pty:
                        # Write to PTY
                        os.write(self.master_fd, (full_input + "\n").encode('utf-8'))
                    else:
                        # Write to pipe
                        self.process.stdin.write(full_input + "\n")
                        self.process.stdin.flush()
                    
                    # Log session
                    self._log_interaction("input", user_input)
                    
                except queue.Empty:
                    continue
                    
        except Exception as e:
            self.logger.error(f"Input writer error: {e}")
        finally:
            self.logger.debug("Input writer thread ending")
    
    def send_input(self, text: str):
        """Send input to Claude."""
        self.input_queue.put(text)
    
    def get_output(self, timeout: float = 0.1) -> Optional[str]:
        """Get output from Claude (non-blocking)."""
        try:
            return self.output_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def _strip_ansi_codes(self, text: str) -> str:
        """Remove ANSI escape codes from text."""
        import re
        ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
        return ansi_escape.sub('', text)
    
    def _process_output_line(self, line: str):
        """Process a line of output from Claude."""
        # Ticket extraction removed from project
        
        # Extract agent delegations
        delegations = self.agent_delegator.extract_delegations(line)
        for delegation in delegations:
            if self.log_level != "OFF":
                self.logger.info(f"Detected delegation to {delegation['agent']}: {delegation['task']}")
        
        # Queue for display
        self.output_queue.put(line)
        
        # Log session
        self._log_interaction("output", line)
    
    def _log_interaction(self, interaction_type: str, content: str):
        """Log interaction for session history."""
        self.session_log.append({
            "type": interaction_type,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def stop(self):
        """Stop the orchestrated session."""
        self.logger.info("Stopping orchestrator")
        self.running = False
        
        # Terminate subprocess
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            
            self.logger.info(f"Claude subprocess terminated (exit code: {self.process.returncode})")
        
        # Clean up PTY
        if hasattr(self, 'use_pty') and self.use_pty and hasattr(self, 'master_fd'):
            try:
                os.close(self.master_fd)
            except:
                pass
        
        # Save session log
        self._save_session_log()
        
        # Ticket creation removed from project
    
    def _save_session_log(self):
        """Save session log to file."""
        try:
            log_dir = Path.home() / ".claude-mpm" / "sessions"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = self.session_start.strftime("%Y%m%d_%H%M%S")
            log_file = log_dir / f"session_{timestamp}.json"
            
            import json
            session_data = {
                "session_start": self.session_start.isoformat(),
                "session_end": datetime.now().isoformat(),
                "interactions": self.session_log,
                # Ticket extraction removed from project
            }
            
            with open(log_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            self.logger.info(f"Session log saved to: {log_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save session log: {e}")
    
    # _create_tickets method removed - TicketExtractor functionality removed from project
    
    def run_interactive(self):
        """Run an interactive session."""
        try:
            from claude_mpm._version import __version__
            print(f"Claude MPM v{__version__} - Interactive Session")
        except ImportError:
            print("Claude MPM Interactive Session")
        print("Type 'exit' or 'quit' to end session")
        print("-" * 50)
        
        # Use print mode for each interaction
        conversation_file = None
        
        while True:
            try:
                user_input = input("\nYou: ").strip()
                if user_input.lower() in ['exit', 'quit']:
                    break
                    
                if user_input:
                    # Prepare message with framework on first interaction
                    if self.first_interaction:
                        framework = self.framework_loader.get_framework_instructions()
                        full_message = framework + "\n\nUser: " + user_input
                        self.first_interaction = False
                    else:
                        full_message = user_input
                    
                    # Build command
                    cmd = [
                        "claude",
                        "--model", "opus", 
                        "--dangerously-skip-permissions",
                        "--print",  # Print mode
                        full_message
                    ]
                    
                    # Continue conversation if we have a file
                    if conversation_file:
                        cmd.extend(["--continue", str(conversation_file)])
                    
                    # Run Claude
                    print("\nClaude: ", end='', flush=True)
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    
                    if result.returncode == 0:
                        print(result.stdout)
                        
                        # Extract conversation file from stderr if mentioned
                        if "conversation saved to" in result.stderr.lower():
                            # Parse conversation file path
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
    
    def run_non_interactive(self, user_input: str):
        """
        Run a non-interactive session with given input.
        
        Args:
            user_input: The input to send to Claude
        """
        # Force non-PTY mode for non-interactive
        saved_use_pty = getattr(self, 'use_pty', False)
        self.use_pty = False
        
        if not self.start():
            return
        
        self.logger.info("Running in non-interactive mode")
        
        try:
            # Send input
            self.send_input(user_input)
            
            # Wait for process to complete or timeout
            import time
            timeout = 300  # 5 minute timeout
            start_time = time.time()
            
            # Collect output
            while self.running and self.process and self.process.poll() is None:
                if time.time() - start_time > timeout:
                    self.logger.warning("Session timeout reached")
                    break
                
                # Try to get output
                output = self.get_output(timeout=0.1)
                if output:
                    print(output)
                
        finally:
            self.use_pty = saved_use_pty
            self.stop()
    
    def _display_output(self):
        """Display output from Claude."""
        while self.running:
            output = self.get_output()
            if output:
                print(output)