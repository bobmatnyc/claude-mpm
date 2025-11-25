# Extended Thinking Quick Reference Guide

**For:** PM Agent (Claude MPM)
**Ticket:** 1M-203
**Version:** 1.0
**Last Updated:** 2025-11-25

---

## 🚀 Quick Decision Framework

### Should I Use Extended Thinking? (5-Second Check)

```
Is this task:
  ☐ Complex architectural decision?
  ☐ Ambiguous requirements needing exploration?
  ☐ Multi-agent coordination (4+ agents)?
  ☐ Trade-off analysis required?
  ☐ Scope protection decision?

If YES to ANY → Consider extended thinking
If NO to ALL → Use base model (faster, cheaper)
```

---

## 💰 Budget Allocation Cheat Sheet

| Task Type | Budget | Use Case |
|-----------|--------|----------|
| **Simple Delegation** | **0 tokens** | Single agent, clear requirements |
| **Complex Task** | **16-32K** | Multi-step decomposition, 2-3 agents |
| **Critical Decision** | **40-64K** | Architecture, major refactoring |

**Rule of Thumb:** 95% of tasks = 0 tokens, 4% = 16-32K, 1% = 40-64K

---

## ✅ DO Use Extended Thinking For:

1. **Architectural Decisions**
   - "Should we use REST or GraphQL for this API?"
   - "Microservices vs. monolith for this feature?"

2. **Complex Task Decomposition**
   - "This feature needs research, design, implementation, testing - what's the optimal order?"
   - "Which agent should handle which part of this multi-step workflow?"

3. **Ambiguous Requirements**
   - "User wants 'better performance' - what does that mean?"
   - "Security requirements are unclear - what should we clarify?"

4. **Trade-off Analysis**
   - "Fast implementation vs. maintainable code vs. low cost - what's the right balance?"
   - "Technical debt now or perfect solution later?"

5. **Scope Protection Decisions**
   - "Is this discovered work in-scope or out-of-scope?"
   - "Should we ask user before expanding scope?"

---

## ❌ DON'T Use Extended Thinking For:

1. **Simple Delegations**
   - ❌ "Delegate research to research agent"
   - ❌ "Create ticket for bug fix"

2. **Routine Operations**
   - ❌ "Read ticket status"
   - ❌ "Update ticket state to in_progress"

3. **Tool Use**
   - ❌ "Attach comment to ticket"
   - ❌ "Run git status"

4. **Templated Responses**
   - ❌ "Report work completion to user"
   - ❌ "Ask clarifying question"

**Remember:** Extended thinking for COMPLEX DECISIONS, not SIMPLE TASKS

---

## 🔄 Interleaved Thinking Decision

### Enable When:
- ✅ Workflow has 5+ sequential tool calls
- ✅ Tool results need interpretation before next step
- ✅ Agent coordination requires reflection
- ✅ Error recovery depends on tool output

### Don't Enable When:
- ❌ Single tool call
- ❌ Batch operations
- ❌ High-throughput tasks
- ❌ Clear sequential steps

**Header Required:** `anthropic-beta: interleaved-thinking-2025-05-14`

---

## 💸 Cost Optimization Rules

### Rule 1: Always Use Prompt Caching
- Cache PM instructions (119KB)
- Cache tool definitions
- 55% cost savings in multi-turn sessions

### Rule 2: Progressive Allocation
- Start with base model (0 tokens)
- Escalate to extended thinking if complexity detected
- Don't overthink simple tasks

### Rule 3: Monitor ROI
- Track: Thinking tokens used
- Measure: Decisions made, errors prevented
- Adjust: Budget based on empirical data

### Break-Even Analysis
```
Caching Break-Even: 2+ turns within 1 hour
Extended Thinking ROI: Must prevent ≥1 failed delegation
Multi-Turn Sessions: Caching offsets thinking cost (55% savings)
```

---

## 🚫 Circuit Breaker Enforcement

**Extended Thinking NEVER Justifies:**

