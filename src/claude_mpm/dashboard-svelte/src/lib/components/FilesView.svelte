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
      firstFile: files[0] ? { path: files[0].file_path, name: files[0].filename } : null
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

  // Format timestamp for display
  function formatTime(timestamp: string): string {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  }

  // Format operation types as badges
  function formatOperationTypes(types: Set<string>): string {
    return Array.from(types).join(', ');
  }

  // Handle row click
  function selectFile(file: FileEntry) {
    selectedFile = file;
  }

  // Keyboard navigation
  function handleKeydown(event: KeyboardEvent, file: FileEntry) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      selectFile(file);
    }
  }
</script>

<div class="flex flex-col h-full bg-white dark:bg-slate-900">
  <div class="flex items-center justify-between px-6 py-3 bg-slate-100 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 transition-colors">
    <h2 class="text-lg font-semibold text-slate-900 dark:text-white">Files ({filteredFiles.length})</h2>
  </div>

  <div class="flex-1 overflow-auto border border-slate-200 dark:border-slate-700 rounded-lg m-4">
    <table class="w-full border-collapse text-sm">
      <thead class="sticky top-0 bg-slate-100 dark:bg-slate-800 z-10 border-b-2 border-slate-200 dark:border-slate-700">
        <tr>
          <th class="px-4 py-3 text-left font-semibold text-slate-600 dark:text-slate-400 uppercase text-xs tracking-wider">Filename</th>
          <th class="px-4 py-3 text-left font-semibold text-slate-600 dark:text-slate-400 uppercase text-xs tracking-wider">Path</th>
          <th class="px-4 py-3 text-left font-semibold text-slate-600 dark:text-slate-400 uppercase text-xs tracking-wider">Operations</th>
          <th class="px-4 py-3 text-left font-semibold text-slate-600 dark:text-slate-400 uppercase text-xs tracking-wider">Last Modified</th>
        </tr>
      </thead>
      <tbody>
        {#each filteredFiles as file (file.file_path)}
          <tr
            class="border-b border-slate-200 dark:border-slate-700 cursor-pointer transition-colors border-l-4
              {selectedFile?.file_path === file.file_path
                ? 'bg-cyan-50 dark:bg-cyan-500/20 border-l-cyan-500 dark:border-l-cyan-400'
                : 'border-l-transparent hover:bg-slate-50 dark:hover:bg-slate-800/50'}"
            onclick={() => selectFile(file)}
            onkeydown={(e) => handleKeydown(e, file)}
            tabindex="0"
            role="button"
            aria-pressed={selectedFile?.file_path === file.file_path}
          >
            <td class="px-4 py-3 font-medium font-mono text-slate-900 dark:text-white">{file.filename}</td>
            <td class="px-4 py-3 text-slate-600 dark:text-slate-400 text-xs font-mono max-w-xs overflow-hidden text-ellipsis whitespace-nowrap" title={file.file_path}>{file.directory}</td>
            <td class="px-4 py-3 min-w-[200px]">
              <div class="flex gap-1 flex-wrap items-center">
                {#each Array.from(file.operation_types) as opType}
                  <span class="inline-block px-2 py-0.5 rounded text-xs font-medium uppercase tracking-wide
                    {opType.toLowerCase() === 'read' ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300' :
                     opType.toLowerCase() === 'write' ? 'bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300' :
                     opType.toLowerCase() === 'edit' ? 'bg-orange-100 dark:bg-orange-900/40 text-orange-700 dark:text-orange-300' :
                     opType.toLowerCase() === 'grep' ? 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300' :
                     opType.toLowerCase() === 'glob' ? 'bg-pink-100 dark:bg-pink-900/40 text-pink-700 dark:text-pink-300' :
                     'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300'}"
                  >{opType}</span>
                {/each}
                <span class="text-slate-500 dark:text-slate-400 text-xs font-medium">×{file.operations.length}</span>
              </div>
            </td>
            <td class="px-4 py-3 text-slate-600 dark:text-slate-400 font-mono text-xs whitespace-nowrap">{formatTime(file.last_modified)}</td>
          </tr>
        {/each}

        {#if filteredFiles.length === 0}
          <tr>
            <td colspan="4" class="text-center py-12 text-slate-400 dark:text-slate-500">
              <div class="flex flex-col items-center">
                <svg class="w-16 h-16 mb-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <p class="text-lg mb-2">No file operations yet</p>
                <p class="text-sm">Waiting for file operations...</p>
              </div>
            </td>
          </tr>
        {/if}
      </tbody>
    </table>
  </div>
</div>
