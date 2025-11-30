---
namespace: mpm/session
command: resume
aliases: [mpm-resume]
migration_target: /mpm/session:resume
category: session
deprecated_aliases: []
deprecated: true
replacement: mpm-session-resume
description: ⚠️ DEPRECATED - Use /mpm-session-resume instead
---
# ⚠️ DEPRECATED: Use `/mpm-session-resume` instead

This command has been renamed for better organization.

**Old Command**: `/mpm-resume`
**New Command**: `/mpm-session-resume`
**Future Command**: `/mpm/session:resume` (when Claude Code supports hierarchical namespaces)

This alias will be removed in Claude MPM v5.1.0.

---

## Migration Information

**Ticket**: 1M-400 - Phase 1 Enhanced Flat Naming with Namespace Metadata

This command has been restructured as part of the hierarchical namespace migration. Please update your workflows to use the new command name.

## What This Command Does

Load and display context from the most recent paused session to seamlessly continue your work.

For full documentation, use `/mpm-session-resume`.
