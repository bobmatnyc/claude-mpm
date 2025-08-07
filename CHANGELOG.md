# Changelog

All notable changes to claude-mpm will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [3.4.17] - 2025-08-07


### Chores

- update package.json version to 3.4.16 ([37c5ab2])
## [3.4.16] - 2025-08-07

## [3.4.15] - 2025-08-07

## [3.4.14] - 2025-08-07


### Chores

- update package.json version to 3.4.13 ([78c8ac0])
## [3.4.13] - 2025-08-07


### Chores

- update package.json version to 3.4.12 ([4adabbc])
## [3.4.12] - 2025-08-07

## [3.4.11] - 2025-08-07

### Bug Fixes

- **socketio**: resolve socketio daemon import path for installed environments ([50740ab])
  - Fix socketio_daemon.py import path issue that prevented Socket.IO server from starting in pipx/pip installed environments
  - Enhanced path detection logic to properly handle both development and installed environments  
  - Added site-packages path detection for pipx/pip installations
  - Reduced Socket.IO startup timeouts from 90s to ~15s (more reasonable now that dependency issue is fixed)
  - Better error messages with debugging information for import failures
  - Timeout reductions: max_attempts 30→12, initial_delay 1.0s→0.75s, max_delay 3.0s→2.0s
  - This fixes a critical issue where users couldn't start the Socket.IO monitoring server, especially with pipx installations

### Documentation

- add release notes for v3.4.10 Socket.IO dependency fix ([db3ae4c])
- enhance changelog entry for v3.4.10 with Socket.IO dependency fix details ([40289cb])

### Chores

- update package.json version to 3.4.10 ([8c0418d])
## [3.4.10] - 2025-08-07

### Bug Fixes

- **dependencies**: include Socket.IO dependencies as core requirements ([0ef2055])
  - Moved python-socketio, aiohttp, and python-engineio from optional to required dependencies
  - Resolves externally-managed-environment error on macOS with pipx installations  
  - Socket.IO monitoring now works out-of-the-box without manual dependency installation
  - Critical fix for users who couldn't use monitoring features due to missing dependencies

### Chores

- update package.json version to 3.4.10 ([8c0418d])
- bump version to 3.4.10 (patch release) ([latest])
## [3.4.9] - 2025-08-07

## [3.4.8] - 2025-08-07

## [3.4.7] - 2025-08-07

## [3.4.6] - 2025-08-07


### Chores

- sync package.json version to 3.4.5 and add release notes ([95278ab])
## [3.4.5] - 2025-08-07

### Changed
- **Project Organization**: Major cleanup and reorganization for better maintainability
  - Moved 458+ test files from `/scripts/` directory to proper `/tests/` directory structure
  - Organized tests by category: agents, integration, services, e2e, and fixtures
  - Consolidated dashboard components (renamed `web/` to `dashboard/`)
  - Enhanced documentation organization with new directory structure

### Added
- **Documentation Structure**: New organized documentation hierarchy
  - `/docs/archive/`: Historical documentation, QA reports, and archived materials
  - `/docs/assets/`: Documentation assets including project logo (claude-mpm.png)
  - `/docs/dashboard/`: Dashboard-specific documentation
  - `/docs/developer/`: Comprehensive developer documentation with API reference
  - `/docs/user/`: End-user guides and tutorials
  - `/tests/fixtures/`: Centralized test data and fixtures
  - `/tests/test-reports/`: Test execution reports and results

### Fixed
- **Backward Compatibility**: Added `ticket_wrapper.py` for seamless migration
  - Maintains compatibility for ticket functionality moved from `/scripts/` to proper location
  - Automatic path resolution and import handling
  - Graceful fallback mechanisms for existing integrations

### Documentation
- **Enhanced Structure Documentation**: Updated `docs/STRUCTURE.md` with current project organization
  - Documented all new directories and their purposes
  - Added file placement guidelines for new directories
  - Updated recent additions section with reorganization details

## [3.4.4] - 2025-08-07

## [3.4.3] - 2025-08-06

### Added
- **Memory System Agent Support**: Enhanced memory routing with 2 new agent types
  - Added `data_engineer` agent with specialized keywords for data pipelines, AI API integrations, and analytics
  - Added `test_integration` agent with focus on E2E testing, cross-system validation, and workflow testing
  - All 10 agent types now fully supported with optimized memory routing

### Improved
- **Memory Routing Algorithm**: Enhanced accuracy and fairness
  - Implemented square root normalization to prevent agents with extensive keyword lists from being unfairly penalized
  - Added multi-word keyword bonus scoring (1.5x multiplier) for better semantic relevance
  - Lowered routing threshold from 0.1 to 0.05 for better handling of diverse agent patterns
  - Enhanced confidence scoring with improved calculation for more accurate routing decisions

