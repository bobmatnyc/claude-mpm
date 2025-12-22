<script lang="ts">
  import type { FileEntry } from '$lib/stores/files.svelte';

  interface Props {
    files: FileEntry[];
    selectedFile?: FileEntry | null;
    selectedStream?: string;
  }

  let { files, selectedFile = $bindable(null), selectedStream = 'all' }: Props = $props();

  $effect(() => {
    console.log('[FilesView] Props received:', {
      filesLength: files.length,
      selectedFile: selectedFile?.file_path,
      selectedStream,
      firstFile: files[0] ? { path: files[0].file_path, name: files[0].filename, ops: files[0].operations.length } : null,
      allFiles: files.map(f => ({ path: f.file_path, ops: f.operations.length }))
    });
  });

  // Filter files by selected stream (matching ToolsView pattern)
  let filteredFiles = $derived.by(() => {
    const result = selectedStream === '' || selectedStream === 'all'
      ? files
      : files; // TODO: add stream filtering when operations are populated
    console.log('[FilesView] Filtered files:', {
      inputLength: files.length,
      outputLength: result.length,
      selectedStream
    });
    return result;
  });

  let fileListContainer = $state<HTMLDivElement | null>(null);
  let isInitialLoad = $state(true);

  // Helper to check if user is scrolled near bottom
  function isNearBottom(container: HTMLDivElement, threshold = 100): boolean {
    const { scrollTop, scrollHeight, clientHeight } = container;
    return scrollHeight - scrollTop - clientHeight < threshold;
  }

  // Auto-scroll logic: always on initial load, otherwise only if near bottom
  $effect(() => {
    if (filteredFiles.length > 0 && fileListContainer) {
      const shouldScroll = isInitialLoad || isNearBottom(fileListContainer);

      if (shouldScroll) {
        setTimeout(() => {
          if (fileListContainer) {
            fileListContainer.scrollTop = fileListContainer.scrollHeight;
            isInitialLoad = false;
          }
        }, 0);
      }
    }
  });

  // Reset to initial load when stream filter changes (scroll to bottom)
  $effect(() => {
    selectedStream;
    isInitialLoad = true;
  });

  // Format timestamp for display
  function formatTimestamp(timestamp: string): string {
    return new Date(timestamp).toLocaleTimeString();
  }

  // Handle row click
  function selectFile(file: FileEntry) {
    console.log('[FilesView] File clicked:', {
      path: file.file_path,
      filename: file.filename,
      operations: file.operations.length
    });
    selectedFile = file;
    console.log('[FilesView] selectedFile after assignment:', selectedFile?.file_path);
  }

  // Keyboard navigation - matching EventStream pattern
  function handleKeydown(e: KeyboardEvent) {
    if (filteredFiles.length === 0) return;

    const currentIndex = selectedFile
      ? filteredFiles.findIndex(f => f.file_path === selectedFile?.file_path)
      : -1;

    let newIndex = currentIndex;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      newIndex = currentIndex < filteredFiles.length - 1 ? currentIndex + 1 : currentIndex;
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      newIndex = currentIndex > 0 ? currentIndex - 1 : 0;
    } else {
      return;
    }

    if (newIndex !== currentIndex && newIndex >= 0 && newIndex < filteredFiles.length) {
      selectedFile = filteredFiles[newIndex];
      // Scroll into view
      const fileElement = fileListContainer?.querySelector(
        `[data-file-path="${selectedFile.file_path}"]`
      );
      if (fileElement) {
        fileElement.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
      }
    }
  }

  // Get color for operation badge
  function getOperationColor(opType: string): string {
    const op = opType.toLowerCase();
    switch (op) {
      case 'read':
        return 'bg-blue-500/10 text-blue-600 dark:text-blue-400 border-blue-500/20';
      case 'write':
        return 'bg-purple-500/10 text-purple-600 dark:text-purple-400 border-purple-500/20';
      case 'edit':
        return 'bg-orange-500/10 text-orange-600 dark:text-orange-400 border-orange-500/20';
      case 'grep':
        return 'bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20';
      case 'glob':
        return 'bg-pink-500/10 text-pink-600 dark:text-pink-400 border-pink-500/20';
      default:
        return 'bg-slate-500/10 text-slate-600 dark:text-slate-400 border-slate-500/20';
    }
  }
</script>

<div class="flex flex-col h-full bg-white dark:bg-slate-900">
  <!-- Header - matching EventStream/ToolsView pattern -->
  <div class="flex items-center justify-between px-6 py-3 bg-slate-100 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 transition-colors">
    <h2 class="text-lg font-semibold text-slate-900 dark:text-white">Files</h2>
    <span class="text-sm text-slate-700 dark:text-slate-300">{filteredFiles.length} files</span>
  </div>

  <div class="flex-1 overflow-y-auto">
    {#if filteredFiles.length === 0}
      <div class="text-center py-12 text-slate-600 dark:text-slate-400">
        <svg class="w-16 h-16 mx-auto mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        <p class="text-lg mb-2 font-medium">No file operations yet</p>
        <p class="text-sm text-slate-500 dark:text-slate-500">Waiting for file operations...</p>
      </div>
    {:else}
      <!-- Table header - matching EventStream/ToolsView pattern -->
      <div class="grid grid-cols-[200px_1fr_120px] gap-3 px-4 py-2 bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-300 sticky top-0 transition-colors">
        <div>Filename</div>
        <div>Operations</div>
        <div class="text-right">Last Modified</div>
      </div>

      <!-- File rows - scrollable container -->
      <div
        bind:this={fileListContainer}
        onkeydown={handleKeydown}
        tabindex="0"
        role="list"
        aria-label="File list - use arrow keys to navigate"
        class="focus:outline-none overflow-y-auto max-h-[calc(100vh-280px)]"
      >
        {#each filteredFiles as file, i (file.file_path)}
          <button
            data-file-path={file.file_path}
            onclick={() => selectFile(file)}
            class="w-full text-left px-4 py-2.5 transition-colors border-l-4 grid grid-cols-[200px_1fr_120px] gap-3 items-center text-xs
              {selectedFile?.file_path === file.file_path
                ? 'bg-cyan-50 dark:bg-cyan-500/20 border-l-cyan-500 dark:border-l-cyan-400 ring-1 ring-cyan-300 dark:ring-cyan-500/30'
                : `border-l-transparent ${i % 2 === 0 ? 'bg-slate-50 dark:bg-slate-800/40' : 'bg-white dark:bg-slate-800/20'} hover:bg-slate-100 dark:hover:bg-slate-700/30`}"
          >
            <!-- Filename -->
            <div class="font-mono text-slate-900 dark:text-white truncate" title={file.file_path}>
              {file.filename}
            </div>

            <!-- Operations with badges -->
            <div class="flex gap-1 flex-wrap items-center">
              {#each Array.from(file.operation_types) as opType}
                <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wide border {getOperationColor(opType)}">
                  {opType}
                </span>
              {/each}
              <span class="text-slate-700 dark:text-slate-300 text-[10px] font-medium ml-1">
                ×{file.operations.length}
              </span>
            </div>

            <!-- Last Modified (right-aligned) -->
            <div class="text-slate-700 dark:text-slate-300 font-mono text-[11px] text-right">
              {formatTimestamp(file.last_modified)}
            </div>
          </button>
        {/each}
      </div>
    {/if}
  </div>
</div>
