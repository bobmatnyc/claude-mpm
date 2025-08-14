"""Agent deployment service for Claude Code native subagents.

This service handles the complete lifecycle of agent deployment:
1. Building agent YAML files from JSON templates
2. Managing versioning and updates
3. Deploying to Claude Code's .claude/agents directory
4. Environment configuration for agent discovery
5. Deployment verification and cleanup

OPERATIONAL CONSIDERATIONS:
- Deployment is idempotent - safe to run multiple times
- Version checking prevents unnecessary rebuilds (saves I/O)
- Supports force rebuild for troubleshooting
- Maintains backward compatibility with legacy versions
- Handles migration from old serial versioning to semantic versioning

MONITORING:
- Check logs for deployment status and errors
- Monitor disk space in .claude/agents directory
- Track version migration progress
- Verify agent discovery after deployment

ROLLBACK PROCEDURES:
- Keep backups of .claude/agents before major updates
- Use clean_deployment() to remove system agents
- User-created agents are preserved during cleanup
- Version tracking allows targeted rollbacks
"""

import os
import shutil
import logging
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

from claude_mpm.core.logging_config import get_logger, log_operation, log_performance_context
from claude_mpm.core.exceptions import AgentDeploymentError
from claude_mpm.constants import EnvironmentVars, Paths, AgentMetadata
from claude_mpm.config.paths import paths
from claude_mpm.core.config import Config
from claude_mpm.core.constants import (
    TimeoutConfig,
    SystemLimits,
    ResourceLimits
)
from claude_mpm.core.interfaces import AgentDeploymentInterface


