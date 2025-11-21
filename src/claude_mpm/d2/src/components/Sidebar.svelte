<script>
  // Use Svelte 5 $bindable() for two-way binding
  let { activeTab = $bindable('events') } = $props();

  const tabs = [
    { id: 'events', label: 'Events', icon: '📡' },
    { id: 'agents', label: 'Agents', icon: '🤖' },
    { id: 'files', label: 'Files', icon: '📁' },
    { id: 'tools', label: 'Tools', icon: '🔧' },
    { id: 'activity', label: 'Activity', icon: '📊' }
  ];

  function selectTab(tabId) {
    activeTab = tabId;
  }
</script>

<aside class="sidebar">
  <nav class="nav">
    {#each tabs as tab}
      <button
        class="nav-item"
        class:active={activeTab === tab.id}
        onclick={() => selectTab(tab.id)}
      >
        <span class="icon">{tab.icon}</span>
        <span class="label">{tab.label}</span>
      </button>
    {/each}
  </nav>
</aside>

<style>
  .sidebar {
    width: 200px;
    background: var(--sidebar-bg);
    border-right: 1px solid var(--border-color);
    display: flex;
    flex-direction: column;
    overflow-y: auto;
  }

  .nav {
    display: flex;
    flex-direction: column;
    padding: 16px 0;
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px 20px;
    border: none;
    background: transparent;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.2s ease;
    text-align: left;
    font-size: 14px;
    font-weight: 500;
    border-left: 3px solid transparent;
  }

  .nav-item:hover {
    background: var(--tab-hover-bg);
    color: var(--text-primary);
  }

  .nav-item.active {
    background: color-mix(in srgb, var(--accent-color) 10%, transparent);
    color: var(--accent-color);
    border-left-color: var(--accent-color);
  }

  .icon {
    font-size: 16px;
    width: 20px;
    text-align: center;
  }

  .label {
    flex: 1;
  }
</style>
