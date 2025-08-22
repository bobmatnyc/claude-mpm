/**
 * Agent Hierarchy Component
 * 
 * Displays agents in a hierarchical tree structure with PM at the top level.
 * Shows subagents as children of the PM that spawned them, tracking delegation
 * relationships from Task tool calls.
 * 
 * WHY: Provides clear visualization of agent delegation relationships, making it
 * easier to understand the flow of work through PM and subagent delegations.
 * 
 * DESIGN DECISION: Uses tree-based visualization with expand/collapse functionality
 * to handle complex delegation chains while maintaining performance with large
 * event streams. Separates hierarchy building from rendering for flexibility.
 */

class AgentHierarchy {
    constructor(agentInference, eventViewer) {
        this.agentInference = agentInference;
        this.eventViewer = eventViewer;
        
        // Hierarchy state
        this.state = {
            // Tree structure with PM nodes at root
            hierarchyTree: null,
            // Map of agent ID to node for quick lookups
            nodeMap: new Map(),
            // Expanded state for tree nodes
            expandedNodes: new Set(),
            // Currently selected node
            selectedNode: null
        };
        
        // Default expand all nodes initially
        this.expandAll = true;
        
        // Set up event listeners
        this.setupEventListeners();
        
        console.log('Agent hierarchy component initialized');
    }
    
    /**
     * Set up event listeners for safe interaction
     */
    setupEventListeners() {
        // Use event delegation for toggle node clicks to avoid undefined dashboard errors
        document.addEventListener('click', (event) => {
            const toggleTarget = event.target.closest('[data-toggle-node]');
            if (toggleTarget && window.dashboard && window.dashboard.agentHierarchy) {
                const nodeId = toggleTarget.dataset.toggleNode;
                window.dashboard.agentHierarchy.toggleNode(nodeId);
            }
        });
    }
    
