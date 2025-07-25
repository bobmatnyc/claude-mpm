# Agent Delegation System

Claude MPM's agent delegation system provides specialized expertise by automatically routing tasks to domain-specific agents.

## How Agent Delegation Works

### The Multi-Agent Architecture

```
                    You
                     ↓
              [Project Manager]
                /    |    \
               /     |     \
        Engineer    QA    Research
             \       |       /
              \      |      /
           Documentation Agent
                    |
              Security Agent
```

### Automatic Detection

Claude MPM detects when specialized agents are needed:

1. **Keyword Analysis** - Matches task keywords to agent specialties
2. **Context Understanding** - PM agent analyzes request context
3. **Explicit Requests** - Direct delegation commands
4. **Pattern Matching** - Recognizes delegation syntax

## Available Agents

### Project Manager (PM)
**Role**: Default coordinator and task router

**Triggers**: All requests start here

**Specializes in**:
- Task analysis and breakdown
- Agent delegation decisions
- Project planning
- Coordination

**Example**:
```
You: I need to build a web application

PM: I'll coordinate this project. Let me delegate specific 
    components to our specialized agents...
```

### Engineer Agent
**Role**: Code implementation and technical solutions

**Triggers**: "implement", "create", "build", "code", "develop"

**Specializes in**:
- Writing code
- System design
- Architecture decisions
- Technical implementation

**Example**:
```
You: Implement a REST API for user management

PM → Engineer: Create REST API with CRUD operations for users
```

### QA Agent
**Role**: Testing, quality assurance, and verification

**Triggers**: "test", "verify", "check", "validate", "QA"

**Specializes in**:
- Writing test cases
- Test implementation
- Bug detection
- Quality metrics

**Example**:
```
You: Write comprehensive tests for the authentication module

PM → QA: Create unit and integration tests for auth module
```

### Research Agent
**Role**: Information gathering and analysis

**Triggers**: "research", "investigate", "analyze", "compare", "study"

**Specializes in**:
- Best practices research
- Technology comparisons
- Market analysis
- Documentation review

**Example**:
```
You: Research the best database for real-time chat

PM → Research: Analyze databases suitable for real-time chat applications
```

### Documentation Agent
**Role**: Creating and maintaining documentation

**Triggers**: "document", "explain", "guide", "tutorial", "readme"

**Specializes in**:
- API documentation
- User guides
- Code documentation
- Technical writing

**Example**:
```
You: Document the API endpoints

PM → Documentation: Create comprehensive API documentation
```

### Security Agent
**Role**: Security analysis and recommendations

**Triggers**: "security", "vulnerability", "exploit", "protect", "secure"

**Specializes in**:
- Security audits
- Vulnerability detection
- Best practices
- Threat modeling

**Example**:
```
You: Audit the authentication system for vulnerabilities

PM → Security: Perform security audit on authentication system
```

## Delegation Patterns

### Automatic Delegation

Claude MPM recognizes these patterns:

```
**Agent Name**: Task description
→ Agent: Task
[Agent] Task
Delegate to Agent: Task
```

### Multi-Agent Coordination

Complex tasks trigger multiple agents:

```
You: Create a secure payment system with tests and documentation

PM identifies sub-tasks:
→ Engineer: Implement payment processing system
→ Security: Audit payment security  
→ QA: Write payment system tests
→ Documentation: Create payment API docs
```

## Subprocess Orchestration

### Parallel Execution

With subprocess mode, agents run simultaneously:

```bash
claude-mpm run --subprocess -i "Build complete user system"

Detected 4 delegations:
[Running in parallel...]
✓ Engineer: User model and API (3.2s)
✓ QA: Test suite (2.8s)
✓ Security: Security audit (2.5s)
✓ Documentation: API docs (2.1s)

Total: 3.2s (parallel) vs 10.6s (sequential)
```

### Sequential Execution

For dependent tasks:

```bash
claude-mpm run --subprocess --no-parallel -i "Create and test API"

Running sequentially:
1. Engineer: Create API → 2.5s
2. QA: Test the created API → 3.1s
Total: 5.6s
```

## Custom Agents

### Adding New Agents

Create agent templates in `.claude/agents/`:

```markdown
# data_analyst_agent.md

You are a specialized Data Analysis Agent.

## Expertise
- Statistical analysis
- Data visualization
- Machine learning
- Report generation

## Triggers
- "analyze data"
- "create visualization"
- "statistical analysis"
- "data insights"
```

### Agent Configuration

