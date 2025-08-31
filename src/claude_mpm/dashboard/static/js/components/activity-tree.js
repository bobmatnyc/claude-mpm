/**
 * Activity Tree Component - Linear Tree View
 * 
 * HTML/CSS-based linear tree visualization for showing PM activity hierarchy.
 * Replaces D3.js with simpler, cleaner linear tree structure.
 * Uses UnifiedDataViewer for consistent data display with Tools viewer.
 */

// Import UnifiedDataViewer for consistent data display
import { UnifiedDataViewer } from './unified-data-viewer.js';

class ActivityTree {
    constructor() {
        this.container = null;
        this.events = [];
        this.processedEventIds = new Set(); // Track which events we've already processed
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
        this.sessionFilterInitialized = false; // Flag to prevent initialization loop
        
        // Add debounce for renderTree to prevent excessive DOM rebuilds
        this.renderTreeDebounced = this.debounce(() => this.renderTree(), 100);
    }
    
    /**
     * Debounce helper to prevent excessive DOM updates
     */
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
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

        // Initialize with current session filter from SessionManager (prevent loop)
        setTimeout(() => {
            if (window.sessionManager && !this.sessionFilterInitialized) {
                const currentFilter = window.sessionManager.getCurrentFilter();
                if (currentFilter !== this.selectedSessionFilter) {
                    this.selectedSessionFilter = currentFilter || 'all';
                    console.log(`ActivityTree: Initialized with current session filter: ${this.selectedSessionFilter}`);
                    this.sessionFilterInitialized = true; // Prevent re-initialization
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
            
            // IMPORTANT: Don't clear sessions! We need to preserve the accumulated agent data
            // Only create new sessions if they don't exist yet
            for (const [sessionId, sessionData] of sessions.entries()) {
                if (!this.sessions.has(sessionId)) {
                    // Create new session only if it doesn't exist
                    const activitySession = {
                        id: sessionId,
                        timestamp: new Date(sessionData.lastActivity || sessionData.startTime || new Date()),
                        expanded: this.expandedSessions.has(sessionId) || true, // Preserve expansion state
                        agents: new Map(),
                        todos: [],
                        userInstructions: [],
                        tools: [],
                        toolsMap: new Map(),
                        status: 'active',
                        currentTodoTool: null,
                        // Preserve additional session metadata
                        working_directory: sessionData.working_directory,
                        git_branch: sessionData.git_branch,
                        eventCount: sessionData.eventCount
                    };
                    this.sessions.set(sessionId, activitySession);
                } else {
                    // Update existing session metadata without clearing accumulated data
                    // CRITICAL: Preserve all accumulated data (tools, agents, todos, etc.)
                    const existingSession = this.sessions.get(sessionId);
                    existingSession.timestamp = new Date(sessionData.lastActivity || sessionData.startTime || existingSession.timestamp);
                    existingSession.eventCount = sessionData.eventCount;
                    existingSession.status = sessionData.status || existingSession.status;
                    // Update metadata without losing accumulated data
                    existingSession.working_directory = sessionData.working_directory || existingSession.working_directory;
                    existingSession.git_branch = sessionData.git_branch || existingSession.git_branch;
                    // DO NOT reset tools, agents, todos, userInstructions, toolsMap, etc.
                    // These are built up from events and must be preserved!
                }
            }
            
            // Process only events we haven't seen before
            const newEvents = events.filter(event => {
                const eventId = event.id || `${event.type}-${event.timestamp}-${Math.random()}`;
                return !this.processedEventIds.has(eventId);
            });
            
            if (newEvents.length > 0) {
                console.log(`ActivityTree: Processing ${newEvents.length} new events`, newEvents);
                
                newEvents.forEach(event => {
                    const eventId = event.id || `${event.type}-${event.timestamp}-${Math.random()}`;
                    this.processedEventIds.add(eventId);
                    this.processEvent(event);
                });
            }
                
            this.events = [...events];
            // Use debounced render to prevent excessive DOM rebuilds
            this.renderTreeDebounced();
            
            // Debug: Log session state after processing
            console.log(`ActivityTree: Sessions after sync with socket client:`, Array.from(this.sessions.entries()));
        });

        // Load existing data from socket client
        const socketState = window.socketClient?.getState();
        
        if (socketState && socketState.events.length > 0) {
            console.log(`ActivityTree: Loading existing data - ${socketState.events.length} events, ${socketState.sessions.size} sessions`);
            
            // Initialize from existing socket client data
            // Don't clear existing sessions - preserve accumulated data
            
            // Convert authoritative sessions Map to our format
            for (const [sessionId, sessionData] of socketState.sessions.entries()) {
                if (!this.sessions.has(sessionId)) {
                    const activitySession = {
                        id: sessionId,
                        timestamp: new Date(sessionData.lastActivity || sessionData.startTime || new Date()),
                        expanded: this.expandedSessions.has(sessionId) || true,
                        agents: new Map(),
                        todos: [],
                        userInstructions: [],
                        tools: [],
                        toolsMap: new Map(),
                        status: 'active',
                        currentTodoTool: null,
                        working_directory: sessionData.working_directory,
                        git_branch: sessionData.git_branch,
                        eventCount: sessionData.eventCount
                    };
                    this.sessions.set(sessionId, activitySession);
                }
            }
            
            // Process only events we haven't seen before
            const unprocessedEvents = socketState.events.filter(event => {
                const eventId = event.id || `${event.type}-${event.timestamp}-${Math.random()}`;
                return !this.processedEventIds.has(eventId);
            });
            
            if (unprocessedEvents.length > 0) {
                console.log(`ActivityTree: Processing ${unprocessedEvents.length} unprocessed events from initial load`);
                unprocessedEvents.forEach(event => {
                    const eventId = event.id || `${event.type}-${event.timestamp}-${Math.random()}`;
                    this.processedEventIds.add(eventId);
                    this.processEvent(event);
                });
            }
            
            this.events = [...socketState.events];
            // Initial render can be immediate
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
                // TodoWrite is now handled as a tool in 'tool_use' events
                // Skip separate TodoWrite processing to avoid duplication
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
        
        // NEW USER PROMPT: Only collapse agents if we have existing ones
        // Don't clear - we want to keep the history!
        if (session.agents.size > 0) {
            console.log('ActivityTree: New user prompt detected, collapsing previous agents');
            
            // Mark all existing agents as completed (not active)
            for (let agent of session.agents.values()) {
                if (agent.status === 'active') {
                    agent.status = 'completed';
                }
                // Collapse all existing agents
                this.expandedAgents.delete(agent.id);
            }
        }
        
        // Reset current active agent for new work
        session.currentActiveAgent = null;
        
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

        // Update session's current todos for latest state tracking
        session.currentTodos = todos.map(todo => ({
            content: todo.content,
            activeForm: todo.activeForm,
            status: todo.status,
            timestamp: event.timestamp
        }));

        // Find the appropriate agent to attach this TodoWrite to
        let targetAgent = session.currentActiveAgent;
        
        if (!targetAgent) {
            // Fall back to most recent active agent
            const activeAgents = this.getAllAgents(session)
                .filter(agent => agent.status === 'active' || agent.status === 'in_progress')
                .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
            
            if (activeAgents.length > 0) {
                targetAgent = activeAgents[0];
            } else {
                // If no active agents, check if this is PM-level
                const allAgents = this.getAllAgents(session);
                const pmAgent = allAgents.find(a => a.isPM);
                if (pmAgent) {
                    targetAgent = pmAgent;
                } else if (allAgents.length > 0) {
                    targetAgent = allAgents[0];
                }
            }
        }

        // Attach or update TodoWrite for the agent
        if (targetAgent) {
            if (!targetAgent.todoWritesMap) {
                targetAgent.todoWritesMap = new Map();
            }
            if (!targetAgent.todoWrites) {
                targetAgent.todoWrites = [];
            }
            
            // Check if we already have a TodoWrite instance
            const existingTodoWrite = targetAgent.todoWritesMap.get('TodoWrite');
            
            if (existingTodoWrite) {
                // Update existing TodoWrite instance
                existingTodoWrite.todos = todos;
                existingTodoWrite.timestamp = event.timestamp;
                existingTodoWrite.updateCount = (existingTodoWrite.updateCount || 1) + 1;
            } else {
                // Create new TodoWrite instance
                const todoWriteInstance = {
                    id: `todowrite-${targetAgent.id}-${Date.now()}`,
                    name: 'TodoWrite',
                    type: 'todowrite',
                    icon: '📝',
                    timestamp: event.timestamp,
                    status: 'completed',
                    todos: todos,
                    params: {
                        todos: todos
                    },
                    updateCount: 1
                };
                
                targetAgent.todoWritesMap.set('TodoWrite', todoWriteInstance);
                targetAgent.todoWrites = [todoWriteInstance]; // Keep single instance
            }
            
            // Update agent's current todos for display when collapsed
            targetAgent.currentTodos = todos;
        } else {
            // No agent found, attach to session level
            if (!session.todoWrites) {
                session.todoWrites = [];
            }
            if (!session.todoWritesMap) {
                session.todoWritesMap = new Map();
            }
            
            const existingTodoWrite = session.todoWritesMap.get('TodoWrite');
            if (existingTodoWrite) {
                existingTodoWrite.todos = todos;
                existingTodoWrite.timestamp = event.timestamp;
                existingTodoWrite.updateCount = (existingTodoWrite.updateCount || 1) + 1;
            } else {
                const todoWriteInstance = {
                    id: `todowrite-session-${Date.now()}`,
                    name: 'TodoWrite',
                    type: 'todowrite',
                    icon: '📝',
                    timestamp: event.timestamp,
                    status: 'completed',
                    todos: todos,
                    updateCount: 1
                };
                session.todoWritesMap.set('TodoWrite', todoWriteInstance);
                session.todoWrites = [todoWriteInstance];
            }
        }
    }

    /**
     * Process SubagentStart event
     */
    processSubagentStart(event, session) {
        const agentName = event.agent_name || event.data?.agent_name || event.data?.agent_type || event.agent_type || event.agent || 'unknown';
        const agentSessionId = event.session_id || event.data?.session_id;
        const parentAgent = event.parent_agent || event.data?.parent_agent;
        
        // Use a composite key based on agent name and session to find existing instances
        // This ensures we track unique agent instances per session
        const agentKey = `${agentName}-${agentSessionId || 'no-session'}`;
        
        // Check if this exact agent already exists (same name and session)
        let existingAgent = null;
        const allAgents = this.getAllAgents(session);
        existingAgent = allAgents.find(a => 
            a.name === agentName && 
            a.sessionId === agentSessionId &&
            a.status === 'active'  // Only reuse if still active
        );
        
        let agent;
        if (existingAgent) {
            // Update existing active agent
            agent = existingAgent;
            agent.timestamp = event.timestamp;
            agent.instanceCount = (agent.instanceCount || 1) + 1;
            // Auto-expand the active agent
            this.expandedAgents.add(agent.id);
        } else {
            // Create new agent instance for first occurrence
            const agentId = `agent-${agentKey}-${Date.now()}`;
            agent = {
                id: agentId,
                name: agentName,
                type: 'agent',
                icon: this.getAgentIcon(agentName),
                timestamp: event.timestamp,
                status: 'active',
                tools: [],
                subagents: new Map(),  // Store nested subagents
                sessionId: agentSessionId,
                parentAgent: parentAgent,
                isPM: agentName.toLowerCase() === 'pm' || agentName.toLowerCase().includes('project manager'),
                instanceCount: 1,
                toolsMap: new Map() // Track unique tools by name
            };
            
            // If this is a subagent, nest it under the parent agent
            if (parentAgent) {
                // Find the parent agent in the session
                let parent = null;
                for (let [id, ag] of session.agents.entries()) {
                    if (ag.sessionId === parentAgent || ag.name === parentAgent) {
                        parent = ag;
                        break;
                    }
                }
                
                if (parent) {
                    // Add as nested subagent
                    if (!parent.subagents) {
                        parent.subagents = new Map();
                    }
                    parent.subagents.set(agent.id, agent);
                } else {
                    // No parent found, add to session level
                    session.agents.set(agent.id, agent);
                }
            } else {
                // Top-level agent, add to session
                session.agents.set(agent.id, agent);
            }
            
            // Auto-expand new agents
            this.expandedAgents.add(agent.id);
        }
        
        // Track the currently active agent for tool/todo association
        session.currentActiveAgent = agent;
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
     * 
     * DISPLAY RULES:
     * 1. TodoWrite is a privileged tool that ALWAYS appears first under the agent/PM
     * 2. Each tool appears only once per unique instance (updated in place)
     * 3. Tools are listed in order of creation (after TodoWrite)
     * 4. Tool instances are updated with new events as they arrive
     */
    processToolUse(event, session) {
        const toolName = event.tool_name || event.data?.tool_name || event.tool || event.data?.tool || 'unknown';
        const params = event.tool_parameters || event.data?.tool_parameters || event.parameters || event.data?.parameters || {};
        const agentSessionId = event.session_id || event.data?.session_id;

        // Find the appropriate agent to attach this tool to
        let targetAgent = session.currentActiveAgent;
        
        if (!targetAgent) {
            // Fall back to finding by session ID or most recent active
            const allAgents = this.getAllAgents(session);
            targetAgent = allAgents.find(a => a.sessionId === agentSessionId) ||
                         allAgents.find(a => a.status === 'active') ||
                         allAgents[0];
        }

        if (targetAgent) {
            if (!targetAgent.toolsMap) {
                targetAgent.toolsMap = new Map();
            }
            if (!targetAgent.tools) {
                targetAgent.tools = [];
            }
            
            // Check if we already have this tool instance
            // Use tool name + params hash for unique identification
            const toolKey = this.getToolKey(toolName, params);
            let existingTool = targetAgent.toolsMap.get(toolKey);
            
            if (existingTool) {
                // UPDATE RULE: Update existing tool instance in place
                existingTool.params = params;
                existingTool.timestamp = event.timestamp;
                existingTool.status = 'in_progress';
                existingTool.eventId = event.id;
                existingTool.callCount = (existingTool.callCount || 1) + 1;
                
                // Update current tool for collapsed display
                targetAgent.currentTool = existingTool;
            } else {
                // CREATE RULE: Create new tool instance
                const tool = {
                    id: `tool-${targetAgent.id}-${toolName}-${Date.now()}`,
                    name: toolName,
                    type: 'tool',
                    icon: this.getToolIcon(toolName),
                    timestamp: event.timestamp,
                    status: 'in_progress',
                    params: params,
                    eventId: event.id,
                    callCount: 1,
                    createdAt: event.timestamp  // Track creation order
                };
                
                // Special handling for Task tool (subagent delegation)
                if (toolName === 'Task' && params.subagent_type) {
                    tool.isSubagentTask = true;
                    tool.subagentType = params.subagent_type;
                }
                
                targetAgent.toolsMap.set(toolKey, tool);
                
                // ORDERING RULE: TodoWrite always goes first, others in creation order
                if (toolName === 'TodoWrite') {
                    // Insert TodoWrite at the beginning
                    targetAgent.tools.unshift(tool);
                } else {
                    // Append other tools in creation order
                    targetAgent.tools.push(tool);
                }
                
                targetAgent.currentTool = tool;
            }
        } else {
            // No agent found, attach to session (PM level)
            // PM RULE: Same display rules apply - TodoWrite first, others in creation order
            if (!session.tools) {
                session.tools = [];
            }
            if (!session.toolsMap) {
                session.toolsMap = new Map();
            }
            
            const toolKey = this.getToolKey(toolName, params);
            let existingTool = session.toolsMap.get(toolKey);
            
            if (existingTool) {
                // UPDATE RULE: Update existing tool instance in place
                existingTool.params = params;
                existingTool.timestamp = event.timestamp;
                existingTool.status = 'in_progress';
                existingTool.eventId = event.id;
                existingTool.callCount = (existingTool.callCount || 1) + 1;
                session.currentTool = existingTool;
            } else {
                const tool = {
                    id: `tool-session-${toolName}-${Date.now()}`,
                    name: toolName,
                    type: 'tool',
                    icon: this.getToolIcon(toolName),
                    timestamp: event.timestamp,
                    status: 'in_progress',
                    params: params,
                    eventId: event.id,
                    callCount: 1,
                    createdAt: event.timestamp  // Track creation order
                };
                
                session.toolsMap.set(toolKey, tool);
                
                // ORDERING RULE: TodoWrite always goes first for PM too
                if (toolName === 'TodoWrite') {
                    session.tools.unshift(tool);
                } else {
                    session.tools.push(tool);
                }
                
                session.currentTool = tool;
            }
        }
    }

    /**
     * Generate unique key for tool instance identification
     * Tools are unique per name + certain parameter combinations
     */
    getToolKey(toolName, params) {
        // For TodoWrite, we want ONE instance per agent/PM that updates in place
        // So we use just the tool name as the key
        if (toolName === 'TodoWrite') {
            return 'TodoWrite';  // Single instance per agent/PM
        }
        
        // For other tools, we generally want one instance per tool type
        // that gets updated with each call (not creating new instances)
        let key = toolName;
        
        // Only add distinguishing params if we need multiple instances
        // For example, multiple files being edited simultaneously
        if (toolName === 'Edit' || toolName === 'Write' || toolName === 'Read') {
            if (params.file_path) {
                key += `-${params.file_path}`;
            }
        }
        
        // For search tools, we might want separate instances for different searches
        if ((toolName === 'Grep' || toolName === 'Glob') && params.pattern) {
            // Only add pattern if significantly different
            key += `-${params.pattern.substring(0, 20)}`;
        }
        
        // Most tools should have a single instance that updates
        // This prevents the tool list from growing unbounded
        return key;
    }

    /**
     * Update tool status after completion
     */
    updateToolStatus(event, session, status) {
        const toolName = event.tool_name || event.data?.tool_name || event.tool || 'unknown';
        const params = event.tool_parameters || event.data?.tool_parameters || event.parameters || event.data?.parameters || {};
        const agentSessionId = event.session_id || event.data?.session_id;
        
        // Generate the same key we used to store the tool
        const toolKey = this.getToolKey(toolName, params);
        
        // Find the appropriate agent
        let targetAgent = session.currentActiveAgent;
        
        if (!targetAgent) {
            const allAgents = this.getAllAgents(session);
            targetAgent = allAgents.find(a => a.sessionId === agentSessionId) ||
                         allAgents.find(a => a.status === 'active');
        }
        
        if (targetAgent && targetAgent.toolsMap) {
            const tool = targetAgent.toolsMap.get(toolKey);
            if (tool) {
                tool.status = status;
                tool.completedAt = event.timestamp;
                if (event.data?.result || event.result) {
                    tool.result = event.data?.result || event.result;
                }
                if (event.data?.duration_ms) {
                    tool.duration = event.data.duration_ms;
                }
                return;
            }
        }
        
        // Check session-level tools
        if (session.toolsMap) {
            const tool = session.toolsMap.get(toolKey);
            if (tool) {
                tool.status = status;
                tool.completedAt = event.timestamp;
                if (event.data?.result || event.result) {
                    tool.result = event.data?.result || event.result;
                }
                if (event.data?.duration_ms) {
                    tool.duration = event.data.duration_ms;
                }
                return;
            }
        }
        
        console.log(`ActivityTree: Could not find tool to update status for ${toolName} with key ${toolKey} (event ${event.id})`);
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
        // Count ALL agents including nested ones
        const agentCount = this.getAllAgents(session).length;
        const todoCount = session.currentTodos ? session.currentTodos.length : 0;
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
     * 
     * PM DISPLAY RULES (documented inline):
     * 1. User instructions appear first (context)
     * 2. PM-level tools follow the same rules as agent tools:
     *    - TodoWrite is privileged and appears first
     *    - Other tools appear in creation order
     *    - Each unique instance is updated in place
     * 3. Agents appear after PM tools
     */
    renderSessionContent(session) {
        let html = '';
        
        // Render user instructions first
        if (session.userInstructions && session.userInstructions.length > 0) {
            for (let instruction of session.userInstructions.slice(-3)) { // Show last 3 instructions
                html += this.renderUserInstructionElement(instruction, 1);
            }
        }
        
        // PM TOOL DISPLAY RULES:
        // Render PM-level tools (TodoWrite first, then others in creation order)
        // The session.tools array is already properly ordered by processToolUse
        if (session.tools && session.tools.length > 0) {
            for (let tool of session.tools) {
                html += this.renderToolElement(tool, 1);
            }
        }
        
        // Render agents (they will have their own TodoWrite at the top)
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
     * Render agent element with proper nesting
     */
    renderAgentElement(agent, level) {
        const statusClass = agent.status === 'active' ? 'status-active' : 'status-completed';
        const isExpanded = this.expandedAgents.has(agent.id);
        const hasTools = agent.tools && agent.tools.length > 0;
        const hasSubagents = agent.subagents && agent.subagents.size > 0;
        const hasContent = hasTools || hasSubagents;
        const isSelected = this.selectedItem && this.selectedItem.type === 'agent' && this.selectedItem.data.id === agent.id;
        
        const expandIcon = hasContent ? (isExpanded ? '▼' : '▶') : '';
        const selectedClass = isSelected ? 'selected' : '';
        
        // Add instance count if called multiple times
        const instanceIndicator = agent.instanceCount > 1 ? ` (${agent.instanceCount}x)` : '';
        
        // Build status display for collapsed state
        let collapsedStatus = '';
        if (!isExpanded && hasContent) {
            const parts = [];
            if (agent.currentTodos && agent.currentTodos.length > 0) {
                const inProgress = agent.currentTodos.find(t => t.status === 'in_progress');
                if (inProgress) {
                    parts.push(`📝 ${inProgress.activeForm || inProgress.content}`);
                }
            }
            if (agent.currentTool) {
                parts.push(`${agent.currentTool.icon} ${agent.currentTool.name}`);
            }
            if (parts.length > 0) {
                collapsedStatus = ` • ${parts.join(' • ')}`;
            }
        }
        
        let html = `
            <div class="tree-node agent ${statusClass} ${selectedClass}" data-level="${level}">
                <div class="tree-node-content">
                    ${expandIcon ? `<span class="tree-expand-icon" onclick="window.activityTreeInstance.toggleAgent('${agent.id}'); event.stopPropagation();">${expandIcon}</span>` : '<span class="tree-expand-icon"></span>'}
                    <span class="tree-icon">${agent.icon}</span>
                    <span class="tree-label clickable" onclick="window.activityTreeInstance.selectItem(${this.escapeJson(agent)}, 'agent', event)">${agent.name}${instanceIndicator}${collapsedStatus}</span>
                    <span class="tree-status ${statusClass}">${agent.status}</span>
                </div>
        `;
        
        // Render nested content when expanded
        if (hasContent && isExpanded) {
            html += '<div class="tree-children">';
            
            // DISPLAY ORDER RULES (documented inline):
            // 1. TodoWrite is a privileged tool - ALWAYS appears first
            // 2. Each tool appears only once per unique instance
            // 3. Tools are displayed in order of creation (after TodoWrite)
            // 4. Tool instances are updated in place as new events arrive
            
            // Render all tools in their proper order
            // The tools array is already ordered: TodoWrite first, then others by creation
            if (hasTools) {
                for (let tool of agent.tools) {
                    html += this.renderToolElement(tool, level + 1);
                }
            }
            
            // Then render subagents (they will have their own TodoWrite at the top)
            if (hasSubagents) {
                const subagents = Array.from(agent.subagents.values());
                for (let subagent of subagents) {
                    html += this.renderAgentElement(subagent, level + 1);
                }
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
        
        // Add visual status indicators
        const statusIcon = this.getToolStatusIcon(tool.status);
        const statusLabel = this.getToolStatusLabel(tool.status);
        
        // Add call count if more than 1
        const callIndicator = tool.callCount > 1 ? ` (${tool.callCount} calls)` : '';
        
        let html = `
            <div class="tree-node tool ${statusClass} ${selectedClass}" data-level="${level}">
                <div class="tree-node-content">
                    <span class="tree-expand-icon"></span>
                    <span class="tree-icon">${tool.icon}</span>
                    <span class="tree-status-icon">${statusIcon}</span>
                    <span class="tree-label clickable" onclick="window.activityTreeInstance.selectItem(${this.escapeJson(tool)}, 'tool', event)">${tool.name}${callIndicator}</span>
                    <span class="tree-params">${params}</span>
                    <span class="tree-status ${statusClass}">${statusLabel}</span>
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
            'architect': '🏗️',
            'project manager': '📊'
        };
        return icons[agentName.toLowerCase()] || '🤖';
    }

    /**
     * Helper to get all agents including nested subagents
     */
    getAllAgents(session) {
        const agents = [];
        
        const collectAgents = (agentMap) => {
            if (!agentMap) return;
            
            for (let agent of agentMap.values()) {
                agents.push(agent);
                if (agent.subagents && agent.subagents.size > 0) {
                    collectAgents(agent.subagents);
                }
            }
        };
        
        collectAgents(session.agents);
        return agents;
    }

    /**
     * Render TodoWrite element
     */
    renderTodoWriteElement(todoWrite, level) {
        const todoWriteId = todoWrite.id;
        const isExpanded = this.expandedTools.has(todoWriteId);
        const expandIcon = isExpanded ? '▼' : '▶';
        const todos = todoWrite.todos || [];
        
        // Calculate status summary
        let completedCount = 0;
        let inProgressCount = 0;
        let pendingCount = 0;
        
        todos.forEach(todo => {
            if (todo.status === 'completed') completedCount++;
            else if (todo.status === 'in_progress') inProgressCount++;
            else pendingCount++;
        });
        
        // Find current in-progress todo for highlighting
        const currentTodo = todos.find(t => t.status === 'in_progress');
        const currentIndicator = currentTodo ? ` • 🔄 ${currentTodo.activeForm || currentTodo.content}` : '';
        
        let statusSummary = '';
        if (inProgressCount > 0) {
            statusSummary = `${inProgressCount} in progress, ${completedCount}/${todos.length} done`;
        } else if (completedCount === todos.length && todos.length > 0) {
            statusSummary = `All ${todos.length} completed ✅`;
        } else {
            statusSummary = `${completedCount}/${todos.length} done`;
        }
        
        // Add update count if more than 1
        const updateIndicator = todoWrite.updateCount > 1 ? ` (${todoWrite.updateCount} updates)` : '';
        
        let html = `
            <div class="tree-node todowrite ${currentTodo ? 'has-active' : ''}" data-level="${level}">
                <div class="tree-node-content">
                    <span class="tree-expand-icon" onclick="window.activityTreeInstance.toggleTodoWrite('${todoWriteId}'); event.stopPropagation();">${expandIcon}</span>
                    <span class="tree-icon">📝</span>
                    <span class="tree-label">TodoWrite${updateIndicator}${!isExpanded ? currentIndicator : ''}</span>
                    <span class="tree-params">${statusSummary}</span>
                    <span class="tree-status status-active">todos</span>
                </div>
        `;
        
        // Show expanded todo items if expanded
        if (isExpanded && todos.length > 0) {
            html += '<div class="tree-children">';
            for (let todo of todos) {
                const statusIcon = this.getCheckboxIcon(todo.status);
                const statusClass = `status-${todo.status}`;
                const displayText = todo.status === 'in_progress' ? todo.activeForm : todo.content;
                const isCurrentTodo = todo === currentTodo;
                
                html += `
                    <div class="tree-node todo-item ${statusClass} ${isCurrentTodo ? 'current-active' : ''}" data-level="${level + 1}">
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
     * Toggle TodoWrite expansion
     */
    toggleTodoWrite(todoWriteId) {
        if (this.expandedTools.has(todoWriteId)) {
            this.expandedTools.delete(todoWriteId);
        } else {
            this.expandedTools.add(todoWriteId);
        }
        this.renderTree();
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
     * Get status icon for tool status
     */
    getToolStatusIcon(status) {
        const icons = {
            'in_progress': '⏳',
            'completed': '✅',
            'failed': '❌',
            'error': '❌',
            'pending': '⏸️',
            'active': '🔄'
        };
        return icons[status] || '❓';
    }

    /**
     * Get formatted status label for tool
     */
    getToolStatusLabel(status) {
        const labels = {
            'in_progress': 'in progress',
            'completed': 'completed',
            'failed': 'failed',
            'error': 'error',
            'pending': 'pending',
            'active': 'active'
        };
        return labels[status] || status;
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
     * Render pinned TODOs element under agent
     */
    renderPinnedTodosElement(pinnedTodos, level) {
        const checklistId = `pinned-todos-${Date.now()}`;
        const isExpanded = this.expandedTools.has(checklistId) !== false; // Default to expanded
        const expandIcon = isExpanded ? '▼' : '▶';
        const todos = pinnedTodos.todos || [];
        
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
            <div class="tree-node pinned-todos" data-level="${level}">
                <div class="tree-node-content">
                    <span class="tree-expand-icon" onclick="window.activityTreeInstance.toggleTodoChecklist('${checklistId}'); event.stopPropagation();">${expandIcon}</span>
                    <span class="tree-icon">📌</span>
                    <span class="tree-label">Pinned TODOs</span>
                    <span class="tree-params">${statusSummary}</span>
                    <span class="tree-status status-active">pinned</span>
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
     * Display item data in left pane using UnifiedDataViewer for consistency with Tools viewer
     */
    displayItemData(item, itemType) {
        // Initialize UnifiedDataViewer if not already available
        if (!this.unifiedViewer) {
            this.unifiedViewer = new UnifiedDataViewer('module-data-content');
        }
        
        // Use the same UnifiedDataViewer as Tools viewer for consistent display
        this.unifiedViewer.display(item, itemType);
        
        // Update module header for consistency
        const moduleHeader = document.querySelector('.module-data-header h5');
        if (moduleHeader) {
            const icons = {
                'agent': '🤖',
                'tool': '🔧', 
                'instruction': '💬',
                'session': '🎯',
                'todo': '📝'
            };
            const icon = icons[itemType] || '📊';
            const name = item.name || item.agentName || item.tool_name || 'Item';
            moduleHeader.textContent = `${icon} ${itemType}: ${name}`;
        }
    }

    // Display methods removed - now using UnifiedDataViewer for consistency

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