"""Wrapper orchestrator that creates a custom Claude wrapper."""

import os
import tempfile
from pathlib import Path
from typing import Optional
from datetime import datetime
import logging

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


class WrapperOrchestrator:
    """Orchestrator that creates a wrapper script for Claude with framework."""
    
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
            self.logger.info(f"Initializing Wrapper Orchestrator (log_level={log_level})")
        else:
            # Minimal logger
            self.logger = get_logger("wrapper_orchestrator")
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
        """Run an interactive session with a custom wrapper."""
        print("Claude MPM Interactive Session")
        print("Creating framework-aware Claude wrapper...")
        print("-" * 50)
        
        # Get framework instructions
        framework = self.framework_loader.get_framework_instructions()
        
        # Create a wrapper script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            wrapper_script = f"""#!/bin/bash
# Claude MPM Wrapper Script
# This script ensures framework instructions are included in every conversation

# Check if this is the first message
if [ ! -f "$HOME/.claude-mpm/.framework_injected" ]; then
    # First message - prepend framework
    echo "Injecting framework instructions..."
    
    # Create the framework message
    FRAMEWORK_MSG=$(cat << 'EOF_FRAMEWORK'
{framework}

User: $@
EOF_FRAMEWORK
)
    
    # Mark as injected
    mkdir -p "$HOME/.claude-mpm"
    touch "$HOME/.claude-mpm/.framework_injected"
    
    # Run Claude with framework
    exec claude --model opus --dangerously-skip-permissions -p "$FRAMEWORK_MSG"
else
    # Subsequent messages - just pass through
    exec claude --model opus --dangerously-skip-permissions "$@"
fi
"""
            f.write(wrapper_script)
            wrapper_path = f.name
        
        try:
            # Make wrapper executable
            os.chmod(wrapper_path, 0o755)
            
            # Clean up any previous session marker
            marker_file = Path.home() / ".claude-mpm" / ".framework_injected"
            if marker_file.exists():
                marker_file.unlink()
            
            # Log wrapper creation
            if self.log_level != "OFF":
                self.logger.info(f"Created wrapper script: {wrapper_path}")
                
                # Save framework to prompts directory
                prompt_path = Path.home() / ".claude-mpm" / "prompts"
                prompt_path.mkdir(parents=True, exist_ok=True)
                prompt_file = prompt_path / f"prompt_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                prompt_file.write_text(framework)
                self.logger.info(f"Framework saved to: {prompt_file}")
            
            print("\nWrapper created. Starting Claude with framework context...")
            print("(Framework will be injected on your first message)")
            print()
            
            # Set CLAUDE_WRAPPER environment variable
            env = os.environ.copy()
            env['CLAUDE_WRAPPER'] = wrapper_path
            
            # Run Claude with our wrapper in PATH
            # Create a temporary directory for our wrapper
            with tempfile.TemporaryDirectory() as tmpdir:
                # Create symlink to wrapper as 'claude'
                wrapper_link = Path(tmpdir) / "claude"
                wrapper_link.symlink_to(wrapper_path)
                
                # Prepend our directory to PATH
                env['PATH'] = f"{tmpdir}:{env['PATH']}"
                
                # Run claude (which will use our wrapper)
                self.subprocess_runner.run(["claude"], env=env)
            
        finally:
            # Clean up
            try:
                os.unlink(wrapper_path)
            except:
                pass
            
            # Clean up marker file
            if marker_file.exists():
                marker_file.unlink()
            
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