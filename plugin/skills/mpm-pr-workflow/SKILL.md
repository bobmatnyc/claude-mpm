---
name: pm-pr-workflow
version: "1.0.0"
description: Branch protection and PR creation workflow
when_to_use: PR creation, branch operations, git push to main
category: pm-workflow
tags: [git, pr, branch-protection, pm-required]
---

# PR Workflow and Branch Protection

## Branch Protection Enforcement

**CRITICAL**: PM must enforce branch protection for main branch.

### Detection (run before any main branch operation)

```bash
git config user.email
```

### Routing Rules

- User is `bobmatnyc@users.noreply.github.com` → Can push directly to main (if explicitly requested)
- Any other user → MUST use feature branch + PR workflow

### User Request Translation

When non-privileged users request main branch operations:

| User Request | PM Action |
|--------------|-----------|
| "commit to main" | "Creating feature branch workflow instead" |
| "push to main" | "Branch protection requires PR workflow" |
| "merge to main" | "Creating PR for review" |

**Error Prevention**: PM proactively guides non-privileged users to correct workflow (don't wait for git errors).

## Worktree-First Branch Setup

Check `workflow.worktree.enabled` (default: `true`) before starting any issue branch.

### When enabled (default)

Replace the plain branch checkout with a git worktree:

```bash
# Create the worktree and branch in one step
git worktree add .claude/worktrees/issue-N-<slug> -b feat/N-<slug>

# All engineering work happens inside the worktree
cd .claude/worktrees/issue-N-<slug>
```

The source directory (`repo/`) stays on `main` throughout; only the worktree
directory advances on the feature branch.

**Post-merge cleanup** (after squash-merge lands on main):

```bash
# Remove the worktree
git worktree remove .claude/worktrees/issue-N-<slug>
git branch -d feat/N-<slug>   # delete the local tracking branch

# Pull latest main in the source dir
git pull
```

- Only run after confirming the squash-merge has landed on main.
- If the worktree has untracked files git will refuse removal — inspect with `git -C .claude/worktrees/issue-N-<slug> status` first.
- After inspecting: commit or stash any work you want to keep, then retry `git worktree remove`; or use `--force` only if you are certain the files are disposable.

### When disabled (opt-out)

Set `workflow.worktree.enabled: false` in `.claude-mpm/config.yaml` to fall back
to the standard branch checkout approach below:

```bash
git checkout -b feat/N-<slug>
```

## PR Workflow Delegation

**Default**: Main-based PRs (unless user explicitly requests stacked)

### When User Requests PRs

- Single ticket → One PR (no question needed)
- Independent features → Main-based (no question needed)
- User says "stacked" or "dependent" → Stacked PRs (no question needed)

### Recommend Main-Based When

- User doesn't specify preference
- Independent features or bug fixes
- Multiple agents working in parallel
- Simple enhancements

### Recommend Stacked PRs When

- User explicitly requests "stacked" or "dependent" PRs
- Large feature with clear phase dependencies
- User is comfortable with rebase workflows

Always delegate to version-control agent with strategy parameters.

## PR Creation Workflow

### Footer Branding (required)

Always append the canonical MPM footer to PR bodies and commit messages:

```
🤖👥 Generated with [Claude MPM](https://github.com/bobmatnyc/claude-mpm)
```

Never use Claude Code's default `🤖 Generated with [Claude Code]` footer. MPM
only overrides the commit *trailer* (`Co-Authored-By`), so the "Generated with"
footer must be set explicitly to the canonical MPM string — otherwise the Claude
Code default leaks into GitHub PRs and issues. The `Co-Authored-By: Claude MPM
<https://github.com/bobmatnyc/claude-mpm>` trailer is separate and stays as-is.

When creating PRs, delegate to version-control agent with:

```
Task:
  agent: "version-control"
  task: "Create PR for {feature}"
  context: |
    Work completed: {summary}
    Files changed: {file_list}
    Tests: {test_status}
    QA verification: {qa_evidence}
  acceptance_criteria:
    - Create feature branch from main
    - Push all commits to feature branch
    - Create PR with proper description
    - Link ticket if applicable
    - Request reviews if needed
```

## Code Review (If Available)

After the PR is created and CI passes, the PM checks whether `trusty-review` is available before proceeding to squash-merge.

### Availability Check

Call `mcp__trusty-review__review_health`. Treat trusty-review as **available** if and only if:

- `status == "ok"` AND
- `reviewer_model` is set (non-empty string)

If the health call throws an exception, returns a non-`ok` status, or returns an empty `reviewer_model`, skip the review step entirely — never block or warn the user about trusty-review being unavailable.

> **Note**: Once the upstream health endpoint exposes an `inference` field, also require `inference == "ok"` as part of the availability check.

### When Available

The PM calls `mcp__trusty-review__review_pr(owner, repo, pr_number)` directly (PM has MCP tool access). Route the verdict as follows:

| Verdict | Action |
|---------|--------|
| `APPROVE` or `APPROVE*` | Proceed to squash-merge |
| `REQUEST_CHANGES` | Delegate findings to Engineer for remediation; re-run CI before merge |
| `BLOCK` | Do not merge; escalate immediately to the user |
| `UNKNOWN` or tool error | Fail open — proceed to squash-merge with a note that review was inconclusive |

### When Unavailable

Skip silently. Do not surface any message to the user about trusty-review being down. The PR workflow continues to squash-merge as normal.

## Common Patterns

### Single Feature PR
```bash
# Feature branch → PR → Main
feature/user-auth → PR #123 → main
```

### Stacked PRs (when requested)
```bash
# Stacked feature development
feature/auth-base → PR #123 → main
feature/oauth (based on auth-base) → PR #124 → feature/auth-base
feature/session (based on oauth) → PR #125 → feature/oauth
```

### Bug Fix PR
```bash
# Hotfix branch → PR → Main
fix/login-error → PR #126 → main
```

## Branch Protection Checklist

Before any main branch operation:
- [ ] Check git user email
- [ ] Verify user has main branch access
- [ ] If not privileged user, route to feature branch workflow
- [ ] Create clear user messaging about branch protection

## Integration with Git File Tracking

All file tracking should happen on feature branches before PR creation:

1. Agent creates files
2. PM tracks files immediately (git add + commit)
3. PM delegates PR creation to version-control
4. version-control pushes branch and creates PR

This ensures all work is tracked before entering PR workflow.
