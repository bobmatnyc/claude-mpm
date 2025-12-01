# Context Management Examples

**Purpose**: Comprehensive examples of PM context management and scope validation workflows
**Usage**: Reference for PM when managing token budgets and scope boundaries
**Related**: validation-templates.md, pm-examples.md

---

## 70% Context Alert Examples

### Threshold Detection and User Prompt

**Trigger**: Token usage reaches 70% of context window (140K/200K tokens)

**PM Detection**:
```json
{
  "context_monitoring": {
    "current_tokens": 140000,
    "max_tokens": 200000,
    "usage_percentage": 70,
    "alert_level": "warning"
  }
}
```

**PM Action - Mandatory Pause Prompt**:
```
⚠️ CONTEXT ALERT: Token usage at 70% (140K/200K tokens)

Current work summary:
- Active tickets: PROJ-123, PROJ-124, PROJ-125
- Agents involved: research, engineer, ticketing
- Key decisions: [brief summary of major decisions]

Recommendations:
Option A: Continue with reduced verbosity (PM will compress responses)
Option B: Create session resume file and start fresh context
Option C: Complete current ticket only, then pause

Please choose how to proceed:
```

**Example User Workflow**:
```
User chooses Option B → PM creates session resume

PM creates: .claude-mpm/sessions/session-2025-12-01-1430.md
Content:
---
Session Resume: 2025-12-01 14:30
Context: 70% threshold reached

Active Work:
- PROJ-123: OAuth2 implementation (80% complete)
  - Status: Frontend done, backend in progress
  - Next: Complete token refresh logic
  - Blockers: None

- PROJ-124: Database migration (pending)
  - Status: Not started
  - Dependencies: PROJ-123 completion

- PROJ-125: UI improvements (on hold)
  - Status: Research phase
  - Dependencies: Design mockups needed

Decisions Made:
1. OAuth2 with JWT tokens (vs session-based)
2. Redis for token storage (vs database)
3. 15-minute token expiry (vs 1-hour)

Next Session Actions:
1. Complete PROJ-123 token refresh logic
2. Test OAuth2 flow end-to-end
3. Create PR for PROJ-123
4. Start PROJ-124 database migration
---

PM: "Session resume file created. Starting fresh context..."
[New conversation begins, user shares resume file]
```

---

## 85% Context Escalation Examples

### Critical Warning and Automatic Pause

**Trigger**: Token usage reaches 85% of context window (170K/200K tokens)

**PM Detection**:
```json
{
  "context_monitoring": {
    "current_tokens": 170000,
    "max_tokens": 200000,
    "usage_percentage": 85,
    "alert_level": "critical"
  }
}
```

**PM Action - Automatic Session Resume Creation**:
```
🚨 CRITICAL CONTEXT ALERT: Token usage at 85% (170K/200K tokens)

Automatically creating session resume file for continuity...

Session resume file: .claude-mpm/sessions/session-2025-12-01-1500.md
Git commit created: "session: pause at 85% context threshold"

Current state preserved:
✅ Active tickets and their status
✅ Agent delegation history
✅ Key decisions and rationale
✅ Next actions and priorities
✅ Blockers and dependencies

Recommendation: START NEW CONVERSATION and reference resume file.

To resume:
1. Start new Claude conversation
2. Share: "Resume from session-2025-12-01-1500.md"
3. PM will load context and continue work
```

**Automatic Git Workflow**:
```bash
# PM automatically executes these commands
git add .claude-mpm/sessions/session-2025-12-01-1500.md
git commit -m "session: pause at 85% context threshold (PROJ-123, PROJ-124, PROJ-125)"
git push origin main

# Resume file preserved in git history
# Other team members can reference if needed
```

---

## 95% Emergency Stop Examples

### Context Limit Enforcement

**Trigger**: Token usage reaches 95% of context window (190K/200K tokens)

**PM Detection**:
```json
{
  "context_monitoring": {
    "current_tokens": 190000,
    "max_tokens": 200000,
    "usage_percentage": 95,
    "alert_level": "emergency"
  }
}
```

