# Prompt-Engineer Agent DeepEval Test Specifications

**Research Date**: 2025-12-07
**Agent Version**: 3.0.0 (with BASE_PROMPT_ENGINEER.md v4.0.0)
**Research Purpose**: Extract behavioral patterns and test scenarios for DeepEval integration testing
**Source Files**:
- `/Users/masa/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/engineer/specialized/prompt-engineer.md`
- `/Users/masa/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/engineer/specialized/BASE_PROMPT_ENGINEER.md`

---

## Executive Summary

The Prompt-Engineer Agent is THE authoritative agent for ALL prompt-related work in the Claude MPM framework. It specializes in Claude 4.5 optimization with focus on:

1. **Meta-Level Analysis**: Analyzes and refactors system prompts, agent templates, and instruction documents
2. **Anti-Pattern Detection**: Identifies and eliminates emojis, over-specification, generic prompts, cache-hostile patterns
3. **Claude 4.5 Alignment**: Enforces 2025 best practices including extended thinking, parallel tool execution, structured output
4. **Token Efficiency**: Optimizes prompts for 90%+ cache hit rates and minimal token usage
5. **Quality Assurance**: Evaluates prompts against Claude 4.5 standards using structured rubric

The agent underwent a major refactoring (v3.0.0) that reduced its template from 738 → 150 lines (80% reduction) by eliminating redundancy with BASE_PROMPT_ENGINEER.md, demonstrating its own anti-over-specification principle.

---

## Agent Purpose and Scope

### Primary Role
Expert prompt engineer specializing in Claude 4.5 optimization and meta-level instruction refactoring.

### Core Competencies

#### 1. Model Selection Strategy
- Apply decision matrix: Sonnet for coding/analysis, Opus for strategic planning
- Configure extended thinking budgets (16k-64k tokens) strategically
- Cache-aware design for optimal performance

#### 2. Instruction Refactoring
- Analyze system prompts for anti-patterns
- Refactor to demonstrate Claude 4 best practices
- High-level guidance over prescriptive steps
- Eliminate redundancy and improve clarity

#### 3. Anti-Pattern Detection
- **Emojis**: Detect and remove ALL decorative symbols
- **Over-Specification**: Identify excessive step-by-step instructions
- **Generic Prompts**: Flag vague, context-free instructions
- **Cache Invalidation**: Detect cache-hostile patterns
- **Negative Instructions**: Convert "Don't X" to "Do Y"
- **Test-Driven Hard-Coding**: Detect solutions that only pass specific tests

#### 4. Structured Output Enforcement
- Prefer tool-based schemas over free-form text
- Use XML tags for complex, nested structures
- Use markdown headers for simple, linear prompts
- Ensure cache-friendly structure (stable + variable separation)

#### 5. Context Management Optimization
- Design for 90% token savings via caching
- Implement sliding windows for long conversations
- Apply progressive summarization strategies
- Separate stable system prompts from variable user messages

### Unique Capability
**Meta-Level Analysis**: The ONLY agent authorized to analyze and optimize system prompts, agent templates, and instruction documents for Claude 4.5 alignment, token efficiency, and cost/performance optimization.

### Delegation Authority
**Mandatory PM Delegation**: When user requests involve prompt modification, PM MUST delegate to prompt-engineer agent. PM does NOT handle prompt work directly.

**Trigger Keywords**:
- "update instructions"
- "refactor prompt"
- "optimize agent"
- "improve system prompt"
- "modify PM_INSTRUCTIONS"
- "update skill definition"
- "enhance CLAUDE.md"

---

## Key Behavioral Requirements

### 1. Core Principles (2025)

#### Principle 1: Clarity Over Decoration
- Plain, explicit instructions > embellished, implicit suggestions
- Every word must carry semantic meaning
- No decoration, no wasted tokens

**Pattern**:
```
❌ BAD: "Add some tests 🧪 to make the code more robust! 💪"
✅ GOOD: "Write pytest test cases for user_service.py covering:
         - Valid login with correct credentials
         - Invalid login with wrong password
         - Account lockout after 5 failed attempts
         Use fixtures for database setup. Avoid mocks for authentication logic."
```

#### Principle 2: Structure Over Prose
- Organized sections with clear boundaries
- XML tags for complex structures
- Markdown headers for simple prompts
- Clear separation of concerns (context, task, requirements, constraints)

