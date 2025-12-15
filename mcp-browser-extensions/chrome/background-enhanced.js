/**
 * Enhanced Service worker for MCP Browser extension
 * Features:
 * - Multi-server discovery
 * - Project identification
 * - Smart port selection
 * - Multi-connection manager (supports up to 10 simultaneous connections)
 * - Per-connection state management (heartbeat, queues, sequences)
 * - Tab-to-connection routing
 */

// Configuration
const PORT_RANGE = { start: 8851, end: 8899 };
// REMOVED: Automatic scanning disabled - scan only on user request
// const SCAN_INTERVAL_MINUTES = 0.5;

// Storage keys for persistence
const STORAGE_KEYS = {
  MESSAGE_QUEUE: 'mcp_message_queue',
  LAST_CONNECTED_PORT: 'mcp_last_connected_port',
  LAST_CONNECTED_PROJECT: 'mcp_last_connected_project',
  LAST_SEQUENCE: 'mcp_last_sequence',
  PORT_PROJECT_MAP: 'mcp_port_project_map',
  DOMAIN_PORT_MAP: 'mcp_domain_port_map',     // domain → port mapping
  URL_PATTERN_RULES: 'mcp_url_pattern_rules'  // URL patterns → port rules
};

// Max queue size to prevent storage bloat
const MAX_QUEUE_SIZE = 500;

// Status colors (kept for reference, now using icon states)
const STATUS_COLORS = {
  RED: '#DC3545',    // Not functional / Error
  YELLOW: '#FFC107', // Listening but not connected
  GREEN: '#4CAF50'   // Connected to server
};

/**
 * Set extension icon state based on connection status
 * Replaces badge-based status with colored icons
 * @param {string} state - Icon state: 'yellow' (inactive), 'green' (connected), or 'red' (error)
 * @param {string} titleText - Optional custom title text for the icon
 */
function setIconState(state, titleText) {
  const validStates = ['yellow', 'green', 'red'];
  if (!validStates.includes(state)) {
    console.error(`[MCP Browser] Invalid icon state: ${state}`);
    state = 'yellow'; // Default to yellow on invalid state
  }

  const iconPath = {
    16: `icons/icon16-${state}.png`,
    32: `icons/icon32-${state}.png`,
    48: `icons/icon48-${state}.png`,
    128: `icons/icon128-${state}.png`
  };

  chrome.action.setIcon({ path: iconPath });

  if (titleText) {
    chrome.action.setTitle({ title: titleText });
  }

  console.log(`[MCP Browser] Icon state changed to: ${state}${titleText ? ` (${titleText})` : ''}`);
}

// State management
let activeServers = new Map(); // port -> server info
let extensionState = 'starting'; // 'starting', 'scanning', 'idle', 'connected', 'error'

// Port to project mapping for faster reconnection
let portProjectMap = {}; // port -> { project_id, project_name, project_path, last_seen }

// Gap detection configuration
const GAP_DETECTION_ENABLED = true;
const MAX_GAP_SIZE = 50; // Max messages to request in gap recovery

// Heartbeat configuration
const HEARTBEAT_INTERVAL = 15000; // 15 seconds
const PONG_TIMEOUT = 10000; // 10 seconds (25s total before timeout)

// Exponential backoff configuration
const BASE_RECONNECT_DELAY = 1000;  // 1 second
const MAX_RECONNECT_DELAY = 30000;  // 30 seconds max

// Maximum simultaneous connections
const MAX_CONNECTIONS = 10;

// Active ports to content scripts for keepalive
const activePorts = new Map(); // tabId -> port

// LEGACY: Single connection fallback (deprecated)
let currentConnection = null;
let messageQueue = [];
let connectionReady = false;
let lastSequenceReceived = 0;
let pendingGapRecovery = false;
let outOfOrderBuffer = [];
let lastPongTime = Date.now();
let reconnectAttempts = 0;

// Connection status (LEGACY - maintained for backward compatibility)
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
 * PortSelector - Intelligent port selection with priority-based strategy
 * Handles smart backend selection for tabs using multiple heuristics
 */
class PortSelector {
  constructor(connectionManager) {
    this.connectionManager = connectionManager;
    this.mruPort = null;  // Most recently used port
    this.mruTimestamp = null;
  }

  /**
   * Select port for a tab using priority-based strategy
   * @param {number} tabId - Tab ID
   * @param {string} url - Tab URL
   * @returns {Promise<number|null>} Port number or null
   */
  async selectPort(tabId, url) {
    console.log(`[PortSelector] Selecting port for tab ${tabId}, URL: ${url}`);

    // Priority 1: Exact URL rule match (user-defined patterns)
    const ruleMatch = await this.matchUrlRules(url);
    if (ruleMatch && this.isBackendAlive(ruleMatch)) {
      console.log(`[PortSelector] P1: URL rule match -> port ${ruleMatch}`);
      return ruleMatch;
    }

    // Priority 2: Domain → backend cache
    const domainMatch = await this.matchDomainCache(url);
    if (domainMatch && this.isBackendAlive(domainMatch)) {
      console.log(`[PortSelector] P2: Domain cache match -> port ${domainMatch}`);
      return domainMatch;
    }

    // Priority 3: Project path heuristic (URL contains project name)
    const projectMatch = await this.matchProjectName(url);
    if (projectMatch && this.isBackendAlive(projectMatch)) {
      console.log(`[PortSelector] P3: Project name match -> port ${projectMatch}`);
      return projectMatch;
    }

    // Priority 4: Most recently used backend
    if (this.mruPort && this.isBackendAlive(this.mruPort)) {
      console.log(`[PortSelector] P4: MRU -> port ${this.mruPort}`);
      return this.mruPort;
    }

    // Priority 5: First available backend (from active connections)
    const firstActive = this.connectionManager.getFirstActivePort();
    if (firstActive) {
      console.log(`[PortSelector] P5: First active -> port ${firstActive}`);
      return firstActive;
    }

    // Priority 6: Full port scan REMOVED - user must manually scan
    // Only scan when user explicitly clicks "Scan for Backends"
    // const scanned = await this.scanForFirstAvailable();
    // if (scanned) {
    //   console.log(`[PortSelector] P6: Scan result -> port ${scanned}`);
    //   return scanned;
    // }

    console.log(`[PortSelector] No port found for tab ${tabId} - user must scan manually`);
    return null;
  }

  /**
   * Match URL against pattern rules
   * @param {string} url - URL to match
   * @returns {Promise<number|null>} Port number or null
   */
  async matchUrlRules(url) {
    for (const rule of this.connectionManager.urlPatternRules) {
      if (rule.pattern.test(url)) {
        console.log(`[PortSelector] URL ${url} matched pattern rule -> port ${rule.port}`);
        return rule.port;
      }
    }
    return null;
  }

  /**
   * Match URL against domain cache
   * @param {string} url - URL to match
   * @returns {Promise<number|null>} Port number or null
   */
  async matchDomainCache(url) {
    const hostname = this._extractHostname(url);
    if (!hostname) {
      return null;
    }

    // Check in-memory cache first
    if (this.connectionManager.domainPortMap[hostname]) {
      console.log(`[PortSelector] Domain ${hostname} found in cache -> port ${this.connectionManager.domainPortMap[hostname]}`);
      return this.connectionManager.domainPortMap[hostname];
    }

    // Load from storage
    try {
      const result = await chrome.storage.local.get(STORAGE_KEYS.DOMAIN_PORT_MAP);
      const storedMap = result[STORAGE_KEYS.DOMAIN_PORT_MAP] || {};
      this.connectionManager.domainPortMap = storedMap;
      return storedMap[hostname] || null;
    } catch (e) {
      console.error('[PortSelector] Failed to load domain-port map:', e);
      return null;
    }
  }

  /**
   * Match URL against project names (URL contains project name)
   * @param {string} url - URL to match
   * @returns {Promise<number|null>} Port number or null
   */
  async matchProjectName(url) {
    try {
      // Load port-project map from storage
      const result = await chrome.storage.local.get(STORAGE_KEYS.PORT_PROJECT_MAP);
      const projectMap = result[STORAGE_KEYS.PORT_PROJECT_MAP] || {};

      // Check if URL contains any project name
      for (const [port, projectInfo] of Object.entries(projectMap)) {
        const projectName = projectInfo.project_name || '';
        const projectPath = projectInfo.project_path || '';

        // Check if URL contains project name or path segment
        if (projectName && url.toLowerCase().includes(projectName.toLowerCase())) {
          console.log(`[PortSelector] URL contains project name "${projectName}" -> port ${port}`);
          return parseInt(port);
        }

        // Check if URL contains project path segment (last directory name)
        if (projectPath) {
          const pathSegment = projectPath.split('/').filter(s => s).pop();
          if (pathSegment && url.toLowerCase().includes(pathSegment.toLowerCase())) {
            console.log(`[PortSelector] URL contains project path segment "${pathSegment}" -> port ${port}`);
            return parseInt(port);
          }
        }
      }
    } catch (e) {
      console.error('[PortSelector] Failed to match project name:', e);
    }

    return null;
  }

  /**
   * Check if backend has an active connection
   * ONLY checks existing connections - does NOT probe ports
   * This prevents ERR_CONNECTION_REFUSED spam
   * @param {number} port - Port to check
   * @returns {boolean} True if we have an active connection
   */
  isBackendAlive(port) {
    // Only check existing connections - never probe ports
    const connection = this.connectionManager.connections.get(port);
    return !!(connection && connection.ws && connection.ws.readyState === WebSocket.OPEN);
  }

  /**
   * Scan port range for first available backend with active connection
   * Note: This only checks existing connections, does not probe ports
   * @returns {number|null} Port number or null
   */
  scanForFirstAvailable() {
    console.log(`[PortSelector] Checking active connections...`);

    for (let port = PORT_RANGE.start; port <= PORT_RANGE.end; port++) {
      if (this.isBackendAlive(port)) {
        console.log(`[PortSelector] Found active connection at port ${port}`);
        return port;
      }
    }

    return null;
  }

  /**
   * Update most recently used port
   * @param {number} port - Port that was used
   */
  updateMRU(port) {
    this.mruPort = port;
    this.mruTimestamp = Date.now();
    console.log(`[PortSelector] Updated MRU to port ${port}`);
  }

  /**
   * Extract hostname from URL
   * @private
   */
  _extractHostname(url) {
    try {
      const urlObj = new URL(url);
      return urlObj.hostname;
    } catch (e) {
      console.warn(`[PortSelector] Failed to extract hostname from ${url}:`, e);
      return null;
    }
  }
}

/**
 * ConnectionManager - Manages multiple simultaneous WebSocket connections
 * Supports N connections with per-connection state, heartbeat, and message queuing
 */
class ConnectionManager {
  constructor() {
    this.connections = new Map(); // port -> connection object
    this.tabConnections = new Map(); // tabId -> port
    this.primaryPort = null; // Currently active/primary connection for badge display
    this.pendingTabs = new Map(); // tabId → { url, awaitingAssignment }
    this.unroutedMessages = []; // Messages without a backend
    this.domainPortMap = {}; // domain → port (cached associations)
    this.urlPatternRules = []; // { pattern: RegExp, port: number }[]
    this.portSelector = new PortSelector(this); // Smart port selection
  }

