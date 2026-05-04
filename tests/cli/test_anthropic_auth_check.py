"""Tests for ``_check_anthropic_auth`` JSON variants.

WHY: Issue #464 reported that the doctor command surfaced "Not
Authenticated" warnings for enterprise/firstParty users even though
``claude auth status`` reported them as logged in. These tests cover the
JSON shapes that the modern ``claude`` CLI returns so we don't regress.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from claude_mpm.cli.startup import _check_anthropic_auth


class _FakeCompleted:
    def __init__(self, stdout: str, returncode: int = 0) -> None:
        self.stdout = stdout
        self.returncode = returncode
        self.stderr = ""


@pytest.fixture(autouse=True)
def _isolate_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure no real ANTHROPIC_API_KEY / Bedrock env leaks into tests."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("CLAUDE_CODE_USE_BEDROCK", raising=False)


def _run_with_stdout(stdout: str, *, isatty: bool = True) -> list[str]:
    """Invoke _check_anthropic_auth with mocked claude output, capture prints."""
    captured: list[str] = []

    def fake_print(*args, **_):
        captured.append(" ".join(str(a) for a in args))

    with (
        patch("subprocess.run", return_value=_FakeCompleted(stdout)),
        patch("sys.stdout.isatty", return_value=isatty),
        patch("builtins.print", side_effect=fake_print),
    ):
        # env_changes={} signals "config loaded, default backend" so the
        # check actually runs (None would short-circuit).
        _check_anthropic_auth(env_changes={})

    return captured


def test_claude_ai_consumer_is_authenticated() -> None:
    """``authMethod: claude.ai`` with ``loggedIn: true`` must pass silently."""
    stdout = json.dumps(
        {
            "loggedIn": True,
            "authMethod": "claude.ai",
            "apiProvider": "firstParty",
            "email": "user@example.com",
        }
    )

    captured = _run_with_stdout(stdout)

    # No "Not authenticated" warning should be printed.
    assert not any("Not authenticated" in line for line in captured), captured


def test_first_party_enterprise_is_authenticated() -> None:
    """Enterprise users (``apiProvider: firstParty``) must also be accepted."""
    stdout = json.dumps(
        {
            "loggedIn": True,
            "authMethod": "firstParty",
            "apiProvider": "firstParty",
            "orgName": "Enterprise Org",
        }
    )

    captured = _run_with_stdout(stdout)

    assert not any("Not authenticated" in line for line in captured), captured


def test_api_key_method_is_authenticated() -> None:
    """``authMethod: apiKey`` with ``loggedIn: true`` should still pass."""
    stdout = json.dumps({"loggedIn": True, "authMethod": "apiKey"})

    captured = _run_with_stdout(stdout)

    assert not any("Not authenticated" in line for line in captured), captured


def test_logged_in_string_true_is_accepted() -> None:
    """Some CLI variants emit ``"loggedIn": "true"`` as a string. Accept it."""
    stdout = '{"loggedIn": "true", "authMethod": "claude.ai"}'

    captured = _run_with_stdout(stdout)

    assert not any("Not authenticated" in line for line in captured), captured


def test_missing_logged_in_with_auth_method_is_accepted() -> None:
    """Older enterprise builds may omit ``loggedIn`` but include authMethod."""
    stdout = json.dumps({"authMethod": "firstParty", "apiProvider": "firstParty"})

    captured = _run_with_stdout(stdout)

    assert not any("Not authenticated" in line for line in captured), captured


def test_logged_in_false_warns() -> None:
    """When ``loggedIn`` is explicitly false we must warn the user."""
    stdout = json.dumps({"loggedIn": False})

    captured = _run_with_stdout(stdout)

    assert any("Not authenticated" in line for line in captured), captured


def test_plain_text_logged_in_legacy_cli() -> None:
    """Older CLI versions print plain text. Make sure that path still works."""
    stdout = "You are logged in as user@example.com"

    captured = _run_with_stdout(stdout)

    assert not any("Not authenticated" in line for line in captured), captured