```python
# In configuration
CUSTOM_AGENTS = {
    "DataAnalyst": {
        "triggers": ["analyze", "visualization", "statistics"],
        "specialization": "data analysis and insights",
        "template": "data_analyst_agent.md"
    }
}
```

## Delegation Examples

### Example 1: Full Stack Development

```
You: Build a blog platform with user authentication

PM: I'll coordinate building a complete blog platform:

**Engineer**: Implement blog backend with user authentication
**Frontend Engineer**: Create React UI for blog
**QA**: Write comprehensive test suite
**Documentation**: Create user and developer documentation

[4 parallel subprocesses launched]
```

### Example 2: Bug Investigation

```
You: BUG: Users report slow page loads

PM: I'll coordinate investigating this performance issue:

**Engineer**: Profile code for performance bottlenecks
**QA**: Create performance benchmarks and tests
**Research**: Investigate best practices for optimization

[3 agents activated]
```

### Example 3: Security Audit

```
You: Perform a security audit of our API

PM: I'll organize a comprehensive security audit:

**Security**: Analyze API for vulnerabilities
**Engineer**: Review code for security issues
**Documentation**: Document security findings and fixes

[Agents work together on audit]
```

## Agent Communication

### Information Sharing

Agents can reference each other's work:

```
Engineer: I've implemented the user model at models/user.py

QA: I'll write tests for the user model that Engineer created...

Documentation: Based on Engineer's implementation and QA's tests,
              here's the API documentation...
```

### Coordination Patterns

```
Sequential: A → B → C
Parallel:   A, B, C (simultaneously)
Hierarchical: A → (B, C) → D
Circular:   A → B → C → A (iteration)
```

## Best Practices

### 1. Clear Task Descriptions

```
# Good: Specific task with context
"Create a REST API for user management with JWT authentication"

# Poor: Vague request
"Make API"
```

### 2. Leverage Specializations

```
# Let each agent do what they do best
"Research best practices" → Research Agent
"Implement the solution" → Engineer Agent
"Verify it works" → QA Agent
```

### 3. Use Explicit Delegation

```
# When you want specific agents
"Have the Security Agent review this code"
"Ask the Research Agent about NoSQL databases"
```

### 4. Combine Agents Effectively

```
# Complementary agents for complete solutions
"Design, implement, test, and document a caching system"
→ Activates Engineer, QA, and Documentation agents
```

## Monitoring Delegations

### In Logs

```bash
# View delegations in session logs
grep "Delegation:" ~/.claude-mpm/sessions/latest.log

# See agent responses
grep "Agent Response:" ~/.claude-mpm/sessions/latest.log
```

### Real-time Monitoring

With subprocess orchestration:
```
[INFO] Detected delegation to Engineer
[INFO] Launching subprocess for Engineer agent
[INFO] Engineer completed in 2.3s
```

## Troubleshooting

### Agent Not Triggered

**Check triggers**:
```
# Use explicit keywords
"test the function" → QA Agent
"verify the function" → QA Agent  
"check the function" → QA Agent
```

**Use explicit delegation**:
```
"QA Agent: Please test this function"
"Delegate to QA: Test this function"
```

### Wrong Agent Selected

**Be more specific**:
```
# Ambiguous
"Review this" → Could be any agent

# Specific
"Security review this" → Security Agent
"Code review this" → Engineer Agent
```

### Delegation Not Detected

**Check syntax**:
```
✓ **Engineer**: Task
✓ → Engineer: Task
✗ Engineer Task (missing delimiter)
```

## Advanced Usage

### Conditional Delegation

```
You: If the code has security issues, get the Security Agent to 
     review it, otherwise have QA write tests

PM: I'll first check for security concerns...
    [Conditionally activates appropriate agent]
```

### Iterative Delegation

```
You: Keep improving this code until it passes all tests

PM: I'll coordinate an iterative improvement process:
    1. Engineer: Implement initial version
    2. QA: Test and report issues
    3. Engineer: Fix issues
    4. Repeat until all tests pass
```

### Cross-Agent Collaboration

```
You: Create a secure API with the Engineer and Security agents 
     working together

PM: I'll have Engineer and Security collaborate:
    - Engineer implements with Security reviewing
    - Security suggests improvements
    - Engineer implements security recommendations
```

## Next Steps

- Explore [Session Logging](session-logging.md) to track delegations
- Learn about [Memory Protection](memory-protection.md) for long tasks
- See [Subprocess Orchestration](../02-guides/subprocess-orchestration.md) for parallel execution
- Check [Configuration](../04-reference/configuration.md) for custom agents