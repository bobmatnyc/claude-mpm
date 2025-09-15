/**
 * File Change Tracker Module
 * 
 * Tracks all file operations (Edit, Write, Read, MultiEdit) from event history
 * and builds a tree structure grouped by working directory.
 * Supports session-based filtering and stores complete edit history with timestamps.
 * 
 * Architecture:
 * - Maintains a hierarchical structure of file changes
 * - Tracks file lifecycle (create, edit, delete)
 * - Provides session-aware filtering
 * - Stores complete history for diff generation
 */
class FileChangeTracker {
    constructor() {
        // Main data structures
        this.fileChanges = new Map(); // Map<filePath, FileChangeData>
        this.sessionData = new Map(); // Map<sessionId, Set<filePath>>
        this.workingDirectories = new Map(); // Map<workingDir, Set<filePath>>
        
        // Current state
        this.currentSessionId = null;
        this.events = [];
        
        // File operation types we track
        this.FILE_OPERATIONS = {
            READ: 'Read',
            WRITE: 'Write',
            EDIT: 'Edit',
            MULTI_EDIT: 'MultiEdit',
            DELETE: 'Delete',
            CREATE: 'Create'
        };
        
        // Initialize
        this.initialized = false;
        console.log('FileChangeTracker initialized');
    }
    
    /**
     * Initialize the tracker
     */
    initialize() {
        if (this.initialized) return;
        this.initialized = true;
        console.log('FileChangeTracker ready');
    }
    
    /**
     * Process an event and extract file operations
     * @param {Object} event - Event data
     */
    processEvent(event) {
        // Check if this is a file-related tool event
        if (!this.isFileOperation(event)) return;
        
        const fileOp = this.extractFileOperation(event);
        if (!fileOp) return;
        
        // Add to our tracking structures
        this.addFileOperation(fileOp);
    }
    
    /**
     * Check if an event is a file operation
     * @param {Object} event - Event to check
     * @returns {boolean}
     */
    isFileOperation(event) {
        // Check for tool events with file operations
        if (event.type === 'tool' || event.subtype === 'pre_tool' || event.subtype === 'post_tool') {
            const toolName = event.tool_name || (event.data && event.data.tool_name);
            return Object.values(this.FILE_OPERATIONS).includes(toolName);
        }
        
        // Check for hook events with file operations
        if (event.type === 'hook' && event.data) {
            const toolName = event.data.tool_name;
            return Object.values(this.FILE_OPERATIONS).includes(toolName);
        }
        
        return false;
    }
    
    /**
     * Extract file operation details from an event
     * @param {Object} event - Event to process
     * @returns {Object|null} File operation data
     */
    extractFileOperation(event) {
        const toolName = event.tool_name || (event.data && event.data.tool_name);
        const params = event.tool_parameters || (event.data && event.data.tool_parameters) || {};
        const result = event.tool_result || (event.data && event.data.tool_result);
        
        // Extract file path based on tool type
        let filePath = null;
        let operation = toolName;
        let content = null;
        let oldContent = null;
        
        switch (toolName) {
            case this.FILE_OPERATIONS.READ:
                filePath = params.file_path;
                content = result && result.content;
                break;
                
            case this.FILE_OPERATIONS.WRITE:
                filePath = params.file_path;
                content = params.content;
                break;
                
            case this.FILE_OPERATIONS.EDIT:
                filePath = params.file_path;
                oldContent = params.old_string;
                content = params.new_string;
                break;
                
            case this.FILE_OPERATIONS.MULTI_EDIT:
                filePath = params.file_path;
                // For MultiEdit, we track each edit
                const edits = params.edits || [];
                return {
                    filePath,
                    operation,
                    timestamp: event.timestamp,
                    sessionId: event.session_id || 'unknown',
                    workingDirectory: this.extractWorkingDirectory(event),
                    edits: edits.map(edit => ({
                        oldContent: edit.old_string,
                        newContent: edit.new_string,
                        replaceAll: edit.replace_all || false
                    })),
                    isMultiEdit: true,
                    success: event.subtype === 'post_tool' && result && result.success !== false
                };
                
            default:
                return null;
        }
        
        if (!filePath) return null;
        
        return {
            filePath,
            operation,
            timestamp: event.timestamp,
            sessionId: event.session_id || 'unknown',
            workingDirectory: this.extractWorkingDirectory(event),
            content,
            oldContent,
            isEdit: operation === this.FILE_OPERATIONS.EDIT,
            isWrite: operation === this.FILE_OPERATIONS.WRITE,
            isRead: operation === this.FILE_OPERATIONS.READ,
            success: event.subtype === 'post_tool' && result && result.success !== false
        };
    }
    
