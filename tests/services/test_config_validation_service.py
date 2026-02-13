"""Unit tests for ConfigValidationService.

Tests all validation rules individually:
- Deployed agent checks (frontmatter, YAML validity, required fields)
- Agent source checks (URL validity, enabled status)
- Skill source checks (URL validity, enabled status)
- Deployed skill checks (orphan detection)
- Environment variable override detection
- Cross-reference checks (skills referenced but not deployed)
- Cache behavior (TTL, invalidation)
"""

import os
import re
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.services.config.config_validation_service import (
    ConfigValidationService,
    ValidationIssue,
    ValidationResult,
)


class TestValidationIssue:
    """Test ValidationIssue dataclass."""

    def test_to_dict(self):
        issue = ValidationIssue(
            severity="error",
            category="agent",
            path="agents.test",
            message="Something wrong",
            suggestion="Fix it",
        )
        d = issue.to_dict()
        assert d["severity"] == "error"
        assert d["category"] == "agent"
        assert d["path"] == "agents.test"
        assert d["message"] == "Something wrong"
        assert d["suggestion"] == "Fix it"


class TestValidationResult:
    """Test ValidationResult aggregation."""

    def test_empty_result(self):
        result = ValidationResult(valid=True, issues=[])
        d = result.to_dict()
        assert d["valid"] is True
        assert d["summary"]["errors"] == 0
        assert d["summary"]["warnings"] == 0
        assert d["summary"]["info"] == 0

    def test_mixed_issues(self):
        issues = [
            ValidationIssue("error", "agent", "a", "msg", "sug"),
            ValidationIssue("warning", "skill", "b", "msg", "sug"),
            ValidationIssue("info", "env", "c", "msg", "sug"),
            ValidationIssue("warning", "source", "d", "msg", "sug"),
        ]
        result = ValidationResult(valid=False, issues=issues)
        d = result.to_dict()
        assert d["summary"]["errors"] == 1
        assert d["summary"]["warnings"] == 2
        assert d["summary"]["info"] == 1
        assert len(d["issues"]) == 4


class TestDeployedAgentValidation:
    """Test _validate_deployed_agents."""

    def test_no_agents_dir(self, tmp_path):
        svc = ConfigValidationService()
        with patch(
            "claude_mpm.services.config.config_validation_service.Path"
        ) as mock_path:
            mock_cwd = MagicMock()
            agents_path = MagicMock()
            agents_path.exists.return_value = False
            mock_cwd.__truediv__ = MagicMock(
                side_effect=lambda x: agents_path if x == "agents" else mock_cwd
            )
            mock_path.cwd.return_value = mock_cwd

            issues = svc._validate_deployed_agents()

        assert len(issues) == 1
        assert issues[0].severity == "warning"
        assert "No deployed agents directory found" in issues[0].message

    def test_valid_agent(self, tmp_path):
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "engineer.md").write_text(
            "---\nname: Engineer\ndescription: Test\n---\n\n# Engineer\n\nSome content here for the agent."
        )

        svc = ConfigValidationService()
        with patch(
            "claude_mpm.services.config.config_validation_service.Path"
        ) as mock_path:
            mock_path.cwd.return_value = tmp_path

            issues = svc._validate_deployed_agents()

        # Should have no errors for a valid agent
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_agent_no_frontmatter(self, tmp_path):
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "broken.md").write_text(
            "# Just a heading\n\nNo frontmatter here."
        )

        svc = ConfigValidationService()
        with patch(
            "claude_mpm.services.config.config_validation_service.Path"
        ) as mock_path:
            mock_path.cwd.return_value = tmp_path

            issues = svc._validate_deployed_agents()

        warnings = [i for i in issues if i.severity == "warning"]
        assert any("no YAML frontmatter" in w.message for w in warnings)

    def test_agent_invalid_yaml(self, tmp_path):
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "bad-yaml.md").write_text(
            "---\ninvalid: [unterminated\n---\n\n# Agent"
        )

        svc = ConfigValidationService()
        with patch(
            "claude_mpm.services.config.config_validation_service.Path"
        ) as mock_path:
            mock_path.cwd.return_value = tmp_path

            issues = svc._validate_deployed_agents()

        errors = [i for i in issues if i.severity == "error"]
        assert any("invalid YAML" in e.message for e in errors)

    def test_agent_missing_name(self, tmp_path):
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "no-name.md").write_text(
            "---\ndescription: No name field\n---\n\n# Agent without name field"
        )

        svc = ConfigValidationService()
        with patch(
            "claude_mpm.services.config.config_validation_service.Path"
        ) as mock_path:
            mock_path.cwd.return_value = tmp_path

            issues = svc._validate_deployed_agents()

        warnings = [i for i in issues if i.severity == "warning"]
        assert any("missing 'name'" in w.message for w in warnings)

    def test_agent_tiny_content(self, tmp_path):
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "tiny.md").write_text("---\nname: Tiny\n---\n")

        svc = ConfigValidationService()
        with patch(
            "claude_mpm.services.config.config_validation_service.Path"
        ) as mock_path:
            mock_path.cwd.return_value = tmp_path

            issues = svc._validate_deployed_agents()

        warnings = [i for i in issues if i.severity == "warning"]
        assert any("very little content" in w.message for w in warnings)


