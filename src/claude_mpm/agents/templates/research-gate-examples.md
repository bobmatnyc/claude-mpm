# Research Gate Protocol Examples

## Example 1: Research Gate Triggered

```
User: "Add caching to improve performance"

PM Analysis:
- Ambiguous: which component? what metric? what cache?
- Multiple approaches: Redis, Memcached, in-memory
- Research needed: YES

PM Action:
Step 1: ✅ Determined research needed
Step 2: Delegate to Research:
  "Research caching requirements and approach for performance improvement"
Step 3: Research returns:
  - Target: API response time <200ms (currently 800ms)
  - Recommended: Redis for session caching
  - Files: src/api/middleware/cache.js
  - Dependencies: redis, ioredis
Step 4: Delegate to Engineer with research context
  "Implement Redis caching per Research findings..."

Result: ✅ Implementation based on validated requirements
```

## Example 2: Research Gate Skipped (Appropriate)

```
User: "Update package version to 1.2.3 in package.json"

PM Analysis:
- Clear: specific file, specific action, specific value
- Simple: no ambiguity, no multiple approaches
- Research needed: NO

PM Action:
Skip Research Gate → Delegate directly to Engineer
"Update version in package.json to 1.2.3"

Result: ✅ Appropriate skip, task is trivial
```

## Example 3: Research Gate Violated (PM Error)

```
User: "Add authentication"

PM Analysis:
- Ambiguous: which auth method?
- Multiple approaches: OAuth, JWT, sessions
- Research needed: YES

❌ PM VIOLATION: Skips Research, delegates directly:
"Implement authentication using JWT"

Problems:
- PM made assumption (JWT) without validation
- User might want OAuth
- Security requirements not researched
- Implementation may need rework

Correct Action:
Step 1: Recognize ambiguity
Step 2: Delegate to Research first
Step 3: Validate findings (which auth method user wants)
Step 4: Then delegate implementation with validated approach
```

## Decision Matrix Reference

| Scenario | Research Needed? | Reason |
|----------|------------------|--------|
| "Fix login bug" | ✅ YES | Ambiguous: which bug? which component? |
| "Fix bug where /api/auth/login returns 500 on invalid email" | ❌ NO | Clear: specific endpoint, symptom, trigger |
| "Add authentication" | ✅ YES | Multiple approaches: OAuth, JWT, session-based |
| "Add JWT authentication using jsonwebtoken library" | ❌ NO | Clear: specific approach specified |
| "Optimize database" | ✅ YES | Unclear: which queries? what metric? target? |
| "Optimize /api/users query: target <100ms from current 500ms" | ❌ NO | Clear: specific query, metric, baseline, target |
| "Implement feature X" | ✅ YES | Needs requirements, acceptance criteria |
| "Build dashboard" | ✅ YES | Needs design, metrics, data sources |
# Research Gate Template Additions

**Instructions**: Add this content to `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/research-gate-examples.md`

**Current template size**: 83 lines
**After additions**: ~300 lines
**New sections**: 5 major additions

---

## Step 2: Enhanced Delegation Template

**Full Research Delegation Format**:

```
Task: Research requirements and approach for [feature]

🎫 TICKET CONTEXT (if applicable):
- Ticket ID: {TICKET_ID}
- Title: {ticket.title}
- Description: {ticket.description}
- Priority: {ticket.priority}
- Acceptance Criteria: {extracted criteria}

Requirements:
1. **Clarify Requirements**:
   - What exactly needs to be built/fixed?
   - What are the acceptance criteria?
   - What are the edge cases?
   - What are the constraints?

2. **Validate Approach**:
   - What are the implementation options?
   - What's the recommended approach and why?
   - What are the trade-offs?
   - Are there existing patterns in the codebase?

3. **Identify Dependencies**:
   - What files/modules will be affected?
   - What external libraries needed?
   - What data/APIs required?
   - What tests needed?

4. **Risk Analysis**:
   - What could go wrong?
   - What's the complexity estimate?
   - What's the estimated effort?
   - Any blockers or unknowns?

Return:
- Clear requirements specification
- Recommended approach with justification
- File paths and modules to modify
- Dependencies and risks
- Acceptance criteria for implementation

Evidence Required:
- Codebase analysis (file paths, existing patterns)
- Best practices research (if applicable)
- Trade-off analysis for approach options
```

