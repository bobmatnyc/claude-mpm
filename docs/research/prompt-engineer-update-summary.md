# Prompt-Engineer Agent Update Summary

**Date**: 2025-12-05
**Version**: 3.0.0 → 4.0.0
**Researcher**: Research Agent
**Purpose**: Align prompt-engineer agent with Claude 4.5 (2025) best practices

---

## Executive Summary

Successfully updated the prompt-engineer agent with comprehensive Claude 4.5 prompt engineering best practices for 2025. Key achievements:

1. **Created BASE_PROMPT_ENGINEER.md**: 7000+ word comprehensive knowledge base
2. **Updated prompt-engineer.md**: v4.0.0 with authority statement and 2025 standards
3. **Documented Best Practices**: Research document with migration guide
4. **Established Authority**: Prompt-engineer is now THE agent for all prompt work

---

## Deliverables

### 1. Best Practices Research Document
**Location**: `/Users/masa/Projects/claude-mpm/docs/research/claude-4.5-prompt-engineering-best-practices-2025.md`

**Contents**:
- 16 comprehensive sections covering Claude 4.5 best practices
- Anti-patterns catalog (emojis, over-specification, negative instructions)
- Communication style guide (fact-based, no emojis)
- Structured prompt patterns (XML tags, markdown headers)
- Extended thinking capabilities
- Tool orchestration optimization
- Migration guide (Claude 3.x → 4.5)
- Quality evaluation framework
- 15+ authoritative sources cited

**Key Findings**:
- Emojis are FORBIDDEN unless user explicitly requests
- Claude 4.5 requires MORE specificity than Claude 3.x
- Over-specification (700+ lines of steps) is an anti-pattern
- High-level guidance outperforms prescriptive checklists
- Parallel tool execution is critical for performance
- Cache optimization can achieve 90% token savings

---

### 2. BASE_PROMPT_ENGINEER.md Knowledge Base
**Location**: `/Users/masa/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/engineer/specialized/BASE_PROMPT_ENGINEER.md`

**Structure**:
- I. Authority and Scope
- II. Core Principles (Clarity, Structure, Evidence)
- III. Communication Style (Emoji anti-pattern, fact-based reporting)
- IV. Structured Prompts (XML tags, markdown headers)
- V. Thinking Capabilities (Extended thinking budgets)
- VI. Tool Orchestration (Parallel execution, action directives)
- VII. Anti-Patterns (Over-specification, generic prompts, cache invalidation)
- VIII. Domain-Specific Patterns (Coding, frontend, research)
- IX. Long-Horizon Reasoning
- X. Migration Guide
- XI. Quality Criteria
- XII. Workflow Integration
- XIII. Advanced Techniques
- XIV. Troubleshooting
- XV. References (15 sources)
- XVI. Version History

**Features**:
- Comprehensive anti-pattern catalog
- Before/after examples for all patterns
- Quality evaluation rubrics (scoring system)
- Troubleshooting decision trees
- Domain-specific guidance (agentic coding, frontend design, research)
- Advanced techniques (prompt chaining, meta few-shot, progressive disclosure)

---

### 3. Updated Prompt-Engineer Agent (v4.0.0)
**Location**: `/Users/masa/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/engineer/specialized/prompt-engineer.md`

**Changes from v3.0.0**:

#### Added
- **Authority Statement**: "THE singular agent for all prompt-related work"
- **Scope Definition**: System prompts, agent templates, skills, instruction documents
- **Delegation Protocol**: PM → prompt-engineer (mandatory)
- **Anti-Pattern Section**: Emojis forbidden, over-specification, negative instructions, generic prompts
- **Communication Style Guide**: Direct, fact-based, no emojis, minimal verbosity
- **Quality Evaluation Framework**: Good/bad prompt checklists, scoring criteria
- **Migration Guide**: Claude 3.x → 4.5 with before/after examples
- **Workflow Integration**: 6-step process (analyze, research, refactor, validate, document, deliver)
- **Extended Thinking Guidance**: When to use "think hard", "think harder", "ultrathink"
- **Tool Orchestration**: Parallel execution, reflection after tools
- **Cache Optimization**: 90% cache hit rate structure
- **Success Metrics**: Token efficiency, quality scores, anti-pattern counts

