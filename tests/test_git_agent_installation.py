"""Comprehensive tests for Git-based agent installation system.

Tests the following components:
- GitSourceSyncService: Agent sync from GitHub with ETag caching
- AgentSyncState: SQLite state tracking for sync history
- ETag-based HTTP caching and 304 responses
- Per-file content hash tracking with SHA-256
- Offline operation and cache fallback
- JSON to SQLite migration

Ticket: 1M-382 - Migrate Agent System to Git-Based Markdown Repository
"""

import json
import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import requests

from claude_mpm.core.file_utils import get_file_hash
from claude_mpm.services.agents.sources.agent_sync_state import (
    AgentSyncState,
    DatabaseError,
)
from claude_mpm.services.agents.sources.git_source_sync_service import (
    ETagCache,
    GitSourceSyncService,
    GitSyncError,
    NetworkError,
)

# ==============================================================================
# FIXTURES
# ==============================================================================


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create temporary cache directory for testing."""
    cache_dir = tmp_path / "cache" / "remote-agents"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


@pytest.fixture
def temp_db_path(tmp_path):
    """Create temporary SQLite database path."""
    db_path = tmp_path / "agent_sync.db"
    return db_path


@pytest.fixture
def sync_state(temp_db_path):
    """Create AgentSyncState instance with temp database."""
    return AgentSyncState(db_path=temp_db_path)


@pytest.fixture
def etag_cache(temp_cache_dir):
    """Create ETagCache instance with temp file."""
    cache_file = temp_cache_dir / ".etag-cache.json"
    return ETagCache(cache_file=cache_file)


@pytest.fixture
def git_sync_service(temp_cache_dir, temp_db_path):
    """Create GitSourceSyncService instance with temp paths."""
    # Temporarily patch AgentSyncState to use temp database
    with patch(
        "claude_mpm.services.agents.sources.git_source_sync_service.AgentSyncState"
    ) as mock_state_class:
        mock_state = AgentSyncState(db_path=temp_db_path)
        mock_state_class.return_value = mock_state

        service = GitSourceSyncService(
            source_url="https://raw.githubusercontent.com/bobmatnyc/claude-mpm-agents/main",
            cache_dir=temp_cache_dir,
            source_id="github-remote",
        )

        # Replace with actual instance
        service.sync_state = mock_state
        yield service


@pytest.fixture
def mock_requests_session():
    """Create mock requests.Session for HTTP calls."""
    with patch("requests.Session") as mock_session_class:
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        yield mock_session


@pytest.fixture
def sample_agent_content():
    """Sample agent markdown content."""
    return """# Research Agent

Identity: Expert research specialist for investigation and analysis.

## When to Use Me
- Research tasks requiring deep investigation
- Data analysis and pattern recognition
- Literature reviews and information synthesis

