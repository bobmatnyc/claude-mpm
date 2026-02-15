# Dashboard Config UI: No multi-project awareness — single port serves one project's data

**Priority:** High
**Labels:** enhancement, dashboard, phase-4, multi-project

## Problem

The dashboard server (`UnifiedMonitorServer`) binds to a single port (8765) and serves configuration data from whichever project root started the server. This creates several issues when multiple claude-mpm instances run across different projects.

### Specific Issues

1. **Port conflict**: Only one dashboard server can bind to 8765. The first project wins; subsequent projects get "port in use" and run without a dashboard.

2. **Wrong project data**: If project A's server is running and you're working in project B, `localhost:8765` shows project A's agents, skills, and configuration — not project B's.

3. **Skills are global, agents are local**: Deploy/undeploy skills via the UI affects `~/.claude/skills/` (shared across ALL projects), while agent deploy/undeploy only affects `.claude/agents/` of the server-owning project. This asymmetry is confusing and potentially dangerous.

4. **No project selector**: The Config tab has no awareness of which project it's serving. There's no indicator, selector, or warning about which project context is active.

### Impact

- Phase 3 deploy/undeploy operations silently act on whichever project owns the running server
- Users could undeploy agents from the wrong project
- Skill deployment affects all projects globally with no project-scoped option

### Paths to Resolution

| Approach | Effort | Tradeoffs |
|----------|--------|-----------|
| Dynamic port per project (hash of project path) | Low | Solves port conflict but user must know which port |
| Project indicator banner in dashboard | Low | Doesn't solve the problem but makes it visible |
| Project selector in Config tab | Medium | Requires service re-initialization per project switch |
| Multi-project registry with shared server | High | Single server manages all projects, cleanest UX |

### Suggested Minimum Fix (Phase 4)

1. Display the active project path prominently in the Config tab header
2. Show a warning banner when the dashboard's project differs from the most recently active CLI session
3. Add `project_root` to all config API responses so the frontend can verify context

### Context

Discovered during Phase 3 implementation (deployment operations). The Phase 0-2 read-only dashboard had minimal risk from this limitation, but Phase 3's destructive operations (deploy, undeploy, mode switch) make it a real concern.
