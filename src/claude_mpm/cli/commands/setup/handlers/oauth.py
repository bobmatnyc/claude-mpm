"""Thin delegator for ``claude-mpm setup oauth --oauth-service ...``."""

from __future__ import annotations

from ....shared import CommandResult


class OAuthMixin:
    """Mixin: delegates to ``claude-mpm oauth setup``."""

    def _setup_oauth(self, args) -> CommandResult:
        """Set up OAuth for a service (delegates to OAuth command)."""
        # Get service name from arguments
        service_name = getattr(args, "oauth_service", None)
        if not service_name:
            return CommandResult.error_result(
                "OAuth setup requires --oauth-service flag. "
                "Example: claude-mpm setup oauth --oauth-service gworkspace-mcp"
            )

        # Delegate to OAuth setup
        from argparse import Namespace

        from ...oauth import manage_oauth

        oauth_args = Namespace(
            oauth_command="setup",
            service_name=service_name,
            no_browser=getattr(args, "no_browser", False),
            no_launch=getattr(args, "no_launch", False),
            force=getattr(args, "force", False),
        )

        exit_code = manage_oauth(oauth_args)
        return CommandResult(
            success=exit_code == 0,
            exit_code=exit_code,
            message=f"OAuth setup for {service_name}",
        )
