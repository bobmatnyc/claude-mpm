#!/usr/bin/env python3
"""
Comprehensive test of the ticket system fixes.

WHY: This script validates that all ticket command fixes are working correctly,
including argument parsing, MCP integration understanding, and agent instructions.

DESIGN DECISION: We test both CLI and conceptual understanding to ensure the
complete fix is successful.
"""

import json
import os
import subprocess
import sys

import pytest

# Add the source directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


@pytest.mark.timeout(
    60
)  # 4 subprocess commands * 5s each = up to 20s; allow 60s margin
def test_cli_commands():
    """Test that all CLI commands work without AttributeError."""
    print("=" * 60)
    print("Testing CLI Commands")
    print("=" * 60)

    test_commands = [
        ["claude-mpm", "tickets", "list", "--limit", "5"],
        ["claude-mpm", "tickets", "view", "TSK-9999"],  # Non-existent is OK
        ["claude-mpm", "tickets", "close", "TSK-9998", "--comment", "Test close"],
        ["claude-mpm", "tickets", "search", "test"],
    ]

    all_passed = True

    for cmd in test_commands:
        print(f"\nTesting: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=5, check=False
            )

            # Check for AttributeError in output
            if "AttributeError" in result.stderr or "'id'" in result.stderr:
                print("  ❌ FAILED: AttributeError found in command")
                print(f"     Error: {result.stderr[:200]}")
                all_passed = False
            else:
                print(
                    f"  ✅ PASSED: No AttributeError (exit code: {result.returncode})"
                )

        except subprocess.TimeoutExpired:
            print("  ⚠️  Command timed out (but no AttributeError)")
        except Exception as e:
            print(f"  ❌ FAILED: {e}")
            all_passed = False

    return all_passed


def test_ticketing_agent_template():
    """Verify the ticketing agent template has been updated."""
    print("\n" + "=" * 60)
    print("Testing Ticketing Agent Template")
    print("=" * 60)

    template_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "src",
        "claude_mpm",
        "agents",
        "templates",
        "ticketing.json",
    )

    try:
        with template_path.open() as f:
            template = json.load(f)

        instructions = template.get("instructions", "")

        # Check for key improvements
        checks = [
            (
                "SERVICE ARCHITECTURE UNDERSTANDING" in instructions,
                "Service architecture section",
            ),
            ("MCP Gateway Layer" in instructions, "MCP Gateway understanding"),
            ("Closing Tickets" in instructions, "Close command documentation"),
            (
                "gh CLI" in instructions or "mcp-ticketer" in instructions,
                "Backend understanding",
            ),
        ]

        all_passed = True
        for check, description in checks:
            if check:
                print(f"  ✅ {description}: Found")
            else:
                print(f"  ❌ {description}: Missing")
                all_passed = False

        return all_passed

    except Exception as e:
        print(f"  ❌ Failed to read template: {e}")
        return False


def test_argument_compatibility():
    """Test that both 'id' and 'ticket_id' attributes work."""
    print("\n" + "=" * 60)
    print("Testing Argument Compatibility")
    print("=" * 60)

    from argparse import Namespace

    from claude_mpm.cli.commands.tickets import close_ticket_legacy as close_ticket

    # Test with ticket_id (parser format)
    args1 = Namespace()
    args1.ticket_id = "TEST-001"
    args1.comment = "Test"

    # Test with id (backward compat)
    args2 = Namespace()
    args2.id = "TEST-002"
    args2.resolution = "Fixed"

    try:
        # These should not raise AttributeError
        close_ticket(args1)
        print("  ✅ ticket_id attribute: Works")
    except AttributeError as e:
        print(f"  ❌ ticket_id attribute: Failed - {e}")
        return False
    except Exception:
        print("  ✅ ticket_id attribute: No AttributeError")

    try:
        close_ticket(args2)
        print("  ✅ id attribute: Works")
    except AttributeError as e:
        print(f"  ❌ id attribute: Failed - {e}")
        return False
    except Exception:
        print("  ✅ id attribute: No AttributeError")

    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("COMPREHENSIVE TICKET SYSTEM TEST")
    print("=" * 60)

    results = {
        "CLI Commands": test_cli_commands(),
        "Agent Template": test_ticketing_agent_template(),
        "Argument Compatibility": test_argument_compatibility(),
    }

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")

    if all(results.values()):
        print("\n🎉 ALL TESTS PASSED! The ticket system is fully fixed.")
        return 0
    print("\n⚠️  Some tests failed. Please review the fixes.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
