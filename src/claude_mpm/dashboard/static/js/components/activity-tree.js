/**
 * Activity Tree Component
 * 
 * D3.js-based collapsible tree visualization for showing PM activity hierarchy.
 * Displays PM actions, TodoWrite delegations, agent assignments, and tool usage.
 */

class ActivityTree {
    constructor() {
        this.container = null;
        this.svg = null;
        this.treeData = null;
        this.root = null;
        this.treeLayout = null;
        this.treeGroup = null;
        this.events = [];
        this.todoWriteStack = [];
        this.activeAgent = null;
        this.activeAgentStack = [];
        this.margin = {top: 20, right: 120, bottom: 20, left: 120};
        this.width = 960 - this.margin.left - this.margin.right;
        this.height = 500 - this.margin.top - this.margin.bottom;
        this.nodeId = 0;
        this.duration = 750;
        this.timeRange = '30min';
        this.searchTerm = '';
        this.tooltip = null;
        this.initialized = false;
    }

    /**
     * Initialize the activity tree visualization
     */
    initialize() {
        console.log('ActivityTree.initialize() called, initialized:', this.initialized);
        
        // Check if already initialized
        if (this.initialized) {
            console.log('Activity tree already initialized, skipping');
            return;
        }
        
        // First try to find the container
        this.container = document.getElementById('activity-tree-container');
        if (!this.container) {
            // Fall back to the inner div if container not found
            this.container = document.getElementById('activity-tree');
            if (!this.container) {
                console.error('Activity tree container not found in DOM');
                return;
            }
        }
        
        // Clear any existing text content that might be in the container
        if (this.container.textContent && this.container.textContent.trim()) {
            console.log('Clearing existing text content from container:', this.container.textContent);
            this.container.textContent = '';
        }
        
        console.log('Activity tree container found:', this.container);
        
        // Check if the container is visible before initializing
        const tabPanel = document.getElementById('activity-tab');
        if (!tabPanel) {
            console.error('Activity tab panel (#activity-tab) not found in DOM');
            return;
        }
        
        // Initialize even if tab is not active, but don't render until visible
        if (!tabPanel.classList.contains('active')) {
            console.log('Activity tab not active, initializing but deferring render');
            // Clear any text content that might be showing
            if (this.container.textContent && this.container.textContent.trim()) {
                this.container.textContent = '';
            }
            // Set up basic structure but defer visualization
            this.setupControls();
            this.initializeTreeData();
            this.subscribeToEvents();
            this.initialized = true;
            return;
        }

        // Clear container before creating visualization
        if (this.container.textContent && this.container.textContent.trim()) {
            console.log('Clearing container text before creating visualization');
            this.container.textContent = '';
        }
        
        this.setupControls();
        this.createVisualization();
        
        if (!this.svg || !this.treeGroup) {
            console.error('Failed to create D3 visualization elements');
            // Show error message in container
            if (this.container) {
                this.container.innerHTML = '<div style="padding: 20px; text-align: center; color: #e53e3e;">⚠️ Failed to create visualization. Please refresh the page.</div>';
            }
            return;
        }
        
        this.initializeTreeData();
        
        // Only update if we have a valid root
        if (this.root) {
            this.update(this.root);
        } else {
            console.warn('Root not created, skipping initial update');
        }
        
        this.subscribeToEvents();
        
        this.initialized = true;
        console.log('Activity tree initialization complete');
    }

    /**
     * Force show the tree visualization
     */
    forceShow() {
        console.log('ActivityTree.forceShow() called');
        
        // Ensure container is available
        if (!this.container) {
            this.container = document.getElementById('activity-tree-container') || document.getElementById('activity-tree');
            if (!this.container) {
                console.error('Cannot find activity tree container');
                return;
            }
        }
        
        // Clear any text content
        if (this.container.textContent && this.container.textContent.trim()) {
            console.log('Clearing text from container:', this.container.textContent);
            this.container.innerHTML = '';
        }
        
        // Create visualization if needed
        if (!this.svg) {
            this.createVisualization();
        }
        
        // Initialize tree data if needed
        if (!this.root) {
            this.initializeTreeData();
        }
        
        // Update the tree
        if (this.root && this.svg && this.treeGroup) {
            this.update(this.root);
        }
        
        // Ensure the SVG is visible
        if (this.svg) {
            const svgNode = this.svg.node();
            if (svgNode) {
                svgNode.style.display = 'block';
                svgNode.style.visibility = 'visible';
            }
        }
    }
    
