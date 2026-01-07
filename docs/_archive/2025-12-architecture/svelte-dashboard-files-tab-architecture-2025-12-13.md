# Svelte Dashboard Architecture Research - Files Tab Implementation

**Research Date:** 2025-12-13
**Purpose:** Understand current dashboard structure to implement Files tab with syntax highlighting and diff viewing
**Status:** Complete

---

## Executive Summary

The Svelte dashboard uses a **derived store pattern** with **pre/post tool event correlation** to display tool executions. The architecture is highly modular and can be extended to create a Files tab by:

1. Creating a new **files.svelte.ts** store that derives file operations from events
2. Building a **FilesView.svelte** component (similar to ToolsView pattern)
3. Extending **JSONExplorer.svelte** or creating **FileViewer.svelte** for syntax highlighting
4. Adding a "Files" tab to **+page.svelte** using existing tab mechanism

**Key Finding:** File operation events (Read, Write, Edit, Grep, Glob) are already captured in `pre_tool` and `post_tool` events with full file path and content data.

---

## 1. Tools Store Architecture (`tools.svelte.ts`)

### Store Pattern: Derived Store with Event Correlation

```typescript
// Pattern: Derived store that transforms events array into tools array
const tools = derived(eventsStore, ($events) => {
    const toolMap = new Map<string, Tool>();

    // Process events and correlate pre_tool + post_tool by correlation_id
    $events.forEach(event => {
        if (event.subtype === 'pre_tool') {
            // Create tool entry with pre_tool data
        } else if (event.subtype === 'post_tool') {
            // Update existing tool with post_tool data
        }
    });

    return Array.from(toolMap.values()).sort(/* by timestamp */);
});
```

### Event Extraction Logic

**Subtype Detection** (lines 31-39):
```typescript
const data = event.data as Record<string, unknown> | null;
const eventSubtype = event.subtype || (data?.subtype as string);

// Only process pre_tool and post_tool events
if (eventSubtype !== 'pre_tool' && eventSubtype !== 'post_tool') {
    return;
}
```

**Correlation ID Matching** (lines 49-60):
```typescript
const correlationId =
    event.correlation_id ||
    (data?.correlation_id as string) ||
    (data?.tool_call_id as string);

// Fallback: Generate ID from session + tool + timestamp
const id = correlationId || `${sessionId}_${toolName}_${timestamp}`;
```

**Pre/Post Event Correlation** (lines 72-155):
- `pre_tool`: Creates new Tool entry with pending status
- `post_tool`: Updates existing Tool entry with results and duration
- Fallback matching: If no correlation_id, matches by session + tool + time window (30 seconds)

### Tool Operation Extraction

**File Operation Detection** (lines 179-223):
```typescript
function extractOperation(toolName: string, data: Record<string, unknown> | null): string {
    switch (toolName) {
        case 'Read':
            return `Read ${truncate(data.file_path, 35)}`;
        case 'Edit':
            return `Edit ${truncate(data.file_path, 35)}`;
        case 'Write':
            return `Write ${truncate(data.file_path, 35)}`;
        case 'Grep':
            return `Search: ${truncate(data.pattern, 30)}`;
        case 'Glob':
            return `Find: ${truncate(data.pattern, 30)}`;
        // ... other tools
    }
}
```

**Key Insight:** File paths are already extracted from `pre_tool` event data and available in the Tool interface.

---

## 2. ToolsView Component (`ToolsView.svelte`)

### Component Structure

**Props Pattern** (lines 4-12):
```typescript
let {
    tools,
    selectedTool = $bindable(null),
    selectedStream = 'all'
}: {
    tools: Tool[];
    selectedTool: Tool | null;
    selectedStream: string;
} = $props();
```

**Key Features:**
- **Stream Filtering:** Filter tools by session_id/source (lines 24-43)
- **Auto-scroll:** Scroll to bottom on new items if user is near bottom (lines 45-75)
- **Keyboard Navigation:** Arrow keys for tool selection (lines 122-151)
- **Two-column Layout:** Tool list + detail view

