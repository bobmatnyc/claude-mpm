"""
Tests for SkillsDeployer service.

WHY: Comprehensive testing of GitHub skills deployment functionality to ensure
reliable downloads, filtering, deployment, and error handling.

COVERAGE:
- GitHub download and parsing
- Toolchain and category filtering
- Deployment to ~/.claude/skills/
- Claude Code restart detection
- Skill removal and cleanup
- Error handling and edge cases
"""

import json
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from claude_mpm.services.skills_deployer import SkillsDeployerService


@pytest.fixture
def mock_manifest():
    """Mock skills manifest with nested structure (matching real GitHub)."""
    return {
        "version": "1.0.0",
        "skills": {
            "universal": [
                {
                    "name": "test-driven-development",
                    "description": "RED-GREEN-REFACTOR cycle",
                    "category": "testing",
                    "path": "universal/testing/test-driven-development",
                },
            ],
            "toolchains": {
                "python": [
                    {
                        "name": "test-skill-python",
                        "description": "Python testing skill",
                        "toolchain": ["python"],
                        "category": "testing",
                        "path": "toolchains/python/test-skill-python",
                    }
                ],
                "javascript": [
                    {
                        "name": "debug-skill-javascript",
                        "description": "JavaScript debugging skill",
                        "toolchain": ["javascript", "typescript"],
                        "category": "debugging",
                        "path": "toolchains/javascript/debug-skill-javascript",
                    }
                ],
                "rust": [
                    {
                        "name": "web-skill-rust",
                        "description": "Rust web skill",
                        "toolchain": ["rust"],
                        "category": "web",
                        "path": "toolchains/rust/web-skill-rust",
                    }
                ],
            },
        },
    }


@pytest.fixture
def mock_github_repo(tmp_path, mock_manifest):
    """Create a mock GitHub repository structure."""
    # Create repo directory structure
    repo_dir = tmp_path / "claude-mpm-skills-main"
    repo_dir.mkdir()

    # Create manifest
    manifest_path = repo_dir / "manifest.json"
    manifest_path.write_text(json.dumps(mock_manifest))

    # Create skills directory structure
    skills_dir = repo_dir / "skills"
    skills_dir.mkdir()

    # Flatten skills from nested structure for directory creation
    all_skills = []
    skills_data = mock_manifest["skills"]

    # Add universal skills
    if "universal" in skills_data:
        all_skills.extend(skills_data["universal"])

    # Add toolchain skills
    if "toolchains" in skills_data:
        for toolchain_skills in skills_data["toolchains"].values():
            all_skills.extend(toolchain_skills)

    # Create test skills
    for skill in all_skills:
        category_dir = skills_dir / skill["category"]
        category_dir.mkdir(exist_ok=True)

        skill_dir = category_dir / skill["name"]
        skill_dir.mkdir()

        # Create SKILL.md
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(
            f"---\nname: {skill['name']}\n"
            f"description: {skill['description']}\n"
            f"version: 1.0.0\n---\n\n# {skill['name']}\n"
        )

    # Create ZIP archive
    zip_path = tmp_path / "skills.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for file in repo_dir.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(tmp_path)
                zf.write(file, arcname)

    return {"zip_path": zip_path, "repo_dir": repo_dir, "manifest": mock_manifest}


@pytest.fixture
def deployer(tmp_path):
    """Create SkillsDeployer with temporary skills directory."""
    deployer = SkillsDeployerService()

    # Override CLAUDE_SKILLS_DIR to use temp directory
    deployer.CLAUDE_SKILLS_DIR = tmp_path / "claude_skills"
    deployer.CLAUDE_SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    return deployer


class TestSkillsDeployerInit:
    """Test SkillsDeployer initialization."""

    def test_init_default(self):
        """Test default initialization."""
        deployer = SkillsDeployerService()

        assert deployer.repo_url == SkillsDeployerService.DEFAULT_REPO_URL
        assert Path.home() / ".claude" / "skills" == deployer.CLAUDE_SKILLS_DIR
        assert deployer.toolchain_analyzer is None

    def test_init_custom_repo(self):
        """Test initialization with custom repository."""
        custom_repo = "https://github.com/custom/repo"
        deployer = SkillsDeployerService(repo_url=custom_repo)

        assert deployer.repo_url == custom_repo

    def test_init_with_toolchain_analyzer(self):
        """Test initialization with toolchain analyzer."""
        mock_analyzer = Mock()
        deployer = SkillsDeployerService(toolchain_analyzer=mock_analyzer)

        assert deployer.toolchain_analyzer == mock_analyzer


