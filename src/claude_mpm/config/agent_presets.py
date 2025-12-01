"""Agent preset configurations for common development scenarios.

This module defines preset bundles of agents for typical development workflows.
Presets enable users to deploy entire agent stacks with a single command like:
    claude-mpm agents deploy --preset python-dev

Design Decision: Presets use agent IDs from AUTO-DEPLOY-INDEX.md format
(e.g., "universal/memory-manager", "engineer/backend/python-engineer").

Trade-offs:
- Simplicity: Static lists are easy to maintain
- Flexibility: Dynamic functions allow auto-detection (future enhancement)
- Discoverability: Presets shown in CLI help and error messages
"""

from typing import Any, Callable, Dict, List, Union

# Type for preset resolver (can be static list or dynamic function)
PresetResolver = Union[List[str], Callable[[], List[str]]]

PRESETS: Dict[str, Dict[str, Any]] = {
    "minimal": {
        "description": "6 core agents for any project",
        "agents": [
            "universal/memory-manager",
            "universal/research",
            "documentation/documentation",
            "engineer/backend/python-engineer",  # Will be language-specific in future
            "qa/qa",
            "ops/core/ops",
        ],
        "use_cases": ["Micro projects", "Quick prototypes", "Learning"],
    },
    "python-dev": {
        "description": "Python backend development stack (8 agents)",
        "agents": [
            "universal/memory-manager",
            "universal/research",
            "documentation/documentation",
            "engineer/backend/python-engineer",
            "qa/qa",
            "qa/api-qa",
            "ops/core/ops",
            "security/security",
        ],
        "use_cases": ["FastAPI projects", "Django projects", "Python APIs"],
    },
    "python-fullstack": {
        "description": "Python backend + React frontend (12 agents)",
        "agents": [
            "universal/memory-manager",
            "universal/research",
            "universal/code-analyzer",
            "documentation/documentation",
            "documentation/ticketing",
            "engineer/backend/python-engineer",
            "engineer/frontend/react-engineer",
            "qa/qa",
            "qa/api-qa",
            "qa/web-qa",
            "ops/core/ops",
            "security/security",
        ],
        "use_cases": ["FastAPI + React", "Django + React", "Full-stack Python"],
    },
    "javascript-backend": {
        "description": "Node.js backend development (8 agents)",
        "agents": [
            "universal/memory-manager",
            "universal/research",
            "documentation/documentation",
            "engineer/backend/javascript-engineer",
            "qa/qa",
            "qa/api-qa",
            "ops/core/ops",
            "security/security",
        ],
        "use_cases": ["Express.js", "Fastify", "Koa", "Node.js APIs"],
    },
    "react-dev": {
        "description": "React frontend development (9 agents)",
        "agents": [
            "universal/memory-manager",
            "universal/research",
            "documentation/documentation",
            "engineer/frontend/react-engineer",
            "engineer/data/typescript-engineer",
            "qa/qa",
            "qa/web-qa",
            "ops/core/ops",
            "security/security",
        ],
        "use_cases": ["React SPAs", "Component libraries", "Frontend projects"],
    },
    "nextjs-fullstack": {
        "description": "Next.js full-stack development (13 agents)",
        "agents": [
            "universal/memory-manager",
            "universal/research",
            "universal/code-analyzer",
            "documentation/documentation",
            "engineer/frontend/nextjs-engineer",
            "engineer/frontend/react-engineer",
            "engineer/data/typescript-engineer",
            "qa/qa",
            "qa/web-qa",
            "ops/core/ops",
            "ops/platform/vercel-ops",
            "security/security",
            "documentation/ticketing",
        ],
        "use_cases": ["Next.js apps", "Vercel deployments", "Full-stack TypeScript"],
    },
    "rust-dev": {
        "description": "Rust systems development (7 agents)",
        "agents": [
            "universal/memory-manager",
            "universal/research",
            "documentation/documentation",
            "engineer/backend/rust-engineer",
            "qa/qa",
            "ops/core/ops",
            "security/security",
        ],
        "use_cases": ["Rust systems", "CLI tools", "WebAssembly"],
    },
    "golang-dev": {
        "description": "Go backend development (8 agents)",
        "agents": [
            "universal/memory-manager",
            "universal/research",
            "documentation/documentation",
            "engineer/backend/golang-engineer",
            "qa/qa",
            "qa/api-qa",
            "ops/core/ops",
            "security/security",
        ],
        "use_cases": ["Go APIs", "Microservices", "Cloud-native apps"],
    },
    "java-dev": {
        "description": "Java/Spring Boot development (9 agents)",
        "agents": [
            "universal/memory-manager",
            "universal/research",
            "documentation/documentation",
            "engineer/backend/java-engineer",
            "qa/qa",
            "qa/api-qa",
            "ops/core/ops",
            "security/security",
            "documentation/ticketing",
        ],
        "use_cases": ["Spring Boot", "Java EE", "Enterprise applications"],
    },
    "mobile-flutter": {
        "description": "Flutter mobile development (8 agents)",
        "agents": [
            "universal/memory-manager",
            "universal/research",
            "documentation/documentation",
            "engineer/mobile/dart-engineer",
            "qa/qa",
            "ops/core/ops",
            "security/security",
            "documentation/ticketing",
        ],
        "use_cases": ["Flutter apps", "Cross-platform mobile", "iOS/Android"],
    },
    "data-eng": {
        "description": "Data engineering stack (10 agents)",
        "agents": [
            "universal/memory-manager",
            "universal/research",
            "documentation/documentation",
            "engineer/backend/python-engineer",
            "engineer/data/data-engineer",
            "qa/qa",
            "ops/core/ops",
            "security/security",
            "documentation/ticketing",
            "universal/code-analyzer",
        ],
        "use_cases": ["dbt projects", "Airflow", "Data pipelines", "ETL"],
    },
}


def get_preset_names() -> List[str]:
    """Get list of all available preset names.

    Returns:
        List of preset names (e.g., ['minimal', 'python-dev', ...])

    Example:
        >>> names = get_preset_names()
        >>> 'minimal' in names
        True
    """
    return list(PRESETS.keys())


def get_preset_info(preset_name: str) -> Dict[str, Any]:
    """Get preset metadata (description, use cases, agent count).

    Args:
        preset_name: Name of preset (e.g., 'python-dev')

    Returns:
        Dict with keys:
        - name: Preset name
        - description: Human-readable description
        - agent_count: Number of agents in preset
        - use_cases: List of use case strings

    Raises:
        ValueError: If preset name is invalid

    Example:
        >>> info = get_preset_info('minimal')
        >>> info['agent_count']
        6
    """
    if preset_name not in PRESETS:
        raise ValueError(f"Unknown preset: {preset_name}")

    preset = PRESETS[preset_name]
    return {
        "name": preset_name,
        "description": preset["description"],
        "agent_count": len(preset["agents"]),
        "use_cases": preset["use_cases"],
    }


def get_preset_agents(preset_name: str) -> List[str]:
    """Get agent list for preset.

    Args:
        preset_name: Name of preset (e.g., 'python-dev')

    Returns:
        List of agent IDs (e.g., ["universal/memory-manager", ...])

    Raises:
        ValueError: If preset name is invalid

    Example:
        >>> agents = get_preset_agents('minimal')
        >>> len(agents)
        6
        >>> 'universal/memory-manager' in agents
        True
    """
    if preset_name not in PRESETS:
        raise ValueError(f"Unknown preset: {preset_name}")

    return PRESETS[preset_name]["agents"]
