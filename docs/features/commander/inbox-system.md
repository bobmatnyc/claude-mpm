# Inbox System Implementation (Issue #176)

**Status**: ✅ Complete
**Phase**: MPM Commander Phase 2
**Date**: 2026-01-13

## Overview

Implemented a centralized inbox system that aggregates events from all projects, sorted by priority and time. This provides a unified view of all pending events across the MPM Commander system.

## Components Implemented

### 1. Core Inbox Module (`src/claude_mpm/commander/inbox/`)

#### `models.py` - InboxItem Dataclass
- **InboxItem**: Enriches events with project metadata
- Properties:
  - `age`: Timedelta since event creation
  - `age_display`: Human-readable age (e.g., "5m ago", "2h ago", "3d ago")

#### `dedup.py` - Event Deduplication
- **EventDeduplicator**: Prevents duplicate events within a time window
- Features:
  - Configurable deduplication window (default: 60 seconds)
  - Content-based hashing (MD5 of title)
  - Automatic cleanup of expired entries
- Deduplication key format: `{project_id}:{event_type}:{title_hash}`

#### `inbox.py` - Main Inbox Class
- **Inbox**: Central event aggregation and querying
- Features:
  - Multi-level filtering (priority, project, event type)
  - Priority-based sorting (CRITICAL > HIGH > NORMAL > LOW > INFO)
  - Time-based sorting within same priority (oldest first)
  - Pagination support (limit + offset)
  - Project metadata enrichment
  - Session runtime tracking
- **InboxCounts**: Summary statistics by priority level

### 2. REST API (`src/claude_mpm/commander/api/routes/inbox.py`)

#### Endpoints

**GET /api/inbox**
- Returns paginated inbox items with filtering
- Query parameters:
  - `limit` (1-100, default: 50): Maximum items to return
  - `offset` (default: 0): Pagination offset
  - `priority`: Filter by priority (critical, high, normal, low, info)
  - `project_id`: Filter by project
  - `event_type`: Filter by event type
- Response: Array of InboxItemResponse

**GET /api/inbox/counts**
- Returns event count breakdown by priority
- Query parameters:
  - `project_id`: Optional project filter
- Response: InboxCountsResponse with counts per priority

### 3. Integration with FastAPI App

Updated `src/claude_mpm/commander/api/app.py`:
- Added global `inbox` instance
- Initialized in lifespan context manager
- Registered inbox router with `/api` prefix
- Used dependency injection to avoid circular imports

## Testing

### Unit Tests (`tests/commander/test_inbox.py`)

**InboxItem Tests** (5 tests):
- Age calculation accuracy
- Age display formatting (seconds, minutes, hours, days)

**EventDeduplicator Tests** (7 tests):
- First occurrence detection
- Duplicate detection within window
- Different attributes (title, project, event type) handled correctly
- Window expiration behavior
- Deduplication key format

**Inbox Tests** (11 tests):
- Sorting by priority (high to low)
- Sorting by time within same priority (oldest first)
- Filtering by priority, project, event type
- Pagination (limit + offset)
- Project metadata enrichment
- Count calculation (all priorities, by project)
- Deduplication integration

**Total**: 23 tests, all passing ✅

## Architecture Decisions

### 1. Deduplication Strategy
- **Choice**: Content-based hashing with time window
- **Rationale**: Prevents event spam without losing unique events
- **Trade-off**: Short window (60s) balances deduplication vs. latency

### 2. Sorting Strategy
- **Choice**: Priority first, then time
- **Rationale**: Critical events always bubble to top, but within same priority, oldest events get attention first (FIFO)
- **Implementation**: Two-key sort tuple: `(priority_index, created_at)`

### 3. Dependency Injection for API Routes
- **Choice**: Lazy import in dependency function
- **Rationale**: Avoids circular import (routes → app → routes)
- **Pattern**: `get_inbox()` dependency injects global instance

### 4. InboxItem Enrichment
- **Choice**: Separate dataclass instead of extending Event
- **Rationale**: Keeps Event model clean, allows inbox-specific computed properties
- **Benefits**: Age display, project metadata, session runtime tracking

## File Structure

```
src/claude_mpm/commander/
├── inbox/
│   ├── __init__.py          # Exports: Inbox, InboxCounts, InboxItem, EventDeduplicator
│   ├── models.py            # InboxItem with age calculation
│   ├── inbox.py             # Inbox class with filtering/sorting/pagination
│   └── dedup.py             # EventDeduplicator for duplicate prevention
├── api/
│   ├── app.py               # Updated with inbox initialization and router
│   └── routes/
│       └── inbox.py         # REST API endpoints

tests/commander/
└── test_inbox.py            # 23 unit tests for inbox system
```

## Usage Example

```python
from claude_mpm.commander.inbox import Inbox
from claude_mpm.commander.events.manager import EventManager
from claude_mpm.commander.registry import ProjectRegistry

# Initialize components
event_manager = EventManager()
project_registry = ProjectRegistry()
inbox = Inbox(event_manager, project_registry)

# Create events
event_manager.create(
    project_id="proj_123",
    event_type=EventType.ERROR,
    title="Connection failed",
    priority=EventPriority.CRITICAL
)

# Query inbox with filters
items = inbox.get_items(
    limit=20,
    priority=EventPriority.HIGH,
    project_id="proj_123"
)

# Get summary counts
counts = inbox.get_counts()
print(f"Critical: {counts.critical}, Total: {counts.total}")

# Check for duplicates before creating
if inbox.should_create_event("proj_123", EventType.ERROR, "Connection failed"):
    event = event_manager.create(...)
```

## API Usage Example

```bash
# Get all pending events
curl http://localhost:8000/api/inbox?limit=50

# Get critical events only
curl http://localhost:8000/api/inbox?priority=critical

# Get events for specific project
curl http://localhost:8000/api/inbox?project_id=proj_123

# Get event counts
curl http://localhost:8000/api/inbox/counts

# Get counts for specific project
curl http://localhost:8000/api/inbox/counts?project_id=proj_123
```

## Performance Characteristics

- **Inbox.get_items()**: O(n log n) where n = total pending events
  - Filtering: O(n)
  - Sorting: O(n log n)
  - Pagination: O(1)
  - Enrichment: O(m) where m = result set size

- **Inbox.get_counts()**: O(n) where n = pending events

- **EventDeduplicator.is_duplicate()**: O(1) average case
  - Hash lookup: O(1)
  - Cleanup: Amortized O(1)

- **Memory**: O(w) where w = dedup window size × event rate
  - Example: 60s window × 10 events/sec = ~600 entries max

## Integration Points

- **EventManager (#174)**: Creates and stores events
- **ProjectRegistry (#170)**: Provides project metadata for enrichment
- **FastAPI App**: Exposes REST API endpoints
- **Future**: Will integrate with notification system for real-time updates

## Next Steps (Future Enhancements)

1. **WebSocket Support**: Real-time inbox updates
2. **Batch Operations**: Mark multiple events as read/dismissed
3. **Search**: Full-text search across event content
4. **Filters**: Save and reuse filter presets
5. **Analytics**: Event volume trends, response time metrics

## Verification

```bash
# Run all inbox tests
uv run pytest tests/commander/test_inbox.py -v

# Verify FastAPI app loads correctly
uv run python -c "from claude_mpm.commander.api.app import app; print('OK')"
```

---

**Related Issues**:
- #174 - EventManager (dependency)
- #170 - ProjectRegistry (dependency)
- #177 - Next phase component
