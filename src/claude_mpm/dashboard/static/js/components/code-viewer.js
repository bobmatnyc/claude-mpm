/**
 * Code Viewer Component - File Activity Tree Viewer
 * 
 * Shows a D3.js tree visualization of files that have been viewed or edited,
 * including AST paths (classes, functions, methods) extracted from the files.
 * This is NOT a directory viewer but an activity-focused visualization.
 * Renders in the File Tree tab of the dashboard.
 */

class CodeViewer {
    constructor() {
        this.container = null;
        this.svg = null;
        this.initialized = false;
        this.fileActivity = new Map(); // Map of file path to activity data
        this.sessions = new Map();
        this.currentSession = null;
        this.treeData = null;
        this.d3Tree = null;
        this.d3Root = null;
        this.selectedNode = null;
        this.width = 800;
        this.height = 600;
        this.nodeRadius = 5;
        this.renderInProgress = false; // Prevent concurrent renders
        this.containerObserver = null;
    }

    /**
     * Initialize the code viewer
     */
    initialize() {
        if (this.initialized) {
            console.log('[CodeViewer] Already initialized, skipping');
            return;
        }

        console.log('[CodeViewer] Initializing...');
        this.setupContainer();
        this.setupEventHandlers();
        this.subscribeToEvents();
        this.processExistingEvents();
        
        this.initialized = true;
        console.log('[CodeViewer] Code Viewer (File Activity Tree) initialized successfully');
    }

    /**
     * Setup the container in the File Tree tab
     */
    setupContainer() {
        // Find the File Tree tab container
        const treeContainer = document.getElementById('claude-tree-container');
        if (!treeContainer) {
            console.error('File Tree container not found');
            return;
        }

        // Store the container reference
        this.container = treeContainer;
        
        // Setup the activity tree interface
        this.renderInterface();
    }

    /**
     * Render the activity tree interface in the File Tree tab
     */
    renderInterface() {
        if (!this.container) {
            console.error('[CodeViewer] Container not found, cannot render interface');
            return;
        }

        // Prevent concurrent renders
        if (this.renderInProgress) {
            console.log('[CodeViewer] Render already in progress, skipping');
            return;
        }
        
        // Check if interface already exists and is intact
        const existingWrapper = this.container.querySelector('.activity-tree-wrapper');
        const existingSvg = this.container.querySelector('#claude-activity-tree-svg');
        if (existingWrapper && existingSvg) {
            console.log('[CodeViewer] Interface already exists and is intact, skipping render');
            return;
        }
        
        this.renderInProgress = true;
        console.log('[CodeViewer] Rendering interface in container:', this.container.id);
        
        // Temporarily disconnect observer to prevent loops
        if (this.containerObserver) {
            this.containerObserver.disconnect();
        }
        
        // Clear any existing content completely
        this.container.innerHTML = '';
        
        // Create the activity tree interface (without redundant session selector)
        this.container.innerHTML = `
            <div class="activity-tree-wrapper" style="height: 100%; display: flex; flex-direction: column;">
                <div class="activity-controls" style="padding: 10px; border-bottom: 1px solid #ddd; background: #f9f9f9; display: flex; align-items: center; gap: 10px;">
                    <button id="claude-expand-all-btn" class="control-btn" style="padding: 4px 8px; font-size: 0.9em;">Expand All</button>
                    <button id="claude-collapse-all-btn" class="control-btn" style="padding: 4px 8px; font-size: 0.9em;">Collapse All</button>
                    <button id="claude-reset-zoom-btn" class="control-btn" style="padding: 4px 8px; font-size: 0.9em;">Reset Zoom</button>
                    <div class="stats" id="claude-tree-stats" style="margin-left: auto; font-size: 0.9em; color: #666;"></div>
                </div>
                <div class="tree-container" id="claude-tree-svg-container" style="flex: 1; overflow: hidden; position: relative; background: white;">
                    <svg id="claude-activity-tree-svg" style="width: 100%; height: 100%;"></svg>
                </div>
                <div class="legend" style="padding: 5px 10px; border-top: 1px solid #ddd; background: #f9f9f9; font-size: 0.85em; display: flex; gap: 15px;">
                    <span class="legend-item"><span style="color: #4CAF50;">●</span> File</span>
                    <span class="legend-item"><span style="color: #2196F3;">●</span> Class</span>
                    <span class="legend-item"><span style="color: #FF9800;">●</span> Function</span>
                    <span class="legend-item"><span style="color: #9C27B0;">●</span> Method</span>
                    <span class="legend-item"><span style="color: #F44336;">◆</span> Edited</span>
                    <span class="legend-item"><span style="color: #4CAF50;">○</span> Viewed</span>
                </div>
            </div>
        `;

        // Get container dimensions for tree sizing
        const svgContainer = document.getElementById('claude-tree-svg-container');
        if (svgContainer) {
            const rect = svgContainer.getBoundingClientRect();
            this.width = rect.width || 800;
            this.height = rect.height || 600;
        }
        
        // Mark render as complete and re-enable observer if needed
        this.renderInProgress = false;
        
        // Re-enable container protection after render
        if (this.containerObserver && this.container) {
            this.containerObserver.observe(this.container, {
                childList: true,
                subtree: false // Only watch direct children, not subtree
            });
        }
    }

