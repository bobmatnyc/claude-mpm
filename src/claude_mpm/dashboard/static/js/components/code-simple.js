// Dead simple directory browser - just lists what's there
class SimpleCodeView {
    constructor() {
        this.currentPath = '/Users/masa/Projects/claude-mpm';
        this.container = null;
    }

    async init(container) {
        this.container = container;
        this.render();
        await this.loadDirectory(this.currentPath);
    }

    render() {
        this.container.innerHTML = `
            <div class="simple-code-view" style="padding: 20px;">
                <h2>Simple Directory Browser</h2>
                <div class="path-bar" style="margin: 10px 0; padding: 10px; background: #f0f0f0; border-radius: 4px;">
                    <strong>Current Path:</strong> 
                    <input type="text" id="path-input" value="${this.currentPath}" style="width: 60%; margin: 0 10px;">
                    <button onclick="simpleCodeView.loadDirectory(document.getElementById('path-input').value)">Load</button>
                    <button onclick="simpleCodeView.goUp()">Go Up</button>
                </div>
                <div id="directory-contents" style="border: 1px solid #ccc; padding: 10px; min-height: 400px; background: white;">
                    Loading...
                </div>
                <div id="debug-info" style="margin-top: 10px; padding: 10px; background: #f9f9f9; font-family: monospace; font-size: 12px;">
                    Debug info will appear here
                </div>
            </div>
        `;
    }

    async loadDirectory(path) {
        this.currentPath = path;
        document.getElementById('path-input').value = path;
        
        const debugDiv = document.getElementById('debug-info');
        const contentsDiv = document.getElementById('directory-contents');
        
        debugDiv.innerHTML = `Fetching: /api/directory/list?path=${encodeURIComponent(path)}`;
        
        try {
            const response = await fetch(`/api/directory/list?path=${encodeURIComponent(path)}`);
            const data = await response.json();
            
            // Show debug info
            debugDiv.innerHTML = `
                <strong>API Response:</strong><br>
                Path: ${data.path}<br>
                Exists: ${data.exists}<br>
                Is Directory: ${data.is_directory}<br>
                Items: ${data.contents ? data.contents.length : 0}<br>
                Raw JSON: <pre>${JSON.stringify(data, null, 2)}</pre>
            `;
            
            // Display contents
            if (!data.exists) {
                contentsDiv.innerHTML = '<p style="color: red;">Path does not exist</p>';
            } else if (!data.is_directory) {
                contentsDiv.innerHTML = '<p style="color: orange;">Path is not a directory</p>';
            } else if (data.error) {
                contentsDiv.innerHTML = `<p style="color: red;">Error: ${data.error}</p>`;
            } else if (!data.contents || data.contents.length === 0) {
                contentsDiv.innerHTML = '<p style="color: gray;">Empty directory</p>';
            } else {
                // Build the list
                let html = '<ul style="list-style: none; padding: 0;">';
                
                for (const item of data.contents) {
                    const icon = item.is_directory ? '📁' : '📄';
                    const style = item.is_directory ? 'cursor: pointer; color: blue;' : 'color: #666;';
                    
                    if (item.is_directory) {
                        html += `<li style="padding: 5px;">
                            ${icon} <a href="#" onclick="simpleCodeView.loadDirectory('${item.path.replace(/'/g, "\\'")}')" style="${style}">
                                ${item.name}
                            </a>
                        </li>`;
                    } else {
                        html += `<li style="padding: 5px;">
                            ${icon} <span style="${style}">${item.name}</span>
                        </li>`;
                    }
                }
                
                html += '</ul>';
                contentsDiv.innerHTML = html;
            }
            
        } catch (error) {
            debugDiv.innerHTML = `<strong style="color: red;">Error:</strong> ${error.message}`;
            contentsDiv.innerHTML = '<p style="color: red;">Failed to load directory</p>';
        }
    }

    goUp() {
        const parent = this.currentPath.substring(0, this.currentPath.lastIndexOf('/')) || '/';
        this.loadDirectory(parent);
    }
}

// Global instance
const simpleCodeView = new SimpleCodeView();