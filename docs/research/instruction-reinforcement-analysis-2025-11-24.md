# Instruction Reinforcement Analysis for Ticket 1M-163

**Research Date**: 2025-11-24
**Ticket**: 1M-163 - Prompt/Instruction Reinforcement/Hydration
**Objective**: Achieve 90% instruction success rate through clarification and research-first workflows
**Researcher**: Research Agent

---

## Executive Summary

This research analyzes PM_INSTRUCTIONS.md and agent templates to identify gaps in clarification prompts and research-first workflows. Current instructions show **strong delegation enforcement** but have **critical gaps in pre-implementation validation** and **insufficient clarification trigger mechanisms**. The analysis reveals that while PM has robust circuit breakers, agents lack systematic clarification protocols, leading to premature implementation without proper requirements validation.

**Key Findings**:
- ✅ PM has excellent structured questions framework (AskUserQuestion templates)
- ❌ Agents lack systematic "Research Check" enforcement (mentioned but not enforced)
- ❌ No explicit "clarification score" or validation gates before implementation
- ❌ Insufficient guidance on WHEN to ask vs. WHEN to proceed
- ⚠️ Research-first workflow exists but lacks explicit enforcement checkpoints

**Recommended Success Metrics**:
- 90% of ambiguous tasks trigger clarification before implementation
- 85% of implementation tasks include research validation step
- 95% of agent responses include "confidence score" or "assumptions stated"
- Zero implementation starts without requirements validation gate

---

## 1. Current Instruction Strengths

### 1.1 PM Structured Questions Framework (Lines 192-477)

**Location**: `src/claude_mpm/agents/PM_INSTRUCTIONS.md:192-477`

**Strengths**:
- ✅ Explicit templates for common decision points (PRWorkflowTemplate, ProjectTypeTemplate, ScopeValidationTemplate)
- ✅ Clear decision tree for WHEN to use structured questions vs. natural language
- ✅ Type-safe question parsing with ResponseParser
- ✅ Context-aware questions (e.g., PRWorkflowTemplate only asks about stacking if num_tickets > 1)

**Example Pattern** (Lines 33-45):
```markdown
### When to Ask User Questions:
**✅ ASK when:**
- Requirements are ambiguous or incomplete
- Multiple valid technical approaches exist (e.g., "main-based vs stacked PRs?")
- User preferences needed (e.g., "draft or ready-for-review PRs?")
- Scope clarification needed (e.g., "should I include tests?")

**❌ DON'T ASK when:**
- Next workflow step is obvious (Research → Implement → Deploy → QA)
- Standard practices apply (always run QA, always verify deployments)
- PM can verify work quality via agents (don't ask "is this good enough?")
- Work is progressing normally (don't ask "should I continue?")
```

**Success Rate Impact**: High (80-85% estimated) - PM has clear guidance on clarification triggers.

---

### 1.2 Scope Protection Protocol (Lines 871-1024)

**Location**: `src/claude_mpm/agents/PM_INSTRUCTIONS.md:871-1024`

**Strengths**:
- ✅ Explicit scope classification matrix (In-Scope, Scope-Adjacent, Out-of-Scope)
- ✅ Mandatory user consultation when scope is unclear (Step 3: Ask User for Scope Decision)
- ✅ ScopeValidationTemplate integration for consistent scope clarification
- ✅ Clear enforcement language ("PM MUST ask user")

**Classification Matrix** (Lines 909-928):
```markdown
✅ In-Scope (Required for Ticket):
- Does this work block the ticket's acceptance criteria?
→ Action: Create subtask under originating ticket

⚠️ Scope-Adjacent (Related but Not Required):
- Is this work related to the ticket but not required?
→ Action: Ask user if they want to expand scope OR defer to backlog

❌ Out-of-Scope (Separate Initiative):
- Is this work unrelated to ticket acceptance criteria?
→ Action: Create separate ticket/epic, do NOT link to originating ticket
```

**Success Rate Impact**: High (85-90% estimated) - Explicit decision tree with enforcement.

---

### 1.3 Circuit Breaker System (Lines 81-160)

**Location**: `src/claude_mpm/agents/PM_INSTRUCTIONS.md:81-160`

**Strengths**:
- ✅ Six circuit breakers for violation detection (Implementation, Investigation, Assertion, etc.)
- ✅ Automatic detection mechanisms that prevent PM from doing work
- ✅ Violation tracking with escalation levels (Warning → Critical → Failure)

**Circuit Breaker #2 - Investigation Detection** (Lines 116-125):
```markdown
### INVESTIGATION VIOLATIONS (NEW - CRITICAL)
❌ Reading multiple files to understand codebase → MUST DELEGATE to Research
❌ Analyzing code patterns or architecture → MUST DELEGATE to Code Analyzer
❌ Searching for solutions or approaches → MUST DELEGATE to Research
```

**Success Rate Impact**: Very High (90-95% estimated) - Prevents PM from premature action.

---

## 2. Critical Gaps Identified

### 2.1 Agent "Research Check" Not Enforced

**Location**: `src/claude_mpm/agents/base_agent.json:6` (line reference from instructions field)

