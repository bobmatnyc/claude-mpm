"""
Pytest configuration and fixtures for DeepEval evaluation tests.

Provides common fixtures for:
- Loading test scenarios
- Mock PM agent responses
- DeepEval test case setup
- Evidence collection utilities
"""

from pathlib import Path
from typing import Any, Dict, List

import pytest
import json


@pytest.fixture
def eval_root() -> Path:
    """Return the root directory for evaluation tests."""
    return Path(__file__).parent


@pytest.fixture
def scenarios_dir(eval_root: Path) -> Path:
    """Return the scenarios directory path."""
    return eval_root / "scenarios"


@pytest.fixture
def load_scenario_file(scenarios_dir: Path):
    """
    Fixture factory to load JSON scenario files.

    Usage:
        scenarios = load_scenario_file("ticketing_scenarios.json")
    """
    def _load(filename: str) -> Dict[str, Any]:
        file_path = scenarios_dir / filename
        if not file_path.exists():
            pytest.fail(f"Scenario file not found: {filename}")

        with open(file_path) as f:
            return json.load(f)

    return _load


@pytest.fixture
def ticketing_scenarios(load_scenario_file) -> List[Dict[str, Any]]:
    """Load ticketing delegation test scenarios."""
    data = load_scenario_file("ticketing_scenarios.json")
    return data.get("scenarios", [])


@pytest.fixture
def circuit_breaker_scenarios(load_scenario_file) -> List[Dict[str, Any]]:
    """Load circuit breaker test scenarios."""
    data = load_scenario_file("circuit_breaker_scenarios.json")
    return data.get("scenarios", [])


@pytest.fixture
def mock_pm_response():
    """
    Fixture factory to create mock PM agent responses.

    Usage:
        response = mock_pm_response(
            used_tools=["Task"],
            delegated_to="ticketing",
            assertions=["Ticket created successfully"]
        )
    """
    def _create_response(
        used_tools: List[str] = None,
        delegated_to: str = None,
        assertions: List[str] = None,
        evidence: Dict[str, Any] = None,
        response_text: str = ""
    ) -> Dict[str, Any]:
        return {
            "used_tools": used_tools or [],
            "delegated_to": delegated_to,
            "assertions": assertions or [],
            "evidence": evidence or {},
            "response_text": response_text,
        }

    return _create_response


@pytest.fixture
def pm_correct_delegation_response(mock_pm_response):
    """Mock PM response showing correct delegation to ticketing agent."""
    return mock_pm_response(
        used_tools=["Task"],
        delegated_to="ticketing",
        assertions=[
            "ticketing agent verified ticket creation",
            "Ticket ID: MPM-123 created successfully"
        ],
        evidence={
            "agent": "ticketing",
            "tool_used": "mcp__mcp-ticketer__ticket",
            "result": {"status": "success", "ticket_id": "MPM-123"}
        },
        response_text=(
            "I've delegated ticket creation to the ticketing agent. "
            "ticketing agent verified: Ticket MPM-123 created successfully "
            "with high priority and authentication tag."
        )
    )


@pytest.fixture
def pm_violation_response(mock_pm_response):
    """Mock PM response showing circuit breaker violation."""
    return mock_pm_response(
        used_tools=["mcp__mcp-ticketer__ticket", "WebFetch"],
        delegated_to=None,  # No delegation occurred
        assertions=["Ticket verified", "Issue is complete"],
        evidence={},  # No agent evidence
        response_text=(
            "I checked the ticket directly using mcp-ticketer. "
            "The ticket looks good and the issue is complete."
        )
    )


@pytest.fixture
def evidence_patterns():
    """Common evidence patterns for validation."""
    return {
        "agent_attribution": [
            r"\[agent_name\] (verified|confirmed|reported)",
            r"According to \[agent_name\]",
            r"\[agent_name\] agent (verified|tested|checked)",
        ],
        "forbidden_tools_pm": [
            r"mcp__mcp-ticketer__",
            r"WebFetch.*linear\.app",
            r"WebFetch.*github\.com/.*issues",
            r"aitrackdown",
        ],
        "correct_delegation": [
            r"Task\(agent=['\"]ticketing['\"]",
            r"I'll delegate to ticketing",
            r"Delegating to ticketing agent",
        ],
        "unverified_assertions": [
            r"(works|working|done|complete|ready|successful) without evidence",
            r"should (work|be ready|be complete)",
            r"looks (good|correct|fine)",
        ],
    }


@pytest.fixture
def deepeval_test_config():
    """Configuration for DeepEval test runs."""
    return {
        "threshold_delegation_correctness": 0.9,
        "threshold_instruction_faithfulness": 0.85,
        "threshold_evidence_quality": 0.8,
        "max_retries": 3,
        "timeout_seconds": 30,
    }


# Async fixtures for async test support
@pytest.fixture
async def async_pm_response_generator():
    """
    Async fixture for generating PM responses during test execution.

    Useful for testing real-time PM behavior simulation.
    """
    async def _generate(prompt: str, context: Dict[str, Any] = None):
        # This would integrate with actual PM agent in future
        # For now, return mock response structure
        return {
            "prompt": prompt,
            "context": context or {},
            "response": "Mock PM response",
            "metadata": {
                "tools_called": [],
                "delegation_occurred": False,
            }
        }

    return _generate


@pytest.fixture(scope="session")
def evaluation_results_dir(tmp_path_factory):
    """Create temporary directory for evaluation results."""
    return tmp_path_factory.mktemp("eval_results")


@pytest.fixture
def save_evaluation_result(evaluation_results_dir):
    """
    Fixture to save evaluation results for debugging.

    Usage:
        save_evaluation_result("test_name", result_dict)
    """
    def _save(test_name: str, result: Dict[str, Any]):
        output_file = evaluation_results_dir / f"{test_name}.json"
        with open(output_file, "w") as f:
            json.dump(result, f, indent=2)
        return output_file

    return _save
