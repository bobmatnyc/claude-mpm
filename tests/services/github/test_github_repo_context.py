"""Unit tests for GitHubRepoContext and GitHubSystemPromptInjector."""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from claude_mpm.services.github.repo_context import GitHubRepoContext, OpenPR
from claude_mpm.services.github.system_prompt_injector import (
    GitHubSystemPromptInjector,
)


def run_async(coro):
    """Helper to run an async coroutine in a synchronous test.

    Uses asyncio.run() to create a fresh event loop for each call, preventing
    event loop state from leaking between tests when running in parallel with
    pytest-xdist workers.
    """
    return asyncio.run(coro)


class TestParseRemoteUrl(unittest.TestCase):
    """Unit tests for _parse_remote_url static method."""

    def test_https_url_with_git_suffix(self) -> None:
        result = GitHubRepoContext._parse_remote_url(
            "https://github.com/owner/repo.git"
        )
        self.assertEqual(result, ("owner", "repo"))

    def test_https_url_without_git_suffix(self) -> None:
        result = GitHubRepoContext._parse_remote_url("https://github.com/owner/repo")
        self.assertEqual(result, ("owner", "repo"))

    def test_ssh_url_with_git_suffix(self) -> None:
        result = GitHubRepoContext._parse_remote_url("git@github.com:owner/repo.git")
        self.assertEqual(result, ("owner", "repo"))

    def test_ssh_url_without_git_suffix(self) -> None:
        result = GitHubRepoContext._parse_remote_url("git@github.com:owner/repo")
        self.assertEqual(result, ("owner", "repo"))

    def test_non_github_url_returns_none(self) -> None:
        result = GitHubRepoContext._parse_remote_url(
            "https://gitlab.com/owner/repo.git"
        )
        self.assertIsNone(result)

    def test_invalid_url_returns_none(self) -> None:
        result = GitHubRepoContext._parse_remote_url("not-a-url")
        self.assertIsNone(result)


class TestDetect(unittest.TestCase):
    """Tests for GitHubRepoContext.detect() async classmethod."""

    def test_returns_none_when_not_a_git_repo(self) -> None:
        """Non-git directories return None."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_async(GitHubRepoContext.detect(tmpdir, timeout_ms=1000))
        self.assertIsNone(result)

    def test_returns_none_on_timeout(self) -> None:
        """TimeoutError during detection returns None gracefully."""

        async def _mock_detect_impl(cwd: str):
            await asyncio.sleep(10)  # Simulate long-running detection

        with patch.object(GitHubRepoContext, "_detect_impl", _mock_detect_impl):
            result = run_async(GitHubRepoContext.detect("/tmp", timeout_ms=50))
        self.assertIsNone(result)

    def test_returns_context_for_mocked_git_repo(self) -> None:
        """When git commands succeed with github remote, returns a context object."""

        async def _mock_run(cmd, cwd):
            if "rev-parse" in cmd:
                return 0, ".git", ""
            if "get-url" in cmd:
                return 0, "https://github.com/testowner/testrepo.git\n", ""
            if "branch" in cmd and "--show-current" in cmd:
                return 0, "feature-branch\n", ""
            if "symbolic-ref" in cmd:
                return 0, "refs/remotes/origin/main\n", ""
            if "gh" in cmd:
                return 0, "[]", ""
            return 1, "", ""

        mock_identity_mgr = MagicMock()
        mock_identity_mgr.return_value.get_active_account.return_value = None

        with (
            patch(
                "claude_mpm.services.github.repo_context._run",
                side_effect=_mock_run,
            ),
            # GitHubIdentityManager is imported inside _detect_impl via
            # "from claude_mpm.services.github.identity_manager import ..."
            # so patch the class in its home module
            patch(
                "claude_mpm.services.github.identity_manager.GitHubIdentityManager",
                mock_identity_mgr,
            ),
        ):
            result = run_async(GitHubRepoContext.detect("/fake/cwd", timeout_ms=3000))

        self.assertIsNotNone(result)
        self.assertEqual(result.owner, "testowner")
        self.assertEqual(result.repo, "testrepo")
        self.assertEqual(result.full_name, "testowner/testrepo")
        self.assertEqual(result.current_branch, "feature-branch")
        self.assertEqual(result.default_branch, "main")
        self.assertEqual(result.open_prs, [])


class TestGitHubSystemPromptInjector(unittest.TestCase):
    """Tests for GitHubSystemPromptInjector."""

    def _make_context(self, **kwargs) -> GitHubRepoContext:
        defaults = {
            "owner": "myorg",
            "repo": "myrepo",
            "full_name": "myorg/myrepo",
            "remote_url": "https://github.com/myorg/myrepo.git",
            "current_branch": "main",
            "default_branch": "main",
            "open_prs": [],
            "active_account": "devuser",
        }
        defaults.update(kwargs)
        return GitHubRepoContext(**defaults)

    def test_inject_into_prompt_appends_block(self) -> None:
        injector = GitHubSystemPromptInjector()
        ctx = self._make_context()
        result = injector.inject_into_prompt("Base prompt.", ctx)
        self.assertIn("Base prompt.", result)
        self.assertIn("myorg/myrepo", result)
        self.assertIn("GitHub Context", result)

    def test_build_context_block_contains_repo_info(self) -> None:
        injector = GitHubSystemPromptInjector()
        ctx = self._make_context()
        block = injector.build_context_block(ctx)
        self.assertIn("myorg/myrepo", block)
        self.assertIn("main", block)
        self.assertIn("devuser", block)

    def test_build_context_block_includes_open_prs(self) -> None:
        injector = GitHubSystemPromptInjector()
        pr = OpenPR(
            number=42,
            title="Add feature",
            url="https://github.com/myorg/myrepo/pull/42",
            state="OPEN",
            head_branch="feature",
        )
        ctx = self._make_context(open_prs=[pr])
        block = injector.build_context_block(ctx)
        self.assertIn("#42", block)
        self.assertIn("Add feature", block)

    def test_build_context_block_no_prs_no_pr_section(self) -> None:
        injector = GitHubSystemPromptInjector()
        ctx = self._make_context(open_prs=[])
        block = injector.build_context_block(ctx)
        # Should not have PR lines when there are no open PRs
        self.assertNotIn("Open PR", block)

    def test_inject_uses_unknown_when_no_account(self) -> None:
        injector = GitHubSystemPromptInjector()
        ctx = self._make_context(active_account=None)
        block = injector.build_context_block(ctx)
        self.assertIn("unknown", block)


if __name__ == "__main__":
    unittest.main()
