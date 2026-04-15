# JSON Manifest Configuration System

## Overview

The manifest configuration system provides a structured, extensible way to configure claude-mpm for a project or organization. It follows the TypeScript `tsconfig.json` `extends` pattern: a repo-level `.claude-mpm/manifest.json` file can extend a named preset (company-wide, built-in, or local), with deep-merge semantics so repo-specific settings always win over the preset.

Key design goals:

- **Preset distribution**: Organizations publish their configuration as a pip or npm package (e.g. `claude-mpm-duetto`), allowing any project to inherit it with a single `"extends": "duetto"` line.
- **Layered overrides**: Repo-level config is merged on top of the preset; scalars and objects follow deep-merge rules; arrays are union-merged for `setup.services` and replaced outright for everything else.
- **Single source of truth**: Running `claude-mpm manifest show` always prints the resolved effective config so there is no ambiguity about what is active.
- **Discoverable CLI**: `claude-mpm manifest` subcommands make the system self-documenting and easy to adopt incrementally.

---

## File Location and Format

The repo-level manifest lives at:

```
<repo-root>/.claude-mpm/manifest.json
```

This file is typically checked into version control so the whole team shares the same baseline configuration.

---

## JSON Schema

### Top-level keys

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `version` | `"1.0"` | yes | Schema version. Currently only `"1.0"` is valid. |
| `extends` | string | no | Name or path of the preset to extend. See [Preset Resolution](#preset-resolution). |
| `agents` | object | no | Agent overrides. Keys are agent names, values are partial agent config objects. |
| `hooks` | object | no | Hook event definitions. Keys are event names (e.g. `PreToolUse`), values are arrays of command strings. |
| `settings` | object | no | Settings overrides, merged into the resolved settings. |
| `setup` | object | no | Automated setup directives run by `claude-mpm setup`. |

### `agents` object

Each key is an agent name matching an agent `.md` file. The value is a partial agent config that is deep-merged onto the preset's agent config for that name (if any).

Supported agent config fields include all MPM-proprietary and Claude Code native fields documented in CLAUDE.md:

```jsonc
{
  "agents": {
    "engineer": {
      "model": "sonnet",        // Claude Code native
      "color": "blue",          // Claude Code native
      "max_tokens": 8192,       // MPM-proprietary
      "resource_tier": "tier2"  // MPM-proprietary
    }
  }
}
```

### `hooks` object

Keys are hook event names: `PreToolUse`, `PostToolUse`, `Stop`, `SubagentStop`, `SessionStart`, `UserPromptSubmit`.

Values are arrays of command strings. During merge, arrays from the repo config **replace** the preset's array for that event (not union-merged).

```jsonc
{
  "hooks": {
    "PreToolUse": ["./hooks/my-hook.sh"],
    "Stop": ["./hooks/cleanup.sh"]
  }
}
```

### `settings` object

Arbitrary settings passed through to the resolved settings. Deep-merged with the preset's `settings`. Common subkeys:

```jsonc
{
  "settings": {
    "permissions": {
      "additionalDirectories": ["~/shared-data"]
    },
    "model": "claude-sonnet-4-5"
  }
}
```

### `setup` object

Directives used by `claude-mpm setup` to initialize the project environment.

| Key | Type | Description |
|-----|------|-------------|
| `services` | string[] | MCP service names to install. Union-merged with preset. |

```jsonc
{
  "setup": {
    "services": ["kuzu-memory", "mcp-ticketer"]
  }
}
```

---

## Preset Resolution

When `extends` is specified, claude-mpm resolves the preset in this order:

1. **Local path** — if the value starts with `./` or `/`, treated as a relative or absolute filesystem path to a JSON file.
2. **User preset directory** — `~/.claude-mpm/presets/<name>.json`
3. **Installed package entry point** — a Python package named `claude-mpm-<name>` that exposes a `claude_mpm.presets` entry point group with key `<name>`. The entry point must be a callable `get_manifest() -> dict`.
4. **Built-in presets** — presets bundled inside the claude-mpm package itself (see [Built-in Presets](#built-in-presets)).

If no preset is found, `manifest validate` reports an error and `setup` aborts.

---

## Merge Strategy

Given a resolved preset `P` and a repo manifest `R`, the effective config `E` is computed as follows:

| Location | Rule |
|----------|------|
| Scalar values | `R` wins; if `R` omits the key, `P` value is used. |
| Object values (`agents`, `settings`, `hooks`) | Deep merge; for any key present in both, `R` wins at the leaf level. |
| `setup.services` | Union of `P` and `R` arrays (deduplication preserves insertion order). |
| All other arrays (e.g. individual `hooks.*` event arrays) | `R` replaces `P` entirely if `R` specifies the key. |

### Example merge

Preset `P`:

```json
{
  "agents": {
    "engineer": { "model": "haiku", "color": "green" }
  },
  "setup": {
    "services": ["kuzu-memory"]
  }
}
```

Repo manifest `R`:

```json
{
  "extends": "acme",
  "agents": {
    "engineer": { "model": "sonnet" }
  },
  "setup": {
    "services": ["mcp-ticketer"]
  }
}
```

Effective config `E`:

```json
{
  "agents": {
    "engineer": { "model": "sonnet", "color": "green" }
  },
  "setup": {
    "services": ["kuzu-memory", "mcp-ticketer"]
  }
}
```

`engineer.model` comes from `R` (wins); `engineer.color` comes from `P` (not overridden); `setup.services` is the union of both arrays.

---

## Examples

### Minimal manifest (no preset)

```json
{
  "version": "1.0",
  "setup": {
    "services": ["kuzu-memory"]
  }
}
```

### Full Duetto example

```json
{
  "version": "1.0",
  "extends": "duetto",
  "agents": {
    "engineer": { "model": "sonnet", "color": "blue" },
    "reviewer": { "model": "haiku", "max_turns": 5 }
  },
  "hooks": {
    "PreToolUse": ["./hooks/my-hook.sh"],
    "Stop": ["./hooks/post-session-report.sh"]
  },
  "settings": {
    "permissions": {
      "additionalDirectories": ["~/shared-data", "~/duetto-datasets"]
    }
  },
  "setup": {
    "services": ["kuzu-memory", "mcp-ticketer"]
  }
}
```

When resolved against the `duetto` preset, this manifest:

- Inherits all Duetto-defined agents, services, and hooks.
- Overrides `engineer.model` to `sonnet` and sets its color.
- Adds a `reviewer` agent.
- Replaces the `PreToolUse` hook array with the repo-specific hook.
- Adds `Stop` hook.
- Deep-merges `settings.permissions`, appending the repo-specific directories to whatever the preset defines.
- Union-merges `setup.services` so Duetto's services are also installed.

---

## Built-in Presets

Claude-mpm ships three built-in presets accessible without installing any additional package:

### `default`

The baseline MPM config. Includes standard agent definitions, no opinionated hooks, and common MCP services. Suitable for individual developers who want a sensible starting point.

```bash
# Use it
echo '{"version":"1.0","extends":"default"}' > .claude-mpm/manifest.json
```

### `minimal`

Only the essentials: version pin and no preset-supplied agents or services. Use when you want full control and prefer to define everything explicitly.

### `enterprise`

Stricter permissions, pre-configured audit hooks (`PreToolUse` and `Stop`), and a conservative model tier. Intended for organizations that require an audit trail and want to enforce model selection policy.

---

## Preset Authoring Guide

Any team or company can publish a preset as a Python package. The following describes how to create a `claude-mpm-duetto` preset package.

### Package layout

```
claude-mpm-duetto/
  pyproject.toml
  manifest.json
  manifest.py
```

### `manifest.json`

The preset configuration. This is a standard manifest without an `extends` key (or it may chain to another preset, including built-ins):

```json
{
  "version": "1.0",
  "agents": {
    "engineer": {
      "model": "sonnet",
      "resource_tier": "tier2"
    },
    "data-analyst": {
      "model": "sonnet",
      "color": "yellow"
    }
  },
  "hooks": {
    "PreToolUse": ["claude-mpm-duetto-hook pre"],
    "Stop": ["claude-mpm-duetto-hook post"]
  },
  "settings": {
    "permissions": {
      "additionalDirectories": ["~/duetto-shared"]
    }
  },
  "setup": {
    "services": ["kuzu-memory", "mcp-ticketer", "duetto-mcp"]
  }
}
```

### `manifest.py`

```python
import json
from pathlib import Path

def get_manifest() -> dict:
    manifest_path = Path(__file__).parent / "manifest.json"
    return json.loads(manifest_path.read_text())
```

### `pyproject.toml`

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "claude-mpm-duetto"
version = "1.0.0"
dependencies = ["claude-mpm>=6.0"]

[project.entry-points."claude_mpm.presets"]
duetto = "manifest:get_manifest"
```

After `pip install claude-mpm-duetto`, any repo can use `"extends": "duetto"` in its manifest.

### npm distribution

If the team also uses claude-mpm via npm, publish a `claude-mpm-duetto` npm package with the same `manifest.json` at the package root. The npm preset resolver looks for `<package-root>/manifest.json` from the entry resolved by `require.resolve('claude-mpm-duetto/manifest.json')`.

---

## CLI Reference

### `claude-mpm setup`

Reads `.claude-mpm/manifest.json`, resolves the preset, and installs the services listed in the merged `setup.services`.

```bash
claude-mpm setup               # reads manifest.json, runs setup.services
claude-mpm setup --manifest    # force re-read manifest and re-apply (idempotent)
```

If no `manifest.json` is found, `setup` falls back to the current behavior (no-op or interactive prompt).

### `claude-mpm manifest init`

Interactively scaffolds a `.claude-mpm/manifest.json`. Asks for:

1. Preset name (or none)
2. Which services to include in `setup.services`
3. Whether to add any agent overrides

```bash
claude-mpm manifest init
```

### `claude-mpm manifest validate`

Validates `.claude-mpm/manifest.json` against the JSON schema and checks that the named preset can be resolved. Exits non-zero on error. Suitable for CI.

```bash
claude-mpm manifest validate
claude-mpm manifest validate --file path/to/other-manifest.json
```

### `claude-mpm manifest show`

Resolves the manifest (including preset) and prints the merged effective config as pretty-printed JSON to stdout. Use this to understand exactly what configuration is active.

```bash
claude-mpm manifest show
claude-mpm manifest show | jq '.agents'
```

---

## Implementation Notes

The following components need to be built or extended.

### New: `src/claude_mpm/manifest/`

A new package containing:

- `loader.py` — reads and parses `.claude-mpm/manifest.json`; validates against the JSON schema using `jsonschema`
- `resolver.py` — implements the four-step preset resolution order; handles local path, user preset dir, entry point, and built-in presets
- `merger.py` — implements the merge strategy (deep merge for objects, union for `setup.services`, replace for other arrays, scalar-wins for scalars)
- `schema.py` — the canonical JSON schema as a Python dict, used by `validate` and by `loader.py` on load
- `presets/` — directory containing `default.json`, `minimal.json`, `enterprise.json`

### New: `src/claude_mpm/cli/manifest_commands.py`

Click command group `manifest` with subcommands `init`, `validate`, `show`.

### Modified: `src/claude_mpm/cli/setup.py`

Extend the existing `setup` command to call `manifest.loader.load_manifest()` and pass the resolved `setup.services` list to the service installer.

### Modified: `src/claude_mpm/migrations/`

Add a migration that detects legacy `.claude-mpm/config.json` (if any) and offers to migrate it to `manifest.json` format.

### Testing

- Unit tests for `merger.py` covering all merge rules, including edge cases (empty preset, empty repo manifest, conflicting nested objects).
- Unit tests for `resolver.py` mocking entry points and filesystem.
- Integration tests for `claude-mpm manifest validate` and `claude-mpm manifest show` using fixture manifests.
- A fixture package `tests/fixtures/claude-mpm-test-preset/` that acts as a minimal installable preset for integration testing.

### JSON Schema enforcement

Use `jsonschema` (already a transitive dependency via other parts of the stack) to validate manifests on load. Emit clear error messages pointing to the offending key and the schema constraint that was violated.

### Entry point discovery

Use `importlib.metadata.entry_points(group="claude_mpm.presets")` (Python 3.9+) to enumerate installed presets. This is the same mechanism used by pytest plugins and sphinx extensions, so the pattern is well-understood.

---

## Related Documentation

- [Configuration Hierarchy](../configuration/README.md)
- [Hierarchical BASE-AGENT Templates](./hierarchical-base-agents.md)
- [Hooks System](./HOOK_EVENT_EMISSION.md)
- [Skills Integration Design](./claude-mpm-skills-integration-design.md)
