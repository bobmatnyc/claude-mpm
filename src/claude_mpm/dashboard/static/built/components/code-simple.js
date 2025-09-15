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

function analyzeFileFromPath(filePath) {
    console.log('[analyzeFileFromPath] Called with path:', filePath);
    if (window.simpleCodeView) {
        window.simpleCodeView.analyzeFileFromPath(filePath);
    } else {
        console.error('[analyzeFileFromPath] simpleCodeView not initialized');
    }
}

class SimpleCodeView {
    constructor() {
        console.log('[SimpleCodeView] Constructor called');
        // Try to get the current working directory from various sources
        this.currentPath = this.getInitialPath();
        this.container = null;
        this.apiBase = window.location.origin;
        console.log('[SimpleCodeView] API base:', this.apiBase);
        
        // Tree view properties
        this.currentView = 'directory';
        this.socket = null;
        this.svg = null;
        this.treeGroup = null;
        this.treeLayout = null;
        this.treeData = null;
        this.width = 800;
        this.height = 600;
        this.margin = {top: 20, right: 20, bottom: 20, left: 120};
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
                <h2>Simple Code Browser</h2>
                
                <div class="view-toggle" style="margin: 10px 0; padding: 10px; background: #f0f0f0; border-radius: 4px;">
                    <button id="dir-view-btn" onclick="window.simpleCodeView.setView('directory')" class="active" 
                            style="margin-right: 10px; padding: 8px 16px; border: 1px solid #ccc; background: #007cba; color: white; border-radius: 4px; cursor: pointer;">
                        📁 Directory View
                    </button>
                    <button id="tree-view-btn" onclick="window.simpleCodeView.setView('tree')" 
                            style="padding: 8px 16px; border: 1px solid #ccc; background: #f9f9f9; color: #333; border-radius: 4px; cursor: pointer;">
                        🌳 Tree View
                    </button>
                </div>
                
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
                
                <div id="tree-view-container" style="display: none;">
                    <div class="file-selector" style="margin: 10px 0; padding: 10px; background: #f9f9f9; border-radius: 4px;">
                        <input type="text" id="file-path-input" placeholder="Enter file path to analyze (e.g., ./src/claude_mpm/core/framework_loader.py)" 
                               style="width: 70%; padding: 8px; margin-right: 10px; border: 1px solid #ccc; border-radius: 4px;">
                        <button onclick="window.simpleCodeView.analyzeFile()" 
                                style="padding: 8px 16px; border: 1px solid #ccc; background: #28a745; color: white; border-radius: 4px; cursor: pointer;">
                            Analyze File
                        </button>
                    </div>
                    <div id="tree-visualization" style="border: 1px solid #ccc; min-height: 500px; background: white; overflow: auto; position: relative;">
                        <div style="padding: 20px; text-align: center; color: #666;">Enter a file path above and click "Analyze File" to view AST tree</div>
                    </div>
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
            
            // Update debug info with response and filtering status
            if (debugDiv) {
                let debugContent = `
                    <strong>Debug Info:</strong><br>
                    API URL: ${apiUrl}<br>
                    Response Status: ${response.status}<br>
                    Path Exists: ${data.exists}<br>
                    Is Directory: ${data.is_directory}<br>
                    Item Count: ${data.contents ? data.contents.length : 0}<br>
                `;
                
                // Add filtering information
                if (data.filtered) {
                    debugContent += `<strong>Filtering:</strong> ${data.filter_info || 'Filtered view'}<br>`;
                    if (data.summary) {
                        debugContent += `<strong>Items:</strong> ${data.summary.directories} directories, ${data.summary.code_files} code files<br>`;
                    }
                }
                
                debugContent += `
                    <details>
                        <summary>Raw Response (click to expand)</summary>
                        <pre style="overflow-x: auto;">${JSON.stringify(data, null, 2)}</pre>
                    </details>
                `;
                
                debugDiv.innerHTML = debugContent;
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
                contentsDiv.innerHTML = '<p style="color: gray;">📭 No code files or subdirectories found (hidden files/folders not shown)</p>';
                this.updateStatus('No code content found', 'gray');
            } else {
                // Build the list with filtering indicator
                let headerText = `Found ${data.contents.length} items`;
                if (data.filtered && data.summary) {
                    headerText += ` (${data.summary.directories} directories, ${data.summary.code_files} code files)`;
                }
                headerText += ':';
                
                let html = `<div style="margin-bottom: 10px; color: #666;">${headerText}</div>`;
                
                // Add filtering notice if applicable
                if (data.filtered) {
                    html += `<div style="margin-bottom: 10px; padding: 8px; background: #e8f4fd; border-left: 3px solid #2196f3; color: #1565c0; font-size: 13px;">
                        🔍 Filtered view: ${data.filter_info || 'Showing only code-related files and directories'}
                    </div>`;
                }
                
                html += '<ul style="list-style: none; padding: 0; margin: 0;">';
                
                // Sort: directories first, then files
                const sorted = data.contents.sort((a, b) => {
                    if (a.is_directory !== b.is_directory) {
                        return a.is_directory ? -1 : 1;
                    }
                    return a.name.localeCompare(b.name);
                });
                
                for (const item of sorted) {
                    if (item.is_directory) {
                        // Make directories clickable
                        html += `<li style="padding: 5px 0;">
                            📁 <a href="#" onclick="loadDir('${item.path.replace(/'/g, "\\'")}'); return false;" style="color: blue; text-decoration: none; cursor: pointer;">
                                ${item.name}/
                            </a>
                        </li>`;
                    } else {
                        // Check if it's a code file and make it clickable
                        const isCodeFile = this.isCodeFile(item.name);
                        const fileIcon = this.getFileIcon(item.name);
                        
                        if (isCodeFile) {
                            // Code files - clickable to show AST
                            html += `<li style="padding: 5px 0;">
                                ${fileIcon} <a href="#" onclick="analyzeFileFromPath('${item.path.replace(/'/g, "\\'")}'); return false;" style="color: #0066cc; text-decoration: none; cursor: pointer; font-weight: 500;" title="Click to view AST">
                                    ${item.name}
                                </a>
                            </li>`;
                        } else {
                            // Non-code files - not clickable
                            html += `<li style="padding: 5px 0;">
                                📄 <span style="color: #666;">${item.name}</span>
                            </li>`;
                        }
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

    // Tree view methods
    setView(view) {
        console.log('[SimpleCodeView.setView] Switching to view:', view);
        this.currentView = view;
        
        const dirContents = document.getElementById('directory-contents');
        const treeContainer = document.getElementById('tree-view-container');
        const dirBtn = document.getElementById('dir-view-btn');
        const treeBtn = document.getElementById('tree-view-btn');
        
        if (view === 'tree') {
            dirContents.style.display = 'none';
            treeContainer.style.display = 'block';
            
            // Update button styles
            dirBtn.style.background = '#f9f9f9';
            dirBtn.style.color = '#333';
            dirBtn.classList.remove('active');
            
            treeBtn.style.background = '#007cba';
            treeBtn.style.color = 'white';
            treeBtn.classList.add('active');
            
            this.initializeTreeView();
        } else {
            dirContents.style.display = 'block';
            treeContainer.style.display = 'none';
            
            // Update button styles
            treeBtn.style.background = '#f9f9f9';
            treeBtn.style.color = '#333';
            treeBtn.classList.remove('active');
            
            dirBtn.style.background = '#007cba';
            dirBtn.style.color = 'white';
            dirBtn.classList.add('active');
        }
    }

    initializeTreeView() {
        console.log('[SimpleCodeView.initializeTreeView] Initializing tree view');
        
        if (!window.d3) {
            this.updateStatus('D3.js not loaded - cannot initialize tree view', 'red');
            return;
        }
        
        this.initializeSocket();
    }

    initializeSocket() {
        console.log('[SimpleCodeView.initializeSocket] Initializing Socket.IO connection');
        
        if (!window.io) {
            this.updateStatus('Socket.IO not loaded - using fallback mode', 'orange');
            return;
        }
        
        try {
            this.socket = io('/');
            
            this.socket.on('connect', () => {
                console.log('[SimpleCodeView] Socket connected');
                this.updateStatus('Connected to analysis server', 'green');
            });
            
            this.socket.on('disconnect', () => {
                console.log('[SimpleCodeView] Socket disconnected');
                this.updateStatus('Disconnected from analysis server', 'orange');
            });
            
            this.socket.on('analysis_progress', (data) => {
                console.log('[SimpleCodeView] Analysis progress:', data);
                this.updateStatus(`Analysis: ${data.message}`, 'blue');
            });
            
            this.socket.on('analysis_complete', (data) => {
                console.log('[SimpleCodeView] Analysis complete:', data);
                this.updateStatus('Analysis complete - rendering tree', 'green');
                this.renderTree(data);
            });
            
            this.socket.on('analysis_error', (error) => {
                console.error('[SimpleCodeView] Analysis error:', error);
                this.showError(`Analysis failed: ${error.message || error}`);
            });
            
        } catch (error) {
            console.error('[SimpleCodeView] Failed to initialize socket:', error);
            this.updateStatus('Socket connection failed - using fallback mode', 'orange');
        }
    }

    async analyzeFile() {
        console.log('[SimpleCodeView.analyzeFile] Starting file analysis');
        
        const fileInput = document.getElementById('file-path-input');
        const filePath = fileInput.value.trim();
        
        if (!filePath) {
            this.showError('Please enter a file path');
            return;
        }
        
        this.hideError();
        this.updateStatus(`Analyzing file: ${filePath}`, 'blue');
        
        // Clear previous tree
        const treeViz = document.getElementById('tree-visualization');
        if (treeViz) {
            treeViz.innerHTML = '<div style="padding: 20px; text-align: center; color: #666;">Analyzing file...</div>';
        }
        
        try {
            if (this.socket && this.socket.connected) {
                // Use Socket.IO for real-time analysis
                this.socket.emit('analyze_file', {
                    path: filePath,
                    working_directory: this.currentPath
                });
            } else {
                // Fallback to HTTP API (we'll create a simple endpoint)
                await this.analyzeFileHTTP(filePath);
            }
        } catch (error) {
            console.error('[SimpleCodeView.analyzeFile] Error:', error);
            this.showError(`Failed to analyze file: ${error.message}`);
        }
    }

    async analyzeFileHTTP(filePath) {
        console.log('[SimpleCodeView.analyzeFileHTTP] Using HTTP fallback for:', filePath);
        
        try {
            // Create a simple mock analysis for demonstration
            // In a real implementation, this would call a proper analysis endpoint
            setTimeout(() => {
                const mockData = this.createMockTreeData(filePath);
                this.renderTree(mockData);
            }, 1000);
            
        } catch (error) {
            throw new Error(`HTTP analysis failed: ${error.message}`);
        }
    }

    createMockTreeData(filePath) {
        // Create mock AST data for demonstration
        const fileName = filePath.split('/').pop() || 'file';
        const ext = fileName.split('.').pop()?.toLowerCase();
        
        let mockData = {
            name: fileName,
            type: 'module',
            children: []
        };
        
        if (ext === 'py') {
            mockData.children = [
                {
                    name: 'imports',
                    type: 'imports',
                    children: [
                        { name: 'import os', type: 'import' },
                        { name: 'from pathlib import Path', type: 'import' }
                    ]
                },
                {
                    name: 'MyClass',
                    type: 'class',
                    children: [
                        { name: '__init__', type: 'method' },
                        { name: 'process_data', type: 'method' },
                        { name: 'save_results', type: 'method' }
                    ]
                },
                {
                    name: 'helper_function',
                    type: 'function',
                    children: []
                }
            ];
        } else if (ext === 'js' || ext === 'ts') {
            mockData.children = [
                {
                    name: 'imports',
                    type: 'imports',
                    children: [
                        { name: "import React from 'react'", type: 'import' },
                        { name: "import { useState } from 'react'", type: 'import' }
                    ]
                },
                {
                    name: 'MyComponent',
                    type: 'function',
                    children: [
                        { name: 'useState', type: 'hook' },
                        { name: 'useEffect', type: 'hook' },
                        { name: 'handleClick', type: 'function' }
                    ]
                }
            ];
        } else {
            mockData.children = [
                { name: 'Content Section 1', type: 'section' },
                { name: 'Content Section 2', type: 'section' },
                { name: 'Content Section 3', type: 'section' }
            ];
        }
        
        return mockData;
    }

    renderTree(data) {
        console.log('[SimpleCodeView.renderTree] Rendering tree with data:', data);
        
        if (!data || !window.d3) {
            this.showError('Cannot render tree: missing data or D3.js');
            return;
        }
        
        this.treeData = data;
        
        // Clear previous visualization
        const container = document.getElementById('tree-visualization');
        if (!container) {
            this.showError('Tree visualization container not found');
            return;
        }
        
        container.innerHTML = '';
        
        // Create SVG
        const margin = this.margin;
        const width = this.width - margin.left - margin.right;
        const height = this.height - margin.top - margin.bottom;
        
        this.svg = d3.select('#tree-visualization')
            .append('svg')
            .attr('width', this.width)
            .attr('height', this.height);
        
        // Add zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on('zoom', (event) => {
                this.treeGroup.attr('transform', event.transform);
            });
        
        this.svg.call(zoom);
        
        // Create main group
        this.treeGroup = this.svg.append('g')
            .attr('transform', `translate(${margin.left},${margin.top})`);
        
        // Create tree layout
        this.treeLayout = d3.tree()
            .size([height, width]);
        
        // Convert data to hierarchy
        const hierarchy = d3.hierarchy(data);
        
        // Generate tree layout
        const treeData = this.treeLayout(hierarchy);
        
        // Add links
        const links = this.treeGroup.selectAll('.link')
            .data(treeData.links())
            .enter()
            .append('path')
            .attr('class', 'link')
            .attr('d', d3.linkHorizontal()
                .x(d => d.y)
                .y(d => d.x)
            )
            .style('fill', 'none')
            .style('stroke', '#ccc')
            .style('stroke-width', '2px');
        
        // Add nodes
        const nodes = this.treeGroup.selectAll('.node')
            .data(treeData.descendants())
            .enter()
            .append('g')
            .attr('class', 'tree-node')
            .attr('transform', d => `translate(${d.y},${d.x})`);
        
        // Add circles for nodes
        nodes.append('circle')
            .attr('r', 6)
            .style('fill', d => this.getNodeColor(d.data.type))
            .style('stroke', '#333')
            .style('stroke-width', '2px');
        
        // Add labels
        nodes.append('text')
            .attr('dy', '.35em')
            .attr('x', d => d.children ? -13 : 13)
            .style('text-anchor', d => d.children ? 'end' : 'start')
            .style('font-size', '12px')
            .style('font-family', 'Arial, sans-serif')
            .text(d => d.data.name);
        
        // Add tooltips
        nodes.append('title')
            .text(d => `${d.data.type}: ${d.data.name}`);
        
        // Add legend
        this.addLegend(container);
        
        this.updateStatus('Tree visualization rendered successfully', 'green');
    }

    getNodeColor(type) {
        const colors = {
            'module': '#1f77b4',
            'class': '#ff7f0e',
            'function': '#2ca02c',
            'method': '#d62728',
            'import': '#9467bd',
            'imports': '#8c564b',
            'section': '#e377c2',
            'hook': '#7f7f7f'
        };
        return colors[type] || '#bcbd22';
    }

    // Check if file is a code file
    isCodeFile(filename) {
        const codeExtensions = [
            '.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.c', '.h',
            '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala',
            '.r', '.m', '.mm', '.sh', '.bash', '.zsh', '.sql', '.html',
            '.css', '.scss', '.sass', '.less', '.xml', '.json', '.yaml', '.yml',
            '.md', '.rst', '.txt', '.log', '.conf', '.ini', '.toml'
        ];
        const ext = filename.toLowerCase().substring(filename.lastIndexOf('.'));
        return codeExtensions.includes(ext);
    }

    // Get appropriate icon for file type
    getFileIcon(filename) {
        const ext = filename.toLowerCase().substring(filename.lastIndexOf('.'));
        const iconMap = {
            '.py': '🐍',
            '.js': '📜', 
            '.jsx': '⚛️',
            '.ts': '📘',
            '.tsx': '⚛️',
            '.json': '📋',
            '.html': '🌐',
            '.css': '🎨',
            '.md': '📝',
            '.yml': '⚙️',
            '.yaml': '⚙️',
            '.sh': '🔧',
            '.go': '🐹',
            '.rs': '🦀',
            '.java': '☕',
            '.rb': '💎',
            '.php': '🐘',
            '.cpp': '⚙️',
            '.c': '⚙️',
            '.h': '📄',
            '.cs': '💜',
            '.swift': '🦉',
            '.kt': '🚀',
            '.scala': '📈',
            '.r': '📊',
            '.sql': '🗃️',
            '.scss': '🎨',
            '.sass': '🎨',
            '.less': '🎨',
            '.xml': '📑',
            '.bash': '🔧',
            '.zsh': '🔧',
            '.md': '📝',
            '.rst': '📝',
            '.txt': '📄',
            '.log': '📋',
            '.conf': '⚙️',
            '.ini': '⚙️',
            '.toml': '⚙️'
        };
        return iconMap[ext] || '💻';
    }

    // New method to analyze file from directory click
    analyzeFileFromPath(filePath) {
        console.log('[SimpleCodeView.analyzeFileFromPath] Analyzing file:', filePath);
        
        // Switch to tree view
        this.setView('tree');
        
        // Set the file path in the input
        const fileInput = document.getElementById('file-path-input');
        if (fileInput) {
            fileInput.value = filePath;
        }
        
        // Trigger analysis
        this.analyzeFile();
    }

    addLegend(container) {
        // Remove existing legend
        const existingLegend = container.querySelector('.tree-legend');
        if (existingLegend) {
            existingLegend.remove();
        }
        
        const legend = document.createElement('div');
        legend.className = 'tree-legend';
        
        const legendTypes = [
            { type: 'module', label: 'Module/File' },
            { type: 'class', label: 'Class' },
            { type: 'function', label: 'Function' },
            { type: 'method', label: 'Method' },
            { type: 'imports', label: 'Imports' },
            { type: 'import', label: 'Import' },
            { type: 'section', label: 'Section' },
            { type: 'hook', label: 'Hook/Other' }
        ];
        
        legend.innerHTML = `
            <strong>Legend</strong><br>
            ${legendTypes.map(item => `
                <div class="tree-legend-item">
                    <div class="tree-legend-color" style="background-color: ${this.getNodeColor(item.type)};"></div>
                    ${item.label}
                </div>
            `).join('')}
            <hr style="margin: 8px 0;">
            <div style="font-size: 11px; color: #666;">
                Zoom: Mouse wheel<br>
                Pan: Click and drag
            </div>
        `;
        
        container.appendChild(legend);
    }
    
    /**
     * Get initial path from various sources
     * @returns {string} Initial path to use
     */
    getInitialPath() {
        // Try to get from working directory manager
        if (window.dashboard && window.dashboard.workingDirectoryManager) {
            const dir = window.dashboard.workingDirectoryManager.getCurrentWorkingDir();
            if (dir) return dir;
        }
        
        // Try to get from working directory element
        const workingDirPath = document.getElementById('working-dir-path');
        if (workingDirPath && workingDirPath.textContent && workingDirPath.textContent !== 'Loading...') {
            return workingDirPath.textContent.trim();
        }
        
        // Try to get from footer
        const footerDir = document.getElementById('footer-working-dir');
        if (footerDir && footerDir.textContent && footerDir.textContent !== 'Unknown') {
            return footerDir.textContent.trim();
        }
        
        // Try to get from recent events
        if (window.socketClient && window.socketClient.events) {
            const eventsWithDir = window.socketClient.events
                .filter(e => e.data && (e.data.working_directory || e.data.cwd || e.data.working_dir))
                .reverse();
            
            if (eventsWithDir.length > 0) {
                const recentEvent = eventsWithDir[0];
                const dir = recentEvent.data.working_directory || 
                           recentEvent.data.cwd || 
                           recentEvent.data.working_dir;
                if (dir) return dir;
            }
        }
        
        // Default fallback
        return '/';
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