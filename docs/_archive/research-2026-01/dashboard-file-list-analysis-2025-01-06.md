# Dashboard File List Implementation Analysis

**Date:** 2025-01-06
**Purpose:** Understand current dashboard structure to plan D3.js radial tree integration

## Executive Summary

The Claude MPM dashboard is a **Svelte-based SPA** with Socket.IO for real-time event streaming. File operations are tracked through tool events and displayed in a tabular format. The architecture is well-suited for adding a D3.js radial tree visualization.

---

## 1. Dashboard Location & Architecture

### Primary Files
```
src/claude_mpm/dashboard-svelte/
├── src/
│   ├── lib/
│   │   ├── components/
│   │   │   ├── FilesView.svelte          # Main file list component
│   │   │   ├── FileViewer.svelte         # File content viewer
│   │   │   ├── Header.svelte
│   │   │   ├── EventStream.svelte
│   │   │   ├── ToolsView.svelte
│   │   │   └── AgentsView.svelte
│   │   ├── stores/
│   │   │   ├── files.svelte.ts           # File data store/utilities
│   │   │   ├── socket.svelte.ts          # Socket.IO connection
│   │   │   ├── tools.svelte.ts
│   │   │   └── agents.svelte.ts
│   │   └── types/
│   │       └── events.ts                 # Event type definitions
│   └── routes/
│       └── +page.svelte                  # Main dashboard page
└── static/
    └── svelte-build/
        └── index.html                     # Built dashboard (served)
```

### Served Dashboard
- **Location:** `src/claude_mpm/dashboard/static/svelte-build/index.html`
- **Server:** `src/claude_mpm/services/monitor/server.py`
- **Port:** `8765` (default)
- **Protocol:** HTTP (dashboard) + Socket.IO (events)

---

## 2. File List Component Analysis

### Component: `FilesView.svelte`

**Current Display Format:**
- **Table-based UI** with 4 columns:
  1. Icon (emoji based on file extension)
  2. Filename (truncated)
  3. Operation badge (read/write/edit)
  4. Timestamp

**Features:**
- Filename filtering (search box)
- Stream filtering (by session_id)
- File deduplication (shows latest per path)
- Click to view file content
- Operation color coding:
  - `read` → Blue
  - `write` → Green
  - `edit` → Amber

**Layout:**
```
┌─────────────────────────────────────────────────────┐
│ [Search filter]                      [N files]      │
├──────┬────────────────┬──────────┬──────────────────┤
│ Icon │ Filename       │ Operation│ Timestamp        │
├──────┼────────────────┼──────────┼──────────────────┤
│ 🐍   │ server.py      │ WRITE    │ 10:23:45 AM     │
│ 📜   │ app.js         │ READ     │ 10:23:44 AM     │
│ 🎨   │ styles.css     │ EDIT     │ 10:23:42 AM     │
└──────┴────────────────┴──────────┴──────────────────┘
```

---

## 3. Data Structure

### TouchedFile Interface
```typescript
interface TouchedFile {
  path: string;              // Full file path
  name: string;              // Filename only
  operation: 'read' | 'write' | 'edit';
  timestamp: string | number;
  toolName: string;          // e.g., "Read", "Write", "Edit"
  eventId: string;           // Unique event ID
  sessionId?: string;        // Stream/session for filtering
  oldContent?: string;       // Content before edit/write
  newContent?: string;       // Content after edit/write
}
```

### Storage
- **State:** Svelte runes (`$state`)
- **Processing:** Derived stores (`$derived.by`)
- **Persistence:** LocalStorage cache (last 50 events per stream)

---

## 4. Event Flow

### WebSocket Event Pipeline

