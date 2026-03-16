# Agent Repository Versioning

How claude-mpm enforces compatibility between the CLI and agent repositories, enabling safe breaking changes to agent templates.

## Motivation

Prior to this feature, there was no mechanism to coordinate breaking changes between the `claude-mpm` CLI and agent repositories like `claude-mpm-agents`. An agent repository maintainer could restructure agent templates, change metadata formats, or require new CLI features — and users running older CLI versions would silently receive broken or incompatible agents with no warning.

The agent repository versioning system solves this by:

1. **Declaring compatibility constraints** in the agent repository via `agents-manifest.yaml`
2. **Checking those constraints at sync time** before downloading agents
3. **Re-checking at deploy time** before copying cached agents into a project
4. **Surfacing actionable warnings** (or hard blocks) to the user with upgrade instructions

The design follows a **fail-open** philosophy: if the manifest is missing, unparseable, or the check fails unexpectedly, sync proceeds normally. Only explicitly declared incompatibilities trigger warnings or blocks.

## Architecture Overview

The versioning system has four components:

```
agents-manifest.yaml          (in agent repository root)
        |
        v
ManifestFetcher                (fetches manifest from remote URL or local path)
        |
        v
ManifestChecker                (evaluates compatibility decision matrix)
        |
        v
ManifestCache (SQLite)         (persists results for deploy-time and offline use)
        |
        v
DeploymentVersionGate          (re-validates at deploy time from cache)
```

### Sync-time flow

1. `GitSourceSyncService.sync_agents()` begins syncing an agent source
2. Before processing any agent files, `_check_manifest_compatibility()` runs
3. `ManifestFetcher` fetches `agents-manifest.yaml` from the repository root (stripping any subdirectory from the source URL)
4. `ManifestChecker.check()` evaluates the manifest against the running CLI version
5. Result is persisted to `ManifestCache` (SQLite at `~/.claude-mpm/cache/manifest_cache.db`)
6. Based on the result:
   - **COMPATIBLE** or **NO_MANIFEST**: sync proceeds normally
   - **INCOMPATIBLE_WARN**: sync proceeds, warning logged, console warning displayed after startup
   - **INCOMPATIBLE_HARD**: sync is aborted for this source (`IncompatibleRepoError` raised)

### Deploy-time flow

When agents are deployed from cache to a project's `.claude/agents/` directory, `DeploymentVersionGate` re-checks the cached manifest to prevent stale cached agents from being deployed if the manifest has since declared them incompatible.

### Console warnings

After the sync pipeline completes, `_display_manifest_compatibility_warnings()` in `startup.py` reads the `ManifestCache` and prints a user-visible warning for every source whose `min_cli_version` exceeds the running CLI version. This makes soft warnings impossible to miss.

## The `agents-manifest.yaml` File

This file lives at the **root** of the agent repository (not inside the `agents/` subdirectory). It declares compatibility constraints that the CLI checks before syncing agents.

### Minimal example

```yaml
repo_format_version: 1
min_cli_version: "5.10.0"
```

### Full example with all supported fields

