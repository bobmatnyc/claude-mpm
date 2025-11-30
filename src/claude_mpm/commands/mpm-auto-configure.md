---
namespace: mpm/agents
command: auto-configure
aliases: [mpm-auto-configure]
migration_target: /mpm/agents:auto-configure
category: agents
deprecated_aliases: []
deprecated: true
replacement: mpm-agents-auto-configure
description: ⚠️ DEPRECATED - Use /mpm-agents-auto-configure instead
---
# ⚠️ DEPRECATED: Use `/mpm-agents-auto-configure` instead

This command has been renamed for better organization.

**Old Command**: `/mpm-auto-configure`
**New Command**: `/mpm-agents-auto-configure`
**Future Command**: `/mpm/agents:auto-configure` (when Claude Code supports hierarchical namespaces)

This alias will be removed in Claude MPM v5.1.0.

---

## Migration Information

**Ticket**: 1M-400 - Phase 1 Enhanced Flat Naming with Namespace Metadata

This command has been restructured as part of the hierarchical namespace migration. Please update your workflows to use the new command name.

## What This Command Does

Automatically detect your project's toolchain and configure the most appropriate agents.

For full documentation, use `/mpm-agents-auto-configure`.
