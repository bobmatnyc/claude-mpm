/**
 * Code Tree Component
 * 
 * D3.js-based tree visualization for displaying AST-based code structure.
 * Shows modules, classes, functions, and methods with complexity-based coloring.
 * Provides real-time updates during code analysis.
 * 
 * ===== CACHE CLEAR INSTRUCTIONS =====
 * If tree still moves/centers after update:
 * 1. Hard refresh: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac)
 * 2. Or open DevTools (F12) → Network tab → Check "Disable cache" 
 * 3. Or clear browser cache: Ctrl+Shift+Delete → Clear cached images and files
 * 
 * Version: 2025-08-29T15:30:00Z - ALL CENTERING REMOVED
 * Last Update: Completely disabled tree centering/movement on node clicks
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
        this.bulkLoadMode = false;  // Track bulk loading preference
        this.expandedPaths = new Set();  // Track which paths are expanded
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
        
        // Listen for working directory changes
        document.addEventListener('workingDirectoryChanged', (e) => {
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
            this.loadingNodes.clear();  // Clear loading state tracking
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
        this.loadingNodes.clear();  // Clear loading state tracking
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
        
        // Add tree controls toolbar
        this.addTreeControls();
        
        // Add breadcrumb navigation
        this.addBreadcrumb();

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

        // DISABLED: All zoom behavior has been completely disabled to prevent tree movement
        // The tree should remain completely stationary - no zooming, panning, or centering allowed
        this.zoom = null;  // Completely disable zoom behavior
        
        // Do NOT apply zoom behavior to SVG - this prevents all zoom/pan interactions
        // this.svg.call(this.zoom);  // DISABLED
        
        console.log('[CodeTree] All zoom and pan behavior disabled - tree is now completely stationary');

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
     * Clear all D3 visualization elements
     */
    clearD3Visualization() {
        if (this.treeGroup) {
            // Remove all existing nodes and links
            this.treeGroup.selectAll('g.node').remove();
            this.treeGroup.selectAll('path.link').remove();
        }
        // Reset node ID counter for proper tracking
        this.nodeId = 0;
    }
    
    /**
     * Initialize tree data structure
     */
    initializeTreeData() {
        const workingDir = this.getWorkingDirectory();
        const dirName = workingDir ? workingDir.split('/').pop() || 'Project Root' : 'Project Root';
        
        // Use '.' as the root path for consistency with relative path handling
        // The actual working directory is retrieved via getWorkingDirectory() when needed
        this.treeData = {
            name: dirName,
            path: '.',  // Always use '.' for root to simplify path handling
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
            // CRITICAL FIX: Create our own socket connection if no shared socket exists
            // This ensures the tree view has a working WebSocket connection
            if (window.socket && window.socket.connected) {
                console.log('[CodeTree] Using existing global socket');
                this.socket = window.socket;
                this.setupEventHandlers();
            } else if (window.dashboard?.socketClient?.socket && window.dashboard.socketClient.socket.connected) {
                console.log('[CodeTree] Using dashboard socket');
                this.socket = window.dashboard.socketClient.socket;
                this.setupEventHandlers();
            } else if (window.socketClient?.socket && window.socketClient.socket.connected) {
                console.log('[CodeTree] Using socketClient socket');
                this.socket = window.socketClient.socket;
                this.setupEventHandlers();
            } else if (window.io) {
                // Create our own socket connection like the simple view does
                console.log('[CodeTree] Creating new socket connection');
                try {
                    this.socket = io('/');
                    
                    this.socket.on('connect', () => {
                        console.log('[CodeTree] Socket connected successfully');
                        this.setupEventHandlers();
                    });
                    
                    this.socket.on('disconnect', () => {
                        console.log('[CodeTree] Socket disconnected');
                    });
                    
                    this.socket.on('connect_error', (error) => {
                        console.error('[CodeTree] Socket connection error:', error);
                    });
                } catch (error) {
                    console.error('[CodeTree] Failed to create socket connection:', error);
                }
            } else {
                console.error('[CodeTree] Socket.IO not available - cannot subscribe to events');
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
        
        
        this.autoDiscovered = true;
        this.analyzing = true;
        
        // Clear any existing nodes
        this.nodes.clear();
        this.loadingNodes.clear();  // Clear loading state for fresh discovery
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
            path: '.',  // Use '.' for root to maintain consistency with relative path handling
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
        
        // Enhanced debug logging
        
        // Request top-level discovery with working directory
        const requestPayload = {
            path: workingDir,  // Use working directory instead of '.'
            depth: 'top_level',
            languages: selectedLanguages,
            ignore_patterns: ignorePatterns,
            request_id: `discover_${Date.now()}`  // Add request ID for tracking
        };
        
        // Sending top-level discovery request
        
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
        this.loadingNodes.clear();  // Clear loading state on cancellation

        if (this.socket) {
            this.socket.emit('code:analysis:cancel');
        }
    }

    /**
     * Add tree control toolbar with expand/collapse and other controls
     */
    addTreeControls() {
        const container = d3.select('#code-tree-container');
        
        // Remove any existing controls
        container.select('.tree-controls-toolbar').remove();
        
        const toolbar = container.append('div')
            .attr('class', 'tree-controls-toolbar');
            
        // Expand All button
        toolbar.append('button')
            .attr('class', 'tree-control-btn')
            .attr('title', 'Expand all loaded directories')
            .text('⊞')
            .on('click', () => this.expandAll());
            
        // Collapse All button  
        toolbar.append('button')
            .attr('class', 'tree-control-btn')
            .attr('title', 'Collapse all directories')
            .text('⊟')
            .on('click', () => this.collapseAll());
            
        // Bulk Load Toggle
        toolbar.append('button')
            .attr('class', 'tree-control-btn')
            .attr('id', 'bulk-load-toggle')
            .attr('title', 'Toggle bulk loading (load 2 levels at once)')
            .text('↕')
            .on('click', () => this.toggleBulkLoad());
            
        // Layout Toggle
        toolbar.append('button')
            .attr('class', 'tree-control-btn')
            .attr('title', 'Toggle between radial and linear layouts')
            .text('◎')
            .on('click', () => this.toggleLayout());
            
        // Path Search
        const searchInput = toolbar.append('input')
            .attr('class', 'tree-control-btn')
            .attr('type', 'text')
            .attr('placeholder', 'Search...')
            .attr('title', 'Search for files and directories')
            .style('width', '120px')
            .style('text-align', 'left')
            .on('input', (event) => this.searchTree(event.target.value))
            .on('keydown', (event) => {
                if (event.key === 'Escape') {
                    event.target.value = '';
                    this.searchTree('');
                }
            });
    }

    /**
     * Add breadcrumb navigation
     */
    addBreadcrumb() {
        const container = d3.select('#code-tree-container');
        
        // Remove any existing breadcrumb
        container.select('.tree-breadcrumb').remove();
        
        const breadcrumb = container.append('div')
            .attr('class', 'tree-breadcrumb');
            
        const pathDiv = breadcrumb.append('div')
            .attr('class', 'breadcrumb-path')
            .attr('id', 'tree-breadcrumb-path');
            
        // Initialize with working directory
        this.updateBreadcrumbPath('/');
    }

    /**
     * Update breadcrumb path based on current navigation
     */
    updateBreadcrumbPath(currentPath) {
        const pathDiv = d3.select('#tree-breadcrumb-path');
        pathDiv.selectAll('*').remove();
        
        const workingDir = this.getWorkingDirectory();
        if (!workingDir || workingDir === 'Loading...' || workingDir === 'Not selected') {
            pathDiv.text('No project selected');
            return;
        }
        
        // Build path segments
        const segments = currentPath === '/' ? 
            [workingDir.split('/').pop() || 'Root'] :
            currentPath.split('/').filter(s => s.length > 0);
            
        segments.forEach((segment, index) => {
            if (index > 0) {
                pathDiv.append('span')
                    .attr('class', 'breadcrumb-separator')
                    .text('/');
            }
            
            pathDiv.append('span')
                .attr('class', index === segments.length - 1 ? 'breadcrumb-segment current' : 'breadcrumb-segment')
                .text(segment)
                .on('click', () => {
                    if (index < segments.length - 1) {
                        // Navigate to parent path
                        const parentPath = segments.slice(0, index + 1).join('/');
                        this.navigateToPath(parentPath);
                    }
                });
        });
    }

    /**
     * Expand all currently loaded directories
     */
    expandAll() {
        if (!this.root) return;
        
        const expandNode = (node) => {
            if (node.data.type === 'directory' && node.data.loaded === true) {
                if (node._children) {
                    node.children = node._children;
                    node._children = null;
                    node.data.expanded = true;
                }
            }
            if (node.children) {
                node.children.forEach(expandNode);
            }
        };
        
        expandNode(this.root);
        this.update(this.root);
        this.showNotification('Expanded all loaded directories', 'success');
    }

    /**
     * Collapse all directories to root level
     */
    collapseAll() {
        if (!this.root) return;
        
        const collapseNode = (node) => {
            if (node.data.type === 'directory' && node.children) {
                node._children = node.children;
                node.children = null;
                node.data.expanded = false;
            }
            if (node._children) {
                node._children.forEach(collapseNode);
            }
        };
        
        collapseNode(this.root);
        this.update(this.root);
        this.showNotification('Collapsed all directories', 'info');
    }

    /**
     * Toggle bulk loading mode
     */
    toggleBulkLoad() {
        this.bulkLoadMode = !this.bulkLoadMode;
        const button = d3.select('#bulk-load-toggle');
        
        if (this.bulkLoadMode) {
            button.classed('active', true);
            this.showNotification('Bulk load enabled - will load 2 levels deep', 'info');
        } else {
            button.classed('active', false);
            this.showNotification('Bulk load disabled - load 1 level at a time', 'info');
        }
    }

    /**
     * Navigate to a specific path in the tree
     */
    navigateToPath(path) {
        // Implementation for navigating to a specific path
        // This would expand the tree to show the specified path
        this.updateBreadcrumbPath(path);
        this.showNotification(`Navigating to: ${path}`, 'info');
    }

    /**
     * Search the tree for matching files/directories
     */
    searchTree(query) {
        if (!this.root || !this.treeGroup) return;
        
        const searchTerm = query.toLowerCase().trim();
        
        // Clear previous search highlights
        this.treeGroup.selectAll('.code-node')
            .classed('search-match', false);
            
        if (!searchTerm) {
            return; // No search term, just clear highlights
        }
        
        // Find matching nodes
        const matchingNodes = [];
        const searchNode = (node) => {
            const name = (node.data.name || '').toLowerCase();
            const path = (node.data.path || '').toLowerCase();
            
            if (name.includes(searchTerm) || path.includes(searchTerm)) {
                matchingNodes.push(node);
            }
            
            if (node.children) {
                node.children.forEach(searchNode);
            }
            if (node._children) {
                node._children.forEach(searchNode);
            }
        };
        
        searchNode(this.root);
        
        // Highlight matching nodes
        if (matchingNodes.length > 0) {
            // Get all current nodes in the tree
            const allNodes = this.treeGroup.selectAll('.code-node').data();
            
            matchingNodes.forEach(matchNode => {
                // Find the corresponding DOM node
                const domNode = this.treeGroup.selectAll('.code-node')
                    .filter(d => d.data.path === matchNode.data.path);
                domNode.classed('search-match', true);
                
                // Expand parent path to show the match
                this.expandPathToNode(matchNode);
            });
            
            this.showNotification(`Found ${matchingNodes.length} matches`, 'success');
            
            // Auto-center on first match if in radial layout - REMOVED
            // Centering functionality has been disabled to prevent unwanted repositioning
            // if (matchingNodes.length > 0 && this.isRadialLayout) {
            //     this.centerOnNode ? this.centerOnNode(matchingNodes[0]) : this.centerOnNodeRadial(matchingNodes[0]);
            // }
        } else {
            this.showNotification('No matches found', 'info');
        }
    }

    /**
     * Expand the tree path to show a specific node
     */
    expandPathToNode(targetNode) {
        const pathToExpand = [];
        let current = targetNode.parent;
        
        // Build path from node to root
        while (current && current !== this.root) {
            pathToExpand.unshift(current);
            current = current.parent;
        }
        
        // Expand each node in the path
        pathToExpand.forEach(node => {
            if (node.data.type === 'directory' && node._children) {
                node.children = node._children;
                node._children = null;
                node.data.expanded = true;
            }
        });
        
        // Update the visualization if we expanded anything
        if (pathToExpand.length > 0) {
            this.update(this.root);
        }
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
        this.socket.on('code:top_level:discovered', (data) => this.onTopLevelDiscovered(data));
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
                // Convert absolute path back to relative path to match tree nodes
                let searchPath = data.path;
                const workingDir = this.getWorkingDirectory();
                if (workingDir && searchPath.startsWith(workingDir)) {
                    // Remove working directory prefix to get relative path
                    searchPath = searchPath.substring(workingDir.length).replace(/^\//, '');
                    // If empty after removing prefix, it's the root
                    if (!searchPath) {
                        searchPath = '.';
                    }
                }
                
                const node = this.findNodeByPath(searchPath);
                if (node && data.children) {
                    // Find D3 node and remove loading pulse (use searchPath, not data.path)
                    const d3Node = this.findD3NodeByPath(searchPath);
                    if (d3Node && this.loadingNodes.has(searchPath)) {
                        this.removeLoadingPulse(d3Node);
                        this.loadingNodes.delete(searchPath);  // Remove from loading set
                        console.log('🎯 [SUBDIRECTORY LOADING] Successfully completed and removed from loading set:', searchPath);
                    }
                    node.children = data.children.map(child => {
                        // Construct full path for child by combining parent path with child name
                        // The backend now returns just the item name, not the full path
                        let childPath;
                        if (searchPath === '.' || searchPath === '') {
                            // Root level - child path is just the name
                            childPath = child.name || child.path;
                        } else {
                            // Subdirectory - combine parent path with child name
                            // Use child.name (backend returns just the name) or fallback to child.path
                            const childName = child.name || child.path;
                            childPath = `${searchPath}/${childName}`;
                        }
                        
                        return {
                            ...child,
                            path: childPath,  // Override with constructed path
                            loaded: child.type === 'directory' ? false : undefined,
                            analyzed: child.type === 'file' ? false : undefined,
                            expanded: false,
                            children: []
                        };
                    });
                    node.loaded = true;
                    node.expanded = true; // Mark as expanded to show children
                    
                    // Update D3 hierarchy and make sure the node is expanded
                    if (this.root && this.svg) {
                        // Store old root to preserve expansion state
                        const oldRoot = this.root;
                        
                        // Recreate hierarchy with updated data
                        this.root = d3.hierarchy(this.treeData);
                        this.root.x0 = this.height / 2;
                        this.root.y0 = 0;
                        
                        // Preserve expansion state from old tree
                        this.preserveExpansionState(oldRoot, this.root);
                        
                        // Find the D3 node again after hierarchy recreation
                        const updatedD3Node = this.findD3NodeByPath(searchPath);
                        if (updatedD3Node) {
                            // D3.hierarchy already creates the children - just ensure visible
                            if (updatedD3Node.children && updatedD3Node.children.length > 0) {
                                updatedD3Node._children = null;
                                updatedD3Node.data.expanded = true;
                                console.log('✅ [D3 UPDATE] Node expanded after loading:', searchPath);
                            }
                        }
                        
                        // Update with the specific node for smooth animation
                        this.update(updatedD3Node || this.root);
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
                    // Clear any existing nodes before creating new ones
                    this.clearD3Visualization();
                    
                    // Create new hierarchy
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
     * Handle top-level discovery event (initial root directory scan)
     */
    onTopLevelDiscovered(data) {
        // Received top-level discovery response
        
        // Update activity ticker
        this.updateActivityTicker(`📁 Discovered ${(data.items || []).length} top-level items`, 'success');
        
        // Add to events display
        this.addEventToDisplay(`📁 Found ${(data.items || []).length} top-level items in project root`, 'info');
        
        // The root node (with path '.') should receive the children
        const rootNode = this.findNodeByPath('.');
        
        console.log('🔎 Looking for root node with path ".", found:', rootNode ? {
            name: rootNode.name,
            path: rootNode.path,
            currentChildren: rootNode.children ? rootNode.children.length : 0
        } : 'NOT FOUND');
        
        if (rootNode && data.items) {
            console.log('🌳 Populating root node with children');
            
            // Update the root node with discovered children
            rootNode.children = data.items.map(child => {
                // Items at root level get their name as the path
                const childPath = child.name;
                
                console.log(`  Adding child: ${child.name} with path: ${childPath}`);
                
                return {
                    name: child.name,
                    path: childPath,  // Just the name for top-level items
                    type: child.type,
                    loaded: child.type === 'directory' ? false : undefined,  // Explicitly false for directories
                    analyzed: child.type === 'file' ? false : undefined,
                    expanded: false,
                    children: child.type === 'directory' ? [] : undefined,
                    size: child.size,
                    has_code: child.has_code
                };
            });
            
            rootNode.loaded = true;
            rootNode.expanded = true;
            
            // Update D3 hierarchy and render
            if (this.root && this.svg) {
                // CRITICAL FIX: Preserve existing D3 node structure when possible
                // Instead of recreating the entire hierarchy, update the existing root
                if (this.root.data === this.treeData) {
                    // Same root data object - update children in place
                    console.log('📊 Updating existing D3 tree structure');
                    
                    // Create D3 hierarchy nodes for the new children
                    this.root.children = rootNode.children.map(childData => {
                        const childNode = d3.hierarchy(childData);
                        childNode.parent = this.root;
                        childNode.depth = 1;
                        return childNode;
                    });
                    
                    // Ensure root is marked as expanded
                    this.root._children = null;
                    this.root.data.expanded = true;
                } else {
                    // Different root - need to recreate
                    console.log('🔄 Recreating D3 tree structure');
                    this.root = d3.hierarchy(this.treeData);
                    this.root.x0 = this.height / 2;
                    this.root.y0 = 0;
                }
                
                // Update the tree visualization
                this.update(this.root);
            }
            
            // Hide loading and show success
            this.hideLoading();
            this.updateBreadcrumb(`Discovered ${data.items.length} items`, 'success');
            this.showNotification(`Found ${data.items.length} top-level items`, 'success');
        } else {
            console.error('❌ Could not find root node to populate');
            this.showNotification('Failed to populate root directory', 'error');
        }
        
        // Mark analysis as complete
        this.analyzing = false;
    }
    
    /**
     * Handle directory discovered event
     */
    onDirectoryDiscovered(data) {
        // CRITICAL DEBUG: Log raw data received
        console.log('🔴 [RAW DATA] Exact data received from backend:', data);
        console.log('🔴 [RAW DATA] Data type:', typeof data);
        console.log('🔴 [RAW DATA] Data keys:', Object.keys(data));
        console.log('🔴 [RAW DATA] Children field:', data.children);
        console.log('🔴 [RAW DATA] Children type:', typeof data.children);
        console.log('🔴 [RAW DATA] Is children array?:', Array.isArray(data.children));
        console.log('🔴 [RAW DATA] Children length:', data.children ? data.children.length : 'undefined');
        
        // Update activity ticker first
        this.updateActivityTicker(`📁 Discovered: ${data.name || 'directory'}`);
        
        // Add to events display
        this.addEventToDisplay(`📁 Found ${(data.children || []).length} items in: ${data.name || data.path}`, 'info');
        
        console.log('✅ [SUBDIRECTORY LOADING] Received directory discovery response:', {
            path: data.path,
            name: data.name,
            childrenCount: (data.children || []).length,
            children: (data.children || []).map(c => ({ name: c.name, type: c.type })),
            workingDir: this.getWorkingDirectory(),
            fullEventData: data
        });
        
        // Convert absolute path back to relative path to match tree nodes
        let searchPath = data.path;
        const workingDir = this.getWorkingDirectory();
        if (workingDir && searchPath.startsWith(workingDir)) {
            // Remove working directory prefix to get relative path
            searchPath = searchPath.substring(workingDir.length).replace(/^\//, '');
            // If empty after removing prefix, it's the root
            if (!searchPath) {
                searchPath = '.';
            }
        }
        
        console.log('🔎 Searching for node with path:', searchPath);
        
        // Find the node that was clicked to trigger this discovery
        const node = this.findNodeByPath(searchPath);
        
        console.log('🔍 Node search result:', {
            searchPath: searchPath,
            nodeFound: !!node,
            nodeName: node?.name,
            nodePath: node?.path,
            nodeChildren: node?.children?.length,
            dataHasChildren: !!data.children,
            dataChildrenLength: data.children?.length
        });
        
        // Debug: log all paths in the tree if node not found
        if (!node) {
            console.warn('Node not found! Logging all paths in tree:');
            this.logAllPaths(this.treeData);
        }
        
        // Located target node for expansion
        
        // Handle both cases: when children exist and when directory is empty
        if (node) {
            console.log('📦 Node found, checking children:', {
                nodeFound: true,
                dataHasChildren: 'children' in data,
                dataChildrenIsArray: Array.isArray(data.children),
                dataChildrenLength: data.children?.length,
                dataChildrenValue: data.children
            });
            
            if (data.children) {
                console.log(`📂 Updating node ${node.name} with ${data.children.length} children`);
                // Update the node with discovered children
                node.children = data.children.map(child => {
                // Construct full path for child by combining parent path with child name
                // The backend now returns just the item name, not the full path
                let childPath;
                if (searchPath === '.' || searchPath === '') {
                    // Root level - child path is just the name
                    childPath = child.name || child.path;
                } else {
                    // Subdirectory - combine parent path with child name
                    // Use child.name (backend returns just the name) or fallback to child.path
                    const childName = child.name || child.path;
                    childPath = `${searchPath}/${childName}`;
                }
                
                return {
                    name: child.name,
                    path: childPath,  // Use constructed path instead of child.path
                    type: child.type,
                    loaded: child.type === 'directory' ? false : undefined,
                    analyzed: child.type === 'file' ? false : undefined,
                    expanded: false,
                    children: child.type === 'directory' ? [] : undefined,
                    size: child.size,
                    has_code: child.has_code
                };
            });
            node.loaded = true;
            node.expanded = true;
            
            // Find D3 node and remove loading pulse (use searchPath, not data.path)
            const d3Node = this.findD3NodeByPath(searchPath);
            if (d3Node) {
                // Remove loading animation
                if (this.loadingNodes.has(searchPath)) {
                    this.removeLoadingPulse(d3Node);
                    this.loadingNodes.delete(searchPath);  // Remove from loading set
                    console.log('🎯 [SUBDIRECTORY LOADING] Successfully completed and removed from loading set (hierarchy update):', searchPath);
                }
            }
            
            // Update D3 hierarchy and redraw with expanded node
            if (this.root && this.svg) {
                // Store old root to preserve expansion state
                const oldRoot = this.root;
                
                // Recreate hierarchy with updated data
                this.root = d3.hierarchy(this.treeData);
                
                // Restore positions for smooth animation
                this.root.x0 = this.height / 2;
                this.root.y0 = 0;
                
                // Preserve expansion state from old tree
                this.preserveExpansionState(oldRoot, this.root);
                
                // Find the D3 node again after hierarchy recreation
                const updatedD3Node = this.findD3NodeByPath(searchPath);
                if (updatedD3Node) {
                    // CRITICAL FIX: D3.hierarchy() creates nodes with children already set
                    // We just need to ensure they're not hidden in _children
                    // When d3.hierarchy creates the tree, it puts all children in the 'children' array
                    
                    // If the node has children from d3.hierarchy, make sure they're visible
                    if (updatedD3Node.children && updatedD3Node.children.length > 0) {
                        // Children are already there from d3.hierarchy - just ensure not hidden
                        updatedD3Node._children = null;
                        updatedD3Node.data.expanded = true;
                        
                        console.log('✅ [D3 UPDATE] Node expanded with children:', {
                            path: searchPath,
                            d3ChildrenCount: updatedD3Node.children.length,
                            dataChildrenCount: updatedD3Node.data.children ? updatedD3Node.data.children.length : 0,
                            childPaths: updatedD3Node.children.map(c => c.data.path)
                        });
                    } else if (!updatedD3Node.children && updatedD3Node.data.children && updatedD3Node.data.children.length > 0) {
                        // This shouldn't happen if d3.hierarchy is working correctly
                        console.error('⚠️ [D3 UPDATE] Data has children but D3 node does not!', {
                            path: searchPath,
                            dataChildren: updatedD3Node.data.children
                        });
                    }
                }
                
                // Force update with the source node for smooth animation
                this.update(updatedD3Node || this.root);
            }
            
                // Provide better feedback for empty vs populated directories
                if (node.children.length === 0) {
                    this.updateBreadcrumb(`Empty directory: ${node.name}`, 'info');
                    this.showNotification(`Directory "${node.name}" is empty`, 'info');
                } else {
                    this.updateBreadcrumb(`Loaded ${node.children.length} items from ${node.name}`, 'success');
                    this.showNotification(`Loaded ${node.children.length} items from "${node.name}"`, 'success');
                }
            } else {
                // data.children is undefined or null - should not happen if backend is working correctly
                console.error('❌ No children data received for directory:', {
                    path: searchPath,
                    dataKeys: Object.keys(data),
                    fullData: data
                });
                this.updateBreadcrumb(`Error loading ${node.name}`, 'error');
                this.showNotification(`Failed to load directory contents`, 'error');
            }
            this.updateStats();
        } else if (!node) {
            console.error('❌ [SUBDIRECTORY LOADING] Node not found for path:', {
                searchPath,
                originalPath: data.path,
                workingDir: this.getWorkingDirectory(),
                allTreePaths: this.getAllTreePaths(this.treeData)
            });
            this.showNotification(`Could not find directory "${searchPath}" in tree`, 'error');
            this.logAllPaths(this.treeData);
        } else if (node && !data.children) {
            console.warn('⚠️ [SUBDIRECTORY LOADING] Directory response has no children:', {
                path: data.path,
                searchPath,
                nodeExists: !!node,
                dataKeys: Object.keys(data),
                fullData: data
            });
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
            this.loadingNodes.delete(data.path);  // Remove from loading set
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
        this.loadingNodes.clear();  // Clear loading state on error

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
        
        // Update breadcrumb for certain events
        if (data.type && data.type.startsWith('discovery.')) {
            // Discovery events
            if (data.type === 'discovery.start') {
                this.updateBreadcrumb(data.message, 'info');
            } else if (data.type === 'discovery.complete') {
                this.updateBreadcrumb(data.message, 'success');
                // Show stats if available
                if (data.stats) {
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
    }

    /**
     * Handle analysis cancelled
     */
    onAnalysisCancelled(data) {
        this.analyzing = false;
        this.hideLoading();
        this.loadingNodes.clear();  // Clear loading state on cancellation
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
            console.log('🔍 [SUBDIRECTORY LOADING] Starting search for path:', path);
        }

        if (node.path === path) {
            console.log('✅ [SUBDIRECTORY LOADING] Found node for path:', path);
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

        if (!node.parent && node === this.treeData) {
            console.warn('❌ [SUBDIRECTORY LOADING] Path not found in tree:', path);
        }
        return null;
    }
    
    /**
     * Helper to log all paths in tree for debugging
     */
    logAllPaths(node, indent = '') {
        console.log(`${indent}${node.path} (${node.name})`);
        if (node.children) {
            for (const child of node.children) {
                this.logAllPaths(child, indent + '  ');
            }
        }
    }
    
    /**
     * Helper to collect all paths in tree for debugging
     */
    getAllTreePaths(node) {
        const paths = [node.path];
        if (node.children) {
            for (const child of node.children) {
                paths.push(...this.getAllTreePaths(child));
            }
        }
        return paths;
    }
    
    /**
     * Find D3 hierarchy node by path
     */
    findD3NodeByPath(path) {
        if (!this.root) return null;
        return this.root.descendants().find(d => d.data.path === path);
    }
    
    /**
     * Preserve expansion state when recreating hierarchy
     */
    preserveExpansionState(oldRoot, newRoot) {
        if (!oldRoot || !newRoot) return;
        
        // Create a map of expanded nodes from the old tree
        const expansionMap = new Map();
        oldRoot.descendants().forEach(node => {
            if (node.data.expanded || (node.children && !node._children)) {
                expansionMap.set(node.data.path, true);
            }
        });
        
        // Apply expansion state to new tree
        newRoot.descendants().forEach(node => {
            if (expansionMap.has(node.data.path)) {
                node.children = node._children || node.children;
                node._children = null;
                node.data.expanded = true;
            }
        });
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
            .attr('class', d => {
                let classes = ['node', 'code-node'];
                if (d.data.type === 'directory') {
                    classes.push('directory');
                    if (d.data.loaded === true && d.children) {
                        classes.push('expanded');
                    }
                    if (d.data.loaded === 'loading') {
                        classes.push('loading');
                    }
                    if (d.data.children && d.data.children.length === 0) {
                        classes.push('empty');
                    }
                } else if (d.data.type === 'file') {
                    classes.push('file');
                }
                return classes.join(' ');
            })
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
            .style('stroke-width', d => d.data.type === 'directory' ? 2 : 1.5)
            .style('cursor', 'pointer')  // Add cursor pointer for visual feedback
            .on('click', (event, d) => this.onNodeClick(event, d))  // CRITICAL FIX: Add click handler to circles
            .on('mouseover', (event, d) => this.showTooltip(event, d))
            .on('mouseout', () => this.hideTooltip());
        
        // Add expand/collapse icons for directories
        nodeEnter.filter(d => d.data.type === 'directory')
            .append('text')
            .attr('class', 'expand-icon')
            .attr('x', 0)
            .attr('y', 0)
            .attr('text-anchor', 'middle')
            .attr('dominant-baseline', 'central')
            .text(d => {
                if (d.data.loaded === 'loading') return '⟳';
                if (d.data.loaded === true && d.children) return '▼';
                return '▶';
            })
            .style('font-size', '10px')
            .style('pointer-events', 'none');

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
            .style('text-shadow', '1px 1px 2px rgba(255,255,255,0.8), -1px -1px 2px rgba(255,255,255,0.8)')
            .on('click', (event, d) => this.onNodeClick(event, d))  // CRITICAL FIX: Add click handler to labels
            .style('cursor', 'pointer');

        // Add icons for node types (files only, directories use expand icons)
        nodeEnter.filter(d => d.data.type !== 'directory')
            .append('text')
            .attr('class', 'node-icon')
            .attr('dy', '.35em')
            .attr('x', 0)
            .attr('text-anchor', 'middle')
            .text(d => this.getNodeIcon(d))
            .style('font-size', '10px')
            .style('fill', 'white')
            .on('click', (event, d) => this.onNodeClick(event, d))  // CRITICAL FIX: Add click handler to file icons
            .style('cursor', 'pointer');
            
        // Add item count badges for directories
        nodeEnter.filter(d => d.data.type === 'directory' && d.data.children)
            .append('text')
            .attr('class', 'item-count-badge')
            .attr('x', 12)
            .attr('y', -8)
            .attr('text-anchor', 'middle')
            .text(d => {
                const count = d.data.children ? d.data.children.length : 0;
                return count > 0 ? count : '';
            })
            .style('font-size', '9px')
            .style('opacity', 0.7)
            .on('click', (event, d) => this.onNodeClick(event, d))  // CRITICAL FIX: Add click handler to count badges
            .style('cursor', 'pointer');

        // Transition to new positions
        const nodeUpdate = nodeEnter.merge(node);

        // CRITICAL FIX: Ensure ALL nodes (new and existing) have click handlers
        // This fixes the issue where subdirectory clicks stop working after tree updates
        nodeUpdate.on('click', (event, d) => this.onNodeClick(event, d));
        
        // ADDITIONAL FIX: Also ensure click handlers on all child elements
        nodeUpdate.selectAll('circle').on('click', (event, d) => this.onNodeClick(event, d));
        nodeUpdate.selectAll('text').on('click', (event, d) => this.onNodeClick(event, d));

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

        // Update node classes based on current state
        nodeUpdate.attr('class', d => {
            let classes = ['node', 'code-node'];
            if (d.data.type === 'directory') {
                classes.push('directory');
                if (d.data.loaded === true && d.children) {
                    classes.push('expanded');
                }
                if (d.data.loaded === 'loading') {
                    classes.push('loading');
                }
                if (d.data.children && d.data.children.length === 0) {
                    classes.push('empty');
                }
            } else if (d.data.type === 'file') {
                classes.push('file');
            }
            return classes.join(' ');
        });
        
        nodeUpdate.select('circle.node-circle')
            .attr('r', d => d.data.type === 'directory' ? 10 : 8)
            .style('fill', d => this.getNodeColor(d))
            
        // Update expand/collapse icons
        nodeUpdate.select('.expand-icon')
            .text(d => {
                if (d.data.loaded === 'loading') return '⟳';
                if (d.data.loaded === true && d.children) return '▼';
                return '▶';
            });
            
        // Update item count badges
        nodeUpdate.select('.item-count-badge')
            .text(d => {
                if (d.data.type !== 'directory') return '';
                const count = d.data.children ? d.data.children.length : 0;
                return count > 0 ? count : '';
            })
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
     * REMOVED: Center the view on a specific node (Linear layout)
     * This method has been completely disabled to prevent unwanted tree movement.
     * All centering functionality has been removed from the code tree.
     */
    centerOnNode(d) {
        // Method disabled - no centering operations will be performed
        console.log('[CodeTree] centerOnNode called but disabled - no centering will occur');
        return;
    }
    
    /**
     * REMOVED: Center the view on a specific node (Radial layout)
     * This method has been completely disabled to prevent unwanted tree movement.
     * All centering functionality has been removed from the code tree.
     */
    centerOnNodeRadial(d) {
        // Method disabled - no centering operations will be performed
        console.log('[CodeTree] centerOnNodeRadial called but disabled - no centering will occur');
        return;
    }
    
    /**
     * Highlight the active node with larger icon
     */
    highlightActiveNode(d) {
        // Reset all nodes to normal size and clear parent context
        // First clear classes on the selection
        const allCircles = this.treeGroup.selectAll('circle.node-circle');
        allCircles
            .classed('active', false)
            .classed('parent-context', false);
        
        // Then apply transition separately
        allCircles
            .transition()
            .duration(300)
            .attr('r', 8)
            .style('stroke', null)
            .style('stroke-width', null)
            .style('opacity', null);
        
        // Reset all labels to normal
        this.treeGroup.selectAll('text.node-label')
            .style('font-weight', 'normal')
            .style('font-size', '12px');
        
        // Find and increase size of clicked node - use data matching
        // Make the size increase MUCH more dramatic: 8 -> 20 (2.5x the size)
        const activeNodeCircle = this.treeGroup.selectAll('g.node')
            .filter(node => node === d)
            .select('circle.node-circle');
        
        // First set the class (not part of transition)
        activeNodeCircle.classed('active', true);
        
        // Then apply the transition with styles - MUCH LARGER
        activeNodeCircle
            .transition()
            .duration(300)
            .attr('r', 20)  // Much larger radius (2.5x)
            .style('stroke', '#3b82f6')
            .style('stroke-width', 5)  // Thicker border
            .style('filter', 'drop-shadow(0 0 15px rgba(59, 130, 246, 0.6))');  // Stronger glow effect
        
        // Also make the label bold
        this.treeGroup.selectAll('g.node')
            .filter(node => node === d)
            .select('text.node-label')
            .style('font-weight', 'bold')
            .style('font-size', '14px');  // Slightly larger text
        
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
        
        // Add pulsing class and orange color - separate operations
        node.classed('loading-pulse', true);
        node.style('fill', '#fb923c');  // Orange color for loading
        
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
     * Note: This function only handles visual animation removal.
     * The caller is responsible for managing the loadingNodes Set.
     */
    removeLoadingPulse(d) {
        // Note: loadingNodes.delete() is handled by the caller for explicit control
        
        // Use consistent selection pattern
        const node = this.treeGroup.selectAll('g.node')
            .filter(node => node === d)
            .select('circle.node-circle');
        
        // Clear class first
        node.classed('loading-pulse', false);
        
        // Then interrupt and transition
        node.interrupt() // Stop animation
            .transition()
            .duration(300)
            .attr('r', this.activeNode === d ? 20 : 8)  // Use 20 for active node
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
        
        // Highlight parent with different style - separate class from styles
        const parentCircle = parentNode.select('circle.node-circle');
        parentCircle.classed('parent-context', true);
        parentCircle
            .style('stroke', '#10b981')
            .style('stroke-width', 3)
            .style('opacity', 0.8);
        
        // REMOVED: Radial zoom adjustment functionality
        // This section previously adjusted zoom to show parent and clicked node together,
        // but has been completely disabled to prevent unwanted tree movement/centering.
        // Only visual highlighting of the parent remains active.
        
        // if (this.isRadialLayout && d.parent) {
        //     // All zoom.transform operations have been disabled
        //     // to prevent tree movement when nodes are clicked
        // }
    }
    
    /**
     * Handle node click - implement lazy loading with enhanced visual feedback
     */
    onNodeClick(event, d) {
        // DEBUG: Log all clicks to verify handler is working
        console.log('🖱️ [NODE CLICK] Clicked on node:', {
            name: d?.data?.name,
            path: d?.data?.path,
            type: d?.data?.type,
            loaded: d?.data?.loaded,
            hasChildren: !!(d?.children || d?._children),
            dataChildren: d?.data?.children?.length || 0
        });
        
        // Handle node click interaction
        
        // Check event parameter
        if (event) {
            try {
                if (typeof event.stopPropagation === 'function') {
                    event.stopPropagation();
                } else {
                }
            } catch (error) {
                console.error('[CodeTree] ERROR calling stopPropagation:', error);
            }
        } else {
        }
        
        // Check d parameter structure
        if (!d) {
            console.error('[CodeTree] ERROR: d is null/undefined, cannot continue');
            return;
        }
        
        if (!d.data) {
            console.error('[CodeTree] ERROR: d.data is null/undefined, cannot continue');
            return;
        }
        
        // Node interaction detected
        
        // === PHASE 1: Immediate Visual Effects (Synchronous) ===
        // These execute immediately before any async operations
        
        
        // Center on clicked node (immediate visual effect) - REMOVED
        // Centering functionality has been disabled to prevent unwanted repositioning
        // when nodes are clicked. All other click functionality remains intact.
        // try {
        //     if (this.isRadialLayout) {
        //         if (typeof this.centerOnNodeRadial === 'function') {
        //             this.centerOnNodeRadial(d);
        //         } else {
        //             console.error('[CodeTree] centerOnNodeRadial is not a function!');
        //         }
        //     } else {
        //         if (typeof this.centerOnNode === 'function') {
        //             this.centerOnNode(d);
        //         } else {
        //             console.error('[CodeTree] centerOnNode is not a function!');
        //         }
        //     }
        // } catch (error) {
        //     console.error('[CodeTree] ERROR during centering:', error, error.stack);
        // }
        
        
        // Highlight with larger icon (immediate visual effect)
        try {
            if (typeof this.highlightActiveNode === 'function') {
                this.highlightActiveNode(d);
            } else {
                console.error('[CodeTree] highlightActiveNode is not a function!');
            }
        } catch (error) {
            console.error('[CodeTree] ERROR during highlightActiveNode:', error, error.stack);
        }
        
        
        // Show parent context (immediate visual effect)
        try {
            if (typeof this.showWithParent === 'function') {
                this.showWithParent(d);
            } else {
                console.error('[CodeTree] showWithParent is not a function!');
            }
        } catch (error) {
            console.error('[CodeTree] ERROR during showWithParent:', error, error.stack);
        }
        
        
        // Add pulsing animation immediately for directories
        
        if (d.data.type === 'directory' && !d.data.loaded) {
            try {
                if (typeof this.addLoadingPulse === 'function') {
                    this.addLoadingPulse(d);
                } else {
                    console.error('[CodeTree] addLoadingPulse is not a function!');
                }
            } catch (error) {
                console.error('[CodeTree] ERROR during addLoadingPulse:', error, error.stack);
            }
        } else {
        }
        
        
        // === PHASE 2: Prepare Data (Synchronous) ===
        
        
        // Get selected languages from checkboxes
        const selectedLanguages = [];
        const checkboxes = document.querySelectorAll('.language-checkbox:checked');
        checkboxes.forEach(cb => {
            selectedLanguages.push(cb.value);
        });
        
        // Get ignore patterns
        const ignorePatternsElement = document.getElementById('ignore-patterns');
        const ignorePatterns = ignorePatternsElement?.value || '';
        
        
        // === PHASE 3: Async Operations (Delayed) ===
        // Add a small delay to ensure visual effects are rendered first
        
        // For directories that haven't been loaded yet, request discovery
        console.log('🔍 [LOAD CHECK]', {
            type: d.data.type,
            loaded: d.data.loaded,
            loadedType: typeof d.data.loaded,
            isDirectory: d.data.type === 'directory',
            notLoaded: !d.data.loaded,
            shouldLoad: d.data.type === 'directory' && !d.data.loaded
        });
        if (d.data.type === 'directory' && !d.data.loaded) {
            // Prevent duplicate requests
            if (this.loadingNodes.has(d.data.path)) {
                this.showNotification(`Already loading: ${d.data.name}`, 'warning');
                return;
            }
            
            // Mark as loading immediately to prevent duplicate requests
            d.data.loaded = 'loading';
            this.loadingNodes.add(d.data.path);
            
            // Ensure path is absolute or relative to working directory
            const fullPath = this.ensureFullPath(d.data.path);
            
            // CRITICAL DEBUG: Log directory loading attempt
            console.log('🚀 [SUBDIRECTORY LOADING] Attempting to load:', {
                originalPath: d.data.path,
                fullPath: fullPath,
                nodeType: d.data.type,
                loaded: d.data.loaded,
                hasSocket: !!this.socket,
                workingDir: this.getWorkingDirectory()
            });
            
            // Sending discovery request for child content
            
            // Store reference to the D3 node for later expansion
            const clickedD3Node = d;
            
            // Delay the socket request to ensure visual effects are rendered
            // Use arrow function to preserve 'this' context
            setTimeout(() => {
                
                // CRITICAL FIX: Use REST API instead of WebSocket for reliability
                // The simple view works because it uses REST API, so let's do the same
                console.log('📡 [SUBDIRECTORY LOADING] Using REST API for directory:', {
                    originalPath: d.data.path,
                    fullPath: fullPath,
                    apiUrl: `${window.location.origin}/api/directory/list?path=${encodeURIComponent(fullPath)}`,
                    loadingNodesSize: this.loadingNodes.size,
                    loadingNodesContent: Array.from(this.loadingNodes)
                });
                
                const apiUrl = `${window.location.origin}/api/directory/list?path=${encodeURIComponent(fullPath)}`;
                
                fetch(apiUrl)
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                        }
                        return response.json();
                    })
                    .then(data => {
                        console.log('✅ [SUBDIRECTORY LOADING] REST API response:', {
                            data: data,
                            pathToDelete: d.data.path,
                            loadingNodesBefore: Array.from(this.loadingNodes)
                        });
                        
                        // Remove from loading set
                        const deleted = this.loadingNodes.delete(d.data.path);
                        d.data.loaded = true;
                        
                        console.log('🧹 [SUBDIRECTORY LOADING] Cleanup result:', {
                            pathDeleted: d.data.path,
                            wasDeleted: deleted,
                            loadingNodesAfter: Array.from(this.loadingNodes)
                        });
                        
                        // Remove loading animation
                        const d3Node = this.findD3NodeByPath(d.data.path);
                        if (d3Node) {
                            this.removeLoadingPulse(d3Node);
                        }
                        
                        // Process the directory contents
                        if (data.exists && data.is_directory && data.contents) {
                            const node = this.findNodeByPath(d.data.path);
                            if (node) {
                                // Add children to the node
                                node.children = data.contents.map(item => ({
                                    name: item.name,
                                    path: `${d.data.path}/${item.name}`,
                                    type: item.is_directory ? 'directory' : 'file',
                                    loaded: item.is_directory ? false : undefined,
                                    analyzed: !item.is_directory ? false : undefined,
                                    expanded: false,
                                    children: item.is_directory ? [] : undefined
                                }));
                                node.loaded = true;
                                node.expanded = true;
                                
                                // Update D3 hierarchy
                                if (this.root && this.svg) {
                                    const oldRoot = this.root;
                                    this.root = d3.hierarchy(this.treeData);
                                    this.root.x0 = this.height / 2;
                                    this.root.y0 = 0;
                                    
                                    this.preserveExpansionState(oldRoot, this.root);
                                    
                                    const updatedD3Node = this.findD3NodeByPath(d.data.path);
                                    if (updatedD3Node && updatedD3Node.children && updatedD3Node.children.length > 0) {
                                        updatedD3Node._children = null;
                                        updatedD3Node.data.expanded = true;
                                    }
                                    
                                    this.update(updatedD3Node || this.root);
                                }
                                
                                this.updateBreadcrumb(`Loaded ${data.contents.length} items`, 'success');
                                this.showNotification(`Loaded ${data.contents.length} items from ${d.data.name}`, 'success');
                            }
                        } else {
                            this.showNotification(`Directory ${d.data.name} is empty or inaccessible`, 'warning');
                        }
                    })
                    .catch(error => {
                        console.error('❌ [SUBDIRECTORY LOADING] REST API error:', {
                            error: error.message,
                            stack: error.stack,
                            pathToDelete: d.data.path,
                            loadingNodesBefore: Array.from(this.loadingNodes)
                        });
                        
                        // Clean up loading state
                        const deleted = this.loadingNodes.delete(d.data.path);
                        d.data.loaded = false;
                        
                        console.log('🧹 [SUBDIRECTORY LOADING] Error cleanup:', {
                            pathDeleted: d.data.path,
                            wasDeleted: deleted,
                            loadingNodesAfter: Array.from(this.loadingNodes)
                        });
                        
                        const d3Node = this.findD3NodeByPath(d.data.path);
                        if (d3Node) {
                            this.removeLoadingPulse(d3Node);
                        }
                        
                        this.showNotification(`Failed to load ${d.data.name}: ${error.message}`, 'error');
                    });
                
                this.updateBreadcrumb(`Loading ${d.data.name}...`, 'info');
                this.showNotification(`Loading directory: ${d.data.name}`, 'info');
                
                // Keep the original else clause for when fetch isn't available
                if (!window.fetch) {
                    console.error('❌ [SUBDIRECTORY LOADING] No WebSocket connection available!');
                    this.showNotification(`Cannot load directory: No connection`, 'error');
                    
                    // Clear loading state since the request failed
                    this.loadingNodes.delete(d.data.path);
                    const d3Node = this.findD3NodeByPath(d.data.path);
                    if (d3Node) {
                        this.removeLoadingPulse(d3Node);
                    }
                    // Reset the loaded flag
                    d.data.loaded = false;
                }
            }, 100);  // 100ms delay to ensure visual effects render first
        } 
        // For files that haven't been analyzed, request analysis
        else if (d.data.type === 'file' && !d.data.analyzed) {
            // Only analyze files of selected languages
            const fileLanguage = this.detectLanguage(d.data.path);
            if (!selectedLanguages.includes(fileLanguage) && fileLanguage !== 'unknown') {
                this.showNotification(`Skipping ${d.data.name} - ${fileLanguage} not selected`, 'warning');
                return;
            }
            
            // Add pulsing animation immediately
            this.addLoadingPulse(d);
            
            // Mark as loading immediately
            d.data.analyzed = 'loading';
            
            // Ensure path is absolute or relative to working directory
            const fullPath = this.ensureFullPath(d.data.path);
            
            // Delay the socket request to ensure visual effects are rendered
            setTimeout(() => {
                
                if (this.socket) {
                    this.socket.emit('code:analyze:file', {
                        path: fullPath
                    });
                    
                    this.updateBreadcrumb(`Analyzing ${d.data.name}...`, 'info');
                    this.showNotification(`Analyzing: ${d.data.name}`, 'info');
                }
            }, 100);  // 100ms delay to ensure visual effects render first
        }
        // Toggle children visibility for already loaded nodes
        else if (d.data.type === 'directory' && d.data.loaded === true) {
            // Directory is loaded, toggle expansion
            if (d.children) {
                // Collapse - hide children
                d._children = d.children;
                d.children = null;
                d.data.expanded = false;
            } else if (d._children) {
                // Expand - show children
                d.children = d._children;
                d._children = null;
                d.data.expanded = true;
            } else if (d.data.children && d.data.children.length > 0) {
                // Children exist in data but not in D3 node, recreate hierarchy
                this.root = d3.hierarchy(this.treeData);
                const updatedD3Node = this.findD3NodeByPath(d.data.path);
                if (updatedD3Node) {
                    updatedD3Node.children = updatedD3Node._children || updatedD3Node.children;
                    updatedD3Node._children = null;
                    updatedD3Node.data.expanded = true;
                }
            }
            this.update(this.root);
        }
        // Also handle other nodes that might have children
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
        } else {
        }
        
        // Update selection
        this.selectedNode = d;
        try {
            this.highlightNode(d);
        } catch (error) {
            console.error('[CodeTree] ERROR during highlightNode:', error);
        }
        
    }
    
    /**
     * Ensure path is absolute or relative to working directory
     */
    ensureFullPath(path) {
        console.log('🔗 ensureFullPath called with:', path);
        
        if (!path) return path;
        
        // If already absolute, return as is
        if (path.startsWith('/')) {
            console.log('  → Already absolute, returning:', path);
            return path;
        }
        
        // Get working directory
        const workingDir = this.getWorkingDirectory();
        console.log('  → Working directory:', workingDir);
        
        if (!workingDir) {
            console.log('  → No working directory, returning original:', path);
            return path;
        }
        
        // Special handling for root path
        if (path === '.') {
            console.log('  → Root path detected, returning working dir:', workingDir);
            return workingDir;
        }
        
        // If path equals working directory, return as is
        if (path === workingDir) {
            console.log('  → Path equals working directory, returning:', workingDir);
            return workingDir;
        }
        
        // Combine working directory with relative path
        const result = `${workingDir}/${path}`.replace(/\/+/g, '/');
        console.log('  → Combining with working dir, result:', result);
        return result;
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
        // DISABLED: All zoom reset operations have been disabled to prevent tree centering/movement
        // The tree should remain stationary and not center/move when interacting with nodes
        console.log('[CodeTree] resetZoom called but disabled - no zoom reset will occur');
        this.showNotification('Zoom reset disabled - tree remains stationary', 'info');
        return;
    }

    /**
     * REMOVED: Focus on a specific node and its subtree
     * This method has been completely disabled to prevent unwanted tree movement.
     * All centering and focus functionality has been removed from the code tree.
     */
    focusOnNode(node) {
        // Method disabled - no focusing/centering operations will be performed
        console.log('[CodeTree] focusOnNode called but disabled - no focusing will occur');
        return;
        
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
});/* Cache buster: 1756393851 */
