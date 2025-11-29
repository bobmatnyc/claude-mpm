"""Unit tests for GitSourceSyncService.

Test Coverage:
- ETag caching (cache hit, cache miss, force refresh)
- Network error handling (timeout, connection error, HTTP errors)
- Cache fallback mechanisms
- File I/O operations (save, load, permissions)
- Agent list management
- URL construction
"""

import json
from pathlib import Path
from unittest import mock

import pytest
import requests

from claude_mpm.services.agents.sources.git_source_sync_service import (
    CacheError,
    ETagCache,
    GitSourceSyncService,
    GitSyncError,
    NetworkError,
)


class TestETagCache:
    """Test ETag cache functionality."""

    def test_empty_cache_on_init(self, tmp_path):
        """Test that new cache starts empty."""
        cache_file = tmp_path / "etags.json"
        cache = ETagCache(cache_file)

        assert cache.get_etag("https://example.com/file.md") is None

    def test_set_and_get_etag(self, tmp_path):
        """Test storing and retrieving ETags."""
        cache_file = tmp_path / "etags.json"
        cache = ETagCache(cache_file)

        url = "https://example.com/research.md"
        etag = '"abc123def456"'  # pragma: allowlist secret

        cache.set_etag(url, etag)
        assert cache.get_etag(url) == etag

    def test_etag_persistence(self, tmp_path):
        """Test that ETags persist across cache instances."""
        cache_file = tmp_path / "etags.json"

        # First instance - store ETag
        cache1 = ETagCache(cache_file)
        cache1.set_etag("https://example.com/test.md", '"etag123"')

        # Second instance - should load from file
        cache2 = ETagCache(cache_file)
        assert cache2.get_etag("https://example.com/test.md") == '"etag123"'

    def test_etag_metadata(self, tmp_path):
        """Test that ETag metadata is stored correctly."""
        cache_file = tmp_path / "etags.json"
        cache = ETagCache(cache_file)

        cache.set_etag("https://example.com/test.md", '"etag123"', file_size=1024)

        # Load raw cache to check metadata
        with cache_file.open() as f:
            data = json.load(f)

        assert "https://example.com/test.md" in data
        entry = data["https://example.com/test.md"]
        assert entry["etag"] == '"etag123"'
        assert entry["file_size"] == 1024
        assert "last_modified" in entry

    def test_invalid_cache_file(self, tmp_path):
        """Test handling of corrupted cache file."""
        cache_file = tmp_path / "etags.json"

        # Write invalid JSON
        cache_file.write_text("not valid json{")

        # Should handle gracefully and return empty cache
        cache = ETagCache(cache_file)
        assert cache.get_etag("https://example.com/test.md") is None

    def test_missing_cache_file(self, tmp_path):
        """Test that missing cache file is handled gracefully."""
        cache_file = tmp_path / "etags.json"

        # Don't create file
        cache = ETagCache(cache_file)

        # Should work without errors
        assert cache.get_etag("https://example.com/test.md") is None

    def test_cache_file_created_on_save(self, tmp_path):
        """Test that cache file is created when saving."""
        cache_file = tmp_path / "subdir" / "etags.json"

        cache = ETagCache(cache_file)
        cache.set_etag("https://example.com/test.md", '"etag"')

        assert cache_file.exists()


