/**
 * Page Structure Component
 * Provides standardized page layout for all dashboard views
 * Includes header with title, connection status, and statistics
 */

export class PageStructure {
    constructor() {
        this.connectionStatus = false;
        this.startTime = Date.now();
        this.uptimeInterval = null;
    }

    /**
     * Create the standard page header structure
     * @param {Object} config - Configuration for the page
     * @param {string} config.title - Page title with emoji
     * @param {Array} config.stats - Statistics to display
     * @returns {string} HTML for the header
     */
    createHeader(config) {
        const { title, stats = [] } = config;

        return `
        <div class="header">
            <h1>${title}</h1>
            <div class="status-bar">
                <div class="status-indicator">
                    <span class="status-dot disconnected" id="connection-status"></span>
                    <span id="connection-text">Disconnected</span>
                </div>
                ${stats.map(stat => `
                    <div class="status-indicator">
                        <span>${stat.icon || ''}</span>
                        <span id="${stat.id}">${stat.defaultValue || '0'}</span>
                    </div>
                `).join('')}
            </div>
        </div>
        `;
    }

    /**
     * Create the statistics panel
     * @param {Array} cards - Statistics cards configuration
     * @returns {string} HTML for the statistics panel
     */
    createStatsPanel(cards) {
        return `
        <div class="stats-panel">
            ${cards.map(card => `
                <div class="stat-card">
                    <div class="stat-icon">${card.icon}</div>
                    <div class="stat-info">
                        <div class="stat-label">${card.label}</div>
                        <div class="stat-value" id="${card.id}">${card.defaultValue || '0'}</div>
                    </div>
                </div>
            `).join('')}
        </div>
        `;
    }

    /**
     * Create the controls panel
     * @param {Array} controls - Control elements configuration
     * @returns {string} HTML for the controls panel
     */
    createControlsPanel(controls = []) {
        if (controls.length === 0) return '';

        return `
        <div class="controls-panel">
            ${controls.map(control => {
                switch (control.type) {
                    case 'select':
                        return `
                            <div class="control-group">
                                <label class="control-label">${control.label}:</label>
                                <select id="${control.id}">
                                    ${control.options.map(opt =>
                                        `<option value="${opt.value}" ${opt.selected ? 'selected' : ''}>${opt.text}</option>`
                                    ).join('')}
                                </select>
                            </div>
                        `;
                    case 'input':
                        return `
                            <div class="control-group">
                                <input type="text" id="${control.id}" placeholder="${control.placeholder || ''}">
                            </div>
                        `;
                    case 'button':
                        return `
                            <button class="btn ${control.class || ''}" id="${control.id}">${control.text}</button>
                        `;
                    default:
                        return '';
                }
            }).join('')}
        </div>
        `;
    }

    /**
     * Apply standard page structure to a container
     * @param {string} containerId - ID of the container element
     * @param {Object} config - Page configuration
     */
    applyStructure(containerId, config) {
        const container = document.getElementById(containerId);
        if (!container) {
            console.error(`Container with ID "${containerId}" not found`);
            return;
        }

        // Create the complete structure
        const structure = `
            ${this.createHeader(config.header)}
            <div id="navigation-container"></div>
            ${config.statsPanel ? this.createStatsPanel(config.statsPanel) : ''}
            ${config.controls ? this.createControlsPanel(config.controls) : ''}
            <div class="main-panel">
                ${config.mainContent || '<div id="main-content"></div>'}
            </div>
        `;

        // Insert the structure
        container.innerHTML = structure;

        // Initialize connection status handlers
        this.initializeConnectionStatus();

        // Initialize uptime counter if needed
        if (config.header.stats && config.header.stats.some(s => s.id === 'uptime')) {
            this.startUptimeCounter();
        }
    }

    /**
     * Initialize connection status indicators
     */
    initializeConnectionStatus() {
        // This will be called by the socket manager when connection changes
        window.addEventListener('connection-status-changed', (event) => {
            this.updateConnectionStatus(event.detail.connected);
        });
    }

    /**
     * Update connection status display
     * @param {boolean} connected - Connection status
     */
    updateConnectionStatus(connected) {
        const statusDot = document.getElementById('connection-status');
        const statusText = document.getElementById('connection-text');

        if (statusDot && statusText) {
            this.connectionStatus = connected;
            statusDot.className = `status-dot ${connected ? 'connected' : 'disconnected'}`;
            statusText.textContent = connected ? 'Connected' : 'Disconnected';
        }
    }

