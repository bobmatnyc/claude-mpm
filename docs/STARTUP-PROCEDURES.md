# Claude MPM Startup Procedures

**Complete initialization sequence from CLI launch to agent delegation**

## Overview

Claude MPM startup follows a multi-phase initialization sequence that prepares the system for agent delegation and task execution.

## Entry Points

1. **CLI Entry**: `src/claude_mpm/__main__.py` → `src/claude_mpm/cli/__init__.py::main()`
2. **Module Entry**: `python -m claude_mpm` → same flow

## Startup Sequence

### Phase 1: Early Environment Setup

**File**: `src/claude_mpm/cli/startup.py::setup_early_environment()`

**Actions**:
- Disable telemetry (`DISABLE_TELEMETRY=1`)
- Suppress ALL logging initially (until user preference loaded)
- Set `CLAUDE_MPM_SKIP_CLEANUP` for configure command
- Process command-line arguments

**Why**: Ensures clean environment before any logging/service initialization

### Phase 2: Argument Parsing & Validation

**File**: `src/claude_mpm/cli/__init__.py::main()`

**Actions**:
- Create argument parser with version info
- Preprocess arguments (expand aliases, handle special flags)
- Parse arguments into namespace object
- Check for configuration file existence
- Prompt for missing configuration (if needed)

**Why**: Validates user input and ensures project is properly configured

### Phase 3: Logging Configuration

**File**: `src/claude_mpm/cli/startup.py::setup_mcp_server_logging()`

**Actions**:
- Configure logging level based on user preference (default: OFF)
- MCP server mode: ERROR-level stderr-only logging
- Normal mode: User-configured logging level

**Why**: Respects user logging preferences, avoids polluting stdout in headless mode

### Phase 4: Startup Migrations

**File**: `src/claude_mpm/cli/startup_migrations.py::run_migrations()`

**Actions**:
- Run pending database/configuration migrations
- Returns list of applied migrations for banner display

**Why**: Ensures backward compatibility across version upgrades

### Phase 5: Startup Banner

**File**: `src/claude_mpm/cli/startup_display.py::display_startup_banner()`

**Actions**:
- Display Claude MPM version, project info
- Show applied migrations (if any)
- Display logging level setting

**Skipped for**: `--help`, `--version`, utility commands

### Phase 6: Background Services Initialization

**File**: `src/claude_mpm/cli/startup.py::run_background_services()`

**Skip conditions**:
- Help/version flags
- Utility commands: `info`, `doctor`, `config`, `configure`, `mcp`, `oauth`, `setup`, `tools`
- Headless mode with `--resume` flag (follow-up messages)

**Order of operations**:

1. **Hook Deployment** (`sync_hooks_on_startup`)
   - Cleanup stale user-level hooks (`~/.claude/hooks/claude-mpm/`)
   - Install project-level hooks (`.claude/settings.local.json`)
   - Shows: "✓ X hooks configured"

2. **Agent Sync** (`sync_remote_agents_on_startup`)
   - Sync from Git sources (`~/.claude-mpm/cache/agents/`)
   - Deploy to `.claude/agents/` (startup reconciliation)
   - Cleanup orphaned agents
   - Cleanup legacy cache directories
   - Save deployment state to prevent duplicate deployment
   - Shows: Progress bar + "X new, Y unchanged"

3. **Agent Summary** (`show_agent_summary`)
   - Shows: "✓ Agents: X deployed / Y cached"

4. **Project Registry** (`initialize_project_registry`)
   - Register/update current project in registry

5. **MCP Auto-Configuration** (`check_mcp_auto_configuration`)
   - Check if MCP needs configuration (pipx installs)
   - Offer one-time auto-configuration (with consent)
   - Skipped for: `doctor`, `configure` commands

6. **MCP Gateway Verification** (`verify_mcp_gateway_startup`)
   - Verify MCP gateway configuration (if not already configured)
   - Runs in background thread (non-blocking)

7. **Update Check** (`check_for_updates_async`)
   - Check for claude-mpm updates (background thread)
   - Respects `updates.check_enabled` config
   - Skips editable installs

8. **Bundled Skills Deployment** (`deploy_bundled_skills`)
   - Deploy skills from `src/claude_mpm/skills/bundled/`
   - Skips if `skills.auto_deploy = false`
   - Shows: "✓ Bundled skills ready (X deployed)"

