/**
 * Refactored Dashboard Coordinator
 *
 * Main coordinator class that orchestrates all dashboard modules while maintaining
 * backward compatibility with the original dashboard interface.
 *
 * WHY: This refactored version breaks down the monolithic 4,133-line dashboard
 * into manageable, focused modules while preserving all existing functionality.
 * Each module handles a specific concern, improving maintainability and testability.
 *
 * DESIGN DECISION: Acts as a thin coordinator layer that initializes modules,
 * manages inter-module communication through events, and provides backward
 * compatibility for existing code that depends on the dashboard interface.
 */

// ES6 Module imports
import { SocketManager } from '@components/socket-manager.js';
import { EventViewer } from '@components/event-viewer.js';
import { ModuleViewer } from '@components/module-viewer.js';
import { SessionManager } from '@components/session-manager.js';
import { AgentInference } from '@components/agent-inference.js';
import { AgentHierarchy } from '@components/agent-hierarchy.js';
import { UIStateManager } from '@components/ui-state-manager.js';
import { EventProcessor } from '@components/event-processor.js';
import { ExportManager } from '@components/export-manager.js';
import { WorkingDirectoryManager } from '@components/working-directory.js';
import { FileToolTracker } from '@components/file-tool-tracker.js';
import { BuildTracker } from '@components/build-tracker.js';
import { UnifiedDataViewer } from '@components/unified-data-viewer.js';
class Dashboard {
    constructor() {
        // Core components (existing)
        this.eventViewer = null;
        this.moduleViewer = null;
        this.sessionManager = null;
        
        // Retry prevention
        this.activityTreeRetryCount = 0;
        this.maxRetryAttempts = 10;

        // New modular components
        this.socketManager = null;
        this.agentInference = null;
        this.agentHierarchy = null;
        this.uiStateManager = null;
        this.eventProcessor = null;
        this.exportManager = null;
        this.workingDirectoryManager = null;
        this.fileToolTracker = null;
        this.buildTracker = null;

        // Initialize the dashboard
        this.init();
    }

    /**
     * Initialize the dashboard and all modules
     */
    init() {
        console.log('Initializing refactored Claude MPM Dashboard...');

        try {
            // Fetch server configuration first
            this.fetchServerConfig();
            
            // Initialize modules in dependency order
            this.initializeSocketManager();
            this.initializeCoreComponents();
            this.initializeBuildTracker();
            this.initializeAgentInference();
            this.initializeAgentHierarchy();
            this.initializeUIStateManager();
            this.initializeWorkingDirectoryManager();
            this.initializeFileToolTracker();
            this.initializeEventProcessor();
            this.initializeExportManager();

            // Set up inter-module communication
            this.setupModuleInteractions();

            // Initialize from URL parameters
            this.initializeFromURL();

            console.log('Claude MPM Dashboard initialized successfully');
        } catch (error) {
            console.error('Error during dashboard initialization:', error);
            // Re-throw to be caught by DOMContentLoaded handler
            throw error;
        }
    }
    
    /**
     * Fetch server configuration for dashboard initialization
     */
    fetchServerConfig() {
        fetch('/api/config')
            .then(response => response.json())
            .then(config => {
                // Store config globally for other components
                window.dashboardConfig = config;
                
                // Update initial UI elements if they exist
                const workingDirEl = document.getElementById('working-dir-path');
                if (workingDirEl && config.workingDirectory) {
                    workingDirEl.textContent = config.workingDirectory;
                }
                
                const gitBranchEl = document.getElementById('footer-git-branch');
                if (gitBranchEl && config.gitBranch) {
                    gitBranchEl.textContent = config.gitBranch;
                }
                
                console.log('Dashboard configuration loaded:', config);
            })
            .catch(error => {
                console.warn('Failed to fetch server config:', error);
                // Set default config as fallback
                window.dashboardConfig = {
                    workingDirectory: '.',
                    gitBranch: 'Unknown'
                };
            });
    }
    
    /**
     * Validate that all critical components are initialized
     * WHY: Ensures dashboard is in a valid state after initialization
     */
    validateInitialization() {
        const criticalComponents = [
            { name: 'socketManager', component: this.socketManager },
            { name: 'eventViewer', component: this.eventViewer },
            { name: 'agentHierarchy', component: this.agentHierarchy }
        ];
        
        const missing = criticalComponents.filter(c => !c.component);
        if (missing.length > 0) {
            console.warn('Missing critical components:', missing.map(c => c.name));
        } else {
            console.log('All critical components initialized');
        }
    }

    /**
     * Post-initialization setup that requires window.dashboard to be set
     * WHY: Some components need to reference window.dashboard but it's not available
     * during constructor execution. This method is called after the Dashboard instance
     * is assigned to window.dashboard, ensuring proper initialization order.
     * 
     * DESIGN DECISION: Separate post-init phase prevents "cannot read property of undefined"
     * errors when components try to access window.dashboard during construction.
     */
    postInit() {
        try {
            // Set global reference for agent hierarchy after dashboard is available
            if (this.agentHierarchy) {
                window.dashboard.agentHierarchy = this.agentHierarchy;
                console.log('Agent hierarchy global reference set');
            }
            
            // Initialize any other components that need window.dashboard
            this.validateInitialization();
        } catch (error) {
            console.error('Error in dashboard postInit:', error);
            // Continue execution - non-critical error
        }
    }

    /**
     * Initialize socket manager
     */
    initializeSocketManager() {
        this.socketManager = new SocketManager();

        // Set up connection controls
        this.socketManager.setupConnectionControls();

        // Backward compatibility
        this.socketClient = this.socketManager.getSocketClient();
        window.socketClient = this.socketClient;
    }

    /**
     * Initialize core existing components
     */
    initializeCoreComponents() {
        // Initialize existing components with socket client
        this.eventViewer = new EventViewer('events-list', this.socketClient);
        this.moduleViewer = new ModuleViewer();
        this.sessionManager = new SessionManager(this.socketClient);

        // Backward compatibility
        window.eventViewer = this.eventViewer;
        window.moduleViewer = this.moduleViewer;
        window.sessionManager = this.sessionManager;
    }

    /**
     * Initialize build tracker
     */
    initializeBuildTracker() {
        this.buildTracker = new BuildTracker();
        
        // Set the socket client for receiving updates
        this.buildTracker.setSocketClient(this.socketClient);
        
        // Mount to header with retry logic for DOM readiness
        const mountBuildTracker = () => {
            const headerTitle = document.querySelector('.header-title');
            if (headerTitle) {
                // Insert after the title and status badge
                this.buildTracker.mount(headerTitle);
                console.log('BuildTracker mounted successfully');
            } else {
                console.warn('Header-title element not found for build tracker, will retry');
                // Retry after a short delay if DOM is still being constructed
                setTimeout(mountBuildTracker, 100);
            }
        };
        
        // Try to mount immediately, with retry logic if needed
        mountBuildTracker();
        
        // Make available globally for debugging
        window.buildTracker = this.buildTracker;
    }

