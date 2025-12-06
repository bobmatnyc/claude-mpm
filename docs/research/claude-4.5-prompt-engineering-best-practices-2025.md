# Claude 4.5 Prompt Engineering Best Practices (2025)

**Research Date**: 2025-12-05
**Target Model**: Claude 4.5 (Sonnet/Opus)
**Purpose**: Update prompt-engineer agent with latest authoritative guidance

---

## Executive Summary

Claude 4.5 represents a significant shift in prompt engineering best practices, moving from prescriptive, emoji-laden instructions to clear, structured, evidence-based prompting. Key changes:

- **Clarity over decoration**: Plain text preferred, emojis strongly discouraged
- **Explicit over implicit**: Be specific about desired outputs
- **Structure over prose**: XML tags and markdown headers for organization
- **Thinking capabilities**: Extended thinking budgets for complex reasoning
- **Parallel execution**: Aggressive multi-tool orchestration
- **Minimal verbosity**: Direct, fact-based communication

---

## 1. Core Principles (2025)

### 1.1 Be Explicit with Instructions

**What Changed**: Claude 4.x models require MORE specificity than Claude 3.x. Previously implicit behaviors must now be explicitly requested.

**Best Practice**:
```
❌ BAD: "Add tests for foo.py"
✅ GOOD: "Write a new test case for foo.py, covering the edge case where
         the user is logged out. Avoid mocks. Use pytest fixtures."
```

**Why**: Claude 4.5 follows instructions precisely but doesn't infer unstated requirements as aggressively as prior versions.

**Source**: [Anthropic Claude 4.x Best Practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-4-best-practices)

---

### 1.2 Provide Context and Motivation

**What Changed**: Claude 4.5 performs better when it understands WHY, not just WHAT.

**Best Practice**:
```
❌ BAD: "Use structured logging"
✅ GOOD: "Use structured logging because we need to query logs in production
         for debugging user-reported errors with millisecond precision."
```

**Why**: Context helps Claude prioritize trade-offs and deliver targeted solutions.

**Source**: Anthropic Claude 4.x documentation

---

### 1.3 Pay Attention to Examples

**Critical Change**: Claude 4.5 scrutinizes examples MORE closely than Claude 3.x.

**Best Practice**:
- Ensure examples align EXACTLY with desired behavior
- Minimize unintended patterns in examples
- Use "meta few-shot" approach: one perfect example + one annotated mistake

**Why**: Examples significantly influence output quality in Claude 4.5.

