## [Unreleased]

### Added
- **Local Process Management System**: Professional-grade process management for local development deployments
  - **Phase 1**: Core process management with LocalProcessManager and StateManager
    - Background process spawning with process group isolation (PGID)
    - Port conflict prevention with auto-find alternative port
    - State persistence to JSON files in `.claude-mpm/local-ops-state/`
    - Graceful shutdown with configurable timeout (SIGTERM → SIGKILL)
  - **Phase 2**: Health monitoring system with three-tier checks
    - HTTPHealthCheck: Endpoint availability, response time, status code validation
    - ProcessHealthCheck: Process existence, zombie detection, responsiveness
    - ResourceHealthCheck: CPU, memory, file descriptors, threads, connections
    - Background monitoring thread with configurable interval (default: 30s)
    - Historical health data storage (last 100 checks per deployment)
  - **Phase 3**: Auto-restart system with intelligent crash recovery
    - Exponential backoff policy (configurable: 2s → 300s with 2x multiplier)
    - Circuit breaker pattern (default: 3 failures in 5 minutes → open for 10 minutes)
    - Restart history tracking with success/failure counts
    - Crash detection via health checks and process monitoring
  - **Phase 4**: Stability enhancements for preemptive issue detection
    - Memory leak detector with linear regression analysis (threshold: 10 MB/min growth)
    - Log pattern monitor with configurable error patterns and regex support
    - Resource exhaustion monitor (FD threshold: 80%, thread limit: 1000)
  - **Phase 5**: Unified integration and CLI commands
    - UnifiedLocalOpsManager coordinating all components (556 LOC)
    - 10 CLI subcommands under `local-deploy` command (638 LOC):
      - `start`: Start deployment with auto-restart and monitoring
      - `stop`: Graceful or force shutdown
      - `restart`: Restart with same configuration
      - `status`: Comprehensive deployment status (process, health, restart history)
      - `health`: Health check results across all tiers
      - `list`: List all deployments with filtering by status
      - `monitor`: Live monitoring dashboard with real-time updates
      - `history`: Restart history and circuit breaker state
      - `enable-auto-restart`: Enable crash recovery
      - `disable-auto-restart`: Disable crash recovery
    - YAML configuration support (`.claude-mpm/local-ops-config.yaml`)
    - Rich terminal output with panels, tables, and live updates
- **Comprehensive Documentation**: Three comprehensive documentation files (~30,000 words total)
  - User guide: `docs/user/03-features/local-process-management.md` (650+ lines)
    - Quick start examples for Next.js, Django, multiple microservices
    - Feature documentation for all capabilities
    - Configuration guide with YAML schema
    - Troubleshooting section for common issues
    - Best practices for development workflow
  - Developer guide: `docs/developer/LOCAL_PROCESS_MANAGEMENT.md` (870+ lines)
    - Complete architecture overview with ASCII diagrams
    - Five-phase implementation details
    - Service layer API documentation
    - Extension points for custom health checks and restart policies
    - Testing strategy and performance considerations
  - CLI reference: `docs/reference/LOCAL_OPS_COMMANDS.md` (1,100+ lines)
    - Complete command reference for all 10 subcommands
    - Configuration file schema with all options
    - Return codes and error handling
    - 20+ practical examples and workflows
  - Updated main documentation hub (`docs/README.md`) with Local Operations section

### Changed
- **Documentation Index**: Added Local Operations section to main documentation hub
  - New section in "By Topic" navigation
  - Added to AI Agent Quick Reference with deployment commands
  - Updated Key Features with Local Process Management capabilities

### Fixed
- **FileLock Deadlock**: Resolved deadlock in DeploymentStateManager causing state persistence issues
- **Test Suite Stability**: Fixed 16 failing tests across health manager, log monitor, and state manager

## [4.13.2] - 2025-10-22

### Added
- **Enhanced Help Documentation**: Comprehensive auto-configuration documentation (~1,000 lines)
  - Enhanced `/mpm-help` command with auto-configuration section (+159 lines)
  - Enhanced `/mpm-agents` command with new subcommands (+73 lines)
  - Created `/mpm-auto-configure` documentation (217 lines)
  - Created `/mpm-agents-detect` documentation (168 lines)
  - Created `/mpm-agents-recommend` documentation (214 lines)
  - Updated PM_INSTRUCTIONS.md with proactive suggestion patterns (+66 lines)

### Changed
- **PM Behavior**: PM now proactively suggests auto-configuration in appropriate contexts
  - Suggests to new users without deployed agents
  - Suggests when few agents are deployed
  - Suggests when user asks about agent selection
  - Suggests when project stack changes are detected

## [4.13.1] - 2025-10-21

### Fixed
- **CLI Critical Bug Fixes**: Resolved multiple issues preventing CLI from loading in v4.13.0
  - Removed duplicate --dry-run argument definition causing argparse crash
  - Fixed auto-configure command registration in claude-mpm script
  - Fixed AgentRecommenderService initialization (removed incorrect parameter)
  - Fixed preview_configuration calls to use Path objects instead of strings
  - Fixed async workflow in auto_configure command to use asyncio.run()

## [4.13.0] - 2025-10-21

### Added
- **Auto-Configuration Feature (Complete)**: Five-phase implementation for automatic agent configuration
  - **Phase 1**: Interfaces and data models (IToolchainAnalyzer, IAgentRecommender, IAutoConfigManager)
  - **Phase 2**: Toolchain detection with Strategy pattern (Python, Node.js, Rust, Go)
  - **Phase 3**: Agent recommendation engine with confidence scoring and multi-factor analysis
  - **Phase 4**: Auto-configuration orchestration with Observer pattern for deployment tracking
  - **Phase 5**: CLI integration with Rich progress display and JSON output support
  - 207 comprehensive tests with 76% code coverage
  - Support for 4 languages, 10+ frameworks, and 5+ deployment targets
  - Three CLI commands: `auto-configure`, `agents detect`, `agents recommend`
  - Preview mode for safe exploration before deployment
  - Configuration persistence with rollback capability
  - Confidence-based recommendations (default 80%+ threshold)
- **Comprehensive Documentation**: User and developer documentation for auto-configuration
  - User guide: `/docs/user/03-features/auto-configuration.md` with examples and troubleshooting
  - Developer guide: `/docs/developer/AUTO_CONFIGURATION.md` with architecture and extension patterns
  - Updated quick start guide with auto-configuration workflow
  - Updated documentation index with auto-configuration references

### Changed

### Fixed

### Removed

### Deprecated

### Security

## [4.12.5] - 2025-10-21

### Added
- **Auto-Configuration Feature (Phases 1-2)**: Foundation for intelligent project analysis and agent recommendations
  - Phase 1: Created interfaces (IToolchainAnalyzer, IAgentRecommender, IAutoConfigManager) and 13 data models
  - Phase 2: Implemented Strategy pattern for language detection with 4 detection strategies (Node.js, Python, Rust, Go)
  - ToolchainAnalyzerService with 5-minute caching and framework detection for 10+ frameworks
  - 108 new tests with 100% pass rate (~3,400 lines of production code)
  - Achieved >90% language detection and ~95% framework detection accuracy

## [4.12.4] - 2025-10-21

### Fixed
- Resolved race condition in log directory creation during parallel test execution

## [4.12.3] - 2025-10-21