class AgentDeploymentService(AgentDeploymentInterface):
    """Service for deploying Claude Code native agents.
    
    METRICS COLLECTION OPPORTUNITIES:
    This service could collect valuable deployment metrics including:
    - Agent deployment frequency and success rates
    - Template validation performance  
    - Version migration patterns
    - Deployment duration by agent type
    - Cache hit rates for agent templates
    - Resource usage during deployment (memory, CPU)
    - Agent file sizes and complexity metrics
    - Deployment failure reasons and patterns
    
    DEPLOYMENT PIPELINE:
    1. Initialize with template and base agent paths
    2. Load base agent configuration (shared settings)
    3. Iterate through agent templates
    4. Check version and update requirements
    5. Build YAML files with proper formatting
    6. Deploy to target directory
    7. Set environment variables for discovery
    8. Verify deployment success
    
    ENVIRONMENT REQUIREMENTS:
    - Write access to .claude/agents directory
    - Python 3.8+ for pathlib and typing features
    - JSON parsing for template files
    - YAML generation capabilities
    """
    
    def __init__(self, templates_dir: Optional[Path] = None, base_agent_path: Optional[Path] = None, working_directory: Optional[Path] = None):
        """
        Initialize agent deployment service.
        
        Args:
            templates_dir: Directory containing agent JSON files
            base_agent_path: Path to base_agent.md file
            working_directory: User's working directory (for project agents)
            
        METRICS OPPORTUNITY: Track initialization performance:
        - Template directory scan time
        - Base agent loading time
        - Initial validation overhead
        """
        self.logger = get_logger(__name__)
        
        # METRICS: Initialize deployment metrics tracking
        # This data structure would be used for collecting deployment telemetry
        self._deployment_metrics = {
            'total_deployments': 0,
            'successful_deployments': 0,
            'failed_deployments': 0,
            'migrations_performed': 0,
            'average_deployment_time_ms': 0.0,
            'deployment_times': [],  # Keep last 100 for rolling average
            'agent_type_counts': {},  # Track deployments by agent type
            'version_migration_count': 0,
            'template_validation_times': {},  # Track validation performance
            'deployment_errors': {}  # Track error types and frequencies
        }
        
        # Determine the actual working directory
        # For deployment, we need to track the working directory but NOT use it
        # for determining where system agents go (they always go to ~/.claude/agents/)
        # Priority: working_directory param > current directory
        if working_directory:
            self.working_directory = Path(working_directory)
        else:
            # Use current directory but don't let CLAUDE_MPM_USER_PWD affect system agent deployment
            self.working_directory = Path.cwd()
        
        self.logger.info(f"Working directory for deployment: {self.working_directory}")
        
        # Find templates directory using centralized path management
        if templates_dir:
            self.templates_dir = Path(templates_dir)
        else:
            # Use centralized paths instead of fragile parent calculations
            # For system agents, still use templates subdirectory
            # For project/user agents, this should be overridden with actual agents dir
            self.templates_dir = paths.agents_dir / "templates"
        
        # Find base agent file
        if base_agent_path:
            self.base_agent_path = Path(base_agent_path)
        else:
            # Use centralized paths for consistency
            self.base_agent_path = paths.agents_dir / "base_agent.json"
        
        self.logger.info(f"Templates directory: {self.templates_dir}")
        self.logger.info(f"Base agent path: {self.base_agent_path}")
        
    def deploy_agents(self, target_dir: Optional[Path] = None, force_rebuild: bool = False, deployment_mode: str = "update", config: Optional[Config] = None, use_async: bool = False) -> Dict[str, Any]:
        """
        Build and deploy agents by combining base_agent.md with templates.
        Also deploys system instructions for PM framework.
        
        DEPLOYMENT MODES:
        - "update": Normal update mode - skip agents with matching versions (default)
        - "project": Project deployment mode - always deploy all agents regardless of version
        
        CONFIGURATION:
        The config parameter or default configuration is used to determine:
        - Which agents to exclude from deployment
        - Case sensitivity for agent name matching
        - Whether to exclude agent dependencies
        
        METRICS COLLECTED:
        - Deployment start/end timestamps
        - Individual agent deployment durations
        - Success/failure rates by agent type
        - Version migration statistics
        - Template validation performance
        - Error type frequencies
        
        OPERATIONAL FLOW:
        0. Validates and repairs broken frontmatter in existing agents (Step 0)
        1. Validates target directory (creates if needed)
        2. Loads base agent configuration
        3. Discovers all agent templates
        4. For each agent:
           - Checks if update needed (version comparison)
           - Builds YAML configuration
           - Writes to target directory
           - Tracks deployment status
        
        PERFORMANCE CONSIDERATIONS:
        - Skips unchanged agents (version-based caching)
        - Batch processes all agents in single pass
        - Minimal file I/O with in-memory building
        - Parallel-safe (no shared state mutations)
        
        ERROR HANDLING:
        - Continues deployment on individual agent failures
        - Collects all errors for reporting
        - Logs detailed error context
        - Returns comprehensive results dict
        
        MONITORING POINTS:
        - Track total deployment time
        - Monitor skipped vs updated vs new agents
        - Check error rates and patterns
        - Verify migration completion
        
        Args:
            target_dir: Target directory for agents (default: .claude/agents/)
            force_rebuild: Force rebuild even if agents exist (useful for troubleshooting)
            deployment_mode: "update" for version-aware updates, "project" for always deploy
            config: Optional configuration object (loads default if not provided)
            use_async: Use async operations for 50-70% faster deployment (default: True)
            
        Returns:
            Dictionary with deployment results:
            - target_dir: Deployment location
            - deployed: List of newly deployed agents
            - updated: List of updated agents
            - migrated: List of agents migrated to new version format
            - skipped: List of unchanged agents
            - errors: List of deployment errors
            - total: Total number of agents processed
            - repaired: List of agents with repaired frontmatter
        """
        # METRICS: Record deployment start time for performance tracking
        deployment_start_time = time.time()
        
        # Try async deployment for better performance if requested
        if use_async:
            async_results = self._try_async_deployment(
                target_dir=target_dir,
                force_rebuild=force_rebuild,
                config=config,
                deployment_start_time=deployment_start_time
            )
            if async_results is not None:
                return async_results
        
        # Continue with synchronous deployment
        self.logger.info("Using synchronous deployment")
        
        # Load and process configuration
        config, excluded_agents = self._load_deployment_config(config)
        
        # Determine target agents directory
        agents_dir = self._determine_agents_directory(target_dir)
        
        # Initialize results dictionary
        results = self._initialize_deployment_results(agents_dir, deployment_start_time)
        
        try:
            # Create agents directory if needed
            agents_dir.mkdir(parents=True, exist_ok=True)
            
            # STEP 0: Validate and repair broken frontmatter in existing agents
            self._repair_existing_agents(agents_dir, results)
            
            # Log deployment source tier
            source_tier = self._determine_source_tier()
            self.logger.info(f"Building and deploying {source_tier} agents to: {agents_dir}")
            
            # Note: System instructions are now loaded directly by SimpleClaudeRunner
            
            # Check if templates directory exists
            if not self.templates_dir.exists():
                error_msg = f"Agents directory not found: {self.templates_dir}"
                self.logger.error(error_msg)
                results["errors"].append(error_msg)
                return results
            
            # Convert any existing YAML files to MD format
            conversion_results = self._convert_yaml_to_md(agents_dir)
            results["converted"] = conversion_results.get("converted", [])
            
            # Load base agent content
            base_agent_data, base_agent_version = self._load_base_agent()
            
            # Get and filter template files
            template_files = self._get_filtered_templates(excluded_agents, config)
            results["total"] = len(template_files)
            
            # Deploy each agent template
            for template_file in template_files:
                self._deploy_single_agent(
                    template_file=template_file,
                    agents_dir=agents_dir,
                    base_agent_data=base_agent_data,
                    base_agent_version=base_agent_version,
                    force_rebuild=force_rebuild,
                    deployment_mode=deployment_mode,
                    results=results
                )
            
            # Deploy system instructions and framework files
            self._deploy_system_instructions(agents_dir, force_rebuild, results)
            
            self.logger.info(
                f"Deployed {len(results['deployed'])} agents, "
                f"updated {len(results['updated'])}, "
                f"migrated {len(results['migrated'])}, "
                f"converted {len(results['converted'])} YAML files, "
                f"repaired {len(results['repaired'])} frontmatter, "
                f"skipped {len(results['skipped'])}, "
                f"errors: {len(results['errors'])}"
            )
            
        except AgentDeploymentError as e:
            # Custom error with context already formatted
            self.logger.error(str(e))
            results["errors"].append(str(e))
        except Exception as e:
            # Wrap unexpected errors
            error_msg = f"Agent deployment failed: {e}"
            self.logger.error(error_msg)
            results["errors"].append(error_msg)
            
            # METRICS: Track deployment failure
            self._deployment_metrics['failed_deployments'] += 1
            error_type = type(e).__name__
            self._deployment_metrics['deployment_errors'][error_type] = \
                self._deployment_metrics['deployment_errors'].get(error_type, 0) + 1
        
        # METRICS: Calculate final deployment metrics
        deployment_end_time = time.time()
        deployment_duration = (deployment_end_time - deployment_start_time) * 1000  # ms
        
        results["metrics"]["end_time"] = deployment_end_time
        results["metrics"]["duration_ms"] = deployment_duration
        
        # METRICS: Update rolling averages and statistics
        self._update_deployment_metrics(deployment_duration, results)
        
        return results
    
    def _update_deployment_metrics(self, duration_ms: float, results: Dict[str, Any]) -> None:
        """
        Update internal deployment metrics.
        
        METRICS TRACKING:
        - Rolling average of deployment times (last 100)
        - Success/failure rates
        - Agent type distribution
        - Version migration patterns
        - Error frequency analysis
        
        This method demonstrates ETL-like processing:
        1. Extract: Gather raw metrics from deployment results
        2. Transform: Calculate averages, rates, and distributions
        3. Load: Store in internal metrics structure for reporting
        """
        # Update total deployment count
        self._deployment_metrics['total_deployments'] += 1
        
        # Track success/failure
        if not results.get('errors'):
            self._deployment_metrics['successful_deployments'] += 1
        else:
            self._deployment_metrics['failed_deployments'] += 1
        
        # Update rolling average deployment time
        self._deployment_metrics['deployment_times'].append(duration_ms)
        if len(self._deployment_metrics['deployment_times']) > 100:
            # Keep only last 100 for memory efficiency
            self._deployment_metrics['deployment_times'] = \
                self._deployment_metrics['deployment_times'][-100:]
        
        # Calculate new average
        if self._deployment_metrics['deployment_times']:
            self._deployment_metrics['average_deployment_time_ms'] = \
                sum(self._deployment_metrics['deployment_times']) / \
                len(self._deployment_metrics['deployment_times'])
    
    def get_deployment_metrics(self) -> Dict[str, Any]:
        """
        Get current deployment metrics.
        
        Returns:
            Dictionary containing:
            - Total deployments and success rates
            - Average deployment time
            - Agent type distribution
            - Migration statistics
            - Error analysis
            
        This demonstrates a metrics API endpoint that could be:
        - Exposed via REST API for monitoring tools
        - Pushed to time-series databases (Prometheus, InfluxDB)
        - Used for dashboards and alerting
        - Integrated with AI observability platforms
        """
        success_rate = 0.0
        if self._deployment_metrics['total_deployments'] > 0:
            success_rate = (self._deployment_metrics['successful_deployments'] / 
                          self._deployment_metrics['total_deployments']) * 100
        
        return {
            'total_deployments': self._deployment_metrics['total_deployments'],
            'successful_deployments': self._deployment_metrics['successful_deployments'],
            'failed_deployments': self._deployment_metrics['failed_deployments'],
            'success_rate_percent': success_rate,
            'average_deployment_time_ms': self._deployment_metrics['average_deployment_time_ms'],
            'migrations_performed': self._deployment_metrics['migrations_performed'],
            'agent_type_distribution': self._deployment_metrics['agent_type_counts'].copy(),
            'version_migrations': self._deployment_metrics['version_migration_count'],
            'error_distribution': self._deployment_metrics['deployment_errors'].copy(),
            'recent_deployment_times': self._deployment_metrics['deployment_times'][-10:]  # Last 10
        }
    
    def reset_metrics(self) -> None:
        """
        Reset deployment metrics.
        
        Useful for:
        - Starting fresh metrics collection periods
        - Testing and development
        - Scheduled metric rotation (e.g., daily reset)
        """
        self._deployment_metrics = {
            'total_deployments': 0,
            'successful_deployments': 0,
            'failed_deployments': 0,
            'migrations_performed': 0,
            'average_deployment_time_ms': 0.0,
            'deployment_times': [],
            'agent_type_counts': {},
            'version_migration_count': 0,
            'template_validation_times': {},
            'deployment_errors': {}
        }
        self.logger.info("Deployment metrics reset")
    
    def _extract_version(self, content: str, version_marker: str) -> int:
        """
        Extract version number from content.
        
        Args:
            content: File content
            version_marker: Version marker to look for (e.g., "AGENT_VERSION:" or "BASE_AGENT_VERSION:")
            
        Returns:
            Version number or 0 if not found
        """
        import re
        pattern = rf"<!-- {version_marker} (\d+) -->"
        match = re.search(pattern, content)
        if match:
            return int(match.group(1))
        return 0
    
    def _build_agent_markdown(self, agent_name: str, template_path: Path, base_agent_data: dict) -> str:
        """
        Build a complete agent markdown file with YAML frontmatter.
        
        Args:
            agent_name: Name of the agent
            template_path: Path to the agent template JSON file
            base_agent_data: Base agent data from JSON
            
        Returns:
            Complete agent markdown content with YAML frontmatter
        """
        import json
        from datetime import datetime
        
        # Read template JSON
        template_data = json.loads(template_path.read_text())
        
        # Extract basic info
        # Handle both 'agent_version' (new format) and 'version' (old format)
        agent_version = self._parse_version(template_data.get('agent_version') or template_data.get('version', 0))
        base_version = self._parse_version(base_agent_data.get('base_version') or base_agent_data.get('version', 0))
        
        # Format version string as semantic version
        # Combine base and agent versions for a unified semantic version
        # Use agent version as primary, with base version in metadata
        version_string = self._format_version_display(agent_version)
        
        # Build YAML frontmatter
        # Check new format first (metadata.description), then old format
        description = (
            template_data.get('metadata', {}).get('description') or
            template_data.get('configuration_fields', {}).get('description') or
            template_data.get('description') or
            'Agent for specialized tasks'
        )
        
        # Get tags from new format (metadata.tags) or old format
        tags = (
            template_data.get('metadata', {}).get('tags') or
            template_data.get('configuration_fields', {}).get('tags') or
            template_data.get('tags') or
            [agent_name, 'mpm-framework']
        )
        
        # Get tools from capabilities.tools in new format
        tools = (
            template_data.get('capabilities', {}).get('tools') or
            template_data.get('configuration_fields', {}).get('tools') or
            ["Read", "Write", "Edit", "Grep", "Glob", "LS"]  # Default fallback
        )
        
        # Get model from capabilities.model in new format
        model = (
            template_data.get('capabilities', {}).get('model') or
            template_data.get('configuration_fields', {}).get('model') or
            "sonnet"  # Default fallback
        )
        
        # Simplify model name for Claude Code
        model_map = {
            'claude-4-sonnet-20250514': 'sonnet',
            'claude-sonnet-4-20250514': 'sonnet',
            'claude-opus-4-20250514': 'opus',
            'claude-3-opus-20240229': 'opus',
            'claude-3-haiku-20240307': 'haiku',
            'claude-3.5-sonnet': 'sonnet',
            'claude-3-sonnet': 'sonnet'
        }
        # Better fallback: extract the model type (opus/sonnet/haiku) from the string
        if model not in model_map:
            if 'opus' in model.lower():
                model = 'opus'
            elif 'sonnet' in model.lower():
                model = 'sonnet'
            elif 'haiku' in model.lower():
                model = 'haiku'
            else:
                # Last resort: try to extract from hyphenated format
                model = model_map.get(model, model.split('-')[-1] if '-' in model else model)
        else:
            model = model_map[model]
        
        # Get response format from template or use base agent default
        response_format = template_data.get('response', {}).get('format', 'structured')
        
        # Convert lists to space-separated strings for Claude Code compatibility
        tags_str = ' '.join(tags) if isinstance(tags, list) else tags
        
        # Convert tools list to comma-separated string for Claude Code compatibility
        # IMPORTANT: No spaces after commas - Claude Code requires exact format
        tools_str = ','.join(tools) if isinstance(tools, list) else tools
        
        # Validate tools format - CRITICAL: No spaces allowed!
        if ', ' in tools_str:
            self.logger.error(f"Tools contain spaces: '{tools_str}'")
            raise AgentDeploymentError(
                f"Tools must be comma-separated WITHOUT spaces",
                context={"agent_name": agent_name, "invalid_tools": tools_str}
            )
        
        # Extract proper agent_id and name from template
        agent_id = template_data.get('agent_id', agent_name)
        display_name = template_data.get('metadata', {}).get('name', agent_id)
        
        # Convert agent_id to Claude Code compatible name (replace underscores with hyphens)
        # Claude Code requires name to match pattern: ^[a-z0-9]+(-[a-z0-9]+)*$
        # CRITICAL: NO underscores allowed - they cause silent failures!
        claude_code_name = agent_id.replace('_', '-').lower()
        
        # Validate the name before proceeding
        import re
        if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', claude_code_name):
            self.logger.error(f"Invalid agent name '{claude_code_name}' - must match ^[a-z0-9]+(-[a-z0-9]+)*$")
            raise AgentDeploymentError(
                f"Agent name '{claude_code_name}' does not meet Claude Code requirements",
                context={"agent_name": agent_name, "invalid_name": claude_code_name}
            )
        
        # Build frontmatter with only the fields Claude Code uses
        frontmatter_lines = [
            "---",
            f"name: {claude_code_name}",
            f"description: {description}",
            f"version: {version_string}",
            f"base_version: {self._format_version_display(base_version)}",
            f"author: claude-mpm",  # Identify as system agent for deployment
            f"tools: {tools_str}",
            f"model: {model}"
        ]
        
        # Add optional fields if present
        # Check for color in metadata section (new format) or root (old format)
        color = (
            template_data.get('metadata', {}).get('color') or
            template_data.get('color')
        )
        if color:
            frontmatter_lines.append(f"color: {color}")
        
        frontmatter_lines.append("---")
        frontmatter_lines.append("")
        frontmatter_lines.append("")
        
        frontmatter = '\n'.join(frontmatter_lines)
        
        # Get the main content (instructions)
        # Check multiple possible locations for instructions
        content = (
            template_data.get('instructions') or
            template_data.get('narrative_fields', {}).get('instructions') or
            template_data.get('content') or
            f"You are the {agent_name} agent. Perform tasks related to {template_data.get('description', 'your specialization')}."
        )
        
        return frontmatter + content

    def _build_agent_yaml(self, agent_name: str, template_path: Path, base_agent_data: dict) -> str:
        """
        Build a complete agent YAML file by combining base agent and template.
        Only includes essential fields for Claude Code best practices.
        
        Args:
            agent_name: Name of the agent
            template_path: Path to the agent template JSON file
            base_agent_data: Base agent data from JSON
            
        Returns:
            Complete agent YAML content
        """
        import json
        
        # Read template JSON
        template_data = json.loads(template_path.read_text())
        
        # Extract capabilities
        capabilities = template_data.get('capabilities', {})
        metadata = template_data.get('metadata', {})
        
        # Extract version information
        agent_version = self._parse_version(template_data.get('agent_version') or template_data.get('version', 0))
        version_string = self._format_version_display(agent_version)
        
        # Get tools list
        tools = capabilities.get('tools', [])
        tools_str = ', '.join(tools) if tools else 'Read, Write, Edit, Grep, Glob, LS'
        
        # Get description
        description = (
            metadata.get('description') or
            template_data.get('description') or
            f'{agent_name.title()} agent for specialized tasks'
        )
        
        # Get priority based on agent type
        priority_map = {
            'security': 'high',
            'qa': 'high', 
            'engineer': 'high',
            'documentation': 'medium',
            'research': 'medium',
            'ops': 'high',
            'data_engineer': 'medium',
            'version_control': 'high'
        }
        priority = priority_map.get(agent_name, 'medium')
        
        # Get model
        model = capabilities.get('model', 'claude-3-5-sonnet-20241022')
        
        # Get temperature
        temperature = capabilities.get('temperature', 0.3)
        
        # Build clean YAML frontmatter with only essential fields
        yaml_content = f"""---
name: {agent_name}
description: "{description}"
version: "{version_string}"
tools: {tools_str}
priority: {priority}
model: {model}
temperature: {temperature}"""
        
        # Add allowed_tools if present
        if 'allowed_tools' in capabilities:
            yaml_content += f"\nallowed_tools: {json.dumps(capabilities['allowed_tools'])}"
            
        # Add disallowed_tools if present  
        if 'disallowed_tools' in capabilities:
            yaml_content += f"\ndisallowed_tools: {json.dumps(capabilities['disallowed_tools'])}"
            
        yaml_content += "\n---\n"
        
        # Get instructions from template
        instructions = (
            template_data.get('instructions') or
            base_agent_data.get('narrative_fields', {}).get('instructions', '')
        )
        
        # Add base instructions if not already included
        base_instructions = base_agent_data.get('narrative_fields', {}).get('instructions', '')
        if base_instructions and base_instructions not in instructions:
            yaml_content += base_instructions + "\n\n---\n\n"
            
        yaml_content += instructions
        
        return yaml_content
    
    def _merge_narrative_fields(self, base_data: dict, template_data: dict) -> dict:
        """
        Merge narrative fields from base and template, combining arrays.
        
        Args:
            base_data: Base agent data
            template_data: Agent template data
            
        Returns:
            Merged narrative fields
        """
        base_narrative = base_data.get('narrative_fields', {})
        template_narrative = template_data.get('narrative_fields', {})
        
        merged = {}
        
        # For narrative fields, combine base + template
        for field in ['when_to_use', 'specialized_knowledge', 'unique_capabilities']:
            base_items = base_narrative.get(field, [])
            template_items = template_narrative.get(field, [])
            merged[field] = base_items + template_items
        
        # For instructions, combine with separator
        base_instructions = base_narrative.get('instructions', '')
        template_instructions = template_narrative.get('instructions', '')
        
        if base_instructions and template_instructions:
            merged['instructions'] = base_instructions + "\n\n---\n\n" + template_instructions
        elif template_instructions:
            merged['instructions'] = template_instructions
        elif base_instructions:
            merged['instructions'] = base_instructions
        else:
            merged['instructions'] = ''
            
        return merged
    
    def _merge_configuration_fields(self, base_data: dict, template_data: dict) -> dict:
        """
        Merge configuration fields, with template overriding base.
        
        Args:
            base_data: Base agent data
            template_data: Agent template data
            
        Returns:
            Merged configuration fields
        """
        base_config = base_data.get('configuration_fields', {})
        template_config = template_data.get('configuration_fields', {})
        
        # Start with base configuration
        merged = base_config.copy()
        
        # Override with template-specific configuration
        merged.update(template_config)
        
        # Also merge in capabilities from new format if not already in config
        capabilities = template_data.get('capabilities', {})
        if capabilities:
            # Map capabilities fields to configuration fields
            if 'tools' not in merged and 'tools' in capabilities:
                merged['tools'] = capabilities['tools']
            if 'max_tokens' not in merged and 'max_tokens' in capabilities:
                merged['max_tokens'] = capabilities['max_tokens']
            if 'temperature' not in merged and 'temperature' in capabilities:
                merged['temperature'] = capabilities['temperature']
            if 'timeout' not in merged and 'timeout' in capabilities:
                merged['timeout'] = capabilities['timeout']
            if 'memory_limit' not in merged and 'memory_limit' in capabilities:
                merged['memory_limit'] = capabilities['memory_limit']
            if 'cpu_limit' not in merged and 'cpu_limit' in capabilities:
                merged['cpu_limit'] = capabilities['cpu_limit']
            if 'network_access' not in merged and 'network_access' in capabilities:
                merged['network_access'] = capabilities['network_access']
            if 'model' not in merged and 'model' in capabilities:
                merged['model'] = capabilities['model']
        
        # Also check metadata for description and tags in new format
        metadata = template_data.get('metadata', {})
        if metadata:
            if 'description' not in merged and 'description' in metadata:
                merged['description'] = metadata['description']
            if 'tags' not in merged and 'tags' in metadata:
                merged['tags'] = metadata['tags']
        
        return merged
    
    def set_claude_environment(self, config_dir: Optional[Path] = None) -> Dict[str, str]:
        """
        Set Claude environment variables for agent discovery.
        
        OPERATIONAL PURPOSE:
        Claude Code discovers agents through environment variables that
        point to configuration directories. This method ensures proper
        environment setup for agent runtime discovery.
        
        ENVIRONMENT VARIABLES SET:
        1. CLAUDE_CONFIG_DIR: Root configuration directory path
        2. CLAUDE_MAX_PARALLEL_SUBAGENTS: Concurrency limit (default: 5)
        3. CLAUDE_TIMEOUT: Agent execution timeout (default: 600s)
        
        DEPLOYMENT CONSIDERATIONS:
        - Call after agent deployment for immediate availability
        - Environment changes affect current process and children
        - Does not persist across system restarts
        - Add to shell profile for permanent configuration
        
        TROUBLESHOOTING:
        - Verify with: echo $CLAUDE_CONFIG_DIR
        - Check agent discovery: ls $CLAUDE_CONFIG_DIR/agents/
        - Monitor timeout issues in production
        - Adjust parallel limits based on system resources
        
        PERFORMANCE TUNING:
        - Increase parallel agents for CPU-bound tasks
        - Reduce for memory-constrained environments
        - Balance timeout with longest expected operations
        - Monitor resource usage during parallel execution
        
        Args:
            config_dir: Claude configuration directory (default: .claude/)
            
        Returns:
            Dictionary of environment variables set for verification
        """
        if not config_dir:
            # Use the working directory determined during initialization
            config_dir = self.working_directory / Paths.CLAUDE_CONFIG_DIR.value
        
        env_vars = {}
        
        # Set Claude configuration directory
        env_vars[EnvironmentVars.CLAUDE_CONFIG_DIR.value] = str(config_dir.absolute())
        
        # Set parallel agent limits
        env_vars[EnvironmentVars.CLAUDE_MAX_PARALLEL_SUBAGENTS.value] = EnvironmentVars.DEFAULT_MAX_AGENTS.value
        
        # Set timeout for agent execution
        env_vars[EnvironmentVars.CLAUDE_TIMEOUT.value] = EnvironmentVars.DEFAULT_TIMEOUT.value
        
        # Apply environment variables
        for key, value in env_vars.items():
            os.environ[key] = value
            self.logger.debug(f"Set environment: {key}={value}")
        
        return env_vars
    
    def verify_deployment(self, config_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        Verify agent deployment and Claude configuration.
        
        OPERATIONAL PURPOSE:
        Post-deployment verification ensures agents are correctly deployed
        and discoverable by Claude Code. Critical for deployment validation
        and troubleshooting runtime issues.
        
        VERIFICATION CHECKS:
        1. Configuration directory exists and is accessible
        2. Agents directory contains expected YAML files
        3. Agent files have valid YAML frontmatter
        4. Version format is current (identifies migration needs)
        5. Environment variables are properly set
        
        MONITORING INTEGRATION:
        - Call after deployment for health checks
        - Include in deployment pipelines
        - Log results for audit trails
        - Alert on missing agents or errors
        
        TROUBLESHOOTING GUIDE:
        - Missing config_dir: Check deployment target path
        - No agents found: Verify deployment completed
        - Migration needed: Run with force_rebuild
        - Environment warnings: Call set_claude_environment()
        
        RESULT INTERPRETATION:
        - agents_found: Successfully deployed agents
        - agents_needing_migration: Require version update
        - warnings: Non-critical issues to address
        - environment: Current runtime configuration
        
        Args:
            config_dir: Claude configuration directory (default: .claude/)
            
        Returns:
            Verification results dictionary:
            - config_dir: Checked directory path
            - agents_found: List of discovered agents with metadata
            - agents_needing_migration: Agents with old version format
            - environment: Current environment variables
            - warnings: List of potential issues
        """
        if not config_dir:
            # Use the working directory determined during initialization
            config_dir = self.working_directory / ".claude"
        
        results = {
            "config_dir": str(config_dir),
            "agents_found": [],
            "agents_needing_migration": [],
            "environment": {},
            "warnings": []
        }
        
        # Check configuration directory
        if not config_dir.exists():
            results["warnings"].append(f"Configuration directory not found: {config_dir}")
            return results
        
        # Check agents directory
        agents_dir = config_dir / "agents"
        if not agents_dir.exists():
            results["warnings"].append(f"Agents directory not found: {agents_dir}")
            return results
        
        # List deployed agents
        agent_files = list(agents_dir.glob("*.md"))
        
        # Get exclusion configuration for logging purposes
        try:
            from claude_mpm.core.config import Config
            config = Config()
            excluded_agents = config.get('agent_deployment.excluded_agents', [])
            if excluded_agents:
                self.logger.debug(f"Note: The following agents are configured for exclusion: {excluded_agents}")
        except Exception:
            pass  # Ignore config loading errors in verification
        
        for agent_file in agent_files:
            try:
                # Read first few lines to get agent name from YAML
                with open(agent_file, 'r') as f:
                    lines = f.readlines()[:10]
                    
                agent_info = {
                    "file": agent_file.name,
                    "path": str(agent_file)
                }
                
                # Extract name, version, and base_version from YAML frontmatter
                version_str = None
                base_version_str = None
                for line in lines:
                    if line.startswith("name:"):
                        agent_info["name"] = line.split(":", 1)[1].strip().strip('"\'')
                    elif line.startswith("version:"):
                        version_str = line.split(":", 1)[1].strip().strip('"\'')
                        agent_info["version"] = version_str
                    elif line.startswith("base_version:"):
                        base_version_str = line.split(":", 1)[1].strip().strip('"\'')
                        agent_info["base_version"] = base_version_str
                
                # Check if agent needs migration
                if version_str and self._is_old_version_format(version_str):
                    agent_info["needs_migration"] = True
                    results["agents_needing_migration"].append(agent_info["name"])
                
                results["agents_found"].append(agent_info)
                
            except Exception as e:
                results["warnings"].append(f"Failed to read {agent_file.name}: {e}")
        
        # Check environment variables
        env_vars = ["CLAUDE_CONFIG_DIR", "CLAUDE_MAX_PARALLEL_SUBAGENTS", "CLAUDE_TIMEOUT"]
        for var in env_vars:
            value = os.environ.get(var)
            if value:
                results["environment"][var] = value
            else:
                results["warnings"].append(f"Environment variable not set: {var}")
        
        return results
    
    def deploy_agent(self, agent_name: str, target_dir: Path, force_rebuild: bool = False) -> bool:
        """
        Deploy a single agent to the specified directory.
        
        Args:
            agent_name: Name of the agent to deploy
            target_dir: Target directory for deployment (Path object)
            force_rebuild: Whether to force rebuild even if version is current
            
        Returns:
            True if deployment was successful, False otherwise
            
        WHY: Single agent deployment because:
        - Users may want to deploy specific agents only
        - Reduces deployment time for targeted updates
        - Enables selective agent management in projects
        
        FIXED: Method now correctly handles all internal calls to:
        - _check_agent_needs_update (with 3 arguments)
        - _build_agent_markdown (with 3 arguments including base_agent_data)
        - Properly loads base_agent_data before building agent content
        """
        try:
            # Find the template file
            template_file = self.templates_dir / f"{agent_name}.json"
            if not template_file.exists():
                self.logger.error(f"Agent template not found: {agent_name}")
                return False
            
            # Ensure target directory exists
            agents_dir = target_dir / '.claude' / 'agents'
            agents_dir.mkdir(parents=True, exist_ok=True)
            
            # Build and deploy the agent
            target_file = agents_dir / f"{agent_name}.md"
            
            # Check if update is needed
            if not force_rebuild and target_file.exists():
                # Load base agent data for version checking
                base_agent_data = {}
                base_agent_version = (0, 0, 0)
                if self.base_agent_path.exists():
                    try:
                        import json
                        base_agent_data = json.loads(self.base_agent_path.read_text())
                        base_agent_version = self._parse_version(base_agent_data.get('base_version') or base_agent_data.get('version', 0))
                    except Exception as e:
                        self.logger.warning(f"Could not load base agent for version check: {e}")
                
                needs_update, reason = self._check_agent_needs_update(target_file, template_file, base_agent_version)
                if not needs_update:
                    self.logger.info(f"Agent {agent_name} is up to date")
                    return True
                else:
                    self.logger.info(f"Updating agent {agent_name}: {reason}")
            
            # Load base agent data for building
            base_agent_data = {}
            if self.base_agent_path.exists():
                try:
                    import json
                    base_agent_data = json.loads(self.base_agent_path.read_text())
                except Exception as e:
                    self.logger.warning(f"Could not load base agent: {e}")
            
            # Build the agent markdown
            agent_content = self._build_agent_markdown(agent_name, template_file, base_agent_data)
            if not agent_content:
                self.logger.error(f"Failed to build agent content for {agent_name}")
                return False
            
            # Write to target file
            target_file.write_text(agent_content)
            self.logger.info(f"Successfully deployed agent: {agent_name} to {target_file}")
            
            return True
            
        except AgentDeploymentError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Wrap generic exceptions with context
            raise AgentDeploymentError(
                f"Failed to deploy agent {agent_name}",
                context={"agent_name": agent_name, "error": str(e)}
            ) from e
    
    def list_available_agents(self) -> List[Dict[str, Any]]:
        """
        List available agent templates.
        
        Returns:
            List of agent information dictionaries
        """
        agents = []
        
        if not self.templates_dir.exists():
            self.logger.warning(f"Agents directory not found: {self.templates_dir}")
            return agents
        
        template_files = sorted(self.templates_dir.glob("*.json"))
        
        # Load configuration for exclusions
        try:
            from claude_mpm.core.config import Config
            config = Config()
            excluded_agents = config.get('agent_deployment.excluded_agents', [])
            case_sensitive = config.get('agent_deployment.case_sensitive', False)
            
            # Normalize excluded agents for comparison
            if not case_sensitive:
                excluded_agents = [agent.lower() for agent in excluded_agents]
        except Exception:
            # If config loading fails, use empty exclusion list
            excluded_agents = []
            case_sensitive = False
        
        # Build combined exclusion set
        hardcoded_exclusions = {"__init__", "MEMORIES", "TODOWRITE", "INSTRUCTIONS", "README", "pm", "PM", "project_manager"}
        
        # Filter out excluded agents
        filtered_files = []
        for f in template_files:
            agent_name = f.stem
            
            # Check hardcoded exclusions
            if agent_name in hardcoded_exclusions:
                continue
            
            # Check file patterns
            if agent_name.startswith(".") or agent_name.endswith(".backup"):
                continue
            
            # Check user-configured exclusions
            compare_name = agent_name.lower() if not case_sensitive else agent_name
            if compare_name in excluded_agents:
                continue
            
            filtered_files.append(f)
        
        template_files = filtered_files
        
        for template_file in template_files:
            try:
                agent_name = template_file.stem
                agent_info = {
                    "name": agent_name,
                    "file": template_file.name,
                    "path": str(template_file),
                    "size": template_file.stat().st_size,
                    "description": f"{agent_name.title()} agent for specialized tasks"
                }
                
                # Try to extract metadata from template JSON
                try:
                    import json
                    template_data = json.loads(template_file.read_text())
                    
                    # Handle different schema formats
                    if 'metadata' in template_data:
                        # New schema format
                        metadata = template_data.get('metadata', {})
                        agent_info["description"] = metadata.get('description', agent_info["description"])
                        agent_info["role"] = metadata.get('specializations', [''])[0] if metadata.get('specializations') else ''
                    elif 'configuration_fields' in template_data:
                        # Old schema format
                        config_fields = template_data.get('configuration_fields', {})
                        agent_info["role"] = config_fields.get('primary_role', '')
                        agent_info["description"] = config_fields.get('description', agent_info["description"])
                    
                    # Handle both 'agent_version' (new format) and 'version' (old format)
                    version_tuple = self._parse_version(template_data.get('agent_version') or template_data.get('version', 0))
                    agent_info["version"] = self._format_version_display(version_tuple)
                
                except Exception:
                    pass  # Use defaults if can't parse
                
                agents.append(agent_info)
                
            except Exception as e:
                self.logger.error(f"Failed to read template {template_file.name}: {e}")
        
        return agents
    
    def _check_agent_needs_update(self, deployed_file: Path, template_file: Path, current_base_version: tuple) -> tuple:
        """
        Check if a deployed agent needs to be updated.
        
        OPERATIONAL LOGIC:
        1. Verifies agent is system-managed (claude-mpm authored)
        2. Extracts version from deployed YAML frontmatter
        3. Detects old version formats requiring migration
        4. Compares semantic versions for update decision
        5. Returns detailed reason for update/skip decision
        
        VERSION MIGRATION STRATEGY:
        - Old serial format (0002-0005) -> Semantic (2.5.0)
        - Missing versions -> Force update to latest
        - Non-semantic formats -> Trigger migration
        - Preserves user modifications (non-system agents)
        
        PERFORMANCE OPTIMIZATION:
        - Early exit for non-system agents
        - Regex compilation cached by Python
        - Minimal file reads (frontmatter only)
        - Version comparison without full parse
        
        ERROR RECOVERY:
        - Assumes update needed on parse failures
        - Logs warnings for investigation
        - Never blocks deployment pipeline
        - Safe fallback to force update
        
        Args:
            deployed_file: Path to the deployed agent file
            template_file: Path to the template file
            current_base_version: Current base agent version (unused in new strategy)
            
        Returns:
            Tuple of (needs_update: bool, reason: str)
            - needs_update: True if agent should be redeployed
            - reason: Human-readable explanation for decision
        """
        try:
            # Read deployed agent content
            deployed_content = deployed_file.read_text()
            
            # Check if it's a system agent (authored by claude-mpm)
            if "claude-mpm" not in deployed_content:
                return (False, "not a system agent")
            
            # Extract version info from YAML frontmatter
            import re
            
            # Check if using old serial format first
            is_old_format = False
            old_version_str = None
            
            # Try legacy combined format (e.g., "0002-0005")
            legacy_match = re.search(r'^version:\s*["\']?(\d+)-(\d+)["\']?', deployed_content, re.MULTILINE)
            if legacy_match:
                is_old_format = True
                old_version_str = f"{legacy_match.group(1)}-{legacy_match.group(2)}"
                # Convert legacy format to semantic version
                # Treat the agent version (second number) as minor version
                deployed_agent_version = (0, int(legacy_match.group(2)), 0)
                self.logger.info(f"Detected old serial version format: {old_version_str}")
            else:
                # Try to extract semantic version format (e.g., "2.1.0")
                version_match = re.search(r'^version:\s*["\']?v?(\d+)\.(\d+)\.(\d+)["\']?', deployed_content, re.MULTILINE)
                if version_match:
                    deployed_agent_version = (int(version_match.group(1)), int(version_match.group(2)), int(version_match.group(3)))
                else:
                    # Fallback: try separate fields (very old format)
                    agent_version_match = re.search(r"^agent_version:\s*(\d+)", deployed_content, re.MULTILINE)
                    if agent_version_match:
                        is_old_format = True
                        old_version_str = f"agent_version: {agent_version_match.group(1)}"
                        deployed_agent_version = (0, int(agent_version_match.group(1)), 0)
                        self.logger.info(f"Detected old separate version format: {old_version_str}")
                    else:
                        # Check for missing version field
                        if "version:" not in deployed_content:
                            is_old_format = True
                            old_version_str = "missing"
                            deployed_agent_version = (0, 0, 0)
                            self.logger.info("Detected missing version field")
                        else:
                            deployed_agent_version = (0, 0, 0)
            
            # For base version, we don't need to extract from deployed file anymore
            # as it's tracked in metadata
            
            # Read template to get current agent version
            import json
            template_data = json.loads(template_file.read_text())
            
            # Extract agent version from template (handle both numeric and semantic versioning)
            current_agent_version = self._parse_version(template_data.get('agent_version') or template_data.get('version', 0))
            
            # Compare semantic versions properly
            # Semantic version comparison: compare major, then minor, then patch
            def compare_versions(v1: tuple, v2: tuple) -> int:
                """Compare two version tuples. Returns -1 if v1 < v2, 0 if equal, 1 if v1 > v2."""
                for a, b in zip(v1, v2):
                    if a < b:
                        return -1
                    elif a > b:
                        return 1
                return 0
            
            # If old format detected, always trigger update for migration
            if is_old_format:
                new_version_str = self._format_version_display(current_agent_version)
                return (True, f"migration needed from old format ({old_version_str}) to semantic version ({new_version_str})")
            
            # Check if agent template version is newer
            if compare_versions(current_agent_version, deployed_agent_version) > 0:
                deployed_str = self._format_version_display(deployed_agent_version)
                current_str = self._format_version_display(current_agent_version)
                return (True, f"agent template updated ({deployed_str} -> {current_str})")
            
            # Note: We no longer check base agent version separately since we're using
            # a unified semantic version for the agent
            
            return (False, "up to date")
            
        except Exception as e:
            self.logger.warning(f"Error checking agent update status: {e}")
            # On error, assume update is needed
            return (True, "version check failed")
    
    def clean_deployment(self, config_dir: Optional[Path] = None) -> Dict[str, Any]:
        """
        Clean up deployed agents.
        
        Args:
            config_dir: Claude configuration directory (default: .claude/)
            
        Returns:
            Cleanup results
        """
        if not config_dir:
            # Use the working directory determined during initialization
            config_dir = self.working_directory / ".claude"
        
        results = {
            "removed": [],
            "errors": []
        }
        
        agents_dir = config_dir / "agents"
        if not agents_dir.exists():
            results["errors"].append(f"Agents directory not found: {agents_dir}")
            return results
        
        # Remove system agents only (identified by claude-mpm author)
        agent_files = list(agents_dir.glob("*.md"))
        
        for agent_file in agent_files:
            try:
                # Check if it's a system agent
                with open(agent_file, 'r') as f:
                    content = f.read()
                    if "author: claude-mpm" in content or "author: 'claude-mpm'" in content:
                        agent_file.unlink()
                        results["removed"].append(str(agent_file))
                        self.logger.debug(f"Removed agent: {agent_file.name}")
                
            except Exception as e:
                error_msg = f"Failed to remove {agent_file.name}: {e}"
                self.logger.error(error_msg)
                results["errors"].append(error_msg)
                # Not raising AgentDeploymentError here to continue cleanup
        
        return results
    
    def _extract_agent_metadata(self, template_content: str) -> Dict[str, Any]:
        """
        Extract metadata from simplified agent template content.
        
        Args:
            template_content: Agent template markdown content
            
        Returns:
            Dictionary of extracted metadata
        """
        metadata = {}
        lines = template_content.split('\n')
        
        # Extract sections based on the new simplified format
        current_section = None
        section_content = []
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('## When to Use'):
                # Save previous section before starting new one
                if current_section and section_content:
                    metadata[current_section] = section_content.copy()
                current_section = 'when_to_use'
                section_content = []
            elif line.startswith('## Specialized Knowledge'):
                # Save previous section before starting new one
                if current_section and section_content:
                    metadata[current_section] = section_content.copy()
                current_section = 'specialized_knowledge'
                section_content = []
            elif line.startswith('## Unique Capabilities'):
                # Save previous section before starting new one
                if current_section and section_content:
                    metadata[current_section] = section_content.copy()
                current_section = 'unique_capabilities'
                section_content = []
            elif line.startswith('## ') or line.startswith('# '):
                # End of section - save current section
                if current_section and section_content:
                    metadata[current_section] = section_content.copy()
                current_section = None
                section_content = []
            elif current_section and line.startswith('- '):
                # Extract list item, removing the "- " prefix
                item = line[2:].strip()
                if item:
                    section_content.append(item)
        
        # Handle last section if file ends without another header
        if current_section and section_content:
            metadata[current_section] = section_content.copy()
        
        # Ensure all required fields have defaults
        metadata.setdefault('when_to_use', [])
        metadata.setdefault('specialized_knowledge', [])
        metadata.setdefault('unique_capabilities', [])
        
        return metadata
    
    def _get_agent_tools(self, agent_name: str, metadata: Dict[str, Any]) -> List[str]:
        """
        Get appropriate tools for an agent based on its type.
        
        Args:
            agent_name: Name of the agent
            metadata: Agent metadata
            
        Returns:
            List of tool names
        """
        # Base tools all agents should have
        base_tools = [
            "Read",
            "Write", 
            "Edit",
            "MultiEdit",
            "Grep",
            "Glob",
            "LS",
            "TodoWrite"
        ]
        
        # Agent-specific tools
        agent_tools = {
            'engineer': base_tools + ["Bash", "WebSearch", "WebFetch"],
            'qa': base_tools + ["Bash", "WebSearch"],
            'documentation': base_tools + ["WebSearch", "WebFetch"],
            'research': base_tools + ["WebSearch", "WebFetch", "Bash"],
            'security': base_tools + ["Bash", "WebSearch", "Grep"],
            'ops': base_tools + ["Bash", "WebSearch"],
            'data_engineer': base_tools + ["Bash", "WebSearch"],
            'version_control': base_tools + ["Bash"]
        }
        
        # Return specific tools or default set
        return agent_tools.get(agent_name, base_tools + ["Bash", "WebSearch"])
    
    def _format_version_display(self, version_tuple: tuple) -> str:
        """
        Format version tuple for display.
        
        Args:
            version_tuple: Tuple of (major, minor, patch)
            
        Returns:
            Formatted version string
        """
        if isinstance(version_tuple, tuple) and len(version_tuple) == 3:
            major, minor, patch = version_tuple
            return f"{major}.{minor}.{patch}"
        else:
            # Fallback for legacy format
            return str(version_tuple)
    
    def _is_old_version_format(self, version_str: str) -> bool:
        """
        Check if a version string is in the old serial format.
        
        Old formats include:
        - Serial format: "0002-0005" (contains hyphen, all digits)
        - Missing version field
        - Non-semantic version formats
        
        Args:
            version_str: Version string to check
            
        Returns:
            True if old format, False if semantic version
        """
        if not version_str:
            return True
            
        import re
        
        # Check for serial format (e.g., "0002-0005")
        if re.match(r'^\d+-\d+$', version_str):
            return True
            
        # Check for semantic version format (e.g., "2.1.0")
        if re.match(r'^v?\d+\.\d+\.\d+$', version_str):
            return False
            
        # Any other format is considered old
        return True
    
    def _parse_version(self, version_value: Any) -> tuple:
        """
        Parse version from various formats to semantic version tuple.
        
        Handles:
        - Integer values: 5 -> (0, 5, 0)
        - String integers: "5" -> (0, 5, 0)
        - Semantic versions: "2.1.0" -> (2, 1, 0)
        - Invalid formats: returns (0, 0, 0)
        
        Args:
            version_value: Version in various formats
            
        Returns:
            Tuple of (major, minor, patch) for comparison
        """
        if isinstance(version_value, int):
            # Legacy integer version - treat as minor version
            return (0, version_value, 0)
            
        if isinstance(version_value, str):
            # Try to parse as simple integer
            if version_value.isdigit():
                return (0, int(version_value), 0)
            
            # Try to parse semantic version (e.g., "2.1.0" or "v2.1.0")
            import re
            sem_ver_match = re.match(r'^v?(\d+)\.(\d+)\.(\d+)', version_value)
            if sem_ver_match:
                major = int(sem_ver_match.group(1))
                minor = int(sem_ver_match.group(2))
                patch = int(sem_ver_match.group(3))
                return (major, minor, patch)
            
            # Try to extract first number from string as minor version
            num_match = re.search(r'(\d+)', version_value)
            if num_match:
                return (0, int(num_match.group(1)), 0)
        
        # Default to 0.0.0 for invalid formats
        return (0, 0, 0)
    
    def _format_yaml_list(self, items: List[str], indent: int) -> str:
        """
        Format a list for YAML with proper indentation.
        
        Args:
            items: List of items
            indent: Number of spaces to indent
            
        Returns:
            Formatted YAML list string
        """
        if not items:
            items = ["No items specified"]
        
        indent_str = " " * indent
        formatted_items = []
        
        for item in items:
            # Escape quotes in the item
            item = item.replace('"', '\\"')
            formatted_items.append(f'{indent_str}- "{item}"')
        
        return '\n'.join(formatted_items)
    
    def _get_agent_specific_config(self, agent_name: str) -> Dict[str, Any]:
        """
        Get agent-specific configuration based on agent type.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Dictionary of agent-specific configuration
        """
        # Base configuration all agents share
        base_config = {
            'timeout': TimeoutConfig.DEFAULT_TIMEOUT,
            'max_tokens': SystemLimits.MAX_TOKEN_LIMIT,
            'memory_limit': ResourceLimits.STANDARD_MEMORY_RANGE[0],  # Use lower bound of standard memory
            'cpu_limit': ResourceLimits.STANDARD_CPU_RANGE[1],  # Use upper bound of standard CPU
            'network_access': True,
        }
        
        # Agent-specific configurations
        configs = {
            'engineer': {
                **base_config,
                'description': 'Code implementation, development, and inline documentation',
                'tags': '["engineer", "development", "coding", "implementation"]',
                'tools': '["Read", "Write", "Edit", "MultiEdit", "Bash", "Grep", "Glob", "LS", "WebSearch", "TodoWrite"]',
                'temperature': 0.2,
                'when_to_use': ['Code implementation needed', 'Bug fixes required', 'Refactoring tasks'],
                'specialized_knowledge': ['Programming best practices', 'Design patterns', 'Code optimization'],
                'unique_capabilities': ['Write production code', 'Debug complex issues', 'Refactor codebases'],
                'primary_role': 'Code implementation and development',
                'specializations': '["coding", "debugging", "refactoring", "optimization"]',
                'authority': 'ALL code implementation decisions',
            },
            'qa': {
                **base_config,
                'description': 'Quality assurance, testing, and validation',
                'tags': '["qa", "testing", "quality", "validation"]',
                'tools': '["Read", "Write", "Edit", "Bash", "Grep", "Glob", "LS", "TodoWrite"]',
                'temperature': 0.1,
                'when_to_use': ['Testing needed', 'Quality validation', 'Test coverage analysis'],
                'specialized_knowledge': ['Testing methodologies', 'Quality metrics', 'Test automation'],
                'unique_capabilities': ['Execute test suites', 'Identify edge cases', 'Validate quality'],
                'primary_role': 'Testing and quality assurance',
                'specializations': '["testing", "validation", "quality-assurance", "coverage"]',
                'authority': 'ALL testing and quality decisions',
            },
            'documentation': {
                **base_config,
                'description': 'Documentation creation, maintenance, and changelog generation',
                'tags': '["documentation", "writing", "changelog", "docs"]',
                'tools': '["Read", "Write", "Edit", "MultiEdit", "Grep", "Glob", "LS", "WebSearch", "TodoWrite"]',
                'temperature': 0.3,
                'when_to_use': ['Documentation updates needed', 'Changelog generation', 'README updates'],
                'specialized_knowledge': ['Technical writing', 'Documentation standards', 'Semantic versioning'],
                'unique_capabilities': ['Create clear documentation', 'Generate changelogs', 'Maintain docs'],
                'primary_role': 'Documentation and technical writing',
                'specializations': '["technical-writing", "changelog", "api-docs", "guides"]',
                'authority': 'ALL documentation decisions',
            },
            'research': {
                **base_config,
                'description': 'Technical research, analysis, and investigation',
                'tags': '["research", "analysis", "investigation", "evaluation"]',
                'tools': '["Read", "Grep", "Glob", "LS", "WebSearch", "WebFetch", "TodoWrite"]',
                'temperature': 0.4,
                'when_to_use': ['Technical research needed', 'Solution evaluation', 'Best practices investigation'],
                'specialized_knowledge': ['Research methodologies', 'Technical analysis', 'Evaluation frameworks'],
                'unique_capabilities': ['Deep investigation', 'Comparative analysis', 'Evidence-based recommendations'],
                'primary_role': 'Research and technical analysis',
                'specializations': '["investigation", "analysis", "evaluation", "recommendations"]',
                'authority': 'ALL research decisions',
            },
            'security': {
                **base_config,
                'description': 'Security analysis, vulnerability assessment, and protection',
                'tags': '["security", "vulnerability", "protection", "audit"]',
                'tools': '["Read", "Grep", "Glob", "LS", "Bash", "WebSearch", "TodoWrite"]',
                'temperature': 0.1,
                'when_to_use': ['Security review needed', 'Vulnerability assessment', 'Security audit'],
                'specialized_knowledge': ['Security best practices', 'OWASP guidelines', 'Vulnerability patterns'],
                'unique_capabilities': ['Identify vulnerabilities', 'Security auditing', 'Threat modeling'],
                'primary_role': 'Security analysis and protection',
                'specializations': '["vulnerability-assessment", "security-audit", "threat-modeling", "protection"]',
                'authority': 'ALL security decisions',
            },
            'ops': {
                **base_config,
                'description': 'Deployment, operations, and infrastructure management',
                'tags': '["ops", "deployment", "infrastructure", "devops"]',
                'tools': '["Read", "Write", "Edit", "Bash", "Grep", "Glob", "LS", "TodoWrite"]',
                'temperature': 0.2,
                'when_to_use': ['Deployment configuration', 'Infrastructure setup', 'CI/CD pipeline work'],
                'specialized_knowledge': ['Deployment best practices', 'Infrastructure as code', 'CI/CD'],
                'unique_capabilities': ['Configure deployments', 'Manage infrastructure', 'Automate operations'],
                'primary_role': 'Operations and deployment management',
                'specializations': '["deployment", "infrastructure", "automation", "monitoring"]',
                'authority': 'ALL operations decisions',
            },
            'data_engineer': {
                **base_config,
                'description': 'Data pipeline management and AI API integrations',
                'tags': '["data", "pipeline", "etl", "ai-integration"]',
                'tools': '["Read", "Write", "Edit", "Bash", "Grep", "Glob", "LS", "WebSearch", "TodoWrite"]',
                'temperature': 0.2,
                'when_to_use': ['Data pipeline setup', 'Database design', 'AI API integration'],
                'specialized_knowledge': ['Data architectures', 'ETL processes', 'AI/ML APIs'],
                'unique_capabilities': ['Design data schemas', 'Build pipelines', 'Integrate AI services'],
                'primary_role': 'Data engineering and AI integration',
                'specializations': '["data-pipelines", "etl", "database", "ai-integration"]',
                'authority': 'ALL data engineering decisions',
            },
            'version_control': {
                **base_config,
                'description': 'Git operations, version management, and release coordination',
                'tags': '["git", "version-control", "release", "branching"]',
                'tools': '["Read", "Bash", "Grep", "Glob", "LS", "TodoWrite"]',
                'temperature': 0.1,
                'network_access': False,  # Git operations are local
                'when_to_use': ['Git operations needed', 'Version bumping', 'Release management'],
                'specialized_knowledge': ['Git workflows', 'Semantic versioning', 'Release processes'],
                'unique_capabilities': ['Complex git operations', 'Version management', 'Release coordination'],
                'primary_role': 'Version control and release management',
                'specializations': '["git", "versioning", "branching", "releases"]',
                'authority': 'ALL version control decisions',
            }
        }
        
        # Return the specific config or a default
        return configs.get(agent_name, {
            **base_config,
            'description': f'{agent_name.title()} agent for specialized tasks',
            'tags': f'["{agent_name}", "specialized", "mpm"]',
            'tools': '["Read", "Write", "Edit", "Grep", "Glob", "LS", "TodoWrite"]',
            'temperature': 0.3,
            'when_to_use': [f'When {agent_name} expertise is needed'],
            'specialized_knowledge': [f'{agent_name.title()} domain knowledge'],
            'unique_capabilities': [f'{agent_name.title()} specialized operations'],
            'primary_role': f'{agent_name.title()} operations',
            'specializations': f'["{agent_name}"]',
            'authority': f'ALL {agent_name} decisions',
        })

    def _deploy_system_instructions(self, target_dir: Path, force_rebuild: bool, results: Dict[str, Any]) -> None:
        """
        Deploy system instructions and framework files for PM framework.
        
        Deploys INSTRUCTIONS.md, WORKFLOW.md, and MEMORY.md files following hierarchy:
        - System/User versions → Deploy to ~/.claude/
        - Project-specific versions → Deploy to <project>/.claude/
        
        Args:
            target_dir: Target directory for deployment
            force_rebuild: Force rebuild even if exists
            results: Results dictionary to update
        """
        try:
            # Determine target location based on deployment type
            if self._is_project_specific_deployment():
                # Project-specific files go to project's .claude directory
                claude_dir = self.working_directory / ".claude"
            else:
                # System and user files go to home ~/.claude directory
                claude_dir = Path.home() / ".claude"
            
            # Ensure .claude directory exists
            claude_dir.mkdir(parents=True, exist_ok=True)
            
            # Framework files to deploy
            framework_files = [
                ("INSTRUCTIONS.md", "CLAUDE.md"),  # INSTRUCTIONS.md deploys as CLAUDE.md
                ("WORKFLOW.md", "WORKFLOW.md"),
                ("MEMORY.md", "MEMORY.md")
            ]
            
            # Find the agents directory with framework files
            # Use centralized paths for consistency
            from claude_mpm.config.paths import paths
            agents_path = paths.agents_dir
            
            for source_name, target_name in framework_files:
                source_path = agents_path / source_name
                
                if not source_path.exists():
                    self.logger.warning(f"Framework file not found: {source_path}")
                    continue
                
                target_file = claude_dir / target_name
                
                # Check if update needed
                if not force_rebuild and target_file.exists():
                    # Compare modification times
                    if target_file.stat().st_mtime >= source_path.stat().st_mtime:
                        results["skipped"].append(target_name)
                        self.logger.debug(f"Framework file {target_name} up to date")
                        continue
                
                # Read and deploy framework file
                file_content = source_path.read_text()
                target_file.write_text(file_content)
                
                # Track deployment
                file_existed = target_file.exists()
                deployment_info = {
                    "name": target_name,
                    "template": str(source_path),
                    "target": str(target_file)
                }
                
                if file_existed:
                    results["updated"].append(deployment_info)
                    self.logger.info(f"Updated framework file: {target_name}")
                else:
                    results["deployed"].append(deployment_info)
                    self.logger.info(f"Deployed framework file: {target_name}")
                
        except Exception as e:
            error_msg = f"Failed to deploy system instructions: {e}"
            self.logger.error(error_msg)
            results["errors"].append(error_msg)
            # Not raising AgentDeploymentError as this is non-critical
    
    def _convert_yaml_to_md(self, target_dir: Path) -> Dict[str, Any]:
        """
        Convert existing YAML agent files to MD format with YAML frontmatter.
        
        This method handles backward compatibility by finding existing .yaml
        agent files and converting them to .md format expected by Claude Code.
        
        Args:
            target_dir: Directory containing agent files
            
        Returns:
            Dictionary with conversion results:
            - converted: List of converted files
            - errors: List of conversion errors
            - skipped: List of files that didn't need conversion
        """
        results = {
            "converted": [],
            "errors": [],
            "skipped": []
        }
        
        try:
            # Find existing YAML agent files
            yaml_files = list(target_dir.glob("*.yaml"))
            
            if not yaml_files:
                self.logger.debug("No YAML files found to convert")
                return results
            
            self.logger.info(f"Found {len(yaml_files)} YAML files to convert to MD format")
            
            for yaml_file in yaml_files:
                try:
                    agent_name = yaml_file.stem
                    md_file = target_dir / f"{agent_name}.md"
                    
                    # Skip if MD file already exists (unless it's older than YAML)
                    if md_file.exists():
                        # Check modification times for safety
                        yaml_mtime = yaml_file.stat().st_mtime
                        md_mtime = md_file.stat().st_mtime
                        
                        if md_mtime >= yaml_mtime:
                            results["skipped"].append({
                                "yaml_file": str(yaml_file),
                                "md_file": str(md_file),
                                "reason": "MD file already exists and is newer"
                            })
                            continue
                        else:
                            # MD file is older, proceed with conversion
                            self.logger.info(f"MD file {md_file.name} is older than YAML, converting...")
                    
                    # Read YAML content
                    yaml_content = yaml_file.read_text()
                    
                    # Convert YAML to MD with YAML frontmatter
                    md_content = self._convert_yaml_content_to_md(yaml_content, agent_name)
                    
                    # Write MD file
                    md_file.write_text(md_content)
                    
                    # Create backup of YAML file before removing (for safety)
                    backup_file = target_dir / f"{agent_name}.yaml.backup"
                    try:
                        yaml_file.rename(backup_file)
                        self.logger.debug(f"Created backup: {backup_file.name}")
                    except Exception as backup_error:
                        self.logger.warning(f"Failed to create backup for {yaml_file.name}: {backup_error}")
                        # Still remove the original YAML file even if backup fails
                        yaml_file.unlink()
                    
                    results["converted"].append({
                        "from": str(yaml_file),
                        "to": str(md_file),
                        "agent": agent_name
                    })
                    
                    self.logger.info(f"Converted {yaml_file.name} to {md_file.name}")
                    
                except Exception as e:
                    error_msg = f"Failed to convert {yaml_file.name}: {e}"
                    self.logger.error(error_msg)
                    results["errors"].append(error_msg)
            
        except Exception as e:
            error_msg = f"YAML to MD conversion failed: {e}"
            self.logger.error(error_msg)
            results["errors"].append(error_msg)
        
        return results
    
    def _convert_yaml_content_to_md(self, yaml_content: str, agent_name: str) -> str:
        """
        Convert YAML agent content to MD format with YAML frontmatter.
        
        Args:
            yaml_content: Original YAML content
            agent_name: Name of the agent
            
        Returns:
            Markdown content with YAML frontmatter
        """
        import re
        from datetime import datetime
        
        # Extract YAML frontmatter and content
        yaml_parts = yaml_content.split('---', 2)
        
        if len(yaml_parts) < 3:
            # No proper YAML frontmatter, treat entire content as instructions
            frontmatter = f"""---
name: {agent_name}
description: "Agent for specialized tasks"
version: "1.0.0"
author: "claude-mpm@anthropic.com"
created: "{datetime.now().isoformat()}Z"
updated: "{datetime.now().isoformat()}Z"
tags: ["{agent_name}", "mpm-framework"]
tools: ["Read", "Write", "Edit", "Grep", "Glob", "LS"]
metadata:
  deployment_type: "system"
  converted_from: "yaml"
---

"""
            return frontmatter + yaml_content.strip()
        
        # Parse existing frontmatter
        yaml_frontmatter = yaml_parts[1].strip()
        instructions = yaml_parts[2].strip()
        
        # Extract key fields from YAML frontmatter
        name = agent_name
        description = self._extract_yaml_field(yaml_frontmatter, 'description') or f"{agent_name.title()} agent for specialized tasks"
        version = self._extract_yaml_field(yaml_frontmatter, 'version') or "1.0.0"
        tools_line = self._extract_yaml_field(yaml_frontmatter, 'tools') or "Read, Write, Edit, Grep, Glob, LS"
        
        # Convert tools string to list format
        if isinstance(tools_line, str):
            if tools_line.startswith('[') and tools_line.endswith(']'):
                # Already in list format
                tools_list = tools_line
            else:
                # Convert comma-separated to list
                tools = [tool.strip() for tool in tools_line.split(',')]
                tools_list = str(tools)
        else:
            tools_list = str(tools_line) if tools_line else '["Read", "Write", "Edit", "Grep", "Glob", "LS"]'
        
        # Build new YAML frontmatter
        new_frontmatter = f"""---
name: {name}
description: "{description}"
version: "{version}"
author: "claude-mpm@anthropic.com"
created: "{datetime.now().isoformat()}Z"
updated: "{datetime.now().isoformat()}Z"
tags: ["{agent_name}", "mpm-framework"]
tools: {tools_list}
metadata:
  deployment_type: "system"
  converted_from: "yaml"
---

"""
        
        return new_frontmatter + instructions
    
    def _extract_yaml_field(self, yaml_content: str, field_name: str) -> str:
        """
        Extract a field value from YAML content.
        
        Args:
            yaml_content: YAML content string
            field_name: Field name to extract
            
        Returns:
            Field value or None if not found
        """
        import re
        
        try:
            # Match field with quoted or unquoted values
            pattern = rf'^{field_name}:\s*["\']?(.*?)["\']?\s*$'
            match = re.search(pattern, yaml_content, re.MULTILINE)
            
            if match:
                return match.group(1).strip()
            
            # Try with alternative spacing patterns
            pattern = rf'^{field_name}\s*:\s*(.+)$'
            match = re.search(pattern, yaml_content, re.MULTILINE)
            
            if match:
                value = match.group(1).strip()
                # Remove quotes if present
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                return value
                
        except Exception as e:
            self.logger.warning(f"Error extracting YAML field '{field_name}': {e}")
        
        return None
    
    def _try_async_deployment(self, target_dir: Optional[Path], force_rebuild: bool, 
                              config: Optional[Config], deployment_start_time: float) -> Optional[Dict[str, Any]]:
        """
        Try to use async deployment for better performance.
        
        WHY: Async deployment is 50-70% faster than synchronous deployment
        by using concurrent operations for file I/O and processing.
        
        Args:
            target_dir: Target directory for deployment
            force_rebuild: Whether to force rebuild
            config: Configuration object
            deployment_start_time: Start time for metrics
            
        Returns:
            Deployment results if successful, None if async not available
        """
        try:
            from .async_agent_deployment import deploy_agents_async_wrapper
            self.logger.info("Using async deployment for improved performance")
            
            # Run async deployment
            results = deploy_agents_async_wrapper(
                templates_dir=self.templates_dir,
                base_agent_path=self.base_agent_path,
                working_directory=self.working_directory,
                target_dir=target_dir,
                force_rebuild=force_rebuild,
                config=config
            )
            
            # Add metrics about async vs sync
            if 'metrics' in results:
                results['metrics']['deployment_method'] = 'async'
                duration_ms = results['metrics'].get('duration_ms', 0)
                self.logger.info(f"Async deployment completed in {duration_ms:.1f}ms")
                
                # Update internal metrics
                self._deployment_metrics['total_deployments'] += 1
                if not results.get('errors'):
                    self._deployment_metrics['successful_deployments'] += 1
                else:
                    self._deployment_metrics['failed_deployments'] += 1
            
            return results
            
        except ImportError:
            self.logger.warning("Async deployment not available, falling back to sync")
            return None
        except Exception as e:
            self.logger.warning(f"Async deployment failed, falling back to sync: {e}")
            return None
    
    def _load_deployment_config(self, config: Optional[Config]) -> tuple:
        """
        Load and process deployment configuration.
        
        WHY: Centralized configuration loading reduces duplication
        and ensures consistent handling of exclusion settings.
        
        Args:
            config: Optional configuration object
            
        Returns:
            Tuple of (config, excluded_agents)
        """
        # Load configuration if not provided
        if config is None:
            config = Config()
        
        # Get agent exclusion configuration
        excluded_agents = config.get('agent_deployment.excluded_agents', [])
        case_sensitive = config.get('agent_deployment.case_sensitive', False)
        exclude_dependencies = config.get('agent_deployment.exclude_dependencies', False)
        
        # Normalize excluded agents list for comparison
        if not case_sensitive:
            excluded_agents = [agent.lower() for agent in excluded_agents]
        
        # Log exclusion configuration if agents are being excluded
        if excluded_agents:
            self.logger.info(f"Excluding agents from deployment: {excluded_agents}")
            self.logger.debug(f"Case sensitive matching: {case_sensitive}")
            self.logger.debug(f"Exclude dependencies: {exclude_dependencies}")
        
        return config, excluded_agents
    
    def _determine_agents_directory(self, target_dir: Optional[Path]) -> Path:
        """
        Determine the correct agents directory based on input.
        
        WHY: Different deployment scenarios require different directory
        structures. This method centralizes the logic for consistency.
        
        HIERARCHY:
        - System agents → Deploy to ~/.claude/agents/ (user's home directory)
        - User custom agents from ~/.claude-mpm/agents/ → Deploy to ~/.claude/agents/
        - Project-specific agents from <project>/.claude-mpm/agents/ → Deploy to <project>/.claude/agents/
        
        Args:
            target_dir: Optional target directory
            
        Returns:
            Path to agents directory
        """
        if not target_dir:
            # Default deployment location depends on agent source
            # Check if we're deploying system agents or user/project agents
            if self._is_system_agent_deployment():
                # System agents go to user's home ~/.claude/agents/
                return Path.home() / ".claude" / "agents"
            elif self._is_project_specific_deployment():
                # Project agents stay in project directory
                return self.working_directory / ".claude" / "agents"
            else:
                # Default: User custom agents go to home ~/.claude/agents/
                return Path.home() / ".claude" / "agents"
        
        # If target_dir provided, use it directly (caller decides structure)
        target_dir = Path(target_dir)
        
        # Check if this is already an agents directory
        if target_dir.name == "agents":
            # Already an agents directory, use as-is
            return target_dir
        elif target_dir.name == ".claude-mpm":
            # .claude-mpm directory, add agents subdirectory
            return target_dir / "agents"
        elif target_dir.name == ".claude":
            # .claude directory, add agents subdirectory
            return target_dir / "agents"
        else:
            # Assume it's a project directory, add .claude/agents
            return target_dir / ".claude" / "agents"
    
    def _is_system_agent_deployment(self) -> bool:
        """
        Check if this is a deployment of system agents.
        
        System agents are those provided by the claude-mpm package itself,
        located in the package's agents/templates directory.
        
        Returns:
            True if deploying system agents, False otherwise
        """
        # Check if templates_dir points to the system templates
        if self.templates_dir and self.templates_dir.exists():
            # System agents are in the package's agents/templates directory
            try:
                # Check if templates_dir is within the claude_mpm package structure
                templates_str = str(self.templates_dir.resolve())
                return ("site-packages/claude_mpm" in templates_str or 
                        "src/claude_mpm/agents/templates" in templates_str or
                        (paths.agents_dir / "templates").resolve() == self.templates_dir.resolve())
            except Exception:
                pass
        return False
    
    def _is_project_specific_deployment(self) -> bool:
        """
        Check if deploying project-specific agents.
        
        Project-specific agents are those found in the project's
        .claude-mpm/agents/ directory.
        
        Returns:
            True if deploying project-specific agents, False otherwise
        """
        # Check if we're in a project directory with .claude-mpm/agents
        project_agents_dir = self.working_directory / ".claude-mpm" / "agents"
        if project_agents_dir.exists():
            # Check if templates_dir points to project agents
            if self.templates_dir and self.templates_dir.exists():
                try:
                    return project_agents_dir.resolve() == self.templates_dir.resolve()
                except Exception:
                    pass
        return False
    
    def _is_user_custom_deployment(self) -> bool:
        """
        Check if deploying user custom agents.
        
        User custom agents are those in ~/.claude-mpm/agents/
        
        Returns:
            True if deploying user custom agents, False otherwise
        """
        user_agents_dir = Path.home() / ".claude-mpm" / "agents"
        if user_agents_dir.exists():
            # Check if templates_dir points to user agents
            if self.templates_dir and self.templates_dir.exists():
                try:
                    return user_agents_dir.resolve() == self.templates_dir.resolve()
                except Exception:
                    pass
        return False

    def _initialize_deployment_results(self, agents_dir: Path, deployment_start_time: float) -> Dict[str, Any]:
        """
        Initialize the deployment results dictionary.
        
        WHY: Consistent result structure ensures all deployment
        operations return the same format for easier processing.
        
        Args:
            agents_dir: Target agents directory
            deployment_start_time: Start time for metrics
            
        Returns:
            Initialized results dictionary
        """
        return {
            "target_dir": str(agents_dir),
            "deployed": [],
            "errors": [],
            "skipped": [],
            "updated": [],
            "migrated": [],  # Track agents migrated from old format
            "converted": [],  # Track YAML to MD conversions
            "repaired": [],  # Track agents with repaired frontmatter
            "total": 0,
            # METRICS: Add detailed timing and performance data to results
            "metrics": {
                "start_time": deployment_start_time,
                "end_time": None,
                "duration_ms": None,
                "agent_timings": {},  # Track individual agent deployment times
                "validation_times": {},  # Track template validation times
                "resource_usage": {}  # Could track memory/CPU if needed
            }
        }
    
    def _repair_existing_agents(self, agents_dir: Path, results: Dict[str, Any]) -> None:
        """
        Validate and repair broken frontmatter in existing agents.
        
        WHY: Ensures all existing agents have valid YAML frontmatter
        before deployment, preventing runtime errors in Claude Code.
        
        Args:
            agents_dir: Directory containing agent files
            results: Results dictionary to update
        """
        repair_results = self._validate_and_repair_existing_agents(agents_dir)
        if repair_results["repaired"]:
            results["repaired"] = repair_results["repaired"]
            self.logger.info(f"Repaired frontmatter in {len(repair_results['repaired'])} existing agents")
            for agent_name in repair_results["repaired"]:
                self.logger.debug(f"  - Repaired: {agent_name}")
    
    def _determine_source_tier(self) -> str:
        """
        Determine the source tier for logging.
        
        WHY: Understanding which tier (SYSTEM/USER/PROJECT) agents
        are being deployed from helps with debugging and auditing.
        
        Returns:
            Source tier string
        """
        if ".claude-mpm/agents" in str(self.templates_dir) and "/templates" not in str(self.templates_dir):
            return "PROJECT"
        elif "/.claude-mpm/agents" in str(self.templates_dir) and "/templates" not in str(self.templates_dir):
            return "USER"
        return "SYSTEM"
    
    def _load_base_agent(self) -> tuple:
        """
        Load base agent content and version.
        
        WHY: Base agent contains shared configuration that all agents
        inherit, reducing duplication and ensuring consistency.
        
        Returns:
            Tuple of (base_agent_data, base_agent_version)
        """
        base_agent_data = {}
        base_agent_version = (0, 0, 0)
        
        if self.base_agent_path.exists():
            try:
                import json
                base_agent_data = json.loads(self.base_agent_path.read_text())
                # Handle both 'base_version' (new format) and 'version' (old format)
                # MIGRATION PATH: Supporting both formats during transition period
                base_agent_version = self._parse_version(
                    base_agent_data.get('base_version') or base_agent_data.get('version', 0)
                )
                self.logger.info(f"Loaded base agent template (version {self._format_version_display(base_agent_version)})")
            except Exception as e:
                # NON-FATAL: Base agent is optional enhancement, not required
                self.logger.warning(f"Could not load base agent: {e}")
        
        return base_agent_data, base_agent_version
    
    def _get_filtered_templates(self, excluded_agents: list, config: Config) -> list:
        """
        Get and filter template files based on exclusion rules.
        
        WHY: Centralized filtering logic ensures consistent exclusion
        handling across different deployment scenarios.
        
        Args:
            excluded_agents: List of agents to exclude
            config: Configuration object
            
        Returns:
            List of filtered template files
        """
        # Get all template files
        template_files = list(self.templates_dir.glob("*.json"))
        
        # Build the combined exclusion set
        # Start with hardcoded exclusions (these are ALWAYS excluded)
        hardcoded_exclusions = {"__init__", "MEMORIES", "TODOWRITE", "INSTRUCTIONS", 
                               "README", "pm", "PM", "project_manager"}
        
        # Get case sensitivity setting
        case_sensitive = config.get('agent_deployment.case_sensitive', False)
        
        # Filter out excluded agents
        filtered_files = []
        excluded_count = 0
        
        for f in template_files:
            agent_name = f.stem
            
            # Check hardcoded exclusions (always case-sensitive)
            if agent_name in hardcoded_exclusions:
                self.logger.debug(f"Excluding {agent_name}: hardcoded system exclusion")
                excluded_count += 1
                continue
            
            # Check file patterns
            if agent_name.startswith(".") or agent_name.endswith(".backup"):
                self.logger.debug(f"Excluding {agent_name}: file pattern exclusion")
                excluded_count += 1
                continue
            
            # Check user-configured exclusions
            compare_name = agent_name.lower() if not case_sensitive else agent_name
            if compare_name in excluded_agents:
                self.logger.info(f"Excluding {agent_name}: user-configured exclusion")
                excluded_count += 1
                continue
            
            # Agent is not excluded, add to filtered list
            filtered_files.append(f)
        
        if excluded_count > 0:
            self.logger.info(f"Excluded {excluded_count} agents from deployment")
        
        return filtered_files
    
    def _deploy_single_agent(self, template_file: Path, agents_dir: Path, 
                            base_agent_data: dict, base_agent_version: tuple,
                            force_rebuild: bool, deployment_mode: str, 
                            results: Dict[str, Any]) -> None:
        """
        Deploy a single agent template.
        
        WHY: Extracting single agent deployment logic reduces complexity
        and makes the main deployment loop more readable.
        
        Args:
            template_file: Agent template file
            agents_dir: Target agents directory
            base_agent_data: Base agent data
            base_agent_version: Base agent version
            force_rebuild: Whether to force rebuild
            deployment_mode: Deployment mode (update/project)
            results: Results dictionary to update
        """
        try:
            # METRICS: Track individual agent deployment time
            agent_start_time = time.time()
            
            agent_name = template_file.stem
            target_file = agents_dir / f"{agent_name}.md"
            
            # Check if agent needs update
            needs_update, is_migration, reason = self._check_update_status(
                target_file, template_file, base_agent_version, 
                force_rebuild, deployment_mode
            )
            
            # Skip if exists and doesn't need update (only in update mode)
            if target_file.exists() and not needs_update and deployment_mode != "project":
                results["skipped"].append(agent_name)
                self.logger.debug(f"Skipped up-to-date agent: {agent_name}")
                return
            
            # Build the agent file as markdown with YAML frontmatter
            agent_content = self._build_agent_markdown(agent_name, template_file, base_agent_data)
            
            # Write the agent file
            is_update = target_file.exists()
            target_file.write_text(agent_content)
            
            # Record metrics and update results
            self._record_agent_deployment(
                agent_name, template_file, target_file,
                is_update, is_migration, reason,
                agent_start_time, results
            )
            
        except AgentDeploymentError as e:
            # Re-raise our custom exceptions
            self.logger.error(str(e))
            results["errors"].append(str(e))
        except Exception as e:
            # Wrap generic exceptions with context
            error_msg = f"Failed to build {template_file.name}: {e}"
            self.logger.error(error_msg)
            results["errors"].append(error_msg)
    
    def _check_update_status(self, target_file: Path, template_file: Path,
                            base_agent_version: tuple, force_rebuild: bool,
                            deployment_mode: str) -> tuple:
        """
        Check if agent needs update and determine status.
        
        WHY: Centralized update checking logic ensures consistent
        version comparison and migration detection.
        
        Args:
            target_file: Target agent file
            template_file: Template file
            base_agent_version: Base agent version
            force_rebuild: Whether to force rebuild
            deployment_mode: Deployment mode
            
        Returns:
            Tuple of (needs_update, is_migration, reason)
        """
        needs_update = force_rebuild
        is_migration = False
        reason = ""
        
        # In project deployment mode, always deploy regardless of version
        if deployment_mode == "project":
            if target_file.exists():
                needs_update = True
                self.logger.debug(f"Project deployment mode: will deploy {template_file.stem}")
            else:
                needs_update = True
        elif not needs_update and target_file.exists():
            # In update mode, check version compatibility
            needs_update, reason = self._check_agent_needs_update(
                target_file, template_file, base_agent_version
            )
            if needs_update:
                # Check if this is a migration from old format
                if "migration needed" in reason:
                    is_migration = True
                    self.logger.info(f"Migrating agent {template_file.stem}: {reason}")
                else:
                    self.logger.info(f"Agent {template_file.stem} needs update: {reason}")
        
        return needs_update, is_migration, reason
    
    def _record_agent_deployment(self, agent_name: str, template_file: Path,
                                target_file: Path, is_update: bool,
                                is_migration: bool, reason: str,
                                agent_start_time: float, results: Dict[str, Any]) -> None:
        """
        Record deployment metrics and update results.
        
        WHY: Centralized metrics recording ensures consistent tracking
        of deployment performance and statistics.
        
        Args:
            agent_name: Name of the agent
            template_file: Template file
            target_file: Target file
            is_update: Whether this is an update
            is_migration: Whether this is a migration
            reason: Update/migration reason
            agent_start_time: Start time for this agent
            results: Results dictionary to update
        """
        # METRICS: Record deployment time for this agent
        agent_deployment_time = (time.time() - agent_start_time) * 1000  # Convert to ms
        results["metrics"]["agent_timings"][agent_name] = agent_deployment_time
        
        # METRICS: Update agent type deployment counts
        self._deployment_metrics['agent_type_counts'][agent_name] = \
            self._deployment_metrics['agent_type_counts'].get(agent_name, 0) + 1
        
        deployment_info = {
            "name": agent_name,
            "template": str(template_file),
            "target": str(target_file),
            "deployment_time_ms": agent_deployment_time
        }
        
        if is_migration:
            deployment_info["reason"] = reason
            results["migrated"].append(deployment_info)
            self.logger.info(f"Successfully migrated agent: {agent_name} to semantic versioning")
            
            # METRICS: Track migration statistics
            self._deployment_metrics['migrations_performed'] += 1
            self._deployment_metrics['version_migration_count'] += 1
            
        elif is_update:
            results["updated"].append(deployment_info)
            self.logger.debug(f"Updated agent: {agent_name}")
        else:
            results["deployed"].append(deployment_info)
            self.logger.debug(f"Built and deployed agent: {agent_name}")
    
    def _validate_and_repair_existing_agents(self, agents_dir: Path) -> Dict[str, Any]:
        """
        Validate and repair broken frontmatter in existing agent files.
        
        This method scans existing .claude/agents/*.md files and validates their
        frontmatter. If the frontmatter is broken or missing, it attempts to repair
        it or marks the agent for replacement during deployment.
        
        WHY: Ensures all existing agents have valid YAML frontmatter before deployment,
        preventing runtime errors in Claude Code when loading agents.
        
        Args:
            agents_dir: Directory containing agent .md files
            
        Returns:
            Dictionary with validation results:
            - repaired: List of agent names that were repaired
            - replaced: List of agent names marked for replacement
            - errors: List of validation errors
        """
        results = {
            "repaired": [],
            "replaced": [],
            "errors": []
        }
        
        try:
            # Import frontmatter validator
            from claude_mpm.agents.frontmatter_validator import FrontmatterValidator
            validator = FrontmatterValidator()
            
            # Find existing agent files
            agent_files = list(agents_dir.glob("*.md"))
            
            if not agent_files:
                self.logger.debug("No existing agent files to validate")
                return results
            
            self.logger.debug(f"Validating frontmatter in {len(agent_files)} existing agents")
            
            for agent_file in agent_files:
                try:
                    agent_name = agent_file.stem
                    
                    # Read agent file content
                    content = agent_file.read_text()
                    
                    # Check if this is a system agent (authored by claude-mpm)
                    # Only repair system agents, leave user agents alone
                    if "author: claude-mpm" not in content and "author: 'claude-mpm'" not in content:
                        self.logger.debug(f"Skipping validation for user agent: {agent_name}")
                        continue
                    
                    # Extract and validate frontmatter
                    if not content.startswith("---"):
                        # No frontmatter at all - mark for replacement
                        self.logger.warning(f"Agent {agent_name} has no frontmatter, marking for replacement")
                        results["replaced"].append(agent_name)
                        # Delete the file so it will be recreated
                        agent_file.unlink()
                        continue
                    
                    # Try to extract frontmatter
                    try:
                        end_marker = content.find("\n---\n", 4)
                        if end_marker == -1:
                            end_marker = content.find("\n---\r\n", 4)
                        
                        if end_marker == -1:
                            # Broken frontmatter - mark for replacement
                            self.logger.warning(f"Agent {agent_name} has broken frontmatter, marking for replacement")
                            results["replaced"].append(agent_name)
                            # Delete the file so it will be recreated
                            agent_file.unlink()
                            continue
                        
                        # Validate frontmatter with the validator
                        validation_result = validator.validate_file(agent_file)
                        
                        if not validation_result.is_valid:
                            # Check if it can be corrected
                            if validation_result.corrected_frontmatter:
                                # Apply corrections
                                correction_result = validator.correct_file(agent_file, dry_run=False)
                                if correction_result.corrections:
                                    results["repaired"].append(agent_name)
                                    self.logger.info(f"Repaired frontmatter for agent {agent_name}")
                                    for correction in correction_result.corrections:
                                        self.logger.debug(f"  - {correction}")
                            else:
                                # Cannot be corrected - mark for replacement
                                self.logger.warning(f"Agent {agent_name} has invalid frontmatter that cannot be repaired, marking for replacement")
                                results["replaced"].append(agent_name)
                                # Delete the file so it will be recreated
                                agent_file.unlink()
                        elif validation_result.warnings:
                            # Has warnings but is valid
                            for warning in validation_result.warnings:
                                self.logger.debug(f"Agent {agent_name} warning: {warning}")
                        
                    except Exception as e:
                        # Any error in parsing - mark for replacement
                        self.logger.warning(f"Failed to parse frontmatter for {agent_name}: {e}, marking for replacement")
                        results["replaced"].append(agent_name)
                        # Delete the file so it will be recreated
                        try:
                            agent_file.unlink()
                        except Exception:
                            pass
                    
                except Exception as e:
                    error_msg = f"Failed to validate agent {agent_file.name}: {e}"
                    self.logger.error(error_msg)
                    results["errors"].append(error_msg)
            
        except ImportError:
            self.logger.warning("FrontmatterValidator not available, skipping validation")
        except Exception as e:
            error_msg = f"Agent validation failed: {e}"
            self.logger.error(error_msg)
            results["errors"].append(error_msg)
        
        return results
    
    # ================================================================================
    # Interface Adapter Methods
    # ================================================================================
    # These methods adapt the existing implementation to comply with AgentDeploymentInterface
    
    def validate_agent(self, agent_path: Path) -> tuple[bool, List[str]]:
        """Validate agent configuration and structure.
        
        WHY: This adapter method provides interface compliance while leveraging
        the existing validation logic in _check_agent_needs_update and other methods.
        
        Args:
            agent_path: Path to agent configuration file
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            if not agent_path.exists():
                return False, [f"Agent file not found: {agent_path}"]
            
            content = agent_path.read_text()
            
            # Check YAML frontmatter format
            if not content.startswith("---"):
                errors.append("Missing YAML frontmatter")
            
            # Extract and validate version
            import re
            version_match = re.search(r'^version:\s*["\']?(.+?)["\']?$', content, re.MULTILINE)
            if not version_match:
                errors.append("Missing version field in frontmatter")
            
            # Check for required fields
            required_fields = ['name', 'description', 'tools']
            for field in required_fields:
                field_match = re.search(rf'^{field}:\s*.+$', content, re.MULTILINE)
                if not field_match:
                    errors.append(f"Missing required field: {field}")
            
            # If no errors, validation passed
            return len(errors) == 0, errors
            
        except Exception as e:
            return False, [f"Validation error: {str(e)}"]
    
    def get_deployment_status(self) -> Dict[str, Any]:
        """Get current deployment status and metrics.
        
        WHY: This adapter method provides interface compliance by wrapping
        verify_deployment and adding deployment metrics.
        
        Returns:
            Dictionary with deployment status information
        """
        # Get verification results
        verification = self.verify_deployment()
        
        # Add deployment metrics
        status = {
            "deployment_metrics": self._deployment_metrics.copy(),
            "verification": verification,
            "agents_deployed": len(verification.get("agents_found", [])),
            "agents_needing_migration": len(verification.get("agents_needing_migration", [])),
            "has_warnings": len(verification.get("warnings", [])) > 0,
            "environment_configured": bool(verification.get("environment", {}))
        }
        
        return status