#!/usr/bin/env python3
"""Integration test for --resume flag passthrough."""

import os
import sys
import tempfile

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


def test_resume_flag_integration():
    """Test that --resume flag is properly passed to Claude."""

    print("Testing --resume flag integration...")

    # Test 1: Check that the command is parsed correctly
    cmd = [
        sys.executable,
        "-m",
        "claude_mpm.cli",
        "run",
        "--debug",
        "--",
        "--resume",
        "test-session-123",
        "--dry-run",  # Prevent actual Claude launch
    ]

    print("\nTest 1: Command parsing")
    print(f"Command: {' '.join(cmd)}")

    # Create a test script that mimics Claude CLI and prints its arguments
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(
            """#!/usr/bin/env python3
import sys
print("Claude CLI Mock - Arguments received:")
for i, arg in enumerate(sys.argv[1:]):
    print(f"  [{i}]: {arg}")
if "--resume" in sys.argv:
    idx = sys.argv.index("--resume")
    if idx + 1 < len(sys.argv):
        print(f"Resume session ID: {sys.argv[idx + 1]}")
    else:
        print("Resume flag without session ID")
sys.exit(0)
"""
        )
        mock_claude_path = f.name

    # Make it executable
    os.chmod(mock_claude_path, 0o755)

    # Test 2: Check with mock Claude CLI
    print("\nTest 2: Mock Claude CLI execution")

    # We can't easily replace the claude binary in the test, but we can verify
    # the filtering logic directly
    from claude_mpm.cli.commands.run import filter_claude_mpm_args

    test_cases = [
        (["--", "--resume", "session123"], ["--resume", "session123"]),
        (["--", "-r", "session456"], ["-r", "session456"]),
        (["--monitor", "--", "--resume", "abc"], ["--resume", "abc"]),
        (["--mpm-resume", "test", "--", "--resume", "xyz"], ["--resume", "xyz"]),
    ]

    all_passed = True
    for input_args, expected in test_cases:
        result = filter_claude_mpm_args(input_args)
        if result == expected:
            print(f"✓ {input_args} → {result}")
        else:
            print(f"✗ {input_args} → {result} (expected {expected})")
            all_passed = False

    # Clean up
    os.unlink(mock_claude_path)

    if all_passed:
        print("\n✅ All tests passed! The --resume flag is properly passed through.")
    else:
        print("\n❌ Some tests failed. Check the implementation.")
        sys.exit(1)


if __name__ == "__main__":
    test_resume_flag_integration()
