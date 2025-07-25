# Claude MPM - Multi-Agent Project Manager

A subprocess orchestration layer for Claude that enables multi-agent workflows, automatic ticket extraction, and comprehensive session management.

> **Fork Notice**: This is a fork and evolution of [claude-multiagent-pm](https://github.com/bobmatnyc/claude-multiagent-pm) that fundamentally changes how Claude is orchestrated from file-based (CLAUDE.md) to subprocess-based control. See [key differences](docs/user/differences-from-claude-multiagent-pm.md).

## 📚 Documentation

- **[User Guide](docs/user/)** - Getting started, usage, and troubleshooting
- **[Developer Guide](docs/developer/)** - Architecture, API reference, and contributing
- **[Design Documents](docs/design/)** - Architectural decisions and design patterns
- **[Differences from claude-multiagent-pm](docs/user/differences-from-claude-multiagent-pm.md)** - Migration guide

## Why Claude MPM?

Unlike traditional CLAUDE.md file-based configuration, Claude MPM runs Claude as a **managed subprocess**, providing:

- **🎮 Full Process Control**: Start, stop, and manage Claude programmatically
- **💉 Dynamic Injection**: Inject framework instructions at runtime, not via static files
- **📊 Real-time Monitoring**: Intercept all I/O for pattern detection and logging
- **🎫 Automatic Ticket Creation**: Extract TODOs, BUGs, and FEATUREs automatically
- **📝 Comprehensive Logging**: Every interaction is logged for review
- **🛡️ Memory Protection**: Prevent runaway processes from consuming system resources

### The Power of Subprocess Control

With Claude MPM, you're not just running Claude - you're orchestrating it:

```bash
# Traditional: Claude reads files, you hope for the best
claude  # Reads CLAUDE.md, no visibility

# Claude MPM: Full control and visibility
claude-mpm  # Launches Claude with monitoring, logging, and automation
```

## How It Works

```
┌─────────────┐       ┌─────────────────┐       ┌──────────────┐
│   Terminal  │──────▶│   Claude MPM    │──────▶│    Claude    │
│   (User)    │       │  (Orchestrator) │       │ (Subprocess) │
└─────────────┘       └─────────────────┘       └──────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
              ┌─────▼─────┐    ┌─────▼─────┐
              │  Ticket   │    │   Agent   │
              │ Extractor │    │ Delegator │
              └───────────┘    └───────────┘
```

## Overview

Claude MPM orchestrates Claude as a subprocess, enabling:

- **Subprocess Control**: Launch and manage Claude as a child process
- **Framework Injection**: Dynamically inject PM framework instructions
- **Ticket Extraction**: Automatically extract TODO/BUG/FEATURE items
- **Agent Delegation Detection**: Track delegations to specialized agents
- **Agent Registry Integration**: Full integration with claude-multiagent-pm's agent system
- **Session Logging**: Comprehensive logging of all interactions
- **AI Trackdown Integration**: Create tickets using ai-trackdown-pytools

## Key Features

### Subprocess Orchestration
- Launch Claude as a managed child process
- Full control over stdin/stdout/stderr
- Dynamic prompt injection without file pollution
- Process-level error handling and recovery

### Automatic Ticket Extraction
- Real-time pattern matching on Claude's output
- Automatic creation of TODO, BUG, FEATURE tickets
- Integration with ai-trackdown-pytools
- No manual ticket creation needed

### Agent Delegation Detection
- Monitor for delegation patterns in output
- Track which agents are handling tasks
- Format proper Task Tool delegations
- Support for all claude-multiagent-pm agents

### Session Management
- Comprehensive logging of all interactions
- Session replay capabilities
- Debug mode for troubleshooting
- Organized log structure

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
- ai-trackdown-pytools (for ticket management)
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
# Run interactive orchestrated session
claude-mpm

# Run with debug logging
claude-mpm --debug

# Run without automatic ticket creation
claude-mpm run --no-tickets

# List recent tickets
claude-mpm tickets

# Show configuration info
claude-mpm info

# Ticket management (automatically available)
claude-mpm-ticket create "Fix bug" -t bug -p high
claude-mpm-ticket list
claude-mpm-ticket view TSK-0001

# Or use the local wrapper
./ticket create "Fix bug" -t bug -p high
```

### Ticket Management

Claude MPM automatically installs ai-trackdown-pytools and provides the `claude-mpm-ticket` command:

```bash
# Create tickets quickly (available after installation)
claude-mpm-ticket create "Add new feature" -t feature
claude-mpm-ticket create "Fix login bug" -t bug -p high -d "Users cannot log in"

# List and view tickets
claude-mpm-ticket list
claude-mpm-ticket view TSK-0001

# Update and close tickets
claude-mpm-ticket update TSK-0001 -s in_progress
claude-mpm-ticket close TSK-0001

# Or use the local wrapper
./ticket create "Fix bug" -t bug -p high
```

See [Ticket Management Guide](docs/user/ticket_wrapper.md) for full documentation.

### Command Line Options

```
claude-mpm [-h] [-d] [--log-dir LOG_DIR] [--framework-path FRAMEWORK_PATH] {run,tickets,info}

Options:
  -d, --debug          Enable debug logging
  --log-dir LOG_DIR    Custom log directory (default: ~/.claude-mpm/logs)
  --framework-path     Path to claude-multiagent-pm framework

Commands:
  run                  Run orchestrated Claude session (default)
  tickets              List recent tickets
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

## How Subprocess Orchestration Works

### The Traditional Way (claude-multiagent-pm)
```
Project/
├── CLAUDE.md          # Static configuration file
└── src/               # Claude reads CLAUDE.md on startup

# User runs: claude
# Claude reads CLAUDE.md from disk
# No external control or monitoring
```

### The Claude MPM Way
```python
# No files in your project!
# Framework injected via subprocess:

orchestrator = SubprocessOrchestrator()
orchestrator.start()  # Launch Claude as subprocess
orchestrator.inject_framework()  # Inject instructions via stdin
orchestrator.monitor_output()  # Real-time pattern detection
orchestrator.extract_tickets()  # Automatic ticket creation
orchestrator.log_session()  # Comprehensive logging

# Full programmatic control over Claude!
```

### Benefits of Subprocess Approach

1. **Clean Projects**: No CLAUDE.md files polluting your repository
2. **Dynamic Control**: Change behavior at runtime
3. **Advanced Features**: Pattern detection, ticket extraction, logging
4. **Better Integration**: Works with any project structure
5. **Process Safety**: Memory limits, error recovery, timeouts

## Architecture

### Core Components

```
claude-mpm/
├── src/claude_mpm/
│   ├── orchestration/           # Subprocess orchestrators
│   │   ├── subprocess_orchestrator.py
│   │   ├── system_prompt_orchestrator.py
│   │   └── agent_delegator.py
│   ├── core/                    # Core functionality
│   │   ├── agent_registry.py    # Agent discovery
│   │   ├── claude_launcher.py   # Main launcher
│   │   └── ticket_extractor.py  # Pattern matching
│   ├── services/                # Business logic
│   │   ├── hook_service.py
│   │   └── ticket_manager.py
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

## Relationship to claude-multiagent-pm

Claude MPM is a fork and evolution of [claude-multiagent-pm](https://github.com/bobmatnyc/claude-multiagent-pm) that changes the fundamental approach:

### What's Different

| Feature | claude-multiagent-pm | Claude MPM |
|---------|---------------------|------------|
| **Context Loading** | CLAUDE.md file | Subprocess injection |
| **Process Control** | None | Full subprocess management |
| **Ticket Extraction** | Manual | Automatic |
| **Session Logging** | No | Yes |
| **Memory Protection** | No | Yes |
| **Dynamic Injection** | No | Yes |

### What's the Same

- Same agent system and templates
- Same specialization patterns
- Same delegation mechanisms
- Compatible agent definitions

### Migration

Moving from claude-multiagent-pm to Claude MPM:

1. **No CLAUDE.md needed** - Framework injected automatically
2. **Same agents work** - Full compatibility maintained
3. **New features** - Tickets, logging, process control
4. **Cleaner projects** - No framework files in your repo

See [detailed differences](docs/user/differences-from-claude-multiagent-pm.md) for more information.

## Development

For detailed development information, see the [Developer Documentation](docs/developer/).

### Quick Start

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
python run_tests.py

# Run example orchestration
python examples/test_orchestration.py

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

**Framework not detected**
```bash
claude-mpm --framework-path /path/to/claude-multiagent-pm
```

**Tickets not created**
```bash
pip install ai-trackdown-pytools  # Install ticket system
mkdir -p tickets/tasks            # Create ticket directory
```

**Debug mode**
```bash
claude-mpm --debug               # Enable debug logging
tail -f ~/.claude-mpm/logs/latest.log  # View logs
```

## License

MIT License - See LICENSE file for details