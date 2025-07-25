# Agent System

The agent system in Claude MPM enables sophisticated multi-agent workflows where specialized AI agents collaborate to complete complex tasks. This document covers the architecture, implementation, and usage of the agent system.

## Overview

The agent system provides:
- **Specialized Agents**: Each agent has specific expertise (engineering, QA, documentation, etc.)
- **Dynamic Discovery**: Agents are discovered and loaded at runtime
- **Parallel Execution**: Multiple agents can work simultaneously
- **Result Synthesis**: Agent outputs are combined intelligently
- **Hierarchical Organization**: Project → User → System agent precedence

## Architecture

### Component Overview

```
┌──────────────────────────────────────────────────┐
│                Agent System                      │
├──────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐ │
│  │   Agent     │  │   Agent     │  │  Agent   │ │
│  │  Registry   │  │  Executor   │  │ Templates│ │
│  └──────┬──────┘  └──────┬──────┘  └─────┬────┘ │
│         │                 │                │      │
│         ▼                 ▼                ▼      │
│  ┌─────────────────────────────────────────────┐ │
│  │          Agent Coordination Layer           │ │
│  └─────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

### Core Components

#### 1. Agent Registry
**File**: `src/claude_mpm/core/agent_registry.py`

Manages agent discovery and registration:

```python
class AgentRegistry:
    """Central registry for all available agents"""
    
    def __init__(self):
        self.agents = {}
        self.discovery_paths = self._get_discovery_paths()
        self.discover_agents()
    
    def discover_agents(self):
        """Discover agents in hierarchical order"""
        # 1. System agents (lowest priority)
        self._discover_system_agents()
        
        # 2. User agents (medium priority)
        self._discover_user_agents()
        
        # 3. Project agents (highest priority)
        self._discover_project_agents()
    
    def register_agent(self, name: str, agent: Agent):
        """Register an agent, replacing if exists"""
        self.agents[name] = agent
        logger.info(f"Registered agent: {name}")
    
    def get_agent(self, name: str) -> Optional[Agent]:
        """Get agent by name"""
        return self.agents.get(name)
    
    def list_agents(self) -> List[Agent]:
        """List all available agents"""
        return list(self.agents.values())
```

#### 2. Agent Base Class
**File**: `src/claude_mpm/agents/base_agent.py`

All agents inherit from this base:

```python
class BaseAgent:
    """Base class for all agents"""
    
    def __init__(self, name: str, template_path: Path):
        self.name = name
        self.template_path = template_path
        self.specializations = []
        self.capabilities = []
        self.load_template()
    
    def load_template(self):
        """Load agent template from markdown file"""
        content = self.template_path.read_text()
        self.template = content
        self._parse_metadata()
    
    def _parse_metadata(self):
        """Extract metadata from template"""
        # Parse YAML frontmatter if present
        if self.template.startswith('---'):
            _, frontmatter, content = self.template.split('---', 2)
            metadata = yaml.safe_load(frontmatter)
            self.specializations = metadata.get('specializations', [])
            self.capabilities = metadata.get('capabilities', [])
    
    def create_prompt(self, task: str, context: dict) -> str:
        """Create agent prompt with task and context"""
        return self.template.format(
            task=task,
            context=json.dumps(context, indent=2)
        )
```

## Agent Types

### System Agents

Built-in agents that ship with Claude MPM:

#### 1. Engineer Agent
**File**: `src/claude_mpm/agents/templates/engineer_agent.md`

```markdown
---
specializations: [coding, architecture, implementation]
capabilities: [create, modify, refactor, optimize]
---

You are an Engineer Agent specialized in software development...

## Core Responsibilities
- Write clean, maintainable code
- Implement features according to specifications
- Follow project coding standards
- Create comprehensive tests

## Guidelines
- Always include error handling
- Document complex logic
- Consider performance implications
- Follow SOLID principles
```

#### 2. QA Agent
**File**: `src/claude_mpm/agents/templates/qa_agent.md`

```markdown
---
specializations: [testing, quality, validation]
capabilities: [test, validate, verify, review]
---

You are a QA Agent specialized in software testing...

## Core Responsibilities
- Write comprehensive test suites
- Perform code reviews
- Validate implementations
- Ensure quality standards

## Testing Approach
- Unit tests for all functions
- Integration tests for workflows
- Edge case coverage
- Performance testing
```

#### 3. Documentation Agent
**File**: `src/claude_mpm/agents/templates/documentation_agent.md`

```markdown
---
specializations: [documentation, technical-writing]
capabilities: [document, explain, diagram, tutorial]
---

