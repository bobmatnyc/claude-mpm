<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { socketStore } from '$lib/stores/socket.svelte';
  import type { ClaudeEvent } from '$lib/types/events';
  import type { TouchedFile } from '$lib/stores/files.svelte';
  import { fetchFileContent, extractFilePath, getOperationType, getFileName } from '$lib/stores/files.svelte';
  import FileViewer from './FileViewer.svelte';

  interface Props {
    selectedStream?: string;
  }

  let { selectedStream = 'all' }: Props = $props();

  // State
  let touchedFiles = $state<TouchedFile[]>([]);
  let selectedFile = $state<TouchedFile | null>(null);
  let fileContent = $state<string>('');
  let contentLoading = $state(false);

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

  // Convert TouchedFile to FileEntry for FileViewer compatibility
  type FileEntry = {
    name: string;
    path: string;
    type: 'file';
    size: number;
    modified: number;
  };

  let selectedFileEntry = $derived<FileEntry | null>(
    selectedFile ? {
      name: selectedFile.name,
      path: selectedFile.path,
      type: 'file' as const,
      size: fileContent.length,
      modified: typeof selectedFile.timestamp === 'string'
        ? new Date(selectedFile.timestamp).getTime() / 1000
        : selectedFile.timestamp / 1000
    } : null
  );
</script>

<div class="flex h-full bg-white dark:bg-slate-900">
  <!-- Left: Files List (40%) -->
  <div class="flex flex-col w-2/5 border-r border-slate-200 dark:border-slate-700">
    <!-- Header -->
    <div
      class="flex items-center justify-between px-4 py-3 bg-slate-100 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 transition-colors"
    >
      <div class="flex items-center gap-2">
        <h2 class="text-base font-semibold text-slate-900 dark:text-white">Files Touched by Claude</h2>
      </div>
      <div class="text-xs text-slate-600 dark:text-slate-400">
        {filteredFiles.length} {filteredFiles.length === 1 ? 'file' : 'files'}
      </div>
    </div>

    <!-- File list -->
    <div class="flex-1 overflow-y-auto">
      {#if filteredFiles.length === 0}
        <div class="flex items-center justify-center h-full text-slate-600 dark:text-slate-400">
          <div class="text-center px-4">
            <div class="text-3xl mb-2">📂</div>
            <p class="text-sm font-medium">No files touched yet</p>
            <p class="text-xs mt-1 text-slate-500 dark:text-slate-500">
              Files that Claude reads, writes, or edits will appear here
            </p>
          </div>
        </div>
      {:else}
        <!-- File rows -->
        <div class="focus:outline-none">
          {#each filteredFiles as file, i (file.eventId)}
            <button
              onclick={() => selectFile(file)}
              class="w-full text-left px-3 py-2.5 transition-colors border-l-2 flex items-start gap-2.5 text-xs hover:bg-slate-100 dark:hover:bg-slate-700/30
                {selectedFile?.path === file.path
                  ? 'bg-cyan-50 dark:bg-cyan-500/20 border-l-cyan-500 dark:border-l-cyan-400'
                  : `border-l-transparent ${i % 2 === 0 ? 'bg-slate-50 dark:bg-slate-800/40' : 'bg-white dark:bg-slate-800/20'}`}"
            >
              <!-- Icon -->
              <div class="text-lg flex-shrink-0 mt-0.5">{getFileIcon(file.path)}</div>

              <!-- File info -->
              <div class="flex-1 min-w-0">
                <!-- File name -->
                <div class="font-mono text-slate-700 dark:text-slate-300 truncate text-xs" title={file.path}>
                  {file.name}
                </div>

                <!-- Path (if different from name) -->
                {#if file.path !== file.name}
                  <div class="text-slate-500 dark:text-slate-600 text-[10px] mt-0.5 truncate" title={file.path}>
                    {file.path}
                  </div>
                {/if}

                <!-- Metadata row -->
                <div class="flex items-center gap-2 mt-1.5">
                  <!-- Operation badge -->
                  <span class="px-1.5 py-0.5 rounded text-[10px] font-medium uppercase {getOperationColor(file.operation)}">
                    {file.operation}
                  </span>

                  <!-- Timestamp -->
                  <span class="text-slate-500 dark:text-slate-600 text-[10px]">
                    {formatTimestamp(file.timestamp)}
                  </span>
                </div>
              </div>
            </button>
          {/each}
        </div>
      {/if}
    </div>
  </div>

  <!-- Right: File Viewer (60%) -->
  <div class="flex-1 min-w-0">
    <FileViewer file={selectedFileEntry} content={fileContent} isLoading={contentLoading} />
  </div>
</div>
