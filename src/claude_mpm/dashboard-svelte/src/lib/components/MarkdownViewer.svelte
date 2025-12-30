<script lang="ts">
  import { onMount } from 'svelte';
  import { marked } from 'marked';
  import mermaid from 'mermaid';
  import { themeStore } from '$lib/stores/theme.svelte';

  interface Props {
    content: string;
  }

  let { content }: Props = $props();

  let renderedHtml = $state<string>('');
  let containerElement: HTMLDivElement;

  // Configure marked for GitHub Flavored Markdown
  marked.setOptions({
    gfm: true,
    breaks: true,
    headerIds: true,
    mangle: false
  });

  // Initialize mermaid with theme-aware configuration
  function initMermaid() {
    const isDark = themeStore.current === 'dark';
    mermaid.initialize({
      startOnLoad: false,
      theme: isDark ? 'dark' : 'default',
      securityLevel: 'loose',
      fontFamily: 'SF Pro, system-ui, -apple-system, sans-serif'
    });
  }

  onMount(() => {
    initMermaid();
  });

  // Re-initialize mermaid when theme changes
  $effect(() => {
    if (themeStore.current) {
      initMermaid();
      // Re-render if we have content
      if (content) {
        renderMarkdown();
      }
    }
  });

  // Render markdown when content changes
  $effect(() => {
    if (content) {
      renderMarkdown();
    }
  });

  async function renderMarkdown() {
    try {
      // Parse markdown to HTML
      const html = await marked.parse(content);
      renderedHtml = html;

      // Wait for DOM to update, then render mermaid diagrams
      setTimeout(async () => {
        if (containerElement) {
          const mermaidBlocks = containerElement.querySelectorAll('code.language-mermaid');

          for (let i = 0; i < mermaidBlocks.length; i++) {
            const block = mermaidBlocks[i] as HTMLElement;
            const code = block.textContent || '';

            try {
              // Generate unique ID for mermaid diagram
              const id = `mermaid-${Date.now()}-${i}`;

              // Render mermaid diagram
              const { svg } = await mermaid.render(id, code);

              // Replace code block with rendered SVG
              const pre = block.parentElement;
              if (pre && pre.tagName === 'PRE') {
                const wrapper = document.createElement('div');
                wrapper.className = 'mermaid-diagram';
                wrapper.innerHTML = svg;
                pre.replaceWith(wrapper);
              }
            } catch (error) {
              console.error('Failed to render mermaid diagram:', error);
              // Leave the code block as-is if rendering fails
            }
          }
        }
      }, 0);
    } catch (error) {
      console.error('Failed to render markdown:', error);
      renderedHtml = `<div class="error">Failed to render markdown: ${error}</div>`;
    }
  }
</script>

<div
  class="markdown-viewer"
  data-theme={themeStore.current}
  bind:this={containerElement}
>
  {@html renderedHtml}
</div>

