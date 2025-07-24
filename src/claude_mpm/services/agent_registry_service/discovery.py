"""
Agent Discovery Module
Handles agent file discovery and metadata extraction

Created: 2025-07-19
Purpose: Agent discovery and scanning functionality
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from .metadata import AgentMetadata
from .utils import (
    determine_tier, has_tier_precedence, AGENT_ROLE_MAPPINGS,
    FRAMEWORK_PATTERNS, ROLE_PATTERNS, DOMAIN_KEYWORDS,
    extract_specialized_metadata, detect_hybrid_agent, 
    assess_complexity_level, parse_explicit_model_config
)

logger = logging.getLogger(__name__)


class AgentDiscovery:
    """Handles agent discovery and metadata extraction"""
    
    def __init__(self, model_selector=None):
        self.model_selector = model_selector
    
    def initialize_discovery_paths(self) -> List[Path]:
        """Initialize agent discovery paths with two-tier hierarchy"""
        paths = []
        
        # Current directory → parent directories scanning
        current_path = Path.cwd()
        while current_path.parent != current_path:  # Until we reach root
            claude_pm_dir = current_path / '.claude-pm' / 'agents'
            if claude_pm_dir.exists():
                paths.append(claude_pm_dir)
            current_path = current_path.parent
        
        # User directory agents
        user_home = Path.home()
        user_agents_dir = user_home / '.claude-pm' / 'agents' / 'user'
        if user_agents_dir.exists():
            paths.append(user_agents_dir)
        
        # System agents - look for framework/agent-roles directory
        try:
            import claude_pm
            package_path = Path(claude_pm.__file__).parent
            path_str = str(package_path.resolve())
            is_wheel_install = 'site-packages' in path_str or 'dist-packages' in path_str
            
            if is_wheel_install:
                # For wheel installations, check data directory
                data_agent_roles = package_path / 'data' / 'framework' / 'agent-roles'
                if data_agent_roles.exists():
                    paths.append(data_agent_roles)
                    logger.debug(f"Found framework agent-roles in data directory: {data_agent_roles}")
                else:
                    # Fallback to legacy location
                    framework_base = package_path.parent
                    agent_roles_path = framework_base / 'framework' / 'agent-roles'
                    if agent_roles_path.exists():
                        paths.append(agent_roles_path)
                        logger.debug(f"Found framework agent-roles directory: {agent_roles_path}")
            else:
                # Source installation
                framework_base = package_path.parent
                agent_roles_path = framework_base / 'framework' / 'agent-roles'
                if agent_roles_path.exists():
                    paths.append(agent_roles_path)
                    logger.debug(f"Found framework agent-roles directory: {agent_roles_path}")
            
            # Also check for Python agents in the module
            framework_path = package_path / 'agents'
            if framework_path.exists():
                paths.append(framework_path)
        except ImportError:
            logger.warning("Claude PM framework not available for system agent discovery")
        
        logger.info(f"Initialized discovery paths: {[str(p) for p in paths]}")
        return paths
    
    def scan_directory(self, directory: Path, tier: str) -> Dict[str, AgentMetadata]:
        """
        Scan directory for agent files and extract metadata
        
        Args:
            directory: Directory path to scan
            tier: Hierarchy tier ('user' or 'system')
            
        Returns:
            Dictionary of discovered agents
        """
        agents = {}
        
        if not directory.exists():
            return agents
        
        logger.debug(f"Scanning directory: {directory} (tier: {tier})")
        
        # Scan for markdown agent files (changed from Python files)
        for agent_file in directory.rglob("*.md"):
            # Skip template files and backup files
            if agent_file.name in ['AGENT_TEMPLATE.md', 'base_agent.md'] or '.backup' in agent_file.name:
                continue
            
            # Skip non-agent markdown files
            if not agent_file.name.endswith('-agent.md'):
                continue
            
            try:
                agent_metadata = self.extract_agent_metadata(agent_file, tier)
                if agent_metadata:
                    agents[agent_metadata.name] = agent_metadata
            except Exception as e:
                logger.warning(f"Error processing agent file {agent_file}: {e}")
        
        return agents
    
    def extract_agent_metadata(self, agent_file: Path, tier: str) -> Optional[AgentMetadata]:
        """
        Extract metadata from agent file
        
        Args:
            agent_file: Path to agent file
            tier: Hierarchy tier
            
        Returns:
            AgentMetadata or None if extraction fails
        """
        try:
            # Get file stats
            stat = agent_file.stat()
            file_size = stat.st_size
            last_modified = stat.st_mtime
            
            # Determine agent name and type from filename
            # e.g., "documentation-agent.md" -> name: "documentation-agent", type: "documentation"
            agent_name = agent_file.stem
            from .classification import classify_agent_type
            agent_type = classify_agent_type(agent_name, agent_file)
            
            # Read file for additional metadata - now handles markdown
            description, version, capabilities = self.parse_agent_file(agent_file)
            
            # Enhanced metadata extraction for ISS-0118
            specializations, frameworks, domains, roles = extract_specialized_metadata(capabilities)
            is_hybrid, hybrid_types = detect_hybrid_agent(agent_type, specializations)
            complexity_level = assess_complexity_level(capabilities, specializations)
            
            # Extract model configuration from agent file
            preferred_model, model_config = self.extract_model_configuration(
                agent_file, agent_type, complexity_level
            )
            
            return AgentMetadata(
                name=agent_name,
                type=agent_type,
                path=str(agent_file),
                tier=tier,
                description=description,
                version=version,
                capabilities=capabilities,
                last_modified=last_modified,
                file_size=file_size,
                validated=False,  # Will be validated later
                specializations=specializations,
                frameworks=frameworks,
                domains=domains,
                roles=roles,
                is_hybrid=is_hybrid,
                hybrid_types=hybrid_types,
                complexity_level=complexity_level,
                preferred_model=preferred_model,
                model_config=model_config
            )
            
        except Exception as e:
            logger.error(f"Failed to extract metadata from {agent_file}: {e}")
            return None
    
    def parse_agent_file(self, agent_file: Path) -> Tuple[Optional[str], Optional[str], List[str]]:
        """
        Parse markdown agent file to extract metadata.
        Extracts description, capabilities, and other metadata from markdown structure.
        
        Args:
            agent_file: Path to agent markdown file
            
        Returns:
            Tuple of (description, version, capabilities)
        """
        description = None
        version = None
        capabilities = []
        
        try:
            content = agent_file.read_text(encoding='utf-8')
            lines = content.split('\n')
            
            # Extract description from Primary Role section
            in_primary_role = False
            for i, line in enumerate(lines):
                if line.strip() == "## 🎯 Primary Role":
                    in_primary_role = True
                    # Get next non-empty line as description
                    for j in range(i+1, min(i+5, len(lines))):
                        desc_line = lines[j].strip()
                        if desc_line and not desc_line.startswith('#'):
                            description = desc_line
                            break
                    break
            
            # Extract capabilities from Core Capabilities section
            in_capabilities = False
            for line in lines:
                if line.strip() == "## 🔧 Core Capabilities":
                    in_capabilities = True
                    continue
                elif in_capabilities and line.startswith('## '):
                    # End of capabilities section
                    break
                elif in_capabilities and line.strip().startswith('- **'):
                    # Extract capability name from bold text
                    cap_match = line.strip()[4:].split('**')[0]
                    if cap_match:
                        capabilities.append(f"capability:{cap_match}")
            
            # Extract specializations from content
            content_lower = content.lower()
            
            # Look for specialization keywords
            specialization_patterns = {
                'changelog': 'specialization:changelog_generation',
                'release notes': 'specialization:release_documentation',
                'documentation pattern': 'specialization:documentation_analysis',
                'api documentation': 'specialization:api_documentation',
                'security': 'specialization:security_analysis',
                'testing': 'specialization:quality_assurance',
                'research': 'specialization:technical_research',
                'version control': 'specialization:git_operations',
                'ticketing': 'specialization:issue_tracking',
                'data': 'specialization:data_management',
                'engineer': 'specialization:code_implementation',
                'ops': 'specialization:deployment_operations'
            }
            
            # Extract specializations based on content and agent type
            agent_stem = agent_file.stem.lower()
            for pattern, capability in specialization_patterns.items():
                if pattern in content_lower:
                    # Add specialization if pattern found in content
                    capabilities.append(capability)
                elif pattern.replace(' ', '-') in agent_stem:
                    # Also check if pattern matches agent filename
                    capabilities.append(capability)
            
            # Extract frameworks mentioned
            for framework, patterns in FRAMEWORK_PATTERNS.items():
                for pattern in patterns:
                    if pattern in content_lower:
                        capabilities.append(f'framework:{framework}')
                        break
            
            # Extract domain capabilities
            if 'devops' in content_lower or 'ci/cd' in content_lower:
                capabilities.append('domain:devops')
            if 'security' in content_lower:
                capabilities.append('domain:security')
            if 'documentation' in content_lower:
                capabilities.append('domain:documentation')
            if 'testing' in content_lower or 'quality' in content_lower:
                capabilities.append('domain:quality_assurance')
            
            # Extract role capabilities based on agent type
            if agent_file.stem in AGENT_ROLE_MAPPINGS:
                capabilities.append(AGENT_ROLE_MAPPINGS[agent_file.stem])
            
            # Default version for markdown agents
            version = "1.0.0"
            
        except Exception as e:
            logger.warning(f"Error parsing agent file {agent_file}: {e}")
        
        return description, version, capabilities
    
    def extract_model_configuration(
        self, 
        agent_file: Path, 
        agent_type: str, 
        complexity_level: str
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Extract model configuration from agent file and apply intelligent selection.
        
        Args:
            agent_file: Path to agent file
            agent_type: Agent type classification
            complexity_level: Assessed complexity level
            
        Returns:
            Tuple of (preferred_model, model_config)
        """
        try:
            # Check for explicit model configuration in agent file
            content = agent_file.read_text(encoding='utf-8')
            preferred_model = None
            model_config = {}
            
            # Parse explicit model preferences from agent file
            explicit_model = parse_explicit_model_config(content)
            if explicit_model:
                preferred_model = explicit_model["model_id"]
                model_config = explicit_model.get("config", {})
                logger.debug(f"Found explicit model configuration in {agent_file.name}: {preferred_model}")
            
            # If no explicit configuration and we have a model selector, use intelligent selection
            if not preferred_model and self.model_selector:
                from claude_pm.services.model_selector import ModelSelectionCriteria
                
                # Create selection criteria based on agent analysis
                criteria = ModelSelectionCriteria(
                    agent_type=agent_type,
                    task_complexity=complexity_level,
                    performance_requirements=self._analyze_performance_requirements(content),
                    reasoning_depth_required=self._analyze_reasoning_requirements(content, agent_type),
                    creativity_required=self._analyze_creativity_requirements(content),
                    speed_priority=self._analyze_speed_requirements(content)
                )
                
                # Select model using ModelSelector
                model_type, model_configuration = self.model_selector.select_model_for_agent(
                    agent_type, criteria
                )
                
                preferred_model = model_type.value
                model_config = {
                    "max_tokens": model_configuration.max_tokens,
                    "context_window": model_configuration.context_window,
                    "selection_criteria": {
                        "task_complexity": criteria.task_complexity,
                        "reasoning_depth": criteria.reasoning_depth_required,
                        "speed_priority": criteria.speed_priority,
                        "creativity_required": criteria.creativity_required
                    },
                    "capabilities": model_configuration.capabilities,
                    "performance_profile": model_configuration.performance_profile,
                    "auto_selected": True
                }
                
                logger.debug(f"Auto-selected model for {agent_type}: {preferred_model}")
            
            return preferred_model, model_config
            
        except Exception as e:
            logger.warning(f"Error extracting model configuration from {agent_file}: {e}")
            # Fallback to default model selection
            try:
                if self.model_selector:
                    model_type, model_configuration = self.model_selector.select_model_for_agent(agent_type)
                    return model_type.value, {
                        "max_tokens": model_configuration.max_tokens,
                        "fallback_selection": True,
                        "error": str(e)
                    }
            except Exception as fallback_error:
                logger.error(f"Fallback model selection failed: {fallback_error}")
            return None, {"error": str(e)}
    
    def _analyze_performance_requirements(self, content: str) -> Dict[str, Any]:
        """Analyze performance requirements from agent file content."""
        requirements = {}
        content_lower = content.lower()
        
        # Speed requirements
        if any(keyword in content_lower for keyword in ['fast', 'quick', 'rapid', 'immediate']):
            requirements["speed_priority"] = True
        
        # Quality requirements  
        if any(keyword in content_lower for keyword in ['quality', 'accurate', 'precise', 'detailed']):
            requirements["quality_priority"] = True
            
        # Resource constraints
        if any(keyword in content_lower for keyword in ['efficient', 'lightweight', 'minimal']):
            requirements["resource_efficiency"] = True
            
        return requirements
    
    def _analyze_reasoning_requirements(self, content: str, agent_type: str) -> str:
        """Analyze reasoning depth requirements from content and agent type."""
        content_lower = content.lower()
        
        # Expert reasoning indicators
        if any(keyword in content_lower for keyword in [
            'architecture', 'design pattern', 'complex system', 'optimization',
            'strategic', 'planning', 'analysis', 'research'
        ]):
            return "expert"
        
        # Deep reasoning indicators
        if any(keyword in content_lower for keyword in [
            'investigate', 'analyze', 'evaluate', 'assess', 'compare'
        ]):
            return "deep"
        
        # Simple reasoning indicators
        if any(keyword in content_lower for keyword in [
            'format', 'display', 'show', 'list', 'basic'
        ]):
            return "simple"
        
        # Agent type-based defaults
        if agent_type in ['engineer', 'architecture', 'orchestrator']:
            return "expert"
        elif agent_type in ['research', 'analysis', 'qa']:
            return "deep"
        else:
            return "standard"
    
    def _analyze_creativity_requirements(self, content: str) -> bool:
        """Analyze creativity requirements from agent file content."""
        content_lower = content.lower()
        
        creativity_indicators = [
            'creative', 'innovative', 'design', 'brainstorm', 'ideate',
            'generate', 'invent', 'original', 'novel'
        ]
        
        return any(indicator in content_lower for indicator in creativity_indicators)
    
    def _analyze_speed_requirements(self, content: str) -> bool:
        """Analyze speed priority requirements from agent file content."""
        content_lower = content.lower()
        
        speed_indicators = [
            'urgent', 'quick', 'fast', 'immediate', 'rapid', 'asap',
            'real-time', 'instant', 'responsive'
        ]
        
        return any(indicator in content_lower for indicator in speed_indicators)