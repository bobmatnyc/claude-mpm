# Agent to Skills Mapping

This document maps Claude MPM agents to their recommended skills from the `claude-mpm-skills` repository.

## Mapping Philosophy

Skills are assigned based on:
- **Core competencies**: Primary technologies the agent works with
- **Testing requirements**: All engineers get TDD and debugging skills
- **Workflow patterns**: Git, collaboration, and planning skills where relevant
- **Specialized domains**: Domain-specific skills (AI, security, infrastructure)

## Backend Engineers

### python-engineer
```
toolchains-python-frameworks-django
toolchains-python-frameworks-fastapi-local-dev
toolchains-python-frameworks-flask
toolchains-python-testing-pytest
toolchains-python-async-asyncio
toolchains-python-async-celery
toolchains-python-data-sqlalchemy
toolchains-python-validation-pydantic
toolchains-python-tooling-mypy
toolchains-python-tooling-pyright
universal-testing-test-driven-development
universal-debugging-systematic-debugging
universal-debugging-verification-before-completion
```

### typescript-engineer
```
toolchains-typescript-core
toolchains-typescript-frameworks-nodejs-backend
toolchains-typescript-frameworks-fastify
toolchains-typescript-data-prisma
toolchains-typescript-data-drizzle
toolchains-typescript-data-kysely
toolchains-typescript-validation-zod
toolchains-typescript-testing-vitest
toolchains-typescript-testing-jest
toolchains-typescript-api-trpc
universal-testing-test-driven-development
universal-debugging-systematic-debugging
universal-debugging-verification-before-completion
```

### javascript-engineer
```
toolchains-javascript-frameworks-express-local-dev
toolchains-javascript-build-vite
toolchains-javascript-testing-playwright
toolchains-javascript-testing-cypress
toolchains-javascript-tooling-biome
universal-testing-test-driven-development
universal-debugging-systematic-debugging
```

### golang-engineer
```
toolchains-golang-web
toolchains-golang-grpc
toolchains-golang-concurrency
toolchains-golang-data
toolchains-golang-cli
toolchains-golang-testing
toolchains-golang-observability
universal-testing-test-driven-development
universal-debugging-systematic-debugging
```

### rust-engineer
```
toolchains-rust-frameworks-axum
toolchains-rust-frameworks-tauri
toolchains-rust-desktop-applications
toolchains-rust-cli-clap
universal-testing-test-driven-development
universal-debugging-systematic-debugging
```

### php-engineer
```
toolchains-php-frameworks-wordpress-plugin-fundamentals
toolchains-php-frameworks-wordpress-block-editor
toolchains-php-frameworks-wordpress-advanced-architecture
toolchains-php-frameworks-wordpress-security-validation
toolchains-php-frameworks-wordpress-testing-qa
toolchains-php-frameworks-espocrm
universal-testing-test-driven-development
```

### phoenix-engineer
```
toolchains-elixir-frameworks-phoenix-liveview
toolchains-elixir-frameworks-phoenix-api-channels
toolchains-elixir-data-ecto-patterns
toolchains-elixir-ops-phoenix-ops
universal-testing-test-driven-development
```

### ruby-engineer
```
(No specific skills yet - add Rails, RSpec, etc. when available)
universal-testing-test-driven-development
universal-debugging-systematic-debugging
```

### java-engineer
```
(No specific skills yet - add Spring, JUnit, etc. when available)
universal-testing-test-driven-development
universal-debugging-systematic-debugging
```

## Frontend Engineers

### react-engineer
```
toolchains-javascript-frameworks-react
toolchains-javascript-frameworks-react-state-machine
toolchains-typescript-core
toolchains-typescript-validation-zod
toolchains-typescript-state-zustand
toolchains-typescript-state-tanstack-query
toolchains-ui-styling-tailwind
toolchains-ui-components-shadcn
toolchains-ui-components-headlessui
toolchains-javascript-testing-playwright
toolchains-typescript-testing-vitest
universal-testing-webapp-testing
universal-web-web-performance-optimization
```

### nextjs-engineer
```
toolchains-nextjs-core
toolchains-nextjs-v16
toolchains-javascript-frameworks-nextjs
toolchains-javascript-frameworks-react
toolchains-typescript-core
toolchains-typescript-validation-zod
toolchains-ui-styling-tailwind
toolchains-ui-components-shadcn
toolchains-platforms-deployment-vercel
toolchains-typescript-testing-vitest
universal-web-web-performance-optimization
universal-infrastructure-env-manager
```

### svelte-engineer
```
toolchains-javascript-frameworks-svelte
toolchains-javascript-frameworks-svelte5-runes-static
toolchains-javascript-frameworks-sveltekit
toolchains-typescript-core
toolchains-ui-styling-tailwind
toolchains-ui-components-daisyui
toolchains-javascript-build-vite
toolchains-typescript-testing-vitest
universal-web-web-performance-optimization
```