    /**
     * Render the content without switching tabs
     * This is called by UIStateManager when the tab is already active
     */
    renderContent() {
        console.log('[CodeViewer] renderContent() called');
        this._showInternal();
    }
    
    /**
     * Show the activity tree (for backward compatibility)
     * Note: Tab switching is now handled by UIStateManager
     */
    show() {
        console.log('[CodeViewer] show() called');
        this._showInternal();
    }
    
    /**
     * Internal show implementation (without tab switching)
     */
    _showInternal() {

        // Get the file tree container
        const claudeTreeContainer = document.getElementById('claude-tree-container');
        if (!claudeTreeContainer) {
            console.error('[CodeViewer] File Tree container not found!');
            return;
        }

        // CRITICAL: Prevent other components from writing to this container
        // Add multiple attributes to mark ownership strongly
        claudeTreeContainer.setAttribute('data-owner', 'code-viewer');
        claudeTreeContainer.setAttribute('data-tab-reserved', 'claude-tree');
        claudeTreeContainer.setAttribute('data-component', 'CodeViewer');
        
        // Store the container reference if not already set
        if (!this.container || this.container !== claudeTreeContainer) {
            this.container = claudeTreeContainer;
        }
        
        // Initialize if needed (this will setup container and render interface)
        if (!this.initialized) {
            this.initialize();
        } else {
            // Only render interface if it doesn't exist
            const existingWrapper = this.container.querySelector('.activity-tree-wrapper');
            if (!existingWrapper) {
                console.log('[CodeViewer] Interface missing, rendering...');
                this.renderInterface();
            }
        }
        
        // Set up mutation observer to protect container (only if not already set)
        if (!this.containerObserver) {
            this.protectContainer();
        }

        // Setup event handlers for the new controls
        this.setupControlHandlers();
        
        // Get current session from main selector
        const mainSessionSelect = document.getElementById('session-select');
        if (mainSessionSelect) {
            this.currentSession = mainSessionSelect.value || null;
        }
        
        // Build and render tree
        this.buildTreeData();
        this.renderTree();
        
        // Update stats
        this.updateStats();
        
        console.log('[CodeViewer] show() completed, container should now have tree interface');
    }

