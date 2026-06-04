# Skills Subsystem — Spec-Linked Documentation

**Status:** Active
**Version:** v1
**Subsystem:** SKILLS

This document specifies the observable behavior of the seven coherent areas that
together constitute the claude-mpm Skills subsystem.  Each section carries a stable
spec ID, a behavior contract (WHAT), a rationale (WHY), and an implementing-modules
table.  All sections are **Active**, with References backfilled into their
implementing modules; they describe actual, verified behavior grounded in direct
code inspection against `src/claude_mpm/skills/` and the research document
`docs/specs/research/02-agents-skills.md`.

The **Known Drift** section at the end documents inoperative or misaligned
behavior discovered during research.

---

## Table of Contents

| ID | Section | Primary module |
|----|---------|----------------|
| SPEC-SKILLS-01~1 | [SkillsRegistry — flat-file skill discovery](#skillsregistry--flat-file-skill-discovery-spec-skills-011) | `claude_mpm.skills.registry` |
| SPEC-SKILLS-02~1 | [SkillsService — directory-based skill discovery](#skillsservice--directory-based-skill-discovery-spec-skills-021) | `claude_mpm.skills.skills_service` |
| SPEC-SKILLS-03~1 | [SkillDiscoveryService — remote/cache skill discovery](#skilldiscoveryservice--remotecache-skill-discovery-spec-skills-031) | `claude_mpm.services.skills.skill_discovery_service` |
| SPEC-SKILLS-04~1 | [Skill frontmatter schema and required keys](#skill-frontmatter-schema-and-required-keys-spec-skills-041) | `claude_mpm.skills.registry`, `claude_mpm.services.skills.skill_discovery_service` |
| SPEC-SKILLS-05~1 | [Bundled skills layout](#bundled-skills-layout-spec-skills-051) | `claude_mpm.skills.bundled` (package) |
| SPEC-SKILLS-06~1 | [SkillManager — agent-to-skill mapping](#skillmanager--agent-to-skill-mapping-spec-skills-061) | `claude_mpm.skills.skill_manager` |
| SPEC-SKILLS-07~1 | [AgentSkillsInjector — graceful-noop behavior](#agentskillsinjector--graceful-noop-behavior-spec-skills-071) | `claude_mpm.skills.agent_skills_injector` |

---

## SkillsRegistry — flat-file skill discovery {#SPEC-SKILLS-01~1}

**ID:** SPEC-SKILLS-01~1
**Status:** Active

### Behavior Contract (WHAT)

- **Inputs:** None at construction time.  Discovery paths are resolved from the
  module's own `__file__` location and the current working directory.

- **Outputs:** A populated `skills` dict (keyed by skill stem name) accessible
  via `get_registry()`, which returns a module-level singleton.

- **Discovery sources and priority order (highest to lowest):**
  1. `.claude/skills/*.md` — project-level overrides (cwd-relative).
  2. `~/.claude/skills/*.md` — user-level overrides.
  3. `src/claude_mpm/skills/bundled/*.md` — flat `.md` files at the **root** of
     the `bundled/` package directory (not in subdirectories).

- **What is discovered:**
  - Only files matching `bundled/*.md` (single glob level, `bundled_dir.glob("*.md")`).
  - As of current code: 21 flat `.md` files at the `bundled/` root.
  - Directory-based skills (`bundled/<category>/<name>/SKILL.md`) are **not**
    discovered by this registry.

- **Skill representation:** Each discovered file is parsed into a `Skill` dataclass
  carrying: `name`, `description`, `license`, `compatibility`, `metadata`,
  `allowed_tools`, `path`, `content`, `source`, `version`, `skill_id`,
  `agent_types`, `tags`, `category`, `toolchain`, `progressive_disclosure`,
  `user_invocable`, `when_to_use`.

- **Backward-compatibility migration** (`_apply_backward_compatibility`):
  Auto-migrates `version`, `author`, `updated`, `tags` from top-level frontmatter
  keys to a nested `metadata` block.  Sets default `compatibility: claude-code`
  if absent.  Parses `allowed-tools` from a space-delimited string when present.

- **Singleton access:** `get_registry()` returns a cached module-level instance;
  a new `SkillsRegistry()` is constructed on first call.

- **Error conditions:** Missing `bundled/` directory logs a warning and returns
  empty skills.  YAML parse failures log a warning per file and skip that file.

### Rationale (WHY)

The flat `.md` format predates the directory-based `SKILL.md` convention.
`SkillsRegistry` exists to preserve backward compatibility with skills authored
before the directory layout was introduced, and to serve as the primary lookup
for `SkillManager.get_agent_skills()` (which delegates to `get_registry()`).
The singleton pattern prevents repeated filesystem scans per process.

The three-tier priority (project > user > bundled) follows the same precedence
model used by the agent discovery system, allowing per-project and per-user
skill overrides without modifying the package.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.skills.registry` | `SkillsRegistry` class; `Skill` dataclass; `get_registry()` singleton accessor |

---

## SkillsService — directory-based skill discovery {#SPEC-SKILLS-02~1}

**ID:** SPEC-SKILLS-02~1
**Status:** Active

### Behavior Contract (WHAT)

- **Inputs:** None at construction time.  Paths are resolved from the module's
  `__file__` location and `Path.cwd()`.

- **Outputs:** Skill metadata dicts (not `Skill` dataclasses) returned from
  `discover_bundled_skills()` and related methods.

- **Discovery target — `discover_bundled_skills()`:**
  Iterates `bundled_skills_path` (`src/claude_mpm/skills/bundled/`) to find
  two-level paths: `<category_dir>/<skill_dir>/SKILL.md`.  Flat `.md` files at
  the root of `bundled/` are silently skipped by this method (only directories are
  iterated at the first level).

  As of current code: discovers 58 directory-based skills.

- **Optional Superpowers integration:**
  After scanning bundled skills, `discover_bundled_skills()` also scans
  `~/.claude/plugins/cache/Superpowers/skills/` if that path exists, treating
  each subdirectory containing `SKILL.md` as an additional skill.  Skills from
  this source are assigned category `"superpowers"`.  Bundled skills take
  precedence on name conflicts (bundled names are excluded from the Superpowers
  scan set).

- **Deployment — `deploy_bundled_skills()`:**
  Copies skill directories from `bundled/` to `.claude/skills/` in the project
  root, preserving directory structure.  Targets `SKILL.md` files within each
  skill directory.

- **Agent-skill lookup — `get_skills_for_agent(agent_id)`:**
  Reads from `self.registry["agent_skills"][agent_id]`.  Returns an empty list
  when `config/skills_registry.yaml` does not exist (the file is missing in the
  current repository; see Known Drift).

- **Registry loading — `_load_registry()`:**
  Reads `config/skills_registry.yaml` relative to the package root (four directory
  levels up from `skills_service.py`).  Returns an empty dict with a warning if
  the file is absent.

- **Version comparison — `check_for_updates()`:**
  Compares `version` fields from deployed `.claude/skills/*/SKILL.md` against
  bundled counterparts.  Returns dicts of updates available, up to date, and
  errors.

- **Error conditions:** All per-skill errors log a warning and continue;
  the method does not abort on individual file failures.

### Rationale (WHY)

Directory-based skills (`SKILL.md` inside a named directory) allow multi-file
skill packages: the directory can contain `SKILL.md`, reference documents,
scripts, and assets.  `SkillsService` manages this newer, richer structure
separately from `SkillsRegistry` to avoid complicating the flat-file loader
with directory traversal logic.

The Superpowers integration is opt-in (gated on path existence) to allow
claude-mpm to surface skills installed by the Claude Superpowers plugin without
creating a hard dependency on it.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.skills.skills_service` | `SkillsService` class; bundled discovery, deployment, version comparison, registry-based agent lookup |

---

## SkillDiscoveryService — remote/cache skill discovery {#SPEC-SKILLS-03~1}

**ID:** SPEC-SKILLS-03~1
**Status:** Active

### Behavior Contract (WHAT)

- **Inputs:**
  - `skills_dir: Path` — directory to scan, typically a Git cache directory
    such as `~/.claude-mpm/cache/skills/system/`.

- **Outputs:** `discover_skills()` returns a list of skill dicts, each containing:
  `skill_id`, `name`, `description`, `skill_version`, `tags`, `agent_types`,
  `content`, `source_file`, `resources`, `deployment_name`, `relative_path`.

- **Discovery pattern:**
  - Scans `skills_dir` recursively for `SKILL.md` files (`rglob("SKILL.md")`).
  - Also scans the top level of `skills_dir` for legacy flat `*.md` files,
    excluding known documentation file names (`readme.md`, `claude.md`,
    `contributing.md`, `changelog.md`, `license.md`, `authors.md`,
    `code_of_conduct.md`, `skill.md`).
  - Files that cannot be parsed or are missing required fields (`name`,
    `description`) are skipped with a warning log.

- **Deployment name calculation:**
  For nested structures, the deployment name is derived by joining path components
  with hyphens (e.g., `collaboration/dispatching-parallel-agents/SKILL.md` →
  deployment name `collaboration-dispatching-parallel-agents`).  Collision
  detection logs a warning if two skill files would produce the same deployment
  name.

- **Required fields:** `name` and `description` must be present in frontmatter;
  absence causes the file to be skipped.

- **`skill_version` field:** `discover_skills()` reads `skill_version` from
  frontmatter with a default of `"1.0.0"` when absent.

- **Error conditions:** Missing or unreadable `skills_dir` returns an empty list.
  Per-file parse errors log at warning or debug level (debug for documentation
  files) and continue.

### Rationale (WHY)

`SkillDiscoveryService` is scoped to a single directory and has no knowledge of
Git operations, caching, or deployment.  This single-responsibility boundary
allows `GitSkillSourceManager` (which handles downloading, ETag caching, and
multi-source coordination) to compose `SkillDiscoveryService` after each sync
without duplicating parsing logic.

The flat-legacy-file fallback in `discover_skills()` preserves backward
compatibility with skill repositories that predated the directory-based
`SKILL.md` convention.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.services.skills.skill_discovery_service` | `SkillDiscoveryService` class; `discover_skills()`, `_parse_skill_file()`, `_calculate_deployment_name()` |
| `claude_mpm.services.skills.git_skill_source_manager` | Composes `SkillDiscoveryService` after each Git sync; handles caching and multi-source coordination |
| `claude_mpm.cli.commands.skill_source` | Instantiates `SkillDiscoveryService` for the `skill-source` CLI command |

---

## Skill frontmatter schema and required keys {#SPEC-SKILLS-04~1}

**ID:** SPEC-SKILLS-04~1
**Status:** Active

### Behavior Contract (WHAT)

The skills subsystem does not enforce a single unified schema across all discovery
paths.  Two parsers with distinct required-field sets exist in parallel:

**Parser A — `SkillsRegistry._parse_skill_frontmatter()` (flat `.md` skills):**
- No fields are formally required at the parser level; missing or empty frontmatter
  produces an empty dict rather than an error.
- The `Skill` dataclass uses `name` and `description` from frontmatter; both
  default to empty string if absent.
- Optional recognized fields: `license`, `compatibility`, `metadata`,
  `allowed_tools`, `version`, `skill_id`, `agent_types`, `tags`, `category`,
  `toolchain`, `progressive_disclosure`, `user_invocable`, `when_to_use`.

**Parser B — `SkillDiscoveryService._parse_skill_file()` (directory-based `SKILL.md`):**
- **Required:** `name` and `description` must both be present; absence causes the
  skill to be skipped.
- `skill_version` is read with a default of `"1.0.0"` when absent.
- Optional: `tags`, `agent_types`.

**Observed inconsistency in version key naming:**
- The 21 flat bundled `.md` files use the key `version` (not `skill_version`).
- `SkillDiscoveryService` reads the key `skill_version`.
- The 58 directory-based bundled `SKILL.md` files, inspected at the root of the
  bundled package, use the key `version` (not `skill_version`).
- Consequence: when `SkillDiscoveryService` discovers the bundled directory-based
  skills, `skill_version` is not found in frontmatter and defaults to `"1.0.0"`
  for all of them, even if they carry an explicit `version` field.

**`SkillsService._parse_skill_metadata()` (used by `discover_bundled_skills()`):**
- Line-based extraction (not full YAML parse); reads `version:` lines.
- Returns the `version` field value, not `skill_version`.

**Validation in `SkillsService.validate_skill_directory()`:**
- Required fields verified: `name`, `description`, `version`, `category` (the
  last two are required by the 16-rule validator but not by `_parse_skill_file()`).

- **Error conditions:** Validation failures produce a list of error strings; the
  method returns `(False, errors)` but does not raise.

### Rationale (WHY)

The dual-parser situation exists because flat skills and directory-based skills
evolved separately, with `SkillsRegistry` predating `SkillDiscoveryService`.
The `skill_version` key was introduced in `SkillDiscoveryService` to distinguish
version metadata from the `version` field that the agentskills.io spec uses for
a different purpose (compatibility version, not skill content version).  The
inconsistency across bundled files is a documentation/authoring gap, not an
intentional design decision.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.skills.registry` | Parser A: YAML frontmatter parsing for flat `.md` skills |
| `claude_mpm.services.skills.skill_discovery_service` | Parser B: frontmatter parsing for directory-based `SKILL.md` |
| `claude_mpm.skills.skills_service` | Line-based metadata extraction for `discover_bundled_skills()`; 16-rule directory validator |

---

## Bundled skills layout {#SPEC-SKILLS-05~1}

**ID:** SPEC-SKILLS-05~1
**Status:** Active

### Behavior Contract (WHAT)

The `src/claude_mpm/skills/bundled/` directory contains two physically distinct
populations of skills that are discovered by separate mechanisms:

**Population 1 — flat `.md` files (root of `bundled/`):**
- 21 files directly under `bundled/` (e.g., `code-review.md`,
  `systematic-debugging.md`, `test-driven-development.md`).
- Discovered exclusively by `SkillsRegistry._load_bundled_skills()` via
  `bundled_dir.glob("*.md")`.
- Format: single-file Markdown with YAML frontmatter at top.

**Population 2 — directory-based skills (`bundled/<category>/<name>/SKILL.md`):**
- 58 skill directories organized under category subdirectories
  (e.g., `bundled/pm/mpm-status/SKILL.md`,
  `bundled/debugging/systematic-debugging/SKILL.md`,
  `bundled/collaboration/brainstorming/SKILL.md`).
- Discovered exclusively by `SkillsService.discover_bundled_skills()` via
  two-level directory iteration.
- Format: `SKILL.md` at the root of the skill directory; optional companion files
  (`references/`, `scripts/`, `assets/`) in the same directory.

**Category subdirectories present as of current code:**
`collaboration`, `debugging`, `infrastructure`, `main`, `pm`, `php`, `react`,
`rust`, `tauri`, `testing`, `toolchains`, `universal`.

**Naming collision risk:**
Both populations include a `systematic-debugging` skill (flat:
`systematic-debugging.md`; directory: `debugging/systematic-debugging/SKILL.md`).
No deduplication or collision detection operates across the two populations because
they are discovered by separate services.

**Deployment target:**
`SkillsService.deploy_bundled_skills()` copies directory-based skills to
`.claude/skills/<name>/SKILL.md` in the project root.  Flat `.md` skills are not
deployed by this method.

### Rationale (WHY)

The two-population structure arose from incremental evolution: flat `.md` files
were the original format; directory-based `SKILL.md` files were introduced later
to support multi-file skill packages.  The flat files were not removed because they
continue to be served by `SkillsRegistry` (which is still in use by `SkillManager`)
and because migrating them to directory format was deferred.

The category subdirectory layout (e.g., `pm/`, `debugging/`, `testing/`) groups
related skills for filesystem browsability and allows `SkillsService` to expose
the category name without embedding it in every `SKILL.md` frontmatter.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.skills.bundled` | Package directory; contains both flat `.md` files and category subdirectories |
| `claude_mpm.skills.registry` | Discovers Population 1 (flat `.md`) |
| `claude_mpm.skills.skills_service` | Discovers and deploys Population 2 (directory-based `SKILL.md`) |

---

## SkillManager — agent-to-skill mapping {#SPEC-SKILLS-06~1}

**ID:** SPEC-SKILLS-06~1
**Status:** Active

### Behavior Contract (WHAT)

- **Inputs:** None at construction time.

- **Outputs:**
  - `get_agent_skills(agent_type)` returns a list of skill names for the given
    agent type.
  - `_get_pm_skills(project_dir)` returns a list of PM skill dicts loaded from
    `.claude/skills/` in the project directory.
  - `get_migration_skills()` returns migration-type skills from `.claude/skills/`,
    `~/.claude-mpm/skills/`, and `~/.claude/skills/`.

- **Agent-to-skill mapping — `_load_agent_mappings()`:**
  At init, `SkillManager` scans `src/claude_mpm/agents/templates/*.json` for files
  with a `skills` field.  The `templates/` directory currently contains **only
  `.md` files** (no `.json` files exist there).  Therefore `_load_agent_mappings()`
  finds no files and `agent_skill_mapping` is always an empty dict after init.

- **Consequence of empty mapping:**
  `get_agent_skills(agent_type)` looks up `agent_skill_mapping`, then falls back
  to `normalize_agent_id`.  Since the mapping is always empty, this method returns
  an empty list for every non-PM agent type.

- **PM skills:**
  `_get_pm_skills()` scans `.claude/skills/` for subdirectories containing
  `SKILL.md`.  This is the only code path in `SkillManager` that returns
  non-empty results in a normal installation.

- **PM skill format — `_load_pm_skill()`:**
  Parses YAML frontmatter from `SKILL.md`.  Skills with `type: migration` trigger
  extended field extraction: `state_key`, `services`, `check_commands`,
  `health_checks`, `system_requirements`, `install_commands`, `verify_commands`,
  `post_install_notes`.

- **Error conditions:** Per-skill load errors log a warning and return `None`;
  the caller filters `None` entries.

### Rationale (WHY)

`SkillManager` was designed when agent definitions were JSON files with a `skills`
field; `_load_agent_mappings()` extracted those lists to build the mapping.  The
agent format migrated to YAML-frontmatter `.md` files, but the `templates/*.json`
path was not updated.  PM skills use a separate scanning path because PM-level
skills (the `mpm-*` series) are always present in `.claude/skills/` and need to
be inspectable regardless of the agent-mapping feature.

`SkillManager` is the integration layer used by the PM itself at runtime; it is
distinct from `SkillsRegistry` (used for skill metadata lookup) and `SkillsService`
(used for deployment).

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.skills.skill_manager` | `SkillManager` class; `_load_agent_mappings()`, `get_agent_skills()`, `_get_pm_skills()`, `get_migration_skills()` |

---

## AgentSkillsInjector — graceful-noop behavior {#SPEC-SKILLS-07~1}

**ID:** SPEC-SKILLS-07~1
**Status:** Active

### Behavior Contract (WHAT)

- **Inputs:**
  - Constructor: `skills_service: SkillsService` — the service used to query
    agent-to-skill mappings.
  - `enhance_agent_template(template_path: Path)` — path to an agent template file.
  - `generate_frontmatter_with_skills(agent_config: dict)` — agent configuration dict.
  - `inject_skills_documentation(agent_content: str, skills: list)` — agent markdown
    body and list of skill names.
  - `inject_complete_skills(agent_id: str, template_content: str)` — agent ID and
    full template content.

- **Current observable behavior (all paths are graceful noops):**

  1. **`__init__`:** If `skills_service.registry` lacks an `agent_skills` key (which
     it always does, because `config/skills_registry.yaml` does not exist), logs a
     single warning at construction time:
     `"AgentSkillsInjector: skills registry has no agent_skills mapping … All inject/enhance calls will be no-ops."`
     No exception is raised.

  2. **`enhance_agent_template(template_path)`:**
     If `template_path` has a `.md` suffix, logs a warning and returns `{}`.
     If the path has a `.json` suffix but the file does not exist or cannot be
     parsed, logs an error.
     Even for valid JSON templates: `SkillsService.get_skills_for_agent()` returns
     `[]` (because the registry is empty), so the returned template dict has
     `skills: {"required": [], "optional": [], "auto_load": True}`.

  3. All other methods (`generate_frontmatter_with_skills`,
     `inject_skills_documentation`, `inject_complete_skills`) call
     `get_skills_for_agent()`, receive empty lists, and return either unchanged
     content or frontmatter/dicts with empty skills fields.

- **Hand-authored frontmatter is the live mechanism:**
  The `skills:` field in deployed agent `.md` frontmatter (e.g., `code-critic.md`
  lists `[code-review-standards, code-production-process, …]`) is authored
  directly by agent maintainers, not injected by `AgentSkillsInjector`.
  `AgentSkillsInjector` does not participate in the current deployment pipeline.

- **`enhance_agent_template` guard (`.md` path):**
  A guard added as part of D3 remediation logs a warning and returns `{}` when
  a `.md` path is passed, rather than raising or attempting a JSON parse.
  This makes the method safe to call in contexts that may inadvertently pass the
  current `.md`-based agent paths.

- **Error conditions:**
  No exceptions are raised by any method under normal operating conditions.
  All error paths log and return safe empty values.

### Rationale (WHY)

`AgentSkillsInjector` was designed to dynamically inject skill assignments at
deploy time without modifying source template files.  The design assumed:
(a) `config/skills_registry.yaml` as a source of truth for agent-to-skill
mappings, and (b) JSON agent templates as the injection target.

Both assumptions became false when the agent format migrated to `.md` frontmatter
and `config/skills_registry.yaml` was never populated.  Rather than removing the
class (which would require updating callers) or silently doing nothing (which would
hide the degradation), the D3 remediation added an explicit warning at construction
time and a `.md` path guard in `enhance_agent_template`.  The class is retained
as a placeholder for the planned redesign tracked in issue #601.

The graceful-noop contract — no exceptions, no side effects, explicit warning —
is the minimal safe behavior that keeps callers functional while the inoperability
is visible in logs.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.skills.agent_skills_injector` | `AgentSkillsInjector` class; all injection methods; D3 `.md` guard; construction-time warning |

---

## Known Drift

This section documents verified mismatches between documented/intended behavior
and actual observed behavior.  Each item is grounded in direct code inspection.

### D3 — Inoperative programmatic skills injection (partial fix applied; #601 open)

**Intended behavior:** `AgentSkillsInjector` injects skill names into agent
templates at deploy time by reading agent-to-skill mappings from
`config/skills_registry.yaml`.

**Actual behavior:** `AgentSkillsInjector` is a graceful noop.  Two root causes:

1. `config/skills_registry.yaml` does not exist anywhere in the repository.
   `SkillsService.get_skills_for_agent()` always returns `[]`.

2. `src/claude_mpm/agents/templates/*.json` do not exist.
   `_load_agent_mappings()` in `SkillManager` finds no files;
   `agent_skill_mapping` is always empty.

**Minimal fix applied this cycle (D3 remediation):**
`AgentSkillsInjector.__init__` now logs a warning when the registry lacks
`agent_skills`.  `enhance_agent_template()` now guards against `.md` paths
(returning `{}` with a warning instead of attempting a JSON parse).

**Live mechanism:** The `skills:` field in deployed agent `.md` frontmatter is
hand-authored by agent maintainers.

**Full restore tracked in:** issue #601.

---

### DUAL discovery split (SkillsRegistry vs SkillsService)

The 21 flat `.md` files in `bundled/` root and the 58 directory-based
`SKILL.md` files under `bundled/<category>/<name>/` are each discovered by only
one service:

- `SkillsRegistry` discovers **only** the 21 flat files (via `glob("*.md")`).
- `SkillsService.discover_bundled_skills()` discovers **only** the 58 directory
  files (via two-level directory iteration).

Neither service is aware of the other's population.  No code combines or
deduplicates across the two sets.  A skill name that exists in both populations
(e.g., `systematic-debugging`) is discoverable via both paths independently with
no collision handling.

The real discovery services for the two populations, verified during SLD work:

| Service | Population | Method |
|---------|-----------|--------|
| `SkillsService.discover_bundled_skills()` | 58 directory-based bundled skills | Two-level directory iteration in `skills/bundled/` |
| `SkillDiscoveryService.discover_skills()` | Remote/cache skills (and legacy flat files in a target dir) | `rglob("SKILL.md")` + top-level `*.md` fallback |

No documentation acknowledges this split.

---

### Missing `config/skills_registry.yaml` and `agents/templates/*.json`

`SkillsService.get_skills_for_agent()` is documented to read from
`config/skills_registry.yaml`.  This file does not exist.  `SkillManager`
is documented to load agent-skill mappings from `agents/templates/*.json`.
No JSON files exist in that directory.  Both methods return empty results
silently (with a warning log) in every fresh installation.

---

### `version` vs `skill_version` frontmatter key inconsistency

`SkillDiscoveryService._parse_skill_file()` reads frontmatter key `skill_version`
(defaulting to `"1.0.0"` if absent).  All 58 directory-based bundled `SKILL.md`
files inspected use `version:` (not `skill_version:`).  Therefore
`SkillDiscoveryService` reports `skill_version = "1.0.0"` for all bundled skills
regardless of what `version:` is set to in their frontmatter.

`SkillsService._parse_skill_metadata()` reads the `version:` key correctly.
`SkillsRegistry` reads the `version:` key via `_apply_backward_compatibility()`.

The inconsistency is confined to `SkillDiscoveryService` (used for remote/cache
skills) and does not affect bundled skill deployment or version comparison
(`check_for_updates()`), which uses `SkillsService`.
