"""TODO Hijacker - Monitors Claude's TODO files and transforms them into agent delegations."""

import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent

try:
    from ..core.logger import get_logger
    from ..utils.config_manager import ConfigurationManager
    from .todo_transformer import TodoTransformer
except ImportError:
    from core.logger import get_logger
    from utils.config_manager import ConfigurationManager
    from orchestration.todo_transformer import TodoTransformer


class TodoFileHandler(FileSystemEventHandler):
    """Handles file system events for Claude's TODO files."""
    
    def __init__(self, callback: Callable[[Path], None], logger: logging.Logger):
        """Initialize the handler."""
        self.callback = callback
        self.logger = logger
        self._last_processed = {}
        
    def on_modified(self, event: FileModifiedEvent):
        """Handle file modification events."""
        if event.is_directory:
            return
            
        path = Path(event.src_path)
        if path.suffix == '.json' and 'todos' in str(path):
            # Debounce - only process if file hasn't been processed in last second
            now = time.time()
            if path in self._last_processed:
                if now - self._last_processed[path] < 1.0:
                    return
            
            self._last_processed[path] = now
            self.logger.debug(f"TODO file modified: {path}")
            self.callback(path)
    
    def on_created(self, event: FileCreatedEvent):
        """Handle file creation events."""
        if event.is_directory:
            return
            
        path = Path(event.src_path)
        if path.suffix == '.json' and 'todos' in str(path):
            self.logger.debug(f"TODO file created: {path}")
            # Wait a moment for file to be fully written
            time.sleep(0.1)
            self.callback(path)


