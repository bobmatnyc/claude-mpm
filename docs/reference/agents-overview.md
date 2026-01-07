# Agent System Overview

Complete guide to Claude MPM's multi-agent system for orchestrated task execution.

## Quick Start

- **New to agents?** Start with [agents/pm-workflow.md](../agents/pm-workflow.md) to understand orchestration
- **Creating agents?** Follow [agents/creating-agents.md](../agents/creating-agents.md) step-by-step guide
- **Learning patterns?** Study [agents/agent-patterns.md](../agents/agent-patterns.md) for best practices
- **Reference needed?** Browse [agents/agent-capabilities-reference.md](../agents/agent-capabilities-reference.md) for all agents

## System Overview

Claude MPM uses a three-tier agent hierarchy with the PM agent orchestrating workflow:

```
User Request
     ↓
  PM Agent (orchestrator)
     ↓
  ├─→ Research Agent (analysis)
  ├─→ Engineer Agent (implementation)
  ├─→ QA Agent (testing)
  └─→ Documentation Agent (docs)
```

## Three-Tier Agent System

Agents are loaded with the following precedence (highest to lowest):

1. **PROJECT** (`.claude-mpm/agents/`) - Highest priority, project-specific
2. **USER** (`~/.claude-agents/`) - Personal customizations
3. **SYSTEM** (bundled) - Default agents included with Claude MPM

## Core Agents (16 Specialized Agents)

### Core Development
- **Engineer** - Software development and implementation
- **Research** - Code analysis and research
- **Documentation** - Documentation creation and maintenance
- **QA** - Testing and quality assurance
- **Security** - Security analysis and implementation

### Language-Specific Engineers
- **Python Engineer (v2.3.0)** - Type-safe, async-first Python with SOA patterns
  - Service-oriented architecture with ABC interfaces for applications
  - Lightweight script patterns for automation and one-off tasks
  - Dependency injection containers with auto-resolution

- **JavaScript Engineer (v1.0.0)** - Vanilla JavaScript specialist
  - Node.js backend frameworks (Express, Fastify, Koa, Hapi)
  - Browser extensions (Chrome, Firefox) with Manifest V3
  - Web Components (Custom Elements, Shadow DOM)
  - Modern ESM patterns and CommonJS interop
  - Build tooling (Vite, esbuild, Rollup, Webpack)
  - Testing with Vitest, Jest, Mocha
  - **When to Use**: Backend APIs without TypeScript, browser extensions, Web Components, CLI tools, legacy jQuery modernization
  - **Routing**: Priority 80, triggers on `express`, `fastify`, `browser extension`, `web components`, vanilla JS file patterns

- **Rust Engineer (v1.1.0)** - Memory-safe, high-performance systems
  - Trait-based service architecture
  - Dependency injection patterns
  - Async programming with tokio

### Operations & Infrastructure
- **Ops** - Operations and deployment with git commit authority (v2.2.2+)
- **Version Control** - Git and version management
- **Data Engineer** - Data pipeline and ETL development

### Web Development
- **Web UI** - Frontend and UI development
- **Web QA** - Web testing and E2E validation

### Project Management
- **Ticketing** - Issue tracking and management
- **Project Organizer** - File organization and structure
- **Memory Manager** - Project memory and context management

### Code Quality
- **Refactoring Engineer** - Code refactoring and optimization
- **Code Analyzer** - Static code analysis with AST and tree-sitter

## Agent Memory System

Agents learn project-specific patterns using a simple list format and can update memories via JSON response fields:

- `remember` - Incremental updates (add new learnings)
- `MEMORIES` - Complete replacement

Initialize with:
```bash
claude-mpm memory init
```

See [developer/memory-integration.md](../developer/memory-integration.md) for technical details.

## Skills System

Claude MPM includes 20 bundled skills that eliminate redundant agent guidance:

**Benefits:**
- 85% reduction in template size
- ~15,000 lines of reusable guidance
- Three-tier organization (bundled/user/project)
- Auto-linking to agents based on roles

