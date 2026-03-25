---
name: mpm
description: Access Claude MPM functionality and manage multi-agent orchestration
user-invocable: true
version: "2.0.0"
category: mpm-command
tags: [mpm-command, system, pm-required, framework]
---

# /mpm - Claude MPM Framework Guide

## What is Claude MPM?

Claude MPM (Multi-Agent Project Manager) extends Claude Code with multi-agent orchestration, project-specific PM instructions, persistent agent memory, real-time monitoring via a WebSocket dashboard, and automation hooks. A **PM agent** coordinates specialized agents to complete work through structured delegation using the Task tool. MPM manages skills deployment, agent selection, session continuity, and cross-project messaging.

## How Delegation Works

The PM receives user requests and delegates to specialized agents via the **Task tool**:

```
Task(description="[what to do]", subagent_type="[agent-type]")
```

- PM analyzes the request, breaks it into subtasks, and selects the right agent for each
- Each agent focuses on its specialty and returns results to PM
- **Parallel execution** when tasks are independent (e.g., frontend + backend simultaneously)
- **Sequential execution** when tasks depend on each other (e.g., implement, then test, then deploy)
- Agents should focus on their delegated task and return clear results -- PM handles orchestration
- If an agent needs help from another specialty, it reports back to PM rather than self-delegating

**Typical workflow**: Research -> Engineer -> Ops (deploy) -> Ops (verify) -> QA -> Documentation

## Available Agents

### Core Agents (always deployed)

| Agent | subagent_type | Role |
|-------|---------------|------|
| Engineer | `engineer` | Code implementation, refactoring, debugging |
| Research | `Research` | Investigation, analysis, codebase exploration |
| QA | `qa` | Testing, validation, quality assurance |
| Documentation | `documentation` | Docs generation, API specs, guides |
| Ops | `ops` | Deployment, infrastructure, operations |
| Security | `security` | Vulnerability assessment, security review |
| Ticketing | `ticketing` | Ticket tracking and workflow management |

### Extended Agents (deployed per project)

| Agent | subagent_type | Role |
|-------|---------------|------|
| Version Control | `version-control` | Git operations, PR management, tagging |
| Code Analyzer | `code-analyzer` | Codebase analysis, architecture review |
| Code Review | `code-review` | PR review, semantic analysis |
| Data Engineer | `data-engineer` | Database management, API integrations |
| Product Owner | `product-owner` | Requirements, user stories, prioritization |

### Language-Specific Engineers

Deployed automatically based on project toolchain detection:

`python-engineer`, `typescript-engineer`, `javascript-engineer`, `golang-engineer`, `rust-engineer`, `java-engineer`, `ruby-engineer`, `php-engineer`, `dart-engineer`

**Framework specialists**: `nextjs-engineer`, `react-engineer`, `svelte-engineer`, `tauri-engineer`, `phoenix-engineer`

### Platform Ops

`local-ops` (local dev, PM2, Docker), `vercel-ops`, `gcp-ops`, `digitalocean-ops`, `clerk-ops`, `railway-ops`

### Specialized Agents

`api-qa`, `web-qa`, `code-review`, `code-analyzer`, `refactoring-engineer`, `prompt-engineer`, `content-agent`, `imagemagick`, `memory-manager`

## Skills System

**Skills** are markdown files deployed to `.claude/skills/{name}/SKILL.md` that provide agents with specialized knowledge and procedures.

- **User-invocable skills** respond to `/skill-name` slash commands (e.g., `/mpm`, `/mpm-help`)
- **Non-invocable skills** activate automatically based on context triggers
- Skills have **frontmatter** with: `name`, `description`, `user-invocable`, `version`, `category`, `tags`
- **Categories**: `mpm-command`, `pm-workflow`, `pm-reference`, `toolchains-*`, `universal-*`
- **Progressive disclosure**: Metadata loads first; full content loads on trigger
- Skills can include `references/` subdirectories for detailed supplementary content

## Memory System

Agent memories provide persistent context across sessions.

- **Storage**: `.claude-mpm/memories/{agent_id}_memories.md`
- PM manages memory files directly (read, consolidate, save)
- Each agent has domain-specific memory categories
- **Trigger phrases**: "remember", "don't forget", "always", "never", "going forward"
- **Size limit**: 80KB per file (~20k tokens)
- **Routing**: Keyword-based routing sends memories to the appropriate agent
- Memories are automatically loaded when an agent is delegated work

## Hooks and Dashboard

Claude Code hooks capture tool usage, responses, and agent activity in real-time.

**Event flow**: Hook -> Connection Manager -> Monitor Server -> Dashboard

**Dashboard** at `http://localhost:8765/` shows:
- Tools being used and files being read/written
- Agent delegations and completions
- Session timeline and activity feed

**Monitor commands**: `/mpm-monitor start`, `/mpm-monitor stop`, `/mpm-monitor status`

## Available Commands

| Command | Description |
|---------|-------------|
| `/mpm` | This guide -- MPM overview and framework reference |
| `/mpm-help` | Detailed help for MPM commands |
| `/mpm-init` | Initialize or update a project for MPM |
| `/mpm-status` | System health and status |
| `/mpm-doctor` | Run diagnostic checks |
| `/mpm-config` | Manage configuration |
| `/mpm-monitor` | Control monitoring server and dashboard |
| `/mpm-version` | Version information |
| `/mpm-message` | Cross-project messaging |
| `/mpm-organize` | Intelligent file consolidation |
| `/mpm-ticket-view` | Ticketing workflow management |
| `/mpm-session-pause` | Save session state for later |
| `/mpm-session-resume` | Resume from paused session |
| `/mpm-postmortem` | Analyze session errors |

## Cross-Project Messaging

`/mpm-message` sends asynchronous messages between Claude MPM instances running in different projects on the same machine.

- Messages stored in a shared SQLite database at `~/.claude-mpm/messaging.db`
- Checked periodically: on session start, every 10 commands, every 30 minutes
- Message types: `task`, `request`, `notification`, `reply`
- Always use the `MessageService` API or `claude-mpm message` CLI -- never query the database directly

## For Agents: How to Work Within MPM

When you receive a delegated task from PM:

1. **Focus on your delegated task** -- PM handles orchestration and coordination
2. **Return clear results with evidence**: file paths created/modified, test counts and pass rates, URLs, error details
3. **Your agent memory is loaded automatically** -- reference it for project-specific conventions and past decisions
4. **If you need another specialty**, report back to PM with what you need rather than self-delegating
5. **Track files you create or modify** -- PM will handle git operations and file tracking
6. **Follow project patterns** -- check your memory and existing code conventions before implementing
7. **Escalate blockers immediately** -- do not silently fail or produce partial results without explanation
