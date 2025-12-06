# Claude 4.5 Prompt Engineering Quick Reference (2025)

**For**: Developers, PM, and prompt writers
**Purpose**: Fast lookup of critical do's and don'ts
**Full Guide**: See `BASE_PROMPT_ENGINEER.md` and `claude-4.5-prompt-engineering-best-practices-2025.md`

---

## 🔴 CRITICAL ANTI-PATTERNS (FORBIDDEN)

### ❌ EMOJIS
```
WRONG: "🎯 Goal: Implement auth 🔐"
RIGHT: "Goal: Implement authentication"
```
**Why**: Anthropic's official guidance prohibits emojis unless user explicitly requests.

---

### ❌ OVER-SPECIFICATION
```
WRONG: 700 lines of "Step 1: Open file. Step 2: Read line 42..."
RIGHT: "Refactor auth to use dependency injection. Follow SOLID. 90%+ test coverage."
```
**Why**: Claude 4.5 performs better with high-level guidance.

---

### ❌ NEGATIVE INSTRUCTIONS
```
WRONG: "Do not use markdown"
RIGHT: "Respond with smoothly flowing prose paragraphs"
```
**Why**: Positive framing provides clear target.

---

### ❌ GENERIC PROMPTS
```
WRONG: "Make the code better"
RIGHT: "Reduce cyclomatic complexity to <10. Extract helper functions. Maintain API."
```
**Why**: Specificity required for Claude 4.5.

---

## ✅ BEST PRACTICES

### 1. Be Explicit and Specific
```xml
<codebase_context>
Tech stack: Django 4.2, PostgreSQL, Redis
Current auth: Session-based
</codebase_context>

<task>
Implement OAuth2 (Google, GitHub).
Maintain backward compatibility.
</task>

<requirements>
- Authorization code grant with PKCE
- JWT tokens (access: 1h, refresh: 30d)
- Rate limit: 5 attempts/min/IP
- Log all auth events
</requirements>
```

---

### 2. Use XML Tags for Structure
```xml
<background_information>
<!-- Context -->
</background_information>

<task>
<!-- What to do -->
</task>

<requirements>
<!-- Functional requirements -->
</requirements>

<constraints>
<!-- Boundaries -->
</constraints>
```

---

### 3. Provide Context and Motivation
```
"Use structured logging because we query production logs for debugging
 user-reported errors. JSON format with timestamp, user_id, request_id
 enables Datadog filtering."
```
**Pattern**: [INSTRUCTION] because [REASON/CONTEXT]

---

### 4. Direct, Fact-Based Communication
```
WRONG: "🎉 Amazing progress! Successfully implemented wonderful feature! 🚀"
RIGHT: "Implemented OAuth2 authentication. Tests pass. Ready for review."
```
**Style**: [ACTION] → [RESULT] → [NEXT STEP]

---

### 5. Use Extended Thinking for Complexity
```
"Think hard about security implications, then implement OAuth2 with token rotation."
```

**Budgets**:
- `think` → Default (~4k tokens)
- `think hard` → Medium (~16k tokens)
- `think harder` → Large (~32k tokens)
- `ultrathink` → Maximum (~64k tokens)

---

### 6. Request Parallel Tool Execution
```
"If you intend to call multiple tools and there are no dependencies
 between the tool calls, make all of the independent tool calls in parallel."
```

---

### 7. Optimize for Cache (90% Savings)
```
[SYSTEM PROMPT - Cached, Stable]
- Role definition
- Core instructions
- Quality standards

[USER MESSAGE - Variable, Not Cached]
- Specific task
- File contents
- Dynamic data
```

---

## 📋 QUALITY CHECKLIST

### Good Prompt Has:
- ✅ Clarity (explicit, unambiguous)
- ✅ Structure (XML/markdown)
- ✅ Context (WHY not just WHAT)
- ✅ Specificity (detailed requirements)
- ✅ Examples (aligned behavior)
- ✅ Cache-friendly (stable/variable split)
- ✅ Professional (no emojis, fact-based)
- ✅ Actionable (measurable success)

### Bad Prompt Has:
- ❌ Vagueness ("make better")
- ❌ Over-specification (700+ lines)
- ❌ Emojis
- ❌ Negative framing ("Don't X")
- ❌ Generic (any project)
- ❌ Cache-hostile
- ❌ Celebratory tone

---

## 🔧 MIGRATION CHECKLIST (3.x → 4.5)

- [ ] Remove ALL emojis
- [ ] Convert negative to positive ("Don't X" → "Do Y")
- [ ] Add XML structure for multi-section prompts
- [ ] Increase specificity (make implicit explicit)
- [ ] Add context/motivation (explain WHY)
- [ ] Enable thinking ("think hard" for complex)
- [ ] Request parallelization
- [ ] Reduce over-specification (high-level guidance)

---

## 📞 WHEN TO USE PROMPT-ENGINEER AGENT

**Trigger Keywords**:
- "update instructions"
- "refactor prompt"
- "optimize agent"
- "improve system prompt"
- "modify PM_INSTRUCTIONS"
- "update skill definition"

**Delegation Protocol**:
1. User requests prompt modification
2. PM recognizes prompt work
3. PM delegates to prompt-engineer (MANDATORY)
4. Prompt-engineer refactors
5. PM reviews and approves

**Why**: Prompt-engineer is THE authority for all prompt work.

---

## 🚨 IMMEDIATE ACTION REQUIRED

**Breaking Change**: Remove ALL emojis from:
- `PM_INSTRUCTIONS.md`
- `WORKFLOW.md`
- `MEMORY.md`
- All agent templates
- All skill definitions

**How**: Delegate to prompt-engineer agent:
```
"Remove all emojis from PM_INSTRUCTIONS.md according to Claude 4.5 standards"
```

---

## 📚 FULL DOCUMENTATION

- **Comprehensive Guide**: `BASE_PROMPT_ENGINEER.md` (7000+ words)
- **Research Report**: `claude-4.5-prompt-engineering-best-practices-2025.md`
- **Update Summary**: `prompt-engineer-update-summary.md`
- **Agent Definition**: `agents/engineer/specialized/prompt-engineer.md` (v4.0.0)

---

**Last Updated**: 2025-12-05
**Version**: 1.0.0