    /**
     * Extract working directory from event
     * @param {Object} event - Event data
     * @returns {string} Working directory path
     */
    extractWorkingDirectory(event) {
        // Try to extract from event data
        if (event.data && event.data.working_directory) {
            return event.data.working_directory;
        }
        
        // Try to extract from context
        if (event.context && event.context.working_directory) {
            return event.context.working_directory;
        }
        
        // Try to extract from file path (get parent directory)
        const filePath = event.tool_parameters?.file_path || 
                        (event.data && event.data.tool_parameters?.file_path);
        if (filePath) {
            const parts = filePath.split('/');
            parts.pop(); // Remove filename
            return parts.join('/') || '/';
        }
        
        return 'unknown';
    }
    
    /**
     * Add a file operation to our tracking structures
     * @param {Object} fileOp - File operation data
     */
    addFileOperation(fileOp) {
        const { filePath, sessionId, workingDirectory } = fileOp;
        
        // Initialize file change data if needed
        if (!this.fileChanges.has(filePath)) {
            this.fileChanges.set(filePath, {
                path: filePath,
                fileName: this.getFileName(filePath),
                workingDirectory,
                sessions: new Set(),
                operations: [],
                firstSeen: fileOp.timestamp,
                lastModified: fileOp.timestamp,
                currentContent: null,
                initialContent: null,
                totalEdits: 0,
                totalReads: 0,
                totalWrites: 0
            });
        }
        
        const fileData = this.fileChanges.get(filePath);
        
        // Update session tracking
        fileData.sessions.add(sessionId);
        if (!this.sessionData.has(sessionId)) {
            this.sessionData.set(sessionId, new Set());
        }
        this.sessionData.get(sessionId).add(filePath);
        
        // Update working directory tracking
        if (!this.workingDirectories.has(workingDirectory)) {
            this.workingDirectories.set(workingDirectory, new Set());
        }
        this.workingDirectories.get(workingDirectory).add(filePath);
        
        // Add operation to history
        fileData.operations.push(fileOp);
        fileData.lastModified = fileOp.timestamp;
        
        // Update content tracking
        if (fileOp.isRead && fileOp.content && !fileData.initialContent) {
            fileData.initialContent = fileOp.content;
            fileData.currentContent = fileOp.content;
            fileData.totalReads++;
        } else if (fileOp.isWrite) {
            if (!fileData.initialContent) {
                fileData.initialContent = '';
            }
            fileData.currentContent = fileOp.content;
            fileData.totalWrites++;
        } else if (fileOp.isEdit) {
            // Apply edit to current content
            if (fileData.currentContent && fileOp.oldContent) {
                fileData.currentContent = fileData.currentContent.replace(
                    fileOp.oldContent,
                    fileOp.content || ''
                );
            }
            fileData.totalEdits++;
        } else if (fileOp.isMultiEdit && fileOp.edits) {
            // Apply multiple edits
            let content = fileData.currentContent || '';
            for (const edit of fileOp.edits) {
                if (edit.replaceAll) {
                    content = content.replaceAll(edit.oldContent, edit.newContent);
                } else {
                    content = content.replace(edit.oldContent, edit.newContent);
                }
            }
            fileData.currentContent = content;
            fileData.totalEdits += fileOp.edits.length;
        }
    }
    
    /**
     * Get file name from path
     * @param {string} filePath - Full file path
     * @returns {string} File name
     */
    getFileName(filePath) {
        const parts = filePath.split('/');
        return parts[parts.length - 1] || filePath;
    }
    
    /**
     * Update with new events
     * @param {Array} events - Array of events
     */
    updateEvents(events) {
        // Clear and rebuild
        this.clear();
        this.events = events;
        
        // Process all events
        for (const event of events) {
            this.processEvent(event);
        }
        
        console.log(`FileChangeTracker updated: ${this.fileChanges.size} files tracked`);
    }
    
