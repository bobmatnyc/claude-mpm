"""Validation tests for skill_to_agent_mapping.yaml configuration.

WHY: Prevent configuration errors that cause orphan detection failures.
These tests validate mapping consistency and prevent language-specific skills
from being incorrectly mapped to generic agents.

References:
- Bug: Orphan skill detection not working (2025-12-30)
- Fix: docs/bugfixes/orphan-skill-detection-fix-2025-12-30.md
"""

from pathlib import Path

import pytest
import yaml

# Path to configuration file
CONFIG_PATH = (
    Path(__file__).parent.parent.parent
    / "src"
    / "claude_mpm"
    / "config"
    / "skill_to_agent_mapping.yaml"
)

# Language-specific toolchain patterns
# Format: {language_prefix: [allowed_language_engineers]}
# Generic agents can be added via VALID_CROSS_MAPPINGS below
LANGUAGE_TOOLCHAINS = {
    "toolchains/python": ["python-engineer"],
    "toolchains/typescript": ["typescript-engineer", "javascript-engineer"],
    "toolchains/javascript": ["javascript-engineer", "typescript-engineer"],
    "toolchains/golang": ["golang-engineer"],
    "toolchains/rust": ["rust-engineer", "tauri-engineer"],
    "toolchains/php": ["php-engineer"],
    "toolchains/elixir": ["phoenix-engineer"],
    "toolchains/java": ["java-engineer"],
    "toolchains/ruby": ["ruby-engineer"],
    "toolchains/dart": ["dart-engineer"],
}

# Valid cross-mappings where generic agents ARE allowed for language-specific skills
# Format: {skill_path_prefix: [allowed_generic_agents]}
VALID_CROSS_MAPPINGS = {
    # Web UI frameworks in JS/TS (React, Next.js, Svelte, Vue)
    "toolchains/javascript/frameworks": ["web-ui"],
    "toolchains/javascript/build/vite": ["web-ui"],
    "toolchains/typescript/state": ["web-ui"],  # Zustand, TanStack Query
    "toolchains/ui": ["web-ui"],  # UI component libraries
    "toolchains/nextjs": ["web-ui"],  # Next.js-specific
    # Data engineer needs data patterns across languages
    "toolchains/python/data": ["data-engineer"],
    "toolchains/python/async": ["data-engineer"],  # Async patterns for data pipelines
    "toolchains/python/testing": ["data-engineer"],  # Testing data pipelines
    "toolchains/python/tooling": ["data-engineer"],  # Type checking for data code
    "toolchains/python/validation": ["data-engineer"],  # Pydantic for data validation
    "toolchains/python/frameworks/django": ["data-engineer"],  # Django ORM for data
    "toolchains/typescript/data": ["data-engineer"],  # Drizzle, Kysely, Prisma
    "toolchains/platforms/backend/supabase": [
        "data-engineer"
    ],  # Multi-language backend
    # QA needs testing tools across languages
    "toolchains/javascript/testing": ["web-qa"],
    "toolchains/typescript/testing": ["web-qa"],
    # Security for WordPress (PHP-specific security patterns)
    # NOTE: This was removed in the fix - WordPress security is PHP-only
}

# Generic agents that should NOT be in language-specific toolchains
GENERIC_AGENTS = {
    "web-ui",
    "data-engineer",
    "security",
    "qa",
    "web-qa",
    "api-qa",
    "ops",
    "local-ops",
    "vercel-ops",
    "gcp-ops",
    "clerk-ops",
    "documentation",
    "ticketing",
    "research",
    "product-owner",
    "project-organizer",
    "memory-manager",
}


@pytest.fixture
def skill_mapping_config():
    """Load skill_to_agent_mapping.yaml configuration."""
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_config_file_exists():
    """Verify configuration file exists."""
    assert CONFIG_PATH.exists(), f"Configuration file not found: {CONFIG_PATH}"


def test_config_has_required_sections(skill_mapping_config):
    """Verify configuration has all required sections."""
    required_sections = ["skill_mappings", "all_agents_list", "inference_rules"]

    for section in required_sections:
        assert section in skill_mapping_config, f"Missing required section: {section}"