class TestGitHubDownload:
    """Test GitHub repository download functionality."""

    @patch("urllib.request.urlopen")
    def test_download_success(self, mock_urlopen, deployer, mock_github_repo):
        """Test successful GitHub download."""
        # Mock URL open to return ZIP file
        mock_response = Mock()
        mock_response.read.return_value = mock_github_repo["zip_path"].read_bytes()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = deployer._download_from_github()

        assert "temp_dir" in result
        assert "manifest" in result
        assert "repo_dir" in result
        assert result["manifest"]["version"] == "1.0.0"
        # Verify manifest has skills (now nested structure)
        assert "skills" in result["manifest"]
        assert isinstance(result["manifest"]["skills"], dict)

        # Cleanup
        deployer._cleanup(result["temp_dir"])

    @patch("urllib.request.urlopen")
    def test_download_no_manifest(self, mock_urlopen, deployer, tmp_path):
        """Test download with missing manifest."""
        # Create ZIP without manifest
        zip_path = tmp_path / "no_manifest.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("test-repo-main/README.md", "Test content")

        mock_response = Mock()
        mock_response.read.return_value = zip_path.read_bytes()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        with pytest.raises(Exception, match=r"manifest.json not found"):
            deployer._download_from_github()

    @patch("urllib.request.urlopen")
    def test_download_network_error(self, mock_urlopen, deployer):
        """Test download with network error."""
        mock_urlopen.side_effect = Exception("Network error")

        with pytest.raises(Exception, match="Network error"):
            deployer._download_from_github()


class TestSkillFiltering:
    """Test skill filtering by toolchain and categories."""

    def test_filter_by_toolchain_single(self, deployer, mock_manifest):
        """Test filtering by single toolchain."""
        # Flatten manifest first
        skills = deployer._flatten_manifest_skills(mock_manifest)

        result = deployer._filter_skills(skills, toolchain=["python"], categories=None)

        assert len(result) == 1
        assert result[0]["name"] == "test-skill-python"

    def test_filter_by_toolchain_multiple(self, deployer, mock_manifest):
        """Test filtering by multiple toolchains."""
        # Flatten manifest first
        skills = deployer._flatten_manifest_skills(mock_manifest)

        result = deployer._filter_skills(
            skills, toolchain=["python", "rust"], categories=None
        )

        assert len(result) == 2
        assert any(s["name"] == "test-skill-python" for s in result)
        assert any(s["name"] == "web-skill-rust" for s in result)

    def test_filter_by_category(self, deployer, mock_manifest):
        """Test filtering by category."""
        # Flatten manifest first
        skills = deployer._flatten_manifest_skills(mock_manifest)

        result = deployer._filter_skills(skills, toolchain=None, categories=["testing"])

        # Now we have 2 testing skills: 1 universal + 1 python
        assert len(result) == 2
        assert all(s["category"] == "testing" for s in result)

    def test_filter_by_toolchain_and_category(self, deployer, mock_manifest):
        """Test filtering by both toolchain and category."""
        # Flatten manifest first
        skills = deployer._flatten_manifest_skills(mock_manifest)

        result = deployer._filter_skills(
            skills, toolchain=["javascript"], categories=["debugging"]
        )

        assert len(result) == 1
        assert result[0]["name"] == "debug-skill-javascript"

    def test_filter_no_match(self, deployer, mock_manifest):
        """Test filtering with no matches."""
        # Flatten manifest first
        skills = deployer._flatten_manifest_skills(mock_manifest)

        result = deployer._filter_skills(skills, toolchain=["go"], categories=None)

        assert len(result) == 0

    def test_filter_none_returns_all(self, deployer, mock_manifest):
        """Test that None filters return all skills."""
        # Need to flatten manifest first
        skills = deployer._flatten_manifest_skills(mock_manifest)

        result = deployer._filter_skills(skills, toolchain=None, categories=None)

        # Now we have 4 skills: 1 universal + 3 toolchain-specific
        assert len(result) == 4


