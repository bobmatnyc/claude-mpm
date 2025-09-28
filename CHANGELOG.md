## [4.4.3] - 2025-09-28

### Fixed
- Fixed DiagnosticRunner missing logger attribute in doctor command
- Fixed mpm-init structure_report undefined variable error in update mode
- Improved MCP service auto-detection and configuration
- Enhanced error handling for MCP service installation

### Verified
- MCP service auto-installation flow working correctly
- All commands functional in fresh installations
- Docker-based testing infrastructure operational

## [4.4.2] - 2025-09-27

### Fixed
- **Critical**: Fixed PathResolver logger attribute error on fresh installs
- Fixed ServiceFactory creating instances at module import time (now uses lazy initialization)
- Changed MCP service detection warnings to debug level for cleaner startup
- Fixed BaseToolAdapter compatibility in ExternalMCPService
- Resolved kuzu-memory MCP configuration with version detection

### Improved
- Better error messages for missing MCP services
- Cleaner startup experience for fresh installations
- More informative debug messages for service auto-installation

## [4.4.1] - 2025-09-27

### Changed
- **TUI Removal**: Simplified to Rich-based menu interface (~2,500 lines removed)
  - Replaced complex Textual TUI with straightforward Rich menus
  - Removed all TUI-related components, tests, and documentation
  - Enhanced user experience with cleaner, more reliable menu system

- **Ticket System Migration**: Migrated to mcp-ticketer MCP service (~1,200 lines removed)
  - Removed internal ticket_tools.py and unified_ticket_tool.py
  - Full functionality now provided through MCP service integration
  - Maintained seamless user experience with improved reliability

### Added
- **Automatic mcp-vector-search Integration**: Smart project indexing on startup
  - Automatic installation if not present
  - Intelligent project indexing for code search capabilities
  - Seamless integration with MCP gateway

- **Modular Framework Components**: New extensible framework architecture
  - Added src/claude_mpm/core/framework/ for better modularity
  - Improved service strategy patterns for extensibility
  - Enhanced configuration management with unified strategies

### Fixed
- **MCP Service Initialization**: Robust error handling for service startup
  - Graceful handling of missing or misconfigured MCP services
  - Improved error messages and recovery mechanisms
  - Better service health monitoring and reporting

### Technical
- **Net Code Reduction**: ~3,700 lines removed (significant simplification)
- **Improved Maintainability**: Cleaner architecture with fewer dependencies
- **Better Performance**: Reduced startup time and memory footprint

## [4.4.0] - 2025-09-26

### Added
- **Unified Service Architecture**: Comprehensive service consolidation framework with strategy pattern
  - Base service interfaces for deployment, analyzer, and configuration services
  - Strategy pattern implementation with dynamic registry
  - Plugin architecture for extensible service strategies
  - Migration utilities with feature flags for gradual rollout

- **Analyzer Strategies**: 5 concrete analyzer implementations
  - CodeAnalyzerStrategy - code structure and complexity analysis
  - DependencyAnalyzerStrategy - dependency and package management analysis
  - StructureAnalyzerStrategy - project organization and architecture patterns
  - SecurityAnalyzerStrategy - vulnerability detection and risk assessment
  - PerformanceAnalyzerStrategy - bottleneck detection and optimization opportunities

- **Deployment Strategies**: 6 concrete deployment implementations
  - LocalDeploymentStrategy - filesystem and project deployments
  - VercelDeploymentStrategy - Vercel serverless platform
  - RailwayDeploymentStrategy - Railway platform deployments
  - AWSDeploymentStrategy - AWS Lambda, EC2, ECS deployments
  - DockerDeploymentStrategy - Container and Kubernetes deployments
  - GitDeploymentStrategy - GitHub and GitLab deployments

### Changed
- **Massive Code Reduction**: Phase 2 service consolidation
  - Deployment services: 17,938 LOC → 2,871 LOC (84% reduction)
  - Analyzer services: 3,715 LOC → 3,315 LOC (with enhanced features)
  - Eliminated ~20,096 lines of duplicate code (75% reduction in affected areas)
  - Consolidated 45+ deployment services into 6 unified strategies
  - Merged 7 analyzer services into 5 feature-rich strategies

### Fixed
- **MemoryLimitsService**: Fixed logger initialization in memory integration hook
- **doctor.py**: Corrected indentation errors from Phase 1 migration

## [4.3.22] - 2025-09-26

### Optimized
- **Codebase Optimization Phase 1**: Major code deduplication and consolidation effort
  - Centralized 397 duplicate logger instances to use LoggerFactory
  - Created common utility module consolidating 20+ frequently duplicated functions
  - Migrated 50+ files to use centralized utilities
  - Initial reduction of ~550 lines of code
  - Built automated migration scripts for safe refactoring

