/**
 * Build Tracker Component
 * 
 * WHY: Displays and manages version/build information for both MPM and Monitor UI,
 * providing users with clear visibility of the current system versions.
 * 
 * DESIGN DECISION: Implemented as a standalone component that can be easily
 * integrated into the dashboard header, with automatic updates from SocketIO.
 */

export class BuildTracker {
    constructor() {
        this.element = null;
        this.buildInfo = {
            monitor: {
                version: "1.0.0",
                build: 1,
                formatted_build: "0001",
                full_version: "v1.0.0-0001"
            },
            mpm: {
                version: "unknown",
                build: "unknown",
                full_version: "v0.0.0"
            }
        };
        
        // Socket client reference (will be set during initialization)
        this.socketClient = null;
        
        // Initialize the component
        this.init();
    }
    
    /**
     * Initialize the build tracker component
     */
    async init() {
        // Try to load version.json for dashboard version
        await this.loadDashboardVersion();
        
        this.createElements();
        this.setupEventListeners();
    }
    
    /**
     * Load dashboard version from version.json if available
     * 
     * WHY: Attempts to load the actual dashboard version from the 
     * version.json file created by the version management script.
     * Falls back to defaults if file is not available.
     */
    async loadDashboardVersion() {
        try {
            // Try to fetch version.json from the dashboard root
            const response = await fetch('/version.json');
            if (response.ok) {
                const versionData = await response.json();
                
                // Update monitor build info with loaded data
                this.buildInfo.monitor = {
                    version: versionData.version || "1.0.0",
                    build: versionData.build || 1,
                    formatted_build: versionData.formatted_build || "0001",
                    full_version: versionData.full_version || "v1.0.0-0001"
                };
                
                // Dashboard version loaded successfully
            }
        } catch (error) {
            // Silently fall back to defaults if version.json not available
        }
    }
    
    /**
     * Create the DOM elements for version display
     * 
     * WHY: Creates a clean, unobtrusive version display that fits
     * seamlessly into the dashboard header.
     */
    createElements() {
        // Create container element
        this.element = document.createElement('div');
        this.element.className = 'version-display';
        this.element.id = 'version-display';
        
        // Create MPM version element
        const mpmVersion = document.createElement('span');
        mpmVersion.className = 'version-item mpm-version';
        mpmVersion.id = 'mpm-version';
        mpmVersion.innerHTML = `
            <span class="version-label">MPM</span>
            <span class="version-value">v0.0.0</span>
        `;
        
        // Create separator
        const separator = document.createElement('span');
        separator.className = 'version-separator';
        separator.textContent = '|';
        
        // Create Monitor version element
        const monitorVersion = document.createElement('span');
        monitorVersion.className = 'version-item monitor-version';
        monitorVersion.id = 'monitor-version';
        monitorVersion.innerHTML = `
            <span class="version-label">Monitor</span>
            <span class="version-value">v1.0.0-0001</span>
        `;
        
        // Assemble elements
        this.element.appendChild(mpmVersion);
        this.element.appendChild(separator);
        this.element.appendChild(monitorVersion);
        
        // Add tooltip for detailed info
        this.element.title = 'Click for detailed version information';
    }
    
    /**
     * Set the socket client for receiving updates
     * 
     * @param {Object} socketClient - The Socket.IO client instance
     */
    setSocketClient(socketClient) {
        this.socketClient = socketClient;
        
        // Listen for build info updates
        if (this.socketClient && this.socketClient.socket) {
            // Listen for welcome message with build info
            this.socketClient.socket.on('welcome', (eventData) => {
                // Handle both old format (direct) and new schema (nested in data)
                const buildInfo = eventData.build_info || 
                                 (eventData.data && eventData.data.build_info);
                if (buildInfo) {
                    this.updateBuildInfo(buildInfo);
                }
            });
            
            // Listen for status updates with build info
            this.socketClient.socket.on('status', (eventData) => {
                // Handle both old format (direct) and new schema (nested in data)
                const buildInfo = eventData.build_info || 
                                 (eventData.data && eventData.data.build_info);
                if (buildInfo) {
                    this.updateBuildInfo(buildInfo);
                }
            });
            
            // Listen for explicit build info updates
            this.socketClient.socket.on('build_info', (data) => {
                this.updateBuildInfo(data);
            });
        }
    }
    
    /**
     * Update the build information
     * 
     * @param {Object} buildInfo - Build information from server
     */
    updateBuildInfo(buildInfo) {
        // Store the build info
        this.buildInfo = buildInfo;
        
        // Update display
        this.updateDisplay();
    }
    
