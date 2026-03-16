"""Tests for DeploymentReconciler filename normalization through deploy_agent_file().

Verifies that _deploy_agent() and _deploy_skill() use deploy_agent_file()
instead of raw shutil.copy2, ensuring filename normalization, frontmatter
injection, and legacy cleanup are applied during reconciliation deployment.

Regression guard for: https://github.com/bobmatnyc/claude-mpm/issues/F1
"""

import inspect
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_mpm.services.agents.deployment.deployment_reconciler import (
    DeploymentReconciler,
)


def _create_agent_file(
    directory: Path, filename: str, name: str, author: str = "claude-mpm"
) -> Path:
    """Create a minimal agent markdown file with valid frontmatter.

    Args:
        directory: Directory to create the file in.
        filename: Filename for the agent file (e.g., "tmux-agent.md").
        name: Display name for the agent (e.g., "Tmux Agent").
        author: Author field in frontmatter (default: "claude-mpm").

    Returns:
        Path to the created file.
    """
    directory.mkdir(parents=True, exist_ok=True)
    file_path = directory / filename
    content = f"""---
name: {name}
author: {author}
---
# {name}

This is the {name} agent.
"""
    file_path.write_text(content, encoding="utf-8")
    return file_path


def _create_reconciler() -> DeploymentReconciler:
    """Create a DeploymentReconciler with mocked config and path_manager."""
    with patch(
        "claude_mpm.services.agents.deployment.deployment_reconciler.get_path_manager"
    ):
        with patch(
            "claude_mpm.services.agents.deployment.deployment_reconciler.UnifiedConfig"
        ):
            reconciler = DeploymentReconciler.__new__(DeploymentReconciler)
            reconciler.config = MagicMock()
            reconciler.path_manager = MagicMock()
            return reconciler


class TestDeployAgentNormalizesFilename:
    """Verify _deploy_agent uses deploy_agent_file for proper normalization."""

    def test_deploy_agent_normalizes_agent_suffix(self, tmp_path: Path) -> None:
        """Agent file with '-agent' suffix should be deployed without the suffix.

        tmux-agent.md -> tmux.md (the -agent suffix is stripped by normalize_deployment_filename)
        """
        cache_dir = tmp_path / "cache"
        deploy_dir = tmp_path / "deploy"

        _create_agent_file(cache_dir, "tmux-agent.md", "Tmux Agent")

        reconciler = _create_reconciler()
        reconciler._deploy_agent("tmux-agent", cache_dir, deploy_dir)

        # The normalized filename should strip the -agent suffix
        assert (deploy_dir / "tmux.md").exists(), (
            "Expected tmux.md to exist after normalization (strip -agent suffix)"
        )
        assert not (deploy_dir / "tmux-agent.md").exists(), (
            "tmux-agent.md should NOT exist — deploy_agent_file normalizes it to tmux.md"
        )

    def test_deploy_agent_underscore_to_kebab(self, tmp_path: Path) -> None:
        """Agent file with underscores should be deployed with dashes.

        python_engineer.md -> python-engineer.md
        """
        cache_dir = tmp_path / "cache"
        deploy_dir = tmp_path / "deploy"

        _create_agent_file(cache_dir, "python_engineer.md", "Python Engineer")

        reconciler = _create_reconciler()
        reconciler._deploy_agent("python_engineer", cache_dir, deploy_dir)

        assert (deploy_dir / "python-engineer.md").exists(), (
            "Expected python-engineer.md (dashes) after normalization"
        )
        assert not (deploy_dir / "python_engineer.md").exists(), (
            "python_engineer.md (underscores) should NOT exist after normalization"
        )

    def test_deploy_agent_uppercase_to_lowercase(self, tmp_path: Path) -> None:
        """Agent file with uppercase letters should be deployed as lowercase.

        QA.md -> qa.md
        """
        cache_dir = tmp_path / "cache"
        deploy_dir = tmp_path / "deploy"

        _create_agent_file(cache_dir, "QA.md", "QA Agent")

        reconciler = _create_reconciler()
        reconciler._deploy_agent("QA", cache_dir, deploy_dir)

        assert (deploy_dir / "qa.md").exists(), (
            "Expected qa.md (lowercase) after normalization"
        )


class TestDeploySkillNormalizesFilename:
    """Verify _deploy_skill uses deploy_agent_file for proper normalization."""

    def test_deploy_skill_normalizes_filename(self, tmp_path: Path) -> None:
        """Skill file with underscores should be deployed with dashes.

        git_workflow.md -> git-workflow.md
        """
        cache_dir = tmp_path / "cache"
        deploy_dir = tmp_path / "deploy"

        _create_agent_file(cache_dir, "git_workflow.md", "Git Workflow")

        reconciler = _create_reconciler()
        reconciler._deploy_skill("git_workflow", cache_dir, deploy_dir)

        assert (deploy_dir / "git-workflow.md").exists(), (
            "Expected git-workflow.md (dashes) after normalization"
        )
        assert not (deploy_dir / "git_workflow.md").exists(), (
            "git_workflow.md (underscores) should NOT exist after normalization"
        )


class TestNoShutilCopy2InDeployMethods:
    """Regression guard: deployment methods must NOT use shutil.copy2."""

    def test_deploy_agent_does_not_use_shutil_copy(self) -> None:
        """_deploy_agent source code must not contain shutil.copy2 or shutil.copy."""
        source = inspect.getsource(DeploymentReconciler._deploy_agent)
        assert "shutil.copy2" not in source, (
            "_deploy_agent still uses shutil.copy2 — must use deploy_agent_file instead"
        )
        assert "shutil.copy" not in source, (
            "_deploy_agent still uses shutil.copy — must use deploy_agent_file instead"
        )

    def test_deploy_skill_does_not_use_shutil_copy(self) -> None:
        """_deploy_skill source code must not contain shutil.copy2 or shutil.copy."""
        source = inspect.getsource(DeploymentReconciler._deploy_skill)
        assert "shutil.copy2" not in source, (
            "_deploy_skill still uses shutil.copy2 — must use deploy_agent_file instead"
        )
        assert "shutil.copy" not in source, (
            "_deploy_skill still uses shutil.copy — must use deploy_agent_file instead"
        )

    def test_deploy_methods_call_deploy_agent_file(self) -> None:
        """Both deploy methods must call deploy_agent_file."""
        agent_source = inspect.getsource(DeploymentReconciler._deploy_agent)
        skill_source = inspect.getsource(DeploymentReconciler._deploy_skill)

        assert "deploy_agent_file" in agent_source, (
            "_deploy_agent must call deploy_agent_file"
        )
        assert "deploy_agent_file" in skill_source, (
            "_deploy_skill must call deploy_agent_file"
        )


class TestReconcilerImportCleanup:
    """Verify shutil is no longer imported in deployment_reconciler module."""

    def test_no_shutil_import(self) -> None:
        """The deployment_reconciler module should not import shutil."""
        import claude_mpm.services.agents.deployment.deployment_reconciler as mod

        source = inspect.getsource(mod)
        # Check there's no 'import shutil' statement (not in a comment or string)
        import re

        # Match 'import shutil' at the start of a line (module-level import)
        shutil_imports = re.findall(r"^import shutil", source, re.MULTILINE)
        assert len(shutil_imports) == 0, (
            "deployment_reconciler.py still imports shutil — it should be removed "
            "since deploy_agent_file replaces all shutil.copy2 usage"
        )