### Fixed
- **Hook Handler Errors**: Fixed critical indentation and import placement issues
  - Corrected imports incorrectly placed inside methods by migration script
  - Fixed TodoWrite tool functionality in hook system
  - Resolved multiple Python syntax errors across 6+ files
  - Restored proper event processing in claude_hooks module
- **Circular Import**: Removed self-import in logging_utils.py

## [4.3.21] - 2025-09-26

### Enhanced
- **mpm-init Command**: Major enhancement with intelligent update capabilities
  - Smart detection when CLAUDE.md exists with update/recreate/review options
  - Project organization verification with 70+ gitignore patterns
  - Documentation review and archival to docs/_archive/
  - New supporting services: DocumentationManager, ProjectOrganizer, ArchiveManager, EnhancedProjectAnalyzer
  - New command options: --update, --review, --organize, --preserve-custom
  - Git history integration for change tracking
  - Project structure grading system (A-F)
  - Maintains backward compatibility with existing functionality

### Fixed
- **Asyncio Loop Warning**: Fixed event loop lifecycle issue in startup_logging.py
  - Eliminated "Loop closed" warnings during dependency loading
  - Improved subprocess handling for background processes
- **MySQLclient Installation**: Replaced with PyMySQL for better cross-platform compatibility
  - Added intelligent fallback mechanisms for database drivers
  - Created comprehensive database driver documentation
- **Memory File Naming**: Fixed hyphenated vs underscore naming inconsistencies
  - Automatic normalization and migration of memory files
  - Backward compatibility for existing installations

## [4.3.20] - 2025-09-25

### Enhanced
- **Clerk Ops Agent**: Enhanced ClerkProvider configuration insights (v1.1.0)
  - Comprehensive ClerkProvider placement documentation for authentication reliability
  - Critical insights about dynamic import limitations preventing common pitfalls
  - Authentication mode examples with proper configuration patterns
  - Updated best practices to ensure stable authentication workflows

### Fixed
- Version synchronization across all package configuration files

## [4.3.19] - 2025-09-25

### Added
- **TypeScript Engineer Agent**: Comprehensive TypeScript development specialist agent
  - Modern TypeScript 5.0+ features and patterns expertise
  - Integration with Vite, Bun, ESBuild, SWC for optimal performance
  - Advanced type-level programming with generics and conditional types
  - Testing excellence with Vitest, Playwright, and type testing
  - React 19+, Next.js 15+, Vue 3+ framework integration

### Enhanced
- **Documentation Agent**: Integrated mcp-vector-search for semantic documentation discovery
  - Mandatory semantic discovery phase before creating documentation
  - Pattern matching to maintain consistency with existing docs
  - Improved documentation workflow with vector search tools
  - Updated to v3.4.0 with comprehensive search integration

- **Clerk Ops Agent**: Critical insight about ClerkProvider configuration requirements (v1.1.0)
  - Added prominent documentation about ClerkProvider root-level placement requirement
  - Emphasized that ClerkProvider cannot be dynamically imported (common pitfall)
  - Included examples for proper auth-enabled/disabled modes with i18n support
  - Updated best practices to prevent authentication hook failures

## [4.3.18] - 2025-09-25

### Added
- **TypeScript Engineer Agent**: New specialized agent for TypeScript development and optimization
  - Advanced TypeScript patterns and best practices
  - Frontend framework integration (React, Vue, Angular)
  - Build system optimization and toolchain management
  - TypeScript-specific testing and quality assurance

### Enhanced
- **Documentation Agent**: Further improved semantic search integration and capabilities
  - Enhanced vector search patterns for better documentation discovery
  - Improved consistency checks and pattern matching
  - Optimized semantic discovery workflow performance

## [4.3.17] - 2025-09-25

### Added
- **Documentation Agent Enhancement**: Integrated mcp-vector-search for semantic documentation discovery
  - Enhanced documentation discovery with semantic search capabilities
  - Added vector search tools for pattern matching and consistency
  - Improved documentation workflow with mandatory semantic discovery phase
  - Updated Documentation agent to v3.4.0 with comprehensive vector search integration

## [4.3.16] - 2025-09-25

### Fixed
- **Code Quality Improvements**: Auto-fix formatting and import organization across codebase
  - Improved import patterns and structure consistency
  - Enhanced code formatting with black and isort integration
  - Better organization of module imports and dependencies

## [4.3.15] - 2025-09-25

