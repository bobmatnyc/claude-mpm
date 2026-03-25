---
description: "Multi-Agent Project Manager orchestration - delegation patterns, agent types, and verification protocol"
globs: "**/*"
alwaysApply: false
---

# MPM Orchestrator

Multi-Agent Project Manager orchestration skill for Claude Code.

## Delegation-First Principle

MPM operates on a delegation-first model: complex tasks should be broken into
subtasks and assigned to specialized agents rather than handled monolithically.

When a user request involves multiple domains (research + implementation + testing),
create a plan that delegates each domain to the appropriate agent type.

## Available Agent Types

| Agent | Specialization |
|-------|---------------|
| **engineer** | Code implementation, refactoring, architecture |
| **research** | Investigation, analysis, information gathering |
| **qa** | Testing, quality assurance, verification |
| **ops** | Deployment, infrastructure, CI/CD |
| **security** | Security audits, vulnerability assessment |
| **docs** | Documentation, technical writing |
| **data** | Data analysis, ETL, database operations |
| **design** | UI/UX design, prototyping |

## When to Delegate vs Handle Directly

**Delegate when:**
- Task spans multiple domains (research + code + test)
- Task requires deep specialized knowledge
- Task can be parallelized across agents
- Task benefits from independent verification

**Handle directly when:**
- Simple, single-domain task (quick code fix)
- Conversational / clarification exchange
- Task is a meta-operation (status check, configuration)

## Orchestration Protocol

1. **Analyze** the request and identify required domains
2. **Plan** the delegation (which agents, what order, dependencies)
3. **Delegate** subtasks to specialized agents
4. **Monitor** progress and handle failures
5. **Verify** results meet requirements before reporting completion

## Verification Protocol

Before marking any delegated task complete:
- Run relevant tests (unit, integration)
- Verify type safety (mypy, tsc)
- Check for regressions
- Confirm the output matches the original request

## Cross-Project Messaging

Use MPM messaging tools to coordinate across projects:
- `mpm-messaging` MCP server provides send/read/list/reply
- Messages persist in a shared SQLite database
- Use shortcuts for frequently-contacted projects

## Quick Commands

- `/mpm-status` -- Show system status, active agents, version
- `/mpm-help` -- List available commands and agent types
