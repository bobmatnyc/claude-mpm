# Agent Sync Internals

Developer guide to Claude MPM's git-based agent synchronization system.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Core Components](#core-components)
- [Database Schema](#database-schema)
- [API Reference](#api-reference)
- [Testing Guidelines](#testing-guidelines)
- [Contributing](#contributing)

## Architecture Overview

The agent synchronization system consists of three main layers:

```
┌─────────────────────────────────────────────────────────────┐
│                     Integration Layer                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  startup_sync.py                                     │   │
│  │  - Integrates sync into Claude MPM startup flow     │   │
│  │  - Manages configuration loading                    │   │
│  │  - Handles errors gracefully (non-blocking)         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                      Service Layer                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  GitSourceSyncService                                │   │
│  │  - ETag-based HTTP caching                          │   │
│  │  - File download and validation                     │   │
│  │  - SHA-256 content hashing                          │   │
│  │  - Cache management                                 │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                      Storage Layer                           │
│  ┌─────────────────────┐      ┌─────────────────────────┐   │
│  │  AgentSyncState     │      │  ETagCache             │   │
│  │  - SQLite database  │      │  - JSON file storage   │   │
│  │  - Sync history     │      │  - HTTP ETags          │   │
│  │  - Content hashes   │      │  - Last modified       │   │
│  └─────────────────────┘      └─────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Non-Blocking**: Sync failures never prevent Claude MPM startup
2. **Efficient**: ETag caching minimizes network usage
3. **Resilient**: Graceful degradation to cached agents when offline
4. **Simple**: Connection-per-operation pattern for SQLite
5. **Testable**: Comprehensive test coverage with mocked dependencies

## Core Components

### 1. GitSourceSyncService

Main service for syncing agents from Git repositories.

**File**: `src/claude_mpm/services/agents/sources/git_source_sync_service.py`

**Responsibilities**:
- Fetch repository contents via GitHub API
- Download agent files using ETag-based caching
- Verify content integrity with SHA-256 hashes
- Manage local file cache
- Coordinate with AgentSyncState and ETagCache

**Key Methods**:

```python
class GitSourceSyncService:
    def __init__(
        self,
        cache_dir: Path,
        state: AgentSyncState,
        etag_cache: ETagCache
    ):
        """Initialize sync service.

        Args:
            cache_dir: Local directory for cached agent files
            state: SQLite state tracking service
            etag_cache: ETag cache for HTTP optimization
        """

    def sync_from_source(
        self,
        source_url: str,
        branch: str = "main"
    ) -> Dict[str, Any]:
        """Sync agents from Git repository.

        Args:
            source_url: GitHub repository URL
            branch: Git branch to sync from

        Returns:
            {
                "downloaded": int,    # New/updated files
                "cached": int,        # Unchanged files (cache hit)
                "errors": [],         # Error messages
                "duration_ms": int    # Sync duration
            }

        Raises:
            NetworkError: Network/HTTP failures
            CacheError: Cache read/write failures
        """

    def _fetch_repository_contents(
        self,
        repo_url: str,
        branch: str
    ) -> List[Dict[str, Any]]:
        """Fetch repository file listing from GitHub API.

        Args:
            repo_url: GitHub repository URL
            branch: Git branch

        Returns:
            List of file metadata dicts from GitHub API

        Raises:
            NetworkError: GitHub API request failed
        """

    def _download_file(
        self,
        file_url: str,
        local_path: Path
    ) -> bool:
        """Download single file with ETag caching.

        Args:
            file_url: Raw file URL
            local_path: Where to save file

        Returns:
            True if downloaded, False if cached (304)

        Raises:
            NetworkError: Download failed
        """
```

**Error Handling Philosophy**:
- Network errors: Log warning, continue with cached agents
- GitHub rate limiting: Return partial results, log error
- File corruption: Delete and re-download
- Cache errors: Fall back to re-downloading

---

### 2. AgentSyncState

SQLite-based state tracking service.

**File**: `src/claude_mpm/services/agents/sources/agent_sync_state.py`

**Responsibilities**:
- Manage SQLite connection lifecycle
- Track per-file content hashes (SHA-256)
- Record sync history with timestamps
- Query file change status
- Provide migration utilities

**Database Location**: `~/.config/claude-mpm/agent_sync.db`

**Key Methods**:

```python
class AgentSyncState:
    SCHEMA_VERSION = 1

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize sync state service.

        Args:
            db_path: Custom database path (default: ~/.config/claude-mpm/agent_sync.db)
        """

    def record_sync(
        self,
        source_url: str,
        file_path: str,
        content_hash: str,
        etag: Optional[str] = None
    ):
        """Record successful sync of a file.

        Args:
            source_url: Repository URL
            file_path: Relative path in repository
            content_hash: SHA-256 hash of content
            etag: HTTP ETag value

        Thread Safety: Uses connection-per-operation pattern
        """

    def get_file_state(
        self,
        source_url: str,
        file_path: str
    ) -> Optional[Dict[str, Any]]:
        """Get sync state for specific file.

        Args:
            source_url: Repository URL
            file_path: Relative path in repository

        Returns:
            {
                "content_hash": str,
                "etag": str,
                "synced_at": str (ISO timestamp)
            }
            or None if never synced
        """

    def has_file_changed(
        self,
        source_url: str,
        file_path: str,
        new_hash: str
    ) -> bool:
        """Check if file content has changed.

        Args:
            source_url: Repository URL
            file_path: Relative path in repository
            new_hash: New SHA-256 hash to compare

        Returns:
            True if hash differs from stored hash
        """
```

**Schema Design Decisions**:

1. **Connection-per-operation**: Simplifies management, prevents leaks
2. **Foreign keys enabled**: Enforces referential integrity
3. **Row factory**: Enables dict-like access to results
4. **Indexes**: Optimized for sync_history lookups
5. **Text timestamps**: ISO 8601 format for readability

---

### 3. ETagCache

JSON-based ETag storage for HTTP caching.

**File**: `src/claude_mpm/services/agents/sources/git_source_sync_service.py` (nested class)

**Responsibilities**:
- Store HTTP ETag values for URLs
- Track last modified timestamps
- Enable conditional HTTP requests

**Storage Location**: `~/.claude-mpm/cache/remote-agents/.etag_cache.json`

**Key Methods**:

```python
class ETagCache:
    def __init__(self, cache_file: Path):
        """Initialize ETag cache.

        Args:
            cache_file: JSON file path for ETag storage
        """

    def get_etag(self, url: str) -> Optional[str]:
        """Retrieve stored ETag for URL.

        Args:
            url: URL to look up

        Returns:
            ETag string or None
        """

    def set_etag(
        self,
        url: str,
        etag: str,
        file_size: Optional[int] = None
    ):
        """Store ETag for URL.

        Args:
            url: URL to store ETag for
            etag: ETag value
            file_size: Optional file size in bytes
        """
```

**Design Decision: JSON vs SQLite**

We chose JSON for ETag storage instead of SQLite:

**Rationale**:
- ETags are small text strings (20-40 chars)
- Typically <100 ETags for agent sync
- Human-readable format aids debugging
- File I/O is fast enough for this scale

**Trade-offs**:
- ✅ Simplicity: No schema management
- ✅ Debuggability: Can inspect with `cat`
- ✅ Performance: <1ms for 100 ETags
- ❌ Scalability: Would degrade at >1000 ETags

**Extension Point**: Can migrate to SQLite if ETag count grows significantly.

---

### 4. Startup Integration

Integrates sync into Claude MPM startup flow.

**File**: `src/claude_mpm/services/agents/startup_sync.py`

**Key Function**:

```python
def sync_agents_on_startup(
    config: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Synchronize agents on Claude MPM startup.

    Design Decision: Non-blocking integration

    Rationale: Sync failures should not prevent startup.
    Network issues or slow responses shouldn't block core
    functionality. Log errors but continue with cached agents.

    Args:
        config: Configuration dict (defaults to Config singleton)

    Returns:
        {
            "enabled": bool,
            "sources_synced": int,
            "total_downloaded": int,
            "cache_hits": int,
            "errors": [],
            "duration_ms": int
        }

    Error Handling:
    - Configuration errors: Return error result, don't raise
    - Network errors: Log, return partial results
    - Source failures: Continue with other sources
    """
```

**Integration Points**:
- Called from Claude MPM initialization
- Loads config from `~/.claude-mpm/configuration.yaml`
- Uses global Config singleton if not provided
- Non-blocking: Startup continues even if sync fails

## Database Schema

### Tables

#### `sync_history`

Tracks all synced files with content hashes.

```sql
CREATE TABLE IF NOT EXISTS sync_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_url TEXT NOT NULL,
    file_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,  -- SHA-256 hex digest
    etag TEXT,                    -- HTTP ETag value
    synced_at TEXT NOT NULL,      -- ISO 8601 timestamp
    UNIQUE(source_url, file_path) -- One entry per source+file
);

CREATE INDEX idx_sync_history_source
    ON sync_history(source_url);

CREATE INDEX idx_sync_history_file
    ON sync_history(source_url, file_path);
```

**Fields**:
- `id`: Auto-increment primary key
- `source_url`: GitHub repository URL
- `file_path`: Relative path in repository (e.g., "engineer.md")
- `content_hash`: SHA-256 hash of file content (hex string)
- `etag`: HTTP ETag value for caching
- `synced_at`: When file was synced (UTC timestamp)

**Constraints**:
- `UNIQUE(source_url, file_path)`: Only one record per file
- Updates use `INSERT OR REPLACE` pattern

---

#### `source_metadata`

Tracks repository-level sync metadata.

```sql
CREATE TABLE IF NOT EXISTS source_metadata (
    source_url TEXT PRIMARY KEY,
    last_commit_sha TEXT,
    last_sync_at TEXT,
    total_files INTEGER
);

CREATE INDEX idx_source_metadata_sync
    ON source_metadata(last_sync_at);
```

**Fields**:
- `source_url`: GitHub repository URL (primary key)
- `last_commit_sha`: Latest commit SHA synced (future use)
- `last_sync_at`: When source was last synced (UTC)
- `total_files`: Number of files in source

**Usage**:
- Track when sources were last synced
- Enable delta syncs in future (using commit SHA)
- Provide sync status reporting

---

### Queries

**Common Operations**:

```sql
-- Get all synced files for source
SELECT file_path, content_hash, synced_at
FROM sync_history
WHERE source_url = ?
ORDER BY synced_at DESC;

-- Check if file has changed
SELECT content_hash
FROM sync_history
WHERE source_url = ? AND file_path = ?;

-- Get recent syncs
SELECT file_path, synced_at
FROM sync_history
WHERE source_url = ?
ORDER BY synced_at DESC
LIMIT 10;

-- Count files per source
SELECT source_url, COUNT(*) as file_count
FROM sync_history
GROUP BY source_url;

-- Find stale sources (not synced recently)
SELECT source_url, last_sync_at
FROM source_metadata
WHERE datetime(last_sync_at) < datetime('now', '-7 days');
```

**Maintenance**:

```sql
-- Vacuum database (reclaim space)
VACUUM;

-- Analyze for query optimization
ANALYZE;

-- Check integrity
PRAGMA integrity_check;

-- Show database size
SELECT page_count * page_size as size
FROM pragma_page_count(), pragma_page_size();
```

## API Reference

### GitSourceSyncService

#### Constructor

```python
GitSourceSyncService(
    cache_dir: Path,
    state: AgentSyncState,
    etag_cache: ETagCache
)
```

**Parameters**:
- `cache_dir`: Local directory for agent file cache
- `state`: AgentSyncState instance for database tracking
- `etag_cache`: ETagCache instance for HTTP optimization

**Example**:
```python
from pathlib import Path
from claude_mpm.services.agents.sources import (
    GitSourceSyncService,
    AgentSyncState,
)
from claude_mpm.services.agents.sources.git_source_sync_service import ETagCache

cache_dir = Path("~/.claude-mpm/cache/agents").expanduser()
state = AgentSyncState()
etag_cache = ETagCache(cache_dir / ".etag_cache.json")

service = GitSourceSyncService(cache_dir, state, etag_cache)
```

---

#### sync_from_source()

```python
sync_from_source(
    source_url: str,
    branch: str = "main"
) -> Dict[str, Any]
```

**Parameters**:
- `source_url`: GitHub repository URL (e.g., "https://github.com/owner/repo")
- `branch`: Git branch to sync from (default: "main")

**Returns**:
```python
{
    "downloaded": 3,      # Files downloaded (new or updated)
    "cached": 45,         # Files unchanged (cache hit)
    "errors": [],         # List of error messages
    "duration_ms": 127    # Total sync duration in milliseconds
}
```

**Raises**:
- `NetworkError`: GitHub API request failed
- `CacheError`: Cache directory not writable

**Example**:
```python
result = service.sync_from_source(
    "https://github.com/bobmatnyc/claude-mpm-agents"
)

print(f"Downloaded: {result['downloaded']}")
print(f"Cached: {result['cached']}")
print(f"Duration: {result['duration_ms']}ms")
```

---

### AgentSyncState

#### Constructor

```python
AgentSyncState(db_path: Optional[Path] = None)
```

**Parameters**:
- `db_path`: Custom database path (default: `~/.config/claude-mpm/agent_sync.db`)

**Example**:
```python
from claude_mpm.services.agents.sources import AgentSyncState

# Use default location
state = AgentSyncState()

# Use custom location
custom_path = Path("/tmp/agent_sync_test.db")
state = AgentSyncState(db_path=custom_path)
```

---

#### record_sync()

```python
record_sync(
    source_url: str,
    file_path: str,
    content_hash: str,
    etag: Optional[str] = None
)
```

**Parameters**:
- `source_url`: Repository URL
- `file_path`: Relative file path (e.g., "engineer.md")
- `content_hash`: SHA-256 hash (hex string)
- `etag`: HTTP ETag value (optional)

**Example**:
```python
state.record_sync(
    source_url="https://github.com/bobmatnyc/claude-mpm-agents",
    file_path="engineer.md",
    content_hash="abc123...",
    etag='"def456..."'
)
```

---

#### get_file_state()

```python
get_file_state(
    source_url: str,
    file_path: str
) -> Optional[Dict[str, Any]]
```

**Parameters**:
- `source_url`: Repository URL
- `file_path`: Relative file path

**Returns**:
```python
{
    "content_hash": "abc123...",
    "etag": '"def456..."',
    "synced_at": "2025-11-29T10:00:00Z"
}
# or None if never synced
```

**Example**:
```python
file_state = state.get_file_state(
    "https://github.com/bobmatnyc/claude-mpm-agents",
    "engineer.md"
)

if file_state:
    print(f"Last synced: {file_state['synced_at']}")
    print(f"Hash: {file_state['content_hash']}")
else:
    print("File never synced")
```

---

#### has_file_changed()

```python
has_file_changed(
    source_url: str,
    file_path: str,
    new_hash: str
) -> bool
```

**Parameters**:
- `source_url`: Repository URL
- `file_path`: Relative file path
- `new_hash`: New SHA-256 hash to compare

**Returns**: `True` if hash differs from stored hash

**Example**:
```python
from claude_mpm.core.file_utils import get_file_hash

new_hash = get_file_hash(local_file_path)
if state.has_file_changed(source_url, "engineer.md", new_hash):
    print("File has changed - need to update")
else:
    print("File unchanged - use cached version")
```

---

### ETagCache

#### get_etag()

```python
get_etag(url: str) -> Optional[str]
```

**Parameters**:
- `url`: URL to look up ETag for

**Returns**: ETag string or `None` if not cached

**Example**:
```python
etag = etag_cache.get_etag(
    "https://raw.githubusercontent.com/owner/repo/main/agent.md"
)

if etag:
    headers = {"If-None-Match": etag}
    response = requests.get(url, headers=headers)
    if response.status_code == 304:
        print("Not modified - use cached version")
```

---

#### set_etag()

```python
set_etag(
    url: str,
    etag: str,
    file_size: Optional[int] = None
)
```

**Parameters**:
- `url`: URL to store ETag for
- `etag`: ETag value from HTTP response
- `file_size`: Optional file size in bytes

**Example**:
```python
response = requests.get(url)
etag = response.headers.get("ETag")
file_size = len(response.content)

etag_cache.set_etag(url, etag, file_size)
```

## Testing Guidelines

### Test Structure

Tests are organized by component:

```
tests/
├── services/
│   └── agents/
│       └── sources/
│           ├── test_git_source_sync_service.py
│           ├── test_agent_sync_state.py
│           └── test_startup_sync.py
└── integration/
    ├── test_real_git_sync.py
    └── test_startup_integration.py
```

### Unit Tests

**File**: `tests/services/agents/sources/test_git_source_sync_service.py`

**Coverage**:
- ETag cache hit/miss scenarios
- Network error handling
- File download and validation
- SHA-256 hash verification
- Error recovery

**Example Test**:
```python
def test_sync_uses_etag_cache(mock_requests):
    """Test that sync uses ETags for conditional requests."""
    # Setup
    etag = '"abc123"'
    mock_requests.get.return_value.headers = {"ETag": etag}
    mock_requests.get.return_value.status_code = 304  # Not Modified

    # Execute
    result = service.sync_from_source(source_url)

    # Verify
    assert result["cached"] == 1
    assert result["downloaded"] == 0
    mock_requests.get.assert_called_with(
        url,
        headers={"If-None-Match": etag}
    )
```

---

**File**: `tests/services/agents/sources/test_agent_sync_state.py`

**Coverage**:
- Database initialization
- CRUD operations
- Concurrent access
- Migration scenarios
- Integrity checks

**Example Test**:
```python
def test_record_sync_creates_entry(state):
    """Test recording sync creates database entry."""
    state.record_sync(
        source_url="https://github.com/test/repo",
        file_path="test.md",
        content_hash="abc123",
        etag='"def456"'
    )

    file_state = state.get_file_state(
        "https://github.com/test/repo",
        "test.md"
    )

    assert file_state is not None
    assert file_state["content_hash"] == "abc123"
    assert file_state["etag"] == '"def456"'
```

---

### Integration Tests

**File**: `tests/integration/test_real_git_sync.py`

**Purpose**: Test against real GitHub API (optional, requires network)

**Usage**:
```bash
# Run with network access
pytest tests/integration/test_real_git_sync.py

# Skip integration tests
pytest -m "not integration"
```

**Example**:
```python
@pytest.mark.integration
def test_real_github_sync():
    """Test sync against real GitHub repository."""
    service = GitSourceSyncService(cache_dir, state, etag_cache)

    result = service.sync_from_source(
        "https://github.com/bobmatnyc/claude-mpm-agents"
    )

    assert result["downloaded"] + result["cached"] > 0
    assert result["errors"] == []
```

---

### Test Coverage Requirements

**Target**: 93%+ overall coverage (current: 93%)

**Critical Paths**:
- ✅ ETag caching logic
- ✅ Network error handling
- ✅ Database operations
- ✅ File validation
- ✅ Startup integration

**Run Coverage**:
```bash
pytest --cov=src/claude_mpm/services/agents/sources \
       --cov-report=html \
       tests/services/agents/sources/

# View report
open htmlcov/index.html
```

## Contributing

### Adding New Features

#### 1. Multi-Source Support (Ticket 1M-390)

**Required Changes**:
- Update `sync_agents_on_startup()` to process multiple sources
- Implement priority-based conflict resolution
- Add source management CLI commands
- Update tests for multi-source scenarios

**Priority Resolution Algorithm**:
```python
def resolve_conflicts(agents_by_source: Dict[str, List[Agent]]) -> List[Agent]:
    """Resolve conflicts when same agent in multiple sources.

    Args:
        agents_by_source: Dict mapping source priority to agent list

    Returns:
        Merged agent list with conflicts resolved
    """
    merged = {}
    for priority in sorted(agents_by_source.keys()):
        for agent in agents_by_source[priority]:
            # Lower priority number wins
            if agent.name not in merged:
                merged[agent.name] = agent
    return list(merged.values())
```

---

#### 2. GitHub Authentication

**Required Changes**:
- Add `github_token` configuration option
- Update GitHub API requests to use authentication
- Increase rate limit handling
- Add token validation

**Example**:
```python
def _get_github_headers(self) -> Dict[str, str]:
    """Get headers for GitHub API requests."""
    headers = {"Accept": "application/vnd.github.v3+json"}

    if self.config.get("github_token"):
        headers["Authorization"] = f"token {self.config['github_token']}"

    return headers
```

---

#### 3. Sync Interval Configuration

**Required Changes**:
- Add `sync_interval` configuration option
- Implement background sync scheduler
- Add sync status tracking
- Update startup integration

**Example**:
```python
class BackgroundSyncScheduler:
    """Schedule periodic agent syncs."""

    def __init__(self, interval_seconds: int):
        self.interval = interval_seconds
        self.last_sync = None

    def should_sync(self) -> bool:
        """Check if sync is needed."""
        if not self.last_sync:
            return True
        elapsed = time.time() - self.last_sync
        return elapsed >= self.interval
```

### Code Style

Follow project conventions:

```python
# Use type hints
def sync_from_source(self, source_url: str) -> Dict[str, Any]:
    """Sync agents from source."""
    ...

# Document exceptions
def download_file(self, url: str) -> bytes:
    """Download file.

    Raises:
        NetworkError: Download failed
    """
    ...

# Use context managers for resources
with self._get_connection() as conn:
    conn.execute(query, params)
```

### Pull Request Checklist

- [ ] Tests added/updated (93%+ coverage)
- [ ] Documentation updated
- [ ] Type hints added
- [ ] Error handling implemented
- [ ] Logging added for debugging
- [ ] Integration tests pass
- [ ] Code formatted with black
- [ ] Linter passes (ruff)

## Related Documentation

- [Agent Synchronization Guide](../../guides/agent-synchronization.md) - User guide
- [Configuration Reference](../../configuration/reference.md) - Configuration options
- [Testing Guide](../../reference/QA.md) - Testing standards

---

**Last Updated**: 2025-11-29
**Related Ticket**: 1M-382 (Git-based agent synchronization internals)
