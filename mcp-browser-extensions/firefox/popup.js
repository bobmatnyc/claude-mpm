/**
 * Firefox popup script for MCP Browser
 * Simplified dashboard for Firefox (Manifest V2)
 */

let refreshInterval = null;

/**
 * Load dashboard state
 */
async function loadDashboard() {
  try {
    const status = await sendMessage({ type: 'get_status' });
    const connectionsResponse = await sendMessage({ type: 'get_connections' });

    updateStatus(status);
    renderConnections(connectionsResponse?.connections || []);
  } catch (error) {
    console.error('[Popup] Failed to load dashboard:', error);
  }
}

/**
 * Update status indicators
 */
function updateStatus(status) {
  const statusIndicator = document.getElementById('status-indicator');
  const statusText = document.getElementById('status-text');
  const connectionCount = document.getElementById('connection-count');
  const messageCount = document.getElementById('message-count');

  if (!status) {
    statusIndicator.className = 'status-indicator disconnected';
    statusText.textContent = 'Error';
    connectionCount.textContent = '0';
    messageCount.textContent = '0';
    return;
  }

  const activeCount = status.totalConnections || 0;
  connectionCount.textContent = activeCount;
  messageCount.textContent = status.messageCount || '0';

  if (activeCount > 0) {
    statusIndicator.className = 'status-indicator connected';
    statusText.textContent = `Connected (${activeCount})`;
  } else {
    statusIndicator.className = 'status-indicator disconnected';
    statusText.textContent = 'No Connections';
  }
}

/**
 * Render connections list
 */
function renderConnections(connections) {
  const container = document.getElementById('connections-container');
  const list = document.getElementById('connections-list');

  if (!connections || connections.length === 0) {
    container.style.display = 'none';
    return;
  }

  container.style.display = 'block';
  list.innerHTML = '';

  connections.forEach(connection => {
    const card = document.createElement('div');
    card.className = 'connection-card';

    const header = document.createElement('div');
    header.className = 'connection-header';

    const project = document.createElement('span');
    project.className = 'connection-project';
    project.textContent = connection.projectName || `Port ${connection.port}`;

    const port = document.createElement('span');
    port.className = 'connection-port';
    port.textContent = `Port ${connection.port}`;

    header.appendChild(project);
    header.appendChild(port);
    card.appendChild(header);

    if (connection.projectPath) {
      const path = document.createElement('div');
      path.style.fontSize = '11px';
      path.style.opacity = '0.7';
      path.style.marginTop = '4px';
      path.textContent = connection.projectPath;
      card.appendChild(path);
    }

    list.appendChild(card);
  });
}

/**
 * Send message to background script
 */
function sendMessage(message) {
  return browser.runtime.sendMessage(message);
}

/**
 * Handle scan button
 */
async function handleScan() {
  const button = document.getElementById('scan-button');
  const originalText = button.textContent;

  try {
    button.disabled = true;
    button.textContent = '🔄 Scanning...';

    await sendMessage({ type: 'scan_servers' });
    await loadDashboard();

  } catch (error) {
    console.error('[Popup] Scan failed:', error);
  } finally {
    button.disabled = false;
    button.textContent = originalText;
  }
}

/**
 * Handle test button
 */
async function handleTest() {
  try {
    const tabs = await browser.tabs.query({ active: true, currentWindow: true });
    if (tabs[0]) {
      await browser.tabs.executeScript(tabs[0].id, {
        code: `
          console.log('[MCP Browser Test] Test message at', new Date().toISOString());
          console.info('[MCP Browser Test] Extension is working!');
          console.warn('[MCP Browser Test] This is a warning');
          console.error('[MCP Browser Test] This is an error (test only)');
        `
      });

      const button = document.getElementById('test-button');
      button.textContent = 'Messages Sent!';
      button.disabled = true;

      setTimeout(() => {
        button.textContent = 'Generate Test Message';
        button.disabled = false;
      }, 1500);
    }
  } catch (error) {
    console.error('[Popup] Test failed:', error);
  }
}

/**
 * Start auto-refresh
 */
function startAutoRefresh() {
  if (refreshInterval) {
    clearInterval(refreshInterval);
  }
  refreshInterval = setInterval(loadDashboard, 2000);
}

// Event listeners
document.getElementById('scan-button').addEventListener('click', handleScan);
document.getElementById('test-button').addEventListener('click', handleTest);

// Cleanup
window.addEventListener('unload', () => {
  if (refreshInterval) {
    clearInterval(refreshInterval);
  }
});

// Initialize
loadDashboard();
startAutoRefresh();
