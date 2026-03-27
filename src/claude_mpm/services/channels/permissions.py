"""Unified permission model for bot clients across all channel adapters.

Loads permissions from bot-permissions.yaml files at two levels:
- Global: ~/.claude-mpm/bot-permissions.yaml
- Project: {project_root}/.claude-mpm/bot-permissions.yaml

When no configuration files exist, the system defaults to ALLOW ALL,
ensuring it works without any setup.
"""

from __future__ import annotations

import fnmatch
import importlib.util
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

HAS_YAML = importlib.util.find_spec("yaml") is not None


@dataclass
class RateLimitConfig:
    """Rate limiting configuration per user."""

    max_sessions_per_hour: int = 10
    max_concurrent_sessions: int = 2


@dataclass
class GitRequirements:
    """Git state requirements for a project."""

    branch_pattern: str = ".*"  # regex pattern for allowed branches
    require_clean: str = "ignore"  # "ignore" | "warn" | "block"


@dataclass
class BotPermission:
    """A permission entry mapping platform identity to role and project access."""

    platform: str  # "github", "telegram", "slack"
    identity: str  # user_id, github login, slack user id
    role: str = "user"  # "admin", "user", "readonly"
    project_patterns: list[str] = field(default_factory=lambda: ["*"])
    rate_limit: RateLimitConfig | None = None
    git: GitRequirements | None = None


@dataclass
class RoleDefinition:
    """Defines what a role can do."""

    can_run: bool = True
    can_kill_others: bool = False
    max_concurrent_sessions: int = 2


