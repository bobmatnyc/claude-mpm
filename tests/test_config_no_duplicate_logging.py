#!/usr/bin/env python3
"""Test that configuration loading messages are not duplicated."""

import logging
import sys
from pathlib import Path
from unittest import TestCase

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


class TestConfigNoDuplicateLogging(TestCase):
    """Test that configuration loading doesn't produce duplicate messages."""

    def setUp(self):
        """Reset singleton before each test."""
        Config.reset_singleton()

    def tearDown(self):
        """Reset singleton after each test."""
        Config.reset_singleton()

    def test_single_success_message():
        """Test that 'Successfully loaded configuration' appears only once."""
        with self.assertLogs("claude_mpm.core.config", level=logging.INFO) as cm:
            # Create multiple Config instances
            Config(config_file=Path.cwd() / ".claude-mpm" / "configuration.yaml")
            Config(config_file=Path.cwd() / ".claude-mpm" / "configuration.yaml")
            Config()

            # Count success messages
            success_messages = [
                msg for msg in cm.output if "✓ Successfully loaded configuration" in msg
            ]

            # Should only appear once
            self.assertEqual(
                len(success_messages),
                1,
                f"Expected 1 success message, got {len(success_messages)}",
            )

    def test_reload_prevention():
        """Test that calling load_file on same file doesn't reload."""
        config_file = Path.cwd() / ".claude-mpm" / "configuration.yaml"

        with self.assertLogs("claude_mpm.core.config", level=logging.DEBUG) as cm:
            config = Config(config_file=config_file)

            # Try to load the same file again
            config.load_file(config_file)
            config.load_file(config_file)

            # Check for skip messages at DEBUG level
            skip_messages = [
                msg for msg in cm.output if "skipping reload" in msg.lower()
            ]

            # Should have skip messages for the duplicate load attempts
            self.assertGreaterEqual(
                len(skip_messages),
                2,
                "Expected skip messages for duplicate load attempts",
            )

    def test_singleton_with_services():
        """Test that services share the same Config singleton."""
        from claude_mpm.services.agent_capabilities_service import (
            AgentCapabilitiesService,
        )
        from claude_mpm.services.system_instructions_service import (
            SystemInstructionsService,
        )

        with self.assertLogs("claude_mpm.core.config", level=logging.INFO) as cm:
            service1 = AgentCapabilitiesService()
            service2 = SystemInstructionsService()

            # Verify they share the same config
            self.assertIs(service1.config, service2.config)

            # Count success messages
            success_messages = [
                msg for msg in cm.output if "✓ Successfully loaded configuration" in msg
            ]

            # Should only appear once even with multiple services
            self.assertEqual(
                len(success_messages),
                1,
                f"Expected 1 success message with multiple services, got {len(success_messages)}",
            )


if __name__ == "__main__":
    import unittest

    unittest.main()
