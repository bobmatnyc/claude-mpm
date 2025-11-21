<script>
  import EventsTab from './tabs/EventsTab.svelte';

  // Use Svelte 5 $props()
  let { activeTab } = $props();
</script>

<main class="main-content">
  {#if activeTab === 'events'}
    <EventsTab />
  {:else if activeTab === 'agents'}
    <div class="placeholder">
      <div class="placeholder-icon">🤖</div>
      <h3>Agents</h3>
      <p>Agent monitoring will be displayed here</p>
    </div>
  {:else if activeTab === 'files'}
    <div class="placeholder">
      <div class="placeholder-icon">📁</div>
      <h3>Files</h3>
      <p>File operations will be displayed here</p>
    </div>
  {:else if activeTab === 'tools'}
    <div class="placeholder">
      <div class="placeholder-icon">🔧</div>
      <h3>Tools</h3>
      <p>Tool execution will be displayed here</p>
    </div>
  {:else if activeTab === 'activity'}
    <div class="placeholder">
      <div class="placeholder-icon">📊</div>
      <h3>Activity</h3>
      <p>Activity metrics will be displayed here</p>
    </div>
  {/if}
</main>

<style>
  .main-content {
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  .placeholder {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: var(--text-secondary);
    text-align: center;
    padding: 40px;
  }

  .placeholder-icon {
    font-size: 64px;
    margin-bottom: 24px;
    opacity: 0.5;
  }

  .placeholder h3 {
    font-size: 24px;
    font-weight: 600;
    color: var(--text-secondary);
    margin-bottom: 8px;
  }

  .placeholder p {
    font-size: 14px;
    color: var(--text-tertiary);
  }
</style>