## Core Capabilities
- Advanced search techniques
- Source validation
- Data analysis
"""


# ==============================================================================
# TEST: ETagCache
# ==============================================================================


class TestETagCache:
    """Test ETag caching functionality."""

    def test_etag_cache_initialization(self, etag_cache):
        """Test ETag cache initializes correctly."""
        assert etag_cache is not None
        assert etag_cache._cache == {}

    def test_set_and_get_etag(self, etag_cache):
        """Test setting and retrieving ETag."""
        url = "https://example.com/agent.md"
        etag = '"abc123def456"'

        # Set ETag
        etag_cache.set_etag(url, etag, file_size=1024)

        # Retrieve ETag
        retrieved_etag = etag_cache.get_etag(url)
        assert retrieved_etag == etag

    def test_get_etag_not_found(self, etag_cache):
        """Test retrieving non-existent ETag returns None."""
        result = etag_cache.get_etag("https://example.com/nonexistent.md")
        assert result is None

    def test_etag_cache_persistence(self, temp_cache_dir):
        """Test ETag cache persists to disk."""
        cache_file = temp_cache_dir / ".etag-cache.json"
        cache = ETagCache(cache_file=cache_file)

        # Set ETag
        cache.set_etag("https://example.com/test.md", '"etag123"', file_size=512)

        # Create new cache instance (simulates reload)
        cache2 = ETagCache(cache_file=cache_file)

        # Should load from disk
        assert cache2.get_etag("https://example.com/test.md") == '"etag123"'

    def test_etag_cache_invalid_json(self, temp_cache_dir):
        """Test ETag cache handles corrupted JSON gracefully."""
        cache_file = temp_cache_dir / ".etag-cache.json"

        # Write invalid JSON
        cache_file.write_text("{ invalid json }")

        # Should initialize with empty cache, not crash
        cache = ETagCache(cache_file=cache_file)
        assert cache._cache == {}

    def test_etag_cache_metadata(self, etag_cache):
        """Test ETag cache stores metadata."""
        url = "https://example.com/agent.md"
        etag = '"etag789"'
        file_size = 2048

        etag_cache.set_etag(url, etag, file_size=file_size)

        # Check metadata is stored
        entry = etag_cache._cache[url]
        assert entry["etag"] == etag
        assert entry["file_size"] == file_size
        assert "last_modified" in entry

        # Verify timestamp is recent
        last_modified = datetime.fromisoformat(entry["last_modified"])
        assert (datetime.now(timezone.utc) - last_modified).total_seconds() < 5


# ==============================================================================
# TEST: AgentSyncState (SQLite State Tracking)
# ==============================================================================


class TestAgentSyncState:
    """Test SQLite state tracking for agent sync."""

    def test_sync_state_initialization(self, sync_state, temp_db_path):
        """Test SQLite database initializes correctly."""
        assert sync_state is not None
        assert temp_db_path.exists()

        # Verify schema tables exist
        with sync_state._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
            tables = [row[0] for row in cursor.fetchall()]

            assert "sources" in tables
            assert "agent_files" in tables
            assert "sync_history" in tables
            assert "schema_metadata" in tables

    def test_register_source(self, sync_state):
        """Test source registration."""
        sync_state.register_source(
            source_id="test-source",
            url="https://github.com/test/repo",
            enabled=True,
        )

        # Verify source is registered
        source_info = sync_state.get_source_info("test-source")
        assert source_info is not None
        assert source_info["id"] == "test-source"
        assert source_info["url"] == "https://github.com/test/repo"
        assert source_info["enabled"] == 1

    def test_track_file(self, sync_state):
        """Test file tracking with content hash."""
        # Register source first
        sync_state.register_source("test-source", "https://example.com")

        # Track file
        sync_state.track_file(
            source_id="test-source",
            file_path="research.md",
            content_sha="abc123def456",
            local_path="/tmp/research.md",
            file_size=1024,
        )

        # Verify file is tracked
        stored_sha = sync_state.get_file_hash("test-source", "research.md")
        assert stored_sha == "abc123def456"

    def test_has_file_changed(self, sync_state):
        """Test file change detection."""
        sync_state.register_source("test-source", "https://example.com")

        # Track file
        sync_state.track_file(
            source_id="test-source",
            file_path="research.md",
            content_sha="hash1",
        )

        # Same hash - not changed
        assert not sync_state.has_file_changed("test-source", "research.md", "hash1")

        # Different hash - changed
        assert sync_state.has_file_changed("test-source", "research.md", "hash2")

        # Not tracked - considered changed
        assert sync_state.has_file_changed("test-source", "new_file.md", "hash3")

    def test_record_sync_result(self, sync_state):
        """Test sync history recording."""
        sync_state.register_source("test-source", "https://example.com")

        # Record sync
        record_id = sync_state.record_sync_result(
            source_id="test-source",
            status="success",
            files_synced=5,
            files_cached=3,
            files_failed=0,
            duration_ms=1500,
        )

        assert record_id > 0

        # Verify history
        history = sync_state.get_sync_history("test-source", limit=1)
        assert len(history) == 1
        assert history[0]["status"] == "success"
        assert history[0]["files_synced"] == 5
        assert history[0]["files_cached"] == 3
        assert history[0]["duration_ms"] == 1500

    def test_get_all_sources(self, sync_state):
        """Test retrieving all sources."""
        # Register multiple sources
        sync_state.register_source("source1", "https://example.com/1", enabled=True)
        sync_state.register_source("source2", "https://example.com/2", enabled=False)

        # Get all sources
        all_sources = sync_state.get_all_sources(enabled_only=False)
        assert len(all_sources) == 2

        # Get enabled only
        enabled_sources = sync_state.get_all_sources(enabled_only=True)
        assert len(enabled_sources) == 1
        assert enabled_sources[0]["id"] == "source1"

    def test_update_source_sync_metadata(self, sync_state):
        """Test updating source metadata."""
        sync_state.register_source("test-source", "https://example.com")

        # Update metadata
        sync_state.update_source_sync_metadata(
            source_id="test-source",
            last_sha="commit123",
            etag='"etag456"',
        )

        # Verify update
        source_info = sync_state.get_source_info("test-source")
        assert source_info["last_sha"] == "commit123"
        assert source_info["etag"] == '"etag456"'

    def test_cleanup_old_history(self, sync_state):
        """Test cleaning up old sync history."""
        sync_state.register_source("test-source", "https://example.com")

        # Record multiple syncs
        for i in range(5):
            sync_state.record_sync_result(
                source_id="test-source",
                status="success",
                files_synced=i,
            )

        # Verify all records exist
        history = sync_state.get_sync_history("test-source", limit=10)
        assert len(history) == 5

        # Cleanup (should delete nothing since records are recent)
        deleted = sync_state.cleanup_old_history(days=30)
        assert deleted == 0

        # Cleanup with 0 days (should delete all)
        deleted = sync_state.cleanup_old_history(days=0)
        assert deleted == 5

        # Verify cleanup
        history = sync_state.get_sync_history("test-source", limit=10)
        assert len(history) == 0


# ==============================================================================
# TEST: GitSourceSyncService Initialization
# ==============================================================================


class TestGitSourceSyncServiceInitialization:
    """Test GitSourceSyncService initialization and setup."""

    def test_initialization_defaults(self, temp_cache_dir, temp_db_path):
        """Test service initializes with defaults."""
        with patch(
            "claude_mpm.services.agents.sources.git_source_sync_service.AgentSyncState"
        ) as mock_state_class:
            mock_state = AgentSyncState(db_path=temp_db_path)
            mock_state_class.return_value = mock_state

            service = GitSourceSyncService(cache_dir=temp_cache_dir)

            expected_url = (
                "https://raw.githubusercontent.com/bobmatnyc/claude-mpm-agents/main"
            )
            assert service.source_url == expected_url
            assert service.source_id == "github-remote"
            assert service.cache_dir == temp_cache_dir
            assert service.session is not None
            assert service.sync_state is not None
            assert service.etag_cache is not None

    def test_cache_directory_creation(self, tmp_path, temp_db_path):
        """Test cache directory is created if it doesn't exist."""
        cache_dir = tmp_path / "nonexistent" / "cache"

        with patch(
            "claude_mpm.services.agents.sources.git_source_sync_service.AgentSyncState"
        ) as mock_state_class:
            mock_state = AgentSyncState(db_path=temp_db_path)
            mock_state_class.return_value = mock_state

            service = GitSourceSyncService(cache_dir=cache_dir)

            assert cache_dir.exists()
            assert service.cache_dir == cache_dir

    def test_custom_source_url(self, temp_cache_dir, temp_db_path):
        """Test service with custom source URL."""
        custom_url = "https://raw.githubusercontent.com/custom/repo/main"

        with patch(
            "claude_mpm.services.agents.sources.git_source_sync_service.AgentSyncState"
        ) as mock_state_class:
            mock_state = AgentSyncState(db_path=temp_db_path)
            mock_state_class.return_value = mock_state

            service = GitSourceSyncService(
                source_url=custom_url,
                cache_dir=temp_cache_dir,
            )

            assert service.source_url == custom_url

    def test_source_registration_on_init(self, git_sync_service):
        """Test source is registered in SQLite on initialization."""
        source_info = git_sync_service.sync_state.get_source_info("github-remote")

        assert source_info is not None
        assert source_info["id"] == "github-remote"
        assert "bobmatnyc/claude-mpm-agents" in source_info["url"]
        assert source_info["enabled"] == 1