class TestSkillDeployment:
    """Test skill deployment to Claude skills directory."""

    @patch("urllib.request.urlopen")
    def test_deploy_single_skill(self, mock_urlopen, deployer, mock_github_repo):
        """Test deploying a single filtered skill."""
        # Setup mock download
        mock_response = Mock()
        mock_response.read.return_value = mock_github_repo["zip_path"].read_bytes()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = deployer.deploy_skills(toolchain=["python"], categories=None)

        assert result["deployed_count"] == 1
        assert "test-skill-python" in result["deployed_skills"]
        assert result["skipped_count"] == 0
        assert len(result["errors"]) == 0

        # Verify skill was deployed
        deployed_path = deployer.CLAUDE_SKILLS_DIR / "test-skill-python"
        assert deployed_path.exists()
        assert (deployed_path / "SKILL.md").exists()

    @patch("urllib.request.urlopen")
    def test_deploy_all_skills(self, mock_urlopen, deployer, mock_github_repo):
        """Test deploying all skills without filtering."""
        mock_response = Mock()
        mock_response.read.return_value = mock_github_repo["zip_path"].read_bytes()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Deploy all skills (no filtering)
        result = deployer.deploy_skills(toolchain=None, categories=None, force=True)

        # Now we have 4 skills: 1 universal + 3 toolchain-specific
        assert result["deployed_count"] == 4
        assert len(result["errors"]) == 0

    @patch("urllib.request.urlopen")
    def test_deploy_skip_existing(self, mock_urlopen, deployer, mock_github_repo):
        """Test that existing skills are skipped unless force=True."""
        mock_response = Mock()
        mock_response.read.return_value = mock_github_repo["zip_path"].read_bytes()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # First deployment
        result1 = deployer.deploy_skills(toolchain=["python"], force=False)
        assert result1["deployed_count"] == 1

        # Second deployment (should skip)
        result2 = deployer.deploy_skills(toolchain=["python"], force=False)
        assert result2["deployed_count"] == 0
        assert result2["skipped_count"] == 1

    @patch("urllib.request.urlopen")
    def test_deploy_force_overwrite(self, mock_urlopen, deployer, mock_github_repo):
        """Test force deployment overwrites existing skills."""
        mock_response = Mock()
        mock_response.read.return_value = mock_github_repo["zip_path"].read_bytes()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # First deployment
        deployer.deploy_skills(toolchain=["python"], force=False)

        # Force redeployment
        result = deployer.deploy_skills(toolchain=["python"], force=True)

        assert result["deployed_count"] == 1
        assert result["skipped_count"] == 0

    @patch("urllib.request.urlopen")
    def test_deploy_download_error(self, mock_urlopen, deployer):
        """Test deployment with download error."""
        mock_urlopen.side_effect = Exception("Network error")

        result = deployer.deploy_skills()

        assert result["deployed_count"] == 0
        assert len(result["errors"]) > 0
        assert "Download failed" in result["errors"][0]


class TestClaudeCodeDetection:
    """Test Claude Code process detection."""

    @patch("subprocess.run")
    def test_claude_code_running_macos(self, mock_run, deployer):
        """Test detecting Claude Code on macOS."""
        mock_result = Mock()
        mock_result.stdout = "user  1234  Claude Code\n"
        mock_run.return_value = mock_result

        with patch("platform.system", return_value="Darwin"):
            assert deployer._is_claude_code_running() is True

    @patch("subprocess.run")
    def test_claude_code_not_running(self, mock_run, deployer):
        """Test when Claude Code is not running."""
        mock_result = Mock()
        mock_result.stdout = "user  1234  python\nuser  5678  vim\n"
        mock_run.return_value = mock_result

        with patch("platform.system", return_value="Darwin"):
            assert deployer._is_claude_code_running() is False

    @patch("subprocess.run")
    def test_claude_code_check_error(self, mock_run, deployer):
        """Test error handling in process detection."""
        mock_run.side_effect = Exception("Process check failed")

        # Should return False on error, not raise
        assert deployer._is_claude_code_running() is False


