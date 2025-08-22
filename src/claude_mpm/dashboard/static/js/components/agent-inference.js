/**
 * Agent Inference Module
 *
 * Handles agent inference and processing logic for determining whether events
 * originate from the main agent or subagents based on event patterns and context.
 *
 * WHY: Separated from main dashboard to isolate complex agent inference logic
 * that analyzes event patterns to determine agent context. This provides better
 * maintainability and testability for a critical feature.
 *
 * DESIGN DECISION: This module maintains its own state for inference tracking
 * but relies on the event viewer for source data, keeping clear separation of
 * concerns while enabling delegation context tracking across events.
 */
class AgentInference {
    constructor(eventViewer) {
        this.eventViewer = eventViewer;

        // Agent inference state tracking
        this.state = {
            // Track current subagent delegation context
            currentDelegation: null,
            // Map of session_id -> agent context
            sessionAgents: new Map(),
            // Map of event indices -> inferred agent
            eventAgentMap: new Map(),
            // PM delegation tracking for unique instance views
            pmDelegations: new Map(), // delegation_id -> delegation context
            // Map of agent events to their PM delegation
            agentToDelegation: new Map(), // agent_name -> delegation_id
            // Track orphan subagent events (SubagentStart without PM Task)
            orphanSubagents: new Map(), // event_index -> orphan context
            // Track SubagentStart events for orphan detection
            subagentStartEvents: new Map() // agent_name -> array of start events
        };

        console.log('Agent inference system initialized');
    }

    /**
     * Initialize the agent inference system
     * Called when the dashboard initializes
     */
    initialize() {
        this.state = {
            currentDelegation: null,
            sessionAgents: new Map(),
            eventAgentMap: new Map(),
            pmDelegations: new Map(),
            agentToDelegation: new Map(),
            orphanSubagents: new Map(),
            subagentStartEvents: new Map()
        };
    }

