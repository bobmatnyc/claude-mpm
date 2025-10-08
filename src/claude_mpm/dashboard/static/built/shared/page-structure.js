/**
 * Shared Page Structure Component
 * Provides consistent header and navigation across all dashboard pages
 */

export class PageStructure {
    constructor() {
        this.pages = [
            { id: 'main', label: '📈 Main Dashboard', href: '/static/' },
            { id: 'events', label: '📊 Events', href: '/static/events.html' },
            { id: 'agents', label: '🤖 Agents', href: '/static/agents.html' },
            { id: 'tools', label: '🔧 Tools', href: '/static/tools.html' },
            { id: 'files', label: '📁 Files', href: '/static/files.html' },
            { id: 'activity', label: '🌳 Activity', href: '/static/activity.html' }
        ];
    }

    getCurrentPage() {
        const path = window.location.pathname;

        if (path.includes('events.html')) return 'events';
        if (path.includes('agents.html')) return 'agents';
        if (path.includes('tools.html')) return 'tools';
        if (path.includes('files.html')) return 'files';
        if (path.includes('activity.html')) return 'activity';
        if (path.includes('index.html') || path.endsWith('/static/') || path.endsWith('/')) return 'main';

        return 'main';
    }

    generateNavigation() {
        const currentPage = this.getCurrentPage();

        const navItems = this.pages.map(page => {
            const isActive = page.id === currentPage;
            return `
                <a href="${page.href}" class="nav-item ${isActive ? 'active' : ''}" data-page="${page.id}">
                    ${page.label}
                </a>
            `;
        }).join('');

        return `
            <div class="page-header">
                <div class="header-brand">
                    <h1>🚀 Claude MPM Monitor</h1>
                    <p>Real-time monitoring for agents, tools, files, and events</p>
                </div>
                <div class="header-navigation">
                    ${navItems}
                </div>
                <div class="header-status">
                    <div id="page-connection-status" class="connection-status">
                        <span class="status-indicator">●</span>
                        <span class="status-text">Checking...</span>
                    </div>
                </div>
            </div>
        `;
    }

    generateCSS() {
        return `
            <style id="page-structure-styles">
                .page-header {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 2rem;
                    text-align: center;
                    margin-bottom: 2rem;
                    border-radius: 12px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                }

                .header-brand h1 {
                    margin: 0 0 0.5rem 0;
                    font-size: 2.5rem;
                    font-weight: 700;
                    background: linear-gradient(135deg, #fff 0%, #e0e0e0 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    background-clip: text;
                }

                .header-brand p {
                    margin: 0 0 1.5rem 0;
                    opacity: 0.9;
                    font-size: 1.1rem;
                }

                .header-navigation {
                    display: flex;
                    justify-content: center;
                    gap: 1rem;
                    flex-wrap: wrap;
                    margin-bottom: 1.5rem;
                }

                .nav-item {
                    padding: 0.75rem 1.5rem;
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(10px);
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    border-radius: 25px;
                    color: white;
                    text-decoration: none;
                    font-size: 0.9rem;
                    font-weight: 500;
                    transition: all 0.3s ease;
                    display: inline-block;
                }

                .nav-item:hover {
                    background: rgba(255, 255, 255, 0.2);
                    transform: translateY(-2px);
                    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
                }

                .nav-item.active {
                    background: rgba(255, 255, 255, 0.25);
                    border-color: rgba(255, 255, 255, 0.4);
                    font-weight: 600;
                    box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
                }

                .header-status {
                    display: flex;
                    justify-content: center;
                }

                .connection-status {
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    padding: 0.5rem 1rem;
                    background: rgba(255, 255, 255, 0.1);
                    border-radius: 20px;
                    border: 1px solid rgba(255, 255, 255, 0.2);
                    font-size: 0.9rem;
                }

                .status-indicator {
                    font-size: 1.2rem;
                }

                .connection-status.connected .status-indicator {
                    color: #22c55e;
                    text-shadow: 0 0 10px #22c55e;
                }

                .connection-status.connecting .status-indicator {
                    color: #fbbf24;
                    text-shadow: 0 0 10px #fbbf24;
                    animation: pulse 1s infinite;
                }

                .connection-status.disconnected .status-indicator {
                    color: #ef4444;
                    text-shadow: 0 0 10px #ef4444;
                }

                @keyframes pulse {
                    0%, 100% { opacity: 1; }
                    50% { opacity: 0.5; }
                }

                @media (max-width: 768px) {
                    .page-header {
                        padding: 1.5rem;
                    }

                    .header-brand h1 {
                        font-size: 2rem;
                    }

                    .header-navigation {
                        gap: 0.5rem;
                    }

                    .nav-item {
                        padding: 0.5rem 1rem;
                        font-size: 0.8rem;
                    }
                }
            </style>
        `;
    }

    insertIntoPage(containerId = 'page-header') {
        // Insert CSS
        const existingStyles = document.getElementById('page-structure-styles');
        if (!existingStyles) {
            document.head.insertAdjacentHTML('beforeend', this.generateCSS());
        }

        // Insert HTML
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = this.generateNavigation();
            this.setupEventListeners();
        } else {
            // If no container found, create one at the top of the body
            document.body.insertAdjacentHTML('afterbegin', `
                <div id="${containerId}">
                    ${this.generateNavigation()}
                </div>
            `);
            this.setupEventListeners();
        }
    }

    setupEventListeners() {
        // Listen for connection status changes
        document.addEventListener('socketConnectionStatus', (e) => {
            this.updateConnectionStatus(e.detail.status, e.detail.type);
        });
    }

    updateConnectionStatus(status, type) {
        const statusElement = document.getElementById('page-connection-status');
        if (statusElement) {
            const indicator = statusElement.querySelector('.status-indicator');
            const text = statusElement.querySelector('.status-text');

            if (text) text.textContent = status;

            statusElement.className = `connection-status ${type}`;
        }
    }

    initialize() {
        // Auto-initialize when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                this.insertIntoPage();
            });
        } else {
            this.insertIntoPage();
        }
    }
}

// Auto-initialize
const pageStructure = new PageStructure();
pageStructure.initialize();

// Export for manual use
export default PageStructure;
window.PageStructure = PageStructure;