class TestListAvailableSkills:
    """Test listing available skills from GitHub."""

    @patch("urllib.request.urlopen")
    def test_list_available_success(self, mock_urlopen, deployer, mock_github_repo):
        """Test successful listing of available skills."""
        mock_response = Mock()
        mock_response.read.return_value = mock_github_repo["zip_path"].read_bytes()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = deployer.list_available_skills()

        # Now we have 4 skills: 1 universal + 3 toolchain-specific
        assert result["total_skills"] == 4
        assert len(result["by_category"]) == 3  # testing, debugging, web
        # Multiple toolchains: python, javascript, typescript, rust
        assert "testing" in result["by_category"]
        assert "python" in result["by_toolchain"]

    @patch("urllib.request.urlopen")
    def test_list_available_error(self, mock_urlopen, deployer):
        """Test list available with error."""
        mock_urlopen.side_effect = Exception("Network error")

        result = deployer.list_available_skills()

        assert result["total_skills"] == 0
        assert "error" in result


class TestCheckDeployedSkills:
    """Test checking currently deployed skills."""

    def test_check_deployed_empty(self, deployer):
        """Test checking when no skills are deployed."""
        result = deployer.check_deployed_skills()

        assert result["deployed_count"] == 0
        assert len(result["skills"]) == 0

    @patch("urllib.request.urlopen")
    def test_check_deployed_with_skills(self, mock_urlopen, deployer, mock_github_repo):
        """Test checking deployed skills."""
        # Deploy some skills first
        mock_response = Mock()
        mock_response.read.return_value = mock_github_repo["zip_path"].read_bytes()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        deployer.deploy_skills(toolchain=["python"])

        # Check deployed
        result = deployer.check_deployed_skills()

        assert result["deployed_count"] == 1
        assert len(result["skills"]) == 1
        assert result["skills"][0]["name"] == "test-skill-python"


class TestRemoveSkills:
    """Test skill removal functionality."""

    @patch("urllib.request.urlopen")
    def test_remove_specific_skill(self, mock_urlopen, deployer, mock_github_repo):
        """Test removing a specific skill."""
        # Deploy skills first
        mock_response = Mock()
        mock_response.read.return_value = mock_github_repo["zip_path"].read_bytes()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        deployer.deploy_skills(toolchain=["python"])

        # Remove skill
        result = deployer.remove_skills(["test-skill-python"])

        assert result["removed_count"] == 1
        assert "test-skill-python" in result["removed_skills"]
        assert len(result["errors"]) == 0

        # Verify removal
        deployed_path = deployer.CLAUDE_SKILLS_DIR / "test-skill-python"
        assert not deployed_path.exists()

    @patch("urllib.request.urlopen")
    def test_remove_all_skills(self, mock_urlopen, deployer, mock_github_repo):
        """Test removing all skills."""
        # Deploy skills first
        mock_response = Mock()
        mock_response.read.return_value = mock_github_repo["zip_path"].read_bytes()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        deployer.deploy_skills(toolchain=["python", "rust"], force=True)

        # Remove all
        result = deployer.remove_skills(None)  # None = remove all

        assert result["removed_count"] == 2
        assert len(result["errors"]) == 0

    def test_remove_nonexistent_skill(self, deployer):
        """Test removing a skill that doesn't exist."""
        result = deployer.remove_skills(["nonexistent-skill"])

        assert result["removed_count"] == 0
        assert len(result["errors"]) == 1
        assert "not found" in result["errors"][0].lower()


