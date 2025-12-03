# Claude MPM Framework - Project Memory Configuration

This codebase IS the Claude MPM framework source code. It uses KuzuMemory for intelligent context management.

## PROJECT vs FRAMEWORK Distinction (CRITICAL)

**This codebase IS the FRAMEWORK** (Claude MPM framework source code)

- **FRAMEWORK**: This repository - the Claude MPM framework source code
  - Location: `/Users/masa/Projects/claude-mpm`
  - Purpose: Develop and maintain the Claude MPM framework
  - Cache: `~/.claude-mpm/cache/remote-agents/` (agent repository)
  - Deployment: Agents deployed from cache to project `.claude/agents/`

- **PROJECT**: User installations that USE this framework
  - Location: Any directory where `mpm-init` has been run
  - Purpose: Use Claude MPM for multi-agent orchestration
  - Configuration: `.claude-mpm/` in project root
  - Agents: Deployed to `.claude/agents/` from framework cache

**Key Distinction:**
- When working on THIS codebase: You're developing the FRAMEWORK
- When using `claude-mpm` in another directory: You're using it as a PROJECT

## Framework Information

- **Path**: /Users/masa/Projects/claude-mpm
- **Type**: Python CLI framework for multi-agent orchestration
- **Purpose**: Claude Multi-Agent Project Manager - Orchestrate Claude with agent delegation and ticket tracking

## Key Technologies

- **Language**: Python 3.10+
- **CLI Framework**: Click
- **Agent System**: Multi-agent orchestration with JSON templates
- **Ticketing**: MCP-based (mcp-ticketer) with CLI fallback
- **Memory**: KuzuMemory for context management
- **Version Control**: Git-based agent synchronization
- **Cache Architecture**: `~/.claude-mpm/cache/remote-agents/`

## Cache Directory Architecture

### Framework Cache Structure

- **Primary Cache**: `~/.claude-mpm/cache/remote-agents/`
  - Git repository cache with full metadata
  - Multi-repository support
  - ETag-based sync optimization
  - Contains 45+ agent templates

### Deployment Flow

1. **Startup Sync**: Framework syncs agents from GitHub to cache
2. **Agent Discovery**: RemoteAgentDiscoveryService parses markdown
3. **Version-Aware Copy**: Agents deployed to project `.claude/agents/`
4. **Runtime Discovery**: Claude Code discovers agents in project

### Legacy Note

- `cache/agents/` is deprecated (legacy flat structure)
- All new code should use `cache/remote-agents/` only

## Agent Deployment Model

### Standard Deployment Workflow

1. **Update Agent**: Modify agent in framework cache
2. **Sync Changes**: Git pull or ETag sync on startup
3. **Deploy to Project**: Use `mpm-agents-deploy` or auto-deployment
4. **Verify**: Check `.claude/agents/` for updated files

### Cache Update Process

- **Automatic**: Startup sync pulls latest agents (ETag-cached)
- **Manual**: `mpm-agents-sync` or `git pull` in cache directory
- **Development**: Edit `~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/*.md`

## Memory Integration

KuzuMemory is configured to enhance all AI interactions with project-specific context.

### Available Commands

- `kuzu-memory enhance <prompt>` - Enhance prompts with project context
- `kuzu-memory learn <content>` - Store learning from conversations (async)
- `kuzu-memory recall <query>` - Query project memories
- `kuzu-memory stats` - View memory statistics

### MCP Tools Available

When interacting with Claude Desktop, the following MCP tools are available:

- **kuzu_enhance**: Enhance prompts with project memories
- **kuzu_learn**: Store new learnings asynchronously
- **kuzu_recall**: Query specific memories
- **kuzu_stats**: Get memory system statistics

## Framework Development Guidelines

### When Developing the Framework

1. **Agent Templates**: Edit in `src/claude_mpm/agents/templates/*.json`
2. **Cache Operations**: Always use `remote-agents/` path, never legacy `agents/`
3. **Startup Behavior**: Test with `agent_sync.enabled = true` (default)
4. **Testing**: Run `make test` before commits
5. **Documentation**: Update docs when adding features

### When Testing Framework Changes

1. **Test in isolated project**: Create test directory, run `mpm-init`
2. **Agent deployment**: Verify agents deploy to `.claude/agents/`
3. **Cache verification**: Check `~/.claude-mpm/cache/remote-agents/`
4. **Startup sync**: Test with fresh cache (delete and re-sync)

### Contributing to Framework Agents

**See detailed guide**: [docs/developer/agent-modification-workflow.md](docs/developer/agent-modification-workflow.md)

The agent cache at `~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/` is a full git repository. To contribute:

1. Edit agents in the cache directory
2. Commit with conventional commit messages
3. Test locally with `claude-mpm run`
4. Push to GitHub or create PR

This workflow enables contributions to the official Claude MPM agent repository.

### Memory Storage (Framework Development)

- Store framework architecture decisions
- Document API design patterns
- Record agent template conventions
- Capture build/release procedures
- Use kuzu-memory enhance for all AI interactions
- Store important decisions with kuzu-memory learn
- Query context with kuzu-memory recall when needed
- Keep memories project-specific and relevant

## Memory Guidelines

- Store project decisions and conventions
- Record technical specifications and API details
- Capture user preferences and patterns
- Document error solutions and workarounds
- Focus on framework architecture and design patterns
- Document agent deployment workflows
- Record cache synchronization behavior

---

*Generated by KuzuMemory Claude Hooks Installer*
*Updated for Claude MPM framework specificity*
