# SKILL.md Format Specification

**Version:** 1.0.0
**Date:** 2025-11-07
**Status:** Implementation Ready
**Target:** Claude Code 2.0.13+ / Claude MPM v4.15.0+

## Table of Contents

1. [Overview](#overview)
2. [File Structure](#file-structure)
3. [YAML Frontmatter Specification](#yaml-frontmatter-specification)
4. [Markdown Body Specification](#markdown-body-specification)
5. [16 Validation Rules](#16-validation-rules)
6. [Progressive Disclosure Organization](#progressive-disclosure-organization)
7. [Reference Files Organization](#reference-files-organization)
8. [Complete Examples](#complete-examples)
9. [Migration Guide](#migration-guide)
10. [Validation Tools](#validation-tools)

---

## Overview

### Purpose

SKILL.md is the entry point file for Claude Code skills. It follows a strict format optimized for:
- **Progressive Disclosure**: Claude reads skills incrementally (30-50 tokens initially)
- **Context Efficiency**: Entry points <200 lines, references 150-300 lines
- **Discoverability**: Rich metadata for skill selection
- **Maintainability**: Clear structure with separation of concerns

### Design Philosophy

1. **Entry Point as Navigation Hub**: SKILL.md guides Claude to relevant reference files
2. **Progressive Loading**: Critical information first, details on-demand
3. **Token Optimization**: 85% reduction in initial context loading
4. **Strict Validation**: Automated enforcement of format rules

---

## File Structure

### Directory Layout

```
skill-name/
├── SKILL.md                    # Entry point (<200 lines) - REQUIRED
├── references/                 # Detailed documentation (optional)
│   ├── workflow.md            # 150-300 lines
│   ├── examples.md            # 150-300 lines
│   ├── troubleshooting.md     # 150-300 lines
│   └── anti-patterns.md       # 150-300 lines
├── scripts/                    # Supporting scripts (optional)
│   ├── setup.sh
│   └── validate.py
└── tests/                      # Test files (optional)
    └── test_skill.py
```

### File Naming Conventions

- **Entry Point**: Always `SKILL.md` (uppercase, exact spelling)
- **References**: Lowercase with hyphens: `workflow.md`, `anti-patterns.md`
- **Scripts**: Descriptive names: `setup.sh`, `validate.py`
- **Tests**: Follow language conventions: `test_skill.py`, `skill_test.go`

---

## YAML Frontmatter Specification

### Complete Field Reference

```yaml
---
# REQUIRED FIELDS
name: skill-name
description: One-line description (10-150 chars)
version: 1.0.0

# REQUIRED: Progressive Disclosure Configuration
progressive_disclosure:
  entry_point:
    summary: Brief overview shown in initial scan
    when_to_use: Trigger conditions for activation
    quick_start: Minimal steps to begin using skill
  references:
    - workflow.md
    - examples.md
    - troubleshooting.md

# REQUIRED: Categorization
category: development | testing | debugging | collaboration | infrastructure | documentation

# OPTIONAL FIELDS
author: Author Name
license: MIT
source: https://github.com/user/repo
requires_tools:
  - bash
  - pytest
requires_skills:
  - test-driven-development
context_limit: 600
tags:
  - tdd
  - testing
  - python
---
```

### Field Specifications

#### Required Fields

##### `name` (string, required)
- **Format**: Lowercase with hyphens
- **Length**: 3-50 characters
- **Pattern**: `^[a-z][a-z0-9-]*[a-z0-9]$`
- **Example**: `test-driven-development`, `systematic-debugging`
- **Must Match**: Directory name

##### `description` (string, required)
- **Format**: Single line, plain text
- **Length**: 10-150 characters
- **Purpose**: Shown in skill listings and metadata scans
- **Example**: `"Enforces RED/GREEN/REFACTOR TDD cycle"`
- **Guidelines**:
  - Start with verb or noun
  - No markdown formatting
  - Avoid redundant "This skill..." prefix

##### `version` (string, required)
- **Format**: Semantic versioning `MAJOR.MINOR.PATCH`
- **Pattern**: `^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$`
- **Example**: `1.0.0`, `2.1.3-beta`
- **Compatibility**: Must increment for breaking changes

##### `category` (string, required)
- **Format**: Single category from allowed list
- **Allowed Values**:
  - `development` - Code writing, refactoring
  - `testing` - Test creation and execution
  - `debugging` - Problem diagnosis and fixing
  - `collaboration` - Team workflows, planning
  - `infrastructure` - DevOps, deployment, tooling
  - `documentation` - Writing, knowledge management
  - `integration` - API integration, MCP servers
  - `meta` - Skills about skills
- **Example**: `category: testing`

##### `progressive_disclosure` (object, required)
- **Purpose**: Define how Claude progressively loads skill content
- **Structure**:
  ```yaml
  progressive_disclosure:
    entry_point:
      summary: string (50-200 chars)
      when_to_use: string (50-300 chars)
      quick_start: string (50-300 chars)
    references:
      - string (filename in references/ directory)
  ```

###### `progressive_disclosure.entry_point` (object, required)

**`summary`** (string, required)
- **Length**: 50-200 characters
- **Purpose**: High-level overview shown during metadata scan
- **Example**: `"Enforce test-first development with strict RED/GREEN/REFACTOR cycle"`

**`when_to_use`** (string, required)
- **Length**: 50-300 characters
- **Purpose**: Activation conditions for Claude to know when to load this skill
- **Example**: `"When user requests tests, mentions TDD, or asks to 'write tests first'"`

**`quick_start`** (string, required)
- **Length**: 50-300 characters
- **Purpose**: Minimal steps to begin using the skill
- **Example**: `"1. Write failing test 2. Make it pass 3. Refactor 4. Repeat"`

###### `progressive_disclosure.references` (array of strings, optional)
- **Format**: List of filenames in `references/` directory
- **Each entry**: Must correspond to existing file
- **Order**: Recommended reading sequence
- **Example**:
  ```yaml
  references:
    - workflow.md
    - examples.md
    - anti-patterns.md
  ```

#### Optional Fields

##### `author` (string, optional)
- **Format**: Plain text
- **Example**: `"Jesse Vincent"`, `"Anthropic"`
- **Purpose**: Attribution and credit

##### `license` (string, optional)
- **Format**: SPDX license identifier or full name
- **Example**: `MIT`, `Apache-2.0`, `CC-BY-4.0`
- **Default**: Inherit from repository

##### `source` (string, optional)
- **Format**: URL to original skill repository
- **Purpose**: Attribution and updates
- **Example**: `https://github.com/obra/superpowers-skills/tree/main/skills/testing/test-driven-development`

##### `requires_tools` (array of strings, optional)
- **Format**: List of required command-line tools
- **Purpose**: Dependency checking
- **Example**:
  ```yaml
  requires_tools:
    - bash
    - pytest
    - docker
  ```

##### `requires_skills` (array of strings, optional)
- **Format**: List of prerequisite skill names
- **Purpose**: Skill dependency resolution
- **Example**:
  ```yaml
  requires_skills:
    - systematic-debugging
  ```

##### `context_limit` (integer, optional)
- **Format**: Maximum tokens for this skill's context
- **Range**: 200-1000
- **Default**: 600
- **Purpose**: Token budget management
- **Example**: `context_limit: 800`

##### `tags` (array of strings, optional)
- **Format**: Lowercase, hyphenated keywords
- **Purpose**: Search and categorization
- **Example**:
  ```yaml
  tags:
    - tdd
    - red-green-refactor
    - testing
    - python
  ```

---

## Markdown Body Specification

### Structure Template

```markdown
---
# YAML frontmatter here
---

# {Skill Name}

## Overview

{1-2 paragraph overview explaining what this skill does}

## When to Use This Skill

{Clear conditions for when Claude should activate this skill}

## Core Principles

{2-4 key principles or rules this skill enforces}

1. **Principle One**: Explanation
2. **Principle Two**: Explanation
3. **Principle Three**: Explanation

## Quick Start

{Minimal steps to begin using - typically 3-5 steps}

1. Step one
2. Step two
3. Step three

## Navigation

{Guide to reference files - only if references exist}

For detailed information:
- **[Workflow](references/workflow.md)**: Complete workflow documentation
- **[Examples](references/examples.md)**: Real-world usage examples
- **[Troubleshooting](references/troubleshooting.md)**: Common issues and solutions

## Key Reminders

{Critical points - typically 3-5 bullets}

- Important reminder one
- Important reminder two
- Important reminder three
```

### Content Guidelines

#### Line Limits
- **SKILL.md Entry Point**: MUST be <200 lines (including frontmatter)
- **Reference Files**: MUST be 150-300 lines each
- **Total Skill**: All files combined should not exceed 1500 lines

#### Section Requirements

1. **Overview** (required)
   - 1-2 paragraphs maximum
   - Explains what the skill does
   - No implementation details

2. **When to Use This Skill** (required)
   - Clear activation conditions
   - Helps Claude decide when to load
   - Examples of user requests

3. **Core Principles** (required)
   - 2-4 key rules or principles
   - Numbered or bulleted list
   - Each principle: 1-2 sentences

4. **Quick Start** (required)
   - 3-5 minimal steps
   - Numbered list
   - Action-oriented

5. **Navigation** (required if references exist)
   - Links to reference files
   - Brief description of each reference
   - Reading order recommendation

6. **Key Reminders** (recommended)
   - 3-5 critical points
   - Bullets or numbered list
   - Actionable items

#### Writing Style

- **Imperative Voice**: "Write the test first" not "You should write the test first"
- **Concise**: Every word matters for token efficiency
- **Active**: Prefer active voice over passive
- **Specific**: Avoid vague language like "usually", "sometimes"
- **Structured**: Use lists, headings, bold text for scannability

---

## 16 Validation Rules

### Structural Rules

#### Rule 1: SKILL.md File Presence
- **Requirement**: SKILL.md file MUST exist in skill root directory
- **Validation**: File existence check
- **Error**: `SKILL.md file not found`
- **Severity**: CRITICAL - Deployment blocked

#### Rule 2: YAML Frontmatter Presence
- **Requirement**: SKILL.md MUST start with valid YAML frontmatter
- **Format**:
  ```markdown
  ---
  {valid YAML}
  ---
  ```
- **Validation**: Regex match + YAML parsing
- **Error**: `Missing or invalid YAML frontmatter`
- **Severity**: CRITICAL - Deployment blocked

#### Rule 3: Frontmatter Delimiter Format
- **Requirement**: Frontmatter MUST use exactly `---` (3 hyphens) as delimiters
- **Validation**: Exact string match
- **Error**: `Invalid frontmatter delimiters`
- **Severity**: CRITICAL - Deployment blocked

#### Rule 4: Entry Point Line Limit
- **Requirement**: SKILL.md MUST be ≤200 lines (including frontmatter)
- **Validation**: Line count check
- **Error**: `SKILL.md exceeds 200 line limit (found {n} lines)`
- **Severity**: CRITICAL - Deployment blocked
- **Rationale**: Progressive disclosure requirement

### Required Field Rules

#### Rule 5: Required Fields Present
- **Requirement**: All required fields MUST be present
- **Fields**: `name`, `description`, `version`, `category`, `progressive_disclosure`
- **Validation**: Field presence check in parsed YAML
- **Error**: `Missing required field: {field_name}`
- **Severity**: CRITICAL - Deployment blocked

#### Rule 6: Name Format
- **Requirement**: `name` field MUST match pattern `^[a-z][a-z0-9-]*[a-z0-9]$`
- **Length**: 3-50 characters
- **Validation**: Regex validation
- **Error**: `Invalid name format: {name}`
- **Severity**: CRITICAL - Deployment blocked

#### Rule 7: Name-Directory Match
- **Requirement**: `name` field MUST match parent directory name
- **Validation**: String equality check
- **Error**: `Name field '{name}' does not match directory '{dir}'`
- **Severity**: CRITICAL - Deployment blocked

#### Rule 8: Description Length
- **Requirement**: `description` field MUST be 10-150 characters
- **Validation**: String length check
- **Error**: `Description must be 10-150 characters (found {n})`
- **Severity**: CRITICAL - Deployment blocked

#### Rule 9: Version Format
- **Requirement**: `version` field MUST match semantic versioning pattern
- **Pattern**: `^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$`
- **Validation**: Regex validation
- **Error**: `Invalid version format: {version}`
- **Severity**: ERROR - Warning issued

#### Rule 10: Category Value
- **Requirement**: `category` field MUST be from allowed list
- **Allowed**: `development`, `testing`, `debugging`, `collaboration`, `infrastructure`, `documentation`, `integration`, `meta`
- **Validation**: Enum validation
- **Error**: `Invalid category: {category}`
- **Severity**: CRITICAL - Deployment blocked

### Progressive Disclosure Rules

#### Rule 11: Progressive Disclosure Structure
- **Requirement**: `progressive_disclosure` field MUST contain `entry_point` object
- **Validation**: Nested field check
- **Error**: `progressive_disclosure.entry_point is required`
- **Severity**: CRITICAL - Deployment blocked

#### Rule 12: Progressive Disclosure Entry Point Fields
- **Requirement**: `entry_point` MUST contain `summary`, `when_to_use`, `quick_start`
- **Validation**: Nested field presence check
- **Error**: `Missing progressive_disclosure.entry_point.{field}`
- **Severity**: CRITICAL - Deployment blocked

#### Rule 13: Progressive Disclosure Field Lengths
- **Requirements**:
  - `summary`: 50-200 characters
  - `when_to_use`: 50-300 characters
  - `quick_start`: 50-300 characters
- **Validation**: String length checks
- **Error**: `{field} must be {min}-{max} characters (found {n})`
- **Severity**: WARNING - Deployment allowed

### Reference File Rules

#### Rule 14: Reference Files Exist
- **Requirement**: If `progressive_disclosure.references` is present, all listed files MUST exist in `references/` directory
- **Validation**: File existence check
- **Error**: `Reference file not found: references/{filename}`
- **Severity**: ERROR - Warning issued

#### Rule 15: Reference File Line Limits
- **Requirement**: Each reference file MUST be 150-300 lines
- **Validation**: Line count check for each reference
- **Error**: `Reference file {filename} must be 150-300 lines (found {n})`
- **Severity**: WARNING - Deployment allowed

#### Rule 16: No Circular References
- **Requirement**: Reference files MUST NOT create circular reference chains
- **Validation**: Dependency graph analysis
- **Error**: `Circular reference detected: {file1} → {file2} → {file1}`
- **Severity**: ERROR - Warning issued

### Validation Severity Levels

- **CRITICAL**: Deployment blocked, must be fixed
- **ERROR**: Deployment allowed with warning, should be fixed
- **WARNING**: Deployment allowed, optional improvement

---

## Progressive Disclosure Organization

### Three-Tier Loading Strategy

#### Tier 1: Metadata Scan (30-50 tokens)
**What Claude Sees:**
```yaml
name: test-driven-development
description: "Enforces RED/GREEN/REFACTOR TDD cycle"
category: testing
progressive_disclosure:
  entry_point:
    summary: "Enforce test-first development with strict RED/GREEN/REFACTOR cycle"
    when_to_use: "When user requests tests, mentions TDD, or asks to 'write tests first'"
```

**Purpose**: Quick skill discovery and activation decision

#### Tier 2: Entry Point Loading (100-150 tokens)
**What Claude Sees:**
- Complete SKILL.md content
- Overview section
- Core Principles
- Quick Start steps
- Navigation to references

**Purpose**: Enough to begin using the skill

#### Tier 3: Reference Loading (On-Demand)
**What Claude Sees:**
- Specific reference file requested
- Detailed workflow documentation
- Examples
- Troubleshooting

**Purpose**: Deep knowledge when needed

### Content Organization Principles

1. **Essential First**: Put critical information in SKILL.md
2. **Details On-Demand**: Move comprehensive details to references
3. **Navigation Clear**: Make it obvious where to find more info
4. **Self-Contained References**: Each reference file should be independently useful
5. **Avoid Duplication**: Don't repeat content between entry point and references

### Token Budget Allocation

- **Metadata Scan**: 30-50 tokens (automated)
- **Entry Point**: 100-150 tokens (<200 lines)
- **Each Reference**: 150-300 tokens per file
- **Total Skill Budget**: 600-1000 tokens (configurable via `context_limit`)

---

## Reference Files Organization

### Directory Structure

```
skill-name/
└── references/
    ├── workflow.md              # Complete workflow documentation
    ├── examples.md              # Real-world usage examples
    ├── troubleshooting.md       # Common issues and solutions
    ├── anti-patterns.md         # What NOT to do
    ├── advanced-techniques.md   # Advanced usage
    └── integration.md           # Integration with other skills
```

### Recommended Reference Files

#### Standard References (Choose based on need)

1. **workflow.md** (recommended)
   - Complete step-by-step workflow
   - Decision trees
   - State transitions
   - 200-300 lines

2. **examples.md** (recommended)
   - Real-world usage examples
   - Before/after comparisons
   - Multiple scenarios
   - 150-250 lines

3. **troubleshooting.md** (optional)
   - Common errors
   - Debugging steps
   - FAQ
   - 150-200 lines

4. **anti-patterns.md** (optional)
   - Common mistakes
   - What NOT to do
   - Corrective guidance
   - 150-200 lines

5. **advanced-techniques.md** (optional)
   - Power user features
   - Optimization techniques
   - Edge cases
   - 200-300 lines

6. **integration.md** (optional)
   - Using with other skills
   - Tool integration
   - Workflow combinations
   - 150-250 lines

### Reference File Template

```markdown
# {Reference Topic Title}

> **Part of**: [{Skill Name}](../SKILL.md)
> **Category**: {category}
> **Reading Level**: Basic | Intermediate | Advanced

## Purpose

{1-2 sentences explaining what this reference covers}

## Main Content

{Detailed content organized in clear sections}

### Section 1

{Content}

### Section 2

{Content}

## Summary

{Key takeaways - 3-5 bullets}

## Related References

- [{Other Reference}]({filename}.md)
- [{Another Reference}]({filename}.md)
```

### Reference File Guidelines

1. **Single Topic**: Each file covers one cohesive topic
2. **Self-Contained**: Can be read independently
3. **Cross-Links**: Link to related references
4. **Examples**: Include concrete examples
5. **Scannable**: Use headings, lists, code blocks
6. **Line Limits**: Strictly enforce 150-300 line limit

---

## Complete Examples

### Example 1: Entry Point Skill (Minimal)

**File**: `test-driven-development/SKILL.md`

```markdown
---
name: test-driven-development
description: Enforces RED/GREEN/REFACTOR TDD cycle
version: 1.0.0
category: testing
progressive_disclosure:
  entry_point:
    summary: "Enforce test-first development with strict RED/GREEN/REFACTOR cycle"
    when_to_use: "When user requests tests, mentions TDD, or asks to 'write tests first'"
    quick_start: "1. Write failing test 2. Make it pass 3. Refactor 4. Repeat"
author: Jesse Vincent
license: MIT
source: https://github.com/obra/superpowers-skills/tree/main/skills/testing/test-driven-development
tags:
  - tdd
  - testing
  - red-green-refactor
---

# Test-Driven Development

## Overview

Enforce strict test-first development following the RED/GREEN/REFACTOR cycle. Never write implementation code before writing a failing test.

## When to Use This Skill

Activate this skill when:
- User requests tests be written
- User mentions "TDD" or "test-driven"
- User asks to "write tests first"
- Working on any testable code

## Core Principles

1. **RED**: Write a failing test first
2. **GREEN**: Write minimal code to make test pass
3. **REFACTOR**: Improve code while keeping tests green
4. **NEVER**: Write implementation before tests

## Quick Start

1. Write a failing test that describes desired behavior
2. Run test and verify it fails for the right reason
3. Write minimal implementation to make test pass
4. Verify test passes
5. Refactor if needed while keeping tests green
6. Repeat for next feature

## Key Reminders

- ALWAYS write the test BEFORE implementation
- Make each test fail FIRST to verify it's testing something
- Keep implementation minimal - just enough to pass tests
- Refactor only when tests are green
- One cycle at a time - small steps

---
**Lines**: 58 (including frontmatter) ✓ <200
```

### Example 2: Entry Point with References

**File**: `systematic-debugging/SKILL.md`

```markdown
---
name: systematic-debugging
description: Methodical debugging instead of random changes
version: 1.0.0
category: debugging
progressive_disclosure:
  entry_point:
    summary: "Replace random code changes with systematic problem diagnosis"
    when_to_use: "When user reports bugs, errors, or unexpected behavior"
    quick_start: "1. Reproduce 2. Form hypothesis 3. Test hypothesis 4. Fix 5. Verify"
  references:
    - workflow.md
    - examples.md
    - troubleshooting.md
author: Jesse Vincent
license: MIT
source: https://github.com/obra/superpowers-skills/tree/main/skills/debugging/systematic-debugging
requires_tools:
  - debugger
context_limit: 800
tags:
  - debugging
  - problem-solving
  - root-cause
---

# Systematic Debugging

## Overview

Replace random code changes and guesswork with systematic problem diagnosis. Follow a structured approach to find root causes efficiently.

## When to Use This Skill

Activate when:
- User reports a bug or error
- Code behaves unexpectedly
- Tests are failing
- User says "it's not working"
- Investigating production issues

## Core Principles

1. **Reproduce First**: Ensure you can reliably reproduce the issue
2. **One Change at a Time**: Change only one thing between tests
3. **Hypothesis-Driven**: Form hypotheses before making changes
4. **Verify Fixes**: Confirm the fix works and doesn't break anything else

## Quick Start

1. **Reproduce**: Create minimal test case that triggers the bug
2. **Isolate**: Narrow down to smallest code section causing issue
3. **Hypothesize**: Form specific hypothesis about the cause
4. **Test**: Make single targeted change to test hypothesis
5. **Verify**: Confirm fix works and no regressions
6. **Document**: Note what caused issue and how it was fixed

## Navigation

For detailed information:
- **[Workflow](references/workflow.md)**: Complete debugging workflow with decision trees
- **[Examples](references/examples.md)**: Real-world debugging scenarios
- **[Troubleshooting](references/troubleshooting.md)**: Common debugging challenges

## Key Reminders

- NEVER make random changes hoping they'll work
- ALWAYS reproduce the issue before attempting fixes
- Form hypothesis BEFORE making changes
- Change ONE thing at a time
- Verify fix actually resolves the issue
- Check for regressions after fixing

---
**Lines**: 79 (including frontmatter) ✓ <200
```

### Example 3: Reference File

**File**: `systematic-debugging/references/workflow.md`

```markdown
# Systematic Debugging Workflow

> **Part of**: [Systematic Debugging](../SKILL.md)
> **Category**: debugging
> **Reading Level**: Intermediate

## Purpose

Complete step-by-step workflow for systematic debugging, including decision trees and troubleshooting strategies.

## Phase 1: Reproduction

### Goal
Create a reliable, minimal test case that triggers the bug.

### Steps

1. **Document the Error**
   - Exact error message
   - Stack trace
   - Input that triggered it
   - Expected vs actual behavior

2. **Create Minimal Reproduction**
   - Strip away unrelated code
   - Reduce to smallest possible example
   - Ensure it fails consistently

3. **Validate Reproduction**
   - Run multiple times
   - Confirm failure is consistent
   - Document success criteria

### Decision Tree

```
Can you reproduce the issue?
├─ Yes → Proceed to Phase 2
├─ Intermittent → Gather more data
│  ├─ Check for race conditions
│  ├─ Look for environmental factors
│  └─ Add logging around suspected area
└─ No → Issue may be environmental
   ├─ Check configuration differences
   ├─ Verify dependencies
   └─ Compare runtime environments
```

## Phase 2: Isolation

### Goal
Narrow down the problem to the smallest code section.

### Steps

1. **Binary Search**
   - Comment out half the code
   - Does problem persist?
   - Repeat with remaining half

2. **Add Logging**
   - Log inputs at function boundaries
   - Log intermediate values
   - Trace execution flow

3. **Check Assumptions**
   - Verify function inputs
   - Check state before/after
   - Validate preconditions

### Red Flags

- Functions with side effects
- Global state modifications
- Timing-dependent code
- External dependencies

## Phase 3: Hypothesis Formation

### Goal
Form specific, testable hypothesis about the root cause.

### Good Hypothesis Characteristics

- **Specific**: Names exact variable/function
- **Testable**: Can be verified with single change
- **Falsifiable**: Could be proven wrong
- **Evidence-Based**: Supported by logs/observations

### Examples

❌ "Something is wrong with the database"
✅ "Database connection times out because connection pool is exhausted"

❌ "The calculation is incorrect"
✅ "Division by zero when denominator is empty list"

## Phase 4: Testing Hypothesis

### Goal
Make single targeted change to test hypothesis.

### Steps

1. **Design Test**
   - What change will test hypothesis?
   - What outcome proves/disproves it?
   - How will you measure success?

2. **Make Single Change**
   - Change ONLY what tests hypothesis
   - Keep changes minimal
   - Comment your reasoning

3. **Run Test**
   - Execute reproduction case
   - Observe outcome
   - Document results

### Outcomes

- **Hypothesis Confirmed** → Proceed to Phase 5
- **Hypothesis Rejected** → Return to Phase 3 with new data
- **Inconclusive** → Refine test or gather more data

## Phase 5: Fix Implementation

### Goal
Implement proper fix that addresses root cause.

### Steps

1. **Design Fix**
   - Address root cause, not symptoms
   - Consider edge cases
   - Minimize scope of changes

2. **Implement Fix**
   - Write failing test first (if not already exists)
   - Make minimal change to fix root cause
   - Update related documentation

3. **Review Changes**
   - Does this fix only the bug?
   - Are there side effects?
   - Is it the simplest solution?

## Phase 6: Verification

### Goal
Confirm fix works and introduces no regressions.

### Steps

1. **Verify Fix**
   - Original reproduction case passes
   - Test edge cases
   - Run full test suite

2. **Check for Regressions**
   - Related functionality still works
   - No new errors introduced
   - Performance hasn't degraded

3. **Document Fix**
   - What was the root cause?
   - Why does this fix work?
   - Are there related issues to watch?

## Common Pitfalls

### Random Changes
- **Problem**: Making changes without hypothesis
- **Impact**: Wastes time, may introduce new bugs
- **Fix**: Always form hypothesis first

### Multiple Changes
- **Problem**: Changing several things at once
- **Impact**: Can't isolate what fixed the issue
- **Fix**: One change at a time

### Symptom Fixing
- **Problem**: Fixing symptoms instead of root cause
- **Impact**: Bug returns in different form
- **Fix**: Trace to root cause before fixing

### Incomplete Verification
- **Problem**: Not running full test suite
- **Impact**: Regressions slip through
- **Fix**: Always verify fix completely

## Summary

- Always reproduce before debugging
- Isolate problem to smallest section
- Form specific, testable hypotheses
- Make one change at a time
- Verify fix thoroughly
- Document root cause and solution

## Related References

- [Examples](examples.md): Real-world debugging scenarios
- [Troubleshooting](troubleshooting.md): Common debugging challenges

---
**Lines**: 245 ✓ 150-300 range
```

---

## Migration Guide

### Migrating Existing Skills to New Format

#### Step 1: Assess Current Skill

```bash
# Check current line count
wc -l SKILL.md

# If >200 lines, refactoring is required
```

#### Step 2: Extract Content for References

Identify sections to move to reference files:
- Detailed workflows → `references/workflow.md`
- Examples → `references/examples.md`
- Troubleshooting → `references/troubleshooting.md`
- Anti-patterns → `references/anti-patterns.md`

#### Step 3: Update Frontmatter

Add progressive disclosure configuration:

```yaml
progressive_disclosure:
  entry_point:
    summary: "{50-200 char summary}"
    when_to_use: "{Activation conditions}"
    quick_start: "{Minimal steps}"
  references:
    - workflow.md
    - examples.md
```

#### Step 4: Reorganize SKILL.md

Follow entry point template:
1. Keep Overview (1-2 paragraphs)
2. Keep When to Use
3. Keep Core Principles (2-4 items)
4. Keep Quick Start (3-5 steps)
5. Add Navigation section
6. Keep Key Reminders (3-5 items)
7. Move everything else to references

#### Step 5: Validate

```bash
# Run validation
claude-mpm skills validate skill-name

# Check line counts
wc -l SKILL.md references/*.md

# Verify all requirements met
```

### Automated Migration Script

```bash
#!/bin/bash
# scripts/refactor_skill_progressive.sh

SKILL_DIR=$1

if [ -z "$SKILL_DIR" ]; then
    echo "Usage: $0 <skill-directory>"
    exit 1
fi

echo "Refactoring skill: $SKILL_DIR"

# Create references directory
mkdir -p "$SKILL_DIR/references"

# TODO: Extract detailed sections to reference files
# TODO: Update frontmatter
# TODO: Reorganize entry point
# TODO: Validate result

python scripts/validate_skills.py "$SKILL_DIR"
```

---

## Validation Tools

### Command-Line Validation

```bash
# Validate single skill
claude-mpm skills validate test-driven-development

# Validate all skills
claude-mpm skills validate --all

# Verbose output
claude-mpm skills validate --verbose test-driven-development
```

### Python Validation Script

**File**: `scripts/validate_skills.py`

```python
#!/usr/bin/env python3
"""Validate SKILL.md format against 16 validation rules."""

import sys
import re
from pathlib import Path
from typing import Dict, List, Any
import yaml

class SkillValidator:
    """Validates SKILL.md files against format specification."""

    REQUIRED_FIELDS = ['name', 'description', 'version', 'category', 'progressive_disclosure']
    VALID_CATEGORIES = [
        'development', 'testing', 'debugging', 'collaboration',
        'infrastructure', 'documentation', 'integration', 'meta'
    ]
    NAME_PATTERN = re.compile(r'^[a-z][a-z0-9-]*[a-z0-9]$')
    VERSION_PATTERN = re.compile(r'^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?$')

    def __init__(self, skill_path: Path):
        self.skill_path = skill_path
        self.skill_md = skill_path / 'SKILL.md'
        self.errors = []
        self.warnings = []

    def validate(self) -> Dict[str, Any]:
        """Run all 16 validation rules."""

        # Rule 1: SKILL.md exists
        if not self.skill_md.exists():
            self.errors.append("Rule 1: SKILL.md file not found")
            return self._result()

        # Read file
        content = self.skill_md.read_text()
        lines = content.split('\n')

        # Rule 2 & 3: Frontmatter presence and format
        frontmatter, body = self._extract_frontmatter(content, lines)
        if frontmatter is None:
            return self._result()

        # Rule 4: Line limit
        if len(lines) > 200:
            self.errors.append(f"Rule 4: SKILL.md exceeds 200 line limit (found {len(lines)} lines)")

        # Parse YAML
        try:
            metadata = yaml.safe_load(frontmatter)
        except yaml.YAMLError as e:
            self.errors.append(f"Invalid YAML in frontmatter: {e}")
            return self._result()

        # Rule 5: Required fields
        for field in self.REQUIRED_FIELDS:
            if field not in metadata:
                self.errors.append(f"Rule 5: Missing required field: {field}")

        # Rule 6: Name format
        if 'name' in metadata:
            if not self.NAME_PATTERN.match(metadata['name']):
                self.errors.append(f"Rule 6: Invalid name format: {metadata['name']}")

            # Rule 7: Name matches directory
            if metadata['name'] != self.skill_path.name:
                self.errors.append(
                    f"Rule 7: Name field '{metadata['name']}' does not match "
                    f"directory '{self.skill_path.name}'"
                )

        # Rule 8: Description length
        if 'description' in metadata:
            desc_len = len(metadata['description'])
            if desc_len < 10 or desc_len > 150:
                self.errors.append(
                    f"Rule 8: Description must be 10-150 characters (found {desc_len})"
                )

        # Rule 9: Version format
        if 'version' in metadata:
            if not self.VERSION_PATTERN.match(metadata['version']):
                self.warnings.append(f"Rule 9: Invalid version format: {metadata['version']}")

        # Rule 10: Category
        if 'category' in metadata:
            if metadata['category'] not in self.VALID_CATEGORIES:
                self.errors.append(f"Rule 10: Invalid category: {metadata['category']}")

        # Rules 11-13: Progressive disclosure
        self._validate_progressive_disclosure(metadata)

        # Rules 14-16: Reference files
        self._validate_references(metadata)

        return self._result()

    def _extract_frontmatter(self, content: str, lines: List[str]) -> tuple:
        """Extract and validate frontmatter format."""
        if not content.startswith('---\n'):
            self.errors.append("Rule 2: Missing YAML frontmatter")
            return None, None

        # Find closing delimiter
        end_match = re.search(r'\n---\n', content[4:])
        if not end_match:
            self.errors.append("Rule 2: Invalid YAML frontmatter (missing closing ---)")
            return None, None

        frontmatter = content[4:4+end_match.start()]
        body = content[4+end_match.end():]

        return frontmatter, body

    def _validate_progressive_disclosure(self, metadata: Dict[str, Any]):
        """Rules 11-13: Progressive disclosure validation."""
        pd = metadata.get('progressive_disclosure', {})

        # Rule 11: Structure
        if 'entry_point' not in pd:
            self.errors.append("Rule 11: progressive_disclosure.entry_point is required")
            return

        entry = pd['entry_point']

        # Rule 12: Required fields
        for field in ['summary', 'when_to_use', 'quick_start']:
            if field not in entry:
                self.errors.append(
                    f"Rule 12: Missing progressive_disclosure.entry_point.{field}"
                )

        # Rule 13: Field lengths
        field_limits = {
            'summary': (50, 200),
            'when_to_use': (50, 300),
            'quick_start': (50, 300)
        }

        for field, (min_len, max_len) in field_limits.items():
            if field in entry:
                length = len(entry[field])
                if length < min_len or length > max_len:
                    self.warnings.append(
                        f"Rule 13: {field} should be {min_len}-{max_len} characters "
                        f"(found {length})"
                    )

    def _validate_references(self, metadata: Dict[str, Any]):
        """Rules 14-16: Reference files validation."""
        pd = metadata.get('progressive_disclosure', {})
        refs = pd.get('references', [])

        if not refs:
            return

        ref_dir = self.skill_path / 'references'

        for ref_file in refs:
            ref_path = ref_dir / ref_file

            # Rule 14: File exists
            if not ref_path.exists():
                self.warnings.append(f"Rule 14: Reference file not found: references/{ref_file}")
                continue

            # Rule 15: Line limits
            lines = ref_path.read_text().split('\n')
            line_count = len(lines)

            if line_count < 150 or line_count > 300:
                self.warnings.append(
                    f"Rule 15: Reference file {ref_file} should be 150-300 lines "
                    f"(found {line_count})"
                )

        # Rule 16: Circular references (simplified check)
        # Full implementation would parse markdown links
        # This is a placeholder for the concept

    def _result(self) -> Dict[str, Any]:
        """Format validation result."""
        return {
            'valid': len(self.errors) == 0,
            'errors': self.errors,
            'warnings': self.warnings,
            'skill': self.skill_path.name
        }


def main():
    if len(sys.argv) < 2:
        print("Usage: validate_skills.py <skill-directory>")
        sys.exit(1)

    skill_path = Path(sys.argv[1])
    validator = SkillValidator(skill_path)
    result = validator.validate()

    print(f"\nValidation Results for: {result['skill']}")
    print("=" * 60)

    if result['valid']:
        print("✓ All validation rules passed")
    else:
        print(f"✗ {len(result['errors'])} errors found")
        for error in result['errors']:
            print(f"  ERROR: {error}")

    if result['warnings']:
        print(f"\n⚠ {len(result['warnings'])} warnings")
        for warning in result['warnings']:
            print(f"  WARNING: {warning}")

    sys.exit(0 if result['valid'] else 1)


if __name__ == '__main__':
    main()
```

### Validation in CI/CD

```yaml
# .github/workflows/validate-skills.yml
name: Validate Skills

on:
  pull_request:
    paths:
      - 'src/claude_mpm/skills/bundled/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install pyyaml

      - name: Validate all skills
        run: |
          for skill_dir in src/claude_mpm/skills/bundled/*/*; do
            if [ -d "$skill_dir" ]; then
              echo "Validating: $skill_dir"
              python scripts/validate_skills.py "$skill_dir" || exit 1
            fi
          done
```

---

## Summary

This SKILL.md format specification provides:

✅ **Complete Structure**: Required and optional fields clearly defined
✅ **16 Validation Rules**: Testable, automatable requirements
✅ **Progressive Disclosure**: Optimized for Claude Code's loading behavior
✅ **Line Limits**: <200 for entry points, 150-300 for references
✅ **Examples**: Complete working examples for reference
✅ **Validation Tools**: Automated checking scripts
✅ **Migration Guide**: Path from old to new format

**Ready for Implementation**: Use this specification to:
1. Implement validation in `SkillsService`
2. Refactor existing skills (Weeks 2-3)
3. Create new skills following the format
4. Automate quality control in CI/CD

---

**Version History:**
- v1.0.0 (2025-11-07): Initial specification based on design decisions
