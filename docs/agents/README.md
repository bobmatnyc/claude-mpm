# Agent Documentation

Documentation for agent creators and the PM workflow.

## Documentation Files

- **[PM Workflow](pm-workflow.md)** - How the Project Manager agent orchestrates multi-agent workflows
- **[Research Agent](research-agent.md)** - Research agent with skill gap detection and recommendations (NEW)
- **[Agent Patterns](agent-patterns.md)** - Effective patterns for creating specialized agents
- **[Creating Agents](creating-agents.md)** - Step-by-step guide to agent development
- **[Agent Capabilities Reference](agent-capabilities-reference.md)** - Comprehensive catalog of all specialized agents

## Quick Links

**New to agents?**
1. Read [PM Workflow](pm-workflow.md) → Understand orchestration
2. Explore [Research Agent](research-agent.md) → Learn about skill recommendations (NEW)
3. Study [Agent Patterns](agent-patterns.md) → Learn best practices
4. Follow [Creating Agents](creating-agents.md) → Build your first agent
5. Browse [Agent Capabilities Reference](agent-capabilities-reference.md) → See all available agents

**Want to deploy skills?**
1. Read [Research Agent](research-agent.md) → Understand skill detection
2. Check [Skills Deployment Guide](../guides/skills-deployment-guide.md) → Deployment details
3. Use [Skills Quick Reference](../reference/skills-quick-reference.md) → Command reference

**Common Tasks:**
- Understand PM delegation: [PM Workflow - Delegation](pm-workflow.md#delegation-workflow)
- Learn agent structure: [Creating Agents - Structure](creating-agents.md#agent-structure)
- See effective patterns: [Agent Patterns - Design Patterns](agent-patterns.md#design-patterns)
- Create custom agent: [Creating Agents - Quick Start](creating-agents.md#quick-start)
- Find the right agent: [Agent Capabilities Reference - Operations](agent-capabilities-reference.md#operations-agents)

## Agent System Overview

Claude MPM uses a three-tier agent hierarchy with the PM agent orchestrating workflow:

```
User Request
     ↓
  PM Agent (orchestrator)
     ↓
  ├─→ Research Agent (analysis + skill recommendations)
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

**Skills Integration**: Research Agent detects skill gaps and recommends Claude Code skills

## Enhanced Research Agent (v2.6.0)

The Research Agent now includes **intelligent skill gap detection** and **proactive recommendations**:

**New Capabilities:**
- **Technology Stack Detection**: Automatically identifies languages, frameworks, and tools
- **Skill Gap Analysis**: Compares detected technologies to deployed Claude Code skills
- **Proactive Recommendations**: Suggests relevant skills during project analysis
- **Priority Ranking**: Categorizes skill recommendations (high/medium/low priority)
- **Deployment Integration**: Works with Skills Deployment system for easy installation

**When Research Agent Recommends Skills:**
1. **Project Initialization** - Analyzing new projects for the first time
2. **Technology Changes** - Detecting new dependencies or frameworks
3. **Work Type Detection** - Starting testing, debugging, or deployment work
4. **Quality Issues** - Code review findings suggest preventive skills

**Example Workflow:**
```
User: "Analyze this FastAPI project"
     ↓
Research Agent:
  ├─ Detects: Python 3.11, FastAPI, pytest, Docker
  ├─ Checks: Currently deployed skills
  ├─ Identifies: 3 skill gaps (TDD, backend-engineer, docker-workflow)
  └─ Recommends: claude-mpm skills deploy-github --toolchain python
```

**Related Documentation:**
- [Research Agent Documentation](research-agent.md) - Complete guide with skill detection
- [Skills Deployment Guide](../guides/skills-deployment-guide.md) - How to deploy skills
- [Skills Quick Reference](../reference/skills-quick-reference.md) - Command reference

## Resources

- **User Guide**: [../user/user-guide.md](../user/user-guide.md)
- **Developer Guide**: [../developer/README.md](../developer/README.md)
- **Extending**: [../developer/extending.md](../developer/extending.md)
