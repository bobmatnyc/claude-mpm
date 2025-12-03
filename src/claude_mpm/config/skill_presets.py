"""Skill preset configurations for common development scenarios.

This module defines preset bundles of skills for typical development workflows.
Presets enable users to deploy entire skill stacks with a single command like:
    claude-mpm skills deploy --preset python-min
    claude-mpm skills deploy --preset python-max

Design Decision: Presets use skill IDs from skill manifest format.

Architecture:
- MIN presets: Essential skills only (faster startup, lower resource usage)
- MAX presets: Full skill toolkit with specialized capabilities (comprehensive coverage)
- All presets include: skill-creator for extending capabilities

Trade-offs:
- Simplicity: Static lists are easy to maintain
- Flexibility: Dynamic functions allow auto-detection (future enhancement)
- Discoverability: Presets shown in CLI help and error messages
"""

from typing import Any, Callable, Dict, List, Union

# Type for preset resolver (can be static list or dynamic function)
PresetResolver = Union[List[str], Callable[[], List[str]]]

# Core skills included in ALL presets (MIN and MAX)
CORE_SKILLS = [
    "universal-main-skill-creator",  # Skill creation and management
]

PRESETS: Dict[str, Dict[str, Any]] = {
    # ========================================
    # Universal Minimal Preset
    # ========================================
    "minimal": {
        "description": "Core skills only - universal starter kit",
        "skills": CORE_SKILLS,
        "use_cases": ["Any project type", "Quick start", "Learning"],
    },
    # ========================================
    # Python Toolchain Presets
    # ========================================
    "python-min": {
        "description": "Python essentials (4 skills)",
        "skills": CORE_SKILLS
        + [
            "toolchains-python-testing-pytest",
            "toolchains-python-async-asyncio",
            "toolchains-python-tooling-mypy",
        ],
        "use_cases": [
            "Python scripts",
            "Small Python projects",
            "FastAPI microservices",
        ],
    },
    "python-max": {
        "description": "Full Python skill stack (8+ skills)",
        "skills": CORE_SKILLS
        + [
            "toolchains-python-frameworks-flask",
            "toolchains-python-testing-pytest",
            "toolchains-python-async-asyncio",
            "toolchains-python-tooling-mypy",
            "universal-testing-testing-anti-patterns",
            "universal-testing-condition-based-waiting",
            "universal-debugging-verification-before-completion",
        ],
        "use_cases": ["FastAPI production", "Django projects", "Python APIs at scale"],
    },
    # ========================================
    # JavaScript/TypeScript Toolchain Presets
    # ========================================
    "javascript-min": {
        "description": "Node.js essentials (3 skills)",
        "skills": CORE_SKILLS
        + [
            "toolchains-javascript-frameworks-react",
            "toolchains-javascript-tooling-biome",
        ],
        "use_cases": ["Express.js", "Node.js scripts", "Backend microservices"],
    },
    "javascript-max": {
        "description": "Full Node.js skill stack (7+ skills)",
        "skills": CORE_SKILLS
        + [
            "toolchains-javascript-frameworks-react",
            "toolchains-javascript-frameworks-vue",
            "toolchains-javascript-tooling-biome",
            "toolchains-typescript-testing-vitest",
            "toolchains-typescript-testing-jest",
            "universal-testing-testing-anti-patterns",
        ],
        "use_cases": ["Express.js production", "Fastify", "Koa", "Enterprise Node.js"],
    },
    # ========================================
    # React Toolchain Presets
    # ========================================
    "react-min": {
        "description": "React essentials (3 skills)",
        "skills": CORE_SKILLS
        + [
            "toolchains-javascript-frameworks-react",
            "toolchains-typescript-core",
        ],
        "use_cases": ["React SPAs", "Component libraries", "Quick prototypes"],
    },
    "react-max": {
        "description": "Full React skill stack (8+ skills)",
        "skills": CORE_SKILLS
        + [
            "toolchains-javascript-frameworks-react",
            "toolchains-javascript-frameworks-react-state-machine",
            "toolchains-typescript-core",
            "toolchains-typescript-testing-vitest",
            "toolchains-ui-components-headlessui",
            "universal-testing-testing-anti-patterns",
            "universal-architecture-software-patterns",
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
        "description": "Next.js essentials (4 skills)",
        "skills": CORE_SKILLS
        + [
            "toolchains-nextjs-core",
            "toolchains-javascript-frameworks-react",
            "toolchains-typescript-core",
        ],
        "use_cases": ["Next.js apps", "Vercel deployment", "Full-stack TypeScript"],
    },
    "nextjs-max": {
        "description": "Full Next.js skill stack (10+ skills)",
        "skills": CORE_SKILLS
        + [
            "toolchains-nextjs-core",
            "toolchains-nextjs-v16",
            "toolchains-javascript-frameworks-react",
            "toolchains-javascript-frameworks-react-state-machine",
            "toolchains-typescript-core",
            "toolchains-typescript-data-prisma",
            "toolchains-typescript-data-drizzle",
            "toolchains-typescript-testing-vitest",
            "universal-architecture-software-patterns",
        ],
        "use_cases": ["Next.js production", "Enterprise apps", "Full-stack at scale"],
    },
    # ========================================
    # TypeScript/Data Toolchain Presets
    # ========================================
    "typescript-min": {
        "description": "TypeScript essentials (3 skills)",
        "skills": CORE_SKILLS
        + [
            "toolchains-typescript-core",
            "toolchains-typescript-testing-vitest",
        ],
        "use_cases": ["Type-safe apps", "TypeScript projects", "Node.js with types"],
    },
    "typescript-max": {
        "description": "Full TypeScript skill stack (8+ skills)",
        "skills": CORE_SKILLS
        + [
            "toolchains-typescript-core",
            "toolchains-typescript-testing-vitest",
            "toolchains-typescript-testing-jest",
            "toolchains-typescript-data-prisma",
            "toolchains-typescript-data-drizzle",
            "toolchains-typescript-data-kysely",
            "universal-architecture-software-patterns",
        ],
        "use_cases": ["Enterprise TypeScript", "Full-stack apps", "Type-safe APIs"],
    },
    # ========================================
    # Rust Toolchain Presets
    # ========================================
    "rust-min": {
        "description": "Rust essentials (2 skills)",
        "skills": CORE_SKILLS
        + [
            "toolchains-rust-desktop-applications",
        ],
        "use_cases": ["Rust CLI tools", "Systems programming", "WebAssembly"],
    },
    "rust-max": {
        "description": "Full Rust skill stack (4+ skills)",
        "skills": CORE_SKILLS
        + [
            "toolchains-rust-desktop-applications",
            "toolchains-rust-frameworks-tauri",
            "universal-architecture-software-patterns",
        ],
        "use_cases": [
            "Rust production systems",
            "Performance-critical apps",
            "Safe systems",
        ],
    },
    # ========================================
    # WordPress Toolchain Presets
    # ========================================
    "wordpress-min": {
        "description": "WordPress essentials (2 skills)",
        "skills": CORE_SKILLS
        + [
            "toolchains-php-frameworks-wordpress-plugin-fundamentals",
        ],
        "use_cases": [
            "WordPress plugins",
            "Theme customization",
            "Quick WordPress dev",
        ],
    },
    "wordpress-max": {
        "description": "Full WordPress skill stack (3+ skills)",
        "skills": CORE_SKILLS
        + [
            "toolchains-php-frameworks-wordpress-plugin-fundamentals",
            "toolchains-php-frameworks-wordpress-block-editor",
            "toolchains-php-frameworks-espocrm",
        ],
        "use_cases": ["WordPress production", "Block themes", "Custom blocks", "FSE"],
    },
    # ========================================
    # AI/MCP Toolchain Presets
    # ========================================
    "ai-min": {
        "description": "AI essentials (2 skills)",
        "skills": CORE_SKILLS
        + [
            "toolchains-ai-protocols-mcp",
        ],
        "use_cases": ["MCP servers", "Claude integrations", "AI tools"],
    },
    "ai-max": {
        "description": "Full AI skill stack (3+ skills)",
        "skills": CORE_SKILLS
        + [
            "toolchains-ai-protocols-mcp",
            "toolchains-ai-services-openrouter",
            "universal-main-artifacts-builder",
        ],
        "use_cases": ["Multi-model AI apps", "Claude Desktop extensions", "AI tooling"],
    },
    # ========================================
    # Svelte Toolchain Presets
    # ========================================
    "svelte-min": {
        "description": "Svelte essentials (2 skills)",
        "skills": CORE_SKILLS
        + [
            "toolchains-javascript-frameworks-svelte",
        ],
        "use_cases": ["Svelte apps", "Reactive UIs", "Minimal JavaScript"],
    },
    "svelte-max": {
        "description": "Full Svelte skill stack (3+ skills)",
        "skills": CORE_SKILLS
        + [
            "toolchains-javascript-frameworks-svelte",
            "toolchains-javascript-frameworks-sveltekit",
            "toolchains-typescript-core",
        ],
        "use_cases": ["SvelteKit production", "Full-stack Svelte", "SSR/SSG apps"],
    },
    # ========================================
    # Universal/Testing Toolchain Presets
    # ========================================
    "testing-min": {
        "description": "Testing essentials (3 skills)",
        "skills": CORE_SKILLS
        + [
            "universal-testing-testing-anti-patterns",
            "universal-testing-condition-based-waiting",
        ],
        "use_cases": ["Test quality", "Async testing", "Test improvement"],
    },
    "testing-max": {
        "description": "Full testing skill stack (6+ skills)",
        "skills": CORE_SKILLS
        + [
            "universal-testing-testing-anti-patterns",
            "universal-testing-condition-based-waiting",
            "universal-debugging-verification-before-completion",
            "toolchains-typescript-testing-vitest",
            "toolchains-typescript-testing-jest",
            "toolchains-python-testing-pytest",
        ],
        "use_cases": ["Comprehensive testing", "Test automation", "Quality assurance"],
    },
    # ========================================
    # Collaboration Toolchain Presets
    # ========================================
    "collaboration-min": {
        "description": "Collaboration essentials (2 skills)",
        "skills": CORE_SKILLS
        + [
            "universal-collaboration-brainstorming",
        ],
        "use_cases": ["Idea refinement", "Design thinking", "Feature planning"],
    },
    "collaboration-max": {
        "description": "Full collaboration skill stack (4+ skills)",
        "skills": CORE_SKILLS
        + [
            "universal-collaboration-brainstorming",
            "universal-collaboration-writing-plans",
            "universal-collaboration-requesting-code-review",
            "universal-collaboration-dispatching-parallel-agents",
        ],
        "use_cases": ["Team coordination", "Code reviews", "Planning", "Parallel work"],
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
    """Get preset metadata (description, use cases, skill count).

    Args:
        preset_name: Name of preset (e.g., 'python-min')

    Returns:
        Dict with keys:
        - name: Preset name
        - description: Human-readable description
        - skill_count: Number of skills in preset
        - use_cases: List of use case strings

    Raises:
        ValueError: If preset name is invalid

    Example:
        >>> info = get_preset_info('python-min')
        >>> info['skill_count']
        4
    """
    if preset_name not in PRESETS:
        raise ValueError(f"Unknown preset: {preset_name}")

    preset = PRESETS[preset_name]
    return {
        "name": preset_name,
        "description": preset["description"],
        "skill_count": len(preset["skills"]),
        "use_cases": preset["use_cases"],
    }


def get_preset_skills(preset_name: str) -> List[str]:
    """Get skill list for preset.

    Args:
        preset_name: Name of preset (e.g., 'python-min')

    Returns:
        List of skill IDs (e.g., ["universal-main-skill-creator", ...])

    Raises:
        ValueError: If preset name is invalid

    Example:
        >>> skills = get_preset_skills('python-min')
        >>> len(skills)
        4
        >>> 'universal-main-skill-creator' in skills
        True
    """
    if preset_name not in PRESETS:
        raise ValueError(f"Unknown preset: {preset_name}")

    return PRESETS[preset_name]["skills"]
