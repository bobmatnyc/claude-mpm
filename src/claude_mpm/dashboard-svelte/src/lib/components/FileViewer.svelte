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
    </div>

    <!-- Content area -->
    <div class="viewer-content">
      {#if isLoading}
        <div class="loading-state">
          <div class="spinner"></div>
          <p>Loading content...</p>
        </div>
      {:else if !content}
        <div class="no-content">
          <p>File is empty or not loaded</p>
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
    padding: 1rem 1.5rem;
    border-bottom: 1px solid var(--color-border);
    background: var(--color-bg-secondary);
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
</style>