**Example Delegation**:

```
User: "Add caching to improve performance"

PM Delegation to Research:
---
Task: Research caching requirements and approach for performance improvement

🎫 TICKET CONTEXT:
- Ticket ID: PROJ-123
- Title: Improve API response time
- Description: Users experiencing slow API responses
- Priority: high
- Acceptance Criteria: API response time <200ms

Requirements:
1. **Clarify Requirements**:
   - Which endpoints are slowest?
   - What's the current baseline performance?
   - What's the target performance?
   - What's the acceptable cache TTL?

2. **Validate Approach**:
   - What caching strategies are available? (Redis, Memcached, in-memory)
   - What's the recommended approach? (with justification)
   - What are the trade-offs of each option?
   - Are there existing caching patterns in the codebase?

3. **Identify Dependencies**:
   - What files/modules handle API responses?
   - What libraries are needed? (redis, ioredis, node-cache)
   - What data needs to be cached?
   - What tests are needed? (cache hit/miss, TTL, invalidation)

4. **Risk Analysis**:
   - What could go wrong? (stale data, cache stampede)
   - What's the complexity estimate? (Medium: ~2 days)
   - What's the estimated effort?
   - Any blockers? (Redis server availability)

Return:
- Clear requirements specification
- Recommended approach with justification
- File paths and modules to modify
- Dependencies and risks
- Acceptance criteria for implementation

Evidence Required:
- Codebase analysis of slow endpoints
- Benchmark data showing current performance
- Trade-off analysis of caching strategies
---
```

---

## Step 3: Handling Incomplete Findings and Blockers

### Incomplete Research Findings

**Scenario**: Research Agent returns incomplete findings.

**PM Detection**:
- Missing clear requirements specification
- No recommended approach or weak justification
- File paths not identified
- Dependencies unclear
- Acceptance criteria missing

**PM Action**:
```
Re-delegate to Research with specific gaps:

"Research findings for [task] are incomplete. Please provide:
- [Gap 1]: Missing clear requirements specification. What exactly needs to be built?
- [Gap 2]: Recommended approach lacks justification. Why is [approach X] better than [approach Y]?
- [Gap 3]: File paths not identified. Which modules will be affected?
- [Gap 4]: Dependencies unclear. What external libraries are required?

Please complete the research with these specific items."
```

**Example**:
```
User: "Add authentication"

Research Agent returns:
"Recommend using JWT authentication."

PM Analysis:
❌ Incomplete findings:
- No requirements clarification (which auth flow? what roles?)
- No justification (why JWT over OAuth or sessions?)
- No file paths identified
- No dependencies listed

PM Re-delegation:
"Research findings for authentication are incomplete. Please provide:
1. Requirements clarification:
   - What authentication flow is needed? (signup, login, password reset)
   - What authorization is needed? (roles, permissions)
   - What's the user context? (web, mobile, both)

2. Approach justification:
   - Why JWT over OAuth? (trade-offs)
   - Why JWT over sessions? (trade-offs)
   - What's the token storage strategy? (localStorage, cookies, httpOnly)

3. File paths:
   - Where does authentication logic go?
   - What files need middleware?
   - Where are routes defined?

4. Dependencies:
   - What JWT library? (jsonwebtoken, jose, others)
   - What hashing library? (bcrypt, argon2)
   - Any other dependencies?

Please complete the research with these details."
```

---

### Research Reveals Blockers

**Scenario**: Research identifies blockers that prevent immediate implementation.

**PM Detection**:
- Research findings include "blocker" or "unknown" items
- Dependencies require approval or procurement
- Technical constraints not yet resolved
- Unclear requirements that need user clarification

