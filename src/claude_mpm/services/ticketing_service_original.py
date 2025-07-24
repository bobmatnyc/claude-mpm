#!/usr/bin/env python3
"""
Ticketing Service
=================

Core service that wraps ai-trackdown-pytools for simplified ticket management.
Provides a clean interface for PM orchestration and agent ticket operations.

Key Features:
- Singleton pattern for consistent ticket management
- Simplified API wrapping ai-trackdown-pytools
- Automatic ticket directory management
- Thread-safe operations
- Comprehensive error handling and logging
- Integration with Claude PM Framework

Usage:
    from claude_pm.services.ticketing_service import TicketingService
    
    # Get singleton instance
    ticketing = TicketingService.get_instance()
    
    # Create a ticket
    ticket = ticketing.create_ticket(
        title="Implement new feature",
        description="Detailed description",
        priority="high"
    )
    
    # List tickets
    tickets = ticketing.list_tickets(status="open")
    
    # Update ticket
    ticketing.update_ticket("CLAUDE-001", status="in_progress")
"""

import asyncio
import json
import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Import ai-trackdown-pytools
try:
    from ai_trackdown_pytools import Task, Project
    from ai_trackdown_pytools.core.task import TaskManager
    AI_TRACKDOWN_AVAILABLE = True
    # Map to expected names
    Ticket = Task
    TicketManager = TaskManager
except ImportError:
    AI_TRACKDOWN_AVAILABLE = False
    # Define fallback classes for type hints
    class TicketStatus:
        OPEN = "open"
        IN_PROGRESS = "in_progress"
        RESOLVED = "resolved"
        CLOSED = "closed"
    
    class TicketPriority:
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"
        CRITICAL = "critical"

import logging

logger = logging.getLogger(__name__)


