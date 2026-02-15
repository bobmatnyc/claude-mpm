# Dashboard UI Research: Agents & Skills Configuration Tabs

**Date**: 2026-02-14
**Researcher**: Research Agent
**Scope**: Current dashboard UI implementation for agents/skills display in the Config tab

---

## 1. Architecture Overview

### Project Structure

The dashboard is a **SvelteKit** application located at:
```
src/claude_mpm/dashboard-svelte/
```

The Python backend serves the built frontend from:
```
src/claude_mpm/dashboard/static/svelte-build/
```

### Key Directories

| Path | Purpose |
|------|---------|
| `dashboard-svelte/src/routes/` | SvelteKit routes (`+page.svelte`, `+layout.svelte`) |
| `dashboard-svelte/src/lib/components/` | Reusable components |
| `dashboard-svelte/src/lib/components/config/` | Config tab components (agents, skills, sources) |
| `dashboard-svelte/src/lib/components/shared/` | Shared UI primitives (Modal, Toast, Badge, etc.) |
| `dashboard-svelte/src/lib/stores/` | Svelte stores (state management) |
| `dashboard-svelte/src/lib/stores/config/` | Config-specific stores (skillLinks) |

### Technology Stack

- **Frontend Framework**: SvelteKit with **Svelte 5** (Runes API - `$state`, `$derived`, `$effect`, `$props`)
- **CSS Framework**: **Tailwind CSS** (via `@tailwind` directives in `app.css`)
- **Design System**: Custom color palette based on **Slate** (backgrounds) and **Cyan** (accent/primary)
- **State Management**: Hybrid pattern - Svelte 4 `writable()` stores bridged to Svelte 5 `$state` via `$effect()` subscriptions
- **Backend**: Python **aiohttp** web server (not Flask/FastAPI despite CLAUDE.md stating otherwise)
- **Real-time**: **Socket.IO** for config events and sync progress
- **Dark Mode**: Full dark mode support via `.dark` class on root element with `themeStore`

---

## 2. Main Layout Architecture

### `+page.svelte` (src/routes/+page.svelte)

The main page implements a **split-panel layout** with:
- **Left panel**: View selector tabs + content area (resizable width, default 40%)
- **Draggable divider**: 6px wide, resizable cursor
- **Right panel**: Detail/explorer view (remaining width)

### Top-Level View Tabs

```typescript
type ViewMode = 'events' | 'tools' | 'files' | 'agents' | 'config';
// Note: 'tokens' tab exists but is hidden (commented out)
```

| Tab | Left Panel Component | Right Panel Component |
|-----|---------------------|----------------------|
| Events | `EventStream` | `JSONExplorer` |
| Tools | `ToolsView` | `JSONExplorer` |
| Files | `FilesView` | `FileViewer` |
| Agents | `AgentsView` | `AgentDetail` |
| Config | `ConfigView(panelSide="left")` | `ConfigView(panelSide="right")` |

**Key Pattern**: The Config tab is unique - it renders `ConfigView` in **both** panels with a `panelSide` prop to determine left vs right behavior.

### Tab Styling

```css
.tab {
    padding: 0.5rem 1.5rem;
    font-size: 0.875rem;
    font-weight: 600;
    background-color: #475569; /* slate-600 */
    color: #94a3b8; /* slate-400 */
    border-top-left-radius: 0.375rem;
    border-top-right-radius: 0.375rem;
}
.tab.active {
    background-color: #0891b2; /* cyan-600 */
    color: #ffffff;
}
```

---

## 3. Agents Tab (Real-Time Monitoring)

### Component: `AgentsView.svelte`

**Purpose**: Shows a **tree view** of running agent sessions (PM + sub-agents) from real-time Socket.IO events. This is NOT the Config agents list - it tracks active agent execution.

**Data Source**: `createAgentsStore(filteredEventsStore)` - derived from Socket.IO events filtered by selected stream.

**Layout**: Flat list rendered from a flattened tree structure with indentation.

