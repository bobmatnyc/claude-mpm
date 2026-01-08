# MPM Prompt Examples Library

**Version**: 1.0.0
**Last Updated**: January 2026
**Audience**: All MPM users
**Related**: [Prompting Guide](prompting-guide.md), [Agent System Overview](../reference/agents-overview.md)

---

## Table of Contents

1. [Overview](#overview)
2. [Debugging Without Commits](#debugging-without-commits)
3. [TxDD Workflow Examples](#txdd-workflow-examples)
4. [Scaffold from Spec](#scaffold-from-spec)
5. [Codebase-wide Refactors with Guardrails](#codebase-wide-refactors-with-guardrails)
6. [Multi-Agent Coordination](#multi-agent-coordination)
7. [Investigation/Research Mode](#investigationresearch-mode)
8. [Quick Reference](#quick-reference)

---

## Overview

This library demonstrates MPM's unique multi-agent capabilities through concrete prompt examples. Each example includes:

- **The Prompt**: What to say to the PM agent
- **Why It Works**: The underlying MPM capabilities being leveraged
- **Agents Involved**: Which specialized agents handle the work
- **Variations**: Alternative ways to phrase the same request

**Key Principle**: MPM's PM agent coordinates specialized agents automatically. Your prompts should focus on *what* you want to achieve and *your constraints*, not *how* to do it.

---

## Debugging Without Commits

### Example 1: Exploratory Debugging

**Prompt**:
```
Debug why login fails for users with special characters in email addresses.
Do not commit any changes - this is investigation only.
Report what you find and suggest fixes.
```

**Why It Works**:
- `Do not commit` signals exploratory mode - PM won't commit findings
- Clear scope: specific bug to investigate
- Actionable output requested: findings + suggestions

**Agents Involved**:
1. **Research Agent** - Analyzes codebase for email handling
2. **Engineer Agent** - Reproduces issue and identifies root cause
3. **PM Agent** - Synthesizes findings into report

**Variations**:

```
Investigate the memory leak in the background worker.
Don't commit anything - just add instrumentation and report metrics.
```

```
Debug the race condition causing duplicate orders.
Investigation only - no commits.
Add logging to help identify the timing issue.
```

---

### Example 2: Branch-Based Investigation

**Prompt**:
```
Create a branch 'debug/payment-webhooks' and investigate why Stripe webhooks
are timing out. Add detailed logging but don't merge to main - I want to
review the findings first.
```

**Why It Works**:
- Explicit branch creation keeps exploration isolated
- PM understands not to merge (`don't merge to main`)
- Logging adds observability without changing behavior
- User maintains control with review step

**Agents Involved**:
1. **Version Control Agent** - Creates branch
2. **Research Agent** - Analyzes webhook flow
3. **Engineer Agent** - Adds logging
4. **PM Agent** - Commits to debug branch only

**Variations**:

```
On a new branch 'investigate/cache-misses', add performance instrumentation
to the Redis cache layer. Don't merge - I'll review the metrics first.
```

```
Create branch 'debug/auth-tokens' and add verbose logging to the JWT validation.
Keep this branch separate - we'll delete it after debugging.
```

---

### Example 3: Add Instrumentation for Debugging

**Prompt**:
```
The API response time has doubled in the last week.
Add timing instrumentation to all database queries and API endpoints.
Don't commit - I want to collect metrics first, then we'll remove the logging.
```

**Why It Works**:
- Clear problem statement (response time doubled)
- Specific instrumentation requested
- No commit prevents polluting git history with temporary debug code
- Sets expectation that instrumentation is temporary

**Agents Involved**:
1. **Research Agent** - Identifies all database queries and endpoints
2. **Engineer Agent** - Adds timing instrumentation
3. **PM Agent** - Holds changes uncommitted

**Variations**:

```
Add debug logging to the email sending flow - I need to see why some emails
aren't being delivered. Don't commit this yet.
```

```
The background jobs are failing sporadically. Add detailed logging to the job
queue processing. Keep this uncommitted so we can remove it after debugging.
```

---

## TxDD Workflow Examples

### Example 1: Test-First Feature Development

**Prompt**:
```
Implement user authentication with email/password.

Requirements:
- Users can register with email/password
- Passwords must be 8+ characters with at least 1 number
- Passwords are hashed before storage (bcrypt)
- Users can login and logout
- Session tokens expire after 24 hours

Write tests first that verify all requirements, then implement to make tests pass.
```

**Why It Works**:
- Clear requirements serve as specification
- `Write tests first` triggers TxDD workflow
- Specific validation rules become test cases
- PM coordinates Engineer → QA workflow

**Agents Involved**:
1. **QA Agent** - Writes comprehensive test suite based on requirements
2. **Engineer Agent** - Implements to pass tests
3. **Security Agent** - Reviews password hashing implementation
4. **PM Agent** - Verifies all requirements are tested and met

**Variations**:

```
Add rate limiting to API endpoints.

Requirements:
- Max 100 requests per minute per IP address
- Return 429 status when limit exceeded
- Include Retry-After header in response
- Exempt admin users from rate limiting

Write tests first, then implement.
```

```
Implement password reset flow.

Spec:
- User requests reset via email
- Reset token valid for 1 hour
- Token is single-use
- User must confirm new password
- Old password immediately invalidated

TDD approach: tests first, then implementation.
```

---

### Example 2: Specification-Driven API Development

**Prompt**:
```
Build a REST API for managing blog posts.

OpenAPI Specification:
- GET /posts - List all posts (paginated, 20 per page)
- GET /posts/:id - Get single post
- POST /posts - Create post (title, content, authorId required)
- PUT /posts/:id - Update post
- DELETE /posts/:id - Delete post

Validation:
- Title: 1-200 characters
- Content: 1-50000 characters
- Author must exist

Write integration tests that verify the spec, then implement the API.
```

**Why It Works**:
- OpenAPI spec is unambiguous specification
- Validation rules become test assertions
- PM treats spec as contract - tests verify compliance
- Encourages API-first design

**Agents Involved**:
1. **QA Agent** - Creates integration tests from OpenAPI spec
2. **Engineer Agent** - Implements API controllers and validation
3. **Documentation Agent** - Generates API documentation from spec
4. **PM Agent** - Verifies implementation matches specification

**Variations**:

```
Create a GraphQL API for our product catalog.

Schema:
type Product {
  id: ID!
  name: String!
  price: Float!
  inventory: Int!
  categories: [Category!]!
}

type Query {
  products(limit: Int = 10, offset: Int = 0): [Product!]!
  product(id: ID!): Product
}

type Mutation {
  createProduct(input: ProductInput!): Product!
  updateInventory(id: ID!, quantity: Int!): Product!
}

Write tests that validate the schema, then implement resolvers.
```

---

### Example 3: Acceptance Criteria as Tests

**Prompt**:
```
Feature: Shopping cart checkout

Acceptance Criteria:
✓ User can add items to cart
✓ Cart displays correct subtotal
✓ Tax is calculated based on shipping address
✓ Shipping cost is added to total
✓ Discount codes can be applied
✓ Invalid discount codes show error message
✓ Payment is processed via Stripe
✓ Order confirmation email is sent
✓ Cart is emptied after successful checkout

Write tests for each acceptance criterion first, then implement the checkout flow.
```

**Why It Works**:
- Acceptance criteria map directly to test cases
- ✓ checkboxes make criteria explicit and countable
- PM can verify each criterion has corresponding test
- Clear definition of "done"

**Agents Involved**:
1. **QA Agent** - Creates test suite with one test per criterion
2. **Engineer Agent** - Implements checkout flow
3. **Web QA Agent** - Adds E2E tests for user flow
4. **PM Agent** - Verifies all acceptance criteria have passing tests

**Variations**:

```
Feature: File upload with virus scanning

Acceptance Criteria:
✓ Files up to 100MB can be uploaded
✓ Supported formats: PDF, DOCX, XLSX, PNG, JPG
✓ Files are scanned for viruses before storage
✓ Infected files are rejected with error message
✓ Clean files are stored in S3
✓ Upload progress is displayed to user
✓ User receives notification when upload completes

Tests first, then implementation.
```

---

## Scaffold from Spec

### Example 1: New Microservice from Architecture Spec

**Prompt**:
```
Create a new notification service with the following architecture:

Technology Stack:
- Python 3.11+ with FastAPI
- PostgreSQL for notification history
- Redis for rate limiting
- Celery for async job processing
- SendGrid for email, Twilio for SMS

Service Structure:
- /api/v1/notifications - REST API
- /workers - Celery background workers
- /models - SQLAlchemy models
- /services - Business logic layer
- /integrations - SendGrid/Twilio clients

Features:
- Send email notifications
- Send SMS notifications
- Rate limiting (per user and global)
- Notification templates
- Delivery status tracking
- Retry failed deliveries

Generate the complete project structure with configuration files,
dependency management, and basic implementations for each component.
```

**Why It Works**:
- Complete technology stack specified
- Clear service boundaries and structure
- Features list guides implementation priorities
- PM can coordinate multiple agents to scaffold everything

**Agents Involved**:
1. **Research Agent** - Analyzes best practices for each technology
2. **Python Engineer** - Scaffolds FastAPI app structure
3. **Data Engineer** - Designs database schema
4. **Ops Agent** - Creates Docker configuration
5. **Documentation Agent** - Generates README and API docs
6. **PM Agent** - Orchestrates consistent structure

**Variations**:

```
Scaffold a React TypeScript SPA with the following:

Stack:
- React 18 with TypeScript
- Vite for build tooling
- React Router for navigation
- TanStack Query for data fetching
- Tailwind CSS for styling
- Vitest + React Testing Library

Structure:
- /src/pages - Route components
- /src/components - Reusable components
- /src/hooks - Custom hooks
- /src/api - API client
- /src/types - TypeScript definitions
- /src/utils - Utility functions

Set up linting (ESLint), formatting (Prettier), and testing infrastructure.
```

---

### Example 2: Project Structure from Design Doc

**Prompt**:
```
Create a CLI tool for managing Kubernetes deployments.

Requirements Document:

Purpose:
- Simplify common kubectl operations
- Provide deployment templates
- Handle rollbacks safely
- Validate configurations before apply

User Stories:
1. As a developer, I can deploy to staging with one command
2. As an operator, I can rollback deployments if they fail
3. As a team lead, I can define deployment templates
4. As anyone, I get clear error messages when configs are invalid

Technical Requirements:
- Written in Go
- Use Cobra for CLI framework
- Support multiple Kubernetes contexts
- Configuration via YAML files
- Colored output for readability
- Comprehensive error handling

Create the complete project structure following Go best practices,
including main.go, command structure, configuration handling, and tests.
```

**Why It Works**:
- Requirements doc provides complete context
- User stories guide feature implementation
- Technical requirements specify tooling
- PM can break down into tasks for multiple agents

**Agents Involved**:
1. **Research Agent** - Studies Go CLI best practices and Cobra patterns
2. **Engineer Agent** - Scaffolds Go project structure
3. **Documentation Agent** - Creates README with usage examples
4. **QA Agent** - Sets up test framework
5. **PM Agent** - Ensures structure matches requirements

**Variations**:

```
Build a data pipeline for processing user analytics events.

Design Specification:

Data Flow:
1. Events arrive via Kafka topic
2. Validated against schema
3. Enriched with user metadata
4. Aggregated into time windows
5. Stored in ClickHouse for analytics

Architecture:
- Event consumers (Python + kafka-python)
- Schema validation (JSON Schema)
- Enrichment service (queries PostgreSQL)
- Aggregation service (PySpark)
- Storage writer (ClickHouse client)

Quality Requirements:
- At-least-once delivery guarantee
- Handle 10k events/second
- Monitoring via Prometheus
- Dead letter queue for failed events

Scaffold the complete pipeline with all services and infrastructure config.
```

---

### Example 3: Technology Selection Guidance

**Prompt**:
```
I need to build a real-time collaborative document editor.

Requirements:
- Multiple users can edit simultaneously
- Changes appear instantly for all users
- Offline editing with sync when reconnected
- Revision history
- Support for rich text formatting
- Must scale to 10k concurrent users

Research and recommend:
1. Technology stack (language, framework, database)
2. Real-time sync approach (WebSockets, CRDTs, OT, etc.)
3. Database choice for documents and revisions
4. Caching strategy
5. Deployment architecture

Then scaffold the project based on your recommendations.
```

**Why It Works**:
- Requirements guide technology selection
- Asks for research first, then implementation
- PM delegates research before scaffolding
- Explicit decision points ensure informed choices

**Agents Involved**:
1. **Research Agent** - Analyzes options for real-time sync, databases, etc.
2. **Engineer Agent** - Recommends stack based on requirements
3. **Data Engineer** - Designs schema for documents and revisions
4. **Ops Agent** - Plans deployment architecture
5. **PM Agent** - Synthesizes recommendations, then scaffolds
6. **Documentation Agent** - Documents technology choices and rationale

**Variations**:

```
Build a machine learning API for image classification.

Requirements:
- Accept image uploads
- Return top 5 predicted categories with confidence scores
- Support batch processing
- Handle 100 requests/second
- Model updates without downtime
- A/B testing for model versions

Research and recommend the stack, then create project structure:
- ML framework (TensorFlow, PyTorch, etc.)
- API framework
- Model serving approach
- Storage for uploaded images
- Queue system for batch jobs
- Monitoring and metrics collection
```

---

## Codebase-wide Refactors with Guardrails

### Example 1: Safe Database Migration

**Prompt**:
```
Refactor all database queries to use the repository pattern.

Requirements:
- Create repository classes for each model (User, Post, Comment)
- Move all queries from controllers to repositories
- Ensure all existing tests pass before and after each file change
- Create a separate commit for each repository implementation
- Run full test suite between each commit
- If any tests fail, stop and report the issue

Process one model at a time: User first, then Post, then Comment.
```

**Why It Works**:
- Clear pattern to apply (repository pattern)
- Explicit safety guardrails (tests must pass)
- Incremental approach (one model at a time)
- Atomic commits (one per repository)
- Fail-fast on test failures
- PM can enforce verification at each step

**Agents Involved**:
1. **Research Agent** - Analyzes current query patterns
2. **Refactoring Engineer** - Implements repository pattern
3. **QA Agent** - Runs test suite after each change
4. **Version Control Agent** - Creates commits
5. **PM Agent** - Enforces guardrails and sequence

**Variations**:

```
Migrate from callbacks to async/await throughout the codebase.

Safety Requirements:
- All tests must pass before starting
- Refactor one file at a time
- Run tests after each file
- Commit each file separately with descriptive message
- If tests fail, revert that file and document why
- Don't proceed to next file until current file is committed

Start with utility functions, then services, then controllers.
```

```
Replace all direct SQL queries with the ORM.

Guardrails:
- Full test coverage required before starting
- Maintain identical query behavior
- Performance cannot regress (benchmark critical queries)
- One file per commit
- Tests must pass after each file
- Document any queries that can't be translated to ORM

Process in this order: read queries, then inserts, then updates, then deletes.
```

---

### Example 2: Incremental Type Safety Addition

**Prompt**:
```
Add TypeScript types to our JavaScript codebase incrementally.

Strategy:
1. Enable TypeScript in strict mode but allow .js files
2. Start with utility functions (convert to .ts)
3. Then convert pure functions
4. Then convert classes
5. Finally convert React components

Rules:
- Each file must type-check with no 'any' types
- All tests for that file must pass
- One file per commit
- If conversion is too complex, document why and skip for now
- Keep running list of skipped files for future iteration

Generate tsconfig.json, then begin conversions.
```

**Why It Works**:
- Incremental strategy reduces risk
- Clear conversion order (simple to complex)
- No 'any' types ensures quality
- Skip mechanism prevents getting stuck
- Tracking skipped files enables future work

**Agents Involved**:
1. **Research Agent** - Analyzes codebase to categorize files
2. **Engineer Agent** - Converts files to TypeScript
3. **QA Agent** - Runs type checker and tests
4. **Version Control Agent** - Commits each conversion
5. **Documentation Agent** - Tracks skipped files
6. **PM Agent** - Orchestrates incremental process

**Variations**:

```
Add comprehensive error handling to all API endpoints.

Incremental Plan:
1. Define standard error response format
2. Create error handling middleware
3. Refactor GET endpoints to use new format
4. Then POST endpoints
5. Then PUT/PATCH endpoints
6. Then DELETE endpoints

Requirements:
- All errors must include error code, message, and timestamp
- 4xx errors log at INFO level
- 5xx errors log at ERROR level with stack trace
- Tests must verify error responses
- Commit each endpoint file separately
```

---

### Example 3: Dependency Upgrade with Rollback Plan

**Prompt**:
```
Upgrade React from 17 to 18 across the entire application.

Migration Plan:
1. Review breaking changes in React 18
2. Update package.json and install dependencies
3. Run tests - if they all pass, proceed to step 4
   If tests fail, create a branch 'react-18-blockers' with failing tests and stop
4. Update root render calls to use createRoot
5. Run tests after each file change
6. Fix any warnings one component at a time
7. Update Suspense boundaries for new behavior
8. Final full test suite run

Rollback Criteria:
- If more than 10 tests fail after dependency update, stop and report
- If any test failures can't be fixed within the component, document and skip
- Keep comprehensive notes on all changes for easy rollback

Commit strategy:
- Separate commit for package.json update
- Separate commit for each fixed component
- Tag the final working state as 'react-18-migration-complete'
```

**Why It Works**:
- Explicit migration plan with steps
- Clear success criteria (tests pass)
- Defined rollback triggers (>10 failures)
- Incremental verification (test after each file)
- Documentation of issues for future troubleshooting

**Agents Involved**:
1. **Research Agent** - Reviews React 18 breaking changes
2. **Engineer Agent** - Updates code to React 18 patterns
3. **QA Agent** - Runs test suite repeatedly
4. **Version Control Agent** - Creates rollback branch if needed
5. **Documentation Agent** - Tracks changes and issues
6. **PM Agent** - Enforces rollback criteria

**Variations**:

```
Upgrade PostgreSQL from 12 to 15.

Migration Process:
1. Review PostgreSQL 15 breaking changes
2. Create full database backup
3. Set up PostgreSQL 15 in separate container
4. Migrate schema
5. Run all database tests against new version
6. If tests pass, migrate data in batches
7. Verify data integrity after each batch
8. Update application connection config
9. Run full integration test suite

Rollback Plan:
- Keep PostgreSQL 12 running during migration
- If any batch migration fails, stop and restore from backup
- If integration tests fail, revert connection config
- Document all schema changes for rollback script
```

---

## Multi-Agent Coordination

### Example 1: Full-Stack Feature with Research → Implementation → QA

**Prompt**:
```
Implement OAuth2 authentication flow for GitHub login.

Phase 1 - Research:
- Analyze GitHub OAuth2 documentation
- Identify required API endpoints and scopes
- Document the complete OAuth flow
- Identify security considerations

Phase 2 - Implementation:
- Backend: OAuth callback handler, token exchange, user creation/lookup
- Frontend: Login button, callback page, session management
- Security review of token storage and CSRF protection

Phase 3 - QA:
- Integration tests for OAuth flow
- E2E tests for user login experience
- Security tests for CSRF, token validation
- Test error cases (denied authorization, expired tokens)

Have Research agent complete Phase 1 first and present findings.
Then Engineer implements based on research.
Then Security reviews the implementation.
Finally QA validates everything works correctly.
```

**Why It Works**:
- Explicit multi-phase workflow
- Each phase has clear deliverables
- Sequential dependencies (research → implement → review → test)
- PM coordinates handoffs between agents
- Each agent works in their domain of expertise

**Agents Involved**:
1. **Research Agent** - Phase 1: OAuth documentation and flow analysis
2. **Engineer Agent** - Phase 2: Backend and frontend implementation
3. **Security Agent** - Phase 2: Security review and hardening
4. **QA Agent** - Phase 3: Test suite creation
5. **Web QA Agent** - Phase 3: E2E testing
6. **PM Agent** - Orchestrates phases and ensures deliverables

**Variations**:

```
Build a payment processing system with Stripe.

Workflow:
1. Research: Analyze Stripe API, webhooks, error handling best practices
2. Implementation: Payment endpoints, webhook handler, database schema
3. Security: Review PCI compliance, audit sensitive data handling
4. QA: Integration tests, webhook verification, failure case testing
5. Documentation: API docs, webhook setup guide, error code reference

Execute phases sequentially with explicit handoff between agents.
```

```
Migrate monolith to microservices architecture.

Multi-Agent Process:
1. Research: Analyze current monolith, identify service boundaries
2. Architect: Design microservice interfaces, data ownership, communication
3. Engineer: Implement first microservice (user service)
4. Ops: Set up deployment, monitoring, service mesh
5. QA: Integration tests, load tests, failover scenarios
6. Documentation: Service documentation, deployment runbook

Start with Research, then get my approval before proceeding to architecture phase.
```

---

### Example 2: Complex Feature Development with Coordination

**Prompt**:
```
Build a real-time notification system.

Architecture:
- WebSocket server for real-time delivery
- Message queue (RabbitMQ) for reliable delivery
- Database for notification history
- Frontend component for notification display

Agent Coordination:
1. Research: Best practices for WebSocket scaling, message queue patterns
2. Data Engineer: Design database schema for notifications
3. Backend Engineer: Implement WebSocket server and queue consumers
4. Frontend Engineer: Build notification UI component
5. Ops: Configure RabbitMQ, deploy WebSocket server
6. QA: Test real-time delivery, queue reliability, UI updates
7. Documentation: WebSocket API, queue setup, deployment guide

Agents should work in parallel where possible:
- Data Engineer and Research can work simultaneously
- Backend and Frontend can implement in parallel after schemas are defined
- QA can write tests while implementation is ongoing

PM: Coordinate the parallel work and dependencies.
```

**Why It Works**:
- Complex system broken into agent-sized tasks
- Parallel work identified (data + research, backend + frontend)
- Dependencies explicit (schemas before implementation)
- PM coordinates timing and handoffs
- Each agent has clear deliverable

**Agents Involved**:
1. **Research Agent** - Parallel: WebSocket and queue best practices
2. **Data Engineer** - Parallel: Schema design
3. **Engineer Agent** - Depends on schema: WebSocket and queue implementation
4. **Web UI Agent** - Depends on API: Frontend component
5. **Ops Agent** - Parallel: Infrastructure setup
6. **QA Agent** - Parallel: Test writing, Sequential: Test execution
7. **Documentation Agent** - After implementation: Documentation
8. **PM Agent** - Orchestrates dependencies and parallelism

**Variations**:

```
Create a multi-tenant SaaS application.

Complex Requirements:
- Tenant isolation (database per tenant vs schema per tenant)
- Subdomain routing (tenant1.app.com)
- Billing integration (Stripe subscriptions)
- Usage metering and quotas
- Admin dashboard per tenant
- Cross-tenant reporting for super admin

Agent Workflow:
1. Research + Architect: Multi-tenancy strategy (work together)
2. Data Engineer: Design tenant isolation approach
3. Backend Engineer: Tenant middleware, billing API (depends on data design)
4. Frontend Engineer: Tenant switcher, admin dashboard (parallel with backend)
5. Ops: Subdomain DNS, tenant provisioning automation
6. QA: Tenant isolation tests, billing scenarios
7. Security: Audit tenant isolation, data leakage tests

PM: Manage complexity, coordinate research with architect, enable parallel work.
```

---

### Example 3: Investigation → Fix → Verify Workflow

**Prompt**:
```
Production issue: API response times have increased from 200ms to 2000ms over the past week.

Investigation Workflow:
1. Research: Analyze recent deployments, dependency changes, traffic patterns
2. Data Engineer: Query database for slow queries, check index usage
3. Ops: Check server metrics (CPU, memory, disk I/O)
4. Research: Synthesize findings and identify root cause
5. Engineer: Implement fix based on root cause
6. QA: Verify fix in staging with realistic load
7. Ops: Deploy to production with monitoring
8. QA: Verify production metrics return to normal

Each phase reports findings before next phase begins.
Stop if root cause isn't clear after investigation phases.
```

**Why It Works**:
- Systematic investigation from multiple angles
- Each agent investigates their domain
- Root cause synthesis before fix
- Verification in staging before production
- Stop condition if root cause unclear
- PM coordinates sequential workflow with gates

**Agents Involved**:
1. **Research Agent** - Recent changes analysis, synthesis of findings
2. **Data Engineer** - Database performance analysis
3. **Ops Agent** - Infrastructure metrics investigation and deployment
4. **Engineer Agent** - Implements fix
5. **QA Agent** - Staging and production verification
6. **PM Agent** - Coordinates investigation, gates progression

**Variations**:

```
Bug: Users report sporadic data corruption in their profiles.

Root Cause Analysis:
1. QA: Reproduce the issue with test data
2. Research: Analyze code paths that modify user profiles
3. Data Engineer: Check database transaction logs for anomalies
4. Security: Check for potential injection attacks or unauthorized access
5. Research: Identify root cause from all findings
6. Engineer: Implement fix with additional validation
7. QA: Regression tests, run at high concurrency to verify fix
8. Security: Final audit of the fix

Don't proceed to fix until root cause is confirmed.
```

---

## Investigation/Research Mode

### Example 1: Deep Codebase Analysis ("Founder Mode")

**Prompt**:
```
I'm taking over this codebase and need a comprehensive understanding.

Research and document:

1. Architecture Overview:
   - High-level system design
   - Service boundaries and responsibilities
   - Data flow between components
   - External dependencies and integrations

2. Code Organization:
   - Directory structure and purposes
   - Naming conventions
   - Code organization patterns

3. Technology Stack:
   - Languages, frameworks, libraries (with versions)
   - Build tools and configuration
   - Testing infrastructure

4. Data Model:
   - Database schema
   - Key entity relationships
   - Data validation and constraints

5. Business Logic:
   - Core features and user workflows
   - Background jobs and scheduled tasks
   - API endpoints and contracts

6. Quality and Operations:
   - Test coverage and strategy
   - Deployment process
   - Monitoring and logging approach

7. Known Issues:
   - TODOs and FIXMEs in code
   - Technical debt areas
   - Missing tests or documentation

Create a comprehensive report with code examples and recommendations.
Don't commit anything - this is pure analysis.
```

**Why It Works**:
- Comprehensive scope covers all aspects
- Structured analysis areas guide research
- "Don't commit" keeps it read-only
- Code examples make findings concrete
- PM coordinates multiple research passes

**Agents Involved**:
1. **Research Agent** - Code analysis, pattern identification
2. **Code Analyzer Agent** - AST analysis, complexity metrics
3. **Data Engineer** - Database schema analysis
4. **Ops Agent** - Deployment and infrastructure review
5. **QA Agent** - Test coverage analysis
6. **Documentation Agent** - Creates comprehensive report
7. **PM Agent** - Synthesizes all findings

**Variations**:

```
Analyze this legacy codebase to plan a modernization effort.

Investigation Areas:
1. Technical Debt Assessment:
   - Outdated dependencies
   - Deprecated APIs in use
   - Code duplication
   - Complexity hotspots

2. Modernization Opportunities:
   - Old patterns vs modern alternatives
   - Performance bottlenecks
   - Security vulnerabilities
   - Testing gaps

3. Migration Risk Analysis:
   - Critical business logic areas
   - External API dependencies
   - Database migration challenges
   - Backward compatibility requirements

4. Modernization Roadmap:
   - Recommended migration order
   - Quick wins vs long-term refactors
   - Resource estimation
   - Risk mitigation strategies

Research only - no code changes.
```

---

### Example 2: Architecture Investigation

**Prompt**:
```
Investigate why our system doesn't scale horizontally.

Analysis Required:

1. Stateful Components:
   - Identify all components storing state in memory
   - Session management approach
   - Caching strategies
   - In-memory data structures

2. Database Bottlenecks:
   - Query performance at scale
   - Lock contention issues
   - Connection pool limitations
   - Schema design scalability

3. External Dependencies:
   - Third-party API rate limits
   - Service-to-service communication patterns
   - Single points of failure
   - Network latency issues

4. Deployment Architecture:
   - Load balancer configuration
   - Container orchestration
   - Auto-scaling policies
   - Health check implementation

5. Recommendations:
   - Specific changes needed for horizontal scaling
   - Trade-offs of each approach
   - Implementation complexity
   - Performance impact

Provide detailed analysis with evidence from the codebase.
Investigation only - no implementation.
```

**Why It Works**:
- Focused investigation goal (horizontal scaling blockers)
- Systematic analysis of typical scaling issues
- Evidence-based conclusions from codebase
- Actionable recommendations
- "Investigation only" prevents premature fixes

**Agents Involved**:
1. **Research Agent** - Code analysis for state management
2. **Data Engineer** - Database scalability analysis
3. **Ops Agent** - Infrastructure and deployment review
4. **Code Analyzer Agent** - Dependency mapping
5. **PM Agent** - Synthesizes findings and recommendations

**Variations**:

```
Analyze our security posture for SOC 2 compliance.

Security Audit:
1. Authentication and Authorization:
   - Auth implementation analysis
   - Session management security
   - Permission enforcement
   - API authentication

2. Data Protection:
   - Sensitive data identification
   - Encryption at rest and in transit
   - Data access logging
   - PII handling

3. Infrastructure Security:
   - Network segmentation
   - Secrets management
   - Dependency vulnerabilities
   - Security headers

4. Compliance Gaps:
   - Missing controls for SOC 2
   - Required logging and monitoring
   - Access control deficiencies
   - Remediation roadmap

Investigation and report only - no code changes yet.
```

---

### Example 3: Dependency Analysis and Mapping

**Prompt**:
```
Map the entire dependency graph of our microservices.

Investigation:

1. Service Inventory:
   - All microservices and their responsibilities
   - Communication protocols (REST, gRPC, message queues)
   - Deployment relationships

2. Dependency Mapping:
   - Service-to-service dependencies
   - Shared databases or datastores
   - External API dependencies
   - Library and framework dependencies

3. Failure Impact Analysis:
   - What happens if each service fails?
   - Cascading failure scenarios
   - Services without fallback mechanisms
   - Circular dependencies

4. Optimization Opportunities:
   - Unnecessary dependencies
   - Opportunities for async communication
   - Services that could be merged
   - Services that should be split

5. Deliverable:
   - Visual dependency graph
   - Failure impact matrix
   - Recommended architectural changes

Research and document - no code changes.
```

**Why It Works**:
- Systematic service and dependency discovery
- Risk analysis (failure scenarios)
- Optimization identification
- Visual deliverable (dependency graph)
- "No code changes" keeps it analytical

**Agents Involved**:
1. **Research Agent** - Service discovery and communication analysis
2. **Code Analyzer Agent** - Dependency extraction
3. **Ops Agent** - Deployment and infrastructure dependencies
4. **Documentation Agent** - Creates dependency graph and matrix
5. **PM Agent** - Coordinates analysis and synthesizes recommendations

**Variations**:

```
Analyze our frontend bundle to reduce size.

Bundle Investigation:
1. Current State:
   - Total bundle size
   - Breakdown by dependency
   - Duplicate dependencies
   - Unused code

2. Optimization Opportunities:
   - Large dependencies with smaller alternatives
   - Unnecessary polyfills
   - Code splitting opportunities
   - Tree-shaking effectiveness

3. Impact Analysis:
   - Load time improvement estimates
   - Browser compatibility trade-offs
   - Breaking change risks
   - Implementation effort

4. Recommendations:
   - Prioritized optimization list
   - Quick wins vs long-term refactors
   - Bundle size targets

Analysis only - don't implement optimizations yet.
```

---

## Quick Reference

### Debugging Patterns

| Goal | Key Phrases | Agents |
|------|-------------|---------|
| Investigate without changing code | "Do not commit", "investigation only" | Research, Engineer |
| Isolated debugging | "Create a branch", "don't merge to main" | Version Control, Research |
| Add temporary instrumentation | "Don't commit", "temporary logging" | Engineer, Research |

### TxDD Patterns

| Goal | Key Phrases | Agents |
|------|-------------|---------|
| Test-first development | "Write tests first", "TDD approach" | QA, Engineer |
| Spec-driven API | "OpenAPI spec", "verify the spec" | QA, Engineer, Documentation |
| Acceptance criteria | "Acceptance criteria", "tests for each criterion" | QA, Engineer, PM |

### Scaffolding Patterns

| Goal | Key Phrases | Agents |
|------|-------------|---------|
| New service/project | "Technology stack", "project structure", "scaffold" | Research, Engineer, Ops |
| Architecture from design | "Requirements document", "design specification" | Research, Engineer, Documentation |
| Technology selection | "Research and recommend", "then scaffold" | Research, Engineer |

### Refactoring Patterns

| Goal | Key Phrases | Agents |
|------|-------------|---------|
| Safe incremental refactor | "Tests must pass", "one file at a time", "separate commits" | Refactoring Engineer, QA, Version Control |
| Migration with rollback | "Rollback criteria", "if tests fail, stop" | Engineer, QA, Version Control |
| Type safety addition | "Incremental", "no 'any' types", "skip if too complex" | Engineer, QA, Documentation |

### Multi-Agent Patterns

| Goal | Key Phrases | Agents |
|------|-------------|---------|
| Phased workflow | "Phase 1", "Phase 2", "sequential" | Multiple agents, PM coordinates |
| Parallel work | "Work in parallel", "simultaneously" | Multiple agents, PM coordinates |
| Investigation workflow | "Research first", "synthesize findings", "then fix" | Research, Engineer, QA, Ops |

### Research Patterns

| Goal | Key Phrases | Agents |
|------|-------------|---------|
| Codebase deep dive | "Comprehensive understanding", "research and document" | Research, Code Analyzer, Documentation |
| Architecture analysis | "Investigate why", "analysis required", "evidence from codebase" | Research, Data Engineer, Ops |
| Dependency mapping | "Map the dependency graph", "failure impact analysis" | Research, Code Analyzer, Documentation |

---

## See Also

- **[Prompting Guide](prompting-guide.md)** - General principles for effective MPM prompts
- **[Agent System Overview](../reference/agents-overview.md)** - Complete agent capabilities reference
- **[Ticketing Workflows](ticketing-workflows.md)** - Using tickets with MPM
- **[Architecture Overview](../architecture/overview.md)** - System architecture and design patterns

---

**Questions or examples to add?** Open an issue on GitHub or contribute via PR.