    /**
     * Initialize agent inference system
     */
    initializeAgentInference() {
        this.agentInference = new AgentInference(this.eventViewer);
        this.agentInference.initialize();
    }
    
    /**
     * Initialize agent hierarchy component
     * WHY: Creates the agent hierarchy visualization component but defers global
     * reference setting to postInit() to avoid initialization order issues.
     */
    initializeAgentHierarchy() {
        try {
            this.agentHierarchy = new AgentHierarchy(this.agentInference, this.eventViewer);
            // Global reference will be set in postInit() after window.dashboard exists
            console.log('Agent hierarchy component created');
        } catch (error) {
            console.error('Failed to initialize agent hierarchy:', error);
            // Create a stub to prevent further errors
            this.agentHierarchy = {
                render: () => '<div class="error">Agent hierarchy unavailable</div>',
                expandAllNodes: () => {},
                collapseAllNodes: () => {},
                updateWithNewEvents: () => {}
            };
        }
    }

    /**
     * Initialize UI state manager
     */
    initializeUIStateManager() {
        this.uiStateManager = new UIStateManager();
        this.setupTabFilters(); // Set up filters after UI state manager
    }

    /**
     * Initialize working directory manager
     */
    initializeWorkingDirectoryManager() {
        this.workingDirectoryManager = new WorkingDirectoryManager(this.socketManager);
    }

    /**
     * Initialize file-tool tracker
     */
    initializeFileToolTracker() {
        this.fileToolTracker = new FileToolTracker(this.agentInference, this.workingDirectoryManager);
    }

    /**
     * Initialize event processor
     */
    initializeEventProcessor() {
        this.eventProcessor = new EventProcessor(this.eventViewer, this.agentInference);
    }


    /**
     * Initialize export manager
     */
    initializeExportManager() {
        this.exportManager = new ExportManager(this.eventViewer);
    }

    /**
     * Set up interactions between modules
     */
    setupModuleInteractions() {
        // Socket events to update file operations and tool calls
        this.socketManager.onEventUpdate((events) => {
            this.fileToolTracker.updateFileOperations(events);
            this.fileToolTracker.updateToolCalls(events);

            // Process agent inference for new events
            this.agentInference.processAgentInference();
            
            // Update agent hierarchy with new events
            this.agentHierarchy.updateWithNewEvents(events);

            // Auto-scroll events list if on events tab
            if (this.uiStateManager.getCurrentTab() === 'events') {
                this.exportManager.scrollListToBottom('events-list');
            }

            // Re-render current tab
            this.renderCurrentTab();
        });

        // Connection status changes
        this.socketManager.onConnectionStatusChange((status, type) => {
            // Set up git branch listener when connected
            if (type === 'connected') {
                this.workingDirectoryManager.updateGitBranch(
                    this.workingDirectoryManager.getCurrentWorkingDir()
                );
            }
        });

        // Tab changes
        document.addEventListener('tabChanged', (e) => {
            this.renderCurrentTab();
            this.uiStateManager.updateTabNavigationItems();
        });

        // Events clearing
        document.addEventListener('eventsClearing', () => {
            this.fileToolTracker.clear();
            this.agentInference.initialize();
        });

        // Card details requests
        document.addEventListener('showCardDetails', (e) => {
            this.showCardDetails(e.detail.tabName, e.detail.index);
        });

        // Session changes
        document.addEventListener('sessionFilterChanged', (e) => {
            console.log('Session filter changed, re-rendering current tab:', this.uiStateManager.getCurrentTab());
            this.renderCurrentTab();
        });
    }

    /**
     * Set up tab filters
     */
    setupTabFilters() {
        // Agents tab filters
        const agentsSearchInput = document.getElementById('agents-search-input');
        const agentsTypeFilter = document.getElementById('agents-type-filter');

        if (agentsSearchInput) {
            agentsSearchInput.addEventListener('input', () => {
                if (this.uiStateManager.getCurrentTab() === 'agents') this.renderCurrentTab();
            });
        }

        if (agentsTypeFilter) {
            agentsTypeFilter.addEventListener('change', () => {
                if (this.uiStateManager.getCurrentTab() === 'agents') this.renderCurrentTab();
            });
        }

        // Tools tab filters
        const toolsSearchInput = document.getElementById('tools-search-input');
        const toolsTypeFilter = document.getElementById('tools-type-filter');

        if (toolsSearchInput) {
            toolsSearchInput.addEventListener('input', () => {
                if (this.uiStateManager.getCurrentTab() === 'tools') this.renderCurrentTab();
            });
        }

        if (toolsTypeFilter) {
            toolsTypeFilter.addEventListener('change', () => {
                if (this.uiStateManager.getCurrentTab() === 'tools') this.renderCurrentTab();
            });
        }

        // Files tab filters
        const filesSearchInput = document.getElementById('files-search-input');
        const filesTypeFilter = document.getElementById('files-type-filter');

        if (filesSearchInput) {
            filesSearchInput.addEventListener('input', () => {
                if (this.uiStateManager.getCurrentTab() === 'files') this.renderCurrentTab();
            });
        }

        if (filesTypeFilter) {
            filesTypeFilter.addEventListener('change', () => {
                if (this.uiStateManager.getCurrentTab() === 'files') this.renderCurrentTab();
            });
        }
    }

    /**
     * Initialize from URL parameters
     */
    initializeFromURL() {
        const params = new URLSearchParams(window.location.search);
        this.socketManager.initializeFromURL(params);
    }