class TestGitSourceSyncService:
    """Test GitSourceSyncService functionality."""

    @pytest.fixture
    def service(self, tmp_path):
        """Create service instance with temp cache dir."""
        return GitSourceSyncService(
            source_url="https://raw.githubusercontent.com/test/repo/main",
            cache_dir=tmp_path,
        )

    def test_init_creates_cache_dir(self, tmp_path):
        """Test that initialization creates cache directory."""
        cache_dir = tmp_path / "cache"
        service = GitSourceSyncService(cache_dir=cache_dir)

        assert cache_dir.exists()
        assert service.cache_dir == cache_dir

    def test_init_default_cache_dir(self):
        """Test that default cache directory is set correctly."""
        service = GitSourceSyncService()

        expected_dir = Path.home() / ".claude-mpm" / "cache" / "remote-agents"
        assert service.cache_dir == expected_dir

    def test_source_url_trailing_slash_removed(self, tmp_path):
        """Test that trailing slash is removed from source URL."""
        service = GitSourceSyncService(
            source_url="https://raw.githubusercontent.com/test/repo/main/",
            cache_dir=tmp_path,
        )

        assert service.source_url == "https://raw.githubusercontent.com/test/repo/main"

    def test_get_cached_agents_dir(self, service):
        """Test getting cached agents directory."""
        assert service.get_cached_agents_dir() == service.cache_dir

    @mock.patch("requests.Session.get")
    def test_sync_agents_first_download(self, mock_get, service):
        """Test first sync downloads all agents."""
        # Mock successful HTTP response
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.text = "# Research Agent\n---\nagent_id: research"
        mock_response.headers = {"ETag": '"abc123"'}
        mock_get.return_value = mock_response

        results = service.sync_agents()

        # Should download agents (not cached yet)
        assert len(results["synced"]) > 0
        assert len(results["cached"]) == 0
        assert len(results["failed"]) == 0
        assert results["total_downloaded"] > 0

    @mock.patch("requests.Session.get")
    def test_sync_agents_with_etag_cache_hit(self, mock_get, service, tmp_path):
        """Test that 304 response uses cached content."""
        # First sync - download
        mock_response_200 = mock.MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.text = "# Agent Content"
        mock_response_200.headers = {"ETag": '"abc123"'}
        mock_get.return_value = mock_response_200

        results1 = service.sync_agents()
        assert len(results1["synced"]) > 0

        # Second sync - should get 304
        mock_response_304 = mock.MagicMock()
        mock_response_304.status_code = 304
        mock_get.return_value = mock_response_304

        results2 = service.sync_agents()

        # Should use cache
        assert len(results2["cached"]) > 0
        assert results2["cache_hits"] > 0
        assert len(results2["synced"]) == 0

        # Check that If-None-Match header was sent
        assert mock_get.call_args[1]["headers"]["If-None-Match"] == '"abc123"'

    @mock.patch("requests.Session.get")
    def test_sync_agents_force_refresh(self, mock_get, service):
        """Test force_refresh bypasses ETag cache."""
        # Pre-populate ETag cache
        url = f"{service.source_url}/research.md"
        service.etag_cache.set_etag(url, '"old_etag"')

        # Mock response
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.text = "# Content"
        mock_response.headers = {"ETag": '"new_etag"'}
        mock_get.return_value = mock_response

        results = service.sync_agents(force_refresh=True)

        # Should download even though ETag exists
        assert len(results["synced"]) > 0

        # Check that If-None-Match header was NOT sent
        call_headers = mock_get.call_args[1].get("headers", {})
        assert "If-None-Match" not in call_headers

    @mock.patch("requests.Session.get")
    def test_network_error_handling(self, mock_get, service, tmp_path):
        """Test graceful handling of network failures."""
        # Pre-populate cache for fallback
        cache_file = service.cache_dir / "research.md"
        cache_file.write_text("# Cached Agent")

        # Mock network error
        mock_get.side_effect = requests.exceptions.ConnectionError("Network down")

        results = service.sync_agents()

        # Should record failures
        assert len(results["failed"]) > 0
        assert len(results["synced"]) == 0

    @mock.patch("requests.Session.get")
    def test_http_404_error(self, mock_get, service):
        """Test handling of 404 Not Found."""
        mock_response = mock.MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        results = service.sync_agents()

        # Should record as failed
        assert len(results["failed"]) > 0

    @mock.patch("requests.Session.get")
    def test_partial_sync_success(self, mock_get, service):
        """Test that partial failures don't stop entire sync."""
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count % 2 == 0:
                # Every second request fails
                raise requests.exceptions.Timeout()
            else:
                # Every other request succeeds
                mock_response = mock.MagicMock()
                mock_response.status_code = 200
                mock_response.text = "# Agent"
                mock_response.headers = {"ETag": f'"etag{call_count}"'}
                return mock_response

        mock_get.side_effect = side_effect

        results = service.sync_agents()

        # Should have both successes and failures
        assert len(results["synced"]) > 0
        assert len(results["failed"]) > 0

    @mock.patch("requests.Session.head")
    def test_check_for_updates(self, mock_head, service):
        """Test checking for updates without downloading."""
        # Pre-populate ETag cache
        url = f"{service.source_url}/research.md"
        service.etag_cache.set_etag(url, '"old_etag"')

        # Mock HEAD response with new ETag
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"ETag": '"new_etag"'}
        mock_head.return_value = mock_response

        updates = service.check_for_updates()

        # Should detect update
        assert "research.md" in updates
        assert updates["research.md"] is True

        # Verify HEAD request was used (not GET)
        mock_head.assert_called()

    @mock.patch("requests.Session.head")
    def test_check_for_updates_no_changes(self, mock_head, service):
        """Test check when no updates available."""
        # Pre-populate ETag cache
        url = f"{service.source_url}/research.md"
        service.etag_cache.set_etag(url, '"same_etag"')

        # Mock HEAD response with same ETag
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"ETag": '"same_etag"'}
        mock_head.return_value = mock_response

        updates = service.check_for_updates()

        # Should not detect update
        assert "research.md" in updates
        assert updates["research.md"] is False

    @mock.patch("requests.Session.get")
    def test_download_agent_file(self, mock_get, service):
        """Test downloading single agent file."""
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.text = "# Research Agent Content"
        mock_response.headers = {"ETag": '"abc123"'}
        mock_get.return_value = mock_response

        content = service.download_agent_file("research.md")

        assert content == "# Research Agent Content"
        # Verify file was cached
        cache_file = service.cache_dir / "research.md"
        assert cache_file.exists()

    @mock.patch("requests.Session.get")
    def test_download_agent_file_cache_fallback(self, mock_get, service):
        """Test cache fallback when download fails."""
        # Pre-populate cache
        cache_file = service.cache_dir / "research.md"
        cache_file.write_text("# Cached Content")

        # Mock network error
        mock_get.side_effect = requests.exceptions.Timeout()

        content = service.download_agent_file("research.md")

        # Should return cached content
        assert content == "# Cached Content"

    def test_save_to_cache(self, service):
        """Test saving content to cache."""
        content = "# Agent Content\n---\nagent_id: test"
        service._save_to_cache("test.md", content)

        cache_file = service.cache_dir / "test.md"
        assert cache_file.exists()
        assert cache_file.read_text() == content

    def test_load_from_cache(self, service):
        """Test loading content from cache."""
        # Create cache file
        cache_file = service.cache_dir / "test.md"
        cache_file.write_text("# Cached Content")

        content = service._load_from_cache("test.md")
        assert content == "# Cached Content"

    def test_load_from_cache_missing_file(self, service):
        """Test loading from cache when file doesn't exist."""
        content = service._load_from_cache("nonexistent.md")
        assert content is None

    def test_get_agent_list(self, service):
        """Test getting agent list."""
        agent_list = service._get_agent_list()

        # Should return list of agent filenames
        assert isinstance(agent_list, list)
        assert len(agent_list) > 0
        assert all(name.endswith(".md") for name in agent_list)
        assert "research.md" in agent_list
        assert "engineer.md" in agent_list

    @mock.patch("requests.Session.get")
    def test_etag_update_on_new_content(self, mock_get, service):
        """Test that ETag is updated when new content is downloaded."""
        url = f"{service.source_url}/research.md"

        # First download
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.text = "# Content"
        mock_response.headers = {"ETag": '"etag_v1"'}
        mock_get.return_value = mock_response

        service.download_agent_file("research.md")
        assert service.etag_cache.get_etag(url) == '"etag_v1"'

        # Second download with new ETag
        mock_response.headers = {"ETag": '"etag_v2"'}
        service.download_agent_file("research.md")
        assert service.etag_cache.get_etag(url) == '"etag_v2"'

    def test_cache_directory_creation(self, tmp_path):
        """Test automatic cache directory creation."""
        cache_dir = tmp_path / "nested" / "cache" / "dir"

        service = GitSourceSyncService(cache_dir=cache_dir)

        assert cache_dir.exists()

    @mock.patch("requests.Session.get")
    def test_sync_preserves_encoding(self, mock_get, service):
        """Test that UTF-8 encoding is preserved."""
        # Content with unicode characters
        unicode_content = "# Agent\nDescription: 日本語 中文 한글 emoji 🚀"

        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.text = unicode_content
        mock_response.headers = {"ETag": '"abc"'}
        mock_get.return_value = mock_response

        service.download_agent_file("test.md")

        # Read from cache and verify encoding
        cached = service._load_from_cache("test.md")
        assert cached == unicode_content

    @mock.patch("requests.Session.get")
    def test_timeout_configuration(self, mock_get, service):
        """Test that HTTP requests have timeout configured."""
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.text = "# Content"
        mock_response.headers = {}
        mock_get.return_value = mock_response

        service.download_agent_file("test.md")

        # Verify timeout was set
        assert mock_get.call_args[1]["timeout"] == 30


