#!/usr/bin/env python3
"""Test that --resume flag is properly passed through to Claude CLI."""

import os
import sys
import unittest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from claude_mpm.cli.commands.run import filter_claude_mpm_args


class TestResumeFlagPassthrough(unittest.TestCase):
    """Test that --resume flag is properly passed through to Claude."""

    def test_resume_with_session_id():
        """Test --resume with session ID is passed through."""
        claude_args = ["--", "--resume", "session123"]
        filtered = filter_claude_mpm_args(claude_args)
        self.assertEqual(filtered, ["--resume", "session123"])

    def test_resume_without_session_id():
        """Test --resume without session ID is passed through."""
        claude_args = ["--", "--resume"]
        filtered = filter_claude_mpm_args(claude_args)
        self.assertEqual(filtered, ["--resume"])

    def test_short_form_resume():
        """Test -r (short form) is passed through."""
        claude_args = ["--", "-r", "session456"]
        filtered = filter_claude_mpm_args(claude_args)
        self.assertEqual(filtered, ["-r", "session456"])

    def test_resume_with_other_claude_flags():
        """Test --resume with other Claude flags."""
        claude_args = ["--", "--resume", "abc123", "--model", "opus", "--continue"]
        filtered = filter_claude_mpm_args(claude_args)
        self.assertEqual(
            filtered, ["--resume", "abc123", "--model", "opus", "--continue"]
        )

    def test_mpm_flags_are_filtered():
        """Test that MPM-specific flags are filtered out."""
        claude_args = ["--monitor", "--", "--resume", "test123"]
        filtered = filter_claude_mpm_args(claude_args)
        # --monitor should be filtered, -- should be removed, --resume should pass through
        self.assertEqual(filtered, ["--resume", "test123"])

    def test_mpm_resume_is_filtered():
        """Test that --mpm-resume is filtered (it's MPM-specific)."""
        claude_args = ["--mpm-resume", "session789", "--model", "opus"]
        filtered = filter_claude_mpm_args(claude_args)
        # --mpm-resume and its value should be filtered
        self.assertEqual(filtered, ["--model", "opus"])

    def test_double_dash_separator_removed():
        """Test that -- separator is removed from filtered args."""
        claude_args = ["--", "--model", "opus"]
        filtered = filter_claude_mpm_args(claude_args)
        # -- should be removed
        self.assertEqual(filtered, ["--model", "opus"])

    def test_empty_args():
        """Test handling of empty argument list."""
        self.assertEqual(filter_claude_mpm_args([]), [])
        self.assertEqual(filter_claude_mpm_args(None), [])

    def test_only_separator():
        """Test handling of only -- separator."""
        claude_args = ["--"]
        filtered = filter_claude_mpm_args(claude_args)
        self.assertEqual(filtered, [])


if __name__ == "__main__":
    unittest.main()
