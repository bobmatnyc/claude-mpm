"""Channel configuration loader from .claude-mpm/channels.yaml."""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HAS_YAML = importlib.util.find_spec("yaml") is not None


@dataclass
class TerminalChannelConfig:
    enabled: bool = True
    default_cwd: str | None = None


@dataclass
class TelegramChannelConfig:
    enabled: bool = False
    bot_token_env: str = "CLAUDE_MPM_TELEGRAM_BOT_TOKEN"
    allowed_user_ids: list[int] = field(default_factory=list)
    default_cwd: str = "~"
    session_mode: str = "per_user"  # "per_user" | "shared"
    auth_required: bool = True
    stream_edits: bool = True
    edit_interval_ms: int = 2000


@dataclass
class SlackChannelConfig:
    enabled: bool = False
    bot_token_env: str = "SLACK_BOT_TOKEN"
    app_token_env: str = "SLACK_APP_TOKEN"
    allowed_workspace_ids: list[str] = field(default_factory=list)
    allowed_channel_ids: list[str] = field(default_factory=list)
    allowed_user_ids: list[str] = field(default_factory=list)
    default_cwd: str = "~"
    session_mode: str = "per_user"
    auth_required: bool = True
    use_block_kit: bool = True
    update_interval_ms: int = 3000


@dataclass
class GitHubChannelConfig:
    enabled: bool = False
    pat_env: str = "GITHUB_TOKEN"
    owner: str | None = None  # repo owner, e.g. "bobmatnyc"
    repo: str | None = None  # repo name, e.g. "claude-mpm"
    label_gate: str = "mpm:run"
    mode: str = "polling"  # "polling" | "webhook" | "both"
    poll_interval_seconds: int = 30
    webhook_port: int = 9876
    webhook_secret_env: str = "GITHUB_WEBHOOK_SECRET"
    output_mode: str = "streaming"  # "streaming" | "summary"
    comment_debounce_seconds: float = 5.0
    allowed_user_types: list[str] = field(
        default_factory=lambda: ["member", "owner", "collaborator"]
    )
    max_prompt_chars: int = 2000


@dataclass
class SecurityConfig:
    pairing_token_length: int = 32
    token_rotation_days: int = 90
    require_local_confirmation: bool = True
    max_auth_attempts: int = 5
    lockout_minutes: int = 30


@dataclass
class MemoryConfig:
    namespace_strategy: str = "user_project"


@dataclass
class VectorSearchConfig:
    auto_probe: bool = True
    probe_timeout_ms: int = 2000
    graceful_fallback: bool = True


@dataclass
class HubConfig:
    port: int = 8766
    max_sessions: int = 10
    session_ttl_hours: int = 24