```
┌────────────────────────────────────────────────────────────┐
│ 1. Backend: Claude tool execution                         │
│    - Read/Write/Edit file operations                      │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│ 2. Hook System: Pre-tool event                           │
│    - Captures tool_name, tool_parameters                  │
│    - Extracts file_path, content, old_string, new_string │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│ 3. Socket.IO: Event emission                             │
│    Event type: 'hook_event'                               │
│    Subtype: 'pre_tool'                                    │
│    Data: { tool_name, tool_parameters, session_id, ... } │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│ 4. Frontend: socket.svelte.ts                            │
│    - Receives event via Socket.IO client                  │
│    - Normalizes event structure                           │
│    - Stores in events array                               │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│ 5. FilesView.svelte: processToolEvent()                  │
│    - Filters for 'pre_tool' events                        │
│    - Extracts file path from tool_parameters              │
│    - Determines operation type (read/write/edit)          │
│    - Creates TouchedFile object                           │
│    - Adds to touchedFiles array                           │
└────────────────────────┬───────────────────────────────────┘
                         │
                         ▼
┌────────────────────────────────────────────────────────────┐
│ 6. Reactive UI Update                                     │
│    - Svelte reactivity triggers re-render                 │
│    - File appears in table instantly                      │
└────────────────────────────────────────────────────────────┘
```

### Key Event Fields
```javascript
{
  id: "evt_1234567890_123",
  type: "hook",
  event: "hook_event",
  subtype: "pre_tool",
  timestamp: "2025-01-06T15:23:45.123Z",
  session_id: "claude-abc123",
  data: {
    tool_name: "Write",
    tool_parameters: {
      file_path: "/path/to/file.py",
      content: "print('hello')",
      // OR for Edit:
      old_string: "old code",
      new_string: "new code"
    }
  }
}
```

---

## 5. Tech Stack

### Frontend
- **Framework:** Svelte 5 (with runes/signals)
- **Build Tool:** Vite + SvelteKit
- **Styling:** Tailwind CSS
- **WebSocket:** Socket.IO client (`socket.io-client`)
- **State Management:** Svelte stores + runes
- **Icons:** Emoji (no icon library)

### Backend
- **Server:** aiohttp + Socket.IO Python (`python-socketio`)
- **Event System:** EventBus + Hook interceptors
- **File Watching:** watchdog (for hot reload)
- **Build Output:** Static files served from `/dashboard/static/svelte-build/`

### Existing Visualization Libraries
**None detected in FilesView.** However, other parts use:
- `cytoscape` + `cytoscape-fcose` (graph layouts - for agents view)
- `katex` (math rendering - unused in files tab)

---

## 6. Integration Points for D3.js Radial Tree

### Recommended Approach

#### Option A: Side-by-side view (RECOMMENDED)
Add a toggle to switch between table and radial tree:

```
┌─────────────────────────────────────────────────────────┐
│ [Search]  [Stream]  [View: Table | Tree]   [50 files]  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│              [Radial Tree Visualization]                │
│                                                         │
│          ┌───────┐                                      │
│       ┌──┤ src/ ─┼──┐                                   │
│       │  └───────┘  │                                   │
│   ┌───┴───┐    ┌───┴────┐                               │
│   │ lib/  │    │ utils/ │                               │
│   └───────┘    └────────┘                               │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**Implementation:**
1. Add D3.js v7 to package.json
2. Create `FileTreeView.svelte` component
3. Update `FilesView.svelte` to toggle between table and tree
4. Transform flat file list into hierarchical structure
5. Use D3 radial tree layout with zoom/pan

#### Option B: Mini tree in right panel
Show tree when no file selected:

```
┌─────────────────┬───────────────────────────────────────┐
│ File List       │ [File Content or Tree Preview]        │
│ (table)         │                                       │
│                 │         ┌─────┐                       │
│ server.py  WRITE│      ┌──┤ src ├──┐                    │
│ app.js     READ │      │  └─────┘  │                    │
│ styles.css EDIT │  ┌───┴──┐    ┌───┴───┐                │
│                 │  │ lib  │    │ utils │                │
└─────────────────┴───────────────────────────────────────┘
```

#### Option C: Overlay/modal
Button to open full-screen radial tree visualization.

---

## 7. Data Transformation for D3

### Current: Flat array
```javascript
[
  { path: "/proj/src/lib/utils.py", operation: "write", ... },
  { path: "/proj/src/app.py", operation: "read", ... },
  { path: "/proj/tests/test_app.py", operation: "edit", ... }
]
```

### Required: Hierarchical tree
```javascript
{
  name: "proj",
  path: "/proj",
  children: [
    {
      name: "src",
      path: "/proj/src",
      children: [
        { name: "app.py", path: "/proj/src/app.py", operation: "read", isFile: true },
        {
          name: "lib",
          path: "/proj/src/lib",
          children: [
            { name: "utils.py", path: "/proj/src/lib/utils.py", operation: "write", isFile: true }
          ]
        }
      ]
    },
    {
      name: "tests",
      path: "/proj/tests",
      children: [
        { name: "test_app.py", path: "/proj/tests/test_app.py", operation: "edit", isFile: true }
      ]
    }
  ]
}
```

### Transformation Function Needed
```typescript
function buildFileTree(files: TouchedFile[], projectRoot: string): TreeNode {
  // Group files by directory structure
  // Build nested tree with operation metadata
  // Root node = project root
  // Leaf nodes = files with operation info
}
```

---

## 8. Implementation Plan

### Phase 1: Add D3.js dependency
```bash
cd src/claude_mpm/dashboard-svelte
npm install d3@7
npm install @types/d3 --save-dev
```

### Phase 2: Create tree transformation utility
**File:** `src/lib/utils/file-tree-builder.ts`
```typescript
import type { TouchedFile } from '$lib/stores/files.svelte';

