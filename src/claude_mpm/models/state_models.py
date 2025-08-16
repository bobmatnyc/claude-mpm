"""State models for context preservation across Claude Code restarts.

This module defines data models for capturing and restoring various aspects
of the Claude Code execution state to enable seamless restarts.

Design Principles:
- Comprehensive state capture (process, conversation, project, restart info)
- Serialization-friendly data structures
- Validation and sanitization of sensitive data
- Platform-agnostic representations
"""

import os
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from enum import Enum


class StateType(Enum):
    """Types of state that can be captured."""
    PROCESS = "process"
    CONVERSATION = "conversation"
    PROJECT = "project"
    RESTART = "restart"
    FULL = "full"


@dataclass
class ProcessState:
    """Process execution state information.
    
    Captures the runtime state of the Claude Code process including
    environment, working directory, and command line arguments.
    """
    
    # Process identification
    pid: int
    parent_pid: int
    process_name: str
    
    # Execution context
    command: List[str]
    args: List[str]
    working_directory: str
    
    # Environment (filtered for security)
    environment: Dict[str, str]
    
    # Resource usage
    memory_mb: float
    cpu_percent: float
    open_files: List[str]
    
    # Timing
    start_time: float
    capture_time: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'pid': self.pid,
            'parent_pid': self.parent_pid,
            'process_name': self.process_name,
            'command': self.command,
            'args': self.args,
            'working_directory': self.working_directory,
            'environment': self._sanitize_environment(self.environment),
            'memory_mb': round(self.memory_mb, 2),
            'cpu_percent': round(self.cpu_percent, 2),
            'open_files': self.open_files[:100],  # Limit to prevent huge lists
            'start_time': self.start_time,
            'start_time_iso': datetime.fromtimestamp(self.start_time).isoformat(),
            'capture_time': self.capture_time,
            'capture_time_iso': datetime.fromtimestamp(self.capture_time).isoformat()
        }
    
    @staticmethod
    def _sanitize_environment(env: Dict[str, str]) -> Dict[str, str]:
        """Remove sensitive environment variables."""
        sensitive_patterns = [
            'TOKEN', 'KEY', 'SECRET', 'PASSWORD', 'CREDENTIAL',
            'API_KEY', 'AUTH', 'PRIVATE'
        ]
        
        sanitized = {}
        for key, value in env.items():
            # Check if key contains sensitive patterns
            is_sensitive = any(pattern in key.upper() for pattern in sensitive_patterns)
            
            if is_sensitive:
                sanitized[key] = '***REDACTED***'
            else:
                sanitized[key] = value
        
        return sanitized
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProcessState':
        """Create from dictionary."""
        return cls(
            pid=data['pid'],
            parent_pid=data['parent_pid'],
            process_name=data['process_name'],
            command=data['command'],
            args=data['args'],
            working_directory=data['working_directory'],
            environment=data['environment'],
            memory_mb=data['memory_mb'],
            cpu_percent=data['cpu_percent'],
            open_files=data['open_files'],
            start_time=data['start_time'],
            capture_time=data['capture_time']
        )


@dataclass
class ConversationContext:
    """Represents a single conversation context."""
    
    conversation_id: str
    title: str
    created_at: float
    updated_at: float
    message_count: int
    
    # Context window information
    total_tokens: int
    max_tokens: int
    
    # File references in conversation
    referenced_files: List[str]
    open_tabs: List[str]
    
    # Conversation metadata
    tags: List[str]
    is_active: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationContext':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class ConversationState:
    """Claude conversation state and context.
    
    Captures the current conversation state including active conversations,
    context windows, and file references.
    """
    
    # Active conversation
    active_conversation_id: Optional[str]
    active_conversation: Optional[ConversationContext]
    
    # Recent conversations (for context)
    recent_conversations: List[ConversationContext]
    
    # Global context
    total_conversations: int
    total_storage_mb: float
    
    # User preferences preserved
    preferences: Dict[str, Any]
    
    # File state
    open_files: List[str]
    recent_files: List[str]
    pinned_files: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'active_conversation_id': self.active_conversation_id,
            'active_conversation': self.active_conversation.to_dict() if self.active_conversation else None,
            'recent_conversations': [c.to_dict() for c in self.recent_conversations],
            'total_conversations': self.total_conversations,
            'total_storage_mb': round(self.total_storage_mb, 2),
            'preferences': self.preferences,
            'open_files': self.open_files,
            'recent_files': self.recent_files,
            'pinned_files': self.pinned_files
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationState':
        """Create from dictionary."""
        return cls(
            active_conversation_id=data.get('active_conversation_id'),
            active_conversation=(
                ConversationContext.from_dict(data['active_conversation'])
                if data.get('active_conversation') else None
            ),
            recent_conversations=[
                ConversationContext.from_dict(c)
                for c in data.get('recent_conversations', [])
            ],
            total_conversations=data.get('total_conversations', 0),
            total_storage_mb=data.get('total_storage_mb', 0.0),
            preferences=data.get('preferences', {}),
            open_files=data.get('open_files', []),
            recent_files=data.get('recent_files', []),
            pinned_files=data.get('pinned_files', [])
        )


