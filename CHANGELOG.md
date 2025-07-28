# Changelog

All notable changes to claude-mpm will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.2] - 2025-07-27

## [2.2.0] - 2025-07-27

## [2.0.0] - 2025-07-27

### BREAKING CHANGES
- **Agent Schema Standardization**: Complete overhaul of agent definition format
  - Agent IDs no longer use `_agent` suffix (e.g., `research_agent` → `research`)
  - Migrated from YAML to JSON format with strict schema validation
  - All agents must conform to new standardized schema at `src/claude_mpm/schemas/agent_schema.json`
  - Resource allocation now uses predefined tiers (intensive, standard, lightweight)
  - Model names standardized (e.g., `claude-sonnet-4-20250514` → `claude-4-sonnet-20250514`)

### Added
- **Comprehensive Schema Validation Framework**
  - JSON Schema-based validation for all agent definitions
  - Business rule validation for resource allocation consistency
  - Automatic validation on agent load
  - Migration tools for converting old format to new
- **Resource Tier System**
  - Three predefined tiers: intensive (900s/3072MB), standard (600s/2048MB), lightweight (300s/1024MB)
  - Automatic resource allocation based on agent type
  - Clear rationale for resource assignments
- **Enhanced Agent Metadata**
  - Required metadata fields: name, description, category, tags
  - Optional fields: author, created_at, updated_at
  - Improved agent discoverability through standardized tags
- **Validation API**
  - `AgentValidator` class for programmatic validation
  - Detailed error and warning reporting
  - Integration with CI/CD pipelines

### Changed
- **Agent Definition Format**
  - Migrated from YAML to JSON for better schema validation
  - Standardized field names and structure
  - Added required version field using semantic versioning
  - Instructions limited to 8000 characters for consistency
- **Agent Loader Improvements**
  - Backward compatibility for old agent IDs (both `research` and `research_agent` work)
  - Performance improvements through caching (1.6x faster)
  - Better error messages for validation failures
- **Model Naming Convention**
  - Standardized to `claude-{version}-{variant}-{date}` format
  - Updated all agents to use consistent model names

### Fixed
- **Validation Issues**
  - Inconsistent versioning across agents (was using integers, now semantic)
  - Resource allocation inconsistencies
  - Missing required fields in some agents
  - Tool array inconsistencies

### Migration Guide
- See [Schema Standardization Migration Guide](docs/user/05-migration/schema-standardization-migration.md)
- Use backward compatibility layer during transition
- Run validation on all custom agents before deployment

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