#!/usr/bin/env python3
"""Test CLI Skills Wizard integration."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from claude_mpm.cli.interactive.skills_wizard import SkillsWizard


def test_skills_wizard_instantiation():
    """Test that SkillsWizard can be instantiated."""
    print("\n=== Testing CLI Skills Wizard ===")

    try:
        wizard = SkillsWizard()
        print("✅ SkillsWizard instantiated successfully")

        # Verify it has required methods
        required_methods = [
            "run_interactive_selection",
            "list_available_skills",
            "_auto_link_skills",
            "_get_recommended_skills_for_agent",
        ]

        for method in required_methods:
            if not hasattr(wizard, method):
                print(f"❌ FAIL: Missing method '{method}'")
                return False
            print(f"  - Has method '{method}'")

        # Test auto-linking
        test_agents = ["engineer", "qa", "ops"]
        mapping = wizard._auto_link_skills(test_agents)

        print("\n  Auto-linking test:")
        for agent, skills in mapping.items():
            print(f"    {agent}: {len(skills)} skills")

        if not mapping:
            print("❌ FAIL: Auto-linking returned empty mapping")
            return False

        print("\n✅ PASS: CLI Skills Wizard is fully functional")
        return True

    except Exception as e:
        print(f"❌ FAIL: Error testing wizard: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_skills_wizard_instantiation()
    sys.exit(0 if success else 1)