class PermissionManager:
    """Loads and evaluates permissions from bot-permissions.yaml files.

    Permission files are loaded from two locations (merged, project takes priority):
    - Global: ~/.claude-mpm/bot-permissions.yaml
    - Project: .claude-mpm/bot-permissions.yaml (relative to project_root)
    """

    def __init__(self) -> None:
        self._permissions: list[BotPermission] = []
        self._roles: dict[str, RoleDefinition] = {
            "admin": RoleDefinition(
                can_run=True, can_kill_others=True, max_concurrent_sessions=10
            ),
            "user": RoleDefinition(
                can_run=True, can_kill_others=False, max_concurrent_sessions=2
            ),
            "readonly": RoleDefinition(
                can_run=False, can_kill_others=False, max_concurrent_sessions=0
            ),
        }
        self._rate_tracker: dict[str, list[float]] = {}
        self._concurrent_tracker: dict[str, int] = {}

    def load(self, project_root: Path | None = None) -> None:
        """Load permissions from global and project-level config files.

        Global file: ~/.claude-mpm/bot-permissions.yaml
        Project file: {project_root}/.claude-mpm/bot-permissions.yaml

        Project-level permissions override global ones for the same identity.
        """
        self._permissions = []

        # Load global
        global_path = Path.home() / ".claude-mpm" / "bot-permissions.yaml"
        if global_path.exists():
            self._load_file(global_path)

        # Load project-level (overrides global for same identity)
        if project_root:
            project_path = project_root / ".claude-mpm" / "bot-permissions.yaml"
            if project_path.exists():
                self._load_file(project_path, override=True)

    def _load_file(self, path: Path, override: bool = False) -> None:
        """Parse a bot-permissions.yaml file and add permissions."""
        if not HAS_YAML:
            logger.debug("PyYAML not available, skipping %s", path)
            return

        try:
            import yaml

            with open(path) as f:
                data = yaml.safe_load(f) or {}
        except Exception:
            logger.warning("Failed to parse %s", path, exc_info=True)
            return

        # Parse roles
        if roles_data := data.get("roles"):
            for role_name, role_def in roles_data.items():
                if isinstance(role_def, dict):
                    self._roles[role_name] = RoleDefinition(
                        can_run=role_def.get("can_run", True),
                        can_kill_others=role_def.get("can_kill_others", False),
                        max_concurrent_sessions=role_def.get(
                            "max_concurrent_sessions", 2
                        ),
                    )

        # Parse permissions
        for entry in data.get("permissions", []):
            if not isinstance(entry, dict):
                continue
            platform = entry.get("platform", "")
            identity = str(entry.get("identity", ""))
            if not platform or not identity:
                continue

            # Build rate limit config
            rate_limit: RateLimitConfig | None = None
            if rl_data := entry.get("rate_limit"):
                rate_limit = RateLimitConfig(
                    max_sessions_per_hour=rl_data.get("max_sessions_per_hour", 10),
                    max_concurrent_sessions=rl_data.get("max_concurrent_sessions", 2),
                )

            # Build git requirements
            git: GitRequirements | None = None
            if git_data := entry.get("git"):
                git = GitRequirements(
                    branch_pattern=git_data.get("branch_pattern", ".*"),
                    require_clean=git_data.get("require_clean", "ignore"),
                )

            perm = BotPermission(
                platform=platform,
                identity=identity,
                role=entry.get("role", "user"),
                project_patterns=entry.get("project_patterns", ["*"]),
                rate_limit=rate_limit,
                git=git,
            )

            if override:
                # Remove existing permission for same platform+identity
                self._permissions = [
                    p
                    for p in self._permissions
                    if not (p.platform == platform and p.identity == identity)
                ]

            self._permissions.append(perm)

    def check(
        self, platform: str, identity: str, project_root: str | None = None
    ) -> tuple[bool, str]:
        """Check if an identity is allowed to create sessions.

        Returns (allowed: bool, reason: str).

        If no permissions are loaded (no config files), default to ALLOW ALL.
        This ensures the system works without any configuration.
        """
        # If no permissions loaded, allow all (unconfigured = open)
        if not self._permissions:
            return True, ""

        # Find matching permission
        perm = self._find_permission(platform, identity)
        if perm is None:
            # Identity not in permission list — deny by default when
            # permissions are explicitly configured
            return False, f"No permission entry for {platform}:{identity}"

        # Check role allows running
        role_def = self._roles.get(perm.role)
        if role_def is None:
            return False, f"Unknown role '{perm.role}'"
        if not role_def.can_run:
            return False, f"Role '{perm.role}' does not allow running sessions"

        # Check project pattern
        if project_root and perm.project_patterns:
            matched = any(
                fnmatch.fnmatch(project_root, pattern)
                for pattern in perm.project_patterns
            )
            if not matched:
                return (
                    False,
                    f"Project '{project_root}' does not match allowed patterns "
                    f"{perm.project_patterns}",
                )

        return True, ""

    def check_rate_limit(self, platform: str, identity: str) -> tuple[bool, str]:
        """Check if identity is within rate limits.

        Returns (allowed: bool, reason: str).
        Uses a sliding window for sessions_per_hour.
        """
        perm = self._find_permission(platform, identity)
        if perm is None or perm.rate_limit is None:
            return True, ""

        rl = perm.rate_limit
        key = f"{platform}:{identity}"
        now = time.time()

        # Check concurrent sessions
        concurrent = self._concurrent_tracker.get(key, 0)
        if concurrent >= rl.max_concurrent_sessions:
            return (
                False,
                f"Concurrent session limit exceeded: "
                f"{concurrent}/{rl.max_concurrent_sessions}",
            )

        # Check sessions per hour (sliding window)
        timestamps = self._rate_tracker.get(key, [])
        # Remove entries older than 1 hour
        one_hour_ago = now - 3600
        timestamps = [ts for ts in timestamps if ts > one_hour_ago]
        self._rate_tracker[key] = timestamps

        if len(timestamps) >= rl.max_sessions_per_hour:
            return (
                False,
                f"Rate limit exceeded: {len(timestamps)}/{rl.max_sessions_per_hour} "
                f"sessions per hour",
            )

        return True, ""

    def record_session_start(self, platform: str, identity: str) -> None:
        """Record that a session was started (for rate limiting)."""
        key = f"{platform}:{identity}"
        now = time.time()

        # Track timestamp for hourly rate
        if key not in self._rate_tracker:
            self._rate_tracker[key] = []
        self._rate_tracker[key].append(now)

        # Increment concurrent count
        self._concurrent_tracker[key] = self._concurrent_tracker.get(key, 0) + 1

    def record_session_end(self, platform: str, identity: str) -> None:
        """Record that a session ended (for concurrent session tracking)."""
        key = f"{platform}:{identity}"
        current = self._concurrent_tracker.get(key, 0)
        if current > 0:
            self._concurrent_tracker[key] = current - 1

    def get_role(self, platform: str, identity: str) -> RoleDefinition:
        """Get the role definition for an identity."""
        perm = self._find_permission(platform, identity)
        if perm is None:
            return self._roles.get("user", RoleDefinition())
        return self._roles.get(perm.role, RoleDefinition())

    def _find_permission(self, platform: str, identity: str) -> BotPermission | None:
        """Find the first matching permission entry for a platform+identity."""
        for perm in self._permissions:
            if perm.platform == platform and perm.identity == identity:
                return perm
        return None