#### AgentNode Type (from agents.svelte.ts store):
```typescript
interface AgentNode {
    id: string;
    name: string;           // Agent type (e.g., "svelte-engineer")
    sessionId: string;
    status: 'active' | 'completed' | 'error';
    startTime: number;
    endTime: number | null;
    children: AgentNode[];
    toolCalls: ToolCall[];
    todos: TodoActivity[];
    tokenUsage: { totalTokens: number; ... };
    plans: Plan[];
    responses: Response[];
    userPrompt?: string;
    delegationPrompt?: string;
    delegationDescription?: string;
    groupedToolCalls: GroupedToolCall[];
}
```

#### Tree Rendering Pattern:
- Uses `flattenTree()` function to convert hierarchical tree to flat array with `depth` for indentation
- Each node is indented by `depth * 24px`
- Collapsible nodes tracked via `Set<string>` in `collapsedNodes` state
- Click to select agent, separate click on chevron to expand/collapse

#### Stats Header:
- Total agents count
- Active agents count
- Total tools used
- Total todos
- Total tokens

#### UI Elements per Agent Row:
- Expand/collapse chevron (if has children)
- Agent type icon (emoji-based: PM, Research, Engineer, QA, Ops, Security, Data)
- Status icon (active, completed, error)
- Agent name (formatted from kebab-case to Title Case)
- Session ID (truncated to 8 chars)
- Stats badges: tool count, todo count, sub-agent count
- Duration (auto-formatted: ms, s, or m:s)

#### Selection Highlighting:
```
Selected: bg-cyan-50 dark:bg-cyan-500/20 border-l-cyan-500 ring-1 ring-cyan-300
Default:  alternating bg-slate-50/bg-white with hover states
```

### Component: `AgentDetail.svelte`

**Purpose**: Right panel detail view showing full information about a selected running agent.

**Sections** (vertically scrollable):
1. **Header**: Agent type icon + name, session ID (copyable), status, duration
2. **User Request** (PM only): Blue background card with expandable text
3. **Delegation Prompt** (sub-agents): Purple background card with expandable text
4. **Work Plans**: Amber cards with plan status, mode, plan file path, content
5. **Responses**: Slate cards with timestamp, type badge, content
6. **Tool Calls**: Grouped by tool name, clickable to navigate to Tools tab
7. **Todo List**: Timeline of todo activities with status icons
8. **Delegated Agents**: Summary cards of child agents

**Key UX Pattern**: Tool calls are clickable - clicking navigates to the Tools tab and selects the corresponding tool (cross-tab navigation via `handleToolClickFromAgent`).

---

## 4. Config Tab (Configuration Management)

### Component: `ConfigView.svelte`

**Purpose**: Master configuration management interface with sub-tabs.

**Dual-Panel Design**: Single component used in both panels:
- `panelSide="left"`: Shows summary cards, sub-tabs, and list views
- `panelSide="right"`: Shows detail views for selected items

### Config Sub-Tabs

```typescript
type ConfigSubTab = 'agents' | 'skills' | 'sources' | 'skill-links';
```

Sub-tab styling (different from main tabs):
```
Active:   bg-white dark:bg-slate-900 text-cyan-700 border border-b-0
Inactive: text-slate-500 hover:text-slate-700
```

### Left Panel Layout

1. **Active Session Warning Banner** (conditional, amber themed)
2. **Summary Cards Row**: Deployed agents count, available count, deployed skills count, sources count + "Auto-Configure" button
3. **Error Banner** (conditional, red themed)
4. **Sub-tabs**: Agents | Skills | Sources | Skill Links
5. **Validation Panel**: Always visible, collapsed by default, shows errors/warnings/info
6. **Sub-tab Content**: The active list component

### Right Panel (Detail View)

Renders one of:
- **Agent Detail**: Name, badges, description, metadata grid (version, type/category, location/source, priority), path, specializations/tags, source URL
- **Skill Detail**: Name, badges, description, category, collection, deploy mode, deploy date, path
- **Source Detail**: ID, type badge, URL, priority, status, branch, subdirectory
- **Empty State**: Gear icon + "Select an item from the list to view details"

---

## 5. AgentsList Component

**File**: `config/AgentsList.svelte`

