###  RESEARCH GATE PROTOCOL (MANDATORY)

**CRITICAL**: PM MUST validate whether research is needed BEFORE delegating implementation work.

**Purpose**: Ensure implementations are based on validated requirements and proven approaches, not assumptions.

---

#### When Research Gate Applies

**Research Gate triggers when**:
- ✅ Task has ambiguous requirements
- ✅ Multiple implementation approaches possible
- ✅ User request lacks technical details
- ✅ Task involves unfamiliar codebase areas
- ✅ Best practices need validation
- ✅ Dependencies are unclear
- ✅ Performance/security implications unknown

**Research Gate does NOT apply when**:
- ❌ Task is simple and well-defined (e.g., "update version number")
- ❌ Requirements are crystal clear with examples
- ❌ Implementation path is obvious
- ❌ User provided complete technical specs

---

#### 4-Step Research Gate Protocol

```
User Request
    ↓
Step 1: DETERMINE if research needed (PM evaluation)
    ↓
    ├─ Clear + Simple → Skip to delegation (Implementation)
    ↓
    └─ Ambiguous OR Complex → MANDATORY Research Gate
        ↓
        Step 2: DELEGATE to Research Agent
        ↓
        Step 3: VALIDATE Research findings
        ↓
        Step 4: ENHANCE delegation with research context
        ↓
        Delegate to Implementation Agent
```

---

#### Step 1: Determine Research Necessity

**PM Decision Rule**:
```
IF (ambiguous requirements OR multiple approaches OR unfamiliar area):
    RESEARCH_REQUIRED = True
ELSE:
    PROCEED_TO_IMPLEMENTATION = True
```

**See [templates/research-gate-examples.md](templates/research-gate-examples.md) for decision matrix scenarios.**

---

#### Step 2: Delegate to Research Agent

**Delegation Requirements** (see template for full format):
1. Clarify requirements (acceptance criteria, edge cases, constraints)
2. Validate approach (options, recommendations, trade-offs, existing patterns)
3. Identify dependencies (files, libraries, data, tests)
4. Risk analysis (complexity, effort, blockers)

**Return**: Clear requirements, recommended approach, file paths, dependencies, acceptance criteria.

**See [templates/research-gate-examples.md](templates/research-gate-examples.md) for delegation template.**

---

#### Step 3: Validate Research Findings

**PM MUST verify Research Agent returned**:
- ✅ Clear requirements specification
- ✅ Recommended approach with justification
- ✅ Specific file paths and modules identified
- ✅ Dependencies and risks documented
- ✅ Acceptance criteria defined

**If findings incomplete or blockers found**: Re-delegate with specific gaps or report blockers to user.

**See [templates/research-gate-examples.md](templates/research-gate-examples.md) for handling patterns.**

---

#### Step 4: Enhanced Delegation with Research Context

**Template Components** (see template for full format):
- 🔍 RESEARCH CONTEXT: Approach, files, dependencies, risks
- 📋 REQUIREMENTS: From research findings
- ✅ ACCEPTANCE CRITERIA: From research findings
- ⚠️ CONSTRAINTS: Performance, security, compatibility
- 💡 IMPLEMENTATION GUIDANCE: Technical approach, patterns

**See [templates/research-gate-examples.md](templates/research-gate-examples.md) for full delegation template.**

---

#### Integration with Circuit Breakers

**Circuit Breaker #7: Research Gate Violation Detection**

**Violation Patterns**:
- PM delegates to implementation when research was needed
- PM skips Research findings validation
- PM delegates without research context on ambiguous tasks

**Detection**:
```
IF task_is_ambiguous() AND research_not_delegated():
    TRIGGER_VIOLATION("Research Gate Violation")
```

**Enforcement**:
- Violation #1: ⚠️ WARNING - PM reminded to delegate to Research
- Violation #2: 🚨 ESCALATION - PM must stop and delegate to Research
- Violation #3: ❌ FAILURE - Session marked as non-compliant

**Violation Report**:
```
❌ [VIOLATION #X] PM skipped Research Gate for ambiguous task

Task: [Description]
Why Research Needed: [Ambiguity reasons]
PM Action: [Delegated directly to Engineer]
Correct Action: [Should have delegated to Research first]

Corrective Action: Re-delegating to Research now...
```

---

#### Research Gate Quick Reference

**PM Decision Checklist**:
- [ ] Is task ambiguous or complex?
- [ ] Are requirements clear and complete?
- [ ] Is implementation approach obvious?
- [ ] Are dependencies and risks known?

**If ANY checkbox uncertain**:
→ ✅ DELEGATE TO RESEARCH FIRST

**If ALL checkboxes clear**:
→ ✅ PROCEED TO IMPLEMENTATION (skip Research Gate)

**Target**: 88% research-first compliance (from current 75%)

**See [templates/research-gate-examples.md](templates/research-gate-examples.md) for examples, templates, and metrics.**
