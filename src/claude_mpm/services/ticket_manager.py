"""Ticket management using ai-trackdown-pytools."""

from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from claude_mpm.core.logging_config import get_logger

from ..core.interfaces import TicketManagerInterface


class TicketManager(TicketManagerInterface):
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
        self.logger = get_logger(__name__)
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
            
            # Use standardized config format (.trackdown.yaml)
            config_file = self.project_path / ".trackdown.yaml"
            
            # Check if config exists, create if needed
            if not config_file.exists():
                try:
                    config = Config.create_default(config_file)  # Pass Path object directly
                    config.set("paths.tickets_dir", "tickets")
                    config.set("paths.epics_dir", "tickets/epics")
                    config.set("paths.issues_dir", "tickets/issues")
                    config.set("paths.tasks_dir", "tickets/tasks")
                    config.save()
                    self.logger.info("Created .trackdown.yaml configuration")
                except Exception as config_error:
                    self.logger.warning(f"Could not create config file: {config_error}")
                    self.logger.info("Proceeding without config file - using defaults")
            else:
                self.logger.info(f"Using configuration from: {config_file}")
            
            # Initialize TaskManager directly with the project path
            # TaskManager will handle project initialization internally
            task_manager = TaskManager(self.project_path)  # Pass Path object directly
            
            # Verify it's using the right directory
            if hasattr(task_manager, 'tasks_dir'):
                self.logger.info(f"TaskManager using tasks directory: {task_manager.tasks_dir}")
            else:
                self.logger.info(f"Initialized TaskManager for: {self.project_path}")
            
            return task_manager
            
        except ImportError as e:
            import_msg = str(e)
            if "ai_trackdown_pytools" in import_msg.lower():
                self.logger.error("ai-trackdown-pytools is not installed")
                self.logger.info("Install with: pip install ai-trackdown-pytools")
            else:
                self.logger.error(f"Missing dependency: {import_msg}")
                self.logger.info("Ensure all required packages are installed")
            self.logger.debug(f"Import error details: {import_msg}")
            return None
        except AttributeError as e:
            attr_msg = str(e)
            if "TaskManager" in attr_msg:
                self.logger.error("TaskManager class not found in ai-trackdown-pytools")
                self.logger.info("This may indicate an incompatible version")
            else:
                self.logger.error(f"ai-trackdown-pytools API mismatch: {attr_msg}")
            self.logger.info("Try updating: pip install --upgrade ai-trackdown-pytools")
            return None
        except FileNotFoundError as e:
            self.logger.error(f"Required file or directory not found: {e}")
            self.logger.info("Ensure the project directory exists and is accessible")
            return None
        except PermissionError as e:
            self.logger.error(f"Permission denied accessing ticket files: {e}")
            self.logger.info("Check file permissions in the tickets/ directory")
            self.logger.info("You may need to run with appropriate permissions")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error initializing TaskManager: {e.__class__.__name__}: {e}")
            self.logger.info("This could be due to:")
            self.logger.info("  - Corrupted configuration files")
            self.logger.info("  - Incompatible ai-trackdown-pytools version")
            self.logger.info("  - Missing dependencies")
            self.logger.debug(f"Full error details:", exc_info=True)
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
            priority: Priority level (low, medium, high, critical)
            tags: List of tags/labels
            source: Source identifier
            parent_epic: Parent epic ID (optional)
            parent_issue: Parent issue ID (optional)
            **kwargs: Additional metadata
            
        Returns:
            Ticket ID if created, None on failure
        """
        if not self.task_manager:
            self.logger.error("TaskManager not available - cannot create ticket")
            self.logger.info("Please ensure ai-trackdown-pytools is installed and properly configured")
            self.logger.info("Run: pip install ai-trackdown-pytools")
            return None
        
        try:
            # Validate input
            if not title or not title.strip():
                self.logger.error("Cannot create ticket with empty title")
                return None
            
            # Validate priority
            valid_priorities = ['low', 'medium', 'high', 'critical']
            if priority.lower() not in valid_priorities:
                self.logger.warning(f"Invalid priority '{priority}', using 'medium'")
                self.logger.info(f"Valid priorities are: {', '.join(valid_priorities)}")
                priority = 'medium'
            
            # Validate ticket type
            valid_types = ['task', 'bug', 'feature', 'issue', 'enhancement', 'documentation']
            if ticket_type.lower() not in valid_types:
                self.logger.warning(f"Non-standard ticket type '{ticket_type}'")
                self.logger.info(f"Common types are: {', '.join(valid_types)}")
            
            # Prepare tags
            if tags is None:
                tags = []
            
            # Add type and source tags
            tags.extend([ticket_type, f"source:{source}", "auto-extracted"])
            
            # Remove duplicates
            tags = list(set(tags))
            
            # Prepare task data
            task_data = {
                'title': title.strip(),
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
            
            # Add parent references if provided
            if parent_epic:
                task_data['metadata']['parent_epic'] = parent_epic
                self.logger.debug(f"Linking to parent epic: {parent_epic}")
            if parent_issue:
                task_data['metadata']['parent_issue'] = parent_issue
                self.logger.debug(f"Linking to parent issue: {parent_issue}")
            
            # Create the task
            task = self.task_manager.create_task(**task_data)
            
            if task and hasattr(task, 'id'):
                self.logger.info(f"Successfully created ticket: {task.id} - {title}")
                return task.id
            else:
                self.logger.error(f"Task creation failed - no ID returned")
                self.logger.info("The task may have been created but without proper ID assignment")
                return None
            
        except AttributeError as e:
            attr_msg = str(e)
            if "create_task" in attr_msg:
                self.logger.error("create_task method not found in TaskManager")
                self.logger.info("The ai-trackdown-pytools API may have changed")
                self.logger.info("Check for updates or API documentation")
            else:
                self.logger.error(f"API mismatch when creating ticket: {attr_msg}")
            return None
        except ValueError as e:
            self.logger.error(f"Invalid data provided for ticket: {e}")
            self.logger.info("Check that all required fields are provided correctly")
            return None
        except PermissionError as e:
            self.logger.error(f"Permission denied when creating ticket: {e}")
            self.logger.info("Check write permissions for the tickets/ directory")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error creating ticket: {e.__class__.__name__}: {e}")
            self.logger.info("This could be due to:")
            self.logger.info("  - Disk full or quota exceeded")
            self.logger.info("  - Invalid characters in title or description")
            self.logger.info("  - Network issues (if using remote storage)")
            self.logger.debug("Full error details:", exc_info=True)
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
            self.logger.warning("TaskManager not available - cannot list tickets")
            self.logger.info("Run: pip install ai-trackdown-pytools")
            return []
        
        try:
            # Validate limit
            if limit < 1:
                self.logger.warning(f"Invalid limit {limit}, using 10")
                limit = 10
            elif limit > 100:
                self.logger.warning(f"Limit {limit} too high, capping at 100")
                limit = 100
            
            tasks = self.task_manager.get_recent_tasks(limit=limit)
            
            if not tasks:
                self.logger.info("No tickets found in the system")
                return []
            
            tickets = []
            for task in tasks:
                try:
                    ticket_data = {
                        'id': getattr(task, 'id', 'UNKNOWN'),
                        'title': getattr(task, 'title', 'Untitled'),
                        'status': getattr(task, 'status', 'unknown'),
                        'priority': getattr(task, 'priority', 'medium'),
                        'tags': getattr(task, 'tags', []),
                        'created_at': getattr(task, 'created_at', 'N/A'),
                    }
                    tickets.append(ticket_data)
                except Exception as task_error:
                    self.logger.warning(f"Error processing task: {task_error}")
                    self.logger.debug(f"Task object type: {type(task)}")
                    continue
            
            self.logger.info(f"Retrieved {len(tickets)} tickets")
            return tickets
            
        except AttributeError as e:
            attr_msg = str(e)
            if "get_recent_tasks" in attr_msg:
                self.logger.error("get_recent_tasks method not found in TaskManager")
                self.logger.info("This method may not be available in your version")
                self.logger.info("Try using the CLI directly: aitrackdown task list")
            else:
                self.logger.error(f"API mismatch when listing tickets: {attr_msg}")
            return []
        except FileNotFoundError as e:
            self.logger.error(f"Tickets directory not found: {e}")
            self.logger.info("Ensure the tickets/ directory exists")
            return []
        except PermissionError as e:
            self.logger.error(f"Permission denied reading tickets: {e}")
            self.logger.info("Check read permissions for the tickets/ directory")
            return []
        except Exception as e:
            self.logger.error(f"Failed to list tickets: {e.__class__.__name__}: {e}")
            self.logger.info("Try using the CLI directly: aitrackdown task list")
            self.logger.debug("Full error details:", exc_info=True)
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
            self.logger.error("TaskManager not available - cannot retrieve ticket")
            self.logger.info("Run: pip install ai-trackdown-pytools")
            return None
        
        if not ticket_id or not ticket_id.strip():
            self.logger.error("Invalid ticket ID provided")
            return None
        
        try:
            task = self.task_manager.load_task(ticket_id.strip())
            
            if not task:
                self.logger.warning(f"Ticket {ticket_id} not found")
                return None
            
            # Safely extract all fields with defaults
            ticket_data = {
                'id': getattr(task, 'id', ticket_id),
                'title': getattr(task, 'title', 'Untitled'),
                'description': getattr(task, 'description', ''),
                'status': getattr(task, 'status', 'unknown'),
                'priority': getattr(task, 'priority', 'medium'),
                'tags': getattr(task, 'tags', []),
                'assignees': getattr(task, 'assignees', []),
                'created_at': getattr(task, 'created_at', 'N/A'),
                'updated_at': getattr(task, 'updated_at', 'N/A'),
                'metadata': getattr(task, 'metadata', {}),
            }
            
            self.logger.info(f"Successfully retrieved ticket: {ticket_id}")
            return ticket_data
            
        except AttributeError as e:
            attr_msg = str(e)
            if "load_task" in attr_msg:
                self.logger.error("load_task method not found in TaskManager")
                self.logger.info("The API may have changed or this method is not available")
            else:
                self.logger.error(f"Error accessing ticket attributes: {attr_msg}")
            return None
        except FileNotFoundError as e:
            self.logger.error(f"Ticket file not found: {ticket_id}")
            self.logger.info(f"The ticket may have been deleted or the ID is incorrect")
            return None
        except PermissionError as e:
            self.logger.error(f"Permission denied reading ticket {ticket_id}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Failed to get ticket {ticket_id}: {e.__class__.__name__}: {e}")
            self.logger.info(f"Try using the CLI: aitrackdown show {ticket_id}")
            self.logger.debug("Full error details:", exc_info=True)
            return None
    
    # ================================================================================
    # Interface Adapter Methods
    # ================================================================================
    # These methods adapt the existing implementation to comply with TicketManagerInterface
    
    def create_task(self, title: str, description: str, **kwargs) -> Optional[str]:
        """Create a new task ticket.
        
        WHY: This adapter method provides interface compliance by wrapping
        the underlying task manager's create functionality.
        
        Args:
            title: Task title
            description: Task description
            **kwargs: Additional task properties
            
        Returns:
            Task ID if created successfully, None otherwise
        """
        if not self.task_manager:
            self.logger.error("Task manager not initialized")
            return None
        
        try:
            # Create task using ai-trackdown-pytools
            from ai_trackdown_pytools.core.task import Task
            
            task = Task(
                title=title,
                description=description,
                status=kwargs.get('status', 'open'),
                priority=kwargs.get('priority', 'medium'),
                tags=kwargs.get('tags', []),
                assignees=kwargs.get('assignees', [])
            )
            
            # Save the task
            task_id = self.task_manager.create_task(task)
            self.logger.info(f"Created task {task_id}: {title}")
            return task_id
            
        except ImportError:
            self.logger.error("ai-trackdown-pytools not available")
            return None
        except Exception as e:
            self.logger.error(f"Failed to create task: {e}")
            return None
    
    def update_task(self, task_id: str, **updates) -> bool:
        """Update an existing task.
        
        WHY: This adapter method provides interface compliance by wrapping
        task update operations.
        
        Args:
            task_id: ID of task to update
            **updates: Fields to update
            
        Returns:
            True if update successful
        """
        if not self.task_manager:
            self.logger.error("Task manager not initialized")
            return False
        
        try:
            # Get the existing task
            task = self.task_manager.get_task(task_id)
            if not task:
                self.logger.error(f"Task {task_id} not found")
                return False
            
            # Apply updates
            for key, value in updates.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            
            # Save the updated task
            self.task_manager.update_task(task)
            self.logger.info(f"Updated task {task_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update task {task_id}: {e}")
            return False
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task details.
        
        WHY: This adapter method provides interface compliance by wrapping
        the existing get_ticket method.
        
        Args:
            task_id: ID of task to retrieve
            
        Returns:
            Task data dictionary or None if not found
        """
        # Use existing get_ticket method which already returns dict format
        return self.get_ticket(task_id)
    
    def list_tasks(self, status: Optional[str] = None, **filters) -> List[Dict[str, Any]]:
        """List tasks with optional filtering.
        
        WHY: This adapter method provides interface compliance by wrapping
        task listing operations.
        
        Args:
            status: Optional status filter
            **filters: Additional filter criteria
            
        Returns:
            List of task dictionaries
        """
        if not self.task_manager:
            self.logger.error("Task manager not initialized")
            return []
        
        try:
            # Get all tasks
            tasks = self.task_manager.list_tasks()
            
            # Apply filters
            filtered_tasks = []
            for task in tasks:
                # Check status filter
                if status and task.get('status') != status:
                    continue
                
                # Check additional filters
                match = True
                for key, value in filters.items():
                    if task.get(key) != value:
                        match = False
                        break
                
                if match:
                    filtered_tasks.append(task)
            
            return filtered_tasks
            
        except Exception as e:
            self.logger.error(f"Failed to list tasks: {e}")
            return []
    
    def close_task(self, task_id: str, resolution: Optional[str] = None) -> bool:
        """Close a task.
        
        WHY: This adapter method provides interface compliance by updating
        task status to closed.
        
        Args:
            task_id: ID of task to close
            resolution: Optional resolution description
            
        Returns:
            True if close successful
        """
        updates = {'status': 'closed'}
        if resolution:
            updates['resolution'] = resolution
        
        return self.update_task(task_id, **updates)