  /**
   * Create or return existing connection for a port
   * @param {number} port - Port number to connect to
   * @param {Object} projectInfo - Optional project information
   * @returns {Promise<Object>} Connection object
   */
  async connectToBackend(port, projectInfo = null) {
    console.log(`[ConnectionManager] Connecting to port ${port}...`);

    // Check connection limit
    if (!this.connections.has(port) && this.connections.size >= MAX_CONNECTIONS) {
      throw new Error(`Maximum connections (${MAX_CONNECTIONS}) reached`);
    }

    // Return existing connection if already connected
    if (this.connections.has(port)) {
      const conn = this.connections.get(port);
      if (conn.ws && conn.ws.readyState === WebSocket.OPEN) {
        console.log(`[ConnectionManager] Reusing existing connection to port ${port}`);
        return conn;
      }
      // Clean up stale connection
      await this.disconnectBackend(port);
    }

    // Create new connection object
    const connection = {
      ws: null,
      port: port,
      projectId: projectInfo?.project_id || null,
      projectName: projectInfo?.project_name || projectInfo?.projectName || `Port ${port}`,
      projectPath: projectInfo?.project_path || projectInfo?.projectPath || '',
      tabs: new Set(),
      messageQueue: [],
      connectionReady: false,
      lastSequence: 0,
      reconnectAttempts: 0,
      heartbeatInterval: null,
      lastPongTime: Date.now(),
      pendingGapRecovery: false,
      outOfOrderBuffer: [],
      intentionallyClosed: false  // Flag to prevent reconnect on intentional close
    };

    try {
      // Create WebSocket
      const ws = new WebSocket(`ws://localhost:${port}`);
      connection.ws = ws;

      // Wait for connection to open
      await new Promise((resolve, reject) => {
        const timeout = setTimeout(() => {
          ws.close();
          reject(new Error(`Connection timeout for port ${port}`));
        }, 3000);

        ws.onopen = async () => {
          clearTimeout(timeout);
          console.log(`[ConnectionManager] WebSocket opened for port ${port}`);

          // CRITICAL: Set up message handler BEFORE sending any messages
          // This prevents race conditions where server responses arrive before handler is ready
          // NOTE: We only set up onmessage here, NOT onclose (that stays as the reject handler until fully connected)
          this._setupMessageHandler(connection);

          // Load last sequence from storage
          const storageKey = `mcp_last_sequence_${port}`;
          const result = await chrome.storage.local.get(storageKey);
          connection.lastSequence = result[storageKey] || 0;

          // Send connection_init handshake
          const initMessage = {
            type: 'connection_init',
            lastSequence: connection.lastSequence,
            extensionVersion: chrome.runtime.getManifest().version,
            capabilities: ['console_capture', 'dom_interaction']
          };

          try {
            ws.send(JSON.stringify(initMessage));
            console.log(`[ConnectionManager] Sent connection_init for port ${port} with lastSequence: ${connection.lastSequence}`);
          } catch (e) {
            console.error(`[ConnectionManager] Failed to send connection_init for port ${port}:`, e);
            reject(e);
            return;
          }

          resolve();
        };

        ws.onerror = (error) => {
          clearTimeout(timeout);
          console.error(`[ConnectionManager] Connection error for port ${port}:`, error);
          reject(error);
        };

        ws.onclose = () => {
          clearTimeout(timeout);
          reject(new Error(`Connection closed for port ${port}`));
        };
      });

      // Now set up the full handlers including reconnect logic (after promise resolved)
      this._setupCloseHandler(connection);

      // Store connection
      this.connections.set(port, connection);

      // Set as primary if it's the first connection
      if (!this.primaryPort) {
        this.primaryPort = port;
      }

      // Process any pending tabs waiting for assignment
      await this.processPendingTabs(port);

      console.log(`[ConnectionManager] Successfully connected to port ${port} (${connection.projectName})`);
      return connection;

    } catch (error) {
      console.error(`[ConnectionManager] Failed to connect to port ${port}:`, error);
      throw error;
    }
  }

  /**
   * Disconnect from a specific backend
   * @param {number} port - Port to disconnect from
   */
  async disconnectBackend(port) {
    console.log(`[ConnectionManager] Disconnecting from port ${port}...`);

    const connection = this.connections.get(port);
    if (!connection) {
      console.log(`[ConnectionManager] No connection found for port ${port}`);
      return;
    }

    // Mark as intentionally closed to prevent auto-reconnect
    connection.intentionallyClosed = true;

    // Stop heartbeat
    if (connection.heartbeatInterval) {
      clearInterval(connection.heartbeatInterval);
      connection.heartbeatInterval = null;
    }

    // Close WebSocket
    if (connection.ws) {
      try {
        connection.ws.close();
      } catch (e) {
        console.error(`[ConnectionManager] Error closing WebSocket for port ${port}:`, e);
      }
    }

    // Save last sequence
    const storageKey = `mcp_last_sequence_${port}`;
    await chrome.storage.local.set({ [storageKey]: connection.lastSequence });

    // Save message queue if not empty
    if (connection.messageQueue.length > 0) {
      const queueKey = `mcp_message_queue_${port}`;
      await chrome.storage.local.set({ [queueKey]: connection.messageQueue.slice(-MAX_QUEUE_SIZE) });
    }

    // Clean up storage keys to prevent memory leaks
    await chrome.storage.local.remove([
      `mcp_message_queue_${port}`,
      `mcp_last_sequence_${port}`
    ]);

    // Remove all tab associations
    for (const [tabId, tabPort] of this.tabConnections.entries()) {
      if (tabPort === port) {
        this.tabConnections.delete(tabId);
      }
    }

    // Remove connection
    this.connections.delete(port);

    // Update primary port if this was primary
    if (this.primaryPort === port) {
      const remainingPorts = Array.from(this.connections.keys());
      this.primaryPort = remainingPorts.length > 0 ? remainingPorts[0] : null;
    }

    console.log(`[ConnectionManager] Disconnected from port ${port}`);
  }

  /**
   * Get connection object for a specific tab
   * @param {number} tabId - Tab ID
   * @returns {Object|null} Connection object or null
   */
  getConnectionForTab(tabId) {
    const port = this.tabConnections.get(tabId);
    if (!port) {
      return null;
    }
    return this.connections.get(port) || null;
  }

