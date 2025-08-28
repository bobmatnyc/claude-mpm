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
        // Radial layout settings
        this.isRadialLayout = true;  // Toggle for radial vs linear layout
        this.margin = {top: 20, right: 20, bottom: 20, left: 20};
        this.width = 960 - this.margin.left - this.margin.right;
        this.height = 600 - this.margin.top - this.margin.bottom;
        this.radius = Math.min(this.width, this.height) / 2;
        this.nodeId = 0;
        this.duration = 750;
        this.languageFilter = 'all';
        this.searchTerm = '';
        this.tooltip = null;
        this.initialized = false;
        this.analyzing = false;
        this.selectedNode = null;
        this.socket = null;
        this.autoDiscovered = false;  // Track if auto-discovery has been done
        this.zoom = null;  // Store zoom behavior
        this.activeNode = null;  // Track currently active node
        this.loadingNodes = new Set();  // Track nodes that are loading
    }

    /**
     * Initialize the code tree visualization
     */
    initialize() {
        if (this.initialized) {
            return;
        }
        
        this.container = document.getElementById('code-tree-container');
        if (!this.container) {
            console.error('Code tree container not found');
            return;
        }
        
        // Check if tab is visible
        const tabPanel = document.getElementById('code-tab');
        if (!tabPanel) {
            console.error('Code tab panel not found');
            return;
        }
        
        // Check if working directory is set
        const workingDir = this.getWorkingDirectory();
        if (!workingDir || workingDir === 'Loading...' || workingDir === 'Not selected') {
            this.showNoWorkingDirectoryMessage();
            this.initialized = true;
            return;
        }
        
        // Initialize always
        this.setupControls();
        this.initializeTreeData();
        this.subscribeToEvents();
        
        // Set initial status message
        const breadcrumbContent = document.getElementById('breadcrumb-content');
        if (breadcrumbContent && !this.analyzing) {
            this.updateActivityTicker('Loading project structure...', 'info');
        }
        
        // Only create visualization if tab is visible
        if (tabPanel.classList.contains('active')) {
            this.createVisualization();
            if (this.root && this.svg) {
                this.update(this.root);
            }
            // Auto-discover root level when tab is active
            this.autoDiscoverRootLevel();
        }
        
        this.initialized = true;
    }

    /**
     * Render visualization when tab becomes visible
     */
    renderWhenVisible() {
        // Check if working directory is set
        const workingDir = this.getWorkingDirectory();
        if (!workingDir || workingDir === 'Loading...' || workingDir === 'Not selected') {
            this.showNoWorkingDirectoryMessage();
            return;
        }
        
        // If no directory message is shown, remove it
        this.removeNoWorkingDirectoryMessage();
        
        if (!this.initialized) {
            this.initialize();
            return;
        }
        
        if (!this.svg) {
            this.createVisualization();
            if (this.svg && this.treeGroup) {
                this.update(this.root);
            }
        } else {
            // Force update with current data
            if (this.root && this.svg) {
                this.update(this.root);
            }
        }
        
        // Auto-discover root level if not done yet
        if (!this.autoDiscovered) {
            this.autoDiscoverRootLevel();
        }
    }

    /**
     * Set up control event handlers
     */
    setupControls() {
        // Remove analyze and cancel button handlers since they're no longer in the UI

        const languageFilter = document.getElementById('language-filter');
        if (languageFilter) {
            languageFilter.addEventListener('change', (e) => {
                this.languageFilter = e.target.value;
                this.filterTree();
            });
        }

        const searchBox = document.getElementById('code-search');
        if (searchBox) {
            searchBox.addEventListener('input', (e) => {
                this.searchTerm = e.target.value.toLowerCase();
                this.filterTree();
            });
        }

        const expandBtn = document.getElementById('code-expand-all');
        if (expandBtn) {
            expandBtn.addEventListener('click', () => this.expandAll());
        }
        
        const collapseBtn = document.getElementById('code-collapse-all');
        if (collapseBtn) {
            collapseBtn.addEventListener('click', () => this.collapseAll());
        }
        
        const resetZoomBtn = document.getElementById('code-reset-zoom');
        if (resetZoomBtn) {
            resetZoomBtn.addEventListener('click', () => this.resetZoom());
        }
        
        const toggleLegendBtn = document.getElementById('code-toggle-legend');
        if (toggleLegendBtn) {
            toggleLegendBtn.addEventListener('click', () => this.toggleLegend());
        }
        
        // Listen for show hidden files toggle
        const showHiddenFilesCheckbox = document.getElementById('show-hidden-files');
        if (showHiddenFilesCheckbox) {
            showHiddenFilesCheckbox.addEventListener('change', () => {
                // Clear tree and re-discover with new settings
                this.autoDiscovered = false;
                this.initializeTreeData();
                this.autoDiscoverRootLevel();
                this.showNotification(
                    showHiddenFilesCheckbox.checked ? 'Showing hidden files' : 'Hiding hidden files', 
                    'info'
                );
            });
        }
        
        // Listen for working directory changes
        document.addEventListener('workingDirectoryChanged', (e) => {
            console.log('Working directory changed to:', e.detail.directory);
            this.onWorkingDirectoryChanged(e.detail.directory);
        });
    }
    
    /**
     * Handle working directory change
     */
    onWorkingDirectoryChanged(newDirectory) {
        if (!newDirectory || newDirectory === 'Loading...' || newDirectory === 'Not selected') {
            // Show no directory message
            this.showNoWorkingDirectoryMessage();
            // Reset tree state
            this.autoDiscovered = false;
            this.analyzing = false;
            this.nodes.clear();
            this.stats = {
                files: 0,
                classes: 0,
                functions: 0,
                methods: 0,
                lines: 0
            };
            this.updateStats();
            return;
        }
        
        // Remove any no directory message
        this.removeNoWorkingDirectoryMessage();
        
        // Reset discovery state for new directory
        this.autoDiscovered = false;
        this.analyzing = false;
        
        // Clear existing data
        this.nodes.clear();
        this.stats = {
            files: 0,
            classes: 0,
            functions: 0,
            methods: 0,
            lines: 0
        };
        
        // Re-initialize with new directory
        this.initializeTreeData();
        if (this.svg) {
            this.update(this.root);
        }
        
        // Check if Code tab is currently active
        const tabPanel = document.getElementById('code-tab');
        if (tabPanel && tabPanel.classList.contains('active')) {
            // Auto-discover in the new directory
            this.autoDiscoverRootLevel();
        }
        
        this.updateStats();
    }

    /**
     * Show loading spinner
     */
    showLoading() {
        let loadingDiv = document.getElementById('code-tree-loading');
        if (!loadingDiv) {
            // Create loading element if it doesn't exist
            const container = document.getElementById('code-tree-container');
            if (container) {
                loadingDiv = document.createElement('div');
                loadingDiv.id = 'code-tree-loading';
                loadingDiv.innerHTML = `
                    <div class="code-tree-spinner"></div>
                    <div class="code-tree-loading-text">Analyzing code structure...</div>
                `;
                container.appendChild(loadingDiv);
            }
        }
        if (loadingDiv) {
            loadingDiv.classList.remove('hidden');
        }
    }

    /**
     * Hide loading spinner
     */
    hideLoading() {
        const loadingDiv = document.getElementById('code-tree-loading');
        if (loadingDiv) {
            loadingDiv.classList.add('hidden');
        }
    }

    /**
     * Create the D3.js visualization
     */
    createVisualization() {
        if (typeof d3 === 'undefined') {
            console.error('D3.js is not loaded');
            return;
        }

        const container = d3.select('#code-tree-container');
        container.selectAll('*').remove();

        if (!container || !container.node()) {
            console.error('Code tree container not found');
            return;
        }

        // Calculate dimensions
        const containerNode = container.node();
        const containerWidth = containerNode.clientWidth || 960;
        const containerHeight = containerNode.clientHeight || 600;

        this.width = containerWidth - this.margin.left - this.margin.right;
        this.height = containerHeight - this.margin.top - this.margin.bottom;
        this.radius = Math.min(this.width, this.height) / 2;

        // Create SVG
        this.svg = container.append('svg')
            .attr('width', containerWidth)
            .attr('height', containerHeight);

        // Create tree group with appropriate centering
        const centerX = containerWidth / 2;
        const centerY = containerHeight / 2;
        
        // Different initial positioning for different layouts
        if (this.isRadialLayout) {
            // Radial: center in the middle of the canvas
            this.treeGroup = this.svg.append('g')
                .attr('transform', `translate(${centerX},${centerY})`);
        } else {
            // Linear: start from left with some margin
            this.treeGroup = this.svg.append('g')
                .attr('transform', `translate(${this.margin.left + 100},${centerY})`);
        }

        // Create tree layout with improved spacing
        if (this.isRadialLayout) {
            // Use d3.cluster for better radial distribution
            this.treeLayout = d3.cluster()
                .size([2 * Math.PI, this.radius - 100])
                .separation((a, b) => {
                    // Enhanced separation for radial layout
                    if (a.parent == b.parent) {
                        // Base separation on tree depth for better spacing
                        const depthFactor = Math.max(1, 4 - a.depth);
                        // Increase spacing for nodes with many siblings
                        const siblingCount = a.parent ? (a.parent.children?.length || 1) : 1;
                        const siblingFactor = siblingCount > 5 ? 2 : (siblingCount > 3 ? 1.5 : 1);
                        // More spacing at outer levels where circumference is larger
                        const radiusFactor = 1 + (a.depth * 0.2);
                        return (depthFactor * siblingFactor) / (a.depth || 1) * radiusFactor;
                    } else {
                        // Different parents - ensure enough space
                        return 4 / (a.depth || 1);
                    }
                });
        } else {
            // Linear layout with dynamic sizing based on node count
            // Use nodeSize for consistent spacing regardless of tree size
            this.treeLayout = d3.tree()
                .nodeSize([30, 200])  // Fixed spacing: 30px vertical, 200px horizontal
                .separation((a, b) => {
                    // Consistent separation for linear layout
                    if (a.parent == b.parent) {
                        // Same parent - standard spacing
                        return 1;
                    } else {
                        // Different parents - slightly more space
                        return 1.5;
                    }
                });
        }

        // Add zoom behavior with proper transform handling
        this.zoom = d3.zoom()
            .scaleExtent([0.1, 10])
            .on('zoom', (event) => {
                if (this.isRadialLayout) {
                    // Radial: maintain center point
                    this.treeGroup.attr('transform', 
                        `translate(${centerX + event.transform.x},${centerY + event.transform.y}) scale(${event.transform.k})`);
                } else {
                    // Linear: maintain left margin
                    this.treeGroup.attr('transform', 
                        `translate(${this.margin.left + 100 + event.transform.x},${centerY + event.transform.y}) scale(${event.transform.k})`);
                }
            });

        this.svg.call(this.zoom);

        // Add controls overlay
        this.addVisualizationControls();

        // Create tooltip
        this.tooltip = d3.select('body').append('div')
            .attr('class', 'code-tree-tooltip')
            .style('opacity', 0)
            .style('position', 'absolute')
            .style('background', 'rgba(0, 0, 0, 0.8)')
            .style('color', 'white')
            .style('padding', '8px')
            .style('border-radius', '4px')
            .style('font-size', '12px')
            .style('pointer-events', 'none');
    }

    /**
     * Initialize tree data structure
     */
    initializeTreeData() {
        const workingDir = this.getWorkingDirectory();
        const dirName = workingDir ? workingDir.split('/').pop() || 'Project Root' : 'Project Root';
        const path = workingDir || '.';
        
        this.treeData = {
            name: dirName,
            path: path,
            type: 'root',
            children: [],
            loaded: false,
            expanded: true  // Start expanded
        };

        if (typeof d3 !== 'undefined') {
            this.root = d3.hierarchy(this.treeData);
            this.root.x0 = this.height / 2;
            this.root.y0 = 0;
        }
    }

    /**
     * Subscribe to code analysis events
     */
    subscribeToEvents() {
        if (!this.socket) {
            if (window.socket) {
                this.socket = window.socket;
                this.setupEventHandlers();
            } else if (window.dashboard?.socketClient?.socket) {
                this.socket = window.dashboard.socketClient.socket;
                this.setupEventHandlers();
            } else if (window.socketClient?.socket) {
                this.socket = window.socketClient.socket;
                this.setupEventHandlers();
            }
        }
    }

    /**
     * Automatically discover root-level objects when tab opens
     */
    autoDiscoverRootLevel() {
        if (this.autoDiscovered || this.analyzing) {
            return;
        }
        
        // Update activity ticker
        this.updateActivityTicker('🔍 Discovering project structure...', 'info');
        
        // Get working directory
        const workingDir = this.getWorkingDirectory();
        if (!workingDir || workingDir === 'Loading...' || workingDir === 'Not selected') {
            console.warn('Cannot auto-discover: no working directory set');
            this.showNoWorkingDirectoryMessage();
            return;
        }
        
        // Ensure we have an absolute path
        if (!workingDir.startsWith('/') && !workingDir.match(/^[A-Z]:\\/)) {
            console.error('Working directory is not absolute:', workingDir);
            this.showNotification('Invalid working directory path', 'error');
            return;
        }
        
        console.log('Auto-discovering root level for:', workingDir);
        
        this.autoDiscovered = true;
        this.analyzing = true;
        
        // Clear any existing nodes
        this.nodes.clear();
        this.stats = {
            files: 0,
            classes: 0,
            functions: 0,
            methods: 0,
            lines: 0
        };
        
        // Subscribe to events if not already done
        if (this.socket && !this.socket.hasListeners('code:node:found')) {
            this.setupEventHandlers();
        }
        
        // Update tree data with working directory as the root
        const dirName = workingDir.split('/').pop() || 'Project Root';
        this.treeData = {
            name: dirName,
            path: workingDir,
            type: 'root',
            children: [],
            loaded: false,
            expanded: true  // Start expanded to show discovered items
        };
        
        if (typeof d3 !== 'undefined') {
            this.root = d3.hierarchy(this.treeData);
            this.root.x0 = this.height / 2;
            this.root.y0 = 0;
        }
        
        // Update UI
        this.showLoading();
        this.updateBreadcrumb(`Discovering structure in ${dirName}...`, 'info');
        
        // Get selected languages from checkboxes
        const selectedLanguages = [];
        document.querySelectorAll('.language-checkbox:checked').forEach(cb => {
            selectedLanguages.push(cb.value);
        });
        
        // Get ignore patterns
        const ignorePatterns = document.getElementById('ignore-patterns')?.value || '';
        
        // Get show hidden files setting
        const showHiddenFiles = document.getElementById('show-hidden-files')?.checked || false;
        
        // Debug logging
        console.log('[DEBUG] Show hidden files checkbox value:', showHiddenFiles);
        console.log('[DEBUG] Checkbox element:', document.getElementById('show-hidden-files'));
        
        // Request top-level discovery with working directory
        const requestPayload = {
            path: workingDir,  // Use working directory instead of '.'
            depth: 'top_level',
            languages: selectedLanguages,
            ignore_patterns: ignorePatterns,
            show_hidden_files: showHiddenFiles
        };
        
        console.log('[DEBUG] Sending discovery request with payload:', requestPayload);
        
        if (this.socket) {
            this.socket.emit('code:discover:top_level', requestPayload);
        }
        
        // Update stats display
        this.updateStats();
    }
    
    /**
     * Legacy analyzeCode method - redirects to auto-discovery
     */
    analyzeCode() {
        if (this.analyzing) {
            return;
        }

        // Redirect to auto-discovery
        this.autoDiscoverRootLevel();
    }

    /**
     * Cancel ongoing analysis - removed since we no longer have a cancel button
     */
    cancelAnalysis() {
        this.analyzing = false;
        this.hideLoading();

        if (this.socket) {
            this.socket.emit('code:analysis:cancel');
        }

        this.updateBreadcrumb('Analysis cancelled', 'warning');
        this.showNotification('Analysis cancelled', 'warning');
        this.addEventToDisplay('Analysis cancelled', 'warning');
    }

    /**
     * Create the events display area
     */
    createEventsDisplay() {
        let eventsContainer = document.getElementById('analysis-events');
        if (!eventsContainer) {
            const treeContainer = document.getElementById('code-tree-container');
            if (treeContainer) {
                eventsContainer = document.createElement('div');
                eventsContainer.id = 'analysis-events';
                eventsContainer.className = 'analysis-events';
                eventsContainer.style.display = 'none';
                treeContainer.appendChild(eventsContainer);
            }
        }
    }

    /**
     * Clear the events display
     */
    clearEventsDisplay() {
        const eventsContainer = document.getElementById('analysis-events');
        if (eventsContainer) {
            eventsContainer.innerHTML = '';
            eventsContainer.style.display = 'block';
        }
    }

    /**
     * Add an event to the display
     */
    addEventToDisplay(message, type = 'info') {
        const eventsContainer = document.getElementById('analysis-events');
        if (eventsContainer) {
            const eventEl = document.createElement('div');
            eventEl.className = 'analysis-event';
            eventEl.style.borderLeftColor = type === 'warning' ? '#f59e0b' : 
                                          type === 'error' ? '#ef4444' : '#3b82f6';
            
            const timestamp = new Date().toLocaleTimeString();
            eventEl.innerHTML = `<span style="color: #718096;">[${timestamp}]</span> ${message}`;
            
            eventsContainer.appendChild(eventEl);
            // Auto-scroll to bottom
            eventsContainer.scrollTop = eventsContainer.scrollHeight;
        }
    }

    /**
     * Setup Socket.IO event handlers
     */
    setupEventHandlers() {
        if (!this.socket) return;

        // Analysis lifecycle events
        this.socket.on('code:analysis:accepted', (data) => this.onAnalysisAccepted(data));
        this.socket.on('code:analysis:queued', (data) => this.onAnalysisQueued(data));
        this.socket.on('code:analysis:start', (data) => this.onAnalysisStart(data));
        this.socket.on('code:analysis:complete', (data) => this.onAnalysisComplete(data));
        this.socket.on('code:analysis:cancelled', (data) => this.onAnalysisCancelled(data));
        this.socket.on('code:analysis:error', (data) => this.onAnalysisError(data));

        // Node discovery events
        this.socket.on('code:directory:discovered', (data) => this.onDirectoryDiscovered(data));
        this.socket.on('code:file:discovered', (data) => this.onFileDiscovered(data));
        this.socket.on('code:file:analyzed', (data) => this.onFileAnalyzed(data));
        this.socket.on('code:node:found', (data) => this.onNodeFound(data));

        // Progress updates
        this.socket.on('code:analysis:progress', (data) => this.onProgressUpdate(data));
        
        // Lazy loading responses
        this.socket.on('code:directory:contents', (data) => {
            // Update the requested directory with its contents
            if (data.path) {
                const node = this.findNodeByPath(data.path);
                if (node && data.children) {
                    // Find D3 node and remove loading pulse
                    const d3Node = this.findD3NodeByPath(data.path);
                    if (d3Node && this.loadingNodes.has(data.path)) {
                        this.removeLoadingPulse(d3Node);
                    }
                    node.children = data.children.map(child => ({
                        ...child,
                        loaded: child.type === 'directory' ? false : undefined,
                        analyzed: child.type === 'file' ? false : undefined,
                        expanded: false,
                        children: []
                    }));
                    node.loaded = true;
                    
                    // Update D3 hierarchy
                    if (this.root && this.svg) {
                        this.root = d3.hierarchy(this.treeData);
                        this.root.x0 = this.height / 2;
                        this.root.y0 = 0;
                        this.update(this.root);
                    }
                    
                    // Update stats based on discovered contents
                    if (data.stats) {
                        this.stats.files += data.stats.files || 0;
                        this.stats.directories += data.stats.directories || 0;
                        this.updateStats();
                    }
                    
                    this.updateBreadcrumb(`Loaded ${data.path}`, 'success');
                    this.hideLoading();
                }
            }
        });
        
        // Top level discovery response
        this.socket.on('code:top_level:discovered', (data) => {
            if (data.items && Array.isArray(data.items)) {
                // Add discovered items to the root node
                this.treeData.children = data.items.map(item => ({
                    name: item.name,
                    path: item.path,
                    type: item.type,
                    language: item.type === 'file' ? this.detectLanguage(item.path) : undefined,
                    size: item.size,
                    lines: item.lines,
                    loaded: item.type === 'directory' ? false : undefined,
                    analyzed: item.type === 'file' ? false : undefined,
                    expanded: false,
                    children: []
                }));
                
                this.treeData.loaded = true;
                
                // Update stats
                if (data.stats) {
                    this.stats = { ...this.stats, ...data.stats };
                    this.updateStats();
                }
                
                // Update D3 hierarchy
                if (typeof d3 !== 'undefined') {
                    this.root = d3.hierarchy(this.treeData);
                    this.root.x0 = this.height / 2;
                    this.root.y0 = 0;
                    if (this.svg) {
                        this.update(this.root);
                    }
                }
                
                this.analyzing = false;
                this.hideLoading();
                this.updateBreadcrumb(`Discovered ${data.items.length} root items`, 'success');
                this.showNotification(`Found ${data.items.length} items in project root`, 'success');
            }
        });
    }

    /**
     * Handle analysis start event
     */
    onAnalysisStart(data) {
        this.analyzing = true;
        const message = data.message || 'Starting code analysis...';
        
        // Update activity ticker
        this.updateActivityTicker('🚀 Starting analysis...', 'info');
        
        this.updateBreadcrumb(message, 'info');
        this.addEventToDisplay(`🚀 ${message}`, 'info');
        
        // Initialize or clear the tree
        if (!this.treeData || this.treeData.children.length === 0) {
            this.initializeTreeData();
        }
        
        // Reset stats
        this.stats = { 
            files: 0, 
            classes: 0, 
            functions: 0, 
            methods: 0, 
            lines: 0 
        };
        this.updateStats();
    }

    /**
     * Handle directory discovered event
     */
    onDirectoryDiscovered(data) {
        // Update activity ticker first
        this.updateActivityTicker(`📁 Discovered: ${data.name || 'directory'}`);
        
        // Add to events display
        this.addEventToDisplay(`📁 Found ${(data.children || []).length} items in: ${data.name || data.path}`, 'info');
        
        // Find the node that was clicked to trigger this discovery
        const node = this.findNodeByPath(data.path);
        if (node && data.children) {
            // Update the node with discovered children
            node.children = data.children.map(child => ({
                name: child.name,
                path: child.path,
                type: child.type,
                loaded: child.type === 'directory' ? false : undefined,
                analyzed: child.type === 'file' ? false : undefined,
                expanded: false,
                children: child.type === 'directory' ? [] : undefined,
                size: child.size,
                has_code: child.has_code
            }));
            node.loaded = true;
            node.expanded = true;
            
            // Find D3 node and remove loading pulse
            const d3Node = this.findD3NodeByPath(data.path);
            if (d3Node) {
                // Remove loading animation
                if (this.loadingNodes.has(data.path)) {
                    this.removeLoadingPulse(d3Node);
                }
                
                // Expand the node in D3
                if (d3Node.data) {
                    d3Node.data.children = node.children;
                    d3Node._children = null;
                }
            }
            
            // Update D3 hierarchy and redraw
            if (this.root && this.svg) {
                this.root = d3.hierarchy(this.treeData);
                this.update(this.root);
            }
            
            this.updateBreadcrumb(`Loaded ${node.children.length} items from ${node.name}`, 'success');
            this.updateStats();
        } else if (!node) {
            // This might be a top-level directory discovery
            const pathParts = data.path ? data.path.split('/').filter(p => p) : [];
            const isTopLevel = pathParts.length === 1;
            
            if (isTopLevel || data.forceAdd) {
                const dirNode = {
                    name: data.name || pathParts[pathParts.length - 1] || 'Unknown',
                    path: data.path,
                    type: 'directory',
                    children: [],
                    loaded: false,
                    expanded: false,
                    stats: data.stats || {}
                };
                
                this.addNodeToTree(dirNode, data.parent || '');
                this.updateBreadcrumb(`Discovered: ${data.path}`, 'info');
            }
        }
    }

    /**
     * Handle file discovered event
     */
    onFileDiscovered(data) {
        // Update activity ticker
        const fileName = data.name || (data.path ? data.path.split('/').pop() : 'file');
        this.updateActivityTicker(`📄 Found: ${fileName}`);
        
        // Add to events display
        this.addEventToDisplay(`📄 Discovered: ${data.path || 'Unknown file'}`, 'info');
        
        const pathParts = data.path ? data.path.split('/').filter(p => p) : [];
        const parentPath = pathParts.slice(0, -1).join('/');
        
        const fileNode = {
            name: data.name || pathParts[pathParts.length - 1] || 'Unknown',
            path: data.path,
            type: 'file',
            language: data.language || this.detectLanguage(data.path),
            size: data.size || 0,
            lines: data.lines || 0,
            children: [],
            analyzed: false
        };
        
        this.addNodeToTree(fileNode, parentPath);
        this.stats.files++;
        this.updateStats();
        this.updateBreadcrumb(`Found: ${data.path}`, 'info');
    }

    /**
     * Handle file analyzed event
     */
    onFileAnalyzed(data) {
        // Remove loading pulse if this file was being analyzed
        const d3Node = this.findD3NodeByPath(data.path);
        if (d3Node && this.loadingNodes.has(data.path)) {
            this.removeLoadingPulse(d3Node);
        }
        // Update activity ticker
        if (data.path) {
            const fileName = data.path.split('/').pop();
            this.updateActivityTicker(`🔍 Analyzed: ${fileName}`);
        }
        
        const fileNode = this.findNodeByPath(data.path);
        if (fileNode) {
            fileNode.analyzed = true;
            fileNode.complexity = data.complexity || 0;
            fileNode.lines = data.lines || 0;
            
            // Add code elements as children
            if (data.elements && Array.isArray(data.elements)) {
                fileNode.children = data.elements.map(elem => ({
                    name: elem.name,
                    type: elem.type.toLowerCase(),
                    path: `${data.path}#${elem.name}`,
                    line: elem.line,
                    complexity: elem.complexity || 1,
                    docstring: elem.docstring || '',
                    children: elem.methods ? elem.methods.map(m => ({
                        name: m.name,
                        type: 'method',
                        path: `${data.path}#${elem.name}.${m.name}`,
                        line: m.line,
                        complexity: m.complexity || 1,
                        docstring: m.docstring || ''
                    })) : []
                }));
            }
            
            // Update stats
            if (data.stats) {
                this.stats.classes += data.stats.classes || 0;
                this.stats.functions += data.stats.functions || 0;
                this.stats.methods += data.stats.methods || 0;
                this.stats.lines += data.stats.lines || 0;
            }
            
            this.updateStats();
            if (this.root) {
                this.update(this.root);
            }
            
            this.updateBreadcrumb(`Analyzed: ${data.path}`, 'success');
        }
    }

    /**
     * Handle node found event
     */
    onNodeFound(data) {
        // Add to events display with appropriate icon
        const typeIcon = data.type === 'class' ? '🏛️' : 
                        data.type === 'function' ? '⚡' : 
                        data.type === 'method' ? '🔧' : '📦';
        this.addEventToDisplay(`${typeIcon} Found ${data.type || 'node'}: ${data.name || 'Unknown'}`);
        
        // Extract node info
        const nodeInfo = {
            name: data.name || 'Unknown',
            type: (data.type || 'unknown').toLowerCase(),
            path: data.path || '',
            line: data.line || 0,
            complexity: data.complexity || 1,
            docstring: data.docstring || ''
        };

        // Map event types to our internal types
        const typeMapping = {
            'class': 'class',
            'function': 'function',
            'method': 'method',
            'module': 'module',
            'file': 'file',
            'directory': 'directory'
        };

        nodeInfo.type = typeMapping[nodeInfo.type] || nodeInfo.type;

        // Determine parent path
        let parentPath = '';
        if (data.parent_path) {
            parentPath = data.parent_path;
        } else if (data.file_path) {
            parentPath = data.file_path;
        } else if (nodeInfo.path.includes('/')) {
            const parts = nodeInfo.path.split('/');
            parts.pop();
            parentPath = parts.join('/');
        }

        // Update stats based on node type
        switch(nodeInfo.type) {
            case 'class':
                this.stats.classes++;
                break;
            case 'function':
                this.stats.functions++;
                break;
            case 'method':
                this.stats.methods++;
                break;
            case 'file':
                this.stats.files++;
                break;
        }

        // Add node to tree
        this.addNodeToTree(nodeInfo, parentPath);
        this.updateStats();

        // Show progress in breadcrumb
        const elementType = nodeInfo.type.charAt(0).toUpperCase() + nodeInfo.type.slice(1);
        this.updateBreadcrumb(`Found ${elementType}: ${nodeInfo.name}`, 'info');
    }

    /**
     * Handle progress update
     */
    onProgressUpdate(data) {
        const progress = data.progress || 0;
        const message = data.message || `Processing... ${progress}%`;
        
        this.updateBreadcrumb(message, 'info');
        
        // Update progress bar if it exists
        const progressBar = document.querySelector('.code-tree-progress');
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }
    }

    /**
     * Handle analysis complete event
     */
    onAnalysisComplete(data) {
        this.analyzing = false;
        this.hideLoading();
        
        // Update activity ticker
        this.updateActivityTicker('✅ Ready', 'success');
        
        // Add completion event
        this.addEventToDisplay('✅ Analysis complete!', 'success');

        // Update tree visualization
        if (this.root && this.svg) {
            this.update(this.root);
        }

        // Update stats from completion data
        if (data.stats) {
            this.stats = { ...this.stats, ...data.stats };
            this.updateStats();
        }

        const message = data.message || `Analysis complete: ${this.stats.files} files, ${this.stats.classes} classes, ${this.stats.functions} functions`;
        this.updateBreadcrumb(message, 'success');
        this.showNotification(message, 'success');
    }

    /**
     * Handle analysis error
     */
    onAnalysisError(data) {
        this.analyzing = false;
        this.hideLoading();

        const message = data.message || data.error || 'Analysis failed';
        this.updateBreadcrumb(message, 'error');
        this.showNotification(message, 'error');
    }

    /**
     * Handle analysis accepted
     */
    onAnalysisAccepted(data) {
        const message = data.message || 'Analysis request accepted';
        this.updateBreadcrumb(message, 'info');
    }

    /**
     * Handle analysis queued
     */
    onAnalysisQueued(data) {
        const position = data.position || 0;
        const message = `Analysis queued (position ${position})`;
        this.updateBreadcrumb(message, 'warning');
        this.showNotification(message, 'info');
    }
    
    /**
     * Handle INFO events for granular work tracking
     */
    onInfoEvent(data) {
        // Log to console for debugging
        console.log('[INFO]', data.type, data.message);
        
        // Update breadcrumb for certain events
        if (data.type && data.type.startsWith('discovery.')) {
            // Discovery events
            if (data.type === 'discovery.start') {
                this.updateBreadcrumb(data.message, 'info');
            } else if (data.type === 'discovery.complete') {
                this.updateBreadcrumb(data.message, 'success');
                // Show stats if available
                if (data.stats) {
                    console.log('[DISCOVERY STATS]', data.stats);
                }
            } else if (data.type === 'discovery.directory' || data.type === 'discovery.file') {
                // Quick flash of discovery events
                this.updateBreadcrumb(data.message, 'info');
            }
        } else if (data.type && data.type.startsWith('analysis.')) {
            // Analysis events
            if (data.type === 'analysis.start') {
                this.updateBreadcrumb(data.message, 'info');
            } else if (data.type === 'analysis.complete') {
                this.updateBreadcrumb(data.message, 'success');
                // Show stats if available
                if (data.stats) {
                    const statsMsg = `Found: ${data.stats.classes || 0} classes, ${data.stats.functions || 0} functions, ${data.stats.methods || 0} methods`;
                    console.log('[ANALYSIS STATS]', statsMsg);
                }
            } else if (data.type === 'analysis.class' || data.type === 'analysis.function' || data.type === 'analysis.method') {
                // Show found elements briefly
                this.updateBreadcrumb(data.message, 'info');
            } else if (data.type === 'analysis.parse') {
                this.updateBreadcrumb(data.message, 'info');
            }
        } else if (data.type && data.type.startsWith('filter.')) {
            // Filter events - optionally show in debug mode
            if (window.debugMode || this.showFilterEvents) {
                console.debug('[FILTER]', data.type, data.path, data.reason);
                if (this.showFilterEvents) {
                    this.updateBreadcrumb(data.message, 'warning');
                }
            }
        } else if (data.type && data.type.startsWith('cache.')) {
            // Cache events
            if (data.type === 'cache.hit') {
                console.debug('[CACHE HIT]', data.file);
                if (this.showCacheEvents) {
                    this.updateBreadcrumb(data.message, 'info');
                }
            } else if (data.type === 'cache.miss') {
                console.debug('[CACHE MISS]', data.file);
            }
        }
        
        // Optionally add to an event log display if enabled
        if (this.eventLogEnabled && data.message) {
            this.addEventToDisplay(data);
        }
    }
    
    /**
     * Add event to display log (if we have one)
     */
    addEventToDisplay(data) {
        // Could be implemented to show events in a dedicated log area
        // For now, just maintain a recent events list
        if (!this.recentEvents) {
            this.recentEvents = [];
        }
        
        this.recentEvents.unshift({
            timestamp: data.timestamp || new Date().toISOString(),
            type: data.type,
            message: data.message,
            data: data
        });
        
        // Keep only last 100 events
        if (this.recentEvents.length > 100) {
            this.recentEvents.pop();
        }
        
        // Could update a UI element here if we had an event log display
        console.log('[EVENT LOG]', data.type, data.message);
    }

    /**
     * Handle analysis cancelled
     */
    onAnalysisCancelled(data) {
        this.analyzing = false;
        this.hideLoading();
        const message = data.message || 'Analysis cancelled';
        this.updateBreadcrumb(message, 'warning');
    }

    /**
     * Show notification toast
     */
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `code-tree-notification ${type}`;
        notification.textContent = message;
        
        // Change from appending to container to positioning absolutely within it
        const container = document.getElementById('code-tree-container');
        if (container) {
            // Position relative to the container
            notification.style.position = 'absolute';
            notification.style.top = '10px';
            notification.style.right = '10px';
            notification.style.zIndex = '1000';
            
            // Ensure container is positioned
            if (!container.style.position || container.style.position === 'static') {
                container.style.position = 'relative';
            }
            
            container.appendChild(notification);
            
            // Animate out after 3 seconds
            setTimeout(() => {
                notification.style.animation = 'slideOutRight 0.3s ease';
                setTimeout(() => notification.remove(), 300);
            }, 3000);
        }
    }

    /**
     * Add node to tree structure
     */
    addNodeToTree(nodeInfo, parentPath = '') {
        // CRITICAL: Validate that nodeInfo.path doesn't contain absolute paths
        // The backend should only send relative paths now
        if (nodeInfo.path && nodeInfo.path.startsWith('/')) {
            console.error('Absolute path detected in node, skipping:', nodeInfo.path);
            return;
        }
        
        // Also validate parent path
        if (parentPath && parentPath.startsWith('/')) {
            console.error('Absolute path detected in parent, skipping:', parentPath);
            return;
        }
        
        // Find parent node
        let parentNode = this.treeData;
        
        if (parentPath) {
            parentNode = this.findNodeByPath(parentPath);
            if (!parentNode) {
                // CRITICAL: Do NOT create parent structure if it doesn't exist
                // This prevents creating nodes above the working directory
                console.warn('Parent node not found, skipping node creation:', parentPath);
                console.warn('Attempted to add node:', nodeInfo);
                return;
            }
        }

        // Check if node already exists
        const existingNode = parentNode.children?.find(c => 
            c.path === nodeInfo.path || 
            (c.name === nodeInfo.name && c.type === nodeInfo.type)
        );

        if (existingNode) {
            // Update existing node
            Object.assign(existingNode, nodeInfo);
            return;
        }

        // Add new node
        if (!parentNode.children) {
            parentNode.children = [];
        }
        
        // Ensure the node has a children array
        if (!nodeInfo.children) {
            nodeInfo.children = [];
        }
        
        parentNode.children.push(nodeInfo);

        // Store node reference for quick access
        this.nodes.set(nodeInfo.path, nodeInfo);

        // Update tree if initialized
        if (this.root && this.svg) {
            // Recreate hierarchy with new data
            this.root = d3.hierarchy(this.treeData);
            this.root.x0 = this.height / 2;
            this.root.y0 = 0;
            
            // Update only if we have a reasonable number of nodes to avoid performance issues
            if (this.nodes.size < 1000) {
                this.update(this.root);
            } else if (this.nodes.size % 100 === 0) {
                // Update every 100 nodes for large trees
                this.update(this.root);
            }
        }
    }

    /**
     * Find node by path in tree
     */
    findNodeByPath(path, node = null) {
        if (!node) {
            node = this.treeData;
        }

        if (node.path === path) {
            return node;
        }

        if (node.children) {
            for (const child of node.children) {
                const found = this.findNodeByPath(path, child);
                if (found) {
                    return found;
                }
            }
        }

        return null;
    }
    
    /**
     * Find D3 hierarchy node by path
     */
    findD3NodeByPath(path) {
        if (!this.root) return null;
        return this.root.descendants().find(d => d.data.path === path);
    }

    /**
     * Update statistics display
     */
    updateStats() {
        // Update stats display - use correct IDs from HTML
        const statsElements = {
            'file-count': this.stats.files,
            'class-count': this.stats.classes,
            'function-count': this.stats.functions,
            'line-count': this.stats.lines
        };

        for (const [id, value] of Object.entries(statsElements)) {
            const elem = document.getElementById(id);
            if (elem) {
                elem.textContent = value.toLocaleString();
            }
        }

        // Update progress text
        const progressText = document.getElementById('code-progress-text');
        if (progressText) {
            const statusText = this.analyzing ? 
                `Analyzing... ${this.stats.files} files processed` : 
                `Ready - ${this.stats.files} files in tree`;
            progressText.textContent = statusText;
        }
    }

    /**
     * Update breadcrumb trail
     */
    updateBreadcrumb(message, type = 'info') {
        const breadcrumbContent = document.getElementById('breadcrumb-content');
        if (breadcrumbContent) {
            breadcrumbContent.textContent = message;
            breadcrumbContent.className = `breadcrumb-${type}`;
        }
    }

    /**
     * Detect language from file extension
     */
    detectLanguage(filePath) {
        const ext = filePath.split('.').pop().toLowerCase();
        const languageMap = {
            'py': 'python',
            'js': 'javascript',
            'ts': 'typescript',
            'jsx': 'javascript',
            'tsx': 'typescript',
            'java': 'java',
            'cpp': 'cpp',
            'c': 'c',
            'cs': 'csharp',
            'rb': 'ruby',
            'go': 'go',
            'rs': 'rust',
            'php': 'php',
            'swift': 'swift',
            'kt': 'kotlin',
            'scala': 'scala',
            'r': 'r',
            'sh': 'bash',
            'ps1': 'powershell'
        };
        return languageMap[ext] || 'unknown';
    }

    /**
     * Add visualization controls for layout toggle
     */
    addVisualizationControls() {
        const controls = this.svg.append('g')
            .attr('class', 'viz-controls')
            .attr('transform', 'translate(10, 10)');
            
        // Add layout toggle button
        const toggleButton = controls.append('g')
            .attr('class', 'layout-toggle')
            .style('cursor', 'pointer')
            .on('click', () => this.toggleLayout());
            
        toggleButton.append('rect')
            .attr('width', 120)
            .attr('height', 30)
            .attr('rx', 5)
            .attr('fill', '#3b82f6')
            .attr('opacity', 0.8);
            
        toggleButton.append('text')
            .attr('x', 60)
            .attr('y', 20)
            .attr('text-anchor', 'middle')
            .attr('fill', 'white')
            .style('font-size', '12px')
            .text(this.isRadialLayout ? 'Switch to Linear' : 'Switch to Radial');
    }
    
    /**
     * Toggle between radial and linear layouts
     */
    toggleLayout() {
        this.isRadialLayout = !this.isRadialLayout;
        this.createVisualization();
        if (this.root) {
            this.update(this.root);
        }
        this.showNotification(
            this.isRadialLayout ? 'Switched to radial layout' : 'Switched to linear layout',
            'info'
        );
    }

    /**
     * Convert radial coordinates to Cartesian
     */
    radialPoint(x, y) {
        return [(y = +y) * Math.cos(x -= Math.PI / 2), y * Math.sin(x)];
    }

    /**
     * Update D3 tree visualization
     */
    update(source) {
        if (!this.treeLayout || !this.treeGroup || !source) {
            return;
        }

        // Compute the new tree layout
        const treeData = this.treeLayout(this.root);
        const nodes = treeData.descendants();
        const links = treeData.descendants().slice(1);

        if (this.isRadialLayout) {
            // Radial layout adjustments
            nodes.forEach(d => {
                // Store original x,y for transitions
                if (d.x0 === undefined) {
                    d.x0 = d.x;
                    d.y0 = d.y;
                }
            });
        } else {
            // Linear layout with nodeSize doesn't need manual normalization
            // The tree layout handles spacing automatically
        }

        // Update nodes
        const node = this.treeGroup.selectAll('g.node')
            .data(nodes, d => d.id || (d.id = ++this.nodeId));

        // Enter new nodes
        const nodeEnter = node.enter().append('g')
            .attr('class', 'node')
            .attr('transform', d => {
                if (this.isRadialLayout) {
                    const [x, y] = this.radialPoint(source.x0 || 0, source.y0 || 0);
                    return `translate(${x},${y})`;
                } else {
                    return `translate(${source.y0},${source.x0})`;
                }
            })
            .on('click', (event, d) => this.onNodeClick(event, d));

        // Add circles for nodes
        nodeEnter.append('circle')
            .attr('class', 'node-circle')
            .attr('r', 1e-6)
            .style('fill', d => this.getNodeColor(d))
            .style('stroke', d => this.getNodeStrokeColor(d))
            .style('stroke-width', 2)
            .on('mouseover', (event, d) => this.showTooltip(event, d))
            .on('mouseout', () => this.hideTooltip());

        // Add labels for nodes with smart positioning
        nodeEnter.append('text')
            .attr('class', 'node-label')
            .attr('dy', '.35em')
            .attr('x', d => {
                if (this.isRadialLayout) {
                    // For radial layout, initial position
                    return 0;
                } else {
                    // Linear layout: standard positioning
                    return d.children || d._children ? -13 : 13;
                }
            })
            .attr('text-anchor', d => {
                if (this.isRadialLayout) {
                    return 'start';  // Will be adjusted in update
                } else {
                    // Linear layout: standard anchoring
                    return d.children || d._children ? 'end' : 'start';
                }
            })
            .text(d => {
                // Truncate long names
                const maxLength = 20;
                const name = d.data.name || '';
                return name.length > maxLength ? 
                       name.substring(0, maxLength - 3) + '...' : name;
            })
            .style('fill-opacity', 1e-6)
            .style('font-size', '12px')
            .style('font-family', '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif')
            .style('text-shadow', '1px 1px 2px rgba(255,255,255,0.8), -1px -1px 2px rgba(255,255,255,0.8)');

        // Add icons for node types
        nodeEnter.append('text')
            .attr('class', 'node-icon')
            .attr('dy', '.35em')
            .attr('x', 0)
            .attr('text-anchor', 'middle')
            .text(d => this.getNodeIcon(d))
            .style('font-size', '10px')
            .style('fill', 'white');

        // Transition to new positions
        const nodeUpdate = nodeEnter.merge(node);

        nodeUpdate.transition()
            .duration(this.duration)
            .attr('transform', d => {
                if (this.isRadialLayout) {
                    const [x, y] = this.radialPoint(d.x, d.y);
                    return `translate(${x},${y})`;
                } else {
                    return `translate(${d.y},${d.x})`;
                }
            });

        nodeUpdate.select('circle.node-circle')
            .attr('r', 8)
            .style('fill', d => this.getNodeColor(d))
            .style('stroke', d => this.getNodeStrokeColor(d))
            .attr('cursor', 'pointer');

        // Update text labels with proper rotation for radial layout
        const isRadial = this.isRadialLayout;  // Capture the layout type
        nodeUpdate.select('text.node-label')
            .style('fill-opacity', 1)
            .style('fill', '#333')
            .each(function(d) {
                const selection = d3.select(this);
                
                if (isRadial) {
                    // For radial layout, apply rotation and positioning
                    const angle = (d.x * 180 / Math.PI) - 90;  // Convert to degrees
                    
                    // Determine if text should be flipped (left side of circle)
                    const shouldFlip = angle > 90 || angle < -90;
                    
                    // Calculate text position and rotation
                    if (shouldFlip) {
                        // Text on left side - rotate 180 degrees to read properly
                        selection
                            .attr('transform', `rotate(${angle + 180})`)
                            .attr('x', -15)  // Negative offset for flipped text
                            .attr('text-anchor', 'end')
                            .attr('dy', '.35em');
                    } else {
                        // Text on right side - normal orientation
                        selection
                            .attr('transform', `rotate(${angle})`)
                            .attr('x', 15)  // Positive offset for normal text
                            .attr('text-anchor', 'start')
                            .attr('dy', '.35em');
                    }
                } else {
                    // Linear layout - no rotation needed
                    selection
                        .attr('transform', null)
                        .attr('x', d.children || d._children ? -13 : 13)
                        .attr('text-anchor', d.children || d._children ? 'end' : 'start')
                        .attr('dy', '.35em');
                }
            });

        // Remove exiting nodes
        const nodeExit = node.exit().transition()
            .duration(this.duration)
            .attr('transform', d => {
                if (this.isRadialLayout) {
                    const [x, y] = this.radialPoint(source.x, source.y);
                    return `translate(${x},${y})`;
                } else {
                    return `translate(${source.y},${source.x})`;
                }
            })
            .remove();

        nodeExit.select('circle')
            .attr('r', 1e-6);

        nodeExit.select('text.node-label')
            .style('fill-opacity', 1e-6);
        
        nodeExit.select('text.node-icon')
            .style('fill-opacity', 1e-6);

        // Update links
        const link = this.treeGroup.selectAll('path.link')
            .data(links, d => d.id);

        // Enter new links
        const linkEnter = link.enter().insert('path', 'g')
            .attr('class', 'link')
            .attr('d', d => {
                const o = {x: source.x0, y: source.y0};
                return this.isRadialLayout ? 
                    this.radialDiagonal(o, o) : 
                    this.diagonal(o, o);
            })
            .style('fill', 'none')
            .style('stroke', '#ccc')
            .style('stroke-width', 2);

        // Transition to new positions
        const linkUpdate = linkEnter.merge(link);

        linkUpdate.transition()
            .duration(this.duration)
            .attr('d', d => this.isRadialLayout ? 
                this.radialDiagonal(d, d.parent) : 
                this.diagonal(d, d.parent));

        // Remove exiting links
        link.exit().transition()
            .duration(this.duration)
            .attr('d', d => {
                const o = {x: source.x, y: source.y};
                return this.isRadialLayout ? 
                    this.radialDiagonal(o, o) : 
                    this.diagonal(o, o);
            })
            .remove();

        // Store old positions for transition
        nodes.forEach(d => {
            d.x0 = d.x;
            d.y0 = d.y;
        });
    }

    /**
     * Center the view on a specific node (Linear layout)
     */
    centerOnNode(d) {
        if (!this.svg || !this.zoom) return;
        
        const transform = d3.zoomTransform(this.svg.node());
        const x = -d.y * transform.k + this.width / 2;
        const y = -d.x * transform.k + this.height / 2;
        
        this.svg.transition()
            .duration(750)
            .call(
                this.zoom.transform,
                d3.zoomIdentity
                    .translate(x, y)
                    .scale(transform.k)
            );
    }
    
    /**
     * Center the view on a specific node (Radial layout)
     */
    centerOnNodeRadial(d) {
        if (!this.svg || !this.zoom) return;
        
        // Use the same radialPoint function for consistency
        const [x, y] = this.radialPoint(d.x, d.y);
        
        // Get current transform
        const transform = d3.zoomTransform(this.svg.node());
        
        // Calculate translation to center the node
        // The tree is already centered at width/2, height/2 via transform
        // So we need to adjust relative to that center
        const targetX = this.width / 2 - x * transform.k;
        const targetY = this.height / 2 - y * transform.k;
        
        // Apply smooth transition to center the node
        this.svg.transition()
            .duration(750)
            .call(
                this.zoom.transform,
                d3.zoomIdentity
                    .translate(targetX, targetY)
                    .scale(transform.k)
            );
    }
    
    /**
     * Highlight the active node with larger icon
     */
    highlightActiveNode(d) {
        // Reset all nodes to normal size and clear parent context
        this.treeGroup.selectAll('circle.node-circle')
            .transition()
            .duration(300)
            .attr('r', 8)
            .classed('active', false)
            .classed('parent-context', false)
            .style('stroke', null)
            .style('stroke-width', null)
            .style('opacity', null);
        
        // Find and increase size of clicked node - use data matching
        this.treeGroup.selectAll('g.node')
            .filter(node => node === d)
            .select('circle.node-circle')
            .transition()
            .duration(300)
            .attr('r', 12)  // Larger radius
            .classed('active', true)
            .style('stroke', '#3b82f6')
            .style('stroke-width', 3);
        
        // Store active node
        this.activeNode = d;
    }
    
    /**
     * Add pulsing animation for loading state
     */
    addLoadingPulse(d) {
        // Use consistent selection pattern
        const node = this.treeGroup.selectAll('g.node')
            .filter(node => node === d)
            .select('circle.node-circle');
        
        // Add to loading set
        this.loadingNodes.add(d.data.path);
        
        // Add pulsing class and orange color
        node.classed('loading-pulse', true)
            .style('fill', '#fb923c');  // Orange color for loading
        
        // Create pulse animation
        const pulseAnimation = () => {
            if (!this.loadingNodes.has(d.data.path)) return;
            
            node.transition()
                .duration(600)
                .attr('r', 14)
                .style('opacity', 0.6)
                .transition()
                .duration(600)
                .attr('r', 10)
                .style('opacity', 1)
                .on('end', () => {
                    if (this.loadingNodes.has(d.data.path)) {
                        pulseAnimation(); // Continue pulsing
                    }
                });
        };
        
        pulseAnimation();
    }
    
    /**
     * Remove pulsing animation when loading complete
     */
    removeLoadingPulse(d) {
        // Remove from loading set
        this.loadingNodes.delete(d.data.path);
        
        // Use consistent selection pattern
        const node = this.treeGroup.selectAll('g.node')
            .filter(node => node === d)
            .select('circle.node-circle');
        
        node.classed('loading-pulse', false)
            .interrupt() // Stop animation
            .transition()
            .duration(300)
            .attr('r', this.activeNode === d ? 12 : 8)
            .style('opacity', 1)
            .style('fill', d => this.getNodeColor(d));  // Restore original color
    }
    
    /**
     * Show parent node alongside for context
     */
    showWithParent(d) {
        if (!d.parent) return;
        
        // Make parent more visible
        const parentNode = this.treeGroup.selectAll('g.node')
            .filter(node => node === d.parent);
        
        // Highlight parent with different style
        parentNode.select('circle.node-circle')
            .classed('parent-context', true)
            .style('stroke', '#10b981')
            .style('stroke-width', 3)
            .style('opacity', 0.8);
        
        // For radial, adjust zoom to show both parent and clicked node
        if (this.isRadialLayout && d.parent) {
            // Calculate bounding box including parent and immediate children
            const nodes = [d, d.parent];
            if (d.children) nodes.push(...d.children);
            else if (d._children) nodes.push(...d._children);
            
            const angles = nodes.map(n => n.x);
            const radii = nodes.map(n => n.y);
            
            const minAngle = Math.min(...angles);
            const maxAngle = Math.max(...angles);
            const maxRadius = Math.max(...radii);
            
            // Zoom to fit parent and children
            const angleSpan = maxAngle - minAngle;
            const scale = Math.min(
                angleSpan > 0 ? (Math.PI * 2) / (angleSpan * 2) : 2.5,  // Fit angle span
                this.width / (2 * maxRadius),      // Fit radius
                2.5  // Max zoom
            );
            
            // Calculate center angle and radius
            const centerAngle = (minAngle + maxAngle) / 2;
            const centerRadius = maxRadius / 2;
            const centerX = centerRadius * Math.cos(centerAngle - Math.PI / 2);
            const centerY = centerRadius * Math.sin(centerAngle - Math.PI / 2);
            
            this.svg.transition()
                .duration(750)
                .call(
                    this.zoom.transform,
                    d3.zoomIdentity
                        .translate(this.width / 2 - centerX * scale, this.height / 2 - centerY * scale)
                        .scale(scale)
                );
        }
    }
    
    /**
     * Handle node click - implement lazy loading with enhanced visual feedback
     */
    onNodeClick(event, d) {
        event.stopPropagation();
        
        // Center on clicked node
        if (this.isRadialLayout) {
            this.centerOnNodeRadial(d);
        } else {
            this.centerOnNode(d);
        }
        
        // Highlight with larger icon
        this.highlightActiveNode(d);
        
        // Show parent context
        this.showWithParent(d);
        
        // Get selected languages from checkboxes
        const selectedLanguages = [];
        document.querySelectorAll('.language-checkbox:checked').forEach(cb => {
            selectedLanguages.push(cb.value);
        });
        
        // Get ignore patterns
        const ignorePatterns = document.getElementById('ignore-patterns')?.value || '';
        
        // Get show hidden files setting
        const showHiddenFiles = document.getElementById('show-hidden-files')?.checked || false;
        
        // For directories that haven't been loaded yet, request discovery
        if (d.data.type === 'directory' && !d.data.loaded) {
            // Add pulsing animation
            this.addLoadingPulse(d);
            
            // Ensure path is absolute or relative to working directory
            const fullPath = this.ensureFullPath(d.data.path);
            
            // Request directory contents via Socket.IO
            if (this.socket) {
                this.socket.emit('code:discover:directory', {
                    path: fullPath,
                    depth: 1,  // Only get immediate children
                    languages: selectedLanguages,
                    ignore_patterns: ignorePatterns,
                    show_hidden_files: showHiddenFiles
                });
                
                // Mark as loading to prevent duplicate requests
                d.data.loaded = 'loading';
                this.updateBreadcrumb(`Loading ${d.data.name}...`, 'info');
                this.showNotification(`Loading directory: ${d.data.name}`, 'info');
            }
        } 
        // For files that haven't been analyzed, request analysis
        else if (d.data.type === 'file' && !d.data.analyzed) {
            // Only analyze files of selected languages
            const fileLanguage = this.detectLanguage(d.data.path);
            if (!selectedLanguages.includes(fileLanguage) && fileLanguage !== 'unknown') {
                this.showNotification(`Skipping ${d.data.name} - ${fileLanguage} not selected`, 'warning');
                return;
            }
            
            // Add pulsing animation
            this.addLoadingPulse(d);
            
            // Ensure path is absolute or relative to working directory
            const fullPath = this.ensureFullPath(d.data.path);
            
            // Get current show_hidden_files setting
            const showHiddenFilesCheckbox = document.getElementById('show-hidden-files');
            const showHiddenFiles = showHiddenFilesCheckbox ? showHiddenFilesCheckbox.checked : false;
            
            if (this.socket) {
                this.socket.emit('code:analyze:file', {
                    path: fullPath,
                    show_hidden_files: showHiddenFiles
                });
                
                d.data.analyzed = 'loading';
                this.updateBreadcrumb(`Analyzing ${d.data.name}...`, 'info');
                this.showNotification(`Analyzing: ${d.data.name}`, 'info');
            }
        }
        // Toggle children visibility for already loaded nodes
        else if (d.children || d._children) {
            if (d.children) {
                d._children = d.children;
                d.children = null;
                d.data.expanded = false;
            } else {
                d.children = d._children;
                d._children = null;
                d.data.expanded = true;
            }
            this.update(d);
        }
        
        // Update selection
        this.selectedNode = d;
        this.highlightNode(d);
    }
    
    /**
     * Ensure path is absolute or relative to working directory
     */
    ensureFullPath(path) {
        if (!path) return path;
        
        // If already absolute, return as is
        if (path.startsWith('/')) {
            return path;
        }
        
        // Get working directory
        const workingDir = this.getWorkingDirectory();
        if (!workingDir) {
            return path;
        }
        
        // If path is relative, make it relative to working directory
        if (path === '.' || path === workingDir) {
            return workingDir;
        }
        
        // Combine working directory with relative path
        return `${workingDir}/${path}`.replace(/\/+/g, '/');
    }

    /**
     * Highlight selected node
     */
    highlightNode(node) {
        // Remove previous highlights
        this.treeGroup.selectAll('circle.node-circle')
            .style('stroke-width', 2)
            .classed('selected', false);

        // Highlight selected node
        this.treeGroup.selectAll('circle.node-circle')
            .filter(d => d === node)
            .style('stroke-width', 4)
            .classed('selected', true);
    }

    /**
     * Create diagonal path for links
     */
    diagonal(s, d) {
        return `M ${s.y} ${s.x}
                C ${(s.y + d.y) / 2} ${s.x},
                  ${(s.y + d.y) / 2} ${d.x},
                  ${d.y} ${d.x}`;
    }
    
    /**
     * Create radial diagonal path for links
     */
    radialDiagonal(s, d) {
        const path = d3.linkRadial()
            .angle(d => d.x)
            .radius(d => d.y);
        return path({source: s, target: d});
    }

    /**
     * Get node color based on type and complexity
     */
    getNodeColor(d) {
        const type = d.data.type;
        const complexity = d.data.complexity || 1;

        // Base colors by type
        const baseColors = {
            'root': '#6B7280',
            'directory': '#3B82F6',
            'file': '#10B981',
            'module': '#8B5CF6',
            'class': '#F59E0B',
            'function': '#EF4444',
            'method': '#EC4899'
        };

        const baseColor = baseColors[type] || '#6B7280';

        // Adjust brightness based on complexity (higher complexity = darker)
        if (complexity > 10) {
            return d3.color(baseColor).darker(0.5);
        } else if (complexity > 5) {
            return d3.color(baseColor).darker(0.25);
        }
        
        return baseColor;
    }

    /**
     * Get node stroke color
     */
    getNodeStrokeColor(d) {
        if (d.data.loaded === 'loading' || d.data.analyzed === 'loading') {
            return '#FCD34D';  // Yellow for loading
        }
        if (d.data.type === 'directory' && !d.data.loaded) {
            return '#94A3B8';  // Gray for unloaded
        }
        if (d.data.type === 'file' && !d.data.analyzed) {
            return '#CBD5E1';  // Light gray for unanalyzed
        }
        return this.getNodeColor(d);
    }

    /**
     * Get icon for node type
     */
    getNodeIcon(d) {
        const icons = {
            'root': '📦',
            'directory': '📁',
            'file': '📄',
            'module': '📦',
            'class': 'C',
            'function': 'ƒ',
            'method': 'm'
        };
        return icons[d.data.type] || '•';
    }

    /**
     * Show tooltip on hover
     */
    showTooltip(event, d) {
        if (!this.tooltip) return;

        const info = [];
        info.push(`<strong>${d.data.name}</strong>`);
        info.push(`Type: ${d.data.type}`);
        
        if (d.data.language) {
            info.push(`Language: ${d.data.language}`);
        }
        if (d.data.complexity) {
            info.push(`Complexity: ${d.data.complexity}`);
        }
        if (d.data.lines) {
            info.push(`Lines: ${d.data.lines}`);
        }
        if (d.data.path) {
            info.push(`Path: ${d.data.path}`);
        }
        
        // Special messages for lazy-loaded nodes
        if (d.data.type === 'directory' && !d.data.loaded) {
            info.push('<em>Click to explore contents</em>');
        } else if (d.data.type === 'file' && !d.data.analyzed) {
            info.push('<em>Click to analyze file</em>');
        }

        this.tooltip.transition()
            .duration(200)
            .style('opacity', .9);

        this.tooltip.html(info.join('<br>'))
            .style('left', (event.pageX + 10) + 'px')
            .style('top', (event.pageY - 28) + 'px');
    }

    /**
     * Hide tooltip
     */
    hideTooltip() {
        if (!this.tooltip) return;
        
        this.tooltip.transition()
            .duration(500)
            .style('opacity', 0);
    }

    /**
     * Filter tree based on language and search
     */
    filterTree() {
        if (!this.root) return;

        // Apply filters
        this.root.descendants().forEach(d => {
            d.data._hidden = false;

            // Language filter
            if (this.languageFilter !== 'all') {
                if (d.data.type === 'file' && d.data.language !== this.languageFilter) {
                    d.data._hidden = true;
                }
            }

            // Search filter
            if (this.searchTerm) {
                if (!d.data.name.toLowerCase().includes(this.searchTerm)) {
                    d.data._hidden = true;
                }
            }
        });

        // Update display
        this.update(this.root);
    }

    /**
     * Expand all nodes in the tree
     */
    expandAll() {
        if (!this.root) return;
        
        // Recursively expand all nodes
        const expandRecursive = (node) => {
            if (node._children) {
                node.children = node._children;
                node._children = null;
            }
            if (node.children) {
                node.children.forEach(expandRecursive);
            }
        };
        
        expandRecursive(this.root);
        this.update(this.root);
        this.showNotification('All nodes expanded', 'info');
    }

    /**
     * Collapse all nodes in the tree
     */
    collapseAll() {
        if (!this.root) return;
        
        // Recursively collapse all nodes except root
        const collapseRecursive = (node) => {
            if (node.children) {
                node._children = node.children;
                node.children = null;
            }
            if (node._children) {
                node._children.forEach(collapseRecursive);
            }
        };
        
        this.root.children?.forEach(collapseRecursive);
        this.update(this.root);
        this.showNotification('All nodes collapsed', 'info');
    }

    /**
     * Reset zoom to fit the tree
     */
    resetZoom() {
        if (!this.svg || !this.zoom) return;
        
        // Reset to identity transform for radial layout (centered)
        this.svg.transition()
            .duration(750)
            .call(
                this.zoom.transform,
                d3.zoomIdentity
            );
        
        this.showNotification('Zoom reset', 'info');
    }

    /**
     * Focus on a specific node and its subtree
     */
    focusOnNode(node) {
        if (!this.svg || !this.zoom || !node) return;
        
        // Get all descendants of this node
        const descendants = node.descendants ? node.descendants() : [node];
        
        if (this.isRadialLayout) {
            // For radial layout, calculate the bounding box in polar coordinates
            const angles = descendants.map(d => d.x);
            const radii = descendants.map(d => d.y);
            
            const minAngle = Math.min(...angles);
            const maxAngle = Math.max(...angles);
            const minRadius = Math.min(...radii);
            const maxRadius = Math.max(...radii);
            
            // Convert polar bounds to Cartesian for centering
            const centerAngle = (minAngle + maxAngle) / 2;
            const centerRadius = (minRadius + maxRadius) / 2;
            
            // Convert to Cartesian coordinates
            const centerX = centerRadius * Math.cos(centerAngle - Math.PI / 2);
            const centerY = centerRadius * Math.sin(centerAngle - Math.PI / 2);
            
            // Calculate the span for zoom scale
            const angleSpan = maxAngle - minAngle;
            const radiusSpan = maxRadius - minRadius;
            
            // Calculate scale to fit the subtree
            // Use angle span to determine scale (radial layout specific)
            let scale = 1;
            if (angleSpan > 0 && radiusSpan > 0) {
                // Scale based on the larger dimension
                const angleFactor = Math.PI * 2 / angleSpan;  // Full circle / angle span
                const radiusFactor = this.radius / radiusSpan;
                scale = Math.min(angleFactor, radiusFactor, 3);  // Max zoom of 3x
                scale = Math.max(scale, 1);  // Min zoom of 1x
            }
            
            // Animate the zoom and center
            this.svg.transition()
                .duration(750)
                .call(
                    this.zoom.transform,
                    d3.zoomIdentity
                        .translate(this.width/2 - centerX * scale, this.height/2 - centerY * scale)
                        .scale(scale)
                );
                
        } else {
            // For linear/tree layout
            const xValues = descendants.map(d => d.x);
            const yValues = descendants.map(d => d.y);
            
            const minX = Math.min(...xValues);
            const maxX = Math.max(...xValues);
            const minY = Math.min(...yValues);
            const maxY = Math.max(...yValues);
            
            // Calculate center
            const centerX = (minX + maxX) / 2;
            const centerY = (minY + maxY) / 2;
            
            // Calculate bounds
            const width = maxX - minX;
            const height = maxY - minY;
            
            // Calculate scale to fit
            const padding = 100;
            let scale = 1;
            if (width > 0 && height > 0) {
                const scaleX = (this.width - padding) / width;
                const scaleY = (this.height - padding) / height;
                scale = Math.min(scaleX, scaleY, 2.5);  // Max zoom of 2.5x
                scale = Math.max(scale, 0.5);  // Min zoom of 0.5x
            }
            
            // Animate zoom to focus
            this.svg.transition()
                .duration(750)
                .call(
                    this.zoom.transform,
                    d3.zoomIdentity
                        .translate(this.width/2 - centerX * scale, this.height/2 - centerY * scale)
                        .scale(scale)
                );
        }
        
        // Update breadcrumb with focused path
        const path = this.getNodePath(node);
        this.updateBreadcrumb(`Focused: ${path}`, 'info');
    }
    
    /**
     * Get the full path of a node
     */
    getNodePath(node) {
        const path = [];
        let current = node;
        while (current) {
            if (current.data && current.data.name) {
                path.unshift(current.data.name);
            }
            current = current.parent;
        }
        return path.join(' / ');
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
     * Get the current working directory
     */
    getWorkingDirectory() {
        // Try to get from dashboard's working directory manager
        if (window.dashboard && window.dashboard.workingDirectoryManager) {
            return window.dashboard.workingDirectoryManager.getCurrentWorkingDir();
        }
        
        // Fallback to checking the DOM element
        const workingDirPath = document.getElementById('working-dir-path');
        if (workingDirPath) {
            const pathText = workingDirPath.textContent.trim();
            if (pathText && pathText !== 'Loading...' && pathText !== 'Not selected') {
                return pathText;
            }
        }
        
        return null;
    }
    
    /**
     * Show a message when no working directory is selected
     */
    showNoWorkingDirectoryMessage() {
        const container = document.getElementById('code-tree-container');
        if (!container) return;
        
        // Remove any existing message
        this.removeNoWorkingDirectoryMessage();
        
        // Hide loading if shown
        this.hideLoading();
        
        // Create message element
        const messageDiv = document.createElement('div');
        messageDiv.id = 'no-working-dir-message';
        messageDiv.className = 'no-working-dir-message';
        messageDiv.innerHTML = `
            <div class="message-icon">📁</div>
            <h3>No Working Directory Selected</h3>
            <p>Please select a working directory from the top menu to analyze code.</p>
            <button id="select-working-dir-btn" class="btn btn-primary">
                Select Working Directory
            </button>
        `;
        messageDiv.style.cssText = `
            text-align: center;
            padding: 40px;
            color: #666;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        `;
        
        // Style the message elements
        const messageIcon = messageDiv.querySelector('.message-icon');
        if (messageIcon) {
            messageIcon.style.cssText = 'font-size: 48px; margin-bottom: 16px; opacity: 0.5;';
        }
        
        const h3 = messageDiv.querySelector('h3');
        if (h3) {
            h3.style.cssText = 'margin: 16px 0; color: #333; font-size: 20px;';
        }
        
        const p = messageDiv.querySelector('p');
        if (p) {
            p.style.cssText = 'margin: 16px 0; color: #666; font-size: 14px;';
        }
        
        const button = messageDiv.querySelector('button');
        if (button) {
            button.style.cssText = `
                margin-top: 20px;
                padding: 10px 20px;
                background: #3b82f6;
                color: white;
                border: none;
                border-radius: 6px;
                cursor: pointer;
                font-size: 14px;
                transition: background 0.2s;
            `;
            button.addEventListener('mouseenter', () => {
                button.style.background = '#2563eb';
            });
            button.addEventListener('mouseleave', () => {
                button.style.background = '#3b82f6';
            });
            button.addEventListener('click', () => {
                // Trigger working directory selection
                const changeDirBtn = document.getElementById('change-dir-btn');
                if (changeDirBtn) {
                    changeDirBtn.click();
                } else if (window.dashboard && window.dashboard.workingDirectoryManager) {
                    window.dashboard.workingDirectoryManager.showChangeDirDialog();
                }
            });
        }
        
        container.appendChild(messageDiv);
        
        // Update breadcrumb
        this.updateBreadcrumb('Please select a working directory', 'warning');
    }
    
    /**
     * Remove the no working directory message
     */
    removeNoWorkingDirectoryMessage() {
        const message = document.getElementById('no-working-dir-message');
        if (message) {
            message.remove();
        }
    }
    
    /**
     * Export tree data
     */
    exportTree() {
        const exportData = {
            timestamp: new Date().toISOString(),
            workingDirectory: this.getWorkingDirectory(),
            stats: this.stats,
            tree: this.treeData
        };

        const blob = new Blob([JSON.stringify(exportData, null, 2)], 
                             {type: 'application/json'});
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `code-tree-${Date.now()}.json`;
        link.click();
        URL.revokeObjectURL(url);

        this.showNotification('Tree exported successfully', 'success');
    }

    /**
     * Update activity ticker with real-time messages
     */
    updateActivityTicker(message, type = 'info') {
        const breadcrumb = document.getElementById('breadcrumb-content');
        if (breadcrumb) {
            // Add spinning icon for loading states
            const icon = type === 'info' && message.includes('...') ? '⟳ ' : '';
            breadcrumb.innerHTML = `${icon}${message}`;
            breadcrumb.className = `breadcrumb-${type}`;
        }
    }
    
    /**
     * Update ticker message
     */
    updateTicker(message, type = 'info') {
        const ticker = document.getElementById('code-tree-ticker');
        if (ticker) {
            ticker.textContent = message;
            ticker.className = `ticker ticker-${type}`;
            
            // Auto-hide after 5 seconds for non-error messages
            if (type !== 'error') {
                setTimeout(() => {
                    ticker.style.opacity = '0';
                    setTimeout(() => {
                        ticker.style.opacity = '1';
                        ticker.textContent = '';
                    }, 300);
                }, 5000);
            }
        }
    }
}

// Export for use in other modules
window.CodeTree = CodeTree;

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Check if we're on a page with code tree container
    if (document.getElementById('code-tree-container')) {
        window.codeTree = new CodeTree();
        
        // Listen for tab changes to initialize when code tab is selected
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-tab="code"]')) {
                setTimeout(() => {
                    if (window.codeTree && !window.codeTree.initialized) {
                        window.codeTree.initialize();
                    } else if (window.codeTree) {
                        window.codeTree.renderWhenVisible();
                    }
                }, 100);
            }
        });
    }
});