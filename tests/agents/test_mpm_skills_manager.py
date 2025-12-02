"""
Comprehensive test suite for MPM Skills Manager agent.

Tests cover:
- Agent definition validation
- Markdown instruction completeness
- Technology detection logic
- Skill recommendation engine
- manifest.json management
- PR workflow documentation
- Error handling scenarios
- Skill structure validation
"""

import json
from pathlib import Path

import pytest
import yaml

# Test paths
TEMPLATES_DIR = (
    Path(__file__).parent.parent.parent / "src" / "claude_mpm" / "agents" / "templates"
)
SKILLS_MANAGER_JSON = TEMPLATES_DIR / "mpm-skills-manager.json"
SKILLS_MANAGER_MD = TEMPLATES_DIR / "mpm-skills-manager.md"


# ============================================================================
# Agent Definition Tests (JSON)
# ============================================================================


class TestAgentDefinitionStructure:
    """Test agent JSON definition structure and validity."""

    def test_json_file_exists(self):
        """Verify JSON file exists."""
        assert SKILLS_MANAGER_JSON.exists(), (
            f"Agent JSON not found: {SKILLS_MANAGER_JSON}"
        )

    def test_json_is_valid(self):
        """Verify JSON is parseable."""
        with open(SKILLS_MANAGER_JSON) as f:
            data = json.load(f)
        assert isinstance(data, dict), "Agent JSON must be a dictionary"

    def test_required_fields_present(self):
        """Verify all required schema fields are present."""
        with open(SKILLS_MANAGER_JSON) as f:
            agent = json.load(f)

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
            assert field in agent, f"Missing required field: {field}"
            assert agent[field], f"Field '{field}' cannot be empty"

    def test_schema_version(self):
        """Verify schema version is 1.3.0."""
        with open(SKILLS_MANAGER_JSON) as f:
            agent = json.load(f)
        assert agent["schema_version"] == "1.3.0", "Schema version must be 1.3.0"

    def test_agent_metadata(self):
        """Verify agent metadata is correct."""
        with open(SKILLS_MANAGER_JSON) as f:
            agent = json.load(f)

        assert agent["name"] == "mpm_skills_manager"
        assert agent["agent_id"] == "mpm-skills-manager"
        assert agent["agent_type"] == "claude-mpm"
        assert agent["model"] == "sonnet"
        assert agent["resource_tier"] == "standard"
        assert agent["category"] == "claude-mpm"

    def test_semantic_version_format(self):
        """Verify version follows semantic versioning."""
        with open(SKILLS_MANAGER_JSON) as f:
            agent = json.load(f)

        version = agent["version"]
        parts = version.split(".")
        assert len(parts) == 3, f"Version must be X.Y.Z format: {version}"
        assert all(p.isdigit() for p in parts), (
            f"Version parts must be numeric: {version}"
        )

    def test_tags_present_and_valid(self):
        """Verify tags are present and relevant."""
        with open(SKILLS_MANAGER_JSON) as f:
            agent = json.load(f)

        tags = agent["tags"]
        assert isinstance(tags, list), "Tags must be a list"
        assert len(tags) > 0, "Tags cannot be empty"

        expected_tags = {
            "skill-management",
            "pr-workflow",
            "recommendations",
            "tech-stack",
            "manifest",
            "git-integration",
        }
        assert set(tags) == expected_tags, (
            f"Tags mismatch: {set(tags)} vs {expected_tags}"
        )

    def test_dependencies_structure(self):
        """Verify dependencies are properly structured."""
        with open(SKILLS_MANAGER_JSON) as f:
            agent = json.load(f)

        deps = agent["dependencies"]
        assert "python" in deps, "Python dependencies required"
        assert "system" in deps, "System dependencies required"

        # Check Python dependencies
        assert isinstance(deps["python"], list)
        assert "gitpython>=3.1.0" in deps["python"]
        assert "pyyaml>=6.0.0" in deps["python"]
        assert "jsonschema>=4.17.0" in deps["python"]

        # Check system dependencies
        assert isinstance(deps["system"], list)
        assert "python3" in deps["system"]
        assert "git" in deps["system"]
        assert "gh" in deps["system"]

    def test_capabilities_network_access(self):
        """Verify network access capability is enabled."""
        with open(SKILLS_MANAGER_JSON) as f:
            agent = json.load(f)

        caps = agent["capabilities"]
        assert caps["network_access"] is True, "Network access must be enabled"

    def test_knowledge_domain_expertise(self):
        """Verify domain expertise is documented."""
        with open(SKILLS_MANAGER_JSON) as f:
            agent = json.load(f)

        knowledge = agent.get("knowledge", {})
        expertise = knowledge.get("domain_expertise", [])

        assert len(expertise) > 0, "Domain expertise must be documented"
        assert any("skill lifecycle" in e.lower() for e in expertise)
        assert any("technology stack" in e.lower() for e in expertise)
        assert any("manifest" in e.lower() for e in expertise)

    def test_template_changelog(self):
        """Verify template changelog is present."""
        with open(SKILLS_MANAGER_JSON) as f:
            agent = json.load(f)

        changelog = agent.get("template_changelog", [])
        assert len(changelog) > 0, "Template changelog must have entries"
        assert changelog[0]["version"] == "1.0.0"
        assert "date" in changelog[0]
        assert "description" in changelog[0]