  /**
   * Assign a tab to a specific connection
   * @param {number} tabId - Tab ID
   * @param {number} port - Port number
   */
  assignTabToConnection(tabId, port) {
    console.log(`[ConnectionManager] assignTabToConnection called: tabId=${tabId}, port=${port}`);
    console.log(`[ConnectionManager] Available connections:`, Array.from(this.connections.keys()));

    const connection = this.connections.get(port);
    if (!connection) {
      console.warn(`[ConnectionManager] Cannot assign tab ${tabId} to port ${port} - connection not found`);
      console.warn(`[ConnectionManager] tabConnections Map:`, Array.from(this.tabConnections.entries()));
      return false;
    }

    // Remove from previous connection if exists
    const previousPort = this.tabConnections.get(tabId);
    if (previousPort && previousPort !== port) {
      const prevConn = this.connections.get(previousPort);
      if (prevConn) {
        prevConn.tabs.delete(tabId);
      }
      console.log(`[ConnectionManager] Removed tab ${tabId} from previous port ${previousPort}`);
      // Note: We'll show the new border below, no need to hide here
    }

    // Assign to new connection
    connection.tabs.add(tabId);
    this.tabConnections.set(tabId, port);
    console.log(`[ConnectionManager] Assigned tab ${tabId} to port ${port}`);
    console.log(`[ConnectionManager] tabConnections Map after assignment:`, Array.from(this.tabConnections.entries()));

    // NOTE: Border is now shown only during command execution, not on connection
    // See executeCommandOnTab() for border flash logic

    // Update badge for the newly connected tab (if it's active)
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      if (tabs[0]?.id === tabId) {
        updateBadgeForTab(tabId);
      }
    });

    return true;
  }

  /**
   * Remove a tab from all connections
   * @param {number} tabId - Tab ID
   */
  removeTab(tabId) {
    const port = this.tabConnections.get(tabId);
    if (port) {
      const connection = this.connections.get(port);
      if (connection) {
        connection.tabs.delete(tabId);
        console.log(`[ConnectionManager] Removed tab ${tabId} from port ${port}`);
      }
      this.tabConnections.delete(tabId);

      // Hide control border when tab is disconnected
      this._sendTabMessage(tabId, { type: 'hide_control_border' });
    }
  }

  /**
   * Send message to a specific tab's content script
   * @param {number} tabId - Tab ID
   * @param {Object} message - Message to send
   * @private
   */
  _sendTabMessage(tabId, message) {
    chrome.tabs.sendMessage(tabId, message, (response) => {
      if (chrome.runtime.lastError) {
        // Tab might not be ready or doesn't exist - this is normal
        console.debug(`[ConnectionManager] Could not send message to tab ${tabId}:`, chrome.runtime.lastError.message);
      }
    });
  }

  /**
   * Send message through the connection associated with a tab
   * @param {number} tabId - Tab ID
   * @param {Object} message - Message to send
   * @returns {Promise<boolean>} Success status
   */
  async sendMessage(tabId, message) {
    const connection = this.getConnectionForTab(tabId);
    if (!connection) {
      console.warn(`[ConnectionManager] No connection found for tab ${tabId}, message queued`);
      return false;
    }

    return this._sendToConnection(connection, message);
  }

  /**
   * Broadcast message to all active connections
   * @param {Object} message - Message to send
   * @returns {Promise<number>} Number of successful sends
   */
  async broadcastToAll(message) {
    let successCount = 0;
    for (const connection of this.connections.values()) {
      const success = await this._sendToConnection(connection, message);
      if (success) successCount++;
    }
    console.log(`[ConnectionManager] Broadcast sent to ${successCount}/${this.connections.size} connections`);
    return successCount;
  }

  /**
   * Get list of active connections
   * @returns {Array} Array of connection info objects
   */
  getActiveConnections() {
    return Array.from(this.connections.values()).map(conn => ({
      port: conn.port,
      projectId: conn.projectId,
      projectName: conn.projectName,
      projectPath: conn.projectPath,
      tabCount: conn.tabs.size,
      queueSize: conn.messageQueue.length,
      ready: conn.connectionReady,
      isPrimary: conn.port === this.primaryPort
    }));
  }

  /**
   * Get first active port from connections
   * Used as fallback in port selection
   * @returns {number|null} Port number or null
   */
  getFirstActivePort() {
    for (const [port, conn] of this.connections) {
      if (conn.ws && conn.ws.readyState === WebSocket.OPEN) {
        return port;
      }
    }
    return null;
  }

  /**
   * Register a tab and find the appropriate backend for it
   * Uses PortSelector for intelligent port selection
   * @param {number} tabId - Tab ID
   * @param {string} url - Tab URL
   * @returns {Promise<boolean>} True if tab was assigned, false if pending
   */
  async registerTab(tabId, url) {
    console.log(`[ConnectionManager] Registering tab ${tabId} with URL: ${url}`);

    // Use PortSelector for intelligent port selection
    const selectedPort = await this.portSelector.selectPort(tabId, url);

    if (selectedPort) {
      // Ensure connection exists
      if (!this.connections.has(selectedPort)) {
        try {
          await this.connectToBackend(selectedPort);
        } catch (error) {
          console.error(`[ConnectionManager] Failed to connect to selected port ${selectedPort}:`, error);
          // Mark as pending if connection fails
          this.pendingTabs.set(tabId, { url, awaitingAssignment: true });
          this._updatePendingBadge();
          return false;
        }
      }

      // Assign tab to connection
      this.assignTabToConnection(tabId, selectedPort);

      // Cache domain → port association
      const hostname = this._extractHostname(url);
      if (hostname) {
        await this.cacheDomainPort(hostname, selectedPort);
      }

      // Update MRU
      this.portSelector.updateMRU(selectedPort);

      // Flush any unrouted messages
      await this.flushUnroutedMessages(tabId);

      this._updatePendingBadge();
      return true;
    }

    // No port found - mark as pending
    console.log(`[ConnectionManager] Tab ${tabId} marked as pending assignment (no port available)`);
    this.pendingTabs.set(tabId, { url, awaitingAssignment: true });
    this._updatePendingBadge();
    return false;
  }

  /**
   * Find backend port for a given URL using pattern rules
   * @param {string} url - URL to match
   * @returns {number|null} Port number or null
   */
  findBackendForUrl(url) {
    for (const rule of this.urlPatternRules) {
      if (rule.pattern.test(url)) {
        console.log(`[ConnectionManager] URL ${url} matched pattern rule -> port ${rule.port}`);
        return rule.port;
      }
    }
    return null;
  }

  /**
   * Get cached port for a domain
   * @param {string} domain - Domain name
   * @returns {Promise<number|null>} Port number or null
   */
  async getCachedPortForDomain(domain) {
    // Check in-memory cache first
    if (this.domainPortMap[domain]) {
      console.log(`[ConnectionManager] Domain ${domain} found in cache -> port ${this.domainPortMap[domain]}`);
      return this.domainPortMap[domain];
    }

    // Load from storage
    try {
      const result = await chrome.storage.local.get(STORAGE_KEYS.DOMAIN_PORT_MAP);
      const storedMap = result[STORAGE_KEYS.DOMAIN_PORT_MAP] || {};
      this.domainPortMap = storedMap;
      return storedMap[domain] || null;
    } catch (e) {
      console.error('[ConnectionManager] Failed to load domain-port map:', e);
      return null;
    }
  }

  /**
   * Cache domain → port mapping
   * @param {string} domain - Domain name
   * @param {number} port - Port number
   * @returns {Promise<void>}
   */
  async cacheDomainPort(domain, port) {
    console.log(`[ConnectionManager] Caching domain ${domain} -> port ${port}`);
    this.domainPortMap[domain] = port;

    try {
      await chrome.storage.local.set({
        [STORAGE_KEYS.DOMAIN_PORT_MAP]: this.domainPortMap
      });
    } catch (e) {
      console.error('[ConnectionManager] Failed to save domain-port map:', e);
    }
  }

  /**
   * Route a message to the appropriate backend for a tab
   * @param {number} tabId - Tab ID
   * @param {Object} message - Message to route
   * @returns {Promise<boolean>} Success status
   */
  async routeMessage(tabId, message) {
    const connection = this.getConnectionForTab(tabId);

    if (!connection) {
      console.warn(`[ConnectionManager] No connection for tab ${tabId}, queueing message`);
      this.unroutedMessages.push({ tabId, message, timestamp: Date.now() });

      // Enforce max size to prevent memory leak (1000 messages)
      if (this.unroutedMessages.length > 1000) {
        this.unroutedMessages = this.unroutedMessages.slice(-1000);
      }

      return false;
    }

    // Add routing metadata
    const enrichedMessage = {
      ...message,
      tabId: tabId,
      routedAt: Date.now()
    };

    return this._sendToConnection(connection, enrichedMessage);
  }

  /**
   * Process pending tabs once a connection is established
   * @param {number} port - Port that was just connected
   * @returns {Promise<void>}
   */
  async processPendingTabs(port) {
    if (this.pendingTabs.size === 0) {
      return;
    }

    console.log(`[ConnectionManager] Processing ${this.pendingTabs.size} pending tabs for port ${port}`);

    for (const [tabId, { url }] of this.pendingTabs.entries()) {
      // Try to register this tab again
      const assigned = await this.registerTab(tabId, url);
      if (assigned) {
        this.pendingTabs.delete(tabId);
      }
    }

    this._updatePendingBadge();
  }

  /**
   * Flush unrouted messages for a specific tab
   * @param {number} tabId - Tab ID
   * @returns {Promise<void>}
   */
  async flushUnroutedMessages(tabId) {
    const connection = this.getConnectionForTab(tabId);
    if (!connection) {
      return;
    }

    const messagesToFlush = this.unroutedMessages.filter(item => item.tabId === tabId);
    if (messagesToFlush.length === 0) {
      return;
    }

    console.log(`[ConnectionManager] Flushing ${messagesToFlush.length} unrouted messages for tab ${tabId}`);

    for (const { message } of messagesToFlush) {
      await this._sendToConnection(connection, message);
    }

    // Remove flushed messages
    this.unroutedMessages = this.unroutedMessages.filter(item => item.tabId !== tabId);
  }

  /**
   * Load URL pattern rules from storage
   * @returns {Promise<void>}
   */
  async loadUrlPatternRules() {
    try {
      const result = await chrome.storage.local.get(STORAGE_KEYS.URL_PATTERN_RULES);
      const rules = result[STORAGE_KEYS.URL_PATTERN_RULES] || [];

      // Convert stored patterns to RegExp objects
      this.urlPatternRules = rules.map(rule => ({
        pattern: new RegExp(rule.pattern),
        port: rule.port
      }));

      console.log(`[ConnectionManager] Loaded ${this.urlPatternRules.length} URL pattern rules`);
    } catch (e) {
      console.error('[ConnectionManager] Failed to load URL pattern rules:', e);
    }
  }

  /**
   * Save URL pattern rules to storage
   * @param {Array} rules - Array of { pattern: string, port: number }
   * @returns {Promise<void>}
   */
  async saveUrlPatternRules(rules) {
    try {
      // Store patterns as strings
      const storableRules = rules.map(rule => ({
        pattern: rule.pattern instanceof RegExp ? rule.pattern.source : rule.pattern,
        port: rule.port
      }));

      await chrome.storage.local.set({
        [STORAGE_KEYS.URL_PATTERN_RULES]: storableRules
      });

      // Update in-memory rules
      this.urlPatternRules = storableRules.map(rule => ({
        pattern: new RegExp(rule.pattern),
        port: rule.port
      }));

      console.log(`[ConnectionManager] Saved ${rules.length} URL pattern rules`);
    } catch (e) {
      console.error('[ConnectionManager] Failed to save URL pattern rules:', e);
    }
  }

  /**
   * Internal: Extract hostname from URL
   * @private
   */
  _extractHostname(url) {
    try {
      const urlObj = new URL(url);
      return urlObj.hostname;
    } catch (e) {
      console.warn(`[ConnectionManager] Failed to extract hostname from ${url}:`, e);
      return null;
    }
  }

  /**
   * Internal: Update icon to show pending tabs
   * @private
   */
  _updatePendingBadge() {
    if (this.pendingTabs.size > 0) {
      setIconState('yellow', `MCP Browser: ${this.pendingTabs.size} tab(s) awaiting assignment`);
    } else {
      // Restore normal icon state
      this._updateGlobalStatus();
    }
  }

  /**
   * Get total connection count for badge display
   * @returns {number} Number of active connections
   */
  getConnectionCount() {
    let activeCount = 0;
    for (const conn of this.connections.values()) {
      if (conn.ws && conn.ws.readyState === WebSocket.OPEN && conn.connectionReady) {
        activeCount++;
      }
    }
    return activeCount;
  }

  /**
   * Internal: Send message to a specific connection
   * @private
   */
  async _sendToConnection(connection, message) {
    if (connection.ws && connection.ws.readyState === WebSocket.OPEN && connection.connectionReady) {
      try {
        connection.ws.send(JSON.stringify(message));
        return true;
      } catch (e) {
        console.error(`[ConnectionManager] Failed to send message to port ${connection.port}:`, e);
        return false;
      }
    } else {
      // Queue message
      connection.messageQueue.push(message);
      if (connection.messageQueue.length > MAX_QUEUE_SIZE) {
        connection.messageQueue.shift();
      }
      // Persist queue
      const queueKey = `mcp_message_queue_${connection.port}`;
      await chrome.storage.local.set({ [queueKey]: connection.messageQueue.slice(-MAX_QUEUE_SIZE) });
      return false;
    }
  }

  /**
   * Internal: Set up message handler only for a connection
   * Called early in connection setup to receive connection_ack before promise resolves
   * @private
   */
  _setupMessageHandler(connection) {
    const { ws, port } = connection;

    ws.onmessage = async (event) => {
      try {
        const data = JSON.parse(event.data);

        // Handle connection_ack
        if (data.type === 'connection_ack') {
          console.log(`[ConnectionManager] Connection acknowledged for port ${port}`);
          connection.connectionReady = true;

          // Update project info if provided
          if (data.project_id) {
            connection.projectId = data.project_id;
            connection.projectName = data.project_name || connection.projectName;
            connection.projectPath = data.project_path || connection.projectPath;

            // Update port-project mapping
            await updatePortProjectMapping(port, {
              project_id: data.project_id,
              project_name: data.project_name,
              project_path: data.project_path
            });
          }

          // Handle replayed messages
          if (data.replay && Array.isArray(data.replay)) {
            console.log(`[ConnectionManager] Receiving ${data.replay.length} replayed messages for port ${port}`);
            for (const msg of data.replay) {
              if (msg.sequence !== undefined && msg.sequence > connection.lastSequence) {
                connection.lastSequence = msg.sequence;
              }
            }
          }

          // Update last sequence
          if (data.currentSequence !== undefined) {
            connection.lastSequence = data.currentSequence;
            const storageKey = `mcp_last_sequence_${port}`;
            await chrome.storage.local.set({ [storageKey]: connection.lastSequence });
          }

          // Start heartbeat
          this._startHeartbeat(connection);

          // Flush message queue
          await this._flushMessageQueue(connection);

          // Update badge to show connected state
          updateBadgeStatus();

          // Update status if this is primary connection
          if (this.primaryPort === port) {
            this._updateGlobalStatus();
          }

          return;
        }

        // Handle pong
        if (data.type === 'pong') {
          connection.lastPongTime = Date.now();
          console.log(`[ConnectionManager] Pong received from port ${port}`);
          return;
        }

        // Handle gap recovery
        if (data.type === 'gap_recovery_response') {
          console.log(`[ConnectionManager] Gap recovery response received for port ${port}`);
          connection.pendingGapRecovery = false;

          if (data.messages && Array.isArray(data.messages)) {
            for (const msg of data.messages) {
              if (msg.sequence !== undefined && msg.sequence > connection.lastSequence) {
                connection.lastSequence = msg.sequence;
              }
            }

            const storageKey = `mcp_last_sequence_${port}`;
            await chrome.storage.local.set({ [storageKey]: connection.lastSequence });

            this._processBufferedMessages(connection);
          }

          return;
        }

        // Handle sequenced messages
        if (data.sequence !== undefined) {
          const shouldProcess = this._checkSequenceGap(connection, data.sequence);
          if (!shouldProcess) {
            return;
          }
          connection.lastSequence = data.sequence;
        }

        // Handle regular server messages
        this._handleServerMessage(connection, data);

      } catch (error) {
        console.error(`[ConnectionManager] Failed to parse message from port ${port}:`, error);
      }
    };

    // Set up error handler
    ws.onerror = (error) => {
      console.error(`[ConnectionManager] WebSocket error for port ${port}:`, error);
    };
  }

  /**
   * Internal: Set up close handler with reconnect logic
   * Called AFTER connection promise resolves to not interfere with initial setup
   * @private
   */
  _setupCloseHandler(connection) {
    const { ws, port } = connection;

    ws.onclose = async () => {
      console.log(`[ConnectionManager] Connection closed for port ${port}, intentional: ${connection.intentionallyClosed}`);

      // Update badge to show disconnected state
      updateBadgeStatus();

      // Stop heartbeat
      if (connection.heartbeatInterval) {
        clearInterval(connection.heartbeatInterval);
        connection.heartbeatInterval = null;
      }

      // Save state
      const storageKey = `mcp_last_sequence_${port}`;
      await chrome.storage.local.set({ [storageKey]: connection.lastSequence });

      // Only reconnect if NOT intentionally closed
      if (connection.intentionallyClosed) {
        console.log(`[ConnectionManager] Connection was intentionally closed, not reconnecting`);
        this.connections.delete(port);
        this._updateGlobalStatus();
        return;
      }

      // Schedule reconnect with exponential backoff
      connection.reconnectAttempts++;
      const delay = this._calculateReconnectDelay(connection.reconnectAttempts);
      console.log(`[ConnectionManager] Scheduling reconnect for port ${port} in ${delay}ms (attempt ${connection.reconnectAttempts})`);

      setTimeout(async () => {
        try {
          // Remove old connection
          this.connections.delete(port);

          // Attempt reconnect
          await this.connectToBackend(port, {
            project_id: connection.projectId,
            project_name: connection.projectName,
            project_path: connection.projectPath
          });

          // Reassign tabs
          for (const tabId of connection.tabs) {
            this.assignTabToConnection(tabId, port);
          }

          // Update badge after successful reconnect
          console.log(`[ConnectionManager] Reconnect successful for port ${port}`);
          updateBadgeStatus();

        } catch (error) {
          console.error(`[ConnectionManager] Reconnect failed for port ${port}:`, error);
          // Update badge to show error/disconnected state
          updateBadgeStatus();
        }
      }, delay);

      // Update global status
      this._updateGlobalStatus();
    };
  }

  /**
   * Internal: Set up all WebSocket event handlers for a connection (legacy method for compatibility)
   * @private
   */
  _setupConnectionHandlers(connection) {
    this._setupMessageHandler(connection);
    this._setupCloseHandler(connection);
  }

  /**
   * Internal: Start heartbeat for a connection
   * @private
   */
  _startHeartbeat(connection) {
    if (connection.heartbeatInterval) {
      clearInterval(connection.heartbeatInterval);
    }

    console.log(`[ConnectionManager] Starting heartbeat for port ${connection.port}`);
    connection.heartbeatInterval = setInterval(() => {
      if (connection.ws && connection.ws.readyState === WebSocket.OPEN) {
        // Check for pong timeout
        const timeSinceLastPong = Date.now() - connection.lastPongTime;
        if (timeSinceLastPong > HEARTBEAT_INTERVAL + PONG_TIMEOUT) {
          console.warn(`[ConnectionManager] Heartbeat timeout for port ${connection.port} - no pong for ${timeSinceLastPong}ms`);
          connection.ws.close();
          return;
        }

        // Send heartbeat
        try {
          connection.ws.send(JSON.stringify({
            type: 'heartbeat',
            timestamp: Date.now()
          }));
          console.log(`[ConnectionManager] Heartbeat sent to port ${connection.port}`);
        } catch (e) {
          console.warn(`[ConnectionManager] Heartbeat failed for port ${connection.port}:`, e);
        }
      } else {
        clearInterval(connection.heartbeatInterval);
        connection.heartbeatInterval = null;
      }
    }, HEARTBEAT_INTERVAL);
  }

  /**
   * Internal: Flush message queue for a connection
   * @private
   */
  async _flushMessageQueue(connection) {
    if (!connection.ws || connection.ws.readyState !== WebSocket.OPEN) {
      return;
    }

    console.log(`[ConnectionManager] Flushing ${connection.messageQueue.length} queued messages for port ${connection.port}`);

    while (connection.messageQueue.length > 0) {
      const message = connection.messageQueue.shift();
      try {
        connection.ws.send(JSON.stringify(message));
      } catch (e) {
        console.error(`[ConnectionManager] Failed to send queued message to port ${connection.port}:`, e);
        connection.messageQueue.unshift(message);
        break;
      }
    }

    // Clear stored queue
    const queueKey = `mcp_message_queue_${connection.port}`;
    await chrome.storage.local.remove(queueKey);
  }

  /**
   * Internal: Check for sequence gaps
   * @private
   */
  _checkSequenceGap(connection, incomingSequence) {
    if (!GAP_DETECTION_ENABLED || incomingSequence === undefined) {
      return true;
    }

    const expectedSequence = connection.lastSequence + 1;

    if (incomingSequence === expectedSequence) {
      return true;
    }

    if (incomingSequence <= connection.lastSequence) {
      console.log(`[ConnectionManager] Duplicate message (seq ${incomingSequence}) for port ${connection.port}`);
      return false;
    }

    const gapSize = incomingSequence - expectedSequence;
    console.warn(`[ConnectionManager] Gap detected for port ${connection.port}: expected ${expectedSequence}, got ${incomingSequence} (gap: ${gapSize})`);

    if (gapSize > MAX_GAP_SIZE) {
      console.warn(`[ConnectionManager] Gap too large (${gapSize}) for port ${connection.port}, accepting and resetting`);
      return true;
    }

    if (!connection.pendingGapRecovery) {
      this._requestGapRecovery(connection, expectedSequence, incomingSequence - 1);
    }

    connection.outOfOrderBuffer.push({ sequence: incomingSequence });

    // Prevent unbounded growth - memory leak fix
    if (connection.outOfOrderBuffer.length > 100) {
      console.warn('[ConnectionManager] Out of order buffer too large, clearing');
      connection.outOfOrderBuffer = [];
      connection.pendingGapRecovery = false;
    }

    return false;
  }

  /**
   * Internal: Request gap recovery
   * @private
   */
  _requestGapRecovery(connection, fromSequence, toSequence) {
    if (!connection.ws || connection.ws.readyState !== WebSocket.OPEN) {
      return;
    }

    connection.pendingGapRecovery = true;
    console.log(`[ConnectionManager] Requesting gap recovery for port ${connection.port}: sequences ${fromSequence} to ${toSequence}`);

    try {
      connection.ws.send(JSON.stringify({
        type: 'gap_recovery',
        fromSequence: fromSequence,
        toSequence: toSequence
      }));
    } catch (e) {
      console.error(`[ConnectionManager] Failed to request gap recovery for port ${connection.port}:`, e);
      connection.pendingGapRecovery = false;
    }
  }

  /**
   * Internal: Process buffered messages
   * @private
   */
  _processBufferedMessages(connection) {
    if (connection.outOfOrderBuffer.length === 0) return;

    connection.outOfOrderBuffer.sort((a, b) => a.sequence - b.sequence);

    const stillBuffered = [];
    for (const item of connection.outOfOrderBuffer) {
      if (item.sequence === connection.lastSequence + 1) {
        connection.lastSequence = item.sequence;
      } else if (item.sequence > connection.lastSequence + 1) {
        stillBuffered.push(item);
      }
    }

    connection.outOfOrderBuffer = stillBuffered;
  }

  /**
   * Internal: Calculate reconnect delay with exponential backoff
   * @private
   */
  _calculateReconnectDelay(attempts) {
    const exponentialDelay = Math.min(
      BASE_RECONNECT_DELAY * Math.pow(2, attempts),
      MAX_RECONNECT_DELAY
    );

    const jitter = exponentialDelay * 0.25 * (Math.random() - 0.5);
    return Math.max(exponentialDelay + jitter, BASE_RECONNECT_DELAY);
  }

  /**
   * Internal: Handle server message
   * @private
   */
  _handleServerMessage(connection, data) {
    // Route to original handler with connection info
    handleServerMessage(data, connection);
  }

  /**
   * Internal: Update global connection status
   * @private
   */
  _updateGlobalStatus() {
    // Update legacy connectionStatus for backward compatibility
    const primaryConn = this.primaryPort ? this.connections.get(this.primaryPort) : null;

    // Count active connections for badge
    const activeConnections = this.getConnectionCount();

    if (primaryConn && primaryConn.connectionReady) {
      connectionStatus.connected = true;
      connectionStatus.port = primaryConn.port;
      connectionStatus.projectName = primaryConn.projectName;
      connectionStatus.projectPath = primaryConn.projectPath;
      connectionStatus.lastError = null;
      extensionState = 'connected';
    } else if (this.connections.size > 0) {
      // At least one connection exists
      const anyConn = Array.from(this.connections.values())[0];
      connectionStatus.connected = true;
      connectionStatus.port = anyConn.port;
      connectionStatus.projectName = anyConn.projectName;
      connectionStatus.projectPath = anyConn.projectPath;
      extensionState = 'connected';
    } else {
      connectionStatus.connected = false;
      connectionStatus.port = null;
      connectionStatus.projectName = null;
      connectionStatus.projectPath = null;
      extensionState = activeServers.size > 0 ? 'idle' : 'idle';
    }

    // Update icon with connection status - green when connected, yellow when idle, red on error
    if (activeConnections > 0) {
      setIconState('green', `MCP Browser: Connected (${activeConnections} connection${activeConnections > 1 ? 's' : ''})`);
    } else if (extensionState === 'error' || connectionStatus.lastError) {
      setIconState('red', `MCP Browser: Error - ${connectionStatus.lastError || 'Connection failed'}`);
    } else if (connectionStatus.availableServers.length > 0) {
      setIconState('yellow', 'MCP Browser: Server available, connecting...');
    } else {
      setIconState('yellow', 'MCP Browser: Scanning for servers...');
    }
  }
}

