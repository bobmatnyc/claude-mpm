"""Unified setup commands for claude-mpm CLI.

WHY: Users need a consistent way to set up various services and integrations.

This package replaces the former ``setup.py`` god module (~2,700 lines) with
one handler module per service group. The public surface remains identical
so callers and tests can keep importing from ``claude_mpm.cli.commands.setup``.

Public API re-exported here:

* :class:`SetupCommand` — composed dispatcher (BaseCommand + handler mixins).
* :func:`manage_setup` — CLI entry point used by the executor.
* :class:`AuthFailedError`, :func:`_mcp_config_transaction`,
  :func:`_read_mcp_json_snapshot`, :func:`_restore_mcp_json` — .mcp.json
  rollback primitives (imported directly by tests).
* :func:`parse_service_args` — service-arg tokenizer.
* :data:`AUTONOMOUS_SETUP_SERVICES` — declarative registry of tools that
  implement their own ``<binary> setup`` and need no custom handler.

Module-level names ``console``, ``Path``, and ``subprocess`` are re-exported
because existing tests target them via
``patch("claude_mpm.cli.commands.setup.console")`` etc. ``Path`` and
``subprocess`` patch the underlying ``pathlib``/``subprocess`` modules
(via attribute access), so the patches propagate to handler modules without
extra work. ``console`` is a single shared instance from ``_shared``.
"""

from __future__ import annotations

import subprocess  # nosec B404
from pathlib import Path

from ._shared import console
from .command import SetupCommand, manage_setup
from .manifest_integration import ManifestSetupMixin
from .mcp_config import (
    AuthFailedError,
    _mcp_config_transaction,
    _read_mcp_json_snapshot,
    _restore_mcp_json,
)
from .parse_args import AUTONOMOUS_SETUP_SERVICES, parse_service_args

__all__ = [
    "AUTONOMOUS_SETUP_SERVICES",
    "AuthFailedError",
    "ManifestSetupMixin",
    "Path",
    "SetupCommand",
    "_mcp_config_transaction",
    "_read_mcp_json_snapshot",
    "_restore_mcp_json",
    "console",
    "manage_setup",
    "parse_service_args",
    "subprocess",
]