@dataclass
class ChannelsConfig:
    hub: HubConfig = field(default_factory=HubConfig)
    terminal: TerminalChannelConfig = field(default_factory=TerminalChannelConfig)
    telegram: TelegramChannelConfig = field(default_factory=TelegramChannelConfig)
    slack: SlackChannelConfig = field(default_factory=SlackChannelConfig)
    github: GitHubChannelConfig = field(default_factory=GitHubChannelConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    vector_search: VectorSearchConfig = field(default_factory=VectorSearchConfig)


def load_channels_config(config_dir: Path | None = None) -> ChannelsConfig:
    """Load channels.yaml from .claude-mpm/ or return defaults."""
    if config_dir is None:
        config_dir = Path.home() / ".claude-mpm"
    config_file = config_dir / "channels.yaml"
    if not config_file.exists() or not HAS_YAML:
        return ChannelsConfig()
    try:
        import yaml

        with open(config_file) as f:
            data = yaml.safe_load(f) or {}
        return _parse_config(data)
    except Exception:
        return ChannelsConfig()


def _parse_github_config_from_env(cfg: GitHubChannelConfig) -> GitHubChannelConfig:
    """Override GitHubChannelConfig fields from environment variables."""
    import os

    if val := os.environ.get("CLAUDE_MPM_GITHUB_OWNER"):
        cfg.owner = val
    if val := os.environ.get("CLAUDE_MPM_GITHUB_REPO"):
        cfg.repo = val
    if val := os.environ.get("CLAUDE_MPM_GITHUB_LABEL"):
        cfg.label_gate = val
    if val := os.environ.get("CLAUDE_MPM_GITHUB_MODE"):
        cfg.mode = val
    if val := os.environ.get("CLAUDE_MPM_GITHUB_POLL_INTERVAL"):
        try:
            cfg.poll_interval_seconds = int(val)
        except ValueError:
            pass
    return cfg


def _parse_config(data: dict[str, Any]) -> ChannelsConfig:
    cfg = ChannelsConfig()
    if hub_data := data.get("hub"):
        cfg.hub = HubConfig(
            **{k: v for k, v in hub_data.items() if hasattr(HubConfig, k)}
        )  # type: ignore[call-arg]
    if ch := data.get("channels", {}):
        if t := ch.get("terminal"):
            cfg.terminal = TerminalChannelConfig(
                **{k: v for k, v in t.items() if hasattr(TerminalChannelConfig, k)}
            )  # type: ignore[call-arg]
        if tg := ch.get("telegram"):
            cfg.telegram = TelegramChannelConfig(
                **{k: v for k, v in tg.items() if hasattr(TelegramChannelConfig, k)}
            )  # type: ignore[call-arg]
        if sl := ch.get("slack"):
            cfg.slack = SlackChannelConfig(
                **{k: v for k, v in sl.items() if hasattr(SlackChannelConfig, k)}
            )  # type: ignore[call-arg]
        if gh := ch.get("github"):
            cfg.github = GitHubChannelConfig(
                **{k: v for k, v in gh.items() if hasattr(GitHubChannelConfig, k)}
            )  # type: ignore[call-arg]
    cfg.github = _parse_github_config_from_env(cfg.github)
    if sec := data.get("security"):
        cfg.security = SecurityConfig(
            **{k: v for k, v in sec.items() if hasattr(SecurityConfig, k)}
        )  # type: ignore[call-arg]
    if mem := data.get("memory"):
        cfg.memory = MemoryConfig(
            **{k: v for k, v in mem.items() if hasattr(MemoryConfig, k)}
        )  # type: ignore[call-arg]
    if vs := data.get("vector_search"):
        cfg.vector_search = VectorSearchConfig(
            **{k: v for k, v in vs.items() if hasattr(VectorSearchConfig, k)}
        )  # type: ignore[call-arg]
    return cfg


def write_default_channels_config(config_dir: Path | None = None) -> Path:
    """Write a default channels.yaml if it doesn't exist."""
    if config_dir is None:
        config_dir = Path.home() / ".claude-mpm"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "channels.yaml"
    if config_file.exists():
        return config_file
    default_content = """\
# Claude MPM Multi-Channel Connection Manager
# Generated by: claude-mpm channels setup

version: "1.0"
hub:
  port: 8766
  max_sessions: 10
  session_ttl_hours: 24

channels:
  terminal:
    enabled: true
    default_cwd: null

  telegram:
    enabled: false
    bot_token_env: CLAUDE_MPM_TELEGRAM_BOT_TOKEN
    allowed_user_ids: []       # add telegram numeric user IDs here
    default_cwd: "~"
    session_mode: per_user     # per_user | shared
    auth_required: true

  slack:
    enabled: false
    bot_token_env: SLACK_BOT_TOKEN
    app_token_env: SLACK_APP_TOKEN
    allowed_workspace_ids: []
    allowed_channel_ids: []
    allowed_user_ids: []
    default_cwd: "~"
    session_mode: per_user
    auth_required: true

security:
  pairing_token_length: 32
  token_rotation_days: 90
  require_local_confirmation: true
  max_auth_attempts: 5
  lockout_minutes: 30

memory:
  namespace_strategy: user_project

vector_search:
  auto_probe: true
  probe_timeout_ms: 2000
  graceful_fallback: true
"""
    config_file.write_text(default_content)
    return config_file
