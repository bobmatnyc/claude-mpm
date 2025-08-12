#!/usr/bin/env python3
"""
Agent Registry Service - Consolidated Module
===========================================

Provides fully synchronous agent discovery and management system with caching,
validation, and hierarchical organization support.

Features:
- Two-tier hierarchy discovery (user → system)
- Synchronous directory scanning
- Agent metadata collection and caching
- Agent type detection and classification  
- SharedPromptCache integration
- Agent validation and error handling

This is a consolidated version combining all functionality from the previous
multi-file implementation for better maintainability.
"""

import os
import json
import time
import hashlib
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

from claude_mpm.core.config_paths import ConfigPaths
from claude_mpm.services.memory.cache.simple_cache import SimpleCacheService
from claude_mpm.agents.frontmatter_validator import FrontmatterValidator, ValidationResult

logger = logging.getLogger(__name__)


# ============================================================================
# Constants and Types
# ============================================================================

CORE_AGENT_TYPES = {
    'engineer', 'architect', 'qa', 'security', 'documentation',
    'ops', 'data', 'research', 'version_control'
}

SPECIALIZED_AGENT_TYPES = {
    'pm_orchestrator', 'frontend', 'backend', 'devops', 'ml',
    'database', 'api', 'mobile', 'cloud', 'testing'
}

ALL_AGENT_TYPES = CORE_AGENT_TYPES | SPECIALIZED_AGENT_TYPES


class AgentTier(Enum):
    """Agent hierarchy tiers."""
    PROJECT = "project"  # Highest precedence - project-specific agents
    USER = "user"
    SYSTEM = "system"


class AgentType(Enum):
    """Agent classification types."""
    CORE = "core"
    SPECIALIZED = "specialized"
    CUSTOM = "custom"
    UNKNOWN = "unknown"


# ============================================================================
# Data Models
# ============================================================================

@dataclass
class AgentMetadata:
    """Complete metadata for discovered agent."""
    name: str
    path: str
    tier: AgentTier
    agent_type: AgentType
    description: str = ""
    version: str = "0.0.0"
    dependencies: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_modified: float = field(default_factory=time.time)
    file_size: int = 0
    checksum: str = ""
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['tier'] = self.tier.value
        data['agent_type'] = self.agent_type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMetadata':
        """Create from dictionary."""
        data['tier'] = AgentTier(data['tier'])
        data['agent_type'] = AgentType(data['agent_type'])
        return cls(**data)


# ============================================================================
# Main Registry Class
# ============================================================================