// Initialize ConnectionManager
const connectionManager = new ConnectionManager();

/**
 * Calculate reconnection delay with exponential backoff and jitter
 * @returns {number} Delay in milliseconds
 */
function calculateReconnectDelay() {
  // Exponential backoff: 1s, 2s, 4s, 8s, 16s, 30s (capped)
  const exponentialDelay = Math.min(
    BASE_RECONNECT_DELAY * Math.pow(2, reconnectAttempts),
    MAX_RECONNECT_DELAY
  );

  // Add jitter (±25%) to prevent thundering herd
  const jitter = exponentialDelay * 0.25 * (Math.random() - 0.5);
  const delay = Math.max(exponentialDelay + jitter, BASE_RECONNECT_DELAY);

  return delay;
}

/**
 * Check for sequence gaps and handle accordingly
 * @param {number} incomingSequence - The sequence number of the incoming message
 * @returns {boolean} - True if message should be processed immediately, false if buffered
 */
function checkSequenceGap(incomingSequence) {
  if (!GAP_DETECTION_ENABLED || incomingSequence === undefined) {
    return true; // Process immediately
  }

  const expectedSequence = lastSequenceReceived + 1;

  // Perfect order - process immediately
  if (incomingSequence === expectedSequence) {
    return true;
  }

  // Duplicate - skip
  if (incomingSequence <= lastSequenceReceived) {
    console.log(`[MCP Browser] Duplicate message (seq ${incomingSequence}), skipping`);
    return false;
  }

  // Gap detected - message arrived too early
  const gapSize = incomingSequence - expectedSequence;
  console.warn(`[MCP Browser] Gap detected: expected ${expectedSequence}, got ${incomingSequence} (gap: ${gapSize})`);

  // If gap is too large, just accept and move on (likely server restart)
  if (gapSize > MAX_GAP_SIZE) {
    console.warn(`[MCP Browser] Gap too large (${gapSize}), accepting and resetting sequence`);
    return true;
  }

  // Request gap recovery if not already pending
  if (!pendingGapRecovery) {
    requestGapRecovery(expectedSequence, incomingSequence - 1);
  }

  // Buffer this message for later processing
  outOfOrderBuffer.push({ sequence: incomingSequence, message: null }); // Will be set by caller

  // Prevent unbounded growth - memory leak fix
  if (outOfOrderBuffer.length > 100) {
    console.warn('[MCP Browser] Out of order buffer too large, clearing');
    outOfOrderBuffer = [];
    pendingGapRecovery = false;
  }

  return false;
}

/**
 * Request recovery of missed messages
 */
function requestGapRecovery(fromSequence, toSequence) {
  if (!currentConnection || currentConnection.readyState !== WebSocket.OPEN) {
    return;
  }

  pendingGapRecovery = true;
  console.log(`[MCP Browser] Requesting gap recovery: sequences ${fromSequence} to ${toSequence}`);

  try {
    currentConnection.send(JSON.stringify({
      type: 'gap_recovery',
      fromSequence: fromSequence,
      toSequence: toSequence
    }));
  } catch (e) {
    console.error('[MCP Browser] Failed to request gap recovery:', e);
    pendingGapRecovery = false;
  }
}

/**
 * Process messages that were buffered during gap recovery
 */
function processBufferedMessages() {
  if (outOfOrderBuffer.length === 0) return;

  // Sort by sequence
  outOfOrderBuffer.sort((a, b) => a.sequence - b.sequence);

  // Process messages that are now valid
  const stillBuffered = [];
  for (const item of outOfOrderBuffer) {
    if (item.sequence === lastSequenceReceived + 1) {
      lastSequenceReceived = item.sequence;
      console.log(`[MCP Browser] Processing buffered message seq ${item.sequence}`);
    } else if (item.sequence > lastSequenceReceived + 1) {
      stillBuffered.push(item);
    }
    // Skip if already processed (duplicate)
  }

  outOfOrderBuffer = stillBuffered;

  if (stillBuffered.length > 0) {
    console.log(`[MCP Browser] ${stillBuffered.length} messages still buffered`);
  }
}

/**
 * Handle keepalive port connections from content scripts.
 * Maintaining open ports prevents service worker termination.
 */
chrome.runtime.onConnect.addListener((port) => {
  if (port.name === 'keepalive') {
    const tabId = port.sender?.tab?.id;
    if (tabId) {
      console.log(`[MCP Browser] Keepalive port connected from tab ${tabId}`);
      activePorts.set(tabId, port);

      port.onDisconnect.addListener(() => {
        console.log(`[MCP Browser] Keepalive port disconnected from tab ${tabId}`);
        activePorts.delete(tabId);
      });

      // Optional: Send acknowledgment
      port.postMessage({ type: 'keepalive_ack' });
    }
  }
});