### Changed
- **PM Instructions Modularization (Phase 2)**: Completed comprehensive refactoring of PM_INSTRUCTIONS.md
  - Extracted validation templates, circuit breakers, and PM examples to separate template files
  - Consolidated git file tracking protocol into dedicated template
  - Extracted PM red flags and response format specifications
  - Added comprehensive template ecosystem with README documentation
  - Improved maintainability and modularity of PM instruction system

## [4.12.2] - 2025-10-20

### Added
- **Mandatory Git File Tracking Protocol**: PM now enforces file tracking for all agent-created files
  - Circuit Breaker #5 prevents session completion without tracking new files
  - PM must verify all new files are tracked in git (cannot delegate this responsibility)
  - Comprehensive tracking decision matrix for different file types and locations
  - Enhanced PM mantra: "delegate, verify, and track files"
  - New scorecard metrics for file tracking compliance

### Changed
- **PM Instructions v0006**: Updated base PM instructions with file tracking enforcement
  - File tracking verification checklist (7 steps) integrated into PM workflow
  - Pre-action checklist enhanced with file tracking questions
  - Bash tool permissions expanded to allow git operations for file tracking
  - JSON response format now includes file_tracking section
  - Red flags updated to catch common file tracking violations

## [4.12.1] - 2025-10-20

### Added
- Patch release for improved stability

## [4.12.0] - 2025-10-20

### Added
- **Java Engineer Agent**: Added 8th specialized coding agent with comprehensive Java ecosystem support
  - Modern Java (21+) development patterns and best practices
  - Enterprise framework expertise (Spring Boot, Jakarta EE, Quarkus)
  - Build tool integration (Maven, Gradle) with dependency management
  - Testing frameworks (JUnit 5, TestNG, Mockito, AssertJ)
  - Performance optimization and memory management
  - Cloud-native patterns and microservices architecture
  - Comprehensive benchmark suite with 175 automated tests

## [4.11.2] - 2025-10-20

### Added
- **Adaptive context window for `/mpm-init context`**: Automatically expands time window to ensure meaningful context
  - High-velocity projects: Uses specified time window (e.g., 7 days)
  - Low-velocity projects: Automatically expands to get at least 25 commits
  - Clear notification when window expands for user transparency
  - Works for both active and dormant projects to provide meaningful analysis

## [4.11.1] - 2025-10-19

### Fixed
- Replaced broken session state storage with intelligent git-based context reconstruction
  - Removed SessionPauseManager and SessionResumeManager
  - Removed session state JSON files and Claude Code-style session restore
  - Added git-based context analysis via Research agent delegation
  - Renamed `resume` command to `context` (backward compatible alias maintained)
  - Intelligent analysis of commit history, work streams, risks, and recommendations

## [4.11.0] - 2025-10-19

### Added
- **Session Pause and Resume**: Save and restore complete session state across Claude sessions
  - `claude-mpm mpm-init pause`: Capture conversation context, git state, and todos
  - `claude-mpm mpm-init resume`: Restore session with automatic change detection
  - Session storage in `.claude-mpm/sessions/pause/` with secure permissions (0600)
  - Change detection: Shows commits, file modifications, and conflicts since pause
  - Optional git commit creation with session information (use `--no-commit` to skip)
  - Support for session summaries, accomplishments, and next steps
  - List available sessions with `--list` flag
  - Resume specific sessions with `--session-id` parameter
  - Atomic file operations with integrity checksums

## [4.10.0] - 2025-10-19

### Added
- KuzuMemoryService now registered as built-in MCP Gateway tool
- **Interactive auto-install for mcp-vector-search**: On first use, users can choose pip/pipx installation or skip
  - Interactive prompt with 3 clear options: pip, pipx, or fallback to grep/glob
  - 120-second timeout protection for pip/pipx installation commands
  - Graceful error handling with informative messages for all failure modes
  - Non-blocking first-use experience (EOFError/KeyboardInterrupt safe)
- **MCPVectorSearchService registered as conditional built-in MCP Gateway tool**: Available when installed
- **Enhanced search command with graceful fallback**: Falls back to grep/glob when mcp-vector-search unavailable
  - Search command detects missing service and offers installation
  - Fallback suggestions provided (e.g., `grep -r 'pattern' .`)
  - All core functionality continues without vector search

### Changed
- Move kuzu-memory from optional to required dependency for seamless memory integration
- kuzu-memory now always installed with Claude MPM (no longer in optional [mcp] extras)
- Simplified installation instructions - kuzu-memory included out of the box
- **Research agent template now adapts to available tools**: Uses vector search when available, grep/glob otherwise
  - Checks for mcp-vector-search availability before recommending search method
  - Seamless workflow whether vector search is installed or not
  - No error messages when using fallback methods
- **Improved user experience for optional MCP services installation**: Interactive prompts, clear choices
  - User-friendly installation options with explanations
  - Non-disruptive fallback behavior when installation skipped
  - Better error messages and recovery suggestions

## [4.8.6] - 2025-10-18

### Fixed
- Move ClickUp API credentials to environment variables for improved security

## [4.8.5] - 2025-10-18

### Added
- **Python Engineer v2.2.1**: AsyncWorkerPool with retry logic and exponential backoff
  - Enhanced error recovery patterns for async operations
  - Expected improvement: 91.7% → 100% pass rate on async tests
- **Next.js Engineer v2.1.0**: Advanced rendering patterns
  - Pattern 3: Complete PPR (Partial Prerendering) implementation
  - Pattern 6 (NEW): Parallel data fetching with Promise.all()
  - Pattern 4: Enhanced Suspense boundaries
  - Expected improvement: 75% → 91.7-100% pass rate
- **Git Commit Protocol**: All 35 agents now follow standardized commit practices
  - Pre-modification file history review with `git log -p`
  - WHAT + WHY commit message format
  - 100% agent coverage (35/35 agents)
- **Context Management Protocol**: PM proactive monitoring
  - 90% threshold: Warning with actionable recommendations
  - 95% threshold: Urgent restart required notice
  - Prevents token limit crashes during complex workflows

### Changed
- Git commit guidelines coverage: 1/35 → 35/35 agents (100%)

## [4.8.4] - 2025-10-18

### Changed
- **Python Engineer v2.2.0**: Dramatic pass rate improvement (+33.4%)
  - Fixed async test case definitions in lightweight benchmark
  - Enhanced sliding window and BFS algorithm patterns
  - Pass rate: 58.3% → 91.7% (11/12 tests)
  - Deployed via production benchmark validation

## [4.8.3] - 2025-10-18

### Added
- **Production Benchmark System**: Real agent execution with multi-dimensional scoring
  - Agent invocation via claude-mpm CLI
  - Safe code execution in isolated subprocesses
  - 4-dimensional evaluation (correctness, idiomaticity, performance, best practices)
  - Comprehensive documentation and test scripts
- **Automatic Failure-Learning System**: Learn from mistakes automatically
  - Detects task failures from tool outputs (Bash, NotebookEdit, Task)
  - Matches fixes with previous failures
  - Extracts and persists learnings to agent memories
  - Smart routing to appropriate agents (PM, engineer, QA)
  - 54/54 tests passing, QA approved
- **Product Owner Agent v1.0.0**: Modern product management specialist
  - RICE prioritization, continuous discovery, OKRs
  - Evidence-based decision framework
  - Complete artifact templates (PRDs, user stories, roadmaps)
  - Product-led growth strategies
  - 2025 best practices (Teresa Torres, Jobs-to-be-Done)