    /**
     * Protect the container from being overwritten by other components
     */
    protectContainer() {
        const container = document.getElementById('claude-tree-container');
        if (!container) return;
        
        // Disconnect any existing observer
        if (this.containerObserver) {
            this.containerObserver.disconnect();
        }
        
        // Flag to prevent re-render loops
        let reRenderScheduled = false;
        
        // Create a new observer to watch for unwanted changes
        this.containerObserver = new MutationObserver((mutations) => {
            for (const mutation of mutations) {
                // Check if nodes were added that shouldn't be there
                for (const node of mutation.addedNodes) {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        const element = node;
                        
                        // AGGRESSIVE filtering: Block ANY content that's not our tree interface
                        const isUnwantedContent = (
                            element.classList?.contains('event-item') ||
                            element.classList?.contains('events-list') ||
                            element.classList?.contains('no-events') ||
                            element.id === 'events-list' ||
                            (element.textContent && (
                                element.textContent.includes('[hook]') ||
                                element.textContent.includes('hook.user_prompt') ||
                                element.textContent.includes('hook.pre_tool') ||
                                element.textContent.includes('hook.post_tool') ||
                                element.textContent.includes('Connect to Socket.IO') ||
                                element.textContent.includes('No events')
                            )) ||
                            // Block any div without our expected classes
                            (element.tagName === 'DIV' && 
                             !element.classList?.contains('activity-tree-wrapper') &&
                             !element.classList?.contains('activity-controls') &&
                             !element.classList?.contains('tree-container') &&
                             !element.classList?.contains('legend') &&
                             !element.id?.startsWith('claude-'))
                        );
                        
                        if (isUnwantedContent) {
                            console.warn('[CodeViewer] BLOCKED unwanted content in File Tree container:', element);
                            console.warn('[CodeViewer] Element classes:', element.classList?.toString());
                            console.warn('[CodeViewer] Element text preview:', element.textContent?.substring(0, 100));
                            
                            // Remove the unwanted content immediately
                            try {
                                node.remove();
                            } catch (e) {
                                console.warn('[CodeViewer] Failed to remove unwanted node:', e);
                            }
                            
                            // Schedule a single re-render if needed
                            if (!reRenderScheduled && !this.renderInProgress) {
                                reRenderScheduled = true;
                                setTimeout(() => {
                                    reRenderScheduled = false;
                                    if (!container.querySelector('.activity-tree-wrapper')) {
                                        console.log('[CodeViewer] Re-rendering interface after blocking unwanted content');
                                        this.renderInterface();
                                        this.setupControlHandlers();
                                        this.buildTreeData();
                                        this.renderTree();
                                    }
                                }, 50);
                            }
                        }
                    }
                }
                
                // Also check if our content was removed
                if (mutation.type === 'childList' && mutation.removedNodes.length > 0) {
                    for (const node of mutation.removedNodes) {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            const element = node;
                            if (element.classList?.contains('activity-tree-wrapper')) {
                                console.warn('[CodeViewer] Our tree interface was removed! Re-rendering...');
                                if (!reRenderScheduled && !this.renderInProgress) {
                                    reRenderScheduled = true;
                                    setTimeout(() => {
                                        reRenderScheduled = false;
                                        this.renderInterface();
                                        this.setupControlHandlers();
                                        this.buildTreeData();
                                        this.renderTree();
                                    }, 50);
                                }
                            }
                        }
                    }
                }
            }
        });
        
        // Start observing only direct children to reduce overhead
        this.containerObserver.observe(container, {
            childList: true,
            subtree: false // Only watch direct children, not entire subtree
        });
        
        console.log('[CodeViewer] Container protection enabled with aggressive filtering');
    }

    /**
     * Setup event handlers for controls
     */
    setupControlHandlers() {
        // Listen to main session selector changes
        const mainSessionSelect = document.getElementById('session-select');
        if (mainSessionSelect && !mainSessionSelect.hasAttribute('data-tree-listener')) {
            mainSessionSelect.setAttribute('data-tree-listener', 'true');
            mainSessionSelect.addEventListener('change', (e) => {
                this.currentSession = e.target.value || null;
                console.log('[CodeViewer] Session changed to:', this.currentSession);
                if (this.isTabActive()) {
                    this.buildTreeData();
                    this.renderTree();
                    this.updateStats();
                }
            });
        }

        // Expand all button
        const expandBtn = document.getElementById('claude-expand-all-btn');
        if (expandBtn && !expandBtn.hasAttribute('data-listener')) {
            expandBtn.setAttribute('data-listener', 'true');
            expandBtn.addEventListener('click', () => {
                this.expandAllNodes();
            });
        }

        // Collapse all button
        const collapseBtn = document.getElementById('claude-collapse-all-btn');
        if (collapseBtn && !collapseBtn.hasAttribute('data-listener')) {
            collapseBtn.setAttribute('data-listener', 'true');
            collapseBtn.addEventListener('click', () => {
                this.collapseAllNodes();
            });
        }

        // Reset zoom button
        const resetBtn = document.getElementById('claude-reset-zoom-btn');
        if (resetBtn && !resetBtn.hasAttribute('data-listener')) {
            resetBtn.setAttribute('data-listener', 'true');
            resetBtn.addEventListener('click', () => {
                this.resetZoom();
            });
        }
    }

    /**
     * Setup event handlers
     */
    setupEventHandlers() {
        // Tab handling is done in show() method
    }

    /**
     * Subscribe to events from socket and event bus
     */
    subscribeToEvents() {
        // Listen for claude events from socket
        if (window.socket) {
            window.socket.on('claude_event', (event) => {
                console.log('[CodeViewer] Received claude_event:', event);
                if (this.isFileOperationEvent(event)) {
                    this.processClaudeEvent(event);
                    // Only update if the File Tree tab is active
                    if (this.isTabActive()) {
                        this.buildTreeData();
                        this.renderTree();
                        this.updateStats();
                    }
                }
            });
        }

        // Listen for events from event bus
        if (window.eventBus) {
            window.eventBus.on('claude_event', (event) => {
                console.log('[CodeViewer] Received claude_event from eventBus:', event);
                if (this.isFileOperationEvent(event)) {
                    this.processClaudeEvent(event);
                    // Only update if the File Tree tab is active
                    if (this.isTabActive()) {
                        this.buildTreeData();
                        this.renderTree();
                        this.updateStats();
                    }
                }
            });
        }
    }

    /**
     * Check if File Tree tab is active
     */
    isTabActive() {
        const claudeTreeContent = document.getElementById('claude-tree-tab');
        return claudeTreeContent && claudeTreeContent.classList.contains('active');
    }

    /**
     * Process existing events from dashboard
     */
    processExistingEvents() {
        if (window.dashboard && window.dashboard.eventStore) {
            const events = window.dashboard.eventStore.getAllEvents();
            events.forEach(event => {
                if (this.isFileOperationEvent(event)) {
                    this.processClaudeEvent(event);
                }
            });
        }
    }

    /**
     * Check if an event is a file operation event
     */
    isFileOperationEvent(event) {
        // Check if this is a hook event with file operation tool
        if (event.type === 'hook' && 
            (event.subtype === 'pre_tool' || event.subtype === 'post_tool') &&
            event.data && event.data.tool_name) {
            const fileOps = ['Read', 'Write', 'Edit', 'MultiEdit', 'NotebookEdit'];
            return fileOps.includes(event.data.tool_name);
        }
        return false;
    }

    /**
     * Check if an event is a file operation (legacy format)
     */
    isFileOperation(event) {
        const fileOps = ['Read', 'Write', 'Edit', 'MultiEdit', 'NotebookEdit'];
        return fileOps.includes(event.tool_name);
    }

    /**
     * Process a claude event with file operation
     */
    processClaudeEvent(event) {
        if (!this.isFileOperationEvent(event)) return;

        // Extract data from claude_event structure
        const data = event.data || {};
        const tool_name = data.tool_name;
        const tool_parameters = data.tool_parameters || {};
        const tool_output = data.tool_output;
        const timestamp = event.timestamp || new Date().toISOString();
        const session_id = event.session_id || data.session_id;
        const working_directory = data.working_directory || '/';
        
        const filePath = tool_parameters.file_path || tool_parameters.notebook_path;
        
        console.log('[CodeViewer] Processing file operation:', tool_name, filePath);
        
        this.processFileOperation({
            tool_name,
            tool_parameters,
            tool_output,
            timestamp,
            session_id,
            working_directory,
            filePath
        });
    }

    /**
     * Process a file operation event (legacy format)
     */
    processEvent(event) {
        if (!this.isFileOperation(event)) return;

        const { tool_name, tool_parameters, tool_output, timestamp, session_id, working_directory } = event;
        const filePath = tool_parameters?.file_path || tool_parameters?.notebook_path;
        
        this.processFileOperation({
            tool_name,
            tool_parameters,
            tool_output,
            timestamp,
            session_id,
            working_directory,
            filePath
        });
    }

    /**
     * Process a file operation
     */
    processFileOperation({ tool_name, tool_parameters, tool_output, timestamp, session_id, working_directory, filePath }) {
        if (!filePath) return;

        // Track session
        if (session_id && !this.sessions.has(session_id)) {
            this.sessions.set(session_id, {
                id: session_id,
                working_directory: working_directory || '/',
                files: new Set()
            });
            // Update session list when new session is added
            this.updateSessionList();
        }

        // Get or create file activity
        if (!this.fileActivity.has(filePath)) {
            this.fileActivity.set(filePath, {
                path: filePath,
                operations: [],
                sessions: new Set(),
                working_directories: new Set(),
                lastContent: null,
                astPaths: []
            });
        }

        const activity = this.fileActivity.get(filePath);
        
        // Add operation
        activity.operations.push({
            type: tool_name,
            timestamp: timestamp,
            parameters: tool_parameters,
            output: tool_output,
            session_id: session_id
        });

        // Track session and working directory
        if (session_id) {
            activity.sessions.add(session_id);
            const session = this.sessions.get(session_id);
            if (session) {
                session.files.add(filePath);
            }
        }
        if (working_directory) {
            activity.working_directories.add(working_directory);
        }

        // Update content and extract AST if applicable
        if (tool_name === 'Write' && tool_parameters.content) {
            activity.lastContent = tool_parameters.content;
            activity.astPaths = this.extractASTPaths(tool_parameters.content, filePath);
        } else if (tool_name === 'Read' && tool_output?.content) {
            activity.lastContent = tool_output.content;
            activity.astPaths = this.extractASTPaths(tool_output.content, filePath);
        } else if (tool_name === 'Edit' && activity.lastContent) {
            // Apply edit to content if we have it
            const oldString = tool_parameters.old_string;
            const newString = tool_parameters.new_string;
            if (oldString && newString) {
                activity.lastContent = activity.lastContent.replace(oldString, newString);
                activity.astPaths = this.extractASTPaths(activity.lastContent, filePath);
            }
        }
        
        console.log('[CodeViewer] File activity updated:', filePath, 'Total files:', this.fileActivity.size)
    }

    /**
     * Extract AST paths from code content
     */
    extractASTPaths(content, filePath) {
        if (!content || typeof content !== 'string') return [];
        
        const ext = filePath.split('.').pop()?.toLowerCase();
        const paths = [];

        if (ext === 'py') {
            // Python: Extract classes, functions, and methods
            const classRegex = /^class\s+(\w+)/gm;
            const functionRegex = /^def\s+(\w+)/gm;
            const methodRegex = /^\s{4,}def\s+(\w+)/gm;

            let match;
            while ((match = classRegex.exec(content)) !== null) {
                paths.push({ name: match[1], type: 'class' });
            }
            while ((match = functionRegex.exec(content)) !== null) {
                paths.push({ name: match[1], type: 'function' });
            }
            while ((match = methodRegex.exec(content)) !== null) {
                if (!paths.some(p => p.name === match[1])) {
                    paths.push({ name: match[1], type: 'method' });
                }
            }
        } else if (ext === 'js' || ext === 'jsx' || ext === 'ts' || ext === 'tsx') {
            // JavaScript/TypeScript: Extract classes, functions, methods
            const classRegex = /class\s+(\w+)/g;
            const functionRegex = /function\s+(\w+)/g;
            const arrowFunctionRegex = /const\s+(\w+)\s*=\s*\([^)]*\)\s*=>/g;
            const methodRegex = /(\w+)\s*\([^)]*\)\s*\{/g;

            let match;
            while ((match = classRegex.exec(content)) !== null) {
                paths.push({ name: match[1], type: 'class' });
            }
            while ((match = functionRegex.exec(content)) !== null) {
                paths.push({ name: match[1], type: 'function' });
            }
            while ((match = arrowFunctionRegex.exec(content)) !== null) {
                paths.push({ name: match[1], type: 'function' });
            }
        }

        return paths;
    }

    /**
     * Build tree data from file activity
     */
    buildTreeData() {
        const root = {
            name: 'File Activity',
            type: 'root',
            children: []
        };

        // Group by working directory
        const dirMap = new Map();

        for (const [filePath, activity] of this.fileActivity.entries()) {
            // Filter by session if selected
            if (this.currentSession) {
                if (!activity.sessions.has(this.currentSession)) {
                    continue;
                }
            }

            // Determine working directory
            const workingDirs = Array.from(activity.working_directories);
            const workingDir = workingDirs[0] || '/';

            if (!dirMap.has(workingDir)) {
                dirMap.set(workingDir, {
                    name: workingDir.split('/').pop() || workingDir,
                    path: workingDir,
                    type: 'directory',
                    children: []
                });
            }

            // Create file node
            const fileName = filePath.split('/').pop();
            const hasEdits = activity.operations.some(op => op.type === 'Edit' || op.type === 'Write');
            
            const fileNode = {
                name: fileName,
                path: filePath,
                type: 'file',
                edited: hasEdits,
                operations: activity.operations.length,
                children: []
            };

            // Add AST nodes
            if (activity.astPaths.length > 0) {
                activity.astPaths.forEach(ast => {
                    fileNode.children.push({
                        name: ast.name,
                        type: ast.type,
                        path: `${filePath}#${ast.name}`,
                        children: []
                    });
                });
            }

            dirMap.get(workingDir).children.push(fileNode);
        }

        // Add directories to root
        root.children = Array.from(dirMap.values());
        
        // If only one directory and it's the root, flatten
        if (root.children.length === 1 && root.children[0].path === '/') {
            root.children = root.children[0].children;
        }

        this.treeData = root;
    }

    /**
     * Render the D3 tree
     */
    renderTree() {
        if (!this.treeData || !this.container) return;

        // Ensure SVG element exists
        const svgElement = document.getElementById('claude-activity-tree-svg');
        if (!svgElement) {
            console.warn('[CodeViewer] SVG element not found, skipping tree render');
            return;
        }
        
        const svg = d3.select(svgElement);
        if (svg.empty()) {
            console.warn('[CodeViewer] D3 could not select SVG element');
            return;
        }
        
        svg.selectAll('*').remove();

        // Get actual dimensions
        const svgContainer = document.getElementById('claude-tree-svg-container');
        if (svgContainer) {
            const rect = svgContainer.getBoundingClientRect();
            this.width = rect.width || 800;
            this.height = rect.height || 600;
        }

        // Create container group for zoom/pan
        const g = svg.append('g');

        // Setup zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on('zoom', (event) => {
                g.attr('transform', event.transform);
            });

        svg.call(zoom);

        // Create tree layout
        const treeLayout = d3.tree()
            .size([this.height - 100, this.width - 200]);

        // Create hierarchy
        this.d3Root = d3.hierarchy(this.treeData);
        
        // Apply tree layout
        treeLayout(this.d3Root);

        // Create links
        const link = g.selectAll('.link')
            .data(this.d3Root.links())
            .enter().append('path')
            .attr('class', 'link')
            .attr('d', d3.linkHorizontal()
                .x(d => d.y + 100)
                .y(d => d.x + 50))
            .style('fill', 'none')
            .style('stroke', '#ccc')
            .style('stroke-width', 1);

        // Create nodes
        const node = g.selectAll('.node')
            .data(this.d3Root.descendants())
            .enter().append('g')
            .attr('class', 'node')
            .attr('transform', d => `translate(${d.y + 100},${d.x + 50})`);

        // Add circles for nodes
        node.append('circle')
            .attr('r', this.nodeRadius)
            .style('fill', d => this.getNodeColor(d.data))
            .style('stroke', d => d.data.edited ? '#F44336' : '#999')
            .style('stroke-width', d => d.data.edited ? 2 : 1)
            .style('cursor', 'pointer')
            .on('click', (event, d) => this.handleNodeClick(event, d));

        // Add text labels
        node.append('text')
            .attr('dy', '.35em')
            .attr('x', d => d.children ? -10 : 10)
            .style('text-anchor', d => d.children ? 'end' : 'start')
            .style('font-size', '12px')
            .style('cursor', 'pointer')
            .text(d => d.data.name)
            .on('click', (event, d) => this.handleNodeClick(event, d));

        // Store tree reference
        this.d3Tree = { svg, g, zoom };
    }

    /**
     * Get node color based on type
     */
    getNodeColor(node) {
        switch (node.type) {
            case 'root': return '#666';
            case 'directory': return '#FFC107';
            case 'file': return '#4CAF50';
            case 'class': return '#2196F3';
            case 'function': return '#FF9800';
            case 'method': return '#9C27B0';
            default: return '#999';
        }
    }

    /**
     * Handle node click
     */
    handleNodeClick(event, d) {
        event.stopPropagation();
        
        // Toggle children
        if (d.children) {
            d._children = d.children;
            d.children = null;
        } else if (d._children) {
            d.children = d._children;
            d._children = null;
        }

        // Re-render tree
        this.renderTree();

        // Update selection
        this.selectedNode = d;
        
        // Update the data viewer in the left pane if it's a file
        if (d.data.type === 'file' && this.fileActivity.has(d.data.path)) {
            this.showFileDetails(d.data.path);
        }
    }

    /**
     * Show file details in the left viewer pane
     */
    showFileDetails(filePath) {
        const activity = this.fileActivity.get(filePath);
        if (!activity) return;

        const dataContent = document.getElementById('module-data-content');
        if (!dataContent) return;

        // Update header
        const dataHeader = document.querySelector('.module-data-header h5');
        if (dataHeader) {
            dataHeader.innerHTML = `📄 ${filePath.split('/').pop()}`;
        }

        // Build operations display
        let html = '<div style="padding: 10px; overflow-y: auto; height: 100%;">';
        html += `<div style="margin-bottom: 15px;">`;
        html += `<strong>File Path:</strong> ${filePath}<br>`;
        html += `<strong>Operations:</strong> ${activity.operations.length}<br>`;
        html += `<strong>Sessions:</strong> ${activity.sessions.size}`;
        html += `</div>`;

        // Show operations timeline
        html += '<div style="margin-bottom: 15px;"><strong>Operations Timeline:</strong></div>';
        activity.operations.forEach((op, index) => {
            const time = new Date(op.timestamp).toLocaleTimeString();
            html += `<div style="margin-bottom: 10px; padding: 8px; background: #f5f5f5; border-left: 3px solid ${this.getOperationColor(op.type)};">`;
            html += `<div><strong>${op.type}</strong> at ${time}</div>`;
            
            if (op.type === 'Edit' && op.parameters) {
                html += `<div style="margin-top: 5px; font-size: 0.9em;">`;
                html += `<div style="color: #d32f2f;">- ${this.escapeHtml(op.parameters.old_string || '').substring(0, 100)}</div>`;
                html += `<div style="color: #388e3c;">+ ${this.escapeHtml(op.parameters.new_string || '').substring(0, 100)}</div>`;
                html += `</div>`;
            }
            html += `</div>`;
        });

        // Show AST structure if available
        if (activity.astPaths.length > 0) {
            html += '<div style="margin-top: 15px;"><strong>AST Structure:</strong></div>';
            html += '<ul style="list-style: none; padding-left: 10px;">';
            activity.astPaths.forEach(ast => {
                const icon = ast.type === 'class' ? '🔷' : ast.type === 'function' ? '🔶' : '🔸';
                html += `<li>${icon} ${ast.name} (${ast.type})</li>`;
            });
            html += '</ul>';
        }

        html += '</div>';
        dataContent.innerHTML = html;
    }

    /**
     * Get operation color
     */
    getOperationColor(type) {
        switch (type) {
            case 'Write': return '#4CAF50';
            case 'Edit': return '#FF9800';
            case 'Read': return '#2196F3';
            default: return '#999';
        }
    }

    /**
     * Escape HTML
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Expand all nodes
     */
    expandAllNodes() {
        if (!this.d3Root) return;
        
        this.d3Root.descendants().forEach(d => {
            if (d._children) {
                d.children = d._children;
                d._children = null;
            }
        });
        
        this.renderTree();
    }

    /**
     * Collapse all nodes
     */
    collapseAllNodes() {
        if (!this.d3Root) return;
        
        this.d3Root.descendants().forEach(d => {
            if (d.children && d.depth > 0) {
                d._children = d.children;
                d.children = null;
            }
        });
        
        this.renderTree();
    }

    /**
     * Reset zoom
     */
    resetZoom() {
        if (!this.d3Tree) return;
        
        this.d3Tree.svg.transition()
            .duration(750)
            .call(this.d3Tree.zoom.transform, d3.zoomIdentity);
    }

    /**
     * Update session list in main selector
     */
    updateSessionList() {
        // Update the main session selector if it exists
        const mainSelect = document.getElementById('session-select');
        if (!mainSelect) return;

        const currentValue = mainSelect.value;
        
        // Clear existing options except "All Sessions"
        while (mainSelect.options.length > 1) {
            mainSelect.remove(1);
        }

        // Add session options from our tracked sessions
        for (const [sessionId, session] of this.sessions.entries()) {
            // Check if option already exists
            let exists = false;
            for (let i = 0; i < mainSelect.options.length; i++) {
                if (mainSelect.options[i].value === sessionId) {
                    exists = true;
                    break;
                }
            }
            
            if (!exists) {
                const option = document.createElement('option');
                option.value = sessionId;
                option.textContent = `Session ${sessionId.substring(0, 8)}... (${session.files.size} files)`;
                mainSelect.appendChild(option);
            }
        }
        
        // Restore previous selection if it still exists
        if (currentValue) {
            mainSelect.value = currentValue;
        }
    }

    /**
     * Update statistics
     */
    updateStats() {
        const stats = document.getElementById('claude-tree-stats');
        if (!stats) return;

        const totalFiles = this.currentSession
            ? Array.from(this.fileActivity.values()).filter(a => a.sessions.has(this.currentSession)).length
            : this.fileActivity.size;
        
        const totalOps = this.currentSession
            ? Array.from(this.fileActivity.values())
                .filter(a => a.sessions.has(this.currentSession))
                .reduce((sum, a) => sum + a.operations.length, 0)
            : Array.from(this.fileActivity.values())
                .reduce((sum, a) => sum + a.operations.length, 0);

        stats.textContent = `Files: ${totalFiles} | Operations: ${totalOps} | Sessions: ${this.sessions.size}`;
    }
}

