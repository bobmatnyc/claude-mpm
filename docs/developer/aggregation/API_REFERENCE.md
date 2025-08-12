# Event Aggregator API Reference

## EventAggregator Class

Main service class for capturing and managing agent activity sessions.

### Constructor

```python
class EventAggregator:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8765,
        save_dir: Optional[str] = None
    ):
        """
        Initialize the event aggregator.
        
        Args:
            host: Socket.IO server hostname
            port: Socket.IO server port
            save_dir: Directory for saving sessions (uses config if None)
        """
```

### Methods

#### start()

```python
def start(self) -> None:
    """
    Start the event aggregator service.
    
    Connects to Socket.IO dashboard and begins capturing events.
    Creates activity directory if it doesn't exist.
    
    Raises:
        ConnectionError: If unable to connect to Socket.IO server
        PermissionError: If unable to create activity directory
    """
```

#### stop()

```python
def stop(self) -> None:
    """
    Stop the event aggregator service.
    
    Saves all active sessions before stopping.
    Disconnects from Socket.IO server gracefully.
    """
```

#### get_status()

```python
def get_status(self) -> Dict[str, Any]:
    """
    Get current aggregator status.
    
    Returns:
        Dictionary containing:
        - running: bool
        - connected: bool
        - active_sessions: int
        - total_events: int
        - save_directory: str
        - dashboard_port: int
    """
```

#### list_sessions()

```python
def list_sessions(self) -> List[Dict[str, Any]]:
    """
    List all captured sessions.
    
    Returns:
        List of session metadata dictionaries containing:
        - session_id: str
        - start_time: datetime
        - end_time: Optional[datetime]
        - event_count: int
        - file_path: Path
    """
```

#### get_session()

```python
def get_session(self, session_id: str) -> Optional[AgentSession]:
    """
    Get a specific session by ID.
    
    Args:
        session_id: Session identifier
        
    Returns:
        AgentSession object or None if not found
    """
```

#### export_session()

```python
def export_session(
    self,
    session_id: str,
    output_path: Optional[Path] = None,
    format: str = "full"
) -> Path:
    """
    Export a session to file.
    
    Args:
        session_id: Session identifier
        output_path: Output file path (auto-generated if None)
        format: Export format ('full', 'summary', 'events')
        
    Returns:
        Path to exported file
        
    Raises:
        ValueError: If session not found or invalid format
    """
```

## AgentSession Class

Represents a complete agent activity session.

### Constructor

```python
class AgentSession:
    def __init__(
        self,
        session_id: str,
        start_time: datetime
    ):
        """
        Initialize a new session.
        
        Args:
            session_id: Unique session identifier
            start_time: Session start timestamp
        """
```

### Properties

```python
@property
def duration(self) -> timedelta:
    """Get session duration."""

@property
def is_active(self) -> bool:
    """Check if session is still active."""

@property
def event_count(self) -> int:
    """Get total number of events."""
```

### Methods

#### add_event()

```python
def add_event(
    self,
    event_type: str,
    data: Dict[str, Any],
    timestamp: Optional[str] = None
) -> SessionEvent:
    """
    Add an event to the session.
    
    Args:
        event_type: Type of event (e.g., 'UserPromptSubmit')
        data: Event data dictionary
        timestamp: ISO format timestamp (auto-generated if None)
        
    Returns:
        Created SessionEvent object
    """
```

#### add_delegation()

```python
def add_delegation(
    self,
    agent_type: str,
    instructions: str,
    start_time: datetime
) -> AgentDelegation:
    """
    Add an agent delegation to the session.
    
    Args:
        agent_type: Type of agent (e.g., 'engineer')
        instructions: Delegation instructions/prompt
        start_time: Delegation start timestamp
        
    Returns:
        Created AgentDelegation object
    """
```

#### complete_delegation()

```python
def complete_delegation(
    self,
    agent_type: str,
    end_time: datetime,
    success: bool = True,
    response: Optional[str] = None
) -> None:
    """
    Mark a delegation as complete.
    
    Args:
        agent_type: Type of agent
        end_time: Delegation end timestamp
        success: Whether delegation succeeded
        response: Agent response text
    """
```

#### to_dict()

```python
def to_dict(self) -> Dict[str, Any]:
    """
    Convert session to dictionary for serialization.
    
    Returns:
        Dictionary representation of session
    """
```

#### save()

```python
def save(self, filepath: Path) -> None:
    """
    Save session to JSON file.
    
    Args:
        filepath: Path to save file
        
    Raises:
        IOError: If unable to write file
    """
```

#### load()

```python
@classmethod
def load(cls, filepath: Path) -> 'AgentSession':
    """
    Load session from JSON file.
    
    Args:
        filepath: Path to session file
        
    Returns:
        Loaded AgentSession object
        
    Raises:
        FileNotFoundError: If file doesn't exist
        JSONDecodeError: If file is invalid JSON
    """
```

## SessionEvent Class

Represents a single event within a session.

```python
@dataclass
class SessionEvent:
    timestamp: str
    event_type: str
    category: str
    data: Dict[str, Any]
    session_id: str
    correlation_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
```

## AgentDelegation Class

Represents an agent delegation within a session.

```python
@dataclass
class AgentDelegation:
    agent_type: str
    start_time: datetime
    end_time: Optional[datetime]
    instructions: str
    event_count: int = 0
    tool_operations: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    success: bool = False
    response_preview: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
```

## SessionMetrics Class

Session statistics and metrics.

