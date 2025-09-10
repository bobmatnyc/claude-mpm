/**
 * File Change Viewer Component
 * 
 * Displays files edited by Claude in a tree structure grouped by working directory.
 * Integrates with FileChangeTracker for tracking changes and DiffViewer for showing diffs.
 * Supports session-based filtering and displays change indicators.
 */

class FileChangeViewer {
    constructor() {
        this.modal = null;
        this.currentFile = null;
        this.initialized = false;
        this.fileTracker = null;
        this.diffViewer = null;
        this.currentSessionId = null;
        this.treeContainer = null;
    }

    /**
     * Initialize the file change viewer
     */
    initialize() {
        if (this.initialized) return;
        
        // Create dependent components
        this.fileTracker = new FileChangeTracker();
        this.diffViewer = new DiffViewer();
        
        this.createModal();
        this.setupEventHandlers();
        this.subscribeToEvents();
        this.injectStyles();
        
        this.initialized = true;
        console.log('File change viewer initialized');
    }

    /**
     * Create modal DOM structure
     */
    createModal() {
        const modalHtml = `
            <div class="file-change-modal" id="file-change-modal">
                <div class="file-change-content">
                    <div class="file-change-header">
                        <div class="file-change-title">
                            <span class="title-icon">📝</span>
                            <span class="title-text">Files Changed by Claude</span>
                        </div>
                        <div class="file-change-controls">
                            <div class="session-filter">
                                <label>Session:</label>
                                <select id="file-session-filter" class="session-select">
                                    <option value="">All Sessions</option>
                                </select>
                            </div>
                            <div class="file-stats" id="file-stats">
                                <span class="stat-item">
                                    <span class="stat-icon">📄</span>
                                    <span class="stat-value" id="total-files">0</span>
                                    <span class="stat-label">files</span>
                                </span>
                                <span class="stat-item">
                                    <span class="stat-icon">✏️</span>
                                    <span class="stat-value" id="total-edits">0</span>
                                    <span class="stat-label">edits</span>
                                </span>
                                <span class="stat-item">
                                    <span class="stat-icon">💾</span>
                                    <span class="stat-value" id="total-writes">0</span>
                                    <span class="stat-label">writes</span>
                                </span>
                            </div>
                            <button class="file-change-close" id="file-change-close">×</button>
                        </div>
                    </div>
                    <div class="file-change-body">
                        <div class="file-tree-container" id="file-tree-container">
                            <!-- File tree will be inserted here -->
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Add modal to body
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        this.modal = document.getElementById('file-change-modal');
        this.treeContainer = document.getElementById('file-tree-container');
    }

    /**
     * Inject CSS styles
     */
    injectStyles() {
        const styleId = 'file-change-viewer-styles';
        if (document.getElementById(styleId)) return;
        
        const styles = `
            <style id="${styleId}">
                .file-change-modal {
                    display: none;
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0, 0, 0, 0.5);
                    z-index: 9999;
                    padding: 20px;
                    overflow: auto;
                }
                
                .file-change-modal.show {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                
                .file-change-content {
                    background: white;
                    border-radius: 8px;
                    width: 90%;
                    max-width: 1200px;
                    height: 80%;
                    display: flex;
                    flex-direction: column;
                    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
                }
                
                .file-change-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 16px 20px;
                    border-bottom: 1px solid #e2e8f0;
                    background: #f8fafc;
                    border-radius: 8px 8px 0 0;
                }
                
                .file-change-title {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-size: 16px;
                    font-weight: 600;
                    color: #2d3748;
                }
                
                .title-icon {
                    font-size: 20px;
                }
                
                .file-change-controls {
                    display: flex;
                    align-items: center;
                    gap: 20px;
                }
                
                .session-filter {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }
                
                .session-filter label {
                    font-size: 13px;
                    color: #4a5568;
                }
                
                .session-select {
                    padding: 4px 8px;
                    border: 1px solid #cbd5e0;
                    border-radius: 4px;
                    font-size: 13px;
                    background: white;
                }
                