#### Improved
- **Routing Keywords**: Added "PM_INSTRUCTIONS", "agent template", "skill definition"
- **Model Config**: Confirmed temperature 0.3, extended thinking enabled
- **Description**: Now explicitly states "THE authoritative agent" and lists anti-patterns
- **Tags**: Added "anti-patterns", "system-prompt-refactoring"

#### Removed
- Over-specification (agent already refactored from 738 → 150 lines in v3.0.0)
- Generic guidance without examples

---

## Gap Analysis

### What Was Missing in v3.0.0

1. **No Anti-Pattern Section**
   - ✅ Fixed: Added explicit emoji prohibition, over-specification warning

2. **No Communication Style Guide**
   - ✅ Fixed: Added fact-based reporting, minimal verbosity standards

3. **No Authority Statement**
   - ✅ Fixed: Established as THE prompt expert with delegation protocol

4. **No Quality Criteria**
   - ✅ Fixed: Added good/bad prompt checklists with scoring

5. **No Migration Guidance**
   - ✅ Fixed: Claude 3.x → 4.5 checklist with examples

6. **Missing BASE File**
   - ✅ Fixed: Created comprehensive 7000+ word knowledge base

---

## Key 2025 Best Practices

### 1. Emoji Anti-Pattern (CRITICAL)

**Anthropic Official Guidance**:
> "Claude does not use emojis unless the person in the conversation asks it to or if the person's message immediately prior contains an emoji, and is judicious about its use of emojis even in these circumstances."

**Action Required**: Remove ALL emojis from PM instructions, agent templates, skills.

**Example**:
```
❌ "🎯 Goal: Implement authentication 🔐"
✅ "Goal: Implement authentication"
```

---

### 2. Over-Specification Anti-Pattern

**Finding**: Claude 4.5 performs better with high-level guidance than prescriptive checklists.

**Evidence**: Prompt-engineer agent improved from 738 → 150 lines by removing over-specification.

**Example**:
```
❌ 700 lines: "Step 1: Open file. Step 2: Read line 42. Step 3..."
✅ High-level: "Refactor authentication to use dependency injection. Follow SOLID principles. Ensure 90%+ test coverage."
```

---

### 3. Communication Style: Direct, Fact-Based

**What Changed**: Claude 4.5 is "more direct and grounded" with "less verbose" output.

**Example**:
```
❌ "🎉 Wonderful progress! We've successfully implemented the amazing feature! 🚀"
✅ "Implemented OAuth2 authentication. Tests pass. Ready for review."
```

---

### 4. Explicit Instructions Required

**What Changed**: Claude 4.5 requires MORE specificity than Claude 3.x.

**Example**:
```
❌ "Add tests for foo.py"
✅ "Write pytest test cases for foo.py covering:
   - Valid login with correct credentials
   - Invalid login with wrong password
   - Account lockout after 5 failed attempts
   Use fixtures for database setup. Avoid mocks."
```

---

### 5. Structured Prompts (XML Tags)

**Why**: Claude was fine-tuned with XML tags in training data.

**Example**:
```xml
<background_information>
Tech stack: Django 4.2, PostgreSQL, Redis
</background_information>

<task>
Add rate limiting to /api/login endpoint.
</task>

<requirements>
- 5 attempts per minute per IP
- Use Redis for storage
- Return HTTP 429 with retry-after header
</requirements>
```

---

### 6. Extended Thinking Budgets

**New Capability**: Claude 4.5 supports explicit thinking budgets.

