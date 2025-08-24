#!/usr/bin/env python3
"""
Agent Profile Loader Service - Consolidated Module
================================================

Comprehensive agent profile loading service with enhanced prompt integration.
Implements three-tier hierarchy precedence and improved prompt system integration.

Key Features:
- Three-tier hierarchy precedence (Project → User → System)
- Improved prompt integration with training system
- SharedPromptCache integration for performance optimization
- AgentRegistry integration for enhanced discovery
- Training system integration for prompt improvement
- Task Tool subprocess creation enhancement
- Profile validation and error handling

This is a consolidated version combining all functionality from the previous
multi-file implementation for better maintainability.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from claude_mpm.core.base_service import BaseService
from claude_mpm.core.config import Config
from claude_mpm.core.unified_paths import get_path_manager
from claude_mpm.services.agents.registry import AgentRegistry
from claude_mpm.services.memory.cache.shared_prompt_cache import SharedPromptCache

logger = logging.getLogger(__name__)

# ============================================================================
# Data Models
# ============================================================================


class ProfileTier(Enum):
    """Agent profile hierarchy tiers with precedence order."""

    PROJECT = "project"  # Highest precedence - project-specific agents
    USER = "user"  # Medium precedence - user-level agents
    SYSTEM = "system"  # Lowest precedence - framework/built-in agents


class ProfileStatus(Enum):
    """Profile loading status."""

    LOADED = "loaded"
    ERROR = "error"
    NOT_FOUND = "not_found"
    CACHED = "cached"


@dataclass
class ImprovedPrompt:
    """Improved prompt data structure."""

    prompt_id: str
    agent_name: str
    version: str
    content: str
    metrics: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    validated: bool = False


@dataclass
class AgentProfile:
    """Complete agent profile with hierarchy information."""

    name: str
    role: str
    description: str
    tier: ProfileTier
    source_path: str
    instructions: str = ""
    capabilities: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    improved_prompts: List[ImprovedPrompt] = field(default_factory=list)
    status: ProfileStatus = ProfileStatus.LOADED
    error: Optional[str] = None
    loaded_at: datetime = field(default_factory=datetime.now)
    cache_key: Optional[str] = None


# ============================================================================
# Main Service Class
# ============================================================================


class AgentProfileLoader(BaseService):
    """
    Comprehensive agent profile loading service with enhanced prompt integration.

    This consolidated version combines all functionality from the previous
    multi-file implementation into a single, maintainable module.
    """

    def __init__(self, config: Optional[Config] = None):
        """Initialize the agent profile loader."""
        super().__init__(name="agent_profile_loader", config=config)

        # Core configuration
        self.working_directory = Path(os.getcwd())
        self.framework_path = self._detect_framework_path()
        self.user_home = Path.home()

        # Tier paths configuration
        self.tier_paths = {
            ProfileTier.PROJECT: self.working_directory / "agents",
            ProfileTier.USER: get_path_manager().get_user_agents_dir(),
            ProfileTier.SYSTEM: Path(__file__).parent.parent / "agents" / "templates",
        }

        # Remove None values
        self.tier_paths = {k: v for k, v in self.tier_paths.items() if v is not None}

        # Profile cache
        self.profile_cache: Dict[str, AgentProfile] = {}
        self.cache_ttl = 3600  # 1 hour

        # Service integrations
        self.shared_cache: Optional[SharedPromptCache] = None
        self.agent_registry: Optional[AgentRegistry] = None

        # Improved prompts storage
        self.improved_prompts_path = (
            get_path_manager().get_user_config_dir() / "improved_prompts"
        )
        self.improved_prompts_path.mkdir(parents=True, exist_ok=True)

        # Performance tracking
        self.load_metrics: Dict[str, float] = {}

        logger.info("AgentProfileLoader initialized successfully")
        logger.info(f"  Working directory: {self.working_directory}")
        logger.info(f"  Framework path: {self.framework_path}")
        logger.info(f"  Tier paths: {list(self.tier_paths.keys())}")

    async def _initialize(self) -> None:
        """Initialize the service and its integrations."""
        logger.info("Initializing AgentProfileLoader service...")

        # Initialize service integrations
        try:
            self.shared_cache = SharedPromptCache.get_instance()
            self.agent_registry = AgentRegistry(cache_service=self.shared_cache)
            logger.info("Successfully initialized service integrations")
        except Exception as e:
            logger.warning(f"Failed to initialize some integrations: {e}")

        # Discover and cache initial profiles
        await self._discover_all_profiles()

        logger.info("AgentProfileLoader service initialized successfully")

    async def _cleanup(self) -> None:
        """Cleanup service resources."""
        logger.info("Cleaning up AgentProfileLoader service...")

        # Clear caches
        self.profile_cache.clear()

        # Save any pending improved prompts
        await self._save_improved_prompts()

        logger.info("AgentProfileLoader service cleaned up")

    async def _health_check(self) -> Dict[str, bool]:
        """Perform service health checks."""
        checks = {}

        try:
            # Check tier paths
            checks["tier_paths_accessible"] = all(
                path.exists() for path in self.tier_paths.values()
            )

            # Check service integrations
            checks["shared_cache_integration"] = self.shared_cache is not None
            checks["agent_registry_integration"] = self.agent_registry is not None

            # Check profile discovery
            profile_count = len(self.profile_cache)
            checks["profiles_loaded"] = profile_count > 0

            # Check improved prompts storage
            checks["improved_prompts_storage"] = self.improved_prompts_path.exists()

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            checks["health_check_error"] = False

        return checks

    # ========================================================================
    # Core Profile Loading
    # ========================================================================

    async def load_agent_profile(
        self, agent_name: str, use_cache: bool = True
    ) -> Optional[AgentProfile]:
        """
        Load agent profile with three-tier hierarchy precedence.

        Args:
            agent_name: Name of the agent to load
            use_cache: Whether to use cached profile if available

        Returns:
            AgentProfile or None if not found
        """
        start_time = asyncio.get_event_loop().time()

        # Check cache first
        if use_cache and agent_name in self.profile_cache:
            profile = self.profile_cache[agent_name]
            if (datetime.now() - profile.loaded_at).seconds < self.cache_ttl:
                self.load_metrics[f"{agent_name}_cache_hit"] = (
                    asyncio.get_event_loop().time() - start_time
                )
                return profile

        # Load profile with tier precedence
        profile = await self._load_profile_with_precedence(agent_name)

        if profile:
            # Load improved prompts
            profile.improved_prompts = await self._load_improved_prompts(agent_name)

            # Cache the profile
            self.profile_cache[agent_name] = profile

            # Update metrics
            self.load_metrics[f"{agent_name}_load_time"] = (
                asyncio.get_event_loop().time() - start_time
            )

            # Integrate with SharedPromptCache if available
            if self.shared_cache and profile.status == ProfileStatus.LOADED:
                cache_key = f"agent_profile_{agent_name}"
                await self.shared_cache.set_cached_result(cache_key, profile)
                profile.cache_key = cache_key

        return profile

    async def _load_profile_with_precedence(
        self, agent_name: str
    ) -> Optional[AgentProfile]:
        """Load profile following tier precedence: Project → User → System."""
        for tier in [ProfileTier.PROJECT, ProfileTier.USER, ProfileTier.SYSTEM]:
            if tier not in self.tier_paths:
                continue

            profile = await self._load_profile_from_tier(agent_name, tier)
            if profile and profile.status == ProfileStatus.LOADED:
                return profile

        return None

    async def _load_profile_from_tier(
        self, agent_name: str, tier: ProfileTier
    ) -> Optional[AgentProfile]:
        """Load profile from specific tier."""
        tier_path = self.tier_paths[tier]

        # Try different file formats and naming conventions
        # Check .md files first (Claude Code format), then fall back to YAML/JSON
        possible_files = [
            tier_path / f"{agent_name}.md",
            tier_path / f"{agent_name}_agent.md",
            tier_path / f"{agent_name}-agent.md",
            tier_path / f"{agent_name}.yaml",
            tier_path / f"{agent_name}.yml",
            tier_path / f"{agent_name}.json",
            tier_path / f"{agent_name}_agent.yaml",
            tier_path / f"{agent_name}_agent.yml",
            tier_path / f"{agent_name}_agent.json",
            tier_path / f"{agent_name}-agent.yaml",
            tier_path / f"{agent_name}-agent.yml",
            tier_path / f"{agent_name}-agent.json",
        ]

        for file_path in possible_files:
            if file_path.exists():
                return await self._parse_profile_file(file_path, tier)

        return None

    async def _parse_profile_file(
        self, file_path: Path, tier: ProfileTier
    ) -> Optional[AgentProfile]:
        """Parse agent profile from file."""
        try:
            # Read file content
            content = file_path.read_text()

            # Parse based on file extension
            if file_path.suffix == ".md":
                # Parse markdown with YAML frontmatter
                data, instructions = self._parse_markdown_with_frontmatter(content)
            elif file_path.suffix in [".yaml", ".yml"]:
                data = yaml.safe_load(content)
                instructions = data.get("instructions", "")
            elif file_path.suffix == ".json":
                data = json.loads(content)
                instructions = data.get("instructions", "")
            else:
                # Try to parse as YAML first, then JSON
                try:
                    data = yaml.safe_load(content)
                    instructions = data.get("instructions", "")
                except:
                    data = json.loads(content)
                    instructions = data.get("instructions", "")

            # Create profile
            return AgentProfile(
                name=data.get("name", file_path.stem),
                role=data.get("role", "agent"),
                description=data.get("description", ""),
                tier=tier,
                source_path=str(file_path),
                instructions=instructions,
                capabilities=data.get("capabilities", []),
                constraints=data.get("constraints", []),
                metadata=data.get("metadata", {}),
                status=ProfileStatus.LOADED,
            )

        except Exception as e:
            logger.error(f"Error parsing profile {file_path}: {e}")
            return AgentProfile(
                name=file_path.stem,
                role="error",
                description="Failed to load profile",
                tier=tier,
                source_path=str(file_path),
                status=ProfileStatus.ERROR,
                error=str(e),
            )

    def _parse_markdown_with_frontmatter(
        self, content: str
    ) -> Tuple[Dict[str, Any], str]:
        """
        Parse markdown file with YAML frontmatter.

        Args:
            content: Markdown content with YAML frontmatter

        Returns:
            Tuple of (frontmatter_data, markdown_content)
        """
        import re

        # Check if content starts with YAML frontmatter
        if not content.strip().startswith("---"):
            # No frontmatter, treat entire content as instructions
            return {"name": "unknown", "description": "No frontmatter found"}, content

        # Split frontmatter and content
        parts = re.split(r"^---\s*$", content, 2, re.MULTILINE)

        if len(parts) < 3:
            # Invalid frontmatter structure
            return {"name": "unknown", "description": "Invalid frontmatter"}, content

        # Parse YAML frontmatter
        frontmatter_text = parts[1].strip()
        markdown_content = parts[2].strip()

        try:
            frontmatter_data = yaml.safe_load(frontmatter_text)
            if not isinstance(frontmatter_data, dict):
                frontmatter_data = {
                    "name": "unknown",
                    "description": "Invalid frontmatter format",
                }
        except Exception as e:
            logger.error(f"Error parsing YAML frontmatter: {e}")
            frontmatter_data = {
                "name": "unknown",
                "description": f"YAML parse error: {e}",
            }

        return frontmatter_data, markdown_content

    # ========================================================================
    # Profile Discovery
    # ========================================================================

    async def _discover_all_profiles(self) -> Dict[ProfileTier, List[str]]:
        """Discover all available agent profiles across tiers."""
        discovered = {}

        for tier, tier_path in self.tier_paths.items():
            if not tier_path.exists():
                continue

            agents = []
            # Check for .md files (Claude Code format) and YAML/JSON files
            file_patterns = ["*.md", "*.yaml", "*.yml", "*.json"]
            for pattern in file_patterns:
                for file_path in tier_path.glob(pattern):
                    agent_name = file_path.stem
                    # Remove common suffixes
                    if agent_name.endswith(("_agent", "-agent")):
                        agent_name = agent_name[:-6]

                    if agent_name not in agents:
                        agents.append(agent_name)

            discovered[tier] = agents
            logger.debug(f"Discovered {len(agents)} agents in {tier.value} tier")

        return discovered

    async def get_available_agents(
        self, tier: Optional[ProfileTier] = None
    ) -> List[str]:
        """Get list of available agents, optionally filtered by tier."""
        discovered = await self._discover_all_profiles()

        if tier:
            return discovered.get(tier, [])

        # Combine all tiers, removing duplicates
        all_agents = set()
        for agents in discovered.values():
            all_agents.update(agents)

        return sorted(all_agents)

    # ========================================================================
    # Improved Prompts Management
    # ========================================================================

    async def _load_improved_prompts(self, agent_name: str) -> List[ImprovedPrompt]:
        """Load improved prompts for an agent."""
        prompts = []
        prompt_file = self.improved_prompts_path / f"{agent_name}_prompts.json"

        if prompt_file.exists():
            try:
                with open(prompt_file) as f:
                    data = json.load(f)
                    for prompt_data in data:
                        prompt = ImprovedPrompt(
                            prompt_id=prompt_data["prompt_id"],
                            agent_name=prompt_data["agent_name"],
                            version=prompt_data["version"],
                            content=prompt_data["content"],
                            metrics=prompt_data.get("metrics", {}),
                            metadata=prompt_data.get("metadata", {}),
                            created_at=datetime.fromisoformat(
                                prompt_data["created_at"]
                            ),
                            validated=prompt_data.get("validated", False),
                        )
                        prompts.append(prompt)
            except Exception as e:
                logger.error(f"Error loading improved prompts for {agent_name}: {e}")

        return prompts

    async def save_improved_prompt(
        self, agent_name: str, prompt: ImprovedPrompt
    ) -> bool:
        """Save an improved prompt for an agent."""
        try:
            # Load existing prompts
            prompts = await self._load_improved_prompts(agent_name)

            # Add or update prompt
            existing_idx = None
            for idx, existing in enumerate(prompts):
                if existing.prompt_id == prompt.prompt_id:
                    existing_idx = idx
                    break

            if existing_idx is not None:
                prompts[existing_idx] = prompt
            else:
                prompts.append(prompt)

            # Save to file
            prompt_file = self.improved_prompts_path / f"{agent_name}_prompts.json"
            with open(prompt_file, "w") as f:
                json.dump(
                    [
                        {
                            "prompt_id": p.prompt_id,
                            "agent_name": p.agent_name,
                            "version": p.version,
                            "content": p.content,
                            "metrics": p.metrics,
                            "metadata": p.metadata,
                            "created_at": p.created_at.isoformat(),
                            "validated": p.validated,
                        }
                        for p in prompts
                    ],
                    f,
                    indent=2,
                )

            return True

        except Exception as e:
            logger.error(f"Error saving improved prompt: {e}")
            return False

    async def _save_improved_prompts(self) -> None:
        """Save all pending improved prompts."""
        for agent_name, profile in self.profile_cache.items():
            if profile.improved_prompts:
                for prompt in profile.improved_prompts:
                    await self.save_improved_prompt(agent_name, prompt)

    # ========================================================================
    # Task Integration
    # ========================================================================

    async def enhance_task_creation(
        self, agent_name: str, task_params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Enhance Task Tool subprocess creation with agent profile data.

        Args:
            agent_name: Name of the agent
            task_params: Original task parameters

        Returns:
            Enhanced task parameters
        """
        profile = await self.load_agent_profile(agent_name)

        if not profile:
            logger.warning(f"No profile found for agent {agent_name}")
            return task_params

        # Enhance with profile data
        enhanced = task_params.copy()

        # Add agent metadata
        enhanced["agent_metadata"] = {
            "name": profile.name,
            "role": profile.role,
            "tier": profile.tier.value,
            "capabilities": profile.capabilities,
            "constraints": profile.constraints,
        }

        # Add improved prompts if available
        if profile.improved_prompts:
            best_prompt = max(
                profile.improved_prompts, key=lambda p: p.metrics.get("success_rate", 0)
            )
            enhanced["improved_prompt"] = {
                "content": best_prompt.content,
                "version": best_prompt.version,
                "metrics": best_prompt.metrics,
            }

        # Add custom instructions if available
        if profile.instructions:
            enhanced["additional_instructions"] = profile.instructions

        return enhanced

    # ========================================================================
    # Metrics and Validation
    # ========================================================================

    async def validate_profile(self, agent_name: str) -> Dict[str, Any]:
        """Validate agent profile structure and content."""
        profile = await self.load_agent_profile(agent_name)

        if not profile:
            return {"valid": False, "error": "Profile not found"}

        validation_results = {"valid": True, "warnings": [], "errors": []}

        # Check required fields
        if not profile.name:
            validation_results["errors"].append("Missing agent name")
            validation_results["valid"] = False

        if not profile.role:
            validation_results["errors"].append("Missing agent role")
            validation_results["valid"] = False

        # Check profile completeness
        if not profile.description:
            validation_results["warnings"].append("Missing agent description")

        if not profile.capabilities:
            validation_results["warnings"].append("No capabilities defined")

        if not profile.constraints:
            validation_results["warnings"].append("No constraints defined")

        # Validate improved prompts
        for prompt in profile.improved_prompts:
            if not prompt.validated:
                validation_results["warnings"].append(
                    f"Unvalidated prompt: {prompt.prompt_id}"
                )

        return validation_results

    async def get_profile_metrics(self) -> Dict[str, Any]:
        """Get comprehensive profile loading metrics."""
        metrics = {
            "cache_size": len(self.profile_cache),
            "load_metrics": self.load_metrics,
            "tier_stats": {},
        }

        # Count profiles by tier
        for profile in self.profile_cache.values():
            tier = profile.tier.value
            metrics["tier_stats"][tier] = metrics["tier_stats"].get(tier, 0) + 1

        # Calculate average load times
        if self.load_metrics:
            load_times = [
                v for k, v in self.load_metrics.items() if k.endswith("_load_time")
            ]
            if load_times:
                metrics["avg_load_time"] = sum(load_times) / len(load_times)

        # Count improved prompts
        total_prompts = sum(
            len(p.improved_prompts) for p in self.profile_cache.values()
        )
        metrics["total_improved_prompts"] = total_prompts

        return metrics

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def _detect_framework_path(self) -> Optional[Path]:
        """Detect the framework path for system-level agents."""
        possible_paths = [
            self.working_directory / "framework",
            self.working_directory / "src" / "claude_mpm" / "framework",
            Path(__file__).parent.parent / "framework",
        ]

        for path in possible_paths:
            if path.exists() and (path / "agent-roles").exists():
                return path

        return None

    def invalidate_cache(self, agent_name: Optional[str] = None) -> None:
        """Invalidate profile cache."""
        if agent_name:
            self.profile_cache.pop(agent_name, None)
        else:
            self.profile_cache.clear()

    async def reload_profile(self, agent_name: str) -> Optional[AgentProfile]:
        """Force reload of agent profile, bypassing cache."""
        self.invalidate_cache(agent_name)
        return await self.load_agent_profile(agent_name, use_cache=False)