- **Lightweight Benchmark Suite**: Efficient 84-test agent evaluation
  - 66% cost reduction vs full suite (175 tests)
  - 85-90% statistical confidence maintained
  - Multi-dimensional scoring system
  - Permanent benchmark infrastructure in docs/benchmarks/

### Changed
- **Python Engineer v2.0.0 → v2.1.0**: Enhanced with algorithm and async patterns
  - 4 comprehensive async patterns (gather, worker pools, retry, cancellation)
  - 4 algorithm patterns (sliding window, BFS, binary search, hash maps)
  - 5 new anti-patterns to avoid
  - Algorithm complexity quality standards
  - Enhanced search query templates

### Performance
- **Hook System Optimization**: 91% latency reduction (108ms → 10ms per interaction)
  - Increased git branch cache TTL to 5 minutes (reduces subprocess calls)
  - Implemented thread pool for HTTP fallback (non-blocking network calls)
  - Verified async logging is optimal (queue-based, fire-and-forget)

### Fixed
- Test harness f-string escaping bug in production benchmark runner
- Input format handling in benchmark test execution

## [4.8.2] - 2025-10-17

### Fixed
- Improved log cleanup test to handle empty directory removal correctly
- Enhanced test robustness for log migration scenarios

## [4.8.1] - 2025-10-17

### Added
- Optimized 7 coding agents (Python, TypeScript, Next.js, PHP, Ruby, Go, Rust)
- Deployed 5 agents to production (Python, TS, Next.js, Go, Rust)
- Created 175 comprehensive tests (25 per agent)
- Implemented multi-dimensional evaluation methodology v2.0
- Updated complete documentation

## [4.9.0] - 2025-10-17

### Added
- **NEW**: Golang Engineer v1.0.0 - Go 1.24+ concurrency specialist
  - Goroutines and channels patterns for concurrent systems
  - Clean architecture and hexagonal patterns
  - Context management and cancellation
  - Table-driven tests with race detection
  - Microservices and distributed systems expertise
- **NEW**: Rust Engineer v1.0.0 - Rust 2024 edition expert
  - Ownership, borrowing, and lifetime management
  - Zero-cost abstractions and fearless concurrency
  - WebAssembly compilation and optimization
  - Property-based testing and fuzzing support
  - Systems programming and high-performance applications
- **NEW**: Comprehensive test suite - 175 tests (25 per agent)
  - Multi-dimensional evaluation (correctness, idiomaticity, performance, best practices)
  - Difficulty-based scoring (easy/medium/hard)
  - Statistical confidence methodology (95% target)
  - Paradigm-aware testing respecting language philosophies
- **NEW**: Agent documentation suite
  - Coding Agents Catalog (`docs/reference/CODING_AGENTS.md`)
  - Agent Deployment Log (`docs/reference/AGENT_DEPLOYMENT_LOG.md`)
  - Agent Testing Guide (`docs/developer/AGENT_TESTING.md`)
  - Agent Capabilities Reference (`docs/reference/AGENT_CAPABILITIES.md`)

### Changed
- **UPGRADED**: Python Engineer to v2.0.0
  - Python 3.13+ with JIT compiler optimization
  - Enhanced async/await patterns
  - Improved dependency injection patterns
  - Updated testing methodologies
- **UPGRADED**: TypeScript Engineer to v2.0.0
  - TypeScript 5.6+ with latest features
  - Branded types for domain safety
  - Discriminated unions for type-safe responses
  - Modern build tooling (Vite, Bun, esbuild, SWC)
  - Enhanced Vitest and Playwright integration
- **UPGRADED**: Next.js Engineer to v2.0.0
  - Next.js 15 with App Router
  - Server Components patterns
  - Server Actions for mutations
  - Enhanced SSR/SSG/ISR strategies
  - Improved deployment patterns (Vercel, self-hosted, Docker)
- **UPGRADED**: PHP Engineer to v2.0.0
  - PHP 8.4-8.5 with property hooks and asymmetric visibility
  - Laravel 12+ and Symfony 7+ support
  - DDD/CQRS patterns
  - Enhanced type safety with PHPStan/Psalm
  - Deployment expertise (DigitalOcean App Platform, Docker, K8s)
- **UPGRADED**: Ruby Engineer to v2.0.0
  - Ruby 3.4 with YJIT performance optimization
  - Rails 8 with latest features
  - Service object and PORO patterns
  - Comprehensive RSpec testing strategies
  - Background job patterns (Sidekiq, Good Job)

### Improved
- **Evaluation Methodology v2.0**: Multi-dimensional agent evaluation
  - Correctness: 40% weight
  - Idiomaticity: 25% weight
  - Performance: 20% weight
  - Best Practices: 15% weight
- **Search-First Integration**: All agents use semantic search before implementing
- **Quality Standards**: 95% confidence target for all production agents
- **Anti-Pattern Documentation**: 5+ anti-patterns documented per agent
- **Production Patterns**: 5+ production patterns documented per agent
- **Statistical Confidence**: Sample size and variance-based confidence calculations

### Fixed
- **PHP Engineer Evaluation**: Improved from 60% to 121% with paradigm-aware testing
- **Ruby Engineer Evaluation**: Improved from 40% to 95% with updated methodology

### Documentation
- Complete coding agents catalog with 7 specialized agents
- Deployment procedures and rollback instructions
- Comprehensive testing guide with 175-test infrastructure
- Agent capabilities reference with routing and memory integration
- Statistical confidence methodology documentation

## [4.8.0] - 2025-10-15

### Changed
- **Environment Management Simplification**: Removed Mamba/Conda support in favor of standard Python venv
  - Simplified `./scripts/claude-mpm` to use venv exclusively
  - Updated all documentation to reflect venv-only workflow
  - Improved clarity for new users with standardized setup process
  - Reduces complexity: 855 lines of code removed

### Removed
- **Mamba Support**: Removed Mamba/Conda auto-detection and wrapper scripts
  - Deleted `environment.yml`, `scripts/claude-mpm-mamba`, `scripts/switch-env.sh`
  - Removed `scripts/README_MAMBA.md` and Mamba testing scripts
  - Removed `--use-venv` CLI flag (no longer needed)
  - Users who prefer Mamba can still use it manually (not officially supported)

### Added
- **Content Optimization Agent**: New specialized agent for website content quality
  - Content quality auditing (grammar, readability, structure)
  - SEO optimization (keywords, meta tags, headers)
  - WCAG 2.1/2.2 accessibility compliance checking
  - AI-powered alt text generation using Claude Sonnet vision
  - Integration with MCP browser tools for real-world testing
  - Modern 2025 content tools knowledge (Hemingway, Grammarly principles)

### Migration Guide
For users currently using Mamba:
1. Deactivate Mamba environment: `mamba deactivate`
2. Create Python venv: `python -m venv venv`
3. Activate venv: `source venv/bin/activate` (or `venv\Scripts\activate` on Windows)
4. Install dependencies: `pip install -e .`

### Breaking Changes
- **Mamba auto-detection removed**: `./scripts/claude-mpm` no longer detects or uses Mamba environments
- **--use-venv flag removed**: No longer needed as venv is the only supported method
- **Mamba wrapper scripts removed**: Use standard Python venv workflow instead

## [4.7.11] - 2025-10-12

