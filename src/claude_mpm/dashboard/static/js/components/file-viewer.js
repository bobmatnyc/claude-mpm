/**
 * File Viewer Component
 * 
 * A simple file content viewer that displays file contents in a modal window.
 * This component handles file loading via HTTP requests and displays the content
 * with basic syntax highlighting support.
 */

class FileViewer {
    constructor() {
        this.modal = null;
        this.currentFile = null;
        this.initialized = false;
        this.contentCache = new Map();
    }

    /**
     * Initialize the file viewer
     */
    initialize() {
        if (this.initialized) {
            return;
        }

        this.createModal();
        this.setupEventHandlers();
        
        this.initialized = true;
        console.log('File viewer initialized');
    }

    /**
     * Create modal DOM structure
     */
    createModal() {
        const modalHtml = `
            <div class="file-viewer-modal" id="file-viewer-modal">
                <div class="file-viewer-content">
                    <div class="file-viewer-header">
                        <h2>📄 File Viewer</h2>
                        <button class="file-viewer-close" id="file-viewer-close">×</button>
                    </div>
                    <div class="file-viewer-path" id="file-viewer-path">
                        Loading...
                    </div>
                    <div class="file-viewer-body">
                        <pre class="file-viewer-code" id="file-viewer-code">
                            <code id="file-viewer-code-content">Loading file content...</code>
                        </pre>
                    </div>
                    <div class="file-viewer-footer">
                        <div class="file-viewer-info">
                            <span id="file-viewer-type">Type: --</span>
                            <span id="file-viewer-lines">Lines: --</span>
                            <span id="file-viewer-size">Size: --</span>
                        </div>
                        <button class="file-viewer-copy" id="file-viewer-copy">📋 Copy</button>
                    </div>
                </div>
            </div>
        `;

        // Add modal to body
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        this.modal = document.getElementById('file-viewer-modal');

        // Add styles if not already present
        if (!document.getElementById('file-viewer-styles')) {
            const styles = `
                <style id="file-viewer-styles">
                    .file-viewer-modal {
                        display: none;
                        position: fixed;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        background: rgba(0, 0, 0, 0.7);
                        z-index: 10000;
                        animation: fadeIn 0.2s;
                    }

                    .file-viewer-modal.show {
                        display: flex;
                        align-items: center;
                        justify-content: center;
                    }

                    .file-viewer-content {
                        background: #1e1e1e;
                        border-radius: 8px;
                        width: 90%;
                        max-width: 1200px;
                        height: 80%;
                        display: flex;
                        flex-direction: column;
                        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
                    }

                    .file-viewer-header {
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        padding: 15px 20px;
                        background: #2d2d30;
                        border-radius: 8px 8px 0 0;
                        border-bottom: 1px solid #3e3e42;
                    }

                    .file-viewer-header h2 {
                        margin: 0;
                        color: #cccccc;
                        font-size: 18px;
                    }

                    .file-viewer-close {
                        background: none;
                        border: none;
                        color: #999;
                        font-size: 24px;
                        cursor: pointer;
                        padding: 0;
                        width: 30px;
                        height: 30px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                    }

                    .file-viewer-close:hover {
                        color: #fff;
                    }

                    .file-viewer-path {
                        padding: 10px 20px;
                        background: #252526;
                        color: #8b8b8b;
                        font-family: 'Consolas', 'Monaco', monospace;
                        font-size: 12px;
                        border-bottom: 1px solid #3e3e42;
                        word-break: break-all;
                    }

                    .file-viewer-body {
                        flex: 1;
                        overflow: auto;
                        padding: 20px;
                        background: #1e1e1e;
                    }

                    .file-viewer-code {
                        margin: 0;
                        padding: 0;
                        background: transparent;
                        overflow: visible;
                    }

                    .file-viewer-code code {
                        font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
                        font-size: 13px;
                        line-height: 1.5;
                        color: #d4d4d4;
                        white-space: pre;
                        display: block;
                    }

                    .file-viewer-footer {
                        padding: 15px 20px;
                        background: #2d2d30;
                        border-top: 1px solid #3e3e42;
                        display: flex;
                        justify-content: space-between;
                        align-items: center;
                        border-radius: 0 0 8px 8px;
                    }

                    .file-viewer-info {
                        display: flex;
                        gap: 20px;
                        color: #8b8b8b;
                        font-size: 12px;
                    }

                    .file-viewer-copy {
                        background: #0e639c;
                        color: white;
                        border: none;
                        padding: 6px 12px;
                        border-radius: 4px;
                        cursor: pointer;
                        font-size: 12px;
                    }

                    .file-viewer-copy:hover {
                        background: #1177bb;
                    }

                    .file-viewer-copy.copied {
                        background: #4ec9b0;
                    }

                    .file-viewer-error {
                        color: #f48771;
                        padding: 20px;
                        text-align: center;
                    }

                    @keyframes fadeIn {
                        from { opacity: 0; }
                        to { opacity: 1; }
                    }
                </style>
            `;
            document.head.insertAdjacentHTML('beforeend', styles);
        }
    }