    /**
     * Render the visualization when tab becomes visible (called when switching to Activity tab)
     */
    renderWhenVisible() {
        console.log('ActivityTree.renderWhenVisible() called');
        
        // Ensure the container is clean
        if (this.container && this.container.textContent && this.container.textContent.trim() && !this.svg) {
            console.log('Clearing text content before rendering:', this.container.textContent);
            this.container.textContent = '';
        }
        
        if (!this.initialized) {
            console.log('Not initialized yet, calling initialize...');
            this.initialize();
            return;
        }
        
        // If already initialized but no visualization, create it
        if (!this.svg) {
            console.log('Creating deferred visualization...');
            this.createVisualization();
            if (this.svg && this.treeGroup && this.root) {
                this.update(this.root);
            } else if (!this.root) {
                console.warn('No root node available, initializing tree data...');
                this.initializeTreeData();
                if (this.root && this.svg && this.treeGroup) {
                    this.update(this.root);
                }
            }
        }
        
        // Force update to ensure tree is rendered with current data
        if (this.root && this.svg) {
            console.log('Updating tree with current data...');
            this.update(this.root);
        } else {
            console.warn('Cannot update tree - missing components:', {
                hasRoot: !!this.root,
                hasSvg: !!this.svg,
                hasTreeGroup: !!this.treeGroup
            });
        }
    }

