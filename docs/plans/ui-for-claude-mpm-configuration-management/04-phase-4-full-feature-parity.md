# Phase 4: Full Feature Parity & Advanced Features

> **Implementation Plan for Configuration Management UI**
>
> Date: 2026-02-13
> Branch: `ui-agents-skills-config`
> Status: Planning
> Risk Level: HIGHEST

---

## Table of Contents

1. [Phase Summary](#1-phase-summary)
2. [Feature Priority Matrix](#2-feature-priority-matrix)
3. [Feature Specifications](#3-feature-specifications)
4. [Pagination Strategy](#4-pagination-strategy)
5. [Testing Strategy](#5-testing-strategy)
6. [Performance Optimization](#6-performance-optimization)
7. [UX Design Considerations](#7-ux-design-considerations)
8. [What Stays CLI-Only](#8-what-stays-cli-only)
9. [Migration Path](#9-migration-path)
10. [Definition of Done](#10-definition-of-done)
11. [Devil's Advocate Summary](#11-devils-advocate-summary)
12. [Files Created/Modified](#12-files-createdmodified)
13. [Long-Term Roadmap Beyond Phase 4](#13-long-term-roadmap-beyond-phase-4)

---

## 1. Phase Summary

### Goal

Complete the configuration management UI to achieve full feature parity with the CLI for supported operations, plus introduce advanced features that go beyond what the CLI offers: visualization of skill-to-agent relationships, configuration history with restore, bulk operations, and import/export for team sharing.

### Approach: Incremental Feature Releases

Phase 4 is explicitly designed as a collection of **independent, shippable features** ordered by value/risk ratio. Each priority level (P1-P8) can be released on its own. There is no "big bang" release. This is critical because:

- Phase 4 has the highest risk level of all phases
- Features at the P6-P8 level are "nice to have" and can be cut without degrading the core experience
- Each feature adds complexity to both the frontend and backend; incremental releases allow monitoring of maintenance burden

### Timeline

| Priority | Feature | Estimated Effort |
|----------|---------|-----------------|
| P1 | Skill-to-Agent Linking Visualization | 1 week |
| P2 | Configuration Validation Display | 3 days |
| P3 | Configuration History/Versioning | 1 week |
| P4 | YAML Editor with Syntax Validation | 1 week |
| P5 | Bulk Operations | 3-5 days |
| P6 | Import/Export | 3-5 days |
| P7 | Collection Management | 3 days |
| P8 | Advanced Auto-Configure | 1 week |
| **Total** | | **4-6 weeks** |

### Risk Level: HIGHEST

Phase 4 introduces the most complex state management patterns in the entire UI:
- Bidirectional relationship visualization (P1)
- Temporal data with diff rendering (P3)
- In-browser code editing with real-time validation (P4)
- Multi-item selection with partial failure handling (P5)
- Cross-system data import with conflict resolution (P6)

Any of these features, implemented poorly, can cause data loss or configuration corruption. The incremental approach is a mandatory risk mitigation strategy, not a convenience.

### Dependencies

- **Phase 1** (read-only views): Must be complete -- provides the data layer
- **Phase 2** (source management + mutations): Must be complete -- provides file locking via `ConfigFileLock`, optimistic concurrency control, and Socket.IO event patterns for mutations
- **Phase 3** (deploy/undeploy + auto-configure): Must be complete -- provides the deploy/undeploy infrastructure that bulk operations (P5) and advanced auto-configure (P8) build upon

---

## 2. Feature Priority Matrix

| Feature | Priority | Effort | Value | Risk | Dependencies |
|---------|:--------:|:------:|:-----:|:----:|:-------------|
| Skill-to-Agent Linking Visualization | **P1** | 1 week | High | Medium | Endpoints #26-27 (already spec'd) |
| Configuration Validation Display | **P2** | 3 days | High | Low | `UnifiedConfig.validate()`, `ConfigurationService` |
| Configuration History/Versioning | **P3** | 1 week | Medium | High | `ConfigFileLock`, new storage system |
| YAML Editor with Syntax Validation | **P4** | 1 week | Medium | Medium | CodeMirror 6 or Monaco dependency |
| Bulk Operations | **P5** | 3-5 days | Medium | High | Phase 3 deploy/undeploy endpoints |
| Import/Export | **P6** | 3-5 days | Low-Medium | Medium | All config read endpoints |
| Collection Management | **P7** | 3 days | Low | Medium | `SkillsConfig` service |
| Advanced Auto-Configure | **P8** | 1 week | Low | High | Phase 3 auto-configure |

### Value/Risk Scoring Rationale

- **P1 (Skill-to-Agent Linking)**: Highest value because it exposes a relationship that is invisible in the CLI. Users currently have no way to visualize which skills serve which agents without reading YAML files manually. Medium risk because it is read-only.
- **P2 (Validation Display)**: High value because it surfaces configuration errors proactively. Low risk because the validation logic already exists in the service layer.
- **P3 (History)**: Medium value, high risk. The value is real (undo capability), but the risk of maintaining a parallel versioning system alongside git is substantial.
- **P4 (YAML Editor)**: Medium value as a power-user escape hatch. Medium risk due to the large dependency (CodeMirror/Monaco) and the potential for users to introduce syntax errors.
- **P5 (Bulk Operations)**: Medium value for efficiency. High risk because bulk undeploy of 20 agents is extremely destructive.
- **P6 (Import/Export)**: Low-medium value. Useful for team sharing but the use case is infrequent.
- **P7 (Collection Management)**: Low value because it overlaps with source management (Phase 2).
- **P8 (Advanced Auto-Configure)**: Low value because basic auto-configure (Phase 3) covers the primary use case. High risk due to "meta-complexity" of configuring configuration.

---

## 3. Feature Specifications

### P1 -- Skill-to-Agent Linking Visualization

#### Description and User Value

Provides a visual representation of the bidirectional mapping between skills and agents. Currently, this information is buried across YAML config files, agent frontmatter `skills:` fields, and inline content markers. The UI makes these relationships discoverable and navigable.

The research explicitly determined that a **matrix view is unusable** at the expected scale (40 agents x 200 skills = 8,000 cells). The chosen UX is a **dual-panel with chip-based assignment**.

#### API Endpoints

Both endpoints are already specified in the backend API spec (Group 5):

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/config/skill-links/` | Full bidirectional mapping with stats |
| GET | `/api/config/skill-links/agent/{agent_name}` | Per-agent skills (required, optional, from content markers) |

**Service layer**: `SkillToAgentMapper` -- in-memory bidirectional index built from YAML config. All `get_*` methods are async-safe (in-memory lookups, no I/O).

**Response structure** (from spec):

```json
{
    "success": true,
    "links": {
        "by_agent": {
            "python-engineer": {
                "frontmatter_skills": ["systematic-debugging", "python-core"],
                "content_marker_skills": ["mpm-delegation-patterns"],
                "total": 3
            }
        },
        "by_skill": {
            "systematic-debugging": {
                "agents": ["python-engineer", "typescript-engineer", "qa"],
                "source": "frontmatter"
            }
        }
    },
    "stats": {
        "total_skills": 85,
        "total_agents": 12,
        "avg_agents_per_skill": 3.2,
        "avg_skills_per_agent": 8.5
    }
}
```

#### Frontend Components

| Component | Purpose |
|-----------|---------|
| `SkillLinksView.svelte` | Top-level view (left panel tab content) |
| `AgentSkillPanel.svelte` | Left sub-panel: agent list with skill count badges |
| `SkillChipList.svelte` | Right sub-panel: chip-based skill display for selected agent |
| `SkillChip.svelte` | Individual chip: skill name, source indicator (auto/manual), removable (future) |

**Layout**: Dual-panel within the config section:
- **Left panel**: Scrollable agent list with search/filter input. Each agent row shows name + skill count badge.
- **Right panel**: When an agent is selected, shows assigned skills as chips. Each chip indicates its source (`frontmatter`, `content_marker`, `user_defined`). Auto-populated skills (BR-14) have an "auto-managed" visual indicator and cannot be manually removed.

#### Data Flow

```
User clicks agent in left panel
  -> SkillLinksView dispatches fetch to /api/config/skill-links/agent/{name}
  -> Response populates SkillChipList with categorized skills
  -> Chips render with source-specific styling
  -> Search/filter input debounces (300ms) and filters both panels client-side
```

Initial load fetches `/api/config/skill-links/` for the full mapping and stats, enabling the agent list to show accurate skill counts without per-agent requests.

#### Edge Cases

- Agent with zero skills: Show empty state with explanation ("No skills are linked to this agent")
- Skill referenced by agent frontmatter but not deployed: Show chip with warning indicator ("Skill not deployed -- agent may not function as expected")
- Unmapped skills (fallback to pattern inference): Show with different styling ("Inferred from naming pattern, not explicitly mapped")
- Agent in the mapping but not deployed: Gray out in agent list, show "(not deployed)" label
- Very large agent list (40+ agents): Requires search/filter; pagination if >100

#### Devil's Advocate Counterpoint

> "Read-only linking view may be sufficient for Phase 4. Write operations on the mapping are risky -- skill assignments are derived from multiple sources (frontmatter, content markers, user config). Allowing users to 'assign' a skill to an agent via the UI when that skill may also be auto-assigned by frontmatter creates a confusing dual-authority model. Consider keeping P1 read-only and deferring write operations to a future phase."

**Mitigation**: Phase 4 P1 is read-only. No write endpoints for skill-to-agent links are included. The UI clearly differentiates auto-managed skills from user-added skills but does not allow modification of auto-managed links.

#### Acceptance Criteria

- [ ] Agent list loads and displays all agents with skill count badges
- [ ] Selecting an agent shows its skills categorized by source (required, optional, content markers)
- [ ] Auto-populated skills (BR-14) are visually distinguished and show "auto-managed" indicator
- [ ] Search/filter works on both agent names and skill names
- [ ] Stats summary (total skills, total agents, averages) is displayed
- [ ] Undeployed skills referenced by agents show a warning indicator
- [ ] Empty states are handled gracefully
- [ ] Response time for full mapping is <500ms

---

### P2 -- Configuration Validation Display

#### Description and User Value

Surfaces configuration validation errors and warnings proactively. Instead of discovering issues at `claude-mpm init` time or when Claude Code fails to load an agent, users see a real-time health check of their configuration.

#### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/config/validate` | Run validation and return results |

**Service layer**: Delegates to `UnifiedConfig.validate()` and `ConfigurationService` validation methods. Also cross-references deployed agents against sources, and deployed skills against agent references.

**Response structure**:

```json
{
    "success": true,
    "valid": false,
    "issues": [
        {
            "severity": "error",
            "category": "agent",
            "path": "agents.python-engineer",
            "message": "Agent 'python-engineer' referenced by source 'my-agents' but not deployed",
            "suggestion": "Deploy the agent or remove the source reference"
        },
        {
            "severity": "warning",
            "category": "skill",
            "path": "skills.agent_referenced",
            "message": "Skill 'flask-framework' is in agent_referenced but no deployed agent requires it",
            "suggestion": "This skill may have been orphaned after an agent was undeployed"
        },
        {
            "severity": "info",
            "category": "config",
            "path": "network.socketio_port",
            "message": "Value overridden by environment variable CLAUDE_MPM_NETWORK__SOCKETIO_PORT",
            "suggestion": "The effective value is 9000, not the file value of 8765"
        }
    ],
    "summary": {
        "errors": 1,
        "warnings": 1,
        "info": 1
    }
}
```

#### Frontend Components

| Component | Purpose |
|-----------|---------|
| `ValidationPanel.svelte` | Displays validation results with severity grouping |
| `ValidationIssueCard.svelte` | Individual issue with severity icon, message, path, and suggestion |

**Layout**: Can be rendered as a collapsible panel in the config overview, or as a dedicated sub-tab. Shows a summary badge (e.g., "2 errors, 1 warning") that is visible even when the panel is collapsed.

#### Data Flow

```
Config tab loads or config changes detected (via Socket.IO config_updated event)
  -> Auto-fetch GET /api/config/validate
  -> Render issues grouped by severity (errors first, then warnings, then info)
  -> Each issue card is expandable to show full path and suggestion
  -> Clicking an issue navigates to the relevant config section (if applicable)
```

#### Edge Cases

- All valid: Show green "Configuration is healthy" state
- Environment variable overrides (Risk C-6): Show info-level issues for any value overridden by env var
- Dual config system drift (Risk C-7): Show warning if `UnifiedConfig` and `Config` singleton disagree
- Validation itself errors: Show error boundary, not blank panel

#### Devil's Advocate Counterpoint

> "Validation errors may be confusing if users don't understand the configuration model. Showing 'Agent foo referenced but not deployed' assumes the user knows what 'referenced' means (source config vs. deployed state vs. agent_sources.yaml). Without excellent error messages that explain the configuration model, the validation panel becomes noise rather than signal."

**Mitigation**: Every validation issue must include three parts: (1) what is wrong, (2) where it is (config path), and (3) what to do about it (actionable suggestion). The suggestion should use terminology from the UI, not internal service names.

#### Acceptance Criteria

- [ ] Validation runs automatically when the config tab opens
- [ ] Validation re-runs when config changes are detected via Socket.IO events
- [ ] Issues are grouped by severity with correct icons (error=red, warning=yellow, info=blue)
- [ ] Summary badge shows counts at a glance
- [ ] Each issue includes a human-readable message and actionable suggestion
- [ ] Environment variable overrides are surfaced as info-level issues
- [ ] Green "healthy" state displays when no issues exist
- [ ] Validation endpoint responds in <1s

---

### P3 -- Configuration History/Versioning

#### Description and User Value

Tracks all configuration changes with timestamp, source (UI/CLI), and before/after diff. Enables users to review what changed and restore a previous configuration state. This is the "undo" capability that configuration management inherently needs.

#### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/config/history/` | List history snapshots (paginated) |
| GET | `/api/config/history/{snapshot_id}` | Get a single snapshot with full diff |
| POST | `/api/config/history/{snapshot_id}/restore` | Restore configuration from a snapshot |

**New backend service**: `ConfigHistoryService`

**Storage**: `.claude-mpm/config-history/` directory with timestamped JSON snapshots.

**Snapshot schema**:

```json
{
    "id": "snap_20260213_143022_abc123",
    "timestamp": "2026-02-13T14:30:22Z",
    "operation": "agent_deploy",
    "source": "ui",
    "entity_type": "agent",
    "entity_id": "python-engineer",
    "changes": {
        "before": {
            "deployed": false,
            "source": null
        },
        "after": {
            "deployed": true,
            "source": "my-agents-repo"
        }
    },
    "config_files_affected": [
        ".claude/agents/python-engineer.md"
    ]
}
```

**Retention policy**: 30 days or 100 snapshots (whichever is reached first). Configurable via `configuration.yaml`.

#### Frontend Components

| Component | Purpose |
|-----------|---------|
| `HistoryTimeline.svelte` | Timeline view with scrollable list of snapshots |
| `HistoryEntry.svelte` | Individual entry: timestamp, operation, entity, expandable diff |
| `DiffViewer.svelte` | Before/after diff display (shared component, also used by P4 and P6) |
| `RestoreConfirmDialog.svelte` | Confirmation dialog showing what will change when restoring |

**Layout**: Vertical timeline on the left, detail panel on the right. Each timeline entry shows timestamp + operation type icon + entity name. Selecting an entry shows the full diff in the detail panel with a "Restore" button.

#### Data Flow

```
Config history tab selected
  -> Fetch GET /api/config/history/?limit=50&cursor=...
  -> Render timeline entries
  -> User clicks entry -> Fetch GET /api/config/history/{snapshot_id}
  -> Show before/after diff
  -> User clicks "Restore" -> Show RestoreConfirmDialog with preview
  -> User confirms -> POST /api/config/history/{snapshot_id}/restore
  -> Server validates snapshot, applies changes with ConfigFileLock
  -> Socket.IO broadcasts config_updated event
  -> UI refreshes all config views
```

#### Backend Implementation

```python
class ConfigHistoryService:
    """Tracks configuration changes as timestamped snapshots."""

    def __init__(self, history_dir: Path = None):
        self.history_dir = history_dir or Path.home() / ".claude-mpm" / "config-history"
        self.history_dir.mkdir(parents=True, exist_ok=True)
        self.max_snapshots = 100
        self.max_age_days = 30

    def record_change(self, operation: str, entity_type: str, entity_id: str,
                      before: dict, after: dict, source: str = "ui") -> str:
        """Create a snapshot. Called by all mutation endpoints."""
        # Generate snapshot ID, write JSON, enforce retention
        ...

    def list_snapshots(self, limit: int = 50, cursor: str = None) -> dict:
        """List snapshots in reverse chronological order."""
        ...

    def get_snapshot(self, snapshot_id: str) -> dict:
        """Get a single snapshot with full diff."""
        ...

    def restore_snapshot(self, snapshot_id: str) -> dict:
        """Restore configuration to snapshot state. Uses ConfigFileLock."""
        ...

    def _enforce_retention(self):
        """Delete snapshots exceeding age or count limits."""
        ...
```

**Integration point**: All Phase 2 and Phase 3 mutation endpoints must call `ConfigHistoryService.record_change()` after successful mutations. This is a cross-cutting concern best implemented as middleware or a decorator.

#### Edge Cases

- Restore a snapshot when the config has changed significantly since then: Show a comprehensive diff preview and warn about potential conflicts
- Snapshot references a file that no longer exists: Handle gracefully, show warning in restore preview
- Concurrent restore from two browser tabs: `ConfigFileLock` serializes the operations; the second restore may fail validation if the first changed the state
- History directory grows large: Retention policy auto-prunes old snapshots
- Restore during an active Claude Code session: Show the standard "restart Claude Code" warning

#### Devil's Advocate Counterpoint

> "Git already tracks file changes -- is a separate history system needed? The answer depends on context: if the user's project directory has git initialized, they already have file-level history via `git log`. However, config files live in `~/.claude-mpm/config/` (home directory), which is typically not a git repository. Additionally, git tracks file-level changes, not semantic operation-level changes ('deployed python-engineer from my-agents-repo'). The history system provides operation-level semantics that git cannot."
>
> **However**: This creates data duplication for project-level config files (`.claude-mpm/configuration.yaml`), which ARE in the git repo. And maintaining a custom versioning system is non-trivial tech debt.

**Mitigation**: Phase 4 history is limited to operation-level snapshots (not full file backups). Snapshots are lightweight JSON files (<1KB each). The retention policy (30 days / 100 snapshots) bounds the storage cost. For project-level configs that are in git, the history system is supplementary, not primary.

#### Acceptance Criteria

- [ ] All mutation operations (Phase 2-3 endpoints) create history snapshots
- [ ] Timeline view loads with reverse-chronological entries
- [ ] Expanding an entry shows before/after diff
- [ ] "Restore" button opens confirmation dialog with change preview
- [ ] Restore applies changes and broadcasts config_updated via Socket.IO
- [ ] Retention policy auto-prunes old snapshots
- [ ] Cursor-based pagination works for history entries
- [ ] Concurrent restore attempts are serialized via `ConfigFileLock`

---

### P4 -- YAML Editor with Syntax Validation

#### Description and User Value

An in-browser YAML editor for directly editing `configuration.yaml`, `agent_sources.yaml`, and `skill_sources.yaml`. This is the "escape hatch" for power users who need to make changes not supported by the structured UI. It also serves as a learning tool for users transitioning from CLI to UI.

#### API Endpoints

Reuses existing endpoints:
- GET `/api/config/project/` -- reads config file content
- PUT/PATCH on the relevant config endpoints -- saves changes

New endpoint for raw file access:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/config/files/{file_type}` | Get raw YAML content for a config file |
| PUT | `/api/config/files/{file_type}` | Save raw YAML content (with validation) |

Where `file_type` is one of: `configuration`, `agent_sources`, `skill_sources`.

**Save flow**: Client sends raw YAML string -> Server parses YAML -> Server validates against expected schema -> If valid, write with `ConfigFileLock` -> Return success. If invalid, return validation errors with line numbers.

#### Frontend Components

| Component | Purpose |
|-----------|---------|
| `YamlEditor.svelte` | Wrapper around CodeMirror 6 with YAML mode |
| `YamlEditorToolbar.svelte` | File selector, save button, validation status, format button |
| `SchemaErrorOverlay.svelte` | Inline error markers and hover tooltips |
| `ParsedPreview.svelte` | Side panel showing parsed YAML as structured tree |

**Editor library decision**: CodeMirror 6 is recommended over Monaco because:
- CodeMirror 6: ~150KB gzipped, modular, good YAML support, better mobile support
- Monaco: ~2MB gzipped, designed for VS Code, overkill for YAML-only editing
- The dashboard is a lightweight monitoring tool; a 2MB editor dependency is disproportionate

#### Data Flow

```
User selects config file from dropdown
  -> Fetch GET /api/config/files/{file_type}
  -> Load content into CodeMirror editor
  -> On keystroke: YAML parse (client-side, ~50ms debounce for syntax errors)
  -> On save: Send PUT /api/config/files/{file_type} with raw YAML + ETag
  -> Server validates syntax + schema
  -> If valid: write with ConfigFileLock, return success, broadcast config_updated
  -> If invalid: return errors with line numbers
  -> Client highlights error lines in editor
```

#### Edge Cases

- Invalid YAML syntax: Show inline error with line number, disable save button
- Valid YAML but invalid schema (e.g., port number as string): Show schema validation errors distinctly from syntax errors
- Concurrent edit (CLI modifies file while editor is open): ETag mismatch on save -> show "file changed externally" dialog with option to reload or force save
- Very large config file: Not expected (config files are typically <10KB), but CodeMirror handles it
- User pastes malformed content: YAML parser catches immediately

#### Devil's Advocate Counterpoint

> "Exposing raw YAML editing undermines the purpose of the structured UI. If users can bypass the form-based interface and edit YAML directly, they can introduce configurations that the structured UI doesn't know how to display. This creates a 'two-way door' problem where the YAML editor and the structured UI must both understand every possible configuration shape."
>
> **Counter**: Power users need an escape hatch for configurations not yet supported by the structured UI. The YAML editor is explicitly labeled as an advanced feature. The structured UI remains the primary interface. Schema validation on save ensures that edited YAML is still valid.

**Mitigation**: The YAML editor shows a prominent warning: "Direct YAML editing is an advanced feature. Changes made here may not be fully reflected in the structured UI." Schema validation on save prevents invalid configurations. The structured UI refreshes from disk after any YAML editor save.

#### Acceptance Criteria

- [ ] CodeMirror 6 loads with YAML syntax highlighting
- [ ] Three config files are selectable from a dropdown
- [ ] Real-time YAML syntax validation with inline error markers
- [ ] Schema validation on save with line-number-annotated errors
- [ ] Save uses `ConfigFileLock` and ETag-based concurrency control
- [ ] "File changed externally" detection and conflict resolution
- [ ] Parsed preview panel shows structured representation alongside raw YAML
- [ ] Bundle size impact is documented and <200KB gzipped for the editor
- [ ] "Advanced feature" warning is displayed on first use

---

### P5 -- Bulk Operations

#### Description and User Value

Select multiple agents or skills and deploy/undeploy them in a single operation. Eliminates the tedious one-by-one deploy workflow when setting up a new project or making large-scale changes.

#### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/config/agents/deploy-bulk` | Deploy multiple agents |
| POST | `/api/config/agents/undeploy-bulk` | Undeploy multiple agents |
| POST | `/api/config/skills/deploy-bulk` | Deploy multiple skills |
| POST | `/api/config/skills/undeploy-bulk` | Undeploy multiple skills |

**Request structure**:

```json
{
    "items": ["python-engineer", "qa", "data-engineer"],
    "force": false,
    "continue_on_error": true
}
```

**Response structure** (partial failure support):

```json
{
    "success": true,
    "results": [
        {"name": "python-engineer", "status": "success"},
        {"name": "qa", "status": "success"},
        {"name": "data-engineer", "status": "error", "error": "Source not found"}
    ],
    "summary": {
        "total": 3,
        "succeeded": 2,
        "failed": 1
    }
}
```

**Long-running**: Bulk operations with >5 items should use the async operation pattern (similar to `sync-all`). Socket.IO emits `bulk_progress` events per item, then `bulk_completed` with summary.

#### Frontend Components

| Component | Purpose |
|-----------|---------|
| `BulkSelectionBar.svelte` | Floating bar with "Select All" / "Select None" / "Deploy Selected" / "Undeploy Selected" |
| `BulkProgressDialog.svelte` | Modal showing per-item progress during bulk operation |
| `BulkResultsSummary.svelte` | Post-operation summary with per-item status |

**Selection UX**: Checkbox appears on each agent/skill card in the existing list views. Selection state is managed in the parent component. The `BulkSelectionBar` appears when at least one item is selected, showing "N selected" with action buttons.

**Quick selection filters**:
- "Select All" / "Select None"
- "Select Deployed" / "Select Available" (context-dependent)
- "Select by Source" dropdown (for agents from a specific repo)

#### Data Flow

```
User checks boxes on agent/skill cards
  -> BulkSelectionBar appears with count and actions
  -> User clicks "Deploy Selected"
  -> If >3 items for undeploy: show extra confirmation dialog
  -> POST /api/config/agents/deploy-bulk with item list
  -> Server processes sequentially, emits bulk_progress per item
  -> BulkProgressDialog shows real-time per-item status
  -> On completion: show BulkResultsSummary
  -> If partial failure: highlight failed items, show error details
  -> Refresh agent/skill lists
```

#### Edge Cases

- User selects 20 agents for undeploy: **Strong confirmation required**. Dialog shows all 20 names, requires typing "UNDEPLOY" to confirm, warns about Claude Code restart.
- Partial failure: Continue processing remaining items. Show per-item status in results. Failed items remain in their original state.
- User navigates away during bulk operation: Operation continues on server. Show "operation in progress" on return.
- Empty selection: Disable action buttons.
- Selecting a core/immutable agent for undeploy: Exclude from selection or show "cannot undeploy: required by system" (BR-05 equivalent).

#### Devil's Advocate Counterpoint

> "Bulk undeploy of 20 agents is extremely destructive -- needs very strong confirmation guardrails. A single misclick on 'Select All' + 'Undeploy' could remove every agent from a project. This is the configuration equivalent of `rm -rf`. The confirmation dialog must be genuinely friction-inducing for destructive operations, not a dismissable toast."

**Mitigation**: Undeploy operations with >3 items require typing a confirmation word ("UNDEPLOY"). The confirmation dialog lists every item that will be affected. There is no "skip confirmation" option. Deploy operations (additive) use a standard confirmation dialog without typing requirement.

#### Acceptance Criteria

- [ ] Checkboxes appear on agent/skill cards in list views
- [ ] Bulk selection bar shows item count and available actions
- [ ] "Select All" / "Select None" / filter shortcuts work
- [ ] Bulk deploy processes all items and shows per-item progress
- [ ] Bulk undeploy (>3 items) requires typing "UNDEPLOY" to confirm
- [ ] Partial failures are reported with per-item error details
- [ ] Operation continues on error when `continue_on_error` is true
- [ ] History snapshots are created for each item in the bulk operation (P3)

---

### P6 -- Import/Export

#### Description and User Value

Export the current configuration as a portable bundle (JSON or YAML) for sharing with team members, backup, or migrating to a new machine. Import a configuration bundle with diff preview and per-item conflict resolution.

#### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/config/export` | Export full configuration bundle |
| POST | `/api/config/import` | Import configuration with validation |
| POST | `/api/config/import/preview` | Preview import diff without applying |

**Export bundle structure**:

```json
{
    "version": "1.0",
    "exported_at": "2026-02-13T14:30:22Z",
    "exported_from": "/path/to/project",
    "configuration": { /* configuration.yaml contents */ },
    "agent_sources": { /* agent_sources.yaml contents */ },
    "skill_sources": { /* skill_sources.yaml contents */ },
    "deployed_agents": ["python-engineer", "qa", "engineer"],
    "deployed_skills": ["systematic-debugging", "python-core"],
    "skill_links": { /* skill-to-agent mapping summary */ },
    "metadata": {
        "claude_mpm_version": "5.7.34",
        "total_agents": 12,
        "total_skills": 45
    }
}
```

**Import flow**: Upload bundle -> Server validates structure and version -> Server computes diff against current config -> Return diff preview -> User reviews and accepts/rejects per-item changes -> Server applies accepted changes.

#### Frontend Components

| Component | Purpose |
|-----------|---------|
| `ExportButton.svelte` | Simple button that triggers download of the bundle |
| `ImportWizard.svelte` | Multi-step import flow: upload -> preview -> select -> apply |
| `ImportDiffView.svelte` | Shows what will change, with per-item accept/reject checkboxes |
| `ImportConflictCard.svelte` | Individual conflict: current value vs imported value |

#### Data Flow

**Export**:
```
User clicks "Export Configuration"
  -> Fetch GET /api/config/export
  -> Browser downloads JSON file: claude-mpm-config-{date}.json
```

**Import**:
```
User clicks "Import Configuration"
  -> File picker opens
  -> User selects JSON file
  -> POST /api/config/import/preview with file contents
  -> Server returns diff: { added: [...], modified: [...], removed: [...], unchanged: [...] }
  -> ImportDiffView shows categorized changes
  -> User checks/unchecks individual changes
  -> User clicks "Apply Selected Changes"
  -> POST /api/config/import with file contents + selected_changes list
  -> Server applies changes with ConfigFileLock
  -> History snapshots created for each change (P3)
  -> Socket.IO broadcasts config_updated
```

#### Edge Cases

- Import from a different claude-mpm version: Show version mismatch warning, attempt best-effort compatibility
- Import references source URLs not accessible from current machine: Show warning per-source: "URL may not be accessible"
- Import references agents/skills not available from current sources: Show as "cannot import" with explanation
- Import into a project with active Claude Code session: Standard "restart required" warning
- Import of empty or malformed file: Validation catches before preview step
- Import bundle exceeds reasonable size (>1MB): Reject with error

#### Devil's Advocate Counterpoint

> "Import of another project's config could have unintended consequences -- source URLs may not be accessible, tokens may differ, and the local environment may not match. A configuration that works on one machine is not guaranteed to work on another. The import feature must make this uncertainty visible, not hide it behind a smooth UX."

**Mitigation**: The import preview step explicitly validates reachability of source URLs (with timeouts). Unresolvable sources are flagged with warnings. The user must acknowledge these warnings before proceeding. The import is non-destructive by default -- it adds/modifies but does not remove existing configuration unless the user explicitly selects removals.

#### Acceptance Criteria

- [ ] Export produces a valid JSON bundle with all config data
- [ ] Export file downloads to the user's machine
- [ ] Import accepts JSON file upload
- [ ] Import preview shows categorized diff (added/modified/removed/unchanged)
- [ ] Per-item accept/reject is available in the preview
- [ ] Unreachable source URLs are flagged as warnings
- [ ] Version mismatch shows compatibility warning
- [ ] Applied changes create history snapshots (P3)
- [ ] Invalid/malformed files are rejected with clear error messages

---

### P7 -- Collection Management

#### Description and User Value

UI for managing skill collections. Collections group related skills together (e.g., "python-tools", "devops-essentials"). The default collection "claude-mpm" is immutable (BR-11). Users can add, remove, enable/disable custom collections and control collection priority ordering.

#### API Endpoints

Reuses existing agent/skill collections endpoints from the spec. Additional endpoints:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/config/collections/` | List all collections with status |
| POST | `/api/config/collections/` | Add a new collection |
| PUT | `/api/config/collections/{id}` | Update collection (enable/disable, priority) |
| DELETE | `/api/config/collections/{id}` | Remove a collection |

**Service layer**: `SkillsConfig` from the service catalog.

#### Frontend Components

| Component | Purpose |
|-----------|---------|
| `CollectionsManager.svelte` | List of collections with drag-to-reorder priority |
| `CollectionCard.svelte` | Individual collection: name, status, skill count, enable/disable toggle |
| `AddCollectionDialog.svelte` | Form for adding a new collection |

#### Data Flow

```
Collections tab selected
  -> Fetch GET /api/config/collections/
  -> Render ordered list of collections
  -> Default collection shows lock icon, toggle/delete disabled
  -> User drags to reorder -> PUT priority change
  -> User toggles enable/disable -> PUT status change
  -> User adds collection -> POST, refresh list
  -> User deletes collection -> DELETE with confirmation
```

#### Edge Cases

- Attempt to delete default collection: Button disabled, tooltip explains why (BR-11)
- Attempt to disable default collection: Same protection
- Collection with deployed skills: Show warning before deletion ("N skills from this collection are currently deployed")
- Duplicate collection name: Server rejects with 409 Conflict
- Empty collection: Show in list with "0 skills" badge

#### Devil's Advocate Counterpoint

> "Collection management overlaps significantly with source management (Phase 2). Users may be confused about whether to manage their skill groupings via 'Sources' or 'Collections'. These are distinct concepts (sources = where skills come from; collections = how skills are organized), but the distinction is subtle enough to cause UX confusion."

**Mitigation**: The collections UI is placed as a sub-section under the skills tab, not as a top-level tab. The UI includes explanatory text: "Collections organize skills into logical groups. To add new skill sources, use the Sources tab." Cross-links between the two sections aid navigation.

#### Acceptance Criteria

- [ ] Collections list loads with correct order and status
- [ ] Default collection shows lock icon, cannot be deleted or disabled
- [ ] Drag-to-reorder updates priority
- [ ] Enable/disable toggle works for non-default collections
- [ ] Add collection dialog validates input
- [ ] Delete confirmation shows impact (deployed skills from this collection)
- [ ] Explanatory text distinguishes collections from sources

---

### P8 -- Advanced Auto-Configure

#### Description and User Value

Extends the Phase 3 auto-configure with power-user features: custom rule overrides, saved profiles, dry-run simulation mode, and visual comparison of auto-configure recommendations against current configuration.

#### API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/config/auto-configure/profiles` | List saved profiles |
| POST | `/api/config/auto-configure/profiles` | Save a profile |
| DELETE | `/api/config/auto-configure/profiles/{id}` | Delete a profile |
| POST | `/api/config/auto-configure/dry-run` | Simulate auto-configure without applying |
| POST | `/api/config/auto-configure/compare` | Compare recommendation vs current |

**Service layer**: Extends `AutoConfigManagerService` from Phase 3.

#### Frontend Components

| Component | Purpose |
|-----------|---------|
| `AutoConfigAdvanced.svelte` | Advanced auto-configure panel with tabs for profiles/rules/compare |
| `ProfileManager.svelte` | CRUD for auto-configure profiles |
| `RuleEditor.svelte` | Override individual auto-configure recommendations |
| `DryRunResults.svelte` | Shows what would change without applying |
| `ConfigCompareView.svelte` | Side-by-side: recommended vs current |

#### Data Flow

```
User navigates to Advanced Auto-Configure
  -> Loads saved profiles (if any)
  -> User clicks "Dry Run"
  -> POST /api/config/auto-configure/dry-run with current rules/overrides
  -> Show DryRunResults: what would be deployed/undeployed/changed
  -> User adjusts overrides in RuleEditor
  -> User can save as a named profile
  -> User clicks "Apply" -> uses standard auto-configure apply flow (Phase 3)
```

#### Edge Cases

- No profiles saved: Show empty state with "Create your first profile" CTA
- Profile references agents/skills that no longer exist: Show warnings during profile load
- Dry run produces no changes: Show "Current configuration matches recommendation"
- Conflicting rules in profile: Validation catches before save

#### Devil's Advocate Counterpoint

> "Auto-configure profiles add another configuration layer on top of configuration -- meta-complexity risk. Users are now configuring the system that configures the system. This is powerful for experts but bewildering for newcomers. The risk is that P8 becomes a feature that 2% of users love and 98% of users are confused by."

**Mitigation**: P8 is the lowest priority feature and can be cut entirely without impacting core value. It is hidden behind an "Advanced" toggle that is collapsed by default. The basic auto-configure flow (Phase 3) remains the primary experience. Profiles are explicitly labeled as "advanced/expert" features.

#### Acceptance Criteria

- [ ] Dry run shows what would change without applying
- [ ] Profile CRUD (create, load, update, delete) works
- [ ] Rule overrides modify auto-configure behavior
- [ ] Comparison view shows recommended vs current side-by-side
- [ ] "Advanced" section is collapsed by default
- [ ] Features are accessible only after Phase 3 auto-configure is functional

---

## 4. Pagination Strategy

### Why Pagination is Mandatory in Phase 4

By Phase 4, the data sets grow significantly:
- Available agents: 100+ (across all sources)
- Available skills: 200+ (across all collections)
- Skill-to-agent links: N agents x M skills (potentially thousands of relationships)
- Configuration history: 100+ snapshots

Without pagination, these endpoints will produce multi-megabyte responses that degrade browser performance.

### Approach: Cursor-Based Pagination

Cursor-based pagination is preferred over offset-based for these reasons:
- **Stable under mutations**: Adding/removing items doesn't shift page boundaries
- **Efficient for append-only data**: History snapshots are naturally ordered by timestamp
- **Simple cursor**: Use `snapshot_id` or `timestamp` as cursor value

#### Backend Implementation Pattern

```python
from dataclasses import dataclass
from typing import Optional, List, TypeVar, Generic

T = TypeVar('T')

@dataclass
class PaginatedResponse(Generic[T]):
    items: List[T]
    next_cursor: Optional[str]
    has_more: bool
    total_count: int  # Optional: omit if expensive to compute

async def list_with_pagination(
    query_fn,
    cursor: Optional[str] = None,
    limit: int = 50,
    max_limit: int = 100
) -> PaginatedResponse:
    """Generic pagination wrapper."""
    effective_limit = min(limit, max_limit)
    # Fetch one extra to determine has_more
    items = await query_fn(after_cursor=cursor, limit=effective_limit + 1)
    has_more = len(items) > effective_limit
    if has_more:
        items = items[:effective_limit]
    next_cursor = items[-1].id if items and has_more else None
    return PaginatedResponse(
        items=items,
        next_cursor=next_cursor,
        has_more=has_more,
        total_count=-1  # Omit or compute lazily
    )
```

**Query parameter convention**:
- `?limit=50` -- items per page (max 100)
- `?cursor=<opaque_string>` -- start after this item
- `?sort=desc` -- sort direction (default: desc for history, asc for lists)

#### Frontend: Page Controls (Not Infinite Scroll)

Infinite scroll is inappropriate for configuration management because:
- Users need to understand the full scope of their configuration
- Selection state (for bulk operations) is confusing with infinite scroll
- Page controls give users a sense of position and total count

**Component**: `PaginationControls.svelte`
- Shows: "Showing 1-50 of 127" with Previous/Next buttons
- "Load More" button as an alternative to full pagination
- Remembers page position when navigating back

#### Endpoints Requiring Pagination

| Endpoint | Default Limit | Max Limit | Sort Default |
|----------|:------------:|:---------:|:------------:|
| GET `/api/config/agents/available` | 50 | 100 | name asc |
| GET `/api/config/skills/available` | 50 | 100 | name asc |
| GET `/api/config/skill-links/` | 50 | 100 | agent name asc |
| GET `/api/config/history/` | 50 | 100 | timestamp desc |
| GET `/api/config/collections/` | 20 | 50 | priority asc |

Endpoints that do NOT need pagination (small, bounded data sets):
- GET `/api/config/agents/deployed` (typically 5-20)
- GET `/api/config/skills/deployed` (typically 10-40)
- GET `/api/config/sources/` (typically 2-5)
- GET `/api/config/validate` (typically 0-20 issues)

---

## 5. Testing Strategy

### Current State: Zero Frontend Tests

The dashboard currently has **no frontend tests**. By Phase 4, the config UI will be complex enough (10-12 config-specific components + 6-8 shared components) that untested code becomes a liability. A testing framework must be established before or during Phase 4.

### Test Layers

#### Layer 1: Unit Tests (Backend Business Logic)

**Framework**: pytest (already in use)

**Coverage targets**:
- `ConfigHistoryService`: snapshot creation, retention, restore logic
- `ConfigValidationService`: all validation rules produce correct severity/message
- Bulk operation logic: partial failure handling, continue-on-error semantics
- Import/export: schema validation, version compatibility, diff computation
- Pagination: cursor encoding/decoding, boundary conditions

**Example test cases**:

```python
# Config history tests
def test_snapshot_creation_records_before_after():
    """Verify snapshot captures both states."""

def test_retention_policy_deletes_old_snapshots():
    """Verify snapshots beyond 30 days / 100 count are pruned."""

def test_restore_snapshot_applies_changes_with_lock():
    """Verify restore acquires ConfigFileLock and writes atomically."""

def test_restore_snapshot_rejects_if_file_changed():
    """Verify optimistic concurrency check prevents stale restore."""

# Bulk operation tests
def test_bulk_deploy_continues_on_error():
    """Verify partial failure does not abort remaining items."""

def test_bulk_undeploy_records_individual_history_snapshots():
    """Verify each item in bulk operation gets its own history entry."""

# Import/export tests
def test_export_includes_all_config_sections():
    """Verify export bundle contains all expected sections."""

def test_import_preview_computes_correct_diff():
    """Verify diff correctly categorizes added/modified/removed/unchanged."""

def test_import_rejects_invalid_version():
    """Verify version mismatch is handled gracefully."""
```

**Target**: 90%+ coverage for Phase 4 backend services. All 7 new endpoints (P2, P3, P6) must have comprehensive test suites.

#### Layer 2: Component Tests (Frontend Form Validation)

**Framework**: Vitest + @testing-library/svelte

**Priority components to test**:
- `BulkSelectionBar.svelte`: Selection state management, count display, button enable/disable
- `ImportDiffView.svelte`: Per-item checkbox state, accept/reject logic
- `YamlEditor.svelte`: Validation state, error marker positioning
- `RestoreConfirmDialog.svelte`: Confirmation logic, button states
- `PaginationControls.svelte`: Page state, button enable/disable

**Example**:

```typescript
import { render, fireEvent } from '@testing-library/svelte';
import BulkSelectionBar from './BulkSelectionBar.svelte';

test('shows correct count when items selected', () => {
    const { getByText } = render(BulkSelectionBar, {
        props: { selectedCount: 5, totalCount: 20 }
    });
    expect(getByText('5 selected')).toBeTruthy();
});

test('disables deploy button when no items selected', () => {
    const { getByRole } = render(BulkSelectionBar, {
        props: { selectedCount: 0, totalCount: 20 }
    });
    expect(getByRole('button', { name: 'Deploy Selected' })).toBeDisabled();
});
```

#### Layer 3: Integration Tests (Critical Workflows)

**Framework**: Vitest (backend mocked via MSW or similar)

**Critical flows to test**:
1. **Mode switch**: Navigate between config tabs, verify data loads correctly
2. **Import/export round-trip**: Export config, import into clean state, verify equivalence
3. **Bulk deploy + history**: Deploy 3 agents, verify 3 history entries created
4. **YAML edit + validation**: Edit YAML, introduce error, verify save is blocked
5. **Restore from history**: Make change, restore previous state, verify config reverted

#### Layer 4: E2E Tests

**Framework**: Playwright

**Priority E2E scenarios**:
1. **Auto-configure full flow**: Open dashboard -> Config tab -> Auto-Configure -> Detect -> Preview -> Apply -> Verify agents deployed
2. **Bulk operations**: Select 3 agents -> Deploy -> Verify all deployed -> Select all -> Undeploy -> Confirm -> Verify all undeployed
3. **Import/export**: Export -> Modify config via API -> Import exported file -> Preview diff -> Apply -> Verify restored

**E2E test frequency**: Run on CI for PRs that touch config UI code. Not run on every commit (too slow).

#### Performance Tests

**Focus areas**:
- Pagination endpoints with 500+ items: Response time <200ms
- Skill-links endpoint with 40 agents x 200 skills: Response time <500ms
- History endpoint with 100 snapshots: Response time <100ms
- Concurrent access: 5 simultaneous requests to mutation endpoints with `ConfigFileLock`
- CodeMirror initialization time: <500ms on first load

**Tool**: pytest-benchmark for backend, Lighthouse for frontend

---

## 6. Performance Optimization

### 6.1 Lazy Loading Patterns

**Principle**: Don't fetch data until the user navigates to the relevant section.

| Data | When to Load | Strategy |
|------|-------------|----------|
| Agent/skill lists | When config tab opens | Single fetch, cache in store |
| Agent detail | When agent is selected | On-demand fetch, LRU cache (20 items) |
| Skill links | When skill-links sub-tab opens | Single fetch, refresh on config_updated |
| History entries | When history sub-tab opens | Paginated fetch, append on scroll |
| Validation results | When config tab opens | Auto-fetch, refresh on config_updated |
| YAML file content | When YAML editor opens | On-demand per-file |
| Collection details | When collections sub-tab opens | Single fetch |

**Implementation**: Svelte stores with lazy initialization:

```typescript
// Lazy-loaded store pattern
class LazyStore<T> {
    private data = $state<T | null>(null);
    private loading = $state(false);
    private loaded = $state(false);

    async load() {
        if (this.loaded || this.loading) return;
        this.loading = true;
        try {
            this.data = await fetchData();
            this.loaded = true;
        } finally {
            this.loading = false;
        }
    }

    invalidate() {
        this.loaded = false;
        this.data = null;
    }
}
```

### 6.2 Debounced Search

All search/filter inputs use a 300ms debounce:
- Agent list search (P1, P5)
- Skill list search (P1, P5)
- History search (P3)
- YAML editor syntax validation (P4, 50ms for keystroke feedback)

**Implementation**:

```typescript
function debounce(fn: Function, delay: number) {
    let timeout: ReturnType<typeof setTimeout>;
    return (...args: any[]) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => fn(...args), delay);
    };
}

// In component
const debouncedSearch = debounce((query: string) => {
    filteredItems = items.filter(item =>
        item.name.toLowerCase().includes(query.toLowerCase())
    );
}, 300);
```

### 6.3 Response Caching Strategy

| Resource | Cache Duration | Invalidation |
|----------|:-------------:|:------------|
| Available agents | 5 minutes | `config_updated` Socket.IO event |
| Available skills | 5 minutes | `config_updated` Socket.IO event |
| Deployed agents | 30 seconds | `agent_deployed`/`agent_undeployed` events |
| Deployed skills | 30 seconds | `skill_deployed`/`skill_undeployed` events |
| Skill links | 5 minutes | `config_updated` event |
| Validation | 60 seconds | Any mutation event |
| History | No cache | Always fresh (paginated, low cost) |
| Config files (YAML editor) | No cache | ETag-based freshness check |

**Implementation**: Stores track a `lastFetched` timestamp and `isStale` flag. Socket.IO events set `isStale = true`. Next access triggers a re-fetch.

### 6.4 Bundle Size Considerations

The largest dependency concern for Phase 4 is the YAML editor:

| Library | Size (gzipped) | Features |
|---------|:--------------:|----------|
| CodeMirror 6 (YAML mode only) | ~80-150KB | Syntax highlighting, basic editing |
| CodeMirror 6 (full) | ~200KB | + autocomplete, linting, search |
| Monaco Editor | ~2MB | Full VS Code experience |

**Recommendation**: CodeMirror 6 with YAML language support and linting extensions. Total added bundle size: ~150KB gzipped. This is acceptable for a feature that loads on-demand (lazy-loaded when the YAML editor tab is opened).

**Dynamic import**:

```typescript
// Load CodeMirror only when YAML editor is opened
const loadEditor = async () => {
    const { EditorView } = await import('@codemirror/view');
    const { yaml } = await import('@codemirror/lang-yaml');
    // Initialize editor...
};
```

**Current dashboard bundle**: ~250KB gzipped (Svelte + Socket.IO + D3). Adding CodeMirror would increase total to ~400KB, but only if the user opens the YAML editor.

---

## 7. UX Design Considerations

### 7.1 Information Architecture with 8+ Sub-Features

Phase 4 adds 8 features to an already feature-rich config section. Without careful IA, the config tab becomes overwhelming.

**Proposed navigation structure**:

```
Config Tab
  ├── Overview           (Dashboard: deployed counts, validation status, quick actions)
  ├── Agents             (List, deploy/undeploy, bulk operations)
  ├── Skills             (List, deploy/undeploy, bulk operations)
  │   └── Collections    (Sub-section within Skills)
  ├── Sources            (Phase 2: source management)
  ├── Skill Links        (P1: visualization)
  ├── Auto-Configure     (Phase 3 + P8 advanced)
  ├── History            (P3: timeline)
  └── Advanced
      ├── YAML Editor    (P4)
      ├── Import/Export  (P6)
      └── Validation     (P2: also shown in Overview)
```

**Key decisions**:
- "Advanced" section groups power-user features that most users do not need
- Validation summary appears on the Overview (always visible) but full details are in Advanced
- Collections are a sub-section of Skills, not a top-level tab
- Skill Links gets its own tab because it is a unique visualization, not a list

### 7.2 Progressive Disclosure

Users should not see 8 tabs on first visit. Progressive disclosure rules:

1. **First visit**: Show Overview + Agents + Skills tabs. Other tabs are visible but subdued.
2. **Advanced section**: Collapsed by default. Expand arrow with label "Advanced: YAML Editor, Import/Export, Validation Details".
3. **Tooltips on tabs**: Hover over any tab shows a one-sentence description of what it contains.
4. **Empty states**: Every section has a helpful empty state that explains what the feature does and how to get started.
5. **Feature discovery**: When validation finds issues, show a subtle badge on the "Validation" tab to draw attention.

### 7.3 Power User vs. Casual User Paths

| Task | Casual User Path | Power User Path |
|------|-------------------|-----------------|
| Deploy an agent | Config > Agents > Click "Deploy" | Bulk select > Deploy Selected |
| Check config health | Config > Overview (validation badge) | Config > Advanced > Validation (full details) |
| Edit configuration | Config > Agents/Skills/Sources (forms) | Config > Advanced > YAML Editor |
| Share config | Not needed | Config > Advanced > Export |
| Undo a change | Config > History > Restore | Same (only path) |
| View skill relationships | Config > Skill Links | Same (only path) |

### 7.4 Keyboard Navigation and Accessibility

**Keyboard shortcuts** (within config section):

| Shortcut | Action |
|----------|--------|
| `Tab` / `Shift+Tab` | Navigate between interactive elements |
| `Enter` / `Space` | Activate buttons, checkboxes, expand/collapse |
| `Escape` | Close dialogs, cancel operations |
| `/` | Focus search input (when in a list view) |
| `Ctrl+A` | Select All (when in bulk selection mode) |
| `Ctrl+S` | Save (when in YAML editor) |

**ARIA attributes**:
- All tabs use `role="tablist"`, `role="tab"`, `role="tabpanel"`
- Dialogs use `role="dialog"` with `aria-modal="true"`
- Bulk selection checkboxes have `aria-label` describing the item
- Validation badges use `aria-live="polite"` for screen reader updates
- Status messages (deploy success/failure) use `aria-live="assertive"`

**Color contrast**: All severity colors (error red, warning yellow, info blue) meet WCAG AA contrast ratio (4.5:1) against the dark/light backgrounds.

---

## 8. What Stays CLI-Only

The following operations are **permanently CLI-only**. This is not a temporary limitation -- these operations are fundamentally unsuitable for a web UI due to their side effects, security requirements, or process lifecycle coupling.

| Operation | CLI Command | Rationale |
|-----------|------------|-----------|
| Project initialization | `claude-mpm init` | Creates directories, generates configs, initializes git -- too many side effects for a web UI. Requires interactive prompts for project type, agent selection, etc. |
| Hook installation/removal | `claude-mpm hooks install` | Modifies system-level Claude Code hooks. Requires shell access and file permissions that a web UI cannot safely obtain. |
| OAuth setup | `claude-mpm auth setup` | Interactive OAuth flow requiring browser redirects and credential storage. The dashboard itself runs as a local server -- it cannot authenticate to itself. |
| Session management | `claude-mpm session pause/resume` | Tied to terminal process lifecycle. Sessions are OS processes, not configuration state. The dashboard can monitor sessions but not control process lifecycle. |
| Memory management | `claude-mpm memory ...` | Agent memory files are runtime state, not configuration. Editing memory files via a web UI risks corrupting agent context mid-session. |

**CLI command generator fallback**: For operations close to the CLI-only boundary (e.g., complex multi-source agent deployment), the UI can generate the equivalent CLI command and show a "Copy to clipboard" button. This educates users about the CLI while providing value from the UI.

---

## 9. Migration Path

### Transitioning Users from CLI-Heavy to UI-First Workflow

Phase 4 marks the point where the UI becomes a viable primary interface for most configuration tasks. However, long-time CLI users need a smooth transition.

### Stage 1: Awareness (Phase 1-2)

- Dashboard shows a "Configuration" tab with read-only views
- Users discover that the UI provides better visibility than the CLI
- CLI power users learn the UI's information architecture passively

### Stage 2: Complementary (Phase 3)

- UI handles deploy/undeploy and auto-configure
- CLI remains the "fallback" for anything the UI doesn't support
- Users begin doing simple operations (single agent deploy) in the UI

### Stage 3: UI-Primary (Phase 4)

- Bulk operations make the UI more efficient than CLI for multi-item tasks
- YAML editor provides the CLI's flexibility within the UI
- Import/export enables workflows (team sharing) that the CLI cannot do
- History provides undo capability that the CLI lacks
- **The UI now offers capabilities beyond the CLI**

### Transition Aids

1. **CLI command display**: Every UI operation shows the equivalent CLI command in a collapsible section ("What this does: `claude-mpm agents deploy python-engineer`"). This builds CLI literacy and trust.

2. **"Run in terminal" option**: For operations the user is not comfortable doing in the UI, offer a "Copy CLI command" button that generates the equivalent command.

3. **Documentation**: Update `claude-mpm --help` to mention dashboard equivalents: "This operation is also available in the dashboard at Config > Agents."

4. **No forced migration**: The CLI continues to work for everything. The UI is an alternative, not a replacement. Users choose their preferred interface per-task.

---

## 10. Definition of Done

### Per-Feature Acceptance Criteria Summary

Each feature (P1-P8) has detailed acceptance criteria in Section 3. The following are **cross-cutting** criteria that apply to all features:

#### Functionality

- [ ] All specified API endpoints return correct responses for valid inputs
- [ ] All error cases return appropriate HTTP status codes and error messages
- [ ] `ConfigFileLock` is used for all file mutations
- [ ] Socket.IO events are emitted for all state changes
- [ ] Optimistic concurrency control (ETag) is implemented for all write endpoints

#### Frontend

- [ ] Components render correctly in both light and dark modes
- [ ] Loading states are shown during async operations
- [ ] Error states are shown when operations fail
- [ ] Empty states are shown when no data exists
- [ ] All interactive elements are keyboard-navigable
- [ ] ARIA attributes are present on semantic elements

#### Testing

- [ ] Backend: Unit tests cover all new service methods (90%+ coverage)
- [ ] Backend: Integration tests cover all new API endpoints
- [ ] Frontend: Component tests cover form validation logic for P4 and P5
- [ ] E2E: At least one end-to-end test covers each critical flow

#### Performance

- [ ] Paginated endpoints respond in <200ms for 500+ items
- [ ] Non-paginated endpoints respond in <500ms
- [ ] CodeMirror is lazy-loaded and does not impact initial page load
- [ ] No memory leaks from Socket.IO event listeners or editor instances

#### Documentation

- [ ] API endpoints documented with request/response schemas
- [ ] New components documented with props and usage examples
- [ ] Configuration options (history retention, pagination limits) documented
- [ ] Migration guide updated with Phase 4 capabilities

---

## 11. Devil's Advocate Summary

### Consolidated Risks and Mitigations for Phase 4

Phase 4 is the highest-risk phase. The following risks are ordered by severity.

#### Risk 1: Phase 4 Scope Creep

> "Phase 4 scope creep is the biggest risk -- ruthless prioritization needed."

**Severity**: Critical

Phase 4 contains 8 features totaling 4-6 weeks of work. The temptation to add "just one more feature" to each priority level is strong. Each added feature increases the maintenance surface area and delays the overall completion.

**Mitigation**:
- P1-P3 are the "must have" features. P4-P5 are "should have". P6-P8 are "nice to have".
- If time-pressured, cut P6-P8 entirely. They are escape hatches, not core value.
- Each feature ships independently. Do not bundle features into a "Phase 4 release."
- Track feature completion against the original estimate. If P1 takes 2 weeks instead of 1, re-evaluate the remaining features.

#### Risk 2: Frontend Testing Debt

> "The frontend will need a testing framework before Phase 4 -- this is deferred tech debt."

**Severity**: High

The dashboard has zero frontend tests. Phase 4 adds complex interactive components (bulk selection, YAML editor, import wizard) that are prone to subtle state management bugs. Shipping these without tests is reckless.

**Mitigation**:
- Establish Vitest + @testing-library/svelte before starting P1
- Require component tests for any component with form validation or selection state
- Do not require tests for simple display-only components (e.g., `SkillChip.svelte`)
- E2E tests can be deferred to the end of Phase 4 but must exist before Phase 4 is declared complete

#### Risk 3: Configuration History Creates Data Duplication

> "Configuration history in a separate system (not git) creates data duplication."

**Severity**: Medium

Project-level config files are already tracked by git. Adding a separate history system means two sources of truth for file-level changes.

**Mitigation**:
- History snapshots store operation-level metadata (who, what, when), not full file copies
- History is supplementary to git, not a replacement
- Storage cost is bounded by retention policy (30 days / 100 snapshots)
- If the project has git, consider offering "view in git log" as an alternative for file-level history

#### Risk 4: YAML Editor and Import/Export Are Escape Hatches

> "The YAML editor and import/export features can be cut if time-pressured -- they're escape hatches, not core value."

**Severity**: Low

P4 and P6 provide functionality that the CLI already offers (editing YAML, copying config files). Their UI value is convenience, not capability.

**Mitigation**:
- Explicitly label these as "Advanced" features
- If time-pressured, cut P4 first (users can edit YAML in their text editor)
- If further pressed, cut P6 (users can manually copy config files)
- P7 and P8 can also be cut with minimal impact

#### Risk 5: Codebase Maintainability at Scale

> "By Phase 4, the codebase will have 30+ new files -- maintainability requires good documentation."

**Severity**: Medium

Phase 4 adds ~15 frontend components and ~5 backend services. Combined with Phase 1-3, the config UI will have 30+ new files in a codebase that was originally a simple monitoring dashboard.

**Mitigation**:
- Every new file has a JSDoc/docstring header explaining its purpose
- Component props are typed with TypeScript interfaces
- Service methods have comprehensive docstrings with examples
- A component catalog (Storybook or equivalent) is considered but not required
- The directory structure is consistent: `components/config/`, `stores/config/`, `services/config/`

#### Risk 6: Bulk Operations as a Destructive Weapon

> "Bulk undeploy of 20 agents is extremely destructive."

**Severity**: High

A single accidental "Select All" + "Undeploy" can remove every agent from a project. This is not recoverable without history (P3) or manual re-deployment.

**Mitigation**:
- P5 (bulk operations) should not ship before P3 (history) -- this creates an implicit ordering dependency
- Destructive bulk operations require typing confirmation word
- Confirmation dialog lists every affected item by name
- History snapshots provide rollback capability
- Consider a "soft delete" model where undeployed agents can be re-deployed from the same view

---

## 12. Files Created/Modified

### Per-Feature File Lists

#### P1 -- Skill-to-Agent Linking Visualization

**Backend (new)**:
- `src/claude_mpm/dashboard/handlers/config_skill_links.py` -- API handlers for skill-links endpoints

**Frontend (new)**:
- `dashboard-svelte/src/lib/components/config/SkillLinksView.svelte`
- `dashboard-svelte/src/lib/components/config/AgentSkillPanel.svelte`
- `dashboard-svelte/src/lib/components/config/SkillChipList.svelte`
- `dashboard-svelte/src/lib/components/config/SkillChip.svelte`
- `dashboard-svelte/src/lib/stores/config/skillLinks.svelte.ts`

**Frontend (modified)**:
- `dashboard-svelte/src/routes/+page.svelte` -- add skill-links tab

**Tests (new)**:
- `tests/dashboard/test_config_skill_links.py`

#### P2 -- Configuration Validation Display

**Backend (new)**:
- `src/claude_mpm/dashboard/handlers/config_validate.py`
- `src/claude_mpm/services/config/config_validation_service.py`

**Frontend (new)**:
- `dashboard-svelte/src/lib/components/config/ValidationPanel.svelte`
- `dashboard-svelte/src/lib/components/config/ValidationIssueCard.svelte`

**Tests (new)**:
- `tests/dashboard/test_config_validate.py`
- `tests/services/test_config_validation_service.py`

#### P3 -- Configuration History/Versioning

**Backend (new)**:
- `src/claude_mpm/services/config/config_history_service.py`
- `src/claude_mpm/dashboard/handlers/config_history.py`

**Backend (modified)**:
- All Phase 2-3 mutation handlers -- add `ConfigHistoryService.record_change()` calls

**Frontend (new)**:
- `dashboard-svelte/src/lib/components/config/HistoryTimeline.svelte`
- `dashboard-svelte/src/lib/components/config/HistoryEntry.svelte`
- `dashboard-svelte/src/lib/components/config/DiffViewer.svelte` -- shared component
- `dashboard-svelte/src/lib/components/config/RestoreConfirmDialog.svelte`
- `dashboard-svelte/src/lib/stores/config/history.svelte.ts`

**Tests (new)**:
- `tests/services/test_config_history_service.py`
- `tests/dashboard/test_config_history.py`

#### P4 -- YAML Editor with Syntax Validation

**Backend (new)**:
- `src/claude_mpm/dashboard/handlers/config_files.py`

**Frontend (new)**:
- `dashboard-svelte/src/lib/components/config/YamlEditor.svelte`
- `dashboard-svelte/src/lib/components/config/YamlEditorToolbar.svelte`
- `dashboard-svelte/src/lib/components/config/SchemaErrorOverlay.svelte`
- `dashboard-svelte/src/lib/components/config/ParsedPreview.svelte`

**Frontend (modified)**:
- `dashboard-svelte/package.json` -- add CodeMirror 6 dependencies

**Tests (new)**:
- `tests/dashboard/test_config_files.py`
- `dashboard-svelte/src/lib/components/config/__tests__/YamlEditor.test.ts`

#### P5 -- Bulk Operations

**Backend (new)**:
- `src/claude_mpm/dashboard/handlers/config_bulk.py`

**Frontend (new)**:
- `dashboard-svelte/src/lib/components/config/BulkSelectionBar.svelte`
- `dashboard-svelte/src/lib/components/config/BulkProgressDialog.svelte`
- `dashboard-svelte/src/lib/components/config/BulkResultsSummary.svelte`

**Frontend (modified)**:
- Agent and skill list components -- add checkbox selection support

**Tests (new)**:
- `tests/dashboard/test_config_bulk.py`
- `dashboard-svelte/src/lib/components/config/__tests__/BulkSelectionBar.test.ts`

#### P6 -- Import/Export

**Backend (new)**:
- `src/claude_mpm/services/config/config_import_export_service.py`
- `src/claude_mpm/dashboard/handlers/config_import_export.py`

**Frontend (new)**:
- `dashboard-svelte/src/lib/components/config/ExportButton.svelte`
- `dashboard-svelte/src/lib/components/config/ImportWizard.svelte`
- `dashboard-svelte/src/lib/components/config/ImportDiffView.svelte`
- `dashboard-svelte/src/lib/components/config/ImportConflictCard.svelte`

**Tests (new)**:
- `tests/services/test_config_import_export_service.py`
- `tests/dashboard/test_config_import_export.py`

#### P7 -- Collection Management

**Backend (new)**:
- `src/claude_mpm/dashboard/handlers/config_collections.py`

**Frontend (new)**:
- `dashboard-svelte/src/lib/components/config/CollectionsManager.svelte`
- `dashboard-svelte/src/lib/components/config/CollectionCard.svelte`
- `dashboard-svelte/src/lib/components/config/AddCollectionDialog.svelte`

**Tests (new)**:
- `tests/dashboard/test_config_collections.py`

#### P8 -- Advanced Auto-Configure

**Backend (new)**:
- `src/claude_mpm/services/config/autoconfig_profiles_service.py`
- `src/claude_mpm/dashboard/handlers/config_autoconfig_advanced.py`

**Frontend (new)**:
- `dashboard-svelte/src/lib/components/config/AutoConfigAdvanced.svelte`
- `dashboard-svelte/src/lib/components/config/ProfileManager.svelte`
- `dashboard-svelte/src/lib/components/config/RuleEditor.svelte`
- `dashboard-svelte/src/lib/components/config/DryRunResults.svelte`
- `dashboard-svelte/src/lib/components/config/ConfigCompareView.svelte`

**Tests (new)**:
- `tests/services/test_autoconfig_profiles_service.py`
- `tests/dashboard/test_config_autoconfig_advanced.py`

#### Shared/Infrastructure

**Frontend (new)**:
- `dashboard-svelte/src/lib/components/shared/PaginationControls.svelte`
- `dashboard-svelte/src/lib/components/shared/ConfirmDialog.svelte` -- generic confirmation dialog
- `dashboard-svelte/src/lib/components/shared/SearchInput.svelte` -- debounced search input
- `dashboard-svelte/src/lib/components/shared/EmptyState.svelte` -- generic empty state
- `dashboard-svelte/src/lib/components/shared/Badge.svelte` -- status/count badge
- `dashboard-svelte/src/lib/components/shared/Chip.svelte` -- generic chip component
- `dashboard-svelte/src/lib/utils/pagination.ts`
- `dashboard-svelte/src/lib/utils/debounce.ts`
- `dashboard-svelte/vitest.config.ts` -- test configuration
- `dashboard-svelte/src/lib/test-utils/setup.ts` -- test setup

### File Count Summary

| Category | New Files | Modified Files |
|----------|:---------:|:--------------:|
| Backend handlers | 8 | 5-8 (Phase 2-3 handlers for history integration) |
| Backend services | 4 | 0 |
| Frontend components (config) | 27 | 3-5 (existing list components for bulk selection) |
| Frontend components (shared) | 6 | 0 |
| Frontend stores | 2 | 1 |
| Frontend utils | 2 | 0 |
| Frontend config/test setup | 2 | 1 (package.json) |
| Test files | 12 | 0 |
| **Total** | **~63** | **~15** |

---

## 13. Long-Term Roadmap Beyond Phase 4

Phase 4 completes the core configuration management UI. The following are potential future directions, not commitments.

### Monitoring Integration

- Show agent deployment status alongside agent performance metrics (from the existing monitoring dashboard)
- Correlation: "Agent X was deployed at time T. Performance degraded at T+1. Consider rolling back."
- Requires bridging config state with the event monitoring system

### Team Configuration Sharing

- Build on P6 (Import/Export) to create a configuration registry
- Publish configurations to a shared repository
- Browse and import community configurations
- Version-controlled configuration templates (e.g., "Python Full-Stack Setup v2")

### Configuration Templates

- Pre-built configurations for common project types (Python web, TypeScript frontend, data science)
- Template marketplace or curated list
- One-click project setup: select template -> auto-configure -> deploy

### Multi-Project Dashboard

- Manage configurations across multiple projects from a single dashboard instance
- Switch project context within the UI
- Compare configurations between projects
- Requires significant backend refactoring (currently single-project scoped)

### Configuration Drift Detection

- Continuously monitor for drift between declared configuration and actual deployed state
- Alert when an agent file is modified outside of claude-mpm
- Alert when a skill is deployed but not in any config
- Runs as a background check, similar to Terraform plan

### AI-Assisted Configuration

- Use Claude to analyze project structure and recommend agent/skill configurations
- Natural language configuration: "Set up my project for Python API development with testing"
- Auto-generate agent configurations from project analysis
- Goes beyond auto-configure (Phase 3/P8) by using LLM understanding of the project

---

*End of Phase 4 Implementation Plan*

**Document version**: 1.0
**Last updated**: 2026-02-13
**Research sources**: 01-service-layer-api-catalog.md, 02-data-models-business-rules.md, 03-frontend-architecture-ux-guide.md, 04-backend-api-specification.md, 05-risk-assessment-devils-advocate.md