**Current Instruction** (Weak):
```markdown
## Task Execution Protocol
1. **Acknowledge**: Confirm understanding of task, context, and acceptance criteria
2. **Research Check**: If implementation details unclear, request PM delegate research first
3. **Execute**: Perform work within specialization, maintaining audit trails
```

**Problem**: "Research Check" is mentioned as Step 2 but has NO enforcement mechanism.

**Gap Analysis**:
- ❌ No explicit decision tree for "unclear implementation details"
- ❌ No confidence threshold (e.g., "if confidence < 85%, request research")
- ❌ No validation gate - agents can skip directly to Step 3 (Execute)
- ❌ No examples of WHEN research is needed vs. WHEN to proceed

**Impact on Success Rate**: **Critical** - Agents may implement based on ambiguous requirements, leading to rework and failures.

**Evidence of Gap**:
```bash
# Search shows "Research Check" mentioned only once in base_agent.json
# No follow-up enforcement or validation in agent templates
grep -r "Research Check" src/claude_mpm/agents/templates/*.json
# Result: 0 matches in specialized agent templates
```

---

### 2.2 No Clarification Trigger Framework for Agents

**Problem**: While PM has clear "When to Ask" guidance (lines 33-45), agents have NO equivalent framework.

**Current State**:
- ✅ PM: Explicit list of clarification triggers (ambiguous requirements, multiple approaches, etc.)
- ❌ Agents: No systematic guidance on recognizing ambiguity
- ❌ Agents: No "clarification score" or confidence threshold
- ❌ Agents: No examples of ambiguous tasks that require clarification

**Recommended Trigger Framework** (Missing):
```markdown
### Agent Clarification Triggers (MISSING FROM CURRENT INSTRUCTIONS)

**MANDATORY CLARIFICATION when:**
1. **Ambiguous Scope**: Task description lacks acceptance criteria
2. **Multiple Valid Approaches**: 2+ implementation patterns could work
3. **Missing Context**: Key technical details not provided (API endpoints, data schemas, etc.)
4. **Confidence < 85%**: Agent estimates <85% chance of correctness
5. **Impact > Component**: Change affects multiple systems or components
6. **Security/Data Concerns**: Task involves sensitive operations or data

**Example Scenarios**:
❌ "Fix the authentication bug" → Clarify: Which authentication flow? What's the bug behavior?
❌ "Optimize the API" → Clarify: What metrics? What's the target performance?
✅ "Add username field to User model with varchar(100)" → Clear, can proceed
```

**Impact on Success Rate**: **High** - Lack of triggers leads to assumptions and incorrect implementations (estimated 15-20% failure rate).

---

### 2.3 Insufficient Research-First Enforcement

**Location**: `src/claude_mpm/agents/PM_INSTRUCTIONS.md:607-619`

**Current Research-First Pattern**:
```markdown
### DELEGATION-FIRST RESPONSE PATTERNS

**User asks question → PM uses vector search for quick context → Delegates to Research with better scope**
**User reports bug → PM searches for related code → Delegates to QA with specific areas to check**
**User wants feature → PM delegates to Engineer (NEVER implements)**
```

**Gaps**:
1. ❌ No explicit "Research Phase BEFORE Implementation Phase" enforcement
2. ❌ PM can delegate directly to Engineer without Research step (pattern allows it)
3. ❌ No validation that Research findings were reviewed before implementation starts
4. ❌ No "Research Gate" - Engineer can start work before Research completes

**Current Workflow** (Line 1323):
```markdown
START → [DELEGATE Research] → [DELEGATE Code Analyzer] → [DELEGATE Implementation]
```

**Problem**: Arrow notation implies sequence but doesn't ENFORCE it. PM could skip Research if task seems "clear enough."

**Missing Enforcement Example**:
```markdown
### MANDATORY RESEARCH GATE (MISSING)

**BEFORE delegating to Engineer, PM MUST:**
1. ✅ Verify Research phase completed with findings report
2. ✅ Confirm acceptance criteria are clear and measurable
3. ✅ Validate no ambiguities remain (Research flagged none)
4. ✅ Ensure Engineer has all context from Research findings

**PM CANNOT delegate to Engineer if:**
- ❌ Research phase was skipped
- ❌ Research flagged ambiguities without resolution
- ❌ Acceptance criteria are vague or missing
- ❌ Engineer lacks context for informed implementation
```

**Impact on Success Rate**: **Medium-High** - Skipping research leads to incomplete understanding (estimated 10-15% failure rate).

---

### 2.4 Agent Confidence Reporting Not Standardized

**Location**: `src/claude_mpm/agents/base_agent.json` - Task Completion Report format

**Current Report Format** (Lines in base_agent.json instructions):
```markdown
### Reporting Format
## Task Completion Report
**Status**: [Success/Partial/Failed]
**Summary**: [Brief overview of work performed]

### Files Touched
- Created: [list with paths]
- Modified: [list with paths and change types]

### Actions Performed
- [Specific action 1]
- [Specific action 2]

### Unresolved Issues (if any)
- **Error**: [description]
- **Impact**: [how it affects the task]
- **Assistance Required**: [what help is needed]
```

