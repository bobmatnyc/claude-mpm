# Agent Templates Guide

## Overview

Agent templates are the foundation of Claude MPM's multi-agent architecture. They define specialized AI agents with specific domains of expertise, tools, and operational constraints. Each agent template provides a focused capability that can be orchestrated by the Project Manager (PM) agent to handle complex tasks.

## What Are Agent Templates?

Agent templates are JSON configuration files that define:

- **Agent Type**: The specialized role (e.g., engineer, research, qa)
- **Narrative Fields**: When to use the agent, specialized knowledge, and capabilities
- **Configuration Fields**: Technical settings like model, tools, temperature, and resource limits
- **Instructions**: Detailed operational guidelines for the agent

Each template follows a strict schema (`agent_schema.json`) ensuring consistency and proper integration with the framework.

## Available Agent Templates

### Core System Agents

1. **Research Agent** (`research_agent.json`)
   - **Purpose**: Codebase analysis using tree-sitter AST parsing
   - **Specializations**: Pattern discovery, architecture assessment, dependency mapping
   - **Key Tools**: Read, Grep, Glob, LS, WebSearch, Bash
   - **When to Use**: Pre-implementation analysis, technical investigation, best practices discovery

2. **Engineer Agent** (`engineer_agent.json`)
   - **Purpose**: Code implementation following research-identified patterns
   - **Specializations**: Implementation, refactoring, debugging, integration
   - **Key Tools**: Read, Write, Edit, MultiEdit, Bash, Grep
   - **When to Use**: Feature implementation, bug fixes, code refactoring

3. **QA Agent** (`qa_agent.json`)
   - **Purpose**: Testing strategies and quality validation
   - **Specializations**: Test automation, quality gates, validation
   - **Key Tools**: Read, Write, Edit, Bash, Grep
   - **When to Use**: Test creation, quality assurance, validation tasks

4. **Security Agent** (`security_agent.json`)
   - **Purpose**: Security review and vulnerability assessment
   - **Specializations**: Security audits, compliance, vulnerability detection
   - **Key Tools**: Read, Grep, WebSearch, specialized security tools
   - **When to Use**: Security-sensitive operations, compliance checks

5. **Documentation Agent** (`documentation_agent.json`)
   - **Purpose**: Technical documentation creation and maintenance
   - **Specializations**: API docs, user guides, technical writing
   - **Key Tools**: Read, Write, Edit, WebSearch
   - **When to Use**: Documentation tasks, API reference, guides

6. **Ops Agent** (`ops_agent.json`)
   - **Purpose**: Deployment, CI/CD, and infrastructure
   - **Specializations**: Deployment automation, monitoring, infrastructure
   - **Key Tools**: Bash, Read, Write, deployment tools
   - **When to Use**: Deployment tasks, CI/CD setup, infrastructure management

7. **Version Control Agent** (`version_control_agent.json`)
   - **Purpose**: Git operations and release management
   - **Specializations**: Branching strategies, merge conflicts, releases
   - **Key Tools**: Bash (git commands), Read, Write
   - **When to Use**: Version control operations, release preparation

8. **Data Engineer Agent** (`data_engineer_agent.json`)
   - **Purpose**: Database design and data pipeline development
   - **Specializations**: ETL pipelines, data modeling, analytics
   - **Key Tools**: Read, Write, Edit, Bash, database tools
   - **When to Use**: Database tasks, data transformations, analytics

## Agent Registry and Dynamic Discovery

The agent registry system provides dynamic discovery and management of agent templates:

### Core Components

1. **AgentRegistry** (`core/agent_registry.py`)
   - Discovers agents from multiple locations
   - Provides metadata about each agent
   - Supports filtering by type and tier

2. **Agent Hierarchy**
   - **System Agents**: Core framework agents (highest precedence)
   - **User Agents**: User-defined custom agents
   - **Project Agents**: Project-specific agent overrides

### Discovery Process

```python
from claude_mpm.core.agent_registry import AgentRegistry, create_agent_registry

# Create registry instance
registry = create_agent_registry()

# Discover all agents
agents = registry.discover_agents()

# List agents by type
qa_agents = registry.list_agents(agent_type="qa")

# Get specific agent
engineer = registry.get_agent("engineer")
```

### Agent Metadata

Each discovered agent includes:
- **name**: Agent identifier
- **type**: Agent type (engineer, qa, etc.)
- **path**: Location of template file
- **tier**: System/user/project hierarchy level
- **specializations**: List of specialized capabilities
- **description**: Brief description of agent purpose

## Creating Custom Agent Templates

### Template Structure

```json
{
  "version": 5,
  "agent_type": "custom_agent",
  "narrative_fields": {
    "when_to_use": [
      "Specific use case 1",
      "Specific use case 2"
    ],
    "specialized_knowledge": [
      "Domain expertise 1",
      "Technical knowledge area"
    ],
    "unique_capabilities": [
      "Capability 1",
      "Capability 2"
    ],
    "instructions": "# Custom Agent Instructions\n\nDetailed markdown instructions..."
  },
  "configuration_fields": {
    "model": "claude-4-sonnet-20250514",
    "description": "Brief agent description",
    "tags": ["custom", "specialized"],
    "tools": ["Read", "Write", "Edit"],
    "temperature": 0.1,
    "timeout": 600,
    "max_tokens": 8192,
    "primary_role": "Primary responsibility",
    "specializations": ["spec1", "spec2"],
    "authority": "Domain of authority"
  }
}
```

### Best Practices for Custom Agents