    /**
     * Render current tab content
     */
    renderCurrentTab() {
        const currentTab = this.uiStateManager.getCurrentTab();

        switch (currentTab) {
            case 'events':
                // Events tab is handled by EventViewer
                break;
            case 'activity':
                // Trigger Activity tab rendering through the component
                // Check if ActivityTree class is available (from built module)
                if (window.ActivityTree && typeof window.ActivityTree === 'function') {
                    // Reset retry count on successful load
                    this.activityTreeRetryCount = 0;
                    
                    // Create or get instance
                    if (!window.activityTreeInstance) {
                        console.log('Creating new ActivityTree instance...');
                        window.activityTreeInstance = new window.ActivityTree();
                    }
                    
                    // Initialize if needed and render
                    if (window.activityTreeInstance) {
                        if (!window.activityTreeInstance.initialized) {
                            console.log('Initializing ActivityTree...');
                            window.activityTreeInstance.initialize();
                        }
                        
                        if (typeof window.activityTreeInstance.renderWhenVisible === 'function') {
                            console.log('Dashboard triggering activity tree render...');
                            window.activityTreeInstance.renderWhenVisible();
                        }
                        
                        // Force show to ensure the tree is visible
                        if (typeof window.activityTreeInstance.forceShow === 'function') {
                            console.log('Dashboard forcing activity tree to show...');
                            window.activityTreeInstance.forceShow();
                        }
                    }
                } else if (window.activityTree && typeof window.activityTree === 'function') {
                    // Fallback to legacy approach if available
                    const activityTreeInstance = window.activityTree();
                    if (activityTreeInstance) {
                        if (typeof activityTreeInstance.renderWhenVisible === 'function') {
                            console.log('Dashboard triggering activity tree render (legacy)...');
                            activityTreeInstance.renderWhenVisible();
                        }
                        if (typeof activityTreeInstance.forceShow === 'function') {
                            console.log('Dashboard forcing activity tree to show (legacy)...');
                            activityTreeInstance.forceShow();
                        }
                    }
                } else {
                    // Module not loaded yet, retry after a delay (with retry limit)
                    if (this.activityTreeRetryCount < this.maxRetryAttempts) {
                        this.activityTreeRetryCount++;
                        console.warn(`Activity tree component not available, retrying in 100ms... (attempt ${this.activityTreeRetryCount}/${this.maxRetryAttempts})`);
                        setTimeout(() => {
                            if (this.uiStateManager.getCurrentTab() === 'activity') {
                                this.renderCurrentTab();
                            }
                        }, 100);
                    } else {
                        console.error('Maximum retry attempts reached for ActivityTree initialization. Giving up.');
                        const activityContainer = document.getElementById('activity-tree-container') || document.getElementById('activity-tree');
                        if (activityContainer) {
                            activityContainer.innerHTML = '<div class="error-message">⚠️ Activity Tree failed to load. Please refresh the page.</div>';
                        }
                    }
                }
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

        // Update selection UI if we have a selected card
        const selectedCard = this.uiStateManager.getSelectedCard();
        if (selectedCard.tab === currentTab) {
            this.uiStateManager.updateCardSelectionUI();
        }

        // Update unified selection UI to maintain consistency
        this.uiStateManager.updateUnifiedSelectionUI();
    }

    /**
     * Render agents tab with flat chronological view
     */
    renderAgents() {
        const agentsList = document.getElementById('agents-list');
        if (!agentsList) return;
        
        // Get filter values
        const searchText = document.getElementById('agents-search-input')?.value || '';
        const agentType = document.getElementById('agents-type-filter')?.value || '';
        
        // Generate flat HTML
        const flatHTML = this.renderAgentsFlat(searchText, agentType);
        agentsList.innerHTML = flatHTML;
        
        // Remove hierarchy controls if they exist
        this.removeHierarchyControls();
        
        // Update filter dropdowns with available agent types
        const uniqueInstances = this.agentInference.getUniqueAgentInstances();
        this.updateAgentsFilterDropdowns(uniqueInstances);
    }
    
    /**
     * Remove hierarchy control buttons (flat view doesn't need them)
     */
    removeHierarchyControls() {
        const existingControls = document.getElementById('hierarchy-controls');
        if (existingControls) {
            existingControls.remove();
        }
    }
    
    /**
     * Render agents as a flat chronological list
     * @param {string} searchText - Search filter
     * @param {string} agentType - Agent type filter 
     * @returns {string} HTML for flat agent list
     */
    renderAgentsFlat(searchText, agentType) {
        const events = this.eventViewer.events;
        if (!events || events.length === 0) {
            return '<div class="no-events">No agent events found...</div>';
        }
        
        // Process agent inference to get agent mappings
        this.agentInference.processAgentInference();
        const eventAgentMap = this.agentInference.getEventAgentMap();
        
        // Collect all agent events with metadata
        const agentEvents = [];
        events.forEach((event, index) => {
            const inference = eventAgentMap.get(index);
            if (inference && (inference.type === 'subagent' || inference.type === 'main_agent')) {
                // Apply filters
                let includeEvent = true;
                
                if (searchText) {
                    const searchLower = searchText.toLowerCase();
                    includeEvent = includeEvent && (
                        inference.agentName.toLowerCase().includes(searchLower) ||
                        (event.tool_name && event.tool_name.toLowerCase().includes(searchLower)) ||
                        (event.data && JSON.stringify(event.data).toLowerCase().includes(searchLower))
                    );
                }
                
                if (agentType) {
                    includeEvent = includeEvent && inference.agentName.includes(agentType);
                }
                
                if (includeEvent) {
                    agentEvents.push({
                        event,
                        inference,
                        index,
                        timestamp: new Date(event.timestamp)
                    });
                }
            }
        });
        
        if (agentEvents.length === 0) {
            return '<div class="no-events">No agent events match the current filters...</div>';
        }
        
        // Generate HTML for each event
        const html = agentEvents.map((item, listIndex) => {
            const { event, inference, index, timestamp } = item;
            
            // Determine action/tool
            let action = 'Activity';
            let actionIcon = '📋';
            let details = '';
            
            if (event.event_type === 'SubagentStart') {
                action = 'Started';
                actionIcon = '🟢';
                details = 'Agent session began';
            } else if (event.event_type === 'SubagentStop') {
                action = 'Stopped';
                actionIcon = '🔴';
                details = 'Agent session ended';
            } else if (event.tool_name) {
                action = `Tool: ${event.tool_name}`;
                actionIcon = this.getToolIcon(event.tool_name);
                
                // Add tool parameters as details
                if (event.data && event.data.tool_parameters) {
                    const params = event.data.tool_parameters;
                    if (params.file_path) {
                        details = params.file_path;
                    } else if (params.command) {
                        details = params.command.substring(0, 50) + (params.command.length > 50 ? '...' : '');
                    } else if (params.pattern) {
                        details = `pattern="${params.pattern}"`;
                    } else if (params.query) {
                        details = `query="${params.query}"`;
                    }
                }
            }
            
            // Status based on event type
            let status = 'completed';
            if (event.event_type === 'SubagentStart') {
                status = 'active';
            } else if (event.data && event.data.error) {
                status = 'error';
            }
            
            return `
                <div class="agent-event-item" data-index="${listIndex}" onclick="window.dashboard.showCardDetails('agents', ${index})">
                    <div class="agent-event-header">
                        <div class="agent-event-time">${this.formatTimestamp(timestamp)}</div>
                        <div class="agent-event-agent">
                            ${this.getAgentIcon(inference.agentName)} ${inference.agentName}
                        </div>
                        <div class="agent-event-action">
                            ${actionIcon} ${action}
                        </div>
                        <div class="agent-event-status status-${status}">
                            ${this.getStatusIcon(status)}
                        </div>
                    </div>
                    ${details ? `<div class="agent-event-details">${this.escapeHtml(details)}</div>` : ''}
                </div>
            `;
        }).join('');
        
        return `<div class="agent-events-flat">${html}</div>`;
    }
    
    /**
     * Get icon for agent type
     */
    getAgentIcon(agentName) {
        const agentIcons = {
            'PM': '🎯',
            'Engineer Agent': '🔧',
            'Research Agent': '🔍', 
            'QA Agent': '✅',
            'Documentation Agent': '📝',
            'Security Agent': '🔒',
            'Ops Agent': '⚙️',
            'Version Control Agent': '📦',
            'Data Engineer Agent': '💾',
            'Test Integration Agent': '🧪'
        };
        return agentIcons[agentName] || '🤖';
    }
    
    /**
     * Get icon for tool
     */
    getToolIcon(toolName) {
        const toolIcons = {
            'Read': '📖',
            'Write': '✏️',
            'Edit': '📝',
            'Bash': '💻',
            'Grep': '🔍',
            'Glob': '📂',
            'LS': '📁',
            'Task': '📋'
        };
        return toolIcons[toolName] || '🔧';
    }
    
    /**
     * Get icon for status
     */
    getStatusIcon(status) {
        const statusIcons = {
            'active': '🟢',
            'completed': '✅',
            'error': '❌',
            'pending': '🟡'
        };
        return statusIcons[status] || '❓';
    }
    
    /**
     * Format timestamp for display
     */
    formatTimestamp(timestamp) {
        return timestamp.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit', 
            second: '2-digit',
            hour12: false
        });
    }
    
    /**
     * Escape HTML for safe display
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Render tools tab with unique instance view (one row per unique tool call)
     */
    renderTools() {
        const toolsList = document.getElementById('tools-list');
        if (!toolsList) return;

        const toolCalls = this.fileToolTracker.getToolCalls();
        const toolCallsArray = Array.from(toolCalls.entries());
        const uniqueToolInstances = this.eventProcessor.getUniqueToolInstances(toolCallsArray);
        const toolHTML = this.eventProcessor.generateToolHTML(uniqueToolInstances);

        toolsList.innerHTML = toolHTML;
        this.exportManager.scrollListToBottom('tools-list');

        // Update filter dropdowns
        this.updateToolsFilterDropdowns(uniqueToolInstances);
    }

    /**
     * Render files tab with unique instance view (one row per unique file)
     */
    renderFiles() {
        const filesList = document.getElementById('files-list');
        if (!filesList) return;

        const fileOperations = this.fileToolTracker.getFileOperations();
        const filesArray = Array.from(fileOperations.entries());
        const uniqueFileInstances = this.eventProcessor.getUniqueFileInstances(filesArray);
        const fileHTML = this.eventProcessor.generateFileHTML(uniqueFileInstances);

        filesList.innerHTML = fileHTML;
        this.exportManager.scrollListToBottom('files-list');

        // Update filter dropdowns
        this.updateFilesFilterDropdowns(filesArray);
    }

    /**
     * Update agents filter dropdowns for unique instances
     */
    updateAgentsFilterDropdowns(uniqueInstances) {
        const agentTypes = new Set();

        // uniqueInstances is already an array of unique agent instances
        uniqueInstances.forEach(instance => {
            if (instance.agentName && instance.agentName !== 'Unknown') {
                agentTypes.add(instance.agentName);
            }
        });

        const sortedTypes = Array.from(agentTypes).filter(type => type && type.trim() !== '');
        this.populateFilterDropdown('agents-type-filter', sortedTypes, 'All Agent Types');

        // Debug log
        if (sortedTypes.length > 0) {
            console.log('Agent types found for filter:', sortedTypes);
        } else {
            console.log('No agent types found for filter. Instances:', uniqueInstances.length);
        }
    }

    /**
     * Update tools filter dropdowns
     */
    updateToolsFilterDropdowns(toolCallsArray) {
        const toolNames = [...new Set(toolCallsArray.map(([key, toolCall]) => toolCall.tool_name))]
            .filter(name => name);

        this.populateFilterDropdown('tools-type-filter', toolNames, 'All Tools');
    }

    /**
     * Update files filter dropdowns
     */
    updateFilesFilterDropdowns(filesArray) {
        const operations = [...new Set(filesArray.flatMap(([path, data]) =>
            data.operations.map(op => op.operation)
        ))].filter(op => op);

        this.populateFilterDropdown('files-type-filter', operations, 'All Operations');
    }

    /**
     * Populate filter dropdown with values
     */
    populateFilterDropdown(selectId, values, allOption = 'All') {
        const select = document.getElementById(selectId);
        if (!select) return;

        const currentValue = select.value;
        const sortedValues = values.sort((a, b) => a.localeCompare(b));

        // Clear existing options except the first "All" option
        select.innerHTML = `<option value="">${allOption}</option>`;

        // Add sorted values
        sortedValues.forEach(value => {
            const option = document.createElement('option');
            option.value = value;
            option.textContent = value;
            select.appendChild(option);
        });

        // Restore previous selection if it still exists
        if (currentValue && sortedValues.includes(currentValue)) {
            select.value = currentValue;
        }
    }

    /**
     * Show card details for specified tab and index
     */
    showCardDetails(tabName, index) {
        switch (tabName) {
            case 'events':
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
     * Show agent details by index
     */
    showAgentDetailsByIndex(index) {
        const events = this.eventProcessor.getFilteredEventsForTab('agents');

        // Defensive checks
        if (!events || !Array.isArray(events) || index < 0 || index >= events.length) {
            console.warn('Dashboard: Invalid agent index or events array');
            return;
        }

        const filteredSingleEvent = this.eventProcessor.applyAgentsFilters([events[index]]);

        if (filteredSingleEvent.length > 0 && this.moduleViewer &&
            typeof this.moduleViewer.showAgentEvent === 'function') {
            const event = filteredSingleEvent[0];
            this.moduleViewer.showAgentEvent(event, index);
        }
    }

    /**
     * Show agent instance details for unique instance view
     * @param {string} instanceId - Agent instance ID
     */
    showAgentInstanceDetails(instanceId) {
        const pmDelegations = this.agentInference.getPMDelegations();
        const instance = pmDelegations.get(instanceId);

        if (!instance) {
            // Check if it's an implied delegation
            const uniqueInstances = this.agentInference.getUniqueAgentInstances();
            const impliedInstance = uniqueInstances.find(inst => inst.id === instanceId);

            if (!impliedInstance) {
                console.error('Agent instance not found:', instanceId);
                return;
            }

            // For implied instances, show basic info
            this.showImpliedAgentDetails(impliedInstance);
            return;
        }

        // Show full PM delegation details
        if (this.moduleViewer && typeof this.moduleViewer.showAgentInstance === 'function') {
            this.moduleViewer.showAgentInstance(instance);
        } else {
            // Fallback: show in console or basic modal
            console.log('Agent Instance Details:', {
                id: instanceId,
                agentName: instance.agentName,
                type: 'PM Delegation',
                eventCount: instance.agentEvents.length,
                startTime: instance.timestamp,
                pmCall: instance.pmCall
            });
        }
    }

    /**
     * Show implied agent details (agents without explicit PM delegation)
     * @param {Object} impliedInstance - Implied agent instance
     */
    showImpliedAgentDetails(impliedInstance) {
        if (this.moduleViewer && typeof this.moduleViewer.showImpliedAgent === 'function') {
            this.moduleViewer.showImpliedAgent(impliedInstance);
        } else {
            // Fallback: show in console or basic modal
            console.log('Implied Agent Details:', {
                id: impliedInstance.id,
                agentName: impliedInstance.agentName,
                type: 'Implied PM Delegation',
                eventCount: impliedInstance.eventCount,
                startTime: impliedInstance.timestamp,
                note: 'No explicit PM call found - inferred from agent activity'
            });
        }
    }

    /**
     * Show tool details by index
     */
    showToolDetailsByIndex(index) {
        const toolCalls = this.fileToolTracker.getToolCalls();
        const toolCallsArray = Array.from(toolCalls.entries());
        const filteredToolCalls = this.eventProcessor.applyToolCallFilters(toolCallsArray);

        if (index >= 0 && index < filteredToolCalls.length) {
            const [toolCallKey] = filteredToolCalls[index];
            this.showToolCallDetails(toolCallKey);
        }
    }

    /**
     * Show file details by index
     */
    showFileDetailsByIndex(index) {
        const fileOperations = this.fileToolTracker.getFileOperations();
        let filesArray = Array.from(fileOperations.entries());
        filesArray = this.eventProcessor.applyFilesFilters(filesArray);

        if (index >= 0 && index < filesArray.length) {
            const [filePath] = filesArray[index];
            this.showFileDetails(filePath);
        }
    }

    /**
     * Show tool call details
     */
    showToolCallDetails(toolCallKey) {
        const toolCall = this.fileToolTracker.getToolCall(toolCallKey);
        if (toolCall && this.moduleViewer) {
            this.moduleViewer.showToolCall(toolCall, toolCallKey);
        }
    }

    /**
     * Show file details
     */
    showFileDetails(filePath) {
        const fileData = this.fileToolTracker.getFileOperationsForFile(filePath);
        if (fileData && this.moduleViewer) {
            this.moduleViewer.showFileOperations(fileData, filePath);
        }
    }

    // ====================================
    // BACKWARD COMPATIBILITY METHODS
    // ====================================

    /**
     * Switch tab (backward compatibility)
     */
    switchTab(tabName) {
        this.uiStateManager.switchTab(tabName);
    }

    /**
     * Select card (backward compatibility)
     */
    selectCard(tabName, index, type, data) {
        this.uiStateManager.selectCard(tabName, index, type, data);
    }

    /**
     * Clear events (backward compatibility)
     */
    clearEvents() {
        this.exportManager.clearEvents();
    }

    /**
     * Export events (backward compatibility)
     */
    exportEvents() {
        this.exportManager.exportEvents();
    }

    /**
     * Clear selection (backward compatibility)
     */
    clearSelection() {
        this.uiStateManager.clearSelection();
        if (this.eventViewer) {
            this.eventViewer.clearSelection();
        }
        if (this.moduleViewer) {
            this.moduleViewer.clear();
        }
    }


    /**
     * Get current working directory (backward compatibility)
     */
    get currentWorkingDir() {
        return this.workingDirectoryManager.getCurrentWorkingDir();
    }

    /**
     * Set current working directory (backward compatibility)
     */
    set currentWorkingDir(dir) {
        this.workingDirectoryManager.setWorkingDirectory(dir);
    }

    /**
     * Get current tab (backward compatibility)
     */
    get currentTab() {
        return this.uiStateManager.getCurrentTab();
    }

    /**
     * Get selected card (backward compatibility)
     */
    get selectedCard() {
        return this.uiStateManager.getSelectedCard();
    }

    /**
     * Get file operations (backward compatibility)
     */
    get fileOperations() {
        return this.fileToolTracker.getFileOperations();
    }

    /**
     * Get tool calls (backward compatibility)
     */
    get toolCalls() {
        return this.fileToolTracker.getToolCalls();
    }


    /**
     * Get tab navigation state (backward compatibility)
     */
    get tabNavigation() {
        return this.uiStateManager ? this.uiStateManager.tabNavigation : null;
    }
}

// Global functions for backward compatibility
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

// File Viewer Modal Functions - Removed broken duplicate (using the one at line 1505)

window.copyFileContent = function() {
    const modal = document.getElementById('file-viewer-modal');
    if (!modal) return;

    const codeElement = modal.querySelector('.file-content-code');
    if (!codeElement) return;

    const text = codeElement.textContent;

    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            // Show brief feedback
            const button = modal.querySelector('.file-content-copy');
            if (button) {
                const originalText = button.textContent;
                button.textContent = '✅ Copied!';
                setTimeout(() => {
                    button.textContent = originalText;
                }, 2000);
            }
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

        const button = modal.querySelector('.file-content-copy');
        if (button) {
            const originalText = button.textContent;
            button.textContent = '✅ Copied!';
            setTimeout(() => {
                button.textContent = originalText;
            }, 2000);
        }
    }
};

