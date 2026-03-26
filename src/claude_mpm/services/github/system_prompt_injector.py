"""Inject GitHub context into system prompts."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .repo_context import GitHubRepoContext

_TEMPLATE = """
## GitHub Context

- Repository: {full_name}
- Branch: {current_branch} (default: {default_branch})
- Account: {active_account}
{pr_lines}
GitHub MCP tools (mcp__github__*) are available for repository operations.
""".strip()


class GitHubSystemPromptInjector:
    """Builds and injects a GitHub context block into system prompts."""

    def build_context_block(self, ctx: GitHubRepoContext) -> str:
        pr_lines = ""
        if ctx.open_prs:
            lines = [
                f'- Open PR #{pr.number}: "{pr.title}" ({pr.url})'
                for pr in ctx.open_prs
            ]
            pr_lines = "\n".join(lines) + "\n"
        return _TEMPLATE.format(
            full_name=ctx.full_name,
            current_branch=ctx.current_branch,
            default_branch=ctx.default_branch,
            active_account=ctx.active_account or "unknown",
            pr_lines=pr_lines,
        )

    def inject_into_prompt(self, base_prompt: str, ctx: GitHubRepoContext) -> str:
        """Append GitHub context block to an existing system prompt."""
        block = self.build_context_block(ctx)
        return f"{base_prompt}\n\n{block}"
