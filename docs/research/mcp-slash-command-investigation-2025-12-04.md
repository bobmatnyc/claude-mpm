# `/mcp` Slash Command Investigation

**Research Date:** 2025-12-04
**Project:** Claude MPM Framework
**Context:** User mentioned "/mcp was turned into a local slash command" - investigation needed
**Researcher:** Research Agent

---

## Executive Summary

**KEY FINDING:** `/mcp` is a **native built-in Claude Code command**, NOT a Claude MPM custom command.

**What `/mcp` is:**
- Built-in Claude Code slash command (part of Claude Desktop/Claude Code platform)
- Opens MCP (Model Context Protocol) configuration interface
- Allows users to add, remove, or configure MCP servers
- Manages connections to external tools and services (GitHub, Jira, databases, etc.)

**What changed:**
- **NOTHING changed with `/mcp` itself** - it remains a Claude platform command
- User's statement "turned into a local slash command" is **inaccurate**
- `/mcp` was NEVER a Claude MPM custom command
- Claude MPM has NEVER had a `/mcp` slash command in its source

**Recommendation:**
- No action needed - `/mcp` is correctly functioning as a Claude Code built-in
- No cleanup required in Claude MPM codebase (never existed)
- User may have been confused about command ownership (Claude vs Claude MPM)

---

## 1. What is `/mcp`?

### 1.1 Origin and Purpose

**Source:** Claude Code Built-in Command (Anthropic Platform)

**Purpose:**
- Opens Model Context Protocol (MCP) configuration interface
- Manages MCP server installations and connections
- Configures external tool integrations

**Usage:**
```
/mcp
```

**When to use:**
- Need to connect Claude to external services
- Want to add MCP servers (mcp-ticketer, mcp-browser, etc.)
- Configure database connections, APIs, or automation tools
- Manage existing MCP server configurations

### 1.2 Platform Context

**Built-in Claude Code Slash Commands:**
- `/help` - Display all available slash commands
- `/mcp` - MCP server configuration interface
- `/agent` - Create and manage specialized AI subagents
- `/hooks` - Configure PreToolUse and PostToolUse hooks

**Timeline:**
- **MCP Protocol:** Introduced 2024
- **Claude Code Core:** Released February 2025
- **Plugins Support:** Added 2025
- **Agent Skills:** Introduced October 2025

---

## 2. Investigation of User Statement

### 2.1 User's Claim

> "/mcp was turned into a local slash command"

### 2.2 Analysis

**Evidence Review:**

1. **Git History Search:**
   - Searched all commits mentioning "mcp" or "/mcp"
   - Found ZERO commits adding or removing `/mcp` slash command
   - Found NO source file: `src/claude_mpm/commands/mcp.md`
   - Found NO deployment of `/mcp` to `~/.claude/commands/`

2. **Codebase Search:**
   - Searched for `/mcp` in all markdown files
   - Found NO slash command definition for `/mcp`
   - Found NO documentation about `/mcp` as MPM command

3. **Command Deployment Service:**
   - Reviewed `src/claude_mpm/services/command_deployment_service.py`
   - No logic for deploying `/mcp` command
   - Only deploys files from `src/claude_mpm/commands/*.md`

4. **User's `.claude/commands/` Directory:**
   - Checked for `mcp.md` in deployed commands
   - NOT FOUND - no mcp.md file exists

**Conclusion:** `/mcp` was NEVER a Claude MPM command. It has always been a Claude Code built-in.

### 2.3 Possible User Confusion

