/**
 * File and Tool Tracker Module
 * 
 * Tracks file operations and tool calls by pairing pre/post events and maintaining
 * organized collections for the files and tools tabs. Provides analysis of
 * tool execution patterns and file operation history.
 * 
 * WHY: Extracted from main dashboard to isolate complex event pairing logic
 * that groups related events into meaningful operations. This provides better
 * maintainability for the intricate logic of matching tool events with their results.
 * 
 * DESIGN DECISION: Maintains separate tracking for file operations and tool calls
 * with event pairing logic that matches pre/post events by session, tool name,
 * and timestamp proximity for accurate operation reconstruction.
 */
class FileToolTracker {
    constructor(agentInference, workingDirectoryManager) {
        this.agentInference = agentInference;
        this.workingDirectoryManager = workingDirectoryManager;
        
        // File tracking for files tab
        this.fileOperations = new Map(); // Map of file paths to operations
        
        // Tool call tracking for tools tab
        this.toolCalls = new Map(); // Map of tool call keys to paired pre/post events
        
        console.log('File-tool tracker initialized');
    }

    /**
     * Update file operations from events
     * @param {Array} events - Events to process
     */
    updateFileOperations(events) {
        // Clear existing data
        this.fileOperations.clear();

        console.log('updateFileOperations - processing', events.length, 'events');

        // Group events by session and timestamp to match pre/post pairs
        const eventPairs = new Map(); // Key: session_id + timestamp + tool_name
        let fileOperationCount = 0;
        
        // First pass: collect all tool events and group them
        events.forEach((event, index) => {
            const isFileOp = this.isFileOperation(event);
            if (isFileOp) fileOperationCount++;
            
            if (index < 5) { // Debug first 5 events with more detail
                console.log(`Event ${index}:`, {
                    type: event.type,
                    subtype: event.subtype,
                    tool_name: event.tool_name,
                    tool_parameters: event.tool_parameters,
                    isFileOp: isFileOp
                });
            }
            
            if (isFileOp) {
                const toolName = event.tool_name;
                const sessionId = event.session_id || 'unknown';
                const eventKey = `${sessionId}_${toolName}_${Math.floor(new Date(event.timestamp).getTime() / 1000)}`; // Group by second
                
                if (!eventPairs.has(eventKey)) {
                    eventPairs.set(eventKey, {
                        pre_event: null,
                        post_event: null,
                        tool_name: toolName,
                        session_id: sessionId
                    });
                }
                
                const pair = eventPairs.get(eventKey);
                if (event.subtype === 'pre_tool' || event.type === 'hook' && !event.subtype.includes('post')) {
                    pair.pre_event = event;
                } else if (event.subtype === 'post_tool' || event.subtype.includes('post')) {
                    pair.post_event = event;
                } else {
                    // For events without clear pre/post distinction, treat as both
                    pair.pre_event = event;
                    pair.post_event = event;
                }
            }
        });
        
        console.log('updateFileOperations - found', fileOperationCount, 'file operations in', eventPairs.size, 'event pairs');
        
        // Second pass: extract file paths and operations from paired events
        eventPairs.forEach((pair, key) => {
            const filePath = this.extractFilePathFromPair(pair);
            
            if (filePath) {
                console.log('File operation detected for:', filePath, 'from pair:', key);
                
                if (!this.fileOperations.has(filePath)) {
                    this.fileOperations.set(filePath, {
                        path: filePath,
                        operations: [],
                        lastOperation: null
                    });
                }

                const fileData = this.fileOperations.get(filePath);
                const operation = this.getFileOperationFromPair(pair);
                const timestamp = pair.post_event?.timestamp || pair.pre_event?.timestamp;
                
                const agentInfo = this.extractAgentFromPair(pair);
                const workingDirectory = this.workingDirectoryManager.extractWorkingDirectoryFromPair(pair);
                
                fileData.operations.push({
                    operation: operation,
                    timestamp: timestamp,
                    agent: agentInfo.name,
                    confidence: agentInfo.confidence,
                    sessionId: pair.session_id,
                    details: this.getFileOperationDetailsFromPair(pair),
                    workingDirectory: workingDirectory
                });
                fileData.lastOperation = timestamp;
            } else {
                console.log('No file path found for pair:', key, pair);
            }
        });
        
        console.log('updateFileOperations - final result:', this.fileOperations.size, 'file operations');
        if (this.fileOperations.size > 0) {
            console.log('File operations map:', Array.from(this.fileOperations.entries()));
        }
    }

