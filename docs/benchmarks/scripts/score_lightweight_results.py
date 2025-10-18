#!/usr/bin/env python3
"""
Scoring Engine for Lightweight SWE Benchmark
Calculates multi-dimensional scores with difficulty weighting

Scoring System:
- 4 Dimensions: Correctness (40%), Idiomaticity (25%), Performance (20%), Best Practices (15%)
- Difficulty Multipliers: Easy (1.0x), Medium (1.2x), Hard (1.5x)
- Grade Scale: A+ (95%+), A (90-94%), B+ (80-89%), B (75-79%), C+ (70-74%), C (65-69%), D (60-64%), F (<60%)
"""

import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime


class LightweightScorer:
    """Calculates scores for lightweight benchmark results"""

    # Dimension weights (must sum to 1.0)
    DIMENSION_WEIGHTS = {
        "correctness": 0.40,
        "idiomaticity": 0.25,
        "performance": 0.20,
        "best_practices": 0.15
    }

    # Difficulty multipliers
    DIFFICULTY_MULTIPLIERS = {
        "easy": 1.0,
        "medium": 1.2,
        "hard": 1.5
    }

    # Grade thresholds (score percentage -> grade)
    GRADE_THRESHOLDS = [
        (95, "A+", "Exceptional"),
        (90, "A", "Excellent"),
        (85, "A-", "Very Good"),
        (80, "B+", "Good"),
        (75, "B", "Above Average"),
        (70, "B-", "Satisfactory"),
        (65, "C+", "Fair"),
        (60, "C", "Adequate"),
        (55, "C-", "Below Average"),
        (50, "D+", "Poor"),
        (45, "D", "Very Poor"),
        (0, "F", "Failing")
    ]

    def __init__(self, results_dir: Path):
        self.results_dir = results_dir

    def calculate_test_score(self, test_result: Dict) -> Dict:
        """
        Calculate weighted score for single test.

        Returns:
            {
                "test_id": str,
                "difficulty": str,
                "base_score": float (0-10),
                "difficulty_multiplier": float,
                "weighted_score": float,
                "max_possible": float,
                "dimension_breakdown": dict
            }
        """
        difficulty = test_result.get('difficulty', 'medium')
        multiplier = self.DIFFICULTY_MULTIPLIERS[difficulty]
        dimensions = test_result.get('dimensions', {})

        # Calculate dimension contributions
        dimension_breakdown = {}
        base_score = 0.0

        for dim, weight in self.DIMENSION_WEIGHTS.items():
            dim_value = dimensions.get(dim, 0.0)
            weighted_value = dim_value * weight
            dimension_breakdown[dim] = {
                "raw_score": dim_value,
                "weight": weight,
                "weighted_score": round(weighted_value, 3)
            }
            base_score += weighted_value

        # Apply difficulty multiplier
        final_score = base_score * multiplier
        max_possible = 10.0 * multiplier

        return {
            "test_id": test_result['test_id'],
            "test_name": test_result.get('test_name', ''),
            "difficulty": difficulty,
            "passed": test_result.get('passed', False),
            "base_score": round(base_score, 2),
            "difficulty_multiplier": multiplier,
            "weighted_score": round(final_score, 2),
            "max_possible": max_possible,
            "percentage": round((final_score / max_possible * 100) if max_possible > 0 else 0, 2),
            "dimension_breakdown": dimension_breakdown
        }

    def calculate_agent_score(self, agent_results: Dict) -> Dict:
        """Calculate overall score for agent"""
        test_results = agent_results.get('results', [])

        if not test_results:
            return self._empty_score(agent_results.get('agent_id', 'unknown'))

        # Score each test
        test_scores = []
        total_points = 0.0
        max_points = 0.0

        # Dimension aggregates
        dimension_totals = {dim: 0.0 for dim in self.DIMENSION_WEIGHTS}
        dimension_max = {dim: 0.0 for dim in self.DIMENSION_WEIGHTS}

        # Difficulty breakdown
        difficulty_breakdown = {
            "easy": {"total": 0, "passed": 0, "points": 0.0, "max_points": 0.0},
            "medium": {"total": 0, "passed": 0, "points": 0.0, "max_points": 0.0},
            "hard": {"total": 0, "passed": 0, "points": 0.0, "max_points": 0.0}
        }

        # Category breakdown
        category_scores = {}

        for result in test_results:
            test_score = self.calculate_test_score(result)
            test_scores.append(test_score)

            # Accumulate totals
            total_points += test_score['weighted_score']
            max_points += test_score['max_possible']

            # Dimension aggregation
            for dim, breakdown in test_score['dimension_breakdown'].items():
                dimension_totals[dim] += breakdown['weighted_score']
                dimension_max[dim] += breakdown['raw_score'] * breakdown['weight']

            # Difficulty tracking
            difficulty = test_score['difficulty']
            difficulty_breakdown[difficulty]['total'] += 1
            difficulty_breakdown[difficulty]['points'] += test_score['weighted_score']
            difficulty_breakdown[difficulty]['max_points'] += test_score['max_possible']
            if test_score['passed']:
                difficulty_breakdown[difficulty]['passed'] += 1

            # Category tracking
            category = result.get('category', 'general')
            if category not in category_scores:
                category_scores[category] = {
                    "total": 0,
                    "passed": 0,
                    "points": 0.0,
                    "max_points": 0.0
                }
            category_scores[category]['total'] += 1
            category_scores[category]['points'] += test_score['weighted_score']
            category_scores[category]['max_points'] += test_score['max_possible']
            if test_score['passed']:
                category_scores[category]['passed'] += 1

        # Calculate percentages
        overall_percentage = (total_points / max_points * 100) if max_points > 0 else 0

        # Dimension percentages
        dimension_scores = {}
        for dim in self.DIMENSION_WEIGHTS:
            dim_max = dimension_max[dim]
            dim_percentage = (dimension_totals[dim] / dim_max * 100) if dim_max > 0 else 0
            dimension_scores[dim] = {
                "points": round(dimension_totals[dim], 2),
                "max_points": round(dim_max, 2),
                "percentage": round(dim_percentage, 2),
                "weight": self.DIMENSION_WEIGHTS[dim]
            }

        # Calculate difficulty percentages
        for diff in difficulty_breakdown:
            stats = difficulty_breakdown[diff]
            if stats['max_points'] > 0:
                stats['percentage'] = round(stats['points'] / stats['max_points'] * 100, 2)
            else:
                stats['percentage'] = 0.0
            stats['points'] = round(stats['points'], 2)
            stats['max_points'] = round(stats['max_points'], 2)

        # Calculate category percentages
        for category in category_scores:
            stats = category_scores[category]
            if stats['max_points'] > 0:
                stats['percentage'] = round(stats['points'] / stats['max_points'] * 100, 2)
            else:
                stats['percentage'] = 0.0
            stats['points'] = round(stats['points'], 2)
            stats['max_points'] = round(stats['max_points'], 2)

        # Assign grade
        grade, grade_desc = self._get_grade(overall_percentage)

        # Identify strengths and weaknesses
        strengths, weaknesses = self._analyze_performance(
            dimension_scores, difficulty_breakdown, category_scores
        )

        return {
            "agent_id": agent_results.get('agent_id', 'unknown'),
            "language": agent_results.get('language', 'unknown'),
            "total_tests": len(test_scores),
            "tests_passed": sum(1 for ts in test_scores if ts['passed']),
            "pass_rate": round(sum(1 for ts in test_scores if ts['passed']) / len(test_scores) * 100, 2),
            "total_points": round(total_points, 2),
            "max_points": round(max_points, 2),
            "percentage": round(overall_percentage, 2),
            "grade": grade,
            "grade_description": grade_desc,
            "dimension_scores": dimension_scores,
            "difficulty_breakdown": difficulty_breakdown,
            "category_scores": category_scores,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "test_scores": test_scores
        }

    def _empty_score(self, agent_id: str) -> Dict:
        """Return empty score structure"""
        return {
            "agent_id": agent_id,
            "total_tests": 0,
            "tests_passed": 0,
            "pass_rate": 0.0,
            "total_points": 0.0,
            "max_points": 0.0,
            "percentage": 0.0,
            "grade": "N/A",
            "grade_description": "No Results"
        }

    def _get_grade(self, percentage: float) -> tuple:
        """Convert percentage to letter grade and description"""
        for threshold, grade, description in self.GRADE_THRESHOLDS:
            if percentage >= threshold:
                return grade, description
        return "F", "Failing"

    def _analyze_performance(self, dimension_scores: Dict,
                            difficulty_breakdown: Dict,
                            category_scores: Dict) -> tuple:
        """Identify strengths and weaknesses"""
        strengths = []
        weaknesses = []

        # Dimension analysis
        dim_list = [(dim, data['percentage']) for dim, data in dimension_scores.items()]
        dim_list.sort(key=lambda x: x[1], reverse=True)

        if dim_list[0][1] >= 80:
            strengths.append(f"Strong {dim_list[0][0]} ({dim_list[0][1]:.1f}%)")
        if dim_list[-1][1] < 70:
            weaknesses.append(f"Weak {dim_list[-1][0]} ({dim_list[-1][1]:.1f}%)")

        # Difficulty analysis
        for diff in ['easy', 'medium', 'hard']:
            stats = difficulty_breakdown[diff]
            if stats['total'] > 0:
                pass_rate = (stats['passed'] / stats['total']) * 100
                if pass_rate >= 85:
                    strengths.append(f"Excellent {diff} test performance ({pass_rate:.0f}%)")
                elif pass_rate < 60:
                    weaknesses.append(f"Struggles with {diff} tests ({pass_rate:.0f}%)")

        # Category analysis (top and bottom)
        if category_scores:
            cat_list = [(cat, data['percentage']) for cat, data in category_scores.items()]
            cat_list.sort(key=lambda x: x[1], reverse=True)

            if cat_list[0][1] >= 85:
                strengths.append(f"Excels in {cat_list[0][0]} ({cat_list[0][1]:.1f}%)")
            if len(cat_list) > 1 and cat_list[-1][1] < 65:
                weaknesses.append(f"Needs improvement in {cat_list[-1][0]} ({cat_list[-1][1]:.1f}%)")

        return strengths[:3], weaknesses[:3]  # Top 3 of each

    def score_all_agents(self, results_file: Path) -> Dict:
        """Score all agents from benchmark results"""
        with open(results_file) as f:
            data = json.load(f)

        scores = {}
        for agent_id, agent_results in data.get('results', {}).items():
            scores[agent_id] = self.calculate_agent_score(agent_results)

        # Create leaderboard
        leaderboard = self._create_leaderboard(scores)

        # Calculate aggregate statistics
        aggregate_stats = self._calculate_aggregate_stats(scores)

        return {
            "benchmark_type": "lightweight",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "total_agents": len(scores),
            "scores": scores,
            "leaderboard": leaderboard,
            "aggregate_statistics": aggregate_stats
        }

    def _create_leaderboard(self, scores: Dict) -> List[Dict]:
        """Create sorted leaderboard"""
        leaderboard = []

        for agent_id, score in scores.items():
            leaderboard.append({
                "rank": 0,  # Will be set after sorting
                "agent_id": agent_id,
                "language": score.get('language', 'unknown'),
                "score": score['percentage'],
                "grade": score['grade'],
                "tests_passed": f"{score['tests_passed']}/{score['total_tests']}",
                "pass_rate": score['pass_rate']
            })

        # Sort by score descending, then by pass_rate
        leaderboard.sort(key=lambda x: (x['score'], x['pass_rate']), reverse=True)

        # Assign ranks (handle ties)
        for i, entry in enumerate(leaderboard):
            if i == 0:
                entry['rank'] = 1
            elif entry['score'] == leaderboard[i-1]['score']:
                entry['rank'] = leaderboard[i-1]['rank']  # Tied
            else:
                entry['rank'] = i + 1

        return leaderboard

    def _calculate_aggregate_stats(self, scores: Dict) -> Dict:
        """Calculate aggregate statistics across all agents"""
        if not scores:
            return {}

        # Overall statistics
        total_tests = sum(s['total_tests'] for s in scores.values())
        total_passed = sum(s['tests_passed'] for s in scores.values())
        avg_score = sum(s['percentage'] for s in scores.values()) / len(scores)

        # Dimension averages
        dimension_avg = {}
        for dim in self.DIMENSION_WEIGHTS:
            dim_scores = [s['dimension_scores'][dim]['percentage']
                         for s in scores.values()
                         if 'dimension_scores' in s]
            dimension_avg[dim] = round(sum(dim_scores) / len(dim_scores), 2) if dim_scores else 0.0

        # Grade distribution
        grade_dist = {}
        for score in scores.values():
            grade = score['grade']
            grade_dist[grade] = grade_dist.get(grade, 0) + 1

        return {
            "total_tests_executed": total_tests,
            "total_tests_passed": total_passed,
            "overall_pass_rate": round(total_passed / total_tests * 100, 2) if total_tests > 0 else 0,
            "average_score": round(avg_score, 2),
            "highest_score": max(s['percentage'] for s in scores.values()),
            "lowest_score": min(s['percentage'] for s in scores.values()),
            "dimension_averages": dimension_avg,
            "grade_distribution": grade_dist
        }

    def generate_report(self, scores_data: Dict, output_file: Path):
        """Generate human-readable report"""
        lines = []
        lines.append("=" * 80)
        lines.append("LIGHTWEIGHT SWE BENCHMARK - SCORING REPORT")
        lines.append("=" * 80)
        lines.append("")

        # Leaderboard
        lines.append("📊 LEADERBOARD")
        lines.append("-" * 80)
        lines.append(f"{'Rank':<6} {'Agent':<25} {'Score':<10} {'Grade':<8} {'Pass Rate':<12} {'Tests':<10}")
        lines.append("-" * 80)

        for entry in scores_data['leaderboard']:
            lines.append(
                f"{entry['rank']:<6} "
                f"{entry['agent_id']:<25} "
                f"{entry['score']:>6.2f}%   "
                f"{entry['grade']:<8} "
                f"{entry['pass_rate']:>6.1f}%      "
                f"{entry['tests_passed']:<10}"
            )

        lines.append("")
        lines.append("-" * 80)
        lines.append("")

        # Aggregate stats
        agg = scores_data['aggregate_statistics']
        lines.append("📈 AGGREGATE STATISTICS")
        lines.append("-" * 80)
        lines.append(f"Total Tests Executed: {agg['total_tests_executed']}")
        lines.append(f"Total Tests Passed: {agg['total_tests_passed']} ({agg['overall_pass_rate']:.1f}%)")
        lines.append(f"Average Score: {agg['average_score']:.2f}%")
        lines.append(f"Score Range: {agg['lowest_score']:.1f}% - {agg['highest_score']:.1f}%")
        lines.append("")
        lines.append("Dimension Averages:")
        for dim, avg in agg['dimension_averages'].items():
            lines.append(f"  {dim.capitalize():<20} {avg:>6.1f}%")
        lines.append("")

        # Agent details
        lines.append("=" * 80)
        lines.append("AGENT DETAILS")
        lines.append("=" * 80)
        lines.append("")

        for agent_id, score in scores_data['scores'].items():
            lines.append(f"🤖 {agent_id}")
            lines.append(f"   Language: {score['language']}")
            lines.append(f"   Grade: {score['grade']} - {score['grade_description']}")
            lines.append(f"   Score: {score['percentage']:.2f}% ({score['total_points']:.1f}/{score['max_points']:.1f} points)")
            lines.append(f"   Pass Rate: {score['pass_rate']:.1f}% ({score['tests_passed']}/{score['total_tests']})")
            lines.append("")
            lines.append("   Dimensions:")
            for dim, data in score['dimension_scores'].items():
                lines.append(f"      {dim.capitalize():<20} {data['percentage']:>6.1f}%  ({data['points']:.1f}/{data['max_points']:.1f})")
            lines.append("")
            if score.get('strengths'):
                lines.append(f"   ✓ Strengths: {', '.join(score['strengths'])}")
            if score.get('weaknesses'):
                lines.append(f"   ⚠ Weaknesses: {', '.join(score['weaknesses'])}")
            lines.append("")
            lines.append("-" * 80)
            lines.append("")

        # Save report
        with open(output_file, 'w') as f:
            f.write('\n'.join(lines))

        return lines


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Score lightweight benchmark results"
    )

    # Use path relative to script location
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent  # docs/benchmarks
    default_results_dir = base_dir / "results" / "lightweight"

    parser.add_argument(
        "--results",
        default=str(default_results_dir / "benchmark_results.json"),
        help="Path to benchmark results JSON"
    )
    parser.add_argument(
        "--output",
        default=str(default_results_dir),
        help="Output directory for scores"
    )
    args = parser.parse_args()

    results_file = Path(args.results)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not results_file.exists():
        print(f"❌ Results file not found: {results_file}")
        print("   Run benchmark first: python3 scripts/run_lightweight_benchmark.py")
        exit(1)

    # Score results
    scorer = LightweightScorer(output_dir)
    scores = scorer.score_all_agents(results_file)

    # Save scores
    scores_file = output_dir / "scores.json"
    with open(scores_file, 'w') as f:
        json.dump(scores, f, indent=2)

    print(f"✅ Scores saved to {scores_file}")

    # Generate report
    report_file = output_dir / "scoring_report.txt"
    scorer.generate_report(scores, report_file)

    print(f"✅ Report saved to {report_file}")

    # Print summary
    print()
    print("📊 Quick Summary:")
    print("-" * 60)
    for entry in scores['leaderboard'][:3]:
        print(f"  {entry['rank']}. {entry['agent_id']:<20} {entry['score']:>6.2f}% ({entry['grade']})")
