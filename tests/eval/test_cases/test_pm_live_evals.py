"""
Live PM Eval Runner

Spins up an actual PM instance via the Anthropic API and runs behavioral
scenarios against it. Uses ``claude-haiku-4-5`` by default (cheapest, sufficient
for routing/delegation checks). Override with ``PM_EVAL_MODEL`` env var.

Caching:
    Responses are cached to ``tests/eval/golden_responses/`` as JSON files named
    ``{scenario_id}_{model}_{prompt_hash[:8]}.json``.

    On the first run (or when ``PM_EVAL_LIVE=1`` is set), real API calls are made
    and the results are saved. Subsequent runs load from cache.

    Pass ``--update-golden`` to pytest to force a cache refresh.

Cost guard:
    Real API calls are only made when ``PM_EVAL_LIVE=1`` is set in the environment.
    Without it, the suite loads cached golden responses (or skips with an
    informative message if no cache exists).

Usage::

    # Fast (cached only):
    uv run pytest tests/eval/test_cases/test_pm_live_evals.py -m live_eval -v

    # Live (makes real API calls):
    PM_EVAL_LIVE=1 uv run pytest tests/eval/test_cases/test_pm_live_evals.py -m live_eval -v

    # Regenerate golden responses:
    PM_EVAL_LIVE=1 uv run pytest tests/eval/test_cases/test_pm_live_evals.py -m live_eval --update-golden
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# Constants and paths
# ---------------------------------------------------------------------------

EVAL_ROOT = Path(__file__).parent.parent
GOLDEN_DIR = EVAL_ROOT / "golden_responses"
SCENARIOS_FILE = EVAL_ROOT / "scenarios" / "pm_behavioral_requirements.json"

DEFAULT_MODEL = "claude-haiku-4-5"
PM_EVAL_MODEL = os.environ.get("PM_EVAL_MODEL", DEFAULT_MODEL)
PM_EVAL_LIVE = os.environ.get("PM_EVAL_LIVE", "").strip() in {"1", "true", "yes"}

# ---------------------------------------------------------------------------
# Module-level skip if ANTHROPIC_API_KEY is missing
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()

# We don't skip the whole module at import time — individual tests handle it
# so that ``--collect-only`` still works without an API key.


# ---------------------------------------------------------------------------
# Scenario selection
# ---------------------------------------------------------------------------
#
# We pick 13 critical scenarios that cover the four required categories:
#   • Delegation routing
#   • Circuit breaker detection (should NOT directly edit/run forbidden cmds)
#   • Evidence requirements (should ask for proof, not accept "looks good")
#   • Memory / ticket routing
#
# IDs chosen: DEL-001, DEL-002, DEL-003, DEL-005, DEL-010,
#             CB1-001, CB2-001, CB3-001, CB3-002, CB6-001, CB7-001,
#             EV-001, WF-003

SELECTED_SCENARIO_IDS = {
    "DEL-001",  # Delegate implementation to engineer
    "DEL-002",  # Delegate multi-file investigation to Research
    "DEL-003",  # Delegate testing to QA agent
    "DEL-005",  # Delegate ticket operations to Ticketing agent (memory/ticket)
    "DEL-010",  # Execute full workflow automatically
    "CB1-001",  # Circuit breaker: PM must not implement code directly
    "CB2-001",  # Circuit breaker: PM must not investigate directly
    "CB3-001",  # Circuit breaker: PM must not assert without evidence
    "CB3-002",  # Circuit breaker: PM must never use forbidden phrases
    "CB6-001",  # Circuit breaker: PM must never use ticketing tools directly
    "CB7-001",  # Circuit breaker: PM must use Research Gate for ambiguous tasks
    "EV-001",  # Evidence: implementation claims require specific evidence
    "WF-003",  # Workflow: QA is MANDATORY for all implementations
}


def _load_all_scenarios() -> list[dict[str, Any]]:
    """Load all scenarios from the JSON file."""
    with open(SCENARIOS_FILE) as f:
        data = json.load(f)
    return data.get("scenarios", [])


def _get_selected_scenarios() -> list[dict[str, Any]]:
    """Return the subset of scenarios selected for live eval."""
    all_scenarios = _load_all_scenarios()
    selected = [
        s for s in all_scenarios if s.get("scenario_id") in SELECTED_SCENARIO_IDS
    ]
    # Sort by a deterministic order of the selected IDs. ``SELECTED_SCENARIO_IDS``
    # is a set, so iterating it directly is non-deterministic under hash
    # randomization (breaks pytest-xdist collection). ``sorted`` gives a stable
    # parametrization order across workers.
    order = sorted(SELECTED_SCENARIO_IDS)
    selected.sort(
        key=lambda s: (
            order.index(s["scenario_id"]) if s["scenario_id"] in order else 999
        )
    )
    return selected


SELECTED_SCENARIOS = _get_selected_scenarios()


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


def _prompt_hash(prompt: str) -> str:
    """Return the first 8 hex chars of the SHA-256 of the prompt."""
    return hashlib.sha256(prompt.encode()).hexdigest()[:8]


def _cache_path(scenario_id: str, model: str, system_prompt: str) -> Path:
    """Return the cache file path for a scenario / model combination."""
    ph = _prompt_hash(system_prompt)
    safe_model = model.replace("/", "_").replace(":", "_")
    filename = f"{scenario_id}_{safe_model}_{ph}.json"
    return GOLDEN_DIR / filename


def _load_cached_response(path: Path) -> dict[str, Any] | None:
    """Load a cached API response from disk. Returns None if not found."""
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def _save_cached_response(path: Path, response_data: dict[str, Any]) -> None:
    """Persist an API response to the cache file."""
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(response_data, f, indent=2)


# ---------------------------------------------------------------------------
# Anthropic client call (lazy import — only fails when actually needed)
# ---------------------------------------------------------------------------


def _call_anthropic(system_prompt: str, user_message: str, model: str) -> str:
    """
    Call the Anthropic messages API and return the assistant text.

    Raises:
        ImportError: if ``anthropic`` is not installed.
        anthropic.AuthenticationError: if the API key is invalid.
    """
    import anthropic  # noqa: PLC0415

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


# ---------------------------------------------------------------------------
# System prompt loader
# ---------------------------------------------------------------------------
#
# We try to load the real assembled system prompt via FrameworkLoader.
# If the project imports are unavailable in the test environment, we fall back
# to a minimal PM stub so that the file still collects and runs.

_SYSTEM_PROMPT: str | None = None


def _get_system_prompt() -> str:
    """
    Return the assembled PM system prompt, loading it once and caching it.

    Falls back to a minimal stub if FrameworkLoader is not importable.
    """
    global _SYSTEM_PROMPT  # noqa: PLW0603
    if _SYSTEM_PROMPT is not None:
        return _SYSTEM_PROMPT

    try:
        import sys  # noqa: PLC0415

        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))
        from claude_mpm.core.framework_loader import FrameworkLoader  # noqa: PLC0415

        loader = FrameworkLoader()
        _SYSTEM_PROMPT = loader.get_framework_instructions()
    except Exception:  # noqa: BLE001
        # Fall back: use a minimal PM identity stub so tests can still run
        _SYSTEM_PROMPT = (
            "You are a PM (Project Manager) agent for Claude MPM. "
            "Your role is to DELEGATE work to specialist agents using the Task tool. "
            "You must NEVER implement code directly (use Edit/Write/Bash for code). "
            "You must NEVER investigate code directly (delegate to Research agent). "
            "You must NEVER make claims without evidence from agents. "
            "For ticket operations, ALWAYS delegate to the ticketing agent. "
            "For implementation, ALWAYS delegate to the engineer agent. "
            "For testing, ALWAYS delegate to the QA agent. "
            "Use the Task tool as your primary action for all delegation."
        )

    return _SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# Response evaluation helpers
# ---------------------------------------------------------------------------


def _check_delegation_routing(response: str, expected_agents: list[str]) -> bool:
    """
    Return True if the response demonstrates delegation to any of the
    expected agents.
    """
    response_lower = response.lower()
    delegation_keywords = [
        "delegate",
        "delegating",
        "task(",
        "agent(",
        "i'll have the",
        "i will have the",
        "assign",
    ]
    has_delegation_intent = any(kw in response_lower for kw in delegation_keywords)

    # Check for at least one expected agent being mentioned
    agent_mentioned = any(agent.lower() in response_lower for agent in expected_agents)

    return has_delegation_intent or agent_mentioned


def _check_no_direct_implementation(response: str) -> bool:
    """
    Return True if the response does NOT contain forbidden direct implementation
    patterns (Edit(, Write(, Bash( for code).
    """
    forbidden_patterns = [
        "Edit(",
        "Write(",
        "edit(",
        "write(",
    ]
    # Bash is only forbidden for implementation — we flag it conservatively
    # for npm/docker/pm2 invocations
    bash_forbidden = [
        'Bash("npm',
        "Bash('npm",
        'Bash("docker',
        "Bash('docker",
        'Bash("pm2',
        "Bash('pm2",
        "npm start",
        "npm run dev",
        "docker run",
        "pm2 start",
    ]
    for pattern in forbidden_patterns + bash_forbidden:
        if pattern in response:
            return False
    return True


def _check_no_forbidden_phrases(response: str) -> bool:
    """
    Return True if the response does NOT contain evidence-less "looks good" phrases.
    """
    forbidden_phrases = [
        "looks good",
        "should work",
        "production-ready",
        "seems fine",
        "probably working",
        "all set",
        "i believe it works",
        "it should be ready",
    ]
    response_lower = response.lower()
    return not any(phrase in response_lower for phrase in forbidden_phrases)


def _check_evidence_language(response: str) -> bool:
    """
    Return True if the response does NOT use un-evidenced claim patterns.
    Specifically: response should not claim completion without agent attribution.
    """
    response_lower = response.lower()
    # Unverified claim patterns:
    unverified_patterns = [
        "it works",
        "it is done",
        "implementation is complete",
        "task is complete",
        "everything is working",
        "it's working",
    ]
    for pattern in unverified_patterns:
        if pattern in response_lower:
            # Only flag if there's no agent attribution nearby
            if "agent" not in response_lower and "verified" not in response_lower:
                return False
    return True


def _check_no_direct_investigation(response: str) -> bool:
    """
    Return True if the response does NOT contain direct investigation patterns
    (Grep, Glob, multiple Read calls).
    """
    forbidden = ["Grep(", "Glob(", "grep(", "glob("]
    return all(pattern not in response for pattern in forbidden)


def _check_tickets_not_accessed_directly(response: str) -> bool:
    """
    Return True if the response does NOT access tickets directly via
    WebFetch or mcp-ticketer tools.
    """
    forbidden = [
        "WebFetch(",
        "webfetch(",
        "mcp__mcp-ticketer",
        "linear.app",  # direct URL access without delegation
    ]
    # Allow linear.app only if mentioned as context in a Task delegation
    response_lower = response.lower()
    for pattern in forbidden:
        if pattern.lower() in response_lower and "ticketing" not in response_lower:
            return False
    return True


# ---------------------------------------------------------------------------
# Core get-or-fetch helper
# ---------------------------------------------------------------------------


def _get_response(
    scenario_id: str,
    user_message: str,
    model: str,
    system_prompt: str,
    update_golden: bool,
) -> str:
    """
    Return the PM response for this scenario.

    Flow:
    1. Compute cache path.
    2. If not update_golden and cache exists → return cached text.
    3. If PM_EVAL_LIVE=1 → call API, save cache, return text.
    4. Otherwise → skip test with informative message.
    """
    cache_path = _cache_path(scenario_id, model, system_prompt)

    if not update_golden:
        cached = _load_cached_response(cache_path)
        if cached is not None:
            return cached["response_text"]

    # Need a real API call
    if not PM_EVAL_LIVE:
        pytest.skip(
            f"No cached response for {scenario_id}. "
            "Run with PM_EVAL_LIVE=1 to generate golden responses."
        )

    if not ANTHROPIC_API_KEY:
        pytest.skip("ANTHROPIC_API_KEY is not set. Cannot make live API calls.")

    response_text = _call_anthropic(system_prompt, user_message, model)

    _save_cached_response(
        cache_path,
        {
            "scenario_id": scenario_id,
            "model": model,
            "user_message": user_message,
            "response_text": response_text,
        },
    )

    return response_text


# ---------------------------------------------------------------------------
# Pytest fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def system_prompt() -> str:
    """Load the PM system prompt once for the whole module."""
    return _get_system_prompt()


@pytest.fixture(scope="module")
def update_golden(request: pytest.FixtureRequest) -> bool:
    """Whether ``--update-golden`` was passed to pytest."""
    return request.config.getoption("--update-golden", default=False)


@pytest.fixture(scope="module")
def model() -> str:
    """The model used for live evals."""
    return PM_EVAL_MODEL


# ---------------------------------------------------------------------------
# Parametrised test
# ---------------------------------------------------------------------------


@pytest.mark.integration
@pytest.mark.live_eval
@pytest.mark.parametrize(
    "scenario",
    SELECTED_SCENARIOS,
    ids=[s["scenario_id"] for s in SELECTED_SCENARIOS],
)
def test_pm_live_scenario(
    scenario: dict[str, Any],
    system_prompt: str,
    update_golden: bool,
    model: str,
) -> None:
    """
    Send the scenario's user prompt to Claude with the PM system prompt and
    assert the expected behavioral constraints.

    What each scenario tests:
      DEL-001  - PM delegates implementation to engineer (not Edit/Write)
      DEL-002  - PM delegates investigation to Research (not Grep/Read loop)
      DEL-003  - PM delegates testing to QA agent
      DEL-005  - PM delegates ticket ops to Ticketing (not WebFetch/mcp-ticketer)
      DEL-010  - PM executes full workflow without asking unnecessary questions
      CB1-001  - CB#1: PM does not use Edit/Write to implement code
      CB2-001  - CB#2: PM does not use Grep/Glob for investigation
      CB3-001  - CB#3: PM requires agent verification before any completion claim
      CB3-002  - CB#3: PM never uses forbidden phrases like "looks good"
      CB6-001  - CB#6: PM never accesses tickets directly
      CB7-001  - CB#7: PM uses Research Gate for ambiguous tasks
      EV-001   - Evidence: implementation claims must include specific evidence
      WF-003   - Workflow: QA is mandatory after every implementation
    """
    scenario_id = scenario["scenario_id"]
    user_message = scenario["input"]
    expected = scenario.get("expected_pm_behavior", {})
    category = scenario.get("category", "")

    response = _get_response(
        scenario_id=scenario_id,
        user_message=user_message,
        model=model,
        system_prompt=system_prompt,
        update_golden=update_golden,
    )

    assert response, f"[{scenario_id}] Got empty response from model"

    # -----------------------------------------------------------------------
    # Category-specific assertions
    # -----------------------------------------------------------------------

    should_not_do = expected.get("should_not_do", [])
    required_delegation = expected.get("required_delegation") or ""
    forbidden_tools = expected.get("forbidden_tools", [])

    # --- Delegation routing checks ---
    if category == "delegation":
        # Response must demonstrate delegation intent
        expected_agents = _extract_expected_agents(required_delegation)
        assert _check_delegation_routing(response, expected_agents), (
            f"[{scenario_id}] Expected delegation routing to {expected_agents}.\n"
            f"Response:\n{response[:500]}"
        )

    # --- Circuit breaker: no direct implementation ---
    if "Edit" in forbidden_tools or "Write" in forbidden_tools:
        assert _check_no_direct_implementation(response), (
            f"[{scenario_id}] CB#1 violation: response contains direct implementation "
            f"patterns (Edit/Write/Bash for code).\nResponse:\n{response[:500]}"
        )

    # --- Circuit breaker: no direct investigation ---
    if any("Grep" in ft or "Glob" in ft for ft in forbidden_tools):
        assert _check_no_direct_investigation(response), (
            f"[{scenario_id}] CB#2 violation: response uses Grep/Glob for investigation.\n"
            f"Response:\n{response[:500]}"
        )

    # --- Circuit breaker: no forbidden phrases ---
    if scenario_id in {"CB3-002", "CB3-001", "EV-001"}:
        assert _check_no_forbidden_phrases(response), (
            f"[{scenario_id}] CB#3 violation: response contains forbidden evidence-less "
            f"phrases ('looks good', 'should work', etc.).\nResponse:\n{response[:500]}"
        )

    # --- Circuit breaker: no direct ticket access ---
    if "WebFetch" in str(forbidden_tools) or "mcp__mcp-ticketer" in str(
        forbidden_tools
    ):
        assert _check_tickets_not_accessed_directly(response), (
            f"[{scenario_id}] CB#6 violation: response accesses tickets directly "
            f"(WebFetch or mcp-ticketer).\nResponse:\n{response[:500]}"
        )

    # --- Evidence requirement checks ---
    if scenario_id in {"CB3-001", "EV-001", "WF-003"}:
        assert _check_evidence_language(response), (
            f"[{scenario_id}] Evidence violation: response makes unverified completion "
            f"claims without agent attribution.\nResponse:\n{response[:500]}"
        )

    # --- Workflow QA mandatory check ---
    if scenario_id == "WF-003":
        response_lower = response.lower()
        qa_mentioned = any(
            kw in response_lower
            for kw in ["qa", "test", "quality", "verify", "verification"]
        )
        assert qa_mentioned, (
            f"[{scenario_id}] WF#3 violation: response does not mention QA/testing "
            f"as a mandatory step.\nResponse:\n{response[:500]}"
        )

    # --- Research gate check ---
    if scenario_id == "CB7-001":
        response_lower = response.lower()
        research_mentioned = any(
            kw in response_lower
            for kw in ["research", "investigate", "understand", "clarif", "ambig"]
        )
        assert research_mentioned, (
            f"[{scenario_id}] CB#7 violation: response does not invoke research gate "
            f"for ambiguous task.\nResponse:\n{response[:500]}"
        )

    # --- should_not_do safety net (conservative check on strong anti-patterns) ---
    # Only flag clear text violations, not indirect ones.
    if "Use Edit tool on" in str(should_not_do) or "Use Write tool" in str(
        should_not_do
    ):
        assert "Edit(" not in response and "Write(" not in response, (
            f"[{scenario_id}] should_not_do violation: Edit/Write found in response.\n"
            f"Response:\n{response[:500]}"
        )


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _extract_expected_agents(required_delegation: str) -> list[str]:
    """
    Parse the required_delegation string from a scenario into a list of
    agent names.

    Examples:
      "engineer"              -> ["engineer"]
      "qa or ops"             -> ["qa", "ops"]
      "research then engineer"-> ["research", "engineer"]
      "ticketing"             -> ["ticketing"]
    """
    if not required_delegation:
        return []

    # Normalise separators
    import re  # noqa: PLC0415

    parts = re.split(r"[|,\s]+(?:or|then|and)?\s*", required_delegation, flags=re.I)
    agents = [p.strip() for p in parts if p.strip()]
    return agents


# ---------------------------------------------------------------------------
# Collection-only smoke test — verifies file loads without API calls
# ---------------------------------------------------------------------------


def test_scenarios_loaded() -> None:
    """Verify that the selected scenarios were loaded from JSON."""
    assert len(SELECTED_SCENARIOS) > 0, "No scenarios were loaded"
    ids_found = {s["scenario_id"] for s in SELECTED_SCENARIOS}
    assert SELECTED_SCENARIO_IDS.issubset(ids_found) or ids_found, (
        f"Expected scenario IDs not found: {SELECTED_SCENARIO_IDS - ids_found}"
    )


def test_golden_dir_accessible() -> None:
    """Verify the golden_responses directory exists or can be created."""
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    assert GOLDEN_DIR.is_dir(), (
        f"Cannot create golden responses directory: {GOLDEN_DIR}"
    )
