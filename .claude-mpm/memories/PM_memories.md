# PM Agent Memory

## Delegation Reinforcement

### STRICT DELEGATION RULE (project-specific override)
In this project, the PM delegates ALL code-related tasks to specialist agents, even small ones.

The "trivial edit < 5 lines" exception in PM instructions does NOT apply here.
The user has explicitly requested stricter delegation.

**ALWAYS delegate:**
- Any file read for the purpose of understanding code (delegate to Research)
- Any code/config edit, regardless of size (delegate to python-engineer or engineer)
- Diagnostic/linting fixes (delegate to python-engineer)
- Dependency investigation (delegate to Research)
- Installation/verification logic changes (delegate to python-engineer)

**PM may do directly (narrow exceptions only):**
- Pure git operations: `git status`, `git add`, `git commit`, `git pull`, `git push`, `git log`
- Single-command operational tasks explicitly listed in CLAUDE.md (e.g., `make test`, `make release-patch`)
- Reading ≤ 2 config/docs files purely for orchestration context (not code understanding)

### Pattern: "Small fix visible in diagnostics"
When Pyright/linter diagnostics appear → delegate to python-engineer, do NOT fix directly.
Even if the fix looks like a 1-line change, the PM should not be making code judgments.

### Pattern: "Investigation + Fix"
Research finds root cause → PM delegates fix to python-engineer.
PM never reads code files to understand them and then fixes inline.

### Pattern: "specific pytest invocation = investigation"
`uv run pytest tests/specific_test.py -v` is NOT a single test command.
Running targeted test files is investigation → delegate to python-engineer.
Only `make test` (or CLAUDE.md-documented shortcuts) are allowed direct test commands.
Never use: `uv run pytest tests/specific*.py`, `pytest -k "pattern"`, `pytest --tb=long`

### Pattern: "pre-commit sequencing"
PM must NOT attempt git commit while known lint/test failures exist.
Correct sequence: Delegate fix → Receive confirmation → git add → git commit.
Wrong sequence (commit, get failure, fix, retry) wastes a round-trip and violates the verification chain.

### Pattern: "make commands are operational, not PM work"
ALL make targets → delegate to Local Ops (including make test, make release-*, make build)
PM never runs make directly, even if documented in CLAUDE.md.

### Pattern: "Bash is for git only"
PM's Bash usage is limited to git operations.
Any non-git Bash command (make, pytest, sed, rm, curl) → delegate.

### Pattern: "Read for code understanding = Research"
Using the Read tool to understand code before taking action → delegate to Research.
PM may only Read ≤2 config/docs files for orchestration context (not code comprehension).
If PM reads a .py file to understand it → Circuit Breaker #2 violation.

## MCP Server Stack

Both trusty-* and the older kuzu-memory / mcp-vector-search servers are fully supported. The PM should use whichever MCP server is active in the current session. trusty-* are preferred when available, but users who have the older tools configured should continue using them — neither is deprecated.

### Memory: trusty-memory (preferred) or kuzu-memory (also supported)

**trusty-memory** (preferred if available):
- MCP prefix: `mcp__trusty-memory__*`
- Tools: `memory_remember`, `memory_recall`, `memory_recall_deep`, `memory_list`, `memory_forget`, `palace_create`, `palace_list`, `palace_info`, `kg_assert`, `kg_query`
- Palace for this project: `claude-mpm`
- Daemon: runs on port 3038, launchd plist at `/Users/masa/Library/LaunchAgents/com.bobmatnyc.trusty-memory.plist`
- Skill: `trusty-memory` (call with Skill tool)

**kuzu-memory** (also supported — use if configured instead of trusty-memory):
- MCP prefix: `mcp__kuzu-memory__*`
- Core tools: `kuzu_recall` (query), `kuzu_learn` (async store), `kuzu_remember` (immediate store)

### Search: trusty-search (preferred) or mcp-vector-search (also supported)

**trusty-search** (preferred if available):
- MCP prefix: `mcp__trusty-search__*`
- Tools: `search_code`, `index_file`, `remove_file`, `list_indexes`, `create_index`, `search_health`, `reindex`, `index_status`, `chat`
- Index name for this project: `claude-mpm`
- Daemon: runs on port 7878, launchd plist at `/Users/masa/Library/LaunchAgents/com.bobmatnyc.trusty-search.plist`
- Skill: `trusty-search` (call with Skill tool)

**mcp-vector-search** (also supported — use if configured instead of trusty-search):
- MCP prefix: `mcp__mcp-vector-search__*`
- Core tool: `search_code`

### Context-First Protocol
Before delegating to Research or reading files:
1. Query project memory first (`mcp__trusty-memory__memory_recall` or `mcp__kuzu-memory__kuzu_recall`)
2. Only then delegate to Research agent (Research will use whichever code-search backend is configured)

PM does NOT run code search directly. That is the Research agent's job.

### Pattern: "Research agent grep cascade = violation"
When delegating to Research, explicitly instruct: "Use the configured semantic code search (trusty-search or mcp-vector-search) first, grep only as last resort."
If a Research agent returns results from 5+ grep/find calls without using semantic search, that is a protocol violation.
Add to ALL Research agent delegations: "Search via mcp__trusty-search__search_code or mcp__mcp-vector-search__search_code before any grep/Bash."

## Session Workflow (Mandatory)

For every feature/fix task, follow this exact sequence:

1. **Review GH** — check related GitHub issues/PRs for context
2. **Pull ticket | prompt → ticket** — fetch existing ticket details OR create a new ticket if none exists
3. **Implement** — delegate to appropriate engineer agent
4. **Test** — delegate to QA agent; must pass before proceeding
5. **Document** — update CLAUDE.md, README, or relevant docs
6. **Patch bump** — `make release-patch` via Local Ops
7. **Publish** — `make release-publish` via Local Ops
8. **Deploy locally** — install the published version locally via Local Ops
9. **Smoke test** — delegate to QA for basic sanity check of the deployed version

Do NOT skip steps. Do NOT combine patch bump + publish into one delegation without deploy + smoke test following.
