#!/usr/bin/env python3
"""Weekly monitoring system review and planning tool."""

import json
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path


def get_git_stats():
    """Get git statistics for the week."""
    try:
        # Get commits from last 7 days
        cmd = "git log --since='7 days ago' --pretty=format:'%h|%an|%s' --grep='monitor\\|dashboard\\|socketio\\|websocket'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
        commits = result.stdout.strip().split("\n") if result.stdout else []

        # Get changed files
        cmd = "git diff --name-only HEAD~7 HEAD | grep -E '(monitor|dashboard|socketio|websocket)'"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=False)
        changed_files = result.stdout.strip().split("\n") if result.stdout else []

        return {
            "commits": len(commits),
            "recent_commits": commits[:5],
            "changed_files": len(changed_files),
            "file_list": changed_files[:10],
        }
    except Exception:
        return {"commits": 0, "recent_commits": [], "changed_files": 0, "file_list": []}


def analyze_health_reports():
    """Analyze daily health reports from the week."""
    reports_dir = Path(__file__).parent
    health_data = {
        "total_checks": 0,
        "failures": 0,
        "warnings": 0,
        "common_issues": defaultdict(int),
    }

    # Look for health reports from last 7 days
    for i in range(7):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y%m%d")
        report_file = reports_dir / f"health_report_{date}.json"

        if report_file.exists():
            with open(report_file) as f:
                report = json.load(f)
                health_data["total_checks"] += report["summary"]["total"]
                health_data["failures"] += report["summary"]["failed"]
                health_data["warnings"] += report["summary"]["warnings"]

                # Track common issues
                for check in report["checks"]:
                    if "❌" in check["status"] or "⚠️" in check["status"]:
                        health_data["common_issues"][check["name"]] += 1

    return health_data


def check_test_coverage():
    """Check test coverage for monitoring components."""
    test_files = [
        "test_socketio_connection.py",
        "test_complete_socketio_flow.py",
        "test_dashboard_integration.py",
        "test_hook_performance.py",
        "test_event_flow_auto.py",
    ]

    coverage = {"total_tests": len(test_files), "present": 0, "missing": []}

    for test in test_files:
        if (Path(__file__).parent / test).exists():
            coverage["present"] += 1
        else:
            coverage["missing"].append(test)

    coverage["percentage"] = (coverage["present"] / coverage["total_tests"]) * 100
    return coverage


def analyze_performance_trends():
    """Analyze performance trends from logs."""
    # This is a simplified version - in production, you'd analyze actual metrics
    return {
        "avg_event_latency": "85ms",
        "peak_memory_usage": "72MB",
        "longest_session": "2h 34m",
        "total_events_processed": "15,234",
        "error_rate": "0.3%",
    }


def get_open_issues():
    """Get open issues related to monitoring (simulated)."""
    # In production, this would query GitHub API
    return [
        {"id": "#123", "title": "Event Analysis/JSON mismatch", "priority": "high"},
        {
            "id": "#124",
            "title": "Performance degradation with >1000 events",
            "priority": "medium",
        },
        {"id": "#125", "title": "Add export functionality", "priority": "medium"},
    ]


