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
 * DESIGN DECISION: Uses intelligent correlation strategy for tool calls that:
 * - Separates pre_tool and post_tool events first
 * - Correlates based on temporal proximity, parameter similarity, and context
 * - Handles timing differences between pre/post events (tools can run for minutes)
 * - Prevents duplicate tool entries by ensuring each tool call appears once
 * - Supports both paired and orphaned events for comprehensive tracking
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
                const toolName = event.tool_name || (event.data && event.data.tool_name);
                const sessionId = event.session_id || (event.data && event.data.session_id) || 'unknown';
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
                if (event.subtype === 'pre_tool' || (event.type === 'hook' && event.subtype && !event.subtype.includes('post'))) {
                    pair.pre_event = event;
                } else if (event.subtype === 'post_tool' || (event.subtype && event.subtype.includes('post'))) {
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

        // Improved correlation strategy: collect events first, then correlate intelligently
        const preToolEvents = [];
        const postToolEvents = [];
        let toolOperationCount = 0;

        // First pass: separate pre_tool and post_tool events
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
                if (event.subtype === 'pre_tool' || (event.type === 'hook' && event.subtype && !event.subtype.includes('post'))) {
                    preToolEvents.push(event);
                } else if (event.subtype === 'post_tool' || (event.subtype && event.subtype.includes('post'))) {
                    postToolEvents.push(event);
                } else {
                    // For events without clear pre/post distinction, treat as standalone
                    preToolEvents.push(event);
                    postToolEvents.push(event);
                }
            }
        });

        console.log('updateToolCalls - found', toolOperationCount, 'tool operations:', preToolEvents.length, 'pre_tool,', postToolEvents.length, 'post_tool');

        // Second pass: correlate pre_tool events with post_tool events
        const toolCallPairs = new Map();
        const usedPostEvents = new Set();

        preToolEvents.forEach((preEvent, preIndex) => {
            const toolName = preEvent.tool_name || (preEvent.data && preEvent.data.tool_name);
            const sessionId = preEvent.session_id || (preEvent.data && preEvent.data.session_id) || 'unknown';
            const preTimestamp = new Date(preEvent.timestamp).getTime();

            // Create a base pair for this pre_tool event
            const pairKey = `${sessionId}_${toolName}_${preIndex}_${preTimestamp}`;
            const pair = {
                pre_event: preEvent,
                post_event: null,
                tool_name: toolName,
                session_id: sessionId,
                operation_type: preEvent.operation_type || 'tool_execution',
                timestamp: preEvent.timestamp,
                duration_ms: null,
                success: null,
                exit_code: null,
                result_summary: null,
                agent_type: null,
                agent_confidence: null
            };

            // Get agent info from pre_event
            const agentInfo = this.extractAgentFromEvent(preEvent);
            pair.agent_type = agentInfo.name;
            pair.agent_confidence = agentInfo.confidence;

            // Try to find matching post_tool event
            let bestMatchIndex = -1;
            let bestMatchScore = -1;
            const maxTimeDiffMs = 300000; // 5 minutes max time difference

            postToolEvents.forEach((postEvent, postIndex) => {
                // Skip already used post events
                if (usedPostEvents.has(postIndex)) return;

                // Must match tool name and session
                const postToolName = postEvent.tool_name || (postEvent.data && postEvent.data.tool_name);
                const postSessionId = postEvent.session_id || (postEvent.data && postEvent.data.session_id) || 'unknown';
                if (postToolName !== toolName || postSessionId !== sessionId) return;

                const postTimestamp = new Date(postEvent.timestamp).getTime();
                const timeDiff = Math.abs(postTimestamp - preTimestamp);

                // Post event should generally come after pre event (or very close)
                const isTemporallyValid = postTimestamp >= preTimestamp - 1000; // Allow 1s clock skew

                // Calculate correlation score (higher is better)
                let score = 0;
                if (isTemporallyValid && timeDiff <= maxTimeDiffMs) {
                    score = 1000 - (timeDiff / 1000); // Prefer closer timestamps

                    // Boost score for parameter similarity (if available)
                    if (this.compareToolParameters(preEvent, postEvent)) {
                        score += 500;
                    }

                    // Boost score for same working directory
                    if (preEvent.working_directory && postEvent.working_directory &&
                        preEvent.working_directory === postEvent.working_directory) {
                        score += 100;
                    }
                }

                if (score > bestMatchScore) {
                    bestMatchScore = score;
                    bestMatchIndex = postIndex;
                }
            });

            // If we found a good match, pair them
            if (bestMatchIndex >= 0 && bestMatchScore > 0) {
                const postEvent = postToolEvents[bestMatchIndex];
                pair.post_event = postEvent;
                pair.duration_ms = postEvent.duration_ms;
                pair.success = postEvent.success;
                pair.exit_code = postEvent.exit_code;
                pair.result_summary = postEvent.result_summary;

                usedPostEvents.add(bestMatchIndex);
                console.log(`Paired pre_tool ${toolName} at ${preEvent.timestamp} with post_tool at ${postEvent.timestamp} (score: ${bestMatchScore})`);
            } else {
                console.log(`No matching post_tool found for ${toolName} at ${preEvent.timestamp} (still running or orphaned)`);
            }

            toolCallPairs.set(pairKey, pair);
        });

        // Third pass: handle any orphaned post_tool events (shouldn't happen but be safe)
        postToolEvents.forEach((postEvent, postIndex) => {
            if (usedPostEvents.has(postIndex)) return;

            const toolName = postEvent.tool_name || (postEvent.data && postEvent.data.tool_name);
            console.log('Orphaned post_tool event found:', toolName, 'at', postEvent.timestamp);

            const sessionId = postEvent.session_id || (postEvent.data && postEvent.data.session_id) || 'unknown';
            const postTimestamp = new Date(postEvent.timestamp).getTime();

            const pairKey = `orphaned_${sessionId}_${toolName}_${postIndex}_${postTimestamp}`;
            const pair = {
                pre_event: null,
                post_event: postEvent,
                tool_name: toolName,
                session_id: sessionId,
                operation_type: 'tool_execution',
                timestamp: postEvent.timestamp,
                duration_ms: postEvent.duration_ms,
                success: postEvent.success,
                exit_code: postEvent.exit_code,
                result_summary: postEvent.result_summary,
                agent_type: null,
                agent_confidence: null
            };

            const agentInfo = this.extractAgentFromEvent(postEvent);
            pair.agent_type = agentInfo.name;
            pair.agent_confidence = agentInfo.confidence;

            toolCallPairs.set(pairKey, pair);
        });

        // Store the correlated tool calls
        this.toolCalls = toolCallPairs;

        console.log('updateToolCalls - final result:', this.toolCalls.size, 'tool calls');
        if (this.toolCalls.size > 0) {
            console.log('Tool calls map keys:', Array.from(this.toolCalls.keys()));
        }
    }

    /**
     * Check if event is a tool operation
     * @param {Object} event - Event to check
     * @returns {boolean} - True if tool operation
     */
    isToolOperation(event) {
        // Tool operations have tool_name and are hook events with pre_tool or post_tool subtype
        // Check both top-level and data.tool_name for compatibility
        const hasToolName = event.tool_name || (event.data && event.data.tool_name);
        const isHookEvent = event.type === 'hook';
        const isToolSubtype = event.subtype === 'pre_tool' || event.subtype === 'post_tool' ||
                              (event.subtype && typeof event.subtype === 'string' && event.subtype.includes('tool'));
        
        return hasToolName && isHookEvent && isToolSubtype;
    }

    /**
     * Check if event is a file operation
     * @param {Object} event - Event to check
     * @returns {boolean} - True if file operation
     */
    isFileOperation(event) {
        // File operations are tool events with tools that operate on files
        // Check both top-level and data for tool_name
        let toolName = event.tool_name || (event.data && event.data.tool_name) || '';
        toolName = toolName.toLowerCase();
        
        // Check case-insensitively since tool names can come in different cases
        const fileTools = ['read', 'write', 'edit', 'grep', 'multiedit', 'glob', 'ls', 'bash', 'notebookedit'];
        
        // Get tool parameters from either location
        const toolParams = event.tool_parameters || (event.data && event.data.tool_parameters);

        // Also check if Bash commands involve file operations
        if (toolName === 'bash' && toolParams) {
            const command = toolParams.command || '';
            // Check for common file operations in bash commands
            if (command.match(/\b(cat|less|more|head|tail|touch|mv|cp|rm|mkdir|ls|find)\b/)) {
                return true;
            }
        }

        return toolName && fileTools.includes(toolName);
    }

    /**
     * Extract file path from event
     * @param {Object} event - Event to extract from
     * @returns {string|null} - File path or null
     */
    extractFilePath(event) {
        // Debug logging for file path extraction
        const fileTools = ['Read', 'Write', 'Edit', 'MultiEdit', 'NotebookEdit'];
        const toolName = event.tool_name || (event.data && event.data.tool_name);
        
        if (fileTools.includes(toolName)) {
            console.log('Extracting file path from event:', {
                tool_name: toolName,
                has_tool_parameters_top: !!event.tool_parameters,
                has_tool_parameters_data: !!(event.data && event.data.tool_parameters),
                tool_parameters: event.tool_parameters,
                data_tool_parameters: event.data?.tool_parameters
            });
        }
        
        // Try various locations where file path might be stored
        // Check top-level tool_parameters first (after transformation)
        if (event.tool_parameters?.file_path) return event.tool_parameters.file_path;
        if (event.tool_parameters?.path) return event.tool_parameters.path;
        if (event.tool_parameters?.notebook_path) return event.tool_parameters.notebook_path;
        
        // Check in data object as fallback
        if (event.data?.tool_parameters?.file_path) return event.data.tool_parameters.file_path;
        if (event.data?.tool_parameters?.path) return event.data.tool_parameters.path;
        if (event.data?.tool_parameters?.notebook_path) return event.data.tool_parameters.notebook_path;
        if (event.file_path) return event.file_path;
        if (event.path) return event.path;

        // For Glob tool, use the pattern as a pseudo-path
        if (event.tool_name?.toLowerCase() === 'glob' && event.tool_parameters?.pattern) {
            return `[glob] ${event.tool_parameters.pattern}`;
        }

        // For Bash commands, try to extract file paths from the command
        if (event.tool_name?.toLowerCase() === 'bash' && event.tool_parameters?.command) {
            const command = event.tool_parameters.command;
            
            // Enhanced regex to handle commands with flags
            // Match command followed by optional flags (starting with -) and then the file path
            // Patterns to handle:
            // 1. tail -50 /path/to/file
            // 2. head -n 100 /path/to/file  
            // 3. cat /path/to/file
            // 4. grep -r "pattern" /path/to/file
            const fileMatch = command.match(/(?:cat|less|more|head|tail|touch|mv|cp|rm|mkdir|ls|find|echo.*>|sed|awk|grep)(?:\s+-[a-zA-Z0-9]+)*(?:\s+[0-9]+)*\s+([^\s;|&]+)/);
            
            // If first match might be a flag, try a more specific pattern
            if (fileMatch && fileMatch[1]) {
                const possiblePath = fileMatch[1];
                // Check if it's actually a flag (starts with -)
                if (possiblePath.startsWith('-')) {
                    // Try alternative pattern that skips all flags
                    const altMatch = command.match(/(?:cat|less|more|head|tail|touch|mv|cp|rm|mkdir|ls|find|echo.*>|sed|awk|grep)(?:\s+-[^\s]+)*\s+([^-][^\s;|&]*)/);
                    if (altMatch && altMatch[1]) {
                        return altMatch[1];
                    }
                }
                return possiblePath;
            }
        }

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
            case 'notebookedit': return 'edit';
            case 'grep': return 'search';
            case 'glob': return 'search';
            case 'ls': return 'list';
            case 'bash':
                // Check bash command for file operation type
                const command = event.tool_parameters?.command || '';
                if (command.match(/\b(cat|less|more|head|tail)\b/)) return 'read';
                if (command.match(/\b(touch|echo.*>|tee)\b/)) return 'write';
                if (command.match(/\b(sed|awk)\b/)) return 'edit';
                if (command.match(/\b(grep|find)\b/)) return 'search';
                if (command.match(/\b(ls|dir)\b/)) return 'list';
                if (command.match(/\b(mv|cp)\b/)) return 'copy/move';
                if (command.match(/\b(rm|rmdir)\b/)) return 'delete';
                if (command.match(/\b(mkdir)\b/)) return 'create';
                return 'bash';
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
     * Get tool calls as array for unique instance view
     * Each entry represents a unique tool call instance
     * @returns {Array} - Array of [key, toolCall] pairs
     */
    getToolCallsArray() {
        return Array.from(this.toolCalls.entries());
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

    /**
     * Compare tool parameters between pre_tool and post_tool events
     * to determine if they're likely from the same tool call
     * @param {Object} preEvent - Pre-tool event
     * @param {Object} postEvent - Post-tool event
     * @returns {boolean} - True if parameters suggest same tool call
     */
    compareToolParameters(preEvent, postEvent) {
        // Extract parameters from both events
        const preParams = preEvent.tool_parameters || preEvent.data?.tool_parameters || {};
        const postParams = postEvent.tool_parameters || postEvent.data?.tool_parameters || {};

        // If no parameters in either event, can't compare meaningfully
        if (Object.keys(preParams).length === 0 && Object.keys(postParams).length === 0) {
            return false; // No boost for empty parameters
        }

        // Compare key parameters that are likely to be the same
        const importantParams = ['file_path', 'path', 'pattern', 'command', 'notebook_path'];
        let matchedParams = 0;
        let totalComparableParams = 0;

        importantParams.forEach(param => {
            const preValue = preParams[param];
            const postValue = postParams[param];

            if (preValue !== undefined || postValue !== undefined) {
                totalComparableParams++;
                if (preValue === postValue) {
                    matchedParams++;
                }
            }
        });

        // If we found comparable parameters, check if most match
        if (totalComparableParams > 0) {
            return (matchedParams / totalComparableParams) >= 0.8; // 80% parameter match threshold
        }

        // If no important parameters to compare, check if the parameter structure is similar
        const preKeys = Object.keys(preParams).sort();
        const postKeys = Object.keys(postParams).sort();

        if (preKeys.length === 0 && postKeys.length === 0) {
            return false;
        }

        // Simple structural similarity check
        if (preKeys.length === postKeys.length) {
            const keyMatches = preKeys.filter(key => postKeys.includes(key)).length;
            return keyMatches >= Math.max(1, preKeys.length * 0.5); // At least 50% key overlap
        }

        return false;
    }

    /**
     * Extract agent information from event using inference system
     * @param {Object} event - Event to extract agent from
     * @returns {Object} - Agent info with name and confidence
     */
    extractAgentFromEvent(event) {
        if (this.agentInference) {
            const inference = this.agentInference.getInferredAgentForEvent(event);
            if (inference) {
                return {
                    name: inference.agentName || 'Unknown',
                    confidence: inference.confidence || 'unknown'
                };
            }
        }

        // Fallback to direct event properties
        const agentName = event.agent_type || event.subagent_type ||
                          event.data?.agent_type || event.data?.subagent_type || 'PM';

        return {
            name: agentName,
            confidence: 'direct'
        };
    }
}
// ES6 Module export
export { FileToolTracker };
export default FileToolTracker;