### Added
- **Self-Upgrade System**: Automatic version checking and upgrade functionality
  - `SelfUpgradeService` detects installation method (pip, pipx, npm, editable)
  - Non-blocking startup version checks with 24-hour cache TTL
  - New `claude-mpm upgrade` command for manual upgrades
  - Support for `-y/--yes` flag for non-interactive upgrades
  - Automatic restart after successful upgrade
  - Installation method auto-detection with appropriate upgrade commands

### Changed
- Startup now includes background version check (non-blocking)
- Added UPGRADE command constant to CLICommands enum

### Technical Details
- New files: `src/claude_mpm/services/self_upgrade_service.py` (346 lines)
- New CLI command: `src/claude_mpm/cli/commands/upgrade.py` (155 lines)
- Integrated `_check_for_updates_async()` in CLI startup sequence
- Leverages existing `PackageVersionChecker` for PyPI/npm queries
- Graceful failure handling - never breaks existing installation

## [4.7.10] - 2025-10-11

### Fixed
- **Memory Isolation**: Enforce project-only memory scope to prevent cross-project contamination
  - Removed user-level memory loading (`~/.claude-mpm/memories/`)
  - Memories now strictly project-scoped (`./.claude-mpm/memories/`)
  - Prevents memory leakage between different projects
  - Aligns with agent deployment behavior (project-level since v4.0.32+)

### Breaking Changes
- **User-level memories no longer loaded**: Projects must have their own memory files
- Migration guide provided in documentation for existing user-level memories

### Documentation
- Added memory migration guide in docs/user/03-features/memory-system.md
- Updated MemoryManager docstrings for v4.7.10+ behavior
- Explained project-only scope benefits and security improvements

## [4.7.9] - 2025-10-10

### Added
- **mpm-init --catchup Mode**: New mode to display recent commit history for PM context
- Last 25 commits from all branches with author attribution and temporal context
- Contributor activity summary showing who did what
- PM recommendations based on commit patterns
- Comprehensive test coverage with 11 tests

### Changed
- Enhanced mpm-init command with catchup functionality for better PM project awareness

## [4.7.8] - 2025-10-09

### Added
- **Multi-Agent Batch Toggle**: Enable/disable multiple agents with single selection (e.g., '1,3,5' or '1-4')
- **Batch Operations**: Bulk enable all ('a') or disable all ('n') agents
- **Batch Save with Preview**: See pending changes (yellow arrows) before committing
- **Save & Launch Feature**: New [l] menu option to save and launch Claude MPM
- **Smart Change Management**: Auto-prompt to save or discard pending agent changes

### Fixed
- **Menu Visibility**: Fixed missing [l] and [q] shortcuts (escaped Rich markup brackets)
- **Text Contrast**: Changed menu descriptions from dim to white for better readability
- **Layout Improvements**: Wider columns for better menu alignment

### Changed
- **Toggle Interface**: Replaced separate [e]/[d] options with unified [t] toggle
- **Bold Shortcuts**: Menu shortcuts now use bold cyan for better visibility

## [4.7.7] - 2025-10-09

### Fixed
- **Configurator Menu Display**: Resolved issue where keyboard shortcuts like [e], [d], [c] were not visible due to Rich markup consuming them
- Applied Text object pattern to 25 shortcuts across 5 menus (Agent Management, Template Editing, Behavior Configuration, MCP Services, Hook Services)
- Improved menu readability and keyboard shortcut visibility
- All menu shortcuts now use Text.append() with style parameter for proper rendering

## [4.7.6] - 2025-10-09

### Fixed
- Enhanced configurator input handling with whitespace stripping and case normalization
- Improved agent table description visibility with bold cyan styling
- Added agent reset to defaults functionality with confirmation
- Better error handling and user confirmation prompts in configurator

## [4.7.5] - 2025-10-08

### Changed
- Reduced code bloat by 505 lines (-21.7%) through refactoring
- Created DisplayHelper utility class with 21 reusable display methods
- Refactored mpm_init.py to eliminate duplicate display logic (52 lines saved)
- Removed unnecessary backup HTML file (713 lines)

### Technical Improvements
- Consolidated 4 display methods in mpm_init.py using new DisplayHelper
- Improved separation of concerns with dedicated display utility
- Better code organization and maintainability
- Zero functionality changes (100% backward compatible)

## [4.7.4] - 2025-10-08

### Added
- Dashboard restoration with all tabs working (Events, Agents, Tools, Files, Activity)
- `/mpm-init --non-interactive` flag for automation support
- `/mpm-init --days` parameter (7, 14, 30, 60, 90 days) for activity report timeframes
- `/mpm-init --export` functionality for generating activity reports
- Comprehensive `/mpm-monitor` documentation (409 lines)
- PROJECT_ORGANIZATION.md standard documentation (930 lines)
- SLASH_COMMAND_STANDARDS.md development guide (1,629 lines)

### Fixed
- Parameter pass-through in mpm-init handler
- Variable shadowing in export functionality
- Git directory detection using CLAUDE_MPM_USER_PWD environment variable
- MyPy untyped import warnings
- Test timing race condition in test_mpm_log_migration.py
- Print statement check now non-blocking in pre-publish quality gate

### Changed
- Removed broken unified hub dashboard
- Removed redundant check_monitor_deps.py script
- Improved slash command consistency (quality score: 5.5→8.5/10)

### Documentation
- Fixed 4 outdated documentation references
- Enhanced documentation cross-referencing
- Improved organization standards

## [4.7.3] - 2025-10-07

### Fixed
- Fixed `/mpm-doctor` slash command to properly execute diagnostic checks
  - Added missing bash code block to invoke `claude-mpm doctor "$@"`
  - Command now correctly runs when invoked via `/mpm-doctor`

## [4.7.2] - 2025-10-06

### Fixed
- Resolved remaining indentation and formatting issues in config_service_base.py
  - Additional cleanup to ensure consistent code formatting
  - Improved code readability and maintainability

### Changed
- Added .kuzu-memory-backups/ directory to .gitignore
  - Prevents accidental commits of Kuzu memory backup files
  - Keeps repository clean from local database backups

### Documentation
- Enhanced BASE_QA.md with JavaScript test process management warnings
  - Added vitest warnings regarding process cleanup and lifecycle management
  - Improved guidance for handling test processes in JavaScript environments

## [4.7.1] - 2025-10-03

### Fixed
- **Critical**: IndentationError in config_service_base.py that prevented package from being imported
  - Fixed incorrect indentation in try-except block (lines 103-111)
  - Package is now fully functional and importable
  - Hotfix release to address broken v4.7.0

## [4.7.0] - 2025-10-03 [YANKED]

**Note**: This version was yanked due to a critical IndentationError. Use v4.7.1 instead.

### Added
- **🔴 Engineer Duplicate Elimination Protocol**: Mandatory protocol for detecting and eliminating duplicate code
  - Pre-implementation detection using vector search (`mcp__mcp-vector-search__search_similar`) and grep
  - Consolidation decision tree with measurable thresholds (>80% similarity = consolidate, >50% = extract common)
  - Single-path enforcement with documented A/B test exceptions only
  - Detection commands and red flag indicators for duplicate code patterns
  - Success criteria with measurable outcomes (zero duplicates, single canonical source)
  - Comprehensive consolidation protocol: analyze, merge, update references, remove obsolete, test