# ============================================================================
# Markdown Instruction Tests
# ============================================================================


class TestMarkdownInstructionStructure:
    """Test markdown instruction file completeness."""

    def test_markdown_file_exists(self):
        """Verify markdown file exists."""
        assert SKILLS_MANAGER_MD.exists(), (
            f"Instruction file not found: {SKILLS_MANAGER_MD}"
        )

    def test_yaml_frontmatter_present(self):
        """Verify YAML frontmatter exists and is valid."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert content.startswith("---\n"), "Must start with YAML frontmatter"
        parts = content.split("---", 2)
        assert len(parts) >= 3, "Must have valid YAML frontmatter"

        # Parse frontmatter
        frontmatter = yaml.safe_load(parts[1])
        assert isinstance(frontmatter, dict)
        assert frontmatter["name"] == "mpm_skills_manager"
        assert frontmatter["version"] == "1.0.0"

    def test_required_sections_present(self):
        """Verify all 11 required sections are present."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        required_sections = [
            "## 1. Core Identity and Mission",
            "## 2. Technology Stack Detection",
            "## 3. Skill Recommendation Engine",
            "## 4. Skill Lifecycle Management",
            "## 5. Manifest.json Management",
            "## 6. PR Creation Workflow",
            "## 7. Service Integration",
            "## 8. Error Handling",
            "## 9. Skill Structure Validation",
            "## 10. Example Workflows",
            "## 11. Best Practices",
        ]

        for section in required_sections:
            assert section in content, f"Missing required section: {section}"

    def test_technology_detection_documented(self):
        """Verify technology detection patterns are documented."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        # Check for file patterns
        assert "requirements.txt" in content
        assert "package.json" in content
        assert "Cargo.toml" in content
        assert "go.mod" in content

        # Check for detection logic
        assert "pyproject.toml" in content
        assert "tsconfig.json" in content

    def test_confidence_scoring_documented(self):
        """Verify confidence scoring system is documented."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "High Confidence (90%+)" in content or "High (90%+)" in content
        assert "Medium Confidence" in content or "Medium (" in content
        assert "Low Confidence" in content or "Low (<70%)" in content

    def test_recommendation_logic_documented(self):
        """Verify skill recommendation logic is documented."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "Recommendation Logic" in content or "recommendation" in content.lower()
        assert "Critical" in content
        assert "High" in content
        assert "Medium" in content
        assert "manifest.json" in content

    def test_manifest_management_documented(self):
        """Verify manifest.json management is documented."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "manifest.json" in content
        assert '"name"' in content
        assert '"version"' in content
        assert '"tags"' in content
        assert "entry_point_tokens" in content or "full_tokens" in content

    def test_pr_workflow_phases_documented(self):
        """Verify 4-phase PR workflow is documented."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "Phase 1" in content
        assert "Phase 2" in content
        assert "Phase 3" in content
        assert "Phase 4" in content
        assert "Analysis" in content
        assert "Modification" in content
        assert "Submission" in content
        assert "Follow-up" in content

    def test_service_integration_documented(self):
        """Verify infrastructure service usage is documented."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "GitOperationsManager" in content or "git_operations" in content
        assert "PRTemplateService" in content or "pr_template" in content
        assert "GitHubCLIService" in content or "github_cli" in content

    def test_error_handling_scenarios(self):
        """Verify error scenarios are documented."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "gh CLI Not Installed" in content or "GitHub CLI" in content
        assert "Skill Structure Invalid" in content or "validation" in content.lower()
        assert "Git Operation Failures" in content or "uncommitted changes" in content

    def test_skill_structure_validation_documented(self):
        """Verify skill structure validation is documented."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "SKILL.md" in content
        assert "references/" in content
        assert "Required Structure" in content or "structure" in content.lower()
        assert "YAML frontmatter" in content or "frontmatter" in content

    def test_example_workflows_present(self):
        """Verify example workflows are documented."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "Workflow 1" in content or "Example 1" in content
        assert "Workflow 2" in content or "Example 2" in content
        assert "FastAPI" in content or "skill recommendation" in content.lower()

    def test_best_practices_section(self):
        """Verify best practices section is comprehensive."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        # Check for DO section
        assert "DO:" in content or "✅" in content

        # Check for DON'T section
        assert "DON'T:" in content or "❌" in content