    /**
     * Infer agent context from event payload
     * Based on production-ready detection from design document
     * @param {Object} event - Event payload
     * @returns {Object} - {type: 'main_agent'|'subagent', confidence: 'definitive'|'high'|'medium'|'default', agentName: string}
     */
    inferAgentFromEvent(event) {
        // Handle both direct properties and nested data properties
        const data = event.data || {};
        const sessionId = event.session_id || data.session_id || 'unknown';
        const eventType = event.hook_event_name || data.hook_event_name || event.type || '';
        const subtype = event.subtype || data.subtype || '';
        const toolName = event.tool_name || data.tool_name || '';

        // Debug logging for first few events to understand structure
        if (Math.random() < 0.1) {
            console.log('Agent inference debug:', {
                eventType,
                toolName,
                hasData: !!event.data,
                dataKeys: Object.keys(data),
                eventKeys: Object.keys(event),
                agentType: event.agent_type || data.agent_type,
                subagentType: event.subagent_type || data.subagent_type
            });
        }

        // Direct event detection (highest confidence) - from design doc
        if (eventType === 'SubagentStop' || subtype === 'subagent_stop') {
            const agentName = this.extractAgentNameFromEvent(event);
            // Log SubagentStop events for debugging
            console.log('SubagentStop event detected:', {
                agentName: agentName,
                sessionId: sessionId,
                eventType: eventType,
                subtype: subtype,
                rawAgentType: event.agent_type || data.agent_type
            });
            return {
                type: 'subagent',
                confidence: 'definitive',
                agentName: agentName,
                reason: 'SubagentStop event'
            };
        }

        if (eventType === 'Stop' || subtype === 'stop') {
            return {
                type: 'main_agent',
                confidence: 'definitive',
                agentName: 'PM',
                reason: 'Stop event'
            };
        }

        // Tool-based detection (high confidence) - from design doc
        if (toolName === 'Task') {
            const agentName = this.extractSubagentTypeFromTask(event);
            if (agentName) {
                // Log Task delegations for debugging
                console.log('Task delegation detected:', {
                    agentName: agentName,
                    sessionId: sessionId,
                    eventType: eventType
                });
                return {
                    type: 'subagent',
                    confidence: 'high',
                    agentName: agentName,
                    reason: 'Task tool with subagent_type'
                };
            }
        }

        // Hook event pattern analysis (high confidence)
        if (eventType === 'PreToolUse' && toolName === 'Task') {
            const agentName = this.extractSubagentTypeFromTask(event);
            if (agentName) {
                return {
                    type: 'subagent',
                    confidence: 'high',
                    agentName: agentName,
                    reason: 'PreToolUse Task delegation'
                };
            }
        }

        // Session pattern analysis (medium confidence) - from design doc
        if (sessionId) {
            const sessionLower = sessionId.toLowerCase();
            if (['subagent', 'task', 'agent-'].some(pattern => sessionLower.includes(pattern))) {
                return {
                    type: 'subagent',
                    confidence: 'medium',
                    agentName: 'Subagent',
                    reason: 'Session ID pattern'
                };
            }
        }

        // Agent type field analysis - check multiple possible locations
        const agentType = event.agent_type || data.agent_type || event.agent_id || data.agent_id;
        const subagentType = event.subagent_type || data.subagent_type;

        if (subagentType && subagentType !== 'unknown') {
            return {
                type: 'subagent',
                confidence: 'high',
                agentName: this.normalizeAgentName(subagentType),
                reason: 'subagent_type field'
            };
        }

        if (agentType && agentType !== 'unknown' && agentType !== 'main') {
            return {
                type: 'subagent',
                confidence: 'medium',
                agentName: this.normalizeAgentName(agentType),
                reason: 'agent_type field'
            };
        }

        // Check for delegation_details from hook handler
        if (data.delegation_details?.agent_type) {
            return {
                type: 'subagent',
                confidence: 'high',
                agentName: this.normalizeAgentName(data.delegation_details.agent_type),
                reason: 'delegation_details'
            };
        }

        // Check if this looks like a Hook event from Socket.IO
        if (event.type && event.type.startsWith('hook.')) {
            // Extract the hook type
            const hookType = event.type.replace('hook.', '');

            // Handle SubagentStart events
            if (hookType === 'subagent_start' || (data.hook_event_name === 'SubagentStart')) {
                const rawAgentName = data.agent_type || data.agent_id || 'Subagent';
                console.log('SubagentStart event from Socket.IO:', {
                    agentName: rawAgentName,
                    sessionId: sessionId,
                    hookType: hookType
                });
                return {
                    type: 'subagent',
                    confidence: 'definitive',
                    agentName: this.normalizeAgentName(rawAgentName),
                    reason: 'Socket.IO hook SubagentStart'
                };
            }

            // Handle SubagentStop events
            if (hookType === 'subagent_stop' || (data.hook_event_name === 'SubagentStop')) {
                const rawAgentName = data.agent_type || data.agent_id || 'Subagent';
                return {
                    type: 'subagent',
                    confidence: 'high',
                    agentName: this.normalizeAgentName(rawAgentName),
                    reason: 'Socket.IO hook SubagentStop'
                };
            }
        }

        // Default to main agent (from design doc)
        return {
            type: 'main_agent',
            confidence: 'default',
            agentName: 'PM',
            reason: 'default classification'
        };
    }

    /**
     * Normalize agent name from lowercase/underscore format to display format
     * @param {string} agentName - Raw agent name (e.g., 'engineer', 'test_integration')
     * @returns {string} - Normalized display name (e.g., 'Engineer Agent', 'Test Integration Agent')
     */
    normalizeAgentName(agentName) {
        if (!agentName) return 'Unknown';

        // Agent name mapping from raw format to display format
        const agentNameMap = {
            'engineer': 'Engineer Agent',
            'research': 'Research Agent',
            'qa': 'QA Agent',
            'documentation': 'Documentation Agent',
            'security': 'Security Agent',
            'ops': 'Ops Agent',
            'version_control': 'Version Control Agent',
            'data_engineer': 'Data Engineer Agent',
            'test_integration': 'Test Integration Agent',
            'pm': 'PM Agent'
        };

        // Check if we have a direct mapping
        const normalized = agentNameMap[agentName.toLowerCase()];
        if (normalized) {
            return normalized;
        }

        // If no direct mapping, apply basic formatting:
        // Convert underscore to space, capitalize words, and add "Agent" if not present
        let formatted = agentName
            .replace(/_/g, ' ')
            .split(' ')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
            .join(' ');

        // Add "Agent" suffix if not already present
        if (!formatted.toLowerCase().includes('agent')) {
            formatted += ' Agent';
        }

        return formatted;
    }