**Quick Access:**
```bash
# Interactive skills management
claude-mpm configure
# Choose option 2: Skills Management
```

See [user/skills-guide.md](../user/skills-guide.md) for details.

## Agent Capabilities

Agents define capabilities that determine what tasks they can handle:

**Capability Types:**
- **Primary**: Core expertise (e.g., Python Engineer → Python development)
- **Secondary**: Supporting skills (e.g., Engineer → Testing)
- **Tools**: External integrations (e.g., Security → Security scanners)

The PM agent uses capabilities to intelligently route tasks to the most qualified specialist.

## Creating Custom Agents

Custom agents can be created at two levels:

**User Level** (`~/.claude-agents/`):
- Personal agents available across all projects
- Custom specializations
- Workflow preferences

**Project Level** (`.claude-mpm/agents/`):
- Project-specific agents
- Domain-specific needs
- Team workflows

**Agent Structure:**
```markdown
---
name: my-agent
version: 1.0.0
capabilities:
  - custom-capability
---

# My Agent

Agent prompt and instructions here...
```

See [agents/creating-agents.md](../agents/creating-agents.md) for complete guide.

## PM Workflow & Delegation

The PM agent orchestrates multi-agent workflows through intelligent delegation:

1. **Analyze Request**: Understand user's goals
2. **Select Specialists**: Match capabilities to tasks
3. **Delegate Work**: Route to appropriate agents
4. **Coordinate**: Manage handoffs between agents
5. **Integrate**: Combine results into cohesive output

See [agents/pm-workflow.md](../agents/pm-workflow.md) for detailed workflow patterns.

## Agent Patterns

Effective agent design follows these patterns:

**Specialization**: Focus on specific domain expertise
- ✅ Python Engineer for Python-specific development
- ❌ Generic coder that does everything

**Clear Capabilities**: Define precise skill boundaries
- ✅ "Python development, testing, type hints"
- ❌ "Everything software"

**Collaborative**: Work with other agents
- ✅ Engineer → QA handoff for testing
- ❌ Engineer tries to do all QA work

**Memory-Enabled**: Learn and improve over time
- ✅ Remember project patterns and decisions
- ❌ Treat every task as first encounter

See [agents/agent-patterns.md](../agents/agent-patterns.md) for comprehensive patterns.

## Advanced Topics

### Agent Versioning

Agents support semantic versioning (MAJOR.MINOR.PATCH):
```yaml
---
name: my-agent
version: 2.1.0
---
```

Check versions with `/mpm-version` command in Claude Code.

### Agent Schema

Agents follow a strict schema for frontmatter:
```yaml
---
name: string          # Required, unique identifier
version: string       # Required, semantic version
capabilities: array   # Required, list of capabilities
description: string   # Optional, brief description
---
```

See [developer/10-schemas/agent_schema_documentation.md](../developer/10-schemas/agent_schema_documentation.md) for complete schema.

### Hook Integration

Agents can integrate with the hook system:
- **pre_tool_use**: Before tool execution
- **post_tool_use**: After tool execution
- **session_start**: When session begins
- **session_end**: When session completes

See [developer/pretool-use-hooks.md](../developer/pretool-use-hooks.md) for details.

## See Also

- **[PM Workflow](../agents/pm-workflow.md)** - Orchestration patterns
- **[Creating Agents](../agents/creating-agents.md)** - Step-by-step development
- **[Agent Patterns](../agents/agent-patterns.md)** - Best practices
- **[Agent Capabilities Reference](../agents/agent-capabilities-reference.md)** - Complete agent catalog
- **[Skills Guide](../user/skills-guide.md)** - Skills system integration
- **[Developer Guide](../developer/README.md)** - Technical documentation
- **[API Reference](../developer/api-reference.md)** - API documentation

---

**Complete Agent Documentation**: [agents/README.md](../agents/README.md)
