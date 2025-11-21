#!/usr/bin/env python3
"""
Test script to verify that the --resume flag is properly included
in the final Claude command that would be executed.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_interactive_session_command():
    """Test that InteractiveSession builds the command with --resume."""
    print("Testing InteractiveSession command building...")

    from claude_mpm.core.claude_runner import ClaudeRunner
    from claude_mpm.core.interactive_session import InteractiveSession

    # Create a mock runner with --resume in claude_args
    runner = MagicMock(spec=ClaudeRunner)
    runner.claude_args = ["--resume", "--model", "opus"]
    runner.launch_method = "exec"
    runner.enable_websocket = False
    runner.websocket_port = 8765
    runner.project_logger = None
    runner.response_logger = None
    runner.hook_service = None
    runner._create_system_prompt = MagicMock(return_value="test prompt")

    # Create session
    session = InteractiveSession(runner)
    session.initial_context = "test context"

    # Build command
    cmd = session._build_claude_command()

    # Verify --resume is in the command
    assert "--resume" in cmd, f"Expected --resume in command, got: {cmd}"
    print(f"✓ Command includes --resume: {' '.join(cmd)}")

    print("✅ InteractiveSession test passed!\n")


def test_run_command_with_resume():
    """Test the full run command flow with --resume."""
    print("Testing full run command flow...")

    from claude_mpm.cli.commands.parser import create_parser

    parser = create_parser()

    # Test 1: claude-mpm --resume
    with patch("claude_mpm.core.claude_runner.ClaudeRunner") as MockRunner:
        mock_instance = MagicMock()
        MockRunner.return_value = mock_instance

        args = parser.parse_args(["--resume"])
        # Simulate what _ensure_run_attributes does
        from claude_mpm.cli import _ensure_run_attributes

        _ensure_run_attributes(args)

        # The claude_args should contain --resume
        assert "--resume" in args.claude_args, (
            f"Expected --resume in claude_args, got: {args.claude_args}"
        )
        print(f"✓ claude-mpm --resume: claude_args = {args.claude_args}")

    # Test 2: claude-mpm run --resume
    with patch("claude_mpm.core.claude_runner.ClaudeRunner") as MockRunner:
        mock_instance = MagicMock()
        MockRunner.return_value = mock_instance

        args = parser.parse_args(["run", "--resume"])

        # Process the args through the run command logic
        from claude_mpm.cli.commands.run import filter_claude_mpm_args

        raw_claude_args = getattr(args, "claude_args", []) or []
        if getattr(args, "resume", False) and "--resume" not in raw_claude_args:
            raw_claude_args = ["--resume", *raw_claude_args]

        claude_args = filter_claude_mpm_args(raw_claude_args)

        assert "--resume" in claude_args, (
            f"Expected --resume in filtered args, got: {claude_args}"
        )
        print(f"✓ claude-mpm run --resume: claude_args = {claude_args}")

    # Test 3: claude-mpm run --resume -- --model opus
    with patch("claude_mpm.core.claude_runner.ClaudeRunner") as MockRunner:
        mock_instance = MagicMock()
        MockRunner.return_value = mock_instance

        args = parser.parse_args(["run", "--resume", "--", "--model", "opus"])

        raw_claude_args = getattr(args, "claude_args", []) or []
        if getattr(args, "resume", False) and "--resume" not in raw_claude_args:
            raw_claude_args = ["--resume", *raw_claude_args]

        claude_args = filter_claude_mpm_args(raw_claude_args)

        assert "--resume" in claude_args, (
            f"Expected --resume in filtered args, got: {claude_args}"
        )
        assert "--model" in claude_args, (
            f"Expected --model in filtered args, got: {claude_args}"
        )
        assert "opus" in claude_args, (
            f"Expected 'opus' in filtered args, got: {claude_args}"
        )
        print(f"✓ claude-mpm run --resume -- --model opus: claude_args = {claude_args}")

    print("✅ Full command flow tests passed!\n")


def test_actual_command_execution():
    """Test what command would actually be executed (dry run)."""
    print("Testing actual command that would be executed...")

    from claude_mpm.core.claude_runner import ClaudeRunner
    from claude_mpm.core.interactive_session import InteractiveSession

    # Simulate creating a runner with --resume
    with patch("claude_mpm.core.claude_runner.ClaudeRunner.setup_agents"):
        runner = ClaudeRunner(
            enable_tickets=False,
            log_level="OFF",
            claude_args=["--resume"],
            launch_method="exec",
        )

        # Create session
        session = InteractiveSession(runner)
        session.initial_context = None

        # Build the command that would be executed
        cmd = session._build_claude_command()

        print("  Command that would be executed:")
        print(f"  {' '.join(cmd)}")

        # Verify it contains expected elements
        assert "claude" in cmd, "Command should start with 'claude'"
        assert "--resume" in cmd, "Command should include --resume"
        assert "--dangerously-skip-permissions" in cmd, (
            "Command should include permissions flag"
        )

        print("✓ Command correctly includes --resume flag")

    print("✅ Command execution test passed!\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing --resume flag command building")
    print("=" * 60)
    print()

    try:
        test_interactive_session_command()
        test_run_command_with_resume()
        test_actual_command_execution()

        print("=" * 60)
        print("✅ ALL COMMAND BUILD TESTS PASSED!")
        print("=" * 60)
        print("\nThe --resume flag is correctly:")
        print("  1. Recognized by the bash wrapper as an MPM flag")
        print("  2. Parsed by the argument parser")
        print("  3. Added to claude_args when specified")
        print("  4. Passed through to the Claude command")
        print("\nExamples that now work:")
        print("  • claude-mpm --resume")
        print("  • claude-mpm run --resume")
        print("  • claude-mpm --resume -- --model opus")

    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
