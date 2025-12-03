"""Agent preset configurations for common development scenarios.

This module defines preset bundles of agents for typical development workflows.
Presets enable users to deploy entire agent stacks with a single command like:
    claude-mpm agents deploy --preset python-min
    claude-mpm agents deploy --preset python-max

Design Decision: Presets use agent IDs from AUTO-DEPLOY-INDEX.md format
(e.g., "universal/memory-manager", "engineer/backend/python-engineer").

Architecture:
- MIN presets: Essential agents only (faster startup, lower resource usage)
- MAX presets: Full toolchain with specialized agents (comprehensive coverage)
- All presets include: mpm-agent-manager, mpm-skills-manager, engineer, research, documentation

Trade-offs:
- Simplicity: Static lists are easy to maintain
- Flexibility: Dynamic functions allow auto-detection (future enhancement)
- Discoverability: Presets shown in CLI help and error messages
"""

from typing import Any, Callable, Dict, List, Union

# Type for preset resolver (can be static list or dynamic function)
PresetResolver = Union[List[str], Callable[[], List[str]]]

# Core agents included in ALL presets (MIN and MAX)
CORE_AGENTS = [
    "claude-mpm/mpm-agent-manager",  # Agent lifecycle management
    "claude-mpm/mpm-skills-manager",  # Skills management
    "universal/research",  # Codebase investigation
    "documentation/documentation",  # Documentation generation
    "engineer/core/engineer",  # General-purpose engineering
]