    /**
     * Build hierarchical structure from events
     * @returns {Object} Tree structure with PM at root
     */
    buildHierarchy() {
        // Process agent inference first
        this.agentInference.processAgentInference();
        
        // Get PM delegations and events
        const pmDelegations = this.agentInference.getPMDelegations();
        const events = this.eventViewer.events;
        const eventAgentMap = this.agentInference.getEventAgentMap();
        
        // Create root PM nodes
        const mainPM = {
            id: 'pm_main',
            type: 'pm',
            name: 'PM (Main Session)',
            children: [],
            events: [],
            eventCount: 0,
            status: 'active',
            startTime: null,
            endTime: null,
            expanded: true
        };
        
        // Map to store multiple implied PM groups
        const impliedPMGroups = new Map();
        
        // Clear node map
        this.state.nodeMap.clear();
        this.state.nodeMap.set(mainPM.id, mainPM);
        
        // Track which agents have been added
        const processedAgents = new Set();
        
        // Process explicit PM delegations
        for (const [delegationId, delegation] of pmDelegations) {
            const agentNode = {
                id: delegationId,
                type: 'subagent',
                name: delegation.agentName,
                delegationContext: this.extractDelegationContext(delegation.pmCall),
                children: [], // Subagents could theoretically delegate to others
                events: delegation.agentEvents,
                eventCount: delegation.agentEvents.length,
                status: delegation.endIndex ? 'completed' : 'active',
                startTime: delegation.timestamp,
                endTime: delegation.endIndex ? events[delegation.endIndex]?.timestamp : null,
                startIndex: delegation.startIndex,
                endIndex: delegation.endIndex,
                expanded: this.expandAll || this.state.expandedNodes.has(delegationId)
            };
            
            mainPM.children.push(agentNode);
            this.state.nodeMap.set(delegationId, agentNode);
            processedAgents.add(delegation.agentName);
            
            // Update main PM stats
            mainPM.eventCount++;
            if (!mainPM.startTime || new Date(delegation.timestamp) < new Date(mainPM.startTime)) {
                mainPM.startTime = delegation.timestamp;
            }
            if (delegation.endIndex && events[delegation.endIndex]) {
                const endTime = events[delegation.endIndex].timestamp;
                if (!mainPM.endTime || new Date(endTime) > new Date(mainPM.endTime)) {
                    mainPM.endTime = endTime;
                }
            }
        }
        
        // Get orphan subagent groups from agent inference
        const orphanGroups = this.agentInference.getOrphanGroups();
        
        // Create implied PM nodes for each orphan group
        let impliedPMCounter = 1;
        for (const [groupingKey, orphans] of orphanGroups) {
            // Create an implied PM node for this group
            const impliedPM = {
                id: `pm_implied_${groupingKey}`,
                type: 'pm',
                name: `PM (Implied #${impliedPMCounter})`,
                children: [],
                events: [],
                eventCount: 0,
                status: 'inferred',
                startTime: null,
                endTime: null,
                expanded: true,
                isImplied: true,
                tooltip: 'Inferred PM - Subagents started without explicit PM delegation'
            };
            
            impliedPMGroups.set(groupingKey, impliedPM);
            this.state.nodeMap.set(impliedPM.id, impliedPM);
            impliedPMCounter++;
            
            // Group orphan events by agent name within this implied PM
            const agentEventGroups = new Map();
            
            for (const orphan of orphans) {
                // Find all events for this orphan agent
                const agentEvents = [];
                events.forEach((event, index) => {
                    const inference = eventAgentMap.get(index);
                    if (inference && inference.agentName === orphan.agentName) {
                        // Check if this event is orphaned (not in any PM delegation)
                        let isOrphan = true;
                        for (const [_, delegation] of pmDelegations) {
                            if (delegation.agentEvents.some(e => e.eventIndex === index)) {
                                isOrphan = false;
                                break;
                            }
                        }
                        
                        if (isOrphan) {
                            agentEvents.push({
                                eventIndex: index,
                                event: event,
                                inference: inference
                            });
                        }
                    }
                });
                
                if (agentEvents.length > 0) {
                    if (!agentEventGroups.has(orphan.agentName)) {
                        agentEventGroups.set(orphan.agentName, []);
                    }
                    agentEventGroups.get(orphan.agentName).push(...agentEvents);
                }
            }
            
            // Create subagent nodes for each agent in this implied PM group
            for (const [agentName, agentEvents] of agentEventGroups) {
                if (agentEvents.length === 0) continue;
                
                const firstEvent = agentEvents[0].event;
                const lastEvent = agentEvents[agentEvents.length - 1].event;
                
                const agentNode = {
                    id: `implied_agent_${groupingKey}_${agentName}`,
                    type: 'subagent',
                    name: agentName,
                    delegationContext: 'Orphan agent - no explicit PM delegation found',
                    children: [],
                    events: agentEvents,
                    eventCount: agentEvents.length,
                    status: 'inferred',
                    startTime: firstEvent.timestamp,
                    endTime: lastEvent.timestamp,
                    startIndex: agentEvents[0].eventIndex,
                    endIndex: agentEvents[agentEvents.length - 1].eventIndex,
                    expanded: this.expandAll,
                    isImplied: true,
                    tooltip: 'This agent was spawned without an explicit PM Task delegation'
                };
                
                impliedPM.children.push(agentNode);
                this.state.nodeMap.set(agentNode.id, agentNode);
                
                // Update implied PM stats
                impliedPM.eventCount += agentEvents.length;
                if (!impliedPM.startTime || new Date(firstEvent.timestamp) < new Date(impliedPM.startTime)) {
                    impliedPM.startTime = firstEvent.timestamp;
                }
                if (!impliedPM.endTime || new Date(lastEvent.timestamp) > new Date(impliedPM.endTime)) {
                    impliedPM.endTime = lastEvent.timestamp;
                }
            }
        }
        
        // Also find completely orphaned subagent events (not caught by SubagentStart)
        const uncategorizedOrphans = [];
        events.forEach((event, index) => {
            const inference = eventAgentMap.get(index);
            if (inference && inference.type === 'subagent') {
                // Check if this agent is already in a PM delegation or implied PM
                let isOrphan = true;
                
                // Check explicit delegations
                for (const [_, delegation] of pmDelegations) {
                    if (delegation.agentEvents.some(e => e.eventIndex === index)) {
                        isOrphan = false;
                        break;
                    }
                }
                
                // Check implied PMs
                if (isOrphan) {
                    for (const [_, impliedPM] of impliedPMGroups) {
                        for (const child of impliedPM.children) {
                            if (child.events.some(e => e.eventIndex === index)) {
                                isOrphan = false;
                                break;
                            }
                        }
                        if (!isOrphan) break;
                    }
                }
                
                if (isOrphan) {
                    uncategorizedOrphans.push({
                        eventIndex: index,
                        event: event,
                        inference: inference
                    });
                }
            }
        });
        
        // If there are uncategorized orphans, create a generic implied PM for them
        if (uncategorizedOrphans.length > 0) {
            const genericImpliedPM = {
                id: 'pm_implied_generic',
                type: 'pm',
                name: 'PM (Implied - Uncategorized)',
                children: [],
                events: [],
                eventCount: 0,
                status: 'inferred',
                startTime: null,
                endTime: null,
                expanded: true,
                isImplied: true,
                tooltip: 'Orphan agents without clear grouping'
            };
            
            // Group by agent name
            const agentGroups = new Map();
            for (const orphan of uncategorizedOrphans) {
                const agentName = orphan.inference.agentName;
                if (!agentGroups.has(agentName)) {
                    agentGroups.set(agentName, []);
                }
                agentGroups.get(agentName).push(orphan);
            }
            
            // Create nodes for each agent
            for (const [agentName, agentEvents] of agentGroups) {
                const firstEvent = agentEvents[0].event;
                const lastEvent = agentEvents[agentEvents.length - 1].event;
                
                const agentNode = {
                    id: `implied_generic_${agentName}`,
                    type: 'subagent',
                    name: agentName,
                    delegationContext: 'Uncategorized orphan agent',
                    children: [],
                    events: agentEvents,
                    eventCount: agentEvents.length,
                    status: 'inferred',
                    startTime: firstEvent.timestamp,
                    endTime: lastEvent.timestamp,
                    startIndex: agentEvents[0].eventIndex,
                    endIndex: agentEvents[agentEvents.length - 1].eventIndex,
                    expanded: this.expandAll,
                    isImplied: true
                };
                
                genericImpliedPM.children.push(agentNode);
                this.state.nodeMap.set(agentNode.id, agentNode);
                genericImpliedPM.eventCount += agentEvents.length;
                
                if (!genericImpliedPM.startTime || new Date(firstEvent.timestamp) < new Date(genericImpliedPM.startTime)) {
                    genericImpliedPM.startTime = firstEvent.timestamp;
                }
                if (!genericImpliedPM.endTime || new Date(lastEvent.timestamp) > new Date(genericImpliedPM.endTime)) {
                    genericImpliedPM.endTime = lastEvent.timestamp;
                }
            }
            
            if (genericImpliedPM.children.length > 0) {
                impliedPMGroups.set('generic', genericImpliedPM);
                this.state.nodeMap.set(genericImpliedPM.id, genericImpliedPM);
            }
        }
        
        // Count PM's own events (not delegated)
        let pmOwnEvents = 0;
        events.forEach((event, index) => {
            const inference = eventAgentMap.get(index);
            if (inference && inference.type === 'main_agent') {
                pmOwnEvents++;
                mainPM.events.push({
                    eventIndex: index,
                    event: event,
                    inference: inference
                });
            }
        });
        mainPM.eventCount += pmOwnEvents;
        
        // Update PM status based on children
        if (mainPM.children.length > 0) {
            const hasActive = mainPM.children.some(child => child.status === 'active');
            mainPM.status = hasActive ? 'active' : 'completed';
        }
        
        // Build final tree structure
        const tree = {
            roots: []
        };
        
        // Only add PMs that have content
        if (mainPM.eventCount > 0 || mainPM.children.length > 0) {
            tree.roots.push(mainPM);
        }
        
        // Add all implied PM groups that have content
        for (const [_, impliedPM] of impliedPMGroups) {
            if (impliedPM.children.length > 0) {
                tree.roots.push(impliedPM);
            }
        }
        
        this.state.hierarchyTree = tree;
        
        console.log('Hierarchy built:', {
            mainPM: {
                children: mainPM.children.length,
                events: mainPM.eventCount,
                ownEvents: pmOwnEvents
            },
            impliedPMGroups: impliedPMGroups.size,
            totalImpliedAgents: Array.from(impliedPMGroups.values())
                .reduce((sum, pm) => sum + pm.children.length, 0)
        });
        
        return tree;
    }
    