    /**
     * Extract subagent type from Task tool parameters
     * @param {Object} event - Event with Task tool
     * @returns {string|null} - Subagent type or null
     */
    extractSubagentTypeFromTask(event) {
        let rawAgentName = null;

        // Check tool_parameters directly
        if (event.tool_parameters?.subagent_type) {
            rawAgentName = event.tool_parameters.subagent_type;
        }
        // Check nested in data.tool_parameters (hook events)
        else if (event.data?.tool_parameters?.subagent_type) {
            rawAgentName = event.data.tool_parameters.subagent_type;
        }
        // Check delegation_details (new structure)
        else if (event.data?.delegation_details?.agent_type) {
            rawAgentName = event.data.delegation_details.agent_type;
        }
        // Check tool_input fallback
        else if (event.tool_input?.subagent_type) {
            rawAgentName = event.tool_input.subagent_type;
        }

        // Normalize the agent name before returning
        return rawAgentName ? this.normalizeAgentName(rawAgentName) : null;
    }

    /**
     * Extract agent name from any event
     * @param {Object} event - Event payload
     * @returns {string} - Agent name
     */
    extractAgentNameFromEvent(event) {
        // Priority order based on reliability from design doc
        const data = event.data || {};

        // 1. Task tool subagent_type (highest priority)
        if (event.tool_name === 'Task' || data.tool_name === 'Task') {
            const taskAgent = this.extractSubagentTypeFromTask(event);
            if (taskAgent) return taskAgent;
        }

        // 2. Direct subagent_type field
        if (event.subagent_type && event.subagent_type !== 'unknown') {
            return this.normalizeAgentName(event.subagent_type);
        }
        if (data.subagent_type && data.subagent_type !== 'unknown') {
            return this.normalizeAgentName(data.subagent_type);
        }

        // 2.5. Check delegation_details
        if (data.delegation_details?.agent_type && data.delegation_details.agent_type !== 'unknown') {
            return this.normalizeAgentName(data.delegation_details.agent_type);
        }

        // 3. Agent type fields (but not 'main' or 'unknown')
        if (event.agent_type && !['main', 'unknown'].includes(event.agent_type)) {
            return this.normalizeAgentName(event.agent_type);
        }
        if (data.agent_type && !['main', 'unknown'].includes(data.agent_type)) {
            return this.normalizeAgentName(data.agent_type);
        }

        // 4. Agent ID field as fallback
        if (event.agent_id && !['main', 'unknown'].includes(event.agent_id)) {
            return this.normalizeAgentName(event.agent_id);
        }
        if (data.agent_id && !['main', 'unknown'].includes(data.agent_id)) {
            return this.normalizeAgentName(data.agent_id);
        }

        // 5. Other fallbacks
        if (event.agent && event.agent !== 'unknown') {
            return this.normalizeAgentName(event.agent);
        }

        if (event.name && event.name !== 'unknown') {
            return this.normalizeAgentName(event.name);
        }

        // Default fallback
        return 'Unknown';
    }

