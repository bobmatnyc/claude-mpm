"""
Verify command for MCP service health checks.
"""

import argparse

from ...core.logger import get_logger
from ...services.mcp_service_verifier import MCPServiceVerifier, ServiceStatus


def add_parser(subparsers) -> None:
    """Add the verify command parser."""
    parser = subparsers.add_parser(
        "verify",
        help="Verify MCP services installation and configuration",
        description="Performs comprehensive health checks on MCP services",
    )

    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to automatically fix detected issues",
    )

    parser.add_argument(
        "--service",
        type=str,
        help="Verify a specific service only",
        choices=["mcp-vector-search", "mcp-browser", "mcp-ticketer", "kuzu-memory"],
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format",
    )

    parser.set_defaults(func=handle_verify)


def handle_verify(args: argparse.Namespace) -> int:
    """
    Handle the verify command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success, non-zero for issues found)
    """
    logger = get_logger(__name__)
    verifier = MCPServiceVerifier()

    try:
        # Run verification
        if args.service:
            # Verify single service
            logger.info(f"Verifying {args.service}...")
            diagnostic = verifier._verify_service(args.service)
            diagnostics = {args.service: diagnostic}

            # Auto-fix if requested
            if (
                args.fix
                and diagnostic.fix_command
                and diagnostic.status != ServiceStatus.WORKING
            ):
                logger.info(f"Attempting to fix {args.service}...")
                if verifier._attempt_auto_fix(args.service, diagnostic):
                    # Re-verify after fix
                    diagnostic = verifier._verify_service(args.service)
                    diagnostics = {args.service: diagnostic}
        else:
            # Verify all services
            logger.info("Verifying all MCP services...")
            diagnostics = verifier.verify_all_services(auto_fix=args.fix)

        # Output results
        if args.json:
            import json

            # Convert to JSON-serializable format
            json_output = {}
            for name, diag in diagnostics.items():
                json_output[name] = {
                    "status": diag.status.value,
                    "message": diag.message,
                    "installed_path": diag.installed_path,
                    "configured_command": diag.configured_command,
                    "fix_command": diag.fix_command,
                    "details": diag.details,
                }
            print(json.dumps(json_output, indent=2))
        else:
            verifier.print_diagnostics(diagnostics)

        # Determine exit code
        all_working = all(
            d.status == ServiceStatus.WORKING for d in diagnostics.values()
        )

        if all_working:
            logger.info("✅ All verified services are fully operational")
            return 0
        issues_count = sum(
            1 for d in diagnostics.values() if d.status != ServiceStatus.WORKING
        )
        logger.warning(f"⚠️ {issues_count} service(s) have issues")
        return 1

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        if args.json:
            import json

            print(json.dumps({"error": str(e)}, indent=2))
        else:
            print(f"\n❌ Verification failed: {e}")
        return 2
