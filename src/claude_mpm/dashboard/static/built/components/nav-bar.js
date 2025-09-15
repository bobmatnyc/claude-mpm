/**
 * Standardized Navigation Bar Component
 * Provides consistent navigation across all dashboard views
 */
export class NavBar {
    constructor() {
        this.pages = [
            { id: 'activity', label: '🎯 Activity', href: '/static/activity.html' },
            { id: 'events', label: '📡 Events', href: '/static/events.html' },
            { id: 'agents', label: '🤖 Agents', href: '/static/agents.html' },
            { id: 'tools', label: '🔧 Tools', href: '/static/tools.html' },
            { id: 'files', label: '📁 Files', href: '/static/files.html' }
        ];
    }

    /**
     * Get the current page ID based on the URL
     */
    getCurrentPage() {
        const path = window.location.pathname;
        const filename = path.split('/').pop().replace('.html', '');
        return filename || 'activity';
    }

    /**
     * Generate the navigation HTML
     */
    getHTML() {
        const currentPage = this.getCurrentPage();

        const navItems = this.pages.map(page => {
            const isActive = page.id === currentPage;
            return `<a href="${page.href}" class="nav-tab ${isActive ? 'active' : ''}">${page.label}</a>`;
        }).join('\n            ');

        return `
        <div class="nav-tabs">
            ${navItems}
        </div>`;
    }

    /**
     * Generate the CSS styles for the navigation
     */
    getCSS() {
        return `
        .nav-tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            padding: 15px;
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 12px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }

        .nav-tab {
            padding: 10px 20px;
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            color: #94a3b8;
            text-decoration: none;
            transition: all 0.3s;
            font-size: 14px;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .nav-tab:hover {
            background: rgba(255, 255, 255, 0.1);
            color: #e0e0e0;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
        }

        .nav-tab.active {
            background: linear-gradient(135deg, #10b981 0%, #06b6d4 100%);
            color: white;
            border-color: transparent;
            box-shadow: 0 4px 15px rgba(16, 185, 129, 0.3);
        }

        .nav-tab.active:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(16, 185, 129, 0.4);
        }

        /* Responsive design */
        @media (max-width: 768px) {
            .nav-tabs {
                flex-wrap: wrap;
            }

            .nav-tab {
                flex: 1;
                min-width: 100px;
                justify-content: center;
                padding: 8px 12px;
                font-size: 13px;
            }
        }`;
    }

    /**
     * Insert the navigation into a container element
     * @param {string} containerId - ID of the container element
     */
    insertInto(containerId) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = this.getHTML();
        }
    }

    /**
     * Insert navigation styles into the document head
     */
    insertStyles() {
        const styleId = 'nav-bar-styles';
        if (!document.getElementById(styleId)) {
            const style = document.createElement('style');
            style.id = styleId;
            style.textContent = this.getCSS();
            document.head.appendChild(style);
        }
    }

    /**
     * Initialize the navigation bar
     * @param {string} containerId - Optional container ID to insert into
     */
    initialize(containerId = null) {
        this.insertStyles();
        if (containerId) {
            this.insertInto(containerId);
        }
    }
}

// Export for use in dashboard pages
export default NavBar;