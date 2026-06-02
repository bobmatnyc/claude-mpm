# Agents Subsystem — Spec-Linked Documentation

**Status:** Active
**Version:** v1
**Subsystem:** AGENTS

This document covers the agent subsystem of `claude_mpm`: discovery and loading,
frontmatter validation, agent metadata, name normalization, the assembly pipeline,
BASE template composition, bundled vs. deployed agents, deployment services, orphan
detection, and the frontmatter schema. Skills are a separate subsystem and are not
covered here.

The IDs below use the `{#SPEC-AGENTS-NN~1}` anchor form recognised by the traceability
checker. Engineer agents will add matching `References: SPEC-AGENTS-NN~1` entries to
implementing module docstrings once this spec is reviewed.

---

## Table of Contents

| ID | Section | Primary implementing unit |
|----|---------|--------------------------|
| SPEC-AGENTS-01~1 | [Agent discovery and registry](#agent-discovery-and-registry-spec-agents-011) | `UnifiedAgentRegistry.discover_agents` |
| SPEC-AGENTS-02~1 | [AgentLoader public interface](#agentloader-public-interface-spec-agents-021) | `AgentLoader` |
| SPEC-AGENTS-03~1 | [Frontmatter validation and auto-correction](#frontmatter-validation-and-auto-correction-spec-agents-031) | `FrontmatterValidator.validate_and_correct` |
| SPEC-AGENTS-04~1 | [Agent name normalization](#agent-name-normalization-spec-agents-041) | `AgentNameNormalizer` |
| SPEC-AGENTS-05~1 | [Static capability registry](#static-capability-registry-spec-agents-051) | `agents_metadata.ALL_AGENT_CONFIGS` |
| SPEC-AGENTS-06~1 | [Agent assembly pipeline — subagent path](#agent-assembly-pipeline--subagent-path-spec-agents-061) | `AgentTemplateBuilder.build_agent_markdown` |
| SPEC-AGENTS-07~1 | [PM framework assembly pipeline](#pm-framework-assembly-pipeline-spec-agents-071) | `SystemInstructionsDeployer.deploy_system_instructions` |
| SPEC-AGENTS-08~1 | [BASE template composition](#base-template-composition-spec-agents-081) | `AgentTemplateBuilder._discover_base_agent_templates` |
| SPEC-AGENTS-09~1 | [SLD instruction injection hook](#sld-instruction-injection-hook-spec-agents-091) | `AgentTemplateBuilder.build_agent_markdown` + `get_sld_instruction_for_agent` |
| SPEC-AGENTS-10~1 | [Bundled vs. deployed agent sources](#bundled-vs-deployed-agent-sources-spec-agents-101) | `UnifiedAgentRegistry`, `AgentDeploymentService` |
| SPEC-AGENTS-11~1 | [AgentDeploymentService — deploy and remove](#agentdeploymentservice--deploy-and-remove-spec-agents-111) | `AgentDeploymentService.deploy_agents` |
| SPEC-AGENTS-12~1 | [Startup reconciliation and orphan detection](#startup-reconciliation-and-orphan-detection-spec-agents-121) | `perform_startup_reconciliation`, `_detect_and_remove_orphaned_agents` |
| SPEC-AGENTS-13~1 | [Frontmatter schema](#frontmatter-schema-spec-agents-131) | `frontmatter_schema.json`, `FrontmatterValidator` |

---

## Agent discovery and registry {#SPEC-AGENTS-01~1}

**ID:** SPEC-AGENTS-01~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

- **Inputs:** None at call time. Discovery paths are configured at `UnifiedAgentRegistry`
  init time from `PathManager` values, in priority order: (1) `.claude/agents/` in cwd,
  (2) `path_manager.get_project_agents_dir()`, (3) `path_manager.get_user_agents_dir()`
  (deprecated), (4) `path_manager.get_system_agents_dir()`, (5)
  `~/.claude-mpm/cache/agents/`.

- **Outputs:** A dict mapping agent stem names to `AgentMetadata` dataclass instances.
  Higher-priority tiers shadow lower-priority tiers when the same stem appears in
  multiple paths. The tier value (`PROJECT`, `USER`, `SYSTEM`) is recorded on each
  `AgentMetadata` instance.

- **Preconditions:** At least one discovery path must exist on disk; missing paths are
  silently skipped. The registry is a lazy singleton — it is created on first call to
  `get_agent_registry()`.

- **Postconditions:** Calling `discover_agents()` a second time with `force_refresh=False`
  returns the cached result. `force_refresh=True` re-scans all paths. Accepted file
  extensions are `.md`, `.json`, `.yaml`, `.yml`.

- **Tier precedence:** Applied after all paths are scanned via `_apply_tier_precedence()`.
  When the same stem appears at multiple tiers the highest-tier entry wins; the others
  are discarded.

- **Error conditions:** Any path that cannot be read is skipped and logged at debug level.
  The function never raises to its caller.

### Rationale (WHY)

Centralising discovery in one registry eliminates the need for every consumer to
re-implement path-walking. The five-path priority ordering ensures user-authored agents
in `.claude/agents/` always override remote-cached or system-level agents, which is
necessary for per-project customisation without breaking the shared cache.

The lazy singleton avoids repeated filesystem scans at import time. `force_refresh`
allows callers (notably the CLI `reload-agents` flag) to pick up newly placed files
without restarting the process.

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/core/unified_agent_registry.py` | `UnifiedAgentRegistry` | Primary registry class |
| `src/claude_mpm/core/unified_agent_registry.py` | `UnifiedAgentRegistry.discover_agents` | Discovery entry point |
| `src/claude_mpm/core/unified_agent_registry.py` | `UnifiedAgentRegistry._apply_tier_precedence` | Tier shadowing logic |
| `src/claude_mpm/core/unified_agent_registry.py` | `get_agent_registry` | Lazy singleton factory |

---

## AgentLoader public interface {#SPEC-AGENTS-02~1}

**ID:** SPEC-AGENTS-02~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

- **Inputs (primary methods):**
  - `list_agents()` — no arguments. Returns a dict of all discovered agents (delegates to
    `self.registry.list_agents()`).
  - `get_agent(agent_id: str)` — returns a plain `dict[str, Any]` or `None`. Coerces
    `AgentMetadata` dataclasses to dicts before returning so callers may use `.get()`.
  - `get_agent_prompt(agent_id: str, force_reload: bool = False)` — returns the markdown
    body of the agent file as a string, with YAML frontmatter stripped. Uses a multi-step
    name resolution cascade (exact match → `{name}_agent` suffix → `_agent` strip →
    normalizer alias lookup → lowercase-hyphen-to-underscore clean).
  - `get_agent_metadata(agent_id: str)` — returns a structured dict containing `agent_id`,
    `name`, `description`, `category`, `version`, `model`, `resource_tier`, `tier`,
    `tools`, `capabilities`, `source_file`, `has_project_memory`, and optional memory
    fields. Returns `None` if the agent is not found.

- **Outputs:** Described per-method above.

- **Preconditions:** The module-level singleton `_loader` must be initialised. The first
  call to any module-level function (`get_agent_prompt`, `list_available_agents`, etc.)
  triggers `_get_loader()`, which creates the singleton.

- **Postconditions:** `get_agent_prompt` returns only the body text (no frontmatter). For
  `.md` files, frontmatter is stripped via `_extract_md_body`. For legacy JSON files,
  the `instructions` field is extracted.

- **Error conditions:** `get_agent_prompt` returns `None` if the agent is not found after
  all resolution steps. `get_agent_metadata` returns `None` if the agent is not found.
  Neither raises to the caller.

### Rationale (WHY)

`AgentLoader` is the stable public facade over `UnifiedAgentRegistry`, isolating
consumers from registry internals and dataclass types. The dict coercion in `get_agent`
ensures backward compatibility for downstream code written when agents were stored as
plain dicts (pre-dataclass era).

The multi-step name resolution cascade exists because agent names arrive in many formats
from user input, the Task tool, and the TodoWrite system. Centralising the cascade in
`get_agent_prompt` prevents per-call ad-hoc normalisation across the codebase.

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/agents/agent_loader.py` | `AgentLoader` | Public facade class |
| `src/claude_mpm/agents/agent_loader.py` | `AgentLoader.get_agent` | Dataclass→dict coercion |
| `src/claude_mpm/agents/agent_loader.py` | `AgentLoader.get_agent_prompt` | Body extraction + name resolution |
| `src/claude_mpm/agents/agent_loader.py` | `AgentLoader.get_agent_metadata` | Structured metadata dict |
| `src/claude_mpm/agents/agent_loader.py` | `_get_loader` | Lazy singleton factory |

---

## Frontmatter validation and auto-correction {#SPEC-AGENTS-03~1}

**ID:** SPEC-AGENTS-03~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

- **Inputs:**
  - `validate_and_correct(frontmatter: dict)` — accepts a parsed YAML frontmatter dict.
  - `correct_file(file_path: Path, dry_run: bool = False)` — accepts a path to an `.md`
    agent file.

- **Outputs:**
  - `validate_and_correct` returns a `ValidationResult` with `corrected_frontmatter` (a
    new dict with corrections applied, never mutating the input) and `field_corrections`
    (a dict mapping field names to descriptions of corrections made).
  - `correct_file` calls `validate_and_correct` and writes corrections back to disk using
    line-by-line regex replacement that preserves YAML structure. When `dry_run=True`,
    no file is written.

- **Schema loading:** Attempts to load `src/claude_mpm/schemas/frontmatter_schema.json`
  at init time. Falls back to a hardcoded field set if the file is missing.

- **Required fields** (from schema): `name`, `description`, `version`, `model`.

- **Field-level rules:**
  - `name`: normalised to `^[a-z][a-z0-9_]*$` — auto-corrected (lowercased,
    hyphens converted to underscores, invalid characters stripped).
  - `model`: normalised via `ModelTier.normalize()` to `opus | sonnet | haiku`.
    Full model version strings are accepted and normalised to tier names.
  - `tools`: parsed from string representation or JSON array; case-normalised against
    `TOOL_CORRECTIONS` dict. Unknown tools produce warnings, not errors.
  - `version`, `base_version`: validated against `\d+\.\d+\.\d+`; `v` prefix stripped;
    two-part versions padded.
  - `collection_id`, `source_path`, `canonical_id`: auto-generated when `collection_id`
    is present but `canonical_id` is missing.

- **Error conditions:** Individual field errors are recorded in `ValidationResult.errors`
  but do not abort processing of other fields. `correct_file` logs failures and returns
  without raising.

### Rationale (WHY)

Auto-correction reduces manual maintenance burden when agents are authored in external
repositories with varying style conventions or when agents are migrated from legacy JSON
format. Non-mutating validation allows callers to inspect proposed corrections before
committing them to disk.

The schema-file approach (with hardcoded fallback) avoids hard-coding the full field
list in Python source while still making the validator functional in environments where
the schema file is missing (e.g., during testing with a partial install).

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/agents/frontmatter_validator.py` | `FrontmatterValidator` | Validator class |
| `src/claude_mpm/agents/frontmatter_validator.py` | `FrontmatterValidator.validate_and_correct` | Non-mutating validation |
| `src/claude_mpm/agents/frontmatter_validator.py` | `FrontmatterValidator.correct_file` | In-place file correction |
| `src/claude_mpm/agents/frontmatter_validator.py` | `FrontmatterValidator._validate_name_field` | Name normalisation |

---

## Agent name normalization {#SPEC-AGENTS-04~1}

**ID:** SPEC-AGENTS-04~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

- **Inputs:** Raw agent name strings from user input, the Task tool, TodoWrite, or
  any other caller.

- **Outputs (key methods):**
  - `normalize(name: str) -> str` — returns display name (e.g., `"engineer"` →
    `"Engineer"`).
  - `to_key(name: str) -> str` — returns underscore-normalised key (e.g.,
    `"Python Engineer"` → `"python_engineer"`).
  - `to_todo_prefix(name: str) -> str` — formats for todo output.
  - `from_task_format(name: str) -> str` — reverse mapping from task tool format.

- **Canonical name tables:** `CANONICAL_NAMES` is built at class load time by
  `_build_canonical_names_dynamic()`, which merges the static `AGENT_NAME_MAP`
  (from `agent_name_registry.py`) with a runtime scan of `.claude/agents/`. Static
  entries take priority for known agents. `ALIASES` provides a reverse mapping from
  aliases to canonical stems.

- **Preconditions:** None. Unknown names fall through to lowercase/underscore
  normalisation rather than raising.

- **Error conditions:** No exceptions raised; unrecognised names are normalised
  heuristically.

### Rationale (WHY)

Agent names arrive in multiple formats from different subsystems and there is no
authoritative single format enforced at input boundaries. A centralised normalizer
prevents each consumer from implementing ad-hoc normalisation, which historically
caused lookup misses when format expectations diverged.

The dynamic scan of `.claude/agents/` at class load time ensures custom project agents
become resolvable without code changes to the static map. Static entries take priority
to prevent user agents from accidentally overriding known-agent display names.

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/core/agent_name_normalizer.py` | `AgentNameNormalizer` | Normalizer class with class-level tables |
| `src/claude_mpm/core/agent_name_normalizer.py` | `AgentNameNormalizer.normalize` | Display name lookup |
| `src/claude_mpm/core/agent_name_normalizer.py` | `AgentNameNormalizer.to_key` | Underscore-key conversion |
| `src/claude_mpm/core/agent_name_normalizer.py` | `_build_canonical_names_dynamic` | Dynamic table construction |
| `src/claude_mpm/core/agent_name_registry.py` | `AGENT_NAME_MAP` | Static curated name map |

---

## Static capability registry {#SPEC-AGENTS-05~1}

**ID:** SPEC-AGENTS-05~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

- **Inputs:** None at runtime. `agents_metadata.py` is a static module containing
  hardcoded capability dictionaries for 14 agent types.

- **Outputs:** `ALL_AGENT_CONFIGS` — a dict mapping agent type strings (e.g.,
  `"documentation"`, `"engineer"`, `"security"`) to config dicts containing `name`,
  `version`, `type`, `capabilities` (list of strings), `primary_interface`, and
  `performance_targets`.

- **Preconditions:** None. The module initialises at import time with no I/O.

- **Postconditions:** `ALL_AGENT_CONFIGS` is importable from `claude_mpm.agents` via
  the package `__init__.py` re-export. It is not wired into any runtime discovery,
  routing, or deployment path.

- **Error conditions:** None — purely static data.

### Rationale (WHY)

The module was introduced to provide a machine-readable capability registry that could
drive programmatic agent selection. It serves as documentation-in-code form of the
intended capability contract for each agent type. It is not currently wired into
discovery or dispatch (see Known Drift), making it informational rather than
operational.

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/agents/agents_metadata.py` | `ALL_AGENT_CONFIGS` | Static capability dict |
| `src/claude_mpm/agents/__init__.py` | — | Re-exports `ALL_AGENT_CONFIGS` |

---

## Agent assembly pipeline — subagent path {#SPEC-AGENTS-06~1}

**ID:** SPEC-AGENTS-06~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

- **Inputs:**
  - `agent_type: str` — agent category (e.g., `"engineer"`, `"qa"`, `"ops"`).
  - `template_path: Path` — path to the source `.md` agent file.
  - `config: dict | None` — optional project configuration dict (used for the SLD
    injection hook; safe to pass `None`).
  - Additional optional arguments: `agent_name`, `agent_version`, `tools`,
    `permission_mode`, `model`, and others that override frontmatter values.

- **Outputs:** A fully assembled `.md` string with YAML frontmatter followed by the
  agent's instruction body. The string is ready to be written to `.claude/agents/`.

- **Assembly sequence:**
  1. Parse existing frontmatter from `template_path`.
  2. Merge caller-supplied overrides into frontmatter fields.
  3. Add `initialPrompt` if `get_initial_prompt(agent_name, agent_type)` returns a
     non-empty string. Per-name lookup (`INITIAL_PROMPT_BY_NAME`) takes priority over
     per-type lookup (`INITIAL_PROMPT_BY_TYPE`). Agents in `INITIAL_PROMPT_EXCLUDED_NAMES`
     never receive an `initialPrompt`.
  4. Apply default tools list (`["Read", "Write", "Edit", "Grep", "Glob", "Bash"]`)
     if no tools are specified.
  5. Render the YAML frontmatter block.
  6. Load the agent body text from `template_path`.
  7. Discover BASE template files via `_discover_base_agent_templates(template_path)`.
     Compose the body as: `[BASE templates (closest-first)] + [agent body]`, joined
     by `\n\n---\n\n`. If no hierarchical BASE templates are found, fall back to
     `_load_base_agent_instructions(agent_type)` (deprecated).
  8. Append a memory instructions block if neither `"memory-update"` nor `"Remember"`
     appear in the composed body.
  9. Append the SLD instruction block if `get_sld_instruction_for_agent(agent_type,
     config)` returns a non-empty string (see SPEC-AGENTS-09~1).

- **Error conditions:** Missing `template_path` raises `FileNotFoundError`. Individual
  field override failures are logged and skipped; the assembly does not abort.

### Rationale (WHY)

Build-time assembly rather than runtime assembly ensures agents are lightweight when
invoked — no dynamic template merging occurs on each Claude Code subprocess launch.
The pipeline produces a self-contained `.md` file that Claude Code reads directly.

The `initialPrompt` injection at assembly time (rather than authoring it in source
templates) allows the same source template to produce different run-mode behaviours
across agent types without duplicating template files.

The `\n\n---\n\n` separator between composed sections is a Markdown horizontal rule,
which Claude Code renders visually and which provides a clean content boundary for
debugging deployed files.

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/services/agents/deployment/agent_template_builder.py` | `AgentTemplateBuilder` | Builder class |
| `src/claude_mpm/services/agents/deployment/agent_template_builder.py` | `AgentTemplateBuilder.build_agent_markdown` | Full assembly entry point |
| `src/claude_mpm/services/agents/deployment/agent_template_builder.py` | `get_initial_prompt` | `initialPrompt` lookup |
| `src/claude_mpm/services/agents/deployment/agent_template_builder.py` | `INITIAL_PROMPT_BY_NAME` | Per-name lookup table |
| `src/claude_mpm/services/agents/deployment/agent_template_builder.py` | `INITIAL_PROMPT_BY_TYPE` | Per-type fallback table |
| `src/claude_mpm/services/agents/deployment/agent_template_builder.py` | `INITIAL_PROMPT_EXCLUDED_NAMES` | Blocklist for excluded agents |

---

## PM framework assembly pipeline {#SPEC-AGENTS-07~1}

**ID:** SPEC-AGENTS-07~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

- **Inputs:**
  - `target_dir: Path` — unused; present for interface compatibility. Output always
    goes to the project's `.claude-mpm/` directory.
  - `force_rebuild: bool` — when `True`, rebuilds the merged file even if it already
    exists.
  - `results: dict` — a mutable results dict updated in-place with deployment outcomes
    and errors.

- **Outputs:** Writes `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md`, a merged file composed
  from four source blocks in order: `PM_INSTRUCTIONS.md`, `AGENT_DELEGATION.md`,
  `WORKFLOW.md`, `MEMORY.md`. Each block is separated by a markdown horizontal rule.

- **Block resolution (additive override semantics):** For each block other than
  `WORKFLOW.md`, the resolver concatenates user override (`~/.claude-mpm/<BLOCK>.md`) +
  project override (`.claude-mpm/<BLOCK>.md`) when either exists; otherwise uses the
  system default from `src/claude_mpm/agents/`. Stale overrides (detected by presence
  of other-block marker strings) are skipped with a logged warning.

- **`WORKFLOW.md` lazy-load:** `WORKFLOW.md` uses a dedicated resolver that mirrors
  `InstructionLoader.load_workflow_instructions()`. When no override exists, a short
  `WORKFLOW_SYSTEM_REFERENCE` stub is inlined rather than the full system-level
  `WORKFLOW.md`. This keeps the deployed file concise while preserving the live prompt
  behaviour. The system-level `WORKFLOW.md` contains a mandatory **Delivery Workflow**
  section (issue → branch → build/test → commit → PR → squash-merge → publish, with
  trivial-work and release-tooling exemptions) in addition to the
  `## Mandatory 5-Phase Sequence`; the latter heading remains the stale-override
  fingerprint used by `BLOCK_MARKERS` / `_detect_stale_override`.

- **Error conditions:** If no blocks resolve to any content, an error is appended to
  `results["errors"]` and the function returns without writing. Individual block
  resolution failures are logged and the block is omitted (empty string contribution).

### Rationale (WHY)

The PM framework instructions are assembled once at deployment/startup and written to
a static file that Claude Code loads as context. This is preferable to dynamic assembly
on every PM invocation because it makes the PM's effective instructions inspectable
(humans can read `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md`) and avoids repeated I/O
during the session.

Additive override semantics allow teams to extend PM behaviour by dropping a
`.claude-mpm/PM_INSTRUCTIONS.md` file without replacing the system defaults entirely.
Stale-override detection prevents the common misconfiguration where a previously
deployed merged file is accidentally used as an override (causing content duplication).

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/services/agents/deployment/system_instructions_deployer.py` | `SystemInstructionsDeployer` | Deployer class |
| `src/claude_mpm/services/agents/deployment/system_instructions_deployer.py` | `SystemInstructionsDeployer.deploy_system_instructions` | Assembly and write entry point |
| `src/claude_mpm/services/agents/deployment/system_instructions_deployer.py` | `SystemInstructionsDeployer._resolve_workflow_block` | WORKFLOW.md lazy-load logic |
| `src/claude_mpm/services/agents/deployment/system_instructions_deployer.py` | `SystemInstructionsDeployer._detect_stale_override` | Stale override detection |

---

## BASE template composition {#SPEC-AGENTS-08~1}

**ID:** SPEC-AGENTS-08~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

- **Inputs:** `agent_file: Path` — the path to the source agent `.md` file being
  assembled.

- **Outputs:** An ordered list of `Path` objects pointing to discovered `BASE-AGENT.md`
  or `BASE_AGENT.md` files, sorted from closest to farthest relative to `agent_file`.

- **Discovery algorithm:** `_discover_base_agent_templates` walks upward from the
  directory containing `agent_file`, up to 10 directory levels, checking each level
  for files named `BASE-AGENT.md` (hyphen variant, used in external agent repos) or
  `BASE_AGENT.md` (underscore variant, used in the framework source tree). Discovery
  stops at the git repository root after finding a `BASE-AGENT.md`. All found paths
  are returned in closest-first order.

- **Composition in `build_agent_markdown`:** The base template list is composed in
  reverse (farthest-first, so more general instructions appear before more specific
  ones), then the agent's own body is appended last. Sections are joined with
  `\n\n---\n\n`.

- **Fallback:** If `_discover_base_agent_templates` returns an empty list,
  `_load_base_agent_instructions(agent_type)` is called as a deprecated fallback.
  This method attempts to load `BASE_{TYPE}.md` (e.g., `BASE_ENGINEER.md`) from the
  framework agents directory.

- **Error conditions:** If no base templates are found and the deprecated fallback also
  returns empty, the agent body is composed without any base content.

### Rationale (WHY)

Hierarchical BASE template discovery allows per-domain or per-subdirectory instruction
specialisation without requiring every agent to explicitly reference its base template.
An agent in `agents/python/` can have a Python-specific `BASE-AGENT.md` while still
inheriting the root-level `BASE_AGENT.md` instructions.

The hyphen vs. underscore naming variants exist because the framework source uses
underscores (matching Python convention) while external agent repositories use hyphens
(matching the broader Claude Code agent naming convention). Supporting both variants
avoids requiring external repos to rename their base files.

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/services/agents/deployment/agent_template_builder.py` | `AgentTemplateBuilder._discover_base_agent_templates` | Hierarchical BASE discovery |
| `src/claude_mpm/services/agents/deployment/agent_template_builder.py` | `AgentTemplateBuilder._load_base_agent_instructions` | Deprecated type-based fallback |
| `src/claude_mpm/agents/BASE_AGENT.md` | — | Root-level base template (git standards, memory routing, handoff protocol) |
| `src/claude_mpm/agents/BASE_ENGINEER.md` | — | Engineer-specific base (legacy fallback only) |
| `src/claude_mpm/agents/BASE_PM.md` | — | PM-specific base (legacy fallback only) |

---

## SLD instruction injection hook {#SPEC-AGENTS-09~1}

**ID:** SPEC-AGENTS-09~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

- **Inputs:**
  - `agent_type: str` — the category of agent being assembled (e.g., `"engineer"`,
    `"documentation"`, `"ops"`).
  - `config: dict | None` — the project configuration dict, used to read
    `workflow.spec_linked_docs.enabled`. Passing `None` is safe (treated as disabled).

- **Outputs:** `get_sld_instruction_for_agent(agent_type, config)` returns a non-empty
  string containing the SLD instruction block when both conditions are met: (1) the
  project configuration has `workflow.spec_linked_docs.enabled: true`, and (2) the
  `agent_type` is in the target set (`"engineer"` or `"documentation"`, plus any
  `agent_type` value ending in `"-engineer"` as a defensive suffix match).

  Returns `""` (empty string) when the feature is disabled or when the agent type is
  not in the target set.

- **Injection point:** `build_agent_markdown` calls `get_sld_instruction_for_agent`
  after all other content has been composed and appends the result with
  `"\n\n---\n\n"` as separator. An empty return value produces no separator and no
  content.

- **Error conditions:** If the configuration dict is malformed or missing keys,
  `get_sld_instruction_for_agent` returns `""` (fails closed — injection disabled,
  not errored).

### Rationale (WHY)

The SLD instruction block tells engineer and documentation agents how to write
`References` blocks in docstrings and how the traceability CI check works. Injecting
it at assembly time ensures every engineer agent receives the instructions without
requiring manual maintenance of each agent's source template.

Returning `""` when the feature is disabled makes the call safe to concatenate
unconditionally in `build_agent_markdown` — no conditional logic needed at the
injection site.

The `agent_type` target set is restricted to `engineer` and `documentation` because
SLD is a code-authoring and documentation discipline. Ops, QA, research, and security
agents do not produce source code or spec files as primary outputs, so injecting SLD
instructions into them would be noise.

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/config/sld_config.py` | `get_sld_instruction_for_agent` | Feature-gated instruction retrieval |
| `src/claude_mpm/config/sld_config.py` | `is_sld_target_agent_type` | Agent type classifier |
| `src/claude_mpm/services/agents/deployment/agent_template_builder.py` | `AgentTemplateBuilder.build_agent_markdown` | Injection site |

---

## Bundled vs. deployed agent sources {#SPEC-AGENTS-10~1}

**ID:** SPEC-AGENTS-10~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

- **Bundled agents** are agent `.md` files shipped inside the `claude_mpm` package at
  `src/claude_mpm/agents/bundled/`. At the time of writing, the bundled set contains
  two agents: `rust-engineer.md` and `ticketing.md`.

- **Remote/cached agents** are the primary source for production deployments. They are
  fetched from external GitHub repositories by `sync_remote_agents_on_startup` (covered
  in SPEC-CLI-06~1) and cached to `~/.claude-mpm/cache/agents/`. Discovery path (5) in
  SPEC-AGENTS-01~1 makes cached agents available to `UnifiedAgentRegistry`.

- **Deployed agents** reside in `.claude/agents/` at the project root. This is the
  Claude Code native discovery location. `AgentDeploymentService` and
  `perform_startup_reconciliation` populate this directory.

- **Retired/unused agents** reside in `.claude/agents/unused/` and are not included in
  any discovery path.

- **Tier relationship:** Agents in `.claude/agents/` (cwd, tier: PROJECT) shadow
  agents in `~/.claude-mpm/cache/agents/` (tier: SYSTEM) when both provide the same
  stem. Bundled agents are lowest priority.

- **Error conditions:** If `.claude/agents/` is absent, `UnifiedAgentRegistry` skips
  the path (no error). The sync subsystem is responsible for populating the cache;
  if the cache is empty, only bundled agents are available.

### Rationale (WHY)

The tiered source model allows the majority of the agent library to live in a maintained
external repository (reducing package size and enabling independent versioning) while
still supporting project-local overrides and a minimal bundled set for offline or first-
run scenarios.

The `unused/` convention provides a reversible archival mechanism: agents can be
retired from active deployment without permanent deletion, preserving the file for
reference or restoration.

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/agents/bundled/` | — | In-package bundled agent source |
| `src/claude_mpm/core/unified_agent_registry.py` | `UnifiedAgentRegistry` | Multi-source discovery with tier precedence |
| `src/claude_mpm/cli/startup.py` | `sync_remote_agents_on_startup` | Cache population from GitHub |

---

## AgentDeploymentService — deploy and remove {#SPEC-AGENTS-11~1}

**ID:** SPEC-AGENTS-11~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

- **Inputs:**
  - `deploy_agents(agents: list[AgentConfig], ...)` — accepts a list of `AgentConfig`
    objects describing agents to install or update.
  - `deploy_agent(agent: AgentConfig, ...)` — single-agent variant.
  - Additional utilities: `deployment_utils.normalize_deployment_filename`,
    `deployment_utils.ensure_agent_id_in_frontmatter`,
    `deployment_utils.ensure_model_in_frontmatter`, and `deployment_utils.deploy_agent_file`
    are used by the service internally.

- **Outputs:** Agent `.md` files written to the active agents directory (`.claude/agents/`
  by default). Deployment state JSON updated. Returns a deployment result describing
  counts of deployed, skipped, and failed agents.

- **Deployment utilities contract:**
  - `normalize_deployment_filename(name: str) -> str` — converts agent name to
    hyphen-separated lowercase filename (e.g., `"python_engineer"` → `"python-engineer.md"`).
  - `ensure_agent_id_in_frontmatter(content, filename) -> str` — inserts `agent_id` if
    absent.
  - `ensure_model_in_frontmatter(content, agent_name) -> str` — inserts default model
    tier if absent.
  - `validate_agent_file(source_file) -> ValidationResult` — checks the file is
    parseable and has required frontmatter fields.
  - `deploy_agent_file(source, dest, ...) -> DeploymentResult` — performs the atomic
    file copy.

- **Error conditions:** Per-agent failures are caught and recorded; they do not abort
  deployment of remaining agents. Files that fail validation are skipped and counted
  as failed.

### Rationale (WHY)

Separating deployment mechanics into `deployment_utils` functions (pure functions
operating on paths and strings) from the service class (which handles configuration
and state) makes the utility functions independently testable and reusable by other
deployment paths (e.g., single-agent deployer, multi-source deployment service).

The `ensure_*` post-processing functions exist to handle agents sourced from external
repositories that may omit `agent_id` or `model` fields. Rather than requiring all
external authors to follow MPM conventions, the deployment pipeline adds missing fields
at deploy time.

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/services/agents/deployment/agent_deployment.py` | `AgentDeploymentService` | Primary deployment service |
| `src/claude_mpm/services/agents/deployment/agent_deployment.py` | `AgentDeploymentService.deploy_agents` | Batch deployment entry point |
| `src/claude_mpm/services/agents/deployment_utils.py` | `normalize_deployment_filename` | Filename normalisation |
| `src/claude_mpm/services/agents/deployment_utils.py` | `ensure_agent_id_in_frontmatter` | `agent_id` injection |
| `src/claude_mpm/services/agents/deployment_utils.py` | `ensure_model_in_frontmatter` | Model tier injection |
| `src/claude_mpm/services/agents/deployment_utils.py` | `validate_agent_file` | Pre-deployment validation |
| `src/claude_mpm/services/agents/deployment_utils.py` | `deploy_agent_file` | Atomic file write |

---

## Startup reconciliation and orphan detection {#SPEC-AGENTS-12~1}

**ID:** SPEC-AGENTS-12~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

- **Inputs:**
  - `perform_startup_reconciliation(project_path: Path, config: UnifiedConfig, silent: bool)` —
    accepts a project path and a `UnifiedConfig` describing which agents should be
    deployed, updated, or left unchanged.
  - `_detect_and_remove_orphaned_agents(deployed_dir, expected_agents, ...)` — called
    internally after reconciliation completes.

- **Outputs:**
  - `perform_startup_reconciliation` returns a `DeploymentResult` capturing counts of
    deployed, removed, and unchanged agents. When `silent=False`, progress information
    is emitted to the terminal.
  - `_detect_and_remove_orphaned_agents` deletes orphaned `.md` files from
    `.claude/agents/` and returns the count of files removed.

- **Orphan definition:** An orphaned agent is a `.md` file in `.claude/agents/` that
  (a) carries MPM-managed provenance markers in its frontmatter and (b) is not present
  in the expected set derived from the current configuration.

- **Threshold guard (mass-deletion protection):** Orphan removal is suppressed if the
  ratio of orphan candidates to total deployed agents exceeds `ORPHAN_RATIO_THRESHOLD`
  AND the absolute count exceeds `ORPHAN_ABSOLUTE_FLOOR`. This prevents a partial
  cache sync from incorrectly marking the majority of deployed agents as orphans.

- **Local-only agent preservation:** Agents identified by `is_local_only()` (i.e.,
  user-authored agents not managed by MPM) are excluded from orphan candidates
  regardless of whether they appear in the expected set.

- **Error conditions:** Individual file deletion failures are logged and counted as
  failed removals; they do not abort the loop. Top-level exceptions in reconciliation
  are caught; the deployment result reflects the error.

### Rationale (WHY)

Reconciliation replaces the earlier "deploy everything, always" approach. By computing
the diff between deployed state and desired state, reconciliation minimises filesystem
writes (unchanged agents are not rewritten) and removes stale agents that were deployed
by a previous configuration.

The threshold guard exists because the cache is populated by a network sync that can
fail partially: if only half the expected agents were downloaded before a timeout, a
naive orphan-removal pass would delete all agents not in the partial cache, leaving the
user with an empty or severely reduced agent set. The ratio + absolute floor heuristic
provides a safety net without requiring explicit "reconciliation disabled" flags.

Local-only agent preservation is a deliberate policy: MPM manages MPM-sourced agents
and must not delete agents the user created independently.

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/services/agents/deployment/startup_reconciliation.py` | `perform_startup_reconciliation` | Reconciliation entry point |
| `src/claude_mpm/services/agents/deployment/startup_reconciliation.py` | `_detect_and_remove_orphaned_agents` | Orphan detection and removal |
| `src/claude_mpm/services/agents/deployment/deployment_reconciler.py` | `DeploymentReconciler` | Core reconcile-agents logic |
| `src/claude_mpm/services/agents/deployment/deployment_reconciler.py` | `DeploymentReconciler.reconcile_agents` | Agent-level reconciliation |

---

## Frontmatter schema {#SPEC-AGENTS-13~1}

**ID:** SPEC-AGENTS-13~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

- **Active schema:** `src/claude_mpm/schemas/frontmatter_schema.json` governs `.md`
  agent files. Title: "Agent Frontmatter Schema". Required fields: `name`,
  `description`, `version`, `model`. `additionalProperties: true` (unrecognised fields
  are permitted but not validated). Name pattern: `^[a-z][a-z0-9_-]*$` (hyphens and
  underscores allowed).

- **Claude Code native fields** (subset present in deployed agents): `name`,
  `description`, `model`, `effort`, `permissionMode`, `maxTurns`, `memory`, `color`,
  `skills`.

- **MPM-proprietary fields** (declared in schema; present in some deployed agents):
  `agent_id`, `agent_type`, `version`, `initialPrompt`.

- **`initialPrompt` field:** Defined in `frontmatter_schema.json` as
  `{"type": "string", "minLength": 1, "maxLength": 500}`. Injected at assembly time by
  `AgentTemplateBuilder.build_agent_markdown` — it is not authored in source templates
  and not present in all agents (only those matched by `INITIAL_PROMPT_BY_NAME` or
  `INITIAL_PROMPT_BY_TYPE`).

- **Legacy schema:** `src/claude_mpm/schemas/agent_schema.json` (version 1.3.0) governs
  the old JSON agent format. Required fields: `schema_version`, `agent_id`,
  `agent_version`, `agent_type`, `metadata`, `capabilities`, `instructions`. Used only
  by `AgentValidator` for validating legacy JSON agents; not used by the current `.md`
  pipeline.

- **Field list in CLAUDE.md vs. deployed reality:** CLAUDE.md lists `schema_version`,
  `resource_tier`, `timeout`, `capabilities`, `temperature` as MPM-proprietary fields.
  Inspection of deployed `.md` agents finds these fields absent; they appear only in
  the legacy JSON schema. CLAUDE.md's field list is partially stale (see Known Drift).

- **Error conditions:** `FrontmatterValidator` logs warnings for unknown tool names but
  does not fail on `additionalProperties`. Required field absence triggers a validation
  error recorded in `ValidationResult.errors`.

### Rationale (WHY)

Two schemas exist because the agent format migrated from JSON (circa v1.x) to YAML
frontmatter in `.md` files (current). Maintaining the legacy schema allows the
`AgentValidator` to still process JSON agents in mixed-format environments or during
migration without disrupting the new frontmatter pipeline.

`additionalProperties: true` in `frontmatter_schema.json` is intentional: Claude Code
may add new native fields over time, and MPM extension fields will evolve with new
feature work. A strict schema would require updates every time either set expands.

### Implementing Modules

| Module path | Qualname | Role |
|-------------|----------|------|
| `src/claude_mpm/schemas/frontmatter_schema.json` | — | Active `.md` frontmatter schema |
| `src/claude_mpm/schemas/agent_schema.json` | — | Legacy JSON agent schema |
| `src/claude_mpm/agents/frontmatter_validator.py` | `FrontmatterValidator` | Schema consumer (loads `frontmatter_schema.json`) |
| `src/claude_mpm/validation/agent_validator.py` | `AgentValidator` | Legacy JSON schema consumer |

---

## Known Drift

The following gaps between documentation/research and actual code were identified during
the grounding pass for this spec. Items marked **[FIXED]** were corrected in a prior
cycle; others remain as informational drift for future resolution.

| Drift ID | Component | Documented or Expected | Actual Behaviour | Severity |
|----------|-----------|----------------------|------------------|----------|
| D1 | `agent_loader.py` module docstring | References 7 sub-modules (`agent_registry.py`, `agent_cache.py`, `agent_validator.py`, `model_selector.py`, `legacy_support.py`, `async_loader.py`, `metrics_collector.py`) | None of these files exist; actual delegation is to `unified_agent_registry.py` | Medium |
| D2 | `AgentLoader.get_agent_metadata` | Expected to return metadata dict safely | Previously called `.get()` on `AgentMetadata` dataclass (no `.get()` method) causing `AttributeError` | **[FIXED this cycle]** — now routes through `self.get_agent()` which coerces to dict first |
| D3 | `_analyze_task_complexity` | Dynamic model selection based on task | Always returns hardcoded medium-complexity defaults; `TaskComplexityAnalyzer` permanently unavailable | Medium |
| D4 | CLAUDE.md MPM-proprietary field list | Lists `schema_version`, `resource_tier`, `timeout`, `capabilities`, `temperature` as active MPM fields | Not present in any sampled deployed `.md` agent; `initialPrompt` is used in 5+ deployed agents but absent from CLAUDE.md list | Medium |
| D5 | `FrontmatterValidator` name regex | `^[a-z][a-z0-9_]*$` (underscores only) | `frontmatter_schema.json` allows `^[a-z][a-z0-9_-]*$` (hyphens and underscores); deployed agents with hyphenated names (e.g., `nestjs-engineer`) would fail validator name checks | Medium |
| D6 | `agents_metadata.py` wiring | Intended as runtime capability registry | `ALL_AGENT_CONFIGS` is not imported by any runtime discovery, routing, or dispatch code; it is documentation-in-code only | Low |
| D7 | `BASE_ENGINEER.md`, `BASE_PM.md` | CLAUDE.md implies active base templates | Legacy fallback only; `_load_base_agent_instructions()` is explicitly marked DEPRECATED; `BASE_AGENT.md` is the only active base template in hierarchical composition | Low |
| D8 | `initialPrompt` field | Not listed in CLAUDE.md or research at time of writing | Used in 5+ deployed agents; documented in `frontmatter_schema.json`; injected at build time by `agent_template_builder.py` via `INITIAL_PROMPT_BY_NAME` / `INITIAL_PROMPT_BY_TYPE` lookup tables | Low |
| D9 | Bundled agents in `src/agents/bundled/` | Implied to be a comprehensive bundled set | Only 2 files (`rust-engineer.md`, `ticketing.md`); the vast majority of deployed agents originate from the external GitHub cache | Low |