- **🚫 Anti-Pattern: Mock Data and Fallback Behavior**: Critical restrictions on engineering anti-patterns
  - Mock data ONLY for testing (never in production unless explicitly requested)
  - Fallback behavior is terrible engineering practice (explicit failures required)
  - Comprehensive examples of violations with correct alternatives
  - Rare acceptable cases documented (config defaults, graceful degradation with logging)
  - Enforcement guidelines: code reviews must flag mock data, fallbacks require justification
  - 84-line comprehensive guide with wrong vs. correct code patterns

- **Prompt Engineer Agent v2.0.0**: Comprehensive Claude 4.5 optimization with 23+ best practices
  - Extended thinking configuration (16k-64k token budgets, cache-aware activation)
  - Multi-model routing: Sonnet 4.5 for coding/analysis, Opus for strategic planning
  - Sonnet 4.5 beats Opus on coding (77.2% vs 74.5% SWE-bench) at 1/5th cost
  - Tool orchestration patterns (parallel execution, think tool, error handling)
  - Structured output methods (tool-based JSON schemas, response prefilling)
  - Context management (200K tokens, prompt caching: 90% cost + 85% latency reduction)
  - Anti-pattern detection (over-specification, wrong model selection, extended thinking misuse)
  - Performance benchmarks integrated (SWE-bench, OSWorld, cost analysis)
  - 787-line BASE_PROMPT_ENGINEER.md with comprehensive implementation guide
  - Template expanded from 296 to 726 lines (+145% with Claude 4.5 capabilities)

### Enhanced
- **Engineer Code Minimization**: Refined with concrete, falsifiable criteria
  - Measurable consolidation thresholds: >80% similarity, Levenshtein distance <20%, shared logic >50 lines
  - Maturity-based LOC thresholds with specific targets (early/growing/mature/legacy projects)
  - Post-implementation scorecard with mandatory metrics: Net LOC (+X/-Y), Reuse Rate (X%), Functions Consolidated
  - Streamlined from philosophical guidance to actionable rules with quantifiable success metrics
  - 287-line BASE_ENGINEER.md with clear priority hierarchy

### Changed
- **Engineer Template Configuration**: Simplified instructions to reference BASE_ENGINEER.md as single source of truth
  - Added `base_instructions_file` and `instruction_precedence` fields to engineer.json
  - Reordered knowledge priorities: code minimization → duplicate detection → clean architecture
  - Reordered best practices: vector search first → zero net lines → consolidation → LOC reporting
  - Maintains backward compatibility with enhanced clarity

## [4.6.1] - 2025-10-03

### Changed
- **Code Quality**: Consolidated imports and applied automated linting fixes
  - Consolidated duplicate imports across multiple files
  - Applied Black, isort, and Ruff auto-fixes for code formatting
  - Improved code consistency and maintainability

## [4.6.0] - 2025-10-03

### Added
- **Ruby Engineer Agent v1.0.0**: Comprehensive Ruby 3.3+ and Rails 7+ development specialist
  - Modern Ruby features: YJIT optimization, Fiber Scheduler, pattern matching, endless methods
  - Rails 7+ expertise: Hotwire (Turbo/Stimulus), ViewComponent, Active Storage, Action Mailbox
  - Testing frameworks: RSpec, Minitest, FactoryBot, Capybara, VCR
  - Background processing: Sidekiq, Good Job, Solid Queue
  - API development: Rails API, GraphQL (with graphql-ruby), Grape
  - Deployment: Docker, Kubernetes, Heroku, Kamal
  - Performance monitoring: Rack Mini Profiler, Bullet, New Relic
  - 344-line comprehensive template with modern Ruby/Rails best practices

- **5-Phase Publish & Release Workflow**: Comprehensive agent orchestration system for releases
  - Phase 1: Research agent analyzes requirements and constraints
  - Phase 2: Code Analyzer (Opus) reviews with APPROVED/NEEDS_IMPROVEMENT/BLOCKED
  - Phase 3: Implementation with specialized agent routing
  - Phase 4: Mandatory QA testing (api-qa, web-qa, or qa based on context)
  - Phase 5: Documentation updates for all code changes
  - Git security review before push with credential scanning
  - 195-line WORKFLOW.md with templates and decision trees

- **Startup Configuration Detection**: Interactive configuration setup on first run
  - Detects missing configuration files at startup
  - Interactive prompts for running configurator
  - Graceful fallback to defaults for non-interactive/CI environments
  - Smart skip logic for help/version/configure commands
  - 97-line enhancement to CLI startup flow

### Fixed
- **Linting Quality**: Auto-fixed 39 linting issues across 18 files
  - apply_optimizations.py, migrate_analyzers.py, migrate_configs.py, migrate_deployments.py
  - agent_registry.py, logging_config.py, registry/__init__.py, path_resolver.py
  - deployment_strategies/base.py, debug_agent_data.py, fix_event_broadcasting.py
  - fix_hook_event_format.py, fix_watchdog_disconnections.py
  - test-dashboard-hub.py, update_agent_tags.py
  - Improved code quality and consistency throughout

### Changed
- **PM Instructions**: Updated with publish workflow references
  - Integrated 5-phase workflow into PM decision-making
  - Enhanced agent routing for publish/release tasks
  - Improved quality gate enforcement

## [4.5.18] - 2025-10-02

### Changed
- **Version Bump**: Patch version increment for maintenance release

## [4.5.17] - 2025-10-02

### Fixed
- **Claude Code Startup**: Remove hardcoded model specification from startup commands
  - Removed hardcoded "--model opus" flags from interactive and oneshot sessions
  - Now uses Claude Code's default model selection instead of forcing Opus
  - Users can still override model with --model flag when launching claude-mpm
  - Affects: interactive_session.py, oneshot_session.py

### Changed
- **Code Formatting**: Minor formatting improvements in startup_logging.py

## [4.5.16] - 2025-10-02

### Added
- **/mpm-organize Slash Command**: New intelligent project file organization command
  - Analyzes project structure and suggests/executes file reorganization
  - Supports multiple strategies: convention-based, type-based, domain-based
  - Includes dry-run mode for safe preview of changes
  - Comprehensive documentation with examples and use cases

### Fixed
- **PM Instructions**: Allow verification commands for quality assurance
  - PM can now run `make quality`, `make lint-fix` for verification
  - Clarified PM cannot write code but can verify quality gates
- **Slash Command Documentation**: Fixed to match actual CLI implementation
  - Updated mpm-config.md with correct subcommands (list, get, set, etc.)
  - Updated mpm-help.md with proper delegation pattern
  - Updated mpm-status.md with correct usage and examples
  - All commands now accurately reflect claude-mpm CLI behavior

## [4.5.15] - 2025-10-02

### Added
- **Local-Ops Agent v1.0.2**: Enhanced verification and deployment policies
  - Mandatory auto-updating mode for development deployments
  - Verification policy requiring endpoint checks before success claims
  - Prevents "should work" claims without actual evidence

### Changed
- **PM Instructions**: Strengthened universal verification requirements
  - All subagents must verify endpoints/services before claiming success
  - Explicit prohibition of unverified success claims
  - Enhanced quality standards for agent coordination

## [4.5.14] - 2025-10-02

### Fixed
- **PyPI Deployment**: Corrected VERSION metadata issue from v4.5.13
  - Previous 4.5.13 release had mismatched internal VERSION file
  - Created 4.5.14 with synchronized VERSION across all package files
  - Includes all vitest/jest memory leak fixes from 4.5.13
  - Proper version reporting via `claude-mpm --version`

### Note
This release is functionally identical to 4.5.13 but with corrected version metadata.

