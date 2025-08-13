"""Framework loader for Claude MPM."""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

from ..utils.imports import safe_import

# Import with fallback support - using absolute imports as primary since we're at module level
get_logger = safe_import('claude_mpm.core.logger', 'core.logger', ['get_logger'])
AgentRegistryAdapter = safe_import('claude_mpm.core.agent_registry', 'core.agent_registry', ['AgentRegistryAdapter'])


class FrameworkLoader:
    """
    Load and prepare framework instructions for injection.
    
    This component handles:
    1. Finding the framework (claude-multiagent-pm)
    2. Loading INSTRUCTIONS.md instructions
    3. Preparing agent definitions
    4. Formatting for injection
    """
    
    def __init__(self, framework_path: Optional[Path] = None, agents_dir: Optional[Path] = None):
        """
        Initialize framework loader.
        
        Args:
            framework_path: Explicit path to framework (auto-detected if None)
            agents_dir: Custom agents directory (overrides framework agents)
        """
        self.logger = get_logger("framework_loader")
        self.framework_path = framework_path or self._detect_framework_path()
        self.agents_dir = agents_dir
        self.framework_version = None
        self.framework_last_modified = None
        self.framework_content = self._load_framework_content()
        
        # Initialize agent registry
        self.agent_registry = AgentRegistryAdapter(self.framework_path)
        
    def _detect_framework_path(self) -> Optional[Path]:
        """Auto-detect claude-mpm framework."""
        # First check if we're in claude-mpm project
        current_file = Path(__file__)
        if "claude-mpm" in str(current_file):
            # We're running from claude-mpm, use its agents
            for parent in current_file.parents:
                if parent.name == "claude-mpm":
                    if (parent / "src" / "claude_mpm" / "agents").exists():
                        self.logger.info(f"Using claude-mpm at: {parent}")
                        return parent
                    break
        
        # Otherwise check common locations for claude-mpm
        candidates = [
            # Development location
            Path.home() / "Projects" / "claude-mpm",
            # Current directory
            Path.cwd() / "claude-mpm",
        ]
        
        for candidate in candidates:
            if candidate and candidate.exists():
                # Check for claude-mpm agents directory
                if (candidate / "src" / "claude_mpm" / "agents").exists():
                    self.logger.info(f"Found claude-mpm at: {candidate}")
                    return candidate
        
        self.logger.warning("Framework not found, will use minimal instructions")
        return None
    
    def _get_npm_global_path(self) -> Optional[Path]:
        """Get npm global installation path."""
        try:
            import subprocess
            result = subprocess.run(
                ["npm", "root", "-g"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                npm_root = Path(result.stdout.strip())
                return npm_root / "@bobmatnyc" / "claude-multiagent-pm"
        except:
            pass
        return None
    
    def _discover_framework_paths(self) -> tuple[Optional[Path], Optional[Path], Optional[Path]]:
        """
        Discover agent directories based on priority.
        
        Returns:
            Tuple of (agents_dir, templates_dir, main_dir)
        """
        agents_dir = None
        templates_dir = None
        main_dir = None
        
        if self.agents_dir and self.agents_dir.exists():
            agents_dir = self.agents_dir
            self.logger.info(f"Using custom agents directory: {agents_dir}")
        elif self.framework_path:
            # Prioritize templates directory over main agents directory
            templates_dir = self.framework_path / "src" / "claude_mpm" / "agents" / "templates"
            main_dir = self.framework_path / "src" / "claude_mpm" / "agents"
            
            if templates_dir.exists() and any(templates_dir.glob("*.md")):
                agents_dir = templates_dir
                self.logger.info(f"Using agents from templates directory: {agents_dir}")
            elif main_dir.exists() and any(main_dir.glob("*.md")):
                agents_dir = main_dir
                self.logger.info(f"Using agents from main directory: {agents_dir}")
                
        return agents_dir, templates_dir, main_dir
    
    def _try_load_file(self, file_path: Path, file_type: str) -> Optional[str]:
        """
        Try to load a file with error handling.
        
        Args:
            file_path: Path to the file to load
            file_type: Description of file type for logging
            
        Returns:
            File content if successful, None otherwise
        """
        try:
            content = file_path.read_text()
            if hasattr(self.logger, 'level') and self.logger.level <= logging.INFO:
                self.logger.info(f"Loaded {file_type} from: {file_path}")
            
            # Extract metadata if present
            import re
            version_match = re.search(r'<!-- FRAMEWORK_VERSION: (\d+) -->', content)
            if version_match:
                version = version_match.group(1)  # Keep as string to preserve leading zeros
                self.logger.info(f"Framework version: {version}")
                # Store framework version if this is the main INSTRUCTIONS.md
                if 'INSTRUCTIONS.md' in str(file_path):
                    self.framework_version = version
                    
            # Extract modification timestamp
            timestamp_match = re.search(r'<!-- LAST_MODIFIED: ([^>]+) -->', content)
            if timestamp_match:
                timestamp = timestamp_match.group(1).strip()
                self.logger.info(f"Last modified: {timestamp}")
                # Store timestamp if this is the main INSTRUCTIONS.md
                if 'INSTRUCTIONS.md' in str(file_path):
                    self.framework_last_modified = timestamp
            
            return content
        except Exception as e:
            if hasattr(self.logger, 'level') and self.logger.level <= logging.ERROR:
                self.logger.error(f"Failed to load {file_type}: {e}")
            return None
    
    def _load_instructions_file(self, content: Dict[str, Any]) -> None:
        """
        Load INSTRUCTIONS.md or legacy CLAUDE.md from working directory.
        
        Args:
            content: Dictionary to update with loaded instructions
        """
        working_instructions = Path.cwd() / "INSTRUCTIONS.md"
        working_claude = Path.cwd() / "CLAUDE.md"  # Legacy support
        
        if working_instructions.exists():
            loaded_content = self._try_load_file(working_instructions, "working directory INSTRUCTIONS.md")
            if loaded_content:
                content["working_claude_md"] = loaded_content
        elif working_claude.exists():
            # Legacy support for CLAUDE.md
            loaded_content = self._try_load_file(working_claude, "working directory CLAUDE.md (legacy)")
            if loaded_content:
                content["working_claude_md"] = loaded_content
    
    def _load_single_agent(self, agent_file: Path) -> tuple[Optional[str], Optional[str]]:
        """
        Load a single agent file.
        
        Args:
            agent_file: Path to the agent file
            
        Returns:
            Tuple of (agent_name, agent_content) or (None, None) on failure
        """
        try:
            agent_name = agent_file.stem
            # Skip README files
            if agent_name.upper() == "README":
                return None, None
            content = agent_file.read_text()
            self.logger.debug(f"Loaded agent: {agent_name}")
            return agent_name, content
        except Exception as e:
            self.logger.error(f"Failed to load agent {agent_file}: {e}")
            return None, None
    
    def _load_base_agent_fallback(self, content: Dict[str, Any], main_dir: Optional[Path]) -> None:
        """
        Load base_agent.md from main directory as fallback.
        
        Args:
            content: Dictionary to update with base agent
            main_dir: Main agents directory path
        """
        if main_dir and main_dir.exists() and "base_agent" not in content["agents"]:
            base_agent_file = main_dir / "base_agent.md"
            if base_agent_file.exists():
                agent_name, agent_content = self._load_single_agent(base_agent_file)
                if agent_name and agent_content:
                    content["agents"][agent_name] = agent_content
    
    def _load_agents_directory(self, content: Dict[str, Any], agents_dir: Optional[Path], 
                               templates_dir: Optional[Path], main_dir: Optional[Path]) -> None:
        """
        Load agent definitions from the appropriate directory.
        
        Args:
            content: Dictionary to update with loaded agents
            agents_dir: Primary agents directory to load from
            templates_dir: Templates directory path
            main_dir: Main agents directory path
        """
        if not agents_dir or not agents_dir.exists():
            return
            
        content["loaded"] = True
        
        # Load all agent files
        for agent_file in agents_dir.glob("*.md"):
            agent_name, agent_content = self._load_single_agent(agent_file)
            if agent_name and agent_content:
                content["agents"][agent_name] = agent_content
        
        # If we used templates dir, also check main dir for base_agent.md
        if agents_dir == templates_dir:
            self._load_base_agent_fallback(content, main_dir)
    
    def _load_framework_content(self) -> Dict[str, Any]:
        """Load framework content."""
        content = {
            "claude_md": "",
            "agents": {},
            "version": "unknown",
            "loaded": False,
            "working_claude_md": "",
            "framework_instructions": ""
        }
        
        # Load instructions file from working directory
        self._load_instructions_file(content)
        
        if not self.framework_path:
            return content
        
        # Load framework's INSTRUCTIONS.md
        framework_instructions_path = self.framework_path / "src" / "claude_mpm" / "agents" / "INSTRUCTIONS.md"
        if framework_instructions_path.exists():
            loaded_content = self._try_load_file(framework_instructions_path, "framework INSTRUCTIONS.md")
            if loaded_content:
                content["framework_instructions"] = loaded_content
                content["loaded"] = True
                # Add framework version to content
                if self.framework_version:
                    content["instructions_version"] = self.framework_version
                    content["version"] = self.framework_version  # Update main version key
                # Add modification timestamp to content
                if self.framework_last_modified:
                    content["instructions_last_modified"] = self.framework_last_modified
        
        # Load BASE_PM.md for core framework requirements
        base_pm_path = self.framework_path / "src" / "claude_mpm" / "agents" / "BASE_PM.md"
        if base_pm_path.exists():
            base_pm_content = self._try_load_file(base_pm_path, "BASE_PM framework requirements")
            if base_pm_content:
                content["base_pm_instructions"] = base_pm_content
        
        # Discover agent directories
        agents_dir, templates_dir, main_dir = self._discover_framework_paths()
        
        # Load agents from discovered directory
        self._load_agents_directory(content, agents_dir, templates_dir, main_dir)
        
        return content
    
    def get_framework_instructions(self) -> str:
        """
        Get formatted framework instructions for injection.
        
        Returns:
            Complete framework instructions ready for injection
        """
        if self.framework_content["loaded"] or self.framework_content["working_claude_md"]:
            # Build framework from components
            return self._format_full_framework()
        else:
            # Use minimal fallback
            return self._format_minimal_framework()
    
    def _format_full_framework(self) -> str:
        """Format full framework instructions."""
        from datetime import datetime
        
        # If we have the full framework INSTRUCTIONS.md, use it
        if self.framework_content.get("framework_instructions"):
            instructions = self.framework_content["framework_instructions"]
            
            # Add working directory instructions if they exist
            if self.framework_content["working_claude_md"]:
                instructions += f"\n\n## Working Directory Instructions\n{self.framework_content['working_claude_md']}\n"
            
            # Add dynamic agent capabilities section
            instructions += self._generate_agent_capabilities_section()
            
            # Add current date for temporal awareness
            instructions += f"\n\n## Temporal Context\n**Today's Date**: {datetime.now().strftime('%Y-%m-%d')}\n"
            instructions += "Apply date awareness to all time-sensitive tasks and decisions.\n"
            
            # Add BASE_PM.md framework requirements AFTER INSTRUCTIONS.md
            if self.framework_content.get("base_pm_instructions"):
                instructions += f"\n\n{self.framework_content['base_pm_instructions']}\n"
            
            return instructions
        
        # Otherwise fall back to generating framework
        instructions = f"""
<!-- Framework injected by Claude MPM -->
<!-- Version: {self.framework_content['version']} -->
<!-- Timestamp: {datetime.now().isoformat()} -->

# Claude MPM Framework Instructions

You are operating within the Claude Multi-Agent Project Manager (MPM) framework.

## Core Role
You are a multi-agent orchestrator. Your primary responsibilities are:
- Delegate all implementation work to specialized agents via Task Tool
- Coordinate multi-agent workflows and cross-agent collaboration
- Extract and track TODO/BUG/FEATURE items for ticket creation
- Maintain project visibility and strategic oversight
- NEVER perform direct implementation work yourself

"""
        
        # Add working directory INSTRUCTIONS.md (or CLAUDE.md) if exists
        if self.framework_content["working_claude_md"]:
            instructions += f"""
## Working Directory Instructions
{self.framework_content["working_claude_md"]}

"""
        
        # Add agent definitions
        if self.framework_content["agents"]:
            instructions += "## Available Agents\n\n"
            instructions += "You have the following specialized agents available for delegation:\n\n"
            
            # List agents with brief descriptions and correct IDs
            agent_list = []
            for agent_name in sorted(self.framework_content["agents"].keys()):
                # Use the actual agent_name as the ID (it's the filename stem)
                agent_id = agent_name
                clean_name = agent_name.replace('-', ' ').replace('_', ' ').title()
                if 'engineer' in agent_name.lower() and 'data' not in agent_name.lower():
                    agent_list.append(f"- **Engineer Agent** (`{agent_id}`): Code implementation and development")
                elif 'qa' in agent_name.lower():
                    agent_list.append(f"- **QA Agent** (`{agent_id}`): Testing and quality assurance")
                elif 'documentation' in agent_name.lower():
                    agent_list.append(f"- **Documentation Agent** (`{agent_id}`): Documentation creation and maintenance")
                elif 'research' in agent_name.lower():
                    agent_list.append(f"- **Research Agent** (`{agent_id}`): Investigation and analysis")
                elif 'security' in agent_name.lower():
                    agent_list.append(f"- **Security Agent** (`{agent_id}`): Security analysis and protection")
                elif 'version' in agent_name.lower():
                    agent_list.append(f"- **Version Control Agent** (`{agent_id}`): Git operations and version management")
                elif 'ops' in agent_name.lower():
                    agent_list.append(f"- **Ops Agent** (`{agent_id}`): Deployment and operations")
                elif 'data' in agent_name.lower():
                    agent_list.append(f"- **Data Engineer Agent** (`{agent_id}`): Data management and AI API integration")
                else:
                    agent_list.append(f"- **{clean_name}** (`{agent_id}`): Available for specialized tasks")
            
            instructions += "\n".join(agent_list) + "\n\n"
            
            # Add full agent details
            instructions += "### Agent Details\n\n"
            for agent_name, agent_content in sorted(self.framework_content["agents"].items()):
                instructions += f"#### {agent_name.replace('-', ' ').title()}\n"
                instructions += agent_content + "\n\n"
        
        # Add orchestration principles
        instructions += """
## Orchestration Principles
1. **Always Delegate**: Never perform direct work - use Task Tool for all implementation
2. **Comprehensive Context**: Provide rich, filtered context to each agent
3. **Track Everything**: Extract all TODO/BUG/FEATURE items systematically
4. **Cross-Agent Coordination**: Orchestrate workflows spanning multiple agents
5. **Results Integration**: Actively receive and integrate agent results

## Task Tool Format
```
**[Agent Name]**: [Clear task description with deliverables]

TEMPORAL CONTEXT: Today is [date]. Apply date awareness to [specific considerations].

**Task**: [Detailed task breakdown]
1. [Specific action item 1]
2. [Specific action item 2]
3. [Specific action item 3]

**Context**: [Comprehensive filtered context for this agent]
**Authority**: [Agent's decision-making scope]
**Expected Results**: [Specific deliverables needed]
**Integration**: [How results integrate with other work]
```

## Ticket Extraction Patterns
Extract tickets from these patterns:
- TODO: [description] → TODO ticket
- BUG: [description] → BUG ticket
- FEATURE: [description] → FEATURE ticket
- ISSUE: [description] → ISSUE ticket
- FIXME: [description] → BUG ticket

---
"""
        
        return instructions
    
    def _generate_agent_capabilities_section(self) -> str:
        """Generate dynamic agent capabilities section from deployed agents."""
        try:
            from pathlib import Path
            import yaml
            
            # Read directly from deployed agents in .claude/agents/
            # This ensures we show the exact agent IDs that work with the Task tool
            agents_dir = Path.cwd() / ".claude" / "agents"
            
            if not agents_dir.exists():
                self.logger.warning("No .claude/agents directory found")
                return self._get_fallback_capabilities()
            
            # Build capabilities section
            section = "\n\n## Available Agent Capabilities\n\n"
            section += "You have the following specialized agents available for delegation:\n\n"
            
            # Collect deployed agents
            deployed_agents = []
            for agent_file in agents_dir.glob("*.md"):
                # Skip hidden files and system files
                if agent_file.name.startswith('.'):
                    continue
                    
                # The agent ID is the filename without extension
                # This is what the Task tool expects
                agent_id = agent_file.stem
                
                # Try to read agent metadata from frontmatter
                agent_name = agent_id.replace('_', ' ').title()
                agent_desc = "Specialized agent"
                
                try:
                    with open(agent_file, 'r') as f:
                        content = f.read()
                        # Extract YAML frontmatter if present
                        if content.startswith('---'):
                            end_marker = content.find('---', 3)
                            if end_marker > 0:
                                frontmatter = content[3:end_marker]
                                metadata = yaml.safe_load(frontmatter)
                                if metadata:
                                    agent_name = metadata.get('name', agent_name)
                                    agent_desc = metadata.get('description', agent_desc)
                except Exception as e:
                    self.logger.debug(f"Could not read metadata from {agent_file}: {e}")
                
                deployed_agents.append((agent_id, agent_name, agent_desc))
            
            if not deployed_agents:
                return self._get_fallback_capabilities()
            
            # Sort agents and display them
            deployed_agents.sort(key=lambda x: x[0])
            
            # Group common agent types
            core_agents = []
            other_agents = []
            
            core_types = ['engineer', 'research', 'qa', 'documentation', 'security', 
                         'data_engineer', 'ops', 'version_control']
            
            for agent_id, name, desc in deployed_agents:
                if agent_id in core_types:
                    core_agents.append((agent_id, name, desc))
                else:
                    other_agents.append((agent_id, name, desc))
            
            # Display core agents first
            if core_agents:
                section += "### Engineering Agents\n"
                for agent_id, name, desc in core_agents:
                    # Format: Name (agent_id) - use Name for TodoWrite, agent_id for Task tool
                    clean_name = name.replace(' Agent', '').replace('-', ' ')
                    section += f"- **{clean_name}** (`{agent_id}`): {desc}\n"
            
            # Display other/custom agents
            if other_agents:
                section += "\n### Research Agents\n"
                for agent_id, name, desc in other_agents:
                    clean_name = name.replace(' Agent', '').replace('-', ' ')
                    section += f"- **{clean_name}** (`{agent_id}`): {desc}\n"
            
            # Add summary and usage instructions
            section += f"\n**Total Available Agents**: {len(deployed_agents)}\n"
            section += "Use the agent ID in parentheses when delegating tasks via the Task tool.\n"
            
            return section
            
        except Exception as e:
            self.logger.warning(f"Could not generate dynamic agent capabilities: {e}")
            return self._get_fallback_capabilities()
    
    def _get_fallback_capabilities(self) -> str:
        """Return fallback capabilities when dynamic discovery fails."""
        return """

## Available Agent Capabilities

You have the following specialized agents available for delegation:

- **Engineer** (`engineer`): Code implementation and development
- **Research** (`research`): Investigation and analysis  
- **QA** (`qa`): Testing and quality assurance
- **Documentation** (`documentation`): Documentation creation and maintenance
- **Security** (`security`): Security analysis and protection
- **Data Engineer** (`data_engineer`): Data management and pipelines
- **Ops** (`ops`): Deployment and operations
- **Version Control** (`version_control`): Git operations and version management

**IMPORTANT**: Use the exact agent ID in parentheses when delegating tasks.
"""
    
    def _format_minimal_framework(self) -> str:
        """Format minimal framework instructions when full framework not available."""
        return """
# Claude PM Framework Instructions

You are operating within a Claude PM Framework deployment.

## Role
You are a multi-agent orchestrator. Your primary responsibilities:
- Delegate tasks to specialized agents via Task Tool
- Coordinate multi-agent workflows
- Extract TODO/BUG/FEATURE items for ticket creation
- NEVER perform direct implementation work

## Core Agents
- Documentation Agent - Documentation tasks
- Engineer Agent - Code implementation  
- QA Agent - Testing and validation
- Research Agent - Investigation and analysis
- Version Control Agent - Git operations

## Important Rules
1. Always delegate work via Task Tool
2. Provide comprehensive context to agents
3. Track all TODO/BUG/FEATURE items
4. Maintain project visibility

---
"""
    
    def get_agent_list(self) -> list:
        """Get list of available agents."""
        # First try agent registry
        if self.agent_registry:
            agents = self.agent_registry.list_agents()
            if agents:
                return list(agents.keys())
        
        # Fallback to loaded content
        return list(self.framework_content["agents"].keys())
    
    def get_agent_definition(self, agent_name: str) -> Optional[str]:
        """Get specific agent definition."""
        # First try agent registry
        if self.agent_registry:
            definition = self.agent_registry.get_agent_definition(agent_name)
            if definition:
                return definition
        
        # Fallback to loaded content
        return self.framework_content["agents"].get(agent_name)
    
    def get_agent_hierarchy(self) -> Dict[str, list]:
        """Get agent hierarchy from registry."""
        if self.agent_registry:
            return self.agent_registry.get_agent_hierarchy()
        return {'project': [], 'user': [], 'system': []}