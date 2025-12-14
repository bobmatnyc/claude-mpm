/**
 * Firefox background script for MCP Browser extension (Manifest V2)
 * Firefox uses persistent background pages (no service worker), so lifecycle is simpler
 * Uses browser.* namespace (promise-based) instead of chrome.* (callback-based)
 */

// Configuration
const PORT_RANGE = { start: 8851, end: 8899 };
const SCAN_INTERVAL_MS = 30000; // 30 seconds

// Storage keys
const STORAGE_KEYS = {
  MESSAGE_QUEUE: 'mcp_message_queue',
  LAST_CONNECTED_PORT: 'mcp_last_connected_port',
  LAST_SEQUENCE: 'mcp_last_sequence',
  PORT_PROJECT_MAP: 'mcp_port_project_map',
  DOMAIN_PORT_MAP: 'mcp_domain_port_map'
};

// Max queue size
const MAX_QUEUE_SIZE = 500;

// Status colors
const STATUS_COLORS = {
  RED: '#DC3545',
  YELLOW: '#FFC107',
  GREEN: '#4CAF50'
};

// State management
let activeServers = new Map();
let extensionState = 'starting';
let portProjectMap = {};

// Gap detection
const GAP_DETECTION_ENABLED = true;
const MAX_GAP_SIZE = 50;

// Heartbeat configuration
const HEARTBEAT_INTERVAL = 15000;
const PONG_TIMEOUT = 10000;

// Reconnect configuration
const BASE_RECONNECT_DELAY = 1000;
const MAX_RECONNECT_DELAY = 30000;

// Maximum simultaneous connections
const MAX_CONNECTIONS = 10;

// Connection state (legacy single connection)
let currentConnection = null;
let messageQueue = [];
let connectionReady = false;
let lastSequenceReceived = 0;
let pendingGapRecovery = false;
let outOfOrderBuffer = [];
let lastPongTime = Date.now();
let reconnectAttempts = 0;
let heartbeatInterval = null;
let scanInterval = null;

// Connection status
const connectionStatus = {
  connected: false,
  port: null,
  projectName: null,
  projectPath: null,
  lastError: null,
  messageCount: 0,
  connectionTime: null,
  availableServers: []
};

/**
 * ConnectionManager - Manages multiple WebSocket connections
 */
class ConnectionManager {
  constructor() {
    this.connections = new Map();
    this.tabConnections = new Map();
    this.primaryPort = null;
    this.pendingTabs = new Map();
    this.domainPortMap = {};
  }

