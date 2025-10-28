# PM Workflow

How the Project Manager agent orchestrates multi-agent workflows.

## Table of Contents

- [Overview](#overview)
- [Delegation Workflow](#delegation-workflow)
- [Task Routing](#task-routing)
- [Coordination Patterns](#coordination-patterns)
- [Best Practices](#best-practices)

## Overview

The PM (Project Manager) agent is the orchestrator in Claude MPM's multi-agent system. It analyzes user requests, breaks them into subtasks, and delegates to specialist agents.

**PM Responsibilities:**
- **Task Analysis**: Understand user intent and requirements
- **Planning**: Break complex tasks into manageable subtasks
- **Delegation**: Route subtasks to appropriate specialist agents
- **Coordination**: Manage dependencies between subtasks
- **Integration**: Combine results from multiple agents
- **Quality**: Ensure deliverables meet requirements

## Delegation Workflow

### 1. Request Analysis

PM receives user request and analyzes:
- **Intent**: What user wants to accomplish
- **Complexity**: Single-agent vs multi-agent task
- **Requirements**: Technical requirements and constraints
- **Dependencies**: Task dependencies and order

### 2. Task Planning

PM creates execution plan:
- **Decomposition**: Break into subtasks
- **Sequencing**: Determine execution order
- **Agent Selection**: Match subtasks to specialist capabilities
- **Context Preparation**: Prepare context for each agent

### 3. Delegation

PM delegates subtasks:

```
PM: "I need to implement authentication for the API."
    ↓
    Research Phase:
    PM → Research Agent: "Analyze current auth implementation"
    ↓
    Implementation Phase:
    PM → Engineer Agent: "Implement JWT-based authentication"
    ↓
    Testing Phase:
    PM → QA Agent: "Create test suite for authentication"
    ↓
    Documentation Phase:
    PM → Documentation Agent: "Update API docs with auth endpoints"
```

### 4. Coordination

PM manages execution:
- **Sequential Tasks**: Wait for dependencies
- **Parallel Tasks**: Execute independently
- **Error Handling**: Retry or reassign on failure
- **Progress Tracking**: Monitor completion

### 5. Integration

PM combines results:
- **Result Aggregation**: Collect outputs from all agents
- **Quality Check**: Verify deliverables
- **Consolidation**: Create unified response
- **Memory Update**: Store learnings

## Task Routing

PM routes tasks based on agent capabilities and specialization.

### Capability Matching

**Research Agent** (`research`):
- Codebase analysis
- Documentation review
- Architecture understanding
- Pattern identification

**Engineer Agent** (`engineer`):
- Feature implementation
- Code refactoring
- Bug fixes
- Technical design

**QA Agent** (`qa`):
- Test creation
- Quality validation
- Bug verification
- Test coverage analysis

**Documentation Agent** (`documentation`):
- API documentation
- User guides
- Code comments
- README updates

### Routing Logic

```python
# Simplified routing logic
def route_task(task: str) -> str:
    if "analyze" in task or "understand" in task:
        return "research"
    elif "implement" in task or "create" in task:
        return "engineer"
    elif "test" in task or "validate" in task:
        return "qa"
    elif "document" in task:
        return "documentation"
    else:
        return "pm"  # PM handles unclear tasks
```

### Multi-Agent Tasks

Complex tasks require multiple agents:

**Example: "Add feature X"**
1. Research Agent: Analyze codebase for integration points
2. Engineer Agent: Implement feature
3. QA Agent: Create tests
4. Documentation Agent: Update docs

**Example: "Fix bug Y"**
1. Research Agent: Reproduce and analyze bug
2. Engineer Agent: Implement fix
3. QA Agent: Verify fix and add regression test

## Coordination Patterns

### Sequential Execution

Tasks with dependencies execute sequentially:

```
Request: "Refactor module X and update tests"
    ↓
Research: Analyze current structure
    ↓
Engineer: Refactor module (depends on research)
    ↓
QA: Update tests (depends on refactoring)
```

### Parallel Execution

Independent tasks execute in parallel:

```
Request: "Document API endpoints and create examples"
    ↓
    ├─→ Documentation: API reference
    └─→ Engineer: Example implementations
```

### Iterative Execution

Tasks requiring multiple passes:

```
Request: "Optimize performance"
    ↓
Research: Identify bottlenecks
    ↓
Engineer: Implement optimization
    ↓
QA: Measure performance
    ↓
Research: Analyze new metrics (if needed)
    ↓
[Repeat until performance goal met]
```

### Error Recovery

Handling agent failures:

```
Task fails
    ↓
PM analyzes failure
    ↓
    ├─→ Retry with same agent (transient error)
    ├─→ Reassign to different agent (capability mismatch)
    └─→ Break into smaller subtasks (too complex)
```

## Best Practices

### For PM Agent

**Clear Delegation:**
- Provide specific, actionable instructions
- Include necessary context
- Specify success criteria
- Set realistic expectations

**Effective Coordination:**
- Identify dependencies early
- Parallelize when possible
- Monitor progress actively
- Adjust plan when needed

**Quality Focus:**
- Verify deliverables meet requirements
- Ensure consistency across agents
- Validate integrations work
- Request improvements if needed

### For Specialist Agents

**Accept Delegation:**
- Acknowledge task clearly
- Request clarification if needed
- Report progress to PM
- Return to PM when complete

**Stay Focused:**
- Work within assigned scope
- Don't expand scope without PM approval
- Delegate back to PM for out-of-scope work
- Complete assigned task before moving on

**Communicate:**
- Report blockers immediately
- Share important findings
- Update PM on progress
- Request help when stuck

### For Users

**Clear Requests:**
- Be specific about what you want
- Provide context
- Specify constraints
- Indicate priority

**Trust PM:**
- Let PM handle delegation
- Don't micromanage agent selection
- Allow PM to adjust plan
- Review final results, not intermediate steps

**Provide Feedback:**
- Clarify when PM misunderstands
- Adjust requirements if needed
- Validate final deliverables
- Store learnings for future tasks

---

**Next Steps:**
- Agent Patterns: See [agent-patterns.md](agent-patterns.md)
- Creating Agents: See [creating-agents.md](creating-agents.md)
- User Guide: See [../user/user-guide.md](../user/user-guide.md)
