# Changelog

All notable changes to claude-mpm will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-07-26

## [1.0.1] - 2025-07-26

## [1.0.0] - 2025-07-26

### BREAKING CHANGES
- **Simplified architecture**: Replaced the entire orchestrator system with a simple runner
  - Removed 16 orchestrator implementations and consolidated to `simple_runner.py`
  - Deleted todo hijacking and subprocess runner features
  - Removed agent modification tracker service
  - Archived old orchestrators to `orchestration/archive/`

### Added
- **TodoWrite Agent Prefix Hook system**: Automatic delegation of todo items to specialized agents
  - `todo_agent_prefix_hook.py` for automatic todo list delegation
  - `tool_call_interceptor.py` for intercepting TodoWrite tool calls
  - Comprehensive documentation and example implementations
  - Test script for validating todo hook functionality
- **Enhanced CLI with argument preprocessing**: Better command-line interaction
  - Support for `@agent` syntax for direct agent specification
  - Pass-through arguments to Claude with proper escaping
  - Improved logging and error handling in CLI operations

### Changed
- **Updated agent instructions**: Clearer guidelines for agent development
- **Simplified ticket manager**: Removed unnecessary complexity in ticket management
- **Streamlined test suite**: Removed 15 obsolete test files related to old orchestration patterns
- **Updated remaining tests**: Modified to work with simplified architecture
- **Improved framework loader**: Better clarity and maintainability

### Removed
- Complex orchestrator system (moved to archive)
- Todo hijacking features
- Subprocess runner features
- Agent modification tracker service
- Obsolete tests for deprecated features

### Fixed
- Test suite compatibility with new architecture
- Import paths and module references

## [0.5.0] - 2024-01-25

### Added
- Comprehensive deployment support for multiple distribution channels:
  - PyPI deployment with enhanced setup.py and post-install hooks
  - npm deployment with Node.js wrapper scripts
  - Local installation with install.sh/uninstall.sh scripts
- Automatic directory initialization system:
  - User-level ~/.claude-mpm directory structure
  - Project-level .claude-mpm directory support
  - Configuration file templates
- Ticket command as a proper entry point:
  - Available as `ticket` after installation
  - Integrated with ai-trackdown-pytools
  - Simplified ticket management interface
- Project initialization module (claude_mpm.init):
  - Automatic directory creation on first run
  - Dependency validation
  - Configuration management
- MANIFEST.in for proper package distribution
- Robust wrapper scripts handling both source and installed versions

### Changed
- Enhanced setup.py with post-installation hooks
- Updated entry points to include ticket command
- Improved CLI initialization to ensure directories exist
- Modified wrapper scripts to handle multiple installation scenarios

### Fixed
- Import path issues in various modules
- Virtual environment handling in wrapper scripts

## [0.3.0] - 2024-01-15

### Added
- Hook service architecture for context filtering and ticket automation
- JSON-RPC based hook system
- Built-in example hooks for common use cases

## [0.2.0] - 2024-01-10

### Added
- Initial interactive subprocess orchestration with pexpect
- Real-time I/O monitoring
- Process control capabilities

## [0.1.0] - 2024-01-05

### Added
- Basic claude-mpm framework with agent orchestration
- Agent registry system
- Framework loader
- Basic CLI structure

[1.0.0]: https://github.com/bobmatnyc/claude-mpm/compare/v0.5.0...v1.0.0
[0.5.0]: https://github.com/bobmatnyc/claude-mpm/compare/v0.3.0...v0.5.0
[0.3.0]: https://github.com/bobmatnyc/claude-mpm/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/bobmatnyc/claude-mpm/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/bobmatnyc/claude-mpm/releases/tag/v0.1.0