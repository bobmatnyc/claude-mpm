#!/usr/bin/env python3
"""
Base Agent Loader Utility
========================

Provides functionality to load and prepend base agent instructions to all agent prompts.
Integrates with SharedPromptCache for performance optimization.

Key Features:
- Load base_agent.md content with caching
- Prepend base instructions to agent prompts
- Thread-safe operations
- Error handling for missing base instructions
- Integration with SharedPromptCache
- Dynamic prompt templates based on task complexity

Usage:
    from claude_mpm.agents.base_agent_loader import prepend_base_instructions

    # Get agent prompt with base instructions prepended
    full_prompt = prepend_base_instructions(get_agent_prompt("documentation-agent"))
"""

import json
import logging
import os
from enum import Enum
from pathlib import Path
from typing import Dict, Optional

from claude_mpm.services.memory.cache.shared_prompt_cache import SharedPromptCache

# Module-level logger
logger = logging.getLogger(__name__)

# Cache key for base agent instructions
BASE_AGENT_CACHE_KEY = "base_agent:instructions"


def _get_base_agent_file() -> Path:
    """Get the base agent file path with priority-based search.

    Priority order:
    1. Environment variable override (CLAUDE_MPM_BASE_AGENT_PATH)
    2. Current working directory (for local development)
    3. Known development locations
    4. User override location (~/.claude/agents/)
    5. Package installation location (fallback)
    """
    # Priority 0: Check environment variable override
    env_path = os.environ.get("CLAUDE_MPM_BASE_AGENT_PATH")
    if env_path:
        env_base_agent = Path(env_path)
        if env_base_agent.exists():
            logger.info(f"Using environment variable base_agent: {env_base_agent}")
            return env_base_agent
        logger.warning(
            f"CLAUDE_MPM_BASE_AGENT_PATH set but file doesn't exist: {env_base_agent}"
        )

    # Priority 1: Check current working directory for local development
    cwd = Path.cwd()
    cwd_base_agent = cwd / "src" / "claude_mpm" / "agents" / "base_agent.json"
    if cwd_base_agent.exists():
        logger.info(f"Using local development base_agent from cwd: {cwd_base_agent}")
        return cwd_base_agent

    # Priority 2: Check known development locations
    known_dev_paths = [
        Path("/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/base_agent.json"),
        Path.home()
        / "Projects"
        / "claude-mpm"
        / "src"
        / "claude_mpm"
        / "agents"
        / "base_agent.json",
        Path.home()
        / "projects"
        / "claude-mpm"
        / "src"
        / "claude_mpm"
        / "agents"
        / "base_agent.json",
    ]

    for dev_path in known_dev_paths:
        if dev_path.exists():
            logger.info(f"Using development base_agent: {dev_path}")
            return dev_path

    # Priority 3: Check user override location
    user_base_agent = Path.home() / ".claude" / "agents" / "base_agent.json"
    if user_base_agent.exists():
        logger.info(f"Using user override base_agent: {user_base_agent}")
        return user_base_agent

    # Priority 4: Check if we're running from a wheel installation
    try:
        import claude_mpm

        package_path = Path(claude_mpm.__file__).parent
        path_str = str(package_path.resolve())

        # For development/editable installs, check if there's a local src directory
        if "site-packages" in path_str or "dist-packages" in path_str:
            # Check if this is a pipx/pip installation
            if "pipx" in path_str:
                logger.debug(f"Detected pipx installation at {package_path}")

            # For wheel installations, check data directory
            data_base_agent = package_path / "data" / "agents" / "base_agent.json"
            if data_base_agent.exists():
                logger.info(f"Using wheel installation base_agent: {data_base_agent}")
                return data_base_agent

            # Also check direct agents directory in package
            pkg_base_agent = package_path / "agents" / "base_agent.json"
            if pkg_base_agent.exists():
                logger.info(f"Using package base_agent: {pkg_base_agent}")
                return pkg_base_agent
    except Exception as e:
        logger.debug(f"Exception checking package path: {e}")

    # Final fallback: Use the base_agent.json relative to this file
    base_agent_path = Path(__file__).parent / "base_agent.json"
    if base_agent_path.exists():
        logger.info(f"Using fallback base_agent relative to module: {base_agent_path}")
        return base_agent_path

    # Error if no base agent found
    logger.error("Base agent template file not found in any location")
    logger.error("Searched locations:")
    logger.error(f"  1. CWD: {cwd_base_agent}")
    logger.error(f"  2. Dev paths: {known_dev_paths}")
    logger.error(f"  3. User: {user_base_agent}")
    logger.error(f"  4. Module: {base_agent_path}")
    raise FileNotFoundError("base_agent.json not found in any expected location")


# Base agent file path (dynamically determined)
BASE_AGENT_FILE = _get_base_agent_file()