function createFileViewerModal() {
    const modal = document.createElement('div');
    modal.id = 'file-viewer-modal';
    modal.className = 'modal file-viewer-modal';

    modal.innerHTML = `
        <div class="modal-content file-viewer-content">
            <div class="file-viewer-header">
                <h2 class="file-viewer-title">
                    <span class="file-viewer-icon">📄</span>
                    <span class="file-viewer-title-text">File Viewer</span>
                </h2>
                <div class="file-viewer-meta">
                    <span class="file-viewer-file-path"></span>
                    <span class="file-viewer-file-size"></span>
                </div>
                <button class="file-viewer-close" onclick="hideFileViewerModal()">
                    <span>&times;</span>
                </button>
            </div>
            <div class="file-viewer-body">
                <div class="file-viewer-loading">
                    <div class="loading-spinner"></div>
                    <span>Loading file content...</span>
                </div>
                <div class="file-viewer-error" style="display: none;">
                    <div class="error-icon">⚠️</div>
                    <div class="error-message"></div>
                    <div class="error-suggestions"></div>
                </div>
                <div class="file-viewer-content-area" style="display: none;">
                    <div class="file-viewer-toolbar">
                        <div class="file-viewer-info">
                            <span class="file-extension"></span>
                            <span class="file-encoding"></span>
                        </div>
                        <div class="file-viewer-actions">
                            <button class="file-content-copy" onclick="copyFileContent()">
                                📋 Copy
                            </button>
                        </div>
                    </div>
                    <div class="file-viewer-scroll-wrapper">
                        <pre class="file-content-display"><code class="file-content-code"></code></pre>
                    </div>
                </div>
            </div>
        </div>
    `;

    // Close modal when clicking outside
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            hideFileViewerModal();
        }
    });

    // Close modal with Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.style.display === 'flex') {
            hideFileViewerModal();
        }
    });

    return modal;
}

