"""Simplified Claude runner replacing the complex orchestrator system."""

import subprocess
import sys
from pathlib import Path
from typing import Optional

try:
    from claude_mpm.services.agent_deployment import AgentDeploymentService
    from claude_mpm.services.ticket_manager import TicketManager
    from claude_mpm.core.logger import get_logger
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
        
        # Load system instructions
        self.system_instructions = self._load_system_instructions()
    
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
        
        if initial_context:
            print("🚀 Claude MPM Framework Ready!")
            print("")
            print("📋 Specialized Agents Deployed:")
            print("  - engineer: Coding, implementation, technical tasks")
            print("  - qa: Testing, validation, quality assurance")  
            print("  - documentation: Docs, guides, explanations")
            print("  - research: Investigation and analysis")
            print("  - security: Security-related tasks")
            print("  - ops: Deployment and infrastructure")
            print("  - version_control: Git and version management")
            print("  - data_engineer: Data processing and APIs")
            print("")
            print("💡 Usage:")
            print("  • Type '/agents' to see all available agents") 
            print("  • Use 'Task(description=\"task here\", subagent_type=\"agent_name\")'")
            print("  • Or delegate naturally: 'Please have the engineer review this code'")
            print("")
            print("Starting Claude...")
        
        print("-" * 40)
        
        # Build command with system instructions
        cmd = [
            "claude",
            "--model", "opus", 
            "--dangerously-skip-permissions"
        ]
        
        # Add system instructions if available
        system_prompt = self._create_system_prompt()
        if system_prompt and system_prompt != create_simple_context():
            cmd.extend(["--append-system-prompt", system_prompt])
        
        # Run interactive Claude directly
        try:
            # Use execvp to replace the current process with Claude
            # This should avoid any subprocess issues
            import os
            
            # Clean environment
            clean_env = os.environ.copy()
            claude_vars_to_remove = [
                'CLAUDE_CODE_ENTRYPOINT', 'CLAUDECODE', 'CLAUDE_CONFIG_DIR',
                'CLAUDE_MAX_PARALLEL_SUBAGENTS', 'CLAUDE_TIMEOUT'
            ]
            for var in claude_vars_to_remove:
                clean_env.pop(var, None)
            
            print("Launching Claude...")
            
            # Replace current process with Claude
            os.execvpe(cmd[0], cmd, clean_env)
            
        except Exception as e:
            print(f"Failed to launch Claude: {e}")
            # Fallback to subprocess
            try:
                subprocess.run(cmd, stdin=None, stdout=None, stderr=None)
            except Exception as fallback_error:
                print(f"Fallback also failed: {fallback_error}")
    
    def run_oneshot(self, prompt: str, context: Optional[str] = None) -> bool:
        """Run Claude with a single prompt and return success status."""
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
            "--dangerously-skip-permissions", 
            "--print",
            full_prompt
        ]
        
        # Add system instructions if available
        system_prompt = self._create_system_prompt()
        if system_prompt and system_prompt != create_simple_context():
            # Insert system prompt before the user prompt
            cmd.insert(-1, "--append-system-prompt")
            cmd.insert(-1, system_prompt)
        
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