```python
@dataclass
class SessionMetrics:
    total_events: int = 0
    session_duration_ms: int = 0
    event_breakdown: Dict[str, int] = field(default_factory=dict)
    agents_used: List[str] = field(default_factory=list)
    tools_used: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    total_delegations: int = 0
    successful_delegations: int = 0
    failed_delegations: int = 0
    
    def update(self, event: SessionEvent) -> None:
        """Update metrics based on event."""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
```

## CLI Commands

### aggregate start

```python
def start_aggregator(args) -> int:
    """
    Start the event aggregator service.
    
    Args:
        args: Parsed command arguments
        
    Returns:
        Exit code (0 for success)
    """
```

### aggregate stop

```python
def stop_aggregator(args) -> int:
    """
    Stop the event aggregator service.
    
    Args:
        args: Parsed command arguments
        
    Returns:
        Exit code (0 for success)
    """
```

### aggregate status

```python
def show_status(args) -> int:
    """
    Show aggregator status.
    
    Args:
        args: Parsed command arguments
        
    Returns:
        Exit code (0 for success)
    """
```

### aggregate sessions

```python
def list_sessions(args) -> int:
    """
    List captured sessions.
    
    Args:
        args: Parsed command arguments including:
        - limit: Maximum number to show
        - sort: Sort order (time, events, duration)
        
    Returns:
        Exit code (0 for success)
    """
```

### aggregate view

```python
def view_session(args) -> int:
    """
    View session details.
    
    Args:
        args: Parsed command arguments including:
        - session_id: Session to view
        - verbose: Show full details
        
    Returns:
        Exit code (0 for success)
    """
```

### aggregate export

```python
def export_session(args) -> int:
    """
    Export session to file.
    
    Args:
        args: Parsed command arguments including:
        - session_id: Session to export
        - output: Output file path
        - format: Export format (full, summary, events)
        
    Returns:
        Exit code (0 for success)
    """
```

## Usage Examples

### Python Integration

```python
from claude_mpm.services.event_aggregator import EventAggregator
from claude_mpm.models.agent_session import AgentSession

# Create aggregator
aggregator = EventAggregator()

# Start capturing
aggregator.start()

# Check status
status = aggregator.get_status()
print(f"Active sessions: {status['active_sessions']}")

# List sessions
sessions = aggregator.list_sessions()
for session_info in sessions:
    print(f"Session {session_info['session_id']}: {session_info['event_count']} events")

# Get specific session
session = aggregator.get_session("abc123")
if session:
    print(f"Duration: {session.duration}")
    
# Export session
export_path = aggregator.export_session("abc123", format="summary")
print(f"Exported to {export_path}")

# Stop aggregator
aggregator.stop()
```

### Async Integration

```python
import asyncio
from claude_mpm.services.event_aggregator import EventAggregator

async def monitor_sessions():
    """Monitor active sessions asynchronously."""
    aggregator = EventAggregator()
    aggregator.start()
    
    while True:
        status = aggregator.get_status()
        print(f"Events captured: {status['total_events']}")
        await asyncio.sleep(10)
        
        # Check for completed sessions
        for session_id in aggregator.get_completed_sessions():
            aggregator.export_session(session_id)

# Run async monitoring
asyncio.run(monitor_sessions())
```

### Custom Event Processing

```python
from claude_mpm.models.agent_session import AgentSession

class CustomProcessor:
    """Custom event processor."""
    
    def process_session(self, session: AgentSession):
        """Process a completed session."""
        # Count tool usage
        tool_counts = {}
        for event in session.events:
            if event.category == 'tool':
                tool_name = event.data.get('tool_name')
                tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
        
        # Analyze delegations
        for delegation in session.delegations:
            print(f"Agent {delegation.agent_type}:")
            print(f"  Duration: {delegation.end_time - delegation.start_time}")
            print(f"  Files: {delegation.files_modified}")
        
        return tool_counts

# Load and process session
session = AgentSession.load('.claude-mpm/activity/session_abc.json')
processor = CustomProcessor()
results = processor.process_session(session)
```

## Error Handling

### Common Exceptions

```python
class AggregatorError(Exception):
    """Base exception for aggregator errors."""

class ConnectionError(AggregatorError):
    """Unable to connect to Socket.IO server."""

class SessionNotFoundError(AggregatorError):
    """Requested session does not exist."""

class InvalidFormatError(AggregatorError):
    """Invalid export format specified."""
```

### Error Handling Example

```python
from claude_mpm.services.event_aggregator import (
    EventAggregator,
    ConnectionError,
    SessionNotFoundError
)

try:
    aggregator = EventAggregator()
    aggregator.start()
except ConnectionError as e:
    print(f"Failed to connect: {e}")
    # Try alternative port
    aggregator = EventAggregator(port=8766)
    aggregator.start()

try:
    session = aggregator.get_session("invalid_id")
except SessionNotFoundError:
    print("Session not found")
    # List available sessions
    sessions = aggregator.list_sessions()
    if sessions:
        session = aggregator.get_session(sessions[0]['session_id'])
```

## Configuration Access

```python
from claude_mpm.core.config import Config

# Access aggregator configuration
config = Config()
activity_dir = config.get('event_aggregator.activity_directory')
timeout_mins = config.get('event_aggregator.session_timeout_minutes')
capture_settings = config.get('event_aggregator.capture')

print(f"Activity directory: {activity_dir}")
print(f"Session timeout: {timeout_mins} minutes")
print(f"Capture settings: {capture_settings}")
```