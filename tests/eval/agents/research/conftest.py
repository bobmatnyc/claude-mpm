"""
Pytest fixtures for Research Agent test harness.

Provides fixtures for loading test scenarios and creating test cases.
"""

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest


@pytest.fixture
def scenarios_dir() -> Path:
    """Get path to Research Agent scenarios directory."""
    return Path(__file__).parent.parent.parent / "scenarios" / "research"


@pytest.fixture
def load_scenarios(scenarios_dir: Path) -> Callable[[str], dict[str, Any]]:
    """Create scenario loader function.

    Args:
        scenarios_dir: Path to scenarios directory

    Returns:
        Function that loads scenario JSON files
    """

    def _load(filename: str) -> dict[str, Any]:
        """Load scenario file by name.

        Args:
            filename: Name of scenario file (e.g., "memory_scenarios.json")

        Returns:
            Parsed JSON scenario data
        """
        with open(scenarios_dir / filename) as f:
            return json.load(f)

    return _load


@pytest.fixture
def memory_scenarios(load_scenarios: Callable) -> list[dict[str, Any]]:
    """Load memory protocol scenarios.

    Returns:
        List of memory efficiency test scenarios (MEM-R-001 to MEM-R-006)
    """
    return load_scenarios("memory_scenarios.json")["scenarios"]


@pytest.fixture
def discovery_scenarios(load_scenarios: Callable) -> list[dict[str, Any]]:
    """Load discovery pattern scenarios.

    Returns:
        List of discovery pattern test scenarios (DSC-R-001 to DSC-R-005)
    """
    return load_scenarios("discovery_scenarios.json")["scenarios"]


@pytest.fixture
def output_scenarios(load_scenarios: Callable) -> list[dict[str, Any]]:
    """Load output requirements scenarios.

    Returns:
        List of output requirement test scenarios (OUT-R-001 to OUT-R-004)
    """
    return load_scenarios("output_scenarios.json")["scenarios"]


@pytest.fixture
def get_scenario_by_id() -> Callable[[list[dict], str], dict[str, Any]]:
    """Create helper function to get scenario by ID.

    Returns:
        Function that finds scenario by scenario_id
    """

    def _get(scenarios: list[dict[str, Any]], scenario_id: str) -> dict[str, Any]:
        """Get scenario by ID.

        Args:
            scenarios: List of scenarios to search
            scenario_id: Scenario ID to find (e.g., "MEM-R-001")

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
