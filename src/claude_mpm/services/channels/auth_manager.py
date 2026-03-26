"""Authentication manager for channel users (Phase 2)."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

_PAIRING_CODE_EXPIRY_SECONDS = 600  # 10 minutes


@dataclass
class ChannelUser:
    """A paired channel user."""

    channel: str
    user_id: str  # channel-specific numeric/string ID
    user_display: str
    local_unix_user: str  # local unix username
    paired_at: float = field(default_factory=time.time)
    token_hash: str = ""  # sha256 of the long-lived token (stored here)
    # actual token stored in system keyring

    @property
    def namespace_key(self) -> str:
        return f"{self.channel}:{self.user_id}"


@dataclass
class PairingCode:
    code: str
    channel: str
    user_id: str
    user_display: str
    created_at: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        return time.time() - self.created_at > _PAIRING_CODE_EXPIRY_SECONDS


class AuthManager:
    """Manages channel user pairing, token storage, and auth validation.

    Token storage uses system keyring when available, falls back to
    ~/.claude-mpm/channels/users/<hash>.json (less secure, warns user).
    """

    def __init__(self, users_dir: Path | None = None) -> None:
        self._users_dir = users_dir or (
            Path.home() / ".claude-mpm" / "channels" / "users"
        )
        self._users_dir.mkdir(parents=True, exist_ok=True)
        self._pending_codes: dict[str, PairingCode] = {}  # code -> PairingCode
        self._auth_attempts: dict[str, list[float]] = {}  # user_key -> timestamps
        self._has_keyring = self._check_keyring()

    def _check_keyring(self) -> bool:
        try:
            import keyring  # noqa: F401

            return True
        except ImportError:
            return False

    # ── Pairing ────────────────────────────────────────────────────────────

    def generate_pairing_code(
        self, channel: str, user_id: str, user_display: str
    ) -> str:
        """Generate a short-lived pairing code for a channel user."""
        # Clean up expired codes
        self._pending_codes = {
            k: v for k, v in self._pending_codes.items() if not v.is_expired()
        }
        code = self._make_pairing_code()
        self._pending_codes[code] = PairingCode(
            code=code, channel=channel, user_id=user_id, user_display=user_display
        )
        logger.info("Generated pairing code for %s:%s", channel, user_id)
        return code

    def _make_pairing_code(self) -> str:
        """Generate human-readable code like MPM-7X3K-9PQ2."""
        raw = secrets.token_hex(4).upper()
        return f"MPM-{raw[:4]}-{raw[4:]}"

    def confirm_pairing(self, code: str) -> ChannelUser | None:
        """Called from terminal to confirm a pairing code. Returns the paired user or None."""
        pending = self._pending_codes.pop(code, None)
        if pending is None:
            return None
        if pending.is_expired():
            return None

        token = secrets.token_hex(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        user = ChannelUser(
            channel=pending.channel,
            user_id=pending.user_id,
            user_display=pending.user_display,
            local_unix_user=os.environ.get("USER", "unknown"),
            token_hash=token_hash,
        )
        self._save_user(user)
        self._store_token(pending.channel, pending.user_id, token)
        logger.info("Paired user %s:%s", pending.channel, pending.user_id)
        return user

    # ── Auth validation ─────────────────────────────────────────────────────

    def is_authorized(self, channel: str, user_id: str) -> bool:
        """Check if a channel user is authorized (has a valid paired token)."""
        user = self._load_user(channel, user_id)
        if user is None:
            return False
        stored_token = self._load_token(channel, user_id)
        if stored_token is None:
            return False
        computed_hash = hashlib.sha256(stored_token.encode()).hexdigest()
        return computed_hash == user.token_hash

    def revoke(self, channel: str, user_id: str) -> bool:
        """Revoke a user's auth token."""
        user_file = self._user_file(channel, user_id)
        if user_file.exists():
            user_file.unlink()
        self._delete_token(channel, user_id)
        logger.info("Revoked auth for %s:%s", channel, user_id)
        return True

    # ── Persistence ─────────────────────────────────────────────────────────

    def _user_hash(self, channel: str, user_id: str) -> str:
        return hashlib.sha256(f"{channel}:{user_id}".encode()).hexdigest()[:16]

    def _user_file(self, channel: str, user_id: str) -> Path:
        return self._users_dir / f"{self._user_hash(channel, user_id)}.json"

    def _save_user(self, user: ChannelUser) -> None:
        f = self._user_file(user.channel, user.user_id)
        data = {
            "channel": user.channel,
            "user_id": user.user_id,
            "user_display": user.user_display,
            "local_unix_user": user.local_unix_user,
            "paired_at": user.paired_at,
            "token_hash": user.token_hash,
        }
        f.write_text(json.dumps(data, indent=2))

    def _load_user(self, channel: str, user_id: str) -> ChannelUser | None:
        f = self._user_file(channel, user_id)
        if not f.exists():
            return None
        try:
            data = json.loads(f.read_text())
            return ChannelUser(**data)
        except Exception:
            return None

    def _store_token(self, channel: str, user_id: str, token: str) -> None:
        if self._has_keyring:
            import keyring

            keyring.set_password("claude-mpm-channels", f"{channel}:{user_id}", token)
        else:
            # Fallback: store in file with warning
            token_file = self._users_dir / f"{self._user_hash(channel, user_id)}.token"
            token_file.write_text(token)
            token_file.chmod(0o600)
            logger.warning(
                "keyring not available; token stored in plaintext at %s. "
                "Install 'keyring' package for secure storage.",
                token_file,
            )

    def _load_token(self, channel: str, user_id: str) -> str | None:
        if self._has_keyring:
            import keyring

            return keyring.get_password("claude-mpm-channels", f"{channel}:{user_id}")
        token_file = self._users_dir / f"{self._user_hash(channel, user_id)}.token"
        if token_file.exists():
            return token_file.read_text().strip()
        return None

    def _delete_token(self, channel: str, user_id: str) -> None:
        if self._has_keyring:
            try:
                import keyring

                keyring.delete_password("claude-mpm-channels", f"{channel}:{user_id}")
            except Exception:
                pass
        token_file = self._users_dir / f"{self._user_hash(channel, user_id)}.token"
        if token_file.exists():
            token_file.unlink()
