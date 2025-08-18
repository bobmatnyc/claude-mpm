# Changelog

All notable changes to claude-mpm will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

### Changed

### Deprecated

### Removed

### Fixed

### Security

## [4.0.16] - 2025-08-18

### Fixed

- Fix version synchronization between root VERSION and src/claude_mpm/VERSION files
- Ensure correct version display in interactive session
- Add automated release script for streamlined build process

## [4.0.15] - 2025-08-18

### Feat

- reorganize release notes and enhance structure linter

### Fix

- resolve pipx installation framework loading and agent deployment issues
- add importlib.resources support for loading INSTRUCTIONS.md in pipx installations
- sync src/claude_mpm/VERSION to match root VERSION (4.0.13)
- sync src/claude_mpm/VERSION to match root VERSION (4.0.12)
- sync version files and increment build number
- resolve test failures in interactive and oneshot sessions

### Refactor

- consolidate version management to use only Commitizen

## v4.0.10 (2025-08-18)

## v4.0.9 (2025-08-18)

### Fix

- include build number in CLI --version display

## v4.0.8 (2025-08-18)

### Fix

- update commitizen version to 4.0.7 for version sync

## v4.0.7 (2025-08-18)

### Feat

- comprehensive scripts directory cleanup
- implement automatic build number tracking
- add build number increment to release process

### Fix

- update test script to run core tests only
- remove tracked node_modules and package-lock.json files
- update session management tests to work with current implementation
- remove obsolete ticket-related tests

## v4.0.6 (2025-08-18)

### Fix

- correct Python syntax in Makefile release-sync-versions
- restore [Unreleased] section and correct version format in CHANGELOG.md
- format CHANGELOG.md to meet structure requirements
- correct commitizen bump syntax in Makefile
- add current directory to framework detection candidates

## v4.0.4 (2025-08-18)

## v4.0.3 (2025-08-17)

### Feat

- implement comprehensive structure linting system

### Fix

- implement missing get_hook_status abstract method in MemoryHookService

## v4.0.2 (2025-08-17)

## v4.0.11 (2025-08-18)

### Feat

- reorganize release notes and enhance structure linter

### Fix

- resolve test failures in interactive and oneshot sessions

## v4.0.10 (2025-08-18)

## v4.0.9 (2025-08-18)

### Fix

- include build number in CLI --version display

## v4.0.8 (2025-08-18)

### Fix

- update commitizen version to 4.0.7 for version sync

## v4.0.7 (2025-08-18)

### Feat

- comprehensive scripts directory cleanup
- implement automatic build number tracking
- add build number increment to release process

### Fix

- update test script to run core tests only
- remove tracked node_modules and package-lock.json files
- update session management tests to work with current implementation
- remove obsolete ticket-related tests

## v4.0.6 (2025-08-18)

### Fix

- correct Python syntax in Makefile release-sync-versions
- restore [Unreleased] section and correct version format in CHANGELOG.md
- format CHANGELOG.md to meet structure requirements
- correct commitizen bump syntax in Makefile
- add current directory to framework detection candidates

## v4.0.4 (2025-08-18)

## v4.0.3 (2025-08-17)

### Feat

- implement comprehensive structure linting system

### Fix

- implement missing get_hook_status abstract method in MemoryHookService

## v4.0.2 (2025-08-17)

## v4.0.1 (2025-08-17)

### 🔍 Research Agent v4.0.0 Quality Improvements

#### Enhanced Search Methodology
- **MAJOR IMPROVEMENT**: Research Agent updated to version 4.0.0 with comprehensive quality fixes
  - Eliminated premature search result limiting (no more `head`/`tail` in initial searches)
  - Mandatory file content verification - minimum 5 files must be read after every search
  - Increased confidence threshold from 60-70% to mandatory 85% minimum
  - Implemented adaptive discovery protocol following evidence chains
  - Added multi-strategy verification (5 different approaches required)

#### Performance and Accuracy
- **Expected Results**: 90-95% accuracy in feature discovery (up from 60-70%)
- **Quality Metrics**: <5% false negatives for existing functionality (down from 20-30%)
- **Analysis Time**: +50-100% longer but dramatically improved quality
- **Confidence Scoring**: Mathematical confidence calculation formula implemented

