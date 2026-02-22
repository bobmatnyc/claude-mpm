# SQLite Messaging Database Migration

## Overview
Successfully migrated Claude MPM's cross-project messaging system from file-based storage (markdown files) to SQLite database storage, implementing GitHub issue #306.

## Implementation Summary

### 1. Database Module (`messaging_db.py`)
- **Location**: `src/claude_mpm/services/communication/messaging_db.py`
- **Features**:
  - SQLite with WAL (Write-Ahead Logging) mode for concurrent access
  - Two tables: `sessions` (peer discovery) and `messages` (communication)
  - Efficient querying with indexes on commonly filtered fields
  - JSON serialization for complex fields (metadata, attachments)
  - Session management with heartbeat and cleanup mechanisms
  - Thread-safe connection management with context managers

### 2. Updated MessageService
- **Location**: `src/claude_mpm/services/communication/message_service.py`
- **Changes**:
  - Replaced file I/O operations with database operations
  - Maintains same public API for backward compatibility
  - Per-project database: `.claude-mpm/messaging.db`
  - Global session registry: `~/.claude-mpm/session-registry.db`
  - All existing CLI commands continue to work without changes

### 3. Migration Script
- **Location**: `src/claude_mpm/migrations/migrate_messages_to_db.py`
- **Features**:
  - Migrates existing markdown messages to SQLite
  - Handles inbox, outbox, and archive directories
  - Preserves all message data and metadata
  - Can be run safely multiple times (idempotent)
  - Supports both single project and recursive migration

### 4. Test Coverage
- **Database Tests**: 16 tests in `test_messaging_db.py`
  - Table creation and WAL mode verification
  - CRUD operations for messages and sessions
  - Concurrent access testing
  - JSON serialization/deserialization
  - Index performance validation

- **Integration Tests**: 8 tests in `test_message_service_integration.py`
  - End-to-end messaging between projects
  - Message persistence across service instances
  - Filtering by agent and priority
  - Session registry functionality

- **Total**: 38 tests pass (including existing TaskInjector tests)

## Database Schema

### Messages Table
```sql
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    from_project TEXT NOT NULL,
    from_agent TEXT NOT NULL DEFAULT 'pm',
    to_project TEXT NOT NULL,
    to_agent TEXT NOT NULL DEFAULT 'pm',
    message_type TEXT NOT NULL DEFAULT 'notification',
    priority TEXT NOT NULL DEFAULT 'normal',
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'unread',
    created_at TEXT NOT NULL,
    read_at TEXT,
    replied_to TEXT,
    task_injected INTEGER NOT NULL DEFAULT 0,
    metadata TEXT,  -- JSON
    attachments TEXT -- JSON
)
```

### Sessions Table
```sql
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    project_path TEXT NOT NULL,
    project_name TEXT NOT NULL,
    started_at TEXT NOT NULL,
    last_active TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    pid INTEGER
)
```

## Performance Improvements
- **Concurrent Access**: WAL mode allows multiple readers with one writer
- **Efficient Queries**: Indexes on status, to_project, priority, created_at
- **Batch Operations**: Support for bulk message retrieval
- **Connection Pooling**: Context manager ensures proper resource management

## Migration Path
For existing installations:
```bash
# Migrate current project
python -m claude_mpm.migrations.migrate_messages_to_db

# Migrate all projects recursively
python -m claude_mpm.migrations.migrate_messages_to_db ~/projects --recursive

# Force re-migration (if needed)
python -m claude_mpm.migrations.migrate_messages_to_db --force
```

## Backward Compatibility
- All existing CLI commands work unchanged
- Message IDs remain consistent
- File paths and project references preserved
- Old markdown files can be kept or deleted after migration

## Testing
Run tests with:
```bash
# All communication tests
pytest tests/services/communication/ -v

# Just database tests
pytest tests/services/communication/test_messaging_db.py -v

# Integration tests
pytest tests/services/communication/test_message_service_integration.py -v
```

## Key Benefits
1. **Performance**: Database queries are much faster than file I/O
2. **Concurrency**: Multiple Claude instances can safely access messages
3. **Reliability**: ACID properties ensure data integrity
4. **Scalability**: Can handle thousands of messages efficiently
5. **Querying**: Complex filters and aggregations now possible
6. **Maintenance**: Easier to manage than directory structures

## Future Enhancements
- Message compression for old/archived messages
- Full-text search capabilities
- Message threading and conversation tracking
- Analytics and reporting features
- Automatic cleanup policies