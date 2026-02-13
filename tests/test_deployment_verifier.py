"""Tests for DeploymentVerifier - post-deployment filesystem verification.

Tests cover:
- Agent deployed: file exists, valid YAML frontmatter, required fields, size
- Agent undeployed: file removed
- Skill deployed: directory exists, contains files
- Skill undeployed: directory removed
- Mode switch: config file reflects expected mode
- Timestamps on verification results
"""

import pytest

from claude_mpm.services.config_api.deployment_verifier import (
    DeploymentVerifier,
    VerificationCheck,
    VerificationResult,
)

VALID_AGENT_CONTENT = """---
name: test-agent
description: A test agent for verification
version: 1.0
---

# Test Agent

This is the agent body.
"""

MISSING_FRONTMATTER_CONTENT = """# No frontmatter delimiters here

Just plain markdown without --- delimiters.
"""

MISSING_FIELDS_CONTENT = """---
version: 1.0
---

Agent without name or description.
"""


@pytest.fixture
def agents_dir(tmp_path):
    """Create a temporary agents directory."""
    d = tmp_path / "agents"
    d.mkdir()
    return d


@pytest.fixture
def skills_dir(tmp_path):
    """Create a temporary skills directory."""
    d = tmp_path / "skills"
    d.mkdir()
    return d


@pytest.fixture
def verifier(agents_dir, skills_dir):
    """Create DeploymentVerifier with tmp dirs."""
    return DeploymentVerifier(agents_dir=agents_dir, skills_dir=skills_dir)


class TestVerifyAgentDeployed:
    def test_verify_agent_deployed_success(self, verifier, agents_dir):
        """Agent with valid frontmatter passes all checks."""
        (agents_dir / "test-agent.md").write_text(VALID_AGENT_CONTENT)

        result = verifier.verify_agent_deployed("test-agent")

        assert isinstance(result, VerificationResult)
        assert result.passed is True
        check_names = [c.check for c in result.checks]
        assert "file_exists" in check_names
        assert "file_size" in check_names
        assert "yaml_frontmatter" in check_names
        assert "required_fields" in check_names
        assert all(c.passed for c in result.checks)

    def test_verify_agent_deployed_missing_file(self, verifier, agents_dir):
        """Missing agent file fails file_exists check."""
        result = verifier.verify_agent_deployed("nonexistent-agent")

        assert result.passed is False
        file_check = next(c for c in result.checks if c.check == "file_exists")
        assert file_check.passed is False
        assert "not found" in file_check.details.lower()

    def test_verify_agent_deployed_missing_frontmatter(self, verifier, agents_dir):
        """Agent without YAML frontmatter delimiters fails yaml_frontmatter check."""
        (agents_dir / "broken.md").write_text(MISSING_FRONTMATTER_CONTENT)

        result = verifier.verify_agent_deployed("broken")

        assert result.passed is False
        fm_check = next(c for c in result.checks if c.check == "yaml_frontmatter")
        assert fm_check.passed is False

    def test_verify_agent_deployed_missing_required_fields(self, verifier, agents_dir):
        """Agent missing name/description fails required_fields check."""
        (agents_dir / "nofields.md").write_text(MISSING_FIELDS_CONTENT)

        result = verifier.verify_agent_deployed("nofields")

        assert result.passed is False
        fields_check = next(c for c in result.checks if c.check == "required_fields")
        assert fields_check.passed is False
        assert "name" in fields_check.details.lower()
        assert "description" in fields_check.details.lower()

    def test_verify_agent_deployed_empty_file(self, verifier, agents_dir):
        """Empty file fails size check."""
        (agents_dir / "empty.md").write_text("")

        result = verifier.verify_agent_deployed("empty")

        assert result.passed is False
        size_check = next(c for c in result.checks if c.check == "file_size")
        assert size_check.passed is False
        assert "empty" in size_check.details.lower()


class TestVerifyAgentUndeployed:
    def test_verify_agent_undeployed_success(self, verifier, agents_dir):
        """After deletion, verify_agent_undeployed passes."""
        # File doesn't exist -> should pass
        result = verifier.verify_agent_undeployed("deleted-agent")

        assert result.passed is True
        check = result.checks[0]
        assert check.check == "file_removed"
        assert check.passed is True

    def test_verify_agent_undeployed_file_still_exists(self, verifier, agents_dir):
        """If file still exists after undeploy, verification fails."""
        (agents_dir / "still-here.md").write_text("content")

        result = verifier.verify_agent_undeployed("still-here")

        assert result.passed is False
        check = result.checks[0]
        assert check.check == "file_removed"
        assert check.passed is False
        assert "still exists" in check.details.lower()


