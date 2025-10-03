from pathlib import Path

"""Agent Session Model for Event Aggregation.

WHY: This model represents a complete agent activity session, capturing all events
from initial prompt through delegations, tool operations, and final responses.
It provides a structured way to analyze what happened during an agent session.

DESIGN DECISION: We use a hierarchical event structure to maintain relationships
between related events (e.g., pre_tool and post_tool pairs) while preserving
chronological order for session replay and analysis.
"""

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class EventCategory(Enum):
    """Categories for different types of events in a session."""

    PROMPT = "prompt"
    DELEGATION = "delegation"
    TOOL = "tool"
    FILE = "file"
    TODO = "todo"
    RESPONSE = "response"
    MEMORY = "memory"
    STATUS = "status"
    SYSTEM = "system"


@dataclass
class SessionEvent:
    """Individual event within a session.

    WHY: Each event needs to be self-contained with all necessary context
    for later analysis, including timing, category, and relationships.
    """

    timestamp: str
    event_type: str  # Original event type from Socket.IO
    category: EventCategory
    data: Dict[str, Any]
    session_id: Optional[str] = None
    agent_context: Optional[str] = None  # Which agent was active
    correlation_id: Optional[str] = None  # For matching pre/post events

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "category": self.category.value,
            "data": self.data,
            "session_id": self.session_id,
            "agent_context": self.agent_context,
            "correlation_id": self.correlation_id,
        }


@dataclass
class ToolOperation:
    """Represents a complete tool operation with pre/post events.

    WHY: Tool operations often span multiple events (pre_tool, post_tool).
    This structure correlates them for complete analysis.
    """

    tool_name: str
    agent_type: str
    start_time: str
    end_time: Optional[str] = None
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    duration_ms: Optional[int] = None
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class AgentDelegation:
    """Represents an agent delegation with its full lifecycle.

    WHY: Agent delegations are key session events that need special tracking
    to understand the flow of work between agents.
    """

    agent_type: str
    task_description: str
    start_time: str
    end_time: Optional[str] = None
    prompt: Optional[str] = None
    response: Optional[str] = None
    tool_operations: List[ToolOperation] = field(default_factory=list)
    file_changes: List[str] = field(default_factory=list)
    todos_modified: List[Dict[str, Any]] = field(default_factory=list)
    memory_updates: List[Dict[str, Any]] = field(default_factory=list)
    duration_ms: Optional[int] = None
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "agent_type": self.agent_type,
            "task_description": self.task_description,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "prompt": self.prompt,
            "response": self.response,
            "tool_operations": [op.to_dict() for op in self.tool_operations],
            "file_changes": self.file_changes,
            "todos_modified": self.todos_modified,
            "memory_updates": self.memory_updates,
            "duration_ms": self.duration_ms,
            "success": self.success,
            "error": self.error,
        }


@dataclass
class SessionMetrics:
    """Aggregated metrics for a session.

    WHY: Quick summary statistics help identify patterns and anomalies
    without processing all events.
    """

    total_events: int = 0
    event_counts: Dict[str, int] = field(default_factory=dict)
    agents_used: Set[str] = field(default_factory=set)
    tools_used: Set[str] = field(default_factory=set)
    files_modified: Set[str] = field(default_factory=set)
    total_delegations: int = 0
    total_tool_calls: int = 0
    total_file_operations: int = 0
    session_duration_ms: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total_events": self.total_events,
            "event_counts": self.event_counts,
            "agents_used": list(self.agents_used),
            "tools_used": list(self.tools_used),
            "files_modified": list(self.files_modified),
            "total_delegations": self.total_delegations,
            "total_tool_calls": self.total_tool_calls,
            "total_file_operations": self.total_file_operations,
            "session_duration_ms": self.session_duration_ms,
        }


