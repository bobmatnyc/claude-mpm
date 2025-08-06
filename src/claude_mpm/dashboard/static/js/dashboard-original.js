/**
 * Main Dashboard Application
 * Coordinates all components and handles tab management
 */

class Dashboard {
    constructor() {
        // Components
        this.socketClient = null;
        this.eventViewer = null;
        this.moduleViewer = null;
        this.sessionManager = null;
        this.hudVisualizer = null;
        
        // State
        this.currentTab = 'events';
        this.autoScroll = true;
        this.hudMode = false;
        
        // Working directory state - will be set properly during initialization
        this.currentWorkingDir = null;
        
        // Selection state - tracks the currently selected card across all tabs
        this.selectedCard = {
            tab: null,        // which tab the selection is in
            index: null,      // index of selected item in that tab
            type: null,       // 'event', 'agent', 'tool', 'file'
            data: null        // the actual data object
        };
        
        // Navigation state for each tab
        this.tabNavigation = {
            events: { selectedIndex: -1, items: [] },
            agents: { selectedIndex: -1, items: [] },
            tools: { selectedIndex: -1, items: [] },
            files: { selectedIndex: -1, items: [] }
        };
        
        // File tracking for files tab
        this.fileOperations = new Map(); // Map of file paths to operations
        
        // Tool call tracking for tools tab
        this.toolCalls = new Map(); // Map of tool call keys to paired pre/post events
        
        // Agent events tracking for agents tab
        this.agentEvents = []; // Array of filtered agent events
        
        this.init();
    }

    /**
     * Initialize the dashboard
     */
    init() {
        // Initialize components
        this.initializeComponents();
        this.setupEventHandlers();
        this.setupTabNavigation();
        this.setupUnifiedKeyboardNavigation();
        this.initializeFromURL();
        
        // Initialize agent inference system
        this.initializeAgentInference();
        
        // Initialize working directory for current session
        this.initializeWorkingDirectory();
        
        // Watch for footer directory changes
        this.watchFooterDirectory();
        
        // Initialize HUD button state
        this.updateHUDButtonState();
        
        console.log('Claude MPM Dashboard initialized');
    }

    /**
     * Initialize agent inference system
     * Based on docs/design/main-subagent-identification.md
     */
    initializeAgentInference() {
        // Agent inference state tracking
        this.agentInference = {
            // Track current subagent delegation context
            currentDelegation: null,
            // Map of session_id -> agent context
            sessionAgents: new Map(),
            // Map of event indices -> inferred agent
            eventAgentMap: new Map()
        };
        
        console.log('Agent inference system initialized');
    }

    /**
     * Infer agent context from event payload
     * Based on production-ready detection from design document
     * @param {Object} event - Event payload
     * @returns {Object} - {type: 'main_agent'|'subagent', confidence: 'definitive'|'high'|'medium'|'default', agentName: string}
     */
    inferAgentFromEvent(event) {
        // Handle both direct properties and nested data properties
        const data = event.data || {};
        const sessionId = event.session_id || data.session_id || 'unknown';
        const eventType = event.hook_event_name || data.hook_event_name || event.type || '';
        const subtype = event.subtype || '';
        const toolName = event.tool_name || data.tool_name || '';
        
        // Direct event detection (highest confidence) - from design doc
        if (eventType === 'SubagentStop' || subtype === 'subagent_stop') {
            const agentName = this.extractAgentNameFromEvent(event);
            return {
                type: 'subagent',
                confidence: 'definitive',
                agentName: agentName,
                reason: 'SubagentStop event'
            };
        }
        
        if (eventType === 'Stop' || subtype === 'stop') {
            return {
                type: 'main_agent',
                confidence: 'definitive',
                agentName: 'PM',
                reason: 'Stop event'
            };
        }
        
        // Tool-based detection (high confidence) - from design doc
        if (toolName === 'Task') {
            const agentName = this.extractSubagentTypeFromTask(event);
            if (agentName) {
                return {
                    type: 'subagent',
                    confidence: 'high',
                    agentName: agentName,
                    reason: 'Task tool with subagent_type'
                };
            }
        }
        
        // Hook event pattern analysis (high confidence)
        if (eventType === 'PreToolUse' && toolName === 'Task') {
            const agentName = this.extractSubagentTypeFromTask(event);
            if (agentName) {
                return {
                    type: 'subagent',
                    confidence: 'high',
                    agentName: agentName,
                    reason: 'PreToolUse Task delegation'
                };
            }
        }
        
        // Session pattern analysis (medium confidence) - from design doc
        if (sessionId) {
            const sessionLower = sessionId.toLowerCase();
            if (['subagent', 'task', 'agent-'].some(pattern => sessionLower.includes(pattern))) {
                return {
                    type: 'subagent',
                    confidence: 'medium',
                    agentName: 'Subagent',
                    reason: 'Session ID pattern'
                };
            }
        }
        
        // Agent type field analysis
        const agentType = event.agent_type || event.data?.agent_type;
        const subagentType = event.subagent_type || event.data?.subagent_type;
        
        if (subagentType && subagentType !== 'unknown') {
            return {
                type: 'subagent',
                confidence: 'high',
                agentName: subagentType,
                reason: 'subagent_type field'
            };
        }
        
        if (agentType && agentType !== 'unknown' && agentType !== 'main') {
            return {
                type: 'subagent',
                confidence: 'medium',
                agentName: agentType,
                reason: 'agent_type field'
            };
        }
        
        // Default to main agent (from design doc)
        return {
            type: 'main_agent',
            confidence: 'default',
            agentName: 'PM',
            reason: 'default classification'
        };
    }

    /**
     * Extract subagent type from Task tool parameters
     * @param {Object} event - Event with Task tool
     * @returns {string|null} - Subagent type or null
     */
    extractSubagentTypeFromTask(event) {
        // Check tool_parameters directly
        if (event.tool_parameters?.subagent_type) {
            return event.tool_parameters.subagent_type;
        }
        
        // Check nested in data.tool_parameters (hook events)
        if (event.data?.tool_parameters?.subagent_type) {
            return event.data.tool_parameters.subagent_type;
        }
        
        // Check delegation_details (new structure)
        if (event.data?.delegation_details?.agent_type) {
            return event.data.delegation_details.agent_type;
        }
        
        // Check tool_input fallback
        if (event.tool_input?.subagent_type) {
            return event.tool_input.subagent_type;
        }
        
        return null;
    }

    /**
     * Extract agent name from any event
     * @param {Object} event - Event payload
     * @returns {string} - Agent name
     */
    extractAgentNameFromEvent(event) {
        // Priority order based on reliability from design doc
        const data = event.data || {};
        
        // 1. Task tool subagent_type (highest priority)
        if (event.tool_name === 'Task' || data.tool_name === 'Task') {
            const taskAgent = this.extractSubagentTypeFromTask(event);
            if (taskAgent) return taskAgent;
        }
        
        // 2. Direct subagent_type field
        if (event.subagent_type && event.subagent_type !== 'unknown') {
            return event.subagent_type;
        }
        if (data.subagent_type && data.subagent_type !== 'unknown') {
            return data.subagent_type;
        }
        
        // 3. Agent type fields (but not 'main' or 'unknown')
        if (event.agent_type && !['main', 'unknown'].includes(event.agent_type)) {
            return event.agent_type;
        }
        if (data.agent_type && !['main', 'unknown'].includes(data.agent_type)) {
            return event.agent_type;
        }
        
        if (event.data?.agent_type && !['main', 'unknown'].includes(event.data.agent_type)) {
            return event.data.agent_type;
        }
        
        // 5. Other fallbacks
        if (event.agent && event.agent !== 'unknown') {
            return event.agent;
        }
        
        if (event.name && event.name !== 'unknown') {
            return event.name;
        }
        
        // Default fallback
        return 'Unknown';
    }

    /**
     * Process all events and build agent inference context
     * This tracks delegation boundaries and agent context throughout the session
     */
    processAgentInference() {
        const events = this.eventViewer.events;
        
        // Reset inference state
        this.agentInference.currentDelegation = null;
        this.agentInference.sessionAgents.clear();
        this.agentInference.eventAgentMap.clear();
        
        console.log('Processing agent inference for', events.length, 'events');
        
        // Process events chronologically to track delegation context
        events.forEach((event, index) => {
            const inference = this.inferAgentFromEvent(event);
            const sessionId = event.session_id || 'default';
            
            // Track delegation boundaries
            if (event.tool_name === 'Task' && inference.type === 'subagent') {
                // Start of subagent delegation
                this.agentInference.currentDelegation = {
                    agentName: inference.agentName,
                    sessionId: sessionId,
                    startIndex: index,
                    endIndex: null
                };
                console.log('Delegation started:', this.agentInference.currentDelegation);
            } else if (inference.confidence === 'definitive' && inference.reason === 'SubagentStop event') {
                // End of subagent delegation
                if (this.agentInference.currentDelegation) {
                    this.agentInference.currentDelegation.endIndex = index;
                    console.log('Delegation ended:', this.agentInference.currentDelegation);
                    this.agentInference.currentDelegation = null;
                }
            }
            
            // Determine agent for this event based on context
            let finalAgent = inference;
            
            // If we're in a delegation context and this event doesn't have high confidence agent info,
            // inherit from delegation context
            if (this.agentInference.currentDelegation && 
                inference.confidence === 'default' && 
                sessionId === this.agentInference.currentDelegation.sessionId) {
                finalAgent = {
                    type: 'subagent',
                    confidence: 'inherited',
                    agentName: this.agentInference.currentDelegation.agentName,
                    reason: 'inherited from delegation context'
                };
            }
            
            // Store the inference result
            this.agentInference.eventAgentMap.set(index, finalAgent);
            
            // Update session agent tracking
            this.agentInference.sessionAgents.set(sessionId, finalAgent);
            
            // Debug first few inferences
            if (index < 5) {
                console.log(`Event ${index} agent inference:`, {
                    event_type: event.type,
                    subtype: event.subtype,
                    tool_name: event.tool_name,
                    inference: finalAgent
                });
            }
        });
        
        console.log('Agent inference processing complete. Results:', {
            total_events: events.length,
            inferred_agents: this.agentInference.eventAgentMap.size,
            unique_sessions: this.agentInference.sessionAgents.size
        });
    }

    /**
     * Get inferred agent for a specific event
     * @param {number} eventIndex - Index of event in events array
     * @returns {Object|null} - Agent inference result or null
     */
    getInferredAgent(eventIndex) {
        return this.agentInference.eventAgentMap.get(eventIndex) || null;
    }

    /**
     * Get inferred agent for an event object
     * @param {Object} event - Event object
     * @returns {Object|null} - Agent inference result or null
     */
    getInferredAgentForEvent(event) {
        const events = this.eventViewer.events;
        const eventIndex = events.indexOf(event);
        if (eventIndex === -1) return null;
        
        return this.getInferredAgent(eventIndex);
    }

    /**
     * Initialize all components
     */
    initializeComponents() {
        // Initialize socket client
        this.socketClient = new SocketClient();
        
        // Initialize UI components
        this.eventViewer = new EventViewer('events-list', this.socketClient);
        this.moduleViewer = new ModuleViewer('module-content');
        this.sessionManager = new SessionManager(this.socketClient);
        this.hudVisualizer = new HUDVisualizer();
        
        // Store globally for backward compatibility
        window.socketClient = this.socketClient;
        window.eventViewer = this.eventViewer;
        window.moduleViewer = this.moduleViewer;
        window.sessionManager = this.sessionManager;
        window.hudVisualizer = this.hudVisualizer;
        
        // Initialize HUD visualizer
        this.hudVisualizer.initialize();
        
        // Setup component interactions
        this.setupComponentInteractions();
    }

    /**
     * Setup interactions between components
     */
    setupComponentInteractions() {
        // Socket connection status is now handled in the header connection status badge
        // Footer now focuses on session-specific information

        // Listen for socket events to update file operations and tool calls
        this.socketClient.onEventUpdate((events) => {
            this.updateFileOperations(events);
            this.updateToolCalls(events);
            // Process agent inference after events are updated
            this.processAgentInference();
            this.renderCurrentTab();
            
            // Process new events for HUD visualization
            if (this.hudMode && this.hudVisualizer && events.length > 0) {
                // Get the most recent event for HUD processing
                const latestEvent = events[events.length - 1];
                this.handleHUDEvent(latestEvent);
            }
            
            // Auto-scroll events list if on events tab
            if (this.currentTab === 'events') {
                this.scrollListToBottom('events-list');
            }
        });

        // Listen for connection status changes
        document.addEventListener('socketConnectionStatus', (e) => {
            this.updateConnectionStatus(e.detail.status, e.detail.type);
            
            // Set up git branch listener when connected
            if (e.detail.type === 'connected' && this.socketClient && this.socketClient.socket) {
                // Remove any existing listener first
                this.socketClient.socket.off('git_branch_response');
                
                // Add the listener
                this.socketClient.socket.on('git_branch_response', (data) => {
                    if (data.success) {
                        const footerBranch = document.getElementById('footer-git-branch');
                        if (footerBranch) {
                            footerBranch.textContent = data.branch;
                        }
                    } else {
                        const footerBranch = document.getElementById('footer-git-branch');
                        if (footerBranch) {
                            footerBranch.textContent = 'No Git';
                        }
                    }
                });
                
                // Request git branch for current working directory
                this.updateGitBranch(this.currentWorkingDir);
            }
        });

        // Listen for session filter changes to update dropdown options
        document.addEventListener('sessionFilterChanged', (e) => {
            console.log('Session filter changed, re-rendering current tab:', this.currentTab);
            this.renderCurrentTab();
            // Update HUD button state based on session selection
            this.updateHUDButtonState();
        });
    }