**Source**: [Anthropic System Prompt Updates](https://blog.promptlayer.com/what-we-can-learn-from-anthropics-system-prompt-updates/)

---

## 2. Communication Style (2025)

### 2.1 Emoji Anti-Pattern (CRITICAL)

**Official Guidance**:
> "Claude does not use emojis unless the person in the conversation asks it to or if the person's message immediately prior contains an emoji, and is judicious about its use of emojis even in these circumstances."

**Claude Code Directive**:
> "Only use emojis if the user explicitly requests it. Avoid using emojis in all communication unless asked."

**Why This Matters**:
- Emojis are considered unprofessional in technical/coding contexts
- They add no semantic value and waste tokens
- Claude 4.5's system prompt explicitly discourages them

**Migration Impact**: Remove ALL emoji usage from PM instructions, agent templates, and system prompts unless user-facing entertainment contexts.

**Source**: [Claude 4 System Prompt](https://simonwillison.net/2025/May/25/claude-4-system-prompt/), [Claude Code Analysis](https://minusx.ai/blog/decoding-claude-code/)

---

### 2.2 Direct, Fact-Based Reporting

**What Changed**: Claude 4.5 is "more direct and grounded" with "less verbose" output.

**Best Practice**:
```
❌ BAD: "🎉 Great progress! We've successfully implemented the amazing
         new authentication system! 🚀"
✅ GOOD: "Implemented OAuth2 authentication. Tests pass. Ready for review."
```

**Why**: Claude 4.5 provides "fact-based progress reports rather than self-celebratory updates."

**Source**: [Anthropic Claude 4.x Best Practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-4-best-practices)

---

### 2.3 Avoid Negative Instructions

**What Changed**: Negative framing ("Don't do X") is less effective than positive framing.

**Best Practice**:
```
❌ BAD: "Do not use markdown"
✅ GOOD: "Your response should be composed of smoothly flowing prose paragraphs"
```

**Alternative**: Use XML format indicators like `<smoothly_flowing_prose_paragraphs>` to steer formatting.

**Source**: Anthropic Claude 4.x documentation

---

## 3. Structured Prompts (2025)

### 3.1 XML Tags for Organization

**Why XML Tags**: Claude was fine-tuned with XML tags in training data, making them particularly effective.

**Best Practice**:
```xml
<background_information>
This codebase uses FastAPI with SQLAlchemy ORM.
Authentication uses JWT tokens with 1-hour expiration.
</background_information>

<instructions>
Add rate limiting to the /api/login endpoint.
Use Redis for rate limit storage.
Limit to 5 attempts per minute per IP address.
</instructions>

<examples>
<example>
Rate limit exceeded response:
{"error": "Too many requests", "retry_after": 47}
</example>
</examples>

<output_format>
Provide implementation code followed by test cases.
</output_format>
```

**Common Tags**:
- `<thinking>` and `<answer>` for chain-of-thought
- `<examples>`, `<document>`, `<instructions>` for organization
- `<quotes>` for RAG applications
- Custom tags for domain-specific structure

**Source**: [Anthropic XML Tags Guide](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/use-xml-tags)

---

### 3.2 Markdown Headers as Alternative

**When to Use**: For simpler prompts without deep nesting.

**Best Practice**:
```markdown
## Background
Project uses Next.js 14 with App Router.

## Task
Add server-side pagination to the products page.

## Requirements
- Fetch 20 products per page
- Include total count in response
- Handle edge cases (empty results, last page)

## Output
TypeScript code with inline type definitions.
```

**Source**: Anthropic prompt engineering overview

---

## 4. Thinking Capabilities (2025)

### 4.1 Extended Thinking Budgets

**What's New**: Claude 4.5 supports extended thinking with configurable budgets.

**Thinking Budget Triggers**:
- "think" → Default thinking
- "think hard" → Medium thinking budget (~16k tokens)
- "think harder" → Large thinking budget (~32k tokens)
- "ultrathink" → Maximum thinking budget (~64k tokens)

**Best Practice**:
```
❌ BAD: "Implement authentication" (no thinking guidance)
✅ GOOD: "Think hard about security implications, then implement OAuth2
         authentication with proper token rotation."
```

**When to Use Extended Thinking**:
- Complex architectural decisions
- Security-critical implementations
- Multi-step refactoring plans
- Bug investigation and root cause analysis

**Source**: [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)

---

### 4.2 Sensitivity to "Think" Keyword

**Critical**: When extended thinking is DISABLED, Claude Opus 4.5 is "particularly sensitive to the word 'think' and its variants."

**Workaround**: Replace with "consider," "believe," or "evaluate" if not using extended thinking.

**Source**: Anthropic Claude 4.x documentation

---

### 4.3 Reflection After Tool Use

**Best Practice**: Encourage reflection on tool results before proceeding.

**Example**:
```
"After receiving tool results, carefully reflect on their quality and
determine optimal next steps before proceeding."
```

**Source**: Anthropic Claude 4.x documentation

---

## 5. Tool Orchestration (2025)

### 5.1 Parallel Tool Execution

**What Changed**: Claude 4.5 Sonnet is "particularly aggressive in firing off multiple operations simultaneously."

**Best Practice**:
```
"If you intend to call multiple tools and there are no dependencies
between the tool calls, make all of the independent tool calls in parallel."
```

**Why**: Significant performance improvement for independent operations.

**Source**: [Anthropic Claude 4.x Best Practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-4-best-practices)

---

### 5.2 Explicit Action Directives

**What Changed**: Claude 4.5 requires explicit instructions to take action.

**Best Practice**:
```
❌ BAD: "This function could be optimized"
✅ GOOD: "Implement changes rather than only suggesting them. Refactor the
         get_user() function to use a single database query."
```

**Alternative** (conservative mode):
```
"Do not jump into implementation unless clearly instructed to make changes."
```

**Source**: Anthropic Claude 4.x documentation

---

## 6. Anti-Patterns (2025)

### 6.1 Over-Specification (NEW)

**What**: Providing excessively detailed step-by-step instructions.

**Why It's Bad**: Claude 4.5 performs better with high-level guidance than prescriptive checklists.

**Example**:
```
❌ BAD (738 lines of detailed steps):
"Step 1: Open the file
 Step 2: Read line 42
 Step 3: Check if variable x exists
 Step 4: If x exists, proceed to step 5..."

✅ GOOD (high-level guidance):
"Refactor the authentication module to use dependency injection.
 Follow SOLID principles. Ensure 90%+ test coverage."
```

**Evidence**: Prompt-engineer agent refactored from 738→150 lines by eliminating over-specification.

**Source**: prompt-engineer.md changelog (v3.0.0)

---

### 6.2 Generic Prompts

**What**: Vague instructions that require Claude to guess intent.

**Example**:
```
❌ BAD: "Make the code better"
✅ GOOD: "Reduce function complexity from 15 to <10 cyclomatic complexity.
         Extract helper functions. Maintain current API surface."
```

**Source**: Claude Code best practices

---

### 6.3 Cache Invalidation

**What**: Frequently changing parts of prompts that should be cached.

**Best Practice**:
- Place stable instructions in system prompts (cached)
- Place variable data (file contents, user input) in user messages
- Structure prompts to maximize cache hit rates (~90% token savings)

**Source**: Anthropic context management documentation

---

### 6.4 Mixing Refactoring with Features

**What**: Combining refactoring and new features in single task.

**Best Practice**:
```
"Never mix refactoring with feature work. Complete refactoring first,
 ensure tests pass, then add new features."
```

**Source**: BASE-AGENT.md engineering principles

---

### 6.5 Test-Driven Hard-Coding

**What**: Implementing solutions that ONLY pass specific test cases without generalizing.

**Best Practice**:
```
"Implement high-quality, general-purpose solutions rather than focusing
 solely on passing specific test cases."
```

**Source**: Anthropic Claude 4.x documentation

---

## 7. Long-Horizon Reasoning (2025)

### 7.1 Context Awareness

**What's New**: Claude 4.5 tracks remaining token budget throughout conversations.

**Best Practice**:
- Use first window to establish framework (tests, setup scripts)
- Write tests in structured formats (JSON)
- Create quality-of-life tools (init scripts, linters)
- Use git for state tracking across sessions
- Start fresh windows rather than relying solely on compaction

**Source**: Anthropic Claude 4.x documentation

---

### 7.2 State Tracking

**Best Practice**:
- Structured formats (JSON) for test results
- Unstructured text for progress notes
- Git checkpoints for history
- Emphasize incremental progress

**Source**: Anthropic Claude 4.x documentation

---

## 8. Domain-Specific Patterns (2025)

### 8.1 Agentic Coding

**Code Exploration**:
```
"ALWAYS read and understand relevant files before proposing code edits.
 Do not speculate about code you have not inspected."
```

**Hallucination Reduction**:
```
"Never speculate about code you have not opened. Investigate files
 before answering questions about codebases."
```

**Minimal Engineering**:
```
"Avoid over-engineering. Only make changes that are directly requested
 or clearly necessary. Keep solutions simple and focused."
```

**Source**: [Anthropic Claude 4.x Best Practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-4-best-practices)

---

### 8.2 Frontend Design

**Anti-Pattern**: Converging toward generic "AI slop" aesthetics.

**Best Practice**: Explicitly request distinctive designs:
```
"Use unique typography (avoid Arial, Inter). Create cohesive color scheme
 with dominant colors and sharp accents. Add purposeful animations for
 key moments. Use atmospheric backgrounds with gradients or patterns.
 Design context-specific character, not cookie-cutter layouts."
```

**Source**: Anthropic Claude 4.x documentation

---

### 8.3 Research & Information Gathering

**Structured Approach**:
- Define clear success criteria
- Encourage source verification across multiple sources
- Develop competing hypotheses
- Track confidence levels
- Update structured notes files for persistence

**Source**: Anthropic Claude 4.x documentation

---

## 9. Response Format Control (2025)

### 9.1 Prefilling for Format

**What**: Starting Claude's response to steer output format.

**Example**:
```
User: "Generate JSON config"
Assistant (prefilled): {
  "config": {
```

**When to Use**:
- Forcing specific output formats (JSON, XML, code blocks)
- Skipping preambles ("Here's the config...")
- Enforcing structure compliance

**Source**: Anthropic prompt engineering overview

---

### 9.2 Match Prompt Style to Output

**Principle**: Formatting style in prompt influences response style.

**Example**:
```
❌ BAD (markdown-heavy prompt):
# Instructions
- Do this
- Do that
**Important**: Follow these rules

Result: Markdown-heavy response

✅ GOOD (plain text prompt):
Instructions:
1. Do this
2. Do that

Important: Follow these rules

Result: Plain text response
```

**Source**: Anthropic Claude 4.x documentation

---

### 9.3 Minimize Markdown Usage

**Guidance**: For reports and technical content:
```
"Use standard paragraph breaks for organization and reserve markdown
 primarily for `inline code`, code blocks (```...```), and simple headings."
```

**Source**: Anthropic Claude 4.x documentation

---

## 10. Subagent Orchestration (2025)

### 10.1 Natural Delegation

**What's New**: Claude 4.5 proactively recognizes when tasks benefit from specialized subagents.

**Best Practice**:
- Define well-structured subagent tools
- Let Claude orchestrate naturally without explicit delegation instructions
- Provide clear tool descriptions and examples

**Source**: Anthropic Claude 4.x documentation

---

## 11. Vision Capabilities (2025)

### 11.1 Multi-Image Processing

**What's New**: Claude Opus 4.5 improved image processing across multiple images.

**Best Practice**: Pair with crop tool for zooming into relevant regions (boosts performance).

**Source**: Anthropic Claude 4.x documentation

---

## 12. Migration Guide (Claude 3.x → 4.5)

### 12.1 Required Changes

| Category | Claude 3.x | Claude 4.5 |
|----------|-----------|------------|
| **Emojis** | Common in prompts | Forbidden unless user requests |
| **Verbosity** | Celebratory updates | Direct, fact-based reporting |
| **Specificity** | Moderate | High (explicit instructions) |
| **Examples** | Moderate attention | High scrutiny |
| **Thinking** | Implicit | Explicit budgets ("think hard") |
| **Tools** | Sequential | Parallel by default |

### 12.2 Prompt Refactoring Checklist

- [ ] Remove ALL emojis from system prompts
- [ ] Replace negative instructions ("Don't X") with positive ("Do Y")
- [ ] Add XML tags for multi-section prompts
- [ ] Make implicit requirements explicit
- [ ] Add context/motivation for instructions
- [ ] Enable extended thinking for complex tasks
- [ ] Request parallel tool execution where applicable
- [ ] Reduce over-specification (high-level guidance > detailed steps)
- [ ] Add reflection prompts after tool use
- [ ] Structure prompts for cache efficiency

---

## 13. Prompt-Engineer Agent Authority

### 13.1 Scope of Authority

The prompt-engineer agent is THE authoritative agent for:
- All system prompt modifications (PM instructions, agents, skills)
- Instruction optimization and refactoring
- Claude 4.5 best practices enforcement
- Anti-pattern detection and remediation
- Meta-level prompt analysis and improvement

### 13.2 Delegation Workflow

**Correct Flow**:
```
User Request
    ↓
PM Agent (recognizes prompt work)
    ↓
Delegate to prompt-engineer agent
    ↓
Prompt-engineer analyzes/refactors
    ↓
PM reviews and approves
    ↓
Deploy to project
```

**Why**: Centralized prompt expertise prevents drift and ensures consistency.

---

## 14. Quality Criteria (2025)

### 14.1 Good Prompt Characteristics

✅ **Clarity**: Explicit, unambiguous instructions
✅ **Structure**: XML tags or markdown headers for organization
✅ **Context**: Explains WHY, not just WHAT
✅ **Examples**: Aligned with desired behavior, minimal noise
✅ **Specificity**: Detailed about desired outcomes
✅ **Efficiency**: Cache-friendly structure
✅ **Actionability**: Clear success criteria

### 14.2 Bad Prompt Characteristics

❌ **Vagueness**: "Make it better," "Fix the code"
❌ **Over-specification**: 700+ lines of step-by-step instructions
❌ **Emojis**: Unprofessional decoration
❌ **Negative framing**: "Don't do X" instead of "Do Y"
❌ **Generic instructions**: Could apply to any project
❌ **Cache-hostile**: Frequently changing stable content
❌ **Implicit assumptions**: Relies on Claude to infer requirements

---

## 15. Sources and References

### Primary Sources
1. [Anthropic Claude 4.x Best Practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-4-best-practices)
2. [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
3. [Anthropic XML Tags Guide](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/use-xml-tags)
4. [Claude 4 System Prompt Analysis](https://simonwillison.net/2025/May/25/claude-4-system-prompt/)

### Secondary Sources
5. [Claude Code System Prompt Changes](https://mikhail.io/2025/09/sonnet-4-5-system-prompt-changes/)
6. [Anthropic System Prompt Updates](https://blog.promptlayer.com/what-we-can-learn-from-anthropics-system-prompt-updates/)
7. [Claude Code Internal Analysis](https://minusx.ai/blog/decoding-claude-code/)
8. [CLAUDE.md Best Practices](https://arize.com/blog/claude-md-best-practices-learned-from-optimizing-claude-code-with-prompt-learning/)

### Framework Sources
9. BASE-AGENT.md (Engineering principles)
10. prompt-engineer.md v3.0.0 changelog

---

## 16. Gap Analysis (Current vs. 2025)

### Current Prompt-Engineer Agent (v3.0.0)

**Strengths**:
- Already refactored from 738→150 lines (demonstrates anti-over-specification)
- References BASE_PROMPT_ENGINEER.md (though file not found in cache)
- Includes extended thinking configuration
- Model selection decision matrix
- Tool orchestration awareness

**Gaps**:
1. **No Anti-Pattern Section**: Missing explicit emoji prohibition, negative framing
2. **No Communication Style Guide**: Doesn't mention fact-based reporting
3. **No Authority Statement**: Doesn't establish itself as THE prompt expert
4. **No Quality Criteria**: Missing "good vs bad prompt" evaluation framework
5. **No Migration Guidance**: Doesn't help convert Claude 3.x prompts to 4.5
6. **Missing BASE File**: References BASE_PROMPT_ENGINEER.md but file doesn't exist

### Required Updates

1. **Add Anti-Patterns Section** with:
   - Emoji prohibition
   - Over-specification warning
   - Negative instruction anti-pattern
   - Cache-hostile structure warning

2. **Add Communication Style Section** with:
   - Direct, fact-based reporting
   - Minimal verbosity
   - Professional tone

3. **Add Authority Statement**:
   - "THE authoritative agent for all prompt work"
   - Scope: system prompts, agent templates, skills
   - Delegation workflow

4. **Add Quality Criteria**:
   - Good prompt checklist
   - Bad prompt warning signs
   - Evaluation framework

5. **Add Migration Guide**:
   - Claude 3.x → 4.5 checklist
   - Before/after examples
   - Testing protocol

6. **Create BASE_PROMPT_ENGINEER.md** (currently missing):
   - Comprehensive knowledge base
   - All patterns and anti-patterns
   - Reference examples
   - Decision trees

---

## Conclusion

Claude 4.5 prompt engineering in 2025 emphasizes **clarity over decoration**, **structure over prose**, and **evidence-based communication**. The shift away from emojis, verbose updates, and over-specification represents a maturation of prompt engineering practices toward professional, efficient, token-optimized interactions.

The prompt-engineer agent must be updated to reflect these standards and establish itself as the authoritative source for all prompt-related work in the Claude MPM framework.
