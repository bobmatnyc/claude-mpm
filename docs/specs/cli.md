# CLI Subsystem — Spec-Linked Documentation

**Status:** Active
**Version:** v1
**Subsystem:** CLI

This document covers the six highest-complexity units in the `claude_mpm` CLI subsystem.
Each section constitutes one governed specification with a stable ID, a behavior
contract (WHAT), a rationale section (WHY), and an implementing-modules table.

The IDs below use the `{#SPEC-CLI-NN~1}` anchor form that the traceability checker
recognizes as a declaration. Engineer agents will add matching `References: SPEC-CLI-NN~1`
entries to the docstrings of the implementing functions once this spec is reviewed.

---

## Table of Contents

| ID | Section | Implementing function |
|----|---------|----------------------|
| SPEC-CLI-01~1 | [Unified agent deployment](#unified-agent-deployment-spec-cli-011) | `AgentDeploymentHandler.deploy_agents_unified` |
| SPEC-CLI-02~1 | [Legacy session run orchestration](#legacy-session-run-orchestration-spec-cli-021) | `run_session_legacy` |
| SPEC-CLI-03~1 | [Command execution dispatch](#command-execution-dispatch-spec-cli-031) | `execute_command` |
| SPEC-CLI-04~1 | [Argument parser construction](#argument-parser-construction-spec-cli-041) | `create_parser` |
| SPEC-CLI-05~1 | [Remote skills sync on startup](#remote-skills-sync-on-startup-spec-cli-051) | `sync_remote_skills_on_startup` |
| SPEC-CLI-06~1 | [Remote agents sync on startup](#remote-agents-sync-on-startup-spec-cli-061) | `sync_remote_agents_on_startup` |

---

## Unified agent deployment {#SPEC-CLI-01~1}

**ID:** SPEC-CLI-01~1
**Status:** Active

### Behavior Contract (WHAT)

- **Inputs:** A list of `AgentConfig` objects representing all agents available for
  installation. Each `AgentConfig` carries at minimum a `name`, `description`, and
  optional `agent_id`, `source_type`, `source_dict`, `is_deployed`, and `display_name`
  attributes.

- **Outputs:** No return value. Side effects are: zero or more agent files written to
  the active scope's agents directory (install path), zero or more agent files deleted
  from that directory (removal path), and zero or more deployment-state JSON files
  updated to reflect the removals.

- **Preconditions:** An interactive TTY must be available. `self.cmd` must be a
  fully-initialised `ConfigureCommand` with a `_ctx`, `unified_config`, and
  `recommendation_service` attached.

- **Postconditions:** The filesystem state of the active agents directory reflects the
  selections the user confirmed. Required agents (those listed in
  `unified_config.agents.required`) are always present in the final selection regardless
  of user input. If the user cancels at any confirmation prompt the filesystem is
  unchanged.

- **Key decision branches:**
  1. If `agents` list is empty (or reduces to empty after filtering `BASE_AGENT`
     entries), print a warning and return immediately.
  2. Agents are grouped by collection (derived from `source_type` and remote repo URL).
     Within each collection they are further grouped by hierarchical path category.
  3. The main body is an unbounded loop. On each iteration a fresh `questionary.checkbox`
     widget is presented with the current `current_selection` state reflected as pre-
     checked items.
  4. If the user selects any choice whose value matches the sentinels
     `__SELECT_ALL_<id>__`, `__DESELECT_ALL_<id>__`, `__SELECT_REC_<id>__`, or
     `__DESELECT_REC_<id>__`, `current_selection` is updated accordingly and the loop
     continues (re-presents the widget). No deployment occurs on control iterations.
  5. If the user presses Enter with no sentinel values selected, the loop breaks and the
     final selection is taken from the checkbox return value (not from
     `current_selection`).
  6. If `questionary.checkbox` raises any exception (e.g., non-TTY stdin), the function
     prints a diagnostic message and returns without making changes.
  7. If `selected_values is None` (user pressed Ctrl-C inside questionary), the function
     returns without making changes.
  8. Required agents in `to_remove` are silently dropped and a warning is printed; they
     are never removed.
  9. Deployment of each install candidate delegates to
     `self.cmd._deploy_single_agent(agent, show_feedback=False)`.
  10. Removal of each candidate: agent `.md` files are resolved through
      `self.cmd._agent_file_paths(leaf_name)` and deleted if present; deployment-state
      JSON files are updated by key deletion for the agent's normalized and raw name.

- **Error conditions:**
  - `questionary.checkbox` exception: caught, user shown error and function returns.
  - Individual install/remove failures: caught per-agent; counters are incremented for
    the summary message but do not abort remaining operations.
  - `get_deployed_agent_ids()` or `recommendation_service.get_recommended_agents()`
    exceptions: caught with `logger.warning`; missing IDs default to empty set (sync
    skips recommended marking, not fatal).

### Rationale (WHY)

The unified approach replaces what were previously separate "install" and "remove"
flows with a single checkbox list that shows the complete agent roster and its current
deployment state simultaneously. This eliminates the need for the user to navigate
multiple menu screens and makes the install/remove relationship visually explicit (a
checked item is installed; unchecking it removes it).

The re-display loop exists because `questionary.checkbox` does not natively support
hierarchical bulk-selection controls. Sentinel values are injected as normal checkbox
choices; when the user selects one, the loop intercepts the sentinel, updates
`current_selection`, and re-presents the widget with the new state pre-applied. This
is a UI workaround for a questionary limitation, not a design preference.

The `BASE_AGENT` filter prevents the internal base template from appearing in the
user-facing list. The "required agents are always selected" guarantee prevents users
from breaking core MPM functionality by accidentally unchecking critical agents. Both
invariants are enforced redundantly: once when building the checkbox list (items are
pre-checked and marked `disabled="required"`) and again after the loop breaks (required
IDs are force-added to `final_selection` and `to_remove` is filtered).

Rationale for the `agent_id` vs. display name distinction: earlier code tracked
selection by display name, which caused collisions between agents whose leaf names
differed only in casing or separator characters. Using `agent_id` (the technical ID)
as the selection key and value throughout is the fix for that class of bug.

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/cli/commands/configure_agent_deployment.py` | `AgentDeploymentHandler.deploy_agents_unified` | Full implementation |

---

## Legacy session run orchestration {#SPEC-CLI-02~1}

**ID:** SPEC-CLI-02~1
**Status:** Active

### Behavior Contract (WHAT)

- **Inputs:** `args` — an `argparse.Namespace` (or compatible object) produced by the
  run subparser. Relevant attributes include (but are not limited to): `headless`,
  `sdk`, `prompt`, `logging`, `no_dangerously_skip_permissions`, `update_statusline`,
  `slack`, `mpm_resume`, `resume`, `no_tickets`, `claude_args`, `launch_method`,
  `monitor`, `websocket_port`, `non_interactive`, `input`, `intercept_commands`,
  `chrome`, `no_chrome`, `no_native_agents`, `check_dependencies`,
  `force_check_dependencies`, `no_prompt`, `force_prompt`, `reload_agents`.

- **Outputs:** None (returns implicitly). All meaningful output is a side effect:
  process replacement (interactive mode via `exec`), subprocess launch, or oneshot
  response printed to stdout.

- **Early-exit paths (before any heavy startup work):**
  1. If `args.no_dangerously_skip_permissions` is true, sets
     `CLAUDE_MPM_NO_SKIP_PERMISSIONS=1` in the environment.
  2. If `args.headless` is true, calls `_run_headless_session(args)` and exits the
     process with that function's return code via `sys.exit`.
  3. If `args.sdk` is true and `args.prompt` is a non-empty string, sets
     `CLAUDE_MPM_RUNTIME=sdk`, calls `run_sdk_oneshot(args.prompt, args)`, and returns.

- **Main startup sequence (when none of the early-exit paths apply):**
  1. If logging is enabled, initialises startup log file via `setup_startup_logging`.
  2. Runs pending version-based database migrations via `run_pending_migrations`.
  3. Runs statusline autoconfig (`run_migration` from `migrate_statusline_autoconfig`),
     which is idempotent; `--update-statusline` forces a refresh.
  4. If `args.slack` is true, starts the Slack bot via `_start_slack_bot` and returns.
  5. Cleans up old startup log files.
  6. Performs startup configuration health check and `.claude.json` memory check.
  7. If `args.reload_agents` is true, deletes deployed system agents via
     `_handle_reload_agents`.
  8. Attempts to start vector search indexing (non-blocking, failure is ignored).
  9. Handles session resumption (`args.mpm_resume`): if value is `"last"`, resolves to
     the most recent interactive session ID; otherwise uses the provided session ID
     directly. Missing sessions are logged and the function returns early.
  10. Deploys MPM slash commands on startup.
  11. Performs smart dependency checking if `args.check_dependencies` is true:
      determines whether a check is needed (TTL and deployment-hash comparison), whether
      the environment allows interactive prompting, and optionally installs missing
      Python dependencies. Failures are caught and do not abort startup.
  12. Assembles `claude_args`: starts from `args.claude_args`, prepends `--resume`
      (and optionally `--fork-session`) if `args.resume` is set, prepends `--chrome` or
      `--no-chrome` if those flags are set, then runs the list through
      `filter_claude_mpm_args` to strip MPM-specific flags before passing them to the
      Claude CLI process.
  13. Optionally starts Socket.IO / WebSocket monitoring server via
      `UnifiedDashboardManager` if `args.monitor` is true.
  14. Constructs a `ClaudeRunner` with the assembled arguments.
  15. Creates session context: if resuming, builds an enhanced context string that
      includes previous session metadata and updates session usage counters; otherwise
      creates a new session record via `SessionManager` and uses a simple context.
  16. Dispatches to one of three execution modes:
      - SDK oneshot (`launch_method == "sdk"` and `args.prompt` non-empty): calls
        `run_sdk_oneshot`.
      - Non-interactive (`args.non_interactive` or `args.input`): calls
        `runner.run_oneshot`.
      - Interactive with command interception (`args.intercept_commands`): launches
        `interactive_wrapper.py` as a subprocess.
      - Plain interactive (default): calls `runner.run_interactive`.

- **Error conditions:** All top-level exceptions in each phase are caught and either
  logged (non-fatal) or result in an early return. The function does not propagate
  exceptions to its caller.

### Rationale (WHY)

This function is explicitly labeled "legacy" because it was frozen during a migration to
the `RunCommand`/`BaseCommand` class pattern. It is preserved verbatim so that
`RunCommand._execute_run_session()` can delegate to it without re-implementing the full
startup sequence during the transition. The docstring comment "Will be gradually
refactored" confirms this is a transitional state.

The complexity (CC 79) arises from the accumulation of many independent startup concerns
handled sequentially in a single function: mode-dispatch early exits, migration runner,
statusline autoconfig, Slack bot, log cleanup, health checks, agent reload, vector
search, session management, dependency checking, argument assembly, monitoring setup,
runner construction, and session dispatch. Each of these phases was added incrementally
as features were introduced, and all of them live here because the caller (`RunCommand`)
was designed to be thin.

The `filter_claude_mpm_args` step is necessary because `argparse.REMAINDER` captures
all trailing arguments indiscriminately; MPM-specific flags that happened to appear
after `--` would otherwise be forwarded to the Claude CLI subprocess, which does not
understand them.

The three early-exit paths (headless, SDK oneshot, and permission flag setup) are placed
at the very top of the function to minimize wasted startup work for those modes. Bug
#486 in the codebase is cited as the reason the SDK prompt early-exit was added: without
it, transient failures in the longer startup sequence (dependency checking, monitoring
setup) would abort the process before the SDK dispatch at the bottom could be reached.

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/cli/commands/run.py` | `run_session_legacy` | Full implementation |
| `src/claude_mpm/cli/commands/run.py` | `RunCommand._execute_run_session` | Thin delegating wrapper |

---

## Command execution dispatch {#SPEC-CLI-03~1}

**ID:** SPEC-CLI-03~1
**Status:** Active

### Behavior Contract (WHAT)

- **Inputs:**
  - `command: str` — the name of the command to execute, already resolved from parsed
    CLI arguments.
  - `args` — the full `argparse.Namespace` from the main parser, passed through
    unchanged to the selected handler.

- **Outputs:** An integer exit code. Returns `0` on success, `1` on unknown command or
  handler error. Returns whatever integer the called handler returns, coerced to `0` if
  the handler returns `None`.

- **Command routing — two tiers:**
  1. **Lazy-import tier (evaluated first, top-to-bottom):** A sequence of explicit
     `if command == "<name>":` branches handles commands that are either experimental,
     heavyweight, or that require special argument pre-processing before calling their
     handler. Commands in this tier include: `run-guarded`, `mpm-init`, `uninstall`,
     `verify`, `skill-source`, `agent-source`, `summarize`, `oauth`, `auth`, `slack`,
     `install`, `setup`, `settings`, `tools`, `provider`, `profile`, `auto-configure`,
     `local-deploy`, `hook-errors`, `update-statusline`, `autotodos`, `channels`,
     `serve`, `ztk-stats`, `ztk`, `llmlingua-stats`. Each branch performs a local
     import of its handler module immediately before calling it.
  2. **Dict-lookup tier (evaluated second):** A static `command_map` dict maps stable
     command names (sourced from `CLICommands` enum values) to pre-imported handler
     callables. Covers: `run`, `tickets`, `info`, `agents`, `agent-manager`, `memory`,
     `monitor`, `dashboard`, `config`, `configure`, `aggregate`, `analyze-code`,
     `cleanup`, `mcp`, `doctor`, `upgrade`, `skills`, `migrate`, `debug`, `gh`,
     `message`, `queue`.

- **Special sub-routing within the lazy tier:**
  - `hook-errors`: dispatches to `_handle_hook_errors(args)`, which itself routes to
    one of five Click-based sub-handlers based on `args.hook_errors_command`.
  - `autotodos`: dispatches to `_handle_autotodos(args)`, which routes to one of six
    Click-based sub-handlers based on `args.autotodos_command`.
  - `settings`: routes to `settings_clean_hooks_command` if
    `args.settings_command == "clean-hooks"`; returns `1` for unknown subcommands.
  - `ztk-stats` and `llmlingua-stats`: pre-process `args.all_time` (if true, set
    `args.days = 0`) before calling the handler.

- **Unknown command path:** If `command` is not found in either tier, prints an error
  to stderr, calls `suggest_similar_commands` to find fuzzy matches from the full
  command list, prints the suggestion if found, and returns `1`.

- **Return value normalisation:** Every handler result is coerced: `result if result is
  not None else 0`. `CommandResult` objects from class-based handlers are unwrapped to
  `result.exit_code`.

- **Error conditions:** Exceptions from handler calls are not caught by this function.
  The caller is responsible for any top-level exception handling.

### Rationale (WHY)

The two-tier structure exists because of a fundamental tension between startup latency
and completeness. Commands in the dict-lookup tier are expected to be used frequently
(e.g., `run`, `agents`, `skills`) and their imports are paid at module load time. Commands
in the lazy-import tier are either experimental (`run-guarded`, `llmlingua-stats`),
infrequently used (`oauth`, `uninstall`), or heavyweight enough that loading them on
every invocation would add measurable latency to all commands, not just those that use
them. Lazy imports isolate that cost to the commands that actually need it.

The function itself exists as a routing layer rather than embedding dispatch logic in
`cli/__init__.py` or in each command's parser. Centralising routing here makes it
easier to add new commands without touching the main entrypoint and allows the set of
known commands to be reconstructed as a list (for the fuzzy-suggestion fallback) without
duplicating string constants across files.

The `CLICommands` enum-driven dict tier is the stable contract surface; the lazy
`if command ==` tier is where experimental or lower-priority commands land until they
are either promoted to the dict or removed. The separation is informal (there is no
enforcement), but the pattern is consistent throughout the file.

The rationale for `result if result is not None else 0` normalisation: historically
some command handlers return `None` to indicate success, some return `0`, and some
return `CommandResult` objects. The coercion prevents the caller from receiving an
unexpected `None` exit code.

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/cli/executor.py` | `execute_command` | Full implementation |
| `src/claude_mpm/cli/executor.py` | `_handle_hook_errors` | Sub-router for `hook-errors` |
| `src/claude_mpm/cli/executor.py` | `_handle_autotodos` | Sub-router for `autotodos` |

---

## Argument parser construction {#SPEC-CLI-04~1}

**ID:** SPEC-CLI-04~1
**Status:** Active

### Behavior Contract (WHAT)

- **Inputs:**
  - `prog_name: str` — program name string passed to `argparse`; defaults to
    `"claude-mpm"`.
  - `version: str` — version string used in `--version` output; defaults to `"0.0.0"`.

- **Outputs:** A fully configured `SuggestingArgumentParser` instance with all
  subparsers registered. The returned parser is ready to call `.parse_args()` on.

- **Construction sequence:**
  1. Calls `create_main_parser(prog_name, version)` to produce a
     `SuggestingArgumentParser` with common arguments (`--version`, logging group,
     config group) already attached.
  2. Calls `add_top_level_run_arguments(parser)` to attach run-mode flags
     (`--no-hooks`, `--no-tickets`, `--monitor`, `--mpm-resume`, `--resume`,
     `--reload-agents`, `--headless`, `--sdk`, `--prompt`, `--ztk`, `--no-ztk`,
     `--debug-ztk`, `--channels`, `--model`, `--inject-port`, and approximately 20
     others) at the top level for backward compatibility with bare `claude-mpm <flag>`
     invocations that do not specify an explicit subcommand.
  3. Creates a `subparsers` action group via `parser.add_subparsers`.
  4. Iterates through approximately 35 subparser-registration calls, each wrapped in
     an independent `try/except ImportError: pass` block. Each call imports a
     dedicated `*_parser.py` module and invokes its `add_*_subparser(subparsers)`
     factory. Subparsers covered include: `run`, `tickets`, `agents`, `source`,
     `skill-source`, `agent-source`, `auto-configure`, `memory`, `skills`, `messages`,
     `queue`, `config`, `settings`, `profile`, `monitor`, `dashboard`, `local-deploy`,
     `mcp`, `agent-manager`, `configure`, `oauth`, `auth`, `setup`, `install`, `slack`,
     `tools`, `provider`, `uninstall`, `debug`, `analyze`, `analyze-code`, `mpm-init`,
     `search`, `channels`, `serve`.
  5. Within the final outer `try` block, also directly inlines the subparser
     definitions for: `hook-errors` (with `hook_errors_command` positional, `--format`,
     `--hook-type`, `-y` arguments), `autotodos` (with `autotodos_command` positional
     plus `text`, `--format`, `--output`, `--error-key`, `--event-type`, `--file`,
     `--save`, `-y` arguments), and the `aggregate`, `cleanup`, `mcp-pipx-config`,
     `doctor`, `gh`, `postmortem`, `upgrade`, `migrate`, `verify`, `summarize`,
     `update-statusline`, `ztk-stats`, `ztk`, `llmlingua-stats` commands (each via
     their own `add_*_parser(subparsers)` factory call).
  6. Returns the fully built parser.

- **Error conditions:** Any `ImportError` from an individual subparser module is
  silently swallowed; the corresponding subcommand is absent from the parser but all
  others remain available. This makes partial installations functional. Non-`ImportError`
  exceptions from the final outer `try` block are also caught via the broad `except
  ImportError: pass` (note: this means other exceptions such as `TypeError` or
  `AttributeError` in that final block are also silently swallowed — rationale unclear;
  inferred as broad safety net for testing / refactoring contexts).

- **`SuggestingArgumentParser` behavior (error override):** When `argparse` would
  normally call `sys.exit(2)` with a plain error message, the overriding `error()`
  method instead prints a Rich-formatted error, calls `suggest_similar_commands` to
  find fuzzy matches, prints any suggestion found, then calls `sys.exit(2)`. This
  applies to invalid subcommand choices and unrecognised arguments.

### Rationale (WHY)

The function is a pure factory: it has no state and no side effects other than
constructing and returning the parser object. All callers need a fully configured
parser; this single entry point ensures consistency across all invocation paths (the
main CLI entrypoint, tests, and any tool that constructs the parser programmatically).

Top-level run arguments are registered at both the top level and inside the `run`
subparser. This duplication is intentional: it preserves backward compatibility for
users who type `claude-mpm --no-tickets` without an explicit `run` subcommand. The
`ensure_run_attributes` function in `executor.py` fills in defaults when the bare
top-level form is used, so both invocation styles reach the run handler with a complete
attribute set.

The `try/except ImportError: pass` pattern around every subparser registration exists
because the codebase supports partial installations where some optional command modules
are not installed. A missing module for an infrequently used command should not prevent
the common commands from working. This is a deliberate availability trade-off: the
parser succeeds with a reduced command set rather than failing entirely.

The inline `hook-errors` and `autotodos` subparser definitions (not delegated to their
own `*_parser.py` modules) appear to be an oversight or were added during a fast
iteration cycle where creating a dedicated parser module was deferred. Rationale for
this inconsistency is not documented in the code; inferred as technical debt.

The `SuggestingArgumentParser` subclass exists because the stock argparse error message
for invalid subcommands is widely considered unfriendly. The suggestion mechanism
reduces user friction when a command name is misspelled.

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/cli/parsers/base_parser.py` | `create_parser` | Full implementation |
| `src/claude_mpm/cli/parsers/base_parser.py` | `create_main_parser` | Creates the base `SuggestingArgumentParser` |
| `src/claude_mpm/cli/parsers/base_parser.py` | `add_top_level_run_arguments` | Attaches top-level run flags for backward compat |
| `src/claude_mpm/cli/parsers/base_parser.py` | `SuggestingArgumentParser` | Custom parser with fuzzy-match error override |

---

## Remote skills sync on startup {#SPEC-CLI-05~1}

**ID:** SPEC-CLI-05~1
**Status:** Active

### Behavior Contract (WHAT)

- **Inputs:**
  - `force_sync: bool` — if `True`, bypasses the TTL gate and forces a full network
    sync. Defaults to `False`.

- **Outputs:** None (returns implicitly). Side effects: skill files downloaded from
  remote Git sources to `~/.claude-mpm/cache/`, deployed to `.claude/skills/` in the
  current working directory, and TTL state updated in
  `~/.claude-mpm/cache/sync-state.json`.

- **TTL gate:** If `force_sync` is `False` and the `"skills"` key in the sync-state
  file was written within the last `CLAUDE_MPM_SYNC_TTL` seconds (default 86400), the
  function returns immediately without any network activity.

- **Main sync workflow (when TTL gate is not triggered):**
  1. Loads active profile from `ConfigLoader` and sets up `ProfileManager` for profile-
     based skill filtering.
  2. Instantiates `SkillSourceConfiguration` and `GitSkillSourceManager`. If no sources
     are enabled (empty list from `config.get_enabled_sources()`), returns immediately.
  3. **Phase 1 — File discovery:** For each enabled source, queries the GitHub Tree API
     via `_discover_repository_files_via_tree_api` to count relevant files (`.md`,
     `.json`, `.gitignore`) and unique skill directories (directories containing
     `SKILL.md`). If Tree API discovery fails for a source, falls back to estimates of
     150 files and 50 skills. Constructs a `ProgressBar` with the discovered total.
  4. **Phase 1 — Sync:** Calls `manager.sync_all_sources(force=force_sync,
     progress_callback=_cumulative_progress)`. The `_cumulative_progress` closure
     converts per-source monotonically-increasing counters into a single cumulative
     counter across all sources, preventing the progress bar from appearing to reset
     between sources. Finishes the progress bar with
     ``"Complete: N downloaded, M cached (T files, S skills)"`` when any files
     were served from cache, or ``"Complete: N files downloaded (S skills)"``
     on a first sync where all files are new downloads.
  5. **Phase 2 — Agent scanning:** Scans `.claude/agents/` in the current working
     directory via `get_required_skills_from_agents` to discover which skill IDs are
     referenced by deployed agents. Saves the resulting list to
     `.claude-mpm/configuration.yaml` via `save_agent_skills_to_config`. This step
     always runs (even if the sync used cached files) to ensure cleanup logic has an
     accurate filter list.
  6. **Phase 3 — Skill resolution:** Calls `get_skills_to_deploy(project_config_path)`
     to determine which skills to deploy. The function returns either `user_defined`
     (explicit list in config) or `agent_referenced` (derived from Phase 2 agent scan)
     skills. An empty resolved list triggers a warning log (all-or-nothing deployment
     without cleanup would result).
  7. **Phase 4 — Profile filtering:** If an active profile is set and the profile
     manager is loaded, filters `skills_to_deploy` to only those skills for which
     `profile_manager.is_skill_enabled(skill)` returns `True`. A safeguard warns if the
     filter removes all skills (possible naming mismatch in profile config). When no
     explicit skill list exists, derives the list from all available skills filtered by
     the profile.
  8. **Phase 5 — Deployment:** Calls `manager.deploy_skills(target_dir=.claude/skills/,
     force=force_sync, skill_filter=set(skills_to_deploy))`. An empty
     `skills_to_deploy` list passes `skill_filter=set()` (deploy nothing), not `None`
     (deploy everything). Displays a second `ProgressBar` for deployment. Logs
     deployment errors.
  9. Records successful sync time via `_mark_sync_done("skills")`.

- **Error conditions:** A top-level `try/except Exception` wraps the entire workflow.
  Any exception logs at debug level and returns without updating the TTL timestamp.
  Startup is never blocked.

### Rationale (WHY)

Skill sync runs unconditionally on every startup but is gated behind a 24-hour TTL to
avoid unnecessary network traffic. The TTL is project-global (not per-source) to keep
the state file simple.

The agent-scanning step (Phase 2) was introduced to enable selective deployment: instead
of always deploying every skill from every source, the deployer only installs the skills
that the currently deployed agents actually reference. This bounds the number of skills
visible to Claude Code in the project's `.claude/skills/` directory, avoids polluting
the user's skill namespace with unrelated skills, and enables cleanup (removing skills
that are no longer referenced). The comment in the code ("ALWAYS run to ensure cleanup
works") documents why this step cannot be skipped even when the sync uses cached files.

The two-tier progress display (sync phase, then deploy phase) exists because the two
operations are conceptually distinct — downloading files and writing them to the skill
directory — and have different durations. Displaying one bar for both would be
misleading.

The `_cumulative_progress` closure exists because `sync_all_sources` provides per-source
counters that reset to 1 at the start of each new source, which would cause a
`ProgressBar` tracking a global total to jump backward. The closure detects resets and
banks the previous source's contribution into an offset, maintaining a monotonically
increasing global counter. This is an implementation detail of the progress-bar
integration with an upstream API that was not designed with multi-source progress in
mind.

Skill files are deployed to the project-local `.claude/skills/` rather than the user-
global `~/.claude/skills/` to keep different projects' skill sets isolated and to avoid
a project's dependencies polluting the user's global namespace. This is a deliberate
isolation trade-off documented directly in a code comment.

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/cli/startup.py` | `sync_remote_skills_on_startup` | Full implementation |

---

## Remote agents sync on startup {#SPEC-CLI-06~1}

**ID:** SPEC-CLI-06~1
**Status:** Active

### Behavior Contract (WHAT)

- **Inputs:**
  - `force_sync: bool` — if `True`, bypasses the TTL gate and forces a full network
    sync. Defaults to `False`.

- **Outputs:** None (returns implicitly). Side effects: agent files downloaded from
  remote Git sources to `~/.claude-mpm/cache/agents/`, deployed to `.claude/agents/`
  in the current working directory via reconciliation, legacy agent cache directories
  removed, TTL state updated in `~/.claude-mpm/cache/sync-state.json`, and a
  deployment-state JSON written to `.claude-mpm/cache/deployment_state.json`.

- **TTL gate:** If `force_sync` is `False` AND the `"agents"` sync-state key is within
  TTL AND `_agent_sources_changed_since_last_sync()` returns `False` (i.e., the
  `~/.claude-mpm/config/agent_sources.yaml` file has not been modified since the last
  recorded sync), the function returns immediately. If `agent_sources.yaml` has been
  modified more recently than the last sync, the TTL is bypassed regardless of age.

- **Main sync workflow (when TTL gate is not triggered):**
  1. **Config resolution:** Loads `active_profile` from `ConfigLoader`. Calls
     `AgentPipelineConfig.resolve(mode="startup", profile=active_profile,
     project_dir=project_root)` to determine the effective set of enabled agents,
     required agents, and exclusions. Logs any warnings from pipeline config resolution.
  2. **Phase 1 — Git sync:** Calls `sync_agents_on_startup(force_refresh=force_sync)`
     (from `services.agents.startup_sync`). This function downloads or validates agent
     files from all configured Git sources using ETag-based caching. Returns a result
     dict with keys `enabled`, `sources_synced`, `total_downloaded`, `cache_hits`,
     `duration_ms`, and `errors`.
  3. **Phase 2 — Deployment (conditional):** Only executes if
     `result.get("enabled") and result.get("sources_synced", 0) > 0`. Constructs a
     `UnifiedConfig` and overlays the pipeline config's effective agent list onto it,
     but only if there is an explicit agent selection (active profile or
     `pipeline_config.has_explicit_agent_selection`). If there is no explicit selection,
     sets `unified_config.agents.auto_discover = True` instead, so the reconciler
     preserves all currently deployed agents. Calls
     `perform_startup_reconciliation(project_path, unified_config, silent=False)` to
     deploy configured agents from cache to `.claude/agents/`, remove agents no longer
     in the effective set, and leave unchanged agents untouched. Displays a `ProgressBar`
     for the reconciliation result (total of deployed + removed + unchanged operations).
     Logs any reconciliation errors (up to 10 shown on TTY). Calls
     `_save_deployment_state_after_reconciliation` to write a deployment-state file that
     prevents `ClaudeRunner.setup_agents()` from re-deploying agents that reconciliation
     already placed.
  4. **Phase 3 — Legacy cache cleanup:** Calls `cleanup_legacy_agent_cache()` to remove
     known legacy category directories from `~/.claude-mpm/cache/agents/`. Runs after
     sync and deployment to avoid removing directories that sync might recreate.
  5. Records successful sync time via `_mark_sync_done("agents")`.

- **Error conditions:**
  - A top-level `try/except Exception` wraps the entire workflow. Any exception logs at
    debug level and returns without recording sync time. Legacy cache cleanup is
    attempted even after a top-level exception (in its own nested `try/except`).
  - Deployment step failures (step 2) are caught separately; they log a warning and
    continue to the legacy cleanup and TTL recording steps.
  - `_display_manifest_compatibility_warnings()` is called between Git sync and
    deployment (after sync populates the `ManifestCache`). Any exceptions within that
    function are internally suppressed.

### Rationale (WHY)

The two-condition TTL gate (time-based AND source-file-based) exists because the
standard TTL alone would leave users waiting up to 24 hours to see the effect of adding
a new agent source to `agent_sources.yaml`. The file-modification check bypasses the
TTL specifically for configuration changes, while preserving the performance benefit of
the TTL for the common case (no config changes).

The conditional on `result.get("sources_synced", 0) > 0` before deployment is
intentional: if Git sync was disabled or no sources were synced (e.g., all sources
returned 304 Not Modified with no files to update), skipping reconciliation avoids
writing a new deployment-state file that would indicate a fresh deployment when in
fact nothing changed. This prevents `ClaudeRunner.setup_agents()` from seeing a stale
"already deployed" state.

The `UnifiedConfig` overlay logic (explicitly setting `agents.enabled` vs. setting
`auto_discover = True`) addresses a subtle edge case: when no profile is active and no
explicit agent selection is configured, `AgentPipelineConfig.get_agents_to_deploy()`
returns only the small required-agents set. If that empty-ish list were written to
`unified_config.agents.enabled`, the reconciler would interpret it as "deploy only
these agents" and remove all others. The `auto_discover = True` path instead tells the
reconciler to use its early-return path that preserves existing deployments. The code
comment "overriding with that tiny list would cause the reconciler to remove all other
agents" confirms this is a known correctness invariant, not a performance optimisation.

`_save_deployment_state_after_reconciliation` exists specifically to prevent
`ClaudeRunner.setup_agents()` from running a redundant second deployment on the same
startup. Without this state file, `setup_agents()` has no way to know reconciliation
already ran and would redeploy all agents, showing a confusing "✓ Deployed 31 native
agents" message after the startup progress bar already showed the deployment.

Legacy cache cleanup runs after sync (not before) because sync can recreate legacy
directories that cleanup would have just removed. The comment "CRITICAL: This must run
AFTER sync completes" in the code makes this ordering constraint explicit.

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/cli/startup.py` | `sync_remote_agents_on_startup` | Full implementation |
| `src/claude_mpm/cli/startup.py` | `_save_deployment_state_after_reconciliation` | Post-reconciliation state persistence |
| `src/claude_mpm/cli/startup.py` | `cleanup_legacy_agent_cache` | Legacy cache directory removal |
