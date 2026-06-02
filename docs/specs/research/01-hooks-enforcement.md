# Hooks & Enforcement Subsystem — Ground-Truth Specification

**Research date:** 2026-06-01  
**Scope:** Issue #523 cross-reference table — Hooks & Enforcement  
**Method:** Direct code inspection; every claim cites exact file and line.

---

## Table of Contents

1. [Hook Relay / Dispatcher](#1-hook-relay--dispatcher)
2. [Hook Wiring / settings.json](#2-hook-wiring--settingsjson)
3. [Hook Event Handlers](#3-hook-event-handlers)
4. [Hook Event Services](#4-hook-event-services)
5. [Circuit Breaker](#5-circuit-breaker)
6. [Model Tier Enforcement](#6-model-tier-enforcement)
7. [Permission Gate](#7-permission-gate)
8. [Component Map (Quick Reference)](#8-component-map-quick-reference)

---

## 1. Hook Relay / Dispatcher

### Files verified to exist

| Path | Role |
|------|------|
| `src/claude_mpm/scripts/claude-hook-fast.sh` | Ultra-fast bash relay (primary for all events) |
| `src/claude_mpm/scripts/claude-hook-handler.sh` | Python environment resolver; invokes `hook_handler.py` |
| `src/claude_mpm/hooks/pretooluse_dispatcher.py` | Consolidated PreToolUse/PermissionRequest Python dispatcher |

### 1a. `claude-hook-fast.sh`

**WHAT**

Version 2.1 (line 34). Reads all stdin into `$INPUT` at startup (line 38), then processes without re-reading. Key behaviors:

- **Event extraction** (lines 61–88): pure-bash `_extract_json_str` helper handles both compact (`"key":"value"`) and spaced (`"key": "value"`) JSON. Tries `hook_event_name` first, falls back to `event` field.
- **WorktreeCreate handler** (lines 101–174): runs *before* the sub-agent early-exit guard. Sanitizes the `name` slug, determines `REPO_ROOT` from the `cwd` field, creates a sibling directory `<parent>/<repo-name>-worktrees/<slug>`. Three attempts: (1) `git worktree add` with new branch, (2) without new branch, (3) re-use existing path. Prints the absolute worktree path on success; exits 1 on failure.
- **WorktreeRemove handler** (lines 187–211): runs before the sub-agent guard. Runs `git -C "$REPO_ROOT" worktree remove --force "$WORKTREE_PATH"`. Always emits `{"continue": true}`.
- **Sub-agent early exit** (lines 217–220): if `CLAUDE_MPM_SUB_AGENT` is set, emits `{"continue": true}` and exits immediately for all non-worktree events.
- **Event routing** (lines 225–235): maps Claude Code event names to `SUBTYPE` strings for dashboard compatibility (`PreToolUse` → `pre_tool`, etc.).
- **Dashboard POST** (lines 277–296): fire-and-forget `curl` to `http://localhost:${CLAUDE_MPM_SOCKETIO_PORT:-8765}/api/events` with `--connect-timeout 0.2 --max-time 0.3`. Runs in background (`&`).
- **Response shape** (lines 319–329): PreToolUse and PermissionRequest return `{"continue": true}` synchronously (decision events). All other events return `{"async": true, "asyncTimeout": 60000}`.

**WHY**

Designed to reduce hook latency from ~450 ms (Python startup) to ~15 ms. It handles only observability (fire-and-forget dashboard forwarding) and two special structural events (WorktreeCreate/Remove). Decision logic lives in separate Python hooks wired independently.

**DRIFT**

- CLAUDE.md (line 98) identifies this as "Shell hook dispatcher (`claude-hook-fast.sh`)" under `scripts/` — **correct** path.
- CLAUDE.md (line 123) calls it the "Hook dispatcher" — accurate but incomplete: it does not replace the Python handler; both coexist in `settings.json` for most events.
- The script comment at line 309 explicitly notes that `{"async": true}` is *wrong* for PreToolUse/PermissionRequest — but the *actual* settings.json wires this script for PreToolUse with a 15 s timeout entry (see Section 2), meaning the script is invoked first but any decision logic relies on the second Python hook entry in the same hook array. This dual-hook pattern is not documented in CLAUDE.md or any in-repo prose doc.
- `WorktreeCreate` and `WorktreeRemove` handling is entirely undocumented in CLAUDE.md and the hooks README.

---

### 1b. `claude-hook-handler.sh`

**WHAT**

Version 1.0 (line 57). Responsible for locating the correct Python environment and `exec`-ing into `claude_mpm.hooks.claude_hooks.hook_handler` (lines 241–243).

- **Python resolution** (lines 124–171): priority chain — (1) `uv run` if `uv.lock` present, (2) UV tools venv, (3) pipx venv, (4) project `venv/` or `.venv/`, (5) `$VIRTUAL_ENV`, (6) `python3`, (7) `python`.
- **PYTHONPATH** (lines 177–202): appends `src/` for development installs; no-op for UV/pipx/pip.
- **Module availability check** (lines 222–234): runs `python -c "import claude_mpm"` before exec. If it fails, emits `{"continue": true}` and exits cleanly.
- **exec** (lines 241–243): replaces the shell process with `python -W ignore::RuntimeWarning -m claude_mpm.hooks.claude_hooks.hook_handler`, redirecting stderr to `/tmp/claude-mpm-hook-error.log`.

**WHY**

Needed because Claude Code invokes hooks as raw commands, so there is no guarantee the Python environment is activated. The script bridges the gap for all installation methods.

**DRIFT**

- `CLAUDE.md` does not mention `claude-hook-handler.sh` at all; it references only `claude-hook-fast.sh` as the dispatcher. The handler script is a separate, essential component that does the heavy Python processing.
- The file header says it is deployed to `~/.claude/hooks/claude-mpm/claude-hook-handler.sh` (line 22), but the actual installed path (as used in `settings.json`) is the absolute path within the package source tree or the `claude-hook` PATH entry point — the header comment describes a deployment model that does not match how it is actually wired in the current `settings.json`.

---

### 1c. `pretooluse_dispatcher.py`

**WHAT**

Consolidated dispatcher for PreToolUse and PermissionRequest events. Invocable as `python3 -m claude_mpm.hooks.pretooluse_dispatcher`.

Processing order (lines 62–95):
1. Parse event from stdin; fail-open on any parse error.
2. Route `PermissionRequest` to `model_tier_hook.build_permission_request_response()`.
3. For `PreToolUse`: run circuit breaker first; if deny, return immediately.
4. Branch on `tool_name`: `Agent` → model tier injection; `Bash` → ztk rewrite; anything else → pass-through.

**WHY**

Replaces four separate subprocess spawns per tool call with a single subprocess that calls importable functions directly. Performance goal: reduce per-tool-call overhead.

**DRIFT**

- **`pretooluse_dispatcher.py` is NOT wired in the current `settings.json`** (verified by inspecting `.claude/settings.json`). The actual settings.json wires `claude-hook` (the hook_handler entry point) twice per event — once with a 15 s timeout and once with a 60 s timeout — plus the absolute path to `claude-hook-handler.sh`. The `pretooluse_dispatcher` exists as an importable module and is used *internally* by `tool_handler.py` via direct function calls (lines 222–246 of `tool_handler.py`), but it is not registered as a standalone hook command.
- `tool_handler.py` (lines 192–246) already inlines the circuit-breaker + model-tier + ztk logic directly in `handle_pre_tool_fast()`, making `pretooluse_dispatcher.py` redundant for the actual hot path. Both paths exist in the codebase simultaneously.

---

## 2. Hook Wiring / settings.json

### File verified

`.claude/settings.json` — project-level, git-tracked.

**WHAT**

The `"hooks"` key (lines 3–186) registers hooks for these events:

| Event | Hook entries (command) | Timeout |
|-------|------------------------|---------|
| `PreToolUse` | `claude-hook` (×2) + abs path `claude-hook-handler.sh` | 15 s, 60 s, 60 s |
| `PostToolUse` | `claude-hook` (×2) + abs path `claude-hook-handler.sh` | 15 s, 60 s, 60 s |
| `PostToolUseFailure` | `python3 -m claude_mpm.hooks.tool_failure_hook` | 5 s |
| `Stop` | `claude-hook` (×2) + abs path `claude-hook-handler.sh` | 15 s, 60 s, 60 s |
| `SubagentStop` | `claude-hook` (×2) + abs path `claude-hook-handler.sh` | 15 s, 60 s, 60 s |
| `SessionStart` | `claude-hook` (×1) | 15 s |
| `UserPromptSubmit` | `claude-hook` (×2) + abs path `claude-hook-handler.sh` + `python3 -m claude_mpm.hooks.message_check_hook` | 15 s, 60 s, 60 s, 10 s |
| `PermissionRequest` | `claude-hook` (×1) | 15 s |

All entries carry `"_mpm": true` (authoritative MPM ownership marker, per comment at line 345 of `hook_installer_service.py`).

The `claude-hook` entry point resolves via pyproject.toml to `claude_mpm.hooks.claude_hooks.hook_handler:main` (pyproject.toml line 51).

**WHY**

- `claude-hook` appears twice per event because `HookInstallerService.install_hooks()` uses a merge strategy that may add duplicate entries when re-run. This is a side-effect of the idempotent merge logic.
- The absolute path `claude-hook-handler.sh` provides a fallback for environments where `claude-hook` is not on PATH.
- `PostToolUseFailure` and `message_check_hook` are separate Python invocations to handle specific concerns not covered by the main hook handler.

**DRIFT**

- **Duplicate `claude-hook` entries**: the presence of `claude-hook` twice per event (timeout 15 s and 60 s) is clearly unintentional — each invocation reads stdin, so the second invocation gets empty stdin and emits `{"continue": true}` silently. This has no functional impact (fail-open) but wastes process spawns per tool call. Undocumented and likely a regression from repeated `mpm-init` runs.
- **Absolute path in settings.json**: `.claude/settings.json` hardcodes `/Volumes/SSD1/Projects/claude-mpm/src/claude_mpm/scripts/claude-hook-handler.sh` — a machine-specific path. This is checked into git and will not work on other machines.
- **`PermissionRequest` only wires `claude-hook`** (the full Python handler) with a 15 s timeout. The `model_tier_hook.py` and `pretooluse_dispatcher.py` are not wired as separate entries — permission decisions go through `hook_handler.py` which routes them to `model_tier_hook.build_permission_request_response()` via `_route_event()`.
- **`claude-hook-fast.sh`** is NOT listed in `settings.json` at all. CLAUDE.md calls it "the" hook dispatcher, but the actual settings use `claude-hook` (Python) as the primary hook command.
- **`HookInstallerService.is_hooks_configured()`** (lines 53–100) accepts only `hook_wrapper.sh` or `claude-hook-handler.sh` as valid hook markers (line 85). It does NOT accept `claude-hook` as a valid hook. This means `is_hooks_configured()` returns `False` for the current `settings.json` state (which uses `claude-hook`), causing spurious re-installs.

---

### `HookInstallerService` (`src/claude_mpm/services/hook_installer_service.py`)

**WHAT**

Manages programmatic install/uninstall of hook entries in `.claude/settings.json`.

- `install_hooks()` (line 286): prefers the `claude-hook` PATH entry point (`shutil.which("claude-hook")`); falls back to absolute script path. Merges rather than overwrites existing hooks.
- `is_hooks_configured()` (line 33): validates presence of 5 required hook types and looks for `hook_wrapper.sh` or `claude-hook-handler.sh` in any hook command — does not check for `claude-hook`.
- `uninstall_hooks()` (line 484): filters MPM hooks by matching `hook_wrapper.sh`, `claude-hook-handler.sh`, or `claude-mpm` in command strings.

**DRIFT**

- `is_hooks_configured()` uses only substring match on `hook_wrapper.sh` / `claude-hook-handler.sh` (line 85) despite the service's own `install_hooks()` preferring the plain `claude-hook` command. Result: the service always reports "not configured" for installations that correctly use `claude-hook`, triggering a re-install on every startup.
- The service comment (line 346) says `"_mpm": True` is the "authoritative signal" for MPM hooks, but `is_hooks_configured()` ignores this field entirely and relies on script-name substrings.

---

## 3. Hook Event Handlers

All handlers are in `src/claude_mpm/hooks/claude_hooks/handlers/`. They were extracted from `event_handlers.EventHandlers` as part of issue #509 refactor.

### 3a. `tool_handler.py` — `ToolHandler`

**WHAT**

Handles `PreToolUse` and `PostToolUse` events via `handle_pre_tool_fast()` and `handle_post_tool_fast()`.

**`handle_pre_tool_fast()`** (line 178):

1. **Circuit breaker** (lines 192–208): calls `context_circuit_breaker.evaluate(event)`. If deny, returns `hookSpecificOutput` with `permissionDecision: deny` immediately.
2. **Model tier injection** (lines 221–235): if `tool_name == "Agent"`, calls `model_tier_hook.build_model_tier_response(event)`. Returns `hookSpecificOutput` with `updatedInput` when model was injected; short-circuits.
3. **ztk rewrite** (lines 236–246): if `tool_name == "Bash"`, calls `ztk_hook.build_ztk_response(event)`. Returns modified input if ztk is available.
4. **Observability** (lines 248–332): extracts tool parameters, operation type, security risk; stores correlation ID in `CorrelationManager`; emits `pre_tool` Socket.IO event; handles `Task` delegation specially (`_handle_task_delegation()`); emits `todo_updated` event for `TodoWrite` calls.
5. Returns `None` (normal continue) for the common path.

**`handle_post_tool_fast()`** (line 489):

- Extracts result data, duration, exit code; classifies exit code 2 as `"blocked"`.
- Retrieves pre-tool correlation ID from `CorrelationManager`.
- Includes full output for `Read`, `Edit`, `Write`, `Grep`, `Glob`.
- Handles `Task` delegation completion: triggers memory post-delegation hook and response tracking.
- **Context usage update** (lines 587–610): if event has `usage` dict, persists token counts to `<cwd>/.claude-mpm/state/context-usage.json` via `ContextUsageTracker`.
- **Terminal title** (lines 623–628): for `TodoWrite` and `ExitPlanMode`, builds an OSC 0 escape sequence and returns `{"terminalSequence": seq}` (opt-in via `CLAUDE_MPM_TERMINAL_TITLE=true`).

**Task delegation handling** (`_handle_task_delegation()`, line 334):

- Normalizes agent type, tracks delegation in `StateManagerService`, emits `subagent_start` event.
- Triggers memory pre-delegation hook if `memory_hook_manager` is available.
- Logs agent prompt asynchronously with `asyncio.wait_for(timeout=2.0)`.

**DRIFT**

- `handle_pre_tool_fast()` inlines the circuit-breaker, model-tier, and ztk logic (steps 1–3) that `pretooluse_dispatcher.py` was documented as consolidating. Both implementations coexist, creating two separate code paths for the same logic.
- `StateManagerService.get_git_branch()` (line 196 of `state_manager.py`) uses `os.chdir(working_dir)` — this is a process-global operation that can cause race conditions when multiple threads run in the same process. CLAUDE.md's "Stability Patterns" (Hooks System section) explicitly warns against this: "Use subprocess-relative operations (`git -C`) instead of process-global state (e.g., `os.chdir`)." The state manager violates this documented pattern.

---

### 3b. `stop_handler.py` — `StopHandler`

**WHAT**

Handles `Stop` events via `handle_stop_fast()` (line 21).

1. **Auto-pause** (lines 40–84): if `usage` key present and `AutoPauseHandler` initialized, passes token data to `on_usage_update()`; emits threshold warning to log (not stderr — CLAUDE.md warns against unconditional stderr writes). If pause is active, finalizes session file.
2. **Response tracking** (lines 87–94): delegates to `response_tracking_manager.track_stop_response()`.
3. **Cross-project message check** (lines 99–169): fetches unread messages via `MessageService`. If unread messages exist and `stop_hook_active` is False, returns `{"continue": True, "stopReason": reason}` — blocking the Stop event. Marks notified messages as read. Resets `message_check_hook` throttle state.
4. **Socket.IO emission** (line 172): emits `stop` event plus `token_usage_updated` event if usage data available.
5. **Resume log generation** (lines 181–185): calls `_generate_resume_log_on_stop()` — this wiring was missing before issue #462 fix.

**WHY**

The Stop handler is the primary lifecycle checkpoint: auto-pause finalization, message delivery enforcement, and session resume log generation all happen here to ensure they fire regardless of whether Claude stops normally or abnormally.

**DRIFT**

- `stop_hook_active` field is checked (line 110) to prevent infinite re-blocking loops, but this field is undocumented in the hook contract spec and relies on Claude Code including it in subsequent Stop events after a block — behavior that is not guaranteed.
- CLAUDE.md lists `Stop` under hooks but does not describe the cross-project message blocking behavior or resume log generation on stop.

---

### 3c. `user_prompt_handler.py` — `UserPromptHandler`

**WHAT**

Handles `UserPromptSubmit` events via `handle_user_prompt_fast()` (line 24).

- Skips `/mpm` commands unless `DEBUG` is enabled (line 35).
- Detects `@alias` at start of prompt (regex `^@([a-zA-Z][a-zA-Z0-9_-]*)\s`) and saves to `~/.claude-mpm/state/last_project.json` (lines 128–169).
- Emits `command_acknowledged` event immediately for dashboard feedback.
- Captures PM-level directives to persistent memory via `get_pm_memory()` (lines 172–203).
- Classifies urgency by keyword matching (`urgent`, `error`, `bug`, `fix`, `broken`).
- Stores prompt in `pending_prompts` dict for later `AssistantResponse` correlation.
- Emits `user_prompt` Socket.IO event.

The comment at lines 119–123 explicitly notes that the inline cross-project message check was removed to avoid SQLite race conditions with `message_check_hook.py` running as a separate subprocess.

**DRIFT**

- `@alias` sticky-context feature and PM directive capture are not documented in CLAUDE.md or the hooks README.
- The `message_check_hook.py` runs as a separate `UserPromptSubmit` hook subprocess (as confirmed in `settings.json`); the inline call was removed but the interaction between the two is undocumented.

---

### 3d. `assistant_response_handler.py` — `AssistantResponseHandler`

**WHAT**

Handles `AssistantResponse` events via `handle_assistant_response()` (line 21).

- Tracks response via `response_tracking_manager.track_assistant_response()`.
- **Delegation pattern scanner** (lines 121–183): calls `_scan_for_delegation_patterns()` which uses a `delegation_detector` service to find anti-patterns (PM asking user to run commands manually instead of delegating). Logs violations as `pm.violation` events in the event log with `event_type="pm.violation"` — NOT as autotodos.
- Emits `assistant_response` Socket.IO event with content preview, code/JSON detection flags, and prompt correlation.

**DRIFT**

- Issue #523 table lists `assistant_response_handler.py` — file exists at the correct path. Behavior (delegation scanning, violation logging) is entirely undocumented in CLAUDE.md.
- The `delegation_detector` and `event_log` services are accessed via `self.base.delegation_detector` and `self.base.event_log` (lines 145–146) — injected through the `BaseEventHandler`. The `BaseEventHandler` class is in `handlers/base.py` but its constructor and injection mechanism are not part of the #523 scope and were not exhaustively read.

---

### 3e. `subagent_handler.py` — `SubagentHandler`

**WHAT**

Handles `SubagentStop` and `SubagentStart` events.

- `handle_subagent_stop_fast()` (line 20): delegates entirely to `self.hook_handler.subagent_processor.process_subagent_stop(event)`. Falls back to `self.hook_handler.handle_subagent_stop(event)` if processor unavailable.
- `handle_subagent_start_fast()` (line 162): extracts `agent_type` (tries `agent_type`, then `subagent_type`), generates `agent_id`, emits `subagent_start` Socket.IO event.
- `_handle_subagent_response_tracking()` (line 29): fuzzy session-ID matching for delegation request correlation (prefix matching on first 8 or 16 chars).

**DRIFT**

- `SubagentStop` processing is fully delegated to `SubagentResponseProcessor` (in services/); the handler itself contains only routing. The response-tracking logic that lives in `SubagentHandler._handle_subagent_response_tracking()` (lines 29–160) appears to be dead code — the `SubagentResponseProcessor._track_response()` in `services/subagent_processor.py` duplicates the same fuzzy-matching and tracking logic. Two implementations exist.

---

### 3f. `passthrough_handlers.py`

**WHAT**

File exists at `src/claude_mpm/hooks/claude_hooks/handlers/passthrough_handlers.py`. Not read in detail (not in #523 scope), but presence confirmed.

---

## 4. Hook Event Services

All services are in `src/claude_mpm/hooks/claude_hooks/services/`.

### 4a. `state_manager.py` — `StateManagerService`

**WHAT**

Manages in-process state for a single hook handler invocation.

- **Delegation tracking** (lines 73–122): `track_delegation(session_id, agent_type, request_data)` stores active delegations in a dict with history deque (maxlen=100). Cleanup removes entries older than 5 minutes.
- **Git branch cache** (lines 168–230): caches `git branch --show-current` results per working-directory for 30 seconds. Uses `os.chdir()` (see drift note).
- **Pending prompts** (line 67): dict mapping session_id → prompt data for response correlation.
- **Fuzzy session matching** (lines 232–263): `find_matching_request()` tries exact match, then prefix-based fuzzy match on first 8 or 16 chars of session ID.
- **Periodic cleanup** (lines 138–166): triggered every 100 events (`CLEANUP_INTERVAL_EVENTS`); caps delegation/prompt dicts at 200/100 entries.

**DRIFT**

- Uses `os.chdir()` at line 196 — violates the "Stability Patterns" documented in CLAUDE.md (Hooks System section: "Use subprocess-relative operations (`git -C`) instead of process-global state (e.g., `os.chdir`)"). The fix is straightforward: `subprocess.run(["git", "-C", working_dir, "branch", "--show-current"], ...)` without any chdir.
- "Issue #523 services" table references `state_manager.py` — file exists at the correct location.

---

### 4b. `subagent_processor.py` — `SubagentResponseProcessor`

**WHAT**

Processes `SubagentStop` events with three responsibilities:

1. **Agent type detection** (`_extract_basic_info()`, line 126): priority chain — (1) `StateManagerService.get_delegation_agent_type()`, (2) event `agent_type`/`subagent_type` fields, (3) keyword inference from `task` field text, (4) default `"pm"` (sets `agent_type_inferred=True`).
2. **Structured response extraction** (`_extract_structured_response()`, line 170): regex-searches output for ` ```json ... ``` ` blocks; logs presence of `MEMORIES` field.
3. **Response tracking** (`_track_response()`, line 197): calls `state_manager.find_matching_request()` with fuzzy fallback; calls `response_tracker.track_response()`; cleans up request entry.

Emits `subagent_stop` event via `connection_manager.emit_event()`.

**DRIFT**

- Issue #523 references this file — exists at correct path.
- Duplicate logic with `SubagentHandler._handle_subagent_response_tracking()` (described in §3e). The processor is the live path; the handler's method appears unused.

---

### 4c. `duplicate_detector.py` — `DuplicateEventDetector`

**WHAT**

Detects duplicate events within a 100 ms window using a thread-safe deque (maxlen=10).

- `generate_event_key()` (line 56): for `PreToolUse`, key includes session, tool, and agent/prompt prefix; for `UserPromptSubmit`, includes prompt prefix; for others, just event type + session.
- `is_duplicate()` (line 31): checks recent events within `duplicate_window_seconds` (default 0.1 s); records non-duplicates.

**WHY**

Claude Code may call the same hook multiple times because the hook is registered under multiple event-type entries (as seen in `settings.json`). The detector prevents redundant downstream processing.

**DRIFT**

- Issue #523 references this file — exists at correct path.
- The 100 ms deduplication window may be too short to catch the second `claude-hook` invocation from the duplicate `settings.json` entries (both have the same timeout but run sequentially). The duplicate in settings.json should be fixed at the source rather than relying on the detector.

---

### 4d. `connection_manager.py` vs `connection_manager_http.py`

**WHAT**

Two files exist:

- `connection_manager.py`: "old SocketIO-based" implementation (commented out in `services/__init__.py` line 4). Uses `get_connection_pool()` from `claude_mpm.core.socketio_pool` with HTTP fallback.
- `connection_manager_http.py`: "new HTTP-based" implementation (active, imported at line 5 of `services/__init__.py`). Uses synchronous HTTP POST via `requests` to `http://localhost:8765/api/events` with a 2.0 s timeout. Uses `ThreadPoolExecutor` for non-blocking emission.

The active `ConnectionManagerService` (`connection_manager_http.py`) implements single-path emission: direct HTTP POST only, no EventBus, no duplicate Socket.IO paths.

**DRIFT**

- Issue #523 scope references `connection_manager.py` — this file is **present but effectively dead code**. The active implementation is `connection_manager_http.py`. This is a significant naming/attribution error.
- `connection_manager.py` still references the now-removed EventBus architecture in its imports and documentation, meaning the file is also internally inconsistent (imports `get_connection_pool` from `claude_mpm.core.socketio_pool` but the comment says EventBus was removed).

---

## 5. Circuit Breaker

### File: `src/claude_mpm/hooks/context_circuit_breaker.py`

**WHAT**

Denies tool calls when context usage reaches or exceeds 95%.

- **State source** (line 37): reads `<cwd>/.claude-mpm/state/context-usage.json`, written by `ContextUsageTracker`.
- **`evaluate(event)`** (line 72): returns non-empty dict with `permissionDecision: "deny"` when fired; returns empty dict otherwise (pass-through signal).
- **Session-ID guard** (lines 87–89): only fires when `state["session_id"]` matches current session (from event payload or `CLAUDE_SESSION_ID` env var). Stale state files from prior runs do not block.
- **Fail-open** (lines 41–58): returns `None` if file missing, unreadable, malformed, or session mismatch.
- **`main()` entrypoint** (line 113): wraps `evaluate()` in the `hookSpecificOutput` envelope for standalone invocation.
- **Threshold**: `CRITICAL_THRESHOLD = 95.0` (line 35), matching `ContextUsageTracker.THRESHOLDS["critical"]`.

**WHY**

Prevents context window overflow that would drop earlier conversation context. Fail-open is intentional: false denials (blocking sessions because of a stale state file) are worse than false permits.

**DRIFT**

- CLAUDE.md (Hooks System section) mentions circuit breakers abstractly ("Checking circuit breakers" in spinner verbs) but does not describe this module's behavior, its state file path, or its 95% threshold.
- The circuit breaker is invoked in two places: (1) `tool_handler.py`'s `handle_pre_tool_fast()` (lines 192–208) directly calls `context_circuit_breaker.evaluate()`; (2) `pretooluse_dispatcher.py` (lines 81–83) also calls it. The `pretooluse_dispatcher` is not wired in settings.json (see §1c drift), so path (1) is the live path.
- The `main()` entrypoint allows standalone invocation (`python3 -m claude_mpm.hooks.context_circuit_breaker`) but this is not wired in settings.json either.

---

## 6. Model Tier Enforcement

### File: `src/claude_mpm/hooks/model_tier_hook.py`

**WHAT**

Handles two hook types from a single module:

**PreToolUse / Agent model injection** (`build_model_tier_response()`, line 241):

- Only acts on `tool_name == "Agent"` calls that do not already have a `"model"` field in `tool_input`.
- **Version gate** (lines 276–277): skips injection if `supports_pretool_modify()` returns False (requires Claude Code v2.0.30+).
- **Model resolution priority** (lines 289–297):
  1. Explicit `model` in Agent tool call (already handled above).
  2. `models.agents.<name>` from `~/.claude-mpm/config/configuration.yaml` (user-level), overridden by `.claude-mpm/configuration.yaml` (project-level).
  3. Frontmatter `model:` field in `.claude/agents/<name>.md`.
  4. Built-in `_HAIKU_AGENTS` set (17 agent names including `ops`, `documentation`, `ticketing`, `memory-manager`, etc.).
  5. Default: `claude-opus-4-7`.
- **Short-alias injection** (lines 300–301): maps resolved model IDs to short aliases (`opus`, `sonnet`, `haiku`) for Claude Code compatibility.
- **Sub-agent environment marking** (lines 310–313): injects `CLAUDE_MPM_SUB_AGENT: "1"` into `tool_input["env"]`, enabling the fast-hook sub-agent early-exit.
- **Returns** `hookSpecificOutput` with `updatedInput` (modified `tool_input`) and `additionalContext` (model resolution info).

**PermissionRequest routing** (`build_permission_request_response()`, line 216):

- Calls `permission_policy.evaluate(event)` and wraps the decision in `hookSpecificOutput` with `permissionDecision` and `permissionDecisionReason`.

**`main()`** (line 323):

- Reads event from stdin, routes to appropriate handler by `hook_event_name`.

**DRIFT**

- CLAUDE.md (line 124) describes this file correctly: "Model tier enforcement: `src/claude_mpm/hooks/model_tier_hook.py`". However, it does not describe PermissionRequest routing, YAML config loading, frontmatter reading, version gating, or sub-agent env injection.
- Default model is `claude-opus-4-7` (line 82–86). This is pinned to a specific version, not a tier alias. The `_TIER_ALIASES` dict maps `claude-opus-4-7 → claude-opus-4-7` (same), but injection normalizes to the short alias `opus` via `_INJECT_SHORT_ALIAS`. This is correct but potentially confusing.
- The `model_tier_hook` is not listed in `settings.json` as a standalone hook command. It is invoked via `build_model_tier_response()` function calls from `tool_handler.py` (line 224) and `pretooluse_dispatcher.py` (line 88). CLAUDE.md's description implies it is a directly-wired hook, which is no longer true.
- 17 haiku-tier agents are hardcoded in `_HAIKU_AGENTS` (lines 55–78). This list is invisible from the docs and configuration.

---

## 7. Permission Gate

### File: `src/claude_mpm/hooks/permission_policy.py`

**WHAT**

Pure decision engine for PermissionRequest events.

- **`evaluate(event)`** (line 116): decision priority:
  1. Tool in `SAFE_TOOLS` → `allow`. (`Read`, `Glob`, `Grep`, `WebSearch`, `WebFetch`, `TodoRead`, `TodoWrite`, `NotebookRead`, `LS`)
  2. Tool in `MUTATING_TOOLS` (`Edit`, `Write`, `MultiEdit`, `NotebookEdit`) AND agent tier in `READ_ONLY_TIERS` → `deny`.
  3. Tool is `Bash` AND command matches `DESTRUCTIVE_BASH_PATTERNS` → `deny`.
  4. Default → `allow` (fail open, issue #421 preservation).
- **Read-only tiers** (lines 86–94): `research`, `qa`, `documentation-reviewer`, `code-reviewer`, `ticketing`.
- **Destructive bash patterns** (lines 99–108): 8 regex patterns covering `rm -rf /`, `sudo rm`, fork bomb, `mkfs`, `dd` to raw disk, redirect to raw disk, `shutdown`/`reboot`/`halt`/`poweroff`.
- **Agent tier extraction** (`_extract_agent_tier()`, line 187): accepts `agent_id`, `subagent_type`, or `agent_type` fields; normalizes with `normalize_agent_id()`.
- Returns `PermissionDecision(decision, reason)` dataclass — pure, no side effects.

**WHY**

Introduced in issue #421 to replace the prior unconditional approve behavior. Fail-open default preserves backward compatibility while adding explicit protection for destructive operations.

**DRIFT**

- Not mentioned in CLAUDE.md at all.
- `SAFE_TOOLS` includes `TodoWrite` — a write operation. This is intentional (todo management is deemed safe), but the name `SAFE_TOOLS` is misleading given it includes a mutating tool.
- `READ_ONLY_TIERS` does not include `security` or `planner` agents. Security agents typically should not mutate files, but they are not protected. This may be intentional (security agents need to patch code) but is undocumented.
- `NotebookEdit` is in `MUTATING_TOOLS` but `NotebookRead` is in `SAFE_TOOLS`. This asymmetry is correct but not documented.
- The decision engine receives `tool_name` from the PermissionRequest event payload. For PermissionRequest events, the payload schema may differ from PreToolUse — the module assumes the same field names, which may not hold in all Claude Code versions.

---

## 8. Component Map (Quick Reference)

| Component | Documented location (#523 scope) | Actual location | Status |
|-----------|----------------------------------|-----------------|--------|
| Hook relay | `claude-hook-fast.sh` | `src/claude_mpm/scripts/claude-hook-fast.sh` | Exists; NOT wired in settings.json as primary |
| Python handler | `claude-hook-handler.sh` | `src/claude_mpm/scripts/claude-hook-handler.sh` | Exists; wired via absolute path in settings.json |
| Entry point | `claude-hook` (PATH) | `claude_mpm.hooks.claude_hooks.hook_handler:main` | Exists; wired (duplicated) in settings.json |
| PreToolUse dispatcher | `pretooluse_dispatcher.py` | `src/claude_mpm/hooks/pretooluse_dispatcher.py` | Exists but NOT wired in settings.json; logic inlined in `tool_handler.py` |
| Tool handler | `handlers/tool_handler.py` | Correct | Exists |
| Stop handler | `handlers/stop_handler.py` | Correct | Exists |
| User prompt handler | `handlers/user_prompt_handler.py` | Correct | Exists |
| Assistant response handler | `handlers/assistant_response_handler.py` | Correct | Exists |
| Subagent handler | `handlers/subagent_handler.py` | Correct | Exists |
| State manager | `services/state_manager.py` | Correct | Exists |
| Subagent processor | `services/subagent_processor.py` | Correct | Exists |
| Duplicate detector | `services/duplicate_detector.py` | Correct | Exists |
| Connection manager | `services/connection_manager.py` | Correct path but DEAD CODE | Superseded by `connection_manager_http.py` |
| Circuit breaker | `hooks/context_circuit_breaker.py` | Correct | Exists |
| Model tier hook | `hooks/model_tier_hook.py` | Correct | Exists; not wired standalone |
| Permission gate | `hooks/permission_policy.py` | Correct | Exists |
| Hook installer | `services/hook_installer_service.py` | Correct | Exists |

---

## Summary of Significant Drift

1. **`claude-hook-fast.sh` is NOT the primary wired dispatcher.** CLAUDE.md and the hooks README describe it as "the" hook dispatcher, but the actual `settings.json` wires `claude-hook` (the full Python handler) as the primary command for all events. `claude-hook-fast.sh` is not in `settings.json` at all. The fast script is available but unused by the production hook configuration.

2. **`pretooluse_dispatcher.py` is not wired in `settings.json`.** The module exists and is functional, but its logic has been inlined directly into `tool_handler.py`'s `handle_pre_tool_fast()` (lines 192–246). Two parallel implementations of the circuit-breaker + model-tier + ztk dispatch chain coexist without documentation.

3. **Duplicate `claude-hook` entries in `settings.json`.** For PreToolUse, PostToolUse, Stop, SubagentStop, and UserPromptSubmit, `claude-hook` appears twice (timeouts 15 s and 60 s). The second invocation reads empty stdin and emits a no-op `{"continue": true}`, wasting process spawns per tool call. This is an artifact of repeated `mpm-init` / `install_hooks()` runs that the merge logic fails to deduplicate.

4. **`HookInstallerService.is_hooks_configured()` is broken.** It validates hook presence by checking for `hook_wrapper.sh` or `claude-hook-handler.sh` command substrings (line 85), but the current installation uses `claude-hook` (the PATH entry point). The method therefore always returns `False` for current installations, causing spurious re-installs on startup. The `"_mpm": true` marker field — which the code comments call the "authoritative signal" — is ignored by the validator.

5. **`connection_manager.py` is dead code; `connection_manager_http.py` is the live implementation.** Issue #523's scope lists `connection_manager.py` as an active service, but `services/__init__.py` has it commented out (line 4) and imports `connection_manager_http.py` instead (line 5). The old SocketIO-based manager is not loaded at runtime.

6. **`state_manager.py` uses `os.chdir()` in `get_git_branch()`** (line 196) — a process-global operation that violates the "Stability Patterns" explicitly documented in CLAUDE.md's Hooks System section: "Use subprocess-relative operations (`git -C`) instead of process-global state."

---

*Total components documented: 17*  
*(Hook relay ×3, settings.json + HookInstallerService, handlers ×5, services ×4, circuit breaker, model tier, permission gate)*
