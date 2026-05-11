"""Argument parsing for ``claude-mpm setup``.

Splits the freeform ``setup`` positional arglist (e.g.
``slack-mpm oauth --oauth-service gworkspace-mcp``) into structured per-service
configs. Also hosts the declarative ``AUTONOMOUS_SETUP_SERVICES`` registry for
tools that need no custom handler.
"""

from __future__ import annotations

from typing import Any

from ...constants import GLOBAL_SETUP_FLAGS, VALUE_FLAGS, SetupService

# ---------------------------------------------------------------------------
# Declarative registry for tools that support autonomous `<binary> setup`.
# These services do NOT need a custom _setup_* method; the generic
# _run_autonomous_setup() handles install + subprocess delegation.
#
# Keys  : service names as passed to `claude-mpm setup <service>`.
# Values:
#   binary       - the CLI binary to invoke for `<binary> setup`
#   install_spec - SetupService enum member to pass to PackageInstallerService
#                  (None means no auto-install attempt)
#   mcp_server_name - if set, _ensure_mcp_configured is called after setup
#                     (optional; leave None to skip)
# ---------------------------------------------------------------------------
AUTONOMOUS_SETUP_SERVICES: dict[str, dict] = {
    "mcp-ticketer": {
        "binary": "mcp-ticketer",
        "install_spec": SetupService.MCP_TICKETER,
        "mcp_server_name": None,
    },
    "notion-mpm": {
        "binary": "notion-mpm",
        "install_spec": SetupService.NOTION_MPM,
        "mcp_server_name": None,
    },
}


def parse_service_args(service_args: list[str]) -> dict[str, Any]:
    """
    Parse service arguments into structured service configs.

    Args:
        service_args: Raw argument list (e.g., ['slack', 'oauth', '--oauth-service', 'gworkspace-mcp'])

    Returns:
        Dict with 'services' list and 'global_options' dict
        Example: {
            'services': [
                {'name': 'slack', 'options': {}},
                {'name': 'oauth', 'options': {'oauth_service': 'gworkspace-mcp'}}
            ],
            'global_options': {'no_launch': True}
        }
    """
    if not service_args:
        return {"services": [], "global_options": {}}

    # Use enum values for valid services
    valid_services = {str(s) for s in SetupService}

    # Global flags from constants
    global_flags = {str(f) for f in GLOBAL_SETUP_FLAGS}

    # Pre-process service_args to split comma-separated values
    expanded_args = []
    for arg in service_args:
        if "," in arg:
            # Split on commas and add each part
            expanded_args.extend(
                [part.strip() for part in arg.split(",") if part.strip()]
            )
        else:
            expanded_args.append(arg)
    service_args = expanded_args

    services = []
    current_service = None
    current_options = {}
    global_options = {}

    i = 0
    while i < len(service_args):
        arg = service_args[i]

        # Check if this is a service name
        if arg in valid_services:
            # Save previous service if exists
            if current_service:
                services.append({"name": current_service, "options": current_options})

            # Start new service
            current_service = arg
            current_options = {}
            i += 1
            continue

        # Check if this is a flag
        if arg.startswith("--"):
            flag_name = arg[2:].replace("-", "_")

            # Check if this is a global flag
            if flag_name in global_flags:
                # Global flag - can be used with or without a service
                global_options[flag_name] = True
                # Also apply to current service if one exists
                if current_service:
                    current_options[flag_name] = True
                i += 1
                continue

            # Non-global flag requires a current service
            if not current_service:
                raise ValueError(
                    f"Flag {arg} found before any service name. "
                    "Flags must come after the service they apply to."
                )

            # Check if flag expects a value (using VALUE_FLAGS enum)
            value_flag_names = {str(f) for f in VALUE_FLAGS}
            if flag_name in value_flag_names:
                # Flag expects a value
                if i + 1 >= len(service_args):
                    raise ValueError(f"Flag {arg} requires a value")
                current_options[flag_name] = service_args[i + 1]
                i += 2
            else:
                # Boolean flag
                current_options[flag_name] = True
                i += 1
            continue

        # Unknown argument — treat as a plain service name string (open-world dispatch).
        # This allows new tools to be delegated without code changes.
        if current_service:
            services.append({"name": current_service, "options": current_options})
        current_service = arg
        current_options = {}
        i += 1
        continue

    # Save last service
    if current_service:
        services.append({"name": current_service, "options": current_options})

    return {"services": services, "global_options": global_options}
