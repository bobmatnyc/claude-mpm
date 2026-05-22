"""Diagnostic check for the memory auto-capture hook.

Reports the availability of the trusty-memory and kuzu-memory backends used by
``claude_mpm.hooks.memory_capture``. Implements GitHub issues #536 / #537.
"""

from __future__ import annotations

import shutil
import urllib.error
import urllib.request
from pathlib import Path

from ....core.enums import OperationResult, ValidationSeverity
from ..models import DiagnosticResult
from .base_check import BaseDiagnosticCheck


class MemoryCaptureCheck(BaseDiagnosticCheck):
    """Check trusty-memory and kuzu-memory availability for auto-capture."""

    @property
    def name(self) -> str:
        return "memory_capture_check"

    @property
    def category(self) -> str:
        return "Memory Auto-Capture"

    def run(self) -> DiagnosticResult:
        details: dict[str, object] = {}

        # trusty-memory: binary present?
        trusty_installed = shutil.which("trusty-memory") is not None
        details["trusty_memory_installed"] = trusty_installed

        # trusty-memory: daemon reachable?
        trusty_daemon_up = False
        trusty_url = self._trusty_base_url()
        details["trusty_memory_url"] = trusty_url
        if trusty_installed:
            trusty_daemon_up = self._http_health(f"{trusty_url}/health")
        details["trusty_memory_daemon_reachable"] = trusty_daemon_up

        # kuzu-memory: binary present?
        kuzu_installed = shutil.which("kuzu-memory") is not None
        details["kuzu_memory_installed"] = kuzu_installed

        # Active backend (matches hook selection priority).
        if trusty_installed and trusty_daemon_up:
            active = "trusty-memory"
        elif kuzu_installed:
            active = "kuzu-memory"
        else:
            active = "none"
        details["active_backend"] = active
        details["palace"] = Path.cwd().name

        if active == "none":
            return DiagnosticResult(
                category=self.category,
                status=ValidationSeverity.WARNING,
                message=(
                    "No memory backend available — auto-capture is a no-op. "
                    "Install trusty-memory or kuzu-memory to enable."
                ),
                details=details,
                fix_command="claude-mpm setup trusty-memory",
                fix_description=(
                    "Install and start trusty-memory, or install kuzu-memory as fallback."
                ),
            )

        if active == "trusty-memory":
            message = f"Active backend: trusty-memory (palace: {details['palace']})"
        else:
            message = (
                f"Active backend: kuzu-memory (trusty-memory unavailable; "
                f"daemon reachable: {trusty_daemon_up})"
            )

        return DiagnosticResult(
            category=self.category,
            status=OperationResult.SUCCESS,
            message=message,
            details=details,
        )

    @staticmethod
    def _trusty_base_url() -> str:
        addr_file = Path.home() / ".trusty-memory" / "http_addr"
        try:
            addr = addr_file.read_text(encoding="utf-8").strip()
            if addr:
                return f"http://{addr}"
        except OSError:
            pass
        return "http://127.0.0.1:7070"

    @staticmethod
    def _http_health(url: str, timeout: float = 0.5) -> bool:
        try:
            req = urllib.request.Request(url, method="GET")  # nosec B310
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310
                return bool(200 <= resp.status < 300)
        except (urllib.error.URLError, TimeoutError, OSError):
            return False
