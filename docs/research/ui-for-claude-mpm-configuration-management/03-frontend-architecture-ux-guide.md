# Frontend Architecture & UX Extension Guide

## Claude MPM Dashboard - Svelte 5 SPA Analysis

**Date**: 2026-02-13
**Scope**: Complete frontend architecture analysis for configuration UI integration
**Status**: Implementation-ready reference

---

## Part 1: Frontend Architecture Analysis

### 1.1 Component Tree & File Organization

```
dashboard-svelte/
├── src/
│   ├── app.css                          # Global styles + CSS variables + Tailwind directives
│   ├── routes/
│   │   ├── +layout.ts                   # SPA config: prerender=true, ssr=false
│   │   ├── +layout.svelte               # Root layout: Socket.IO connect, theme class
│   │   └── +page.svelte                 # Main page: tab navigation, split panels, all state
│   └── lib/
│       ├── types/
│       │   └── events.ts                # ClaudeEvent, Tool, SocketState, StreamEvent interfaces
│       ├── stores/
│       │   ├── socket.svelte.ts         # Socket.IO connection + event bus (traditional writable stores)
│       │   ├── tools.svelte.ts          # Derived store: events → correlated Tool[]
│       │   ├── agents.svelte.ts         # Derived store: events → AgentNode tree
│       │   ├── files.svelte.ts          # Utility functions (no store - component manages state)
│       │   └── theme.svelte.ts          # Svelte 5 class-based store with $state rune
│       ├── components/
│       │   ├── Header.svelte            # Top bar: project/stream selectors, theme toggle, connection status
│       │   ├── EventStream.svelte       # Left panel view: raw event list with activity filter
│       │   ├── ToolsView.svelte         # Left panel view: correlated tool executions
│       │   ├── AgentsView.svelte        # Left panel view: hierarchical agent tree
│       │   ├── TokensView.svelte        # Left panel view: token usage breakdown (hidden)
│       │   ├── FilesView.svelte         # Left panel view: touched files list + radial tree
│       │   ├── AgentDetail.svelte       # Right panel: selected agent details
│       │   ├── JSONExplorer.svelte      # Right panel: event/tool JSON viewer
│       │   ├── FileViewer.svelte        # Right panel: syntax-highlighted file content + git diff
│       │   ├── FileTreeRadial.svelte    # D3-based radial file tree visualization
│       │   ├── MarkdownViewer.svelte    # Markdown renderer with mermaid support
│       │   └── CopyButton.svelte        # Reusable clipboard copy button
│       └── utils/
│           ├── event-correlation.ts     # pre_tool/post_tool event matching logic
│           └── file-tree-builder.ts     # Flat files → D3 hierarchy converter
├── package.json                         # Dependencies + scripts
├── vite.config.ts                       # Dev server + proxy config
├── svelte.config.js                     # Static adapter → ../dashboard/static/svelte-build
├── tailwind.config.js                   # Tailwind v3, class-based dark mode
├── postcss.config.js                    # PostCSS with Tailwind + autoprefixer
└── tsconfig.json                        # TypeScript config
```

### 1.2 Component Hierarchy (Parent-Child Relationships)

```
+layout.svelte                           [ROOT - Socket.IO lifecycle, theme class]
  └── +page.svelte                       [MAIN - All tab/panel state management]
       ├── Header.svelte                 [Header bar - reads socketStore directly]
       │
       ├── [LEFT PANEL - conditional on viewMode]
       │   ├── EventStream.svelte        [viewMode='events']
       │   ├── ToolsView.svelte          [viewMode='tools']
       │   ├── AgentsView.svelte         [viewMode='agents']
       │   ├── TokensView.svelte         [viewMode='tokens' - hidden]
       │   └── FilesView.svelte          [viewMode='files']
       │       └── FileTreeRadial.svelte [Sub-view when tree mode selected]
       │           └── (D3 SVG)
       │
       └── [RIGHT PANEL - conditional on viewMode + selection]
            ├── JSONExplorer.svelte      [Events/Tools: JSON data explorer]
            ├── FileViewer.svelte        [Files: syntax-highlighted content + diff]
            │   └── MarkdownViewer.svelte [Sub-view for .md files]
            └── AgentDetail.svelte       [Agents: detailed agent info]
                └── CopyButton.svelte    [Reusable - used in many places]
```

### 1.3 Navigation System

**Mechanism**: Conditional rendering via a `viewMode` state variable in `+page.svelte`.

```typescript
// +page.svelte:20
type ViewMode = 'events' | 'tools' | 'files' | 'agents' | 'tokens';
let viewMode = $state<ViewMode>('events');
```

**Tab rendering** (`+page.svelte:198-237`):
```svelte
<div class="flex gap-0 px-2 pt-2">
  <button onclick={() => viewMode = 'events'} class="tab" class:active={viewMode === 'events'}>
    Events
  </button>
  <!-- ... more buttons ... -->
</div>
```

**There is NO router** - the entire app is a single SvelteKit page with `+layout.ts` exporting `prerender = true` and `ssr = false`. All view switching is done through the `viewMode` state variable with `{#if}` / `{:else if}` blocks.

**Adding a new tab** requires:
1. Extending the `ViewMode` type union
2. Adding a `<button>` in the tab bar
3. Adding an `{:else if}` block in both left and right panels
4. Updating the selection-clearing `$effect` at line 109

### 1.4 State Management

#### Store Architecture

| Store | Type | File | Mechanism | Purpose |
|-------|------|------|-----------|---------|
| `socketStore` | Singleton factory function | `socket.svelte.ts` | Traditional Svelte `writable()` stores | Socket.IO connection, event bus, stream tracking |
| `toolsStore` | Derived | `tools.svelte.ts` | `derived()` from filtered events store | Correlated pre/post tool events → Tool[] |
| `agentsStore` | Derived | `agents.svelte.ts` | `derived()` from filtered events store | Event tree → hierarchical AgentNode |
| `themeStore` | Class instance | `theme.svelte.ts` | Svelte 5 `$state` rune in class | Dark/light theme with localStorage |
| `filesStore` | N/A (not a store) | `files.svelte.ts` | Utility functions only | File extraction helpers, no reactive state |

