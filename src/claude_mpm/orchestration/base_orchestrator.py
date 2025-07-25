"""Base orchestrator class with common functionality."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

try:
    from ..core.logger import get_logger, setup_logging
    from ..core.framework_loader import FrameworkLoader
    from .ticket_extractor import TicketExtractor
    from .agent_delegator import AgentDelegator
except ImportError:
    from core.logger import get_logger, setup_logging
    from core.framework_loader import FrameworkLoader
    from orchestration.ticket_extractor import TicketExtractor
    from orchestration.agent_delegator import AgentDelegator


class BaseOrchestrator(ABC):
    """
    Abstract base class for all orchestrators.
    
    Provides common functionality:
    - Framework loading
    - Ticket extraction
    - Agent delegation
    - Hook service integration
    - Logging setup
    - Session management
    """
    
    def __init__(
        self,
        framework_path: Optional[Path] = None,
        agents_dir: Optional[Path] = None,
        log_level: str = "OFF",
        log_dir: Optional[Path] = None,
        hook_manager=None,
    ):
        """
        Initialize base orchestrator.
        
        Args:
            framework_path: Path to framework directory
            agents_dir: Custom agents directory
            log_level: Logging level (OFF, INFO, DEBUG)
            log_dir: Custom log directory
            hook_manager: Hook service manager instance
        """
        self.log_level = log_level
        self.log_dir = log_dir or (Path.home() / ".claude-mpm" / "logs")
        self.hook_manager = hook_manager
        
        # Set up logging
        if log_level != "OFF":
            self.logger = setup_logging(level=log_level, log_dir=log_dir)
            self.logger.info(f"Initializing {self.__class__.__name__} (log_level={log_level})")
            if hook_manager and hook_manager.is_available():
                self.logger.info(f"Hook service available on port {hook_manager.port}")
        else:
            self.logger = get_logger(self.__class__.__name__.lower())
            self.logger.setLevel(logging.WARNING)
        
        # Core components
        self.framework_loader = FrameworkLoader(framework_path, agents_dir)
        self.ticket_extractor = TicketExtractor()
        self.agent_delegator = AgentDelegator(self.framework_loader.agent_registry)
        
        # Session state
        self.session_start = datetime.now()
        self.session_log = []
        self.ticket_creation_enabled = True
        
        # Hook client
        self.hook_client = self._initialize_hook_client()
    
    def _initialize_hook_client(self):
        """Initialize hook client if available."""
        if not self.hook_manager or not self.hook_manager.is_available():
            return None
            
        try:
            hook_client = self.hook_manager.get_client()
            if hook_client:
                health = hook_client.health_check()
                if health.get('status') == 'healthy':
                    self.logger.info(f"Hook client initialized with {health.get('hook_count', 0)} hooks")
                    return hook_client
                else:
                    self.logger.warning("Hook service not healthy, disabling hooks")
        except Exception as e:
            self.logger.warning(f"Failed to initialize hook client: {e}")
        
        return None
    
    def log_interaction(self, interaction_type: str, content: str):
        """Log interaction for session history."""
        self.session_log.append({
            "type": interaction_type,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def get_framework_instructions(self) -> str:
        """Get framework instructions with hook processing."""
        framework = self.framework_loader.get_framework_instructions()
        
        # Process through pre-delegation hook if available
        if self.hook_client:
            try:
                hook_result = self.hook_client.execute_pre_delegation_hook(
                    prompt="Framework initialization",
                    agent_type="system",
                    framework_content=framework[:1000]  # Send preview
                )
                if hook_result.get('modified_prompt'):
                    self.logger.info("Framework modified by pre-delegation hook")
                    # In practice, we'd handle framework modification differently
            except Exception as e:
                self.logger.debug(f"Pre-delegation hook failed: {e}")
        
        return framework
    
    def save_session_log(self):
        """Save session log to file."""
        try:
            log_dir = Path.home() / ".claude-mpm" / "sessions"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            timestamp = self.session_start.strftime("%Y%m%d_%H%M%S")
            log_file = log_dir / f"session_{timestamp}.json"
            
            import json
            session_data = {
                "orchestrator": self.__class__.__name__,
                "session_start": self.session_start.isoformat(),
                "session_end": datetime.now().isoformat(),
                "interactions": self.session_log,
                "tickets_extracted": self.ticket_extractor.get_all_tickets(),
            }
            
            with open(log_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            self.logger.info(f"Session log saved to: {log_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save session log: {e}")
    
    def create_tickets(self):
        """Create tickets using ticket manager."""
        if not self.ticket_creation_enabled:
            self.logger.info("Ticket creation disabled")
            return
            
        tickets = self.ticket_extractor.get_all_tickets()
        if not tickets:
            self.logger.info("No tickets to create")
            return
        
        try:
            from ..services.ticket_manager import TicketManager
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
                    self.logger.info(f"Created ticket: {ticket_id} - {ticket['title']}")
                except Exception as e:
                    self.logger.error(f"Failed to create ticket '{ticket['title']}': {e}")
            
            self.logger.info(f"Created {created_count}/{len(tickets)} tickets")
            
        except ImportError:
            self.logger.warning("TicketManager not available, skipping ticket creation")
        except Exception as e:
            self.logger.error(f"Error creating tickets: {e}")
    
    def process_output_line(self, line: str):
        """Process a line of output from Claude."""
        # Extract tickets
        tickets = self.ticket_extractor.extract_from_line(line)
        for ticket in tickets:
            if self.log_level != "OFF":
                self.logger.info(f"Extracted ticket: {ticket['type']} - {ticket['title']}")
        
        # Extract agent delegations
        delegations = self.agent_delegator.extract_delegations(line)
        for delegation in delegations:
            if self.log_level != "OFF":
                self.logger.info(f"Detected delegation to {delegation['agent']}: {delegation['task']}")
        
        # Process through hooks if available
        if self.hook_client:
            try:
                hook_result = self.hook_client.execute_ticket_extraction_hook(
                    line=line,
                    tickets_found=len(tickets),
                    delegations_found=len(delegations)
                )
                # Could modify behavior based on hook result
            except Exception as e:
                self.logger.debug(f"Ticket extraction hook failed: {e}")
        
        return {
            "tickets": tickets,
            "delegations": delegations
        }
    
    def cleanup(self):
        """Cleanup resources and save session data."""
        self.save_session_log()
        self.create_tickets()
        
        # Execute submit hook if available
        if self.hook_client:
            try:
                self.hook_client.execute_submit_hook(
                    session_type=self.__class__.__name__,
                    duration=(datetime.now() - self.session_start).total_seconds(),
                    tickets_created=len(self.ticket_extractor.get_all_tickets())
                )
            except Exception as e:
                self.logger.debug(f"Submit hook failed: {e}")
    
    @abstractmethod
    def run_interactive(self):
        """Run an interactive session."""
        pass
    
    @abstractmethod
    def run_non_interactive(self, user_input: str):
        """Run a non-interactive session with given input."""
        pass