# Show recommended agents for detected project stack

Get intelligent agent recommendations based on your project's detected toolchain.

## Usage

```
/mpm-agents-recommend
```

## Description

This command analyzes your detected project stack and recommends the most appropriate agents, organized by priority:
- **Essential agents**: Core agents required for your primary stack
- **Recommended agents**: Complementary agents for full functionality
- **Optional agents**: Specialized agents for detected tools

Each recommendation includes an explanation of why that agent is suggested.

## Implementation

When you run `/mpm-agents-recommend`, the PM will execute:
```bash
claude-mpm agents recommend
```

This runs the detection phase and then applies recommendation rules to suggest the best agents for your specific technology stack.

## Expected Output

```
🤖 Agent Recommendations
=========================

Based on detected stack:
  Python 3.11, FastAPI 0.104.0, pytest, Docker, Vercel

Essential Agents (Must Have):
  ✓ fastapi-engineer
    Reason: FastAPI framework detected - specialized agent for FastAPI development
    Capabilities: FastAPI routes, Pydantic models, async endpoints, dependency injection

  ✓ python-engineer
    Reason: Python project - general Python development support
    Capabilities: Python code, testing, debugging, package management

  ✓ api-qa
    Reason: API testing for FastAPI backend
    Capabilities: API endpoint testing, validation, load testing, contract testing

Recommended Agents (Strongly Suggested):
  ○ docker-ops
    Reason: Docker configuration detected
    Capabilities: Docker builds, container management, docker-compose orchestration

  ○ vercel-ops
    Reason: Vercel deployment configuration found
    Capabilities: Vercel deployments, serverless functions, domain management

  ○ playwright-qa
    Reason: Comprehensive E2E testing capability
    Capabilities: Browser automation, visual testing, API testing

Optional Agents (Nice to Have):
  ○ local-ops-agent
    Reason: Local development and PM2 process management
    Capabilities: Local server management, port handling, PM2 operations

  ○ security-agent
    Reason: Security scanning and best practices
    Capabilities: Dependency scanning, code security, auth patterns

Summary:
  Recommended: 3 essential + 2 recommended = 5 agents
  Optional: 2 additional agents for enhanced capabilities

  Total recommended deployment: 5 agents
  Maximum useful deployment: 7 agents

Next Steps:
  1. Review recommendations above
  2. Run '/mpm-auto-configure --preview' to see deployment plan
  3. Run '/mpm-auto-configure' to deploy recommended agents
  4. Or deploy individually: '/mpm-agents deploy <agent-name>'
```

## Recommendation Logic

### Python Projects

**If FastAPI detected:**
- Essential: fastapi-engineer, python-engineer, api-qa
- Recommended: docker-ops (if Docker), vercel-ops (if Vercel)

**If Flask detected:**
- Essential: flask-engineer, python-engineer, api-qa
- Recommended: docker-ops (if Docker)

**If Django detected:**
- Essential: django-engineer, python-engineer, api-qa
- Recommended: docker-ops (if Docker)

**If pytest detected:**
- Add to recommended: api-qa, playwright-qa

### JavaScript/TypeScript Projects

**If Next.js detected:**
- Essential: nextjs-engineer, react-engineer, web-qa
- Recommended: playwright-qa, vercel-ops (if Vercel)

**If React detected (without Next.js):**
- Essential: react-engineer, web-qa
- Recommended: playwright-qa

**If Vue detected:**
- Essential: vue-engineer, web-qa
- Recommended: playwright-qa

**If Express detected:**
- Essential: node-engineer, api-qa
- Recommended: docker-ops (if Docker)

**If Nest.js detected:**
- Essential: nestjs-engineer, node-engineer, api-qa
- Recommended: docker-ops (if Docker)

### Full-Stack Projects

**Python backend + React frontend:**
- Essential: fastapi-engineer (or flask-engineer), python-engineer, react-engineer, api-qa, web-qa
- Recommended: playwright-qa, docker-ops, local-ops-agent

**Node.js backend + React frontend:**
- Essential: node-engineer, react-engineer, api-qa, web-qa
- Recommended: playwright-qa, docker-ops

### Testing-Focused Projects

**If Playwright detected:**
- Add to recommended: playwright-qa

**If Jest/Vitest detected:**
- Ensure web-qa or api-qa in recommended

### Deployment-Focused Projects

**If Vercel detected:**
- Add to recommended: vercel-ops

**If Railway detected:**
- Add to recommended: railway-ops

**If Docker detected:**
- Add to recommended: docker-ops

**If PM2 detected:**
- Add to recommended: local-ops-agent

## Agent Descriptions

### Backend Specialists
- **fastapi-engineer**: FastAPI expert - routes, Pydantic, async, websockets
- **flask-engineer**: Flask expert - blueprints, extensions, templates
- **django-engineer**: Django expert - models, views, ORM, admin
- **node-engineer**: Node.js expert - Express, async, streams
- **nestjs-engineer**: NestJS expert - modules, decorators, DI

### Frontend Specialists
- **nextjs-engineer**: Next.js expert - app router, server components, SSR
- **react-engineer**: React expert - hooks, state, components
- **vue-engineer**: Vue expert - composition API, components

### QA Specialists
- **api-qa**: API testing expert - REST, GraphQL, validation
- **web-qa**: Web testing expert - fetch, integration, E2E
- **playwright-qa**: Browser automation expert - UI testing, visual regression

### Ops Specialists
- **docker-ops**: Docker expert - builds, compose, containers
- **vercel-ops**: Vercel deployment expert - serverless, edge
- **railway-ops**: Railway deployment expert
- **local-ops-agent**: Local development expert - PM2, ports, processes

## Use Cases

1. **Planning**: Understand what agents you should deploy before starting work
2. **Validation**: Verify that auto-configuration will suggest the right agents
3. **Learning**: Discover what capabilities are available for your stack
4. **Optimization**: Find additional agents that could enhance your workflow

## Tips

1. **Start here**: Run this before `/mpm-auto-configure` to preview recommendations
2. **Essential vs Optional**: Focus on essential agents first, add others as needed
3. **Stack-specific**: Recommendations are tailored to YOUR detected stack
4. **Flexible**: You can always deploy additional agents later or skip some
5. **Explanations**: Pay attention to the "Reason" for each recommendation

## Customizing Recommendations

After seeing recommendations, you can:
1. **Accept all**: Run `/mpm-auto-configure` to deploy all recommended agents
2. **Pick and choose**: Deploy specific agents with `/mpm-agents deploy <name>`
3. **Skip optional**: Deploy only essential and recommended agents
4. **Add more**: Deploy additional agents not in recommendations

## Related Commands

- `/mpm-agents-detect` - See what was detected in your project
- `/mpm-auto-configure` - Automatically deploy recommended agents
- `/mpm-agents deploy <name>` - Deploy specific agents manually
- `/mpm-agents` - View all available and deployed agents
- `/mpm-help agents` - Learn more about agent management
