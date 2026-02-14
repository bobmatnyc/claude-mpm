## [Unreleased]

### Added

### Changed

### Fixed

### Documentation

### Tests

## [5.8.13] - 2026-02-13

### Changed
- Patch release for PyPI publication

## [5.8.12] - 2026-02-13

### Added
- **PackageInstallerService**: Declarative package installation abstraction
  - New centralized service for handling pipx/uv/pip installations
  - InstallerType, InstallAction enums for clean API
  - PackageSpec dataclass for declarative package definitions
  - PACKAGE_SPECS mapping for all setup services
  - Refactored kuzu-memory setup as proof of concept (190 -> 35 lines)

## [5.8.11] - 2026-02-13

### Changed
- Patch release for PyPI publication

## [5.8.10] - 2026-02-13

### Changed
- Patch release for PyPI publication

## [5.8.9] - 2026-02-13

### Changed
- Patch release for PyPI publication

## [5.8.8] - 2026-02-13

### Changed
- Patch release for PyPI publication

## [5.8.7] - 2026-02-13

### Changed
- Patch release for PyPI publication

## [5.8.6] - 2026-02-13

### Changed
- Patch release for PyPI publication

## [5.8.5] - 2026-02-13

### Changed
- Patch release for PyPI publication

## [5.8.4] - 2026-02-13

### Changed
- Patch release for PyPI publication

## [5.8.3] - 2026-02-13

### Changed
- Patch release for PyPI publication

## [5.8.2] - 2026-02-13

### Changed
- Patch release for PyPI publication

## [5.8.1] - 2026-02-13

### Fixed
- Fixed startup warning by adding `AgentCapabilitiesService.get_all_agents()` method
- Fixed hooks architecture by removing direct kuzu-memory hooks integration
- Fixed multi-service setup bug that caused early termination
- Added documentation for comma-delimited service support

## [5.8.0] - 2026-02-13

