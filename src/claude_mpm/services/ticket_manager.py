"""Ticket management using ai-trackdown-pytools."""

from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    from ..core.logger import get_logger
except ImportError:
    from core.logger import get_logger


class TicketManager:
    """
    Manage ticket creation using ai-trackdown-pytools.
    
    This wraps the ai-trackdown-pytools API for creating tickets
    in the standard tickets/ directory structure.
    """
    
    def __init__(self, project_path: Optional[Path] = None):
        """
        Initialize ticket manager.
        
        Args:
            project_path: Project root (defaults to current directory)
        """
        self.logger = get_logger("ticket_manager")
        self.project_path = project_path or Path.cwd()
        self.task_manager = self._init_task_manager()
        
    def _init_task_manager(self):
        """Initialize ai-trackdown-pytools TaskManager."""
        try:
            from ai_trackdown_pytools.core.task import TaskManager
            from ai_trackdown_pytools import Config, Project
            
            # First, ensure tickets directory exists
            tickets_dir = self.project_path / "tickets"
            if not tickets_dir.exists():
                tickets_dir.mkdir(exist_ok=True)
                (tickets_dir / "epics").mkdir(exist_ok=True)
                (tickets_dir / "issues").mkdir(exist_ok=True)
                (tickets_dir / "tasks").mkdir(exist_ok=True)
                self.logger.info(f"Created tickets directory structure at: {tickets_dir}")
            
            # Check if we need to configure ai-trackdown
            config_file = self.project_path / ".trackdown.yaml"
            if not config_file.exists():
                # Create default config that uses tickets/ directory
                config = Config.create_default(config_file)
                config.set("paths.tickets_dir", "tickets")
                config.set("paths.epics_dir", "tickets/epics")
                config.set("paths.issues_dir", "tickets/issues")
                config.set("paths.tasks_dir", "tickets/tasks")
                config.save()
                self.logger.info("Created .trackdown.yaml configuration")
            
            # Initialize TaskManager directly with the project path
            # TaskManager will handle project initialization internally
            task_manager = TaskManager(self.project_path)
            
            # Verify it's using the right directory
            if hasattr(task_manager, 'tasks_dir'):
                self.logger.info(f"TaskManager using tasks directory: {task_manager.tasks_dir}")
            else:
                self.logger.info(f"Initialized TaskManager for: {self.project_path}")
            
            return task_manager
            
        except ImportError:
            self.logger.error("ai-trackdown-pytools not installed")
            self.logger.info("Install with: pip install ai-trackdown-pytools")
            return None
        except Exception as e:
            self.logger.error(f"Failed to initialize TaskManager: {e}")
            self.logger.debug(f"Error details: {str(e)}", exc_info=True)
            return None
    
    def create_ticket(
        self,
        title: str,
        ticket_type: str = "task",
        description: str = "",
        priority: str = "medium",
        tags: Optional[List[str]] = None,
        source: str = "claude-mpm",
        parent_epic: Optional[str] = None,
        parent_issue: Optional[str] = None,
        **kwargs
    ) -> Optional[str]:
        """
        Create a ticket using ai-trackdown-pytools.
        
        Args:
            title: Ticket title
            ticket_type: Type (task, bug, feature, etc.)
            description: Detailed description
            priority: Priority level (low, medium, high)
            tags: List of tags/labels
            source: Source identifier
            **kwargs: Additional metadata
            
        Returns:
            Ticket ID if created, None on failure
        """
        if not self.task_manager:
            self.logger.error("TaskManager not available")
            return None
        
        try:
            # Prepare tags
            if tags is None:
                tags = []
            
            # Add type and source tags
            tags.extend([ticket_type, f"source:{source}", "auto-extracted"])
            
            # Remove duplicates
            tags = list(set(tags))
            
            # Prepare task data
            task_data = {
                'title': title,
                'description': description or f"Auto-extracted {ticket_type} from Claude MPM session",
                'status': 'open',
                'priority': priority.lower(),
                'assignees': [],
                'tags': tags,
                'metadata': {
                    'source': source,
                    'ticket_type': ticket_type,
                    'created_by': 'claude-mpm',
                    'extracted_at': datetime.now().isoformat(),
                    **kwargs
                }
            }
            
            # Create the task
            task = self.task_manager.create_task(**task_data)
            
            self.logger.info(f"Created ticket: {task.id} - {title}")
            return task.id
            
        except Exception as e:
            self.logger.error(f"Failed to create ticket: {e}")
            return None
    
    def list_recent_tickets(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List recent tickets.
        
        Args:
            limit: Maximum number of tickets to return
            
        Returns:
            List of ticket summaries
        """
        if not self.task_manager:
            return []
        
        try:
            tasks = self.task_manager.get_recent_tasks(limit=limit)
            
            tickets = []
            for task in tasks:
                tickets.append({
                    'id': task.id,
                    'title': task.title,
                    'status': task.status,
                    'priority': task.priority,
                    'tags': task.tags,
                    'created_at': task.created_at,
                })
            
            return tickets
            
        except Exception as e:
            self.logger.error(f"Failed to list tickets: {e}")
            return []
    
    def get_ticket(self, ticket_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific ticket.
        
        Args:
            ticket_id: Ticket ID
            
        Returns:
            Ticket data or None
        """
        if not self.task_manager:
            return None
        
        try:
            task = self.task_manager.load_task(ticket_id)
            
            return {
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'status': task.status,
                'priority': task.priority,
                'tags': task.tags,
                'assignees': task.assignees,
                'created_at': task.created_at,
                'updated_at': task.updated_at,
                'metadata': task.metadata,
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get ticket {ticket_id}: {e}")
            return None