"""Version information for claude-mpm."""

try:
    # Try to get version from setuptools-scm (when installed as package)
    from importlib.metadata import version, PackageNotFoundError
    try:
        __version__ = version("claude-mpm")
    except PackageNotFoundError:
        __version__ = "2.0.0"
except ImportError:
    # Fallback for older Python versions
    __version__ = "2.0.0"

# This file may be overwritten by setuptools-scm during build
# The try/except ensures we always have a version available

def get_version_tuple():
    """Get version as a tuple of integers."""
    parts = __version__.split(".")[:3]  # Take only major.minor.patch
    try:
        return tuple(int(p) for p in parts if p.isdigit())
    except:
        return (1, 0, 0)

__version_info__ = get_version_tuple()

# Version history
# 2.0.0 - BREAKING: Complete agent schema standardization, JSON format, resource tiers
# 1.1.0 - BREAKING: Removed JSON-RPC hooks, enhanced Claude Code hooks with project-specific logging
# 1.0.0 - BREAKING: Architecture simplification, TodoWrite hooks, enhanced CLI, terminal UI
# 0.5.0 - Comprehensive deployment support for PyPI, npm, and local installation
# 0.3.0 - Added hook service architecture for context filtering and ticket automation
# 0.2.0 - Initial interactive subprocess orchestration with pexpect
# 0.1.0 - Basic claude-mpm framework with agent orchestration