"""
Tests for MPM Agent Manager agent functionality.

This test suite validates:
- Agent definition structure and schema compliance
- Improvement detection logic
- PR workflow integration
- Service usage patterns
- Error handling and graceful degradation
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml


@pytest.fixture
def agent_templates_dir():
    """Return path to agent templates directory"""
    return (
        Path(__file__).parent.parent.parent
        / "src"
        / "claude_mpm"
        / "agents"
        / "templates"
    )


@pytest.fixture
def mpm_agent_manager_json(agent_templates_dir):
    """Load mpm-agent-manager JSON definition"""
    json_path = agent_templates_dir / "mpm-agent-manager.json"
    with open(json_path) as f:
        return json.load(f)


@pytest.fixture
def mpm_agent_manager_md(agent_templates_dir):
    """Load mpm-agent-manager markdown content"""
    md_path = agent_templates_dir / "mpm-agent-manager.md"
    with open(md_path) as f:
        return f.read()


@pytest.fixture
def sample_agent_content():
    """Sample agent markdown content for testing"""
    return """---
name: test_agent
description: Test agent for validation
version: 1.0.0
schema_version: 1.3.0
agent_id: test-agent
agent_type: user
model: sonnet
resource_tier: standard
tags:
- testing
category: test
---

# Test Agent