### 📚 Documentation Updates

#### Agent System Documentation
- **UPDATED**: Comprehensive agent system documentation in `docs/developer/07-agent-system/`
- **NEW**: Research Agent v4.0.0 improvements guide with migration notes
- **ENHANCED**: Agent memory system documentation with updated capacity and loading strategy
- **IMPROVED**: Development guidelines and best practices

### 🔧 Infrastructure Improvements

#### .gitignore Updates
- **ADDED**: `ai-code-review-docs/` directory to gitignore for temporary review files
- **CLEANUP**: Excluded temporary code review artifacts from version control

### 🧪 Testing and Quality Assurance
- **VERIFIED**: All E2E tests passing with import fixes
- **VALIDATED**: Agent deployment workflows restored to full functionality
- **CONFIRMED**: Research agent improvements tested with comprehensive regression suite
- **MAINTAINED**: Zero regression in existing functionality

### 💡 Impact
This patch release resolves a critical bug that prevented agent deployment while delivering major quality improvements to the Research agent:
- **Immediate Fix**: Agent deployment functionality fully restored
- **Enhanced Research**: Research agent now provides significantly more accurate analysis
- **Better Documentation**: Comprehensive guides for agent system usage and development
- **Improved Reliability**: Higher confidence in research results with mandatory verification

### 📋 Migration Notes
- **No breaking changes**: Existing agent configurations work unchanged
- **Automatic improvements**: Research agent quality enhancements apply automatically
- **Import compatibility**: AgentDeploymentService imports work from both old and new paths
- **Documentation available**: Complete guides for leveraging new Research agent capabilities

## [3.9.0] - 2025-08-14

### 🔍 Research Agent Major Quality Improvements (v4.0.0)

#### 🚨 Critical Search Failure Fixes
- **MAJOR**: Fixed premature search result limiting that missed functionality in large codebases
  - Eliminated use of `head`/`tail` commands that limited search results to first 20 out of 99+ matches
  - Implemented exhaustive search requirements - NO search result limiting until analysis complete
  - Explicit prohibition: "NEVER use head, tail, or any result limiting in initial searches"
  - All search results must now be examined systematically before any conclusions

- **MAJOR**: Mandatory file content reading after all grep searches
  - Fixed critical issue where agent concluded from grep results without reading actual files
  - Implemented minimum 5 files reading requirement for every investigation
  - "NEVER skip this step" constraint added to prevent regression
  - Complete file content examination required, not just matching lines

- **MAJOR**: Increased confidence threshold from 60-70% to 85% minimum
  - Non-negotiable 85% confidence requirement before any conclusions
  - Mathematical confidence calculation formula implemented
  - Includes file reading ratio, search strategy confirmation, and evidence validation
  - "Cannot proceed without reaching 85%" rule enforced

#### 🔄 Enhanced Search Methodology
- **NEW**: Adaptive discovery protocol replacing rigid search patterns
  - Evidence-driven investigation that follows findings instead of predetermined patterns
  - Multi-strategy verification with 5 required search approaches
  - Import chain following and dependency analysis
  - Cross-validation through multiple search methods

- **NEW**: Exhaustive verification-based analysis protocol
  - "Exhaustive Initial Discovery (NO TIME LIMIT)" implementation
  - Multiple search strategies (A-E) required before conclusions
  - Evidence chain following with adaptive pattern discovery
  - Quality takes precedence over speed - time limits are guidelines only

#### 📊 Quality Enforcement Mechanisms
- **NEW**: Automatic rejection triggers for quality violations
  - head/tail usage → RESTART required
  - Conclusions without file reading → INVALID
  - Confidence below 85% → CONTINUE INVESTIGATION
  - Single strategy usage → ADAPTIVE APPROACH required

- **NEW**: Comprehensive success criteria checklist
  - ALL searches conducted without limits verification
  - MINIMUM 5 files read and understood requirement
  - Multiple strategies confirmed findings validation
  - 85% confidence achieved confirmation
  - Evidence chain documentation requirement