**PM Action - Mandatory Stop**:
```
🛑 EMERGENCY CONTEXT LIMIT: Token usage at 95% (190K/200K tokens)

STOPPING ALL WORK IMMEDIATELY

Session resume file created: .claude-mpm/sessions/emergency-2025-12-01-1530.md
Git commit created: "session: emergency stop at 95% context threshold"

⚠️ YOU MUST START A NEW CONVERSATION NOW ⚠️

This conversation cannot continue safely. Next response may be truncated or fail.

To resume work:
1. Start new Claude conversation immediately
2. Share: "Emergency resume from emergency-2025-12-01-1530.md"
3. PM will load context and resume from safe state

DO NOT continue in this conversation. Context overflow risk.
```

**Emergency Resume File Content**:
```markdown
---
EMERGENCY SESSION RESUME: 2025-12-01 15:30
Context: 95% threshold - EMERGENCY STOP

Critical State:
- Work stopped mid-task to prevent context overflow
- Last action: Engineer implementing PROJ-123 token refresh
- Conversation unsafe, must switch to new context

Active Work (CRITICAL):
- PROJ-123: OAuth2 implementation
  - Status: 85% complete, token refresh in progress
  - Last code change: src/auth/refresh.js (partially complete)
  - IMPORTANT: Function refreshToken() needs completion
  - Test status: 12/15 passing, 3 pending completion

Immediate Next Steps:
1. Complete refreshToken() function in src/auth/refresh.js
2. Fix 3 failing tests in tests/auth/refresh.test.js
3. Run full test suite: npm test
4. Create PR if all tests pass

Blockers: None
Dependencies: None
Estimated completion: 30 minutes

⚠️ RESUME PRIORITY: HIGH - work was mid-function
---
```

---

## Scope Validation Template Examples

### Complete OAuth2 Scenario

**Scenario**: Research Agent discovers 10 optimization opportunities during OAuth2 implementation

**Step 1: User Request**
```
User: "Implement TICKET-123: Add OAuth2 authentication"
```

**Step 2: PM Delegates to Research**
```
PM → Research: "Research OAuth2 implementation requirements for TICKET-123"
```

**Step 3: Research Returns Findings + Discoveries**
```
Research → PM: "OAuth2 research complete.

Core Requirements (In-Scope):
1. Google OAuth2 integration
2. Token refresh mechanism
3. User profile sync

Discoveries (10 items):
1. Token storage strategy needed (Redis vs DB)
2. Session management approach (cookies vs localStorage)
3. Error handling for expired tokens
4. Logout flow implementation
5. Token revocation endpoint
6. Profile update sync frequency
7. Database schema for user tokens
8. Rate limiting for auth endpoints
9. Monitoring for auth failures
10. Documentation for auth flow
```

**Step 4: PM Classifies Discoveries**
```
PM Analysis:

In-Scope (2 items - directly related to TICKET-123):
- Item 1: Token storage strategy (required for OAuth2)
- Item 3: Error handling for expired tokens (part of token refresh)

Scope-Adjacent (3 items - related but separate concerns):
- Item 2: Session management (auth-adjacent)
- Item 4: Logout flow (auth-adjacent)
- Item 7: Database schema for tokens (infrastructure)

Out-of-Scope (5 items - different domains):
- Item 6: Profile sync frequency (separate feature)
- Item 8: Rate limiting (infrastructure/security)
- Item 9: Monitoring (ops/observability)
- Item 10: Documentation (separate task)
- Item 5: Token revocation (security enhancement)
```

**Step 5: PM Uses ScopeValidationTemplate**
```python
ScopeValidationTemplate(
    originating_ticket="TICKET-123",
    ticket_title="Add OAuth2 authentication",
    in_scope_items=[
        "Token storage strategy (Redis vs DB)",
        "Error handling for expired tokens"
    ],
    scope_adjacent_items=[
        "Session management approach",
        "Logout flow implementation",
        "Database schema for user tokens"
    ],
    out_of_scope_items=[
        "Profile update sync frequency",
        "Rate limiting for auth endpoints",
        "Monitoring for auth failures",
        "Documentation for auth flow",
        "Token revocation endpoint"
    ]
)
```

