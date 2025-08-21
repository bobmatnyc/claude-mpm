# Claude MPM (npm wrapper)

This is the npm wrapper for the **Claude Multi-Agent Project Manager (claude-mpm)**, a Python framework that extends Claude Desktop with multi-agent orchestration capabilities.

## Requirements

- **Node.js** 14.0.0 or later
- **Python** 3.8 or later
- **macOS** or **Linux** (Windows support via WSL)

## Installation

```bash
npm install -g @bobmatnyc/claude-mpm
```

## Usage

Once installed, you can use the `claude-mpm` command directly:

```bash
# Initialize claude-mpm
claude-mpm config init

# Deploy agents
claude-mpm agents deploy

# Run with an agent
claude-mpm run --agent engineer

# View version info
claude-mpm info
```

## What this package does

This npm package is a wrapper that:

1. **Detects Python 3.8+** on your system
2. **Automatically installs** the `claude-mpm` Python package 
3. **Launches the Python CLI** with your arguments

## Python Package

The actual claude-mpm functionality is provided by the Python package. If you prefer to install directly with Python:

```bash
pip install claude-mpm
```

## Features

- **Multi-Agent Orchestration**: Coordinate specialized AI agents for different tasks
- **Ticket Management**: Integrated ticketing system with aitrackdown
- **Memory System**: Persistent agent memory and context management
- **WebSocket Dashboard**: Real-time monitoring of agent activities
- **MCP Gateway**: Model Context Protocol server integration
- **Claude Desktop Integration**: Seamless integration with Anthropic's Claude Desktop

## Documentation

For detailed documentation, visit the [main repository](https://github.com/bobmatnyc/claude-mpm).

## License

MIT - see [LICENSE](LICENSE) file.

## Support

- **Issues**: [GitHub Issues](https://github.com/bobmatnyc/claude-mpm/issues)
- **Repository**: [GitHub](https://github.com/bobmatnyc/claude-mpm)