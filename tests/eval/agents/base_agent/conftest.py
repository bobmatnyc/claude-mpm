"""
Pytest fixtures for BASE_AGENT test harness.

Provides fixtures for loading test scenarios and creating test cases.
"""

import json
from pathlib import Path
from typing import Any, Callable, Dict, List

import pytest


@pytest.fixture
def scenarios_dir() -> Path:
    """Get path to BASE_AGENT scenarios directory."""
    return Path(__file__).parent.parent.parent / "scenarios" / "base_agent"


@pytest.fixture
def load_scenarios(scenarios_dir: Path) -> Callable[[str], Dict[str, Any]]:
    """Create scenario loader function.

    Args:
        scenarios_dir: Path to scenarios directory

    Returns:
        Function that loads scenario JSON files
    """
    def _load(filename: str) -> Dict[str, Any]:
        """Load scenario file by name.

        Args:
            filename: Name of scenario file (e.g., "verification_scenarios.json")

        Returns:
            Parsed JSON scenario data
        """
        with open(scenarios_dir / filename) as f:
            return json.load(f)
    return _load


@pytest.fixture
def verification_scenarios(load_scenarios: Callable) -> List[Dict[str, Any]]:
    """Load verification protocol scenarios.

    Returns:
        List of verification test scenarios (VER-001 to VER-008)
    """
    return load_scenarios("verification_scenarios.json")["scenarios"]


@pytest.fixture
def memory_scenarios(load_scenarios: Callable) -> List[Dict[str, Any]]:
    """Load memory protocol scenarios.

    Returns:
        List of memory protocol test scenarios (MEM-001 to MEM-006)
    """
    return load_scenarios("memory_scenarios.json")["scenarios"]


@pytest.fixture
def template_scenarios(load_scenarios: Callable) -> List[Dict[str, Any]]:
    """Load template merging scenarios.

    Returns:
        List of template merging test scenarios (TPL-001 to TPL-003)
    """
    return load_scenarios("template_scenarios.json")["scenarios"]


@pytest.fixture
def orchestration_scenarios(load_scenarios: Callable) -> List[Dict[str, Any]]:
    """Load tool orchestration scenarios.

    Returns:
        List of orchestration test scenarios (ORC-001 to ORC-003)
    """
    return load_scenarios("orchestration_scenarios.json")["scenarios"]


@pytest.fixture
def get_scenario_by_id() -> Callable[[List[Dict], str], Dict[str, Any]]:
    """Create helper function to get scenario by ID.

    Returns:
        Function that finds scenario by scenario_id
    """
    def _get(scenarios: List[Dict[str, Any]], scenario_id: str) -> Dict[str, Any]:
        """Get scenario by ID.

        Args:
            scenarios: List of scenarios to search
            scenario_id: Scenario ID to find (e.g., "VER-001")

        Returns:
            Scenario dictionary

        Raises:
            ValueError: If scenario not found
        """
        for scenario in scenarios:
            if scenario["scenario_id"] == scenario_id:
                return scenario
        raise ValueError(f"Scenario {scenario_id} not found")
    return _get
