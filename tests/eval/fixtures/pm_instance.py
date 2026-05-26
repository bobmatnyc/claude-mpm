"""
Pytest fixtures for PM tmux instance management.
"""

import pytest

from tests.eval.utils.tmux_pm_client import TmuxPMClient


@pytest.fixture(scope="module")
def tmux_pm():
    """
    Provide a tmux PM client for the test module.

    Skips tests if the mpm-eval tmux session is not running.
    """
    client = TmuxPMClient()

    if not client.is_running():
        pytest.skip(
            "mpm-eval tmux session not running. Start with:\n"
            "  tmux kill-session -t mpm-eval 2>/dev/null || true\n"
            "  tmux new-session -d -s mpm-eval -c /Volumes/Kemono/Users/masa/Projects/claude-mpm\n"
            "  tmux send-keys -t mpm-eval 'claude --model claude-haiku-4-5' Enter"
        )

    yield client

    # Optional: reset after all tests in module
    client.reset()


@pytest.fixture(autouse=True)
def reset_pm_between_tests(tmux_pm):
    """Reset PM state between tests by sending Ctrl+C."""
    yield
    tmux_pm.reset()
