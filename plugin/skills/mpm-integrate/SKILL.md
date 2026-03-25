---
description: "Manage API integrations for Claude MPM projects"
globs: "**/*"
alwaysApply: false
---

# MPM Integrate

Manage API integrations for Claude MPM projects.

## When to Use

- User says "list integrations" or "show available integrations"
- User says "add integration" or "install integration"
- User says "remove integration" or "uninstall integration"
- User says "check integration status"
- User says "call integration" or "execute operation"

## Commands

### List Integrations

Show available and installed integrations:

```bash
# Show both available and installed
mpm integrate list

# Show only available from catalog
mpm integrate list --available

# Show only installed
mpm integrate list --installed
```

### Add Integration

Install an integration from the catalog:

```bash
# Install to project scope (default)
mpm integrate add jsonplaceholder

# Install to user scope
mpm integrate add jsonplaceholder --scope user
```

### Remove Integration

Uninstall an integration:

```bash
# Remove from any scope
mpm integrate remove jsonplaceholder

# Remove from specific scope
mpm integrate remove jsonplaceholder --scope project
```

### Check Status

Check health of an installed integration:

```bash
mpm integrate status jsonplaceholder
```

### Call Operation

Execute an integration operation:

```bash
# Basic call
mpm integrate call jsonplaceholder list_posts

# With parameters
mpm integrate call jsonplaceholder get_post -p id=1
```

### Validate Manifest

Validate an integration manifest:

```bash
mpm integrate validate ./myintegration/
```

## Storage Locations

- **Project scope**: `.claude/integrations/` - Specific to current project
- **User scope**: `~/.claude-mpm/integrations/` - Available across all projects

## Creating Custom Integrations

1. Copy template: `src/claude_mpm/integrations/catalog/TEMPLATE.yaml`
2. Create directory: `myservice/integration.yaml`
3. Define operations, auth, and health check
4. Validate: `mpm integrate validate myservice/`
5. Add to catalog or install directly
