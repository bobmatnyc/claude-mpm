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

## 🔴 Delivery Workflow (PR-based)

**No direct-to-main for substantive work.** Feature / fix / refactor work lands on `main` only via a squash-merged Pull Request: `issue → branch → build/test → commit → PR → squash-merge`. Create/reference a GitHub issue first, branch off latest `main` (`feat/<issue>-<slug>`, `fix/<issue>-<slug>`), then open a PR and squash-merge after CI passes (delete the branch).

- **Trivial work** (docs / chore / typo): issue optional, but branch + PR are still required — never commit trivial work directly to `main`.
- **Exemption (direct-to-main allowed):** release tooling only — `make release-*` version bumps and `chore: update uv.lock` commits.

---

## 🔴 Release Workflow

Always use Makefile targets. Never manually edit version files.

```bash
# 1. Switch to correct GitHub account
claude-mpm gh switch   # must be bobmatnyc, not bob-duetto

# 2. Bump version and build
make release-patch     # bug fixes  (6.2.x → 6.2.y)
make release-minor     # new features  (6.2.x → 6.3.0)
make release-major     # breaking changes  (6.x.x → 7.0.0)

# 3. Publish to PyPI, Homebrew, npm, GitHub
make release-publish
```

**DO NOT**: call `./scripts/publish_to_pypi.sh` directly or push with wrong GitHub account.

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
- `agents/` — Agent definitions (`.md` files with YAML frontmatter)
- `skills/` — Skill definitions
- `migrations/` — Version-based config migrations (run on startup)
- `hooks/` — PreToolUse / PostToolUse hook handlers
- `mcp/` — MCP server implementations
- `services/` — FastAPI services (UI, session, etc.)
- `scripts/` — Shell hook dispatcher (`claude-hook-fast.sh`)

Notable agents:
- **Planner** (`.claude/agents/planner.md`) — routes complex architecture/planning tasks to `claude-opus-4-7`
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

- **Stdin reads**: Always guard `sys.stdin.read()` and `json.load(sys.stdin)` with `select.select(timeout=1.0)` to prevent blocking on empty stdin
- **Async operations**: Wrap blocking async calls with `asyncio.wait_for(timeout=N)` to prevent indefinite waits
- **External process calls**: Use subprocess-relative operations (`git -C`) instead of process-global state (e.g., `os.chdir`) to avoid race conditions
- **I/O timeouts**: Add explicit timeouts to database connections (e.g., `sqlite3.connect(timeout=1.0)`) and HTTP executor shutdown (use `wait=False`)
- **Version checks**: Cache expensive version checks to disk (keyed by binary mtime) to prevent re-entrancy hangs
- **Subprocess management**: Use `executor.shutdown(wait=False)` when shutting down HTTP executors in signal handlers to avoid blocking exit

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
1. Create `src/claude_mpm/migrations/migrate_<description>.py` with a `run_migration() -> bool` function
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
- **Types**: `mypy --strict` (Python 3.11 target in config)
- **Imports**: sorted by `ruff --select I`
- Run before committing: `uv run ruff format . && uv run ruff check --fix .`
