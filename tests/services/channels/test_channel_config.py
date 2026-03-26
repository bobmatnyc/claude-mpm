"""Unit tests for channel configuration loading."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from claude_mpm.services.channels.channel_config import (
    ChannelsConfig,
    HubConfig,
    MemoryConfig,
    SecurityConfig,
    SlackChannelConfig,
    TelegramChannelConfig,
    TerminalChannelConfig,
    VectorSearchConfig,
    load_channels_config,
    write_default_channels_config,
)


class TestChannelsConfigDefaults(unittest.TestCase):
    """ChannelsConfig has sensible defaults without a config file."""

    def test_default_hub_port(self) -> None:
        cfg = ChannelsConfig()
        self.assertEqual(cfg.hub.port, 8766)

    def test_default_hub_max_sessions(self) -> None:
        cfg = ChannelsConfig()
        self.assertEqual(cfg.hub.max_sessions, 10)

    def test_default_terminal_enabled(self) -> None:
        cfg = ChannelsConfig()
        self.assertTrue(cfg.terminal.enabled)

    def test_default_telegram_disabled(self) -> None:
        cfg = ChannelsConfig()
        self.assertFalse(cfg.telegram.enabled)

    def test_default_slack_disabled(self) -> None:
        cfg = ChannelsConfig()
        self.assertFalse(cfg.slack.enabled)

    def test_default_vector_search_auto_probe(self) -> None:
        cfg = ChannelsConfig()
        self.assertTrue(cfg.vector_search.auto_probe)

    def test_default_security_max_auth_attempts(self) -> None:
        cfg = ChannelsConfig()
        self.assertEqual(cfg.security.max_auth_attempts, 5)


class TestLoadChannelsConfig(unittest.TestCase):
    """load_channels_config returns defaults when file is missing."""

    def test_missing_config_returns_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg = load_channels_config(Path(tmpdir))
        self.assertIsInstance(cfg, ChannelsConfig)
        self.assertEqual(cfg.hub.port, 8766)

    def test_load_with_yaml_file(self) -> None:
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("PyYAML not installed")

        import yaml

        content = {
            "hub": {"port": 9000, "max_sessions": 5},
            "channels": {
                "terminal": {"enabled": True},
                "telegram": {"enabled": True, "allowed_user_ids": [123]},
            },
            "vector_search": {"auto_probe": False},
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_file = Path(tmpdir) / "channels.yaml"
            cfg_file.write_text(yaml.dump(content))
            cfg = load_channels_config(Path(tmpdir))

        self.assertEqual(cfg.hub.port, 9000)
        self.assertEqual(cfg.hub.max_sessions, 5)
        self.assertTrue(cfg.telegram.enabled)
        self.assertFalse(cfg.vector_search.auto_probe)

    def test_load_with_malformed_yaml(self) -> None:
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("PyYAML not installed")

        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_file = Path(tmpdir) / "channels.yaml"
            cfg_file.write_text(": invalid: yaml: {{{{")
            cfg = load_channels_config(Path(tmpdir))

        # Should fall back to defaults on parse error
        self.assertIsInstance(cfg, ChannelsConfig)


class TestWriteDefaultChannelsConfig(unittest.TestCase):
    """write_default_channels_config creates a config file."""

    def test_writes_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_default_channels_config(Path(tmpdir))
            self.assertTrue(path.exists())

    def test_does_not_overwrite_existing(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_file = Path(tmpdir) / "channels.yaml"
            cfg_file.write_text("# existing content\n")
            write_default_channels_config(Path(tmpdir))
            self.assertEqual(cfg_file.read_text(), "# existing content\n")

    def test_written_file_contains_hub_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_default_channels_config(Path(tmpdir))
            content = path.read_text()
            self.assertIn("hub:", content)
            self.assertIn("channels:", content)


if __name__ == "__main__":
    unittest.main()
