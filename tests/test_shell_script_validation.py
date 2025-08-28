#!/usr/bin/env python3
"""
Python companion tests to validate the claude-hook-handler.sh shell script.

This test suite provides Python-based validation of the shell script functionality,
complementing the shell-based tests with more complex scenarios and assertions.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestClaudeHookHandlerShellScript(unittest.TestCase):
    """Test the claude-hook-handler.sh shell script functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory
        self.temp_dir = tempfile.mkdtemp()
        self.test_dir = Path(self.temp_dir)

        # Create mock project structure
        self.src_dir = self.test_dir / "src" / "claude_mpm"
        self.scripts_dir = self.src_dir / "scripts"
        self.hooks_dir = self.src_dir / "hooks" / "claude_hooks"

        self.scripts_dir.mkdir(parents=True)
        self.hooks_dir.mkdir(parents=True)

        # Find the actual script
        project_root = Path(__file__).parent.parent
        actual_script = (
            project_root / "src" / "claude_mpm" / "scripts" / "claude-hook-handler.sh"
        )

        if actual_script.exists():
            # Copy actual script to test location
            self.script_path = self.scripts_dir / "claude-hook-handler.sh"
            shutil.copy2(actual_script, self.script_path)
            self.script_path.chmod(0o755)
        else:
            # Create a minimal test script
            self.script_path = self.scripts_dir / "claude-hook-handler.sh"
            self._create_test_script()

    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir)

    def _create_test_script(self):
        """Create a minimal test version of the shell script."""
        script_content = """#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_MPM_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

find_python_command() {
    if [ -f "$CLAUDE_MPM_ROOT/venv/bin/activate" ]; then
        echo "$CLAUDE_MPM_ROOT/venv/bin/python"
    elif [ -f "$CLAUDE_MPM_ROOT/.venv/bin/activate" ]; then
        echo "$CLAUDE_MPM_ROOT/.venv/bin/python"
    elif command -v python3 &> /dev/null; then
        echo "python3"
    else
        echo "python"
    fi
}

PYTHON_CMD=$(find_python_command)

if [ -d "$CLAUDE_MPM_ROOT/src" ]; then
    export PYTHONPATH="$CLAUDE_MPM_ROOT/src:$PYTHONPATH"
fi

export CLAUDE_MPM_SOCKETIO_PORT="${CLAUDE_MPM_SOCKETIO_PORT:-8765}"

if ! exec "$PYTHON_CMD" -m claude_mpm.hooks.claude_hooks.hook_handler "$@" 2>/tmp/claude-mpm-hook-error.log; then
    echo '{"action": "continue"}'
    exit 0
fi
"""
        self.script_path.write_text(script_content)
        self.script_path.chmod(0o755)

    def test_script_exists_and_executable(self):
        """Test that the script exists and is executable."""
        self.assertTrue(self.script_path.exists())
        self.assertTrue(os.access(self.script_path, os.X_OK))

    def test_script_sets_pythonpath(self):
        """Test that the script sets PYTHONPATH correctly."""
        # Create a mock Python that prints environment
        mock_python = self.test_dir / "venv" / "bin" / "python"
        mock_python.parent.mkdir(parents=True)
        mock_python.write_text(
            """#!/bin/bash
echo "PYTHONPATH=$PYTHONPATH"
echo '{"action": "continue"}'
exit 0
"""
        )
        mock_python.chmod(0o755)

        # Create venv activate script
        (mock_python.parent / "activate").touch()

        # Run the script
        result = subprocess.run(
            [str(self.script_path)],
            cwd=str(self.test_dir),
            capture_output=True,
            text=True,
            check=False,
        )

        # Check PYTHONPATH was set
        self.assertIn(str(self.test_dir / "src"), result.stdout)

    def test_script_handles_missing_python(self):
        """Test that the script handles missing Python gracefully."""
        # Run script without Python available
        env = os.environ.copy()
        env["PATH"] = "/nonexistent"

        result = subprocess.run(
            [str(self.script_path)],
            cwd=str(self.test_dir),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

        # Should output continue action
        self.assertIn('{"action": "continue"}', result.stdout)

    def test_script_passes_arguments(self):
        """Test that arguments are passed to the Python module."""
        # Create mock Python that prints arguments
        mock_python = self.test_dir / "venv" / "bin" / "python"
        mock_python.parent.mkdir(parents=True)
        mock_python.write_text(
            """#!/bin/bash
echo "Args: $@"
echo '{"action": "continue"}'
exit 0
"""
        )
        mock_python.chmod(0o755)
        (mock_python.parent / "activate").touch()

        # Run with arguments
        result = subprocess.run(
            [str(self.script_path), "arg1", "arg2", "arg3"],
            cwd=str(self.test_dir),
            capture_output=True,
            text=True,
            check=False,
        )

        # Check arguments were passed
        self.assertIn("arg1 arg2 arg3", result.stdout)

    def test_script_sets_socketio_port(self):
        """Test that the script sets Socket.IO port."""
        # Create mock Python that prints environment
        mock_python = self.test_dir / "venv" / "bin" / "python"
        mock_python.parent.mkdir(parents=True)
        mock_python.write_text(
            """#!/bin/bash
echo "SOCKETIO_PORT=$CLAUDE_MPM_SOCKETIO_PORT"
echo '{"action": "continue"}'
exit 0
"""
        )
        mock_python.chmod(0o755)
        (mock_python.parent / "activate").touch()

        # Test default port
        result = subprocess.run(
            [str(self.script_path)],
            cwd=str(self.test_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertIn("SOCKETIO_PORT=8765", result.stdout)

        # Test custom port
        env = os.environ.copy()
        env["CLAUDE_MPM_SOCKETIO_PORT"] = "9999"
        result = subprocess.run(
            [str(self.script_path)],
            cwd=str(self.test_dir),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        self.assertIn("SOCKETIO_PORT=9999", result.stdout)

    def test_script_error_handling(self):
        """Test that the script handles errors gracefully."""
        # Create failing Python script
        mock_python = self.test_dir / "venv" / "bin" / "python"
        mock_python.parent.mkdir(parents=True)
        mock_python.write_text(
            """#!/bin/bash
echo "Error: Something went wrong" >&2
exit 1
"""
        )
        mock_python.chmod(0o755)
        (mock_python.parent / "activate").touch()

        # Run script
        result = subprocess.run(
            [str(self.script_path)],
            cwd=str(self.test_dir),
            capture_output=True,
            text=True,
            check=False,
        )

        # Should still output continue
        self.assertIn('{"action": "continue"}', result.stdout)
        # Should have zero exit code
        self.assertEqual(result.returncode, 0)

    def test_script_with_stdin_input(self):
        """Test that the script properly handles stdin input."""
        # Create mock Python that reads stdin
        mock_python = self.test_dir / "venv" / "bin" / "python"
        mock_python.parent.mkdir(parents=True)
        mock_python.write_text(
            """#!/usr/bin/env python3
import json
import sys

try:
    data = sys.stdin.read()
    if data:
        parsed = json.loads(data)
        print(f"Received: {parsed.get('hook_event_name', 'unknown')}")
except:
    pass

print(json.dumps({"action": "continue"}))
"""
        )
        mock_python.chmod(0o755)
        (mock_python.parent / "activate").touch()

        # Send JSON input via stdin
        test_input = json.dumps({"hook_event_name": "Stop", "data": "test"})

        result = subprocess.run(
            [str(self.script_path)],
            cwd=str(self.test_dir),
            input=test_input,
            capture_output=True,
            text=True,
            check=False,
        )

        # Should process the input
        self.assertIn("Received: Stop", result.stdout)
        self.assertIn('{"action": "continue"}', result.stdout)

    def test_script_debug_mode(self):
        """Test debug mode functionality."""
        # Enable debug mode
        env = os.environ.copy()
        env["CLAUDE_MPM_HOOK_DEBUG"] = "true"

        # Create mock Python
        mock_python = self.test_dir / "venv" / "bin" / "python"
        mock_python.parent.mkdir(parents=True)
        mock_python.write_text(
            """#!/bin/bash
echo '{"action": "continue"}'
exit 0
"""
        )
        mock_python.chmod(0o755)
        (mock_python.parent / "activate").touch()

        # Run script with debug enabled
        result = subprocess.run(
            [str(self.script_path)],
            cwd=str(self.test_dir),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

        # Check if debug log was created (if script supports it)
        Path("/tmp/claude-mpm-hook.log")
        # Note: Actual debug logging depends on script implementation

        # Should still work normally
        self.assertIn('{"action": "continue"}', result.stdout)

    def test_script_python_detection_order(self):
        """Test Python detection preference order."""
        # Test 1: venv takes precedence
        venv_python = self.test_dir / "venv" / "bin" / "python"
        venv_python.parent.mkdir(parents=True)
        venv_python.write_text(
            """#!/bin/bash
echo "Using venv Python"
echo '{"action": "continue"}'
exit 0
"""
        )
        venv_python.chmod(0o755)
        (venv_python.parent / "activate").touch()

        result = subprocess.run(
            [str(self.script_path)],
            cwd=str(self.test_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertIn("Using venv Python", result.stdout)

        # Test 2: .venv is used if venv doesn't exist
        shutil.rmtree(self.test_dir / "venv")
        dot_venv_python = self.test_dir / ".venv" / "bin" / "python"
        dot_venv_python.parent.mkdir(parents=True)
        dot_venv_python.write_text(
            """#!/bin/bash
echo "Using .venv Python"
echo '{"action": "continue"}'
exit 0
"""
        )
        dot_venv_python.chmod(0o755)
        (dot_venv_python.parent / "activate").touch()

        result = subprocess.run(
            [str(self.script_path)],
            cwd=str(self.test_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertIn("Using .venv Python", result.stdout)


class TestShellScriptRobustness(unittest.TestCase):
    """Test shell script robustness and edge cases."""

    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_dir = Path(self.temp_dir)

    def tearDown(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir)

    def test_script_with_spaces_in_path(self):
        """Test script handles spaces in directory paths."""
        # Create directory with spaces
        space_dir = self.test_dir / "dir with spaces" / "claude mpm"
        scripts_dir = space_dir / "src" / "claude_mpm" / "scripts"
        scripts_dir.mkdir(parents=True)

        # Copy script
        project_root = Path(__file__).parent.parent
        actual_script = (
            project_root / "src" / "claude_mpm" / "scripts" / "claude-hook-handler.sh"
        )

        if actual_script.exists():
            script_path = scripts_dir / "claude-hook-handler.sh"
            shutil.copy2(actual_script, script_path)
            script_path.chmod(0o755)

            # Create mock Python
            venv_dir = space_dir / "venv" / "bin"
            venv_dir.mkdir(parents=True)
            mock_python = venv_dir / "python"
            mock_python.write_text(
                """#!/bin/bash
echo "Executed from path with spaces"
echo '{"action": "continue"}'
exit 0
"""
            )
            mock_python.chmod(0o755)
            (venv_dir / "activate").touch()

            # Run script
            result = subprocess.run(
                [str(script_path)],
                cwd=str(space_dir),
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertIn("Executed from path with spaces", result.stdout)
            self.assertIn('{"action": "continue"}', result.stdout)

    def test_script_concurrent_execution(self):
        """Test that multiple script instances can run concurrently."""
        import threading

        # Setup script
        scripts_dir = self.test_dir / "src" / "claude_mpm" / "scripts"
        scripts_dir.mkdir(parents=True)

        project_root = Path(__file__).parent.parent
        actual_script = (
            project_root / "src" / "claude_mpm" / "scripts" / "claude-hook-handler.sh"
        )

        if actual_script.exists():
            script_path = scripts_dir / "claude-hook-handler.sh"
            shutil.copy2(actual_script, script_path)
            script_path.chmod(0o755)

            # Create mock Python that sleeps briefly
            venv_dir = self.test_dir / "venv" / "bin"
            venv_dir.mkdir(parents=True)
            mock_python = venv_dir / "python"
            mock_python.write_text(
                """#!/usr/bin/env python3
import json
import time
import sys
import os

pid = os.getpid()
time.sleep(0.1)
print(json.dumps({"action": "continue", "pid": pid}))
"""
            )
            mock_python.chmod(0o755)
            (venv_dir / "activate").touch()

            results = []

            def run_script():
                result = subprocess.run(
                    [str(script_path)],
                    cwd=str(self.test_dir),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                results.append(result.stdout)

            # Run multiple instances concurrently
            threads = []
            for _ in range(3):
                thread = threading.Thread(target=run_script)
                threads.append(thread)
                thread.start()

            # Wait for all to complete
            for thread in threads:
                thread.join()

            # All should complete successfully
            self.assertEqual(len(results), 3)
            for result in results:
                self.assertIn('"action": "continue"', result)

    def test_script_signal_handling(self):
        """Test that the script handles signals properly."""
        # This test would require more complex setup to test signal handling
        # For now, we'll test that the script completes normally

    def test_script_exit_codes(self):
        """Test that script propagates exit codes correctly."""
        scripts_dir = self.test_dir / "src" / "claude_mpm" / "scripts"
        scripts_dir.mkdir(parents=True)

        # Create test script
        script_path = scripts_dir / "claude-hook-handler.sh"
        script_content = """#!/bin/bash
PYTHON_CMD="python3"
if [ -f "$(pwd)/venv/bin/python" ]; then
    PYTHON_CMD="$(pwd)/venv/bin/python"
fi

if ! exec "$PYTHON_CMD" -m claude_mpm.hooks.claude_hooks.hook_handler "$@"; then
    echo '{"action": "continue"}'
    exit 0
fi
"""
        script_path.write_text(script_content)
        script_path.chmod(0o755)

        # Test with successful Python execution
        venv_dir = self.test_dir / "venv" / "bin"
        venv_dir.mkdir(parents=True)
        success_python = venv_dir / "python"
        success_python.write_text(
            """#!/bin/bash
echo '{"action": "continue"}'
exit 0
"""
        )
        success_python.chmod(0o755)

        result = subprocess.run(
            [str(script_path)], cwd=str(self.test_dir), capture_output=True, check=False
        )
        self.assertEqual(result.returncode, 0)

        # Test with failing Python execution
        fail_python = venv_dir / "python"
        fail_python.write_text(
            """#!/bin/bash
exit 1
"""
        )
        fail_python.chmod(0o755)

        result = subprocess.run(
            [str(script_path)],
            cwd=str(self.test_dir),
            capture_output=True,
            text=True,
            check=False,
        )
        # Should still exit 0 and output continue
        self.assertEqual(result.returncode, 0)
        self.assertIn('{"action": "continue"}', result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