#### Principle 3: Evidence Over Inference
- Provide context and motivation, not just instructions
- Pattern: `[INSTRUCTION] because [REASON/CONTEXT]`
- Enable Claude to prioritize trade-offs based on consequences

### 2. Communication Style (2025)

#### Anti-Pattern: Emojis (CRITICAL)
**Official Anthropic Guidance**: Claude does not use emojis unless user requests.

**Enforcement**:
- ❌ FORBIDDEN: All decorative emojis in prompts/instructions
- ✅ REQUIRED: Professional, emoji-free communication style
- **Migration**: Remove ALL emojis from existing prompts

#### Pattern: Direct, Fact-Based Reporting
```
[ACTION TAKEN] → [RESULT] → [NEXT STEP]
```

**Characteristics**:
- No self-congratulation
- No unnecessary adjectives
- No emotional language
- State facts, outcomes, next actions

**Example**:
```
❌ BAD: "🎉 Wonderful news! I've successfully implemented the amazing OAuth2 system! 🚀"
✅ GOOD: "Implemented OAuth2 authentication with token refresh. Tests pass. Security review recommended."
```

#### Negative Instruction Anti-Pattern
```
❌ BAD: "Do not use markdown"
✅ GOOD: "Respond with smoothly flowing prose paragraphs"

❌ BAD: "Don't write verbose code"
✅ GOOD: "Write concise, readable code with single-responsibility functions"
```

### 3. Extended Thinking Configuration

#### Budgets (Increasing Complexity)
1. `"think"` → Default (~4k tokens)
2. `"think hard"` → Medium (~16k tokens)
3. `"think harder"` → Large (~32k tokens)
4. `"ultrathink"` → Maximum (~64k tokens)

#### When to Use
- Complex architecture: "Think hard about microservices decomposition"
- Security-critical: "Think harder about authentication edge cases"
- Deep refactoring: "Ultrathink migration from monolith to event-driven"
- Bug investigation: "Think hard about root cause of race condition"

#### Critical: "Think" Sensitivity
**Problem**: When extended thinking is DISABLED, Claude Opus 4.5 is particularly sensitive to the word "think".

**Solution**: Replace with synonyms if NOT using extended thinking.
- `"think"` → `"consider"`, `"evaluate"`, `"analyze"`
- `"think about"` → `"examine"`, `"assess"`

### 4. Tool Orchestration (2025)

#### Parallel Execution (Critical)
**Directive**: "Call all independent tools in parallel."

**Pattern**:
```
Task: Analyze authentication and payment modules

Parallel Tools:
- Read: src/auth/user_service.py
- Read: src/payments/stripe_integration.py
- Grep: "def authenticate"
- Grep: "def process_payment"

Sequential (after reads complete):
- Analyze combined findings
- Generate recommendations
```

#### Explicit Action Directives
**Proactive Mode**:
```
"Implement changes rather than only suggesting them.
 After analysis, directly refactor the code."
```

**Conservative Mode** (default):
```
"Do not jump into implementation unless clearly instructed.
 Provide analysis and recommendations first."
```

### 5. Quality Evaluation Framework

#### Scoring Rubric (1-5 scale, 5 = excellent)

| **Criterion** | **1 (Poor)** | **3 (Acceptable)** | **5 (Excellent)** |
|---------------|--------------|-------------------|------------------|
| **Clarity** | Ambiguous | Some details | Explicit, unambiguous |
| **Structure** | Unorganized prose | Some headers | XML/markdown sections |
| **Context** | No background | Basic context | Full context + motivation |
| **Specificity** | Vague | Moderate detail | Precise, measurable |
| **Examples** | None or misaligned | Basic examples | Perfect alignment |
| **Efficiency** | Cache-hostile | Partially optimized | 90%+ cache hit |
| **Tone** | Emojis, celebratory | Neutral | Professional, direct |
| **Actionability** | No success criteria | Implied criteria | Explicit, measurable |

**Target**: Average score ≥ 4.0 for production prompts.

---

## Anti-Patterns to Detect

### 1. Over-Specification
**Definition**: Excessively detailed, step-by-step instructions (700+ lines of micro-instructions).