**Step 6: PM Presents Options to User**
```
🎯 SCOPE VALIDATION: Research discovered 10 items during TICKET-123 work

Original ticket: TICKET-123 - Add OAuth2 authentication

Classification:
✅ In-Scope (2): Core OAuth2 requirements
⚠️ Scope-Adjacent (3): Related auth concerns
❌ Out-of-Scope (5): Different domains (ops, docs, security)

How should we handle these discoveries?

Option A: Include all 10 items in TICKET-123 scope
- Expands current ticket significantly
- Delays completion (estimate: +3 days)
- Single large PR with multiple concerns

Option B: Create 2 subtasks under TICKET-123, defer 8 to backlog
- Subtasks: "Token storage strategy", "Error handling"
- Deferred: 8 items added to backlog for future work
- Focused PR on core OAuth2 functionality

Option C: Create 2 subtasks + separate epic for 8 items
- Subtasks: Same as Option B
- New epic: "Auth Infrastructure" (3 items)
- New epic: "System Observability" (5 items)
- Clear organization, proper prioritization

Please select an option:
```

**Step 7: User Chooses Option C**
```
User: "Option C - create subtasks and separate epics"
```

**Step 8: PM Delegates to Ticketing**
```
PM → Ticketing: "Based on TICKET-123 scope validation:

1. Create 2 subtasks under TICKET-123:
   - TICKET-123-1: Implement token storage strategy (Redis vs DB)
   - TICKET-123-2: Add error handling for expired tokens

2. Create new epic: AUTH-INFRA - Auth Infrastructure
   - AUTH-INFRA-1: Session management approach
   - AUTH-INFRA-2: Logout flow implementation
   - AUTH-INFRA-3: Database schema for user tokens

3. Create new epic: OBS-001 - System Observability
   - OBS-001-1: Profile update sync frequency
   - OBS-001-2: Rate limiting for auth endpoints
   - OBS-001-3: Monitoring for auth failures
   - OBS-001-4: Documentation for auth flow
   - OBS-001-5: Token revocation endpoint"
```

**Step 9: Ticketing Executes**
```
Ticketing → PM: "Tickets created:
- TICKET-123-1: Token storage strategy (subtask)
- TICKET-123-2: Error handling (subtask)
- Epic AUTH-INFRA created with 3 tickets
- Epic OBS-001 created with 5 tickets

Original TICKET-123 now has clear scope boundaries."
```

**Step 10: PM Delegates Implementation**
```
PM → Engineer: "Implement TICKET-123 (OAuth2 authentication)

🎫 TICKET CONTEXT:
- Ticket ID: TICKET-123
- Scope: Core OAuth2 flow (Google integration, token refresh, profile sync)
- Subtasks: TICKET-123-1 (storage), TICKET-123-2 (error handling)

✅ IN-SCOPE:
- Implement Google OAuth2 integration
- Implement token refresh mechanism
- Sync user profile from Google
- Complete TICKET-123-1 (token storage decision)
- Complete TICKET-123-2 (error handling)

❌ OUT-OF-SCOPE (tracked separately):
- Session management (AUTH-INFRA-1)
- Logout flow (AUTH-INFRA-2)
- Monitoring, docs, rate limiting (OBS-001 epic)

Proceed with in-scope items only."
```

**Key Learning**: Scope validation prevents scope creep by:
1. Classifying discoveries into in-scope, scope-adjacent, out-of-scope
2. Presenting clear options to user (expand vs subtask vs separate epic)
3. Creating proper ticket hierarchy based on user choice
4. Providing explicit scope boundaries to implementation agents

---

## Token Usage Monitoring Patterns

### Continuous Monitoring

**PM Internal State**:
```json
{
  "context_monitoring": {
    "current_tokens": 85000,
    "max_tokens": 200000,
    "usage_percentage": 42.5,
    "alert_level": "normal",
    "last_check": "2025-12-01T14:30:00Z",
    "alerts_triggered": []
  }
}
```

