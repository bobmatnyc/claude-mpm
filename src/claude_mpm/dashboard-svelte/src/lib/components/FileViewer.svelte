<script lang="ts">
  import { onMount } from 'svelte';
  import type { FileEntry } from '$lib/stores/files.svelte';
  import { themeStore } from '$lib/stores/theme.svelte';
  import Highlight, { HighlightSvelte } from 'svelte-highlight';
  import python from 'svelte-highlight/languages/python';
  import typescript from 'svelte-highlight/languages/typescript';
  import javascript from 'svelte-highlight/languages/javascript';
  import markdown from 'svelte-highlight/languages/markdown';
  import json from 'svelte-highlight/languages/json';
  import xml from 'svelte-highlight/languages/xml';
  import css from 'svelte-highlight/languages/css';
  import bash from 'svelte-highlight/languages/bash';
  import yaml from 'svelte-highlight/languages/yaml';
  import scss from 'svelte-highlight/languages/scss';
  import sql from 'svelte-highlight/languages/sql';

  interface Props {
    file: FileEntry | null;
    content: string;
    isLoading?: boolean;
  }

  let { file, content, isLoading = false }: Props = $props();

  // Project root for relative path display
  let projectRoot = $state<string>('');

  onMount(async () => {
    // Fetch working directory for relative path display
    try {
      const response = await fetch('/api/working-directory');
      const data = await response.json();
      if (data.working_directory) {
        projectRoot = data.working_directory;
      }
    } catch (error) {
      console.error('[FileViewer] Failed to fetch working directory:', error);
    }
  });

  type ViewMode = 'content' | 'changes';
  let viewMode = $state<ViewMode>('content');

  // Git commit history
  interface CommitInfo {
    hash: string;
    full_hash: string;
    message: string;
    time_ago: string;
  }

  // Git diff state
  let gitDiff = $state<string>('');
  let hasGitChanges = $state<boolean>(false);
  let isGitTracked = $state<boolean>(false);
  let isDiffLoading = $state<boolean>(false);
  let commitHistory = $state<CommitInfo[]>([]);
  let hasUncommitted = $state<boolean>(false);
  let selectedCommit = $state<string>('');  // Empty string means "uncommitted"

  // Fetch git diff when file changes, view mode changes, or commit selection changes
  $effect(() => {
    if (file && viewMode === 'changes') {
      fetchGitDiff(selectedCommit);
    }
  });

  async function fetchGitDiff(commitHash: string = '') {
    if (!file) return;

    isDiffLoading = true;
    try {
      const url = commitHash
        ? `/api/file/diff?path=${encodeURIComponent(file.path)}&commit=${encodeURIComponent(commitHash)}`
        : `/api/file/diff?path=${encodeURIComponent(file.path)}`;

      const response = await fetch(url);
      const data = await response.json();

      if (data.success) {
        gitDiff = data.diff || '';
        hasGitChanges = data.has_changes || false;
        isGitTracked = data.tracked !== false;
        commitHistory = data.history || [];
        hasUncommitted = data.has_uncommitted || false;
      } else {
        gitDiff = '';
        hasGitChanges = false;
        isGitTracked = false;
        commitHistory = [];
        hasUncommitted = false;
      }
    } catch (error) {
      console.error('Failed to fetch git diff:', error);
      gitDiff = '';
      hasGitChanges = false;
      isGitTracked = false;
      commitHistory = [];
      hasUncommitted = false;
    } finally {
      isDiffLoading = false;
    }
  }

  // Update commit selection
  function selectCommit(commitHash: string) {
    selectedCommit = commitHash;
    fetchGitDiff(commitHash);
  }

  // Check for git changes on file load
  $effect(() => {
    if (file) {
      checkGitStatus();
    }
  });

  async function checkGitStatus() {
    if (!file) return;

    console.log('[FileViewer] Checking git status for:', file.path);
    console.log('[FileViewer] File object:', file);

    try {
      const url = `/api/file/diff?path=${encodeURIComponent(file.path)}`;
      console.log('[FileViewer] Fetching from URL:', url);

      const response = await fetch(url);
      console.log('[FileViewer] Response status:', response.status);

      const data = await response.json();
      console.log('[FileViewer] Git status response:', JSON.stringify(data, null, 2));

      if (data.success) {
        hasGitChanges = data.has_changes || false;
        isGitTracked = data.tracked !== false;
        commitHistory = data.history || [];
        hasUncommitted = data.has_uncommitted || false;

        // Reset selected commit when file changes
        selectedCommit = '';

        console.log('[FileViewer] Git status updated:', {
          hasGitChanges,
          isGitTracked,
          showToggle: isGitTracked && (hasUncommitted || commitHistory.length > 0),
          tracked_value: data.tracked,
          has_changes_value: data.has_changes,
          history_count: commitHistory.length,
          has_uncommitted: hasUncommitted
        });
      } else {
        console.log('[FileViewer] Git status check failed:', data.error);
        hasGitChanges = false;
        isGitTracked = false;
        commitHistory = [];
        hasUncommitted = false;
      }
    } catch (error) {
      console.error('[FileViewer] Failed to check git status:', error);
      hasGitChanges = false;
      isGitTracked = false;
      commitHistory = [];
      hasUncommitted = false;
    }
  }

  // Compute whether to enable the Changes button
  // Show if tracked AND (has uncommitted changes OR has commit history)
  let showToggle = $derived(isGitTracked && (hasUncommitted || commitHistory.length > 0));

  // Format git diff with syntax highlighting
  function formatGitDiff(diffText: string): string {
    const lines = diffText.split('\n');
    return lines.map(line => {
      if (line.startsWith('@@')) {
        return `<span class="diff-hunk">${escapeHtml(line)}</span>`;
      } else if (line.startsWith('+++') || line.startsWith('---')) {
        return `<span class="diff-file">${escapeHtml(line)}</span>`;
      } else if (line.startsWith('+')) {
        return `<span class="diff-add">${escapeHtml(line)}</span>`;
      } else if (line.startsWith('-')) {
        return `<span class="diff-remove">${escapeHtml(line)}</span>`;
      } else if (line.startsWith('diff --git')) {
        return `<span class="diff-header">${escapeHtml(line)}</span>`;
      } else if (line.startsWith('index ')) {
        return `<span class="diff-index">${escapeHtml(line)}</span>`;
      } else {
        return `<span class="diff-context">${escapeHtml(line)}</span>`;
      }
    }).join('\n');
  }

  function escapeHtml(text: string): string {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Map file extensions to language modules
  const langMap: Record<string, any> = {
    py: python,
    ts: typescript,
    tsx: typescript,
    js: javascript,
    jsx: javascript,
    md: markdown,
    markdown: markdown,
    json: json,
    html: xml,
    xml: xml,
    css: css,
    scss: scss,
    sass: scss,
    sh: bash,
    bash: bash,
    yaml: yaml,
    yml: yaml,
    sql: sql,
  };

  function getLanguage(filename: string) {
    const ext = filename.split('.').pop()?.toLowerCase() || '';
    return langMap[ext] || null;
  }

  function formatSize(bytes: number): string {
    if (bytes === 0) return '0 B';
    const kb = bytes / 1024;
    if (kb < 1024) return `${kb.toFixed(1)} KB`;
    const mb = kb / 1024;
    return `${mb.toFixed(1)} MB`;
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

{#if file}
  <div class="file-viewer">
    <!-- Header -->
    <div class="viewer-header">
      <div class="file-info">
        <h3 class="file-path">{getDisplayPath(file.path)}</h3>
        <p class="file-meta">
          {formatSize(file.size)}
          · Last modified {new Date(file.modified * 1000).toLocaleString()}
        </p>
      </div>

      <!-- View Mode Toggle (always show, but disable Changes if no git changes) -->
      <div class="view-toggle">
        <button
          class="toggle-btn"
          class:active={viewMode === 'content'}
          onclick={() => viewMode = 'content'}
        >
          Content
        </button>
        <button
          class="toggle-btn"
          class:active={viewMode === 'changes'}
          class:disabled={!showToggle}
          onclick={() => {
            if (showToggle) {
              viewMode = 'changes';
            }
          }}
          disabled={!showToggle}
          title={!showToggle ? 'No git changes detected' : 'View git changes'}
        >
          Changes
        </button>
      </div>
    </div>

    <!-- Content area -->
    <div class="viewer-content">
      {#if isLoading}
        <div class="loading-state">
          <div class="spinner"></div>
          <p>Loading content...</p>
        </div>
      {:else if !content && viewMode === 'content'}
        <div class="no-content">
          <p>File is empty or not loaded</p>
        </div>
      {:else if viewMode === 'changes'}
        <!-- Git Diff View -->
        <div class="diff-container">
          <!-- Commit selector dropdown -->
          {#if commitHistory.length > 0 || hasUncommitted}
            <div class="commit-selector">
              <label for="commit-select">View changes from:</label>
              <select
                id="commit-select"
                bind:value={selectedCommit}
                onchange={() => selectCommit(selectedCommit)}
              >
                {#if hasUncommitted}
                  <option value="">Uncommitted changes</option>
                {/if}
                {#each commitHistory as commit}
                  <option value={commit.full_hash}>
                    {commit.hash} - {commit.message} ({commit.time_ago})
                  </option>
                {/each}
              </select>
            </div>
          {/if}

          {#if isDiffLoading}
            <div class="loading-state">
              <div class="spinner"></div>
              <p>Loading git diff...</p>
            </div>
          {:else if !hasGitChanges && !selectedCommit}
            <div class="no-content">
              <p>No uncommitted changes detected</p>
            </div>
          {:else if !gitDiff}
            <div class="no-content">
              <p>No changes in selected commit</p>
            </div>
          {:else}
            <pre class="diff-content">{@html formatGitDiff(gitDiff)}</pre>
          {/if}
        </div>
      {:else}
        <!-- Syntax highlighted content -->
        <div class="code-container" data-theme={themeStore.current}>
          {#if file.name.endsWith('.svelte')}
            <HighlightSvelte code={content} />
          {:else}
            {@const lang = getLanguage(file.name)}
            {#if lang}
              <Highlight language={lang} code={content} />
            {:else}
              <!-- Fallback for unsupported file types -->
              <pre class="plaintext">{content}</pre>
            {/if}
          {/if}
        </div>
      {/if}
    </div>
  </div>
{:else}
  <div class="file-viewer empty">
    <div class="empty-message">
      <p>Select a file to view its contents</p>
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
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 1.5rem;
    border-bottom: 1px solid var(--color-border);
    background: var(--color-bg-secondary);
  }

  .file-info {
    flex: 1;
    min-width: 0;
  }

  .view-toggle {
    display: flex;
    gap: 0;
    background: var(--color-bg-primary);
    border: 1px solid var(--color-border);
    border-radius: 0.375rem;
    overflow: hidden;
  }

  .toggle-btn {
    padding: 0.375rem 0.75rem;
    font-size: 0.8125rem;
    font-weight: 500;
    color: var(--color-text-secondary);
    background: transparent;
    border: none;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .toggle-btn:hover:not(.disabled) {
    background: var(--color-bg-secondary);
    color: var(--color-text-primary);
  }

  .toggle-btn.active {
    background: var(--color-primary);
    color: white;
  }

  .toggle-btn.disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .toggle-btn:not(:last-child) {
    border-right: 1px solid var(--color-border);
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

  .viewer-content {
    flex: 1;
    overflow: auto;
    padding: 1rem;
  }

  .code-container {
    font-size: 0.875rem;
    line-height: 1.5;
  }

  .code-container :global(pre) {
    margin: 0;
    padding: 0 !important;
    border-radius: 0.375rem;
    overflow-x: auto;
  }

  .code-container :global(pre code.hljs) {
    display: block;
    padding: 1rem;
    border-radius: 0.375rem;
  }

  /* Light theme overrides for syntax highlighting */
  .code-container[data-theme='light'] :global(pre code.hljs) {
    background: #fafafa !important;
    color: #383a42 !important;
  }

  .code-container[data-theme='light'] :global(.hljs-comment),
  .code-container[data-theme='light'] :global(.hljs-quote) {
    color: #a0a1a7 !important;
  }

  .code-container[data-theme='light'] :global(.hljs-keyword),
  .code-container[data-theme='light'] :global(.hljs-selector-tag),
  .code-container[data-theme='light'] :global(.hljs-addition) {
    color: #a626a4 !important;
  }

  .code-container[data-theme='light'] :global(.hljs-number),
  .code-container[data-theme='light'] :global(.hljs-string),
  .code-container[data-theme='light'] :global(.hljs-meta .hljs-string),
  .code-container[data-theme='light'] :global(.hljs-literal),
  .code-container[data-theme='light'] :global(.hljs-doctag),
  .code-container[data-theme='light'] :global(.hljs-regexp) {
    color: #50a14f !important;
  }

  .code-container[data-theme='light'] :global(.hljs-title),
  .code-container[data-theme='light'] :global(.hljs-section),
  .code-container[data-theme='light'] :global(.hljs-name),
  .code-container[data-theme='light'] :global(.hljs-selector-id),
  .code-container[data-theme='light'] :global(.hljs-selector-class) {
    color: #c18401 !important;
  }

  .code-container[data-theme='light'] :global(.hljs-attribute),
  .code-container[data-theme='light'] :global(.hljs-attr),
  .code-container[data-theme='light'] :global(.hljs-variable),
  .code-container[data-theme='light'] :global(.hljs-template-variable),
  .code-container[data-theme='light'] :global(.hljs-class .hljs-title),
  .code-container[data-theme='light'] :global(.hljs-type) {
    color: #986801 !important;
  }

  .code-container[data-theme='light'] :global(.hljs-symbol),
  .code-container[data-theme='light'] :global(.hljs-bullet),
  .code-container[data-theme='light'] :global(.hljs-subst),
  .code-container[data-theme='light'] :global(.hljs-meta),
  .code-container[data-theme='light'] :global(.hljs-meta .hljs-keyword),
  .code-container[data-theme='light'] :global(.hljs-selector-attr),
  .code-container[data-theme='light'] :global(.hljs-selector-pseudo),
  .code-container[data-theme='light'] :global(.hljs-link) {
    color: #4078f2 !important;
  }

  .code-container[data-theme='light'] :global(.hljs-built_in),
  .code-container[data-theme='light'] :global(.hljs-deletion) {
    color: #e45649 !important;
  }

  /* Dark theme overrides for syntax highlighting */
  .code-container[data-theme='dark'] :global(pre code.hljs) {
    background: #282c34 !important;
    color: #abb2bf !important;
  }

  .code-container[data-theme='dark'] :global(.hljs-comment),
  .code-container[data-theme='dark'] :global(.hljs-quote) {
    color: #5c6370 !important;
  }

  .code-container[data-theme='dark'] :global(.hljs-keyword),
  .code-container[data-theme='dark'] :global(.hljs-selector-tag),
  .code-container[data-theme='dark'] :global(.hljs-addition) {
    color: #c678dd !important;
  }

  .code-container[data-theme='dark'] :global(.hljs-number),
  .code-container[data-theme='dark'] :global(.hljs-string),
  .code-container[data-theme='dark'] :global(.hljs-meta .hljs-string),
  .code-container[data-theme='dark'] :global(.hljs-literal),
  .code-container[data-theme='dark'] :global(.hljs-doctag),
  .code-container[data-theme='dark'] :global(.hljs-regexp) {
    color: #98c379 !important;
  }

  .code-container[data-theme='dark'] :global(.hljs-title),
  .code-container[data-theme='dark'] :global(.hljs-section),
  .code-container[data-theme='dark'] :global(.hljs-name),
  .code-container[data-theme='dark'] :global(.hljs-selector-id),
  .code-container[data-theme='dark'] :global(.hljs-selector-class) {
    color: #e5c07b !important;
  }

  .code-container[data-theme='dark'] :global(.hljs-attribute),
  .code-container[data-theme='dark'] :global(.hljs-attr),
  .code-container[data-theme='dark'] :global(.hljs-variable),
  .code-container[data-theme='dark'] :global(.hljs-template-variable),
  .code-container[data-theme='dark'] :global(.hljs-class .hljs-title),
  .code-container[data-theme='dark'] :global(.hljs-type) {
    color: #d19a66 !important;
  }

  .code-container[data-theme='dark'] :global(.hljs-symbol),
  .code-container[data-theme='dark'] :global(.hljs-bullet),
  .code-container[data-theme='dark'] :global(.hljs-subst),
  .code-container[data-theme='dark'] :global(.hljs-meta),
  .code-container[data-theme='dark'] :global(.hljs-meta .hljs-keyword),
  .code-container[data-theme='dark'] :global(.hljs-selector-attr),
  .code-container[data-theme='dark'] :global(.hljs-selector-pseudo),
  .code-container[data-theme='dark'] :global(.hljs-link) {
    color: #61afef !important;
  }

  .code-container[data-theme='dark'] :global(.hljs-built_in),
  .code-container[data-theme='dark'] :global(.hljs-deletion) {
    color: #e06c75 !important;
  }

  .code-container .plaintext {
    margin: 0;
    padding: 1rem;
    border-radius: 0.375rem;
    overflow-x: auto;
    background: var(--color-bg-secondary);
    color: var(--color-text-primary);
    font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
    font-size: 0.875rem;
    line-height: 1.5;
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
    to {
      transform: rotate(360deg);
    }
  }

  /* Diff View Styles */
  .diff-container {
    font-size: 0.875rem;
    line-height: 1.5;
    height: 100%;
    overflow: auto;
  }

  .commit-selector {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1rem;
    background: var(--color-bg-secondary);
    border-bottom: 1px solid var(--color-border);
    position: sticky;
    top: 0;
    z-index: 10;
  }

  .commit-selector label {
    font-size: 0.8125rem;
    font-weight: 500;
    color: var(--color-text-secondary);
    white-space: nowrap;
  }

  .commit-selector select {
    flex: 1;
    padding: 0.375rem 0.75rem;
    font-size: 0.8125rem;
    font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
    color: var(--color-text-primary);
    background: var(--color-bg-primary);
    border: 1px solid var(--color-border);
    border-radius: 0.375rem;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .commit-selector select:hover {
    border-color: var(--color-primary);
  }

  .commit-selector select:focus {
    outline: none;
    border-color: var(--color-primary);
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
  }

  .diff-content {
    margin: 0;
    padding: 1rem;
    background: var(--color-bg-secondary);
    color: var(--color-text-primary);
    font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
    font-size: 0.875rem;
    line-height: 1.6;
    overflow-x: auto;
    white-space: pre;
    tab-size: 4;
  }

  /* Git diff syntax highlighting */
  .diff-content :global(.diff-header) {
    color: #a78bfa;
    font-weight: 600;
  }

  .diff-content :global(.diff-file) {
    color: #8b5cf6;
    font-weight: 600;
  }

  .diff-content :global(.diff-hunk) {
    color: #0891b2;
    background-color: rgba(8, 145, 178, 0.1);
    font-weight: 600;
  }

  .diff-content :global(.diff-add) {
    background-color: rgba(34, 197, 94, 0.15);
    color: #22c55e;
  }

  .diff-content :global(.diff-remove) {
    background-color: rgba(239, 68, 68, 0.15);
    color: #ef4444;
  }

  .diff-content :global(.diff-context) {
    color: var(--color-text-secondary);
  }

  .diff-content :global(.diff-index) {
    color: var(--color-text-tertiary);
    font-size: 0.8125rem;
  }

  /* Dark mode adjustments */
  :global(.dark) .diff-content :global(.diff-add) {
    background-color: rgba(34, 197, 94, 0.2);
    color: #4ade80;
  }

  :global(.dark) .diff-content :global(.diff-remove) {
    background-color: rgba(239, 68, 68, 0.2);
    color: #f87171;
  }

  :global(.dark) .diff-content :global(.diff-hunk) {
    background-color: rgba(8, 145, 178, 0.15);
  }
</style>
