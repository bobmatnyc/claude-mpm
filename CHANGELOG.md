# Changelog

All notable changes to claude-mpm will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.5.0]: https://github.com/bobmatnyc/claude-mpm/compare/v0.3.0...v0.5.0
[0.3.0]: https://github.com/bobmatnyc/claude-mpm/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/bobmatnyc/claude-mpm/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/bobmatnyc/claude-mpm/releases/tag/v0.1.0