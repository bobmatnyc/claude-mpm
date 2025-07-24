#!/usr/bin/env python3
"""
File system monitoring for agent files.

This module handles real-time file system event detection and processing
for agent file changes.
"""

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from .models import ModificationType
from claude_mpm.core.mixins import LoggerMixin

if TYPE_CHECKING:
    from . import AgentModificationTracker


class AgentFileSystemHandler(FileSystemEventHandler, LoggerMixin):
    """File system event handler for agent file monitoring."""
    
    def __init__(self, tracker: 'AgentModificationTracker'):
        super().__init__()
        self.tracker = tracker
        # LoggerMixin provides self.logger automatically
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        if self._is_agent_file(event.src_path):
            asyncio.create_task(
                self.tracker._handle_file_modification(event.src_path, ModificationType.MODIFY)
            )
    
    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
        
        if self._is_agent_file(event.src_path):
            asyncio.create_task(
                self.tracker._handle_file_modification(event.src_path, ModificationType.CREATE)
            )
    
    def on_deleted(self, event):
        """Handle file deletion events."""
        if event.is_directory:
            return
        
        if self._is_agent_file(event.src_path):
            asyncio.create_task(
                self.tracker._handle_file_modification(event.src_path, ModificationType.DELETE)
            )
    
    def on_moved(self, event):
        """Handle file move events."""
        if event.is_directory:
            return
        
        if self._is_agent_file(event.src_path) or self._is_agent_file(event.dest_path):
            asyncio.create_task(
                self.tracker._handle_file_move(event.src_path, event.dest_path)
            )
    
    def _is_agent_file(self, file_path: str) -> bool:
        """Check if file is an agent file."""
        path = Path(file_path)
        
        # Check file extension
        if path.suffix not in ['.py', '.md']:
            return False
        
        # Check if it's in an agent directory
        path_str = str(path)
        agent_indicators = [
            '.claude-pm/agents',
            'claude_pm/agents',
            '_agent.py',
            '-agent.py',
            'agent_',
            '-profile.md'
        ]
        
        return any(indicator in path_str for indicator in agent_indicators)


class FileMonitor(LoggerMixin):
    """File system monitor for agent directories."""
    
    def __init__(self):
        # LoggerMixin provides self.logger automatically
        self.file_observer: Optional[Observer] = None
        self.watched_paths: Set[Path] = set()
    
    async def setup_monitoring(self, tracker: 'AgentModificationTracker', event_handler: AgentFileSystemHandler) -> None:
        """Set up file system monitoring for agent files."""
        try:
            # Create observer
            self.file_observer = Observer()
            
            # Add watch paths for agent directories
            await self._discover_watch_paths()
            
            for watch_path in self.watched_paths:
                if watch_path.exists():
                    self.file_observer.schedule(
                        event_handler,
                        str(watch_path),
                        recursive=True
                    )
                    self.logger.debug(f"Watching agent path: {watch_path}")
            
            # Start monitoring
            self.file_observer.start()
            self.logger.info(f"File system monitoring started for {len(self.watched_paths)} paths")
            
        except Exception as e:
            self.logger.error(f"Failed to setup file monitoring: {e}")
            raise
    
    async def _discover_watch_paths(self) -> None:
        """Discover paths to watch for agent files."""
        watch_paths = set()
        
        # Current working directory agents
        current_agents = Path.cwd() / '.claude-pm' / 'agents'
        if current_agents.exists():
            watch_paths.add(current_agents)
        
        # Walk parent directories
        current_path = Path.cwd()
        while current_path.parent != current_path:
            parent_agents = current_path.parent / '.claude-pm' / 'agents'
            if parent_agents.exists():
                watch_paths.add(parent_agents)
            current_path = current_path.parent
        
        # User directory agents
        user_agents = Path.home() / '.claude-pm' / 'agents'
        if user_agents.exists():
            watch_paths.add(user_agents)
        
        # System agents (if available)
        try:
            import claude_pm
            system_agents = Path(claude_pm.__file__).parent / 'agents'
            if system_agents.exists():
                watch_paths.add(system_agents)
        except ImportError:
            pass
        
        self.watched_paths = watch_paths
        self.logger.debug(f"Discovered {len(watch_paths)} agent paths to watch")
    
    def stop_monitoring(self) -> None:
        """Stop file system monitoring."""
        if self.file_observer:
            self.file_observer.stop()
            self.file_observer.join(timeout=5)
            self.logger.info("File system monitoring stopped")