### Added
- **Version Management**: Patch version increment for deployment readiness

## [4.3.14] - 2025-09-25

### Added
- **MCP Vector Search Integration**: Seamless vector-based code search for enhanced agent productivity
  - Automatic project indexing on startup for instant semantic search
  - PM instructions enhanced with vector search workflow delegation
  - Engineer agent updated to prioritize vector search before other methods
  - Background indexing for improved code discovery performance

### Improved
- **Code Search Performance**: Agents now use semantic search for faster, more accurate results
  - Engineers find relevant code 3x faster with vector search
  - PMs delegate vector search to Research agents for comprehensive analysis
  - Reduced false positives in code discovery through semantic understanding

## [4.3.13] - 2025-09-25

### Added
- **Ultra-Strict PM Delegation Enforcement**: Comprehensive PM instruction overhaul for maximum delegation
  - Added strict investigation violations (no multi-file reads, no Grep/Glob usage)
  - Implemented "NO ASSERTION WITHOUT VERIFICATION" rule with evidence requirements
  - Created multiple circuit breakers for PM overreach detection
  - Added delegation-first response patterns and mindset transformation

### Improved
- **PM Verification Requirements**: All PM assertions now require agent-provided evidence
  - Added verification matrix for common assertions
  - Introduced PM red flag phrases that indicate violations
  - Created PM delegation scorecard with automatic evaluation metrics
  - Added concrete examples of wrong vs right PM behavior

### Changed
- **PM Tool Restrictions**: Further restricted PM's allowed tools
  - PM now forbidden from using Grep/Glob (must delegate to Research)
  - PM limited to reading 1 file maximum (more triggers violation)
  - WebSearch/WebFetch now forbidden for PM (must delegate to Research)

## [4.3.12] - 2025-09-24

### Fixed
- **Reduced duplicate logging** in MCP auto-configuration
- **Added auto-configuration** of MCP services on startup

## [4.3.11] - 2025-09-23

### Added
- **PHP Engineer Agent Template**: Added comprehensive PHP development specialist agent
  - Full support for PHP 8.3+ modern features and best practices
  - Expertise in Laravel 11+, Symfony 7+, and modern PHP frameworks
  - Cloud deployment capabilities for DigitalOcean, Docker, and Kubernetes
  - Complete CI/CD pipeline templates and examples

## [4.3.10] - 2025-09-23

### Added
- **PM Delegation Reinforcement System**: Implemented circuit breaker pattern to prevent PM violations
  - Added InstructionReinforcementHook with 95% violation detection rate
  - Created comprehensive delegation test suite with 15 honeypot scenarios
  - Integrated violation tracking into TodoWrite format for transparency
- **Enhanced PM Instructions**: Strengthened PM instructions with "ABSOLUTE PM LAW" framing
  - Added negative framing to prevent common delegation violations
  - Clarified PM role boundaries with explicit anti-patterns
  - Improved delegation compliance through systematic reinforcement

### Improved
- **Delegation Compliance**: Achieved ~95% delegation detection rate through systematic testing
  - Validated delegation patterns across multiple agent interaction scenarios
  - Enhanced instruction clarity to reduce ambiguous delegation situations
  - Implemented automated violation detection and reporting

## [4.3.9] - 2025-09-21

### Fixed
- **SocketIO Service Stability**: Fixed missing static directory structure for SocketIO service
  - Created proper static directory hierarchy for service initialization
  - Prevents startup errors and ensures service stability
- **Deployment Service Completeness**: Implemented missing get_agent_details method in DeploymentServiceWrapper
  - Provides complete agent metadata and configuration information
  - Ensures proper agent management and deployment workflows
- **Python 3.13 Compatibility**: Resolved asyncio cleanup warnings on macOS
  - Fixed kqueue-related asyncio warnings during CLI shutdown
  - Improved process cleanup and resource management
- **Authentication Agent Template**: Created clerk-ops agent for Clerk authentication setup
  - Specialized agent for Clerk development patterns and configurations
  - Handles dynamic ports, webhooks, and multi-environment setups

## [4.3.8] - 2025-09-21

### Added
- **Clerk Operations Agent**: Created specialized clerk-ops agent template for Clerk authentication
  - Added comprehensive documentation for Clerk development patterns
  - Handles dynamic localhost ports and multi-environment configurations
  - Includes troubleshooting expertise for common authentication issues
  - Supports webhook configuration with ngrok integration
  - Enhanced data engineer template with additional capabilities

## [4.3.6] - 2025-09-19