    /**
     * Setup general event handlers
     */
    setupEventHandlers() {
        // Connection controls
        const connectBtn = document.getElementById('connect-btn');
        const disconnectBtn = document.getElementById('disconnect-btn');
        const portInput = document.getElementById('port-input');

        if (connectBtn) {
            connectBtn.addEventListener('click', () => {
                const port = portInput ? portInput.value : '8765';
                this.socketClient.connect(port);
            });
        }

        if (disconnectBtn) {
            disconnectBtn.addEventListener('click', () => {
                this.socketClient.disconnect();
            });
        }

        // Connection toggle button
        const connectionToggleBtn = document.getElementById('connection-toggle-btn');
        if (connectionToggleBtn) {
            connectionToggleBtn.addEventListener('click', () => {
                this.toggleConnectionControls();
            });
        }

        // Working directory controls
        const changeDirBtn = document.getElementById('change-dir-btn');
        const workingDirPath = document.getElementById('working-dir-path');
        
        if (changeDirBtn) {
            changeDirBtn.addEventListener('click', () => {
                this.showChangeDirDialog();
            });
        }
        
        if (workingDirPath) {
            workingDirPath.addEventListener('click', () => {
                this.showChangeDirDialog();
            });
        }
        
        // Action buttons
        const clearBtn = document.querySelector('button[onclick="clearEvents()"]');
        const exportBtn = document.getElementById('export-btn');
        
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                this.clearEvents();
            });
        }
        
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                this.exportEvents();
            });
        }

        // HUD toggle button
        const hudToggleBtn = document.getElementById('hud-toggle-btn');
        if (hudToggleBtn) {
            hudToggleBtn.addEventListener('click', () => {
                this.toggleHUD();
            });
        }

        // Clear selection button
        const clearSelectionBtn = document.querySelector('button[onclick="clearSelection()"]');
        if (clearSelectionBtn) {
            clearSelectionBtn.addEventListener('click', () => {
                this.clearSelection();
            });
        }

        // Tab-specific filters
        this.setupTabFilters();
    }

    /**
     * Setup filtering for each tab
     */
    setupTabFilters() {
        // Agents tab filters
        const agentsSearchInput = document.getElementById('agents-search-input');
        const agentsTypeFilter = document.getElementById('agents-type-filter');
        
        if (agentsSearchInput) {
            agentsSearchInput.addEventListener('input', () => {
                if (this.currentTab === 'agents') this.renderCurrentTab();
            });
        }
        
        if (agentsTypeFilter) {
            agentsTypeFilter.addEventListener('change', () => {
                if (this.currentTab === 'agents') this.renderCurrentTab();
            });
        }

        // Tools tab filters
        const toolsSearchInput = document.getElementById('tools-search-input');
        const toolsTypeFilter = document.getElementById('tools-type-filter');
        
        if (toolsSearchInput) {
            toolsSearchInput.addEventListener('input', () => {
                if (this.currentTab === 'tools') this.renderCurrentTab();
            });
        }
        
        if (toolsTypeFilter) {
            toolsTypeFilter.addEventListener('change', () => {
                if (this.currentTab === 'tools') this.renderCurrentTab();
            });
        }

        // Files tab filters
        const filesSearchInput = document.getElementById('files-search-input');
        const filesTypeFilter = document.getElementById('files-type-filter');
        
        if (filesSearchInput) {
            filesSearchInput.addEventListener('input', () => {
                if (this.currentTab === 'files') this.renderCurrentTab();
            });
        }
        
        if (filesTypeFilter) {
            filesTypeFilter.addEventListener('change', () => {
                if (this.currentTab === 'files') this.renderCurrentTab();
            });
        }
    }

    /**
     * Populate filter dropdown with unique values from data
     * @param {string} selectId - ID of the select element
     * @param {Array} values - Array of unique values to populate
     * @param {string} allOption - Text for the "All" option
     */
    populateFilterDropdown(selectId, values, allOption) {
        const select = document.getElementById(selectId);
        if (!select) return;

        // Store current selection
        const currentValue = select.value;

        // Clear existing options except the first "All" option
        select.innerHTML = `<option value="">${allOption}</option>`;

        // Add unique values, sorted alphabetically
        const sortedValues = [...values].sort();
        sortedValues.forEach(value => {
            const option = document.createElement('option');
            option.value = value;
            option.textContent = value;
            select.appendChild(option);
        });

        // Restore selection if it still exists
        if (currentValue && sortedValues.includes(currentValue)) {
            select.value = currentValue;
        }
    }

    /**
     * Setup tab navigation
     */
    setupTabNavigation() {
        const tabButtons = document.querySelectorAll('.tab-button');
        tabButtons.forEach(button => {
            button.addEventListener('click', () => {
                const tabName = this.getTabNameFromButton(button);
                this.switchTab(tabName);
            });
        });
    }

    /**
     * Setup unified keyboard navigation for all tabs
     */
    setupUnifiedKeyboardNavigation() {
        document.addEventListener('keydown', (e) => {
            // Only handle navigation if no input is focused
            if (document.activeElement && 
                (document.activeElement.tagName === 'INPUT' || 
                 document.activeElement.tagName === 'TEXTAREA' || 
                 document.activeElement.tagName === 'SELECT')) {
                return;
            }

            if (e.key === 'ArrowUp' || e.key === 'ArrowDown') {
                e.preventDefault();
                this.handleUnifiedArrowNavigation(e.key === 'ArrowDown' ? 1 : -1);
            } else if (e.key === 'Enter') {
                e.preventDefault();
                this.handleUnifiedEnterKey();
            } else if (e.key === 'Escape') {
                e.preventDefault();
                this.clearUnifiedSelection();
            }
        });
    }

    /**
     * Get tab name from button text
     */
    getTabNameFromButton(button) {
        const text = button.textContent.toLowerCase();
        if (text.includes('events')) return 'events';
        if (text.includes('agents')) return 'agents';
        if (text.includes('tools')) return 'tools';
        if (text.includes('files')) return 'files';
        return 'events';
    }

    /**
     * Initialize from URL parameters
     */
    initializeFromURL() {
        const urlParams = new URLSearchParams(window.location.search);
        const defaultPort = urlParams.get('port') || '8765';
        const autoConnect = urlParams.get('autoconnect');
        
        const portInput = document.getElementById('port-input');
        if (portInput) {
            portInput.value = defaultPort;
        }
        
        // Auto-connect logic:
        // - Connect if autoconnect=true (explicit)
        // - Connect by default unless autoconnect=false (explicit)
        // - Don't connect if already connected or connecting
        const shouldAutoConnect = autoConnect === 'true' || (autoConnect !== 'false' && autoConnect === null);
        
        if (shouldAutoConnect && !this.socketClient.isConnected && !this.socketClient.isConnecting) {
            console.log('Auto-connecting to Socket.IO server on page load...');
            this.socketClient.connect(defaultPort);
        }
    }

    /**
     * Switch to a different tab
     */
    switchTab(tabName) {
        console.log(`[DEBUG] switchTab called with tabName: ${tabName}`);
        this.currentTab = tabName;
        
        // Update tab buttons
        document.querySelectorAll('.tab-button').forEach(btn => {
            btn.classList.remove('active');
            if (this.getTabNameFromButton(btn) === tabName) {
                btn.classList.add('active');
            }
        });
        
        // Update tab content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        
        const activeTab = document.getElementById(`${tabName}-tab`);
        console.log(`[DEBUG] Active tab element found:`, activeTab);
        if (activeTab) {
            activeTab.classList.add('active');
        }
        
        // Render content for the active tab
        console.log(`[DEBUG] About to render current tab: ${tabName}`);
        this.renderCurrentTab();
        
        // Auto-scroll to bottom after tab content is rendered
        const listId = `${tabName}-list`;
        console.log(`[DEBUG] About to scroll list with ID: ${listId}`);
        this.scrollListToBottom(listId);
        
        // Fallback: Try again with longer delay in case content takes time to render
        setTimeout(() => {
            console.log(`[DEBUG] Fallback scroll attempt for ${listId}`);
            this.scrollListToBottom(listId);
        }, 200);
        
        console.log(`[DEBUG] Switched to ${tabName} tab`);
    }

    /**
     * Handle unified arrow key navigation across all tabs
     * @param {number} direction - Direction: 1 for down, -1 for up
     */
    handleUnifiedArrowNavigation(direction) {
        const tabNav = this.tabNavigation[this.currentTab];
        if (!tabNav) return;

        // Update items list for current tab
        this.updateTabNavigationItems();

        if (tabNav.items.length === 0) return;

        // Calculate new index
        let newIndex = tabNav.selectedIndex + direction;
        
        // Wrap around
        if (newIndex >= tabNav.items.length) {
            newIndex = 0;
        } else if (newIndex < 0) {
            newIndex = tabNav.items.length - 1;
        }

        // Update selection
        this.selectCardByIndex(this.currentTab, newIndex);
    }

    /**
     * Handle unified Enter key across all tabs
     */
    handleUnifiedEnterKey() {
        const tabNav = this.tabNavigation[this.currentTab];
        if (!tabNav || tabNav.selectedIndex === -1) return;

        // Trigger click on the selected item
        const selectedElement = tabNav.items[tabNav.selectedIndex];
        if (selectedElement && selectedElement.onclick) {
            selectedElement.click();
        }
    }

    /**
     * Clear unified selection across all tabs
     */
    clearUnifiedSelection() {
        // Clear all tab navigation states
        Object.keys(this.tabNavigation).forEach(tabName => {
            this.tabNavigation[tabName].selectedIndex = -1;
        });
        
        // Clear card selection
        this.clearCardSelection();
        
        // Clear EventViewer selection if it exists
        if (this.eventViewer) {
            this.eventViewer.clearSelection();
        }
        
        // Clear module viewer
        if (this.moduleViewer) {
            this.moduleViewer.clear();
        }
    }

    /**
     * Update items list for current tab navigation
     */
    updateTabNavigationItems() {
        const tabNav = this.tabNavigation[this.currentTab];
        if (!tabNav) return;

        let containerSelector;
        switch (this.currentTab) {
            case 'events':
                containerSelector = '#events-list .event-item';
                break;
            case 'agents':
                containerSelector = '#agents-list .event-item';
                break;
            case 'tools':
                containerSelector = '#tools-list .event-item';
                break;
            case 'files':
                containerSelector = '#files-list .file-item, #files-list .event-item';
                break;
        }

        if (containerSelector) {
            tabNav.items = Array.from(document.querySelectorAll(containerSelector));
        }
    }

    /**
     * Select a card by index in the specified tab
     * @param {string} tabName - Tab name
     * @param {number} index - Index of item to select
     */
    selectCardByIndex(tabName, index) {
        const tabNav = this.tabNavigation[tabName];
        if (!tabNav || index < 0 || index >= tabNav.items.length) return;

        // Update navigation state
        tabNav.selectedIndex = index;
        
        // Update visual selection
        this.updateUnifiedSelectionUI();
        
        // Scroll selected item into view
        const selectedElement = tabNav.items[index];
        if (selectedElement) {
            selectedElement.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'nearest' 
            });
        }

        // Update details view based on tab
        this.showCardDetails(tabName, index);
    }

    /**
     * Update visual selection UI for current tab
     */
    updateUnifiedSelectionUI() {
        const tabNav = this.tabNavigation[this.currentTab];
        if (!tabNav) return;

        // Clear all selections in current tab
        tabNav.items.forEach((item, index) => {
            item.classList.toggle('selected', index === tabNav.selectedIndex);
        });
    }

    /**
     * Show card details based on tab and index
     * @param {string} tabName - Tab name
     * @param {number} index - Index of item
     */
    showCardDetails(tabName, index) {
        switch (tabName) {
            case 'events':
                // Use EventViewer's existing method
                if (this.eventViewer) {
                    this.eventViewer.showEventDetails(index);
                }
                break;
            case 'agents':
                this.showAgentDetailsByIndex(index);
                break;
            case 'tools':
                this.showToolDetailsByIndex(index);
                break;
            case 'files':
                this.showFileDetailsByIndex(index);
                break;
        }
    }

    /**
     * Select a card and update the UI
     * @param {string} tabName - Tab name (events, agents, tools, files)
     * @param {number} index - Index of the item in that tab
     * @param {string} type - Type of item (event, agent, tool, file)
     * @param {Object} data - The data object for the selected item
     */
    selectCard(tabName, index, type, data) {
        // Clear previous selection
        this.clearCardSelection();
        
        // Update selection state
        this.selectedCard = {
            tab: tabName,
            index: index,
            type: type,
            data: data
        };
        
        // Update visual selection in the current tab
        this.updateCardSelectionUI();
        
        console.log('Card selected:', this.selectedCard);
    }
    
    /**
     * Clear card selection
     */
    clearCardSelection() {
        // Clear visual selection from all tabs
        document.querySelectorAll('.event-item.selected, .file-item.selected').forEach(el => {
            el.classList.remove('selected');
        });
        
        // Reset selection state
        this.selectedCard = {
            tab: null,
            index: null,
            type: null,
            data: null
        };
    }
    
    /**
     * Update visual selection in the current tab
     */
    updateCardSelectionUI() {
        if (!this.selectedCard.tab || this.selectedCard.index === null) return;
        
        // Get the list container for the selected tab
        let listContainer;
        switch (this.selectedCard.tab) {
            case 'events':
                listContainer = document.getElementById('events-list');
                break;
            case 'agents':
                listContainer = document.getElementById('agents-list');
                break;
            case 'tools':
                listContainer = document.getElementById('tools-list');
                break;
            case 'files':
                listContainer = document.getElementById('files-list');
                break;
        }
        
        if (listContainer) {
            const cards = listContainer.querySelectorAll('.event-item, .file-item');
            cards.forEach((card, index) => {
                card.classList.toggle('selected', index === this.selectedCard.index);
            });
        }
    }

    /**
     * Show agent details by index in the current filtered list
     * @param {number} index - Index in the filtered agents list
     */
    showAgentDetailsByIndex(index) {
        // Use stored filtered agent events instead of recalculating
        const agentEvents = this.agentEvents;

        if (index < 0 || index >= agentEvents.length) {
            console.warn('Invalid agent index:', index, 'Available agents:', agentEvents.length);
            return;
        }

        const event = agentEvents[index];
        const eventIndex = this.eventViewer.events.indexOf(event);
        this.showAgentDetails(index, eventIndex);
    }

    /**
     * Show tool details by index in the current filtered list
     * @param {number} index - Index in the filtered tool calls list
     */
    showToolDetailsByIndex(index) {
        // Get filtered tool calls array (same as renderTools)
        let toolCallsArray = Array.from(this.toolCalls.entries())
            .filter(([key, toolCall]) => {
                return toolCall.tool_name && (toolCall.pre_event || toolCall.post_event);
            })
            .sort((a, b) => {
                const timeA = new Date(a[1].timestamp || 0);
                const timeB = new Date(b[1].timestamp || 0);
                return timeA - timeB;
            });

        // Apply tab-specific filters
        toolCallsArray = this.applyToolCallFilters(toolCallsArray);

        if (index < 0 || index >= toolCallsArray.length) return;

        const [toolCallKey] = toolCallsArray[index];
        this.showToolCallDetails(toolCallKey);
    }

    /**
     * Show file details by index in the current filtered list
     * @param {number} index - Index in the filtered files list
     */
    showFileDetailsByIndex(index) {
        let filesArray = Array.from(this.fileOperations.entries())
            .filter(([filePath, fileData]) => {
                return fileData.operations && fileData.operations.length > 0;
            })
            .sort((a, b) => {
                const timeA = a[1].lastOperation ? new Date(a[1].lastOperation) : new Date(0);
                const timeB = b[1].lastOperation ? new Date(b[1].lastOperation) : new Date(0);
                return timeA - timeB;
            });

        filesArray = this.applyFilesFilters(filesArray);

        if (index < 0 || index >= filesArray.length) return;

        const [filePath] = filesArray[index];
        this.showFileDetails(filePath);
    }

    /**
     * Render content for the current tab
     */
    renderCurrentTab() {
        switch (this.currentTab) {
            case 'events':
                // Events are automatically rendered by EventViewer
                break;
            case 'agents':
                this.renderAgents();
                break;
            case 'tools':
                this.renderTools();
                break;
            case 'files':
                this.renderFiles();
                break;
        }
        
        // Update navigation items for the current tab after rendering
        this.updateTabNavigationItems();
        
        // Restore selection after rendering if it's in the current tab
        if (this.selectedCard.tab === this.currentTab) {
            this.updateCardSelectionUI();
        }
        
        // Update unified selection UI to maintain consistency
        this.updateUnifiedSelectionUI();
    }

    /**
     * Render agents tab
     */
    renderAgents() {
        console.log('=== RENDERAGENTS DEBUG START ===');
        console.log('1. Function called, checking agentsList element...');
        
        const agentsList = document.getElementById('agents-list');
        if (!agentsList) {
            console.error('agentsList element not found!');
            return;
        }
        console.log('2. agentsList element found:', agentsList);

        const events = this.getFilteredEventsForTab('agents');
        console.log('3. Total events from getFilteredEventsForTab:', events.length);
        
        // Enhanced debugging: log first few events to understand structure
        if (events.length > 0) {
            console.log('Agent tab - sample events for analysis:');
            events.slice(0, 3).forEach((event, i) => {
                console.log(`  Event ${i}:`, {
                    type: event.type,
                    subtype: event.subtype,
                    tool_name: event.tool_name,
                    agent_type: event.agent_type,
                    subagent_type: event.subagent_type,
                    tool_parameters: event.tool_parameters,
                    delegation_details: event.delegation_details,
                    data: event.data ? {
                        agent_type: event.data.agent_type,
                        subagent_type: event.data.subagent_type,
                        event_type: event.data.event_type,
                        tool_name: event.data.tool_name,
                        tool_parameters: event.data.tool_parameters,
                        delegation_details: event.data.delegation_details
                    } : 'no data field'
                });
            });
            
            // Count events by type and tool_name for debugging
            const eventCounts = {};
            const toolCounts = {};
            const agentCounts = {};
            events.forEach(event => {
                const key = `${event.type}.${event.subtype || 'none'}`;
                eventCounts[key] = (eventCounts[key] || 0) + 1;
                
                if (event.tool_name) {
                    toolCounts[event.tool_name] = (toolCounts[event.tool_name] || 0) + 1;
                }
                
                // Count agent types from multiple sources
                const agentTypes = [];
                if (event.agent_type) agentTypes.push(`direct:${event.agent_type}`);
                if (event.subagent_type) agentTypes.push(`sub:${event.subagent_type}`);
                if (event.tool_parameters?.subagent_type) agentTypes.push(`tool_param:${event.tool_parameters.subagent_type}`);
                if (event.data?.agent_type) agentTypes.push(`data:${event.data.agent_type}`);
                if (event.data?.subagent_type) agentTypes.push(`data_sub:${event.data.subagent_type}`);
                if (event.data?.delegation_details?.agent_type) agentTypes.push(`delegation:${event.data.delegation_details.agent_type}`);
                
                agentTypes.forEach(agentType => {
                    agentCounts[agentType] = (agentCounts[agentType] || 0) + 1;
                });
            });
            console.log('Agent tab - event type breakdown:', eventCounts);
            console.log('Agent tab - tool breakdown:', toolCounts);
            console.log('Agent tab - agent type breakdown:', agentCounts);
        }
        
        // Use agent inference to filter events instead of hardcoded logic
        let agentEvents = events
            .map((event, index) => ({ event, index, inference: this.inferAgentFromEvent(event) }))
            .filter(({ event, index, inference }) => {
                // Show events that have meaningful agent context
                if (!inference) return false;
                
                // Include events that are definitely agent-related
                const isAgentRelated = inference.type === 'subagent' || 
                                     (inference.type === 'main_agent' && inference.confidence !== 'default') ||
                                     event.tool_name === 'Task' ||
                                     event.hook_event_name === 'SubagentStop' ||
                                     event.subtype === 'subagent_stop';
                
                // Debug first few events
                if (index < 5) {
                    console.log(`Agent filter [${index}] - ${isAgentRelated ? 'MATCHED' : 'SKIPPED'}:`, {
                        type: event.type,
                        subtype: event.subtype,
                        tool_name: event.tool_name,
                        inference: inference,
                        isAgentRelated
                    });
                }
                
                return isAgentRelated;
            })
            .map(({ event, inference }) => ({ event, inference }))
            .sort((a, b) => new Date(a.event.timestamp) - new Date(b.event.timestamp));

        // Extract unique agent types from the data for filter dropdown
        const uniqueAgentTypes = new Set();
        agentEvents.forEach(({ event, inference }) => {
            if (inference && inference.agentName && inference.agentName !== 'Unknown') {
                uniqueAgentTypes.add(inference.agentName);
            }
            // Also check for agent_type in the event data
            if (event.agent_type && event.agent_type !== 'unknown' && event.agent_type !== 'main') {
                uniqueAgentTypes.add(event.agent_type);
            }
            if (event.subagent_type) {
                uniqueAgentTypes.add(event.subagent_type);
            }
        });

        // Populate the agents filter dropdown
        this.populateFilterDropdown('agents-type-filter', Array.from(uniqueAgentTypes), 'All Agents');

        // Apply tab-specific filters to the agentEvents array while preserving inference data
        let filteredAgentEvents = agentEvents.filter(({ event }) => {
            // Create a temporary array with just events for the existing filter function
            const singleEventArray = [event];
            const filteredSingleEvent = this.applyAgentsFilters(singleEventArray);
            return filteredSingleEvent.length > 0;
        });
        
        // Store filtered agent events with inference data in class property
        this.agentEventsWithInference = filteredAgentEvents;
        
        // Also store just the events for backward compatibility
        this.agentEvents = filteredAgentEvents.map(({ event }) => event);

        console.log('4. Agent tab - filtering summary:', {
            total_events: events.length,
            agent_events_found: filteredAgentEvents.length,
            percentage: filteredAgentEvents.length > 0 ? ((filteredAgentEvents.length / events.length) * 100).toFixed(1) + '%' : '0%'
        });

        if (filteredAgentEvents.length === 0) {
            console.log('5. No agent events found, showing empty message');
            agentsList.innerHTML = '<div class="no-events">No agent events found...</div>';
            return;
        }

        console.log('Rendering', filteredAgentEvents.length, 'agent events');

        const agentsHtml = filteredAgentEvents.map(({ event, inference }, index) => {
            const timestamp = new Date(event.timestamp).toLocaleTimeString();
            
            let agentName = inference ? inference.agentName : 'Unknown';
            let operation = 'operation';
            let prompt = '';
            let description = '';
            let taskPreview = '';
            let confidence = inference ? inference.confidence : 'unknown';
            let reason = inference ? inference.reason : 'no inference';
            
            // Extract Task tool information if present
            const data = event.data || {};
            if (event.tool_name === 'Task' || data.tool_name === 'Task') {
                operation = 'delegation';
                
                // Try different sources for Task tool data
                const taskParams = event.tool_parameters || data.tool_parameters || data.delegation_details || {};
                
                if (taskParams.prompt) {
                    prompt = taskParams.prompt;
                    taskPreview = prompt.length > 200 ? prompt.substring(0, 200) + '...' : prompt;
                }
                if (taskParams.description) {
                    description = taskParams.description;
                }
            }
            
            // Extract operation from event type/subtype
            if (event.subtype) {
                operation = event.subtype.replace(/_/g, ' ');
            } else {
                operation = this.extractOperation(event.type) || 'operation';
            }
            
            // Add confidence indicator
            const confidenceIcon = {
                'definitive': '🎯',
                'high': '✅',
                'medium': '⚠️',
                'inherited': '📋',
                'default': '❓',
                'unknown': '❔'
            }[confidence] || '❔';

            const onclickString = `dashboard.selectCard('agents', ${index}, 'agent', ${index}); dashboard.showAgentDetailsByIndex(${index});`;

            return `
                <div class="event-item event-agent" onclick="${onclickString}">
                    <div class="event-header">
                        <span class="event-type">🤖 ${agentName}</span>
                        <span class="confidence-indicator" title="Confidence: ${confidence} (${reason})">${confidenceIcon}</span>
                        <span class="event-timestamp">${timestamp}</span>
                    </div>
                    <div class="event-data">
                        <strong>Operation:</strong> ${operation}
                        <strong>Inference:</strong> ${inference ? inference.type : 'unknown'} (${confidence})
                        ${taskPreview ? `<br><strong>Task Preview:</strong> ${taskPreview}` : ''}
                        ${description ? `<br><strong>Description:</strong> ${description}` : ''}
                        ${event.session_id || data.session_id ? `<br><strong>Session:</strong> ${(event.session_id || data.session_id).substring(0, 8)}...` : ''}
                    </div>
                </div>
            `;
        }).join('');

        console.log('9. Generated HTML length:', agentsHtml.length);
        console.log('10. Sample HTML (first 500 chars):', agentsHtml.substring(0, 500));
        
        agentsList.innerHTML = agentsHtml;
        
        // Check if the HTML was actually set
        console.log('11. HTML set in DOM, innerHTML length:', agentsList.innerHTML.length);
        console.log('12. Number of event-agent elements:', agentsList.querySelectorAll('.event-agent').length);
        
        // Test onclick on first element if exists
        const firstAgent = agentsList.querySelector('.event-agent');
        if (firstAgent) {
            console.log('13. First agent element found:', firstAgent);
            console.log('14. First agent onclick attribute:', firstAgent.getAttribute('onclick'));
            
            // Add a test click event listener as well
            firstAgent.addEventListener('click', function(e) {
                console.log('15. CLICK EVENT DETECTED on agent element!', e.target);
            });
        } else {
            console.log('13. No .event-agent elements found in DOM after setting innerHTML');
        }
        
        console.log('=== RENDERAGENTS DEBUG END ===');
        this.scrollListToBottom('agents-list');
    }

    /**
     * Render tools tab - shows paired tool calls instead of individual events
     */
    renderTools() {
        const toolsList = document.getElementById('tools-list');
        if (!toolsList) return;

        console.log('Tools tab - total tool calls:', this.toolCalls.size);
        
        if (this.toolCalls.size === 0) {
            toolsList.innerHTML = '<div class="no-events">No tool calls found...</div>';
            return;
        }

        // Convert to array and sort by timestamp
        let toolCallsArray = Array.from(this.toolCalls.entries())
            .filter(([key, toolCall]) => {
                // Ensure we have valid data
                return toolCall.tool_name && (toolCall.pre_event || toolCall.post_event);
            })
            .sort((a, b) => {
                const timeA = new Date(a[1].timestamp || 0);
                const timeB = new Date(b[1].timestamp || 0);
                return timeA - timeB;
            });

        console.log('Tools tab - after filtering:', toolCallsArray.length, 'tool calls');

        // Extract unique tool names from the data for filter dropdown
        const uniqueToolNames = new Set();
        toolCallsArray.forEach(([key, toolCall]) => {
            if (toolCall.tool_name) {
                uniqueToolNames.add(toolCall.tool_name);
            }
        });

        // Populate the tools filter dropdown
        this.populateFilterDropdown('tools-type-filter', Array.from(uniqueToolNames), 'All Tools');

        // Apply tab-specific filters to tool calls
        toolCallsArray = this.applyToolCallFilters(toolCallsArray);

        console.log('Tools tab - after search/type filters:', toolCallsArray.length, 'tool calls');

        if (toolCallsArray.length === 0) {
            toolsList.innerHTML = '<div class="no-events">No tool calls match current filters...</div>';
            return;
        }

        const toolsHtml = toolCallsArray.map(([key, toolCall], index) => {
            const timestamp = new Date(toolCall.timestamp).toLocaleTimeString();
            const toolName = toolCall.tool_name || 'Unknown Tool';
            
            // Use inferred agent data instead of hardcoded 'PM'
            let agentName = 'PM';
            let confidence = 'default';
            
            // Try to get inference from pre_event first, then post_event
            const preEvent = toolCall.pre_event;
            const postEvent = toolCall.post_event;
            
            if (preEvent) {
                const eventIndex = this.eventViewer.events.indexOf(preEvent);
                const inference = this.getInferredAgent(eventIndex);
                if (inference) {
                    agentName = inference.agentName;
                    confidence = inference.confidence;
                }
            } else if (postEvent) {
                const eventIndex = this.eventViewer.events.indexOf(postEvent);
                const inference = this.getInferredAgent(eventIndex);
                if (inference) {
                    agentName = inference.agentName;
                    confidence = inference.confidence;
                }
            }
            
            // Fallback to existing logic if no inference available
            if (agentName === 'PM' && confidence === 'default') {
                agentName = toolCall.agent_type || 'PM';
            }
            
            // Extract tool target/parameters from pre_event
            const target = preEvent ? this.extractToolTarget(toolName, preEvent.tool_parameters, preEvent.tool_parameters) : 'Unknown target';
            
            // Determine status and duration
            let statusInfo = '';
            let statusClass = '';
            
            if (toolCall.post_event) {
                // We have completion data
                const duration = toolCall.duration_ms ? `${toolCall.duration_ms}ms` : 'Unknown duration';
                const success = toolCall.success !== undefined ? toolCall.success : 'Unknown';
                
                if (success === true) {
                    statusInfo = `✅ Success (${duration})`;
                    statusClass = 'tool-success';
                } else if (success === false) {
                    statusInfo = `❌ Failed (${duration})`;
                    statusClass = 'tool-failure';
                } else {
                    statusInfo = `⏳ Completed (${duration})`;
                    statusClass = 'tool-completed';
                }
            } else {
                // Only pre_event - still running or incomplete
                statusInfo = '⏳ Running...';
                statusClass = 'tool-running';
            }
            
            // Add confidence indicator for agent inference
            const confidenceIcon = {
                'definitive': '🎯',
                'high': '✅',
                'medium': '⚠️',
                'inherited': '📋',
                'default': '❓',
                'unknown': '❔'
            }[confidence] || '❔';
            
            return `
                <div class="event-item event-tool ${statusClass}" onclick="dashboard.selectCard('tools', ${index}, 'toolCall', '${key}'); dashboard.showToolCallDetails('${key}')">
                    <div class="event-header">
                        <span class="event-type">🔧 ${toolName}</span>
                        <span class="event-timestamp">${timestamp}</span>
                    </div>
                    <div class="event-data">
                        <strong>Agent:</strong> ${agentName} (${confidence})<br>
                        <strong>Status:</strong> ${statusInfo}<br>
                        <strong>Target:</strong> ${target}
                        ${toolCall.session_id ? `<br><strong>Session:</strong> ${toolCall.session_id.substring(0, 8)}...` : ''}
                    </div>
                </div>
            `;
        }).join('');

        toolsList.innerHTML = toolsHtml;
        this.scrollListToBottom('tools-list');
    }

    /**
     * Render files tab with file-centric view
     */
    renderFiles() {
        const filesList = document.getElementById('files-list');
        if (!filesList) return;

        console.log('Files tab - file operations:', this.fileOperations.size);
        console.log('Files tab - operations map:', this.fileOperations);

        if (this.fileOperations.size === 0) {
            filesList.innerHTML = '<div class="no-events">No file operations found...</div>';
            return;
        }

        // Convert to array and sort by most recent operations at bottom (chronological order)
        let filesArray = Array.from(this.fileOperations.entries())
            .filter(([filePath, fileData]) => {
                // Ensure we have valid data
                return fileData.operations && fileData.operations.length > 0;
            })
            .sort((a, b) => {
                const timeA = a[1].lastOperation ? new Date(a[1].lastOperation) : new Date(0);
                const timeB = b[1].lastOperation ? new Date(b[1].lastOperation) : new Date(0);
                return timeA - timeB;
            });

        console.log('Files tab - after filtering:', filesArray.length, 'files');

        // Extract unique operations from the data for filter dropdown
        const uniqueOperations = new Set();
        filesArray.forEach(([filePath, fileData]) => {
            if (fileData.operations && fileData.operations.length > 0) {
                fileData.operations.forEach(operation => {
                    if (operation.operation) {
                        uniqueOperations.add(operation.operation);
                    }
                });
            }
        });

        // Populate the files filter dropdown
        this.populateFilterDropdown('files-type-filter', Array.from(uniqueOperations), 'All Operations');

        // Apply tab-specific filters
        filesArray = this.applyFilesFilters(filesArray);

        console.log('Files tab - after search/type filters:', filesArray.length, 'files');

        if (filesArray.length === 0) {
            filesList.innerHTML = '<div class="no-events">No files match current filters...</div>';
            return;
        }

        const filesHtml = filesArray.map(([filePath, fileData], index) => {
            if (!fileData.operations || fileData.operations.length === 0) {
                console.warn('File with no operations:', filePath);
                return '';
            }
            
            const icon = this.getFileOperationIcon(fileData.operations);
            const lastOp = fileData.operations[fileData.operations.length - 1];
            const timestamp = new Date(lastOp.timestamp).toLocaleTimeString();
            
            // Get unique operations as text, joined with |
            const uniqueOperations = [...new Set(fileData.operations.map(op => op.operation))];
            const operationsText = uniqueOperations.join('|');
            
            return `
                <div class="event-item file-item" onclick="dashboard.selectCard('files', ${index}, 'file', '${filePath}'); dashboard.showFileDetails('${filePath}')">
                    <div class="event-header">
                        <span class="event-type">${icon}</span>
                        <span class="file-path">${this.getRelativeFilePath(filePath)}</span>
                        <span class="event-timestamp">${timestamp}</span>
                    </div>
                    <div class="event-data">
                        <strong>Operations:</strong> ${operationsText}<br>
                        <strong>Agent:</strong> ${lastOp.agent} ${lastOp.confidence ? `(${lastOp.confidence})` : ''}
                    </div>
                </div>
            `;
        }).join('');

        filesList.innerHTML = filesHtml;
        this.scrollListToBottom('files-list');
    }

    /**
     * Show agent details in module viewer
     */
    showAgentDetails(agentIndex, eventIndex) {
        console.log('showAgentDetails called with agentIndex:', agentIndex, 'eventIndex:', eventIndex);
        
        // Use stored filtered agent events with inference data if available
        const agentEventsWithInference = this.agentEventsWithInference || [];
        const agentEvents = this.agentEvents;
        
        let event, inference;
        
        // Try to get event and inference data together
        if (agentEventsWithInference[agentIndex]) {
            event = agentEventsWithInference[agentIndex].event;
            inference = agentEventsWithInference[agentIndex].inference;
        } else if (agentEvents[agentIndex]) {
            // Fallback to just event data
            event = agentEvents[agentIndex];
            inference = null;
        } else {
            return;
        }
        
        // Extract agent information using inference data first, then fallback to event data
        let agentName = 'Unknown Agent';
        let prompt = '';
        let description = '';
        let fullPrompt = '';
        
        // Use inference data for agent name if available
        if (inference && inference.agentName && inference.agentName !== 'Unknown') {
            agentName = inference.agentName;
        } else if (event.tool_name === 'Task' && event.tool_parameters?.subagent_type) {
            agentName = event.tool_parameters.subagent_type;
        } else if (event.subagent_type) {
            agentName = event.subagent_type;
        } else if (event.agent_type && event.agent_type !== 'unknown') {
            agentName = event.agent_type;
        }
        
        // Extract task information
        if (event.tool_name === 'Task' && event.tool_parameters) {
            prompt = event.tool_parameters.prompt || '';
            description = event.tool_parameters.description || '';
            fullPrompt = prompt;
        }

        // Add debug logging
        console.log('showAgentDetails called with:', { 
            agentIndex, 
            eventIndex, 
            event, 
            inference, 
            agentName: agentName,
            hasInferenceData: !!inference 
        });
        console.log('moduleViewer available:', !!this.moduleViewer);

        // Create enhanced event object with inference data for module viewer
        const enhancedEvent = {
            ...event,
            _inference: inference, // Add inference data as a private property
            _agentName: agentName  // Add resolved agent name
        };

        // Use the module viewer's ingest method to properly display the agent event
        if (this.moduleViewer) {
            console.log('Calling moduleViewer.ingest with enhanced event:', enhancedEvent);
            this.moduleViewer.ingest(enhancedEvent);
        }
        
        // Also show the event details in EventViewer
        if (eventIndex >= 0) {
            this.eventViewer.showEventDetails(eventIndex);
        }
    }

    /**
     * Toggle prompt expansion
     */
    togglePromptExpansion(button) {
        const promptDiv = button.parentElement.previousElementSibling;
        const isExpanded = promptDiv.style.maxHeight !== '300px';
        
        if (isExpanded) {
            promptDiv.style.maxHeight = '300px';
            button.textContent = 'Show More';
        } else {
            promptDiv.style.maxHeight = 'none';
            button.textContent = 'Show Less';
        }
    }

    /**
     * Show tool details in module viewer
     */
    showToolDetails(toolIndex, eventIndex) {
        // Get the tool event
        const events = this.getFilteredEventsForTab('tools');
        const toolEvents = this.applyToolsFilters(events.filter(event => {
            const type = event.type || '';
            const subtype = event.subtype || '';
            
            const isHookToolEvent = type === 'hook' && (
                subtype.includes('tool') || 
                subtype.includes('pre_') || 
                subtype.includes('post_')
            );
            const hasToolName = event.tool_name;
            const hasToolsArray = event.tools && Array.isArray(event.tools);
            const isLegacyHookEvent = type.startsWith('hook.') && (
                type.includes('tool') || 
                type.includes('pre') || 
                type.includes('post')
            );
            
            return isHookToolEvent || hasToolName || hasToolsArray || isLegacyHookEvent;
        }));

        const event = toolEvents[toolIndex];
        if (!event) return;

        // Extract tool information
        let toolName = event.tool_name || 'Unknown Tool';
        if (event.tools && Array.isArray(event.tools) && event.tools.length > 0) {
            toolName = event.tools[0];
        }
        
        let agentName = 'PM';
        if (event.subagent_type) {
            agentName = event.subagent_type;
        } else if (event.agent_type && event.agent_type !== 'main' && event.agent_type !== 'unknown') {
            agentName = event.agent_type;
        }

        const target = this.extractToolTarget(toolName, event.tool_parameters, event.tool_parameters);
        
        let operation = 'execution';
        if (event.subtype) {
            if (event.subtype.includes('pre_')) {
                operation = 'pre-execution';
            } else if (event.subtype.includes('post_')) {
                operation = 'post-execution';
            } else {
                operation = event.subtype.replace(/_/g, ' ');
            }
        }

        const content = `
            <div class="structured-view-section">
                <div class="structured-view-header">
                    <h4>🔧 Tool Details</h4>
                </div>
                <div class="tool-details">
                    <div class="tool-info">
                        <div class="structured-field">
                            <strong>Tool Name:</strong> ${toolName}
                        </div>
                        <div class="structured-field">
                            <strong>Agent:</strong> ${agentName}
                        </div>
                        <div class="structured-field">
                            <strong>Operation:</strong> ${operation}
                        </div>
                        <div class="structured-field">
                            <strong>Target:</strong> ${target}
                        </div>
                        <div class="structured-field">
                            <strong>Timestamp:</strong> ${new Date(event.timestamp).toLocaleString()}
                        </div>
                        <div class="structured-field">
                            <strong>Event Type:</strong> ${event.type}.${event.subtype || 'default'}
                        </div>
                        ${event.session_id ? `
                            <div class="structured-field">
                                <strong>Session ID:</strong> ${event.session_id}
                            </div>
                        ` : ''}
                    </div>
                    
                    ${event.tool_parameters ? `
                        <div class="parameters-section">
                            <div class="structured-view-header">
                                <h4>⚙️ Parameters</h4>
                            </div>
                            <div class="structured-data">
                                <pre style="white-space: pre-wrap; font-family: monospace; font-size: 12px; line-height: 1.4;">${JSON.stringify(event.tool_parameters, null, 2)}</pre>
                            </div>
                        </div>
                    ` : ''}
                </div>
            </div>
        `;

        // Use the new dual-pane approach for tools
        if (this.moduleViewer.dataContainer) {
            this.moduleViewer.dataContainer.innerHTML = content;
        }
        if (this.moduleViewer.jsonContainer && event) {
            this.moduleViewer.jsonContainer.innerHTML = `<pre>${JSON.stringify(event, null, 2)}</pre>`;
        }
        
        // Also show the event details in EventViewer
        if (eventIndex >= 0) {
            this.eventViewer.showEventDetails(eventIndex);
        }
    }

    /**
     * Show tool call details in module viewer with combined pre/post data
     */
    showToolCallDetails(toolCallKey) {
        const toolCall = this.toolCalls.get(toolCallKey);
        if (!toolCall) return;

        const toolName = toolCall.tool_name || 'Unknown Tool';
        const agentName = toolCall.agent_type || 'PM';
        const timestamp = new Date(toolCall.timestamp).toLocaleString();

        // Extract information from pre and post events
        const preEvent = toolCall.pre_event;
        const postEvent = toolCall.post_event;
        
        // Get parameters from pre-event
        const parameters = preEvent?.tool_parameters || {};
        const target = preEvent ? this.extractToolTarget(toolName, parameters, parameters) : 'Unknown target';
        
        // Get execution results from post-event
        const duration = toolCall.duration_ms ? `${toolCall.duration_ms}ms` : '-';
        const success = toolCall.success !== undefined ? toolCall.success : null;
        const exitCode = toolCall.exit_code !== undefined ? toolCall.exit_code : null;
        // Format result summary properly if it's an object
        let resultSummary = toolCall.result_summary || 'No summary available';
        let formattedResultSummary = '';
        
        if (typeof resultSummary === 'object' && resultSummary !== null) {
            // Format the result summary object into human-readable text
            const parts = [];
            
            if (resultSummary.exit_code !== undefined) {
                parts.push(`Exit Code: ${resultSummary.exit_code}`);
            }
            
            if (resultSummary.has_output !== undefined) {
                parts.push(`Has Output: ${resultSummary.has_output ? 'Yes' : 'No'}`);
            }
            
            if (resultSummary.has_error !== undefined) {
                parts.push(`Has Error: ${resultSummary.has_error ? 'Yes' : 'No'}`);
            }
            
            if (resultSummary.output_lines !== undefined) {
                parts.push(`Output Lines: ${resultSummary.output_lines}`);
            }
            
            if (resultSummary.output_preview) {
                parts.push(`Output Preview: ${resultSummary.output_preview}`);
            }
            
            if (resultSummary.error_preview) {
                parts.push(`Error Preview: ${resultSummary.error_preview}`);
            }
            
            formattedResultSummary = parts.join('\n');
        } else {
            formattedResultSummary = String(resultSummary);
        }

        // Status information
        let statusIcon = '⏳';
        let statusText = 'Running...';
        let statusClass = 'tool-running';
        
        if (postEvent) {
            if (success === true) {
                statusIcon = '✅';
                statusText = 'Success';
                statusClass = 'tool-success';
            } else if (success === false) {
                statusIcon = '❌';
                statusText = 'Failed';
                statusClass = 'tool-failure';
            } else {
                statusIcon = '⏳';
                statusText = 'Completed';
                statusClass = 'tool-completed';
            }
        }

        const content = `
            <div class="structured-view-section">
                <div class="structured-view-header">
                    <h4>🔧 Tool Call Details</h4>
                </div>
                <div class="tool-call-details">
                    <div class="tool-call-info ${statusClass}">
                        <div class="structured-field">
                            <strong>Tool Name:</strong> ${toolName}
                        </div>
                        <div class="structured-field">
                            <strong>Agent:</strong> ${agentName}
                        </div>
                        <div class="structured-field">
                            <strong>Status:</strong> ${statusIcon} ${statusText}
                        </div>
                        <div class="structured-field">
                            <strong>Target:</strong> ${target}
                        </div>
                        <div class="structured-field">
                            <strong>Started:</strong> ${timestamp}
                        </div>
                        <div class="structured-field">
                            <strong>Duration:</strong> ${duration}
                        </div>
                        ${success !== null ? `
                            <div class="structured-field">
                                <strong>Success:</strong> ${success}
                            </div>
                        ` : ''}
                        ${exitCode !== null ? `
                            <div class="structured-field">
                                <strong>Exit Code:</strong> ${exitCode}
                            </div>
                        ` : ''}
                        ${toolCall.session_id ? `
                            <div class="structured-field">
                                <strong>Session ID:</strong> ${toolCall.session_id}
                            </div>
                        ` : ''}
                    </div>
                    
                    ${formattedResultSummary && formattedResultSummary !== 'No summary available' ? `
                        <div class="result-section">
                            <div class="structured-view-header">
                                <h4>📊 Result Summary</h4>
                            </div>
                            <div class="structured-data">
                                <div class="result-summary" style="white-space: pre-wrap; max-height: 200px; overflow-y: auto; padding: 10px; background: #f8fafc; border-radius: 6px; font-family: monospace; font-size: 12px; line-height: 1.4;">
                                    ${formattedResultSummary}
                                </div>
                                ${typeof resultSummary === 'object' && resultSummary !== null ? `
                                    <div class="result-summary-json" style="white-space: pre-wrap; max-height: 200px; overflow-y: auto; padding: 10px; background: #f0f9ff; border-radius: 6px; font-family: monospace; font-size: 11px; line-height: 1.3; margin-top: 10px;">
                                        <h5 style="margin: 0 0 8px 0; font-size: 11px; color: #4a5568;">Raw JSON:</h5>
                                        ${JSON.stringify(resultSummary, null, 2)}
                                    </div>
                                ` : ''}
                            </div>
                        </div>
                    ` : ''}
                    
                    ${toolName === 'TodoWrite' && parameters.todos ? `
                        <div class="todos-section">
                            <div class="todos-list">
                                ${parameters.todos.map(todo => {
                                    const statusIcon = {
                                        'pending': '⏳',
                                        'in_progress': '🔄',
                                        'completed': '✅'
                                    }[todo.status] || '❓';
                                    
                                    const priorityColor = {
                                        'high': '#dc2626',
                                        'medium': '#f59e0b',
                                        'low': '#10b981'
                                    }[todo.priority] || '#6b7280';
                                    
                                    return `
                                        <div class="todo-item" style="padding: 8px; margin: 4px 0; border-left: 3px solid ${priorityColor}; background: #f8fafc; border-radius: 4px;">
                                            <div style="display: flex; align-items: center; gap: 8px;">
                                                <span style="font-size: 16px;">${statusIcon}</span>
                                                <span style="font-weight: 500; color: #374151;">${todo.content}</span>
                                                <span style="font-size: 11px; color: ${priorityColor}; text-transform: uppercase; font-weight: 600; margin-left: auto;">${todo.priority}</span>
                                            </div>
                                        </div>
                                    `;
                                }).join('')}
                            </div>
                        </div>
                    ` : ''}
                    
                    ${Object.keys(parameters).length > 0 && toolName !== 'TodoWrite' ? `
                        <div class="parameters-section">
                            <div class="structured-view-header">
                                <h4>⚙️ Parameters</h4>
                            </div>
                            <div class="structured-data">
                                <pre style="white-space: pre-wrap; font-family: monospace; font-size: 12px; line-height: 1.4;">${JSON.stringify(parameters, null, 2)}</pre>
                            </div>
                        </div>
                    ` : ''}
                    
                    <div class="raw-data-section">
                        <div class="structured-view-header">
                            <h4>🔧 JSON Event Data</h4>
                        </div>
                        <div class="structured-data">
                            <div style="margin-bottom: 15px;">
                                <strong>Pre-execution Event:</strong>
                                <pre style="white-space: pre-wrap; font-family: monospace; font-size: 11px; line-height: 1.3; background: #f0f9ff; padding: 8px; border-radius: 4px; max-height: 300px; overflow-y: auto;">${preEvent ? JSON.stringify(preEvent, null, 2) : 'No pre-event data'}</pre>
                            </div>
                            <div>
                                <strong>Post-execution Event:</strong>
                                <pre style="white-space: pre-wrap; font-family: monospace; font-size: 11px; line-height: 1.3; background: #f0f9ff; padding: 8px; border-radius: 4px; max-height: 300px; overflow-y: auto;">${postEvent ? JSON.stringify(postEvent, null, 2) : 'No post-event data'}</pre>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Special handling for TodoWrite - show only checklist with standard header
        if (toolName === 'TodoWrite' && parameters.todos) {
            // Create contextual header matching module-viewer pattern
            const contextualHeader = `
                <div class="contextual-header">
                    <h3 class="contextual-header-text">TodoWrite: ${agentName} ${this.formatTimestamp(toolCall.timestamp)}</h3>
                </div>
            `;
            
            const todoContent = `
                <div class="todo-checklist">
                    ${parameters.todos.map(todo => {
                        const statusIcon = {
                            'pending': '⏳',
                            'in_progress': '🔄',
                            'completed': '✅'
                        }[todo.status] || '❓';
                        
                        const priorityIcon = {
                            'high': '🔴',
                            'medium': '🟡',
                            'low': '🟢'
                        }[todo.priority] || '🟡';
                        
                        return `
                            <div class="todo-item todo-${todo.status || 'pending'}">
                                <span class="todo-status">${statusIcon}</span>
                                <span class="todo-content">${todo.content || 'No content'}</span>
                                <span class="todo-priority priority-${todo.priority || 'medium'}">${priorityIcon}</span>
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
            
            if (this.moduleViewer.dataContainer) {
                this.moduleViewer.dataContainer.innerHTML = contextualHeader + todoContent;
            }
            if (this.moduleViewer.jsonContainer) {
                const toolCallData = {
                    toolCall: toolCall,
                    preEvent: preEvent,
                    postEvent: postEvent
                };
                this.moduleViewer.jsonContainer.innerHTML = `<pre>${JSON.stringify(toolCallData, null, 2)}</pre>`;
            }
        } else {
            // For other tools, use the module viewer's ingest method with pre-event
            if (this.moduleViewer && preEvent) {
                this.moduleViewer.ingest(preEvent);
            }
        }
    }



    /**
     * Show detailed file operations in module viewer
     */
    showFileDetails(filePath) {
        const fileData = this.fileOperations.get(filePath);
        if (!fileData) return;

        // Filter operations by selected session if applicable
        let operations = fileData.operations;
        if (this.selectedSessionId) {
            operations = operations.filter(op => op.sessionId === this.selectedSessionId);
            if (operations.length === 0) {
                // No operations from this session
                this.moduleViewer.showErrorMessage(
                    'No Operations in Selected Session',
                    `This file has no operations from the selected session.`
                );
                return;
            }
        }

        // Get file name from path for header
        const fileName = filePath.split('/').pop() || filePath;
        const lastOp = operations[operations.length - 1];
        const headerTimestamp = this.formatTimestamp(lastOp.timestamp);
        
        // Create contextual header matching module-viewer pattern
        const contextualHeader = `
            <div class="contextual-header">
                <h3 class="contextual-header-text">File: ${fileName} ${headerTimestamp}</h3>
            </div>
        `;

        const content = `
            <div class="structured-view-section">
                <div class="file-details">
                    <div class="file-path-display">
                        <strong>Full Path:</strong> ${filePath}
                    </div>
                    <div class="operations-list">
                        ${operations.map(op => `
                            <div class="operation-item">
                                <div class="operation-header">
                                    <span class="operation-icon">${this.getOperationIcon(op.operation)}</span>
                                    <span class="operation-type">${op.operation}</span>
                                    <span class="operation-timestamp">${new Date(op.timestamp).toLocaleString()}</span>
                                    ${(['edit', 'write'].includes(op.operation)) ? `
                                        <span class="git-diff-icon" 
                                              onclick="showGitDiffModal('${filePath}', '${op.timestamp}')"
                                              title="View git diff for this file operation"
                                              style="margin-left: 8px; cursor: pointer; font-size: 16px;">
                                            📋
                                        </span>
                                    ` : ''}
                                </div>
                                <div class="operation-details">
                                    <strong>Agent:</strong> ${op.agent}<br>
                                    <strong>Session:</strong> ${op.sessionId ? op.sessionId.substring(0, 8) + '...' : 'Unknown'}
                                    ${op.details ? `<br><strong>Details:</strong> ${op.details}` : ''}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        `;

        // Use the new dual-pane approach for file details with standard header
        if (this.moduleViewer.dataContainer) {
            this.moduleViewer.dataContainer.innerHTML = contextualHeader + content;
        }
        if (this.moduleViewer.jsonContainer) {
            // Show the file data with operations
            this.moduleViewer.jsonContainer.innerHTML = `<pre>${JSON.stringify(fileData, null, 2)}</pre>`;
        }
    }

    /**
     * Update file operations from events
     */
    updateFileOperations(events) {
        // Clear existing data
        this.fileOperations.clear();

        console.log('updateFileOperations - processing', events.length, 'events');

        // Group events by session and timestamp to match pre/post pairs
        const eventPairs = new Map(); // Key: session_id + timestamp + tool_name
        let fileOperationCount = 0;
        
        // First pass: collect all tool events and group them
        events.forEach((event, index) => {
            const isFileOp = this.isFileOperation(event);
            if (isFileOp) fileOperationCount++;
            
            if (index < 5) { // Debug first 5 events with more detail
                console.log(`Event ${index}:`, {
                    type: event.type,
                    subtype: event.subtype,
                    tool_name: event.tool_name,
                    tool_parameters: event.tool_parameters,
                    isFileOp: isFileOp
                });
            }
            
            if (isFileOp) {
                const toolName = event.tool_name;
                const sessionId = event.session_id || 'unknown';
                const eventKey = `${sessionId}_${toolName}_${Math.floor(new Date(event.timestamp).getTime() / 1000)}`; // Group by second
                
                if (!eventPairs.has(eventKey)) {
                    eventPairs.set(eventKey, {
                        pre_event: null,
                        post_event: null,
                        tool_name: toolName,
                        session_id: sessionId
                    });
                }
                
                const pair = eventPairs.get(eventKey);
                if (event.subtype === 'pre_tool' || event.type === 'hook' && !event.subtype.includes('post')) {
                    pair.pre_event = event;
                } else if (event.subtype === 'post_tool' || event.subtype.includes('post')) {
                    pair.post_event = event;
                } else {
                    // For events without clear pre/post distinction, treat as both
                    pair.pre_event = event;
                    pair.post_event = event;
                }
            }
        });
        
        console.log('updateFileOperations - found', fileOperationCount, 'file operations in', eventPairs.size, 'event pairs');
        
        // Second pass: extract file paths and operations from paired events
        eventPairs.forEach((pair, key) => {
            const filePath = this.extractFilePathFromPair(pair);
            
            if (filePath) {
                console.log('File operation detected for:', filePath, 'from pair:', key);
                
                if (!this.fileOperations.has(filePath)) {
                    this.fileOperations.set(filePath, {
                        path: filePath,
                        operations: [],
                        lastOperation: null
                    });
                }

                const fileData = this.fileOperations.get(filePath);
                const operation = this.getFileOperationFromPair(pair);
                const timestamp = pair.post_event?.timestamp || pair.pre_event?.timestamp;
                
                const agentInfo = this.extractAgentFromPair(pair);
                const workingDirectory = this.extractWorkingDirectoryFromPair(pair);
                
                fileData.operations.push({
                    operation: operation,
                    timestamp: timestamp,
                    agent: agentInfo.name,
                    confidence: agentInfo.confidence,
                    sessionId: pair.session_id,
                    details: this.getFileOperationDetailsFromPair(pair),
                    workingDirectory: workingDirectory
                });
                fileData.lastOperation = timestamp;
            } else {
                console.log('No file path found for pair:', key, pair);
            }
        });
        
        console.log('updateFileOperations - final result:', this.fileOperations.size, 'file operations');
        if (this.fileOperations.size > 0) {
            console.log('File operations map:', Array.from(this.fileOperations.entries()));
        }
    }

    /**
     * Update tool calls from events - pairs pre/post tool events into complete tool calls
     */
    updateToolCalls(events) {
        // Clear existing data
        this.toolCalls.clear();

        console.log('updateToolCalls - processing', events.length, 'events');

        // Group events by session and timestamp to match pre/post pairs
        const toolCallPairs = new Map(); // Key: session_id + timestamp + tool_name
        let toolOperationCount = 0;
        
        // First pass: collect all tool events and group them
        events.forEach((event, index) => {
            const isToolOp = this.isToolOperation(event);
            if (isToolOp) toolOperationCount++;
            
            if (index < 5) { // Debug first 5 events with more detail
                console.log(`Tool Event ${index}:`, {
                    type: event.type,
                    subtype: event.subtype,
                    tool_name: event.tool_name,
                    tool_parameters: event.tool_parameters,
                    isToolOp: isToolOp
                });
            }
            
            if (isToolOp) {
                const toolName = event.tool_name;
                const sessionId = event.session_id || 'unknown';
                const eventKey = `${sessionId}_${toolName}_${Math.floor(new Date(event.timestamp).getTime() / 1000)}`; // Group by second
                
                if (!toolCallPairs.has(eventKey)) {
                    toolCallPairs.set(eventKey, {
                        pre_event: null,
                        post_event: null,
                        tool_name: toolName,
                        session_id: sessionId,
                        operation_type: null,
                        timestamp: null,
                        duration_ms: null,
                        success: null,
                        exit_code: null,
                        result_summary: null,
                        agent_type: null
                    });
                }
                
                const pair = toolCallPairs.get(eventKey);
                if (event.subtype === 'pre_tool' || (event.type === 'hook' && !event.subtype.includes('post'))) {
                    pair.pre_event = event;
                    pair.timestamp = event.timestamp;
                    pair.operation_type = event.operation_type || 'tool_execution';
                    pair.agent_type = event.agent_type || event.subagent_type || 'PM';
                } else if (event.subtype === 'post_tool' || event.subtype.includes('post')) {
                    pair.post_event = event;
                    pair.duration_ms = event.duration_ms;
                    pair.success = event.success;
                    pair.exit_code = event.exit_code;
                    pair.result_summary = event.result_summary;
                    if (!pair.agent_type) {
                        pair.agent_type = event.agent_type || event.subagent_type || 'PM';
                    }
                } else {
                    // For events without clear pre/post distinction, treat as both
                    pair.pre_event = event;
                    pair.post_event = event;
                    pair.timestamp = event.timestamp;
                    pair.agent_type = event.agent_type || event.subagent_type || 'PM';
                }
            }
        });
        
        console.log('updateToolCalls - found', toolOperationCount, 'tool operations in', toolCallPairs.size, 'tool call pairs');
        
        // Second pass: store complete tool calls
        toolCallPairs.forEach((pair, key) => {
            // Ensure we have at least a pre_event or post_event
            if (pair.pre_event || pair.post_event) {
                console.log('Tool call detected for:', pair.tool_name, 'from pair:', key);
                this.toolCalls.set(key, pair);
            } else {
                console.log('No valid tool call found for pair:', key, pair);
            }
        });
        
        console.log('updateToolCalls - final result:', this.toolCalls.size, 'tool calls');
        if (this.toolCalls.size > 0) {
            console.log('Tool calls map:', Array.from(this.toolCalls.entries()));
        }
    }

    /**
     * Check if event is a tool operation
     */
    isToolOperation(event) {
        const type = event.type || '';
        const subtype = event.subtype || '';
        
        // Check for hook events with tool subtypes
        const isHookToolEvent = type === 'hook' && (
            subtype.includes('tool') || 
            subtype.includes('pre_') || 
            subtype.includes('post_')
        );
        
        // Events with tool_name
        const hasToolName = event.tool_name;
        
        // Events with tools array (multiple tools)
        const hasToolsArray = event.tools && Array.isArray(event.tools);
        
        // Legacy hook events with tool patterns (backward compatibility)
        const isLegacyHookEvent = type.startsWith('hook.') && (
            type.includes('tool') || 
            type.includes('pre') || 
            type.includes('post')
        );
        
        return isHookToolEvent || hasToolName || hasToolsArray || isLegacyHookEvent;
    }

    /**
     * Check if event is a file operation
     */
    isFileOperation(event) {
        const toolName = event.tool_name;
        const fileTools = ['Read', 'Write', 'Edit', 'MultiEdit', 'Glob', 'LS', 'NotebookRead', 'NotebookEdit', 'Grep'];
        
        // Check for direct tool name match
        if (fileTools.includes(toolName)) {
            console.log('isFileOperation - direct tool match:', toolName);
            return true;
        }
        
        // Check for hook events that involve file tools (updated for new structure)
        const type = event.type || '';
        const subtype = event.subtype || '';
        
        // Check both legacy format and new format
        const isHookEvent = type === 'hook' || type.startsWith('hook.');
        
        if (isHookEvent) {
            // Check if tool_name indicates file operation
            if (fileTools.includes(event.tool_name)) {
                console.log('isFileOperation - hook tool match:', event.tool_name);
                return true;
            }
            
            // Check if parameters suggest file operation
            const params = event.tool_parameters || {};
            const hasFileParams = !!(params.file_path || params.path || params.notebook_path || params.pattern);
            
            // Also check top-level event for file parameters (flat structure)
            const hasDirectFileParams = !!(event.file_path || event.path || event.notebook_path || event.pattern);
            
            const hasAnyFileParams = hasFileParams || hasDirectFileParams;
            if (hasAnyFileParams) {
                console.log('isFileOperation - file params match:', { hasFileParams, hasDirectFileParams, params, directParams: { file_path: event.file_path, path: event.path } });
            }
            
            return hasAnyFileParams;
        }
        
        return false;
    }

    /**
     * Extract file path from event
     */
    extractFilePath(event) {
        // Check tool_parameters first
        const params = event.tool_parameters;
        if (params) {
            if (params.file_path) return params.file_path;
            if (params.path) return params.path;
            if (params.notebook_path) return params.notebook_path;
        }
        
        // Check top-level event (flat structure)
        if (event.file_path) return event.file_path;
        if (event.path) return event.path;
        if (event.notebook_path) return event.notebook_path;
        
        // Check tool_input if available (sometimes path is here)
        if (event.tool_input) {
            if (event.tool_input.file_path) return event.tool_input.file_path;
            if (event.tool_input.path) return event.tool_input.path;
            if (event.tool_input.notebook_path) return event.tool_input.notebook_path;
        }
        
        // Check result/output if available (sometimes path is in result)
        if (event.result) {
            if (event.result.file_path) return event.result.file_path;
            if (event.result.path) return event.result.path;
        }
        
        return null;
    }
    
    /**
     * Extract file path from paired pre/post events
     */
    extractFilePathFromPair(pair) {
        // Try pre_event first, then post_event
        const preEvent = pair.pre_event;
        const postEvent = pair.post_event;
        
        if (preEvent) {
            const prePath = this.extractFilePath(preEvent);
            if (prePath) return prePath;
        }
        
        if (postEvent) {
            const postPath = this.extractFilePath(postEvent);
            if (postPath) return postPath;
        }
        
        return null;
    }

    /**
     * Get file operation type
     */
    getFileOperation(event) {
        const toolName = event.tool_name;
        const operationMap = {
            'Read': 'read',
            'Write': 'write',
            'Edit': 'edit',
            'MultiEdit': 'edit',
            'Glob': 'search',
            'LS': 'list',
            'NotebookRead': 'read',
            'NotebookEdit': 'edit',
            'Grep': 'search'
        };
        
        return operationMap[toolName] || 'operation';
    }
    
    /**
     * Get file operation type from paired events
     */
    getFileOperationFromPair(pair) {
        const toolName = pair.tool_name;
        const operationMap = {
            'Read': 'read',
            'Write': 'write',
            'Edit': 'edit',
            'MultiEdit': 'edit',
            'Glob': 'search',
            'LS': 'list',
            'NotebookRead': 'read',
            'NotebookEdit': 'edit',
            'Grep': 'search'
        };
        
        return operationMap[toolName] || 'operation';
    }
    
    /**
     * Extract agent from paired events using inference
     */
    extractAgentFromPair(pair) {
        // Try to get inference from either event
        const preEvent = pair.pre_event;
        const postEvent = pair.post_event;
        
        if (preEvent) {
            const eventIndex = this.eventViewer.events.indexOf(preEvent);
            const inference = this.getInferredAgent(eventIndex);
            if (inference) {
                return {
                    name: inference.agentName,
                    confidence: inference.confidence
                };
            }
        }
        
        if (postEvent) {
            const eventIndex = this.eventViewer.events.indexOf(postEvent);
            const inference = this.getInferredAgent(eventIndex);
            if (inference) {
                return {
                    name: inference.agentName,
                    confidence: inference.confidence
                };
            }
        }
        
        // Fallback to legacy logic
        const preAgent = preEvent?.agent_type || preEvent?.subagent_type;
        const postAgent = postEvent?.agent_type || postEvent?.subagent_type;
        
        // Prefer non-'main' and non-'unknown' agents
        if (preAgent && preAgent !== 'main' && preAgent !== 'unknown') {
            return { name: preAgent, confidence: 'legacy' };
        }
        if (postAgent && postAgent !== 'main' && postAgent !== 'unknown') {
            return { name: postAgent, confidence: 'legacy' };
        }
        
        // Fallback to any agent
        const agentName = preAgent || postAgent || 'PM';
        return { name: agentName, confidence: 'fallback' };
    }

    /**
     * Extract working directory from event pair
     */
    extractWorkingDirectoryFromPair(pair) {
        // Try to get working directory from either event's data
        const preEvent = pair.pre_event;
        const postEvent = pair.post_event;
        
        // Check pre_event first
        if (preEvent?.data?.working_directory) {
            return preEvent.data.working_directory;
        }
        
        // Check post_event
        if (postEvent?.data?.working_directory) {
            return postEvent.data.working_directory;
        }
        
        // Check tool_parameters for working directory
        if (preEvent?.tool_parameters?.working_dir) {
            return preEvent.tool_parameters.working_dir;
        }
        
        if (postEvent?.tool_parameters?.working_dir) {
            return postEvent.tool_parameters.working_dir;
        }
        
        // Fallback to null (will use default behavior in showGitDiffModal)
        return null;
    }

    /**
     * Get file operation details
     */
    getFileOperationDetails(event) {
        const toolName = event.tool_name;
        const params = event.tool_parameters;
        
        switch (toolName) {
            case 'Edit':
            case 'MultiEdit':
                return `Modified content`;
            case 'Write':
                return `Created/updated file`;
            case 'Read':
                return `Read file content`;
            case 'NotebookRead':
                return `Read notebook content`;
            case 'NotebookEdit':
                return `Modified notebook`;
            case 'Glob':
                return `Searched pattern: ${params?.pattern || 'unknown'}`;
            case 'Grep':
                return `Searched pattern: ${params?.pattern || 'unknown'}`;
            case 'LS':
                return `Listed directory`;
            default:
                return '';
        }
    }
    
    /**
     * Get file operation details from paired events
     */
    getFileOperationDetailsFromPair(pair) {
        const toolName = pair.tool_name;
        
        // Get parameters from either event
        const preParams = pair.pre_event?.tool_parameters || {};
        const postParams = pair.post_event?.tool_parameters || {};
        const params = { ...preParams, ...postParams };
        
        switch (toolName) {
            case 'Edit':
            case 'MultiEdit':
                return `Modified content`;
            case 'Write':
                return `Created/updated file`;
            case 'Read':
                return `Read file content`;
            case 'NotebookRead':
                return `Read notebook content`;
            case 'NotebookEdit':
                return `Modified notebook`;
            case 'Glob':
                return `Searched pattern: ${params?.pattern || 'unknown'}`;
            case 'Grep':
                return `Searched pattern: ${params?.pattern || 'unknown'}`;
            case 'LS':
                return `Listed directory`;
            default:
                return '';
        }
    }

    /**
     * Get icon for file operations - shows combined icons for read+write
     */
    getFileOperationIcon(operations) {
        // Check for notebook operations first
        const hasNotebook = operations.some(op => op.details && (op.details.includes('notebook') || op.details.includes('Notebook')));
        if (hasNotebook) return '📓';
        
        const hasWrite = operations.some(op => ['write', 'edit'].includes(op.operation));
        const hasRead = operations.some(op => op.operation === 'read');
        const hasSearch = operations.some(op => op.operation === 'search');
        const hasList = operations.some(op => op.operation === 'list');
        
        // Show both icons for read+write combinations
        if (hasWrite && hasRead) return '📖✏️'; // Both read and write
        if (hasWrite) return '✏️'; // Write only
        if (hasRead) return '📖'; // Read only
        if (hasSearch) return '🔍'; // Search only
        if (hasList) return '📋'; // List only
        return '📄'; // Default
    }

    /**
     * Get icon for specific operation
     */
    getOperationIcon(operation) {
        const icons = {
            read: '📖',
            write: '📝',
            edit: '✏️',
            search: '🔍',
            list: '📋'
        };
        return icons[operation] || '📄';
    }

    /**
     * Format timestamp for display
     * @param {string|number} timestamp - Timestamp to format
     * @returns {string} Formatted time
     */
    formatTimestamp(timestamp) {
        if (!timestamp) return 'Unknown time';
        
        try {
            const date = new Date(timestamp);
            return date.toLocaleTimeString('en-US', {
                hour: 'numeric',
                minute: '2-digit',
                second: '2-digit',
                hour12: true
            });
        } catch (e) {
            return 'Invalid time';
        }
    }

    /**
     * Get relative file path for display
     */
    getRelativeFilePath(filePath) {
        // Try to make path relative to common base paths
        const commonPaths = [
            '/Users/masa/Projects/claude-mpm/',
            '.'
        ];
        
        for (const basePath of commonPaths) {
            if (filePath.startsWith(basePath)) {
                return filePath.substring(basePath.length).replace(/^\//, '');
            }
        }
        
        // If no common path found, show last 2-3 path segments
        const parts = filePath.split('/');
        if (parts.length > 3) {
            return '.../' + parts.slice(-2).join('/');
        }
        
        return filePath;
    }

    /**
     * Apply agents tab filtering
     */
    applyAgentsFilters(events) {
        const searchInput = document.getElementById('agents-search-input');
        const typeFilter = document.getElementById('agents-type-filter');
        
        const searchText = searchInput ? searchInput.value.toLowerCase() : '';
        const typeValue = typeFilter ? typeFilter.value : '';
        
        return events.filter(event => {
            // Search filter
            if (searchText) {
                const searchableText = [
                    event.subagent_type || '',
                    event.agent_type || '',
                    event.name || '',
                    event.type || '',
                    event.subtype || ''
                ].join(' ').toLowerCase();
                
                if (!searchableText.includes(searchText)) {
                    return false;
                }
            }
            
            // Type filter
            if (typeValue) {
                const agentType = event.subagent_type || event.agent_type || 'unknown';
                if (!agentType.toLowerCase().includes(typeValue.toLowerCase())) {
                    return false;
                }
            }
            
            return true;
        });
    }

    /**
     * Apply tools tab filtering
     */
    applyToolsFilters(events) {
        const searchInput = document.getElementById('tools-search-input');
        const typeFilter = document.getElementById('tools-type-filter');
        
        const searchText = searchInput ? searchInput.value.toLowerCase() : '';
        const typeValue = typeFilter ? typeFilter.value : '';
        
        return events.filter(event => {
            // Search filter
            if (searchText) {
                const searchableText = [
                    event.tool_name || '',
                    event.agent_type || '',
                    event.type || '',
                    event.subtype || ''
                ].join(' ').toLowerCase();
                
                if (!searchableText.includes(searchText)) {
                    return false;
                }
            }
            
            // Type filter
            if (typeValue) {
                const toolName = event.tool_name || '';
                if (toolName !== typeValue) {
                    return false;
                }
            }
            
            return true;
        });
    }

    /**
     * Apply tools tab filtering for tool calls
     */
    applyToolCallFilters(toolCallsArray) {
        const searchInput = document.getElementById('tools-search-input');
        const typeFilter = document.getElementById('tools-type-filter');
        
        const searchText = searchInput ? searchInput.value.toLowerCase() : '';
        const typeValue = typeFilter ? typeFilter.value : '';
        
        return toolCallsArray.filter(([key, toolCall]) => {
            // Search filter
            if (searchText) {
                const searchableText = [
                    toolCall.tool_name || '',
                    toolCall.agent_type || '',
                    'tool_call'
                ].join(' ').toLowerCase();
                
                if (!searchableText.includes(searchText)) {
                    return false;
                }
            }
            
            // Type filter
            if (typeValue) {
                const toolName = toolCall.tool_name || '';
                if (toolName !== typeValue) {
                    return false;
                }
            }
            
            return true;
        });
    }

    /**
     * Apply files tab filtering
     */
    applyFilesFilters(fileOperations) {
        const searchInput = document.getElementById('files-search-input');
        const typeFilter = document.getElementById('files-type-filter');
        
        const searchText = searchInput ? searchInput.value.toLowerCase() : '';
        const typeValue = typeFilter ? typeFilter.value : '';
        
        return fileOperations.filter(([filePath, fileData]) => {
            // Session filter - filter operations within each file
            if (this.selectedSessionId) {
                // Filter operations for this file by session
                const sessionOperations = fileData.operations.filter(op => 
                    op.sessionId === this.selectedSessionId
                );
                
                // If no operations from this session, exclude the file
                if (sessionOperations.length === 0) {
                    return false;
                }
                
                // Update the fileData to only include session-specific operations
                // (Note: This creates a filtered view without modifying the original)
                fileData = {
                    ...fileData,
                    operations: sessionOperations,
                    lastOperation: sessionOperations[sessionOperations.length - 1]?.timestamp || fileData.lastOperation
                };
            }
            
            // Search filter
            if (searchText) {
                const searchableText = [
                    filePath,
                    ...fileData.operations.map(op => op.operation),
                    ...fileData.operations.map(op => op.agent)
                ].join(' ').toLowerCase();
                
                if (!searchableText.includes(searchText)) {
                    return false;
                }
            }
            
            // Type filter
            if (typeValue) {
                const hasOperationType = fileData.operations.some(op => op.operation === typeValue);
                if (!hasOperationType) {
                    return false;
                }
            }
            
            return true;
        });
    }

    /**
     * Extract operation from event type
     */
    extractOperation(eventType) {
        if (!eventType) return 'unknown';
        
        if (eventType.includes('pre_')) return 'pre-' + eventType.split('pre_')[1];
        if (eventType.includes('post_')) return 'post-' + eventType.split('post_')[1];
        if (eventType.includes('delegation')) return 'delegation';
        if (eventType.includes('start')) return 'started';
        if (eventType.includes('end')) return 'ended';
        
        // Extract operation from type like "hook.pre_tool" -> "pre_tool"
        const parts = eventType.split('.');
        return parts.length > 1 ? parts[1] : eventType;
    }

    /**
     * Extract tool name from hook event type
     */
    extractToolFromHook(eventType) {
        if (!eventType || !eventType.startsWith('hook.')) return null;
        
        // For hook events, the tool name might be in the data
        return 'Tool'; // Fallback - actual tool name should be in event.tool_name
    }

    /**
     * Extract tool name from subtype
     */
    extractToolFromSubtype(subtype) {
        if (!subtype) return null;
        
        // Try to extract tool name from subtype patterns like 'pre_tool' or 'post_tool'
        if (subtype.includes('tool')) {
            return 'Tool'; // Generic fallback
        }
        
        return null;
    }

    /**
     * Extract tool target for display
     */
    extractToolTarget(toolName, params, toolParameters) {
        const allParams = { ...params, ...toolParameters };
        
        switch (toolName) {
            case 'Read':
            case 'Write':
            case 'Edit':
            case 'MultiEdit':
                return allParams.file_path || 'Unknown file';
            case 'Bash':
                return allParams.command || 'Unknown command';
            case 'Glob':
                return allParams.pattern || 'Unknown pattern';
            case 'Grep':
                return `"${allParams.pattern || 'unknown'}" in ${allParams.path || 'unknown path'}`;
            case 'LS':
                return allParams.path || 'Unknown path';
            default:
                if (Object.keys(allParams).length > 0) {
                    return JSON.stringify(allParams).substring(0, 50) + '...';
                }
                return 'No parameters';
        }
    }

    /**
     * Get filtered events for a specific tab
     */
    getFilteredEventsForTab(tabName) {
        // Use ALL events, not the EventViewer's filtered events
        // Each tab will apply its own filtering logic
        const events = this.eventViewer.events;
        console.log(`getFilteredEventsForTab(${tabName}) - using RAW events: ${events.length} total`);
        
        // Enhanced debugging for empty events
        if (events.length === 0) {
            console.log(`❌ NO RAW EVENTS available!`);
            console.log('EventViewer state:', {
                total_events: this.eventViewer.events.length,
                filtered_events: this.eventViewer.filteredEvents.length,
                search_filter: this.eventViewer.searchFilter,
                type_filter: this.eventViewer.typeFilter,
                session_filter: this.eventViewer.sessionFilter
            });
        } else {
            console.log('✅ Raw events available for', tabName, '- sample:', events[0]);
            console.log('EventViewer filters (IGNORED for tabs):', {
                search_filter: this.eventViewer.searchFilter,
                type_filter: this.eventViewer.typeFilter,
                session_filter: this.eventViewer.sessionFilter
            });
        }
        
        return events;
    }

    /**
     * Scroll a list container to the bottom
     * @param {string} listId - The ID of the list container element
     */
    scrollListToBottom(listId) {
        console.log(`[DEBUG] scrollListToBottom called with listId: ${listId}`);
        
        // Use setTimeout to ensure DOM updates are completed
        setTimeout(() => {
            const listElement = document.getElementById(listId);
            console.log(`[DEBUG] Element found for ${listId}:`, listElement);
            
            if (listElement) {
                const scrollHeight = listElement.scrollHeight;
                const clientHeight = listElement.clientHeight;
                const currentScrollTop = listElement.scrollTop;
                const computedStyle = window.getComputedStyle(listElement);
                
                console.log(`[DEBUG] Scroll metrics for ${listId}:`);
                console.log(`  - scrollHeight: ${scrollHeight}`);
                console.log(`  - clientHeight: ${clientHeight}`);
                console.log(`  - currentScrollTop: ${currentScrollTop}`);
                console.log(`  - needsScroll: ${scrollHeight > clientHeight}`);
                console.log(`  - overflowY: ${computedStyle.overflowY}`);
                console.log(`  - height: ${computedStyle.height}`);
                console.log(`  - maxHeight: ${computedStyle.maxHeight}`);
                
                if (scrollHeight > clientHeight) {
                    // Method 1: Direct scrollTop assignment
                    listElement.scrollTop = scrollHeight;
                    console.log(`[DEBUG] Method 1 - Scroll applied to ${listId}, new scrollTop: ${listElement.scrollTop}`);
                    
                    // Method 2: Force layout recalculation and try again if needed
                    if (listElement.scrollTop !== scrollHeight) {
                        console.log(`[DEBUG] Method 1 failed, trying method 2 with layout recalculation`);
                        listElement.offsetHeight; // Force reflow
                        listElement.scrollTop = scrollHeight;
                        console.log(`[DEBUG] Method 2 - new scrollTop: ${listElement.scrollTop}`);
                    }
                    
                    // Method 3: scrollIntoView on last element if still not working
                    if (listElement.scrollTop < scrollHeight - clientHeight - 10) {
                        console.log(`[DEBUG] Methods 1-2 failed, trying method 3 with scrollIntoView`);
                        const lastElement = listElement.lastElementChild;
                        if (lastElement) {
                            lastElement.scrollIntoView({ behavior: 'instant', block: 'end' });
                            console.log(`[DEBUG] Method 3 - scrollIntoView applied on last element`);
                        }
                    }
                } else {
                    console.log(`[DEBUG] No scroll needed for ${listId} - content fits in container`);
                }
            } else {
                console.error(`[DEBUG] Element not found for ID: ${listId}`);
                // Log all elements with similar IDs to help debug
                const allElements = document.querySelectorAll('[id*="list"]');
                console.log(`[DEBUG] Available elements with 'list' in ID:`, Array.from(allElements).map(el => el.id));
            }
        }, 50);  // Small delay to ensure content is rendered
    }

    /**
     * Test scroll functionality - adds dummy content and tries to scroll
     * This is for debugging purposes only
     * @returns {Promise<string>} Status message indicating test results
     */
    async testScrollFunctionality() {
        console.log('[DEBUG] Testing scroll functionality...');
        const results = [];
        const listId = `${this.currentTab}-list`;
        const listElement = document.getElementById(listId);
        
        if (!listElement) {
            const errorMsg = `❌ Could not find list element: ${listId}`;
            console.error(`[DEBUG] ${errorMsg}`);
            
            // Debug: Show available elements
            const allElements = document.querySelectorAll('[id*="list"]');
            const availableIds = Array.from(allElements).map(el => el.id);
            console.log(`[DEBUG] Available elements with 'list' in ID:`, availableIds);
            results.push(errorMsg);
            results.push(`Available list IDs: ${availableIds.join(', ')}`);
            return results.join('\n');
        }
        
        // Get initial state
        const initialScrollTop = listElement.scrollTop;
        const initialScrollHeight = listElement.scrollHeight;
        const initialClientHeight = listElement.clientHeight;
        const computedStyle = window.getComputedStyle(listElement);
        
        results.push(`✅ Found list element: ${listId}`);
        results.push(`📊 Initial state: scrollTop=${initialScrollTop}, scrollHeight=${initialScrollHeight}, clientHeight=${initialClientHeight}`);
        results.push(`🎨 CSS: overflowY=${computedStyle.overflowY}, height=${computedStyle.height}, maxHeight=${computedStyle.maxHeight}`);
        
        // Test 1: Direct scroll without adding content
        console.log('[DEBUG] Test 1: Direct scroll test');
        listElement.scrollTop = 999999;
        await new Promise(resolve => setTimeout(resolve, 50));
        const directScrollResult = listElement.scrollTop;
        results.push(`🧪 Test 1 - Direct scroll to 999999: scrollTop=${directScrollResult} ${directScrollResult > 0 ? '✅' : '❌'}`);
        
        // Reset scroll position
        listElement.scrollTop = 0;
        
        // Test 2: Add visible content to force scrolling need
        console.log('[DEBUG] Test 2: Adding test content');
        const originalContent = listElement.innerHTML;
        
        // Add 15 large test items to definitely exceed container height
        for (let i = 0; i < 15; i++) {
            const testItem = document.createElement('div');
            testItem.className = 'event-item test-scroll-item';
            testItem.style.cssText = 'background: #fffacd !important; border: 2px solid #f39c12 !important; padding: 20px; margin: 10px 0; min-height: 60px;';
            testItem.innerHTML = `<strong>🧪 Test Item ${i + 1}</strong><br>This is a test item to verify scrolling functionality.<br><em>Item height: ~80px total</em>`;
            listElement.appendChild(testItem);
        }
        
        // Force layout recalculation
        listElement.offsetHeight;
        
        const afterContentScrollHeight = listElement.scrollHeight;
        const afterContentClientHeight = listElement.clientHeight;
        const needsScroll = afterContentScrollHeight > afterContentClientHeight;
        
        results.push(`📦 Added 15 test items (expected ~1200px total height)`);
        results.push(`📊 After content: scrollHeight=${afterContentScrollHeight}, clientHeight=${afterContentClientHeight}`);
        results.push(`🔍 Needs scroll: ${needsScroll ? 'YES ✅' : 'NO ❌'}`);
        
        if (needsScroll) {
            // Test 3: Multiple scroll methods
            console.log('[DEBUG] Test 3: Testing different scroll methods');
            
            // Method A: Direct scrollTop assignment
            listElement.scrollTop = afterContentScrollHeight;
            await new Promise(resolve => setTimeout(resolve, 50));
            const methodAResult = listElement.scrollTop;
            const methodASuccess = methodAResult > (afterContentScrollHeight - afterContentClientHeight - 50);
            results.push(`🔧 Method A - scrollTop assignment: ${methodAResult} ${methodASuccess ? '✅' : '❌'}`);
            
            // Method B: scrollIntoView on last element
            const lastElement = listElement.lastElementChild;
            if (lastElement) {
                lastElement.scrollIntoView({ behavior: 'instant', block: 'end' });
                await new Promise(resolve => setTimeout(resolve, 50));
                const methodBResult = listElement.scrollTop;
                const methodBSuccess = methodBResult > (afterContentScrollHeight - afterContentClientHeight - 50);
                results.push(`🔧 Method B - scrollIntoView: ${methodBResult} ${methodBSuccess ? '✅' : '❌'}`);
            }
            
            // Method C: Using the existing scrollListToBottom method
            console.log('[DEBUG] Test 4: Using scrollListToBottom method');
            this.scrollListToBottom(listId);
            await new Promise(resolve => setTimeout(resolve, 100));
            const methodCResult = listElement.scrollTop;
            const methodCSuccess = methodCResult > (afterContentScrollHeight - afterContentClientHeight - 50);
            results.push(`🔧 Method C - scrollListToBottom: ${methodCResult} ${methodCSuccess ? '✅' : '❌'}`);
        }
        
        // Clean up test content after a visible delay
        setTimeout(() => {
            console.log('[DEBUG] Cleaning up test content...');
            const testItems = listElement.querySelectorAll('.test-scroll-item');
            testItems.forEach(item => item.remove());
            results.push(`🧹 Cleaned up ${testItems.length} test items`);
        }, 2000);
        
        const finalResult = results.join('\n');
        console.log('[DEBUG] Test complete. Results:', finalResult);
        return finalResult;
    }

    /**
     * Update connection status in UI
     */
    updateConnectionStatus(status, type) {
        const statusElement = document.getElementById('connection-status');
        if (statusElement) {
            statusElement.textContent = status;
            statusElement.className = `status-badge status-${type}`;
            
            // Update status indicator
            const indicator = statusElement.querySelector('span');
            if (indicator) {
                indicator.textContent = type === 'connected' ? '●' : '●';
            }
        }
    }

    /**
     * Clear all events
     */
    clearEvents() {
        this.eventViewer.clearEvents();
        this.fileOperations.clear();
        this.toolCalls.clear();
        this.agentEvents = [];
        this.renderCurrentTab();
    }

    /**
     * Export current events
     */
    exportEvents() {
        this.eventViewer.exportEvents();
    }

    /**
     * Toggle connection controls visibility
     */
    toggleConnectionControls() {
        const controlsRow = document.getElementById('connection-controls-row');
        const toggleBtn = document.getElementById('connection-toggle-btn');
        
        if (controlsRow && toggleBtn) {
            const isVisible = controlsRow.classList.contains('show');
            
            if (isVisible) {
                controlsRow.classList.remove('show');
                controlsRow.style.display = 'none';
                toggleBtn.textContent = 'Connection Settings';
            } else {
                controlsRow.style.display = 'flex';
                // Use setTimeout to ensure display change is applied before adding animation class
                setTimeout(() => {
                    controlsRow.classList.add('show');
                }, 10);
                toggleBtn.textContent = 'Hide Connection Settings';
            }
        }
    }

    /**
     * Clear current selection
     */
    clearSelection() {
        this.clearCardSelection();
        this.eventViewer.clearSelection();
        this.moduleViewer.clear();
    }
    
    /**
     * Show dialog to change working directory
     */
    showChangeDirDialog() {
        const currentDir = this.currentWorkingDir || this.getDefaultWorkingDir();
        const newDir = prompt('Enter new working directory:', currentDir);
        
        if (newDir && newDir !== currentDir) {
            this.setWorkingDirectory(newDir);
        }
    }
    
    /**
     * Set the working directory for the current session
     * @param {string} dir - New working directory path
     */
    setWorkingDirectory(dir) {
        this.currentWorkingDir = dir;
        
        // Update UI
        const pathElement = document.getElementById('working-dir-path');
        if (pathElement) {
            pathElement.textContent = dir;
            pathElement.title = `Click to change from ${dir}`;
        }
        
        // Update footer (with flag to prevent observer loop)
        const footerDir = document.getElementById('footer-working-dir');
        if (footerDir) {
            this._updatingFooter = true;
            footerDir.textContent = dir;
            // Reset flag after a small delay to ensure observer has processed
            setTimeout(() => {
                this._updatingFooter = false;
            }, 10);
        }
        
        // Store in session data if a session is selected
        const sessionSelect = document.getElementById('session-select');
        if (sessionSelect && sessionSelect.value) {
            const sessionId = sessionSelect.value;
            // Store working directory per session in localStorage
            const sessionDirs = JSON.parse(localStorage.getItem('sessionWorkingDirs') || '{}');
            sessionDirs[sessionId] = dir;
            localStorage.setItem('sessionWorkingDirs', JSON.stringify(sessionDirs));
        }
        
        console.log(`Working directory set to: ${dir}`);
        
        // Request git branch for the new directory
        this.updateGitBranch(dir);
    }
    
    /**
     * Update git branch display for current working directory
     * @param {string} dir - Working directory path
     */
    updateGitBranch(dir) {
        if (!this.socketClient || !this.socketClient.socket || !this.socketClient.socket.connected) {
            // Not connected, set to unknown
            const footerBranch = document.getElementById('footer-git-branch');
            if (footerBranch) {
                footerBranch.textContent = 'Not Connected';
            }
            return;
        }
        
        // Request git branch from server
        this.socketClient.socket.emit('get_git_branch', dir);
    }
    
    /**
     * Get default working directory
     */
    getDefaultWorkingDir() {
        // Try to get from footer first (may be set by server)
        const footerDir = document.getElementById('footer-working-dir');
        if (footerDir && footerDir.textContent && footerDir.textContent !== 'Unknown') {
            return footerDir.textContent;
        }
        // Fallback to hardcoded default
        return '/Users/masa/Projects/claude-mpm';
    }
    
    /**
     * Initialize working directory on dashboard load
     */
    initializeWorkingDirectory() {
        // Check if there's a selected session
        const sessionSelect = document.getElementById('session-select');
        if (sessionSelect && sessionSelect.value) {
            // Load working directory for selected session
            this.loadWorkingDirectoryForSession(sessionSelect.value);
        } else {
            // Set default working directory
            this.setWorkingDirectory(this.getDefaultWorkingDir());
        }
    }
    
    /**
     * Watch footer directory for changes and sync working directory
     */
    watchFooterDirectory() {
        const footerDir = document.getElementById('footer-working-dir');
        if (!footerDir) return;
        
        // Store observer reference for later use
        this.footerDirObserver = new MutationObserver((mutations) => {
            // Skip if we're updating from setWorkingDirectory
            if (this._updatingFooter) return;
            
            mutations.forEach((mutation) => {
                if (mutation.type === 'childList' || mutation.type === 'characterData') {
                    const newDir = footerDir.textContent.trim();
                    // Only update if it's a valid directory path and different from current
                    if (newDir && 
                        newDir !== 'Unknown' && 
                        newDir !== 'Not Connected' &&
                        newDir.startsWith('/') &&
                        newDir !== this.currentWorkingDir) {
                        console.log(`Footer directory changed to: ${newDir}, syncing working directory`);
                        this.setWorkingDirectory(newDir);
                    }
                }
            });
        });
        
        // Start observing
        this.footerDirObserver.observe(footerDir, {
            childList: true,
            characterData: true,
            subtree: true
        });
    }
    
    /**
     * Load working directory for a session
     * @param {string} sessionId - Session ID
     */
    loadWorkingDirectoryForSession(sessionId) {
        if (!sessionId) {
            // No session selected, use default
            this.setWorkingDirectory(this.getDefaultWorkingDir());
            return;
        }
        
        // Load from localStorage
        const sessionDirs = JSON.parse(localStorage.getItem('sessionWorkingDirs') || '{}');
        const dir = sessionDirs[sessionId] || this.getDefaultWorkingDir();
        this.setWorkingDirectory(dir);
    }

    /**
     * Toggle HUD visualizer mode
     */
    toggleHUD() {
        if (!this.isSessionSelected()) {
            console.log('Cannot toggle HUD: No session selected');
            return;
        }

        this.hudMode = !this.hudMode;
        this.updateHUDDisplay();
        
        console.log('HUD mode toggled:', this.hudMode ? 'ON' : 'OFF');
    }

    /**
     * Check if a session is currently selected
     * @returns {boolean} - True if session is selected
     */
    isSessionSelected() {
        const sessionSelect = document.getElementById('session-select');
        return sessionSelect && sessionSelect.value && sessionSelect.value !== '';
    }

    /**
     * Update HUD display based on current mode
     */
    updateHUDDisplay() {
        const eventsWrapper = document.querySelector('.events-wrapper');
        const hudToggleBtn = document.getElementById('hud-toggle-btn');
        
        if (!eventsWrapper || !hudToggleBtn) return;

        if (this.hudMode) {
            // Switch to HUD mode
            eventsWrapper.classList.add('hud-mode');
            hudToggleBtn.classList.add('btn-hud-active');
            hudToggleBtn.textContent = 'Normal View';
            
            // Activate the HUD visualizer (with lazy loading)
            if (this.hudVisualizer) {
                this.hudVisualizer.activate().then(() => {
                    // Process existing events after libraries are loaded
                    this.processExistingEventsForHUD();
                }).catch((error) => {
                    console.error('Failed to activate HUD:', error);
                    // Optionally revert HUD mode on failure
                    // this.hudMode = false;
                    // this.updateHUDDisplay();
                });
            }
        } else {
            // Switch to normal mode
            eventsWrapper.classList.remove('hud-mode');
            hudToggleBtn.classList.remove('btn-hud-active');
            hudToggleBtn.textContent = 'HUD';
            
            // Deactivate the HUD visualizer
            if (this.hudVisualizer) {
                this.hudVisualizer.deactivate();
            }
        }
    }

    /**
     * Update HUD button state based on session selection
     */
    updateHUDButtonState() {
        const hudToggleBtn = document.getElementById('hud-toggle-btn');
        if (!hudToggleBtn) return;

        if (this.isSessionSelected()) {
            hudToggleBtn.disabled = false;
            hudToggleBtn.title = 'Toggle HUD visualizer';
        } else {
            hudToggleBtn.disabled = true;
            hudToggleBtn.title = 'Select a session to enable HUD';
            
            // If HUD is currently active, turn it off
            if (this.hudMode) {
                this.hudMode = false;
                this.updateHUDDisplay();
            }
        }
    }

    /**
     * Process existing events for HUD visualization
     */
    processExistingEventsForHUD() {
        if (!this.hudVisualizer || !this.eventViewer) return;
        
        console.log('🔄 Processing existing events for HUD visualization...');
        
        // Clear existing visualization
        this.hudVisualizer.clear();
        
        // Get all events (not just filtered ones) to build complete tree structure
        const allEvents = this.eventViewer.getAllEvents();
        
        if (allEvents.length === 0) {
            console.log('❌ No events available for HUD visualization');
            return;
        }
        
        // Sort events chronologically to ensure proper tree building
        const sortedEvents = [...allEvents].sort((a, b) => {
            const timeA = new Date(a.timestamp).getTime();
            const timeB = new Date(b.timestamp).getTime();
            return timeA - timeB;
        });
        
        console.log(`📊 Processing ${sortedEvents.length} events chronologically for HUD:`);
        console.log(`   • Earliest: ${new Date(sortedEvents[0].timestamp).toLocaleString()}`);
        console.log(`   • Latest: ${new Date(sortedEvents[sortedEvents.length - 1].timestamp).toLocaleString()}`);
        
        // Process events with enhanced hierarchy building
        this.hudVisualizer.processExistingEvents(sortedEvents);
        
        console.log(`✅ Processed ${sortedEvents.length} events for HUD visualization`);
    }

    /**
     * Handle new socket events for HUD
     * @param {Object} event - Socket event data
     */
    handleHUDEvent(event) {
        if (this.hudMode && this.hudVisualizer) {
            this.hudVisualizer.processEvent(event);
        }
    }
}

// Global functions for backward compatibility
window.connectSocket = function() {
    if (window.dashboard) {
        const port = document.getElementById('port-input')?.value || '8765';
        window.dashboard.socketClient.connect(port);
    }
};

window.disconnectSocket = function() {
    if (window.dashboard) {
        window.dashboard.socketClient.disconnect();
    }
};

window.clearEvents = function() {
    if (window.dashboard) {
        window.dashboard.clearEvents();
    }
};

window.exportEvents = function() {
    if (window.dashboard) {
        window.dashboard.exportEvents();
    }
};

window.clearSelection = function() {
    if (window.dashboard) {
        window.dashboard.clearSelection();
    }
};

window.switchTab = function(tabName) {
    if (window.dashboard) {
        window.dashboard.switchTab(tabName);
    }
};

// Detail view functions
window.showAgentDetailsByIndex = function(index) {
    if (window.dashboard) {
        window.dashboard.showAgentDetailsByIndex(index);
    }
};

window.showToolCallDetails = function(toolCallKey) {
    if (window.dashboard) {
        window.dashboard.showToolCallDetails(toolCallKey);
    }
};

window.showFileDetails = function(filePath) {
    if (window.dashboard) {
        window.dashboard.showFileDetails(filePath);
    }
};

// Debug function for testing scroll functionality
window.testScroll = async function() {
    if (window.dashboard) {
        console.log('🧪 Starting scroll functionality test...');
        try {
            const result = await window.dashboard.testScrollFunctionality();
            console.log('📋 Test results:\n' + result);
            
            // Also display results in an alert for easier viewing
            alert('Scroll Test Results:\n\n' + result);
            
            return result;
        } catch (error) {
            const errorMsg = `❌ Test failed with error: ${error.message}`;
            console.error(errorMsg, error);
            alert(errorMsg);
            return errorMsg;
        }
    } else {
        const errorMsg = '❌ Dashboard not initialized';
        console.error(errorMsg);
        alert(errorMsg);
        return errorMsg;
    }
};

// Simple direct scroll test function
window.testDirectScroll = function() {
    if (!window.dashboard) {
        console.error('❌ Dashboard not initialized');
        return 'Dashboard not initialized';
    }
    
    const currentTab = window.dashboard.currentTab;
    const listId = `${currentTab}-list`;
    const element = document.getElementById(listId);
    
    if (!element) {
        const msg = `❌ Element ${listId} not found`;
        console.error(msg);
        return msg;
    }
    
    console.log(`🎯 Direct scroll test on ${listId}`);
    console.log(`Before: scrollTop=${element.scrollTop}, scrollHeight=${element.scrollHeight}, clientHeight=${element.clientHeight}`);
    
    // Try direct assignment to maximum scroll
    element.scrollTop = 999999;
    
    setTimeout(() => {
        console.log(`After: scrollTop=${element.scrollTop}, scrollHeight=${element.scrollHeight}, clientHeight=${element.clientHeight}`);
        const success = element.scrollTop > 0 || element.scrollHeight <= element.clientHeight;
        const result = `${success ? '✅' : '❌'} Direct scroll test: scrollTop=${element.scrollTop}`;
        console.log(result);
        alert(result);
        return result;
    }, 50);
    
    return 'Test running...';
};

// CSS layout diagnostic function
window.diagnoseCSSLayout = function() {
    if (!window.dashboard) {
        return 'Dashboard not initialized';
    }
    
    const currentTab = window.dashboard.currentTab;
    const listId = `${currentTab}-list`;
    const results = [];
    
    // Check the full hierarchy
    const containers = [
        'events-wrapper',
        'events-container', 
        `${currentTab}-tab`,
        listId
    ];
    
    results.push(`🔍 CSS Layout Diagnosis for ${currentTab} tab:`);
    results.push('');
    
    containers.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            const computed = window.getComputedStyle(element);
            const rect = element.getBoundingClientRect();
            
            results.push(`📦 ${id}:`);
            results.push(`  Display: ${computed.display}`);
            results.push(`  Position: ${computed.position}`);
            results.push(`  Width: ${computed.width} (${rect.width}px)`);
            results.push(`  Height: ${computed.height} (${rect.height}px)`);
            results.push(`  Max-height: ${computed.maxHeight}`);
            results.push(`  Overflow-Y: ${computed.overflowY}`);
            results.push(`  Flex: ${computed.flex}`);
            results.push(`  Flex-direction: ${computed.flexDirection}`);
            
            if (element.scrollHeight !== element.clientHeight) {
                results.push(`  📊 ScrollHeight: ${element.scrollHeight}, ClientHeight: ${element.clientHeight}`);
                results.push(`  📊 ScrollTop: ${element.scrollTop} (can scroll: ${element.scrollHeight > element.clientHeight})`);
            }
            results.push('');
        } else {
            results.push(`❌ ${id}: Not found`);
            results.push('');
        }
    });
    
    const diagnosis = results.join('\n');
    console.log(diagnosis);
    alert(diagnosis);
    return diagnosis;
};

// Run all scroll diagnostics
window.runScrollDiagnostics = async function() {
    console.log('🔬 Running complete scroll diagnostics...');
    
    // Step 1: CSS Layout diagnosis
    console.log('\n=== STEP 1: CSS Layout Diagnosis ===');
    const cssResult = window.diagnoseCSSLayout();
    
    // Step 2: Direct scroll test
    console.log('\n=== STEP 2: Direct Scroll Test ===');
    await new Promise(resolve => setTimeout(resolve, 1000));
    const directResult = window.testDirectScroll();
    
    // Step 3: Full scroll functionality test
    console.log('\n=== STEP 3: Full Scroll Functionality Test ===');
    await new Promise(resolve => setTimeout(resolve, 2000));
    const fullResult = await window.testScroll();
    
    const summary = `
🔬 SCROLL DIAGNOSTICS COMPLETE
===============================

Step 1 - CSS Layout: See console for details
Step 2 - Direct Scroll: ${directResult}
Step 3 - Full Test: See alert for details

Check browser console for complete logs.
    `;
    
    console.log(summary);
    return summary;
};

// Git Diff Modal Functions
window.showGitDiffModal = function(filePath, timestamp, workingDir) {
    // Use the dashboard's current working directory if not provided
    if (!workingDir && window.dashboard && window.dashboard.currentWorkingDir) {
        workingDir = window.dashboard.currentWorkingDir;
    }
    
    // Create modal if it doesn't exist
    let modal = document.getElementById('git-diff-modal');
    if (!modal) {
        modal = createGitDiffModal();
        document.body.appendChild(modal);
    }
    
    // Update modal content
    updateGitDiffModal(modal, filePath, timestamp, workingDir);
    
    // Show the modal as flex container
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden'; // Prevent background scrolling
};

window.hideGitDiffModal = function() {
    const modal = document.getElementById('git-diff-modal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = ''; // Restore background scrolling
    }
};

function createGitDiffModal() {
    const modal = document.createElement('div');
    modal.id = 'git-diff-modal';
    modal.className = 'modal git-diff-modal';
    
    modal.innerHTML = `
        <div class="modal-content git-diff-content">
            <div class="git-diff-header">
                <h2 class="git-diff-title">
                    <span class="git-diff-icon">📋</span>
                    <span class="git-diff-title-text">Git Diff</span>
                </h2>
                <div class="git-diff-meta">
                    <span class="git-diff-file-path"></span>
                    <span class="git-diff-timestamp"></span>
                </div>
                <button class="git-diff-close" onclick="hideGitDiffModal()">
                    <span>&times;</span>
                </button>
            </div>
            <div class="git-diff-body">
                <div class="git-diff-loading">
                    <div class="loading-spinner"></div>
                    <span>Loading git diff...</span>
                </div>
                <div class="git-diff-error" style="display: none;">
                    <div class="error-icon">⚠️</div>
                    <div class="error-message"></div>
                    <div class="error-suggestions"></div>
                </div>
                <div class="git-diff-content-area" style="display: none;">
                    <div class="git-diff-toolbar">
                        <div class="git-diff-info">
                            <span class="commit-hash"></span>
                            <span class="diff-method"></span>
                        </div>
                        <div class="git-diff-actions">
                            <button class="git-diff-copy" onclick="copyGitDiff()">
                                📋 Copy
                            </button>
                        </div>
                    </div>
                    <div class="git-diff-scroll-wrapper">
                        <pre class="git-diff-display"><code class="git-diff-code"></code></pre>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // Close modal when clicking outside
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            hideGitDiffModal();
        }
    });
    
    // Close modal with Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.style.display === 'block') {
            hideGitDiffModal();
        }
    });
    
    return modal;
}

async function updateGitDiffModal(modal, filePath, timestamp, workingDir) {
    // Update header info
    const filePathElement = modal.querySelector('.git-diff-file-path');
    const timestampElement = modal.querySelector('.git-diff-timestamp');
    
    filePathElement.textContent = filePath;
    timestampElement.textContent = timestamp ? new Date(timestamp).toLocaleString() : 'Latest';
    
    // Show loading state
    modal.querySelector('.git-diff-loading').style.display = 'flex';
    modal.querySelector('.git-diff-error').style.display = 'none';
    modal.querySelector('.git-diff-content-area').style.display = 'none';
    
    try {
        // Get the Socket.IO server port with multiple fallbacks
        let port = 8765; // Default fallback
        
        // Try to get port from socketClient first
        if (window.dashboard && window.dashboard.socketClient && window.dashboard.socketClient.port) {
            port = window.dashboard.socketClient.port;
        }
        // Fallback to port input field if socketClient port is not available
        else {
            const portInput = document.getElementById('port-input');
            if (portInput && portInput.value) {
                port = portInput.value;
            }
        }
        
        
        // Build URL parameters
        const params = new URLSearchParams({
            file: filePath
        });
        
        if (timestamp) {
            params.append('timestamp', timestamp);
        }
        if (workingDir) {
            params.append('working_dir', workingDir);
        }
        
        const requestUrl = `http://localhost:${port}/api/git-diff?${params}`;
        console.log('🌐 Making git diff request to:', requestUrl);
        
        // Test server connectivity first
        try {
            const healthResponse = await fetch(`http://localhost:${port}/health`, {
                method: 'GET',
                headers: {
                    'Accept': 'application/json',
                    'Content-Type': 'application/json'
                },
                mode: 'cors'
            });
            
            if (!healthResponse.ok) {
                throw new Error(`Server health check failed: ${healthResponse.status} ${healthResponse.statusText}`);
            }
            
            console.log('✅ Server health check passed');
        } catch (healthError) {
            throw new Error(`Cannot reach server at localhost:${port}. Health check failed: ${healthError.message}`);
        }
        
        // Make the actual git diff request
        const response = await fetch(requestUrl, {
            method: 'GET',
            headers: {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            },
            mode: 'cors'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const result = await response.json();
        console.log('📦 Git diff response:', result);
        
        // Hide loading
        modal.querySelector('.git-diff-loading').style.display = 'none';
        
        if (result.success) {
            console.log('📊 Displaying successful git diff');
            // Show successful diff
            displayGitDiff(modal, result);
        } else {
            console.log('⚠️ Displaying git diff error:', result);
            // Show error
            displayGitDiffError(modal, result);
        }
        
    } catch (error) {
        console.error('❌ Failed to fetch git diff:', error);
        console.error('Error details:', {
            name: error.name,
            message: error.message,
            stack: error.stack,
            filePath,
            timestamp,
            workingDir
        });
        
        modal.querySelector('.git-diff-loading').style.display = 'none';
        
        // Create detailed error message based on error type
        let errorMessage = `Network error: ${error.message}`;
        let suggestions = [];
        
        if (error.message.includes('Failed to fetch')) {
            errorMessage = 'Failed to connect to the monitoring server';
            suggestions = [
                'Check if the monitoring server is running on port 8765',
                'Verify the port configuration in the dashboard',
                'Check browser console for CORS or network errors',
                'Try refreshing the page and reconnecting'
            ];
        } else if (error.message.includes('health check failed')) {
            errorMessage = error.message;
            suggestions = [
                'The server may be starting up - try again in a few seconds',
                'Check if another process is using port 8765',
                'Restart the claude-mpm monitoring server'
            ];
        } else if (error.message.includes('HTTP')) {
            errorMessage = `Server error: ${error.message}`;
            suggestions = [
                'The server encountered an internal error',
                'Check the server logs for more details',
                'Try with a different file or working directory'
            ];
        }
        
        displayGitDiffError(modal, {
            error: errorMessage,
            file_path: filePath,
            working_dir: workingDir,
            suggestions: suggestions,
            debug_info: {
                error_type: error.name,
                original_message: error.message,
                port: window.dashboard?.socketClient?.port || document.getElementById('port-input')?.value || '8765',
                timestamp: new Date().toISOString()
            }
        });
    }
}

function highlightGitDiff(diffText) {
    /**
     * Apply basic syntax highlighting to git diff output
     * WHY: Git diffs have a standard format that can be highlighted for better readability:
     * - Lines starting with '+' are additions (green)
     * - Lines starting with '-' are deletions (red)  
     * - Lines starting with '@@' are context headers (blue)
     * - File headers and metadata get special formatting
     */
    return diffText
        .split('\n')
        .map(line => {
            // Escape HTML entities
            const escaped = line
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
            
            // Apply diff highlighting
            if (line.startsWith('+++') || line.startsWith('---')) {
                return `<span class="diff-header">${escaped}</span>`;
            } else if (line.startsWith('@@')) {
                return `<span class="diff-meta">${escaped}</span>`;
            } else if (line.startsWith('+')) {
                return `<span class="diff-addition">${escaped}</span>`;
            } else if (line.startsWith('-')) {
                return `<span class="diff-deletion">${escaped}</span>`;
            } else if (line.startsWith('commit ') || line.startsWith('Author:') || line.startsWith('Date:')) {
                return `<span class="diff-header">${escaped}</span>`;
            } else {
                return `<span class="diff-context">${escaped}</span>`;
            }
        })
        .join('\n');
}

function displayGitDiff(modal, result) {
    console.log('📝 displayGitDiff called with:', result);
    const contentArea = modal.querySelector('.git-diff-content-area');
    const commitHashElement = modal.querySelector('.commit-hash');
    const methodElement = modal.querySelector('.diff-method');
    const codeElement = modal.querySelector('.git-diff-code');
    
    console.log('🔍 Elements found:', {
        contentArea: !!contentArea,
        commitHashElement: !!commitHashElement,
        methodElement: !!methodElement,
        codeElement: !!codeElement
    });
    
    // Update metadata
    if (commitHashElement) commitHashElement.textContent = `Commit: ${result.commit_hash}`;
    if (methodElement) methodElement.textContent = `Method: ${result.method}`;
    
    // Update diff content with basic syntax highlighting
    if (codeElement && result.diff) {
        console.log('💡 Setting diff content, length:', result.diff.length);
        codeElement.innerHTML = highlightGitDiff(result.diff);
        
        // Force scrolling to work by setting explicit heights
        const wrapper = modal.querySelector('.git-diff-scroll-wrapper');
        if (wrapper) {
            // Give it a moment for content to render
            setTimeout(() => {
                const modalContent = modal.querySelector('.modal-content');
                const header = modal.querySelector('.git-diff-header');
                const toolbar = modal.querySelector('.git-diff-toolbar');
                
                const modalHeight = modalContent?.offsetHeight || 0;
                const headerHeight = header?.offsetHeight || 0;
                const toolbarHeight = toolbar?.offsetHeight || 0;
                
                const availableHeight = modalHeight - headerHeight - toolbarHeight - 40; // 40px for padding
                
                console.log('🎯 Setting explicit scroll height:', {
                    modalHeight,
                    headerHeight,
                    toolbarHeight,
                    availableHeight
                });
                
                wrapper.style.maxHeight = `${availableHeight}px`;
                wrapper.style.overflowY = 'auto';
            }, 50);
        }
    } else {
        console.warn('⚠️ Missing codeElement or diff data');
    }
    
    // Show content area
    if (contentArea) {
        contentArea.style.display = 'block';
        console.log('✅ Content area displayed');
        
        // Debug height information and force scrolling test
        setTimeout(() => {
            const modal = document.querySelector('.modal-content.git-diff-content');
            const body = document.querySelector('.git-diff-body');
            const wrapper = document.querySelector('.git-diff-scroll-wrapper');
            const display = document.querySelector('.git-diff-display');
            const code = document.querySelector('.git-diff-code');
            
            console.log('🔍 Height debugging:', {
                modalHeight: modal?.offsetHeight,
                bodyHeight: body?.offsetHeight,
                wrapperHeight: wrapper?.offsetHeight,
                wrapperScrollHeight: wrapper?.scrollHeight,
                displayHeight: display?.offsetHeight,
                displayScrollHeight: display?.scrollHeight,
                codeHeight: code?.offsetHeight,
                wrapperStyle: wrapper ? window.getComputedStyle(wrapper).overflow : null,
                bodyStyle: body ? window.getComputedStyle(body).overflow : null
            });
            
            // Force test - add a lot of content to test scrolling
            if (code && code.textContent.length < 1000) {
                console.log('🧪 Adding test content for scrolling...');
                code.innerHTML = code.innerHTML + '\n\n' + '// TEST SCROLLING\n'.repeat(100);
            }
            
            // Force fix scrolling with inline styles
            if (wrapper) {
                console.log('🔧 Applying scrolling fix...');
                wrapper.style.height = '100%';
                wrapper.style.overflow = 'auto';
                wrapper.style.maxHeight = 'calc(100% - 60px)'; // Account for toolbar
            }
            
            // Also check parent heights
            const contentArea = document.querySelector('.git-diff-content-area');
            if (contentArea) {
                const computedStyle = window.getComputedStyle(contentArea);
                console.log('📏 Content area height:', computedStyle.height);
                if (computedStyle.height === 'auto' || !computedStyle.height) {
                    contentArea.style.height = '100%';
                }
            }
        }, 100);
    }
}

function displayGitDiffError(modal, result) {
    const errorArea = modal.querySelector('.git-diff-error');
    const messageElement = modal.querySelector('.error-message');
    const suggestionsElement = modal.querySelector('.error-suggestions');
    
    messageElement.textContent = result.error || 'Unknown error occurred';
    
    if (result.suggestions && result.suggestions.length > 0) {
        suggestionsElement.innerHTML = `
            <h4>Suggestions:</h4>
            <ul>
                ${result.suggestions.map(s => `<li>${s}</li>`).join('')}
            </ul>
        `;
    } else {
        suggestionsElement.innerHTML = '';
    }
    
    errorArea.style.display = 'block';
}

window.copyGitDiff = function() {
    const modal = document.getElementById('git-diff-modal');
    if (!modal) return;
    
    const codeElement = modal.querySelector('.git-diff-code');
    if (!codeElement) return;
    
    const text = codeElement.textContent;
    
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            // Show brief feedback
            const button = modal.querySelector('.git-diff-copy');
            const originalText = button.textContent;
            button.textContent = '✅ Copied!';
            setTimeout(() => {
                button.textContent = originalText;
            }, 2000);
        }).catch(err => {
            console.error('Failed to copy text:', err);
        });
    } else {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        
        const button = modal.querySelector('.git-diff-copy');
        const originalText = button.textContent;
        button.textContent = '✅ Copied!';
        setTimeout(() => {
            button.textContent = originalText;
        }, 2000);
    }
};

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new Dashboard();
    console.log('Dashboard ready');
});

// Export for use in other modules
window.Dashboard = Dashboard;