#### Data Flow Pattern

```
Socket.IO Server (http://localhost:8765)
    │
    ▼ (WebSocket events: claude_event, hook_event, tool_event, etc.)
socketStore.handleEvent()
    │
    ├── events: writable<ClaudeEvent[]>  ──────→ EventStream component
    ├── streams: writable<Set<string>>   ──────→ Header (stream selector)
    ├── streamMetadata: writable<Map>    ──────→ Header (project names)
    ├── streamActivity: writable<Map>    ──────→ Header (active indicators)
    ├── selectedStream: writable<string> ──────→ All views (filtering)
    └── projectFilter: writable<'current'|'all'> → Header + filtering
         │
         ▼
    +page.svelte creates filteredEventsStore (derived from events + selectedStream)
         │
         ├──→ createToolsStore(filteredEventsStore) → derived → Tool[]
         └──→ createAgentsStore(filteredEventsStore) → derived → AgentNode tree
```

#### Store Subscription Pattern (Hybrid Svelte 4/5)

The stores use traditional Svelte `writable()`/`derived()` but components consume them through Svelte 5's `$effect` + `$state` pattern:

```typescript
// Pattern used in +page.svelte for derived stores
let toolsWrapper = $state<{ value: Tool[] }>({ value: [] });

$effect(() => {
  const unsubscribe = toolsStore.subscribe(value => {
    toolsWrapper = { value };  // New object reference triggers reactivity
  });
  return unsubscribe;
});

let tools = $derived(toolsWrapper.value);
```

```typescript
// Pattern used in components for socketStore (traditional $ prefix)
const { events: allEventsStore } = socketStore;
let allEvents = $state<ClaudeEvent[]>([]);

$effect(() => {
  const unsubscribe = allEventsStore.subscribe(value => {
    allEvents = value;
  });
  return unsubscribe;
});
```

**IMPORTANT**: The `socketStore` writable stores cannot use `$` auto-subscription because they're traditional Svelte stores in a `.ts` file, not Svelte 5 runes. Components bridge this with `$effect` + manual `.subscribe()`.

#### Theme Store (Pure Svelte 5 Runes)

```typescript
class ThemeStore {
  current = $state<'light' | 'dark'>('dark');

  toggle = () => {
    this.current = this.current === 'dark' ? 'light' : 'dark';
    localStorage.setItem('theme', this.current);
    this.applyTheme(this.current);
  };
}
export const themeStore = new ThemeStore();
```

Components access directly: `let currentTheme = $derived(themeStore.current);`

### 1.5 Data Fetching Patterns

| Pattern | Usage | Example |
|---------|-------|---------|
| **Socket.IO real-time** | Primary data source for all events | `socketStore.connect()` in `+layout.svelte:onMount()` |
| **fetch() one-time** | Working directory, file content, git diffs | `fetch('/api/working-directory')` in socket store + FilesView |
| **fetch() on-demand** | File content when user selects a file | `fetchFileContent(path)` in `FilesView.selectFile()` |
| **Derived computation** | Tools and Agents from events | `createToolsStore(eventsStore)` — recomputes on every event |
| **localStorage cache** | Event history per stream (last 50) | `saveCachedEvents()` / `loadCachedEvents()` in socket store |

**API Base URL**: `http://localhost:8765` (hardcoded in socket store, proxied via Vite dev server)

**Loading states**: Managed per-component with `$state` booleans:
```typescript
let contentLoading = $state(false);  // FilesView, FileViewer
let isDiffLoading = $state(false);   // FileViewer
```

**Error handling**: Console logging + inline error messages. No global error boundary.

### 1.6 UI Component Library & Primitives

#### Available Primitives

| Primitive | Implementation | Used In |
|-----------|----------------|---------|
| **Buttons** | Tailwind classes, no shared component | Every view (`<button class="...">`) |
| **Select dropdowns** | Native `<select>` with Tailwind | Header (stream/project filter), EventStream (activity), ToolsView (tool type) |
| **Text input** | Native `<input type="text">` with Tailwind | FilesView (filename filter) |
| **Toggle buttons** | Custom grouped buttons | FilesView (table/tree), FileViewer (content/changes) |
| **Tabs** | Custom styled buttons with `.tab`/`.active` CSS | +page.svelte (view mode) |
| **Tables** | CSS Grid (`grid-cols-[...]`) | EventStream, ToolsView, FilesView, JSONExplorer |
| **Tree view** | Custom recursive rendering with indent | AgentsView, TokensView |
| **Badges/chips** | Inline `<span>` with Tailwind | Status indicators, counts throughout |
| **Copy button** | `CopyButton.svelte` — the ONLY reusable component | AgentDetail, FileViewer, JSONExplorer, FilesView |
| **Expandable text** | Custom toggle with truncation | AgentDetail (prompts, plans, responses) |
| **Split panel** | Custom drag divider in +page.svelte | Main layout |
| **Empty states** | Inline SVG + text patterns | All views |

#### NO shared form components exist today. No modals, no toasts, no validation patterns, no checkboxes, no radio buttons, no switches/toggles.

### 1.7 Styling System

**Framework**: Tailwind CSS v3.4.16 with PostCSS + autoprefixer

**Dark mode**: Class-based (`darkMode: 'class'` in tailwind.config.js). The `<html>` element gets `.dark` class applied by `ThemeStore.applyTheme()`.

**Pattern**: Dual classes everywhere:
```svelte
<div class="bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
```

**CSS Variables** (in `app.css`): Used ONLY by `FileViewer.svelte` for theme-aware scoped styles:
```css
:root { --color-bg-primary: #ffffff; --color-primary: #0891b2; ... }
.dark { --color-bg-primary: #0f172a; --color-primary: #06b6d4; ... }
```

**Scoped styles**: Some components use `<style>` blocks (FileViewer, Header, +page.svelte) for complex styling that can't be done with Tailwind utility classes alone.

