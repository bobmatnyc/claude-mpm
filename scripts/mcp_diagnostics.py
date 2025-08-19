#!/usr/bin/env python3
"""
MCP Server Diagnostics Script
==============================

This script provides comprehensive diagnostics for troubleshooting MCP server issues.
Run this if the MCP server is not working in Claude Desktop.

WHY: When things go wrong, we need detailed information about the environment,
configuration, and potential issues to quickly identify and fix problems.
"""

import sys
import os
import json
import subprocess
import shutil
from pathlib import Path
from datetime import datetime


def print_section(title):
    """Print a formatted section header."""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}")


def check_command(cmd, name):
    """Check if a command exists and get its version."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5
        )
        output = result.stdout + result.stderr
        # Get first line of output
        version = output.split('\n')[0] if output else "Unknown version"
        return True, version
    except (subprocess.SubprocessError, FileNotFoundError):
        return False, None


def diagnose():
    """Run comprehensive diagnostics."""
    print("MCP Server Diagnostics Report")
    print(f"Generated: {datetime.now().isoformat()}")
    
    # System Information
    print_section("System Information")
    print(f"Operating System: {sys.platform}")
    print(f"Python Version: {sys.version}")
    print(f"Python Executable: {sys.executable}")
    print(f"Current Directory: {os.getcwd()}")
    
    # Python Environment
    print_section("Python Environment")
    
    # Check for virtual environment
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    print(f"Virtual Environment: {'Yes' if in_venv else 'No'}")
    
    if in_venv:
        print(f"Virtual Env Path: {sys.prefix}")
    
    # Check Python path
    print(f"\nPython Path (first 5 entries):")
    for i, path in enumerate(sys.path[:5], 1):
        print(f"  {i}. {path}")
    
    # Check for different Python versions
    print_section("Python Installations")
    
    pythons = [
        ("python", ["python", "--version"]),
        ("python3", ["python3", "--version"]),
        ("python3.8", ["python3.8", "--version"]),
        ("python3.9", ["python3.9", "--version"]),
        ("python3.10", ["python3.10", "--version"]),
        ("python3.11", ["python3.11", "--version"]),
        ("python3.12", ["python3.12", "--version"]),
        ("python3.13", ["python3.13", "--version"]),
    ]
    
    for name, cmd in pythons:
        exists, version = check_command(cmd, name)
        if exists:
            print(f"  ✓ {name}: {version}")
        else:
            print(f"  ✗ {name}: Not found")
    
    # Project Structure
    print_section("Project Structure")
    
    project_root = Path.cwd()
    if not (project_root / "pyproject.toml").exists():
        # Try to find project root
        for parent in Path.cwd().parents:
            if (parent / "pyproject.toml").exists():
                project_root = parent
                break
    
    print(f"Project Root: {project_root}")
    
    # Check critical files
    critical_files = [
        ("pyproject.toml", project_root / "pyproject.toml"),
        ("Wrapper Script", project_root / "scripts" / "mcp_wrapper.py"),
        ("Server Script", project_root / "src" / "claude_mpm" / "scripts" / "mcp_server.py"),
        ("stdio_server.py", project_root / "src" / "claude_mpm" / "services" / "mcp_gateway" / "server" / "stdio_server.py"),
        ("claude_mpm __init__", project_root / "src" / "claude_mpm" / "__init__.py"),
        ("VERSION file", project_root / "VERSION"),
    ]
    
    all_present = True
    for name, path in critical_files:
        if path.exists():
            size = path.stat().st_size
            print(f"  ✓ {name}: {path.relative_to(project_root) if path.is_relative_to(project_root) else path} ({size} bytes)")
        else:
            print(f"  ✗ {name}: NOT FOUND at {path}")
            all_present = False
    
    # Check installed packages
    print_section("Package Installation")
    
    try:
        import claude_mpm
        print(f"  ✓ claude_mpm installed: {claude_mpm.__file__}")
        
        # Check version
        version_file = Path(claude_mpm.__file__).parent / "VERSION"
        if version_file.exists():
            version = version_file.read_text().strip()
            print(f"    Version: {version}")
    except ImportError as e:
        print(f"  ✗ claude_mpm not installed: {e}")
        print("    Run: pip install -e .")
    
    # Check dependencies
    dependencies = [
        "mcp",
        "pydantic",
        "asyncio",
        "aiohttp",
        "flask",
        "watchdog",
        "psutil",
    ]
    
    print("\nKey Dependencies:")
    for dep in dependencies:
        try:
            module = __import__(dep)
            location = getattr(module, '__file__', 'built-in')
            version = getattr(module, '__version__', 'unknown')
            print(f"  ✓ {dep}: {version} ({location})")
        except ImportError:
            print(f"  ✗ {dep}: Not installed")
    
    # Claude Desktop Configuration
    print_section("Claude Desktop Configuration")
    
    config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    
    if config_path.exists():
        print(f"Config file found: {config_path}")
        
        try:
            with open(config_path) as f:
                config = json.load(f)
            
            if "mcpServers" in config:
                print("\nMCP Servers configured:")
                for server_name, server_config in config["mcpServers"].items():
                    print(f"\n  {server_name}:")
                    print(f"    Command: {server_config.get('command', 'NOT SET')}")
                    if 'args' in server_config:
                        print(f"    Args: {json.dumps(server_config['args'])}")
                    if 'cwd' in server_config:
                        print(f"    CWD: {server_config['cwd']}")
                    
                    # Check if it's our server
                    if server_name == "claude-mpm-gateway":
                        args = server_config.get('args', [])
                        if args and 'mcp_wrapper.py' in str(args):
                            print("    ✓ Using wrapper script (recommended)")
                        elif args and 'mcp_server.py' in str(args):
                            print("    ⚠ Using legacy server script (consider updating to wrapper)")
                        else:
                            print("    ✗ Unknown script configuration")
            else:
                print("  ⚠ No MCP servers configured")
                print("\nTo configure, add this to claude_desktop_config.json:")
                print(json.dumps({
                    "mcpServers": {
                        "claude-mpm-gateway": {
                            "command": "python3",
                            "args": [str(project_root / "scripts" / "mcp_wrapper.py")],
                            "cwd": str(project_root)
                        }
                    }
                }, indent=2))
        except Exception as e:
            print(f"  ✗ Error reading config: {e}")
    else:
        print(f"  ✗ Config file not found at {config_path}")
        print("\nClaude Desktop may not be installed or configured")
    
    # Test MCP Server Startup
    print_section("MCP Server Startup Test")
    
    wrapper_path = project_root / "scripts" / "mcp_wrapper.py"
    if wrapper_path.exists():
        print(f"Testing wrapper script: {wrapper_path}")
        
        try:
            # Start the server process
            proc = subprocess.Popen(
                ["python3", str(wrapper_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(project_root)
            )
            
            # Wait briefly
            import time
            time.sleep(2)
            
            # Check if it's still running
            if proc.poll() is None:
                print("  ✓ Server process started successfully")
                proc.terminate()
            else:
                print("  ✗ Server process died immediately")
                stderr = proc.stderr.read()
                if stderr:
                    print("\nError output:")
                    for line in stderr.split('\n')[:10]:
                        if line.strip():
                            print(f"    {line}")
        except Exception as e:
            print(f"  ✗ Failed to start server: {e}")
    else:
        print(f"  ✗ Wrapper script not found at {wrapper_path}")
    
    # Recommendations
    print_section("Recommendations")
    
    issues = []
    
    if not all_present:
        issues.append("Some critical files are missing. Run: git status")
    
    try:
        import claude_mpm
    except ImportError:
        issues.append("claude-mpm not installed. Run: pip install -e .")
    
    if not config_path.exists():
        issues.append("Claude Desktop config not found. Is Claude Desktop installed?")
    elif "claude-mpm-gateway" not in config.get("mcpServers", {}):
        issues.append("MCP server not configured in Claude Desktop")
    
    if issues:
        print("Issues found:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
    else:
        print("✅ No major issues detected!")
        print("\nIf MCP is still not working:")
        print("  1. Restart Claude Desktop")
        print("  2. Check Claude Desktop developer console for errors")
        print("  3. Try running the wrapper script manually to see errors:")
        print(f"     python3 {wrapper_path}")
    
    print("\n" + "=" * 60)
    print(" End of Diagnostics Report")
    print("=" * 60)


if __name__ == "__main__":
    diagnose()