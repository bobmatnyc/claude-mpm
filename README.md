# Claude MPM - Multi-Agent Project Manager

> **Note**: This project is a fork of [claude-multiagent-pm](https://github.com/kfsone/claude-multiagent-pm), enhanced to integrate with [Claude Code](https://docs.anthropic.com/en/docs/claude-code) v1.0.60+'s native agent system. This integration enables seamless orchestration of Claude Code's built-in agents (research, engineer, qa, documentation, security, ops, version_control, data_engineer) through a unified project management interface.

A framework for Claude that enables multi-agent workflows and extensible capabilities through a modular architecture.


## 📚 Documentation

- **[User Guide](docs/user/)** - Getting started, usage, and troubleshooting
- **[Developer Guide](docs/developer/)** - Architecture, API reference, and contributing
- **[Design Documents](docs/design/)** - Architectural decisions and design patterns
- **[Differences from claude-multiagent-pm](docs/user/differences-from-claude-multiagent-pm.md)** - Migration guide

## Why Claude MPM?

Claude MPM provides a modular framework for extending Claude's capabilities:

- **🧩 Modular Architecture**: Extensible agent system and hook-based customization
- **🤖 Multi-Agent Support**: Specialized agents for different tasks
- **📝 Comprehensive Logging**: Every interaction is logged for review
- **🛠️ Service-Based Design**: Clean separation of concerns through services

## How It Works

```
┌─────────────┐       ┌─────────────────┐       ┌──────────────┐
│   Terminal  │──────▶│   Claude MPM    │──────▶│   Services   │
│   (User)    │       │   Framework     │       │   & Agents   │
└─────────────┘       └─────────────────┘       └──────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
              ┌─────▼─────┐    ┌─────▼─────┐
              │   Hook    │    │   Agent   │
              │  System   │    │  Registry │
              └───────────┘    └───────────┘
```

## Overview

Claude MPM provides a modular framework for extending Claude's capabilities:

- **Agent System**: Specialized agents for different task types
- **Hook System**: Extensible architecture through pre/post hooks
- **Service Layer**: Clean separation of business logic
- **Agent Registry**: Dynamic agent discovery and loading
- **Session Logging**: Comprehensive logging of all interactions

## Key Features

### Agent System
- Specialized agents for different domains (Research, Engineer, etc.)
- Dynamic agent discovery and registration
- Template-based agent definitions
- Extensible agent architecture

### Hook System
- Pre and post-processing hooks
- Customizable behavior injection
- Plugin-like extensibility
- Clean integration points

### Service Architecture
- Modular service components
- Clean separation of concerns
- Reusable business logic
- Well-defined interfaces

### Session Management
- Comprehensive logging of all interactions
- Debug mode for troubleshooting
- Organized log structure
- Performance monitoring

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/claude-mpm.git
cd claude-mpm

# Run development installation script
./install_dev.sh

# Activate virtual environment
source venv/bin/activate
```

### Dependencies

#### Core Requirements
- Python 3.8+
- Claude CLI (must be installed and in PATH)

#### Automatically Installed
- tree-sitter & language packs (for code analysis)
- All other Python dependencies

#### Code Analysis Dependencies
- **tree-sitter** (>=0.21.0) - Core parsing library for advanced code analysis
- **tree-sitter-language-pack** (>=0.20.0) - Multi-language support package providing parsers for 41+ programming languages

These tree-sitter dependencies enable:
- **Advanced Code Analysis**: The TreeSitterAnalyzer component provides syntax-aware code parsing for Research Agent operations
- **Agent Modification Tracking**: Real-time analysis of agent code changes with AST-level understanding
- **Multi-Language Support**: Out-of-the-box support for Python, JavaScript, TypeScript, Go, Rust, Java, C/C++, and 35+ other languages
- **Performance**: Fast, incremental parsing suitable for real-time analysis during agent operations

## Usage

### Basic Usage

```bash
# Run interactive session
claude-mpm

# Run with debug logging
claude-mpm --debug

# Show configuration info
claude-mpm info
```


### Command Line Options

```
claude-mpm [-h] [-d] [--log-dir LOG_DIR] {run,info}

Options:
  -d, --debug          Enable debug logging
  --log-dir LOG_DIR    Custom log directory (default: ~/.claude-mpm/logs)

Commands:
  run                  Run Claude session (default)
  info                 Show framework and configuration info
```

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/yourusername/claude-mpm.git
cd claude-mpm
./install_dev.sh
source venv/bin/activate

# 2. Run interactive session
claude-mpm

# 3. Or run a single command
claude-mpm run -i "Explain the codebase structure" --non-interactive
```


## Architecture

### Core Components

```
claude-mpm/
├── src/claude_mpm/
│   ├── agents/                  # Agent templates
│   ├── core/                    # Core functionality
│   │   ├── agent_registry.py    # Agent discovery
│   │   └── simple_runner.py     # Main runner
│   ├── services/                # Business logic
│   │   ├── hook_service.py
│   │   └── agent_deployment.py
│   ├── hooks/                   # Hook system
│   └── cli/                     # CLI interface
└── docs/                        # Organized documentation
    ├── user/                    # User guides
    ├── developer/               # Developer docs
    └── design/                  # Architecture docs
```

## Testing

```bash
# Run all tests
./scripts/run_all_tests.sh

# Run E2E tests
./scripts/run_e2e_tests.sh

# Run specific test
pytest tests/test_orchestrator.py -v
```

## Logging

Logs are stored in `~/.claude-mpm/logs/` by default:

- `mpm_YYYYMMDD_HHMMSS.log` - Detailed debug logs
- `latest.log` - Symlink to most recent log
- Session logs in `~/.claude-mpm/sessions/`


## Development

For detailed development information, see the [Developer Documentation](docs/developer/).

### Quick Start

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
python run_tests.py

# Test agent integration
python examples/test_agent_integration.py
```

### Key Resources

- [Architecture Overview](docs/developer/README.md#architecture-overview)
- [Project Structure](docs/developer/STRUCTURE.md)
- [Testing Guide](docs/developer/QA.md)
- [API Reference](docs/developer/README.md#api-reference)
- [Contributing Guide](docs/developer/README.md#contributing)

## Troubleshooting

For detailed troubleshooting, see the [User Guide](docs/user/README.md#troubleshooting).

### Quick Fixes

**Claude not found**
```bash
which claude  # Check if Claude is in PATH
```


**Debug mode**
```bash
claude-mpm --debug               # Enable debug logging
tail -f ~/.claude-mpm/logs/latest.log  # View logs
```

## License

MIT License - See LICENSE file for details