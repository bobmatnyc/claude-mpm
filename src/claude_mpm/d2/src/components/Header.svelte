<script>
  import { themeStore } from '../stores/theme.js';

  // Use Svelte 5 $props() for type-safe props
  let { statusText, statusColor, port } = $props();

  function handleThemeToggle() {
    themeStore.toggle();
  }
</script>

<header class="header">
  <div class="header-content">
    <div class="title">
      <h1>Claude MPM Dashboard</h1>
      <span class="version">v2.0</span>
    </div>

    <div class="header-actions">
      <div class="connection-status">
        <div class="status-indicator" style="background: {statusColor}"></div>
        <span class="status-text">{statusText}</span>
        <span class="port">:{port}</span>
      </div>

      <button class="theme-toggle" onclick={handleThemeToggle} aria-label="Toggle theme">
        {#if $themeStore === 'light'}
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
          </svg>
        {:else}
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="5"></circle>
            <line x1="12" y1="1" x2="12" y2="3"></line>
            <line x1="12" y1="21" x2="12" y2="23"></line>
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
            <line x1="1" y1="12" x2="3" y2="12"></line>
            <line x1="21" y1="12" x2="23" y2="12"></line>
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
          </svg>
        {/if}
      </button>
    </div>
  </div>
</header>

<style>
  .header {
    height: 60px;
    background: linear-gradient(135deg, var(--header-bg-start) 0%, var(--header-bg-end) 100%);
    border-bottom: 1px solid var(--border-color);
    display: flex;
    align-items: center;
    padding: 0 24px;
    box-shadow: var(--shadow-md);
  }

  .header-content {
    width: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .title {
    display: flex;
    align-items: baseline;
    gap: 12px;
  }

  h1 {
    font-size: 20px;
    font-weight: 600;
    color: var(--text-primary);
    letter-spacing: -0.02em;
  }

  .version {
    font-size: 12px;
    color: var(--text-tertiary);
    font-weight: 500;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .connection-status {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    background: var(--overlay-bg);
    border-radius: 6px;
    border: 1px solid var(--overlay-border);
  }

  .status-indicator {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    box-shadow: 0 0 8px currentColor;
    transition: background 0.3s ease;
  }

  .status-text {
    font-size: 13px;
    font-weight: 500;
    color: var(--text-primary);
  }

  .port {
    font-size: 12px;
    color: var(--text-tertiary);
    font-family: 'Monaco', 'Menlo', monospace;
  }

  .theme-toggle {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    padding: 8px;
    background: var(--overlay-bg);
    border: 1px solid var(--overlay-border);
    border-radius: 6px;
    color: var(--text-primary);
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .theme-toggle:hover {
    background: var(--tab-hover-bg);
    border-color: var(--border-color);
  }

  .theme-toggle:active {
    transform: scale(0.95);
  }

  .theme-toggle svg {
    transition: transform 0.3s ease;
  }

  .theme-toggle:hover svg {
    transform: rotate(15deg);
  }
</style>