**Missing Elements**:
- ❌ No "Confidence Score" field (e.g., "Confidence: 90% - assumptions stated below")
- ❌ No "Assumptions Made" section (critical for identifying ambiguity gaps)
- ❌ No "Clarifications Needed" section for partial understanding
- ❌ No "Research Findings Used" section to confirm research-first workflow

**Recommended Addition**:
```markdown
### Confidence & Assumptions (MISSING)
**Confidence Score**: 90% (High/Medium/Low)
**Assumptions Made**:
- Assumption 1: API endpoint is RESTful (not GraphQL)
- Assumption 2: Authentication uses JWT tokens
**Clarifications Needed**:
- Clarify: Should error responses follow RFC 7807 format?
- Confirm: Rate limiting strategy (per-user or per-IP)?
**Research Findings Applied**:
- Used Research findings from docs/research/api-patterns-2025-11-23.md
- Validated approach against Code Analyzer recommendations
```

**Impact on Success Rate**: **Medium** - Lack of confidence reporting hides ambiguity (estimated 8-12% failure rate).

---

## 3. Research-First Workflow Analysis

### 3.1 Current Research-First Pattern

**Location**: Multiple references in PM_INSTRUCTIONS.md

**Pattern Identified**:
1. PM receives user request
2. PM uses vector search for quick context (Lines 584-606)
3. PM delegates to Research for deep investigation (Lines 607-619)
4. PM delegates to Code Analyzer for solution review (Workflow Pipeline, Line 1323)
5. PM delegates to Engineer for implementation

**Strengths**:
- ✅ Research phase exists in workflow pipeline
- ✅ PM can use vector search before delegation for context
- ✅ Code Analyzer review before implementation adds validation layer

**Weaknesses**:
- ❌ Research phase is OPTIONAL (PM can skip if task seems clear)
- ❌ No validation that Research was actually consulted before implementation
- ❌ No "Research Findings Review" checkpoint
- ❌ Engineer can start without waiting for Research completion

---

### 3.2 Best Practices from 2025 Research

**Source**: Web search results on research-first AI agent workflows

**Key Findings**:

#### 3.2.1 Two-Mode System (Plan + Act)
**Reference**: Anthropic Building Effective Agents research

**Pattern**:
- **PLAN MODE**: Agent gathers context, asks clarifying questions, brainstorms ideas
- **ACT MODE**: Once clear strategy in place, execute step-by-step

**Current Status in Claude MPM**:
- ⚠️ PM has PLAN elements (vector search, delegation) but no explicit mode separation
- ❌ Agents have NO plan mode - they acknowledge and execute immediately

**Recommendation**: Add explicit PLAN → ACT gate for agents.

---

#### 3.2.2 Escape Hatches for Uncertainty
**Reference**: Lenny's Newsletter - AI Prompt Engineering in 2025

**Pattern**:
> "Prompts now explicitly instruct the LLM to ask for clarification or signal uncertainty as a best practice, known as 'building escape hatches.'"

**Current Status in Claude MPM**:
- ✅ PM has escape hatches (asks for clarification when ambiguous)
- ❌ Agents lack explicit "escape hatch" instructions
- ❌ No agent instruction to "signal uncertainty" with confidence scores

**Recommendation**: Add "uncertainty signaling" to agent instructions.

---

#### 3.2.3 Decomposition Before Execution
**Reference**: Multiple sources on advanced prompt techniques

**Pattern**:
> "Asking a model to first break a problem into sub-problems (decomposition) or critique its own answer (self-criticism) can lead to smarter, more accurate outputs."

**Current Status in Claude MPM**:
- ⚠️ Code Analyzer provides some decomposition (solution review)
- ❌ No explicit agent instruction to decompose tasks before executing
- ❌ No self-criticism step in agent workflow

**Recommendation**: Add "Task Decomposition" step to agent protocol.

---

#### 3.2.4 Workflow-First Design with Agent Flexibility
**Reference**: Microsoft Building AI Agents blog

**Pattern**:
> "The workflow handles 80% of predictable work, while the agent jumps in for the 20% that needs creative reasoning or planning."

**Current Status in Claude MPM**:
- ✅ PM handles workflow orchestration (80% predictable)
- ✅ Agents handle specialized execution (20% creative)
- ✅ Good separation of concerns

**No changes needed** - current architecture aligns with best practice.

---

#### 3.2.5 Context Engineering Over Prompt Engineering
**Reference**: Lakera Prompt Engineering Guide 2025

**Pattern**:
> "Building with language models is becoming less about finding the right words and more about 'what configuration of context is most likely to generate our model's desired behavior?'"

**Current Status in Claude MPM**:
- ✅ PM passes rich context to agents (ticket context, research findings, etc.)
- ✅ Structured context sections in delegation (🎫 TICKET CONTEXT, Requirements, Success Criteria)
- ⚠️ Context format is good but not standardized across all delegations

**Recommendation**: Standardize delegation context template.

---

## 4. Specific Improvement Recommendations

### 4.1 Add Agent Clarification Framework (HIGH PRIORITY)

