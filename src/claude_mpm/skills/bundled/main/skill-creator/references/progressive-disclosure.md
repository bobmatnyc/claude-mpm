# Progressive Disclosure Pattern for Skills

## What is Progressive Disclosure?

Progressive disclosure is a design pattern that reveals information progressively, starting with the essential and expanding to detail as needed. For skills, it means organizing content into layers that Claude loads based on task complexity.

**Core principle:** Don't load what you don't need. Start simple, go deep when required.

## Why Progressive Disclosure?

### The Context Window Problem

Claude has a limited context window. Every token counts. Traditional monolithic skills load ALL content when activated, consuming precious context even for simple tasks.

**Without progressive disclosure:**
```
User: "Create a simple skill for tracking todos"
Claude loads: 209 lines of skill-creator content
Claude needs: Maybe 40 lines for this simple case
Wasted: 169 lines of context (80%)
```

**With progressive disclosure:**
```
User: "Create a simple skill for tracking todos"
Claude loads: 150 lines of entry point
Claude identifies: Needs basic structure only
Claude loads: skill-structure.md (additional 200 lines)
Total: 350 lines
Context saved: Didn't load workflow details, examples, best practices (600+ lines)
```

### Benefits

1. **Efficient Context Usage** - Load only what's needed for current task
2. **Faster Comprehension** - Entry point provides quick orientation
3. **Scalable Depth** - Can have unlimited detail without bloating entry
4. **Better Organization** - Related content grouped logically
5. **Easier Maintenance** - Update specific references without touching entry
6. **Clearer Navigation** - Explicit signposting to deeper content

## Three-Level Architecture

Skills using progressive disclosure operate on three levels:

### Level 1: Metadata (Always Loaded)

**Content:** YAML frontmatter
- `name:` - Skill identifier
- `description:` - Purpose and activation conditions
- `progressive_disclosure:` - Navigation metadata

**Size:** ~100-200 words

**Purpose:** Determine if skill should activate

**Example:**
```yaml
---
name: mcp-builder
description: Create high-quality MCP servers that enable LLMs to effectively interact with external services. Use when building MCP integrations for APIs or services in Python (FastMCP) or Node/TypeScript (MCP SDK).
progressive_disclosure:
  entry_point:
    summary: "Build agent-friendly MCP servers through research-driven design"
    when_to_use: "When integrating external APIs/services via MCP protocol"
    quick_start: "1. Research 2. Plan 3. Implement 4. Evaluate 5. Iterate"
  references:
    - design_principles.md
    - workflow.md
```

### Level 2: Entry Point (Loaded on Activation)

**Content:** SKILL.md body
- Overview
- When to Use
- Core Principles (brief)
- Quick Start
- Navigation to references
- Key reminders and warnings

**Size:** 140-160 lines (optimal), <200 lines (maximum)

**Purpose:** Orient Claude to skill's approach and provide quick start

**What to Include:**
- Essential workflow overview
- Activation conditions
- Core principles (summary)
- Critical warnings
- Navigation to detailed references

**What to Exclude:**
- Detailed step-by-step procedures (→ workflow reference)
- Complete specifications (→ technical reference)
- Extensive examples (→ examples reference)
- Best practice details (→ best practices reference)
- Advanced patterns (→ advanced reference)

### Level 3: References (Loaded as Needed)

**Content:** Reference files in `references/` directory
- Detailed workflows
- Technical specifications
- Examples and templates
- Best practices
- Advanced patterns

**Size:** 150-500 lines per file, 3-5 files typical

**Purpose:** Provide deep detail when Claude determines it's needed

**Organization Patterns:**
- By topic (design, workflow, evaluation)
- By role (developer, designer, architect)
- By phase (planning, implementation, testing)
- By complexity (basics, intermediate, advanced)

## Implementing Progressive Disclosure

### Step 1: Analyze Current Skill

Review existing skill to identify:

1. **Essential content** - Needed for every task
2. **Conditional content** - Needed for specific scenarios
3. **Reference content** - Looked up as needed
4. **Natural boundaries** - Topic divisions

**Analysis questions:**
- What must Claude know immediately?
- What can wait until needed?
- What topics cluster together?
- Where are natural section breaks?

### Step 2: Plan Reference Organization

Design 3-5 reference files based on:
- Topic clustering
- Usage patterns
- Content size balance
- Logical flow