### Props
```typescript
interface Props {
    deployedAgents: DeployedAgent[];
    availableAgents: AvailableAgent[];
    loading: LoadingState;
    onSelect: (agent: DeployedAgent | AvailableAgent) => void;
    selectedAgent: DeployedAgent | AvailableAgent | null;
    onSessionWarning?: (active: boolean) => void;
}
```

### Layout Pattern

**Two collapsible sections**:

1. **"Deployed (N)"** - expandable header with count
   - List of deployed agents
   - Each item shows: name, Core badge, version badge, specializations
   - Core agents show lock icon (undeploy protected)
   - Non-core agents show trash icon for undeploy
   - Selection highlighting: `bg-cyan-50 dark:bg-cyan-900/20 border-l-2 border-l-cyan-500`

2. **"Available (N)"** - expandable header with count
   - "Deploy All (N)" button when multiple undeployed agents exist
   - Each item shows: name, deployed checkmark, source badge, description (truncated to 80 chars)
   - Deploy button for undeployed agents (cyan themed)
   - Deploying spinner animation

### Search
- SearchInput component at top with debounced search (300ms default)
- Filters both deployed and available agents by name and description

### Actions
- **Deploy**: POST to store, handles 409 conflicts with force redeploy dialog
- **Undeploy**: Confirmation dialog requiring name input to confirm (ConfirmDialog)
- **Batch Deploy**: Deploy all available undeployed agents
- **Session Warning**: Checks for active Claude Code sessions after mutations

### Deployed Agent Data Shape
```typescript
interface DeployedAgent {
    name: string;
    location: string;     // e.g., "project"
    path: string;
    version: string;
    type: string;
    specializations?: string[];
    is_core: boolean;
}
```

### Available Agent Data Shape
```typescript
interface AvailableAgent {
    agent_id: string;
    name: string;
    description: string;
    version: string;
    source: string;
    source_url: string;
    priority: number;
    category: string;
    tags: string[];
    is_deployed: boolean;
}
```

---

## 6. SkillsList Component

**File**: `config/SkillsList.svelte`

### Layout Pattern

Very similar to AgentsList with key differences:

1. **Mode Header**: Shows current deployment mode (Full/Selective) with "Switch Mode" button
2. **Deployed Skills Section**: Similar to agents but with:
   - System badge for immutable collections (`PM_CORE_SKILLS`, `CORE_SKILLS`)
   - Category badge
   - Deploy mode badge (User Defined / Agent Referenced)
   - "Requested" badge for user-requested skills
   - Collection name
3. **Available Skills Section**: Similar to agents but with:
   - Deployed checkmark
   - Category badge
   - Description preview

### Deployed Skill Data Shape
```typescript
interface DeployedSkill {
    name: string;
    path: string;
    description: string;
    category: string;
    collection: string;
    is_user_requested: boolean;
    deploy_mode: 'agent_referenced' | 'user_defined';
    deploy_date: string;
}
```

### Available Skill Data Shape
```typescript
interface AvailableSkill {
    name: string;
    description: string;
    category: string;
    collection: string;
    is_deployed: boolean;
}
```

### Key Differences from AgentsList
- Has deployment mode context (Full vs Selective)
- Skills can be "System" (immutable, lock icon) vs regular
- Skills have more metadata: deploy_mode, deploy_date, collection, is_user_requested
- No "Deploy All" batch button for skills (unlike agents)

---

## 7. Skill Links View

**File**: `config/SkillLinksView.svelte`

### Layout
Dual-panel within the left panel:
- **Left half**: `AgentSkillPanel` - paginated agent list (50 per page) with search, skill count badges
- **Right half**: `SkillChipList` - skills grouped by source type for selected agent

### Skill Link Groups
- User Defined
- Required (Frontmatter)
- Content Markers
- Inferred

### SkillChip Component
Individual chips showing skill name with visual indicators for deployment status and auto-management.

---

## 8. Validation Panel

**File**: `config/ValidationPanel.svelte`

### Behavior
- Fetches from `GET /api/config/validate` on mount
- Collapsible with issue count badges
- Sorted by severity: errors > warnings > info
- States: Loading, Error (with retry), Healthy (green), Issues (expandable)

### Issue Display
```typescript
interface ValidationIssue {
    severity: 'error' | 'warning' | 'info';
    message: string;
    path?: string;
    suggestion?: string;
}
```

