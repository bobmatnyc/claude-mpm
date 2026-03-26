"""Unit tests for GitHubIdentityManager."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from claude_mpm.services.github.identity_manager import (
    GitHubAccount,
    GitHubIdentityManager,
)


class TestGitHubAccount(unittest.TestCase):
    """Tests for GitHubAccount dataclass."""

    def test_keyring_account_format(self) -> None:
        acc = GitHubAccount(username="octocat")
        self.assertEqual(acc.keyring_account, "claude-mpm-github:octocat")

    def test_default_flags(self) -> None:
        acc = GitHubAccount(username="octocat")
        self.assertFalse(acc.is_active)
        self.assertFalse(acc.token_stored)


class TestGitHubIdentityManagerInit(unittest.TestCase):
    """Tests for manager initialisation."""

    def _make_manager(self, tmpdir: Path) -> GitHubIdentityManager:
        # Patch STATE_DIR so tests don't pollute ~/.claude-mpm
        with patch.object(GitHubIdentityManager, "STATE_DIR", tmpdir):
            with patch.object(
                GitHubIdentityManager, "ACCOUNTS_FILE", tmpdir / "accounts.json"
            ):
                with patch.object(
                    GitHubIdentityManager,
                    "ACTIVE_ACCOUNT_FILE",
                    tmpdir / "active-account",
                ):
                    mgr = GitHubIdentityManager.__new__(GitHubIdentityManager)
                    mgr._project_dir = None
                    tmpdir.mkdir(parents=True, exist_ok=True)
                    mgr._has_keyring = False
                    return mgr

    def test_load_accounts_returns_empty_when_no_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = self._make_manager(Path(tmpdir))
            # Patch ACCOUNTS_FILE to a non-existent path
            with patch.object(
                type(mgr), "ACCOUNTS_FILE", Path(tmpdir) / "accounts.json"
            ):
                accounts = mgr._load_accounts()
        self.assertEqual(accounts, [])

    def test_load_accounts_parses_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            accounts_file = Path(tmpdir) / "accounts.json"
            accounts_file.write_text(
                json.dumps([{"username": "alice"}, {"username": "bob"}])
            )
            mgr = self._make_manager(Path(tmpdir))
            with patch.object(type(mgr), "ACCOUNTS_FILE", accounts_file):
                accounts = mgr._load_accounts()
        self.assertEqual(len(accounts), 2)
        usernames = [a.username for a in accounts]
        self.assertIn("alice", usernames)
        self.assertIn("bob", usernames)

    def test_save_and_load_accounts_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            accounts_file = Path(tmpdir) / "accounts.json"
            mgr = self._make_manager(Path(tmpdir))
            with patch.object(type(mgr), "ACCOUNTS_FILE", accounts_file):
                mgr._save_accounts([GitHubAccount("alice"), GitHubAccount("bob")])
                loaded = mgr._load_accounts()
        self.assertEqual({a.username for a in loaded}, {"alice", "bob"})

    def test_user_hash_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = self._make_manager(Path(tmpdir))
        h1 = mgr._user_hash("octocat")
        h2 = mgr._user_hash("octocat")
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 16)

    def test_user_hash_differs_for_different_users(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = self._make_manager(Path(tmpdir))
        self.assertNotEqual(mgr._user_hash("alice"), mgr._user_hash("bob"))


class TestGetActiveAccountFallback(unittest.TestCase):
    """Tests for get_active_account priority chain."""

    def test_falls_back_to_gh_cli(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = GitHubIdentityManager.__new__(GitHubIdentityManager)
            mgr._project_dir = None
            mgr._has_keyring = False
            # Override instance-level class attributes to use tmpdir
            mgr.ACTIVE_ACCOUNT_FILE = Path(tmpdir) / "active-account"
            mgr.ACCOUNTS_FILE = Path(tmpdir) / "accounts.json"
            mgr.STATE_DIR = Path(tmpdir)

            with (
                patch.object(mgr, "_get_active_from_gh_cli", return_value="ghuser"),
                # GitHubAccountManager is a local import inside get_active_account;
                # patch it in its home module
                patch(
                    "claude_mpm.services.github.github_account_manager"
                    ".GitHubAccountManager.get_required_account",
                    return_value=None,
                ),
            ):
                result = mgr.get_active_account()

        self.assertEqual(result, "ghuser")

    def test_uses_stored_active_account(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            active_file = Path(tmpdir) / "active-account"
            active_file.write_text("stored_user")

            mgr = GitHubIdentityManager.__new__(GitHubIdentityManager)
            mgr._project_dir = None
            mgr._has_keyring = False
            mgr.ACTIVE_ACCOUNT_FILE = active_file
            mgr.ACCOUNTS_FILE = Path(tmpdir) / "accounts.json"
            mgr.STATE_DIR = Path(tmpdir)

            with patch(
                "claude_mpm.services.github.github_account_manager"
                ".GitHubAccountManager.get_required_account",
                return_value=None,
            ):
                result = mgr.get_active_account()

        self.assertEqual(result, "stored_user")


class TestGetTokenFallback(unittest.TestCase):
    """get_token falls back through keyring → gh CLI → env vars."""

    def test_returns_env_var_as_last_resort(self) -> None:
        mgr = GitHubIdentityManager.__new__(GitHubIdentityManager)
        mgr._project_dir = None
        mgr._has_keyring = False

        import os

        with (
            patch.object(mgr, "get_active_account", return_value=None),
            patch.object(mgr, "_load_token", return_value=None),
            patch(
                "subprocess.run",
                return_value=MagicMock(returncode=1, stdout=""),
            ),
            patch.dict(os.environ, {"GITHUB_TOKEN": "env_token"}),
        ):
            token = mgr.get_token()

        self.assertEqual(token, "env_token")

    def test_prefers_keyring_over_env_var(self) -> None:
        mgr = GitHubIdentityManager.__new__(GitHubIdentityManager)
        mgr._project_dir = None
        mgr._has_keyring = False

        import os

        with (
            patch.object(mgr, "get_active_account", return_value="alice"),
            patch.object(mgr, "_load_token", return_value="keyring_token"),
            patch.dict(os.environ, {"GITHUB_TOKEN": "env_token"}),
        ):
            token = mgr.get_token()

        self.assertEqual(token, "keyring_token")


if __name__ == "__main__":
    unittest.main()