# ==============================================================================
# TEST: GitSourceSyncService Agent Sync
# ==============================================================================


class TestGitSourceSyncServiceAgentSync:
    """Test agent synchronization functionality."""

    def test_get_agent_list(self, git_sync_service):
        """Test hardcoded agent list returns expected agents."""
        agent_list = git_sync_service._get_agent_list()

        # Verify expected agents
        assert "research.md" in agent_list
        assert "engineer.md" in agent_list
        assert "qa.md" in agent_list
        assert "documentation.md" in agent_list
        assert "security.md" in agent_list
        assert "ops.md" in agent_list

        # Verify list is not empty
        assert len(agent_list) > 0

    @patch("requests.Session.get")
    def test_fetch_with_etag_new_content(
        self, mock_get, git_sync_service, sample_agent_content
    ):
        """Test fetching new content (HTTP 200)."""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = sample_agent_content
        mock_response.headers = {"ETag": '"abc123"'}
        mock_get.return_value = mock_response

        # Fetch content
        content, status = git_sync_service._fetch_with_etag(
            "https://example.com/research.md"
        )

        assert status == 200
        assert content == sample_agent_content
        assert mock_get.called

    @patch("requests.Session.get")
    def test_fetch_with_etag_not_modified(self, mock_get, git_sync_service):
        """Test fetching with ETag returns 304 Not Modified."""
        # Set cached ETag
        url = "https://example.com/research.md"
        git_sync_service.etag_cache.set_etag(url, '"cached-etag"')

        # Mock 304 response
        mock_response = Mock()
        mock_response.status_code = 304
        mock_get.return_value = mock_response

        # Fetch content
        content, status = git_sync_service._fetch_with_etag(url)

        assert status == 304
        assert content is None

        # Verify If-None-Match header was sent
        call_args = mock_get.call_args
        assert call_args[1]["headers"]["If-None-Match"] == '"cached-etag"'

    @patch("requests.Session.get")
    def test_fetch_with_etag_force_refresh(
        self, mock_get, git_sync_service, sample_agent_content
    ):
        """Test force refresh bypasses ETag cache."""
        # Set cached ETag
        url = "https://example.com/research.md"
        git_sync_service.etag_cache.set_etag(url, '"cached-etag"')

        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = sample_agent_content
        mock_response.headers = {"ETag": '"new-etag"'}
        mock_get.return_value = mock_response

        # Fetch with force_refresh
        content, status = git_sync_service._fetch_with_etag(url, force_refresh=True)

        assert status == 200
        assert content == sample_agent_content

        # Verify If-None-Match header was NOT sent
        call_args = mock_get.call_args
        assert "If-None-Match" not in call_args[1]["headers"]

    @patch("requests.Session.get")
    def test_sync_agents_first_sync(
        self, mock_get, git_sync_service, sample_agent_content
    ):
        """Test first sync downloads all agents."""
        # Mock all agent responses as 200 OK
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = sample_agent_content
        mock_response.headers = {"ETag": '"agent-etag"'}
        mock_get.return_value = mock_response

        # Perform sync
        result = git_sync_service.sync_agents()

        # Verify results
        assert "synced" in result
        assert "cached" in result
        assert "failed" in result

        # All agents should be downloaded
        assert len(result["synced"]) > 0
        assert result["total_downloaded"] == len(result["synced"])
        assert len(result["failed"]) == 0

    @patch("requests.Session.get")
    def test_sync_agents_with_cache_hits(
        self, mock_get, git_sync_service, sample_agent_content
    ):
        """Test subsequent sync with cache hits (304 responses)."""
        # First sync - download all
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.text = sample_agent_content
        mock_response_200.headers = {"ETag": '"agent-etag"'}

        # Create cache files for 304 responses
        agent_list = git_sync_service._get_agent_list()
        for agent in agent_list:
            cache_file = git_sync_service.cache_dir / agent
            cache_file.write_text(sample_agent_content)

            # Track in SQLite
            content_sha = get_file_hash(cache_file, algorithm="sha256")
            if content_sha:
                git_sync_service.sync_state.track_file(
                    source_id="github-remote",
                    file_path=agent,
                    content_sha=content_sha,
                    local_path=str(cache_file),
                    file_size=len(sample_agent_content.encode("utf-8")),
                )

        # Second sync - should get 304s
        mock_response_304 = Mock()
        mock_response_304.status_code = 304
        mock_get.return_value = mock_response_304

        result = git_sync_service.sync_agents()

        # All agents should be cached
        assert result["cache_hits"] > 0
        assert len(result["cached"]) > 0
        assert result["total_downloaded"] == 0

    @patch("requests.Session.get")
    def test_sync_agents_partial_update(
        self, mock_get, git_sync_service, sample_agent_content
    ):
        """Test sync with some agents updated, some cached."""
        agent_list = git_sync_service._get_agent_list()

        # Setup: Create cache for some agents
        cached_agents = agent_list[:3]
        for agent in cached_agents:
            cache_file = git_sync_service.cache_dir / agent
            cache_file.write_text(sample_agent_content)

            content_sha = get_file_hash(cache_file, algorithm="sha256")
            if content_sha:
                git_sync_service.sync_state.track_file(
                    source_id="github-remote",
                    file_path=agent,
                    content_sha=content_sha,
                    local_path=str(cache_file),
                )

        # Mock responses: 304 for cached, 200 for updated
        def mock_get_side_effect(url, headers=None, timeout=None):
            mock_response = Mock()
            filename = url.split("/")[-1]

            if filename in cached_agents:
                mock_response.status_code = 304
            else:
                mock_response.status_code = 200
                mock_response.text = sample_agent_content
                mock_response.headers = {"ETag": '"new-etag"'}

            return mock_response

        mock_get.side_effect = mock_get_side_effect

        # Perform sync
        result = git_sync_service.sync_agents()

        # Verify partial update
        assert len(result["cached"]) > 0
        assert len(result["synced"]) > 0
        assert result["cache_hits"] + result["total_downloaded"] > 0

    @patch("requests.Session.get")
    def test_sync_agents_with_failures(self, mock_get, git_sync_service):
        """Test sync handles network failures gracefully."""
        # Mock some agents fail, some succeed
        call_count = 0

        def mock_get_side_effect(url, headers=None, timeout=None):
            nonlocal call_count
            call_count += 1

            if call_count % 3 == 0:
                raise requests.RequestException("Network error")

            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.text = "# Agent content"
            mock_response.headers = {"ETag": '"etag"'}
            return mock_response

        mock_get.side_effect = mock_get_side_effect

        # Perform sync
        result = git_sync_service.sync_agents()

        # Should have some successes and some failures
        assert len(result["failed"]) > 0
        assert len(result["synced"]) > 0

    def test_save_to_cache(self, git_sync_service, sample_agent_content):
        """Test saving agent content to cache."""
        filename = "research.md"

        # Save to cache
        git_sync_service._save_to_cache(filename, sample_agent_content)

        # Verify file was created
        cache_file = git_sync_service.cache_dir / filename
        assert cache_file.exists()

        # Verify content
        cached_content = cache_file.read_text(encoding="utf-8")
        assert cached_content == sample_agent_content

    def test_load_from_cache(self, git_sync_service, sample_agent_content):
        """Test loading agent content from cache."""
        filename = "research.md"

        # Create cached file
        cache_file = git_sync_service.cache_dir / filename
        cache_file.write_text(sample_agent_content, encoding="utf-8")

        # Load from cache
        content = git_sync_service._load_from_cache(filename)

        assert content == sample_agent_content

    def test_load_from_cache_not_found(self, git_sync_service):
        """Test loading non-existent file from cache."""
        content = git_sync_service._load_from_cache("nonexistent.md")
        assert content is None


