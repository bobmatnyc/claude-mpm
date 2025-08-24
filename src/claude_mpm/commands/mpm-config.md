# View or modify claude-mpm configuration

Manage Claude MPM configuration settings.

Usage: /mpm-config [key] [value]

Examples:
- /mpm-config - Show all configuration
- /mpm-config list - List all configuration keys
- /mpm-config set logging debug - Set logging level to debug
- /mpm-config get websocket-port - Get WebSocket port setting

Configuration categories:
- logging: Logging levels and output
- websocket: WebSocket server settings
- hooks: Hook service configuration
- memory: Memory system settings
- agents: Agent deployment options