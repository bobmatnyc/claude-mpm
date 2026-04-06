---
name: auto-bug-reporter
version: "1.0.0"
description: Automatically file GitHub issues when claude-mpm errors are encountered during a session
when_to_use: Import errors, hook failures, CLI errors, MCP tool errors, test failures in claude-mpm
category: pm-workflow
tags: [bug-reporting, github, issues, auto-report, claude-mpm]
effort: low
---

# Auto Bug Reporter

Automatically file GitHub issues when you encounter errors, crashes, or unexpected behavior in claude-mpm during a session.

## Trigger Conditions

File an issue automatically when you encounter ANY of the following:

- **Import errors** in claude-mpm modules (e.g., `ModuleNotFoundError`, `ImportError` from claude-mpm source paths)
- **Hook errors** — stop hook, start hook, or prompt hook failures
- **Agent deployment failures** — agent fails to start, crashes mid-task, or returns unexpected errors
- **Skill deployment failures** — skill fails to load, parse, or execute
- **MCP tool errors** from claude-mpm tools (e.g., `mcp-ticketer`, `mpm-messaging`, `mcp-vector-search` when used within claude-mpm context)
- **Test failures** in claude-mpm's own test suite (not user project tests)
- **CLI errors** from `claude-mpm` commands (e.g., `claude-mpm init`, `claude-mpm run`, `claude-mpm doctor`)
- **Configuration errors** — missing config, invalid YAML, malformed `.claude/settings.json`
- **Orchestration errors** — PM fails to delegate, agent routing breaks

## Do NOT File Issues For

- User project errors unrelated to claude-mpm internals
- Rate limit errors from Anthropic API (HTTP 429)
- Network connectivity issues (DNS failures, timeouts)
- Pyright or mypy diagnostics in user code (not claude-mpm source)
- Pre-existing known issues already filed (search first)
- Errors from user-written hooks or custom agents not part of claude-mpm

## How to File

Use the `mcp__github__create_issue` tool:

- **Owner**: `bobmatnyc`
- **Repo**: `claude-mpm`
- **Labels**: `["bug", "auto-reported"]`
- **Title format**: `auto: <brief description of error>`

### Issue Body Template

```markdown
## Auto-Reported Bug

**Encountered during**: <what the user was doing when the error occurred>
**Error**: <exact error message or traceback>
**File**: <file path and line number if known>
**Version**: <claude-mpm version if known — run `claude-mpm --version` or check pyproject.toml>

## Reproduction

<steps or context that led to the error>

## Severity

- [ ] Blocking (prevents core functionality)
- [ ] Degraded (workaround exists)
- [ ] Cosmetic (no functional impact)

_Filed automatically by claude-mpm auto-bug-reporter_
```

## Step-by-Step Procedure

1. **Detect the error** — identify it matches a trigger condition above.

2. **Search for duplicates first** using `mcp__github__search_issues`:
   ```
   repo:bobmatnyc/claude-mpm is:issue <key error terms>
   ```
   If a matching open issue already exists, skip filing and note the existing issue number.

3. **Gather context**:
   - Exact error message or stack trace
   - What the user was attempting when the error occurred
   - File path and line number if visible
   - claude-mpm version (check `pyproject.toml` or `uv run claude-mpm --version`)

4. **File the issue** using `mcp__github__create_issue` with owner `bobmatnyc`, repo `claude-mpm`, the title and body from the template above, and labels `["bug", "auto-reported"]`.

5. **Tell the user** immediately after filing:
   ```
   Filed auto-bug-report: #<issue_number> — <title>
   ```

6. **Continue the user's task** — do not stop or wait. The issue is filed; move on.

## Rate Limiting

- Do not file duplicate issues — always search existing issues first.
- Maximum **3 auto-filed issues per session** to avoid noise.
- If you have already filed 3 issues in the current session, log the error to the user verbally but do not file another issue.

## Severity Guidance

| Error Type | Severity |
|---|---|
| Agent or hook completely non-functional | Blocking |
| CLI command fails with traceback | Blocking |
| MCP tool errors breaking workflow | Blocking |
| Config error with a manual workaround | Degraded |
| Incorrect output, wrong behavior | Degraded |
| Minor display or formatting glitch | Cosmetic |

## Example Filed Issue

**Title**: `auto: ModuleNotFoundError for claude_mpm.hooks.stop_hook`

**Body**:
```markdown
## Auto-Reported Bug

**Encountered during**: Running `claude-mpm run` with a custom stop hook configured
**Error**: `ModuleNotFoundError: No module named 'claude_mpm.hooks.stop_hook'`
**File**: `src/claude_mpm/hooks/stop_hook.py` (missing)
**Version**: 6.2.5

## Reproduction

1. Configure a stop hook in `.claude/settings.json`
2. Run `claude-mpm run`
3. At session end, hook dispatch fails with ModuleNotFoundError

## Severity

- [x] Blocking (prevents core functionality)

_Filed automatically by claude-mpm auto-bug-reporter_
```

## Related Skills

- `mpm-bug-reporting` — Manual PM-driven bug reporting with routing to multiple repos
- `mpm-verification-protocols` — QA evidence standards
- `mpm-doctor` — Diagnosing claude-mpm environment issues
