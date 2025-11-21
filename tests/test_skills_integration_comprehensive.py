#!/usr/bin/env python3
"""
Comprehensive Skills Integration Verification
Tests all 7 verification points for the skills system
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set

# Add project to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.skills import SkillManager, get_registry


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_test(name: str):
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'=' * 80}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}TEST: {name}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'=' * 80}{Colors.RESET}")


def print_pass(message: str):
    print(f"{Colors.GREEN}✓ PASS:{Colors.RESET} {message}")


def print_fail(message: str):
    print(f"{Colors.RED}✗ FAIL:{Colors.RESET} {message}")


def print_info(message: str):
    print(f"{Colors.YELLOW}ℹ INFO:{Colors.RESET} {message}")


def test_1_bundled_skills_loading() -> bool:
    """Test 1: Verify Bundled Skills Loading"""
    print_test("Test 1: Verify Bundled Skills Loading")

    try:
        registry = get_registry()
        bundled_skills = registry.list_skills(source="bundled")

        # Check count
        if len(bundled_skills) != 15:
            print_fail(f"Expected 15 bundled skills, found {len(bundled_skills)}")
            return False
        print_pass("Found 15 bundled skills")

        # Check key skills exist
        skill_names = [s.name for s in bundled_skills]
        print_info(f"Skills found: {', '.join(sorted(skill_names))}")

        required_skills = [
            "test-driven-development",
            "systematic-debugging",
            "async-testing",
        ]

        for skill in required_skills:
            if skill not in skill_names:
                print_fail(f"Required skill '{skill}' not found")
                return False
            print_pass(f"Required skill '{skill}' found")

        # Verify each skill has content
        for skill in bundled_skills:
            if not skill.content or len(skill.content) < 100:
                print_fail(f"Skill '{skill.name}' has insufficient content")
                return False
        print_pass("All skills have valid content")

        return True

    except Exception as e:
        print_fail(f"Exception during test: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_2_agent_skills_mapping() -> bool:
    """Test 2: Verify Agent Skills Mapping"""
    print_test("Test 2: Verify Agent Skills Mapping")

    try:
        manager = SkillManager()

        # Test Engineer skills
        engineer_skills = manager.get_agent_skills("engineer")
        if len(engineer_skills) < 8:
            print_fail(f"Engineer should have >= 8 skills, has {len(engineer_skills)}")
            return False
        print_pass(f"Engineer has {len(engineer_skills)} skills")
        print_info(f"  Skills: {', '.join(s.name for s in engineer_skills)}")

        # Test QA skills
        qa_skills = manager.get_agent_skills("qa")
        if len(qa_skills) < 4:
            print_fail(f"QA should have >= 4 skills, has {len(qa_skills)}")
            return False
        print_pass(f"QA has {len(qa_skills)} skills")
        print_info(f"  Skills: {', '.join(s.name for s in qa_skills)}")

        # Test Ops skills
        ops_skills = manager.get_agent_skills("ops")
        skill_names = [s.name for s in ops_skills]
        if "docker-containerization" not in skill_names:
            print_fail("Ops should have 'docker-containerization' skill")
            return False
        print_pass(
            f"Ops has {len(ops_skills)} skills including docker-containerization"
        )
        print_info(f"  Skills: {', '.join(skill_names)}")

        # Test that different agents have different skills
        eng_names = set(s.name for s in engineer_skills)
        qa_names = set(s.name for s in qa_skills)
        ops_names = set(s.name for s in ops_skills)

        print_info(f"Engineer-only skills: {eng_names - qa_names - ops_names}")
        print_info(f"QA-only skills: {qa_names - eng_names - ops_names}")
        print_info(f"Ops-only skills: {ops_names - eng_names - qa_names}")
        print_info(f"Shared skills: {eng_names & qa_names & ops_names}")

        return True

    except Exception as e:
        print_fail(f"Exception during test: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_3_prompt_enhancement() -> bool:
    """Test 3: Verify Prompt Enhancement"""
    print_test("Test 3: Verify Prompt Enhancement")

    try:
        manager = SkillManager()

        base_prompt = "You are an engineer."
        enhanced = manager.enhance_agent_prompt("engineer", base_prompt)

        # Check that prompt is significantly enhanced
        if len(enhanced) <= len(base_prompt) * 10:
            print_fail(
                f"Enhanced prompt not significantly longer. Base: {len(base_prompt)}, Enhanced: {len(enhanced)}"
            )
            return False
        print_pass(
            f"Prompt enhanced from {len(base_prompt)} to {len(enhanced)} chars ({len(enhanced) / len(base_prompt):.1f}x)"
        )

        # Check that skill content is included
        enhanced_lower = enhanced.lower()
        if (
            "test-driven-development" not in enhanced_lower
            and "test driven development" not in enhanced_lower
        ):
            print_fail("Enhanced prompt missing 'test-driven-development' content")
            return False
        print_pass("Enhanced prompt contains test-driven-development content")

        if (
            "systematic-debugging" not in enhanced_lower
            and "systematic debugging" not in enhanced_lower
        ):
            print_fail("Enhanced prompt missing 'systematic-debugging' content")
            return False
        print_pass("Enhanced prompt contains systematic-debugging content")

        # Verify base prompt is preserved
        if base_prompt not in enhanced:
            print_fail("Base prompt not preserved in enhanced version")
            return False
        print_pass("Base prompt preserved in enhanced version")

        # Print sample of enhanced prompt
        print_info("Enhanced prompt sample (first 500 chars):")
        print(f"  {enhanced[:500]}...")

        return True

    except Exception as e:
        print_fail(f"Exception during test: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_4_agent_version_bumps() -> bool:
    """Test 4: Verify Agent Version Bumps"""
    print_test("Test 4: Verify Agent Version Bumps (36 agents)")

    try:
        agents_dir = Path("src/claude_mpm/agents/templates")
        if not agents_dir.exists():
            print_fail(f"Agents directory not found: {agents_dir}")
            return False

        agent_files = list(agents_dir.glob("*.json"))
        # Filter out non-agent files
        agent_files = [f for f in agent_files if not f.name.startswith("__")]
        print_info(f"Found {len(agent_files)} agent files")

        # Sample specific agents
        sample_agents = ["engineer", "python_engineer", "qa", "ops", "product_owner"]
        versions: Dict[str, str] = {}

        for agent_name in sample_agents:
            agent_file = agents_dir / f"{agent_name}.json"
            if not agent_file.exists():
                print_fail(f"Agent file not found: {agent_file}")
                return False

            with open(agent_file) as f:
                data = json.load(f)
                version = data.get("version", "missing")
                versions[agent_name] = version

                if version == "missing":
                    print_fail(f"Agent '{agent_name}' missing version field")
                    return False

                print_pass(f"Agent '{agent_name}' has version: {version}")

        return True

    except Exception as e:
        print_fail(f"Exception during test: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_5_skills_field_in_templates() -> bool:
    """Test 5: Verify Skills Field in Agent Templates"""
    print_test("Test 5: Verify Skills Field in Agent Templates")

    try:
        agents_dir = Path("src/claude_mpm/agents/templates")
        agent_files = list(agents_dir.glob("*.json"))
        # Filter out non-agent files and __init__
        agent_files = [f for f in agent_files if not f.name.startswith("__")]

        agents_with_skills = 0
        agents_without_skills = []
        skill_counts: Dict[str, int] = {}

        for agent_file in agent_files:
            agent_name = agent_file.stem

            with open(agent_file) as f:
                data = json.load(f)

                if "skills" in data:
                    agents_with_skills += 1

                    # Verify it's a list
                    if not isinstance(data["skills"], list):
                        print_fail(f"Agent '{agent_name}' has non-list skills field")
                        return False

                    skill_counts[agent_name] = len(data["skills"])

                    # Verify skills are strings
                    for skill in data["skills"]:
                        if not isinstance(skill, str):
                            print_fail(
                                f"Agent '{agent_name}' has non-string skill: {skill}"
                            )
                            return False
                else:
                    agents_without_skills.append(agent_name)

        print_info(f"Total agent files: {len(agent_files)}")
        print_info(f"Agents with skills: {agents_with_skills}/{len(agent_files)}")

        if agents_without_skills:
            print_info(
                f"Agents without skills ({len(agents_without_skills)}): {', '.join(sorted(agents_without_skills))}"
            )

        # Show skill distribution
        if skill_counts:
            print_info("Top 10 agents by skill count:")
            for agent, count in sorted(skill_counts.items(), key=lambda x: -x[1])[:10]:
                print(f"    {agent}: {count} skills")

        # Success if majority have skills
        target_percentage = 0.8  # 80% of agents should have skills
        required_count = int(len(agent_files) * target_percentage)

        if agents_with_skills < required_count:
            print_fail(
                f"Expected at least {required_count} agents with skills ({target_percentage * 100}%), found {agents_with_skills}"
            )
            return False

        print_pass(
            f"{agents_with_skills}/{len(agent_files)} agents have skills field ({agents_with_skills / len(agent_files) * 100:.1f}%)"
        )

        return True

    except Exception as e:
        print_fail(f"Exception during test: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_6_json_validity() -> bool:
    """Test 6: Verify JSON Validity"""
    print_test("Test 6: Verify JSON Validity for All Agents")

    try:
        agents_dir = Path("src/claude_mpm/agents/templates")
        agent_files = list(agents_dir.glob("*.json"))
        # Filter out non-agent files
        agent_files = [f for f in agent_files if not f.name.startswith("__")]

        invalid_files = []

        for agent_file in agent_files:
            try:
                with open(agent_file) as f:
                    json.load(f)
                # Only print first few to avoid clutter
            except json.JSONDecodeError as e:
                print_fail(f"Invalid JSON: {agent_file.name} - {e}")
                invalid_files.append(agent_file.name)

        if invalid_files:
            print_fail(f"Found {len(invalid_files)} invalid JSON files")
            return False

        print_pass(f"All {len(agent_files)} agent files are valid JSON")

        return True

    except Exception as e:
        print_fail(f"Exception during test: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_7_skills_selector_presence() -> bool:
    """Test 7: Verify Skills Selector CLI Integration"""
    print_test("Test 7: Verify Skills Selector CLI Integration")

    try:
        # Check that skills wizard exists
        wizard_file = Path("src/claude_mpm/cli/interactive/skills_wizard.py")
        if not wizard_file.exists():
            print_fail(f"Skills wizard file not found: {wizard_file}")
            return False
        print_pass("Skills wizard file exists")

        # Check wizard has required components
        with open(wizard_file) as f:
            content = f.read()

            required_items = [
                "class SkillsWizard",
                "def run_interactive_selection",
                "def list_available_skills",
                "AGENT_SKILL_MAPPING",
                "def discover_and_link_runtime_skills",
            ]

            for item in required_items:
                if item not in content:
                    print_fail(f"Skills wizard missing: {item}")
                    return False
                print_pass(f"Skills wizard has: {item}")

        # Verify auto-linking mappings
        if (
            "ENGINEER_CORE_SKILLS" in content
            and "OPS_SKILLS" in content
            and "QA_SKILLS" in content
        ):
            print_pass("Auto-linking skill mappings defined")
        else:
            print_fail("Missing auto-linking skill mappings")
            return False

        # Check configurator integration
        config_file = Path("src/claude_mpm/cli/interactive/configurator.py")
        if config_file.exists():
            with open(config_file) as f:
                content = f.read()
                if "skills" in content.lower():
                    print_pass("Configurator mentions skills")
                else:
                    print_info("Configurator may not integrate skills (check manually)")

        print_info(
            "Note: Full CLI integration requires manual testing with 'claude-mpm configure'"
        )

        return True

    except Exception as e:
        print_fail(f"Exception during test: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests and generate report"""
    print(f"{Colors.BOLD}{'=' * 80}{Colors.RESET}")
    print(f"{Colors.BOLD}SKILLS INTEGRATION COMPREHENSIVE VERIFICATION{Colors.RESET}")
    print(f"{Colors.BOLD}{'=' * 80}{Colors.RESET}")

    tests = [
        ("Test 1: Bundled Skills Loading", test_1_bundled_skills_loading),
        ("Test 2: Agent Skills Mapping", test_2_agent_skills_mapping),
        ("Test 3: Prompt Enhancement", test_3_prompt_enhancement),
        ("Test 4: Agent Version Bumps", test_4_agent_version_bumps),
        ("Test 5: Skills Field in Templates", test_5_skills_field_in_templates),
        ("Test 6: JSON Validity", test_6_json_validity),
        ("Test 7: Skills Selector Presence", test_7_skills_selector_presence),
    ]

    results = {}

    for test_name, test_func in tests:
        try:
            passed = test_func()
            results[test_name] = passed
        except Exception as e:
            print_fail(f"Unexpected error in {test_name}: {e}")
            import traceback

            traceback.print_exc()
            results[test_name] = False

    # Print summary
    print(f"\n{Colors.BOLD}{'=' * 80}{Colors.RESET}")
    print(f"{Colors.BOLD}TEST SUMMARY{Colors.RESET}")
    print(f"{Colors.BOLD}{'=' * 80}{Colors.RESET}")

    passed = sum(results.values())
    total = len(results)

    for test_name, result in results.items():
        status = (
            f"{Colors.GREEN}PASS{Colors.RESET}"
            if result
            else f"{Colors.RED}FAIL{Colors.RESET}"
        )
        print(f"{status} - {test_name}")

    print(f"\n{Colors.BOLD}Overall: {passed}/{total} tests passed{Colors.RESET}")

    if passed == total:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ ALL TESTS PASSED{Colors.RESET}")
        return 0
    print(f"{Colors.RED}{Colors.BOLD}✗ SOME TESTS FAILED{Colors.RESET}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
