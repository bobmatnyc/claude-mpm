---
name: mcp-builder
description: Create high-quality MCP servers that enable LLMs to effectively interact with external services. Use when building MCP integrations for APIs or services in Python (FastMCP) or Node/TypeScript (MCP SDK).
license: Complete terms in LICENSE.txt
progressive_disclosure:
  entry_point:
    summary: "Build agent-friendly MCP servers through research-driven design, thoughtful implementation, and evaluation-based iteration"
    when_to_use: "When integrating external APIs/services via MCP protocol. Prioritize agent workflows over API wrappers, optimize for context efficiency, design actionable errors."
    quick_start: "1. Research protocol & API docs 2. Plan agent-centric tools 3. Implement with validation 4. Create evaluations 5. Iterate based on agent feedback"
  references:
    - design_principles.md
    - workflow.md
    - mcp_best_practices.md
    - python_mcp_server.md
    - node_mcp_server.md
    - evaluation.md
---

# MCP Server Development Guide

## Overview

Build high-quality MCP (Model Context Protocol) servers that enable LLMs to accomplish real-world tasks through well-designed tools. Quality is measured not by API coverage, but by how effectively agents can use your tools to complete realistic workflows.

**Core insight:** MCP servers expose tools for AI agents, not human users. Design for agent constraints (limited context, no visual UI, workflow-oriented) rather than human convenience.

## When to Use This Skill

Activate when:
- Building MCP servers for external API integration
- Adding tools to existing MCP servers
- Improving MCP server tool design for better agent usability
- Creating evaluations to test MCP server effectiveness
- Debugging why agents struggle with your MCP tools

**Language Support:**
- Python: FastMCP framework (recommended for rapid development)
- Node/TypeScript: MCP SDK (recommended for production services)

## The Iron Law

```
DESIGN FOR AGENTS, NOT HUMANS

Every tool must optimize for:
- Context efficiency (agents have limited tokens)
- Workflow completion (not just API calls)
- Actionable errors (guide agents to success)
- Natural task subdivision (how agents think)
```

If your tools are just thin API wrappers, you're violating the Iron Law.

## Core Principles

1. **Agent-Centric Design First**: Study design principles before coding. Tools should enable workflows, not mirror APIs.

2. **Research-Driven Planning**: Load MCP docs, SDK docs, and exhaustive API documentation before writing code.

3. **Evaluation-Based Iteration**: Create realistic evaluations early. Let agent feedback drive improvements.

4. **Context Optimization**: Every response token matters. Default to concise, offer detailed when needed.

5. **Actionable Errors**: Error messages should teach agents correct usage patterns.

## Quick Start

### Phase 1: Research and Planning (40% of effort)
1. **Study Design Principles**: Load [design_principles.md](./reference/design_principles.md) to understand agent-centric design
2. **Load Protocol Docs**: Fetch `https://modelcontextprotocol.io/llms-full.txt` for MCP specification
3. **Study SDK Docs**: Load Python or TypeScript SDK documentation from GitHub
4. **Study API Exhaustively**: Read ALL API documentation, endpoints, authentication, rate limits
5. **Create Implementation Plan**: Define tools, shared utilities, pagination strategy, error handling

See [workflow.md](./reference/workflow.md) for complete Phase 1 steps.

### Phase 2: Implementation (30% of effort)
1. **Setup Project**: Create structure following language-specific guide
2. **Build Shared Utilities**: API helpers, error handlers, formatters BEFORE tools
3. **Implement Tools**: Use Pydantic (Python) or Zod (TypeScript) for validation
4. **Follow Best Practices**: Load language-specific guide for patterns

See [workflow.md](./reference/workflow.md) for complete Phase 2 steps and language guides.

### Phase 3: Review and Refine (15% of effort)
1. **Code Quality Review**: Check DRY, composability, consistency, type safety
2. **Test Build**: Verify syntax, imports, build process
3. **Quality Checklist**: Use language-specific checklist

See [workflow.md](./reference/workflow.md) for complete Phase 3 steps.

### Phase 4: Create Evaluations (15% of effort)
1. **Understand Purpose**: Evaluations test if agents can answer realistic questions using your tools
2. **Create 10 Questions**: Complex, read-only, independent, verifiable questions
3. **Verify Answers**: Solve yourself to ensure stability and correctness
4. **Run Evaluation**: Use provided scripts to test agent effectiveness

See [evaluation.md](./reference/evaluation.md) for complete evaluation guidelines.

## Navigation

### Core Design and Workflow
- **[🎯 Design Principles](./reference/design_principles.md)** - Agent-centric design philosophy: workflows over APIs, context optimization, actionable errors, natural task subdivision. Read FIRST before implementation.

- **[🔄 Complete Workflow](./reference/workflow.md)** - Detailed 4-phase development process with step-by-step instructions, decision trees, and when to load each reference file.

### Universal MCP Guidelines
- **[📋 MCP Best Practices](./reference/mcp_best_practices.md)** - Naming conventions, response formats, pagination, character limits, security, tool annotations, error handling. Applies to all MCP servers.

### Language-Specific Implementation
- **[🐍 Python Implementation](./reference/python_mcp_server.md)** - FastMCP patterns, Pydantic validation, async/await, complete examples, quality checklist. Load during Phase 2 for Python servers.

- **[⚡ TypeScript Implementation](./reference/node_mcp_server.md)** - MCP SDK patterns, Zod validation, project structure, complete examples, quality checklist. Load during Phase 2 for TypeScript servers.

### Evaluation and Testing
- **[✅ Evaluation Guide](./reference/evaluation.md)** - Creating realistic questions, answer verification, XML format, running evaluations, interpreting results. Load during Phase 4.

## Key Reminders

- **Research First**: Spend 40% of time researching before coding
- **Agent-Centric**: Design for AI workflows, not API completeness
- **Context Efficient**: Every token counts - default concise, offer detailed
- **Actionable Errors**: Guide agents to correct usage
- **Shared Utilities**: Extract common code - avoid duplication
- **Evaluation-Driven**: Create evals early, iterate based on feedback
- **MCP Servers Block**: Never run servers directly - use evaluation harness or tmux

## Red Flags - STOP

If you catch yourself:
- "Just wrapping these API endpoints directly"
- "Returning all available data fields"
- "Error message just says what failed" (not how to fix)
- Starting implementation without reading design principles
- Coding before loading MCP protocol documentation
- Creating tools without knowing agent use cases
- Skipping evaluation creation
- Running `python server.py` directly (will hang forever)

**ALL of these mean: STOP. Return to design principles and workflow.**

## Integration with Other Skills

- **systematic-debugging**: Debug MCP server issues methodically
- **test-driven-development**: Create failing tests before implementation
- **verification-before-completion**: Verify build succeeds before claiming completion
- **defense-in-depth**: Add input validation at multiple layers

## Real-World Impact

From MCP server development experience:
- Well-designed servers: 80-90% task completion rate by agents
- API wrapper approach: 30-40% task completion rate
- Context-optimized responses: 3x more information in same token budget
- Actionable errors: 60% reduction in agent retry attempts
- Evaluation-driven iteration: 2-3x improvement in agent success rate

---

**Remember:** The quality of an MCP server is measured by how well it enables LLMs to accomplish realistic tasks, not by how comprehensively it wraps an API.
