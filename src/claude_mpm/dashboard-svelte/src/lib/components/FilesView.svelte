<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { socketStore } from '$lib/stores/socket.svelte';
  import type { ClaudeEvent } from '$lib/types/events';
  import type { TouchedFile } from '$lib/stores/files.svelte';
  import { fetchFileContent, extractFilePath, getOperationType, getFileName } from '$lib/stores/files.svelte';

  interface Props {
    selectedStream?: string;
    selectedFile?: TouchedFile | null;
    fileContent?: string;
    contentLoading?: boolean;
  }

  let {
    selectedStream = 'all',
    selectedFile = $bindable(null),
    fileContent = $bindable(''),
    contentLoading = $bindable(false)
  }: Props = $props();

  // State
  let touchedFiles = $state<TouchedFile[]>([]);

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

  // Filter files by selected stream
  let filteredFiles = $derived.by(() => {
    if (selectedStream === 'all' || selectedStream === '') {
      return uniqueFiles;
    }
    // For stream filtering, we'd need to track session_id with each file
    // For now, just return all files when stream is selected
    return uniqueFiles;
  });

  // Subscribe to socket events
  let unsubscribeEvents: (() => void) | null = null;

  onMount(() => {
    console.log('[FilesView] Mounted, subscribing to socket events');

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
  function processToolEvent(event: ClaudeEvent) {
    // Only process pre_tool events (when tool is invoked)
    const data = event.data;
    const dataSubtype =
      data && typeof data === 'object' && !Array.isArray(data)
        ? (data as Record<string, unknown>).subtype as string | undefined
        : undefined;
    const eventSubtype = event.subtype || dataSubtype;

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

    // Add to touched files
    const fileName = getFileName(filePath);
    const touchedFile: TouchedFile = {
      path: filePath,
      name: fileName,
      operation,
      timestamp: event.timestamp,
      toolName,
      eventId: event.id
    };

    console.log('[FilesView] File touched:', touchedFile);
    touchedFiles = [...touchedFiles, touchedFile];
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
      fileContent = await fetchFileContent(file.path);
      console.log('[FilesView] Loaded file content:', {
        path: file.path,
        size: fileContent.length,
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
</script>

<!-- LEFT PANE: File List (matching Tools/Events styling) -->
<div class="flex flex-col h-full bg-white dark:bg-slate-900">
  <!-- Header with filters -->
  <div class="flex items-center justify-between px-6 py-3 bg-slate-100 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 transition-colors">
    <div class="flex items-center gap-3">
      <!-- Future: Add operation filter dropdown here if needed -->
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
        <div>File Path</div>
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