---

## 9. Shared UI Components

### Badge (`components/Badge.svelte`)
- **Text-based badge** (non-snippet version used in Config tab)
- Variants: default (slate), primary (cyan), success (green), warning (amber), danger (red), info (blue)
- Sizes: sm (`px-2 py-0.5 text-xs`), md (`px-2.5 py-1 text-sm`)
- Uses `rounded-full` pill shape

### Badge (`components/shared/Badge.svelte`)
- **Snippet-based badge** (takes children snippet instead of text prop)
- Different variant color scheme (darker backgrounds)
- **NOTE**: There are TWO Badge components with similar but different APIs and color schemes. This is an inconsistency.

### SearchInput (`components/shared/SearchInput.svelte`)
- Search icon prefix, clear button suffix
- Debounced input (configurable delay, default 300ms)
- Tailwind styled input with focus ring

### ConfirmDialog (`components/shared/ConfirmDialog.svelte`)
- Built on Modal component
- Optional type-to-confirm input
- Destructive (red) and non-destructive (cyan) variants
- Warning icon for destructive actions

### Modal (`components/shared/Modal.svelte`)
- Backdrop click to close, Escape to close
- Snippets: children, footer
- Sizes: sm, md, lg

### Toast (`components/shared/Toast.svelte`)
- Global notification system
- Types: success, error, warning, info
- Managed by `toastStore`

### EmptyState (`components/shared/EmptyState.svelte`)
- Standard empty state display with message

### PaginationControls (`components/shared/PaginationControls.svelte`)
- Previous/Next navigation
- Page/total display
- Used in AgentSkillPanel (skill-links tab)

---

## 10. API Endpoints

### Backend: `services/monitor/config_routes.py`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/config/project/summary` | GET | High-level config overview (counts, mode) |
| `/api/config/agents/deployed` | GET | List deployed agents |
| `/api/config/agents/available` | GET | List available agents from git sources |
| `/api/config/skills/deployed` | GET | List deployed skills |
| `/api/config/skills/available` | GET | List available skills from collections |
| `/api/config/sources` | GET | List configured sources |
| `/api/config/skill-links/` | GET | Skill-to-agent linking data |
| `/api/config/skill-links/agent/{agent_name}` | GET | Skills linked to specific agent |
| `/api/config/validate` | GET | Run configuration validation |

### Mutation Endpoints (from config_api handlers):

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/config/agents/deploy` | POST | Deploy a single agent |
| `/api/config/agents/{name}` | DELETE | Undeploy an agent |
| `/api/config/agents/deploy-collection` | POST | Batch deploy agents |
| `/api/config/skills/deploy` | POST | Deploy a single skill |
| `/api/config/skills/{name}` | DELETE | Undeploy a skill |
| `/api/config/skills/deployment-mode` | GET/PUT | Get/switch deployment mode |
| `/api/config/sources/{type}` | POST/PATCH/DELETE | CRUD sources |
| `/api/config/sources/{type}/sync` | POST | Sync a source |
| `/api/config/sources/sync-all` | POST | Sync all sources |
| `/api/config/auto-configure/detect` | POST | Detect project toolchain |
| `/api/config/auto-configure/preview` | POST | Preview auto-config |
| `/api/config/auto-configure/apply` | POST | Apply auto-config |
| `/api/config/active-sessions` | GET | Check for active Claude sessions |

### Data Flow
```
Backend (Python/aiohttp) --> REST API --> Frontend Store (writable) --> $effect subscription --> $state --> Component
                                     \
                                      --> Socket.IO events --> handleConfigEvent() --> refetch stores
