/**
 * Session Manager Component
 * Handles session selection and management
 */

class SessionManager {
    constructor(socketClient) {
        this.socketClient = socketClient;
        this.sessions = new Map();
        this.currentSessionId = null;
        this.selectedSessionId = '';
        
        this.init();
    }

    /**
     * Initialize the session manager
     */
    init() {
        this.setupEventHandlers();
        this.setupSocketListeners();
        this.updateSessionSelect();
    }

    /**
     * Setup event handlers for UI controls
     */
    setupEventHandlers() {
        // Session selection dropdown
        const sessionSelect = document.getElementById('session-select');
        if (sessionSelect) {
            sessionSelect.addEventListener('change', (e) => {
                this.selectedSessionId = e.target.value;
                this.onSessionFilterChanged();
            });
        }

        // Refresh sessions button
        const refreshBtn = document.querySelector('button[onclick="refreshSessions()"]');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.refreshSessions();
            });
        }
    }

    /**
     * Setup socket event listeners
     */
    setupSocketListeners() {
        // Listen for socket event updates
        this.socketClient.onEventUpdate((events, sessions) => {
            this.sessions = sessions;
            this.updateSessionSelect();
        });

        // Listen for connection status changes
        document.addEventListener('socketConnectionStatus', (e) => {
            if (e.detail.type === 'connected') {
                // Request fresh session data when connected
                setTimeout(() => this.refreshSessions(), 1000);
            }
        });
    }

    /**
     * Update the session selection dropdown
     */
    updateSessionSelect() {
        const sessionSelect = document.getElementById('session-select');
        if (!sessionSelect) return;

        // Store current selection
        const currentSelection = sessionSelect.value;

        // Clear existing options except default ones
        sessionSelect.innerHTML = `
            <option value="">All Sessions</option>
            <option value="current">Current Session</option>
        `;

        // Add sessions from the sessions map
        if (this.sessions && this.sessions.size > 0) {
            const sortedSessions = Array.from(this.sessions.values())
                .sort((a, b) => new Date(b.lastActivity || b.startTime) - new Date(a.lastActivity || a.startTime));

            sortedSessions.forEach(session => {
                const option = document.createElement('option');
                option.value = session.id;
                
                // Format session display text
                const startTime = new Date(session.startTime || session.last_activity).toLocaleString();
                const eventCount = session.eventCount || session.event_count || 0;
                const isActive = session.id === this.currentSessionId;
                
                option.textContent = `${session.id.substring(0, 8)}... (${eventCount} events, ${startTime})${isActive ? ' [ACTIVE]' : ''}`;
                sessionSelect.appendChild(option);
            });
        }

        // Restore selection if it still exists
        if (currentSelection && Array.from(sessionSelect.options).some(opt => opt.value === currentSelection)) {
            sessionSelect.value = currentSelection;
        } else {
            this.selectedSessionId = sessionSelect.value;
        }
    }

    /**
     * Handle session filter change
     */
    onSessionFilterChanged() {
        // Notify event viewer about filter change
        const eventViewer = window.eventViewer;
        if (eventViewer) {
            eventViewer.setSessionFilter(this.selectedSessionId);
        }

        // Update footer information
        this.updateFooterInfo();

        // Dispatch custom event for other components
        document.dispatchEvent(new CustomEvent('sessionFilterChanged', {
            detail: { sessionId: this.selectedSessionId }
        }));
    }

    /**
     * Refresh sessions from server
     */
    refreshSessions() {
        if (this.socketClient && this.socketClient.getConnectionState().isConnected) {
            console.log('Refreshing sessions...');
            this.socketClient.requestStatus();
        } else {
            console.warn('Cannot refresh sessions: not connected to server');
        }
    }

    /**
     * Update footer information based on selected session
     */
    updateFooterInfo() {
        const footerSessionEl = document.getElementById('footer-session');
        const footerWorkingDirEl = document.getElementById('footer-working-dir');
        const footerGitBranchEl = document.getElementById('footer-git-branch');

        if (!footerSessionEl) return;

        let sessionInfo = 'All Sessions';
        let workingDir = '';
        let gitBranch = '';

        if (this.selectedSessionId === 'current') {
            sessionInfo = this.currentSessionId ? 
                `Current: ${this.currentSessionId.substring(0, 8)}...` : 
                'Current: None';
        } else if (this.selectedSessionId) {
            const session = this.sessions.get(this.selectedSessionId);
            if (session) {
                sessionInfo = `${this.selectedSessionId.substring(0, 8)}...`;
                workingDir = session.working_directory || session.workingDirectory || '';
                gitBranch = session.git_branch || session.gitBranch || '';
            }
        }

        footerSessionEl.textContent = sessionInfo;
        if (footerWorkingDirEl) footerWorkingDirEl.textContent = workingDir || 'Unknown';
        if (footerGitBranchEl) footerGitBranchEl.textContent = gitBranch || 'Unknown';
    }

    /**
     * Set current session ID (from server status)
     * @param {string} sessionId - Current session ID
     */
    setCurrentSessionId(sessionId) {
        this.currentSessionId = sessionId;
        this.updateSessionSelect();
        this.updateFooterInfo();
    }

    /**
     * Add or update a session
     * @param {Object} sessionData - Session data
     */
    addSession(sessionData) {
        if (!sessionData.id) return;
        
        const existingSession = this.sessions.get(sessionData.id);
        if (existingSession) {
            // Update existing session
            Object.assign(existingSession, sessionData);
        } else {
            // Add new session
            this.sessions.set(sessionData.id, {
                id: sessionData.id,
                startTime: sessionData.startTime || sessionData.start_time || new Date().toISOString(),
                lastActivity: sessionData.lastActivity || sessionData.last_activity || new Date().toISOString(),
                eventCount: sessionData.eventCount || sessionData.event_count || 0,
                working_directory: sessionData.working_directory || sessionData.workingDirectory || '',
                git_branch: sessionData.git_branch || sessionData.gitBranch || '',
                agent_type: sessionData.agent_type || sessionData.agentType || '',
                ...sessionData
            });
        }
        
        this.updateSessionSelect();
    }

    /**
     * Remove a session
     * @param {string} sessionId - Session ID to remove
     */
    removeSession(sessionId) {
        if (this.sessions.has(sessionId)) {
            this.sessions.delete(sessionId);
            
            // If the removed session was selected, reset to all sessions
            if (this.selectedSessionId === sessionId) {
                this.selectedSessionId = '';
                const sessionSelect = document.getElementById('session-select');
                if (sessionSelect) {
                    sessionSelect.value = '';
                }
                this.onSessionFilterChanged();
            }
            
            this.updateSessionSelect();
        }
    }

    /**
     * Get current session filter
     * @returns {string} Current session filter
     */
    getCurrentFilter() {
        return this.selectedSessionId;
    }

    /**
     * Get session information
     * @param {string} sessionId - Session ID
     * @returns {Object|null} Session data or null if not found
     */
    getSession(sessionId) {
        return this.sessions.get(sessionId) || null;
    }

    /**
     * Get all sessions
     * @returns {Map} All sessions
     */
    getAllSessions() {
        return this.sessions;
    }

    /**
     * Get current active session ID
     * @returns {string|null} Current session ID
     */
    getCurrentSessionId() {
        return this.currentSessionId;
    }

    /**
     * Clear all sessions
     */
    clearSessions() {
        this.sessions.clear();
        this.currentSessionId = null;
        this.selectedSessionId = '';
        this.updateSessionSelect();
        this.updateFooterInfo();
    }

    /**
     * Export session data
     * @returns {Object} Session export data
     */
    exportSessionData() {
        return {
            sessions: Array.from(this.sessions.entries()),
            currentSessionId: this.currentSessionId,
            selectedSessionId: this.selectedSessionId
        };
    }

    /**
     * Import session data
     * @param {Object} data - Session import data
     */
    importSessionData(data) {
        if (data.sessions && Array.isArray(data.sessions)) {
            this.sessions.clear();
            data.sessions.forEach(([id, sessionData]) => {
                this.sessions.set(id, sessionData);
            });
        }
        
        if (data.currentSessionId) {
            this.currentSessionId = data.currentSessionId;
        }
        
        if (data.selectedSessionId !== undefined) {
            this.selectedSessionId = data.selectedSessionId;
        }
        
        this.updateSessionSelect();
        this.updateFooterInfo();
    }
}

// Global functions for backward compatibility
window.refreshSessions = function() {
    if (window.sessionManager) {
        window.sessionManager.refreshSessions();
    }
};

// Export for global use
window.SessionManager = SessionManager;