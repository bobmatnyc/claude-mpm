/**
 * Code Tree Component
 * 
 * D3.js-based tree visualization for displaying AST-based code structure.
 * Shows modules, classes, functions, and methods with complexity-based coloring.
 * Provides real-time updates during code analysis.
 */

class CodeTree {
    constructor() {
        this.container = null;
        this.svg = null;
        this.treeData = null;
        this.root = null;
        this.treeLayout = null;
        this.treeGroup = null;
        this.nodes = new Map();
        this.stats = {
            files: 0,
            classes: 0,
            functions: 0,
            methods: 0,
            lines: 0
        };
        this.margin = {top: 20, right: 150, bottom: 20, left: 150};
        this.width = 960 - this.margin.left - this.margin.right;
        this.height = 600 - this.margin.top - this.margin.bottom;
        this.nodeId = 0;
        this.duration = 750;
        this.languageFilter = 'all';
        this.searchTerm = '';
        this.tooltip = null;
        this.initialized = false;
        this.analyzing = false;
        this.selectedNode = null;
        this.socket = null;
    }

    /**
     * Initialize the code tree visualization
     */
    initialize() {
        console.log('CodeTree.initialize() called');
        
        if (this.initialized) {
            console.log('Code tree already initialized');
            return;
        }
        
        this.container = document.getElementById('code-tree-container');
        if (!this.container) {
            console.error('Code tree container not found');
            return;
        }
        
        console.log('Code tree container found:', this.container);
        
        // Check if tab is visible
        const tabPanel = document.getElementById('code-tab');
        if (!tabPanel) {
            console.error('Code tab panel not found');
            return;
        }
        
        console.log('Code tab panel found, active:', tabPanel.classList.contains('active'));
        
        // Initialize always
        this.setupControls();
        this.initializeTreeData();
        this.subscribeToEvents();
        
        // Only create visualization if tab is visible
        if (tabPanel.classList.contains('active')) {
            console.log('Tab is active, creating visualization');
            this.createVisualization();
            if (this.root && this.svg) {
                this.update(this.root);
            }
        } else {
            console.log('Tab is not active, deferring visualization');
        }
        
        this.initialized = true;
        console.log('Code tree initialization complete');
    }

    /**
     * Render visualization when tab becomes visible
     */
    renderWhenVisible() {
        console.log('CodeTree.renderWhenVisible() called');
        console.log('Current state - initialized:', this.initialized, 'svg:', !!this.svg);
        
        if (!this.initialized) {
            console.log('Not initialized, calling initialize()');
            this.initialize();
            return;
        }
        
        if (!this.svg) {
            console.log('No SVG found, creating visualization');
            this.createVisualization();
            if (this.svg && this.treeGroup) {
                console.log('SVG created, updating tree');
                this.update(this.root);
            } else {
                console.log('Failed to create SVG or treeGroup');
            }
        } else {
            console.log('SVG exists, forcing update');
            // Force update with current data
            if (this.root && this.svg) {
                this.update(this.root);
            }
        }
    }

