<script lang="ts">
  import type { FileEntry, FileOperation } from '$lib/stores/files.svelte';
  import { onMount } from 'svelte';
  import { codeToHtml, type BundledLanguage } from 'shiki';
  import * as Diff from 'diff';
  import * as Diff2Html from 'diff2html';

  interface Props {
    file: FileEntry | null;
  }

  let { file }: Props = $props();

  // State
  let selectedOperation = $state<FileOperation | null>(null);
  let highlightedContent = $state<string>('');
  let diffHtml = $state<string>('');

  // Derived state
  let currentOperation = $derived(selectedOperation || file?.operations[0] || null);
  let showDiff = $derived(currentOperation?.type === 'Edit');
  let showContent = $derived(
    currentOperation?.type === 'Read' ||
    currentOperation?.type === 'Write'
  );

  // Update highlighted content when operation or file changes
  $effect(() => {
    async function updateContent() {
      if (!currentOperation || !file) {
        highlightedContent = '';
        diffHtml = '';
        return;
      }

      if (showDiff && currentOperation.old_string && currentOperation.new_string) {
        // Generate diff HTML
        const patch = Diff.createPatch(
          file.filename,
          currentOperation.old_string,
          currentOperation.new_string,
          'before',
          'after'
        );

        diffHtml = Diff2Html.html(patch, {
          drawFileList: false,
          matching: 'lines',
          outputFormat: 'side-by-side'
        });
      } else if (showContent) {
        // Syntax highlight content
        const content = currentOperation.content || currentOperation.written_content || '';
        const language = getLanguageFromFilename(file.filename);

        try {
          highlightedContent = await codeToHtml(content, {
            lang: language as BundledLanguage,
            themes: {
              light: 'github-light',
              dark: 'github-dark'
            }
          });
        } catch (e) {
          // Fallback to plain text if language detection fails
          highlightedContent = `<pre><code>${escapeHtml(content)}</code></pre>`;
        }
      }
    }

    updateContent();
  });

  // Reset selected operation when file changes
  $effect(() => {
    if (file) {
      selectedOperation = file.operations[0] || null;
    }
  });

  function getLanguageFromFilename(filename: string): string {
    const ext = filename.split('.').pop()?.toLowerCase();
    const langMap: Record<string, string> = {
      ts: 'typescript',
      js: 'javascript',
      py: 'python',
      svelte: 'svelte',
      json: 'json',
      md: 'markdown',
      html: 'html',
      css: 'css',
      sh: 'bash',
      yaml: 'yaml',
      yml: 'yaml',
      toml: 'toml'
    };
    return langMap[ext || ''] || 'text';
  }

  function escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function formatTimestamp(timestamp: string): string {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  }

  function getOperationLabel(op: FileOperation): string {
    const time = formatTimestamp(op.timestamp);
    return `${op.type} - ${time}`;
  }
</script>

{#if file}
  <div class="file-viewer">
    <!-- Header -->
    <div class="viewer-header">
      <div class="file-info">
        <h3 class="file-path">{file.file_path}</h3>
        <p class="file-meta">
          {file.operations.length} operation{file.operations.length !== 1 ? 's' : ''}
          · Last modified {formatTimestamp(file.last_modified)}
        </p>
      </div>

      <!-- Operation selector -->
      {#if file.operations.length > 1}
        <div class="operation-selector">
          <label for="operation-select">View:</label>
          <select
            id="operation-select"
            bind:value={selectedOperation}
          >
            {#each file.operations as operation, i}
              <option value={operation}>
                {getOperationLabel(operation)}
                {i === 0 ? ' (Latest)' : ''}
              </option>
            {/each}
          </select>
        </div>
      {/if}
    </div>

    <!-- Content area -->
    <div class="viewer-content">
      {#if showDiff}
        <!-- Diff view for Edit operations -->
        <div class="diff-container">
          {@html diffHtml}
        </div>
      {:else if showContent}
        <!-- Syntax highlighted content for Read/Write -->
        <div class="code-container">
          {@html highlightedContent}
        </div>
      {:else if currentOperation?.type === 'Grep' || currentOperation?.type === 'Glob'}
        <!-- Search results -->
        <div class="search-results">
          <div class="search-info">
            <strong>Pattern:</strong> <code>{currentOperation.pattern}</code>
          </div>
          {#if currentOperation.matches !== undefined}
            <div class="search-info">
              <strong>Matches:</strong> {currentOperation.matches}
            </div>
          {/if}
          <p class="search-note">
            Full search results available in the raw event data.
          </p>
        </div>
      {:else}
        <div class="no-content">
          <p>No preview available for this operation.</p>
        </div>
      {/if}
    </div>
  </div>
{:else}
  <div class="file-viewer empty">
    <div class="empty-message">
      <p>Select a file to view details</p>
    </div>
  </div>
{/if}

<style>
  .file-viewer {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: var(--color-bg-primary);
    border: 1px solid var(--color-border);
    border-radius: 0.5rem;
    overflow: hidden;
  }

  .file-viewer.empty {
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .empty-message {
    text-align: center;
    color: var(--color-text-tertiary);
    font-size: 1rem;
  }

  .viewer-header {
    padding: 1rem 1.5rem;
    border-bottom: 1px solid var(--color-border);
    background: var(--color-bg-secondary);
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
  }

  .file-info {
    flex: 1;
    min-width: 0;
  }

  .file-path {
    margin: 0 0 0.25rem 0;
    font-size: 1rem;
    font-weight: 600;
    font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
    color: var(--color-text-primary);
    word-break: break-all;
  }

  .file-meta {
    margin: 0;
    font-size: 0.8125rem;
    color: var(--color-text-secondary);
  }

  .operation-selector {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-shrink: 0;
  }

  .operation-selector label {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--color-text-secondary);
  }

  .operation-selector select {
    padding: 0.375rem 0.75rem;
    border: 1px solid var(--color-border);
    border-radius: 0.375rem;
    background: var(--color-bg-primary);
    color: var(--color-text-primary);
    font-size: 0.875rem;
    font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
    cursor: pointer;
  }

  .operation-selector select:focus {
    outline: 2px solid var(--color-primary);
    outline-offset: 2px;
  }

  .viewer-content {
    flex: 1;
    overflow: auto;
    padding: 1rem;
  }

  .diff-container {
    font-size: 0.875rem;
  }

  .diff-container :global(.d2h-wrapper) {
    border: none;
  }

  .diff-container :global(.d2h-file-header) {
    display: none;
  }

  .code-container :global(pre) {
    margin: 0;
    padding: 1rem;
    border-radius: 0.375rem;
    overflow-x: auto;
    font-size: 0.875rem;
    line-height: 1.5;
  }

  .search-results {
    padding: 1rem;
    background: var(--color-bg-secondary);
    border-radius: 0.375rem;
  }

  .search-info {
    margin-bottom: 0.75rem;
    font-size: 0.875rem;
    color: var(--color-text-primary);
  }

  .search-info code {
    padding: 0.125rem 0.375rem;
    background: var(--color-bg-code);
    border-radius: 0.25rem;
    font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
    font-size: 0.8125rem;
  }

  .search-note {
    margin: 1rem 0 0 0;
    padding-top: 0.75rem;
    border-top: 1px solid var(--color-border);
    font-size: 0.8125rem;
    color: var(--color-text-tertiary);
    font-style: italic;
  }

  .no-content {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: var(--color-text-tertiary);
    font-style: italic;
  }
</style>