@dataclass
class ProjectState:
    """Project and Git repository state.
    
    Captures the current project context including Git branch,
    modified files, and project metadata.
    """
    
    # Project identification
    project_path: str
    project_name: str
    
    # Git state
    git_branch: Optional[str]
    git_commit: Optional[str]
    git_status: Dict[str, List[str]]  # staged, modified, untracked
    git_remotes: Dict[str, str]
    
    # File state
    modified_files: List[str]
    open_editors: List[str]
    breakpoints: Dict[str, List[int]]  # file -> line numbers
    
    # Project metadata
    project_type: str  # python, node, go, etc.
    dependencies: Dict[str, str]  # package -> version
    environment_vars: Dict[str, str]  # project-specific env vars
    
    # Build/test state
    last_build_status: Optional[str]
    last_test_results: Optional[Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'project_path': self.project_path,
            'project_name': self.project_name,
            'git_branch': self.git_branch,
            'git_commit': self.git_commit,
            'git_status': self.git_status,
            'git_remotes': self.git_remotes,
            'modified_files': self.modified_files,
            'open_editors': self.open_editors,
            'breakpoints': self.breakpoints,
            'project_type': self.project_type,
            'dependencies': self.dependencies,
            'environment_vars': ProcessState._sanitize_environment(self.environment_vars),
            'last_build_status': self.last_build_status,
            'last_test_results': self.last_test_results
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectState':
        """Create from dictionary."""
        return cls(
            project_path=data['project_path'],
            project_name=data['project_name'],
            git_branch=data.get('git_branch'),
            git_commit=data.get('git_commit'),
            git_status=data.get('git_status', {}),
            git_remotes=data.get('git_remotes', {}),
            modified_files=data.get('modified_files', []),
            open_editors=data.get('open_editors', []),
            breakpoints=data.get('breakpoints', {}),
            project_type=data.get('project_type', 'unknown'),
            dependencies=data.get('dependencies', {}),
            environment_vars=data.get('environment_vars', {}),
            last_build_status=data.get('last_build_status'),
            last_test_results=data.get('last_test_results')
        )


@dataclass
class RestartState:
    """Information about the restart event.
    
    Captures why and when a restart occurred, along with relevant
    metrics at the time of restart.
    """
    
    # Restart identification
    restart_id: str
    restart_count: int
    
    # Timing
    timestamp: float
    previous_uptime: float
    
    # Reason and context
    reason: str
    trigger: str  # manual, memory, crash, scheduled
    
    # Metrics at restart
    memory_mb: float
    memory_limit_mb: float
    cpu_percent: float
    
    # Error information (if applicable)
    error_type: Optional[str]
    error_message: Optional[str]
    error_traceback: Optional[str]
    
    # Recovery information
    recovery_attempted: bool
    recovery_successful: bool
    data_preserved: List[str]  # Types of data preserved
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'restart_id': self.restart_id,
            'restart_count': self.restart_count,
            'timestamp': self.timestamp,
            'timestamp_iso': datetime.fromtimestamp(self.timestamp).isoformat(),
            'previous_uptime': self.previous_uptime,
            'reason': self.reason,
            'trigger': self.trigger,
            'memory_mb': round(self.memory_mb, 2),
            'memory_limit_mb': round(self.memory_limit_mb, 2),
            'cpu_percent': round(self.cpu_percent, 2),
            'error_type': self.error_type,
            'error_message': self.error_message,
            'error_traceback': self.error_traceback,
            'recovery_attempted': self.recovery_attempted,
            'recovery_successful': self.recovery_successful,
            'data_preserved': self.data_preserved
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RestartState':
        """Create from dictionary."""
        return cls(
            restart_id=data['restart_id'],
            restart_count=data['restart_count'],
            timestamp=data['timestamp'],
            previous_uptime=data['previous_uptime'],
            reason=data['reason'],
            trigger=data['trigger'],
            memory_mb=data['memory_mb'],
            memory_limit_mb=data['memory_limit_mb'],
            cpu_percent=data['cpu_percent'],
            error_type=data.get('error_type'),
            error_message=data.get('error_message'),
            error_traceback=data.get('error_traceback'),
            recovery_attempted=data.get('recovery_attempted', False),
            recovery_successful=data.get('recovery_successful', False),
            data_preserved=data.get('data_preserved', [])
        )


@dataclass
class CompleteState:
    """Complete state snapshot combining all state components.
    
    This is the main state object that gets serialized and restored
    across Claude Code restarts.
    """
    
    # State components
    process_state: ProcessState
    conversation_state: ConversationState
    project_state: ProjectState
    restart_state: RestartState
    
    # Metadata
    state_version: str = "1.0.0"
    state_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d_%H%M%S"))
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'state_version': self.state_version,
            'state_id': self.state_id,
            'created_at': self.created_at,
            'created_at_iso': datetime.fromtimestamp(self.created_at).isoformat(),
            'process': self.process_state.to_dict(),
            'conversation': self.conversation_state.to_dict(),
            'project': self.project_state.to_dict(),
            'restart': self.restart_state.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CompleteState':
        """Create from dictionary."""
        return cls(
            state_version=data.get('state_version', '1.0.0'),
            state_id=data.get('state_id'),
            created_at=data.get('created_at'),
            process_state=ProcessState.from_dict(data['process']),
            conversation_state=ConversationState.from_dict(data['conversation']),
            project_state=ProjectState.from_dict(data['project']),
            restart_state=RestartState.from_dict(data['restart'])
        )
    
    def validate(self) -> List[str]:
        """Validate state data and return list of issues."""
        issues = []
        
        # Check required fields
        if not self.state_id:
            issues.append("State ID is required")
        
        if not self.process_state.pid:
            issues.append("Process PID is required")
        
        if not self.project_state.project_path:
            issues.append("Project path is required")
        
        # Check path validity
        if self.project_state.project_path:
            project_path = Path(self.project_state.project_path)
            if not project_path.exists():
                issues.append(f"Project path does not exist: {project_path}")
        
        # Check state version compatibility
        if self.state_version != "1.0.0":
            issues.append(f"Unsupported state version: {self.state_version}")
        
        return issues