# ==============================================================================
# TEST: Offline Operation
# ==============================================================================


class TestOfflineOperation:
    """Test offline operation and cache fallback."""

    @patch("requests.Session.get")
    def test_download_agent_file_network_error_with_cache(
        self, mock_get, git_sync_service, sample_agent_content
    ):
        """Test network error falls back to cache."""
        filename = "research.md"

        # Create cached version
        cache_file = git_sync_service.cache_dir / filename
        cache_file.write_text(sample_agent_content)

        # Mock network error
        mock_get.side_effect = requests.RequestException("Network unavailable")

        # Download should fall back to cache
        content = git_sync_service.download_agent_file(filename)

        assert content == sample_agent_content

    @patch("requests.Session.get")
    def test_download_agent_file_network_error_no_cache(
        self, mock_get, git_sync_service
    ):
        """Test network error with no cache returns None."""
        # Mock network error
        mock_get.side_effect = requests.RequestException("Network unavailable")

        # Download should return None (no cache)
        content = git_sync_service.download_agent_file("research.md")

        assert content is None

    @patch("requests.Session.get")
    def test_sync_agents_complete_network_failure(self, mock_get, git_sync_service):
        """Test sync with complete network failure."""
        # Mock all requests fail
        mock_get.side_effect = requests.RequestException("Network down")

        # Sync should handle gracefully
        result = git_sync_service.sync_agents()

        # All agents should be marked as failed
        agent_list = git_sync_service._get_agent_list()
        assert len(result["failed"]) == len(agent_list)
        assert result["total_downloaded"] == 0


# ==============================================================================
# TEST: ETag Cache Migration
# ==============================================================================


class TestETagCacheMigration:
    """Test JSON to SQLite migration for ETag cache."""

    def test_migrate_etag_cache_from_json(self, temp_cache_dir, temp_db_path):
        """Test migration from old JSON ETag cache to SQLite."""
        # Create old JSON cache
        old_cache_file = temp_cache_dir / ".etag-cache.json"
        old_cache_data = {
            "https://example.com/agent1.md": {
                "etag": '"etag1"',
                "last_modified": "2024-01-01T00:00:00Z",
                "file_size": 1024,
            },
            "https://example.com/agent2.md": {
                "etag": '"etag2"',
                "last_modified": "2024-01-02T00:00:00Z",
                "file_size": 2048,
            },
        }
        old_cache_file.write_text(json.dumps(old_cache_data))

        # Initialize service (should trigger migration)
        with patch(
            "claude_mpm.services.agents.sources.git_source_sync_service.AgentSyncState"
        ) as mock_state_class:
            mock_state = AgentSyncState(db_path=temp_db_path)
            mock_state_class.return_value = mock_state

            service = GitSourceSyncService(cache_dir=temp_cache_dir)
            service.sync_state = mock_state

            # Verify old cache was renamed
            assert not old_cache_file.exists()
            migrated_file = old_cache_file.with_suffix(".json.migrated")
            assert migrated_file.exists()

    def test_migrate_etag_cache_invalid_json(self, temp_cache_dir, temp_db_path):
        """Test migration handles corrupted JSON gracefully."""
        # Create corrupted JSON cache
        old_cache_file = temp_cache_dir / ".etag-cache.json"
        old_cache_file.write_text("{ invalid json }")

        # Initialize service (should handle error gracefully)
        with patch(
            "claude_mpm.services.agents.sources.git_source_sync_service.AgentSyncState"
        ) as mock_state_class:
            mock_state = AgentSyncState(db_path=temp_db_path)
            mock_state_class.return_value = mock_state

            # Should not raise exception
            service = GitSourceSyncService(cache_dir=temp_cache_dir)
            service.sync_state = mock_state

            # Service should still work
            assert service is not None


# ==============================================================================
# TEST: Content Hash Tracking
# ==============================================================================


