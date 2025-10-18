#!/usr/bin/env python3
"""
Select Lightweight Test Suite
Intelligently selects 12 tests from each agent's 25-test expanded suite.

Selection Strategy:
- 4 Easy tests (highest quality/variety)
- 5 Medium tests (best category coverage)
- 3 Hard tests (most challenging)

Selection Criteria:
- Category diversity (avoid duplicates)
- Comprehensive skill coverage
- Representative difficulty progression
"""

import json
from pathlib import Path
from typing import Dict, List
from collections import defaultdict


class TestSelector:
    """Selects optimal test subset for lightweight benchmark"""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.expanded_dir = base_path / "benchmarks" / "expanded"
        self.lightweight_dir = base_path / "benchmarks" / "lightweight"

        # Target distribution
        self.target_counts = {
            "easy": 4,
            "medium": 5,
            "hard": 3
        }

    def load_expanded_suite(self, language: str) -> List[Dict]:
        """Load expanded test suite for language"""
        test_file = self.expanded_dir / f"{language}_tests.json"
        with open(test_file) as f:
            return json.load(f)

    def calculate_test_score(self, test: Dict, category_counts: Dict[str, int]) -> float:
        """
        Calculate selection priority score for test.

        Factors:
        - Category uniqueness (prefer diverse categories)
        - Test complexity (prefer comprehensive tests)
        - Educational value (prefer clear learning objectives)
        """
        score = 0.0

        # Category diversity bonus (lower count = higher bonus)
        category = test.get("category", "general")
        category_bonus = 1.0 / (category_counts.get(category, 0) + 1)
        score += category_bonus * 10

        # Test case count (more comprehensive)
        test_case_count = len(test.get("test_cases", []))
        score += min(test_case_count, 5) * 2

        # Has constraints and hints (educational value)
        if test.get("constraints"):
            score += 3
        if test.get("hints"):
            score += 3

        # Has solution approach (learning value)
        if test.get("solution_approach"):
            score += 5

        # Complexity indicators (time/space)
        if test.get("time_complexity"):
            score += 2
        if test.get("space_complexity"):
            score += 2

        return score

    def select_tests_by_difficulty(self, tests: List[Dict], difficulty: str, count: int) -> List[Dict]:
        """Select top N tests for a given difficulty level"""
        # Filter by difficulty
        difficulty_tests = [t for t in tests if t.get("difficulty") == difficulty]

        if len(difficulty_tests) <= count:
            return difficulty_tests

        # Track category usage
        category_counts = defaultdict(int)
        selected = []
        remaining = difficulty_tests.copy()

        # Iteratively select best test based on current category distribution
        for _ in range(count):
            # Score all remaining tests
            scored_tests = []
            for test in remaining:
                score = self.calculate_test_score(test, category_counts)
                scored_tests.append((score, test))

            # Select highest scoring test
            scored_tests.sort(key=lambda x: x[0], reverse=True)
            _, best_test = scored_tests[0]

            # Add to selected and update counts
            selected.append(best_test)
            category = best_test.get("category", "general")
            category_counts[category] += 1
            remaining.remove(best_test)

        return selected

    def create_lightweight_suite(self, language: str, agent_id: str) -> Dict:
        """Create lightweight test suite for agent"""
        # Load full suite
        full_suite = self.load_expanded_suite(language)

        # Select tests by difficulty
        selected_tests = []
        for difficulty, count in self.target_counts.items():
            tests = self.select_tests_by_difficulty(full_suite, difficulty, count)
            selected_tests.extend(tests)

        # Sort by difficulty then category
        difficulty_order = {"easy": 0, "medium": 1, "hard": 2}
        selected_tests.sort(key=lambda t: (
            difficulty_order.get(t.get("difficulty", "medium"), 1),
            t.get("category", "general")
        ))

        # Create suite metadata
        suite = {
            "agent_id": agent_id,
            "language": language,
            "suite_type": "lightweight",
            "total_tests": len(selected_tests),
            "difficulty_distribution": {
                "easy": sum(1 for t in selected_tests if t.get("difficulty") == "easy"),
                "medium": sum(1 for t in selected_tests if t.get("difficulty") == "medium"),
                "hard": sum(1 for t in selected_tests if t.get("difficulty") == "hard")
            },
            "category_coverage": list(set(t.get("category", "general") for t in selected_tests)),
            "source_suite": "expanded_v1",
            "version": "1.0.0",
            "tests": selected_tests
        }

        return suite

    def generate_all_suites(self):
        """Generate lightweight suites for all 7 agents"""
        agents = [
            ("python", "python_engineer"),
            ("typescript", "typescript_engineer"),
            ("nextjs", "nextjs_engineer"),
            ("php", "php_engineer"),
            ("ruby", "ruby_engineer"),
            ("golang", "golang_engineer"),
            ("rust", "rust_engineer")
        ]

        print("🎯 Generating Lightweight Test Suites")
        print("=" * 60)
        print()

        summaries = []

        for language, agent_id in agents:
            print(f"📝 {agent_id}:")
            suite = self.create_lightweight_suite(language, agent_id)

            # Save suite
            output_file = self.lightweight_dir / f"{language}_mini.json"
            with open(output_file, 'w') as f:
                json.dump(suite, f, indent=2)

            # Print summary
            dist = suite["difficulty_distribution"]
            print(f"   ✓ Selected {suite['total_tests']} tests: "
                  f"{dist['easy']} easy, {dist['medium']} medium, {dist['hard']} hard")
            print(f"   ✓ Categories: {', '.join(suite['category_coverage'])}")
            print(f"   ✓ Saved to: {output_file.name}")
            print()

            summaries.append({
                "agent_id": agent_id,
                "language": language,
                "total_tests": suite["total_tests"],
                "distribution": dist,
                "categories": suite["category_coverage"]
            })

        # Generate summary report
        self._generate_summary_report(summaries)

        print("✅ Lightweight test suites generated successfully!")
        print(f"📊 Total tests: {sum(s['total_tests'] for s in summaries)}")
        print(f"📂 Location: {self.lightweight_dir}")

    def _generate_summary_report(self, summaries: List[Dict]):
        """Generate summary report of selection"""
        report = {
            "generation_date": "2025-10-18",
            "suite_type": "lightweight",
            "total_agents": len(summaries),
            "total_tests": sum(s["total_tests"] for s in summaries),
            "selection_strategy": {
                "easy_tests_per_agent": self.target_counts["easy"],
                "medium_tests_per_agent": self.target_counts["medium"],
                "hard_tests_per_agent": self.target_counts["hard"],
                "total_per_agent": sum(self.target_counts.values())
            },
            "agents": summaries
        }

        output_file = self.lightweight_dir / "suite_manifest.json"
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        print(f"📋 Manifest saved to: {output_file.name}")
        print()


if __name__ == "__main__":
    # Use path relative to script location
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent  # docs/benchmarks

    selector = TestSelector(base_dir)
    selector.generate_all_suites()