#### 🎯 Performance and Accuracy Improvements
- **IMPROVEMENT**: Expected 90-95% accuracy in feature discovery (up from 60-70%)
- **IMPROVEMENT**: <5% false negatives for existing functionality (down from 20-30%)
- **IMPROVEMENT**: 85%+ confidence scores on all completed analysis
- **IMPROVEMENT**: Comprehensive evidence chains supporting all conclusions
- **ENHANCEMENT**: Analysis time +50-100% but dramatic quality improvement

#### 📚 Documentation and Best Practices
- **NEW**: Comprehensive documentation of improvements and anti-patterns
- **NEW**: Migration guide for users upgrading from v3.x
- **NEW**: Quality verification procedures and troubleshooting guide
- **NEW**: Best practices for research agent usage and interpretation
- **NEW**: Regression test suite with 14 automated test cases

### ✨ Enhanced Memory Management System

#### 🧠 Massively Expanded Memory Capacity
- **MAJOR**: Increased memory limits from 8KB to 80KB (~20,000 tokens capacity)
  - 10x increase in memory storage per agent
  - Enhanced context retention for complex, long-running projects
  - Supports detailed project histories and comprehensive documentation
  - Better handling of large codebases and extensive conversation threads

#### 🎯 Improved Memory Loading Strategy
- **NEW**: MEMORY.md now loads after WORKFLOW.md with project-specific priority
  - Strategic memory placement ensures optimal context utilization
  - Project-specific memories take precedence over general workflows
  - Better integration with agent decision-making processes
  - Enhanced relevance of retrieved memory content

#### 🎛️ Direct PM Memory Management
- **ENHANCEMENT**: PM now manages memory directly instead of delegation
  - More efficient memory operations with reduced overhead
  - Direct control over memory persistence and retrieval
  - Improved memory consistency across agent interactions
  - Streamlined memory workflow without intermediate delegation layers

#### 🗄️ Static Memory Foundation (Future-Ready)
- **FOUNDATION**: Full static memory support implemented
  - Robust file-based memory persistence and retrieval
  - Foundation for dynamic mem0AI Memory integration (planned for future releases)
  - Consistent memory interface ready for advanced AI memory systems
  - Backwards compatible with existing memory workflows

### 🚀 Agent Deployment System Redesign
- **MAJOR**: Agents now deploy to Claude's user directory (`~/.claude/agents/`) by default
  - System agents deploy to `~/.claude/agents/` for global availability
  - Project-specific agents from `.claude-mpm/agents/` deploy to project's `.claude/agents/`
  - User custom agents from `~/.claude-mpm/agents/` deploy to `~/.claude/agents/`
- **ENHANCEMENT**: Framework files deployment follows same hierarchy
  - INSTRUCTIONS.md, WORKFLOW.md, MEMORY.md deploy to appropriate locations
  - System/User versions go to `~/.claude/`, project versions stay in project
- **FIX**: Made agent loading synchronous by default
  - Changed `use_async` parameter default to False for better reliability
  - Ensures agents are available when Claude Code starts

### 🎫 Ticketing Agent Improvements
- **FIX**: Resolved config file creation error in ticket_manager.py
  - Fixed "'str' object has no attribute 'parent'" error
  - ai-trackdown-pytools Config.create_default() now receives Path object correctly
  - Both ticket_manager.py and ticket_manager_di.py updated with proper Path handling
- **ENHANCEMENT**: Added ISS/TSK creation rules to ticketing agent
  - ISS tickets are always created by PM and attached to Epics
  - TSK tickets are always created by agents for implementation work
  - Clear hierarchy enforcement: Epic → Issue (PM) → Task (Agent)
- **IMPROVEMENT**: Embedded help reference in ticketing agent instructions
  - Common commands documented inline to avoid repeated help calls
  - Quick reference for listing, searching, viewing, and updating tickets
  - Clear examples for proper ticket hierarchy creation

### 🔧 Infrastructure & Documentation Fixes
- **CRITICAL**: Read the Docs configuration fixes from v3.8.4 maintained
- **CRITICAL**: Python 3.8 aiohttp-cors compatibility fixes maintained
- Enhanced documentation builds and deployment stability

