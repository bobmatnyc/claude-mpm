"""Unit tests for agent startup synchronization service.

Tests the startup integration of GitSourceSyncService to ensure
agent templates are synchronized correctly on Claude MPM initialization.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from claude_mpm.services.agents.startup_sync import (get_sync_status,
                                                     sync_agents_on_startup)


class TestSyncAgentsOnStartup:
    """Test suite for sync_agents_on_startup function."""

    def test_sync_disabled_in_config(self):
        """Test that sync is skipped when disabled in configuration."""
        config = {"agent_sync": {"enabled": False}}

        result = sync_agents_on_startup(config=config)

        assert result["enabled"] is False
        assert result["sources_synced"] == 0
        assert result["total_downloaded"] == 0
        assert result["cache_hits"] == 0
        assert len(result["errors"]) == 0

    def test_sync_with_no_sources_configured(self):
        """Test sync behavior when no sources are configured."""
        config = {"agent_sync": {"enabled": True, "sources": []}}

        result = sync_agents_on_startup(config=config)

        assert result["enabled"] is True
        assert result["sources_synced"] == 0
        assert result["total_downloaded"] == 0

    def test_sync_skips_disabled_sources(self):
        """Test that disabled sources are skipped during sync."""
        config = {
            "agent_sync": {
                "enabled": True,
                "sources": [
                    {"id": "source1", "url": "https://example.com", "enabled": False},
                    {"id": "source2", "url": "https://example.com", "enabled": False},
                ],
            }
        }

        result = sync_agents_on_startup(config=config)

        assert result["enabled"] is True
        assert result["sources_synced"] == 0

    def test_sync_skips_sources_without_url(self):
        """Test that sources without URL are skipped with error logged."""
        config = {
            "agent_sync": {
                "enabled": True,
                "sources": [{"id": "bad-source", "enabled": True}],
            }
        }

        result = sync_agents_on_startup(config=config)

        assert result["enabled"] is True
        assert result["sources_synced"] == 0
        assert len(result["errors"]) == 1
        assert "missing URL" in result["errors"][0]

    @patch("claude_mpm.services.agents.startup_sync.GitSourceSyncService")
    def test_successful_single_source_sync(self, mock_sync_service_class):
        """Test successful synchronization of a single source."""
        # Mock sync service instance
        mock_service = MagicMock()
        mock_service.sync_agents.return_value = {
            "synced": ["agent1.md", "agent2.md"],
            "cached": ["agent3.md"],
            "failed": [],
            "total_downloaded": 2,
            "cache_hits": 1,
        }
        mock_sync_service_class.return_value = mock_service

        config = {
            "agent_sync": {
                "enabled": True,
                "sources": [
                    {
                        "id": "github-remote",
                        "url": "https://raw.githubusercontent.com/test/repo/main/agents",
                        "enabled": True,
                    }
                ],
            }
        }

        result = sync_agents_on_startup(config=config)

        assert result["enabled"] is True
        assert result["sources_synced"] == 1
        assert result["total_downloaded"] == 2
        assert result["cache_hits"] == 1
        assert len(result["errors"]) == 0
        assert result["duration_ms"] >= 0  # Can be 0 for very fast mocked execution

        # Verify sync service was called correctly
        mock_sync_service_class.assert_called_once()
        mock_service.sync_agents.assert_called_once_with(force_refresh=False)

    @patch("claude_mpm.services.agents.startup_sync.GitSourceSyncService")
    def test_multiple_sources_sync(self, mock_sync_service_class):
        """Test synchronization with multiple enabled sources."""
        # Mock sync service to return different results for each source
        mock_service = MagicMock()
        mock_service.sync_agents.side_effect = [
            {
                "synced": ["agent1.md"],
                "cached": ["agent2.md"],
                "failed": [],
                "total_downloaded": 1,
                "cache_hits": 1,
            },
            {
                "synced": ["agent3.md"],
                "cached": ["agent4.md"],
                "failed": [],
                "total_downloaded": 1,
                "cache_hits": 1,
            },
        ]
        mock_sync_service_class.return_value = mock_service

        config = {
            "agent_sync": {
                "enabled": True,
                "sources": [
                    {
                        "id": "source1",
                        "url": "https://example.com/source1",
                        "enabled": True,
                    },
                    {
                        "id": "source2",
                        "url": "https://example.com/source2",
                        "enabled": True,
                    },
                ],
            }
        }

        result = sync_agents_on_startup(config=config)

        assert result["enabled"] is True
        assert result["sources_synced"] == 2
        assert result["total_downloaded"] == 2  # 1 + 1
        assert result["cache_hits"] == 2  # 1 + 1
        assert len(result["errors"]) == 0

        # Verify sync service was called twice
        assert mock_service.sync_agents.call_count == 2

    @patch("claude_mpm.services.agents.startup_sync.GitSourceSyncService")
    def test_partial_sync_failure(self, mock_sync_service_class):
        """Test that partial failures are logged but don't stop sync."""
        mock_service = MagicMock()
        mock_service.sync_agents.return_value = {
            "synced": ["agent1.md"],
            "cached": ["agent2.md"],
            "failed": ["agent3.md", "agent4.md"],
            "total_downloaded": 1,
            "cache_hits": 1,
        }
        mock_sync_service_class.return_value = mock_service

        config = {
            "agent_sync": {
                "enabled": True,
                "sources": [
                    {
                        "id": "github-remote",
                        "url": "https://example.com/agents",
                        "enabled": True,
                    }
                ],
            }
        }

        result = sync_agents_on_startup(config=config)

        assert result["enabled"] is True
        assert result["sources_synced"] == 1
        assert len(result["errors"]) == 1
        assert "failed to sync 2 agents" in result["errors"][0]

    @patch("claude_mpm.services.agents.startup_sync.GitSourceSyncService")
    def test_source_exception_doesnt_stop_other_sources(self, mock_sync_service_class):
        """Test that exception in one source doesn't prevent syncing others."""
        mock_service = MagicMock()
        # First call raises exception, second succeeds
        mock_service.sync_agents.side_effect = [
            Exception("Network error"),
            {
                "synced": ["agent1.md"],
                "cached": [],
                "failed": [],
                "total_downloaded": 1,
                "cache_hits": 0,
            },
        ]
        mock_sync_service_class.return_value = mock_service

        config = {
            "agent_sync": {
                "enabled": True,
                "sources": [
                    {
                        "id": "bad-source",
                        "url": "https://example.com/bad",
                        "enabled": True,
                    },
                    {
                        "id": "good-source",
                        "url": "https://example.com/good",
                        "enabled": True,
                    },
                ],
            }
        }

        result = sync_agents_on_startup(config=config)

        assert result["enabled"] is True
        assert result["sources_synced"] == 1  # Only second source succeeded
        assert result["total_downloaded"] == 1
        assert len(result["errors"]) == 1
        assert "bad-source" in result["errors"][0]

    @patch("claude_mpm.services.agents.startup_sync.GitSourceSyncService")
    def test_custom_cache_dir_is_used(self, mock_sync_service_class):
        """Test that custom cache directory from config is used."""
        mock_service = MagicMock()
        mock_service.sync_agents.return_value = {
            "synced": [],
            "cached": [],
            "failed": [],
            "total_downloaded": 0,
            "cache_hits": 0,
        }
        mock_sync_service_class.return_value = mock_service

        custom_cache = "/custom/cache/path"
        config = {
            "agent_sync": {
                "enabled": True,
                "cache_dir": custom_cache,
                "sources": [
                    {
                        "id": "test",
                        "url": "https://example.com",
                        "enabled": True,
                    }
                ],
            }
        }

        sync_agents_on_startup(config=config)

        # Verify cache_dir was passed correctly
        call_args = mock_sync_service_class.call_args
        assert call_args[1]["cache_dir"] == Path(custom_cache)

    @patch("claude_mpm.services.agents.startup_sync.Config")
    def test_loads_config_from_singleton_when_not_provided(self, mock_config_class):
        """Test that Config singleton is used when config parameter is None."""
        mock_config_instance = MagicMock()
        mock_config_instance.to_dict.return_value = {"agent_sync": {"enabled": False}}
        mock_config_class.return_value = mock_config_instance

        result = sync_agents_on_startup(config=None)

        # Verify Config was instantiated
        mock_config_class.assert_called_once()
        mock_config_instance.to_dict.assert_called_once()

        # Verify sync was disabled (from mocked config)
        assert result["enabled"] is False

    def test_graceful_handling_of_unexpected_errors(self):
        """Test that unexpected errors are caught and logged gracefully."""
        # Provide invalid config to trigger exception
        invalid_config = {"agent_sync": None}  # Will cause .get() to fail

        result = sync_agents_on_startup(config=invalid_config)

        # Should not raise exception, but capture error
        assert result["enabled"] is False
        assert len(result["errors"]) > 0
        assert result["duration_ms"] >= 0

    @patch("claude_mpm.services.agents.startup_sync.GitSourceSyncService")
    def test_expanduser_on_cache_dir(self, mock_sync_service_class):
        """Test that ~ is expanded in cache_dir path."""
        mock_service = MagicMock()
        mock_service.sync_agents.return_value = {
            "synced": [],
            "cached": [],
            "failed": [],
            "total_downloaded": 0,
            "cache_hits": 0,
        }
        mock_sync_service_class.return_value = mock_service

        config = {
            "agent_sync": {
                "enabled": True,
                "cache_dir": "~/.custom/cache",
                "sources": [
                    {
                        "id": "test",
                        "url": "https://example.com",
                        "enabled": True,
                    }
                ],
            }
        }

        sync_agents_on_startup(config=config)

        # Verify expanduser was called on cache_dir
        call_args = mock_sync_service_class.call_args
        cache_dir = call_args[1]["cache_dir"]
        assert str(cache_dir) != "~/.custom/cache"  # Should be expanded
        assert "~" not in str(cache_dir)