**Target File**: `src/claude_mpm/agents/base_agent.json` → instructions field

**Add After**: "Task Execution Protocol" section

**Recommended Addition**:
```markdown
## Clarification Framework (MANDATORY)

**BEFORE executing ANY task, agent MUST evaluate clarity:**

### Clarity Checklist (BLOCKING)
1. ✅ **Acceptance Criteria Clear**: Task has measurable success criteria
2. ✅ **Approach Unambiguous**: Single clear implementation path identified
3. ✅ **Context Complete**: All required technical details provided
4. ✅ **Confidence ≥ 85%**: Agent estimates ≥85% chance of correctness
5. ✅ **No Security/Data Unknowns**: Sensitive operations are fully specified

**IF ANY checkbox is ❌, agent MUST:**
1. **STOP** before executing
2. **REQUEST** PM delegate to Research for clarification
3. **DOCUMENT** specific ambiguities in clarification request
4. **WAIT** for Research findings before proceeding

### Clarification Request Template
```
🚫 CLARIFICATION REQUIRED

**Task**: [Original task description]

**Ambiguities Identified**:
1. [Specific ambiguity 1] - Need clarification on [what]
2. [Specific ambiguity 2] - Multiple valid approaches: [list options]

**Questions for Research**:
- Question 1: [Specific question]
- Question 2: [Specific question]

**Confidence Score**: [XX]% (Below 85% threshold)

**Recommendation**: Request PM delegate to Research before implementation.
```

### Examples

**❌ AMBIGUOUS - Requires Clarification**:
- "Fix the authentication bug" → What's the bug? Which flow?
- "Optimize the API" → What metrics? What's acceptable performance?
- "Add user profile" → What fields? What validation rules?

**✅ CLEAR - Can Proceed**:
- "Add 'email' field to User model (varchar(255), unique, not null)"
- "Fix NullPointerException in UserService.login() line 42"
- "Optimize /api/users endpoint to <200ms p95 latency"
```

**Expected Impact**: Reduce ambiguous implementations from ~15-20% to <5% (target 90% success rate).

---

### 4.2 Enforce Research Gate for PM (HIGH PRIORITY)

**Target File**: `src/claude_mpm/agents/PM_INSTRUCTIONS.md`

**Add After**: Line 619 (DELEGATION-FIRST RESPONSE PATTERNS section)

**Recommended Addition**:
```markdown
### 🚦 MANDATORY RESEARCH GATE (NEW)

**CRITICAL**: PM MUST NOT delegate to Engineer without Research validation.

**Research Gate Protocol**:

**STEP 1: Determine if Research is Required**
```
IF task meets ANY criteria:
  - Ambiguous requirements (unclear acceptance criteria)
  - Multiple valid approaches exist
  - Technical unknowns (API details, data schemas, etc.)
  - Complex system (affects >1 component)
  - User said "figure out how" or "investigate"
THEN:
  → Research REQUIRED (proceed to Step 2)
ELSE:
  → Research OPTIONAL (can proceed to Engineer if trivial)
```

**STEP 2: Delegate to Research and Wait**
```
PM: "I'll have Research investigate [specific aspects] before implementation..."
[Delegates to Research with specific investigation scope]
[BLOCKS until Research returns with findings]
```

**STEP 3: Validate Research Findings**
```
PM reviews Research response and verifies:
✅ All ambiguities resolved (Research flagged none remaining)
✅ Acceptance criteria are clear and measurable
✅ Technical approach is validated (no unknowns)
✅ Research provided recommendations or patterns

IF any validation fails:
  → Request additional Research or user clarification
```

**STEP 4: Enhanced Delegation to Engineer**
```
PM to Engineer: "Implement [task] based on Research findings..."

🔬 RESEARCH CONTEXT (from Research Agent):
- Findings: [Key technical findings from Research]
- Recommendations: [Recommended approach]
- Patterns: [Relevant codebase patterns identified]
- Acceptance Criteria: [Clear, measurable criteria from Research]