@dataclass
class AgentSession:
    """Complete representation of an agent activity session.

    WHY: This is the top-level model that captures everything that happened
    during a Claude MPM session, from initial prompt to final response.

    DESIGN DECISION: We maintain both a flat chronological event list and
    structured representations (delegations, tool operations) to support
    different analysis needs.
    """

    session_id: str
    start_time: str
    end_time: Optional[str] = None
    working_directory: str = ""
    launch_method: str = ""
    initial_prompt: Optional[str] = None
    final_response: Optional[str] = None

    # Event collections
    events: List[SessionEvent] = field(default_factory=list)
    delegations: List[AgentDelegation] = field(default_factory=list)

    # Session state
    current_agent: Optional[str] = None
    active_delegation: Optional[AgentDelegation] = None
    pending_tool_operations: Dict[str, ToolOperation] = field(default_factory=dict)

    # Metrics
    metrics: SessionMetrics = field(default_factory=SessionMetrics)

    # Metadata
    claude_pid: Optional[int] = None
    git_branch: Optional[str] = None
    project_root: Optional[str] = None

    def add_event(
        self, event_type: str, data: Dict[str, Any], timestamp: Optional[str] = None
    ) -> SessionEvent:
        """Add an event to the session.

        WHY: Centralizes event processing logic including categorization
        and metric updates.
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat() + "Z"

        # Categorize the event
        category = self._categorize_event(event_type, data)

        # Create the event
        event = SessionEvent(
            timestamp=timestamp,
            event_type=event_type,
            category=category,
            data=data,
            session_id=self.session_id,
            agent_context=self.current_agent,
        )

        self.events.append(event)

        # Update metrics
        self.metrics.total_events += 1
        self.metrics.event_counts[event_type] = (
            self.metrics.event_counts.get(event_type, 0) + 1
        )

        # Process specific event types
        self._process_event(event)

        return event

    def _categorize_event(self, event_type: str, data: Dict[str, Any]) -> EventCategory:
        """Categorize an event based on its type and data.

        WHY: Categories help with filtering and analysis of related events.
        """
        # Check event type patterns
        if "prompt" in event_type.lower() or event_type == "user_input":
            return EventCategory.PROMPT
        if "delegation" in event_type.lower() or event_type == "Task":
            return EventCategory.DELEGATION
        if "tool" in event_type.lower() or event_type in [
            "PreToolUse",
            "PostToolUse",
        ]:
            return EventCategory.TOOL
        if (
            "file" in event_type.lower()
            or "write" in event_type.lower()
            or "read" in event_type.lower()
        ):
            return EventCategory.FILE
        if "todo" in event_type.lower():
            return EventCategory.TODO
        if "response" in event_type.lower() or event_type in ["Stop", "SubagentStop"]:
            return EventCategory.RESPONSE
        if "memory" in event_type.lower():
            return EventCategory.MEMORY
        if "status" in event_type.lower() or "session" in event_type.lower():
            return EventCategory.STATUS
        return EventCategory.SYSTEM

    def _process_event(self, event: SessionEvent):
        """Process specific event types to update session state.

        WHY: Different event types require different processing to maintain
        accurate session state and correlations.
        """
        event_type = event.event_type
        data = event.data

        # Track user prompts
        if event.category == EventCategory.PROMPT:
            if not self.initial_prompt and "prompt" in data:
                self.initial_prompt = data["prompt"]

        # Track agent delegations
        elif event_type == "Task" or "delegation" in event_type.lower():
            agent_type = data.get("agent_type", "unknown")
            self.current_agent = agent_type
            self.metrics.agents_used.add(agent_type)

            # Create new delegation
            delegation = AgentDelegation(
                agent_type=agent_type,
                task_description=data.get("description", ""),
                start_time=event.timestamp,
                prompt=data.get("prompt"),
            )
            self.delegations.append(delegation)
            self.active_delegation = delegation
            self.metrics.total_delegations += 1

        # Track tool operations
        elif event_type == "PreToolUse":
            tool_name = data.get("tool_name", "unknown")
            self.metrics.tools_used.add(tool_name)
            self.metrics.total_tool_calls += 1

            # Create pending tool operation
            tool_op = ToolOperation(
                tool_name=tool_name,
                agent_type=self.current_agent or "unknown",
                start_time=event.timestamp,
                input_data=data.get("tool_input"),
            )

            # Store with correlation ID if available
            correlation_id = f"{event.session_id}:{tool_name}:{event.timestamp}"
            self.pending_tool_operations[correlation_id] = tool_op
            event.correlation_id = correlation_id

            # Add to active delegation if exists
            if self.active_delegation:
                self.active_delegation.tool_operations.append(tool_op)

        elif event_type == "PostToolUse":
            # Match with pending tool operation
            tool_name = data.get("tool_name", "unknown")

            # Find matching pending operation
            for corr_id, tool_op in list(self.pending_tool_operations.items()):
                if tool_op.tool_name == tool_name and not tool_op.end_time:
                    tool_op.end_time = event.timestamp
                    tool_op.output_data = data.get("tool_output")
                    tool_op.success = data.get("success", True)
                    tool_op.error = data.get("error")

                    # Calculate duration
                    try:
                        start = datetime.fromisoformat(
                            tool_op.start_time.replace("Z", "+00:00")
                        )
                        end = datetime.fromisoformat(
                            event.timestamp.replace("Z", "+00:00")
                        )
                        tool_op.duration_ms = int((end - start).total_seconds() * 1000)
                    except Exception:
                        pass

                    event.correlation_id = corr_id
                    del self.pending_tool_operations[corr_id]
                    break

        # Track file operations
        elif event.category == EventCategory.FILE:
            file_path = data.get("file_path") or data.get("path") or data.get("file")
            if file_path:
                self.metrics.files_modified.add(file_path)
                self.metrics.total_file_operations += 1

                if self.active_delegation:
                    self.active_delegation.file_changes.append(file_path)

        # Track responses
        elif event_type in ["Stop", "SubagentStop"]:
            response = (
                data.get("response") or data.get("content") or data.get("message")
            )
            if response:
                if event_type == "SubagentStop" and self.active_delegation:
                    self.active_delegation.response = response
                    self.active_delegation.end_time = event.timestamp
                    self.active_delegation = None
                elif event_type == "Stop":
                    self.final_response = response

        # Track todo updates
        elif event.category == EventCategory.TODO:
            if self.active_delegation and "todos" in data:
                self.active_delegation.todos_modified.append(data["todos"])

        # Track memory updates
        elif event.category == EventCategory.MEMORY and self.active_delegation:
            self.active_delegation.memory_updates.append(data)

    def finalize(self):
        """Finalize the session by calculating final metrics.

        WHY: Some metrics can only be calculated after all events are processed.
        """
        if not self.end_time and self.events:
            self.end_time = self.events[-1].timestamp

        # Calculate session duration
        if self.start_time and self.end_time:
            try:
                start = datetime.fromisoformat(self.start_time.replace("Z", "+00:00"))
                end = datetime.fromisoformat(self.end_time.replace("Z", "+00:00"))
                self.metrics.session_duration_ms = int(
                    (end - start).total_seconds() * 1000
                )
            except Exception:
                pass

        # Finalize any pending delegations
        for delegation in self.delegations:
            if not delegation.end_time:
                delegation.end_time = self.end_time
                delegation.success = False
                delegation.error = "Delegation did not complete"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "working_directory": self.working_directory,
            "launch_method": self.launch_method,
            "initial_prompt": self.initial_prompt,
            "final_response": self.final_response,
            "events": [e.to_dict() for e in self.events],
            "delegations": [d.to_dict() for d in self.delegations],
            "metrics": self.metrics.to_dict(),
            "metadata": {
                "claude_pid": self.claude_pid,
                "git_branch": self.git_branch,
                "project_root": self.project_root,
            },
        }

    def save_to_file(self, directory: Optional[str] = None) -> str:
        """Save the session to a JSON file.

        WHY: Persistent storage allows for later analysis and debugging.

        Args:
            directory: Directory to save to (defaults to .claude-mpm/sessions/)

        Returns:
            Path to the saved file
        """
        if directory is None:
            directory = Path.cwd() / ".claude-mpm" / "sessions"
        else:
            directory = Path(directory)

        # Create directory if it doesn't exist
        directory.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = self.start_time.replace(":", "-").replace(".", "-")[:19]
        filename = f"session_{self.session_id[:8]}_{timestamp}.json"
        filepath = directory / filename

        # Save to file
        with filepath.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

        return str(filepath)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentSession":
        """Create an AgentSession from a dictionary.

        WHY: Allows loading saved sessions for analysis.
        """
        session = cls(
            session_id=data["session_id"],
            start_time=data["start_time"],
            end_time=data.get("end_time"),
            working_directory=data.get("working_directory", ""),
            launch_method=data.get("launch_method", ""),
            initial_prompt=data.get("initial_prompt"),
            final_response=data.get("final_response"),
        )

        # Restore events
        for event_data in data.get("events", []):
            event = SessionEvent(
                timestamp=event_data["timestamp"],
                event_type=event_data["event_type"],
                category=EventCategory(event_data["category"]),
                data=event_data["data"],
                session_id=event_data.get("session_id"),
                agent_context=event_data.get("agent_context"),
                correlation_id=event_data.get("correlation_id"),
            )
            session.events.append(event)

        # Restore delegations
        for del_data in data.get("delegations", []):
            delegation = AgentDelegation(
                agent_type=del_data["agent_type"],
                task_description=del_data["task_description"],
                start_time=del_data["start_time"],
                end_time=del_data.get("end_time"),
                prompt=del_data.get("prompt"),
                response=del_data.get("response"),
                tool_operations=[
                    ToolOperation(**op) for op in del_data.get("tool_operations", [])
                ],
                file_changes=del_data.get("file_changes", []),
                todos_modified=del_data.get("todos_modified", []),
                memory_updates=del_data.get("memory_updates", []),
                duration_ms=del_data.get("duration_ms"),
                success=del_data.get("success", True),
                error=del_data.get("error"),
            )
            session.delegations.append(delegation)

        # Restore metrics
        metrics_data = data.get("metrics", {})
        session.metrics = SessionMetrics(
            total_events=metrics_data.get("total_events", 0),
            event_counts=metrics_data.get("event_counts", {}),
            agents_used=set(metrics_data.get("agents_used", [])),
            tools_used=set(metrics_data.get("tools_used", [])),
            files_modified=set(metrics_data.get("files_modified", [])),
            total_delegations=metrics_data.get("total_delegations", 0),
            total_tool_calls=metrics_data.get("total_tool_calls", 0),
            total_file_operations=metrics_data.get("total_file_operations", 0),
            session_duration_ms=metrics_data.get("session_duration_ms"),
        )

        # Restore metadata
        metadata = data.get("metadata", {})
        session.claude_pid = metadata.get("claude_pid")
        session.git_branch = metadata.get("git_branch")
        session.project_root = metadata.get("project_root")

        return session

    @classmethod
    def load_from_file(cls, filepath: str) -> "AgentSession":
        """Load a session from a JSON file.

        WHY: Enables analysis of historical sessions.
        """
        with Path(filepath).open(
            encoding="utf-8",
        ) as f:
            data = json.load(f)
        return cls.from_dict(data)