**Color palette**: Slate for neutrals, Cyan (#0891b2/cyan-600) as primary accent, standard semantic colors (green/success, red/error, yellow/warning, blue/info, purple/special).

**Font**: System font stack. Monospace: `'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace`.

### 1.8 Build Pipeline

**SvelteKit** with `@sveltejs/adapter-static` — builds to static HTML/JS/CSS.

**Build output**: `../dashboard/static/svelte-build/` (relative to svelte.config.js)
This maps to: `src/claude_mpm/dashboard/static/svelte-build/`

**Python serves these** as static files via the Flask/FastAPI dashboard server at `/`.

**Dev workflow**:
```bash
cd src/claude_mpm/dashboard-svelte
npm run dev          # Vite dev server on port 5173
```

**Vite proxy config** (`vite.config.ts`):
- `/api/*` → `http://localhost:8765` (Python backend)
- `/socket.io/*` → `http://localhost:8765` (WebSocket, with `ws: true`)

**Key dependencies**:
| Package | Version | Purpose |
|---------|---------|---------|
| `svelte` | ^5.2.9 | Framework (Svelte 5 with runes) |
| `@sveltejs/kit` | ^2.11.1 | SvelteKit framework |
| `@sveltejs/adapter-static` | ^3.0.6 | Static site generation |
| `tailwindcss` | ^3.4.16 | Utility-first CSS |
| `socket.io-client` | ^4.8.1 | Real-time communication |
| `d3` | ^7.9.0 | File tree visualization |
| `shiki` | ^3.20.0 | Code highlighting (present but not directly used - svelte-highlight used instead) |
| `svelte-highlight` | ^7.9.0 | Syntax highlighting in FileViewer |
| `marked` | ^17.0.1 | Markdown rendering |
| `mermaid` | ^11.12.2 | Diagram rendering in markdown |
| `diff` | ^8.0.2 | Diff computation |
| `diff2html` | ^3.4.52 | Diff rendering |

---

## Part 2: UX Design Considerations

### 2.1 Skill-to-Agent Linking Matrix

**Challenge**: Many-to-many relationship. Users need to see which skills are assigned to which agents and modify these assignments.

**Recommended UX Pattern**: **Dual-panel with chip-based assignment**

```
┌─────────────────────────────────┬──────────────────────────────────┐
│ AGENTS (left list)              │ SKILL ASSIGNMENTS (right detail) │
│                                 │                                  │
│ > PM Agent             [12]     │ Agent: PM Agent                  │
│   Research Agent       [8]      │ ─────────────────────            │
│   Engineer Agent       [15]     │ Assigned Skills:                 │
│   QA Agent             [5]      │ [test-driven-dev ×]              │
│                                 │ [git-workflow ×]                 │
│                                 │ [systematic-debugging ×]         │
│                                 │                                  │
│                                 │ Available Skills:                │
│                                 │ ┌───────────────────────┐       │
│                                 │ │ Search skills...      │       │
│                                 │ └───────────────────────┘       │
│                                 │ [+ webapp-testing]               │
│                                 │ [+ code-review]                  │
│                                 │ [+ brainstorming]                │
└─────────────────────────────────┴──────────────────────────────────┘
```

**Implementation details**:
- Left list: clickable agent rows (reuse AgentsView pattern)
- Right panel: selected agent's skills as removable chips
- Searchable "Available Skills" list below
- Click `+` to assign, click `x` to unassign
- Badge count `[12]` shows skill count per agent
- Bulk mode: checkbox multi-select on agents, "Assign to selected" action

**Alternative for overview**: Matrix/grid view toggle:
```
              skill-a  skill-b  skill-c  skill-d
PM Agent        [x]      [x]      [ ]      [x]
Research        [ ]      [x]      [x]      [ ]
Engineer        [x]      [ ]      [x]      [x]
```

### 2.2 agent_referenced vs user_defined Mode Switch

**Challenge**: Potentially destructive — switching modes may reset or override skill configurations.

**Recommended UX Pattern**: **Confirmation dialog with preview of changes**

```
┌─────────────────────────────────────────┐
│  ⚠️  Switch to "agent_referenced" mode?  │
│                                          │
│  Current mode: user_defined              │
│                                          │
│  This will:                              │
│  • Scan CLAUDE.md files for agent refs   │
│  • Override 3 manual skill assignments   │
│  • Add 7 auto-detected skills            │
│                                          │
│  Changes preview:                        │
│  - Remove: [custom-skill-1]              │
│  - Remove: [custom-skill-2]              │
│  + Add: [webapp-testing] (from agent X)  │
│  + Add: [git-workflow] (from agent Y)    │
│                                          │
│  [Cancel]            [Switch Mode →]     │
└─────────────────────────────────────────┘
```

**Implementation details**:
- Toggle switch with "user_defined" / "agent_referenced" labels
- Before switching, call API to get diff preview
- Show impact summary in a modal overlay
- "Switch Mode" button is destructive-red styled
- After switch, show success toast with undo option (30s window)

### 2.3 Auto-Configure Wizard

**Challenge**: Multi-step flow with long-running operations.

**Recommended UX Pattern**: **Stepper wizard with progressive disclosure**

```
Step 1          Step 2           Step 3          Step 4
[Detect]  ───→  [Recommend]  ───→  [Preview]  ───→  [Apply]
  ●              ○                 ○               ○

┌─────────────────────────────────────────────────────────┐
│  Step 1: Detecting Skill Sources                        │
│                                                          │
│  Scanning...                                             │
│  ┌──────────────────────────────────────────┐            │
│  │ ████████████░░░░░░░░  60%                │            │
│  │ Scanning git repositories...              │            │
│  └──────────────────────────────────────────┘            │
│                                                          │
│  Found:                                                  │
│  ✅ obra/superpowers (12 skills)                         │
│  ✅ mrgoonie/claudekit-skills (8 skills)                 │
│  🔄 zxkane/aws-skills (scanning...)                      │
│  ⏳ custom-skills/ (queued)                              │
│                                                          │
│  [Cancel]                           [Next: Review →]     │
└─────────────────────────────────────────────────────────┘
```

**Step flow**:
1. **Detect**: Scan configured git sources + local directories. Show progress bar + found sources incrementally.
2. **Recommend**: Display recommended skills per agent based on project tech stack. Users can check/uncheck.
3. **Preview**: Show exact file changes that will be made to `~/.claude/skills/`. Diff-style preview.
4. **Apply**: Execute deployment with per-skill progress. Show success/failure per item.

**Key UX elements**:
- Stepper indicator at top showing progress
- "Back" button on each step (except during active operations)
- Cancel with confirmation if operations are in progress
- Each step loads independently — can restart from any step

### 2.4 Git Source Sync Progress

**Challenge**: Long-running network I/O for cloning/pulling git repositories.

**Recommended UX Pattern**: **Real-time progress feed with per-source status**

```
┌─────────────────────────────────────────────────────────┐
│  Syncing Skill Sources                        [Cancel]   │
│                                                          │
│  ✅ obra/superpowers             Synced (2.3s)           │
│     12 skills · Last: 2 min ago                          │
│                                                          │
│  🔄 mrgoonie/claudekit-skills   Cloning...               │
│     ████████████░░░░░░░░  65% · 1.2 MB / 1.8 MB         │
│                                                          │
│  ⏳ zxkane/aws-skills            Queued                   │
│                                                          │
│  ❌ custom-repo/skills           Failed: Network timeout  │
│     [Retry]  [View Error]                                │
│                                                          │
│  Progress: 1/4 complete                                  │
└─────────────────────────────────────────────────────────┘
```

**Implementation details**:
- Use Socket.IO for real-time progress updates (backend emits progress events)
- Each source shows: status icon, name, progress bar (when active), timing
- Failed sources show inline error with retry button
- Cancel button sends abort signal (backend should support graceful abort)
- After completion, auto-transition to results summary

### 2.5 Conflict Resolution

**Challenge**: Multiple git sources may provide skills with the same ID.

**Recommended UX Pattern**: **Inline conflict cards with source comparison**

```
┌─────────────────────────────────────────────────────────┐
│  ⚠️  2 Conflicts Detected                               │
│                                                          │
│  ┌───────────────────────────────────────────────────┐   │
│  │  Conflict: "test-driven-development"               │   │
│  │                                                    │   │
│  │  Source A: obra/superpowers                        │   │
│  │  • Updated: 2 days ago · 45 lines                 │   │
│  │  • [Preview]                                      │   │
│  │                                                    │   │
│  │  Source B: custom-skills/                          │   │
│  │  • Updated: 1 week ago · 32 lines                 │   │
│  │  • [Preview]                                      │   │
│  │                                                    │   │
│  │  Resolution:                                      │   │
│  │  (●) Use Source A (obra/superpowers)               │   │
│  │  ( ) Use Source B (custom-skills/)                 │   │
│  │  ( ) Skip (don't deploy this skill)               │   │
│  └───────────────────────────────────────────────────┘   │
│                                                          │
│  [Resolve All (use newest)]        [Apply Selections]    │
└─────────────────────────────────────────────────────────┘
```

**Implementation details**:
- Card-based layout for each conflict
- Side-by-side preview (or tabbed) showing skill content from each source
- Radio button selection per conflict
- "Resolve All" bulk action (use newest, use first source, skip all)
- Remember resolution preferences for future syncs

### 2.6 Active Session Safety

**Challenge**: Modifying skill/agent files while Claude Code sessions are active could cause issues.

**Recommended UX Pattern**: **Warning banner with session detection**

```
┌─────────────────────────────────────────────────────────┐
│  ⚠️  2 Active Claude Code Sessions Detected             │
│                                                          │
│  Changes to skills and agents will take effect on        │
│  new sessions only. Running sessions use cached configs. │
│                                                          │
│  Active sessions:                                        │
│  • claude-mpm (session abc123) — 5 min active            │
│  • my-project (session def456) — 2 min active            │
│                                                          │
│  [Continue Anyway]  [Wait for Sessions to End]           │
└─────────────────────────────────────────────────────────┘
```

**Implementation details**:
- Banner appears at top of configuration views when active sessions detected
- Yellow/amber warning styling (not blocking red)
- Uses existing Socket.IO `streamActivity` data to detect active sessions
- "Continue Anyway" dismisses warning (safe because changes only affect new sessions)
- Non-modal — users can still browse and configure, warning is informational

### 2.7 Two-Phase Deployment Visualization

**Challenge**: Making the Cache (index) → Deploy (copy to `~/.claude/skills/`) pipeline intuitive.

**Recommended UX Pattern**: **Pipeline visualization with status indicators**

```
┌─────────────────────────────────────────────────────────┐
│  Skill: test-driven-development                          │
│                                                          │
│  ┌──────────┐     ┌──────────┐     ┌──────────┐        │
│  │  SOURCE   │ ──→ │  CACHE   │ ──→ │ DEPLOYED │        │
│  │  ✅ Git   │     │  ✅ v2.1 │     │  ⚠️ v2.0 │        │
│  └──────────┘     └──────────┘     └──────────┘        │
│                                                          │
│  Cache has newer version. [Deploy Now]                   │
└─────────────────────────────────────────────────────────┘
```

**Implementation details**:
- Three-stage pipeline: Source → Cache → Deployed
- Each stage shows version/timestamp and status icon
- When cache is ahead of deployed, show "Deploy Now" action
- Batch deploy: "Deploy All Cached Changes" button
- Visual diff between cached and deployed versions on hover/click

---

## Part 3: Extension Guide — Adding Configuration Views

### 3.1 How to Add a New Tab/View

**Step 1**: Extend the `ViewMode` type in `+page.svelte`:

```typescript
// Before:
type ViewMode = 'events' | 'tools' | 'files' | 'agents' | 'tokens';

// After:
type ViewMode = 'events' | 'tools' | 'files' | 'agents' | 'tokens' | 'config';
```

**Step 2**: Add tab button in the tab bar (`+page.svelte`, after the Agents button ~line 226):

```svelte
<button
  onclick={() => viewMode = 'config'}
  class="tab"
  class:active={viewMode === 'config'}
>
  Config
</button>
```

**Step 3**: Add left panel view rendering (`+page.svelte`, inside the conditional block ~line 241):

```svelte
{:else if viewMode === 'config'}
  <ConfigView bind:selectedItem />
```

**Step 4**: Add right panel rendering (`+page.svelte`, inside the right panel conditional ~line 284):

```svelte
{:else if viewMode === 'config'}
  <ConfigDetail item={selectedItem} />
```

**Step 5**: Update the selection-clearing effect (`+page.svelte:109-127`):

```typescript
$effect(() => {
  if (viewMode === 'config') {
    selectedEvent = null;
    selectedTool = null;
    selectedFile = null;
    selectedAgent = null;
  }
  // ... existing cases
});
```

**Step 6**: Add imports at the top of `+page.svelte`:

```typescript
import ConfigView from '$lib/components/ConfigView.svelte';
import ConfigDetail from '$lib/components/ConfigDetail.svelte';
```

### 3.2 How to Create a New Store for Configuration State

**Option A: Traditional Svelte Store (recommended for data that comes from API)**

Create `src/lib/stores/config.svelte.ts`:

```typescript
import { writable, derived, get } from 'svelte/store';

// Types
export interface SkillConfig {
  id: string;
  name: string;
  source: string;
  version: string;
  deployed: boolean;
  cachedVersion?: string;
  agents: string[];       // Agent IDs this skill is assigned to
}

export interface AgentConfig {
  id: string;
  name: string;
  type: string;
  skills: string[];       // Skill IDs assigned to this agent
  mode: 'agent_referenced' | 'user_defined';
}

export interface ConfigState {
  skills: SkillConfig[];
  agents: AgentConfig[];
  sources: GitSource[];
  mode: 'agent_referenced' | 'user_defined';
  loading: boolean;
  error: string | null;
}

export interface GitSource {
  id: string;
  url: string;
  branch: string;
  lastSync: string | null;
  skillCount: number;
  status: 'synced' | 'syncing' | 'error' | 'pending';
}

function createConfigStore() {
  const state = writable<ConfigState>({
    skills: [],
    agents: [],
    sources: [],
    mode: 'user_defined',
    loading: false,
    error: null,
  });

  // Derived stores for filtered views
  const deployedSkills = derived(state, ($state) =>
    $state.skills.filter(s => s.deployed)
  );

  const cachedSkills = derived(state, ($state) =>
    $state.skills.filter(s => s.cachedVersion && !s.deployed)
  );

  const pendingDeployments = derived(state, ($state) =>
    $state.skills.filter(s => s.cachedVersion && s.cachedVersion !== s.version)
  );

  // Actions
  async function fetchConfig() {
    state.update(s => ({ ...s, loading: true, error: null }));
    try {
      const response = await fetch('/api/config/skills');
      const data = await response.json();
      if (data.success) {
        state.update(s => ({
          ...s,
          skills: data.skills,
          agents: data.agents,
          sources: data.sources,
          mode: data.mode,
          loading: false,
        }));
      } else {
        state.update(s => ({ ...s, loading: false, error: data.error }));
      }
    } catch (err) {
      state.update(s => ({
        ...s,
        loading: false,
        error: err instanceof Error ? err.message : 'Failed to fetch config',
      }));
    }
  }

  async function deploySkill(skillId: string) {
    try {
      const response = await fetch(`/api/config/skills/${skillId}/deploy`, {
        method: 'POST',
      });
      const data = await response.json();
      if (data.success) {
        // Update local state
        state.update(s => ({
          ...s,
          skills: s.skills.map(skill =>
            skill.id === skillId
              ? { ...skill, deployed: true, version: skill.cachedVersion || skill.version }
              : skill
          ),
        }));
      }
      return data;
    } catch (err) {
      return { success: false, error: String(err) };
    }
  }

  async function assignSkillToAgent(skillId: string, agentId: string) {
    try {
      const response = await fetch(`/api/config/skills/${skillId}/assign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ agent_id: agentId }),
      });
      const data = await response.json();
      if (data.success) {
        state.update(s => ({
          ...s,
          skills: s.skills.map(skill =>
            skill.id === skillId
              ? { ...skill, agents: [...skill.agents, agentId] }
              : skill
          ),
          agents: s.agents.map(agent =>
            agent.id === agentId
              ? { ...agent, skills: [...agent.skills, skillId] }
              : agent
          ),
        }));
      }
      return data;
    } catch (err) {
      return { success: false, error: String(err) };
    }
  }

  async function syncSource(sourceId: string) {
    state.update(s => ({
      ...s,
      sources: s.sources.map(src =>
        src.id === sourceId ? { ...src, status: 'syncing' as const } : src
      ),
    }));
    try {
      const response = await fetch(`/api/config/sources/${sourceId}/sync`, {
        method: 'POST',
      });
      const data = await response.json();
      if (data.success) {
        await fetchConfig();  // Refresh all data
      }
      return data;
    } catch (err) {
      state.update(s => ({
        ...s,
        sources: s.sources.map(src =>
          src.id === sourceId ? { ...src, status: 'error' as const } : src
        ),
      }));
      return { success: false, error: String(err) };
    }
  }

  return {
    state,
    deployedSkills,
    cachedSkills,
    pendingDeployments,
    fetchConfig,
    deploySkill,
    assignSkillToAgent,
    syncSource,
  };
}