    /**
     * Setup event handlers
     */
    setupEventHandlers() {
        // Close button
        document.getElementById('file-viewer-close').addEventListener('click', () => {
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

        // Copy button
        document.getElementById('file-viewer-copy').addEventListener('click', () => {
            this.copyContent();
        });
    }

    /**
     * Show the file viewer with file content
     */
    async show(filePath) {
        console.log('[FileViewer] show() called with path:', filePath);
        console.log('[FileViewer] initialized:', this.initialized);
        
        if (!this.initialized) {
            console.log('[FileViewer] Not initialized, initializing now...');
            this.initialize();
        }

        this.currentFile = filePath;
        this.modal.classList.add('show');
        
        // Update path
        document.getElementById('file-viewer-path').textContent = filePath;
        
        console.log('[FileViewer] Modal shown, loading file content...');
        // Load file content
        await this.loadFileContent(filePath);
    }

    /**
     * Hide the file viewer
     */
    hide() {
        this.modal.classList.remove('show');
        this.currentFile = null;
    }

    /**
     * Load file content
     */
    async loadFileContent(filePath) {
        const codeContent = document.getElementById('file-viewer-code-content');
        
        console.log('[FileViewer] loadFileContent called with path:', filePath);
        
        // Check cache first
        if (this.contentCache.has(filePath)) {
            console.log('[FileViewer] Using cached content for:', filePath);
            this.displayContent(this.contentCache.get(filePath));
            return;
        }
        
        // Show loading state
        codeContent.textContent = 'Loading file content...';
        
        try {
            // Check if we have a socket connection available
            if (window.socket && window.socket.connected) {
                console.log('[FileViewer] Using Socket.IO to load file:', filePath);
                
                // Create a promise to wait for the response
                const responsePromise = new Promise((resolve, reject) => {
                    const timeoutId = setTimeout(() => {
                        console.error('[FileViewer] Socket.IO request timed out for:', filePath);
                        reject(new Error('Socket.IO request timed out'));
                    }, 10000); // 10 second timeout
                    
                    // Set up one-time listener for the response
                    window.socket.once('file_content_response', (data) => {
                        clearTimeout(timeoutId);
                        console.log('[FileViewer] Received file_content_response:', data);
                        resolve(data);
                    });
                    
                    // Emit the read_file event
                    console.log('[FileViewer] Emitting read_file event with data:', {
                        file_path: filePath,
                        working_dir: window.workingDirectory || '/',
                        max_size: 5 * 1024 * 1024  // 5MB limit
                    });
                    
                    window.socket.emit('read_file', {
                        file_path: filePath,
                        working_dir: window.workingDirectory || '/',
                        max_size: 5 * 1024 * 1024  // 5MB limit
                    });
                });
                
                // Wait for the response
                const data = await responsePromise;
                
                if (data.success && data.content !== undefined) {
                    console.log('[FileViewer] Successfully loaded file content, caching...');
                    // Cache the content
                    this.contentCache.set(filePath, data.content);
                    
                    // Display the content
                    this.displayContent(data.content);
                    
                    // Update file info
                    this.updateFileInfo(data);
                } else {
                    console.error('[FileViewer] Server returned error:', data.error);
                    throw new Error(data.error || 'Failed to load file content');
                }
            } else {
                console.error('[FileViewer] No Socket.IO connection available');
                throw new Error('No socket connection available. Please ensure the dashboard is connected to the monitoring server.');
            }
        } catch (error) {
            console.error('[FileViewer] Error loading file:', error);
            console.error('[FileViewer] Error stack:', error.stack);
            
            // If API fails, show error message with helpful information
            this.displayError(filePath, error.message);
        }
    }

    /**
     * Display file content
     */
    displayContent(content) {
        const codeContent = document.getElementById('file-viewer-code-content');
        
        // Set the content
        codeContent.textContent = content || '(Empty file)';
        
        // Update line count
        const lines = content ? content.split('\n').length : 0;
        document.getElementById('file-viewer-lines').textContent = `Lines: ${lines}`;
        
        // Update file size
        const size = content ? new Blob([content]).size : 0;
        document.getElementById('file-viewer-size').textContent = `Size: ${this.formatFileSize(size)}`;
        
        // Detect and set file type
        const fileType = this.detectFileType(this.currentFile);
        document.getElementById('file-viewer-type').textContent = `Type: ${fileType}`;
        
        // Apply syntax highlighting if Prism is available
        if (window.Prism) {
            const language = this.detectLanguage(this.currentFile);
            codeContent.className = `language-${language}`;
            Prism.highlightElement(codeContent);
        }
    }

    /**
     * Display error message
     */
    displayError(filePath, errorMessage) {
        const codeContent = document.getElementById('file-viewer-code-content');
        
        // For now, show a helpful message since the API endpoint doesn't exist yet
        const errorHtml = `
            <div class="file-viewer-error">
                ⚠️ File content loading is not yet implemented
                
                File path: ${filePath}
                
                The file viewing functionality requires:
                1. A server-side /api/file endpoint
                2. Proper file reading permissions
                3. Security validation for file access
                
                Error: ${errorMessage}
                
                This feature will be available once the backend API is implemented.
            </div>
        `;
        
        codeContent.innerHTML = errorHtml;
        
        // Update info
        document.getElementById('file-viewer-lines').textContent = 'Lines: --';
        document.getElementById('file-viewer-size').textContent = 'Size: --';
        document.getElementById('file-viewer-type').textContent = 'Type: --';
    }

    /**
     * Update file info
     */
    updateFileInfo(data) {
        if (data.lines !== undefined) {
            document.getElementById('file-viewer-lines').textContent = `Lines: ${data.lines}`;
        }
        
        if (data.size !== undefined) {
            document.getElementById('file-viewer-size').textContent = `Size: ${this.formatFileSize(data.size)}`;
        }
        
        if (data.type) {
            document.getElementById('file-viewer-type').textContent = `Type: ${data.type}`;
        }
    }

    /**
     * Format file size for display
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    /**
     * Detect file type from path
     */
    detectFileType(path) {
        if (!path) return 'Unknown';
        
        const ext = path.split('.').pop()?.toLowerCase();
        const typeMap = {
            'py': 'Python',
            'js': 'JavaScript',
            'ts': 'TypeScript',
            'jsx': 'React JSX',
            'tsx': 'React TSX',
            'html': 'HTML',
            'css': 'CSS',
            'json': 'JSON',
            'xml': 'XML',
            'yaml': 'YAML',
            'yml': 'YAML',
            'md': 'Markdown',
            'txt': 'Text',
            'sh': 'Shell Script',
            'bash': 'Bash Script',
            'sql': 'SQL',
            'go': 'Go',
            'rs': 'Rust',
            'java': 'Java',
            'cpp': 'C++',
            'c': 'C',
            'cs': 'C#',
            'rb': 'Ruby',
            'php': 'PHP'
        };
        
        return typeMap[ext] || 'Text';
    }

    /**
     * Detect language for syntax highlighting
     */
    detectLanguage(path) {
        if (!path) return 'plaintext';
        
        const ext = path.split('.').pop()?.toLowerCase();
        const languageMap = {
            'py': 'python',
            'js': 'javascript',
            'ts': 'typescript',
            'jsx': 'jsx',
            'tsx': 'tsx',
            'html': 'html',
            'css': 'css',
            'json': 'json',
            'xml': 'xml',
            'yaml': 'yaml',
            'yml': 'yaml',
            'md': 'markdown',
            'sh': 'bash',
            'bash': 'bash',
            'sql': 'sql',
            'go': 'go',
            'rs': 'rust',
            'java': 'java',
            'cpp': 'cpp',
            'c': 'c',
            'cs': 'csharp',
            'rb': 'ruby',
            'php': 'php'
        };
        
        return languageMap[ext] || 'plaintext';
    }

    /**
     * Copy file content to clipboard
     */
    async copyContent() {
        const codeContent = document.getElementById('file-viewer-code-content');
        const button = document.getElementById('file-viewer-copy');
        const content = codeContent.textContent;
        
        try {
            await navigator.clipboard.writeText(content);
            
            // Show feedback
            const originalText = button.textContent;
            button.textContent = '✅ Copied!';
            button.classList.add('copied');
            
            setTimeout(() => {
                button.textContent = originalText;
                button.classList.remove('copied');
            }, 2000);
        } catch (err) {
            console.error('Failed to copy:', err);
            alert('Failed to copy content to clipboard');
        }
    }
}

// Create singleton instance
const fileViewer = new FileViewer();

// Create global function for easy access
// Only set if not already defined by dashboard.js
if (!window.showFileViewerModal) {
    window.showFileViewerModal = (filePath) => {
        console.log('[FileViewer] showFileViewerModal called with path:', filePath);
        fileViewer.show(filePath);
    };
}

// Expose the singleton for debugging
window.fileViewerInstance = fileViewer;

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.FileViewer = fileViewer;
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => {
            fileViewer.initialize();
        });
    } else {
        // DOM is already loaded
        fileViewer.initialize();
    }
}

export default fileViewer;