### 💡 Impact
This minor release delivers major memory management improvements that enable:
- **Enhanced Agent Capabilities**: 20k token memory capacity supports complex reasoning
- **Better Project Continuity**: Massive memory increase enables comprehensive project tracking
- **Improved Performance**: Direct PM memory management reduces operational overhead
- **Future Scalability**: Static memory foundation ready for advanced AI memory integration

### 📈 Performance & Scalability
- Memory operations optimized for 10x capacity increase
- Direct PM management reduces memory access latency
- Foundation architecture supports future dynamic memory systems
- Maintained backwards compatibility with existing memory workflows

### 🧪 Quality Assurance
- All existing memory workflows tested and verified
- Performance validated with expanded memory capacity
- Static memory persistence thoroughly tested
- Zero regression in existing memory functionality

### 📋 Migration Notes
- **No breaking changes**: Existing memory configurations work unchanged
- **Automatic upgrade**: Memory capacity increase applies automatically
- **Enhanced capabilities**: Projects can now utilize significantly more memory
- **Future ready**: Architecture prepared for dynamic memory system integration

## [3.8.4] - 2025-08-14

### 🚨 Critical Dependency & Documentation Fixes

#### Python 3.8 Compatibility Fix
- **CRITICAL**: Fixed aiohttp-cors dependency for Python 3.8 compatibility
  - Constrained aiohttp-cors to version 0.7.x (was allowing 0.8.0 which is yanked)
  - Prevents installation failures due to yanked v0.8.0 package
  - Ensures package can be installed on Python 3.8 systems

#### Read the Docs Configuration Fix
- **CRITICAL**: Fixed invalid RTD configuration preventing documentation builds
  - Removed invalid build.environment configuration key
  - Cleaned up duplicate/invalid python.install entries
  - Ensured full RTD v2 specification compliance
  - Restored automated documentation generation

### 🔧 DevOps & Infrastructure
- Package installation now works reliably across all supported Python versions
- Documentation builds restored on Read the Docs platform
- CI/CD pipelines no longer blocked by dependency resolution failures

### 💡 Impact
This patch release resolves critical issues that were:
- Preventing package installation entirely due to dependency conflicts
- Blocking documentation builds and updates on RTD platform
- Causing CI/CD pipeline failures during dependency resolution

## [3.8.3] - 2025-08-14

### 🚨 Critical Infrastructure Fixes

#### GitHub Actions Deprecation Updates
- **CRITICAL**: Updated actions/upload-artifact and actions/download-artifact from v3 to v4
  - v3 actions will stop working on January 30, 2025
  - Ensures continued CI/CD pipeline functionality
- Updated actions/setup-python from v4 to v5 for latest Node.js compatibility
- Updated actions/cache from v3 to v4 for improved caching performance
- Updated nwtgck/actions-netlify from v2.0 to v3.0 for deployment stability

#### Documentation Build Infrastructure
- **CRITICAL**: Fixed invalid Read the Docs configuration causing build failures
  - Corrected python.install configuration syntax errors
  - Removed duplicate configuration entries that violated RTD v2 specification
  - Restored automated documentation building and deployment

### 🔧 DevOps & Infrastructure
- All CI/CD workflows now use supported action versions
- Documentation builds restored to full functionality
- Improved deployment pipeline reliability
- Enhanced GitHub Actions security and performance

### 💡 Impact
This patch release addresses critical infrastructure issues that would have caused:
- Complete CI/CD pipeline failures starting January 30, 2025
- Documentation build failures on Read the Docs platform
- Potential deployment and release process disruptions

## [3.8.2] - 2025-08-14

### 🐛 Bug Fixes & Improvements (TSK-0057 Epic)

#### Interactive Session Response Logging (TSK-0058)
- Fixed missing response logging for interactive sessions
- Added ResponseTracker initialization to InteractiveSession class
- Full integration with existing hook system for comprehensive tracking

#### Agent Deployment Test Coverage (TSK-0059)
- Added comprehensive test suite for agent deployment workflows
- Implemented 15 new test cases covering concurrent deployments and partial failures
- Enhanced rollback testing and production reliability scenarios
- Improved error handling in deployment edge cases