### Tool List Rendering

**Table-like Grid Layout** (lines 175-227):
```typescript
<!-- Header -->
<div class="grid grid-cols-[140px_1fr_80px_100px] gap-3 ...">
    <div>Tool Name</div>
    <div>Operation</div>
    <div>Status</div>
    <div>Duration</div>
</div>

<!-- Rows -->
{#each filteredTools as tool}
    <button class="grid grid-cols-[140px_1fr_80px_100px] gap-3 ...">
        <div>{tool.toolName}</div>
        <div>{tool.operation}</div>
        <div>{getStatusIcon(tool.status)}</div>
        <div>{formatDuration(tool.duration)}</div>
    </button>
{/each}
```

**Selection Pattern:**
- Click handler: `onclick={() => selectTool(tool)}`
- Bindable selection: `selectedTool = $bindable(null)`
- Visual feedback: Conditional CSS classes based on `selectedTool?.id === tool.id`

---

## 3. Event Stream Structure (Backend)

### Event Types and Payloads

**Pre-Tool Event** (`event_handlers.py` lines 118-185):
```python
pre_tool_data = {
    "tool_name": tool_name,              # "Read", "Write", "Edit", "Grep", "Glob"
    "operation_type": operation_type,     # Classified operation
    "tool_parameters": tool_params,       # Extracted params
    "session_id": event.get("session_id"),
    "working_directory": working_dir,
    "git_branch": git_branch,
    "timestamp": timestamp,
    "correlation_id": tool_call_id,      # UUID for correlation
    "is_file_operation": tool_name in ["Write", "Edit", "Read", "Glob"],
    "security_risk": assess_security_risk(...)
}
```

**Post-Tool Event** (`event_handlers.py` line 386):
```python
post_tool_data = {
    "tool_name": tool_name,
    "output": tool_output,               # File content, search results, etc.
    "error": error_message,
    "success": success_boolean,
    "exit_code": exit_code,
    "correlation_id": retrieved_tool_call_id,
    "duration_ms": duration_ms
}
```

### File-Related Tool Parameters

**Read Tool:**
```typescript
{
    file_path: string,
    limit?: number,
    offset?: number
}
```

**Write Tool:**
```typescript
{
    file_path: string,
    content: string
}
```

**Edit Tool:**
```typescript
{
    file_path: string,
    old_string: string,
    new_string: string,
    replace_all?: boolean
}
```

**Grep Tool:**
```typescript
{
    pattern: string,
    path?: string,
    glob?: string,
    output_mode?: "content" | "files_with_matches" | "count"
}
```

**Glob Tool:**
```typescript
{
    pattern: string,
    path?: string
}
```

---

## 4. JSONExplorer Component (`JSONExplorer.svelte`)

### Current Implementation

**Two View Modes:**
1. **Event View:** Recursive JSON explorer for raw events (lines 370-378)
2. **Tool View:** Table-based display for pre/post tool data (lines 217-369)

**Tool View Pattern** (lines 217-298):
- Pre-tool section: Table of invocation details
- Tool parameters: Nested table for parameters
- Post-tool section: Table of results
- Output display: `<pre>` blocks for output/error

### Extensibility for File Viewing

**Current Limitations:**
- No syntax highlighting (uses plain `<pre>` tags)
- No diff viewing for Edit operations
- No file tree navigation

**Extension Points:**
1. Add conditional rendering for file operations
2. Integrate syntax highlighter for `output` field
3. Add diff viewer for Edit tool comparison
4. Create file-specific detail view

---

## 5. Page Integration (`+page.svelte`)

### Tab Switching Mechanism

**View Mode State** (line 13):
```typescript
let viewMode = $state<ViewMode>('events');  // 'events' | 'tools'
```