    /**
     * Process all events and build agent inference context
     * This tracks delegation boundaries and agent context throughout the session
     */
    processAgentInference() {
        const events = this.eventViewer.events;

        // Reset inference state
        this.state.currentDelegation = null;
        this.state.sessionAgents.clear();
        this.state.eventAgentMap.clear();
        this.state.pmDelegations.clear();
        this.state.agentToDelegation.clear();
        this.state.orphanSubagents.clear();
        this.state.subagentStartEvents.clear();

        console.log('Processing agent inference for', events.length, 'events');

        // Early return if no events
        if (!events || events.length === 0) {
            console.log('No events to process for agent inference');
            return;
        }

        // Process events chronologically to track delegation context
        events.forEach((event, index) => {
            let finalAgent; // Declare outside try-catch to ensure scope availability

            try {
                const inference = this.inferAgentFromEvent(event);
                const sessionId = event.session_id || event.data?.session_id || 'default';

                // Determine agent for this event based on context
                finalAgent = inference;

                // If we're in a delegation context and this event doesn't have high confidence agent info,
                // inherit from delegation context
                if (this.state.currentDelegation &&
                    inference.confidence === 'default' &&
                    sessionId === this.state.currentDelegation.sessionId) {
                    finalAgent = {
                        type: 'subagent',
                        confidence: 'inherited',
                        agentName: this.state.currentDelegation.agentName,
                        reason: 'inherited from delegation context'
                    };
                }

                // Track SubagentStart events for orphan detection
                const hookEventName = event.hook_event_name || event.data?.hook_event_name || '';
                const isSubagentStart = hookEventName === 'SubagentStart' || 
                                       event.type === 'hook.subagent_start' ||
                                       event.subtype === 'subagent_start';
                
                if (isSubagentStart && inference.type === 'subagent') {
                    // Track this SubagentStart event
                    if (!this.state.subagentStartEvents.has(inference.agentName)) {
                        this.state.subagentStartEvents.set(inference.agentName, []);
                    }
                    this.state.subagentStartEvents.get(inference.agentName).push({
                        eventIndex: index,
                        event: event,
                        timestamp: event.timestamp,
                        sessionId: sessionId
                    });
                }

                // Track delegation boundaries and PM delegations
                if (event.tool_name === 'Task' && inference.type === 'subagent') {
                    // Start of subagent delegation - create PM delegation entry
                    const delegationId = `pm_${sessionId}_${index}_${inference.agentName}`;
                    const pmDelegation = {
                        id: delegationId,
                        agentName: inference.agentName,
                        sessionId: sessionId,
                        startIndex: index,
                        endIndex: null,
                        pmCall: event, // Store the PM call event
                        timestamp: event.timestamp,
                        agentEvents: [] // Collect all events from this agent
                    };

                    this.state.pmDelegations.set(delegationId, pmDelegation);
                    this.state.agentToDelegation.set(inference.agentName, delegationId);

                    this.state.currentDelegation = {
                        agentName: inference.agentName,
                        sessionId: sessionId,
                        startIndex: index,
                        endIndex: null,
                        delegationId: delegationId
                    };
                    console.log('Delegation started:', this.state.currentDelegation);
                } else if (inference.confidence === 'definitive' && inference.reason === 'SubagentStop event') {
                    // End of subagent delegation
                    if (this.state.currentDelegation) {
                        this.state.currentDelegation.endIndex = index;

                        // Update PM delegation end point
                        const pmDelegation = this.state.pmDelegations.get(this.state.currentDelegation.delegationId);
                        if (pmDelegation) {
                            pmDelegation.endIndex = index;
                        }

                        console.log('Delegation ended:', this.state.currentDelegation);
                        this.state.currentDelegation = null;
                    }
                }

                // Track events within PM delegation context
                if (this.state.currentDelegation && finalAgent.type === 'subagent') {
                    const pmDelegation = this.state.pmDelegations.get(this.state.currentDelegation.delegationId);
                    if (pmDelegation) {
                        pmDelegation.agentEvents.push({
                            eventIndex: index,
                            event: event,
                            inference: finalAgent
                        });
                    }
                }

                // Store the inference result
                this.state.eventAgentMap.set(index, finalAgent);

                // Update session agent tracking
                this.state.sessionAgents.set(sessionId, finalAgent);

                // Debug first few inferences
                if (index < 5) {
                    console.log(`Event ${index} agent inference:`, {
                        event_type: event.type || event.hook_event_name,
                        subtype: event.subtype,
                        tool_name: event.tool_name,
                        inference: finalAgent,
                        hasData: !!event.data,
                        agentType: event.agent_type || event.data?.agent_type
                    });
                }
            } catch (error) {
                console.error(`Error processing event ${index} for agent inference:`, error);

                // Set a default finalAgent if not already set due to error
                if (!finalAgent) {
                    finalAgent = {
                        type: 'main_agent',
                        confidence: 'error',
                        agentName: 'PM',
                        reason: 'error during processing'
                    };
                }

                // Store the default inference for this event
                this.state.eventAgentMap.set(index, finalAgent);
            }
        });

        // Identify orphan subagents after all events are processed
        this.identifyOrphanSubagents(events);

        console.log('Agent inference processing complete. Results:', {
            total_events: events.length,
            inferred_agents: this.state.eventAgentMap.size,
            unique_sessions: this.state.sessionAgents.size,
            pm_delegations: this.state.pmDelegations.size,
            agent_to_delegation_mappings: this.state.agentToDelegation.size,
            orphan_subagents: this.state.orphanSubagents.size
        });
    }

