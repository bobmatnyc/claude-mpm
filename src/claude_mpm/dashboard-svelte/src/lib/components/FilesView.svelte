<script lang="ts">
  import { onMount } from 'svelte';
  import type { FileEntry } from '$lib/stores/files.svelte';
  import { fetchFiles, fetchFileContent } from '$lib/stores/files.svelte';
  import FileViewer from './FileViewer.svelte';

  interface Props {
    selectedStream?: string;
  }

  let { selectedStream = 'all' }: Props = $props();

  // State
  let files = $state<FileEntry[]>([]);
  let directories = $state<FileEntry[]>([]);
  let currentPath = $state<string>('');
  let isLoading = $state(false);
  let loadError = $state<string | null>(null);
  let selectedFile = $state<FileEntry | null>(null);
  let fileContent = $state<string>('');
  let contentLoading = $state(false);

  // Combined file list (directories first, then files)
  let allEntries = $derived.by(() => {
    return [...directories, ...files];
  });

  // Load files from working directory
  async function loadFiles(path?: string) {
    isLoading = true;
    loadError = null;

    try {
      const listing = await fetchFiles(path);
      currentPath = listing.path;
      directories = listing.directories;
      files = listing.files;
      console.log('[FilesView] Loaded files:', {
        path: currentPath,
        directories: directories.length,
        files: files.length,
      });
    } catch (error) {
      loadError = error instanceof Error ? error.message : 'Failed to load files';
      console.error('[FilesView] Error loading files:', error);
    } finally {
      isLoading = false;
    }
  }

  // Load file content
  async function loadFileContent(file: FileEntry) {
    if (file.type === 'directory') {
      // Navigate into directory
      await loadFiles(file.path);
      selectedFile = null;
      fileContent = '';
      return;
    }

    contentLoading = true;
    selectedFile = file;

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

  // Handle row click
  function selectEntry(entry: FileEntry) {
    console.log('[FilesView] Entry clicked:', {
      name: entry.name,
      type: entry.type,
      path: entry.path,
    });
    loadFileContent(entry);
  }

  // Navigate to parent directory
  async function navigateUp() {
    if (!currentPath) return;

    const parts = currentPath.split('/');
    if (parts.length <= 1) return;

    const parentPath = parts.slice(0, -1).join('/') || '/';
    await loadFiles(parentPath);
    selectedFile = null;
    fileContent = '';
  }

  // Keyboard navigation
  function handleKeydown(e: KeyboardEvent) {
    if (allEntries.length === 0) return;

    const currentIndex = selectedFile
      ? allEntries.findIndex((f) => f.path === selectedFile?.path)
      : -1;

    let newIndex = currentIndex;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      newIndex = currentIndex < allEntries.length - 1 ? currentIndex + 1 : currentIndex;
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      newIndex = currentIndex > 0 ? currentIndex - 1 : 0;
    } else if (e.key === 'Enter' && selectedFile) {
      e.preventDefault();
      loadFileContent(selectedFile);
      return;
    } else if (e.key === 'Backspace') {
      e.preventDefault();
      navigateUp();
      return;
    } else {
      return;
    }

    if (newIndex !== currentIndex && newIndex >= 0 && newIndex < allEntries.length) {
      selectedFile = allEntries[newIndex];
    }
  }

  // Format file size
  function formatSize(bytes: number): string {
    if (bytes === 0) return '-';
    const kb = bytes / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB`;
    const mb = kb / 1024;
    return `${mb.toFixed(1)} MB`;
  }

  // Format timestamp
  function formatTimestamp(timestamp: number): string {
    return new Date(timestamp * 1000).toLocaleTimeString();
  }

  // Get file icon
  function getFileIcon(entry: FileEntry): string {
    if (entry.type === 'directory') return '📁';

    const ext = entry.extension || '';
    if (['.py'].includes(ext)) return '🐍';
    if (['.js', '.ts', '.jsx', '.tsx'].includes(ext)) return '📜';
    if (['.json'].includes(ext)) return '📋';
    if (['.md', '.txt'].includes(ext)) return '📄';
    if (['.css', '.scss', '.sass'].includes(ext)) return '🎨';
    if (['.html', '.svelte', '.vue'].includes(ext)) return '🌐';
    return '📄';
  }

  // Get file type color
  function getFileColor(entry: FileEntry): string {
    if (entry.type === 'directory') {
      return 'text-blue-600 dark:text-blue-400';
    }
    return 'text-slate-700 dark:text-slate-300';
  }

  // Load files on mount
  onMount(() => {
    loadFiles();
  });
</script>

<div class="flex h-full bg-white dark:bg-slate-900">
  <!-- Left: File Browser (40%) -->
  <div class="flex flex-col w-2/5 border-r border-slate-200 dark:border-slate-700">
    <!-- Header with breadcrumb -->
    <div
      class="flex items-center justify-between px-4 py-3 bg-slate-100 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 transition-colors"
    >
      <div class="flex items-center gap-2 flex-1 min-w-0">
        <h2 class="text-base font-semibold text-slate-900 dark:text-white">Files</h2>
        {#if currentPath}
          <span class="text-xs text-slate-600 dark:text-slate-400 font-mono truncate">
            {currentPath.split('/').slice(-2).join('/')}
          </span>
        {/if}
      </div>
      <div class="flex items-center gap-2">
        {#if currentPath}
          <button
            onclick={navigateUp}
            class="px-2 py-1 text-xs bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 rounded transition-colors"
            title="Go up"
          >
            ⬆️
          </button>
        {/if}
        <button
          onclick={() => loadFiles(currentPath)}
          class="px-2 py-1 text-xs bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 rounded transition-colors"
          disabled={isLoading}
          title="Refresh"
        >
          {isLoading ? '⏳' : '🔄'}
        </button>
      </div>
    </div>

    <!-- File list -->
    <div class="flex-1 overflow-y-auto">
      {#if isLoading}
        <div class="flex items-center justify-center h-full text-slate-600 dark:text-slate-400">
          <div class="text-center">
            <div class="text-3xl mb-2">⏳</div>
            <p class="text-sm">Loading...</p>
          </div>
        </div>
      {:else if loadError}
        <div class="flex items-center justify-center h-full text-red-600 dark:text-red-400">
          <div class="text-center">
            <div class="text-3xl mb-2">⚠️</div>
            <p class="text-sm font-semibold">Error</p>
            <p class="text-xs mt-1">{loadError}</p>
          </div>
        </div>
      {:else if allEntries.length === 0}
        <div class="text-center py-8 text-slate-600 dark:text-slate-400">
          <div class="text-3xl mb-2">📂</div>
          <p class="text-sm">Empty directory</p>
        </div>
      {:else}
        <!-- File rows -->
        <div
          onkeydown={handleKeydown}
          tabindex="0"
          role="list"
          aria-label="File list"
          class="focus:outline-none"
        >
          {#each allEntries as entry, i (entry.path)}
            <button
              data-file-path={entry.path}
              onclick={() => selectEntry(entry)}
              class="w-full text-left px-3 py-2 transition-colors border-l-2 flex items-center gap-2 text-xs
                {selectedFile?.path === entry.path
                  ? 'bg-cyan-50 dark:bg-cyan-500/20 border-l-cyan-500 dark:border-l-cyan-400'
                  : `border-l-transparent ${i % 2 === 0 ? 'bg-slate-50 dark:bg-slate-800/40' : 'bg-white dark:bg-slate-800/20'} hover:bg-slate-100 dark:hover:bg-slate-700/30`}"
            >
              <!-- Icon -->
              <div class="text-lg flex-shrink-0">{getFileIcon(entry)}</div>

              <!-- Name and metadata -->
              <div class="flex-1 min-w-0">
                <div class="font-mono {getFileColor(entry)} truncate text-xs" title={entry.path}>
                  {entry.name}{#if entry.type === 'directory'}/{/if}
                </div>
                {#if entry.type === 'file'}
                  <div class="text-slate-500 dark:text-slate-600 text-[10px] mt-0.5">
                    {formatSize(entry.size)}
                  </div>
                {/if}
              </div>
            </button>
          {/each}
        </div>
      {/if}
    </div>
  </div>

  <!-- Right: File Viewer (60%) -->
  <div class="flex-1 min-w-0">
    <FileViewer file={selectedFile} content={fileContent} isLoading={contentLoading} />
  </div>
</div>
