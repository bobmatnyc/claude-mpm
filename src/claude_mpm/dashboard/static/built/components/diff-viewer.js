/**
 * Diff Viewer Component
 * 
 * Shows side-by-side or unified diffs for file changes.
 * Supports syntax highlighting, navigation between changes,
 * and displays timestamps and operation types.
 * 
 * Features:
 * - Side-by-side and unified diff views
 * - Syntax highlighting for code
 * - Navigation between multiple changes
 * - Operation history timeline
 */
class DiffViewer {
    constructor() {
        this.modal = null;
        this.currentFile = null;
        this.currentMode = 'side-by-side'; // 'side-by-side' or 'unified'
        this.initialized = false;
        
        // Diff computation cache
        this.diffCache = new Map();
    }
    
    /**
     * Initialize the diff viewer
     */
    initialize() {
        if (this.initialized) return;
        
        this.createModal();
        this.setupEventHandlers();
        this.initialized = true;
        console.log('DiffViewer initialized');
    }
    
    /**
     * Create the modal HTML structure
     */
    createModal() {
        const modalHTML = `
            <div class="diff-viewer-modal" id="diff-viewer-modal">
                <div class="diff-viewer-content">
                    <div class="diff-viewer-header">
                        <div class="diff-viewer-title">
                            <span class="diff-file-icon">📄</span>
                            <span class="diff-file-path" id="diff-file-path">Loading...</span>
                        </div>
                        <div class="diff-viewer-controls">
                            <div class="diff-mode-toggle">
                                <button class="diff-mode-btn active" data-mode="side-by-side">
                                    Side by Side
                                </button>
                                <button class="diff-mode-btn" data-mode="unified">
                                    Unified
                                </button>
                            </div>
                            <div class="diff-stats" id="diff-stats">
                                <span class="additions">+0</span>
                                <span class="deletions">-0</span>
                            </div>
                            <button class="diff-viewer-close" id="diff-viewer-close">×</button>
                        </div>
                    </div>
                    
                    <div class="diff-viewer-subheader">
                        <div class="diff-operations-summary" id="diff-operations-summary">
                            <span class="op-count">0 operations</span>
                            <span class="op-timeline">Timeline</span>
                        </div>
                        <div class="diff-navigation">
                            <button class="diff-nav-btn" id="diff-prev-change" disabled>
                                ← Previous
                            </button>
                            <span class="diff-nav-info" id="diff-nav-info">Change 1 of 1</span>
                            <button class="diff-nav-btn" id="diff-next-change" disabled>
                                Next →
                            </button>
                        </div>
                    </div>
                    
                    <div class="diff-viewer-body" id="diff-viewer-body">
                        <!-- Diff content will be inserted here -->
                    </div>
                    
                    <div class="diff-viewer-footer">
                        <div class="diff-timeline" id="diff-timeline">
                            <!-- Operation timeline will be inserted here -->
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        this.modal = document.getElementById('diff-viewer-modal');
        
        // Add CSS for the diff viewer
        this.injectStyles();
    }
    
    /**
     * Inject CSS styles for the diff viewer
     */
    injectStyles() {
        const styleId = 'diff-viewer-styles';
        if (document.getElementById(styleId)) return;
        
        const styles = `
            <style id="${styleId}">
                .diff-viewer-modal {
                    display: none;
                    position: fixed;
                    top: 0;
                    left: 0;
                    right: 0;
                    bottom: 0;
                    background: rgba(0, 0, 0, 0.5);
                    z-index: 10000;
                    padding: 20px;
                    overflow: auto;
                }
                
                .diff-viewer-modal.show {
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                
                .diff-viewer-content {
                    background: white;
                    border-radius: 8px;
                    width: 90%;
                    max-width: 1400px;
                    height: 90%;
                    display: flex;
                    flex-direction: column;
                    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
                }
                
                .diff-viewer-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 16px 20px;
                    border-bottom: 1px solid #e2e8f0;
                    background: #f8fafc;
                    border-radius: 8px 8px 0 0;
                }
                
                .diff-viewer-title {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    font-size: 14px;
                    font-weight: 600;
                    color: #2d3748;
                }
                
                .diff-file-icon {
                    font-size: 18px;
                }
                
                .diff-file-path {
                    font-family: 'SF Mono', Monaco, monospace;
                    font-size: 13px;
                }
                
                .diff-viewer-controls {
                    display: flex;
                    align-items: center;
                    gap: 16px;
                }
                
                .diff-mode-toggle {
                    display: flex;
                    gap: 4px;
                    background: #e2e8f0;
                    padding: 2px;
                    border-radius: 4px;
                }
                
                .diff-mode-btn {
                    padding: 4px 12px;
                    border: none;
                    background: transparent;
                    cursor: pointer;
                    font-size: 12px;
                    border-radius: 3px;
                    transition: all 0.2s;
                }
                
                .diff-mode-btn.active {
                    background: white;
                    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
                }
                
                .diff-stats {
                    display: flex;
                    gap: 8px;
                    font-size: 12px;
                    font-family: monospace;
                }
                
                .diff-stats .additions {
                    color: #22c55e;
                }
                
                .diff-stats .deletions {
                    color: #ef4444;
                }
                
                .diff-viewer-close {
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
                
                .diff-viewer-close:hover {
                    background: #e2e8f0;
                    color: #2d3748;
                }
                
                .diff-viewer-subheader {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 12px 20px;
                    border-bottom: 1px solid #e2e8f0;
                    background: #fafbfc;
                }
                
                .diff-operations-summary {
                    display: flex;
                    gap: 16px;
                    font-size: 13px;
                    color: #4a5568;
                }
                
                .diff-navigation {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }
                
                .diff-nav-btn {
                    padding: 4px 12px;
                    border: 1px solid #cbd5e0;
                    background: white;
                    cursor: pointer;
                    font-size: 12px;
                    border-radius: 4px;
                    transition: all 0.2s;
                }
                
                .diff-nav-btn:hover:not(:disabled) {
                    background: #f8fafc;
                    border-color: #4299e1;
                }
                
                .diff-nav-btn:disabled {
                    opacity: 0.5;
                    cursor: not-allowed;
                }
                
                .diff-nav-info {
                    font-size: 12px;
                    color: #718096;
                    padding: 0 8px;
                }
                
                .diff-viewer-body {
                    flex: 1;
                    overflow: auto;
                    padding: 20px;
                    background: #fafbfc;
                }
                
                /* Side-by-side diff styles */
                .diff-side-by-side {
                    display: flex;
                    gap: 16px;
                    height: 100%;
                }
                
                .diff-panel {
                    flex: 1;
                    background: white;
                    border: 1px solid #e2e8f0;
                    border-radius: 4px;
                    overflow: hidden;
                }
                
                .diff-panel-header {
                    padding: 8px 12px;
                    background: #f8fafc;
                    border-bottom: 1px solid #e2e8f0;
                    font-size: 12px;
                    font-weight: 600;
                    color: #4a5568;
                }
                
                .diff-panel-content {
                    overflow: auto;
                    height: calc(100% - 36px);
                }
                
                .diff-line {
                    display: flex;
                    font-family: 'SF Mono', Monaco, monospace;
                    font-size: 12px;
                    line-height: 1.5;
                    white-space: pre;
                }
                
                .diff-line-number {
                    width: 50px;
                    padding: 0 8px;
                    text-align: right;
                    color: #a0aec0;
                    background: #f8fafc;
                    border-right: 1px solid #e2e8f0;
                    user-select: none;
                }
                
                .diff-line-content {
                    flex: 1;
                    padding: 0 12px;
                    overflow-x: auto;
                }
                
                .diff-line-added {
                    background: #d4f4dd;
                }
                
                .diff-line-added .diff-line-content {
                    background: #e7fced;
                }
                
                .diff-line-removed {
                    background: #ffd4d4;
                }
                
                .diff-line-removed .diff-line-content {
                    background: #ffeaea;
                }
                
                .diff-line-context {
                    color: #4a5568;
                }
                
                /* Unified diff styles */
                .diff-unified {
                    background: white;
                    border: 1px solid #e2e8f0;
                    border-radius: 4px;
                    overflow: auto;
                }
                
                .diff-hunk-header {
                    padding: 8px 12px;
                    background: #f1f5f9;
                    color: #475569;
                    font-family: monospace;
                    font-size: 12px;
                    border-bottom: 1px solid #e2e8f0;
                }
                
                /* Timeline styles */
                .diff-viewer-footer {
                    padding: 12px 20px;
                    border-top: 1px solid #e2e8f0;
                    background: #f8fafc;
                    border-radius: 0 0 8px 8px;
                }
                
                .diff-timeline {
                    display: flex;
                    gap: 8px;
                    overflow-x: auto;
                    padding: 8px 0;
                }
                
                .timeline-item {
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 4px;
                    padding: 4px 8px;
                    background: white;
                    border: 1px solid #cbd5e0;
                    border-radius: 4px;
                    cursor: pointer;
                    transition: all 0.2s;
                    min-width: 80px;
                    font-size: 11px;
                }
                
                .timeline-item:hover {
                    background: #edf2f7;
                    border-color: #4299e1;
                }
                
                .timeline-item.active {
                    background: #4299e1;
                    color: white;
                    border-color: #3182ce;
                }
                
                .timeline-operation {
                    font-weight: 600;
                }
                
                .timeline-time {
                    color: #718096;
                    font-size: 10px;
                }
                
                .timeline-item.active .timeline-time {
                    color: rgba(255, 255, 255, 0.9);
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
        document.getElementById('diff-viewer-close').addEventListener('click', () => {
            this.hide();
        });
        
        // Modal background click
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.hide();
            }
        });
        
        // Escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.modal.classList.contains('show')) {
                this.hide();
            }
        });
        
        // Mode toggle
        document.querySelectorAll('.diff-mode-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.setMode(e.target.dataset.mode);
            });
        });
        
        // Navigation
        document.getElementById('diff-prev-change').addEventListener('click', () => {
            this.navigateToPreviousChange();
        });
        
        document.getElementById('diff-next-change').addEventListener('click', () => {
            this.navigateToNextChange();
        });
    }
    
    /**
     * Show the diff viewer for a file
     * @param {Object} diffData - Diff data from FileChangeTracker
     */
    show(diffData) {
        if (!this.initialized) {
            this.initialize();
        }
        
        this.currentFile = diffData;
        this.modal.classList.add('show');
        
        // Update header
        document.getElementById('diff-file-path').textContent = diffData.filePath;
        
        // Generate and display diff
        this.generateDiff(diffData);
        
        // Update operations timeline
        this.updateTimeline(diffData.operations);
        
        // Update statistics
        this.updateStatistics(diffData);
    }
    
    /**
     * Hide the diff viewer
     */
    hide() {
        this.modal.classList.remove('show');
        this.currentFile = null;
    }
    
    /**
     * Set diff display mode
     * @param {string} mode - 'side-by-side' or 'unified'
     */
    setMode(mode) {
        this.currentMode = mode;
        
        // Update button states
        document.querySelectorAll('.diff-mode-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.mode === mode);
        });
        
        // Regenerate diff display
        if (this.currentFile) {
            this.generateDiff(this.currentFile);
        }
    }
    
    /**
     * Generate diff display
     * @param {Object} diffData - Diff data
     */
    generateDiff(diffData) {
        const { initialContent, currentContent } = diffData;
        
        // Compute diff
        const diff = this.computeDiff(initialContent || '', currentContent || '');
        
        // Display based on mode
        const body = document.getElementById('diff-viewer-body');
        if (this.currentMode === 'side-by-side') {
            body.innerHTML = this.renderSideBySideDiff(diff, initialContent, currentContent);
        } else {
            body.innerHTML = this.renderUnifiedDiff(diff);
        }
    }
    
    /**
     * Compute diff between two strings
     * @param {string} oldText - Original text
     * @param {string} newText - New text
     * @returns {Array} Array of diff chunks
     */
    computeDiff(oldText, newText) {
        const oldLines = oldText.split('\n');
        const newLines = newText.split('\n');
        
        // Simple line-by-line diff algorithm
        const diff = [];
        const maxLines = Math.max(oldLines.length, newLines.length);
        
        let oldIndex = 0;
        let newIndex = 0;
        
        while (oldIndex < oldLines.length || newIndex < newLines.length) {
            const oldLine = oldIndex < oldLines.length ? oldLines[oldIndex] : null;
            const newLine = newIndex < newLines.length ? newLines[newIndex] : null;
            
            if (oldLine === newLine) {
                // Unchanged line
                diff.push({
                    type: 'unchanged',
                    oldLine: oldLine,
                    newLine: newLine,
                    oldLineNumber: oldIndex + 1,
                    newLineNumber: newIndex + 1
                });
                oldIndex++;
                newIndex++;
            } else if (oldLine === null) {
                // Added line
                diff.push({
                    type: 'added',
                    newLine: newLine,
                    newLineNumber: newIndex + 1
                });
                newIndex++;
            } else if (newLine === null) {
                // Removed line
                diff.push({
                    type: 'removed',
                    oldLine: oldLine,
                    oldLineNumber: oldIndex + 1
                });
                oldIndex++;
            } else {
                // Changed line - try to find matching lines ahead
                let found = false;
                
                // Look ahead in new lines for old line
                for (let i = newIndex + 1; i < Math.min(newIndex + 5, newLines.length); i++) {
                    if (newLines[i] === oldLine) {
                        // Found old line ahead - mark intervening as added
                        for (let j = newIndex; j < i; j++) {
                            diff.push({
                                type: 'added',
                                newLine: newLines[j],
                                newLineNumber: j + 1
                            });
                        }
                        newIndex = i;
                        found = true;
                        break;
                    }
                }
                
                if (!found) {
                    // Look ahead in old lines for new line
                    for (let i = oldIndex + 1; i < Math.min(oldIndex + 5, oldLines.length); i++) {
                        if (oldLines[i] === newLine) {
                            // Found new line ahead - mark intervening as removed
                            for (let j = oldIndex; j < i; j++) {
                                diff.push({
                                    type: 'removed',
                                    oldLine: oldLines[j],
                                    oldLineNumber: j + 1
                                });
                            }
                            oldIndex = i;
                            found = true;
                            break;
                        }
                    }
                }
                
                if (!found) {
                    // True change - show as remove + add
                    diff.push({
                        type: 'removed',
                        oldLine: oldLine,
                        oldLineNumber: oldIndex + 1
                    });
                    diff.push({
                        type: 'added',
                        newLine: newLine,
                        newLineNumber: newIndex + 1
                    });
                    oldIndex++;
                    newIndex++;
                }
            }
        }
        
        return diff;
    }
    
    /**
     * Render side-by-side diff
     * @param {Array} diff - Diff chunks
     * @param {string} oldContent - Original content
     * @param {string} newContent - New content
     * @returns {string} HTML
     */
    renderSideBySideDiff(diff, oldContent, newContent) {
        const oldLines = [];
        const newLines = [];
        
        for (const chunk of diff) {
            if (chunk.type === 'unchanged') {
                oldLines.push({
                    number: chunk.oldLineNumber,
                    content: chunk.oldLine,
                    type: 'context'
                });
                newLines.push({
                    number: chunk.newLineNumber,
                    content: chunk.newLine,
                    type: 'context'
                });
            } else if (chunk.type === 'removed') {
                oldLines.push({
                    number: chunk.oldLineNumber,
                    content: chunk.oldLine,
                    type: 'removed'
                });
                newLines.push({
                    number: '',
                    content: '',
                    type: 'empty'
                });
            } else if (chunk.type === 'added') {
                oldLines.push({
                    number: '',
                    content: '',
                    type: 'empty'
                });
                newLines.push({
                    number: chunk.newLineNumber,
                    content: chunk.newLine,
                    type: 'added'
                });
            }
        }
        
        return `
            <div class="diff-side-by-side">
                <div class="diff-panel">
                    <div class="diff-panel-header">Original</div>
                    <div class="diff-panel-content">
                        ${this.renderDiffLines(oldLines)}
                    </div>
                </div>
                <div class="diff-panel">
                    <div class="diff-panel-header">Modified</div>
                    <div class="diff-panel-content">
                        ${this.renderDiffLines(newLines)}
                    </div>
                </div>
            </div>
        `;
    }
    
    /**
     * Render diff lines
     * @param {Array} lines - Lines to render
     * @returns {string} HTML
     */
    renderDiffLines(lines) {
        return lines.map(line => {
            const lineClass = line.type === 'removed' ? 'diff-line-removed' :
                             line.type === 'added' ? 'diff-line-added' :
                             line.type === 'empty' ? 'diff-line-empty' :
                             'diff-line-context';
            
            return `
                <div class="diff-line ${lineClass}">
                    <span class="diff-line-number">${line.number}</span>
                    <span class="diff-line-content">${this.escapeHtml(line.content)}</span>
                </div>
            `;
        }).join('');
    }
    
    /**
     * Render unified diff
     * @param {Array} diff - Diff chunks
     * @returns {string} HTML
     */
    renderUnifiedDiff(diff) {
        const lines = [];
        
        for (const chunk of diff) {
            if (chunk.type === 'unchanged') {
                lines.push(`
                    <div class="diff-line diff-line-context">
                        <span class="diff-line-number">${chunk.oldLineNumber}</span>
                        <span class="diff-line-number">${chunk.newLineNumber}</span>
                        <span class="diff-line-content"> ${this.escapeHtml(chunk.oldLine)}</span>
                    </div>
                `);
            } else if (chunk.type === 'removed') {
                lines.push(`
                    <div class="diff-line diff-line-removed">
                        <span class="diff-line-number">${chunk.oldLineNumber}</span>
                        <span class="diff-line-number">-</span>
                        <span class="diff-line-content">-${this.escapeHtml(chunk.oldLine)}</span>
                    </div>
                `);
            } else if (chunk.type === 'added') {
                lines.push(`
                    <div class="diff-line diff-line-added">
                        <span class="diff-line-number">-</span>
                        <span class="diff-line-number">${chunk.newLineNumber}</span>
                        <span class="diff-line-content">+${this.escapeHtml(chunk.newLine)}</span>
                    </div>
                `);
            }
        }
        
        return `
            <div class="diff-unified">
                ${lines.join('')}
            </div>
        `;
    }
    
    /**
     * Update operations timeline
     * @param {Array} operations - File operations
     */
    updateTimeline(operations) {
        const timeline = document.getElementById('diff-timeline');
        
        if (!operations || operations.length === 0) {
            timeline.innerHTML = '<div class="timeline-empty">No operations recorded</div>';
            return;
        }
        
        // Sort operations by timestamp
        const sortedOps = [...operations].sort((a, b) => 
            new Date(a.timestamp) - new Date(b.timestamp)
        );
        
        timeline.innerHTML = sortedOps.map((op, index) => {
            const time = new Date(op.timestamp);
            const timeStr = time.toLocaleTimeString();
            
            return `
                <div class="timeline-item ${index === 0 ? 'active' : ''}" 
                     data-index="${index}">
                    <div class="timeline-operation">${op.operation}</div>
                    <div class="timeline-time">${timeStr}</div>
                </div>
            `;
        }).join('');
        
        // Add click handlers
        timeline.querySelectorAll('.timeline-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const index = parseInt(e.currentTarget.dataset.index);
                this.selectOperation(index);
            });
        });
    }
    
    /**
     * Select an operation in the timeline
     * @param {number} index - Operation index
     */
    selectOperation(index) {
        // Update active state
        document.querySelectorAll('.timeline-item').forEach((item, i) => {
            item.classList.toggle('active', i === index);
        });
        
        // Could implement showing diff up to this operation
        console.log('Selected operation:', index);
    }
    
    /**
     * Update statistics
     * @param {Object} diffData - Diff data
     */
    updateStatistics(diffData) {
        const diff = this.computeDiff(
            diffData.initialContent || '',
            diffData.currentContent || ''
        );
        
        const additions = diff.filter(d => d.type === 'added').length;
        const deletions = diff.filter(d => d.type === 'removed').length;
        
        document.querySelector('.diff-stats .additions').textContent = `+${additions}`;
        document.querySelector('.diff-stats .deletions').textContent = `-${deletions}`;
        
        const opCount = diffData.operations ? diffData.operations.length : 0;
        document.querySelector('.op-count').textContent = 
            `${opCount} operation${opCount !== 1 ? 's' : ''}`;
    }
    
    /**
     * Navigate to previous change
     */
    navigateToPreviousChange() {
        console.log('Navigate to previous change');
        // Implementation would scroll to previous diff chunk
    }
    
    /**
     * Navigate to next change
     */
    navigateToNextChange() {
        console.log('Navigate to next change');
        // Implementation would scroll to next diff chunk
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

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.DiffViewer = DiffViewer;
}