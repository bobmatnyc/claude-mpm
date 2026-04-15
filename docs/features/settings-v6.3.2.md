# Settings Updates in v6.3.2

## Overview

Claude MPM v6.3.2 introduces two important settings enhancements:

1. **`permissions.additionalDirectories` migration** — Automatically grants file access permissions to specified directories
2. **`autoMemoryEnabled: true`** — Enables automatic kuzu-memory integration by default in the settings template

These settings are registered via the v6.3.2 startup migration and provide better access control and memory management capabilities.

## Permissions: additionalDirectories

### Purpose

The `permissions.additionalDirectories` setting allows users to explicitly grant Claude Code file access to additional directories beyond the project root.

### Configuration

#### In `.claude/settings.json` (team settings)

```json
{
  "permissions": {
    "additionalDirectories": [
      "/Users/masa/Projects/shared-library",
      "/opt/local/tools",
      "~/Documents/research"
    ]
  }
}
```

#### In `.claude/settings.local.json` (personal override)

```json
{
  "permissions": {
    "additionalDirectories": [
      "/Users/masa/Projects/personal-scripts"
    ]
  }
}
```

### Usage Examples

#### Single Additional Directory

```json
{
  "permissions": {
    "additionalDirectories": [
      "/Users/masa/Projects/shared-library"
    ]
  }
}
```

#### Multiple Directories

```json
{
  "permissions": {
    "additionalDirectories": [
      "/Users/masa/Projects/shared-library",
      "/opt/local/tools",
      "~/Documents/research",
      "/home/user/workspace/tools"
    ]
  }
}
```

#### With Absolute and Relative Paths

```json
{
  "permissions": {
    "additionalDirectories": [
      "/absolute/path/to/directory",
      "~/home-relative/directory",
      "../relative/from/project/root"
    ]
  }
}
```

### Path Resolution

Paths are resolved in order:

1. **Absolute paths**: Used as-is (`/Users/masa/Projects/...`)
2. **Home-relative paths**: Expanded using `~` (`~/Documents/...`)
3. **Relative paths**: Resolved from project root (`../other-project/...`)

### Migration: v6.3.2-permissions-directories

The v6.3.2 startup migration:

1. **Checks for existing settings** in `.claude/settings.json`
2. **Adds `permissions.additionalDirectories`** if not present
3. **Preserves existing permissions** (no overwrites)
4. **Idempotent** — Safe to run multiple times

### Use Cases

#### Monorepo Projects

Grant access to shared packages in a monorepo:

```json
{
  "permissions": {
    "additionalDirectories": [
      "../shared-packages",
      "../tools",
      "../types"
    ]
  }
}
```

#### Shared Development Tools

Grant access to organization-wide tools:

```json
{
  "permissions": {
    "additionalDirectories": [
      "/opt/org/build-tools",
      "/opt/org/deployment-scripts",
      "/opt/org/shared-templates"
    ]
  }
}
```

#### Research and Documentation

Grant access to shared documentation:

```json
{
  "permissions": {
    "additionalDirectories": [
      "~/Documents/architecture",
      "~/Documents/specifications",
      "~/Documents/research-notes"
    ]
  }
}
```

### Verification

Check if directories have been added to settings:

```bash
# View settings
cat .claude/settings.json | jq '.permissions.additionalDirectories'

# Expected output:
# [
#   "/Users/masa/Projects/shared-library",
#   "~/Documents/research"
# ]
```

### Troubleshooting

#### Directory Not Accessible

If Claude Code cannot access a directory:

1. **Verify the path exists**:
   ```bash
   ls -la /path/to/directory
   ```

2. **Check permissions**:
   ```bash
   stat /path/to/directory
   ```

3. **Verify settings are correct**:
   ```bash
   cat .claude/settings.json | jq '.permissions'
   ```

4. **Reload Claude Code**: Changes to settings require restart

#### Path Resolution Issues

- **Absolute paths**: Must start with `/`
- **Home paths**: Use `~` (expands to `$HOME`)
- **Relative paths**: Start with `../` or `./`

---

## Auto Memory: autoMemoryEnabled

### Purpose

The `autoMemoryEnabled: true` setting enables automatic kuzu-memory integration, ensuring that session context and learnings are automatically persisted without manual configuration.

### Configuration

#### In Settings Template (v6.3.2+)

```json
{
  "memory": {
    "autoMemoryEnabled": true,
    "provider": "kuzu-memory",
    "persistenceStrategy": "automatic"
  }
}
```

#### In `.claude/settings.json`

```json
{
  "memory": {
    "autoMemoryEnabled": true
  }
}
```

### What It Does

When `autoMemoryEnabled: true`:

1. **Automatic persistence**: Session context is automatically saved to kuzu-memory
2. **Memory consolidation**: On session end, memories are consolidated and archived
3. **Context injection**: Previous session context is automatically loaded
4. **No manual configuration**: Works out-of-the-box without additional setup

