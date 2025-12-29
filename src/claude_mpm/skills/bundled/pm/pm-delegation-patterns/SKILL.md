---
name: pm-delegation-patterns
version: "1.0.0"
description: Common delegation patterns for PM agent
when_to_use: delegation questions, agent selection, workflow patterns
category: pm-reference
tags: [delegation, agents, patterns, pm-required]
---

# Common Delegation Patterns

## Full Stack Feature

**Workflow**: Research → Analyzer → react-engineer + Engineer → Ops (deploy) → Ops (VERIFY) → api-qa + web-qa → Docs

**When**: Complete feature requiring frontend, backend, and deployment

**Example**:
```
User: "Add user dashboard with analytics"
PM delegates:
  1. Research: Investigate dashboard frameworks and analytics libraries
  2. Code Analyzer: Review solution approach
  3. react-engineer: Build dashboard UI components
  4. Engineer: Implement analytics API endpoints
  5. Ops: Deploy to staging
  6. Ops: Verify deployment (health checks, logs)
  7. api-qa: Test API endpoints
  8. web-qa: Test dashboard UI
  9. Documentation: Update API docs and user guide
```

## API Development

**Workflow**: Research → Analyzer → Engineer → Deploy (if needed) → Ops (VERIFY) → web-qa (fetch tests) → Docs

**When**: Backend API implementation without frontend

**Example**:
```
User: "Create REST API for user management"
PM delegates:
  1. Research: API design patterns, authentication
  2. Code Analyzer: Review API design
  3. Engineer: Implement API endpoints
  4. Ops: Deploy API to staging (if needed)
  5. Ops: Verify deployment
  6. web-qa: Run fetch tests on endpoints
  7. Documentation: Generate API documentation
```

## Web UI

**Workflow**: Research → Analyzer → web-ui/react-engineer → Ops (deploy) → Ops (VERIFY with Playwright) → web-qa → Docs

**When**: Frontend-only changes

**Example**:
```
User: "Redesign landing page"
PM delegates:
  1. Research: UI/UX best practices, component libraries
  2. Code Analyzer: Review design approach
  3. react-engineer: Implement new landing page
  4. Ops: Deploy to staging
  5. Ops: Verify deployment with Playwright
  6. web-qa: Visual regression testing
  7. Documentation: Update component documentation
```

## Local Development

**Workflow**: Research → Analyzer → Engineer → **local-ops** (PM2/Docker) → **local-ops** (VERIFY logs+fetch) → QA → Docs

**When**: Working with localhost, PM2, Docker, or local processes

**Example**:
```
User: "Set up local development server"
PM delegates:
  1. Research: Local development setup best practices
  2. Code Analyzer: Review setup approach
  3. Engineer: Configure development environment
  4. local-ops: Start server with PM2/Docker
  5. local-ops: Verify server running (lsof, curl, logs)
  6. QA: Test local endpoints
  7. Documentation: Update setup guide
```

## Bug Fix

**Workflow**: Research → Analyzer → Engineer → Deploy → Ops (VERIFY) → web-qa (regression) → version-control

**When**: Fixing reported bugs

**Example**:
```
User: "Fix login error on Safari"
PM delegates:
  1. Research: Investigate Safari-specific issues
  2. Code Analyzer: Review fix approach
  3. Engineer: Implement fix
  4. Ops: Deploy fix to staging
  5. Ops: Verify deployment
  6. web-qa: Run regression tests, verify Safari fix
  7. version-control: Create PR with fix
```

## Vercel Site

**Workflow**: Research → Analyzer → Engineer → vercel-ops (deploy) → vercel-ops (VERIFY) → web-qa → Docs

**When**: Vercel-hosted applications

**Example**:
```
User: "Deploy blog to Vercel"
PM delegates:
  1. Research: Vercel deployment best practices
  2. Code Analyzer: Review deployment config
  3. Engineer: Configure Vercel settings
  4. vercel-ops: Deploy to Vercel
  5. vercel-ops: Verify deployment (health check)
  6. web-qa: Test deployed site
  7. Documentation: Update deployment guide
```

## Railway App

**Workflow**: Research → Analyzer → Engineer → railway-ops (deploy) → railway-ops (VERIFY) → api-qa → Docs

**When**: Railway-hosted applications

**Example**:
```
User: "Deploy API to Railway"
PM delegates:
  1. Research: Railway deployment patterns
  2. Code Analyzer: Review Railway config
  3. Engineer: Configure Railway settings
  4. railway-ops: Deploy to Railway
  5. railway-ops: Verify deployment
  6. api-qa: Test API endpoints
  7. Documentation: Update deployment docs
```

## Agent Selection by Trigger Keywords

| Keywords | Agent | Use Case |
|----------|-------|----------|
| localhost, PM2, docker-compose, port, process | **local-ops** | Local development |
| vercel, edge function, serverless | **vercel-ops** | Vercel platform |
| railway, nixpacks | **railway-ops** | Railway platform |
| gcp, google cloud, IAM, OAuth consent | **gcp-ops** | Google Cloud |
| clerk, auth middleware, OAuth provider | **clerk-ops** | Clerk authentication |
| browser, screenshot, click, navigate, DOM | **web-qa** | Browser testing |
| ticket, issue, PROJ-123, #123 | **ticketing** | Ticket operations |
| skill, stack, framework | **mpm-skills-manager** | Skill management |

## Delegation Best Practices

1. **Provide Context**: Include relevant background for agent
2. **Clear Acceptance Criteria**: Define completion criteria
3. **Wait for Completion**: Don't interrupt agent work
4. **Collect Evidence**: Get specific artifacts from agents
5. **Immediate File Tracking**: Track files right after agent creates them
6. **Chain Verification**: QA verification after implementation
