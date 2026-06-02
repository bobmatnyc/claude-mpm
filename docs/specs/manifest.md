# Manifest Configuration Subsystem — Spec-Linked Documentation

**Status:** Active (sections: draft pending backfill)
**Version:** v1
**Subsystem:** MANIFEST

This document covers the core behavioral contracts for the claude-mpm manifest
configuration system.  Each section constitutes one governed specification with a
stable ID, a behavior contract (WHAT), a rationale section (WHY), and an
implementing-modules table.

The IDs below use the `{#SPEC-MANIFEST-NN~1}` anchor form that the traceability
checker recognizes as a declaration.  Engineer agents add matching
`References: SPEC-MANIFEST-NN~1` entries to the docstrings of implementing modules.

Design source of truth: `docs/design/manifest-config-system.md`

---

## Table of Contents

| ID | Section | Implementing module(s) |
|----|---------|------------------------|
| SPEC-MANIFEST-01~1 | [Detection-gated loading — dormant-unless-present contract](#detection-gated-loading--dormant-unless-present-contract-spec-manifest-011) | `claude_mpm.manifest.loader` |
| SPEC-MANIFEST-02~1 | [Deep-merge semantics including setup.services union](#deep-merge-semantics-including-setupservices-union-spec-manifest-021) | `claude_mpm.manifest.merger` |
| SPEC-MANIFEST-03~1 | [Schema validation contract](#schema-validation-contract-spec-manifest-031) | `claude_mpm.manifest.schema` |
| SPEC-MANIFEST-04~1 | [Preset resolution — four-step resolution order](#preset-resolution--four-step-resolution-order-spec-manifest-041) | `claude_mpm.manifest.resolver`, `claude_mpm.manifest.presets` |

---

## Detection-gated loading — dormant-unless-present contract {#SPEC-MANIFEST-01~1}

**ID:** SPEC-MANIFEST-01~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

- **Inputs:**
  - `start_dir: Path | str` — a directory path from which to search upward for
    `.claude-mpm/manifest.json`.
  - Optional `preset_resolver: Callable[[str], dict] | None` — injectable callable
    used to resolve the `extends` preset name to a raw manifest dict.

- **Outputs:**
  - `find_manifest(start_dir) -> Path | None` — returns the absolute path to the
    manifest file if one is found at `<repo-root>/.claude-mpm/manifest.json`;
    returns `None` if no such file exists anywhere in the directory hierarchy.
  - `load_manifest(start_dir, preset_resolver=None) -> ManifestResult | None` —
    returns `None` (sentinel "no manifest") when no manifest file is found.
    Returns a `ManifestResult` when the file exists.  Never raises due to absence
    of the manifest file.

- **Preconditions:** `start_dir` must be a readable directory.

- **Postconditions (file absent):** The function returns `None`.  No logging, no
  warnings, no defaults applied, no state mutated.  Existing system behavior is
  completely unchanged.

- **Postconditions (file present):**
  1. The file is read and parsed as JSON.  A `ManifestLoadError` is raised on
     malformed JSON with a clear, actionable message.
  2. The parsed dict is validated against the manifest JSON schema (SPEC-MANIFEST-03~1).
     A `ManifestValidationError` is raised with the offending key and violated
     constraint when validation fails.
  3. If `extends` is absent or `preset_resolver` is `None`, a `ManifestResult` is
     returned with the raw repo manifest (no preset merged).
  4. If `extends` is present AND `preset_resolver` is provided, the resolver is
     called with the `extends` string and its return value is deep-merged under
     the repo manifest via the merger (SPEC-MANIFEST-02~1).  The resulting merged
     dict is stored in `ManifestResult.effective`.

- **Error conditions:**
  - Missing file: returns `None` (not an error).
  - Malformed JSON: raises `ManifestLoadError`.
  - Schema violation: raises `ManifestValidationError`.
  - Resolver failure: propagates the resolver's exception unchanged.

### Rationale (WHY)

- The "dormant unless detected" contract is the foundational design constraint
  for this subsystem.  Many projects using claude-mpm do not have a manifest.
  If the loader applied defaults or emitted warnings on every startup without a
  file, it would break the experience for the majority of users who have not
  opted in.  Returning `None` (not an empty dict, not a default manifest) makes
  the absent case unambiguously distinguishable from "manifest present but empty".

- The injectable `preset_resolver` parameter creates a clean seam for PR2
  (preset resolution) without requiring the loader to be rewritten.  PR1 callers
  that do not yet have a resolver simply omit it; the loader degrades gracefully.

- Searching upward from `start_dir` (rather than requiring an absolute path)
  mirrors `git` and `tsconfig.json` discovery conventions, allowing `load_manifest`
  to be called from any subdirectory of a project.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.manifest.loader` | Full implementation: `find_manifest`, `load_manifest`, `ManifestResult` |

---

## Deep-merge semantics including setup.services union {#SPEC-MANIFEST-02~1}

**ID:** SPEC-MANIFEST-02~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

- **Inputs:**
  - `preset: dict` — the resolved preset manifest dict (may be empty).
  - `repo: dict` — the repo-level manifest dict (may be empty).

- **Outputs:** A new dict `effective` representing the merged configuration.
  Neither `preset` nor `repo` is mutated.

- **Merge rules (applied recursively):**

  | Location | Rule |
  |----------|------|
  | Scalar values | `repo` wins; if `repo` omits the key, `preset` value is used. |
  | Object values (`agents`, `settings`, `hooks`, and any nested dicts) | Deep merge; for any key present in both, `repo` wins at the leaf level via recursive application of these rules. |
  | `setup.services` array | Union of `preset["setup"]["services"]` and `repo["setup"]["services"]`, deduplicated, preserving insertion order (preset entries first, then repo-only extras). |
  | All other arrays | `repo` replaces `preset` entirely when `repo` specifies the key.  If `repo` omits the key, `preset` value is used. |

- **Preconditions:** Both `preset` and `repo` must be valid Python dicts.  Values
  may be of any JSON-compatible type.

- **Postconditions:**
  - The returned dict contains all keys from `preset` that are not overridden by `repo`.
  - All keys from `repo` appear in the result with their `repo` values (or merged
    sub-dicts where the rule requires deep merge).
  - `effective["setup"]["services"]` (when both sides supply the key) is the
    deduplicated union preserving preset-first insertion order.
  - All other array keys in `effective` come from `repo` when `repo` sets them.

- **Error conditions:** Raises `TypeError` if either argument is not a `dict`.

### Rationale (WHY)

- The split between "object deep-merge" and "array replace" is deliberate.
  Objects (agents, settings) represent named configurations where partial overrides
  are the common case (e.g. override one agent's model without restating all its
  other fields).  Arrays outside `setup.services` represent ordered command lists
  (hook arrays) where a partial override would produce unpredictable behavior.
  Replacing the entire array gives the repo author full control.

- `setup.services` is the single exception to the array-replace rule because the
  expected semantics is "run the preset's services AND the repo's services".
  A union merge with deduplication matches how most users will think about it:
  "I want the company standard services PLUS my project-specific ones."

- Pure-function design (no I/O, no global state) makes the merger independently
  testable and usable in any context where the caller has already loaded the dicts.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.manifest.merger` | Full implementation: `deep_merge` pure function |

---

## Schema validation contract {#SPEC-MANIFEST-03~1}

**ID:** SPEC-MANIFEST-03~1
**Status:** draft (pending backfill)

### Behavior Contract (WHAT)

- **Inputs:** `data: dict` — a parsed manifest dict to validate.

- **Outputs:** `None` on success (no return value).

- **Schema structure (JSON Schema draft-07):**

  | Key | Type | Required | Constraint |
  |-----|------|----------|------------|
  | `version` | string | yes | Enum: `["1.0"]` |
  | `extends` | string | no | Min length 1 |
  | `agents` | object | no | Values are objects |
  | `hooks` | object | no | Values are arrays of strings |
  | `settings` | object | no | Arbitrary key-value pairs |
  | `setup` | object | no | Contains optional `services` (array of strings) |

- **Additional properties:** Allowed at the top level (the schema does not set
  `additionalProperties: false`).  This matches the design doc's intent of an
  extensible format where future top-level keys can be added without breaking
  existing validators.

- **Error conditions:** Raises `ManifestValidationError` when `data` fails
  validation.  The error message includes the offending JSON path and the
  schema constraint that was violated.  The exception carries `path` (a
  dot-separated string) and `message` (human-readable description) attributes.

### Rationale (WHY)

- JSON Schema draft-07 is used (rather than Pydantic or a hand-written
  validator) because `jsonschema` is already a transitive dependency of the
  claude-mpm stack and adds zero new installation cost.  The schema dict lives
  in Python source so it is importable, testable, and diffable via normal code
  review tooling.

- Allowing additional properties at the top level makes the schema forward-compatible:
  an older version of claude-mpm can load a manifest written for a newer version
  without validation errors, provided the known fields are valid.  Individual
  subsections (e.g. `setup`) may be stricter if their semantics require it.

- `ManifestValidationError` is a distinct exception type (not a generic
  `ValueError`) so callers can catch it precisely and present actionable error
  messages without catching unrelated `ValueError` exceptions from other parts of
  the system.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.manifest.schema` | `MANIFEST_SCHEMA` dict, `validate_manifest`, `ManifestValidationError` |

---

## Preset resolution — four-step resolution order {#SPEC-MANIFEST-04~1}

**ID:** SPEC-MANIFEST-04~1
**Status:** active

### Behavior Contract (WHAT)

- **Inputs:**
  - `extends: str` — the value of the `extends` key in a repo manifest.  May be
    a local path (starts with `./` or `/`), a preset name, or a built-in preset
    name.

- **Outputs:** A validated manifest dict representing the resolved preset.

- **Resolution order (FIRST MATCH WINS):**

  | Step | Source | Condition / Location |
  |------|--------|----------------------|
  | 1 | **Local path** | `extends` starts with `./` or `/`.  Resolved relative to the current working directory for `./`; absolute path used as-is for `/`. |
  | 2 | **User preset directory** | `~/.claude-mpm/presets/<extends>.json` |
  | 3 | **Package entry point** | `importlib.metadata.entry_points(group="claude_mpm.presets")` with key `== extends`.  Entry point must be callable; called as `get_manifest() -> dict`. |
  | 4 | **Built-in presets** | Bundled JSON files in `claude_mpm/manifest/presets/` package; loaded via `importlib.resources` so the package works when installed as a wheel. |

- **Dormant principle:** Resolution is only ever triggered when (a) a manifest
  file is detected by the loader and (b) that manifest contains a non-empty
  `extends` key.  Projects without a manifest file are completely unaffected.

- **Validation:** Each resolved preset dict is validated against the manifest
  JSON schema (SPEC-MANIFEST-03~1) before being returned.  A preset with an
  invalid shape raises `ManifestValidationError`.

- **Multi-level chains:** If a resolved preset itself contains an `extends` key,
  that key is ignored for now (multi-level chaining is out of scope for this
  implementation — see TODO referencing optional feature O1 in `resolver.py`).

- **Error conditions:**
  - No source matches: raises `PresetResolutionError` with a message listing all
    sources that were tried.
  - JSON file present but unreadable / invalid JSON: raises `PresetResolutionError`
    wrapping the underlying I/O or parse error.
  - Resolved preset fails schema validation: raises `ManifestValidationError`.

### Rationale (WHY)

- The four-step order mirrors common precedence conventions in tooling (local >
  user > installed > built-in) so that more specific overrides win over more
  general ones without surprising the user.

- Local paths allow teams to version-control presets alongside their code without
  publishing a Python package.

- The user preset directory (`~/.claude-mpm/presets/`) gives individual
  developers a personal preset slot that does not require any installation step.

- Entry points are the standard Python extension mechanism (pytest plugins,
  Sphinx extensions, Babel extractors all use the same pattern), so third-party
  preset authors can publish a `claude-mpm-<name>` pip package and have it
  auto-discovered without requiring the user to configure any path.

- Built-in presets serve as zero-install defaults and as reference implementations
  that demonstrate valid manifest structure.

- Loading bundled JSON via `importlib.resources` (not raw `__file__` path joins)
  is required for correct behavior when the package is installed as a zip-safe
  wheel.

### Implementing Modules

| Module | Role |
|--------|------|
| `claude_mpm.manifest.resolver` | `resolve_preset`, `PresetResolutionError`; implements the four-step resolution order |
| `claude_mpm.manifest.presets` | `load_builtin_preset`; loads bundled `default.json`, `minimal.json`, `enterprise.json` via `importlib.resources` |
