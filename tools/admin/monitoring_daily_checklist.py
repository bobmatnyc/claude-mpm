#!/usr/bin/env python3
"""Daily monitoring system checklist and health check."""

import json
import os
import shlex
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


def run_command(cmd, timeout=30):
    """Run a command and return success status and output."""
    try:
        # Split command string into a list to avoid shell=True
        command_parts = shlex.split(cmd)
        result = subprocess.run(
            command_parts,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=Path(__file__).parent.parent,
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)


def check_monitoring_health():
    """Run daily health checks on the monitoring system."""
    print("🏥 Claude MPM Monitoring System Health Check")
    print("=" * 60)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    checks = []

    # 1. Check Socket.IO server
    print("1️⃣ Checking Socket.IO Server...")
    success, stdout, stderr = run_command(
        "python -c \"import socketio; print('Socket.IO available')\""
    )
    checks.append(
        {
            "name": "Socket.IO Library",
            "status": "✅ OK" if success else "❌ Failed",
            "details": stdout.strip() if success else stderr,
        }
    )

    # 2. Check WebSocket dependencies
    print("2️⃣ Checking WebSocket Support...")
    success, stdout, stderr = run_command(
        "python -c \"import websockets; print('WebSockets available')\""
    )
    checks.append(
        {
            "name": "WebSocket Library",
            "status": "✅ OK" if success else "❌ Failed",
            "details": stdout.strip() if success else stderr,
        }
    )

    # 3. Check dashboard file
    print("3️⃣ Checking Dashboard...")
    dashboard_path = Path(__file__).parent / "claude_mpm_socketio_dashboard.html"
    dashboard_exists = dashboard_path.exists()
    checks.append(
        {
            "name": "Dashboard File",
            "status": "✅ OK" if dashboard_exists else "❌ Missing",
            "details": f"Size: {dashboard_path.stat().st_size} bytes"
            if dashboard_exists
            else "File not found",
        }
    )

    # 4. Check test scripts
    print("4️⃣ Checking Test Scripts...")
    test_scripts = [
        "test_socketio_connection.py",
        "test_complete_socketio_flow.py",
        "test_hook_performance.py",
        "run_all_socketio_tests.py",
    ]
    missing_tests = []
    for script in test_scripts:
        if not (Path(__file__).parent / script).exists():
            missing_tests.append(script)

    checks.append(
        {
            "name": "Test Scripts",
            "status": "✅ OK"
            if not missing_tests
            else f"⚠️ {len(missing_tests)} missing",
            "details": f"Missing: {', '.join(missing_tests)}"
            if missing_tests
            else "All test scripts present",
        }
    )

    # 5. Check recent errors
    print("5️⃣ Checking Recent Errors...")
    log_file = Path.home() / ".claude_mpm" / "logs" / "claude_mpm.log"
    error_count = 0
    if log_file.exists():
        with open(log_file, "r") as f:
            # Check last 1000 lines
            lines = f.readlines()[-1000:]
            error_count = sum(1 for line in lines if "ERROR" in line)

    checks.append(
        {
            "name": "Recent Errors",
            "status": "✅ OK" if error_count < 10 else f"⚠️ {error_count} errors",
            "details": f"Found {error_count} errors in last 1000 log lines",
        }
    )

    # 6. Performance check
    print("6️⃣ Running Performance Check...")
    start_time = time.time()
    success, stdout, stderr = run_command(
        "python -c \"from claude_mpm.services.socketio_server import get_socketio_server; print('Server init OK')\"",
        timeout=5,
    )
    load_time = time.time() - start_time

    checks.append(
        {
            "name": "Server Init Performance",
            "status": "✅ OK" if load_time < 2 else f"⚠️ Slow ({load_time:.2f}s)",
            "details": f"Initialization time: {load_time:.2f}s",
        }
    )

    # Summary
    print("\n📊 Health Check Summary")
    print("=" * 60)

    failed_checks = [c for c in checks if "❌" in c["status"]]
    warning_checks = [c for c in checks if "⚠️" in c["status"]]

    for check in checks:
        print(f"{check['status']} {check['name']}")
        if check["details"]:
            print(f"   └─ {check['details']}")

    print("\n📈 Overall Status:")
    if failed_checks:
        print(f"❌ CRITICAL: {len(failed_checks)} checks failed")
    elif warning_checks:
        print(f"⚠️ WARNING: {len(warning_checks)} checks need attention")
    else:
        print("✅ All systems operational")

    # Save report
    report = {
        "timestamp": datetime.now().isoformat(),
        "checks": checks,
        "summary": {
            "total": len(checks),
            "passed": len([c for c in checks if "✅" in c["status"]]),
            "warnings": len(warning_checks),
            "failed": len(failed_checks),
        },
    }

    report_path = (
        Path(__file__).parent
        / f"health_report_{datetime.now().strftime('%Y%m%d')}.json"
    )
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n💾 Report saved to: {report_path}")

    return len(failed_checks) == 0