    /**
     * Get inferred agent for a specific event
     * @param {number} eventIndex - Index of event in events array
     * @returns {Object|null} - Agent inference result or null
     */
    getInferredAgent(eventIndex) {
        return this.state.eventAgentMap.get(eventIndex) || null;
    }

    /**
     * Get inferred agent for an event object
     * @param {Object} event - Event object
     * @returns {Object|null} - Agent inference result or null
     */
    getInferredAgentForEvent(event) {
        const events = this.eventViewer.events;

        // Try to find by exact reference first
        let eventIndex = events.indexOf(event);

        // If exact match fails, try to find by timestamp or session_id + timestamp
        if (eventIndex === -1 && event.timestamp) {
            eventIndex = events.findIndex(e =>
                e.timestamp === event.timestamp &&
                e.session_id === event.session_id
            );
        }

        // If we still can't find it, perform inline inference
        if (eventIndex === -1) {
            console.log('Agent inference: Could not find event in events array, performing inline inference');
            return this.inferAgentFromEvent(event);
        }

        // Get cached inference or perform new inference
        let inference = this.getInferredAgent(eventIndex);
        if (!inference) {
            inference = this.inferAgentFromEvent(event);
            // Cache the result
            this.state.eventAgentMap.set(eventIndex, inference);
        }

        return inference;
    }

    /**
     * Get current delegation context
     * @returns {Object|null} - Current delegation or null
     */
    getCurrentDelegation() {
        return this.state.currentDelegation;
    }

    /**
     * Get session agents map
     * @returns {Map} - Map of session IDs to agent contexts
     */
    getSessionAgents() {
        return this.state.sessionAgents;
    }

    /**
     * Get event agent map
     * @returns {Map} - Map of event indices to agent contexts
     */
    getEventAgentMap() {
        return this.state.eventAgentMap;
    }

    /**
     * Get PM delegations for unique instance views
     * @returns {Map} - Map of delegation IDs to PM delegation contexts
     */
    getPMDelegations() {
        return this.state.pmDelegations;
    }

    /**
     * Get agent to delegation mapping
     * @returns {Map} - Map of agent names to delegation IDs
     */
    getAgentToDelegationMap() {
        return this.state.agentToDelegation;
    }

    /**
     * Build hierarchical delegation tree structure
     * @returns {Object} Tree structure with PM nodes and subagent children
     */
    buildDelegationHierarchy() {
        // Get all PM delegations
        const pmDelegations = this.getPMDelegations();
        const events = this.eventViewer.events;
        
        // Build hierarchy tree
        const hierarchy = {
            mainPM: {
                type: 'pm',
                name: 'PM',
                delegations: [],
                ownEvents: [],
                totalEvents: 0
            },
            impliedPM: {
                type: 'pm_implied',
                name: 'Implied PM',
                delegations: [],
                ownEvents: [],
                totalEvents: 0
            }
        };
        
        // Process explicit PM delegations
        for (const [delegationId, delegation] of pmDelegations) {
            hierarchy.mainPM.delegations.push({
                id: delegationId,
                agentName: delegation.agentName,
                taskContext: this.extractTaskContext(delegation.pmCall),
                events: delegation.agentEvents,
                startTime: delegation.timestamp,
                endTime: delegation.endIndex ? events[delegation.endIndex]?.timestamp : null,
                status: delegation.endIndex ? 'completed' : 'active'
            });
            hierarchy.mainPM.totalEvents += delegation.agentEvents.length;
        }
        
        // Find PM's own events
        events.forEach((event, index) => {
            const inference = this.getInferredAgent(index);
            if (inference && inference.type === 'main_agent') {
                hierarchy.mainPM.ownEvents.push({
                    eventIndex: index,
                    event: event
                });
                hierarchy.mainPM.totalEvents++;
            }
        });
        
        // Find orphan subagent events
        const orphanEvents = new Map();
        events.forEach((event, index) => {
            const inference = this.getInferredAgent(index);
            if (inference && inference.type === 'subagent') {
                // Check if this is part of any PM delegation
                let isOrphan = true;
                for (const [_, delegation] of pmDelegations) {
                    if (delegation.agentEvents.some(e => e.eventIndex === index)) {
                        isOrphan = false;
                        break;
                    }
                }
                
                if (isOrphan) {
                    const agentName = inference.agentName;
                    if (!orphanEvents.has(agentName)) {
                        orphanEvents.set(agentName, []);
                    }
                    orphanEvents.get(agentName).push({
                        eventIndex: index,
                        event: event,
                        inference: inference
                    });
                }
            }
        });
        
        // Add orphan agents as implied PM delegations
        for (const [agentName, agentEvents] of orphanEvents) {
            hierarchy.impliedPM.delegations.push({
                id: `implied_${agentName}`,
                agentName: agentName,
                taskContext: 'No explicit PM delegation',
                events: agentEvents,
                startTime: agentEvents[0].event.timestamp,
                endTime: agentEvents[agentEvents.length - 1].event.timestamp,
                status: 'completed'
            });
            hierarchy.impliedPM.totalEvents += agentEvents.length;
        }
        
        return hierarchy;
    }
    