export interface TreeNode {
  name: string;
  path: string;
  operation?: 'read' | 'write' | 'edit';
  isFile: boolean;
  children?: TreeNode[];
  metadata?: {
    timestamp: string | number;
    toolName: string;
  };
}

export function buildFileTree(
  files: TouchedFile[],
  projectRoot: string
): TreeNode {
  // Implementation
}
```

### Phase 3: Create radial tree component
**File:** `src/lib/components/FileTreeVisualization.svelte`
```svelte
<script lang="ts">
  import * as d3 from 'd3';
  import { onMount } from 'svelte';
  import type { TreeNode } from '$lib/utils/file-tree-builder';

  interface Props {
    treeData: TreeNode;
    onFileSelect?: (path: string) => void;
  }

  let { treeData, onFileSelect }: Props = $props();
  let svgContainer: HTMLDivElement;

  onMount(() => {
    renderTree();
  });

  function renderTree() {
    // D3 radial tree implementation
    // - Use d3.tree() with radial projection
    // - Color nodes by operation type
    // - Add zoom/pan behavior
    // - Click handler to select file
  }
</script>

<div bind:this={svgContainer} class="tree-container"></div>
```

### Phase 4: Update FilesView with toggle
Add view mode selector and conditional rendering:
```svelte
<script lang="ts">
  let viewMode = $state<'table' | 'tree'>('table');
</script>

<!-- View toggle buttons -->
<div class="view-selector">
  <button on:click={() => viewMode = 'table'}>Table</button>
  <button on:click={() => viewMode = 'tree'}>Tree</button>
</div>

