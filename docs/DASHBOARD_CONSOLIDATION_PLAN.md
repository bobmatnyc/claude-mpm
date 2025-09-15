# Dashboard Consolidation Plan

## Executive Summary

This document provides a comprehensive analysis of all dashboard files in the Claude MPM project and a detailed plan to consolidate them into a unified, maintainable structure with clear separation between legacy and new implementations.

## Current Dashboard Inventory

### Production Dashboards (7 files)

#### Main Entry Points
1. **`/src/claude_mpm/dashboard/templates/index.html`**
   - Title: "Claude MPM Socket.IO Dashboard"
   - Main production dashboard served at root `/`
   - Full-featured with all tabs (Activity, Code, Agents, Tools, Files, Events)
   - Uses vanilla JavaScript components

2. **`/src/claude_mpm/dashboard/static/index.html`**
   - Title: "Claude MPM Dashboard Hub"
   - Dashboard navigation hub
   - Provides links to different dashboard views
   - Clean landing page design

#### Feature-Specific Dashboards
3. **`/src/claude_mpm/dashboard/static/events.html`**
   - Title: "Claude MPM - Events Dashboard"
   - Dedicated events viewer
   - Real-time event streaming
   - Filtering and search capabilities

4. **`/src/claude_mpm/dashboard/static/monitors.html`**
   - Title: "Claude MPM - Dashboard Monitors"
   - Multiple monitor layouts
   - Grid view for different aspects

5. **`/src/claude_mpm/dashboard/static/monitors-index.html`**
   - Title: "Claude MPM - Monitor Dashboard"
   - Alternative monitor entry point

#### Legacy Dashboards (4 files)
Already properly organized in `/static/legacy/`:
- `activity.html` - Activity monitoring
- `agents.html` - Agent management
- `files.html` - File tracking
- `tools.html` - Tools monitoring

### Test & Development Dashboards (30+ files)

#### Test Archive (5 files in `/static/test-archive/`)
- `dashboard.html` - Old main dashboard backup
- `debug-events.html` - Event debugging
- `test_debug.html` - Debug utilities
- `test-navigation.html` - Navigation testing
- `test-react-exports.html` - React export testing

#### Root Directory Test Files (15 files)
Temporary test files that should be removed:
- `activity_dashboard_fixed.html`
- `activity_dashboard_test.html`
- `test_activity_connection.html`
- `test_claude_tree_tab.html`
- `test_dashboard.html`
- `test_dashboard_fixed.html`
- `test_dashboard_verification.html`
- `test_file_data.html`
- `test_file_tree_*.html` (multiple)
- `test_file_viewer.html`
- `test_final_activity.html`
- `test_tab_fix.html`

#### Tools Directory (5 files)
Development utilities in `/tools/dev/misc/`:
- `claude_mpm_monitor.html`
- `debug_dashboard.html`
- `diagnostic_dashboard_namespace_test.html`
- `websocket_memory_monitor.html`
- `websocket_monitor.html`

#### Tests Directory (20+ files)
Various test dashboards for different features

### React Components (New Implementation)

Located in `/src/claude_mpm/dashboard/react/`:
- **Entries**: `events.tsx` - React event viewer
- **Components**: ErrorBoundary, EventViewer, DataInspector, shared components
- **Contexts**: DashboardContext for state management
- **Hooks**: Custom React hooks
- **Utils**: Utility functions

### JavaScript Components (28 files)

Located in `/src/claude_mpm/dashboard/static/js/components/`:
- Core components: activity-tree, agent-hierarchy, code-tree, event-viewer
- UI managers: session-manager, socket-manager, ui-state-manager
- Viewers: code-viewer, diff-viewer, file-viewer, module-viewer
- Trackers: build-tracker, file-change-tracker, file-tool-tracker
- Utilities: event-processor, export-manager, working-directory

## Categorization

### By Technology Stack

1. **Vanilla JavaScript Dashboards** (Production)
   - Main dashboard (`templates/index.html`)
   - Feature dashboards (events, monitors)
   - Legacy dashboards (already organized)

2. **React-Based Dashboards** (New)
   - React event viewer
   - Component library being developed
   - Modern state management with contexts

3. **Test/Development Dashboards**
   - Should not be in production
   - Mix of technologies for testing

### By Purpose

1. **Main Dashboard** - Full-featured monitoring
2. **Event Monitoring** - Real-time event streams
3. **Activity Tracking** - Session and activity visualization
4. **Agent Management** - Agent hierarchy and status
5. **File Operations** - File tracking and changes
6. **Tools Monitoring** - Tool usage and correlation
7. **Development/Debug** - Testing and debugging utilities

## Consolidation Plan

### Phase 1: Directory Structure Reorganization