  async connectToBackend(port, projectInfo = null) {
    console.log(`[ConnectionManager] Connecting to port ${port}...`);

    if (!this.connections.has(port) && this.connections.size >= MAX_CONNECTIONS) {
      throw new Error(`Maximum connections (${MAX_CONNECTIONS}) reached`);
    }

    if (this.connections.has(port)) {
      const conn = this.connections.get(port);
      if (conn.ws && conn.ws.readyState === WebSocket.OPEN) {
        return conn;
      }
      await this.disconnectBackend(port);
    }

    const connection = {
      ws: null,
      port: port,
      projectId: projectInfo?.project_id || null,
      projectName: projectInfo?.project_name || `Port ${port}`,
      projectPath: projectInfo?.project_path || '',
      tabs: new Set(),
      messageQueue: [],
      connectionReady: false,
      lastSequence: 0,
      reconnectAttempts: 0,
      heartbeatInterval: null,
      lastPongTime: Date.now()
    };

    const ws = new WebSocket(`ws://localhost:${port}`);
    connection.ws = ws;

    await new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        ws.close();
        reject(new Error(`Connection timeout for port ${port}`));
      }, 3000);

      ws.onopen = async () => {
        clearTimeout(timeout);
        console.log(`[ConnectionManager] WebSocket opened for port ${port}`);

        const storageKey = `mcp_last_sequence_${port}`;
        const result = await browser.storage.local.get(storageKey);
        connection.lastSequence = result[storageKey] || 0;

        const initMessage = {
          type: 'connection_init',
          lastSequence: connection.lastSequence,
          extensionVersion: browser.runtime.getManifest().version,
          capabilities: ['console_capture', 'dom_interaction']
        };

        ws.send(JSON.stringify(initMessage));
        resolve();
      };

      ws.onerror = (error) => {
        clearTimeout(timeout);
        reject(error);
      };
    });

    this._setupConnectionHandlers(connection);
    this.connections.set(port, connection);

    if (!this.primaryPort) {
      this.primaryPort = port;
    }

    return connection;
  }

  async disconnectBackend(port) {
    const connection = this.connections.get(port);
    if (!connection) return;

    if (connection.heartbeatInterval) {
      clearInterval(connection.heartbeatInterval);
    }

    if (connection.ws) {
      connection.ws.close();
    }

    const storageKey = `mcp_last_sequence_${port}`;
    await browser.storage.local.set({ [storageKey]: connection.lastSequence });

    for (const [tabId, tabPort] of this.tabConnections.entries()) {
      if (tabPort === port) {
        this.tabConnections.delete(tabId);
      }
    }

    this.connections.delete(port);

    if (this.primaryPort === port) {
      const remainingPorts = Array.from(this.connections.keys());
      this.primaryPort = remainingPorts.length > 0 ? remainingPorts[0] : null;
    }
  }

  getConnectionForTab(tabId) {
    const port = this.tabConnections.get(tabId);
    return port ? this.connections.get(port) : null;
  }

  assignTabToConnection(tabId, port) {
    const connection = this.connections.get(port);
    if (!connection) return;

    const previousPort = this.tabConnections.get(tabId);
    if (previousPort && previousPort !== port) {
      const prevConn = this.connections.get(previousPort);
      if (prevConn) {
        prevConn.tabs.delete(tabId);
      }
    }

    connection.tabs.add(tabId);
    this.tabConnections.set(tabId, port);
  }

  removeTab(tabId) {
    const port = this.tabConnections.get(tabId);
    if (port) {
      const connection = this.connections.get(port);
      if (connection) {
        connection.tabs.delete(tabId);
      }
      this.tabConnections.delete(tabId);
    }
  }

  async sendMessage(tabId, message) {
    const connection = this.getConnectionForTab(tabId);
    if (!connection) return false;

    if (connection.ws && connection.ws.readyState === WebSocket.OPEN && connection.connectionReady) {
      connection.ws.send(JSON.stringify(message));
      return true;
    } else {
      connection.messageQueue.push(message);
      if (connection.messageQueue.length > MAX_QUEUE_SIZE) {
        connection.messageQueue.shift();
      }
      return false;
    }
  }

  getActiveConnections() {
    return Array.from(this.connections.values()).map(conn => ({
      port: conn.port,
      projectName: conn.projectName,
      projectPath: conn.projectPath,
      tabCount: conn.tabs.size,
      queueSize: conn.messageQueue.length,
      ready: conn.connectionReady,
      isPrimary: conn.port === this.primaryPort
    }));
  }

  async registerTab(tabId, url) {
    // Simple strategy: use primary connection or first available
    const targetPort = this.primaryPort || Array.from(this.connections.keys())[0];

    if (targetPort) {
      this.assignTabToConnection(tabId, targetPort);
      return true;
    }

    this.pendingTabs.set(tabId, { url, awaitingAssignment: true });
    return false;
  }

  _setupConnectionHandlers(connection) {
    const { ws, port } = connection;

    ws.onmessage = async (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'connection_ack') {
          connection.connectionReady = true;

          if (data.project_id) {
            connection.projectId = data.project_id;
            connection.projectName = data.project_name || connection.projectName;
            connection.projectPath = data.project_path || connection.projectPath;
          }

          if (data.currentSequence !== undefined) {
            connection.lastSequence = data.currentSequence;
            const storageKey = `mcp_last_sequence_${port}`;
            await browser.storage.local.set({ [storageKey]: connection.lastSequence });
          }

          this._startHeartbeat(connection);
          await this._flushMessageQueue(connection);
          updateBadgeStatus();
          return;
        }

        if (data.type === 'pong') {
          connection.lastPongTime = Date.now();
          return;
        }

        if (data.sequence !== undefined) {
          connection.lastSequence = data.sequence;
        }

      } catch (error) {
        console.error(`[ConnectionManager] Parse error for port ${port}:`, error);
      }
    };

    ws.onerror = (error) => {
      console.error(`[ConnectionManager] WebSocket error for port ${port}:`, error);
    };

    ws.onclose = async () => {
      console.log(`[ConnectionManager] Connection closed for port ${port}`);

      if (connection.heartbeatInterval) {
        clearInterval(connection.heartbeatInterval);
      }

      const storageKey = `mcp_last_sequence_${port}`;
      await browser.storage.local.set({ [storageKey]: connection.lastSequence });

      connection.reconnectAttempts++;
      const delay = Math.min(BASE_RECONNECT_DELAY * Math.pow(2, connection.reconnectAttempts), MAX_RECONNECT_DELAY);

      setTimeout(async () => {
        try {
          this.connections.delete(port);
          await this.connectToBackend(port, {
            project_id: connection.projectId,
            project_name: connection.projectName,
            project_path: connection.projectPath
          });

          for (const tabId of connection.tabs) {
            this.assignTabToConnection(tabId, port);
          }
        } catch (error) {
          console.error(`[ConnectionManager] Reconnect failed for port ${port}:`, error);
        }
      }, delay);

      updateBadgeStatus();
    };
  }

  _startHeartbeat(connection) {
    if (connection.heartbeatInterval) {
      clearInterval(connection.heartbeatInterval);
    }

    connection.heartbeatInterval = setInterval(() => {
      if (connection.ws && connection.ws.readyState === WebSocket.OPEN) {
        const timeSinceLastPong = Date.now() - connection.lastPongTime;
        if (timeSinceLastPong > HEARTBEAT_INTERVAL + PONG_TIMEOUT) {
          connection.ws.close();
          return;
        }

        connection.ws.send(JSON.stringify({
          type: 'heartbeat',
          timestamp: Date.now()
        }));
      }
    }, HEARTBEAT_INTERVAL);
  }

  async _flushMessageQueue(connection) {
    if (!connection.ws || connection.ws.readyState !== WebSocket.OPEN) return;

    while (connection.messageQueue.length > 0) {
      const message = connection.messageQueue.shift();
      try {
        connection.ws.send(JSON.stringify(message));
      } catch (e) {
        connection.messageQueue.unshift(message);
        break;
      }
    }
  }
}