    /**
     * Extract task context from PM call
     * @param {Object} pmCall - PM's Task tool call
     * @returns {string} Task description
     */
    extractTaskContext(pmCall) {
        if (!pmCall) return 'Unknown task';
        
        const params = pmCall.tool_parameters || pmCall.data?.tool_parameters || {};
        return params.task || params.request || params.description || 'Task delegation';
    }
    
    /**
     * Identify orphan subagents (SubagentStart without PM Task delegation)
     * @param {Array} events - All events to analyze
     */
    identifyOrphanSubagents(events) {
        const ORPHAN_TIME_WINDOW = 5000; // 5 seconds to group orphans together
        
        // Check each SubagentStart event
        for (const [agentName, startEvents] of this.state.subagentStartEvents) {
            for (const startEvent of startEvents) {
                const eventIndex = startEvent.eventIndex;
                const timestamp = new Date(startEvent.timestamp).getTime();
                
                // Check if this SubagentStart has a corresponding PM Task delegation
                let hasTaskDelegation = false;
                
                // Look for a Task tool call within a reasonable time window before this SubagentStart
                for (let i = Math.max(0, eventIndex - 20); i < eventIndex; i++) {
                    const prevEvent = events[i];
                    if (!prevEvent) continue;
                    
                    const prevTimestamp = new Date(prevEvent.timestamp).getTime();
                    const timeDiff = timestamp - prevTimestamp;
                    
                    // Check if this is a Task tool call within 10 seconds
                    if (prevEvent.tool_name === 'Task' && timeDiff >= 0 && timeDiff < 10000) {
                        const inference = this.state.eventAgentMap.get(i);
                        if (inference && inference.agentName === agentName) {
                            hasTaskDelegation = true;
                            break;
                        }
                    }
                }
                
                // If no Task delegation found, mark as orphan
                if (!hasTaskDelegation) {
                    this.state.orphanSubagents.set(eventIndex, {
                        agentName: agentName,
                        timestamp: startEvent.timestamp,
                        sessionId: startEvent.sessionId,
                        event: startEvent.event,
                        groupingKey: null // Will be set by grouping logic
                    });
                }
            }
        }
        
        // Group orphan subagents by time proximity or session
        this.groupOrphanSubagents(ORPHAN_TIME_WINDOW);
    }
    
    /**
     * Group orphan subagents that occur close together in time or same session
     * @param {number} timeWindow - Time window in milliseconds for grouping
     */
    groupOrphanSubagents(timeWindow) {
        const orphansList = Array.from(this.state.orphanSubagents.values())
            .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        
        let currentGroup = null;
        let lastTimestamp = null;
        
        for (const orphan of orphansList) {
            const timestamp = new Date(orphan.timestamp).getTime();
            
            // Check if this orphan should be in the same group
            if (!currentGroup || 
                (lastTimestamp && timestamp - lastTimestamp > timeWindow)) {
                // Start a new group
                currentGroup = `implied_pm_${orphan.sessionId}_${timestamp}`;
            }
            
            orphan.groupingKey = currentGroup;
            lastTimestamp = timestamp;
        }
    }
    
    /**
     * Check if a subagent event is an orphan (no PM Task delegation)
     * @param {number} eventIndex - Index of the event
     * @returns {boolean} True if the event is from an orphan subagent
     */
    isOrphanSubagent(eventIndex) {
        return this.state.orphanSubagents.has(eventIndex);
    }
    
    /**
     * Get orphan subagent context for an event
     * @param {number} eventIndex - Index of the event  
     * @returns {Object|null} Orphan context or null
     */
    getOrphanContext(eventIndex) {
        return this.state.orphanSubagents.get(eventIndex) || null;
    }
    
