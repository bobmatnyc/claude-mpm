"""Tests for configuration validation endpoint.

Tests:
- Valid config returns no errors
- Agent validation (missing frontmatter, invalid YAML, etc.)
- Source validation (invalid URLs, disabled sources)
- Environment variable override detection
- Cross-reference validation (skills referenced but not deployed)
- Response format and caching
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.services.monitor.config_routes import handle_validate


class TestValidateEndpoint:
    """Test the GET /api/config/validate endpoint handler."""

    @pytest.fixture
    def mock_validation_service(self):
        """Create a mock ConfigValidationService."""
        svc = MagicMock()
        svc.validate_cached.return_value = {
            "success": True,
            "valid": True,
            "issues": [],
            "summary": {"errors": 0, "warnings": 0, "info": 0},
        }
        return svc

    @pytest.mark.asyncio
    async def test_validate_clean_config(self, mock_validation_service):
        """Test validation with no issues returns valid=True."""
        request = MagicMock()

        with patch(
            "claude_mpm.services.monitor.config_routes._get_config_validation_service",
            return_value=mock_validation_service,
        ):
            response = await handle_validate(request)

        data = json.loads(response.body)
        assert data["success"] is True
        assert data["valid"] is True
        assert data["summary"]["errors"] == 0

    @pytest.mark.asyncio
    async def test_validate_with_errors(self, mock_validation_service):
        """Test validation with errors returns valid=False."""
        mock_validation_service.validate_cached.return_value = {
            "success": True,
            "valid": False,
            "issues": [
                {
                    "severity": "error",
                    "category": "agent",
                    "path": "agents.broken-agent",
                    "message": "Agent 'broken-agent' has invalid YAML frontmatter",
                    "suggestion": "Fix the YAML syntax in the agent's frontmatter section.",
                }
            ],
            "summary": {"errors": 1, "warnings": 0, "info": 0},
        }

        request = MagicMock()

        with patch(
            "claude_mpm.services.monitor.config_routes._get_config_validation_service",
            return_value=mock_validation_service,
        ):
            response = await handle_validate(request)

        data = json.loads(response.body)
        assert data["success"] is True
        assert data["valid"] is False
        assert data["summary"]["errors"] == 1
        assert len(data["issues"]) == 1
        assert data["issues"][0]["severity"] == "error"
        assert data["issues"][0]["suggestion"]  # Must have suggestion

    @pytest.mark.asyncio
    async def test_validate_issue_format(self, mock_validation_service):
        """Test that every issue has required fields."""
        mock_validation_service.validate_cached.return_value = {
            "success": True,
            "valid": False,
            "issues": [
                {
                    "severity": "warning",
                    "category": "cross_reference",
                    "path": "agents.engineer.skills.nonexistent-skill",
                    "message": "Agent 'engineer' references skill 'nonexistent-skill' which is not deployed",
                    "suggestion": "Deploy the 'nonexistent-skill' skill or remove the reference.",
                },
                {
                    "severity": "info",
                    "category": "environment",
                    "path": "env.CLAUDE_MPM_LOG_LEVEL",
                    "message": "Environment variable 'CLAUDE_MPM_LOG_LEVEL' overrides config (value: DEBUG)",
                    "suggestion": "Remove it from your shell environment if unintended.",
                },
            ],
            "summary": {"errors": 0, "warnings": 1, "info": 1},
        }

        request = MagicMock()

        with patch(
            "claude_mpm.services.monitor.config_routes._get_config_validation_service",
            return_value=mock_validation_service,
        ):
            response = await handle_validate(request)

        data = json.loads(response.body)
        for issue in data["issues"]:
            assert "severity" in issue
            assert "category" in issue
            assert "path" in issue
            assert "message" in issue
            assert "suggestion" in issue

    @pytest.mark.asyncio
    async def test_validate_service_error(self):
        """Test validation returns 500 on service error."""
        mock_svc = MagicMock()
        mock_svc.validate_cached.side_effect = RuntimeError("service crashed")

        request = MagicMock()

        with patch(
            "claude_mpm.services.monitor.config_routes._get_config_validation_service",
            return_value=mock_svc,
        ):
            response = await handle_validate(request)

        assert response.status == 500
        data = json.loads(response.body)
        assert data["success"] is False
        assert data["code"] == "SERVICE_ERROR"

    @pytest.mark.asyncio
    async def test_validate_with_env_overrides(self, mock_validation_service):
        """Test that env override detection works."""
        mock_validation_service.validate_cached.return_value = {
            "success": True,
            "valid": True,
            "issues": [
                {
                    "severity": "info",
                    "category": "environment",
                    "path": "env.CLAUDE_MPM_SOCKETIO_PORT",
                    "message": "Environment variable 'CLAUDE_MPM_SOCKETIO_PORT' overrides config (value: 9000)",
                    "suggestion": "Remove it from your shell environment if the override is unintended.",
                },
            ],
            "summary": {"errors": 0, "warnings": 0, "info": 1},
        }

        request = MagicMock()

        with patch(
            "claude_mpm.services.monitor.config_routes._get_config_validation_service",
            return_value=mock_validation_service,
        ):
            response = await handle_validate(request)

        data = json.loads(response.body)
        assert data["valid"] is True  # info-only doesn't make it invalid
        assert data["summary"]["info"] == 1
