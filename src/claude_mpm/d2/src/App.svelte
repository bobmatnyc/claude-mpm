<script>
  import { onMount, onDestroy } from 'svelte';
  import Header from './components/Header.svelte';
  import Sidebar from './components/Sidebar.svelte';
  import MainContent from './components/MainContent.svelte';
  import { socketStore } from './stores/socket.js';
  import { eventsStore } from './stores/events.js';

  let activeTab = $state('events');

  onMount(() => {
    // Connect to Socket.IO server
    socketStore.connect();

    // Get the client and listen for events
    const client = socketStore.getClient();
    if (client) {
      // Listen for Claude Code events
      client.on('claude_event', (data) => {
        console.log('Received claude_event:', data);
        eventsStore.addEvent(data);
      });

      // Listen for heartbeat events
      client.on('heartbeat', (data) => {
        console.log('Received heartbeat:', data);
        eventsStore.addEvent({
          source: 'system',
          type: 'heartbeat',
          timestamp: data.timestamp,
          data: data
        });
      });

      // Listen for any other events (for debugging)
      client.socket.onAny((eventName, ...args) => {
        if (eventName !== 'claude_event' && eventName !== 'heartbeat' && eventName !== 'connection_status') {
          console.log('Received event:', eventName, args);
        }
      });
    }
  });

  onDestroy(() => {
    // Cleanup on component destroy
    socketStore.disconnect();
  });
</script>

<div class="app">
  <Header
    statusText={$socketStore.statusText}
    statusColor={$socketStore.statusColor}
    port={$socketStore.port}
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
    background: #0f0f0f;
    color: #e0e0e0;
  }

  .app-body {
    flex: 1;
    display: flex;
    overflow: hidden;
  }
</style>