    /**
     * Setup control handlers
     */
    setupControls() {
        // Expand all button
        const expandAllBtn = document.getElementById('expand-all');
        if (expandAllBtn) {
            expandAllBtn.addEventListener('click', () => this.expandAll());
        }

        // Collapse all button
        const collapseAllBtn = document.getElementById('collapse-all');
        if (collapseAllBtn) {
            collapseAllBtn.addEventListener('click', () => this.collapseAll());
        }

        // Reset zoom button
        const resetZoomBtn = document.getElementById('reset-zoom');
        if (resetZoomBtn) {
            resetZoomBtn.addEventListener('click', () => this.resetZoom());
        }

        // Time range selector
        const timeRangeSelect = document.getElementById('time-range');
        if (timeRangeSelect) {
            timeRangeSelect.addEventListener('change', (e) => {
                this.timeRange = e.target.value;
                this.filterEventsByTime();
            });
        }

        // Search input
        const searchInput = document.getElementById('activity-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.searchTerm = e.target.value.toLowerCase();
                this.highlightSearchResults();
            });
        }
    }

    /**
     * Create the D3 visualization
     */
    createVisualization() {
        // Check if D3 is available
        if (typeof d3 === 'undefined') {
            console.error('D3.js is not loaded! Cannot create activity tree visualization.');
            // Try to display an error message in the container
            if (this.container) {
                this.container.innerHTML = '<div style="padding: 20px; text-align: center; color: #e53e3e;">⚠️ D3.js is not loaded. Cannot create visualization.</div>';
            }
            return;
        }

        // Calculate dimensions based on container
        const containerRect = this.container.getBoundingClientRect();
        this.width = containerRect.width - this.margin.left - this.margin.right;
        this.height = Math.max(500, containerRect.height - this.margin.top - this.margin.bottom);

        console.log('Creating D3 visualization with dimensions:', { width: this.width, height: this.height });

        // Clear any existing content (including text)
        d3.select(this.container).selectAll('*').remove();

        // Create SVG
        this.svg = d3.select(this.container)
            .append('svg')
            .attr('width', '100%')
            .attr('height', '100%')
            .attr('viewBox', `0 0 ${this.width + this.margin.left + this.margin.right} ${this.height + this.margin.top + this.margin.bottom}`);

        // Create main group for tree positioning
        this.treeGroup = this.svg.append('g')
            .attr('class', 'tree-group')
            .attr('transform', `translate(${this.margin.left},${this.margin.top})`);

        // Add zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.1, 3])
            .on('zoom', (event) => {
                this.treeGroup.attr('transform', 
                    `translate(${this.margin.left + event.transform.x},${this.margin.top + event.transform.y}) scale(${event.transform.k})`
                );
            });

        this.svg.call(zoom);

        // Create tree layout
        this.treeLayout = d3.tree()
            .size([this.height, this.width]);
        
        console.log('ActivityTree: Tree layout created:', this.treeLayout);

        // Create tooltip
        this.tooltip = d3.select('body').append('div')
            .attr('class', 'activity-tooltip')
            .style('opacity', 0);
        
        console.log('ActivityTree: Visualization complete, svg:', this.svg, 'treeGroup:', this.treeGroup);
    }

    /**
     * Initialize tree data structure
     */
    initializeTreeData() {
        console.log('ActivityTree: Initializing tree data');
        
        this.treeData = {
            name: 'PM',
            type: 'pm',
            icon: '🎯',
            children: [],
            _children: null
        };

        // Check if D3 is available
        if (typeof d3 === 'undefined') {
            console.error('ActivityTree: D3 is not available - cannot create hierarchy!');
            // Try to display an error message
            if (this.container) {
                this.container.innerHTML = '<div style="padding: 20px; text-align: center; color: #e53e3e;">⚠️ Waiting for D3.js to load...</div>';
            }
            return;
        }

        this.root = d3.hierarchy(this.treeData);
        this.root.x0 = this.height / 2;
        this.root.y0 = 0;
        
        console.log('ActivityTree: Root node created:', this.root);
        
        // Update stats immediately after creating root
        this.updateStats();
    }

    /**
     * Subscribe to socket events
     */
    subscribeToEvents() {
        if (!window.socketClient) {
            console.warn('Socket client not available for activity tree');
            setTimeout(() => this.subscribeToEvents(), 1000);
            return;
        }

        console.log('ActivityTree: Setting up event subscription');

        // Subscribe to event updates from the socket client
        // Process ALL events and determine their type internally
        window.socketClient.onEventUpdate((events) => {
            console.log(`ActivityTree: onEventUpdate called with ${events.length} total events`);
            
            // Process only the new events since last update
            const newEventCount = events.length - this.events.length;
            if (newEventCount > 0) {
                // Process only the new events
                const newEvents = events.slice(this.events.length);
                
                console.log(`ActivityTree: Processing ${newEventCount} new events`, newEvents);
                
                // Process all events, regardless of format
                newEvents.forEach(event => {
                    this.processEvent(event);
                });
                
                // Update our event count
                this.events = [...events];
            }
        });

        // Load existing events if available
        const existingEvents = window.socketClient?.events || window.eventViewer?.events || [];
        
        if (existingEvents.length > 0) {
            console.log(`ActivityTree: Processing ${existingEvents.length} existing events`, existingEvents);
            existingEvents.forEach(event => {
                this.processEvent(event);
            });
            this.events = [...existingEvents];
        } else {
            console.log('ActivityTree: No existing events found');
            this.events = [];
        }
    }

    /**
     * Process an event and update the tree
     */
    processEvent(event) {
        if (!event) {
            console.log('ActivityTree: Ignoring null event');
            return;
        }
        
        // Handle events with the actual format from the server
        let eventType = null;
        
        // First check if hook_event_name exists (from transformation)
        if (event.hook_event_name) {
            eventType = event.hook_event_name;
        }
        // Map from type/subtype for hook events
        else if (event.type === 'hook' && event.subtype) {
            const mapping = {
                'pre_tool': 'PreToolUse',
                'post_tool': 'PostToolUse',
                'subagent_start': 'SubagentStart',
                'subagent_stop': 'SubagentStop',
                'todo_write': 'TodoWrite'
            };
            eventType = mapping[event.subtype];
        }
        // Handle todo events
        else if (event.type === 'todo' && event.subtype === 'updated') {
            eventType = 'TodoWrite';
        }
        // Handle subagent events
        else if (event.type === 'subagent') {
            if (event.subtype === 'started') {
                eventType = 'SubagentStart';
            } else if (event.subtype === 'stopped') {
                eventType = 'SubagentStop';
            }
        }
        // Handle start event
        else if (event.type === 'start') {
            eventType = 'Start';
        }
        
        if (!eventType) {
            // Only log if it's a potentially relevant event
            if (event.type === 'hook' || event.type === 'todo' || event.type === 'subagent') {
                console.log('ActivityTree: Cannot determine event type for:', event);
            }
            return;
        }
        
        console.log(`ActivityTree: Processing event: ${eventType}`, event);
        
        const timestamp = new Date(event.timestamp);
        if (!this.isEventInTimeRange(timestamp)) {
            return;
        }
        
        switch (eventType) {
            case 'TodoWrite':
                this.processTodoWrite(event);
                break;
            case 'SubagentStart':
                this.processSubagentStart(event);
                break;
            case 'SubagentStop':
                this.processSubagentStop(event);
                break;
            case 'PreToolUse':
                this.processToolUse(event);
                break;
            case 'PostToolUse':
                this.updateToolStatus(event, 'completed');
                break;
            case 'Start':
                this.initializeTreeData();
                this.update(this.root);
                break;
        }
        
        this.updateStats();
    }

    /**
     * Process TodoWrite event
     */
    processTodoWrite(event) {
        console.log('ActivityTree: Processing TodoWrite event:', event);
        
        // Look for todos in multiple places for compatibility
        let todos = event.todos || 
                    event.data?.todos || 
                    event.data ||  // Sometimes todos are directly in data
                    [];
        
        // Handle case where todos might be an object with todos property
        if (todos && typeof todos === 'object' && todos.todos) {
            todos = todos.todos;
        }
        
        // Ensure todos is an array
        if (!Array.isArray(todos)) {
            console.log('ActivityTree: Invalid todos format in event:', event);
            return;
        }
        
        if (todos.length === 0) {
            console.log('ActivityTree: No todos in event');
            return;
        }

        // Find in-progress todo
        const activeTodo = todos.find(t => t.status === 'in_progress');
        if (!activeTodo) {
            console.log('ActivityTree: No in-progress todo found');
            return;
        }

        console.log('ActivityTree: Found active todo:', activeTodo);

        // Create TodoWrite node
        const todoNode = {
            name: activeTodo.activeForm || activeTodo.content,
            type: 'todowrite',
            icon: '📝',
            content: activeTodo.content,
            status: activeTodo.status,
            timestamp: event.timestamp,
            children: [],
            _children: null,
            eventId: event.id
        };

        // Add to PM root
        if (!this.root) {
            console.error('ActivityTree: No root node!');
            return;
        }
        
        if (!this.root.data) {
            console.error('ActivityTree: Root has no data!');
            return;
        }
        
        if (!this.root.data.children) {
            this.root.data.children = [];
        }
        
        console.log('ActivityTree: Adding TodoWrite node to root');
        this.root.data.children.push(todoNode);

        // Track this TodoWrite
        this.todoWriteStack.push({
            node: todoNode,
            content: activeTodo.content
        });

        console.log('ActivityTree: Calling update with root:', this.root);
        this.update(this.root);
        console.log('ActivityTree: Update complete');
    }

    /**
     * Process SubagentStart event
     */
    processSubagentStart(event) {
        // Look for agent_name in multiple places for compatibility
        const agentName = event.agent_name || 
                         event.data?.agent_name || 
                         event.data?.agent_type || 
                         event.agent_type ||  // Check direct agent_type field
                         event.agent ||        // Check agent field
                         'unknown';
        const agentIcon = this.getAgentIcon(agentName);

        // Create agent node
        const agentNode = {
            name: agentName,
            type: 'agent',
            icon: agentIcon,
            timestamp: event.timestamp,
            children: [],
            _children: null,
            eventId: event.id,
            sessionId: event.session_id || event.data?.session_id
        };

        // Find parent - either last TodoWrite or PM root
        let parent = null;
        if (this.todoWriteStack.length > 0) {
            // Check if TodoWrite mentions this agent
            const todoWrite = this.todoWriteStack[this.todoWriteStack.length - 1];
            if (todoWrite.content && todoWrite.content.toLowerCase().includes(agentName.toLowerCase())) {
                parent = todoWrite.node;
            }
        }

        if (!parent) {
            parent = this.root.data;
        }

        if (!parent.children) {
            parent.children = [];
        }
        parent.children.push(agentNode);

        // Track active agent
        this.activeAgent = agentNode;
        this.activeAgentStack.push(agentNode);

        this.update(this.root);
    }

    /**
     * Process SubagentStop event
     */
    processSubagentStop(event) {
        // Mark agent as completed (look for session_id in multiple places)
        const sessionId = event.session_id || event.data?.session_id;
        if (this.activeAgent && this.activeAgent.sessionId === sessionId) {
            this.activeAgent.status = 'completed';
            this.activeAgentStack.pop();
            this.activeAgent = this.activeAgentStack.length > 0 ? 
                this.activeAgentStack[this.activeAgentStack.length - 1] : null;
        }

        this.update(this.root);
    }

    /**
     * Process tool use event
     */
    processToolUse(event) {
        // Get tool name from various possible locations
        const toolName = event.tool_name || 
                        event.data?.tool_name || 
                        event.tool ||           // Check event.tool field
                        event.data?.tool ||
                        'unknown';
        
        const toolIcon = this.getToolIcon(toolName);
        
        // Get parameters from various possible locations
        const params = event.tool_parameters || 
                      event.data?.tool_parameters || 
                      event.parameters ||          // Check event.parameters field
                      event.data?.parameters ||
                      {};

        // Create tool node
        const toolNode = {
            name: toolName,
            type: 'tool',
            icon: toolIcon,
            timestamp: event.timestamp,
            status: 'in_progress',
            children: [],
            _children: null,
            eventId: event.id
        };

        // Add file/command as child if applicable
        if (toolName === 'Read' && params.file_path) {
            toolNode.children.push({
                name: params.file_path,
                type: 'file',
                icon: '📄',
                timestamp: event.timestamp
            });
        } else if (toolName === 'Edit' && params.file_path) {
            toolNode.children.push({
                name: params.file_path,
                type: 'file',
                icon: '✏️',
                timestamp: event.timestamp
            });
        } else if (toolName === 'Write' && params.file_path) {
            toolNode.children.push({
                name: params.file_path,
                type: 'file',
                icon: '💾',
                timestamp: event.timestamp
            });
        } else if (toolName === 'Bash' && params.command) {
            toolNode.children.push({
                name: params.command.substring(0, 50) + (params.command.length > 50 ? '...' : ''),
                type: 'command',
                icon: '⚡',
                timestamp: event.timestamp
            });
        } else if (toolName === 'WebFetch' && params.url) {
            toolNode.children.push({
                name: params.url,
                type: 'url',
                icon: '🌐',
                timestamp: event.timestamp
            });
        }

        // Find parent - active agent or PM root
        let parent = this.activeAgent || this.root.data;
        if (!parent.children) {
            parent.children = [];
        }
        parent.children.push(toolNode);

        this.update(this.root);
    }

    /**
     * Update tool status after completion
     */
    updateToolStatus(event, status) {
        // Find tool node by event ID and update status
        const findAndUpdate = (node) => {
            if (node.eventId === event.id) {
                node.status = status;
                return true;
            }
            if (node.children) {
                for (let child of node.children) {
                    if (findAndUpdate(child)) return true;
                }
            }
            if (node._children) {
                for (let child of node._children) {
                    if (findAndUpdate(child)) return true;
                }
            }
            return false;
        };

        findAndUpdate(this.root.data);
        this.update(this.root);
    }

    /**
     * Get agent icon based on name
     */
    getAgentIcon(agentName) {
        const icons = {
            'engineer': '👷',
            'research': '🔬',
            'qa': '🧪',
            'ops': '⚙️',
            'pm': '📊',
            'architect': '🏗️'
        };
        return icons[agentName.toLowerCase()] || '🤖';
    }

    /**
     * Get tool icon based on name
     */
    getToolIcon(toolName) {
        const icons = {
            'read': '👁️',
            'write': '✍️',
            'edit': '✏️',
            'bash': '💻',
            'webfetch': '🌐',
            'grep': '🔍',
            'glob': '📂',
            'todowrite': '📝'
        };
        return icons[toolName.toLowerCase()] || '🔧';
    }

    /**
     * Update the tree visualization
     */
    update(source) {
        console.log('ActivityTree: update() called with source:', source);
        
        // Check if D3 is available
        if (typeof d3 === 'undefined') {
            console.error('ActivityTree: Cannot update - D3.js not loaded');
            return;
        }
        
        // Check if visualization is ready
        if (!this.svg || !this.treeGroup) {
            console.warn('ActivityTree: Cannot update - SVG not initialized');
            // Try to create visualization if container exists
            if (this.container) {
                console.log('Attempting to create visualization from update()');
                this.createVisualization();
                // Check again after creation attempt
                if (!this.svg || !this.treeGroup) {
                    console.error('Failed to create visualization in update()');
                    return;
                }
            } else {
                return;
            }
        }
        
        if (!this.treeLayout) {
            console.warn('ActivityTree: Cannot update - tree layout not initialized');
            // Try to create tree layout
            if (typeof d3 !== 'undefined') {
                this.treeLayout = d3.tree().size([this.height, this.width]);
                console.log('Created tree layout in update()');
            } else {
                return;
            }
        }
        
        // Ensure source has valid data
        if (!source || !source.data) {
            console.error('ActivityTree: Invalid source in update()', source);
            return;
        }
        
        // Ensure we have a valid root
        if (!this.root) {
            console.error('ActivityTree: No root node available for update');
            return;
        }
        
        // Compute the new tree layout
        let treeData;
        try {
            treeData = this.treeLayout(this.root);
        } catch (error) {
            console.error('ActivityTree: Error computing tree layout:', error);
            return;
        }
        
        const nodes = treeData.descendants();
        const links = treeData.links();
        
        console.log(`ActivityTree: Updating tree with ${nodes.length} nodes`);
        
        // Check if we actually have the tree container
        if (nodes.length === 1 && this.container) {
            // Only root node exists, ensure container shows the tree
            const svgElement = this.container.querySelector('svg');
            if (!svgElement) {
                console.warn('SVG element not found in container after update');
            }
        }

        // Normalize for fixed-depth
        nodes.forEach((d) => {
            d.y = d.depth * 180;
        });

        // Update nodes
        const node = this.treeGroup.selectAll('g.node')
            .data(nodes, (d) => d.id || (d.id = ++this.nodeId));

        // Enter new nodes
        const nodeEnter = node.enter().append('g')
            .attr('class', 'node')
            .attr('transform', (d) => `translate(${source.y0},${source.x0})`)
            .on('click', (event, d) => this.click(d));

        // Add circles for nodes
        nodeEnter.append('circle')
            .attr('class', (d) => `node-circle ${d.data.type}`)
            .attr('r', 1e-6)
            .style('fill', (d) => d._children ? this.getNodeColor(d.data.type) : '#fff')
            .style('stroke', (d) => this.getNodeColor(d.data.type));

        // Add icons
        nodeEnter.append('text')
            .attr('class', 'node-icon')
            .attr('dy', '.35em')
            .attr('text-anchor', 'middle')
            .style('font-size', '14px')
            .text((d) => d.data.icon || '');

        // Add labels
        nodeEnter.append('text')
            .attr('class', 'node-label')
            .attr('dy', '.35em')
            .attr('x', (d) => d.children || d._children ? -25 : 25)
            .attr('text-anchor', (d) => d.children || d._children ? 'end' : 'start')
            .text((d) => d.data.name)
            .style('fill-opacity', 1e-6);

        // Add tooltips
        nodeEnter.on('mouseover', (event, d) => this.showTooltip(event, d))
            .on('mouseout', () => this.hideTooltip());

        // Update existing nodes
        const nodeUpdate = nodeEnter.merge(node);

        // Transition nodes to new position
        nodeUpdate.transition()
            .duration(this.duration)
            .attr('transform', (d) => `translate(${d.y},${d.x})`);

        nodeUpdate.select('circle.node-circle')
            .attr('r', 10)
            .style('fill', (d) => {
                if (d.data.status === 'in_progress') {
                    return this.getNodeColor(d.data.type);
                }
                return d._children ? this.getNodeColor(d.data.type) : '#fff';
            })
            .attr('class', (d) => {
                let classes = `node-circle ${d.data.type}`;
                if (d.data.status === 'in_progress') classes += ' pulsing';
                if (d.data.status === 'failed') classes += ' failed';
                return classes;
            });

        nodeUpdate.select('text.node-label')
            .style('fill-opacity', 1);

        // Remove exiting nodes
        const nodeExit = node.exit().transition()
            .duration(this.duration)
            .attr('transform', (d) => `translate(${source.y},${source.x})`)
            .remove();

        nodeExit.select('circle')
            .attr('r', 1e-6);

        nodeExit.select('text')
            .style('fill-opacity', 1e-6);

        // Update links
        const link = this.treeGroup.selectAll('path.link')
            .data(links, (d) => d.target.id);

        // Enter new links
        const linkEnter = link.enter().insert('path', 'g')
            .attr('class', 'link')
            .attr('d', (d) => {
                const o = {x: source.x0, y: source.y0};
                return this.diagonal({source: o, target: o});
            });

        // Update existing links
        const linkUpdate = linkEnter.merge(link);

        linkUpdate.transition()
            .duration(this.duration)
            .attr('d', this.diagonal);

        // Remove exiting links
        link.exit().transition()
            .duration(this.duration)
            .attr('d', (d) => {
                const o = {x: source.x, y: source.y};
                return this.diagonal({source: o, target: o});
            })
            .remove();

        // Store old positions for transition
        nodes.forEach((d) => {
            d.x0 = d.x;
            d.y0 = d.y;
        });

        // Update breadcrumb on node click
        this.updateBreadcrumb(source);
    }

    /**
     * Create diagonal path for links
     */
    diagonal(d) {
        return `M ${d.source.y} ${d.source.x}
                C ${(d.source.y + d.target.y) / 2} ${d.source.x},
                  ${(d.source.y + d.target.y) / 2} ${d.target.x},
                  ${d.target.y} ${d.target.x}`;
    }

    /**
     * Handle node click for expand/collapse
     */
    click(d) {
        if (d.children) {
            d._children = d.children;
            d.children = null;
        } else {
            d.children = d._children;
            d._children = null;
        }
        this.update(d);
        this.updateBreadcrumb(d);
    }

    /**
     * Get node color based on type
     */
    getNodeColor(type) {
        const colors = {
            'pm': '#4299e1',
            'todowrite': '#48bb78',
            'agent': '#ed8936',
            'tool': '#9f7aea',
            'file': '#38b2ac',
            'command': '#f56565',
            'url': '#4299e1'
        };
        return colors[type] || '#718096';
    }

    /**
     * Show tooltip
     */
    showTooltip(event, d) {
        const content = `
            <strong>${d.data.name}</strong><br>
            Type: ${d.data.type}<br>
            ${d.data.timestamp ? `Time: ${new Date(d.data.timestamp).toLocaleTimeString()}` : ''}
            ${d.data.status ? `<br>Status: ${d.data.status}` : ''}
        `;

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
        this.tooltip.transition()
            .duration(500)
            .style('opacity', 0);
    }

    /**
     * Expand all nodes
     */
    expandAll() {
        const expand = (d) => {
            if (d._children) {
                d.children = d._children;
                d._children = null;
            }
            if (d.children) {
                d.children.forEach(expand);
            }
        };
        
        expand(this.root);
        this.update(this.root);
    }

    /**
     * Collapse all nodes
     */
    collapseAll() {
        const collapse = (d) => {
            if (d.children) {
                d._children = d.children;
                d._children.forEach(collapse);
                d.children = null;
            }
        };
        
        this.root.children?.forEach(collapse);
        this.update(this.root);
    }

    /**
     * Reset zoom
     */
    resetZoom() {
        if (!this.svg) {
            console.warn('Cannot reset zoom: SVG not initialized');
            return;
        }
        
        const zoom = d3.zoom()
            .scaleExtent([0.1, 3])
            .on('zoom', (event) => {
                this.treeGroup.attr('transform', 
                    `translate(${this.margin.left + event.transform.x},${this.margin.top + event.transform.y}) scale(${event.transform.k})`
                );
            });
        
        this.svg.transition()
            .duration(750)
            .call(zoom.transform, d3.zoomIdentity);
        
        // Reset the tree group transform
        this.treeGroup.transition()
            .duration(750)
            .attr('transform', `translate(${this.margin.left},${this.margin.top})`);
    }

    /**
     * Check if event is in time range
     */
    isEventInTimeRange(timestamp) {
        if (this.timeRange === 'all') return true;

        const now = new Date();
        const diff = now - timestamp;
        const minutes = diff / (1000 * 60);

        switch (this.timeRange) {
            case '10min': return minutes <= 10;
            case '30min': return minutes <= 30;
            case 'hour': return minutes <= 60;
            default: return true;
        }
    }

    /**
     * Filter events by time
     */
    filterEventsByTime() {
        this.initializeTreeData();
        
        // Reprocess all events with new time filter
        if (window.eventViewer && window.eventViewer.events) {
            window.eventViewer.events.forEach(event => {
                this.processEvent(event);
            });
        }
    }

    /**
     * Update statistics
     */
    updateStats() {
        // Check if we have a valid root node
        if (!this.root || !this.root.data) {
            console.warn('ActivityTree: Cannot update stats - root not initialized');
            // Set default values
            const nodeCountEl = document.getElementById('node-count');
            const activeCountEl = document.getElementById('active-count');
            const depthEl = document.getElementById('tree-depth');
            
            if (nodeCountEl) nodeCountEl.textContent = '1';
            if (activeCountEl) activeCountEl.textContent = '0';
            if (depthEl) depthEl.textContent = '0';
            return;
        }
        
        const nodeCount = this.countNodes(this.root);
        const activeCount = this.countActiveNodes(this.root.data);
        const depth = this.getTreeDepth(this.root);

        const nodeCountEl = document.getElementById('node-count');
        const activeCountEl = document.getElementById('active-count');
        const depthEl = document.getElementById('tree-depth');
        
        if (nodeCountEl) nodeCountEl.textContent = nodeCount;
        if (activeCountEl) activeCountEl.textContent = activeCount;
        if (depthEl) depthEl.textContent = depth;
        
        console.log(`ActivityTree: Stats updated - Nodes: ${nodeCount}, Active: ${activeCount}, Depth: ${depth}`);
    }

    /**
     * Count total nodes
     */
    countNodes(node) {
        let count = 1;
        if (node.children) {
            node.children.forEach(child => {
                count += this.countNodes(child);
            });
        }
        if (node._children) {
            node._children.forEach(child => {
                count += this.countNodes(child);
            });
        }
        return count;
    }

    /**
     * Count active nodes
     */
    countActiveNodes(node) {
        let count = node.status === 'in_progress' ? 1 : 0;
        if (node.children) {
            node.children.forEach(child => {
                count += this.countActiveNodes(child);
            });
        }
        if (node._children) {
            node._children.forEach(child => {
                count += this.countActiveNodes(child);
            });
        }
        return count;
    }

    /**
     * Get tree depth
     */
    getTreeDepth(node) {
        if (!node.children && !node._children) return 0;
        
        const children = node.children || node._children;
        const depths = children.map(child => this.getTreeDepth(child));
        return Math.max(...depths) + 1;
    }

    /**
     * Update breadcrumb
     */
    updateBreadcrumb(node) {
        const path = [];
        let current = node;
        
        while (current) {
            path.unshift(current.data.name);
            current = current.parent;
        }
        
        const breadcrumb = document.getElementById('activity-breadcrumb');
        if (breadcrumb) {
            breadcrumb.textContent = path.join(' > ');
        }
    }

    /**
     * Highlight search results
     */
    highlightSearchResults() {
        // Clear previous highlights
        this.treeGroup.selectAll('.node-label')
            .style('font-weight', 'normal')
            .style('fill', '#2d3748');

        if (!this.searchTerm) return;

        // Highlight matching nodes
        this.treeGroup.selectAll('.node-label')
            .style('font-weight', d => {
                return d.data.name.toLowerCase().includes(this.searchTerm) ? 'bold' : 'normal';
            })
            .style('fill', d => {
                return d.data.name.toLowerCase().includes(this.searchTerm) ? '#e53e3e' : '#2d3748';
            });
    }
}

