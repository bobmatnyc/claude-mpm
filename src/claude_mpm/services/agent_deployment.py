"""Agent deployment service for Claude Code native subagents."""

import os
import shutil
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from claude_mpm.core.logger import get_logger
from claude_mpm.constants import EnvironmentVars, Paths, AgentMetadata


class AgentDeploymentService:
    """Service for deploying Claude Code native agents."""
    
    def __init__(self, templates_dir: Optional[Path] = None, base_agent_path: Optional[Path] = None):
        """
        Initialize agent deployment service.
        
        Args:
            templates_dir: Directory containing agent template files
            base_agent_path: Path to base_agent.md file
        """
        self.logger = get_logger(self.__class__.__name__)
        
        # Find templates directory
        module_path = Path(__file__).parent.parent
        if templates_dir:
            self.templates_dir = Path(templates_dir)
        else:
            # Default to src/claude_mpm/agents/templates/
            self.templates_dir = module_path / "agents" / "templates"
        
        # Find base agent file
        if base_agent_path:
            self.base_agent_path = Path(base_agent_path)
        else:
            # Default to src/claude_mpm/agents/base_agent.json
            self.base_agent_path = module_path / "agents" / "base_agent.json"
        
        self.logger.info(f"Templates directory: {self.templates_dir}")
        self.logger.info(f"Base agent path: {self.base_agent_path}")
        
    def deploy_agents(self, target_dir: Optional[Path] = None, force_rebuild: bool = False) -> Dict[str, Any]:
        """
        Build and deploy agents by combining base_agent.md with templates.
        Also deploys system instructions for PM framework.
        
        Args:
            target_dir: Target directory for agents (default: .claude/agents/)
            force_rebuild: Force rebuild even if agents exist
            
        Returns:
            Dictionary with deployment results
        """
        if not target_dir:
            target_dir = Path(Paths.CLAUDE_AGENTS_DIR.value).expanduser()
        
        target_dir = Path(target_dir)
        results = {
            "target_dir": str(target_dir),
            "deployed": [],
            "errors": [],
            "skipped": [],
            "updated": [],
            "migrated": [],  # Track agents migrated from old format
            "total": 0
        }
        
        try:
            # Create target directory if needed
            target_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Building and deploying agents to: {target_dir}")
            
            # Note: System instructions are now loaded directly by SimpleClaudeRunner
            
            # Check if templates directory exists
            if not self.templates_dir.exists():
                error_msg = f"Templates directory not found: {self.templates_dir}"
                self.logger.error(error_msg)
                results["errors"].append(error_msg)
                return results
            
            # Load base agent content
            base_agent_data = {}
            base_agent_version = 0
            if self.base_agent_path.exists():
                try:
                    import json
                    base_agent_data = json.loads(self.base_agent_path.read_text())
                    # Handle both 'base_version' (new format) and 'version' (old format)
                    base_agent_version = self._parse_version(base_agent_data.get('base_version') or base_agent_data.get('version', 0))
                    self.logger.info(f"Loaded base agent template (version {self._format_version_display(base_agent_version)})")
                except Exception as e:
                    self.logger.warning(f"Could not load base agent: {e}")
            
            # Get all template files
            template_files = list(self.templates_dir.glob("*.json"))
            # Filter out non-agent files
            template_files = [f for f in template_files if f.stem != "__init__" and not f.stem.startswith(".")]
            results["total"] = len(template_files)
            
            for template_file in template_files:
                try:
                    agent_name = template_file.stem
                    target_file = target_dir / f"{agent_name}.md"
                    
                    # Check if agent needs update
                    needs_update = force_rebuild
                    is_migration = False
                    if not needs_update and target_file.exists():
                        needs_update, reason = self._check_agent_needs_update(
                            target_file, template_file, base_agent_version
                        )
                        if needs_update:
                            # Check if this is a migration from old format
                            if "migration needed" in reason:
                                is_migration = True
                                self.logger.info(f"Migrating agent {agent_name}: {reason}")
                            else:
                                self.logger.info(f"Agent {agent_name} needs update: {reason}")
                    
                    # Skip if exists and doesn't need update
                    if target_file.exists() and not needs_update:
                        results["skipped"].append(agent_name)
                        self.logger.debug(f"Skipped up-to-date agent: {agent_name}")
                        continue
                    
                    # Build the agent file
                    agent_md = self._build_agent_markdown(agent_name, template_file, base_agent_data)
                    
                    # Write the agent file
                    is_update = target_file.exists()
                    target_file.write_text(agent_md)
                    
                    if is_migration:
                        results["migrated"].append({
                            "name": agent_name,
                            "template": str(template_file),
                            "target": str(target_file),
                            "reason": reason
                        })
                        self.logger.info(f"Successfully migrated agent: {agent_name} to semantic versioning")
                    elif is_update:
                        results["updated"].append({
                            "name": agent_name,
                            "template": str(template_file),
                            "target": str(target_file)
                        })
                        self.logger.debug(f"Updated agent: {agent_name}")
                    else:
                        results["deployed"].append({
                            "name": agent_name,
                            "template": str(template_file),
                            "target": str(target_file)
                        })
                        self.logger.debug(f"Built and deployed agent: {agent_name}")
                    
                except Exception as e:
                    error_msg = f"Failed to build {template_file.name}: {e}"
                    self.logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            self.logger.info(
                f"Deployed {len(results['deployed'])} agents, "
                f"updated {len(results['updated'])}, "
                f"migrated {len(results['migrated'])}, "
                f"skipped {len(results['skipped'])}, "
                f"errors: {len(results['errors'])}"
            )
            
        except Exception as e:
            error_msg = f"Agent deployment failed: {e}"
            self.logger.error(error_msg)
            results["errors"].append(error_msg)
        
        return results
    
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
        description = (
            template_data.get('configuration_fields', {}).get('description') or
            template_data.get('description') or
            'Agent for specialized tasks'
        )
        
        tags = (
            template_data.get('configuration_fields', {}).get('tags') or
            template_data.get('tags') or
            [agent_name, 'mpm-framework']
        )
        
        frontmatter = f"""---
name: {agent_name}
description: "{description}"
version: "{version_string}"
author: "{template_data.get('author', 'claude-mpm@anthropic.com')}"
created: "{datetime.now().isoformat()}Z"
updated: "{datetime.now().isoformat()}Z"
tags: {tags}
metadata:
  base_version: "{self._format_version_display(base_version)}"
  agent_version: "{self._format_version_display(agent_version)}"
  deployment_type: "system"
---

"""
        
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
        
        Args:
            agent_name: Name of the agent
            template_path: Path to the agent template JSON file
            base_agent_data: Base agent data from JSON
            
        Returns:
            Complete agent YAML content
        """
        import json
        from datetime import datetime
        
        # Read template JSON
        template_data = json.loads(template_path.read_text())
        
        # Extract versions
        # Handle both 'agent_version' (new format) and 'version' (old format)
        agent_version = self._parse_version(template_data.get('agent_version') or template_data.get('version', 0))
        base_version = self._parse_version(base_agent_data.get('base_version') or base_agent_data.get('version', 0))
        
        # Use semantic version format
        version_string = self._format_version_display(agent_version)
        
        # Merge narrative fields (base + agent specific)
        narrative_fields = self._merge_narrative_fields(base_agent_data, template_data)
        
        # Merge configuration fields (agent overrides base)
        config_fields = self._merge_configuration_fields(base_agent_data, template_data)
        
        # Build YAML frontmatter following best practices
        yaml_content = f"""---