**Tab Rendering** (lines 93-109):
```svelte
<div class="flex gap-0 px-2 pt-2">
    <button
        onclick={() => viewMode = 'events'}
        class:active={viewMode === 'events'}
    >
        Events
    </button>
    <button
        onclick={() => viewMode = 'tools'}
        class:active={viewMode === 'tools'}
    >
        Tools
    </button>
</div>

<!-- Conditional rendering -->
{#if viewMode === 'events'}
    <EventStream bind:selectedEvent selectedStream={$selectedStream} />
{:else}
    <ToolsView {tools} bind:selectedTool selectedStream={$selectedStream} />
{/if}
```

**Selection Management** (lines 46-52):
```typescript
// Clear selections when switching views
$effect(() => {
    if (viewMode === 'events') {
        selectedTool = null;
    } else {
        selectedEvent = null;
    }
});
```

### Layout Structure

**Three-panel Layout:**
1. **Left Panel:** View tabs + EventStream/ToolsView (resizable)
2. **Divider:** Draggable divider for panel resizing
3. **Right Panel:** JSONExplorer for details (resizable)

**Adding Files Tab:**
```svelte
// Add to ViewMode type
export type ViewMode = 'events' | 'tools' | 'files';

// Add tab button
<button
    onclick={() => viewMode = 'files'}
    class:active={viewMode === 'files'}
>
    Files
</button>

// Add conditional rendering
{:else if viewMode === 'files'}
    <FilesView {files} bind:selectedFile selectedStream={$selectedStream} />
```

---

## 6. File Operations Event Examples

### Read Event Flow

**Pre-tool (sent before file read):**
```json
{
    "event": "claude_event",
    "subtype": "pre_tool",
    "correlation_id": "abc123...",
    "data": {
        "tool_name": "Read",
        "tool_parameters": {
            "file_path": "/path/to/file.py",
            "limit": 2000,
            "offset": 0
        },
        "working_directory": "/Users/masa/Projects/...",
        "git_branch": "main",
        "timestamp": "2025-12-13T10:30:00Z"
    }
}
```

**Post-tool (sent after file read):**
```json
{
    "event": "claude_event",
    "subtype": "post_tool",
    "correlation_id": "abc123...",
    "data": {
        "tool_name": "Read",
        "output": "     1→import os\n     2→import sys\n...",
        "success": true,
        "exit_code": 0,
        "duration_ms": 45
    }
}
```

### Edit Event Flow

**Pre-tool:**
```json
{
    "tool_name": "Edit",
    "tool_parameters": {
        "file_path": "/path/to/file.py",
        "old_string": "def old_function():\n    pass",
        "new_string": "def new_function():\n    return True"
    }
}
```

**Post-tool:**
```json
{
    "tool_name": "Edit",
    "output": "Successfully edited file",
    "success": true
}
```

### Grep Event Flow

**Pre-tool:**
```json
{
    "tool_name": "Grep",
    "tool_parameters": {
        "pattern": "TODO",
        "path": "/Users/masa/Projects/claude-mpm/src",
        "output_mode": "content"
    }
}
```

**Post-tool:**
```json
{
    "tool_name": "Grep",
    "output": "/path/file.py:42:    # TODO: implement this\n...",
    "success": true
}
```

---

## 7. Recommended Implementation Plan

### Phase 1: Create Files Store

**File:** `src/lib/stores/files.svelte.ts`

