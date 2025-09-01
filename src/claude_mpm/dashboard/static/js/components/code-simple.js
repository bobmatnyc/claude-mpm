// Ultra-simple directory browser - maximum compatibility and debugging
console.log('[code-simple.js] Script loaded at', new Date().toISOString());

// Global function for onclick handlers
function loadDir(path) {
    console.log('[loadDir] Called with path:', path);
    if (window.simpleCodeView) {
        window.simpleCodeView.loadDirectory(path);
    } else {
        console.error('[loadDir] simpleCodeView not initialized');
    }
}

function goUp() {
    console.log('[goUp] Called');
    if (window.simpleCodeView) {
        window.simpleCodeView.goUp();
    } else {
        console.error('[goUp] simpleCodeView not initialized');
    }
}

class SimpleCodeView {
    constructor() {
        console.log('[SimpleCodeView] Constructor called');
        this.currentPath = '/Users/masa/Projects/claude-mpm';
        this.container = null;
        this.apiBase = window.location.origin;
        console.log('[SimpleCodeView] API base:', this.apiBase);
    }

    init(container) {
        console.log('[SimpleCodeView.init] Starting with container:', container);
        
        if (!container) {
            console.error('[SimpleCodeView.init] No container provided!');
            document.body.innerHTML += '<div style="color:red;font-size:20px;">ERROR: No container for SimpleCodeView</div>';
            return;
        }
        
        this.container = container;
        this.render();
        
        // Load initial directory after a short delay to ensure DOM is ready
        setTimeout(() => {
            console.log('[SimpleCodeView.init] Loading initial directory after delay');
            this.loadDirectory(this.currentPath);
        }, 100);
    }

    render() {
        console.log('[SimpleCodeView.render] Rendering UI');
        
        const html = `
            <div class="simple-code-view" style="padding: 20px;">
                <h2>Simple Directory Browser</h2>
                
                <div id="status-bar" style="padding: 10px; background: #e0e0e0; border-radius: 4px; margin-bottom: 10px;">
                    Status: Initializing...
                </div>
                
                <div class="path-bar" style="margin: 10px 0; padding: 10px; background: #f0f0f0; border-radius: 4px;">
                    <strong>Current Path:</strong> 
                    <input type="text" id="path-input" value="${this.currentPath}" style="width: 50%; margin: 0 10px;">
                    <button id="load-btn" onclick="loadDir(document.getElementById('path-input').value)">Load</button>
                    <button id="up-btn" onclick="goUp()">Go Up</button>
                </div>
                
                <div id="error-display" style="display:none; padding: 10px; background: #fee; color: red; border: 1px solid #fcc; border-radius: 4px; margin: 10px 0;">
                </div>
                
                <div id="directory-contents" style="border: 1px solid #ccc; padding: 10px; min-height: 400px; background: white;">
                    <div style="color: #666;">Waiting to load directory...</div>
                </div>
                
                <div id="debug-info" style="margin-top: 10px; padding: 10px; background: #f9f9f9; font-family: monospace; font-size: 12px;">
                    <strong>Debug Info:</strong><br>
                    API Base: ${this.apiBase}<br>
                    Current Path: ${this.currentPath}<br>
                    Status: Waiting for first load...
                </div>
            </div>
        `;
        
        this.container.innerHTML = html;
        console.log('[SimpleCodeView.render] UI rendered');
        
        this.updateStatus('UI Rendered - Ready to load directory', 'blue');
    }

    updateStatus(message, color = 'black') {
        console.log('[SimpleCodeView.updateStatus]', message);
        const statusBar = document.getElementById('status-bar');
        if (statusBar) {
            statusBar.innerHTML = `Status: ${message}`;
            statusBar.style.color = color;
        }
    }

    showError(message) {
        console.error('[SimpleCodeView.showError]', message);
        const errorDiv = document.getElementById('error-display');
        if (errorDiv) {
            errorDiv.style.display = 'block';
            errorDiv.innerHTML = `Error: ${message}`;
        }
        this.updateStatus('Error occurred', 'red');
    }

    hideError() {
        const errorDiv = document.getElementById('error-display');
        if (errorDiv) {
            errorDiv.style.display = 'none';
        }
    }

