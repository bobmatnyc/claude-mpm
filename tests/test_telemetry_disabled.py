#!/usr/bin/env python3
"""
Test script to verify that DISABLE_TELEMETRY is set correctly.
"""

import os
import subprocess
import sys
from pathlib import Path


def test_python_module():
    """Test if DISABLE_TELEMETRY is set when running as Python module."""
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import os; os.environ.setdefault('DISABLE_TELEMETRY', '0'); "
                "import sys; sys.path.insert(0, 'src'); "
                "from claude_mpm import __main__; "
                "print(os.environ.get('DISABLE_TELEMETRY', 'not set'))",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            check=False,
        )
        output = result.stdout.strip()
        return output == "1"
    except Exception as e:
        print(f"  Error: {e}")
        return False


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


def test_python_script(script_path):
    """Test if a Python script sets DISABLE_TELEMETRY."""
    try:
        # Check if the script contains the environment setting
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
                print(f"  ✅ {description}: DISABLE_TELEMETRY=1 is set")
            else:
                print(f"  ❌ {description}: DISABLE_TELEMETRY not properly set")
                bash_passed = False
        else:
            print(f"  ⚠️  {description}: Script not found at {script_path}")

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
                print(f"  ✅ {description}: Sets DISABLE_TELEMETRY=1")
            else:
                print(f"  ❌ {description}: Does not set DISABLE_TELEMETRY")
                python_passed = False
        else:
            print(f"  ⚠️  {description}: Script not found at {script_path}")

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
                print(f"  ✅ {description}: Sets DISABLE_TELEMETRY=1")
            else:
                print(f"  ❌ {description}: Does not set DISABLE_TELEMETRY")
                node_passed = False
        else:
            print(f"  ⚠️  {description}: Script not found at {script_path}")

    # Test the actual Python module import
    print("\n4. Testing Runtime Behavior:")
    if test_python_module():
        print("  ✅ Python module sets DISABLE_TELEMETRY=1 on import")
        module_passed = True
    else:
        print("  ❌ Python module does not set DISABLE_TELEMETRY properly")
        module_passed = False

    print("\n" + "=" * 60)
    all_passed = bash_passed and python_passed and node_passed and module_passed
    if all_passed:
        print("✅ SUCCESS: All entry points properly set DISABLE_TELEMETRY=1")
        print("Telemetry is disabled by default in claude-mpm")
    else:
        print("⚠️  WARNING: Some entry points may not disable telemetry")
        print("Please review the failed tests above")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