PRESETS: Dict[str, Dict[str, Any]] = {
    # ========================================
    # Universal Minimal Preset
    # ========================================
    "minimal": {
        "description": "Core agents only - universal starter kit",
        "agents": CORE_AGENTS
        + [
            "qa/qa",
            "ops/core/ops",
        ],
        "use_cases": ["Any project type", "Quick start", "Learning"],
    },
    # ========================================
    # Python Toolchain Presets
    # ========================================
    "python-min": {
        "description": "Python essentials (8 agents)",
        "agents": CORE_AGENTS
        + [
            "engineer/backend/python-engineer",
            "qa/qa",
            "ops/core/ops",
        ],
        "use_cases": [
            "Python scripts",
            "Small Python projects",
            "FastAPI microservices",
        ],
    },
    "python-max": {
        "description": "Full Python development stack (14+ agents)",
        "agents": CORE_AGENTS
        + [
            "engineer/backend/python-engineer",
            "universal/code-analyzer",
            "universal/memory-manager",
            "qa/qa",
            "qa/api-qa",
            "ops/core/ops",
            "security/security",
            "documentation/ticketing",
            "refactoring/refactoring-engineer",
        ],
        "use_cases": ["FastAPI production", "Django projects", "Python APIs at scale"],
    },
    # ========================================
    # JavaScript/TypeScript Toolchain Presets
    # ========================================
    "javascript-min": {
        "description": "Node.js essentials (8 agents)",
        "agents": CORE_AGENTS
        + [
            "engineer/backend/javascript-engineer",
            "qa/qa",
            "ops/core/ops",
        ],
        "use_cases": ["Express.js", "Node.js scripts", "Backend microservices"],
    },
    "javascript-max": {
        "description": "Full Node.js development stack (13+ agents)",
        "agents": CORE_AGENTS
        + [
            "engineer/backend/javascript-engineer",
            "engineer/data/typescript-engineer",
            "universal/code-analyzer",
            "qa/qa",
            "qa/api-qa",
            "ops/core/ops",
            "security/security",
            "documentation/ticketing",
        ],
        "use_cases": ["Express.js production", "Fastify", "Koa", "Enterprise Node.js"],
    },
    # ========================================
    # React Toolchain Presets
    # ========================================
    "react-min": {
        "description": "React essentials (8 agents)",
        "agents": CORE_AGENTS
        + [
            "engineer/frontend/react-engineer",
            "qa/qa",
            "ops/core/ops",
        ],
        "use_cases": ["React SPAs", "Component libraries", "Quick prototypes"],
    },
    "react-max": {
        "description": "Full React development stack (12+ agents)",
        "agents": CORE_AGENTS
        + [
            "engineer/frontend/react-engineer",
            "engineer/data/typescript-engineer",
            "universal/code-analyzer",
            "qa/qa",
            "qa/web-qa",
            "ops/core/ops",
            "security/security",
        ],
        "use_cases": [
            "React production apps",
            "Component systems",
            "Frontend at scale",
        ],
    },
    # ========================================
    # Next.js Toolchain Presets
    # ========================================
    "nextjs-min": {
        "description": "Next.js essentials (9 agents)",
        "agents": CORE_AGENTS
        + [
            "engineer/frontend/nextjs-engineer",
            "engineer/frontend/react-engineer",
            "qa/qa",
            "ops/platform/vercel-ops",
        ],
        "use_cases": ["Next.js apps", "Vercel deployment", "Full-stack TypeScript"],
    },
    "nextjs-max": {
        "description": "Full Next.js development stack (15+ agents)",
        "agents": CORE_AGENTS
        + [
            "engineer/frontend/nextjs-engineer",
            "engineer/frontend/react-engineer",
            "engineer/data/typescript-engineer",
            "universal/code-analyzer",
            "universal/memory-manager",
            "qa/qa",
            "qa/web-qa",
            "qa/api-qa",
            "ops/core/ops",
            "ops/platform/vercel-ops",
            "security/security",
            "documentation/ticketing",
        ],
        "use_cases": ["Next.js production", "Enterprise apps", "Full-stack at scale"],
    },
    # ========================================
    # Go Toolchain Presets
    # ========================================
    "golang-min": {
        "description": "Go essentials (8 agents)",
        "agents": CORE_AGENTS
        + [
            "engineer/backend/golang-engineer",
            "qa/qa",
            "ops/core/ops",
        ],
        "use_cases": ["Go microservices", "CLI tools", "Small Go projects"],
    },
    "golang-max": {
        "description": "Full Go development stack (12+ agents)",
        "agents": CORE_AGENTS
        + [
            "engineer/backend/golang-engineer",
            "universal/code-analyzer",
            "qa/qa",
            "qa/api-qa",
            "ops/core/ops",
            "security/security",
            "documentation/ticketing",
        ],
        "use_cases": [
            "Go production APIs",
            "Cloud-native apps",
            "Microservices at scale",
        ],
    },
    # ========================================
    # Rust Toolchain Presets
    # ========================================
    "rust-min": {
        "description": "Rust essentials (8 agents)",
        "agents": CORE_AGENTS
        + [
            "engineer/backend/rust-engineer",
            "qa/qa",
            "ops/core/ops",
        ],
        "use_cases": ["Rust CLI tools", "Systems programming", "WebAssembly"],
    },
    "rust-max": {
        "description": "Full Rust development stack (11+ agents)",
        "agents": CORE_AGENTS
        + [
            "engineer/backend/rust-engineer",
            "universal/code-analyzer",
            "qa/qa",
            "ops/core/ops",
            "security/security",
            "documentation/ticketing",
        ],
        "use_cases": [
            "Rust production systems",
            "Performance-critical apps",
            "Safe systems",
        ],
    },
    # ========================================
    # Java Toolchain Presets
    # ========================================
    "java-min": {
        "description": "Java essentials (8 agents)",
        "agents": CORE_AGENTS
        + [
            "engineer/backend/java-engineer",
            "qa/qa",
            "ops/core/ops",
        ],
        "use_cases": [
            "Spring Boot basics",
            "Java microservices",
            "Small Java projects",
        ],
    },
    "java-max": {
        "description": "Full Java development stack (13+ agents)",
        "agents": CORE_AGENTS
        + [
            "engineer/backend/java-engineer",
            "universal/code-analyzer",
            "qa/qa",
            "qa/api-qa",
            "ops/core/ops",
            "security/security",
            "documentation/ticketing",
            "refactoring/refactoring-engineer",
        ],
        "use_cases": [
            "Spring Boot production",
            "Enterprise Java",
            "Microservices at scale",
        ],
    },
    # ========================================
    # Mobile/Flutter Toolchain Presets
    # ========================================
    "flutter-min": {
        "description": "Flutter essentials (8 agents)",
        "agents": CORE_AGENTS
        + [
            "engineer/mobile/dart-engineer",
            "qa/qa",
            "ops/core/ops",
        ],
        "use_cases": ["Flutter apps", "Mobile prototypes", "Cross-platform basics"],
    },
    "flutter-max": {
        "description": "Full Flutter development stack (12+ agents)",
        "agents": CORE_AGENTS
        + [
            "engineer/mobile/dart-engineer",
            "universal/code-analyzer",
            "qa/qa",
            "ops/core/ops",
            "security/security",
            "documentation/ticketing",
            "universal/memory-manager",
        ],
        "use_cases": ["Flutter production", "iOS/Android apps", "Enterprise mobile"],
    },
    # ========================================
    # Legacy Presets (kept for backward compatibility)
    # ========================================
    "python-dev": {
        "description": "Python backend (LEGACY - use python-max)",
        "agents": CORE_AGENTS
        + [
            "engineer/backend/python-engineer",
            "qa/qa",
            "qa/api-qa",
            "ops/core/ops",
            "security/security",
        ],
        "use_cases": ["Legacy preset - migrate to python-max"],
    },
    "javascript-backend": {
        "description": "Node.js backend (LEGACY - use javascript-max)",
        "agents": CORE_AGENTS
        + [
            "engineer/backend/javascript-engineer",
            "qa/qa",
            "qa/api-qa",
            "ops/core/ops",
            "security/security",
        ],
        "use_cases": ["Legacy preset - migrate to javascript-max"],
    },
    "react-dev": {
        "description": "React development (LEGACY - use react-max)",
        "agents": CORE_AGENTS
        + [
            "engineer/frontend/react-engineer",
            "engineer/data/typescript-engineer",
            "qa/qa",
            "qa/web-qa",
            "ops/core/ops",
            "security/security",
        ],
        "use_cases": ["Legacy preset - migrate to react-max"],
    },
    "nextjs-fullstack": {
        "description": "Next.js full-stack (LEGACY - use nextjs-max)",
        "agents": CORE_AGENTS
        + [
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
        "use_cases": ["Legacy preset - migrate to nextjs-max"],
    },
    "rust-dev": {
        "description": "Rust development (LEGACY - use rust-max)",
        "agents": CORE_AGENTS
        + [
            "engineer/backend/rust-engineer",
            "qa/qa",
            "ops/core/ops",
            "security/security",
        ],
        "use_cases": ["Legacy preset - migrate to rust-max"],
    },
    "golang-dev": {
        "description": "Go development (LEGACY - use golang-max)",
        "agents": CORE_AGENTS
        + [
            "engineer/backend/golang-engineer",
            "qa/qa",
            "qa/api-qa",
            "ops/core/ops",
            "security/security",
        ],
        "use_cases": ["Legacy preset - migrate to golang-max"],
    },
    "java-dev": {
        "description": "Java/Spring Boot (LEGACY - use java-max)",
        "agents": CORE_AGENTS
        + [
            "engineer/backend/java-engineer",
            "qa/qa",
            "qa/api-qa",
            "ops/core/ops",
            "security/security",
            "documentation/ticketing",
        ],
        "use_cases": ["Legacy preset - migrate to java-max"],
    },
    "mobile-flutter": {
        "description": "Flutter mobile (LEGACY - use flutter-max)",
        "agents": CORE_AGENTS
        + [
            "engineer/mobile/dart-engineer",
            "qa/qa",
            "ops/core/ops",
            "security/security",
            "documentation/ticketing",
        ],
        "use_cases": ["Legacy preset - migrate to flutter-max"],
    },
    "data-eng": {
        "description": "Data engineering stack (12 agents)",
        "agents": CORE_AGENTS
        + [
            "engineer/backend/python-engineer",
            "engineer/data/data-engineer",
            "universal/code-analyzer",
            "qa/qa",
            "ops/core/ops",
            "security/security",
            "documentation/ticketing",
        ],
        "use_cases": ["dbt projects", "Airflow", "Data pipelines", "ETL"],
    },
}


def get_preset_names() -> List[str]:
    """Get list of all available preset names.

    Returns:
        List of preset names (e.g., ['minimal', 'python-min', 'python-max', ...])

    Example:
        >>> names = get_preset_names()
        >>> 'python-min' in names
        True
    """
    return list(PRESETS.keys())


def get_preset_info(preset_name: str) -> Dict[str, Any]:
    """Get preset metadata (description, use cases, agent count).

    Args:
        preset_name: Name of preset (e.g., 'python-min')

    Returns:
        Dict with keys:
        - name: Preset name
        - description: Human-readable description
        - agent_count: Number of agents in preset
        - use_cases: List of use case strings

    Raises:
        ValueError: If preset name is invalid

    Example:
        >>> info = get_preset_info('python-min')
        >>> info['agent_count']
        8
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
        preset_name: Name of preset (e.g., 'python-min')

    Returns:
        List of agent IDs (e.g., ["claude-mpm/mpm-agent-manager", ...])

    Raises:
        ValueError: If preset name is invalid

    Example:
        >>> agents = get_preset_agents('python-min')
        >>> len(agents)
        8
        >>> 'claude-mpm/mpm-agent-manager' in agents
        True
    """
    if preset_name not in PRESETS:
        raise ValueError(f"Unknown preset: {preset_name}")

    return PRESETS[preset_name]["agents"]
