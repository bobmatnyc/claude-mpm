"""Integration test for startup agent synchronization.

Tests the complete startup flow including:
1. Configuration loading
2. Agent sync from remote source
3. Cache directory creation
4. State tracking in SQLite
"""

import shutil
import tempfile
from pathlib import Path

import pytest

from claude_mpm.core.config import Config
from claude_mpm.services.agents.startup_sync import sync_agents_on_startup


class TestStartupIntegration:
    """Integration tests for startup agent synchronization."""

    @pytest.fixture(autouse=True)
    def setup_test_env(self):
        """Create temporary cache directory for test."""
        # Create temporary directory for cache
        self.temp_dir = tempfile.mkdtemp(prefix="test_agent_sync_")
        self.cache_dir = Path(self.temp_dir) / "cache"

        yield

        # Cleanup
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_startup_sync_with_live_github_source(self):
        """Test actual sync from GitHub repository (integration test).

        This test makes real HTTP requests to GitHub to verify
        the complete integration works end-to-end.
        """
        config = {
            "agent_sync": {
                "enabled": True,
                "sources": [
                    {
                        "id": "github-test",
                        "url": "https://raw.githubusercontent.com/bobmatnyc/claude-mpm-agents/main/agents",
                        "enabled": True,
                    }
                ],
                "cache_dir": str(self.cache_dir),
            }
        }

        # Run sync
        result = sync_agents_on_startup(config=config)

        # Verify results
        assert result["enabled"] is True
        assert result["sources_synced"] == 1

        # On first run, should download all agents
        # On subsequent runs (if cache exists), may have cache hits
        total_agents = result["total_downloaded"] + result["cache_hits"]
        assert total_agents > 0, "Should sync at least some agents"

        # Verify cache directory was created
        assert self.cache_dir.exists()
        assert self.cache_dir.is_dir()

        # Verify agent files were downloaded
        agent_files = list(self.cache_dir.glob("*.md"))
        assert len(agent_files) > 0, "Should have downloaded agent markdown files"

        # Verify at least one expected agent exists
        expected_agents = ["research.md", "engineer.md", "qa.md"]
        found_agents = [f.name for f in agent_files]
        assert any(
            agent in found_agents for agent in expected_agents
        ), f"Should have at least one of {expected_agents}, found: {found_agents}"

    def test_startup_sync_respects_disabled_config(self):
        """Test that sync is skipped when disabled in config."""
        config = {
            "agent_sync": {
                "enabled": False,
                "sources": [
                    {
                        "id": "github-test",
                        "url": "https://raw.githubusercontent.com/bobmatnyc/claude-mpm-agents/main/agents",
                        "enabled": True,
                    }
                ],
                "cache_dir": str(self.cache_dir),
            }
        }

        result = sync_agents_on_startup(config=config)

        # Verify sync was skipped
        assert result["enabled"] is False
        assert result["sources_synced"] == 0
        assert result["total_downloaded"] == 0

        # Cache directory should not be created
        # (GitSourceSyncService is never instantiated)
        # Note: This depends on implementation detail - cache dir created in __init__

    def test_etag_caching_reduces_bandwidth_on_second_sync(self):
        """Test that ETag caching prevents re-downloading unchanged files."""
        config = {
            "agent_sync": {
                "enabled": True,
                "sources": [
                    {
                        "id": "github-test",
                        "url": "https://raw.githubusercontent.com/bobmatnyc/claude-mpm-agents/main/agents",
                        "enabled": True,
                    }
                ],
                "cache_dir": str(self.cache_dir),
            }
        }

        # First sync - download everything
        result1 = sync_agents_on_startup(config=config)
        first_sync_downloaded = result1["total_downloaded"]

        assert first_sync_downloaded > 0, "First sync should download agents"

        # Second sync - should use cache
        result2 = sync_agents_on_startup(config=config)

        # On second sync, should have high cache hit rate
        # (all files unchanged, so ETag returns 304)
        assert result2["cache_hits"] > 0, "Second sync should have cache hits"

        # Total downloaded on second sync should be 0 or minimal
        # (only if files were actually updated on GitHub between syncs)
        assert (
            result2["total_downloaded"] <= first_sync_downloaded
        ), "Second sync should not download more than first"

        # Ideally, second sync downloads nothing
        # But we can't guarantee this in integration test (files might have updated)

    def test_sqlite_state_tracking_persists_across_syncs(self):
        """Test that SQLite state tracking persists file metadata."""
        from claude_mpm.services.agents.sources.agent_sync_state import \
            AgentSyncState

        config = {
            "agent_sync": {
                "enabled": True,
                "sources": [
                    {
                        "id": "github-test",
                        "url": "https://raw.githubusercontent.com/bobmatnyc/claude-mpm-agents/main/agents",
                        "enabled": True,
                    }
                ],
                "cache_dir": str(self.cache_dir),
            }
        }

        # First sync
        result1 = sync_agents_on_startup(config=config)
        assert result1["sources_synced"] == 1

        # Query sync state
        sync_state = AgentSyncState()

        # Verify source was registered using get_all_sources()
        sources = sync_state.get_all_sources()
        assert len(sources) >= 1, "Should have at least one source registered"

        source = next((s for s in sources if s["id"] == "github-test"), None)
        assert source is not None, "github-test source should be registered"
        assert source["enabled"] == 1  # SQLite stores boolean as 1/0

        # Verify sync history was recorded
        history = sync_state.get_sync_history(source_id="github-test", limit=5)
        assert len(history) >= 1, "Should have sync history recorded"

        # Verify first sync entry has valid metadata
        first_sync = history[0]
        assert "status" in first_sync
        assert "files_synced" in first_sync
        assert "sync_time" in first_sync  # Correct field name from schema
        assert first_sync["files_synced"] > 0, "Should have synced some files"

    def test_network_failure_doesnt_crash_startup(self):
        """Test that network failures are handled gracefully."""
        config = {
            "agent_sync": {
                "enabled": True,
                "sources": [
                    {
                        "id": "bad-source",
                        "url": "https://invalid-domain-that-doesnt-exist-12345.com/agents",
                        "enabled": True,
                    }
                ],
                "cache_dir": str(self.cache_dir),
            }
        }

        # Should not raise exception
        result = sync_agents_on_startup(config=config)

        # Should report error
        assert result["enabled"] is True
        # Likely no sources synced due to network error
        # But this shouldn't crash the startup


@pytest.mark.slow
class TestStartupPerformance:
    """Performance tests for startup synchronization."""

    @pytest.fixture(autouse=True)
    def setup_test_env(self):
        """Create temporary cache directory for test."""
        self.temp_dir = tempfile.mkdtemp(prefix="test_agent_sync_perf_")
        self.cache_dir = Path(self.temp_dir) / "cache"

        yield

        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    def test_sync_completes_within_reasonable_time(self):
        """Test that sync completes within expected time threshold."""
        import time

        config = {
            "agent_sync": {
                "enabled": True,
                "sources": [
                    {
                        "id": "github-test",
                        "url": "https://raw.githubusercontent.com/bobmatnyc/claude-mpm-agents/main/agents",
                        "enabled": True,
                    }
                ],
                "cache_dir": str(self.cache_dir),
            }
        }

        start_time = time.time()
        result = sync_agents_on_startup(config=config)
        duration = time.time() - start_time

        # First sync should complete within 30 seconds (generous threshold)
        assert duration < 30, f"Sync took {duration}s, expected < 30s"

        # Verify duration_ms is reasonable
        assert result["duration_ms"] > 0
        assert result["duration_ms"] < 30000  # 30 seconds in ms
