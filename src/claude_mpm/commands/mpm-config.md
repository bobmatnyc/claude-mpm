---
namespace: mpm/config
command: view
aliases: [mpm-config]
migration_target: /mpm/config:view
category: config
deprecated_aliases: []
deprecated: true
replacement: mpm-config-view
description: ⚠️ DEPRECATED - Use /mpm-config-view instead
---
# ⚠️ DEPRECATED: Use `/mpm-config-view` instead

This command has been renamed for better organization.

**Old Command**: `/mpm-config`
**New Command**: `/mpm-config-view`
**Future Command**: `/mpm/config:view` (when Claude Code supports hierarchical namespaces)

This alias will be removed in Claude MPM v5.1.0.

---

## Migration Information

**Ticket**: 1M-400 - Phase 1 Enhanced Flat Naming with Namespace Metadata

This command has been restructured as part of the hierarchical namespace migration. Please update your workflows to use the new command name.

## What This Command Does

View and validate Claude MPM configuration settings.

For full documentation, use `/mpm-config-view`.