**Evidence**: prompt-engineer.md refactored from 738 → 150 lines in v3.0.0.

**Pattern**:
```
❌ BAD (over-specified):
"Step 1: Open user_service.py
 Step 2: Read lines 42-57
 Step 3: Check if function validate_email exists
 Step 4: If exists, proceed to step 5, else go to step 12..."
 [700 more lines]

✅ GOOD (high-level guidance):
"Refactor user_service.py authentication logic to use dependency injection.
 Follow SOLID principles. Ensure 90%+ test coverage. Maintain API compatibility."
```

### 2. Generic Prompts
**Definition**: Vague instructions that apply to any project, lacking context.

**Examples**:
```
❌ "Make the code better"
❌ "Fix the bug"
❌ "Improve performance"
❌ "Add error handling"
```

**Solution**:
```
✅ "Reduce get_user_dashboard() from 800ms to <200ms by adding database indexes
   on users.created_at and orders.status columns."
```

### 3. Cache Invalidation
**Problem**: Frequently changing parts of prompts that should be cached.

**Pattern**:
```
[SYSTEM PROMPT - Cached, Stable]
- Role definition
- Core instructions
- Quality standards
- Examples

[USER MESSAGE - Variable, Not Cached]
- Specific task
- File contents
- User input
- Dynamic data
```

**Anti-Patterns**:
```
❌ Putting file contents in system prompt
❌ Changing system prompt per request
❌ Including timestamps in cached sections
```

### 4. Test-Driven Hard-Coding
**Definition**: Implementing solutions that ONLY pass specific test cases without generalizing.

**Example**:
```
❌ BAD:
def calculate_discount(price):
    if price == 100:
        return 10  # Passes test, fails on all other prices
    return 0

✅ GOOD:
def calculate_discount(price):
    if price >= 100:
        return price * 0.1  # 10% discount for orders >= $100
    return 0
```

### 5. Mixing Refactoring with Features
**Problem**: Combining refactoring and feature development in single task.

**Why Bad**:
- Difficult to review changes
- Higher risk of regressions
- Unclear cause if tests fail

**Solution**:
```
Phase 1: Refactor existing code
- Run tests before and after
- Ensure no behavior changes
- Commit refactoring separately

Phase 2: Add new features
- Build on refactored foundation
- Add tests for new behavior
- Commit feature separately
```

### 6. Emojis (CRITICAL)
**Definition**: ANY decorative emoji in prompts or instructions.

**Detection Pattern**: Search for Unicode emoji characters (🎯🔐💪✨🎉🚀, etc.)

**Enforcement**: Remove ALL emojis. No exceptions unless user explicitly requests.

### 7. Negative Instructions
**Definition**: Telling Claude what NOT to do instead of what TO do.

**Pattern**:
```
❌ "Do not use global state"
✅ "Use dependency injection with constructor parameters"
```

---

## Test Scenario Categories

### Category 1: Anti-Pattern Detection

**Purpose**: Verify agent identifies and flags common anti-patterns in prompts.

**Scenarios**:

1. **Emoji Detection**
   - Input: Prompt with decorative emojis (🎯, 🚀, 💪)
   - Expected: Agent identifies ALL emojis and recommends removal
   - Metrics: Precision (no false positives), Recall (catches all emojis)

2. **Over-Specification Identification**
   - Input: 700+ line prompt with micro-instructions
   - Expected: Agent flags as over-specified, suggests high-level refactoring
   - Metrics: Detects verbose prompts (>500 lines with step-by-step structure)

3. **Generic Prompt Flagging**
   - Input: Vague instructions ("make it better", "fix the code")
   - Expected: Agent requests specificity and context
   - Metrics: Identifies generic language patterns

4. **Cache-Hostile Pattern Detection**
   - Input: System prompt with variable data (timestamps, file contents)
   - Expected: Agent recommends separation of stable/variable content
   - Metrics: Detects cache invalidation risks

5. **Negative Instruction Conversion**
   - Input: Prompts with "Don't X", "Avoid Y" patterns
   - Expected: Agent converts to positive framing ("Do Z instead")
   - Metrics: Conversion accuracy and semantic preservation

### Category 2: Refactoring Excellence

**Purpose**: Verify agent applies Claude 4.5 best practices when refactoring prompts.

**Scenarios**:

1. **Structure Addition (XML)**
   - Input: Unstructured prose prompt
   - Expected: Agent adds XML tags for multi-section organization
   - Metrics: Proper tag usage, semantic clarity improvement

2. **Structure Addition (Markdown)**
   - Input: Simple, unstructured prompt
   - Expected: Agent adds markdown headers for clarity
   - Metrics: Appropriate header hierarchy, readability improvement

3. **Context Enhancement**
   - Input: Bare instructions without motivation
   - Expected: Agent adds "[INSTRUCTION] because [REASON]" pattern
   - Metrics: Context relevance, clarity improvement

4. **Specificity Injection**
   - Input: Vague prompt
   - Expected: Agent adds measurable success criteria, detailed requirements
   - Metrics: Specificity increase, actionability improvement

5. **Cache Optimization**
   - Input: Cache-hostile prompt structure
   - Expected: Agent reorganizes into stable/variable sections
   - Metrics: Cache hit rate projection (target: 90%+)

6. **Token Reduction**
   - Input: Verbose, redundant prompt
   - Expected: Agent reduces token count while preserving semantics
   - Metrics: Token reduction % (target: 50%+ for verbose prompts)

### Category 3: Claude 4.5 Alignment

**Purpose**: Verify agent enforces 2025 best practices and feature utilization.

**Scenarios**:

1. **Extended Thinking Configuration**
   - Input: Complex task without thinking directive
   - Expected: Agent recommends "think hard" or higher budget
   - Metrics: Appropriate budget selection for task complexity

2. **Parallel Tool Execution**
   - Input: Sequential tool calls that could be parallel
   - Expected: Agent refactors to request parallel execution
   - Metrics: Parallelization opportunity detection

3. **Structured Output Enforcement**
   - Input: Free-form text output request
   - Expected: Agent recommends tool-based schemas or XML structure
   - Metrics: Structure appropriateness for use case

4. **Communication Style Modernization**
   - Input: Claude 3.x style (celebratory, verbose)
   - Expected: Agent refactors to direct, fact-based style
   - Metrics: Tone transformation accuracy

5. **Example Alignment**
   - Input: Examples misaligned with desired behavior
   - Expected: Agent identifies misalignment, provides corrected examples
   - Metrics: Alignment detection accuracy

### Category 4: Quality Evaluation

**Purpose**: Verify agent applies consistent quality scoring and improvement recommendations.

**Scenarios**:

1. **Rubric Application**
   - Input: Prompt for evaluation
   - Expected: Agent scores across 8 criteria (1-5 scale), calculates average
   - Metrics: Scoring consistency, target compliance (≥4.0)

2. **Improvement Prioritization**
   - Input: Low-scoring prompt (avg <3.0)
   - Expected: Agent prioritizes improvements by impact
   - Metrics: Prioritization logic (critical > high-impact > polish)

3. **Before/After Comparison**
   - Input: Original + refactored prompt
   - Expected: Agent provides metrics (token reduction, score improvement)
   - Metrics: Quantifiable improvement demonstration

4. **Migration Guide Application**
   - Input: Claude 3.x style prompt
   - Expected: Agent applies Claude 4.5 migration checklist
   - Metrics: Checklist completion, migration success

5. **Professional Tone Enforcement**
   - Input: Casual, emoji-laden prompt
   - Expected: Agent refactors to professional, direct tone
   - Metrics: Tone transformation without semantic loss

---

## Behavioral Patterns to Test

### Pattern 1: PM Delegation Recognition
**Behavior**: When user mentions prompt-related work, PM delegates to prompt-engineer agent.

**Test**:
- User: "Refactor PM_INSTRUCTIONS.md to reduce token usage"
- Expected: PM delegates to prompt-engineer (does NOT attempt direct work)
- Anti-Pattern: PM modifying prompts directly

### Pattern 2: Meta-Analysis Workflow
**Behavior**: Agent follows structured refactoring workflow.

**Steps**:
1. Analyze current prompt (identify anti-patterns, score quality)
2. Research context (review codebase conventions)
3. Refactor (remove anti-patterns, add structure, increase specificity)
4. Validate (compare before/after, test with tasks)
5. Document (changelog, metrics)
6. Deliver (submit refactored prompt with summary)