### web-ui
```
toolchains-ui-styling-tailwind
toolchains-ui-components-shadcn
toolchains-ui-components-headlessui
toolchains-ui-components-daisyui
toolchains-javascript-frameworks-react
toolchains-javascript-frameworks-vue
toolchains-javascript-frameworks-svelte
universal-web-web-performance-optimization
```

## Mobile & Desktop Engineers

### tauri-engineer
```
toolchains-rust-frameworks-tauri
toolchains-rust-desktop-applications
toolchains-javascript-frameworks-react
toolchains-javascript-frameworks-svelte
toolchains-javascript-frameworks-vue
toolchains-typescript-core
toolchains-ui-styling-tailwind
```

### dart-engineer
```
(No specific skills yet - add Flutter when available)
universal-testing-test-driven-development
universal-debugging-systematic-debugging
```

## QA Engineers

### qa
```
toolchains-javascript-testing-playwright
toolchains-javascript-testing-cypress
toolchains-python-testing-pytest
toolchains-typescript-testing-vitest
toolchains-typescript-testing-jest
toolchains-golang-testing
universal-testing-webapp-testing
universal-testing-test-driven-development
universal-testing-test-quality-inspector
universal-testing-testing-anti-patterns
universal-testing-condition-based-waiting
universal-debugging-verification-before-completion
```

### api-qa
```
toolchains-javascript-testing-playwright
toolchains-python-testing-pytest
toolchains-typescript-testing-vitest
universal-testing-test-driven-development
universal-testing-test-quality-inspector
universal-web-api-design-patterns
universal-debugging-verification-before-completion
```

### web-qa
```
toolchains-javascript-testing-playwright
toolchains-javascript-testing-cypress
universal-testing-webapp-testing
universal-testing-condition-based-waiting
universal-web-web-performance-optimization
universal-debugging-verification-before-completion
```

## Ops Engineers

### ops
```
toolchains-universal-infrastructure-docker
toolchains-universal-infrastructure-github-actions
universal-infrastructure-kubernetes
universal-infrastructure-terraform
universal-infrastructure-env-manager
universal-observability-opentelemetry
universal-debugging-systematic-debugging
universal-debugging-root-cause-tracing
```

### vercel-ops
```
toolchains-platforms-deployment-vercel
toolchains-nextjs-core
toolchains-universal-infrastructure-github-actions
universal-infrastructure-env-manager
```

### gcp-ops
```
toolchains-universal-infrastructure-docker
universal-infrastructure-kubernetes
universal-infrastructure-terraform
toolchains-universal-infrastructure-github-actions
```

### local-ops
```
toolchains-universal-infrastructure-docker
toolchains-python-frameworks-fastapi-local-dev
toolchains-javascript-frameworks-express-local-dev
universal-infrastructure-env-manager
```

### clerk-ops
```
(Clerk-specific skills not yet available)
toolchains-nextjs-core
universal-infrastructure-env-manager
```

## Data Engineers

### data-engineer
```
toolchains-python-data-sqlalchemy
toolchains-typescript-data-prisma
toolchains-typescript-data-drizzle
toolchains-typescript-data-kysely
toolchains-golang-data
toolchains-elixir-data-ecto-patterns
universal-data-database-migration
universal-data-json-data-handling
universal-data-xlsx
```

## Security & Analysis

### security
```
universal-security-security-scanning
universal-security-threat-modeling
toolchains-php-frameworks-wordpress-security-validation
universal-infrastructure-kubernetes
universal-debugging-root-cause-tracing
```

### code-analyzer
```
universal-architecture-software-patterns
universal-debugging-root-cause-tracing
universal-testing-test-quality-inspector
universal-testing-testing-anti-patterns
```

### research
```
universal-architecture-software-patterns
universal-debugging-root-cause-tracing
universal-debugging-systematic-debugging
universal-collaboration-brainstorming
```

## Specialized Engineers

### refactoring-engineer
```
universal-architecture-software-patterns
universal-testing-test-driven-development
universal-debugging-systematic-debugging
toolchains-typescript-core
toolchains-python-frameworks-django
toolchains-python-frameworks-fastapi-local-dev
```

### prompt-engineer
```
toolchains-ai-protocols-mcp
toolchains-ai-frameworks-langchain
toolchains-ai-frameworks-langgraph
toolchains-ai-frameworks-dspy
toolchains-ai-sdks-anthropic
toolchains-ai-services-openrouter
toolchains-ai-techniques-session-compression
universal-main-mcp-builder
```

### agentic-coder-optimizer
```
toolchains-ai-protocols-mcp
universal-main-skill-creator
universal-collaboration-dispatching-parallel-agents
```

