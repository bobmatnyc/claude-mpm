#!/usr/bin/env python3
"""
Lightweight SWE Benchmark Runner for Claude MPM Agents
Executes 12 tests per agent (84 total) with multi-dimensional scoring

This runner simulates agent execution and evaluates solutions across:
- Correctness (0-10): Solution works and passes tests
- Idiomaticity (0-10): Language-specific patterns and conventions
- Performance (0-10): Efficiency and optimization
- Best Practices (0-10): Code quality, maintainability, security
"""

import json
import time
import random
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime


class LightweightBenchmarkRunner:
    """Runs lightweight 12-test benchmark on coding agents"""

    # Dimension weights for final score
    DIMENSION_WEIGHTS = {
        "correctness": 0.40,
        "idiomaticity": 0.25,
        "performance": 0.20,
        "best_practices": 0.15
    }

    def __init__(self, base_path: Path, mock_mode: bool = True):
        self.base_path = base_path
        self.lightweight_dir = base_path / "benchmarks" / "lightweight"
        self.results_dir = base_path / "results" / "lightweight"
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.mock_mode = mock_mode

    def load_agent_tests(self, language: str) -> Dict:
        """Load 12 selected tests for agent"""
        test_file = self.lightweight_dir / f"{language}_mini.json"
        with open(test_file) as f:
            return json.load(f)

    def _mock_agent_execution(self, test: Dict, agent_id: str) -> Tuple[bool, str, float]:
        """
        Mock agent execution for testing.

        In production, this would invoke the actual Claude MPM agent
        with the test and evaluate the response.

        Returns: (passed, solution, execution_time)
        """
        # Simulate realistic execution time
        difficulty_times = {
            "easy": (0.5, 2.0),
            "medium": (1.5, 5.0),
            "hard": (3.0, 10.0)
        }
        difficulty = test.get("difficulty", "medium")
        min_time, max_time = difficulty_times[difficulty]
        execution_time = random.uniform(min_time, max_time)

        # Simulate realistic pass rates by difficulty
        pass_rates = {
            "easy": 0.90,
            "medium": 0.75,
            "hard": 0.60
        }
        base_pass_rate = pass_rates[difficulty]

        # Adjust by agent quality (some agents are better)
        agent_quality_modifiers = {
            "python_engineer": 1.0,
            "typescript_engineer": 0.95,
            "nextjs_engineer": 0.92,
            "php_engineer": 0.98,
            "ruby_engineer": 0.94,
            "golang_engineer": 0.90,
            "rust_engineer": 0.88
        }
        quality_mod = agent_quality_modifiers.get(agent_id, 0.85)
        adjusted_pass_rate = min(base_pass_rate * quality_mod, 0.95)

        # Determine if test passed
        passed = random.random() < adjusted_pass_rate

        # Generate mock solution
        solution = f"""
// Mock solution for {test['name']}
// Difficulty: {difficulty}
// Category: {test.get('category', 'general')}

{test.get('signature', 'function solution() {}')}
    // Implementation would go here
    // Status: {'PASSED' if passed else 'FAILED'}
    return result;
}}
""".strip()

        return passed, solution, execution_time

    def _evaluate_dimensions(self, test: Dict, passed: bool, solution: str,
                            execution_time: float, agent_id: str) -> Dict[str, float]:
        """
        Evaluate solution across all dimensions.

        In production, this would use sophisticated analysis:
        - Code parsing for idiomaticity
        - Test execution for correctness
        - Profiling for performance
        - Static analysis for best practices

        For now, uses intelligent mock scoring.
        """
        difficulty = test.get("difficulty", "medium")

        # Correctness: Binary but with partial credit for near-solutions
        if passed:
            correctness = random.uniform(8.5, 10.0)
        else:
            # Sometimes partial solutions get partial credit
            correctness = random.uniform(0.0, 4.0)

        # Idiomaticity: Higher for easier problems, varies by agent
        agent_idiomaticity = {
            "python_engineer": 0.95,
            "typescript_engineer": 0.88,
            "nextjs_engineer": 0.85,
            "php_engineer": 0.92,
            "ruby_engineer": 0.90,
            "golang_engineer": 0.87,
            "rust_engineer": 0.82
        }
        base_idiom = agent_idiomaticity.get(agent_id, 0.80)
        if passed:
            idiomaticity = random.uniform(base_idiom * 7, base_idiom * 10)
        else:
            idiomaticity = random.uniform(3.0, 6.0)

        # Performance: Based on execution time and difficulty expectations
        expected_times = {
            "easy": 1.5,
            "medium": 3.0,
            "hard": 6.0
        }
        expected = expected_times[difficulty]
        if execution_time <= expected * 0.8:
            performance = random.uniform(8.5, 10.0)
        elif execution_time <= expected:
            performance = random.uniform(7.0, 8.5)
        elif execution_time <= expected * 1.5:
            performance = random.uniform(5.0, 7.0)
        else:
            performance = random.uniform(2.0, 5.0)

        # Best Practices: Correlates with idiomaticity for mock
        if passed:
            best_practices = random.uniform(
                idiomaticity * 0.8,
                min(idiomaticity * 1.1, 10.0)
            )
        else:
            best_practices = random.uniform(3.0, 6.0)

        return {
            "correctness": round(correctness, 2),
            "idiomaticity": round(idiomaticity, 2),
            "performance": round(performance, 2),
            "best_practices": round(best_practices, 2)
        }

    def run_single_test(self, agent_id: str, test: Dict) -> Dict:
        """
        Run a single test on agent.

        Returns: {
            "test_id": str,
            "test_name": str,
            "difficulty": str,
            "category": str,
            "passed": bool,
            "dimensions": {
                "correctness": 0-10,
                "idiomaticity": 0-10,
                "performance": 0-10,
                "best_practices": 0-10
            },
            "weighted_score": float,
            "execution_time": float,
            "solution": str
        }
        """
        # Execute test
        if self.mock_mode:
            passed, solution, execution_time = self._mock_agent_execution(test, agent_id)
        else:
            # Production mode: Delegate to production_benchmark_runner
            # This maintains backward compatibility while enabling real execution
            # Import here to avoid circular dependency
            try:
                from production_benchmark_runner import ProductionBenchmarkRunner
                prod_runner = ProductionBenchmarkRunner(self.base_path, mock_mode=False)
                return prod_runner.run_single_test(agent_id, test)
            except ImportError:
                raise NotImplementedError(
                    "Real agent execution requires production_benchmark_runner.py. "
                    "Run in mock mode or implement production runner."
                )

        # Evaluate dimensions
        dimensions = self._evaluate_dimensions(
            test, passed, solution, execution_time, agent_id
        )

        # Calculate weighted score
        weighted_score = sum(
            dimensions[dim] * self.DIMENSION_WEIGHTS[dim]
            for dim in self.DIMENSION_WEIGHTS
        )

        return {
            "test_id": test["id"],
            "test_name": test["name"],
            "difficulty": test.get("difficulty", "medium"),
            "category": test.get("category", "general"),
            "passed": passed,
            "dimensions": dimensions,
            "weighted_score": round(weighted_score, 2),
            "execution_time": round(execution_time, 2),
            "solution_length": len(solution)
        }

    def run_agent_benchmark(self, language: str, agent_id: str) -> Dict:
        """Run all 12 tests for agent"""
        suite = self.load_agent_tests(language)
        results = []

        print(f"\n🎯 Running lightweight benchmark for {agent_id}")
        print(f"   Language: {language}")
        print(f"   Tests: {suite['total_tests']}")
        print()

        start_time = time.time()

        for i, test in enumerate(suite['tests'], 1):
            print(f"   [{i:2d}/12] {test['name']:<40} ({test['difficulty']:<6}) ... ", end="", flush=True)

            result = self.run_single_test(agent_id, test)
            results.append(result)

            # Status indicator
            if result['passed']:
                status = "✅"
            else:
                status = "❌"

            # Dimension summary
            dims = result['dimensions']
            print(f"{status} [{dims['correctness']:.1f} {dims['idiomaticity']:.1f} "
                  f"{dims['performance']:.1f} {dims['best_practices']:.1f}]")

        total_time = time.time() - start_time

        # Calculate summary statistics
        passed_count = sum(1 for r in results if r['passed'])
        total_weighted_score = sum(r['weighted_score'] for r in results)

        # Breakdown by difficulty
        difficulty_stats = {}
        for diff in ['easy', 'medium', 'hard']:
            diff_results = [r for r in results if r['difficulty'] == diff]
            if diff_results:
                difficulty_stats[diff] = {
                    "total": len(diff_results),
                    "passed": sum(1 for r in diff_results if r['passed']),
                    "avg_score": round(sum(r['weighted_score'] for r in diff_results) / len(diff_results), 2)
                }

        print()
        print(f"   ✓ Completed in {total_time:.1f}s")
        print(f"   ✓ Passed: {passed_count}/12 ({passed_count/12*100:.1f}%)")
        print(f"   ✓ Avg Score: {total_weighted_score/12:.2f}/10.0")

        return {
            "agent_id": agent_id,
            "language": language,
            "total_tests": len(results),
            "passed_tests": passed_count,
            "pass_rate": round(passed_count / len(results) * 100, 2),
            "total_weighted_score": round(total_weighted_score, 2),
            "average_score": round(total_weighted_score / len(results), 2),
            "difficulty_breakdown": difficulty_stats,
            "execution_time": round(total_time, 2),
            "results": results,
            "timestamp": datetime.now().isoformat()
        }

    def run_all_agents(self) -> Dict:
        """Run benchmark on all 7 agents"""
        agents = [
            ("python", "python_engineer"),
            ("typescript", "typescript_engineer"),
            ("nextjs", "nextjs_engineer"),
            ("php", "php_engineer"),
            ("ruby", "ruby_engineer"),
            ("golang", "golang_engineer"),
            ("rust", "rust_engineer")
        ]

        print("=" * 80)
        print("🚀 LIGHTWEIGHT SWE BENCHMARK - CLAUDE MPM AGENTS")
        print("=" * 80)
        print(f"Suite: Lightweight (12 tests per agent)")
        print(f"Total tests: 84 (7 agents × 12 tests)")
        print(f"Execution mode: {'Mock' if self.mock_mode else 'Production'}")
        print()

        all_results = {}
        overall_start = time.time()

        for language, agent_id in agents:
            all_results[agent_id] = self.run_agent_benchmark(language, agent_id)

        overall_time = time.time() - overall_start

        # Calculate aggregate statistics
        total_tests = sum(r['total_tests'] for r in all_results.values())
        total_passed = sum(r['passed_tests'] for r in all_results.values())
        overall_pass_rate = round(total_passed / total_tests * 100, 2)

        print()
        print("=" * 80)
        print("📊 BENCHMARK SUMMARY")
        print("=" * 80)
        print(f"Total agents: {len(agents)}")
        print(f"Total tests: {total_tests}")
        print(f"Tests passed: {total_passed}/{total_tests} ({overall_pass_rate}%)")
        print(f"Total time: {overall_time:.1f}s ({overall_time/60:.1f} minutes)")
        print(f"Avg time per agent: {overall_time/len(agents):.1f}s")
        print()

        return {
            "benchmark_type": "lightweight",
            "version": "1.0.0",
            "execution_mode": "mock" if self.mock_mode else "production",
            "total_agents": len(agents),
            "total_tests": total_tests,
            "total_passed": total_passed,
            "overall_pass_rate": overall_pass_rate,
            "execution_time": round(overall_time, 2),
            "timestamp": datetime.now().isoformat(),
            "results": all_results
        }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Run lightweight SWE benchmark on Claude MPM agents"
    )
    parser.add_argument(
        "--agent",
        help="Run specific agent only (e.g., python_engineer)"
    )
    parser.add_argument(
        "--production",
        action="store_true",
        help="Run in production mode (requires real agents)"
    )
    args = parser.parse_args()

    # Use path relative to script location
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent  # docs/benchmarks

    runner = LightweightBenchmarkRunner(
        base_dir,
        mock_mode=not args.production
    )

    if args.agent:
        # Run single agent
        # Map agent ID to language
        agent_to_lang = {
            "python_engineer": "python",
            "typescript_engineer": "typescript",
            "nextjs_engineer": "nextjs",
            "php_engineer": "php",
            "ruby_engineer": "ruby",
            "golang_engineer": "golang",
            "rust_engineer": "rust"
        }
        language = agent_to_lang.get(args.agent)
        if not language:
            print(f"❌ Unknown agent: {args.agent}")
            exit(1)

        result = runner.run_agent_benchmark(language, args.agent)

        # Save result
        output_file = runner.results_dir / f"{args.agent}_benchmark.json"
        with open(output_file, 'w') as f:
            json.dump({
                "benchmark_type": "lightweight",
                "version": "1.0.0",
                "results": {args.agent: result}
            }, f, indent=2)

        print(f"\n✅ Results saved to {output_file}")
    else:
        # Run all agents
        results = runner.run_all_agents()

        # Save results
        output_file = runner.results_dir / "benchmark_results.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"✅ Complete results saved to {output_file}")