**Common reference patterns:**

**Technical Skills:**
- `structure.md` - Architecture and components
- `workflow.md` - Step-by-step processes
- `best-practices.md` - Quality guidelines
- `examples.md` - Templates and samples

**Domain Skills:**
- `fundamentals.md` - Core concepts
- `procedures.md` - Standard workflows
- `reference-data.md` - Schemas, APIs, specs
- `advanced.md` - Complex scenarios

**Tool Integration Skills:**
- `getting-started.md` - Setup and basics
- `api-reference.md` - Complete API docs
- `patterns.md` - Common usage patterns
- `troubleshooting.md` - Error handling

### Step 3: Add Progressive Disclosure Frontmatter

Add to YAML frontmatter:

```yaml
progressive_disclosure:
  entry_point:
    summary: "One-sentence core workflow description"
    when_to_use: "Specific activation conditions and key priorities"
    quick_start: "5-step numbered workflow (1. First 2. Second ...)"
  references:
    - first-reference.md
    - second-reference.md
    - third-reference.md
```

**Guidelines:**
- `summary:` - One sentence, focus on outcome
- `when_to_use:` - Clear conditions, priorities, key principles
- `quick_start:` - Exactly 5 numbered steps
- `references:` - List in logical reading order

### Step 4: Refactor Entry Point

Reduce entry point to 140-160 lines by:

**Keep in Entry Point:**
- Overview (2-3 sentences)
- When to Use (clear activation)
- The Iron Law (if applicable)
- Core Principles (3-5 brief points)
- Quick Start (high-level workflow)
- Navigation (links to all references with descriptions)
- Key Reminders (critical points)
- Red Flags (stop conditions)
- Integration with Other Skills
- Real-World Impact (if applicable)

**Move to References:**
- Detailed step-by-step workflows → `workflow.md`
- Complete specifications → `structure.md` or technical reference
- Extensive examples → `examples.md`
- Best practice details → `best-practices.md`
- Advanced patterns → `advanced.md`

**Writing tips:**
- Each section: 5-15 lines maximum
- Use bullet points for scannability
- Link to references with context
- Avoid duplicating reference content

### Step 5: Create Reference Files

For each reference file:

**Header:**
```markdown
# Reference Topic Name

## Purpose

Brief description of what this reference covers and when to use it.
```

**Content organization:**
- Clear section headers
- Logical progression
- Self-contained (can be read independently)
- Cross-references to other references when needed

**Size targets:**
- Minimum: 150 lines (or combine with another reference)
- Optimal: 200-400 lines
- Maximum: 500 lines (consider splitting if larger)

### Step 6: Add Navigation

In entry point, create clear navigation:

```markdown
## Navigation

### Core Workflow
- **[🔄 Complete Workflow](./references/workflow.md)** - Detailed step-by-step process with decision trees and examples. Load when executing the full workflow.

### Technical Details
- **[🏗️ Skill Structure](./references/structure.md)** - Component architecture, file organization, and requirements. Load when designing skill layout.

### Implementation Guidance
- **[✅ Best Practices](./references/best-practices.md)** - Quality guidelines, patterns, and anti-patterns. Load when implementing or reviewing.

### Examples and Templates
- **[📚 Examples](./references/examples.md)** - Complete skill examples and templates. Load when starting new skill or seeking inspiration.
```

**Navigation best practices:**
- Use emoji for visual scanning
- Include brief description of content
- Mention when to load
- Group related references
- Order by typical usage flow

## Real-World Examples

### Example 1: mcp-builder (209 → 160 lines)

**Before:** Monolithic 209-line SKILL.md

**After:** Progressive disclosure with 6 references
- Entry: 160 lines (23% reduction)
- `design_principles.md` - Agent-centric design philosophy
- `workflow.md` - 4-phase development process
- `mcp_best_practices.md` - Universal MCP guidelines
- `python_mcp_server.md` - Python implementation patterns
- `node_mcp_server.md` - TypeScript implementation patterns
- `evaluation.md` - Testing and iteration

**Impact:**
- Simple tasks load 160 lines (vs 209)
- Complex tasks load ~600 lines total (entry + relevant references)
- Clear separation by concern
- Easier to maintain and update

### Example 2: testing-anti-patterns (Long → 140 lines)

**Before:** Lengthy monolithic content

