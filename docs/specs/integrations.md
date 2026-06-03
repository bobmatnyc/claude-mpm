# Integrations & Infrastructure Subsystem — Spec-Linked Documentation

**Status:** Active
**Version:** v1
**Subsystem:** INTEGRATIONS

This document covers the Integrations & Infrastructure subsystem of `claude_mpm`, spanning
MCP service discovery and configuration, memory enrichment and persistence (multi-backend
dispatcher with trusty-memory as primary and kuzu-memory as live fallback), the version-based
migrations system, and the Dashboard/UI service.

Each section constitutes one governed specification with a stable ID, a behavior contract
(WHAT), a rationale section (WHY), and an implementing-modules table. All sections carry
`**Status:** draft (pending backfill)` — the CI UNCOVERED check is therefore exempted
until implementing modules add matching `References` docstring blocks.

---

## Table of Contents

| ID | Section | Primary implementing unit |
|----|---------|--------------------------|
| SPEC-INTEGRATIONS-01~1 | [Trusty service address discovery](#trusty-service-address-discovery-spec-integrations-011) | `TrustyMixin._trusty_search_base_url`, `_trusty_memory_base_url` |
| SPEC-INTEGRATIONS-02~1 | [Trusty MCP service setup](#trusty-mcp-service-setup-spec-integrations-021) | `TrustyMixin._setup_trusty_search`, `_setup_trusty_memory`, `_setup_trusty_analyze` |
| SPEC-INTEGRATIONS-03~1 | [Trusty autodetect migration](#trusty-autodetect-migration-spec-integrations-031) | `migrate_trusty_autodetect.run_migration` |
| SPEC-INTEGRATIONS-04~1 | [MCP config builder](#mcp-config-builder-spec-integrations-041) | `MCPServiceConfigBuilder.generate_service_config` |
| SPEC-INTEGRATIONS-05~1 | [MCP service installer](#mcp-service-installer-spec-integrations-051) | `MCPServiceInstaller.install_missing_services` |
| SPEC-INTEGRATIONS-06~1 | [Memory enrichment — multi-backend dispatcher](#memory-enrichment--multi-backend-dispatcher-spec-integrations-061) | `memory_capture.handle_user_prompt_submit` |
| SPEC-INTEGRATIONS-07~1 | [Memory capture — session lifecycle events](#memory-capture--session-lifecycle-events-spec-integrations-071) | `memory_capture.main` |
| SPEC-INTEGRATIONS-08~1 | [Memory enrichment — delegation layer](#memory-enrichment--delegation-layer-spec-integrations-081) | `MemoryPreDelegationHook`, `MemoryPostDelegationHook`, `KuzuEnrichmentHook` |
| SPEC-INTEGRATIONS-09~1 | [Migrations system — registry and runner](#migrations-system--registry-and-runner-spec-integrations-091) | `runner.run_pending_migrations`, `registry.MIGRATIONS` |
| SPEC-INTEGRATIONS-10~1 | [Dashboard / UI service application](#dashboard--ui-service-application-spec-integrations-101) | `ui_service.app.create_app` |
| SPEC-INTEGRATIONS-11~1 | [Dashboard / UI service daemon lifecycle](#dashboard--ui-service-daemon-lifecycle-spec-integrations-111) | `ServeDaemon`, `_ServeDaemonManager` |

---

## Trusty service address discovery {#SPEC-INTEGRATIONS-01~1}

**ID:** SPEC-INTEGRATIONS-01~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

- **Inputs:** None (reads from filesystem at call time).

- **Outputs:** A `host:port` string suitable for building HTTP base URLs.

- **Behavior:**
  - `_trusty_search_base_url()` reads `~/.trusty-search/http_addr` (a single line of
    `host:port` text). If the file is absent or unreadable, returns the static fallback
    `"127.0.0.1:7878"`.
  - `_trusty_memory_base_url()` reads `~/.trusty-memory/http_addr` with the same
    semantics; fallback is `"127.0.0.1:7070"`.
  - The autodetect migration (`migrate_trusty_autodetect`) mirrors this pattern: per-service
    `addr_file` entries in `_SERVICES` point to `~/.trusty-search/http_addr` and
    `~/.trusty-memory/http_addr`; these are read at each startup pass.

- **Preconditions:** None — the functions are unconditionally safe to call.

- **Postconditions:** Always returns a non-empty string; never raises.

- **Error conditions:** Any `OSError` from the file read is silently swallowed; the static
  fallback is returned instead.

### Rationale (WHY)

Trusty daemons bind to OS-assigned ports and write the chosen address to a well-known file
rather than using a fixed port. Hardcoding port 7878 or 7070 caused silent failures when the
OS chose a different port. Reading the `http_addr` file at call time (rather than caching at
startup) means any daemon restart that picks a new port is automatically reflected on the next
call. The fallback preserves backward compatibility with older trusty versions that always used
the default ports.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.cli.commands.setup.handlers.trusty` | `TrustyMixin._trusty_search_base_url`, `_trusty_memory_base_url` |
| `claude_mpm.migrations.migrate_trusty_autodetect` | `_SERVICES` addr-file entries read in `run_migration` |

---

## Trusty MCP service setup {#SPEC-INTEGRATIONS-02~1}

**ID:** SPEC-INTEGRATIONS-02~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

- **Inputs:** Invoked as part of the `claude-mpm setup` interactive wizard. Relevant
  arguments from the CLI namespace include `--force` and `--upgrade`, both forwarded to
  `PackageInstallerService`.

- **Outputs:** Side effects only — no return value.

- **`_setup_trusty_search` behavior:**
  1. Installs the `trusty-search` binary via cargo (delegates to
     `TrustyMixin._install_cargo_binary`).
  2. HTTP health-checks the address from `_trusty_search_base_url()`; if unhealthy, writes
     a macOS LaunchAgent plist at
     `~/Library/LaunchAgents/com.bobmatnyc.trusty-search.plist` with `KeepAlive=true` and
     loads it via `launchctl`.
  3. Polls up to 10 × 0.5 s for the daemon to answer the health endpoint, re-resolving the
     dynamic port on each attempt.
  4. Runs `trusty-search index <project_root>` (120 s timeout; non-fatal on timeout).
  5. Writes a `.mcp.json` entry: `{"type":"stdio","command":"trusty-search","args":["serve"]}`.
  6. Injects a `PostToolUse` hook into `.claude/settings.json` and
     `~/.claude/settings.json` tagged `_mpm_service: "trusty-search"`.

- **`_setup_trusty_memory` behavior:**
  1. Installs the `trusty-memory` binary via cargo.
  2. Checks daemon health via `trusty-memory status` (5 s) then HTTP fallback; if unhealthy,
     writes and loads plist `com.bobmatnyc.trusty-memory` (`KeepAlive=true`).
  3. Creates a palace via `POST /api/v1/palaces` with `name = Path.cwd().name`, checking
     `GET /api/v1/palaces` first to avoid duplicates.
  4. Writes a `.mcp.json` entry:
     `{"type":"stdio","command":"trusty-memory-mcp-bridge","args":[]}`.
  5. Injects `SessionStart`, `Stop`, and `SubagentStop` hooks tagged
     `_mpm_service: "trusty-memory"`.

- **`_setup_trusty_analyze` behavior:**
  1. Installs the `trusty-analyzer` binary via cargo.
  2. Health-checks `127.0.0.1:7879/health` (hardcoded — no dynamic discovery for this
     service).
  3. If unhealthy, writes and loads plist `com.bobmatnyc.trusty-analyzer`.
  4. Writes `.mcp.json` entry: `{"type":"stdio","command":"trusty-analyzer","args":["mcp"]}`.
  5. No hook injection for trusty-analyzer.

- **Hook idempotency:** Before injecting hooks, `_inject_hooks_to_settings` removes any
  existing hooks tagged with `_LEGACY_SERVICES = {"kuzu-memory", "mcp-vector-search"}`, then
  deduplicates by `_mpm_service`. Re-running setup is safe.

- **JSON write safety:** All `.mcp.json` and `settings.json` writes use `_atomic_write_json`
  (write to temp file in same directory, then `os.replace`) to prevent partial-write
  corruption.

- **Preconditions:** macOS (launchd plist writes are macOS-specific); cargo on PATH for
  binary installation.

- **Error conditions:** Individual phases (cargo install, launchctl load, health poll) are
  wrapped in their own exception handlers; failures log and continue to the next phase.

### Rationale (WHY)

The setup flow is intentionally split across three methods (one per trusty service) because
each service has distinct installation requirements, health-check mechanisms, and MCP entry
shapes. Merging them into a single function would make each variant's error-handling harder
to read and test independently.

LaunchAgent persistence (`KeepAlive=true`) ensures daemons survive reboots and crash-restart
automatically — required because Claude Code hooks calling `trusty-memory` HTTP endpoints
assume the daemon is always running. Without persistence, a reboot or crash would silently
disable memory capture until the user manually restarted the daemon.

The health-poll loop (step 3 of `_setup_trusty_search`) is needed because launchd loads a
plist asynchronously; the daemon may not be ready to accept connections immediately after
`launchctl load`. Re-resolving the dynamic port on each poll iteration handles the edge case
where the daemon writes its address file after startup completes on a newly assigned port.

The `trusty-memory-mcp-bridge` command (not `trusty-memory mcp`) is the correct stdio MCP
entry; earlier documentation and hook entries that used the `mcp` subcommand form were
incorrect and were repaired by migration `fix_trusty_memory_bridge` (v6.5.0).

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.cli.commands.setup.handlers.trusty` | `TrustyMixin._setup_trusty_search`, `_setup_trusty_memory`, `_setup_trusty_analyze`, `_inject_hooks_to_settings`, `_inject_trusty_hooks`, `_atomic_write_json`, `_write_launchd_plist`, `_ensure_launchd_loaded` |

---

## Trusty autodetect migration {#SPEC-INTEGRATIONS-03~1}

**ID:** SPEC-INTEGRATIONS-03~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

- **Inputs:** `project_dir: Path` — the project root directory.

- **Outputs:** `bool` — `True` if at least one `.mcp.json` entry was written; `False`
  if all services were absent or their entries already existed.

- **Run mode:** Registered with `run_always=True` in the migration registry; executes on
  every startup pass.

- **Per-service behavior (for `trusty-search` and `trusty-memory`):**
  1. Checks `shutil.which(binary_name)` to determine whether the binary is installed.
  2. If binary present, HTTP health-probes the address from the service's `addr_file`
     (`~/.trusty-{svc}/http_addr`, with static fallback if absent) at `/health`.
  3. If healthy and the `mcpServers` key for this service is absent from `.mcp.json`,
     writes the entry using `_mcp_config_transaction` (atomic JSON update).
  4. If unhealthy or binary absent, skips without error.

- **Postconditions:** After a successful pass, `.mcp.json` contains entries for all
  locally running trusty services whose binaries are on PATH. Existing entries are
  never overwritten.

- **Error conditions:** Individual service probe failures are caught and logged; the
  migration continues with the remaining services and returns `False` for that service.

### Rationale (WHY)

This migration addresses the gap between initial `claude-mpm setup` (which configures trusty
services interactively) and the common case where a user installs trusty-search or
trusty-memory independently after the first setup run. Without autodetect, the user would
need to re-run `claude-mpm setup` to get the `.mcp.json` entries populated.

`run_always=True` is required because daemon state changes between sessions (the user may
install trusty-memory, start it, or upgrade it between two Claude Code sessions). A one-shot
migration that ran only once at install time would miss these post-install state changes.

The "write only if absent" behavior prevents the migration from clobbering entries that the
setup wizard wrote with richer configuration.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.migrations.migrate_trusty_autodetect` | `run_migration` (full implementation) |

---

## MCP config builder {#SPEC-INTEGRATIONS-04~1}

**ID:** SPEC-INTEGRATIONS-04~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

- **Inputs:**
  - `service_name: str` — one of the known service identifiers.
  - `project_path: Path` — project root, used for `{project_root}` substitution in
    `mcp-vector-search` args.

- **Outputs:** A `dict` with at minimum `"command"` and `"args"` keys, suitable for
  direct insertion into `.mcp.json`'s `mcpServers` object. Returns `None` if all
  resolution strategies fail.

- **`STATIC_MCP_CONFIGS` entries (verified at time of research):**

  | Service key | `command` value | `args` value |
  |-------------|-----------------|--------------|
  | `kuzu-memory` | resolved binary path | `["mcp", "serve"]` |
  | `mcp-ticketer` | resolved binary path | `["mcp"]` |
  | `mcp-browser` | resolved binary path | `["mcp"]` |
  | `mcp-vector-search` | resolved python binary | `["-m", "mcp_vector_search.mcp.server", "{project_root}"]` |
  | `trusty-search` | `"trusty-search"` | `["serve"]` |
  | `trusty-memory` | `"trusty-memory-mcp-bridge"` | `[]` |
  | `trusty-analyzer` | `"trusty-analyzer"` | `["mcp"]` |

- **`generate_service_config(service_name)` priority chain:**
  1. Attempt `get_static_service_config` (binary path resolution + static template).
  2. Validate with `test_service_command` (runs `--help`, expects exit 0 or 1 with no
     import error text).
  3. If static+validate fails: try `pipx run <service> --version` (5 s); use `pipx run`
     form if exit 0.
  4. If pipx fails: try `uvx <service> --version` (5 s); use `uvx` form if exit 0.
  5. If all fail: `locator.detect_service_path(service_name)`.

- **Binary path resolution** for pipx-installed services (`kuzu-memory`, `mcp-ticketer`,
  `mcp-browser`): checks `~/.local/pipx/venvs/<name>/bin/<name>` first, then
  `shutil.which`, then known paths; falls back to `pipx run` form.

- **`get_fallback_config`:** Currently handles only `mcp-vector-search` (returns `pipx run`
  form).

- **Preconditions:** None — the builder does not require any service to be running.

- **Error conditions:** `test_service_command` catches all subprocess exceptions and returns
  `False`; the priority chain falls through to the next strategy.

### Rationale (WHY)

Extracted from a `MCPConfigManager` god-class (issue #507) to reduce coupling between config
generation, installation, and JSON file management. Separating config generation makes each
concern independently testable and prevents the god-class from accumulating more unrelated
responsibilities.

Static configs are preferred because dynamic binary detection is fragile: PATH contents vary
across shells, virtual environments, and OS versions. Testing a static config with
`test_service_command` immediately catches the most common failure (binary not on PATH)
before writing a broken config to `.mcp.json`. The fallback chain (pipx → uvx → detect)
exists because some users install tools through package managers other than the one the
static config assumed.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.services.mcp.config_builder` | `MCPServiceConfigBuilder` (class, all methods) |

---

## MCP service installer {#SPEC-INTEGRATIONS-05~1}

**ID:** SPEC-INTEGRATIONS-05~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

- **Inputs:** None (reads service classification constants at construction time).

- **Outputs:**
  - `install_missing_services()` returns `(True, summary_str)` on full success or
    `(False, failed_list)` if any service failed all fallback installation methods.

- **Service classification:**

  ```
  PIPX_SERVICES  = {"mcp-vector-search", "mcp-browser", "mcp-ticketer", "kuzu-memory"}
  CARGO_SERVICES = {"trusty-search", "trusty-memory", "trusty-analyzer"}
  ```

  `install_missing_services()` auto-installs only `PIPX_SERVICES`. Trusty services
  (`CARGO_SERVICES`) require `TrustyMixin._install_cargo_binary` from the setup handler
  and are not installed by this class.

- **`_install_service_with_fallback(service_name)` installation chain:**
  1. `pipx install <service>` (120 s timeout); on success, calls
     `inject_missing_dependencies` then `_verify_service_installed`.
  2. `uvx install <service>` fallback.
  3. `pip install --user <service>` fallback.

- **`inject_missing_dependencies(service_name)`:** Runs `pipx inject <service> <dep>` for
  each entry in `SERVICE_MISSING_DEPENDENCIES`. Currently: `mcp-ticketer` → `gql`.

- **`_verify_service_installed(service_name, method)`:** Waits 1 s (pipx symlink delay),
  checks `locator.detect_service_path`, then runs `--version`/`--help`.

- **Preconditions:** `pipx` or `uvx` or `pip` available on PATH.

- **Postconditions:** Each successfully installed service is detectable via
  `locator.detect_service_path` after `_verify_service_installed` completes.

- **Error conditions:** All subprocess exceptions are caught per-service; other services
  continue installing regardless of a sibling's failure.

### Rationale (WHY)

Extracted from the same `MCPConfigManager` god-class (issue #507). The isolation allows
installation logic to be unit-tested independently from config generation and file management.

The three-fallback installation chain (pipx → uvx → pip) exists because the user population
uses different Python environment managers. Pipx is the preferred target because it installs
tools in isolated virtual environments, preventing dependency conflicts. Uvx and pip are
progressively less isolated but allow the tool to succeed on systems without pipx.

The 1-second sleep in `_verify_service_installed` is a documented pragmatic workaround for
pipx needing time to create symlinks in `~/.local/bin/` after writing the venv.

`CARGO_SERVICES` is defined but intentionally not auto-installed because cargo-compiled
binaries require a Rust toolchain and architecture-specific compilation, which cannot be
assumed present. Those services are handled by the interactive `TrustyMixin` setup flow.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.services.mcp.service_installer` | `MCPServiceInstaller` (class, all methods) |

---

## Memory enrichment — multi-backend dispatcher {#SPEC-INTEGRATIONS-06~1}

**ID:** SPEC-INTEGRATIONS-06~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

- **Inputs:** `event: dict` — a parsed Claude Code hook event with `hook_event_name ==
  "UserPromptSubmit"`.

- **Outputs:** A response dict with `hookSpecificOutput.additionalContext` populated with
  recalled memory content (or empty string if no backend is available / recall returns
  nothing). The response dict conforms to the Claude Code hook response schema.

- **Backend selection (`_select_backend()`):**
  - Instantiates `TrustyMemoryBackend` and checks `is_available()`.
  - If available, uses trusty-memory as the primary backend.
  - Otherwise instantiates `KuzuMemoryBackend` and checks `is_available()`.
  - If available, uses kuzu-memory as the fallback backend.
  - If neither is available, returns `None` (no enrichment).
  - Selection is evaluated once at module import time and cached in `_BACKEND`.

- **`TrustyMemoryBackend.recall(query, palace)`:**
  - Primary: `GET /api/v1/palaces/<palace>/recall?q=<query>&limit=5` (800 ms timeout).
  - Fallback: `trusty-memory recall --palace <palace> <query>` CLI (2 s timeout).

- **`KuzuMemoryBackend.recall(query)`:**
  - `kuzu-memory recall <query>` (2 s timeout).

- **`handle_user_prompt_submit(event)` behavior:**
  - Recalls from the cached backend synchronously (capped at 800 ms to avoid slowing the
    user's prompt).
  - Fires a background store (daemon thread) for any new content that should be persisted
    asynchronously.
  - Injects recall results as `additionalContext` in the hook response.

- **Preconditions:** Module must be invoked from the Claude Code hook dispatcher with a
  valid JSON event on stdin.

- **Postconditions:** The response is always well-formed even when the backend is
  unavailable or the recall times out (empty `additionalContext` rather than an error).

- **Error conditions:** All backend I/O errors are caught; the function returns an empty
  `additionalContext` response rather than propagating.

### Rationale (WHY)

The two-backend design (trusty-memory primary, kuzu-memory fallback) reflects the migration
path of the project: trusty-memory is the intended long-term backend with richer API support
and HTTP-first access, while kuzu-memory provides continuity for users who have accumulated
a kuzu graph and have not yet migrated. Both backends implement the same `AbstractMemoryCaptureBackend`
ABC, making the dispatcher backend-agnostic.

The 800 ms synchronous recall cap and the background-thread store ensure that memory
enrichment never blocks the user's prompt submission perceptibly. Recall latency is
user-visible; store latency is not.

Module-level caching of `_BACKEND` avoids re-detecting available backends on every prompt
event, since binary and daemon availability rarely changes mid-session.

**Note on kuzu-memory status:** Kuzu-memory is NOT deprecated or removed. It is the live
fallback backend in production code. The `remove_memory_capture_hook` migration (v6.4.9)
only removed stale hook registration entries from `settings.json`; it did not remove or
replace the Python module. The description "module moved to trusty-memory" in that migration
is inaccurate — the module was refactored into a multi-backend dispatcher, not moved.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.hooks.memory_capture` | `handle_user_prompt_submit`, `_select_backend`, `TrustyMemoryBackend`, `KuzuMemoryBackend`, `AbstractMemoryCaptureBackend` |

---

## Memory capture — session lifecycle events {#SPEC-INTEGRATIONS-07~1}

**ID:** SPEC-INTEGRATIONS-07~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

- **Inputs:** Claude Code hook event JSON on stdin. The module is invoked by the Claude
  Code hook dispatcher (`claude-hook` / `claude-hook-fast.sh`) for multiple event types.

- **Outputs:** For `UserPromptSubmit`: a JSON response dict written to stdout. For all
  other events: no stdout output (side effects only).

- **`main()` dispatcher routing:**
  - Reads stdin with `select.select(timeout=1.0)` to prevent blocking on empty stdin.
  - Parses the JSON event and extracts `hook_event_name`.
  - Routes:
    - `"UserPromptSubmit"` → `handle_user_prompt_submit(event)` (see SPEC-INTEGRATIONS-06~1).
    - `"SessionStart"` → `_handle_session_start(event)`: stores a session-start fact via the
      active backend.
    - `"Stop"` or `"SubagentStop"` → `_handle_session_end(event)`: stores
      `"Session ended in <project>"` with tags `["session-end", project]` via the active
      backend.
    - `"PostToolUse"` → `_handle_post_tool_use(event)`: captures file paths (from
      Write/Edit/MultiEdit/NotebookEdit tool calls) and git commit messages (from Bash
      tool calls that contain `git commit` output).

- **Backend for SessionStart / Stop / SubagentStop:** Uses the same `_BACKEND` selected by
  `_select_backend()` (trusty-memory primary, kuzu-memory fallback).

- **Preconditions:** Valid JSON on stdin (guarded by `select.select` timeout); `_BACKEND`
  may be `None` in which case storage calls are silently skipped.

- **Postconditions:** For Stop/SubagentStop, at least one store attempt is made if a backend
  is available. The process exits cleanly regardless of backend availability.

- **Error conditions:** All exceptions within each handler are caught; the `main()` function
  always exits without propagating.

### Rationale (WHY)

Concentrating all Claude Code hook event types in a single `main()` dispatcher allows one
registered binary (`claude-hook`) to handle every event that requires memory capture, rather
than registering separate binaries per event type. This reduces the number of `settings.json`
hook entries and the surface area for hook registration drift.

The `select.select(timeout=1.0)` stdin guard (rather than a bare `sys.stdin.read()`) prevents
the hook process from hanging indefinitely when the hook dispatcher provides no stdin, which
can happen when a hook fires without payload data.

Session-start and session-end stores use background threads to avoid delaying Claude Code's
startup or shutdown sequences.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.hooks.memory_capture` | `main`, `_handle_session_start`, `_handle_session_end`, `_handle_post_tool_use` |

---

## Memory enrichment — delegation layer {#SPEC-INTEGRATIONS-08~1}

**ID:** SPEC-INTEGRATIONS-08~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

This section covers three hooks that operate within the MPM Python delegation pipeline,
distinct from the Claude Code hook event system.

**`MemoryPreDelegationHook` (`PreDelegationHook`, priority unspecified):**
- Fires before each agent-to-agent delegation.
- Loads agent-specific memory from `AgentMemoryManager.load_agent_memory(agent_id)`.
- Injects the result as `"agent_memory"` key in the delegation context dict.
- Gracefully disables itself if `AgentMemoryManager` cannot be imported.

**`MemoryPostDelegationHook` (`PostDelegationHook`, priority unspecified):**
- Fires after each agent-to-agent delegation completes.
- Extracts `# Add To Memory:`, `# Memorize:`, and `# Remember:` blocks from the
  result text (with `Type:` and `Content:` subfields).
- Stores each extracted learning via `AgentMemoryManager.add_learning(agent_id, type, content)`.
- Memory entry content is capped at 5–100 characters.
- Gracefully disables itself if `AgentMemoryManager` cannot be imported.

**`KuzuEnrichmentHook` (`PreDelegationHook`, priority 10):**
- Fires before each agent-to-agent delegation.
- Enabled only if `kuzu-memory` binary is found (pipx venv path or `shutil.which`).
- Calls `KuzuMemoryHook._retrieve_memories(query)` (5 s timeout) to recall relevant
  knowledge from the kuzu graph.
- Injects results as a `=== RELEVANT KNOWLEDGE FROM KUZU MEMORY ===` section in the
  delegation context.

- **Distinction from Claude Code hooks:** These hooks are NOT Claude Code hook events. They
  are fired by the MPM orchestration layer's `HookContext` mechanism during Python-level
  agent delegation, not by Claude Code's `settings.json` `PreToolUse`/`PostToolUse` events.

- **Preconditions:** `AgentMemoryManager` importable; delegation pipeline initialised.

- **Error conditions:** All three hooks catch import failures and runtime exceptions
  gracefully; delegation continues even if memory enrichment fails.

### Rationale (WHY)

Agent-level memory (file-based markdown at `.claude-mpm/memories/<agent-id>.md`) and graph
memory (kuzu-memory) serve different enrichment purposes than the session-level memory in
`memory_capture.py`. Agent-level memory accumulates project-specific learnings per agent over
time, giving each specialist agent context about the current project. Graph memory provides
cross-session semantic recall of related concepts.

Separating these hooks into the delegation pipeline (rather than the Claude Code hook system)
allows them to receive the structured delegation context (agent ID, prompt, prior results)
rather than the raw Claude Code event JSON, enabling more precise memory queries.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.hooks.memory_integration_hook` | `MemoryPreDelegationHook`, `MemoryPostDelegationHook` |
| `claude_mpm.hooks.kuzu_enrichment_hook` | `KuzuEnrichmentHook` |
| `claude_mpm.hooks.kuzu_memory_hook` | `KuzuMemoryHook` (used by `KuzuEnrichmentHook`) |

---

## Migrations system — registry and runner {#SPEC-INTEGRATIONS-09~1}

**ID:** SPEC-INTEGRATIONS-09~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

- **State file:** `~/.claude-mpm/migrations.json` — a JSON dict with keys `"completed"`
  (list of migration IDs that returned `True`) and `"last_version"`. Global (not
  per-project).

- **`Migration` NamedTuple fields:** `id: str`, `version: str`, `description: str`,
  `run: Callable[[], bool]`, `run_always: bool = False`.

- **`get_pending_migrations()` → `list[Migration]`:**
  Returns all migrations where `run_always=True` OR `id not in completed`.

- **`run_pending_migrations(current_version)` → `int`:**
  - Iterates pending migrations in `MIGRATIONS` registry order.
  - For each migration:
    - `run_always=True` migrations: always execute; never written to `completed`
      (they run every startup); output suppressed for no-op runs.
    - One-shot migrations: execute; if `run()` returns `True`, call
      `mark_migration_complete(id)` to add to `completed`. If `run()` returns `False`,
      the ID is NOT added to `completed` (migration will run again on next startup).
  - Exceptions are caught, logged, and printed; remaining migrations continue.
  - Returns count of migrations that returned `True`.

- **Registry catalog (23 entries at time of research, spanning v5.6.91 to v6.5.0):**
  Two migrations have `run_always=True`: `trusty_autodetect` (v6.3.10) and
  `check_migration_skills` (v6.4.1). All others are one-shot.

- **Scan-and-repair migrations:** `fix_mcp_command_args` (v6.4.2) and
  `fix_trusty_memory_bridge` (v6.5.0) are repair-if-needed migrations that return `False`
  when nothing is broken (idempotent probes). Because `False` does not trigger
  `mark_migration_complete`, these IDs remain absent from `completed` on clean installs,
  causing `get_migration_status()` to permanently count them as pending even though they
  represent no real work.

- **Preconditions:** `~/.claude-mpm/` directory must be writable. Called at startup via
  `run_pending_migrations()` (invoked from `run_session_legacy`).

- **Error conditions:** Per-migration exceptions are isolated; the runner always
  completes the full list.

### Rationale (WHY)

A global state file (rather than per-project) matches the scope of what migrations actually
do: modify user-level infrastructure (hook entries in `~/.claude/settings.json`, global agent
deployments, global skill locations). Project-scoped migrations would require every project
to re-run the same infrastructure changes independently.

`run_always=True` for `trusty_autodetect` is necessary because daemon availability changes
between sessions (user may install trusty-memory between two Claude Code sessions). A one-shot
migration would miss these post-install state changes.

The one-shot "return `True` to complete" model decouples migration idempotency from completion
semantics: a repair migration that finds nothing to fix returns `False` (stays pending) rather
than `True` (marks complete and never runs again), ensuring the repair probe runs on subsequent
startups in case the problem reappears. This is intentional for repair migrations, though it
creates a misleading "pending" count for genuinely clean systems.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.migrations.runner` | `run_pending_migrations`, `get_pending_migrations`, `get_migration_status`, `mark_migration_complete` |
| `claude_mpm.migrations.registry` | `MIGRATIONS` (catalog), `Migration` (NamedTuple) |
| `claude_mpm.migrations.v6_3_1_deploy_claude_assets` | `run_migration` — deploys statusline.sh and settings.json to `~/.claude/` (one-shot, create-if-missing, idempotent) |

---

## Dashboard / UI service application {#SPEC-INTEGRATIONS-10~1}

**ID:** SPEC-INTEGRATIONS-10~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

- **Inputs:** `service_config: UIServiceConfig | None` — configuration dataclass; if `None`,
  constructed via `UIServiceConfig.from_env()`.

- **Outputs:** A fully configured `FastAPI` application instance, ready for ASGI serving.

- **`UIServiceConfig` fields and defaults:**

  | Field | Default | Env var |
  |-------|---------|---------|
  | `host` | `127.0.0.1` | `CLAUDE_MPM_UI_HOST` |
  | `port` | `7777` | `CLAUDE_MPM_UI_PORT` |
  | `max_sessions` | `10` | `CLAUDE_MPM_UI_MAX_SESSIONS` |
  | `session_timeout_minutes` | `60` | `CLAUDE_MPM_UI_SESSION_TIMEOUT` |
  | `cors_origins` | localhost/127.0.0.1 | `CLAUDE_MPM_UI_CORS_ORIGINS` |
  | `global_sessions_dir` | `~/.claude-mpm/sessions` | `CLAUDE_MPM_UI_SESSIONS_DIR` |

- **`create_app(service_config)` behavior:**
  1. Instantiates `FastAPI` with `docs_url="/api/v1/docs"`,
     `redoc_url="/api/v1/redoc"`, `openapi_url="/api/v1/openapi.json"`.
  2. Stores `UIServiceConfig` and `ProcessManager` on `app.state`.
  3. Configures `CORSMiddleware` with configured `allow_origins`, plus regex
     `http://(localhost|127\.0\.0\.1)(:\d+)?`, and `allow_credentials=True`.
  4. Registers 12 routers under `/api/v1` prefix: `sessions`, `messages`, `auth`,
     `models`, `config`, `permissions`, `hooks`, `mcp`, `commands`, `memory`,
     `tools`, `diagnostics`.
  5. Defines `GET /api/v1/ws/sessions/{session_id}` inline (not via a router) as a
     WebSocket endpoint. Client sends `{"type":"message"|"interrupt"|"command"}` JSON;
     server streams `StreamEvent` objects.
  6. Defines `GET /api/v1/health` returning `{"status":"healthy","active_sessions":N}`.

- **`ProcessManager` key behaviors:**
  - `create_session(config)`: spawns `claude --output-format stream-json` subprocess;
    persists session state to `~/.claude-mpm/sessions/<id>.json`.
  - `send_message(session_id, content)`: `AsyncIterator[StreamEvent]` — writes to
    subprocess stdin, yields parsed NDJSON events.
  - `interrupt(session_id)`: sends `SIGINT` to the subprocess.
  - `_cleanup_loop`: background task evicting timed-out sessions.
  - Sessions persist across daemon restarts via `_persist_session`/`_load_persisted_sessions`.

- **Preconditions:** FastAPI and uvicorn available in the environment.

- **Error conditions:** Router registration failures are not caught at the `create_app`
  level; all routers are expected to import cleanly.

### Rationale (WHY)

FastAPI was chosen for full async support (streaming NDJSON from Claude subprocess),
built-in WebSocket support, and automatic OpenAPI documentation generation. The REST + SSE +
WebSocket surface allows browser-based UIs and external tooling to control and observe Claude
Code sessions without requiring direct terminal access.

Session persistence (`~/.claude-mpm/sessions/`) allows the UI service daemon to survive
restarts without losing active session context: clients can resume interrupted sessions via
`POST /sessions` with a `resume_id`.

The WebSocket endpoint is defined inline in `app.py` rather than in a router file because
FastAPI's router system does not support WebSocket lifespan management (`@router.websocket`)
as cleanly as the inline form, and the WebSocket requires direct access to `app.state`.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.services.ui_service.app` | `create_app`, WebSocket endpoint |
| `claude_mpm.services.ui_service.config` | `UIServiceConfig` |
| `claude_mpm.services.ui_service.process_manager` | `ProcessManager` |
| `claude_mpm.services.ui_service.routers.*` | 12 router modules (sessions, messages, auth, models, config, permissions, hooks, mcp, commands, memory, tools, diagnostics) |

---

## Dashboard / UI service daemon lifecycle {#SPEC-INTEGRATIONS-11~1}

**ID:** SPEC-INTEGRATIONS-11~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

- **Public API:** `ServeDaemon(host, port)` — exposes `start(force_restart)`, `stop()`,
  `restart()`, `status()`.

- **`start(force_restart)` behavior:**
  1. If `CLAUDE_MPM_SERVE_DAEMON=1` in the environment, raises `RuntimeError` (recursion
     prevention guard).
  2. Delegates to `_ServeDaemonManager.start_daemon_subprocess()`, which launches:
     ```
     python -m claude_mpm.cli serve start --background --port N --host H [--channels ...] [--project-root ...]
     ```
     with `CLAUDE_MPM_SERVE_DAEMON=1` set in the child environment.
  3. Writes a PID file at `~/.claude-mpm/serve-<port>.pid`.
  4. Logs daemon output to `~/.claude-mpm/logs/serve-<port>.log`.
  5. Polls up to 30 s (configurable via `CLAUDE_MPM_SERVE_TIMEOUT`) for the PID file to
     appear and the port to be bound.
  6. Returns `True` if startup succeeds within the timeout; `False` otherwise.

- **`stop()` behavior:** Reads the PID file, sends `SIGTERM` to the daemon process, waits
  for process exit, removes the PID file.

- **`status()` behavior:** Returns a dict with `running: bool`, `pid: int | None`,
  `port: int`, `url: str`.

- **Bare `/health` endpoint:** `_patch_health_endpoint(app)` adds `/health` (not under
  `/api/v1`) returning `{"service":"claude-mpm-serve","status":"healthy"}` for
  `DaemonManager.is_our_service()` compatibility checking.

- **ChannelHub integration (optional):** When `--channels` is specified, `uvicorn.serve()`
  and `hub.start()` run concurrently via `asyncio.gather`. `ChannelHub` is imported with
  `type: ignore[import-not-found]`, indicating it is an optional or not-yet-published module.

- **Preconditions:** Port must be free. `~/.claude-mpm/` must be writable.

- **Error conditions:** Port-already-bound errors are surfaced in the `status()` result.
  Startup timeout causes `start()` to return `False` without raising.

### Rationale (WHY)

The daemon pattern (PID file + subprocess with recursion prevention via env var) mirrors
the monitor daemon, providing `start`/`stop`/`status` CLI parity with `claude-mpm monitor`.
This consistency means users and scripts can manage both daemons with identical idioms.

The `CLAUDE_MPM_SERVE_DAEMON=1` env var guard prevents the daemon subprocess from attempting
to re-daemonize itself when the CLI routes through `serve start`. Without it, the startup
code would detect the `--background` flag and attempt to fork again indefinitely.

The 30-second startup poll (rather than a fixed sleep) allows the daemon to start faster on
responsive systems while tolerating slow systems without a hard failure. The polling checks
both PID file presence and port binding because the PID file may appear before the port is
actually bound (uvicorn binds the port slightly after writing the PID).

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.services.ui_service.serve_daemon` | `ServeDaemon`, `_ServeDaemonManager`, `_patch_health_endpoint` |

---

## Known drift {#known-drift}

The following discrepancies between the research findings and other documentation or issue
references are recorded here for traceability.

### Kuzu-memory is the live fallback backend (not deprecated or removed)

**Finding:** Issue #523 uses language that implies kuzu-memory was superseded by
trusty-memory. The actual code state (verified at time of research) is:

- `kuzu-memory` remains in `PIPX_SERVICES` (auto-installed by `MCPServiceInstaller`).
- `kuzu-memory` remains in `STATIC_MCP_CONFIGS` (config_builder).
- `KuzuMemoryBackend` in `memory_capture.py` is the active fallback when trusty-memory is
  unreachable (`_select_backend()` tries trusty-memory first, then kuzu-memory).
- `kuzu_enrichment_hook.py`, `kuzu_memory_hook.py`, and `kuzu_response_hook.py` are all
  live code used in the delegation pipeline.

Kuzu-memory is not deprecated. It is a live fallback tier in production code.

### `remove_memory_capture_hook` migration description is inaccurate

**Finding:** Migration `remove_memory_capture_hook` (v6.4.9) describes itself as "module
moved to trusty-memory, issue #555." The `memory_capture.py` module exists at 831 lines and
is the active handler for `UserPromptSubmit`, `SessionStart`, `Stop`, and `SubagentStop`.
What the migration removes is stale `_mpm_service: "memory-capture"` hook entries from
`settings.json`; it does not remove or move the Python module. The module was refactored into
a multi-backend dispatcher, not moved.

### Issue #523 mislabels memory hooks

**Finding:** Issue #523 lists `memory_integration_hook.py` and `kuzu_enrichment_hook.py`
under "Memory enrichment (UserPromptSubmit)." Neither file handles `UserPromptSubmit`.
Both are Python-level delegation hooks (`PreDelegationHook`, `PostDelegationHook`,
`SubmitHook`) that fire in the MPM Python orchestration pipeline around agent-to-agent
delegation, not around Claude Code's `UserPromptSubmit` event. The actual `UserPromptSubmit`
handler is `memory_capture.py`.

### Trusty-memory MCP command: docs vs code

**Finding:** `docs/developer/memory-integration.md` shows
`{"command": "trusty-memory", "args": ["mcp"]}` as the MCP entry for trusty-memory. Every
code path that writes this entry uses `{"command": "trusty-memory-mcp-bridge", "args": []}`:
`trusty.py` (setup handler), `migrate_trusty_autodetect.py`, and `config_builder.py`
`STATIC_MCP_CONFIGS`. The docs describe the broken earlier form that migration
`fix_trusty_memory_bridge` (v6.5.0) was written to repair.

### Scan-and-repair migrations inflate the pending count

**Finding:** `fix_mcp_command_args` (v6.4.2) and `fix_trusty_memory_bridge` (v6.5.0) are
repair-if-needed migrations. They return `False` when no broken entries are found, so
`mark_migration_complete` is never called and they never appear in `completed`. On a clean
system, `get_migration_status()` permanently reports them as pending even though they have
no real work to do. This is a semantic misuse of the one-shot migration model; they would
more accurately be registered as `run_always=True` (like `trusty_autodetect`) or given a
separate completion sentinel for "first clean-scan" completion.

### Trusty-analyzer uses hardcoded port

**Finding:** `_setup_trusty_analyze` health-checks `127.0.0.1:7879/health` (hardcoded),
while `_setup_trusty_search` and `_setup_trusty_memory` both read dynamic addresses from
`~/.trusty-{svc}/http_addr`. This is an inconsistency within the codebase: if
trusty-analyzer adopts dynamic port assignment in a future version, the setup handler will
silently fail to detect it.