```typescript
import { derived } from 'svelte/store';
import type { ClaudeEvent, FileOperation } from '$lib/types/events';

interface FileOperation {
    id: string;
    filePath: string;
    operation: 'read' | 'write' | 'edit' | 'search';
    timestamp: string | number;
    status: 'pending' | 'success' | 'error';
    preToolEvent: ClaudeEvent;
    postToolEvent: ClaudeEvent | null;
    content?: string;  // For read/write
    oldContent?: string;  // For edit (diff view)
    newContent?: string;  // For edit (diff view)
    searchResults?: string;  // For grep
}

function createFilesStore(eventsStore) {
    return derived(eventsStore, ($events) => {
        const fileMap = new Map<string, FileOperation>();

        $events.forEach(event => {
            const data = event.data as Record<string, unknown> | null;
            const subtype = event.subtype || data?.subtype;
            const toolName = data?.tool_name as string;

            // Filter file operations only
            if (!['Read', 'Write', 'Edit', 'Grep', 'Glob'].includes(toolName)) {
                return;
            }

            // Correlate pre/post events (similar to tools.svelte.ts)
            // Extract file path, content, etc.
        });

        return Array.from(fileMap.values()).sort(/* by timestamp */);
    });
}
```

### Phase 2: Create FilesView Component

**File:** `src/lib/components/FilesView.svelte`

**Structure:**
- File list with path, operation, status, timestamp
- Grid layout: `[Operation] [Path] [Status] [Time]`
- Selection handling with bindable `selectedFile`
- Stream filtering support

### Phase 3: Extend Detail View

**Option A:** Extend JSONExplorer with file-specific view
**Option B:** Create dedicated FileViewer.svelte component

**Required Features:**
1. Syntax highlighting for Read/Write operations
2. Diff view for Edit operations
3. Search results highlighting for Grep
4. File tree for Glob results

### Phase 4: Add Files Tab to Page

**File:** `src/routes/+page.svelte`

```typescript
// Add to type definition
export type ViewMode = 'events' | 'tools' | 'files';

// Create files store
const filesStore = createFilesStore(eventsStore);
let files = $state<FileOperation[]>([]);

$effect(() => {
    const unsubscribe = filesStore.subscribe(value => {
        files = value;
    });
    return unsubscribe;
});

// Add tab and conditional rendering
```

---

## 8. Dependencies for Syntax Highlighting and Diff Viewing

### Recommended Libraries

#### 1. **Shiki** - Modern Syntax Highlighter
```bash
npm install shiki
```

**Advantages:**
- Uses VS Code's TextMate grammars
- Supports 100+ languages
- Works in SSR (Svelte/SvelteKit compatible)
- Small bundle size (~50KB gzipped)
- No runtime dependencies

**Usage Pattern:**
```typescript
import { getHighlighter } from 'shiki';

const highlighter = await getHighlighter({
    themes: ['github-dark', 'github-light'],
    langs: ['python', 'javascript', 'typescript', 'markdown']
});

const html = highlighter.codeToHtml(code, {
    lang: 'python',
    theme: 'github-dark'
});
```

#### 2. **diff** - JavaScript Text Differencing
```bash
npm install diff
```

**Advantages:**
- Industry standard (used by GitHub, GitLab)
- Supports line, word, and character diffs
- Generates unified, context, and JSON diffs
- ~15KB minified

**Usage Pattern:**
```typescript
import * as Diff from 'diff';

const diff = Diff.createPatch('filename', oldContent, newContent);
// Or structured diff
const changes = Diff.diffLines(oldContent, newContent);
```

#### 3. **diff2html** - Pretty Diff Viewer
```bash
npm install diff2html
```

**Advantages:**
- Beautiful GitHub-style diff UI
- Line-by-line and side-by-side views
- Syntax highlighting integration
- ~80KB minified

**Usage Pattern:**
```typescript
import { Diff2Html } from 'diff2html';
import 'diff2html/bundles/css/diff2html.min.css';

const diffHtml = Diff2Html.html(unifiedDiff, {
    drawFileList: true,
    matching: 'lines',
    outputFormat: 'side-by-side'
});
```

### Alternative: Monaco Editor (Heavy but Feature-Rich)

```bash
npm install monaco-editor
```

**Advantages:**
- Full VS Code editor experience
- Built-in diff viewer
- IntelliSense, search, folding

**Disadvantages:**
- Large bundle size (~3MB)
- Complex setup with SvelteKit
- Overkill for view-only use case

