#!/usr/bin/env python3
"""
Test script to verify framework loader functionality after caching optimizations.

This script verifies that all functionality still works correctly with the
performance optimizations in place.
"""

import logging
import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.framework_loader import FrameworkLoader
from claude_mpm.services.core.service_container import ServiceContainer

# Agent definitions written into the isolated project by
# ``isolated_agents_project``. Names are prefixed so they can never collide
# with a real deployed agent if the isolation ever leaks, and are already
# lowercase kebab-case so the file stem and the normalized agent id
# (``get_deployed_agent_ids``) are the same string.
FIXTURE_AGENTS = {
    "fixture-engineer": "Implements features and fixes bugs.",
    "fixture-qa": "Validates behavior and writes tests.",
}


@pytest.fixture()
def isolated_agents_project(tmp_path, monkeypatch):
    """Point deployed-agent discovery at a tmp project with known agent files.

    Why: #958 -- ``AgentLoader.get_deployed_agents`` globs
    ``Path.cwd()/.claude/agents`` and ``Path.home()/.claude/agents``, so
    ``test_agent_capabilities_loading`` asserted against whatever those
    directories happened to hold. Under ``pytest -n auto`` the repo's
    ``.claude/agents`` is not deterministically populated before the test
    runs, so the assertion passed only when some other test's write landed
    first.

    What: Builds ``{tmp}/isolated_project`` with a ``.claude-mpm`` marker (so
    ``PathResolver.find_project_root`` stops there), writes one ``.md`` file
    per entry in ``FIXTURE_AGENTS`` into its ``.claude/agents``, then chdirs
    into it, sets ``CLAUDE_MPM_USER_PWD``, and redirects ``Path.home()`` to an
    empty fake home. Both discovery roots are then fully owned by the test.

    Test: ``test_agent_capabilities_loading``.
    """
    project = tmp_path / "isolated_project"
    agents_dir = project / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    (project / ".claude-mpm").mkdir()

    for name, description in FIXTURE_AGENTS.items():
        (agents_dir / f"{name}.md").write_text(
            f"---\nname: {name}\ndescription: {description}\nmodel: sonnet\n---\n\n"
            f"# {name}\n\n{description}\n"
        )

    fake_home = tmp_path / "home"
    (fake_home / ".claude" / "agents").mkdir(parents=True)
    monkeypatch.setattr(Path, "home", classmethod(lambda _cls: fake_home))

    monkeypatch.chdir(project)
    monkeypatch.setenv("CLAUDE_MPM_USER_PWD", str(project))

    return project


def _make_loader() -> FrameworkLoader:
    """Build a FrameworkLoader with its own isolated ServiceContainer.

    WHAT: Constructs FrameworkLoader(service_container=ServiceContainer())
    instead of the bare FrameworkLoader() default (get_global_container()).

    WHY: FrameworkLoader._register_services only binds ICacheManager the
    FIRST time it's requested from a given container, and the default
    container is a process-wide singleton that outlives any single test
    file under ``pytest -n auto``. If another test file in the same xdist
    worker builds a FrameworkLoader() against an isolated/empty project
    directory before this module's tests run, that empty deployed-agents
    result gets cached in the shared CacheManager (30s TTL) and is
    silently inherited here, producing "Found 0 deployed agents instead
    of >0" even though this repo's real .claude/agents directory is
    non-empty. A fresh ServiceContainer() per loader sidesteps the shared
    cache entirely. Same pattern as
    tests/test_agent_manifest_filtering.py::_make_loader().
    """
    return FrameworkLoader(service_container=ServiceContainer())


