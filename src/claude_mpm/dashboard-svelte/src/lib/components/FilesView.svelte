<script lang="ts">
  import type { FileEntry } from '$lib/stores/files.svelte';

  interface Props {
    files: FileEntry[];
    selectedFile?: FileEntry | null;
    sessionFilter?: string | null;
  }

  let { files, selectedFile = $bindable(null), sessionFilter = null }: Props = $props();

  // Filter files by session if needed
  let filteredFiles = $derived(
    sessionFilter
      ? files.filter(f =>
          f.operations.some(op =>
            op.pre_event?.session_id === sessionFilter ||
            op.post_event?.session_id === sessionFilter
          )
        )
      : files
  );

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

<div class="files-view">
  <div class="files-header">
    <h2>Files ({filteredFiles.length})</h2>
  </div>

  <div class="files-table-container">
    <table class="files-table">
      <thead>
        <tr>
          <th>Filename</th>
          <th>Path</th>
          <th>Operations</th>
          <th>Last Modified</th>
        </tr>
      </thead>
      <tbody>
        {#each filteredFiles as file (file.file_path)}
          <tr
            class="file-row"
            class:selected={selectedFile?.file_path === file.file_path}
            onclick={() => selectFile(file)}
            onkeydown={(e) => handleKeydown(e, file)}
            tabindex="0"
            role="button"
            aria-pressed={selectedFile?.file_path === file.file_path}
          >
            <td class="filename">{file.filename}</td>
            <td class="filepath" title={file.file_path}>{file.directory}</td>
            <td class="operations">
              <div class="operation-badges">
                {#each Array.from(file.operation_types) as opType}
                  <span class="badge badge-{opType.toLowerCase()}">{opType}</span>
                {/each}
                <span class="operation-count">×{file.operations.length}</span>
              </div>
            </td>
            <td class="timestamp">{formatTime(file.last_modified)}</td>
          </tr>
        {/each}

        {#if filteredFiles.length === 0}
          <tr>
            <td colspan="4" class="empty-state">
              No file operations yet
            </td>
          </tr>
        {/if}
      </tbody>
    </table>
  </div>
</div>

<style>
  .files-view {
    display: flex;
    flex-direction: column;
    height: 100%;
    gap: 1rem;
  }

  .files-header {
    padding: 0 1rem;
  }

  .files-header h2 {
    margin: 0;
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--color-text-primary);
  }

  .files-table-container {
    flex: 1;
    overflow: auto;
    border: 1px solid var(--color-border);
    border-radius: 0.5rem;
  }

  .files-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.875rem;
  }

  .files-table thead {
    position: sticky;
    top: 0;
    background: var(--color-bg-secondary);
    z-index: 1;
    border-bottom: 2px solid var(--color-border);
  }

  .files-table th {
    padding: 0.75rem 1rem;
    text-align: left;
    font-weight: 600;
    color: var(--color-text-secondary);
    text-transform: uppercase;
    font-size: 0.75rem;
    letter-spacing: 0.05em;
  }

  .files-table tbody tr {
    border-bottom: 1px solid var(--color-border);
  }

  .file-row {
    cursor: pointer;
    transition: background-color 0.15s ease;
  }

  .file-row:hover {
    background: var(--color-bg-hover);
  }

  .file-row.selected {
    background: var(--color-bg-selected);
    border-left: 3px solid var(--color-primary);
  }

  .file-row:focus {
    outline: 2px solid var(--color-primary);
    outline-offset: -2px;
  }

  .files-table td {
    padding: 0.75rem 1rem;
    color: var(--color-text-primary);
  }

  .filename {
    font-weight: 500;
    font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
  }

  .filepath {
    color: var(--color-text-secondary);
    font-size: 0.8125rem;
    font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
    max-width: 300px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .operations {
    min-width: 200px;
  }

  .operation-badges {
    display: flex;
    gap: 0.25rem;
    flex-wrap: wrap;
    align-items: center;
  }

  .badge {
    display: inline-block;
    padding: 0.125rem 0.5rem;
    border-radius: 0.25rem;
    font-size: 0.75rem;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.025em;
  }

  .badge-read {
    background: var(--color-badge-read, #e3f2fd);
    color: var(--color-badge-read-text, #1565c0);
  }

  .badge-write {
    background: var(--color-badge-write, #f3e5f5);
    color: var(--color-badge-write-text, #6a1b9a);
  }

  .badge-edit {
    background: var(--color-badge-edit, #fff3e0);
    color: var(--color-badge-edit-text, #e65100);
  }

  .badge-grep {
    background: var(--color-badge-grep, #e8f5e9);
    color: var(--color-badge-grep-text, #2e7d32);
  }

  .badge-glob {
    background: var(--color-badge-glob, #fce4ec);
    color: var(--color-badge-glob-text, #c2185b);
  }

  .operation-count {
    color: var(--color-text-tertiary);
    font-size: 0.75rem;
    font-weight: 500;
  }

  .timestamp {
    color: var(--color-text-secondary);
    font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
    font-size: 0.8125rem;
    white-space: nowrap;
  }

  .empty-state {
    text-align: center;
    padding: 3rem 1rem;
    color: var(--color-text-tertiary);
    font-style: italic;
  }

  /* Dark mode support */
  @media (prefers-color-scheme: dark) {
    .badge-read {
      background: var(--color-badge-read, #1e3a5f);
      color: var(--color-badge-read-text, #90caf9);
    }

    .badge-write {
      background: var(--color-badge-write, #4a148c);
      color: var(--color-badge-write-text, #ce93d8);
    }

    .badge-edit {
      background: var(--color-badge-edit, #e65100);
      color: var(--color-badge-edit-text, #ffcc80);
    }

    .badge-grep {
      background: var(--color-badge-grep, #1b5e20);
      color: var(--color-badge-grep-text, #a5d6a7);
    }

    .badge-glob {
      background: var(--color-badge-glob, #880e4f);
      color: var(--color-badge-glob-text, #f48fb1);
    }
  }
</style>