def test_language_toolchains_not_mapped_to_generic_agents(skill_mapping_config):
    """Verify language-specific toolchains are NOT mapped to generic agents.

    This test prevents the bug where:
    - toolchains/elixir/frameworks/phoenix-liveview → web-ui (INVALID)
    - toolchains/golang/data → data-engineer (INVALID)
    - toolchains/php/frameworks/wordpress/block-editor → web-ui (INVALID)

    Language-specific toolchains should ONLY be mapped to their language-specific
    engineers, not generic agents, UNLESS explicitly allowed in VALID_CROSS_MAPPINGS.

    Valid exceptions (in VALID_CROSS_MAPPINGS):
    - toolchains/javascript/frameworks/* → web-ui (React, Next.js, etc.)
    - toolchains/python/data → data-engineer (data pipelines)
    - toolchains/typescript/data → data-engineer (Drizzle, Prisma, etc.)
    """
    skill_mappings = skill_mapping_config["skill_mappings"]

    violations = []

    for skill_path, agent_list in skill_mappings.items():
        # Skip if not a language toolchain
        language = None
        for lang_prefix in LANGUAGE_TOOLCHAINS:
            if skill_path.startswith(lang_prefix):
                language = lang_prefix
                break

        if not language:
            continue  # Not a language toolchain

        # Get allowed agents for this language
        allowed_language_agents = set(LANGUAGE_TOOLCHAINS[language])

        # Check for valid cross-mappings
        allowed_generic_agents = set()
        for cross_mapping_prefix, allowed_generics in VALID_CROSS_MAPPINGS.items():
            if skill_path.startswith(cross_mapping_prefix):
                allowed_generic_agents.update(allowed_generics)

        # Combine allowed agents
        all_allowed_agents = allowed_language_agents | allowed_generic_agents

        # Check if any generic agents are in the mapping
        mapped_agents = set(agent_list) if isinstance(agent_list, list) else set()
        generic_agents_in_mapping = mapped_agents & GENERIC_AGENTS

        # Find invalid generic agents (not in allowed list)
        invalid_generic_agents = generic_agents_in_mapping - allowed_generic_agents

        if invalid_generic_agents:
            violations.append(
                {
                    "skill": skill_path,
                    "language": language,
                    "invalid_agents": list(invalid_generic_agents),
                    "allowed_agents": list(all_allowed_agents),
                }
            )

    # Report violations
    if violations:
        error_msg = "\n\nLanguage-specific toolchains mapped to generic agents:\n\n"
        for v in violations:
            error_msg += f"  ❌ {v['skill']}\n"
            error_msg += f"     Invalid: {', '.join(v['invalid_agents'])}\n"
            error_msg += f"     Allowed: {', '.join(v['allowed_agents'])}\n\n"

        error_msg += (
            "SOLUTION: Remove generic agents from language-specific toolchains.\n"
            "If this is a valid cross-mapping, add to VALID_CROSS_MAPPINGS in test.\n"
            "See: docs/bugfixes/orphan-skill-detection-fix-2025-12-30.md\n"
        )

        pytest.fail(error_msg)


def test_no_orphaned_elixir_skills_when_no_phoenix_engineer(skill_mapping_config):
    """Regression test: Elixir skills should only map to phoenix-engineer.

    Prevents the specific bug where:
    - toolchains/elixir/frameworks/phoenix-liveview → web-ui
    - toolchains/elixir/data/ecto-patterns → data-engineer

    This caused orphan detection to fail because web-ui/data-engineer were
    deployed but phoenix-engineer was not.
    """
    skill_mappings = skill_mapping_config["skill_mappings"]

    elixir_skills = {
        path: agents
        for path, agents in skill_mappings.items()
        if path.startswith("toolchains/elixir")
    }

    violations = []
    for skill_path, agent_list in elixir_skills.items():
        agents = set(agent_list) if isinstance(agent_list, list) else set()

        # Only phoenix-engineer should be mapped
        if agents != {"phoenix-engineer"}:
            violations.append(
                {
                    "skill": skill_path,
                    "agents": list(agents),
                    "expected": ["phoenix-engineer"],
                }
            )

    if violations:
        error_msg = "\n\nElixir skills mapped to non-phoenix agents:\n\n"
        for v in violations:
            error_msg += f"  ❌ {v['skill']}\n"
            error_msg += f"     Mapped to: {', '.join(v['agents'])}\n"
            error_msg += f"     Expected: {', '.join(v['expected'])}\n\n"

        pytest.fail(error_msg)