```

---

## 11. State Management

### Config Store (`stores/config.svelte.ts`)

Uses Svelte 4 `writable()` stores:
```typescript
export const projectSummary = writable<ProjectSummary | null>(null);
export const deployedAgents = writable<DeployedAgent[]>([]);
export const availableAgents = writable<AvailableAgent[]>([]);
export const deployedSkills = writable<DeployedSkill[]>([]);
export const availableSkills = writable<AvailableSkill[]>([]);
export const configSources = writable<ConfigSource[]>([]);
export const configLoading = writable<LoadingState>({...});
export const configErrors = writable<ConfigError[]>([]);
export const syncStatus = writable<Record<string, SyncState>>({});
export const mutating = writable(false);
```

### Bridge Pattern (Svelte 4 store -> Svelte 5 reactivity)
In ConfigView.svelte, each writable store is subscribed to via `$effect()` and its value copied into a `$state` variable:
```typescript
let deployedAgentsData = $state<DeployedAgent[]>([]);
$effect(() => {
    const unsub = deployedAgents.subscribe(v => { deployedAgentsData = v; });
    return unsub;
});
```

This pattern is used consistently across all config data. It's verbose but necessary for Svelte 5 Runes compatibility with Svelte 4 stores.

### SkillLinks Store (`stores/config/skillLinks.svelte.ts`)
Separate store for skill-to-agent linking data. Follows same writable + transform pattern. Transforms backend flat response format to frontend hierarchical format.

---

## 12. Identified Patterns and Conventions

### UI Patterns

1. **Collapsible Sections**: Deployed/Available sections use expandable headers with chevron rotation
2. **List Item Selection**: Cyan left border + background highlight (`bg-cyan-50 dark:bg-cyan-900/20 border-l-2 border-l-cyan-500`)
3. **Loading States**: Spinner SVG + text message, consistent across all components
4. **Empty States**: Centered text with optional icon, search-aware messaging
5. **Action Buttons**: Small icon buttons inline with list items, with hover color changes
6. **Badges**: Pill-shaped, color-coded by semantic meaning (deployed=green, core=cyan, system=red, etc.)
7. **Destructive Actions**: Confirmation dialog with type-to-confirm, red styling
8. **Multi-Step Modals**: ModeSwitch and AutoConfig use step indicators (1 -> 2)
9. **Toast Notifications**: Global toast for action results (success/error)

### Color Conventions

| Semantic | Color |
|----------|-------|
| Primary/Accent | Cyan-600 (`#0891b2`) |
| Success/Deployed | Green/Emerald |
| Warning/Requested | Amber |
| Error/Danger/System | Red |
| Info/Available | Blue |
| Default/Neutral | Slate |

### Responsive Design
- No explicit mobile breakpoints detected
- The split-panel layout uses percentage-based widths with min-width constraints
- Scrollable panels within fixed-height containers
- Text truncation with `truncate` class

---

## 13. Identified Limitations and Inconsistencies

### Critical Issues

1. **Duplicate Badge Components**: Two `Badge.svelte` files exist with different APIs:
   - `components/Badge.svelte` (text prop, used in Config tab)
   - `components/shared/Badge.svelte` (snippet children, different color scheme)
   - This creates confusion and inconsistent styling across the app

2. **No Sorting Controls**: Neither agents nor skills lists have sort controls. Items are displayed in the order returned by the API with no client-side sorting options.

3. **No Filtering by Category/Tag**: Available agents have `category` and `tags` fields, available skills have `category` and `collection`. None of these have filter UI. Only text search is available.

4. **Limited Metadata Display in Lists**: The list items show minimal information. Key metadata (description, tags, category) is only visible in the right-panel detail view. Users must click each item to see useful context.

5. **No Bulk Selection**: Only batch "Deploy All" exists for agents. No multi-select checkboxes for selective batch operations.

### UX Gaps

6. **No Agent Description in Deployed List**: Deployed agents only show name, Core badge, version, and specializations. There's no description field in the `DeployedAgent` type. Users lose context about what an agent does after deployment.

7. **Agent vs Config Confusion**: The "Agents" main tab shows runtime agent monitoring (AgentsView), while the "Config > Agents" sub-tab shows agent configuration (AgentsList). The names overlap and could confuse users.

8. **No Skill Content Preview**: Neither deployed nor available skills show any content preview. Users can't see what a skill actually does without leaving the dashboard.

9. **Skill Links Tab is Read-Only**: Shows which skills are linked to which agents but provides no way to modify the links.

10. **No Visual Diff**: When deploying/undeploying, there's no diff view showing what will change in the agent definition files.

11. **Missing Pagination**: AgentsList and SkillsList don't paginate. If there are many items, the list scrolls infinitely. Only AgentSkillPanel (skill-links) has pagination.