**Likely Scenario:**
- User saw `/mcp` in Claude Code slash command list
- User assumed it was a Claude MPM command (because it's related to MCP)
- User misinterpreted its origin as "turned into" local command
- Actually: `/mcp` was always a Claude platform built-in, never changed

**Evidence for Confusion:**
- Claude MPM **uses** MCP services (mcp-ticketer, mcp-browser, mcp-vector-search)
- Claude MPM **manages** MCP service availability checks
- Claude MPM does NOT **implement** the `/mcp` command itself
- Users might conflate "uses MCP" with "owns /mcp command"

---

## 3. Claude MPM's MCP Integration

### 3.1 What Claude MPM Actually Does

**MCP Service Management:**
- Checks if MCP services are available (READ-ONLY)
- Provides installation instructions if missing
- Configures which services to **expect** (not install)
- NEVER modifies `~/.claude.json` (as of v5.0.7+)

**Key Files:**
- `src/claude_mpm/services/mcp_config_manager.py` - Service availability checks
- `src/claude_mpm/services/mcp_service_verifier.py` - Verification logic
- `config/mcp_services.yaml` - Expected MCP services configuration

**User Responsibility:**
- Install MCP servers: `pip install mcp-ticketer mcp-browser mcp-vector-search`
- Configure via Claude Desktop UI or manually edit `~/.claude.json`
- Claude MPM only checks availability (since v5.0.7)

### 3.2 Recent MCP Changes in Claude MPM

**v5.0.7 (2025-12-04) - MCP Auto-Configuration Removal:**
- Removed auto-modification of `~/.claude.json`
- Deprecated `MCPConfigManager.ensure_mcp_services_configured()`
- Added read-only check: `check_mcp_services_available()`
- Users now must manually install and configure MCP services

**Documentation:**
- `docs/developer/mcp-auto-config-removal.md` - Comprehensive removal guide
- Breaking change: Users responsible for MCP service installation

**Impact:**
- Claude MPM no longer touches MCP server configurations
- `/mcp` command ownership remains with Claude Code platform
- Clear separation: Platform manages MCP, MPM uses MCP

---

## 4. Slash Command Ownership Clarification

### 4.1 Claude Code Built-in Commands

**Owned by:** Anthropic (Claude Code Platform)
**Location:** Claude Desktop/Claude Code internal system
**Examples:**
- `/help` - Help system
- `/mcp` - MCP configuration
- `/agent` - Subagent management
- `/hooks` - Hook configuration

**Characteristics:**
- Always available in Claude Code
- Not stored in `~/.claude/commands/`
- Cannot be customized or removed by users
- Managed by Anthropic platform updates

### 4.2 Claude MPM Custom Commands

**Owned by:** Claude MPM Framework (bobmatnyc/claude-mpm)
**Location:** `src/claude_mpm/commands/*.md` → `~/.claude/commands/*.md`
**Examples:**
- `/mpm` - Main MPM entry point
- `/mpm-agents-list` - List available agents
- `/mpm-status` - Show MPM status
- `/mpm-ticket-view` - View ticket details
- `/mpm-doctor` - Run diagnostics

**Characteristics:**
- Deployed by Claude MPM on startup
- Stored as markdown files in `~/.claude/commands/`
- Can be customized by editing source files
- Managed by `command_deployment_service.py`

### 4.3 Naming Convention Protection

**Why `/mpm` prefix exists:**
- Prevents namespace collision with Claude Code built-ins
- Clear separation: `/mpm-*` = MPM commands, others = platform commands
- Example: `/help` (Claude) vs `/mpm-help` (MPM-specific help)

**If `/mcp` were an MPM command:**
- It would be named `/mpm-mcp` to avoid collision
- It would exist in `src/claude_mpm/commands/mpm-mcp.md`
- It would be deployed to `~/.claude/commands/mpm-mcp.md`
- **NONE OF THIS EXISTS** - confirming `/mcp` is NOT an MPM command

---

## 5. Timeline Analysis

### 5.1 `/mcp` Command History

**Claude Code Platform:**
- 2024: MCP protocol introduced by Anthropic
- Feb 2025: Claude Code launched with `/mcp` built-in
- 2025: MCP server ecosystem grows (ticketer, browser, vector-search)
- **Status:** `/mcp` has been a built-in since Claude Code launch

**Claude MPM Framework:**
- Never implemented `/mcp` command
- Always delegated MCP configuration to Claude platform
- Used MCP services via mcp-ticketer, mcp-browser, etc.
- **Status:** No `/mcp` command in any version

### 5.2 Recent Deprecated Command Cleanup

**Context from Git History:**

**v5.0.4 (2025-12-03) - Deprecated Command Cleanup:**
- Auto-removed deprecated `/mpm` commands on startup
- Commands deprecated: `/mpm-agents`, `/mpm-config`, `/mpm-ticket`, etc.
- Migrated to hierarchical naming: `/mpm-agents-list`, `/mpm-config-view`, etc.

**v5.0.5 (2025-12-03) - Hide Deprecated Aliases:**
- Moved deprecated aliases to `deprecated_aliases` field
- Prevented deprecated commands from showing in UI
- Cleaner command lists for users

**Audit Document:**
- `docs/research/deprecated-mpm-commands-audit-2025-12-03.md`
- Confirmed all deprecated `/mpm-*` commands removed
- **NO MENTION OF `/mcp` IN ANY AUDIT** - because it's not an MPM command

**User Likely Confused:**
- Saw deprecation cleanup of `/mpm-*` commands
- Misinterpreted this as affecting `/mcp` (similar naming)
- Actually: `/mcp` unaffected by Claude MPM command cleanup

---

## 6. Verification Evidence

### 6.1 Git History Evidence

**Commands Searched:**
```bash
# Search for /mcp in git history
git log --all --oneline --grep="/mcp" -i

# Search for mcp.md file
git log --all --oneline --follow -- "**/mcp.md"

# Search for MCP-related commits
git log --all --oneline --grep="mcp" | head -20
```

**Results:**
- Found MCP-related commits (service management, auto-config removal)
- Found ZERO commits adding/removing `/mcp` slash command
- Found NO file history for `mcp.md` command file

### 6.2 File System Evidence

**Source Directory:**
```bash
ls -la /Users/masa/Projects/claude-mpm/src/claude_mpm/commands/
```

**Files Present:**
- ✅ `mpm.md` - Main MPM command
- ✅ `mpm-agents-list.md` - Agent listing
- ✅ `mpm-config-view.md` - Config viewing
- ❌ `mcp.md` - NOT FOUND

**Deployed Directory:**
```bash
ls -la ~/.claude/commands/ | grep -i mcp
```

**Result:**
- NO `mcp.md` file in user's commands directory
- NO MCP-related command files deployed by MPM

### 6.3 Code Search Evidence

**Pattern Search:**
```bash
grep -r "^/mcp" **/*.md
```

**Results:**
- Found `/mpm` commands (MPM-owned)
- Found NO `/mcp` command definitions
- Found references to MCP services (not slash commands)

---

## 7. Recommendation

### 7.1 Current Status Assessment

**Status:** ✅ **NO ACTION REQUIRED**

**Rationale:**
1. `/mcp` is correctly functioning as Claude Code built-in
2. Claude MPM never owned or implemented `/mcp` command
3. No cleanup needed (command never existed in MPM codebase)
4. User statement appears to be based on confusion

### 7.2 If User Wants to Remove `/mcp`

**Option 1: Not Possible**
- `/mcp` is a Claude Code built-in
- Cannot be removed or disabled by users
- Part of core Claude Code functionality

**Option 2: Hide from UI (Not Recommended)**
- Would require hacking Claude Code internals
- Not supported or recommended approach
- Would break MCP configuration functionality

**Option 3: Educate User**
- Explain `/mcp` is Claude Code built-in
- Clarify distinction between Claude and MPM commands
- Show how to use `/mcp` for MCP server management

### 7.3 If User Wants MCP-Related MPM Command

**Current Approach:**
- Users use native `/mcp` for MCP server configuration
- Claude MPM checks MCP service availability via `mcp_config_manager.py`
- Clear separation of concerns

**Alternative (Not Recommended):**
- Could create `/mpm-mcp-status` command
- Would check MCP service availability (read-only)
- Duplicates functionality of `check_mcp_services_available()`
- Adds unnecessary complexity

### 7.4 Documentation Improvement

**Add to User Guide:**
```markdown
## Claude Code vs Claude MPM Commands

### Claude Code Built-in Commands
- `/help` - Platform help
- `/mcp` - MCP server configuration
- `/agent` - Subagent management
- `/hooks` - Hook configuration

### Claude MPM Custom Commands
- `/mpm` - MPM main menu
- `/mpm-agents-list` - List MPM agents
- `/mpm-status` - MPM system status
- `/mpm-doctor` - MPM diagnostics

**Note:** Claude MPM does NOT implement `/mcp`. Use the native
Claude Code `/mcp` command for MCP server configuration.
```

---

## 8. Questions Answered

### 8.1 What was `/mcp` originally?

**Answer:** Native Claude Code built-in command for MCP server configuration.

**Evidence:**
- Part of Claude Code platform since February 2025
- Implemented by Anthropic, not Claude MPM
- Never existed as MPM custom command

### 8.2 What changed?

**Answer:** NOTHING changed with `/mcp` itself.

**What DID change (v5.0.7):**
- Claude MPM stopped auto-configuring MCP services in `~/.claude.json`
- Users now manually install/configure MCP servers
- Claude MPM only checks MCP service availability (read-only)

**User Confusion:**
- Likely conflated MCP service management changes with `/mcp` command
- Actually: Service management policy changed, command unchanged

### 8.3 Is this Claude or project change?

**Answer:** Mixed - but NOT about `/mcp` command.

**Claude Code Platform:**
- `/mcp` command unchanged (always been built-in)
- MCP protocol and ecosystem growing

**Claude MPM Project (v5.0.7):**
- Changed MCP service management approach
- Removed auto-configuration of `~/.claude.json`
- Made MCP services user-controlled
- `/mcp` command unaffected (never owned by MPM)

### 8.4 Should we keep or remove `/mcp`?

**Answer:** CANNOT remove - it's a Claude Code built-in.

**Options:**
- Keep as-is (recommended): Users use native `/mcp` for MCP config
- Document distinction: Clarify Claude vs MPM command ownership
- No cleanup needed: `/mcp` was never in Claude MPM codebase

---

## 9. Related Documentation

### 9.1 MCP Service Management

**Recent Changes:**
- `docs/developer/mcp-auto-config-removal.md` - v5.0.7 removal guide
- Stopped auto-configuring `~/.claude.json`
- Users now manually install MCP servers

### 9.2 Deprecated Command Cleanup

**Recent Audits:**
- `docs/research/deprecated-mpm-commands-audit-2025-12-03.md`
- Removed 6 deprecated `/mpm-*` commands
- Migrated to hierarchical naming
- **NO `/mcp` MENTIONED** - not an MPM command

### 9.3 Slash Command Architecture

**Research Documents:**
- `docs/research/slash-command-structure-2025-11-29.md`
- How Claude MPM slash commands work
- Deployment from `src/claude_mpm/commands/` to `~/.claude/commands/`
- Naming convention: `/mpm-*` prefix

---

## 10. Conclusion

**Summary:**

1. **`/mcp` is a Claude Code built-in command** - owned by Anthropic platform
2. **Claude MPM has NEVER implemented `/mcp`** - confirmed via git history and file system
3. **User's statement is inaccurate** - likely confusion about command ownership
4. **No action required** - `/mcp` correctly functioning as intended
5. **Recent MCP changes** - only affected service management, not `/mcp` command

**User Education Needed:**
- Explain distinction between Claude Code built-ins and MPM custom commands
- Clarify `/mcp` is for MCP server configuration (platform feature)
- Show how Claude MPM uses MCP services (not manages `/mcp` command)

**Final Recommendation:**
- Document command ownership in user guide
- Add clarification to TROUBLESHOOTING.md
- No code changes required in Claude MPM
- Consider adding `/mpm-mcp-status` if users need MPM-specific MCP checks (optional)

---

**Research Status:** ✅ COMPLETE
**Action Required:** Documentation improvement only
**Code Changes:** None needed
**User Communication:** Clarify command ownership distinction

---

## 11. Web Research Citations

### Source 1: Claude Code Slash Commands Guide
- **URL:** https://alexop.dev/posts/claude-code-slash-commands-guide/
- **Title:** "How to Speed Up Your Claude Code Experience with Slash Commands"
- **Key Finding:** `/mcp` opens MCP configuration interface for adding/removing MCP servers
- **Evidence:** Built-in Claude Code command, not project-specific

### Source 2: Claude Code Documentation
- **URL:** https://code.claude.com/docs/en/slash-commands
- **Title:** "Slash commands - Claude Code Docs"
- **Key Finding:** Built-in commands stored as prompt templates in `.claude/commands`
- **Evidence:** Platform commands vs custom commands distinction

### Source 3: Anthropic Engineering Blog
- **URL:** https://www.anthropic.com/engineering/claude-code-best-practices
- **Title:** "Claude Code: Best practices for agentic coding"
- **Key Finding:** MCP integration is core Claude Code feature
- **Evidence:** Platform-level support for MCP, not third-party implementation

### Source 4: First Principles Consulting Guide
- **URL:** https://firstprinciplescg.com/resources/claude-code-slash-commands-the-complete-reference-guide/
- **Title:** "Claude Code Slash Commands - The Complete Reference Guide"
- **Key Finding:** `/mcp` listed as built-in command for MCP server management
- **Evidence:** Confirms platform ownership of `/mcp` command

---

**Token Usage Note:** This research used ~75K tokens to thoroughly investigate the user's claim. The comprehensive analysis confirms NO action is needed regarding `/mcp` command in Claude MPM codebase.