You are a Documentation Agent specialized in technical writing...

## Core Responsibilities
- Create clear documentation
- Write API references
- Develop tutorials
- Maintain README files

## Documentation Standards
- Clear and concise language
- Code examples
- Visual diagrams where helpful
- Comprehensive coverage
```

#### 4. Research Agent
**File**: `src/claude_mpm/agents/templates/research_agent.md`

Enhanced with tree-sitter for code analysis:

```markdown
---
specializations: [analysis, research, investigation]
capabilities: [analyze, research, investigate, explore]
---

You are a Research Agent with advanced code analysis capabilities...

## Enhanced Capabilities
- AST-level code analysis via tree-sitter
- Cross-language pattern detection
- Dependency analysis
- Architecture exploration

## Research Tools
- Tree-sitter for 41+ languages
- Pattern matching across codebases
- Impact analysis
- Code metrics
```

### Custom Agents

Create project-specific agents:

```markdown
# .claude-pm/agents/project-specific/database_agent.md
---
specializations: [database, sql, optimization]
capabilities: [query, optimize, migrate, design]
---

You are a Database Agent for the e-commerce project...

## Project Context
- PostgreSQL 14 database
- High-volume transactions
- Real-time analytics requirements

## Responsibilities
- Design efficient schemas
- Optimize query performance
- Plan migrations
- Ensure data integrity
```

## Agent Discovery

### Discovery Hierarchy

Agents are discovered in a specific order, with later discoveries overriding earlier ones:

```python
def _get_discovery_paths(self) -> List[Path]:
    """Get agent discovery paths in precedence order"""
    paths = []
    
    # 1. System agents (lowest priority)
    system_path = Path(__file__).parent / 'agents' / 'templates'
    paths.append(system_path)
    
    # 2. User agents (walk up directory tree)
    current = Path.cwd()
    while current != current.parent:
        user_path = current / '.claude-pm' / 'agents' / 'user-agents'
        if user_path.exists():
            paths.append(user_path)
        current = current.parent
    
    # Home directory agents
    home_agents = Path.home() / '.claude-pm' / 'agents' / 'user-defined'
    if home_agents.exists():
        paths.append(home_agents)
    
    # 3. Project agents (highest priority)
    project_path = Path.cwd() / '.claude-pm' / 'agents' / 'project-specific'
    if project_path.exists():
        paths.append(project_path)
    
    return paths
```

### Dynamic Loading

Agents are loaded dynamically at runtime:

```python
def _load_agent_from_file(self, file_path: Path) -> Agent:
    """Load an agent from a markdown file"""
    try:
        # Extract agent name from filename
        name = file_path.stem.replace('_agent', '')
        
        # Create agent instance
        agent = Agent(
            name=name,
            template_path=file_path,
            priority=self._get_priority(file_path)
        )
        
        # Validate agent
        if self._validate_agent(agent):
            return agent
        
    except Exception as e:
        logger.error(f"Failed to load agent from {file_path}: {e}")
        return None
```

## Agent Execution

### Delegation Detection

The orchestrator detects delegation patterns:

```python
class DelegationDetector:
    """Detects agent delegations in Claude output"""
    
    PATTERNS = [
        # **Agent Name**: task
        re.compile(r'\*\*([^*]+)\*\*:\s*(.+)'),
        
        # Task(Agent: description)
        re.compile(r'Task\(([^:]+):\s*([^)]+)\)'),
        
        # Delegating to Agent: task
        re.compile(r'Delegating to ([^:]+):\s*(.+)')
    ]
    
    def detect_delegations(self, text: str) -> List[Delegation]:
        """Extract delegations from text"""
        delegations = []
        
        for pattern in self.PATTERNS:
            for match in pattern.finditer(text):
                agent_ref = match.group(1).strip()
                task = match.group(2).strip()
                
                # Normalize agent name
                agent_name = self._normalize_agent_name(agent_ref)
                
                delegations.append(Delegation(
                    agent=agent_name,
                    task=task,
                    context=self._extract_context(text, match)
                ))
        
        return delegations