def setup_logging():
    """Setup logging to see detailed information."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%H:%M:%S",
    )


def test_agent_capabilities_loading(isolated_agents_project):
    """Test that agent capabilities are loaded correctly.

    Runs against ``isolated_agents_project`` rather than the repo's real
    ``.claude/agents``, so the deployed-agent set is exactly ``FIXTURE_AGENTS``
    no matter which xdist worker picks the test up or what ran before it
    (#958).
    """
    print("\n" + "=" * 60)
    print("Testing Agent Capabilities Loading")
    print("=" * 60)

    loader = _make_loader()

    # Test deployed agents discovery
    deployed_agents = loader._get_deployed_agents()
    print(f"✓ Found {len(deployed_agents)} deployed agents")
    print(f"  Deployed agents: {', '.join(sorted(deployed_agents))}")

    assert deployed_agents == set(FIXTURE_AGENTS), (
        f"Expected exactly the fixture agents, got {sorted(deployed_agents)}"
    )

    # Test agent capabilities generation
    capabilities = loader._generate_agent_capabilities_section()
    print(f"✓ Generated agent capabilities section ({len(capabilities)} chars)")

    # Verify capabilities contain expected elements
    assert "Available Agent Capabilities" in capabilities
    for name in FIXTURE_AGENTS:
        assert name in capabilities, f"Capabilities section missing agent: {name}"

    # Test specific agent parsing
    agent_dirs = [Path.cwd() / ".claude" / "agents", Path.home() / ".claude" / "agents"]

    parsed_agents = []
    for agents_dir in agent_dirs:
        if agents_dir.exists():
            for agent_file in agents_dir.glob("*.md"):
                if not agent_file.name.startswith("."):
                    metadata = loader._parse_agent_metadata(agent_file)
                    if metadata:
                        parsed_agents.append(metadata)

    print(f"✓ Successfully parsed {len(parsed_agents)} agent metadata files")

    assert len(parsed_agents) == len(FIXTURE_AGENTS)

    # Verify metadata structure
    required_fields = ["id", "display_name", "description"]
    for sample_agent in parsed_agents:
        for field in required_fields:
            assert field in sample_agent, (
                f"Agent metadata missing required field: {field}"
            )
    print(f"✓ Agent metadata contains required fields: {required_fields}")

    return True


def test_memory_loading():
    """Test that memories are loaded correctly."""
    print("\n" + "=" * 60)
    print("Testing Memory Loading")
    print("=" * 60)

    loader = _make_loader()
    content = {}

    # Test memory loading
    loader._load_actual_memories(content)

    if "actual_memories" in content:
        memory_size = len(content["actual_memories"])
        print(f"✓ Loaded PM memories ({memory_size} bytes)")
        print(f"  Memory preview: {content['actual_memories'][:100]}...")
    else:
        print("! No PM memories found")

    # NEW ARCHITECTURE: Agent memories should NOT be in framework content
    # They are loaded at deployment time and appended to agent files
    if "agent_memories" in content and len(content["agent_memories"]) > 0:
        agent_count = len(content["agent_memories"])
        print(f"⚠ Found agent memories in framework content: {agent_count} agents")
        print("  NOTE: Agent memories should now be in agent files, not framework")
        for agent_name in content["agent_memories"]:
            memory_size = len(content["agent_memories"][agent_name])
            print(f"  - {agent_name}: {memory_size} bytes")
    else:
        print("✓ No agent memories in framework (correct - now loaded at deployment)")

    return True


def test_framework_content_loading():
    """Test that framework content loads correctly."""
    print("\n" + "=" * 60)
    print("Testing Framework Content Loading")
    print("=" * 60)

    loader = _make_loader()
    content = loader.framework_content

    # Check essential content is loaded
    essential_fields = [
        "loaded",
        "framework_instructions",
        "workflow_instructions",
        "memory_instructions",
        "agents",
    ]

    for field in essential_fields:
        if content.get(field):
            print(f"✓ {field}: loaded")
        else:
            print(f"⚠ {field}: not loaded or empty")

    print(f"✓ Framework loaded status: {content.get('loaded', False)}")
    print(f"✓ Framework version: {content.get('version', 'unknown')}")
    print(f"✓ Agent count: {len(content.get('agents', {}))}")

    return True


def test_full_instruction_generation():
    """Test that full framework instructions can be generated."""
    print("\n" + "=" * 60)
    print("Testing Full Framework Instructions")
    print("=" * 60)

    loader = _make_loader()

    # Generate full instructions
    instructions = loader.get_framework_instructions()

    print(f"✓ Generated framework instructions ({len(instructions)} chars)")

    # Check that essential sections are present
    expected_sections = [
        "Claude MPM Framework",
        "Available Agent Capabilities",
        "Temporal Context",
    ]

    for section in expected_sections:
        if section in instructions:
            print(f"✓ Contains section: {section}")
        else:
            print(f"⚠ Missing section: {section}")

    # Verify instructions contain agent information
    deployed_agents = loader._get_deployed_agents()
    if deployed_agents:
        # Check that some agent names appear in instructions
        agents_mentioned = sum(1 for agent in deployed_agents if agent in instructions)
        print(
            f"✓ Instructions mention {agents_mentioned}/{len(deployed_agents)} deployed agents"
        )

    return True


def test_yaml_metadata_parsing():
    """Test YAML metadata parsing works correctly."""
    print("\n" + "=" * 60)
    print("Testing YAML Metadata Parsing")
    print("=" * 60)

    loader = _make_loader()

    # Find an agent file with YAML frontmatter
    agent_dirs = [Path.cwd() / ".claude" / "agents", Path.home() / ".claude" / "agents"]

    yaml_found = False
    for agents_dir in agent_dirs:
        if agents_dir.exists():
            for agent_file in agents_dir.glob("*.md"):
                if not agent_file.name.startswith("."):
                    try:
                        with agent_file.open() as f:
                            content = f.read()
                        if content.startswith("---"):
                            metadata = loader._parse_agent_metadata(agent_file)
                            if metadata:
                                print(
                                    f"✓ Successfully parsed YAML metadata from {agent_file.name}"
                                )
                                print(f"  Agent ID: {metadata.get('id')}")
                                print(f"  Display name: {metadata.get('display_name')}")
                                print(
                                    f"  Description: {metadata.get('description', '')[:50]}..."
                                )
                                yaml_found = True
                                break
                    except Exception as e:
                        print(f"⚠ Failed to parse {agent_file.name}: {e}")
        if yaml_found:
            break

    if not yaml_found:
        print("! No YAML frontmatter found in agent files")

    return True


def main():
    """Run this module's tests through pytest.

    Delegates to pytest instead of calling the test functions in a hand-rolled
    loop: ``test_agent_capabilities_loading`` now takes the
    ``isolated_agents_project`` fixture, which only pytest can supply (#958).
    """
    setup_logging()
    return pytest.main([__file__, "-v"])


if __name__ == "__main__":
    sys.exit(main())