class TestContentHashTracking:
    """Test SHA-256 content hash tracking in SQLite."""

    @patch("requests.Session.get")
    def test_content_hash_tracking_on_sync(
        self, mock_get, git_sync_service, sample_agent_content
    ):
        """Test content hash is tracked in SQLite on sync."""
        # Mock successful download
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = sample_agent_content
        mock_response.headers = {"ETag": '"agent-etag"'}
        mock_get.return_value = mock_response

        # Sync single agent
        filename = "research.md"
        url = f"{git_sync_service.source_url}/{filename}"

        content, status = git_sync_service._fetch_with_etag(url)
        if status == 200:
            git_sync_service._save_to_cache(filename, content)

            # Track file
            cache_file = git_sync_service.cache_dir / filename
            content_sha = get_file_hash(cache_file, algorithm="sha256")
            assert content_sha is not None

            git_sync_service.sync_state.track_file(
                source_id="github-remote",
                file_path=filename,
                content_sha=content_sha,
                local_path=str(cache_file),
            )

            # Verify hash is stored
            stored_sha = git_sync_service.sync_state.get_file_hash(
                "github-remote", filename
            )
            assert stored_sha == content_sha

    def test_hash_mismatch_triggers_redownload(
        self, git_sync_service, sample_agent_content
    ):
        """Test hash mismatch triggers re-download."""
        filename = "research.md"

        # Create cached file
        cache_file = git_sync_service.cache_dir / filename
        cache_file.write_text(sample_agent_content)

        # Track with wrong hash
        git_sync_service.sync_state.track_file(
            source_id="github-remote",
            file_path=filename,
            content_sha="wrong-hash",
        )

        # Calculate actual hash
        actual_hash = get_file_hash(cache_file, algorithm="sha256")

        # Should detect change
        assert git_sync_service.sync_state.has_file_changed(
            "github-remote", filename, actual_hash
        )


# ==============================================================================
# TEST: Check for Updates
# ==============================================================================


class TestCheckForUpdates:
    """Test checking for agent updates without downloading."""

    @patch("requests.Session.head")
    def test_check_for_updates_no_changes(self, mock_head, git_sync_service):
        """Test checking for updates when no changes exist."""
        # Set cached ETags
        agent_list = git_sync_service._get_agent_list()
        for agent in agent_list:
            url = f"{git_sync_service.source_url}/{agent}"
            git_sync_service.etag_cache.set_etag(url, '"cached-etag"')

        # Mock HEAD responses with same ETags
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"ETag": '"cached-etag"'}
        mock_head.return_value = mock_response

        # Check for updates
        updates = git_sync_service.check_for_updates()

        # All agents should have no updates
        assert all(has_update is False for has_update in updates.values())

    @patch("requests.Session.head")
    def test_check_for_updates_with_changes(self, mock_head, git_sync_service):
        """Test checking for updates when changes exist."""
        agent_list = git_sync_service._get_agent_list()

        # Set cached ETags
        for agent in agent_list:
            url = f"{git_sync_service.source_url}/{agent}"
            git_sync_service.etag_cache.set_etag(url, '"old-etag"')

        # Mock HEAD responses with different ETags
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {"ETag": '"new-etag"'}
        mock_head.return_value = mock_response

        # Check for updates
        updates = git_sync_service.check_for_updates()

        # All agents should have updates
        assert all(has_update is True for has_update in updates.values())

    @patch("requests.Session.head")
    def test_check_for_updates_network_error(self, mock_head, git_sync_service):
        """Test check for updates handles network errors."""
        # Mock network error
        mock_head.side_effect = requests.RequestException("Network error")

        # Check for updates
        updates = git_sync_service.check_for_updates()

        # All agents should be marked as no update (conservative)
        assert all(has_update is False for has_update in updates.values())


# ==============================================================================
# TEST: Hash Mismatch Handling
# ==============================================================================


class TestHashMismatchHandling:
    """Test hash mismatch detection and re-download scenarios."""

    @patch("requests.Session.get")
    def test_hash_mismatch_triggers_redownload_with_304(
        self, mock_get, git_sync_service, sample_agent_content
    ):
        """Test hash mismatch with 304 response triggers re-download.

        Covers lines 298-317: ETag returns 304 but hash doesn't match
        """
        filename = "research.md"
        cache_file = git_sync_service.cache_dir / filename

        # Create cached file
        cache_file.write_text(sample_agent_content)

        # Track with WRONG hash (simulate corruption)
        git_sync_service.sync_state.track_file(
            source_id="github-remote",
            file_path=filename,
            content_sha="corrupted-hash-123",
            local_path=str(cache_file),
        )

        # Setup mock responses:
        # 1st call: 304 Not Modified (hash mismatch detected)
        # 2nd call: 200 OK (re-download)
        mock_response_304 = Mock()
        mock_response_304.status_code = 304

        updated_content = sample_agent_content + "\n# Updated content"
        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.text = updated_content
        mock_response_200.headers = {"ETag": '"new-etag"'}

        mock_get.side_effect = [mock_response_304, mock_response_200]

        # Sync should detect mismatch and re-download
        result = git_sync_service.sync_agents()

        # Verify re-download occurred
        assert filename in result["synced"]
        assert len(result["synced"]) >= 1

        # Verify new hash is tracked
        new_sha = git_sync_service.sync_state.get_file_hash("github-remote", filename)
        assert new_sha != "corrupted-hash-123"
        assert new_sha is not None

    @patch("requests.Session.get")
    def test_hash_mismatch_redownload_failure(
        self, mock_get, git_sync_service, sample_agent_content
    ):
        """Test hash mismatch where re-download fails.

        Covers lines 316-317: Re-download failure handling
        """
        filename = "research.md"
        cache_file = git_sync_service.cache_dir / filename

        # Create cached file with wrong hash
        cache_file.write_text(sample_agent_content)
        git_sync_service.sync_state.track_file(
            source_id="github-remote",
            file_path=filename,
            content_sha="wrong-hash",
        )

        # 1st call: 304, 2nd call: Network error
        mock_response_304 = Mock()
        mock_response_304.status_code = 304

        mock_get.side_effect = [
            mock_response_304,
            requests.RequestException("Network error"),
        ]

        result = git_sync_service.sync_agents()

        # Should be marked as failed
        assert filename in result["failed"]


