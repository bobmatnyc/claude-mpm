#!/usr/bin/env python3
"""
Test script to verify that DISABLE_TELEMETRY is handled correctly.

The expected behaviour after centralisation:
- When DISABLE_TELEMETRY is *not* set in the environment, entry points default
  it to "1" (telemetry disabled).
- When DISABLE_TELEMETRY is *already* set (e.g. DISABLE_TELEMETRY=0 by the
  user), entry points preserve that value instead of overwriting it.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest


def _run_python_snippet(snippet: str, env: dict | None = None) -> str:
    """Run a one-liner Python snippet in a subprocess and return its stdout."""
    run_env = os.environ.copy()
    if env is not None:
        run_env.update(env)
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            f"import sys; sys.path.insert(0, 'src'); {snippet}",
        ],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
        check=False,
        env=run_env,
    )
    return result.stdout.strip()


def test_python_module_default():
    """Entry point defaults DISABLE_TELEMETRY to '1' when not pre-set."""
    # Strip DISABLE_TELEMETRY from the child environment so we test the true
    # default path.
    child_env = {k: v for k, v in os.environ.items() if k != "DISABLE_TELEMETRY"}
    output = _run_python_snippet(
        "import os; "
        "from claude_mpm import __main__; "
        "print(os.environ.get('DISABLE_TELEMETRY', 'not set'))",
        env=child_env,
    )
    assert output == "1", (
        f"Expected DISABLE_TELEMETRY='1' when not pre-set, got {output!r}"
    )


def test_python_module_preserves_override():
    """Entry point preserves DISABLE_TELEMETRY='0' when pre-set by the user."""
    child_env = dict(os.environ)
    child_env["DISABLE_TELEMETRY"] = "0"
    output = _run_python_snippet(
        "import os; "
        "from claude_mpm import __main__; "
        "print(os.environ.get('DISABLE_TELEMETRY', 'not set'))",
        env=child_env,
    )
    assert output == "0", (
        f"Expected DISABLE_TELEMETRY='0' to be preserved, got {output!r}"
    )


@pytest.mark.skip(
    reason="Helper function called from main() with a script_path argument. "
    "Not a standalone pytest test — 'script_path' is not a registered pytest fixture."
)
def test_bash_script(script_path):
    """Test if a bash script sets DISABLE_TELEMETRY."""
    try:
        # Create a test that checks if the variable is exported
        test_cmd = f"bash -c 'source {script_path} 2>/dev/null; echo $DISABLE_TELEMETRY' 2>/dev/null | head -1"
        result = subprocess.run(
            test_cmd,
            capture_output=True,
            text=True,
            shell=True,
            cwd=Path(__file__).parent.parent,
            check=False,
        )
        output = result.stdout.strip()
        return output == "1"
    except Exception as e:
        print(f"  Error: {e}")
        return False


@pytest.mark.skip(
    reason="Helper function called from main() with a script_path argument. "
    "Not a standalone pytest test — 'script_path' is not a registered pytest fixture."
)
def test_python_script(script_path):
    """Test if a Python script sets DISABLE_TELEMETRY (via setdefault pattern)."""
    try:
        # Accept both the old hard-override pattern and the new setdefault pattern
        with script_path.open() as f:
            content = f.read()
        return (
            "os.environ['DISABLE_TELEMETRY'] = '1'" in content
            or 'os.environ["DISABLE_TELEMETRY"] = "1"' in content
            or "os.environ.setdefault('DISABLE_TELEMETRY', '1')" in content
            or 'os.environ.setdefault("DISABLE_TELEMETRY", "1")' in content
        )
    except Exception as e:
        print(f"  Error: {e}")
        return False


def main():
    """Run telemetry disable tests."""
    print("=" * 60)
    print("Testing DISABLE_TELEMETRY Environment Variable Setup")
    print("=" * 60)

    project_root = Path(__file__).parent.parent
    os.chdir(project_root)

    # Test bash scripts
    print("\n1. Testing Bash Entry Points:")
    bash_scripts = [
        ("claude-mpm", "Main wrapper"),
        ("scripts/claude-mpm", "Scripts wrapper"),
        ("scripts/claude-mpm-socketio", "SocketIO wrapper"),
    ]

    bash_passed = True
    for script, description in bash_scripts:
        script_path = project_root / script
        if script_path.exists():
            if test_bash_script(script_path):
                print(f"  OK {description}: DISABLE_TELEMETRY=1 is set")
            else:
                print(f"  FAIL {description}: DISABLE_TELEMETRY not properly set")
                bash_passed = False
        else:
            print(f"  SKIP {description}: Script not found at {script_path}")

    # Test Python entry points
    print("\n2. Testing Python Entry Points:")
    python_scripts = [
        ("src/claude_mpm/__main__.py", "Main module"),
        ("src/claude_mpm/cli/__main__.py", "CLI module"),
        ("src/claude_mpm/cli/__init__.py", "CLI init (main function)"),
        ("scripts/mcp_server.py", "MCP server"),
        ("scripts/mcp_wrapper.py", "MCP wrapper"),
        ("scripts/ticket.py", "Ticket script"),
        ("bin/claude-mpm-mcp", "MCP binary"),
        ("bin/claude-mpm-mcp-simple", "MCP simple binary"),
        ("bin/socketio-daemon", "SocketIO daemon"),
    ]

    python_passed = True
    for script, description in python_scripts:
        script_path = project_root / script
        if script_path.exists():
            if test_python_script(script_path):
                print(f"  OK {description}: Sets DISABLE_TELEMETRY=1")
            else:
                print(f"  FAIL {description}: Does not set DISABLE_TELEMETRY")
                python_passed = False
        else:
            print(f"  SKIP {description}: Script not found at {script_path}")

    # Test Node.js scripts
    print("\n3. Testing Node.js Entry Points:")
    node_scripts = [
        ("bin/claude-mpm", "Node.js main wrapper"),
        ("bin/ticket", "Node.js ticket wrapper"),
    ]

    node_passed = True
    for script, description in node_scripts:
        script_path = project_root / script
        if script_path.exists():
            with script_path.open() as f:
                content = f.read()
            if "process.env.DISABLE_TELEMETRY = '1'" in content:
                print(f"  OK {description}: Sets DISABLE_TELEMETRY=1")
            else:
                print(f"  FAIL {description}: Does not set DISABLE_TELEMETRY")
                node_passed = False
        else:
            print(f"  SKIP {description}: Script not found at {script_path}")

    # Test the actual Python module import
    print("\n4. Testing Runtime Behavior:")
    child_env = {k: v for k, v in os.environ.items() if k != "DISABLE_TELEMETRY"}
    output = _run_python_snippet(
        "import os; "
        "from claude_mpm import __main__; "
        "print(os.environ.get('DISABLE_TELEMETRY', 'not set'))",
        env=child_env,
    )
    module_passed = output == "1"
    if module_passed:
        print("  OK Python module defaults DISABLE_TELEMETRY=1")
    else:
        print(f"  FAIL Python module produced unexpected value: {output!r}")

    print("\n" + "=" * 60)
    all_passed = bash_passed and python_passed and node_passed and module_passed
    if all_passed:
        print("SUCCESS: All entry points properly set DISABLE_TELEMETRY=1")
        print("Telemetry is disabled by default in claude-mpm")
    else:
        print("WARNING: Some entry points may not disable telemetry")
        print("Please review the failed tests above")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
