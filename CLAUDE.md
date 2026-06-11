# Claude MPM Project

Claude Multi-Agent Project Manager — orchestrates Claude subagents with agent delegation, skills, MCP integration, session management, and semantic code search.

- **Language**: Python 3.13+
- **Framework**: FastAPI + Click CLI
- **Package**: `src/claude_mpm/` (src layout)
- **Version**: managed via `commitizen` + `make release-*`

---

## Priority Guide

🔴 **CRITICAL** — Must follow, prevents data loss or broken releases  
🟡 **IMPORTANT** — Follow unless there is a clear reason not to  
🟢 **RECOMMENDED** — Best practice, apply when practical  
⚪ **OPTIONAL** — Nice to have

---

## 🔴 Git Commit Rules

**ONE FILE PER COMMIT.** Never bundle multiple file changes into a single commit.

```bash
# Correct
git add src/claude_mpm/migrations/runner.py
git commit -m "feat: add migration runner with rich output"

git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with priority rankings"
```

Use conventional commit prefixes: `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `chore`

### Referencing Issues

Use `Closes #N` in the commit body to auto-close a GitHub issue when the commit lands on `main`. `Fixes #N` and `Resolves #N` are equivalent.

```bash
git commit -m "fix: resolve agent discovery path bug

Closes #447"
```

---

## 🟡 Worktree Development Workflow

Keep the primary checkout on `main`/HEAD at all times — never check out a feature branch in it.

**Per-issue worktree:**

```bash
git worktree add .claude/worktrees/issue-<N>-<slug> -b feat/<N>-<slug>
# All build, test, and commit operations happen inside the worktree
```

`.claude/worktrees/` is gitignored; each issue gets its own tree. Parallel agents or parallel issues use separate worktrees — never run concurrent branch mutations in one tree.

**Cleanup after squash-merge:**

```bash
git worktree remove .claude/worktrees/issue-<N>-<slug>
git branch -d feat/<N>-<slug>
git pull
```

Only run after confirming the squash-merge has landed on `main`.

> **Note:** The MPM PM enforces this automatically via the Agent tool's `isolation: "worktree"` parameter. Canonical rules live in `src/claude_mpm/agents/WORKFLOW.md`.

---

## 🔴 Release Workflow

`claude-mpm gh switch` first (must be bobmatnyc, not bob-duetto) → `make release-patch|minor|major` → `make release-publish`. Never call `./scripts/publish_to_pypi.sh` directly.

---

## 🔴 Security: credential files

Credential/identity files (e.g. `scripts/lib/gh_identity.sh`) must **never** be pushed directly to `main` — always open a Pull Request so they get owner review. This is enforced by `.githooks/pre-push` (install via `scripts/setup-git-hooks.sh`), which blocks direct pushes to `main` that touch sensitive paths, and by a CI backstop (`.github/workflows/guard-sensitive-paths.yml`) that catches `--no-verify` bypasses. Release version-bump pushes (VERSION, pyproject.toml, etc.) are unaffected.

---

## 🔴 Test Workflow

```bash
make test                           # full suite with xdist parallelization
uv run pytest -n auto               # same, explicit
uv run pytest -p no:xdist tests/    # serial mode for flaky/order-dependent tests
uv run pytest tests/path/test_x.py  # single file
```

---

## Architecture Overview

```
CLI (click)  →  Services  →  Agents  →  Claude Code subprocess
                                 ↓
                            Skills / MCP servers
```

**Deep dive**: See [`docs/developer/AGENT_ASSEMBLY_PIPELINE.md`](docs/developer/AGENT_ASSEMBLY_PIPELINE.md) for how agent definitions are produced, composed, and delivered to running prompts.