// Create and export singleton instance
window.CodeViewer = new CodeViewer();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.CodeViewer.initialize();
        
        // If File Tree tab is already active, show it
        const claudeTreeTab = document.getElementById('claude-tree-tab');
        if (claudeTreeTab && claudeTreeTab.classList.contains('active')) {
            console.log('[CodeViewer] File Tree tab is active on load, showing tree...');
            setTimeout(() => window.CodeViewer.show(), 100);
        }
    });
} else {
    window.CodeViewer.initialize();
    
    // If File Tree tab is already active, show it
    const claudeTreeTab = document.getElementById('claude-tree-tab');
    if (claudeTreeTab && claudeTreeTab.classList.contains('active')) {
        console.log('[CodeViewer] File Tree tab is active, showing tree...');
        setTimeout(() => window.CodeViewer.show(), 100);
    }
}

// Also listen for tab changes to ensure we render when needed
document.addEventListener('tabChanged', (event) => {
    if (event.detail && event.detail.newTab === 'claude-tree') {
        console.log('[CodeViewer] Tab changed to File Tree, forcing show...');
        setTimeout(() => window.CodeViewer.show(), 50);
    }
});

// Tab click handling is now done by UIStateManager
// CodeViewer.renderContent() is called when the File Tree tab is activated

// FALLBACK: Periodic check to ensure File Tree tab is properly rendered
setInterval(() => {
    const claudeTreeTab = document.getElementById('claude-tree-tab');
    const claudeTreeContainer = document.getElementById('claude-tree-container');
    
    if (claudeTreeTab && claudeTreeTab.classList.contains('active') && 
        claudeTreeContainer && !claudeTreeContainer.querySelector('.activity-tree-wrapper')) {
        console.log('[CodeViewer] Periodic check: File Tree tab is active but not properly rendered, fixing...');
        window.CodeViewer.show();
    }
}, 5000);