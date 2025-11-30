---
namespace: mpm/agents
command: list
aliases: [mpm-agents]
migration_target: /mpm/agents:list
category: agents
deprecated_aliases: []
deprecated: true
replacement: mpm-agents-list
description: ⚠️ DEPRECATED - Use /mpm-agents-list instead
---
# ⚠️ DEPRECATED: Use `/mpm-agents-list` instead

This command has been renamed for better organization.

**Old Command**: `/mpm-agents`
**New Command**: `/mpm-agents-list`
**Future Command**: `/mpm/agents:list` (when Claude Code supports hierarchical namespaces)

This alias will be removed in Claude MPM v5.1.0.

---

## Migration Information

**Ticket**: 1M-400 - Phase 1 Enhanced Flat Naming with Namespace Metadata

This command has been restructured as part of the hierarchical namespace migration. Please update your workflows to use the new command name.

## What This Command Does

List all available Claude MPM agents with their versions and deployment status.

For full documentation, use `/mpm-agents-list`.