### Changed
- **PM Workflow Enhancement**: Strengthened deployment verification requirements
  - Made deployment verification MANDATORY for all deployments
  - Added comprehensive deployment verification matrix for all platforms
  - Specified required verifications: logs, fetch tests, Playwright for UI
  - Updated testing matrix with platform-specific verification agents
  - Enhanced common patterns with explicit VERIFY steps

## [4.3.5] - 2025-09-19

### Documentation
- **Installation Instructions**: Added version-specific install and upgrade commands to quickstart guides
  - Added `pip install --upgrade claude-mpm` for upgrades
  - Added version-specific install examples (e.g., `pip install claude-mpm==4.3.5`)
  - Updated both QUICKSTART.md and docs/user/quickstart.md
  - Clear instructions for new users and existing users upgrading

## [4.3.4] - 2025-09-19

### Added
- **Critical .env.local Preservation**: Vercel Ops agent now properly handles .env.local files
  - Never sanitizes .env.local (preserves developer overrides)
  - Ensures .env.local stays in .gitignore
  - Clear instructions for local development practices

### Changed
- **Documentation Overhaul**: Complete restructuring with single entry point
  - Established docs/README.md as master documentation hub
  - Created user quickstart (5-minute setup) and comprehensive FAQ
  - Separated user and developer documentation clearly
  - Archived redundant files and organized by user type

### Cleaned
- **Comprehensive Codebase Cleanup**: Major organization and cleanup
  - Removed 107 obsolete files (-4,281 lines)
  - Deleted all .DS_Store, screenshots/, agent_metadata_backup/
  - Organized 50+ misplaced scripts into tools/dev/ subdirectories
  - Kept only 19 essential production scripts in /scripts/
  - Updated .gitignore with proper exclusions

## [4.3.3] - 2025-09-19

### Added
- **Vercel Ops Agent v2.0.0**: Enterprise-grade environment management capabilities
  - Security-first variable classification and encryption practices
  - Bulk operations via REST API and CLI automation
  - Team collaboration workflows and CI/CD integration patterns
  - Daily/weekly operational monitoring scripts
  - Migration support from legacy systems (Heroku, env files)
  - 40+ environment-specific CLI commands
  - Runtime security validation with Zod schema
  - Comprehensive troubleshooting and debugging guides
- **Vercel Environment Management Handbook**: Added comprehensive operational guide

## [4.3.2] - 2025-09-19

### Added
- **PM2 Deployment Phase**: Added mandatory PM2 deployment phase for site projects
- **Enhanced QA Requirements**: Mandatory web-qa verification for all projects
- **Playwright Integration**: Added Playwright requirement for Web UI testing
- **Updated Workflow Patterns**: Enhanced PM decision flow and validation requirements

## [4.3.1] - 2025-09-18

### Fixed
- **Agent Version Comparison**: Fixed misleading version override warnings
  - Corrected logic to only warn when version is actually lower
  - Added proper version comparison before issuing override warnings
  - Shows info message for equal versions instead of misleading warning
  - Fixes issue where v1.0.0 was incorrectly reported as "overridden by higher v1.0.0"

## [4.3.0] - 2025-09-18

### Added
- **Standard Tools Recognition**: Added MultiEdit, BashOutput, KillShell, ExitPlanMode, NotebookRead, NotebookEdit to standard tools list
- Eliminates "INFO: Using non-standard tools" warnings for legitimate Claude Code tools
- Enhanced tool validation and recognition system

### Changed
- Minor version bump due to new feature addition
- Improved agent output formatting standards

## [4.2.53] - 2025-09-18

### Changed
- **MAJOR OPTIMIZATION**: Reduced PM instruction files from 1,460 to 407 lines (72% reduction)
- Optimized PM_INSTRUCTIONS.md: 510 → 121 lines (76% reduction)
- Optimized BASE_PM.md: 481 → 111 lines (77% reduction)
- Optimized WORKFLOW.md: 397 → 103 lines (74% reduction)
- Eliminated redundancy while preserving all critical functionality
- Enhanced clarity with measurable, testable rules
- Removed emotional language in favor of clear directives
- Consolidated duplicate content across files

### Improved
- PM instruction clarity and enforceability
- Reduced cognitive load for PM operations
- Better structured delegation rules
- Cleaner workflow definitions

## [4.2.52] - 2025-09-18

### Changed
- Pre-optimization checkpoint before PM instruction refactoring
- Preparing for significant reduction in instruction verbosity

## [4.2.51] - 2025-09-17

### Changed
- Cleaned up project root documentation and organized test artifacts
- Moved 23 test/implementation documentation files from root to /tmp/
- Removed 2 test artifacts from project root
- Organized documentation structure for better maintainability
- Preserved all essential project files in root directory

