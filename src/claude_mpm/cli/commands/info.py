"""
Info command implementation for claude-mpm.

WHY: This module provides system information and configuration details to help
users understand their claude-mpm setup and troubleshoot issues.
"""

import shutil
from pathlib import Path

from ...core.logger import get_logger


def show_info(args):
    """
    Show framework and configuration information.
    
    WHY: Users need to verify their installation, check dependencies, and understand
    what agents are available. This command provides a comprehensive overview of
    the claude-mpm environment.
    
    DESIGN DECISION: We check for all major components and dependencies, showing
    both what's working (✓) and what's missing (✗) to help with troubleshooting.
    
    Args:
        args: Parsed command line arguments
    """
    try:
        from ...core.framework_loader import FrameworkLoader
    except ImportError:
        from claude_mpm.core.framework_loader import FrameworkLoader
    
    print("Claude MPM - Multi-Agent Project Manager")
    print("=" * 50)
    
    # Framework info
    loader = FrameworkLoader(args.framework_path)
    if loader.framework_content["loaded"]:
        print(f"Framework: claude-multiagent-pm")
        print(f"Version: {loader.framework_content['version']}")
        print(f"Path: {loader.framework_path}")
        print(f"Agents: {', '.join(loader.get_agent_list())}")
    else:
        print("Framework: Not found (using minimal instructions)")
    
    print()
    
    # Configuration
    print("Configuration:")
    print(f"  Log directory: {args.log_dir or '~/.claude-mpm/logs'}")
    print(f"  Debug mode: {args.debug}")
    
    # Show agent hierarchy
    if loader.agent_registry:
        hierarchy = loader.agent_registry.get_agent_hierarchy()
        print("\nAgent Hierarchy:")
        print(f"  Project agents: {len(hierarchy['project'])}")
        print(f"  User agents: {len(hierarchy['user'])}")
        print(f"  System agents: {len(hierarchy['system'])}")
        
        # Show core agents
        core_agents = loader.agent_registry.get_core_agents()
        print(f"\nCore Agents: {', '.join(core_agents)}")
    
    # Check dependencies
    print("\nDependencies:")
    
    # Check Claude CLI
    claude_path = shutil.which("claude")
    if claude_path:
        print(f"  ✓ Claude CLI: {claude_path}")
    else:
        print("  ✗ Claude CLI: Not found in PATH")
    
    # Check ai-trackdown-pytools
    try:
        import ai_trackdown_pytools
        print("  ✓ ai-trackdown-pytools: Installed")
    except ImportError:
        print("  ✗ ai-trackdown-pytools: Not installed")
    
    # Check Claude Code hooks
    claude_settings = Path.home() / ".claude" / "settings.json"
    if claude_settings.exists():
        print("  ✓ Claude Code Hooks: Installed")
        print("     Use /mpm commands in Claude Code")
    else:
        print("  ✗ Claude Code Hooks: Not installed")
        print("     Run: python scripts/install_hooks.py")