# Core Identity
name: "{agent_name}"
description: "{config_fields.get('description', '')}"
version: "{version_string}"
author: "claude-mpm@anthropic.com"
created: "{datetime.now().isoformat()}Z"
updated: "{datetime.now().isoformat()}Z"

# Categorization
tags: {config_fields.get('tags', [])}
team: "{config_fields.get('team', 'mpm-framework')}"
project: "{config_fields.get('project', 'claude-mpm')}"
priority: "{config_fields.get('priority', 'high')}"

# Behavioral Configuration
tools: {config_fields.get('tools', [])}
timeout: {config_fields.get('timeout', 600)}
max_tokens: {config_fields.get('max_tokens', 8192)}
model: "{config_fields.get('model', 'claude-3-5-sonnet-20241022')}"
temperature: {config_fields.get('temperature', 0.3)}

# Access Control
file_access: "{config_fields.get('file_access', 'project')}"
network_access: {str(config_fields.get('network_access', True)).lower()}
dangerous_tools: {str(config_fields.get('dangerous_tools', False)).lower()}
review_required: {str(config_fields.get('review_required', False)).lower()}

# Resource Management
memory_limit: {config_fields.get('memory_limit', 2048)}
cpu_limit: {config_fields.get('cpu_limit', 50)}
execution_timeout: {config_fields.get('timeout', 600)}

# When/Why/What sections extracted from template
when_to_use:
{self._format_yaml_list(narrative_fields.get('when_to_use', []), 2)}

rationale:
  specialized_knowledge:
{self._format_yaml_list(narrative_fields.get('specialized_knowledge', []), 4)}
  unique_capabilities:
{self._format_yaml_list(narrative_fields.get('unique_capabilities', []), 4)}