const connectionManager = new ConnectionManager();

/**
 * Update extension badge
 */
function updateBadgeStatus() {
  const activeCount = connectionManager.connections.size;

  if (activeCount > 0) {
    browser.browserAction.setBadgeBackgroundColor({ color: STATUS_COLORS.GREEN });
    browser.browserAction.setBadgeText({ text: String(activeCount) });
  } else if (activeServers.size > 0) {
    browser.browserAction.setBadgeBackgroundColor({ color: STATUS_COLORS.YELLOW });
    browser.browserAction.setBadgeText({ text: String(activeServers.size) });
  } else {
    browser.browserAction.setBadgeBackgroundColor({ color: STATUS_COLORS.YELLOW });
    browser.browserAction.setBadgeText({ text: '...' });
  }
}

/**
 * Scan for available servers
 */
async function scanForServers() {
  console.log(`[MCP Browser] Scanning ports ${PORT_RANGE.start}-${PORT_RANGE.end}...`);
  const servers = [];

  for (let port = PORT_RANGE.start; port <= PORT_RANGE.end; port++) {
    const serverInfo = await probePort(port);
    if (serverInfo) {
      servers.push(serverInfo);
      activeServers.set(port, serverInfo);
    }
  }

  connectionStatus.availableServers = servers;
  updateBadgeStatus();
  return servers;
}

/**
 * Probe a single port
 */
async function probePort(port) {
  return new Promise((resolve) => {
    let ws = null;

    const timeout = setTimeout(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
      resolve(null);
    }, 2000);

    try {
      ws = new WebSocket(`ws://localhost:${port}`);

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'connection_ack') {
            ws.send(JSON.stringify({ type: 'server_info' }));
            return;
          }

          if (data.type === 'server_info_response') {
            clearTimeout(timeout);
            ws.close();

            if (data.project_name && data.project_name !== 'Unknown') {
              resolve({
                port: port,
                projectName: data.project_name,
                projectPath: data.project_path || '',
                version: data.version || '1.0.0'
              });
            } else {
              resolve(null);
            }
          }
        } catch (e) {
          console.warn(`[MCP Browser] Parse error for port ${port}:`, e);
        }
      };

      ws.onerror = () => {
        clearTimeout(timeout);
        resolve(null);
      };

    } catch (error) {
      clearTimeout(timeout);
      resolve(null);
    }
  });
}