```yaml
# Schema version for the manifest format itself.
# CLI will hard-block if this exceeds its MAX_SUPPORTED_REPO_FORMAT (currently 1).
repo_format_version: 1

# Minimum CLI version required for this agent repository.
# CLI versions below this receive a warning but still sync (soft constraint).
# Must be a valid PEP 440 version string (e.g., "5.10.0", not "v5.10.0").
min_cli_version: "5.10.0"

# Advisory maximum CLI version. If the CLI exceeds this, an informational
# log is emitted but sync is never blocked. Useful for signaling that the
# repository hasn't been tested with newer CLI versions yet.
max_cli_version: "6.0.0"

# Free-text migration guidance shown alongside compatibility warnings.
migration_notes: |
  Agent templates now use the v2 metadata format.
  Run 'claude-mpm agents deploy-all --force-sync' after upgrading.

# Fine-grained version ranges (checked before min_cli_version).
# First matching range wins. If no range matches, falls through to
# min_cli_version check.
compatibility_ranges:
  - cli: ">=5.10.0"
    status: full
  - cli: ">=5.8.0 <5.10.0"
    status: degraded
    notes: "Some agents may not render correctly. Upgrade recommended."

# Per-agent overrides for min_cli_version.
# Agents not listed here inherit the repo-level min_cli_version.
agents:
  rust-engineer:
    min_cli_version: "5.11.0"
    notes: "Rust engineer requires the new tool-use metadata format."
  data-scientist:
    min_cli_version: "5.10.0"

# Deprecation warnings (informational only, never block sync).
# Shown when the feature has not yet been removed (removed_in > CLI version).
deprecation_warnings:
  - feature: "legacy_template_format"
    removed_in: "6.0.0"
    replacement: "v2_template_format"
    deadline: "2025-06-01"
```

### Field reference

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `repo_format_version` | integer | No | `1` | Schema version of the manifest. CLI hard-blocks if this exceeds its `MAX_SUPPORTED_REPO_FORMAT`. Increment this when making breaking changes to the manifest format itself. |
| `min_cli_version` | string | No | `"0.0.0"` | Minimum CLI version (PEP 440). Versions below this receive a warning. |
| `max_cli_version` | string | No | — | Advisory upper bound. Never blocks; informational log only. |
| `migration_notes` | string | No | — | Free-text guidance shown with compatibility warnings. |
| `compatibility_ranges` | list | No | — | Ordered list of CLI version ranges with `full` or `degraded` status. |
| `agents` | dict | No | — | Per-agent `min_cli_version` overrides keyed by agent name. |
| `deprecation_warnings` | list | No | — | Informational deprecation notices (never block). |

## Compatibility Decision Matrix

The `ManifestChecker` evaluates rules top-to-bottom; first match wins:

| # | Condition | Result | Effect |
|---|-----------|--------|--------|
| 1 | Manifest absent or empty | `NO_MANIFEST` | Fail-open: sync proceeds without constraints |
| 2 | YAML parse failure | `NO_MANIFEST` | Fail-open with warning log |
| 3 | Parsed value is not a dict | `NO_MANIFEST` | Fail-open with warning log |
| 4 | `repo_format_version` > `MAX_SUPPORTED_REPO_FORMAT` | `INCOMPATIBLE_HARD` | **Sync blocked**. User must upgrade CLI. |
| 4a | `compatibility_ranges` match found | `COMPATIBLE` or `INCOMPATIBLE_WARN` | Takes precedence over rule 5 |
| 5 | CLI version < `min_cli_version` | `INCOMPATIBLE_WARN` | Sync proceeds with console warning |
| 6 | CLI version > `max_cli_version` | `COMPATIBLE` | Advisory log only; never blocks |
| 7 | All checks pass | `COMPATIBLE` | Normal operation |

### Hard block vs. soft warning

- **Hard block** (`INCOMPATIBLE_HARD`): Only triggered by `repo_format_version`. This represents a fundamental change to how the CLI interprets the repository structure — an older CLI physically cannot parse the new format. The sync is skipped entirely for this source.

- **Soft warning** (`INCOMPATIBLE_WARN`): Triggered by `min_cli_version` or `degraded` compatibility ranges. Agents are still synced and deployed, but the user sees a clear upgrade nudge. This is the appropriate level for "agents work but may have issues" scenarios.

## CLI Commands

### Adding an agent source from a branch

When developing or testing agent changes on a feature branch, add the branch as a separate agent source:

```bash
claude-mpm agent-source add https://github.com/bobmatnyc/claude-mpm-agents \
  --branch my-feature-branch
```

This creates a separate source entry with identifier `bobmatnyc/claude-mpm-agents/my-feature-branch/agents`. The branch's agents are cached independently from the `main` branch, so both can coexist.