class PromptTemplate(Enum):
    """Dynamic prompt template levels."""

    MINIMAL = "MINIMAL"  # Core instructions only (~300 chars)
    STANDARD = "STANDARD"  # Core + context + basic integration (~700 chars)
    FULL = "FULL"  # All sections including escalation (~1500 chars)


# Template section definitions
# Optimized to reduce STANDARD template size while maintaining essential guidance
TEMPLATE_SECTIONS = {
    "core_principles": {
        "templates": ["MINIMAL", "STANDARD", "FULL"],
        "content": "Core Agent Principles",
    },
    "communication_standards": {
        "templates": ["MINIMAL", "STANDARD", "FULL"],
        "content": "Communication Standards",
    },
    "test_protocols": {
        "templates": ["FULL"],  # Moved to FULL only - not needed for most tasks
        "content": "Test Response Protocol",
    },
    "reporting_requirements": {
        "templates": ["STANDARD", "FULL"],
        "content": "Reporting Requirements",
    },
    "error_handling": {"templates": ["STANDARD", "FULL"], "content": "Error Handling"},
    "security_awareness": {"templates": ["FULL"], "content": "Security Awareness"},
    "temporal_context": {
        "templates": ["FULL"],  # Moved to FULL - not essential for STANDARD
        "content": "Temporal Context Integration",
    },
    "quality_standards": {"templates": ["FULL"], "content": "Quality Standards"},
    "tool_usage": {
        "templates": ["FULL"],  # Moved to FULL - agent-specific guidance suffices
        "content": "Tool Usage Guidelines",
    },
    "collaboration_protocols": {
        "templates": ["STANDARD", "FULL"],  # Keep for STANDARD - essential
        "content": "Collaboration Protocols",
    },
    "cross_agent_dependencies": {
        "templates": ["FULL"],  # Only needed for complex multi-agent tasks
        "content": "Cross-Agent Dependencies",
    },
    "performance_optimization": {
        "templates": ["FULL"],
        "content": "Performance Optimization",
    },
    "escalation_triggers": {"templates": ["FULL"], "content": "Escalation Triggers"},
    "output_formatting": {
        "templates": ["FULL"],  # Moved to FULL - basic formatting in STANDARD suffices
        "content": "Output Formatting Standards",
    },
    "framework_integration": {
        "templates": ["FULL"],
        "content": "Framework Integration",
    },
    "constraints": {
        "templates": ["MINIMAL", "STANDARD", "FULL"],
        "content": "Universal Constraints",
    },
    "success_criteria": {
        "templates": ["FULL"],  # Moved to FULL - implicit for simpler tasks
        "content": "Success Criteria",
    },
}


def load_base_agent_instructions(force_reload: bool = False) -> Optional[str]:
    """
    Load base agent instructions from base_agent.json with caching.
    Conditionally includes test-mode instructions based on CLAUDE_PM_TEST_MODE.

    Args:
        force_reload: Force reload from file, bypassing cache

    Returns:
        str: Base agent instructions content, or None if file not found
    """
    try:
        # Check if we're in test mode
        test_mode = os.environ.get("CLAUDE_PM_TEST_MODE", "").lower() in [
            "true",
            "1",
            "yes",
        ]

        # Get cache instance
        cache = SharedPromptCache.get_instance()

        # Different cache keys for test mode vs normal mode
        cache_key = f"{BASE_AGENT_CACHE_KEY}:{'test' if test_mode else 'normal'}"

        # Check cache first (unless force reload)
        if not force_reload:
            cached_content = cache.get(cache_key)
            if cached_content is not None:
                logger.debug(
                    f"Base agent instructions loaded from cache (test_mode={test_mode})"
                )
                return str(cached_content)

        # Get fresh base agent file path
        base_agent_file = _get_base_agent_file()

        # Load from file
        if not base_agent_file.exists():
            logger.warning(f"Base agent instructions file not found: {base_agent_file}")
            return None

        logger.debug(f"Loading base agent instructions from: {base_agent_file}")

        # Load JSON and extract instructions
        with open(base_agent_file, encoding="utf-8") as f:
            base_agent_data = json.load(f)

        # Extract instructions from the JSON structure
        if (
            "narrative_fields" in base_agent_data
            and "instructions" in base_agent_data["narrative_fields"]
        ):
            content = base_agent_data["narrative_fields"]["instructions"]
        else:
            # Fallback for older format
            content = base_agent_data.get("instructions", "")

        if not content:
            logger.error("No instructions found in base agent JSON")
            return None

        # If NOT in test mode, remove test-specific instructions to save context
        if not test_mode:
            content = _remove_test_mode_instructions(content)
            logger.debug("Test-mode instructions removed (not in test mode)")
        else:
            logger.info(
                "Test-mode instructions included (CLAUDE_PM_TEST_MODE is enabled)"
            )

        # Cache the content with 1 hour TTL
        cache.set(cache_key, content, ttl=3600)
        logger.debug(
            f"Base agent instructions cached successfully (test_mode={test_mode})"
        )

        return content

    except Exception as e:
        logger.error(f"Error loading base agent instructions: {e}")
        return None