```

### Parallel Execution

Agents execute in parallel using ThreadPoolExecutor:

```python
class AgentExecutor:
    """Executes agent tasks in parallel"""
    
    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.registry = AgentRegistry()
    
    def execute_delegations(self, delegations: List[Delegation]) -> List[Result]:
        """Execute multiple delegations in parallel"""
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            futures = []
            for delegation in delegations:
                future = executor.submit(
                    self._execute_single,
                    delegation
                )
                futures.append((delegation, future))
            
            # Collect results
            results = []
            for delegation, future in futures:
                try:
                    result = future.result(timeout=300)
                    results.append(result)
                except TimeoutError:
                    results.append(self._timeout_result(delegation))
                except Exception as e:
                    results.append(self._error_result(delegation, e))
            
            return results
    
    def _execute_single(self, delegation: Delegation) -> Result:
        """Execute a single agent delegation"""
        
        # Get agent
        agent = self.registry.get_agent(delegation.agent)
        if not agent:
            raise ValueError(f"Unknown agent: {delegation.agent}")
        
        # Create subprocess
        process = self._create_agent_process(agent)
        
        # Build prompt
        prompt = agent.create_prompt(
            task=delegation.task,
            context=delegation.context
        )
        
        # Execute
        stdout, stderr = process.communicate(
            input=prompt,
            timeout=300
        )
        
        # Parse result
        return self._parse_result(stdout, stderr, delegation)
```

### Result Formatting

Agent results are formatted to match Claude's Task tool output:

```python
def format_agent_result(agent: str, result: str, metadata: dict) -> str:
    """Format agent result for display"""
    
    # Format header
    header = f"{'=' * 50}\n"
    header += f"Agent: {agent}\n"
    header += f"Status: {metadata.get('status', 'completed')}\n"
    header += f"Execution Time: {metadata.get('execution_time', 0):.2f}s\n"
    header += f"{'=' * 50}\n"
    
    # Format content
    content = result
    
    # Format footer
    footer = f"\n{'=' * 50}\n"
    footer += f"Tokens Used: {metadata.get('tokens_used', 'N/A')}\n"
    footer += f"Cost: ${metadata.get('cost', 0):.4f}\n"
    footer += f"{'=' * 50}"
    
    return header + content + footer
```

## Agent Communication Protocol

### Task Message Format

Messages sent to agents follow a structured format:

```python
{
    "version": "1.0",
    "agent": "engineer",
    "task": {
        "description": "Create a REST API endpoint",
        "requirements": [
            "POST /api/users",
            "Validate input",
            "Store in database",
            "Return JSON response"
        ],
        "constraints": [
            "Use FastAPI",
            "Include tests",
            "Follow project standards"
        ]
    },
    "context": {
        "project_type": "web_api",
        "language": "python",
        "framework": "fastapi",
        "database": "postgresql",
        "existing_code": {
            "models": "...",
            "schemas": "..."
        }
    }
}
```

### Response Format

Agents return structured responses:

```python
{
    "version": "1.0",
    "agent": "engineer",
    "status": "success",
    "result": {
        "code": "...",
        "tests": "...",
        "documentation": "...",
        "notes": "..."
    },
    "metadata": {
        "execution_time": 2.5,
        "tokens_used": 1500,
        "model": "claude-3-opus",
        "confidence": 0.95
    }
}
```

## Advanced Features

### Agent Selection

Intelligent agent selection based on task:

```python
class AgentSelector:
    """Selects best agent for a given task"""
    
    def select_agent(self, task: str, context: dict) -> Agent:
        """Select most appropriate agent"""
        
        # Extract task features
        features = self._extract_features(task)
        
        # Score each agent
        scores = {}
        for agent in self.registry.list_agents():
            score = 0
            
            # Match specializations
            for spec in agent.specializations:
                if spec in features['keywords']:
                    score += 10
            
            # Match capabilities
            for cap in agent.capabilities:
                if cap in features['actions']:
                    score += 5
            
            # Context matching
            if self._matches_context(agent, context):
                score += 8
            
            scores[agent.name] = score
        
        # Return highest scoring agent
        best_agent = max(scores, key=scores.get)
        return self.registry.get_agent(best_agent)
```

### Cross-Agent Coordination

Agents can coordinate through shared context:

```python
class AgentCoordinator:
    """Coordinates multiple agents on complex tasks"""
    
    def coordinate_workflow(self, workflow: List[Step]) -> WorkflowResult:
        """Execute multi-step workflow with different agents"""
        
        shared_context = {}
        results = []
        
        for step in workflow:
            # Add previous results to context
            step.context.update(shared_context)
            
            # Execute step
            result = self.executor.execute_single(
                Delegation(
                    agent=step.agent,
                    task=step.task,
                    context=step.context
                )
            )
            
            results.append(result)
            
            # Update shared context
            shared_context[step.name] = result.data
            
            # Check dependencies
            if not self._check_dependencies(step, results):
                break
        
        return WorkflowResult(results, shared_context)
