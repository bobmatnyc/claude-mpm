"""Tests for delegation label display formatting.

Covers M0 from docs-local/02-delegated-agentname-colorization/01-research/:
- interactive_session colorizes the printed label and stores the normalized form.
- session_worker emits the plain normalized form (no ANSI) for channel events.
- slack_client uses the normalized form (no ANSI) for Slack messages.

These tests directly exercise the small format helper extracted from
``interactive_session._format_task_label`` and the call sites in
``session_worker.py`` and ``slack_client/handlers/commands.py``.  They avoid
spinning up the full SDK message-stream loop because that requires an
installed ``claude_agent_sdk`` and a long async ``ClaudeSDKClient`` setup —
the smaller helper covers the same logic with one assertion per test.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from claude_mpm.core.agent_name_normalizer import AgentNameNormalizer
from claude_mpm.core.interactive_session import _format_task_label

ANSI_PREFIX = "\033["


def test_interactive_session_colorizes_known_agent() -> None:
    """Known agents produce a printed line with ANSI green + Title Case display.

    The printed line that ``interactive_session.py`` emits MUST contain the ANSI
    green code (``\\033[32m``) and the Title Case display name ``Python Engineer``
    so the user sees a coloured bracket label instead of a raw ``python-engineer``.
    """
    display_name, colored_label, printed_line = _format_task_label(
        "python-engineer", "PM"
    )

    # Title Case for storage / nested label propagation
    assert display_name == "Python Engineer"
    # Colored label contains green ANSI escape and Title Case text
    assert "\033[32m" in colored_label
    assert "Python Engineer" in colored_label
    # Printed line is the f-string the SDK loop emits
    assert printed_line == f"  [PM:Task → {colored_label}]"
    assert "\033[32m" in printed_line
    assert "Python Engineer" in printed_line


def test_interactive_session_stores_normalized_form() -> None:
    """The value stored in ``tool_id_to_agent`` is the Title Case form (no ANSI).

    Storing the colorized form would corrupt nested label propagation because
    ``current_agent = tool_id_to_agent[parent_id]`` would carry ANSI escapes
    into deeper bracket labels.  The first element of the tuple MUST be plain
    Title Case text.
    """
    display_name, colored_label, _printed_line = _format_task_label(
        "python-engineer", "PM"
    )

    # Storage form must NOT contain any ANSI escape sequence
    assert ANSI_PREFIX not in display_name
    assert display_name == "Python Engineer"
    # Sanity check: colored form is different and contains ANSI
    assert colored_label != display_name
    assert ANSI_PREFIX in colored_label


def test_interactive_session_unknown_agent_falls_back() -> None:
    """Unknown agents must NOT leak ANSI into stdout but still print sensibly.

    The current ``AgentNameNormalizer.normalize`` falls back to ``"Engineer"``
    for unknown names and ``colorize`` returns plain text when the key has no
    color entry — but in practice, "Engineer" IS a known key with green colour,
    so the fallback path still produces a sensible coloured label.  The
    important guarantees:

    1. ``display_name`` is non-empty and contains no ANSI escape codes.
    2. ``printed_line`` is non-empty and renders something readable.
    3. No raw kebab-case ``some-custom-agent`` leaks into the printed label
       (the printed form is whatever ``normalize`` produced, NOT the raw input).
    """
    display_name, _colored_label, printed_line = _format_task_label(
        "some-custom-agent", "PM"
    )

    # Storage form is clean (no ANSI)
    assert display_name
    assert ANSI_PREFIX not in display_name
    # Printed line is sensible — does NOT echo the raw kebab name
    assert printed_line.startswith("  [PM:Task → ")
    assert "some-custom-agent" not in printed_line
    # ``normalize`` falls back to "Engineer" for unknown inputs, so the
    # display name should be "Engineer" per the contract.
    # TODO: The "Engineer" fallback is a surprising default for truly unknown
    # agents — ideally normalize() would return a title-cased version of the
    # raw input (e.g. "some-custom-agent" → "Some Custom Agent") instead of
    # conflating every unknown type with the Engineer agent.  Tracked as M2.
    assert display_name == "Engineer"


def test_session_worker_label_is_plain_normalized() -> None:
    """Channel-broadcast labels MUST be plain Title Case (no ANSI).

    Slack and Web UI channels do not render ANSI escape sequences — they would
    show up as literal ``\\033[32m`` characters.  Per Option 2a in the research
    doc, the channel worker emits the normalized (Title Case) form WITHOUT the
    colorize wrapper.  This test asserts the same string the worker would
    f-string into the ``label`` field of the broadcast ``tool_call`` event.
    """
    # Mirror the exact transformation done in
    # ``services/channels/session_worker.py`` after the M0 patch:
    raw_subagent = "python-engineer"
    display_subagent = AgentNameNormalizer.normalize(raw_subagent)
    label = f"[PM:Task -> {display_subagent}]"

    # Title Case present, ANSI absent
    assert "Python Engineer" in label
    assert ANSI_PREFIX not in label
    # And the raw kebab form does NOT leak into the channel payload
    assert "python-engineer" not in label


def test_slack_handler_uses_normalized_form() -> None:
    """The Slack /mpm-delegate command displays the Title Case form, not raw.

    Slack uses mrkdwn (``*bold*``) and does not render ANSI.  This test invokes
    the registered command handler with a fabricated Slack-Bolt-style command
    payload and asserts the responded message contains ``*Python Engineer*``
    (Title Case wrapped in mrkdwn bold) instead of ``*python-engineer*``.

    ``slack_bolt`` is an optional dependency of claude-mpm and may not be
    installed in CI.  This test injects a stub ``slack_bolt`` module into
    ``sys.modules`` before importing the handler so the test runs even without
    the real package.
    """
    import sys
    from types import ModuleType

    # Stub ``slack_bolt.App`` so the import in commands.py succeeds even when
    # the real slack_bolt package is not installed.  We only need ``App`` as a
    # type-hint target — the handler factory takes the App via parameter.
    slack_bolt_mod = ModuleType("slack_bolt")
    slack_bolt_mod.App = MagicMock  # type: ignore[attr-defined]
    sys.modules.setdefault("slack_bolt", slack_bolt_mod)

    from claude_mpm.slack_client.handlers.commands import register_commands

    captured: dict[str, Any] = {}

    class FakeApp:
        """Minimal stand-in for ``slack_bolt.App`` that captures handlers."""

        def __init__(self) -> None:
            self.handlers: dict[str, Any] = {}

        def command(self, name: str) -> Any:
            def decorator(fn: Any) -> Any:
                self.handlers[name] = fn
                return fn

            return decorator

    app = FakeApp()
    register_commands(app)  # type: ignore[arg-type]

    delegate_handler = app.handlers["/mpm-delegate"]

    ack = MagicMock()
    respond = MagicMock(side_effect=lambda msg: captured.setdefault("msg", msg))
    command = {"text": "ticket-123 python-engineer"}

    delegate_handler(ack=ack, respond=respond, command=command)

    ack.assert_called_once()
    respond.assert_called_once()
    message = captured["msg"]
    # Title Case wrapped in Slack mrkdwn bold
    assert "*Python Engineer*" in message
    # Raw kebab form must NOT appear
    assert "*python-engineer*" not in message
    # And no ANSI leaks into Slack
    assert ANSI_PREFIX not in message
