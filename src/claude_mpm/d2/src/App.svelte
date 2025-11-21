<script>
  import { onMount, onDestroy } from 'svelte';
  import Header from './components/Header.svelte';
  import Sidebar from './components/Sidebar.svelte';
  import MainContent from './components/MainContent.svelte';
  import { socketStore } from './stores/socket.js';
  import { eventsStore } from './stores/events.js';
  import { themeStore } from './stores/theme.js';

  // Destructure individual stores from socketStore
  const { statusText, statusColor, port } = socketStore;

  let activeTab = $state('events');

  // Socket.IO client instance (set during onMount)
  let client = null;

  // Event handler functions (defined outside lifecycle for proper cleanup)
  function handleClaudeEvent(data) {
    console.log('Received claude_event:', data);
    eventsStore.addEvent(data);
  }

  function handleHeartbeat(data) {
    console.log('Received heartbeat:', data);
    eventsStore.addEvent({
      source: 'system',
      type: 'heartbeat',
      timestamp: data.timestamp,
      data: data
    });
  }

  function handleAnyEvent(eventName, ...args) {
    if (eventName !== 'claude_event' && eventName !== 'heartbeat' && eventName !== 'connection_status') {
      console.log('Received event:', eventName, args);
    }
  }

  onMount(() => {
    // Initialize theme on mount
    themeStore.initialize();

    // Connect to Socket.IO server
    socketStore.connect();

    // Get the client and listen for events
    client = socketStore.getClient();
    if (client) {
      // Listen for Claude Code events
      client.on('claude_event', handleClaudeEvent);

      // Listen for heartbeat events
      client.on('heartbeat', handleHeartbeat);

      // Listen for any other events (for debugging)
      client.socket.onAny(handleAnyEvent);
    }
  });

  onDestroy(() => {
    // Cleanup event listeners before disconnect
    if (client) {
      client.off('claude_event', handleClaudeEvent);
      client.off('heartbeat', handleHeartbeat);
      if (client.socket) {
        client.socket.offAny(handleAnyEvent);
      }
    }

    // Disconnect Socket.IO
    socketStore.disconnect();
  });
</script>

<div class="app">
  <Header
    statusText={$statusText}
    statusColor={$statusColor}
    port={$port}
  />

  <div class="app-body">
    <Sidebar bind:activeTab={activeTab} />
    <MainContent activeTab={activeTab} />
  </div>
</div>

<style>
  :global(body) {
    margin: 0;
    padding: 0;
    overflow: hidden;
  }

  .app {
    width: 100vw;
    height: 100vh;
    display: flex;
    flex-direction: column;
    background: var(--bg-primary);
    color: var(--text-primary);
  }

  .app-body {
    flex: 1;
    display: flex;
    overflow: hidden;
  }
</style>