/**
 * Auto-connect to best available server
 */
async function autoConnect() {
  console.log('[MCP Browser] Auto-connect starting...');

  const servers = await scanForServers();

  if (servers.length === 0) {
    console.log('[MCP Browser] No servers found');
    return;
  }

  // Connect to first server
  try {
    await connectionManager.connectToBackend(servers[0].port, servers[0]);
    console.log(`[MCP Browser] Connected to port ${servers[0].port}`);
  } catch (error) {
    console.error('[MCP Browser] Auto-connect failed:', error);
  }
}

/**
 * Handle messages from content scripts and popup
 */
browser.runtime.onMessage.addListener(async (request, sender) => {
  if (request.type === 'console_messages') {
    const tabs = await browser.tabs.query({ active: true, currentWindow: true });
    const activeTab = tabs[0];

    if (sender.tab && activeTab && sender.tab.id === activeTab.id) {
      const batchMessage = {
        type: 'batch',
        messages: request.messages,
        url: request.url,
        timestamp: request.timestamp,
        frameId: sender.frameId
      };

      await connectionManager.sendMessage(sender.tab.id, batchMessage);
    }

    return Promise.resolve({ received: true });
  }

  if (request.type === 'get_status') {
    const connections = connectionManager.getActiveConnections();
    return Promise.resolve({
      ...connectionStatus,
      multiConnection: true,
      connections: connections,
      totalConnections: connections.length
    });
  }

  if (request.type === 'get_connections') {
    return Promise.resolve({
      connections: connectionManager.getActiveConnections()
    });
  }

  if (request.type === 'scan_servers') {
    const servers = await scanForServers();
    return Promise.resolve({ servers: servers });
  }

  if (request.type === 'connect_to_server') {
    try {
      const connection = await connectionManager.connectToBackend(request.port, request.serverInfo);
      return Promise.resolve({
        success: true,
        connection: {
          port: connection.port,
          projectName: connection.projectName,
          projectPath: connection.projectPath
        }
      });
    } catch (error) {
      return Promise.resolve({ success: false, error: error.message });
    }
  }

  if (request.type === 'disconnect') {
    if (request.port) {
      await connectionManager.disconnectBackend(request.port);
    }
    return Promise.resolve({ received: true });
  }

  if (request.type === 'assign_tab_to_port') {
    connectionManager.assignTabToConnection(request.tabId, request.port);
    return Promise.resolve({ success: true });
  }

  if (request.type === 'get_pending_tabs') {
    const pending = Array.from(connectionManager.pendingTabs.entries()).map(([tabId, info]) => ({
      tabId,
      ...info
    }));
    return Promise.resolve({ pendingTabs: pending });
  }

  return Promise.resolve({ received: false });
});

/**
 * Track tab removal
 */
browser.tabs.onRemoved.addListener((tabId) => {
  connectionManager.removeTab(tabId);

  if (connectionManager.pendingTabs.has(tabId)) {
    connectionManager.pendingTabs.delete(tabId);
  }
});

/**
 * Register tabs on update
 */
browser.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.url) {
    await connectionManager.registerTab(tabId, tab.url);
  }
});

/**
 * Register tabs on navigation
 */
browser.webNavigation.onCompleted.addListener(async (details) => {
  if (details.frameId === 0) {
    await connectionManager.registerTab(details.tabId, details.url);
  }
});

/**
 * Initialize extension
 */
async function initializeExtension() {
  console.log('[MCP Browser] Firefox extension initializing...');

  extensionState = 'starting';
  updateBadgeStatus();

  // Start auto-connect
  await autoConnect();

  // Set up periodic scanning
  scanInterval = setInterval(scanForServers, SCAN_INTERVAL_MS);
}

// Start extension
initializeExtension();