    /**
     * Extract delegation context from PM Task call
     * @param {Object} pmCall - The PM's Task tool call event
     * @returns {string} Description of what was delegated
     */
    extractDelegationContext(pmCall) {
        if (!pmCall) return 'Unknown delegation';
        
        // Try to extract task description from tool parameters
        const params = pmCall.tool_parameters || pmCall.data?.tool_parameters || {};
        const task = params.task || params.request || params.description;
        
        if (task) {
            // Truncate long tasks
            const maxLength = 100;
            if (task.length > maxLength) {
                return task.substring(0, maxLength) + '...';
            }
            return task;
        }
        
        // Fallback to tool input
        const toolInput = pmCall.tool_input || pmCall.data?.tool_input;
        if (toolInput && typeof toolInput === 'string') {
            const maxLength = 100;
            if (toolInput.length > maxLength) {
                return toolInput.substring(0, maxLength) + '...';
            }
            return toolInput;
        }
        
        return 'Task delegation';
    }
    
    /**
     * Render the hierarchy tree to HTML
     * @param {Object} filters - Optional filters for display
     * @returns {string} HTML string for the hierarchy
     */
    render(filters = {}) {
        const tree = this.state.hierarchyTree || this.buildHierarchy();
        
        if (!tree.roots || tree.roots.length === 0) {
            return '<div class="agent-hierarchy-empty">No agent activity detected</div>';
        }
        
        // Apply filters if provided
        const filteredTree = this.applyFilters(tree, filters);
        
        // Generate HTML
        const html = filteredTree.roots.map(root => this.renderNode(root, 0)).join('');
        
        return `<div class="agent-hierarchy">${html}</div>`;
    }
    