### imagemagick
```
(No specific skills - specialized image processing agent)
```

## Universal Agents

### engineer (base)
```
universal-testing-test-driven-development
universal-debugging-systematic-debugging
universal-debugging-verification-before-completion
universal-collaboration-git-workflow
universal-architecture-software-patterns
```

### product-owner
```
universal-collaboration-writing-plans
universal-collaboration-brainstorming
universal-architecture-software-patterns
```

### project-organizer
```
universal-collaboration-writing-plans
universal-collaboration-git-workflow
universal-data-json-data-handling
```

### documentation
```
universal-web-api-documentation
universal-collaboration-writing-plans
universal-main-artifacts-builder
```

### ticketing
```
universal-collaboration-writing-plans
universal-collaboration-brainstorming
```

### content-agent
```
universal-main-artifacts-builder
universal-collaboration-writing-plans
universal-web-api-documentation
```

### memory-manager
```
universal-collaboration-writing-plans
universal-data-json-data-handling
```

### version-control
```
universal-collaboration-git-workflow
universal-collaboration-git-worktrees
universal-collaboration-stacked-prs
universal-collaboration-requesting-code-review
toolchains-universal-infrastructure-github-actions
```

## MPM-Specific Agents

### mpm-agent-manager
```
universal-main-skill-creator
universal-collaboration-dispatching-parallel-agents
universal-collaboration-writing-plans
```

### mpm-skills-manager
```
universal-main-skill-creator
```

## Skill Categories Summary

### Universal Skills (applicable to most agents)
- `universal-testing-test-driven-development` - Core TDD methodology
- `universal-debugging-systematic-debugging` - Systematic debugging approach
- `universal-debugging-verification-before-completion` - Verification protocols
- `universal-collaboration-git-workflow` - Git best practices
- `universal-architecture-software-patterns` - Design patterns and architecture

### Language-Specific Toolchains
- **Python**: django, fastapi, flask, pytest, sqlalchemy, pydantic, mypy
- **TypeScript**: core, nodejs-backend, fastify, prisma, drizzle, zod, vitest
- **JavaScript**: react, nextjs, express, vite, playwright, cypress
- **Go**: web, grpc, concurrency, data, cli, testing
- **Rust**: axum, tauri, desktop-applications, clap
- **PHP**: wordpress (multiple), espocrm
- **Elixir**: phoenix-liveview, phoenix-api-channels, ecto-patterns

### Testing & QA Skills
- `universal-testing-webapp-testing` - Web application E2E testing
- `universal-testing-test-quality-inspector` - Test quality validation
- `universal-testing-testing-anti-patterns` - Testing anti-pattern detection
- `universal-testing-condition-based-waiting` - Proper wait strategies
- Language-specific: playwright, cypress, pytest, vitest, jest

### Infrastructure & Ops Skills
- `universal-infrastructure-docker` - Docker containerization
- `universal-infrastructure-kubernetes` - K8s orchestration
- `universal-infrastructure-terraform` - IaC with Terraform
- `universal-infrastructure-env-manager` - Environment variable management
- `universal-observability-opentelemetry` - OpenTelemetry observability

### AI & Collaboration Skills
- `toolchains-ai-protocols-mcp` - Model Context Protocol
- `toolchains-ai-frameworks-langchain` - LangChain framework
- `toolchains-ai-frameworks-langgraph` - LangGraph for agents
- `universal-main-skill-creator` - Creating new skills
- `universal-collaboration-dispatching-parallel-agents` - Multi-agent orchestration

## Implementation Notes

1. **Skill Paths**: Skills are referenced by their path with dashes instead of slashes
   - Example: `toolchains/python/frameworks/django` → `toolchains-python-frameworks-django`

2. **Agent Templates**: Update agent `.md` files with `skills:` field containing array of skill IDs

3. **Minimal Viable Set**: Start with core skills for each agent, expand as needed

4. **Overlap is OK**: Multiple agents can share the same skills (e.g., all engineers get TDD)

5. **Missing Skills**: Some agents reference skills that don't exist yet (Ruby, Java, Flutter, etc.)
   - These are noted as "(No specific skills yet - add X when available)"
   - Still get universal skills like TDD and systematic debugging

## Usage in Agent Templates

Add to agent markdown frontmatter:

```yaml
skills:
  - toolchains-python-frameworks-django
  - toolchains-python-testing-pytest
  - universal-testing-test-driven-development
  - universal-debugging-systematic-debugging
```

Or in JSON format for agent configuration:

```json
{
  "skills": [
    "toolchains-python-frameworks-django",
    "toolchains-python-testing-pytest",
    "universal-testing-test-driven-development"
  ]
}
```
