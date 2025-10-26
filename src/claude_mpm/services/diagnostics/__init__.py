"""
Diagnostic service for claude-mpm health checks.

WHY: Provide a comprehensive diagnostic tool to help users identify and fix
common issues with their claude-mpm installation and configuration.

DESIGN DECISIONS:
- Modular check system for easy extension
- Interface-based design for consistency
- Clear status levels (ok, warning, error)
- Actionable fix suggestions
"""

from .diagnostic_runner import DiagnosticRunner
from .doctor_reporter import DoctorReporter
from .models import DiagnosticResult

__all__ = ["DiagnosticResult", "DiagnosticRunner", "DoctorReporter"]