    async loadDirectory(path) {
        console.log('[SimpleCodeView.loadDirectory] Loading path:', path);
        
        this.currentPath = path;
        this.hideError();
        this.updateStatus(`Loading ${path}...`, 'blue');
        
        // Update path input
        const pathInput = document.getElementById('path-input');
        if (pathInput) {
            pathInput.value = path;
        }
        
        // Update debug info
        const debugDiv = document.getElementById('debug-info');
        const contentsDiv = document.getElementById('directory-contents');
        
        const apiUrl = `${this.apiBase}/api/directory/list?path=${encodeURIComponent(path)}`;
        
        if (debugDiv) {
            debugDiv.innerHTML = `
                <strong>Debug Info:</strong><br>
                API URL: ${apiUrl}<br>
                Timestamp: ${new Date().toISOString()}<br>
                Status: Fetching...
            `;
        }
        
        try {
            console.log('[SimpleCodeView.loadDirectory] Fetching:', apiUrl);
            
            const response = await fetch(apiUrl);
            console.log('[SimpleCodeView.loadDirectory] Response status:', response.status);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            console.log('[SimpleCodeView.loadDirectory] Data received:', data);
            
            // Update debug info with response
            if (debugDiv) {
                debugDiv.innerHTML = `
                    <strong>Debug Info:</strong><br>
                    API URL: ${apiUrl}<br>
                    Response Status: ${response.status}<br>
                    Path Exists: ${data.exists}<br>
                    Is Directory: ${data.is_directory}<br>
                    Item Count: ${data.contents ? data.contents.length : 0}<br>
                    <details>
                        <summary>Raw Response (click to expand)</summary>
                        <pre style="overflow-x: auto;">${JSON.stringify(data, null, 2)}</pre>
                    </details>
                `;
            }
            
            // Display contents
            if (!data.exists) {
                contentsDiv.innerHTML = '<p style="color: red;">❌ Path does not exist</p>';
                this.updateStatus('Path does not exist', 'red');
            } else if (!data.is_directory) {
                contentsDiv.innerHTML = '<p style="color: orange;">⚠️ Path is not a directory</p>';
                this.updateStatus('Not a directory', 'orange');
            } else if (data.error) {
                contentsDiv.innerHTML = `<p style="color: red;">❌ Error: ${data.error}</p>`;
                this.showError(data.error);
            } else if (!data.contents || data.contents.length === 0) {
                contentsDiv.innerHTML = '<p style="color: gray;">📭 Empty directory (no visible contents)</p>';
                this.updateStatus('Empty directory', 'gray');
            } else {
                // Build the list
                let html = `<div style="margin-bottom: 10px; color: #666;">Found ${data.contents.length} items:</div>`;
                html += '<ul style="list-style: none; padding: 0; margin: 0;">';
                
                // Sort: directories first, then files
                const sorted = data.contents.sort((a, b) => {
                    if (a.is_directory !== b.is_directory) {
                        return a.is_directory ? -1 : 1;
                    }
                    return a.name.localeCompare(b.name);
                });
                
                for (const item of sorted) {
                    const icon = item.is_directory ? '📁' : '📄';
                    
                    if (item.is_directory) {
                        // Make directories clickable
                        html += `<li style="padding: 5px 0;">
                            ${icon} <a href="#" onclick="loadDir('${item.path.replace(/'/g, "\\'")}'); return false;" style="color: blue; text-decoration: none; cursor: pointer;">
                                ${item.name}/
                            </a>
                        </li>`;
                    } else {
                        // Files are not clickable
                        html += `<li style="padding: 5px 0;">
                            ${icon} <span style="color: #666;">${item.name}</span>
                        </li>`;
                    }
                }
                
                html += '</ul>';
                contentsDiv.innerHTML = html;
                this.updateStatus(`Loaded ${data.contents.length} items`, 'green');
            }
            
        } catch (error) {
            console.error('[SimpleCodeView.loadDirectory] Error:', error);
            
            const errorMsg = `Failed to load directory: ${error.message}`;
            this.showError(errorMsg);
            
            if (contentsDiv) {
                contentsDiv.innerHTML = `
                    <div style="color: red;">
                        <p>❌ Failed to load directory</p>
                        <p>Error: ${error.message}</p>
                        <p style="font-size: 12px;">Check browser console for details</p>
                    </div>
                `;
            }
            
            if (debugDiv) {
                debugDiv.innerHTML += `<br><span style="color:red;">ERROR: ${error.stack || error.message}</span>`;
            }
        }
    }

    goUp() {
        console.log('[SimpleCodeView.goUp] Current path:', this.currentPath);
        if (this.currentPath === '/' || this.currentPath === '') {
            console.log('[SimpleCodeView.goUp] Already at root');
            this.updateStatus('Already at root directory', 'orange');
            return;
        }
        
        const lastSlash = this.currentPath.lastIndexOf('/');
        const parent = lastSlash > 0 ? this.currentPath.substring(0, lastSlash) : '/';
        console.log('[SimpleCodeView.goUp] Going up to:', parent);
        this.loadDirectory(parent);
    }
}

// Create global instance
console.log('[code-simple.js] Creating global simpleCodeView instance');
window.simpleCodeView = new SimpleCodeView();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
    console.log('[code-simple.js] DOM still loading, waiting for DOMContentLoaded');
    document.addEventListener('DOMContentLoaded', () => {
        console.log('[code-simple.js] DOMContentLoaded fired');
        const container = document.getElementById('code-container');
        if (container) {
            window.simpleCodeView.init(container);
        } else {
            console.error('[code-simple.js] No code-container element found!');
        }
    });
} else {
    console.log('[code-simple.js] DOM already loaded, initializing immediately');
    setTimeout(() => {
        const container = document.getElementById('code-container');
        if (container) {
            window.simpleCodeView.init(container);
        } else {
            console.error('[code-simple.js] No code-container element found!');
        }
    }, 0);
}

console.log('[code-simple.js] Script setup complete');