class AgentRegistry:
    """
    Core Agent Registry - Fully synchronous agent discovery and management system.
    
    This consolidated version combines all functionality from the previous
    multi-file implementation into a single, maintainable module.
    """
    
    def __init__(self, cache_service=None, model_selector=None):
        """Initialize AgentRegistry with optional cache service and model selector."""
        # Use provided cache service or create a default one
        if cache_service is None:
            # Create a simple in-memory cache with 1 hour TTL by default
            self.cache_service = SimpleCacheService(default_ttl=3600, max_size=500)
            self.cache_enabled = True
        else:
            self.cache_service = cache_service
            self.cache_enabled = True
        
        self.model_selector = model_selector
        
        # Initialize frontmatter validator
        self.frontmatter_validator = FrontmatterValidator()
        
        # Registry storage
        self.registry: Dict[str, AgentMetadata] = {}
        self.discovery_paths: List[Path] = []
        
        # Cache configuration
        self.cache_ttl = 3600  # 1 hour
        self.cache_prefix = "agent_registry"
        
        # Track discovered files for cache invalidation
        self.discovered_files: Set[Path] = set()
        
        # Discovery configuration
        self.file_extensions = {'.md', '.json', '.yaml', '.yml'}
        self.ignore_patterns = {'__pycache__', '.git', 'node_modules', '.pytest_cache'}
        
        # Statistics
        self.discovery_stats = {
            'last_discovery': None,
            'total_discovered': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'discovery_duration': 0.0
        }
        
        # Setup discovery paths
        self._setup_discovery_paths()
        
        logger.info(f"AgentRegistry initialized with cache={'enabled' if self.cache_enabled else 'disabled'}")
    
    def _setup_discovery_paths(self) -> None:
        """Setup standard discovery paths for agent files."""
        # Project-level agents (highest priority)
        project_path = ConfigPaths.get_project_agents_dir()
        if project_path.exists():
            self.discovery_paths.append(project_path)
        
        # User-level agents
        user_path = ConfigPaths.get_user_agents_dir()
        if user_path.exists():
            self.discovery_paths.append(user_path)
        
        # System-level agents - multiple possible locations
        system_paths = [
            Path(__file__).parent.parent / 'agents' / 'templates',
            Path('/opt/claude-pm/agents'),
            Path('/usr/local/claude-pm/agents')
        ]
        
        for path in system_paths:
            if path.exists():
                self.discovery_paths.append(path)
        
        logger.debug(f"Discovery paths configured: {[str(p) for p in self.discovery_paths]}")
    
    # ========================================================================
    # Discovery Methods
    # ========================================================================
    
    def discover_agents(self, force_refresh: bool = False) -> Dict[str, AgentMetadata]:
        """
        Discover all available agents across configured paths.
        
        Args:
            force_refresh: Force re-discovery even if cache is valid
            
        Returns:
            Dictionary of agent name to metadata
        """
        start_time = time.time()
        
        # Try cache first
        if not force_refresh and self.cache_enabled:
            cached = self._get_cached_registry()
            if cached:
                self.registry = cached
                self.discovery_stats['cache_hits'] += 1
                logger.debug("Using cached agent registry")
                return self.registry
        
        self.discovery_stats['cache_misses'] += 1
        
        # Clear existing registry and discovered files
        self.registry.clear()
        self.discovered_files.clear()
        
        # Discover agents from all paths
        for discovery_path in self.discovery_paths:
            tier = self._determine_tier(discovery_path)
            self._discover_path(discovery_path, tier)
        
        # Handle tier precedence
        self._apply_tier_precedence()
        
        # Cache the results with file tracking
        if self.cache_enabled:
            self._cache_registry()
        
        # Update statistics
        self.discovery_stats['last_discovery'] = time.time()
        self.discovery_stats['total_discovered'] = len(self.registry)
        self.discovery_stats['discovery_duration'] = time.time() - start_time
        
        logger.info(f"Discovered {len(self.registry)} agents in {self.discovery_stats['discovery_duration']:.2f}s")
        
        return self.registry
    
    def _discover_path(self, path: Path, tier: AgentTier) -> None:
        """Discover agents in a specific path."""
        if not path.exists():
            return
        
        for file_path in path.rglob('*'):
            # Skip directories and ignored patterns
            if file_path.is_dir():
                continue
            
            if any(pattern in str(file_path) for pattern in self.ignore_patterns):
                continue
            
            # Check file extension
            if file_path.suffix not in self.file_extensions:
                continue
            
            # Extract agent name
            agent_name = self._extract_agent_name(file_path)
            if not agent_name:
                continue
            
            # Track discovered file for cache invalidation
            self.discovered_files.add(file_path)
            
            # Create metadata
            metadata = self._create_agent_metadata(file_path, agent_name, tier)
            
            # Validate agent
            if self._validate_agent(metadata):
                # Check tier precedence
                if agent_name in self.registry:
                    existing = self.registry[agent_name]
                    if self._has_tier_precedence(metadata.tier, existing.tier):
                        self.registry[agent_name] = metadata
                        logger.debug(f"Replaced {agent_name} with higher precedence version from {tier.value}")
                else:
                    self.registry[agent_name] = metadata
    
    def _extract_agent_name(self, file_path: Path) -> Optional[str]:
        """Extract agent name from file path."""
        name = file_path.stem
        
        # Remove common suffixes
        suffixes_to_remove = ['_agent', '-agent', '.agent']
        for suffix in suffixes_to_remove:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
                break
        
        # Skip empty or invalid names
        if not name or name.startswith('.'):
            return None
        
        return name
    
    def _create_agent_metadata(self, file_path: Path, agent_name: str, tier: AgentTier) -> AgentMetadata:
        """Create agent metadata from file."""
        # Get file stats
        stat = file_path.stat()
        
        # Calculate checksum
        checksum = ""
        try:
            with open(file_path, 'rb') as f:
                checksum = hashlib.md5(f.read()).hexdigest()
        except Exception as e:
            logger.warning(f"Failed to calculate checksum for {file_path}: {e}")
        
        # Determine agent type
        agent_type = self._classify_agent(agent_name)
        
        # Extract description and metadata from file
        description = ""
        version = "0.0.0"
        capabilities = []
        metadata = {}
        
        try:
            content = file_path.read_text()
            
            # Try to parse as JSON/YAML/MD for structured data
            if file_path.suffix in ['.md', '.json', '.yaml', '.yml']:
                try:
                    if file_path.suffix == '.json':
                        data = json.loads(content)
                        description = data.get('description', '')
                        version = data.get('version', '0.0.0')
                        capabilities = data.get('capabilities', [])
                        metadata = data.get('metadata', {})
                    elif file_path.suffix == '.md':
                        # Parse markdown with YAML frontmatter
                        import yaml
                        import re
                        
                        # Check for YAML frontmatter
                        if content.strip().startswith('---'):
                            parts = re.split(r'^---\s*$', content, 2, re.MULTILINE)
                            if len(parts) >= 3:
                                frontmatter_text = parts[1].strip()
                                data = yaml.safe_load(frontmatter_text)
                                
                                # Validate and correct frontmatter
                                validation_result = self.frontmatter_validator.validate_and_correct(data)
                                if validation_result.corrections:
                                    logger.info(f"Applied corrections to {file_path.name}:")
                                    for correction in validation_result.corrections:
                                        logger.info(f"  - {correction}")
                                    
                                    # Use corrected frontmatter if available
                                    if validation_result.corrected_frontmatter:
                                        data = validation_result.corrected_frontmatter
                                
                                if validation_result.errors:
                                    logger.warning(f"Validation errors in {file_path.name}:")
                                    for error in validation_result.errors:
                                        logger.warning(f"  - {error}")
                                
                                description = data.get('description', '')
                                version = data.get('version', '0.0.0')
                                capabilities = data.get('tools', [])  # Tools in .md format
                                metadata = data
                            else:
                                # No frontmatter, use defaults
                                description = f"{file_path.stem} agent"
                                version = '1.0.0'
                                capabilities = []
                                metadata = {}
                        else:
                            # No frontmatter, use defaults
                            description = f"{file_path.stem} agent"
                            version = '1.0.0'
                            capabilities = []
                            metadata = {}
                    else:
                        # YAML files
                        import yaml
                        data = yaml.safe_load(content)
                        description = data.get('description', '')
                        version = data.get('version', '0.0.0')
                        capabilities = data.get('capabilities', [])
                        metadata = data.get('metadata', {})
                except Exception:
                    pass
            
            # Extract from markdown files
            elif file_path.suffix == '.md':
                lines = content.split('\n')
                for i, line in enumerate(lines[:20]):  # Check first 20 lines
                    if line.strip().startswith('#') and i == 0:
                        description = line.strip('#').strip()
                    elif line.startswith('Version:'):
                        version = line.split(':', 1)[1].strip()
                    elif line.startswith('Description:'):
                        description = line.split(':', 1)[1].strip()
        
        except Exception as e:
            logger.warning(f"Failed to parse {file_path}: {e}")
        
        return AgentMetadata(
            name=agent_name,
            path=str(file_path),
            tier=tier,
            agent_type=agent_type,
            description=description,
            version=version,
            capabilities=capabilities,
            created_at=stat.st_ctime,
            last_modified=stat.st_mtime,
            file_size=stat.st_size,
            checksum=checksum,
            metadata=metadata
        )
    
    def _classify_agent(self, agent_name: str) -> AgentType:
        """Classify agent based on name."""
        name_lower = agent_name.lower()
        
        # Remove common suffixes for classification
        for suffix in ['_agent', '-agent', '.agent']:
            if name_lower.endswith(suffix):
                name_lower = name_lower[:-len(suffix)]
        
        if name_lower in CORE_AGENT_TYPES:
            return AgentType.CORE
        elif name_lower in SPECIALIZED_AGENT_TYPES:
            return AgentType.SPECIALIZED
        elif any(core in name_lower for core in CORE_AGENT_TYPES):
            return AgentType.CORE
        elif any(spec in name_lower for spec in SPECIALIZED_AGENT_TYPES):
            return AgentType.SPECIALIZED
        else:
            return AgentType.CUSTOM
    
    def _determine_tier(self, path: Path) -> AgentTier:
        """Determine tier based on path location."""
        path_str = str(path)
        
        # Check if it's a project-level path (in current working directory)
        # Project agents are in <project_root>/.claude-mpm/agents
        project_agents_dir = ConfigPaths.get_project_agents_dir()
        if project_agents_dir.exists() and (path == project_agents_dir or project_agents_dir in path.parents):
            return AgentTier.PROJECT
        
        # Check if it's a user-level path (in home directory)
        user_agents_dir = ConfigPaths.get_user_agents_dir()
        if user_agents_dir.exists() and (path == user_agents_dir or user_agents_dir in path.parents):
            return AgentTier.USER
        
        # Everything else is system-level
        return AgentTier.SYSTEM
    
    def _has_tier_precedence(self, tier1: AgentTier, tier2: AgentTier) -> bool:
        """Check if tier1 has precedence over tier2."""
        precedence = {
            AgentTier.PROJECT: 3,  # Highest precedence
            AgentTier.USER: 2,
            AgentTier.SYSTEM: 1
        }
        return precedence.get(tier1, 0) > precedence.get(tier2, 0)
    
    def _apply_tier_precedence(self) -> None:
        """Apply tier precedence rules to discovered agents."""
        # Group agents by name
        agents_by_name: Dict[str, List[AgentMetadata]] = {}
        
        for agent in self.registry.values():
            if agent.name not in agents_by_name:
                agents_by_name[agent.name] = []
            agents_by_name[agent.name].append(agent)
        
        # Apply precedence
        self.registry.clear()
        for agent_name, agents in agents_by_name.items():
            if len(agents) == 1:
                self.registry[agent_name] = agents[0]
            else:
                # Sort by tier precedence
                agents.sort(key=lambda a: {AgentTier.PROJECT: 3, AgentTier.USER: 2, AgentTier.SYSTEM: 1}.get(a.tier, 0), reverse=True)
                self.registry[agent_name] = agents[0]
                
                if len(agents) > 1:
                    logger.debug(f"Applied tier precedence for {agent_name}: using {agents[0].tier.value} version")
    
    # ========================================================================
    # Validation Methods
    # ========================================================================
    
    def _validate_agent(self, metadata: AgentMetadata) -> bool:
        """Validate agent metadata and file."""
        errors = []
        
        # Check file exists
        if not Path(metadata.path).exists():
            errors.append("Agent file does not exist")
        
        # Check name validity
        if not metadata.name or metadata.name.startswith('.'):
            errors.append("Invalid agent name")
        
        # Check for required fields based on file type
        if metadata.path.endswith('.json'):
            try:
                with open(metadata.path) as f:
                    data = json.load(f)
                    if 'name' not in data:
                        errors.append("Missing 'name' field in JSON")
                    if 'role' not in data:
                        errors.append("Missing 'role' field in JSON")
            except Exception as e:
                errors.append(f"Invalid JSON: {e}")
        
        # Update metadata
        metadata.is_valid = len(errors) == 0
        metadata.validation_errors = errors
        
        return metadata.is_valid
    
    # ========================================================================
    # Cache Methods
    # ========================================================================
    
    def _get_cached_registry(self) -> Optional[Dict[str, AgentMetadata]]:
        """Get registry from cache if available."""
        if not self.cache_service:
            return None
        
        try:
            cache_key = f"{self.cache_prefix}_registry"
            cached_data = self.cache_service.get(cache_key)
            
            if cached_data:
                # Deserialize metadata
                registry = {}
                for name, data in cached_data.items():
                    registry[name] = AgentMetadata.from_dict(data)
                
                # Also restore discovered files set
                files_key = f"{self.cache_prefix}_discovered_files"
                discovered_files = self.cache_service.get(files_key)
                if discovered_files:
                    self.discovered_files = {Path(f) for f in discovered_files}
                
                return registry
        
        except Exception as e:
            logger.warning(f"Failed to get cached registry: {e}")
        
        return None
    
    def _cache_registry(self) -> None:
        """Cache the current registry with file tracking."""
        if not self.cache_service:
            return
        
        try:
            cache_key = f"{self.cache_prefix}_registry"
            
            # Serialize metadata
            cache_data = {
                name: metadata.to_dict() 
                for name, metadata in self.registry.items()
            }
            
            # If the cache service supports file tracking, use it
            if hasattr(self.cache_service, 'set'):
                import inspect
                sig = inspect.signature(self.cache_service.set)
                if 'tracked_files' in sig.parameters:
                    # Cache with file tracking for automatic invalidation
                    self.cache_service.set(
                        cache_key, 
                        cache_data, 
                        ttl=self.cache_ttl,
                        tracked_files=list(self.discovered_files)
                    )
                else:
                    # Fall back to regular caching
                    self.cache_service.set(cache_key, cache_data, ttl=self.cache_ttl)
            else:
                # Fall back to regular caching
                self.cache_service.set(cache_key, cache_data, ttl=self.cache_ttl)
            
            # Also cache the discovered files list
            files_key = f"{self.cache_prefix}_discovered_files"
            self.cache_service.set(
                files_key, 
                [str(f) for f in self.discovered_files],
                ttl=self.cache_ttl
            )
            
            logger.debug(f"Cached agent registry with {len(self.discovered_files)} tracked files")
        
        except Exception as e:
            logger.warning(f"Failed to cache registry: {e}")
    
    def invalidate_cache(self) -> None:
        """Invalidate the registry cache."""
        if self.cache_service:
            try:
                # Invalidate both registry and files cache
                registry_key = f"{self.cache_prefix}_registry"
                files_key = f"{self.cache_prefix}_discovered_files"
                
                self.cache_service.delete(registry_key)
                self.cache_service.delete(files_key)
                
                # Also clear in-memory registry to force re-discovery
                self.registry.clear()
                self.discovered_files.clear()
                
                logger.debug("Invalidated registry cache")
            except Exception as e:
                logger.warning(f"Failed to invalidate cache: {e}")
    
    # ========================================================================
    # Query Methods
    # ========================================================================
    
    def get_agent(self, name: str) -> Optional[AgentMetadata]:
        """Get metadata for a specific agent."""
        # Ensure registry is populated
        if not self.registry:
            self.discover_agents()
        
        return self.registry.get(name)
    
    def list_agents(self, tier: Optional[AgentTier] = None, 
                   agent_type: Optional[AgentType] = None) -> List[AgentMetadata]:
        """List agents with optional filtering."""
        # Ensure registry is populated
        if not self.registry:
            self.discover_agents()
        
        agents = list(self.registry.values())
        
        # Apply filters
        if tier:
            agents = [a for a in agents if a.tier == tier]
        
        if agent_type:
            agents = [a for a in agents if a.agent_type == agent_type]
        
        return agents
    
    def get_agent_names(self) -> List[str]:
        """Get list of all agent names."""
        if not self.registry:
            self.discover_agents()
        
        return sorted(self.registry.keys())
    
    def get_core_agents(self) -> List[AgentMetadata]:
        """Get all core framework agents."""
        return self.list_agents(agent_type=AgentType.CORE)
    
    def get_specialized_agents(self) -> List[AgentMetadata]:
        """Get all specialized agents."""
        return self.list_agents(agent_type=AgentType.SPECIALIZED)
    
    def get_custom_agents(self) -> List[AgentMetadata]:
        """Get all custom user-defined agents."""
        return self.list_agents(agent_type=AgentType.CUSTOM)
    
    def search_agents(self, query: str) -> List[AgentMetadata]:
        """Search agents by name or description."""
        if not self.registry:
            self.discover_agents()
        
        query_lower = query.lower()
        results = []
        
        for agent in self.registry.values():
            if (query_lower in agent.name.lower() or 
                query_lower in agent.description.lower()):
                results.append(agent)
        
        return results
    
    # ========================================================================
    # Statistics and Monitoring
    # ========================================================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive registry statistics."""
        if not self.registry:
            self.discover_agents()
        
        stats = {
            'total_agents': len(self.registry),
            'discovery_stats': self.discovery_stats.copy(),
            'agents_by_tier': {},
            'agents_by_type': {},
            'validation_stats': {
                'valid': 0,
                'invalid': 0,
                'errors': []
            },
            'cache_metrics': {}
        }
        
        # Add cache metrics if available
        if self.cache_enabled and hasattr(self.cache_service, 'get_cache_metrics'):
            stats['cache_metrics'] = self.cache_service.get_cache_metrics()
        
        # Count by tier
        for agent in self.registry.values():
            tier = agent.tier.value
            stats['agents_by_tier'][tier] = stats['agents_by_tier'].get(tier, 0) + 1
        
        # Count by type
        for agent in self.registry.values():
            agent_type = agent.agent_type.value
            stats['agents_by_type'][agent_type] = stats['agents_by_type'].get(agent_type, 0) + 1
        
        # Validation stats
        for agent in self.registry.values():
            if agent.is_valid:
                stats['validation_stats']['valid'] += 1
            else:
                stats['validation_stats']['invalid'] += 1
                stats['validation_stats']['errors'].extend(agent.validation_errors)
        
        return stats
    
    def validate_all_agents(self) -> Dict[str, List[str]]:
        """Validate all discovered agents and return errors."""
        if not self.registry:
            self.discover_agents()
        
        errors = {}
        
        for agent_name, metadata in self.registry.items():
            # Re-validate
            self._validate_agent(metadata)
            
            if not metadata.is_valid:
                errors[agent_name] = metadata.validation_errors
        
        return errors
    
    # ========================================================================
    # Utility Methods
    # ========================================================================
    
    def add_discovery_path(self, path: Union[str, Path]) -> None:
        """Add a new path for agent discovery."""
        path = Path(path)
        if path.exists() and path not in self.discovery_paths:
            self.discovery_paths.append(path)
            logger.info(f"Added discovery path: {path}")
            # Invalidate cache since paths changed
            self.invalidate_cache()
            # Force re-discovery with new path
            self.discover_agents(force_refresh=True)
    
    def remove_discovery_path(self, path: Union[str, Path]) -> None:
        """Remove a path from agent discovery."""
        path = Path(path)
        if path in self.discovery_paths:
            self.discovery_paths.remove(path)
            logger.info(f"Removed discovery path: {path}")
            # Invalidate cache since paths changed
            self.invalidate_cache()
            # Force re-discovery without the removed path
            self.discover_agents(force_refresh=True)
    
    def export_registry(self, output_path: Union[str, Path]) -> None:
        """Export registry to JSON file."""
        if not self.registry:
            self.discover_agents()
        
        output_path = Path(output_path)
        
        # Serialize registry
        export_data = {
            'metadata': {
                'exported_at': time.time(),
                'total_agents': len(self.registry),
                'discovery_paths': [str(p) for p in self.discovery_paths]
            },
            'agents': {
                name: metadata.to_dict()
                for name, metadata in self.registry.items()
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Exported registry to {output_path}")
    
    def import_registry(self, input_path: Union[str, Path]) -> None:
        """Import registry from JSON file."""
        input_path = Path(input_path)
        
        with open(input_path, 'r') as f:
            data = json.load(f)
        
        # Clear current registry
        self.registry.clear()
        
        # Import agents
        for name, agent_data in data.get('agents', {}).items():
            self.registry[name] = AgentMetadata.from_dict(agent_data)
        
        # Cache imported registry
        if self.cache_enabled:
            self._cache_registry()
        
        logger.info(f"Imported {len(self.registry)} agents from {input_path}")