### Behavior

**Session Start**:
- Automatically loads saved context from kuzu-memory
- Injects previous session learnings
- Restores agent metadata

**During Session**:
- Continuously saves observations to kuzu-memory
- Tracks learnings and decisions
- Updates session memory asynchronously

**Session End**:
- Consolidates all session memories
- Archives learnings for future sessions
- Triggers `SessionEnd` hook for cleanup

### Example: Automatic Memory Flow

```
Session 1: User works on authentication task
    ↓
[autoMemoryEnabled: true]
    ↓
Learnings saved: "OAuth2 implementation pattern", "JWT validation"
    ↓
Session ends → Memories consolidated
────────────────────────────────

Session 2: User works on another task
    ↓
[autoMemoryEnabled: true]
    ↓
Previous session context loaded: "OAuth2 pattern", "JWT validation"
    ↓
New context is available to Claude Code agents
```

### Configuration Options

```json
{
  "memory": {
    "autoMemoryEnabled": true,
    "provider": "kuzu-memory",
    "persistenceStrategy": "automatic",
    "autoConsolidateInterval": 300,
    "archiveInterval": 86400,
    "retentionDays": 90
  }
}
```

**Options**:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `autoMemoryEnabled` | boolean | `true` (v6.3.2+) | Enable automatic memory persistence |
| `provider` | string | `kuzu-memory` | Memory backend provider |
| `persistenceStrategy` | string | `automatic` | How memories are saved (automatic/manual) |
| `autoConsolidateInterval` | integer | `300` | Seconds between auto-consolidation |
| `archiveInterval` | integer | `86400` | Seconds between archival (24 hours) |
| `retentionDays` | integer | `90` | How long to keep archived memories |

### Migration: v6.3.2-auto-memory-template

The v6.3.2 startup migration:

1. **Updates settings template** to include `autoMemoryEnabled: true`
2. **Enables memory integration** if kuzu-memory is available
3. **Preserves custom memory settings** (no overwrites)
4. **Idempotent** — Safe to run multiple times

### Use Cases

#### Development Sessions

Enable automatic context persistence for development work:

```json
{
  "memory": {
    "autoMemoryEnabled": true
  }
}
```

#### Long-Running Projects

Maintain context across multiple sessions:

```json
{
  "memory": {
    "autoMemoryEnabled": true,
    "archiveInterval": 43200,
    "retentionDays": 180
  }
}
```

#### Research and Exploration

Track learnings across investigative sessions:

```json
{
  "memory": {
    "autoMemoryEnabled": true,
    "persistenceStrategy": "automatic",
    "autoConsolidateInterval": 600
  }
}
```

### Verification

Check if automatic memory is enabled:

```bash
# View memory settings
cat .claude/settings.json | jq '.memory'

# Expected output:
# {
#   "autoMemoryEnabled": true,
#   "provider": "kuzu-memory"
# }
```

### Troubleshooting

#### Memory Not Persisting

1. **Check kuzu-memory is installed**:
   ```bash
   which kuzu-memory
   ```

2. **Verify settings are enabled**:
   ```bash
   cat .claude/settings.json | jq '.memory.autoMemoryEnabled'
   ```

3. **Check kuzu-memory logs**:
   ```bash
   tail -f ~/.claude-mpm/logs/kuzu-memory.log
   ```

4. **Restart Claude Code**: Changes require reload

#### Context Not Loading

1. **Check if memories exist**:
   ```bash
   ls -la ~/.kuzu-memory/
   ```

2. **Verify session context was saved**:
   ```bash
   kuzu-memory list-sessions
   ```

3. **Force consolidation** (if needed):
   ```bash
   kuzu-memory consolidate-memories
   ```

## Configuration Hierarchy

Both settings follow the configuration hierarchy:

1. **Managed settings** (MDM) — org-enforced, cannot override
2. **Project settings** — `.claude/settings.local.json` (highest priority)
3. **Team settings** — `.claude/settings.json`
4. **Global settings** — `~/.claude/settings.json`
5. **Built-in defaults** — MPM defaults

### Example: Override Team Settings

Team sets default (team settings):
```json
{
  "memory": {
    "autoMemoryEnabled": true
  }
}
```

User overrides locally (local settings):
```json
{
  "memory": {
    "autoMemoryEnabled": false
  }
}
```

**Result**: User's local setting takes precedence

## Related Documentation

- [Settings Configuration](../configuration/reference.md)
- [Permissions System](../guides/permissions.md)
- [kuzu-memory Integration](../integrations/kuzu-memory.md)
- [Startup Migrations](./startup-migrations.md)

## Related Files

- **Settings Template**: `.claude/settings.json`
- **Local Overrides**: `.claude/settings.local.json`
- **Migration**: `src/claude_mpm/migrations/v6_3_2_*.py`
- **Configuration**: `src/claude_mpm/config/`