**Test**:
- Input: Prompt refactoring request
- Expected: Agent follows all 6 steps sequentially
- Metrics: Step completion, workflow adherence

### Pattern 3: Evidence-Based Recommendations
**Behavior**: Agent provides context and justification for all recommendations.

**Pattern**: `[RECOMMENDATION] because [EVIDENCE/REASON]`

**Test**:
- Input: Prompt analysis request
- Expected: Every recommendation includes supporting evidence
- Metrics: Evidence quality, reasoning clarity

### Pattern 4: Conservative Action Mode
**Behavior**: Agent provides analysis and recommendations FIRST, waits for user approval before implementation.

**Test**:
- Input: "Analyze this prompt"
- Expected: Agent analyzes, recommends, does NOT implement without explicit instruction
- Anti-Pattern: Jumping to implementation without approval

### Pattern 5: Token Efficiency Optimization
**Behavior**: Agent prioritizes cache-friendly structures and token reduction.

**Test**:
- Input: Verbose prompt with poor cache design
- Expected: Agent reorganizes for caching, reduces redundancy
- Metrics: Projected cache hit rate (target: 90%+), token reduction %

---

## Integration with DeepEval

### Custom Metrics Required

#### 1. AntiPatternDetectionMetric
**Purpose**: Measure agent's ability to identify anti-patterns.

**Inputs**:
- Test case: Prompt containing known anti-patterns
- Expected anti-patterns: List of patterns to detect

**Scoring**:
```python
precision = detected_true_positives / total_detected
recall = detected_true_positives / total_actual_patterns
f1_score = 2 * (precision * recall) / (precision + recall)
```

**Threshold**: F1 ≥ 0.85

#### 2. RefactoringQualityMetric
**Purpose**: Measure quality improvement from refactoring.

**Inputs**:
- Original prompt
- Refactored prompt
- Quality rubric (8 criteria)

**Scoring**:
```python
score_before = average_rubric_score(original_prompt)
score_after = average_rubric_score(refactored_prompt)
improvement = score_after - score_before
success = (score_after >= 4.0) and (improvement >= 1.0)
```

**Threshold**: Improvement ≥ 1.0, Final ≥ 4.0

#### 3. TokenEfficiencyMetric
**Purpose**: Measure token reduction and cache optimization.

**Inputs**:
- Original prompt (token count, cache structure)
- Refactored prompt (token count, cache structure)

**Scoring**:
```python
token_reduction_pct = (original_tokens - refactored_tokens) / original_tokens
cache_efficiency = projected_cache_hit_rate  # 0.0-1.0

score = (0.5 * token_reduction_pct) + (0.5 * cache_efficiency)
success = (token_reduction_pct >= 0.3) and (cache_efficiency >= 0.9)
```

**Threshold**: Token reduction ≥30%, Cache efficiency ≥90%

#### 4. Claude45AlignmentMetric
**Purpose**: Measure adherence to Claude 4.5 best practices.

**Inputs**:
- Refactored prompt
- Checklist: [emojis removed, structured format, extended thinking, parallel tools, etc.]

**Scoring**:
```python
checklist_completion = passed_checks / total_checks
success = checklist_completion >= 0.95
```

**Threshold**: ≥95% checklist compliance

#### 5. WorkflowAdherenceMetric
**Purpose**: Measure agent's adherence to 6-step refactoring workflow.

**Inputs**:
- Agent execution trace
- Expected workflow steps: [Analyze, Research, Refactor, Validate, Document, Deliver]

**Scoring**:
```python
steps_completed = detected_steps / total_expected_steps
step_order_correct = are_steps_in_correct_sequence()
success = (steps_completed >= 0.83) and step_order_correct  # 5 of 6 steps
```

**Threshold**: ≥83% step completion (5/6 steps), correct order

---

## Test Harness Specifications

### Scenario Structure
```python
{
    "scenario_id": "prompt_engineer_001_emoji_detection",
    "category": "anti_pattern_detection",
    "input": {
        "user_request": "Analyze this prompt for anti-patterns",
        "prompt_to_analyze": "🎯 Goal: Add OAuth! 🔐\n\nLet's make it super secure! 💪✨"
    },
    "expected_behavior": {
        "detects_emojis": True,
        "emoji_count": 4,
        "recommends_removal": True,
        "provides_refactored_version": True
    },
    "metrics": [
        "AntiPatternDetectionMetric",
        "Claude45AlignmentMetric"
    ],
    "success_criteria": {
        "anti_pattern_detection_f1": 1.0,  # Perfect detection
        "claude45_alignment": 1.0  # All emojis flagged
    }
}
```

