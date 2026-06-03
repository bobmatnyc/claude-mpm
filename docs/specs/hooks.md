# Hooks & Enforcement Subsystem — Spec-Linked Documentation

**Status:** Active
**Version:** v1
**Subsystem:** HOOKS

This document covers the ten highest-complexity behavioral areas in the claude-mpm
Hooks & Enforcement subsystem. Each section constitutes one governed specification
with a stable ID, a behavior contract (WHAT), a rationale section (WHY), and an
implementing-modules table.

The IDs below use the `{#SPEC-HOOKS-NN~1}` anchor form that the traceability
checker recognizes as a declaration. Engineer agents will add matching
`References: SPEC-HOOKS-NN~1` entries to the docstrings of the implementing
functions once this spec is reviewed.

---

## Table of Contents

| ID | Section | Implementing function(s) |
|----|---------|--------------------------|
| SPEC-HOOKS-01~1 | [Bash relay — claude-hook-fast.sh](#bash-relay--claude-hook-fastsh-spec-hooks-011) | `claude-hook-fast.sh` |
| SPEC-HOOKS-02~1 | [Python environment resolver — claude-hook-handler.sh](#python-environment-resolver--claude-hook-handlersh-spec-hooks-021) | `claude-hook-handler.sh` |
| SPEC-HOOKS-03~1 | [Hook entry-point router — hook_handler.main](#hook-entry-point-router--hook_handlermain-spec-hooks-031) | `HookHandler._route_event` |
| SPEC-HOOKS-04~1 | [Hook installation and idempotent merge — HookInstallerService](#hook-installation-and-idempotent-merge--hookinstallerservice-spec-hooks-041) | `HookInstallerService.install_hooks` / `is_hooks_configured` |
| SPEC-HOOKS-05~1 | [PreToolUse enforcement pipeline — ToolHandler](#pretooluse-enforcement-pipeline--toolhandler-spec-hooks-051) | `ToolHandler.handle_pre_tool_fast` |
| SPEC-HOOKS-06~1 | [PostToolUse observability pipeline — ToolHandler](#posttooluse-observability-pipeline--toolhandler-spec-hooks-061) | `ToolHandler.handle_post_tool_fast` |
| SPEC-HOOKS-07~1 | [Stop lifecycle handler](#stop-lifecycle-handler-spec-hooks-071) | `StopHandler.handle_stop_fast` |
| SPEC-HOOKS-08~1 | [UserPromptSubmit handler](#userpromptsubmit-handler-spec-hooks-081) | `UserPromptHandler.handle_user_prompt_fast` |
| SPEC-HOOKS-09~1 | [SubagentStop/Start handler and processor](#subagentstostart-handler-and-processor-spec-hooks-091) | `SubagentHandler`, `SubagentResponseProcessor` |
| SPEC-HOOKS-10~1 | [Event services — duplicate detector, state manager, connection manager](#event-services--duplicate-detector-state-manager-connection-manager-spec-hooks-101) | `DuplicateEventDetector`, `StateManagerService`, `ConnectionManagerService` |
| SPEC-HOOKS-11~1 | [Context circuit breaker](#context-circuit-breaker-spec-hooks-111) | `context_circuit_breaker.evaluate` |
| SPEC-HOOKS-12~1 | [Model tier enforcement](#model-tier-enforcement-spec-hooks-121) | `model_tier_hook.build_model_tier_response` |
| SPEC-HOOKS-13~1 | [Permission gate](#permission-gate-spec-hooks-131) | `permission_policy.evaluate` |

---

## Bash relay — claude-hook-fast.sh {#SPEC-HOOKS-01~1}

**Status:** Active

### Behavior Contract (WHAT)

- **Inputs:** Hook event JSON delivered by Claude Code on stdin; environment variable
  `CLAUDE_MPM_SUB_AGENT` (optional) and `CLAUDE_MPM_SOCKETIO_PORT` (optional, default
  `8765`).

- **Outputs:** One JSON object on stdout per invocation. PreToolUse and
  PermissionRequest return `{"continue": true}` synchronously (decision events). All
  other event types return `{"async": true, "asyncTimeout": 60000}`.

- **Event extraction:** A pure-bash helper `_extract_json_str` extracts field values
  from the stdin payload without requiring `jq`. It handles both compact and spaced
  JSON forms. It tries `hook_event_name` first, then falls back to `event`.

- **WorktreeCreate branch:** Runs before the sub-agent guard. Sanitizes the `name`
  slug (replaces non-alphanumeric characters, lowercases), determines `REPO_ROOT` from
  the event `cwd` field, and creates a sibling worktree directory under
  `<parent>/<repo-name>-worktrees/<slug>`. Attempts three strategies in order: (1)
  `git worktree add` with a new branch, (2) without a new branch, (3) re-use of an
  existing path. Prints the absolute worktree path to stdout on success; exits 1 on
  failure.

- **WorktreeRemove branch:** Runs before the sub-agent guard. Executes
  `git -C "$REPO_ROOT" worktree remove --force "$WORKTREE_PATH"`. Always emits
  `{"continue": true}`.

- **Sub-agent early-exit guard:** After WorktreeCreate/Remove handling, if
  `CLAUDE_MPM_SUB_AGENT` is set (any non-empty value), emits `{"continue": true}` and
  exits immediately for all remaining event types, skipping dashboard forwarding.

- **Event routing:** Maps Claude Code event names to `SUBTYPE` strings for dashboard
  payload compatibility (`PreToolUse` → `pre_tool`, `PostToolUse` → `post_tool`, etc.).

- **Dashboard POST:** Fire-and-forget `curl` to
  `http://localhost:${PORT}/api/events` with `--connect-timeout 0.2 --max-time 0.3`,
  run in the background (`&`). Failure does not affect the response to Claude Code.

- **Error conditions:** Worktree operations fail with exit code 1 if the `git worktree
  add` command fails on all three attempts. All other operations are best-effort;
  the script always terminates with a valid JSON response.

### Rationale (WHY)

Designed to reduce hook invocation latency from ~450 ms (Python startup) to ~15 ms.
The script handles only two structural side-effects (WorktreeCreate/Remove) and one
observability concern (fire-and-forget dashboard POST). All enforcement decisions are
delegated to the Python hook handler wired alongside this script in settings.json.
The sub-agent early-exit guard prevents recursive hook invocations when Claude Code
itself spawns sub-agents.

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/scripts/claude-hook-fast.sh` | (shell script) | Full implementation |

---

## Python environment resolver — claude-hook-handler.sh {#SPEC-HOOKS-02~1}

**Status:** Active

### Behavior Contract (WHAT)

- **Inputs:** Hook event delivered by Claude Code on stdin; environment variable
  `CLAUDE_MPM_ROOT` (directory of the claude-mpm installation).

- **Outputs:** No direct stdout output from the script itself. The script `exec`s
  into the Python hook handler process, which then writes the hook response.

- **Python resolution:** Tries the following in order, stopping at the first success:
  (1) `uv run` if `uv.lock` is present in the project root; (2) UV tools venv;
  (3) pipx venv; (4) project `venv/` or `.venv/`; (5) `$VIRTUAL_ENV`; (6) `python3`;
  (7) `python`.

- **PYTHONPATH:** Appends `src/` to `PYTHONPATH` for development installs (where the
  package is not pip-installed). No modification for UV/pipx/pip-installed packages.

- **Module availability check:** Runs `python -c "import claude_mpm"` before exec. If
  the import fails, emits `{"continue": true}` and exits cleanly without invoking the
  Python handler.

- **exec:** Replaces the shell process with:
  `python -W ignore::RuntimeWarning -m claude_mpm.hooks.claude_hooks.hook_handler`,
  redirecting stderr to `/tmp/claude-mpm-hook-error.log`. `RuntimeWarning` suppression
  prevents frozen runpy warnings from polluting Claude Code's REPL.

- **Fallback:** If `exec` fails (extremely rare), the script falls through and emits
  `{"continue": true}` as a fail-open response.

- **Error conditions:** Module import failure, no resolvable Python executable, or
  exec failure all result in `{"continue": true}` (fail-open).

### Rationale (WHY)

Claude Code invokes hooks as raw shell commands without activating any virtual
environment. This script bridges the gap for all supported installation methods (UV,
pipx, pip, venv, development). The `exec` pattern (rather than `python ...`) avoids a
redundant shell process lingering after the Python handler starts.

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/scripts/claude-hook-handler.sh` | (shell script) | Full implementation |

---

## Hook entry-point router — hook_handler.main {#SPEC-HOOKS-03~1}

**Status:** Active

### Behavior Contract (WHAT)

- **Inputs:** Hook event JSON on stdin. Reads all stdin once at startup.

- **Outputs:** One JSON object on stdout. The shape varies by hook type:
  - `PreToolUse`: `{"hookSpecificOutput": {"permissionDecision": "deny", ...}}` on
    circuit-breaker or model-tier injection; or modified `updatedInput` for model
    injection; or `{}` / nothing for normal pass-through.
  - `PermissionRequest`: `{"hookSpecificOutput": {"permissionDecision": "allow"|"deny",
    "permissionDecisionReason": "..."}}`.
  - `Stop`: optionally `{"decision": "block", "reason": "..."}` to block the stop.
  - `PostToolUse`: optionally `{"terminalSequence": "..."}` for terminal title updates.
  - All other events: `{}` or nothing (no output needed for observability events).

- **Event routing (`_route_event`):** Extracts `hook_event_name` (tries multiple
  field names as fallback). Dispatches to typed handlers via a static dict:
  `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `Stop`, `SubagentStop`,
  `SubagentStart`, `PermissionRequest`, `SessionStart`, `AssistantResponse`.
  Unknown event types are logged and ignored (no output).

- **Duplicate suppression:** Before routing, queries `DuplicateEventDetector.is_duplicate()`.
  If duplicate detected, emits `{"continue": true}` and returns early.

- **Stdin guard:** Reads stdin with `select.select(timeout=1.0)` to prevent blocking on
  empty stdin. Returns fail-open `{"continue": true}` if no data within 1 second or if
  JSON parsing fails.

- **PermissionRequest fallback:** If routing returns `None` for a PermissionRequest
  event, emits `{"hookSpecificOutput": {"permissionDecision": "allow"}}` to avoid
  hanging Claude Code.

- **Error conditions:** Any unhandled exception in the handler catches and logs at debug
  level, then emits `{"continue": true}`. The handler never propagates exceptions to
  Claude Code.

### Rationale (WHY)

Centralizes all event dispatch so individual handlers remain testable in isolation.
The single stdin read at startup avoids race conditions from multiple reads. Fail-open
on all error paths (parse error, handler exception, timeout) ensures that hook failures
never block the Claude Code session.

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/hooks/claude_hooks/hook_handler.py` | `HookHandler._route_event` | Event dispatch |
| `src/claude_mpm/hooks/claude_hooks/hook_handler.py` | `HookHandler.main` | Stdin read, JSON parse, output |

---

## Hook installation and idempotent merge — HookInstallerService {#SPEC-HOOKS-04~1}

**Status:** Active

### Behavior Contract (WHAT)

- **Inputs (`install_hooks`):** Optional `force: bool` (default `False`). Reads
  `.claude/settings.json` in the current project root.

- **Outputs (`install_hooks`):** Modifies `.claude/settings.json` in-place by merging
  MPM hook entries into the `"hooks"` key for each supported event type. Returns `True`
  on success, `False` on failure. No-ops if `is_hooks_configured()` returns `True` and
  `force` is `False`.

- **Hook command selection:** Prefers `claude-hook` (PATH-based entry point, resolved
  via `shutil.which`). Falls back to the absolute path of `claude-hook-handler.sh` if
  `claude-hook` is not on PATH.

- **MPM ownership marker:** Each installed hook entry carries `"_mpm": True`. This is
  the authoritative signal identifying MPM-owned entries.

- **Idempotency (`_is_existing_mpm_hook`):** Before inserting a new entry, checks
  whether an existing entry matches via: `_mpm` marker, or `command == "claude-hook"`,
  or `"hook_wrapper.sh"` in command, or `"claude-hook-handler.sh"` in command. If a
  match is found, the existing entry is updated rather than duplicated.

- **`is_hooks_configured()`:** Returns `True` if all five required event types
  (`PreToolUse`, `PostToolUse`, `Stop`, `SubagentStop`, `UserPromptSubmit`) each have
  at least one hook entry matching the `_is_existing_mpm_hook` predicate. Returns
  `False` otherwise. Does not mutate any files.

- **`uninstall_hooks()`:** Removes all hook entries where `_is_claude_mpm_hook()`
  returns `True` (matches `"hook_wrapper.sh"`, `"claude-hook-handler.sh"`, `"claude-mpm"`,
  `"claude-hook"`, or `_mpm` marker). Writes the filtered settings back to disk.

- **Error conditions:** File read/write failures, JSON parse errors, or missing settings
  file are caught; `install_hooks` returns `False` and logs the exception.

### Rationale (WHY)

Programmatic hook management (rather than manual settings.json editing) ensures
consistent hook configuration across all supported installation methods and enables
`mpm-init` to be safely re-run. The `_mpm` marker was introduced as the authoritative
ownership signal to replace fragile script-name substring matching, which broke when
the primary hook command changed from `claude-hook-handler.sh` to `claude-hook`.

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/services/hook_installer_service.py` | `HookInstallerService.install_hooks` | Hook installation with merge |
| `src/claude_mpm/services/hook_installer_service.py` | `HookInstallerService.is_hooks_configured` | Validation predicate |
| `src/claude_mpm/services/hook_installer_service.py` | `HookInstallerService.uninstall_hooks` | Hook removal |
| `src/claude_mpm/services/hook_installer_service.py` | `HookInstallerService._is_existing_mpm_hook` | Idempotency predicate |

---

## PreToolUse enforcement pipeline — ToolHandler {#SPEC-HOOKS-05~1}

**Status:** Active

### Behavior Contract (WHAT)

- **Inputs:** A `PreToolUse` hook event dict containing `tool_name`, `tool_input`,
  `session_id`, and optional `usage` fields.

- **Outputs:** One of:
  - `{"hookSpecificOutput": {"permissionDecision": "deny", ...}}` — circuit breaker
    fired; tool call is blocked.
  - `{"hookSpecificOutput": {"updatedInput": {...}, "additionalContext": "..."}}` —
    model tier injection applied for `Agent` tool; tool input is modified.
  - Modified ztk response dict for `Bash` tool if ztk rewrite applied.
  - `None` — normal pass-through; tool call proceeds unchanged.

- **Processing order (strict):**
  1. **Circuit breaker:** Calls `context_circuit_breaker.evaluate(event)`. If the
     result is non-empty (deny decision), returns immediately with the deny envelope.
     No further steps run.
  2. **Model tier injection:** If `tool_name == "Agent"` and the tool does not already
     specify a `model` field, calls `model_tier_hook.build_model_tier_response(event)`.
     If injection succeeds and produces a response, returns that response. Errors in
     this step are caught and logged; execution continues (fail-open).
  3. **ztk rewrite:** If `tool_name == "Bash"`, calls `ztk_hook.build_ztk_response(event)`.
     Returns the modified input if ztk is available and rewrites the command. Errors
     caught and logged; execution continues.
  4. **Observability:** Extracts tool parameters, operation type, security risk
     classification. Stores a correlation ID in `CorrelationManager` for matching with
     the subsequent `PostToolUse` event. Emits a `pre_tool` Socket.IO event via the
     connection manager. For `Task` tool calls, delegates to `_handle_task_delegation()`.
     For `TodoWrite` calls, emits a `todo_updated` event.
  5. Returns `None` (normal continue) at the end of the observability path.

- **`_handle_task_delegation()`:** Normalizes agent type, records delegation in
  `StateManagerService`, emits `subagent_start` event. Logs the agent prompt
  asynchronously with `asyncio.wait_for(timeout=2.0)`.

- **Error conditions:** Circuit breaker, model tier, and ztk steps each have
  independent try/except wrapping. A failure in any enforcement step causes fail-open
  (tool call proceeds). Observability failures are logged and do not block the tool.

### Rationale (WHY)

The strict enforcement-before-observability ordering ensures that a denied tool call
does not emit spurious `pre_tool` events to the dashboard. Fail-open on all enforcement
steps ensures that bugs in the hook subsystem never permanently block Claude Code
sessions. The circuit breaker check runs first because it is the highest-priority
safety gate (context overflow blocks all tools unconditionally).

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/hooks/claude_hooks/handlers/tool_handler.py` | `ToolHandler.handle_pre_tool_fast` | Full PreToolUse pipeline |
| `src/claude_mpm/hooks/claude_hooks/handlers/tool_handler.py` | `ToolHandler._handle_task_delegation` | Task delegation side-effects |

---

## PostToolUse observability pipeline — ToolHandler {#SPEC-HOOKS-06~1}

**Status:** Active

### Behavior Contract (WHAT)

- **Inputs:** A `PostToolUse` hook event dict containing `tool_name`, `tool_result`,
  `session_id`, optional `usage` dict, and correlation metadata.

- **Outputs:** One of:
  - `{"terminalSequence": "<OSC 0 escape>"}` — terminal title update for `TodoWrite`
    and `ExitPlanMode` events when `CLAUDE_MPM_TERMINAL_TITLE=true` is set.
  - `None` — normal observability-only path.

- **Processing:**
  1. Extracts result data, duration, exit code. Classifies exit code 2 as `"blocked"`.
  2. Retrieves pre-tool correlation ID from `CorrelationManager` using the session ID
     and tool name.
  3. For `Read`, `Edit`, `Write`, `Grep`, `Glob` tools, includes the full output in
     the observability payload.
  4. For `Task` tool: triggers memory post-delegation hook via `memory_hook_manager`
     and response tracking via `SubagentResponseProcessor`.
  5. **Context usage update:** If the event contains a `usage` dict, persists token
     counts to `<cwd>/.claude-mpm/state/context-usage.json` via `ContextUsageTracker`.
     This file is the data source for the circuit breaker.
  6. **Terminal title:** For `TodoWrite` and `ExitPlanMode`, builds an OSC 0 escape
     sequence showing the current todo status and returns it as `terminalSequence`.
  7. Emits `post_tool` Socket.IO event with result summary, duration, and correlation ID.

- **Error conditions:** All steps wrapped in try/except; failures are logged at debug
  level. Context usage file write failures do not block hook response.

### Rationale (WHY)

`PostToolUse` is the primary observability checkpoint for tool execution outcomes.
Writing context usage to disk here (rather than reading it from the event directly in
the circuit breaker) decouples the two hooks: the circuit breaker only needs to read a
simple JSON file, not parse complex event payloads. The terminal title feature is
opt-in (requires env var) to avoid breaking environments that do not handle OSC
sequences.

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/hooks/claude_hooks/handlers/tool_handler.py` | `ToolHandler.handle_post_tool_fast` | Full PostToolUse pipeline |
| `src/claude_mpm/hooks/context_circuit_breaker.py` | (module) | Consumes `context-usage.json` written here |

---

## Stop lifecycle handler {#SPEC-HOOKS-07~1}

**Status:** Active

### Behavior Contract (WHAT)

- **Inputs:** A `Stop` hook event dict containing `session_id`, optional `usage` dict,
  and optional `stop_hook_active` boolean field.

- **Outputs:** One of:
  - `{"continue": True, "stopReason": "..."}` — blocks the Stop event (cross-project
    messages pending). Claude Code retries the Stop hook after user notification.
  - `{}` or `None` — allows the stop to proceed normally.

- **Processing order:**
  1. **Auto-pause:** If `usage` is present and `AutoPauseHandler` is initialized, passes
     token data to `on_usage_update()`. If the auto-pause threshold is reached, emits a
     warning (to log only, not stderr) and finalizes the session pause file.
  2. **Response tracking:** Delegates to `response_tracking_manager.track_stop_response()`.
  3. **Cross-project message check:** Queries `MessageService` for unread messages. If
     unread messages exist AND `stop_hook_active` is `False`, returns
     `{"continue": True, "stopReason": reason}` to block the stop. Marks notified
     messages as read. Resets the `message_check_hook` throttle state.
  4. **Socket.IO emission:** Emits `stop` event plus `token_usage_updated` if usage
     data is available.
  5. **Resume log generation:** Calls `_generate_resume_log_on_stop()` to write a
     session resume log, enabling `/mpm-session-resume` to reconstruct session context.

- **`stop_hook_active` guard:** Prevents infinite re-blocking. Claude Code is expected
  to set this field in subsequent Stop events after a block, signaling that the hook
  has already run and should not block again. This behavior is not guaranteed by the
  Claude Code contract; it is observed behavior.

- **Error conditions:** Each phase has independent try/except. A failure in the message
  check or resume log generation does not prevent the stop from proceeding.

### Rationale (WHY)

The Stop event is the primary session lifecycle checkpoint. Consolidating auto-pause
finalization, message delivery enforcement, and resume log generation here ensures
they fire regardless of how the session ends. Cross-project message blocking uses the
Stop hook (rather than UserPromptSubmit) because it must be the final action before
the session closes, not the first action on the next prompt.

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/hooks/claude_hooks/handlers/stop_handler.py` | `StopHandler.handle_stop_fast` | Full Stop pipeline |
| `src/claude_mpm/hooks/claude_hooks/handlers/stop_handler.py` | `StopHandler._generate_resume_log_on_stop` | Resume log generation |

---

## UserPromptSubmit handler {#SPEC-HOOKS-08~1}

**Status:** Active

### Behavior Contract (WHAT)

- **Inputs:** A `UserPromptSubmit` hook event dict containing `prompt`, `session_id`,
  and optional metadata fields.

- **Outputs:** No structured decision output. Emits `command_acknowledged` and
  `user_prompt` Socket.IO events as side effects.

- **Processing:**
  1. **MPM command skip:** If the prompt starts with `/mpm` and `DEBUG` is not enabled,
     returns immediately without further processing.
  2. **Alias detection:** Applies regex `^@([a-zA-Z][a-zA-Z0-9_-]*)\s` to the prompt.
     If a match is found, saves the alias to
     `~/.claude-mpm/state/last_project.json` for sticky project context.
  3. **Dashboard feedback:** Emits `command_acknowledged` immediately.
  4. **PM directive capture:** Calls `get_pm_memory().capture_directive(prompt)` to
     persist PM-level instructions to long-term memory.
  5. **Urgency classification:** Classifies the prompt as urgent if it contains
     keywords `urgent`, `error`, `bug`, `fix`, or `broken`.
  6. **Prompt storage:** Saves the prompt to `pending_prompts[session_id]` for later
     correlation with `AssistantResponse` events.
  7. **Socket.IO emission:** Emits `user_prompt` event with prompt text, urgency, and
     session metadata.

- **Cross-project message check:** Handled by a separate `message_check_hook.py`
  subprocess (wired in `settings.json`), not by this handler. The inline check was
  removed to avoid SQLite race conditions between processes.

- **Error conditions:** Each step is independently guarded. Alias detection and PM
  directive capture failures are logged and do not prevent event emission.

### Rationale (WHY)

The alias detection enables "sticky" project context: when a user types `@myproject`
at the start of a prompt, subsequent tool calls can infer the active project without
re-specifying it. PM directive capture enables persistent cross-session instructions
without requiring explicit memory commands. Separating the cross-project message check
into its own subprocess (`message_check_hook.py`) avoids SQLite write contention
between the main hook handler process and the message-check process.

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/hooks/claude_hooks/handlers/user_prompt_handler.py` | `UserPromptHandler.handle_user_prompt_fast` | Full UserPromptSubmit pipeline |
| `src/claude_mpm/hooks/message_check_hook.py` | `main` | Separate subprocess: cross-project message check |

---

## SubagentStop/Start handler and processor {#SPEC-HOOKS-09~1}

**Status:** Active

### Behavior Contract (WHAT)

- **Inputs (`SubagentStop`):** A `SubagentStop` hook event dict containing
  `session_id`, `output` (the sub-agent's full response text), and optional
  `agent_type` / `subagent_type` fields.

- **Inputs (`SubagentStart`):** A `SubagentStart` hook event dict containing
  `session_id` and optional `agent_type` / `subagent_type` fields.

- **Outputs:** No structured decision output for either event type. Side effects only.

- **SubagentStop processing (`SubagentHandler.handle_subagent_stop_fast`):**
  Delegates entirely to `SubagentResponseProcessor.process_subagent_stop(event)`.
  Falls back to the legacy `hook_handler.handle_subagent_stop(event)` method if the
  processor is unavailable.

- **`SubagentResponseProcessor.process_subagent_stop()`:**
  1. **Agent type detection:** Priority chain — (1) `StateManagerService.get_delegation_agent_type(session_id)`;
     (2) event `agent_type`/`subagent_type` fields; (3) keyword inference from the
     `task` field text; (4) default `"pm"` (sets `agent_type_inferred=True`).
  2. **Structured response extraction:** Regex-searches the `output` field for
     ` ```json ... ``` ` blocks. Logs presence of a `MEMORIES` field.
  3. **Response tracking:** Calls `StateManagerService.find_matching_request()` with
     fuzzy fallback (prefix matching on 8 or 16 chars of session ID). Calls
     `response_tracker.track_response()`. Cleans up the delegation request entry.
  4. Emits `subagent_stop` Socket.IO event.

- **SubagentStart processing (`SubagentHandler.handle_subagent_start_fast`):**
  Extracts `agent_type` (tries `agent_type`, then `subagent_type`), generates
  `agent_id`, emits `subagent_start` Socket.IO event with agent metadata.

- **Error conditions:** Failures in agent type detection default to `"pm"`. Response
  tracking failures are logged; they do not prevent event emission.

### Rationale (WHY)

Sub-agent lifecycle events (start/stop) are the primary mechanism for the dashboard
and response-tracking system to correlate delegation requests with their completions.
The fuzzy session-ID matching exists because Claude Code may generate session IDs for
sub-agents that share only a prefix with the parent session ID. The agent-type
inference fallback chain handles cases where the sub-agent's event payload does not
include explicit type information.

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/hooks/claude_hooks/handlers/subagent_handler.py` | `SubagentHandler.handle_subagent_stop_fast` | Routing to processor |
| `src/claude_mpm/hooks/claude_hooks/handlers/subagent_handler.py` | `SubagentHandler.handle_subagent_start_fast` | SubagentStart observability |
| `src/claude_mpm/hooks/claude_hooks/services/subagent_processor.py` | `SubagentResponseProcessor.process_subagent_stop` | SubagentStop processing |

---

## Event services — duplicate detector, state manager, connection manager {#SPEC-HOOKS-10~1}

**Status:** Active

### Behavior Contract (WHAT)

**`DuplicateEventDetector`**

- **`generate_event_key(event)`:** Returns a string key identifying the event.
  For `PreToolUse`: key includes session, tool name, and agent/prompt prefix.
  For `UserPromptSubmit`: includes prompt prefix. For others: event type + session.
- **`is_duplicate(event)`:** Checks the recent-events deque (maxlen=10) for a matching
  key within the `duplicate_window_seconds` window (default 0.1 s). Records
  non-duplicates. Thread-safe via deque operations.

**`StateManagerService`**

- **`track_delegation(session_id, agent_type, request_data)`:** Stores active
  delegations in an in-process dict with a history deque (maxlen=100). Cleans up
  entries older than 5 minutes.
- **`get_git_branch(working_dir)`:** Returns the current git branch for the given
  directory. Caches results per-directory for 30 seconds. Uses `os.chdir()` internally
  (see Known Drift).
- **`find_matching_request(session_id)`:** Tries exact session-ID match first, then
  prefix-based fuzzy match on first 8 or 16 characters.
- **Periodic cleanup:** Every 100 events, caps delegation dict at 200 entries and
  prompt dict at 100 entries.

**`ConnectionManagerService` (HTTP-based)**

- **`emit_event(namespace, event, data)`:** Posts the event payload to
  `http://localhost:{CLAUDE_MPM_SERVER_PORT}/api/events` via a synchronous HTTP POST
  with a 2.0 s timeout. Submission is dispatched to a `ThreadPoolExecutor` thread so
  the caller is not blocked.
- **Failure behavior:** `requests.Timeout` and `requests.ConnectionError` are caught
  and logged at debug level. Unavailability of the dashboard server never blocks hook
  processing.
- **`requests` availability:** If `requests` is not installed, emit is a no-op with a
  logged warning.

### Rationale (WHY)

`DuplicateEventDetector` exists because the same hook is registered multiple times in
`settings.json` (see Known Drift) and because Claude Code may invoke hooks in rapid
succession. The 100 ms window is chosen to catch near-simultaneous duplicates without
suppressing legitimate sequential events.

`StateManagerService` provides in-process correlation across the PreToolUse →
PostToolUse → SubagentStop event chain. In-process storage (rather than disk or
database) avoids I/O latency on the hot path.

`ConnectionManagerService` uses HTTP POST (rather than Socket.IO) because the hook
handler and the dashboard server run as separate processes, and HTTP POST is simpler
and more reliable than maintaining a persistent Socket.IO connection from a short-lived
hook subprocess.

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/hooks/claude_hooks/services/duplicate_detector.py` | `DuplicateEventDetector` | Duplicate suppression |
| `src/claude_mpm/hooks/claude_hooks/services/state_manager.py` | `StateManagerService` | In-process correlation state |
| `src/claude_mpm/hooks/claude_hooks/services/connection_manager_http.py` | `ConnectionManagerService` | Dashboard HTTP POST |

---

## Context circuit breaker {#SPEC-HOOKS-11~1}

**Status:** Active

### Behavior Contract (WHAT)

- **Inputs:** A `PreToolUse` hook event dict containing `session_id` and `cwd`.

- **Outputs:** Non-empty dict `{"hookSpecificOutput": {"permissionDecision": "deny", ...}}`
  when the breaker fires; empty dict `{}` when the breaker does not fire (pass-through).

- **State source:** Reads `<cwd>/.claude-mpm/state/context-usage.json`. This file is
  written by `ContextUsageTracker` in the `PostToolUse` handler.

- **Threshold:** `CRITICAL_THRESHOLD = 95.0` (percent). Fires when
  `state["percentage"] >= 95.0`.

- **Session-ID guard:** Only fires when `state["session_id"]` matches the current
  session ID (from event payload or `CLAUDE_SESSION_ID` env var). A stale state file
  from a prior session does not trigger a block.

- **Fail-open cases:** Returns empty dict (no block) if the state file is missing,
  unreadable, malformed JSON, or if the session IDs do not match. Returns empty dict
  if the percentage is below the threshold.

- **`main()` entrypoint:** Wraps `evaluate()` in the `hookSpecificOutput` envelope
  for standalone invocation. Not currently wired as a standalone hook in settings.json.

- **Error conditions:** All file I/O failures are caught and treated as fail-open.

### Rationale (WHY)

Prevents context window overflow that would cause Claude Code to silently drop earlier
conversation context. The 95% threshold matches `ContextUsageTracker.THRESHOLDS["critical"]`
to maintain a single source of truth for the critical threshold. Fail-open is
intentional: false denials (blocking a session due to a stale or missing state file)
are worse than false permits, because false denials require manual intervention while
false permits merely allow one more tool call before the overflow.

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/hooks/context_circuit_breaker.py` | `evaluate` | Circuit breaker decision logic |
| `src/claude_mpm/hooks/context_circuit_breaker.py` | `main` | Standalone entrypoint |

---

## Model tier enforcement {#SPEC-HOOKS-12~1}

**Status:** Active

### Behavior Contract (WHAT)

**`build_model_tier_response(event)` — called for PreToolUse on `Agent` tool calls:**

- **Inputs:** A `PreToolUse` event dict where `tool_name == "Agent"`.

- **Precondition:** Only injects a model if the `tool_input` dict does not already
  contain a `"model"` field. If a model is already specified, returns immediately with
  no modification.

- **Version gate:** Calls `supports_pretool_modify()` before injection. If the Claude
  Code version is below v2.0.30 (which does not support `updatedInput` for PreToolUse),
  skips injection and returns a no-op response.

- **Model resolution priority (highest to lowest):**
  1. `models.agents.<agent_name>` in `~/.claude-mpm/config/configuration.yaml`
     (user-level, overridden by project-level `.claude-mpm/configuration.yaml`).
  2. `model:` frontmatter field in `.claude/agents/<agent_name>.md`.
  3. Membership in the hardcoded `_HAIKU_AGENTS` set (17 agent names).
  4. Default: `claude-opus-4-7`.

- **Short-alias injection:** Resolved model IDs are mapped to short aliases via
  `_INJECT_SHORT_ALIAS` (`claude-opus-4-7 → opus`, `claude-sonnet-4-5 → sonnet`,
  `claude-haiku-4-5 → haiku`).

- **Sub-agent environment marking:** Injects `CLAUDE_MPM_SUB_AGENT: "1"` into
  `tool_input["env"]`, enabling `claude-hook-fast.sh` to skip processing for nested
  agent invocations.

- **Returns:** `{"hookSpecificOutput": {"updatedInput": modified_tool_input, "additionalContext": "..."}}`.

**`build_permission_request_response(event)` — called for PermissionRequest events:**

- Calls `permission_policy.evaluate(event)` and wraps the result in
  `{"hookSpecificOutput": {"permissionDecision": decision, "permissionDecisionReason": reason}}`.

- **Error conditions:** Both functions fail-open on any exception (returns empty or
  minimal response), preventing hook failures from blocking the Claude Code session.

### Rationale (WHY)

Model tier enforcement ensures that lightweight agents (ops, documentation, ticketing)
use cheaper Haiku-class models automatically, without requiring the user or PM to
explicitly specify models in every Agent tool call. The `_HAIKU_AGENTS` hardcoded list
provides a baseline; YAML configuration and frontmatter allow per-project overrides
without modifying code. The `CLAUDE_MPM_SUB_AGENT` injection is the mechanism that
enables `claude-hook-fast.sh` to skip recursive hook processing for sub-agent
invocations.

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/hooks/model_tier_hook.py` | `build_model_tier_response` | PreToolUse model injection |
| `src/claude_mpm/hooks/model_tier_hook.py` | `build_permission_request_response` | PermissionRequest routing |

---

## Permission gate {#SPEC-HOOKS-13~1}

**Status:** Active

### Behavior Contract (WHAT)

- **Inputs:** A `PermissionRequest` event dict containing `tool_name`, `tool_input`,
  and optionally `agent_id`, `subagent_type`, or `agent_type` fields.

- **Outputs:** A `PermissionDecision(decision, reason)` dataclass where `decision` is
  `"allow"` or `"deny"` and `reason` is a human-readable explanation string. Pure
  function; no side effects.

- **Decision priority (evaluated in order, first match wins):**
  1. `tool_name in SAFE_TOOLS` → `allow`.
     SAFE_TOOLS: `Read`, `Glob`, `Grep`, `WebSearch`, `WebFetch`, `TodoRead`,
     `TodoWrite`, `NotebookRead`, `LS`.
  2. `tool_name in MUTATING_TOOLS` AND `agent_tier in READ_ONLY_TIERS` → `deny`.
     MUTATING_TOOLS: `Edit`, `Write`, `MultiEdit`, `NotebookEdit`.
     READ_ONLY_TIERS: `research`, `qa`, `documentation-reviewer`, `code-reviewer`,
     `ticketing`.
  3. `tool_name == "Bash"` AND command matches any `DESTRUCTIVE_BASH_PATTERNS` → `deny`.
     Patterns cover: `rm -rf /`, `sudo rm`, fork bomb (`:(){ :|:& };:`), `mkfs`,
     `dd` to raw disk, redirect to raw disk, `shutdown`/`reboot`/`halt`/`poweroff`.
  4. Default → `allow` (fail-open).

- **Agent tier extraction (`_extract_agent_tier`):** Tries `agent_id`, then
  `subagent_type`, then `agent_type` fields. Normalizes via `normalize_agent_id()`.
  Returns empty string if none found (defaults to non-read-only tier behavior).

- **Error conditions:** Any exception inside `evaluate()` propagates to the caller
  (`build_permission_request_response`), which wraps it in a fail-open allow response.

### Rationale (WHY)

Introduced to replace prior unconditional-approve behavior (issue #421). Fail-open
default preserves backward compatibility for agent tiers not explicitly listed in
READ_ONLY_TIERS, while adding explicit protection for destructive filesystem and
system operations. The `SAFE_TOOLS` allowlist prevents unnecessary friction for
read-only operations that no tier should need to block.

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/hooks/permission_policy.py` | `evaluate` | Permission decision logic |
| `src/claude_mpm/hooks/permission_policy.py` | `_extract_agent_tier` | Agent tier normalization |
| `src/claude_mpm/hooks/model_tier_hook.py` | `build_permission_request_response` | Wraps PermissionDecision for hook output |

---

## Known drift

This section records places where prior documentation (CLAUDE.md, issue #523 scope
table, and the research baseline at `docs/specs/research/01-hooks-enforcement.md`)
was inaccurate about this subsystem as of the research date (2026-06-01).

**1. `claude-hook-fast.sh` is NOT the primary wired hook dispatcher.**
CLAUDE.md (line 98) calls it "the" hook dispatcher. The actual `settings.json` wires
`claude-hook` (the Python entry point) as the primary command for all events.
`claude-hook-fast.sh` is present in the scripts directory but is not listed in
`settings.json`. It runs only if explicitly invoked; it is not the production hook
command.

**2. `pretooluse_dispatcher.py` is NOT wired in `settings.json`.**
The module exists at `src/claude_mpm/hooks/pretooluse_dispatcher.py` and is
functional, but the circuit-breaker + model-tier + ztk dispatch logic it contains has
been inlined into `ToolHandler.handle_pre_tool_fast()`. Two parallel code paths for
the same logic coexist without documentation.

**3. Duplicate `claude-hook` entries in `settings.json`.**
For PreToolUse, PostToolUse, Stop, SubagentStop, and UserPromptSubmit, `claude-hook`
appears twice (with different timeouts: 15 s and 60 s). The second invocation reads
empty stdin and emits a no-op `{"continue": true}`. This is an artifact of repeated
`mpm-init` / `install_hooks()` runs. `DuplicateEventDetector` partially mitigates the
impact but does not eliminate the redundant process spawns.

**4. `is_hooks_configured()` validator — FIXED in D5, research baseline was stale.**
The research baseline (§2 drift note) stated that `is_hooks_configured()` would always
return `False` for the current `settings.json` because it only matched
`hook_wrapper.sh` or `claude-hook-handler.sh` command substrings. This was true at the
time of the original research but was **fixed as defect D5**: the current code (lines
86–89 of `hook_installer_service.py`) now also accepts the `_mpm` marker field and the
`claude-hook` command string as valid hook signatures.

**5. `connection_manager.py` is dead code; `connection_manager_http.py` is the live implementation.**
`services/__init__.py` has `connection_manager.py` commented out (line 4) and imports
`connection_manager_http.py` (line 5). The old SocketIO-based manager still exists on
disk and still references the removed EventBus architecture in its imports.

**6. `state_manager.py` uses `os.chdir()` in `get_git_branch()`.**
Line 196 of `state_manager.py` uses `os.chdir(working_dir)` — a process-global
operation. CLAUDE.md's Hooks System "Stability Patterns" section explicitly warns
against this: "Use subprocess-relative operations (`git -C`) instead of process-global
state (e.g., `os.chdir`)." This violation remains unfixed as of the research date.

**7. `SubagentHandler._handle_subagent_response_tracking()` appears to be dead code.**
The method exists at lines 29–160 of `subagent_handler.py` but the `SubagentStop`
processing path delegates entirely to `SubagentResponseProcessor.process_subagent_stop()`,
which duplicates the same fuzzy-matching and tracking logic. The handler's own method
is not called from the live dispatch path.

**8. `model_tier_hook.py` is not wired as a standalone hook.**
CLAUDE.md's description implies `model_tier_hook.py` is a directly-wired hook command.
It is not registered in `settings.json`. It is invoked exclusively via function calls
from `ToolHandler.handle_pre_tool_fast()` (for PreToolUse on `Agent` calls) and via
`build_permission_request_response()` from within the main hook handler for
PermissionRequest events.