Options:
- `--subdirectory <path>` — Subdirectory containing agents (default: `agents`)
- `--priority <int>` — Lower number = higher precedence (default: `100`)
- `--disabled` — Add but don't enable yet
- `--test` — Validate access without saving
- `--no-test` — Skip access validation (not recommended)

### Removing a branch-based agent source

When the feature branch is merged or no longer needed:

```bash
claude-mpm agent-source remove bobmatnyc/claude-mpm-agents/my-feature-branch/agents
```

The source identifier follows the pattern `{owner}/{repo}/{branch}/{subdirectory}`. To find the exact identifier, list all sources:

```bash
claude-mpm agent-source list
```

Add `--force` to skip the confirmation prompt:

```bash
claude-mpm agent-source remove bobmatnyc/claude-mpm-agents/my-feature-branch/agents --force
```

### Forcing an agent sync

By default, claude-mpm syncs agent sources once every 24 hours (TTL-gated). To force an immediate sync that bypasses the TTL:

```bash
claude-mpm --force-sync
```

This flag applies to the normal startup pipeline — it forces both agent and skill syncs to re-fetch from remote sources regardless of cache freshness. It also re-evaluates manifest compatibility.

You can also force-sync a specific source using the `agent-source update` command:

```bash
# Force update a specific source
claude-mpm agent-source update bobmatnyc/claude-mpm-agents/main/agents --force

# Force update all enabled sources
claude-mpm agent-source update --force
```

Alternatively, set the environment variable `CLAUDE_MPM_SYNC_TTL=0` to always sync on every startup, or `CLAUDE_MPM_FORCE_SYNC=1` for a one-time forced sync.

## Developing with the Versioning System

### For agent repository maintainers

#### Adding a manifest to your repository

1. Create `agents-manifest.yaml` at the repository root (sibling to `agents/`, not inside it)
2. Start with the minimal fields:

```yaml
repo_format_version: 1
min_cli_version: "5.9.0"
```

3. Commit and push. On the next sync, CLI versions below 5.9.0 will see a warning.

#### Making a breaking change to agents

1. Make the agent template changes on a feature branch
2. Update `min_cli_version` in `agents-manifest.yaml` to the CLI version that supports the change
3. If the change is structural (new metadata format, new file layout), consider whether `repo_format_version` needs to increment
4. Add `migration_notes` explaining what changed and what users need to do
5. Test by adding the branch as an agent source:

```bash
claude-mpm agent-source add https://github.com/your-org/your-agents \
  --branch breaking-change-branch
claude-mpm --force-sync
```

6. Verify that:
   - The manifest is fetched (check debug logs: `CLAUDE_MPM_LOG_LEVEL=DEBUG`)
   - The compatibility check produces the expected result
   - Console warnings appear for older CLI versions
7. Merge the branch. Users on older CLIs will see the upgrade warning; users on newer CLIs sync normally.

#### When to use `repo_format_version` vs. `min_cli_version`

| Change type | Use | Example |
|-------------|-----|---------|
| New agent template using existing features | `min_cli_version` | Agent uses a metadata field added in 5.10.0 |
| Structural change to agent file layout | `min_cli_version` | Agents moved from flat to nested directory |
| Breaking change to manifest format itself | `repo_format_version` | New mandatory manifest fields that old CLIs would ignore |

`repo_format_version` should only be incremented for changes to how the CLI **parses the manifest itself**. For all other compatibility constraints, use `min_cli_version` or `compatibility_ranges`.

### For claude-mpm CLI developers

#### Key source files

| File | Purpose |
|------|---------|
| `services/agents/compatibility/__init__.py` | Package exports |
| `services/agents/compatibility/manifest_checker.py` | Core decision matrix logic |
| `services/agents/compatibility/manifest_fetcher.py` | HTTP/local fetch with URL normalization |
| `services/agents/compatibility/manifest_cache.py` | SQLite persistence for offline/deploy-time use |
| `services/agents/compatibility/deploy_gate.py` | Deploy-time re-validation |
| `services/agents/sources/git_source_sync_service.py` | Integration point: calls `_check_manifest_compatibility()` |
| `cli/startup.py` | Console warning display (`_display_manifest_compatibility_warnings`) |