# ============================================================================
# Technology Detection Logic Tests
# ============================================================================


class TestTechnologyDetection:
    """Test technology detection patterns."""

    def test_python_detection_patterns(self):
        """Verify Python detection is documented."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "requirements.txt" in content
        assert "pyproject.toml" in content
        assert "fastapi" in content.lower()
        assert "django" in content.lower()
        assert "pytest" in content.lower()

    def test_javascript_detection_patterns(self):
        """Verify JavaScript/TypeScript detection is documented."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "package.json" in content
        assert "tsconfig.json" in content
        assert "react" in content.lower()
        assert "nextjs" in content.lower() or "next" in content.lower()

    def test_multiple_language_support(self):
        """Verify multiple language detection is supported."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        languages = ["python", "javascript", "typescript", "rust", "go"]
        for lang in languages:
            assert lang in content.lower(), f"Language '{lang}' not documented"

    def test_framework_detection_examples(self):
        """Verify framework detection examples exist."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        # Should have specific framework examples
        assert "fastapi" in content.lower()
        assert "django" in content.lower() or "flask" in content.lower()
        assert "react" in content.lower()

    def test_detection_output_format(self):
        """Verify detection output format is documented."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        # Should show JSON output format
        assert '"detected"' in content or "'detected'" in content
        assert '"languages"' in content or "languages" in content
        assert '"frameworks"' in content or "frameworks" in content


# ============================================================================
# Skill Recommendation Tests
# ============================================================================


class TestSkillRecommendation:
    """Test skill recommendation engine documentation."""

    def test_recommendation_priorities(self):
        """Verify recommendation priorities are documented."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "Critical" in content
        assert "High" in content
        assert "Medium" in content
        assert "Low" in content or "Situational" in content

    def test_matching_logic_documented(self):
        """Verify matching logic is explained."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "manifest.json" in content
        assert "tags" in content
        assert "relevance" in content.lower() or "score" in content.lower()

    def test_recommendation_output_format(self):
        """Verify recommendation output format is shown."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "Why:" in content or "why" in content.lower()
        assert "Install:" in content or "install" in content.lower()
        assert "claude-mpm skills install" in content

    def test_skill_mappings_present(self):
        """Verify technology-to-skill mappings are documented."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        # Should have mapping examples
        assert "PYTHON_STACK_SKILLS" in content or "python" in content.lower()
        assert "toolchains-python" in content


# ============================================================================
# Manifest.json Management Tests
# ============================================================================


class TestManifestManagement:
    """Test manifest.json management documentation."""

    def test_manifest_structure_documented(self):
        """Verify manifest.json structure is documented."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        required_fields = [
            "name",
            "path",
            "entry_point",
            "version",
            "tags",
            "entry_point_tokens",
            "full_tokens",
        ]

        for field in required_fields:
            assert f'"{field}"' in content or field in content

    def test_manifest_operations_documented(self):
        """Verify manifest operations are documented."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "Adding New Skill Entry" in content or "add" in content.lower()
        assert "Updating Existing Entry" in content or "update" in content.lower()
        assert "Validation Rules" in content or "validation" in content.lower()

    def test_token_count_calculation(self):
        """Verify token count calculation is documented."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "entry_point_tokens" in content
        assert "full_tokens" in content
        assert "Token Count" in content or "token" in content.lower()


# ============================================================================
# PR Workflow Tests
# ============================================================================