                .file-stats {
                    display: flex;
                    gap: 16px;
                }
                
                .stat-item {
                    display: flex;
                    align-items: center;
                    gap: 4px;
                    font-size: 13px;
                    color: #4a5568;
                }
                
                .stat-icon {
                    font-size: 14px;
                }
                
                .stat-value {
                    font-weight: 600;
                    color: #2d3748;
                }
                
                .file-change-close {
                    width: 32px;
                    height: 32px;
                    border: none;
                    background: transparent;
                    font-size: 24px;
                    cursor: pointer;
                    color: #718096;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    border-radius: 4px;
                    transition: all 0.2s;
                }
                
                .file-change-close:hover {
                    background: #e2e8f0;
                    color: #2d3748;
                }
                
                .file-change-body {
                    flex: 1;
                    overflow: auto;
                    padding: 20px;
                    background: #fafbfc;
                }
                
                .file-tree-container {
                    display: flex;
                    flex-direction: column;
                    gap: 16px;
                }
                
                /* Directory groups */
                .directory-group {
                    background: white;
                    border: 1px solid #e2e8f0;
                    border-radius: 6px;
                    overflow: hidden;
                }
                
                .directory-header {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 12px 16px;
                    background: #f8fafc;
                    border-bottom: 1px solid #e2e8f0;
                    cursor: pointer;
                    transition: background 0.2s;
                }
                
                .directory-header:hover {
                    background: #f1f5f9;
                }
                
                .directory-info {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }
                
                .directory-icon {
                    font-size: 16px;
                    color: #4299e1;
                }
                
                .directory-path {
                    font-family: 'SF Mono', Monaco, monospace;
                    font-size: 13px;
                    font-weight: 600;
                    color: #2d3748;
                }
                
                .directory-stats {
                    display: flex;
                    gap: 12px;
                    font-size: 12px;
                    color: #718096;
                }
                
                .directory-files {
                    padding: 12px;
                    display: none;
                }
                
                .directory-group.expanded .directory-files {
                    display: block;
                }
                
                .directory-group.expanded .directory-icon::before {
                    content: '📂';
                }
                
                .directory-group:not(.expanded) .directory-icon::before {
                    content: '📁';
                }
                
                /* File items */
                .file-item {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    padding: 10px 12px;
                    background: #f8fafc;
                    border: 1px solid #e2e8f0;
                    border-radius: 4px;
                    margin-bottom: 8px;
                    cursor: pointer;
                    transition: all 0.2s;
                }
                
                .file-item:hover {
                    background: white;
                    border-color: #4299e1;
                    transform: translateX(4px);
                }
                
                .file-item:last-child {
                    margin-bottom: 0;
                }
                
                .file-info {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    flex: 1;
                }
                
                .file-icon {
                    font-size: 14px;
                }
                
                .file-name {
                    font-family: 'SF Mono', Monaco, monospace;
                    font-size: 13px;
                    color: #2d3748;
                    font-weight: 500;
                }
                
                .file-badges {
                    display: flex;
                    gap: 6px;
                }
                
                .file-badge {
                    padding: 2px 6px;
                    font-size: 11px;
                    border-radius: 3px;
                    font-weight: 600;
                }
                
                .badge-edit {
                    background: #fef3c7;
                    color: #92400e;
                }
                
                .badge-write {
                    background: #dbeafe;
                    color: #1e40af;
                }
                
                .badge-read {
                    background: #e0e7ff;
                    color: #3730a3;
                }
                
                .file-timestamp {
                    font-size: 11px;
                    color: #a0aec0;
                }
                
                /* Empty state */
                .empty-state {
                    text-align: center;
                    padding: 40px;
                    color: #718096;
                }
                
                .empty-state-icon {
                    font-size: 48px;
                    margin-bottom: 16px;
                }
                