**Recommendation:** Use **Shiki + diff2html** for optimal bundle size and features.

---

## 9. Key Patterns to Reuse

### Pattern 1: Derived Store for Data Transformation
```typescript
// Extract specific event types into domain objects
const domainStore = derived(eventsStore, ($events) => {
    return $events
        .filter(/* criteria */)
        .map(/* transform */)
        .sort(/* order */);
});
```

### Pattern 2: Pre/Post Event Correlation
```typescript
// Use correlation_id or fallback to session+tool+time matching
const correlationId = event.correlation_id || generateFallbackId();
const existing = map.get(correlationId);

if (subtype === 'pre') {
    map.set(correlationId, { ...data, status: 'pending' });
} else if (subtype === 'post') {
    existing.status = data.success ? 'success' : 'error';
    existing.duration = calculateDuration();
}
```

### Pattern 3: Bindable Selection with Effect
```typescript
let selectedItem = $bindable(null);

// Clear selection when view changes
$effect(() => {
    if (viewModeChanged) {
        selectedItem = null;
    }
});
```

### Pattern 4: Stream Filtering
```typescript
let filteredItems = $derived.by(() => {
    return selectedStream === 'all'
        ? items
        : items.filter(item => item.session_id === selectedStream);
});
```

### Pattern 5: Keyboard Navigation
```typescript
function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'ArrowDown') {
        selectNext();
    } else if (e.key === 'ArrowUp') {
        selectPrevious();
    }
}
```

---

## 10. Modular Refactoring Recommendations

### Current Architecture Strengths
1. **Separation of Concerns:** Store logic separate from view components
2. **Reusable Patterns:** Consistent pre/post correlation across stores
3. **Type Safety:** Strong TypeScript types for events and domain objects

### Areas for Improvement

#### A. Extract Correlation Logic
**Current:** Duplicated in tools.svelte.ts
**Recommendation:** Create shared correlation utility

```typescript
// src/lib/utils/event-correlation.ts
export function correlateEvents<T>(
    events: ClaudeEvent[],
    filter: (event: ClaudeEvent) => boolean,
    extract: (event: ClaudeEvent) => Partial<T>,
    merge: (pre: T, post: ClaudeEvent) => T
): T[] {
    // Reusable correlation logic
}
```

#### B. Extract Operation Extractors
**Current:** Tool-specific logic in tools.svelte.ts
**Recommendation:** Create operation registry

```typescript
// src/lib/utils/operation-extractors.ts
export const operationExtractors = {
    Read: (data) => `Read ${truncate(data.file_path, 35)}`,
    Edit: (data) => `Edit ${truncate(data.file_path, 35)}`,
    // ... extensible registry
};
```

#### C. Shared Detail View Components
**Current:** JSONExplorer handles all detail views
**Recommendation:** Component composition

```typescript
// src/lib/components/details/ToolDetail.svelte
// src/lib/components/details/FileDetail.svelte
// src/lib/components/details/EventDetail.svelte

// JSONExplorer becomes a router
{#if tool}
    <ToolDetail {tool} />
{:else if file}
    <FileDetail {file} />
{:else if event}
    <EventDetail {event} />
{/if}
```

#### D. Shared List Component
**Pattern:** Both ToolsView and FilesView will have similar structure
**Recommendation:** Generic list component

```typescript
// src/lib/components/ItemList.svelte
<script lang="ts" generics="T">
    let {
        items,
        selectedItem = $bindable(null),
        columns,
        renderCell
    }: {
        items: T[];
        selectedItem: T | null;
        columns: Column[];
        renderCell: (item: T, column: string) => string;
    } = $props();
</script>
```

---

## 11. File Tree Navigation (Future Enhancement)

### Data Structure for Glob Results

When Glob returns file paths, group them into tree structure:

```typescript
interface FileTreeNode {
    name: string;
    path: string;
    type: 'file' | 'directory';
    children?: FileTreeNode[];
    operation?: FileOperation;  // Link to operation
}

function buildFileTree(filePaths: string[]): FileTreeNode {
    // Group by directory structure
    // Create hierarchical tree
}
```

### Component Structure

```svelte
<!-- FileTree.svelte -->
<script lang="ts">
    let { tree, onSelect } = $props();
</script>

<ul>
    {#each tree.children as node}
        {#if node.type === 'directory'}
            <li>
                <FolderIcon /> {node.name}
                <FileTree tree={node} {onSelect} />
            </li>
        {:else}
            <li onclick={() => onSelect(node)}>
                <FileIcon /> {node.name}
            </li>
        {/if}
    {/each}
</ul>
```

---

## 12. Summary: Quick Reference

### What You Need to Know

1. **Events Flow:** Backend emits `pre_tool` and `post_tool` events with full file operation data
2. **Store Pattern:** Use `derived()` to transform events array into file operations array
3. **Component Pattern:** Build FilesView similar to ToolsView (grid layout, selection, filtering)
4. **Detail View:** Extend JSONExplorer or create FileViewer with syntax highlighting
5. **Tab Integration:** Add 'files' to ViewMode type and conditional rendering in +page.svelte

### Event Data You Can Use

- `tool_name`: "Read", "Write", "Edit", "Grep", "Glob"
- `tool_parameters.file_path`: Full path to file
- `tool_parameters.content`: File content (Write)
- `tool_parameters.old_string` / `new_string`: Edit diff data
- `tool_parameters.pattern`: Search pattern (Grep)
- `output`: File content (Read) or search results (Grep)
- `correlation_id`: Match pre/post events
- `timestamp`: Sort operations chronologically
- `success` / `error`: Operation status

### Dependencies to Install

```bash
npm install shiki          # Syntax highlighting
npm install diff           # Diff generation
npm install diff2html      # Diff UI
```

### Files to Create

1. `src/lib/stores/files.svelte.ts` - Files store
2. `src/lib/components/FilesView.svelte` - File list view
3. `src/lib/components/FileViewer.svelte` - File detail view with syntax highlighting
4. `src/lib/types/events.ts` - Add FileOperation interface

### Files to Modify

1. `src/routes/+page.svelte` - Add Files tab
2. `src/lib/components/JSONExplorer.svelte` - Add file-specific detail view (or route to FileViewer)

---

## Appendix: Type Definitions

### Existing Types (`src/lib/types/events.ts`)

```typescript
export interface ClaudeEvent {
    id: string;
    event?: string;
    type: string;
    timestamp: string | number;
    data: unknown;
    sessionId?: string;
    session_id?: string;
    subtype?: string;
    source?: string;
    correlation_id?: string;
}

export interface Tool {
    id: string;
    toolName: string;
    operation: string;
    status: 'pending' | 'success' | 'error';
    duration: number | null;
    preToolEvent: ClaudeEvent;
    postToolEvent: ClaudeEvent | null;
    timestamp: string | number;
}

export type ViewMode = 'events' | 'tools';
```

### Proposed FileOperation Type

```typescript
export interface FileOperation {
    id: string;
    filePath: string;
    fileName: string;  // Extracted from path
    operation: 'read' | 'write' | 'edit' | 'search' | 'find';
    status: 'pending' | 'success' | 'error';
    timestamp: string | number;
    duration: number | null;
    preToolEvent: ClaudeEvent;
    postToolEvent: ClaudeEvent | null;

    // Operation-specific data
    content?: string;          // Read/Write content
    oldContent?: string;       // Edit old content
    newContent?: string;       // Edit new content
    pattern?: string;          // Grep/Glob pattern
    searchResults?: string;    // Grep results
    fileList?: string[];       // Glob results
    language?: string;         // Detected language for syntax highlighting
    lineCount?: number;        // File stats
}

export type ViewMode = 'events' | 'tools' | 'files';
```

---

**End of Research Document**