1. **Focus on Specialization**: Each agent should have a clear, focused purpose
2. **Define Clear Boundaries**: Specify when to use vs. when not to use
3. **Tool Selection**: Only include tools necessary for the agent's role
4. **Temperature Settings**: Lower for deterministic tasks, higher for creative work
5. **Resource Limits**: Set appropriate timeout, memory, and CPU limits

### Custom Agent Placement

Place custom agent templates in:
- **Project-specific**: `.claude-mpm/agents/` (highest priority)
- **User-wide**: `~/.claude-mpm/agents/`
- **System-wide**: `$CLAUDE_MPM_PATH/agents/templates/`

### Agent Template Generation

The framework includes a meta-template (`src/claude_mpm/agents/agent-template.yaml`) for generating new agent profiles. This YAML template provides the structure and schema for creating consistent agent templates across the system.

## Agent Selection and Delegation

### PM Agent's Selection Strategy

The Project Manager agent follows these rules for agent selection:

1. **Task Analysis**: Examines the task requirements and context
2. **Specialization Matching**: Matches task needs to agent specializations
3. **Research First**: For unknown codebases, delegates to Research agent first
4. **Security Priority**: Routes security-sensitive tasks to Security agent
5. **Workload Balancing**: Distributes tasks when multiple agents could handle them

### Delegation Format

The PM uses the Task tool with this format:

```python
Task(
    description="Analyze authentication patterns in the codebase",
    subagent_type="research-agent",  # Must match deployed agent YAML name
    context={
        "goal": "Understand current auth implementation",
        "scope": "auth module and middleware",
        "deliverables": ["pattern analysis", "recommendations"]
    }
)
```

### Agent Communication Protocol

Agents communicate through:
1. **TODO Format**: Agents report follow-up tasks as TODOs
2. **Structured Output**: Clear sections for completed work, findings, and next steps
3. **Context Preservation**: Important context passed between agents

## Agent Template Usage Examples

### Example 1: Research-First Implementation

```python
# PM delegates to Research agent first
Task(
    description="Research payment processing patterns",
    subagent_type="research-agent",
    context={
        "goal": "Understand payment flow for error handling implementation",
        "research_scope": {
            "codebase": "payment module",
            "patterns": "error handling, transactions",
            "external": "payment gateway best practices"
        }
    }
)

# Then delegates to Engineer with research results
Task(
    description="Implement error handling based on research",
    subagent_type="engineer",
    context={
        "research_findings": research_results,
        "patterns_to_follow": identified_patterns,
        "constraints": architectural_constraints
    }
)
```

### Example 2: Security-Sensitive Feature

```python
# Automatically routed to Security agent
Task(
    description="Review authentication endpoint implementation",
    subagent_type="security-agent",
    context={
        "code_location": "/api/auth/*",
        "concerns": ["SQL injection", "JWT validation", "rate limiting"],
        "compliance": ["OWASP guidelines"]
    }
)
```

### Example 3: Multi-Agent Workflow

```python
# 1. Research analyzes codebase
# 2. Engineer implements feature
# 3. QA creates tests
# 4. Documentation updates guides
# 5. Security reviews implementation
# 6. Ops prepares deployment
```

## Best Practices for Agent Development

### 1. Agent Design Principles

- **Single Responsibility**: Each agent should excel at one domain
- **Clear Interfaces**: Well-defined inputs and outputs
- **Tool Minimization**: Only tools essential for the role
- **Error Handling**: Comprehensive error reporting

### 2. Inter-Agent Communication

- **Structured TODOs**: Use consistent TODO format for task handoffs
- **Context Preservation**: Pass essential context between agents
- **Clear Deliverables**: Specify expected outputs explicitly

### 3. Performance Optimization

- **Resource Limits**: Set appropriate limits for agent type
- **Token Efficiency**: Optimize prompts for token usage
- **Caching**: Leverage SharedPromptCache for frequently used prompts

### 4. Testing Agent Templates

```python
# Test agent discovery
from claude_mpm.core.agent_registry import discover_agents

agents = discover_agents()
assert "engineer" in agents
assert "research" in agents

# Test agent selection
from claude_mpm.core.agent_registry import AgentRegistryAdapter

adapter = AgentRegistryAdapter()
agent = adapter.select_agent_for_task(
    "implement user authentication",
    required_specializations=["coding", "security"]
)
assert agent['metadata']['type'] == 'engineer'
```

### 5. Monitoring and Debugging

- **Agent Logs**: Each agent logs its operations
- **Task Tracking**: PM tracks all delegated tasks
- **Performance Metrics**: Monitor token usage, execution time

## Advanced Features

### Dynamic Agent Loading

Agents are loaded dynamically based on:
- Task requirements
- Available resources
- User preferences
- Project configuration

### Agent Versioning

- Template version field ensures compatibility
- Backward compatibility for older templates
- Migration paths for template updates

### Agent Composition

Complex tasks may require:
- Sequential agent execution
- Parallel agent operations
- Conditional agent selection
- Iterative refinement between agents

## Troubleshooting

### Common Issues

1. **Agent Not Found**
   - Check agent template location
   - Verify JSON syntax
   - Ensure proper file naming

2. **Tool Access Errors**
   - Verify tools listed in template
   - Check tool permissions
   - Ensure tool availability

3. **Performance Issues**
   - Review resource limits
   - Optimize token usage
   - Check for inefficient patterns

### Debug Commands

```bash
# List all discovered agents
claude-mpm debug agents list

# Validate agent template
claude-mpm debug agents validate custom_agent.json

# Test agent selection
claude-mpm debug agents select "implement feature"
```

## Future Enhancements

- **Learning Agents**: Agents that improve from experience
- **Collaborative Agents**: Direct agent-to-agent communication
- **Specialized Tool Integration**: Domain-specific tool support
- **Agent Marketplace**: Community-contributed agent templates