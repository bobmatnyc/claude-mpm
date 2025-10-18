#!/usr/bin/env python3
"""
Generate Display Formats for Benchmark Scores

Creates:
- Markdown tables
- SVG badges
- HTML dashboards
- ASCII visualizations
"""

import json
from pathlib import Path
from typing import Dict, List
from datetime import datetime


class BenchmarkDisplayGenerator:
    """Generates various display formats for benchmark scores"""

    def __init__(self, results_dir: Path):
        self.results_dir = results_dir

    def load_scores(self) -> Dict:
        """Load scoring results"""
        scores_file = self.results_dir / "scores.json"
        with open(scores_file) as f:
            return json.load(f)

    def generate_markdown_table(self, scores: Dict) -> str:
        """Generate comprehensive markdown table"""
        md = []

        md.append("# Agent Benchmark Scores (Lightweight Suite)")
        md.append("")
        md.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md.append(f"**Total Agents:** {scores['total_agents']}")
        md.append("")

        # Leaderboard
        md.append("## 🏆 Leaderboard")
        md.append("")
        md.append("| Rank | Agent | Language | Score | Grade | Pass Rate | Easy | Medium | Hard | Status |")
        md.append("|------|-------|----------|-------|-------|-----------|------|--------|------|--------|")

        for entry in scores['leaderboard']:
            agent_id = entry['agent_id']
            agent_score = scores['scores'][agent_id]
            breakdown = agent_score['difficulty_breakdown']

            easy = f"{breakdown['easy']['passed']}/{breakdown['easy']['total']}"
            medium = f"{breakdown['medium']['passed']}/{breakdown['medium']['total']}"
            hard = f"{breakdown['hard']['passed']}/{breakdown['hard']['total']}"

            status = "✅" if entry['score'] >= 80 else "⚠️" if entry['score'] >= 70 else "❌"

            md.append(
                f"| {entry['rank']} | "
                f"{agent_id.replace('_', ' ').title()} | "
                f"{entry['language'].capitalize()} | "
                f"{entry['score']:.1f}% | "
                f"{entry['grade']} | "
                f"{entry['pass_rate']:.1f}% | "
                f"{easy} | {medium} | {hard} | {status} |"
            )

        md.append("")

        # Dimension Breakdown
        md.append("## 📊 Dimension Breakdown")
        md.append("")
        md.append("| Agent | Correctness | Idiomaticity | Performance | Best Practices |")
        md.append("|-------|-------------|--------------|-------------|----------------|")

        for entry in scores['leaderboard']:
            agent_id = entry['agent_id']
            dims = scores['scores'][agent_id]['dimension_scores']

            md.append(
                f"| {agent_id.replace('_', ' ').title()} | "
                f"{dims['correctness']['percentage']:.1f}% | "
                f"{dims['idiomaticity']['percentage']:.1f}% | "
                f"{dims['performance']['percentage']:.1f}% | "
                f"{dims['best_practices']['percentage']:.1f}% |"
            )

        md.append("")

        # Aggregate Statistics
        agg = scores['aggregate_statistics']
        md.append("## 📈 Aggregate Statistics")
        md.append("")
        md.append(f"- **Total Tests:** {agg['total_tests_executed']}")
        md.append(f"- **Tests Passed:** {agg['total_tests_passed']} ({agg['overall_pass_rate']:.1f}%)")
        md.append(f"- **Average Score:** {agg['average_score']:.2f}%")
        md.append(f"- **Score Range:** {agg['lowest_score']:.1f}% - {agg['highest_score']:.1f}%")
        md.append("")
        md.append("### Dimension Averages")
        md.append("")
        for dim, avg in agg['dimension_averages'].items():
            bar = self._create_bar(avg, 100, 30)
            md.append(f"- **{dim.replace('_', ' ').title()}:** {avg:.1f}% {bar}")
        md.append("")

        # Detailed Agent Profiles
        md.append("## 🤖 Agent Profiles")
        md.append("")

        for entry in scores['leaderboard']:
            agent_id = entry['agent_id']
            agent_score = scores['scores'][agent_id]

            md.append(f"### {agent_id.replace('_', ' ').title()}")
            md.append("")
            md.append(f"**Language:** {agent_score['language'].capitalize()}  ")
            md.append(f"**Grade:** {agent_score['grade']} - {agent_score['grade_description']}  ")
            md.append(f"**Score:** {agent_score['percentage']:.2f}%  ")
            md.append(f"**Pass Rate:** {agent_score['pass_rate']:.1f}% ({agent_score['tests_passed']}/{agent_score['total_tests']})")
            md.append("")

            # Dimension scores
            md.append("**Dimensions:**")
            md.append("")
            for dim, data in agent_score['dimension_scores'].items():
                bar = self._create_bar(data['percentage'], 100, 30)
                md.append(f"- {dim.replace('_', ' ').title()}: {data['percentage']:.1f}% {bar}")
            md.append("")

            # Strengths and Weaknesses
            if agent_score.get('strengths'):
                md.append("**✓ Strengths:**")
                for strength in agent_score['strengths']:
                    md.append(f"  - {strength}")
                md.append("")

            if agent_score.get('weaknesses'):
                md.append("**⚠ Areas for Improvement:**")
                for weakness in agent_score['weaknesses']:
                    md.append(f"  - {weakness}")
                md.append("")

            md.append("---")
            md.append("")

        return '\n'.join(md)

    def _create_bar(self, value: float, max_value: float, width: int = 20) -> str:
        """Create ASCII progress bar"""
        filled = int((value / max_value) * width)
        bar = '█' * filled + '░' * (width - filled)
        return f"`{bar}`"

    def generate_badges(self, scores: Dict) -> str:
        """Generate shields.io badge markdown"""
        badges = []

        badges.append("# Agent Benchmark Badges")
        badges.append("")
        badges.append("## Individual Agent Badges")
        badges.append("")

        for entry in scores['leaderboard']:
            agent_id = entry['agent_id']
            agent_name = agent_id.replace('_', '-')
            score = entry['score']
            grade = entry['grade'].replace('+', '%2B').replace('-', '%2D')

            # Determine color based on score
            if score >= 90:
                color = "brightgreen"
            elif score >= 80:
                color = "green"
            elif score >= 70:
                color = "yellowgreen"
            elif score >= 60:
                color = "yellow"
            else:
                color = "orange"

            badge_url = f"https://img.shields.io/badge/{agent_name}-{score:.0f}%25_{grade}-{color}"
            badges.append(f"![{agent_id}]({badge_url})")
            badges.append("")

        badges.append("## Combined Badge")
        badges.append("")

        agg = scores['aggregate_statistics']
        overall_score = agg['average_score']
        overall_color = "brightgreen" if overall_score >= 90 else "green" if overall_score >= 75 else "yellow"

        combined_badge = f"https://img.shields.io/badge/Overall-{overall_score:.0f}%25-{overall_color}"
        badges.append(f"![Overall Score]({combined_badge})")
        badges.append("")

        badges.append("## Dimension Badges")
        badges.append("")

        for dim, avg in agg['dimension_averages'].items():
            dim_name = dim.replace('_', '%20')
            dim_color = "brightgreen" if avg >= 80 else "green" if avg >= 70 else "yellow"
            dim_badge = f"https://img.shields.io/badge/{dim_name}-{avg:.0f}%25-{dim_color}"
            badges.append(f"![{dim}]({dim_badge})")
            badges.append("")

        return '\n'.join(badges)

    def generate_html_dashboard(self, scores: Dict) -> str:
        """Generate interactive HTML dashboard"""
        html = []

        html.append("<!DOCTYPE html>")
        html.append("<html lang='en'>")
        html.append("<head>")
        html.append("    <meta charset='UTF-8'>")
        html.append("    <meta name='viewport' content='width=device-width, initial-scale=1.0'>")
        html.append("    <title>Lightweight SWE Benchmark Dashboard</title>")
        html.append("    <style>")
        html.append(self._get_css())
        html.append("    </style>")
        html.append("</head>")
        html.append("<body>")
        html.append("    <div class='container'>")
        html.append("        <header>")
        html.append("            <h1>🚀 Lightweight SWE Benchmark Dashboard</h1>")
        html.append(f"            <p class='subtitle'>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>")
        html.append("        </header>")

        # Summary stats
        agg = scores['aggregate_statistics']
        html.append("        <div class='stats-grid'>")
        html.append(f"            <div class='stat-card'>")
        html.append(f"                <div class='stat-value'>{scores['total_agents']}</div>")
        html.append(f"                <div class='stat-label'>Agents</div>")
        html.append(f"            </div>")
        html.append(f"            <div class='stat-card'>")
        html.append(f"                <div class='stat-value'>{agg['total_tests_executed']}</div>")
        html.append(f"                <div class='stat-label'>Tests</div>")
        html.append(f"            </div>")
        html.append(f"            <div class='stat-card'>")
        html.append(f"                <div class='stat-value'>{agg['overall_pass_rate']:.1f}%</div>")
        html.append(f"                <div class='stat-label'>Pass Rate</div>")
        html.append(f"            </div>")
        html.append(f"            <div class='stat-card'>")
        html.append(f"                <div class='stat-value'>{agg['average_score']:.1f}%</div>")
        html.append(f"                <div class='stat-label'>Avg Score</div>")
        html.append(f"            </div>")
        html.append("        </div>")

        # Leaderboard
        html.append("        <section class='leaderboard'>")
        html.append("            <h2>🏆 Leaderboard</h2>")
        html.append("            <table>")
        html.append("                <thead>")
        html.append("                    <tr>")
        html.append("                        <th>Rank</th>")
        html.append("                        <th>Agent</th>")
        html.append("                        <th>Language</th>")
        html.append("                        <th>Score</th>")
        html.append("                        <th>Grade</th>")
        html.append("                        <th>Pass Rate</th>")
        html.append("                        <th>Tests</th>")
        html.append("                    </tr>")
        html.append("                </thead>")
        html.append("                <tbody>")

        for entry in scores['leaderboard']:
            grade_class = self._get_grade_class(entry['grade'])
            html.append("                    <tr>")
            html.append(f"                        <td class='rank'>{entry['rank']}</td>")
            html.append(f"                        <td class='agent-name'>{entry['agent_id'].replace('_', ' ').title()}</td>")
            html.append(f"                        <td>{entry['language'].capitalize()}</td>")
            html.append(f"                        <td class='score'>{entry['score']:.1f}%</td>")
            html.append(f"                        <td><span class='grade {grade_class}'>{entry['grade']}</span></td>")
            html.append(f"                        <td>{entry['pass_rate']:.1f}%</td>")
            html.append(f"                        <td>{entry['tests_passed']}</td>")
            html.append("                    </tr>")

        html.append("                </tbody>")
        html.append("            </table>")
        html.append("        </section>")

        # Dimension comparison
        html.append("        <section class='dimensions'>")
        html.append("            <h2>📊 Dimension Comparison</h2>")
        html.append("            <div class='dimension-grid'>")

        for dim, avg in agg['dimension_averages'].items():
            html.append("                <div class='dimension-card'>")
            html.append(f"                    <h3>{dim.replace('_', ' ').title()}</h3>")
            html.append(f"                    <div class='progress-bar'>")
            html.append(f"                        <div class='progress-fill' style='width: {avg}%'></div>")
            html.append(f"                    </div>")
            html.append(f"                    <div class='dimension-value'>{avg:.1f}%</div>")
            html.append("                </div>")

        html.append("            </div>")
        html.append("        </section>")

        html.append("    </div>")
        html.append("</body>")
        html.append("</html>")

        return '\n'.join(html)

    def _get_css(self) -> str:
        """Get CSS for HTML dashboard"""
        return """
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            padding: 40px;
        }
        header {
            text-align: center;
            margin-bottom: 40px;
            border-bottom: 2px solid #f0f0f0;
            padding-bottom: 20px;
        }
        h1 {
            color: #333;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .subtitle {
            color: #666;
            font-size: 0.9em;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-value {
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 10px;
        }
        .stat-label {
            font-size: 0.9em;
            opacity: 0.9;
        }
        .leaderboard, .dimensions {
            margin-bottom: 40px;
        }
        h2 {
            color: #333;
            margin-bottom: 20px;
            font-size: 1.8em;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #f0f0f0;
        }
        th {
            background: #f8f9fa;
            font-weight: 600;
            color: #555;
        }
        tr:hover {
            background: #f8f9fa;
        }
        .rank {
            font-weight: bold;
            color: #667eea;
        }
        .agent-name {
            font-weight: 500;
        }
        .score {
            font-weight: bold;
        }
        .grade {
            padding: 4px 12px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 0.9em;
        }
        .grade-a { background: #10b981; color: white; }
        .grade-b { background: #3b82f6; color: white; }
        .grade-c { background: #f59e0b; color: white; }
        .grade-d { background: #ef4444; color: white; }
        .dimension-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
        }
        .dimension-card {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
        }
        .dimension-card h3 {
            font-size: 1.1em;
            margin-bottom: 15px;
            color: #555;
        }
        .progress-bar {
            background: #e0e0e0;
            border-radius: 10px;
            height: 20px;
            overflow: hidden;
            margin-bottom: 10px;
        }
        .progress-fill {
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            height: 100%;
            transition: width 0.3s ease;
        }
        .dimension-value {
            text-align: right;
            font-weight: bold;
            color: #667eea;
        }
        """

    def _get_grade_class(self, grade: str) -> str:
        """Get CSS class for grade"""
        if grade.startswith('A'):
            return 'grade-a'
        elif grade.startswith('B'):
            return 'grade-b'
        elif grade.startswith('C'):
            return 'grade-c'
        else:
            return 'grade-d'

    def generate_ascii_chart(self, scores: Dict) -> str:
        """Generate ASCII bar chart"""
        lines = []

        lines.append("=" * 80)
        lines.append("AGENT BENCHMARK SCORES (Lightweight Suite)")
        lines.append("=" * 80)
        lines.append("")

        # Sort agents by score
        agents = [(e['agent_id'], e['score']) for e in scores['leaderboard']]

        # Find max score for scaling
        max_score = max(score for _, score in agents)
        bar_width = 50

        for rank, (agent_id, score) in enumerate(agents, 1):
            # Create bar
            filled = int((score / 100) * bar_width)
            bar = '█' * filled + '░' * (bar_width - filled)

            # Get grade
            grade = next(e['grade'] for e in scores['leaderboard'] if e['agent_id'] == agent_id)

            lines.append(f"{rank}. {agent_id:<25} [{bar}] {score:>6.1f}% ({grade})")

        lines.append("")
        lines.append("=" * 80)

        return '\n'.join(lines)

    def generate_all_displays(self):
        """Generate all display formats"""
        print("🎨 Generating Benchmark Displays")
        print("=" * 60)
        print()

        scores = self.load_scores()

        # Markdown table
        print("📝 Generating markdown table...")
        md_table = self.generate_markdown_table(scores)
        md_file = self.results_dir / "benchmark_report.md"
        with open(md_file, 'w') as f:
            f.write(md_table)
        print(f"   ✓ Saved to: {md_file.name}")

        # Badges
        print("🏅 Generating badges...")
        badges = self.generate_badges(scores)
        badges_file = self.results_dir / "badges.md"
        with open(badges_file, 'w') as f:
            f.write(badges)
        print(f"   ✓ Saved to: {badges_file.name}")

        # HTML dashboard
        print("🌐 Generating HTML dashboard...")
        html = self.generate_html_dashboard(scores)
        html_file = self.results_dir / "dashboard.html"
        with open(html_file, 'w') as f:
            f.write(html)
        print(f"   ✓ Saved to: {html_file.name}")

        # ASCII chart
        print("📊 Generating ASCII chart...")
        ascii_chart = self.generate_ascii_chart(scores)
        ascii_file = self.results_dir / "leaderboard.txt"
        with open(ascii_file, 'w') as f:
            f.write(ascii_chart)
        print(f"   ✓ Saved to: {ascii_file.name}")

        print()
        print("✅ All displays generated successfully!")
        print()
        print("📂 Generated files:")
        print(f"   - {md_file.name} (Markdown report)")
        print(f"   - {badges_file.name} (Badge markdown)")
        print(f"   - {html_file.name} (HTML dashboard)")
        print(f"   - {ascii_file.name} (ASCII leaderboard)")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate display formats for benchmark scores"
    )

    # Use path relative to script location
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent  # docs/benchmarks
    default_results_dir = base_dir / "results" / "lightweight"

    parser.add_argument(
        "--results-dir",
        default=str(default_results_dir),
        help="Directory containing scores.json"
    )
    args = parser.parse_args()

    results_dir = Path(args.results_dir)

    if not (results_dir / "scores.json").exists():
        print("❌ scores.json not found!")
        print("   Run scoring first: python3 scripts/score_lightweight_results.py")
        exit(1)

    generator = BenchmarkDisplayGenerator(results_dir)
    generator.generate_all_displays()