export const configStore = createConfigStore();
```

**Option B: Svelte 5 Runes Class (for UI-only state like theme store)**

```typescript
class ConfigUIState {
  selectedSkill = $state<string | null>(null);
  selectedAgent = $state<string | null>(null);
  activePanel = $state<'skills' | 'agents' | 'sources'>('skills');
  searchQuery = $state('');
  showDeployedOnly = $state(false);

  selectSkill = (id: string) => { this.selectedSkill = id; };
  selectAgent = (id: string) => { this.selectedAgent = id; };
}

export const configUI = new ConfigUIState();
```

### 3.3 How to Add API Fetch Calls

**Pattern from existing code** (see `files.svelte.ts:33-52` and `socket.svelte.ts:156-167`):

```typescript
// 1. Simple GET request
async function fetchConfig(): Promise<ConfigData> {
  try {
    const response = await fetch('/api/config/skills');
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    const data = await response.json();
    if (data.error) {
      throw new Error(data.error);
    }
    return data;
  } catch (error) {
    console.error('[ConfigStore] Error fetching config:', error);
    throw error;
  }
}

// 2. POST request with body
async function deploySkill(skillId: string): Promise<{ success: boolean }> {
  const response = await fetch(`/api/config/skills/${skillId}/deploy`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ force: false }),
  });
  return response.json();
}
```

**In components**, call API with loading/error state:

```svelte
<script lang="ts">
  let loading = $state(false);
  let error = $state<string | null>(null);
  let data = $state<ConfigData | null>(null);

  async function loadConfig() {
    loading = true;
    error = null;
    try {
      const response = await fetch('/api/config/skills');
      const result = await response.json();
      if (result.success) {
        data = result;
      } else {
        error = result.error || 'Unknown error';
      }
    } catch (err) {
      error = err instanceof Error ? err.message : 'Network error';
    } finally {
      loading = false;
    }
  }

  // Load on mount
  import { onMount } from 'svelte';
  onMount(() => { loadConfig(); });