async function updateFileViewerModal(modal, filePath, workingDir) {
    // Update header info
    const filePathElement = modal.querySelector('.file-viewer-file-path');
    const fileSizeElement = modal.querySelector('.file-viewer-file-size');

    if (filePathElement) {
        filePathElement.textContent = filePath;
    }
    if (fileSizeElement) {
        fileSizeElement.textContent = '';
    }

    // Show loading state
    const loadingElement = modal.querySelector('.file-viewer-loading');
    const errorElement = modal.querySelector('.file-viewer-error');
    const contentArea = modal.querySelector('.file-viewer-content-area');
    
    if (loadingElement) {
        loadingElement.style.display = 'flex';
    }
    if (errorElement) {
        errorElement.style.display = 'none';
    }
    if (contentArea) {
        contentArea.style.display = 'none';
    }

    try {
        // Get the Socket.IO client
        const socket = window.socket || window.dashboard?.socketClient?.socket || window.socketClient?.socket;
        
        console.log('[FileViewer] Socket search results:', {
            'window.socket': !!window.socket,
            'window.socket.connected': window.socket?.connected,
            'dashboard.socketClient.socket': !!window.dashboard?.socketClient?.socket,
            'dashboard.socketClient.socket.connected': window.dashboard?.socketClient?.socket?.connected,
            'window.socketClient.socket': !!window.socketClient?.socket,
            'window.socketClient.socket.connected': window.socketClient?.socket?.connected
        });
        
        if (!socket) {
            throw new Error('No socket connection available. Please ensure the dashboard is connected.');
        }
        
        if (!socket.connected) {
            console.warn('[FileViewer] Socket found but not connected, attempting to use anyway...');
        }
        
        console.log('[FileViewer] Socket found, setting up listener for file_content_response');

        // Set up one-time listener for file content response
        const responsePromise = new Promise((resolve, reject) => {
            const responseHandler = (data) => {
                console.log('[FileViewer] Received file_content_response:', data);
                if (data.file_path === filePath) {
                    socket.off('file_content_response', responseHandler);
                    if (data.success) {
                        console.log('[FileViewer] File content loaded successfully');
                        resolve(data);
                    } else {
                        console.error('[FileViewer] File read failed:', data.error);
                        reject(new Error(data.error || 'Failed to read file'));
                    }
                }
            };

            socket.on('file_content_response', responseHandler);
            console.log('[FileViewer] Listener registered for file_content_response');

            // Timeout after 10 seconds
            setTimeout(() => {
                socket.off('file_content_response', responseHandler);
                console.error('[FileViewer] Request timeout after 10 seconds');
                reject(new Error('Request timeout - server did not respond'));
            }, 10000);
        });

        // Send file read request
        const requestData = {
            file_path: filePath,
            working_dir: workingDir
        };
        console.log('[FileViewer] Emitting read_file event with data:', requestData);
        socket.emit('read_file', requestData);

        // File viewer request sent

        // Wait for response
        const result = await responsePromise;
        // File content received successfully

        // Hide loading
        const loadingEl = modal.querySelector('.file-viewer-loading');
        if (loadingEl) {
            loadingEl.style.display = 'none';
        }

        // Show successful content
        displayFileContent(modal, result);

    } catch (error) {
        console.error('❌ Failed to fetch file content:', error);

        const loadingEl2 = modal.querySelector('.file-viewer-loading');
        if (loadingEl2) {
            loadingEl2.style.display = 'none';
        }

        // Create detailed error message
        let errorMessage = error.message || 'Unknown error occurred';
        let suggestions = [];

        if (error.message.includes('No socket connection')) {
            errorMessage = 'Failed to connect to the monitoring server';
            suggestions = [
                'Check if the monitoring server is running',
                'Verify the socket connection in the dashboard',
                'Try refreshing the page and reconnecting'
            ];
        } else if (error.message.includes('timeout')) {
            errorMessage = 'Request timed out';
            suggestions = [
                'The file may be too large to load quickly',
                'Check your network connection',
                'Try again in a few moments'
            ];
        } else if (error.message.includes('File does not exist')) {
            errorMessage = 'File not found';
            suggestions = [
                'The file may have been moved or deleted',
                'Check the file path spelling',
                'Refresh the file list to see current files'
            ];
        } else if (error.message.includes('Access denied')) {
            errorMessage = 'Access denied';
            suggestions = [
                'The file is outside the allowed directories',
                'File access is restricted for security reasons'
            ];
        }

        displayFileError(modal, {
            error: errorMessage,
            file_path: filePath,
            working_dir: workingDir,
            suggestions: suggestions
        });
    }
}

