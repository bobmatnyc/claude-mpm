<script lang="ts">
  import type { FileEntry, FileOperation } from '$lib/stores/files.svelte';
  import { onMount } from 'svelte';
  import { codeToHtml, type BundledLanguage } from 'shiki';
  import * as Diff from 'diff';
  import * as Diff2Html from 'diff2html';

  interface GitCommit {
    hash: string;
    author: string;
    date: string;
    message: string;
  }

  interface Props {
    file: FileEntry | null;
  }

  let { file }: Props = $props();

  // Debug logging for file prop changes
  $effect(() => {
    console.log('[FileViewer] File prop changed:', {
      hasFile: !!file,
      path: file?.file_path,
      operations: file?.operations.length
    });
  });

  // State
  let selectedOperation = $state<FileOperation | null>(null);
  let highlightedContent = $state<string>('');
  let diffHtml = $state<string>('');
  let isLoading = $state<boolean>(false);
  let loadError = $state<string | null>(null);
  let gitHistory = $state<GitCommit[]>([]);
  let gitHistoryLoading = $state<boolean>(false);
  let gitHistoryExpanded = $state<boolean>(false);

  // Derived state
  let currentOperation = $derived(selectedOperation || file?.operations[0] || null);
  let showDiff = $derived(currentOperation?.type === 'Edit');
  let showContent = $derived(
    currentOperation?.type === 'Read' ||
    currentOperation?.type === 'Write'
  );

  // Fetch file content from server API
  async function fetchFileContent(filePath: string): Promise<string> {
    console.log('[FileViewer] Fetching content from server:', filePath);

    const response = await fetch('/api/file', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path: filePath })
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Failed to read file' }));
      throw new Error(errorData.error || `HTTP ${response.status}`);
    }

    const data = await response.json();
    if (!data.success) {
      throw new Error(data.error || 'Failed to read file');
    }

    return data.content;
  }

  // Fetch git history from server API
  async function fetchGitHistory(filePath: string): Promise<GitCommit[]> {
    try {
      const response = await fetch('/api/git-history', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: filePath, limit: 10 })
      });

      if (!response.ok) {
        console.warn('[FileViewer] Git history API returned', response.status);
        return [];
      }

      const data = await response.json();
      return data.commits || [];
    } catch (error) {
      console.warn('[FileViewer] Failed to fetch git history:', error);
      return [];
    }
  }

  // Update highlighted content when operation or file changes
  $effect(() => {
    async function updateContent() {
      if (!currentOperation || !file) {
        highlightedContent = '';
        diffHtml = '';
        isLoading = false;
        loadError = null;
        return;
      }

      isLoading = true;
      loadError = null;

      console.log('[FileViewer] Rendering operation:', {
        type: currentOperation.type,
        filePath: file.file_path,
        showDiff,
        showContent
      });

      try {
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
          // For Read/Write operations, fetch current file content from server
          console.log('[FileViewer] Fetching file content from server API');
          const content = await fetchFileContent(file.file_path);

          if (!content) {
            loadError = 'File is empty';
            highlightedContent = '';
            return;
          }

          console.log('[FileViewer] Fetched content:', {
            length: content.length,
            preview: content.substring(0, 100)
          });

          const language = getLanguageFromFilename(file.filename);

          try {
            highlightedContent = await codeToHtml(content, {
              lang: language as BundledLanguage,
              themes: {
                light: 'github-light',
                dark: 'github-dark'
              },
              decorations: [
                {
                  // Add line numbers via CSS counter
                  start: { line: 0, character: 0 },
                  end: { line: content.split('\n').length, character: 0 }
                }
              ]
            });
          } catch (e) {
            // Fallback to plain text if syntax highlighting fails
            console.warn('[FileViewer] Syntax highlighting failed for', language, ':', e);
            highlightedContent = addLineNumbers(content);
          }
        }
      } catch (e) {
        loadError = e instanceof Error ? e.message : 'Failed to render content';
        console.error('[FileViewer] Error rendering content:', e);
      } finally {
        isLoading = false;
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

  // Fetch git history when file changes
  $effect(() => {
    async function loadGitHistory() {
      if (!file) {
        gitHistory = [];
        gitHistoryExpanded = false;
        return;
      }

      gitHistoryLoading = true;
      gitHistory = await fetchGitHistory(file.file_path);
      gitHistoryLoading = false;
    }

    loadGitHistory();
  });

  function getLanguageFromFilename(filename: string): string {
    const ext = filename.split('.').pop()?.toLowerCase();
    const langMap: Record<string, string> = {
      ts: 'typescript',
      tsx: 'tsx',
      js: 'javascript',
      jsx: 'jsx',
      py: 'python',
      svelte: 'svelte',
      json: 'json',
      md: 'markdown',
      markdown: 'markdown',
      html: 'html',
      css: 'css',
      scss: 'scss',
      sass: 'sass',
      sh: 'bash',
      bash: 'bash',
      yaml: 'yaml',
      yml: 'yaml',
      toml: 'toml',
      rs: 'rust',
      go: 'go',
      java: 'java',
      c: 'c',
      cpp: 'cpp',
      h: 'c',
      hpp: 'cpp',
      rb: 'ruby',
      php: 'php',
      sql: 'sql',
      xml: 'xml',
      vue: 'vue'
    };
    return langMap[ext || ''] || 'text';
  }

  function addLineNumbers(content: string): string {
    const lines = content.split('\n');
    const lineNumberWidth = String(lines.length).length;

    const numberedLines = lines.map((line, i) => {
      const lineNum = String(i + 1).padStart(lineNumberWidth, ' ');
      const escaped = escapeHtml(line);
      return `<span class="line"><span class="line-number">${lineNum}</span>${escaped}</span>`;
    }).join('\n');

    return `<pre class="code-with-lines"><code>${numberedLines}</code></pre>`;
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

  function formatRelativeTime(dateStr: string): string {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffDay > 30) {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    } else if (diffDay > 0) {
      return `${diffDay} day${diffDay !== 1 ? 's' : ''} ago`;
    } else if (diffHour > 0) {
      return `${diffHour} hour${diffHour !== 1 ? 's' : ''} ago`;
    } else if (diffMin > 0) {
      return `${diffMin} minute${diffMin !== 1 ? 's' : ''} ago`;
    } else {
      return 'just now';
    }
  }

  function shortenHash(hash: string): string {
    return hash.substring(0, 7);
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
      {#if isLoading}
        <div class="loading-state">
          <div class="spinner"></div>
          <p>Loading content...</p>
        </div>
      {:else if loadError}
        <div class="error-state">
          <p class="error-message">⚠️ {loadError}</p>
        </div>
      {:else if showDiff}
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

      <!-- Git History Section -->
      <div class="git-history-section">
        <button
          class="git-history-toggle"
          onclick={() => gitHistoryExpanded = !gitHistoryExpanded}
        >
          <span class="toggle-icon">{gitHistoryExpanded ? '▼' : '▶'}</span>
          <span class="toggle-label">Git History</span>
          {#if gitHistoryLoading}
            <span class="history-badge loading">Loading...</span>
          {:else if gitHistory.length > 0}
            <span class="history-badge">{gitHistory.length} commit{gitHistory.length !== 1 ? 's' : ''}</span>
          {/if}
        </button>

        {#if gitHistoryExpanded}
          <div class="git-history-content">
            {#if gitHistoryLoading}
              <div class="history-loading">
                <div class="spinner-small"></div>
                <p>Loading git history...</p>
              </div>
            {:else if gitHistory.length === 0}
              <div class="history-empty">
                <p>No git history available</p>
              </div>
            {:else}
              <div class="commit-list">
                {#each gitHistory as commit}
                  <div class="commit-item">
                    <div class="commit-header">
                      <code class="commit-hash">{shortenHash(commit.hash)}</code>
                      <span class="commit-author">{commit.author}</span>
                      <span class="commit-date">{formatRelativeTime(commit.date)}</span>
                    </div>
                    <div class="commit-message">{commit.message}</div>
                  </div>
                {/each}
              </div>
            {/if}
          </div>
        {/if}
      </div>
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

  /* Line numbers for fallback rendering */
  .code-container :global(.code-with-lines) {
    counter-reset: line;
  }

  .code-container :global(.line) {
    display: block;
  }

  .code-container :global(.line-number) {
    display: inline-block;
    width: 3em;
    margin-right: 1em;
    padding-right: 0.5em;
    text-align: right;
    color: var(--color-text-tertiary);
    border-right: 1px solid var(--color-border);
    user-select: none;
  }

  /* Shiki already handles line numbers via themes, but we enhance with CSS */
  .code-container :global(.shiki) {
    padding: 1rem;
    border-radius: 0.375rem;
    overflow-x: auto;
  }

  .code-container :global(.shiki code) {
    counter-reset: line;
  }

  .code-container :global(.shiki code .line) {
    display: block;
  }

  .code-container :global(.shiki code .line::before) {
    content: counter(line);
    counter-increment: line;
    display: inline-block;
    width: 3em;
    margin-right: 1em;
    padding-right: 0.5em;
    text-align: right;
    color: var(--color-text-tertiary);
    border-right: 1px solid var(--color-border);
    user-select: none;
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

  .loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    gap: 1rem;
    color: var(--color-text-secondary);
  }

  .spinner {
    width: 2rem;
    height: 2rem;
    border: 3px solid var(--color-border);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .error-state {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    padding: 2rem;
  }

  .error-message {
    color: #dc2626; /* red-600 */
    background: #fef2f2; /* red-50 */
    border: 1px solid #fecaca; /* red-200 */
    padding: 1rem 1.5rem;
    border-radius: 0.5rem;
    font-size: 0.875rem;
  }

  :global(.dark) .error-message {
    color: #fca5a5; /* red-300 */
    background: #7f1d1d; /* red-900 */
    border-color: #991b1b; /* red-800 */
  }

  /* Git History Section */
  .git-history-section {
    margin-top: 1.5rem;
    border-top: 1px solid var(--color-border);
    padding-top: 1rem;
  }

  .git-history-toggle {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.75rem 1rem;
    background: var(--color-bg-secondary);
    border: 1px solid var(--color-border);
    border-radius: 0.375rem;
    cursor: pointer;
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--color-text-primary);
    transition: background-color 0.2s;
  }

  .git-history-toggle:hover {
    background: var(--color-bg-tertiary);
  }

  .toggle-icon {
    font-size: 0.75rem;
    color: var(--color-text-secondary);
  }

  .toggle-label {
    flex: 1;
    text-align: left;
  }

  .history-badge {
    padding: 0.25rem 0.5rem;
    background: var(--color-primary);
    color: white;
    border-radius: 0.25rem;
    font-size: 0.75rem;
    font-weight: 500;
  }

  .history-badge.loading {
    background: var(--color-text-tertiary);
  }

  .git-history-content {
    margin-top: 0.75rem;
    padding: 1rem;
    background: var(--color-bg-secondary);
    border: 1px solid var(--color-border);
    border-radius: 0.375rem;
  }

  .history-loading {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 1rem;
    color: var(--color-text-secondary);
    font-size: 0.875rem;
  }

  .spinner-small {
    width: 1.25rem;
    height: 1.25rem;
    border: 2px solid var(--color-border);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  .history-empty {
    padding: 1.5rem;
    text-align: center;
    color: var(--color-text-tertiary);
    font-size: 0.875rem;
    font-style: italic;
  }

  .commit-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .commit-item {
    padding: 0.75rem;
    background: var(--color-bg-primary);
    border: 1px solid var(--color-border);
    border-radius: 0.375rem;
  }

  .commit-header {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 0.5rem;
    font-size: 0.8125rem;
  }

  .commit-hash {
    padding: 0.125rem 0.375rem;
    background: var(--color-bg-code);
    border: 1px solid var(--color-border);
    border-radius: 0.25rem;
    font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
    font-size: 0.75rem;
    color: var(--color-primary);
  }

  .commit-author {
    font-weight: 500;
    color: var(--color-text-primary);
  }

  .commit-date {
    margin-left: auto;
    color: var(--color-text-tertiary);
  }

  .commit-message {
    font-size: 0.875rem;
    color: var(--color-text-secondary);
    line-height: 1.5;
  }
</style>
