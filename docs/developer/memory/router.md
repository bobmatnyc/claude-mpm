# Memory Router Service

## Overview

The Memory Router service (`src/claude_mpm/services/memory/router.py`) intelligently routes memory commands to appropriate agents based on content analysis. It ensures that learnings and insights are stored with the most relevant agent for future retrieval.

## Purpose

**WHY**: When users say "remember this for next time", the system needs to determine which agent should store the information. Different types of knowledge belong to different specialists.

**DESIGN DECISION**: Uses keyword matching and context analysis rather than ML models for simplicity, transparency, and predictable routing decisions that users can understand.

## Key Responsibilities

1. **Content Analysis**: Analyze memory content to determine subject matter
2. **Agent Selection**: Choose the most appropriate agent for storage
3. **Confidence Scoring**: Provide confidence levels for routing decisions
4. **Reasoning**: Explain why content was routed to specific agents

## API Reference

### MemoryRouter Class

```python
from claude_mpm.services.memory.router import MemoryRouter

# Initialize router
router = MemoryRouter(config)

# Analyze and route content
result = router.analyze_and_route("Use dependency injection pattern in services")
# Returns: {
#     "target_agent": "engineer",
#     "section": "Design Patterns",
#     "confidence": 0.92,
#     "reasoning": "Content contains programming patterns and architecture concepts"
# }

# Get routing suggestions for content
suggestions = router.get_routing_suggestions("Security vulnerability in API")
# Returns multiple possible agents with confidence scores
```

### Key Methods

#### `analyze_and_route(content, context=None)`
Analyzes content and determines the best agent for storage.

**Parameters:**
- `content`: The memory content to route
- `context`: Optional context about the current task

**Returns:** Dictionary with target_agent, section, confidence, and reasoning

#### `get_routing_suggestions(content, top_k=3)`
Gets multiple routing suggestions ranked by confidence.

**Parameters:**
- `content`: The memory content to analyze
- `top_k`: Number of top suggestions to return

**Returns:** List of routing suggestions with confidence scores

#### `validate_routing(agent_id, content)`
Validates if content is appropriate for a specific agent.

**Parameters:**
- `agent_id`: Target agent identifier
- `content`: Content to validate

**Returns:** Boolean indicating if routing is valid

## Routing Patterns

### Agent Specializations

**Engineer Agent**:
- Keywords: implementation, code, function, class, api, refactor
- Topics: Programming, architecture, optimization, debugging

**QA Agent**:
- Keywords: test, quality, validation, coverage, regression
- Topics: Testing strategies, quality metrics, test automation

**Security Agent**:
- Keywords: vulnerability, encryption, authentication, threat
- Topics: Security policies, compliance, threat mitigation

**Documentation Agent**:
- Keywords: document, guide, readme, tutorial, specification
- Topics: Technical writing, API docs, user guides

**Research Agent**:
- Keywords: analysis, investigation, comparison, evaluation
- Topics: Technology research, benchmarking, feasibility studies

**PM Agent**:
- Keywords: project, milestone, deadline, coordination, stakeholder
- Topics: Project management, team coordination, planning

**Data Engineer Agent**:
- Keywords: pipeline, ETL, database, analytics, model
- Topics: Data processing, ML/AI integration, analytics

**Ops Agent**:
- Keywords: deployment, infrastructure, monitoring, scaling
- Topics: DevOps, CI/CD, system administration

## Routing Algorithm

1. **Keyword Matching**: Scan content for agent-specific keywords
2. **Context Analysis**: Consider current task and project context
3. **Confidence Calculation**: Score based on keyword density and relevance
4. **Section Mapping**: Determine appropriate memory section
5. **Reasoning Generation**: Explain the routing decision

## Example Usage

### Basic Routing

```python
# Route a testing-related memory
result = router.analyze_and_route(
    "Always mock external APIs in unit tests"
)
# Routes to QA agent with high confidence

# Route an architecture decision
result = router.analyze_and_route(
    "Use microservices architecture for scalability"
)
# Routes to Engineer agent, Architecture Patterns section
```

### Context-Aware Routing

```python
# Provide context for better routing
context = {
    "current_task": "security_audit",
    "agent_active": "security"
}

result = router.analyze_and_route(
    "Check all user inputs for SQL injection",
    context=context
)
# Routes to Security agent with context consideration
```

### Multi-Agent Routing

```python
# Get multiple routing options
suggestions = router.get_routing_suggestions(
    "Implement OAuth2 authentication with proper testing"
)
# Returns:
# 1. Engineer (0.85) - Implementation details
# 2. Security (0.78) - Authentication security
# 3. QA (0.65) - Testing requirements
```

## Routing Rules

### Priority Rules

1. **Explicit Agent Mentions**: If content mentions specific agent, route there
2. **Strong Keywords**: High-confidence keywords override weak signals
3. **Context Priority**: Current task context influences routing
4. **Default Fallback**: Route to PM agent when uncertain

### Conflict Resolution

When content matches multiple agents:
1. Calculate confidence scores for each
2. Consider current context
3. Choose highest confidence above threshold (0.6)
4. If tied, use agent priority order

## Configuration

```yaml
memory:
  routing:
    confidence_threshold: 0.6
    enable_multi_routing: false
    context_weight: 0.3
    keyword_weight: 0.7
```

## Best Practices

1. **Provide Context**: Include task context for accurate routing
2. **Clear Content**: Write clear, focused memory content
3. **Review Routing**: Check routing decisions for critical memories
4. **Update Patterns**: Extend routing patterns as needed
5. **Monitor Accuracy**: Track routing accuracy over time

## Error Handling

- **Ambiguous Content**: Returns low confidence with reasoning
- **No Match**: Defaults to PM agent with explanation
- **Invalid Agent**: Validates agent existence before routing
- **Empty Content**: Rejects empty or trivial content

## Testing

Unit tests:
- `tests/services/test_memory_router.py`

Integration tests:
- `tests/integration/test_memory_routing.py`

## Related Services

- [Memory Builder](builder.md) - Generates memory content
- [Memory Optimizer](optimizer.md) - Optimizes routed memories
- [Agent Memory Manager](../02-core-components/memory-system.md#agentmemorymanager) - Stores routed memories