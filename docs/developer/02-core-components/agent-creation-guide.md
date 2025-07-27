# Agent Creation Guide

## Overview

This guide walks you through creating custom agents for Claude MPM using the standardized schema format introduced in v2.0.0.

## Prerequisites

- Understanding of the [Agent Schema](../04-api-reference/agent-schema-api.md)
- Claude MPM v2.0.0 or later installed
- Basic understanding of JSON and agent concepts

## Agent Schema Structure

Every agent must conform to the standardized schema with these required sections:

```json
{
  "id": "unique_identifier",
  "version": "1.0.0",
  "metadata": { /* agent information */ },
  "capabilities": { /* technical configuration */ },
  "instructions": "Detailed agent instructions..."
}
```

## Step-by-Step Agent Creation

### Step 1: Define Agent Purpose

Before creating an agent, clearly define:
- What tasks will it handle?
- What tools does it need?
- What resource tier is appropriate?
- What makes it unique from existing agents?

### Step 2: Choose Resource Tier

Select the appropriate tier based on your agent's requirements:

| Tier | Use When | Timeout | Memory | CPU |
|------|----------|---------|---------|-----|
| **lightweight** | Simple, fast operations | 300s | 1024MB | 30% |
| **standard** | Normal complexity tasks | 600s | 2048MB | 50% |
| **intensive** | Complex analysis/implementation | 900s | 3072MB | 70% |

### Step 3: Create Agent Definition

Here's a complete example of a custom agent:

```json
{
  "id": "code_reviewer",
  "version": "1.0.0",
  "metadata": {
    "name": "Code Review Agent",
    "description": "Performs comprehensive code reviews focusing on quality, security, and best practices",
    "category": "quality",
    "tags": ["code-review", "quality", "security", "best-practices"],
    "author": "Your Name",
    "created_at": "2025-07-27T00:00:00Z",
    "updated_at": "2025-07-27T00:00:00Z"
  },
  "capabilities": {
    "model": "claude-4-sonnet-20250514",
    "tools": ["Read", "Grep", "Glob", "LS", "TodoWrite"],
    "resource_tier": "standard",
    "temperature": 0.1,
    "max_tokens": 8192,
    "timeout": 600,
    "memory_limit": 2048,
    "cpu_limit": 50,
    "network_access": false,
    "file_access": {
      "read_paths": ["/project"],
      "write_paths": []
    }
  },
  "instructions": "# Code Review Agent

You are a specialized agent for performing comprehensive code reviews. Your focus is on identifying potential issues, suggesting improvements, and ensuring code quality.

## Core Responsibilities

1. **Code Quality Analysis**
   - Review code structure and organization
   - Identify code smells and anti-patterns
   - Suggest refactoring opportunities
   - Check naming conventions and readability

2. **Security Review**
   - Identify potential security vulnerabilities
   - Check for proper input validation
   - Review authentication and authorization
   - Identify sensitive data exposure risks

3. **Performance Analysis**
   - Identify performance bottlenecks
   - Suggest optimization opportunities
   - Review algorithm complexity
   - Check for resource leaks

4. **Best Practices Compliance**
   - Verify adherence to language-specific best practices
   - Check error handling patterns
   - Review testing coverage
   - Validate documentation completeness

## Review Process

1. Start with a high-level overview of the changes
2. Analyze each file systematically
3. Group findings by severity (Critical, Major, Minor, Suggestion)
4. Provide specific, actionable feedback
5. Include code examples for improvements

## Output Format

Structure your reviews as:

```markdown
## Code Review Summary

**Files Reviewed**: X
**Critical Issues**: Y
**Major Issues**: Z
**Minor Issues**: W

### Critical Issues
[List critical security or functionality issues]

### Major Issues
[List significant quality or performance issues]

### Minor Issues
[List style or minor improvement suggestions]

### Positive Observations
[Highlight good practices found]
```

Always be constructive and educational in your feedback."
}
```

### Step 4: Validate Your Agent

Use the validation framework to ensure your agent is correctly defined:

```python
from claude_mpm.validation import AgentValidator
import json

# Load your agent definition
with open('code_reviewer.json', 'r') as f:
    agent = json.load(f)

# Validate
validator = AgentValidator()
result = validator.validate_agent(agent)

if result.valid:
    print("✓ Agent is valid!")
else:
    print("✗ Validation failed:")
    for error in result.errors:
        print(f"  ERROR: {error}")
    for warning in result.warnings:
        print(f"  WARNING: {warning}")
```

### Step 5: Test Your Agent

Create a test file to verify your agent works correctly:

```python
# test_code_reviewer.py
from claude_mpm.core import AgentLoader

# Load the agent
loader = AgentLoader()
agent = loader.get_agent("code_reviewer")

# Verify agent loaded correctly
print(f"Agent: {agent['metadata']['name']}")
print(f"Description: {agent['metadata']['description']}")
print(f"Tools: {', '.join(agent['capabilities']['tools'])}")

# Get the prompt
prompt = loader.get_prompt("code_reviewer")
print(f"\nPrompt length: {len(prompt)} characters")
```

### Step 6: Deploy Your Agent

1. Save your agent to the agents directory:
   ```bash
   cp code_reviewer.json src/claude_mpm/agents/
   ```

2. The agent will be automatically discovered by the AgentLoader