def _remove_test_mode_instructions(content: str) -> str:
    """
    Remove test-mode specific instructions from base agent content.

    This removes the "Standard Test Response Protocol"
    sections to save context when not in test mode.

    Args:
        content: Full base agent instructions content

    Returns:
        str: Content with test-mode instructions removed
    """
    lines = content.split("\n")
    filtered_lines = []
    skip_section = False

    i = 0
    while i < len(lines):
        line = lines[i]

        # Check if we're entering the test response protocol section
        if line.strip() == "## Standard Test Response Protocol":
            skip_section = True
            i += 1
            continue

        # Check if we're in the test section and need to continue skipping
        if skip_section:
            # Check if we've reached a new top-level section (## but not ###)
            # Only stop skipping when we hit another ## section (same level as test section)
            if line.startswith("##") and not line.startswith("###"):
                skip_section = False
                # Don't skip this line - it's the start of a new section
                filtered_lines.append(line)
                i += 1
                continue
            # Skip this line as we're still in test section (includes ### subsections)
            i += 1
            continue

        # Not in test section, keep the line
        filtered_lines.append(line)
        i += 1

    # Join back and clean up extra blank lines
    result = "\n".join(filtered_lines)

    # Replace multiple consecutive newlines with double newlines
    while "\n\n\n" in result:
        result = result.replace("\n\n\n", "\n\n")

    return result.strip()


def _build_dynamic_prompt(content: str, template: PromptTemplate) -> str:
    """
    Build a dynamic prompt based on the template level.

    Args:
        content: Full base agent content
        template: Template level to use

    Returns:
        str: Filtered content based on template
    """
    if template == PromptTemplate.FULL:
        # Return full content for FULL template
        return content

    # Parse content into sections
    sections = _parse_content_sections(content)

    # Build prompt based on template sections
    filtered_lines = []
    filtered_lines.append("# Base Agent Instructions\n")
    filtered_lines.append("## 🤖 Agent Framework Context\n")
    filtered_lines.append(
        "You are operating as a specialized agent within the Claude PM Framework. You have been delegated a specific task by the PM Orchestrator and must complete it according to your specialized role and authority.\n"
    )

    # Add sections based on template
    template_name = template.value
    for _section_key, section_config in TEMPLATE_SECTIONS.items():
        if template_name in section_config["templates"]:
            section_name = section_config["content"]
            assert isinstance(section_name, str), "Section name must be string"
            if section_name in sections:
                filtered_lines.append(sections[section_name])

    # Clean up multiple newlines
    result = "\n".join(filtered_lines)
    while "\n\n\n" in result:
        result = result.replace("\n\n\n", "\n\n")

    return result.strip()


def _parse_content_sections(content: str) -> Dict[str, str]:
    """
    Parse content into named sections.

    Args:
        content: Full content to parse

    Returns:
        Dict mapping section names to their content
    """
    sections = {}
    current_section = None
    current_content = []

    lines = content.split("\n")

    for line in lines:
        # Check if this is a section header
        if line.startswith("### "):
            # Save previous section if exists
            if current_section:
                sections[current_section] = "\n".join(current_content)
                current_content = []

            # Extract section name
            current_section = line[4:].strip()
            current_content.append(line)

        elif line.startswith("## ") and "Agent Framework Context" not in line:
            # Handle ## level sections (skip the main header)
            if current_section:
                sections[current_section] = "\n".join(current_content)
                current_content = []

            current_section = line[3:].strip()
            current_content.append(line)

        elif line.startswith("#### "):
            # Handle #### level subsections
            if current_section:
                # Check for PM Orchestrator Integration vs PM Workflow Integration
                subsection_name = line[5:].strip()
                if subsection_name in [
                    "PM Orchestrator Integration",
                    "PM Workflow Integration",
                ]:
                    # Merge these redundant sections under "Collaboration Protocols"
                    if current_section != "Collaboration Protocols":
                        current_section = "PM Integration"
                current_content.append(line)

        elif current_section:
            current_content.append(line)

    # Save final section
    if current_section and current_content:
        sections[current_section] = "\n".join(current_content)

    # Merge redundant PM sections if both exist
    if (
        "PM Orchestrator Integration" in sections
        and "PM Workflow Integration" in sections
    ):
        # Combine into single PM Integration section
        sections["PM Integration"] = (
            "#### PM Integration\n"
            + sections["PM Orchestrator Integration"]
            .replace("#### PM Orchestrator Integration", "")
            .strip()
            + "\n\n"
            + sections["PM Workflow Integration"]
            .replace("#### PM Workflow Integration", "")
            .strip()
        )
        # Remove redundant sections
        del sections["PM Orchestrator Integration"]
        del sections["PM Workflow Integration"]

    return sections