class TestVerifySkillDeployed:
    def test_verify_skill_deployed_success(self, verifier, skills_dir):
        """Skill directory with files passes verification."""
        skill_dir = skills_dir / "tdd"
        skill_dir.mkdir()
        (skill_dir / "skill.md").write_text("TDD content")

        result = verifier.verify_skill_deployed("tdd")

        assert result.passed is True
        check_names = [c.check for c in result.checks]
        assert "directory_exists" in check_names
        assert "has_files" in check_names
        assert all(c.passed for c in result.checks)

    def test_verify_skill_deployed_empty_directory(self, verifier, skills_dir):
        """Empty skill directory fails has_files check."""
        (skills_dir / "empty-skill").mkdir()

        result = verifier.verify_skill_deployed("empty-skill")

        assert result.passed is False
        files_check = next(c for c in result.checks if c.check == "has_files")
        assert files_check.passed is False
        assert "empty" in files_check.details.lower()

    def test_verify_skill_deployed_missing_directory(self, verifier, skills_dir):
        """Missing directory fails directory_exists check."""
        result = verifier.verify_skill_deployed("nonexistent-skill")

        assert result.passed is False
        dir_check = next(c for c in result.checks if c.check == "directory_exists")
        assert dir_check.passed is False
        assert "not found" in dir_check.details.lower()


class TestVerifySkillUndeployed:
    def test_verify_skill_undeployed_success(self, verifier, skills_dir):
        """After deletion, verify_skill_undeployed passes."""
        result = verifier.verify_skill_undeployed("removed-skill")

        assert result.passed is True
        check = result.checks[0]
        assert check.check == "directory_removed"
        assert check.passed is True

    def test_verify_skill_undeployed_dir_still_exists(self, verifier, skills_dir):
        """If directory still exists after undeploy, verification fails."""
        (skills_dir / "still-here").mkdir()

        result = verifier.verify_skill_undeployed("still-here")

        assert result.passed is False


class TestVerifyModeSwitch:
    def test_verify_mode_switch(self, tmp_path):
        """Verify config file reflects expected mode after switch."""
        import yaml

        config_path = tmp_path / "configuration.yaml"
        config_path.write_text(yaml.dump({"mode": "selective"}))

        verifier = DeploymentVerifier()
        result = verifier.verify_mode_switch("selective", config_path=config_path)

        assert result.passed is True
        check_names = [c.check for c in result.checks]
        assert "config_parseable" in check_names
        assert "mode_matches" in check_names

    def test_verify_mode_switch_wrong_mode(self, tmp_path):
        """Verification fails when config has wrong mode."""
        import yaml

        config_path = tmp_path / "configuration.yaml"
        config_path.write_text(yaml.dump({"mode": "full"}))

        verifier = DeploymentVerifier()
        result = verifier.verify_mode_switch("selective", config_path=config_path)

        assert result.passed is False
        mode_check = next(c for c in result.checks if c.check == "mode_matches")
        assert mode_check.passed is False
        assert "selective" in mode_check.details
        assert "full" in mode_check.details

    def test_verify_mode_switch_missing_config(self, tmp_path):
        """Verification fails when config file doesn't exist."""
        config_path = tmp_path / "nonexistent.yaml"

        verifier = DeploymentVerifier()
        result = verifier.verify_mode_switch("selective", config_path=config_path)

        assert result.passed is False


class TestVerificationTimestamp:
    def test_verification_result_has_timestamp(self, verifier, agents_dir):
        """All verification results include ISO timestamp."""
        (agents_dir / "ts-agent.md").write_text(VALID_AGENT_CONTENT)

        result = verifier.verify_agent_deployed("ts-agent")
        assert result.timestamp  # Non-empty
        # ISO format check (contains T and timezone info)
        assert "T" in result.timestamp

    def test_failed_result_has_timestamp(self, verifier):
        """Failed verification also includes timestamp."""
        result = verifier.verify_agent_deployed("missing")
        assert result.timestamp
        assert "T" in result.timestamp
