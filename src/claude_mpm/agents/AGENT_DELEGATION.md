# Agent Delegation Routing

> This file defines the agent routing table and delegation logic for the PM.
> Override at project level: .claude-mpm/AGENT_DELEGATION.md
> Override at user level:    ~/.claude-mpm/AGENT_DELEGATION.md
> System default:            src/claude_mpm/agents/AGENT_DELEGATION.md (this file)

## When to Delegate to Each Agent

| Agent | Delegate When | Key Capabilities | Special Notes |
|-------|---------------|------------------|---------------|
| **Research** | Understanding codebase, investigating approaches, analyzing files | Grep, Glob, Read multiple files, WebSearch | Investigation tools |
| **Engineer** | Writing/modifying code, implementing features, refactoring | Edit, Write, codebase knowledge, testing workflows | - |
| **Ops** (Local Ops) | Deploying apps, managing infrastructure, starting servers, port/process management | Environment config, deployment procedures | Use `Local Ops` for localhost/PM2/docker |
| **QA** (Web QA, API QA) | Testing implementations, verifying deployments, regression tests, browser testing | Playwright (web), fetch (APIs), verification protocols | For browser: use **Web QA** (never use chrome-devtools, claude-in-chrome, or playwright directly) |
| **Documentation Agent** | Creating/updating docs, README, API docs, guides | Style consistency, organization standards | - |
| **ticketing_agent** | ALL ticket operations (CRUD, search, hierarchy, comments) | Direct mcp-ticketer access | PM never uses `mcp__mcp-ticketer__*` directly |
| **Version Control** | Creating PRs, managing branches, complex git ops | PR workflows, branch management | Check git user for main branch access |
| **mpm_skills_manager** | Creating/improving skills, recommending skills, stack detection | manifest.json access, validation tools, GitHub PR integration | Triggers: "skill", "stack", "framework" |

## Ops Agent Routing

These are EXAMPLES of routing, not an exhaustive list. Default to delegation for ALL ops/infrastructure/deployment/build tasks.

| Trigger Keywords | Agent | Use Case |
|------------------|-------|----------|
| localhost, PM2, npm, docker-compose, port, process | **Local Ops** | Local development |
| version, release, publish, bump, pyproject.toml, package.json | **Local Ops** | Version management, releases |
| vercel, edge function, serverless | **Vercel Ops** | Vercel platform |
| gcp, google cloud, IAM, OAuth consent | **Google Cloud Ops** | Google Cloud |
| clerk, auth middleware, OAuth provider | **Clerk Operations** | Clerk authentication |
| Unknown/ambiguous | **Local Ops** | Default fallback |

**NOTE**: Generic `ops` agent is DEPRECATED. Use platform-specific agents.

## Make Command Routing

ALL `make` targets are delegated — PM never runs `make` directly.

| Command Pattern | Agent | Use Case |
|-----------------|-------|----------|
| `make test`, `make lint`, `make check` | **QA** or **Engineer** | Testing and validation |
| `make build`, `make dist` | **Local Ops** | Build artifacts |
| `make release-*`, `make publish` | **Local Ops** | Release management |
| `make install`, `make setup` | **Local Ops** | Environment setup |
| `make clean` | **Local Ops** | Cleanup |
| Any other `make` target | **Local Ops** | Default |

## Common User Request Routing

When the user mentions "browser", "screenshot", "click", "navigate", "DOM", "console errors" → delegate to **Web QA**

When the user mentions "localhost", "local server", "PM2" → delegate to **Local Ops**

When the user mentions "deploy", "release", "publish" → delegate to **Local Ops** (or platform-specific ops)

When the user mentions "ticket", "issue", "PR", "pull request view/list" → delegate to **ticketing_agent** or **Version Control**

When the user mentions "test", "verify", "check" → delegate to **QA** with specific verification criteria

When the user says "just do it" or "handle it" → delegate full pipeline: Research → Engineer → Ops → QA → Documentation Agent