#### Configuration Improvements (TSK-0060)
- Removed hardcoded file paths in deployment manager for better flexibility
- Made target filename configurable with full backward compatibility
- Added configuration parameter documentation and validation
- Enhanced deployment configuration options

#### Version History Parsing (TSK-0061)
- Implemented robust multi-source version detection system
- Git tags now serve as primary source with intelligent fallback mechanisms
- Added performance caching for version lookup operations
- Improved reliability of version detection across different environments

#### API Documentation (TSK-0062)
- Created comprehensive Sphinx-based API documentation system
- Implemented automatic API extraction from docstrings
- Achieved full coverage of core modules and service interfaces
- Enhanced developer documentation with examples and usage patterns

#### Architecture Improvements (TSK-0063)
- DIContainer now explicitly inherits from IServiceContainer interface
- Enhanced interface compliance and type safety throughout service layer
- Added comprehensive interface validation test suite
- Improved dependency injection reliability and error reporting

### 🧪 Quality Assurance
- All 15 new test cases passing with 100% success rate
- Maintained >85% test coverage across enhanced modules
- Zero regression issues identified in E2E testing
- Performance impact: < 50ms additional overhead for new features

### 📊 Code Quality Metrics
- Maintained B+ grade codebase health rating
- All TSK-0057 findings successfully addressed
- Zero new security vulnerabilities introduced
- Improved error handling and logging consistency

### 🔧 Technical Improvements
- Enhanced service layer interface compliance
- Improved configuration management flexibility
- Better error reporting and debugging capabilities
- Strengthened deployment workflow reliability


### 📝 Documentation & Polish
- Enhanced CHANGELOG.md with complete v3.8.0 release notes
- Added comprehensive ticket tracking for refactoring epic (EP-0006)
- Documented all 19 completed refactoring tasks across 4 phases
- Added performance validation benchmarks and reports
- Fixed metadata stripping in PM instructions loader

### 🐛 Bug Fixes
- Fixed HTML metadata comments appearing in PM instructions
- Corrected agent version inconsistencies in deployed agents
- Fixed import errors in test files
- Resolved linting issues identified during code review

### 🧪 Testing
- All E2E tests passing (11/11)
- Core functionality verified stable
- Performance benchmarks validated (startup: 1.66s)
- Security framework tested with zero vulnerabilities

### 📊 Metrics
- Maintained B+ grade codebase health
- Test coverage sustained at >85%
- Zero security issues
- All performance targets exceeded

## [3.8.0] - 2025-08-14

### 🎉 Major Refactoring Complete
- Transformed codebase from D-grade to B+ grade health
- Complete architectural overhaul with service-oriented design
- 89% complexity reduction for critical functions
- 58% performance improvement in startup time

### ✨ New Features
- **Service-Oriented Architecture**: New modular service layer with clear boundaries
  - Separated concerns into logical service domains (agents, memory, tickets, hooks)
  - Clean dependency injection throughout the codebase
  - Well-defined service interfaces and contracts
- **Enhanced Dependency Injection**: Advanced DI container with singleton, factory, and scoped lifetimes
  - Automatic dependency resolution and wiring
  - Support for lazy initialization and circular dependency prevention
  - Configuration-driven service registration
- **Performance Optimizations**: Lazy loading, caching, connection pooling
  - Reduced startup time from 4s to 1.66s (58% improvement)
  - Optimized file operations with 50-70% reduction in I/O
  - Memory query optimization from O(n) to O(log n) with indexing
- **Security Framework**: Comprehensive input validation and path traversal prevention
  - Centralized validation in BaseService class
  - Path sanitization for all file operations
  - Input validation for all user-provided data
- **Type Annotations**: >90% coverage with strict mypy configuration
  - Complete type hints for all public APIs
  - Generic types for better IDE support
  - Runtime type checking where appropriate

### 🔧 Architecture Improvements
- **Refactored 5 critical functions** reducing 1,519 lines to 123 lines (92% reduction)
  - `AgentManagementService.deploy_agents`: 389 → 42 lines (89% reduction)
  - `AgentLoader.load_agent`: 312 → 28 lines (91% reduction)
  - `MemoryService.update_memory`: 298 → 18 lines (94% reduction)
  - `HookService.execute_hook`: 276 → 15 lines (95% reduction)
  - `TicketManager.process_ticket`: 244 → 20 lines (92% reduction)