    /**
     * Update the version display elements
     * 
     * WHY: Keeps the UI in sync with the latest version information
     * received from the server.
     */
    updateDisplay() {
        // Update MPM version
        const mpmElement = this.element.querySelector('.mpm-version .version-value');
        if (mpmElement && this.buildInfo.mpm) {
            const mpmVersion = this.buildInfo.mpm.full_version || 
                              `v${this.buildInfo.mpm.version}`;
            mpmElement.textContent = mpmVersion;
            
            // Add build number to tooltip if available
            if (this.buildInfo.mpm.build && this.buildInfo.mpm.build !== "unknown") {
                mpmElement.parentElement.title = `MPM Build: ${this.buildInfo.mpm.build}`;
            }
        }
        
        // Update Monitor version
        const monitorElement = this.element.querySelector('.monitor-version .version-value');
        if (monitorElement && this.buildInfo.monitor) {
            const monitorVersion = this.buildInfo.monitor.full_version || 
                                  `v${this.buildInfo.monitor.version}-${this.buildInfo.monitor.formatted_build}`;
            monitorElement.textContent = monitorVersion;
            
            // Add last updated to tooltip if available
            if (this.buildInfo.monitor.last_updated) {
                const lastUpdated = new Date(this.buildInfo.monitor.last_updated).toLocaleString();
                monitorElement.parentElement.title = `Monitor Build: ${this.buildInfo.monitor.formatted_build}\nLast Updated: ${lastUpdated}`;
            }
        }
    }
    
    /**
     * Setup event listeners
     * 
     * WHY: Allows users to interact with the version display for
     * additional information or actions.
     */
    setupEventListeners() {
        // Click handler for showing detailed version info
        this.element.addEventListener('click', () => {
            this.showDetailedInfo();
        });
    }
    
    /**
     * Show detailed version information in a modal or alert
     * 
     * WHY: Provides power users with detailed build and version
     * information for debugging and support purposes.
     */
    showDetailedInfo() {
        const info = [];
        
        // MPM information
        if (this.buildInfo.mpm) {
            info.push('=== MPM Framework ===');
            info.push(`Version: ${this.buildInfo.mpm.version}`);
            if (this.buildInfo.mpm.build && this.buildInfo.mpm.build !== "unknown") {
                info.push(`Build: ${this.buildInfo.mpm.build}`);
            }
            info.push(`Full: ${this.buildInfo.mpm.full_version}`);
        }
        
        info.push('');
        
        // Monitor information
        if (this.buildInfo.monitor) {
            info.push('=== Monitor UI ===');
            info.push(`Version: ${this.buildInfo.monitor.version}`);
            info.push(`Build: ${this.buildInfo.monitor.formatted_build} (${this.buildInfo.monitor.build})`);
            info.push(`Full: ${this.buildInfo.monitor.full_version}`);
            if (this.buildInfo.monitor.last_updated) {
                const lastUpdated = new Date(this.buildInfo.monitor.last_updated).toLocaleString();
                info.push(`Updated: ${lastUpdated}`);
            }
        }
        
        // Version information compiled
        
        // Create a simple modal-like display
        const modal = document.createElement('div');
        modal.className = 'version-modal';
        modal.innerHTML = `
            <div class="version-modal-content">
                <h3>Version Information</h3>
                <pre>${info.join('\n')}</pre>
                <button onclick="this.parentElement.parentElement.remove()">Close</button>
            </div>
        `;
        
        // Add to body
        document.body.appendChild(modal);
        
        // Auto-remove after 10 seconds
        setTimeout(() => {
            modal.remove();
        }, 10000);
    }
    
    /**
     * Mount the component to a parent element
     * 
     * @param {HTMLElement|string} parent - Parent element or selector
     */
    mount(parent) {
        const parentElement = typeof parent === 'string' 
            ? document.querySelector(parent) 
            : parent;
        
        if (!this.element) {
            return;
        }
        
        if (!parentElement) {
            return;
        }
        
        // Check if already mounted to prevent duplicates
        if (this.element.parentNode === parentElement) {
            return;
        }
        
        parentElement.appendChild(this.element);
    }
    
    /**
     * Get the component's DOM element
     * 
     * @returns {HTMLElement} The component's root element
     */
    getElement() {
        return this.element;
    }
    
    /**
     * Destroy the component and clean up
     */
    destroy() {
        if (this.element && this.element.parentNode) {
            this.element.parentNode.removeChild(this.element);
        }
        
        // Clean up socket listeners
        if (this.socketClient && this.socketClient.socket) {
            this.socketClient.socket.off('welcome');
            this.socketClient.socket.off('status');
            this.socketClient.socket.off('build_info');
        }
        
        this.element = null;
        this.socketClient = null;
    }
}