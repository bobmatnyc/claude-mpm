"""Test script for skills optimize command."""

from pathlib import Path

from src.claude_mpm.services.skills.project_inspector import ProjectInspector
from src.claude_mpm.services.skills.skill_recommendation_engine import (
    SkillRecommendationEngine,
)


def test_project_inspection():
    """Test project inspection on claude-mpm itself."""
    print("=" * 80)
    print("Testing Project Inspection")
    print("=" * 80)

    inspector = ProjectInspector(Path.cwd())
    stack = inspector.inspect()

    print("\n📊 Detected Technology Stack:\n")

    if stack.languages:
        print("Languages:")
        for lang, conf in sorted(
            stack.languages.items(), key=lambda x: x[1], reverse=True
        ):
            print(f"  - {lang}: {conf:.2f} ({int(conf * 100)}% confidence)")

    if stack.frameworks:
        print("\nFrameworks:")
        for fw, conf in sorted(
            stack.frameworks.items(), key=lambda x: x[1], reverse=True
        ):
            print(f"  - {fw}: {conf:.2f} ({int(conf * 100)}% confidence)")

    if stack.tools:
        print("\nTools:")
        for tool, conf in sorted(stack.tools.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {tool}: {conf:.2f} ({int(conf * 100)}% confidence)")

    if stack.databases:
        print("\nDatabases:")
        for db, conf in sorted(
            stack.databases.items(), key=lambda x: x[1], reverse=True
        ):
            print(f"  - {db}: {conf:.2f} ({int(conf * 100)}% confidence)")

    return stack


def test_skill_recommendations(tech_stack):
    """Test skill recommendations."""
    print("\n" + "=" * 80)
    print("Testing Skill Recommendations")
    print("=" * 80)

    engine = SkillRecommendationEngine()
    already_deployed = engine.get_deployed_skills(Path.cwd())

    print(f"\n📦 Already deployed skills: {len(already_deployed)}")
    if already_deployed:
        for skill in sorted(already_deployed):
            print(f"  - {skill}")

    print("\n🎯 Generating recommendations...\n")

    recommendations = engine.recommend_skills(
        tech_stack, already_deployed, max_recommendations=15
    )

    if not recommendations:
        print("❌ No recommendations found")
        return

    print(f"✅ Found {len(recommendations)} recommendations:\n")

    # Group by priority
    from collections import defaultdict

    by_priority = defaultdict(list)

    for rec in recommendations:
        by_priority[rec.priority].append(rec)

    # Display by priority
    priority_order = ["critical", "high", "medium", "low"]
    for priority_name in priority_order:
        skills = [r for r in recommendations if r.priority.value == priority_name]
        if not skills:
            continue

        print(f"\n{priority_name.upper()} Priority ({len(skills)}):")
        for rec in skills:
            print(f"  - {rec.skill_id}")
            print(f"    Score: {rec.relevance_score:.2f}")
            print(f"    Matched: {', '.join(rec.matched_technologies)}")
            print(f"    Reason: {rec.justification}")
            print()


if __name__ == "__main__":
    try:
        # Test inspection
        stack = test_project_inspection()

        # Test recommendations
        test_skill_recommendations(stack)

        print("\n" + "=" * 80)
        print("✅ All tests passed!")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