Key packages:
- `cli/` — Click commands and interactive wizards
- `agents/` — Bundled default agent templates (`.md` files with YAML frontmatter); **active deployed agents live in `.claude/agents/`**
- `skills/` — Skill definitions
- `migrations/` — Version-based config migrations (run on startup)
- `hooks/` — PreToolUse / PostToolUse hook handlers
- `mcp/` — MCP server implementations
- `services/` — FastAPI services (UI, session, etc.)
- `scripts/` — Shell hook dispatcher (`claude-hook-fast.sh`)

Notable agents:
- **Planner** (configured via `manifest/presets/default.json`) — routes complex architecture/planning tasks to `claude-opus-4-7`
- **Code Contracts** — engineer agents write `icontract` preconditions/postconditions/invariants alongside implementations; QA agents (code-critic) derive a three-level test pyramid from them: contract-targeted unit tests, property-based tests via `hypothesis`/`fast-check`, and precondition violation tests. See [`docs/features/code-contracts.md`](docs/features/code-contracts.md).

---

## 🟡 Subagent Patterns

Agent frontmatter (`agents/*.md`) supports **both** MPM-proprietary and Claude Code native fields:

**MPM-proprietary**: `agent_id`, `agent_type`, `resource_tier`, `schema_version`, `capabilities`, `temperature`, `max_tokens`, `timeout`

**Claude Code native**: `name`, `description`, `model`, `tools`, `disallowedTools`, `permissionMode`, `maxTurns`, `memory`, `skills`, `hooks`, `background`, `effort`, `isolation`, `color`

Invoke subagents via the `Agent` tool (not bash):
```
Agent(subagent_type="agent-name", description="...", prompt="...", model="haiku")
```

---

## 🟡 Hooks System

Hook dispatcher: `src/claude_mpm/scripts/claude-hook-fast.sh`  
Model tier enforcement: `src/claude_mpm/hooks/model_tier_hook.py`

Hooks are configured in `.claude/settings.json` (team-shared) and `.claude/settings.local.json` (personal, git-ignored). Local overrides team settings.

Key hook events: `PreToolUse`, `PostToolUse`, `Stop`, `SubagentStop`, `SessionStart`, `UserPromptSubmit`

### Stability Patterns

When adding new hooks or hook handlers, follow these patterns to prevent hangs:

Key patterns: `select.select` stdin guards, `asyncio.wait_for` timeouts, `git -C` subprocess isolation, `sqlite3.connect(timeout=1.0)`, `executor.shutdown(wait=False)`, disk-cached version checks.

---

## 🟡 Configuration Hierarchy

1. `managed-settings.json` / MDM — org-enforced, cannot override
2. Command-line arguments — single-session
3. `.claude/settings.local.json` — personal project settings (git-ignored)
4. `.claude/settings.json` — team-shared (checked in)
5. `~/.claude/settings.json` — global personal defaults

---

## 🟡 Migrations

Migrations run automatically on startup via `run_pending_migrations()`. State tracked in `~/.claude-mpm/migrations.json`.

To add a new migration:
1. Create `src/claude_mpm/migrations/v<version>_<description>.py` (preferred) or `migrate_<description>.py` with a `run_migration() -> bool` function
2. Register it in `src/claude_mpm/migrations/registry.py` with a unique `id` and `version`

---

## 🟢 Debugging Tips

- Use `/doctor` (`claude-mpm doctor`) for diagnostics
- Run long terminal commands as background tasks for better log visibility
- Use browser automation MCPs (Playwright) for console log inspection
- Hook failures: check `~/.claude-mpm/` logs; test hook scripts manually
- For flaky tests: use `-p no:xdist` to serialize execution

---

## 🟢 Code Standards

- **Formatter**: `ruff format` (Black-compatible, 88 chars)
- **Linter**: `ruff check` (replaces flake8, isort, pyupgrade)
- **Types**: `mypy` with partial strict flags (`warn_return_any`, `disallow_untyped_defs`); Python 3.13 target
- **Imports**: sorted by `ruff --select I`
- Run before committing: `uv run ruff format . && uv run ruff check --fix .`