    /**
     * Render a single node and its children
     * @param {Object} node - Node to render
     * @param {number} level - Indentation level
     * @returns {string} HTML string for the node
     */
    renderNode(node, level) {
        const isExpanded = node.expanded || this.state.expandedNodes.has(node.id);
        const hasChildren = node.children && node.children.length > 0;
        const isSelected = this.state.selectedNode === node.id;
        
        // Icon based on node type and status
        const icon = this.getNodeIcon(node);
        const expandIcon = hasChildren ? (isExpanded ? '▼' : '▶') : '&nbsp;&nbsp;';
        
        // Status color
        const statusClass = this.getStatusClass(node.status);
        
        // Add special styling for implied nodes
        const impliedClass = node.isImplied ? 'agent-node-implied' : '';
        const tooltipAttr = node.tooltip ? `title="${this.escapeHtml(node.tooltip)}"` : '';
        
        // Build node HTML
        let html = `
            <div class="agent-node agent-node-level-${level} ${isSelected ? 'agent-node-selected' : ''} ${impliedClass}" 
                 data-node-id="${node.id}" ${tooltipAttr}>
                <div class="agent-node-header ${statusClass}" 
                     data-toggle-node="${node.id}" style="cursor: pointer">
                    <span class="agent-node-expand">${expandIcon}</span>
                    <span class="agent-node-icon">${icon}</span>
                    <span class="agent-node-name">${this.escapeHtml(node.name)}</span>
                    <span class="agent-node-stats">
                        <span class="agent-event-count">${node.eventCount} events</span>
                        ${node.status ? `<span class="agent-status">${node.status}</span>` : ''}
                    </span>
                </div>
        `;
        
        // Add details if expanded
        if (isExpanded && (node.delegationContext || node.startTime)) {
            html += '<div class="agent-node-details">';
            
            if (node.delegationContext && node.delegationContext !== 'Unknown delegation') {
                html += `
                    <div class="agent-delegation-context">
                        <strong>Task:</strong> ${this.escapeHtml(node.delegationContext)}
                    </div>
                `;
            }
            
            if (node.startTime) {
                const duration = this.calculateDuration(node.startTime, node.endTime);
                html += `
                    <div class="agent-timing">
                        <span class="agent-time-start">${this.formatTime(node.startTime)}</span>
                        ${duration ? `<span class="agent-duration">(${duration})</span>` : ''}
                    </div>
                `;
            }
            
            html += '</div>';
        }
        
        // Render children if expanded
        if (isExpanded && hasChildren) {
            html += '<div class="agent-node-children">';
            html += node.children.map(child => this.renderNode(child, level + 1)).join('');
            html += '</div>';
        }
        
        html += '</div>';
        
        return html;
    }
    