**Threshold Triggers**:
- 70% → Warning alert + user prompt
- 85% → Critical alert + auto-create resume file
- 95% → Emergency stop + mandatory conversation switch

**PM Reports Token Usage**:
```
Every major delegation, PM includes token status:

"Delegating to engineer... (Context: 42% - 85K/200K tokens)"
"Research complete. (Context: 58% - 116K/200K tokens)"
⚠️ "Approaching 70% threshold. (Context: 68% - 136K/200K tokens)"
```

---

## Session Resume Examples

### Git-Based Session Continuity

**Creating Resume File**:
```markdown
# Session Resume: 2025-12-01 14:30

## Context Summary
Token usage: 72% (144K/200K)
Reason: Proactive pause before critical threshold

## Active Work

### PROJ-123: OAuth2 Implementation
**Status**: 60% complete
**Current Phase**: Backend token refresh logic
**Completed**:
- ✅ Google OAuth2 setup
- ✅ Frontend login button
- ✅ User profile sync
**Remaining**:
- ⏳ Token refresh endpoint
- ⏳ Error handling
- ⏳ Tests for refresh flow
**Blockers**: None
**Next Actions**:
1. Implement refreshToken() in src/auth/refresh.js
2. Add tests in tests/auth/refresh.test.js
3. Test end-to-end OAuth2 flow

### PROJ-124: Database Migration
**Status**: Not started
**Dependencies**: PROJ-123 completion required
**Reason**: Migration needs auth schema from PROJ-123

### PROJ-125: UI Improvements
**Status**: On hold
**Reason**: Awaiting design mockups from stakeholder

## Key Decisions
1. **OAuth2 vs Session-based**: Chose OAuth2 for external identity provider support
2. **Token Storage**: Redis for performance (<50ms token lookup requirement)
3. **Token Expiry**: 15 minutes (security requirement from compliance team)

## Technical Context
- Branch: feature/oauth2-implementation
- Last commit: e4b8c1a "feat: add Google OAuth2 frontend"
- Tests passing: 12/15 (3 pending token refresh tests)
- Dependencies added: google-auth-library, ioredis

## Resume Instructions
1. Verify current branch: `git checkout feature/oauth2-implementation`
2. Check test status: `npm test`
3. Continue from refreshToken() implementation
4. Estimated completion: 2-3 hours

---
Generated: 2025-12-01 14:30:00
Token usage at pause: 72%
Resume priority: Medium (no blockers)
```

**Using Resume File**:
```
New conversation:

User: "Resume from session-2025-12-01-1430.md"

PM: "Resuming session from 2025-12-01 14:30...

Context loaded:
- PROJ-123: OAuth2 implementation (60% complete)
- Last action: Frontend complete, backend refresh in progress
- Next: Complete refreshToken() in src/auth/refresh.js

Current status check...
[Delegates to engineer: "Verify project state and continue token refresh implementation"]

Ready to continue. What would you like to work on?"
```

---

## Success Metrics

**Context management is working if**:
- ✅ PM detects 70% threshold and pauses for user decision
- ✅ PM auto-creates resume file at 85% threshold
- ✅ PM enforces hard stop at 95% threshold
- ✅ Resume files enable seamless session continuity
- ✅ No context overflow errors or truncated responses
- ✅ User has clear options at each threshold

**Red Flags**:
- ❌ PM continues past 85% without creating resume file
- ❌ Context reaches 95%+ without emergency stop
- ❌ Resume files missing critical state information
- ❌ Session resume fails due to incomplete context
- ❌ Token monitoring not reported to user

---

## Related References

- **Validation Templates**: See [validation-templates.md](validation-templates.md)
- **PM Examples**: See [pm-examples.md](pm-examples.md)
- **Structured Questions**: See [structured-questions-examples.md](structured-questions-examples.md)

---

**Last Updated**: 2025-12-01
**Phase**: Phase 3 Optimization - Example Extraction