    /**
     * Start the uptime counter
     */
    startUptimeCounter() {
        if (this.uptimeInterval) {
            clearInterval(this.uptimeInterval);
        }

        this.uptimeInterval = setInterval(() => {
            const uptime = Date.now() - this.startTime;
            const hours = Math.floor(uptime / 3600000);
            const minutes = Math.floor((uptime % 3600000) / 60000);
            const seconds = Math.floor((uptime % 60000) / 1000);

            const uptimeElement = document.getElementById('uptime');
            if (uptimeElement) {
                uptimeElement.textContent =
                    `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
            }
        }, 1000);
    }

    /**
     * Update a statistic value
     * @param {string} statId - ID of the statistic element
     * @param {string|number} value - New value
     */
    updateStat(statId, value) {
        const element = document.getElementById(statId);
        if (element) {
            element.textContent = value;
        }
    }

    /**
     * Update multiple statistics at once
     * @param {Object} stats - Object with stat IDs as keys and values as values
     */
    updateStats(stats) {
        Object.entries(stats).forEach(([id, value]) => {
            this.updateStat(id, value);
        });
    }

    /**
     * Clean up resources
     */
    destroy() {
        if (this.uptimeInterval) {
            clearInterval(this.uptimeInterval);
            this.uptimeInterval = null;
        }
    }
}

// Export default styles that should be applied to all pages
export const pageStyles = `
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }

    body {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        color: #e0e0e0;
        min-height: 100vh;
        padding: 20px;
    }

    .container {
        max-width: 1600px;
        margin: 0 auto;
    }

    .header {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 20px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }

    .header h1 {
        font-size: 24px;
        margin-bottom: 10px;
        background: linear-gradient(135deg, #10b981 0%, #06b6d4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .status-bar {
        display: flex;
        gap: 20px;
        align-items: center;
        flex-wrap: wrap;
    }

    .status-indicator {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 16px;
        background: rgba(255, 255, 255, 0.05);
        border-radius: 20px;
        font-size: 14px;
    }

    .status-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        animation: pulse 2s infinite;
    }

    .status-dot.connected {
        background: #4ade80;
        box-shadow: 0 0 10px #4ade80;
    }

    .status-dot.disconnected {
        background: #f87171;
        box-shadow: 0 0 10px #f87171;
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    .stats-panel {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 15px;
        margin-bottom: 20px;
    }

    .stat-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 15px;
        display: flex;
        align-items: center;
        gap: 15px;
    }

    .stat-icon {
        font-size: 24px;
        background: linear-gradient(135deg, #10b981 0%, #06b6d4 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .stat-info {
        flex: 1;
    }

    .stat-label {
        font-size: 12px;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .stat-value {
        font-size: 24px;
        font-weight: 600;
        color: #e0e0e0;
    }

    .controls-panel {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 20px;
        display: flex;
        gap: 15px;
        align-items: center;
        flex-wrap: wrap;
    }

    .control-group {
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .control-label {
        font-size: 14px;
        color: #94a3b8;
    }

    select, input[type="text"] {
        padding: 8px 12px;
        background: rgba(255, 255, 255, 0.1);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 6px;
        color: #e0e0e0;
        font-size: 14px;
    }

    select option {
        background: #1e293b;
    }

    .btn {
        padding: 8px 16px;
        background: linear-gradient(135deg, #10b981 0%, #06b6d4 100%);
        border: none;
        border-radius: 6px;
        color: white;
        cursor: pointer;
        font-size: 14px;
        font-weight: 500;
        transition: all 0.3s;
    }

    .btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(16, 185, 129, 0.3);
    }

    .btn.btn-secondary {
        background: rgba(255, 255, 255, 0.1);
    }

    .btn.btn-secondary:hover {
        background: rgba(255, 255, 255, 0.15);
    }

    .main-panel {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px;
        padding: 20px;
        min-height: 500px;
    }

    /* Scrollbar styling */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }

    ::-webkit-scrollbar-track {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.2);
        border-radius: 4px;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: rgba(255, 255, 255, 0.3);
    }
`;