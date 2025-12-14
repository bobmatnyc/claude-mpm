/**
 * Popup script for status display (Safari-compatible)
 */

// Use cross-browser API
const browserAPI = typeof browser !== 'undefined' ? browser : chrome;

let sessionStartTime = Date.now();

// Update status display
function updateStatus() {
  browserAPI.runtime.sendMessage({ type: 'get_status' }, (response) => {
    console.log('Status response:', response); // Debug log

    // Handle Safari's response format
    if (browserAPI.runtime.lastError) {
      console.error('Error getting status:', browserAPI.runtime.lastError);
      document.getElementById('status-text').textContent = 'Extension Error';
      document.getElementById('status-indicator').className = 'status-indicator disconnected';
      return;
    }

    if (!response) {
      document.getElementById('status-text').textContent = 'Extension Error';
      document.getElementById('status-indicator').className = 'status-indicator disconnected';
      console.error('No response from background script');
      return;
    }

    const statusIndicator = document.getElementById('status-indicator');
    const statusText = document.getElementById('status-text');
    const portValue = document.getElementById('port-value');
    const portSelect = document.getElementById('port-select');
    const messageCount = document.getElementById('message-count');
    const errorContainer = document.getElementById('error-container');

    if (response.connected) {
      statusIndicator.className = 'status-indicator connected';
      statusText.textContent = 'Connected';
      portValue.textContent = response.port || '-';

      // Update port select to show current port
      if (response.port && portSelect.value === 'auto') {
        // Don't change if user manually selected a port
        portValue.textContent = `(${response.port})`;
      }

      messageCount.textContent = response.messageCount || '0';
      errorContainer.innerHTML = '';

      // Update session time
      if (response.connectionTime) {
        sessionStartTime = response.connectionTime;
      }
    } else {
      statusIndicator.className = 'status-indicator disconnected';
      statusText.textContent = 'Disconnected';
      portValue.textContent = '-';

      if (response.lastError) {
        errorContainer.innerHTML = `
          <div class="error-message">
            ${response.lastError}
          </div>
        `;
      }
    }
  });
}

// Update session timer
function updateSessionTime() {
  const sessionTime = document.getElementById('session-time');
  const elapsed = Math.floor((Date.now() - sessionStartTime) / 1000);

  if (elapsed < 60) {
    sessionTime.textContent = `${elapsed}s`;
  } else if (elapsed < 3600) {
    const minutes = Math.floor(elapsed / 60);
    const seconds = elapsed % 60;
    sessionTime.textContent = `${minutes}m ${seconds}s`;
  } else {
    const hours = Math.floor(elapsed / 3600);
    const minutes = Math.floor((elapsed % 3600) / 60);
    sessionTime.textContent = `${hours}h ${minutes}m`;
  }
}

// Reconnect button handler
document.getElementById('reconnect-button').addEventListener('click', () => {
  // Send reconnect message to background script
  browserAPI.runtime.sendMessage({ type: 'reconnect' });

  // Update button text temporarily
  const button = document.getElementById('reconnect-button');
  button.textContent = 'Reconnecting...';
  button.disabled = true;

  setTimeout(() => {
    button.textContent = 'Reconnect';
    button.disabled = false;
    updateStatus();
  }, 2000);
});

// Test button handler
document.getElementById('test-button').addEventListener('click', () => {
  // Send a test console message
  browserAPI.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (tabs[0]) {
      browserAPI.scripting.executeScript({
        target: { tabId: tabs[0].id },
        func: () => {
          console.log('[mcp-browser Safari Test] Test message generated at', new Date().toISOString());
          console.info('[mcp-browser Safari Test] Extension is working correctly!');
          console.warn('[mcp-browser Safari Test] This is a test warning');
        }
      }, () => {
        // Handle Safari's callback format
        if (browserAPI.runtime.lastError) {
          console.error('Error executing script:', browserAPI.runtime.lastError);
          return;
        }

        // Update button text temporarily
        const button = document.getElementById('test-button');
        button.textContent = 'Message Sent!';
        button.disabled = true;

        setTimeout(() => {
          button.textContent = 'Generate Test Message';
          button.disabled = false;
          updateStatus();
        }, 1500);
      });
    }
  });
});

// Port selection handler
document.getElementById('port-select').addEventListener('change', (e) => {
  const selectedPort = e.target.value;

  if (selectedPort === 'auto') {
    // Send auto-connect message
    browserAPI.runtime.sendMessage({ type: 'set_port_mode', mode: 'auto' });
  } else {
    // Send specific port message
    browserAPI.runtime.sendMessage({ type: 'connect_to_port', port: parseInt(selectedPort) });
  }

  // Update button text temporarily
  const portSelect = document.getElementById('port-select');
  portSelect.disabled = true;

  setTimeout(() => {
    portSelect.disabled = false;
    updateStatus();
  }, 2000);
});

// Update status on load
updateStatus();

// Update status periodically
setInterval(updateStatus, 2000);

// Update session time every second
setInterval(updateSessionTime, 1000);

console.log('[MCP Browser Safari] Popup script loaded');
