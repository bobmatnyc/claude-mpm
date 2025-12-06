"""BASE_AGENT behavioral scenarios for DeepEval Phase 2 testing.

This module contains scenario definitions for testing BASE_AGENT compliance across:
- Verification protocols
- Memory management
- Template inheritance
- Tool orchestration
"""

from pathlib import Path
import json

SCENARIO_DIR = Path(__file__).parent


def load_scenarios(category: str) -> list[dict]:
    """Load scenarios from a category file.

    Args:
        category: One of 'verification', 'memory', 'template', 'orchestration', 'all'

    Returns:
        List of scenario dictionaries
    """
    scenario_file = SCENARIO_DIR / f"{category}_scenarios.json"
    if not scenario_file.exists():
        return []

    with open(scenario_file) as f:
        data = json.load(f)
        return data.get("scenarios", [])


def get_all_scenarios() -> list[dict]:
    """Load all scenarios from all_scenarios.json."""
    return load_scenarios("all")


__all__ = ["load_scenarios", "get_all_scenarios"]