function displayFileContent(modal, result) {
    // Display file content in modal
    const contentArea = modal.querySelector('.file-viewer-content-area');
    const extensionElement = modal.querySelector('.file-extension');
    const encodingElement = modal.querySelector('.file-encoding');
    const fileSizeElement = modal.querySelector('.file-viewer-file-size');
    const codeElement = modal.querySelector('.file-content-code');

    // Update metadata
    if (extensionElement) extensionElement.textContent = `Type: ${result.extension || 'unknown'}`;
    if (encodingElement) encodingElement.textContent = `Encoding: ${result.encoding || 'unknown'}`;
    if (fileSizeElement) fileSizeElement.textContent = `Size: ${formatFileSize(result.file_size)}`;

    // Update content with basic syntax highlighting
    if (codeElement && result.content) {
        // Setting file content
        codeElement.innerHTML = highlightCode(result.content, result.extension);

        // Force scrolling to work by setting explicit heights
        const wrapper = modal.querySelector('.file-viewer-scroll-wrapper');
        if (wrapper) {
            // Give it a moment for content to render
            setTimeout(() => {
                const modalContent = modal.querySelector('.modal-content');
                const header = modal.querySelector('.file-viewer-header');
                const toolbar = modal.querySelector('.file-viewer-toolbar');

                const modalHeight = modalContent?.offsetHeight || 0;
                const headerHeight = header?.offsetHeight || 0;
                const toolbarHeight = toolbar?.offsetHeight || 0;

                const availableHeight = modalHeight - headerHeight - toolbarHeight - 40; // 40px for padding

                // Setting file viewer scroll height

                wrapper.style.maxHeight = `${availableHeight}px`;
                wrapper.style.overflowY = 'auto';
            }, 50);
        }
    } else {
        console.warn('⚠️ Missing codeElement or file content');
    }

    // Show content area
    if (contentArea) {
        contentArea.style.display = 'block';
        // File content area displayed
    }
}

