---
name: pm-pr-workflow
version: "1.0.0"
description: Branch protection and PR creation workflow
when_to_use: PR creation, branch operations, git push to main
category: pm-workflow
tags: [git, pr, branch-protection, pm-required]
effort: medium
---

# PR Workflow and Branch Protection

## Branch Protection Enforcement

**CRITICAL**: PM must enforce branch protection for main branch.

### Routing Rules

- All users → MUST use feature branch + PR workflow for protected branches (main/master). No exceptions.

### User Request Translation

When users request main branch operations:

| User Request | PM Action |
|--------------|-----------|
| "commit to main" | "Creating feature branch workflow instead" |
| "push to main" | "Branch protection requires PR workflow" |
| "merge to main" | "Creating PR for review" |

**Error Prevention**: PM proactively guides users to feature branch + PR workflow (don't wait for git errors).

## Delivery Workflow Requirements

The PR workflow is the framework default for landing work on `main`. Enforce these rules:

### Issue-First (Substantive Work)

For substantive work (feature / fix / refactor), **create or reference a GitHub issue before creating the branch**. The issue captures intent + acceptance criteria. Delegate issue creation to the ticketing_agent / Version Control agent. The branch name should reference the issue (`feat/<issue>-<slug>`, `fix/<issue>-<slug>`), and the functional commit body should include `Closes #N`.

### Squash-Merge Is Required

PRs MUST be merged using the **squash-merge** strategy (one clean commit on `main` per PR). **Delete the feature branch immediately after the squash-merge.** Do not use merge commits or rebase-merge for these PRs.

### Normalize Trailers on Squash-Merge (issue #863)

Squash-merge concatenates every branch commit's body into one message, which buries each interior commit's git trailer block as mid-body prose — so only the LAST commit's `X-AI-*` / `X-MPM-Version` trailers stay parseable by `git interpret-trailers --parse` on `main`. To keep token/model/version provenance intact, generate an aggregated trailer block and squash-merge with it:

```bash
# Compose the normalized squash body (sums tokens, unions models, latest version).
python scripts/squash_merge_trailers.py --pr <PR> --body-file /tmp/squash-body.txt

# Squash-merge with the normalized body and delete the branch.
gh pr merge <PR> --squash \
  --subject "feat: clean squash subject (#<PR>)" \
  --body-file /tmp/squash-body.txt \
  --delete-branch
```

The script is side-effect free (it never merges). See `docs/developer/squash-merge-trailers.md`. Verify after merge: `git log -1 --format=%B main | git interpret-trailers --parse`.

### Trivial-Work Exemption (Issue Optional)

Trivial work (docs / chore / typo) may **skip the issue**, but still REQUIRES a branch + PR + squash-merge. Never commit trivial work directly to `main`.

### Release-Tooling Exemption (Direct-to-Main Allowed)

Direct commits to `main` are permitted ONLY for release tooling: `make release-*` version bumps and `chore: update uv.lock` commits. Nothing else may bypass the PR workflow.

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
- [ ] Route to feature branch + PR workflow (no exceptions)
- [ ] Create clear user messaging about branch protection

## Integration with Git File Tracking

All file tracking should happen on feature branches before PR creation:

1. Agent creates files
2. PM tracks files immediately (git add + commit)
3. PM delegates PR creation to version-control
4. version-control pushes branch and creates PR

This ensures all work is tracked before entering PR workflow.