class TestErrorClasses:
    """Test custom exception classes."""

    def test_git_sync_error(self):
        """Test GitSyncError exception."""
        error = GitSyncError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, Exception)

    def test_network_error(self):
        """Test NetworkError exception."""
        error = NetworkError("Network failure")
        assert str(error) == "Network failure"
        assert isinstance(error, GitSyncError)

    def test_cache_error(self):
        """Test CacheError exception."""
        error = CacheError("Cache failure")
        assert str(error) == "Cache failure"
        assert isinstance(error, GitSyncError)


# Integration-style tests (these could be moved to integration tests)
class TestGitSourceSyncServiceIntegration:
    """Integration tests for full sync workflow."""

    @mock.patch("requests.Session.get")
    def test_full_sync_workflow(self, mock_get, tmp_path):
        """Test complete sync workflow from start to finish."""
        service = GitSourceSyncService(
            source_url="https://raw.githubusercontent.com/test/repo/main",
            cache_dir=tmp_path,
        )

        # First sync - all downloads
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.text = "# Agent Content"
        mock_response.headers = {"ETag": '"etag1"'}
        mock_get.return_value = mock_response

        results1 = service.sync_agents()
        assert results1["total_downloaded"] > 0
        assert results1["cache_hits"] == 0

        # Second sync - all cached (304 responses)
        mock_response.status_code = 304
        results2 = service.sync_agents()
        assert results2["total_downloaded"] == 0
        assert results2["cache_hits"] > 0

        # Third sync - some updates
        def mixed_response(*args, **kwargs):
            url = args[0]
            if "research.md" in url:
                # Updated file
                r = mock.MagicMock()
                r.status_code = 200
                r.text = "# Updated Content"
                r.headers = {"ETag": '"etag2"'}
                return r
            else:
                # Not modified
                r = mock.MagicMock()
                r.status_code = 304
                return r

        mock_get.side_effect = mixed_response
        results3 = service.sync_agents()

        assert results3["total_downloaded"] > 0  # At least one download
        assert results3["cache_hits"] > 0  # At least one cache hit

    @mock.patch("requests.Session.get")
    def test_cache_persistence_across_instances(self, mock_get, tmp_path):
        """Test that cache persists across service instances."""
        # First instance - download agents
        service1 = GitSourceSyncService(
            source_url="https://raw.githubusercontent.com/test/repo/main",
            cache_dir=tmp_path,
        )

        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.text = "# Content"
        mock_response.headers = {"ETag": '"etag1"'}
        mock_get.return_value = mock_response

        results1 = service1.sync_agents()
        assert results1["total_downloaded"] > 0

        # Second instance - should use cached data
        service2 = GitSourceSyncService(
            source_url="https://raw.githubusercontent.com/test/repo/main",
            cache_dir=tmp_path,
        )

        mock_response.status_code = 304
        results2 = service2.sync_agents()

        # Should use cache from first instance
        assert results2["cache_hits"] > 0
        assert results2["total_downloaded"] == 0