    /**
     * Update tool calls from events - pairs pre/post tool events into complete tool calls
     * @param {Array} events - Events to process
     */
    updateToolCalls(events) {
        // Clear existing data
        this.toolCalls.clear();

        console.log('updateToolCalls - processing', events.length, 'events');

        // Group events by session and timestamp to match pre/post pairs
        const toolCallPairs = new Map(); // Key: session_id + timestamp + tool_name
        let toolOperationCount = 0;
        
        // First pass: collect all tool events and group them
        events.forEach((event, index) => {
            const isToolOp = this.isToolOperation(event);
            if (isToolOp) toolOperationCount++;
            
            if (index < 5) { // Debug first 5 events with more detail
                console.log(`Tool Event ${index}:`, {
                    type: event.type,
                    subtype: event.subtype,
                    tool_name: event.tool_name,
                    tool_parameters: event.tool_parameters,
                    isToolOp: isToolOp
                });
            }
            
            if (isToolOp) {
                const toolName = event.tool_name;
                const sessionId = event.session_id || 'unknown';
                const eventKey = `${sessionId}_${toolName}_${Math.floor(new Date(event.timestamp).getTime() / 1000)}`; // Group by second
                
                if (!toolCallPairs.has(eventKey)) {
                    toolCallPairs.set(eventKey, {
                        pre_event: null,
                        post_event: null,
                        tool_name: toolName,
                        session_id: sessionId,
                        operation_type: null,
                        timestamp: null,
                        duration_ms: null,
                        success: null,
                        exit_code: null,
                        result_summary: null,
                        agent_type: null
                    });
                }
                
                const pair = toolCallPairs.get(eventKey);
                if (event.subtype === 'pre_tool' || (event.type === 'hook' && !event.subtype.includes('post'))) {
                    pair.pre_event = event;
                    pair.timestamp = event.timestamp;
                    pair.operation_type = event.operation_type || 'tool_execution';
                    pair.agent_type = event.agent_type || event.subagent_type || 'PM';
                } else if (event.subtype === 'post_tool' || event.subtype.includes('post')) {
                    pair.post_event = event;
                    pair.duration_ms = event.duration_ms;
                    pair.success = event.success;
                    pair.exit_code = event.exit_code;
                    pair.result_summary = event.result_summary;
                    if (!pair.agent_type) {
                        pair.agent_type = event.agent_type || event.subagent_type || 'PM';
                    }
                } else {
                    // For events without clear pre/post distinction, treat as both
                    pair.pre_event = event;
                    pair.post_event = event;
                    pair.timestamp = event.timestamp;
                    pair.agent_type = event.agent_type || event.subagent_type || 'PM';
                }
            }
        });
        
        console.log('updateToolCalls - found', toolOperationCount, 'tool operations in', toolCallPairs.size, 'tool call pairs');
        
        // Second pass: store complete tool calls
        toolCallPairs.forEach((pair, key) => {
            // Ensure we have at least a pre_event or post_event
            if (pair.pre_event || pair.post_event) {
                console.log('Tool call detected for:', pair.tool_name, 'from pair:', key);
                this.toolCalls.set(key, pair);
            } else {
                console.log('No valid tool call found for pair:', key, pair);
            }
        });
        
        console.log('updateToolCalls - final result:', this.toolCalls.size, 'tool calls');
        if (this.toolCalls.size > 0) {
            console.log('Tool calls map:', Array.from(this.toolCalls.entries()));
        }
    }

    /**
     * Check if event is a tool operation
     * @param {Object} event - Event to check
     * @returns {boolean} - True if tool operation
     */
    isToolOperation(event) {
        // Tool operations have tool_name and are hook events with pre_tool or post_tool subtype
        return event.tool_name && 
               event.type === 'hook' && 
               (event.subtype === 'pre_tool' || event.subtype === 'post_tool' || 
                event.subtype.includes('tool'));
    }

    /**
     * Check if event is a file operation
     * @param {Object} event - Event to check
     * @returns {boolean} - True if file operation
     */
    isFileOperation(event) {
        // File operations are tool events with tools that operate on files
        const fileTools = ['Read', 'Write', 'Edit', 'Grep', 'MultiEdit'];
        return event.tool_name && fileTools.includes(event.tool_name);
    }

    /**
     * Extract file path from event
     * @param {Object} event - Event to extract from
     * @returns {string|null} - File path or null
     */
    extractFilePath(event) {
        // Try various locations where file path might be stored
        if (event.tool_parameters?.file_path) return event.tool_parameters.file_path;
        if (event.tool_parameters?.path) return event.tool_parameters.path;
        if (event.data?.tool_parameters?.file_path) return event.data.tool_parameters.file_path;
        if (event.data?.tool_parameters?.path) return event.data.tool_parameters.path;
        if (event.file_path) return event.file_path;
        if (event.path) return event.path;
        
        return null;
    }

