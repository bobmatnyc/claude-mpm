/**
 * Socket.IO Store (Traditional Svelte Stores)
 *
 * Manages Socket.IO connection state using traditional Svelte stores.
 * Uses writable and derived stores for module-level reactivity.
 *
 * IMPORTANT: This file uses traditional stores instead of Svelte 5 runes
 * because the store is created at module-load time, outside component context.
 * Runes ($state, $derived) can only be used inside components.
 */

import { writable, derived } from 'svelte/store';
import { getSocketClient } from '../lib/socketio.js';

// Default configuration (fallbacks if not running in browser)
const DEFAULT_PORT = 8765;
const DEFAULT_HOST = 'localhost';

// Auto-detect from current page URL (browser environment)
function getAutoDetectedPort() {
  if (typeof window !== 'undefined' && window.location.port) {
    return parseInt(window.location.port, 10);
  }
  return DEFAULT_PORT;
}

function getAutoDetectedHost() {
  if (typeof window !== 'undefined' && window.location.hostname) {
    return window.location.hostname;
  }
  return DEFAULT_HOST;
}

function createSocketStore() {
  // Use writable stores instead of $state
  const connected = writable(false);
  const reconnecting = writable(false);
  const port = writable(getAutoDetectedPort());
  const host = writable(getAutoDetectedHost());

  let client = null;

  // Use derived stores instead of $derived
  const statusText = derived(
    [connected, reconnecting],
    ([$connected, $reconnecting]) =>
      $connected ? 'Connected' : $reconnecting ? 'Reconnecting...' : 'Disconnected'
  );

  const statusColor = derived(
    [connected, reconnecting],
    ([$connected, $reconnecting]) =>
      $connected ? '#22c55e' : $reconnecting ? '#eab308' : '#ef4444'
  );

  const url = derived(
    [host, port],
    ([$host, $port]) => `http://${$host}:${$port}`
  );

  function connect(customHost = null, customPort = null) {
    // Use auto-detected values if no custom values provided
    const finalHost = customHost || getAutoDetectedHost();
    const finalPort = customPort || getAutoDetectedPort();

    host.set(finalHost);
    port.set(finalPort);

    client = getSocketClient(`http://${finalHost}:${finalPort}`);

    // Listen for connection status changes
    client.on('connection_status', (status) => {
      connected.set(status.connected);
      reconnecting.set(status.reconnecting);
    });

    client.connect();
  }

  function disconnect() {
    if (client) {
      client.disconnect();
      connected.set(false);
      reconnecting.set(false);
    }
  }

  function getClient() {
    return client;
  }

  return {
    // Export stores with subscribe method for Svelte auto-subscription
    connected: { subscribe: connected.subscribe },
    reconnecting: { subscribe: reconnecting.subscribe },
    port: { subscribe: port.subscribe },
    host: { subscribe: host.subscribe },
    statusText: { subscribe: statusText.subscribe },
    statusColor: { subscribe: statusColor.subscribe },
    url: { subscribe: url.subscribe },
    // Export methods
    connect,
    disconnect,
    getClient
  };
}

export const socketStore = createSocketStore();