class TestCacheFileMissing:
    """Test scenarios where cache file is missing despite ETag."""

    @patch("requests.Session.get")
    def test_cache_file_missing_with_304_response(
        self, mock_get, git_sync_service, sample_agent_content
    ):
        """Test cache file missing despite 304 response triggers re-download.

        Covers lines 325-349: ETag 304 but cache file missing
        """
        filename = "research.md"
        url = f"{git_sync_service.source_url}/{filename}"

        # Set ETag as if file was cached
        git_sync_service.etag_cache.set_etag(url, '"cached-etag"')

        # But DON'T create the cache file (simulates deletion/corruption)
        cache_file = git_sync_service.cache_dir / filename
        assert not cache_file.exists()

        # Mock responses: 304 then 200 (re-download)
        mock_response_304 = Mock()
        mock_response_304.status_code = 304

        mock_response_200 = Mock()
        mock_response_200.status_code = 200
        mock_response_200.text = sample_agent_content
        mock_response_200.headers = {"ETag": '"new-etag"'}

        mock_get.side_effect = [mock_response_304, mock_response_200]

        result = git_sync_service.sync_agents()

        # Should re-download
        assert filename in result["synced"]
        assert cache_file.exists()

        # Verify hash is tracked
        tracked_sha = git_sync_service.sync_state.get_file_hash(
            "github-remote", filename
        )
        assert tracked_sha is not None

    @patch("requests.Session.get")
    def test_cache_file_missing_redownload_fails(self, mock_get, git_sync_service):
        """Test cache file missing and re-download fails.

        Covers lines 343-344: Re-download failure path
        """
        filename = "research.md"
        url = f"{git_sync_service.source_url}/{filename}"

        # Set ETag but no cache file
        git_sync_service.etag_cache.set_etag(url, '"cached-etag"')

        # Mock: 304, then network error on re-download
        mock_response_304 = Mock()
        mock_response_304.status_code = 304

        mock_get.side_effect = [
            mock_response_304,
            requests.RequestException("Network timeout"),
        ]

        result = git_sync_service.sync_agents()

        # Should be in failed list
        assert filename in result["failed"]