</script>

{#if loading}
  <div class="flex items-center justify-center h-full text-slate-500 dark:text-slate-400">
    <p>Loading configuration...</p>
  </div>
{:else if error}
  <div class="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded">
    <p class="text-red-700 dark:text-red-300">{error}</p>
    <button onclick={loadConfig} class="mt-2 text-sm text-red-600 dark:text-red-400 underline">
      Retry
    </button>
  </div>
{:else if data}
  <!-- Render config data -->
{/if}
```

### 3.4 How to Handle Forms and Validation

**No form patterns exist in the current codebase.** Here's the recommended pattern based on Svelte 5 runes and the existing styling:

```svelte
<script lang="ts">
  // Form state
  let formData = $state({
    url: '',
    branch: 'main',
    autoSync: true,
  });

  let errors = $state<Record<string, string>>({});
  let submitting = $state(false);

  // Validation
  function validate(): boolean {
    const newErrors: Record<string, string> = {};

    if (!formData.url.trim()) {
      newErrors.url = 'Repository URL is required';
    } else if (!formData.url.match(/^https?:\/\/.+\.git$/)) {
      newErrors.url = 'Must be a valid git URL ending in .git';
    }

    if (!formData.branch.trim()) {
      newErrors.branch = 'Branch name is required';
    }

    errors = newErrors;
    return Object.keys(newErrors).length === 0;
  }

  async function handleSubmit() {
    if (!validate()) return;

    submitting = true;
    try {
      const response = await fetch('/api/config/sources', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      const result = await response.json();
      if (result.success) {
        // Reset form
        formData = { url: '', branch: 'main', autoSync: true };
        errors = {};
        // Refresh parent data...
      } else {
        errors = { _form: result.error || 'Failed to add source' };
      }
    } catch (err) {
      errors = { _form: 'Network error' };
    } finally {
      submitting = false;
    }
  }
</script>

<form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }} class="space-y-4 p-4">
  <!-- Text Input -->
  <div>
    <label for="url" class="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-1">
      Repository URL
    </label>
    <input
      id="url"
      type="text"
      bind:value={formData.url}
      placeholder="https://github.com/user/repo.git"
      class="w-full px-3 py-2 text-sm rounded-lg border transition-colors
        {errors.url
          ? 'border-red-400 dark:border-red-500 focus:ring-red-500'
          : 'border-slate-300 dark:border-slate-600 focus:ring-cyan-500'}
        bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100
        placeholder-slate-400 dark:placeholder-slate-500
        focus:outline-none focus:ring-2 focus:border-transparent"
    />
    {#if errors.url}
      <p class="mt-1 text-xs text-red-600 dark:text-red-400">{errors.url}</p>
    {/if}
  </div>

  <!-- Select -->
  <div>
    <label for="branch" class="block text-sm font-semibold text-slate-700 dark:text-slate-300 mb-1">
      Branch
    </label>
    <select
      id="branch"
      bind:value={formData.branch}
      class="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-600
        bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100
        focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-colors"
    >
      <option value="main">main</option>
      <option value="master">master</option>
    </select>
  </div>

  <!-- Toggle/Checkbox -->
  <div class="flex items-center gap-3">
    <button
      type="button"
      onclick={() => formData.autoSync = !formData.autoSync}
      class="relative inline-flex h-6 w-11 items-center rounded-full transition-colors
        {formData.autoSync ? 'bg-cyan-600' : 'bg-slate-300 dark:bg-slate-600'}"
    >
      <span
        class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform
          {formData.autoSync ? 'translate-x-6' : 'translate-x-1'}"
      ></span>
    </button>
    <span class="text-sm text-slate-700 dark:text-slate-300">Auto-sync on startup</span>
  </div>

  <!-- Form-level error -->
  {#if errors._form}
    <div class="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded">
      <p class="text-sm text-red-700 dark:text-red-300">{errors._form}</p>
    </div>
  {/if}

  <!-- Submit Button -->
  <div class="flex justify-end gap-3">
    <button
      type="button"
      class="px-4 py-2 text-sm font-medium text-slate-700 dark:text-slate-300
        bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600
        rounded-lg transition-colors"
    >
      Cancel
    </button>
    <button
      type="submit"
      disabled={submitting}
      class="px-4 py-2 text-sm font-medium text-white
        bg-cyan-600 hover:bg-cyan-700 disabled:opacity-50 disabled:cursor-not-allowed
        rounded-lg transition-colors"
    >
      {submitting ? 'Adding...' : 'Add Source'}
    </button>
  </div>
</form>
```

### 3.5 How to Integrate Socket.IO for Real-Time Updates

**For configuration changes that need real-time updates** (e.g., sync progress):

**Step 1**: Add new event types to the backend Socket.IO emissions.

**Step 2**: Listen in the socket store (`socket.svelte.ts`):

```typescript
// Add to the eventTypes array in connect() (line 208)
const eventTypes = [
  'claude_event', 'hook_event', 'tool_event', 'cli_event',
  'system_event', 'agent_event', 'build_event', 'session_event',
  'response_event', 'file_event',
  'config_event'  // NEW
];
```

**Step 3**: Create a dedicated config event handler in the store or component:

```typescript
// Option A: In configStore - subscribe to socket events
import { socketStore } from './socket.svelte';

// In a component with onMount:
onMount(() => {
  const unsubscribe = socketStore.events.subscribe((events) => {
    // Filter for config_event types
    const configEvents = events.filter(e =>
      e.event === 'config_event' || e.type === 'config_event'
    );

    configEvents.forEach(event => {
      const data = event.data as Record<string, unknown>;
      if (data.subtype === 'sync_progress') {
        updateSyncProgress(data);
      } else if (data.subtype === 'skill_deployed') {
        handleSkillDeployed(data);
      }
    });
  });

  return unsubscribe;
});
```

**Option B**: Direct Socket.IO subscription (cleaner for dedicated use):

```typescript
// In component
import { socketStore } from '$lib/stores/socket.svelte';
import { get } from 'svelte/store';

onMount(() => {
  const socket = get(socketStore.socket);
  if (socket) {
    socket.on('config_event', (data: any) => {
      if (data.subtype === 'sync_progress') {
        syncProgress = data.progress;
        syncMessage = data.message;
      }
    });
  }
});
```

### 3.6 Modal/Overlay Pattern (New — needed for config UI)

Since no modal exists today, here's the pattern to establish:

Create `src/lib/components/Modal.svelte`:

```svelte
<script lang="ts">
  let {
    open = false,
    title = '',
    onClose,
    size = 'md',
    children,
  }: {
    open: boolean;
    title?: string;
    onClose: () => void;
    size?: 'sm' | 'md' | 'lg' | 'xl';
    children: any;
  } = $props();

  const sizeClasses = {
    sm: 'max-w-sm',
    md: 'max-w-lg',
    lg: 'max-w-2xl',
    xl: 'max-w-4xl',
  };

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') onClose();
  }
</script>

{#if open}
  <div
    class="fixed inset-0 z-50 flex items-center justify-center"
    onkeydown={handleKeydown}
    role="dialog"
    aria-modal="true"
    aria-label={title}
  >
    <!-- Backdrop -->
    <div
      class="absolute inset-0 bg-black/50 dark:bg-black/70"
      onclick={onClose}
    ></div>

    <!-- Modal content -->
    <div class="relative {sizeClasses[size]} w-full mx-4 bg-white dark:bg-slate-800
      rounded-xl shadow-2xl border border-slate-200 dark:border-slate-700 max-h-[85vh] flex flex-col">

      {#if title}
        <div class="px-6 py-4 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
          <h2 class="text-lg font-bold text-slate-900 dark:text-slate-100">{title}</h2>
          <button
            onclick={onClose}
            class="p-1 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 transition-colors"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      {/if}

      <div class="flex-1 overflow-y-auto p-6">
        {@render children()}
      </div>
    </div>
  </div>
{/if}
```

### 3.7 Toast/Notification Pattern (New — needed for config UI)

Create `src/lib/components/Toast.svelte`:

```svelte
<script lang="ts">
  let {
    message = '',
    type = 'info',
    show = false,
    duration = 5000,
    onDismiss,
  }: {
    message: string;
    type?: 'info' | 'success' | 'warning' | 'error';
    show: boolean;
    duration?: number;
    onDismiss?: () => void;
  } = $props();

  const typeStyles = {
    info: 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300',
    success: 'bg-green-50 dark:bg-green-900/30 border-green-200 dark:border-green-800 text-green-700 dark:text-green-300',
    warning: 'bg-yellow-50 dark:bg-yellow-900/30 border-yellow-200 dark:border-yellow-800 text-yellow-700 dark:text-yellow-300',
    error: 'bg-red-50 dark:bg-red-900/30 border-red-200 dark:border-red-800 text-red-700 dark:text-red-300',
  };

  $effect(() => {
    if (show && duration > 0) {
      const timer = setTimeout(() => { onDismiss?.(); }, duration);
      return () => clearTimeout(timer);
    }
  });
</script>

{#if show}
  <div class="fixed bottom-4 right-4 z-50 animate-slide-up">
    <div class="px-4 py-3 rounded-lg border shadow-lg {typeStyles[type]} flex items-center gap-3">
      <p class="text-sm font-medium">{message}</p>
      <button onclick={() => onDismiss?.()} class="text-current opacity-60 hover:opacity-100">
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  </div>
{/if}
```

---

## Part 4: Recommended Configuration View Component Structure

### Complete Component Map for Config UI

```
src/lib/
├── components/
│   ├── config/
│   │   ├── ConfigView.svelte            # Main config left panel (sub-tab navigation)
│   │   ├── ConfigDetail.svelte          # Main config right panel (detail/forms)
│   │   │
│   │   ├── SkillsList.svelte            # Skills listing with search/filter
│   │   ├── SkillDetail.svelte           # Skill detail + deployment pipeline
│   │   ├── SkillAssignments.svelte      # Skill-to-agent assignment chips
│   │   │
│   │   ├── AgentsList.svelte            # Agent configs listing
│   │   ├── AgentDetail.svelte           # Agent detail + assigned skills
│   │   │
│   │   ├── SourcesList.svelte           # Git source repos listing
│   │   ├── SourceForm.svelte            # Add/edit source form
│   │   ├── SyncProgress.svelte          # Real-time sync progress display
│   │   │
│   │   ├── ConflictResolver.svelte      # Conflict resolution cards
│   │   ├── DeploymentPipeline.svelte    # Cache → Deploy visualization
│   │   ├── ModeSwitch.svelte            # agent_referenced/user_defined toggle
│   │   └── WizardStepper.svelte         # Auto-configure wizard stepper
│   │
│   ├── shared/                          # NEW: shared UI primitives
│   │   ├── Modal.svelte                 # Modal overlay
│   │   ├── Toast.svelte                 # Toast notifications
│   │   ├── Toggle.svelte                # Toggle switch
│   │   ├── Badge.svelte                 # Status badge
│   │   ├── ProgressBar.svelte           # Progress indicator
│   │   └── SearchInput.svelte           # Search input with icon
│   │
│   └── [existing components...]
│
└── stores/
    ├── config.svelte.ts                 # Configuration data store
    └── [existing stores...]
```

### ConfigView Sub-Navigation Pattern

The config view should have its own sub-tabs within the left panel:

```svelte
<!-- ConfigView.svelte -->
<script lang="ts">
  type ConfigPanel = 'skills' | 'agents' | 'sources';
  let activePanel = $state<ConfigPanel>('skills');

  let selectedItem = $bindable<any>(null);
</script>

<div class="flex flex-col h-full bg-white dark:bg-slate-900">
  <!-- Sub-navigation -->
  <div class="flex items-center gap-0 px-4 py-2 bg-slate-100 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700">
    <button
      onclick={() => activePanel = 'skills'}
      class="px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors
        {activePanel === 'skills'
          ? 'bg-cyan-600 text-white'
          : 'text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'}"
    >
      Skills
    </button>
    <button
      onclick={() => activePanel = 'agents'}
      class="px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors
        {activePanel === 'agents'
          ? 'bg-cyan-600 text-white'
          : 'text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'}"
    >
      Agents
    </button>
    <button
      onclick={() => activePanel = 'sources'}
      class="px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors
        {activePanel === 'sources'
          ? 'bg-cyan-600 text-white'
          : 'text-slate-600 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700'}"
    >
      Sources
    </button>
  </div>

  <!-- Panel content -->
  <div class="flex-1 min-h-0 overflow-y-auto">
    {#if activePanel === 'skills'}
      <SkillsList bind:selectedItem />
    {:else if activePanel === 'agents'}
      <AgentsList bind:selectedItem />
    {:else if activePanel === 'sources'}
      <SourcesList bind:selectedItem />
    {/if}
  </div>
</div>
```

---

## Appendix: Key Patterns Reference

### A. Props Pattern (Svelte 5)

```typescript
// Bindable prop (two-way binding)
let { selectedItem = $bindable(null) }: { selectedItem: Item | null } = $props();

// Read-only props
let { items, title = 'Default' }: { items: Item[]; title?: string } = $props();

// Callback prop
let { onSelect }: { onSelect?: (item: Item) => void } = $props();
```

### B. Reactive Derivation Pattern

```typescript
// Simple derived
let filteredItems = $derived(items.filter(i => i.active));

// Complex derived (with function body)
let stats = $derived.by(() => {
  const total = items.length;
  const active = items.filter(i => i.active).length;
  return { total, active };
});
```

### C. Effect Pattern

```typescript
// Cleanup-returning effect
$effect(() => {
  const unsubscribe = store.subscribe(value => { localState = value; });
  return unsubscribe;
});

// Dependency-tracking effect
$effect(() => {
  // Runs when `viewMode` or `selectedStream` changes
  viewMode;  // Just reading triggers tracking
  selectedStream;
  // Reset selections...
});
```

### D. Styling Consistency Reference

| Element | Light | Dark |
|---------|-------|------|
| Page background | `bg-slate-50` | `dark:bg-slate-900` |
| Panel background | `bg-white` | `dark:bg-slate-900` |
| Header/toolbar | `bg-slate-100` | `dark:bg-slate-800` |
| Card/section | `bg-slate-50` | `dark:bg-slate-800/40` |
| Border | `border-slate-200` | `dark:border-slate-700` |
| Primary text | `text-slate-900` | `dark:text-slate-100` |
| Secondary text | `text-slate-700` | `dark:text-slate-300` |
| Tertiary text | `text-slate-500` | `dark:text-slate-500` |
| Primary accent | `bg-cyan-600` | `bg-cyan-600` (same) |
| Active/selected | `bg-cyan-50` / `border-l-cyan-500` | `dark:bg-cyan-500/20` / `dark:border-l-cyan-400` |
| Hover row | `hover:bg-slate-100` | `dark:hover:bg-slate-700/30` |
| Alternating rows | Even: `bg-slate-50` / Odd: `bg-white` | Even: `dark:bg-slate-800/40` / Odd: `dark:bg-slate-800/20` |
| Error | `text-red-600` | `dark:text-red-400` |
| Success | `text-green-600` | `dark:text-green-400` |
| Warning | `text-yellow-600` | `dark:text-yellow-400` |
| Info | `text-blue-600` | `dark:text-blue-400` |
| Badge | `bg-{color}-500/20 text-{color}-600 border border-{color}-500/30` | `dark:text-{color}-400` |
| Button primary | `bg-cyan-600 hover:bg-cyan-700 text-white` | same |
| Button secondary | `bg-slate-100 hover:bg-slate-200 text-slate-700` | `dark:bg-slate-700 dark:hover:bg-slate-600 dark:text-slate-300` |
| Input | `border-slate-300 bg-white text-slate-900` | `dark:border-slate-600 dark:bg-slate-700 dark:text-slate-100` |
| Input focus | `focus:ring-2 focus:ring-cyan-500` | same |

### E. Empty State Pattern

Every view follows this pattern for empty states:

```svelte
<div class="text-center py-12 text-slate-600 dark:text-slate-400">
  <svg class="w-16 h-16 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="..." />
  </svg>
  <p class="text-lg mb-2 font-medium">{title}</p>
  <p class="text-sm text-slate-500 dark:text-slate-500">{subtitle}</p>
</div>
```