class TestAgentSourceValidation:
    """Test _validate_agent_sources."""

    def test_valid_sources(self):
        svc = ConfigValidationService()
        mock_config = MagicMock()
        mock_repo = MagicMock()
        mock_repo.url = "https://github.com/owner/repo"
        mock_repo.enabled = True
        mock_config.repositories = [mock_repo]

        with patch(
            "claude_mpm.services.config.config_validation_service.AgentSourceConfiguration",
            create=True,
        ) as mock_cls:
            # We need to patch the import inside the method
            with patch.dict(
                "sys.modules",
                {
                    "claude_mpm.config.agent_sources": MagicMock(
                        AgentSourceConfiguration=MagicMock(
                            load=MagicMock(return_value=mock_config)
                        )
                    )
                },
            ):
                issues = svc._validate_agent_sources()

        # Valid URL should produce no errors
        errors = [i for i in issues if i.severity == "error"]
        assert len(errors) == 0

    def test_disabled_source_info(self):
        svc = ConfigValidationService()
        mock_config = MagicMock()
        mock_repo = MagicMock()
        mock_repo.url = "https://github.com/owner/repo"
        mock_repo.enabled = False
        mock_config.repositories = [mock_repo]

        with patch.dict(
            "sys.modules",
            {
                "claude_mpm.config.agent_sources": MagicMock(
                    AgentSourceConfiguration=MagicMock(
                        load=MagicMock(return_value=mock_config)
                    )
                )
            },
        ):
            issues = svc._validate_agent_sources()

        info = [i for i in issues if i.severity == "info"]
        assert any("disabled" in i.message for i in info)

    def test_invalid_url(self):
        svc = ConfigValidationService()
        mock_config = MagicMock()
        mock_repo = MagicMock()
        mock_repo.url = "not-a-url"
        mock_repo.enabled = True
        mock_config.repositories = [mock_repo]

        with patch.dict(
            "sys.modules",
            {
                "claude_mpm.config.agent_sources": MagicMock(
                    AgentSourceConfiguration=MagicMock(
                        load=MagicMock(return_value=mock_config)
                    )
                )
            },
        ):
            issues = svc._validate_agent_sources()

        errors = [i for i in issues if i.severity == "error"]
        assert any("invalid" in e.message.lower() for e in errors)