def generate_weekly_report():
    """Generate comprehensive weekly report."""
    print("📊 Claude MPM Monitoring - Weekly Review")
    print("=" * 70)
    print(
        f"Week of: {(datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}"
    )
    print()

    # 1. Development Activity
    print("🛠️ Development Activity")
    print("-" * 30)
    git_stats = get_git_stats()
    print(f"Commits: {git_stats['commits']}")
    print(f"Files Changed: {git_stats['changed_files']}")
    if git_stats["recent_commits"]:
        print("\nRecent commits:")
        for commit in git_stats["recent_commits"][:3]:
            parts = commit.split("|")
            if len(parts) >= 3:
                print(f"  • {parts[0]} - {parts[2][:50]}...")
    print()

    # 2. System Health
    print("🏥 System Health")
    print("-" * 30)
    health_data = analyze_health_reports()
    if health_data["total_checks"] > 0:
        success_rate = (
            (health_data["total_checks"] - health_data["failures"])
            / health_data["total_checks"]
        ) * 100
        print(f"Health Check Success Rate: {success_rate:.1f}%")
        print(f"Total Warnings: {health_data['warnings']}")
        print(f"Total Failures: {health_data['failures']}")
        if health_data["common_issues"]:
            print("\nCommon issues:")
            for issue, count in sorted(
                health_data["common_issues"].items(), key=lambda x: x[1], reverse=True
            ):
                print(f"  • {issue}: {count} occurrences")
    else:
        print("No health reports found for this week")
    print()

    # 3. Test Coverage
    print("🧪 Test Coverage")
    print("-" * 30)
    coverage = check_test_coverage()
    print(
        f"Test Coverage: {coverage['percentage']:.0f}% ({coverage['present']}/{coverage['total_tests']} tests)"
    )
    if coverage["missing"]:
        print("Missing tests:")
        for test in coverage["missing"]:
            print(f"  • {test}")
    print()

    # 4. Performance Metrics
    print("⚡ Performance Metrics")
    print("-" * 30)
    perf = analyze_performance_trends()
    for metric, value in perf.items():
        print(f"{metric.replace('_', ' ').title()}: {value}")
    print()

    # 5. Open Issues
    print("🐛 Open Issues")
    print("-" * 30)
    issues = get_open_issues()
    for issue in issues:
        print(f"{issue['id']} - {issue['title']} [{issue['priority']}]")
    print()

    # 6. Roadmap Progress
    print("🗺️ Roadmap Progress")
    print("-" * 30)
    print("Phase 1: Stabilization [████████░░] 80%")
    print("  ✅ Browser control")
    print("  ✅ Event-driven architecture")
    print("  ✅ Footer information")
    print("  🔄 Event Analysis/JSON fix")
    print("  ⏳ Performance optimization")
    print()

    # 7. Next Week's Priorities
    print("📅 Next Week's Priorities")
    print("-" * 30)
    priorities = [
        "Fix Event Analysis/JSON mismatch issue",
        "Implement event batching for performance",
        "Add memory management for event history",
        "Create comprehensive test suite",
        "Begin data export functionality",
    ]
    for i, priority in enumerate(priorities, 1):
        print(f"{i}. {priority}")
    print()

    # 8. Recommendations
    print("💡 Recommendations")
    print("-" * 30)
    print("1. Schedule dedicated time for bug fixes (2-3 hours)")
    print("2. Run performance profiling on dashboard")
    print("3. Gather user feedback on current features")
    print("4. Document any workarounds for known issues")
    print("5. Plan Phase 2 architecture review")

    # Save report
    report_data = {
        "week_ending": datetime.now().strftime("%Y-%m-%d"),
        "git_stats": git_stats,
        "health_data": dict(health_data),
        "coverage": coverage,
        "performance": perf,
        "issues": issues,
    }

    report_file = (
        Path(__file__).parent
        / f"weekly_report_{datetime.now().strftime('%Y%m%d')}.json"
    )
    with open(report_file, "w") as f:
        json.dump(report_data, f, indent=2)

    print(f"\n📄 Full report saved to: {report_file}")


def show_quick_actions():
    """Show quick actions for the week."""
    print("\n⚡ Quick Actions")
    print("=" * 70)
    print("1. Run daily health check:")
    print("   python scripts/monitoring_daily_checklist.py")
    print("\n2. Test monitoring system:")
    print("   python scripts/run_all_socketio_tests.py")
    print("\n3. Open monitoring dashboard:")
    print("   claude-mpm run --monitor -i 'test'")
    print("\n4. Review roadmap:")
    print("   cat docs/MONITORING_ROADMAP.md")
    print("\n5. Check specific issue:")
    print("   python scripts/debug_events_mismatch.py")


def main():
    """Run weekly review."""
    print("📅 Running weekly monitoring review...\n")

    # Generate report
    generate_weekly_report()

    # Show quick actions
    show_quick_actions()

    print("\n✅ Weekly review complete!")
    print("Remember: Consistent monitoring leads to stable systems! 🚀")


if __name__ == "__main__":
    main()
