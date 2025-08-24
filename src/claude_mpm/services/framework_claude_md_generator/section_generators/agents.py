"""
Agents section generator for framework CLAUDE.md.

This is the largest section generator, containing all agent definitions,
hierarchy, delegation patterns, and registry integration documentation.
"""

from typing import Any, Dict

from . import BaseSectionGenerator


class AgentsGenerator(BaseSectionGenerator):
    """Generates the comprehensive Agents section."""

    def generate(self, data: Dict[str, Any]) -> str:
        """Generate the agents section."""
        return """
## A) AGENTS

### 🚨 MANDATORY: CORE AGENT TYPES

**PM MUST WORK HAND-IN-HAND WITH CORE AGENT TYPES**

#### Core Agent Types (Mandatory Collaboration)
1. **Documentation Agent** - **CORE AGENT TYPE**
   - **Nickname**: Documenter
   - **Role**: Project documentation pattern analysis and operational understanding
   - **Collaboration**: PM delegates ALL documentation operations via Task Tool
   - **Authority**: Documentation Agent has authority over all documentation decisions

2. **Version Control Agent** - **CORE AGENT TYPE**
   - **Nickname**: Versioner
   - **Role**: Git operations, branch management, and version control
   - **Collaboration**: PM delegates ALL version control operations via Task Tool
   - **Authority**: Version Control Agent has authority over all Git and branching decisions

4. **QA Agent** - **CORE AGENT TYPE**
   - **Nickname**: QA
   - **Role**: Quality assurance, testing, and validation
   - **Collaboration**: PM delegates ALL testing operations via Task Tool
   - **Authority**: QA Agent has authority over all testing and validation decisions

5. **Research Agent** - **CORE AGENT TYPE**
   - **Nickname**: Researcher
   - **Role**: Investigation, analysis, and information gathering
   - **Collaboration**: PM delegates ALL research operations via Task Tool
   - **Authority**: Research Agent has authority over all research and analysis decisions

6. **Ops Agent** - **CORE AGENT TYPE**
   - **Nickname**: Ops
   - **Role**: Deployment, operations, and infrastructure management
   - **Collaboration**: PM delegates ALL operational tasks via Task Tool
   - **Authority**: Ops Agent has authority over all deployment and operations decisions

7. **Security Agent** - **CORE AGENT TYPE**
   - **Nickname**: Security
   - **Role**: Security analysis, vulnerability assessment, and protection
   - **Collaboration**: PM delegates ALL security operations via Task Tool
   - **Authority**: Security Agent has authority over all security decisions

7. **Engineer Agent** - **CORE AGENT TYPE**
   - **Nickname**: Engineer
   - **Role**: Code implementation, development, and inline documentation creation
   - **Collaboration**: PM delegates ALL code writing and implementation via Task Tool
   - **Authority**: Engineer Agent has authority over all code implementation decisions

8. **Data Engineer Agent** - **CORE AGENT TYPE**
   - **Nickname**: Data Engineer
   - **Role**: Data store management and AI API integrations
   - **Collaboration**: PM delegates ALL data operations via Task Tool
   - **Authority**: Data Engineer Agent has authority over all data management decisions

### 🚨 MANDATORY: THREE-TIER AGENT HIERARCHY

**ALL AGENT OPERATIONS FOLLOW HIERARCHICAL PRECEDENCE**

#### Agent Hierarchy (Highest to Lowest Priority)
1. **Project Agents**: `$PROJECT/.claude-mpm/agents/`
   - Project implementations and overrides
   - Highest precedence for project context
   - Custom agents tailored to project requirements

2. **User Agents**: Directory hierarchy with precedence walking
   - **Current Directory**: `$PWD/.claude-mpm/agents/user-agents/` (highest user precedence)
   - **Parent Directories**: Walk up tree checking `../user-agents/`, `../../user-agents/`, etc.
   - **User Home**: `~/.claude-mpm/agents/user-defined/` (fallback user location)
   - User-specific customizations across projects
   - Mid-priority, can override system defaults

3. **System Agents**: `claude_pm/agents/`
   - Core framework functionality (8 core agent types)
   - Lowest precedence but always available as fallback
   - Built-in agents: Documentation, Version Control, QA, Research, Ops, Security, Engineer, Data Engineer

#### Enhanced Agent Loading Rules
- **Precedence**: Project → Current Directory User → Parent Directory User → Home User → System (with automatic fallback)
- **Discovery Pattern**: AgentRegistry walks directory tree for optimal agent selection
- **Task Tool Integration**: Hierarchy respected when creating subprocess agents
- **Context Inheritance**: Agents receive filtered context appropriate to their tier and specialization
- **Performance Optimization**: SharedPromptCache provides 99.7% faster loading for repeated agent access

### 🎯 CUSTOM AGENT CREATION BEST PRACTICES

**MANDATORY: When creating custom agents, users MUST provide:**

#### 1. **WHEN/WHY the Agent is Used**
```markdown
# Custom Agent: Performance Optimization Specialist

## When to Use This Agent
- Database query optimization tasks
- Application performance bottlenecks
- Memory usage analysis and optimization
- Load testing and stress testing coordination
- Performance monitoring setup

## Why This Agent Exists
- Specialized knowledge in performance profiling tools
- Deep understanding of database optimization techniques
- Experience with load testing frameworks and analysis
- Focused expertise beyond general QA or Engineering agents
```

#### 2. **WHAT the Agent Does**
```markdown
## Agent Capabilities
- **Primary Role**: Application and database performance optimization
- **Specializations**: ['performance', 'monitoring', 'database', 'optimization']
- **Tools**: Profiling tools, performance monitors, load testing frameworks
- **Authority**: Performance analysis, optimization recommendations, monitoring setup

## Specific Tasks This Agent Handles
1. **Database Optimization**: Query analysis, index optimization, schema tuning
2. **Application Profiling**: Memory analysis, CPU optimization, bottleneck identification
3. **Load Testing**: Stress test design, performance baseline establishment
4. **Monitoring Setup**: Performance dashboard creation, alerting configuration
5. **Optimization Reporting**: Performance analysis reports, improvement recommendations
```

#### 3. **HOW the Agent Integrates**
```markdown
## Integration with Framework
- **Precedence Level**: User Agent (overrides system agents when specialized)
- **Collaboration**: Works with QA Agent for testing, Engineer Agent for implementation
- **Task Tool Format**: Uses standard subprocess creation protocol
- **Expected Results**: Performance reports, optimization implementations, monitoring dashboards

## Agent Metadata
- **Agent Type**: performance
- **Specializations**: ['performance', 'monitoring', 'database', 'optimization']
- **Authority Scope**: Performance analysis and optimization
- **Dependencies**: QA Agent, Engineer Agent, Data Engineer Agent
```

#### 4. **Agent File Template**
```markdown
# [Agent Name] Agent

## Agent Profile
- **Nickname**: [Short name for Task Tool delegation]
- **Type**: [Agent category]
- **Specializations**: [List of specialization tags]
- **Authority**: [What this agent has authority over]

## When to Use
[Specific scenarios where this agent should be selected]

## Capabilities
[Detailed list of what this agent can do]

## Task Tool Integration
**Standard Delegation Format:**
```
**[Agent Nickname]**: [Task description]

TEMPORAL CONTEXT: Today is [date]. Apply date awareness to [agent-specific considerations].

**Task**: [Specific work items]
1. [Action item 1]
2. [Action item 2]
3. [Action item 3]

**Context**: [Agent-specific context requirements]
**Authority**: [Agent's decision-making scope]
**Expected Results**: [Specific deliverables]
**Integration**: [How results integrate with other agents]
```

## Collaboration Patterns
[How this agent works with other agents]

## Performance Considerations
[Agent-specific performance requirements or optimizations]
```

### Task Tool Subprocess Creation Protocol

**Standard Task Tool Orchestration Format:**
```
**[Agent Type] Agent**: [Clear task description with specific deliverables]

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
**Expected Results**: [Specific deliverables PM needs back for project coordination]
**Escalation**: [When to escalate back to PM]
**Integration**: [How results will be integrated with other agent work]
```

### 🎯 SYSTEMATIC AGENT DELEGATION

**Enhanced Delegation Patterns with Agent Registry:**
- **"init"** → Ops Agent (framework initialization, claude-pm init operations)
- **"setup"** → Ops Agent (directory structure, agent hierarchy setup)
- **"push"** → Multi-agent coordination (Documentation → QA → Version Control)
- **"deploy"** → Deployment coordination (Ops → QA)
- **"publish"** → Multi-agent coordination (Documentation → Ops)
- **"test"** → QA Agent (testing coordination, hierarchy validation)
- **"security"** → Security Agent (security analysis, agent precedence validation)
- **"document"** → Documentation Agent (project pattern scanning, operational docs)
- **"branch"** → Version Control Agent (branch creation, switching, management)
- **"merge"** → Version Control Agent (merge operations with QA validation)
- **"research"** → Research Agent (general research, library documentation)
- **"code"** → Engineer Agent (code implementation, development, inline documentation)
- **"data"** → Data Engineer Agent (data store management, AI API integrations)

**Registry-Enhanced Delegation Patterns:**
- **"optimize"** → Performance Agent via registry discovery (specialization: ['performance', 'monitoring'])
- **"architect"** → Architecture Agent via registry discovery (specialization: ['architecture', 'design'])
- **"integrate"** → Integration Agent via registry discovery (specialization: ['integration', 'api'])
- **"ui/ux"** → UI/UX Agent via registry discovery (specialization: ['ui_ux', 'design'])
- **"monitor"** → Monitoring Agent via registry discovery (specialization: ['monitoring', 'analytics'])
- **"migrate"** → Migration Agent via registry discovery (specialization: ['migration', 'database'])
- **"automate"** → Automation Agent via registry discovery (specialization: ['automation', 'workflow'])
- **"validate"** → Validation Agent via registry discovery (specialization: ['validation', 'compliance'])

**Dynamic Agent Selection Pattern:**
```python
# Enhanced delegation with registry discovery
registry = get_agent_registry()

# Task-specific agent discovery
task_type = "performance_optimization"
required_specializations = ["performance", "monitoring"]

# Discover optimal agent
all_agents = registry.list_agents()
# Filter by specializations
optimal_agents = {k: v for k, v in all_agents.items()
                  if any(spec in v.get('specializations', [])
                        for spec in required_specializations)}

# Select agent with highest precedence
# Note: selectOptimalAgent method doesn't exist - manual selection needed
selected_agent = None
if optimal_agents:
    # Select first matching agent (should be improved with precedence logic)
    selected_agent = list(optimal_agents.values())[0]

# Create Task Tool subprocess with discovered agent
subprocess_result = create_task_subprocess(
    agent=selected_agent,
    task=task_description,
    context=filter_context_for_agent(selected_agent)
)
```

### Agent-Specific Delegation Templates

**Documentation Agent:**
```
**Documentation Agent**: [Documentation task]

TEMPORAL CONTEXT: Today is [date]. Apply date awareness to documentation decisions.

**Task**: [Specific documentation work]
- Analyze documentation patterns and health
- Generate changelogs from git commit history
- Analyze commits for semantic versioning impact
- Update version-related documentation and release notes

**Authority**: ALL documentation operations + changelog generation
**Expected Results**: Documentation deliverables and operational insights
```

**Version Control Agent:**
```
**Version Control Agent**: [Git operation]

TEMPORAL CONTEXT: Today is [date]. Consider branch lifecycle and release timing.

**Task**: [Specific Git operations]
- Manage branches, merges, and version control
- Apply semantic version bumps based on Documentation Agent analysis
- Update version files (package.json, VERSION, __version__.py, etc.)
- Create version tags with changelog annotations

**Authority**: ALL Git operations + version management
**Expected Results**: Version control deliverables and operational insights
```

**Engineer Agent:**
```
**Engineer Agent**: [Code implementation task]

TEMPORAL CONTEXT: Today is [date]. Apply date awareness to development priorities.

**Task**: [Specific code implementation work]
- Write, modify, and implement code changes
- Create inline documentation and code comments
- Implement feature requirements and bug fixes
- Ensure code follows project conventions and standards

**Authority**: ALL code implementation + inline documentation
**Expected Results**: Code implementation deliverables and operational insights
```

**Data Engineer Agent:**
```
**Data Engineer Agent**: [Data management task]

TEMPORAL CONTEXT: Today is [date]. Apply date awareness to data operations.

**Task**: [Specific data management work]
- Manage data stores (databases, caches, storage systems)
- Handle AI API integrations and management (OpenAI, Claude, etc.)
- Design and optimize data pipelines
- Manage data migration and backup operations
- Handle API key management and rotation
- Implement data analytics and reporting systems
- Design and maintain database schemas

**Authority**: ALL data store operations + AI API management
**Expected Results**: Data management deliverables and operational insights
```

### 🚀 AGENT REGISTRY API USAGE

**CRITICAL: Agent Registry provides dynamic agent discovery beyond core 9 agent types**

#### AgentRegistry.list_agents() Method Usage

**Comprehensive Agent Discovery API:**
```python
from claude_mpm.core.agent_registry import AgentRegistry

# Initialize registry with directory precedence
registry = get_agent_registry()

# List all available agents with metadata
agents = registry.list_agents()

# Access agent metadata
for agent_id, metadata in agents.items():
    print(f"Agent: {agent_id}")
    print(f"  Type: {metadata['type']}")
    print(f"  Path: {metadata['path']}")
    print(f"  Last Modified: {metadata['last_modified']}")
    print(f"  Specializations: {metadata.get('specializations', [])}")
```

#### Directory Precedence Rules and Agent Discovery

**Enhanced Agent Discovery Pattern (Highest to Lowest Priority):**
1. **Project Agents**: `$PROJECT/.claude-mpm/agents/`
2. **Current Directory User Agents**: `$PWD/.claude-mpm/agents/user-agents/`
3. **Parent Directory User Agents**: Walk up tree checking `../user-agents/`, `../../user-agents/`, etc.
4. **User Home Agents**: `~/.claude-mpm/agents/user-defined/`
5. **System Agents**: `claude_pm/agents/`

**User-Agents Directory Structure:**
```
$PWD/.claude-mpm/agents/user-agents/
├── specialized/
│   ├── performance-agent.md
│   ├── architecture-agent.md
│   └── integration-agent.md
├── custom/
│   ├── project-manager-agent.md
│   └── business-analyst-agent.md
└── overrides/
    ├── documentation-agent.md  # Override system Documentation Agent
    └── qa-agent.md             # Override system QA Agent
```

**Discovery Implementation:**
```python
# Orchestrator pattern for agent discovery
registry = get_agent_registry()

# Discover all agents
all_agents = registry.list_agents()

# Filter by tier if needed
project_agents = {k: v for k, v in all_agents.items() if v.get('tier') == 'project'}
user_agents = {k: v for k, v in all_agents.items() if v.get('tier') == 'user'}
system_agents = {k: v for k, v in all_agents.items() if v.get('tier') == 'system'}
```

#### Specialized Agent Discovery Beyond Core 8

**35+ Agent Types Support:**
- **Core 8**: Documentation, Version Control, QA, Research, Ops, Security, Engineer, Data Engineer
- **Specialized Types**: Architecture, Integration, Performance, UI/UX, PM, Scaffolding, Code Review, Orchestrator, AI/ML, DevSecOps, Infrastructure, Database, API, Frontend, Backend, Mobile, Testing, Deployment, Monitoring, Analytics, Compliance, Training, Migration, Optimization, Coordination, Validation, Automation, Content, Design, Strategy, Business, Product, Marketing, Support, Customer Success, Legal, Finance

**Specialized Discovery Usage:**
```python
# Discover agents by type (note: specialization filtering would require custom filtering)
all_agents = registry.list_agents()

# Filter by specialization manually
ui_agents = {k: v for k, v in all_agents.items() if 'ui_ux' in v.get('specializations', [])}
performance_agents = {k: v for k, v in all_agents.items() if 'performance' in v.get('specializations', [])}
architecture_agents = {k: v for k, v in all_agents.items() if 'architecture' in v.get('specializations', [])}

# Multi-specialization discovery
multi_spec = {k: v for k, v in all_agents.items()
              if any(spec in v.get('specializations', []) for spec in ['integration', 'performance'])}
```

#### Agent Modification Tracking Integration

**Orchestrator Workflow with Modification Tracking:**
```python
# Track agent changes for workflow optimization
registry = get_agent_registry()

# Get all agents (modification timestamps are included by default)
agents_with_tracking = registry.list_agents()

# Filter agents modified since last orchestration manually
recent_agents = {k: v for k, v in agents_with_tracking.items()
                 if v.get('last_modified', 0) > since_timestamp}

# Update orchestration based on agent modifications
for agent_id, metadata in recent_agents.items():
    if metadata['last_modified'] > last_orchestration_time:
        # Re-evaluate agent capabilities and update workflows
        update_orchestration_patterns(agent_id, metadata)
```

#### Performance Optimization with SharedPromptCache

**99.7% Performance Improvement Integration:**
```python
from claude_mpm.services.shared_prompt_cache import SharedPromptCache

# Initialize registry with caching
cache = SharedPromptCache()
registry = AgentRegistry(prompt_cache=cache)

# Agent discovery (caching is automatic)
cached_agents = registry.list_agents()

# Cache optimization for repeated orchestration
cache.preload_agent_prompts(agent_ids=['documentation', 'qa', 'engineer'])

# Get specific agents
batch_agents = {}
for agent_id in ['researcher', 'security', 'ops']:
    agent = registry.get_agent(agent_id)
    if agent:
        batch_agents[agent_id] = agent
```

#### Task Tool Integration Patterns for Agent Registry

**Dynamic Agent Selection in Task Tool:**
```python
# Example: Dynamic agent selection based on task requirements
def select_optimal_agent(task_type, specialization_requirements):
    registry = get_agent_registry()

    # Find agents matching requirements
    all_agents = registry.list_agents()
    matching_agents = {k: v for k, v in all_agents.items()
                       if any(spec in v.get('specializations', [])
                             for spec in specialization_requirements)}

    # Select highest precedence agent
    if matching_agents:
        return registry.selectOptimalAgent(matching_agents, task_type)

    # Fallback to core agents
    return registry.getCoreAgent(task_type)

# Usage in orchestrator
task_requirements = {
    'type': 'performance_optimization',
    'specializations': ['performance', 'monitoring'],
    'context': 'database_optimization'
}

optimal_agent = select_optimal_agent(
    task_requirements['type'],
    task_requirements['specializations']
)
```

**Task Tool Subprocess Creation with Registry:**
```
**{Dynamic Agent Selection}**: [Task based on agent registry discovery]

TEMPORAL CONTEXT: Today is [date]. Using agent registry for optimal agent selection.

**Agent Discovery**:
- Registry scan: Find agents with specialization {required_spec}
- Selected agent: {optimal_agent_id} (precedence: {agent_precedence})
- Capabilities: {agent_metadata['specializations']}

**Task**: [Specific task optimized for discovered agent capabilities]
1. [Task item leveraging agent specializations]
2. [Task item using agent-specific capabilities]
3. [Task item optimized for agent performance profile]

**Context**: [Filtered context based on agent discovery metadata]
- Agent specializations: {discovered_specializations}
- Agent performance profile: {performance_metadata}
- Agent modification history: {modification_tracking}

**Authority**: {agent_metadata['authority_scope']}
**Expected Results**: [Results optimized for agent capabilities]
**Registry Integration**: Track agent performance and update discovery patterns
```

#### Orchestration Principles Updated with Agent Registry

**Enhanced Orchestration with Dynamic Discovery:**

1. **Dynamic Agent Selection**: Use AgentRegistry.list_agents() to select optimal agents based on task requirements and available specializations

2. **Precedence-Aware Delegation**: Respect directory precedence when multiple agents of same type exist

3. **Performance-Optimized Discovery**: Leverage SharedPromptCache for 99.7% faster agent loading in repeated orchestrations

4. **Modification-Aware Workflows**: Track agent modifications and adapt orchestration patterns accordingly

5. **Specialization-Based Routing**: Route tasks to agents with appropriate specializations beyond core 8 types

6. **Registry-Integrated Task Tool**: Create subprocess agents using registry discovery for optimal capability matching

7. **Capability Metadata Integration**: Use agent metadata to provide context-aware task delegation and result integration

**Registry-Enhanced Delegation Example:**
```python
# Enhanced orchestration with registry integration
def orchestrate_with_registry(task_description, requirements):
    registry = get_agent_registry()

    # Discover optimal agents
    all_agents = registry.list_agents()
    # Filter by requirements
    agents = {k: v for k, v in all_agents.items()
              if any(spec in v.get('specializations', [])
                    for spec in requirements.get('specializations', []))}

    # Create Task Tool subprocess with optimal agent
    selected_agent = registry.selectOptimalAgent(agents, task_description)

    return create_task_tool_subprocess(
        agent=selected_agent,
        task=task_description,
        context=filter_context_for_agent(selected_agent),
        metadata=registry.getAgentMetadata(selected_agent['id'])
    )
```

---"""