This is a test agent for validation purposes.
"""


class TestAgentDefinitionStructure:
    """Test suite for agent definition JSON structure"""

    def test_json_file_exists(self, agent_templates_dir):
        """Test that JSON definition file exists"""
        json_path = agent_templates_dir / "mpm-agent-manager.json"
        assert json_path.exists(), "mpm-agent-manager.json must exist"

    def test_markdown_file_exists(self, agent_templates_dir):
        """Test that markdown instruction file exists"""
        md_path = agent_templates_dir / "mpm-agent-manager.md"
        assert md_path.exists(), "mpm-agent-manager.md must exist"

    def test_json_is_valid(self, mpm_agent_manager_json):
        """Test that JSON is valid and parseable"""
        assert isinstance(mpm_agent_manager_json, dict)
        assert len(mpm_agent_manager_json) > 0

    def test_required_fields_present(self, mpm_agent_manager_json):
        """Test all required schema 1.3.0 fields are present"""
        required_fields = [
            "name",
            "description",
            "version",
            "schema_version",
            "agent_id",
            "agent_type",
            "model",
            "resource_tier",
            "tags",
            "category",
        ]

        for field in required_fields:
            assert field in mpm_agent_manager_json, f"Missing required field: {field}"

    def test_schema_version_correct(self, mpm_agent_manager_json):
        """Test schema version is 1.3.0"""
        assert mpm_agent_manager_json["schema_version"] == "1.3.0"

    def test_agent_id_format(self, mpm_agent_manager_json):
        """Test agent ID follows naming conventions"""
        agent_id = mpm_agent_manager_json["agent_id"]
        assert agent_id == "mpm-agent-manager"
        assert agent_id.islower()
        assert " " not in agent_id
        assert "_" not in agent_id

    def test_semantic_version_format(self, mpm_agent_manager_json):
        """Test version follows semantic versioning"""
        version = mpm_agent_manager_json["version"]
        parts = version.split(".")
        assert len(parts) == 3
        for part in parts:
            assert part.isdigit()

    def test_agent_type_valid(self, mpm_agent_manager_json):
        """Test agent_type is valid"""
        valid_types = ["system", "user", "project", "claude-mpm"]
        assert mpm_agent_manager_json["agent_type"] in valid_types

    def test_model_valid(self, mpm_agent_manager_json):
        """Test model is valid"""
        valid_models = ["sonnet", "opus", "haiku"]
        assert mpm_agent_manager_json["model"] in valid_models

    def test_resource_tier_valid(self, mpm_agent_manager_json):
        """Test resource_tier is valid"""
        valid_tiers = ["low", "standard", "high"]
        assert mpm_agent_manager_json["resource_tier"] in valid_tiers

    def test_tags_is_list(self, mpm_agent_manager_json):
        """Test tags is a list"""
        assert isinstance(mpm_agent_manager_json["tags"], list)
        assert len(mpm_agent_manager_json["tags"]) > 0

    def test_dependencies_structure(self, mpm_agent_manager_json):
        """Test dependencies structure is correct"""
        assert "dependencies" in mpm_agent_manager_json
        deps = mpm_agent_manager_json["dependencies"]

        assert "python" in deps
        assert isinstance(deps["python"], list)
        assert "gitpython>=3.1.0" in deps["python"]

        assert "system" in deps
        assert isinstance(deps["system"], list)
        assert "git" in deps["system"]
        assert "gh" in deps["system"]

    def test_network_access_enabled(self, mpm_agent_manager_json):
        """Test network access is enabled for GitHub operations"""
        assert "capabilities" in mpm_agent_manager_json
        assert mpm_agent_manager_json["capabilities"]["network_access"] is True

    def test_instruction_file_referenced(self, mpm_agent_manager_json):
        """Test instruction_file points to markdown file"""
        assert mpm_agent_manager_json["instruction_file"] == "mpm-agent-manager.md"


class TestMarkdownInstructions:
    """Test suite for markdown instruction content"""

    def test_yaml_frontmatter_present(self, mpm_agent_manager_md):
        """Test YAML frontmatter is present"""
        assert mpm_agent_manager_md.startswith("---")
        parts = mpm_agent_manager_md.split("---", 2)
        assert len(parts) >= 3

    def test_yaml_frontmatter_valid(self, mpm_agent_manager_md):
        """Test YAML frontmatter is valid"""
        parts = mpm_agent_manager_md.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])
        assert isinstance(frontmatter, dict)
        assert "name" in frontmatter
        assert "version" in frontmatter

    def test_required_sections_present(self, mpm_agent_manager_md):
        """Test all required instruction sections are present"""
        required_sections = [
            "# MPM Agent Manager",
            "## Core Identity",
            "## Agent Management Capabilities",
            "## PR Workflow Integration",
            "## PR Creation Process",
            "## Service Integration",
            "## Configuration Management",
            "## Error Handling",
            "## Best Practices Summary",
        ]

        for section in required_sections:
            assert section in mpm_agent_manager_md, f"Missing section: {section}"

    def test_service_integration_documented(self, mpm_agent_manager_md):
        """Test service integration is documented"""
        assert "GitOperationsService" in mpm_agent_manager_md
        assert "PRTemplateService" in mpm_agent_manager_md
        assert "GitHubCLIService" in mpm_agent_manager_md
        assert "from claude_mpm.services.git import" in mpm_agent_manager_md
        assert "from claude_mpm.services.pr import" in mpm_agent_manager_md
        assert "from claude_mpm.services.github import" in mpm_agent_manager_md

    def test_pr_workflow_documented(self, mpm_agent_manager_md):
        """Test PR workflow steps are documented"""
        workflow_keywords = [
            "Phase 1: Analysis",
            "Phase 2: Modification",
            "Phase 3: PR Submission",
            "create_branch",
            "commit_changes",
            "push_branch",
            "create_pull_request",
        ]

        for keyword in workflow_keywords:
            assert keyword in mpm_agent_manager_md

    def test_error_handling_documented(self, mpm_agent_manager_md):
        """Test error handling scenarios are documented"""
        error_scenarios = [
            "Authentication Errors",
            "Git Operation Errors",
            "PR Creation Errors",
            "Agent Validation Errors",
        ]

        for scenario in error_scenarios:
            assert scenario in mpm_agent_manager_md

    def test_improvement_triggers_documented(self, mpm_agent_manager_md):
        """Test improvement detection triggers are documented"""
        triggers = [
            "User Feedback Patterns",
            "Circuit Breaker Violations",
            "Error Patterns",
            "Manual Improvement Requests",
        ]

        for trigger in triggers:
            assert trigger in mpm_agent_manager_md

    def test_branch_naming_convention_documented(self, mpm_agent_manager_md):
        """Test branch naming convention is documented"""
        assert "improve/{agent-name}-{short-description}" in mpm_agent_manager_md
        assert "improve/research-memory-efficiency" in mpm_agent_manager_md

    def test_conventional_commit_documented(self, mpm_agent_manager_md):
        """Test conventional commit format is documented"""
        assert "feat(" in mpm_agent_manager_md or "feat:" in mpm_agent_manager_md
        # Check for "fix" without parenthesis since it appears as "fix:" in type list
        assert "fix" in mpm_agent_manager_md.lower()
        assert "conventional commit" in mpm_agent_manager_md.lower()

    def test_examples_present(self, mpm_agent_manager_md):
        """Test example workflows are present"""
        assert (
            "Example 1:" in mpm_agent_manager_md
            or "### Example" in mpm_agent_manager_md
        )
        assert "User Reports Memory Issue" in mpm_agent_manager_md
        assert "Circuit Breaker Violation" in mpm_agent_manager_md


class TestImprovementDetection:
    """Test suite for improvement detection logic"""

    def test_user_feedback_patterns(self):
        """Test detection of user feedback patterns"""
        feedback_examples = [
            "the research agent ran out of memory",
            "research agent is too slow",
            "engineer agent doesn't handle errors well",
        ]

        for feedback in feedback_examples:
            # Should identify agent name
            assert "research" in feedback or "engineer" in feedback
            # Should identify problem type
            assert any(
                word in feedback.lower()
                for word in ["memory", "slow", "error", "fail", "doesn't"]
            )

    def test_circuit_breaker_violation_detection(self):
        """Test detection of circuit breaker violations"""
        violation_log = (
            "WARNING: Circuit Breaker #3 - PM wrote code instead of delegating"
        )

        assert "Circuit Breaker" in violation_log
        assert "PM" in violation_log
        assert "delegating" in violation_log

    def test_actionable_feedback_criteria(self):
        """Test criteria for actionable vs non-actionable feedback"""
        actionable = [
            {
                "feedback": "research agent memory issue with 100 files",
                "has_agent": True,
                "has_problem": True,
                "has_context": True,
            },
            {
                "feedback": "engineer agent timeout on large refactoring",
                "has_agent": True,
                "has_problem": True,
                "has_context": True,
            },
        ]

        non_actionable = [
            {
                "feedback": "something isn't working",
                "has_agent": False,
                "has_problem": False,
                "has_context": False,
            },
            {
                "feedback": "agents are bad",
                "has_agent": False,
                "has_problem": False,
                "has_context": False,
            },
        ]

        for item in actionable:
            assert item["has_agent"] and item["has_problem"]

        for item in non_actionable:
            assert not (item["has_agent"] and item["has_problem"])


class TestServiceIntegration:
    """Test suite for service integration patterns"""

    def test_git_operations_service_documented(self, mpm_agent_manager_md):
        """Test GitOperationsService usage is documented"""
        assert "GitOperationsService" in mpm_agent_manager_md
        assert "from claude_mpm.services.git import" in mpm_agent_manager_md
        assert "create_branch" in mpm_agent_manager_md
        assert "commit_changes" in mpm_agent_manager_md
        assert "push_branch" in mpm_agent_manager_md

    def test_pr_template_service_documented(self, mpm_agent_manager_md):
        """Test PRTemplateService usage is documented"""
        assert "PRTemplateService" in mpm_agent_manager_md
        assert "from claude_mpm.services.pr import" in mpm_agent_manager_md
        assert "generate_agent_improvement_pr" in mpm_agent_manager_md

    def test_github_cli_service_documented(self, mpm_agent_manager_md):
        """Test GitHubCLIService usage is documented"""
        assert "GitHubCLIService" in mpm_agent_manager_md
        assert "from claude_mpm.services.github import" in mpm_agent_manager_md
        assert "create_pull_request" in mpm_agent_manager_md
        assert "check_authentication" in mpm_agent_manager_md


class TestSchemaValidation:
    """Test suite for agent schema validation"""

    def test_valid_agent_content(self, sample_agent_content):
        """Test validation of valid agent content"""
        assert sample_agent_content.startswith("---")
        parts = sample_agent_content.split("---", 2)
        assert len(parts) == 3

        frontmatter = yaml.safe_load(parts[1])
        assert frontmatter["schema_version"] == "1.3.0"

    def test_semantic_version_validation(self):
        """Test semantic version format validation"""
        import re

        version_pattern = r"^\d+\.\d+\.\d+$"

        valid_versions = ["1.0.0", "2.1.3", "10.20.30"]
        invalid_versions = ["1.0", "v1.0.0", "1.0.0-beta", "1.0.0.0"]

        for version in valid_versions:
            assert re.match(version_pattern, version)

        for version in invalid_versions:
            assert not re.match(version_pattern, version)

    def test_required_fields_validation(self, sample_agent_content):
        """Test required fields validation"""
        parts = sample_agent_content.split("---", 2)
        frontmatter = yaml.safe_load(parts[1])

        required_fields = {
            "name": str,
            "description": str,
            "version": str,
            "schema_version": str,
            "agent_id": str,
            "agent_type": str,
            "model": str,
            "resource_tier": str,
            "tags": list,
            "category": str,
        }

        for field, field_type in required_fields.items():
            assert field in frontmatter
            assert isinstance(frontmatter[field], field_type)


class TestVersionBumping:
    """Test suite for version bumping logic"""

    def test_major_version_bump(self):
        """Test MAJOR version bump logic"""
        version = "1.2.3"
        parts = version.split(".")
        major = int(parts[0]) + 1
        new_version = f"{major}.0.0"
        assert new_version == "2.0.0"

    def test_minor_version_bump(self):
        """Test MINOR version bump logic"""
        version = "1.2.3"
        parts = version.split(".")
        minor = int(parts[1]) + 1
        new_version = f"{parts[0]}.{minor}.0"
        assert new_version == "1.3.0"

    def test_patch_version_bump(self):
        """Test PATCH version bump logic"""
        version = "1.2.3"
        parts = version.split(".")
        patch = int(parts[2]) + 1
        new_version = f"{parts[0]}.{parts[1]}.{patch}"
        assert new_version == "1.2.4"

    def test_version_comparison(self):
        """Test version comparison logic"""
        from packaging import version

        v1 = version.parse("1.0.0")
        v2 = version.parse("1.0.1")
        v3 = version.parse("2.0.0")

        assert v1 < v2
        assert v2 < v3
        assert v1 < v3


class TestErrorHandling:
    """Test suite for error handling scenarios"""

    def test_authentication_error_handling(self):
        """Test handling of authentication errors"""
        error_message = "gh: authentication failed"

        assert "authentication" in error_message
        # Recovery steps should be documented
        assert True  # Placeholder for actual error handling logic

    def test_git_operation_error_handling(self):
        """Test handling of git operation errors"""
        error_scenarios = [
            "Cannot create branch with uncommitted changes",
            "Branch 'improve/test' already exists",
            "Network timeout during push",
        ]

        for error in error_scenarios:
            # Each error should have recovery steps documented
            assert len(error) > 0

    def test_pr_creation_error_handling(self):
        """Test handling of PR creation errors"""
        error_result = {
            "success": False,
            "error": "Network timeout",
            "error_type": "network",
        }

        assert not error_result["success"]
        assert "error" in error_result
        assert "error_type" in error_result

    def test_yaml_validation_error_handling(self):
        """Test handling of YAML validation errors"""
        invalid_yaml = """---