    /**
     * Setup control handlers
     */
    setupControls() {
        // Analyze button
        const analyzeBtn = document.getElementById('analyze-code');
        if (analyzeBtn) {
            analyzeBtn.addEventListener('click', () => this.startAnalysis());
        }
        
        // Cancel button
        const cancelBtn = document.getElementById('cancel-analysis');
        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.cancelAnalysis());
        }

        // Expand all button
        const expandAllBtn = document.getElementById('code-expand-all');
        if (expandAllBtn) {
            expandAllBtn.addEventListener('click', () => this.expandAll());
        }

        // Collapse all button
        const collapseAllBtn = document.getElementById('code-collapse-all');
        if (collapseAllBtn) {
            collapseAllBtn.addEventListener('click', () => this.collapseAll());
        }

        // Reset zoom button
        const resetZoomBtn = document.getElementById('code-reset-zoom');
        if (resetZoomBtn) {
            resetZoomBtn.addEventListener('click', () => this.resetZoom());
        }
        
        // Toggle legend button
        const toggleLegendBtn = document.getElementById('code-toggle-legend');
        if (toggleLegendBtn) {
            toggleLegendBtn.addEventListener('click', () => this.toggleLegend());
        }

        // Language filter
        const languageFilter = document.getElementById('language-filter');
        if (languageFilter) {
            languageFilter.addEventListener('change', (e) => {
                this.languageFilter = e.target.value;
                this.filterByLanguage();
            });
        }

        // Search input
        const searchInput = document.getElementById('code-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.searchTerm = e.target.value.toLowerCase();
                this.highlightSearchResults();
            });
        }
    }

    /**
     * Create D3 visualization
     */
    createVisualization() {
        console.log('Creating code tree visualization');
        
        // Check if D3 is available
        if (typeof d3 === 'undefined') {
            console.error('D3.js is not loaded! Cannot create code tree visualization.');
            return;
        }
        
        console.log('D3 is available:', typeof d3);
        
        const container = document.getElementById('code-tree');
        if (!container) {
            console.error('Code tree div not found');
            return;
        }
        
        console.log('Code tree div found:', container);
        
        // Create root if it doesn't exist
        if (!this.root && this.treeData) {
            console.log('Creating D3 hierarchy from tree data');
            this.root = d3.hierarchy(this.treeData);
            this.root.x0 = this.height / 2;
            this.root.y0 = 0;
        }

        // Clear any existing SVG
        d3.select(container).selectAll("*").remove();

        // Get container dimensions
        const rect = container.getBoundingClientRect();
        this.width = rect.width - this.margin.left - this.margin.right;
        this.height = Math.max(500, rect.height) - this.margin.top - this.margin.bottom;

        // Create SVG
        this.svg = d3.select(container)
            .append('svg')
            .attr('width', '100%')
            .attr('height', '100%')
            .attr('viewBox', `0 0 ${rect.width} ${rect.height}`)
            .call(d3.zoom()
                .scaleExtent([0.1, 3])
                .on('zoom', (event) => {
                    this.treeGroup.attr('transform', event.transform);
                }));

        this.treeGroup = this.svg.append('g')
            .attr('transform', `translate(${this.margin.left},${this.margin.top})`);

        // Create tree layout
        this.treeLayout = d3.tree()
            .size([this.height, this.width]);

        // Create tooltip
        this.tooltip = d3.select('body').append('div')
            .attr('class', 'code-tooltip')
            .style('opacity', 0);
    }

    /**
     * Initialize tree data structure
     */
    initializeTreeData() {
        console.log('Initializing tree data...');
        
        this.treeData = {
            name: 'Project Root',
            type: 'module',
            path: '/',
            complexity: 0,
            children: []
        };

        // Only create D3 hierarchy if D3 is available
        if (typeof d3 !== 'undefined') {
            this.root = d3.hierarchy(this.treeData);
            this.root.x0 = this.height / 2;
            this.root.y0 = 0;
            console.log('Tree root created:', this.root);
        } else {
            console.warn('D3 not available yet, deferring hierarchy creation');
            this.root = null;
        }
    }

    /**
     * Subscribe to Socket.IO events
     */
    subscribeToEvents() {
        // Try multiple socket sources
        this.getSocket();
        
        if (this.socket) {
            console.log('CodeTree: Socket available, subscribing to events');
            
            // Code analysis events - match the server-side event names
            this.socket.on('code:analysis:start', (data) => this.handleAnalysisStart(data));
            this.socket.on('code:analysis:accepted', (data) => this.handleAnalysisAccepted(data));
            this.socket.on('code:analysis:queued', (data) => this.handleAnalysisQueued(data));
            this.socket.on('code:analysis:cancelled', (data) => this.handleAnalysisCancelled(data));
            this.socket.on('code:analysis:progress', (data) => this.handleProgress(data));
            this.socket.on('code:analysis:complete', (data) => this.handleAnalysisComplete(data));
            this.socket.on('code:analysis:error', (data) => this.handleAnalysisError(data));
            
            // File and node events
            this.socket.on('code:file:start', (data) => this.handleFileStart(data));
            this.socket.on('code:file:complete', (data) => this.handleFileComplete(data));
            this.socket.on('code:node:found', (data) => this.handleNodeFound(data));
        } else {
            console.warn('CodeTree: Socket not available yet, will retry on analysis');
        }
    }
    
    /**
     * Get socket connection from available sources
     */
    getSocket() {
        // Try multiple sources for the socket
        if (!this.socket) {
            // Try window.socket first (most common)
            if (window.socket) {
                this.socket = window.socket;
                console.log('CodeTree: Using window.socket');
            }
            // Try from dashboard's socketClient
            else if (window.dashboard?.socketClient?.socket) {
                this.socket = window.dashboard.socketClient.socket;
                console.log('CodeTree: Using dashboard.socketClient.socket');
            }
            // Try from socketClient directly
            else if (window.socketClient?.socket) {
                this.socket = window.socketClient.socket;
                console.log('CodeTree: Using socketClient.socket');
            }
        }
        return this.socket;
    }

    /**
     * Start code analysis
     */
    startAnalysis() {
        if (this.analyzing) {
            console.log('Analysis already in progress');
            return;
        }

        console.log('Starting code analysis...');
        
        // Ensure socket is available
        this.getSocket();
        if (!this.socket) {
            console.error('Socket not available');
            this.showNotification('Cannot connect to server. Please check connection.', 'error');
            return;
        }
        
        // Re-subscribe to events if needed (in case socket reconnected)
        if (!this.socket._callbacks || !this.socket._callbacks['code:analysis:start']) {
            console.log('Re-subscribing to code analysis events');
            this.subscribeToEvents();
        }
        
        this.analyzing = true;
        
        // Update button state - but keep it responsive
        const analyzeBtn = document.getElementById('analyze-code');
        const cancelBtn = document.getElementById('cancel-analysis');
        if (analyzeBtn) {
            analyzeBtn.textContent = 'Analyzing...';
            analyzeBtn.classList.add('analyzing');
        }
        if (cancelBtn) {
            cancelBtn.style.display = 'inline-block';
        }
        
        // Show analysis status in footer
        this.showFooterAnalysisStatus('Starting analysis...');
        
        // Reset tree but keep visualization
        this.initializeTreeData();
        this.nodes.clear();
        this.stats = {
            files: 0,
            classes: 0,
            functions: 0,
            methods: 0,
            lines: 0
        };
        this.updateStats();
        
        // Create visualization if not already created
        if (!this.svg) {
            this.createVisualization();
        }
        
        // Initial tree update with empty root
        if (this.root && this.svg) {
            this.update(this.root);
        }
        
        // Get analysis parameters from UI
        const pathInput = document.getElementById('analysis-path');
        let path = pathInput?.value?.trim();
        
        // Use working directory if no path specified
        if (!path || path === '') {
            // Try to get working directory from various sources
            path = window.workingDirectory || 
                   window.dashboard?.workingDirectory || 
                   window.socketClient?.sessions?.values()?.next()?.value?.working_directory ||
                   '.';
            
            // Update the input field with the detected path
            if (pathInput && path !== '.') {
                pathInput.value = path;
            }
        }
        
        const languages = this.getSelectedLanguages();
        const maxDepth = parseInt(document.getElementById('max-depth')?.value) || null;
        const ignorePatterns = this.getIgnorePatterns();
        
        // Generate request ID
        const requestId = this.generateRequestId();
        this.currentRequestId = requestId;
        
        // Build request payload
        const requestPayload = {
            request_id: requestId,
            path: path,
            languages: languages.length > 0 ? languages : null,
            max_depth: maxDepth,
            ignore_patterns: ignorePatterns.length > 0 ? ignorePatterns : null
        };
        
        console.log('Emitting code:analyze:request with payload:', requestPayload);
        
        // Request analysis from server
        this.socket.emit('code:analyze:request', requestPayload);
        
        // Set a longer safety timeout (60 seconds) for truly stuck requests
        // This is just a safety net - normal cancellation flow should work
        this.requestTimeout = setTimeout(() => {
            if (this.analyzing && this.currentRequestId === requestId) {
                console.warn('Analysis appears stuck after 60 seconds');
                this.showNotification('Analysis is taking longer than expected. You can cancel if needed.', 'warning');
                // Don't auto-reset, let user decide to cancel
            }
        }, 60000); // 60 second safety timeout
    }
    
    /**
     * Cancel current analysis
     */
    cancelAnalysis() {
        if (!this.analyzing) {
            return;
        }
        
        console.log('Cancelling analysis...');
        
        if (this.socket && this.currentRequestId) {
            this.socket.emit('code:analyze:cancel', {
                request_id: this.currentRequestId
            });
        }
        
        this.resetAnalysisState();
    }
    
    /**
     * Reset analysis state
     */
    resetAnalysisState() {
        this.analyzing = false;
        this.currentRequestId = null;
        
        // Clear any timeouts
        if (this.requestTimeout) {
            clearTimeout(this.requestTimeout);
            this.requestTimeout = null;
        }
        
        // Update button state
        const analyzeBtn = document.getElementById('analyze-code');
        const cancelBtn = document.getElementById('cancel-analysis');
        if (analyzeBtn) {
            analyzeBtn.disabled = false;
            analyzeBtn.textContent = 'Analyze';
            analyzeBtn.classList.remove('analyzing');
        }
        if (cancelBtn) {
            cancelBtn.style.display = 'none';
        }
        
        // Hide analysis status in footer
        this.hideFooterAnalysisStatus();
    }
    
    /**
     * Generate unique request ID
     */
    generateRequestId() {
        return `analysis-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    }
    
    /**
     * Get selected languages from UI
     */
    getSelectedLanguages() {
        const languages = [];
        const checkboxes = document.querySelectorAll('.language-checkbox:checked');
        checkboxes.forEach(cb => {
            languages.push(cb.value);
        });
        return languages;
    }
    
    /**
     * Get ignore patterns from UI
     */
    getIgnorePatterns() {
        const patterns = [];
        const input = document.getElementById('ignore-patterns');
        if (input && input.value) {
            patterns.push(...input.value.split(',').map(p => p.trim()).filter(p => p));
        }
        return patterns;
    }

    /**
     * Handle analysis start event
     */
    handleAnalysisStart(data) {
        console.log('Code analysis started:', data);
        
        // Only handle if this is for our current request
        if (data.request_id && data.request_id !== this.currentRequestId) {
            return;
        }
        
        // Clear request timeout since we got a response
        if (this.requestTimeout) {
            clearTimeout(this.requestTimeout);
            this.requestTimeout = null;
        }
        
        const message = `Analyzing ${data.total_files || 0} files...`;
        this.updateProgress(0, message);
        this.updateTicker(message, 'progress');
        this.showNotification('Analysis started - building tree in real-time...', 'info');
    }

    /**
     * Handle file start event
     */
    handleFileStart(data) {
        console.log('Analyzing file:', data.path);
        const message = `Analyzing: ${data.path}`;
        this.updateProgress(data.progress || 0, message);
        this.updateTicker(`📄 ${data.path}`, 'file');
        
        // Add file node to tree
        const fileNode = {
            name: data.name || data.path.split('/').pop(),
            type: 'file',
            path: data.path,
            language: data.language,
            children: []
        };
        
        this.addNodeToTree(fileNode, data.path);
        this.stats.files++;
        this.updateStats();
        
        // Incremental tree update - update visualization as files are discovered
        if (this.svg && this.root) {
            // Throttle updates to avoid performance issues
            if (!this.updateThrottleTimer) {
                this.updateThrottleTimer = setTimeout(() => {
                    this.update(this.root);
                    this.updateThrottleTimer = null;
                }, 100); // Update every 100ms max
            }
        }
    }

    /**
     * Handle file complete event
     */
    handleFileComplete(data) {
        console.log('File analysis complete:', data.path);
        
        // Update the file node if we have stats
        if (data.stats) {
            const fileNode = this.nodes.get(data.path);
            if (fileNode) {
                fileNode.stats = data.stats;
                if (data.stats.lines) {
                    this.stats.lines += data.stats.lines;
                    this.updateStats();
                }
            }
        }
    }

    /**
     * Handle node found event
     */
    handleNodeFound(data) {
        console.log('Node found:', data);
        
        // Update ticker with node discovery
        const icons = {
            'function': '⚡',
            'class': '🏛️',
            'method': '🔧',
            'module': '📦'
        };
        const icon = icons[data.type] || '📌';
        const nodeName = data.name || 'unnamed';
        this.updateTicker(`${icon} ${nodeName}`, 'node');
        
        // Create node object
        const node = {
            name: data.name,
            type: data.type, // module, class, function, method
            path: data.path,
            line: data.line,
            complexity: data.complexity || 0,
            docstring: data.docstring,
            params: data.params,
            returns: data.returns,
            children: []
        };
        
        // Add to tree
        this.addNodeToTree(node, data.parent_path || data.path);
        
        // Update stats
        switch (data.type) {
            case 'class':
                this.stats.classes++;
                break;
            case 'function':
                this.stats.functions++;
                break;
            case 'method':
                this.stats.methods++;
                break;
        }
        
        if (data.lines) {
            this.stats.lines += data.lines;
        }
        
        this.updateStats();
        
        // Incremental tree update - batch updates for performance
        if (this.svg && this.root) {
            // Clear existing throttle timer
            if (this.updateThrottleTimer) {
                clearTimeout(this.updateThrottleTimer);
            }
            
            // Set new throttle timer - batch multiple nodes together
            this.updateThrottleTimer = setTimeout(() => {
                this.update(this.root);
                this.updateThrottleTimer = null;
            }, 200); // Update every 200ms max for node additions
        }
    }

    /**
     * Handle progress update
     */
    handleProgress(data) {
        this.updateProgress(data.percentage, data.message);
    }

    /**
     * Handle analysis complete
     */
    handleAnalysisComplete(data) {
        console.log('Code analysis complete:', data);
        
        // Only handle if this is for our current request
        if (data.request_id && data.request_id !== this.currentRequestId) {
            return;
        }
        
        this.resetAnalysisState();
        
        // Final tree update
        if (this.svg) {
            this.update(this.root);
        }
        
        // Update final stats
        if (data.stats) {
            this.stats = {...this.stats, ...data.stats};
            this.updateStats();
        }
        
        // Show completion message
        const completeMessage = `✅ Complete: ${this.stats.files} files, ${this.stats.functions} functions, ${this.stats.classes} classes`;
        this.updateTicker(completeMessage, 'progress');
        this.showNotification('Analysis complete', 'success');
    }

    /**
     * Handle analysis error
     */
    handleAnalysisError(data) {
        console.error('Code analysis error:', data);
        
        // Only handle if this is for our current request
        if (data.request_id && data.request_id !== this.currentRequestId) {
            return;
        }
        
        this.resetAnalysisState();
        
        // Show error message
        const errorMessage = data.message || 'Unknown error';
        this.updateTicker(`❌ ${errorMessage}`, 'error');
        this.showNotification(`Analysis failed: ${errorMessage}`, 'error');
    }
    
    /**
     * Handle analysis accepted event
     */
    handleAnalysisAccepted(data) {
        console.log('Analysis request accepted:', data);
        
        if (data.request_id === this.currentRequestId) {
            // Clear timeout since server responded
            if (this.requestTimeout) {
                clearTimeout(this.requestTimeout);
                this.requestTimeout = null;
            }
            this.showNotification('Analysis request accepted by server', 'info');
        }
    }
    
    /**
     * Handle analysis queued event
     */
    handleAnalysisQueued(data) {
        console.log('Analysis queued:', data);
        
        if (data.request_id === this.currentRequestId) {
            this.showNotification(`Analysis queued (position: ${data.queue_size || 1})`, 'info');
        }
    }
    
    /**
     * Handle analysis cancelled event
     */
    handleAnalysisCancelled(data) {
        console.log('Analysis cancelled:', data);
        
        if (!data.request_id || data.request_id === this.currentRequestId) {
            this.resetAnalysisState();
            this.showNotification('Analysis cancelled', 'warning');
        }
    }
    
    /**
     * Show notification message
     */
    showNotification(message, type = 'info') {
        console.log(`CodeTree notification: ${message} (${type})`);
        
        // Try to find existing notification area in the Code tab
        let notification = document.querySelector('#code-tab .notification-area');
        
        // If not found, create one in the Code tab
        if (!notification) {
            const codeTab = document.getElementById('code-tab');
            if (!codeTab) {
                console.error('Code tab not found for notification');
                return;
            }
            
            notification = document.createElement('div');
            notification.className = 'notification-area';
            notification.style.cssText = `
                position: absolute;
                top: 10px;
                right: 10px;
                max-width: 400px;
                z-index: 1000;
                padding: 12px 16px;
                border-radius: 4px;
                font-size: 14px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                transition: opacity 0.3s ease;
            `;
            codeTab.insertBefore(notification, codeTab.firstChild);
        }
        
        // Set colors based on type
        const colors = {
            info: { bg: '#e3f2fd', text: '#1976d2', border: '#90caf9' },
            success: { bg: '#e8f5e9', text: '#388e3c', border: '#81c784' },
            warning: { bg: '#fff3e0', text: '#f57c00', border: '#ffb74d' },
            error: { bg: '#ffebee', text: '#d32f2f', border: '#ef5350' }
        };
        
        const color = colors[type] || colors.info;
        notification.style.backgroundColor = color.bg;
        notification.style.color = color.text;
        notification.style.border = `1px solid ${color.border}`;
        
        // Set message
        notification.textContent = message;
        notification.style.display = 'block';
        notification.style.opacity = '1';
        
        // Clear existing timeout
        if (this.notificationTimeout) {
            clearTimeout(this.notificationTimeout);
        }
        
        // Auto-hide after 5 seconds
        this.notificationTimeout = setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => {
                notification.style.display = 'none';
            }, 300);
        }, 5000);
    }

    /**
     * Add node to tree structure
     */
    addNodeToTree(node, parentPath) {
        // Find parent in tree
        let parent = this.findNodeByPath(parentPath);
        if (!parent) {
            parent = this.treeData;
        }
        
        // Check if node already exists (avoid duplicates)
        if (this.nodes.has(node.path)) {
            console.log('Node already exists:', node.path);
            return;
        }
        
        // Add node to parent's children
        if (!parent.children) {
            parent.children = [];
        }
        parent.children.push(node);
        
        // Store node reference
        this.nodes.set(node.path, node);
        
        // Update hierarchy only if D3 is available
        if (typeof d3 !== 'undefined') {
            // Preserve expanded/collapsed state
            const oldExpandedNodes = new Set();
            if (this.root) {
                this.root.descendants().forEach(d => {
                    if (d.children) {
                        oldExpandedNodes.add(d.data.path);
                    }
                });
            }
            
            // Create new hierarchy
            this.root = d3.hierarchy(this.treeData);
            this.root.x0 = this.height / 2;
            this.root.y0 = 0;
            
            // Restore expanded state
            this.root.descendants().forEach(d => {
                if (oldExpandedNodes.has(d.data.path) && d._children) {
                    d.children = d._children;
                    d._children = null;
                }
            });
        }
    }

    /**
     * Find node by path
     */
    findNodeByPath(path) {
        return this.nodes.get(path);
    }

    /**
     * Update progress in footer
     */
    updateProgress(percentage, message) {
        const footerStatus = document.getElementById('footer-analysis-progress');
        if (footerStatus) {
            // Format the message with percentage if available
            let statusText = message || 'Analyzing...';
            if (percentage > 0) {
                statusText = `[${Math.round(percentage)}%] ${statusText}`;
            }
            footerStatus.textContent = statusText;
        }
    }
    
    /**
     * Show analysis status in footer
     */
    showFooterAnalysisStatus(message) {
        const container = document.getElementById('footer-analysis-container');
        const progress = document.getElementById('footer-analysis-progress');
        
        if (container) {
            container.style.display = 'flex';
        }
        
        if (progress) {
            progress.textContent = message || 'Analyzing...';
            // Add pulsing animation
            progress.style.animation = 'pulse 1.5s ease-in-out infinite';
        }
    }
    
    /**
     * Hide analysis status in footer
     */
    hideFooterAnalysisStatus() {
        const container = document.getElementById('footer-analysis-container');
        const progress = document.getElementById('footer-analysis-progress');
        
        if (container) {
            // Fade out after a brief delay
            setTimeout(() => {
                container.style.display = 'none';
            }, 2000);
        }
        
        if (progress) {
            progress.style.animation = 'none';
        }
    }

    /**
     * Update statistics display
     */
    updateStats() {
        const fileCount = document.getElementById('file-count');
        const classCount = document.getElementById('class-count');
        const functionCount = document.getElementById('function-count');
        const lineCount = document.getElementById('line-count');
        
        if (fileCount) fileCount.textContent = this.stats.files;
        if (classCount) classCount.textContent = this.stats.classes;
        if (functionCount) functionCount.textContent = this.stats.functions;
        if (lineCount) lineCount.textContent = this.stats.lines;
    }

    /**
     * Update tree visualization
     */
    update(source) {
        if (!this.svg || !this.treeGroup) {
            return;
        }

        // Compute new tree layout
        const treeData = this.treeLayout(this.root);
        const nodes = treeData.descendants();
        const links = treeData.links();

        // Normalize for fixed-depth
        nodes.forEach(d => {
            d.y = d.depth * 180;
        });

        // Update nodes
        const node = this.treeGroup.selectAll('g.code-node')
            .data(nodes, d => d.id || (d.id = ++this.nodeId));

        // Enter new nodes
        const nodeEnter = node.enter().append('g')
            .attr('class', d => `code-node ${d.data.type} complexity-${this.getComplexityLevel(d.data.complexity)}`)
            .attr('transform', d => `translate(${source.y0},${source.x0})`)
            .on('click', (event, d) => this.toggleNode(event, d))
            .on('mouseover', (event, d) => this.showTooltip(event, d))
            .on('mouseout', () => this.hideTooltip());

        // Add circles
        nodeEnter.append('circle')
            .attr('r', 1e-6)
            .style('fill', d => d._children ? '#e2e8f0' : this.getNodeColor(d.data.type));

        // Add text labels
        nodeEnter.append('text')
            .attr('dy', '.35em')
            .attr('x', d => d.children || d._children ? -13 : 13)
            .attr('text-anchor', d => d.children || d._children ? 'end' : 'start')
            .text(d => d.data.name)
            .style('fill-opacity', 1e-6);

        // Add icons
        nodeEnter.append('text')
            .attr('class', 'node-icon')
            .attr('dy', '.35em')
            .attr('x', 0)
            .attr('text-anchor', 'middle')
            .text(d => this.getNodeIcon(d.data.type))
            .style('font-size', '16px');

        // Transition nodes to their new position
        const nodeUpdate = nodeEnter.merge(node);

        nodeUpdate.transition()
            .duration(this.duration)
            .attr('transform', d => `translate(${d.y},${d.x})`);

        nodeUpdate.select('circle')
            .attr('r', 8)
            .style('fill', d => d._children ? '#e2e8f0' : this.getNodeColor(d.data.type));

        nodeUpdate.select('text')
            .style('fill-opacity', 1);

        // Remove exiting nodes
        const nodeExit = node.exit().transition()
            .duration(this.duration)
            .attr('transform', d => `translate(${source.y},${source.x})`)
            .remove();

        nodeExit.select('circle')
            .attr('r', 1e-6);

        nodeExit.select('text')
            .style('fill-opacity', 1e-6);

        // Update links
        const link = this.treeGroup.selectAll('path.code-link')
            .data(links, d => d.target.id);

        // Enter new links
        const linkEnter = link.enter().insert('path', 'g')
            .attr('class', 'code-link')
            .attr('d', d => {
                const o = {x: source.x0, y: source.y0};
                return this.diagonal(o, o);
            });

        // Transition links to their new position
        const linkUpdate = linkEnter.merge(link);

        linkUpdate.transition()
            .duration(this.duration)
            .attr('d', d => this.diagonal(d.source, d.target));

        // Remove exiting links
        link.exit().transition()
            .duration(this.duration)
            .attr('d', d => {
                const o = {x: source.x, y: source.y};
                return this.diagonal(o, o);
            })
            .remove();

        // Store old positions for transition
        nodes.forEach(d => {
            d.x0 = d.x;
            d.y0 = d.y;
        });
    }

    /**
     * Create diagonal path for links
     */
    diagonal(source, target) {
        return `M ${source.y} ${source.x}
                C ${(source.y + target.y) / 2} ${source.x},
                  ${(source.y + target.y) / 2} ${target.x},
                  ${target.y} ${target.x}`;
    }

    /**
     * Toggle node expansion/collapse
     */
    toggleNode(event, d) {
        if (d.children) {
            d._children = d.children;
            d.children = null;
        } else {
            d.children = d._children;
            d._children = null;
        }
        
        this.update(d);
        
        // Update breadcrumb
        this.updateBreadcrumb(d);
        
        // Mark as selected
        this.selectNode(d);
        
        // Show code viewer if it's a code node
        if (d.data.type !== 'module' && d.data.type !== 'file') {
            this.showCodeViewer(d.data);
        }
    }

    /**
     * Select a node
     */
    selectNode(node) {
        // Remove previous selection
        if (this.selectedNode) {
            d3.select(this.selectedNode).classed('selected', false);
        }
        
        // Add selection to new node
        this.selectedNode = node;
        if (node) {
            d3.select(node).classed('selected', true);
        }
    }

    /**
     * Update breadcrumb navigation
     */
    updateBreadcrumb(node) {
        const path = [];
        let current = node;
        
        while (current) {
            path.unshift(current.data.name);
            current = current.parent;
        }
        
        const breadcrumbContent = document.getElementById('breadcrumb-content');
        if (breadcrumbContent) {
            breadcrumbContent.textContent = path.join(' > ');
            breadcrumbContent.className = 'ticker-file';
        }
    }
    
    /**
     * Update ticker with event
     */
    updateTicker(message, type = 'info') {
        const breadcrumbContent = document.getElementById('breadcrumb-content');
        if (breadcrumbContent) {
            // Add class based on type
            let className = '';
            switch(type) {
                case 'file': className = 'ticker-file'; break;
                case 'node': className = 'ticker-node'; break;
                case 'progress': className = 'ticker-progress'; break;
                case 'error': className = 'ticker-error'; break;
                default: className = '';
            }
            
            breadcrumbContent.textContent = message;
            breadcrumbContent.className = className + ' ticker-event';
            
            // Trigger animation
            breadcrumbContent.style.animation = 'none';
            setTimeout(() => {
                breadcrumbContent.style.animation = '';
            }, 10);
        }
    }

    /**
     * Show code viewer for a node
     */
    showCodeViewer(nodeData) {
        // Emit event to open code viewer
        if (window.CodeViewer) {
            window.CodeViewer.show(nodeData);
        }
    }

    /**
     * Show tooltip
     */
    showTooltip(event, d) {
        if (!this.tooltip) return;
        
        let content = `<strong>${d.data.name}</strong><br/>`;
        content += `Type: ${d.data.type}<br/>`;
        
        if (d.data.complexity) {
            content += `Complexity: ${d.data.complexity}<br/>`;
        }
        
        if (d.data.line) {
            content += `Line: ${d.data.line}<br/>`;
        }
        
        if (d.data.docstring) {
            content += `<em>${d.data.docstring.substring(0, 100)}...</em>`;
        }
        
        this.tooltip.transition()
            .duration(200)
            .style('opacity', .9);
        
        this.tooltip.html(content)
            .style('left', (event.pageX + 10) + 'px')
            .style('top', (event.pageY - 28) + 'px');
    }

    /**
     * Hide tooltip
     */
    hideTooltip() {
        if (this.tooltip) {
            this.tooltip.transition()
                .duration(500)
                .style('opacity', 0);
        }
    }

    /**
     * Get node color based on type
     */
    getNodeColor(type) {
        const colors = {
            module: '#8b5cf6',
            file: '#6366f1',
            class: '#3b82f6',
            function: '#f59e0b',
            method: '#10b981'
        };
        return colors[type] || '#718096';
    }

    /**
     * Get node icon based on type
     */
    getNodeIcon(type) {
        const icons = {
            module: '📦',
            file: '📄',
            class: '🏛️',
            function: '⚡',
            method: '🔧'
        };
        return icons[type] || '📌';
    }

    /**
     * Get complexity level
     */
    getComplexityLevel(complexity) {
        if (complexity <= 5) return 'low';
        if (complexity <= 10) return 'medium';
        return 'high';
    }

    /**
     * Expand all nodes
     */
    expandAll() {
        this.expand(this.root);
        this.update(this.root);
    }

    /**
     * Expand node recursively
     */
    expand(node) {
        if (node._children) {
            node.children = node._children;
            node._children = null;
        }
        if (node.children) {
            node.children.forEach(child => this.expand(child));
        }
    }

    /**
     * Collapse all nodes
     */
    collapseAll() {
        this.collapse(this.root);
        this.update(this.root);
    }

    /**
     * Collapse node recursively
     */
    collapse(node) {
        if (node.children) {
            node._children = node.children;
            node.children.forEach(child => this.collapse(child));
            node.children = null;
        }
    }

    /**
     * Reset zoom
     */
    resetZoom() {
        if (this.svg) {
            this.svg.transition()
                .duration(750)
                .call(d3.zoom().transform, d3.zoomIdentity);
        }
    }
    
    /**
     * Toggle legend visibility
     */
    toggleLegend() {
        const legend = document.getElementById('tree-legend');
        if (legend) {
            if (legend.style.display === 'none') {
                legend.style.display = 'block';
            } else {
                legend.style.display = 'none';
            }
        }
    }

    /**
     * Filter nodes by language
     */
    filterByLanguage() {
        // Implementation for language filtering
        console.log('Filtering by language:', this.languageFilter);
        // This would filter the tree data and update visualization
        this.update(this.root);
    }

    /**
     * Highlight search results
     */
    highlightSearchResults() {
        if (!this.treeGroup) return;
        
        // Clear previous highlights
        this.treeGroup.selectAll('.code-node').classed('highlighted', false);
        
        if (!this.searchTerm) return;
        
        // Highlight matching nodes
        this.treeGroup.selectAll('.code-node').each((d, i, nodes) => {
            if (d.data.name.toLowerCase().includes(this.searchTerm)) {
                d3.select(nodes[i]).classed('highlighted', true);
            }
        });
    }
}

// Export for use in dashboard
if (typeof window !== 'undefined') {
    window.CodeTree = CodeTree;
    
    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', () => {
        const codeTree = new CodeTree();
        window.codeTree = codeTree;
        
        // Listen for tab switches to initialize when Code tab is activated
        document.querySelectorAll('.tab-button').forEach(button => {
            button.addEventListener('click', () => {
                if (button.getAttribute('data-tab') === 'code') {
                    console.log('Code tab activated, initializing tree...');
                    codeTree.renderWhenVisible();
                }
            });
        });
    });
}

export default CodeTree;