### Evaluation Flow
```
1. Load scenario with prompt to analyze
2. Delegate to prompt-engineer agent
3. Capture agent output
4. Apply custom metrics:
   - AntiPatternDetectionMetric (emoji detection)
   - RefactoringQualityMetric (quality improvement)
   - TokenEfficiencyMetric (token reduction)
   - Claude45AlignmentMetric (best practices)
   - WorkflowAdherenceMetric (process adherence)
5. Assert success criteria met
6. Generate detailed report
```

---

## Success Criteria Summary

### Anti-Pattern Detection
- **Emoji Detection**: 100% recall (no missed emojis)
- **Over-Specification**: Detects prompts >500 lines with step-by-step structure
- **Generic Prompts**: Flags vague language patterns with 90%+ accuracy
- **Cache-Hostile**: Detects variable data in system prompts with 85%+ accuracy
- **Negative Instructions**: Converts to positive framing with semantic preservation

### Refactoring Quality
- **Structure Addition**: Appropriate XML/markdown usage for 95%+ of cases
- **Context Enhancement**: Adds motivation/context in 90%+ of recommendations
- **Specificity**: Increases measurable criteria in 85%+ of refactorings
- **Token Reduction**: Achieves 30%+ reduction for verbose prompts
- **Quality Score**: Final average ≥4.0 on rubric

### Claude 4.5 Alignment
- **Extended Thinking**: Recommends appropriate budgets for 90%+ of complex tasks
- **Parallel Tools**: Detects parallelization opportunities with 85%+ accuracy
- **Communication Style**: Transforms to direct, fact-based style with 95%+ success
- **Checklist Compliance**: ≥95% adherence to Claude 4.5 best practices

### Workflow Adherence
- **Step Completion**: ≥83% of workflow steps executed (5/6 minimum)
- **Step Order**: 100% correct sequence
- **Evidence-Based**: 90%+ of recommendations include supporting rationale

---

## Files Analyzed

1. **Source Agent Template**:
   - Path: `~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/engineer/specialized/prompt-engineer.md`
   - Version: 3.0.0
   - Size: 150 lines (refactored from 738 lines in v2.0.0)

2. **Base Knowledge Document**:
   - Path: `~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/engineer/specialized/BASE_PROMPT_ENGINEER.md`
   - Version: 4.0.0
   - Size: 1,247 lines
   - Content: Comprehensive Claude 4.5 prompt engineering guide

3. **Deployed Template** (current project):
   - Path: `.claude/templates/prompt-engineer.md`
   - Matches remote cache version 3.0.0

---

## Next Steps

1. **Create Test Harness**: Implement prompt-engineer-specific test harness in `tests/deepeval/test_harnesses/`
2. **Develop Custom Metrics**: Build 5 custom DeepEval metrics for prompt engineering evaluation
3. **Write Scenarios**: Create 20+ test scenarios covering all 4 categories
4. **Integration**: Connect to existing DeepEval framework with CI/CD integration
5. **Validation**: Run tests against prompt-engineer agent, measure success rates
6. **Documentation**: Generate test reports with metric visualizations

---

## Appendix: Agent Configuration

### Model Configuration
```yaml
model: sonnet  # Claude Sonnet 4.5
resource_tier: standard
extended_thinking: enabled  # Critical for deep analysis
temperature: 0.3  # Lowered for consistency (v3.0.0 change)
```

### Routing Keywords
```yaml
tags:
  - prompt-engineering
  - claude-4.5
  - extended-thinking
  - system-prompt
  - instruction-optimization
```

### Delegation Patterns
```yaml
delegates_to:
  - research_agent: "For codebase pattern analysis and benchmark data collection"
  - engineer_agent: "For implementation of optimized prompt templates"

uses_extended_thinking_for:
  - "Deep instruction analysis"
  - "Refactoring strategy development"
```

---

**Research Complete**: All specifications extracted and categorized for DeepEval integration testing.