                .empty-state-text {
                    font-size: 14px;
                }
            </style>
        `;
        
        document.head.insertAdjacentHTML('beforeend', styles);
    }

    /**
     * Setup event handlers
     */
    setupEventHandlers() {
        // Close button
        document.getElementById('file-change-close').addEventListener('click', () => {
            this.hide();
        });
        
        // Close on backdrop click
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.hide();
            }
        });
        
        // Close on ESC key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal.classList.contains('show')) {
                this.hide();
            }
        });
        
        // Session filter
        document.getElementById('file-session-filter').addEventListener('change', (e) => {
            this.currentSessionId = e.target.value;
            this.updateFileTree();
        });
    }

    /**
     * Subscribe to events
     */
    subscribeToEvents() {
        // Subscribe to socket if available
        if (window.socket) {
            // We might want to listen for file operation events
        }
        
        // Listen for event viewer updates
        if (window.eventViewer) {
            // Hook into event updates to refresh our view
            const originalAddEvent = window.eventViewer.addEvent;
            window.eventViewer.addEvent = (event) => {
                originalAddEvent.call(window.eventViewer, event);
                if (this.modal && this.modal.classList.contains('show')) {
                    this.updateFromEvents();
                }
            };
        }
    }

    /**
     * Show the file change viewer
     * @param {Array} events - Optional events to display
     */
    show(events = null) {
        if (!this.initialized) {
            this.initialize();
        }
        
        this.modal.classList.add('show');
        
        // Update with events
        if (events) {
            this.fileTracker.updateEvents(events);
        } else if (window.eventViewer) {
            this.fileTracker.updateEvents(window.eventViewer.events);
        }
        
        // Update session filter
        this.updateSessionFilter();
        
        // Display file tree
        this.updateFileTree();
        
        // Update statistics
        this.updateStatistics();
    }

    /**
     * Hide the file change viewer
     */
    hide() {
        this.modal.classList.remove('show');
        this.currentFile = null;
    }

    /**
     * Update from events
     */
    updateFromEvents() {
        if (window.eventViewer) {
            this.fileTracker.updateEvents(window.eventViewer.events);
            this.updateFileTree();
            this.updateStatistics();
        }
    }

    /**
     * Update session filter dropdown
     */
    updateSessionFilter() {
        const select = document.getElementById('file-session-filter');
        const sessions = Array.from(this.fileTracker.sessionData.keys());
        
        // Clear existing options except "All Sessions"
        select.innerHTML = '<option value="">All Sessions</option>';
        
        // Add session options
        sessions.forEach(sessionId => {
            const option = document.createElement('option');
            option.value = sessionId;
            option.textContent = `Session: ${sessionId.substring(0, 8)}...`;
            select.appendChild(option);
        });
        
        // Restore selection
        if (this.currentSessionId) {
            select.value = this.currentSessionId;
        }
    }

    /**
     * Update file tree display
     */
    updateFileTree() {
        const tree = this.fileTracker.getFileTree(this.currentSessionId);
        
        if (Object.keys(tree).length === 0) {
            this.treeContainer.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">📁</div>
                    <div class="empty-state-text">No file changes detected</div>
                </div>
            `;
            return;
        }
        
        // Build tree HTML
        const treeHtml = Object.entries(tree)
            .sort((a, b) => b[1].totalOperations - a[1].totalOperations)
            .map(([dirPath, dirData]) => this.renderDirectoryGroup(dirPath, dirData))
            .join('');
        
        this.treeContainer.innerHTML = treeHtml;
        
        // Add event handlers
        this.attachTreeHandlers();
    }

    /**
     * Render a directory group
     * @param {string} dirPath - Directory path
     * @param {Object} dirData - Directory data
     * @returns {string} HTML
     */
    renderDirectoryGroup(dirPath, dirData) {
        const displayPath = dirPath === 'unknown' ? 'Unknown Directory' : dirPath;
        
        return `
            <div class="directory-group" data-path="${dirPath}">
                <div class="directory-header">
                    <div class="directory-info">
                        <span class="directory-icon"></span>
                        <span class="directory-path">${this.escapeHtml(displayPath)}</span>
                    </div>
                    <div class="directory-stats">
                        <span>${dirData.files.length} files</span>
                        <span>${dirData.totalEdits} edits</span>
                        <span>${dirData.totalWrites} writes</span>
                    </div>
                </div>
                <div class="directory-files">
                    ${dirData.files.map(file => this.renderFileItem(file)).join('')}
                </div>
            </div>
        `;
    }

    /**
     * Render a file item
     * @param {Object} fileData - File data
     * @returns {string} HTML
     */
    renderFileItem(fileData) {
        const badges = [];
        if (fileData.totalEdits > 0) {
            badges.push(`<span class="file-badge badge-edit">✏️ ${fileData.totalEdits}</span>`);
        }
        if (fileData.totalWrites > 0) {
            badges.push(`<span class="file-badge badge-write">💾 ${fileData.totalWrites}</span>`);
        }
        if (fileData.totalReads > 0 && fileData.totalEdits === 0 && fileData.totalWrites === 0) {
            badges.push(`<span class="file-badge badge-read">👁️ ${fileData.totalReads}</span>`);
        }
        
        const timestamp = new Date(fileData.lastModified).toLocaleTimeString();
        
        return `
            <div class="file-item" data-path="${fileData.path}">
                <div class="file-info">
                    <span class="file-icon">📄</span>
                    <span class="file-name">${this.escapeHtml(fileData.fileName)}</span>
                    <div class="file-badges">${badges.join('')}</div>
                </div>
                <span class="file-timestamp">${timestamp}</span>
            </div>
        `;
    }

    /**
     * Attach tree event handlers
     */
    attachTreeHandlers() {
        // Directory headers - toggle expansion
        document.querySelectorAll('.directory-header').forEach(header => {
            header.addEventListener('click', (e) => {
                const group = header.closest('.directory-group');
                group.classList.toggle('expanded');
            });
        });
        
        // File items - show diff or content
        document.querySelectorAll('.file-item').forEach(item => {
            item.addEventListener('click', (e) => {
                e.stopPropagation();
                const filePath = item.dataset.path;
                this.showFileDetails(filePath);
            });
        });
        
        // Auto-expand first directory
        const firstDir = document.querySelector('.directory-group');
        if (firstDir) {
            firstDir.classList.add('expanded');
        }
    }

    /**
     * Show file details (diff or content)
     * @param {string} filePath - File path
     */
    showFileDetails(filePath) {
        const fileData = this.fileTracker.getFileDetails(filePath);
        if (!fileData) return;
        
        // If file has edits or writes, show diff
        if (fileData.totalEdits > 0 || fileData.totalWrites > 0) {
            const diffData = this.fileTracker.getFileDiff(filePath);
            if (diffData) {
                this.diffViewer.show(diffData);
            }
        } else {
            // For read-only files, could show content in a simple viewer
            console.log('Read-only file:', filePath);
            // Could implement a simple content viewer here
        }
    }

    /**
     * Update statistics
     */
    updateStatistics() {
        const stats = this.fileTracker.getStatistics();
        
        document.getElementById('total-files').textContent = stats.totalFiles;
        document.getElementById('total-edits').textContent = 
            Array.from(this.fileTracker.fileChanges.values())
                .reduce((sum, f) => sum + f.totalEdits, 0);
        document.getElementById('total-writes').textContent = 
            Array.from(this.fileTracker.fileChanges.values())
                .reduce((sum, f) => sum + f.totalWrites, 0);
    }

    /**
     * Escape HTML for safe display
     * @param {string} text - Text to escape
     * @returns {string} Escaped text
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }
}

// Create singleton instance
const fileChangeViewer = new FileChangeViewer();

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.FileChangeViewer = fileChangeViewer;
}

export default fileChangeViewer;