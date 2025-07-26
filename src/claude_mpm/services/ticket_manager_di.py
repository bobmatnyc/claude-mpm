"""
Enhanced Ticket Manager with Dependency Injection support.

This version demonstrates proper constructor injection and testability.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from ..core.injectable_service import InjectableService
from ..core.config import Config
from ..core.logger import get_logger


class ITaskManagerAdapter:
    """Interface for task manager adapter."""
    
    def create_task(self, **kwargs) -> Any:
        """Create a task."""
        raise NotImplementedError
        
    def get_recent_tasks(self, limit: int) -> List[Any]:
        """Get recent tasks."""
        raise NotImplementedError
        
    def load_task(self, task_id: str) -> Any:
        """Load a specific task."""
        raise NotImplementedError


class AITrackdownAdapter(ITaskManagerAdapter):
    """Adapter for ai-trackdown-pytools."""
    
    def __init__(self, project_path: Path):
        """Initialize the adapter."""
        self.project_path = project_path
        self.logger = get_logger("ai_trackdown_adapter")
        self._task_manager = self._init_task_manager()
        
    def _init_task_manager(self):
        """Initialize ai-trackdown-pytools TaskManager."""
        try:
            from ai_trackdown_pytools.core.task import TaskManager
            from ai_trackdown_pytools import Config as TrackdownConfig, Project
            
            # Ensure tickets directory exists
            tickets_dir = self.project_path / "tickets"
            if not tickets_dir.exists():
                tickets_dir.mkdir(exist_ok=True)
                (tickets_dir / "epics").mkdir(exist_ok=True)
                (tickets_dir / "issues").mkdir(exist_ok=True)
                (tickets_dir / "tasks").mkdir(exist_ok=True)
                self.logger.info(f"Created tickets directory structure at: {tickets_dir}")
            
            # Configure ai-trackdown if needed
            config_file = self.project_path / ".trackdown.yaml"
            if not config_file.exists():
                config = TrackdownConfig.create_default(config_file)
                config.set("paths.tickets_dir", "tickets")
                config.set("paths.epics_dir", "tickets/epics")
                config.set("paths.issues_dir", "tickets/issues")
                config.set("paths.tasks_dir", "tickets/tasks")
                config.save()
                self.logger.info("Created .trackdown.yaml configuration")
            
            # Initialize task manager directly
            return TaskManager(self.project_path)
            
        except ImportError:
            self.logger.error("ai-trackdown-pytools not installed")
            return None
        except Exception as e:
            self.logger.error(f"Failed to initialize TaskManager: {e}")
            return None
            
    def create_task(self, **kwargs) -> Any:
        """Create a task."""
        if not self._task_manager:
            raise RuntimeError("Task manager not available")
        return self._task_manager.create_task(**kwargs)
        
    def get_recent_tasks(self, limit: int) -> List[Any]:
        """Get recent tasks."""
        if not self._task_manager:
            return []
        return self._task_manager.get_recent_tasks(limit=limit)
        
    def load_task(self, task_id: str) -> Any:
        """Load a specific task."""
        if not self._task_manager:
            raise RuntimeError("Task manager not available")
        return self._task_manager.load_task(task_id)


class TicketManagerDI(InjectableService):
    """
    Enhanced Ticket Manager with Dependency Injection.
    
    This version demonstrates:
    - Constructor injection of dependencies
    - Interface-based design for testability
    - Configuration injection
    - Easy mocking for tests
    """
    
    # Type annotations for dependency injection
    config: Config
    task_adapter: Optional[ITaskManagerAdapter]
    
    def __init__(
        self,
        name: str = "ticket_manager",
        config: Optional[Config] = None,
        task_adapter: Optional[ITaskManagerAdapter] = None,
        project_path: Optional[Path] = None,
        **kwargs
    ):
        """
        Initialize ticket manager with dependency injection.
        
        Args:
            name: Service name
            config: Configuration service (injected)
            task_adapter: Task manager adapter (injected)
            project_path: Project path override
            **kwargs: Additional arguments for base class
        """
        # Call parent constructor
        super().__init__(name=name, config=config, **kwargs)
        
        # Use injected adapter or create default
        if task_adapter:
            self.task_adapter = task_adapter
        else:
            # Get project path from config or parameter
            if project_path is None:
                project_path = Path(self.config.get('project.path', '.'))
            self.task_adapter = AITrackdownAdapter(project_path)
            
        self.logger.info(f"Initialized {name} with DI support")
        
    async def _initialize(self) -> None:
        """Initialize the service."""
        self.logger.info("TicketManager service initialized")
        
    async def _cleanup(self) -> None:
        """Cleanup service resources."""
        self.logger.info("TicketManager service cleaned up")
        
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
        Create a ticket.
        
        Args:
            title: Ticket title
            ticket_type: Type (task, bug, feature, etc.)
            description: Detailed description
            priority: Priority level
            tags: List of tags
            source: Source identifier
            **kwargs: Additional metadata
            
        Returns:
            Ticket ID if created, None on failure
        """
        if not self.task_adapter:
            self.logger.error("Task adapter not available")
            return None
            
        try:
            # Prepare tags
            if tags is None:
                tags = []
                
            # Add standard tags
            tags.extend([ticket_type, f"source:{source}", "auto-extracted"])
            tags = list(set(tags))  # Remove duplicates
            
            # Prepare task data
            task_data = {
                'title': title,
                'description': description or f"Auto-extracted {ticket_type}",
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
            
            # Add parent references if provided
            if parent_epic:
                task_data['metadata']['parent_epic'] = parent_epic
            if parent_issue:
                task_data['metadata']['parent_issue'] = parent_issue
                
            # Create the task
            task = self.task_adapter.create_task(**task_data)
            
            # Update metrics
            self.update_metrics(tickets_created=self._metrics.custom_metrics.get('tickets_created', 0) + 1)
            
            self.logger.info(f"Created ticket: {task.id} - {title}")
            return task.id
            
        except Exception as e:
            self.logger.error(f"Failed to create ticket: {e}")
            self.update_metrics(tickets_failed=self._metrics.custom_metrics.get('tickets_failed', 0) + 1)
            return None
            
    def list_recent_tickets(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        List recent tickets.
        
        Args:
            limit: Maximum number of tickets
            
        Returns:
            List of ticket summaries
        """
        if not self.task_adapter:
            return []
            
        try:
            tasks = self.task_adapter.get_recent_tasks(limit=limit)
            
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
        if not self.task_adapter:
            return None
            
        try:
            task = self.task_adapter.load_task(ticket_id)
            
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
            
    async def _health_check(self) -> Dict[str, bool]:
        """Perform custom health checks."""
        checks = {
            'task_adapter_available': self.task_adapter is not None,
        }
        
        # Check if we can access the ticket directory
        try:
            project_path = Path(self.config.get('project.path', '.'))
            tickets_dir = project_path / "tickets"
            checks['tickets_directory_accessible'] = tickets_dir.exists()
        except Exception:
            checks['tickets_directory_accessible'] = False
            
        return checks
        
    async def _collect_custom_metrics(self) -> None:
        """Collect custom metrics."""
        # Count tickets if possible
        try:
            if self.task_adapter:
                recent_tickets = self.task_adapter.get_recent_tasks(limit=100)
                self._metrics.custom_metrics['total_tickets'] = len(recent_tickets)
        except Exception as e:
            self.logger.warning(f"Failed to collect ticket metrics: {e}")