/**
 * Get count of active keepalive ports
 */
function getActivePortCount() {
  return activePorts.size;
}

/**
 * Chrome Alarms handler for persistent timers
 * Handles reconnection and heartbeat (automatic scanning REMOVED)
 */
chrome.alarms.onAlarm.addListener((alarm) => {
  console.log(`[MCP Browser] Alarm triggered: ${alarm.name}`);
  if (alarm.name === 'reconnect') {
    autoConnect();
  } else if (alarm.name === 'heartbeat') {
    sendHeartbeat();
  }
  // REMOVED: Automatic server scanning
  // } else if (alarm.name === 'serverScan') {
  //   scanForServers();
});

/**
 * Start heartbeat alarm to keep service worker alive during active connections
 */
function startHeartbeat() {
  console.log('[MCP Browser] Starting heartbeat alarm');
  chrome.alarms.create('heartbeat', {
    delayInMinutes: HEARTBEAT_INTERVAL / 60000,
    periodInMinutes: HEARTBEAT_INTERVAL / 60000
  });
}

/**
 * Stop heartbeat alarm
 */
function stopHeartbeat() {
  console.log('[MCP Browser] Stopping heartbeat alarm');
  chrome.alarms.clear('heartbeat');
}

/**
 * Send heartbeat and check for pong timeout
 */
function sendHeartbeat() {
  if (currentConnection && currentConnection.readyState === WebSocket.OPEN) {
    // Check if we received pong recently
    const timeSinceLastPong = Date.now() - lastPongTime;
    if (timeSinceLastPong > HEARTBEAT_INTERVAL + PONG_TIMEOUT) {
      console.warn(`[MCP Browser] Heartbeat timeout - no pong for ${timeSinceLastPong}ms, reconnecting`);
      // Close connection and trigger reconnect
      currentConnection.close();
      stopHeartbeat();

      // Calculate delay with backoff
      const delay = calculateReconnectDelay();
      reconnectAttempts++;
      console.log(`[MCP Browser] Scheduling reconnect in ${delay}ms (attempt ${reconnectAttempts})`);
      chrome.alarms.create('reconnect', { delayInMinutes: delay / 60000 });
      return;
    }

    // Send heartbeat with timestamp
    try {
      currentConnection.send(JSON.stringify({
        type: 'heartbeat',
        timestamp: Date.now()
      }));
      console.log('[MCP Browser] Heartbeat sent');
    } catch (e) {
      console.warn('[MCP Browser] Heartbeat failed:', e);
    }
  } else {
    // Stop heartbeat if connection is not open
    stopHeartbeat();
  }
}

/**
 * Save message queue to chrome.storage.local
 */
async function saveMessageQueue() {
  try {
    // Limit queue size before saving
    const queueToSave = messageQueue.slice(-MAX_QUEUE_SIZE);
    await chrome.storage.local.set({ [STORAGE_KEYS.MESSAGE_QUEUE]: queueToSave });
    console.log(`[MCP Browser] Queue saved: ${queueToSave.length} messages`);
  } catch (e) {
    console.error('[MCP Browser] Failed to save queue:', e);
  }
}

/**
 * Load message queue from chrome.storage.local
 */
async function loadMessageQueue() {
  try {
    const result = await chrome.storage.local.get(STORAGE_KEYS.MESSAGE_QUEUE);
    if (result[STORAGE_KEYS.MESSAGE_QUEUE]) {
      messageQueue = result[STORAGE_KEYS.MESSAGE_QUEUE];
      console.log(`[MCP Browser] Queue loaded: ${messageQueue.length} messages`);
    }
  } catch (e) {
    console.error('[MCP Browser] Failed to load queue:', e);
  }
}

/**
 * Clear message queue from storage after successful flush
 */
async function clearStoredQueue() {
  try {
    await chrome.storage.local.remove(STORAGE_KEYS.MESSAGE_QUEUE);
    console.log('[MCP Browser] Stored queue cleared');
  } catch (e) {
    console.error('[MCP Browser] Failed to clear stored queue:', e);
  }
}

/**
 * Save last connected server info for faster reconnection
 */
async function saveConnectionState(port, projectName) {
  try {
    await chrome.storage.local.set({
      [STORAGE_KEYS.LAST_CONNECTED_PORT]: port,
      [STORAGE_KEYS.LAST_CONNECTED_PROJECT]: projectName
    });
    console.log(`[MCP Browser] Connection state saved: port ${port}, project ${projectName}`);
  } catch (e) {
    console.error('[MCP Browser] Failed to save connection state:', e);
  }
}

/**
 * Load last connected server info
 */
async function loadConnectionState() {
  try {
    const result = await chrome.storage.local.get([
      STORAGE_KEYS.LAST_CONNECTED_PORT,
      STORAGE_KEYS.LAST_CONNECTED_PROJECT
    ]);
    return {
      port: result[STORAGE_KEYS.LAST_CONNECTED_PORT] || null,
      projectName: result[STORAGE_KEYS.LAST_CONNECTED_PROJECT] || null
    };
  } catch (e) {
    console.error('[MCP Browser] Failed to load connection state:', e);
    return { port: null, projectName: null };
  }
}

/**
 * Clear connection state (on intentional disconnect)
 */
async function clearConnectionState() {
  try {
    await chrome.storage.local.remove([
      STORAGE_KEYS.LAST_CONNECTED_PORT,
      STORAGE_KEYS.LAST_CONNECTED_PROJECT
    ]);
  } catch (e) {
    console.error('[MCP Browser] Failed to clear connection state:', e);
  }
}

/**
 * Load port-project mapping from storage
 */
async function loadPortProjectMap() {
  try {
    const result = await chrome.storage.local.get(STORAGE_KEYS.PORT_PROJECT_MAP);
    portProjectMap = result[STORAGE_KEYS.PORT_PROJECT_MAP] || {};
    console.log(`[MCP Browser] Loaded ${Object.keys(portProjectMap).length} port-project mappings`);
  } catch (e) {
    console.error('[MCP Browser] Failed to load port-project map:', e);
  }
}

/**
 * Save port-project mapping to storage
 */
async function savePortProjectMap() {
  try {
    await chrome.storage.local.set({ [STORAGE_KEYS.PORT_PROJECT_MAP]: portProjectMap });
  } catch (e) {
    console.error('[MCP Browser] Failed to save port-project map:', e);
  }
}

/**
 * Update port-project mapping from server info
 */
async function updatePortProjectMapping(port, serverInfo) {
  portProjectMap[port] = {
    project_id: serverInfo.project_id,
    project_name: serverInfo.project_name,
    project_path: serverInfo.project_path,
    last_seen: Date.now()
  };

  await savePortProjectMap();

  // Note: Icon state and tooltip are updated via updateBadgeForTab when tabs switch
  console.log(`[MCP Browser] Updated mapping: port ${port} → ${serverInfo.project_name || 'Unknown'}`);
}

/**
 * Update extension icon to reflect current status
 * Per-tab icon colors:
 * - GREEN: Current tab is connected to a backend
 * - YELLOW: Current tab is not connected (but backends available or scanning)
 * - RED: Error state
 */
function updateBadgeStatus() {
  // Get current active tab and update badge based on its connection status
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    const currentTab = tabs[0];
    updateBadgeForTab(currentTab?.id);
  });
}

/**
 * Update icon for a specific tab
 * @param {number} tabId - The tab ID to check connection status for
 */
function updateBadgeForTab(tabId) {
  if (extensionState === 'error') {
    // RED: Error state
    setIconState('red', 'MCP Browser: Error');
    return;
  }

  // Check if this tab is assigned to a backend
  const assignedPort = tabId ? connectionManager.tabConnections.get(tabId) : null;
  const connection = assignedPort ? connectionManager.connections.get(assignedPort) : null;
  // Tab is connected if it has an assigned port with an active WebSocket
  const isTabConnected = connection && connection.ws && connection.ws.readyState === WebSocket.OPEN;

  console.log(`[MCP Browser] updateBadgeForTab: tabId=${tabId}, assignedPort=${assignedPort}, isConnected=${isTabConnected}`);

  if (isTabConnected) {
    // GREEN: This tab is connected to a backend
    const projectName = connection.projectName || 'Unknown';
    setIconState('green', `MCP Browser: Connected to ${projectName}`);
  } else if (connectionManager.connections.size > 0 || connectionStatus.availableServers.length > 0) {
    // YELLOW: Backends available but this tab is not connected
    setIconState('yellow', 'MCP Browser: Backends available (tab not connected)');
  } else if (extensionState === 'scanning') {
    // YELLOW: Scanning for servers
    setIconState('yellow', 'MCP Browser: Scanning for servers...');
  } else {
    // YELLOW: Idle, no backends
    setIconState('yellow', 'MCP Browser: No backends available');
  }
}

// Listen for tab activation to update badge per-tab
chrome.tabs.onActivated.addListener((activeInfo) => {
  updateBadgeForTab(activeInfo.tabId);
});

// Listen for tab updates (URL changes) to update badge
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (changeInfo.status === 'complete' && tab.active) {
    updateBadgeForTab(tabId);
  }
});

/**
 * Scan all ports for running MCP Browser servers
 * @returns {Promise<Array>} Array of available servers
 */
async function scanForServers() {
  console.log(`[MCP Browser] Scanning ports ${PORT_RANGE.start}-${PORT_RANGE.end} for servers...`);
  extensionState = 'scanning';
  updateBadgeStatus();

  const servers = [];

  for (let port = PORT_RANGE.start; port <= PORT_RANGE.end; port++) {
    const serverInfo = await probePort(port);
    if (serverInfo) {
      servers.push(serverInfo);
      activeServers.set(port, serverInfo);
    }
  }

  connectionStatus.availableServers = servers;

  // Clear any previous error if servers found
  if (servers.length > 0) {
    connectionStatus.lastError = null;
  } else {
    connectionStatus.lastError = 'No servers found. Run "mcp-browser start" to start a server.';
  }

  extensionState = servers.length > 0 ? 'idle' : 'idle';
  updateBadgeStatus();

  console.log(`[MCP Browser] Found ${servers.length} active server(s):`, servers);
  return servers;
}

/**
 * Probe a single port for MCP Browser server
 * @param {number} port - Port to probe
 * @returns {Promise<Object|null>} Server info or null
 */
async function probePort(port) {
  return new Promise((resolve) => {
    let ws = null; // Declare ws in the proper scope
    let serverInfoRequested = false;

    const timeout = setTimeout(() => {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
      resolve(null);
    }, 2000); // Increased timeout to handle two-message protocol

    try {
      ws = new WebSocket(`ws://localhost:${port}`);

      ws.onopen = () => {
        console.log(`[MCP Browser] WebSocket opened for port ${port}`);
        // Don't send server_info immediately - wait for connection_ack first
        // The server sends connection_ack automatically on connect
      };

      // Handle incoming messages
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          // Handle connection_ack - server sends this first
          if (data.type === 'connection_ack') {
            // Now request server info
            if (!serverInfoRequested) {
              serverInfoRequested = true;
              ws.send(JSON.stringify({ type: 'server_info' }));
            }
            return;
          }

          // Handle server_info_response - this is what we're waiting for
          if (data.type === 'server_info_response') {
            clearTimeout(timeout);
            ws.close();
            // Only accept servers with valid project information
            if (data.project_name && data.project_name !== 'Unknown') {
              const serverInfo = {
                port: port,
                projectName: data.project_name,
                projectPath: data.project_path || '',
                version: data.version || '1.0.0',
                connected: false
              };

              // Update port-project mapping if identity is present
              if (data.project_id) {
                updatePortProjectMapping(port, data).catch(err => {
                  console.error('[MCP Browser] Failed to update port mapping:', err);
                });
              }

              resolve(serverInfo);
            } else {
              // Not a valid MCP Browser server
              ws.close();
              resolve(null);
            }
          }
        } catch (e) {
          // Not a valid response - ignore and wait for more messages
          console.warn(`[MCP Browser] Failed to parse message from port ${port}:`, e);
        }
      };

      ws.onerror = (error) => {
        console.warn(`[MCP Browser] WebSocket error for port ${port}:`, error);
        clearTimeout(timeout);
        resolve(null);
      };

      ws.onclose = (event) => {
        console.log(`[MCP Browser] WebSocket closed for port ${port}, code: ${event.code}`);
        clearTimeout(timeout);
      };
    } catch (error) {
      console.error(`[MCP Browser] Failed to create WebSocket for port ${port}:`, error);
      clearTimeout(timeout);
      resolve(null);
    }
  });
}

