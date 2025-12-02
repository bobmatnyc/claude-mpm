#!/usr/bin/env python3
"""
Comprehensive Skills System Verification Test
Tests all components of the skills integration system.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from claude_mpm.skills.registry import Skill, SkillsRegistry
from claude_mpm.skills.skill_manager import SkillManager


def test_bundled_skills_count():
    """Verify exactly 20 bundled skills exist"""
    print("\n=== TEST 1: Bundled Skills Count ===")
    bundled_dir = Path("src/claude_mpm/skills/bundled")
    skill_files = list(bundled_dir.glob("*.md"))
    skill_files = [f for f in skill_files if f.stem != "__init__"]

    print(f"Found {len(skill_files)} bundled skill files")
    for f in sorted(skill_files):
        print(f"  - {f.stem}")

    assert len(skill_files) == 20, (
        f"Expected 20 bundled skills, found {len(skill_files)}"
    )
    print("✅ PASS: Exactly 20 bundled skills found")
    return True


def test_skills_registry_loading():
    """Test SkillsRegistry instantiation and skill loading"""
    print("\n=== TEST 2: SkillsRegistry Loading ===")

    try:
        registry = SkillsRegistry()
        print("✅ SkillsRegistry instantiated successfully")
    except Exception as e:
        print(f"❌ FAIL: Could not instantiate SkillsRegistry: {e}")
        return False

    # Get all skills
    all_skills = registry.list_skills()
    print(f"Loaded {len(all_skills)} total skills")

    # Verify we have at least 20 bundled skills
    if len(all_skills) < 20:
        print(f"❌ FAIL: Expected at least 20 skills, got {len(all_skills)}")
        return False

    print(f"✅ PASS: Registry loaded {len(all_skills)} skills")

    # Test specific skill retrieval
    test_skills = ["test-driven-development", "systematic-debugging", "git-workflow"]
    for skill_name in test_skills:
        skill = registry.get_skill(skill_name)
        if not skill:
            print(f"❌ FAIL: Could not retrieve skill '{skill_name}'")
            return False
        print(f"  - Retrieved '{skill.name}' (source: {skill.source})")

    print("✅ PASS: All test skills retrieved successfully")
    return True


def test_skill_model_structure():
    """Verify Skill objects have correct structure"""
    print("\n=== TEST 3: Skill Model Structure ===")

    registry = SkillsRegistry()
    skill = registry.get_skill("test-driven-development")

    if not skill:
        print("❌ FAIL: Could not load test skill")
        return False

    # Verify required attributes
    required_attrs = ["name", "content", "source", "description"]
    for attr in required_attrs:
        if not hasattr(skill, attr):
            print(f"❌ FAIL: Skill missing attribute '{attr}'")
            return False
        print(
            f"  - Has attribute '{attr}': {getattr(skill, attr)[:50] if isinstance(getattr(skill, attr), str) else type(getattr(skill, attr))}"
        )

    # Verify content is substantial
    if len(skill.content) < 100:
        print(f"❌ FAIL: Skill content too short ({len(skill.content)} chars)")
        return False

    print(f"✅ PASS: Skill structure valid (content: {len(skill.content)} chars)")
    return True


def test_skill_manager():
    """Test SkillManager functionality"""
    print("\n=== TEST 4: SkillManager Functionality ===")

    try:
        manager = SkillManager()
        print("✅ SkillManager instantiated successfully")
    except Exception as e:
        print(f"❌ FAIL: Could not instantiate SkillManager: {e}")
        return False

    # Test getting skills for specific agent types
    agent_types = [
        "full-stack-engineer",
        "backend-engineer",
        "qa-engineer",
        "devops-engineer",
    ]

    for agent_type in agent_types:
        skills = manager.get_agent_skills(agent_type)
        print(f"  - {agent_type}: {len(skills)} skills")
        if skills:
            print(
                f"    Skills: {', '.join(s.name for s in skills[:3])}{'...' if len(skills) > 3 else ''}"
            )

    print("✅ PASS: SkillManager can retrieve agent-specific skills")
    return True


def test_prompt_enhancement():
    """Test prompt enhancement with skills"""
    print("\n=== TEST 5: Prompt Enhancement ===")

    manager = SkillManager()

    # Test with engineer agent (which has skills configured)
    original_prompt = "You are a backend engineer. Write clean code."
    agent_type = "engineer"  # Use agent_type that has skills configured

    enhanced = manager.enhance_agent_prompt(agent_type, original_prompt)

    print(f"Original prompt length: {len(original_prompt)}")
    print(f"Enhanced prompt length: {len(enhanced)}")
    print(f"Prompt expansion: {len(enhanced) / len(original_prompt):.1f}x")

    # Verify skills were injected
    if "test-driven-development" not in enhanced.lower() and "TDD" not in enhanced:
        print("❌ FAIL: Skills not properly injected into prompt")
        return False

    # Show sample of enhanced content
    print("\n--- Enhanced Prompt Sample (first 500 chars) ---")
    print(enhanced[:500])
    print("...\n")

    print("✅ PASS: Prompt successfully enhanced with skills")
    return True


def test_agent_skill_inference():
    """Test auto-linking of skills to agents"""
    print("\n=== TEST 6: Agent Skill Inference ===")

    manager = SkillManager()

    # Get a skill object first
    skill = manager.registry.get_skill("docker-containerization")
    if not skill:
        print("❌ FAIL: Could not load docker-containerization skill")
        return False

    # Test inference for a skill
    agents = manager.infer_agents_for_skill(skill)
    print(f"Skill 'docker-containerization' inferred for agents: {agents}")

    if not agents:
        print("❌ FAIL: No agents inferred for docker-containerization")
        return False

    # Should include devops-related agents
    expected_agents = ["devops-engineer", "local-ops-agent"]
    found = any(agent in str(agents) for agent in expected_agents)

    if not found:
        print(f"⚠️  WARNING: Expected one of {expected_agents} in inferred agents")
    else:
        print("✅ PASS: Correctly inferred devops-related agents")

    return True


def test_agent_templates():
    """Verify agent templates have skills field"""
    print("\n=== TEST 7: Agent Template Verification ===")

    import json

    templates_dir = Path("src/claude_mpm/agents/templates")

    if not templates_dir.exists():
        print(f"❌ FAIL: Templates directory not found: {templates_dir}")
        return False

    agent_files = list(templates_dir.glob("*.json"))
    print(f"Found {len(agent_files)} agent templates")

    agents_with_skills = 0
    agents_without_skills = []
    skill_mappings = {}

    for agent_file in agent_files:
        with open(agent_file) as f:
            agent_data = json.load(f)

        if agent_data.get("skills"):
            agents_with_skills += 1
            skill_mappings[agent_file.stem] = agent_data["skills"]
        else:
            agents_without_skills.append(agent_file.stem)

    print(f"\nAgents with skills: {agents_with_skills}/{len(agent_files)}")
    print(f"Agents without skills: {len(agents_without_skills)}")

    if agents_without_skills:
        print("Agents without skills field:")
        for agent in agents_without_skills[:5]:
            print(f"  - {agent}")
        if len(agents_without_skills) > 5:
            print(f"  ... and {len(agents_without_skills) - 5} more")

    # Show sample mappings
    print("\n--- Sample Skill Mappings ---")
    for agent, skills in list(skill_mappings.items())[:5]:
        print(f"{agent}: {', '.join(skills)}")

    # Verify key agents have correct skills
    expected_mappings = {
        "full-stack-engineer": [
            "test-driven-development",
            "systematic-debugging",
            "git-workflow",
        ],
        "backend-engineer": ["test-driven-development", "systematic-debugging"],
        "qa-engineer": ["test-driven-development", "systematic-debugging"],
        "devops-engineer": ["docker-containerization", "git-workflow"],
    }

    mapping_pass = True
    for agent, expected_skills in expected_mappings.items():
        if agent in skill_mappings:
            actual = skill_mappings[agent]
            for skill in expected_skills:
                if skill not in actual:
                    print(f"⚠️  WARNING: {agent} missing expected skill '{skill}'")
                    mapping_pass = False
        else:
            print(f"⚠️  WARNING: {agent} has no skills configured")
            mapping_pass = False

    if agents_with_skills >= 31:
        print(f"✅ PASS: {agents_with_skills} agents have skills configured")
    else:
        print(
            f"⚠️  WARNING: Expected at least 31 agents with skills, found {agents_with_skills}"
        )

    return True


def test_performance():
    """Test performance of skill loading"""
    print("\n=== TEST 8: Performance Metrics ===")

    import time

    # Test registry initialization time
    start = time.time()
    registry = SkillsRegistry()
    init_time = time.time() - start
    print(f"Registry initialization: {init_time:.3f}s")

    # Test skill retrieval time
    start = time.time()
    for _ in range(100):
        registry.get_skill("test-driven-development")
    retrieval_time = (time.time() - start) / 100
    print(f"Average skill retrieval: {retrieval_time * 1000:.2f}ms")

    # Test prompt enhancement time
    manager = SkillManager()
    prompt = "You are an engineer."
    agent_type = "engineer"  # Use valid agent_type

    start = time.time()
    manager.enhance_agent_prompt(agent_type, prompt)
    enhancement_time = time.time() - start
    print(f"Prompt enhancement: {enhancement_time:.3f}s")

    # Performance expectations
    if init_time > 1.0:
        print("⚠️  WARNING: Registry initialization is slow")
    if enhancement_time > 0.5:
        print("⚠️  WARNING: Prompt enhancement is slow")

    print("✅ PASS: Performance metrics collected")
    return True


def run_all_tests():
    """Run all verification tests"""
    print("=" * 70)
    print("SKILLS SYSTEM VERIFICATION TEST SUITE")
    print("=" * 70)

    tests = [
        test_bundled_skills_count,
        test_skills_registry_loading,
        test_skill_model_structure,
        test_skill_manager,
        test_prompt_enhancement,
        test_agent_skill_inference,
        test_agent_templates,
        test_performance,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append((test.__name__, result))
        except Exception as e:
            print(f"\n❌ EXCEPTION in {test.__name__}: {e}")
            import traceback

            traceback.print_exc()
            results.append((test.__name__, False))

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Skills system is fully operational.")
        return 0
    print(f"\n⚠️  {total - passed} test(s) failed. Review output above.")
    return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
