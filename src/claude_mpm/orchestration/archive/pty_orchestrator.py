"""Orchestrator using built-in pty module for terminal interaction."""

import os
import pty
import select
import subprocess
import sys
import termios
import tty
from pathlib import Path
from typing import Optional
from datetime import datetime
import logging
import threading
import fcntl

try:
    from ..core.logger import get_logger, setup_logging
    from ..utils.subprocess_runner import SubprocessRunner, OutputMode
    # TicketExtractor removed from project
    from ..core.framework_loader import FrameworkLoader
    from .agent_delegator import AgentDelegator
except ImportError:
    from core.logger import get_logger, setup_logging
    from utils.subprocess_runner import SubprocessRunner, OutputMode
    # TicketExtractor removed from project
    from core.framework_loader import FrameworkLoader
    from orchestration.agent_delegator import AgentDelegator


class PTYOrchestrator:
    """Orchestrator using built-in pty module for proper terminal control."""
    
    def __init__(
        self,
        framework_path: Optional[Path] = None,
        agents_dir: Optional[Path] = None,
        log_level: str = "OFF",
        log_dir: Optional[Path] = None,
    ):
        """Initialize the orchestrator."""
        self.log_level = log_level
        self.log_dir = log_dir or (Path.home() / ".claude-mpm" / "logs")
        
        # Set up logging
        if log_level != "OFF":
            self.logger = setup_logging(level=log_level, log_dir=log_dir)
            self.logger.info(f"Initializing PTY Orchestrator (log_level={log_level})")
        else:
            # Minimal logger
            self.logger = get_logger("pty_orchestrator")
            self.logger.setLevel(logging.WARNING)
        
        # Components
        self.framework_loader = FrameworkLoader(framework_path, agents_dir)
        # TicketExtractor removed from project
        self.agent_delegator = AgentDelegator(self.framework_loader.agent_registry)
        
        # State
        self.first_interaction = True
        self.session_start = datetime.now()
        self.session_log = []
        # Ticket creation removed from project
        self.process = None
        self.master_fd = None
        
        # Initialize subprocess runner
        self.subprocess_runner = SubprocessRunner(logger=self.logger)
        
    def run_interactive(self):
        """Run an interactive session using pty."""
        print("Claude MPM Interactive Session")
        print("Type 'exit' or 'quit' to end session")
        print("-" * 50)
        
        # Save terminal settings
        old_tty = termios.tcgetattr(sys.stdin)
        
        try:
            # Create a pseudo-terminal
            master, slave = pty.openpty()
            self.master_fd = master
            
            # Start Claude process
            self.logger.info("Starting Claude with pty")
            self.process = subprocess.Popen(
                ['claude', '--model', 'opus', '--dangerously-skip-permissions'],
                stdin=slave,
                stdout=slave,
                stderr=slave,
                preexec_fn=os.setsid
            )
            
            # Close slave fd in parent
            os.close(slave)
            
            # Set non-blocking
            fcntl.fcntl(master, fcntl.F_SETFL, os.O_NONBLOCK)
            
            # Put terminal in raw mode
            tty.setraw(sys.stdin.fileno())
            
            # Framework injection flag
            framework_injected = False
            framework_buffer = []
            
            # I/O loop
            while True:
                try:
                    # Check if process is still alive
                    if self.process.poll() is not None:
                        break
                    
                    # Use select to check for available data
                    r, w, e = select.select([sys.stdin, master], [], [], 0.1)
                    
                    # Handle input from user
                    if sys.stdin in r:
                        data = os.read(sys.stdin.fileno(), 1024)
                        
                        # Check for exit
                        if data == b'\x03' or data == b'\x04':  # Ctrl+C or Ctrl+D
                            break
                        
                        # Inject framework on first real input (after initial Claude startup)
                        if not framework_injected and data.strip() and not data.startswith(b'\x1b'):
                            self.logger.info("Injecting framework instructions")
                            framework = self.framework_loader.get_framework_instructions()
                            
                            # Save prompt if debugging
                            if self.log_level == "DEBUG":
                                prompt_path = Path.home() / ".claude-mpm" / "prompts"
                                prompt_path.mkdir(parents=True, exist_ok=True)
                                prompt_file = prompt_path / f"prompt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                                prompt_file.write_text(framework)
                                self.logger.debug(f"Framework saved to: {prompt_file}")
                            
                            # Send framework first
                            os.write(master, framework.encode('utf-8') + b'\n')
                            framework_injected = True
                            
                            # Then send user input
                            os.write(master, data)
                        else:
                            # Normal input
                            os.write(master, data)
                    
                    # Handle output from Claude
                    if master in r:
                        try:
                            data = os.read(master, 1024)
                            if data:
                                # Write to stdout
                                sys.stdout.write(data.decode('utf-8', errors='replace'))
                                sys.stdout.flush()
                                
                                # Process for tickets
                                text = data.decode('utf-8', errors='replace')
                                for line in text.split('\n'):
                                    # Ticket extraction removed from project
                                    
                                    # Extract agent delegations
                                    delegations = self.agent_delegator.extract_delegations(line)
                                    for delegation in delegations:
                                        if self.log_level != "OFF":
                                            self.logger.info(f"Detected delegation to {delegation['agent']}: {delegation['task']}")
                        except OSError:
                            # No data available
                            pass
                            
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    self.logger.error(f"Error in I/O loop: {e}")
                    break
                    
        finally:
            # Restore terminal settings
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_tty)
            
            # Clean up
            self.stop()
    
    def stop(self):
        """Stop the orchestrated session."""
        self.logger.info("Stopping PTY orchestrator")
        
        # Terminate process
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except:
                self.process.kill()
                self.process.wait()
        
        # Close master fd
        if self.master_fd:
            try:
                os.close(self.master_fd)
            except:
                pass
        
        # Save session log
        self._save_session_log()
        
        # Ticket creation removed from project
        
        print("\n\nSession ended")
    
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
            
            if self.log_level != "OFF":
                self.logger.info(f"Session log saved to: {log_file}")
                
        except Exception as e:
            self.logger.error(f"Failed to save session log: {e}")
    
    # _create_tickets method removed - TicketExtractor functionality removed from project
    
    def run_non_interactive(self, user_input: str):
        """Run a non-interactive session using print mode."""
        # For non-interactive, fall back to simple print mode
        try:
            # Prepare message with framework
            framework = self.framework_loader.get_framework_instructions()
            full_message = framework + "\n\nUser: " + user_input
            
            # Build command
            cmd = [
                "claude",
                "--model", "opus",
                "--dangerously-skip-permissions",
                "--print",  # Print mode
                full_message
            ]
            
            # Run Claude
            result = self.subprocess_runner.run(cmd)
            
            if result.success:
                print(result.stdout)
                
                # Ticket extraction removed from project
            else:
                print(f"Error: {result.stderr}")
                
            # Ticket creation removed from project
                
        except Exception as e:
            print(f"Error: {e}")
            self.logger.error(f"Non-interactive error: {e}")