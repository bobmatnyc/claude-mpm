# Project Memory Configuration

This project uses KuzuMemory for intelligent context management.

## Project Information
- **Path**: /Users/masa/Projects/claude-mpm
- **Language**: Python
- **Framework**: Flask

## Memory Integration

KuzuMemory is configured to enhance all AI interactions with project-specific context.

### Available Commands:
- `kuzu-memory enhance <prompt>` - Enhance prompts with project context
- `kuzu-memory learn <content>` - Store learning from conversations (async)
- `kuzu-memory recall <query>` - Query project memories
- `kuzu-memory stats` - View memory statistics

### MCP Tools Available:
When interacting with Claude Desktop, the following MCP tools are available:
- **kuzu_enhance**: Enhance prompts with project memories
- **kuzu_learn**: Store new learnings asynchronously
- **kuzu_recall**: Query specific memories
- **kuzu_stats**: Get memory system statistics

## Project Context

Claude Multi-Agent Project Manager - Orchestrate Claude with agent delegation and ticket tracking

## Key Technologies
- Python
- Flask
- Flask

## Development Guidelines

**📚 IMPORTANT: Read [CONTRIBUTING.md](CONTRIBUTING.md) first for complete development guidelines.**

CONTRIBUTING.md is your primary guide for:
- **Quality Workflow**: `make lint-fix`, `make quality`, `make safe-release-build`
- **Code Structure**: Where files belong (scripts, tests, modules)
- **Commit Guidelines**: Conventional commits format (feat:, fix:, docs:, etc.)
- **Testing Requirements**: 85%+ coverage, comprehensive test suites
- **Architecture Standards**: Service-oriented architecture, interface contracts

### Quick Development Commands

```bash
# During development - auto-fix issues
make lint-fix

# Before every commit - comprehensive checks
make quality

# For releases - quality gate + build
make safe-release-build
```

### Project Organization

- See [CONTRIBUTING.md](CONTRIBUTING.md) for complete file placement rules
- ALL scripts go in `/scripts/`, NEVER in project root
- ALL tests go in `/tests/`, NEVER in project root
- Python modules always under `/src/claude_mpm/`

### Memory Integration (KuzuMemory)

- Use kuzu-memory enhance for all AI interactions
- Store important decisions with kuzu-memory learn
- Query context with kuzu-memory recall when needed
- Keep memories project-specific and relevant

## 🎯 Framework vs. Project Work - CRITICAL DISTINCTION

### When Working ON Claude MPM Framework

**IMPORTANT**: If you're working on Claude MPM itself (not using it for another project), follow these rules:

**Source of Truth**:
- ✅ All changes go in `/src/claude_mpm/` directory
- ✅ Agent templates: `/src/claude_mpm/agents/templates/*.json`
- ✅ PM instructions: `/src/claude_mpm/agents/PM_INSTRUCTIONS.md`
- ✅ Scripts: `/scripts/` directory
- ✅ Tests: `/tests/` directory

**NEVER Modify Deployed Files**:
- ❌ DO NOT edit `~/.claude/agents/` (deployed agents)
- ❌ DO NOT edit `.claude-mpm/agents/` (project-local agents)
- ❌ DO NOT edit installed package files

**Correct Workflow**:
1. Modify source files in `/src/claude_mpm/`
2. Test changes with `make quality`
3. Redeploy agents: `claude-mpm agents deploy <agent-name> --force`
4. Verify changes took effect

**Detection Rule**: If current working directory is `/Users/masa/Projects/claude-mpm`, you're working ON the framework.

### When Using Claude MPM For Your Project

**IMPORTANT**: If you're using Claude MPM to manage another project, these rules apply:

**Project Files**:
- ✅ Work with files in your project directory
- ✅ Use deployed agents from `~/.claude/agents/`
- ✅ Follow project-specific conventions

**Framework Updates**:
- ⚠️ If you need framework changes, switch to framework work mode
- ⚠️ Update source → test → redeploy → resume project work

### Quick Check

**Am I working on framework or project?**
```bash
pwd  # Check current directory
# If /Users/masa/Projects/claude-mpm → Framework work
# If anything else → Project work
```

**Framework work indicators**:
- Modifying agent templates
- Updating PM instructions
- Changing core functionality
- Adding new features to Claude MPM
- Fixing bugs in the framework

**Project work indicators**:
- Building a web application
- Implementing features for a client
- Using agents to manage tickets
- Normal development workflow

### Common Mistakes

❌ **WRONG**: Editing `~/.claude/agents/research_agent.md` to fix Research agent
✅ **CORRECT**: Edit `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/research.json`, then redeploy

❌ **WRONG**: Modifying `.claude-mpm/agents/PM_INSTRUCTIONS.md` in project
✅ **CORRECT**: Edit `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/PM_INSTRUCTIONS.md`, then redeploy

❌ **WRONG**: Testing framework changes without redeployment
✅ **CORRECT**: Source change → `make quality` → `claude-mpm agents deploy --force` → Test

## Memory Guidelines

- Store project decisions and conventions
- Record technical specifications and API details
- Capture user preferences and patterns
- Document error solutions and workarounds

## Deployment and Release

**Complete deployment guide**: See [docs/reference/DEPLOY.md](docs/reference/DEPLOY.md)

### Homebrew Tap Integration

The Homebrew tap is automatically updated during release workflow (Phase 5.5):

**Quick Commands**:
```bash
# Test update without changes
make update-homebrew-tap-dry-run

# Trigger manual update (if automation fails)
make update-homebrew-tap

# Update via manage_version script
./scripts/manage_version.py update-homebrew --dry-run
```

**Automatic Integration**:
- Runs automatically during `make release-publish`
- Non-blocking: Homebrew failures don't stop PyPI releases
- Phase 1: Requires manual push confirmation
- Retry logic: 10 attempts with exponential backoff

**Manual Fallback** (if automation fails):
```bash
cd /path/to/homebrew-tools
./scripts/update_formula.sh $(cat VERSION)
git add Formula/claude-mpm.rb
git commit -m "feat: update to v$(cat VERSION)"
git push origin main
```

**Key Points**:
- ✅ Non-blocking design ensures PyPI always releases
- ✅ Automatic SHA256 fetching from PyPI
- ✅ Local formula testing before commit
- ✅ Comprehensive error handling and logging
- ⚠️ See [docs/reference/HOMEBREW_UPDATE_TROUBLESHOOTING.md](docs/reference/HOMEBREW_UPDATE_TROUBLESHOOTING.md) for troubleshooting

---

*Generated by KuzuMemory Claude Hooks Installer*