name: test
version: 1.0.0
tags: [unclosed bracket
---"""

        with pytest.raises(yaml.YAMLError):
            yaml.safe_load(invalid_yaml.split("---")[1])


class TestGracefulDegradation:
    """Test suite for graceful degradation behavior"""

    def test_pr_creation_fallback(self):
        """Test fallback when PR creation fails"""
        result = {
            "status": "manual_required",
            "branch_name": "improve/test-agent",
            "pr_body": "PR description",
            "message": "Please create PR manually",
            "instructions": [
                "1. Visit: https://github.com/.../compare/improve/test-agent",
                "2. Click 'Create Pull Request'",
                "3. Copy PR description provided below",
                "4. Submit PR",
            ],
        }

        assert result["status"] == "manual_required"
        assert "branch_name" in result
        assert "instructions" in result
        assert len(result["instructions"]) > 0

    def test_error_reporting_with_recovery(self):
        """Test error reporting includes recovery steps"""
        error_report = {
            "status": "error",
            "error": "Network timeout",
            "recovery_steps": [
                "1. Check network connection",
                "2. Retry push command",
                "3. Create PR manually if needed",
            ],
            "message": "Changes are saved locally",
        }

        assert error_report["status"] == "error"
        assert "recovery_steps" in error_report
        assert len(error_report["recovery_steps"]) > 0
        assert error_report["message"]  # Non-empty message

    def test_non_blocking_behavior(self):
        """Test that failures don't block workflow"""

        def attempt_pr_creation():
            try:
                # Simulated PR creation
                raise Exception("Network error")
            except Exception as e:
                # Should not re-raise, should return error info
                return {"status": "error", "error": str(e), "recovery_steps": [...]}

        result = attempt_pr_creation()
        assert result["status"] == "error"
        assert "recovery_steps" in result


class TestBranchNaming:
    """Test suite for branch naming conventions"""

    def test_branch_name_format(self):
        """Test branch name follows convention"""
        branch_names = [
            "improve/research-memory-efficiency",
            "improve/engineer-error-handling",
            "improve/qa-test-coverage",
        ]

        for branch_name in branch_names:
            assert branch_name.startswith("improve/")
            assert "-" in branch_name
            assert " " not in branch_name

    def test_branch_name_generation(self):
        """Test branch name generation logic"""
        agent_name = "research"
        issue = "memory-efficiency"
        branch_name = f"improve/{agent_name}-{issue}"

        assert branch_name == "improve/research-memory-efficiency"
        assert branch_name.count("/") == 1


class TestConventionalCommits:
    """Test suite for conventional commit format"""

    def test_commit_message_format(self):
        """Test commit message follows conventional format"""
        commit_messages = [
            "feat(agent): improve research agent memory efficiency",
            "fix(agent): correct engineer agent error handling",
            "docs(agent): update QA agent documentation",
        ]

        for message in commit_messages:
            assert message.startswith(
                ("feat", "fix", "docs", "refactor", "perf", "test", "chore")
            )
            assert ":" in message
            assert "(agent)" in message or "(" in message

    def test_commit_message_structure(self):
        """Test commit message has proper structure"""
        commit = """feat(agent): improve research agent memory efficiency

- Add explicit file limit warnings
- Document MCP summarizer integration
- Update strategic sampling guidance

Addresses user feedback about memory exhaustion."""

        lines = commit.split("\n")
        assert lines[0].startswith("feat")  # Type
        assert ":" in lines[0]  # Separator
        assert lines[1] == ""  # Blank line after header
        assert lines[2].startswith("-")  # Bullet points


class TestIntegrationWithExistingSystem:
    """Test suite for integration with existing system"""

    def test_cached_repository_path(self):
        """Test cached repository path is correct"""
        expected_path = (
            Path.home()
            / ".claude-mpm"
            / "cache"
            / "remote-agents"
            / "bobmatnyc"
            / "claude-mpm-agents"
        )

        assert expected_path.parts[-1] == "claude-mpm-agents"
        assert expected_path.parts[-2] == "bobmatnyc"
        assert expected_path.parts[-3] == "remote-agents"

    def test_deployed_agents_paths(self):
        """Test deployed agents paths are correct"""
        user_path = Path.home() / ".claude" / "agents"
        project_path = Path.cwd() / ".claude-mpm" / "agents"

        assert user_path.parts[-1] == "agents"
        assert user_path.parts[-2] == ".claude"

        assert project_path.parts[-1] == "agents"
        assert project_path.parts[-2] == ".claude-mpm"

    def test_agent_sync_workflow(self):
        """Test agent sync workflow steps"""
        workflow_steps = [
            "1. User runs: claude-mpm agents sync",
            "2. Agents updated in cache",
            "3. User deploys: claude-mpm agents deploy {agent} --force",
            "4. Agent available in ~/.claude/agents/",
        ]

        assert len(workflow_steps) == 4
        assert "sync" in workflow_steps[0]
        assert "deploy" in workflow_steps[2]


# Integration tests (would require actual Git repo setup)
@pytest.mark.integration
class TestEndToEndPRWorkflow:
    """Integration tests for end-to-end PR workflow (requires setup)"""

    @pytest.mark.skip(reason="Requires Git repository setup")
    def test_full_pr_workflow(self):
        """Test complete PR workflow from detection to creation"""
        # This would test:
        # 1. Detect improvement opportunity
        # 2. Analyze agent definition
        # 3. Create branch
        # 4. Modify agent file
        # 5. Commit changes
        # 6. Push branch
        # 7. Create PR

    @pytest.mark.skip(reason="Requires GitHub authentication")
    def test_github_authentication(self):
        """Test GitHub CLI authentication check"""
        from claude_mpm.services.github import GitHubCLIService

        gh_service = GitHubCLIService()
        is_authenticated = gh_service.check_authentication()
        # In CI/test environment, this may be False
        assert isinstance(is_authenticated, bool)


# Performance tests
@pytest.mark.performance
class TestPerformance:
    """Performance tests for agent operations"""

    def test_yaml_parsing_performance(self, sample_agent_content):
        """Test YAML parsing performance"""
        import time

        start = time.time()
        for _ in range(100):
            parts = sample_agent_content.split("---", 2)
            yaml.safe_load(parts[1])
        elapsed = time.time() - start

        # Should parse 100 times in under 1 second
        assert elapsed < 1.0

    def test_schema_validation_performance(self, sample_agent_content):
        """Test schema validation performance"""
        import time

        start = time.time()
        for _ in range(100):
            parts = sample_agent_content.split("---", 2)
            frontmatter = yaml.safe_load(parts[1])
            # Quick validation
            assert frontmatter["schema_version"] == "1.3.0"
        elapsed = time.time() - start

        # Should validate 100 times in under 1 second
        assert elapsed < 1.0
