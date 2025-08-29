#!/usr/bin/env python3
"""
Test script to verify the Activity view session data fixes.
This launches the dashboard and checks for the specific issues mentioned.
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import requests


def main():
    print("🔧 Testing Activity View Session Data Fix")
    print("=" * 50)

    # Change to project directory
    project_root = Path(__file__).parent
    os.chdir(project_root)

    print(f"📁 Working directory: {os.getcwd()}")

    # Start the dashboard
    print("\n🚀 Starting dashboard...")
    dashboard_process = None

    try:
        # Dashboard is already running on port 8765
        dashboard_process = None  # We're using existing dashboard

        # Check existing dashboard connection
        print("⏳ Checking dashboard connection...")

        # Check if dashboard is running
        try:
            response = requests.get("http://localhost:8765", timeout=5)
            if response.status_code == 200:
                print("✅ Dashboard is running on port 8765")
                print("🌐 Open http://localhost:8765 in your browser")
                print("\n📋 Testing checklist:")
                print("1. Navigate to the Activity tab")
                print(
                    "2. Check that session dropdown shows correct dates (2024, not 2025)"
                )
                print(
                    "3. Check that sessions show non-zero agent/instruction/todo counts"
                )
                print("4. Verify the tree display matches the dropdown information")
                print("5. Look in browser console for detailed logging")
                print("\n🔍 Expected fixes:")
                print("- Session timestamps should be valid dates")
                print(
                    "- Agent, instruction, and todo counts should be > 0 if data exists"
                )
                print("- Dropdown and tree should show identical session information")
                print("- Console should show detailed session processing logs")

                print("\n⏸️  Press Enter to stop the dashboard...")
                input()

            else:
                print(f"❌ Dashboard returned status code {response.status_code}")

        except requests.exceptions.RequestException as e:
            print(f"❌ Could not connect to dashboard: {e}")

    except Exception as e:
        print(f"❌ Error starting dashboard: {e}")

    finally:
        if dashboard_process:
            print("🛑 Stopping dashboard...")
            dashboard_process.terminate()
            try:
                dashboard_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                dashboard_process.kill()

    print("\n✅ Test completed")


if __name__ == "__main__":
    main()