    /**
     * Extract file path from event pair
     * @param {Object} pair - Event pair object
     * @returns {string|null} - File path or null
     */
    extractFilePathFromPair(pair) {
        // Try pre_event first, then post_event
        let filePath = null;
        
        if (pair.pre_event) {
            filePath = this.extractFilePath(pair.pre_event);
        }
        
        if (!filePath && pair.post_event) {
            filePath = this.extractFilePath(pair.post_event);
        }
        
        return filePath;
    }

    /**
     * Get file operation type from event
     * @param {Object} event - Event to analyze
     * @returns {string} - Operation type
     */
    getFileOperation(event) {
        if (!event.tool_name) return 'unknown';
        
        const toolName = event.tool_name.toLowerCase();
        switch (toolName) {
            case 'read': return 'read';
            case 'write': return 'write';
            case 'edit': return 'edit';
            case 'multiedit': return 'edit';
            case 'grep': return 'search';
            default: return toolName;
        }
    }

    /**
     * Get file operation from event pair
     * @param {Object} pair - Event pair object
     * @returns {string} - Operation type
     */
    getFileOperationFromPair(pair) {
        // Try pre_event first, then post_event
        if (pair.pre_event) {
            return this.getFileOperation(pair.pre_event);
        }
        
        if (pair.post_event) {
            return this.getFileOperation(pair.post_event);
        }
        
        return 'unknown';
    }

    /**
     * Extract agent information from event pair
     * @param {Object} pair - Event pair object
     * @returns {Object} - Agent info with name and confidence
     */
    extractAgentFromPair(pair) {
        // Try to get agent info from inference system first
        const event = pair.pre_event || pair.post_event;
        if (event && this.agentInference) {
            const inference = this.agentInference.getInferredAgentForEvent(event);
            if (inference) {
                return {
                    name: inference.agentName || 'Unknown',
                    confidence: inference.confidence || 'unknown'
                };
            }
        }
        
        // Fallback to direct event properties
        const agentName = event?.agent_type || event?.subagent_type || 
                          pair.pre_event?.agent_type || pair.post_event?.agent_type || 'PM';
        
        return {
            name: agentName,
            confidence: 'direct'
        };
    }

    /**
     * Get detailed operation information from event pair
     * @param {Object} pair - Event pair object
     * @returns {Object} - Operation details
     */
    getFileOperationDetailsFromPair(pair) {
        const details = {};
        
        // Extract details from pre_event (parameters)
        if (pair.pre_event) {
            const params = pair.pre_event.tool_parameters || pair.pre_event.data?.tool_parameters || {};
            details.parameters = params;
            details.tool_input = pair.pre_event.tool_input;
        }
        
        // Extract details from post_event (results)
        if (pair.post_event) {
            details.result = pair.post_event.result;
            details.success = pair.post_event.success;
            details.error = pair.post_event.error;
            details.exit_code = pair.post_event.exit_code;
            details.duration_ms = pair.post_event.duration_ms;
        }
        
        return details;
    }

    /**
     * Get file operations map
     * @returns {Map} - File operations map
     */
    getFileOperations() {
        return this.fileOperations;
    }

    /**
     * Get tool calls map
     * @returns {Map} - Tool calls map
     */
    getToolCalls() {
        return this.toolCalls;
    }

    /**
     * Get file operations for a specific file
     * @param {string} filePath - File path
     * @returns {Object|null} - File operations data or null
     */
    getFileOperationsForFile(filePath) {
        return this.fileOperations.get(filePath) || null;
    }

    /**
     * Get tool call by key
     * @param {string} key - Tool call key
     * @returns {Object|null} - Tool call data or null
     */
    getToolCall(key) {
        return this.toolCalls.get(key) || null;
    }

    /**
     * Clear all tracking data
     */
    clear() {
        this.fileOperations.clear();
        this.toolCalls.clear();
        console.log('File-tool tracker cleared');
    }

    /**
     * Get statistics about tracked operations
     * @returns {Object} - Statistics
     */
    getStatistics() {
        return {
            fileOperations: this.fileOperations.size,
            toolCalls: this.toolCalls.size,
            uniqueFiles: this.fileOperations.size,
            totalFileOperations: Array.from(this.fileOperations.values())
                .reduce((sum, data) => sum + data.operations.length, 0)
        };
    }
}