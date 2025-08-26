/**
 * Code Viewer Component
 * 
 * Modal window for displaying source code with syntax highlighting.
 * Supports navigation between parent/child nodes and shows code metrics.
 */

class CodeViewer {
    constructor() {
        this.modal = null;
        this.currentNode = null;
        this.socket = null;
        this.initialized = false;
        this.codeCache = new Map();
    }

    /**
     * Initialize the code viewer
     */
    initialize() {
        if (this.initialized) {
            return;
        }

        this.createModal();
        this.setupEventHandlers();
        this.subscribeToEvents();
        
        this.initialized = true;
        console.log('Code viewer initialized');
    }

    /**
     * Create modal DOM structure
     */
    createModal() {
        const modalHtml = `
            <div class="code-viewer-modal" id="code-viewer-modal">
                <div class="code-viewer-content">
                    <div class="code-viewer-header">
                        <div class="code-viewer-title" id="code-viewer-title">
                            Loading...
                        </div>
                        <div class="code-viewer-info">
                            <span id="code-viewer-type">Type: --</span>
                            <span id="code-viewer-lines">Lines: --</span>
                            <span id="code-viewer-complexity">Complexity: --</span>
                        </div>
                        <button class="code-viewer-close" id="code-viewer-close">×</button>
                    </div>
                    <div class="code-viewer-body">
                        <pre class="code-viewer-code line-numbers" id="code-viewer-code">
                            <code class="language-python" id="code-viewer-code-content"></code>
                        </pre>
                    </div>
                    <div class="code-viewer-navigation">
                        <div class="nav-group">
                            <button class="code-nav-button" id="code-nav-parent" disabled>
                                ⬆️ Parent
                            </button>
                            <button class="code-nav-button" id="code-nav-prev" disabled>
                                ⬅️ Previous
                            </button>
                            <button class="code-nav-button" id="code-nav-next" disabled>
                                ➡️ Next
                            </button>
                        </div>
                        <div class="nav-info">
                            <span id="code-nav-position">-- / --</span>
                        </div>
                        <div class="nav-actions">
                            <button class="code-nav-button" id="code-copy">
                                📋 Copy
                            </button>
                            <button class="code-nav-button" id="code-open-file">
                                📂 Open File
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Add modal to body
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        this.modal = document.getElementById('code-viewer-modal');
    }

    /**
     * Setup event handlers
     */
    setupEventHandlers() {
        // Close button
        document.getElementById('code-viewer-close').addEventListener('click', () => {
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

        // Navigation buttons
        document.getElementById('code-nav-parent').addEventListener('click', () => {
            this.navigateToParent();
        });

        document.getElementById('code-nav-prev').addEventListener('click', () => {
            this.navigateToPrevious();
        });

        document.getElementById('code-nav-next').addEventListener('click', () => {
            this.navigateToNext();
        });

        // Action buttons
        document.getElementById('code-copy').addEventListener('click', () => {
            this.copyCode();
        });

        document.getElementById('code-open-file').addEventListener('click', () => {
            this.openInEditor();
        });
    }

    /**
     * Subscribe to Socket.IO events
     */
    subscribeToEvents() {
        if (window.socket) {
            this.socket = window.socket;
            
            // Listen for code content responses
            this.socket.on('code:content:response', (data) => {
                this.handleCodeContent(data);
            });
        }
    }

    /**
     * Show the code viewer with node data
     */
    show(nodeData) {
        if (!this.initialized) {
            this.initialize();
        }

        this.currentNode = nodeData;
        this.modal.classList.add('show');
        
        // Update header
        this.updateHeader(nodeData);
        
        // Load code content
        this.loadCode(nodeData);
        
        // Update navigation
        this.updateNavigation(nodeData);
    }

    /**
     * Hide the code viewer
     */
    hide() {
        this.modal.classList.remove('show');
        this.currentNode = null;
    }

    /**
     * Update modal header
     */
    updateHeader(nodeData) {
        // Update title
        const title = document.getElementById('code-viewer-title');
        title.textContent = `${nodeData.name} (${nodeData.path || 'Unknown'})`;
        
        // Update info
        document.getElementById('code-viewer-type').textContent = `Type: ${nodeData.type}`;
        document.getElementById('code-viewer-lines').textContent = `Lines: ${nodeData.lines || '--'}`;
        document.getElementById('code-viewer-complexity').textContent = `Complexity: ${nodeData.complexity || '--'}`;
    }

    /**
     * Load code content
     */
    loadCode(nodeData) {
        const codeContent = document.getElementById('code-viewer-code-content');
        
        // Check cache first
        const cacheKey = `${nodeData.path}:${nodeData.line}`;
        if (this.codeCache.has(cacheKey)) {
            this.displayCode(this.codeCache.get(cacheKey));
            return;
        }
        
        // Show loading state
        codeContent.textContent = 'Loading code...';
        
        // Request code from server
        if (this.socket) {
            this.socket.emit('code:content:request', {
                path: nodeData.path,
                line: nodeData.line,
                type: nodeData.type,
                name: nodeData.name
            });
        } else {
            // Fallback: show mock code for demo
            this.displayMockCode(nodeData);
        }
    }

    /**
     * Handle code content response
     */
    handleCodeContent(data) {
        if (!data.success) {
            this.displayError(data.error || 'Failed to load code');
            return;
        }
        
        // Cache the content
        const cacheKey = `${data.path}:${data.line}`;
        this.codeCache.set(cacheKey, data.content);
        
        // Display the code
        this.displayCode(data.content);
    }

    /**
     * Display code with syntax highlighting
     */
    displayCode(code) {
        const codeContent = document.getElementById('code-viewer-code-content');
        const codeElement = document.getElementById('code-viewer-code');
        
        // Set the code content
        codeContent.textContent = code;
        
        // Update language class based on file extension
        const language = this.detectLanguage(this.currentNode.path);
        codeContent.className = `language-${language}`;
        
        // Apply Prism syntax highlighting
        if (window.Prism) {
            Prism.highlightElement(codeContent);
            
            // Add line numbers if plugin is available
            if (Prism.plugins && Prism.plugins.lineNumbers) {
                Prism.plugins.lineNumbers.resize(codeElement);
            }
        }
    }

    /**
     * Display mock code for demo purposes
     */
    displayMockCode(nodeData) {
        let mockCode = '';
        
        switch (nodeData.type) {
            case 'class':
                mockCode = `class ${nodeData.name}:
    """
    ${nodeData.docstring || 'A sample class implementation.'}
    """
    
    def __init__(self):
        """Initialize the ${nodeData.name} class."""
        self._data = {}
        self._initialized = False
    
    def process(self, input_data):
        """Process the input data."""
        if not self._initialized:
            self._initialize()
        return self._transform(input_data)
    
    def _initialize(self):
        """Initialize internal state."""
        self._initialized = True
    
    def _transform(self, data):
        """Transform the data."""
        return data`;
                break;
                
            case 'function':
                mockCode = `def ${nodeData.name}(${nodeData.params ? nodeData.params.join(', ') : ''}):
    """
    ${nodeData.docstring || 'A sample function implementation.'}
    
    Args:
        ${nodeData.params ? nodeData.params.map(p => `${p}: Description of ${p}`).join('\n        ') : 'None'}
    
    Returns:
        ${nodeData.returns || 'None'}: Return value description
    """
    # Implementation here
    result = None
    
    # Process logic
    for item in range(10):
        result = process_item(item)
    
    return result`;
                break;
                
            case 'method':
                mockCode = `    def ${nodeData.name}(self${nodeData.params ? ', ' + nodeData.params.join(', ') : ''}):
        """
        ${nodeData.docstring || 'A sample method implementation.'}
        """
        # Method implementation
        self._validate()
        result = self._process()
        return result`;
                break;
                
            default:
                mockCode = `# ${nodeData.name}
# Type: ${nodeData.type}
# Path: ${nodeData.path || 'Unknown'}
# Line: ${nodeData.line || 'Unknown'}

# Code content would appear here
# This is a placeholder for demonstration purposes`;
        }
        