    /**
     * Get all orphan subagent groups
     * @returns {Map} Map of groupingKey -> array of orphan contexts
     */
    getOrphanGroups() {
        const groups = new Map();
        
        for (const orphan of this.state.orphanSubagents.values()) {
            const key = orphan.groupingKey;
            if (!groups.has(key)) {
                groups.set(key, []);
            }
            groups.get(key).push(orphan);
        }
        
        return groups;
    }

    /**
     * Get unique agent instances (one per agent type, consolidating multiple delegations)
     * This is used for the unique instance view in the agents tab
     * @returns {Array} - Array of unique agent instances
     */
    getUniqueAgentInstances() {
        const agentMap = new Map(); // agentName -> consolidated data

        // Consolidate all PM delegations by agent name
        for (const [delegationId, delegation] of this.state.pmDelegations) {
            const agentName = delegation.agentName;

            if (!agentMap.has(agentName)) {
                // First delegation for this agent type
                agentMap.set(agentName, {
                    id: `consolidated_${agentName}`,
                    type: 'consolidated_agent',
                    agentName: agentName,
                    delegations: [], // Array of all delegations
                    pmCalls: [], // Array of all PM calls
                    allEvents: [], // Combined events from all delegations
                    firstTimestamp: delegation.timestamp,
                    lastTimestamp: delegation.timestamp,
                    totalEventCount: delegation.agentEvents.length,
                    delegationCount: 1
                });
            }

            // Add this delegation to the consolidated agent
            const agent = agentMap.get(agentName);
            agent.delegations.push({
                id: delegationId,
                pmCall: delegation.pmCall,
                timestamp: delegation.timestamp,
                eventCount: delegation.agentEvents.length,
                startIndex: delegation.startIndex,
                endIndex: delegation.endIndex,
                events: delegation.agentEvents
            });

            if (delegation.pmCall) {
                agent.pmCalls.push(delegation.pmCall);
            }

            // Merge events from all delegations
            agent.allEvents = agent.allEvents.concat(delegation.agentEvents);

            // Update consolidated metadata
            if (new Date(delegation.timestamp) < new Date(agent.firstTimestamp)) {
                agent.firstTimestamp = delegation.timestamp;
            }
            if (new Date(delegation.timestamp) > new Date(agent.lastTimestamp)) {
                agent.lastTimestamp = delegation.timestamp;
            }

            agent.totalEventCount += delegation.agentEvents.length;
            agent.delegationCount++;
        }

        // Handle agents that appear without explicit PM delegation (implied PM)
        const events = this.eventViewer.events;
        for (let index = 0; index < events.length; index++) {
            const inference = this.getInferredAgent(index);
            if (inference && inference.type === 'subagent' && !agentMap.has(inference.agentName)) {
                // Create consolidated agent for implied delegation
                agentMap.set(inference.agentName, {
                    id: `consolidated_${inference.agentName}`,
                    type: 'consolidated_agent',
                    agentName: inference.agentName,
                    delegations: [{
                        id: `implied_pm_${inference.agentName}_${index}`,
                        pmCall: null,
                        timestamp: events[index].timestamp,
                        eventCount: 1,
                        startIndex: index,
                        endIndex: null,
                        events: [{
                            eventIndex: index,
                            event: events[index],
                            inference: inference
                        }]
                    }],
                    pmCalls: [],
                    allEvents: [{
                        eventIndex: index,
                        event: events[index],
                        inference: inference
                    }],
                    firstTimestamp: events[index].timestamp,
                    lastTimestamp: events[index].timestamp,
                    totalEventCount: 1,
                    delegationCount: 1,
                    isImplied: true
                });
            }
        }

        // Convert map to array and sort by first appearance (timestamp)
        const uniqueInstances = Array.from(agentMap.values())
            .sort((a, b) => new Date(a.firstTimestamp) - new Date(b.firstTimestamp));

        console.log('Consolidated unique agents:', {
            total_unique_agents: uniqueInstances.length,
            agents: uniqueInstances.map(agent => ({
                name: agent.agentName,
                delegations: agent.delegationCount,
                totalEvents: agent.totalEventCount
            }))
        });

        return uniqueInstances;
    }
}

// ES6 Module export
export { AgentInference };
export default AgentInference;