### Technical Debt

12. **Svelte 4/5 Bridge Pattern**: The verbose `$effect(() => { store.subscribe() })` pattern is used everywhere. This should eventually migrate to Svelte 5's native `$state.snapshot()` or the `.subscribe` rune if it becomes available.

13. **Inconsistent Type Guards**: `isDeployedAgent` uses `'is_core' in agent` heuristic. `isDeployedSkill` uses `'deploy_mode' in skill`. These are fragile if types change.

14. **Hardcoded System Detection**: System/immutable detection uses hardcoded arrays (`PM_CORE_SKILLS`, `CORE_SKILLS`, `bobmatnyc/claude-mpm-agents/agents`). Should come from backend.

15. **No Caching**: Available agents/skills are refetched every time the Config tab opens. No client-side caching with staleness checks.

---

## 14. Component Dependency Map

```
+page.svelte
  +-- Header.svelte
  +-- EventStream.svelte
  +-- ToolsView.svelte
  +-- FilesView.svelte
  +-- AgentsView.svelte .............. (Real-time monitoring)
  |   +-- (inline tree rendering)
  +-- AgentDetail.svelte ............. (Real-time agent detail)
  |   +-- CopyButton.svelte
  +-- ConfigView.svelte .............. (Configuration management)
  |   +-- AgentsList.svelte
  |   |   +-- Badge.svelte
  |   |   +-- SearchInput.svelte (shared/)
  |   |   +-- ConfirmDialog.svelte (shared/)
  |   +-- SkillsList.svelte
  |   |   +-- Badge.svelte
  |   |   +-- SearchInput.svelte (shared/)
  |   |   +-- ConfirmDialog.svelte (shared/)
  |   +-- SourcesList.svelte
  |   |   +-- Badge.svelte
  |   |   +-- Modal.svelte (shared/)
  |   |   +-- SourceForm.svelte
  |   |   +-- SyncProgress.svelte
  |   +-- SkillLinksView.svelte
  |   |   +-- AgentSkillPanel.svelte
  |   |   |   +-- SearchInput.svelte (shared/)
  |   |   |   +-- Badge.svelte
  |   |   |   +-- PaginationControls.svelte (shared/)
  |   |   +-- SkillChipList.svelte
  |   |       +-- SkillChip.svelte
  |   |       +-- EmptyState.svelte (shared/)
  |   +-- ValidationPanel.svelte
  |   |   +-- ValidationIssueCard.svelte
  |   +-- ModeSwitch.svelte ......... (Modal)
  |   |   +-- Modal.svelte (shared/)
  |   |   +-- Badge.svelte
  |   +-- AutoConfigPreview.svelte ... (Modal)
  |       +-- Modal.svelte (shared/)
  |       +-- Badge.svelte
  |       +-- DeploymentPipeline.svelte
  +-- JSONExplorer.svelte
  +-- FileViewer.svelte
  +-- TokensView.svelte
  +-- Toast.svelte (shared/)
```

---

## 15. Summary of Key Findings

### What's Working Well
- Consistent dark mode support with Tailwind
- Clean split-panel layout with resizable divider
- Good use of confirmation dialogs for destructive actions
- Real-time Socket.IO integration for config events
- Type-safe TypeScript throughout
- Clear separation of concerns between monitoring (Agents tab) and configuration (Config tab)

### What Needs Improvement
- **Information density**: List items show too little metadata; need expandable previews or richer list cards
- **Filtering/sorting**: Only text search is available; need category filters, sort controls
- **Duplicate components**: Badge component exists twice with different APIs
- **Missing metadata in deployed items**: Deployed agents lack description; deployed skills lack content preview
- **No pagination** on main agent/skill lists
- **Read-only skill links**: Can view but not modify skill-to-agent associations
- **No bulk operations**: Limited to "Deploy All" for agents; no multi-select pattern

### Architecture Strengths for Extension
- Component-based architecture makes adding new sub-tabs straightforward
- Store pattern supports easy addition of new data sources
- Badge, Modal, ConfirmDialog, SearchInput patterns are well-established and reusable
- The dual-panel ConfigView pattern (left list + right detail) is extensible for new item types