class TestSecurityValidation:
    """Test security path validation."""

    def test_validate_safe_path_valid(self, deployer, tmp_path):
        """Test valid path within base directory."""
        base = tmp_path / "base"
        base.mkdir()
        target = base / "subdir" / "file.txt"

        assert deployer._validate_safe_path(base, target) is True

    def test_validate_safe_path_traversal(self, deployer, tmp_path):
        """Test path traversal attempt is rejected."""
        base = tmp_path / "base"
        base.mkdir()
        target = tmp_path / "outside" / "file.txt"

        assert deployer._validate_safe_path(base, target) is False

    def test_validate_safe_path_symlink_escape(self, deployer, tmp_path):
        """Test symlink escape attempt is rejected."""
        base = tmp_path / "base"
        base.mkdir()

        outside = tmp_path / "outside"
        outside.mkdir()

        # Create symlink trying to escape
        link = base / "escape_link"
        link.symlink_to(outside)

        target = link / "file.txt"

        # Should be rejected as it resolves outside base
        assert deployer._validate_safe_path(base, target) is False


class TestCleanup:
    """Test temporary file cleanup."""

    def test_cleanup_removes_directory(self, deployer, tmp_path):
        """Test cleanup removes temporary directory."""
        temp_dir = tmp_path / "temp_test"
        temp_dir.mkdir()
        (temp_dir / "test.txt").write_text("test")

        assert temp_dir.exists()

        deployer._cleanup(temp_dir)

        assert not temp_dir.exists()

    def test_cleanup_nonexistent_directory(self, deployer, tmp_path):
        """Test cleanup handles nonexistent directory gracefully."""
        temp_dir = tmp_path / "nonexistent"

        # Should not raise exception
        deployer._cleanup(temp_dir)


class TestManifestFlattening:
    """Test manifest structure flattening (legacy vs. nested)."""

    def test_flatten_manifest_legacy_flat(self, deployer):
        """Test flattening legacy flat list manifest."""
        legacy_manifest = {
            "skills": [
                {"name": "skill1", "category": "test"},
                {"name": "skill2", "category": "test"},
            ]
        }

        skills = deployer._flatten_manifest_skills(legacy_manifest)

        assert len(skills) == 2
        assert skills[0]["name"] == "skill1"
        assert skills[1]["name"] == "skill2"

    def test_flatten_manifest_nested_structure(self, deployer):
        """Test flattening new nested dict manifest."""
        nested_manifest = {
            "skills": {
                "universal": [{"name": "universal1", "category": "test"}],
                "toolchains": {
                    "python": [{"name": "python1", "toolchain": ["python"]}],
                    "javascript": [{"name": "js1", "toolchain": ["javascript"]}],
                },
            }
        }

        skills = deployer._flatten_manifest_skills(nested_manifest)

        assert len(skills) == 3
        assert any(s["name"] == "universal1" for s in skills)
        assert any(s["name"] == "python1" for s in skills)
        assert any(s["name"] == "js1" for s in skills)

    def test_flatten_manifest_invalid_structure(self, deployer):
        """Test that invalid manifest raises ValueError."""
        invalid_manifest = {"skills": "invalid string"}

        with pytest.raises(ValueError, match="must be a list or dict"):
            deployer._flatten_manifest_skills(invalid_manifest)

    def test_flatten_manifest_empty_dict(self, deployer):
        """Test flattening empty nested dict."""
        empty_manifest = {"skills": {}}

        skills = deployer._flatten_manifest_skills(empty_manifest)

        assert len(skills) == 0

    def test_flatten_manifest_partial_nested(self, deployer):
        """Test flattening nested dict with only universal skills."""
        partial_manifest = {
            "skills": {
                "universal": [
                    {"name": "universal1", "category": "test"},
                    {"name": "universal2", "category": "test"},
                ]
            }
        }

        skills = deployer._flatten_manifest_skills(partial_manifest)

        assert len(skills) == 2
        assert all(s["name"].startswith("universal") for s in skills)

    def test_flatten_manifest_partial_toolchains_only(self, deployer):
        """Test flattening nested dict with only toolchain skills."""
        toolchains_only = {
            "skills": {
                "toolchains": {
                    "python": [{"name": "python1", "toolchain": ["python"]}],
                    "rust": [{"name": "rust1", "toolchain": ["rust"]}],
                }
            }
        }

        skills = deployer._flatten_manifest_skills(toolchains_only)

        assert len(skills) == 2
        skill_names = [s["name"] for s in skills]
        assert "python1" in skill_names
        assert "rust1" in skill_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