class TestETagCacheErrorHandling:
    """Test ETag cache error handling edge cases."""

    def test_cache_save_permission_error(self, tmp_path, monkeypatch):
        """Test handling of permission errors when saving cache."""
        cache_file = tmp_path / "etags.json"
        cache = ETagCache(cache_file)

        # Mock open to raise PermissionError
        import builtins
        original_open = builtins.open

        def mock_open(*args, **kwargs):
            if str(cache_file) in str(args[0]) and "w" in args[1]:
                raise PermissionError("Permission denied")
            return original_open(*args, **kwargs)

        monkeypatch.setattr("builtins.open", mock_open)

        # Should handle gracefully without raising
        cache.set_etag("https://example.com/test.md", '"etag"')

    def test_cache_save_io_error(self, tmp_path, monkeypatch):
        """Test handling of IO errors when saving cache."""
        cache_file = tmp_path / "etags.json"
        cache = ETagCache(cache_file)

        # Mock open to raise IOError
        import builtins
        original_open = builtins.open

        def mock_open(*args, **kwargs):
            if str(cache_file) in str(args[0]) and "w" in args[1]:
                raise IOError("Disk full")
            return original_open(*args, **kwargs)

        monkeypatch.setattr("builtins.open", mock_open)

        # Should handle gracefully without raising
        cache.set_etag("https://example.com/test.md", '"etag"')

    def test_cache_load_permission_error(self, tmp_path, monkeypatch):
        """Test handling of permission errors when loading cache."""
        cache_file = tmp_path / "etags.json"
        cache_file.write_text('{"test": "data"}')

        # Mock open to raise PermissionError
        import builtins
        original_open = builtins.open

        def mock_open(*args, **kwargs):
            if str(cache_file) in str(args[0]) and "r" in args[1]:
                raise PermissionError("Permission denied")
            return original_open(*args, **kwargs)

        monkeypatch.setattr("builtins.open", mock_open)

        # Should handle gracefully and return empty cache
        cache = ETagCache(cache_file)
        assert cache.get_etag("https://example.com/test.md") is None


