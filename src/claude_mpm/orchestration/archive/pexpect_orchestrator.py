"""Orchestrator using pexpect for proper terminal interaction."""

import pexpect
import sys
import os
from pathlib import Path
from typing import Optional
from datetime import datetime
import logging

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


class PexpectOrchestrator:
    """Orchestrator using pexpect for proper terminal control."""
    
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
            self.logger.info(f"Initializing Pexpect Orchestrator (log_level={log_level})")
        else:
            # Minimal logger
            self.logger = get_logger("pexpect_orchestrator")
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
        self.child = None
        
    def run_interactive(self):
        """Run an interactive session using pexpect."""
        print("Claude MPM Interactive Session (Terminal Mode)")
        print("Type '/exit' to end session")
        print("-" * 50)
        
        try:
            # Start Claude with pexpect
            self.logger.info("Starting Claude with pexpect")
            self.child = pexpect.spawn(
                'claude',
                ['--model', 'opus', '--dangerously-skip-permissions'],
                encoding='utf-8',
                timeout=None,
                dimensions=(24, 80)  # Standard terminal size
            )
            
            # Set up logging if needed
            if self.log_level == "DEBUG":
                log_file = open(self.log_dir / f"pexpect_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log", 'w')
                self.child.logfile = log_file
            
            # Wait for Claude to be ready
            self.logger.info("Waiting for Claude prompt")
            self.child.expect('>', timeout=10)
            
            # First interaction - inject framework
            if self.first_interaction:
                self.logger.info("Injecting framework instructions")
                framework = self.framework_loader.get_framework_instructions()
                
                # Save prompt if debugging
                if self.log_level == "DEBUG":
                    prompt_path = Path.home() / ".claude-mpm" / "prompts"
                    prompt_path.mkdir(parents=True, exist_ok=True)
                    prompt_file = prompt_path / f"prompt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                    prompt_file.write_text(framework)
                    self.logger.debug(f"Framework saved to: {prompt_file}")
                
                # Send framework
                self.child.sendline(framework)
                self.child.expect('>', timeout=60)  # Give more time for framework processing
                self.first_interaction = False
                
                # Clear the screen after framework injection
                print("\033[2J\033[H")  # Clear screen and move cursor to top
                print("Claude MPM Interactive Session")
                print("Type '/exit' to end session")
                print("-" * 50)
            
            # Interactive loop
            while True:
                try:
                    # Get user input
                    user_input = input("\nYou: ")
                    
                    # Check for exit
                    if user_input.strip().lower() in ['/exit', 'exit', 'quit']:
                        break
                    
                    # Send to Claude
                    self.child.sendline(user_input)
                    
                    # Capture response
                    print("\nClaude: ", end='', flush=True)
                    self.child.expect('>', timeout=120)  # 2 minute timeout for responses
                    
                    # Get the response (everything before the prompt)
                    response = self.child.before
                    
                    # Process response for tickets
                    for line in response.split('\n'):
                        # Ticket extraction removed from project
                        
                        # Extract agent delegations
                        delegations = self.agent_delegator.extract_delegations(line)
                        for delegation in delegations:
                            if self.log_level != "OFF":
                                self.logger.info(f"Detected delegation to {delegation['agent']}: {delegation['task']}")
                    
                    # Display response
                    print(response)
                    
                    # Log interaction
                    self._log_interaction("input", user_input)
                    self._log_interaction("output", response)
                    
                except pexpect.TIMEOUT:
                    print("\n[Timeout waiting for response]")
                    self.logger.warning("Response timeout")
                except KeyboardInterrupt:
                    print("\n[Interrupted]")
                    break
                except Exception as e:
                    print(f"\n[Error: {e}]")
                    self.logger.error(f"Interaction error: {e}")
                    
        except Exception as e:
            print(f"\nFailed to start Claude: {e}")
            self.logger.error(f"Failed to start Claude: {e}")
        finally:
            self.stop()
    
    def _log_interaction(self, interaction_type: str, content: str):
        """Log interaction for session history."""
        self.session_log.append({
            "type": interaction_type,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def stop(self):
        """Stop the orchestrated session."""
        self.logger.info("Stopping pexpect orchestrator")
        
        # Close pexpect child
        if self.child:
            try:
                self.child.sendline('/exit')
                self.child.expect(pexpect.EOF, timeout=5)
            except:
                pass
            finally:
                self.child.close()
                
        # Save session log
        self._save_session_log()
        
        # Create tickets
        # Ticket creation removed from project
        
        print("\nSession ended")
    
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
            import subprocess
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(result.stdout)
                
                # Ticket extraction removed from project
            else:
                print(f"Error: {result.stderr}")
                
            # Create tickets
            # Ticket creation removed from project
                
        except Exception as e:
            print(f"Error: {e}")
            self.logger.error(f"Non-interactive error: {e}")