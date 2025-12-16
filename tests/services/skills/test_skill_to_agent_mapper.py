"""Tests for SkillToAgentMapper service.

WHY: Comprehensive testing of skill-to-agent mapping functionality to ensure
reliable YAML parsing, bidirectional lookup, ALL_AGENTS expansion, and
pattern-based inference.

COVERAGE:
- YAML configuration loading and validation
- Forward mapping: skill -> agents
- Inverse mapping: agent -> skills
- ALL_AGENTS marker expansion
- Pattern-based inference (language, framework, domain)
- Error handling and edge cases
- Statistics and introspection
"""

import tempfile
from pathlib import Path
from textwrap import dedent

import pytest
import yaml

from claude_mpm.services.skills.skill_to_agent_mapper import SkillToAgentMapper


@pytest.fixture
def mock_config_minimal():
    """Minimal valid configuration."""
    return {
        "skill_mappings": {
            "toolchains/python/frameworks/django": ["python-engineer", "data-engineer", "engineer"],
            "toolchains/typescript/core": ["typescript-engineer", "javascript-engineer", "engineer"],
        },
        "all_agents_list": ["engineer", "python-engineer", "typescript-engineer", "javascript-engineer"],
    }


@pytest.fixture
def mock_config_with_all_agents():
    """Configuration with ALL_AGENTS marker."""
    return {
        "skill_mappings": {
            "toolchains/python/frameworks/django": ["python-engineer", "data-engineer", "engineer"],
            "universal/debugging/systematic-debugging": ["ALL_AGENTS"],
        },
        "all_agents_list": [
            "engineer",
            "python-engineer",
            "typescript-engineer",
            "qa",
            "ops",
        ],
    }


@pytest.fixture
def mock_config_with_inference():
    """Configuration with inference rules."""
    return {
        "skill_mappings": {
            "toolchains/python/frameworks/django": ["python-engineer", "data-engineer", "engineer"],
        },
        "all_agents_list": ["engineer", "python-engineer", "typescript-engineer", "data-engineer"],
        "inference_rules": {
            "language_patterns": {
                "python": ["python-engineer", "data-engineer", "engineer"],
                "typescript": ["typescript-engineer", "javascript-engineer", "engineer"],
            },
            "framework_patterns": {
                "nextjs": ["nextjs-engineer", "react-engineer", "typescript-engineer"],
                "django": ["python-engineer", "engineer"],
            },
            "domain_patterns": {
                "testing": ["qa", "engineer"],
                "security": ["security", "ops", "engineer"],
            },
        },
    }


@pytest.fixture
def temp_config_file(tmp_path, mock_config_minimal):
    """Create temporary YAML config file."""
    config_file = tmp_path / "skill_to_agent_mapping.yaml"
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(mock_config_minimal, f)
    return config_file


@pytest.fixture
def temp_config_with_all_agents(tmp_path, mock_config_with_all_agents):
    """Create temporary YAML config file with ALL_AGENTS."""
    config_file = tmp_path / "skill_to_agent_mapping_all.yaml"
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(mock_config_with_all_agents, f)
    return config_file


@pytest.fixture
def temp_config_with_inference(tmp_path, mock_config_with_inference):
    """Create temporary YAML config file with inference rules."""
    config_file = tmp_path / "skill_to_agent_mapping_inference.yaml"
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(mock_config_with_inference, f)
    return config_file


# Initialization Tests


def test_init_with_default_config():
    """Test initialization with default config path."""
    mapper = SkillToAgentMapper()
    assert mapper is not None
    # Default config should exist in package
    assert mapper.config_path.exists()
    assert len(mapper._skill_to_agents) > 0
    assert len(mapper._agent_to_skills) > 0


def test_init_with_custom_config(temp_config_file):
    """Test initialization with custom config path."""
    mapper = SkillToAgentMapper(config_path=temp_config_file)
    assert mapper.config_path == temp_config_file
    assert len(mapper._skill_to_agents) == 2


def test_init_missing_config_file(tmp_path):
    """Test initialization with missing config file."""
    nonexistent_file = tmp_path / "missing.yaml"
    with pytest.raises(FileNotFoundError, match="Configuration file not found"):
        SkillToAgentMapper(config_path=nonexistent_file)