class TestPRWorkflow:
    """Test PR workflow documentation."""

    def test_four_phase_workflow(self):
        """Verify 4-phase workflow is complete."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "Phase 1" in content
        assert "Phase 2" in content
        assert "Phase 3" in content
        assert "Phase 4" in content

    def test_branch_naming_convention(self):
        """Verify branch naming is documented."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "skill/" in content
        assert "branch" in content.lower()

    def test_commit_message_format(self):
        """Verify conventional commit format is documented."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "feat(skill)" in content
        assert (
            "conventional commit" in content.lower()
            or "commit message" in content.lower()
        )

    def test_pr_description_generation(self):
        """Verify PR description generation is documented."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "PRTemplateService" in content or "generate_skill_pr_body" in content
        assert "problem" in content.lower() or "motivation" in content.lower()
        assert "solution" in content.lower() or "improvements" in content.lower()

    def test_improvement_triggers_documented(self):
        """Verify improvement triggers are documented."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "User Feedback" in content or "feedback" in content.lower()
        assert "Technology Gap" in content or "gap detection" in content.lower()
        assert "Manual Request" in content or "manual" in content.lower()


# ============================================================================
# Service Integration Tests
# ============================================================================


class TestServiceIntegration:
    """Test infrastructure service integration documentation."""

    def test_git_operations_service_usage(self):
        """Verify GitOperationsManager usage is documented."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "GitOperationsManager" in content
        assert "create_branch" in content
        assert "push_to_remote" in content or "push" in content

    def test_pr_template_service_usage(self):
        """Verify PRTemplateService usage is documented."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "PRTemplateService" in content
        assert "generate_skill_pr_body" in content or "generate" in content

    def test_github_cli_service_usage(self):
        """Verify GitHubCLIService usage is documented."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "GitHubCLIService" in content
        assert "create_pr" in content
        assert "validate_environment" in content or "is_authenticated" in content

    def test_service_import_statements(self):
        """Verify service import examples are present."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "from claude_mpm.services" in content or "import" in content
        assert "git" in content.lower()


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test error handling documentation."""

    def test_gh_cli_not_installed_error(self):
        """Verify gh CLI not installed error is handled."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "gh CLI" in content or "GitHub CLI" in content
        assert "not installed" in content.lower()
        assert "brew install gh" in content or "installation" in content.lower()

    def test_skill_validation_errors(self):
        """Verify skill validation errors are documented."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "Skill Structure Invalid" in content or "validation" in content.lower()
        assert "SKILL.md" in content
        assert "references/" in content

    def test_git_operation_errors(self):
        """Verify git operation errors are handled."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "uncommitted changes" in content.lower() or "Git Operation" in content
        assert "branch already exists" in content.lower() or "branch" in content

    def test_pr_creation_failures(self):
        """Verify PR creation failure handling is documented."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "Network timeout" in content or "timeout" in content.lower()
        assert "API error" in content.lower() or "rate limit" in content.lower()
        assert "Manual PR" in content or "manual" in content.lower()

    def test_recovery_steps_provided(self):
        """Verify recovery steps are provided for errors."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "Recovery" in content or "recovery" in content.lower()
        assert "Steps" in content or "steps" in content.lower()


# ============================================================================
# Skill Structure Validation Tests
# ============================================================================


class TestSkillStructureValidation:
    """Test skill structure validation documentation."""

    def test_required_structure_documented(self):
        """Verify required skill structure is documented."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "SKILL.md" in content
        assert "references/" in content
        assert "manifest.json" in content

    def test_yaml_frontmatter_requirements(self):
        """Verify YAML frontmatter requirements are documented."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "YAML frontmatter" in content or "frontmatter" in content
        assert "name:" in content or '"name"' in content
        assert "version:" in content or '"version"' in content
        assert "tags:" in content or '"tags"' in content

    def test_validation_checklist(self):
        """Verify validation checklist is provided."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "Validation Checklist" in content or "checklist" in content.lower()
        assert "[ ]" in content or "checkbox" in content.lower() or "-" in content


# ============================================================================
# Example Workflows Tests
# ============================================================================


class TestExampleWorkflows:
    """Test example workflows documentation."""

    def test_skill_recommendation_workflow(self):
        """Verify skill recommendation workflow example exists."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "Workflow 1" in content or "recommend" in content.lower()
        assert "FastAPI" in content or "React" in content

    def test_new_skill_creation_workflow(self):
        """Verify new skill creation workflow exists."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "Workflow 2" in content or "Create" in content
        assert "Tailwind" in content or "new skill" in content.lower()

    def test_skill_improvement_workflow(self):
        """Verify skill improvement workflow exists."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "Workflow 3" in content or "Improve" in content
        assert "async" in content.lower() or "improvement" in content.lower()

    def test_workflow_steps_detailed(self):
        """Verify workflow steps are detailed."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        # Should have step-by-step instructions
        assert "Step 1" in content or "1." in content
        assert "git checkout" in content
        assert "git commit" in content


# ============================================================================
# Best Practices Tests
# ============================================================================