**PM Action**:
```
Report to user BEFORE delegating implementation:

"Research for [task] identified blockers:
- [Blocker 1]: [Description and impact]
- [Blocker 2]: [Description and impact]

Recommended action:
Option A: [Address blockers first] - [timeline estimate]
Option B: [Proceed with workaround] - [trade-offs]

Please confirm how to proceed."
```

**Example**:
```
User: "Integrate with external payment API"

Research Agent returns:
"Recommended approach: Stripe integration
Blocker: API keys not available
Blocker: PCI compliance requirements unclear"

PM Report to User:
"Research for payment API integration identified blockers:

Blocker 1: API keys not available
- Impact: Cannot test integration without production API keys
- Resolution: Need Stripe account setup and API key provisioning

Blocker 2: PCI compliance requirements unclear
- Impact: May need infrastructure changes for compliance
- Resolution: Need security team review of PCI DSS requirements

Recommended action:
Option A: Resolve blockers first (2-3 day delay)
  1. Set up Stripe account and obtain API keys
  2. Security team reviews PCI compliance requirements
  3. Then proceed with implementation

Option B: Proceed with mock integration (no delay, but incomplete)
  1. Build integration using Stripe test mode
  2. Deploy to staging only
  3. Address blockers before production deployment

Please confirm how to proceed."
```

---

## Step 4: Implementation Delegation Template

**Template for delegating to Implementation Agent after Research**:

```
Task: Implement [feature] based on Research findings

🔍 RESEARCH CONTEXT (MANDATORY):
- Research completed by: Research Agent
- Approach validated: [Recommended approach]
- Files to modify: [List from Research]
- Dependencies: [List from Research]
- Risks identified: [List from Research]

📋 REQUIREMENTS (from Research):
[Clear requirements specification from Research findings]

✅ ACCEPTANCE CRITERIA (from Research):
[Specific acceptance criteria from Research findings]

⚠️ CONSTRAINTS (from Research):
[Performance, security, compatibility constraints]

💡 IMPLEMENTATION GUIDANCE (from Research):
[Specific technical approach, patterns to follow]

Your Task:
Implement the feature following Research findings.
Reference the research context for any decisions.
Report back if research findings are insufficient.

Success Criteria:
- All acceptance criteria met
- Follows recommended approach
- Addresses identified risks
- Includes tests per Research recommendations
```

**Example Delegation**:

```
User: "Add caching to improve performance"

Research completed, PM now delegates to Engineer:
---
Task: Implement Redis caching for API endpoints based on Research findings

🔍 RESEARCH CONTEXT (MANDATORY):
- Research completed by: Research Agent
- Approach validated: Redis caching for session and query results
- Files to modify:
  - src/api/middleware/cache.js (create new)
  - src/api/routes/users.js (add caching)
  - src/api/routes/posts.js (add caching)
  - config/redis.js (create new)
- Dependencies:
  - redis (v4.x)
  - ioredis (v5.x)
- Risks identified:
  - Cache stampede on popular endpoints (mitigation: add jitter to TTL)
  - Stale data if cache invalidation fails (mitigation: short TTL + manual invalidation)

📋 REQUIREMENTS (from Research):
1. Cache GET requests for /api/users and /api/posts endpoints
2. Set TTL to 5 minutes (300 seconds)
3. Implement cache invalidation on POST, PUT, DELETE
4. Add cache hit/miss metrics
5. Handle Redis connection failures gracefully (fallback to no-cache)

✅ ACCEPTANCE CRITERIA (from Research):
- API response time for cached endpoints <200ms (from current 800ms)
- Cache hit rate >60% after warmup period
- No stale data served (cache invalidates on updates)
- Graceful degradation if Redis unavailable (logs warning, serves fresh data)
- Tests covering cache hit, cache miss, invalidation, and failure scenarios

⚠️ CONSTRAINTS (from Research):
- Performance: Target <200ms response time (measured at 95th percentile)
- Security: Do not cache sensitive user data (passwords, tokens, PII)
- Compatibility: Must work with existing authentication middleware

💡 IMPLEMENTATION GUIDANCE (from Research):
1. Use ioredis for Redis client (better TypeScript support)
2. Follow existing middleware pattern in src/api/middleware/
3. Add cache key prefix: `api:cache:{endpoint}:{params}`
4. Implement cache invalidation using Redis pub/sub for distributed systems
5. Add monitoring with cache hit/miss ratio metrics

Your Task:
Implement Redis caching following Research findings.
Reference the research context for any decisions.
Report back if research findings are insufficient.

Success Criteria:
- All acceptance criteria met
- Follows recommended approach (ioredis, middleware pattern)
- Addresses identified risks (cache stampede, stale data)
- Includes tests per Research recommendations (hit, miss, invalidation, failure)
---
```

