#!/usr/bin/env python3
"""Test script for skills integration."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from claude_mpm.skills import SkillManager, get_registry


def test_skills_registry():
    """Test that skills are loaded correctly."""
    print("\n=== Testing Skills Registry ===\n")

    registry = get_registry()

    # List all skills
    bundled_skills = registry.list_skills(source="bundled")
    print(f"✓ Loaded {len(bundled_skills)} bundled skills:")
    for skill in bundled_skills:
        print(f"  - {skill.name}: {skill.description[:60]}...")

    # Test getting specific skill
    tdd_skill = registry.get_skill("test-driven-development")
    if tdd_skill:
        print(f"\n✓ Retrieved TDD skill: {len(tdd_skill.content)} characters")
    else:
        print("\n✗ Failed to retrieve TDD skill")
        return False

    return True


def test_skill_manager():
    """Test that skill manager integrates with agents."""
    print("\n=== Testing Skill Manager ===\n")

    manager = SkillManager()

    # Test getting agent skills
    engineer_skills = manager.get_agent_skills("engineer")
    print(f"✓ Engineer agent has {len(engineer_skills)} skills:")
    for skill in engineer_skills:
        print(f"  - {skill.name}")

    # Test enhancing agent prompt
    base_prompt = "This is a test agent prompt."
    enhanced_prompt = manager.enhance_agent_prompt("engineer", base_prompt)

    if "Available Skills" in enhanced_prompt:
        print("\n✓ Agent prompt enhanced successfully")
        print(f"  Original length: {len(base_prompt)} chars")
        print(f"  Enhanced length: {len(enhanced_prompt)} chars")
        print(f"  Skills added: {enhanced_prompt.count('###')} sections")
    else:
        print("\n✗ Failed to enhance agent prompt")
        return False

    # Test listing agent skill mappings
    mappings = manager.list_agent_skill_mappings()
    if "engineer" in mappings:
        print("\n✓ Agent skill mappings loaded:")
        for agent_id, skills in mappings.items():
            print(f"  - {agent_id}: {len(skills)} skills")
    else:
        print("\n✗ No agent skill mappings found")
        return False

    return True


def test_skill_content():
    """Test that skill content is properly formatted."""
    print("\n=== Testing Skill Content ===\n")

    registry = get_registry()

    # Test a few key skills
    test_skills = [
        "test-driven-development",
        "systematic-debugging",
        "async-testing",
        "performance-profiling",
    ]

    for skill_name in test_skills:
        skill = registry.get_skill(skill_name)
        if skill:
            # Check that content has meaningful structure
            has_title = skill.content.startswith("#")
            has_content = len(skill.content) > 100
            has_examples = "```" in skill.content or "Example" in skill.content

            status = "✓" if (has_title and has_content and has_examples) else "✗"
            print(
                f"{status} {skill_name}: "
                f"{len(skill.content)} chars, "
                f"{'title' if has_title else 'no title'}, "
                f"{'examples' if has_examples else 'no examples'}"
            )
        else:
            print(f"✗ {skill_name}: Not found")
            return False

    return True


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("Skills Integration Test Suite")
    print("=" * 70)

    tests = [
        ("Skills Registry", test_skills_registry),
        ("Skill Manager", test_skill_manager),
        ("Skill Content", test_skill_content),
    ]

    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ {test_name} failed with error: {e}")
            import traceback

            traceback.print_exc()
            results.append((test_name, False))

    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    print(f"\n❌ {total - passed} test(s) failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