### Fixed
- **Agent Validation**: Added comprehensive validation functions
  - New `get_supported_agents()` method for retrieving all supported agent types
  - New `is_agent_supported()` method for validating agent types before routing
  - Enhanced error handling with timestamp and content length logging for better debugging

### Documentation
- **Comprehensive Agent Documentation**: Updated memory system documentation
  - Added detailed descriptions of all 10 supported agent types with specialized keywords
  - Enhanced routing algorithm documentation with recent improvements
  - Added comprehensive test coverage documentation for new agent types

## [3.4.2] - 2025-08-06

### Other Changes

- Merge branch 'feature/dash-node-viz' ([fb2ad11])
## [3.4.1] - 2025-08-06

### Improved
- **Socket.IO Server Reliability**: Enhanced PID validation with comprehensive health monitoring
  - Added defensive error handling for PID file validation
  - Implemented circuit breaker pattern for service resilience
  - Enhanced process resource monitoring and network connectivity checks
  - Added automatic recovery mechanisms with graduated escalation strategies
- **Dashboard Experience**: Consolidated agent display and enhanced file operations
  - Eliminated duplicate agent entries through improved tool correlation
  - Enhanced file viewer with integrated Git tracking support
  - Improved HUD component loading and visualization consistency
  - Better error handling and user feedback across dashboard components
- **Git Operations**: Enhanced working directory handling and branch validation
  - Fixed git diff operations with proper working directory context
  - Added robust branch existence checks and error handling
  - Improved version control operation reliability and error messages

### Fixed
- **System Architecture**: Major cleanup and organization improvements
  - Moved 458+ obsolete test files from `/scripts/` to `/tests/` directory
  - Consolidated dashboard components (renamed `web/` to `dashboard/`)
  - Enhanced memory system integration and CLI command structure
  - Removed redundant documentation and streamlined project organization

### Performance
- **Health Monitoring**: Implemented comprehensive system health checks
  - Added process validation with resource usage monitoring
  - Network connectivity verification for service dependencies
  - Configurable health check thresholds and recovery actions
  - Enhanced logging and diagnostic reporting for troubleshooting

## [3.4.0] - 2025-08-06

### Added
- **Agent Memory System Enhancements**:
  - Project-specific memory generation using new `ProjectAnalyzer` service
  - `/mpm memory init` command for quick project onboarding
  - Dynamic file discovery based on project type and characteristics
  - Agent-specific memory customization based on role
  - Real-time memory updates through hook integration
  - Hook-based context injection for dynamic memory loading

- **Socket.IO Server Reliability Features**:
  - Enhanced PID file validation with process verification using psutil
  - Comprehensive health monitoring system with configurable thresholds
  - Automatic recovery mechanisms with circuit breaker pattern
  - Enhanced error messages with platform-specific resolution steps
  - Graduated recovery strategies (log warnings, clear connections, restart service, emergency stop)
  - Health check API endpoints (`/health`, `/diagnostics`, `/metrics`)
  - JSON-enriched PID file format with process metadata and file locking

### Improved
- **Memory Templates**: Removed repetitive "Max: 15 items" annotations - limits now enforced programmatically
- **Documentation Processing**: Enhanced to dynamically discover relevant files based on project analysis
- **Memory Initialization**: Fixed PM agent type bug, now uses general-purpose agent

### Fixed
- Memory files now contain actual project-specific information instead of generic templates
- `/mpm memory init` command properly executes without PM agent type error

### Changed
- **Project Organization**: Deep clean for publishing readiness
  - Moved 100+ test files from `/scripts/` to `/tests/`
  - Archived 20+ QA reports to `docs/archive/`
  - Enhanced .gitignore to prevent temporary file commits
  - Removed debug HTML files and temporary test scripts

### Documentation
- Added comprehensive memory system documentation in `docs/MEMORY.md`
- Updated README with memory usage section and quick examples
- Added hook integration details for dynamic context injection

## [3.3.2] - 2025-08-04

## [3.3.1] - 2025-08-05

### Added
- **Per-Session Working Directories**: Each session can now have its own working directory
  - Set working directory via UI in monitoring dashboard
  - Directories persist across session switches
  - Git operations automatically use session's directory
  - Footer displays current working directory and git branch

### Fixed
- **Git Diff Viewer**: Fixed cross-project file operations
  - All git commands now properly use `-C` flag with working directory
  - Git diff viewer uses dashboard's current working directory
  - Improved error handling and display for git operations
  - Fixed "No git history found" errors for files in different projects

