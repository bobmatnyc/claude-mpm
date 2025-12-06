"""Research Agent behavioral scenarios for DeepEval Phase 2.

This module provides scenario loading for Research Agent evaluation:
- Memory Management Protocol (6 scenarios)
- Discovery Pattern Protocol (5 scenarios)
- Output Requirements (4 scenarios)

Total: 15 scenarios testing Research Agent instruction adherence.
"""

import json
from pathlib import Path
from typing import Any

SCENARIOS_DIR = Path(__file__).parent


def load_scenarios(category: str) -> list[dict[str, Any]]:
    """Load scenarios for a specific category.

    Args:
        category: Scenario category (memory, discovery, output, or all)

    Returns:
        List of scenario dictionaries

    Raises:
        FileNotFoundError: If scenario file doesn't exist
        ValueError: If category is invalid
    """
    valid_categories = {"memory", "discovery", "output", "all"}
    if category not in valid_categories:
        raise ValueError(
            f"Invalid category '{category}'. Must be one of: {valid_categories}"
        )

    scenario_file = SCENARIOS_DIR / f"{category}_scenarios.json"
    if not scenario_file.exists():
        raise FileNotFoundError(f"Scenario file not found: {scenario_file}")

    with open(scenario_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data.get("scenarios", [])


def get_all_scenarios() -> list[dict[str, Any]]:
    """Load all Research Agent scenarios across all categories.

    Returns:
        Combined list of all 15 scenarios
    """
    return load_scenarios("all")


def get_scenarios_by_priority(priority: str) -> list[dict[str, Any]]:
    """Filter scenarios by priority level.

    Args:
        priority: Priority level (critical, high, medium, low)

    Returns:
        Scenarios matching the priority level
    """
    all_scenarios = get_all_scenarios()
    return [s for s in all_scenarios if s.get("priority") == priority]


def get_scenario_by_id(scenario_id: str) -> dict[str, Any] | None:
    """Find scenario by ID across all categories.

    Args:
        scenario_id: Scenario identifier (e.g., "MEM-R-001")

    Returns:
        Scenario dict if found, None otherwise
    """
    all_scenarios = get_all_scenarios()
    for scenario in all_scenarios:
        if scenario.get("scenario_id") == scenario_id:
            return scenario
    return None


__all__ = [
    "load_scenarios",
    "get_all_scenarios",
    "get_scenarios_by_priority",
    "get_scenario_by_id",
]
