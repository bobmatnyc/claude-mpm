"""
Agents command implementation for claude-mpm.

WHY: This module manages Claude Code native agents, including listing, deploying,
and cleaning agent deployments.
"""

from pathlib import Path
import json
import yaml
from typing import Dict, Any, Optional

from ...core.logger import get_logger
from ...constants import AgentCommands
from ..utils import get_agent_versions_display
from ...core.agent_registry import AgentRegistryAdapter
from ...agents.frontmatter_validator import FrontmatterValidator


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
        from ...services import AgentDeploymentService
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
        
        elif args.agents_command == AgentCommands.VIEW.value:
            _view_agent(args)
        
        elif args.agents_command == AgentCommands.FIX.value:
            _fix_agents(args)
        
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
        args: Command arguments with 'system', 'deployed', and 'by_tier' flags
        deployment_service: Agent deployment service instance
    """
    if hasattr(args, 'by_tier') and args.by_tier:
        # List agents grouped by tier
        _list_agents_by_tier()
    elif args.system:
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
        print("Use --system to list system agents, --deployed to list deployed agents, or --by-tier to group by precedence")


def _deploy_agents(args, deployment_service, force=False):
    """
    Deploy both system and project agents.
    
    WHY: Agents need to be deployed to the working directory for Claude Code to use them.
    This function handles both regular and forced deployment, including project-specific agents.
    
    Args:
        args: Command arguments with optional 'target' path
        deployment_service: Agent deployment service instance
        force: Whether to force rebuild all agents
    """
    # Deploy system agents first
    if force:
        print("Force deploying all system agents...")
    else:
        print("Deploying system agents...")
    
    results = deployment_service.deploy_agents(args.target, force_rebuild=force)
    
    # Also deploy project agents if they exist
    from pathlib import Path
    project_agents_dir = Path.cwd() / '.claude-mpm' / 'agents'
    if project_agents_dir.exists():
        json_files = list(project_agents_dir.glob('*.json'))
        if json_files:
            print(f"\nDeploying {len(json_files)} project agents...")
            from claude_mpm.services.agents.deployment.agent_deployment import AgentDeploymentService
            project_service = AgentDeploymentService(
                templates_dir=project_agents_dir,
                base_agent_path=project_agents_dir / 'base_agent.json' if (project_agents_dir / 'base_agent.json').exists() else None
            )
            project_results = project_service.deploy_agents(
                target_dir=args.target if args.target else Path.cwd() / '.claude' / 'agents',
                force_rebuild=force,
                deployment_mode='project'
            )
            
            # Merge project results into main results
            if project_results.get('deployed'):
                results['deployed'].extend(project_results['deployed'])
                print(f"✓ Deployed {len(project_results['deployed'])} project agents")
            if project_results.get('updated'):
                results['updated'].extend(project_results['updated'])
                print(f"✓ Updated {len(project_results['updated'])} project agents")
            if project_results.get('errors'):
                results['errors'].extend(project_results['errors'])
    
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


def _list_agents_by_tier():
    """
    List agents grouped by precedence tier.
    
    WHY: Users need to understand which agents are active across different tiers
    and which version takes precedence when multiple versions exist.
    """
    try:
        adapter = AgentRegistryAdapter()
        if not adapter.registry:
            print("❌ Could not initialize agent registry")
            return
        
        # Get all agents and group by tier
        all_agents = adapter.registry.list_agents()
        
        # Group agents by tier and name
        tiers = {'project': {}, 'user': {}, 'system': {}}
        agent_names = set()
        
        for agent_id, metadata in all_agents.items():
            tier = metadata.get('tier', 'system')
            if tier in tiers:
                tiers[tier][agent_id] = metadata
                agent_names.add(agent_id)
        
        # Display header
        print("\n" + "=" * 80)
        print(" " * 25 + "AGENT HIERARCHY BY TIER")
        print("=" * 80)
        print("\nPrecedence: PROJECT > USER > SYSTEM")
        print("(Agents in higher tiers override those in lower tiers)\n")
        
        # Display each tier
        tier_order = [('PROJECT', 'project'), ('USER', 'user'), ('SYSTEM', 'system')]
        
        for tier_display, tier_key in tier_order:
            agents = tiers[tier_key]
            print(f"\n{'─' * 35} {tier_display} TIER {'─' * 35}")
            
            if not agents:
                print(f"  No agents at {tier_key} level")
            else:
                # Check paths to determine actual locations
                if tier_key == 'project':
                    print(f"  Location: .claude-mpm/agents/ (in current project)")
                elif tier_key == 'user':
                    print(f"  Location: ~/.claude-mpm/agents/")
                else:
                    print(f"  Location: Built-in framework agents")
                
                print(f"\n  Found {len(agents)} agent(s):\n")
                
                for agent_id, metadata in sorted(agents.items()):
                    # Check if this agent is overridden by higher tiers
                    is_active = True
                    overridden_by = []
                    
                    for check_tier_display, check_tier_key in tier_order:
                        if check_tier_key == tier_key:
                            break
                        if agent_id in tiers[check_tier_key]:
                            is_active = False
                            overridden_by.append(check_tier_display)
                    
                    # Display agent info
                    status = "✓ ACTIVE" if is_active else f"⊗ OVERRIDDEN by {', '.join(overridden_by)}"
                    print(f"    📄 {agent_id:<20} [{status}]")
                    
                    # Show metadata
                    if 'description' in metadata:
                        print(f"       Description: {metadata['description']}")
                    if 'path' in metadata:
                        path = Path(metadata['path'])
                        print(f"       File: {path.name}")
                    print()
        
        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY:")
        print(f"  Total unique agents: {len(agent_names)}")
        print(f"  Project agents: {len(tiers['project'])}")
        print(f"  User agents: {len(tiers['user'])}")
        print(f"  System agents: {len(tiers['system'])}")
        print("=" * 80 + "\n")
        
    except Exception as e:
        print(f"❌ Error listing agents by tier: {e}")


def _view_agent(args):
    """
    View detailed information about a specific agent.
    
    WHY: Users need to inspect agent configurations, frontmatter, and instructions
    to understand what an agent does and how it's configured.
    
    Args:
        args: Command arguments with 'agent_name' attribute
    """
    if not hasattr(args, 'agent_name') or not args.agent_name:
        print("❌ Please specify an agent name to view")
        print("Usage: claude-mpm agents view <agent_name>")
        return
    
    try:
        adapter = AgentRegistryAdapter()
        if not adapter.registry:
            print("❌ Could not initialize agent registry")
            return
        
        # Get the agent
        agent = adapter.registry.get_agent(args.agent_name)
        if not agent:
            print(f"❌ Agent '{args.agent_name}' not found")
            print("\nAvailable agents:")
            all_agents = adapter.registry.list_agents()
            for agent_id in sorted(all_agents.keys()):
                print(f"  - {agent_id}")
            return
        
        # Read the agent file
        agent_path = Path(agent.path)
        if not agent_path.exists():
            print(f"❌ Agent file not found: {agent_path}")
            return
        
        with open(agent_path, 'r') as f:
            content = f.read()
        
        # Display agent information
        print("\n" + "=" * 80)
        print(f" AGENT: {agent.name}")
        print("=" * 80)
        
        # Basic info
        print(f"\n📋 BASIC INFORMATION:")
        print(f"  Name: {agent.name}")
        print(f"  Type: {agent.type}")
        print(f"  Tier: {agent.tier.upper()}")
        print(f"  Path: {agent_path}")
        if agent.description:
            print(f"  Description: {agent.description}")
        if agent.specializations:
            print(f"  Specializations: {', '.join(agent.specializations)}")
        
        # Extract and display frontmatter
        if content.startswith("---"):
            try:
                end_marker = content.find("\n---\n", 4)
                if end_marker == -1:
                    end_marker = content.find("\n---\r\n", 4)
                
                if end_marker != -1:
                    frontmatter_str = content[4:end_marker]
                    frontmatter = yaml.safe_load(frontmatter_str)
                    
                    print(f"\n📝 FRONTMATTER:")
                    for key, value in frontmatter.items():
                        if isinstance(value, list):
                            print(f"  {key}: [{', '.join(str(v) for v in value)}]")
                        elif isinstance(value, dict):
                            print(f"  {key}:")
                            for k, v in value.items():
                                print(f"    {k}: {v}")
                        else:
                            print(f"  {key}: {value}")
                    
                    # Extract instructions preview
                    instructions_start = end_marker + 5
                    instructions = content[instructions_start:].strip()
                    
                    if instructions:
                        print(f"\n📖 INSTRUCTIONS PREVIEW (first 500 chars):")
                        print("  " + "-" * 76)
                        preview = instructions[:500]
                        if len(instructions) > 500:
                            preview += "...\n\n  [Truncated - {:.1f}KB total]".format(len(instructions) / 1024)
                        
                        for line in preview.split('\n'):
                            print(f"  {line}")
                        print("  " + "-" * 76)
            except Exception as e:
                print(f"\n⚠️  Could not parse frontmatter: {e}")
        else:
            print(f"\n⚠️  No frontmatter found in agent file")
        
        # File stats
        import os
        stat = os.stat(agent_path)
        from datetime import datetime
        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        print(f"\n📊 FILE STATS:")
        print(f"  Size: {stat.st_size:,} bytes")
        print(f"  Last modified: {modified}")
        
        print("\n" + "=" * 80 + "\n")
        
    except Exception as e:
        print(f"❌ Error viewing agent: {e}")


def _fix_agents(args):
    """
    Fix agent frontmatter issues using FrontmatterValidator.
    
    WHY: Agent files may have formatting issues in their frontmatter that prevent
    proper loading. This command automatically fixes common issues.
    
    Args:
        args: Command arguments with 'agent_name', 'dry_run', and 'all' flags
    """
    validator = FrontmatterValidator()
    
    try:
        adapter = AgentRegistryAdapter()
        if not adapter.registry:
            print("❌ Could not initialize agent registry")
            return
        
        # Determine which agents to fix
        agents_to_fix = []
        
        if hasattr(args, 'all') and args.all:
            # Fix all agents
            all_agents = adapter.registry.list_agents()
            for agent_id, metadata in all_agents.items():
                agents_to_fix.append((agent_id, metadata['path']))
            print(f"\n🔧 Checking {len(agents_to_fix)} agent(s) for frontmatter issues...\n")
        elif hasattr(args, 'agent_name') and args.agent_name:
            # Fix specific agent
            agent = adapter.registry.get_agent(args.agent_name)
            if not agent:
                print(f"❌ Agent '{args.agent_name}' not found")
                return
            agents_to_fix.append((agent.name, agent.path))
            print(f"\n🔧 Checking agent '{agent.name}' for frontmatter issues...\n")
        else:
            print("❌ Please specify an agent name or use --all to fix all agents")
            print("Usage: claude-mpm agents fix [agent_name] [--dry-run] [--all]")
            return
        
        dry_run = hasattr(args, 'dry_run') and args.dry_run
        if dry_run:
            print("🔍 DRY RUN MODE - No changes will be made\n")
        
        # Process each agent
        total_issues = 0
        total_fixed = 0
        
        for agent_name, agent_path in agents_to_fix:
            path = Path(agent_path)
            if not path.exists():
                print(f"⚠️  Skipping {agent_name}: File not found at {path}")
                continue
            
            print(f"📄 {agent_name}:")
            
            # Validate and potentially fix
            result = validator.correct_file(path, dry_run=dry_run)
            
            if result.is_valid and not result.corrections:
                print("  ✓ No issues found")
            else:
                if result.errors:
                    print("  ❌ Errors:")
                    for error in result.errors:
                        print(f"    - {error}")
                    total_issues += len(result.errors)
                
                if result.warnings:
                    print("  ⚠️  Warnings:")
                    for warning in result.warnings:
                        print(f"    - {warning}")
                    total_issues += len(result.warnings)
                
                if result.corrections:
                    if dry_run:
                        print("  🔧 Would fix:")
                    else:
                        print("  ✓ Fixed:")
                        total_fixed += len(result.corrections)
                    for correction in result.corrections:
                        print(f"    - {correction}")
            
            print()
        
        # Summary
        print("=" * 80)
        print("SUMMARY:")
        print(f"  Agents checked: {len(agents_to_fix)}")
        print(f"  Total issues found: {total_issues}")
        if dry_run:
            print(f"  Issues that would be fixed: {sum(1 for _, path in agents_to_fix if validator.validate_file(Path(path)).corrections)}")
            print("\n💡 Run without --dry-run to apply fixes")
        else:
            print(f"  Issues fixed: {total_fixed}")
            if total_fixed > 0:
                print("\n✓ Frontmatter issues have been fixed!")
        print("=" * 80 + "\n")
        
    except Exception as e:
        print(f"❌ Error fixing agents: {e}")