**Triggers**:
- "think" → Default (~4k tokens)
- "think hard" → Medium (~16k tokens)
- "think harder" → Large (~32k tokens)
- "ultrathink" → Maximum (~64k tokens)

**When to Use**: Complex architecture, security-critical tasks, deep refactoring.

---

### 7. Parallel Tool Execution

**What Changed**: Claude 4.5 Sonnet is "particularly aggressive in firing off multiple operations simultaneously."

**Directive**:
```
"If you intend to call multiple tools and there are no dependencies
 between the tool calls, make all of the independent tool calls in parallel."
```

---

### 8. Negative Instruction Anti-Pattern

**Problem**: Telling Claude what NOT to do is less effective.

**Example**:
```
❌ "Do not use markdown"
✅ "Respond with smoothly flowing prose paragraphs"
```

---

## Migration Recommendations

### For PM Instructions

1. **Immediate Actions** (breaking changes):
   - Remove ALL emojis from PM_INSTRUCTIONS.md
   - Remove ALL emojis from WORKFLOW.md
   - Remove ALL emojis from MEMORY.md

2. **High Priority** (quality improvements):
   - Add XML structure to multi-section instructions
   - Convert negative instructions to positive
   - Add context/motivation for key directives
   - Increase specificity in task descriptions

3. **Medium Priority** (optimization):
   - Optimize for cache efficiency (stable vs. variable content)
   - Add extended thinking directives for complex tasks
   - Request parallel tool execution where applicable

4. **Low Priority** (refinement):
   - Review examples for alignment
   - Reduce over-specification if present
   - Add quality criteria for task completion

---

### For Agent Templates

1. **Scan for Anti-Patterns**:
   ```bash
   # Find emojis in agent templates
   grep -r "[🎯🔐💪✨🎉🚀]" ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/

   # Find negative instructions
   grep -ri "do not\|don't\|avoid" ~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/ | grep -v "avoid over-engineering"
   ```

2. **Prioritize Refactoring**:
   - High-traffic agents first (engineer, research, pm)
   - User-facing agents (ticketing, git)
   - Specialized agents (prompt-engineer already done)

3. **Quality Gates**:
   - Evaluate each agent using quality framework (target ≥4.0/5.0)
   - Measure token usage before/after
   - Test with representative tasks

---

### For CLAUDE.md Files

1. **Structure Review**:
   - Add markdown headers if missing
   - Separate stable (project info) from variable (current tasks)

2. **Content Audit**:
   - Remove emojis
   - Add context for key conventions
   - Make implicit requirements explicit

3. **Testing**:
   - Verify Claude loads and understands CLAUDE.md
   - Test with new tasks to ensure guidance is followed

---

## Testing Protocol

### Phase 1: Smoke Testing
- Deploy updated prompt-engineer.md to test environment
- Verify agent loads without errors
- Test basic prompt analysis task
- Confirm BASE_PROMPT_ENGINEER.md is accessible

### Phase 2: Functional Testing
- Test anti-pattern detection (provide emoji-laden prompt)
- Test refactoring workflow (provide vague prompt)
- Test quality evaluation (score sample prompts)
- Test migration guidance (convert Claude 3.x prompt)

### Phase 3: Integration Testing
- Test PM → prompt-engineer delegation
- Test prompt-engineer → engineer delegation
- Test prompt-engineer → research delegation
- Verify workflow integration

### Phase 4: Regression Testing
- Ensure no functionality lost from v3.0.0
- Verify model config still works (temperature 0.3, extended thinking)
- Confirm routing keywords trigger correctly

---

## Success Metrics

### Immediate (v4.0.0 Launch)
- ✅ BASE_PROMPT_ENGINEER.md created (7000+ words)
- ✅ Prompt-engineer.md updated to v4.0.0
- ✅ Authority statement established
- ✅ Anti-pattern section added
- ✅ Quality framework documented