def test_init_invalid_yaml(tmp_path):
    """Test initialization with invalid YAML."""
    config_file = tmp_path / "invalid.yaml"
    config_file.write_text("{ invalid yaml: [ unclosed")

    with pytest.raises(yaml.YAMLError, match="Invalid YAML"):
        SkillToAgentMapper(config_path=config_file)


def test_init_missing_skill_mappings(tmp_path):
    """Test initialization with missing skill_mappings section."""
    config_file = tmp_path / "missing_mappings.yaml"
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump({"all_agents_list": ["engineer"]}, f)

    with pytest.raises(ValueError, match="missing required section: skill_mappings"):
        SkillToAgentMapper(config_path=config_file)


def test_init_missing_all_agents_list(tmp_path):
    """Test initialization with missing all_agents_list section."""
    config_file = tmp_path / "missing_all_agents.yaml"
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump({"skill_mappings": {"test/skill": ["engineer"]}}, f)

    with pytest.raises(ValueError, match="missing required section: all_agents_list"):
        SkillToAgentMapper(config_path=config_file)


# Forward Mapping Tests (skill -> agents)


def test_get_agents_for_skill_exact_match(temp_config_file):
    """Test getting agents for skill with exact match."""
    mapper = SkillToAgentMapper(config_path=temp_config_file)
    agents = mapper.get_agents_for_skill("toolchains/python/frameworks/django")
    assert set(agents) == {"python-engineer", "data-engineer", "engineer"}


def test_get_agents_for_skill_not_found(temp_config_file):
    """Test getting agents for unmapped skill (no inference)."""
    mapper = SkillToAgentMapper(config_path=temp_config_file)
    agents = mapper.get_agents_for_skill("toolchains/rust/frameworks/actix")
    assert agents == []


def test_get_agents_for_skill_returns_copy(temp_config_file):
    """Test that returned list is a copy (not reference)."""
    mapper = SkillToAgentMapper(config_path=temp_config_file)
    agents1 = mapper.get_agents_for_skill("toolchains/python/frameworks/django")
    agents2 = mapper.get_agents_for_skill("toolchains/python/frameworks/django")

    # Modify one list
    agents1.append("new-agent")

    # Other list should be unchanged
    assert "new-agent" not in agents2
    assert len(agents1) == len(agents2) + 1


# Inverse Mapping Tests (agent -> skills)


def test_get_skills_for_agent_exact_match(temp_config_file):
    """Test getting skills for agent."""
    mapper = SkillToAgentMapper(config_path=temp_config_file)
    skills = mapper.get_skills_for_agent("python-engineer")
    assert "toolchains/python/frameworks/django" in skills


def test_get_skills_for_agent_multiple_skills(temp_config_file):
    """Test getting multiple skills for engineer agent."""
    mapper = SkillToAgentMapper(config_path=temp_config_file)
    skills = mapper.get_skills_for_agent("engineer")
    # Engineer should have both mapped skills
    assert len(skills) == 2
    assert "toolchains/python/frameworks/django" in skills
    assert "toolchains/typescript/core" in skills


def test_get_skills_for_agent_not_found(temp_config_file):
    """Test getting skills for unmapped agent."""
    mapper = SkillToAgentMapper(config_path=temp_config_file)
    skills = mapper.get_skills_for_agent("rust-engineer")
    assert skills == []


def test_get_skills_for_agent_returns_copy(temp_config_file):
    """Test that returned list is a copy."""
    mapper = SkillToAgentMapper(config_path=temp_config_file)
    skills1 = mapper.get_skills_for_agent("engineer")
    skills2 = mapper.get_skills_for_agent("engineer")

    # Modify one list
    skills1.append("new/skill")

    # Other list should be unchanged
    assert "new/skill" not in skills2


# ALL_AGENTS Expansion Tests