3. Use your agent:
   ```bash
   claude-mpm
   > @code_reviewer Please review the recent changes to the authentication module
   ```

## Best Practices

### 1. Clear, Focused Instructions

- Keep instructions specific to the agent's purpose
- Provide clear guidelines and examples
- Include output format specifications
- Stay within the 8000 character limit

### 2. Appropriate Tool Selection

Only include tools the agent actually needs:

```json
// Good: Minimal tools for read-only analysis
"tools": ["Read", "Grep", "Glob", "LS", "TodoWrite"]

// Bad: Including unnecessary write tools for analysis
"tools": ["Read", "Write", "Edit", "MultiEdit", "Bash", "Grep", "Glob", "LS", "WebSearch", "TodoWrite"]
```

### 3. Resource Allocation

Match resources to actual needs:

```json
// Good: Standard tier for code review
"resource_tier": "standard",
"timeout": 600,
"memory_limit": 2048

// Bad: Intensive tier for simple analysis
"resource_tier": "intensive",
"timeout": 900,
"memory_limit": 3072
```

### 4. Temperature Settings

Use appropriate temperature for the task:

- `0.0 - 0.1`: Deterministic tasks (code generation, analysis)
- `0.2 - 0.5`: Balanced tasks (documentation, reviews)
- `0.6 - 1.0`: Creative tasks (brainstorming, design)

### 5. Metadata Quality

Provide comprehensive metadata:

```json
"metadata": {
  "name": "Code Review Agent",  // Clear, descriptive name
  "description": "Performs comprehensive code reviews...",  // Specific description
  "category": "quality",  // Accurate category
  "tags": ["code-review", "quality", "security"],  // Relevant tags
  "author": "Your Name",  // Attribution
  "created_at": "2025-07-27T00:00:00Z",  // Timestamps
  "updated_at": "2025-07-27T00:00:00Z"
}
```

## Advanced Features

### Knowledge Base

Add domain-specific knowledge:

```json
"knowledge": {
  "domain_expertise": [
    "Python best practices and PEP standards",
    "Security vulnerabilities (OWASP Top 10)",
    "Performance optimization patterns"
  ],
  "best_practices": [
    "Always validate input at trust boundaries",
    "Use prepared statements for database queries",
    "Implement proper error handling without exposing internals"
  ],
  "constraints": [
    "Cannot modify code directly",
    "Must maintain constructive tone",
    "Should prioritize security issues"
  ]
}
```

### Interaction Patterns

Define how the agent interacts:

```json
"interactions": {
  "output_format": {
    "structure": "markdown",
    "includes": ["summary", "detailed-findings", "recommendations"]
  },
  "handoff_agents": ["engineer", "security", "qa"],
  "triggers": [
    {
      "condition": "critical security issue found",
      "action": "recommend security agent review"
    }
  ]
}
```

### Testing Configuration

Add test cases for validation:

```json
"testing": {
  "test_cases": [
    {
      "name": "Basic code review",
      "input": "Review this Python function for quality",
      "expected_behavior": "Provides structured review with categorized findings",
      "validation_criteria": [
        "Output includes severity categories",
        "Specific line references provided",
        "Actionable recommendations included"
      ]
    }
  ]
}
```

## Common Patterns

### Analysis Agents

For agents that analyze without modifying:

```json
{
  "capabilities": {
    "tools": ["Read", "Grep", "Glob", "LS", "TodoWrite"],
    "resource_tier": "standard",
    "temperature": 0.1,
    "network_access": false,
    "file_access": {
      "read_paths": ["/project"],
      "write_paths": []
    }
  }
}
```

### Implementation Agents

For agents that create or modify code:

```json
{
  "capabilities": {
    "tools": ["Read", "Write", "Edit", "MultiEdit", "Bash", "Grep", "Glob", "LS", "TodoWrite"],
    "resource_tier": "intensive",
    "temperature": 0.05,
    "network_access": true,
    "file_access": {
      "read_paths": ["/project"],
      "write_paths": ["/project"]
    }
  }
}
```

### Research Agents

For agents that gather information:

```json
{
  "capabilities": {
    "tools": ["Read", "Grep", "Glob", "LS", "WebSearch", "WebFetch", "TodoWrite"],
    "resource_tier": "intensive",
    "temperature": 0.2,
    "network_access": true,
    "file_access": {
      "read_paths": ["/project"],
      "write_paths": ["/project/research"]
    }
  }
}
```

## Troubleshooting

### Common Validation Errors

1. **Missing Required Fields**
   ```
   ERROR: 'metadata.category' is a required property
   ```
   Solution: Ensure all required fields are present

2. **Invalid Pattern**
   ```
   ERROR: 'MY_AGENT' does not match '^[a-z][a-z0-9_]*$'
   ```
   Solution: Use lowercase alphanumeric with underscores

3. **Character Limit Exceeded**
   ```
   ERROR: 'instructions' is too long (8500 chars), maximum 8000
   ```
   Solution: Condense instructions or move details to knowledge section

### Performance Issues

If your agent is slow:
1. Check if resource tier matches actual needs
2. Review tool selection (remove unnecessary tools)
3. Optimize instructions for clarity and focus
4. Consider breaking complex agents into specialized ones

## Next Steps

1. Review existing agents for examples
2. Start with a simple agent and iterate
3. Test thoroughly before deployment
4. Share your agents with the community
5. Contribute improvements back to the project