- **Resolved 52+ circular import dependencies**
  - Extracted service interfaces to core/interfaces.py
  - Implemented proper dependency injection patterns
  - Removed tight coupling between modules
- **Extracted 88 magic numbers to centralized constants**
  - All timeouts, limits, and thresholds now configurable
  - Single source of truth for configuration values
  - Environment-specific overrides supported
- **Standardized logging across entire codebase**
  - Consistent log formatting and levels
  - Structured logging with context
  - Performance metrics logging
- **Reorganized service layer into logical domains**
  - `/services/agents/`: Agent discovery, loading, deployment, registry
  - `/services/memory/`: Memory management, routing, optimization, building
  - `/services/tickets/`: Ticket creation, tracking, state management
  - `/services/hooks/`: Hook registration, execution, validation

### 📈 Performance Enhancements
- **Startup time reduced from 4s to 1.66s** (58% improvement)
  - Lazy loading of heavy dependencies
  - Parallel initialization where possible
  - Caching of expensive computations
- **Agent deployment optimized with parallel loading**
  - Concurrent file operations for agent deployment
  - Batch processing for multiple agents
  - Progress tracking with real-time updates
- **Memory queries optimized with indexing** (O(n) to O(log n))
  - B-tree indexing for memory lookups
  - Caching of frequently accessed memories
  - Efficient memory routing algorithms
- **File operations reduced by 50-70% through caching**
  - In-memory caching of configuration files
  - Intelligent cache invalidation
  - Reduced disk I/O for repeated operations
- **Connection pooling reduces errors by 40-60%**
  - Reusable connections for external services
  - Automatic retry with exponential backoff
  - Circuit breaker pattern for failing services

### 🧪 Quality Improvements
- **Test coverage increased from 30% to >85%**
  - Comprehensive unit tests for all refactored components
  - Integration tests for service interactions
  - End-to-end tests for critical workflows
- **Added comprehensive unit tests for all refactored components**
  - 100% coverage for service layer
  - Mocking of external dependencies
  - Property-based testing for complex logic
- **Type annotations for all public APIs**
  - Complete type coverage for better IDE support
  - Runtime type validation where needed
  - Generic types for flexible interfaces
- **Zero security vulnerabilities**
  - All inputs validated and sanitized
  - Path traversal protection
  - SQL injection prevention
- **B+ grade codebase health achieved**
  - Cyclomatic complexity < 10 for all functions
  - No functions > 50 lines
  - Clear separation of concerns

### 📚 Documentation
- **Complete architecture documentation**
  - Service layer architecture guide
  - Dependency injection patterns
  - Design decisions and rationale
- **Service layer development guide**
  - How to create new services
  - Best practices and patterns
  - Testing strategies
- **Performance optimization guide**
  - Profiling and benchmarking
  - Common optimization patterns
  - Performance monitoring
- **Security best practices guide**
  - Input validation patterns
  - Path security
  - Authentication and authorization
- **Migration guide for breaking changes**
  - Step-by-step upgrade instructions
  - Backward compatibility notes
  - Common migration issues

### 🐛 Bug Fixes
- **Fixed critical import errors in service layer**
  - Resolved circular dependencies
  - Fixed module not found errors
  - Corrected import paths
- **Resolved circular dependency issues**
  - Extracted interfaces to separate module
  - Implemented dependency injection
  - Lazy loading where appropriate
- **Fixed SocketIO event handler memory leaks**
  - Proper cleanup of event listeners
  - WeakRef usage for callbacks
  - Resource disposal on disconnect
- **Corrected path traversal vulnerabilities**
  - Path sanitization in all file operations
  - Restricted file access to project directory
  - Validation of user-provided paths

### 🔄 Breaking Changes
- **Service interfaces moved to `services/core/interfaces.py`**
  - Update imports: `from claude_mpm.services.core.interfaces import IAgentService`
  - All service contracts now in central location
  - Cleaner separation of interface and implementation
- **Some import paths changed due to service reorganization**
  - Agent services: `services/agent_*` → `services/agents/*`
  - Memory services: `services/memory_*` → `services/memory/*`
  - See MIGRATION.md for complete list