9. **Remote Skills Sync** (`sync_remote_skills_on_startup`)
   - Sync from Git sources (`~/.claude-mpm/cache/skills/`)
   - Scan deployed agents for skill requirements
   - Save agent-referenced skills to `configuration.yaml`
   - Resolve deployment list (user_defined vs agent_referenced)
   - Apply profile filtering (if active profile)
   - Deploy to `.claude/skills/` with cleanup
   - Shows: Progress bar + "X new, Y unchanged, Z removed"

10. **Runtime Skills Discovery** (`discover_and_link_runtime_skills`)
    - Discover user-added skills in `.claude/skills/`
    - Shows: "✓ Runtime skills linked"

11. **Skill Summary** (`show_skill_summary`)
    - Shows: "✓ Skills: X deployed / Y cached"

12. **PM Skills Verification** (`verify_and_show_pm_skills`)
    - Verify required PM skills (8 framework skills)
    - Auto-repair if missing/corrupted
    - Shows: "✓ PM skills: 8/8 verified"

13. **Output Style Deployment** (`deploy_output_style_on_startup`)
    - Deploy output styles to `~/.claude/output-styles/`
    - Styles: `claude-mpm.md`, `claude-mpm-teacher.md`, `claude-mpm-research.md`
    - Shows: "✓ Output styles ready"

14. **Chrome DevTools Auto-Install** (`auto_install_chrome_devtools_on_startup`)
    - Install chrome-devtools-mcp if enabled
    - Configures in `.mcp.json`

**Result**: "✓ Launching Claude... Ready"

### Phase 7: Command Execution

**File**: `src/claude_mpm/cli/executor.py::execute_command()`

**Actions**:
- Route command to appropriate handler
- Default command: `run` (launch Claude Code)
- Execute and return exit code

---

## Agent Discovery & Deployment

### Cache Structure

```
~/.claude-mpm/cache/agents/
└── bobmatnyc/
    └── claude-mpm-agents/
        └── agents/
            ├── engineer/
            │   ├── python-engineer.md
            │   └── typescript-engineer.md
            ├── ops/
            │   └── local-ops.md
            └── ...
```

### Discovery Priority

1. **Project-level**: `.claude/agents/` (highest priority)
2. **User overrides**: `~/.claude-mpm/agents/`
3. **Cached remote**: `~/.claude-mpm/cache/agents/`

### Deployment Process

**Service**: `src/claude_mpm/services/agents/deployment/startup_reconciliation.py`

**Steps**:
1. Load `configuration.yaml` (enabled agents list)
2. Apply profile filtering (if active profile)
3. Scan cache for available agents
4. Compare with currently deployed agents
5. Deploy new agents, remove orphaned agents
6. Save deployment state (prevents duplicate deployment)

**Deployment State**: `.claude-mpm/cache/deployment_state.json`
```json
{
  "version": "5.7.23",
  "agent_count": 15,
  "deployment_hash": "sha256:...",
  "deployed_at": 1234567890.123
}
```

---

## Instructions Compilation

### Agent Instruction Structure

Each agent receives:
1. **BASE_AGENT.md** - Base instructions (inherited by all agents)
2. **Agent-specific instructions** - From agent template file
3. **Memory content** - From `.claude-mpm/memories/{agent}.md`
4. **Required skills** - Loaded dynamically when skill patterns detected

### BASE_AGENT Inheritance

**File**: `src/claude_mpm/agents/BASE_AGENT.md`

**Provides**:
- Git workflow standards
- Memory routing patterns
- Output format standards
- Handoff protocol
- Proactive code quality improvements

### Memory Integration

**Backend Types**:
- **Static**: File-based (`.claude-mpm/memories/*.md`)
- **Kuzu**: Graph-based (`kuzu-memories/` directory)

**Memory Routing**:
- Defined in agent JSON templates: `memory_routing_rules`
- Examples:
  - Engineer: implementation patterns, architecture decisions
  - Research: analysis findings, domain knowledge
  - QA: testing strategies, bug patterns

### Local File Override

**Priority order**:
1. `.claude/agents/{agent-name}.md` (project-local override)
2. `~/.claude-mpm/agents/{agent-name}.md` (user-level override)
3. `~/.claude-mpm/cache/agents/.../agents/{agent-name}.md` (remote cached)

---

## Dynamic Delegation Authority

