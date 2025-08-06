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
class Dashboard {
    constructor() {
        // Core components (existing)
        this.eventViewer = null;
        this.moduleViewer = null;
        this.sessionManager = null;
        
        // New modular components
        this.socketManager = null;
        this.agentInference = null;
        this.uiStateManager = null;
        this.eventProcessor = null;
        this.exportManager = null;
        this.workingDirectoryManager = null;
        this.fileToolTracker = null;
        
        // Initialize the dashboard
        this.init();
    }

    /**
     * Initialize the dashboard and all modules
     */
    init() {
        console.log('Initializing refactored Claude MPM Dashboard...');
        
        // Initialize modules in dependency order
        this.initializeSocketManager();
        this.initializeCoreComponents();
        this.initializeAgentInference();
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
     * Initialize agent inference system
     */
    initializeAgentInference() {
        this.agentInference = new AgentInference(this.eventViewer);
        this.agentInference.initialize();
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
                console.log('[DASHBOARD-INIT-DEBUG] Connection established, waiting for directory to be ready...');
                
                // Wait for working directory to be properly initialized
                this.workingDirectoryManager.whenDirectoryReady(() => {
                    const currentDir = this.workingDirectoryManager.getCurrentWorkingDir();
                    console.log('[DASHBOARD-INIT-DEBUG] Directory ready, requesting git branch for:', currentDir);
                    this.workingDirectoryManager.updateGitBranch(currentDir);
                });
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
     * Render agents tab with unique instance view (one row per PM delegation)
     */
    renderAgents() {
        const agentsList = document.getElementById('agents-list');
        if (!agentsList) return;

        // Process agent inference to get PM delegations
        this.agentInference.processAgentInference();
        
        // Generate HTML for unique agent instances
        const events = this.eventProcessor.getFilteredEventsForTab('agents');
        const agentHTML = this.eventProcessor.generateAgentHTML(events);
        
        agentsList.innerHTML = agentHTML;
        this.exportManager.scrollListToBottom('agents-list');
        
        // Update filter dropdowns with unique instances
        const uniqueInstances = this.agentInference.getUniqueAgentInstances();
        this.updateAgentsFilterDropdowns(uniqueInstances);
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
            console.log('No agent types found for filter. Unique instances:', uniqueInstances.length);
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

// File Viewer Modal Functions - REMOVED DUPLICATE (keeping the one at line 1553)
window.showFileViewerModal = function(filePath, workingDir) {
    // Use the dashboard's current working directory if not provided
    if (!workingDir && window.dashboard && window.dashboard.currentWorkingDir) {
        workingDir = window.dashboard.currentWorkingDir;
    }
    
    // Create modal if it doesn't exist
    let modal = document.getElementById('file-viewer-modal');
    if (!modal) {
        modal = createFileViewerModal();
        document.body.appendChild(modal);
    }
    
    // Update modal content
    updateFileViewerModal(modal, filePath, workingDir);
    
    // Show the modal as flex container
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden'; // Prevent background scrolling
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
        
        const button = modal.querySelector('.file-content-copy');
        const originalText = button.textContent;
        button.textContent = '✅ Copied!';
        setTimeout(() => {
            button.textContent = originalText;
        }, 2000);
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
    
    filePathElement.textContent = filePath;
    fileSizeElement.textContent = '';
    
    // Show loading state
    modal.querySelector('.file-viewer-loading').style.display = 'flex';
    modal.querySelector('.file-viewer-error').style.display = 'none';
    modal.querySelector('.file-viewer-content-area').style.display = 'none';
    
    try {
        // Get the Socket.IO client
        const socket = window.socket || window.dashboard?.socketClient?.socket;
        if (!socket) {
            throw new Error('No socket connection available');
        }
        
        // Set up one-time listener for file content response
        const responsePromise = new Promise((resolve, reject) => {
            const responseHandler = (data) => {
                if (data.file_path === filePath) {
                    socket.off('file_content_response', responseHandler);
                    if (data.success) {
                        resolve(data);
                    } else {
                        reject(new Error(data.error || 'Failed to read file'));
                    }
                }
            };
            
            socket.on('file_content_response', responseHandler);
            
            // Timeout after 10 seconds
            setTimeout(() => {
                socket.off('file_content_response', responseHandler);
                reject(new Error('Request timeout'));
            }, 10000);
        });
        
        // Send file read request
        socket.emit('read_file', {
            file_path: filePath,
            working_dir: workingDir
        });
        
        console.log('📄 File viewer request sent:', {
            filePath,
            workingDir
        });
        
        // Wait for response
        const result = await responsePromise;
        console.log('📦 File content received:', result);
        
        // Hide loading
        modal.querySelector('.file-viewer-loading').style.display = 'none';
        
        // Show successful content
        displayFileContent(modal, result);
        
    } catch (error) {
        console.error('❌ Failed to fetch file content:', error);
        
        modal.querySelector('.file-viewer-loading').style.display = 'none';
        
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
    console.log('📝 displayFileContent called with:', result);
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
        console.log('💡 Setting file content, length:', result.content.length);
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
                
                console.log('🎯 Setting file viewer scroll height:', {
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
        console.warn('⚠️ Missing codeElement or file content');
    }
    
    // Show content area
    if (contentArea) {
        contentArea.style.display = 'block';
        console.log('✅ File content area displayed');
    }
}

function displayFileError(modal, result) {
    const errorArea = modal.querySelector('.file-viewer-error');
    const messageElement = modal.querySelector('.error-message');
    const suggestionsElement = modal.querySelector('.error-suggestions');
    
    let errorMessage = result.error || 'Unknown error occurred';
    
    messageElement.innerHTML = `
        <div class="error-main">${errorMessage}</div>
        ${result.file_path ? `<div class="error-file">File: ${result.file_path}</div>` : ''}
        ${result.working_dir ? `<div class="error-dir">Working directory: ${result.working_dir}</div>` : ''}
    `;
    
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
    
    console.log('📋 Displaying file viewer error:', {
        originalError: result.error,
        processedMessage: errorMessage,
        suggestions: result.suggestions
    });
    
    errorArea.style.display = 'block';
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

// Git Diff Modal Functions - restored from original dashboard
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
        if (e.key === 'Escape' && modal.style.display === 'flex') {
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
        console.log('📋 Git diff request parameters:', {
            filePath,
            timestamp,
            workingDir,
            urlParams: params.toString()
        });
        
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
    }
}

function displayGitDiffError(modal, result) {
    const errorArea = modal.querySelector('.git-diff-error');
    const messageElement = modal.querySelector('.error-message');
    const suggestionsElement = modal.querySelector('.error-suggestions');
    
    // Create more user-friendly error messages
    let errorMessage = result.error || 'Unknown error occurred';
    let isUntracked = false;
    
    if (errorMessage.includes('not tracked by git')) {
        errorMessage = '📝 This file is not tracked by git yet';
        isUntracked = true;
    } else if (errorMessage.includes('No git history found')) {
        errorMessage = '📋 No git history available for this file';
    }
    
    messageElement.innerHTML = `
        <div class="error-main">${errorMessage}</div>
        ${result.file_path ? `<div class="error-file">File: ${result.file_path}</div>` : ''}
        ${result.working_dir ? `<div class="error-dir">Working directory: ${result.working_dir}</div>` : ''}
    `;
    
    if (result.suggestions && result.suggestions.length > 0) {
        const suggestionTitle = isUntracked ? 'How to track this file:' : 'Suggestions:';
        suggestionsElement.innerHTML = `
            <h4>${suggestionTitle}</h4>
            <ul>
                ${result.suggestions.map(s => `<li>${s}</li>`).join('')}
            </ul>
        `;
    } else {
        suggestionsElement.innerHTML = '';
    }
    
    console.log('📋 Displaying git diff error:', {
        originalError: result.error,
        processedMessage: errorMessage,
        isUntracked,
        suggestions: result.suggestions
    });
    
    errorArea.style.display = 'block';
}

// File Viewer Modal Functions
window.showFileViewerModal = function(filePath) {
    // Use the dashboard's current working directory
    let workingDir = '';
    if (window.dashboard && window.dashboard.currentWorkingDir) {
        workingDir = window.dashboard.currentWorkingDir;
    }
    
    // Create modal if it doesn't exist
    let modal = document.getElementById('file-viewer-modal');
    if (!modal) {
        modal = createFileViewerModal();
        document.body.appendChild(modal);
    }
    
    // Update modal content
    updateFileViewerModal(modal, filePath, workingDir);
    
    // Show the modal as flex container
    modal.style.display = 'flex';
    document.body.style.overflow = 'hidden'; // Prevent background scrolling
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
        
        const button = modal.querySelector('.file-content-copy');
        const originalText = button.textContent;
        button.textContent = '✅ Copied!';
        setTimeout(() => {
            button.textContent = originalText;
        }, 2000);
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
                    <span class="file-viewer-icon">👁️</span>
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
                    <span>Loading file contents...</span>
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
                            <span class="file-encoding">UTF-8</span>
                        </div>
                        <div class="file-viewer-actions">
                            <button class="file-content-copy" onclick="copyFileContent()">
                                📋 Copy
                            </button>
                        </div>
                    </div>
                    <div class="file-viewer-scroll-wrapper">
                        <pre class="file-content-display line-numbers"><code class="file-content-code"></code></pre>
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
    const fileExtensionElement = modal.querySelector('.file-extension');
    
    filePathElement.textContent = filePath;
    
    // Extract and display file extension
    const extension = filePath.split('.').pop() || 'txt';
    fileExtensionElement.textContent = `Type: ${extension.toUpperCase()}`;
    
    // Show loading state
    modal.querySelector('.file-viewer-loading').style.display = 'flex';
    modal.querySelector('.file-viewer-error').style.display = 'none';
    modal.querySelector('.file-viewer-content-area').style.display = 'none';
    
    try {
        // Get the Socket.IO server port with multiple fallbacks
        let port = 8765; // Default fallback
        
        // Try to get port from socketClient first
        if (window.dashboard && window.dashboard.socketClient && window.dashboard.socketClient.port) {
            port = window.dashboard.socketClient.port;
        }
        // Fallback to port input field if socketClient port is not available
        else if (document.getElementById('port-input')) {
            const portInput = document.getElementById('port-input');
            if (portInput.value && !isNaN(portInput.value)) {
                port = parseInt(portInput.value);
            }
        }
        
        // Construct API request URL for file content
        const params = new URLSearchParams();
        params.append('file_path', filePath);
        if (workingDir) {
            params.append('working_dir', workingDir);
        }
        
        const requestUrl = `http://localhost:${port}/api/file-content?${params}`;
        console.log('🌐 Making file content request to:', requestUrl);
        console.log('📄 File content request parameters:', {
            filePath,
            workingDir,
            urlParams: params.toString()
        });
        
        // Test server connectivity first
        try {
            const healthResponse = await fetch(`http://localhost:${port}/health`, {
                method: 'GET',
                mode: 'cors',
                timeout: 5000
            });
            
            if (!healthResponse.ok) {
                throw new Error(`Health check failed: ${healthResponse.status}`);
            }
            
            console.log('✅ Server health check passed');
        } catch (healthError) {
            console.warn('⚠️ Server health check failed:', healthError);
            throw new Error(`Unable to connect to monitoring server on port ${port}. Please ensure the server is running.`);
        }
        
        // Make the actual file content request
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
        console.log('📦 File content received:', result);
        
        // Hide loading
        modal.querySelector('.file-viewer-loading').style.display = 'none';
        
        if (result.success) {
            console.log('📊 Displaying file content');
            // Show file content
            displayFileContent(modal, result, extension);
        } else {
            console.log('⚠️ Displaying file content error:', result);
            // Show error
            displayFileContentError(modal, result);
        }
        
    } catch (error) {
        console.error('❌ Failed to fetch file content:', error);
        
        modal.querySelector('.file-viewer-loading').style.display = 'none';
        
        // Create detailed error message based on error type
        let errorMessage = `Network error: ${error.message}`;
        let suggestions = [];
        
        if (error.message.includes('Failed to fetch')) {
            errorMessage = 'Failed to connect to the monitoring server';
            suggestions = [
                'Check if the monitoring server is running on port 8765',
                'Verify the port configuration in the dashboard',
                'Ensure CORS is enabled on the server'
            ];
        } else if (error.message.includes('Health check failed')) {
            errorMessage = 'Unable to connect to monitoring server';
            suggestions = [
                'The server may be starting up - try again in a few seconds',
                'Check if another process is using the port',
                'Restart the claude-mpm monitoring server'
            ];
        } else if (error.message.includes('HTTP 404')) {
            errorMessage = 'File content API endpoint not found';
            suggestions = [
                'The server may be running an older version',
                'Try restarting the monitoring server',
                'Check server logs for errors'
            ];
        } else if (error.message.includes('timeout')) {
            errorMessage = 'Request timed out while fetching file content';
            suggestions = [
                'File may be too large or server is slow',
                'Try again in a moment',
                'Check server logs for performance issues'
            ];
        }
        
        displayFileContentError(modal, {
            success: false,
            error: errorMessage,
            suggestions: suggestions
        });
    }
}

function displayFileContent(modal, result, extension) {
    console.log('📝 displayFileContent called with:', result);
    const contentArea = modal.querySelector('.file-viewer-content-area');
    const fileSizeElement = modal.querySelector('.file-viewer-file-size');
    const codeElement = modal.querySelector('.file-content-code');
    
    console.log('🔍 File content elements found:', {
        contentArea: !!contentArea,
        fileSizeElement: !!fileSizeElement,
        codeElement: !!codeElement
    });
    
    // Update file size
    if (fileSizeElement && result.file_size) {
        const sizeInBytes = result.file_size;
        const sizeFormatted = sizeInBytes < 1024 
            ? `${sizeInBytes} bytes`
            : sizeInBytes < 1024 * 1024
            ? `${(sizeInBytes / 1024).toFixed(1)} KB`
            : `${(sizeInBytes / (1024 * 1024)).toFixed(1)} MB`;
        fileSizeElement.textContent = `Size: ${sizeFormatted}`;
    }
    
    // Set up content with syntax highlighting
    if (codeElement && result.content) {
        // Determine language for Prism.js
        const languageMap = {
            'js': 'javascript',
            'jsx': 'javascript',
            'ts': 'typescript',
            'tsx': 'typescript',
            'py': 'python',
            'rb': 'ruby',
            'php': 'php',
            'html': 'html',
            'htm': 'html',
            'css': 'css',
            'scss': 'scss',
            'sass': 'sass',
            'json': 'json',
            'xml': 'xml',
            'yaml': 'yaml',
            'yml': 'yaml',
            'md': 'markdown',
            'sh': 'bash',
            'bash': 'bash',
            'zsh': 'bash',
            'sql': 'sql',
            'go': 'go',
            'java': 'java',
            'c': 'c',
            'cpp': 'cpp',
            'h': 'c',
            'hpp': 'cpp'
        };
        
        const language = languageMap[extension.toLowerCase()] || 'text';
        
        // Set up code element with Prism.js classes
        codeElement.className = `file-content-code language-${language}`;
        codeElement.textContent = result.content;
        
        // Apply syntax highlighting with Prism.js if available
        if (window.Prism) {
            // Add line numbers
            codeElement.parentElement.className = 'file-content-display line-numbers';
            
            // Apply highlighting
            window.Prism.highlightElement(codeElement);
        }
        
        contentArea.style.display = 'flex';
        
        console.log('✅ File content displayed successfully');
    } else {
        console.error('❌ Missing code element or content');
    }
}

function displayFileContentError(modal, result) {
    const errorArea = modal.querySelector('.file-viewer-error');
    const messageElement = modal.querySelector('.error-message');
    const suggestionsElement = modal.querySelector('.error-suggestions');
    
    // Create user-friendly error messages
    let errorMessage = result.error || 'Unknown error occurred';
    
    if (errorMessage.includes('not found')) {
        errorMessage = '📁 File not found or not accessible';
    } else if (errorMessage.includes('permission')) {
        errorMessage = '🔒 Permission denied accessing this file';
    } else if (errorMessage.includes('too large')) {
        errorMessage = '📏 File is too large to display';
    } else if (!errorMessage.includes('📁') && !errorMessage.includes('🔒') && !errorMessage.includes('📏')) {
        errorMessage = `⚠️ ${errorMessage}`;
    }
    
    messageElement.textContent = errorMessage;
    
    // Add suggestions if available
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
    
    console.log('📋 Displaying file content error:', {
        originalError: result.error,
        processedMessage: errorMessage,
        suggestions: result.suggestions
    });
    
    errorArea.style.display = 'block';
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
    window.dashboard = new Dashboard();
    console.log('Dashboard loaded and initialized');
});