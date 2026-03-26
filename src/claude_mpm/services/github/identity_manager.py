"""GitHubIdentityManager — multi-account GitHub identity with keyring-backed token storage."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class GitHubAccount:
    username: str
    is_active: bool = False
    token_stored: bool = False  # True if token is in keyring/storage

    @property
    def keyring_account(self) -> str:
        return f"claude-mpm-github:{self.username}"


class GitHubIdentityManager:
    """Manages multiple GitHub accounts with keyring-backed token storage.

    Wraps the existing GitHubAccountManager for .gh-account file convention.
    Adds multi-account registry and token storage layer.
    """

    KEYRING_SERVICE = "claude-mpm-github"
    STATE_DIR = Path.home() / ".claude-mpm" / "github"
    ACCOUNTS_FILE = STATE_DIR / "accounts.json"
    ACTIVE_ACCOUNT_FILE = STATE_DIR / "active-account"

    def __init__(self, project_dir: Path | None = None) -> None:
        self._project_dir = project_dir
        self.STATE_DIR.mkdir(parents=True, exist_ok=True)
        self._has_keyring = self._check_keyring()

    def _check_keyring(self) -> bool:
        try:
            import keyring  # noqa: F401

            return True
        except ImportError:
            return False

    # ── Account discovery ──────────────────────────────────────────────────

    def list_accounts(self) -> list[GitHubAccount]:
        """List all registered accounts."""
        accounts = self._load_accounts()
        active = self._get_active_from_gh_cli()
        for acc in accounts:
            acc.is_active = acc.username == active
            acc.token_stored = self._has_token(acc.username)
        return accounts

    def get_active_account(self, cwd: Path | None = None) -> str | None:
        """Get active account. Priority: .gh-account file → stored → gh CLI."""
        # Check .gh-account in project tree
        try:
            from claude_mpm.services.github.github_account_manager import (
                GitHubAccountManager,
            )

            mgr = GitHubAccountManager()
            project_account = mgr.get_required_account()
            if project_account:
                return project_account
        except Exception:
            pass
        # Stored active account
        if self.ACTIVE_ACCOUNT_FILE.exists():
            stored = self.ACTIVE_ACCOUNT_FILE.read_text().strip()
            if stored:
                return stored
        # Fall back to gh CLI
        return self._get_active_from_gh_cli()

    def _get_active_from_gh_cli(self) -> str | None:
        try:
            result = subprocess.run(
                ["gh", "api", "user", "--jq", ".login"],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    # ── Account management ─────────────────────────────────────────────────

    def switch_account(self, username: str) -> bool:
        """Switch active GitHub account. Wraps gh auth switch."""
        try:
            result = subprocess.run(
                ["gh", "auth", "switch", "--user", username],
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                self.ACTIVE_ACCOUNT_FILE.write_text(username)
                logger.info("Switched to GitHub account: %s", username)
                return True
            logger.error("gh auth switch failed: %s", result.stderr)
            return False
        except Exception:
            logger.exception("Failed to switch GitHub account")
            return False

    def add_account(self, username: str, token: str | None = None) -> GitHubAccount:
        """Register an account. Token is stored in keyring if provided."""
        accounts = self._load_accounts()
        existing = next((a for a in accounts if a.username == username), None)
        if not existing:
            accounts.append(GitHubAccount(username=username))
            self._save_accounts(accounts)
        if token:
            self._store_token(username, token)
        elif not token:
            # Try to get token from gh CLI
            try:
                result = subprocess.run(
                    ["gh", "auth", "token", "--user", username],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0 and result.stdout.strip():
                    self._store_token(username, result.stdout.strip())
            except Exception:
                pass
        return GitHubAccount(username=username, token_stored=self._has_token(username))

    def get_token(self, username: str | None = None) -> str | None:
        """Get GitHub token for account. Falls back to env vars."""
        if username is None:
            username = self.get_active_account()
        if username:
            token = self._load_token(username)
            if token:
                return token
        # Try gh CLI token
        try:
            cmd = ["gh", "auth", "token"]
            if username:
                cmd.extend(["--user", username])
            result = subprocess.run(
                cmd, check=False, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except Exception:
            pass
        # Env var fallbacks
        return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")

    def sync_from_gh_cli(self) -> list[GitHubAccount]:
        """Discover all accounts currently authenticated in gh CLI."""
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            output = result.stdout + result.stderr
            accounts: list[GitHubAccount] = []
            for line in output.splitlines():
                line = line.strip()
                if "Logged in to github.com account" in line:
                    # "Logged in to github.com account username (keyring)"
                    parts = line.split("account")
                    if len(parts) > 1:
                        username = parts[1].strip().split()[0]
                        if username:
                            acc = self.add_account(username)
                            accounts.append(acc)
            self._save_accounts(accounts)
            return accounts
        except Exception:
            logger.exception("Failed to sync from gh CLI")
            return []

    # ── Token storage ──────────────────────────────────────────────────────

    def _has_token(self, username: str) -> bool:
        return self._load_token(username) is not None

    def _store_token(self, username: str, token: str) -> None:
        if self._has_keyring:
            import keyring

            keyring.set_password(self.KEYRING_SERVICE, username, token)
        else:
            token_file = self.STATE_DIR / f"{self._user_hash(username)}.token"
            token_file.write_text(token)
            token_file.chmod(0o600)

    def _load_token(self, username: str) -> str | None:
        if self._has_keyring:
            import keyring

            return keyring.get_password(self.KEYRING_SERVICE, username)
        token_file = self.STATE_DIR / f"{self._user_hash(username)}.token"
        if token_file.exists():
            return token_file.read_text().strip()
        return None

    def _user_hash(self, username: str) -> str:
        return hashlib.sha256(username.encode()).hexdigest()[:16]

    # ── Registry persistence ───────────────────────────────────────────────

    def _load_accounts(self) -> list[GitHubAccount]:
        if not self.ACCOUNTS_FILE.exists():
            return []
        try:
            data = json.loads(self.ACCOUNTS_FILE.read_text())
            return [GitHubAccount(username=a["username"]) for a in data]
        except Exception:
            return []

    def _save_accounts(self, accounts: list[GitHubAccount]) -> None:
        data = [{"username": a.username} for a in accounts]
        self.ACCOUNTS_FILE.write_text(json.dumps(data, indent=2))