### Improved
- **Documentation**: Reorganized for better user experience
  - New QUICKSTART.md for getting started quickly
  - Dedicated monitoring.md for dashboard features
  - Streamlined README.md with clear navigation
  - Removed duplicate content and improved structure

### Changed
- Working directory automatically syncs when footer updates
- Session selection now loads associated working directory
- Git branch detection runs when working directory changes

## [3.3.0] - 2025-08-04

### Added
- **Session Resumption**: New `--resume` flag for continuing previous Claude conversations
  - Resume last session: `claude-mpm run --resume`
  - Resume specific session: `claude-mpm run --resume <session-id>`
  - Compatible with monitoring: `claude-mpm run --resume --monitor`
  - Maintains conversation context and history for improved Claude performance
  - Graceful error handling for invalid session IDs
  - Session continuity provides significant performance benefits for complex workflows

### Other Changes

- Add test file for git diff feature ([5a99eae])
## [3.2.0-beta.1] - 2025-07-30

### Added
- **Agent Memory System** (Beta) - Adaptive agents that learn project-specific patterns
  - Design document: docs/design/agent_memory_system.md
  - Implementation plan: docs/design/agent_memory_implementation_plan.md
  - Memory files stored in .claude-mpm/memories/ for each project
  - Per-agent knowledge accumulation with 8KB size limits
  - Opt-in automatic learning extraction from agent outputs
  - Manual memory management via CLI commands (planned)
  - Full backwards compatibility maintained

### Changed
- Memory system architecture planned for phased implementation:
  - Phase 1: Core memory manager and CLI commands
  - Phase 2: Hook integration for automatic memory injection
  - Phase 3: Agent template enhancements
  - Phase 4: Performance optimization and polish

### Notes
- This is a beta release for testing memory system design and planning
- No functional implementation yet - design phase only
- Memory files will be tracked in version control for team knowledge sharing
- Designed for local deployments with per-project agent specialization

## [3.1.5] - 2025-07-30

### Added
- Configurable WebSocket port with --websocket-port flag
- Instance identification in WebSocket events (port, host, working directory)
- find_websocket_port.py script to find available ports
- Port selection in HTML WebSocket monitor
- Support for running multiple claude-mpm instances on different ports

### Fixed
- WebSocket and launch-method flags now properly recognized in wrapper script

### Changed
- WebSocket server now creates new instances instead of using global singleton
- Enhanced WebSocket events with instance_info for multi-instance support
## [3.1.4] - 2025-07-30

### Added
- subprocess.Popen runner as alternative to os.execvp for better process control
- WebSocket API for real-time monitoring of Claude sessions
- --monitor CLI flag to enable WebSocket server
- --launch-method flag to choose between exec and subprocess launchers
- WebSocket test client and HTML monitor
- Documentation for WebSocket API usage

### Changed
- Renamed SimpleClaudeRunner to ClaudeRunner for clarity
- Made WebSocket imports lazy to avoid circular dependencies

## [3.1.2] - 2025-07-29

### Changed
- Version bump for deployment preparation
- Updated version across all configuration files

## [3.1.1] - 2025-07-28

### Fixed
- **Critical**: Fixed working directory enforcement in base_service.py
  - All file write operations now correctly use absolute paths based on the working directory
  - Prevents accidental writes to system directories outside the project
  - Ensures consistent behavior across all services inheriting from BaseService

### Security
- Enhanced path resolution to always use absolute paths for file operations
- Strengthened working directory boundaries to prevent unauthorized file access

## [3.1.0] - 2025-07-28


### Chores

- update package.json version to 3.0.1 ([f091991])
## [3.1.0] - 2025-07-28

### Added
- **PM (Project Manager) Agent**: New orchestrator agent for multi-agent workflows
  - Coordinates complex tasks across multiple specialized agents
  - Ensures all delegated agents operate within security boundaries
  - Provides high-level task planning and delegation
- **Enhanced Filesystem Security**: Agent-level file access restrictions
  - New `file_access` configuration in agent schema for custom boundaries
  - Granular control over read/write permissions per agent
  - Working directory enforcement for all file operations
- **Security Enhancements**:
  - All agents now validate file operations against configured boundaries
  - Path traversal protection enhanced with agent-specific rules
  - Comprehensive audit logging for all file access attempts

### Changed
- Updated agent schema to support `file_access` configuration
- Enhanced security validation to check agent-specific restrictions
- Improved error messages for security violations

### Security
- **Working Directory Enforcement**: All file write operations are now restricted to the working directory by default
- **Agent Boundaries**: Each agent can define custom file access patterns for additional security
- **Audit Trail**: Enhanced logging provides complete visibility into file access attempts

## [3.0.1] - 2025-07-28