Requirements:
[PM's specific implementation requirements]

Success Criteria:
[How PM will verify completion]
```

**VIOLATION TRACKING**:
- ❌ PM delegates to Engineer without Research when task is ambiguous = VIOLATION
- ❌ PM skips Research validation step = VIOLATION
- ❌ Engineer starts implementation before Research completes = VIOLATION

**Circuit Breaker #7: Research Gate Violation**
```
IF PM delegates to Engineer AND:
   - Task was ambiguous (met Step 1 criteria)
   - Research was NOT delegated first
   - Research findings NOT referenced in Engineer delegation
THEN:
   → VIOLATION: Research Gate Bypassed
   → ESCALATION: Display warning to user
   → REMEDIATION: PM must delegate to Research before continuing
```
```

**Expected Impact**: Ensure 85-90% of implementations have validated requirements before starting.

---

### 4.3 Standardize Agent Confidence Reporting (MEDIUM PRIORITY)

**Target File**: `src/claude_mpm/agents/base_agent.json` → instructions field

**Modify**: "Mandatory PM Reporting" section → "Required Reporting Elements"

**Add After**: "Error Escalation" (item #5)

**Recommended Addition**:
```markdown
6. **Confidence & Assumptions**: Agent's confidence in correctness and any assumptions made:
   - Confidence Score: XX% (High ≥90%, Medium 70-89%, Low <70%)
   - Assumptions: List of assumptions made during execution
   - Clarifications: Open questions or ambiguities that remain
   - Research Used: Reference to research findings applied (if applicable)
```

**Update Reporting Format**:
```markdown
### Reporting Format
```
## Task Completion Report
**Status**: [Success/Partial/Failed]
**Confidence**: [XX]% (High/Medium/Low)
**Summary**: [Brief overview of work performed]

### Confidence & Assumptions
**Confidence Score**: 90% (High)
**Assumptions Made**:
- Assumption 1: [Specific assumption with rationale]
- Assumption 2: [Specific assumption with rationale]
**Clarifications Needed** (if confidence < 85%):
- Clarify: [Open question 1]
- Confirm: [Open question 2]
**Research Findings Applied**:
- Used findings from: [Research document or agent response]
- Validated approach: [How research informed implementation]

### Files Touched
[... rest of report ...]
```
```

**Expected Impact**: Surface confidence levels early, allowing PM to catch low-confidence implementations (<70%) before deployment.

---

### 4.4 Add Task Decomposition Step for Agents (MEDIUM PRIORITY)

**Target File**: `src/claude_mpm/agents/base_agent.json` → instructions field

**Modify**: "Task Execution Protocol" section

**Current Protocol** (5 steps):
```markdown
1. Acknowledge
2. Research Check
3. Execute
4. Validate
5. Report
```

**Recommended Protocol** (6 steps with decomposition):
```markdown
## Task Execution Protocol

1. **Acknowledge**: Confirm understanding of task, context, and acceptance criteria

2. **Research Check**: If implementation details unclear, request PM delegate research first
   - Evaluate clarity using Clarification Framework (see below)
   - If confidence < 85%, STOP and request clarification

3. **Decompose** (NEW): Break task into sub-tasks and validate approach
   - **Decomposition**: List 3-7 sub-tasks with clear dependencies
   - **Approach Validation**: Verify sub-tasks satisfy acceptance criteria
   - **Risk Assessment**: Identify blockers or high-risk sub-tasks
   - **Self-Criticism**: Challenge assumptions and identify edge cases

4. **Execute**: Perform work within specialization, maintaining audit trails
   - Execute sub-tasks sequentially or in parallel based on dependencies
   - Document progress and decisions for each sub-task

5. **Validate**: Verify outputs meet acceptance criteria and quality standards
   - Check each sub-task completion against acceptance criteria
   - Run self-validation tests or checks

6. **Report**: Provide structured completion report with deliverables and next steps
   - Include confidence score and assumptions (see Reporting Format)
```

**Decomposition Template**:
```markdown
## Task Decomposition

**Task**: [Original task description]

**Sub-Tasks**:
1. [Sub-task 1] (Est: 10 min) → Dependencies: None
2. [Sub-task 2] (Est: 15 min) → Dependencies: Sub-task 1
3. [Sub-task 3] (Est: 20 min) → Dependencies: Sub-task 1, 2
4. [Sub-task 4] (Est: 5 min) → Dependencies: Sub-task 3

**Approach Validation**:
✅ All sub-tasks mapped to acceptance criteria
✅ No missing steps identified
✅ Sequence is logical and efficient

**Risk Assessment**:
⚠️ Sub-task 3 may require [external dependency/clarification]
✅ Sub-tasks 1,2,4 have low risk

**Self-Criticism**:
- Challenge: Is Sub-task 2 really necessary? → Yes, required for [reason]
- Edge Case: What if [edge case]? → Handled in Sub-task 4
```

**Expected Impact**: Improve task execution quality by 10-15% through systematic decomposition and self-validation.

---

### 4.5 Standardize Delegation Context Template (LOW-MEDIUM PRIORITY)

**Target File**: `src/claude_mpm/agents/PM_INSTRUCTIONS.md`

**Add After**: Line 725 (Pass ticket context to delegated agent section)

**Recommended Addition**:
```markdown
### 📋 STANDARDIZED DELEGATION TEMPLATE (NEW)

**ALL PM delegations to agents MUST use this consistent format:**

```
Task: [Clear, concise task description in imperative form]

🎯 CONTEXT:
- Originating Request: [User's original request]
- Work Type: [Feature/Bug Fix/Optimization/Research/etc.]
- Priority: [High/Medium/Low based on ticket or user urgency]

🎫 TICKET CONTEXT (if applicable):
- Ticket ID: [TICKET-123]
- Title: [Ticket title]
- Description: [Key details from ticket]
- Acceptance Criteria: [Clear, measurable criteria]
- Tags: [Relevant tags]

🔬 RESEARCH CONTEXT (if applicable):
- Research Findings: [Key findings from Research agent]
- Recommended Approach: [Research-validated approach]
- Relevant Patterns: [Codebase patterns identified]
- Constraints: [Technical constraints or limitations]

📝 REQUIREMENTS:
1. [Specific requirement 1]
2. [Specific requirement 2]
3. [Specific requirement 3]

✅ SUCCESS CRITERIA:
- Criterion 1: [Measurable success criterion]
- Criterion 2: [Measurable success criterion]

🚦 ACCEPTANCE:
Your work is complete when:
- [ ] All requirements satisfied
- [ ] All success criteria met
- [ ] Tests pass (if applicable)
- [ ] Documentation updated (if code changes)

⚠️ CONSTRAINTS:
- Time: [If time-sensitive]
- Scope: [What's explicitly out of scope]
- Dependencies: [Other agents or systems this depends on]
```
```

**Template Usage Rules**:
- 🎯 CONTEXT: ALWAYS include
- 🎫 TICKET CONTEXT: MANDATORY if ticket-based work
- 🔬 RESEARCH CONTEXT: MANDATORY if Research phase completed
- 📝 REQUIREMENTS: ALWAYS include (minimum 1)
- ✅ SUCCESS CRITERIA: ALWAYS include (minimum 1, must be measurable)
- 🚦 ACCEPTANCE: ALWAYS include (checklist format)
- ⚠️ CONSTRAINTS: Include if applicable

**Benefits**:
- Agents receive consistent, structured context
- No information gaps or ambiguity
- Clear success criteria prevent scope creep
- Research findings always propagated to implementation
```

**Expected Impact**: Reduce delegation ambiguity by 15-20% through consistent context structure.

---

## 5. Success Metrics and Validation

### 5.1 Target Success Rates (90% Overall Goal)

**Current Estimated Success Rates** (Based on Gap Analysis):
- PM Delegation Success: 85% (good, needs minor improvement)
- Agent Clarification Success: 65% (critical gap - agents proceed without clarification)
- Research-First Compliance: 75% (medium gap - PM sometimes skips research)
- Confidence Reporting: 60% (medium gap - no standardized confidence scores)
- Task Decomposition: 70% (medium gap - agents don't systematically decompose)

**Target Success Rates** (After Improvements):
- PM Delegation Success: 92% (+7%)
- Agent Clarification Success: 90% (+25%) ← **BIGGEST IMPROVEMENT**
- Research-First Compliance: 88% (+13%)
- Confidence Reporting: 85% (+25%)
- Task Decomposition: 85% (+15%)

**Overall Estimated Success Rate**: 88-90% (meets 90% target)

---

### 5.2 Validation Checkpoints

**Checkpoint 1: Agent Clarification Framework (Week 1-2)**
- Metric: % of ambiguous tasks that trigger clarification request
- Target: 90% of tasks with confidence <85% must trigger clarification
- Validation: Review agent responses for "🚫 CLARIFICATION REQUIRED" blocks

**Checkpoint 2: Research Gate Enforcement (Week 2-3)**
- Metric: % of ambiguous implementations that include Research phase
- Target: 85% of Engineer delegations must reference Research findings (when task was ambiguous)
- Validation: Audit PM delegation messages for "🔬 RESEARCH CONTEXT" section

**Checkpoint 3: Confidence Reporting (Week 3-4)**
- Metric: % of agent reports that include confidence scores
- Target: 95% of agent completion reports must include "Confidence: XX%" field
- Validation: Parse agent responses for "## Confidence & Assumptions" section

**Checkpoint 4: Task Decomposition (Week 4-5)**
- Metric: % of complex tasks (>3 sub-steps) that include decomposition
- Target: 80% of complex tasks must show "## Task Decomposition" section
- Validation: Review agent responses for decomposition blocks before execution

**Checkpoint 5: Overall Success Rate (Week 6)**
- Metric: % of tasks completed without requiring rework due to ambiguity
- Target: 90% of tasks complete successfully on first attempt
- Validation: User feedback + rework rate analysis

---

## 6. Implementation Priority Matrix

### Priority 1: CRITICAL (Implement First) ← **START HERE**
1. **Agent Clarification Framework** (Section 4.1)
   - **Impact**: Very High (addresses 65% → 90% gap)
   - **Effort**: Medium (add ~100 lines to base_agent.json)
   - **Risk**: Low (well-defined additions)
   - **Timeline**: Week 1-2

2. **Research Gate Enforcement** (Section 4.2)
   - **Impact**: High (addresses 75% → 88% gap)
   - **Effort**: Medium-High (add ~150 lines + circuit breaker logic)
   - **Risk**: Medium (changes PM workflow)
   - **Timeline**: Week 2-3

### Priority 2: HIGH (Implement Second)
3. **Agent Confidence Reporting** (Section 4.3)
   - **Impact**: Medium-High (addresses 60% → 85% gap)
   - **Effort**: Low-Medium (modify existing reporting format)
   - **Risk**: Low (additive changes)
   - **Timeline**: Week 3

4. **Task Decomposition** (Section 4.4)
   - **Impact**: Medium (addresses 70% → 85% gap)
   - **Effort**: Medium (add ~80 lines to base_agent.json)
   - **Risk**: Low (optional enhancement)
   - **Timeline**: Week 4

### Priority 3: MEDIUM (Implement Third)
5. **Standardize Delegation Template** (Section 4.5)
   - **Impact**: Medium (reduces delegation ambiguity by 15-20%)
   - **Effort**: Low (documentation + examples)
   - **Risk**: Very Low (template recommendation)
   - **Timeline**: Week 5

---

## 7. Detailed File Modifications

### 7.1 Modifications to base_agent.json

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/base_agent.json`

**Line**: After "Task Execution Protocol" section (approx line 6 in instructions field)

**Add**:
1. **Clarification Framework** (Section 4.1 content) - ~120 lines
2. **Task Decomposition Step** (Section 4.4 content) - ~80 lines
3. **Updated Reporting Format** (Section 4.3 content) - ~40 lines

**Total Addition**: ~240 lines to instructions field

---

### 7.2 Modifications to PM_INSTRUCTIONS.md

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/PM_INSTRUCTIONS.md`

**Location 1**: After line 619 (DELEGATION-FIRST RESPONSE PATTERNS)
**Add**: Research Gate Protocol (Section 4.2 content) - ~150 lines

**Location 2**: After line 725 (Pass ticket context to delegated agent)
**Add**: Standardized Delegation Template (Section 4.5 content) - ~60 lines

**Total Addition**: ~210 lines

---

### 7.3 Testing Strategy

**Phase 1: Unit Testing (Week 1-2)**
- Test Agent Clarification Framework with intentionally ambiguous tasks
- Verify agents trigger "🚫 CLARIFICATION REQUIRED" block
- Validate clarification request template format

**Phase 2: Integration Testing (Week 2-3)**
- Test Research Gate with end-to-end workflows
- Verify PM delegates to Research before Engineer (when required)
- Validate Research findings propagate to Engineer delegation

**Phase 3: Confidence Reporting Testing (Week 3)**
- Verify all agent reports include "Confidence: XX%" field
- Test confidence threshold triggers (< 85% should flag)
- Validate assumptions section completeness

**Phase 4: Decomposition Testing (Week 4)**
- Test task decomposition with complex multi-step tasks
- Verify sub-task sequencing and dependency tracking
- Validate approach validation and self-criticism sections

**Phase 5: End-to-End Success Rate (Week 6)**
- Measure overall success rate across 50-100 test tasks
- Track rework rate due to ambiguity or incomplete requirements
- Validate 90% target success rate achieved

---

## 8. Risks and Mitigations

### Risk 1: Over-Clarification (False Positives)
**Risk**: Agents trigger clarification for clear tasks, slowing workflow.

**Mitigation**:
- Set confidence threshold at 85% (not higher) to avoid over-triggering
- Provide clear examples of tasks that DON'T need clarification
- Track false positive rate and adjust threshold if > 10%

**Monitoring**: Measure % of clarification requests that user deems unnecessary.

---

### Risk 2: PM Resistance to Research Gate
**Risk**: PM may feel "slowed down" by mandatory Research phase.

**Mitigation**:
- Emphasize Research Gate only applies to AMBIGUOUS tasks (not trivial ones)
- Show productivity gains from reduced rework (fewer failed implementations)
- Track time saved from avoided rework vs. time spent on Research

**Monitoring**: Measure rework rate before/after Research Gate implementation.

---

### Risk 3: Increased Token Usage
**Risk**: Clarification requests and decomposition add token overhead.

**Mitigation**:
- Clarification + decomposition estimated at +15-20% tokens per task
- Offset by reduced rework (avoid failed implementations)
- Research phase may catch issues before expensive implementation failures

**Monitoring**: Track token usage per task before/after changes.

---

### Risk 4: Agent Non-Compliance
**Risk**: Agents ignore clarification framework and proceed anyway.

**Mitigation**:
- Add Circuit Breaker #8 for Agent Clarification Bypass (detects missing confidence scores)
- PM-side validation: If agent response lacks confidence score, PM requests re-submission
- Gradually increase enforcement strictness over time

**Monitoring**: Audit agent responses for compliance with clarification framework.

---

## 9. References

### Internal Documentation
1. `src/claude_mpm/agents/PM_INSTRUCTIONS.md` (Lines 1-2035)
2. `src/claude_mpm/agents/base_agent.json` (Instructions field)
3. `src/claude_mpm/agents/templates/research.json` (Research agent template)

### External Research Sources
1. **Anthropic - Building Effective Agents** (2025)
   - URL: https://www.anthropic.com/research/building-effective-agents
   - Key Insight: Two-mode system (PLAN + ACT) improves task success

2. **Anthropic - Effective Context Engineering for AI Agents** (2025)
   - URL: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
   - Key Insight: Context engineering > prompt engineering for 2025

3. **Lenny's Newsletter - AI Prompt Engineering in 2025** (Sander Schulhoff)
   - URL: https://www.lennysnewsletter.com/p/ai-prompt-engineering-in-2025-sander-schulhoff
   - Key Insight: "Escape hatches" for uncertainty signaling

4. **Microsoft - Building AI Agents: Workflow-First vs. Code-First** (2025)
   - URL: https://techcommunity.microsoft.com/blog/azurearchitectureblog/building-ai-agents-workflow-first-vs-code-first-vs-hybrid/4466788
   - Key Insight: Hybrid approach (80% workflow, 20% agent flexibility)

5. **Lakera - The Ultimate Guide to Prompt Engineering in 2025** (2025)
   - URL: https://www.lakera.ai/blog/prompt-engineering-guide
   - Key Insight: Decomposition and self-criticism unlock better performance

6. **GitHub Blog - How to Build Reliable AI Workflows** (2025)
   - URL: https://github.blog/ai-and-ml/github-copilot/how-to-build-reliable-ai-workflows-with-agentic-primitives-and-context-engineering/
   - Key Insight: Agentic primitives + context engineering for reliability

---

## 10. Conclusion

This research identifies **four critical gaps** in current instruction patterns that prevent achieving 90% success rate:

1. **Agent Clarification Framework** (CRITICAL): Agents lack systematic guidance on recognizing ambiguity and requesting clarification before implementation.

2. **Research Gate Enforcement** (HIGH): PM can skip Research phase for ambiguous tasks, leading to implementations based on incomplete understanding.

3. **Confidence Reporting** (MEDIUM): Agents don't report confidence scores, hiding low-confidence implementations that may need validation.

4. **Task Decomposition** (MEDIUM): Agents don't systematically decompose tasks before executing, missing self-validation opportunities.

**Recommended Implementation Order**:
1. Week 1-2: Agent Clarification Framework (biggest impact)
2. Week 2-3: Research Gate Enforcement (second biggest impact)
3. Week 3: Confidence Reporting (enables monitoring)
4. Week 4: Task Decomposition (improves execution quality)
5. Week 5: Standardize Delegation Template (reduces ambiguity)
6. Week 6: Validate 90% success rate target

**Expected Outcome**: Increase overall instruction success rate from estimated **~72-75%** to **88-90%**, meeting the 90% target for ticket 1M-163.

---

## Appendix A: Example Clarification Scenarios

### Scenario 1: Ambiguous Authentication Task

**User Request**: "Fix the authentication bug"

**Current Behavior** (No Clarification Framework):
- Agent proceeds to investigate authentication code
- Agent makes assumptions about which bug (login? logout? token refresh?)
- Agent implements fix for wrong issue
- Result: Rework required, user frustration

**Expected Behavior** (With Clarification Framework):
```
🚫 CLARIFICATION REQUIRED

**Task**: Fix the authentication bug

**Ambiguities Identified**:
1. Multiple authentication flows exist (login, logout, token refresh, OAuth)
2. "Bug" not specified - Could be security issue, UX issue, or functional issue
3. No reproduction steps provided

**Questions for Research**:
- Which authentication flow is affected? (login/logout/token/OAuth)
- What is the observed bug behavior?
- What is the expected behavior?
- Are there reproduction steps or error logs?

**Confidence Score**: 40% (Below 85% threshold)

**Recommendation**: Request PM delegate to Research to clarify bug scope before implementation.
```

**PM Response**: Delegates to Research or asks user for clarification.

**Outcome**: Implementation starts with clear requirements, avoiding rework.

---

### Scenario 2: Clear Implementation Task

**User Request**: "Add 'email' field to User model (varchar(255), unique, not null, with email validation)"

**Current Behavior**: Agent proceeds (task is clear).

**Expected Behavior** (With Clarification Framework):
- Agent evaluates clarity checklist
- All criteria met (✅ acceptance criteria clear, ✅ approach unambiguous, ✅ confidence ≥ 85%)
- Agent proceeds directly to decomposition and execution
- No clarification needed

**Outcome**: No false positive, workflow not slowed.

---

## Appendix B: Research Gate Example Workflow

### Example: "Optimize API Performance" Request

**Without Research Gate** (Current):
```
User: "Optimize the /users API endpoint"
PM: "I'll delegate to Engineer to optimize the endpoint"
Engineer: *Optimizes database query based on assumptions*
Result: Performance improves 20% (but target was 50%), rework needed
```

**With Research Gate** (Proposed):
```
User: "Optimize the /users API endpoint"

PM: "I'll have Research investigate performance bottlenecks first..."
[Delegates to Research]

Research: "Analyzed /users endpoint. Bottlenecks:
1. N+1 query problem (fetching related data)
2. Missing index on users.created_at
3. Response payload includes 50 fields (only 10 used)
Recommendations:
- Add eager loading for related data
- Create composite index
- Implement field filtering
Target: Reduce p95 latency from 800ms to <200ms"

PM: "I'll delegate to Engineer based on Research findings..."
[Delegates to Engineer with Research context]

Engineer: *Implements all 3 optimizations*
Result: Performance improves 70% (exceeds target), no rework needed
```

**Outcome**: Research phase identifies ALL bottlenecks, Engineer implements comprehensive solution, target exceeded on first attempt.

---

**End of Research Document**

---

**Next Steps for Ticket 1M-163**:
1. Review findings with PM and user
2. Prioritize recommendations (Section 6)
3. Implement Agent Clarification Framework (Section 4.1)
4. Implement Research Gate Enforcement (Section 4.2)
5. Deploy and validate improvements
6. Measure success rate against 90% target
