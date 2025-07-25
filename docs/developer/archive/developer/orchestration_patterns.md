# Claude MPM Orchestration Patterns

## Overview

Claude MPM (Multi-Agent Project Manager) implements sophisticated orchestration patterns to enable multi-agent workflows through subprocess delegation. The framework provides multiple orchestration strategies, each optimized for different use cases and interaction models.

## Table of Contents

1. [Core Orchestration Concepts](#core-orchestration-concepts)
2. [Orchestrator Types](#orchestrator-types)
3. [Agent Hierarchy and Discovery](#agent-hierarchy-and-discovery)
4. [Task Tool Protocol](#task-tool-protocol)
5. [Delegation Workflow](#delegation-workflow)
6. [Hook System Integration](#hook-system-integration)
7. [Common Orchestration Scenarios](#common-orchestration-scenarios)
8. [Best Practices](#best-practices)

## Core Orchestration Concepts

### Multi-Agent Architecture

The Claude MPM framework is built on a multi-agent architecture where:

- **PM (Project Manager)** acts as the central orchestrator
- **Specialized Agents** handle domain-specific tasks
- **Subprocess Delegation** enables parallel and autonomous execution
- **Task Tool Protocol** standardizes agent communication

### Orchestration Principles

1. **Never Perform Direct Work**: The PM orchestrator never performs technical tasks directly
2. **Always Use Task Tool**: All work is delegated via Task Tool subprocess creation
3. **Comprehensive Context Provision**: Rich, filtered context is provided to each agent
4. **Results Integration**: Agent results are actively analyzed and integrated
5. **Cross-Agent Coordination**: Workflows span multiple agents with proper sequencing

## Orchestrator Types

Claude MPM provides several orchestrator implementations, each with unique capabilities:

### 1. System Prompt Orchestrator

**File**: `src/claude_mpm/orchestration/system_prompt_orchestrator.py`

**Purpose**: Uses Claude's `--system-prompt` or `--append-system-prompt` flag to inject the framework as a system prompt.

**Key Features**:
- Framework instructions loaded as system prompt
- Simplest implementation with minimal overhead
- Suitable for interactive sessions
- Cannot intercept internal Task tool delegations

**Usage**:
```bash
claude-mpm --mode system-prompt
```

### 2. Subprocess Orchestrator

**File**: `src/claude_mpm/orchestration/subprocess_orchestrator.py`

**Purpose**: Creates real subprocesses for agent delegations, mimicking Claude's built-in Task tool behavior.

**Key Features**:
- Parallel subprocess execution with ThreadPoolExecutor
- Automatic delegation detection in PM responses
- Resource tracking (execution time, token count)
- Formatted results mimicking Claude's Task tool output

**Delegation Detection Patterns**:
```python
# Pattern 1: **Agent Name**: task
# Example: **Engineer Agent**: Create a function...

# Pattern 2: Task(description)
# Example: Task(Engineer role summary)
```

**Usage**:
```bash
claude-mpm --subprocess -i "Your prompt"
```

### 3. Interactive Subprocess Orchestrator

**File**: `src/claude_mpm/orchestration/interactive_subprocess_orchestrator.py`

**Purpose**: Advanced orchestrator using pexpect for interactive subprocess control with resource monitoring.

**Key Features**:
- Interactive subprocess control via pexpect
- Memory usage monitoring and limits
- Process lifecycle management
- Parallel execution with resource constraints
- Real-time process status tracking

**Resource Management**:
```python
# Memory monitoring thresholds
warning_threshold_mb = 512
critical_threshold_mb = 1024
hard_limit_mb = 2048

# Process automatically terminated if exceeding hard limit
```

### 4. Base Orchestrator (MPMOrchestrator)

**File**: `src/claude_mpm/orchestration/orchestrator.py`

**Purpose**: Core orchestrator that launches Claude as a child process with framework injection.

**Key Features**:
- Direct subprocess management
- I/O interception for ticket extraction
- Session logging and history
- Framework injection on first interaction

## Agent Hierarchy and Discovery

### Three-Tier Agent Hierarchy

The framework implements a sophisticated agent discovery system with precedence rules:

1. **Project Agents** (`$PROJECT/.claude-pm/agents/project-specific/`)
   - Highest precedence
   - Project-specific implementations
   - Custom agents tailored to project requirements

2. **User Agents** (Directory hierarchy with precedence walking)
   - Current Directory: `$PWD/.claude-pm/agents/user-agents/`
   - Parent Directories: Walk up tree checking parent directories
   - User Home: `~/.claude-pm/agents/user-defined/`
   - Mid-priority, can override system defaults

3. **System Agents** (`claude_pm/agents/`)
   - Core framework functionality
   - Lowest precedence but always available
   - Built-in agents: Documentation, Engineer, QA, Research, Ops, Security, Version Control, Data Engineer

### Agent Registry Integration

**File**: `src/claude_mpm/core/agent_registry.py`

The AgentRegistry provides dynamic agent discovery:

```python
from claude_mpm.core.agent_registry import AgentRegistryAdapter

# Initialize registry
registry = AgentRegistryAdapter()

# List all available agents
agents = registry.list_agents()

# Select agent for task
agent = registry.select_agent_for_task(
    task_description="Optimize database queries",
    required_specializations=["performance", "database"]
)

# Get agent hierarchy
hierarchy = registry.get_agent_hierarchy()
# Returns: {'project': [...], 'user': [...], 'system': [...]}
```

## Task Tool Protocol

### Standard Delegation Format

The Task Tool protocol standardizes how the PM delegates work to agents:

```markdown
**[Agent Nickname]**: [Clear task description with specific deliverables]

TEMPORAL CONTEXT: Today is [current date]. Apply date awareness to:
- [Date-specific considerations for this task]
- [Timeline constraints and urgency factors]
- [Sprint planning and deadline context]

**Task**: [Detailed task breakdown with specific requirements]
1. [Specific action item 1]
2. [Specific action item 2]
3. [Specific action item 3]

**Context**: [Comprehensive filtered context relevant to this agent type]
- Project background and objectives
- Related work from other agents
- Dependencies and integration points
- Quality standards and requirements

**Authority**: [Agent writing permissions and scope]
**Expected Results**: [Specific deliverables PM needs back]
**Escalation**: [When to escalate back to PM]
**Integration**: [How results will be integrated with other agent work]
```

### Agent Nicknames and Delegation Patterns

Standard agent nicknames for consistent delegation:

- **Documentation Agent** → `Documenter`
- **Engineer Agent** → `Engineer`
- **QA Agent** → `QA`
- **Research Agent** → `Researcher`
- **Ops Agent** → `Ops`
- **Security Agent** → `Security`
- **Version Control Agent** → `Versioner`
- **Data Engineer Agent** → `Data Engineer`

## Delegation Workflow

### 1. Delegation Detection

The orchestrator monitors PM responses for delegation patterns:

```python
def detect_delegations(self, response: str) -> List[Dict[str, str]]:
    delegations = []
    
    # Pattern 1: **Agent Name**: task
    pattern1 = r'\*\*([^*]+)(?:\s+Agent)?\*\*:\s*(.+?)(?=\n\n|\n\*\*|$)'
    
    # Pattern 2: Task Tool → Agent: task
    pattern2 = r'Task Tool\s*→\s*([^:]+):\s*(.+?)(?=\n\n|\nTask Tool|$)'
    
    # Extract and return delegations
```

### 2. Agent Prompt Creation

Each agent receives a focused prompt with their specific framework content:

```python
def create_agent_prompt(self, agent: str, task: str, context: Dict = None) -> str:
    # Get agent-specific framework content
    agent_content = self.framework_loader.get_agent_content(agent)
    
    # Build focused prompt with:
    # - Agent role definition
    # - Temporal context
    # - Specific task
    # - Additional context
    # - Response format requirements
```

### 3. Subprocess Execution

Subprocesses are executed with proper resource management:

```python
# Parallel execution with ThreadPoolExecutor
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
    futures = []
    for delegation in delegations:
        future = executor.submit(
            self.run_subprocess,
            delegation['agent'],
            delegation['task']
        )
        futures.append(future)
    
    # Collect results as they complete
    results = [future.result() for future in futures]
```

### 4. Result Aggregation

Results are formatted to mimic Claude's Task tool output:

```
⏺ Task(Create factorial function...)
  ⎿  Done (0 tool uses · 2.3k tokens · 4.5s)

⏺ Task(Write tests for factorial...)
  ⎿  Done (0 tool uses · 1.8k tokens · 3.2s)

## Agent Responses

### Engineer Agent
[Agent response content...]

### QA Agent
[Agent response content...]
```

## Hook System Integration

The orchestrator integrates with the hook system at multiple points:

### Hook Points

1. **Submit Hook**: Called when user submits initial prompt
2. **Pre-Delegation Hook**: Called before delegating to an agent
3. **Post-Delegation Hook**: Called after agent completes task
4. **Ticket Extraction Hook**: Called to extract tickets from responses

### Hook Client Integration

```python
from claude_mpm.hooks.hook_client import HookServiceClient

# Initialize hook client
hook_client = HookServiceClient(base_url=hook_info['url'])

# Pre-delegation hook
hook_results = hook_client.execute_pre_delegation_hook(
    agent=agent_name,
    context={"task": task_description}
)

# Check for task modifications
modified = hook_client.get_modified_data(hook_results)
if modified and 'task' in modified:
    task = modified['task']  # Use modified task
```

## Common Orchestration Scenarios

### 1. Simple Task Delegation

**User**: "Create a REST API for user management"

**PM Response**:
```markdown
I'll help you create a REST API for user management. Let me delegate this to the appropriate agents.

**Engineer**: Create a REST API for user management with the following endpoints:
- POST /users - Create a new user
- GET /users/:id - Get user by ID
- PUT /users/:id - Update user
- DELETE /users/:id - Delete user

Include proper error handling and validation.

**QA**: Write comprehensive tests for the user management REST API including:
- Unit tests for each endpoint
- Integration tests with a test database
- API documentation tests
```

### 2. Multi-Agent Coordination

**User**: "Deploy the application with proper documentation"

**PM Response**:
```markdown
I'll coordinate the deployment process with documentation updates.

**Documentation Agent**: Update deployment documentation including:
- System requirements
- Environment setup
- Configuration options
- Deployment steps

**QA**: Run full test suite and verify deployment readiness:
- All tests passing
- No security vulnerabilities
- Performance benchmarks met

**Ops**: Deploy application to production:
- Build production artifacts
- Update configuration
- Run deployment scripts
- Verify deployment success
```

### 3. Complex Workflow with Dependencies

**User**: "Analyze performance issues and optimize the database"

**PM Response**:
```markdown
I'll orchestrate a comprehensive performance analysis and optimization.

**Research Agent**: Investigate current performance bottlenecks:
- Analyze slow query logs
- Review application metrics
- Identify resource constraints

**Data Engineer**: Based on research findings, optimize database:
- Create missing indexes
- Optimize query execution plans
- Implement caching strategies
- Configure connection pooling

**QA**: Validate performance improvements:
- Run performance test suite
- Compare before/after metrics
- Ensure no functionality regression

**Documentation Agent**: Document optimization changes:
- Performance analysis findings
- Optimization steps taken
- New configuration parameters
- Monitoring recommendations
```

## Best Practices

### 1. Agent Selection

- Use the most specific agent for the task
- Leverage agent specializations for complex tasks
- Consider creating custom agents for project-specific needs

### 2. Context Management

- Provide comprehensive but filtered context
- Include temporal awareness for time-sensitive tasks
- Reference related agent work for continuity

### 3. Delegation Patterns

- Use clear, actionable task descriptions
- Specify expected deliverables explicitly
- Include escalation criteria

### 4. Resource Management

- Monitor subprocess memory usage
- Set appropriate timeouts for long-running tasks
- Use parallel execution for independent tasks

### 5. Error Handling

- Implement proper error detection in delegations
- Provide fallback strategies for failed tasks
- Log subprocess errors for debugging

### 6. Hook Integration

- Use pre-delegation hooks for task enrichment
- Implement post-delegation hooks for result processing
- Extract tickets consistently across all responses

## Advanced Patterns

### Dynamic Agent Discovery

```python
# Discover agents based on task requirements
def select_optimal_agent(task_type, specializations):
    registry = AgentRegistry()
    
    # Find agents matching requirements
    all_agents = registry.listAgents()
    matching_agents = filter_by_specializations(
        all_agents, 
        specializations
    )
    
    # Select highest precedence agent
    return select_by_precedence(matching_agents)
```

### Conditional Delegation

```python
# Delegate based on analysis results
if "performance" in task_description:
    delegate_to("Performance Agent", task)
elif "security" in task_description:
    delegate_to("Security Agent", task)
else:
    delegate_to("Engineer Agent", task)
```

### Chained Delegations

```python
# Execute delegations in sequence
research_result = await delegate_to("Research Agent", research_task)
implementation = await delegate_to(
    "Engineer Agent", 
    f"Implement based on: {research_result}"
)
validation = await delegate_to(
    "QA Agent",
    f"Validate implementation: {implementation}"
)
```

## Troubleshooting

### Common Issues

1. **Delegation Not Detected**
   - Check delegation format matches expected patterns
   - Ensure proper markdown formatting
   - Verify agent names are recognized

2. **Subprocess Timeout**
   - Increase timeout for complex tasks
   - Break down large tasks into smaller delegations
   - Check for infinite loops in agent logic

3. **Memory Limit Exceeded**
   - Adjust memory limits based on task requirements
   - Monitor agent memory usage patterns
   - Implement streaming for large data processing

4. **Hook Service Connection Failed**
   - Verify hook service is running
   - Check port availability
   - Review hook service logs

## Conclusion

The Claude MPM orchestration patterns provide a flexible and powerful framework for multi-agent collaboration. By understanding these patterns and following best practices, you can build sophisticated AI workflows that leverage the strengths of specialized agents while maintaining coordination and resource efficiency.

For more information, see:
- [Agent Development Guide](agent_development.md)
- [Hook System Documentation](hook_system.md)
- [API Reference](api_reference.md)