function displayFileError(modal, result) {
    const errorArea = modal.querySelector('.file-viewer-error');
    const messageElement = modal.querySelector('.error-message');
    const suggestionsElement = modal.querySelector('.error-suggestions');

    let errorMessage = result.error || 'Unknown error occurred';

    if (messageElement) {
        messageElement.innerHTML = `
            <div class="error-main">${errorMessage}</div>
            ${result.file_path ? `<div class="error-file">File: ${result.file_path}</div>` : ''}
            ${result.working_dir ? `<div class="error-dir">Working directory: ${result.working_dir}</div>` : ''}
        `;
    }

    if (suggestionsElement) {
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
    }

    console.log('📋 Displaying file viewer error:', {
        originalError: result.error,
        processedMessage: errorMessage,
        suggestions: result.suggestions
    });

    if (errorArea) {
        errorArea.style.display = 'block';
    }
}

function highlightCode(code, extension) {
    /**
     * Apply basic syntax highlighting to code content
     * WHY: Provides basic highlighting for common file types to improve readability.
     * This is a simple implementation that can be enhanced with full syntax highlighting
     * libraries like highlight.js or Prism.js if needed.
     */

    // Escape HTML entities first
    const escaped = code
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;');

    // Basic highlighting based on file extension
    switch (extension) {
        case '.js':
        case '.jsx':
        case '.ts':
        case '.tsx':
            return highlightJavaScript(escaped);
        case '.py':
            return highlightPython(escaped);
        case '.json':
            return highlightJSON(escaped);
        case '.css':
            return highlightCSS(escaped);
        case '.html':
        case '.htm':
            return highlightHTML(escaped);
        case '.md':
        case '.markdown':
            return highlightMarkdown(escaped);
        default:
            // Return with line numbers for plain text
            return addLineNumbers(escaped);
    }
}

