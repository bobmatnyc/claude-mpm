<script>
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
    background: #1a1a1a;
    border-right: 1px solid #333;
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
    color: #888;
    cursor: pointer;
    transition: all 0.2s ease;
    text-align: left;
    font-size: 14px;
    font-weight: 500;
    border-left: 3px solid transparent;
  }

  .nav-item:hover {
    background: rgba(255, 255, 255, 0.05);
    color: #e0e0e0;
  }

  .nav-item.active {
    background: rgba(59, 130, 246, 0.1);
    color: #3b82f6;
    border-left-color: #3b82f6;
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