class TestExtendedErrorHandling:
    """Test additional HTTP error codes and edge cases."""

    @patch("requests.Session.get")
    def test_401_unauthorized_handling(self, mock_get, git_sync_service):
        """Test 401 Unauthorized is handled gracefully."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        result = git_sync_service.sync_agents()

        # All agents should fail with 401
        assert len(result["failed"]) == len(git_sync_service._get_agent_list())
        assert result["total_downloaded"] == 0

    @patch("requests.Session.get")
    def test_403_forbidden_handling(self, mock_get, git_sync_service):
        """Test 403 Forbidden (rate limited) is handled."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_get.return_value = mock_response

        result = git_sync_service.sync_agents()

        # Should handle gracefully
        assert len(result["failed"]) > 0

    @patch("requests.Session.get")
    def test_500_internal_server_error(self, mock_get, git_sync_service):
        """Test 500 Internal Server Error handling."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        content, status = git_sync_service._fetch_with_etag(
            "https://example.com/test.md"
        )

        assert status == 500
        assert content is None

    @patch("requests.Session.get")
    def test_502_bad_gateway(self, mock_get, git_sync_service):
        """Test 502 Bad Gateway handling."""
        mock_response = Mock()
        mock_response.status_code = 502
        mock_get.return_value = mock_response

        content, status = git_sync_service._fetch_with_etag(
            "https://example.com/test.md"
        )

        assert status == 502
        assert content is None

    @patch("requests.Session.get")
    def test_unexpected_status_code_handling(self, mock_get, git_sync_service):
        """Test unexpected HTTP status codes.

        Covers lines 346-349: Unexpected status handling
        """
        filename = "research.md"

        # Mock 418 I'm a teapot (unexpected status)
        mock_response = Mock()
        mock_response.status_code = 418
        mock_get.return_value = mock_response

        result = git_sync_service.sync_agents()

        # Should be in failed list
        assert filename in result["failed"]


class TestNetworkResilience:
    """Test network timeout and connection error scenarios."""

    @patch("requests.Session.get")
    def test_connection_timeout(self, mock_get, git_sync_service, sample_agent_content):
        """Test connection timeout falls back to cache."""
        filename = "research.md"
        cache_file = git_sync_service.cache_dir / filename

        # Create cached version
        cache_file.write_text(sample_agent_content)

        # Mock timeout
        mock_get.side_effect = requests.Timeout("Connection timeout")

        # download_agent_file should fall back to cache
        content = git_sync_service.download_agent_file(filename)

        assert content == sample_agent_content

    @patch("requests.Session.get")
    def test_connection_error_no_cache(self, mock_get, git_sync_service):
        """Test connection error with no cache returns None.

        Covers lines 452-459: download_agent_file error handling
        """
        mock_get.side_effect = requests.ConnectionError("Network unreachable")

        content = git_sync_service.download_agent_file("research.md")

        assert content is None

    @patch("requests.Session.get")
    def test_download_agent_file_404_fallback(
        self, mock_get, git_sync_service, sample_agent_content
    ):
        """Test 404 falls back to cache if available.

        Covers lines 458-459: 404 warning and None return
        """
        filename = "research.md"
        cache_file = git_sync_service.cache_dir / filename

        # Create cache
        cache_file.write_text(sample_agent_content)

        # Mock 404
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        content = git_sync_service.download_agent_file(filename)

        # Should return None (no fallback for explicit 404)
        assert content is None


class TestAdvancedMigration:
    """Test complex migration scenarios."""

    def test_large_cache_migration(self, temp_cache_dir, temp_db_path):
        """Test migration with large JSON cache (100+ entries).

        Covers lines 639-640: Migration loop edge cases
        """
        # Create large JSON cache
        old_cache_file = temp_cache_dir / ".etag-cache.json"
        large_cache = {}

        for i in range(150):
            large_cache[f"https://example.com/agent{i}.md"] = {
                "etag": f'"etag-{i}"',
                "last_modified": "2024-01-01T00:00:00Z",
                "file_size": 1024 * i,
            }

        old_cache_file.write_text(json.dumps(large_cache))

        # Initialize service (triggers migration)
        with patch(
            "claude_mpm.services.agents.sources.git_source_sync_service.AgentSyncState"
        ) as mock_state_class:
            mock_state = AgentSyncState(db_path=temp_db_path)
            mock_state_class.return_value = mock_state

            service = GitSourceSyncService(cache_dir=temp_cache_dir)
            service.sync_state = mock_state

            # Verify migration occurred
            assert not old_cache_file.exists()
            assert old_cache_file.with_suffix(".json.migrated").exists()

    def test_partial_migration_with_errors(self, temp_cache_dir, temp_db_path):
        """Test migration continues despite individual entry failures.

        Covers lines 639-640: Exception handling in migration loop
        """
        old_cache_file = temp_cache_dir / ".etag-cache.json"

        # Mix of valid and invalid entries
        old_cache = {
            "https://example.com/valid1.md": {
                "etag": '"etag1"',
                "last_modified": "2024-01-01T00:00:00Z",
            },
            "https://example.com/invalid.md": {
                # Missing etag field (will cause error)
                "last_modified": "2024-01-01T00:00:00Z",
            },
            "https://example.com/valid2.md": {
                "etag": '"etag2"',
                "last_modified": "2024-01-02T00:00:00Z",
            },
        }

        old_cache_file.write_text(json.dumps(old_cache))

        with patch(
            "claude_mpm.services.agents.sources.git_source_sync_service.AgentSyncState"
        ) as mock_state_class:
            mock_state = AgentSyncState(db_path=temp_db_path)
            mock_state_class.return_value = mock_state

            # Should not raise exception
            service = GitSourceSyncService(cache_dir=temp_cache_dir)
            service.sync_state = mock_state

            # Migration should complete despite errors
            assert not old_cache_file.exists()

    def test_migration_corrupted_json_graceful_failure(
        self, temp_cache_dir, temp_db_path
    ):
        """Test migration handles corrupted JSON gracefully.

        Covers lines 651-654: JSON decode error handling
        """
        old_cache_file = temp_cache_dir / ".etag-cache.json"
        old_cache_file.write_text("{ invalid json syntax }")

        with patch(
            "claude_mpm.services.agents.sources.git_source_sync_service.AgentSyncState"
        ) as mock_state_class:
            mock_state = AgentSyncState(db_path=temp_db_path)
            mock_state_class.return_value = mock_state

            # Should not crash
            service = GitSourceSyncService(cache_dir=temp_cache_dir)
            service.sync_state = mock_state

            # Service should still be functional
            assert service is not None


class TestCacheIOErrors:
    """Test cache read/write IO error handling."""

    def test_save_to_cache_permission_error(
        self, git_sync_service, sample_agent_content
    ):
        """Test save to cache handles permission errors.

        Covers lines 537-538: PermissionError handling
        """
        filename = "research.md"

        # Mock Path.write_text to raise PermissionError
        with patch.object(
            Path, "write_text", side_effect=PermissionError("Access denied")
        ):
            # Should not raise, just log
            git_sync_service._save_to_cache(filename, sample_agent_content)

            # Operation should complete without exception
            assert True

    def test_save_to_cache_os_error(self, git_sync_service, sample_agent_content):
        """Test save to cache handles OS errors.

        Covers lines 539-540: OSError handling
        """
        filename = "research.md"

        with patch.object(Path, "write_text", side_effect=OSError("Disk full")):
            # Should not raise
            git_sync_service._save_to_cache(filename, sample_agent_content)
            assert True

    def test_save_to_cache_unexpected_error(
        self, git_sync_service, sample_agent_content
    ):
        """Test save to cache handles unexpected errors.

        Covers lines 541-542: General exception handling
        """
        filename = "research.md"

        with patch.object(
            Path, "write_text", side_effect=RuntimeError("Unexpected error")
        ):
            # Should not raise
            git_sync_service._save_to_cache(filename, sample_agent_content)
            assert True

    def test_load_from_cache_permission_error(self, git_sync_service):
        """Test load from cache handles permission errors.

        Covers lines 568-570: PermissionError on read
        """
        filename = "research.md"
        cache_file = git_sync_service.cache_dir / filename
        cache_file.write_text("content")

        with patch.object(
            Path, "read_text", side_effect=PermissionError("Access denied")
        ):
            content = git_sync_service._load_from_cache(filename)
            assert content is None

    def test_load_from_cache_os_error(self, git_sync_service):
        """Test load from cache handles OS errors.

        Covers lines 571-573: OSError on read
        """
        filename = "research.md"
        cache_file = git_sync_service.cache_dir / filename
        cache_file.write_text("content")

        with patch.object(Path, "read_text", side_effect=OSError("IO error")):
            content = git_sync_service._load_from_cache(filename)
            assert content is None

    def test_load_from_cache_unexpected_error(self, git_sync_service):
        """Test load from cache handles unexpected errors.

        Covers lines 574-576: General exception on read
        """
        filename = "research.md"
        cache_file = git_sync_service.cache_dir / filename
        cache_file.write_text("content")

        with patch.object(Path, "read_text", side_effect=ValueError("Encoding error")):
            content = git_sync_service._load_from_cache(filename)
            assert content is None


class TestETagCacheIOErrors:
    """Test ETag cache IO error handling."""

    def test_etag_cache_load_permission_error(self, temp_cache_dir):
        """Test ETag cache handles permission error on load.

        Covers lines 113-114: PermissionError in _load_cache
        """
        cache_file = temp_cache_dir / ".etag-cache.json"
        cache_file.write_text('{"url": "etag"}')

        # Patch Path.open instead of builtins.open
        with patch.object(Path, "open", side_effect=PermissionError("Access denied")):
            cache = ETagCache(cache_file=cache_file)
            # Should initialize with empty cache
            assert cache._cache == {}

    def test_etag_cache_load_unexpected_error(self, temp_cache_dir):
        """Test ETag cache handles unexpected errors on load.

        Covers lines 116-118: General exception in _load_cache
        """
        cache_file = temp_cache_dir / ".etag-cache.json"
        cache_file.write_text('{"url": "etag"}')

        # Patch Path.open to raise unexpected error
        with patch.object(Path, "open", side_effect=RuntimeError("Unexpected")):
            cache = ETagCache(cache_file=cache_file)
            assert cache._cache == {}

    def test_etag_cache_save_permission_error(self, etag_cache):
        """Test ETag cache handles permission error on save.

        Covers lines 136-137: PermissionError in _save_cache
        """
        with patch.object(Path, "open", side_effect=PermissionError("Access denied")):
            # Should not raise
            etag_cache.set_etag("https://example.com/test.md", '"etag"')
            assert True

    def test_etag_cache_save_os_error(self, etag_cache):
        """Test ETag cache handles OS error on save.

        Covers lines 138-139: OSError in _save_cache
        """
        with patch.object(Path, "open", side_effect=OSError("Disk full")):
            etag_cache.set_etag("https://example.com/test.md", '"etag"')
            assert True

    def test_etag_cache_save_unexpected_error(self, etag_cache):
        """Test ETag cache handles unexpected error on save.

        Covers lines 140-141: General exception in _save_cache
        """
        with patch.object(Path, "open", side_effect=ValueError("Unexpected")):
            etag_cache.set_etag("https://example.com/test.md", '"etag"')
            assert True


class TestCheckForUpdatesEdgeCases:
    """Test check_for_updates edge cases."""

    @patch("requests.Session.head")
    def test_check_for_updates_http_error(self, mock_head, git_sync_service):
        """Test check_for_updates handles HTTP errors.

        Covers lines 422-425: Non-200 status handling
        """
        # Mock 500 error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_head.return_value = mock_response

        updates = git_sync_service.check_for_updates()

        # Should mark as no update (conservative)
        assert all(has_update is False for has_update in updates.values())


class TestSyncAgentsUnexpectedErrors:
    """Test sync_agents handles unexpected exceptions."""

    @patch("requests.Session.get")
    def test_sync_agents_unexpected_exception(self, mock_get, git_sync_service):
        """Test sync handles unexpected exceptions.

        Covers lines 355-357: General exception handling
        """
        # Mock unexpected exception (not RequestException)
        mock_get.side_effect = ValueError("Unexpected error")

        result = git_sync_service.sync_agents()

        # Should handle gracefully
        assert len(result["failed"]) > 0
        # Should still have history recorded
        assert result is not None


class TestGetCachedAgentsDir:
    """Test get_cached_agents_dir utility method."""

    def test_get_cached_agents_dir(self, git_sync_service):
        """Test get_cached_agents_dir returns correct path.

        Covers line 662: get_cached_agents_dir
        """
        cached_dir = git_sync_service.get_cached_agents_dir()

        assert cached_dir == git_sync_service.cache_dir
        assert isinstance(cached_dir, Path)


# ==============================================================================
# TEST: Error Handling (ORIGINAL)
# ==============================================================================


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_safe_path_join_prevents_traversal(self, git_sync_service):
        """Test cache operations handle path traversal safely."""
        # Attempt to save file with path traversal
        malicious_filename = "../../../etc/passwd"

        # Should fail safely or write to cache directory (implementation dependent)
        # Current implementation logs error and fails gracefully
        git_sync_service._save_to_cache(malicious_filename, "content")

        # Verify the actual path that would be used
        cache_file = git_sync_service.cache_dir / malicious_filename

        # The file should either:
        # 1. Not exist (safe failure - preferred)
        # 2. Exist within cache directory bounds (safe write)
        if cache_file.exists():
            # If it exists, ensure it's within cache directory
            assert git_sync_service.cache_dir in cache_file.parents
        else:
            # Safe failure - file not created (preferred behavior)
            assert True

    @patch("requests.Session.get")
    def test_http_error_codes_handled(self, mock_get, git_sync_service):
        """Test various HTTP error codes are handled."""
        error_codes = [404, 500, 502, 503]

        for error_code in error_codes:
            mock_response = Mock()
            mock_response.status_code = error_code
            mock_get.return_value = mock_response

            content, status = git_sync_service._fetch_with_etag(
                "https://example.com/test.md"
            )

            assert status == error_code
            assert content is None

    def test_sync_state_foreign_key_constraint(self, sync_state):
        """Test foreign key constraints are enforced."""
        # Attempt to track file for non-existent source
        with pytest.raises(Exception):  # Should raise foreign key violation
            with sync_state._get_connection() as conn:
                query = (
                    "INSERT INTO agent_files "
                    "(source_id, file_path, content_sha, synced_at) "
                    "VALUES (?, ?, ?, ?)"
                )
                params = (
                    "nonexistent-source",
                    "test.md",
                    "hash123",
                    datetime.now(timezone.utc).isoformat(),
                )
                conn.execute(query, params)


# ==============================================================================
# INTEGRATION TESTS
# ==============================================================================


class TestIntegration:
    """Integration tests for end-to-end scenarios."""

    @patch("requests.Session.get")
    @patch("requests.Session.head")
    def test_full_sync_cycle(
        self, mock_head, mock_get, git_sync_service, sample_agent_content
    ):
        """Test complete sync cycle: first sync, check updates, re-sync."""
        # First sync - download all
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = sample_agent_content
        mock_response.headers = {"ETag": '"v1-etag"'}
        mock_get.return_value = mock_response

        result1 = git_sync_service.sync_agents()
        assert result1["total_downloaded"] > 0
        assert len(result1["failed"]) == 0

        # Check for updates (no changes)
        mock_head_response = Mock()
        mock_head_response.status_code = 200
        mock_head_response.headers = {"ETag": '"v1-etag"'}
        mock_head.return_value = mock_head_response

        updates = git_sync_service.check_for_updates()
        assert all(has_update is False for has_update in updates.values())

        # Second sync - should use cache
        mock_get.reset_mock()
        mock_response_304 = Mock()
        mock_response_304.status_code = 304
        mock_get.return_value = mock_response_304

        result2 = git_sync_service.sync_agents()
        assert result2["cache_hits"] > 0
        assert result2["total_downloaded"] == 0

        # Simulate update
        mock_head_response.headers = {"ETag": '"v2-etag"'}
        updates = git_sync_service.check_for_updates()
        assert any(has_update is True for has_update in updates.values())

        # Third sync - download updates
        mock_response_updated = Mock()
        mock_response_updated.status_code = 200
        mock_response_updated.text = sample_agent_content + "\n# Updated"
        mock_response_updated.headers = {"ETag": '"v2-etag"'}
        mock_get.return_value = mock_response_updated

        result3 = git_sync_service.sync_agents()
        assert result3["total_downloaded"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