{#if viewMode === 'table'}
  <!-- Existing table code -->
{:else}
  <FileTreeVisualization
    treeData={buildFileTree(filteredFiles, projectRoot)}
    onFileSelect={selectFile}
  />
{/if}
```

### Phase 5: Styling and UX polish
- Match dark mode colors
- Add operation color legend
- Implement smooth transitions
- Add tooltips with file metadata

---

## 9. Key Considerations

### Performance
- **File count:** Dashboard filters to 50 most recent events by default
- **Tree complexity:** With 50 files, tree depth typically 3-5 levels
- **D3 rendering:** Should handle 50 nodes easily (can scale to 1000+)

### Interactivity
- **Click node:** Select file (same as table click)
- **Hover node:** Show tooltip with full path + metadata
- **Zoom/pan:** Essential for large projects
- **Search integration:** Highlight matching nodes in tree

### State Management
- **Shared selection:** `selectedFile` is already bindable
- **Filtering:** Both views should respect same filters
- **Reactivity:** Tree must rebuild when `filteredFiles` changes

### Accessibility
- Add keyboard navigation for tree
- Ensure color contrast for operation badges
- Provide ARIA labels for tree nodes

---

## 10. Questions & Next Steps

### Questions for Implementation
1. **View preference:** Should tree/table selection persist in localStorage?
2. **Default view:** Start with table (current) or tree (new)?
3. **Animation:** Animate tree layout on data changes?
4. **Collapsing:** Allow collapsing directory nodes?
5. **Layout:** Radial vs. hierarchical vs. force-directed?

### Next Steps
1. ✅ Analyze current dashboard structure (DONE)
2. ⬜ Create file tree transformation utility
3. ⬜ Prototype D3 radial tree in isolated component
4. ⬜ Integrate tree view with FilesView toggle
5. ⬜ Add interactive features (zoom, filter, select)
6. ⬜ Polish styling to match dashboard theme
7. ⬜ Test with real Claude sessions (50+ file operations)
8. ⬜ Document usage and configuration options

---

## Appendix: Code Snippets

### Current File Processing Logic
```typescript
// From FilesView.svelte, line 110-225
async function processToolEvent(event: ClaudeEvent) {
  // Only process pre_tool events
  if (event.subtype !== 'pre_tool') return;

  const toolName = dataRecord?.tool_name;
  const operation = getOperationType(toolName); // 'read' | 'write' | 'edit'
  const filePath = extractFilePath(data);

  // Create TouchedFile
  const touchedFile: TouchedFile = {
    path: filePath,
    name: getFileName(filePath),
    operation,
    timestamp: event.timestamp,
    toolName,
    eventId: event.id,
    sessionId,
    oldContent,
    newContent
  };

  touchedFiles = [...touchedFiles, touchedFile];
}
```

### Socket Event Registration
```typescript
// From socket.svelte.ts, line 206-216
const eventTypes = [
  'claude_event',
  'hook_event',    // File operations arrive as hook_event
  'cli_event',
  'system_event',
  'agent_event',
  'build_event'
];

eventTypes.forEach(eventType => {
  newSocket.on(eventType, (data: ClaudeEvent) => {
    handleEvent({ ...data, event: eventType });
  });
});
```

---

## Summary for D3.js Integration

**DASHBOARD_LOCATION:** `src/claude_mpm/dashboard-svelte/src/lib/components/FilesView.svelte`

**FILE_LIST_COMPONENT:**
- Component: `FilesView.svelte` (lines 309-383)
- Data store: `files.svelte.ts`
- Processing: `processToolEvent()` function

**TECH_STACK:**
- Svelte 5 + SvelteKit (static adapter)
- Tailwind CSS for styling
- Socket.IO for real-time events
- No existing D3.js (needs to be added)
- Cytoscape available (used in agents view)

**EVENT_FLOW:**
1. Backend tool execution (Read/Write/Edit)
2. Hook system captures pre_tool event
3. Socket.IO emits `hook_event` with `subtype: 'pre_tool'`
4. Frontend `socket.svelte.ts` receives and stores event
5. `FilesView.svelte` subscribes to events store
6. `processToolEvent()` filters and transforms to `TouchedFile`
7. Svelte reactivity updates UI

**DATA_STRUCTURE:**
```typescript
TouchedFile {
  path: string             // "/full/path/to/file.py"
  name: string             // "file.py"
  operation: 'read'|'write'|'edit'
  timestamp: string|number
  sessionId?: string       // For stream filtering
}
```

**INTEGRATION_APPROACH:**
1. Install D3.js v7
2. Create `file-tree-builder.ts` utility (flat → hierarchical)
3. Create `FileTreeVisualization.svelte` component (D3 radial tree)
4. Add table/tree toggle to `FilesView.svelte`
5. Share `selectedFile` state between views
6. Maintain consistent filtering and styling

**Recommended Layout:** Side-by-side toggle (Option A) for best UX