    /**
     * Get files for current session
     * @param {string} sessionId - Session ID to filter by
     * @returns {Array} Array of file change data
     */
    getFilesForSession(sessionId) {
        if (!sessionId) {
            return Array.from(this.fileChanges.values());
        }
        
        const sessionFiles = this.sessionData.get(sessionId);
        if (!sessionFiles) return [];
        
        return Array.from(sessionFiles).map(filePath => 
            this.fileChanges.get(filePath)
        ).filter(Boolean);
    }
    
    /**
     * Get file tree structure grouped by working directory
     * @param {string} sessionId - Optional session filter
     * @returns {Object} Tree structure
     */
    getFileTree(sessionId = null) {
        const files = this.getFilesForSession(sessionId);
        const tree = {};
        
        for (const fileData of files) {
            const wd = fileData.workingDirectory || 'unknown';
            if (!tree[wd]) {
                tree[wd] = {
                    path: wd,
                    name: this.getDirectoryName(wd),
                    files: [],
                    totalOperations: 0,
                    totalEdits: 0,
                    totalReads: 0,
                    totalWrites: 0
                };
            }
            
            tree[wd].files.push(fileData);
            tree[wd].totalOperations += fileData.operations.length;
            tree[wd].totalEdits += fileData.totalEdits;
            tree[wd].totalReads += fileData.totalReads;
            tree[wd].totalWrites += fileData.totalWrites;
        }
        
        // Sort files within each directory
        Object.values(tree).forEach(dir => {
            dir.files.sort((a, b) => 
                new Date(b.lastModified) - new Date(a.lastModified)
            );
        });
        
        return tree;
    }
    
    /**
     * Get directory name from path
     * @param {string} dirPath - Directory path
     * @returns {string} Directory name
     */
    getDirectoryName(dirPath) {
        if (dirPath === 'unknown') return 'Unknown Directory';
        const parts = dirPath.split('/');
        return parts[parts.length - 1] || dirPath;
    }
    
    /**
     * Get file change details
     * @param {string} filePath - File path
     * @returns {Object|null} File change data
     */
    getFileDetails(filePath) {
        return this.fileChanges.get(filePath) || null;
    }
    
    /**
     * Get operations for a file
     * @param {string} filePath - File path
     * @param {string} sessionId - Optional session filter
     * @returns {Array} Array of operations
     */
    getFileOperations(filePath, sessionId = null) {
        const fileData = this.fileChanges.get(filePath);
        if (!fileData) return [];
        
        let operations = fileData.operations;
        if (sessionId) {
            operations = operations.filter(op => op.sessionId === sessionId);
        }
        
        return operations.sort((a, b) => 
            new Date(a.timestamp) - new Date(b.timestamp)
        );
    }
    
    /**
     * Get diff data for a file
     * @param {string} filePath - File path
     * @returns {Object} Diff data with initial and current content
     */
    getFileDiff(filePath) {
        const fileData = this.fileChanges.get(filePath);
        if (!fileData) return null;
        
        return {
            filePath,
            fileName: fileData.fileName,
            initialContent: fileData.initialContent || '',
            currentContent: fileData.currentContent || '',
            hasChanges: fileData.initialContent !== fileData.currentContent,
            operations: fileData.operations,
            totalEdits: fileData.totalEdits,
            totalWrites: fileData.totalWrites
        };
    }
    
    /**
     * Clear all tracked data
     */
    clear() {
        this.fileChanges.clear();
        this.sessionData.clear();
        this.workingDirectories.clear();
        this.events = [];
    }
    
    /**
     * Get statistics
     * @returns {Object} Statistics
     */
    getStatistics() {
        return {
            totalFiles: this.fileChanges.size,
            totalSessions: this.sessionData.size,
            totalDirectories: this.workingDirectories.size,
            filesWithEdits: Array.from(this.fileChanges.values())
                .filter(f => f.totalEdits > 0).length,
            filesWithWrites: Array.from(this.fileChanges.values())
                .filter(f => f.totalWrites > 0).length,
            readOnlyFiles: Array.from(this.fileChanges.values())
                .filter(f => f.totalEdits === 0 && f.totalWrites === 0).length
        };
    }
}

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.FileChangeTracker = FileChangeTracker;
}