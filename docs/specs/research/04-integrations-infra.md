# Integrations & Infrastructure — Ground-Truth Specification Research

**Issue reference:** #523 cross-reference table  
**Research date:** 2026-06-01  
**Methodology:** Direct source reading of every file listed in scope; no assumptions from docs.

---

## Table of Contents

1. [MCP Integrations — Trusty-Search & Trusty-Memory Setup](#1-mcp-integrations--trusty-search--trusty-memory-setup)
2. [MCP Config Builder](#2-mcp-config-builder)
3. [MCP Service Installer](#3-mcp-service-installer)
4. [Memory Enrichment — UserPromptSubmit](#4-memory-enrichment--userpromptsubmit)
5. [Memory Session Persistence — Stop / SubagentStop](#5-memory-session-persistence--stop--subagentsStop)
6. [Migrations System](#6-migrations-system)
7. [Dashboard / UI Service](#7-dashboard--ui-service)
8. [Drift Summary](#8-drift-summary)

---

## 1. MCP Integrations — Trusty-Search & Trusty-Memory Setup

**Primary files:**  
- `src/claude_mpm/cli/commands/setup/handlers/trusty.py` — EXISTS  
- `src/claude_mpm/migrations/migrate_trusty_autodetect.py` — EXISTS

### WHAT

`trusty.py` provides the `TrustyMixin` class (lines 66–917), a mixin composed into the setup command handler. It implements three service-specific setup methods and a suite of shared helpers.

**Shared helpers (`TrustyMixin`):**

| Helper | Lines | Purpose |
|--------|-------|---------|
| `_http_health_check(url, timeout=2.0)` | 83–97 | stdlib-only HTTP probe; non-2xx = False |
| `_cargo_bin_path(binary_name)` | 99–109 | `shutil.which` then `~/.cargo/bin` fallback |
| `_install_cargo_binary(args, service)` | 111–163 | Delegates to `PackageInstallerService`; respects `--force`/`--upgrade` |
| `_write_launchd_plist(...)` | 165–214 | Writes macOS `~/Library/LaunchAgents/<label>.plist` with `KeepAlive=true` |
| `_ensure_launchd_loaded(label, path)` | 216–271 | `launchctl unload` then `load`; verifies with `launchctl list` |
| `_trusty_search_base_url()` | 273–295 | Reads `~/.trusty-search/http_addr`; fallback `127.0.0.1:7878` |
| `_trusty_memory_base_url()` | 297–318 | Reads `~/.trusty-memory/http_addr`; fallback `127.0.0.1:7070` |
| `_atomic_write_json(path, data)` | 324–348 | Writes to same-directory temp file then `os.replace` (atomic) |
| `_load_settings(path)` | 350–367 | Loads `.claude/settings.json`; returns `{"hooks":{}}` skeleton on absence |
| `_inject_hooks_to_settings(path, services)` | 369–497 | Idempotent hook injection; removes `_LEGACY_SERVICES` first |
| `_inject_trusty_hooks(services)` | 499–522 | Calls `_inject_hooks_to_settings` for both project and user-level settings |

**Legacy service cleanup** (line 28):  
`_LEGACY_SERVICES = {"kuzu-memory", "mcp-vector-search"}` — any hooks tagged with these `_mpm_service` values are removed before trusty hooks are injected.

**Hook specifications** (lines 33–63):

- `trusty-memory`: injects `claude-hook` (command) on `SessionStart`, `Stop`, `SubagentStop` events (matcher `*`), tagged `_mpm_service: "trusty-memory"`, timeout 15s.
- `trusty-search`: injects `python3 -m claude_mpm.hooks.trusty_index_hook` on `PostToolUse` with matcher `Write|MultiEdit|Edit|NotebookEdit`, tagged `_mpm_service: "trusty-search"`, timeout 10s, `async: True`.

**`_setup_trusty_search` flow** (lines 528–647):
1. Install `trusty-search` binary via cargo.
2. HTTP health-check `~/.trusty-search/http_addr`/health; if down, write and load launchd plist `com.bobmatnyc.trusty-search` (binary args: `["start"]`).
3. Poll up to 10×0.5s for daemon health, re-resolving the dynamic port each iteration.
4. Run `trusty-search index <project_root>` (timeout 120s, non-fatal if slow).
5. Write `.mcp.json` entry `{"type":"stdio","command":"trusty-search","args":["serve"]}` inside `_mcp_config_transaction`.
6. Inject `PostToolUse` hook via `_inject_trusty_hooks(["trusty-search"])`.

**`_setup_trusty_memory` flow** (lines 649–836):
1. Install `trusty-memory` binary via cargo.
2. Run `trusty-memory status` (5s timeout, guarded against `TimeoutExpired`); HTTP health-check fallback.
3. If unhealthy, write and load launchd plist `com.bobmatnyc.trusty-memory` (binary args: `["serve"]`).
4. Create palace via REST `POST /api/v1/palaces` with name = `Path.cwd().name`; check `GET /api/v1/palaces` first.
5. Write `.mcp.json` entry `{"type":"stdio","command":"trusty-memory-mcp-bridge","args":[]}` inside `_mcp_config_transaction`.
6. Inject `SessionStart/Stop/SubagentStop` hooks via `_inject_trusty_hooks(["trusty-memory"])`.

**`_setup_trusty_analyze` flow** (lines 838–917):
1. Install `trusty-analyzer` binary via cargo.
2. HTTP health-check `127.0.0.1:7879/health` (hardcoded — no dynamic discovery).
3. If unhealthy, write and load launchd plist `com.bobmatnyc.trusty-analyzer`.
4. Write `.mcp.json` entry `{"type":"stdio","command":"trusty-analyzer","args":["mcp"]}`.
5. No hook injection for trusty-analyzer.

**`migrate_trusty_autodetect.py`** — `run_migration(project_dir)` (lines 133–191):
- Module-level `_SERVICES` tuple (lines 51–74) defines trusty-search and trusty-memory with their binary names, addr files, fallback addrs, and target `.mcp.json` entries.
- On each startup: `shutil.which` per binary; HTTP health probe to `/health`; if healthy and the `mcpServers` key is absent, writes the entry inside `_mcp_config_transaction`.
- Returns `True` if any entry was written; registered as `run_always=True` in the migration registry.

### WHY

- **Dynamic port discovery** was introduced because `trusty-search` (issue #56 in trusty-search repo) switched to OS-chosen ports written to `~/.trusty-search/http_addr`. Hardcoding `7878`/`7070` caused silent failures.
- **Launchd persistence** (macOS `KeepAlive=true`) ensures the daemon auto-restarts on crash and survives reboots.
- **Atomic JSON writes** prevent Claude Code hook failures from a partial settings.json write.
- **Idempotent injection** (`_mpm_service` dedup key) lets `claude-mpm setup` be re-run safely without duplicate hooks.
- **Legacy cleanup** (`_LEGACY_SERVICES`) removes predecessor hooks (`kuzu-memory`, `mcp-vector-search`) automatically when trusty services are set up.
- **`run_always` autodetect** means users who install trusty-search/trusty-memory after their first `claude-mpm` run get the MCP entry automatically on the next session.

### DRIFT

- **Trusty-memory MCP command mismatch vs docs** (`docs/developer/memory-integration.md` line ~57): the in-repo docs show `"command": "trusty-memory", "args": ["mcp"]` but the actual setup code writes `"command": "trusty-memory-mcp-bridge", "args": []` (trusty.py line 815–819, migrate_trusty_autodetect.py line 67–71). The docs reflect a broken earlier version that migration `fix_trusty_memory_bridge` (v6.5.0) was specifically written to repair (issue #567).
- **Trusty-analyzer has no dynamic port discovery** (hardcoded `127.0.0.1:7879`) while trusty-search and trusty-memory both use `http_addr` files. This is an inconsistency within the codebase itself, not just against docs.
- **CLAUDE.md does not mention trusty integrations** at all. The setup handlers, hook injection patterns, launchd management, and palace creation are entirely absent from the project-level CLAUDE.md.
- **Kuzu-memory setup handler still exists** at `src/claude_mpm/cli/commands/setup/handlers/kuzu_memory.py` with a full `KuzuMemoryMixin._setup_kuzu_memory` implementation. Issue #523 implies kuzu is replaced, but the setup code for it is live code, not archived.

---

## 2. MCP Config Builder

**Primary file:** `src/claude_mpm/services/mcp/config_builder.py` — EXISTS

### WHAT

`MCPServiceConfigBuilder` class (line 24) provides static template configs and detection-based fallback generation for MCP services.

**`STATIC_MCP_CONFIGS` dict** (lines 33–71) — known-good entries for seven services:

| Service | Command | Args |
|---------|---------|------|
| `kuzu-memory` | `kuzu-memory` (resolved to path) | `["mcp", "serve"]` |
| `mcp-ticketer` | `mcp-ticketer` (resolved to path) | `["mcp"]` |
| `mcp-browser` | `mcp-browser` (resolved to path) | `["mcp"]` |
| `mcp-vector-search` | `python` / pipx fallback | `["-m", "mcp_vector_search.mcp.server", "{project_root}"]` |
| `trusty-search` | `trusty-search` | `["serve"]` |
| `trusty-memory` | `trusty-memory-mcp-bridge` | `[]` |
| `trusty-analyzer` | `trusty-analyzer` | `["mcp"]` |

**`get_static_service_config(service_name, project_path)` (lines 113–237):**
- Copies the static entry.
- For `kuzu-memory`, `mcp-ticketer`, `mcp-browser`: attempts to resolve the binary through pipx venv path (`~/.local/pipx/venvs/<name>/bin/<name>`) then `shutil.which` then known paths; falls back to `pipx run`.
- For `mcp-vector-search`: resolves python binary from the pipx venv; substitutes `{project_root}` in args.
- For trusty services: returns the static entry unchanged (no binary path resolution).

**`test_service_command(service_name, config)` (lines 239–312):** Runs `--help` on the configured command (5s timeout); returns `True` if exit code 0 or 1 with no import errors.

**`generate_service_config(service_name)` (lines 314–466):** Priority chain:
1. `get_static_service_config` + `test_service_command` validation.
2. If static fails: try `pipx run <service> --version` (5s); if OK, use `pipx run` form.
3. If pipx fails: try `uvx <service> --version` (5s); if OK, use `uvx` form.
4. If all fail: `locator.detect_service_path(service_name)`.

**`get_fallback_config(service_name, project_path)` (lines 468–494):** Currently only handles `mcp-vector-search` (returns pipx run form).

### WHY

Extracted from a `MCPConfigManager` god-class (issue #507 referenced in the module docstring). Separating config generation from installation and file management reduces coupling and makes each concern independently testable.

Static configs are preferred because dynamically detecting binary paths is fragile (PATH can vary, pipx paths can change between Python versions). The static-first strategy means a known-good config is validated before any fallback probes run.

### DRIFT

- `kuzu-memory` remains in `STATIC_MCP_CONFIGS` (line 34) even though the project's direction is to replace it with trusty-memory. The service is not marked deprecated or conditional.
- `mcp-vector-search` similarly remains with full static config despite trusty-search being the intended replacement. Issue #523 references these as legacy services but no removal has occurred.
- The `trusty-analyzer` entry in `STATIC_MCP_CONFIGS` (line 66) does not have binary path resolution logic (unlike the pipx-installed services), so if `trusty-analyzer` is not on PATH, `test_service_command` will silently fail and fall through to detection.
- CLAUDE.md and in-repo docs do not document this builder class at all.

---

## 3. MCP Service Installer

**Primary file:** `src/claude_mpm/services/mcp/service_installer.py` — EXISTS

### WHAT

`MCPServiceInstaller` class (line 25) installs missing MCP services using pipx (preferred), uvx, or `pip install --user`.

**Service classification** (lines 29–51):

```python
PIPX_SERVICES = {"mcp-vector-search", "mcp-browser", "mcp-ticketer", "kuzu-memory"}
CARGO_SERVICES = {"trusty-search", "trusty-memory", "trusty-analyzer"}
SERVICE_MISSING_DEPENDENCIES = {"mcp-ticketer": ["gql"]}
```

`CARGO_SERVICES` is defined but **not used** by `install_missing_services` (line 63) — only `PIPX_SERVICES` are auto-installed. Trusty services require `TrustyMixin._install_cargo_binary` from the setup handler.

**`install_missing_services()` flow** (lines 63–93):
1. Detect which `PIPX_SERVICES` are absent via `locator.detect_service_path`.
2. For each missing service: run `_install_service_with_fallback`.
3. Return `(True, summary)` or `(False, failed_list)`.

**`_install_service_with_fallback(service_name)` (lines 95–172):**
1. `pipx install <service>` (120s timeout); on success, call `inject_missing_dependencies` then `_verify_service_installed`.
2. `uvx install <service>` fallback.
3. `pip install --user <service>` fallback.

**`inject_missing_dependencies(service_name)` (lines 174–230):** Runs `pipx inject <service> <dep>` for each dep in `SERVICE_MISSING_DEPENDENCIES`. Currently only `mcp-ticketer` → `gql`.

**`_verify_service_installed(service_name, method)` (lines 232–294):** Sleeps 1s then checks `locator.detect_service_path`; falls back to `pipx run <service> --version`; runs `--version`/`--help` test.

### WHY

Extracted from the same `MCPConfigManager` god-class (issue #507). Isolation allows testing installation logic independently and makes fallback chains explicit rather than buried in a single large class.

The 1-second sleep in `_verify_service_installed` (line 242) is a pragmatic workaround for pipx needing time to symlink executables into `~/.local/bin/`.

### DRIFT

- `CARGO_SERVICES` set is defined but has no corresponding `install_missing_cargo_services` method. The installer effectively ignores trusty services, and any code relying on this class to install trusty-search or trusty-memory will find them unsupported.
- `kuzu-memory` is still in `PIPX_SERVICES`, implying it is still a managed, auto-installed dependency. Issue #523's claim that "the project has migrated toward trusty-memory" is not reflected in the installer's service set.

---

## 4. Memory Enrichment — UserPromptSubmit

**Primary files (per issue #523 scope):**  
- `src/claude_mpm/hooks/memory_integration_hook.py` — EXISTS (but handles pre/post delegation, NOT UserPromptSubmit)
- `src/claude_mpm/hooks/kuzu_enrichment_hook.py` — EXISTS

**Actual UserPromptSubmit handler:**  
- `src/claude_mpm/hooks/memory_capture.py` — ALSO EXISTS (the module the #523 scope did not list)

### WHAT

**`memory_integration_hook.py` — Delegation-level memory (not UserPromptSubmit):**

This file contains `MemoryPreDelegationHook` (line 62) and `MemoryPostDelegationHook` (line 208). These are `PreDelegationHook` and `PostDelegationHook` subclasses — they fire around agent-to-agent delegation, not around user prompts. They operate through the MPM Python hook framework (`base_hook.HookContext`), not through Claude Code's `settings.json` hook events.

- `MemoryPreDelegationHook.execute` (line 107): Loads agent-specific memory from `AgentMemoryManager.load_agent_memory(agent_id)` and injects it as `"agent_memory"` key in the delegation context dict.
- `MemoryPostDelegationHook.execute` (line 276): Calls `_extract_learnings(result_text)` which matches `# Add To Memory: / # Memorize: / # Remember:` blocks (regex line 381) with `Type:` and `Content:` fields; stores via `AgentMemoryManager.add_learning(agent_id, type, content)`.
- Memory entries are capped at 5–100 characters (line 410).
- Both hooks gracefully degrade when `AgentMemoryManager` import fails (lines 32–39).

**`kuzu_enrichment_hook.py` — Kuzu-specific delegation enrichment:**

`KuzuEnrichmentHook(PreDelegationHook)` (line 29): Priority 10. On construction, calls `get_kuzu_memory_hook()` to get a `KuzuMemoryHook` singleton. Enabled only if `kuzu-memory` binary is found on PATH or in pipx. Calls `kuzu_hook._retrieve_memories(query)` which shells out to `kuzu-memory memory recall <query> --format json` (5s timeout). Injects result as `"=== RELEVANT KNOWLEDGE FROM KUZU MEMORY ==="` section into delegation context.

**`memory_capture.py` — The ACTUAL UserPromptSubmit handler (not listed in issue #523 scope):**

This module (831 lines) is the real `UserPromptSubmit` enrichment hook and is invoked by Claude Code's hook system directly (not the Python delegation framework). It implements:

- `AbstractMemoryCaptureBackend` ABC with `is_available()`, `store()`, `recall()` methods (line 169).
- `TrustyMemoryBackend` (line 296): HTTP-first store to `POST /api/v1/palaces/<palace>/drawers` (200ms timeout); falls back to `trusty-memory remember --palace <palace> <fact>` CLI (2s timeout). Recall via `GET /api/v1/palaces/<palace>/recall?q=<query>&limit=5` (800ms timeout); falls back to `trusty-memory recall --palace <palace> <query>` CLI.
- `KuzuMemoryBackend` (line 440): `kuzu-memory memory learn <fact> --no-wait` (2s timeout); recall via `kuzu-memory recall <query>` (2s timeout).
- `_select_backend()` (line 497): tries trusty-memory first; falls back to kuzu-memory; returns `None` if neither available. Cached at module import time (`_BACKEND` line 513).
- `handle_user_prompt_submit(event)` (line 672): recalls from backend (synchronous, 800ms cap), fires background store on daemon thread, injects results via `hookSpecificOutput.additionalContext`.
- `main()` (line 780): reads stdin with `select.select(timeout=1.0)`, dispatches on `hook_event_name`: `SessionStart → _handle_session_start`, `PostToolUse → _handle_post_tool_use`, `Stop/SubagentStop → _handle_session_end`, `UserPromptSubmit → handle_user_prompt_submit`.

The `_handle_post_tool_use` within `memory_capture.py` captures file paths (Write/Edit/NotebookEdit/MultiEdit) and git commit messages from Bash tool calls.

### WHY

- `memory_integration_hook.py` serves the Python-level agent delegation pipeline. It uses file-based `AgentMemoryManager` (markdown files at `.claude-mpm/memories/<agent-id>.md`) to give each subagent its accumulated project-specific learnings.
- `kuzu_enrichment_hook.py` is a companion for the kuzu-memory graph backend, also at the delegation level.
- `memory_capture.py` serves the Claude Code hook event pipeline — a fundamentally different invocation path. It handles raw Claude Code hook events (stdin JSON) rather than the Python delegation context.

The separation exists because enriching Claude Code prompts (UserPromptSubmit) requires being a Claude Code hook process (invoked by the hook dispatcher), while enriching delegated agents requires being part of the MPM orchestration layer.

### DRIFT

- **Issue #523 scope mismatch**: The scope table lists `memory_integration_hook.py` and `kuzu_enrichment_hook.py` as the "Memory enrichment (UserPromptSubmit)" components, but neither handles `UserPromptSubmit`. `memory_integration_hook.py` handles delegation pre/post hooks. The actual `UserPromptSubmit` hook is `memory_capture.py`, which is NOT listed in issue #523's scope table.
- **`memory_capture.py` was supposedly removed** (migration `remove_memory_capture_hook` v6.4.9 references: "module moved to trusty-memory, issue #555"). However, the file EXISTS at full 831 lines and is the active UserPromptSubmit handler. The migration only removes stale `_mpm_service: "memory-capture"` hook entries from `settings.json`; it does NOT delete the Python module. The module reference in the migration description ("module moved to trusty-memory") is misleading — the module was not moved, it was renamed/refactored to serve as a multi-backend dispatcher supporting trusty-memory as the preferred backend with kuzu-memory as fallback.
- **`memory_integration_hook.py` has a bug at line 173**: `datetime.now(datetime.UTC)` should be `datetime.now(datetime.timezone.utc)` or `datetime.now(UTC)` — `datetime.UTC` is not an attribute of `datetime` (it's `datetime.timezone.utc` or the standalone `UTC` from `datetime` module). This will raise `AttributeError` at runtime when the EventBus publish path is hit.

---

## 5. Memory Session Persistence — Stop / SubagentStop

**Primary files (per issue #523 scope):**  
- `src/claude_mpm/hooks/kuzu_response_hook.py` — EXISTS
- `src/claude_mpm/hooks/kuzu_memory_hook.py` — EXISTS

### WHAT

**`kuzu_memory_hook.py` — Base kuzu-memory hook (SubmitHook):**

`KuzuMemoryHook(SubmitHook)` (line 37): Priority 10. Fires on prompt submission (not Stop). Internally:
- `_detect_kuzu_memory()` (line 74): checks `~/.local/pipx/venvs/kuzu-memory/bin/kuzu-memory` then `shutil.which("kuzu-memory")`.
- `execute()` (line 107): retrieves memories for the prompt via `_retrieve_memories(query)`, enriches the prompt data dict.
- `_retrieve_memories(query)` (line 160): runs `kuzu-memory memory recall <query> --format json` (5s timeout). Parses response handling both `{"memories": [...]}` dict form and array form.
- `store_memory(content, tags)` (line 273): uses `subprocess.Popen` with `kuzu-memory memory learn <content> --no-wait` and `start_new_session=True` (fire-and-forget).
- `extract_and_store_learnings(text)` (line 313): regex extraction using `memory_patterns` (`# Remember:`, `Important:`, `Learned:`, etc.) against raw text.

**`kuzu_response_hook.py` — Post-delegation response learning:**

`KuzuResponseHook(PostDelegationHook)` (line 29): Priority 80. Fires after agent delegation completes (not Stop). Reuses `KuzuMemoryHook` singleton for storage:
- `execute()` (line 79): extracts response content from various formats (dict, string, list).
- Calls `kuzu_hook.extract_and_store_learnings(response_content)` which extracts patterns and calls `store_memory` for each.

**The actual Stop/SubagentStop persistence path:**

The hooks registered for `Stop` and `SubagentStop` events in Claude Code settings are `claude-hook` commands tagged `_mpm_service: "trusty-memory"`. The actual Stop handler is inside `memory_capture.py`'s `main()` dispatcher which routes `Stop/SubagentStop` to `_handle_session_end` — storing `"Session ended in <project>"` with `["session-end", project]` tags into the active backend (trusty-memory or kuzu-memory).

### WHY

- `kuzu_memory_hook.py` and `kuzu_response_hook.py` implement the kuzu-memory READ (enrichment) and WRITE (learning extraction) cycle at the delegation layer. These were designed when kuzu-memory was the primary backend for graph-based memory.
- The trusty-memory migration shifted the Stop/SubagentStop capture to `memory_capture.py` which treats trusty-memory as the preferred backend and kuzu-memory as fallback.

### DRIFT

- **Issue #523 classifies these as "Memory session persistence (Stop)" but neither hook fires on the Claude Code `Stop` event.** `KuzuMemoryHook` is a `SubmitHook` (user prompt submission), and `KuzuResponseHook` is a `PostDelegationHook` (fires after agent-to-agent delegation). The actual `Stop` event persistence is in `memory_capture.py` via the `_handle_session_end` function.
- **Both kuzu hook files reference the MPM Python delegation framework** (`HookContext`, `PreDelegationHook`, `PostDelegationHook` from `base_hook`) — not Claude Code's settings.json hook events. They are internal MPM pipeline hooks, not external Claude Code hooks.
- **`kuzu_memory_hook.py` docstring states** (line 21): "NOTE: As of v4.8.6, kuzu-memory is a required dependency" — but kuzu-memory is demonstrably NOT required; the `_detect_kuzu_memory` check at line 54 shows it gracefully disables itself when absent. This comment is stale and incorrect.
- **The trusty-memory `SessionStart/Stop/SubagentStop` hooks** installed by `_setup_trusty_memory` fire `claude-hook` (the generic MPM hook dispatcher). The actual memory-capture work (storing session facts) is done by `memory_capture.py` running under that dispatcher — but the dispatcher routes to modules based on the hook event name, and `memory_capture.py` must be registered as the handler. The registration path is through `claude-hook-fast.sh`/`claude-hook` scripts, not documented in CLAUDE.md.

---

## 6. Migrations System

**Primary files:**  
- `src/claude_mpm/migrations/registry.py` — EXISTS  
- `src/claude_mpm/migrations/runner.py` — EXISTS

### WHAT

**`runner.py` — State management and execution:**

- `STATE_FILE = Path.home() / ".claude-mpm" / "migrations.json"` (line 17): global (not project-scoped) completion tracking.
- `_load_state()` / `_save_state(state)` (lines 20–44): simple JSON dict with `{"completed": [...ids], "last_version": "..."}`.
- `get_pending_migrations()` (lines 47–60): returns migrations where `run_always=True` OR `id not in completed`.
- `run_pending_migrations(current_version)` (lines 82–146):
  - Iterates pending migrations in registry order.
  - `run_always` migrations: run every startup, never persisted to completed, stdout suppressed for no-op runs.
  - One-shot migrations: only call `mark_migration_complete` when `run() → True`.
  - Both types: exceptions are caught, logged, and printed; other migrations continue.
  - Returns count of migrations that returned `True`.
- `get_migration_status()` (lines 149–163): diagnostic view of completed/pending/total.

**`registry.py` — Migration catalog:**

23 registered migrations in `MIGRATIONS: list[Migration]` (line 221), spanning versions 5.6.91 through 6.5.0:

| ID | Version | Description | run_always |
|----|---------|-------------|-----------|
| `5.6.91_async_hooks` | 5.6.91 | Migrate hooks to async execution | No |
| `5.6.95_coauthor_email` | 5.6.95 | Update Co-Authored-By email | No |
| `5.9.48_remove_unsupported_hooks` | 5.9.48 | Remove v2.1.47+ hook events on old installs | No |
| `5.12.0_binary_consolidation` | 5.12.0 | Migrate .mcp.json to `claude-mpm mcp serve` format | No |
| `6.1.0_core_skills_to_user_level` | 6.1.0 | Move mpm-* skills to user level | No |
| `6.2.0_core_agents_to_user_level` | 6.2.0 | Move agents to user level | No |
| `6.2.1_overlap_cleanup` | 6.2.1 | Archive project-level duplicates | No |
| `6.3.0_native_agent_fields` | 6.3.0 | Add Claude Code native frontmatter fields | No |
| `6.3.0_create_commands_dir` | 6.3.0 | Create .claude/commands/ templates | No |
| `v6_3_1_deploy_claude_assets` | 6.3.1 | Deploy statusline.sh and settings.json | No |
| `v6_3_2_agent_color_prompt` | 6.3.2 | Inject color field in agent frontmatter | No |
| `v6_3_2_additional_directories` | 6.3.2 | Add additionalDirectories to settings | No |
| `v6_3_2_permission_request_hook` | 6.3.2 | Add PermissionRequest hook | No |
| `v6_2_35_statusline_autoconfig` | 6.2.35 | Auto-configure statusline | No |
| `v6_3_2_statusline_user_level` | 6.3.2 | Move statusline to user level | No |
| `trusty_autodetect` | 6.3.10 | Auto-detect trusty-search/memory daemons | **Yes** |
| `v6_3_19_hooks_to_project_level` | 6.3.19 | Move hooks to project settings.json | No |
| `check_migration_skills` | 6.4.1 | Detect pending migration skill wizards | **Yes** |
| `fix_mcp_command_args` | 6.4.2 | Fix MCP configs with spaces in command | No |
| `remove_memory_capture_hook` | 6.4.9 | Remove stale memory_capture hook entries | No |
| `v6_4_18_remove_absolute_hook_paths` | 6.4.18 | Replace absolute hook paths with `claude-hook` | No |
| `fix_trusty_memory_bridge` | 6.5.0 | Repair broken trusty-memory MCP entries | No |

Note: `fix_mcp_command_args` and `fix_trusty_memory_bridge` are one-shot migrations that return `False` on a clean system (repair-if-needed, not guaranteed to run to completion). They re-run every startup until they find nothing to fix — effectively acting as quasi-run_always but using the completion gate.

**`Migration` NamedTuple** (lines 12–26):
```python
class Migration(NamedTuple):
    id: str
    version: str
    description: str
    run: Callable[[], bool]
    run_always: bool = False
```

### WHY

- Global state file (`~/.claude-mpm/migrations.json`) rather than per-project: migrations are user-level infrastructure changes (agent deployment, hook injection, settings manipulation), not project-specific transformations.
- `run_always` for `trusty_autodetect` and `check_migration_skills` because these are environment probes that must re-run each session (daemon state can change between runs).
- Silent no-op behavior (issue #595): printing "Running migration..." or "Skipped" on every startup for clean systems was noisy. Only applied changes and genuine failures produce output.

### DRIFT

- **CLAUDE.md documents only**: "Migrations run automatically on startup via `run_pending_migrations()`. State tracked in `~/.claude-mpm/migrations.json`." The actual 23-entry catalog, `run_always` semantics, and repair-migration pattern (returning `False` until no-op) are absent.
- **ID/version mismatch** in the registry: `v6_2_35_statusline_autoconfig` is registered at version `"6.2.35"` but its `id` is `"v6_2_35_statusline_autoconfig"` — version-string inconsistency (other IDs at v6.3.2 use the id prefix `"v6_3_2_"`).
- **`fix_mcp_command_args` and `fix_trusty_memory_bridge` are scan-and-repair migrations** that return `False` when nothing needs fixing. Since `mark_migration_complete` only fires on `True`, these would re-run on every startup until they find and fix something — but once a clean system is achieved they silently no-op without completing. This means they are effectively permanently pending in `migrations.json` on clean installs, which inflates the "pending" count in `get_migration_status()` without representing actual work.
- **`_run_hooks_to_project_level_migration` wrapper** is decorated with `pyright: ignore[unused-function]` (line 209) yet the migration IS registered in MIGRATIONS at line 323. The Pyright comment is incorrect — the function is used.

---

## 7. Dashboard / UI Service

**Primary files:**  
- `src/claude_mpm/services/ui_service/app.py` — EXISTS  
- `src/claude_mpm/services/ui_service/routers/` (12 router files) — EXIST  
- `src/claude_mpm/services/ui_service/serve_daemon.py` — EXISTS

Note: `docs/developer/11-dashboard/` directory exists but contains only a stub `README.md`.

### WHAT

**`app.py` — FastAPI application factory:**

`create_app(service_config)` (line 53):
- Instantiates `FastAPI` with title `"claude-mpm UI Service"`, docs at `/api/v1/docs`, OpenAPI at `/api/v1/openapi.json`.
- Stores `UIServiceConfig` and `ProcessManager` on `app.state`.
- Configures `CORSMiddleware`: `allow_origins = cfg.cors_origins`, regex `http://(localhost|127\.0\.0\.1)(:\d+)?`, credentials allowed.
- Registers 12 routers under `/api/v1` prefix.
- Defines WebSocket endpoint `GET /api/v1/ws/sessions/{session_id}` (line 110): bidirectional; client sends `{"type":"message"|"interrupt"|"command"}` JSON; server streams `StreamEvent` objects.
- `GET /api/v1/health` returns `{"status":"healthy","active_sessions":N}`.

**`UIServiceConfig` (config.py):**

Dataclass with env-var loading (`from_env()`):

| Field | Default | Env Var |
|-------|---------|---------|
| `host` | `127.0.0.1` | `CLAUDE_MPM_UI_HOST` |
| `port` | `7777` | `CLAUDE_MPM_UI_PORT` |
| `max_sessions` | `10` | `CLAUDE_MPM_UI_MAX_SESSIONS` |
| `session_timeout_minutes` | `60` | `CLAUDE_MPM_UI_SESSION_TIMEOUT` |
| `cors_origins` | localhost/127.0.0.1 | `CLAUDE_MPM_UI_CORS_ORIGINS` |
| `global_sessions_dir` | `~/.claude-mpm/sessions` | `CLAUDE_MPM_UI_SESSIONS_DIR` |

**Registered routers and their routes:**

| Router file | Prefix | Key endpoints |
|-------------|--------|---------------|
| `sessions.py` | `/sessions` | CRUD sessions, fork, interrupt, plan-mode |
| `messages.py` | `/messages` | Send/stream messages to sessions |
| `auth.py` | `/auth` | Auth token management |
| `models.py` | `/models` | List available Claude models |
| `config.py` | `/config` | Read/update service config |
| `permissions.py` | `/permissions` | Permission mode management |
| `hooks.py` | `/hooks` | List/manage Claude Code hooks |
| `mcp.py` | `/mcp` | List MCP servers from .mcp.json |
| `commands.py` | `/commands` | List/execute slash commands |
| `memory.py` | `/memory` | Memory read/write operations |
| `tools.py` | `/tools` | Tool call execution |
| `diagnostics.py` | `/diagnostics` | System health checks |

**Sessions router key behavior:**
- `POST /sessions`: calls `pm.create_session(body)` which spawns a `claude --output-format stream-json` subprocess.
- `GET /sessions/{id}/ws` is actually at `/api/v1/ws/sessions/{id}` (defined in app.py, not sessions router).
- Plan mode, fork, interrupt all send CLI commands or signals to the subprocess.

**`serve_daemon.py` — Daemon lifecycle:**

`ServeDaemon` (line 54): Public API: `start(force_restart)`, `stop()`, `restart()`, `status()`.

`_ServeDaemonManager(DaemonManager)` (line 226): Overrides `start_daemon_subprocess()` to launch:
```
python -m claude_mpm.cli serve start --background --port N --host H [--channels ...] [--project-root ...]
```
- Env var `CLAUDE_MPM_SERVE_DAEMON=1` breaks recursion.
- PID file at `~/.claude-mpm/serve-<port>.pid`.
- Logs at `~/.claude-mpm/logs/serve-<port>.log`.
- Waits up to 30s (configurable via `CLAUDE_MPM_SERVE_TIMEOUT`) for PID file + port binding.
- Optional `ChannelHub` integration: when `--channels` specified, `uvicorn.serve()` and `hub.start()` run concurrently via `asyncio.gather`.

`_patch_health_endpoint(app)` (line 376): Adds bare `/health` (not under `/api/v1`) returning `{"service":"claude-mpm-serve","status":"healthy"}` for `DaemonManager.is_our_service()` compatibility.

**`ProcessManager` (process_manager.py):**

Key behaviors (from structure grep):
- `ManagedSession` dataclass: holds session id, model, permission_mode, subprocess handle, `asyncio.Queue` for output, message history.
- `create_session(config)`: spawns `claude --output-format stream-json` subprocess; persists session state to `~/.claude-mpm/sessions/<id>.json`.
- `send_message(session_id, content)`: `AsyncIterator[StreamEvent]` — writes to subprocess stdin and yields parsed NDJSON events.
- `interrupt(session_id)`: sends `SIGINT`.
- Sessions persist across serve daemon restarts via `_persist_session` / `_load_persisted_sessions`.
- `_cleanup_loop`: background task that evicts timed-out sessions.

### WHY

- FastAPI was chosen for full async support (streaming NDJSON from Claude subprocess), WebSocket support, and automatic OpenAPI docs.
- The daemon pattern (PID file + subprocess recursion prevention) mirrors the monitor daemon, enabling `claude-mpm serve start/stop/status` CLI parity with `claude-mpm monitor start/stop/status`.
- Session persistence (`~/.claude-mpm/sessions/`) allows `claude-mpm serve` to survive daemon restarts without losing active session context (users can resume via `POST /sessions` with `resume_id`).

### DRIFT

- **`docs/developer/11-dashboard/README.md` is a stub** — contains no actual content. The Dashboard subsystem is completely undocumented despite being a substantial (1,447 lines across 12 router files + process_manager + serve_daemon).
- **CLAUDE.md does not mention the UI service** at all — no port, no API prefix, no serve command.
- **Default port 7777** is not documented anywhere in CLAUDE.md or architecture docs.
- **WebSocket endpoint** (`/api/v1/ws/sessions/{id}`) is defined inline in `app.py` (not a router), making it invisible to documentation generators that scan router files.
- **ChannelHub integration** (`_serve_with_channels`) is referenced in `serve_daemon.py` but `ChannelHub` is imported with `type: ignore[import-not-found]`, suggesting it is an optional or not-yet-deployed module.

---

## 8. Drift Summary

**5 most significant drift findings:**

1. **Kuzu-memory is NOT removed — it is the active fallback backend.** Issue #523 implies the project "has migrated toward trusty-memory" and uses "kuzu_*" terminology for legacy hooks. The actual state: kuzu-memory hooks (`kuzu_memory_hook.py`, `kuzu_enrichment_hook.py`, `kuzu_response_hook.py`) are all live code; `kuzu-memory` is in `PIPX_SERVICES` (auto-installed), `STATIC_MCP_CONFIGS` (config builder), and `KuzuMemoryBackend` in `memory_capture.py` is the active fallback when trusty-memory is unreachable. Kuzu is not deprecated — it is a fallback tier.

2. **`memory_capture.py` was not "moved to trusty-memory."** Migration `remove_memory_capture_hook` (v6.4.9) describes itself as "module moved to trusty-memory, issue #555" but the module exists at full 831 lines and is the active `UserPromptSubmit`/`SessionStart`/`Stop`/`SubagentStop` handler. What was removed is the hook registration in `settings.json`; the module remains and does both trusty-memory (primary) and kuzu-memory (fallback) capture.

3. **The `memory_integration_hook.py` and `kuzu_enrichment_hook.py` files are NOT UserPromptSubmit handlers.** Issue #523's scope table lists these under "Memory enrichment (UserPromptSubmit)" — but both are Python-level delegation hooks (`PreDelegationHook`, `PostDelegationHook`, `SubmitHook`) that fire around MPM agent-to-agent delegation, not around Claude Code's `UserPromptSubmit` event. The actual `UserPromptSubmit` handler is `memory_capture.py`.

4. **Trusty-memory MCP command in docs differs from code.** `docs/developer/memory-integration.md` shows `"command": "trusty-memory", "args": ["mcp"]` but every code path that writes the MCP entry uses `"command": "trusty-memory-mcp-bridge", "args": []` (trusty.py line 815, autodetect line 67, config_builder line 62). The docs describe the broken form that migration `fix_trusty_memory_bridge` (v6.5.0) exists to repair.

5. **Scan-and-repair migrations inflate the "pending" count permanently on clean installs.** Migrations `fix_mcp_command_args` and `fix_trusty_memory_bridge` return `False` when nothing needs fixing (idempotent probes), so they are never added to `migrations.json["completed"]`. Every `get_migration_status()` call on a clean system reports these as pending, even though they represent no real pending work. This is a semantic misuse of the one-shot migration model; they should either be `run_always=True` or be registered with a completion sentinel that fires on the first clean-scan pass.

---

**Components documented:** 7 (Trusty Setup, Autodetect Migration, MCP Config Builder, MCP Service Installer, Memory Enrichment, Memory Persistence, Migrations System, Dashboard/UI Service — counting Dashboard as one component covering app + routers + serve_daemon).

**Total migration entries cataloged:** 23 registered migrations from v5.6.91 to v6.5.0.