## [4.2.50] - 2025-09-16

### Fixed
- Corrected log directory path to use .claude-mpm/logs instead of project root
- Fixed LogManager default path configuration
- Updated MPM_LOG_DIR constant to correct path
- Fixed hardcoded log path in logger.py
- Prevents creation of logs directory in project root

## [4.2.49] - 2024-09-15

### Added
- Enhanced Security agent v2.4.0 with comprehensive attack vector detection
- SQL injection detection with pattern matching and query validation
- Parameter type and format validation framework (email, URL, phone, UUID)
- Detection for XSS, CSRF, XXE, command injection, and path traversal
- LDAP/NoSQL injection and SSRF vulnerability detection
- Authentication/authorization flaw detection (IDOR, JWT, sessions)
- Insecure deserialization and file upload vulnerability checks
- Hardcoded credential and weak cryptography detection

### Changed
- Security agent now maps vulnerabilities to OWASP Top 10 categories
- Added severity ratings and actionable remediation recommendations

## [4.2.48] - 2024-09-15

### Added
- NextJS Engineer agent specialized in Next.js 14+ and TypeScript
- Mandatory web search capabilities for Python, React, and NextJS engineers
- Focus on 2025 best practices with App Router and Server Components

### Changed
- Updated Python Engineer to v1.1.0 with web search mandate
- Updated React Engineer to v1.1.0 with web search mandate
- Enhanced all engineers to proactively search for current best practices

# Changelog

All notable changes to claude-mpm will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Deprecated

### Fixed

### Removed

### Security

## [4.2.47] - 2025-09-14

### Changed
- **Dashboard Consolidation**: Consolidated multiple test and documentation files into organized structure
- **Documentation Guidelines**: Added instructions for temporary files and test outputs to use tmp/ directory

### Fixed
- **Version Consistency**: Fixed version mismatch across package.json and pyproject.toml files

## [4.2.46] - 2025-09-13

### Fixed
- **Dashboard Data Display**: Fixed isFileOperation method to properly validate hook events with pre_tool/post_tool subtypes
- **File Tree Tab**: Implemented refreshFromFileToolTracker method for proper data synchronization with Files tab
- **Tab Isolation**: Resolved issue where multiple tabs appeared active simultaneously
- **Activity Tab**: Fixed CSS issue causing Activity tab text to display vertically
- **Event Processing**: Added notification mechanism in dashboard.js to update CodeViewer when file operations change

### Added
- **Test Event Generator**: Created generate_test_events.py script for dashboard validation and testing
- **Dashboard Static HTML**: Added dashboard.html to static directory for proper serving

## [4.2.45] - 2025-09-13

### Changed
- **PM Testing Mandate**: Strengthened PM instructions to require comprehensive real-world testing
- **API Verification**: Mandated actual HTTP calls to all endpoints with request/response logs
- **Web Testing**: Required browser DevTools console inspection and screenshots for all web pages
- **Database Testing**: Enforced actual query execution with before/after results
- **Deployment Testing**: Required live URL accessibility checks with browser verification
- **QA Standards**: Automatic rejection for "should work" responses - only real test evidence accepted

## [4.2.44] - 2025-09-12

### Changed
- **Browser Logs Infrastructure**: Removed browser logs tab and infrastructure in favor of browser plugin approach
- **PM Instructions**: Strengthened PM instructions with strict no-fallback policy
- **File Tree Navigation**: Fixed navigation highlighting and event handling
- **Dashboard Architecture**: Clean dashboard with only 6 core tabs
- **Error Handling**: Enhanced error handling to prefer exceptions over silent degradation

### Added
- **API Key Validation**: Implemented API key validation on startup
- **Agent Cleanup**: Cleaned up duplicate and test agents

### Removed
- **Browser Logs Tab**: BREAKING CHANGE - Browser Logs tab removed, will be replaced with browser extension
- **Browser Log Infrastructure**: Removed browser console monitoring infrastructure

## [4.2.43] - 2025-09-11

[Unreleased]: https://github.com/bobmatnyc/claude-mpm/compare/v4.2.50...HEAD
[4.2.50]: https://github.com/bobmatnyc/claude-mpm/compare/v4.2.49...v4.2.50
[4.2.49]: https://github.com/bobmatnyc/claude-mpm/compare/v4.2.48...v4.2.49
[4.2.48]: https://github.com/bobmatnyc/claude-mpm/compare/v4.2.47...v4.2.48
[4.2.47]: https://github.com/bobmatnyc/claude-mpm/compare/v4.2.46...v4.2.47

