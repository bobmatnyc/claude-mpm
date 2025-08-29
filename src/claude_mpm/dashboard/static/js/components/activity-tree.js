/**
 * Activity Tree Component - Linear Tree View
 * 
 * HTML/CSS-based linear tree visualization for showing PM activity hierarchy.
 * Replaces D3.js with simpler, cleaner linear tree structure.
 * Uses simple display methods for data visualization.
 */

class ActivityTree {
    constructor() {
        this.container = null;
        this.events = [];
        this.sessions = new Map();
        this.currentSession = null;
        this.selectedSessionFilter = 'all';
        this.timeRange = '30min';
        this.searchTerm = '';
        this.initialized = false;
        this.expandedSessions = new Set();
        this.expandedAgents = new Set();
        this.expandedTools = new Set();
        this.selectedItem = null;
    }

    /**
     * Initialize the activity tree
     */
    initialize() {
        console.log('ActivityTree.initialize() called, initialized:', this.initialized);
        
        if (this.initialized) {
            console.log('Activity tree already initialized, skipping');
            return;
        }
        
        this.container = document.getElementById('activity-tree-container');
        if (!this.container) {
            this.container = document.getElementById('activity-tree');
            if (!this.container) {
                console.error('Activity tree container not found in DOM');
                return;
            }
        }
        
        // Check if the container is visible before initializing
        const tabPanel = document.getElementById('activity-tab');
        if (!tabPanel) {
            console.error('Activity tab panel (#activity-tab) not found in DOM');
            return;
        }
        
        // Initialize even if tab is not active
        if (!tabPanel.classList.contains('active')) {
            console.log('Activity tab not active, initializing but deferring render');
            this.setupControls();
            this.subscribeToEvents();
            this.initialized = true;
            return;
        }

        this.setupControls();
        this.createLinearTreeView();
        this.subscribeToEvents();
        
        this.initialized = true;
        console.log('Activity tree initialization complete');
    }

    /**
     * Force show the tree visualization
     */
    forceShow() {
        console.log('ActivityTree.forceShow() called');
        
        if (!this.container) {
            this.container = document.getElementById('activity-tree-container') || document.getElementById('activity-tree');
            if (!this.container) {
                console.error('Cannot find activity tree container');
                return;
            }
        }
        
        this.createLinearTreeView();
        this.renderTree();
    }
    
    /**
     * Render the visualization when tab becomes visible
     */
    renderWhenVisible() {
        console.log('ActivityTree.renderWhenVisible() called');
        
        if (!this.initialized) {
            console.log('Not initialized yet, calling initialize...');
            this.initialize();
            return;
        }
        
        this.createLinearTreeView();
        this.renderTree();
    }