**After:** Progressive disclosure with 4 references
- Entry: 140 lines (optimal size)
- `core-anti-patterns.md` - Patterns 1-3
- `completeness-anti-patterns.md` - Patterns 4-5
- `detection-guide.md` - Red flags and gates
- `tdd-connection.md` - Prevention through TDD

**Impact:**
- Ultra-lean entry point
- Deep detail available when needed
- Organized by anti-pattern category
- Easy to reference specific patterns

### Example 3: skill-creator (This Skill!)

**Before:** Monolithic 209-line SKILL.md

**After:** Progressive disclosure with 5 references
- Entry: 150 lines (28% reduction)
- `skill-structure.md` - Architecture and components
- `creation-workflow.md` - 6-step process
- `progressive-disclosure.md` - This pattern guide
- `best-practices.md` - Quality and writing guidelines
- `examples.md` - Complete skill examples

**Meta-insight:** This skill demonstrates its own teachings by applying progressive disclosure!

## Progressive Disclosure Anti-Patterns

### ❌ Anti-Pattern 1: Duplicated Content

**Problem:** Same information in entry point AND references

**Example:**
```markdown
SKILL.md: "Follow these 5 steps: 1. Research 2. Plan ..."
workflow.md: "Step 1: Research. Step 2: Plan ..."
```

**Fix:** Entry has summary, reference has detail
```markdown
SKILL.md: "5-phase workflow: Research → Plan → Implement → Test → Iterate"
workflow.md: "## Phase 1: Research\n\n1. Load protocol docs\n2. Study API ..."
```

### ❌ Anti-Pattern 2: Over-Fragmentation

**Problem:** Too many tiny reference files

**Example:**
- `step1.md` (50 lines)
- `step2.md` (60 lines)
- `step3.md` (55 lines)

**Fix:** Combine related content
```markdown
workflow.md (250 lines with all steps)
```

### ❌ Anti-Pattern 3: Missing Navigation

**Problem:** References exist but entry point doesn't mention them

**Fix:** Explicit navigation section with descriptions

### ❌ Anti-Pattern 4: Bloated Entry Point

**Problem:** Entry point still >200 lines after "refactoring"

**Fix:** Move more content to references, keep only essentials in entry

### ❌ Anti-Pattern 5: Unclear Reference Purpose

**Problem:** Generic filenames, no description of content

**Fix:** Descriptive names, clear navigation descriptions

## When NOT to Use Progressive Disclosure

Progressive disclosure adds organizational complexity. Skip it when:

1. **Skill is simple** - <150 lines total
2. **Content doesn't subdivide** - No natural topic boundaries
3. **Always need everything** - No conditional content
4. **Single workflow** - Linear process, no branching

**Example skills that DON'T need progressive disclosure:**
- Simple code formatters
- Basic file converters
- Trivial workflows
- Single-purpose tools

## Success Metrics

A well-implemented progressive disclosure skill:

- ✅ Entry point: 140-160 lines (optimal) or <200 lines (maximum)
- ✅ 3-5 reference files
- ✅ Each reference: 150-500 lines
- ✅ Clear navigation with descriptions
- ✅ No content duplication
- ✅ Logical topic organization
- ✅ 20-30% reduction from original entry point
- ✅ Maintained or increased total depth
- ✅ Improved usability and discoverability

## Implementation Checklist

Before claiming progressive disclosure is complete:

- [ ] Progressive disclosure frontmatter added to YAML
- [ ] Entry point reduced to <200 lines (optimal: 140-160)
- [ ] 3-5 reference files created
- [ ] Each reference 150-500 lines
- [ ] Clear navigation section in entry point
- [ ] No duplicated content between entry and references
- [ ] Descriptive reference filenames
- [ ] Each reference has clear purpose
- [ ] References organized by logical topics
- [ ] Cross-references added where needed
- [ ] All sections follow imperative voice
- [ ] Examples reference the pattern being taught (for meta-skills)

## The Meta-Lesson

This very document demonstrates progressive disclosure:

**Entry point (SKILL.md):**
- What skills are
- Why create them
- Quick 6-step overview
- Navigation to details

**This reference (progressive-disclosure.md):**
- Deep dive into the pattern
- Implementation guide
- Anti-patterns
- Examples
- Best practices

**Other references:**
- Detailed workflow steps
- Skill structure specifications
- Examples and templates
- Quality guidelines

**By organizing content this way, we practice what we preach.**
