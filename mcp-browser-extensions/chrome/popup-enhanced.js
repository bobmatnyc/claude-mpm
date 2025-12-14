/**
 * Simplified popup script for MCP Browser
 * Features:
 * - Overall server connection status
 * - Current tab connection status
 * - Auto-refresh dashboard
 * Version: 2.1.0 - Simplified Current Tab View
 */

let refreshInterval = null;

/**
 * Load dashboard state
 */
async function loadDashboard() {
  try {
    // Get overall status
    const status = await sendMessage({ type: 'get_status' });

    // Get current tab info
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    const currentTab = tabs[0];

    // Update UI
    updateOverallStatus(status);
    if (currentTab) {
      await updateCurrentTabStatus(currentTab.id);
    }

    // Update backend list
    await updateBackendList(status);

  } catch (error) {
    console.error('[Popup] Failed to load dashboard:', error);
    showError('Failed to load dashboard data');
  }
}

/**
 * Update overall server status indicators
 */
function updateOverallStatus(status) {
  const statusIndicator = document.getElementById('status-indicator');
  const statusText = document.getElementById('status-text');
  const messageCount = document.getElementById('message-count');

  if (!status) {
    statusIndicator.className = 'status-indicator disconnected';
    statusText.textContent = 'Error';
    messageCount.textContent = '0';
    return;
  }

  // Update server connection status
  const activeCount = status.totalConnections || 0;

  if (activeCount > 0) {
    statusIndicator.className = 'status-indicator connected';
    if (activeCount === 1) {
      statusText.textContent = 'Server Connected';
    } else {
      statusText.textContent = `${activeCount} Servers Connected`;
    }
  } else {
    statusIndicator.className = 'status-indicator disconnected';
    statusText.textContent = 'Server Disconnected';
  }

  // Update message count
  messageCount.textContent = status.messageCount || '0';

  // Clear error if connected
  if (activeCount > 0) {
    document.getElementById('error-container').innerHTML = '';
  } else if (status.lastError) {
    showError(status.lastError);
  }
}

/**
 * Update current tab connection status
 */
async function updateCurrentTabStatus(tabId) {
  const tabStatusIndicator = document.getElementById('tab-status-indicator');
  const tabStatusText = document.getElementById('tab-status-text');
  const tabInfoElement = document.getElementById('tab-info');

  try {
    // Get current tab info
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    const currentTab = tabs[0];

    // Get tab connections
    const tabConnectionsResponse = await sendMessage({ type: 'get_tab_connections' });
    const tabConnections = tabConnectionsResponse?.tabConnections || [];

    // Find current tab
    const currentTabConnection = tabConnections.find(tc => tc.tabId === tabId);

    if (currentTabConnection && currentTabConnection.assignedPort) {
      // Tab is connected - show project name if available
      tabStatusIndicator.className = 'status-indicator connected';
      const projectName = currentTabConnection.backendName || `Port ${currentTabConnection.assignedPort}`;
      tabStatusText.textContent = `Connected to ${projectName} (port ${currentTabConnection.assignedPort})`;

      // Show tab title/URL
      if (tabInfoElement && currentTab) {
        const tabTitle = currentTab.title || currentTab.url || 'Unknown';
        tabInfoElement.textContent = `Tab: ${tabTitle}`;
        tabInfoElement.style.display = 'block';
      }
    } else {
      // Tab is not connected
      tabStatusIndicator.className = 'status-indicator disconnected';
      tabStatusText.textContent = 'Not connected';

      // Hide tab info when not connected
      if (tabInfoElement) {
        tabInfoElement.style.display = 'none';
      }
    }
  } catch (error) {
    console.error('[Popup] Failed to get current tab status:', error);
    tabStatusIndicator.className = 'status-indicator disconnected';
    tabStatusText.textContent = 'Error';

    // Hide tab info on error
    if (tabInfoElement) {
      tabInfoElement.style.display = 'none';
    }
  }
}

/**
 * Update backend list display
 */
async function updateBackendList(status) {
  const backendListContainer = document.getElementById('backend-list-container');
  const backendList = document.getElementById('backend-list');

  // Get available servers from status
  const availableServers = status?.availableServers || [];

  // Get current tab to check if connected
  const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
  const currentTab = tabs[0];
  let isCurrentTabConnected = false;

  if (currentTab) {
    const tabConnectionsResponse = await sendMessage({ type: 'get_tab_connections' });
    const tabConnections = tabConnectionsResponse?.tabConnections || [];
    const currentTabConnection = tabConnections.find(tc => tc.tabId === currentTab.id);
    isCurrentTabConnected = currentTabConnection && currentTabConnection.assignedPort;
  }

  // Show backend list only if:
  // 1. There are available backends
  // 2. Current tab is not connected
  if (availableServers.length > 0 && !isCurrentTabConnected) {
    backendListContainer.style.display = 'block';

    // Clear any error message since we found servers
    document.getElementById('error-container').innerHTML = '';

    // Clear existing list
    backendList.innerHTML = '';

    // Render each backend
    console.log(`[Popup] Rendering ${availableServers.length} backends, currentTab:`, currentTab);
    availableServers.forEach(server => {
      const item = document.createElement('div');
      item.className = 'backend-item';

      item.innerHTML = `
        <div class="backend-info">
          <div class="backend-name">${server.projectName || 'Unknown Project'}</div>
          <div class="backend-port">Port ${server.port}</div>
        </div>
        <button class="backend-connect-btn" data-port="${server.port}">Connect</button>
      `;

      // Add click handler to connect button
      const connectBtn = item.querySelector('.backend-connect-btn');
      const tabIdToUse = currentTab?.id;
      console.log(`[Popup] Adding click handler for port ${server.port}, tabId: ${tabIdToUse}`);

      connectBtn.addEventListener('click', async (e) => {
        e.preventDefault();
        console.log(`[Popup] Connect button clicked for port ${server.port}, tabId: ${tabIdToUse}`);
        if (!tabIdToUse) {
          console.error('[Popup] No tab ID available!');
          showError('No active tab found');
          return;
        }
        await handleConnectToBackend(server.port, tabIdToUse);
      });

      backendList.appendChild(item);
    });
  } else {
    // Hide backend list if connected or no backends available
    backendListContainer.style.display = 'none';
  }
}

