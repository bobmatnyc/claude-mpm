# Claude MPM - Multi-Agent Project Manager

A clean implementation of Claude orchestration with subprocess control, framework injection, and automatic ticket extraction.

## Overview

Claude MPM (Multi-Agent Project Manager) orchestrates Claude as a subprocess, enabling:

- **Subprocess Control**: Launch and manage Claude as a child process
- **Framework Injection**: Dynamically inject PM framework instructions
- **Ticket Extraction**: Automatically extract TODO/BUG/FEATURE items
- **Agent Delegation Detection**: Track delegations to specialized agents
- **Agent Registry Integration**: Full integration with claude-multiagent-pm's agent system
- **Session Logging**: Comprehensive logging of all interactions
- **AI Trackdown Integration**: Create tickets using ai-trackdown-pytools

## Installation

### From Source (Development)

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
- ai-trackdown-pytools (optional, for ticket creation)

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

# Quick ticket management (using ticket wrapper)
./ticket create "Fix bug" -t bug -p high
./ticket list
./ticket view TSK-0001
```

### Ticket Management

Claude MPM includes a simplified `ticket` wrapper for ai-trackdown:

```bash
# Create tickets quickly
./ticket create "Add new feature" -t feature
./ticket create "Fix login bug" -t bug -p high -d "Users cannot log in"

# List and view tickets
./ticket list
./ticket view TSK-0001

# Update and close tickets
./ticket update TSK-0001 -s in_progress
./ticket close TSK-0001
```

See [docs/ticket_wrapper.md](docs/ticket_wrapper.md) for full documentation.

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

## How It Works

### 1. Subprocess Orchestration

Claude MPM launches Claude as a subprocess using `subprocess.Popen`, maintaining full control over I/O streams:

```python
# Launch Claude with specific model
process = subprocess.Popen(
    ["claude", "--model", "opus"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)
```

### 2. Framework Injection

On first user interaction, the framework automatically injects PM instructions:

```
User Input → Framework Instructions + User Input → Claude
```

### 3. Ticket Extraction

The orchestrator monitors all Claude output for ticket patterns:

- `TODO:` → task ticket
- `BUG:` → bug ticket
- `FEATURE:` → feature ticket
- `FIXME:` → bug ticket
- `ISSUE:` → issue ticket
- `TASK:` → task ticket
- `ENHANCEMENT:` → enhancement ticket

### 4. Agent Delegation Detection

The orchestrator detects delegation patterns:

- `Delegate to Engineer:` → Explicit delegation
- `→ QA Agent:` → Arrow notation
- `Task for Documentation:` → Task assignment
- `Research Agent should:` → Implicit delegation
- `Ask Ops to:` → Request pattern

### 5. Process Hierarchy

```
Terminal
└── claude-mpm (orchestrator)
    └── claude (child process)
        └── [potential agent subprocesses via Task Tool]
```

## Architecture

```
claude-mpm/
├── src/claude_mpm/
│   ├── orchestrator.py      # Core subprocess orchestration
│   ├── ticket_extractor.py  # Pattern-based ticket extraction
│   ├── agent_delegator.py   # Agent delegation detection
│   ├── agent_registry.py    # claude-multiagent-pm integration
│   ├── framework_loader.py  # Framework instruction loading
│   ├── ticket_manager.py    # ai-trackdown-pytools integration
│   ├── logger.py           # Logging configuration
│   └── cli.py              # Command-line interface
├── tests/                   # Comprehensive test suite
├── examples/               # Usage examples
└── README.md              # This file
```

## Testing

```bash
# Run full test suite with coverage
python run_tests.py

# Run specific test file
pytest tests/test_orchestrator.py -v

# Run with debug output
pytest tests/ -v -s
```

## Logging

Logs are stored in `~/.claude-mpm/logs/` by default:

- `mpm_YYYYMMDD_HHMMSS.log` - Detailed debug logs
- `latest.log` - Symlink to most recent log
- Session logs in `~/.claude-mpm/sessions/`

## Integration with claude-multiagent-pm

Claude MPM is designed to work with the claude-multiagent-pm framework:

1. **Auto-Detection**: Finds framework in common locations
2. **Framework Loading**: Loads INSTRUCTIONS.md (or legacy CLAUDE.md) and agent definitions
3. **Agent Registry**: Full integration with AgentRegistry for dynamic agent discovery
4. **Agent Hierarchy**: Respects project → user → system precedence
5. **Delegation Tracking**: Monitors and reports agent delegations
6. **Task Tool Formatting**: Generates proper Task Tool delegations

### Agent Features

- **Dynamic Discovery**: Uses AgentRegistry.listAgents() for real-time agent discovery
- **Specialization Support**: Routes tasks based on agent specializations
- **Core Agents**: Documentation, Engineer, QA, Research, Ops, Security, Version Control, Data Engineer
- **Custom Agents**: Full support for project and user-defined agents
- **Delegation Patterns**: Detects explicit and implicit delegation patterns

## Development

### Running Tests

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

### Project Structure

- `orchestrator.py` - Main orchestration logic
- `ticket_extractor.py` - Regex-based pattern extraction
- `agent_delegator.py` - Agent delegation detection and formatting
- `agent_registry.py` - Integration with claude-multiagent-pm's agent system
- `framework_loader.py` - Framework detection and loading
- `ticket_manager.py` - Ticket creation via ai-trackdown-pytools
- `logger.py` - Structured logging setup
- `cli.py` - Command-line interface

## Troubleshooting

### Claude not found

Ensure Claude CLI is installed and in your PATH:

```bash
which claude
# Should output: /usr/local/bin/claude or similar
```

### Framework not detected

Specify framework path explicitly:

```bash
claude-mpm --framework-path /path/to/claude-multiagent-pm
```

### Tickets not created

1. Check ai-trackdown-pytools is installed:
   ```bash
   pip install ai-trackdown-pytools
   ```

2. Ensure you're in a project with tickets/ directory

3. Check logs for errors:
   ```bash
   tail -f ~/.claude-mpm/logs/latest.log
   ```

## License

MIT License - See LICENSE file for details