```
src/claude_mpm/dashboard/
├── static/
│   ├── index.html                 # Main hub/landing page
│   ├── dashboard.html              # Main full-featured dashboard
│   ├── events.html                 # Events-only view
│   ├── monitors.html               # Multi-monitor view
│   │
│   ├── legacy/                     # [KEEP AS-IS]
│   │   ├── activity.html
│   │   ├── agents.html
│   │   ├── files.html
│   │   └── tools.html
│   │
│   ├── js/                         # [KEEP AS-IS]
│   │   ├── components/             # Vanilla JS components
│   │   └── stores/                 # State management
│   │
│   ├── css/                        # [KEEP AS-IS]
│   │
│   └── built/                      # [KEEP AS-IS]
│       └── react/                  # React build output
│
├── react/                          # [KEEP AS-IS] React source
│
├── templates/
│   └── index.html                  # Server-rendered template
│
└── archive/                        # [NEW] Move test files here
    ├── test-archive/
    └── development/
```

### Phase 2: File Movements

#### Files to Move to Archive
1. Move all root directory test HTML files to `/archive/testing/`
2. Move `/static/test-archive/` contents to `/archive/test-archive/`
3. Keep development tools in `/tools/dev/misc/` (external to dashboard)

#### Files to Delete (Redundant)
- Duplicate test files with similar names
- Temporary debugging files
- Old backup files

#### Files to Consolidate
1. Merge `monitors.html` and `monitors-index.html` into single monitor dashboard
2. Update main hub (`static/index.html`) to provide clear navigation

### Phase 3: Navigation Structure

#### New URL Mapping

```
/                       → Main dashboard (templates/index.html)
/dashboard             → Alternative main dashboard route
/hub                   → Dashboard hub/selector (static/index.html)
/events                → Events dashboard
/monitors              → Unified monitors view

/legacy/               → Legacy dashboard section
/legacy/activity       → Activity dashboard
/legacy/agents         → Agents dashboard
/legacy/files          → Files dashboard
/legacy/tools          → Tools dashboard

/api/*                 → API endpoints (unchanged)
/static/*              → Static resources (unchanged)
```

#### Navigation Menu Structure

```yaml
Main Navigation:
  - Dashboard (Main)
    - Full Dashboard
    - Events View
    - Monitors Grid

  - Legacy Dashboards
    - Activity Monitor
    - Agent Manager
    - File Tracker
    - Tools Monitor

  - Developer Tools
    - API Documentation
    - WebSocket Monitor
    - Debug Console
```

### Phase 4: Implementation Steps

1. **Create Archive Directory**
   ```bash
   mkdir -p src/claude_mpm/dashboard/archive/{testing,development,test-archive}
   ```

2. **Move Test Files**
   - Move root test files to archive
   - Move test-archive contents
   - Update any references

3. **Consolidate Monitor Dashboards**
   - Merge monitors.html and monitors-index.html
   - Update navigation links

4. **Update Main Hub**
   - Redesign static/index.html as central navigation
   - Add clear sections for production vs legacy
   - Include version information

5. **Update Server Routes**
   - Add new route mappings
   - Implement redirects for backward compatibility
   - Update static file serving

6. **Update Documentation**
   - Document new structure
   - Update README files
   - Create migration guide

## Testing Requirements

### Pre-Consolidation Testing
1. ✓ List all current dashboard URLs
2. ✓ Document which dashboards are actively used
3. ✓ Test each dashboard for basic functionality
4. ✓ Identify broken dashboards

### Post-Consolidation Testing
1. Test all new URLs work correctly
2. Verify redirects for backward compatibility
3. Test navigation between sections
4. Verify no functionality lost
5. Test both legacy and new dashboards
6. Verify static resources load correctly

## Success Criteria

1. **Single Entry Point**: Clear main dashboard at `/`
2. **Organized Structure**: Clean separation of production, legacy, and archive
3. **Clear Navigation**: Easy to navigate between different views
4. **Backward Compatibility**: Existing URLs redirect appropriately
5. **No Lost Functionality**: All features remain accessible
6. **Reduced Clutter**: Test files moved out of production paths
7. **Documentation**: Clear documentation of new structure

## Risk Mitigation

1. **Backup Current State**: Create full backup before changes
2. **Gradual Migration**: Implement in phases with testing
3. **Maintain Redirects**: Keep old URLs working via redirects
4. **Version Control**: Commit after each phase
5. **Rollback Plan**: Document how to revert if needed

## Timeline

- **Phase 1**: Directory structure (1 hour)
- **Phase 2**: File movements (2 hours)
- **Phase 3**: Navigation updates (2 hours)
- **Phase 4**: Testing and documentation (2 hours)

Total estimated time: 7 hours

## Conclusion

This consolidation plan will:
1. Reduce dashboard files from 50+ to ~10 production files
2. Create clear separation between production and test
3. Provide unified navigation experience
4. Maintain all existing functionality
5. Prepare for future React migration
6. Improve maintainability and discoverability