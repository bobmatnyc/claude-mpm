"""Unit tests for src/claude_mpm/core/env_defaults.py.

Tests verify that the centralized env var default system correctly:
  - Applies defaults when the env var is not set
  - Respects existing shell values (does NOT override them)
  - Is idempotent (calling multiple times is safe)
  - Propagates the resolved value to subprocess env dicts
"""

import os

import pytest

from claude_mpm.core.env_defaults import (
    _ENV_DEFAULTS,
    _PRESENCE_BASED_VARS,
    apply_env_defaults,
    apply_subprocess_env_defaults,
    get_telemetry_disabled,
)


class TestApplyEnvDefaults:
    """Tests for apply_env_defaults()."""

    def test_apply_env_defaults_sets_default(self, monkeypatch):
        """When DISABLE_TELEMETRY is not set, apply_env_defaults() sets it to '1'."""
        monkeypatch.delenv("DISABLE_TELEMETRY", raising=False)

        apply_env_defaults()

        assert os.environ["DISABLE_TELEMETRY"] == "1"

    def test_apply_env_defaults_respects_existing(self, monkeypatch):
        """When DISABLE_TELEMETRY='0' is already set, apply_env_defaults() does NOT override it."""
        monkeypatch.setenv("DISABLE_TELEMETRY", "0")

        apply_env_defaults()

        assert os.environ["DISABLE_TELEMETRY"] == "0"

    def test_apply_env_defaults_idempotent(self, monkeypatch):
        """Calling apply_env_defaults() twice does not change the value."""
        monkeypatch.delenv("DISABLE_TELEMETRY", raising=False)

        apply_env_defaults()
        assert os.environ["DISABLE_TELEMETRY"] == "1"

        apply_env_defaults()
        assert os.environ["DISABLE_TELEMETRY"] == "1"

    def test_apply_env_defaults_idempotent_with_override(self, monkeypatch):
        """Calling apply_env_defaults() twice preserves a user-set override."""
        monkeypatch.setenv("DISABLE_TELEMETRY", "0")

        apply_env_defaults()
        apply_env_defaults()

        assert os.environ["DISABLE_TELEMETRY"] == "0"


class TestGetTelemetryDisabled:
    """Tests for get_telemetry_disabled()."""

    def test_get_telemetry_disabled_default(self, monkeypatch):
        """Returns True when DISABLE_TELEMETRY is not set (defaults to '1')."""
        monkeypatch.delenv("DISABLE_TELEMETRY", raising=False)

        assert get_telemetry_disabled() is True

    def test_get_telemetry_disabled_when_explicitly_one(self, monkeypatch):
        """Returns True when DISABLE_TELEMETRY='1'."""
        monkeypatch.setenv("DISABLE_TELEMETRY", "1")

        assert get_telemetry_disabled() is True

    def test_get_telemetry_disabled_when_enabled(self, monkeypatch):
        """Returns False when DISABLE_TELEMETRY='0' (telemetry enabled)."""
        monkeypatch.setenv("DISABLE_TELEMETRY", "0")

        assert get_telemetry_disabled() is False


class TestApplySubprocessEnvDefaults:
    """Tests for apply_subprocess_env_defaults()."""

    def test_apply_subprocess_env_defaults(self, monkeypatch):
        """Sets DISABLE_TELEMETRY on an env dict using the current os.environ value."""
        monkeypatch.delenv("DISABLE_TELEMETRY", raising=False)
        apply_env_defaults()  # sets os.environ["DISABLE_TELEMETRY"] = "1"

        env: dict = {}
        result = apply_subprocess_env_defaults(env)

        assert env["DISABLE_TELEMETRY"] == "1"
        # Returns the same dict (in-place mutation)
        assert result is env

    def test_apply_subprocess_env_defaults_inherits_override(self, monkeypatch):
        """When os.environ has DISABLE_TELEMETRY='0', var is absent from subprocess env."""
        monkeypatch.setenv("DISABLE_TELEMETRY", "0")

        env: dict = {}
        apply_subprocess_env_defaults(env)

        assert "DISABLE_TELEMETRY" not in env

    def test_apply_subprocess_env_defaults_overwrites_existing(self, monkeypatch):
        """Overwrites a pre-existing value in the env dict with the process-level value."""
        monkeypatch.setenv("DISABLE_TELEMETRY", "1")

        env = {"DISABLE_TELEMETRY": "0"}
        apply_subprocess_env_defaults(env)

        assert env["DISABLE_TELEMETRY"] == "1"

    def test_apply_subprocess_env_defaults_does_not_clear_other_keys(self, monkeypatch):
        """Does not remove unrelated keys from the env dict."""
        monkeypatch.setenv("DISABLE_TELEMETRY", "1")

        env = {"SOME_OTHER_VAR": "hello", "PATH": "/usr/bin"}
        apply_subprocess_env_defaults(env)

        assert env["SOME_OTHER_VAR"] == "hello"
        assert env["PATH"] == "/usr/bin"
        assert env["DISABLE_TELEMETRY"] == "1"


class TestPresenceBasedVars:
    """Test presence-based var handling (Claude Code checks existence, not value)."""

    def test_subprocess_removes_var_when_zero(self, monkeypatch):
        """When DISABLE_TELEMETRY=0, var should be completely removed from subprocess env."""
        monkeypatch.setenv("DISABLE_TELEMETRY", "0")
        env = {"DISABLE_TELEMETRY": "0", "OTHER": "value"}
        apply_subprocess_env_defaults(env)
        assert "DISABLE_TELEMETRY" not in env
        assert env["OTHER"] == "value"

    def test_subprocess_removes_var_when_zero_from_copy(self, monkeypatch):
        """Simulates real flow: os.environ.copy() then apply_subprocess_env_defaults."""
        monkeypatch.setenv("DISABLE_TELEMETRY", "0")
        env = os.environ.copy()
        apply_subprocess_env_defaults(env)
        assert "DISABLE_TELEMETRY" not in env

    def test_subprocess_keeps_var_when_one(self, monkeypatch):
        """When DISABLE_TELEMETRY=1, var should be present in subprocess env."""
        monkeypatch.setenv("DISABLE_TELEMETRY", "1")
        env = {}
        apply_subprocess_env_defaults(env)
        assert env["DISABLE_TELEMETRY"] == "1"

    def test_subprocess_sets_var_when_unset(self, monkeypatch):
        """When DISABLE_TELEMETRY not set, defaults to "1" (present in subprocess env)."""
        monkeypatch.delenv("DISABLE_TELEMETRY", raising=False)
        env = {}
        apply_subprocess_env_defaults(env)
        assert env["DISABLE_TELEMETRY"] == "1"


class TestEnvDefaultsRegistry:
    """Tests for the _ENV_DEFAULTS registry itself."""

    def test_disable_telemetry_in_registry(self):
        """DISABLE_TELEMETRY must be in _ENV_DEFAULTS with default '1'."""
        assert "DISABLE_TELEMETRY" in _ENV_DEFAULTS
        assert _ENV_DEFAULTS["DISABLE_TELEMETRY"] == "1"

    def test_disable_telemetry_in_presence_based_vars(self):
        """DISABLE_TELEMETRY must be in _PRESENCE_BASED_VARS."""
        assert "DISABLE_TELEMETRY" in _PRESENCE_BASED_VARS