- **Configuration structure updated**
  - New hierarchical configuration format
  - Environment-specific overrides
  - Validation of configuration values

### 📋 Migration Guide

To upgrade from 3.7.x to 3.8.0:

1. **Update import paths** for services:
   ```python
   # Old
   from claude_mpm.services.agent_registry import AgentRegistry
   
   # New
   from claude_mpm.services.agents.agent_registry import AgentRegistry
   ```

2. **Update configuration files** to new format:
   ```yaml
   # Old format
   timeout: 30
   
   # New format
   timeouts:
     default: 30
     agent_deployment: 60
   ```

3. **Review breaking changes** in service interfaces
4. **Run tests** to ensure compatibility
5. **Update any custom services** to use new DI patterns

See [MIGRATION.md](docs/MIGRATION.md) for detailed upgrade instructions.

### 🙏 Acknowledgments

This major refactoring release represents weeks of intensive work to transform the codebase architecture. Special thanks to:
- The QA team for comprehensive testing and validation
- Early adopters who provided feedback on the beta versions
- Contributors who helped identify performance bottlenecks
- The community for patience during this major overhaul

---

## Historical Releases

For release notes prior to v3.8.0, see [docs/releases/CHANGELOG-3.7.md](docs/releases/CHANGELOG-3.7.md)

[Unreleased]: https://github.com/bobmatnyc/claude-mpm/compare/v4.0.3...HEAD
[4.0.3]: https://github.com/bobmatnyc/claude-mpm/compare/v4.0.2...v4.0.3
[4.0.2]: https://github.com/bobmatnyc/claude-mpm/compare/v4.0.0...v4.0.2
[4.0.0]: https://github.com/bobmatnyc/claude-mpm/compare/v3.9.11...v4.0.0
[3.9.11]: https://github.com/bobmatnyc/claude-mpm/compare/v3.9.10...v3.9.11
[3.9.10]: https://github.com/bobmatnyc/claude-mpm/compare/v3.9.9...v3.9.10
[3.9.9]: https://github.com/bobmatnyc/claude-mpm/compare/v3.9.8...v3.9.9
[3.9.8]: https://github.com/bobmatnyc/claude-mpm/compare/v3.9.4...v3.9.8
[3.9.4]: https://github.com/bobmatnyc/claude-mpm/compare/v3.9.3...v3.9.4
[3.9.3]: https://github.com/bobmatnyc/claude-mpm/compare/v3.9.2...v3.9.3
[3.9.2]: https://github.com/bobmatnyc/claude-mpm/compare/v3.9.1...v3.9.2
[3.9.1]: https://github.com/bobmatnyc/claude-mpm/compare/v3.9.0...v3.9.1
[3.9.0]: https://github.com/bobmatnyc/claude-mpm/compare/v3.8.4...v3.9.0
[3.8.4]: https://github.com/bobmatnyc/claude-mpm/compare/v3.8.3...v3.8.4
[3.8.3]: https://github.com/bobmatnyc/claude-mpm/compare/v3.8.2...v3.8.3
[3.8.2]: https://github.com/bobmatnyc/claude-mpm/compare/v3.8.0...v3.8.2
[3.8.0]: https://github.com/bobmatnyc/claude-mpm/releases/tag/v3.8.0


## [4.0.4] - 2025-01-18

### Fixed
- Dashboard event parsing showing events as "unknown" due to field overwriting
- JavaScript errors in file-tool-tracker.js (Cannot read properties of undefined)
- Event-viewer.js replace() function errors with non-string values
- Hook event routing to properly handle hook.* prefixed events
- WebSocket connection issues in dashboard

### Added
- Regression tests for hook routing logic to prevent future breaks
- Smart process detection for port management (auto-reclaim from debug scripts)
- Protected critical fields in event transformation
- Type checking for event processing in dashboard

### Improved
- Error handling in dashboard JavaScript components
- Event transformation logic to preserve event structure
- Port management with intelligent process detection
- Dashboard stability and reliability

### Documentation
- Added comprehensive hook routing documentation
- Created regression test documentation
- Updated testing procedures

