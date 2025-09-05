/**
 * Session Manager Component
 * Handles session selection and management
 * 
 * WHY: Provides session filtering and management for the dashboard, allowing users
 * to view events from specific sessions or all sessions.
 * 
 * BROWSER COMPATIBILITY: This component runs in the browser. All Node.js-specific
 * globals (process, require, etc.) have been removed. Uses browser-compatible
 * alternatives for path handling and defaults.
 * 
 * FIX APPLIED: Removed process.cwd() reference that caused "process is not defined"
 * error in browser. Now uses window.location.pathname or hardcoded fallbacks.
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

                // Load working directory for this session
                if (window.dashboard && window.dashboard.loadWorkingDirectoryForSession) {
                    window.dashboard.loadWorkingDirectoryForSession(e.target.value);
                }
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
            // Log the sessions data to debug
            console.log('[SESSION-MANAGER] Received sessions update:', sessions);
            this.sessions = sessions;
            this.updateSessionSelect();
            // Update footer info when new events arrive
            this.updateFooterInfo();
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

        // Get the default working directory from various sources
        let defaultWorkingDir = '/';
        
        // Try to get from working directory manager
        if (window.dashboard && window.dashboard.workingDirectoryManager) {
            defaultWorkingDir = window.dashboard.workingDirectoryManager.getDefaultWorkingDir();
        } else {
            // Fallback: Try to get from header display element
            const headerWorkingDir = document.getElementById('working-dir-path');
            if (headerWorkingDir?.textContent?.trim()) {
                const headerPath = headerWorkingDir.textContent.trim();
                if (headerPath !== 'Loading...' && headerPath !== 'Unknown') {
                    defaultWorkingDir = headerPath;
                }
            }
        }
        
        console.log('[SESSION-MANAGER] Using default working directory:', defaultWorkingDir);

        // Update "All Sessions" option to show working directory
        sessionSelect.innerHTML = `
            <option value="">${defaultWorkingDir} | All Sessions</option>
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
                
                // Extract working directory from session or events
                let workingDir = session.working_directory || session.workingDirectory || '';
                
                // Log for debugging
                console.log(`[SESSION-DROPDOWN] Session ${session.id.substring(0, 8)} working_directory:`, workingDir);
                
                if (!workingDir) {
                    const sessionData = this.extractSessionInfoFromEvents(session.id);
                    workingDir = sessionData.workingDir || defaultWorkingDir;
                    console.log(`[SESSION-DROPDOWN] Extracted working directory from events:`, workingDir);
                }
                
                // Format display: working_directory | session_id...
                const shortId = session.id.substring(0, 8);
                const dirDisplay = workingDir || defaultWorkingDir;
                option.textContent = `${dirDisplay} | ${shortId}...${isActive ? ' [ACTIVE]' : ''}`;
                sessionSelect.appendChild(option);
            });
        }

        // Restore selection if it still exists
        if (currentSelection && Array.from(sessionSelect.options).some(opt => opt.value === currentSelection)) {
            sessionSelect.value = currentSelection;
            this.selectedSessionId = currentSelection;
            // Trigger events for restored selection
            this.onSessionFilterChanged();
        } else {
            this.selectedSessionId = sessionSelect.value;
            // Trigger events for new selection
            if (this.selectedSessionId) {
                this.onSessionFilterChanged();
            }
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

        // Also dispatch sessionChanged for backward compatibility with other components
        document.dispatchEvent(new CustomEvent('sessionChanged', {
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
        console.log('[SESSION-DEBUG] updateFooterInfo called, selectedSessionId:', this.selectedSessionId);

        const footerSessionEl = document.getElementById('footer-session');
        const footerWorkingDirEl = document.getElementById('footer-working-dir');
        const footerGitBranchEl = document.getElementById('footer-git-branch');

        if (!footerSessionEl) {
            console.warn('[SESSION-DEBUG] footer-session element not found');
            return;
        }

        let sessionInfo = 'All Sessions';
        // Use browser-compatible fallback for working directory
        // WHY: Removed process.cwd() Node.js reference - not available in browser
        // BROWSER FIX: Use dashboard manager or server-provided config
        let workingDir = window.dashboard?.workingDirectoryManager?.getDefaultWorkingDir() || 
                        window.dashboardConfig?.workingDirectory || 
                        '.';
        let gitBranch = 'Unknown';

        console.log('[SESSION-DEBUG] Initial values - sessionInfo:', sessionInfo, 'workingDir:', workingDir, 'gitBranch:', gitBranch);

        if (this.selectedSessionId === 'current') {
            sessionInfo = this.currentSessionId ?
                `Current: ${this.currentSessionId.substring(0, 8)}...` :
                'Current: None';

            // For current session, try to extract info from recent events
            if (this.currentSessionId) {
                const sessionData = this.extractSessionInfoFromEvents(this.currentSessionId);
                // Browser-compatible working directory fallback
                workingDir = sessionData.workingDir || 
                           window.dashboard?.workingDirectoryManager?.getDefaultWorkingDir() || 
                           window.dashboardConfig?.workingDirectory || 
                           '.';
                gitBranch = sessionData.gitBranch || 'Unknown';
            }
        } else if (this.selectedSessionId) {
            const session = this.sessions.get(this.selectedSessionId);
            if (session) {
                sessionInfo = `${this.selectedSessionId.substring(0, 8)}...`;
                workingDir = session.working_directory || session.workingDirectory || '';
                gitBranch = session.git_branch || session.gitBranch || '';

                // If session doesn't have these values, extract from events
                if (!workingDir || !gitBranch) {
                    const sessionData = this.extractSessionInfoFromEvents(this.selectedSessionId);
                    // Browser-compatible fallback - no process.cwd()
                    workingDir = workingDir || sessionData.workingDir || window.dashboardConfig?.workingDirectory || '.';
                    gitBranch = gitBranch || sessionData.gitBranch || '';
                }
            }
        }

        console.log('[SESSION-DEBUG] Final values before setting footer - sessionInfo:', sessionInfo, 'workingDir:', workingDir, 'gitBranch:', gitBranch);

        footerSessionEl.textContent = sessionInfo;
        if (footerWorkingDirEl) {
            console.log('[SESSION-DEBUG] Setting footer working dir to:', workingDir);
            footerWorkingDirEl.textContent = workingDir;
        } else {
            console.warn('[SESSION-DEBUG] footer-working-dir element not found');
        }
        if (footerGitBranchEl) {
            console.log('[SESSION-DEBUG] Setting footer git branch to:', gitBranch);
            footerGitBranchEl.textContent = gitBranch;
        } else {
            console.warn('[SESSION-DEBUG] footer-git-branch element not found');
        }
    }

    /**
     * Extract working directory and git branch from events for a specific session
     * @param {string} sessionId - Session ID to extract info for
     * @returns {Object} Object with workingDir and gitBranch properties
     */
    extractSessionInfoFromEvents(sessionId) {
        let workingDir = '';
        let gitBranch = '';

        console.log(`[DEBUG] extractSessionInfoFromEvents called for sessionId: ${sessionId}`);

        // Get events from the socket client
        const socketClient = this.socketClient;
        if (socketClient && socketClient.events) {
            console.log(`[DEBUG] Total events available: ${socketClient.events.length}`);

            // Look for session start events or recent events with this session ID
            const sessionEvents = socketClient.events.filter(event =>
                event.data && event.data.session_id === sessionId
            );

            console.log(`[DEBUG] Events matching sessionId ${sessionId}: ${sessionEvents.length}`);

            // Log a few sample events to see their structure
            if (sessionEvents.length > 0) {
                console.log(`[DEBUG] Sample events for session ${sessionId}:`);

                // Show first 3 events
                sessionEvents.slice(0, 3).forEach((event, index) => {
                    console.log(`[DEBUG] Event ${index + 1}:`, {
                        type: event.type,
                        timestamp: event.timestamp,
                        data_keys: event.data ? Object.keys(event.data) : 'no data',
                        full_event: event
                    });
                });

                // Show last 3 events if different from first 3
                if (sessionEvents.length > 3) {
                    console.log(`[DEBUG] Last 3 events for session ${sessionId}:`);
                    sessionEvents.slice(-3).forEach((event, index) => {
                        console.log(`[DEBUG] Last Event ${index + 1}:`, {
                            type: event.type,
                            timestamp: event.timestamp,
                            data_keys: event.data ? Object.keys(event.data) : 'no data',
                            full_event: event
                        });
                    });
                }
            }

            // Find the most recent event with working directory and git branch info
            for (let i = sessionEvents.length - 1; i >= 0; i--) {
                const event = sessionEvents[i];
                if (event.data) {
                    console.log(`[DEBUG] Examining event ${i} data:`, event.data);

                    // Check for working directory info
                    if (!workingDir) {
                        if (event.data.working_directory) {
                            workingDir = event.data.working_directory;
                            console.log(`[DEBUG] Found working_directory: ${workingDir}`);
                        } else if (event.data.cwd) {
                            workingDir = event.data.cwd;
                            console.log(`[DEBUG] Found cwd: ${workingDir}`);
                        } else if (event.data.instance_info && event.data.instance_info.working_dir) {
                            workingDir = event.data.instance_info.working_dir;
                            console.log(`[DEBUG] Found instance_info.working_dir: ${workingDir}`);
                        }
                    }

                    // Check for git branch info - check all possible field names
                    if (!gitBranch) {
                        const possibleBranchFields = [
                            'git_branch',
                            'gitBranch',
                            'branch',
                            'git.branch',
                            'vcs_branch',
                            'current_branch'
                        ];

                        for (const field of possibleBranchFields) {
                            if (event.data[field]) {
                                gitBranch = event.data[field];
                                console.log(`[DEBUG] Found git branch in field '${field}': ${gitBranch}`);
                                break;
                            }
                        }

                        // Check nested locations
                        if (!gitBranch) {
                            if (event.data.instance_info) {
                                console.log(`[DEBUG] Checking instance_info for branch:`, event.data.instance_info);
                                for (const field of possibleBranchFields) {
                                    if (event.data.instance_info[field]) {
                                        gitBranch = event.data.instance_info[field];
                                        console.log(`[DEBUG] Found git branch in instance_info.${field}: ${gitBranch}`);
                                        break;
                                    }
                                }
                            }

                            if (!gitBranch && event.data.git) {
                                console.log(`[DEBUG] Checking git object:`, event.data.git);
                                if (event.data.git.branch) {
                                    gitBranch = event.data.git.branch;
                                    console.log(`[DEBUG] Found git branch in git.branch: ${gitBranch}`);
                                }
                            }
                        }
                    }

                    // If we have both, we can stop looking
                    if (workingDir && gitBranch) {
                        console.log(`[DEBUG] Found both workingDir and gitBranch, stopping search`);
                        break;
                    }
                }
            }
        } else {
            console.log(`[DEBUG] No socket client or events available`);
        }

        console.log(`[DEBUG] Final results - workingDir: '${workingDir}', gitBranch: '${gitBranch}'`);
        return { workingDir, gitBranch };
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

    /**
     * Get events for a specific session
     * @param {string} sessionId - Session ID to get events for
     * @returns {Array} - Filtered events for the session
     */
    getEventsForSession(sessionId) {
        if (!sessionId || !this.socketClient) {
            return [];
        }

        const allEvents = this.socketClient.events || [];
        return allEvents.filter(event => {
            // Check for session ID in various possible locations
            const eventSessionId = event.session_id ||
                                 (event.data && event.data.session_id) ||
                                 null;
            return eventSessionId === sessionId;
        });
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
// ES6 Module export
export { SessionManager };
export default SessionManager;
