<script lang="ts">
  import type { FileEntry } from '$lib/stores/files.svelte';
  import type { TouchedFile, DiffLine } from '$lib/stores/files.svelte';
  import { generateDiff } from '$lib/stores/files.svelte';
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
    touchedFile?: TouchedFile | null; // Original TouchedFile with old/new content
  }

  let { file, content, isLoading = false, touchedFile = null }: Props = $props();

  type ViewMode = 'content' | 'changes';
  let viewMode = $state<ViewMode>('content');

  // Compute whether changes are available
  let hasChanges = $derived(
    touchedFile?.oldContent !== undefined &&
    touchedFile?.newContent !== undefined &&
    (touchedFile.operation === 'write' || touchedFile.operation === 'edit')
  );

  // Generate diff when in changes mode
  let diff = $derived.by(() => {
    if (!hasChanges || viewMode !== 'changes') return [];
    return generateDiff(touchedFile!.oldContent!, touchedFile!.newContent!);
  });

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

      <!-- View Mode Toggle (only show if changes available) -->
      {#if hasChanges}
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
            onclick={() => viewMode = 'changes'}
          >
            Changes
          </button>
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
      {:else if !content && viewMode === 'content'}
        <div class="no-content">
          <p>File is empty or not loaded</p>
        </div>
      {:else if viewMode === 'changes'}
        <!-- Diff View -->
        <div class="diff-container">
          {#if diff.length === 0}
            <div class="no-content">
              <p>No changes detected</p>
            </div>
          {:else}
            <pre class="diff-content">{#each diff as line}<span class="diff-line diff-{line.type}">{#if line.type === 'add'}+{:else if line.type === 'remove'}-{:else} {/if}{line.content}
</span>{/each}</pre>
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

  .toggle-btn:hover {
    background: var(--color-bg-secondary);
    color: var(--color-text-primary);
  }

  .toggle-btn.active {
    background: var(--color-primary);
    color: white;
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
  }

  .diff-content {
    margin: 0;
    padding: 0;
    background: var(--color-bg-secondary);
    color: var(--color-text-primary);
    font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
    font-size: 0.875rem;
    line-height: 1.5;
    overflow-x: auto;
  }

  .diff-line {
    display: block;
    padding: 0.125rem 1rem;
    white-space: pre;
  }

  .diff-line.diff-add {
    background-color: rgba(34, 197, 94, 0.15);
    color: #22c55e;
  }

  .diff-line.diff-remove {
    background-color: rgba(239, 68, 68, 0.15);
    color: #ef4444;
  }

  .diff-line.diff-context {
    background-color: transparent;
    color: var(--color-text-primary);
  }

  /* Dark mode adjustments for diff */
  :global(.dark) .diff-line.diff-add {
    background-color: rgba(34, 197, 94, 0.2);
    color: #4ade80;
  }

  :global(.dark) .diff-line.diff-remove {
    background-color: rgba(239, 68, 68, 0.2);
    color: #f87171;
  }
</style>