    /**
     * Get icon for node based on type and status
     * @param {Object} node - Node to get icon for
     * @returns {string} Icon HTML/emoji
     */
    getNodeIcon(node) {
        if (node.type === 'pm') {
            return node.isImplied ? '🔍' : '👔';
        }
        
        // Map agent names to icons
        const agentIcons = {
            'Engineer Agent': '🔧',
            'Research Agent': '🔍',
            'QA Agent': '✅',
            'Documentation Agent': '📝',
            'Security Agent': '🔒',
            'Ops Agent': '⚙️',
            'Version Control Agent': '📦',
            'Data Engineer Agent': '💾',
            'Test Integration Agent': '🧪'
        };
        
        return agentIcons[node.name] || '🤖';
    }
    
    /**
     * Get status class for styling
     * @param {string} status - Node status
     * @returns {string} CSS class name
     */
    getStatusClass(status) {
        switch (status) {
            case 'active':
                return 'agent-status-active';
            case 'completed':
                return 'agent-status-completed';
            case 'pending':
                return 'agent-status-pending';
            case 'inferred':
                return 'agent-status-inferred';
            default:
                return 'agent-status-unknown';
        }
    }
    
    /**
     * Toggle node expansion
     * @param {string} nodeId - ID of node to toggle
     */
    toggleNode(nodeId) {
        const node = this.state.nodeMap.get(nodeId);
        if (!node) return;
        
        if (this.state.expandedNodes.has(nodeId)) {
            this.state.expandedNodes.delete(nodeId);
            node.expanded = false;
        } else {
            this.state.expandedNodes.add(nodeId);
            node.expanded = true;
        }
        
        // Trigger re-render
        if (window.dashboard) {
            window.dashboard.renderCurrentTab();
        }
    }
    
    /**
     * Select a node
     * @param {string} nodeId - ID of node to select
     */
    selectNode(nodeId) {
        this.state.selectedNode = nodeId;
        const node = this.state.nodeMap.get(nodeId);
        
        if (node) {
            // Dispatch event for other components to react
            const event = new CustomEvent('agentNodeSelected', {
                detail: { node: node }
            });
            document.dispatchEvent(event);
        }
    }
    
