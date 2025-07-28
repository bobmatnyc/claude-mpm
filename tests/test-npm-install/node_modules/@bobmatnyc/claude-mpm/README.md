# Claude MPM - Multi-Agent Project Manager

> **Note**: This project is a fork of [claude-multiagent-pm](https://github.com/kfsone/claude-multiagent-pm), enhanced to integrate with [Claude Code](https://docs.anthropic.com/en/docs/claude-code) v1.0.60+'s native agent system. This integration enables seamless orchestration of Claude Code's built-in agents (research, engineer, qa, documentation, security, ops, version_control, data_engineer) through a unified project management interface.

> **⚠️ Version 2.0.0 Breaking Changes**: Agent schema has been standardized. Agent IDs no longer use the `_agent` suffix (e.g., `research_agent` → `research`). See the [migration guide](docs/user/05-migration/schema-standardization-migration.md) for details.

A framework for Claude that enables multi-agent workflows and extensible capabilities through a modular architecture.

## Quick Start

### Why Interactive Mode?
**Interactive mode is significantly more performant** than non-interactive commands. It maintains context between requests and avoids the overhead of repeatedly launching Claude, making your development workflow much faster and more efficient.

### Installation

```bash
# Install globally via npm (recommended)
npm install -g @bobmatnyc/claude-mpm

# Or use npx for one-time usage
npx @bobmatnyc/claude-mpm
```

### Three Essential Use Cases

#### 1. 🔍 **Understand Your Codebase**
Start with codebase exploration - perfect for onboarding or getting oriented:

```bash
# Launch interactive mode
claude-mpm

# Then ask:
> Explain the codebase structure. What are the main components, how do they interact, and what architectural patterns are used?
```

#### 2. 🚀 **Build a New Project** 
For greenfield development, use detailed, AI-generated prompts for best results:

```bash
claude-mpm

# Example detailed prompt (AI-generated prompts work best):
> Create a modern web application with the following requirements:
> - Next.js 14 with TypeScript and Tailwind CSS
> - Authentication using NextAuth.js with GitHub provider
> - PostgreSQL database with Prisma ORM
> - User dashboard with CRUD operations for "projects"
> - API routes following REST conventions
> - Responsive design with dark/light mode toggle
> - Form validation using react-hook-form and zod
> - Include proper error handling and loading states
> - Set up ESLint, Prettier, and basic testing with Jest
> - Generate a complete project structure with all necessary files
```

#### 3. 🔧 **Enhance Existing Code**
For working on your current codebase, provide rich context:

```bash
claude-mpm

# Example detailed enhancement prompt:
> I need to add real-time notifications to my existing Next.js application. Current tech stack:
> - Next.js 13 with app router
> - TypeScript
> - Tailwind CSS
> - PostgreSQL with Prisma
> - User authentication already implemented
> 
> Requirements:
> - WebSocket-based real-time notifications
> - Toast notifications in the UI
> - Database table to store notification history
> - Mark as read/unread functionality
> - Different notification types (info, warning, success, error)
> - Admin panel to send system-wide notifications
> - Email fallback for offline users
> 
> Please analyze my current codebase structure and implement this feature following my existing patterns and conventions.
```

### 💡 Pro Tips for Better Results

1. **Use AI to generate your prompts**: Ask ChatGPT or Claude to help you create detailed, specific prompts for your use case
2. **Provide context**: Include your tech stack, requirements, and any constraints
3. **Stay interactive**: Keep the conversation going to refine and iterate on solutions
4. **Ask for explanations**: Request explanations of architectural decisions and trade-offs

### Alternative: Non-Interactive Mode
For automation or simple one-off tasks:

```bash
# Quick analysis
claude-mpm run -i "What testing frameworks are used in this project?" --non-interactive

# With subprocess orchestration for complex tasks
claude-mpm run --subprocess -i "Audit this codebase for security vulnerabilities" --non-interactive
```

**Note**: Non-interactive mode has higher overhead and is less efficient for multi-step development workflows.


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

### Other Installation Methods

#### Using UV (Recommended - Fast)
UV is a lightning-fast Python package manager written in Rust, offering 10-100x speed improvements over pip.

```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install claude-mpm with UV
uv pip install claude-mpm

# Or install from git
uv pip install git+https://github.com/bobmatnyc/claude-mpm.git
```

#### Using pip (Traditional)
```bash
# Install from PyPI
pip install claude-mpm

# Or install from git
pip install git+https://github.com/bobmatnyc/claude-mpm.git
```

### From Source (Development)

```bash
# Clone the repository
git clone https://github.com/bobmatnyc/claude-mpm.git
cd claude-mpm

# Option A: Using UV (Recommended - Much faster)
uv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
uv pip install -e .

# Option B: Traditional approach
./install_dev.sh
source venv/bin/activate
```

### Dependencies

#### Core Requirements
- Python 3.8+
- Claude Code CLI 1.0.60+ (must be installed and in PATH)

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