```

### Agent Monitoring

Track agent performance and health:

```python
class AgentMonitor:
    """Monitors agent performance metrics"""
    
    def __init__(self):
        self.metrics = defaultdict(lambda: {
            'executions': 0,
            'successes': 0,
            'failures': 0,
            'total_time': 0,
            'total_tokens': 0
        })
    
    def record_execution(self, agent: str, result: Result):
        """Record agent execution metrics"""
        
        metrics = self.metrics[agent]
        metrics['executions'] += 1
        
        if result.success:
            metrics['successes'] += 1
        else:
            metrics['failures'] += 1
        
        metrics['total_time'] += result.execution_time
        metrics['total_tokens'] += result.tokens_used
    
    def get_agent_stats(self, agent: str) -> dict:
        """Get statistics for an agent"""
        
        metrics = self.metrics[agent]
        if metrics['executions'] == 0:
            return {}
        
        return {
            'success_rate': metrics['successes'] / metrics['executions'],
            'average_time': metrics['total_time'] / metrics['executions'],
            'average_tokens': metrics['total_tokens'] / metrics['executions'],
            'total_executions': metrics['executions']
        }
```

## Testing Agents

### Unit Testing

Test individual agents:

```python
def test_engineer_agent():
    # Load agent
    agent = Agent(
        name='engineer',
        template_path=Path('templates/engineer_agent.md')
    )
    
    # Create test task
    task = "Create a function to calculate factorial"
    context = {
        'language': 'python',
        'requirements': ['recursive', 'iterative']
    }
    
    # Generate prompt
    prompt = agent.create_prompt(task, context)
    
    # Verify prompt contains expected elements
    assert 'factorial' in prompt
    assert 'python' in prompt
    assert agent.name in prompt
```

### Integration Testing

Test agent execution:

```python
def test_agent_execution():
    executor = AgentExecutor()
    
    delegation = Delegation(
        agent='engineer',
        task='Create hello world function',
        context={'language': 'python'}
    )
    
    result = executor.execute_single(delegation)
    
    assert result.success
    assert 'def hello_world' in result.output
    assert result.execution_time < 10
```

## Best Practices

### 1. Agent Template Design

```markdown
---
# Clear metadata
specializations: [specific, focused, skills]
capabilities: [what, agent, can, do]
---

# Clear role definition
You are a [Role] Agent specialized in [domain]...

## Core Responsibilities
- Specific, measurable responsibilities
- Clear scope boundaries
- Quality expectations

## Guidelines
- Step-by-step approach
- Error handling requirements
- Output format specifications

## Context Usage
When provided with context, prioritize:
1. Project-specific requirements
2. Existing code patterns
3. Team conventions
```

### 2. Task Delegation

```python
# Good: Specific, actionable task
"**Engineer Agent**: Create a RESTful API endpoint for user registration 
with email validation and password hashing"

# Bad: Vague task
"**Engineer Agent**: Make user stuff"
```

### 3. Context Management

```python
# Provide rich, filtered context
context = {
    'project_structure': get_relevant_structure(),
    'related_code': get_related_files(task),
    'dependencies': get_dependencies(),
    'conventions': get_coding_standards(),
    'constraints': get_project_constraints()
}
```

### 4. Error Handling

```python
try:
    result = executor.execute_delegation(delegation)
except AgentNotFoundError:
    # Fall back to general agent
    result = executor.execute_with_default(delegation)
except AgentTimeoutError:
    # Retry with extended timeout
    result = executor.execute_with_timeout(delegation, 600)
except Exception as e:
    # Log and continue
    logger.error(f"Agent execution failed: {e}")
    result = ErrorResult(str(e))
```

## Extending the Agent System

### Creating Custom Agents

1. Create agent template:
```bash
mkdir -p .claude-pm/agents/project-specific
vim .claude-pm/agents/project-specific/custom_agent.md
```

2. Define agent behavior:
```markdown
---
specializations: [your, specializations]
capabilities: [your, capabilities]
---

You are a Custom Agent...
```

3. Agent is automatically discovered and available

### Custom Agent Executors

```python
class CustomAgentExecutor(AgentExecutor):
    """Custom executor with special handling"""
    
    def _create_agent_process(self, agent: Agent) -> Process:
        """Create process with custom configuration"""
        
        if agent.name == 'high_memory':
            # Allocate more memory
            env = os.environ.copy()
            env['MEMORY_LIMIT'] = '4096'
            return super()._create_agent_process(agent, env=env)
        
        return super()._create_agent_process(agent)
```

## Next Steps

- See [Orchestrators](orchestrators.md) for delegation detection
- Review [Hook Service](hook-service.md) for agent hooks
- Check [API Reference](../04-api-reference/core-api.md#agent-system) for complete API