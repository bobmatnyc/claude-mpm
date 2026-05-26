"""
Tmux-based behavioral evaluation tests for PM.

These tests exercise the PM against a running claude-mpm instance in tmux,
providing the most realistic evaluation environment. Tests are skipped
if the mpm-eval tmux session is not running.

Run with:
  PM_EVAL_TMUX=1 uv run pytest tests/eval/ -m tmux_eval -v
"""

import os

import pytest

from tests.eval.fixtures.pm_instance import reset_pm_between_tests, tmux_pm

# Cost guard: only run if explicitly enabled
pytestmark = [
    pytest.mark.skipif(
        not os.getenv("PM_EVAL_TMUX"),
        reason="PM_EVAL_TMUX environment variable not set. Set to enable tmux evals.",
    ),
    pytest.mark.tmux_eval,
]


# Test scenarios (same 13 as API evals, but via tmux interaction)
SCENARIOS = [
    {
        "id": "agent_delegation_basic",
        "user_prompt": "Can you help me understand how to delegate work to subagents?",
        "expected_patterns": ["agent", "delegate", "subagent"],
        "forbidden_patterns": ["error", "failed"],
    },
    {
        "id": "agent_delegation_specific_task",
        "user_prompt": "I have a code review task. Which agent would you delegate this to?",
        "expected_patterns": ["engineer", "reviewer", "code", "review"],
        "forbidden_patterns": ["error", "not applicable"],
    },
    {
        "id": "pm_orchestration_workflow",
        "user_prompt": "Walk me through a typical PM orchestration workflow for a feature request.",
        "expected_patterns": ["workflow", "plan", "orchestrate", "agent"],
        "forbidden_patterns": ["unclear", "error"],
    },
    {
        "id": "skill_discovery",
        "user_prompt": "What skills are available to me in this project?",
        "expected_patterns": ["skill", "available", "list"],
        "forbidden_patterns": ["none", "not found"],
    },
    {
        "id": "mcp_integration",
        "user_prompt": "How do I integrate a new MCP server into this project?",
        "expected_patterns": ["mcp", "server", "integration"],
        "forbidden_patterns": ["error", "unsupported"],
    },
    {
        "id": "session_management",
        "user_prompt": "How do I manage sessions in Claude MPM?",
        "expected_patterns": ["session", "manage", "save", "resume"],
        "forbidden_patterns": ["error", "not available"],
    },
    {
        "id": "memory_system",
        "user_prompt": "Tell me about the memory system in Claude MPM.",
        "expected_patterns": ["memory", "persistent", "knowledge"],
        "forbidden_patterns": ["error", "not implemented"],
    },
    {
        "id": "config_hierarchy",
        "user_prompt": "What is the configuration hierarchy in Claude MPM?",
        "expected_patterns": ["config", "settings", "hierarchy"],
        "forbidden_patterns": ["error", "unknown"],
    },
    {
        "id": "agent_failure_recovery",
        "user_prompt": "How does the system handle agent failures?",
        "expected_patterns": ["recovery", "failure", "handle"],
        "forbidden_patterns": ["crash", "undefined"],
    },
    {
        "id": "custom_skill_development",
        "user_prompt": "How do I develop a custom skill for Claude MPM?",
        "expected_patterns": ["skill", "develop", "create", "custom"],
        "forbidden_patterns": ["error", "not supported"],
    },
    {
        "id": "monitoring_logging",
        "user_prompt": "What monitoring and logging capabilities does Claude MPM provide?",
        "expected_patterns": ["monitor", "log", "observe"],
        "forbidden_patterns": ["error", "not available"],
    },
    {
        "id": "performance_optimization",
        "user_prompt": "How can I optimize PM performance for large projects?",
        "expected_patterns": ["performance", "optimize", "large"],
        "forbidden_patterns": ["error", "not possible"],
    },
    {
        "id": "security_best_practices",
        "user_prompt": "What are the security best practices for using Claude MPM?",
        "expected_patterns": ["security", "practice", "best"],
        "forbidden_patterns": ["error", "unsafe"],
    },
]


@pytest.mark.parametrize(
    "scenario",
    SCENARIOS,
    ids=[s["id"] for s in SCENARIOS],
)
def test_pm_tmux_scenario(tmux_pm, reset_pm_between_tests, scenario):
    """Test PM behavior via tmux interaction."""
    response = tmux_pm.send_prompt(scenario["user_prompt"], timeout=45)

    # Check expected patterns
    for pattern in scenario["expected_patterns"]:
        assert pattern.lower() in response.lower(), (
            f"Expected pattern '{pattern}' not found in response for "
            f"scenario '{scenario['id']}'\n"
            f"Response: {response[:500]}"
        )

    # Check forbidden patterns
    for pattern in scenario["forbidden_patterns"]:
        assert pattern.lower() not in response.lower(), (
            f"Forbidden pattern '{pattern}' found in response for "
            f"scenario '{scenario['id']}'\n"
            f"Response: {response[:500]}"
        )