### Short-Term (1 week)
- [ ] All PM instructions reviewed for emojis (target: 0 emojis)
- [ ] Top 10 agent templates audited (target: ≥4.0 quality score)
- [ ] CLAUDE.md best practices documented
- [ ] Testing protocol executed

### Medium-Term (1 month)
- [ ] All agent templates refactored to Claude 4.5 standards
- [ ] Token usage reduced by 20%+ through cache optimization
- [ ] Quality scores improved across all prompts (average ≥4.0)
- [ ] User satisfaction: 50% fewer clarification requests

### Long-Term (3 months)
- [ ] Framework-wide Claude 4.5 alignment (zero anti-patterns)
- [ ] 90%+ cache hit rate across all prompts
- [ ] Automated prompt quality monitoring
- [ ] Prompt-engineer agent usage metrics tracked

---

## Next Steps

### For Framework Developers

1. **Review Updated Agent**:
   - Read prompt-engineer.md v4.0.0
   - Read BASE_PROMPT_ENGINEER.md
   - Understand delegation protocol

2. **Apply to PM Instructions**:
   - Delegate prompt work to prompt-engineer agent
   - Test with example: "Remove emojis from PM_INSTRUCTIONS.md"
   - Verify quality improvement

3. **Audit Agent Templates**:
   - Use prompt-engineer to audit top 10 agents
   - Score using quality framework
   - Prioritize refactoring based on scores

4. **Update Documentation**:
   - Link to BASE_PROMPT_ENGINEER.md in developer docs
   - Add prompt engineering section to contributing guide
   - Document testing protocol for prompt changes

### For PM Agent

1. **Recognize Prompt Work**:
   - Keywords: "update instructions", "refactor prompt", "optimize agent"
   - Delegate to prompt-engineer (MANDATORY)
   - Do NOT attempt prompt modifications directly

2. **Review Prompt-Engineer Output**:
   - Check quality score (target ≥4.0)
   - Verify no anti-patterns
   - Approve or request revision

3. **Track Improvements**:
   - Monitor token usage trends
   - Track clarification request reduction
   - Measure user satisfaction

---

## Resources

### Primary Sources (Official Anthropic)
1. [Claude 4.x Best Practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-4-best-practices)
2. [Claude Code Best Practices](https://www.anthropic.com/engineering/claude-code-best-practices)
3. [XML Tags Guide](https://docs.claude.com/en/docs/build-with-claude/prompt-engineering/use-xml-tags)

### Research Documents (This Project)
1. `/Users/masa/Projects/claude-mpm/docs/research/claude-4.5-prompt-engineering-best-practices-2025.md`
2. `~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/engineer/specialized/BASE_PROMPT_ENGINEER.md`
3. `~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/engineer/specialized/prompt-engineer.md`

### Community Resources
4. [Claude Code System Prompt Analysis](https://mikhail.io/2025/09/sonnet-4-5-system-prompt-changes/)
5. [CLAUDE.md Best Practices](https://arize.com/blog/claude-md-best-practices-learned-from-optimizing-claude-code-with-prompt-learning/)

---

## Conclusion

The prompt-engineer agent has been successfully updated to reflect Claude 4.5 (2025) best practices. Key improvements:

1. **Authority Established**: Now THE agent for all prompt work
2. **Anti-Patterns Documented**: Emojis, over-specification, negative instructions
3. **Quality Framework**: Evaluation criteria and scoring system
4. **Migration Path**: Clear guide from Claude 3.x to 4.5
5. **Comprehensive Knowledge Base**: 7000+ word BASE_PROMPT_ENGINEER.md

The framework is now positioned to systematically improve all prompts across PM instructions, agent templates, and skill definitions to align with 2025 standards.

**Critical Next Step**: Remove ALL emojis from PM_INSTRUCTIONS.md, WORKFLOW.md, and MEMORY.md (breaking change, requires immediate action).

---

**Research Conducted By**: Research Agent
**Date**: 2025-12-05
**Version**: Final Report