❌ **Direct Coding** (CB #1)
- Think about architecture ✅
- Write code yourself ❌

❌ **Direct Testing** (CB #2)
- Think about test strategy ✅
- Run tests yourself ❌

❌ **File Modifications** (CB #3)
- Think about refactoring ✅
- Edit files yourself ❌

❌ **Ticket Operations** (CB #6)
- Think about ticket organization ✅
- Create tickets yourself ❌

**Golden Rule:** Extended thinking improves WHAT you delegate, NOT whether you delegate

---

## 📊 PM Self-Check Decision Tree

```
START: Task arrives

Q1: Is this delegation or implementation decision?
├─ DELEGATION → Thinking allowed ✅
└─ IMPLEMENTATION → Delegate immediately ❌

Q2: Genuine ambiguity/complexity?
├─ YES → Thinking justified ✅
└─ NO → Base model sufficient ❌

Q3: Multi-turn session with caching?
├─ YES → Cost offset by cache savings ✅
└─ NO → Thinking adds cost ⚠️

Q4: Will thinking improve delegation quality?
├─ YES → Positive ROI ✅
└─ NO → Negative ROI ❌

Q5: Budget allocated appropriately?
├─ Simple task → 0 tokens ✅
├─ Complex task → 16-32K tokens ✅
└─ Critical decision → 40-64K tokens ✅

ALL CHECKS PASS → Use Extended Thinking
ANY CHECK FAILS → Use Base Model
```

---

## 🎯 Real-World Examples

### ✅ GOOD: Extended Thinking for Architecture Decision

**Task:** "Add real-time notifications to application"

**PM Thinking (32K budget):**
```
[THINK] Multiple approaches exist:
1. WebSockets (real-time, complex infrastructure)
2. Server-Sent Events (simpler, one-way)
3. Polling (simplest, higher latency)

User context: "notifications for status updates, not chat"
→ SSE sufficient (simpler than WebSockets)

Implementation impact:
- WebSockets: 2 weeks, new infrastructure, ongoing maintenance
- SSE: 3 days, existing infrastructure, lower maintenance
- Polling: 1 day, inefficient at scale

DECISION: Recommend SSE (balance of real-time + simplicity)
```

**PM Action:** Delegate to Engineer with clear approach rationale

**Outcome:** Engineer implements SSE without confusion or rework

---

### ❌ BAD: Extended Thinking for Simple Delegation

**Task:** "Create ticket for bug fix"

**PM Thinking (16K budget - WASTED):**
```
[THINK] Should I create this ticket?
- Yes, user requested it
- Ticket system is configured
- Priority is medium
- Assignee should be default user
- Tags should include "bug"

DECISION: Create ticket
```

**PM Action:** Ticket created (after wasting 16K tokens on obvious decision)

**Outcome:** Same result as base model, but slower and more expensive

**CORRECT APPROACH:** Use base model (0 tokens), create ticket immediately

---

### ✅ GOOD: Extended Thinking for Scope Protection

**Task:** "Improve authentication system"

**PM Thinking (24K budget):**
```
[THINK] User request is ambiguous:
- "Improve" could mean: security, UX, performance, features
- Current system: Session-based, no 2FA, password-only
- Possible improvements:
  1. Add 2FA (security improvement)
  2. Add social login (UX improvement)
  3. Optimize session storage (performance)
  4. Add password complexity rules (security)

Each is 1-2 weeks of work. User might want ONE, not ALL.

DECISION: Ask user to clarify which improvement(s) before committing scope
```

**PM Action:** Ask user structured question with options

**Outcome:** User clarifies "Add 2FA only" - prevents scope creep

---

### ❌ BAD: Extended Thinking Leading to Direct Action

**Task:** "Fix typo in documentation"

**PM Thinking (8K budget):**
```
[THINK] This is a simple typo fix:
- File: README.md
- Line 42: "authnetication" → "authentication"
- Low risk, no code changes
- I can fix this quickly myself

DECISION: Fix typo directly
```

**PM Action:** Edits README.md (CIRCUIT BREAKER VIOLATION)

**CORRECT APPROACH:**
- Skip thinking (simple task)
- Delegate to Documentation agent
- No circuit breaker violation

---

## 📝 Quick Checklist Before Thinking

Before allocating thinking budget, ask:

- [ ] Is this a complex decision requiring trade-off analysis?
- [ ] Would base model struggle with this task's ambiguity?
- [ ] Am I in a multi-turn session (caching active)?
- [ ] Will thinking prevent failed delegation or rework?
- [ ] Is budget allocation appropriate (0%, 10-15%, 20-25%)?

**If 3+ YES → Use extended thinking**
**If 2 or fewer YES → Use base model**

---

## 🔗 Full Documentation Reference

**Complete Guidelines:** `/docs/research/extended-thinking-guidelines-1M-203.md`
**Integration Summary:** `/docs/research/extended-thinking-integration-summary.md`
**Research Foundation:** `/docs/research/claude-4-5-best-practices-2025-11-25.md`

**Target Integration:** `src/claude_mpm/agents/PM_INSTRUCTIONS.md` (after line 1776)

---

## 🎓 Key Principles (Memorize These)

1. **"Extended thinking enhances delegation, never replaces it"**
   - Think about WHAT to delegate
   - NOT whether to delegate

2. **"95% of tasks need 0 thinking tokens"**
   - Simple delegations are the norm
   - Extended thinking is the exception

3. **"Caching makes thinking affordable"**
   - Multi-turn sessions offset thinking cost
   - 55% savings with prompt caching

4. **"All circuit breakers remain enforced"**
   - Thinking doesn't justify direct action
   - Delegation-first mandate always applies

5. **"ROI must be positive"**
   - Thinking should prevent errors
   - Not add latency to simple tasks

---

**PM Commitment:**

> "I will use extended thinking to make BETTER delegation decisions,
> NOT to avoid delegating."

---

**Quick Reference Version:** 1.0
**Ticket:** 1M-203
**Last Updated:** 2025-11-25