        this.displayCode(mockCode);
    }

    /**
     * Display error message
     */
    displayError(message) {
        const codeContent = document.getElementById('code-viewer-code-content');
        codeContent.textContent = `# Error loading code\n# ${message}`;
        codeContent.className = 'language-python';
    }

    /**
     * Detect language from file path
     */
    detectLanguage(path) {
        if (!path) return 'python';
        
        const ext = path.split('.').pop().toLowerCase();
        const languageMap = {
            'py': 'python',
            'js': 'javascript',
            'ts': 'typescript',
            'jsx': 'jsx',
            'tsx': 'tsx',
            'css': 'css',
            'html': 'html',
            'json': 'json',
            'yaml': 'yaml',
            'yml': 'yaml',
            'md': 'markdown',
            'sh': 'bash',
            'bash': 'bash',
            'sql': 'sql',
            'go': 'go',
            'rs': 'rust',
            'cpp': 'cpp',
            'c': 'c',
            'h': 'c',
            'hpp': 'cpp',
            'java': 'java',
            'rb': 'ruby',
            'php': 'php'
        };
        
        return languageMap[ext] || 'plaintext';
    }

    /**
     * Update navigation buttons
     */
    updateNavigation(nodeData) {
        // For now, disable navigation buttons
        // In a real implementation, these would navigate through the AST
        document.getElementById('code-nav-parent').disabled = true;
        document.getElementById('code-nav-prev').disabled = true;
        document.getElementById('code-nav-next').disabled = true;
        document.getElementById('code-nav-position').textContent = '1 / 1';
    }

    /**
     * Navigate to parent node
     */
    navigateToParent() {
        console.log('Navigate to parent node');
        // Implementation would load parent node's code
    }

    /**
     * Navigate to previous sibling
     */
    navigateToPrevious() {
        console.log('Navigate to previous sibling');
        // Implementation would load previous sibling's code
    }

    /**
     * Navigate to next sibling
     */
    navigateToNext() {
        console.log('Navigate to next sibling');
        // Implementation would load next sibling's code
    }

    /**
     * Copy code to clipboard
     */
    async copyCode() {
        const codeContent = document.getElementById('code-viewer-code-content');
        const code = codeContent.textContent;
        
        try {
            await navigator.clipboard.writeText(code);
            
            // Show feedback
            const button = document.getElementById('code-copy');
            const originalText = button.textContent;
            button.textContent = '✅ Copied!';
            setTimeout(() => {
                button.textContent = originalText;
            }, 2000);
        } catch (err) {
            console.error('Failed to copy code:', err);
            alert('Failed to copy code to clipboard');
        }
    }

    /**
     * Open file in editor
     */
    openInEditor() {
        if (!this.currentNode || !this.currentNode.path) {
            alert('File path not available');
            return;
        }
        
        // Emit event to open file
        if (this.socket) {
            this.socket.emit('file:open', {
                path: this.currentNode.path,
                line: this.currentNode.line
            });
        }
        
        console.log('Opening file in editor:', this.currentNode.path);
    }
}

// Create singleton instance
const codeViewer = new CodeViewer();

// Export for use in other modules
if (typeof window !== 'undefined') {
    window.CodeViewer = codeViewer;
    
    // Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', () => {
        codeViewer.initialize();
    });
}

export default codeViewer;