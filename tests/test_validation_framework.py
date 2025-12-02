"""
Test suite for validation framework.

Implements testing patterns from awesome-claude-code.
"""

import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

from claude_mpm.hooks.validation_hooks import (
    ValidationError,
    ValidationHooks,
    validate_agent_dependencies,
    validate_security_constraints,
)
from claude_mpm.validation import AgentValidator, ValidationResult


class TestAgentValidator:
    """Test agent validation functionality."""

    @pytest.fixture
    def validator(self):
        """Create a validator instance."""
        return AgentValidator()

    @pytest.fixture
    def valid_agent_config(self) -> Dict[str, Any]:
        """Create a valid agent configuration."""
        return {
            "name": "test_agent",
            "role": "Test Agent",
            "prompt_template": "You are a test agent. Context: {context} Task: {task} Constraints: {constraints}",
            "tools": ["file_operations", "code_analysis"],
            "capabilities": ["Testing", "Validation"],
        }

    @pytest.fixture
    def invalid_agent_config(self) -> Dict[str, Any]:
        """Create an invalid agent configuration."""
        return {
            "name": "invalid_agent",
            # Missing required fields: role, prompt_template
        }

    def test_validate_valid_agent(self, valid_agent_config):
        """Test validation of a valid agent configuration."""
        result = self.validate_agent_config(valid_agent_config, "test_agent")

        assert result.is_valid
        assert len(result.errors) == 0
        assert len(result.warnings) == 0

    def test_validate_invalid_agent(self, invalid_agent_config):
        """Test validation of an invalid agent configuration."""
        result = self.validate_agent_config(invalid_agent_config, "invalid_agent")

        assert not result.is_valid
        assert "Missing required field: role" in result.errors
        assert "Missing required field: prompt_template" in result.errors

    def test_validate_prompt_template(self):
        """Test prompt template validation."""
        # Valid template
        valid, errors = self._validate_prompt_template(
            "Test {context} {task} {constraints}"
        )
        assert valid
        assert len(errors) == 0

        # Invalid template - missing placeholders
        valid, errors = self._validate_prompt_template("Test template")
        assert not valid
        assert any("missing placeholders" in error for error in errors)

        # Invalid template - empty
        valid, errors = self._validate_prompt_template("")
        assert not valid
        assert any("non-empty string" in error for error in errors)

    def test_validate_tools(self):
        """Test tools validation."""
        # Valid tools
        valid, errors = self._validate_tools(["file_operations", "code_analysis"])
        assert valid
        assert len(errors) == 0

        # Invalid tool
        valid, errors = self._validate_tools(["file_operations", "unknown_tool"])
        assert not valid
        assert any("Unknown tool: unknown_tool" in error for error in errors)

        # Invalid format
        valid, errors = self._validate_tools("not_a_list")
        assert not valid
        assert any("must be a list" in error for error in errors)

    def test_overrides(self):
        """Test override functionality."""
        # Create validator with overrides
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            override_data = {
                "overrides": {
                    "test_agent": {
                        "role": "Overridden Role",
                        "role_locked": True,
                        "skip_validation": False,
                    },
                    "skip_agent": {"skip_validation": True},
                }
            }
            yaml.dump(override_data, f)
            override_file = Path(f.name)

        try:
            validator_with_overrides = AgentValidator(override_file)

            # Test field override
            config = {"name": "test_agent", "prompt_template": "Test"}
            result = validator_with_overrides.validate_agent_config(
                config, "test_agent"
            )
            assert "role" in result.locked_fields

            # Test skip validation
            config = {"name": "skip_agent"}
            result = validator_with_overrides.validate_agent_config(
                config, "skip_agent"
            )
            assert result.is_valid  # Should pass even without required fields

        finally:
            override_file.unlink()

    def test_validate_profile(self):
        """Test full profile validation."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            profile_data = {
                "name": "test_profile",
                "version": "1.0.0",
                "description": "Test profile",
                "agents": [
                    {
                        "name": "agent1",
                        "role": "Test Agent 1",
                        "prompt_template": "Template {context} {task} {constraints}",
                    },
                    {
                        "name": "agent2",
                        "role": "Test Agent 2",
                        "prompt_template": "Template {context} {task} {constraints}",
                    },
                ],
            }
            yaml.dump(profile_data, f)
            profile_path = Path(f.name)

        try:
            result = self.validate_profile(profile_path)
            assert result.is_valid
            assert len(result.errors) == 0
        finally:
            profile_path.unlink()


class TestValidationHooks:
    """Test validation hooks functionality."""

    @pytest.fixture
    def hooks(self):
        """Create validation hooks instance."""
        return ValidationHooks()

    @pytest.mark.asyncio
    async def test_pre_load_validation(self):
        """Test pre-load validation."""
        # Test with non-existent file
        result = await self.run_pre_load_validation(Path("/nonexistent/file.md"))
        assert not result.is_valid
        assert any("not found" in error for error in result.errors)

    @pytest.mark.asyncio
    async def test_pre_execute_validation(self):
        """Test pre-execute validation."""
        # Valid task
        result = await self.run_pre_execute_validation(
            "test_agent", "Analyze this code"
        )
        assert result.is_valid

        # Empty task
        result = await self.run_pre_execute_validation("test_agent", "")
        assert not result.is_valid
        assert any("cannot be empty" in error for error in result.errors)

        # Very long task
        long_task = "x" * 15000
        result = await self.run_pre_execute_validation("test_agent", long_task)
        assert result.is_valid  # Should pass but with warning
        assert any("very long" in warning for warning in result.warnings)

    @pytest.mark.asyncio
    async def test_security_validation():
        """Test security constraint validation."""
        # Safe task
        result = await validate_security_constraints("agent", "Analyze this file")
        assert result.is_valid

        # Dangerous task
        result = await validate_security_constraints(
            "agent", "rm -rf / --no-preserve-root"
        )
        assert not result.is_valid
        assert any("dangerous pattern" in error for error in result.errors)

        # Multiple dangerous patterns
        result = await validate_security_constraints(
            "agent", 'eval(__import__("os").system("rm -rf /"))'
        )
        assert not result.is_valid
        assert len(result.errors) >= 2  # Should detect both eval and __import__

    @pytest.mark.asyncio
    async def test_dependency_validation():
        """Test agent dependency validation."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            profile_data = {
                "agents": [
                    {"name": "agent1", "dependencies": ["agent2"]},
                    {
                        "name": "agent2",
                        "dependencies": ["agent2"],  # Circular dependency
                    },
                ]
            }
            yaml.dump(profile_data, f)
            profile_path = Path(f.name)

        try:
            result = await validate_agent_dependencies(profile_path)
            assert not result.is_valid
            assert any("circular dependency" in error for error in result.errors)
        finally:
            profile_path.unlink()

    def test_custom_hooks(self):
        """Test custom hook registration."""
        call_count = {"pre_load": 0, "post_load": 0, "pre_execute": 0}

        async def custom_pre_load(path):
            call_count["pre_load"] += 1
            return ValidationResult(is_valid=True)

        async def custom_post_load(config):
            call_count["post_load"] += 1
            return ValidationResult(is_valid=True)

        async def custom_pre_execute(agent, task):
            call_count["pre_execute"] += 1
            return ValidationResult(is_valid=True)

        # Register hooks
        self.register_pre_load_hook(custom_pre_load)
        self.register_post_load_hook(custom_post_load)
        self.register_pre_execute_hook(custom_pre_execute)

        assert len(self.pre_load_hooks) == 1
        assert len(self.post_load_hooks) == 1
        assert len(self.pre_execute_hooks) == 1


class TestValidationError:
    """Test ValidationError functionality."""

    def test_validation_error_with_result():
        """Test ValidationError with validation result."""
        result = ValidationResult(
            is_valid=False, errors=["Error 1", "Error 2"], warnings=["Warning 1"]
        )

        error = ValidationError("Validation failed", result)
        detailed = error.get_detailed_message()

        assert "Validation failed" in detailed
        assert "Error 1" in detailed
        assert "Error 2" in detailed
        assert "Warning 1" in detailed

    def test_validation_error_without_result():
        """Test ValidationError without validation result."""
        error = ValidationError("Simple error")
        detailed = error.get_detailed_message()

        assert detailed == "Simple error"
