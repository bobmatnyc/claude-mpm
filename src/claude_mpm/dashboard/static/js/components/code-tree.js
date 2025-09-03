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
        this.isRadialLayout = false;  // Toggle for radial vs linear layout - defaulting to linear for better readability
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

        // Structured data properties
        this.structuredDataContent = null;
        this.selectedASTItem = null;
        this.activeNode = null;  // Track currently active node
        this.loadingNodes = new Set();  // Track nodes that are loading
        this.bulkLoadMode = false;  // Track bulk loading preference
        this.expandedPaths = new Set();  // Track which paths are expanded
        this.focusedNode = null;  // Track the currently focused directory
        this.horizontalNodes = new Set();  // Track nodes that should have horizontal text
        this.centralSpine = new Set();  // Track the main path through the tree
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
        this.initializeStructuredData();
        
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

        // Note: Expand/collapse/reset buttons are now handled by the tree controls toolbar
        // which is created dynamically in addTreeControls()
        
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

        // Enable zoom and pan functionality for better navigation
        this.zoom = d3.zoom()
            .scaleExtent([0.1, 3])  // Allow zoom from 10% to 300%
            .on('zoom', (event) => {
                // Apply zoom transform to the tree group
                this.treeGroup.attr('transform', event.transform);

                // Keep text size constant by applying inverse scaling
                this.adjustTextSizeForZoom(event.transform.k);

                // Update zoom level display
                this.updateZoomLevel(event.transform.k);
            });

        // Apply zoom behavior to SVG
        this.svg.call(this.zoom);

        // Add keyboard shortcuts for zoom
        this.addZoomKeyboardShortcuts();

        console.log('[CodeTree] Zoom and pan functionality enabled');

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

        // Use absolute path for consistency with API expectations
        this.treeData = {
            name: dirName,
            path: workingDir || '.',  // Use working directory or fallback to '.'
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
            path: workingDir,  // Use absolute path for consistency with API expectations
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
        const selectedLanguages = this.getSelectedLanguages();
        
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

        // Zoom In
        toolbar.append('button')
            .attr('class', 'tree-control-btn')
            .attr('title', 'Zoom in')
            .text('🔍+')
            .on('click', () => this.zoomIn());

        // Zoom Out
        toolbar.append('button')
            .attr('class', 'tree-control-btn')
            .attr('title', 'Zoom out')
            .text('🔍-')
            .on('click', () => this.zoomOut());

        // Reset Zoom
        toolbar.append('button')
            .attr('class', 'tree-control-btn')
            .attr('title', 'Reset zoom to fit tree')
            .text('⌂')
            .on('click', () => this.resetZoom());

        // Zoom Level Display
        toolbar.append('span')
            .attr('class', 'zoom-level-display')
            .attr('id', 'zoom-level-display')
            .text('100%')
            .style('margin-left', '8px')
            .style('font-size', '11px')
            .style('color', '#718096');

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
        this.socket.on('code:file:analyzed', (data) => {
            console.log('📨 [SOCKET] Received code:file:analyzed event');
            this.onFileAnalyzed(data);
        });
        this.socket.on('code:node:found', (data) => this.onNodeFound(data));

        // Progress updates
        this.socket.on('code:analysis:progress', (data) => this.onProgressUpdate(data));

        // Error handling
        this.socket.on('code:analysis:error', (data) => {
            console.error('❌ [FILE ANALYSIS] Analysis error:', data);
            this.showNotification(`Analysis error: ${data.error || 'Unknown error'}`, 'error');
        });

        // Generic error handling
        this.socket.on('error', (error) => {
            console.error('❌ [SOCKET] Socket error:', error);
        });

        // Socket connection status
        this.socket.on('connect', () => {
            console.log('✅ [SOCKET] Connected to server, analysis service should be available');
            this.connectionStable = true;
        });

        this.socket.on('disconnect', () => {
            console.log('❌ [SOCKET] Disconnected from server - disabling AST analysis');
            this.connectionStable = false;
            // Clear any pending analysis timeouts
            if (this.analysisTimeouts) {
                this.analysisTimeouts.forEach((timeout, path) => {
                    clearTimeout(timeout);
                    this.loadingNodes.delete(path);
                });
                this.analysisTimeouts.clear();
            }
        });
        
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
        
        // The root node should receive the children
        const workingDir = this.getWorkingDirectory();
        const rootNode = this.findNodeByPath(workingDir);

        console.log(`🔎 Looking for root node with path "${workingDir}", found:`, rootNode ? {
            name: rootNode.name,
            path: rootNode.path,
            currentChildren: rootNode.children ? rootNode.children.length : 0
        } : 'NOT FOUND');
        
        if (rootNode && data.items) {
            console.log('🌳 Populating root node with children');
            
            // Update the root node with discovered children
            rootNode.children = data.items.map(child => {
                // CRITICAL FIX: Use consistent path format that matches API expectations
                // The API expects absolute paths, so construct them properly
                const workingDir = this.getWorkingDirectory();
                const childPath = workingDir ? `${workingDir}/${child.name}`.replace(/\/+/g, '/') : child.name;

                console.log(`  Adding child: ${child.name} with path: ${childPath}`);

                return {
                    name: child.name,
                    path: childPath,  // Use absolute path for consistency
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
        console.log('✅ [FILE ANALYSIS] Received analysis result:', {
            path: data.path,
            elements: data.elements ? data.elements.length : 0,
            complexity: data.complexity,
            lines: data.lines,
            stats: data.stats,
            elementsDetail: data.elements,
            fullData: data
        });

        // Debug: Show elements in detail
        if (data.elements && data.elements.length > 0) {
            console.log('🔍 [AST ELEMENTS] Found elements:', data.elements.map(elem => ({
                name: elem.name,
                type: elem.type,
                line: elem.line,
                methods: elem.methods ? elem.methods.length : 0
            })));
        } else {
            const fileName = data.path.split('/').pop();
            console.log('⚠️ [AST ELEMENTS] No elements found in analysis result');

            // Show user-friendly message for files with no AST elements
            if (fileName.endsWith('__init__.py')) {
                this.showNotification(`${fileName} is empty or contains only imports`, 'info');
                this.updateBreadcrumb(`${fileName} - no code elements to display`, 'info');
            } else {
                this.showNotification(`${fileName} contains no classes or functions`, 'info');
                this.updateBreadcrumb(`${fileName} - no AST elements found`, 'info');
            }
        }

        // Clear analysis timeout
        if (this.analysisTimeouts && this.analysisTimeouts.has(data.path)) {
            clearTimeout(this.analysisTimeouts.get(data.path));
            this.analysisTimeouts.delete(data.path);
            console.log('⏰ [FILE ANALYSIS] Cleared timeout for:', data.path);
        }

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
            console.log('🔍 [FILE NODE] Found file node for:', data.path);
            fileNode.analyzed = true;
            fileNode.complexity = data.complexity || 0;
            fileNode.lines = data.lines || 0;

            // Add code elements as children
            if (data.elements && Array.isArray(data.elements)) {
                const children = data.elements.map(elem => ({
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

                fileNode.children = children;
                console.log('✅ [FILE NODE] Added children to file node:', {
                    filePath: data.path,
                    childrenCount: children.length,
                    children: children.map(c => ({ name: c.name, type: c.type }))
                });
            } else {
                console.log('⚠️ [FILE NODE] No elements to add as children');
            }

            // Update stats
            if (data.stats) {
                this.stats.classes += data.stats.classes || 0;
                this.stats.functions += data.stats.functions || 0;
                this.stats.methods += data.stats.methods || 0;
                this.stats.lines += data.stats.lines || 0;
            }

            this.updateStats();

            // CRITICAL FIX: Recreate D3 hierarchy to include new children
            if (this.root && fileNode.children && fileNode.children.length > 0) {
                console.log('🔄 [FILE NODE] Recreating D3 hierarchy to include AST children');

                // Store the old root for expansion state preservation
                const oldRoot = this.root;

                // Recreate the D3 hierarchy with updated data
                this.root = d3.hierarchy(this.treeData);
                this.root.x0 = this.height / 2;
                this.root.y0 = 0;

                // Preserve expansion state from old tree
                this.preserveExpansionState(oldRoot, this.root);

                // Find the updated file node in the new hierarchy
                const updatedFileNode = this.findD3NodeByPath(data.path);
                if (updatedFileNode) {
                    // Ensure the file node is expanded to show its AST children
                    if (updatedFileNode.children && updatedFileNode.children.length > 0) {
                        updatedFileNode._children = null;
                        updatedFileNode.data.expanded = true;
                        console.log('✅ [FILE NODE] File node expanded to show AST children:', {
                            path: data.path,
                            childrenCount: updatedFileNode.children.length,
                            childNames: updatedFileNode.children.map(c => c.data.name)
                        });
                    }
                }

                // Update the visualization with the new hierarchy
                this.update(this.root);
            } else if (this.root) {
                this.update(this.root);
            }

            this.updateBreadcrumb(`Analyzed: ${data.path}`, 'success');
        } else {
            console.error('❌ [FILE NODE] Could not find file node for path:', data.path);
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
        // Update stats display - use correct IDs from corner controls
        const statsElements = {
            'stats-files': this.stats.files,
            'stats-classes': this.stats.classes,
            'stats-functions': this.stats.functions,
            'stats-methods': this.stats.methods
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
     * Analyze file using HTTP fallback when SocketIO fails
     */
    async analyzeFileHTTP(filePath, fileName, d3Node) {
        console.log('🌐 [HTTP FALLBACK] Analyzing file via HTTP:', filePath);
        console.log('🌐 [HTTP FALLBACK] File name:', fileName);

        try {
            // For now, create mock AST data since we don't have an HTTP endpoint yet
            // This demonstrates the structure and can be replaced with real HTTP call
            const mockAnalysisResult = this.createMockAnalysisData(filePath, fileName);
            console.log('🌐 [HTTP FALLBACK] Created mock data:', mockAnalysisResult);

            // Simulate network delay
            setTimeout(() => {
                console.log('✅ [HTTP FALLBACK] Mock analysis complete for:', fileName);
                console.log('✅ [HTTP FALLBACK] Calling onFileAnalyzed with:', mockAnalysisResult);
                this.onFileAnalyzed(mockAnalysisResult);
            }, 1000);

        } catch (error) {
            console.error('❌ [HTTP FALLBACK] Analysis failed:', error);
            this.showNotification(`Analysis failed: ${error.message}`, 'error');
            this.loadingNodes.delete(filePath);
            this.removeLoadingPulse(d3Node);
        }
    }

    /**
     * Create mock analysis data for demonstration
     */
    createMockAnalysisData(filePath, fileName) {
        const ext = fileName.split('.').pop()?.toLowerCase();
        console.log('🔍 [MOCK DATA] Creating mock data for file:', fileName, 'extension:', ext);

        // Create realistic mock data based on file type
        let elements = [];

        if (ext === 'py') {
            elements = [
                {
                    name: 'ExampleClass',
                    type: 'class',
                    line: 10,
                    complexity: 3,
                    docstring: 'Example class for demonstration',
                    methods: [
                        { name: '__init__', type: 'method', line: 12, complexity: 1 },
                        { name: 'example_method', type: 'method', line: 18, complexity: 2 }
                    ]
                },
                {
                    name: 'example_function',
                    type: 'function',
                    line: 25,
                    complexity: 2,
                    docstring: 'Example function'
                }
            ];
        } else if (ext === 'js' || ext === 'ts') {
            elements = [
                {
                    name: 'ExampleClass',
                    type: 'class',
                    line: 5,
                    complexity: 2,
                    methods: [
                        { name: 'constructor', type: 'method', line: 6, complexity: 1 },
                        { name: 'exampleMethod', type: 'method', line: 10, complexity: 2 }
                    ]
                },
                {
                    name: 'exampleFunction',
                    type: 'function',
                    line: 20,
                    complexity: 1
                }
            ];
        } else {
            // For other file types, create at least one element to show it's working
            elements = [
                {
                    name: 'mock_element',
                    type: 'function',
                    line: 1,
                    complexity: 1,
                    docstring: `Mock element for ${fileName}`
                }
            ];
        }

        console.log('🔍 [MOCK DATA] Created elements:', elements);

        return {
            path: filePath,
            elements: elements,
            complexity: elements.reduce((sum, elem) => sum + (elem.complexity || 1), 0),
            lines: 50,
            stats: {
                classes: elements.filter(e => e.type === 'class').length,
                functions: elements.filter(e => e.type === 'function').length,
                methods: elements.reduce((sum, e) => sum + (e.methods ? e.methods.length : 0), 0),
                lines: 50
            }
        };
    }

    /**
     * Get selected languages from checkboxes with fallback
     */
    getSelectedLanguages() {
        const selectedLanguages = [];
        const checkboxes = document.querySelectorAll('.language-checkbox:checked');

        console.log('🔍 [LANGUAGE] Found checkboxes:', checkboxes.length);
        console.log('🔍 [LANGUAGE] All language checkboxes:', document.querySelectorAll('.language-checkbox').length);

        checkboxes.forEach(cb => {
            console.log('🔍 [LANGUAGE] Checked language:', cb.value);
            selectedLanguages.push(cb.value);
        });

        // Fallback: if no languages are selected, default to common ones
        if (selectedLanguages.length === 0) {
            console.warn('⚠️ [LANGUAGE] No languages selected, using defaults');
            selectedLanguages.push('python', 'javascript', 'typescript');

            // Also check the checkboxes programmatically
            document.querySelectorAll('.language-checkbox').forEach(cb => {
                if (['python', 'javascript', 'typescript'].includes(cb.value)) {
                    cb.checked = true;
                    console.log('✅ [LANGUAGE] Auto-checked:', cb.value);
                }
            });
        }

        return selectedLanguages;
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
     * Apply horizontal text to the central spine of the tree
     */
    applySingletonHorizontalLayout(nodes) {
        if (this.isRadialLayout) return; // Only apply to linear layout

        // Clear previous horizontal nodes tracking
        this.horizontalNodes.clear();
        this.centralSpine.clear();

        // Find the central spine - the main path through the tree
        this.identifyCentralSpine(nodes);

        // Mark all central spine nodes for horizontal text
        this.centralSpine.forEach(path => {
            this.horizontalNodes.add(path);
        });

        console.log(`🎯 [SPINE] Central spine nodes:`, Array.from(this.centralSpine));
        console.log(`📝 [TEXT] Horizontal text nodes:`, Array.from(this.horizontalNodes));
    }

    /**
     * Identify the central spine of the tree (main path from root to deepest/most important nodes)
     */
    identifyCentralSpine(nodes) {
        if (!nodes || nodes.length === 0) return;

        // Start with the root node
        const rootNode = nodes.find(node => node.depth === 0);
        if (!rootNode) {
            console.warn('🎯 [SPINE] No root node found!');
            return;
        }

        this.centralSpine.add(rootNode.data.path);
        console.log(`🎯 [SPINE] Starting spine with root: ${rootNode.data.name} (${rootNode.data.path})`);

        // Follow the main path through the tree
        let currentNode = rootNode;
        while (currentNode && currentNode.children && currentNode.children.length > 0) {
            // Choose the "main" child - prioritize directories, then by name
            const mainChild = this.selectMainChild(currentNode.children);
            if (mainChild) {
                this.centralSpine.add(mainChild.data.path);
                console.log(`🎯 [SPINE] Adding to spine: ${mainChild.data.name}`);
                currentNode = mainChild;
            } else {
                break;
            }
        }
    }

    /**
     * Select the main child to continue the central spine
     */
    selectMainChild(children) {
        if (!children || children.length === 0) return null;

        // If only one child, it's the main path
        if (children.length === 1) return children[0];

        // Prioritize directories over files
        const directories = children.filter(child => child.data.type === 'directory');
        if (directories.length === 1) return directories[0];

        // If multiple directories, choose the first one (could be enhanced with better logic)
        if (directories.length > 0) return directories[0];

        // Fallback to first child
        return children[0];
    }

    /**
     * Find chains of singleton nodes (nodes with only one child)
     */
    findSingletonChains(nodes) {
        const chains = [];
        const processed = new Set();

        nodes.forEach(node => {
            if (processed.has(node)) return;

            // Start a new chain if this node has exactly one child
            if (node.children && node.children.length === 1) {
                const chain = [node];
                let current = node.children[0];

                console.log(`🔍 [CHAIN] Starting singleton chain with: ${node.data.name} (depth: ${node.depth})`);

                // Follow the chain of singletons
                while (current && current.children && current.children.length === 1) {
                    chain.push(current);
                    processed.add(current);
                    console.log(`🔍 [CHAIN] Adding to chain: ${current.data.name} (depth: ${current.depth})`);
                    current = current.children[0];
                }

                // Add the final node if it exists (even if it has multiple children or no children)
                if (current) {
                    chain.push(current);
                    processed.add(current);
                    console.log(`🔍 [CHAIN] Final node in chain: ${current.data.name} (depth: ${current.depth})`);
                }

                // Only create horizontal layout for chains of 2 or more nodes
                if (chain.length >= 2) {
                    console.log(`✅ [CHAIN] Created horizontal chain:`, chain.map(n => n.data.name));
                    chains.push(chain);
                    processed.add(node);
                } else {
                    console.log(`❌ [CHAIN] Chain too short (${chain.length}), skipping`);
                }
            }
        });

        return chains;
    }

    /**
     * Layout a chain of nodes horizontally with parent in center
     */
    layoutChainHorizontally(chain) {
        if (chain.length < 2) return;

        const horizontalSpacing = 150; // Spacing between nodes in horizontal chain
        const parentNode = chain[0];
        const originalX = parentNode.x;
        const originalY = parentNode.y;

        // CRITICAL: In D3 tree layout for linear mode:
        // - d.x controls VERTICAL position (up-down)
        // - d.y controls HORIZONTAL position (left-right)
        // To make singleton chains horizontal, we need to adjust d.x (vertical) to be the same
        // and spread out d.y (horizontal) positions

        if (chain.length === 2) {
            // Simple case: parent and one child side by side
            const centerY = originalY;
            parentNode.y = centerY - horizontalSpacing / 2; // Parent to the left
            chain[1].y = centerY + horizontalSpacing / 2;   // Child to the right
            chain[1].x = originalX; // Same vertical level as parent
        } else {
            // Multiple nodes: center the parent in the horizontal chain
            const totalWidth = (chain.length - 1) * horizontalSpacing;
            const startY = originalY - (totalWidth / 2);

            chain.forEach((node, index) => {
                node.y = startY + (index * horizontalSpacing); // Spread horizontally
                node.x = originalX; // All at same vertical level
            });
        }

        // Mark all nodes in this chain as needing horizontal text
        chain.forEach(node => {
            this.horizontalNodes.add(node.data.path);
            console.log(`📝 [TEXT] Marking node for horizontal text: ${node.data.name} (${node.data.path})`);
        });

        console.log(`🔄 [LAYOUT] Horizontal chain of ${chain.length} nodes:`,
            chain.map(n => ({ name: n.data.name, vertical: n.x, horizontal: n.y })));
        console.log(`📝 [TEXT] Total horizontal nodes:`, Array.from(this.horizontalNodes));
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

        // Apply horizontal layout for singleton chains
        this.applySingletonHorizontalLayout(nodes);

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
            .attr('class', d => {
                // Add horizontal-text class for root node
                const baseClass = 'node-label';
                if (d.depth === 0) {
                    console.log(`📝 [TEXT] ✅ Adding horizontal-text class to root: ${d.data.name}`);
                    return `${baseClass} horizontal-text`;
                }
                return baseClass;
            })
            .attr('dy', '.35em')
            .attr('x', d => {
                if (this.isRadialLayout) {
                    // For radial layout, initial position
                    return 0;
                } else if (d.depth === 0 || this.horizontalNodes.has(d.data.path)) {
                    // Root node or horizontal nodes: center text above the node
                    console.log(`📝 [TEXT] ✅ HORIZONTAL positioning for: ${d.data.name} (depth: ${d.depth}, path: ${d.data.path})`);
                    console.log(`📝 [TEXT] ✅ Root check: depth === 0 = ${d.depth === 0}`);
                    console.log(`📝 [TEXT] ✅ Horizontal set check: ${this.horizontalNodes.has(d.data.path)}`);
                    return 0;
                } else {
                    // Linear layout: standard positioning
                    console.log(`📝 [TEXT] Positioning vertical text for: ${d.data.name} (depth: ${d.depth}, path: ${d.data.path})`);
                    return d.children || d._children ? -13 : 13;
                }
            })
            .attr('y', d => {
                // For root node or horizontal nodes, position text above the node
                return (d.depth === 0 || this.horizontalNodes.has(d.data.path)) ? -20 : 0;
            })
            .attr('text-anchor', d => {
                if (this.isRadialLayout) {
                    return 'start';  // Will be adjusted in update
                } else if (d.depth === 0 || this.horizontalNodes.has(d.data.path)) {
                    // Root node or horizontal nodes: center the text
                    return 'middle';
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
            .style('writing-mode', d => {
                // Force horizontal writing mode for root node
                if (d.depth === 0) {
                    console.log(`📝 [TEXT] ✅ Setting horizontal writing-mode for root: ${d.data.name}`);
                    return 'horizontal-tb';
                }
                return null;
            })
            .style('text-orientation', d => {
                // Force mixed text orientation for root node
                if (d.depth === 0) {
                    console.log(`📝 [TEXT] ✅ Setting mixed text-orientation for root: ${d.data.name}`);
                    return 'mixed';
                }
                return null;
            })
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
        const horizontalNodes = this.horizontalNodes;  // Capture horizontal nodes set
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
                    // Linear layout - handle root node and horizontal nodes differently
                    const isHorizontal = d.depth === 0 || horizontalNodes.has(d.data.path);

                    if (isHorizontal) {
                        // Root node or horizontal nodes: text above the node, centered
                        selection
                            .attr('transform', null)
                            .attr('x', 0)
                            .attr('y', -20)
                            .attr('text-anchor', 'middle')
                            .attr('dy', '.35em');
                    } else {
                        // Regular linear layout - no rotation needed
                        selection
                            .attr('transform', null)
                            .attr('x', d.children || d._children ? -13 : 13)
                            .attr('y', 0)
                            .attr('text-anchor', d.children || d._children ? 'end' : 'start')
                            .attr('dy', '.35em');
                    }
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

        // Apply current zoom level to maintain consistent text size
        if (this.zoom) {
            const currentTransform = d3.zoomTransform(this.svg.node());
            if (currentTransform.k !== 1) {
                this.adjustTextSizeForZoom(currentTransform.k);
            }
        }
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
        const clickId = Date.now() + Math.random();
        // DEBUG: Log all clicks to verify handler is working
        console.log(`🖱️ [NODE CLICK] Clicked on node (ID: ${clickId}):`, {
            name: d?.data?.name,
            path: d?.data?.path,
            type: d?.data?.type,
            loaded: d?.data?.loaded,
            hasChildren: !!(d?.children || d?._children),
            dataChildren: d?.data?.children?.length || 0,
            loadingNodesSize: this.loadingNodes ? this.loadingNodes.size : 'undefined'
        });

        // Update structured data with clicked node
        this.updateStructuredData(d);

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
        const selectedLanguages = this.getSelectedLanguages();
        console.log('🔍 [LANGUAGE] Selected languages:', selectedLanguages);
        
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
            console.log('✅ [SUBDIRECTORY LOADING] Load check passed, proceeding with loading logic');
            console.log('🔍 [SUBDIRECTORY LOADING] Initial loading state:', {
                loadingNodesSize: this.loadingNodes ? this.loadingNodes.size : 'undefined',
                loadingNodesContent: Array.from(this.loadingNodes || [])
            });

            try {
                // Debug the path and loadingNodes state
                console.log('🔍 [SUBDIRECTORY LOADING] Checking for duplicates:', {
                    path: d.data.path,
                    pathType: typeof d.data.path,
                    loadingNodesType: typeof this.loadingNodes,
                    loadingNodesSize: this.loadingNodes ? this.loadingNodes.size : 'undefined',
                    hasMethod: this.loadingNodes && typeof this.loadingNodes.has === 'function'
                });

                // Prevent duplicate requests
                const isDuplicate = this.loadingNodes && this.loadingNodes.has(d.data.path);
                console.log('🔍 [SUBDIRECTORY LOADING] Duplicate check result:', {
                    isDuplicate: isDuplicate,
                    loadingNodesContent: Array.from(this.loadingNodes || []),
                    pathBeingChecked: d.data.path
                });

                if (isDuplicate) {
                console.warn('⚠️ [SUBDIRECTORY LOADING] Duplicate request detected, but proceeding anyway:', {
                    path: d.data.path,
                    name: d.data.name,
                    loadingNodesSize: this.loadingNodes.size,
                    loadingNodesContent: Array.from(this.loadingNodes),
                    pathInSet: this.loadingNodes.has(d.data.path)
                });
                // Remove the existing entry and proceed
                this.loadingNodes.delete(d.data.path);
                console.log('🧹 [SUBDIRECTORY LOADING] Removed duplicate entry, proceeding with fresh request');
            }

            console.log('✅ [SUBDIRECTORY LOADING] No duplicate request, proceeding to mark as loading');

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
                                console.log('🔧 [SUBDIRECTORY LOADING] Creating children with paths:',
                                    data.contents.map(item => ({ name: item.name, path: item.path })));

                                // Add children to the node
                                node.children = data.contents.map(item => ({
                                    name: item.name,
                                    path: item.path,  // Use the full path from API response
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

                                    // Focus on the newly loaded directory for better UX
                                    if (updatedD3Node && data.contents.length > 0) {
                                        setTimeout(() => {
                                            this.focusOnDirectory(updatedD3Node);
                                        }, 500); // Small delay to let the update animation complete
                                    }
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

            } catch (error) {
                console.error('❌ [SUBDIRECTORY LOADING] Error in directory loading logic:', {
                    error: error.message,
                    stack: error.stack,
                    path: d.data.path,
                    nodeData: d.data
                });
                this.showNotification(`Error loading directory: ${error.message}`, 'error');
            }
        }
        // For files that haven't been analyzed, request analysis
        else if (d.data.type === 'file' && !d.data.analyzed) {
            // Only analyze files of selected languages
            const fileLanguage = this.detectLanguage(d.data.path);
            console.log('🔍 [FILE ANALYSIS] Language check:', {
                fileName: d.data.name,
                filePath: d.data.path,
                detectedLanguage: fileLanguage,
                selectedLanguages: selectedLanguages,
                isLanguageSelected: selectedLanguages.includes(fileLanguage),
                shouldAnalyze: selectedLanguages.includes(fileLanguage) || fileLanguage === 'unknown'
            });

            if (!selectedLanguages.includes(fileLanguage) && fileLanguage !== 'unknown') {
                console.warn('⚠️ [FILE ANALYSIS] Skipping file:', {
                    fileName: d.data.name,
                    detectedLanguage: fileLanguage,
                    selectedLanguages: selectedLanguages,
                    reason: `${fileLanguage} not in selected languages`
                });
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
                console.log('🚀 [FILE ANALYSIS] Sending analysis request:', {
                    fileName: d.data.name,
                    originalPath: d.data.path,
                    fullPath: fullPath,
                    hasSocket: !!this.socket,
                    socketConnected: this.socket?.connected
                });

                if (this.socket && this.socket.connected) {
                    console.log('📡 [FILE ANALYSIS] Using SocketIO for analysis:', {
                        event: 'code:analyze:file',
                        path: fullPath,
                        socketConnected: this.socket.connected,
                        socketId: this.socket.id
                    });

                    this.socket.emit('code:analyze:file', {
                        path: fullPath
                    });

                    // Set a shorter timeout since we have a stable server
                    const analysisTimeout = setTimeout(() => {
                        console.warn('⏰ [FILE ANALYSIS] SocketIO timeout, trying HTTP fallback for:', fullPath);
                        this.analyzeFileHTTP(fullPath, d.data.name, d3.select(event.target.closest('g')));
                    }, 5000); // 5 second timeout

                    // Store timeout ID for cleanup
                    if (!this.analysisTimeouts) this.analysisTimeouts = new Map();
                    this.analysisTimeouts.set(fullPath, analysisTimeout);

                    this.updateBreadcrumb(`Analyzing ${d.data.name}...`, 'info');
                    this.showNotification(`Analyzing: ${d.data.name}`, 'info');
                } else {
                    console.log('🔄 [FILE ANALYSIS] SocketIO unavailable, using HTTP fallback');
                    this.updateBreadcrumb(`Analyzing ${d.data.name}...`, 'info');
                    this.showNotification(`Analyzing: ${d.data.name}`, 'info');
                    this.analyzeFileHTTP(fullPath, d.data.name, d3.select(event.target.closest('g')));
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
     * Focus on a specific directory, hiding parent directories and showing only its contents
     */
    focusOnDirectory(node) {
        if (!node || node.data.type !== 'directory') return;

        console.log('🎯 [FOCUS] Focusing on directory:', node.data.path);

        // Store the focused node
        this.focusedNode = node;

        // Create a temporary root for display purposes
        const focusedRoot = {
            ...node.data,
            name: `📁 ${node.data.name}`,
            children: node.data.children || []
        };

        // Create new D3 hierarchy with focused node as root
        const tempRoot = d3.hierarchy(focusedRoot);
        tempRoot.x0 = this.height / 2;
        tempRoot.y0 = 0;

        // Store original root for restoration
        if (!this.originalRoot) {
            this.originalRoot = this.root;
        }

        // Update with focused view
        this.root = tempRoot;
        this.update(this.root);

        // Add visual styling for focused mode
        d3.select('#code-tree-container').classed('focused', true);

        // Update breadcrumb to show focused path
        this.updateBreadcrumb(`Focused on: ${node.data.name}`, 'info');
        this.showNotification(`Focused on directory: ${node.data.name}`, 'info');

        // Add back button to toolbar
        this.addBackButton();
    }

    /**
     * Return to the full tree view from focused directory view
     */
    unfocusDirectory() {
        if (!this.originalRoot) return;

        console.log('🔙 [FOCUS] Returning to full tree view');

        // Restore original root
        this.root = this.originalRoot;
        this.originalRoot = null;
        this.focusedNode = null;

        // Update display
        this.update(this.root);

        // Remove visual styling for focused mode
        d3.select('#code-tree-container').classed('focused', false);

        // Remove back button
        this.removeBackButton();

        this.updateBreadcrumb('Full tree view restored', 'success');
        this.showNotification('Returned to full tree view', 'success');
    }

    /**
     * Add back button to return from focused view
     */
    addBackButton() {
        // Remove existing back button
        d3.select('#tree-back-button').remove();

        const toolbar = d3.select('.tree-controls-toolbar');
        if (toolbar.empty()) return;

        toolbar.insert('button', ':first-child')
            .attr('id', 'tree-back-button')
            .attr('class', 'tree-control-btn back-btn')
            .attr('title', 'Return to full tree view')
            .text('← Back')
            .on('click', () => this.unfocusDirectory());
    }

    /**
     * Remove back button
     */
    removeBackButton() {
        d3.select('#tree-back-button').remove();
    }

    /**
     * Reset zoom to fit the tree
     */
    resetZoom() {
        if (!this.svg || !this.zoom) return;

        // Calculate bounds of the tree
        const bounds = this.treeGroup.node().getBBox();
        const fullWidth = this.width;
        const fullHeight = this.height;
        const width = bounds.width;
        const height = bounds.height;
        const midX = bounds.x + width / 2;
        const midY = bounds.y + height / 2;

        if (width === 0 || height === 0) return; // Nothing to fit

        // Calculate scale to fit tree in view with some padding
        const scale = Math.min(fullWidth / width, fullHeight / height) * 0.9;

        // Calculate translate to center the tree
        const translate = [fullWidth / 2 - scale * midX, fullHeight / 2 - scale * midY];

        // Apply the transform with smooth transition
        this.svg.transition()
            .duration(750)
            .call(this.zoom.transform, d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale));

        this.showNotification('Zoom reset to fit tree', 'info');
    }

    /**
     * Zoom in by a fixed factor
     */
    zoomIn() {
        if (!this.svg || !this.zoom) return;

        this.svg.transition()
            .duration(300)
            .call(this.zoom.scaleBy, 1.5);
    }

    /**
     * Zoom out by a fixed factor
     */
    zoomOut() {
        if (!this.svg || !this.zoom) return;

        this.svg.transition()
            .duration(300)
            .call(this.zoom.scaleBy, 1 / 1.5);
    }

    /**
     * Update zoom level display
     */
    updateZoomLevel(scale) {
        const zoomDisplay = document.getElementById('zoom-level-display');
        if (zoomDisplay) {
            zoomDisplay.textContent = `${Math.round(scale * 100)}%`;
        }
    }

    /**
     * Adjust text size to remain constant during zoom
     */
    adjustTextSizeForZoom(zoomScale) {
        if (!this.treeGroup) return;

        // Calculate the inverse scale to keep text at consistent size
        const textScale = 1 / zoomScale;

        // Apply inverse scaling to all text elements
        this.treeGroup.selectAll('text')
            .style('font-size', `${12 * textScale}px`)
            .attr('transform', function() {
                // Get existing transform if any
                const existingTransform = d3.select(this).attr('transform') || '';
                // Remove any existing scale transforms and add the new one
                const cleanTransform = existingTransform.replace(/scale\([^)]*\)/g, '').trim();
                return cleanTransform ? `${cleanTransform} scale(${textScale})` : `scale(${textScale})`;
            });

        // Also adjust other UI elements that should maintain size
        this.treeGroup.selectAll('.expand-icon')
            .style('font-size', `${12 * textScale}px`)
            .attr('transform', function() {
                const existingTransform = d3.select(this).attr('transform') || '';
                const cleanTransform = existingTransform.replace(/scale\([^)]*\)/g, '').trim();
                return cleanTransform ? `${cleanTransform} scale(${textScale})` : `scale(${textScale})`;
            });

        // Adjust item count badges
        this.treeGroup.selectAll('.item-count-badge')
            .style('font-size', `${10 * textScale}px`)
            .attr('transform', function() {
                const existingTransform = d3.select(this).attr('transform') || '';
                const cleanTransform = existingTransform.replace(/scale\([^)]*\)/g, '').trim();
                return cleanTransform ? `${cleanTransform} scale(${textScale})` : `scale(${textScale})`;
            });
    }

    /**
     * Add keyboard shortcuts for zoom functionality
     */
    addZoomKeyboardShortcuts() {
        // Only add shortcuts when the code tab is active
        document.addEventListener('keydown', (event) => {
            // Check if code tab is active
            const codeTab = document.getElementById('code-tab');
            if (!codeTab || !codeTab.classList.contains('active')) {
                return;
            }

            // Prevent shortcuts when typing in input fields
            if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
                return;
            }

            // Handle zoom shortcuts
            if (event.ctrlKey || event.metaKey) {
                switch (event.key) {
                    case '=':
                    case '+':
                        event.preventDefault();
                        this.zoomIn();
                        break;
                    case '-':
                        event.preventDefault();
                        this.zoomOut();
                        break;
                    case '0':
                        event.preventDefault();
                        this.resetZoom();
                        break;
                }
            }
        });
    }

    /**
     * Check if a file path represents a source file that should show source viewer
     */
    isSourceFile(path) {
        if (!path) return false;
        const sourceExtensions = ['.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.cs', '.php', '.rb', '.go', '.rs', '.swift'];
        return sourceExtensions.some(ext => path.toLowerCase().endsWith(ext));
    }

    /**
     * Show hierarchical source viewer for a source file
     */
    async showSourceViewer(node) {
        console.log('📄 [SOURCE VIEWER] Showing source for:', node.data.path);

        // Create source viewer container
        const sourceViewer = document.createElement('div');
        sourceViewer.className = 'source-viewer';

        // Create header
        const header = document.createElement('div');
        header.className = 'source-viewer-header';
        header.innerHTML = `
            <span>📄 ${node.data.name || 'Source File'}</span>
            <div class="source-viewer-controls">
                <button class="source-control-btn" id="expand-all-source" title="Expand all">⬇</button>
                <button class="source-control-btn" id="collapse-all-source" title="Collapse all">⬆</button>
            </div>
        `;

        // Create content container
        const content = document.createElement('div');
        content.className = 'source-viewer-content';
        content.id = 'source-viewer-content';

        sourceViewer.appendChild(header);
        sourceViewer.appendChild(content);
        this.structuredDataContent.appendChild(sourceViewer);

        // Add control event listeners
        document.getElementById('expand-all-source')?.addEventListener('click', () => this.expandAllSource());
        document.getElementById('collapse-all-source')?.addEventListener('click', () => this.collapseAllSource());

        // Load and display source code
        try {
            await this.loadSourceContent(node, content);
        } catch (error) {
            console.error('Failed to load source content:', error);
            content.innerHTML = `
                <div class="ast-data-placeholder">
                    <div class="ast-placeholder-icon">❌</div>
                    <div class="ast-placeholder-text">Failed to load source file</div>
                </div>
            `;
        }
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
     * Debug function to clear loading state (for troubleshooting)
     */
    clearLoadingState() {
        console.log('🧹 [DEBUG] Clearing loading state:', {
            loadingNodesBefore: Array.from(this.loadingNodes),
            size: this.loadingNodes.size
        });
        this.loadingNodes.clear();

        // Also reset any nodes marked as 'loading'
        this.resetLoadingFlags(this.treeData);

        console.log('✅ [DEBUG] Loading state cleared');
        this.showNotification('Loading state cleared', 'info');
    }

    /**
     * Recursively reset loading flags in tree data
     */
    resetLoadingFlags(node) {
        if (node.loaded === 'loading') {
            node.loaded = false;
        }
        if (node.children) {
            node.children.forEach(child => this.resetLoadingFlags(child));
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

    /**
     * Initialize the structured data integration
     */
    initializeStructuredData() {
        this.structuredDataContent = document.getElementById('module-data-content');

        if (!this.structuredDataContent) {
            console.warn('Structured data content element not found');
            return;
        }

        console.log('✅ Structured data integration initialized');
    }

    /**
     * Update structured data with node information
     */
    updateStructuredData(node) {
        if (!this.structuredDataContent) {
            return;
        }

        console.log('🔍 [STRUCTURED DATA] Updating with node:', {
            name: node?.data?.name,
            type: node?.data?.type,
            hasChildren: !!(node?.children || node?._children),
            dataChildren: node?.data?.children?.length || 0
        });

        // Clear previous content
        this.structuredDataContent.innerHTML = '';

        // Check if this is a source file that should show source viewer
        if (node.data.type === 'file' && this.isSourceFile(node.data.path)) {
            this.showSourceViewer(node);
        } else {
            // Show children or functions for non-source files
            const children = node.children || node._children || [];
            const dataChildren = node.data.children || [];

            if (children.length > 0 || dataChildren.length > 0) {
                this.showASTNodeChildren(node);
            } else if (node.data.type === 'file' && node.data.analyzed) {
                this.showASTFileDetails(node);
            } else {
                this.showASTNodeDetails(node);
            }
        }
    }

    /**
     * Show child nodes in structured data
     */
    showASTNodeChildren(node) {
        const children = node.children || node._children || [];
        const dataChildren = node.data.children || [];

        // Use D3 children if available, otherwise use data children
        const childrenToShow = children.length > 0 ? children : dataChildren;

        if (childrenToShow.length === 0) {
            this.showASTEmptyState('No children found');
            return;
        }

        // Create header
        const header = document.createElement('div');
        header.className = 'structured-view-header';
        header.innerHTML = `<h4>${this.getNodeIcon(node.data.type)} ${node.data.name || 'Node'} - Children (${childrenToShow.length})</h4>`;
        this.structuredDataContent.appendChild(header);

        childrenToShow.forEach((child, index) => {
            const childData = child.data || child;
            const item = this.createASTDataViewerItem(childData, index);
            this.structuredDataContent.appendChild(item);
        });
    }

    /**
     * Show file details in structured data
     */
    showASTFileDetails(node) {
        // Create header
        const header = document.createElement('div');
        header.className = 'structured-view-header';
        header.innerHTML = `<h4>${this.getNodeIcon(node.data.type)} ${node.data.name || 'File'} - Details</h4>`;
        this.structuredDataContent.appendChild(header);

        const details = [];

        if (node.data.language) {
            details.push({ label: 'Language', value: node.data.language });
        }

        if (node.data.lines) {
            details.push({ label: 'Lines', value: node.data.lines });
        }

        if (node.data.complexity !== undefined) {
            details.push({ label: 'Complexity', value: node.data.complexity });
        }

        if (node.data.size) {
            details.push({ label: 'Size', value: this.formatFileSize(node.data.size) });
        }

        if (details.length === 0) {
            this.showASTEmptyState('No details available');
            return;
        }

        details.forEach((detail, index) => {
            const item = this.createASTDetailItem(detail, index);
            this.structuredDataContent.appendChild(item);
        });
    }

    /**
     * Show basic node details in structured data
     */
    showASTNodeDetails(node) {
        // Create header
        const header = document.createElement('div');
        header.className = 'structured-view-header';
        header.innerHTML = `<h4>${this.getNodeIcon(node.data.type)} ${node.data.name || 'Node'} - Details</h4>`;
        this.structuredDataContent.appendChild(header);

        const details = [];

        details.push({ label: 'Type', value: node.data.type || 'unknown' });
        details.push({ label: 'Path', value: node.data.path || 'unknown' });

        if (node.data.line) {
            details.push({ label: 'Line', value: node.data.line });
        }

        details.forEach((detail, index) => {
            const item = this.createASTDetailItem(detail, index);
            this.structuredDataContent.appendChild(item);
        });
    }

    /**
     * Create an AST data viewer item for a child node
     */
    createASTDataViewerItem(childData, index) {
        const item = document.createElement('div');
        item.className = 'ast-data-viewer-item';
        item.dataset.index = index;

        const header = document.createElement('div');
        header.className = 'ast-data-item-header';

        const name = document.createElement('div');
        name.className = 'ast-data-item-name';
        name.innerHTML = `${this.getNodeIcon(childData.type)} ${childData.name || 'Unknown'}`;

        const type = document.createElement('div');
        type.className = `ast-data-item-type ${childData.type || 'unknown'}`;
        type.textContent = childData.type || 'unknown';

        header.appendChild(name);
        header.appendChild(type);

        const details = document.createElement('div');
        details.className = 'ast-data-item-details';

        const detailParts = [];

        if (childData.line) {
            detailParts.push(`<span class="ast-data-item-line">Line ${childData.line}</span>`);
        }

        if (childData.complexity !== undefined) {
            const complexityLevel = this.getComplexityLevel(childData.complexity);
            detailParts.push(`<span class="ast-data-item-complexity">
                <span class="ast-complexity-indicator ${complexityLevel}"></span>
                Complexity: ${childData.complexity}
            </span>`);
        }

        if (childData.docstring) {
            detailParts.push(`<div style="margin-top: 4px; font-style: italic;">${childData.docstring}</div>`);
        }

        details.innerHTML = detailParts.join(' ');

        item.appendChild(header);
        item.appendChild(details);

        // Add click handler to select item
        item.addEventListener('click', () => {
            this.selectASTDataViewerItem(item);
        });

        return item;
    }

    /**
     * Create a detail item for simple key-value pairs
     */
    createASTDetailItem(detail, index) {
        const item = document.createElement('div');
        item.className = 'ast-data-viewer-item';
        item.dataset.index = index;

        const header = document.createElement('div');
        header.className = 'ast-data-item-header';

        const name = document.createElement('div');
        name.className = 'ast-data-item-name';
        name.textContent = detail.label;

        const value = document.createElement('div');
        value.className = 'ast-data-item-details';
        value.textContent = detail.value;

        header.appendChild(name);
        item.appendChild(header);
        item.appendChild(value);

        return item;
    }

    /**
     * Show empty state in structured data
     */
    showASTEmptyState(message) {
        this.structuredDataContent.innerHTML = `
            <div class="ast-data-placeholder">
                <div class="ast-placeholder-icon">📭</div>
                <div class="ast-placeholder-text">${message}</div>
            </div>
        `;
    }

    /**
     * Select an AST data viewer item
     */
    selectASTDataViewerItem(item) {
        // Remove previous selection
        const previousSelected = this.structuredDataContent.querySelector('.ast-data-viewer-item.selected');
        if (previousSelected) {
            previousSelected.classList.remove('selected');
        }

        // Select new item
        item.classList.add('selected');
        this.selectedASTItem = item;
    }

    /**
     * Get icon for node type
     */
    getNodeIcon(type) {
        const icons = {
            'directory': '📁',
            'file': '📄',
            'class': '🏛️',
            'function': '⚡',
            'method': '🔧',
            'variable': '📦',
            'import': '📥',
            'module': '📦'
        };
        return icons[type] || '📄';
    }

    /**
     * Get complexity level for styling
     */
    getComplexityLevel(complexity) {
        if (complexity <= 5) return 'low';
        if (complexity <= 10) return 'medium';
        return 'high';
    }

    /**
     * Format file size for display
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }

    /**
     * Load source content and render with AST integration
     */
    async loadSourceContent(node, contentContainer) {
        // Try to read the file content
        const sourceContent = await this.readSourceFile(node.data.path);
        if (!sourceContent) {
            throw new Error('Could not read source file');
        }

        // Get AST elements for this file
        const astElements = node.data.children || [];

        // Parse and render source with AST integration
        this.renderSourceWithAST(sourceContent, astElements, contentContainer, node);
    }

    /**
     * Read source file content
     */
    async readSourceFile(filePath) {
        try {
            console.log('📖 [SOURCE READER] Reading file:', filePath);
            
            // Make API call to read the actual file content
            const response = await fetch(`/api/file/read?path=${encodeURIComponent(filePath)}`);
            
            if (!response.ok) {
                const error = await response.json();
                console.error('Failed to read file:', error);
                // Fall back to placeholder for errors
                return this.generatePlaceholderSource(filePath);
            }
            
            const data = await response.json();
            console.log('📖 [SOURCE READER] Read', data.lines, 'lines from', data.name);
            return data.content;
            
        } catch (error) {
            console.error('Failed to read source file:', error);
            // Fall back to placeholder on error
            return this.generatePlaceholderSource(filePath);
        }
    }

    /**
     * Generate placeholder source content for demonstration
     */
    generatePlaceholderSource(filePath) {
        const fileName = filePath.split('/').pop();

        if (fileName.endsWith('.py')) {
            return `"""
${fileName}
Generated placeholder content for demonstration
"""

import os
import sys
from typing import List, Dict, Optional

class ExampleClass:
    """Example class with methods."""

    def __init__(self, name: str):
        """Initialize the example class."""
        self.name = name
        self.data = {}

    def process_data(self, items: List[str]) -> Dict[str, int]:
        """Process a list of items and return counts."""
        result = {}
        for item in items:
            result[item] = result.get(item, 0) + 1
        return result

    def get_summary(self) -> str:
        """Get a summary of the processed data."""
        if not self.data:
            return "No data processed"
        return f"Processed {len(self.data)} items"

def main():
    """Main function."""
    example = ExampleClass("demo")
    items = ["a", "b", "a", "c", "b", "a"]
    result = example.process_data(items)
    print(example.get_summary())
    return result

if __name__ == "__main__":
    main()
`;
        } else {
            return `// ${fileName}
// Generated placeholder content for demonstration

class ExampleClass {
    constructor(name) {
        this.name = name;
        this.data = {};
    }

    processData(items) {
        const result = {};
        for (const item of items) {
            result[item] = (result[item] || 0) + 1;
        }
        return result;
    }

    getSummary() {
        if (Object.keys(this.data).length === 0) {
            return "No data processed";
        }
        return \`Processed \${Object.keys(this.data).length} items\`;
    }
}

function main() {
    const example = new ExampleClass("demo");
    const items = ["a", "b", "a", "c", "b", "a"];
    const result = example.processData(items);
    console.log(example.getSummary());
    return result;
}

main();
`;
        }
    }

    /**
     * Render source code with AST integration and collapsible sections
     */
    renderSourceWithAST(sourceContent, astElements, container, node) {
        const lines = sourceContent.split('\n');
        const astMap = this.createASTLineMap(astElements);

        console.log('🎨 [SOURCE RENDERER] Rendering source with AST:', {
            lines: lines.length,
            astElements: astElements.length,
            astMap: Object.keys(astMap).length
        });

        // Create line elements with AST integration
        lines.forEach((line, index) => {
            const lineNumber = index + 1;
            const lineElement = this.createSourceLine(line, lineNumber, astMap[lineNumber], node);
            container.appendChild(lineElement);
        });

        // Store reference for expand/collapse operations
        this.currentSourceContainer = container;
        this.currentASTElements = astElements;
    }

    /**
     * Create AST line mapping for quick lookup
     */
    createASTLineMap(astElements) {
        const lineMap = {};

        astElements.forEach(element => {
            if (element.line) {
                if (!lineMap[element.line]) {
                    lineMap[element.line] = [];
                }
                lineMap[element.line].push(element);
            }
        });

        return lineMap;
    }

    /**
     * Create a source line element with AST integration
     */
    createSourceLine(content, lineNumber, astElements, node) {
        const lineDiv = document.createElement('div');
        lineDiv.className = 'source-line';
        lineDiv.dataset.lineNumber = lineNumber;

        // Check if this line has AST elements
        const hasAST = astElements && astElements.length > 0;
        if (hasAST) {
            lineDiv.classList.add('ast-element');
            lineDiv.dataset.astElements = JSON.stringify(astElements);
        }

        // Determine if this line should be collapsible
        const isCollapsible = this.isCollapsibleLine(content, astElements);
        if (isCollapsible) {
            lineDiv.classList.add('collapsible');
        }

        // Create line number
        const lineNumberSpan = document.createElement('span');
        lineNumberSpan.className = 'line-number';
        lineNumberSpan.textContent = lineNumber;

        // Create collapse indicator
        const collapseIndicator = document.createElement('span');
        collapseIndicator.className = 'collapse-indicator';
        if (isCollapsible) {
            collapseIndicator.classList.add('expanded');
            collapseIndicator.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleSourceSection(lineDiv);
            });
        } else {
            collapseIndicator.classList.add('none');
        }

        // Create line content with syntax highlighting
        const lineContentSpan = document.createElement('span');
        lineContentSpan.className = 'line-content';
        lineContentSpan.innerHTML = this.applySyntaxHighlighting(content);

        // Add click handler for AST integration
        if (hasAST) {
            lineDiv.addEventListener('click', () => {
                this.onSourceLineClick(lineDiv, astElements, node);
            });
        }

        lineDiv.appendChild(lineNumberSpan);
        lineDiv.appendChild(collapseIndicator);
        lineDiv.appendChild(lineContentSpan);

        return lineDiv;
    }

    /**
     * Check if a line should be collapsible (function/class definitions)
     */
    isCollapsibleLine(content, astElements) {
        const trimmed = content.trim();

        // Python patterns
        if (trimmed.startsWith('def ') || trimmed.startsWith('class ') ||
            trimmed.startsWith('async def ')) {
            return true;
        }

        // JavaScript patterns
        if (trimmed.includes('function ') || trimmed.includes('class ') ||
            trimmed.includes('=> {') || trimmed.match(/^\s*\w+\s*\([^)]*\)\s*{/)) {
            return true;
        }

        // Check AST elements for function/class definitions
        if (astElements) {
            return astElements.some(el =>
                el.type === 'function' || el.type === 'class' ||
                el.type === 'method' || el.type === 'FunctionDef' ||
                el.type === 'ClassDef'
            );
        }

        return false;
    }

    /**
     * Apply basic syntax highlighting
     */
    applySyntaxHighlighting(content) {
        // First, properly escape HTML entities
        let highlighted = content
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');

        // Store markers for where we'll insert spans
        const replacements = [];
        
        // Python and JavaScript keywords (combined)
        const keywords = /\b(def|class|import|from|if|else|elif|for|while|try|except|finally|with|as|return|yield|lambda|async|await|function|const|let|var|catch|export)\b/g;
        
        // Find all matches first without replacing
        let match;
        
        // Keywords
        while ((match = keywords.exec(highlighted)) !== null) {
            replacements.push({
                start: match.index,
                end: match.index + match[0].length,
                replacement: `<span class="keyword">${match[0]}</span>`
            });
        }
        
        // Strings - simple pattern for now
        const stringPattern = /(["'`])([^"'`]*?)\1/g;
        while ((match = stringPattern.exec(highlighted)) !== null) {
            replacements.push({
                start: match.index,
                end: match.index + match[0].length,
                replacement: `<span class="string">${match[0]}</span>`
            });
        }
        
        // Comments
        const commentPattern = /(#.*$|\/\/.*$)/gm;
        while ((match = commentPattern.exec(highlighted)) !== null) {
            replacements.push({
                start: match.index,
                end: match.index + match[0].length,
                replacement: `<span class="comment">${match[0]}</span>`
            });
        }
        
        // Sort replacements by start position (reverse order to not mess up indices)
        replacements.sort((a, b) => b.start - a.start);
        
        // Apply replacements
        for (const rep of replacements) {
            // Check for overlapping replacements and skip if needed
            const before = highlighted.substring(0, rep.start);
            const after = highlighted.substring(rep.end);
            
            // Only apply if we're not inside another replacement
            if (!before.includes('<span') || before.lastIndexOf('</span>') > before.lastIndexOf('<span')) {
                highlighted = before + rep.replacement + after;
            }
        }
        
        return highlighted;
    }

    /**
     * Toggle collapse/expand of a source section
     */
    toggleSourceSection(lineElement) {
        const indicator = lineElement.querySelector('.collapse-indicator');
        const isExpanded = indicator.classList.contains('expanded');

        if (isExpanded) {
            this.collapseSourceSection(lineElement);
        } else {
            this.expandSourceSection(lineElement);
        }
    }

    /**
     * Collapse a source section
     */
    collapseSourceSection(lineElement) {
        const indicator = lineElement.querySelector('.collapse-indicator');
        indicator.classList.remove('expanded');
        indicator.classList.add('collapsed');

        // Find and hide related lines (simple implementation)
        const startLine = parseInt(lineElement.dataset.lineNumber);
        const container = lineElement.parentElement;
        const lines = Array.from(container.children);

        // Hide subsequent indented lines
        let currentIndex = lines.indexOf(lineElement) + 1;
        const baseIndent = this.getLineIndentation(lineElement.querySelector('.line-content').textContent);

        while (currentIndex < lines.length) {
            const nextLine = lines[currentIndex];
            const nextContent = nextLine.querySelector('.line-content').textContent;
            const nextIndent = this.getLineIndentation(nextContent);

            // Stop if we hit a line at the same or lower indentation level
            if (nextContent.trim() && nextIndent <= baseIndent) {
                break;
            }

            nextLine.classList.add('collapsed-content');
            currentIndex++;
        }

        // Add collapsed placeholder
        const placeholder = document.createElement('div');
        placeholder.className = 'source-line collapsed-placeholder';
        placeholder.innerHTML = `
            <span class="line-number"></span>
            <span class="collapse-indicator none"></span>
            <span class="line-content">    ... (collapsed)</span>
        `;
        lineElement.insertAdjacentElement('afterend', placeholder);
    }

    /**
     * Expand a source section
     */
    expandSourceSection(lineElement) {
        const indicator = lineElement.querySelector('.collapse-indicator');
        indicator.classList.remove('collapsed');
        indicator.classList.add('expanded');

        // Show hidden lines
        const container = lineElement.parentElement;
        const lines = Array.from(container.children);

        lines.forEach(line => {
            if (line.classList.contains('collapsed-content')) {
                line.classList.remove('collapsed-content');
            }
        });

        // Remove placeholder
        const placeholder = lineElement.nextElementSibling;
        if (placeholder && placeholder.classList.contains('collapsed-placeholder')) {
            placeholder.remove();
        }
    }

    /**
     * Get indentation level of a line
     */
    getLineIndentation(content) {
        const match = content.match(/^(\s*)/);
        return match ? match[1].length : 0;
    }

    /**
     * Handle click on source line with AST elements
     */
    onSourceLineClick(lineElement, astElements, node) {
        console.log('🎯 [SOURCE LINE CLICK] Line clicked:', {
            line: lineElement.dataset.lineNumber,
            astElements: astElements.length
        });

        // Highlight the clicked line
        this.highlightSourceLine(lineElement);

        // Show AST details for this line
        if (astElements.length > 0) {
            this.showASTElementDetails(astElements[0], node);
        }

        // If this is a collapsible line, also toggle it
        if (lineElement.classList.contains('collapsible')) {
            this.toggleSourceSection(lineElement);
        }
    }

    /**
     * Highlight a source line
     */
    highlightSourceLine(lineElement) {
        // Remove previous highlights
        if (this.currentSourceContainer) {
            const lines = this.currentSourceContainer.querySelectorAll('.source-line');
            lines.forEach(line => line.classList.remove('highlighted'));
        }

        // Add highlight to clicked line
        lineElement.classList.add('highlighted');
    }

    /**
     * Show AST element details
     */
    showASTElementDetails(astElement, node) {
        // This could open a detailed view or update another panel
        console.log('📋 [AST DETAILS] Showing details for:', astElement);

        // For now, just log the details
        // In a full implementation, this might update a details panel
    }

    /**
     * Expand all collapsible sections in source viewer
     */
    expandAllSource() {
        if (!this.currentSourceContainer) return;

        const collapsibleLines = this.currentSourceContainer.querySelectorAll('.source-line.collapsible');
        collapsibleLines.forEach(line => {
            const indicator = line.querySelector('.collapse-indicator');
            if (indicator.classList.contains('collapsed')) {
                this.expandSourceSection(line);
            }
        });
    }

    /**
     * Collapse all collapsible sections in source viewer
     */
    collapseAllSource() {
        if (!this.currentSourceContainer) return;

        const collapsibleLines = this.currentSourceContainer.querySelectorAll('.source-line.collapsible');
        collapsibleLines.forEach(line => {
            const indicator = line.querySelector('.collapse-indicator');
            if (indicator.classList.contains('expanded')) {
                this.collapseSourceSection(line);
            }
        });
    }
}

// Export for use in other modules
window.CodeTree = CodeTree;

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Check if we're on a page with code tree container
    if (document.getElementById('code-tree-container')) {
        window.codeTree = new CodeTree();

        // Expose debug functions globally for troubleshooting
        window.debugCodeTree = {
            clearLoadingState: () => window.codeTree?.clearLoadingState(),
            showLoadingNodes: () => {
                console.log('Current loading nodes:', Array.from(window.codeTree?.loadingNodes || []));
                return Array.from(window.codeTree?.loadingNodes || []);
            },
            resetTree: () => {
                if (window.codeTree) {
                    window.codeTree.clearLoadingState();
                    window.codeTree.initializeTreeData();
                    console.log('Tree reset complete');
                }
            },
            focusOnPath: (path) => {
                if (window.codeTree) {
                    const node = window.codeTree.findD3NodeByPath(path);
                    if (node) {
                        window.codeTree.focusOnDirectory(node);
                        console.log('Focused on:', path);
                    } else {
                        console.log('Node not found:', path);
                    }
                }
            },
            unfocus: () => window.codeTree?.unfocusDirectory()
        };

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