def prepend_base_instructions(
    agent_prompt: str,
    separator: str = "\n\n---\n\n",
    template: Optional[PromptTemplate] = None,
    complexity_score: Optional[int] = None,
) -> str:
    """
    Prepend base agent instructions to an agent-specific prompt.

    Args:
        agent_prompt: The agent-specific prompt to prepend to
        separator: String to separate base instructions from agent prompt
        template: Optional template level to use (auto-selected if not provided)
        complexity_score: Optional complexity score for template selection

    Returns:
        str: Combined prompt with base instructions prepended
    """
    # Auto-select template based on complexity if not provided
    if template is None:
        if complexity_score is not None:
            if complexity_score <= 30:
                template = PromptTemplate.MINIMAL
            elif complexity_score <= 70:
                template = PromptTemplate.STANDARD
            else:
                template = PromptTemplate.FULL
        else:
            # Default to STANDARD if no complexity info
            template = PromptTemplate.STANDARD

    # Check if we're in test mode - always use FULL template for tests
    test_mode = os.environ.get("CLAUDE_PM_TEST_MODE", "").lower() in [
        "true",
        "1",
        "yes",
    ]
    if test_mode:
        template = PromptTemplate.FULL

    # Get cache instance
    cache = SharedPromptCache.get_instance()

    # Different cache keys for different templates and test mode
    cache_key = (
        f"{BASE_AGENT_CACHE_KEY}:{template.value}:{'test' if test_mode else 'normal'}"
    )

    # Check cache first
    cached_content = cache.get(cache_key)
    if cached_content is not None:
        logger.debug(
            f"Base agent instructions loaded from cache (template={template.value}, test_mode={test_mode})"
        )
        base_instructions = cached_content
    else:
        # Load full content
        full_content = load_base_agent_instructions()

        # If no base instructions, return original prompt
        if not full_content:
            logger.warning("No base instructions available, returning original prompt")
            return agent_prompt

        # Build dynamic prompt based on template
        base_instructions = _build_dynamic_prompt(full_content, template)

        # Cache the filtered content
        cache.set(cache_key, base_instructions, ttl=3600)
        logger.debug(
            f"Dynamic base agent instructions cached (template={template.value})"
        )

    # Log template selection
    if complexity_score is not None:
        logger.info(
            f"Using {template.value} prompt template "
            f"(complexity_score={complexity_score}, size={len(base_instructions)} chars)"
        )

    # Combine base instructions with agent prompt
    return f"{base_instructions}{separator}{agent_prompt}"


def clear_base_agent_cache() -> None:
    """Clear the cached base agent instructions for all templates and modes."""
    try:
        cache = SharedPromptCache.get_instance()
        # Clear caches for all template levels and modes
        for template in PromptTemplate:
            for mode in ["normal", "test"]:
                cache_key = f"{BASE_AGENT_CACHE_KEY}:{template.value}:{mode}"
                cache.invalidate(cache_key)

        # Also clear the old-style caches for backward compatibility
        cache.invalidate(f"{BASE_AGENT_CACHE_KEY}:normal")
        cache.invalidate(f"{BASE_AGENT_CACHE_KEY}:test")

        logger.debug("Base agent cache cleared (all templates and modes)")
    except Exception as e:
        logger.error(f"Error clearing base agent cache: {e}")


def get_base_agent_path() -> Path:
    """Get the path to the base agent instructions file."""
    return BASE_AGENT_FILE


def validate_base_agent_file() -> bool:
    """
    Validate that base agent file exists and is readable.

    Returns:
        bool: True if file exists and is readable, False otherwise
    """
    try:
        if not BASE_AGENT_FILE.exists():
            logger.error(f"Base agent file does not exist: {BASE_AGENT_FILE}")
            return False

        if not BASE_AGENT_FILE.is_file():
            logger.error(f"Base agent path is not a file: {BASE_AGENT_FILE}")
            return False

        # Try to read the file
        BASE_AGENT_FILE.read_text(encoding="utf-8")
        return True

    except Exception as e:
        logger.error(f"Base agent file validation failed: {e}")
        return False


# Module initialization - validate base agent file on import
if not validate_base_agent_file():
    logger.warning("Base agent file validation failed during module import")

# Export key components
__all__ = [
    "TEMPLATE_SECTIONS",
    "PromptTemplate",
    "clear_base_agent_cache",
    "get_base_agent_path",
    "load_base_agent_instructions",
    "prepend_base_instructions",
    "validate_base_agent_file",
]