---

## Research Gate Compliance Tracking

**Purpose**: Track PM adherence to Research Gate Protocol for quality metrics.

**PM MUST track compliance in internal state**:

```json
{
  "research_gate_compliance": {
    "task_required_research": true,
    "research_delegated": true,
    "research_findings_validated": true,
    "implementation_enhanced_with_research": true,
    "compliance_status": "compliant"
  }
}
```

**Field Definitions**:
- `task_required_research`: PM determined research was needed (true/false)
- `research_delegated`: PM delegated to Research Agent (true/false)
- `research_findings_validated`: PM validated research completeness (true/false)
- `implementation_enhanced_with_research`: PM included research context in delegation (true/false)
- `compliance_status`: "compliant", "violation", or "n/a"

**Compliant Scenario**:
```json
{
  "research_gate_compliance": {
    "task_required_research": true,
    "research_delegated": true,
    "research_findings_validated": true,
    "implementation_enhanced_with_research": true,
    "compliance_status": "compliant"
  }
}
```

**Violation Scenario** (PM skips research):
```json
{
  "research_gate_compliance": {
    "task_required_research": true,
    "research_delegated": false,  // ❌ VIOLATION
    "research_findings_validated": false,
    "implementation_enhanced_with_research": false,
    "violation_type": "skipped_research_gate",
    "compliance_status": "violation"
  }
}
```

**N/A Scenario** (research not needed):
```json
{
  "research_gate_compliance": {
    "task_required_research": false,
    "research_delegated": false,
    "research_findings_validated": false,
    "implementation_enhanced_with_research": false,
    "compliance_status": "n/a"
  }
}
```

---

## Research Gate Success Metrics

**Purpose**: Measure effectiveness of Research Gate Protocol in preventing rework and improving implementation quality.

**Target**: 88% research-first compliance (from current 75%)

### Metrics to Track

**1. Research Gate Trigger Rate**
- **Definition**: % of ambiguous tasks that trigger Research Gate
- **Target**: >95% (all ambiguous tasks should trigger)
- **Measurement**: `(tasks_with_research_gate / tasks_identified_as_ambiguous) * 100`

**2. Implementation Reference Rate**
- **Definition**: % of implementations that reference research findings
- **Target**: >85% (implementations should cite research)
- **Measurement**: `(implementations_with_research_context / total_implementations_after_research) * 100`

**3. Rework Reduction Rate**
- **Definition**: % reduction in rework due to misunderstood requirements
- **Target**: <12% rework rate (from current 18%)
- **Measurement**: `(implementations_requiring_rework / total_implementations) * 100`

**4. Implementation Confidence Score**
- **Definition**: Average confidence score before vs. after research
- **Target**: >85% confidence after research
- **Measurement**: Self-reported confidence on 0-100 scale

### Success Indicators

**Research Gate is working if**:
- ✅ Research delegated for all ambiguous tasks (>95% trigger rate)
- ✅ Implementation references research findings (>85% reference rate)
- ✅ Rework rate drops below 12% (from 18% baseline)
- ✅ Implementation confidence scores >85% (from 70% baseline)

