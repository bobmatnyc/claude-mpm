"""Direct orchestrator that runs Claude with minimal intervention."""

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
except ImportError:
    from core.logger import get_logger, setup_logging
    from utils.subprocess_runner import SubprocessRunner
    # TicketExtractor removed from project
    from core.framework_loader import FrameworkLoader
    from orchestration.agent_delegator import AgentDelegator


class DirectOrchestrator:
    """Orchestrator that runs Claude directly with framework injection via file."""
    
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
            self.logger.info(f"Initializing Direct Orchestrator (log_level={log_level})")
        else:
            # Minimal logger
            self.logger = get_logger("direct_orchestrator")
            self.logger.setLevel(logging.WARNING)
        
        # Components
        self.framework_loader = FrameworkLoader(framework_path, agents_dir)
        # TicketExtractor removed from project
        self.agent_delegator = AgentDelegator(self.framework_loader.agent_registry)
        
        # State
        self.session_start = datetime.now()
        # Ticket creation removed from project
        
        # Initialize subprocess runner
        self.subprocess_runner = SubprocessRunner(logger=self.logger)
        
    def run_interactive(self):
        """Run an interactive session by launching Claude directly."""
        print("Claude MPM Interactive Session")
        print("Framework will be injected on first interaction")
        print("-" * 50)
        
        # Get framework instructions
        framework = self.framework_loader.get_framework_instructions()
        
        # Save framework to a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(framework)
            f.write("\n\nNOTE: This is the claude-mpm framework. Please acknowledge you've received these instructions and then we can begin our session.\n")
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
            
            # Read the framework content
            with open(framework_file, 'r') as f:
                framework_content = f.read()
            
            # Generate a unique session ID
            import uuid
            session_id = str(uuid.uuid4())
            
            # Build command to start Claude with print mode and session ID
            cmd = [
                "claude",
                "--model", "opus",
                "--dangerously-skip-permissions",
                "--session-id", session_id,
                "--print",  # Print mode
                framework_content
            ]
            
            self.logger.info(f"Starting Claude with framework injection (session: {session_id})")
            
            # Run Claude with framework
            print("\nInjecting framework instructions...")
            result = self.subprocess_runner.run(cmd)
            
            if result.success:
                print("\nFramework injected. Claude's response:")
                print("-" * 50)
                print(result.stdout)
                print("-" * 50)
                
                # Debug: show stderr if logging is enabled
                if self.log_level != "OFF" and result.stderr:
                    self.logger.debug(f"Claude stderr: {result.stderr}")
                
                # Check if we can find the conversation file
                # Parse stderr for conversation file location
                conversation_file = None
                if result.stderr:
                    import re
                    # Look for patterns like "Conversation saved to: /path/to/file"
                    match = re.search(r'(?:conversation saved to|saved to)[:\s]+([^\s]+)', result.stderr, re.I)
                    if match:
                        conversation_file = match.group(1).strip()
                        self.logger.info(f"Found conversation file: {conversation_file}")
                
                # Now start interactive Claude session with same session ID
                print("\nStarting interactive session...")
                interactive_cmd = [
                    "claude",
                    "--model", "opus",
                    "--dangerously-skip-permissions"
                ]
                
                # Try to continue the conversation
                if conversation_file and Path(conversation_file).exists():
                    interactive_cmd.extend(["--continue", conversation_file])
                    print(f"Continuing conversation from: {conversation_file}")
                elif session_id:
                    interactive_cmd.extend(["--session-id", session_id])
                    print(f"Using session ID: {session_id}")
                
                # Run Claude interactively
                self.subprocess_runner.run(interactive_cmd)
            else:
                print(f"Error injecting framework: {result.stderr}")
            
            self.logger.info(f"Claude exited with code: {result.returncode}")
            
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