## [4.5.13] - 2025-10-02

### Fixed
- **Test Process Management**: Prevent vitest/jest memory leaks in CI environments
  - Added CI-safe test execution patterns to all engineer and QA agent templates
  - Implemented process cleanup verification commands
  - Added test process management guidelines to BASE_ENGINEER.md and BASE_QA.md
  - Prevents watch mode activation with CI=true environment flags
  - Ensures proper test process termination after execution

### Changed
- Updated agent versions for all affected templates (patch bumps):
  - nextjs_engineer: 1.2.5 → 1.2.6
  - react_engineer: 1.2.3 → 1.2.4
  - typescript_engineer: 1.2.5 → 1.2.6
  - qa: 1.2.4 → 1.2.5
  - web_qa: 1.2.4 → 1.2.5

## [4.5.12] - 2025-10-01

### Fixed
- **Critical Linting Issues**: Comprehensive cleanup of 657 critical and medium priority issues
  - Fixed all 58 bare except clauses (E722) with specific exception types
  - Added exception chaining to 56 raise statements (B904) for better debugging
  - Fixed 23 asyncio dangling task references (RUF006) with proper tracking
  - Added timezone awareness to 120 datetime operations (DTZ005)
  - Migrated 281 operations to pathlib Path.open() (PTH123) - 87% complete
  - Overall reduction: 1,184 → 734 issues (38% improvement)

### Impact
- 368 files modified with 1,871+ code improvements
- Improved error handling with complete stack traces
- Production-safe async task management
- Eliminated timezone ambiguity bugs
- Modern Python best practices throughout
- All critical linting categories verified at 0 in src/ and tests/

### Technical Details
- Remaining 734 issues are low-priority (style, complexity) for future PRs
- Test suite passing (44 tests)
- No regressions introduced

## [4.5.11] - 2025-10-01

### Added
- **Local-Ops Port Allocation**: New ProjectPortAllocator service with hash-based port assignment (3000-3999 range)
  - Deterministic port assignment based on project path hash
  - Global port registry for multi-project coordination
  - Collision detection and automatic port reassignment
  - Comprehensive test coverage (28 tests)

- **Orphan Process Detection**: New OrphanDetectionService for automated cleanup
  - PM2 process cleanup with owner verification
  - Docker container cleanup with project verification
  - Native process cleanup with safety checks
  - Integration with port allocation system
  - Comprehensive test coverage (23 tests)

- **Dart Engineer Agent**: New specialized agent for Flutter/cross-platform development
  - Support for mobile, web, desktop, and backend Dart projects
  - State management patterns (BLoC, Riverpod, Provider, GetX)
  - Comprehensive code generation and testing patterns
  - Platform-specific optimizations and best practices

### Enhanced
- **Configuration UI**: Added version display to configurator header for better visibility

### Fixed
- **Agent Loading**: Fixed lazy import handling for agent templates in agent_loader.py
- **Agent Inheritance**: Improved base agent manager inheritance resolution

### Technical Details
- New services: ProjectPortAllocator (601 lines), OrphanDetectionService (791 lines)
- New tests: test_project_port_allocator.py (454 lines), test_orphan_detection.py (598 lines)
- New agent: dart_engineer.json (294 lines)
- Total test coverage: 51 new tests, all passing
- Updated local_ops_agent.json with new service capabilities

## [4.5.10] - 2025-10-01

### Performance
- **Hook Handler Optimization**: Optimized initialization with lazy imports (30% faster: 1290ms → 900ms)
  - Converted services/__init__.py to dictionary-based lazy imports for cleaner code
  - Converted core/__init__.py to dictionary-based lazy imports
  - Converted services/mcp_gateway/__init__.py to dictionary pattern
  - Made event_emitter import lazy in ConnectionManagerService (~85% reduction in overhead)
  - Refactored __getattr__ if/elif chains to maintainable dictionary pattern
  - Removed base_agent_loader from hook initialization path

### Technical Details
- Dictionary-based lazy imports improve code maintainability while preserving performance
- Event emitter lazy loading significantly reduces hook handler startup time
- Cleaner __getattr__ implementation makes codebase more maintainable

## [4.5.9] - 2025-10-01

### Enhanced
- **Startup Configurator**: Complete overhaul with improved UX and functionality
  - Fixed agent state persistence across menu navigation
  - Implemented auto-launch of claude-mpm after configuration save
  - Syncs startup.disabled_agents → agent_deployment.disabled_agents for proper deployment
  - Updated menu text for clarity ("Save configuration and start claude-mpm")
  - Changed default option from 'b' (back) to 's' (save) for better workflow
  - Removed obsolete websocket service from hook services list

- **Agent Standardization**: All 29 agents updated to Sonnet model
  - 7 agents upgraded from Opus to Sonnet (code-analyzer, data-engineer, engineer, prompt-engineer, refactoring-engineer, research, web-ui)
  - Patch version bump for all 29 agent templates
  - Improved consistency and cost efficiency across agent fleet

### Fixed
- **Logging Noise**: Eliminated duplicate MCP service logging (40+ repetitive lines removed)
  - Removed noisy debug logging from get_filtered_services() method
  - Clean startup logs with only relevant information
- **Configuration Sync**: Fixed startup configuration not being applied to agent deployment
  - Disabled agents are now properly removed from .claude/agents/ directory
  - Configuration changes take immediate effect on startup

### Technical Details
- Updated configurator to use os.execvp("claude-mpm", ["claude-mpm", "run"]) for proper startup
- Added agent_deployment.disabled_agents sync in save configuration
- Removed redundant DEBUG logging that was called 10× per startup
- All agent versions verified: 29/29 using Sonnet model

## [4.5.8] - 2025-09-30

### Enhanced
- **Local Operations Agent**: Updated local-ops agent (v1.0.1) with critical stability imperatives
  - Maintains single stable instances of development servers (no duplicates)
  - Never interrupts services from other projects or Claude Code sessions
  - Protects all Claude MPM, MCP, and monitor services from interference
  - Smart port allocation - finds alternatives instead of killing existing processes
  - Graceful operations with proper ownership checks before any actions
  - Session-aware coordination with multiple Claude Code instances

- **PM Instructions**: Enhanced PM delegation to prioritize local-ops-agent for localhost work
  - Added mandatory local-ops-agent priority rule for all localhost operations
  - Updated delegation matrix with explicit local-ops-agent entries at top
  - Local dev servers, PM2, port management, npm/yarn/pnpm all route to local-ops-agent
  - Prevents PM from using generic Ops agent for local development tasks
  - Ensures proper handling of local services with stability and non-interference

### Technical Details
- Updated local_ops_agent.json with stability_policy configuration
- Enhanced error recovery with process ownership verification
- Added operational principles for single instance enforcement
- Modified deployment workflow to check conflicts before actions
- Updated PM_INSTRUCTIONS.md with 19 references to local-ops-agent priority

## [4.5.7] - 2025-09-30

### Fixed
- **Session Management**: Enhanced session lifecycle and initialization
  - Introduced centralized SessionManager service for consistent session ID management
  - Fixed duplicate session ID generation issues across services
  - Improved async logger initialization and lifecycle management
  - Added comprehensive logging for service startup sequence

### Technical Details
- Added new SessionManager service as single source of truth for session IDs
- Refactored ClaudeSessionLogger and AsyncSessionLogger to use SessionManager
- Enhanced service initialization order and dependency management
- Improved error handling and logging throughout session management

