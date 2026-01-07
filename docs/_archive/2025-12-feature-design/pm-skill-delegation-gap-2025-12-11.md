# PM Skill Management Delegation Gap Analysis

**Date**: 2025-12-11
**Issue**: PM doesn't know to delegate skill-related tasks to mpm-skills-manager agent
**Impact**: PM attempts direct skill operations or delegates to wrong agents (documentation)
**Priority**: HIGH - Breaks skill management workflow

---

## Executive Summary

The PM agent lacks delegation rules for skill-related tasks, causing it to:
1. Attempt non-existent skill operations (e.g., using `svelte-engineer` skill that doesn't exist)
2. Try to create skills directly instead of delegating to `mpm-skills-manager`
3. Delegate to wrong agents (e.g., `documentation` agent instead of `mpm-skills-manager`)

**Root Cause**: PM_INSTRUCTIONS.md lacks skill management delegation rules in both:
- "When to Delegate to Each Agent" section (lines 382-461)
- "Common User Request Patterns" section (lines 1435-1447)

---

## Detailed Findings

### 1. PM Instructions Source Files

**Primary Source**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/PM_INSTRUCTIONS.md`

**Key Sections**:
- **Lines 382-461**: "When to Delegate to Each Agent" - Missing mpm-skills-manager entry
- **Lines 1435-1447**: "Common User Request Patterns" - No skill-related keywords

**Current Agent Delegation Matrix** (lines 382-461):
```
✅ Research Agent (lines 384-393)
✅ Engineer Agent (lines 395-403)
✅ Ops Agent (lines 405-415)
✅ QA Agent (lines 417-425)
✅ Documentation Agent (lines 427-435)
✅ Ticketing Agent (lines 437-445)
✅ Version Control Agent (lines 447-461)
❌ MPM Skills Manager - MISSING
```

### 2. mpm-skills-manager Agent Definition

**Location**: `~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/claude-mpm/mpm-skills-manager.md`

**Agent Capabilities** (from agent file):
- **Technology Stack Detection**: Analyze project files to identify languages, frameworks, tools
- **Skill Discovery**: Parse manifest.json to find available skills
- **Skill Recommendation**: Match detected technologies to relevant skills
- **Skill Deployment**: Deploy skills to user or project directories
- **Manifest Management**: Update manifest.json with new skills or versions
- **PR-based Improvements**: Create pull requests for skill enhancements
- **Validation**: Ensure skill structure and manifest integrity

**Primary Objectives** (lines 69-73):
1. Help users discover skills relevant to their project
2. Improve existing skills based on user feedback
3. Create new skills for detected technologies
4. Maintain skill repository quality

**Key Technologies Detected** (lines 78-145):
- Python: requirements.txt, pyproject.toml, setup.py, Pipfile
- JavaScript/TypeScript: package.json, tsconfig.json
- Ruby: Gemfile
- Rust: Cargo.toml
- Go: go.mod
- Java: pom.xml, build.gradle

### 3. Current Delegation Gap

**Missing in PM Instructions**:

#### Section: "When to Delegate to Each Agent" (after line 461)

**Should Include**:
```markdown
### MPM Skills Manager Agent

Delegate when work involves:
- Creating or improving Claude Code skills
- Recommending skills based on project stack
- Technology stack detection and analysis
- Skill lifecycle management (deploy, update, remove)
- Updating skill manifest.json
- Creating PRs for skill repository contributions
- Validating skill structure and metadata

**Why MPM Skills Manager**: Manages complete skill lifecycle including discovery, recommendation, deployment, and PR-based improvements to skills repository.
```

#### Section: "Common User Request Patterns" (after line 1447)

**Should Include**:
```markdown
When the user mentions "skill", "add skill", "create skill", "recommend skills", "skill for [technology]", delegate to mpm-skills-manager agent for all skill operations.

When the user asks about project technology stack or framework detection, delegate to mpm-skills-manager agent for analysis.
```

### 4. Delegation Trigger Keywords

**User Request Patterns That Should Trigger mpm-skills-manager**:

**Skill Creation/Improvement**:
- "create skill for [technology]"
- "add [technology] skill"
- "improve [skill-name] skill"
- "update skill with [feature]"
- "skill is missing [pattern]"

**Skill Discovery/Recommendation**:
- "recommend skills"
- "what skills do I need"
- "skills for [framework]"
- "detect project stack"
- "suggest skills"

**Skill Management**:
- "deploy skill"
- "install skill"
- "update skills"
- "list skills"
- "remove skill"

**Technology Analysis**:
- "detect technologies"
- "analyze project stack"
- "what frameworks are we using"
- "identify dependencies"

### 5. Anti-Patterns Observed

**Current PM Behavior** (incorrect):
```
User: "Add a Svelte 5 Runes skill"
PM: Attempts to use non-existent "svelte-engineer" skill
PM: Tries to create skill content directly
PM: Eventually delegates to "documentation" agent
```

**Expected PM Behavior** (correct):
```
User: "Add a Svelte 5 Runes skill"
PM: Detects "skill" keyword in request
PM: Delegates to mpm-skills-manager agent
PM: mpm-skills-manager creates skill structure, updates manifest, creates PR
PM: Reports PR URL and next steps to user
```

### 6. Integration Points

**PM Should NOT**:
- Create skill files directly (SKILL.md, references/)
- Update manifest.json directly
- Create PRs to skills repository directly
- Attempt technology stack detection directly
- Recommend skills based on heuristics

**PM SHOULD**:
- Detect skill-related keywords in user requests
- Delegate ALL skill operations to mpm-skills-manager
- Report mpm-skills-manager results to user
- Track any skill files created locally (git workflow)

---

## Recommended Changes

### Change 1: Add MPM Skills Manager to Delegation Matrix

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/PM_INSTRUCTIONS.md`

**Location**: After line 461 (after Version Control Agent section)

**Add**:
```markdown
### MPM Skills Manager Agent

Delegate when work involves:
- Creating or improving Claude Code skills
- Recommending skills based on project technology stack
- Technology stack detection and analysis
- Skill lifecycle management (deploy, update, remove)
- Updating skill manifest.json
- Creating PRs for skill repository contributions
- Validating skill structure and metadata
- Skill discovery and search

**Why MPM Skills Manager**: Manages complete skill lifecycle including technology detection, discovery, recommendation, deployment, and PR-based improvements to skills repository. Has direct access to manifest.json, skill validation tools, and GitHub PR workflow integration.

**Skill-Related Keywords**: "skill", "add skill", "create skill", "improve skill", "recommend skills", "detect stack", "project technologies", "framework detection"
```

### Change 2: Add Skill Keywords to Common Request Patterns

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/PM_INSTRUCTIONS.md`

**Location**: After line 1447 (after "commit to main" pattern)

**Add**:
```markdown
When the user mentions "skill", "add skill", "create skill", "improve skill", "recommend skills", or asks about "project stack", "technologies", "frameworks", delegate to mpm-skills-manager agent for all skill operations and technology analysis.
```

### Change 3: Circuit Breaker for Skill Operations

**File**: `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/circuit-breakers.md`

**Add New Circuit Breaker**:
```markdown
## Circuit Breaker #10: Skill Operations Violation

**Trigger**: PM attempts direct skill operations instead of delegating to mpm-skills-manager

**Detection Patterns**:
- PM tries to create SKILL.md files directly
- PM attempts to modify manifest.json
- PM creates PRs to skills repository without mpm-skills-manager
- PM recommends skills without technology detection
- User request contains skill keywords but PM doesn't delegate

**Violation Examples**:
```
User: "Create a FastAPI skill"
PM: Uses Write tool to create SKILL.md  # ❌ VIOLATION
PM: Updates manifest.json directly      # ❌ VIOLATION
```

**Correct Pattern**:
```
User: "Create a FastAPI skill"
PM: Detects "skill" keyword
PM: Delegates to mpm-skills-manager
mpm-skills-manager: Creates skill structure, updates manifest, creates PR
PM: Reports PR URL to user
```

**Enforcement**:
- Violation #1: ⚠️ WARNING - PM must delegate to mpm-skills-manager
- Violation #2: 🚨 ESCALATION - Flag for review
- Violation #3: ❌ FAILURE - Session non-compliant
```

---

## Implementation Checklist

**Phase 1: Update PM Instructions** (Required)
- [ ] Add "MPM Skills Manager Agent" section after line 461 in PM_INSTRUCTIONS.md
- [ ] Add skill keywords to "Common User Request Patterns" after line 1447
- [ ] Rebuild PM instructions: `mpm-agents-deploy --force-rebuild`
- [ ] Verify deployment: Check `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md`

**Phase 2: Add Circuit Breaker** (Recommended)
- [ ] Add Circuit Breaker #10 to `src/claude_mpm/agents/templates/circuit-breakers.md`
- [ ] Rebuild templates: `mpm-agents-deploy --force-rebuild`
- [ ] Test violation detection with one-shot test cases

**Phase 3: Testing** (Critical)
- [ ] Test case: "Create a Svelte 5 skill" → PM should delegate to mpm-skills-manager
- [ ] Test case: "Recommend skills for FastAPI project" → PM should delegate
- [ ] Test case: "Improve the React skill" → PM should delegate
- [ ] Verify PM doesn't attempt direct skill operations

**Phase 4: Documentation** (Optional)
- [ ] Update developer docs with skill delegation workflow
- [ ] Add examples to PM agent documentation
- [ ] Create troubleshooting guide for skill delegation issues

---

## Testing Scenarios

### Test Case 1: Skill Creation

**User Request**: "Create a skill for Svelte 5 Runes mode"

**Expected PM Behavior**:
1. PM detects "skill" keyword in request
2. PM delegates to mpm-skills-manager agent
3. mpm-skills-manager detects Svelte 5 in project (if applicable)
4. mpm-skills-manager creates skill structure (SKILL.md, references/)
5. mpm-skills-manager updates manifest.json
6. mpm-skills-manager creates PR to skills repository
7. PM reports PR URL and next steps

**Actual PM Behavior** (before fix):
1. PM tries to use non-existent "svelte-engineer" skill
2. PM attempts to create skill content directly
3. PM delegates to "documentation" agent

### Test Case 2: Skill Recommendation

**User Request**: "What skills do I need for my FastAPI + React project?"

**Expected PM Behavior**:
1. PM detects "skills" keyword in request
2. PM delegates to mpm-skills-manager agent
3. mpm-skills-manager analyzes project files (requirements.txt, package.json)
4. mpm-skills-manager recommends:
   - toolchains-python-frameworks-fastapi (Critical)
   - toolchains-javascript-frameworks-react (Critical)
   - toolchains-python-testing-pytest (High)
   - toolchains-typescript-core (High)
5. PM reports recommendations with installation commands

**Actual PM Behavior** (before fix):
1. PM attempts manual skill recommendation without detection
2. PM may recommend incorrect or non-existent skills
3. No technology stack analysis performed

### Test Case 3: Skill Improvement

**User Request**: "The FastAPI skill is missing async database patterns"

**Expected PM Behavior**:
1. PM detects "skill" keyword + "FastAPI skill"
2. PM delegates to mpm-skills-manager agent
3. mpm-skills-manager analyzes existing FastAPI skill
4. mpm-skills-manager adds async database section
5. mpm-skills-manager updates version (1.0.0 → 1.1.0)
6. mpm-skills-manager creates PR with improvements
7. PM reports PR URL and change summary

**Actual PM Behavior** (before fix):
1. PM delegates to documentation agent (wrong agent)
2. Documentation agent doesn't have skill workflow knowledge
3. No PR created, changes lost or incorrectly documented

---

## Related Files

### Source Files (Modify These)
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/PM_INSTRUCTIONS.md` - Add delegation rules
- `/Users/masa/Projects/claude-mpm/src/claude_mpm/agents/templates/circuit-breakers.md` - Add Circuit Breaker #10

### Deployment Artifacts (Auto-Generated, DO NOT EDIT)
- `.claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md` - Merged PM instructions
- `.claude-mpm/templates/circuit-breakers.md` - Template copies

### Agent Definition (Reference Only)
- `~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/claude-mpm/mpm-skills-manager.md`

### Build Commands
```bash
# After modifying source files:
mpm-agents-deploy --force-rebuild

# Verify deployment:
ls -l .claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md
cat .claude-mpm/PM_INSTRUCTIONS_DEPLOYED.md | grep -A 10 "MPM Skills Manager"
```

---

## Risk Assessment

**High Risk**:
- PM continues to operate skills without proper delegation
- Users create malformed skills without validation
- Skills repository receives PRs without proper structure
- Manifest.json becomes corrupted from direct edits

**Medium Risk**:
- User confusion when PM delegates to wrong agent
- Duplicated effort when PM and user both attempt skill creation
- Inconsistent skill recommendations without technology detection

**Low Risk**:
- Minor delays in skill operations while PM learns new patterns
- Initial confusion during transition period

---

## Success Metrics

**After Fix**:
- PM delegates 100% of skill operations to mpm-skills-manager
- Zero Circuit Breaker #10 violations in production
- Skills created via proper PR workflow with validation
- Technology detection runs before skill recommendations
- Manifest.json integrity maintained across all operations

**User Experience Improvement**:
- User asks for skill → PM delegates → Skill created via PR → User informed
- User asks for recommendations → PM delegates → Technologies detected → Skills suggested
- User reports skill gap → PM delegates → PR created with improvement → User notified

---

## Conclusion

The PM delegation authority gap for skill-related tasks is a **HIGH PRIORITY** fix that requires:

1. **Immediate**: Add "MPM Skills Manager Agent" section to PM_INSTRUCTIONS.md (lines 382-461)
2. **Immediate**: Add skill keywords to "Common User Request Patterns" (after line 1447)
3. **Recommended**: Add Circuit Breaker #10 for skill operation violations
4. **Critical**: Rebuild and deploy PM instructions with `mpm-agents-deploy --force-rebuild`
5. **Validation**: Test with one-shot cases to verify delegation behavior

**Estimated Effort**: 30 minutes to implement, 15 minutes to test

**Impact**: Enables proper skill management workflow, prevents PM from attempting direct operations, ensures skills repository quality through validated PR workflow.

---

**Next Steps**:
1. Review this research with PM maintainers
2. Approve recommended changes to PM_INSTRUCTIONS.md
3. Implement changes to source files
4. Rebuild deployment artifacts
5. Test with skill-related user requests
6. Monitor for Circuit Breaker #10 violations
7. Document skill delegation workflow in developer guides
