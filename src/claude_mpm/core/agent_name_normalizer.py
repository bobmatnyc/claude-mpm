"""Agent name normalization utilities for consistent naming across the system."""

from typing import Optional

from claude_mpm.core.logging_utils import get_logger

logger = get_logger(__name__)


class AgentNameNormalizer:
    """
    Handles agent name normalization to ensure consistency across:
    - TodoWrite prefixes
    - Task tool display
    - Agent type identification
    - Color coding
    """

    # Canonical agent names (standardized format)
    # These are the display names used in TodoWrite prefixes
    CANONICAL_NAMES = {
        "research": "Research",
        "engineer": "Engineer",
        "qa": "QA",
        "security": "Security",
        "documentation": "Documentation",
        "ops": "Ops",
        "version_control": "Version Control",
        "data_engineer": "Data Engineer",
        "architect": "Architect",
        "pm": "PM",
        # Additional agent types from deployed agents
        "python_engineer": "Python Engineer",
        "golang_engineer": "Golang Engineer",
        "java_engineer": "Java Engineer",
        "javascript_engineer": "JavaScript Engineer",
        "typescript_engineer": "TypeScript Engineer",
        "rust_engineer": "Rust Engineer",
        "ruby_engineer": "Ruby Engineer",
        "php_engineer": "PHP Engineer",
        "phoenix_engineer": "Phoenix Engineer",
        "nestjs_engineer": "NestJS Engineer",
        "react_engineer": "React Engineer",
        "nextjs_engineer": "NextJS Engineer",
        "svelte_engineer": "Svelte Engineer",
        "dart_engineer": "Dart Engineer",
        "tauri_engineer": "Tauri Engineer",
        "prompt_engineer": "Prompt Engineer",
        "refactoring_engineer": "Refactoring Engineer",
        # QA variants
        "api_qa": "API QA",
        "web_qa": "Web QA",
        "real_user": "Real User",
        # Ops variants
        "clerk_ops": "Clerk Ops",
        "digitalocean_ops": "DigitalOcean Ops",
        "gcp_ops": "GCP Ops",
        "local_ops": "Local Ops",
        "vercel_ops": "Vercel Ops",
        "project_organizer": "Project Organizer",
        "agentic_coder_optimizer": "Agentic Coder Optimizer",
        "tmux": "Tmux",
        # Universal agents
        "code_analyzer": "Code Analyzer",
        "content": "Content",
        "memory_manager": "Memory Manager",
        "product_owner": "Product Owner",
        "web_ui": "Web UI",
        "imagemagick": "ImageMagick",
        "ticketing": "Ticketing",
        # MPM-specific agents
        "mpm_agent_manager": "MPM Agent Manager",
        "mpm_skills_manager": "MPM Skills Manager",
        "tavily_research": "Research",  # Maps to Research
    }

    # Aliases and variations that map to canonical names
    # Keys are normalized (lowercase, underscores) and map to canonical keys
    ALIASES = {
        # Research variations
        "research": "research",
        "researcher": "research",
        "tavily_research": "research",
        # Engineer variations
        "engineer": "engineer",
        "engineering": "engineer",
        "dev": "engineer",
        "developer": "engineer",
        # Language-specific engineers
        "python_engineer": "python_engineer",
        "python": "python_engineer",
        "golang_engineer": "golang_engineer",
        "golang": "golang_engineer",
        "go_engineer": "golang_engineer",
        "java_engineer": "java_engineer",
        "java": "java_engineer",
        "javascript_engineer": "javascript_engineer",
        "javascript": "javascript_engineer",
        "js_engineer": "javascript_engineer",
        "typescript_engineer": "typescript_engineer",
        "typescript": "typescript_engineer",
        "ts_engineer": "typescript_engineer",
        "rust_engineer": "rust_engineer",
        "rust": "rust_engineer",
        "ruby_engineer": "ruby_engineer",
        "ruby": "ruby_engineer",
        "php_engineer": "php_engineer",
        "php": "php_engineer",
        "phoenix_engineer": "phoenix_engineer",
        "phoenix": "phoenix_engineer",
        "elixir_engineer": "phoenix_engineer",
        "nestjs_engineer": "nestjs_engineer",
        "nestjs": "nestjs_engineer",
        # Frontend engineers
        "react_engineer": "react_engineer",
        "react": "react_engineer",
        "nextjs_engineer": "nextjs_engineer",
        "nextjs": "nextjs_engineer",
        "next": "nextjs_engineer",
        "svelte_engineer": "svelte_engineer",
        "svelte": "svelte_engineer",
        "web_ui": "web_ui",
        # Mobile/Desktop engineers
        "dart_engineer": "dart_engineer",
        "dart": "dart_engineer",
        "flutter_engineer": "dart_engineer",
        "flutter": "dart_engineer",
        "tauri_engineer": "tauri_engineer",
        "tauri": "tauri_engineer",
        # Specialized engineers
        "prompt_engineer": "prompt_engineer",
        "refactoring_engineer": "refactoring_engineer",
        "refactoring": "refactoring_engineer",
        # QA variations
        "qa": "qa",
        "quality": "qa",
        "testing": "qa",
        "test": "qa",
        "api_qa": "api_qa",
        "web_qa": "web_qa",
        "real_user": "real_user",
        # Security variations
        "security": "security",
        "sec": "security",
        # Documentation variations
        "documentation": "documentation",
        "docs": "documentation",
        "doc": "documentation",
        "ticketing": "ticketing",
        # Ops variations
        "ops": "ops",
        "operations": "ops",
        "devops": "ops",
        "clerk_ops": "clerk_ops",
        "clerk": "clerk_ops",
        "digitalocean_ops": "digitalocean_ops",
        "digitalocean": "digitalocean_ops",
        "do_ops": "digitalocean_ops",
        "gcp_ops": "gcp_ops",
        "gcp": "gcp_ops",
        "google_cloud": "gcp_ops",
        "local_ops": "local_ops",
        "local": "local_ops",
        "vercel_ops": "vercel_ops",
        "vercel": "vercel_ops",
        "project_organizer": "project_organizer",
        "agentic_coder_optimizer": "agentic_coder_optimizer",
        "tmux": "tmux",
        "tmux_agent": "tmux",
        # Version Control variations
        "version_control": "version_control",
        "git": "version_control",
        "vcs": "version_control",
        # Data Engineer variations
        "data_engineer": "data_engineer",
        "data": "data_engineer",
        # Architect variations
        "architect": "architect",
        "architecture": "architect",
        "arch": "architect",
        # PM variations
        "pm": "pm",
        "project_manager": "pm",
        # Universal agents
        "code_analyzer": "code_analyzer",
        "analyzer": "code_analyzer",
        "content": "content",
        "content_agent": "content",
        "memory_manager": "memory_manager",
        "memory_manager_agent": "memory_manager",
        "product_owner": "product_owner",
        "po": "product_owner",
        "imagemagick": "imagemagick",
        # MPM-specific agents
        "mpm_agent_manager": "mpm_agent_manager",
        "agent_manager": "mpm_agent_manager",
        "mpm_skills_manager": "mpm_skills_manager",
        "skills_manager": "mpm_skills_manager",
    }

    # Agent colors for consistent display
    # Base agent colors
    AGENT_COLORS = {
        # Core agents
        "research": "\033[36m",  # Cyan
        "engineer": "\033[32m",  # Green
        "qa": "\033[33m",  # Yellow
        "security": "\033[31m",  # Red
        "documentation": "\033[34m",  # Blue
        "ops": "\033[35m",  # Magenta
        "version_control": "\033[37m",  # White
        "data_engineer": "\033[96m",  # Bright Cyan
        "architect": "\033[95m",  # Bright Magenta
        "pm": "\033[92m",  # Bright Green
        # Language-specific engineers (all use green variants)
        "python_engineer": "\033[32m",  # Green
        "golang_engineer": "\033[32m",  # Green
        "java_engineer": "\033[32m",  # Green
        "javascript_engineer": "\033[32m",  # Green
        "typescript_engineer": "\033[32m",  # Green
        "rust_engineer": "\033[32m",  # Green
        "ruby_engineer": "\033[32m",  # Green
        "php_engineer": "\033[32m",  # Green
        "phoenix_engineer": "\033[32m",  # Green
        "nestjs_engineer": "\033[32m",  # Green
        "react_engineer": "\033[32m",  # Green
        "nextjs_engineer": "\033[32m",  # Green
        "svelte_engineer": "\033[32m",  # Green
        "dart_engineer": "\033[32m",  # Green
        "tauri_engineer": "\033[32m",  # Green
        "prompt_engineer": "\033[32m",  # Green
        "refactoring_engineer": "\033[32m",  # Green
        "web_ui": "\033[32m",  # Green
        "imagemagick": "\033[32m",  # Green
        # QA variants (all use yellow)
        "api_qa": "\033[33m",  # Yellow
        "web_qa": "\033[33m",  # Yellow
        "real_user": "\033[33m",  # Yellow
        # Ops variants (all use magenta)
        "clerk_ops": "\033[35m",  # Magenta
        "digitalocean_ops": "\033[35m",  # Magenta
        "gcp_ops": "\033[35m",  # Magenta
        "local_ops": "\033[35m",  # Magenta
        "vercel_ops": "\033[35m",  # Magenta
        "project_organizer": "\033[35m",  # Magenta
        "agentic_coder_optimizer": "\033[35m",  # Magenta
        "tmux": "\033[35m",  # Magenta
        # Universal agents
        "code_analyzer": "\033[36m",  # Cyan (like research)
        "content": "\033[34m",  # Blue (like documentation)
        "memory_manager": "\033[36m",  # Cyan
        "product_owner": "\033[92m",  # Bright Green (like PM)
        "ticketing": "\033[34m",  # Blue (like documentation)
        # MPM-specific agents
        "mpm_agent_manager": "\033[95m",  # Bright Magenta
        "mpm_skills_manager": "\033[95m",  # Bright Magenta
    }

    COLOR_RESET = "\033[0m"

    @classmethod
    def normalize(cls, agent_name: str) -> str:
        """
        Normalize an agent name to its canonical form.

        Args:
            agent_name: The agent name to normalize

        Returns:
            The canonical agent name
        """
        if not agent_name:
            return "Engineer"  # Default

        # Clean the input: strip whitespace, convert to lowercase
        cleaned = agent_name.strip().lower()

        # Return default for whitespace-only input
        if not cleaned:
            return "Engineer"

        # Replace hyphens and spaces with underscores for consistent lookup
        cleaned = cleaned.replace("-", "_").replace(" ", "_")

        # Strip common suffixes before alias lookup
        # This handles cases like "research-agent" -> "research" or "python_engineer_agent" -> "python_engineer"
        for suffix in ("_agent", "_agent_agent"):
            if cleaned.endswith(suffix):
                cleaned = cleaned[: -len(suffix)]
                break

        # Check aliases first (exact match)
        if cleaned in cls.ALIASES:
            canonical_key = cls.ALIASES[cleaned]
            return cls.CANONICAL_NAMES.get(canonical_key, "Engineer")

        # Check if it's already a canonical key (exact match)
        if cleaned in cls.CANONICAL_NAMES:
            return cls.CANONICAL_NAMES[cleaned]

        # Try partial matching - but only if the cleaned name contains the alias as a word boundary
        # This prevents "python_engineer" from matching just "engineer"
        # Sort aliases by length (longest first) to ensure more specific matches take priority
        sorted_aliases = sorted(
            cls.ALIASES.items(), key=lambda x: len(x[0]), reverse=True
        )
        for alias, canonical_key in sorted_aliases:
            # Only match if the cleaned name starts with or ends with the alias
            # Or if the alias is a complete match (already handled above)
            if cleaned == alias:
                return cls.CANONICAL_NAMES.get(canonical_key, "Engineer")
            # Allow partial match only for generic aliases (single words like "python", "react")
            # Don't allow "engineer" to match inside "python_engineer"
            if "_" not in alias and alias in cleaned.split("_"):
                return cls.CANONICAL_NAMES.get(canonical_key, "Engineer")

        logger.warning(f"Unknown agent name '{agent_name}', defaulting to Engineer")
        return "Engineer"

    @classmethod
    def to_key(cls, agent_name: str) -> str:
        """
        Convert an agent name to its key format (lowercase with underscores).

        Args:
            agent_name: The agent name to convert

        Returns:
            The key format of the agent name
        """
        normalized = cls.normalize(agent_name)
        return normalized.lower().replace(" ", "_")

    @classmethod
    def to_todo_prefix(cls, agent_name: str) -> str:
        """
        Format agent name for TODO prefix (e.g., [Research]).

        Args:
            agent_name: The agent name to format

        Returns:
            The formatted TODO prefix
        """
        normalized = cls.normalize(agent_name)
        return f"[{normalized}]"

    @classmethod
    def colorize(cls, agent_name: str, text: Optional[str] = None) -> str:
        """
        Apply consistent color coding to agent names.

        Args:
            agent_name: The agent name to colorize
            text: Optional text to colorize (defaults to agent name)

        Returns:
            The colorized text
        """
        key = cls.to_key(agent_name)
        color = cls.AGENT_COLORS.get(key, "")
        display_text = text if text else cls.normalize(agent_name)

        if color:
            return f"{color}{display_text}{cls.COLOR_RESET}"
        return display_text

    @classmethod
    def extract_from_todo(cls, todo_text: str) -> Optional[str]:
        """
        Extract agent name from a TODO line.

        Args:
            todo_text: The TODO text (e.g., "[Research] Analyze patterns")

        Returns:
            The normalized agent name, or None if not found
        """
        import re

        # Match [Agent] at the beginning
        match = re.match(r"^\[([^\]]+)\]", todo_text.strip())
        if match:
            return cls.normalize(match.group(1))

        # Try to find agent mentions in the text
        text_lower = todo_text.lower()
        for alias, canonical_key in cls.ALIASES.items():
            if alias in text_lower:
                return cls.CANONICAL_NAMES.get(canonical_key)

        return None

    @classmethod
    def validate_todo_format(cls, todo_text: str) -> tuple[bool, Optional[str]]:
        """
        Validate that a TODO has proper agent prefix.

        Args:
            todo_text: The TODO text to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        agent = cls.extract_from_todo(todo_text)
        if not agent:
            return (
                False,
                "TODO must start with [Agent] prefix (e.g., [Research], [Engineer])",
            )

        # Check if it's a valid agent
        if cls.to_key(agent) not in cls.CANONICAL_NAMES:
            return (
                False,
                f"Unknown agent '{agent}'. Valid agents: {', '.join(cls.CANONICAL_NAMES.values())}",
            )

        return True, None

    @classmethod
    def to_task_format(cls, agent_name: str) -> str:
        """
        Convert agent name from TodoWrite format to Task tool format.

        Args:
            agent_name: The agent name in TodoWrite format (e.g., "Research", "Version Control")

        Returns:
            The agent name in Task tool format (e.g., "research", "version-control")

        Examples:
            "Research" → "research"
            "Version Control" → "version-control"
            "Data Engineer" → "data-engineer"
            "QA" → "qa"
        """
        # First normalize to canonical form
        normalized = cls.normalize(agent_name)
        # Convert to lowercase and replace spaces with hyphens
        return normalized.lower().replace(" ", "-")

    @classmethod
    def from_task_format(cls, task_format: str) -> str:
        """
        Convert agent name from Task tool format to TodoWrite format.

        Args:
            task_format: The agent name in Task tool format (e.g., "research", "version-control")

        Returns:
            The agent name in TodoWrite format (e.g., "Research", "Version Control")

        Examples:
            "research" → "Research"
            "version-control" → "Version Control"
            "data-engineer" → "Data Engineer"
            "qa" → "QA"
        """
        # Replace hyphens with underscores for lookup
        lookup_key = task_format.replace("-", "_")

        # Check if it's a valid canonical key
        if lookup_key in cls.CANONICAL_NAMES:
            return cls.CANONICAL_NAMES[lookup_key]

        # Try normalizing as-is
        return cls.normalize(task_format)


# Global instance for easy access
agent_name_normalizer = AgentNameNormalizer()