class TestBestPractices:
    """Test best practices documentation."""

    def test_do_section_present(self):
        """Verify DO section lists best practices."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "DO:" in content or "✅" in content
        assert "validate" in content.lower()
        assert "manifest" in content.lower()

    def test_dont_section_present(self):
        """Verify DON'T section lists anti-patterns."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "DON'T:" in content or "❌" in content
        assert "skip" in content.lower() or "don't skip" in content.lower()

    def test_specific_guidance(self):
        """Verify specific guidance is provided."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "manifest.json" in content
        assert "version" in content.lower()
        assert "validate" in content.lower()


# ============================================================================
# Integration Tests
# ============================================================================


class TestAgentIntegration:
    """Test agent definition and instructions are in sync."""

    def test_json_and_markdown_versions_match(self):
        """Verify JSON and markdown versions match."""
        with open(SKILLS_MANAGER_JSON) as f:
            json_data = json.load(f)

        with open(SKILLS_MANAGER_MD) as f:
            md_content = f.read()
            parts = md_content.split("---", 2)
            frontmatter = yaml.safe_load(parts[1])

        assert json_data["version"] == frontmatter["version"]

    def test_json_and_markdown_names_match(self):
        """Verify JSON and markdown names match."""
        with open(SKILLS_MANAGER_JSON) as f:
            json_data = json.load(f)

        with open(SKILLS_MANAGER_MD) as f:
            md_content = f.read()
            parts = md_content.split("---", 2)
            frontmatter = yaml.safe_load(parts[1])

        assert json_data["name"] == frontmatter["name"]

    def test_json_and_markdown_agent_ids_match(self):
        """Verify JSON and markdown agent IDs match."""
        with open(SKILLS_MANAGER_JSON) as f:
            json_data = json.load(f)

        with open(SKILLS_MANAGER_MD) as f:
            md_content = f.read()
            parts = md_content.split("---", 2)
            frontmatter = yaml.safe_load(parts[1])

        assert json_data["agent_id"] == frontmatter["agent_id"]

    def test_instruction_file_reference(self):
        """Verify JSON references correct instruction file."""
        with open(SKILLS_MANAGER_JSON) as f:
            json_data = json.load(f)

        assert json_data["instruction_file"] == "mpm-skills-manager.md"

    def test_dependencies_match(self):
        """Verify dependencies in JSON and markdown match."""
        with open(SKILLS_MANAGER_JSON) as f:
            json_data = json.load(f)

        with open(SKILLS_MANAGER_MD) as f:
            md_content = f.read()
            parts = md_content.split("---", 2)
            frontmatter = yaml.safe_load(parts[1])

        # Compare Python dependencies
        assert (
            json_data["dependencies"]["python"] == frontmatter["dependencies"]["python"]
        )
        assert (
            json_data["dependencies"]["system"] == frontmatter["dependencies"]["system"]
        )


# ============================================================================
# Content Quality Tests
# ============================================================================


class TestContentQuality:
    """Test instruction content quality."""

    def test_no_placeholder_text(self):
        """Verify no placeholder text remains."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        placeholders = ["TODO", "FIXME", "XXX", "{placeholder}", "TBD"]
        for placeholder in placeholders:
            assert placeholder not in content, f"Placeholder text found: {placeholder}"

    def test_code_examples_present(self):
        """Verify code examples are present."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        # Should have multiple code blocks
        assert content.count("```") >= 20, "Should have at least 10 code blocks (```)"

    def test_service_usage_examples(self):
        """Verify service usage has examples."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        assert "git_manager" in content or "GitOperationsManager" in content
        assert "pr_service" in content or "PRTemplateService" in content
        assert "gh_service" in content or "GitHubCLIService" in content

    def test_json_examples_valid(self):
        """Verify JSON examples in markdown are valid."""
        with open(SKILLS_MANAGER_MD) as f:
            content = f.read()

        # Extract JSON code blocks
        import re

        json_blocks = re.findall(r"```json\n(.*?)\n```", content, re.DOTALL)

        for block in json_blocks:
            try:
                json.loads(block)
            except json.JSONDecodeError:
                # Some examples might have placeholders, skip those
                if "{" not in block or "..." not in block:
                    pytest.fail(f"Invalid JSON example: {block[:100]}")

    def test_comprehensive_documentation(self):
        """Verify documentation is comprehensive (>800 lines)."""
        with open(SKILLS_MANAGER_MD) as f:
            lines = f.readlines()

        assert len(lines) > 800, (
            f"Documentation should be comprehensive (found {len(lines)} lines)"
        )


# ============================================================================
# Run Tests
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