class TestGitSourceSyncServiceErrorCoverage:
    """Additional tests for error handling coverage."""

    @pytest.fixture
    def service(self, tmp_path):
        """Create service instance with temp cache dir."""
        return GitSourceSyncService(
            source_url="https://raw.githubusercontent.com/test/repo/main",
            cache_dir=tmp_path,
        )

    def test_save_to_cache_permission_error(self, service, monkeypatch):
        """Test handling of permission errors when saving to cache."""
        import builtins
        original_open = builtins.open

        def mock_open(*args, **kwargs):
            if "test.md" in str(args[0]) and "w" in str(kwargs.get("mode", args[1] if len(args) > 1 else "")):
                raise PermissionError("Permission denied")
            return original_open(*args, **kwargs)

        monkeypatch.setattr("builtins.open", mock_open)

        # Should log error but not raise
        service._save_to_cache("test.md", "# Content")

    def test_save_to_cache_io_error(self, service, monkeypatch):
        """Test handling of IO errors when saving to cache."""
        import builtins
        original_open = builtins.open

        def mock_open(*args, **kwargs):
            if "test.md" in str(args[0]) and "w" in str(kwargs.get("mode", args[1] if len(args) > 1 else "")):
                raise IOError("Disk full")
            return original_open(*args, **kwargs)

        monkeypatch.setattr("builtins.open", mock_open)

        # Should log error but not raise
        service._save_to_cache("test.md", "# Content")

    def test_load_from_cache_permission_error(self, service, tmp_path):
        """Test handling of permission errors when loading from cache."""
        # Create cache file first
        cache_file = service.cache_dir / "test.md"
        cache_file.write_text("# Content")

        # Mock Path.read_text to raise PermissionError
        from pathlib import Path
        original_read_text = Path.read_text

        def mock_read_text(self, *args, **kwargs):
            if "test.md" in str(self):
                raise PermissionError("Permission denied")
            return original_read_text(self, *args, **kwargs)

        with mock.patch.object(Path, "read_text", mock_read_text):
            # Should return None without raising
            content = service._load_from_cache("test.md")
            assert content is None

    def test_load_from_cache_io_error(self, service, tmp_path):
        """Test handling of IO errors when loading from cache."""
        # Create cache file first
        cache_file = service.cache_dir / "test.md"
        cache_file.write_text("# Content")

        # Mock Path.read_text to raise IOError
        from pathlib import Path
        original_read_text = Path.read_text

        def mock_read_text(self, *args, **kwargs):
            if "test.md" in str(self):
                raise IOError("Read error")
            return original_read_text(self, *args, **kwargs)

        with mock.patch.object(Path, "read_text", mock_read_text):
            # Should return None without raising
            content = service._load_from_cache("test.md")
            assert content is None

    def test_load_from_cache_generic_exception(self, service, tmp_path):
        """Test handling of generic exceptions when loading from cache."""
        # Create cache file first
        cache_file = service.cache_dir / "test.md"
        cache_file.write_text("# Content")

        # Mock Path.read_text to raise generic Exception
        from pathlib import Path
        original_read_text = Path.read_text

        def mock_read_text(self, *args, **kwargs):
            if "test.md" in str(self):
                raise Exception("Unexpected error")
            return original_read_text(self, *args, **kwargs)

        with mock.patch.object(Path, "read_text", mock_read_text):
            # Should return None without raising
            content = service._load_from_cache("test.md")
            assert content is None

    def test_save_to_cache_generic_exception(self, service, tmp_path):
        """Test handling of generic exceptions when saving to cache."""
        from pathlib import Path
        original_write_text = Path.write_text

        def mock_write_text(self, *args, **kwargs):
            if "test.md" in str(self):
                raise Exception("Unexpected error")
            return original_write_text(self, *args, **kwargs)

        with mock.patch.object(Path, "write_text", mock_write_text):
            # Should log error but not raise
            service._save_to_cache("test.md", "# Content")

    @mock.patch("requests.Session.head")
    def test_check_for_updates_network_error(self, mock_head, service):
        """Test check_for_updates with network errors."""
        mock_head.side_effect = requests.exceptions.ConnectionError("Network down")

        updates = service.check_for_updates()

        # Should return False for all agents on network error
        assert all(has_update is False for has_update in updates.values())

    @mock.patch("requests.Session.head")
    def test_check_for_updates_http_error(self, mock_head, service):
        """Test check_for_updates with HTTP errors."""
        mock_response = mock.MagicMock()
        mock_response.status_code = 500
        mock_head.return_value = mock_response

        updates = service.check_for_updates()

        # Should return False on HTTP errors
        assert all(has_update is False for has_update in updates.values())

    @mock.patch("requests.Session.get")
    def test_fetch_with_etag_no_etag_header(self, mock_get, service):
        """Test fetch when server doesn't return ETag header."""
        mock_response = mock.MagicMock()
        mock_response.status_code = 200
        mock_response.text = "# Content"
        mock_response.headers = {}  # No ETag
        mock_get.return_value = mock_response

        content, status = service._fetch_with_etag("https://example.com/test.md")

        assert status == 200
        assert content == "# Content"

    @mock.patch("requests.Session.get")
    def test_sync_agents_unexpected_exception(self, mock_get, service):
        """Test sync_agents with unexpected exceptions."""
        mock_get.side_effect = Exception("Unexpected error")

        results = service.sync_agents()

        # Should record as failed
        assert len(results["failed"]) > 0