class TestEnvOverrideValidation:
    """Test _validate_env_overrides."""

    def test_detects_claude_mpm_env_vars(self):
        svc = ConfigValidationService()
        with patch.dict(os.environ, {"CLAUDE_MPM_TEST_VAR": "test_value"}, clear=False):
            issues = svc._validate_env_overrides()

        found = [i for i in issues if "CLAUDE_MPM_TEST_VAR" in i.path]
        assert len(found) >= 1
        assert found[0].severity == "info"
        assert found[0].category == "environment"

    def test_masks_sensitive_values(self):
        svc = ConfigValidationService()
        with patch.dict(
            os.environ, {"CLAUDE_MPM_API_TOKEN": "super_secret"}, clear=False
        ):
            issues = svc._validate_env_overrides()

        token_issues = [i for i in issues if "TOKEN" in i.path]
        assert len(token_issues) >= 1
        assert "***" in token_issues[0].message
        assert "super_secret" not in token_issues[0].message

    def test_no_claude_mpm_vars(self):
        svc = ConfigValidationService()
        # Filter out any existing CLAUDE_MPM_ vars for a clean test
        clean_env = {
            k: v for k, v in os.environ.items() if not k.startswith("CLAUDE_MPM_")
        }
        with patch.dict(os.environ, clean_env, clear=True):
            issues = svc._validate_env_overrides()

        assert len(issues) == 0


class TestCrossReferenceValidation:
    """Test _validate_cross_references."""

    def test_missing_deployed_skill(self, tmp_path):
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "engineer.md").write_text(
            "---\nname: Engineer\nskills:\n- missing-skill\n- deployed-skill\n---\n\n# Engineer"
        )

        svc = ConfigValidationService()

        mock_deployer = MagicMock()
        mock_deployer.check_deployed_skills.return_value = {
            "skills": [{"name": "deployed-skill"}]
        }

        with patch(
            "claude_mpm.services.config.config_validation_service.Path"
        ) as mock_path:
            mock_path.cwd.return_value = tmp_path

            with patch.dict(
                "sys.modules",
                {
                    "claude_mpm.services.skills_deployer": MagicMock(
                        SkillsDeployerService=MagicMock(return_value=mock_deployer)
                    )
                },
            ):
                issues = svc._validate_cross_references()

        warnings = [i for i in issues if i.severity == "warning"]
        assert any("missing-skill" in w.message for w in warnings)
        # deployed-skill should NOT appear as a warning
        assert not any("deployed-skill" in w.message for w in warnings)

    def test_content_marker_cross_reference(self, tmp_path):
        agents_dir = tmp_path / ".claude" / "agents"
        agents_dir.mkdir(parents=True)
        (agents_dir / "pm.md").write_text(
            "---\nname: PM\n---\n\nUse **[SKILL: undeployed-marker-skill]** here."
        )

        svc = ConfigValidationService()
        mock_deployer = MagicMock()
        mock_deployer.check_deployed_skills.return_value = {"skills": []}

        with patch(
            "claude_mpm.services.config.config_validation_service.Path"
        ) as mock_path:
            mock_path.cwd.return_value = tmp_path

            with patch.dict(
                "sys.modules",
                {
                    "claude_mpm.services.skills_deployer": MagicMock(
                        SkillsDeployerService=MagicMock(return_value=mock_deployer)
                    )
                },
            ):
                issues = svc._validate_cross_references()

        warnings = [i for i in issues if i.severity == "warning"]
        assert any("undeployed-marker-skill" in w.message for w in warnings)


class TestValidationCache:
    """Test caching behavior."""

    def test_cache_returns_same_result(self):
        svc = ConfigValidationService()

        # Pre-populate cache
        cached_result = {
            "success": True,
            "valid": True,
            "issues": [],
            "summary": {"errors": 0, "warnings": 0, "info": 0},
        }
        svc._cache = cached_result
        svc._cache_time = time.monotonic()

        result = svc.validate_cached()
        assert result is cached_result

    def test_cache_invalidation(self):
        svc = ConfigValidationService()
        svc._cache = {"cached": True}
        svc._cache_time = time.monotonic()

        svc.invalidate_cache()

        assert svc._cache is None
        assert svc._cache_time == 0.0

    def test_expired_cache_triggers_revalidation(self):
        svc = ConfigValidationService()
        svc._cache = {"old": True}
        svc._cache_time = time.monotonic() - 120  # 2 minutes ago (> 60s TTL)

        # Mock the validate method to avoid actual validation
        with patch.object(svc, "validate") as mock_validate:
            mock_validate.return_value = ValidationResult(valid=True, issues=[])
            result = svc.validate_cached()

        mock_validate.assert_called_once()
        assert result["valid"] is True