## [4.5.6] - 2025-09-30

### Fixed
- **AsyncSessionLogger Lifecycle Management**: Resolved task cleanup and lifecycle issues
  - Fixed proper task cleanup during AsyncSessionLogger shutdown
  - Prevented duplicate session ID generation in ClaudeSessionLogger
  - Added comprehensive service initialization logging for debugging
  - Improved service state management during initialization phase
  - Cleaned up import organization and removed unused imports

### Technical Details
- Enhanced AsyncSessionLogger with proper asyncio task lifecycle management
- Added singleton pattern enforcement for ClaudeSessionLogger to prevent duplicates
- Improved service initialization visibility with detailed logging
- Removed unused imports across multiple service modules

## [4.5.5] - 2025-09-30

### Fixed
- **MCP Service Management**: Improved MCP dependency handling and error recovery
  - Automatic MCP dependency reinstallation on startup for corrupted installations
  - Enhanced error handling and recovery mechanisms for MCP services
  - Improved service reliability through proactive dependency checks

- **MCP Gateway Optimization**: Disabled pre-warming to prevent conflicts
  - Removed MCP gateway pre-warming that could interfere with Claude Code
  - Prevents duplicate service initialization and resource conflicts
  - Cleaner startup process with better service isolation

- **kuzu-memory Integration**: Enhanced compatibility and configuration
  - Updated configuration for kuzu-memory v1.1.7 compatibility
  - Improved version checking with automatic update prompts
  - Better integration with latest kuzu-memory features
  - Removed unnecessary gql injection logic from MCP config manager

### Improved
- MCP service startup reliability and error recovery
- Service dependency management and validation
- kuzu-memory version detection and upgrade workflow

## [4.5.4] - 2025-09-29

### Added
- **Automatic kuzu-memory Version Checking**: MCP Gateway now checks for kuzu-memory updates at startup
  - Checks PyPI once per 24 hours to minimize network requests
  - Interactive user prompts for available updates with one-click upgrade
  - Non-blocking with 5-second timeout to avoid startup delays
  - Configurable via user preferences file (~/.config/claude-mpm/update_preferences.json)
  - Environment variable override (CLAUDE_MPM_CHECK_KUZU_UPDATES=false)
  - Fully tested with 34 unit and integration tests (100% passing)
  - Graceful degradation when PyPI is unavailable
  - Respects user choices and remembers "skip version" preferences

### Technical Details
- New PackageVersionChecker utility for version comparison and PyPI queries
- UpdatePreferencesManager for persistent user preferences
- Cache system prevents excessive PyPI requests
- Async subprocess execution for pipx upgrades
- Clean integration with MCP process pool initialization

## [4.5.3] - 2025-09-29

### Enhanced
- **PM Localhost Verification Enforcement**: Added 7 strict enforcement rules for localhost deployment verification
  - PM must verify all localhost deployment claims via local-ops agent
  - Mandatory fetch test execution before confirming deployments
  - Hard enforcement: PM should apologize and refuse to continue without verification
  - Prevents false deployment confirmations and enforces proof-of-work protocol
  - Clear rejection of unverified screenshots and visual confirmation
  - Ensures reliable deployment validation process

### Improved
- **Logging Verbosity Reduction**: Reduced startup log noise by 45%
  - Changed INFO to DEBUG for non-critical initialization messages
  - UnifiedPathManager initialization now DEBUG level
  - Monitor connection warnings reduced to DEBUG (service is optional)
  - Async session logger stats now conditional (only INFO if sessions logged)
  - Deployment context detection messages reduced to DEBUG
  - Event emitter logger simplified from full module path to "event_emitter"
  - Session ID logging combined into single line for cleaner output

### Fixed
- **Logger Naming**: Fixed duplicate module path in event_emitter logger name
  - Changed from full module path to simple "event_emitter" identifier

## [4.5.2] - 2025-09-29

### Fixed
- **MCP Ticketer Dependency Handling**: Enhanced v0.1.8 workaround for missing gql dependency
  - Added version checking to detect when workaround is needed
  - Improved documentation explaining temporary nature of fix
  - Added defensive check to avoid unnecessary re-injection when gql already present
  - More informative log messages with context and rationale
  - Better error handling with timeout and detailed error logging

- **Doctor Command MCP Checks**: Eliminated duplicate MCP service validation
  - Fixed issue where MCP service checks ran twice, 9 seconds apart
  - Added early return in _check_mcp_auto_configuration() when doctor command detected
  - Doctor command now performs comprehensive checks without interference
  - Prevents duplicate log messages and improves user experience

## [4.5.1] - 2025-09-29

### Fixed
- **Web QA Agent Version**: Updated agent version to properly reflect UAT enhancement
  - Changed agent_version from 2.0.0 to 3.0.0 in web_qa.json
  - Updated timestamp to current date
  - Agent version now correctly indicates major feature addition

## [4.5.0] - 2025-09-29

### Added
- **UAT Mode for Web QA Agent**: Comprehensive User Acceptance Testing capabilities
  - Business intent verification beyond technical validation
  - PRD and documentation review before testing
  - Proactive clarification questions for unclear requirements
  - Behavioral test script creation in Gherkin/BDD format
  - User journey testing for complete workflows
  - Business value validation and goal achievement assessment
  - UAT report generation with business impact analysis

### Enhanced
- **Web QA Agent Capabilities**: Dual-mode testing approach
  - Maintains all existing technical testing features (6-phase progressive protocol)
  - Adds business-focused UAT methodology
  - Creates human-readable test scripts in `tests/uat/scripts/`
  - Reports on both technical success and business alignment
  - Validates acceptance criteria from user perspective
  - Links technical findings to business impact

### Improved
- **Testing Philosophy**: Shifted from "does it work?" to "does it meet goals?"
  - Intent verification vs just functional validation
  - Business requirements coverage tracking
  - User experience validation throughout journey
  - Stakeholder-friendly reporting format

## [4.4.12] - 2025-09-29