<style>
  .markdown-viewer {
    padding: 1rem;
    line-height: 1.6;
    color: var(--color-text-primary);
  }

  /* Typography */
  .markdown-viewer :global(h1),
  .markdown-viewer :global(h2),
  .markdown-viewer :global(h3),
  .markdown-viewer :global(h4),
  .markdown-viewer :global(h5),
  .markdown-viewer :global(h6) {
    margin-top: 1.5rem;
    margin-bottom: 0.75rem;
    font-weight: 600;
    line-height: 1.25;
    color: var(--color-text-primary);
  }

  .markdown-viewer :global(h1) {
    font-size: 2rem;
    border-bottom: 2px solid var(--color-border);
    padding-bottom: 0.5rem;
    margin-top: 0;
  }

  .markdown-viewer :global(h2) {
    font-size: 1.5rem;
    border-bottom: 1px solid var(--color-border);
    padding-bottom: 0.375rem;
  }

  .markdown-viewer :global(h3) {
    font-size: 1.25rem;
  }

  .markdown-viewer :global(h4) {
    font-size: 1.125rem;
  }

  .markdown-viewer :global(h5),
  .markdown-viewer :global(h6) {
    font-size: 1rem;
  }

  /* Paragraphs and text */
  .markdown-viewer :global(p) {
    margin-top: 0;
    margin-bottom: 1rem;
  }

  .markdown-viewer :global(strong) {
    font-weight: 600;
    color: var(--color-text-primary);
  }

  .markdown-viewer :global(em) {
    font-style: italic;
  }

  /* Links */
  .markdown-viewer :global(a) {
    color: var(--color-primary);
    text-decoration: none;
    transition: color 0.15s ease;
  }

  .markdown-viewer :global(a:hover) {
    color: #818cf8;
    text-decoration: underline;
  }

  /* Lists */
  .markdown-viewer :global(ul),
  .markdown-viewer :global(ol) {
    margin-top: 0;
    margin-bottom: 1rem;
    padding-left: 2rem;
  }

  .markdown-viewer :global(li) {
    margin-bottom: 0.25rem;
  }

  .markdown-viewer :global(li > p) {
    margin-bottom: 0.5rem;
  }

  .markdown-viewer :global(ul ul),
  .markdown-viewer :global(ol ol),
  .markdown-viewer :global(ul ol),
  .markdown-viewer :global(ol ul) {
    margin-top: 0.25rem;
    margin-bottom: 0.25rem;
  }

  /* Code blocks */
  .markdown-viewer :global(code) {
    padding: 0.2em 0.4em;
    margin: 0;
    font-size: 0.875rem;
    font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
    background-color: rgba(99, 102, 241, 0.1);
    border-radius: 0.25rem;
    color: var(--color-text-primary);
  }

  .markdown-viewer :global(pre) {
    padding: 1rem;
    margin-top: 0;
    margin-bottom: 1rem;
    font-size: 0.875rem;
    line-height: 1.5;
    font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Code', monospace;
    background-color: var(--color-bg-secondary);
    border: 1px solid var(--color-border);
    border-radius: 0.375rem;
    overflow-x: auto;
  }

  .markdown-viewer :global(pre code) {
    padding: 0;
    margin: 0;
    font-size: 100%;
    background-color: transparent;
    border: 0;
    white-space: pre;
    word-break: normal;
  }

  /* Blockquotes */
  .markdown-viewer :global(blockquote) {
    margin: 0 0 1rem 0;
    padding: 0.5rem 1rem;
    border-left: 0.25rem solid var(--color-primary);
    background-color: rgba(99, 102, 241, 0.05);
    color: var(--color-text-secondary);
  }

  .markdown-viewer :global(blockquote > :first-child) {
    margin-top: 0;
  }

  .markdown-viewer :global(blockquote > :last-child) {
    margin-bottom: 0;
  }

  /* Tables */
  .markdown-viewer :global(table) {
    width: 100%;
    margin-bottom: 1rem;
    border-collapse: collapse;
    border-spacing: 0;
    overflow: hidden;
    border-radius: 0.375rem;
    border: 1px solid var(--color-border);
  }

  .markdown-viewer :global(table th),
  .markdown-viewer :global(table td) {
    padding: 0.75rem;
    text-align: left;
    border-bottom: 1px solid var(--color-border);
  }

  .markdown-viewer :global(table th) {
    font-weight: 600;
    background-color: var(--color-bg-secondary);
    color: var(--color-text-primary);
  }

  .markdown-viewer :global(table tr:last-child td) {
    border-bottom: none;
  }

  .markdown-viewer :global(table tr:hover) {
    background-color: rgba(99, 102, 241, 0.05);
  }

  /* Horizontal rule */
  .markdown-viewer :global(hr) {
    height: 0;
    margin: 1.5rem 0;
    border: 0;
    border-top: 1px solid var(--color-border);
  }

  /* Images */
  .markdown-viewer :global(img) {
    max-width: 100%;
    height: auto;
    border-radius: 0.375rem;
    margin: 1rem 0;
  }

  /* Mermaid diagrams */
  .markdown-viewer :global(.mermaid-diagram) {
    margin: 1rem 0;
    padding: 1rem;
    background-color: var(--color-bg-secondary);
    border: 1px solid var(--color-border);
    border-radius: 0.375rem;
    display: flex;
    justify-content: center;
    overflow-x: auto;
  }

  .markdown-viewer :global(.mermaid-diagram svg) {
    max-width: 100%;
    height: auto;
  }

  /* Task lists */
  .markdown-viewer :global(input[type="checkbox"]) {
    margin-right: 0.5rem;
  }

  .markdown-viewer :global(.task-list-item) {
    list-style: none;
  }

  /* Error state */
  .markdown-viewer :global(.error) {
    padding: 1rem;
    background-color: rgba(239, 68, 68, 0.1);
    border: 1px solid #ef4444;
    border-radius: 0.375rem;
    color: #ef4444;
  }

  /* Dark mode adjustments */
  .markdown-viewer[data-theme='dark'] :global(code) {
    background-color: rgba(139, 92, 246, 0.15);
  }

  .markdown-viewer[data-theme='dark'] :global(blockquote) {
    background-color: rgba(139, 92, 246, 0.1);
  }

  .markdown-viewer[data-theme='dark'] :global(table tr:hover) {
    background-color: rgba(139, 92, 246, 0.1);
  }
</style>
