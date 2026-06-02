# Agents & Skills Subsystem — Ground-Truth Research

**Research date**: 2026-06-01  
**Scope**: Agent delegation & loading, bundled agent set, agent assembly pipeline, skills system  
**Methodology**: Direct file inspection, line-level verification against CLAUDE.md, AGENT_ASSEMBLY_PIPELINE.md, and deployed artefacts

---

## Table of Contents

1. [Agent Discovery & Loading](#1-agent-discovery--loading)
2. [Frontmatter Validation](#2-frontmatter-validation)
3. [Agent Name Normalization](#3-agent-name-normalization)
4. [agents_metadata.py — Static Capability Registry](#4-agents_metadatapy--static-capability-registry)
5. [Bundled Agent Set](#5-bundled-agent-set)
6. [Deployed Agent Set (.claude/agents/)](#6-deployed-agent-set-claudeagents)
7. [Agent Assembly Pipeline](#7-agent-assembly-pipeline)
8. [BASE Template System](#8-base-template-system)
9. [Skills System — SkillsRegistry (registry.py)](#9-skills-system--skillsregistry-registrypy)
10. [Skills System — SkillsService (skills_service.py)](#10-skills-system--skillsservice-skills_servicepy)
11. [Skills System — SkillManager (skill_manager.py)](#11-skills-system--skillmanager-skill_managerpy)
12. [Skills System — AgentSkillsInjector](#12-skills-system--agentskillsinjector)
13. [Frontmatter Schema](#13-frontmatter-schema)
14. [Summary Drift Matrix](#14-summary-drift-matrix)

---

## 1. Agent Discovery & Loading

### WHAT

The primary entry point is `src/claude_mpm/agents/agent_loader.py`. The module header describes itself as a "Unified Agent Loader System — Main Entry Point" and states it delegates to sub-modules (agent_registry.py, agent_cache.py, etc.), but **those sub-modules do not exist in the repository**. The actual delegation is to `src/claude_mpm/core/unified_agent_registry.py`.

**`AgentLoader` class** (lines 154–410):
- Initialises via singleton `get_agent_registry()` which returns a `UnifiedAgentRegistry` instance.
- `list_agents()` calls `self.registry.list_agents()`.
- `get_agent_prompt(agent_id)` reads from the registry; for `.md` files, strips YAML frontmatter using `_extract_md_body()` (lines 313–343), returning only the markdown body as instructions.
- `get_agent_metadata()` (line 345) calls `self.registry.get_agent(agent_id)` directly and then calls `.get()` on the result — this is a latent bug: `UnifiedAgentRegistry.get_agent()` returns `AgentMetadata` dataclasses, which do not have a `.get()` method. The method at `AgentLoader.get_agent()` (line 191) handles the dataclass→dict conversion, but `get_agent_metadata()` bypasses this coercion.

**`UnifiedAgentRegistry`** (`src/claude_mpm/core/unified_agent_registry.py`, line 127):
Discovery paths configured at init time (lines 175–215) in priority order:
1. `.claude/agents/` in cwd — inserted at index 0 (highest priority)
2. `path_manager.get_project_agents_dir()` — project-level agents directory
3. `path_manager.get_user_agents_dir()` — user-level (marked deprecated in comments)
4. `path_manager.get_system_agents_dir()` — system templates
5. `~/.claude-mpm/cache/agents/` — remote GitHub cache

`discover_agents()` (line 217) scans all paths with `rglob("*")`, creating `AgentMetadata` dataclasses. Files with extensions `.md`, `.json`, `.yaml`, `.yml` are accepted. Tier precedence (`PROJECT > USER > SYSTEM`) is applied after discovery via `_apply_tier_precedence()`.

**Module-level functions** (`get_agent_prompt`, `list_available_agents`, etc.) operate through a module-level singleton `_loader: AgentLoader | None`. `_get_loader()` creates it on first call (lazy singleton, line 416).

**Also present but unexplained**:
- `src/claude_mpm/agents/async_agent_loader.py` — a parallel `AsyncAgentLoader` class with its own discovery logic (`AgentTier` enum, `discover_agent_dirs_async()`, `load_json_agent_async()`, `load_md_agent_async()`). It imports `FrontmatterValidator` and uses its own path resolution logic. Relationship to the primary `AgentLoader` is not documented.
- `src/claude_mpm/agents/agent_loader_integration.py` — an `EnhancedAgentLoader` wrapper that delegates to `AgentManager` service. Adds `AgentDefinition` conversion layer on top of `get_agent_prompt()`.
- `src/claude_mpm/agents/system_agent_config.py` — `SystemAgentConfigManager` hardcodes configs for orchestrator, engineer, architecture, documentation, qa, research, ops, security, data_engineer, version_control agent types. These configurations are separate from and do not affect the file-based agent discovery system.

### WHY

Multiple loaders accumulated during refactoring. The module docstring describes a planned refactoring that never fully completed (the sub-modules it references were never created). The `async_agent_loader.py` appears to be a migration artefact.

### DRIFT

- **CLAUDE.md** does not mention `async_agent_loader.py`, `agent_loader_integration.py`, or `system_agent_config.py`, all of which exist.
- **Module docstring** (`agent_loader.py` lines 7–13) references seven sub-modules (`agent_registry.py`, `agent_cache.py`, `agent_validator.py`, `model_selector.py`, `legacy_support.py`, `async_loader.py`, `metrics_collector.py`) — **none of these files exist** at the paths implied by the docstring.
- **`get_agent_metadata()` bug**: Calls `self.registry.get_agent()` which returns `AgentMetadata` dataclass, then calls `.get()` on it (lines 358–387) — `AgentMetadata` has no `.get()` method; this will raise `AttributeError` if triggered.
- **`_analyze_task_complexity()`** (line 639) always returns hardcoded medium-complexity defaults and logs a warning that `TaskComplexityAnalyzer` is unavailable. This means dynamic model selection is never exercised despite the surrounding infrastructure.
- `load_agent_prompt_from_md()` (line 615) has a misleading name — its docstring says it loads from "JSON template" even though it now handles `.md` files; the name predates the format migration.

---

## 2. Frontmatter Validation

### WHAT

**File**: `src/claude_mpm/agents/frontmatter_validator.py`

`FrontmatterValidator` (line 44) validates and auto-corrects YAML frontmatter for `.md` agent files.

**Schema loading**: tries `src/claude_mpm/schemas/frontmatter_schema.json` (line 113–121). Falls back to a hardcoded field set if schema missing.

**Required fields** (from schema): `name`, `description`, `version`, `model`.

**Validated fields**:
- `name`: must match `^[a-z][a-z0-9_]*$` — auto-corrected (lowercased, hyphens→underscores, invalid chars stripped).
- `model`: normalized via `ModelTier.normalize()` to `opus | sonnet | haiku`. Full model version strings (e.g., `claude-3-5-sonnet-20241022`) are normalized to tier names.
- `tools`: parsed from string representation or JSON array; case-normalized against `TOOL_CORRECTIONS` dict.
- `version`, `base_version`: must be `\d+\.\d+\.\d+`; `v1.0.0` prefix stripped, two-part versions padded to three.
- `color`, `author`, `tags`, `max_tokens`, `temperature`, `resource_tier`, `category`.
- NEW: `collection_id` (format: `owner/repo-name`), `source_path`, `canonical_id` — auto-generated if `collection_id` present but `canonical_id` missing.

**`validate_and_correct()`** (line 150): non-mutating — returns `ValidationResult` with `corrected_frontmatter` and `field_corrections`.

**`correct_file()`** (line 668): writes corrections back to disk using `_apply_field_corrections()`, which does line-by-line regex replacement preserving YAML structure.

**Tool name validation** (lines 78–100): `VALID_TOOLS` set includes standard Claude Code tools plus `git`, `docker`, `kubectl`, `terraform`, `aws`, `gcloud`, `azure`. Unknown tools produce warnings, not errors.

### WHY

Auto-correction reduces manual frontmatter maintenance burden when agents are authored or migrated from legacy formats.

### DRIFT

- **CLAUDE.md** lists `agent_id`, `schema_version`, `capabilities`, `temperature`, `timeout` as MPM-proprietary fields. `FrontmatterValidator` validates `temperature` but does not validate `agent_id`, `schema_version`, `capabilities`, or `timeout` — these are accepted as `additionalProperties: true` by the schema but not enforced.
- `_validate_name_field()` (line 209) requires `^[a-z][a-z0-9_]*$` (underscores only), but `frontmatter_schema.json` allows `^[a-z][a-z0-9_-]*$` (hyphens and underscores). The validator is stricter than the schema — deployed agents with hyphenated names (e.g., `nestjs-engineer`) would fail name validation if processed through the validator.
- `VALID_TOOLS` does not include `Agent`, `Task`, `TodoWrite` — these appear in actual deployed frontmatter (`code-critic.md` uses them via the `skills` field pathway, not `tools`).

---

## 3. Agent Name Normalization

### WHAT

**File**: `src/claude_mpm/core/agent_name_normalizer.py`

`AgentNameNormalizer` provides class-level lookup tables:
- `CANONICAL_NAMES`: built dynamically from `AGENT_NAME_MAP` (static curated list in `agent_name_registry.py`) plus runtime scan of `.claude/agents/`.
- `ALIASES`: reverse mapping from aliases to canonical stems.
- `AGENT_COLORS`: per-agent color assignments.

Key methods:
- `normalize(name)`: returns display name (e.g., `"engineer"` → `"Engineer"`).
- `to_key(name)`: returns underscore-normalized key (e.g., `"Python Engineer"` → `"python_engineer"`).
- `to_todo_prefix(name)`: formats for todo output.
- `from_task_format(name)`: reverse mapping from task tool format.

`_build_canonical_names_dynamic()` (line 63): merges static map with runtime-discovered agents from `.claude/agents/`; static entries take priority for known agents.

**`get_agent_prompt()` normalization logic** (lines 841–881 in `agent_loader.py`): uses a multi-step cascade:
1. Exact match
2. `{name}_agent` suffix
3. Strip `_agent` suffix
4. Check normalizer ALIASES/CANONICAL_NAMES
5. Clean (lowercase, hyphens→underscores)

### WHY

Agent names arrive in many formats from user input, TodoWrite, and the Task tool. A centralised normalizer prevents per-call format handling.

### DRIFT

- `AGENT_NAME_MAP` in `agent_name_registry.py` is not examined in this research pass (file exists, referenced by normalizer). The dynamic scan of `.claude/agents/` means new custom agents become resolvable without code changes — but this is not documented in CLAUDE.md.
- The normalizer uses underscore keys (`python_engineer`) while `AGENT_NAME_MAP` uses hyphen stems (`python-engineer`). `_build_canonical_names_from_registry()` performs the conversion but this internal distinction is not documented.

---

## 4. agents_metadata.py — Static Capability Registry

### WHAT

**File**: `src/claude_mpm/agents/agents_metadata.py`

A static Python module containing hardcoded dictionaries for 14 agent types: `documentation`, `version_control`, `qa`, `api_qa`, `web_qa`, `research`, `ops`, `security`, `engineer`, `data_engineer`, `project_organizer`, `imagemagick`, `agentic_coder_optimizer`, `agent_manager`.

Each entry captures `name`, `version`, `type` (e.g., `"core_agent"`, `"optimization_agent"`, `"system_agent"`), `capabilities` (list of strings), `primary_interface`, and `performance_targets`.

All are aggregated in `ALL_AGENT_CONFIGS` dict (line 348).

### WHY

Intended as a registry for capability tracking and programmatic agent selection based on required capabilities.

### DRIFT

- There is no code in the repository that imports or calls `ALL_AGENT_CONFIGS` for agent discovery or dispatch. The module appears to be documentation in code form — it describes what agents should do but is not wired into loading, routing, or capability matching.
- The agent types listed here (`documentation_agent`, `version_control_agent`, `api_qa_agent`, `web_qa_agent`) do not correspond to any deployed `.md` files in `.claude/agents/` or any agents in the bundled set. They appear to be legacy aspirational capability definitions.
- `UnifiedAgentRegistry`, `AgentLoader`, `SystemAgentConfigManager` all define their own capability/metadata systems independently, creating four separate metadata representations with no shared source of truth.

---

## 5. Bundled Agent Set

### WHAT

**Directory**: `src/claude_mpm/agents/bundled/`

Contains exactly two agent definition files:
- `rust-engineer.md` — Rust language engineer agent
- `ticketing.md` — GitHub/JIRA/Linear issue management agent

Both use YAML frontmatter with `model`, `effort`, `name`, `description`, and `category` fields.

**`ticketing.md`** frontmatter fields: `model: haiku`, `effort: fast`, `name: Ticketing`, `description`, `toolchain: universal`, `category: mpm`, `version: 1.1.0`.

### WHY

The `bundled/` directory is the in-package source for agents that ship with the framework. They are deployed to `.claude/agents/` during the `mpm init` / agent deployment step.

### DRIFT

- **CLAUDE.md** references `src/claude_mpm/agents/bundled/` as the bundled agent location, but only two files exist there. The vast majority of deployed agents in `.claude/agents/` (38 total active files) originate from a different source — the external GitHub agents repository cached at `~/.claude-mpm/cache/agents/`.
- The `openrouter_code_reviewer.md` file exists at `src/claude_mpm/agents/openrouter_code_reviewer.md` (not in `bundled/`). Its frontmatter includes `provider: openrouter` and `provider_config` fields that are not documented in CLAUDE.md or validated by `FrontmatterValidator`.
- No README or manifest explains what belongs in `bundled/` vs. the external repo.

---

## 6. Deployed Agent Set (.claude/agents/)

### WHAT

**Directory**: `.claude/agents/` (at project root)

38 active `.md` agent files (non-backup) as of research date. Deployment state tracked in `.deployment-state.json`:
```json
{"version": "5.6.14+build.599", "agent_count": 44, "deployment_hash": "...", "deployed_at": 1768774611}
```

Active agents include: `agentic-coder-optimizer`, `aws-ops`, `clerk-ops`, `code-analyzer`, `code-critic`, `content`, `data-scientist`, `digitalocean-ops`, `imagemagick`, `mpm-agent-manager`, `mpm-skills-manager`, `nestjs-engineer`, `product-owner`, `project-organizer`, `real-user`, `tmux`, `visual-basic-engineer`, `web-ui-engineer`, plus others.

**Frontmatter field usage** (across sampled agents):
- Claude Code native: `name`, `description`, `model`, `effort`, `permissionMode`, `maxTurns`, `memory`, `color`, `skills` (list of skill names)
- MPM extensions: `agent_id`, `agent_type`, `version`, `initialPrompt`
- Absent: `schema_version`, `resource_tier`, `timeout`, `capabilities`, `temperature` — despite CLAUDE.md listing these as MPM-proprietary fields in use

**`initialPrompt`**: present in at least 5 deployed agents (`code-critic`, `agentic-coder-optimizer`, `clerk-ops`, `digitalocean-ops`, `data-scientist`). Verified in `frontmatter_schema.json` as valid (line with `"initialPrompt": {"type": "string", "minLength": 1, "maxLength": 500}`). Not listed in CLAUDE.md's MPM-proprietary field list.

**Unused agents**: `.claude/agents/unused/` contains 15+ retired agents timestamped `20260120_015729`, including `engineer`, `data-engineer`, `python-engineer`, `typescript-engineer`, `version-control`, `memory-manager-agent`. These are not discovered by `UnifiedAgentRegistry` (the `unused` path is not in discovery paths).

### WHY

`.claude/agents/` is the Claude Code native agent discovery location. MPM populates it at deploy time so Claude Code finds agents without MPM-specific wiring.

### DRIFT

- **CLAUDE.md** lists `schema_version`, `resource_tier`, `timeout`, `capabilities`, `temperature` as MPM-proprietary frontmatter fields in active use. Inspection of deployed agents finds these fields absent in all sampled agents. They may exist in legacy JSON-format agents in the external cache.
- **`initialPrompt`** is used in deployed agents and documented in `frontmatter_schema.json` and `agent_template_builder.py` (with per-agent and per-type configuration tables), but is not mentioned in CLAUDE.md's frontmatter field lists.
- The `skills` frontmatter field in deployed agents (e.g., `code-critic.md` lists `code-review-standards`, `code-production-process`, etc.) is a Claude Code native field for referencing installed skills from `.claude/skills/`. CLAUDE.md lists `skills` as a Claude Code native field but does not explain how the values are populated or what names are valid.

---

## 7. Agent Assembly Pipeline

### WHAT

**Document**: `docs/developer/AGENT_ASSEMBLY_PIPELINE.md` (version 6.5.4, last_updated 2025-06-01, status: current)

**Key components verified to exist**:
- `SystemInstructionsDeployer` at `src/claude_mpm/services/agents/deployment/system_instructions_deployer.py` (line 26) — confirmed exists, `deploy_system_instructions()` at line 174, writes to `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md`.
- `AgentTemplateBuilder` at `src/claude_mpm/services/agents/deployment/agent_template_builder.py` (line 118) — confirmed exists, `build_agent_markdown()` at line 436.

**PM Pipeline** (verified):
- Four source blocks merged: `PM_INSTRUCTIONS.md`, `AGENT_DELEGATION.md`, `WORKFLOW.md`, `MEMORY.md`.
- Three-level resolution: user override (`~/.claude-mpm/`) → project override (`.claude-mpm/`) → system default (`src/claude_mpm/agents/`).
- `WORKFLOW.md` lazy-load: inline override if present, else `WORKFLOW_SYSTEM_REFERENCE` stub. File confirmed at `src/claude_mpm/core/framework/loaders/workflow_constants.py`.
- Output file: `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md`.

**Subagent Pipeline** (verified):
- `AgentTemplateBuilder.build_agent_markdown()` (line 436) builds per-agent `.md` with YAML frontmatter.
- Default tools if none specified: `["Read", "Write", "Edit", "Grep", "Glob", "Bash"]` (line 148).
- `_discover_base_agent_templates()` (line 179) walks up from agent file, collecting `BASE-AGENT.md` or `BASE_AGENT.md` (both forms checked, line 228).
- Fallback to `_load_base_agent_instructions()` (line 364, marked DEPRECATED) if no hierarchical templates found — loads `BASE_{TYPE}.md`.
- Content parts joined with `\n\n---\n\n` separator (line 789).
- Memory instructions block auto-appended if neither `"memory-update"` nor `"Remember"` appear in content (lines 791–806).

**`initialPrompt` injection**: `get_initial_prompt_for_agent()` (lines ~95–114 in `agent_template_builder.py`) consults `INITIAL_PROMPT_BY_NAME` and `INITIAL_PROMPT_BY_TYPE` lookup tables, with `INITIAL_PROMPT_EXCLUDED_NAMES` blocklist. This field is injected at deploy time, not authored in source templates.

### WHY

Separation of build-time vs. runtime assembly ensures agents are lightweight at invocation — no dynamic template merging on each call.

### DRIFT

- The pipeline document is substantially accurate against current code. The primary gap is that it does not mention the `initialPrompt` injection mechanism, which is a non-trivial deploy-time feature.
- `base_agent.json` is referenced in `BASE_AGENT.md` (line 16) as "removed" legacy bloat. A `base_agent.json` file does exist in `.claude/worktrees/agent-a0c29fcf.../src/claude_mpm/agents/base_agent.json` (a worktree artefact), not in the main tree. The claim of removal is accurate for the main codebase.
- The document describes template discovery from `~/.claude-mpm/cache/agents/` and project locations. No mention is made of the `src/claude_mpm/agents/bundled/` directory as a source of template files — which is where `ticketing.md` and `rust-engineer.md` live.

---

## 8. BASE Template System

### WHAT

Three BASE template files exist in `src/claude_mpm/agents/`:

**`BASE_AGENT.md`**: Root-level base. Contains git workflow standards (conventional commits, atomic commits, issue references), memory routing description, handoff protocol, proactive code quality rules (search-before-create, mimic patterns, suggest improvements), and memory update JSON format. Explicitly marked as "BUILD INPUT" in an HTML comment (line 3–19). ~50 lines.

**`BASE_ENGINEER.md`**: Engineer-specific base. Contains code quality standards.

**`BASE_PM.md`**: PM-specific base. Contains non-overridable PM rules (marked "Cannot be overridden").

**Usage**:
- `BASE_AGENT.md` is the primary base composed into all subagents via hierarchical discovery (`BASE-AGENT.md` or `BASE_AGENT.md` variants, `agent_template_builder.py` line 228).
- `BASE_ENGINEER.md` and `BASE_PM.md` are used as **legacy fallback** only when no hierarchical `BASE-AGENT.md` found (`_load_base_agent_instructions()` at line 364, marked DEPRECATED).

**Hierarchical discovery flow** (from `_discover_base_agent_templates()`, line 179):
- Walks up from agent file location to repo root (max 10 levels).
- Accepts `BASE-AGENT.md` (hyphen, external repos) or `BASE_AGENT.md` (underscore, framework).
- Stops at git repository root after finding `BASE-AGENT.md`.
- Returns list ordered closest-to-farthest from agent file.

### WHY

Hierarchical composition allows per-domain or per-subdomain instruction specialisation without duplicating common rules.

### DRIFT

- **CLAUDE.md** mentions `BASE_AGENT.md / BASE_ENGINEER.md / BASE_PM.md` as part of the bundled agent set. In practice, only `BASE_AGENT.md` is actively used in the hierarchical composition pipeline; `BASE_ENGINEER.md` and `BASE_PM.md` are legacy fallbacks.
- The `BASE_PM.md` includes a claim of "non-overridable rules" but this is not enforced mechanically — it is merely appended as content and can be overridden by a user-level `PM_INSTRUCTIONS.md` override.
- The content in `BASE_AGENT.md` (git standards, memory routing, handoff protocol, code quality) partially overlaps with instructions in `CLAUDE.md` itself (which is injected into the PM's context by Claude Code). This creates potential instruction duplication for the PM agent.

---

## 9. Skills System — SkillsRegistry (registry.py)

### WHAT

**File**: `src/claude_mpm/skills/registry.py`

`SkillsRegistry` (line 156) is the **legacy flat-file skill registry**. It loads skills from:
1. `src/claude_mpm/skills/bundled/*.md` (flat `.md` files at root of `bundled/`) via `_load_bundled_skills()` (line 332) — uses `bundled_dir.glob("*.md")`.
2. `~/.claude/skills/*.md` — user-level overrides.
3. `.claude/skills/*.md` — project-level overrides.

Skill source priority: project > user > bundled.

**`Skill` dataclass** (line 16): supports `agentskills.io` spec fields (`name`, `description`, `license`, `compatibility`, `metadata`, `allowed_tools`) plus internal fields (`path`, `content`, `source`, `version`, `skill_id`, `agent_types`, `tags`) and claude-mpm extensions (`category`, `toolchain`, `progressive_disclosure`, `user_invocable`, `when_to_use`).

**Backward compatibility migration** (`_apply_backward_compatibility()`, line 195): auto-migrates `version`, `author`, `updated`, `tags` from top-level to `metadata` block; parses `allowed-tools` from space-delimited string; sets default `compatibility: claude-code`.

The `get_registry()` function (line ~490) returns a module-level singleton.

### WHY

The flat `.md` format predates the directory-based `SKILL.md` format. The registry maintains backward compatibility while the newer directory structure becomes standard.

### DRIFT

- This registry only discovers **flat `.md` files** in `bundled/`. The 57 directory-based skills (e.g., `debugging/systematic-debugging/SKILL.md`) are **not discovered by this registry**. They are discovered by `SkillsService.discover_bundled_skills()` (a separate component).
- There are currently 20 flat `.md` skills in `bundled/` root and 57 `SKILL.md` files in subdirectories — creating **two parallel skill populations** with separate discovery paths and different loading mechanisms. No documentation acknowledges this split.
- The `SkillsRegistry` stores skills by `stem` name (filename without extension), while `SkillsService` stores them by `skill_dir.name` (directory name). If a flat `systematic-debugging.md` and a `debugging/systematic-debugging/SKILL.md` both exist, they could collide or diverge.

---

## 10. Skills System — SkillsService (skills_service.py)

### WHAT

**File**: `src/claude_mpm/skills/skills_service.py`

`SkillsService` (line 32) manages **directory-based** (`SKILL.md`) skills.

**Paths**:
- `bundled_skills_path`: `src/claude_mpm/skills/bundled/` (set at line 63)
- `deployed_skills_path`: `.claude/skills/` (relative to project root, line 64)
- `registry_path`: `{project_root}/../../../config/skills_registry.yaml` (line 66–69) — resolves to `<repo_root>/config/skills_registry.yaml`

**`discover_bundled_skills()`** (line 158): iterates `bundled/` → category subdirs → skill subdirs → `SKILL.md`. Also scans `~/.claude/plugins/cache/Superpowers/skills/` if present (lines 210–235).

**Superpowers integration**: `SkillsService` optionally pulls in skills from the Claude Superpowers plugin cache — undocumented behaviour.

**`deploy_bundled_skills()`** (line 280): copies skill directories from `bundled/` to `.claude/skills/` maintaining directory structure. Targets `SKILL.md` files.

**`get_skills_for_agent(agent_id)`** (line 358): reads from `self.registry["agent_skills"][agent_id]` — requires `config/skills_registry.yaml` to be populated.

**`_load_registry()`** (line 107): returns empty dict if `config/skills_registry.yaml` does not exist, with a warning. The `config/` directory **does not exist** in the repository at research date.

### WHY

Directory-based skills allow multi-file skill packages (SKILL.md + reference docs + scripts). `SkillsService` manages the newer structure.

### DRIFT

- `config/skills_registry.yaml` is referenced by `SkillsService` as the source of truth for agent-to-skill mappings, but the file does not exist in the repository. This means `get_skills_for_agent()` always returns empty results in a fresh clone, silently.
- `discover_bundled_skills()` iterates `category_dir → skill_dir → SKILL.md`, which means flat `.md` files at the root of `bundled/` are silently skipped. This is the inverse problem from `SkillsRegistry` — each discovers half the skills.
- The `registry_path` computation (line 66–69) navigates four levels up from `skills_service.py` then into `config/`. This works from the installed package layout but produces a path outside the repo root in development setups where `__file__` is under `src/`. The result is `<repo>/config/skills_registry.yaml`, which does not exist.

---

## 11. Skills System — SkillManager (skill_manager.py)

### WHAT

**File**: `src/claude_mpm/skills/skill_manager.py`

`SkillManager` (line 17) is the integration layer between skills and agents. It:
- At init, loads skill mappings from JSON templates in `src/claude_mpm/agents/templates/*.json` (lines 38–63).
- No JSON files exist at that path (the `templates/` directory contains only `.md` files: circuit-breakers, pm-examples, ticketing-examples, etc.). This means `_load_agent_mappings()` finds no files and `agent_skill_mapping` is always empty after init.
- `get_agent_skills(agent_type)` (line 282): looks up `agent_skill_mapping`, then falls back to `normalize_agent_id`. Since the mapping is always empty, this returns empty lists.
- `_get_pm_skills(project_dir)` (line 65): scans `.claude/skills/` for `SKILL.md` directories — this is the active path for PM skills.
- `get_migration_skills()` (line 212): scans `.claude/skills/`, `~/.claude-mpm/skills/`, `~/.claude/skills/` for migration-type skills.

**PM skill format** (`_load_pm_skill()`, line 100): parses YAML frontmatter; recognizes `type: migration` for extended migration skill fields (`state_key`, `services`, `check_commands`, `health_checks`, `system_requirements`, `install_commands`, `verify_commands`, `post_install_notes`).

### WHY

`SkillManager` was designed to load agent-skill mappings from JSON agent templates (the old format). PM skills (skills used by the PM itself) are loaded dynamically from `.claude/skills/`.

### DRIFT

- `src/claude_mpm/agents/templates/` contains only `.md` files (workflow examples, PM examples, circuit-breaker templates). No JSON agent templates exist there. `_load_agent_mappings()` therefore always produces an empty mapping, effectively disabling the skill→agent association feature for all non-PM agents.
- `SkillManager.get_agent_skills()` always returns empty for any non-PM agent. Any code calling this for, say, `engineer` agent type gets no skills. The `skills` field in deployed agent frontmatter is authored manually (not populated by `SkillManager`).
- Three separate skill-to-agent resolution paths exist (`SkillsRegistry.get_skill()`, `SkillsService.get_skills_for_agent()`, `SkillManager.get_agent_skills()`) with no documented precedence or composition rule.

---

## 12. Skills System — AgentSkillsInjector

### WHAT

**File**: `src/claude_mpm/skills/agent_skills_injector.py`

`AgentSkillsInjector` (line 29) provides methods to inject skill references into agent templates:
- `enhance_agent_template(template_path)` (line 63): reads JSON template, calls `skills_service.get_skills_for_agent(agent_id)`, adds `skills` field to the template dict.
- `generate_frontmatter_with_skills(agent_config)` (line 121): generates YAML frontmatter including `skills`.
- `inject_skills_documentation(agent_content, skills)` (line 177): appends skill documentation to agent markdown body.
- `inject_complete_skills(agent_id, template_content)` (line 228): combines frontmatter generation and documentation injection.

The injector depends on `SkillsService.get_skills_for_agent()`, which always returns empty (due to missing `config/skills_registry.yaml`).

### WHY

Designed to enable dynamic skill injection at deploy time without modifying source template files.

### DRIFT

- The injector is architecturally sound but inoperative in practice because its dependency (`SkillsService.get_skills_for_agent()`) returns empty results.
- The `enhance_agent_template()` method reads **JSON** templates (`json.load()` at line 91) — consistent with the old format. The actual agents are now `.md` files, so this method cannot process current agent definitions.
- Skills in deployed agents (e.g., `code-critic.md` has `skills: [code-review-standards, ...]`) are authored directly in the source `.md` frontmatter, not injected by `AgentSkillsInjector`.

---

## 13. Frontmatter Schema

### WHAT

Two schema files exist:

**`src/claude_mpm/schemas/frontmatter_schema.json`**: Title "Agent Frontmatter Schema". Required fields: `name`, `description`, `version`, `model`. Allows `additionalProperties: true`. Includes `initialPrompt` field definition. Name pattern: `^[a-z][a-z0-9_-]*$` (hyphens allowed).

**`src/claude_mpm/schemas/agent_schema.json`**: Title "Claude MPM Agent Schema", version 1.3.0. Required fields: `schema_version`, `agent_id`, `agent_version`, `agent_type`, `metadata`, `capabilities`, `instructions`. This is the **legacy JSON agent format schema**. `agent_type` enum: `base`, `engineer`, `qa`, `documentation`, `research`, `security`, `ops`, `data_engineer`, `version_control`, `system`, `refactoring`, `memory_manager`.

**`FrontmatterValidator`** loads `frontmatter_schema.json` (line 113). `agent_schema.json` is used by `AgentValidator` in `src/claude_mpm/validation/agent_validator.py` (not part of this research scope but referenced by `async_agent_loader.py`).

### WHY

Two schemas exist because the agent format migrated from JSON (`agent_schema.json` structure) to `.md` with YAML frontmatter (`frontmatter_schema.json` structure).

### DRIFT

- `frontmatter_schema.json` allows hyphenated names (`^[a-z][a-z0-9_-]*$`) but `FrontmatterValidator._validate_name_field()` only allows underscores (`^[a-z][a-z0-9_]*$`). Deployed agents with hyphenated names (`nestjs-engineer`, `code-critic`) would fail validator name checks.
- `agent_schema.json` version 1.3.0 still exists and references `memory_manager` as a valid `agent_type` — there is no `memory-manager` agent in the active deployed set.
- `initialPrompt` is in `frontmatter_schema.json` but absent from `FrontmatterValidator.all_valid_fields` fallback set (line 128–148) — only reached if the schema file fails to load.

---

## 14. Summary Drift Matrix

| Component | Documented Claim | Actual Behaviour | Severity |
|-----------|-----------------|------------------|----------|
| `agent_loader.py` sub-modules | Module docstring lists 7 sub-modules (agent_registry.py, agent_cache.py, etc.) | None of these files exist; real delegation is to `unified_agent_registry.py` | Medium |
| `get_agent_metadata()` bug | Should return metadata dict | Calls `.get()` on `AgentMetadata` dataclass (no `.get()` method) — latent `AttributeError` | High |
| `_analyze_task_complexity()` | Dynamic model selection based on task | Always returns hardcoded medium-complexity defaults; `TaskComplexityAnalyzer` permanently unavailable | Medium |
| CLAUDE.md MPM-proprietary fields | Lists `schema_version`, `resource_tier`, `timeout`, `capabilities`, `temperature` as active fields | Not present in any sampled deployed agent; `initialPrompt` used but not listed | Medium |
| `config/skills_registry.yaml` | `SkillsService` claims this as agent-skill mapping source | File does not exist; `get_skills_for_agent()` always returns empty | High |
| `templates/*.json` for skill mapping | `SkillManager` loads from `agents/templates/*.json` | Directory contains only `.md` files; `agent_skill_mapping` always empty | High |
| Dual skill discovery paths | No documentation | `SkillsRegistry` reads flat `bundled/*.md`; `SkillsService` reads `bundled/*/SKILL.md`; 20 flat vs 57 directory skills, no overlap handling | High |
| `AgentSkillsInjector` | Injects skills into agents at deploy time | Inoperative: depends on missing registry file; processes JSON templates that no longer exist | High |
| `agents_metadata.py` | Describes 14 agent types with capabilities | Not imported by any runtime code; describes agent types not present in deployed set | Low |
| FrontmatterValidator name regex | `^[a-z][a-z0-9_]*$` | Schema allows `^[a-z][a-z0-9_-]*$`; deployed agents with hyphens would fail validation | Medium |
| `BASE_ENGINEER.md`, `BASE_PM.md` | Active base templates | Legacy fallback only; `_load_base_agent_instructions()` explicitly marked DEPRECATED | Low |
| `initialPrompt` field | Not in CLAUDE.md field lists | Used in 5+ deployed agents; documented in `frontmatter_schema.json`; injected at build time by `agent_template_builder.py` | Low |
| Bundled agents in `src/agents/bundled/` | Implies comprehensive bundled set | Only 2 files (`rust-engineer.md`, `ticketing.md`); most deployed agents from external GitHub cache | Low |

---

*Research captured by: Research Agent*  
*Evidence sources: direct file inspection at specified line numbers*
