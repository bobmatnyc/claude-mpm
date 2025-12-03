# Agent Modification Workflow

**Last Updated:** 2025-12-03
**Status:** Active
**Audience:** Contributors, Developers

---

## Overview

This guide explains how to modify agents in the Claude MPM framework and commit changes back to the source repository. The cache directory (`~/.claude-mpm/cache/remote-agents/`) contains full git repositories, making it easy to contribute agent improvements.

### Quick Summary

- ✅ **Cache is a git repository**: `~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/`
- ✅ **Modifications are tracked**: Git automatically detects changes to agent files
- ✅ **Can commit and push**: Full git workflow available
- ✅ **Remote configured**: GitHub remote pre-configured for contributions

---

## Table of Contents

1. [Understanding the Cache Structure](#understanding-the-cache-structure)
2. [Making Agent Modifications](#making-agent-modifications)
3. [Committing Changes](#committing-changes)
4. [Testing Your Changes](#testing-your-changes)
5. [Pushing to Remote](#pushing-to-remote)
6. [Common Workflows](#common-workflows)
7. [Troubleshooting](#troubleshooting)

---

## Understanding the Cache Structure

### Cache Directory Layout

```
~/.claude-mpm/cache/
├── remote-agents/
│   ├── bobmatnyc/
│   │   └── claude-mpm-agents/              # ← Full git repository
│   │       ├── .git/                       # Git metadata
│   │       ├── agents/                     # Agent files
│   │       │   ├── engineer/
│   │       │   │   ├── backend/
│   │       │   │   │   ├── python-engineer.md
│   │       │   │   │   ├── golang-engineer.md
│   │       │   │   │   └── ...
│   │       │   │   ├── frontend/
│   │       │   │   └── core/
│   │       │   ├── qa/
│   │       │   │   ├── api-qa.md
│   │       │   │   ├── web-qa.md
│   │       │   │   └── qa.md
│   │       │   ├── ops/
│   │       │   ├── security/
│   │       │   └── universal/
│   │       ├── templates/                  # PM instruction templates
│   │       ├── build-agent.py             # Agent build scripts
│   │       └── README.md
│   └── [other-repos]/
└── skills/                                 # Skills cache (not git)
```

### Key Points

- **Git Repository**: The cache contains a complete git working copy
- **Remote**: Pre-configured to `https://github.com/bobmatnyc/claude-mpm-agents.git`
- **Branch**: Typically on `main` branch
- **Status**: Clean after sync (no uncommitted changes unless manually edited)

---

## Making Agent Modifications

### Option 1: Direct File Editing

```bash
# Navigate to cache
cd ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents

# Edit an agent file
vim agents/qa/api-qa.md

# Or use your preferred editor
code agents/engineer/backend/python-engineer.md
```

### Option 2: Edit via Deployed Location (Not Recommended)

While you can edit agents in `.claude/agents/`, changes won't be tracked in git. Always edit in the cache directory for proper version control.

### What to Modify

**Common modifications:**
- Agent instructions and workflows
- Version numbers (follow semantic versioning)
- Capabilities and specializations
- Dependencies and requirements
- Examples and best practices

**Frontmatter fields you can update:**
```yaml
---
name: agent_name
version: 1.2.3              # Increment appropriately
description: "..."          # Update if behavior changes
capabilities:               # Add/remove capabilities
  - capability1
  - capability2
tags:                       # Update for discoverability
  - tag1
  - tag2
---
```

---

## Committing Changes

### Step 1: Check Git Status

```bash
cd ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents

# View modified files
git status

# View specific changes
git diff agents/qa/api-qa.md
```

### Step 2: Stage Changes

```bash
# Stage specific file
git add agents/qa/api-qa.md

# Or stage all modified agents
git add agents/
```

### Step 3: Commit with Proper Message

Follow [Conventional Commits](https://www.conventionalcommits.org/) format:

```bash
# Feature addition
git commit -m "feat: add GraphQL testing capabilities to api-qa agent

- Added GraphQL schema validation
- Added subscription testing support
- Updated examples with GraphQL queries

Closes: #123"

# Bug fix
git commit -m "fix: correct authentication workflow in api-qa agent

- Fixed OAuth2 token refresh logic
- Added missing error handling
- Updated documentation

Fixes: #456"

# Documentation update
git commit -m "docs: improve api-qa agent testing examples

- Added cURL examples
- Added Postman collection reference
- Clarified authentication requirements"
```

### Step 4: Verify Commit

```bash
# View commit
git log -1 --stat

# View full commit details
git show HEAD
```

---

## Testing Your Changes

### Test Locally Before Pushing

```bash
# 1. Deploy your modified agent
cd ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents
# Changes are automatically synced on next startup

# 2. Run Claude MPM with the modified agent
claude-mpm run -i "Test task for the modified agent"

# 3. Verify agent behavior is correct
# Test the specific functionality you modified
```

### Validation Checklist

- [ ] Agent file has valid YAML frontmatter
- [ ] Version number incremented appropriately
- [ ] Instructions are clear and unambiguous
- [ ] Examples work as documented
- [ ] No syntax errors in markdown
- [ ] Changes align with agent's purpose

---

## Pushing to Remote

### Prerequisites

- **Authentication**: Ensure you have GitHub credentials configured
- **Permissions**: Need write access to the repository
- **Branch**: Typically push to `main` or create a feature branch

### Push Workflow

```bash
cd ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents

# Check remote is configured
git remote -v
# Should show: origin  https://github.com/bobmatnyc/claude-mpm-agents.git

# Push to main (if you have permissions)
git push origin main

# Or create a pull request workflow
git checkout -b feature/improve-api-qa
git push origin feature/improve-api-qa
# Then create PR on GitHub
```

### Dry Run (Testing Push)

```bash
# Test if push would work without actually pushing
git push --dry-run origin main
```

---

## Common Workflows

### Workflow 1: Quick Fix to Existing Agent

```bash
# 1. Edit agent
vim ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/qa/api-qa.md

# 2. Commit
cd ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents
git add agents/qa/api-qa.md
git commit -m "fix: improve error handling in api-qa agent"

# 3. Test locally
claude-mpm run -i "Test the fix"

# 4. Push
git push origin main
```

### Workflow 2: Adding New Capabilities

```bash
# 1. Pull latest changes
cd ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents
git pull origin main

# 2. Edit agent (add capabilities)
vim agents/engineer/backend/python-engineer.md

# 3. Update version in frontmatter
# version: 1.2.3 → 1.3.0 (minor bump for new feature)

# 4. Commit with detailed message
git add agents/engineer/backend/python-engineer.md
git commit -m "feat: add async/await patterns to python-engineer

- Added asyncio best practices
- Added async framework examples (FastAPI, aiohttp)
- Updated testing section for async code

Closes: #789"

# 5. Test thoroughly
claude-mpm run -i "Test async patterns"

# 6. Push
git push origin main
```

### Workflow 3: Creating Pull Request

```bash
# 1. Create feature branch
cd ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents
git checkout -b feature/enhance-qa-agents

# 2. Make multiple changes
vim agents/qa/api-qa.md
vim agents/qa/web-qa.md

# 3. Commit changes
git add agents/qa/
git commit -m "feat: add comprehensive API contract testing

- Added OpenAPI/Swagger validation
- Added contract testing with Pact
- Updated both api-qa and web-qa agents"

# 4. Push to feature branch
git push origin feature/enhance-qa-agents

# 5. Create PR on GitHub
# Visit: https://github.com/bobmatnyc/claude-mpm-agents
# Click "Compare & pull request"
```

---

## Troubleshooting

### Issue: "Permission denied" when pushing

**Cause:** No write access to repository or authentication failed

**Solution:**
```bash
# Check GitHub authentication
gh auth status

# Login if needed
gh auth login

# Or configure SSH keys
# See: https://docs.github.com/en/authentication
```

### Issue: "Your branch is behind origin/main"

**Cause:** Remote has changes you don't have locally

**Solution:**
```bash
# Pull and rebase
git pull --rebase origin main

# Or merge
git pull origin main

# Then push
git push origin main
```

### Issue: Merge conflicts

**Cause:** Your changes conflict with remote changes

**Solution:**
```bash
# See conflicted files
git status

# Resolve conflicts manually
vim agents/qa/api-qa.md

# Stage resolved files
git add agents/qa/api-qa.md

# Continue rebase/merge
git rebase --continue
# OR
git merge --continue

# Push
git push origin main
```

### Issue: Changes not reflected in Claude MPM

**Cause:** Cache hasn't been synced to deployment location

**Solution:**
```bash
# Force agent re-sync
claude-mpm agents sync --force

# Or restart Claude MPM
# Changes sync automatically on next startup
```

---

## Best Practices

### 1. Always Pull Before Editing

```bash
cd ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents
git pull origin main
# Now edit...
```

### 2. Use Semantic Versioning

- **Patch** (1.2.3 → 1.2.4): Bug fixes, documentation
- **Minor** (1.2.3 → 1.3.0): New features (backward compatible)
- **Major** (1.2.3 → 2.0.0): Breaking changes

### 3. Test Before Pushing

Always test your changes locally before pushing to avoid breaking others.

### 4. Write Descriptive Commits

Good commit messages help reviewers and future maintainers:

```bash
# ✅ Good
git commit -m "feat: add WebSocket testing to api-qa agent

- Added WebSocket connection handling
- Added subscription message validation
- Updated examples with Socket.io

Closes: #123"

# ❌ Bad
git commit -m "updated api-qa"
```

### 5. Keep Changes Focused

One logical change per commit:
- Don't mix bug fixes with new features
- Don't update multiple unrelated agents in one commit
- Make review easier with focused changes

---

## Related Documentation

- [Creating Agents](../agents/creating-agents.md) - How to create new agents
- [Agent Architecture](../developer/ARCHITECTURE.md) - Understanding agent system
- [Cache Architecture](../research/cache-update-workflow-analysis-2025-12-03.md) - How caching works
- [Contributing Guide](../../CONTRIBUTING.md) - General contribution guidelines

---

## Summary

The agent modification workflow is straightforward:

1. **Edit** agents in `~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/`
2. **Commit** changes with conventional commit messages
3. **Test** locally before pushing
4. **Push** to GitHub (main branch or PR)

The cache directory is a full git repository, giving you complete version control and collaboration capabilities!