### Fixed
- Fixed JSON schema validation to properly handle optional fields
- Improved test coverage for agent deployment validation
- Fixed integration tests to handle schema validation errors correctly
- Corrected agent loader backward compatibility handling

### Chores
- update package.json version to 3.0.0 ([f38efbb])
## [3.0.0] - 2025-07-28

### BREAKING CHANGES
- **Agent Definition Format Migration**: Agent definitions migrated from Markdown (.md) to YAML (.yaml) format
  - All agent files must now use YAML format for better structure and validation
  - Existing .md agent files will no longer be recognized
  - See migration guide for converting existing agents

### Added
- **Enhanced Agent Schema**: Comprehensive validation for agent configurations
- **Security Validation**: Built-in security checks for agent configurations
- **Agent Deployment System**: Improved lifecycle management for agents
- **Test Coverage**: Comprehensive test suite for agent deployment
- **Version Control**: Enhanced semantic versioning support

### Changed
- **Agent Templates**: All agent templates updated to use JSON schema format
- **Agent Files**: Migrated all built-in agents from .md to .yaml format
  - `data_engineer.md` → `data_engineer.yaml`
  - `documentation.md` → `documentation.yaml`
  - `engineer.md` → `engineer.yaml`
  - `ops.md` → `ops.yaml`
  - `qa.md` → `qa.yaml`
  - `research.md` → `research.yaml`
  - `security.md` → `security.yaml`
  - `version_control.md` → `version_control.yaml`

### Fixed
- Agent validation and deployment reliability
- Schema validation for agent configurations

## [2.2.0] - 2025-07-28

### Features
- Remove obsolete cli_old directory ([5b7c0f0])

## [2.1.2] - 2025-07-27

### Fixed
- Minor bug fixes and stability improvements
- Package distribution enhancements

## [2.1.1] - 2025-07-27

### Fixed
- Documentation updates and tooling improvements
- Enhanced release script to handle both PyPI and npm publishing

## [2.1.0] - 2025-07-27

### Added
- Dynamic agent capabilities generation
- Support for MCP servers integration

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

### Added
- **Major Hook System Refactor**: Complete overhaul of the hook system architecture
  - New hook deployment and lifecycle management
  - Enhanced hook validation and error handling
  - Improved hook service performance and reliability
- **Agent Deployment Improvements**: Enhanced agent loading and validation
  - Better error messages for agent configuration issues
  - Improved agent discovery mechanism
  - Enhanced agent metadata handling
- **Documentation Enhancements**: Major documentation cleanup and organization
  - New comprehensive guides for hook system
  - Improved developer documentation
  - Better examples and tutorials

### Changed
- Refactored hook system for better modularity
- Updated agent deployment process
- Improved logging and debugging capabilities

### Fixed
- Various stability improvements in hook service
- Agent loading edge cases
- Documentation inconsistencies

## [1.0.1] - 2025-07-26

### Fixed
- npm package bin path configuration (removed leading ./ from bin path)
- Fork handling documentation and Claude Code integration context

### Added
- Unified release script for npm and PyPI synchronization
- Better version synchronization between npm and PyPI packages

### Changed
- Updated README with fork note and Claude Code integration instructions
- Improved npm package configuration

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

[3.1.0]: https://github.com/bobmatnyc/claude-mpm/compare/v3.0.1...v3.1.0
[3.0.1]: https://github.com/bobmatnyc/claude-mpm/compare/v3.0.0...v3.0.1
[3.0.0]: https://github.com/bobmatnyc/claude-mpm/compare/v2.2.0...v3.0.0
[2.2.0]: https://github.com/bobmatnyc/claude-mpm/compare/v2.1.2...v2.2.0
[2.1.2]: https://github.com/bobmatnyc/claude-mpm/compare/v2.1.1...v2.1.2
[2.1.1]: https://github.com/bobmatnyc/claude-mpm/compare/v2.1.0...v2.1.1
[2.1.0]: https://github.com/bobmatnyc/claude-mpm/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/bobmatnyc/claude-mpm/compare/v1.1.0...v2.0.0
[1.1.0]: https://github.com/bobmatnyc/claude-mpm/compare/v1.0.1...v1.1.0
[1.0.1]: https://github.com/bobmatnyc/claude-mpm/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/bobmatnyc/claude-mpm/compare/v0.5.0...v1.0.0
[0.5.0]: https://github.com/bobmatnyc/claude-mpm/compare/v0.3.0...v0.5.0
[0.3.0]: https://github.com/bobmatnyc/claude-mpm/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/bobmatnyc/claude-mpm/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/bobmatnyc/claude-mpm/releases/tag/v0.1.0