/**
 * Connect to a specific server
 * @param {number} port - Port to connect to
 * @param {Object} serverInfo - Optional server info
 * @returns {Promise<boolean>} Success status
 */
async function connectToServer(port, serverInfo = null, retryAttempt = 0) {
  const maxRetries = 3;
  const baseTimeout = 10000; // Increased from 5000ms to 10000ms for more robust handshake
  const retryDelay = Math.min(1000 * Math.pow(2, retryAttempt), 5000); // Exponential backoff: 1s, 2s, 4s

  console.log(`[MCP Browser] Connecting to server on port ${port}... (attempt ${retryAttempt + 1}/${maxRetries + 1})`);

  // Disconnect from current server if connected
  if (currentConnection) {
    currentConnection.close();
    currentConnection = null;
  }

  try {
    const ws = new WebSocket(`ws://localhost:${port}`);

    return new Promise((resolve) => {
      let ackReceived = false;

      const timeout = setTimeout(() => {
        if (ws && ws.readyState !== WebSocket.CLOSED) {
          console.log(`[MCP Browser] Connection timeout - ackReceived: ${ackReceived}, readyState: ${ws.readyState}`);
          ws.close();
        }

        // Retry with exponential backoff if attempts remain
        if (retryAttempt < maxRetries) {
          console.log(`[MCP Browser] Connection timeout, retrying in ${retryDelay}ms...`);
          setTimeout(async () => {
            const retryResult = await connectToServer(port, serverInfo, retryAttempt + 1);
            resolve(retryResult);
          }, retryDelay);
        } else {
          console.log(`[MCP Browser] Connection failed after ${maxRetries + 1} attempts`);
          resolve(false);
        }
      }, baseTimeout);

      ws.onopen = async () => {
        console.log('[MCP Browser] WebSocket opened, waiting for connection_ack...');
        currentConnection = ws;
        lastPongTime = Date.now();
        reconnectAttempts = 0;

        // Reset gap detection state
        pendingGapRecovery = false;
        outOfOrderBuffer = [];

        // Load last sequence from storage
        const result = await chrome.storage.local.get(STORAGE_KEYS.LAST_SEQUENCE);
        lastSequenceReceived = result[STORAGE_KEYS.LAST_SEQUENCE] || 0;

        // Send connection_init handshake
        const initMessage = {
          type: 'connection_init',
          lastSequence: lastSequenceReceived,
          extensionVersion: chrome.runtime.getManifest().version,
          capabilities: ['console_capture', 'dom_interaction']
        };

        try {
          currentConnection.send(JSON.stringify(initMessage));
          console.log(`[MCP Browser] Sent connection_init with lastSequence: ${lastSequenceReceived}`);
        } catch (e) {
          console.error('[MCP Browser] Failed to send connection_init:', e);
          clearTimeout(timeout);
          resolve(false);
          return;
        }

        // Set up temporary message handler to wait for connection_ack
        ws.onmessage = async (event) => {
          try {
            const data = JSON.parse(event.data);

            if (data.type === 'connection_ack') {
              ackReceived = true;
              clearTimeout(timeout);
              console.log('[MCP Browser] Connection acknowledged by server - connection established!');

              // Now set up the full WebSocket handlers
              setupWebSocketHandlers(ws);

              resolve(true);
            }
          } catch (error) {
            console.error('[MCP Browser] Failed to parse message during handshake:', error);
          }
        };
      };

      ws.onerror = (error) => {
        clearTimeout(timeout);
        connectionStatus.lastError = `Connection error on port ${port}`;
        extensionState = 'error';
        updateBadgeStatus();
        console.error(`[MCP Browser] Connection error:`, error);
        resolve(false);
      };

      ws.onclose = () => {
        clearTimeout(timeout);
        if (!ackReceived) {
          console.log('[MCP Browser] WebSocket closed before connection_ack received');
          resolve(false);
        }
      };
    });
  } catch (error) {
    console.error(`[MCP Browser] Failed to connect to port ${port}:`, error);
    return false;
  }
}

/**
 * Handle a replayed message from the server
 */
function handleReplayedMessage(message) {
  console.log(`[MCP Browser] Processing replayed message: ${message.type}`);
  // For now, just log - actual handling depends on message types
  // In the future, this could trigger UI updates or other actions

  // Update sequence if message has one
  if (message.sequence !== undefined && message.sequence > lastSequenceReceived) {
    lastSequenceReceived = message.sequence;
  }
}

/**
 * Set up WebSocket event handlers
 * @param {WebSocket} ws - WebSocket connection
 */
function setupWebSocketHandlers(ws) {
  ws.onmessage = async (event) => {
    try {
      const data = JSON.parse(event.data);

      // Handle connection_ack from server
      if (data.type === 'connection_ack') {
        console.log(`[MCP Browser] Connection acknowledged by server`);
        connectionReady = true;

        // Start heartbeat after handshake complete
        startHeartbeat();

        // Update connection status
        connectionStatus.connected = true;
        connectionStatus.port = ws.url.match(/:(\d+)/)?.[1] || connectionStatus.port;
        connectionStatus.connectionTime = Date.now();
        connectionStatus.lastError = null;
        extensionState = 'connected';
        updateBadgeStatus();

        // Update port-project mapping if identity is present
        if (data.project_id) {
          updatePortProjectMapping(connectionStatus.port, {
            project_id: data.project_id,
            project_name: data.project_name,
            project_path: data.project_path || connectionStatus.projectPath
          }).catch(err => {
            console.error('[MCP Browser] Failed to update port mapping:', err);
          });
        }

        // Handle replayed messages if any
        if (data.replay && Array.isArray(data.replay)) {
          console.log(`[MCP Browser] Receiving ${data.replay.length} replayed messages`);
          for (const msg of data.replay) {
            // Process replayed message
            handleReplayedMessage(msg);
          }
        }

        // Update last sequence if provided
        if (data.currentSequence !== undefined) {
          lastSequenceReceived = data.currentSequence;
          await chrome.storage.local.set({ [STORAGE_KEYS.LAST_SEQUENCE]: lastSequenceReceived });
        }

        // Now flush any queued messages
        await flushMessageQueue();

        return; // Don't process further
      }

      // Handle pong response
      if (data.type === 'pong') {
        lastPongTime = Date.now();
        console.log('[MCP Browser] Pong received');
        return; // Don't process further
      }

      // Handle gap recovery response
      if (data.type === 'gap_recovery_response') {
        console.log(`[MCP Browser] Gap recovery response received`);
        pendingGapRecovery = false;

        // Process recovered messages in order
        if (data.messages && Array.isArray(data.messages)) {
          console.log(`[MCP Browser] Processing ${data.messages.length} recovered messages`);
          for (const msg of data.messages) {
            if (msg.sequence !== undefined && msg.sequence > lastSequenceReceived) {
              lastSequenceReceived = msg.sequence;
              // Process the message content (if applicable)
            }
          }

          // Persist updated sequence
          chrome.storage.local.set({ [STORAGE_KEYS.LAST_SEQUENCE]: lastSequenceReceived });

          // Process any buffered out-of-order messages that are now valid
          processBufferedMessages();
        }

        return;
      }

      // Check for sequence gaps (before processing messages with sequences)
      if (data.sequence !== undefined) {
        const shouldProcess = checkSequenceGap(data.sequence);
        if (!shouldProcess) {
          // Message is buffered or duplicate, don't process further
          return;
        }
        // Update sequence tracking
        lastSequenceReceived = data.sequence;
      }

      handleServerMessage(data);
    } catch (error) {
      console.error('[MCP Browser] Failed to parse server message:', error);
    }
  };

  ws.onerror = (error) => {
    console.error('[MCP Browser] WebSocket error:', error);
    connectionStatus.lastError = 'WebSocket error';
    extensionState = 'error';
    updateBadgeStatus();
  };

  ws.onclose = async () => {
    console.log('[MCP Browser] Connection closed');

    // Reset connection state
    connectionReady = false;
    currentConnection = null;
    connectionStatus.connected = false;
    connectionStatus.port = null;
    connectionStatus.projectName = null;

    // Reset gap detection state
    pendingGapRecovery = false;
    outOfOrderBuffer = [];

    // Save last sequence before reconnect
    await chrome.storage.local.set({ [STORAGE_KEYS.LAST_SEQUENCE]: lastSequenceReceived });

    // Stop heartbeat when disconnected
    stopHeartbeat();

    // Update state - back to YELLOW (listening but not connected)
    extensionState = connectionStatus.availableServers.length > 0 ? 'idle' : 'idle';
    updateBadgeStatus();

    // Try to reconnect after a delay with exponential backoff
    const delay = calculateReconnectDelay();
    reconnectAttempts++;
    console.log(`[MCP Browser] Scheduling reconnect in ${delay}ms (attempt ${reconnectAttempts})`);
    chrome.alarms.create('reconnect', { delayInMinutes: delay / 60000 });
  };
}

/**
 * Try to connect to a specific port
 */
async function tryConnectToPort(port) {
  const serverInfo = await probePort(port);
  if (serverInfo) {
    const connected = await connectToServer(port);
    if (connected) {
      console.log(`[MCP Browser] Connected to port ${port}`);
      return true;
    }
  }
  return false;
}

/**
 * Auto-connect to the best available server
 * MODIFIED: Only tries known ports, NO automatic full port scan
 * User must click "Scan for Backends" button for full scan
 */
async function autoConnect() {
  try {
    console.log('[MCP Browser] Auto-connect starting (known ports only)...');

    // Load port mappings if not already loaded
    if (Object.keys(portProjectMap).length === 0) {
      await loadPortProjectMap();
    }

    // First, try to reconnect to last known server
    const { port: lastPort, projectName: lastProject } = await loadConnectionState();
    if (lastPort) {
      console.log(`[MCP Browser] Trying last connected port: ${lastPort}`);
      const connected = await tryConnectToPort(lastPort);
      if (connected) return;
    }

    // Second, try known project ports (from mapping)
    const knownPorts = Object.keys(portProjectMap).map(p => parseInt(p)).sort((a, b) => {
      // Sort by last_seen, most recent first
      return (portProjectMap[b]?.last_seen || 0) - (portProjectMap[a]?.last_seen || 0);
    });

    for (const port of knownPorts) {
      if (port !== lastPort) { // Don't retry lastPort
        console.log(`[MCP Browser] Trying known project port: ${port} (${portProjectMap[port]?.project_name})`);
        const connected = await tryConnectToPort(port);
        if (connected) return;
      }
    }

    // REMOVED: Automatic full port scan
    // User must explicitly click "Scan for Backends" button in popup
    // Don't show error message on startup - only after user scans and finds nothing
    console.log('[MCP Browser] No known servers available. User can click "Scan for Backends" in popup.');
    extensionState = 'idle';
    updateBadgeStatus();
  } catch (error) {
    console.error('[MCP Browser] Auto-connect failed:', error);
    extensionState = 'error';
    connectionStatus.lastError = error.message || 'Auto-connect failed';
    updateBadgeStatus();
  }
}

/**
 * Handle messages from server (browser control commands)
 * @param {Object} data - Message data
 * @param {Object} connection - Connection object that sent the message
 */
function handleServerMessage(data, connection = null) {
  console.log(`[MCP Browser] Handling server message:`, data.type);

  // Find tabs assigned to this connection
  let targetTabIds = [];

  if (connection) {
    // Get tabs assigned to this connection's port
    const port = connection.port;
    for (const [tabId, tabPort] of connectionManager.tabConnections.entries()) {
      if (tabPort === port) {
        targetTabIds.push(tabId);
      }
    }
    console.log(`[MCP Browser] Found ${targetTabIds.length} tab(s) assigned to port ${port}:`, targetTabIds);
  }

  // Fallback to active tab if no tabs assigned to this connection
  if (targetTabIds.length === 0) {
    console.warn(`[MCP Browser] No tabs assigned to connection (port ${connection?.port}), falling back to active tab`);
    chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
      const activeTab = tabs[0];
      if (!activeTab) {
        console.warn('[MCP Browser] No active tab found for command:', data.type);
        return;
      }
      await executeCommandOnTab(activeTab.id, data, connection);
    });
    return;
  }

  // Execute command on all assigned tabs
  for (const tabId of targetTabIds) {
    executeCommandOnTab(tabId, data, connection);
  }
}