// Make ActivityTree globally available immediately when module loads
window.ActivityTree = ActivityTree;

// Initialize when the Activity tab is selected
// Only set up event listeners when DOM is ready, but expose class immediately
const setupActivityTreeListeners = () => {
    let activityTree = null;

    // Function to initialize the tree
    const initializeActivityTree = () => {
        if (!activityTree) {
            console.log('Creating new Activity Tree instance...');
            activityTree = new ActivityTree();
            // Store instance globally for dashboard access
            window.activityTreeInstance = activityTree;
        }
        
        // Ensure the container is ready and clear any text
        const container = document.getElementById('activity-tree-container') || document.getElementById('activity-tree');
        if (container && container.textContent && container.textContent.trim()) {
            console.log('Clearing text from activity tree container before init:', container.textContent);
            container.textContent = '';
        }
        
        // Always try to initialize when tab becomes active, even if instance exists
        // Small delay to ensure DOM is ready and tab is visible
        setTimeout(() => {
            console.log('Attempting to initialize Activity Tree visualization...');
            activityTree.initialize();
        }, 100);
    };

    // Tab switching logic
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', (e) => {
            const tabName = e.target.getAttribute('data-tab');
            
            if (tabName === 'activity') {
                console.log('Activity tab button clicked, initializing tree...');
                initializeActivityTree();
                // Also call renderWhenVisible and forceShow to ensure proper rendering
                if (activityTree) {
                    setTimeout(() => {
                        activityTree.renderWhenVisible();
                        // Force show to ensure SVG is visible
                        activityTree.forceShow();
                    }, 150);
                }
            }
        });
    });

    // Also listen for custom tab change events
    document.addEventListener('tabChanged', (e) => {
        if (e.detail && e.detail.newTab === 'activity') {
            console.log('Tab changed to activity, initializing tree...');
            initializeActivityTree();
            // Also call renderWhenVisible and forceShow to ensure proper rendering
            if (activityTree) {
                setTimeout(() => {
                    activityTree.renderWhenVisible();
                    // Force show to ensure SVG is visible
                    activityTree.forceShow();
                }, 150);
            }
        }
    });

    // Check if activity tab is already active on load
    const activeTab = document.querySelector('.tab-button.active');
    if (activeTab && activeTab.getAttribute('data-tab') === 'activity') {
        console.log('Activity tab is active on load, initializing tree...');
        initializeActivityTree();
    }
    
    // Also check the tab panel directly
    const activityPanel = document.getElementById('activity-tab');
    if (activityPanel && activityPanel.classList.contains('active')) {
        console.log('Activity panel is active on load, initializing tree...');
        if (!activityTree) {
            initializeActivityTree();
        }
    }

    // Export for debugging
    window.activityTree = () => activityTree;  // Expose instance getter for debugging
};

// Set up listeners when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupActivityTreeListeners);
} else {
    // DOM already loaded
    setupActivityTreeListeners();
}

export { ActivityTree };
export default ActivityTree;