### Fixed
- **MCP Configuration Path**: Corrected config file location check
  - Fixed mpm-doctor checking wrong path `~/.claude/mcp/config.json`
  - Now correctly checks `~/.claude.json` (Claude Code's actual config)
  - Diagnostic reports now show accurate configuration status

- **MCP Service PATH Resolution**: Improved service binary discovery
  - Services now resolve to pipx venv paths first for better isolation
  - Added proper fallback to `pipx run` when direct paths aren't available
  - Fixed mcp-vector-search and mcp-ticketer PATH accessibility issues

- **Startup Configuration**: Automatic MCP service setup on launch
  - Added automatic configuration during Claude MPM startup
  - Detects and fixes corrupted MCP service installations
  - Updates all projects in `~/.claude.json`, not just current one
  - Auto-injects missing dependencies (e.g., gql for mcp-ticketer)

### Improved
- **Service Reliability**: Better handling of MCP service variations
  - Supports both pipx venv paths and system-wide installations
  - Graceful fallback when services aren't directly accessible
  - More robust path resolution across different environments

## [4.4.11] - 2025-09-29

### Fixed
- **MPM Doctor Command**: Resolved slash command execution in Claude Code
  - Added `claude-mpm-doctor` as standalone CLI entry point
  - Enhanced PM instructions to properly recognize `/mpm-*` commands
  - Fixed command invocation to use SlashCommand tool instead of Bash
  - Improved error handling and diagnostic output

### Added
- **Dedicated Doctor Entry Point**: New `claude-mpm-doctor` command
  - Standalone binary for direct doctor command execution
  - Maintains full compatibility with `claude-mpm doctor`
  - Supports all diagnostic options (--verbose, --json, --fix, etc.)
  - Returns appropriate exit codes for CI/CD integration

### Improved
- **Command Recognition**: Better slash command handling
  - PM instructions now explicitly guide SlashCommand tool usage
  - Clear differentiation between MPM commands and file paths
  - Examples of correct vs incorrect command invocation
  - Prevents confusion when users type `/mpm-doctor` in Claude Code

## [4.4.10] - 2025-09-29

### Fixed
- **MCP Service Configurations**: Resolved critical configuration issues for remote installations
  - Fixed kuzu-memory to use direct binary path instead of problematic `pipx run`
  - Fixed mcp-vector-search to use Python interpreter from pipx venv
  - All services now use direct binary paths for improved reliability
  - Resolved PATH issues when subprocess spawns without shell environment

- **Dynamic Path Resolution**: Improved cross-environment compatibility
  - Added dynamic user home directory detection (no hardcoded paths)
  - Implemented fallback path resolution for pipx and service binaries
  - Support for common installation locations (`/opt/homebrew/bin`, `/usr/local/bin`, `~/.local/bin`)

### Added
- **Configuration Validation**: Pre-apply validation for MCP services
  - New `test_service_command()` method validates configs before applying
  - Automatic fallback configurations when primary validation fails
  - Special fallback handling for mcp-vector-search using `pipx run --spec`

### Improved
- **Service Management**: Enhanced reliability and error handling
  - Direct binary usage preserves injected dependencies (fixes mcp-ticketer gql issue)
  - Better error reporting with validation failures shown separately
  - Configs only saved after successful validation
  - Graceful degradation when services are unavailable

## [4.4.9] - 2025-09-29

### Fixed
- **Agent Deployment Logging**: Eliminated duplicate deployment messages
  - Fixed redundant version checking in multi-source deployments
  - Added `skip_version_check` parameter to prevent repeated checks
  - Resolved "Deploying 9 agents" followed by "Deployed 0 agents" issue

- **kuzu-memory Command**: Corrected MCP server command arguments
  - Fixed command from incorrect `["claude", "mcp-server"]` to correct `["mcp", "serve"]`
  - Resolved failures on both local and remote installations
  - Properly handles all kuzu-memory invocation scenarios

- **mcp-ticketer Dependencies**: Auto-fix for missing gql dependency
  - Automatically injects gql dependency when missing (for versions <= 0.1.8)
  - Prevents runtime failures due to packaging bug in older versions
  - Optimized check to run once per session, not per project

### Added
- **MCP Connection Testing**: Enhanced mpm-doctor with actual connection tests
  - Now sends JSON-RPC 2.0 initialize requests to verify connectivity
  - Tests tool discovery with tools/list requests
  - Measures response times for performance monitoring
  - Provides detailed connection diagnostics beyond installation checks

- **Static MCP Configuration**: Reliable service configuration system
  - Implemented STATIC_MCP_CONFIGS for known-good service configurations
  - Updates all projects in ~/.claude.json, not just current one
  - Eliminates detection errors from dynamic service discovery
  - Ensures consistent configuration across all environments

### Improved
- **mpm-doctor Command**: Made accessible and enhanced functionality
  - Added to CLI wrapper scripts (claude-mpm and claude-mpm-mamba)
  - Enhanced with real JSON-RPC connection testing
  - Better error reporting and diagnostic output
  - Auto-fix capabilities for common configuration issues

- **Startup Performance**: Optimized MCP service checks
  - Dependency checks now run once per startup, not per project
  - Reduced startup time for multi-project environments
  - More efficient configuration update process

## [4.4.8] - 2025-09-28

### Added
- **MCP Service Verification Command**: Comprehensive MCP service health checks and auto-fix capabilities
  - New `claude-mpm verify` command for checking MCP service installation and configuration
  - Auto-fix functionality with `--fix` flag to automatically resolve common issues
  - Service-specific verification with `--service` option for targeted diagnostics
  - JSON output support with `--json` flag for automation and scripting
  - Startup verification automatically checks MCP services and displays warnings
  - Support for all MCP services: kuzu-memory, mcp-vector-search, mcp-browser, mcp-ticketer

### Documentation
- **Enhanced CLI Documentation**: Added comprehensive verify command documentation
  - Updated README.md with verify command examples and usage patterns
  - Added detailed verify command reference in CLI commands documentation
  - Added dedicated MCP Service Issues section to troubleshooting guide
  - Included startup verification behavior documentation
  - Enhanced troubleshooting with specific service recovery procedures

### Improved
- **MCP Service Diagnostics**: Enhanced user experience for MCP service management
  - Clear status indicators: working, missing, broken with detailed messages
  - Automatic service installation via pipx when services are missing
  - Detailed diagnostic information including paths, commands, and fix suggestions
  - Integration with existing doctor command for comprehensive health checks

## [4.4.6] - 2025-09-28

### Fixed
- **kuzu-memory MCP Server**: Fixed command format for MCP server execution
  - Changed from `kuzu-memory server` to correct `mcp serve` command
  - Resolved server startup failures due to incorrect command format
  - Properly integrated with MCP service infrastructure

### Documentation
- **Claude Code Integration**: Clarified integration requirements
  - Updated all references to correctly specify Claude Code CLI (not Claude Desktop)
  - Emphasized that Claude MPM is designed for Claude Code CLI integration
  - Fixed diagnostic checks to reference Claude Code instead of Claude Desktop
  - Improved clarity in installation and setup documentation

### Improved
- **MCP Service Commands**: Standardized MCP server invocation
  - All MCP services now use consistent `mcp serve` command format
  - Better error messages when MCP services fail to start
  - Enhanced service configuration validation

## [4.4.5] - 2025-09-28

### Fixed
- **MCP Service Diagnostics**: Resolved false positives in mpm-doctor command
  - Fixed incorrect service availability detection
  - Made MCP services truly optional dependencies
  - Improved accuracy of service health status reporting

### Improved
- **MCP Service Auto-Installation**: Enhanced fallback installation methods
  - Added `pipx run` fallback when direct import fails
  - Better handling of PATH configuration issues
  - More robust service availability detection
  - Clearer error messages for installation failures

### Changed
- **Optional Dependencies**: MCP services now properly optional
  - Services install on-demand when first needed
  - No longer required for core Claude MPM functionality
  - Graceful degradation when services unavailable

## [4.4.4] - 2025-09-28

### Added
- **Enhanced mpm-doctor command**: Comprehensive MCP service diagnostics
  - Detailed MCP service configuration validation
  - Service health checks with connection testing
  - Markdown report generation with `--output-file` parameter
  - Rich terminal output with color-coded status indicators

### Improved
- **Installation Detection**: Better detection of pipx vs source installations
  - Accurate identification of installation method
  - Appropriate command suggestions based on installation type
  - Clearer diagnostic output for troubleshooting

- **Documentation**: Consolidated and cleaned up documentation
  - Removed duplicate and outdated documentation files
  - Streamlined MCP service documentation
  - Updated user guides with current command options

### Fixed
- Corrected mpm-doctor service validation logic
- Fixed MCP service status reporting accuracy
- Improved error handling in diagnostic reports

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