/**
 * Handle connecting current tab to a specific backend
 */
async function handleConnectToBackend(port, tabId) {
  const connectBtn = document.querySelector(`.backend-connect-btn[data-port="${port}"]`);

  try {
    console.log(`[Popup] Connecting tab ${tabId} to backend on port ${port}`);

    if (!tabId) {
      throw new Error('No tab ID provided');
    }
    if (!port) {
      throw new Error('No port provided');
    }

    // Update button state
    if (connectBtn) {
      connectBtn.disabled = true;
      connectBtn.textContent = 'Connecting...';
    }

    // Assign tab to the selected port
    const response = await sendMessage({
      type: 'assign_tab_to_port',
      tabId: tabId,
      port: port
    });

    console.log(`[Popup] assign_tab_to_port response:`, response);

    if (response && response.success) {
      console.log(`[Popup] Successfully connected tab ${tabId} to port ${port}`);

      // Hide the backend list immediately
      const backendListContainer = document.getElementById('backend-list-container');
      if (backendListContainer) {
        backendListContainer.style.display = 'none';
      }

      // Update current tab status immediately
      const tabStatusIndicator = document.getElementById('tab-status-indicator');
      const tabStatusText = document.getElementById('tab-status-text');
      if (tabStatusIndicator && tabStatusText) {
        tabStatusIndicator.className = 'status-indicator connected';
        tabStatusText.textContent = `Connected to port ${port}`;
      }

      // Refresh dashboard to get full status
      await loadDashboard();
    } else {
      throw new Error(response?.error || 'Failed to connect');
    }

  } catch (error) {
    console.error('[Popup] Failed to connect to backend:', error);
    showError(`Failed to connect: ${error.message}`);

    // Re-enable button
    if (connectBtn) {
      connectBtn.disabled = false;
      connectBtn.textContent = 'Connect';
    }
  }
}


/**
 * Handle scan for backends
 */
async function handleScanBackends() {
  const scanButton = document.getElementById('scan-button');
  const originalText = scanButton.textContent;

  try {
    scanButton.disabled = true;
    scanButton.classList.add('scanning');
    scanButton.textContent = '🔄 Scanning...';

    console.log('[Popup] Starting server scan...');
    const response = await sendMessage({ type: 'scan_servers' });

    if (response && response.servers) {
      console.log(`[Popup] Found ${response.servers.length} servers:`, response.servers);
      if (response.servers.length > 0) {
        // Clear error container immediately
        document.getElementById('error-container').innerHTML = '';
      }
    } else {
      console.log('[Popup] Scan response:', response);
    }

    // Refresh dashboard after scan
    console.log('[Popup] Refreshing dashboard...');
    await loadDashboard();
    console.log('[Popup] Dashboard refreshed');

  } catch (error) {
    console.error('[Popup] Scan failed:', error);
    showError('Failed to scan for backends');
  } finally {
    scanButton.disabled = false;
    scanButton.classList.remove('scanning');
    scanButton.textContent = originalText;
  }
}

/**
 * Send message to background script with promise wrapper
 */
function sendMessage(message) {
  return new Promise((resolve, reject) => {
    chrome.runtime.sendMessage(message, (response) => {
      if (chrome.runtime.lastError) {
        reject(chrome.runtime.lastError);
      } else {
        resolve(response);
      }
    });
  });
}

/**
 * Show error message
 */
function showError(message) {
  const errorContainer = document.getElementById('error-container');
  errorContainer.innerHTML = `
    <div class="error-message">
      ${message}
    </div>
  `;

  // Auto-hide after 5 seconds
  setTimeout(() => {
    errorContainer.innerHTML = '';
  }, 5000);
}


/**
 * Start auto-refresh
 */
function startAutoRefresh() {
  if (refreshInterval) {
    clearInterval(refreshInterval);
  }

  refreshInterval = setInterval(() => {
    loadDashboard();
  }, 2000);
}

/**
 * Stop auto-refresh
 */
function stopAutoRefresh() {
  if (refreshInterval) {
    clearInterval(refreshInterval);
    refreshInterval = null;
  }
}

// Event Listeners
document.getElementById('scan-button').addEventListener('click', handleScanBackends);

document.getElementById('test-button').addEventListener('click', () => {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs[0]) {
      chrome.scripting.executeScript({
        target: { tabId: tabs[0].id },
        func: () => {
          console.log('[MCP Browser Test] Test message at', new Date().toISOString());
          console.info('[MCP Browser Test] Extension is working!');
          console.warn('[MCP Browser Test] This is a warning');
          console.error('[MCP Browser Test] This is an error (test only)');
        }
      }, () => {
        const button = document.getElementById('test-button');
        button.textContent = 'Messages Sent!';
        button.disabled = true;

        setTimeout(() => {
          button.textContent = 'Generate Test Message';
          button.disabled = false;
        }, 1500);
      });
    }
  });
});

// Cleanup on popup close
window.addEventListener('unload', () => {
  stopAutoRefresh();
});

// Initial load
loadDashboard();
startAutoRefresh();
