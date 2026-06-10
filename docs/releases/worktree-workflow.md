# Worktree-first workflow is now the default

## Summary

Starting from this release, all issue-linked work in claude-mpm uses git
worktrees by default. Each GitHub issue gets its own `worktree` directory
under `.worktrees/`; the source repository stays pinned to `HEAD` throughout
the entire development cycle.

This is an **opt-out** change: no existing config files need to be edited.
To disable the feature set `workflow.worktree.enabled: false` in
`.claude-mpm/config.yaml`.

## Rationale

| Problem with plain branch checkout | How worktrees solve it |
|------------------------------------|------------------------|
| Source directory changes with the branch — agents lose their HEAD reference | Source dir is always on `main`; worktrees are fully independent |
| Parallel agents on different issues risk conflicts inside the same working tree | Each issue lives in `.worktrees/issue-N-<slug>/` — completely isolated |
| Switching branches requires stashing or committing WIP | No stash/checkout gymnastics; each worktree has its own index |
| `isolation: "worktree"` on Agent tool calls requires an actual worktree | Native alignment: same directory layout the Agent tool expects |

## What the new workflow looks like

### Before (plain branch checkout)

```
repo/                  ← switches between main / feature branches
```

```bash
git checkout -b feat/N-<slug>
# ... work here ...
gh pr create
git checkout main
git branch -d feat/N-<slug>
```

### After (worktree-first, default)

```
repo/                          ← always main, always at HEAD
  .worktrees/
    issue-N-<slug>/            ← git worktree, feat/N-<slug> branch
    issue-M-<other>/           ← another issue, fully independent
```

```bash
git worktree add .worktrees/issue-N-<slug> -b feat/N-<slug>
# work inside .worktrees/issue-N-<slug>/
gh pr create
# after squash-merge:
git worktree remove .worktrees/issue-N-<slug> --force
git pull
```

## Migration / opt-out

To revert to the plain branch-checkout model for a project, add to
`.claude-mpm/config.yaml`:

```yaml
workflow:
  worktree:
    enabled: false
```

No other changes are needed. All other workflow steps (branch naming,
commit conventions, PR footer, trusty-review gate, squash-merge) remain
identical.

## Technical details

The following files were changed as part of this feature:

| File | Change |
|------|--------|
| `src/claude_mpm/services/project/gitignore_manager.py` | Added `.worktrees/` to `STANDARD_GITIGNORE_PATTERNS` (bare `worktrees/` was intentionally excluded as too broad) |
| `src/claude_mpm/cli/commands/config.py` | Added `.worktrees/` to the `config gitignore` recommendation output (bare `worktrees/` excluded) |
| `src/claude_mpm/core/config.py` | Added `workflow.worktree` sub-key to `_apply_defaults()` with `enabled: true` |
| `src/claude_mpm/agents/WORKFLOW.md` | Added **Worktree Workflow (default)** section documenting the 8-step model |
| `plugin/skills/mpm-pr-workflow/SKILL.md` | Added **Worktree-First Branch Setup** section with worktree commands and post-merge cleanup |