### Added
- **Domain Authority System**: Intelligent agent and tool discovery for PM delegation (PR #XXX)
  - **Setup Registry Service**: Centralized tracking of MCP servers and CLI tools
    - Location: `~/.claude-mpm/setup-registry.json`
    - Tracks service names, types, versions, tools, and setup dates
    - Thread-safe registry operations with `SetupRegistry` class
  - **Dynamic Skills Generator**: Auto-generates agent/tool selection skills at startup
    - `mpm-select-agents.md`: Lists all available agents with capabilities
    - `mpm-select-tools.md`: Lists all configured MCP/CLI tools with help text
    - Generated at: `~/.claude-mpm/skills/dynamic/`
    - Runs automatically during Claude MPM startup
  - **PM Integration**: PM agent uses generated skills for intelligent delegation
    - Agent selection based on capabilities and domains
    - Tool selection based on available MCP servers
    - Context-aware routing to appropriate specialists
  - See: [Domain Authority System Documentation](docs/features/domain-authority-system.md)

- **Skills Optimization Command**: Intelligent project-based skill recommendations (PR #XXX)
  - `claude-mpm skills optimize`: Analyze project and recommend relevant skills
  - Auto-detection of languages, frameworks, tools, and databases
  - Priority-based recommendations (Critical, High, Medium, Low)
  - Optional auto-deployment with `--auto-deploy` flag
  - Filter by priority with `--priority` flag
  - Limit recommendations with `--max-skills` flag
  - See: [Skills Optimization Guide](docs/user/skills-optimize.md)

- **MCP-Skillset Integration**: Optional user-level RAG-powered skill recommendations (PR #XXX)
  - User-level MCP server (not project-specific)
  - RAG-powered semantic skill matching
  - Enhanced recommendations via `--use-mcp-skillset` flag
  - Fallback to local manifest if unavailable
  - See: [MCP-Skillset Integration](docs/features/mcp-skillset-integration.md)

### Changed
- **Startup Sequence**: Dynamic skills generation integrated into startup process
  - Skills automatically regenerate on every Claude MPM startup
  - Ensures agent/tool discovery is always current
  - No manual regeneration needed after installing MCP servers

### Documentation
- **New Documentation**:
  - `docs/features/domain-authority-system.md`: Comprehensive domain authority guide
    - Architecture diagrams
    - API reference
    - Usage examples
    - Troubleshooting guide
  - Updated README.md with domain authority system features
  - Skills optimization documentation already comprehensive

- **Documentation Review**:
  - `docs/user/skills-optimize.md`: Verified current (no changes needed)
  - `docs/features/mcp-skillset-integration.md`: Verified current (no changes needed)
  - `docs/integrations/gworkspace-mcp.md`: Already reflects canonical naming

### Technical Details
- New Services:
  - `src/claude_mpm/services/setup_registry.py`: SetupRegistry class
  - `src/claude_mpm/services/dynamic_skills_generator.py`: DynamicSkillsGenerator class
- Integration Points:
  - `src/claude_mpm/cli/startup.py`: Startup integration
  - `src/claude_mpm/services/agent_capabilities_service.py`: Agent discovery
- Generated Files:
  - `~/.claude-mpm/skills/dynamic/mpm-select-agents.md`: Auto-generated agent skill
  - `~/.claude-mpm/skills/dynamic/mpm-select-tools.md`: Auto-generated tool skill
  - `~/.claude-mpm/setup-registry.json`: Tool registry data

## [5.7.34] - 2026-02-12

### Added
- **PM and research workflow skills**: Added comprehensive workflow skills for project management and research tasks (PR #298)

### Changed
- **Google Workspace MCP naming**: Standardized to `gworkspace-mcp` as canonical service name
  - CLI accepts both `gworkspace-mcp` (canonical) and `google-workspace-mcp` (legacy alias)
  - Automatic migration of old `google-workspace-mcp` configurations to `gworkspace-mcp`
  - Command binary remains `google-workspace-mcp` (installed executable)
  - Both names work for backward compatibility

### Fixed
- **Google Workspace MCP setup**: Install `gworkspace-mcp` package before OAuth configuration
  - Setup now runs `uv tool install gworkspace-mcp` before OAuth flow
  - Fixes issue where `.mcp.json` referenced non-existent command
  - Follows same pattern as other MCP services (kuzu-memory, mcp-vector-search)

### Documentation
- **gworkspace-mcp naming**: Updated all documentation to reflect canonical `gworkspace-mcp` naming
  - README.md: Updated references to use canonical name with backward compatibility note
  - docs/integrations/README.md: Updated all setup examples and commands
  - docs/integrations/gworkspace-mcp.md: Added comprehensive naming convention documentation
  - Documented auto-migration behavior for old configurations

## [5.7.33] - 2026-02-11

### Fixed
- **Dashboard display**: Fresh installations now properly show tools, files, and agents
  - Fixed event categorization in broadcaster.py
  - Fixed correlation_id extraction in event-correlation.ts
  - Fixed Svelte 5 reactivity issues with object wrapper pattern
  - Fixed stream filter for 'all-streams' option
  - Added processedEventIds to prevent duplicates in FilesView
  - Enhanced file path extraction for notebook_path field
  - Fixed FileViewer content fetch with proper vite proxy configuration

## [5.7.32] - 2026-02-11

### Fixed
- **Kuzu-memory dependencies**: Fix numpy dependency issue in uv tool install

## [5.7.31] - 2026-02-11

### Fixed
- **Hook installation**: Prevent reinstalling hooks on every startup to avoid file lock conflicts
  - sync_hooks_on_startup() now checks installation status before attempting reinstall
  - Fixes "file is locked" errors during hook execution caused by concurrent writes to settings.local.json

## [5.7.30] - 2026-02-11

### Added
- **mcp-skillset integration**: Added mcp-skillset to setup command for skill management

### Fixed
- **Setup command**: Improved error messages for invalid arguments

## [5.7.29] - 2026-02-11

### Fixed
- **Setup command**: Prevent auto-config from interfering with setup command (issue #297)
  - Auto-configuration now skips during setup to avoid race conditions
  - Setup command has exclusive control over .mcp.json during installation

## [5.7.28] - 2026-02-11

### Added
- **PM Bug Reporting**: External system bug routing support for delegating bugs to external systems

## [5.7.27] - 2026-02-11

### Fixed
- **Kuzu-memory**: Archive migrated memory files to prevent re-import

## [5.7.26] - 2026-02-11

### Fixed
- **Kuzu-memory hooks**: Remove independent hooks during setup to prevent conflicts with unified hooks

### Changed
- **PM instructions**: Circuit Breaker #13 - Language Detection for multilingual support
- **PM instructions**: Circuit Breaker #13 - Model Preference handling for optimal model selection
- **PM instructions**: Circuit Breaker #13 - Research Gate for preventing premature implementation

## [5.7.25] - 2026-02-10

### Added
- **Google Workspace MCP**: Google Docs tabs support (list, get, create, update, move tabs)
- **Google Workspace MCP**: Mermaid diagram rendering tool for creating diagrams in Google Docs

### Fixed
- **Kuzu-memory hooks**: Use async learn for non-blocking storage during prompt enhancement

## [5.7.24] - 2026-02-10

### Fixed
- **Kuzu-memory setup**: Fixed migration command to use correct `kuzu-memory memory learn` syntax
- **Kuzu-memory setup**: Added auto-launch of claude-mpm after setup (consistent with slack setup)
- **Kuzu-memory setup**: Added `--no-start` flag to exit before launching

### Documentation
- **STARTUP-PROCEDURES.md**: Complete documentation of 7-phase initialization sequence
  - Agent discovery and deployment process
  - Instructions compilation and BASE_AGENT inheritance
  - Dynamic delegation authority building
  - Configuration files and setup commands
- **Documentation organization**: Moved files to appropriate subdirectories
  - Developer reference docs consolidated in `docs/developer/`
  - Integration guides in `docs/integrations/`
- **Agent format correction**: Updated docs to reflect markdown+YAML frontmatter (not JSON)

## [5.7.23] - 2026-02-10

### Added
- **Notion MCP integration**: Full Notion API support for page and database operations
  - Workspace search, page CRUD, database queries
  - Block-level content manipulation
  - User and comment management
- **Confluence MCP integration**: Enterprise wiki management capabilities
  - Space and page operations
  - Content search and retrieval
  - Attachment handling
- **Bulk operations framework**: High-performance batch processing tools
  - Parallel execution for large-scale operations
  - Rate limiting and error handling
  - Progress tracking and reporting
- **Kuzu-memory v1.6.33 subservient mode**: Graph-based memory with enhanced context
  - Automatic prompt enhancement with project context
  - Asynchronous learning from conversations
  - Memory recall and statistics
- **Memory backend abstraction**: Pluggable memory system architecture
  - Support for multiple memory backends
  - Configuration schema for memory providers
  - Setup command for kuzu-memory installation

### Documentation
- Added Notion and Confluence MCP setup guides
- Documented bulk operations API and usage patterns
- Updated memory system configuration examples

## [5.7.22] - 2026-02-09

### Changed
- Patch release: Package distribution update

## [5.7.21] - 2026-02-09

### Added
- **Google Workspace bulk operations tools (EP-0002)**: 8 new bulk operation tools for 10x faster batch processing
  - Gmail: export_messages, import_messages (batch email operations)
  - Calendar: export_events, bulk_create_events (batch calendar management)
  - Drive: batch_upload_files, batch_download_files (efficient file sync)
  - Slack: list_all_channels, export_messages (team data access)
- **MCP calendar management**: New calendar CRUD operations in google-workspace-mcp
  - create_calendar, update_calendar, delete_calendar (calendar lifecycle management)
  - Completes calendar management capabilities

### Documentation
- **Comprehensive tools guide**: 450+ line documentation for bulk operations framework
  - Usage patterns, API reference, error handling
  - Performance optimization and rate limiting guidelines
  - Integration examples for common workflows

## [5.7.20] - 2026-02-08

### Fixed
- **Setup command UI**: Setup commands no longer show banner and "Launching Claude..." messages
  - Previously: Setup commands showed startup UI before validation, confusing users
  - Now: Clean output with immediate error messages when validation fails
- **Error message visibility**: Validation errors now print to console instead of being silent
  - Example: `Error: OAuth setup requires --oauth-service flag`
- **VERSION file sync**: Fixed `src/claude_mpm/VERSION` not being updated (was 5.7.11)
  - All VERSION files now stay in sync during release process

### Changed
- `should_show_banner()` now skips banner for setup and slack commands
- `manage_setup()` prints error messages when validation fails

## [5.7.19] - 2026-02-08

### Added
- **Auto-launch after Slack setup**: Slack setup now automatically launches claude-mpm after successful configuration
  - Matches OAuth setup behavior for consistent user experience
  - Can be disabled with `--no-launch` flag

### Fixed
- **Incorrect setup instructions**: Removed incorrect "python -m claude_mpm.slack_bot" instruction
  - Slack bot is integrated as MCP server, not a standalone command
  - Updated "Next steps" to clarify Slack MCP server is configured and ready

### Changed
- Setup help text now clarifies `--no-launch` works for all services

## [5.7.18] - 2026-02-08

### Added
- **Auto-load Slack tokens**: Setup now checks `.env.local` for tokens before prompting
  - Loads `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` if present
  - Only prompts if tokens not found or invalid
  - Skips saving if tokens already in file

### Changed
- Slack setup now matches OAuth setup UX pattern
- Better user experience: no re-entering tokens if already configured

## [5.7.17] - 2026-02-08

### Changed
- Patch version bump

## [5.7.16] - 2026-02-08

### Fixed
- **CRITICAL: Setup timing issue**: Setup commands now run BEFORE Claude Code launches
  - Previously: Setup ran after full initialization (agents, skills, Claude launch)
  - Now: Setup commands bypass initialization and run immediately
  - Fixes: Setup failures due to running too late in startup sequence
- **slack-bolt installation**: Changed from `pip` to `uv pip` for tool environments
  - Fixes: "pip: command not found" error when installing dependencies

### Changed
- Setup commands (`setup`, `slack`, `oauth`) now skip background services for faster startup
- Updated documentation to clarify setup must run before launch

## [5.7.15] - 2026-02-08

### Changed
- Patch version bump for consistency

## [5.7.14] - 2026-02-08

### Added
- **Service-specific options**: Flags after a service name apply to that service
  - Example: `claude-mpm setup slack oauth --oauth-service google-workspace-mcp --no-browser`
  - Follows Unix CLI conventions (flags apply to preceding item)
  - Enables true one-command multi-service setup with different options per service

### Changed
- **Improved setup command parsing**: Custom parser associates flags with their services
- **Better error messages**: Clear guidance when flags are misplaced or missing required values

### Documentation
- Updated examples to show service-specific options patterns
- Added note about flag association rules (flags apply to preceding service)

## [5.7.13] - 2026-02-08

### Added
- **Multi-service setup**: Run `claude-mpm setup slack google-workspace-mcp` to set up multiple services sequentially
- **Deprecation warnings**: Old command patterns now show migration guidance with clear messaging

### Changed
- **Deprecated commands** (still functional with warnings):
  - `claude-mpm slack setup` → Use `claude-mpm setup slack`
  - `claude-mpm oauth setup <service>` → Use `claude-mpm setup oauth --oauth-service <service>`
- OAuth setup now requires explicit `--oauth-service` flag for clarity
- Setup command stops on first failure with clear error messages

### Documentation
- Updated command examples to show new patterns
- Added migration guidance for deprecated commands

## [5.7.12] - 2026-02-08

### Added
- **Unified setup command**: New 'claude-mpm setup [service]' architecture for consistent service setup
- Support for multiple setup targets: slack, google-workspace-mcp, oauth

### Changed
- **CLI structure**: Refactored from 'claude-mpm slack setup' to 'claude-mpm setup slack'
- **Backward compatibility**: Old command structure still works for existing workflows

### Documentation
- Updated setup documentation to reflect new command structure

## [5.7.11] - 2026-02-08

### Added
- **Slack setup command**: New 'claude-mpm slack setup' CLI command for easier Slack app configuration

### Changed
- **Slack setup workflow**: Simplified setup process, no more messy Python one-liners
- **Command patterns**: Slack setup follows oauth command pattern for consistency

### Documentation
- Updated Slack setup documentation for cleaner workflow

## [5.7.10] - 2026-02-08

### Fixed
- **Script distribution**: setup-slack-app.sh now properly distributed with package

### Documentation
- Moved DISTRIBUTED_SCRIPTS.md to developer docs
- Multiple investigation documents created

### Changed
- Hidden Tokens tab until data source resolved

## [5.7.9] - 2026-02-07

### Added
- **Dashboard token tracking UI**: New TokensView component for monitoring token usage

### Changed
- **Event handler token usage**: Add dedicated token_usage_updated event emission for real-time token tracking
- Dashboard Svelte build artifacts updated

## [5.7.8] - 2026-02-07

### Changed
- Patch version bump

## [5.7.7] - 2026-02-06

### Changed
- Patch version bump

## [5.7.6] - 2026-02-06

### Fixed
- **Google Tasks OAuth scope**: Add `https://www.googleapis.com/auth/tasks` scope to OAuth configuration for full Google Tasks API access

## [5.7.5] - 2026-02-06

### Added
- **Delegation matrix generator PoC**: Initial proof of concept for generating agent delegation matrices (#292)

## [5.7.4] - 2026-02-06

### Fixed
- **PM context pollution**: Allow direct execution of simple operational commands instead of unnecessary delegation
  - Add "Simple Operational Commands" exception to PM prohibitions for explicit/documented commands
  - Change "Research (ALWAYS FIRST)" to "Research (CONDITIONAL)" with skip criteria
  - Preserve user context when delegation IS needed (fixes #291)

## [5.7.3] - 2026-02-05

### Added
- **Gmail email management tools**: 16 new MCP tools for comprehensive Gmail message handling
  - Label management: `list_gmail_labels`, `create_gmail_label`, `delete_gmail_label`
  - Single message operations: `modify_gmail_message`, `archive_gmail_message`, `trash_gmail_message`, `untrash_gmail_message`, `mark_gmail_message_read`, `mark_gmail_message_unread`, `star_gmail_message`, `unstar_gmail_message`
  - Batch processing: `batch_modify_gmail_messages`, `batch_archive_gmail_messages`, `batch_trash_gmail_messages`, `batch_mark_gmail_messages_read`, `batch_delete_gmail_messages`

## [5.7.2] - 2026-02-04

### Added
- **Rclone-based Google Drive sync tools**: New MCP tools for bulk file operations using rclone
  - `list_drive_contents`: List Drive folder contents with structured JSON metadata
  - `download_drive_folder`: Download folders from Drive to local filesystem
  - `upload_to_drive`: Upload local folders to Drive
  - `sync_drive_folder`: Bidirectional sync between Drive and local
- **RcloneManager utility class**: Generates temporary rclone config from OAuth tokens in TokenStorage
  - Secure credential handling with automatic cleanup
  - Support for Google Docs export format configuration
  - Requires rclone CLI binary installed separately

## [5.7.1] - 2026-02-04

### Fixed
- Fix `_format_assistant_output` to handle Claude's content block format (list of `{type: "text", text: "..."}` objects)
- Fix process cleanup to handle already-exited processes (avoid ProcessLookupError)

### Tests
- Added 5 new tests for content block parsing edge cases
- Total MCP tests: 194

## [5.7.0] - 2026-02-04

### Added
- **MCP Session Server**: New `mpm-session-server` command exposing claude-mpm headless mode via MCP protocol
  - 5 session management tools: `mpm_session_start`, `mpm_session_continue`, `mpm_session_status`, `mpm_session_list`, `mpm_session_stop`
  - Full async subprocess management with configurable concurrency limits
  - Session forking support for exploring different approaches
  - Context preservation using Claude Code's native `--resume` functionality
  - Comprehensive error handling with rate limit and context window error detection

### Documentation
- Complete MCP Session Server documentation at `docs/mcp-session-server.md`
- Configuration examples for Claude Desktop integration
- Architecture diagrams and usage examples

### Tests
- Comprehensive test suite for MCP Session Server (189 tests)

## [5.6.111] - 2026-02-04

### Changed
- Remove unused root-level config files (.flake8, .readthedocs.yaml)

## [5.6.110] - 2026-02-04

### Added
- Google Docs comment tools with style guidelines for workspace MCP

### Fixed
- Sync full skill directories including scripts and references (#282)

## [5.6.109] - 2026-02-04

### Added
- Headless mode with exec-based execution (#238)

### Fixed
- Include config/*.yaml in package data (#281)

## [5.6.108] - 2026-02-03

### Fixed
- Add timeout to keyring operations to prevent indefinite hangs on macOS

## [5.6.107] - 2026-02-03

### Documentation
- Enhanced project description and metadata in pyproject.toml and README

## [5.6.106] - 2026-02-03

### Documentation
- Added credential testing policy to BASE_AGENT.md

## [5.6.105] - 2026-02-03

### Added
- Google Tasks API support with 13 new MCP tools (now 34 total tools in Workspace MCP)

## [5.6.104] - 2026-02-03

### Added
- Expanded Google Workspace MCP with full CRUD operations and markdown conversion

## [5.6.103] - 2026-02-01

### Changed
- Patch version bump

## [5.6.102] - 2026-02-01

### Changed
- Patch version bump

## [5.6.101] - 2026-01-29

### Added
- Customizable workflow system via /mpm-workflow command
- Workflow loader with project > user > default priority

### Documentation
- Self-action imperative added to BASE_AGENT.md
- Verification requirements added to WORKFLOW.md

## [5.6.100] - 2026-01-29

### Changed
- Removed commander module (extracted to standalone ai-commander package)

## [5.6.99] - 2026-01-29

### Changed
- Patch version bump

## [5.6.98] - 2026-01-28

### Changed
- Patch version bump

## [5.6.97] - 2026-01-28

### Changed
- Patch version bump

## [5.6.96] - 2026-01-27

### Changed
- Patch version bump

## [5.6.95] - 2026-01-26

### Changed
- Patch version bump

## [5.6.94] - 2026-01-26

### Fixed
- Change Edit operation color from amber to yellow to distinguish from "Recent"

## [5.6.93] - 2026-01-26

### Fixed
- Monitor dashboard timestamp display issues ("Invalid Date" and "NaNm NaNs")
- Event history not loading on dashboard connect

## [5.6.92] - 2026-01-25

### Added
- Version-based migration system for automatic upgrades
- Migrations run automatically on first startup of new version
- Migration state tracked in ~/.claude-mpm/migrations.json

## [5.6.91] - 2026-01-25

### Added
- Async hook execution mode for non-blocking hook processing
- Migration script: `python -m claude_mpm.migrations.migrate_async_hooks`

### Changed
- Hooks now return `{"async": true}` for non-blocking execution

## [5.6.90] - 2026-01-25

### Added
- `--slack` CLI flag to start Slack MPM bot (similar to `--monitor`)

### Fixed
- Slack client lazy imports for config validation

## [5.6.89] - 2026-01-24

### Added
- TaskList session integration (pause captures tasks, resume displays them)
- SessionStart hook now reports pending task count
- npm publish script added

### Documentation
- Skills documentation updated

## [5.6.88] - 2026-01-23

### Added
- Slack MPM client scaffold for team collaboration
- Slack app setup script and documentation

## [5.6.87] - 2026-01-23

### Added
- Startup migration to automatically upgrade hooks to fast bash hook on upgrade

## [5.6.86] - 2026-01-23

### Fixed
- Hook installer now recognizes fast hook during upgrades (prevents duplicate entries)

## [5.6.85] - 2026-01-23

### Fixed
- Dashboard ToolsView now properly displays tool executions
- Dashboard FilesView stream filtering for "All Streams" option
- FileViewer content fetch with home directory security check
- Event correlation ID extraction for normalized events
- Svelte 5 reactivity with store subscriptions

### Added
- Fast bash hook script (52x speedup: 415ms → 8ms)
- Event categorization in broadcaster for proper routing

## [5.6.84] - 2026-01-23

### Changed
- Version bump for PyPI release

## [5.6.83] - 2026-01-23

### Changed
- Version bump for PyPI release

## [5.6.82] - 2026-01-23

### Added
- Added startup migration to clean duplicate user-level hooks

## [5.6.81] - 2026-01-23

### Fixed
- Fixed duplicate hook configuration causing "0/2 done" issue in agent execution
- Fixed nested data structures in monitor event handler - tool data now properly extracted

## [5.6.80] - 2026-01-23

### Fixed
- Monitor dashboard event parsing now correctly uses `subtype` field for actual events
- Updated OAuth command parser to use `google-workspace-mcp` naming convention
- env_loader.py now uses `Path.cwd()` for .env.local file resolution

## [5.6.79] - 2026-01-23

### Added
- OAuth auto-detection of credentials and automatic MCP configuration on setup
- `@instance` prefix support for slash commands

### Fixed
- Resolved Commander REPL message handling issues

## [5.6.78] - 2026-01-23

### Changed
- `oauth setup workspace-mcp` now auto-configures .mcp.json
- Renamed google-workspace-mpm to google-workspace-mcp

## [5.6.77] - 2026-01-23

### Changed
- Enhanced migration visibility with startup banner integration
- Added verbose before/after output during migration execution

### Documentation
- Added comprehensive startup migrations guide (`docs/features/startup-migrations.md`)
- Updated README with Automatic Migrations section under Key Features
- Documented migration system visibility: users only see messages when migrations actually apply

## [5.6.76] - 2026-01-23

### Added
- Startup migrations system for automatic config fixes on first run after update
  - Migration registry pattern with version tracking in ~/.claude-mpm/migrations.yaml
  - Non-blocking on failure (logs warning, continues startup)
- First migration: v5.6.76-cache-dir-rename
  - Renames remote-agents/ to agents/ in cache directory
  - Updates configuration.yaml if needed

## [5.6.75] - 2026-01-23

### Changed
- Moved mpm-session-pause and mpm-session-resume from RECOMMENDED to REQUIRED_PM_SKILLS tier

## [5.6.74] - 2026-01-23

### Added
- Added mpm-session-pause to RECOMMENDED_PM_SKILLS for proper deployment

### Fixed
- Skip background services in headless mode with --resume flag (ported from the-original-body/claude-mpm#9)

## [5.6.73] - 2026-01-23

### Changed
- Research agent updated with Google Workspace MCP integration

## [5.6.72] - 2026-01-23

### Added
- `/oauth` command for browser-based OAuth authentication in REPL
- Integrated Google Workspace MCP server (`google-workspace-mcp`)
  - Gmail search and message content retrieval
  - Google Calendar event listing
  - Google Drive file search and content access
- Encrypted token storage with system keychain integration

## [5.6.71] - 2026-01-23

### Fixed
- pass _get_prompt function to prompt_async instead of calling it
  - Allows prompt to update when display is invalidated after connecting
  - Prompt now shows connected instance name (e.g., "Commander (duetto)>")

## [5.6.70] - 2026-01-23

### Added
- bottom_toolbar spinner for Commander REPL using prompt_toolkit's native features
  - Replaces print-based spinner with cleaner UI
  - Spinner updates in toolbar below prompt
  - 100ms frame rate for smooth animation
  - No intrusive terminal output during startup wait

## [5.6.69] - 2026-01-22

### Fixed
- replace sys.stdout.write with print in spinner to work with patch_stdout

## [5.6.68] - 2026-01-22

### Fixed
- clear spinner line before printing prompt in REPL startup

## [5.6.67] - 2026-01-22

### Fixed
- update spinner to use carriage return for in-place updates instead of printing new lines
- clarify prompt shows connected session name (already implemented)

## [5.6.66] - 2026-01-22

### Fixed
- ensure background ready detection always runs

## [5.6.65] - 2026-01-22

### Changed
- bump: version 5.6.65

## [5.6.64] - 2026-01-22

### Changed
- bump: version 5.6.64

## [5.6.63] - 2026-01-22

### Changed
- bump: version 5.6.63

## [5.6.62] - 2026-01-22

### Changed
- bump: version 5.6.62

## [5.6.61] - 2026-01-22

### Changed
- bump: version 5.6.61

## [5.6.60] - 2026-01-22

### Changed
- bump: version 5.6.60

## [5.6.59] - 2026-01-22

### Changed
- bump: version 5.6.59

## [5.6.58] - 2026-01-22

### Changed
- bump: version 5.6.58

## [5.6.57] - 2026-01-22

### Changed
- bump: version 5.6.57

## [5.6.56] - 2026-01-22

### Changed
- bump: version 5.6.56

## [5.6.55] - 2026-01-22

### Changed
- bump: version 5.6.55

## [5.6.54] - 2026-01-22

### Changed
- bump: version 5.6.54

## [5.6.53] - 2026-01-22

### Changed
- bump: version 5.6.53

## [5.6.52] - 2026-01-22

### Fixed
- fix: Commander startup wait no longer spams console
  - Simplified to print once at start and once when ready
  - No more ANSI escape code issues or duplicated output
- fix: Suppress httpx INFO logging in Commander CLI
  - Added httpx/httpcore log level suppression
- fix: Add claude-mpm ready detection patterns
  - MPM now detected as ready via MPM-specific output patterns
  - Detects: "MPM initialized", "SessionStart hook success", etc.

## [5.6.51] - 2026-01-22

### Fixed
- fix: Commander REPL now returns control immediately during instance startup
  - `/register` and `/start` no longer block waiting for instance ready
  - Background task tracks startup progress and auto-connects when ready
  - Status shows above prompt with 🚀 icon (e.g., `🚀 [myapp] Starting up... (5s)`)
  - Truly async event-driven model - can issue other commands while waiting

## [5.6.50] - 2026-01-22

### Fixed
- fix: `/start <path>` now creates worktrees like `/register`
  - Previously `/start <path>` bypassed worktree creation
  - Now uses `register_instance()` which creates proper git worktrees
  - Updated help text to document worktree behavior
  - Shows worktree info when starting instances

## [5.6.49] - 2026-01-22

### Added
- feat: Async event-driven command model with pending request tracking
  - Non-blocking command dispatch (cursor returns immediately)
  - Pending requests shown above cursor with status icons
  - Responses appear above cursor when ready
  - Can continue issuing commands while waiting

## [5.6.48] - 2026-01-21

### Added
- feat: Add animated spinner while waiting for instance ready
  - Shows spinning animation with elapsed time counter
  - Displays checkmark on success, warning symbol on timeout

## [5.6.47] - 2026-01-21

### Fixed
- fix: Remove invalid --dangerously-skip-permissions flag from mpm framework
  - The --dangerously-skip-permissions flag is only valid for 'claude' CLI, not 'claude-mpm'
  - This was causing startup issues in certain configurations
- fix: Add wait_for_ready() method and instance ready tracking
  - Prevents messages being sent before instance is fully initialized
  - Improves reliability of inter-agent communication
- fix: Add more ready detection patterns for Claude CLI startup
  - Better detection of when Claude CLI is ready to accept input
  - Reduces race conditions during instance initialization

## [5.6.46] - 2026-01-21

### Added
- feat: Add WorktreeManager for git worktree session isolation
- feat: Extend RegisteredInstance with worktree tracking fields
- feat: Integrate worktree creation into instance registration
- feat: Add /close command and unify @name/(name) syntax
- feat: Add autocomplete for slash commands and instance names

### Fixed
- fix: MPM framework uses claude-mpm command
- fix: Use tmux new-window to avoid 'no space for new pane' error
- fix: Show instance name in prompt when ready
- fix: Emit events to subscribers for ready detection

## [5.6.45] - 2026-01-21

### Added
- feat: Add RAG-powered capabilities search to Commander
- feat: Add intent detection for greetings and capability queries

## [5.6.44] - 2026-01-21

### Changed
- chore: clean up root directory, move docs to proper locations
- chore: update ruff pre-commit to v0.14.8 and fix formatting

## [5.6.43] - 2026-01-21

### Fixed
- fix: Add missing httpx dependency for commander
  - httpx is required by the commander module but was not listed as a dependency
  - Caused ImportError when the package was installed fresh

## [5.6.42] - 2026-01-21

### Changed
- chore: patch version bump for PyPI release

## [5.6.41] - 2026-01-20

### Fixed
- fix: add early logging suppression to prevent REPL pollution
  - Added logging suppression at the very top of hook_handler.py before any other imports
  - Prevents StreamingHandler's carriage returns from polluting Claude Code's REPL output
  - Fixes the repeated status lines in Claude Code terminal output

## [5.6.40] - 2026-01-20

### Fixed
- fix: suppress RuntimeWarning to prevent REPL pollution
  - Added warnings.filterwarnings at module level before other imports
  - Suppresses RuntimeWarning from frozen runpy during hook execution
  - Prevents extra whitespace from appearing in Claude Code terminal

## [5.6.39] - 2026-01-20

### Added
- feat: add direct Python entry point for faster hook execution
  - Added `claude-hook` console script entry point in pyproject.toml
  - Updated installer to prefer entry point over bash wrapper (~400ms faster)
  - Falls back to bash script for development installs
  - Status now shows `using_entry_point` and `deployment_type`

## [5.6.38] - 2026-01-20

### Added
- feat: add detailed hook installation output
  - Show cleanup status: "Cleaning user-level hooks... (removed)" or "(none found)"
  - Show hook count: "Installing project hooks... 7 hooks configured"
  - Added `_count_installed_hooks()` helper to count configured hooks

## [5.6.37] - 2026-01-20

### Changed
- refactor: consolidate startup deployment and clean up SessionStart
- Consolidated hook cleanup, hook reinstall, and agent sync into single `sync_deployment_on_startup()` function in startup.py
- Removed autotodos and initialization logic from SessionStart handler
- SessionStart now only does lightweight event monitoring
- Hook cleanup removes stale `~/.claude/hooks/claude-mpm/` on MPM startup
- Hook reinstall updates `.claude/settings.local.json` on MPM startup

## [5.6.36] - 2026-01-19

### Fixed
- fix(hook_manager): run hook handler as module (`python -m`) instead of script to fix "attempted relative import with no known parent package" errors

## [5.6.35] - 2026-01-19

### Changed
- chore: patch version bump for PyPI release

## [5.6.34] - 2026-01-19

### Changed
- chore: patch version bump for PyPI release

## [5.6.33] - 2026-01-19

### Changed
- chore: patch version bump for PyPI release

## [5.6.32] - 2026-01-19

### Fixed
- fix(hooks): hook installer now properly MERGES with existing hooks instead of overwriting them
- feat(hooks): kuzu-memory hooks and claude-mpm hooks can now coexist correctly
- refactor(hooks): add `is_our_hook()` and `merge_hooks_for_event()` helper functions

## [5.6.31] - 2026-01-19

### Fixed
- fix(hooks): deploy hooks to project-level settings only - changed from `~/.claude/settings.json` to `{project}/.claude/settings.local.json`
- fix(tests): update hook format expectations from `{"action": "continue"}` to `{"continue": true}`

## [5.6.30] - 2026-01-19

### Fixed
- fix(hooks): use correct JSON response format for Claude Code - changed from {action: continue} to {continue: true}

## [5.6.29] - 2026-01-19

### Fixed
- fix(hooks): default DEBUG to false in all hook modules - fixes REPL pollution from debug logging

## [5.6.28] - 2026-01-19

### Fixed
- fix(startup): add TTY detection to all progress messages - prevents REPL pollution in Claude Code

## [5.6.27] - 2026-01-19

### Fixed
- fix(deploy): disable user-level command deployment - project-level skills are now the only source, old commands cleaned up automatically

## [5.6.26] - 2026-01-19

### Fixed
- fix(startup): remove blank line printing in non-TTY mode - eliminates REPL pollution from newline fallbacks

## [5.6.25] - 2026-01-19

### Fixed
- fix(logging): preserve FileHandlers in LoggerFactory.initialize() - prevents log messages leaking to stderr during hook execution

## [5.6.24] - 2026-01-19

### Fixed
- fix(output-style): treat 'default' as no preference in deployer - ensures Claude MPM style is activated on deployment

## [5.6.23] - 2026-01-19

### Fixed
- fix(startup): add TTY detection for progress clearing - prevents CR characters from appearing in Claude Code REPL

## [5.6.22] - 2026-01-19

### Fixed
- fix(skills): include core 'mpm' skill in discovery filter - the startup deployment was skipping 'mpm' because filter required hyphen

## [5.6.21] - 2026-01-19

### Changed
- chore: index cleanup and rebuild for mcp-vector-search

## [5.6.20] - 2026-01-19

### Added
- feat(network): centralize port configuration with service-specific defaults
- feat(commander): add instance management features (rename, close, disconnect)

### Changed
- chore: index cleanup and rebuild for mcp-vector-search

### Fixed
- fix(commander): skip signal handlers when running in background thread

### Documentation
- docs: add MPM Commander vision and architecture document

### Tests
- test(commander): add instance management tests

## [5.6.19] - 2026-01-18

### Fixed
- Remove redundant setup_agents calls

## [5.6.18] - 2026-01-18

### Fixed
- Fix deployment state path mismatch

## [5.6.17] - 2026-01-18

### Fixed
- Fix duplicate agent deployment after sync

## [5.6.16] - 2026-01-18

### Changed
- Move deployment state to .claude-mpm directory

## [5.6.15] - 2026-01-18

### Fixed
- Agent redeployment on every startup

## [5.6.14] - 2026-01-18

### Added
- **Commander full-cycle work execution** - Complete autonomous work execution with API integration
  - POST /api/events endpoint for hook event handling
  - Autonomous work pickup and execution in daemon main loop
  - python-dotenv auto-loading via env_loader.py
  - FastAPI app.state for shared work queue state
  - Project ID parameter support in registry
- **Multi-runtime adapter architecture** - Support for multiple AI coding assistants
  - ClaudeCodeAdapter: Full capabilities (agents, hooks, skills, monitoring)
  - AuggieAdapter: MCP tools and agent delegation support
  - CodexAdapter: Limited capabilities (no agents yet)
  - MPMAdapter: Full MPM feature support
  - AdapterRegistry with auto-detection and priority-based selection

### Fixed
- Work endpoint error handling (404 vs 500 for missing projects)

### Note
**Commander is in ALPHA status.** The multi-project orchestration system is functional but still under active development. APIs may change.

## [5.6.13] - 2026-01-18

### Added
- **agentskills.io specification support** - Skills now conform to the agentskills.io spec for cross-platform compatibility (Claude Code, VS Code Copilot, OpenCode)
- New spec fields: `license`, `compatibility`, `metadata`, `allowed-tools`
- Backward compatible - existing skills work without changes

## [5.6.12] - 2026-01-17

### Fixed
- **Auto-pause integration** - Wired up auto-pause in event handlers (#220)

## [5.6.11] - 2026-01-17

### Added
- **BlockManager** - Automatic blocking/unblocking for commander operations (#177, #178)
- **ResponseManager** - Centralized response handling for commander (#177)
- **BlockManager integration** - Integrated with RuntimeMonitor and EventHandler

## [5.6.10] - 2026-01-17

### Fixed
- **PM browser tool delegation** - Added claude-in-chrome and playwright to forbidden tools, must delegate to web-qa (#214)

## [5.6.9] - 2026-01-17

### Fixed
- **Commander tmux pane exhaustion** - Returns HTTP 409 with helpful message instead of 500 (#209)

## [5.6.8] - 2026-01-17

### Fixed
- **Import paths** (#197) - Removed `src.` prefix from import paths for cleaner module structure

### Added
- **Private repository support** (#208) - Added token authentication for private skill repositories

## [5.6.7] - 2026-01-17

### Fixed
- **Output style test** - Updated test for renamed file
- **Hooks auto-fix** - Fixed status line for output style schema mismatch

## [5.6.6] - 2026-01-17

### Fixed
- **Lazy yaml import for hooks** (#211) - Performance improvement by deferring yaml import
- **uv run --directory flag** (#212) - Correct uv command usage
- **PM core skills always deployed** (#181) - Deployment consistency improvements
- **Private repo authentication** (#182) - GitHub access for private repositories
- **--all flag for deploy-github** (#184) - Better deployment control
- **Category validation warnings** (#185) - Cleaner console output
- **Debug logging for skill discovery** (#186) - Enhanced troubleshooting

## [5.6.5] - 2026-01-16

### Changed
- **Hook logging consolidation** - Consolidated logging with _log() helper and fixed bandit nosec placement

## [5.6.4] - 2026-01-16

### Fixed
- **SessionStart hook error** - Fixed DEBUG default mismatch in event_handlers.py
- **Logging cleanup** - Removed all remaining stderr writes in event_handlers.py

## [5.6.3] - 2026-01-16

### Fixed
- **Comprehensive logging suppression at startup** - Cleaner console output
- **Hook RuntimeWarning suppressed** - No more noise during hook initialization
- **Stop handler stderr fixed** - Proper error stream handling

## [5.6.2] - 2026-01-16

### Fixed
- **Path resolution**: Installed packages no longer use dev paths
- **Logging**: INFO logs suppressed by default

## [5.6.1] - 2026-01-16

### Added
- **🧪 ALPHA: MPM Commander** - Multi-project orchestration system for autonomous AI coordination
  - Interactive multi-project management with tmux integration
  - Claude Code runtime adapter with idle/error/question detection
  - Project registry with state machine (IDLE, WORKING, BLOCKED, PAUSED, ERROR)
  - Event queue and inbox system for cross-project coordination
  - OpenRouter LLM integration for autonomous decision-making
  - Chat interface CLI with streaming responses
  - ⚠️ **Experimental** - API subject to change
  - Documentation: `docs/commander/`

### Fixed
- **Skills sync no longer deletes custom user skills** - Only removes MPM-managed skills not in configuration; preserves user-created skills

## [5.6.0] - 2026-01-16

### Changed
- Minor version bump for new features and improvements

## [5.5.2] - 2026-01-13

### Changed
- Patch version bump for package publication

## [5.5.1] - 2026-01-12

### Changed
- Patch version bump for package publication

## [5.5.0] - 2026-01-11

### Added
- **Skill-Based Commands**: Convert 12 MPM slash commands to Claude Code 2.1.3+ user-invocable skills
  - Tier 1 (Required): mpm, mpm-init, mpm-status, mpm-help, mpm-doctor
  - Tier 2 (Recommended): mpm-config, mpm-ticket-view, mpm-session-resume, mpm-postmortem
  - Tier 3 (Optional): mpm-monitor, mpm-version, mpm-organize
- **Tiered Skill Deployment**: PMSkillsDeployerService now supports minimal/standard/full deployment tiers
- **Version Gating**: MIN_SKILLS_VERSION = "2.1.3" for user-invocable skills support

### Changed
- **Claude Code Requirement**: Updated minimum version from v2.0.30 to v2.1.3
- **Legacy Commands Deprecated**: All command files in src/claude_mpm/commands/ now marked deprecated

### Fixed
- **Bandit Warnings**: Added nosec comments for intentional subprocess and try/except patterns

## [5.4.106] - 2026-01-11

### Fixed
- **Hook Stdout Fix**: Resolve systemic hook failures across all projects
  - Add `flush=True` to all JSON print statements in hook_handler.py (5 locations)
  - Remove duplicate JSON output from hook_wrapper.sh fallback logic
  - Redirect all 60 click.echo() calls to stderr in hook_errors.py

## [5.4.105] - 2026-01-10

### Fixed
- **Logging Fix**: Fix stderr logging to use sys.stderr instead of sys.stdout

## [5.4.104] - 2026-01-10

### Fixed
- **Hook Error Fix**: Pass working_dir parameter to autotodos to fix hook errors

## [5.4.103] - 2026-01-10

### Changed
- Patch version bump for package publication

## [5.4.102] - 2026-01-09

### Changed
- Patch version bump for package publication

## [5.4.101] - 2026-01-09

### Changed
- Patch version bump for package publication

## [5.4.100] - 2026-01-08

### Changed
- Patch version bump for package publication

## [5.4.99] - 2026-01-08

### Changed
- Patch version bump for package publication

## [5.4.98] - 2026-01-08

### Changed
- Patch version bump for package publication

## [5.4.97] - 2026-01-08

### Changed
- **BREAKING**: Renamed "Founders Mode" to "Research Mode" to better reflect its purpose as a codebase research tool
  - Renamed `CLAUDE_MPM_FOUNDERS_OUTPUT_STYLE.md` to `CLAUDE_MPM_RESEARCH_OUTPUT_STYLE.md`
  - Updated output style from "Claude MPM Founders" to "Claude MPM Research"
  - Updated all documentation to use "Research Mode" terminology
  - Maintained backward compatibility: "founders" style type still works as alias (deprecated)
  - Research Mode is now positioned as a tool for founders, PMs, AND developers conducting codebase research

### Fixed
- **Hook Connection Manager**: Removed async emission path to fix "Event loop is closed" errors

## [5.4.93] - 2026-01-07

### Fixed
- **Monitor Hook Events**: Fixed unsourced hook events showing as "hook hook" in dashboard
- **Dashboard Tools/Files**: Restored tools and files display by adding 'tool_event' listener
- **Agent Deployment**: Removed duplicate memory-manager.md agent (superseded by memory-manager-agent)

### Changed
- **Agent Config**: Updated required agent to use specific memory-manager-agent ID

## [5.4.92] - 2026-01-07

### Fixed
- **Dashboard Event Categorization**: Improved event categorization and display logic
- **Dashboard File Tree**: Enhanced file tree visualization

### Added
- **Documentation**: Added debugging session commit control strategies guide
- **Documentation**: Added Hello World quickstart guide
- **Documentation**: Added /mpm-init re-run workflow guide
- **Dashboard**: Added "All Streams" filter option
- **Doctor Command**: Enhanced troubleshooting output with severity levels and explanations

### Changed
- **Dashboard**: Fixed project default handling
- Archived unused test assets

## [5.4.89] - 2026-01-07

### Changed
- Patch version bump for package publication

## [5.4.88] - 2026-01-06

### Changed
- Patch version bump for package publication

## [5.4.87] - 2026-01-06

### Changed
- Patch version bump for package publication

## [5.4.86] - 2026-01-06

### Added
- **Dashboard Radial Tree View**: D3.js radial tree visualization for modified files
  - Project root at center with files radiating outward
  - Auto-detects project root from file paths
  - Color-coded by operation (read/write/edit)
  - Interactive node and label selection

### Fixed
- **SubagentStart Event Handling**: Dedicated handler for proper agent type extraction
  - Fixed agent conflation in dashboard Agents view
  - Research agents now appear correctly in hierarchy
  - Multiple same-type agents show as distinct nodes
- **Unknown Agent Type**: Default to "pm" for unidentified SubagentStop events

## [5.4.85] - 2026-01-05

### Changed
- Patch version bump for package publication

## [5.4.84] - 2026-01-05

### Changed
- Patch version bump for package publication

## [5.4.83] - 2026-01-05

### Fixed
- **Agent Deployment**: Respect configuration.yaml enabled agents list
  - Agent deployment reconciler now properly filters agents based on configuration
  - Prevents accidental deployment of all agents when only subset configured
  - Ensures alignment between configured and deployed agent sets

### Added
- **Bug Reporting System**: Integrated bug reporting for MPM-managed repositories
  - `/bugs report` command to report bugs in MPM-managed repos
  - `/bugs open` command to view open bug issues
  - Automatic labeling and formatting for bug tracking
  - GitHub integration for issue creation and management

## [5.4.82] - 2026-01-05

### Changed
- Project housecleaning and file reorganization

## [5.4.81] - 2026-01-05

### Changed
- Patch version bump for package publication

## [5.4.80] - 2026-01-05

### Fixed
- Fixed case-sensitivity bug in output style validation that caused error when using "JSON" instead of "json"

## [5.4.79] - 2026-01-04

### Changed
- Patch version bump for package publication

## [5.4.78] - 2026-01-04

### Added
- **Required Agents Feature**: New `required: true` frontmatter property for agent definitions
  - Agents marked as required are always deployed, regardless of configure.yaml
  - Ensures critical agents (e.g., base instructions) are always available
  - Deployment reconciler respects required flag

## [5.4.77] - 2026-01-02

### Fixed
- Bug fixes and stability improvements

## [5.4.76] - 2026-01-02

### Changed
- Patch version bump for package publication

## [5.4.75] - 2026-01-02

### Changed
- Patch version bump for package publication

## [5.4.74] - 2026-01-02

### Changed
- Patch version bump for package publication

## [5.4.73] - 2026-01-02

### Changed
- Patch version bump for package publication

## [5.4.72] - 2026-01-02

### Added
- **Agent/Skill Deployment Model**: Explicit configure.yaml-driven deployment system
  - New `agents.enabled` config for explicit agent deployment list
  - New `skills.enabled` config for manual skill deployment list
  - Agent skill dependencies auto-included from frontmatter
  - Deployment reconciler for agents and skills with `--show-only` dry-run mode
  - Skill selector with topic grouping (similar to agent selector)
  - Commands: `claude-mpm agents reconcile`, `claude-mpm skills select`, `claude-mpm skills reconcile`

### Fixed
- **UV Installation**: Use `uv pip install --python` instead of broken command
- **Pydantic v2 Compatibility**: Use `field_validator` and `model_dump` instead of deprecated APIs

## [5.4.64] - 2025-12-30

### Fixed
- **Output Style Deployment**: Deploy styles to user-level directory for global availability
  - Changed deployment target from project `.claude/` to `~/.claude/settings/output-styles/`
  - Claude Code reads output styles from user-level directory, not project-level
  - Ensures styles are available globally across all projects

## [5.4.63] - 2025-12-30

### Fixed
- **Output Style Auto-Update**: Compare file sizes to detect updated styles
  - Previously only checked if output style files exist
  - Now compares file sizes between source and deployed versions
  - Automatically redeploys when package includes updated styles
  - Ensures users get latest style updates after package upgrade

## [5.4.62] - 2025-12-30

### Fixed
- **Teacher Output Style**: Add YAML frontmatter to make style discoverable
  - Added `name` and `description` frontmatter to CLAUDE_MPM_TEACHER_OUTPUT_STYLE.md
  - Claude Code requires YAML frontmatter to recognize output style files
  - Style now appears in `/output-style` selector

## [5.4.61] - 2025-12-30

### Fixed
- **PM Skills Packaging**: Include PM skills subdirectories in wheel distribution
  - Pattern `skills/bundled/**/*.md` already correctly includes recursive .md files
  - This version bump documents the fix is already in place
  - Resolves "PM skills: 0 deployed" when using pip-installed package
  - Skills in `skills/bundled/pm/*/SKILL.md` now properly packaged in wheel

## [5.4.60] - 2025-12-30

### Fixed
- **Agent Frontmatter**: Preserve skills field during agent deployment
  - Fixed: `build_agent_markdown` was stripping skills field from agent templates
  - This caused v5.4.59's selective skill deployment to deploy 0 skills
  - Skills list from template data now written to deployed agent frontmatter
  - Resolves issue where deployed agents had no skills frontmatter

## [5.4.59] - 2025-12-30

### Fixed
- **Skill Deployment Logic**: Empty skill list now deploys 0 skills instead of ALL
  - Fixed: `[]` (empty list) was falsy → converted to `None` → deployed ALL 119 skills
  - Now correctly checks `if skills_to_deploy is not None` instead of truthiness
  - When no agents have `skills:` frontmatter, zero skills are deployed
- **PM Skills Display**: Fixed "PM skills: 0 deployed" showing incorrectly
  - Added missing `skill_count` attribute to `VerificationResult` dataclass
  - Now correctly shows count of verified PM skills

## [5.4.58] - 2025-12-30

### Fixed
- **Agent Deployment**: Use content comparison instead of mtime
  - Previous mtime-based comparison missed updates when cache had older timestamps
  - Now compares file content directly to detect any changes
  - Ensures agent frontmatter updates (like skills field) are properly deployed

## [5.4.57] - 2025-12-30

### Changed
- **Skill Deployment**: Move from static mapping to agent frontmatter
  - Each agent now declares skills in frontmatter (`skills:` field)
  - Agents without skills frontmatter get zero skills deployed
  - Deprecated `skill_to_agent_mapping.yaml` - no longer affects deployment
  - Updated all 43 agents in claude-mpm-agents repo with skills frontmatter
  - Reduces deployed skills to only what each agent explicitly needs

## [5.4.56] - 2025-12-30

### Fixed
- **Skills Status Display**: Add skills status matching agents format
  - Display '✓ Skills: X deployed / Y cached' during startup
  - Track and report removed orphaned skills count
  - Enhanced logging for agent scan and cleanup debugging
  - Show removed count in cleanup output

## [5.4.55] - 2025-12-30

### Fixed
- **Skill Deployment Location**: Skills now deploy ONLY to project-level `.claude/skills/`
  - Removed user-level deployment to `~/.claude/skills/`
  - Keeps skills isolated per project
- **Skill Cleanup**: Always run agent scanning to enable orphan removal
  - Removed conditional that skipped scanning when using cached skills
  - Ensures `agent_referenced` is always populated for cleanup

## [5.4.54] - 2025-12-30

### Fixed
- **Skill Orphan Detection**: Fixed mappings that caused over-deployment
  - Removed generic agents (web-ui, data-engineer, security) from language-specific skills
  - Phoenix/Elixir skills now ONLY map to phoenix-engineer
  - Golang skills now ONLY map to golang-engineer
  - PHP/WordPress skills now ONLY map to php-engineer
  - Reduces skill count from ~97 to ~50-60 for typical deployments

### Added
- **Auto Pre-commit Hooks**: `claude-mpm init` automatically installs security hooks
  - Installs pre-commit and detect-secrets if missing
  - Sets up hooks without manual user steps

## [5.4.53] - 2025-12-29

### Added
- **Security Scanning**: Comprehensive secret detection improvements
  - Added detect-secrets pre-commit hook
  - Enhanced .gitignore with MCP/credential patterns
  - Security checks during `claude-mpm init`
  - SECURITY.md with incident response procedures
  - Scans for OpenRouter, Anthropic, OpenAI API key patterns

## [5.4.52] - 2025-12-29

### Fixed
- **Skill Cleanup**: Auto-populate agent_referenced when empty to enable orphan cleanup
  - Scans deployed agents to determine required skills
  - Actually removes orphaned skills from ~/.claude/skills/
  - Fixes issue where unneeded skills persisted after mapping changes

## [5.4.51] - 2025-12-29

### Changed
- **Skill Mappings**: Removed framework-specific skills from generic agents
  - Generic agents (engineer, qa, ops) no longer receive framework-specific skills
  - Phoenix, WordPress, Django, etc. skills only go to their specialized agents
  - Reduces skill bloat significantly for users with fewer specialized agents

### Added
- **Dashboard Markdown Rendering**: Markdown files now render with proper formatting
  - Headers, lists, tables, code blocks with syntax highlighting
  - Mermaid diagram support for flowcharts, sequence diagrams, etc.
  - Theme-aware styling (dark/light mode)

## [5.4.50] - 2025-12-29

### Fixed
- **Agent Count Display**: Fixed cache cleanup deleting all agents due to path counting bug
  - Changed from absolute to relative path counting for nested structure detection
  - Cache now properly preserved during agent sync
  - Display correctly shows "X deployed / Y cached"
- **Skill Deployment**: Exclude generic "engineer" agent when specialized engineers exist
  - Prevents over-deployment of skills mapped to generic agent

## [5.4.49] - 2025-12-29

### Fixed
- **Selective Skill Deployment**: Fixed path matching for agent-referenced skills
  - Use configuration-based skill discovery instead of agent frontmatter scanning
  - Added path normalization to match skills by source_path
  - Skills now correctly deployed as individual directories
  - Fixed "0/108 skills" bug caused by path format mismatch

## [5.4.48] - 2025-12-29

### Changed
- **Skills Auto-Linking**: Selective deployment is now the default behavior
  - Removed --all-skills flag (no longer needed)
  - Enhanced cleanup runs on every deployment
  - Skills are automatically linked based on agent dependencies

## [5.4.47] - 2025-12-29

### Fixed
- **Agent Count Display**: Fixed agent count display bug showing 0 cached instead of correct count
- **PM Delegation**: Added PM delegation enforcement with Circuit Breakers #1-5 and vector search protocol

## [5.4.46] - 2025-12-29

### Fixed
- **Agent Exclusion**: Fixed agent exclusion logic to handle all name variations consistently
  - Improved normalization to handle kebab-case, snake_case, and spaces
  - Ensures excluded agents never appear in deployment regardless of naming format

## [5.4.45] - 2025-12-29

### Fixed
- **Agent Exclusion Matching**: Normalize agent names for consistent exclusion filtering
  - Handles "Dart Engineer", "dart_engineer", and "dart-engineer" as the same agent
  - Added `_normalize_agent_name()` helper function for name normalization
  - Excluded agents now properly filtered from deployment
- **Model Field Optional**: Stop defaulting to `model: sonnet` in deployed agents
  - If source agent has no model field, deployed agent also omits model field
  - Allows Claude Code to use its own default model
  - Fixed in agent_format_converter, agent_template_builder, async_agent_deployment, local_template_deployment
- **Duplicate Agent Entries**: Fixed duplicate agents appearing in configurator
  - Added deduplication logic to git_source_manager list_cached_agents()
  - Fixes memory-manager-agent appearing twice

## [5.4.44] - 2025-12-29

### Fixed
- **Agent Discovery**: Support nested `{owner}/{repo}/agents/` cache structure
  - Fixed RemoteAgentDiscoveryService to find agents in GitHub sync cache
  - Updated startup agent counting to support both flat and nested structures
  - Agents now correctly discovered and deployed to `.claude/agents/`
  - Fixes "29 deployed / 0 cached" but "/agents shows nothing" issue

## [5.4.43] - 2025-12-29

### Fixed
- **Dependencies**: Make kuzu-memory optional to avoid cmake build requirement
  - Users without cmake can now install claude-mpm without errors
  - Install kuzu-memory with: `pip install claude-mpm[memory]`
- **PM Skills**: Fix path resolution for installed packages

## [5.4.41] - 2025-12-29

### Changed
- **Version**: Patch version bump for release

## v5.4.96 (2026-01-07)

### Feat

- **autotodos**: wire delegation detector into hook pipeline
- **autotodos**: add delegation pattern detector
- **autotodos**: add POC for error-to-todo injection system

### Fix

- **autotodos**: correct event type model
- sync pyproject.toml version to 5.4.95

### Refactor

- **autotodos**: use event-driven architecture

## v5.4.95 (2026-01-07)

### Fix

- **release**: use twine instead of uv for PyPI publishing
- sync pyproject.toml version to 5.4.94

## v5.4.94 (2026-01-07)

### Fix

- **startup**: resolve 4 startup issues

## v5.4.93 (2026-01-07)

### Fix

- **monitor**: resolve unsourced hook events and missing tools in dashboard

## v5.4.92 (2026-01-07)

### Feat

- **doctor**: enhance troubleshooting output with severity and explanations
- **dashboard**: add All Streams filter and fix project default
- **dashboard**: fix event categorization, file tree enhancements

### Fix

- **dashboard**: improve event categorization and display
- add nosec annotations for bandit false positives
- sync pyproject.toml version to 5.4.91

## v5.4.91 (2026-01-07)

### Feat

- **banner**: add MPM skills count, clarify skills vs commands

### Fix

- **dashboard**: emit todo_updated events for proper tracking
- sync pyproject.toml version to 5.4.90

## v5.4.90 (2026-01-07)

### Feat

- framework improvements, dashboard fix, README reorganization
- extract tool usage guide to mpm-tool-usage-guide skill

### Fix

- **dashboard**: track all agents used in session instead of only last one
- ruff linting errors in validate_context_tracker.py

### Refactor

- extract session management to mpm-session-management skill
- rename PM skills to mpm-* and deploy to .claude/skills/

## v5.4.89 (2026-01-07)

### Fix

- **session**: add .md file pattern to SessionResumeHelper

## v5.4.88 (2026-01-06)

### Feat

- **pm**: strengthen localhost deployment verification rules

### Fix

- **scripts**: extract PyPI token from ~/.pypirc for uv publish

## v5.4.87 (2026-01-06)

### Feat

- **auto-pause**: implement automatic session pausing at 90% context
- **dashboard**: improve radial tree labels and interactions
- **dashboard**: add D3.js radial tree view for modified files
- **hooks**: default unknown agent_type to pm in SubagentStop

### Fix

- **dashboard**: remove radar pulse feature to fix Tree view freeze
- **dashboard**: fix Tree view infinite loop freeze
- **dashboard**: prevent Tree view freeze on file fetch errors
- **dashboard**: fix Agents tab display and add radar pulse to Files tree
- **dashboard**: fix Agents tab by using consistent namespace for events
- **security**: add nosec annotations for bandit warnings
- **dashboard**: use relative paths from project root in tree view
- **dashboard**: use direct x/y positioning for radial tree labels
- **dashboard**: rewrite radial tree with root at center
- **dashboard**: ensure radial tree labels are truly horizontal
- **hooks**: add dedicated SubagentStart handler with agent_type
- **dashboard**: reorder tabs and add agent debugging
- auto-deploy research output style on startup (formerly "founders")
- prefix unused skill_result variable with underscore

## v5.4.83 (2026-01-05)

### Feat

- add bug reporting system for MPM repositories

### Fix

- agent deployment now respects configuration.yaml settings

## v5.4.82 (2026-01-05)

## v5.4.81 (2026-01-05)

## v5.4.80 (2026-01-05)

### Fix

- correct output style name case-sensitivity

## v5.4.79 (2026-01-04)

## v5.4.78 (2026-01-04)

### Feat

- add required agents that are always installed

## v5.4.77 (2026-01-02)

### Fix

- handle FileNotFoundError when cwd doesn't exist

## v5.4.76 (2026-01-02)

### Feat

- add group selection for skill pattern groups
- add pattern detection for skill grouping in UI
- add spacebar toggle selection to skills management
- fix skills UI to show all skills grouped by category
- update skills management to show table like agents
- update skill selector UI to match agent selector
- simplify agent/skill deployment model and fix UV install
- add --force-sync flag to bypass ETag cache for agents/skills
- make selective skill deployment the default

### Fix

- correct config import for skills GitSkillSourceManager
- remove menu items and update skills table to match agents
- strengthen PM delegation enforcement to prevent direct source code reading
- deploy output styles to correct directory (~/.claude/output-styles/)
- resolve startup issues with cache, output styles, and dependency verification
- deploy output styles to user-level directory
- auto-update output styles when source changes
- add YAML frontmatter to teacher output style
- include PM skills subdirectories in package distribution
- preserve skills field in agent frontmatter during deployment
- **skills**: empty skill list deploys 0 skills, fix PM skills display
- **agents**: use content comparison instead of mtime for deployment
- **skills**: add skills status display and improve cleanup logging
- skill deployment to project-only and always run cleanup
- use dict iteration directly in test
- final linting fixes for tests
- resolve linting errors for safe-release-build
- skill orphan detection - reduce over-deployment by fixing mappings
- skill cleanup now auto-populates agent_referenced and removes orphans
- **skills**: auto-populate agent_referenced to enable orphan cleanup
- agent count display and skill deployment optimization
- selective skill deployment path matching
- agent count display and PM delegation enforcement
- add agent exclusion filtering to GitSourceSyncService
- **agents**: exclusion matching, model optional, duplicate entries
- **agents**: support nested {owner}/{repo}/agents/ cache structure

### Refactor

- unify TUI styling for agent and skill selectors
- condense output styles to ~4KB, move detail to PM skills
- move skill mappings from static YAML to agent frontmatter

## v5.4.43 (2025-12-29)

### Fix

- **deps**: make kuzu-memory optional to avoid cmake requirement

## v5.4.42 (2025-12-29)

### Fix

- **skills**: use package-relative path for bundled PM skills

## v5.4.41 (2025-12-29)

### Feat

- **startup**: auto-cleanup legacy agent cache directories
- **agents**: make model field optional for dynamic selection
- **profiles**: implement automatic profile-based agent/skill filtering
- add PM skills status display on startup
- add progress bar for PM skills deployment
- **pm-skills**: add PM skills deployment infrastructure
- populate PM skill files with extracted content
- add automatic log rotation to monitor daemon
- reinforce autonomous PM operation and fix logging levels

### Fix

- **profile**: use full enabled list for agent cleanup, not filtered
- **profile**: add agent cleanup to remove excluded agents
- **profile**: canonical_id matching + skill cleanup
- **profile**: add fuzzy matching for skill filtering
- **profile**: use Config.set() for singleton to enable agent filtering
- **profiles**: pass config to deploy_agents() for profile filtering
- **profiles**: auto-detect project root for profile loading
- **profiles**: support short skill names in profile filtering
- remove MCP service verification warning on startup
- add installed/total count summary to agent list display
- detect UV tool environments and use uv pip for installations
- apply default agents when scoring produces empty recommendations
- reinforce PM delegation rules and fix agent template references

### Refactor

- **commands**: optimize slash command content for 86% token reduction
- **pm-instructions**: consolidate with skill references
- **pm-instructions**: holistic cleanup reducing 313 lines (22%)

## v5.4.30 (2025-12-23)

### Fix

- use explicit conversion flag for error message (ruff RUF010)
- **dashboard**: add image display and project isolation

## v5.4.29 (2025-12-23)

### Fix

- include dashboard svelte-build in package data

## v5.4.28 (2025-12-23)

### Feat

- **dashboard**: add Agents tab with hierarchical agent tracking

## v5.4.27 (2025-12-23)

### Fix

- **dashboard**: improve stream selector and diff viewer UX

## v5.4.26 (2025-12-23)

### Feat

- **dashboard**: historical diff viewer with commit dropdown
- **dashboard**: show project name + session ID in Stream selector
- **dashboard**: add favicon with dashboard grid icon
- **dashboard**: add diff toggle to FileViewer

### Fix

- **dashboard**: fix working-directory API and favicon path
- **cache**: correct inflated agent count from stale repository files
- **dashboard**: convert Path.cwd() to string for API response
- **dashboard**: filename header and diff debug logging
- resolve linting issues for pre-publish checks
- **dashboard**: show filename in list, relative path in viewer
- **dashboard**: extract cwd from root level of events for project name
- **dashboard**: relative paths, git diff, theme-aware code, stream filtering
- **dashboard**: theme toggle and always-visible diff toggle
- **dashboard**: favicon route and git-based diff viewer
- **dashboard**: show diff toggle and add filename filter

## v5.4.24 (2025-12-23)

### Fix

- remove unused imports in monitor and socketio servers
- default test_mode to False for production PM enforcement
- add GET /api/file/read endpoint for file browser
- add missing base_agent.json to source directory
- add claude_event to dashboard relay whitelist
- clarify agent counting terminology (deployed vs cached)
- **dashboard**: remove custom slot for Svelte 5 compatibility
- **dashboard**: use explicit slot pattern for svelte-highlight
- **dashboard**: fix SSR-safe escapeHtml for Python/Svelte fallback

### Refactor

- **dashboard**: convert Files tab to session-specific touched files tracker
- **dashboard**: direct file browser instead of hook events
- **dashboard**: replace Shiki with svelte-highlight

## v5.4.23 (2025-12-23)

### BREAKING CHANGE

- Cache directory moved from ~/.claude-mpm/cache/remote-agents/
to ~/.claude-mpm/cache/agents/. Existing cache will be re-synced automatically.

### Feat

- **dashboard**: add git history display to FileViewer
- **agents**: add Proactive Code Quality Improvements to BASE_AGENT
- **pm**: implement ops agent consolidation and verification delegation

### Fix

- apply ruff linting fixes for pre-publish quality gate
- **dashboard**: use Shiki full bundle for Python/Svelte highlighting
- **dashboard**: fetch file content from server API instead of events
- **dashboard**: correct content extraction path for FileViewer
- **dashboard**: extract file content from nested event data structure
- **dashboard**: add type=hook check to files store extraction
- **dashboard**: files reload on source change + FileViewer layout
- **dashboard**: update static file serving for Svelte-only structure
- **dashboard**: preserve full event structure in HTTP POST handler
- **dashboard**: ensure events persist in history for new clients
- **dashboard**: correct file viewer schema to match backend format
- **dashboard**: enhance file content extraction with multi-path fallback
- **dashboard**: resolve file viewer data extraction mismatch

### Refactor

- **pm**: consolidate instructions + fix deepeval tests
- **agents**: standardize cache directory from remote-agents to agents

## v5.4.21 (2025-12-22)

### Feat

- **pm**: mandate Chrome DevTools MCP for browser verification
- **skills**: add user skill override via configuration.yaml
- **startup**: add skill statistics to progress display
- **skills**: implement selective skill deployment based on agent references
- **dashboard**: fix file tracking, viewer, and styling

### Fix

- resolve ruff linting errors for pre-publish gate

## v5.4.20 (2025-12-21)

### Feat

- expand /mpm-organize to full project organization
- refocus /mpm-organize on documentation-only organization

## v5.4.17 (2025-12-21)

### Feat

- add agent count summary to startup output

### Refactor

- remove redundant agent commands, consolidate into /mpm-configure

## v5.4.16 (2025-12-21)

### Feat

- add chrome-devtools-mcp auto-install on startup

## v5.4.14 (2025-12-20)

### Feat

- add engineer to core agents list

### Refactor

- remove auto gitignore rewriting, add config recommendation

## v5.4.13 (2025-12-20)

### Feat

- add UV tool and Homebrew detection for auto-upgrade

### Fix

- resolve linting issues for pre-publish quality gate
- prefix final unused stdout variable with underscore
- prefix all unused stdout variables with underscore in git_operations_service
- prefix unused stdout variable with underscore
- auto-recover from divergent branches in git sync
- add defensive error handling to hook event handlers
- add matcher field for UserPromptSubmit hook
- make memory_integration logging install-type-aware

### Refactor

- use runtime hooks for agent memory, add observability
- fix agent memory injection flow
- remove unused base_agent_loader infrastructure
- remove redundant CLI commands

## v5.4.39 (2025-12-28)

### Changed
- **Version**: Patch version bump for release

## v5.4.38 (2025-12-28)

### Fixed
- **Monitor Daemon**: Add automatic log rotation to prevent unbounded log growth
  - Uses RotatingFileHandler instead of FileHandler
## [5.4.40] - 2025-12-29

### Fixed
- Profile filtering now correctly excludes agents from deployment
- Pass config to deploy_agents() for profile filtering
- Auto-detect project root for profile loading
- Short skill names match full skill names in profile filtering

### Changed
- Optimized slash commands for 86% token reduction (25K → 3.5K tokens)

  - Backup files: 5 (25MB total max)
  - Consistent with project logging standards in logging_utils.py

## v5.4.37 (2025-12-28)

### Fixed
- **Agent List Display**: Add installed/total count summary to agent list
  - Shows "📊 Agents: XX Installed / YY Total" after table
  - Provides quick visibility into deployment status

## v5.4.36 (2025-12-28)

### Fixed
- **Dependency Installer**: Detect UV tool environments and use uv pip for installations
  - UV tool environments don't have pip module available
  - Detects UV environments via UV_TOOL_DIR variable or executable path
  - Uses 'uv pip install' instead of 'python -m pip install'
  - Fixes "No module named pip" error in UV tool installations

## v5.4.35 (2025-12-28)

### Fixed
- **Agent Recommender**: Apply default agents when scoring produces empty recommendations
  - Previously, default agents only applied when language was "unknown"
  - Now defaults apply for any empty result, including:
    - Language detected but no frameworks (score below threshold)
    - Unknown deployment environments
    - New/unsupported toolchains
  - Fixes auto-configuration failure on plain Python projects

## v5.4.34 (2025-12-25)

### Added
- **Testing**: Added 21 deepeval scenarios for PM instruction compliance
  - Circuit Breaker #9: User Delegation Detection (5 scenarios)
  - Autonomous Operation (5 scenarios)
  - Circuit Breaker #7: Verification Commands (4 scenarios)
  - Circuit Breaker #8: QA Gate (3 scenarios)
  - Research Gate Protocol (4 scenarios)
  - Total scenarios increased from 51 to 72 (41% increase)
  - Test coverage increased from ~75% to ~95%

## v5.4.33 (2025-12-25)

### Added
- **PM Instructions**: Added "Autonomous Operation Principle" section
  - PM now operates independently until ALL work is complete
  - 90% success threshold for upfront clarification only
  - Anti-patterns documented: no nanny coding, permission seeking, or partial completion

### Fixed
- **Agent Discovery Service**: Fixed misleading ERROR → WARNING for non-critical YAML parsing

## v5.4.32 (2025-12-25)

### Fixed
- **PM Instructions**: Added anti-pattern section to prevent PM from instructing users to run commands
  - Added "PM Must Never Instruct Users to Run Commands" anti-pattern section
  - Added Circuit Breaker #9 for user delegation detection
  - Ensures PM delegates to local-ops instead of telling users to run commands
- **Agent Capabilities**: Fixed 16 agent template_file references from .json to .md format

## v5.4.31 (2025-12-23)

### Changed
- **PM Instructions**: Holistic cleanup reducing 313 lines (22%)
  - Removed redundant sections and outdated patterns
  - Improved clarity and organization

## v5.4.30 (2025-12-23)

### Fixed
- **Dashboard**: FileViewer now displays images (PNG, JPG, GIF, SVG, WebP, etc.)
  - Backend returns base64 encoded images with MIME type
  - Image display with max-width constraints
- **Dashboard**: Added project isolation with filter dropdown
  - "Current Only" vs "All Projects" filter in header
  - Default to current project to prevent cross-project event mixing
  - Working directory-based filtering

## v5.4.29 (2025-12-23)

### Fixed
- **Dashboard**: Fixed PyPI package missing dashboard static files
  - Added `dashboard/static/svelte-build/**/*` to package-data in pyproject.toml
  - Ensures dashboard svelte-build files are included in PyPI distribution

## v5.4.28 (2025-12-23)

### Added
- **Dashboard**: New Agents tab with hierarchical agent tracking
  - PM → sub-agent hierarchy visualization
  - Agent type icons and formatted names
  - Tool call grouping (deduplicate same tool+file)
  - Stream activity highlighting (green dot for recent activity)
  - Tool call click-through to Tools tab details
  - User prompts, delegation prompts, and responses display
  - Todo lists with status indicators per agent
  - Work plans detection and display

## v5.4.27 (2025-12-23)

### Fixed
- **Dashboard**: Improved stream selector and diff viewer UX
  - Removed "All Streams" option from stream selector
  - Auto-select first/active stream when detected
  - Auto-display most recent diff when Changes view is selected
  - Consistent stream filtering across Files, Tools, Events tabs

## v5.4.26 (2025-12-23)

### Fixed
- **Dashboard**: Fixed working-directory API and favicon path issues
- **Dashboard**: Corrected inflated agent count from stale repository files in cache
- **Dashboard**: Fixed Path.cwd() conversion to string for API response compatibility
- **Dashboard**: Fixed filename header display and added diff debug logging
- **Dashboard**: Improved filename display in list view and relative path in viewer
- **Dashboard**: Enhanced project name extraction from event root level cwd

### Added
- **Dashboard**: Historical diff viewer with commit dropdown navigation

## v5.4.25 (2025-12-23)

### Fixed
- **Linting**: Resolved ruff linting issues in hook_handler and test files
- **Code Formatting**: Applied consistent formatting across codebase

## v5.4.24 (2025-12-23)

### Fixed
- **Code Quality**: Removed unused imports in monitor and socketio servers
- **Code Formatting**: Applied consistent formatting to server files

## v5.4.23 (2025-12-23)

### Changed
- **Agent Cache Standardization**: Unified cache directory structure
  - Renamed `~/.claude-mpm/cache/remote-agents/` to `~/.claude-mpm/cache/agents/`
  - Automatic migration on first use (no manual intervention required)
  - Updated all documentation to reflect new path
  - Consistent naming across codebase

- **PM Instructions Consolidation**: Streamlined PM agent instructions (31.9% reduction)
  - Reduced from 1,725 to 1,175 lines
  - QA verification consolidated to single dedicated section
  - Agent delegation converted to tabular format for clarity
  - Read Tool hierarchy explicitly defined
  - Improved LLM parsing and decision-making

- **BASE_AGENT Imperatives**: Added proactive code quality improvements section
  - **Search Before Implementing**: Mandatory existing code search before creating new implementations
  - **Mimic Local Patterns**: Follow established project naming conventions and patterns
  - **Suggest Improvements**: Proactive quality suggestions (ask before implementing)
  - Standardized reporting format for findings

### Added
- **PM Instructions Testing**: Comprehensive DeepEval test infrastructure
  - 10 tests for PM verification gate behavior (`test_pm_verification_gate.py`)
  - 7 tests for ticketing delegation behavior (`test_pm_behavior_validation.py`)
  - TicketingDelegationMetric now uses strict binary scoring (pass/fail)
  - Total of 17 PM behavior tests ensuring compliance

- **Documentation**:
  - Created `docs/reference/pm-instructions.md` - Comprehensive PM instructions reference
  - Documents consolidated structure, testing methodology, and BASE_AGENT integration
  - Includes migration notes for users of pre-v5.4.23 versions

### Fixed
- **Documentation**: Updated all cache path references (~30+ updates across 9 files)
  - Core: `README.md`, `docs/deployment/README.md`, `docs/architecture/overview.md`
  - Guides: `docs/guides/agent-synchronization.md` (13 path updates)
  - Developer: `docs/developer/internals/agent-sync-internals.md`, `docs/developer/collection-based-agents-quick-start.md`
  - Agents: `docs/agents/remote-agents.md`, `docs/developer/agent-modification-workflow.md`
  - Build: `Makefile` comment updates
  - Added consistent migration notes across all user-facing documentation

## v5.4.22 (2025-12-22)

### Changed
- **Ops Agent**: Consolidated ops and local-ops into unified ops agent
  - Removed redundant local-ops agent definition
  - Enhanced verification and deployment workflows
  - Improved deployment verification protocols

## v5.4.21 (2025-12-22)

### Added
- **Selective Skills**: Deploy only skills referenced by active agents
  - Reduces deployed skills from ~78 to ~20 for typical projects
  - Skill statistics displayed on startup
  - User skill override via configuration.yaml
  - Skills command for manual skill management

### Changed
- **PM Instructions**: Chrome DevTools MCP now mandatory for browser verification
  - PM agent must verify browser operations using Chrome DevTools
  - Enhanced delegation guidelines for web testing tasks

### Fixed
- **Dashboard**: File tracking, viewer, and styling improvements
  - Comprehensive test suite for dashboard functionality
  - Socket.IO integration tests
  - File tracking validation scripts
- **Code Quality**: Resolve ruff linting errors
  - Replace datetime.utcnow() with timezone-aware datetime.now(timezone.utc)
  - Fix import ordering and unused variables
  - Remove unnecessary else clauses
- **Dependencies**: Update uv.lock and fix deprecation warnings
  - Migrate from dependency-groups to project.dependencies

## v5.4.20 (2025-12-21)

### Changed
- **PM Instructions**: Enhanced PM agent delegation guidelines
  - Added forbidden MCP tools section for browser testing tools
  - Clarified PM must delegate to web-qa for browser operations
  - Documented Circuit Breaker #6 triggers for violations
  - Added delegation guidelines for browser testing tasks

## v5.4.19 (2025-12-21)

### Fixed
- **Version Management**: Patch release for version consistency

## v5.4.18 (2025-12-21)

### Added
- **Project Organization**: Expand /mpm-organize to full project organization
  - Enhanced organization capabilities for better project management
  - Improved structure and workflow for project organization tasks

## v5.4.17 (2025-12-21)

### Changed
- **Command Consolidation**: Removed redundant agent commands, consolidated into /mpm-configure
  - Streamlined CLI interface for better usability
  - All agent configuration now centralized in /mpm-configure command

## v5.4.16 (2025-12-21)

### Added
- **Agent Summary**: Display total agent count on startup for better visibility

## v5.4.15 (2025-12-21)

### Added
- **Chrome DevTools MCP**: Auto-install chrome-devtools-mcp server on first use
  - Detects if server is not installed and prompts user to install
  - Uses npx for zero-configuration installation
  - Adds server to Claude Code config automatically
- **Web QA Agent**: Updated configuration for enhanced browser automation capabilities

### Fixed
- **Code Quality**: Format chrome_devtools_installer.py and tests for ruff compliance

## v5.4.14 (2025-12-21)

### Fixed
- **Dependencies**: Update uv.lock for version consistency

## v5.4.13 (2025-12-20)

### Changed
- **Memory Architecture**: Transitioned from deployment-time to runtime memory loading
  - Agent memories now loaded dynamically via `MemoryPreDelegationHook` during task delegation
  - PM instructions only contain PM.md memory (not all agent memories)
  - Each agent receives only its own memory when delegated to via Task tool
  - Memory changes take effect immediately without restarting Claude Code

### Added
- **EventBus Integration**: Memory loading now emits `agent.memory.loaded` events
  - Observability into when agents load memory and how much
  - Event data includes agent_id, memory_source, memory_size, timestamp
  - See `docs/observability/agent-memory-events.md` for details

### Removed
- **BASE_*.md Templates**: Removed obsolete static template files
  - Replaced by repository-based agent synchronization
  - Agents synced from GitHub repos to `~/.claude-mpm/cache/remote-agents/`
  - Hierarchical `BASE-AGENT.md` files for shared content
- **Deployment-Time Memory Injection**: Removed from ContentFormatter
  - No longer inject all agent memories into PM_INSTRUCTIONS.md

### Documentation
- Added `docs/architecture/memory-flow.md`: Comprehensive memory architecture documentation
- Added `docs/observability/agent-memory-events.md`: EventBus integration guide
- Updated agent documentation to reflect runtime memory loading

## v5.4.12 (2025-12-19)

### Changed
- **Version**: Patch version bump

## v5.4.11 (2025-12-19)

### Fixed
- **Code Quality**: Format event_handlers.py for ruff compliance

## v5.4.10 (2025-12-19)

### Fixed
- **Code Quality**: Fix import sorting in memory_integration.py for ruff compliance

## v5.4.9 (2025-12-19)

### Fixed
- **Hook System**: Add matcher field for SessionStart hook subtypes to prevent hook execution errors
- **Logging**: Resolve SessionStart hook errors and implement install-type-aware logging
- **Code Quality**: Sort imports in logger.py for ruff compliance
- **Dependencies**: Update uv.lock for version consistency

## v5.4.8 (2025-12-19)

### Added
- **Unified /mpm-config command**: Replaces /mpm-config-view with auto-configuration
  - Automatic toolchain detection and configuration
  - Agent review service to categorize and archive unused agents
  - Archive unused agents to `.claude/agents/unused/` instead of deleting
  - Restart notification after configuration changes
- **Command sync on startup**: Auto-deploys MPM commands and removes stale ones

### Fixed
- **Agent deployment**: Suppress YAML frontmatter warnings for template files
- **UV exec compatibility**: Hook handler now works correctly with UV-managed projects
- **Hook installer**: Fixed critical bug causing hooks to self-delete after installation

### Added
- **Automatic session resume on PM startup**: Detects paused sessions and displays context
  - Session resume hooks integrated into PM startup sequence
  - Automatic context restoration from resume logs
  - Implementation: `src/claude_mpm/hooks/__init__.py`
- **Mandatory pause prompts at context thresholds**: Enforced pause at 70%, 85%, 95%
  - User acknowledgment required before continuing
  - Prevents accidental context overflow
  - Implementation: `src/claude_mpm/agents/BASE_PM.md`

### Changed
- **BASE_PM.md**: Enhanced context management with mandatory pause enforcement
  - Pause prompts now require user acknowledgment
  - Clear threshold rules and enforcement guidelines
- **PM_INSTRUCTIONS.md**: Integrated automatic session resume into startup sequence
  - PM now automatically checks for paused sessions on startup
  - Displays resume context before beginning new work

### Fixed
- **Security**: Upgraded 15 dependencies to resolve vulnerabilities (88% reduction)
  - 4 CRITICAL vulnerabilities fixed: RCE, command injection, auth bypass, file overwrite
  - 6 HIGH vulnerabilities fixed: DoS, HTTP smuggling, ReDoS
  - 5 MEDIUM/LOW vulnerabilities fixed
  - authlib: 1.6.1 → 1.6.5 (fixes 3 vulnerabilities)
  - fastmcp: 2.10.6 → 2.13.0.2 (fixes 2 vulnerabilities)
  - python-socketio: 5.13.0 → 5.14.3 (fixes 1 CRITICAL RCE)
  - pip: 25.2 → 25.3 (fixes 1 CRITICAL file overwrite)
  - gunicorn: 21.2.0 → 23.0.0 (fixes 2 HTTP smuggling)
  - fastapi: 0.104.1 → 0.121.0 (fixes 1 ReDoS)
  - starlette: 0.27.0 → 0.49.3 (fixes 2 DoS vulnerabilities)
  - eventlet: 0.40.2 → 0.40.3
  - h2: 4.2.0 → 4.3.0
  - torch: 2.7.1 → 2.9.0

### Documentation
- Added `docs/features/session-auto-resume.md`: Comprehensive feature documentation
- Added `IMPLEMENTATION_SUMMARY.md`: Implementation details for auto-resume functionality

#### Agent Updates

## v5.4.7 (2025-12-18)

### Fix

- correct agent ID mismatch in configure CLI agent selection

## v5.4.5 (2025-12-16)

### Feat

- add skill-to-agent auto-inference mapping (#120)

### Fix

- resolve linting errors in skill_to_agent_mapper.py

## v5.4.4 (2025-12-16)

### Feat

- selective skill deployment based on agent requirements
- **deployment**: implement selective skill deployment

### Fix

- apply ruff linting fixes for release
- show correct agent count when deployment reports 0 configured
- show configured agent count in deployment progress bar
- use agent_id for deployment status detection in configure
- exclude claude-mpm-skills repo from agent discovery

## v5.4.3 (2025-12-15)

### Refactor

- rename /mpm-ticket-organize to /mpm-organize

## v5.4.2 (2025-12-15)

## v5.4.1 (2025-12-15)

### Feat

- auto-update package.json, pyproject.toml, and CHANGELOG.md in automated release
- **release**: add agent repository sync to automated release
- **dashboard**: implement file viewer with Shiki syntax highlighting
- **dashboard**: fix FilesView styling and add 50-event cache per stream

### Fix

- correct project root path calculation in automated_release.py
- **cli**: use display name instead of agent_id in agent selection UI
- **agents**: resolve agent count discrepancy and missing list_sources method
- **dashboard**: extract file paths from tool_parameters
- **dashboard**: debug files display + remove Path column
- **dashboard**: Files tab now displays file operations correctly
- **dashboard**: simplify Files tab to scan all events for file paths

## v5.4.0 (2025-12-13)

### Feat

- **dashboard**: add Files tab with syntax highlighting and diff viewing
- **dashboard**: add Tools view with pre/post tool correlation
- improve EventStream table layout with grid-based design
- add PM delegation rules for mpm-skills-manager agent
- enhance event list with detailed display fields
- add hot reload for dashboard development
- enhance Svelte dashboard with JSON explorer and stream filtering
- add SvelteKit 5 dashboard with real-time event monitoring

### Fix

- replace os.getcwd() with Path.cwd() (PTH109)
- **dashboard**: extract file paths from tool_parameters in hook events
- **dashboard**: add type guards to files.svelte.ts and tools.svelte.ts
- **agents**: prioritize dist/agents/ over source agents/ in discovery
- **monitor**: improve exit code messaging for daemon termination
- add proper type guards for event.data property access in EventStream
- remove unused contextlib import
- use raw strings for pytest regex patterns
- use $effect for store subscription in runes mode
- use traditional Svelte stores for static adapter compatibility
- stream dropdown reactivity in Svelte 5
- convert Svelte 5 socket store to factory function pattern
- serve Svelte assets at /svelte/_app/ to match base path
- configure SvelteKit base path for /svelte mount point
- disable redundant DirectSocketIORelay to prevent event duplication
- improve hook event naming with comprehensive mapping

## v5.3.0 (2025-12-11)

### BREAKING CHANGE

- MCP gateway service has been archived and is no longer active.
Use direct MCP server integrations (mcp-ticketer, mcp-vector-search, etc.) instead.

### Feat

- deprecate MCP gateway, add summarize CLI command
- add EventBus integration and health endpoints to Socket.IO server

### Fix

- resolve ruff linting errors before release

## v5.2.3 (2025-12-11)

### Fix

- make agent dependencies optional via frontmatter

## v5.2.2 (2025-12-10)

### Fix

- make pylint import optional for clone detection

## v5.2.1 (2025-12-10)

### Feat

- add multi-language clone detection support
- add code clone detection to code-analyzer agent

### Fix

- agent deployment path and test fixes
- apply ruff linting and formatting fixes
- use correct pylint API for duplicate detection

## v5.1.12 (2025-12-10)

### Feat

- auto-deploy agents when saving selection in configure
- show Installed status with green highlight for deployed agents

### Fix

- use grey color and properly format YAML name for display
- use YAML name in agent list and improve table colors
- deploy output styles to project-level directory
- deploy output styles to correct directory with both styles
- auto-fix linting errors before publish
- deploy agents to project directory instead of user-level
- show Installed status for deployed agents in initial list
- show asterisk for deployed agents instead of recommended agents
- update AgentRecommendationService.CORE_AGENTS to match ToolchainDetector

## v5.1.11 (2025-12-10)

### Feat

- add branch protection for main branch
- add visual feedback loop for agent selection controls
- add recommended agents feature with toolchain detection
- **ui**: implement two-step agent selection with collection-level toggles
- **ui**: change Select All to Toggle All for select/deselect behavior
- **ui**: group agent selection by collection with Select All option
- **styles**: rename output styles and deploy to ~/.claude/styles/
- **agents**: enhance agent matching with collection-based selection and frontmatter

### Fix

- update CORE_AGENTS to use correct agent IDs and add local-ops-agent
- correct agent count in sources table and add loading spinner
- prioritize frontmatter metadata for agent name/description extraction
- resolve datetime timezone mismatch in socketio health monitor
- reload menu after agent selection and fix loading state
- use YAML frontmatter agent_id for deployment matching
- **ui**: show actual deployment state in individual agent selection
- **ui**: show actual deployment state in agent selection
- **agents**: remove redundant Path import causing scoping error
- **agents**: verify file existence before adding to removal set
- **agents**: extract leaf name for agent removal to match deployed files
- **ui**: normalize agent path formats for accurate change detection
- **ui**: patch correct module for questionary checkbox symbols

### Refactor

- simplify agent management to unified selection view
- simplify agent architecture to 2-location model

## v5.1.8 (2025-12-09)

### Feat

- auto-gitignore user-specific config files during mpm-init

### Fix

- **ui**: fix questionary import scoping for checkbox symbols
- remove unnecessary f-string prefixes in error messages
- **ui**: add exception handling for questionary menu failures
- **ui**: improve configurator feedback and error handling
- **ui**: improve agent configurator checkbox visibility and state tracking

## v5.1.6 (2025-12-08)

### Fix

- enable auto-push for Homebrew tap updates in releases

## v5.1.5 (2025-12-08)

### Feat

- enforce mandatory QA verification gate in PM instructions
- **deepeval**: add PM Proactive Verification test suite

### Fix

- **lint**: combine implicitly concatenated strings
- **lint**: apply ruff auto-fixes for eval tests
- **ci**: add pytest-timeout to eval dependencies
- **deepeval**: calibrate BASE_AGENT and Engineer tests for CI (#105)

## v5.1.4 (2025-12-08)

### Fix

- **deepeval**: calibrate Documentation Agent scenarios to 100% pass rate (#112)
- **deepeval**: calibrate Ops Agent scenarios to 100% pass rate (#111)
- **deepeval**: calibrate QA Agent scenarios to 100% pass rate (#110)
- **deepeval**: calibrate Engineer Agent scenarios to 100% pass rate (#109)

## v5.1.3 (2025-12-07)

### Feat

- **deepeval**: add Prompt-Engineer Agent test suite (#113)
- **deepeval**: add CI/CD and documentation for Documentation Agent tests (#112)
- **deepeval**: implement Documentation Agent test harness and 3 integration tests (#112)
- **deepeval**: add 12 Documentation Agent test scenarios (#112)
- **deepeval**: implement Documentation Agent custom metrics (#112)
- **deepeval**: add CI/CD and documentation for Ops Agent tests (#111)
- **deepeval**: implement Ops Agent test harness and 5 integration tests (#111)
- **deepeval**: add 18 Ops Agent test scenarios (#111)
- **deepeval**: implement Ops Agent custom metrics (#111)
- **pm**: add documentation routing protocol to PM instructions
- **deepeval**: add CI/CD and documentation for QA Agent tests (#110)
- **deepeval**: implement QA Agent test harness and 5 integration tests (#110)
- **deepeval**: add 20 QA Agent test scenarios (#110)
- **deepeval**: implement QA Agent custom metrics (#110)
- **deepeval**: add CI/CD and documentation for Engineer Agent tests (#109)
- **deepeval**: add 6 Engineer Agent workflow integration tests (#109)
- **deepeval**: implement Engineer Agent test harness (#109)
- **deepeval**: add 25 Engineer Agent test scenarios (#109)
- **deepeval**: implement Engineer Agent custom metrics (#109)
- **deepeval**: add Research Agent scenarios and test harness (#108)
- **deepeval**: implement Research Agent custom metrics (#108)
- add CI/CD for DeepEval tests and TkDD protocol (#107)
- **deepeval**: add 5 BASE_AGENT integration tests (#107)
- **deepeval**: implement BASE_AGENT test harness (#107)
- **deepeval**: add 20 BASE_AGENT behavioral scenarios (#107)
- **deepeval**: implement BASE_AGENT custom metrics (#107)

## v5.1.2 (2025-12-06)

### BREAKING CHANGE

- None (additive enforcement, backward compatible)

### Feat

- implement 1M-445 logging fix and 1M-502 UX improvements
- upgrade Circuit Breaker #2 to proactive blocking (40% → 95%)

### Fix

- remove duplicate "Launching Claude" progress bar at startup
- add corrupt git repository detection to Homebrew update script

## v5.1.1 (2025-12-05)

## v5.1.0 (2025-12-05)

### Feat

- add DEL-000 universal delegation pattern test
- implement PM behavioral testing framework integrated with release process
- add PM behavior validation test suite for Circuit Breaker #6
- implement integration testing framework for DeepEval PM evaluation
- implement DeepEval framework for PM instruction evaluation
- enforce ticketing delegation and mandatory verification in PM instructions

### Fix

- add Optional types to conftest.py to resolve RUF013 linting issues

## v5.0.9 (2025-12-04)

### Feat

- add comprehensive agent and skills repository sync workflow

### Fix

- remove pytest-timeout flags not available in UV environment
- use UV virtual environment for test execution
- bump minimum Python version to 3.11 for kuzu-memory compatibility
- remove unused pydoc-markdown dependency causing conflict
- resolve ruff linting violations for 5.0.9 release
- prevent text artifacts in progress bar display
- resolve circular import dependencies using dependency injection

### Refactor

- simplify test mode instruction removal with regex
- consolidate tier precedence pattern in file_loader
- reduce complexity of high-complexity functions

## v5.0.7 (2025-12-04)

### BREAKING CHANGE

- MCP services are now user-controlled and must be installed manually.
Claude MPM no longer auto-modifies ~/.claude.json to add/fix MCP service configurations.

### Fix

- auto-fix import ordering in tests
- remove unused imports and fix linting issues
- remove obsolete MCP auto-configuration code

## v5.0.6 (2025-12-03)

### Feat

- hide deprecated command aliases from UI while preserving functionality
- configure twine with .pypirc for streamlined PyPI publishing

### Fix

- resolve thread safety deadlocks and daemon startup failures
- remove unused shutil import

### Refactor

- move deprecated command aliases to deprecated_aliases field

## v5.0.4 (2025-12-03)

### BREAKING CHANGE

- Switched from checked=True on Choice objects to default parameter

### Feat

- auto-remove deprecated /mpm commands on startup
- add /mpm-postmortem command for automated error analysis
- add Claude MPM Teach mode for beginners
- optimize PM instructions for Claude 4.5 best practices
- consolidate cache to remote-agents + add git workflow
- add toolchain presets and interactive skills configure
- add 'Adjust selection' option to agent installation confirmation
- **1M-502**: improve color readability and terminology
- **1M-502**: Implement unified agent deployment/removal interface
- **1M-502**: Simplify agent selection menu and improve UX flow
- **1M-502**: Fix BASE_AGENT filtering and add multi-select deployment UI
- **1M-502**: Phase 2 - Convert text-input menus to questionary navigation
- implement 1M-502 Phase 1 - BASE_AGENT and deployment filtering
- complete Phase 3 of Git sync refactor (1M-486)
- upgrade configurator with arrow-key navigation using questionary

### Fix

- add per-test timeouts to prevent test suite hangs
- remove unused variables in postmortem and agents parser
- resolve linting issues for postmortem analysis module
- correct agent count in startup deployment progress
- CacheGitManager now finds git repos in nested subdirectories
- remove unnecessary .keys() call in test (linter fix)
- remove [Installed]/[Available] labels from checkbox interface for clearer UX
- add .claude/templates/ to deployed agent detection
- set is_deployed attribute on agents for Status column display
- revert to checked=True (default param is single-select only)
- use questionary default parameter instead of checked for pre-selection
- add checkbox styling to QUESTIONARY_STYLE for proper visual state rendering
- agent removal now updates virtual deployment state
- update get_deployed_agent_ids to check virtual deployment state
- detect virtually deployed agents in configure interface
- **1M-502**: Use hex colors and add install status to checkbox list
- **1M-502**: Use correct color syntax for prompt_toolkit and Rich
- **1M-502**: Replace cyan with high-contrast white/brightyellow color scheme
- **1M-502**: Fix deployment status detection for hierarchical agent IDs

## v5.0.1 (2025-12-01)

### BREAKING CHANGE

- Git repository integration for skills and agents

### Feat

- clarify skills deployment message in startup
- add informative message for Claude Code startup delay
- add "Launching Claude" progress bar matching agent sync style
- add progress indicators for startup operations
- fix PM instructions deployment architecture
- integrate template deployment with PM instructions build
- implement PR-based workflow for agent and skill management (Phase 1-3)
- add 'claude-mpm agents cleanup' command for agent migration
- implement parallel downloads for skills sync with thread-safe ETag caching
- improve sync progress messages to show downloaded vs cached
- implement Phase 2 of git sync refactoring for skills (1M-486)
- implement Phase 1 of agent sync refactoring with Git Tree API (1M-486)
- add user-visible notification when reading system prompt from file
- v5.0 major release - Git repository integration for agents and skills
- wire up agent git sources deployment integration and auto-sync (1M-442 Phase 2)
- add comprehensive agent improvement workflow to agent-manager
- implement agent-source CLI commands (1M-442 Phase 1)
- integrate SkillSourcesCheck into doctor diagnostic system
- implement Phase 3 agent selection modes (1M-382)
- implement Phase 2 single-tier deployment service and CLI (1M-382)
- implement Phase 1 foundation for single-tier agent system (1M-382)
- implement 4-tier agent discovery with remote agents and user-level deprecation
- implement Phase 1 enhanced flat naming with namespace metadata (1M-400)
- complete git-based agent system integration (1M-382)
- migrate agent templates from JSON to Markdown format (1M-382)
- implement SQLite state tracking for agent sync (1M-388)
- implement GitSourceSyncService with ETag-based caching (1M-387)

### Fix

- apply ruff format to match Makefile quality gate requirements
- apply black formatting to 30 remaining files
- resolve final import sorting issues in source code
- resolve remaining import sorting issues detected by ruff
- resolve linting issues and improve code quality
- prioritize PM_INSTRUCTIONS_DEPLOYED.md over source file
- Phase 2 tests - replace GitSourceSyncService mocks with direct _recursive_sync_repository mocks
- deploy skills to project directory (.claude/skills/) not user directory
- resolve skills sync progress bar stuck at 0% (absolute position fix)
- implement file-based caching for oneshot sessions to resolve Linux ARG_MAX issue (1M-485)
- correct PM_INSTRUCTIONS.md filename in SystemInstructionsDeployer
- filter remote agent sync to only pull from /agents directory (1M-442)
- resolve agent deployment failures in v5.0 (1M-442)
- add missing deployment phase to agent startup sync (CRITICAL)
- critical bugs in agent deployment - import path and file discovery (1M-442 QA fixes)
- correct agent-source command suggestions in doctor diagnostic (1M-442 Phase 3)
- complete skill-source update fix for single source path (1M-441)
- resolve skill-source update command crash (1M-441)
- parse YAML frontmatter for agent dependencies

### Refactor

- remove duplicate agent files from source templates directory
- remove deprecated JSON agent templates
- optimize startup process and remove redundancies
- optimize PM instructions with content consolidation (Phase 3)
- optimize PM instructions with template references (Phase 2)
- extract MCP-specific instructions to agent files
- standardize template filenames to use dashes instead of underscores
- remove deprecated command stubs for clean migration (1M-400)

## v4.26.4 (2025-11-29)

### Feat

- add /mpm-ticket slash command for high-level ticketing workflows

### Fix

- correct ticketing agent_id to match deployment name

## v4.26.3 (2025-11-25)

### Feat

- optimize PM_INSTRUCTIONS.md for token efficiency (1M-200, 1M-203)
- add mcp-skillset integration to research agent (v4.9.0)
- migrate Homebrew tap to bobmatnyc/homebrew-tools

### Fix

- update mypy and pytest configuration for compatibility

## v4.26.1 (2025-11-24)

### Feat

- add ticket completeness protocol to PM instructions

### Fix

- correct agent naming from 'ticketing-agent' to 'ticketing'

## v4.26.0 (2025-11-24)

### Feat

- add Circuit Breaker #7 for Research Gate violation detection (1M-163)
- enhance ticketing agent to read full ticket context including comments (1M-178)

### Fix

- remove remaining PM ticket tool usage examples (1M-177)
- remove conflicting ticketing delegation guidance (1M-177)

## v4.25.10 (2025-11-24)

### Feat

- add task decomposition protocol for agents (1M-168)
- add standardized confidence reporting for agents (1M-167)
- add semantic workflow state intelligence to ticketing agent (1M-163)
- add context optimization for ticket reading (1M-163)
- add research gate protocol for ticket 1M-163
- add agent clarification framework for ticket 1M-163

### Fix

- restore OUTPUT_STYLE.md content from git history (1M-175)
- check output style file size before skipping deployment (1M-175)

## v4.25.8 (2025-11-23)

### Feat

- implement ticket-scoped work protection system
- add scope protection protocol to PM instructions

### Fix

- update security agent to validate .gitignore before flagging secrets

## v4.25.7 (2025-11-23)

## v4.25.6 (2025-11-23)

### Feat

- enforce ticket-first workflow with mandatory traceability (v2.8.0)
- add comprehensive work capture to research agent (v2.7.0)
- add automatic .gitignore management to /mpm-init
- add multi-collection support for skills deployment

### Fix

- convert pytest match patterns to raw strings (RUF043)
- resolve all remaining linting errors (RUF059, I001)
- resolve unused variable linting errors (RUF059)

## v4.25.4 (2025-11-21)

### Feat

- add intelligent skills deployment system with GitHub integration

## v4.25.3 (2025-11-21)

### Feat

- implement comprehensive Makefile enhancements and ruff migration

## v4.25.2 (2025-11-21)

### Feat

- implement pytest-xdist parallelization for 3-4x test speedup
- add mcp-ticketer delegation to PM instructions
- add mcp-ticketer integration to research agent
- strengthen DO THE WORK directive in PM instructions
- enforce mandatory ticketing agent delegation in PM instructions
- add git history to CLI startup screen recent activity
- add light/dark theme support to d2 dashboard
- auto-deploy output style on startup

### Fix

- remove unnecessary f-string prefix in startup_display.py
- resolve critical Svelte 5 store architecture error in d2 dashboard
- dashboard pane rendering and Socket.IO improvements
- remove extraneous f-string prefixes in test_output_style_deployment.py

## v4.24.3 (2025-11-19)

### Feat

- add hook error detection and memory system
- add structured questions framework for PM agent

### Fix

- update mypy python_version to 3.9
- resolve pytest collection blocker
- replace list()[0] with next(iter()) in tests
- resolve linting errors in hook error detection
- correct test assertions for command argument order

## v4.24.1 (2025-11-19)

### BREAKING CHANGE

- Default logging changed to OFF for cleaner startup

### Feat

- enhance startup banner with teal robots and launch message
- add enhanced startup banner with Claude Code-style presentation

## v4.24.0 (2025-11-17)

### Feat

- add JavaScript Engineer agent for vanilla JS development

## v4.23.1 (2025-11-15)

### Feat

- add thorough reorganization capability to documentation agent

### Fix

- correct import order in 4 test files
- add Optional type hint to create_temp_directory
- resolve 2 test failures in unit tests

### Refactor

- replace sleep() with wait_for_condition in log monitor tests (partial)
- replace 23 sleep() calls with wait_for_condition in socketio integration tests

## v4.23.0 (2025-11-13)

### Feat

- update ticketing agent to prefer mcp-ticketer with CLI fallback

## v4.22.3 (2025-11-13)

### Feat

- add env-manager skill for environment variable validation
- add Homebrew tap integration to publishing workflow

## v4.22.2 (2025-11-12)

### Feat

- add test-quality-inspector skill for QA agents

### Fix

- use python3 in safe-release-build target

## v4.22.1 (2025-11-12)

### Feat

- add Tauri Engineer agent with 11 progressive skills

### Fix

- check if pytest module is importable instead of just checking pytest binary
- use python3 instead of python in test script
- use extend-ignore for ruff to properly skip import sorting
- use python3 instead of python in lint-structure target
- add --ignore I flag to ruff in Makefile
- explicitly ignore RUF043 and RUF059 in Makefile lint-ruff target

## v4.22.0 (2025-11-12)

### Feat

- add comprehensive stacked PR and git worktree workflows

### Fix

- manually resolve final RUF059 linting errors
- apply automatic linting fixes

## v4.21.5 (2025-11-11)

### Feat

- add native --agents flag support for 5x faster startup

### Fix

- remove unnecessary f-string prefix in test file

## v4.21.4 (2025-11-10)

### Feat

- enforce IMMEDIATE file tracking in PM workflow (BLOCKING)

### Fix

- apply linting fixes for quality gate

## v4.21.3 (2025-11-10)

### Feat

- add architectural documentation and fix command deployment

### Fix

- use next(iter()) instead of single element slice
- resolve linting errors in code_tree_analyzer package

### Refactor

- complete Priority 2 refactoring tasks
- modularize code_tree_analyzer (1,825 → 10 focused modules)

## v4.21.2 (2025-11-09)

## v4.21.1 (2025-11-09)

### Feat

- add /mpm-resume command for automatic session pause

## v4.21.0 (2025-11-09)

### Feat

- implement automatic session resume at 70% context threshold

### Fix

- resolve 9 Ruff linting errors blocking v4.21.0 release
- redirect MCP print statements to stderr to prevent protocol pollution
- replace wildcard imports with explicit imports and add backward compatibility

### Refactor

- **mpm-init**: modularize 2,093-line file into focused components

## v4.20.7 (2025-11-07)

### Feat

- **skills**: add comprehensive Rust desktop applications skill

### Refactor

- **skills**: Tier 3C & 3D progressive disclosure optimizations
- **skills**: Tier 3B progressive disclosure - dispatching-parallel-agents
- **skills**: apply progressive disclosure to skill-creator (209→189 lines)
- **skills**: Tier 3A progressive disclosure optimizations

## v4.20.6 (2025-11-07)

### Feat

- implement /mpm-init pause CLI command
- **skills**: Tier 2 progressive disclosure refactoring

## v4.20.5 (2025-11-07)

### Fix

- **skills**: espocrm-development validation issues

## v4.20.4 (2025-11-07)

### Feat

- **skills**: add EspoCRM development skill for PHP engineers
- **skills**: refactor verification-before-completion to progressive disclosure (Tier 2)
- **skills**: generate license attributions for bundled skills

### Fix

- **skills**: remove 8 non-existent skills from configuration

## v4.20.3 (2025-11-07)

### BREAKING CHANGE

- kuzu-memory and mcp-vector-search are no longer bundled with Claude MPM

### Feat

- **skills**: Week 2 progress - 15 skills downloaded, 2 refactored to progressive disclosure
- add automated pre-publish cleanup to release workflow

### Fix

- **skills**: address CRITICAL and HIGH priority issues from code review

## v4.20.2 (2025-11-07)

### Feat

- add default configuration fallback for auto-configure

## v4.20.1 (2025-11-05)

### Fix

- remove noisy MCP service health checks on startup

## v4.20.0 (2025-11-04)

### Feat

- add automatic session resume and mandatory pause prompts
- implement /mpm-init resume command to read stop event logs
- **agents**: enhance rust and python engineers with DI/SOA patterns
- implement auto-save session feature with async periodic saves

### Fix

- upgrade dependencies to resolve security vulnerabilities
- resolve linting issues for 4.20.0 pre-publish

## v4.18.2 (2025-11-02)

### Feat

- **engineering**: add comprehensive documentation quality standards

## v4.18.1 (2025-11-01)

### Fix

- correct agent name parsing to only read YAML frontmatter
- resolve ruff linting errors for 4.18.0 release

## v4.18.0 (2025-11-01)

### Feat

- add comprehensive resume log system for proactive context management

## v4.17.1 (2025-10-30)

### Fix

- update commitizen version field to 4.17.1

## v4.17.0 (2025-10-30)

### Feat

- add skills versioning system and /mpm-version command

### Fix

- auto-fix import sorting in test_skills_frontmatter
- resolve Ruff linting errors in version_service

## v4.16.3 (2025-10-29)

### Feat

- add comprehensive web-performance-optimization skill

## v4.16.2 (2025-10-29)

## v4.16.1 (2025-10-29)

### Feat

- add 4 new toolchain-specific development skills

## v4.16.0 (2025-10-28)

## v4.15.6 (2025-10-28)

### Feat

- skills integration and agent template cleanup
- major documentation reorganization and monitor improvements
- enhance local-ops agent PM2 monitoring for Next.js (v2.0.1)

### Fix

- update version to 4.15.6 in pyproject.toml
- add PTH123, C401, RUF005 to .ruff.toml ignore list
- remove PTH, RUF, C4 from ruff select to avoid problematic rules
- add RUF005 and C401 to ruff ignore list
- add ruff per-file ignores for skills system
- auto-fix ruff linting errors for quality gate
- auto-fix ruff linting errors for pre-publish quality gate
- update commitizen version to 4.15.3 in pyproject.toml

### Refactor

- **enums**: consolidate ValidationSeverity enum (Batch 29)
- **enums**: consolidate HealthStatus enums (Batch 28)
- **enums**: consolidate ServiceState enums (Batch 27)

## v4.15.2 (2025-10-26)

### BREAKING CHANGE

- MCP services no longer auto-installed - users must install manually
- External MCP services are no longer auto-installed.
Users must manually install optional services using pipx/pip:
  - pipx install mcp-vector-search
  - pipx install mcp-browser
  - pipx install kuzu-memory
  - pipx install mcp-ticketer

### Feat

- prepare v4.15.0 with MCP service user-control and agent enhancements
- **security**: add detect-secrets pre-commit hook for credential protection
- make MCP service installation user-controlled
- Phase 3A Batch 18 enum migration (19 occurrences)
- Phase 3A Batch 17 enum migration (8 occurrences)
- Phase 3A Batch 16 enum migration (9 occurrences)
- Phase 3A Batch 15 - analyzer strategies enum migration (6 occurrences)
- Phase 3B AgentCategory migration - add enum validation
- Phase 3C enum expansion - AgentCategory (12→20), HealthStatus (new), +ROLLBACK
- migrate final 3 CLI files to OutputFormat enum (12 occurrences)
- migrate agent_manager.py to use OutputFormat enum (12 occurrences)
- migrate config.py to use OutputFormat enum (17 occurrences)
- migrate agents.py to use OutputFormat enum (22 occurrences)
- migrate memory.py to use OutputFormat enum
- migrate mcp_check.py to use ServiceState enum
- add comprehensive enum system with 6 core enums

### Fix

- **diagnostics**: correct import order in diagnostic_runner.py
- **tests**: update enum counts and delegation status for consolidation changes
- resolve linting issues from enum migration
- **output-style**: read OUTPUT_STYLE.md directly instead of extracting
- **agent**: add memory format instructions to agentic-coder-optimizer
- resolve cross-project memory contamination and add git tracking enhancements

### Refactor

- **enums**: consolidate DiagnosticStatus into core enums (Batch 26)
- **enums**: consolidate ConfigurationStatus into core OperationResult enum
- **enums**: consolidate ProcessStatus into core ServiceState enum
- **enums**: consolidate StepStatus into core OperationResult enum
- **enums**: consolidate MCPServiceState into core ServiceState enum
- **enums**: migrate Phase 3A Batch 21 to OperationResult enum
- **enums**: migrate Phase 3A Batch 20 to HealthStatus enum
- **enums**: migrate Phase 3A Batch 19 to OperationResult enum
- Phase 3A Batch 14 - migrate 2 subprocess status occurrences
- Phase 3A Batch 13 - migrate 7 session status occurrences
- Phase 3A Batch 12 - eliminate type system redundancy (critical)
- Phase 3A Batch 11 - migrate 5 OperationResult occurrences (core & hooks)
- migrate core tools and logging to enum system
- migrate mpm-init command to enum system
- migrate memory, diagnostics, and socketio main to enum system
- migrate session and socketio services to enum system
- migrate monitor services to enum system
- migrate deployment strategies to enum system
- migrate unified service layer to enum system
- migrate subprocess and health check services to enum system
- migrate analyzer strategies to OperationResult enum
- migrate monitor services to OperationResult enum
- migrate agent deployment services to OperationResult enum
- integrate ValidationSeverity enum into unified services
- replace manual model normalization with ModelTier.normalize()
- Phase 1 dead code removal - shrink codebase by 3,947 lines
- **configure**: extract Startup Manager module (Phase 6/9 - FINAL)
- **configure**: extract Template Editor module (Phase 3/9 - HIGH RISK)
- **configure**: extract Navigation module (Phase 9/9 - Low Risk Complete)
- **configure**: extract Config Persistence module (Phase 8/9)
- **configure**: extract Agent Display module (Phase 4/9)
- **configure**: extract behavior management module (Phase 5/9)
- **configure**: extract hook management module (Phase 7/9)
- **configure**: extract paths and validators (Phase 2/9 complete)
- **configure**: extract helper classes to separate modules (Phase 1)
- **tests**: split agent deployment tests into 8 focused modules
- **tests**: remove broken memory CLI tests for rewrite
- **tests**: split hook_handler_comprehensive into 5 focused modules
- **cli**: eliminate __init__.py anti-pattern by extracting implementations
- **tests**: split 3 monolithic test files into focused modules
- **tools**: reduce complexity of CodeTreeAnalyzer.analyze_file from CC:34 to CC:4
- **cli**: reduce complexity of AgentsCommand._fix_agents from CC:40 to CC:4
- **agents**: reduce complexity of FrontmatterValidator.validate_and_correct from CC:57 to CC:3

## v4.14.3 (2025-10-22)

### Feat

- **cli**: add "did you mean?" suggestions for command typos

## v4.14.2 (2025-10-22)

## v4.14.1 (2025-10-22)

### Feat

- enhance local-ops-agent with comprehensive multi-toolchain support (v2.0.0)

## v4.14.0 (2025-10-22)

### Feat

- add Local Operations Process Management system

### Fix

- resolve linting issues and sync version files

## v4.13.2 (2025-10-22)

## v4.13.1 (2025-10-21)

### Fix

- resolve duplicate --dry-run argument and CLI initialization issues

## v4.13.0 (2025-10-21)

### Feat

- add intelligent auto-configuration system (Phases 1-5)
- add auto-configuration feature (Phases 1-2)

## v4.12.4 (2025-10-21)

### Feat

- extract PM behavior examples to separate template file

### Fix

- resolve race condition in log directory creation during tests

### Refactor

- complete Phase 2 modularization of PM_INSTRUCTIONS.md
- extract response format to template file (Phase 2, Module #3)
- extract PM red flags to template file (Phase 2, Module #2)
- extract Git File Tracking Protocol to dedicated template (Phase 2, Module 1)
- consolidate circuit breakers into template file (Quick Win #2)
- extract validation templates from PM_INSTRUCTIONS.md

## v4.12.2 (2025-10-20)

### Feat

- add mandatory git file tracking protocol to PM instructions

## v4.12.1 (2025-10-20)

### Feat

- add Java Engineer as 8th coding agent with benchmark suite

## v4.11.2 (2025-10-20)

### Feat

- add adaptive context window (days OR 25 commits minimum)

## v4.11.1 (2025-10-19)

### Fix

- replace session state with intelligent git-based context

## v4.11.0 (2025-10-19)

### Feat

- add session pause/resume to /mpm-init command

## v4.10.0 (2025-10-19)

### Feat

- **mcp**: add interactive auto-install for mcp-vector-search

## v4.9.0 (2025-10-19)

### Feat

- **memory**: integrate kuzu-memory as required dependency with auto-setup

## v4.8.6 (2025-10-18)

### Feat

- add Context Management Protocol to PM framework
- implement Git Commit Protocol across all 35 agents
- enhance Next.js Engineer to v2.1.0 with advanced patterns
- add AsyncWorkerPool retry pattern to Python Engineer v2.2.1
- enhance Python Engineer to v2.2.0 with algorithm pattern fixes

### Fix

- move ClickUp API credentials to environment variables

## v4.8.3 (2025-10-18)

### Feat

- Add production benchmarks, failure-learning, and Product Owner agent

### Fix

- prevent cleanup race condition in directory verification test
- handle race condition in mpm log migration test
- resolve linting issues for release

### Perf

- optimize hook system for 91% latency reduction

## v4.8.2 (2025-10-17)

### Fix

- update test to handle log cleanup removing empty directories

## v4.8.0 (2025-10-15)

### BREAKING CHANGE

- Mamba/Conda auto-detection removed. Claude MPM now uses
standard Python venv exclusively for dependency management.

### Feat

- remove Mamba support and simplify to venv-only workflow
- add self-upgrade system with automatic version checks

## v4.7.10 (2025-10-11)

### BREAKING CHANGE

- User-level memories (~/.claude-mpm/memories/) are no longer loaded.
Existing user-level memories must be migrated to project-level.

### Fix

- enforce project-only memory scope to prevent cross-project contamination

## v4.7.9 (2025-10-10)

### Feat

- add mpm-init --catchup mode for PM project context

## v4.7.8 (2025-10-09)

### Feat

- major configurator UX improvements - batch toggle, save & launch, better visibility

## v4.7.7 (2025-10-09)

### Fix

- resolve Rich markup consuming keyboard shortcuts in configurator menus

## v4.7.6 (2025-10-09)

### Fix

- enhance configurator input handling and add agent reset feature
- resolve PEP 668 virtualenv detection and add kuzu-memory bidirectional enrichment

## v4.7.5 (2025-10-08)

### Refactor

- reduce code bloat by 505 lines through DisplayHelper utility

## v4.7.4 (2025-10-08)

### Feat

- dashboard restoration and slash command enhancements

### Fix

- make print statement check non-blocking in pre-publish
- resolve mypy untyped import warnings and test timing issue

## v4.7.3 (2025-10-07)

### Fix

- correct mypy.ini exclude pattern syntax

## v4.7.2 (2025-10-06)

### Fix

- correct PROJECT_ROOT path in run_all_tests.sh
- resolve indentation and formatting issues in config_service_base.py
- critical IndentationError in config_service_base.py
- add ClassVar annotations for mutable class attributes (RUF012) - batch 3
- add ClassVar annotations (RUF012) - batch 3/3
- add ClassVar annotations (RUF012) - batch 2/3
- add ClassVar annotations (RUF012) - batch 1/3
- rename ambiguous variable name 'l' to 'line' (E741)

### Refactor

- combine nested if statements (SIM102) - batch 3
- combine nested if statements (SIM102) - batch 2
- combine nested if statements (SIM102) - batch 1

## v4.7.0 (2025-10-03)

### BREAKING CHANGE

- Engineers must now execute duplicate detection before ANY implementation

### Feat

- upgrade prompt-engineer agent to v2.0.0 with Claude 4.5 best practices
- add anti-pattern restrictions for mock data and fallback behavior
- add mandatory duplicate elimination protocol for Engineer agents

## v4.6.1 (2025-10-03)

## v4.6.0 (2025-10-03)

### Feat

- add Ruby Engineer agent and comprehensive publish workflow
- add project organization command and fix slash command documentation
- strengthen local-ops agent and PM verification policies

### Fix

- remove hardcoded model specification from Claude Code startup

## v4.5.14 (2025-10-02)

## v4.5.13 (2025-10-02)

### Fix

- prevent vitest/jest memory leaks in agent templates

## v4.5.12 (2025-10-01)

### Fix

- comprehensive linting cleanup - 657 critical and medium issues resolved

## v4.5.11 (2025-10-01)

### Feat

- add local-ops port allocation, orphan detection, and Dart engineer agent

### Fix

- reduce hook handler logging noise by changing INFO to DEBUG
- apply ruff auto-fixes for linting issues
- resolve AsyncSessionLogger lifecycle and duplicate session ID issues

### Refactor

- make core package imports lazy to reduce hook overhead
- make hook handler imports lazy to improve performance (partial)

### Perf

- optimize hook handler initialization with lazy imports

## v4.5.5 (2025-09-30)

### Feat

- add automatic kuzu-memory version checking with update prompts
- implement kuzu-memory version checking system with user update prompts
- add UAT mode to web-qa agent for business intent verification
- release v4.4.11 with enhanced doctor command and PM instructions
- release v4.4.9 with critical MCP and deployment fixes

### Fix

- improve MCP service management and kuzu-memory integration
- improve PM localhost verification enforcement and reduce log verbosity
- improve MCP service dependency handling and eliminate duplicate checks
- resolve kuzu-memory Python 3.13 asyncio compatibility issue
- update web-qa agent version to 3.0.0 for UAT release
- release v4.4.12 with critical MCP service configuration fixes
- release v4.4.10 with critical MCP service configuration fixes

### Refactor

- minor code quality improvements

## v4.4.8 (2025-09-29)

### Feat

- release v4.4.7 with local-ops agent and MCP service improvements

## v4.4.7 (2025-09-29)

### Feat

- implement Phase 3 architectural simplification for v4.4.1

### Fix

- additional improvements for fresh installation (v4.4.3)
- resolve critical fresh install errors (v4.4.2)

## v4.4.0 (2025-09-26)

### Feat

- implement Phase 2 service consolidation with 84% code reduction

## v4.3.22 (2025-09-26)

### BREAKING CHANGE

- PM now forbidden from using Grep/Glob and reading >1 file

### Feat

- enhance /mpm-init command with intelligent update capabilities (v4.3.21)
- enhance Clerk Ops agent with critical ClerkProvider configuration insights
- add mcp-vector-search auto-indexing and agent integration
- strengthen PM delegation mandate and verification requirements
- enhance data engineer with comprehensive database migration expertise
- improve memory loading logs to show actual items instead of byte counts
- auto-configure MCP services on startup

### Fix

- resolve hook handler module import error
- reduce duplicate logging in MCP auto-configuration

### Refactor

- update import patterns and code formatting across codebase
- simplify memory loading logs to show only item counts

## v4.3.12 (2025-09-24)

### Feat

- add --reload-agents flag and update MCP to use pipx
- integrate mcp-vector-search and mcp-browser as core services
- integrate mcp-browser with web-qa agent

### Fix

- update MCP browser config to use local venv installation
- update mcp-browser command path in project config
- use Python module invocation for mcp-browser
- prefer pipx installations for MCP services and fix mcp-browser config
- smart detection for local vs pipx MCP service installations
- add mcp-browser to project .mcp.json configuration
- resolve php-engineer metadata extraction error
- configure mcp-browser with pipx installation path
- eliminate repeated agent upgrade messages on startup
- properly configure external MCP services in Claude Desktop

## v4.3.11 (2025-09-23)

### Feat

- add PHP Engineer agent template and lint fixes
- enhance PM delegation with reinforcement system
- add Clerk Operations Agent for authentication setup

### Fix

- resolve critical linting errors for release build
- resolve technical debt and stability improvements

## v4.3.6 (2025-09-19)

## v4.3.5 (2025-09-19)

## v4.3.4 (2025-09-19)

### Feat

- **vercel-ops**: enhance agent with enterprise-grade environment management
- enhance PM instructions with PM2 deployment and mandatory web-qa verification

### Fix

- **vercel-ops**: add critical .env.local preservation instructions
- correct version comparison logic in agent override warnings

## v4.3.0 (2025-09-18)

### BREAKING CHANGE

- Dashboard URLs have changed - use /static/ for hub access
- Browser Logs tab removed - will be replaced with browser extension

### Feat

- bump version to 4.3.0 - add standard tools recognition
- expand standard tools recognition in agent template builder
- improve tools handling in agent deployment system
- enhance Security agent with comprehensive attack vector detection
- add NextJS Engineer agent and enhance engineers with web search
- consolidate dashboards with unified hub and React integration
- strengthen PM mandate for comprehensive real-world testing
- reinforce mandatory QA verification in PM instructions
- implement comprehensive browser console monitoring with complete isolation
- grant web_qa agent full browser console monitoring authority
- implement injectable browser console monitoring system

### Fix

- handle dictionary instructions in agent template builder
- correct log directory path to use .claude-mpm/logs
- update version to 4.2.47 and add temporary files documentation
- resolve agent type parsing issue causing 'unknown' types in listings
- resolve dashboard data display and tab isolation issues
- browser logs tab isolation from hook events
- remove test-non-mpm test agent
- resolve Claude Tree visualization and enhance engineering standards

### Refactor

- optimize PM instructions for clarity and enforceability
- remove browser logs for plugin model & strengthen PM controls

## v4.2.40 (2025-09-10)

### Fix

- replace fork() with subprocess.Popen() for monitor daemon startup

## v4.2.39 (2025-09-10)

### Fix

- disable MCP pre-warming to prevent monitor fork() race conditions

## v4.2.38 (2025-09-09)

### Fix

- improve monitor startup fork safety and thread synchronization

## v4.2.37 (2025-09-09)

### Fix

- resolve daemon startup communication bug (v4.2.37)

## v4.2.36 (2025-09-09)

### Fix

- resolve monitor daemon startup issues and process identification

## v4.2.35 (2025-09-09)

### Fix

- resolve false positive port conflicts in monitor startup

## v4.2.34 (2025-09-09)

### Fix

- prevent race conditions in dashboard daemon restart logic (v4.2.33)

## v4.2.33 (2025-09-09)

### Fix

- prevent race conditions in daemon restart logic (v4.2.33)

## v4.2.32 (2025-09-09)

### Feat

- consolidate all daemon operations into single DaemonManager service
- Created centralized DaemonManager for consistent daemon lifecycle operations
- Eliminated code duplication between UnifiedMonitorDaemon and UnifiedDashboardManager
- Fixed monitor cleanup issues where old monitors weren't properly killed
- Improved process cleanup with enhanced SIGTERM/SIGKILL handling
- Fixed race conditions in port cleanup and daemon startup
- consolidate daemon management into single DaemonManager service (v4.2.31)

### Fix

- enhance monitor cleanup with more aggressive process termination
- resolve Mamba environment detection and document dependency conflicts
- resolve UnboundLocalError in monitor cleanup code
- resolve monitor cleanup race condition for --monitor flag

## v4.2.25 (2025-09-09)

## v4.2.24 (2025-09-08)

## v4.2.23 (2025-09-08)

### Feat

- add Socket.IO service detection and automatic restart (v4.2.23)

## v4.2.22 (2025-09-08)

### Fix

- resolve monitor daemon silent failures and enhance pipx documentation (v4.2.22)

## v4.2.21 (2025-09-08)

### Feat

- add monitor optional dependencies for pipx installation (v4.2.21)

### Fix

- add missing socketio_daemon.py and launch_monitor.py scripts

## v4.2.18 (2025-09-08)

### Fix

- prevent code viewer from defaulting to root directory

## v4.2.17 (2025-09-06)

### Feat

- add comprehensive local agent template support with interactive management

### Fix

- remove remaining linting issues for release

## v4.2.16 (2025-09-05)

### Fix

- resolve dashboard "process is not defined" error and monitor daemon restart issues

## v4.2.15 (2025-09-05)

### Fix

- resolve dashboard stop command error and eliminate hardcoded paths

## v4.2.14 (2025-09-04)

### Fix

- comprehensive dashboard improvements, JS refactoring phase 1, and version bump to 4.2.14

## v4.2.13 (2025-09-04)

### Fix

- resolve missing quickstart guide and fix documentation navigation

## v4.2.12 (2025-09-04)

### BREAKING CHANGE

- Removed deprecated socketio commands, use 'claude-mpm monitor' instead

### Feat

- add JSON support to dashboard code viewer

### Fix

- resolve monitor daemon process management and status detection
- consolidate monitoring architecture and enhance dashboard UI
- eliminate duplicate events with single-path emission architecture
- dashboard code tree root node directory identification
- dashboard code viewer and Socket.IO event handling
- dashboard code tree root node directory identification
- remove duplicate content pane and improve code tree data display
- add defensive import handling for outdated installations
- dashboard code viewer displays content in correct tab

## v4.2.7 (2025-09-03)

### Fix

- dashboard resilience and real event serving

## v4.2.6 (2025-09-03)

### Fix

- dashboard service now works reliably without monitor dependency
- improve Socket.IO client connection resilience
- dashboard AST viewer now displays real file content instead of mock data

## v4.2.3 (2025-09-03)

### Feat

- improve agent deployment and description formatting
- add single-line description formatting to agent deployer
- implement BASE agent instruction system and Google Cloud Ops agent
- enhance file viewing in activity data viewer for single file operations
- add simple directory browser as alternative to complex D3 tree view

### Fix

- dashboard monitoring and source viewer improvements
- improve YAML descriptions with single-line format and commentary
- improve monitor launch error messages and add fallback dashboard launcher
- resolve 'Already loading' issue in code tree directory navigation

## v4.1.29 (2025-08-31)

### Fix

- prevent duplicate empty directory events in code explorer

## v4.1.28 (2025-08-31)

### Fix

- resolve backend issue with empty directory children in code explorer

## v4.1.27 (2025-08-31)

### Feat

- strengthen PM testing and observability requirements
- web qa agent v1.8.0 adds safari testing with applescript
- web qa agent v1.7.0 with 4-phase progressive testing

### Fix

- add debug logging for code explorer empty directory issue
- code explorer showing empty directory for src
- add missing .mjs and .cjs extensions to CODE_EXTENSIONS
- todowrite viewer horizontal status bar display
- activity viewer tools persistence and data viewer improvements
- resolve activity viewer tool display issues
- implement proper activity viewer display rules for TodoWrite
- resolve repeated agent upgrade notifications by fixing author field check
- include version metadata in deployed agent frontmatter
- dashboard activity tree persistence and proper event handling
- dashboard activity viewer persistence and nesting improvements

### Refactor

- consolidate and strengthen PM instructions for firm behavioral enforcement

## v4.1.15 (2025-08-29)

### Fix

- add missing __init__.py files for proper package distribution

## v4.1.14 (2025-08-29)

### Fix

- pipx installation issues and enhance Ops agent security
- dashboard code panel multi-level navigation and remove centering

## v4.1.13 (2025-08-28)

### Fix

- restore agent metadata and improve dashboard stability

## v4.1.12 (2025-08-28)

### Feat

- add PM instruction reinforcement system and improve dashboard visualization

### Fix

- improve ruff linting configuration and resolve syntax errors

## v4.1.11 (2025-08-27)

### Feat

- add mpm-init command and git branding customization v4.1.11

## v4.1.10 (2025-08-26)

### Fix

- properly handle code analysis events in dashboard

## v4.1.9 (2025-08-26)

### Feat

- add mermaid diagram generation for Code Analyzer v4.1.9
- add Claude Code version checking for hook monitoring

### Fix

- correct hook matcher syntax for Claude Code compatibility
- resolve dashboard event broadcasting issues

## v4.1.8 (2025-08-25)

### Feat

- improve event monitoring and debugging tools

### Fix

- enhance hook management and agent-manager configuration
- critical dashboard connection failures - event handler registration and connection resilience

## v4.1.7 (2025-08-25)

### Fix

- improve dashboard/SocketIO connection stability and update agent-manager (v1.1.0)
- resolve linting issues in scripts directory

### Refactor

- reduce complexity in scripts directory

## v4.1.6 (2025-08-25)

### Feat

- add instructions check to mpm-doctor for detecting duplicate CLAUDE.md files

### Fix

- resolve MountError in Textual TUI by yielding ListView items directly

## v4.1.5 (2025-08-25)

### Feat

- add development test files
- optimize agent templates for memory safety and clarity
- complete god class refactoring and service architecture implementation

### Fix

- apply automated linting fixes for release build

### Refactor

- update core registries for refactored services
- eliminate god classes in agent deployment
- eliminate god classes in ticket services
- eliminate god classes in project analyzer
- eliminate god classes in monitoring subsystem
- eliminate god class in tickets.py
- eliminate god class in analyzer.py
- eliminate god classes in monitoring and agent_lifecycle_manager
- Extract services from hook_handler.py god class
- Major god class elimination - Phase 1 complete
- extract services from agent_deployment.py to reduce complexity

## v4.1.2 (2025-08-24)

### Fix

- resolve FileExistsError in logger symlink creation and comprehensive linting cleanup

## v4.1.1 (2025-08-23)

## v4.1.0 (2025-08-22)

### BREAKING CHANGE

- All agents now deploy to project-level .claude/agents directory
regardless of tier or source. This simplifies deployment logic and improves
project isolation while maintaining agent discovery from multiple sources.

### Feat

- bump version to 4.1.0
- **deployment**: standardize all agent deployment to project-level .claude directory
- add hierarchical agent display and monitor UI build tracking system

### Fix

- restore test scripts and update documentation paths
- improve Socket.IO stability and connection reliability
- **agents**: fix MCP tool name and enhance Documentation agent memory protection
- prevent automatic file creation in .claude/ directory during startup
- prevent CLAUDE.md creation during startup in SystemInstructionsDeployer
- update pyproject.toml version to 4.0.30 for PyPI publication
- correct PM customization documentation to reference .claude-mpm/INSTRUCTIONS.md

### Refactor

- reorganize scripts directory and remove obsolete test files

## v4.0.29 (2025-08-21)

## v4.0.28 (2025-08-21)

## v4.0.25 (2025-08-20)

### Fix

- resolve agent upgrade persistence and JSON template issues

## v4.0.24 (2025-08-20)

### Fix

- update MCP installation to use claude-mpm command instead of Python script

## v4.0.23 (2025-08-20)

### Feat

- add comprehensive memory protection to all file-processing agents

## v4.0.22 (2025-08-19)

### Fix

- implement NLP-based memory deduplication and standardize simple list format
- implement NLP-based memory deduplication and standardize simple list format
- correct version format in CHANGELOG.md for 4.0.19
- add memory management instructions to QA agent

### Refactor

- move MCP server script to proper module location

## v4.0.18 (2025-08-18)

### Feat

- implement MCP gateway singleton installation and startup verification

## v4.0.17 (2025-08-18)

### Feat

- add automated release system and Makefile targets

### Fix

- resolve dynamic agent capabilities loading issues

## v4.0.16 (2025-08-18)

## v4.0.15 (2025-08-18)

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

## v4.0.1 (2025-08-17)

## v4.0.0 (2025-08-17)

## v3.9.11 (2025-08-16)

## v3.9.10 (2025-08-16)

## v3.9.9 (2025-08-16)

### Feat

- add MCP Gateway integration and enhanced process management

### Fix

- correct commit parsing in version management script
- ticketing agent instruction template for autonomous ticket creation

## v3.9.7 (2025-08-15)

## v3.9.6 (2025-08-15)

### Fix

- optimize agent memory usage through instruction modifications

## v3.9.5 (2025-08-15)

### Refactor

- major version tracking system overhaul and cleanup command fixes

## v3.9.4 (2025-08-15)

## v3.9.3 (2025-08-15)

## v3.9.2 (2025-08-15)

### Feat

- Research Agent v4.0.0 - critical search failure fixes
- add build tracking system for code changes
- enhance ticketing workflow with automatic phase tracking

### Fix

- resolve circular import in ClaudeRunner with lazy import

## v3.9.0 (2025-08-14)

### Feat

- enhance memory management system with 20k token capacity

## v3.8.4 (2025-08-14)

### Fix

- resolve Read the Docs build.environment configuration error
- constrain aiohttp-cors to 0.7.x for Python 3.8 compatibility

## v3.8.3 (2025-08-14)

### Feat

- major v3.8.2 release - Gemini review fixes, docs improvements, and deployment setup

### Fix

- resolve Read the Docs configuration error

## v3.8.2 (2025-08-14)

## v3.8.1 (2025-08-14)

## v3.8.0 (2025-08-14)

## v3.7.8 (2025-08-13)

### Feat

- remove .claude directory from version control

## v3.7.7 (2025-08-13)

### Fix

- Socket.IO dashboard file viewer now properly displays file operations

## v3.7.6 (2025-08-13)

### Feat

- add ticketing agent guidance to PM instructions

## v3.7.5 (2025-08-13)

### Feat

- improve agent capabilities discovery with clear name/ID separation

### Fix

- update agent dependencies and package names for Python 3.13 compatibility
- correct agent dependencies for Python 3.13 compatibility

## v3.7.4 (2025-08-13)

### Feat

- add Web UI and Web QA specialized agents for front-end development and testing

## v3.7.3 (2025-08-13)

### Fix

- correct agent deployment metadata and version handling

## v3.7.2 (2025-08-13)

### Fix

- update internal VERSION file to 3.7.1
- update version to 3.7.1 to match published release
- correct version to 3.6.2 for documentation patch release

## v3.7.1 (2025-08-12)

## v3.7.0 (2025-08-12)

## v3.6.0 (2025-08-12)

### Feat

- enhance core framework for 3.6.0
- add agent exclusion configuration
- strengthen PM delegation requirements
- add dynamic agent dependency system

### Fix

- improve hook handler and response logging
- resolve agent deployment path and duplication issues

## v3.5.6 (2025-08-11)

## v3.5.5 (2025-08-11)

### Fix

- prevent PM agent from being deployed as subagent

## v3.5.4 (2025-08-11)

### Fix

- correct agent deployment and tools formatting

## v3.5.3 (2025-08-11)

## v3.5.2 (2025-08-11)

### Feat

- Add project-local agent deployment with three-tier precedence system
- Add agent versioning system and strengthen PM delegation rules

### Refactor

- Major codebase cleanup and service reorganization
- Remove obsolete orchestration module
- Centralize config paths with enum and remove obsolete parent_directory_manager

## v3.4.27 (2025-08-08)

### Fix

- remove manager import causing ImportError in 3.4.26

## v3.4.26 (2025-08-08)

## v3.4.25 (2025-08-08)

### Feat

- add project registry for global project tracking

### Fix

- synchronize VERSION files and enhance version management system

## v3.4.24 (2025-08-08)

## v3.4.23 (2025-08-08)

### Feat

- add TodoWrite usage guidelines to agent templates
- add TodoWrite usage guidelines to agent templates

## v3.4.22 (2025-08-08)

## v3.4.21 (2025-08-08)

### Feat

- add urwid dependency for terminal UI components

### Fix

- convert agent files from YAML to Markdown with frontmatter for Claude Code compatibility

## v3.4.20 (2025-08-08)

## v3.4.19 (2025-08-08)

### Fix

- include VERSION file in package distribution to fix version reporting
- restore PM agent orchestration imperative in template
- restore PM agent orchestration imperative in template

## v3.4.17 (2025-08-07)

## v3.4.16 (2025-08-07)

## v3.4.15 (2025-08-07)

### Fix

- resolve static file serving for Socket.IO dashboard
- add aiohttp-cors dependency and fix dashboard path resolution

## v3.4.14 (2025-08-07)

## v3.4.13 (2025-08-07)

## v3.4.12 (2025-08-07)

### Fix

- resolve socketio daemon import path for installed environments

## v3.4.11 (2025-08-07)

## v3.4.10 (2025-08-07)

### Fix

- move Socket.IO dependencies to core requirements

## v3.4.9 (2025-08-07)

## v3.4.8 (2025-08-07)

### Fix

- resolve Socket.IO server false negative startup detection

## v3.4.7 (2025-08-07)

### Fix

- resolve version display and socketio daemon path issues
- resolve NPM wrapper infinite loop in findClaudeMpmCommand

## v3.4.6 (2025-08-07)

### Feat

- comprehensive project reorganization following docs/STRUCTURE.md

## v3.4.5 (2025-08-07)

### Feat

- add monitor command with Socket.IO server management

### Fix

- resolve server undefined error in Socket.IO startup

## v3.4.4 (2025-08-07)

## v3.4.3 (2025-08-06)

### Feat

- enhance memory system with data_engineer and test_integration agent support

## v3.4.2 (2025-08-06)

## v3.4.1 (2025-08-06)

### Feat

- major system improvements including Socket.IO reliability, dashboard enhancements, and comprehensive cleanup
- improve tool correlation to eliminate duplicate entries in tools list
- add comprehensive HUD blank screen debugging solution
- add memory system enhancements and monitoring improvements

### Fix

- resolve git diff working directory issues and improve dashboard layout
- update monitor event viewer dropdown to show actual hook event types
- change /mpm command prefix from colon to space syntax

## v3.3.2 (2025-08-04)

### Feat

- comprehensive memory system enhancements

## v3.3.1 (2025-08-04)

### Feat

- sync working directory when footer directory changes
- add working directory per session with git branch display

### Fix

- git diff viewer now properly uses session working directory
- automatically load working directory when session changes

## v3.3.0 (2025-08-04)

### Feat

- add git diff viewer for file write operations

### Fix

- agent inference to work with nested event data structure

## v3.2.1 (2025-08-03)

### Feat

- enhance dashboard UI with improved layout and functionality

## v3.2.0 (2025-08-03)

### Feat

- release v3.2.0 with dashboard improvements and monitoring consolidation

### Fix

- enhance file path extraction and fix Files tab rendering issues
- resolve Socket.IO event transformation to preserve all event data

## v3.2.0-beta.3 (2025-08-02)

### Feat

- consolidate monitoring interface and fix dashboard tabs
- say hello with enhanced dashboard and test improvements
- add split view dashboard with module viewer
- clean up dashboard header layout
- compact dashboard header with integrated controls
- add TodoWrite list capture to monitoring system
- enhance hook data capture for agent delegations and prompts
- implement Socket.IO monitoring system for real-time Claude MPM session tracking
- add --manager flag for integrated management interface
- add memory management capabilities to PM agent
- add WebSocket event logging for memory operations
- improve memory system with explicit agent-controlled markers
- implement Phase 2 of agent memory system - hook integration
- implement Phase 1 of agent memory system
- add configurable WebSocket port and instance identification

### Fix

- redesign dashboard with split lower section
- add missing Connect button and controls to dashboard header
- improve SubagentStop event handling for Claude Code compatibility
- ensure events display in chronological order in dashboard
- update dashboard to show newest events at bottom with proper auto-scroll
- add websocket and launch-method flags to MPM_FLAGS list in wrapper script
- add backward compatibility for simple_runner imports

### Refactor

- rename simple_runner to claude_runner and add subprocess launch method

## v3.1.3 (2025-07-29)

## v3.1.2 (2025-07-29)

### BREAKING CHANGE

- None - backward compatibility maintained

### Feat

- integrate AgentManager into AgentLifecycleManager as dependency

## v3.1.1 (2025-07-28)

### Fix

- critical working directory enforcement in claude-mpm

## v3.1.0 (2025-07-28)

### BREAKING CHANGE

- Agent configurations now require filesystem_restrictions field

### Feat

- add filesystem restrictions and PM agent support

### Fix

- comprehensive JSON schema fixes and test improvements

## v3.0.1 (2025-07-28)

## v3.0.0 (2025-07-28)

### BREAKING CHANGE

- Agent definitions now use YAML format instead of Markdown

### Feat

- major agent system refactoring and improvements

## v2.2.0 (2025-07-28)

### Feat

- remove obsolete cli_old directory

## v2.1.1 (2025-07-27)

## v2.1.2 (2025-07-27)

### Feat

- enhance release automation with improved npm sync

## v2.1.0 (2025-07-27)

### Feat

- Add comprehensive file security hook system

### Fix

- Update setuptools-scm fallback version to 2.0.0

## v2.0.0 (2025-07-27)

## v2.0.0-rc1 (2025-07-27)

### BREAKING CHANGE

- Agents now require mandatory PM reporting and follow strict workflow phases
- Removed JSON-RPC hook system. All hook functionality now uses Claude Code hooks exclusively.

### Feat

- Enhance agent system with comprehensive workflow management
- Major refactor of hook system and agent deployment improvements

##### Rust Engineer (v1.1.0) - 2025-11-04
- **Added comprehensive dependency injection patterns** with trait-based architecture
  - Constructor injection with trait bounds for compile-time safety
  - Trait objects (dyn Trait) for runtime polymorphism
  - Repository pattern for data access abstraction
  - Builder pattern for complex object construction
- **Added decision criteria** for when to use DI/SOA vs simple code
  - Use DI/SOA: Web services, microservices requiring testability, complex domain logic
  - Use simple code: CLI tools, scripts, file processing utilities, quick prototypes
- **Added anti-patterns section** warning against global state and concrete type coupling
- **Documentation**: All patterns validated with production-ready code examples
- **QA Status**: APPROVED for production use

##### Python Engineer (v2.3.0) - 2025-11-04
- **Added guidance distinguishing lightweight scripts from services**
  - Clear decision tree for when to use DI/SOA patterns vs simple functions
  - Service architecture with ABC interfaces for non-trivial applications
  - Lightweight script patterns for automation and one-off tasks
- **Added Pattern 6: Lightweight Script Pattern** with pandas example
  - Direct, simple approach for scripts, CLI tools, notebooks
  - No unnecessary abstraction for one-off tasks
- **Clarified when NOT to use DI/SOA** for simple automation tasks
  - Scripts: Keep it simple with direct function calls
  - Applications: Use full service architecture with DI
- **Documentation**: Decision criteria validated against real-world use cases
- **QA Status**: APPROVED for production use

## [4.19.0] - 2025-11-04

### Added
- **`/mpm-init resume` command**: Read stop event logs to help resume work from previous sessions
  - Created `ResumeService` for parsing response logs from `.claude-mpm/responses/`
  - Added resume subcommand with `--list`, `--session-id`, `--last` options
  - Parses PM responses for tasks, files, and next steps
  - Two-tier strategy: prefers resume logs, falls back to response logs
  - Displays comprehensive context with time calculations
  - All 15 QA tests passed with 100% success rate
  - Performance: <5ms for 69+ sessions
  - Implementation: `src/claude_mpm/services/cli/resume_service.py`

## [4.18.4] - 2025-11-04

### Added
- **Comprehensive unit tests for SessionResumeHelper**: Complete test suite with 84 tests
  - Achieved 100% line coverage and 99% branch coverage
  - Fast test execution (0.40s) with no flaky behavior
  - Covers all methods including edge cases and error scenarios
  - Integration tests for full workflow validation
  - Implementation: `tests/unit/services/cli/test_session_resume_helper.py`

## [4.18.3] - 2025-11-03

### Added
- **Session Auto-Save Feature**: Fully implemented automatic session saving with async periodic saves
  - Async background task with configurable save intervals (60-1800 seconds)
  - Default: enabled with 5-minute interval (`auto_save: true`, `save_interval: 300`)
  - Graceful shutdown with final save to prevent data loss
  - Robust validation with automatic correction of invalid configurations
  - Thread-safe operations with no performance impact
  - Implementation: `session_manager.py:513-564`, `config.py:780-807`
  - Documentation: Updated `docs/configuration.md` with comprehensive usage examples and troubleshooting
  - QA Verified: 100% pass rate on all test scenarios

## [4.18.2] - 2025-11-02

### Added
- Engineering documentation quality standards and automation gates
  - Comprehensive documentation quality standards in `docs/engineering/DOCUMENTATION_QUALITY_STANDARDS.md`
  - Automated quality gates for documentation review
  - Pre-commit hooks for documentation validation
  - Style guides for technical writing
  - Documentation templates and examples

## [4.18.1] - 2025-11-01

### Fixed
- Agent name parsing now correctly reads only YAML frontmatter (not entire file content)
- Import ordering in agent validator tests

### Changed
- Documentation improvements for publishing automation

## [4.18.0] - 2025-11-01

### Added
- **Resume Log System**: Proactive context management with automatic session logs
  - New graduated thresholds: 70% (caution), 85% (warning), 95% (critical)
  - First warning now triggers at 60k token buffer (improved from 20k at 90%)
  - Automatic 10k-token resume logs when approaching context limits
  - Structured logs with 7 key sections: Context Metrics, Mission Summary, Accomplishments, Key Findings, Decisions, Next Steps, Critical Context
  - Session continuity with seamless resumption on new session start
  - Configurable triggers: model_context_window_exceeded, max_tokens, manual_pause, threshold alerts
  - Automatic cleanup with configurable retention (default: keep last 10 logs)
  - Dual format storage: Markdown (human-readable) and JSON (metadata)
  - See [docs/user/resume-logs.md](docs/user/resume-logs.md) for complete documentation

- **New Data Models** (`src/claude_mpm/models/resume_log.py`):
  - `ContextMetrics`: Token usage and context window metrics tracking
  - `ResumeLog`: Structured container for session resume information with 10k token budget allocation

- **New Service**: `ResumeLogGenerator` (`src/claude_mpm/services/infrastructure/resume_log_generator.py`)
  - Generate resume logs from session state or TODO lists
  - Save/load resume logs to/from filesystem
  - Automatic cleanup with retention policy
  - Statistics and metrics tracking

- **Extended Services**:
  - `SessionManager`: Token tracking, threshold monitoring, resume log integration
  - `ResponseTracking`: Capture stop_reason and usage data from Claude API

- **Comprehensive Documentation**:
  - User guide: `docs/user/resume-logs.md`
  - Developer architecture: `docs/developer/resume-log-architecture.md`
  - Configuration reference: `docs/configuration.md`
  - Examples and tutorials: `docs/examples/resume-log-examples.md`

### Changed
- Context warning thresholds improved from 90%/95% to 70%/85%/95%
  - First warning at 70% provides 60k token buffer for planning
  - 85% warning provides 30k token buffer for wrapping up
  - 95% critical alert provides 10k token buffer for emergency stop
  - Much more proactive than previous 90%/95% thresholds

- Updated `BASE_PM.md` with new threshold warnings and instructions
  - PM agents now display graduated warnings at 70%, 85%, and 95%
  - Clear action recommendations at each threshold level

### Technical
- Extended `ResponseTracking` to capture `stop_reason` and `usage` data from API
- Added cumulative token tracking to `SessionManager`
- Integrated `ResumeLogGenerator` service into session lifecycle
- Automatic resume log loading on session startup
- Token budget allocation system with per-section limits

### QA
- 40/41 tests passing (97.6% coverage)
- Performance: 0.03ms generation, 0.49ms save
- APPROVED FOR PRODUCTION deployment

## [4.17.1] - 2025-10-30

### Fixed
- **Critical:** Bundled skills markdown files now included in pip packages
  - Updated MANIFEST.in to include `src/claude_mpm/skills/bundled/*.md`
  - Updated pyproject.toml package-data configuration to include `"skills/bundled/*.md"`
  - All 20 bundled skills now available in pip installations
  - Fixes empty "Available Skills" sections in configuration interface
  - Affects all users who installed v4.17.0 via pip

## [4.17.0] - 2025-10-30

### Added
- Skills versioning system with YAML frontmatter support
  - All bundled skills now have version tracking (starting at 0.1.0)
  - Skills support semantic versioning (MAJOR.MINOR.PATCH)
  - Backward compatible: skills without frontmatter use default version "unknown"
  - Added `skill_id`, `skill_version`, `updated_at`, and `tags` fields to Skill dataclass
- New `/mpm-version` slash command to display comprehensive version information
  - Shows project version and build number
  - Lists all agents with versions (grouped by tier: system/user/project)
  - Lists all skills with versions (grouped by source: bundled/user/project)
  - Displays summary statistics with totals and counts
- Extended VersionService with new methods:
  - `get_agents_versions()` - Returns agents grouped by tier with counts
  - `get_skills_versions()` - Returns skills grouped by source with counts
  - `get_version_summary()` - Returns complete version information structure

### Changed
- Reduced pytest startup verbosity by removing `-v` flag from default configuration
  - Cleaner test output by default
  - Verbose mode still available with explicit `-v` flag
  - No impact on HTML reports or CI/CD pipelines
- Changed skills loading logs from INFO to DEBUG level
  - Skills no longer listed on startup (reduced console noise)
  - Debug logging still available when needed for troubleshooting

### Fixed
- Fixed 15 VersionService unit tests that were calling methods on wrong object
  - Tests now correctly use version_service fixture instead of VersionService class
  - All version-related tests now passing

## [4.16.3] - 2025-10-29

### Added
- New web-performance-optimization skill (6,206 words)
  - Lighthouse metrics and Core Web Vitals (LCP, INP, CLS, FCP, TTFB)
  - Framework-specific optimizations (Next.js, React, Vue, Vite)
  - Modern 2024-2025 web performance techniques
  - Image optimization, JavaScript optimization, CSS optimization
  - Caching strategies and resource loading patterns

### Changed
- Updated bundled skills count from 19 to 20 in README.md
- Updated bundled skills count from 19 to 20 in user guide

## [4.16.2] - 2025-10-29

### Changed
- Patch release with maintenance updates and improvements

## [4.16.1] - 2025-10-29

### Added
- New toolchain-specific development skills:
  - nextjs-local-dev: Next.js local development guidance (3,026 words)
  - fastapi-local-dev: FastAPI local development guidance (2,827 words)
  - vite-local-dev: Vite local development guidance (2,881 words)
  - express-local-dev: Express.js local development guidance (2,724 words)
- Total: 11,458 words of new skill content

### Changed
- Updated bundled skills count from 15 to 19 in README.md
- Updated bundled skills count from 15 to 19 in user guide

## [4.16.0] - 2025-10-28

### Added
- Skills system with 15 bundled skill modules providing specialized guidance
- Skills selector in CLI configuration wizard for easy skill management
- Auto-linking functionality for skills in agent templates
- Three-tier skills organization (Core, Development, Operations)
- Comprehensive skills documentation in README.md
- PDF documentation suite for skills system

### Changed
- Updated 31 agent templates with skills field integration
- Enhanced CLI configurator with skills wizard
- Improved agent template structure for skills support

### Fixed
- Cleaned and validated all 31 agent templates
- Removed temporary report files from repository

## [4.15.6] - 2025-10-28

### Added
- Skills system integration
  - New skills module with 30+ reusable skill templates
  - Skills selector in CLI configuration wizard
  - Comprehensive skills documentation in user guide
  - PDF documentation generated (claude-mpm-user-guide.pdf)

### Fixed
- Removed duplicate agent versions across 31 agent templates
- Cleaned up agent configuration inconsistencies
- Improved agent template structure and clarity

### Changed
- Enhanced CLI interactive configuration with skills wizard
- Updated all agent templates to support skills integration
- Improved documentation organization with skills section

## [4.15.5] - 2025-10-28

### Changed
- **Major Documentation Reorganization**
  - Reduced from 364 files to 13 files (97% reduction)
  - Clear structure: user/, developer/, agents/ directories
  - All files <1000 lines with internal TOCs
  - Zero broken links, all critical content preserved

### Fixed
- Monitor improvements: removed File Tree tab, unified default port to 8765
- Streamlined 5-tab interface (Events, Agents, Tools, Files, Activity)
- Quality gate fixes: all 230 tests passing, all linters passing
- Security scan clean (zero secrets detected)

## [4.15.4] - 2025-10-27

### Added
- Enhanced PM2 monitoring for local-ops agent (v2.0.1)
  - PM2 memory restart configuration (2G limit, 10 max restarts)
  - Next.js-specific health checks (build artifacts, endpoints)
  - Enhanced PM2 monitoring with metrics extraction and smart alerts
  - Comprehensive agent documentation in docs/agents/LOCAL_OPS_AGENT.md
  - Updated CLI commands reference with PM2 monitoring section

## [4.15.3] - 2025-10-27

### Changed
- **Enum Consolidation Trilogy Complete** (Batches 27-29)
  - Batch 27: ServiceState consolidation (2 duplicates removed)
  - Batch 28: HealthStatus consolidation (3 duplicates removed, added helper methods)
  - Batch 29: ValidationSeverity consolidation (1 duplicate removed)
  - Total: 20 files modified, 6 duplicate enums eliminated
  - All 67 enum tests + 230 core tests passing

## [4.15.2] - 2025-10-26

### Changed
- Patch version bump for release

## [4.15.1] - 2025-10-26

### Changed
- Batch 26 enum consolidation (refactoring improvements)
- Enhanced OUTPUT_STYLE.md tone guidelines

## [4.15.0] - 2025-10-26

### 🎯 MCP Services Philosophy Change

**Why This Change?**

External MCP services (mcp-vector-search, mcp-browser, kuzu-memory, mcp-ticketer) have matured into standalone projects with their own release cycles and communities. Rather than auto-installing and managing these services from Claude MPM, we now encourage users to install and integrate them directly from their source repositories.

**Benefits**:
- ✅ Users get the latest versions directly from source projects
- ✅ Better separation of concerns (each tool manages its own lifecycle)
- ✅ Reduced complexity in Claude MPM installation
- ✅ More control for users over which services to enable
- ✅ Cleaner dependency management

**Migration Guide**:

If you were relying on auto-installed MCP services, manually install them using pipx:

```bash
# Install optional MCP services as needed
pipx install mcp-vector-search
pipx install mcp-browser
pipx install kuzu-memory
pipx install mcp-ticketer
```

Then configure which services to enable in `.claude-mpm/configuration.yaml`:

```yaml
startup:
  enabled_mcp_services:
    - mcp-vector-search
    - kuzu-memory
    # Add only the services you need
```

### Breaking Changes
- **BREAKING**: Removed MCP service auto-installation from Claude MPM
  - MCP services must now be manually installed via pipx or pip
  - Removed auto-installation prompts and dependency injection logic
  - Services are now user-controlled, not package-managed

### Changed
- **MCP Health Checks**: Now configuration-aware and respect enabled_mcp_services
  - Health checks only run for services listed in enabled_mcp_services config
  - Prevents health check failures for intentionally disabled services
  - Improved user experience by eliminating noise from unused services
- **Logging Verbosity**: Reduced health check logging from INFO to DEBUG level
  - MCP service health checks now log at DEBUG level by default
  - Cleaner startup logs with less noise
  - Only failed checks remain at WARNING/ERROR level for visibility

### Fixed
- **Test Suite**: Fixed 3 test failures from enum consolidation (Batches 21-26)
  - Fixed test_deployment_status_format.py to use OperationResult enum
  - Fixed test_delegation.py to use OperationResult enum
  - Fixed test_session_handlers.py to use ServiceState enum
  - All tests now passing after enum migration cleanup

### Enhanced
- **Project Organizer Agent**: Added PROJECT_ORGANIZATION.md support (v1.2.0)
  - Agent now reads and follows PROJECT_ORGANIZATION.md standards when present
  - Improved file organization aligned with project-specific conventions
  - Better integration with existing project structure patterns
  - Enhanced documentation awareness for organization tasks

### Security
- **Credential Protection**: Added detect-secrets pre-commit hook
  - Automatic scanning for credentials before commits
  - Prevents accidental exposure of API keys, tokens, and passwords
  - Integrated into pre-commit hook workflow
- **Git History Cleanup**: Cleaned exposed credentials from git history
  - Removed accidentally committed credentials using git filter-branch
  - Force-pushed cleaned history to all branches
  - Updated all developers to re-clone or fetch cleaned history

## [4.14.9] - 2025-10-25

### Added
- **HealthStatus Enum**: New enum for service health monitoring (6 states)
  - HEALTHY, UNHEALTHY, DEGRADED, UNKNOWN, CHECKING, TIMEOUT
  - Distinct semantic domain from ServiceState (operational) and OperationResult (transactional)
- **OperationResult.ROLLBACK**: New state for rollback operations

### Changed
- **AgentCategory Expansion** (Phase 3C): 12 → 20 categories (+67% growth)
  - Added: ANALYSIS, QUALITY, INFRASTRUCTURE, CONTENT, OPTIMIZATION, SPECIALIZED, SYSTEM, PRODUCT
  - Now covers all 36 agent JSON template categories
  - Organized by functional domains (Engineering, Quality, Operations, etc.)
- **AgentCategory Migration** (Phase 3B): Enum validation in agent loader
  - agent_loader.py: Added category validation with graceful fallback
  - Invalid categories log warning and default to GENERAL
  - Maintains backward compatibility (stores as string values)
- **Service Layer Migration** (Phase 3A Batch 15): 6 more occurrences
  - performance_analyzer.py: 3 occurrences (ERROR, SUCCESS comparisons)
  - security_analyzer.py: 1 occurrence (ERROR in exception handler)
  - structure_analyzer.py: 1 occurrence (SUCCESS comparison)
  - dependency_analyzer.py: 1 occurrence (SUCCESS comparison)
- **Test Suite Updated**: All 67 enum tests pass with new expansions

### Progress Summary
- **Phase 3A Progress**: 108/876 occurrences migrated (12.3%)
- **Phase 3B**: Complete - Agent category validation enabled
- **Phase 3C**: Complete - Enum system expanded for full coverage

## [4.14.8] - 2025-10-25

### Added
- **Enum System**: Comprehensive type-safe enum system for magic string elimination
  - `OperationResult`: Standardize operation outcomes (success, error, failed, etc.)
  - `OutputFormat`: CLI output format handling (json, yaml, text, markdown, etc.)
  - `ServiceState`: Service lifecycle states (idle, running, stopped, error, etc.)
  - `ValidationSeverity`: Error severity levels (info, warning, error, critical)
  - `ModelTier`: Claude model tier normalization (opus, sonnet, haiku)
  - `AgentCategory`: Agent functional categorization
- **ModelTier.normalize()**: Intelligent model name normalization method
  - Handles multiple model name formats (claude-opus-4-20250514, SONNET, etc.)
  - Case-insensitive substring matching
  - Safe default fallback to SONNET
- **Comprehensive Test Suite**: 67 enum tests with 100% pass rate
- **Developer Documentation**: Complete enum migration guide (`docs/developer/ENUM_MIGRATION_GUIDE.md`)
  - All 6 enum reference documentation
  - Migration patterns and use cases
  - Testing guidelines and troubleshooting

### Changed
- **CLI Layer Migration** (Phase 1 & 2): 103 magic strings → type-safe enums
  - `memory.py`: OutputFormat enum (11 occurrences)
  - `agents.py`: OutputFormat enum (22 occurrences)
  - `config.py`: OutputFormat enum (17 occurrences)
  - `agent_manager.py`: OutputFormat enum (12 occurrences)
  - `analyze.py`: OutputFormat enum (4 occurrences)
  - `analyze_code.py`: OutputFormat enum (4 occurrences)
  - `aggregate.py`: OutputFormat enum (4 occurrences)
- **Service Layer Migration** (Phase 3A - Batches 1-14): 102 OperationResult/ServiceState occurrences migrated
  - Agent deployment & monitor services (8 occurrences)
  - Analyzer strategies (19 occurrences)
  - Subprocess & health check services (10 occurrences)
  - Unified service layer (4 occurrences)
  - Deployment strategies (8 occurrences)
  - Monitor services (3 occurrences)
  - Session & SocketIO services (5 occurrences)
  - Memory, diagnostics, & SocketIO main (5 occurrences)
  - MPM-Init command (20 occurrences - largest single file)
  - Core infrastructure: logging, events, registry (4 occurrences)
  - Core hooks: instruction reinforcement (5 occurrences)
  - Session handlers: interactive & oneshot (7 occurrences)
  - Subprocess launcher service (2 occurrences)
- **Type System Consolidation** (Phase 3A Batch 12): Eliminated 4 duplicate Literal types
  - `SessionStatus`: Literal → ServiceState enum
  - `ServiceStatus`: Literal → ServiceState enum
  - `ClaudeStatus.status`: Literal → ServiceState enum
  - `DelegationInfo.status`: Literal → OperationResult enum
  - Single source of truth for all status-related types
- **Service Layer Migration** (Phase 2): Type-safe severity handling
  - `interfaces.py`: AnalysisResult.severity default
  - `unified_analyzer.py`: All severity comparisons use ValidationSeverity
  - `validation_strategy.py`: ValidationRule severity handling
  - `mcp_check.py`: ServiceState enum for service lifecycle
- **Code Reduction**: frontmatter_validator.py - 56 lines of manual model normalization → 3 lines

### Fixed
- Linting issues from enum migration (undefined self, elif simplification, __all__ sorting, Yoda conditions)

## [4.14.8] - 2025-10-25

### Changed
- **Phase 3A Enum Migration** (Batches 1-14): Type system consolidation
  - 102 OperationResult/ServiceState occurrences migrated (11.6% complete)
  - Eliminated 4 duplicate Literal type definitions
  - Complete WebSocket status notification migration
  - All quality checks pass, 67 enum tests pass

## [4.14.7] - 2025-10-24

### Fixed
- Fixed output style deployment truncation bug in agent deployment
- Removed 180 lines of broken extraction logic from extract_output_style_content()
- Agent deployment now reads OUTPUT_STYLE.md directly instead of using broken content extraction
- Ensures complete output style instructions are deployed to all agents

## [4.14.6] - 2025-10-24

### Fixed
- Fixed OUTPUT_STYLE.md packaging issue in pipx installations
- PM agent now receives complete 290-line instruction set instead of truncated 11-line version
- Corrected package_data configuration to include full docs/developer/OUTPUT_STYLE.md

## [4.14.5] - 2025-10-23

### Fixed
- Fixed agentic-coder-optimizer agent to use markdown (.md) memory files instead of JSON
- Added explicit Memory File Format section to agent instructions
- Clarified naming convention: {agent-id}_memories.md
- Prevents agent from creating incorrect JSON-formatted memory files

## [4.14.4] - 2025-10-23

### Changed
- Project organization improvements per PROJECT_ORGANIZATION.md standard
- Moved planning documents to docs/planning/
- Cleaned up project root
- Removed unused TypeScript/Node.js configuration files

### Fixed
- Fixed cross-project memory contamination in PathResolver
- PathResolver now respects CLAUDE_MPM_USER_PWD environment variable
- Proper project-local path resolution for global installations

### Added
- Comprehensive Git File Tracking Protocol to base PM instructions
- Session Resume Capability for git-enabled projects
- PM can now resume sessions by inspecting git history
- Improved directory-aware PATH management for development workflow

## [4.14.3] - 2025-10-22

### Changed
- Version bump for patch release

## [4.14.2] - 2025-10-22

### Changed
- Version bump for patch release

## [4.14.1] - 2025-10-22

### Added
- **local-ops-agent v2.0.0**: Comprehensive multi-toolchain support for local deployments
  - Added Rust support: Actix-web, Rocket, Axum, Warp with Cargo build system
  - Added Go support: Gin, Echo, Fiber with Go modules and live reload
  - Added Java support: Spring Boot with Maven/Gradle and Spring Actuator health checks
  - Added Ruby support: Rails with Puma server
  - Added PHP support: Laravel with Artisan CLI
  - Added Dart support: Flutter Web deployments
  - Enhanced Node.js: Express, NestJS, Remix, SvelteKit, Astro
  - Enhanced Python: FastAPI with uvicorn workers and advanced configuration
  - CLI integration: Complete documentation for all 10 `local-deploy` commands
  - Best practices section: Port selection, health checks, auto-restart, log monitoring, graceful shutdown
  - 14 usage examples covering all major toolchains

### Changed
- local-ops-agent coverage increased from 40% to 95% (+137.5% improvement)
- Framework support expanded from 8 to 38 frameworks (+375%)
- Programming language support expanded from 3 to 8 languages (+166%)

## [4.14.0] - 2025-10-22

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






## [5.4.14] - 2025-12-20

### Fixed
- Automated release improvements

## [5.4.13] - 2025-12-20

### Fixed
- Automated release improvements

## [5.4.3] - 2025-12-15

### Fixed
- Automated release improvements

## [5.4.2] - 2025-12-15

### Fixed
- Automated release improvements

## [5.4.1] - 2025-12-15

### Fixed
- Automated release improvements

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