class TodoHijacker:
    """
    Monitors Claude's TODO files and transforms them into agent delegations.
    
    Claude stores TODOs in ~/.claude/todos/ as JSON files. This class:
    - Monitors the TODO directory for changes
    - Parses TODO files when they're created or modified
    - Transforms TODOs into agent delegations
    - Integrates with the subprocess orchestrator
    """
    
    def __init__(
        self,
        todo_dir: Optional[Path] = None,
        log_level: str = "INFO",
        on_delegation: Optional[Callable[[Dict[str, Any]], None]] = None
    ):
        """
        Initialize the TODO hijacker.
        
        Args:
            todo_dir: Directory where Claude stores TODOs (default: ~/.claude/todos/)
            log_level: Logging level
            on_delegation: Callback for when a delegation is created
        """
        self.logger = get_logger("todo_hijacker")
        self.logger.setLevel(getattr(logging, log_level.upper()))
        
        # Set TODO directory
        if todo_dir:
            self.todo_dir = Path(todo_dir)
        else:
            # Default Claude TODO location
            self.todo_dir = Path.home() / ".claude" / "todos"
        
        # Create directory if it doesn't exist (for testing)
        self.todo_dir.mkdir(parents=True, exist_ok=True)
        
        # Components
        self.transformer = TodoTransformer()
        self.observer = None
        self.on_delegation = on_delegation
        self.config_mgr = ConfigurationManager(cache_enabled=True)
        
        # State tracking
        self._processed_todos = set()
        self._active = False
        
        self.logger.info(f"TodoHijacker initialized, monitoring: {self.todo_dir}")
    
    def start_monitoring(self):
        """Start monitoring the TODO directory."""
        if self._active:
            self.logger.warning("Monitoring already active")
            return
            
        # Process any existing TODO files
        self._scan_existing_todos()
        
        # Set up file system monitoring
        self.observer = Observer()
        handler = TodoFileHandler(self._process_todo_file, self.logger)
        self.observer.schedule(handler, str(self.todo_dir), recursive=True)
        self.observer.start()
        
        self._active = True
        self.logger.info("Started monitoring TODO directory")
    
    def stop_monitoring(self):
        """Stop monitoring the TODO directory."""
        if not self._active:
            return
            
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
        
        self._active = False
        self.logger.info("Stopped monitoring TODO directory")
    
    def _scan_existing_todos(self):
        """Scan and process any existing TODO files."""
        try:
            todo_files = list(self.todo_dir.glob("*.json"))
            self.logger.info(f"Found {len(todo_files)} existing TODO files")
            
            for todo_file in todo_files:
                self._process_todo_file(todo_file)
                
        except Exception as e:
            self.logger.error(f"Error scanning existing TODOs: {e}")
    
    def _process_todo_file(self, file_path: Path):
        """
        Process a TODO file and create delegations.
        
        Args:
            file_path: Path to the TODO JSON file
        """
        try:
            # Read and parse the TODO file
            todo_data = self.config_mgr.load_json(file_path)
            
            # Extract TODOs
            todos = self._extract_todos(todo_data)
            if not todos:
                self.logger.debug(f"No actionable TODOs found in {file_path}")
                return
            
            self.logger.info(f"Processing {len(todos)} TODOs from {file_path.name}")
            
            # Transform each TODO into a delegation
            for todo in todos:
                # Skip if already processed
                todo_id = self._get_todo_id(todo)
                if todo_id in self._processed_todos:
                    continue
                
                # Transform to delegation
                delegation = self.transformer.transform_todo(todo)
                if delegation:
                    self.logger.info(f"Created delegation: {delegation['agent']} - {delegation['task'][:50]}...")
                    
                    # Mark as processed
                    self._processed_todos.add(todo_id)
                    
                    # Trigger callback if provided
                    if self.on_delegation:
                        self.on_delegation(delegation)
                        
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in {file_path}: {e}")
        except Exception as e:
            self.logger.error(f"Error processing TODO file {file_path}: {e}")
    
    def _extract_todos(self, todo_data: Any) -> List[Dict[str, Any]]:
        """
        Extract TODOs from Claude's TODO data structure.
        
        Args:
            todo_data: Parsed TODO JSON data
            
        Returns:
            List of TODO items
        """
        todos = []
        
        # Handle different TODO formats Claude might use
        if isinstance(todo_data, dict):
            # Format 1: {"todos": [...]}
            if "todos" in todo_data:
                todos.extend(todo_data["todos"])
            # Format 2: {"items": [...]}
            elif "items" in todo_data:
                todos.extend(todo_data["items"])
            # Format 3: Direct TODO object
            elif "content" in todo_data or "task" in todo_data:
                todos.append(todo_data)
                
        elif isinstance(todo_data, list):
            # Format 4: Direct list of TODOs
            todos.extend(todo_data)
        
        # Filter out completed or invalid TODOs
        valid_todos = []
        for todo in todos:
            if isinstance(todo, dict):
                # Skip completed TODOs
                if todo.get("status") == "completed" or todo.get("done", False):
                    continue
                # Must have content or task
                if "content" in todo or "task" in todo:
                    valid_todos.append(todo)
        
        return valid_todos
    
    def _get_todo_id(self, todo: Dict[str, Any]) -> str:
        """
        Generate a unique ID for a TODO to track processing.
        
        Args:
            todo: TODO item
            
        Returns:
            Unique identifier string
        """
        # Use ID if available
        if "id" in todo:
            return str(todo["id"])
        
        # Otherwise create ID from content
        content = todo.get("content") or todo.get("task") or ""
        timestamp = todo.get("created_at") or todo.get("timestamp") or ""
        return f"{hash(content)}_{timestamp}"
    
    def get_pending_delegations(self) -> List[Dict[str, Any]]:
        """
        Get all pending delegations from current TODOs.
        
        Returns:
            List of delegation dicts ready for orchestrator
        """
        delegations = []
        
        try:
            # Scan all TODO files
            todo_files = list(self.todo_dir.glob("*.json"))
            
            for todo_file in todo_files:
                todo_data = self.config_mgr.load_json(todo_file)
                
                todos = self._extract_todos(todo_data)
                for todo in todos:
                    todo_id = self._get_todo_id(todo)
                    if todo_id not in self._processed_todos:
                        delegation = self.transformer.transform_todo(todo)
                        if delegation:
                            delegations.append(delegation)
                            
        except Exception as e:
            self.logger.error(f"Error getting pending delegations: {e}")
        
        return delegations
    
    def mark_delegation_completed(self, delegation: Dict[str, Any]):
        """
        Mark a delegation as completed to avoid reprocessing.
        
        Args:
            delegation: The completed delegation
        """
        # Mark the original TODO as processed
        if "todo_id" in delegation:
            self._processed_todos.add(delegation["todo_id"])
    
    def __enter__(self):
        """Context manager entry."""
        self.start_monitoring()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop_monitoring()