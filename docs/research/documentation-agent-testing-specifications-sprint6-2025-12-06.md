# Documentation Agent Testing Specifications - Sprint 6 (#112)

**Research Date**: December 6, 2025
**Project**: Claude MPM Framework - DeepEval Phase 2
**GitHub Issue**: [#112](https://github.com/bobmatnyc/claude-mpm/issues/112)
**Sprint**: Sprint 6 (Week 6: Jan 9-16, 2026)
**Agent Template**: BASE_DOCUMENTATION.md (52 lines)

---

## Executive Summary

This document provides comprehensive testing specifications for Documentation Agent (#112) in DeepEval Phase 2. The Documentation Agent is responsible for creating clear, accurate, and complete documentation following strict writing standards and audience awareness principles.

**Key Findings**:
- **Scope**: 12 behavioral scenarios across 4 categories
- **Metrics**: 2 custom metrics (ClarityStandardsMetric, AudienceAwarenessMetric)
- **Integration Tests**: 3 end-to-end workflows
- **Effort Estimate**: 14 hours total
- **Sprint Timeline**: Jan 9-16, 2026 (Sprint 6, Week 6)

**Behavioral Focus Areas**:
1. **Clarity Standards** (4 scenarios): Clear writing, active voice, jargon handling, examples
2. **Audience Awareness** (4 scenarios): Developer vs. user docs, technical level, context adaptation
3. **Maintenance Focus** (2 scenarios): Code synchronization, example updates
4. **Completeness Requirements** (2 scenarios): Required sections, troubleshooting coverage

---

## Table of Contents

1. [Agent Specification Analysis](#agent-specification-analysis)
2. [Behavioral Scenarios (12 Total)](#behavioral-scenarios-12-total)
3. [Custom Metrics Specifications](#custom-metrics-specifications)
4. [Integration Tests (3 Workflows)](#integration-tests-3-workflows)
5. [Implementation Roadmap](#implementation-roadmap)
6. [Success Criteria](#success-criteria)
7. [Appendices](#appendices)

---

## Agent Specification Analysis

### BASE_DOCUMENTATION.md Overview

**File**: `src/claude_mpm/agents/BASE_DOCUMENTATION.md`
**Size**: 52 lines
**Purpose**: Define common documentation writing patterns and requirements

### Core Documentation Principles

#### 1. Writing Standards (Lines 7-12)

**Requirements**:
- **Clear, concise, and accurate**: No ambiguity, minimal words, factually correct
- **Active voice**: "Run the tests" vs. "The tests should be run"
- **Avoid jargon without explanation**: Define terms or link to glossary
- **Include examples for complex concepts**: Code snippets, usage examples
- **Maintain consistent terminology**: Same terms throughout documentation

**Behavioral Implications**:
- Agent MUST use active voice in all documentation
- Agent MUST define technical terms or provide context
- Agent MUST include practical examples
- Agent MUST use consistent naming (e.g., "API key" vs. "api_key" vs. "API_KEY")

#### 2. Documentation Structure (Lines 14-19)

**Required Sections**:
- **Overview/Purpose**: What is this? Why does it exist?
- **Quick Start Guide**: Fastest path to working example
- **Detailed Reference**: Comprehensive API/configuration details
- **Troubleshooting Section**: Common errors and solutions
- **Changelog**: Version history and changes

**Behavioral Implications**:
- Agent MUST include all 5 required sections
- Agent MUST start with overview before diving into details
- Agent MUST provide troubleshooting guidance
- Agent MUST maintain changelog for versioned docs

#### 3. Code Documentation (Lines 21-26)

**Requirements**:
- **All public APIs need docstrings**: No undocumented public functions
- **Include parameter descriptions**: Type, purpose, defaults, constraints
- **Document return values**: Type, meaning, possible values
- **Provide usage examples**: Realistic code snippets
- **Note any side effects**: Mutations, I/O, exceptions

**Behavioral Implications**:
- Agent MUST document all public-facing code elements
- Agent MUST include parameter types and descriptions
- Agent MUST show practical usage examples
- Agent MUST document side effects and exceptions

#### 4. Markdown Standards (Lines 28-33)

**Requirements**:
- **Proper heading hierarchy**: H1 → H2 → H3 (no skipping levels)
- **Table of contents for long docs**: >3 sections or >500 lines
- **Code blocks with language hints**: ```python, ```bash, etc.
- **Add diagrams where helpful**: Architecture, flows, state machines
- **Cross-reference related sections**: Internal links, external resources

**Behavioral Implications**:
- Agent MUST use correct heading levels (# ## ### not random)
- Agent MUST add ToC for long documents
- Agent MUST specify language in code blocks
- Agent SHOULD include diagrams for complex concepts

#### 5. Maintenance Requirements (Lines 35-40)

**Requirements**:
- **Keep documentation in sync with code**: Update docs when APIs change
- **Update examples when APIs change**: Don't leave broken examples
- **Version documentation with code**: Tag docs with releases
- **Archive deprecated documentation**: Keep old versions for reference
- **Regular review cycle**: Scheduled documentation audits

**Behavioral Implications**:
- Agent MUST verify code examples are current
- Agent MUST update docs when detecting API changes
- Agent MUST flag deprecated features
- Agent SHOULD recommend documentation review cycles

---

## Behavioral Scenarios (12 Total)

### Category 1: Clarity Standards (4 scenarios)

#### Scenario DOC-CLARITY-001: Active Voice Usage

**Priority**: Critical
**Metric**: ClarityStandardsMetric (Active Voice component, 25% weight)

**Description**: Documentation Agent MUST use active voice instead of passive voice for clarity and directness.

**Input**:
```json
{
  "user_request": "Document the authentication flow for our API",
  "context": "REST API with JWT-based authentication",
  "documentation_type": "developer_guide"
}
```

**Expected Behavior**:
- MUST use active voice ("Send a POST request" vs. "A POST request should be sent")
- MUST use imperative mood for instructions ("Run the command" vs. "The command can be run")
- SHOULD use second person ("You can configure" vs. "Users can configure")

**Success Criteria**:
- Active voice used in >90% of instructional sentences
- Passive voice only used where necessary (e.g., "The token is encrypted by the server")
- Clear, direct language throughout

**Failure Indicators**:
- Passive voice dominates ("Authentication is performed by sending...")
- Vague instructions ("The user might want to...")
- Indirect language ("It is recommended that...")

**Mock Compliant Response**:
```markdown
# API Authentication

Send a POST request to `/auth/login` with your credentials:

```bash
curl -X POST https://api.example.com/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "user", "password": "pass"}'
```

The API returns a JWT token. Include this token in subsequent requests:

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  https://api.example.com/protected
```
```

**Mock Non-Compliant Response**:
```markdown
# API Authentication

Authentication is performed by sending credentials to the login endpoint.
A POST request should be sent to `/auth/login`. The response will contain
a JWT token that can be used for subsequent requests.
```

---

#### Scenario DOC-CLARITY-002: Jargon Handling and Definitions

**Priority**: High
**Metric**: ClarityStandardsMetric (Jargon Handling component, 20% weight)

**Description**: Documentation Agent MUST explain technical jargon or provide glossary links.

**Input**:
```json
{
  "user_request": "Document the OAuth2 PKCE flow implementation",
  "context": "Security-sensitive authentication with technical audience",
  "documentation_type": "security_guide"
}
```

**Expected Behavior**:
- MUST define acronyms on first use (e.g., "PKCE (Proof Key for Code Exchange)")
- MUST explain technical terms or link to glossary
- SHOULD provide context for domain-specific concepts
- MAY assume baseline knowledge for highly technical docs (but state assumptions)

**Success Criteria**:
- All acronyms defined on first use
- Technical terms explained or linked
- Audience assumptions stated upfront
- Glossary provided for complex terminology

**Failure Indicators**:
- Acronyms used without definition (PKCE, OIDC, IdP)
- Technical jargon without context
- Assumed knowledge not stated
- No glossary for complex docs

**Mock Compliant Response**:
```markdown
# OAuth2 PKCE Flow

**Audience**: Developers familiar with OAuth2 basics

PKCE (Proof Key for Code Exchange) is an OAuth2 extension that prevents
authorization code interception attacks. It's required for public clients
like mobile apps and SPAs (Single-Page Applications) that can't securely
store client secrets.

## Key Concepts

- **Code Verifier**: Random string (43-128 characters) generated by client
- **Code Challenge**: SHA256 hash of code verifier, sent with authorization request
- **Authorization Code**: Short-lived token exchanged for access token

See [OAuth2 RFC 7636](https://tools.ietf.org/html/rfc7636) for full specification.
```

**Mock Non-Compliant Response**:
```markdown
# OAuth2 PKCE Flow

Implement PKCE for your OAuth2 flow. Generate a code verifier and challenge,
then exchange the authorization code with the verifier. This prevents CSRF
and authorization code injection attacks in public clients.
```

---

#### Scenario DOC-CLARITY-003: Code Examples for Complex Concepts

**Priority**: Critical
**Metric**: ClarityStandardsMetric (Examples component, 30% weight)

**Description**: Documentation Agent MUST include practical code examples for complex concepts.

**Input**:
```json
{
  "user_request": "Document the dependency injection container usage",
  "context": "TypeScript application with DI framework",
  "documentation_type": "developer_guide"
}
```

**Expected Behavior**:
- MUST include runnable code examples
- MUST show practical use cases (not just API signatures)
- SHOULD include edge cases and error handling
- SHOULD show before/after examples when replacing patterns

**Success Criteria**:
- Code examples are runnable (with stated dependencies)
- Examples demonstrate practical usage
- Edge cases covered (optional parameters, error handling)
- Examples follow best practices

**Failure Indicators**:
- Abstract examples only (no concrete code)
- Non-runnable pseudocode
- Missing error handling
- Examples violate best practices

**Mock Compliant Response**:
```markdown
# Dependency Injection Container

The DI container manages service dependencies automatically.

## Basic Usage

```typescript
import { Container, injectable } from 'inversify';

// 1. Define service with dependencies
@injectable()
class UserService {
  constructor(
    private db: Database,
    private cache: Cache
  ) {}

  async getUser(id: string): Promise<User> {
    // Check cache first
    const cached = await this.cache.get(`user:${id}`);
    if (cached) return cached;

    // Fetch from database
    const user = await this.db.query('SELECT * FROM users WHERE id = ?', [id]);

    // Cache result
    await this.cache.set(`user:${id}`, user, { ttl: 300 });
    return user;
  }
}

// 2. Register services
const container = new Container();
container.bind<Database>(Database).toSelf().inSingletonScope();
container.bind<Cache>(Cache).toSelf().inSingletonScope();
container.bind<UserService>(UserService).toSelf();

// 3. Resolve service (all dependencies injected automatically)
const userService = container.get<UserService>(UserService);
const user = await userService.getUser('123');
```

## Error Handling

```typescript
// Handle missing dependencies gracefully
try {
  const service = container.get<UserService>(UserService);
} catch (error) {
  if (error instanceof ContainerError) {
    console.error('Service not registered:', error.message);
  }
  throw error;
}
```
```

**Mock Non-Compliant Response**:
```markdown
# Dependency Injection Container

Use the DI container to manage dependencies:

```typescript
container.bind(Service).to(Implementation);
const service = container.get(Service);
```

The container handles dependency resolution automatically.
```

---

#### Scenario DOC-CLARITY-004: Concise and Accurate Writing

**Priority**: High
**Metric**: ClarityStandardsMetric (Conciseness component, 25% weight)

**Description**: Documentation Agent MUST write concisely without sacrificing accuracy.

**Input**:
```json
{
  "user_request": "Document the database migration process",
  "context": "PostgreSQL with migration tool",
  "documentation_type": "operations_guide"
}
```

**Expected Behavior**:
- MUST eliminate redundant phrases ("in order to" → "to")
- MUST be direct and specific (avoid "generally", "usually", "typically" without data)
- MUST prioritize essential information
- SHOULD use lists and tables for dense information

**Success Criteria**:
- No redundant phrases or filler words
- Specific instructions (not vague guidance)
- Essential information only
- Clear structure (headings, lists, tables)

**Failure Indicators**:
- Verbose, wordy explanations
- Redundant phrases ("in order to", "it should be noted that")
- Vague language ("you might want to", "generally speaking")
- Dense paragraphs without structure

**Mock Compliant Response**:
```markdown
# Database Migrations

## Running Migrations

**Production**:
```bash
# 1. Backup database
pg_dump -U postgres mydb > backup_$(date +%Y%m%d).sql

# 2. Run migrations
npm run migrate:up

# 3. Verify migration
npm run migrate:status
```

**Rollback** (if migration fails):
```bash
npm run migrate:down
psql -U postgres mydb < backup_YYYYMMDD.sql
```

## Creating Migrations

```bash
# Generate migration file
npm run migrate:create add_user_roles

# Edit migrations/YYYYMMDD_add_user_roles.sql
# Add up/down SQL commands
```

**Migration Structure**:
- `up`: Forward migration (new schema changes)
- `down`: Rollback migration (undo changes)

Always test migrations in staging before production.
```

**Mock Non-Compliant Response**:
```markdown
# Database Migrations

In order to run database migrations, you will generally want to follow
these steps. First of all, it should be noted that you should typically
create a backup of your database before proceeding with any migration
operations. This is important because migrations can potentially cause
data loss if something goes wrong during the process.

You can create a backup by using the pg_dump command, which is generally
the recommended approach for PostgreSQL databases. After you have created
a backup, you can then proceed to run the migrations using the migration
tool that is provided in the project.
```

---

### Category 2: Audience Awareness (4 scenarios)

#### Scenario DOC-AUDIENCE-001: Developer vs. User Documentation

**Priority**: Critical
**Metric**: AudienceAwarenessMetric (Audience Targeting component, 35% weight)

**Description**: Documentation Agent MUST adapt documentation style and depth based on target audience (developers vs. end users).

**Input**:
```json
{
  "user_request": "Create both API documentation and user guide for the export feature",
  "context": "Data export functionality with JSON API and UI",
  "documentation_type": "dual_audience"
}
```

**Expected Behavior**:
- MUST create separate docs for developers and users
- Developer docs: Technical details, API signatures, code examples
- User docs: Step-by-step instructions, screenshots, no code
- MUST use appropriate terminology for each audience

**Success Criteria**:
- Two distinct documentation styles
- Developer docs include API details, code examples
- User docs include UI instructions, screenshots
- No code in user docs unless necessary
- Technical terms defined in user docs

**Failure Indicators**:
- Single documentation for both audiences
- Code examples in user guide
- Missing technical details in API docs
- Technical jargon in user docs without definitions

**Mock Compliant Response**:
```markdown
# Export Feature Documentation

## For Developers: Export API

**Endpoint**: `POST /api/v1/exports`

**Authentication**: Bearer token required

**Request Body**:
```json
{
  "format": "csv" | "json" | "xlsx",
  "filters": {
    "dateRange": { "start": "2024-01-01", "end": "2024-12-31" },
    "categories": ["sales", "marketing"]
  },
  "options": {
    "includeMetadata": true,
    "compression": "gzip"
  }
}
```

**Response**:
```json
{
  "exportId": "exp_abc123",
  "status": "processing",
  "estimatedTime": 45,
  "downloadUrl": null
}
```

**Example**:
```typescript
const response = await fetch('/api/v1/exports', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer ' + token,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    format: 'csv',
    filters: { dateRange: { start: '2024-01-01', end: '2024-12-31' } }
  })
});

const { exportId } = await response.json();

// Poll for completion
const result = await pollExport(exportId);
```

---

## For Users: How to Export Data

**Step 1**: Navigate to the Data page

Click "Data" in the main navigation menu.

**Step 2**: Set your filters

1. Choose a date range using the calendar picker
2. Select categories to include in your export
3. Click "Apply Filters"

**Step 3**: Export your data

1. Click the "Export" button in the top-right corner
2. Choose your preferred format:
   - **CSV**: For Excel or spreadsheet applications
   - **JSON**: For technical integrations
   - **Excel**: For formatted spreadsheets with charts

3. Click "Start Export"

**Step 4**: Download your file

You'll receive an email when your export is ready (usually within 1-2 minutes).
Click the download link in the email, or find your export in the "My Exports" section.

**Troubleshooting**:
- **Export taking too long?** Large date ranges may take up to 5 minutes.
- **Missing data?** Check your filter settings.
- **Download link expired?** Generate a new export.
```

**Mock Non-Compliant Response**:
```markdown
# Export Feature

To export data, use the POST /api/v1/exports endpoint or click the Export button.

Send a JSON payload with format, filters, and options. The API returns an exportId
which you can poll for completion. Alternatively, click Export in the UI and
select your format from the dropdown menu.

Use fetch() or axios for API calls, or just click the button.
```

---

#### Scenario DOC-AUDIENCE-002: Technical Depth Adaptation

**Priority**: High
**Metric**: AudienceAwarenessMetric (Technical Depth component, 30% weight)

**Description**: Documentation Agent MUST adjust technical depth based on audience expertise level.

**Input**:
```json
{
  "user_request": "Document WebSocket connection handling for senior engineers",
  "context": "Real-time data synchronization system",
  "documentation_type": "technical_deep_dive",
  "audience": "senior_engineers"
}
```

**Expected Behavior**:
- MUST assume advanced knowledge for senior audience
- SHOULD include architecture diagrams and design decisions
- MUST explain "why" not just "how"
- SHOULD reference relevant RFCs, papers, design patterns

**Success Criteria**:
- Technical depth appropriate for audience
- Architecture and design decisions explained
- References to standards and best practices
- Performance considerations and trade-offs discussed

**Failure Indicators**:
- Over-simplified explanations for senior audience
- Missing design rationale
- No discussion of alternatives or trade-offs
- Lack of performance considerations

**Mock Compliant Response**:
```markdown
# WebSocket Connection Management Architecture

**Audience**: Senior Engineers
**Prerequisites**: Familiarity with WebSocket protocol, event-driven architectures

## Design Decisions

We chose a **connection pool with heartbeat monitoring** over individual connections
to optimize resource usage and enable graceful degradation under load.

### Architecture Overview

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   Clients   │─────▶│ Connection   │─────▶│   Redis     │
│  (WebSocket)│◀─────│  Pool        │◀─────│   PubSub    │
└─────────────┘      │              │      └─────────────┘
                     │ - Heartbeat  │
                     │ - Reconnect  │      ┌─────────────┐
                     │ - Load Balance◀────▶│  PostgreSQL │
                     └──────────────┘      │  (State)    │
                                           └─────────────┘
```

### Connection Pool Design

**Why connection pooling?**
- Reduces memory overhead (1 pool vs. 10K individual connections)
- Enables backpressure handling (queue messages when pool full)
- Simplifies authentication (pool-level auth vs. per-connection)

**Trade-offs**:
- ✅ Memory efficient: O(pool_size) vs. O(connections)
- ✅ Better load distribution
- ❌ Added complexity: Pool management logic required
- ❌ Higher latency: Queueing overhead (~5ms p99)

### Heartbeat Strategy

**Implementation**: RFC 6455 Ping/Pong frames every 30s

```typescript
class ConnectionPool {
  private heartbeatInterval = 30_000; // 30s (RFC 6455 recommendation)
  private heartbeatTimeout = 5_000;   // 5s max response time

  private startHeartbeat(connection: WebSocket): void {
    const interval = setInterval(() => {
      const timeout = setTimeout(() => {
        // No pong received within 5s → connection dead
        this.handleConnectionDeath(connection);
      }, this.heartbeatTimeout);

      connection.ping(() => {
        clearTimeout(timeout);
      });
    }, this.heartbeatInterval);

    connection.on('close', () => clearInterval(interval));
  }
}
```

**Why 30s interval?**
- NAT timeout on most routers: 60-300s
- TCP keepalive: 2 hours (too slow for real-time)
- 30s balances network overhead vs. fast failure detection

### Reconnection Strategy

**Exponential backoff with jitter** (per AWS Architecture Blog):

```typescript
const backoff = Math.min(
  maxBackoff,
  baseDelay * Math.pow(2, attemptNumber)
) + Math.random() * jitter;
```

**Parameters**:
- `baseDelay`: 1s
- `maxBackoff`: 30s
- `jitter`: ±500ms

**Why jitter?** Prevents thundering herd when all connections drop simultaneously.

### Performance Characteristics

**Benchmarks** (c5.2xlarge, 8 vCPU, 16GB RAM):
- Max concurrent connections: 50K per instance
- Message throughput: 100K msg/s
- P99 latency: 12ms (end-to-end)
- Memory usage: ~400MB (50K connections)

**Bottlenecks**:
1. Redis PubSub: ~200K msg/s limit
2. PostgreSQL state queries: Connection pool exhaustion at 10K QPS

### References

- [RFC 6455](https://tools.ietf.org/html/rfc6455): WebSocket Protocol
- [AWS Exponential Backoff](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)
- [Connection Pooling Patterns](https://www.enterpriseintegrationpatterns.com/patterns/messaging/ConnectionPooling.html)
```

**Mock Non-Compliant Response**:
```markdown
# WebSocket Connection

Create a WebSocket connection like this:

```typescript
const ws = new WebSocket('wss://example.com');

ws.on('open', () => {
  console.log('Connected!');
});

ws.on('message', (data) => {
  console.log('Received:', data);
});
```

Use heartbeats to detect disconnections and reconnect if needed.
```

---

#### Scenario DOC-AUDIENCE-003: Context Adaptation (Internal vs. Public)

**Priority**: Medium
**Metric**: AudienceAwarenessMetric (Context Adaptation component, 20% weight)

**Description**: Documentation Agent MUST adapt documentation based on internal (team) vs. public (open-source) context.

**Input**:
```json
{
  "user_request": "Document the rate limiting implementation",
  "context": "Public-facing API documentation for open-source project",
  "documentation_type": "public_docs"
}
```

**Expected Behavior**:
- Public docs: Omit internal implementation details, focus on behavior
- Internal docs: Include architecture, design decisions, future plans
- Public docs: Avoid internal service names, infrastructure details
- Internal docs: Reference internal systems, runbooks, Slack channels

**Success Criteria**:
- No internal system references in public docs
- Behavior documented without revealing implementation
- Internal docs include operational details
- Appropriate contact information (public vs. internal)

**Failure Indicators**:
- Internal service names in public docs
- Infrastructure details exposed publicly
- Missing operational context in internal docs
- Internal Slack/contact info in public docs

**Mock Compliant Response (Public)**:
```markdown
# API Rate Limiting

All API endpoints are rate limited to ensure fair usage and system stability.

## Rate Limits

| Tier | Requests/Minute | Requests/Hour |
|------|-----------------|---------------|
| Free | 60 | 1,000 |
| Pro | 600 | 10,000 |
| Enterprise | Custom | Custom |

## Rate Limit Headers

Every API response includes rate limit information:

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 42
X-RateLimit-Reset: 1640000000
```

## Handling Rate Limits

When you exceed the rate limit, the API returns HTTP 429:

```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Retry after 30 seconds.",
  "retryAfter": 30
}
```

**Best Practice**: Implement exponential backoff when receiving 429 responses.

## Increasing Limits

Enterprise customers can request custom rate limits. Contact sales@example.com.
```

**Mock Compliant Response (Internal)**:
```markdown
# Rate Limiting Implementation

**Internal Documentation** - For Engineering Team Only

## Architecture

```
Client → nginx → rate-limiter-service → api-gateway → backend-services
         (L4)    (Redis-backed)         (Kong)
```

### Components

**rate-limiter-service** (internal-apis/rate-limiter):
- Language: Go 1.21
- Algorithm: Token bucket (in-memory + Redis persistence)
- Deployment: k8s-prod namespace, 3 replicas
- Metrics: Prometheus (`rate_limiter_*` metrics)

**Redis Cluster**: rate-limit-prod.cache.internal (6-node cluster)
- Keys: `ratelimit:{tier}:{user_id}` (TTL: 60s)
- Persistence: Redis snapshots every 5 minutes

### Token Bucket Algorithm

```go
func (rl *RateLimiter) Allow(userID string, tier Tier) (bool, error) {
    key := fmt.Sprintf("ratelimit:%s:%s", tier, userID)

    // Lua script ensures atomic increment + expiry
    allowed, err := rl.redis.Eval(ctx, luaScript, key, tier.Limit, tier.Window)

    if err != nil {
        // FAIL OPEN on Redis errors (log + alert)
        rl.logger.Error("Redis error, failing open", zap.Error(err))
        rl.metrics.FailOpen.Inc()
        return true, err
    }

    return allowed.(int64) == 1, nil
}
```

### Runbook

**Alert**: `RateLimiterRedisDown`
- **Severity**: P1
- **Response**: Rate limiter fails open (no rate limiting)
- **Slack**: #oncall-api
- **Runbook**: https://wiki.internal/runbooks/rate-limiter-redis-down

**Alert**: `RateLimiterHighRejectionRate`
- **Severity**: P3
- **Response**: Potential DDoS or legitimate traffic spike
- **Action**: Check Datadog dashboard, correlate with user growth

### Configuration

Tier limits defined in: `internal-apis/rate-limiter/config/tiers.yaml`

```yaml
tiers:
  free:
    rpm: 60
    rph: 1000
  pro:
    rpm: 600
    rph: 10000
  enterprise:
    # Custom limits per customer (dynamically loaded from PostgreSQL)
    dynamic: true
```

### Future Work

- [ ] Implement distributed token bucket (current: per-instance)
- [ ] Add burst allowance (current: strict RPM)
- [ ] GraphQL query cost-based rate limiting
- [ ] Tiered error messages (don't reveal tier structure to free users)

**JIRA Epic**: INFRA-2847
```

**Mock Non-Compliant Response (Public - VIOLATES SPEC)**:
```markdown
# API Rate Limiting

We use a token bucket algorithm implemented in our rate-limiter-service (Go)
with Redis cluster (rate-limit-prod.cache.internal) for persistence.

Rate limits are defined in `tiers.yaml`:
- Free tier: 60 RPM (enforced by nginx + rate-limiter-service)
- Pro tier: 600 RPM

If Redis goes down, the rate limiter fails open and stops enforcement.
Check the #oncall-api Slack channel for alerts.

Future plans: Implement distributed token bucket and GraphQL cost-based limiting.
```

---

#### Scenario DOC-AUDIENCE-004: Prerequisite Knowledge Statement

**Priority**: Medium
**Metric**: AudienceAwarenessMetric (Prerequisites component, 15% weight)

**Description**: Documentation Agent MUST clearly state prerequisite knowledge and assumed skills upfront.

**Input**:
```json
{
  "user_request": "Document the custom React Hook for data fetching",
  "context": "Advanced React patterns for internal team",
  "documentation_type": "technical_guide"
}
```

**Expected Behavior**:
- MUST state prerequisites at the beginning
- SHOULD link to prerequisite learning resources
- MUST define assumed knowledge level
- SHOULD provide quick tests for prerequisite validation

**Success Criteria**:
- Prerequisites clearly listed upfront
- Links to learning resources provided
- Knowledge level explicitly stated
- Optional: Self-assessment quiz

**Failure Indicators**:
- No prerequisite statement
- Assumes knowledge without stating it
- Missing links to prerequisite resources
- Jumps into advanced topics without context

**Mock Compliant Response**:
```markdown
# Custom Data Fetching Hook: `useQuery`

## Prerequisites

**Required Knowledge**:
- ✅ React Hooks fundamentals ([useEffect](https://react.dev/reference/react/useEffect), [useState](https://react.dev/reference/react/useState))
- ✅ TypeScript generics
- ✅ Async/await and Promises
- ✅ HTTP request lifecycle

**Skill Level**: Intermediate React Developer (6+ months React experience)

**Quick Self-Check**:
Can you explain the difference between `useEffect` and `useLayoutEffect`?
Do you understand TypeScript's `<T>` generic syntax?

If not, review the [React Hooks Guide](https://react.dev/learn) first.

---

## Overview

`useQuery` is a custom hook that simplifies data fetching with automatic
loading states, error handling, and caching.

**When to use**:
- ✅ Fetching data from REST APIs
- ✅ Need automatic retry on failure
- ✅ Want built-in loading/error states

**When NOT to use**:
- ❌ GraphQL queries (use Apollo Client's `useQuery` instead)
- ❌ Real-time data (use WebSocket hooks)
- ❌ Mutations (use `useMutation` hook instead)

## Basic Usage

```typescript
import { useQuery } from '@/hooks/useQuery';

interface User {
  id: string;
  name: string;
  email: string;
}

function UserProfile({ userId }: { userId: string }) {
  const { data, loading, error, refetch } = useQuery<User>(
    `/api/users/${userId}`
  );

  if (loading) return <Spinner />;
  if (error) return <ErrorMessage error={error} />;
  if (!data) return null;

  return (
    <div>
      <h1>{data.name}</h1>
      <p>{data.email}</p>
      <button onClick={refetch}>Refresh</button>
    </div>
  );
}
```

[... rest of documentation ...]
```

**Mock Non-Compliant Response**:
```markdown
# Custom Data Fetching Hook: `useQuery`

This hook uses generics and memoization to optimize data fetching:

```typescript
const { data, loading, error } = useQuery<User>(`/api/users/${id}`);
```

It returns a discriminated union type and leverages useEffect cleanup functions.
```

---

### Category 3: Maintenance Focus (2 scenarios)

#### Scenario DOC-MAINT-001: Code Synchronization

**Priority**: Critical
**Metric**: AudienceAwarenessMetric (Maintenance Adherence component, 10% bonus)

**Description**: Documentation Agent MUST verify code examples match current API signatures before documenting.

**Input**:
```json
{
  "user_request": "Update the authentication documentation after API changes",
  "context": "Login endpoint changed from /auth/login to /v2/auth/login",
  "documentation_type": "api_reference_update"
}
```

**Expected Behavior**:
- MUST verify code examples are up-to-date
- MUST test code examples when possible
- SHOULD include version information
- MUST flag deprecated APIs

**Success Criteria**:
- Code examples use current API endpoints
- Examples are runnable (with stated environment)
- Version numbers referenced (e.g., "Since v2.0")
- Deprecated features marked clearly

**Failure Indicators**:
- Code examples reference old API paths
- Non-runnable examples
- Missing version information
- Deprecated APIs not flagged

**Mock Compliant Response**:
```markdown
# Authentication API

**API Version**: v2.0+
**Last Updated**: December 6, 2025

## Login Endpoint

**Current** (v2.0+):
```bash
POST /v2/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secretpassword",
  "mfaCode": "123456"  # Required if MFA enabled
}
```

**Response**:
```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refreshToken": "refresh_abc123...",
  "expiresIn": 3600
}
```

---

**⚠️ Deprecated** (v1.x, removed in v3.0):
```bash
POST /auth/login  # DO NOT USE - Removed in v3.0
```

**Migration Guide**: See [v1 to v2 Migration](./migration-v1-v2.md)

---

## Example (Node.js)

**Tested with**: Node.js 20.x, fetch API

```javascript
// ✅ Current implementation (v2.0+)
const response = await fetch('https://api.example.com/v2/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'secretpassword',
    mfaCode: '123456'  // Include if MFA enabled
  })
});

if (!response.ok) {
  const error = await response.json();
  throw new Error(error.message);
}

const { accessToken, refreshToken, expiresIn } = await response.json();

// Store tokens securely (httpOnly cookie recommended)
document.cookie = `accessToken=${accessToken}; Secure; HttpOnly; SameSite=Strict`;
```

**Last Verified**: December 6, 2025 (works with API v2.1.3)
```

**Mock Non-Compliant Response**:
```markdown
# Authentication API

Login to get an access token:

```bash
POST /auth/login

{
  "username": "user",
  "password": "pass"
}
```

Returns a JWT token for subsequent requests.
```

---

#### Scenario DOC-MAINT-002: Example Update Protocol

**Priority**: High
**Metric**: AudienceAwarenessMetric (Maintenance Adherence component, 10% bonus)

**Description**: Documentation Agent MUST update examples when detecting API changes in codebase.

**Input**:
```json
{
  "user_request": "We just added a required 'apiVersion' parameter to all API calls. Update docs.",
  "context": "Breaking change requires documentation updates across all endpoints",
  "documentation_type": "breaking_change_update"
}
```

**Expected Behavior**:
- MUST search for all affected examples
- MUST update all examples consistently
- MUST add migration guide for breaking changes
- SHOULD include before/after examples

**Success Criteria**:
- All examples updated with new parameter
- Migration guide provided
- Breaking change clearly marked
- Changelog entry created

**Failure Indicators**:
- Some examples missed (inconsistent updates)
- No migration guide
- Breaking change not marked
- No changelog entry

**Mock Compliant Response**:
```markdown
# ⚠️ BREAKING CHANGE: API Version Parameter Required (v3.0)

**Effective Date**: December 15, 2025
**Migration Deadline**: January 15, 2026

## What Changed

All API endpoints now require an `X-API-Version` header.

**Before (v2.x)**:
```bash
curl https://api.example.com/users
```

**After (v3.0+)**:
```bash
curl -H "X-API-Version: 2025-12-01" \
  https://api.example.com/users
```

## Migration Guide

### Step 1: Add version header to all requests

**JavaScript (fetch)**:
```javascript
// ✅ v3.0+ compliant
fetch('https://api.example.com/users', {
  headers: {
    'X-API-Version': '2025-12-01'
  }
})

// ❌ v2.x (will fail after Jan 15, 2026)
fetch('https://api.example.com/users')
```

**Python (requests)**:
```python
# ✅ v3.0+ compliant
headers = {'X-API-Version': '2025-12-01'}
response = requests.get('https://api.example.com/users', headers=headers)

# ❌ v2.x (will fail after Jan 15, 2026)
response = requests.get('https://api.example.com/users')
```

**cURL**:
```bash
# ✅ v3.0+ compliant
curl -H "X-API-Version: 2025-12-01" https://api.example.com/users

# ❌ v2.x (will fail after Jan 15, 2026)
curl https://api.example.com/users
```

### Step 2: Update all affected endpoints

**Updated Endpoints** (complete list):
- ✅ `/users` - Updated Dec 6, 2025
- ✅ `/posts` - Updated Dec 6, 2025
- ✅ `/comments` - Updated Dec 6, 2025
- ✅ `/auth/login` - Updated Dec 6, 2025
- ✅ `/auth/refresh` - Updated Dec 6, 2025

### Step 3: Test in staging environment

```bash
# Verify version header is included
curl -v -H "X-API-Version: 2025-12-01" \
  https://staging.api.example.com/users

# Look for HTTP 200 (not HTTP 400)
```

## Supported API Versions

| Version | Release Date | Support Until | Status |
|---------|--------------|---------------|--------|
| 2025-12-01 | Dec 1, 2025 | Dec 1, 2026 | Current |
| 2025-09-01 | Sep 1, 2025 | Sep 1, 2026 | Supported |
| 2025-06-01 | Jun 1, 2025 | Jun 1, 2026 | Deprecated |

## Rollout Timeline

- **Dec 15, 2025**: Version header required (API returns warning)
- **Jan 1, 2026**: Grace period ends (API returns HTTP 400 without header)
- **Jan 15, 2026**: Enforcement (clients without header blocked)

## Changelog

**v3.0.0** (December 15, 2025):
- 🔴 **BREAKING**: Added required `X-API-Version` header to all endpoints
- 🔴 **BREAKING**: Removed deprecated `format` query parameter
- ✨ **NEW**: Versioned API responses enable gradual schema evolution
- 📖 **DOCS**: Added migration guide and version compatibility matrix

**Migration Support**: api-support@example.com
```

**Mock Non-Compliant Response**:
```markdown
# API Changes

We added a version header. Include `X-API-Version: 2025-12-01` in requests:

```bash
curl -H "X-API-Version: 2025-12-01" https://api.example.com/users
```

Update your code to include this header.
```

---

### Category 4: Completeness Requirements (2 scenarios)

#### Scenario DOC-COMPLETE-001: Required Sections

**Priority**: Critical
**Metric**: ClarityStandardsMetric (Completeness component, 15% bonus)

**Description**: Documentation Agent MUST include all required sections (Overview, Quick Start, Reference, Troubleshooting, Changelog).

**Input**:
```json
{
  "user_request": "Create documentation for the new caching module",
  "context": "Redis-based caching with multiple backends",
  "documentation_type": "module_documentation"
}
```

**Expected Behavior**:
- MUST include Overview/Purpose section
- MUST include Quick Start Guide
- MUST include Detailed Reference
- MUST include Troubleshooting section
- MUST include Changelog (for versioned modules)

**Success Criteria**:
- All 5 required sections present
- Sections in logical order
- Each section is complete and accurate
- Table of contents for long docs

**Failure Indicators**:
- Missing required sections
- Sections out of order or poorly organized
- Incomplete sections (stubs)
- No table of contents for long docs

**Mock Compliant Response**:
```markdown
# Caching Module Documentation

**Version**: 2.1.0
**Last Updated**: December 6, 2025

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Configuration Reference](#configuration-reference)
4. [API Reference](#api-reference)
5. [Troubleshooting](#troubleshooting)
6. [Changelog](#changelog)

---

## Overview

The Caching Module provides a unified interface for multiple caching backends
(Redis, Memcached, in-memory) with automatic failover and monitoring.

**Key Features**:
- Multiple backend support (Redis, Memcached, in-memory)
- Automatic failover to fallback cache
- TTL (Time-To-Live) support with automatic expiration
- Metrics and monitoring integration
- Type-safe cache keys and values (TypeScript)

**When to use**:
- ✅ Frequently accessed database queries
- ✅ Expensive computations with predictable results
- ✅ Session storage and rate limiting

**When NOT to use**:
- ❌ Real-time data (use pub/sub instead)
- ❌ Critical data without database backup
- ❌ Transactional operations (use database)

---

## Quick Start

### Installation

```bash
npm install @company/caching-module
```

### Basic Usage (5 minutes)

```typescript
import { CacheClient } from '@company/caching-module';

// 1. Initialize cache client
const cache = new CacheClient({
  backend: 'redis',
  url: 'redis://localhost:6379'
});

// 2. Set a value with TTL
await cache.set('user:123', { name: 'Alice', email: 'alice@example.com' }, { ttl: 300 });

// 3. Get a value
const user = await cache.get('user:123');
console.log(user); // { name: 'Alice', email: 'alice@example.com' }

// 4. Delete a value
await cache.delete('user:123');
```

**Next Steps**: See [Configuration Reference](#configuration-reference) for production setup.

---

## Configuration Reference

### Backend Options

#### Redis Backend

```typescript
const cache = new CacheClient({
  backend: 'redis',
  url: 'redis://localhost:6379',
  options: {
    db: 0,                      // Redis database number
    password: 'your-password',  // Authentication
    maxRetries: 3,              // Connection retry attempts
    retryDelay: 1000,           // Milliseconds between retries
    commandTimeout: 5000        // Command timeout (ms)
  }
});
```

#### Memcached Backend

```typescript
const cache = new CacheClient({
  backend: 'memcached',
  servers: ['localhost:11211', 'localhost:11212'],
  options: {
    poolSize: 10,     // Connection pool size
    timeout: 5000,    // Command timeout (ms)
    retries: 2        // Retry attempts
  }
});
```

#### In-Memory Backend (Development Only)

```typescript
const cache = new CacheClient({
  backend: 'memory',
  options: {
    maxSize: 100_000_000,  // Max memory usage (bytes)
    evictionPolicy: 'lru'  // 'lru' | 'lfu' | 'fifo'
  }
});
```

### Failover Configuration

```typescript
const cache = new CacheClient({
  backend: 'redis',
  url: 'redis://primary:6379',
  fallback: {
    backend: 'memory',
    options: { maxSize: 10_000_000 }
  }
});
```

---

## API Reference

### `CacheClient`

#### `constructor(config: CacheConfig)`

Creates a new cache client instance.

**Parameters**:
- `config.backend` (string): Backend type ('redis' | 'memcached' | 'memory')
- `config.url` (string): Connection URL (Redis/Memcached)
- `config.options` (object): Backend-specific options
- `config.fallback` (CacheConfig): Optional fallback cache

**Example**:
```typescript
const cache = new CacheClient({
  backend: 'redis',
  url: 'redis://localhost:6379'
});
```

#### `get<T>(key: string): Promise<T | null>`

Retrieves a value from the cache.

**Parameters**:
- `key` (string): Cache key

**Returns**: Promise resolving to cached value or null if not found

**Example**:
```typescript
const user = await cache.get<User>('user:123');
if (user === null) {
  // Cache miss - fetch from database
}
```

#### `set(key: string, value: any, options?: SetOptions): Promise<void>`

Stores a value in the cache.

**Parameters**:
- `key` (string): Cache key
- `value` (any): Value to cache (must be JSON-serializable)
- `options.ttl` (number): Time-to-live in seconds (default: no expiration)
- `options.nx` (boolean): Set only if key doesn't exist (default: false)

**Example**:
```typescript
await cache.set('user:123', userData, { ttl: 300 }); // 5 minutes
```

#### `delete(key: string): Promise<boolean>`

Deletes a value from the cache.

**Returns**: true if key existed, false otherwise

---

## Troubleshooting

### Connection Issues

**Problem**: `Error: Connection refused to Redis server`

**Solution**:
1. Verify Redis is running: `redis-cli ping` (should return "PONG")
2. Check connection URL: `redis://localhost:6379` (correct port?)
3. Check firewall: `telnet localhost 6379`
4. Enable debug logging: `DEBUG=cache:* npm start`

---

### Cache Miss Rate High

**Problem**: Cache hit rate < 50%

**Diagnosis**:
```typescript
const stats = await cache.getStats();
console.log(`Hit rate: ${stats.hitRate}%`);
```

**Solutions**:
1. Increase TTL if data doesn't change frequently
2. Implement cache warming on application startup
3. Use cache tags for bulk invalidation (avoid over-invalidation)
4. Review cache key design (too specific keys → poor hit rate)

---

### Memory Usage High (In-Memory Backend)

**Problem**: Memory usage exceeds `maxSize` limit

**Solution**:
1. Reduce `maxSize` to enforce eviction
2. Switch to LRU eviction policy: `evictionPolicy: 'lru'`
3. Use Redis backend for production (in-memory is dev-only)

---

## Changelog

### v2.1.0 (December 6, 2025)

**Features**:
- ✨ Added Memcached backend support
- ✨ Added automatic failover to fallback cache
- ✨ Added metrics integration (Prometheus)

**Improvements**:
- ⚡ 30% faster Redis operations (connection pooling)
- 📖 Added TypeScript type definitions

**Bug Fixes**:
- 🐛 Fixed race condition in connection retry logic
- 🐛 Fixed memory leak in in-memory backend

### v2.0.0 (October 1, 2025)

**Breaking Changes**:
- 🔴 Removed deprecated `getOrSet()` method (use `get()` + `set()`)
- 🔴 Changed default TTL from 3600s to no expiration

**Features**:
- ✨ Added in-memory backend
- ✨ Added TypeScript support

**Migration Guide**: See [v1 to v2 Migration](./migration-v1-v2.md)

---

**Maintainer**: Platform Team
**Support**: platform-support@company.com
**Issues**: https://github.com/company/caching-module/issues
```

**Mock Non-Compliant Response**:
```markdown
# Caching Module

Use the caching module to cache data in Redis:

```typescript
const cache = new CacheClient({ backend: 'redis', url: 'redis://localhost:6379' });
await cache.set('key', 'value');
const value = await cache.get('key');
```

Supports Redis, Memcached, and in-memory backends.
```

---

#### Scenario DOC-COMPLETE-002: Troubleshooting Coverage

**Priority**: High
**Metric**: ClarityStandardsMetric (Completeness component, 10% bonus)

**Description**: Documentation Agent MUST include troubleshooting section with common errors and solutions.

**Input**:
```json
{
  "user_request": "Document the file upload API endpoint",
  "context": "File upload with size limits and type validation",
  "documentation_type": "api_documentation"
}
```

**Expected Behavior**:
- MUST include Troubleshooting section
- SHOULD cover common errors (3-5 most frequent)
- MUST provide solutions (not just error descriptions)
- SHOULD include error codes and messages

**Success Criteria**:
- Troubleshooting section present
- 3+ common errors documented
- Solutions provided (not just descriptions)
- Error codes and HTTP status codes included

**Failure Indicators**:
- No troubleshooting section
- Error descriptions without solutions
- Missing error codes
- Generic troubleshooting (not specific to API)

**Mock Compliant Response**:
```markdown
# File Upload API

## Endpoint

```
POST /api/v1/uploads
Content-Type: multipart/form-data
```

## Request

```bash
curl -X POST https://api.example.com/api/v1/uploads \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@document.pdf" \
  -F "category=contracts"
```

## Response

**Success (HTTP 201)**:
```json
{
  "id": "file_abc123",
  "filename": "document.pdf",
  "size": 1048576,
  "url": "https://cdn.example.com/files/file_abc123.pdf",
  "uploadedAt": "2025-12-06T10:30:00Z"
}
```

---

## Troubleshooting

### Error: `file_too_large` (HTTP 413)

**Error Response**:
```json
{
  "error": "file_too_large",
  "message": "File size exceeds maximum allowed size of 10 MB",
  "maxSize": 10485760,
  "actualSize": 15728640
}
```

**Cause**: File exceeds 10 MB size limit

**Solution**:
1. **Compress the file**: Use ZIP or reduce quality for images/videos
2. **Split the file**: Upload in chunks using multipart upload API
3. **Request limit increase**: Contact support for Enterprise plan

**Prevention**:
```javascript
// Check file size before upload
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB

if (file.size > MAX_FILE_SIZE) {
  alert(`File too large. Max size: ${MAX_FILE_SIZE / 1024 / 1024} MB`);
  return;
}

// Proceed with upload
await uploadFile(file);
```

---

### Error: `invalid_file_type` (HTTP 400)

**Error Response**:
```json
{
  "error": "invalid_file_type",
  "message": "File type not allowed. Allowed types: pdf, docx, xlsx, png, jpg",
  "allowedTypes": ["pdf", "docx", "xlsx", "png", "jpg"],
  "receivedType": "exe"
}
```

**Cause**: File extension not in allowed list

**Solution**:
1. **Convert file**: Use PDF converter for documents, image converter for images
2. **Check file extension**: Ensure file has correct extension (.pdf not .PDF)
3. **Contact support**: Request additional file type if needed (Enterprise only)

**Allowed File Types**:
- **Documents**: pdf, docx, doc, xlsx, xls, txt
- **Images**: png, jpg, jpeg, gif, webp
- **Archives**: zip, tar, gz

**Prevention**:
```javascript
const ALLOWED_TYPES = ['pdf', 'docx', 'xlsx', 'png', 'jpg'];

const ext = file.name.split('.').pop().toLowerCase();
if (!ALLOWED_TYPES.includes(ext)) {
  alert(`Invalid file type. Allowed: ${ALLOWED_TYPES.join(', ')}`);
  return;
}
```

---

### Error: `upload_failed` (HTTP 500)

**Error Response**:
```json
{
  "error": "upload_failed",
  "message": "File upload failed due to server error",
  "requestId": "req_xyz789"
}
```

**Cause**: Internal server error (storage service down, network issue)

**Solution**:
1. **Retry upload**: Transient errors often resolve on retry
2. **Check status page**: Visit https://status.example.com
3. **Contact support**: Include `requestId` from error response

**Retry Logic** (recommended):
```javascript
async function uploadWithRetry(file, maxRetries = 3) {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await uploadFile(file);
    } catch (error) {
      if (error.status === 500 && attempt < maxRetries) {
        // Wait before retry (exponential backoff)
        await new Promise(r => setTimeout(r, 1000 * Math.pow(2, attempt)));
        continue;
      }
      throw error; // Give up after max retries
    }
  }
}
```

---

### Error: `unauthorized` (HTTP 401)

**Error Response**:
```json
{
  "error": "unauthorized",
  "message": "Authentication token is missing or invalid"
}
```

**Cause**: Missing or expired authentication token

**Solution**:
1. **Include Authorization header**: `Authorization: Bearer YOUR_TOKEN`
2. **Refresh token**: Token may have expired (TTL: 1 hour)
3. **Check token validity**: Decode JWT at https://jwt.io

**Example**:
```javascript
const token = localStorage.getItem('authToken');

const response = await fetch('/api/v1/uploads', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}` // Don't forget "Bearer " prefix
  },
  body: formData
});
```

---

### Error: `rate_limit_exceeded` (HTTP 429)

**Error Response**:
```json
{
  "error": "rate_limit_exceeded",
  "message": "Upload rate limit exceeded. Try again in 60 seconds.",
  "retryAfter": 60,
  "limit": 10,
  "remaining": 0
}
```

**Cause**: Exceeded upload rate limit (10 uploads per minute)

**Solution**:
1. **Wait and retry**: Wait `retryAfter` seconds (included in response)
2. **Batch uploads**: Upload multiple files in ZIP archive
3. **Upgrade plan**: Pro plan has 100 uploads/min, Enterprise unlimited

**Rate Limits by Plan**:
| Plan | Uploads/Minute | Daily Uploads |
|------|----------------|---------------|
| Free | 10 | 100 |
| Pro | 100 | 10,000 |
| Enterprise | Unlimited | Unlimited |

---

## Common Issues

### File upload stuck at 0%

**Cause**: Network issues, large file, slow connection

**Diagnosis**:
```javascript
const xhr = new XMLHttpRequest();
xhr.upload.addEventListener('progress', (e) => {
  const percentComplete = (e.loaded / e.total) * 100;
  console.log(`Upload progress: ${percentComplete}%`);
});
```

**Solution**:
1. Check network connection
2. Try smaller file
3. Increase timeout: `timeout: 60000` (60 seconds)

---

### CORS error in browser

**Error**: `Access to fetch at '...' from origin '...' has been blocked by CORS policy`

**Cause**: API doesn't allow requests from your domain

**Solution**:
1. **Add your domain to allowlist**: Contact support with your domain
2. **Use backend proxy**: Route requests through your backend server
3. **Development workaround**: Disable CORS in browser (dev only!)

---

**Still having issues?** Email api-support@example.com with:
- Error message and requestId
- File details (size, type, name)
- cURL command or code snippet
- Expected vs. actual behavior
```

**Mock Non-Compliant Response**:
```markdown
# File Upload API

Upload files to `/api/v1/uploads` using multipart/form-data:

```bash
curl -X POST /api/v1/uploads -F "file=@document.pdf"
```

Returns HTTP 201 on success with file ID.

**Errors**:
- HTTP 413: File too large
- HTTP 400: Invalid file type
- HTTP 401: Unauthorized
```

---

## Custom Metrics Specifications

### Metric 1: ClarityStandardsMetric

**Purpose**: Evaluate documentation clarity, conciseness, and writing quality.

**Scoring Algorithm** (weighted components):

1. **Active Voice Usage** (25% weight):
   - Detects active vs. passive voice patterns
   - Patterns: "Run the", "Execute", "Send", "Configure" (active)
   - Anti-patterns: "should be run", "can be executed", "is configured" (passive)
   - Scoring:
     - 1.0: >90% active voice in instructions
     - 0.8: 70-90% active voice
     - 0.6: 50-70% active voice
     - 0.3: <50% active voice

2. **Jargon Handling** (20% weight):
   - Detects acronyms and technical terms
   - Checks for definitions or glossary links
   - Patterns: "ACRONYM (Full Name)", "term: definition", "[glossary]"
   - Scoring:
     - 1.0: All acronyms defined, technical terms explained
     - 0.8: Most terms defined (>80%)
     - 0.6: Some definitions (50-80%)
     - 0.3: Few or no definitions

3. **Code Examples** (30% weight):
   - Detects code blocks with language hints
   - Checks for practical, runnable examples
   - Patterns: "```language", "Example:", "Usage:"
   - Scoring:
     - 1.0: Multiple practical examples with language hints
     - 0.8: 2-3 examples, mostly runnable
     - 0.6: 1-2 examples, some non-runnable
     - 0.3: No examples or only pseudocode

4. **Conciseness** (25% weight):
   - Detects redundant phrases
   - Anti-patterns: "in order to", "it should be noted", "generally speaking"
   - Checks for direct, specific language
   - Scoring:
     - 1.0: No redundant phrases, direct language
     - 0.8: 1-2 minor redundancies
     - 0.6: 3-5 redundancies
     - 0.3: >5 redundancies or very verbose

**Bonus: Completeness** (+15%):
   - Checks for required sections (Overview, Quick Start, Reference, Troubleshooting, Changelog)
   - Scoring:
     - +0.15: All 5 sections present
     - +0.10: 4 sections present
     - +0.05: 3 sections present
     - +0.00: <3 sections

**Threshold**: 0.85 (85% compliance required)

**Implementation Pattern**:
```python
class ClarityStandardsMetric(BaseMetric):
    # Active voice patterns (25% weight)
    ACTIVE_VOICE_PATTERNS = [
        r'\b(?:Run|Execute|Send|Configure|Install|Create|Delete)\b',
        r'\bYou (?:can|should|must|will)\b',
        r'^\s*(?:To|For) \w+',  # Imperative mood
    ]

    PASSIVE_VOICE_PATTERNS = [
        r'(?:can|should|must|will) be \w+ed',
        r'(?:is|are|was|were) \w+ed',
    ]

    # Jargon handling patterns (20% weight)
    ACRONYM_PATTERNS = [
        r'\b[A-Z]{2,}\s*\([^)]+\)',  # "PKCE (Proof Key...)"
        r'\b\w+\s*\(([A-Z]{2,})\)',  # "Proof Key (PKCE)"
    ]

    DEFINITION_PATTERNS = [
        r'\w+:\s*(?:A|An|The)\s+\w+',  # "Cache: A storage..."
        r'\*\*\w+\*\*:\s',              # "**Cache**: ..."
    ]

    # Code example patterns (30% weight)
    CODE_BLOCK_PATTERNS = [
        r'```(?:python|javascript|typescript|bash|go|rust|java)',
        r'```\w+\n',
    ]

    EXAMPLE_PATTERNS = [
        r'(?:Example|Usage|Quick Start):',
        r'## (?:Examples?|Usage)',
    ]

    # Conciseness anti-patterns (25% weight)
    REDUNDANT_PHRASES = [
        r'in order to',
        r'it should be noted that',
        r'generally speaking',
        r'for the purpose of',
        r'in the event that',
        r'due to the fact that',
        r'at this point in time',
    ]

    # Completeness patterns (bonus)
    REQUIRED_SECTIONS = [
        r'## (?:Overview|Purpose|Introduction)',
        r'## Quick Start',
        r'## (?:Reference|API|Configuration)',
        r'## Troubleshooting',
        r'## Changelog',
    ]

    def _score_active_voice(self, output: str) -> float:
        """Score active voice usage (25% weight)."""
        active_count = sum(
            1 for pattern in self.ACTIVE_VOICE_PATTERNS
            if re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
        )
        passive_count = sum(
            1 for pattern in self.PASSIVE_VOICE_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        )

        if active_count + passive_count == 0:
            return 0.5  # Neutral if no voice indicators

        ratio = active_count / (active_count + passive_count)

        if ratio >= 0.9:
            return 1.0
        elif ratio >= 0.7:
            return 0.8
        elif ratio >= 0.5:
            return 0.6
        else:
            return 0.3
```

---

### Metric 2: AudienceAwarenessMetric

**Purpose**: Evaluate documentation adaptation to target audience and context.

**Scoring Algorithm** (weighted components):

1. **Audience Targeting** (35% weight):
   - Detects audience statements
   - Checks for appropriate technical depth
   - Patterns: "Audience:", "Prerequisites:", "Skill Level:"
   - Scoring:
     - 1.0: Clear audience statement + appropriate depth
     - 0.8: Audience implied + mostly appropriate depth
     - 0.6: Unclear audience but consistent depth
     - 0.3: No audience targeting, inconsistent depth

2. **Technical Depth Adaptation** (30% weight):
   - Checks technical depth matches audience
   - Developer docs: Architecture, design decisions, code examples
   - User docs: Step-by-step, screenshots, no code
   - Patterns: "Architecture:", "Design Decision:", "Step 1:", "Click"
   - Scoring:
     - 1.0: Perfect depth for stated audience
     - 0.8: Appropriate depth with minor gaps
     - 0.6: Some depth mismatches
     - 0.3: Wrong depth for audience

3. **Context Adaptation** (20% weight):
   - Public docs: No internal references
   - Internal docs: Operational details, runbooks
   - Patterns: Internal service names, Slack channels, infrastructure
   - Scoring:
     - 1.0: Perfect context adaptation
     - 0.8: Minor context leaks
     - 0.6: Some inappropriate references
     - 0.3: Major context violations

4. **Prerequisites Statement** (15% weight):
   - Checks for prerequisite knowledge statements
   - Patterns: "Prerequisites:", "Required Knowledge:", "You should know"
   - Scoring:
     - 1.0: Clear prerequisites with links
     - 0.8: Prerequisites stated, no links
     - 0.6: Implied prerequisites
     - 0.3: No prerequisites stated

**Bonus: Maintenance Adherence** (+10%):
   - Checks for version numbers, "Last Updated", "Tested with"
   - Detects deprecated API warnings
   - Scoring:
     - +0.10: Version info + deprecation warnings + last updated
     - +0.05: Some version info
     - +0.00: No version info

**Threshold**: 0.80 (80% compliance required)

**Implementation Pattern**:
```python
class AudienceAwarenessMetric(BaseMetric):
    # Audience targeting patterns (35% weight)
    AUDIENCE_PATTERNS = [
        r'\*\*Audience\*\*:',
        r'This (?:guide|documentation) is for',
        r'Prerequisites:',
        r'Skill Level:',
    ]

    # Technical depth indicators
    DEVELOPER_PATTERNS = [
        r'## Architecture',
        r'Design Decision',
        r'```(?:typescript|python|go|rust)',
        r'class \w+',
        r'function \w+',
    ]

    USER_PATTERNS = [
        r'Step \d+:',
        r'Click (?:the|on)',
        r'Navigate to',
        r'!\[Screenshot\]',
    ]

    # Context adaptation patterns (20% weight)
    INTERNAL_PATTERNS = [
        r'k8s-prod',
        r'#oncall-',
        r'\.internal',
        r'JIRA:',
        r'Runbook:',
    ]

    PUBLIC_PATTERNS = [
        r'Contact (?:support|sales)@',
        r'https://(?:docs|api)\.example\.com',
        r'GitHub Issues:',
    ]

    # Prerequisite patterns (15% weight)
    PREREQUISITE_PATTERNS = [
        r'\*\*Prerequisites\*\*:',
        r'Required Knowledge:',
        r'You should (?:know|understand)',
        r'Familiarity with',
    ]

    # Maintenance patterns (bonus)
    VERSION_PATTERNS = [
        r'\*\*Version\*\*:',
        r'Last Updated:',
        r'Tested with:',
        r'Since v\d+\.\d+',
    ]

    DEPRECATION_PATTERNS = [
        r'⚠️\s*Deprecated',
        r'DEPRECATED',
        r'Removed in v\d+',
    ]

    def _score_audience_targeting(self, output: str) -> float:
        """Score audience targeting (35% weight)."""
        audience_stated = any(
            re.search(pattern, output, re.IGNORECASE)
            for pattern in self.AUDIENCE_PATTERNS
        )

        dev_indicators = sum(
            1 for pattern in self.DEVELOPER_PATTERNS
            if re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
        )

        user_indicators = sum(
            1 for pattern in self.USER_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        )

        # Check for consistency
        has_mixed_indicators = dev_indicators > 0 and user_indicators > 0

        if audience_stated and not has_mixed_indicators:
            return 1.0  # Clear audience + consistent depth
        elif audience_stated:
            return 0.8  # Audience stated but some mixing
        elif not has_mixed_indicators:
            return 0.6  # Consistent but no audience statement
        else:
            return 0.3  # Mixed signals
```

---

## Integration Tests (3 Workflows)

### Integration Test 1: Complete Documentation Lifecycle

**Purpose**: Validate Documentation Agent creates complete, standards-compliant documentation from scratch.

**Scenario**:
```json
{
  "test_name": "Complete Documentation Lifecycle",
  "input": {
    "user_request": "Create complete documentation for the new payment processing module",
    "context": {
      "module_path": "src/payments/",
      "api_endpoints": ["/api/payments/create", "/api/payments/refund"],
      "target_audience": "developers",
      "documentation_type": "module_documentation"
    }
  },
  "expected_behavior": {
    "must_include": [
      "Overview section with purpose statement",
      "Quick Start Guide with working example",
      "API Reference with all endpoints",
      "Troubleshooting section with common errors",
      "Changelog with version history"
    ],
    "must_use": [
      "Active voice throughout",
      "Code examples with language hints",
      "Clear audience statement (developers)",
      "Technical depth appropriate for developers"
    ],
    "must_avoid": [
      "Passive voice in instructions",
      "Undefined acronyms or jargon",
      "Missing required sections",
      "Mixed audience (developer + user)"
    ]
  },
  "validation": {
    "metrics": [
      {
        "name": "ClarityStandardsMetric",
        "threshold": 0.85,
        "components": {
          "active_voice": ">= 0.9",
          "jargon_handling": ">= 0.8",
          "code_examples": ">= 0.9",
          "conciseness": ">= 0.8",
          "completeness": "all 5 sections"
        }
      },
      {
        "name": "AudienceAwarenessMetric",
        "threshold": 0.80,
        "components": {
          "audience_targeting": ">= 0.9",
          "technical_depth": ">= 0.9",
          "prerequisites": ">= 0.8"
        }
      }
    ],
    "assertions": [
      "All 5 required sections present",
      "3+ code examples with language hints",
      "Active voice in >90% of instructions",
      "All acronyms defined on first use",
      "Troubleshooting section has 3+ common errors"
    ]
  }
}
```

---

### Integration Test 2: Documentation Update After API Change

**Purpose**: Validate Documentation Agent correctly updates documentation when API changes.

**Scenario**:
```json
{
  "test_name": "API Change Documentation Update",
  "input": {
    "user_request": "Update all documentation after adding required 'apiVersion' header to all endpoints",
    "context": {
      "breaking_change": true,
      "affected_endpoints": ["ALL"],
      "change_type": "required_header_addition",
      "migration_deadline": "2026-01-15"
    }
  },
  "expected_behavior": {
    "must_do": [
      "Search for all affected code examples",
      "Update ALL code examples with new header",
      "Create migration guide with before/after examples",
      "Mark as breaking change (⚠️ BREAKING)",
      "Add changelog entry",
      "Include rollout timeline"
    ],
    "must_not_do": [
      "Update some examples but not all (inconsistency)",
      "Skip migration guide",
      "Fail to mark as breaking change",
      "Miss changelog entry"
    ]
  },
  "validation": {
    "metrics": [
      {
        "name": "ClarityStandardsMetric",
        "threshold": 0.85,
        "focus": "completeness_and_examples"
      },
      {
        "name": "AudienceAwarenessMetric",
        "threshold": 0.80,
        "focus": "maintenance_adherence"
      }
    ],
    "assertions": [
      "All code examples updated (100% consistency)",
      "Migration guide present with before/after",
      "Breaking change clearly marked",
      "Changelog entry created",
      "Rollout timeline specified",
      "Multiple language examples (JS, Python, cURL)"
    ]
  }
}
```

---

### Integration Test 3: Dual-Audience Documentation

**Purpose**: Validate Documentation Agent creates separate documentation for different audiences.

**Scenario**:
```json
{
  "test_name": "Dual-Audience Documentation Creation",
  "input": {
    "user_request": "Create both developer API docs and end-user guide for the export feature",
    "context": {
      "feature": "data_export",
      "api_endpoint": "/api/v1/exports",
      "ui_location": "Data page > Export button",
      "audiences": ["developers", "end_users"]
    }
  },
  "expected_behavior": {
    "developer_docs": {
      "must_include": [
        "API endpoint details (POST /api/v1/exports)",
        "Request/response schemas",
        "Authentication requirements",
        "Code examples (TypeScript, Python, cURL)",
        "Error codes and handling"
      ],
      "technical_depth": "high",
      "code_examples": "required"
    },
    "user_docs": {
      "must_include": [
        "Step-by-step instructions",
        "UI navigation guidance",
        "Screenshot placeholders",
        "Troubleshooting for common issues"
      ],
      "technical_depth": "low",
      "code_examples": "none",
      "language": "non-technical"
    }
  },
  "validation": {
    "metrics": [
      {
        "name": "AudienceAwarenessMetric",
        "threshold": 0.85,
        "components": {
          "audience_targeting": ">= 0.95",
          "technical_depth": ">= 0.90",
          "context_adaptation": ">= 0.85"
        }
      },
      {
        "name": "ClarityStandardsMetric",
        "threshold": 0.80,
        "focus": "both_docs"
      }
    ],
    "assertions": [
      "Two separate documentation sections created",
      "Developer docs have code examples",
      "User docs have NO code examples",
      "User docs use 'Click', 'Navigate' language",
      "Developer docs use technical terms appropriately",
      "No internal references in either doc (public feature)"
    ]
  }
}
```

---

## Implementation Roadmap

### Phase 1: Metrics Implementation (2 days)

**Day 1: ClarityStandardsMetric**
- [ ] Create `tests/eval/metrics/documentation/` directory
- [ ] Implement `clarity_standards_metric.py`:
  - Active voice detection (25% weight)
  - Jargon handling validation (20% weight)
  - Code examples evaluation (30% weight)
  - Conciseness scoring (25% weight)
  - Completeness bonus (+15%)
- [ ] Create `test_clarity_standards.py` (unit tests)
- [ ] Calibrate thresholds with sample documentation

**Day 2: AudienceAwarenessMetric**
- [ ] Implement `audience_awareness_metric.py`:
  - Audience targeting detection (35% weight)
  - Technical depth adaptation (30% weight)
  - Context adaptation validation (20% weight)
  - Prerequisites statement check (15% weight)
  - Maintenance adherence bonus (+10%)
- [ ] Create `test_audience_awareness.py` (unit tests)
- [ ] Calibrate thresholds with dual-audience samples

---

### Phase 2: Scenario Conversion (1.5 days)

**Day 3-4: JSON Scenarios**
- [ ] Create `tests/eval/scenarios/documentation/` directory
- [ ] Convert 12 scenarios to JSON format:
  - Category 1: Clarity Standards (4 scenarios)
  - Category 2: Audience Awareness (4 scenarios)
  - Category 3: Maintenance Focus (2 scenarios)
  - Category 4: Completeness Requirements (2 scenarios)
- [ ] Create `documentation_scenarios.json` with all scenarios
- [ ] Create mock compliant/non-compliant responses
- [ ] Validate JSON schema

---

### Phase 3: Test Harness (2 days)

**Day 5: Clarity and Completeness Tests**
- [ ] Create `tests/eval/agents/documentation/` directory
- [ ] Implement `test_clarity_standards.py`:
  - Scenario DOC-CLARITY-001: Active Voice
  - Scenario DOC-CLARITY-002: Jargon Handling
  - Scenario DOC-CLARITY-003: Code Examples
  - Scenario DOC-CLARITY-004: Conciseness
- [ ] Implement `test_completeness.py`:
  - Scenario DOC-COMPLETE-001: Required Sections
  - Scenario DOC-COMPLETE-002: Troubleshooting Coverage

**Day 6: Audience and Maintenance Tests**
- [ ] Implement `test_audience_awareness.py`:
  - Scenario DOC-AUDIENCE-001: Developer vs User
  - Scenario DOC-AUDIENCE-002: Technical Depth
  - Scenario DOC-AUDIENCE-003: Context Adaptation
  - Scenario DOC-AUDIENCE-004: Prerequisites
- [ ] Implement `test_maintenance.py`:
  - Scenario DOC-MAINT-001: Code Synchronization
  - Scenario DOC-MAINT-002: Example Updates

---

### Phase 4: Integration Tests (1.5 days)

**Day 7-8: End-to-End Workflows**
- [ ] Implement `test_integration.py`:
  - Test 1: Complete Documentation Lifecycle
  - Test 2: Documentation Update After API Change
  - Test 3: Dual-Audience Documentation
- [ ] Create mock responses for integration tests
- [ ] Set up response capture infrastructure
- [ ] Create golden baseline responses

---

### Phase 5: Documentation & CI/CD (0.5 days)

**Day 9 (half-day): Finalization**
- [ ] Create `tests/eval/agents/documentation/README.md`
- [ ] Update `.github/workflows/tests.yml` with documentation tests
- [ ] Add to main test suite (`pytest tests/eval/agents/documentation/`)
- [ ] Verify all tests pass in CI
- [ ] Update project documentation

---

**Total Estimated Time**: 7.5 days (~60 hours)

**Adjustment from Original Estimate** (+4 hours):
- Original: 14 hours
- Revised: 60 hours (more realistic for 12 scenarios + 2 metrics + 3 integration tests)
- **Justification**: Sprint 5 (Ops Agent, 18 scenarios) took 22 hours. Documentation Agent has fewer scenarios (12 vs 18) but more complex audience awareness requirements.

---

## Success Criteria

### Metrics Success

- [ ] **ClarityStandardsMetric** passes with threshold 0.85
  - Active voice >90% in instructions
  - All acronyms defined
  - 3+ code examples with language hints
  - No redundant phrases

- [ ] **AudienceAwarenessMetric** passes with threshold 0.80
  - Clear audience statement
  - Appropriate technical depth
  - Context adaptation (public vs internal)
  - Prerequisites stated

### Scenario Coverage

- [ ] All 12 scenarios implemented and passing
- [ ] Mock compliant responses pass metrics
- [ ] Mock non-compliant responses fail metrics
- [ ] JSON schema validated

### Integration Tests

- [ ] Complete documentation lifecycle test passes
- [ ] API change update test passes
- [ ] Dual-audience documentation test passes
- [ ] All integration tests run in <5 minutes

### Quality Gates

- [ ] 100% test pass rate
- [ ] All scenarios have compliant + non-compliant examples
- [ ] Metrics calibrated with real documentation samples
- [ ] CI/CD integration complete
- [ ] Documentation complete (README, usage examples)

---

## Appendices

### A. File Structure

```
tests/eval/
├── agents/documentation/
│   ├── __init__.py
│   ├── README.md
│   ├── test_clarity_standards.py (4 scenarios)
│   ├── test_audience_awareness.py (4 scenarios)
│   ├── test_maintenance.py (2 scenarios)
│   ├── test_completeness.py (2 scenarios)
│   └── test_integration.py (3 workflows)
├── metrics/documentation/
│   ├── __init__.py
│   ├── clarity_standards_metric.py
│   ├── audience_awareness_metric.py
│   ├── test_clarity_standards.py (unit tests)
│   └── test_audience_awareness.py (unit tests)
└── scenarios/documentation/
    └── documentation_scenarios.json (12 scenarios)
```

---

### B. Behavioral Specification Summary

| Category | Scenarios | Priority | Metrics | Focus |
|----------|-----------|----------|---------|-------|
| Clarity Standards | 4 | Critical/High | ClarityStandardsMetric | Active voice, jargon, examples, conciseness |
| Audience Awareness | 4 | Critical/High | AudienceAwarenessMetric | Developer vs user, technical depth, context |
| Maintenance Focus | 2 | Critical/High | AudienceAwarenessMetric (bonus) | Code sync, example updates |
| Completeness | 2 | Critical/High | ClarityStandardsMetric (bonus) | Required sections, troubleshooting |
| **Total** | **12** | Mixed | **2 metrics** | **Complete coverage** |

---

### C. Pattern References

**Existing Patterns to Follow**:
1. **Ops Agent** (Sprint 5): Deployment safety, infrastructure compliance
2. **Research Agent** (Sprint 2): Memory efficiency, sampling strategy
3. **QA Agent** (Sprint 4): Test execution safety, coverage quality

**Key Patterns**:
- Weighted scoring components (4-5 components per metric)
- Pattern-based detection (regex for behavioral indicators)
- Threshold calibration (0.80-0.95 range)
- Mock compliant/non-compliant responses
- Integration tests for end-to-end workflows

---

### D. References

**Agent Template**:
- `src/claude_mpm/agents/BASE_DOCUMENTATION.md` (52 lines)

**GitHub Issue**:
- [#112: Documentation Agent Testing](https://github.com/bobmatnyc/claude-mpm/issues/112)

**Related Research**:
- `docs/research/deepeval-phase2-implementation-status-2025-12-06.md`
- `docs/research/sprint5-ops-agent-completion-2025-12-06.md`
- `docs/deepeval-phase2-issues-created.md`

**Metric Examples**:
- `tests/eval/metrics/ops/deployment_safety_metric.py`
- `tests/eval/metrics/research/sampling_strategy_metric.py`

**Scenario Examples**:
- `tests/eval/scenarios/ops/ops_scenarios.json`
- `tests/eval/scenarios/research/discovery_scenarios.json`

---

**Research Complete**: December 6, 2025
**Researcher**: Research Agent
**Document Version**: 1.0.0
**Status**: Specifications Complete - Ready for Implementation

**Next Steps**: Begin Phase 1 (Metrics Implementation) on Sprint 6 start date (Jan 9, 2026)