def test_all_agents_expansion(temp_config_with_all_agents):
    """Test ALL_AGENTS marker expansion."""
    mapper = SkillToAgentMapper(config_path=temp_config_with_all_agents)
    agents = mapper.get_agents_for_skill("universal/debugging/systematic-debugging")

    # Should expand to all agents in all_agents_list
    assert len(agents) == 5
    assert set(agents) == {"engineer", "python-engineer", "typescript-engineer", "qa", "ops"}


def test_all_agents_in_inverse_index(temp_config_with_all_agents):
    """Test ALL_AGENTS expansion in inverse index."""
    mapper = SkillToAgentMapper(config_path=temp_config_with_all_agents)

    # All agents should have the universal skill
    for agent_id in ["engineer", "python-engineer", "typescript-engineer", "qa", "ops"]:
        skills = mapper.get_skills_for_agent(agent_id)
        assert "universal/debugging/systematic-debugging" in skills


# Pattern-based Inference Tests


def test_infer_agents_from_language_pattern(temp_config_with_inference):
    """Test inference from language pattern."""
    mapper = SkillToAgentMapper(config_path=temp_config_with_inference)
    agents = mapper.infer_agents_from_pattern("toolchains/python/new-framework")

    # Should match 'python' language pattern
    assert "python-engineer" in agents
    assert "data-engineer" in agents
    assert "engineer" in agents


def test_infer_agents_from_framework_pattern(temp_config_with_inference):
    """Test inference from framework pattern."""
    mapper = SkillToAgentMapper(config_path=temp_config_with_inference)
    agents = mapper.infer_agents_from_pattern("toolchains/typescript/frameworks/nextjs-advanced")

    # Should match 'nextjs' framework pattern
    assert "nextjs-engineer" in agents
    assert "react-engineer" in agents
    assert "typescript-engineer" in agents


def test_infer_agents_from_domain_pattern(temp_config_with_inference):
    """Test inference from domain pattern."""
    mapper = SkillToAgentMapper(config_path=temp_config_with_inference)
    agents = mapper.infer_agents_from_pattern("universal/testing/new-testing-skill")

    # Should match 'testing' domain pattern
    assert "qa" in agents
    assert "engineer" in agents


def test_infer_agents_multiple_patterns(temp_config_with_inference):
    """Test inference combining multiple patterns."""
    mapper = SkillToAgentMapper(config_path=temp_config_with_inference)
    agents = mapper.infer_agents_from_pattern("toolchains/python/testing/pytest-advanced")

    # Should match both 'python' language and 'testing' domain patterns
    assert "python-engineer" in agents
    assert "data-engineer" in agents
    assert "qa" in agents
    assert "engineer" in agents


def test_infer_agents_no_match(temp_config_with_inference):
    """Test inference with no pattern match."""
    mapper = SkillToAgentMapper(config_path=temp_config_with_inference)
    agents = mapper.infer_agents_from_pattern("unknown/path/to/skill")
    assert agents == []


def test_get_agents_for_skill_with_inference_fallback(temp_config_with_inference):
    """Test get_agents_for_skill falling back to inference."""
    mapper = SkillToAgentMapper(config_path=temp_config_with_inference)

    # Unmapped skill should use inference
    agents = mapper.get_agents_for_skill("toolchains/typescript/new-framework")

    # Should match 'typescript' language pattern
    assert "typescript-engineer" in agents
    assert "javascript-engineer" in agents
    assert "engineer" in agents


# Introspection and Statistics Tests


def test_get_all_mapped_skills(temp_config_file):
    """Test getting all mapped skill paths."""
    mapper = SkillToAgentMapper(config_path=temp_config_file)
    skills = mapper.get_all_mapped_skills()

    assert len(skills) == 2
    assert "toolchains/python/frameworks/django" in skills
    assert "toolchains/typescript/core" in skills
    # Should be sorted
    assert skills == sorted(skills)


def test_get_all_agents(temp_config_file):
    """Test getting all agent IDs."""
    mapper = SkillToAgentMapper(config_path=temp_config_file)
    agents = mapper.get_all_agents()

    # All agents mentioned in mappings
    assert "python-engineer" in agents
    assert "typescript-engineer" in agents
    assert "engineer" in agents
    # Should be sorted
    assert agents == sorted(agents)