function highlightJavaScript(code) {
    return addLineNumbers(code
        .replace(/\b(function|const|let|var|if|else|for|while|return|import|export|class|extends)\b/g, '<span class="keyword">$1</span>')
        .replace(/(\/\*[\s\S]*?\*\/|\/\/.*)/g, '<span class="comment">$1</span>')
        .replace(/('[^']*'|"[^"]*"|`[^`]*`)/g, '<span class="string">$1</span>')
        .replace(/\b(\d+)\b/g, '<span class="number">$1</span>'));
}

function highlightPython(code) {
    return addLineNumbers(code
        .replace(/\b(def|class|if|elif|else|for|while|return|import|from|as|try|except|finally|with)\b/g, '<span class="keyword">$1</span>')
        .replace(/(#.*)/g, '<span class="comment">$1</span>')
        .replace(/('[^']*'|"[^"]*"|"""[\s\S]*?""")/g, '<span class="string">$1</span>')
        .replace(/\b(\d+)\b/g, '<span class="number">$1</span>'));
}

function highlightJSON(code) {
    return addLineNumbers(code
        .replace(/("[\w\s]*")\s*:/g, '<span class="property">$1</span>:')
        .replace(/:\s*(".*?")/g, ': <span class="string">$1</span>')
        .replace(/:\s*(\d+)/g, ': <span class="number">$1</span>')
        .replace(/:\s*(true|false|null)/g, ': <span class="keyword">$1</span>'));
}

function highlightCSS(code) {
    return addLineNumbers(code
        .replace(/([.#]?[\w-]+)\s*\{/g, '<span class="selector">$1</span> {')
        .replace(/([\w-]+)\s*:/g, '<span class="property">$1</span>:')
        .replace(/:\s*([^;]+);/g, ': <span class="value">$1</span>;')
        .replace(/(\/\*[\s\S]*?\*\/)/g, '<span class="comment">$1</span>'));
}

function highlightHTML(code) {
    return addLineNumbers(code
        .replace(/(&lt;\/?[\w-]+)/g, '<span class="tag">$1</span>')
        .replace(/([\w-]+)=(['"][^'"]*['"])/g, '<span class="attribute">$1</span>=<span class="string">$2</span>')
        .replace(/(&lt;!--[\s\S]*?--&gt;)/g, '<span class="comment">$1</span>'));
}

function highlightMarkdown(code) {
    return addLineNumbers(code
        .replace(/^(#{1,6})\s+(.*)$/gm, '<span class="header">$1</span> <span class="header-text">$2</span>')
        .replace(/\*\*(.*?)\*\*/g, '<span class="bold">**$1**</span>')
        .replace(/\*(.*?)\*/g, '<span class="italic">*$1*</span>')
        .replace(/`([^`]+)`/g, '<span class="code">`$1`</span>')
        .replace(/^\s*[-*+]\s+(.*)$/gm, '<span class="list-marker">•</span> $1'));
}

function addLineNumbers(code) {
    const lines = code.split('\n');
    return lines.map((line, index) =>
        `<span class="line-number">${String(index + 1).padStart(3, ' ')}</span> ${line || ' '}`
    ).join('\n');
}

function formatFileSize(bytes) {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// File Viewer Modal Functions
window.showFileViewerModal = async function(filePath) {
    console.log('[FileViewer] Opening file:', filePath);
    
    // Use the dashboard's current working directory
    let workingDir = '';
    if (window.dashboard && window.dashboard.currentWorkingDir) {
        workingDir = window.dashboard.currentWorkingDir;
        console.log('[FileViewer] Using working directory:', workingDir);
    }

    // Create modal if it doesn't exist
    let modal = document.getElementById('file-viewer-modal');
    if (!modal) {
        console.log('[FileViewer] Creating new modal');
        modal = createFileViewerModal();
        document.body.appendChild(modal);

        // Small delay to ensure DOM is fully updated
        await new Promise(resolve => setTimeout(resolve, 10));
    }

    // Show the modal as flex container first (ensures proper rendering)
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden'; // Prevent background scrolling

    // Update modal content
    updateFileViewerModal(modal, filePath, workingDir).catch(error => {
        console.error('Error updating file viewer modal:', error);
        // Show error in the modal
        displayFileContentError(modal, { error: error.message });
    });
};

window.hideFileViewerModal = function() {
    const modal = document.getElementById('file-viewer-modal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = ''; // Restore background scrolling
    }
};

window.copyFileContent = function() {
    const modal = document.getElementById('file-viewer-modal');
    if (!modal) return;

    const codeElement = modal.querySelector('.file-content-code');
    if (!codeElement) return;

    const text = codeElement.textContent;

    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(() => {
            // Show brief feedback
            const button = modal.querySelector('.file-content-copy');
            if (button) {
                const originalText = button.textContent;
                button.textContent = '✅ Copied!';
                setTimeout(() => {
                    button.textContent = originalText;
                }, 2000);
            }
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

        const button = modal.querySelector('.file-content-copy');
        if (button) {
            const originalText = button.textContent;
            button.textContent = '✅ Copied!';
            setTimeout(() => {
                button.textContent = originalText;
            }, 2000);
        }
    }
};




function displayFileContentError(modal, result) {
    const errorArea = modal.querySelector('.file-viewer-error');
    const messageElement = modal.querySelector('.error-message');
    const suggestionsElement = modal.querySelector('.error-suggestions');
    const loadingElement = modal.querySelector('.file-viewer-loading');
    const contentArea = modal.querySelector('.file-viewer-content-area');
    
    // Hide loading and content areas, show error
    if (loadingElement) {
        loadingElement.style.display = 'none';
    }
    if (contentArea) {
        contentArea.style.display = 'none';
    }
    if (errorArea) {
        errorArea.style.display = 'flex';
    }

    // Create user-friendly error messages
    let errorMessage = result.error || 'Unknown error occurred';

    if (errorMessage.includes('not found')) {
        errorMessage = '📁 File not found or not accessible';
    } else if (errorMessage.includes('permission')) {
        errorMessage = '🔒 Permission denied accessing this file';
    } else if (errorMessage.includes('too large')) {
        errorMessage = '📏 File is too large to display';
    } else if (errorMessage.includes('socket connection')) {
        errorMessage = '🔌 Not connected to the server. Please check your connection.';
    } else if (errorMessage.includes('timeout')) {
        errorMessage = '⏱️ Request timed out. The server may be busy or unresponsive.';
    } else if (!errorMessage.includes('📁') && !errorMessage.includes('🔒') && !errorMessage.includes('📏')) {
        errorMessage = `⚠️ ${errorMessage}`;
    }

    if (messageElement) {
        messageElement.textContent = errorMessage;
    }

    // Add suggestions if available
    if (suggestionsElement) {
        if (result.suggestions && result.suggestions.length > 0) {
            suggestionsElement.innerHTML = `
                <h4>Suggestions:</h4>
                <ul>
                    ${result.suggestions.map(suggestion => `<li>${suggestion}</li>`).join('')}
                </ul>
            `;
        } else {
            suggestionsElement.innerHTML = `
                <h4>Try:</h4>
                <ul>
                    <li>Check if the file exists and is readable</li>
                    <li>Verify file permissions</li>
                    <li>Ensure the monitoring server has access to this file</li>
                </ul>
            `;
        }
    }

    console.log('📋 Displaying file content error:', {
        originalError: result.error,
        processedMessage: errorMessage,
        suggestions: result.suggestions
    });

    if (errorArea) {
        errorArea.style.display = 'block';
    }
}

// Search Viewer Modal Functions
window.showSearchViewerModal = function(searchParams, searchResults) {
    // Create modal if it doesn't exist
    let modal = document.getElementById('search-viewer-modal');
    if (!modal) {
        modal = createSearchViewerModal();
        document.body.appendChild(modal);
    }

    // Update modal content
    updateSearchViewerModal(modal, searchParams, searchResults);

    // Show the modal as flex container
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden'; // Prevent background scrolling
};

window.hideSearchViewerModal = function() {
    const modal = document.getElementById('search-viewer-modal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = ''; // Restore background scrolling
    }
};

function createSearchViewerModal() {
    const modal = document.createElement('div');
    modal.id = 'search-viewer-modal';
    modal.className = 'modal search-viewer-modal';

    modal.innerHTML = `
        <div class="modal-content search-viewer-content">
            <div class="search-viewer-header">
                <h2 class="search-viewer-title">
                    <span class="search-viewer-icon">🔍</span>
                    <span class="search-viewer-title-text">Search Results</span>
                </h2>
                <button class="search-viewer-close" onclick="hideSearchViewerModal()">
                    <span>&times;</span>
                </button>
            </div>
            <div class="search-viewer-body">
                <div class="search-params-section">
                    <h3>Search Parameters</h3>
                    <pre class="search-params-display"></pre>
                </div>
                <div class="search-results-section">
                    <h3>Search Results</h3>
                    <div class="search-results-display"></div>
                </div>
            </div>
        </div>
    `;

    // Close modal when clicking outside
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            hideSearchViewerModal();
        }
    });

    // Close modal on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.style.display === 'flex') {
            hideSearchViewerModal();
        }
    });

    return modal;
}

function updateSearchViewerModal(modal, searchParams, searchResults) {
    const paramsDisplay = modal.querySelector('.search-params-display');
    const resultsDisplay = modal.querySelector('.search-results-display');

    // Display search parameters in formatted JSON
    if (paramsDisplay && searchParams) {
        paramsDisplay.textContent = JSON.stringify(searchParams, null, 2);
    }

    // Display search results
    if (resultsDisplay && searchResults) {
        let resultsHTML = '';
        
        if (typeof searchResults === 'string') {
            // If results are a string, display as preformatted text
            resultsHTML = `<pre class="search-results-text">${escapeHtml(searchResults)}</pre>`;
        } else if (Array.isArray(searchResults)) {
            // If results are an array, display as a list
            resultsHTML = '<ul class="search-results-list">';
            searchResults.forEach(result => {
                if (typeof result === 'object') {
                    resultsHTML += `<li><pre>${JSON.stringify(result, null, 2)}</pre></li>`;
                } else {
                    resultsHTML += `<li>${escapeHtml(String(result))}</li>`;
                }
            });
            resultsHTML += '</ul>';
        } else if (typeof searchResults === 'object') {
            // If results are an object, display as formatted JSON
            resultsHTML = `<pre class="search-results-json">${JSON.stringify(searchResults, null, 2)}</pre>`;
        } else {
            // Fallback: display as text
            resultsHTML = `<div class="search-results-text">${escapeHtml(String(searchResults))}</div>`;
        }
        
        resultsDisplay.innerHTML = resultsHTML;
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Global window functions for backward compatibility
window.showAgentInstanceDetails = function(instanceId) {
    if (window.dashboard && typeof window.dashboard.showAgentInstanceDetails === 'function') {
        window.dashboard.showAgentInstanceDetails(instanceId);
    } else {
        console.error('Dashboard not available or method not found');
    }
};

// Initialize dashboard when page loads
document.addEventListener('DOMContentLoaded', function() {
    try {
        // Create dashboard instance
        window.dashboard = new Dashboard();
        
        // Call post-initialization setup that requires window.dashboard
        // This must happen after window.dashboard is set
        if (window.dashboard && typeof window.dashboard.postInit === 'function') {
            window.dashboard.postInit();
        }
        
        console.log('Dashboard loaded and initialized successfully');
        
        // Dispatch custom event to signal dashboard ready
        document.dispatchEvent(new CustomEvent('dashboardReady', {
            detail: { dashboard: window.dashboard }
        }));
    } catch (error) {
        console.error('Failed to initialize dashboard:', error);
        // Show user-friendly error message
        document.body.innerHTML = `
            <div style="padding: 20px; font-family: sans-serif;">
                <h1>Dashboard Initialization Error</h1>
                <p>The dashboard failed to load properly. Please refresh the page or check the console for details.</p>
                <pre style="background: #f5f5f5; padding: 10px; border-radius: 4px;">${error.message}</pre>
            </div>
        `;
    }
});

// ES6 Module export
export { Dashboard };
export default Dashboard;