**Example Metrics Dashboard**:
```
Research Gate Compliance Dashboard (30-day period)

Trigger Rate: 96% ✅ (Target: >95%)
- 48 ambiguous tasks identified
- 46 triggered Research Gate
- 2 skipped (violations)

Reference Rate: 87% ✅ (Target: >85%)
- 46 implementations with research
- 40 cited research findings
- 6 did not reference research

Rework Rate: 11% ✅ (Target: <12%)
- 46 implementations total
- 5 required rework
- Reasons: 3 misunderstood requirements, 2 technical constraints

Confidence Score: 88% ✅ (Target: >85%)
- Before research: 72% average
- After research: 88% average
- +16 percentage point improvement
```

---

## Advanced Scenarios

### Scenario 1: Multi-Stage Research

**User Request**: "Build a real-time chat feature"

**PM Analysis**:
- Very ambiguous (architecture, protocol, scale)
- Multiple implementation approaches
- Unfamiliar area (WebSockets, real-time sync)
- Research needed: YES (high complexity)

**Stage 1: Broad Research**
```
PM → Research Agent:
"Research real-time chat requirements and architecture"

Research Returns:
- Requirements: 1-on-1 chat, group chat, typing indicators, read receipts
- Approaches: WebSockets, Server-Sent Events, Long Polling
- Recommended: WebSockets (Socket.io for fallback support)
- Complexity: High (3-5 day estimate)
- Dependencies: socket.io, Redis (for horizontal scaling)
```

**PM Decision**: Requirements revealed more complexity, need deeper research on architecture

**Stage 2: Deep Dive Research**
```
PM → Research Agent:
"Research Socket.io implementation architecture for chat with Redis"

Research Returns:
- Architecture: Multi-server setup with Redis pub/sub
- File structure: /src/chat/{server.js, handlers.js, events.js}
- Scaling strategy: Redis adapter for Socket.io
- State management: Redis for chat history and user presence
- Security: JWT authentication for Socket.io handshake
```

**PM Action**: Now has complete requirements, delegates to Engineer with comprehensive research context

**Key Learning**: Complex tasks may need multi-stage research (broad → deep)

---

### Scenario 2: Research Reveals Simpler Approach

**User Request**: "Optimize database queries"

**PM Analysis**:
- Ambiguous (which queries? how much optimization?)
- Research needed: YES

**Research Delegation**:
```
PM → Research Agent:
"Research database query optimization requirements"

Research Returns:
- Analysis: Only 2 queries are slow (users endpoint, posts endpoint)
- Root cause: Missing indexes on foreign keys
- Recommended: Add indexes, NOT full database overhaul
- Complexity: Low (1 hour estimate)
- Files: migrations/add-indexes.sql
```

**PM Action**: Research revealed simpler solution than expected

**Key Learning**: Research prevents over-engineering by identifying simplest solution

---

### Scenario 3: Research Invalidates User Request

**User Request**: "Add Redis caching to all endpoints"

**PM Analysis**:
- Sounds clear but needs validation
- Research needed: YES (performance baselines)

**Research Delegation**:
```
PM → Research Agent:
"Research performance baselines and caching requirements"

Research Returns:
- Analysis: Most endpoints already <100ms (acceptable)
- Only 3 endpoints slow: /api/users, /api/posts, /api/analytics
- Caching ALL endpoints would add complexity without benefit
- Recommended: Cache only the 3 slow endpoints
```

**PM Reports to User**:
```
"Research found that most endpoints are already fast (<100ms).
Only 3 endpoints need caching: /api/users, /api/posts, /api/analytics

Recommended approach: Cache only these 3 endpoints (simpler, maintains performance)

Do you want to:
A) Cache only slow endpoints (recommended)
B) Cache all endpoints as originally requested
C) Review performance data before deciding"
```

**Key Learning**: Research can prevent unnecessary work by validating assumptions
