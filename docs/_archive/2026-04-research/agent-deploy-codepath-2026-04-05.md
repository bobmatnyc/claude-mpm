# Research: Actual Code Path for `uv run claude-mpm agents deploy`

**Date:** 2026-04-05
**Status:** Completed
**Question:** Why does model injection in `agent_template_builder.py` not fire for 47 of 54 agents during `agents deploy`?

---

## Key Finding

`uv run claude-mpm agents deploy` uses a **completely different code path** than `ClaudeRunner.setup_agents()`. The CLI deploy command **does not call `AgentTemplateBuilder.build_agent_markdown()`** at all. It directly copies files from cache to `.claude/agents/` via `deploy_agent_file()`, bypassing the template builder entirely.

---

## The Two Deploy Paths

### Path A: `uv run claude-mpm agents deploy` (CLI command)

**Entry → Exit with file:line references:**

```
src/claude_mpm/cli/commands/agents.py:603  _deploy_agents()
  -> src/claude_mpm/services/agents/sources/git_source_sync_service.py:1144  deploy_agents_to_project()
     -> src/claude_mpm/services/agents/deployment_utils.py:298  deploy_agent_file()
        -> deployment_utils.py:435  target_file.write_text(deploy_content, encoding="utf-8")
```

**What `deploy_agent_file()` does:**
1. Reads raw source content from cache file (line 368)
2. Optionally calls `ensure_agent_id_in_frontmatter()` (line 427) — only adds `agent_id`, nothing else
3. Writes content directly to `.claude/agents/<name>.md` (line 435)

**`AgentTemplateBuilder.build_agent_markdown()` is NEVER called in this path.**

The agents written via `agents deploy` are verbatim copies of cache files with only `agent_id` potentially injected into frontmatter. No `model` field is added if the source file lacks one.

### Path B: `ClaudeRunner.setup_agents()` (session startup)

**Entry → Exit with file:line references:**

```
src/claude_mpm/core/claude_runner.py:284  setup_agents()
  -> src/claude_mpm/services/agents/deployment/agent_deployment.py:276  deploy_agents()
     -> agent_deployment.py:496  single_agent_deployer.deploy_single_agent()
        -> src/claude_mpm/services/agents/deployment/single_agent_deployer.py:96
           agent_content = self.template_builder.build_agent_markdown(...)
           -> src/claude_mpm/services/agents/deployment/agent_template_builder.py:421  build_agent_markdown()
              -> agent_template_builder.py:527-531  model = DEFAULT_MODEL_BY_TYPE.get(...)  ← injection point
           -> single_agent_deployer.py:102  target_file.write_text(agent_content)
```

**`AgentTemplateBuilder.build_agent_markdown()` IS called here.** Model injection fires at line 527-531.

### Path C: Startup Reconciliation

```
src/claude_mpm/cli/startup.py:1341  perform_startup_reconciliation()
  -> src/claude_mpm/services/agents/deployment/startup_reconciliation.py:219  perform_startup_reconciliation()
     -> deployment_reconciler.py:447  deploy_agent_file(agent_file, deploy_dir)
```

Same as Path A — uses `deploy_agent_file()` directly, no template builder.

---

## Why 47 of 54 Agents Lack Model Fields

When `agents deploy` is run:
1. Agents are fetched from the remote repository into cache (`~/.claude-mpm/cache/agents/`)
2. Cache files are copied as-is to `.claude/agents/` via `deploy_agent_file()`
3. Only `agent_id` is potentially added to frontmatter
4. If the source `.md` file in the repository has no `model:` field in its frontmatter, none is written

The `build_agent_markdown()` model injection at `agent_template_builder.py:527-531` **only executes when `ClaudeRunner.setup_agents()` is called**, and that path is skipped if `.claude/agents/` already has files (line 291-303 in `claude_runner.py`):

```python
# claude_runner.py:289-303
agents_dir = Path.cwd() / ".claude" / "agents"
if agents_dir.exists():
    existing_agents = list(agents_dir.glob("*.md"))
    if len(existing_agents) > 0:
        # Reconciliation already deployed agents - skip
        return True
```

So once `agents deploy` has run (populating `.claude/agents/`), `setup_agents()` short-circuits and never calls the template builder, meaning model injection never happens.

---

## The Fix

Model injection needs to happen in `deploy_agent_file()` in `deployment_utils.py`, not only in `AgentTemplateBuilder.build_agent_markdown()`.

**Option 1 (targeted):** Add model injection to `deploy_agent_file()` alongside the existing `ensure_agent_id_in_frontmatter()` call.

**Option 2 (unified):** Have `deploy_agents_to_project()` in `git_source_sync_service.py` call `AgentTemplateBuilder.build_agent_markdown()` instead of `deploy_agent_file()` for the content step.

**Option 3 (source fix):** Ensure the agent source files in the remote repository already have `model:` fields, so no injection is needed during deploy.

---

## File References Summary

| File | Line | Role |
|------|------|------|
| `src/claude_mpm/cli/commands/agents.py` | 603 | CLI `_deploy_agents()` entry point |
| `src/claude_mpm/cli/commands/agents.py` | 661-662 | Calls `git_sync.deploy_agents_to_project()` |
| `src/claude_mpm/services/agents/sources/git_source_sync_service.py` | 1144 | `deploy_agents_to_project()` |
| `src/claude_mpm/services/agents/sources/git_source_sync_service.py` | 1200 | Sets `deployment_dir = project_dir / ".claude" / "agents"` |
| `src/claude_mpm/services/agents/sources/git_source_sync_service.py` | 1277 | Calls `deploy_agent_file()` |
| `src/claude_mpm/services/agents/deployment_utils.py` | 298 | `deploy_agent_file()` — the actual writer |
| `src/claude_mpm/services/agents/deployment_utils.py` | 427 | Only frontmatter injection: `ensure_agent_id_in_frontmatter()` |
| `src/claude_mpm/services/agents/deployment_utils.py` | 435 | `target_file.write_text(deploy_content)` — writes .md file |
| `src/claude_mpm/services/agents/deployment/agent_template_builder.py` | 421 | `build_agent_markdown()` — model injection lives here |
| `src/claude_mpm/services/agents/deployment/agent_template_builder.py` | 527 | Model injection: `model = DEFAULT_MODEL_BY_TYPE.get(agent_name, DEFAULT_MODEL)` |
| `src/claude_mpm/services/agents/deployment/single_agent_deployer.py` | 96 | Only caller of `build_agent_markdown()` during deploy |
| `src/claude_mpm/core/claude_runner.py` | 289-303 | Short-circuits `setup_agents()` if `.claude/agents/` already populated |
| `src/claude_mpm/services/agents/deployment/deployment_reconciler.py` | 447 | Reconciler also uses `deploy_agent_file()` directly |
