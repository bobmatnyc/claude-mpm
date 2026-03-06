"""Test that normalization functions are consolidated.

This test ensures we don't accidentally reintroduce duplicate
normalization functions across the codebase.
"""

import re
from pathlib import Path

import pytest


def _find_python_files():
    """Find all Python files in src/claude_mpm/."""
    src_dir = Path("src/claude_mpm")
    if not src_dir.exists():
        pytest.skip("Source directory not found")
    return list(src_dir.rglob("*.py"))


class TestNormalizationConsolidation:
    """Verify normalization is centralized."""

    def test_no_inline_filename_normalization(self):
        """No inline .lower().replace('_', '-') patterns outside deployment_utils."""
        allowed_files = {
            "deployment_utils.py",  # The canonical location
            "event_handlers.py",  # Agent type routing fallback (not filename)
            "agent_template_builder.py",  # Claude Code name derivation (not filename)
            "validate_env.py",  # Env var formatting (unrelated to agent filenames)
        }

        violations = []
        pattern = re.compile(r'\.lower\(\)\.replace\(["\']_["\'],\s*["\']-["\']\)')

        for py_file in _find_python_files():
            if py_file.name in allowed_files:
                continue
            if "__pycache__" in str(py_file):
                continue

            content = py_file.read_text(errors="replace")
            for i, line in enumerate(content.splitlines(), 1):
                if pattern.search(line):
                    violations.append(f"  {py_file}:{i}: {line.strip()}")

        assert not violations, (
            "Found inline filename normalization outside deployment_utils.py:\n"
            + "\n".join(violations)
            + "\n\nUse normalize_deployment_filename() instead."
        )

    def test_no_duplicate_core_agents_definitions(self):
        """Only agent_name_registry.py should define CORE_AGENT_IDS."""
        allowed_files = {
            "agent_name_registry.py",
            "agent_presets.py",  # Uses deploy-path format (different purpose)
        }

        violations = []
        # Match new list/set/frozenset definitions, but NOT re-aliases
        pattern = re.compile(r"CORE_AGENTS?\s*=\s*[\[\{](?!})")

        for py_file in _find_python_files():
            if py_file.name in allowed_files:
                continue
            if "__pycache__" in str(py_file):
                continue

            content = py_file.read_text(errors="replace")
            for i, line in enumerate(content.splitlines(), 1):
                if pattern.search(line):
                    violations.append(f"  {py_file}:{i}: {line.strip()}")

        assert not violations, (
            "Found CORE_AGENTS definitions outside agent_name_registry.py:\n"
            + "\n".join(violations)
            + "\n\nImport CORE_AGENT_IDS from agent_name_registry instead."
        )