def test_is_skill_mapped_true(temp_config_file):
    """Test checking if skill is mapped (true case)."""
    mapper = SkillToAgentMapper(config_path=temp_config_file)
    assert mapper.is_skill_mapped("toolchains/python/frameworks/django") is True


def test_is_skill_mapped_false(temp_config_file):
    """Test checking if skill is mapped (false case)."""
    mapper = SkillToAgentMapper(config_path=temp_config_file)
    assert mapper.is_skill_mapped("toolchains/rust/unknown") is False


def test_get_mapping_stats(temp_config_file):
    """Test getting mapping statistics."""
    mapper = SkillToAgentMapper(config_path=temp_config_file)
    stats = mapper.get_mapping_stats()

    assert stats["total_skills"] == 2
    # python-engineer, data-engineer, typescript-engineer, javascript-engineer, engineer = 5 agents
    assert stats["total_agents"] == 5
    assert "avg_agents_per_skill" in stats
    assert "avg_skills_per_agent" in stats
    assert stats["config_path"] == str(temp_config_file)


def test_repr(temp_config_file):
    """Test string representation."""
    mapper = SkillToAgentMapper(config_path=temp_config_file)
    repr_str = repr(mapper)

    assert "SkillToAgentMapper" in repr_str
    assert "skills=2" in repr_str
    assert "agents=" in repr_str


# Edge Cases and Error Handling


def test_empty_skill_path(temp_config_file):
    """Test empty skill path."""
    mapper = SkillToAgentMapper(config_path=temp_config_file)
    agents = mapper.get_agents_for_skill("")
    assert agents == []


def test_empty_agent_id(temp_config_file):
    """Test empty agent ID."""
    mapper = SkillToAgentMapper(config_path=temp_config_file)
    skills = mapper.get_skills_for_agent("")
    assert skills == []


def test_config_with_invalid_agent_list_type(tmp_path):
    """Test configuration with non-list agent value."""
    config_file = tmp_path / "invalid_agents.yaml"
    config = {
        "skill_mappings": {
            "test/skill": "not-a-list",  # Invalid: should be list
        },
        "all_agents_list": ["engineer"],
    }
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(config, f)

    mapper = SkillToAgentMapper(config_path=config_file)

    # Should skip invalid mapping
    agents = mapper.get_agents_for_skill("test/skill")
    assert agents == []


def test_case_sensitivity_in_inference(temp_config_with_inference):
    """Test that inference is case-insensitive."""
    mapper = SkillToAgentMapper(config_path=temp_config_with_inference)

    # Different case variations should all match
    agents_lower = mapper.infer_agents_from_pattern("toolchains/python/test")
    agents_upper = mapper.infer_agents_from_pattern("TOOLCHAINS/PYTHON/TEST")
    agents_mixed = mapper.infer_agents_from_pattern("Toolchains/Python/Test")

    assert set(agents_lower) == set(agents_upper) == set(agents_mixed)


# Integration Test with Real Default Config


def test_default_config_loads_successfully():
    """Test that default config loads without errors."""
    mapper = SkillToAgentMapper()

    # Should have substantial mappings (based on 829-line config file)
    assert len(mapper._skill_to_agents) > 50
    assert len(mapper._agent_to_skills) > 10

    # Test a known mapping from default config
    agents = mapper.get_agents_for_skill("toolchains/python/frameworks/django")
    assert "python-engineer" in agents
    assert "engineer" in agents


def test_default_config_all_agents_expansion():
    """Test ALL_AGENTS expansion in default config."""
    mapper = SkillToAgentMapper()

    # universal/collaboration/git-workflow should have ALL_AGENTS
    agents = mapper.get_agents_for_skill("universal/collaboration/git-workflow")
    assert len(agents) > 20  # Should expand to many agents


def test_default_config_inference_rules():
    """Test inference rules in default config."""
    mapper = SkillToAgentMapper()

    # Test unmapped skill with language pattern
    agents = mapper.get_agents_for_skill("toolchains/python/new-library")
    assert "python-engineer" in agents

    # Test unmapped skill with domain pattern
    agents = mapper.get_agents_for_skill("universal/testing/new-test-skill")
    assert "qa" in agents