def run_quick_tests():
    """Run quick smoke tests."""
    print("\n🧪 Running Quick Tests")
    print("=" * 60)

    # Suppress browser for tests
    os.environ["CLAUDE_MPM_NO_BROWSER"] = "1"

    tests = [
        ("Socket.IO Connection", "python scripts/test_socketio_connection.py"),
        ("Event Flow", "python scripts/test_event_flow_auto.py"),
        ("Dashboard Load", "python scripts/test_dashboard_direct.py"),
    ]

    results = []
    for test_name, cmd in tests:
        print(f"\nRunning: {test_name}...")
        success, stdout, stderr = run_command(cmd, timeout=15)
        results.append(
            {
                "test": test_name,
                "passed": success,
                "output": stdout if success else stderr,
            }
        )
        print("✅ Passed" if success else "❌ Failed")

    passed = sum(1 for r in results if r["passed"])
    print(f"\n📊 Test Results: {passed}/{len(tests)} passed")

    return passed == len(tests)


def check_active_sessions():
    """Check for any active monitoring sessions."""
    print("\n🔍 Checking Active Sessions")
    print("=" * 60)

    # Check for running Socket.IO server
    success, stdout, stderr = run_command(
        "ps aux | grep 'socketio_server' | grep -v grep"
    )
    if success and stdout.strip():
        print("✅ Socket.IO server is running")
        print(f"   └─ {stdout.strip()[:80]}...")
    else:
        print("ℹ️ No Socket.IO server currently running")

    # Check for dashboard connections
    success, stdout, stderr = run_command("lsof -i :8765 | grep LISTEN")
    if success and stdout.strip():
        print("✅ Port 8765 is in use (monitoring active)")
    else:
        print("ℹ️ Port 8765 is free")


def show_next_steps():
    """Show recommended next steps based on health check."""
    print("\n📝 Recommended Actions")
    print("=" * 60)

    print("1. If errors were found:")
    print("   └─ Review logs: ~/.claude_mpm/logs/claude_mpm.log")
    print("   └─ Run: python scripts/diagnostic_socketio_server_monitor.py")

    print("\n2. To start monitoring:")
    print("   └─ claude-mpm run --monitor -i 'your task'")

    print("\n3. To run full test suite:")
    print("   └─ python scripts/run_all_socketio_tests.py")

    print("\n4. To open dashboard manually:")
    print("   └─ open http://localhost:8765/dashboard?autoconnect=true")

    print("\n5. Check the roadmap:")
    print("   └─ cat docs/MONITORING_ROADMAP.md")


def main():
    """Run daily checklist."""
    print("🌅 Good morning! Running daily monitoring checklist...\n")

    # Run health check
    health_ok = check_monitoring_health()

    # Run quick tests if healthy
    if health_ok:
        tests_ok = run_quick_tests()
    else:
        print("\n⚠️ Skipping tests due to health check failures")
        tests_ok = False

    # Check active sessions
    check_active_sessions()

    # Show next steps
    show_next_steps()

    # Final status
    print("\n" + "=" * 60)
    if health_ok and tests_ok:
        print("✅ Daily checklist complete - All systems go! 🚀")
        return 0
    else:
        print("⚠️ Daily checklist complete - Issues need attention")
        return 1


if __name__ == "__main__":
    sys.exit(main())
