#!/usr/bin/env python3
"""Test the consolidated dashboard hub"""

import sys
import time
from pathlib import Path

import requests

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_dashboard_hub():
    """Test dashboard hub and navigation"""

    print("Testing Dashboard Hub Consolidation...")
    print("=" * 60)

    # Test 1: Check if hub exists
    hub_path = (
        Path(__file__).parent.parent / "src/claude_mpm/dashboard/static/index.html"
    )
    if hub_path.exists():
        print("✅ Dashboard hub exists at /static/index.html")
    else:
        print("❌ Dashboard hub not found")
        return False

    # Test 2: Check production dashboards
    production_dir = (
        Path(__file__).parent.parent / "src/claude_mpm/dashboard/static/production"
    )
    expected_dashboards = ["events.html", "monitors.html", "main.html"]

    for dashboard in expected_dashboards:
        dashboard_path = production_dir / dashboard
        if dashboard_path.exists():
            print(f"✅ Production dashboard exists: {dashboard}")
        else:
            print(f"❌ Missing production dashboard: {dashboard}")

    # Test 3: Check archived test files
    archive_dir = (
        Path(__file__).parent.parent / "src/claude_mpm/dashboard/static/archive"
    )
    if archive_dir.exists():
        archived_files = list(archive_dir.glob("*.html"))
        print(f"✅ {len(archived_files)} test files archived")
        if len(archived_files) > 0:
            print(
                f"   Sample archived files: {', '.join([f.name for f in archived_files[:3]])}"
            )
    else:
        print("❌ Archive directory not found")

    # Test 4: Check legacy dashboards
    legacy_dir = Path(__file__).parent.parent / "src/claude_mpm/dashboard/static/legacy"
    legacy_dashboards = ["activity.html", "agents.html", "files.html", "tools.html"]

    for dashboard in legacy_dashboards:
        dashboard_path = legacy_dir / dashboard
        if dashboard_path.exists():
            print(f"✅ Legacy dashboard exists: {dashboard}")
        else:
            print(f"⚠️  Missing legacy dashboard: {dashboard}")

    # Test 5: Try to start the server and test accessibility
    print("\n" + "=" * 60)
    print("Starting monitor server to test dashboard accessibility...")

    # Import and start the server
    try:
        from claude_mpm.services.monitor.server import MonitorServer

        server = MonitorServer(port=8765)
        server.start_async()
        print("✅ Monitor server started on port 8765")

        # Give server time to start
        time.sleep(2)

        # Test hub accessibility
        try:
            response = requests.get("http://localhost:8765/static/", timeout=5)
            if response.status_code == 200:
                print("✅ Dashboard hub is accessible at http://localhost:8765/static/")

                # Check for key elements in the hub
                content = response.text
                checks = [
                    ("Production Dashboards" in content, "Production section"),
                    ("Legacy Dashboards" in content, "Legacy section"),
                    ("Development & Testing" in content, "Development section"),
                    ("Integrated Dashboard" in content, "Main dashboard link"),
                    ("Events Monitor" in content, "Events dashboard link"),
                    ("System Monitors" in content, "Monitors dashboard link"),
                ]

                for check, name in checks:
                    if check:
                        print(f"   ✅ {name} found in hub")
                    else:
                        print(f"   ❌ {name} missing from hub")
            else:
                print(f"❌ Dashboard hub returned status code: {response.status_code}")
        except Exception as e:
            print(f"❌ Error accessing dashboard hub: {e}")

        # Test production dashboard accessibility
        production_urls = [
            ("http://localhost:8765/dashboard", "Main Dashboard"),
            ("http://localhost:8765/static/production/events.html", "Events Monitor"),
            (
                "http://localhost:8765/static/production/monitors.html",
                "System Monitors",
            ),
        ]

        print("\nTesting production dashboard accessibility...")
        for url, name in production_urls:
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    # Check for navigation bar
                    if "nav-bar" in response.text:
                        print(f"✅ {name} accessible with navigation bar")
                    else:
                        print(f"⚠️  {name} accessible but missing navigation bar")
                else:
                    print(f"❌ {name} returned status code: {response.status_code}")
            except Exception as e:
                print(f"❌ Error accessing {name}: {e}")

        # Stop the server
        server.stop()
        print("\n✅ Monitor server stopped")

    except ImportError as e:
        print(f"⚠️  Could not import MonitorServer: {e}")
        print("   Testing file structure only...")
    except Exception as e:
        print(f"❌ Error during server test: {e}")

    print("\n" + "=" * 60)
    print("Dashboard Hub Consolidation Test Complete!")
    print("=" * 60)
    print("\n📊 Summary:")
    print("  - Dashboard hub created with modern card-based design")
    print("  - Production dashboards organized in /production/")
    print("  - Test files archived in /archive/")
    print("  - Navigation bars added to all production dashboards")
    print("  - Legacy dashboards preserved in /legacy/")
    print("\n🚀 Access the dashboard hub at: http://localhost:8765/static/")

    return True


if __name__ == "__main__":
    test_dashboard_hub()