    /**
     * Apply filters to the tree
     * @param {Object} tree - Tree to filter
     * @param {Object} filters - Filter criteria
     * @returns {Object} Filtered tree
     */
    applyFilters(tree, filters) {
        if (!filters || Object.keys(filters).length === 0) {
            return tree;
        }
        
        // Clone tree structure for filtering
        const filteredTree = {
            roots: []
        };
        
        for (const root of tree.roots) {
            const filteredRoot = this.filterNode(root, filters);
            if (filteredRoot) {
                filteredTree.roots.push(filteredRoot);
            }
        }
        
        return filteredTree;
    }
    
    /**
     * Filter a single node and its children
     * @param {Object} node - Node to filter
     * @param {Object} filters - Filter criteria
     * @returns {Object|null} Filtered node or null if filtered out
     */
    filterNode(node, filters) {
        // Check if node matches filters
        let matches = true;
        
        if (filters.searchText) {
            const searchLower = filters.searchText.toLowerCase();
            matches = matches && (
                node.name.toLowerCase().includes(searchLower) ||
                (node.delegationContext && node.delegationContext.toLowerCase().includes(searchLower))
            );
        }
        
        if (filters.agentType) {
            matches = matches && node.name.includes(filters.agentType);
        }
        
        if (filters.status) {
            matches = matches && node.status === filters.status;
        }
        
        // Filter children recursively
        let filteredChildren = [];
        if (node.children) {
            for (const child of node.children) {
                const filteredChild = this.filterNode(child, filters);
                if (filteredChild) {
                    filteredChildren.push(filteredChild);
                }
            }
        }
        
        // Include node if it matches or has matching children
        if (matches || filteredChildren.length > 0) {
            return {
                ...node,
                children: filteredChildren
            };
        }
        
        return null;
    }
    
    /**
     * Format timestamp for display
     * @param {string} timestamp - ISO timestamp
     * @returns {string} Formatted time
     */
    formatTime(timestamp) {
        if (!timestamp) return '';
        const date = new Date(timestamp);
        return date.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: false
        });
    }
    
    /**
     * Calculate duration between timestamps
     * @param {string} start - Start timestamp
     * @param {string} end - End timestamp
     * @returns {string} Formatted duration
     */
    calculateDuration(start, end) {
        if (!start || !end) return '';
        
        const startTime = new Date(start).getTime();
        const endTime = new Date(end).getTime();
        const duration = endTime - startTime;
        
        if (duration < 1000) {
            return `${duration}ms`;
        } else if (duration < 60000) {
            return `${(duration / 1000).toFixed(1)}s`;
        } else {
            const minutes = Math.floor(duration / 60000);
            const seconds = Math.floor((duration % 60000) / 1000);
            return `${minutes}m ${seconds}s`;
        }
    }
    
    /**
     * Escape HTML for safe rendering
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * Update hierarchy when new events arrive
     * @param {Array} events - New events
     */
    updateWithNewEvents(events) {
        // Rebuild hierarchy with new events
        this.buildHierarchy();
    }
    
    /**
     * Clear the hierarchy
     */
    clear() {
        this.state.hierarchyTree = null;
        this.state.nodeMap.clear();
        this.state.expandedNodes.clear();
        this.state.selectedNode = null;
    }
    
    /**
     * Expand all nodes
     */
    expandAllNodes() {
        for (const [nodeId, node] of this.state.nodeMap) {
            this.state.expandedNodes.add(nodeId);
            node.expanded = true;
        }
        this.expandAll = true;
    }
    
    /**
     * Collapse all nodes
     */
    collapseAllNodes() {
        this.state.expandedNodes.clear();
        for (const [nodeId, node] of this.state.nodeMap) {
            node.expanded = false;
        }
        this.expandAll = false;
    }
}

// ES6 Module export
export { AgentHierarchy };
export default AgentHierarchy;