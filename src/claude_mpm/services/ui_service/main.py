"""Entry point for the claude-mpm UI Service.

Run via:
    claude-mpm-ui
or:
    python -m claude_mpm.services.ui_service.main
"""

import logging

logger = logging.getLogger(__name__)


def main() -> None:
    """Start the UI Service using uvicorn.

    Configuration is read from environment variables (CLAUDE_MPM_UI_* prefix).
    """
    # Guard must be called before uvicorn.run() because uvicorn's reloader
    # (reload=True) and multi-worker mode (workers=N) use multiprocessing
    # internally.  On macOS, forking from a multithreaded parent and then
    # calling CoreFoundation / os_log in the child raises EXC_BAD_ACCESS.
    # Setting the default start method to "spawn" on Darwin avoids the crash.
    from claude_mpm.mcp.fork_safety import ensure_spawn_on_darwin

    ensure_spawn_on_darwin()

    import uvicorn

    from claude_mpm.services.ui_service.config import UIServiceConfig

    config = UIServiceConfig.from_env()

    logging.basicConfig(level=getattr(logging, config.log_level.upper(), logging.INFO))
    logger.info("Starting claude-mpm UI Service on %s:%s", config.host, config.port)

    uvicorn.run(
        "claude_mpm.services.ui_service.app:create_app",
        factory=True,
        host=config.host,
        port=config.port,
        reload=config.reload,
        log_level=config.log_level,
    )


if __name__ == "__main__":
    main()