    /**
     * Setup control handlers
     */
    setupControls() {
        // Time range filter dropdown
        const timeRangeSelect = document.getElementById('time-range');
        if (timeRangeSelect) {
            timeRangeSelect.addEventListener('change', (e) => {
                this.timeRange = e.target.value;
                console.log(`ActivityTree: Time range changed to: ${this.timeRange}`);
                this.renderTree();
            });
        }

        // Listen for session filter changes from SessionManager
        document.addEventListener('sessionFilterChanged', (e) => {
            this.selectedSessionFilter = e.detail.sessionId || 'all';
            console.log(`ActivityTree: Session filter changed to: ${this.selectedSessionFilter} (from SessionManager)`);
            this.renderTree();
        });

        // Also listen for sessionChanged for backward compatibility
        document.addEventListener('sessionChanged', (e) => {
            this.selectedSessionFilter = e.detail.sessionId || 'all';
            console.log(`ActivityTree: Session changed to: ${this.selectedSessionFilter} (from SessionManager - backward compat)`);
            this.renderTree();
        });

        // Initialize with current session filter from SessionManager
        setTimeout(() => {
            if (window.sessionManager) {
                const currentFilter = window.sessionManager.getCurrentFilter();
                if (currentFilter !== this.selectedSessionFilter) {
                    this.selectedSessionFilter = currentFilter || 'all';
                    console.log(`ActivityTree: Initialized with current session filter: ${this.selectedSessionFilter}`);
                    this.renderTree();
                }
            }
        }, 100); // Small delay to ensure SessionManager is initialized

        // Expand all button - expand all sessions
        const expandAllBtn = document.getElementById('expand-all');
        if (expandAllBtn) {
            expandAllBtn.addEventListener('click', () => this.expandAllSessions());
        }

        // Collapse all button - collapse all sessions
        const collapseAllBtn = document.getElementById('collapse-all');
        if (collapseAllBtn) {
            collapseAllBtn.addEventListener('click', () => this.collapseAllSessions());
        }

        // Reset zoom button functionality
        const resetZoomBtn = document.getElementById('reset-zoom');
        if (resetZoomBtn) {
            resetZoomBtn.style.display = 'inline-block';
            resetZoomBtn.addEventListener('click', () => this.resetZoom());
        }

        // Search input
        const searchInput = document.getElementById('activity-search');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.searchTerm = e.target.value.toLowerCase();
                this.renderTree();
            });
        }
    }

    /**
     * Create the linear tree view container
     */
    createLinearTreeView() {
        console.log('Creating linear tree view');
        
        // Clear container
        this.container.innerHTML = '';
        
        // Create main tree container
        const treeContainer = document.createElement('div');
        treeContainer.id = 'linear-tree';
        treeContainer.className = 'linear-tree';
        
        this.container.appendChild(treeContainer);
        
        console.log('Linear tree view created');
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
        // FIXED: Now correctly receives both events AND sessions from socket client
        window.socketClient.onEventUpdate((events, sessions) => {
            console.log(`ActivityTree: onEventUpdate called with ${events.length} total events and ${sessions.size} sessions`);
            
            // Use the authoritative sessions from socket client instead of building our own
            this.sessions.clear();
            
            // Convert authoritative sessions Map to our format
            for (const [sessionId, sessionData] of sessions.entries()) {
                const activitySession = {
                    id: sessionId,
                    timestamp: new Date(sessionData.lastActivity || sessionData.startTime || new Date()),
                    expanded: this.expandedSessions.has(sessionId) || true, // Preserve expansion state
                    agents: new Map(),
                    todos: [],
                    userInstructions: [],
                    tools: [],
                    status: 'active',
                    currentTodoTool: null,
                    // Preserve additional session metadata
                    working_directory: sessionData.working_directory,
                    git_branch: sessionData.git_branch,
                    eventCount: sessionData.eventCount
                };
                this.sessions.set(sessionId, activitySession);
            }
            
            // Process only the new events since last update
            const newEventCount = events.length - this.events.length;
            if (newEventCount > 0) {
                const newEvents = events.slice(this.events.length);
                console.log(`ActivityTree: Processing ${newEventCount} new events`, newEvents);
                
                newEvents.forEach(event => {
                    this.processEvent(event);
                });
            }
                
            this.events = [...events];
            this.renderTree();
            
            // Debug: Log session state after processing
            console.log(`ActivityTree: Sessions after sync with socket client:`, Array.from(this.sessions.entries()));
        });

        // Load existing data from socket client
        const socketState = window.socketClient?.getState();
        
        if (socketState && socketState.events.length > 0) {
            console.log(`ActivityTree: Loading existing data - ${socketState.events.length} events, ${socketState.sessions.size} sessions`);
            
            // Initialize from existing socket client data
            this.sessions.clear();
            
            // Convert authoritative sessions Map to our format
            for (const [sessionId, sessionData] of socketState.sessions.entries()) {
                const activitySession = {
                    id: sessionId,
                    timestamp: new Date(sessionData.lastActivity || sessionData.startTime || new Date()),
                    expanded: this.expandedSessions.has(sessionId) || true,
                    agents: new Map(),
                    todos: [],
                    userInstructions: [],
                    tools: [],
                    status: 'active',
                    currentTodoTool: null,
                    working_directory: sessionData.working_directory,
                    git_branch: sessionData.git_branch,
                    eventCount: sessionData.eventCount
                };
                this.sessions.set(sessionId, activitySession);
            }
            
            // Process existing events to populate activity data
            socketState.events.forEach(event => {
                this.processEvent(event);
            });
            this.events = [...socketState.events];
            this.renderTree();
            
            // Debug: Log initial session state
            console.log(`ActivityTree: Initial sessions state:`, Array.from(this.sessions.entries()));
        } else {
            console.log('ActivityTree: No existing events found');
            this.events = [];
            this.sessions.clear();
            this.renderTree();
        }
    }

    /**
     * Process an event and update the session structure
     */
    processEvent(event) {
        if (!event) {
            console.log('ActivityTree: Ignoring null event');
            return;
        }
        
        // Determine event type
        let eventType = this.getEventType(event);
        if (!eventType) {
            return;
        }
        
        console.log(`ActivityTree: Processing event: ${eventType}`, event);
        
        // Fix timestamp processing - ensure we get a valid date
        let timestamp;
        if (event.timestamp) {
            // Handle both ISO strings and already parsed dates
            timestamp = new Date(event.timestamp);
            // Check if date is valid
            if (isNaN(timestamp.getTime())) {
                console.warn('ActivityTree: Invalid timestamp, using current time:', event.timestamp);
                timestamp = new Date();
            }
        } else {
            console.warn('ActivityTree: No timestamp found, using current time');
            timestamp = new Date();
        }
        
        // Get session ID from event - this should match the authoritative sessions
        const sessionId = event.session_id || event.data?.session_id;
        
        // Skip events without session ID - they can't be properly categorized
        if (!sessionId) {
            console.log(`ActivityTree: Skipping event without session_id: ${eventType}`);
            return;
        }
        
        // Find the session - it should already exist from authoritative sessions
        if (!this.sessions.has(sessionId)) {
            console.warn(`ActivityTree: Session ${sessionId} not found in authoritative sessions - skipping event`);
            return;
        }
        
        const session = this.sessions.get(sessionId);
        
        switch (eventType) {
            case 'Start':
                // New PM session started
                this.currentSession = session;
                break;
            case 'user_prompt':
                this.processUserInstruction(event, session);
                break;
            case 'TodoWrite':
                this.processTodoWrite(event, session);
                break;
            case 'SubagentStart':
                this.processSubagentStart(event, session);
                break;
            case 'SubagentStop':
                this.processSubagentStop(event, session);
                break;
            case 'PreToolUse':
                this.processToolUse(event, session);
                break;
            case 'PostToolUse':
                this.updateToolStatus(event, session, 'completed');
                break;
        }
        
        this.updateStats();
    }

    /**
     * Get event type from event data
     */
    getEventType(event) {
        if (event.hook_event_name) {
            return event.hook_event_name;
        }
        
        if (event.type === 'hook' && event.subtype) {
            const mapping = {
                'pre_tool': 'PreToolUse',
                'post_tool': 'PostToolUse',
                'subagent_start': 'SubagentStart',
                'subagent_stop': 'SubagentStop',
                'todo_write': 'TodoWrite'
            };
            return mapping[event.subtype];
        }
        
        if (event.type === 'todo' && event.subtype === 'updated') {
            return 'TodoWrite';
        }
        
        if (event.type === 'subagent') {
            if (event.subtype === 'started') return 'SubagentStart';
            if (event.subtype === 'stopped') return 'SubagentStop';
        }
        
        if (event.type === 'start') {
            return 'Start';
        }
        
        if (event.type === 'user_prompt' || event.subtype === 'user_prompt') {
            return 'user_prompt';
        }
        
        return null;
    }

    // getSessionId method removed - now using authoritative session IDs directly from socket client

    /**
     * Process user instruction/prompt event
     */
    processUserInstruction(event, session) {
        const promptText = event.prompt_text || event.data?.prompt_text || event.prompt || '';
        if (!promptText) return;
        
        const instruction = {
            id: `instruction-${session.id}-${Date.now()}`,
            text: promptText,
            preview: promptText.length > 100 ? promptText.substring(0, 100) + '...' : promptText,
            timestamp: event.timestamp || new Date().toISOString(),
            type: 'user_instruction'
        };
        
        // Add to session's user instructions
        session.userInstructions.push(instruction);
        
        // Keep only last 5 instructions to prevent memory bloat
        if (session.userInstructions.length > 5) {
            session.userInstructions = session.userInstructions.slice(-5);
        }
    }

    /**
     * Process TodoWrite event - attach TODOs to session and active agent
     */
    processTodoWrite(event, session) {
        let todos = event.todos || event.data?.todos || event.data || [];
        
        if (todos && typeof todos === 'object' && todos.todos) {
            todos = todos.todos;
        }
        
        if (!Array.isArray(todos) || todos.length === 0) {
            return;
        }

        // Update session's todos directly for overall checklist view
        session.todos = todos.map(todo => ({
            content: todo.content,
            activeForm: todo.activeForm,
            status: todo.status,
            timestamp: event.timestamp
        }));
        
        // Create TodoWrite tool for session-level display
        const sessionTodoTool = {
            id: `todo-session-${session.id}-${Date.now()}`,
            name: 'TodoWrite',
            type: 'tool',
            icon: '📝',
            timestamp: event.timestamp,
            status: 'active',
            params: {
                todos: todos
            },
            isPrioritizedTool: true
        };
        
        // Update session-level TodoWrite tool
        session.tools = session.tools.filter(t => t.name !== 'TodoWrite');
        session.tools.unshift(sessionTodoTool);
        session.currentTodoTool = sessionTodoTool;

        // ALSO attach TodoWrite to the active agent that triggered it
        const agentSessionId = event.session_id || event.data?.session_id;
        let targetAgent = null;
        
        // Find the appropriate agent to attach this TodoWrite to
        // First try to find by session ID
        if (agentSessionId && session.agents.has(agentSessionId)) {
            targetAgent = session.agents.get(agentSessionId);
        } else {
            // Fall back to most recent active agent
            const activeAgents = Array.from(session.agents.values())
                .filter(agent => agent.status === 'active' || agent.status === 'in_progress')
                .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
            
            if (activeAgents.length > 0) {
                targetAgent = activeAgents[0];
            } else {
                // If no active agents, use the most recently used agent
                const allAgents = Array.from(session.agents.values())
                    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
                if (allAgents.length > 0) {
                    targetAgent = allAgents[0];
                }
            }
        }

        // Create agent-specific TodoWrite tool
        if (targetAgent) {
            const agentTodoTool = {
                id: `todo-agent-${targetAgent.id}-${Date.now()}`,
                name: 'TodoWrite',
                type: 'tool',
                icon: '📝',
                timestamp: event.timestamp,
                status: 'active',
                params: {
                    todos: todos
                },
                isPrioritizedTool: true
            };
            
            // Remove existing TodoWrite tool from agent and add the updated one
            targetAgent.tools = targetAgent.tools.filter(t => t.name !== 'TodoWrite');
            targetAgent.tools.unshift(agentTodoTool);
        }
    }

    /**
     * Process SubagentStart event
     */
    processSubagentStart(event, session) {
        const agentName = event.agent_name || event.data?.agent_name || event.data?.agent_type || event.agent_type || event.agent || 'unknown';
        const agentSessionId = event.session_id || event.data?.session_id;
        
        // Use session ID as unique agent identifier, or create unique ID
        const agentId = agentSessionId || `agent-${Date.now()}-${Math.random()}`;
        
        // Check if agent already exists in this session
        if (!session.agents.has(agentId)) {
            const agent = {
                id: agentId,
                name: agentName,
                type: 'agent',
                icon: this.getAgentIcon(agentName),
                timestamp: event.timestamp,
                status: 'active',
                tools: [],
                sessionId: agentSessionId,
                isPM: false
            };
            
            session.agents.set(agentId, agent);
        } else {
            // Update existing agent status to active
            const existingAgent = session.agents.get(agentId);
            existingAgent.status = 'active';
            existingAgent.timestamp = event.timestamp; // Update timestamp
        }
    }

    /**
     * Process SubagentStop event
     */
    processSubagentStop(event, session) {
        const agentSessionId = event.session_id || event.data?.session_id;
        
        // Find and mark agent as completed
        if (agentSessionId && session.agents.has(agentSessionId)) {
            const agent = session.agents.get(agentSessionId);
            agent.status = 'completed';
        }
    }

    /**
     * Process tool use event
     */
    processToolUse(event, session) {
        const toolName = event.tool_name || event.data?.tool_name || event.tool || event.data?.tool || 'unknown';
        const params = event.tool_parameters || event.data?.tool_parameters || event.parameters || event.data?.parameters || {};
        const agentSessionId = event.session_id || event.data?.session_id;
        
        const tool = {
            id: `tool-${Date.now()}-${Math.random()}`,
            name: toolName,
            type: 'tool',
            icon: this.getToolIcon(toolName),
            timestamp: event.timestamp,
            status: 'in_progress',
            params: params,
            eventId: event.id
        };

        // Find the appropriate agent to attach this tool to
        let targetAgent = null;
        
        // First try to find by session ID
        if (agentSessionId && session.agents.has(agentSessionId)) {
            targetAgent = session.agents.get(agentSessionId);
        } else {
            // Fall back to most recent active agent
            const activeAgents = Array.from(session.agents.values())
                .filter(agent => agent.status === 'active')
                .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
            
            if (activeAgents.length > 0) {
                targetAgent = activeAgents[0];
            } else {
                // If no active agents, attach to session (PM level)
                session.tools.push(tool);
                return;
            }
        }

        if (targetAgent) {
            targetAgent.tools.push(tool);
        }
    }

    /**
     * Update tool status after completion
     */
    updateToolStatus(event, session, status) {
        // Find and update tool status across all agents
        const findAndUpdateTool = (agent) => {
            if (agent.tools) {
                const tool = agent.tools.find(t => t.eventId === event.id);
                if (tool) {
                    tool.status = status;
                    return true;
                }
            }
            return false;
        };

        // Check all agents in session
        for (let agent of session.agents.values()) {
            if (findAndUpdateTool(agent)) return;
        }
        
        // Check session-level tools (PM level)
        if (session.tools && findAndUpdateTool(session)) return;
    }

    /**
     * Render the linear tree view
     */
    renderTree() {
        const treeContainer = document.getElementById('linear-tree');
        if (!treeContainer) return;
        
        // Clear tree
        treeContainer.innerHTML = '';
        
        // Add sessions directly (no project root)
        const sortedSessions = Array.from(this.sessions.values())
            .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        
        for (let session of sortedSessions) {
            if (this.selectedSessionFilter !== 'all' && this.selectedSessionFilter !== session.id) {
                continue;
            }
            
            const sessionElement = this.createSessionElement(session);
            treeContainer.appendChild(sessionElement);
        }
        
        // Session filtering is now handled by the main session selector via event listeners
    }


    /**
     * Create session element
     */
    createSessionElement(session) {
        const isExpanded = this.expandedSessions.has(session.id) || session.expanded;
        
        // Ensure timestamp is valid and format it consistently
        let sessionTime;
        try {
            const sessionDate = session.timestamp instanceof Date ? session.timestamp : new Date(session.timestamp);
            if (isNaN(sessionDate.getTime())) {
                sessionTime = 'Invalid Date';
                console.warn('ActivityTree: Invalid session timestamp:', session.timestamp);
            } else {
                sessionTime = sessionDate.toLocaleString();
            }
        } catch (error) {
            sessionTime = 'Invalid Date';
            console.error('ActivityTree: Error formatting session timestamp:', error, session.timestamp);
        }
        
        const element = document.createElement('div');
        element.className = 'tree-node session';
        element.dataset.sessionId = session.id;
        
        const expandIcon = isExpanded ? '▼' : '▶';
        const agentCount = session.agents ? session.agents.size : 0;
        const todoCount = session.todos ? session.todos.length : 0;
        const instructionCount = session.userInstructions ? session.userInstructions.length : 0;
        
        console.log(`ActivityTree: Rendering session ${session.id}: ${agentCount} agents, ${instructionCount} instructions, ${todoCount} todos at ${sessionTime}`);
        
        element.innerHTML = `
            <div class="tree-node-content" onclick="window.activityTreeInstance.toggleSession('${session.id}')">
                <span class="tree-expand-icon">${expandIcon}</span>
                <span class="tree-icon">🎯</span>
                <span class="tree-label">PM Session</span>
                <span class="tree-meta">${sessionTime} • ${agentCount} agent(s) • ${instructionCount} instruction(s) • ${todoCount} todo(s)</span>
            </div>
            <div class="tree-children" style="display: ${isExpanded ? 'block' : 'none'}">
                ${this.renderSessionContent(session)}
            </div>
        `;
        
        return element;
    }

    /**
     * Render session content (user instructions, todos, agents, tools)
     */
    renderSessionContent(session) {
        let html = '';
        
        // Render user instructions first
        if (session.userInstructions && session.userInstructions.length > 0) {
            for (let instruction of session.userInstructions.slice(-3)) { // Show last 3 instructions
                html += this.renderUserInstructionElement(instruction, 1);
            }
        }
        
        // Render TODOs as checklist directly under session
        if (session.todos && session.todos.length > 0) {
            html += this.renderTodoChecklistElement(session.todos, 1);
        }
        
        // Render session-level tools (PM tools)
        if (session.tools && session.tools.length > 0) {
            for (let tool of session.tools) {
                // Show all tools including TodoWrite - both checklist and tool views are useful
                html += this.renderToolElement(tool, 1);
            }
        }
        
        // Render agents
        const agents = Array.from(session.agents.values())
            .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        
        for (let agent of agents) {
            html += this.renderAgentElement(agent, 1);
        }
        
        return html;
    }

    /**
     * Render user instruction element
     */
    renderUserInstructionElement(instruction, level) {
        const isSelected = this.selectedItem && this.selectedItem.type === 'instruction' && this.selectedItem.data.id === instruction.id;
        const selectedClass = isSelected ? 'selected' : '';
        
        return `
            <div class="tree-node user-instruction ${selectedClass}" data-level="${level}">
                <div class="tree-node-content">
                    <span class="tree-expand-icon"></span>
                    <span class="tree-icon">💬</span>
                    <span class="tree-label clickable" onclick="window.activityTreeInstance.selectItem(${this.escapeJson(instruction)}, 'instruction', event)">User: "${this.escapeHtml(instruction.preview)}"</span>
                    <span class="tree-status status-active">instruction</span>
                </div>
            </div>
        `;
    }

    /**
     * Render TODO checklist element
     */
    renderTodoChecklistElement(todos, level) {
        const checklistId = `checklist-${Date.now()}`;
        const isExpanded = this.expandedTools.has(checklistId) !== false; // Default to expanded
        const expandIcon = isExpanded ? '▼' : '▶';
        
        // Calculate status summary
        let completedCount = 0;
        let inProgressCount = 0;
        let pendingCount = 0;
        
        todos.forEach(todo => {
            if (todo.status === 'completed') completedCount++;
            else if (todo.status === 'in_progress') inProgressCount++;
            else pendingCount++;
        });
        
        let statusSummary = '';
        if (inProgressCount > 0) {
            statusSummary = `${inProgressCount} in progress, ${completedCount} completed`;
        } else if (completedCount === todos.length && todos.length > 0) {
            statusSummary = `All ${todos.length} completed`;
        } else {
            statusSummary = `${todos.length} todo(s)`;
        }
        
        let html = `
            <div class="tree-node todo-checklist" data-level="${level}">
                <div class="tree-node-content">
                    <span class="tree-expand-icon" onclick="window.activityTreeInstance.toggleTodoChecklist('${checklistId}'); event.stopPropagation();">${expandIcon}</span>
                    <span class="tree-icon">☑️</span>
                    <span class="tree-label">TODOs</span>
                    <span class="tree-params">${statusSummary}</span>
                    <span class="tree-status status-active">checklist</span>
                </div>
        `;
        
        // Show expanded todo items if expanded
        if (isExpanded) {
            html += '<div class="tree-children">';
            for (let todo of todos) {
                const statusIcon = this.getCheckboxIcon(todo.status);
                const statusClass = `status-${todo.status}`;
                const displayText = todo.status === 'in_progress' ? todo.activeForm : todo.content;
                
                html += `
                    <div class="tree-node todo-item ${statusClass}" data-level="${level + 1}">
                        <div class="tree-node-content">
                            <span class="tree-expand-icon"></span>
                            <span class="tree-icon">${statusIcon}</span>
                            <span class="tree-label">${this.escapeHtml(displayText)}</span>
                            <span class="tree-status ${statusClass}">${todo.status.replace('_', ' ')}</span>
                        </div>
                    </div>
                `;
            }
            html += '</div>';
        }
        
        html += '</div>';
        return html;
    }

    /**
     * Render agent element
     */
    renderAgentElement(agent, level) {
        const statusClass = agent.status === 'active' ? 'status-active' : 'status-completed';
        const isExpanded = this.expandedAgents.has(agent.id);
        const hasTools = agent.tools && agent.tools.length > 0;
        const isSelected = this.selectedItem && this.selectedItem.type === 'agent' && this.selectedItem.data.id === agent.id;
        
        const expandIcon = hasTools ? (isExpanded ? '▼' : '▶') : '';
        const selectedClass = isSelected ? 'selected' : '';
        
        let html = `
            <div class="tree-node agent ${statusClass} ${selectedClass}" data-level="${level}">
                <div class="tree-node-content">
                    ${expandIcon ? `<span class="tree-expand-icon" onclick="window.activityTreeInstance.toggleAgent('${agent.id}'); event.stopPropagation();">${expandIcon}</span>` : '<span class="tree-expand-icon"></span>'}
                    <span class="tree-icon">${agent.icon}</span>
                    <span class="tree-label clickable" onclick="window.activityTreeInstance.selectItem(${this.escapeJson(agent)}, 'agent', event)">${agent.name}</span>
                    <span class="tree-status ${statusClass}">${agent.status}</span>
                </div>
        `;
        
        // Render tools under this agent
        if (hasTools && isExpanded) {
            html += '<div class="tree-children">';
            for (let tool of agent.tools) {
                html += this.renderToolElement(tool, level + 1);
            }
            html += '</div>';
        }
        
        html += '</div>';
        return html;
    }

    /**
     * Render tool element (non-expandable, clickable to show data)
     */
    renderToolElement(tool, level) {
        const statusClass = `status-${tool.status}`;
        const params = this.getToolParams(tool);
        const isSelected = this.selectedItem && this.selectedItem.type === 'tool' && this.selectedItem.data.id === tool.id;
        const selectedClass = isSelected ? 'selected' : '';
        
        let html = `
            <div class="tree-node tool ${statusClass} ${selectedClass}" data-level="${level}">
                <div class="tree-node-content">
                    <span class="tree-expand-icon"></span>
                    <span class="tree-icon">${tool.icon}</span>
                    <span class="tree-label clickable" onclick="window.activityTreeInstance.selectItem(${this.escapeJson(tool)}, 'tool', event)">${tool.name} (click to view details)</span>
                    <span class="tree-params">${params}</span>
                    <span class="tree-status ${statusClass}">${tool.status}</span>
                </div>
            </div>
        `;
        
        return html;
    }

    /**
     * Get formatted tool parameters
     */
    getToolParams(tool) {
        if (!tool.params) return '';
        
        if (tool.name === 'Read' && tool.params.file_path) {
            return tool.params.file_path;
        }
        if (tool.name === 'Edit' && tool.params.file_path) {
            return tool.params.file_path;
        }
        if (tool.name === 'Write' && tool.params.file_path) {
            return tool.params.file_path;
        }
        if (tool.name === 'Bash' && tool.params.command) {
            const cmd = tool.params.command;
            return cmd.length > 50 ? cmd.substring(0, 50) + '...' : cmd;
        }
        if (tool.name === 'WebFetch' && tool.params.url) {
            return tool.params.url;
        }
        
        return '';
    }

    /**
     * Get status icon for todo status
     */
    getStatusIcon(status) {
        const icons = {
            'pending': '⏸️',
            'in_progress': '🔄',
            'completed': '✅'
        };
        return icons[status] || '❓';
    }

    /**
     * Get checkbox icon for todo checklist items
     */
    getCheckboxIcon(status) {
        const icons = {
            'pending': '⏳',
            'in_progress': '🔄',
            'completed': '✅'
        };
        return icons[status] || '❓';
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
     * Toggle session expansion
     */
    toggleSession(sessionId) {
        if (this.expandedSessions.has(sessionId)) {
            this.expandedSessions.delete(sessionId);
        } else {
            this.expandedSessions.add(sessionId);
        }
        
        // Update the session in the data structure
        const session = this.sessions.get(sessionId);
        if (session) {
            session.expanded = this.expandedSessions.has(sessionId);
        }
        
        this.renderTree();
    }

    /**
     * Expand all sessions
     */
    expandAllSessions() {
        for (let sessionId of this.sessions.keys()) {
            this.expandedSessions.add(sessionId);
            const session = this.sessions.get(sessionId);
            if (session) session.expanded = true;
        }
        this.renderTree();
    }

    /**
     * Collapse all sessions
     */
    collapseAllSessions() {
        this.expandedSessions.clear();
        for (let session of this.sessions.values()) {
            session.expanded = false;
        }
        this.renderTree();
    }


    /**
     * Update statistics
     */
    updateStats() {
        const totalNodes = this.countTotalNodes();
        const activeNodes = this.countActiveNodes();
        const maxDepth = this.calculateMaxDepth();

        const nodeCountEl = document.getElementById('node-count');
        const activeCountEl = document.getElementById('active-count');
        const depthEl = document.getElementById('tree-depth');
        
        if (nodeCountEl) nodeCountEl.textContent = totalNodes;
        if (activeCountEl) activeCountEl.textContent = activeNodes;
        if (depthEl) depthEl.textContent = maxDepth;
        
        console.log(`ActivityTree: Stats updated - Nodes: ${totalNodes}, Active: ${activeNodes}, Depth: ${maxDepth}`);
    }

    /**
     * Count total nodes across all sessions
     */
    countTotalNodes() {
        let count = 0; // No project root anymore
        for (let session of this.sessions.values()) {
            count += 1; // Session
            count += session.agents.size; // Agents
            
            // Count user instructions
            if (session.userInstructions) {
                count += session.userInstructions.length;
            }
            
            // Count todos
            if (session.todos) {
                count += session.todos.length;
            }
            
            // Count session-level tools
            if (session.tools) {
                count += session.tools.length;
            }
            
            // Count tools in agents
            for (let agent of session.agents.values()) {
                if (agent.tools) {
                    count += agent.tools.length;
                }
            }
        }
        return count;
    }

    /**
     * Count active nodes (in progress)
     */
    countActiveNodes() {
        let count = 0;
        for (let session of this.sessions.values()) {
            // Count active session
            if (session.status === 'active') count++;
            
            // Count active todos
            if (session.todos) {
                for (let todo of session.todos) {
                    if (todo.status === 'in_progress') count++;
                }
            }
            
            // Count session-level tools
            if (session.tools) {
                for (let tool of session.tools) {
                    if (tool.status === 'in_progress') count++;
                }
            }
            
            // Count agents and their tools
            for (let agent of session.agents.values()) {
                if (agent.status === 'active') count++;
                if (agent.tools) {
                    for (let tool of agent.tools) {
                        if (tool.status === 'in_progress') count++;
                    }
                }
            }
        }
        return count;
    }

    /**
     * Calculate maximum depth
     */
    calculateMaxDepth() {
        let maxDepth = 0; // No project root anymore
        for (let session of this.sessions.values()) {
            let sessionDepth = 1; // Session level (now root level)
            
            // Check session content (instructions, todos, tools)
            if (session.userInstructions && session.userInstructions.length > 0) {
                sessionDepth = Math.max(sessionDepth, 2); // Instruction level
            }
            
            if (session.todos && session.todos.length > 0) {
                sessionDepth = Math.max(sessionDepth, 3); // Todo checklist -> todo items
            }
            
            if (session.tools && session.tools.length > 0) {
                sessionDepth = Math.max(sessionDepth, 2); // Tool level
            }
            
            // Check agents
            for (let agent of session.agents.values()) {
                if (agent.tools && agent.tools.length > 0) {
                    sessionDepth = Math.max(sessionDepth, 3); // Tool level under agents
                }
            }
            
            maxDepth = Math.max(maxDepth, sessionDepth);
        }
        return maxDepth;
    }

    /**
     * Toggle agent expansion
     */
    toggleAgent(agentId) {
        if (this.expandedAgents.has(agentId)) {
            this.expandedAgents.delete(agentId);
        } else {
            this.expandedAgents.add(agentId);
        }
        this.renderTree();
    }
    
    /**
     * Toggle tool expansion (deprecated - tools are no longer expandable)
     */
    toggleTool(toolId) {
        // Tools are no longer expandable - this method is kept for compatibility
        console.log('Tool expansion is disabled. Tools now show data in the left pane when clicked.');
    }

    /**
     * Toggle TODO checklist expansion
     */
    toggleTodoChecklist(checklistId) {
        if (this.expandedTools.has(checklistId)) {
            this.expandedTools.delete(checklistId);
        } else {
            this.expandedTools.add(checklistId);
        }
        this.renderTree();
    }

    /**
     * Handle item click to show data in left pane
     */
    selectItem(item, itemType, event) {
        // Stop event propagation to prevent expand/collapse when clicking on label
        if (event) {
            event.stopPropagation();
        }
        
        this.selectedItem = { data: item, type: itemType };
        this.displayItemData(item, itemType);
        this.renderTree(); // Re-render to show selection highlight
    }

    /**
     * Display item data in left pane using simple display methods
     */
    displayItemData(item, itemType) {
        // Special handling for TodoWrite tools to match Tools view display
        if (itemType === 'tool' && item.name === 'TodoWrite' && item.params && item.params.todos) {
            this.displayTodoWriteData(item);
            return;
        }
        
        // Use simple display methods based on item type
        switch(itemType) {
            case 'agent':
                this.displayAgentData(item);
                break;
            case 'tool':
                this.displayToolData(item);
                break;
            case 'instruction':
                this.displayInstructionData(item);
                break;
            default:
                this.displayGenericData(item, itemType);
                break;
        }
        
        // Update module header for consistency
        const moduleHeader = document.querySelector('.module-data-header h5');
        if (moduleHeader) {
            const icons = {
                'agent': '🤖',
                'tool': '🔧', 
                'instruction': '💬',
                'session': '🎯'
            };
            const icon = icons[itemType] || '📊';
            const name = item.name || item.agentName || item.tool_name || 'Item';
            moduleHeader.textContent = `${icon} ${itemType}: ${name}`;
        }
    }

    /**
     * Display TodoWrite data in the same clean format as Tools view
     */
    displayTodoWriteData(item) {
        const todos = item.params.todos || [];
        const timestamp = this.formatTimestamp(item.timestamp);
        
        // Calculate status summary
        let completedCount = 0;
        let inProgressCount = 0;
        let pendingCount = 0;
        
        todos.forEach(todo => {
            if (todo.status === 'completed') completedCount++;
            else if (todo.status === 'in_progress') inProgressCount++;
            else pendingCount++;
        });
        
        let html = `
            <div class="unified-viewer-header">
                <h6>📝 TodoWrite: PM ${timestamp}</h6>
                <span class="unified-viewer-status">${this.formatStatus(item.status)}</span>
            </div>
            <div class="unified-viewer-content">
        `;

        if (todos.length > 0) {
            // Status summary 
            html += `
                <div class="detail-section">
                    <span class="detail-section-title">Todo Summary</span>
                    <div class="todo-summary">
                        <div class="summary-item completed">
                            <span class="summary-icon">✅</span>
                            <span class="summary-count">${completedCount}</span>
                            <span class="summary-label">Completed</span>
                        </div>
                        <div class="summary-item in_progress">
                            <span class="summary-icon">🔄</span>
                            <span class="summary-count">${inProgressCount}</span>
                            <span class="summary-label">In Progress</span>
                        </div>
                        <div class="summary-item pending">
                            <span class="summary-icon">⏳</span>
                            <span class="summary-count">${pendingCount}</span>
                            <span class="summary-label">Pending</span>
                        </div>
                    </div>
                </div>
            `;

            // Todo list display (same as Tools view)
            html += `
                <div class="detail-section">
                    <span class="detail-section-title">Todo List (${todos.length} items)</span>
                    <div class="todo-checklist">
            `;
            
            todos.forEach((todo, index) => {
                const statusIcon = this.getCheckboxIcon(todo.status);
                const displayText = todo.status === 'in_progress' ? 
                    (todo.activeForm || todo.content) : todo.content;
                const statusClass = this.formatStatusClass(todo.status);
                
                html += `
                    <div class="todo-checklist-item ${todo.status}">
                        <div class="todo-checkbox">
                            <span class="checkbox-icon ${statusClass}">${statusIcon}</span>
                        </div>
                        <div class="todo-text">
                            <span class="todo-content">${this.escapeHtml(displayText)}</span>
                            <span class="todo-status-badge ${statusClass}">${todo.status.replace('_', ' ')}</span>
                        </div>
                    </div>
                `;
            });
            
            html += `
                    </div>
                </div>
            `;
        } else {
            html += `
                <div class="detail-section">
                    <div class="no-todos">No todo items found</div>
                </div>
            `;
        }

        // Add raw JSON section at the bottom
        html += `
            <div class="detail-section">
                <span class="detail-section-title">Parameters (${Object.keys(item.params).length})</span>
                <div class="params-list">
                    <div class="param-item">
                        <div class="param-key">todos:</div>
                        <div class="param-value">
                            <pre class="param-json">${this.escapeHtml(JSON.stringify(todos, null, 2))}</pre>
                        </div>
                    </div>
                </div>
            </div>
        `;

        html += '</div>';
        
        // Set the content directly
        const container = document.getElementById('module-data-content');
        if (container) {
            container.innerHTML = html;
        }

        // Update module header 
        const moduleHeader = document.querySelector('.module-data-header h5');
        if (moduleHeader) {
            moduleHeader.textContent = `📝 tool: TodoWrite`;
        }
    }

    // Utility methods for TodoWrite display
    formatStatus(status) {
        if (!status) return 'unknown';
        
        const statusMap = {
            'active': '🟢 Active',
            'completed': '✅ Completed', 
            'in_progress': '🔄 In Progress',
            'pending': '⏳ Pending',
            'error': '❌ Error',
            'failed': '❌ Failed'
        };
        
        return statusMap[status] || status;
    }

    formatStatusClass(status) {
        return `status-${status}`;
    }

    formatTimestamp(timestamp) {
        if (!timestamp) return '';
        
        try {
            const date = new Date(timestamp);
            if (isNaN(date.getTime())) return '';
            return date.toLocaleTimeString();
        } catch (error) {
            return '';
        }
    }

    /**
     * Display agent data in a simple format
     */
    displayAgentData(agent) {
        const timestamp = this.formatTimestamp(agent.timestamp);
        const container = document.getElementById('module-data-content');
        if (!container) return;

        let html = `
            <div class="detail-section">
                <span class="detail-section-title">Agent Information</span>
                <div class="agent-info">
                    <div class="info-item">
                        <span class="info-label">Name:</span>
                        <span class="info-value">${this.escapeHtml(agent.name)}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Status:</span>
                        <span class="info-value status-${agent.status}">${agent.status}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Timestamp:</span>
                        <span class="info-value">${timestamp}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Session ID:</span>
                        <span class="info-value">${agent.sessionId || 'N/A'}</span>
                    </div>
                </div>
            </div>
        `;

        if (agent.tools && agent.tools.length > 0) {
            html += `
                <div class="detail-section">
                    <span class="detail-section-title">Tools (${agent.tools.length})</span>
                    <div class="tool-list">
            `;
            
            agent.tools.forEach(tool => {
                html += `
                    <div class="tool-item">
                        <span class="tool-name">${this.escapeHtml(tool.name)}</span>
                        <span class="tool-status status-${tool.status}">${tool.status}</span>
                    </div>
                `;
            });
            
            html += `
                    </div>
                </div>
            `;
        }

        container.innerHTML = html;
    }

    /**
     * Display tool data in a simple format
     */
    displayToolData(tool) {
        const timestamp = this.formatTimestamp(tool.timestamp);
        const container = document.getElementById('module-data-content');
        if (!container) return;

        let html = `
            <div class="detail-section">
                <span class="detail-section-title">Tool Information</span>
                <div class="tool-info">
                    <div class="info-item">
                        <span class="info-label">Name:</span>
                        <span class="info-value">${this.escapeHtml(tool.name)}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Status:</span>
                        <span class="info-value status-${tool.status}">${tool.status}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Timestamp:</span>
                        <span class="info-value">${timestamp}</span>
                    </div>
                </div>
            </div>
        `;

        if (tool.params && Object.keys(tool.params).length > 0) {
            html += `
                <div class="detail-section">
                    <span class="detail-section-title">Parameters</span>
                    <div class="params-list">
            `;
            
            Object.entries(tool.params).forEach(([key, value]) => {
                html += `
                    <div class="param-item">
                        <div class="param-key">${this.escapeHtml(key)}:</div>
                        <div class="param-value">${this.escapeHtml(String(value))}</div>
                    </div>
                `;
            });
            
            html += `
                    </div>
                </div>
            `;
        }

        container.innerHTML = html;
    }

    /**
     * Display instruction data in a simple format
     */
    displayInstructionData(instruction) {
        const timestamp = this.formatTimestamp(instruction.timestamp);
        const container = document.getElementById('module-data-content');
        if (!container) return;

        const html = `
            <div class="detail-section">
                <span class="detail-section-title">User Instruction</span>
                <div class="instruction-info">
                    <div class="info-item">
                        <span class="info-label">Timestamp:</span>
                        <span class="info-value">${timestamp}</span>
                    </div>
                    <div class="instruction-content">
                        <div class="instruction-text">${this.escapeHtml(instruction.text)}</div>
                    </div>
                </div>
            </div>
        `;

        container.innerHTML = html;
    }

    /**
     * Display generic data for unknown types
     */
    displayGenericData(item, itemType) {
        const container = document.getElementById('module-data-content');
        if (!container) return;

        let html = `
            <div class="detail-section">
                <span class="detail-section-title">${itemType || 'Item'} Data</span>
                <div class="generic-data">
                    <pre>${this.escapeHtml(JSON.stringify(item, null, 2))}</pre>
                </div>
            </div>
        `;

        container.innerHTML = html;
    }

    /**
     * Escape HTML for safe display
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Reset zoom and pan to initial state
     */
    resetZoom() {
        if (this.svg && this.zoom) {
            this.svg.transition()
                .duration(this.duration)
                .call(this.zoom.transform, d3.zoomIdentity);
        }
    }
    
    /**
     * Escape JSON for safe inclusion in HTML attributes
     */
    escapeJson(obj) {
        return JSON.stringify(obj).replace(/'/g, '&apos;').replace(/"/g, '&quot;');
    }
}

// Make ActivityTree globally available
window.ActivityTree = ActivityTree;

// Initialize when the Activity tab is selected
const setupActivityTreeListeners = () => {
    let activityTree = null;

    const initializeActivityTree = () => {
        if (!activityTree) {
            console.log('Creating new Activity Tree instance...');
            activityTree = new ActivityTree();
            window.activityTreeInstance = activityTree;
            window.activityTree = () => activityTree; // For debugging
        }
        
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
                if (activityTree) {
                    setTimeout(() => {
                        activityTree.renderWhenVisible();
                        activityTree.forceShow();
                    }, 150);
                }
            }
        });
    });

    // Listen for custom tab change events
    document.addEventListener('tabChanged', (e) => {
        if (e.detail && e.detail.newTab === 'activity') {
            console.log('Tab changed to activity, initializing tree...');
            initializeActivityTree();
            if (activityTree) {
                setTimeout(() => {
                    activityTree.renderWhenVisible();
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
    
    const activityPanel = document.getElementById('activity-tab');
    if (activityPanel && activityPanel.classList.contains('active')) {
        console.log('Activity panel is active on load, initializing tree...');
        if (!activityTree) {
            initializeActivityTree();
        }
    }
};

// Set up listeners when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupActivityTreeListeners);
} else {
    setupActivityTreeListeners();
}

export { ActivityTree };
export default ActivityTree;