### PM Instruction Assembly

**File**: `src/claude_mpm/instructions/PM_INSTRUCTIONS.md`

**Dynamic Sections**:
1. **Available Agent Capabilities** - Generated from deployed agents
2. **Context-Aware Agent Selection** - Routing matrix built at runtime
3. **Memory Integration** - PM's accumulated project knowledge

### Agent Capability Detection

**Source**: Agent JSON templates (`src/claude_mpm/agents/templates/*.json`)

**Extracted metadata**:
- `agent_id`: Unique identifier
- `description`: Agent capabilities summary
- `authority_keywords`: Trigger words for delegation
- `memory_routing_rules`: Knowledge categories to remember

### Delegation Matrix Construction

**Runtime process**:
1. Scan `.claude/agents/` for deployed agents
2. Parse frontmatter metadata from each agent file
3. Extract `agent_id`, `description`, `authority_keywords`
4. Build routing table: `{keywords} → {agent_id}`
5. Inject into PM instructions as "Available Agent Capabilities"

**Result**: PM knows which agents are available and when to delegate to each

### Context-Aware Selection

**Triggers**:
- **Keyword matching**: User request contains agent's authority keywords
- **Task type**: Implementation → engineer, Testing → qa, Deployment → ops
- **Platform-specific**: "vercel" → vercel-ops, "localhost" → local-ops
- **Language-specific**: "python" → python-engineer, "typescript" → typescript-engineer

---

## Configuration Files

### Main Configuration

**File**: `.claude-mpm/configuration.yaml`

**Purpose**: Project-specific settings

**Key sections**:
```yaml
agents:
  enabled: [list of agent IDs]

skills:
  auto_deploy: true
  agent_referenced: [skills from agent scan]
  user_defined: [explicitly enabled skills]

memory:
  backend: kuzu  # or 'static'

updates:
  check_enabled: true
  check_frequency: daily
```

### Profile Configuration

**File**: `.claude-mpm/profiles/{profile-name}.yaml`

**Purpose**: Agent/skill filtering for specific contexts

**Example**:
```yaml
name: "backend-only"
agents:
  enabled:
    - python-engineer
    - local-ops
    - api-qa
skills:
  disabled_patterns:
    - "toolchains-javascript-*"
    - "toolchains-typescript-*"
```

---

## Setup Commands

### `claude-mpm setup kuzu-memory`

**Flow**:
1. Check kuzu-memory installation (install if needed)
2. Migrate existing static memory files to kuzu
3. Update `.claude-mpm/configuration.yaml` → `memory.backend = kuzu`
4. Create `.kuzu-memory-config` (subservient mode)
5. Launch claude-mpm (unless `--no-start`)

### `claude-mpm setup slack`

**Flow**:
1. Run `scripts/setup/setup-slack-app.sh`
2. Configure `.mcp.json` with slack-user-proxy server
3. Launch claude-mpm (unless `--no-launch`)

### `claude-mpm setup google-workspace-mcp`

**Flow**:
1. Delegate to OAuth setup
2. Configure OAuth credentials
3. Launch claude-mpm (unless `--no-launch`)

---

## Key Optimizations

### ETag-Based Caching
- Agent/skill sync uses HTTP ETag headers
- 95%+ bandwidth reduction on repeated syncs
- Only downloads changed files

### Deployment State Tracking
- Prevents duplicate agent deployment
- Hash-based change detection
- Saved after reconciliation

### Background Threading
- Update checks run in daemon thread
- MCP gateway verification runs in background
- Non-blocking for faster startup

### Profile Filtering
- Reduces deployed agents/skills to project needs
- Applied during reconciliation phase
- Saves disk space and reduces clutter

---

## Troubleshooting

### Slow Startup
- Check network connectivity (agent/skill sync)
- Review `.claude-mpm/logs/` for bottlenecks
- Use `--force-sync` to bypass ETag cache

### Missing Agents
- Check `configuration.yaml` → `agents.enabled`
- Verify active profile isn't filtering agents
- Run `claude-mpm doctor` for diagnostics

### Memory Issues
- Check `memory.backend` setting in `configuration.yaml`
- Verify kuzu-memory installation: `kuzu-memory --version`
- Check memory file permissions in `.claude-mpm/memories/`

---

**Last Updated**: 2026-02-10
**Version**: 5.7.23
