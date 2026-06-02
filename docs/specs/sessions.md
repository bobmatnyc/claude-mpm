# Sessions & Runtime Subsystem — Spec-Linked Documentation

**Status:** Active
**Version:** v1
**Subsystem:** SESSIONS

This document covers the Sessions & Runtime subsystem of `claude_mpm`. It spans session
lifecycle management, the two execution runtimes (CLI subprocess and SDK in-process), the
interactive SDK session entry point, the event and hook buses, Socket.IO relay
implementations, and the monitor agent watchdog.

Each section constitutes one governed specification with a stable ID, a behavior contract
(WHAT), a rationale section (WHY), and an implementing-modules table. All sections carry
`**Status:** draft (pending backfill)` — the UNCOVERED check is therefore waived until
code `References` blocks are added in a subsequent backfill phase.

---

## Table of Contents

| ID | Section | Primary module |
|----|---------|----------------|
| SPEC-SESSIONS-01~1 | [Services SessionManager — singleton token tracker](#services-sessionmanager-singleton-token-tracker-spec-sessions-011) | `services/session_manager.py` |
| SPEC-SESSIONS-02~1 | [Core SessionManager — subprocess-reuse registry](#core-sessionmanager-subprocess-reuse-registry-spec-sessions-021) | `core/session_manager.py` |
| SPEC-SESSIONS-03~1 | [SessionManagementService — session orchestration layer](#sessionmanagementservice-session-orchestration-layer-spec-sessions-031) | `services/session_management_service.py` |
| SPEC-SESSIONS-04~1 | [SDK runtime — SDKAgentRunner in-process executor](#sdk-runtime-sdkagentrunner-in-process-executor-spec-sessions-041) | `services/agents/sdk_runtime.py` |
| SPEC-SESSIONS-05~1 | [CLI runtime — CLIAgentRunner subprocess executor](#cli-runtime-cliagentrunner-subprocess-executor-spec-sessions-051) | `services/agents/cli_runtime.py` |
| SPEC-SESSIONS-06~1 | [AgentRuntime ABC, config dataclasses, and factory](#agentruntime-abc-config-dataclasses-and-factory-spec-sessions-061) | `services/agents/agent_runtime.py` |
| SPEC-SESSIONS-07~1 | [Runtime bridge and config resolution](#runtime-bridge-and-config-resolution-spec-sessions-071) | `services/agents/runtime_bridge.py`, `runtime_config.py` |
| SPEC-SESSIONS-08~1 | [Interactive SDK session — _launch_sdk_mode](#interactive-sdk-session-_launch_sdk_mode-spec-sessions-081) | `core/interactive_session.py` |
| SPEC-SESSIONS-09~1 | [SessionStateTracker — SDK session state store](#sessionstatetracker-sdk-session-state-store-spec-sessions-091) | `services/agents/session_state_tracker.py` |
| SPEC-SESSIONS-10~1 | [HookEventBus — cross-process injection queue](#hookeventbus-cross-process-injection-queue-spec-sessions-101) | `services/agents/hook_event_bus.py` |
| SPEC-SESSIONS-11~1 | [EventBus — in-process pyee event emitter](#eventbus-in-process-pyee-event-emitter-spec-sessions-111) | `services/event_bus/event_bus.py` |
| SPEC-SESSIONS-12~1 | [Socket.IO relays — DirectSocketIORelay (live) and SocketIORelay (frozen)](#socketio-relays-directsocketiorelay-live-and-socketiorelay-frozen-spec-sessions-121) | `services/event_bus/direct_relay.py`, `relay.py` |
| SPEC-SESSIONS-13~1 | [MonitorAgent — session watchdog daemon](#monitoragent-session-watchdog-daemon-spec-sessions-131) | `services/agents/monitor_agent.py` |

---

## Services SessionManager — singleton token tracker {#SPEC-SESSIONS-01~1}

**ID:** SPEC-SESSIONS-01~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

`SessionManager` in `services/session_manager.py` is a **thread-safe process-lifetime
singleton** that provides a single canonical session identifier and accumulated token
usage for the running MPM process.

- **Inputs (construction):** No caller arguments; the singleton is initialised via
  `get_session_manager()`. On first access a new instance is created using
  double-checked locking.

- **Session ID generation:** `_generate_session_id()` checks the environment variables
  `CLAUDE_SESSION_ID`, `ANTHROPIC_SESSION_ID`, and `SESSION_ID` in order, falling back
  to a `%Y%m%d_%H%M%S` timestamp string when none are set. The resulting ID is a string,
  not a UUID.

- **Token tracking:**
  - `update_token_usage(input_tokens, output_tokens, stop_reason)` accumulates against a
    hardcoded budget of 200,000 tokens and updates `_context_metrics`.
  - `should_warn_context_limit(threshold=0.70)` returns `True` when total token usage
    exceeds the given fraction of the budget.

- **Resume log integration:** `_load_resume_log()` runs from `__init__` and attempts to
  load a resume log from the most recent previous session via `ResumeLogGenerator`.
  `generate_resume_log(session_state)` writes a resume log on demand.

- **Module-level convenience functions:** `get_session_manager()` returns the singleton.
  `get_session_id()` returns the canonical session ID without holding a reference to the
  manager object.

- **Error conditions:** `reset()` is a class-method for test teardown only; calling it
  in production discards all accumulated state.

### Rationale (WHY)

The singleton addresses race conditions and duplicate session ID generation that arose
when multiple call sites each generated their own identifiers. Centralising the ID into
a single object with double-checked locking makes the session ID a reliable key for log
correlation across concurrent threads.

Protocol-based injection (`ClaudeRunnerProtocol` used in the service layer) avoids
circular imports between the service layer and the core runner; the singleton does not
need to hold a runner reference itself.

The `%Y%m%d_%H%M%S` timestamp fallback (not a UUID) is intentional: session IDs are
displayed in filenames and log prefixes where human-readable sortability matters more
than global uniqueness.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.services.session_manager` | Full implementation — singleton, ID generation, token tracking |

### Known limitations

The hardcoded `_total_budget = 200_000` is never calibrated from actual Claude Code
session data, so the threshold warnings are approximate. The `_context_metrics["model"]`
field is hardcoded to `"claude-sonnet-4.5"`, which is stale relative to the active model
`claude-sonnet-4-6` used elsewhere.

---

## Core SessionManager — subprocess-reuse registry {#SPEC-SESSIONS-02~1}

**ID:** SPEC-SESSIONS-02~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

`SessionManager` in `core/session_manager.py` is a **stateful registry** for
subprocess-reuse sessions. It is entirely unrelated to the services-layer singleton of
the same name (see SPEC-SESSIONS-01~1).

- **Inputs:** `session_dir: Path | None` — directory under which session JSON files are
  persisted. Defaults to `~/.claude-mpm/sessions/`.

- **Session creation:** `create_session(context)` generates a UUID v4 session ID,
  records it in `active_sessions` (in-memory dict), and persists a JSON file to
  `session_dir`. Returns the session ID string.

- **Session reuse:** `get_or_create_session(context)` searches `active_sessions` for a
  session whose context string matches and whose last-used timestamp is recent enough
  (configurable idle timeout). Returns the existing session ID if found; otherwise
  delegates to `create_session`.

- **Activity recording:** `record_agent_use(session_id, agent, task)` appends an entry
  to the session's `agents_run` list and updates `last_used`.

- **Cleanup:** `cleanup_expired_sessions()` iterates `active_sessions`, removes entries
  older than the idle timeout, and deletes the corresponding JSON files.

- **Lookup:** `get_session_by_id(session_id)` returns the session dict or `None`.

- **Context manager helper:** `OrchestrationSession(session_manager, context)` is a
  context manager that calls `get_or_create_session` on enter and records completion on
  exit.

- **Error conditions:** Missing session JSON files on disk do not raise; they are
  silently skipped during cleanup.

### Rationale (WHY)

This class serves orchestration scenarios where multiple tool calls or sub-agent
invocations within the same PM run should share a single Claude subprocess session (via
`--resume`) to avoid repeated context-loading costs. The reuse logic uses `context` as a
semantic key, matching sessions by the orchestration context string rather than by ID.

Persistence to disk (JSON files) allows session IDs to survive across brief MPM process
restarts (e.g., when the CLI is re-invoked) while `get_or_create_session` handles the
reconnection. The services-layer singleton (SPEC-SESSIONS-01~1) has no persistence and
is not suitable for this purpose.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.core.session_manager` | Full implementation — registry, reuse, persistence |

---

## SessionManagementService — session orchestration layer {#SPEC-SESSIONS-03~1}

**ID:** SPEC-SESSIONS-03~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

`SessionManagementService` is a `BaseService` + `SessionManagementInterface` subclass
that acts as the orchestration layer for launching Claude sessions. It does not spawn
subprocesses directly; it delegates to `InteractiveSession` and `OneshotSession` from
the core layer.

- **Inputs (construction):** `runner` — optional object satisfying
  `ClaudeRunnerProtocol`. Used by `run_oneshot_session` to call
  `command_handler_service.is_mpm_command()`. Resolved at `TYPE_CHECKING` time to avoid
  circular imports.

- **`run_interactive_session(initial_context)`:** Delegates to `InteractiveSession` in a
  three-step flow: initialize, setup environment, handle interactive I/O.

- **`run_oneshot_session(prompt, context)`:** Delegates to `OneshotSession` in a
  five-step flow: initialize, deploy agents, setup infrastructure, execute command,
  cleanup.

- **Session log operations:**
  - `create_session_log_file()` creates a timestamped `.jsonl` file under
    `.claude-mpm/logs/sessions/` with an 8-character UUID suffix. Returns the file path.
  - `log_session_event(log_file, event_data)` appends a JSON line with a UTC timestamp.

- **In-memory session tracking:**
  - `start_session(session_config)` creates a UUID-keyed record in `active_sessions`
    (in-memory dict). Returns the UUID as the session ID.
  - `end_session(session_id)` removes the record from `active_sessions`.
  - `get_service_status()` returns a dict with runner availability and active session
    count.

- **`cleanup_sessions()`:** Async method that purges records from `active_sessions` older
  than 24 hours. No callers exist in production code; it is only called from tests.
  Because `active_sessions` is in-memory only, the cleanup has no effect across process
  restarts.

- **Error conditions:** Session IDs generated by `start_session()` (UUID v4) exist in a
  completely separate namespace from IDs generated by the services-layer singleton
  (SPEC-SESSIONS-01~1) or the core registry (SPEC-SESSIONS-02~1).

### Rationale (WHY)

The service was extracted from `ClaudeRunner` to follow the Single Responsibility
Principle: `ClaudeRunner` is responsible for assembling and launching the Claude
subprocess; the service is responsible for session lifecycle bookkeeping. Protocol-based
runner injection (`ClaudeRunnerProtocol`) breaks the circular import that would otherwise
arise between the service layer and the runner.

The `active_sessions` dict is intentionally in-memory only: the service is designed for
a single long-running process, and persisting session state across restarts was judged
out of scope for this extraction.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.services.session_management_service` | Full implementation — orchestration, log creation, in-memory tracking |

---

## SDK runtime — SDKAgentRunner in-process executor {#SPEC-SESSIONS-04~1}

**ID:** SPEC-SESSIONS-04~1
**Status:** draft (pending backfill)

> **Note:** `SDKAgentRunner` is **fully implemented** but is designated **frozen /
> unsupported** by project decision (epic #355 closed). The implementation must not be
> removed, as `_launch_sdk_mode()` (SPEC-SESSIONS-08~1) depends on `ClaudeSDKClient`
> from the same SDK package. However, `SDKAgentRunner` itself is not wired into the
> primary interactive session path and is not under active development.

### Behavior Contract (WHAT)

`SDKAgentRunner(AgentRuntime)` executes prompts against the Claude API in-process using
the `claude-agent-sdk` Python package. The package is imported with a graceful fallback:
if `claude_agent_sdk` is not installed, `SDK_AVAILABLE = False` is set and `None`
sentinel values are assigned so the module still imports cleanly.

- **Inputs (construction):** `system_prompt`, `model`, `cwd`, `max_turns`,
  `allowed_tools`, `permission_mode`, `mcp_servers`. Raises `RuntimeError` immediately
  if `SDK_AVAILABLE` is False.

- **Factory constructors:**
  - `from_config(config: AgentConfig)` — creates from a runtime-agnostic config object;
    calls `resolve_model_to_sdk()` for name translation.
  - `from_agent_template(template_path, mcp_servers)` — loads an MPM agent template
    JSON and extracts `narrative_fields.instructions` or `system_prompt`, model,
    allowed_tools, permission_mode, cwd, max_turns.

- **Execution modes:**
  - `run(prompt, config)` — one-shot via `sdk_query()`.
  - `run_with_hooks(prompt, tool_guard, blocked_tools, config)` — persistent session via
    `ClaudeSDKClient` with a `can_use_tool` async callback for tool interception.
  - `inject(prompts, config)` — multi-turn: sends each prompt sequentially, waiting for
    `ResultMessage` before the next.
  - `resume(session_id, prompt, config)` — resumes a completed session via
    `options.resume=session_id`.
  - `fork(session_id, prompt, config)` — branches history via
    `options.resume=session_id, fork_session=True`.
  - `run_streaming(prompt, on_text, on_tool_call, config)` — fires async callbacks per
    `TextBlock`/`ToolUseBlock` as they arrive.
  - `interruptible(**overrides) -> InterruptibleSession` — returns a context manager
    wrapping `ClaudeSDKClient` with `interrupt()` support.

- **Output style injection:** `_build_options()` loads output style via
  `get_output_style_for_injection()` and prepends it to the system prompt. This
  compensates for SDK sessions not loading `~/.claude/settings.json` natively.

- **Data structures:**
  - `ToolCallRecord` — captures a single tool invocation (name, input, output, approved,
    timestamp).
  - `SDKAgentResult` — structured result with text, session_id, tool_calls, cost_usd,
    num_turns, duration_ms, is_error, raw_messages.
  - `InterruptibleSession` — async context manager with `query(prompt)` and
    `interrupt()` methods.

- **Error conditions:** `RuntimeError` on construction when SDK is unavailable.
  Individual method failures surface as `SDKAgentResult.is_error = True`.

### Rationale (WHY)

`SDKAgentRunner` was built to enable in-process Claude execution, allowing the MPM
process to survive after a session completes and to intercept tool calls via the
`tool_guard` callback. The `AgentRuntime` ABC makes the caller backend-agnostic.

The implementation is frozen because `_launch_sdk_mode()` (SPEC-SESSIONS-08~1) drives
the primary interactive SDK session directly via `ClaudeSDKClient`, bypassing
`SDKAgentRunner`. The runner is used only in sidecar injection scenarios
(`runtime_bridge.execute_agent_prompt()`), not in the main interactive loop. No new
capabilities will be added to `SDKAgentRunner` under the project decision to leave epic
#355 closed.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.services.agents.sdk_runtime` | Full implementation — SDKAgentRunner, SDKAgentResult, ToolCallRecord, InterruptibleSession |

---

## CLI runtime — CLIAgentRunner subprocess executor {#SPEC-SESSIONS-05~1}

**ID:** SPEC-SESSIONS-05~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

`CLIAgentRunner(AgentRuntime)` wraps the `claude` CLI subprocess to implement the
`AgentRuntime` ABC. It uses `asyncio.create_subprocess_exec` directly.

- **Inputs (construction):** `system_prompt`, `model`, `cwd`, `max_turns`. Does NOT
  accept `allowed_tools`, `permission_mode`, `max_budget_usd`, or `mcp_servers`, making
  it a strict subset of `SDKAgentRunner`'s configuration surface.

- **`_build_cli_args(prompt, resume_session, fork, output_json)`:** Assembles
  `["claude", "-p", "--output-format", "json", "--model", ..., "--max-turns", ...,
  "--resume", ..., "--fork-session", "--system-prompt", ..., prompt]`.

- **`_invoke(prompt, resume_session, fork, config)`:** Launches the subprocess via
  `asyncio.create_subprocess_exec`. Config overrides are applied temporarily and
  restored in a `finally` block.

- **`_parse_output(raw, duration_ms)`:** Attempts JSON parse; falls back to raw text.
  Extracts `result`/`text`, `session_id`, `cost_usd`, `num_turns`, `is_error`.

- **Execution modes:**
  - `run(prompt, config)` — one-shot.
  - `run_with_hooks(...)` — raises `NotImplementedError`; the CLI subprocess does not
    expose tool interception.
  - `resume(session_id, prompt, config)` — passes `--resume session_id`.
  - `fork(session_id, prompt, config)` — passes `--resume session_id --fork-session`.

- **Error conditions:** Subprocess failures surface via `AgentResult.is_error`.
  `run_with_hooks` raises `NotImplementedError` always.

### Rationale (WHY)

The CLI runner provides a fallback execution path for environments where
`claude-agent-sdk` is not available. It is also the backend for sidecar injection
scenarios (`runtime_bridge.execute_agent_prompt()`) when the runtime is resolved to
`"cli"`.

The CLI runner is not used in the primary interactive session path. `_launch_sdk_mode()`
uses `ClaudeSDKClient` directly; `_launch_exec_mode()` and `_launch_subprocess_mode()`
use `os.execvpe` and PTY subprocess respectively. The CLI runner covers only the
sidecar/injection use case.

The absence of `allowed_tools`, `permission_mode`, and `mcp_servers` support reflects
the limitations of the CLI subprocess interface: those capabilities require in-process
SDK control. The feature gap is accepted because the CLI runner is not the primary
interactive path.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.services.agents.cli_runtime` | Full implementation — CLIAgentRunner |

### Known limitations

The module-level docstring and the class docstring both claim the runner "wraps
`ClaudeAdapter`". This is historically inaccurate: the class does not import
`ClaudeAdapter` and spawns subprocesses natively via `asyncio.create_subprocess_exec`.
The docstrings are stale and should be corrected in a future cleanup.

---

## AgentRuntime ABC, config dataclasses, and factory {#SPEC-SESSIONS-06~1}

**ID:** SPEC-SESSIONS-06~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

`agent_runtime.py` provides the shared type definitions and factory used by both
`SDKAgentRunner` and `CLIAgentRunner`.

- **`AgentResult` (dataclass):** `text`, `session_id`, `tool_calls` (list of dicts),
  `cost_usd`, `num_turns`, `duration_ms`, `is_error`.

- **`AgentConfig` (dataclass):** `system_prompt`, `model`, `allowed_tools`,
  `permission_mode`, `cwd`, `max_turns`, `max_budget_usd`, `mcp_servers`.

- **Model name translation:**
  - `_MPM_TO_SDK_MODEL` table: `"sonnet"` → `"claude-sonnet-4-6-20260124"`,
    `"opus"` → `"claude-opus-4-20250514"`, `"haiku"` → `"claude-haiku-3-20250307"`.
  - `resolve_model_to_sdk(model)` — converts MPM short names to SDK full names; passes
    through unknown names unchanged.
  - `resolve_model_to_mpm(model)` — inverse mapping.

- **`AgentRuntime` (ABC):** Abstract methods `run()`, `run_with_hooks()`, `resume()`,
  `fork()`, and abstract property `runtime_name`. Both concrete runners must satisfy
  this interface.

- **`create_runtime(runtime_type, config)` (factory):** Accepts `"sdk"` (default) or
  `"cli"`. Returns a constructed `SDKAgentRunner` or `CLIAgentRunner`. Raises
  `ValueError` for unknown types.

- **Error conditions:** `create_runtime` raises `ValueError` on unknown `runtime_type`.
  `SDKAgentRunner.__init__` raises `RuntimeError` if called when SDK is unavailable.

### Rationale (WHY)

Defining `AgentResult` and `AgentConfig` in a shared module decouples the two runtime
implementations from each other: neither must import the other, and callers (such as
`runtime_bridge`) can work with the shared dataclasses without depending on a specific
backend.

The model translation table centralises the mapping from MPM's human-readable names to
SDK's datestamped names in one location, preventing the mapping from diverging across
the codebase.

The factory default of `"sdk"` reflects the primary intended runtime; the `"cli"`
fallback is always available regardless of SDK package installation.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.services.agents.agent_runtime` | AgentResult, AgentConfig, model translation, AgentRuntime ABC, create_runtime factory |

---

## Runtime bridge and config resolution {#SPEC-SESSIONS-07~1}

**ID:** SPEC-SESSIONS-07~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

Two thin modules connect the factory (SPEC-SESSIONS-06~1) to callers that do not need
typed `AgentResult` objects.

**`runtime_config.py`:**

- **`get_runtime_type()`:** Resolution order:
  1. `CLAUDE_MPM_RUNTIME` env var (`"sdk"` or `"cli"`).
  2. Auto-detect: `import claude_agent_sdk` — returns `"sdk"` if available, else
     `"cli"`.
  Returns a string.

- **`get_runtime(config)`:** Calls `get_runtime_type()` then `create_runtime()`. Returns
  a constructed `AgentRuntime` instance.

**`runtime_bridge.py`:**

- **`execute_agent_prompt(prompt, session_id, ...)`:** Unified async entry point. If
  `session_id` is provided, calls `runtime.resume(session_id, prompt)`; otherwise calls
  `runtime.run(prompt)`. Returns a plain dict with keys: `text`, `session_id`,
  `cost_usd`, `num_turns`, `duration_ms`, `is_error`, `tool_calls`, `runtime`.

- **Error conditions:** Exceptions from the underlying runtime propagate unchanged.

### Rationale (WHY)

`runtime_bridge` provides a single dict-returning async function for callers (message
endpoint, sidecar agents) that do not need the typed `AgentResult`. Keeping this thin
bridge separate from the ABC and factory avoids forcing all callers to import the full
runtime hierarchy.

`runtime_config` avoids reading `configuration.yaml` intentionally: the in-code
docstring (line 9) states that the config-file path "is intentionally omitted for now
since the unified config system can layer this on top later." Env-var-based resolution
is sufficient for current use cases and avoids circular import with the config loader.

The `--sdk` flag flow in `run.py` sets `CLAUDE_MPM_RUNTIME=sdk` via env var, which
`runtime_config.get_runtime_type()` then reads. `ClaudeRunner` stores `launch_method`
as-is without validation; the `"sdk"` value is passed through correctly to
`InteractiveSession._launch_sdk_mode()` even though the `ClaudeRunner` constructor
docstring says it only accepts `"exec"` or `"subprocess"`.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.services.agents.runtime_config` | `get_runtime_type`, `get_runtime` |
| `claude_mpm.services.agents.runtime_bridge` | `execute_agent_prompt` |

---

## Interactive SDK session — _launch_sdk_mode {#SPEC-SESSIONS-08~1}

**ID:** SPEC-SESSIONS-08~1
**Status:** draft (pending backfill)

> **Correctness note:** Prior research documents (`sdk-runtime-current-state-2026-05-04.md`,
> line 82) claimed `_launch_sdk_mode()` "DOES NOT EXIST." This was incorrect. The
> function is fully implemented at `src/claude_mpm/core/interactive_session.py` line 660.
> The SDK Runtime epic (#355) was closed based on that stale information. The function
> exists, is wired, and is the primary interactive SDK execution path.

### Behavior Contract (WHAT)

`InteractiveSession._launch_sdk_mode()` is the entry point for an interactive Claude
session that keeps the MPM process alive (as opposed to `_launch_exec_mode`, which
replaces the process via `os.execvpe`). It runs an `asyncio` event loop via
`asyncio.run(_run_sdk_session())`.

- **Preconditions:** `claude_agent_sdk` must be importable; if not, the method logs an
  error and returns `False`.

- **Setup sequence:**
  1. Builds system prompt from `self.runner._create_system_prompt()`.
  2. Detects GitHub context and injects it (best-effort, 3-second timeout).
  3. Sets up `HookEventBus` and a `PreToolUse` hook via `hook_factory.create_pretooluse_hook()`.
  4. Selects model: `CLAUDE_MPM_PM_MODEL` env var → `~/.claude/settings.json` `"model"`
     field → `"claude-sonnet-4-6"`.
  5. Sets `CLAUDE_CODE_SUBAGENT_MODEL=claude-sonnet-4-6` if not already set.
  6. Creates `ClaudeAgentOptions` with system_prompt, cwd, permission_mode, hooks config.
  7. Initialises `SessionStateTracker` and sets it as the global tracker.
  8. Parses `--resume` from `runner.claude_args` if present.
  9. Starts `MonitorAgent` (best-effort; failure is a no-op).
  10. Starts `SDKEventBridge` (best-effort; failure disables dashboard streaming).

- **Main loop (`async with ClaudeSDKClient`):**
  1. Creates `SDKCommandRouter(client, tracker)` for slash commands.
  2. Reads from stdin; routes `/command` strings through the command router; sends other
     input via `client.query(user_input)`.
  3. Processes response messages:
     - `AssistantMessage` → `TextBlock` (print + tracker); `ToolUseBlock` (tracker +
       agent tracking).
     - `ResultMessage` → `tracker.record_result()`.
     - `SystemMessage` → display.

- **State machine transitions (via tracker):**
  - `user_input` → `record_user_input()` → state `PROCESSING`.
  - `ToolUseBlock` → `record_tool_call(tool_name)` → state `TOOL_CALL`.
  - `ResultMessage` → `record_result()` → state `IDLE`.
  - On exit → `record_stopped()` → state `STOPPED`.

- **Teardown:** Calls `monitor.stop()` if the monitor was started.

- **Outputs:** Returns `bool` — `True` on clean exit, `False` on startup failure.

- **Channels fork:** If `runner.channels` or `CLAUDE_MPM_CHANNELS` is set,
  `_launch_sdk_mode()` delegates to `_launch_channel_hub_mode()` instead of running the
  main loop. This is an undocumented alternative flow.

### Rationale (WHY)

`_launch_exec_mode()` replaces the MPM process entirely via `os.execvpe`, which prevents
any post-session cleanup, monitoring, or message injection. `_launch_sdk_mode()` keeps
the MPM process alive so that `MonitorAgent`, `HookEventBus`, `SDKEventBridge`, and
`SessionStateTracker` can run alongside the Claude session.

SDK mode is the only execution path where the full monitoring and injection stack is
active. In exec and subprocess modes, `get_global_tracker()` returns `None` and no
monitor runs.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.core.interactive_session` | `InteractiveSession._launch_sdk_mode` (line 660) — primary SDK session loop |

---

## SessionStateTracker — SDK session state store {#SPEC-SESSIONS-09~1}

**ID:** SPEC-SESSIONS-09~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

`SessionStateTracker` is a thread-safe state store for the SDK interactive session,
updated by the asyncio REPL thread and read by HTTP monitoring handlers.

- **`SessionState` enum:** `IDLE`, `PROCESSING`, `TOOL_CALL`, `STARTING`, `STOPPED`.

- **Write methods (asyncio thread):** `set_state()`, `set_session_id()`, `set_model()`,
  `record_user_input()`, `record_tool_call()`, `record_tool_result()`,
  `record_assistant_message()`, `record_result()`, `record_stopped()`. All writes are
  protected by a `threading.Lock`.

- **Activity buffer:** `deque(maxlen=100)` of `ActivityEvent` records. Each event has:
  type, timestamp, preview (first 200 characters), tool name, status (`"running"` /
  `"complete"` / `"error"`), metadata.

- **Read methods (HTTP thread):**
  - `get_session_state() -> dict` — returns a snapshot of current state, session ID,
    model, token counts, and context usage.
  - `get_activity(limit) -> list[dict]` — returns the most recent `limit` events from
    the activity buffer.

- **Module-level singleton:** `_global_tracker: SessionStateTracker | None = None` with
  `get_global_tracker()` and `set_global_tracker()`. Set by `_launch_sdk_mode()` at
  session start. Returns `None` in exec/subprocess mode.

- **Preconditions:** Only populated in SDK mode. In exec or subprocess mode,
  `get_global_tracker()` returns `None`. Callers must check for `None` before
  dereferencing.

- **Error conditions:** `MonitorAgent._check_session_health()` returns early if
  `get_global_tracker()` returns `None`, preventing null-dereference in non-SDK modes.

### Rationale (WHY)

The tracker decouples the asyncio REPL thread from the HTTP monitoring thread: the REPL
writes state under a lock; the HTTP handlers read snapshots without waiting for the
asyncio loop. This design avoids deadlocks between the event loop and Flask/FastAPI
request handlers.

The `deque(maxlen=100)` activity buffer bounds memory use: old events are discarded
automatically as new ones arrive, with no manual cleanup required.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.services.agents.session_state_tracker` | `SessionStateTracker`, `SessionState`, `get_global_tracker`, `set_global_tracker` |

---

## HookEventBus — cross-process injection queue {#SPEC-SESSIONS-10~1}

**ID:** SPEC-SESSIONS-10~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

`HookEventBus` is a **file-based message queue** that enables cross-process
communication between sidecar agents (and the monitor) and the PM Claude Code session
via the hook `systemMessage` injection mechanism.

- **Queue file:** `~/.claude-mpm/hook_messages.jsonl` (JSON-lines format, default path).

- **`MessagePriority` enum:** `CRITICAL` (0), `HIGH` (1), `NORMAL` (2), `LOW` (3).

- **`HookMessage` dataclass:** `text`, `priority`, `source` (e.g., `"monitor"`,
  `"ci"`), `timestamp`, `metadata`. Serialises via `to_dict()` / deserialises via
  `from_dict()`.

- **`send(message)`:** Appends a JSON line to the queue file using `fcntl.LOCK_EX`
  exclusive file locking.

- **`consume()`:** Reads all lines from the queue file, truncates the file (exclusive
  lock), parses all `HookMessage` instances, sorts by priority (CRITICAL first), and
  returns `list[HookMessage]`. Callers receive all pending messages in priority order.

- **`consume_for_hook()`:** Called by the `PreToolUse` hook on each tool call.
  Increments `_tool_call_count`. `LOW`-priority messages are deferred (re-queued) unless
  `tool_call_count % 5 == 0`. Returns a formatted string for `systemMessage` injection,
  or `None` if nothing to inject.

- **File locking:** Uses POSIX `fcntl.flock()`. Not portable to Windows environments;
  no fallback is provided.

### Rationale (WHY)

File-based queuing allows processes with no shared memory — sidecar agents running as
separate Python processes, monitor agent background threads, CI hooks — to communicate
with the PM session across process boundaries. The PM reads messages on each tool call
via the `PreToolUse` hook, so injections appear at natural breakpoints in Claude's
activity.

`LOW`-priority deferral (every 5 tool calls) prevents low-priority messages from
flooding Claude with injections on every call. `CRITICAL`-priority messages are always
injected immediately.

`HookEventBus` and `EventBus` (SPEC-SESSIONS-11~1) are entirely separate systems: the
hook bus is for cross-process PM injection; the event bus is for in-process dashboard
streaming. They are not connected.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.services.agents.hook_event_bus` | `HookEventBus`, `HookMessage`, `MessagePriority` |

---

## EventBus — in-process pyee event emitter {#SPEC-SESSIONS-11~1}

**ID:** SPEC-SESSIONS-11~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

`EventBus` is a **singleton** backed by `pyee.asyncio.AsyncIOEventEmitter`. It provides
both sync publishing and async/sync handler registration, and serves as the in-process
backbone for dashboard streaming.

- **`_enabled`:** Global on/off switch. When `False`, all `publish()` calls are no-ops.

- **`_event_filters`:** Set of allowed patterns. If empty, all events pass. Patterns
  ending with `"*"` match by prefix.

- **`_event_history`:** `deque(maxlen=100)` for debugging; stores the last 100
  published events.

- **`publish(event_type, data)`:** Sync, thread-safe. Checks `_enabled`, applies
  filters, records in history, emits via pyee, walks `_wildcard_handlers`. Updates stats
  (`events_published`, `events_filtered`, `events_failed`, `last_event_time`).

- **`publish_async(event_type, data)`:** Delegates to `publish()`; pyee handles both
  sync and async handlers.

- **`on(event_type, handler)`:** If `event_type` ends with `"*"`, stores in
  `_wildcard_handlers` by prefix; otherwise wraps in a try/except safe handler and
  registers with pyee.

- **`remove_all_listeners()`:** Removes pyee-registered handlers. Does NOT remove
  wildcard handlers from `_wildcard_handlers`; wildcard handlers accumulate unless the
  singleton is reset.

- **Default relay state:** `EventBusConfig.relay_enabled` defaults to `False`
  (`CLAUDE_MPM_RELAY_ENABLED=false`). The in-code comment confirms: "DirectSocketIORelay
  disabled by default — events already emit via direct `sio.emit()`."

- **Error conditions:** Handler exceptions within pyee-registered callbacks are caught by
  the safe-handler wrapper and logged; they do not propagate to the publisher.

### Rationale (WHY)

The event bus decouples hook handlers from the Socket.IO implementation: handlers emit
events; Socket.IO consumers subscribe. This allows multiple consumers (dashboard,
logging, tests) for the same events without coupling them to a specific transport.

The singleton ensures a single point of event coordination and prevents duplicate event
processing across the codebase.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.services.event_bus.event_bus` | `EventBus` singleton, publish, on, wildcard handlers |
| `claude_mpm.services.event_bus.config` | `EventBusConfig` — env-var-driven configuration |

---

## Socket.IO relays — DirectSocketIORelay (live) and SocketIORelay (frozen) {#SPEC-SESSIONS-12~1}

**ID:** SPEC-SESSIONS-12~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

Two classes bridge the `EventBus` to the Socket.IO dashboard transport. Only
`DirectSocketIORelay` is active in the default configuration.

**`DirectSocketIORelay` (`direct_relay.py`) — ACTIVE:**

- Subscribes to `EventBus` events and emits them directly via the Socket.IO server's
  internal broadcaster, bypassing the client-connection loopback.
- Uses the Socket.IO server object (`sio`) that was passed in at construction time. Does
  not create a client connection.
- Disabled (logs warning and returns) when its `enabled` flag is `False`.
- Used when `EventBusConfig.relay_enabled` is `True` AND the direct relay is configured.
  The default configuration has `relay_enabled=False` because events are emitted via
  `sio.emit()` in the server handlers directly, making relay optional.

**`SocketIORelay` (`relay.py`) — FROZEN / DEAD CODE in default configuration:**

- Creates a Socket.IO *client* that connects back to the server on `localhost`. Events
  received from `EventBus` are forwarded through this client connection.
- Acknowledged as broken in `DirectSocketIORelay`'s docstring: "The original
  SocketIORelay creates a client connection back to the server, causing events to not
  reach the dashboard properly."
- Disabled by default (`CLAUDE_MPM_RELAY_ENABLED=false`). Retained in the codebase but
  not used in normal operation.

- **Module-level singleton for `SocketIORelay`:** `get_relay(port)` and
  `start_relay(port)` manage a single `SocketIORelay` instance. These functions are not
  called from production paths in the default configuration.

### Rationale (WHY)

`DirectSocketIORelay` was introduced specifically to fix the loopback problem in
`SocketIORelay`: when the relay creates a client connection back to the server, events
travel through an extra network hop that does not reach the dashboard event handlers
correctly. The direct path uses the server's broadcaster directly, eliminating the
loopback.

`SocketIORelay` is retained (not deleted) because removing it would require updating
references and tests before the impact can be fully assessed. It is treated as frozen
code. Any future work on dashboard streaming should use `DirectSocketIORelay` or the
direct `sio.emit()` path.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.services.event_bus.direct_relay` | `DirectSocketIORelay` — active relay via server broadcaster |
| `claude_mpm.services.event_bus.relay` | `SocketIORelay` — frozen, client-loopback relay; not used in default config |

---

## MonitorAgent — session watchdog daemon {#SPEC-SESSIONS-13~1}

**ID:** SPEC-SESSIONS-13~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

`MonitorAgent` is a background watchdog daemon thread that polls session health and
injects warnings into the PM via `HookEventBus`. It is active only in SDK mode.

- **`MonitorConfig` (dataclass):** All thresholds. Key fields:
  - `token_limit = 200_000` (matches services `SessionManager`).
  - `warn_thresholds = [70, 80, 90, 95]` percent levels.
  - `poll_interval = 10.0` seconds.
  - `max_session_duration = 3600` seconds.
  - `idle_timeout = 300` seconds.
  - `auto_pause_threshold = 95` — triggers CRITICAL + auto-postmortem.
  - `consecutive_bash=5`, `consecutive_read=3`, `consecutive_write=3`,
    `consecutive_direct=8` — tool-pattern thresholds.

- **Lifecycle:**
  - `start()` — spawns a daemon thread named `"mpm-monitor-agent"`.
  - `stop()` — calls `_trigger_postmortem(reason="stop")` then sets the stop event.
    Joins thread with 5-second timeout.
  - `is_running` property — checks `_thread.is_alive()`.

- **Health checks (each `poll_interval`):**
  1. `_check_context_pressure(state)` — reads `state["context_usage"]["tokens_used"]`
     from `SessionStateTracker`; fires per-threshold warnings. At 95%: sends CRITICAL
     and triggers `_trigger_postmortem(reason="critical_context")`.
  2. `_check_session_duration(state)` — fires once when uptime ≥ 80% of
     `max_session_duration`.
  3. `_check_idle_too_long(state)` — fires if state is `"processing"` and last activity
     is > 300 seconds ago.
  4. `_check_tool_call_patterns()` — walks last 50 activity events in reverse.
     Categorises tools into five groups (implementation, investigation, execution,
     delegation, passive). Tracks streaks with peak values across category switches.
     Fires circuit-breaker warnings labelled "PM CIRCUIT BREAKER #2".
  5. `_check_per_query_limits(events)` — finds the most recent `user_input` event as a
     query boundary; counts investigation/read/vector-search tools since that boundary.
     Thresholds: `investigation_count >= 4`, `read_count >= 3`,
     `vector_search_count >= 2`.
  6. `_check_incoming_messages()` — bridges `/mpm-message` tasks via `TaskInjector` to
     the PM session via `HookEventBus`. Deduplicates by task ID.

- **Tool categories (class-level):**
  - `_DELEGATION_TOOLS`: `{"Agent", "Task", "TaskCreate", "TaskUpdate"}`
  - `_IMPLEMENTATION_TOOLS`: `{"Write", "Edit", "NotebookEdit"}`
  - `_INVESTIGATION_TOOLS`: `{"Read", "Grep", "Glob"}`
  - `_EXECUTION_TOOLS`: `{"Bash"}`
  - `_PASSIVE_TOOLS`: `{"TodoWrite", "TaskList", "TaskGet", "ToolSearch", "AskUserQuestion"}`
  - MCP vector-search tools (`mcp__mcp-vector-search__*`) count as investigation.
  - `mcp__kuzu-memory__kuzu_recall`: first two calls are free; call 3+ counts as
    investigation.

- **Auto-postmortem:** `_trigger_postmortem(reason)` is idempotent per reason (tracked
  in `_postmortem_triggered`). Spawns a daemon thread calling `_run_postmortem()`.
  Saves markdown reports to `~/.claude-mpm/postmortems/` with format
  `{timestamp}-{session_id}-{reason}.md`.

- **Message injection:** `_inject_message(text, priority)` calls
  `HookEventBus.send()` with `source="monitor"`.

- **Ownership:** The monitor is created and owned by `_launch_sdk_mode()`. It is not a
  global singleton. In exec/subprocess mode no monitor runs.

### Rationale (WHY)

The monitor runs in a background daemon thread so that it can observe the session
continuously without interrupting the asyncio REPL loop. File-based injection via
`HookEventBus` allows the daemon thread to communicate with Claude across the
asyncio/threading boundary without shared-memory coordination.

Circuit-breaker warnings (tool-pattern checks) address the behaviour where an AI agent
enters a prolonged investigation loop, preventing convergence. Injecting warnings via
`systemMessage` creates a soft interrupt that the PM sees at the next tool boundary
without halting the session.

Auto-postmortem on CRITICAL context pressure (95%) produces a saved record of the
session state before compaction or termination, preserving context for resumption.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.services.agents.monitor_agent` | `MonitorAgent`, `MonitorConfig` — full watchdog implementation |

---

## Known drift

This section records confirmed discrepancies between the prior research documentation,
project issue tracker assumptions, and the actual current codebase. All items were
verified by direct code inspection during this spec authoring pass.

### SDK mode is fully implemented (contradicts stale research)

Prior research (`docs/research/sdk-runtime-current-state-2026-05-04.md`, line 82)
stated `_launch_sdk_mode()` "DOES NOT EXIST." This was incorrect. The function is a
fully implemented 717-line interactive session at
`src/claude_mpm/core/interactive_session.py` line 660. `MonitorAgent` is instantiated
and running in this path (`interactive_session.py` lines 882–887).

**Project decision:** Epic #355 ("SDK Runtime") was closed "won't do" based on the stale
research. The closure stands as a project decision to not actively develop new SDK runtime
capabilities. SDK mode is therefore treated as **implemented but frozen / unsupported**:
the code exists and runs, but no new features will be added under the current project
direction. `SDKAgentRunner` (SPEC-SESSIONS-04~1) is specifically frozen; the
`_launch_sdk_mode()` path (SPEC-SESSIONS-08~1) is its own separate concern and is
the primary interactive SDK entry point.

### Two unrelated classes named `SessionManager`

- `src/claude_mpm/services/session_manager.py` — thread-safe singleton with token
  tracking, process-lifetime session ID, resume log integration. ID format:
  `%Y%m%d_%H%M%S` timestamp or env-var value.
- `src/claude_mpm/core/session_manager.py` — subprocess-reuse registry with UUID
  session IDs persisted to `~/.claude-mpm/sessions/`. Entirely different purpose.

Both classes are named `SessionManager`. Neither is referenced in CLAUDE.md.
Importers must use the fully qualified module path to distinguish them.

### Two Socket.IO relay implementations

- `SocketIORelay` (`services/event_bus/relay.py`) — creates a Socket.IO client that
  connects back to the server on localhost. Acknowledged as broken in
  `DirectSocketIORelay`'s docstring. Disabled by default.
- `DirectSocketIORelay` (`services/event_bus/direct_relay.py`) — uses the server's
  internal broadcaster directly. Active path.

`SocketIORelay` is retained in the codebase but is dead code in the default
configuration.

### CLIAgentRunner docstring falsely claims it wraps ClaudeAdapter

The module-level docstring of `cli_runtime.py` (line 3) and the class docstring (line
31) both state the runner "wraps `ClaudeAdapter`." The implementation does not import
`ClaudeAdapter` and spawns subprocesses natively via `asyncio.create_subprocess_exec`.
The docstrings are historically stale and should be corrected.

### SessionManagementService.cleanup_sessions is dead code

`SessionManagementService.cleanup_sessions()` (line 295 of
`services/session_management_service.py`) is an async method that purges sessions older
than 24 hours. No production callers exist; it is invoked only in tests. Additionally,
`active_sessions` is in-memory only, so the cleanup has no persistent effect. The method
satisfies the `SessionManagementInterface` ABC requirement and may be retained for that
reason, but its practical utility is nil.

### services/SessionManager hardcodes stale model name

`services/session_manager.py` line 87 hardcodes `"claude-sonnet-4.5"` in
`_context_metrics["model"]`. The active model used throughout the codebase and in the
model mapping table (`agent_runtime.py`) is `"claude-sonnet-4-6-20260124"`. The stale
name makes the token tracking metadata misleading.