#### Incrementing `MAX_SUPPORTED_REPO_FORMAT`

When adding support for a new manifest format version:

1. Update `ManifestChecker.MAX_SUPPORTED_REPO_FORMAT` to the new value
2. Add parsing logic for any new fields
3. Ensure backward compatibility with older manifest versions (format version 1 manifests must still work)
4. Add tests covering the new format version

#### Cache and state locations

| Path | Purpose |
|------|---------|
| `~/.claude-mpm/cache/manifest_cache.db` | SQLite manifest cache (compatibility results + raw content) |
| `~/.claude-mpm/cache/sync-state.json` | TTL timestamps for sync gating |
| `~/.claude-mpm/config/agent_sources.yaml` | Agent source repository configuration |

#### Environment variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `CLAUDE_MPM_SYNC_TTL` | Sync interval in seconds (`0` = always sync) | `86400` (24h) |
| `CLAUDE_MPM_FORCE_SYNC` | Set to `1` or `true` to force sync on next startup | `0` |
| `CLAUDE_MPM_SKIP_MANIFEST_CHECK` | Set to `true` to skip manifest compatibility checks | unset |

## Supported Repository Hosts

The `ManifestFetcher` resolves the manifest URL from the agent source URL. Supported hosts:

| Host | Source URL form | Manifest resolved at |
|------|----------------|---------------------|
| GitHub | `https://raw.githubusercontent.com/{owner}/{repo}/{branch}[/subdir]` | `…/{owner}/{repo}/{branch}/agents-manifest.yaml` |
| GitLab | `https://gitlab.com/{owner}/{repo}/-/raw/{branch}[/subdir]` | `…/{owner}/{repo}/-/raw/{branch}/agents-manifest.yaml` |
| Bitbucket | `https://bitbucket.org/{owner}/{repo}/raw/{branch}[/subdir]` | `…/{owner}/{repo}/raw/{branch}/agents-manifest.yaml` |
| Local | `/absolute/path` or `file:///absolute/path` | `{path}/agents-manifest.yaml` |

The subdirectory portion of the source URL is always stripped so the manifest is fetched from the repository/branch root, not from within the agents directory.

## Troubleshooting

### "Repository manifest format version X is not supported"

This is a **hard block**. The agent repository uses a manifest format version that your CLI does not understand.

**Fix**: Upgrade claude-mpm:
```bash
pip install --upgrade claude-mpm
```

### "This agent repository requires claude-mpm >= X.Y.Z"

This is a **soft warning**. Agents are still synced but may not work correctly.

**Fix**: Upgrade claude-mpm to the version shown in the warning.

### Manifest not being detected

1. Verify the file is named exactly `agents-manifest.yaml` (not `manifest.yaml` or `agents_manifest.yaml`)
2. Verify it is at the repository root, not inside the `agents/` subdirectory
3. Check debug logs: `CLAUDE_MPM_LOG_LEVEL=DEBUG claude-mpm --force-sync`
4. Look for log lines containing "manifest" to trace the fetch and check flow

### Bypassing manifest checks

For development or emergencies, skip manifest checks entirely:

```bash
CLAUDE_MPM_SKIP_MANIFEST_CHECK=true claude-mpm --force-sync
```

This sets the environment variable for a single invocation. Do not use this in production.

## See Also

- [Agent System Overview](README.md) — Agent system documentation index
- [Creating Agents](creating-agents.md) — How to create custom agents
- [Remote Agents](remote-agents.md) — Git-based remote agent sources
- [Version Policy](../getting-started/VERSION_POLICY.md) — PM instructions versioning (separate system)
