# Startup Migrations

## Overview

Claude MPM includes an automatic migration system that runs on first startup after an update. Migrations handle configuration changes, cache directory restructuring, and other one-time fixes needed between versions.

## How It Works

### When Migrations Run

Migrations execute automatically during startup:
1. **First in startup sequence** - Before agent sync or any other operations
2. **Once per installation** - Each migration runs only once
3. **Tracked persistently** - Completed migrations are recorded in `~/.claude-mpm/migrations.yaml`

### Design Principles

- **Non-blocking**: Migration failures log warnings but do not stop startup
- **Idempotent**: Safe to run multiple times (condition checked before migrating)
- **Tracked**: Each migration has a unique ID and runs only once
- **Early**: Runs before agent sync to ensure correct configuration

## What Gets Migrated

Migrations handle various configuration and cache updates:

| Migration ID | Version | Description |
|--------------|---------|-------------|
| `v5.6.76-cache-dir-rename` | 5.6.76 | Renames `remote-agents/` to `agents/` in cache directory |

### v5.6.76-cache-dir-rename

This migration:
1. Moves `~/.claude-mpm/cache/remote-agents/` contents to `~/.claude-mpm/cache/agents/`
2. Removes the old `remote-agents` directory
3. Updates `configuration.yaml` if it references the old path

## Migration History

Completed migrations are tracked in `~/.claude-mpm/migrations.yaml`:

```yaml
migrations:
  - id: v5.6.76-cache-dir-rename
    completed_at: '2026-01-23T10:30:00.000000+00:00'
```

## User Experience

When migrations apply, you will see a notification during startup:

```
Starting startup services...
Running startup migration: Rename remote-agents cache dir to agents
Syncing agents from 1 remote sources...
```

If no migrations are needed (already completed or conditions don't apply), startup proceeds silently without any migration messages.

## Troubleshooting

### Migration Failed

If a migration fails, you will see a warning in the logs:

```
[WARNING] Migration v5.6.76-cache-dir-rename failed
```

**What to do:**
- The failure is non-blocking; startup continues normally
- Check the log file at `~/.claude-mpm/logs/claude-mpm.log` for details
- Most failures are due to permission issues or file locks
- Manually perform the migration if needed (see specific migration docs)

### Force Re-run a Migration

To re-run a migration:
1. Edit `~/.claude-mpm/migrations.yaml`
2. Remove the entry for the specific migration
3. Restart claude-mpm

```bash
# Example: Remove cache-dir-rename migration to re-run it
sed -i '' '/v5.6.76-cache-dir-rename/d' ~/.claude-mpm/migrations.yaml
```

### Check Migration Status

View completed migrations:

```bash
cat ~/.claude-mpm/migrations.yaml
```

## For Developers: Adding New Migrations

To add a new migration, edit `src/claude_mpm/cli/startup_migrations.py`:

### 1. Define Check and Migrate Functions

```python
def _check_my_migration_needed() -> bool:
    """Check if migration is needed.

    Returns:
        True if migration should run.
    """
    # Check condition (e.g., old file exists)
    return Path.home() / ".claude-mpm" / "old_file.yaml".exists()


def _migrate_my_migration() -> bool:
    """Perform the migration.

    Returns:
        True if migration succeeded.
    """
    try:
        # Perform migration steps
        old_file = Path.home() / ".claude-mpm" / "old_file.yaml"
        new_file = Path.home() / ".claude-mpm" / "new_file.yaml"
        shutil.move(str(old_file), str(new_file))
        return True
    except Exception as e:
        logger.warning(f"Migration failed: {e}")
        return False
```

### 2. Register the Migration

Add to the `MIGRATIONS` list:

```python
MIGRATIONS: list[Migration] = [
    # Existing migrations...
    Migration(
        id="v5.7.0-my-migration",
        description="Description shown during startup",
        check=_check_my_migration_needed,
        migrate=_migrate_my_migration,
    ),
]
```

### 3. Migration ID Convention

Use the format: `v{VERSION}-{short-description}`

Examples:
- `v5.6.76-cache-dir-rename`
- `v5.7.0-config-schema-update`
- `v6.0.0-major-restructure`

### 4. Best Practices

- **Always check first**: The `check` function should return `False` if migration is not needed
- **Handle errors gracefully**: Catch exceptions and return `False` on failure
- **Log appropriately**: Use `logger.debug()` for success details, `logger.warning()` for failures
- **Keep migrations focused**: One logical change per migration
- **Test thoroughly**: Add tests in `tests/cli/test_startup_migrations.py`

## Related Files

- **Implementation**: `src/claude_mpm/cli/startup_migrations.py`
- **Integration**: `src/claude_mpm/cli/startup.py`
- **Tests**: `tests/cli/test_startup_migrations.py`
- **Tracking**: `~/.claude-mpm/migrations.yaml`