capabilities:
  primary_role: "{config_fields.get('primary_role', '')}"
  specializations: {config_fields.get('specializations', [])}
  authority: "{config_fields.get('authority', '')}"

# Agent Metadata
metadata:
  source: "claude-mpm"
  template_version: "{self._format_version_display(agent_version)}"
  base_version: "{self._format_version_display(base_version)}"
  deployment_type: "system"
  
...
---

# System Prompt

"""
        
        # Add combined instructions
        combined_instructions = narrative_fields.get('instructions', '')
        if combined_instructions:
            yaml_content += combined_instructions
        
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
        
        return merged
    
    def set_claude_environment(self, config_dir: Optional[Path] = None) -> Dict[str, str]:
        """
        Set Claude environment variables for agent discovery.
        
        Args:
            config_dir: Claude configuration directory (default: .claude/)
            
        Returns:
            Dictionary of environment variables set
        """
        if not config_dir:
            config_dir = Path.cwd() / Paths.CLAUDE_CONFIG_DIR.value
        
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
        
        Args:
            config_dir: Claude configuration directory (default: .claude/)
            
        Returns:
            Verification results
        """
        if not config_dir:
            config_dir = Path.cwd() / ".claude"
        
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
        for agent_file in agent_files:
            try:
                # Read first few lines to get agent name from YAML
                with open(agent_file, 'r') as f:
                    lines = f.readlines()[:10]
                    
                agent_info = {
                    "file": agent_file.name,
                    "path": str(agent_file)
                }
                
                # Extract name and version from YAML frontmatter
                version_str = None
                for line in lines:
                    if line.startswith("name:"):
                        agent_info["name"] = line.split(":", 1)[1].strip().strip('"\'')
                    elif line.startswith("version:"):
                        version_str = line.split(":", 1)[1].strip().strip('"\'')
                        agent_info["version"] = version_str
                
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
    
    def list_available_agents(self) -> List[Dict[str, Any]]:
        """
        List available agent templates.
        
        Returns:
            List of agent information dictionaries
        """
        agents = []
        
        if not self.templates_dir.exists():
            self.logger.warning(f"Templates directory not found: {self.templates_dir}")
            return agents
        
        template_files = sorted(self.templates_dir.glob("*.json"))
        # Filter out non-agent files
        template_files = [f for f in template_files if f.stem != "__init__" and not f.stem.startswith(".")]
        
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
        
        Args:
            deployed_file: Path to the deployed agent file
            template_file: Path to the template file
            current_base_version: Current base agent version
            
        Returns:
            Tuple of (needs_update, reason)
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
            config_dir = Path.cwd() / ".claude"
        
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
            'timeout': 600,
            'max_tokens': 8192,
            'memory_limit': 2048,
            'cpu_limit': 50,
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
        Deploy system instructions for PM framework.
        
        Args:
            target_dir: Target directory for deployment
            force_rebuild: Force rebuild even if exists
            results: Results dictionary to update
        """
        try:
            # Find the INSTRUCTIONS.md file
            module_path = Path(__file__).parent.parent
            instructions_path = module_path / "agents" / "INSTRUCTIONS.md"
            
            if not instructions_path.exists():
                self.logger.warning(f"System instructions not found: {instructions_path}")
                return
            
            # Target file for system instructions - use CLAUDE.md in user's home .claude directory
            target_file = Path("~/.claude/CLAUDE.md").expanduser()
            
            # Ensure .claude directory exists
            target_file.parent.mkdir(exist_ok=True)
            
            # Check if update needed
            if not force_rebuild and target_file.exists():
                # Compare modification times
                if target_file.stat().st_mtime >= instructions_path.stat().st_mtime:
                    results["skipped"].append("CLAUDE.md")
                    self.logger.debug("System instructions up to date")
                    return
            
            # Read and deploy system instructions
            instructions_content = instructions_path.read_text()
            target_file.write_text(instructions_content)
            
            is_update = target_file.exists()
            if is_update:
                results["updated"].append({
                    "name": "CLAUDE.md", 
                    "template": str(instructions_path),
                    "target": str(target_file)
                })
                self.logger.info("Updated system instructions")
            else:
                results["deployed"].append({
                    "name": "CLAUDE.md",
                    "template": str(instructions_path), 
                    "target": str(target_file)
                })
                self.logger.info("Deployed system instructions")
                
        except Exception as e:
            error_msg = f"Failed to deploy system instructions: {e}"
            self.logger.error(error_msg)
            results["errors"].append(error_msg)