/**
 * Execute a browser command on a specific tab
 * @param {number} tabId - Target tab ID
 * @param {Object} data - Command data
 * @param {Object} connection - Connection object to send responses
 */
async function executeCommandOnTab(tabId, data, connection = null) {
  console.log(`[MCP Browser] Executing command ${data.type} on tab ${tabId}`);

  // Verify tab exists
  try {
    await chrome.tabs.get(tabId);
  } catch (e) {
    console.error(`[MCP Browser] Tab ${tabId} not found:`, e);
    return;
  }

  // Show border flash for browser commands (not for passive commands like get_page_content or query_logs)
  const borderCommands = ['navigate', 'click', 'fill_field', 'scroll'];
  if (borderCommands.includes(data.type)) {
    chrome.tabs.sendMessage(tabId, { type: 'show_control_border' }, (response) => {
      if (chrome.runtime.lastError) {
        console.debug(`[MCP Browser] Could not show border on tab ${tabId}:`, chrome.runtime.lastError.message);
      }
    });
  }

    switch (data.type) {
      case 'navigate':
        // Navigate to a URL
        console.log(`[MCP Browser] Navigating to: ${data.url}`);
        chrome.tabs.update(tabId, { url: data.url });
        break;

      case 'click':
        // Click an element
        console.log(`[MCP Browser] Clicking: ${data.selector}`);
        try {
          await chrome.scripting.executeScript({
            target: { tabId: tabId },
            func: (selector) => {
              const element = document.querySelector(selector);
              if (element) {
                element.click();
                return { success: true };
              }
              return { success: false, error: 'Element not found' };
            },
            args: [data.selector]
          });
        } catch (e) {
          console.error('[MCP Browser] Click failed:', e);
        }
        break;

      case 'fill_field':
        // Fill a text field
        console.log(`[MCP Browser] Filling field: ${data.selector} with value`);
        try {
          await chrome.scripting.executeScript({
            target: { tabId: tabId },
            func: (selector, value) => {
              const element = document.querySelector(selector);
              if (element) {
                element.focus();
                element.value = value;
                // Trigger input event for React/Vue etc
                element.dispatchEvent(new Event('input', { bubbles: true }));
                element.dispatchEvent(new Event('change', { bubbles: true }));
                return { success: true };
              }
              return { success: false, error: 'Element not found' };
            },
            args: [data.selector, data.value]
          });
        } catch (e) {
          console.error('[MCP Browser] Fill field failed:', e);
        }
        break;

      case 'scroll':
        // Scroll the page
        console.log(`[MCP Browser] Scrolling:`, data);
        try {
          await chrome.scripting.executeScript({
            target: { tabId: tabId },
            func: (scrollData) => {
              if (scrollData.x !== undefined && scrollData.y !== undefined) {
                window.scrollTo(scrollData.x, scrollData.y);
              } else if (scrollData.direction === 'down') {
                window.scrollBy(0, 500);
              } else if (scrollData.direction === 'up') {
                window.scrollBy(0, -500);
              }
            },
            args: [data]
          });
        } catch (e) {
          console.error('[MCP Browser] Scroll failed:', e);
        }
        break;

      case 'get_page_content':
        // Get page content
        console.log(`[MCP Browser] Getting page content`);
        try {
          const results = await chrome.scripting.executeScript({
            target: { tabId: tabId },
            func: () => {
              return {
                title: document.title,
                url: window.location.href,
                html: document.documentElement.outerHTML,
                text: document.body.innerText
              };
            }
          });
          // Send back to server if needed
          console.log('[MCP Browser] Page content retrieved');
        } catch (e) {
          console.error('[MCP Browser] Get page content failed:', e);
        }
        break;

      case 'extract_content':
        // Extract readable content using Readability
        console.log(`[MCP Browser] Extracting readable content for request ${data.requestId}`);
        try {
          // Load Readability library
          await chrome.scripting.executeScript({
            target: { tabId: tabId },
            files: ['Readability.js']
          });

          // Execute extraction
          const contentResults = await chrome.scripting.executeScript({
            target: { tabId: tabId },
            func: () => {
              try {
                // Clone document for Readability
                const documentClone = document.cloneNode(true);
                const reader = new Readability(documentClone);
                const article = reader.parse();

                if (article) {
                  return {
                    success: true,
                    content: {
                      title: article.title,
                      byline: article.byline,
                      excerpt: article.excerpt,
                      content: article.textContent,
                      htmlContent: article.content,
                      length: article.length,
                      siteName: article.siteName
                    },
                    url: window.location.href,
                    timestamp: new Date().toISOString()
                  };
                } else {
                  return {
                    success: false,
                    error: 'Could not extract readable content from this page'
                  };
                }
              } catch (error) {
                return {
                  success: false,
                  error: `Extraction failed: ${error.message}`
                };
              }
            }
          });

          const extractionResult = contentResults[0].result;

          // Send result back to server with requestId
          const response = {
            type: 'content_extracted',
            requestId: data.requestId,
            response: extractionResult
          };

          // Send to server via connection
          if (connection && connection.ws && connection.ws.readyState === WebSocket.OPEN) {
            connection.ws.send(JSON.stringify(response));
            console.log(`[MCP Browser] Sent content_extracted response for request ${data.requestId}`);
          } else {
            console.error(`[MCP Browser] No active connection to send response for request ${data.requestId}`);
          }
        } catch (e) {
          console.error('[MCP Browser] Content extraction failed:', e);
          // Send error response
          const errorResponse = {
            type: 'content_extracted',
            requestId: data.requestId,
            response: {
              success: false,
              error: e.message
            }
          };
          if (connection && connection.ws && connection.ws.readyState === WebSocket.OPEN) {
            connection.ws.send(JSON.stringify(errorResponse));
          }
        }
        break;

      case 'extract_semantic_dom':
        console.log(`[MCP Browser] Extracting semantic DOM for request ${data.requestId}`);
        try {
          const options = data.options || {};
          const maxTextLength = options.max_text_length || 100;

          const semanticResults = await chrome.scripting.executeScript({
            target: { tabId: tabId },
            func: (opts) => {
              const maxLen = opts.max_text_length || 100;
              const result = {
                url: window.location.href,
                title: document.title,
                headings: [],
                landmarks: [],
                links: [],
                forms: [],
              };

              // Extract headings (h1-h6)
              if (opts.include_headings !== false) {
                document.querySelectorAll('h1, h2, h3, h4, h5, h6').forEach(heading => {
                  const text = heading.textContent?.trim() || '';
                  if (text) {
                    result.headings.push({
                      level: parseInt(heading.tagName[1]),
                      text: text.substring(0, maxLen),
                      id: heading.id || null,
                    });
                  }
                });
              }

              // Extract ARIA landmarks and HTML5 sectioning elements
              if (opts.include_landmarks !== false) {
                const landmarkRoles = ['banner', 'navigation', 'main', 'complementary', 'contentinfo', 'search', 'region', 'form'];
                const seen = new Set();

                // ARIA role landmarks
                landmarkRoles.forEach(role => {
                  document.querySelectorAll(`[role="${role}"]`).forEach(el => {
                    const key = `${role}-${el.id || el.getAttribute('aria-label') || ''}`;
                    if (!seen.has(key)) {
                      seen.add(key);
                      result.landmarks.push({
                        role: role,
                        label: el.getAttribute('aria-label') || el.getAttribute('aria-labelledby') || null,
                        id: el.id || null,
                      });
                    }
                  });
                });

                // Native HTML5 landmarks (only if no role attribute)
                const nativeMapping = {
                  'header': 'banner',
                  'nav': 'navigation',
                  'main': 'main',
                  'aside': 'complementary',
                  'footer': 'contentinfo',
                };

                Object.entries(nativeMapping).forEach(([tag, role]) => {
                  document.querySelectorAll(tag).forEach(el => {
                    if (!el.getAttribute('role')) {
                      const key = `${role}-${el.id || el.getAttribute('aria-label') || tag}`;
                      if (!seen.has(key)) {
                        seen.add(key);
                        result.landmarks.push({
                          role: role,
                          label: el.getAttribute('aria-label') || null,
                          id: el.id || null,
                          tag: tag,
                        });
                      }
                    }
                  });
                });
              }

              // Extract links
              if (opts.include_links !== false) {
                document.querySelectorAll('a[href]').forEach(link => {
                  const text = link.textContent?.trim() || '';
                  const ariaLabel = link.getAttribute('aria-label') || '';
                  // Skip empty links and javascript: links
                  if ((text || ariaLabel) && !link.href.startsWith('javascript:')) {
                    result.links.push({
                      href: link.href,
                      text: text.substring(0, maxLen),
                      ariaLabel: ariaLabel || null,
                    });
                  }
                });
              }

              // Extract forms
              if (opts.include_forms !== false) {
                document.querySelectorAll('form').forEach(form => {
                  const fields = [];
                  form.querySelectorAll('input, textarea, select, button[type="submit"]').forEach(field => {
                    // Skip hidden fields
                    if (field.type === 'hidden') return;

                    // Get label text
                    let labelText = null;
                    if (field.labels && field.labels.length > 0) {
                      labelText = field.labels[0].textContent?.trim().substring(0, maxLen);
                    }

                    fields.push({
                      type: field.type || field.tagName.toLowerCase(),
                      name: field.name || null,
                      id: field.id || null,
                      label: labelText,
                      ariaLabel: field.getAttribute('aria-label') || null,
                      placeholder: field.placeholder || null,
                      required: field.required || false,
                    });
                  });

                  if (fields.length > 0) {
                    result.forms.push({
                      id: form.id || null,
                      name: form.name || null,
                      action: form.action || null,
                      method: form.method || 'get',
                      ariaLabel: form.getAttribute('aria-label') || null,
                      fields: fields,
                    });
                  }
                });
              }

              return { success: true, dom: result };
            },
            args: [options]
          });

          const extractionResult = semanticResults[0]?.result || { success: false, error: 'No result from page' };

          const response = {
            type: 'semantic_dom_extracted',
            requestId: data.requestId,
            response: extractionResult
          };

          if (connection && connection.ws && connection.ws.readyState === WebSocket.OPEN) {
            connection.ws.send(JSON.stringify(response));
            console.log(`[MCP Browser] Sent semantic_dom_extracted response`);
          }
        } catch (e) {
          console.error('[MCP Browser] Semantic DOM extraction failed:', e);
          const errorResponse = {
            type: 'semantic_dom_extracted',
            requestId: data.requestId,
            response: { success: false, error: e.message }
          };
          if (connection && connection.ws && connection.ws.readyState === WebSocket.OPEN) {
            connection.ws.send(JSON.stringify(errorResponse));
          }
        }
        break;

      case 'query_logs':
        // Query console logs - this would need to be implemented in content script
        console.log(`[MCP Browser] Query logs requested`);
        break;

      default:
        console.log(`[MCP Browser] Unknown message type: ${data.type}`);
  }

  // Hide border after command completes (2000ms delay for visibility)
  if (borderCommands.includes(data.type)) {
    setTimeout(() => {
      chrome.tabs.sendMessage(tabId, { type: 'hide_control_border' }, (response) => {
        if (chrome.runtime.lastError) {
          console.debug(`[MCP Browser] Could not hide border on tab ${tabId}:`, chrome.runtime.lastError.message);
        }
      });
    }, 2000);
  }
}

/**
 * Send message to server
 * @param {Object} message - Message to send
 * @returns {Promise<boolean>} Success status
 */