def test_no_orphaned_golang_skills_when_no_golang_engineer(skill_mapping_config):
    """Regression test: Golang skills should only map to golang-engineer.

    Prevents the bug where:
    - toolchains/golang/data → data-engineer
    """
    skill_mappings = skill_mapping_config["skill_mappings"]

    golang_skills = {
        path: agents
        for path, agents in skill_mappings.items()
        if path.startswith("toolchains/golang")
    }

    violations = []
    for skill_path, agent_list in golang_skills.items():
        agents = set(agent_list) if isinstance(agent_list, list) else set()

        # Only golang-engineer should be mapped
        if agents != {"golang-engineer"}:
            violations.append(
                {
                    "skill": skill_path,
                    "agents": list(agents),
                    "expected": ["golang-engineer"],
                }
            )

    if violations:
        error_msg = "\n\nGolang skills mapped to non-golang agents:\n\n"
        for v in violations:
            error_msg += f"  ❌ {v['skill']}\n"
            error_msg += f"     Mapped to: {', '.join(v['agents'])}\n"
            error_msg += f"     Expected: {', '.join(v['expected'])}\n\n"

        pytest.fail(error_msg)


def test_no_orphaned_php_wordpress_skills(skill_mapping_config):
    """Regression test: WordPress skills should only map to php-engineer.

    Prevents the bug where:
    - toolchains/php/frameworks/wordpress/block-editor → web-ui
    - toolchains/php/frameworks/wordpress/security-validation → security
    """
    skill_mappings = skill_mapping_config["skill_mappings"]

    wordpress_skills = {
        path: agents
        for path, agents in skill_mappings.items()
        if "wordpress" in path.lower()
    }

    violations = []
    for skill_path, agent_list in wordpress_skills.items():
        agents = set(agent_list) if isinstance(agent_list, list) else set()

        # Only php-engineer should be mapped
        if agents != {"php-engineer"}:
            violations.append(
                {
                    "skill": skill_path,
                    "agents": list(agents),
                    "expected": ["php-engineer"],
                }
            )

    if violations:
        error_msg = "\n\nWordPress skills mapped to non-php agents:\n\n"
        for v in violations:
            error_msg += f"  ❌ {v['skill']}\n"
            error_msg += f"     Mapped to: {', '.join(v['agents'])}\n"
            error_msg += f"     Expected: {', '.join(v['expected'])}\n\n"

        pytest.fail(error_msg)


def test_all_agents_list_consistency(skill_mapping_config):
    """Verify all_agents_list matches agents used in skill_mappings."""
    all_agents_list = set(skill_mapping_config["all_agents_list"])
    skill_mappings = skill_mapping_config["skill_mappings"]

    # Collect all agents referenced in mappings
    agents_in_mappings = set()
    for agent_list in skill_mappings.values():
        if isinstance(agent_list, list):
            # Skip ALL_AGENTS marker
            if agent_list == ["ALL_AGENTS"]:
                continue
            agents_in_mappings.update(agent_list)

    # Find agents in mappings but not in all_agents_list
    missing_from_list = agents_in_mappings - all_agents_list

    # Find agents in all_agents_list but never used in mappings
    # (This is OK - not all agents need skills, but log for awareness)
    unused_agents = all_agents_list - agents_in_mappings

    if missing_from_list:
        error_msg = (
            f"\n\nAgents used in skill_mappings but not in all_agents_list:\n"
            f"{', '.join(sorted(missing_from_list))}\n\n"
            f"Add these agents to the all_agents_list section.\n"
        )
        pytest.fail(error_msg)

    # Log unused agents (not a failure, just awareness)
    if unused_agents:
        print(
            f"\nINFO: Agents in all_agents_list but not used in mappings: "
            f"{', '.join(sorted(unused_agents))}"
        )


def test_skill_paths_use_forward_slashes(skill_mapping_config):
    """Verify all skill paths use forward slashes (not hyphens) in mappings.

    Skill paths in the configuration should use slashes (toolchains/python/frameworks/django)
    while deployment names use hyphens (toolchains-python-frameworks-django).

    This ensures the SkillToAgentMapper can correctly match skill paths.
    """
    skill_mappings = skill_mapping_config["skill_mappings"]

    violations = []
    for skill_path in skill_mappings:
        # Skip universal/* paths (they can use hyphens in names)
        if skill_path.startswith("universal/") or skill_path.startswith("examples/"):
            continue

        # Toolchain paths should have at least 2 slashes
        # e.g., "toolchains/python/frameworks"
        if skill_path.startswith("toolchains/"):
            slash_count = skill_path.count("/")
            if slash_count < 2:
                violations.append(
                    {
                        "skill": skill_path,
                        "issue": f"Too few path segments (found {slash_count + 1}, expected 3+)",
                    }
                )

    if violations:
        error_msg = "\n\nInvalid skill path formats:\n\n"
        for v in violations:
            error_msg += f"  ❌ {v['skill']}\n"
            error_msg += f"     {v['issue']}\n\n"

        pytest.fail(error_msg)
