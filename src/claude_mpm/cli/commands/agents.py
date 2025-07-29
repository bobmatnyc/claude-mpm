"""
Agents command implementation for claude-mpm.

WHY: This module manages Claude Code native agents, including listing, deploying,
and cleaning agent deployments.
"""

from pathlib import Path

from ...core.logger import get_logger
from ...constants import AgentCommands
from ..utils import get_agent_versions_display


def manage_agents(args):
    """
    Manage Claude Code native agents.
    
    WHY: Claude Code agents need to be deployed and managed. This command provides
    a unified interface for all agent-related operations.
    
    DESIGN DECISION: When no subcommand is provided, we show the current agent
    versions as a quick status check. This matches the behavior users see at startup.
    
    Args:
        args: Parsed command line arguments with agents_command attribute
    """
    logger = get_logger("cli")
    
    try:
        from ...services.agent_deployment import AgentDeploymentService
        deployment_service = AgentDeploymentService()
        
        if not args.agents_command:
            # No subcommand - show agent versions
            # WHY: This provides a quick way for users to check deployed agent versions
            # without needing to specify additional subcommands
            agent_versions = get_agent_versions_display()
            if agent_versions:
                print(agent_versions)
            else:
                print("No deployed agents found")
                print("\nTo deploy agents, run: claude-mpm --mpm:agents deploy")
            return
        
        if args.agents_command == AgentCommands.LIST.value:
            _list_agents(args, deployment_service)
        
        elif args.agents_command == AgentCommands.DEPLOY.value:
            _deploy_agents(args, deployment_service, force=False)
        
        elif args.agents_command == AgentCommands.FORCE_DEPLOY.value:
            _deploy_agents(args, deployment_service, force=True)
        
        elif args.agents_command == AgentCommands.CLEAN.value:
            _clean_agents(args, deployment_service)
        
    except ImportError:
        logger.error("Agent deployment service not available")
        print("Error: Agent deployment service not available")
    except Exception as e:
        logger.error(f"Error managing agents: {e}")
        print(f"Error: {e}")


def _list_agents(args, deployment_service):
    """
    List available or deployed agents.
    
    WHY: Users need to see what agents are available in the system and what's
    currently deployed. This helps them understand the agent ecosystem.
    
    Args:
        args: Command arguments with 'system' and 'deployed' flags
        deployment_service: Agent deployment service instance
    """
    if args.system:
        # List available agent templates
        print("Available Agent Templates:")
        print("-" * 80)
        agents = deployment_service.list_available_agents()
        if not agents:
            print("No agent templates found")
        else:
            for agent in agents:
                print(f"📄 {agent['file']}")
                if 'name' in agent:
                    print(f"   Name: {agent['name']}")
                if 'description' in agent:
                    print(f"   Description: {agent['description']}")
                if 'version' in agent:
                    print(f"   Version: {agent['version']}")
                print()
    
    elif args.deployed:
        # List deployed agents
        print("Deployed Agents:")
        print("-" * 80)
        verification = deployment_service.verify_deployment()
        if not verification["agents_found"]:
            print("No deployed agents found")
        else:
            for agent in verification["agents_found"]:
                print(f"📄 {agent['file']}")
                if 'name' in agent:
                    print(f"   Name: {agent['name']}")
                print(f"   Path: {agent['path']}")
                print()
        
        if verification["warnings"]:
            print("\nWarnings:")
            for warning in verification["warnings"]:
                print(f"  ⚠️  {warning}")
    
    else:
        # Default: show usage
        print("Use --system to list system agents or --deployed to list deployed agents")


def _deploy_agents(args, deployment_service, force=False):
    """
    Deploy system agents.
    
    WHY: Agents need to be deployed to the working directory for Claude Code to use them.
    This function handles both regular and forced deployment.
    
    Args:
        args: Command arguments with optional 'target' path
        deployment_service: Agent deployment service instance
        force: Whether to force rebuild all agents
    """
    if force:
        print("Force deploying all system agents...")
    else:
        print("Deploying system agents...")
    
    results = deployment_service.deploy_agents(args.target, force_rebuild=force)
    
    if results["deployed"]:
        print(f"\n✓ Successfully deployed {len(results['deployed'])} agents to {results['target_dir']}")
        for agent in results["deployed"]:
            print(f"  - {agent['name']}")
    
    if force and results.get("updated", []):
        print(f"\n✓ Updated {len(results['updated'])} agents")
        for agent in results["updated"]:
            print(f"  - {agent['name']}")
    
    if force and results.get("skipped", []):
        print(f"\n✓ Skipped {len(results['skipped'])} up-to-date agents")
    
    if results["errors"]:
        print("\n❌ Errors during deployment:")
        for error in results["errors"]:
            print(f"  - {error}")
    
    if force:
        # Set environment for force deploy
        env_vars = deployment_service.set_claude_environment(
            args.target.parent if args.target else None
        )
        print(f"\n✓ Set Claude environment variables:")
        for key, value in env_vars.items():
            print(f"  - {key}={value}")


def _clean_agents(args, deployment_service):
    """
    Clean deployed system agents.
    
    WHY: Users may want to remove deployed agents to start fresh or clean up
    their working directory.
    
    Args:
        args: Command arguments with optional 'target' path
        deployment_service: Agent deployment service instance
    """
    print("Cleaning deployed system agents...")
    results = deployment_service.clean_deployment(args.target)
    
    if results["removed"]:
        print(f"\n✓ Removed {len(results['removed'])} agents")
        for path in results["removed"]:
            print(f"  - {Path(path).name}")
    else:
        print("No system agents found to remove")
    
    if results["errors"]:
        print("\n❌ Errors during cleanup:")
        for error in results["errors"]:
            print(f"  - {error}")