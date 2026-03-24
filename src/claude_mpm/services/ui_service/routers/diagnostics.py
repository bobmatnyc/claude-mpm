"""Diagnostics router.

Endpoints:
    GET /diagnostics         — run full system checks
    GET /diagnostics/version — version information
"""

import subprocess
import sys
from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/diagnostics", tags=["Diagnostics"])


def _run_cmd(cmd: list[str]) -> tuple[str, int]:
    """Run a command and return (stdout, returncode)."""
    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip(), result.returncode
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return str(exc), 1


def _check_auth() -> dict:
    """Check whether an Anthropic API key is available."""
    import os

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key:
        return {"ok": True, "message": "ANTHROPIC_API_KEY is set"}
    return {"ok": False, "message": "ANTHROPIC_API_KEY not set"}


def _check_cli_version() -> dict:
    """Check that the claude CLI is installed and return its version."""
    stdout, rc = _run_cmd(["claude", "--version"])
    if rc == 0:
        return {"ok": True, "version": stdout, "message": "claude CLI available"}
    return {"ok": False, "version": None, "message": f"claude CLI not found: {stdout}"}


def _check_node_version() -> dict:
    """Check that Node.js is available (required by the claude CLI)."""
    stdout, rc = _run_cmd(["node", "--version"])
    if rc == 0:
        return {"ok": True, "version": stdout, "message": "Node.js available"}
    return {"ok": False, "version": None, "message": f"Node.js not found: {stdout}"}


def _check_settings() -> dict:
    """Validate that ~/.claude/settings.json is well-formed JSON."""
    import json

    settings_path = Path.home() / ".claude" / "settings.json"
    if not settings_path.exists():
        return {
            "ok": True,
            "message": "settings.json not present (will be created on demand)",
        }
    try:
        json.loads(settings_path.read_text())
        return {"ok": True, "message": "settings.json is valid JSON"}
    except json.JSONDecodeError as exc:
        return {"ok": False, "message": f"settings.json parse error: {exc}"}


@router.get("", summary="Run full system diagnostics")
async def run_diagnostics():
    """Run a series of system health checks.

    Returns results for:
    - auth (ANTHROPIC_API_KEY presence)
    - cli (claude CLI availability and version)
    - node (Node.js availability)
    - settings (settings.json validity)
    """
    checks = {
        "auth": _check_auth(),
        "cli": _check_cli_version(),
        "node": _check_node_version(),
        "settings": _check_settings(),
    }
    overall_ok = all(c["ok"] for c in checks.values())
    return {"ok": overall_ok, "checks": checks}


@router.get("/version", summary="Get version information")
async def get_version():
    """Return CLI, service, and Python version information."""
    cli_stdout, cli_rc = _run_cmd(["claude", "--version"])
    cli_version = cli_stdout if cli_rc == 0 else None

    try:
        from claude_mpm import __version__ as service_version
    except ImportError:
        service_version = "unknown"

    python_version = (
        f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    )

    return {
        "cli_version": cli_version,
        "service_version": service_version,
        "python_version": python_version,
    }
