# Agent Documentation

Documentation for agent creators and the PM workflow.

## Documentation Files

- **[PM Workflow](pm-workflow.md)** - How the Project Manager agent orchestrates multi-agent workflows
- **[Agent Patterns](agent-patterns.md)** - Effective patterns for creating specialized agents
- **[Creating Agents](creating-agents.md)** - Step-by-step guide to agent development

## Quick Links

**New to agents?**
1. Read [PM Workflow](pm-workflow.md) → Understand orchestration
2. Study [Agent Patterns](agent-patterns.md) → Learn best practices
3. Follow [Creating Agents](creating-agents.md) → Build your first agent

**Common Tasks:**
- Understand PM delegation: [PM Workflow - Delegation](pm-workflow.md#delegation-workflow)
- Learn agent structure: [Creating Agents - Structure](creating-agents.md#agent-structure)
- See effective patterns: [Agent Patterns - Design Patterns](agent-patterns.md#design-patterns)
- Create custom agent: [Creating Agents - Quick Start](creating-agents.md#quick-start)

## Agent System Overview

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

**Three-Tier System:**
- **PROJECT** (`.claude-mpm/agents/`): Highest priority, project-specific
- **USER** (`~/.claude-agents/`): Personal customizations
- **SYSTEM** (bundled): Default agents

## Key Concepts

**Agent Capabilities**: Define what an agent can do

**Specialization**: Agent's domain expertise

**Delegation**: PM routes tasks based on capabilities

**Memory**: Agents store learnings for continuity

**Frontmatter**: YAML metadata defining agent configuration

## Resources

- **User Guide**: [../user/user-guide.md](../user/user-guide.md)
- **Developer Guide**: [../developer/README.md](../developer/README.md)
- **Extending**: [../developer/extending.md](../developer/extending.md)
