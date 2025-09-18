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