class TestGetSyncStatus:
    """Test suite for get_sync_status function."""

    @patch("claude_mpm.services.agents.startup_sync.Config")
    def test_get_status_with_enabled_sync(self, mock_config_class):
        """Test getting sync status when sync is enabled."""
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda key, default=None: {
            "agent_sync": {
                "enabled": True,
                "sources": [
                    {"id": "source1", "enabled": True},
                    {"id": "source2", "enabled": True},
                    {"id": "source3", "enabled": False},
                ],
                "cache_dir": "/custom/cache",
            }
        }.get(key, default)
        mock_config_class.return_value = mock_config

        status = get_sync_status()

        assert status["enabled"] is True
        assert status["sources_configured"] == 2  # Only enabled sources
        assert status["cache_dir"] == "/custom/cache"

    @patch("claude_mpm.services.agents.startup_sync.Config")
    def test_get_status_with_disabled_sync(self, mock_config_class):
        """Test getting sync status when sync is disabled."""
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda key, default=None: {
            "agent_sync": {"enabled": False, "sources": []}
        }.get(key, default)
        mock_config_class.return_value = mock_config

        status = get_sync_status()

        assert status["enabled"] is False
        assert status["sources_configured"] == 0

    @patch("claude_mpm.services.agents.startup_sync.Config")
    def test_get_status_uses_default_cache_dir(self, mock_config_class):
        """Test that default cache_dir is used when not configured."""
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda key, default=None: {
            "agent_sync": {"enabled": True, "sources": []}
        }.get(key, default)
        mock_config_class.return_value = mock_config

        status = get_sync_status()

        assert "~/.claude-mpm/cache/remote-agents" in status["cache_dir"]

    @patch("claude_mpm.services.agents.startup_sync.Config")
    def test_get_status_handles_exceptions_gracefully(self, mock_config_class):
        """Test that exceptions in get_sync_status are handled gracefully."""
        mock_config_class.side_effect = Exception("Config error")

        status = get_sync_status()

        assert status["enabled"] is False
        assert "error" in status
        assert status["error"] == "Config error"

    @patch("claude_mpm.services.agents.startup_sync.Config")
    def test_get_status_counts_only_enabled_sources(self, mock_config_class):
        """Test that only enabled sources are counted in status."""
        mock_config = MagicMock()
        mock_config.get.side_effect = lambda key, default=None: {
            "agent_sync": {
                "enabled": True,
                "sources": [
                    {"id": "s1", "enabled": True},
                    {"id": "s2", "enabled": False},
                    {"id": "s3", "enabled": True},
                    {"id": "s4", "enabled": False},
                ],
            }
        }.get(key, default)
        mock_config_class.return_value = mock_config

        status = get_sync_status()

        assert status["sources_configured"] == 2  # Only s1 and s3