@dataclass
class TicketData:
    """Simplified ticket data structure for easy use."""
    id: str
    title: str
    description: str
    status: str = "open"
    priority: str = "medium"
    assignee: Optional[str] = None
    labels: List[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class TicketingService:
    """
    Core ticketing service wrapping ai-trackdown-pytools.
    
    Provides simplified interface for ticket management operations
    within the Claude PM Framework.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Implement singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the ticketing service."""
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._ticket_manager = None
            self._tickets_dir = None
            self._setup_service()
    
    @classmethod
    def get_instance(cls) -> 'TicketingService':
        """Get singleton instance of TicketingService."""
        return cls()
    
    def _setup_service(self):
        """Set up the ticketing service."""
        try:
            # Find or create tickets directory
            self._tickets_dir = self._find_tickets_directory()
            
            if AI_TRACKDOWN_AVAILABLE:
                # Initialize ai-trackdown ticket manager
                # TaskManager expects project_path (parent of tickets directory)
                project_path = self._tickets_dir.parent
                self._ticket_manager = TicketManager(project_path)
                logger.info(f"Ticketing service initialized with project path: {project_path}")
            else:
                logger.warning("ai-trackdown-pytools not available, using stub implementation")
                
        except Exception as e:
            logger.error(f"Failed to initialize ticketing service: {e}")
            raise
    
    def _find_tickets_directory(self) -> Path:
        """Find or create the tickets directory."""
        # Check current directory first
        current_dir = Path.cwd()
        tickets_path = current_dir / "tickets"
        
        if tickets_path.exists():
            return tickets_path
        
        # Check for .claude-pm directory
        claude_pm_dir = current_dir / ".claude-pm"
        if claude_pm_dir.exists():
            tickets_path = claude_pm_dir / "tickets"
            tickets_path.mkdir(exist_ok=True)
            return tickets_path
        
        # Create in current directory
        tickets_path.mkdir(exist_ok=True)
        return tickets_path
    
    # Core ticket operations
    
    def create_ticket(
        self,
        title: str,
        description: str,
        priority: str = "medium",
        assignee: Optional[str] = None,
        labels: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> TicketData:
        """
        Create a new ticket.
        
        Args:
            title: Ticket title
            description: Detailed description
            priority: Priority level (low, medium, high, critical)
            assignee: Optional assignee
            labels: Optional list of labels
            metadata: Optional metadata dictionary
            
        Returns:
            TicketData object with created ticket information
        """
        try:
            if not AI_TRACKDOWN_AVAILABLE:
                # Stub implementation
                ticket_id = f"CLAUDE-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                return TicketData(
                    id=ticket_id,
                    title=title,
                    description=description,
                    status="open",
                    priority=priority,
                    assignee=assignee,
                    labels=labels or [],
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                    metadata=metadata or {}
                )
            
            # Use ai-trackdown to create task
            # create_task expects: title, description, status, priority, assignees, tags, metadata
            task_data = {
                'title': title,
                'description': description,
                'status': 'open',
                'priority': priority.lower(),
                'assignees': [assignee] if assignee else [],
                'tags': labels or [],
                'metadata': metadata or {}
            }
            
            ticket = self._ticket_manager.create_task(**task_data)
            
            return self._convert_to_ticket_data(ticket)
            
        except Exception as e:
            logger.error(f"Failed to create ticket: {e}")
            raise
    
    def get_ticket(self, ticket_id: str) -> Optional[TicketData]:
        """
        Get a ticket by ID.
        
        Args:
            ticket_id: Ticket identifier
            
        Returns:
            TicketData object or None if not found
        """
        try:
            if not AI_TRACKDOWN_AVAILABLE:
                return None
            
            ticket = self._ticket_manager.get_ticket(ticket_id)
            if ticket:
                return self._convert_to_ticket_data(ticket)
            return None
            
        except Exception as e:
            logger.error(f"Failed to get ticket {ticket_id}: {e}")
            return None
    
    def list_tickets(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assignee: Optional[str] = None,
        labels: Optional[List[str]] = None,
        limit: Optional[int] = None
    ) -> List[TicketData]:
        """
        List tickets with optional filters.
        
        Args:
            status: Filter by status (open, in_progress, resolved, closed)
            priority: Filter by priority (low, medium, high, critical)
            assignee: Filter by assignee
            labels: Filter by labels (tickets must have all specified labels)
            limit: Maximum number of tickets to return
            
        Returns:
            List of TicketData objects
        """
        try:
            if not AI_TRACKDOWN_AVAILABLE:
                return []
            
            # Build filter criteria
            filters = {}
            if status:
                filters['status'] = getattr(TicketStatus, status.upper(), None)
            if priority:
                filters['priority'] = getattr(TicketPriority, priority.upper(), None)
            if assignee:
                filters['assignee'] = assignee
            if labels:
                filters['labels'] = labels
            
            tickets = self._ticket_manager.list_tickets(**filters)
            
            # Convert and limit results
            result = [self._convert_to_ticket_data(t) for t in tickets]
            if limit:
                result = result[:limit]
                
            return result
            
        except Exception as e:
            logger.error(f"Failed to list tickets: {e}")
            return []
    
    def update_ticket(
        self,
        ticket_id: str,
        title: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assignee: Optional[str] = None,
        labels: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[TicketData]:
        """
        Update an existing ticket.
        
        Args:
            ticket_id: Ticket identifier
            title: New title (optional)
            description: New description (optional)
            status: New status (optional)
            priority: New priority (optional)
            assignee: New assignee (optional)
            labels: New labels (optional, replaces existing)
            metadata: New metadata (optional, merges with existing)
            
        Returns:
            Updated TicketData object or None if not found
        """
        try:
            if not AI_TRACKDOWN_AVAILABLE:
                return None
            
            # Build update data
            updates = {}
            if title is not None:
                updates['title'] = title
            if description is not None:
                updates['description'] = description
            if status is not None:
                updates['status'] = getattr(TicketStatus, status.upper(), None)
            if priority is not None:
                updates['priority'] = getattr(TicketPriority, priority.upper(), None)
            if assignee is not None:
                updates['assignee'] = assignee
            if labels is not None:
                updates['labels'] = labels
            if metadata is not None:
                updates['metadata'] = metadata
            
            ticket = self._ticket_manager.update_ticket(ticket_id, **updates)
            if ticket:
                return self._convert_to_ticket_data(ticket)
            return None
            
        except Exception as e:
            logger.error(f"Failed to update ticket {ticket_id}: {e}")
            return None
    
    def add_comment(
        self,
        ticket_id: str,
        comment: str,
        author: Optional[str] = None
    ) -> bool:
        """
        Add a comment to a ticket.
        
        Args:
            ticket_id: Ticket identifier
            comment: Comment text
            author: Comment author (optional)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not AI_TRACKDOWN_AVAILABLE:
                return False
            
            self._ticket_manager.add_comment(
                ticket_id=ticket_id,
                comment=comment,
                author=author or "claude-pm"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to add comment to ticket {ticket_id}: {e}")
            return False
    
    def close_ticket(
        self,
        ticket_id: str,
        resolution: Optional[str] = None
    ) -> Optional[TicketData]:
        """
        Close a ticket.
        
        Args:
            ticket_id: Ticket identifier
            resolution: Optional resolution description
            
        Returns:
            Updated TicketData object or None if not found
        """
        try:
            if resolution:
                self.add_comment(ticket_id, f"Resolution: {resolution}")
            
            return self.update_ticket(ticket_id, status="closed")
            
        except Exception as e:
            logger.error(f"Failed to close ticket {ticket_id}: {e}")
            return None
    
    # Utility methods
    
    def search_tickets(self, query: str, limit: Optional[int] = None) -> List[TicketData]:
        """
        Search tickets by text query.
        
        Args:
            query: Search query (searches in title and description)
            limit: Maximum number of results
            
        Returns:
            List of matching TicketData objects
        """
        try:
            if not AI_TRACKDOWN_AVAILABLE:
                return []
            
            tickets = self._ticket_manager.search_tickets(query)
            result = [self._convert_to_ticket_data(t) for t in tickets]
            
            if limit:
                result = result[:limit]
                
            return result
            
        except Exception as e:
            logger.error(f"Failed to search tickets: {e}")
            return []
    
    def get_ticket_statistics(self) -> Dict[str, Any]:
        """
        Get ticket statistics.
        
        Returns:
            Dictionary with ticket statistics
        """
        try:
            if not AI_TRACKDOWN_AVAILABLE:
                return {
                    "total": 0,
                    "by_status": {},
                    "by_priority": {},
                    "unassigned": 0
                }
            
            stats = self._ticket_manager.get_statistics()
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get ticket statistics: {e}")
            return {}
    
    def _convert_to_ticket_data(self, ticket: Any) -> TicketData:
        """Convert ai-trackdown ticket to TicketData."""
        # Task uses 'assignees' (list) not 'assignee' (single)
        assignee = ticket.assignees[0] if ticket.assignees else None
        
        # Task uses 'tags' not 'labels'
        labels = ticket.tags if hasattr(ticket, 'tags') else []
        
        return TicketData(
            id=ticket.id,
            title=ticket.title,
            description=ticket.description,
            status=ticket.status if isinstance(ticket.status, str) else str(ticket.status),
            priority=ticket.priority if isinstance(ticket.priority, str) else str(ticket.priority),
            assignee=assignee,
            labels=labels,
            created_at=ticket.created_at,
            updated_at=ticket.updated_at if hasattr(ticket, 'updated_at') else ticket.created_at,
            metadata=ticket.metadata or {}
        )
    
    # Async support for PM orchestration
    
    async def acreate_ticket(self, **kwargs) -> TicketData:
        """Async version of create_ticket."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.create_ticket, **kwargs)
    
    async def aget_ticket(self, ticket_id: str) -> Optional[TicketData]:
        """Async version of get_ticket."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get_ticket, ticket_id)
    
    async def alist_tickets(self, **kwargs) -> List[TicketData]:
        """Async version of list_tickets."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.list_tickets, **kwargs)
    
    async def aupdate_ticket(self, ticket_id: str, **kwargs) -> Optional[TicketData]:
        """Async version of update_ticket."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.update_ticket, ticket_id, **kwargs)


# Convenience functions for direct import
def get_ticketing_service() -> TicketingService:
    """Get the singleton TicketingService instance."""
    return TicketingService.get_instance()