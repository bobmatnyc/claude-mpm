<script lang="ts">
  import type { FileEntry } from '$lib/stores/files.svelte';
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
  import 'svelte-highlight/styles/github-dark.css';

  interface Props {
    file: FileEntry | null;
    content: string;
    isLoading?: boolean;
  }

  let { file, content, isLoading = false }: Props = $props();

  type ViewMode = 'content' | 'changes';
  let viewMode = $state<ViewMode>('content');

  // Git diff state
  let gitDiff = $state<string>('');
  let hasGitChanges = $state<boolean>(false);
  let isGitTracked = $state<boolean>(false);
  let isDiffLoading = $state<boolean>(false);

  // Fetch git diff when file changes or when switching to changes view
  $effect(() => {
    if (file && viewMode === 'changes') {
      fetchGitDiff();
    }
  });

  async function fetchGitDiff() {
    if (!file) return;

    isDiffLoading = true;
    try {
      const response = await fetch(`/api/file/diff?path=${encodeURIComponent(file.path)}`);
      const data = await response.json();

      if (data.success) {
        gitDiff = data.diff || '';
        hasGitChanges = data.has_changes || false;
        isGitTracked = data.tracked !== false;
      } else {
        gitDiff = '';
        hasGitChanges = false;
        isGitTracked = false;
      }
    } catch (error) {
      console.error('Failed to fetch git diff:', error);
      gitDiff = '';
      hasGitChanges = false;
      isGitTracked = false;
    } finally {
      isDiffLoading = false;
    }
  }

  // Check for git changes on file load
  $effect(() => {
    if (file) {
      checkGitStatus();
    }
  });

  async function checkGitStatus() {
    if (!file) return;

    try {
      const response = await fetch(`/api/file/diff?path=${encodeURIComponent(file.path)}`);
      const data = await response.json();

      if (data.success) {
        hasGitChanges = data.has_changes || false;
        isGitTracked = data.tracked !== false;
      }
    } catch (error) {
      console.error('Failed to check git status:', error);
      hasGitChanges = false;
      isGitTracked = false;
    }
  }

  // Compute whether to enable the Changes button (only if git tracked and has changes)
  let showToggle = $derived(isGitTracked && hasGitChanges);

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
</script>

{#if file}
  <div class="file-viewer">
    <!-- Header -->
    <div class="viewer-header">
      <div class="file-info">
        <h3 class="file-path">{file.path}</h3>
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
          {#if isDiffLoading}
            <div class="loading-state">
              <div class="spinner"></div>
              <p>Loading git diff...</p>
            </div>
          {:else if !hasGitChanges}
            <div class="no-content">
              <p>No git changes detected</p>
            </div>
          {:else}
            <pre class="diff-content">{@html formatGitDiff(gitDiff)}</pre>
          {/if}
        </div>
      {:else}
        <!-- Syntax highlighted content -->
        <div class="code-container">
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