async function sendToServer(message) {
  if (currentConnection && currentConnection.readyState === WebSocket.OPEN && connectionReady) {
    // Connection is open AND handshake is complete
    currentConnection.send(JSON.stringify(message));
    connectionStatus.messageCount++;
    return true;
  } else {
    // Queue message if not connected or handshake not complete
    messageQueue.push(message);
    // Enforce max queue size
    if (messageQueue.length > MAX_QUEUE_SIZE) {
      messageQueue.shift();
    }
    // Persist queue to storage
    await saveMessageQueue();
    return false;
  }
}

/**
 * Flush queued messages
 */
async function flushMessageQueue() {
  if (!currentConnection || currentConnection.readyState !== WebSocket.OPEN) {
    return;
  }

  console.log(`[MCP Browser] Flushing ${messageQueue.length} queued messages`);

  while (messageQueue.length > 0) {
    const message = messageQueue.shift();
    try {
      currentConnection.send(JSON.stringify(message));
      connectionStatus.messageCount++;
    } catch (e) {
      console.error('[MCP Browser] Failed to send queued message:', e);
      // Put message back and stop flushing
      messageQueue.unshift(message);
      await saveMessageQueue();
      return;
    }
  }

  // Clear stored queue after successful flush
  await clearStoredQueue();
  console.log('[MCP Browser] Queue flush complete');
}

/**
 * Clean up ports when tabs are closed
 */
chrome.tabs.onRemoved.addListener((tabId) => {
  if (activePorts.has(tabId)) {
    console.log(`[MCP Browser] Tab ${tabId} closed, removing port`);
    activePorts.delete(tabId);
  }

  // Remove tab from ConnectionManager
  connectionManager.removeTab(tabId);

  // Remove unrouted messages for closed tab - memory leak fix
  connectionManager.unroutedMessages = connectionManager.unroutedMessages.filter(item => item.tabId !== tabId);

  // Remove from pending tabs
  if (connectionManager.pendingTabs.has(tabId)) {
    connectionManager.pendingTabs.delete(tabId);
    connectionManager._updatePendingBadge();
  }
});

/**
 * Auto-registration disabled - tabs must be explicitly connected via popup
 *
 * Previously this automatically registered ALL tabs when they loaded,
 * causing unwanted tabs to be connected to the backend.
 *
 * Users now must click "Connect" in the popup to connect specific tabs.
 */
// chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
//   if (changeInfo.status === 'complete' && tab.url) {
//     connectionManager.registerTab(tabId, tab.url).catch(err => {
//       console.error(`[MCP Browser] Failed to register tab ${tabId}:`, err);
//     });
//   }
// });

/**
 * Auto-registration on SPA navigation disabled
 *
 * Previously this automatically registered tabs on every SPA navigation,
 * causing unwanted tabs to be connected to the backend.
 *
 * Users now must click "Connect" in the popup to connect specific tabs.
 */
// chrome.webNavigation.onHistoryStateUpdated.addListener((details) => {
//   if (details.frameId === 0) { // Main frame only
//     connectionManager.registerTab(details.tabId, details.url).catch(err => {
//       console.error(`[MCP Browser] Failed to register tab ${details.tabId} on navigation:`, err);
//     });
//   }
// });

// Handle messages from popup and content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'console_messages') {
    // Process messages from ALL tabs (not just active tab)
    (async () => {
      if (sender.tab) {
        // Batch console messages
        const batchMessage = {
          type: 'batch',
          messages: request.messages,
          url: request.url,
          timestamp: request.timestamp,
          frameId: sender.frameId
        };

        // Use ConnectionManager's routeMessage for intelligent routing
        const sent = await connectionManager.routeMessage(sender.tab.id, batchMessage);
        if (!sent) {
          console.log(`[MCP Browser] Message queued for tab ${sender.tab.id} (no backend assigned)`);
        }
      }
    })();

    sendResponse({ received: true });
  } else if (request.type === 'get_status') {
    // Return enhanced status with all connections
    const connections = connectionManager.getActiveConnections();
    const enhancedStatus = {
      ...connectionStatus,
      multiConnection: true,
      connections: connections,
      totalConnections: connections.length
    };
    sendResponse(enhancedStatus);
  } else if (request.type === 'scan_servers') {
    // Scan for available servers
    scanForServers().then(servers => {
      sendResponse({ servers: servers });
    });
    return true; // Keep channel open for async response
  } else if (request.type === 'connect_to_server') {
    // Connect to specific server using ConnectionManager
    const { port, serverInfo } = request;
    connectionManager.connectToBackend(port, serverInfo).then(connection => {
      sendResponse({ success: true, connection: {
        port: connection.port,
        projectName: connection.projectName,
        projectPath: connection.projectPath
      }});
    }).catch(error => {
      console.error(`[MCP Browser] Failed to connect to port ${port}:`, error);
      sendResponse({ success: false, error: error.message });
    });
    return true; // Keep channel open for async response
  } else if (request.type === 'disconnect') {
    // Disconnect from specific server or all servers
    const { port } = request;
    if (port) {
      // Disconnect from specific port
      connectionManager.disconnectBackend(port).then(() => {
        sendResponse({ received: true, port: port });
      });
    } else {
      // Disconnect from all (legacy behavior + all ConnectionManager connections)
      if (currentConnection) {
        currentConnection.close();
        currentConnection = null;
      }
      // Disconnect all managed connections
      const ports = Array.from(connectionManager.connections.keys());
      Promise.all(ports.map(p => connectionManager.disconnectBackend(p))).then(() => {
        clearConnectionState();
        reconnectAttempts = 0;
        sendResponse({ received: true, disconnectedAll: true });
      });
    }
    return true; // Keep channel open for async response
  } else if (request.type === 'assign_tab_to_port') {
    // Assign a tab to a specific port/connection
    const { tabId, port } = request;
    (async () => {
      try {
        console.log(`[MCP Browser] Assigning tab ${tabId} to port ${port}`);

        // Ensure connection exists to the backend
        if (!connectionManager.connections.has(port)) {
          console.log(`[MCP Browser] No existing connection to port ${port}, creating new connection...`);

          // Attempt connection - connectToBackend handles errors gracefully
          console.log(`[MCP Browser] Connecting to backend on port ${port}...`);
          await connectionManager.connectToBackend(port);
          console.log(`[MCP Browser] Successfully connected to port ${port}`);
        } else {
          console.log(`[MCP Browser] Reusing existing connection to port ${port}`);
        }

        // Assign tab to connection
        connectionManager.assignTabToConnection(tabId, port);
        console.log(`[MCP Browser] Tab ${tabId} assigned to port ${port}`);

        // Get tab URL for domain caching
        try {
          const tab = await chrome.tabs.get(tabId);
          if (tab.url) {
            const hostname = connectionManager._extractHostname(tab.url);
            if (hostname) {
              await connectionManager.cacheDomainPort(hostname, port);
              console.log(`[MCP Browser] Cached domain mapping: ${hostname} -> port ${port}`);
            }
          }
        } catch (tabError) {
          console.warn(`[MCP Browser] Could not cache domain for tab ${tabId}:`, tabError);
          // Non-critical error - continue
        }

        // Update MRU
        connectionManager.portSelector.updateMRU(port);

        console.log(`[MCP Browser] Successfully completed assignment of tab ${tabId} to port ${port}`);
        sendResponse({ success: true });
      } catch (error) {
        console.error(`[MCP Browser] Failed to assign tab ${tabId} to port ${port}:`, error);
        sendResponse({ success: false, error: error.message });
      }
    })();
    return true; // Keep channel open for async response
  } else if (request.type === 'get_connections') {
    // Get list of all active connections
    const connections = connectionManager.getActiveConnections();
    sendResponse({ connections: connections });
  } else if (request.type === 'set_url_pattern_rules') {
    // Set URL pattern rules for routing
    const { rules } = request;
    connectionManager.saveUrlPatternRules(rules).then(() => {
      sendResponse({ success: true });
    }).catch(error => {
      sendResponse({ success: false, error: error.message });
    });
    return true; // Keep channel open for async response
  } else if (request.type === 'get_url_pattern_rules') {
    // Get current URL pattern rules
    sendResponse({
      rules: connectionManager.urlPatternRules.map(rule => ({
        pattern: rule.pattern.source,
        port: rule.port
      }))
    });
  } else if (request.type === 'clear_domain_cache') {
    // Clear domain → port cache
    connectionManager.domainPortMap = {};
    chrome.storage.local.remove(STORAGE_KEYS.DOMAIN_PORT_MAP).then(() => {
      sendResponse({ success: true });
    }).catch(error => {
      sendResponse({ success: false, error: error.message });
    });
    return true; // Keep channel open for async response
  } else if (request.type === 'get_pending_tabs') {
    // Get list of pending tabs
    const pending = Array.from(connectionManager.pendingTabs.entries()).map(([tabId, info]) => ({
      tabId,
      ...info
    }));
    sendResponse({ pendingTabs: pending });
  } else if (request.type === 'get_tab_connections') {
    // Get all tabs with their backend assignments
    console.log(`[MCP Browser] get_tab_connections called`);
    console.log(`[MCP Browser] tabConnections Map:`, Array.from(connectionManager.tabConnections.entries()));
    console.log(`[MCP Browser] connections Map:`, Array.from(connectionManager.connections.keys()));

    chrome.tabs.query({}, async (tabs) => {
      const tabConnections = tabs
        .filter(tab => tab.url && !tab.url.startsWith('chrome://'))
        .map(tab => {
          const assignedPort = connectionManager.tabConnections.get(tab.id);
          const connection = assignedPort ? connectionManager.connections.get(assignedPort) : null;

          return {
            tabId: tab.id,
            title: tab.title || 'Untitled',
            url: tab.url,
            assignedPort: assignedPort || null,
            backendName: connection?.projectName || null,
            backendPath: connection?.projectPath || null,
            isConnected: connection?.connectionReady || false
          };
        });

      console.log(`[MCP Browser] Returning tabConnections:`, tabConnections.filter(tc => tc.assignedPort));
      sendResponse({ tabConnections });
    });
    return true; // Keep channel open for async response
  }
});

// Handle extension installation
chrome.runtime.onInstalled.addListener(async () => {
  console.log('[MCP Browser] Extension installed');

  // Set initial badge - YELLOW (starting state)
  extensionState = 'starting';
  updateBadgeStatus();

  // Load persisted message queue
  await loadMessageQueue();

  // Load port-project mappings
  await loadPortProjectMap();

  // Load URL pattern rules for routing
  await connectionManager.loadUrlPatternRules();

  // Inject content script into all existing tabs
  chrome.tabs.query({}, (tabs) => {
    tabs.forEach(tab => {
      if (tab.url && !tab.url.startsWith('chrome://')) {
        chrome.scripting.executeScript({
          target: { tabId: tab.id },
          files: ['content.js']
        }).catch(err => console.log('Failed to inject into tab:', tab.id, err));
      }
    });
  });

  // Start server scanning (one-time on installation)
  autoConnect();

  // REMOVED: Automatic periodic scanning
  // User must click "Scan for Backends" button in popup to scan
  // chrome.alarms.create('serverScan', {
  //   delayInMinutes: SCAN_INTERVAL_MINUTES,
  //   periodInMinutes: SCAN_INTERVAL_MINUTES
  // });
});

// Handle browser startup
chrome.runtime.onStartup.addListener(async () => {
  console.log('[MCP Browser] Browser started');

  // Load persisted message queue
  await loadMessageQueue();

  // Load port-project mappings
  await loadPortProjectMap();

  // Load URL pattern rules for routing
  await connectionManager.loadUrlPatternRules();

  autoConnect();

  // REMOVED: Automatic periodic scanning
  // User must click "Scan for Backends" button in popup to scan
  // chrome.alarms.create('serverScan', {
  //   delayInMinutes: SCAN_INTERVAL_MINUTES,
  //   periodInMinutes: SCAN_INTERVAL_MINUTES
  // });
});

// Initialize on load
try {
  extensionState = 'starting';
  updateBadgeStatus();

  // Delay initial scan slightly to ensure extension is fully loaded
  chrome.alarms.create('reconnect', { delayInMinutes: 100 / 60000 }); // ~100ms
} catch (error) {
  console.error('[MCP Browser] Initialization error:', error);
  extensionState = 'error';
  updateBadgeStatus();
}