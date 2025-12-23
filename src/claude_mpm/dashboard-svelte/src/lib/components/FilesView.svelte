<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { socketStore } from '$lib/stores/socket.svelte';
  import type { ClaudeEvent } from '$lib/types/events';
  import type { TouchedFile } from '$lib/stores/files.svelte';
  import { fetchFileContent, extractFilePath, getOperationType, getFileName, extractContent } from '$lib/stores/files.svelte';

  interface Props {
    selectedStream?: string;
    selectedFile?: TouchedFile | null;
    fileContent?: string;
    contentLoading?: boolean;
  }

  let {
    selectedStream = '',
    selectedFile = $bindable(null),
    fileContent = $bindable(''),
    contentLoading = $bindable(false)
  }: Props = $props();

  // Project root for relative path display
  let projectRoot = $state<string>('');

  // State
  let touchedFiles = $state<TouchedFile[]>([]);
  let filenameFilter = $state('');

  // Cache to track file content at the time of read operations
  // This allows us to show diffs when files are edited/written later
  const fileContentCache = new Map<string, string>();

  // Deduplicate files by path (keep most recent)
  let uniqueFiles = $derived.by(() => {
    const fileMap = new Map<string, TouchedFile>();

    // Process in reverse order (newest first), so older entries are overwritten
    [...touchedFiles].reverse().forEach(file => {
      fileMap.set(file.path, file);
    });

    // Return as array, sorted by timestamp (newest first)
    return Array.from(fileMap.values()).sort((a, b) => {
      const aTime = typeof a.timestamp === 'string'
        ? new Date(a.timestamp).getTime()
        : a.timestamp;
      const bTime = typeof b.timestamp === 'string'
        ? new Date(b.timestamp).getTime()
        : b.timestamp;
      return bTime - aTime;
    });
  });

  // Filter files by selected stream and filename
  let filteredFiles = $derived.by(() => {
    let files = uniqueFiles;

    // Filter by stream (empty string means show all)
    if (selectedStream !== '') {
      files = files.filter(file => file.sessionId === selectedStream);
    }

    // Filter by filename
    if (filenameFilter.trim() !== '') {
      const filterLower = filenameFilter.toLowerCase();
      files = files.filter(file =>
        file.path.toLowerCase().includes(filterLower) ||
        file.name.toLowerCase().includes(filterLower)
      );
    }

    return files;
  });

  // Subscribe to socket events
  let unsubscribeEvents: (() => void) | null = null;

  onMount(async () => {
    console.log('[FilesView] Mounted, subscribing to socket events');

    // Fetch working directory for relative path display
    try {
      const response = await fetch('/api/working-directory');
      const data = await response.json();
      if (data.success && data.working_directory) {
        projectRoot = data.working_directory;
        console.log('[FilesView] Project root:', projectRoot);
      }
    } catch (error) {
      console.error('[FilesView] Failed to fetch working directory:', error);
    }

    // Subscribe to events store
    unsubscribeEvents = socketStore.events.subscribe((events) => {
      // Find new tool events (pre_tool with file operations)
      events.forEach((event) => {
        processToolEvent(event);
      });
    });
  });

  onDestroy(() => {
    if (unsubscribeEvents) {
      unsubscribeEvents();
      unsubscribeEvents = null;
    }
  });

  // Process tool events to extract file touches
  async function processToolEvent(event: ClaudeEvent) {
    const data = event.data;
    const dataSubtype =
      data && typeof data === 'object' && !Array.isArray(data)
        ? (data as Record<string, unknown>).subtype as string | undefined
        : undefined;
    const eventSubtype = event.subtype || dataSubtype;

    // Handle post_tool events (for caching read results)
    if (eventSubtype === 'post_tool') {
      const dataRecord = data && typeof data === 'object' && !Array.isArray(data)
        ? data as Record<string, unknown>
        : null;

      const toolName = dataRecord?.tool_name as string | undefined;
      const operation = toolName ? getOperationType(toolName) : null;

      // For Read operations, cache the content from the tool result
      if (operation === 'read') {
        const filePath = extractFilePath(data);
        const toolResult = dataRecord?.tool_result;

        if (filePath && toolResult && typeof toolResult === 'string') {
          fileContentCache.set(filePath, toolResult);
          console.log('[FilesView] Cached read content:', filePath);
        }
      }
      return; // Don't create TouchedFile entries for post_tool
    }

    // Only process pre_tool events for creating TouchedFile entries
    if (eventSubtype !== 'pre_tool') {
      return;
    }

    // Extract tool name
    const dataRecord = data && typeof data === 'object' && !Array.isArray(data)
      ? data as Record<string, unknown>
      : null;

    const toolName = dataRecord?.tool_name as string | undefined;
    if (!toolName) {
      return;
    }

    // Check if this is a file operation tool
    const operation = getOperationType(toolName);
    if (!operation) {
      return;
    }

    // Extract file path
    const filePath = extractFilePath(data);
    if (!filePath) {
      return;
    }

    // Check if we already have this file (by event ID to avoid duplicates)
    const alreadyExists = touchedFiles.some(f => f.eventId === event.id);
    if (alreadyExists) {
      return;
    }

    // Extract content for write/edit operations
    const { oldContent, newContent } = extractContent(data);

    // For write/edit operations, try to get old content
    let finalOldContent = oldContent;
    if ((operation === 'write' || operation === 'edit') && !oldContent) {
      // First try cache
      finalOldContent = fileContentCache.get(filePath);

      // If not in cache, try to fetch from server (for existing files)
      if (!finalOldContent && operation === 'write') {
        try {
          finalOldContent = await fetchFileContent(filePath);
          console.log('[FilesView] Fetched old content for write operation:', filePath);
        } catch (error) {
          // File might not exist yet (new file), which is fine
          console.log('[FilesView] Could not fetch old content (might be new file):', filePath);
        }
      }
    }

    // Extract session_id from event
    const sessionId = (
      event.session_id ||
      event.sessionId ||
      (event.data as any)?.session_id ||
      (event.data as any)?.sessionId ||
      event.source ||
      undefined
    );

    // Add to touched files
    const fileName = getFileName(filePath);
    const touchedFile: TouchedFile = {
      path: filePath,
      name: fileName,
      operation,
      timestamp: event.timestamp,
      toolName,
      eventId: event.id,
      sessionId,
      oldContent: finalOldContent,
      newContent
    };

    console.log('[FilesView] File touched:', touchedFile);
    touchedFiles = [...touchedFiles, touchedFile];

    // Update cache with new content for write/edit operations
    if ((operation === 'write' || operation === 'edit') && newContent) {
      fileContentCache.set(filePath, newContent);
    }
  }

  // Load file content when a file is selected
  async function selectFile(file: TouchedFile) {
    if (selectedFile?.path === file.path) {
      // Clicking the same file - deselect
      selectedFile = null;
      fileContent = '';
      return;
    }

    selectedFile = file;
    contentLoading = true;

    try {
      // Load current file content
      fileContent = await fetchFileContent(file.path);

      console.log('[FilesView] Loaded file content:', {
        path: file.path,
        size: fileContent.length,
        hasOldContent: !!file.oldContent,
        hasNewContent: !!file.newContent,
      });
    } catch (error) {
      console.error('[FilesView] Error loading file content:', error);
      fileContent = `Error loading file: ${error instanceof Error ? error.message : 'Unknown error'}`;
    } finally {
      contentLoading = false;
    }
  }

  // Get operation badge color
  function getOperationColor(operation: string): string {
    switch (operation) {
      case 'read':
        return 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300';
      case 'write':
        return 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300';
      case 'edit':
        return 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300';
      default:
        return 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300';
    }
  }

  // Format timestamp
  function formatTimestamp(timestamp: string | number): string {
    const date = typeof timestamp === 'string' ? new Date(timestamp) : new Date(timestamp);
    return date.toLocaleTimeString();
  }

  // Get file extension
  function getFileExtension(path: string): string {
    const parts = path.split('.');
    return parts.length > 1 ? `.${parts.pop()}` : '';
  }

  // Get file icon
  function getFileIcon(path: string): string {
    const ext = getFileExtension(path);

    if (['.py'].includes(ext)) return '🐍';
    if (['.js', '.ts', '.jsx', '.tsx'].includes(ext)) return '📜';
    if (['.json'].includes(ext)) return '📋';
    if (['.md', '.txt'].includes(ext)) return '📄';
    if (['.css', '.scss', '.sass'].includes(ext)) return '🎨';
    if (['.html', '.svelte', '.vue'].includes(ext)) return '🌐';
    if (['.sh', '.bash'].includes(ext)) return '⚙️';
    if (['.yml', '.yaml'].includes(ext)) return '📝';
    return '📄';
  }

  // Get display path (relative to project root)
  function getDisplayPath(fullPath: string): string {
    if (!projectRoot || !fullPath.startsWith(projectRoot)) {
      return fullPath;
    }
    // Remove project root and ensure leading slash
    const relativePath = fullPath.substring(projectRoot.length);
    return relativePath.startsWith('/') ? relativePath : '/' + relativePath;
  }
