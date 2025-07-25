"""Simplified Claude runner replacing the complex orchestrator system."""

import subprocess
import sys
from pathlib import Path
from typing import Optional

try:
    from ..services.agent_deployment import AgentDeploymentService
    from ..services.ticket_manager import TicketManager
    from .logger import get_logger
except ImportError:
    from claude_mpm.services.agent_deployment import AgentDeploymentService
    from claude_mpm.services.ticket_manager import TicketManager
    from claude_mpm.core.logger import get_logger


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
        log_level: str = "OFF"
    ):
        """Initialize the simple runner."""
        self.enable_tickets = enable_tickets
        self.logger = get_logger("simple_runner")
        
        # Initialize services
        self.deployment_service = AgentDeploymentService()
        if enable_tickets:
            try:
                self.ticket_manager = TicketManager()
            except (ImportError, TypeError, Exception) as e:
                self.logger.warning(f"Ticket manager not available: {e}")
                self.ticket_manager = None
                self.enable_tickets = False
    
    def setup_agents(self) -> bool:
        """Deploy native agents to .claude/agents/."""
        try:
            results = self.deployment_service.deploy_agents()
            
            if results["deployed"] or results.get("updated", []):
                deployed_count = len(results['deployed'])
                updated_count = len(results.get('updated', []))
                
                if deployed_count > 0:
                    print(f"✓ Deployed {deployed_count} native agents")
                if updated_count > 0:
                    print(f"✓ Updated {updated_count} agents")
                    
                # Set Claude environment
                self.deployment_service.set_claude_environment()
                return True
            else:
                self.logger.info("All agents already up to date")
                return True
                
        except Exception as e:
            self.logger.error(f"Agent deployment failed: {e}")
            print(f"⚠️  Agent deployment failed: {e}")
            return False
    
    def run_interactive(self, initial_context: Optional[str] = None):
        """Run Claude in interactive mode."""
        print("Claude MPM - Interactive Session")
        print("-" * 40)
        
        # Setup agents
        if not self.setup_agents():
            print("Continuing without native agents...")
        
        # Build command
        cmd = [
            "claude",
            "--model", "opus", 
            "--dangerously-skip-permissions"
        ]
        
        # If we have initial context, send it first
        if initial_context:
            print("Loading initial context...")
            init_cmd = cmd + ["--print", initial_context]
            try:
                result = subprocess.run(init_cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    print("Context loaded. Starting interactive session...")
                    print("-" * 40)
                else:
                    print(f"Warning: Context loading failed: {result.stderr}")
            except Exception as e:
                print(f"Warning: Context loading failed: {e}")
        
        # Run interactive Claude
        try:
            # For interactive mode, we need to let Claude inherit our terminal I/O
            subprocess.run(cmd, stdin=None, stdout=None, stderr=None)
        except KeyboardInterrupt:
            print("\nSession ended by user")
        except Exception as e:
            print(f"Error: {e}")
    
    def run_oneshot(self, prompt: str, context: Optional[str] = None) -> bool:
        """Run Claude with a single prompt and return success status."""
        # Setup agents
        if not self.setup_agents():
            print("Continuing without native agents...")
        
        # Combine context and prompt
        full_prompt = prompt
        if context:
            full_prompt = f"{context}\n\n{prompt}"
        
        # Build command
        cmd = [
            "claude",
            "--model", "opus",
            "--dangerously-skip-permissions", 
            "--print",
            full_prompt
        ]
        
        try:
            # Run Claude
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                response = result.stdout.strip()
                print(response)
                
                # Extract tickets if enabled
                if self.enable_tickets and self.ticket_manager and response:
                    self._extract_tickets(response)
                
                return True
            else:
                print(f"Error: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Error: {e}")
            return False
    
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