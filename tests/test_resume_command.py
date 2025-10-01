#!/usr/bin/env python3
"""
Test script to verify --resume flag command building.

This script simulates the full command building process to help diagnose
why the --resume flag might not be working as expected.
"""

import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.cli.commands.run import filter_claude_mpm_args


def simulate_command_building(resume=False, extra_args=None, launch_method="exec"):
    """Simulate the full command building process."""
    print("\n" + "=" * 60)
    print("CLAUDE-MPM RESUME FLAG VERIFICATION")
    print("=" * 60)

    # Simulate args object
    class Args:
        pass

    args = Args()
    args.resume = resume
    args.claude_args = extra_args or []
    args.logging = "info"
    args.launch_method = launch_method

    print("\n📋 Test Configuration:")
    print(f"   --resume flag: {resume}")
    print(f"   Extra args: {extra_args or []}")
    print(f"   Launch method: {launch_method}")

    # Step 1: Initial arguments
    print("\n1️⃣ Initial State:")
    raw_claude_args = list(args.claude_args) if args.claude_args else []
    print(f"   Raw claude_args: {raw_claude_args}")

    # Step 2: Add --resume if needed (from run.py)
    if args.resume:
        print("\n2️⃣ Processing --resume flag:")
        if "--resume" not in raw_claude_args:
            raw_claude_args = ["--resume", *raw_claude_args]
            print("   ✅ Added --resume to beginning")
        else:
            print("   ℹ️ --resume already present")  # noqa: RUF001
        print(f"   Updated args: {raw_claude_args}")

    # Step 3: Filter MPM-specific args (from run.py)
    print("\n3️⃣ Filtering MPM-specific arguments:")
    filtered_args = filter_claude_mpm_args(raw_claude_args)
    removed = list(set(raw_claude_args) - set(filtered_args))
    if removed:
        print(f"   ❌ Removed: {removed}")
    else:
        print("   ✅ No MPM args to remove")
    print(f"   Filtered args: {filtered_args}")

    # Step 4: Build final command (from interactive_session.py)
    print("\n4️⃣ Building final Claude command:")
    cmd = ["claude", "--model", "opus", "--dangerously-skip-permissions"]
    if filtered_args:
        cmd.extend(filtered_args)

    # Add system prompt (simplified for testing)
    cmd.extend(["--append-system-prompt", "<system_prompt_here>"])

    print(
        "   Base command: ['claude', '--model', 'opus', '--dangerously-skip-permissions']"
    )
    print(f"   Added args: {filtered_args}")
    print(f"   Final command: {' '.join(cmd)}")

    # Step 5: Verification
    print("\n5️⃣ Verification:")
    if "--resume" in cmd:
        position = cmd.index("--resume")
        print(f"   ✅ SUCCESS: --resume IS in final command at position {position}")
        print("   Command will resume Claude's last conversation")
    else:
        print("   ❌ FAILURE: --resume NOT in final command!")
        print("   Claude will start a new conversation")

    # Step 6: Launch method impact
    print(f"\n6️⃣ Launch Method Impact ({launch_method}):")
    if launch_method == "exec":
        print("   • Using os.execvpe() - replaces current process")
        print(f"   • Command: {cmd}")
        print("   • All arguments passed directly to Claude")
    else:
        print("   • Using subprocess - runs as child process")
        print(f"   • Command: {cmd}")
        print("   • Arguments passed via subprocess.run()")

    return cmd


def test_scenarios():
    """Test various scenarios."""
    scenarios = [
        {
            "name": "Basic --resume",
            "resume": True,
            "extra_args": [],
            "launch_method": "exec",
        },
        {
            "name": "--resume with other Claude args",
            "resume": True,
            "extra_args": ["--continue", "--max-tokens", "4000"],
            "launch_method": "exec",
        },
        {
            "name": "--resume already in args",
            "resume": True,
            "extra_args": ["--resume"],
            "launch_method": "exec",
        },
        {
            "name": "--resume with subprocess",
            "resume": True,
            "extra_args": [],
            "launch_method": "subprocess",
        },
        {
            "name": "No --resume flag",
            "resume": False,
            "extra_args": ["--continue"],
            "launch_method": "exec",
        },
        {
            "name": "--resume with MPM flags mixed in",
            "resume": True,
            "extra_args": ["--monitor", "--resume", "--debug"],
            "launch_method": "exec",
        },
    ]

    print("\n" + "=" * 60)
    print("TESTING MULTIPLE SCENARIOS")
    print("=" * 60)

    results = []
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n🧪 Test {i}: {scenario['name']}")
        print("-" * 40)
        cmd = simulate_command_building(
            resume=scenario["resume"],
            extra_args=scenario["extra_args"],
            launch_method=scenario["launch_method"],
        )

        success = "--resume" in cmd
        results.append(
            {"scenario": scenario["name"], "success": success, "command": " ".join(cmd)}
        )

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    for result in results:
        status = "✅" if result["success"] else "❌"
        print(f"{status} {result['scenario']}")
        if not result["success"]:
            print(f"   Command: {result['command']}")

    passed = sum(1 for r in results if r["success"])
    total = len(results)
    print(f"\nResults: {passed}/{total} tests passed")


def interactive_test():
    """Interactive testing mode."""
    print("\n" + "=" * 60)
    print("INTERACTIVE RESUME FLAG TESTING")
    print("=" * 60)
    print("\nThis tool helps diagnose --resume flag issues.")
    print("Enter command line arguments to test how they're processed.")
    print("Examples:")
    print("  --resume")
    print("  --resume --continue")
    print("  --monitor --resume --debug")
    print("\nType 'quit' to exit\n")

    while True:
        try:
            user_input = input("Enter args to test: ").strip()
            if user_input.lower() in ["quit", "exit", "q"]:
                break

            # Parse the input
            args_list = user_input.split() if user_input else []

            # Determine if --resume is present
            has_resume = "--resume" in args_list

            # Remove --resume from args_list since it's handled separately
            extra_args = [arg for arg in args_list if arg != "--resume"]

            # Simulate the command building
            simulate_command_building(
                resume=has_resume, extra_args=extra_args, launch_method="exec"
            )

        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")


def main():
    parser = argparse.ArgumentParser(
        description="Test --resume flag command building in claude-mpm"
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Run in interactive mode"
    )
    parser.add_argument(
        "--test-all", "-t", action="store_true", help="Run all test scenarios"
    )
    parser.add_argument("--resume", action="store_true", help="Test with --resume flag")
    parser.add_argument(
        "--launch-method",
        choices=["exec", "subprocess"],
        default="exec",
        help="Launch method to test",
    )
    parser.add_argument("extra_args", nargs="*", help="Additional arguments to test")

    args = parser.parse_args()

    if args.interactive:
        interactive_test()
    elif args.test_all:
        test_scenarios()
    else:
        # Single test
        simulate_command_building(
            resume=args.resume,
            extra_args=args.extra_args,
            launch_method=args.launch_method,
        )


if __name__ == "__main__":
    main()