</script>

<!-- LEFT PANE: File List (matching Tools/Events styling) -->
<div class="flex flex-col h-full bg-white dark:bg-slate-900">
  <!-- Header with filters -->
  <div class="flex items-center justify-between px-6 py-3 bg-slate-100 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 transition-colors">
    <div class="flex items-center gap-3 flex-1">
      <input
        type="text"
        bind:value={filenameFilter}
        placeholder="Filter by filename..."
        class="px-3 py-1.5 text-sm rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-colors w-64"
      />
    </div>
    <span class="text-sm text-slate-700 dark:text-slate-300">{filteredFiles.length} files</span>
  </div>

  <div class="flex-1 overflow-y-auto">
    {#if filteredFiles.length === 0}
      <div class="text-center py-12 text-slate-600 dark:text-slate-400">
        <svg class="w-16 h-16 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <p class="text-lg mb-2 font-medium">No files touched yet</p>
        <p class="text-sm text-slate-500 dark:text-slate-500">Files that Claude reads, writes, or edits will appear here</p>
      </div>
    {:else}
      <!-- Table header -->
      <div class="grid grid-cols-[50px_1fr_100px_120px] gap-3 px-4 py-2 bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-300 sticky top-0 transition-colors">
        <div></div>
        <div>Filename</div>
        <div>Operation</div>
        <div class="text-right">Timestamp</div>
      </div>

      <!-- File rows - scrollable container -->
      <div
        tabindex="0"
        role="list"
        aria-label="File list"
        class="focus:outline-none overflow-y-auto max-h-[calc(100vh-280px)]"
      >
        {#each filteredFiles as file, i (file.eventId)}
          <button
            onclick={() => selectFile(file)}
            class="w-full text-left px-4 py-2.5 transition-colors border-l-4 grid grid-cols-[50px_1fr_100px_120px] gap-3 items-center text-xs
              {selectedFile?.path === file.path
                ? 'bg-cyan-50 dark:bg-cyan-500/20 border-l-cyan-500 dark:border-l-cyan-400 ring-1 ring-cyan-300 dark:ring-cyan-500/30'
                : `border-l-transparent ${i % 2 === 0 ? 'bg-slate-50 dark:bg-slate-800/40' : 'bg-white dark:bg-slate-800/20'} hover:bg-slate-100 dark:hover:bg-slate-700/30`}"
          >
            <!-- Icon -->
            <div class="text-xl">
              {getFileIcon(file.path)}
            </div>

            <!-- File Path -->
            <div class="text-slate-700 dark:text-slate-300 truncate font-mono text-xs" title={file.path}>
              {file.name}
            </div>

            <!-- Operation -->
            <div class="text-center">
              <span class="px-2 py-0.5 rounded text-[10px] font-medium uppercase {getOperationColor(file.operation)}">
                {file.operation}
              </span>
            </div>

            <!-- Timestamp -->
            <div class="text-slate-700 dark:text-slate-300 font-mono text-[11px] text-right">
              {formatTimestamp(file.timestamp)}
            </div>
          </button>
        {/each}
      </div>
    {/if}
  </div>
</div>
