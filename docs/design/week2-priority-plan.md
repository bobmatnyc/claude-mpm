# Week 2 Priority Plan: Skills Download & Refactoring

**Version:** 1.0.0
**Date:** November 7, 2025
**Week:** Week 2 (Nov 14-21, 2025)
**Focus:** Download and refactor priority skills for bundling

---

## Executive Summary

### Overview
Week 2 focuses on downloading, validating, and refactoring priority skills from external repositories. We will process **23 unique skills** across **4 source repositories**, with priority given to high-impact skills used by multiple agents.

### Key Metrics

| Metric | Value |
|--------|-------|
| **Total Skills** | 23 skills |
| **Core Skills (10+ agents)** | 2 skills |
| **Important Skills (5-9 agents)** | 2 skills |
| **Specialized Skills (1-4 agents)** | 19 skills |
| **Estimated Download Time** | 30-45 minutes |
| **Estimated Refactoring Effort** | 24-32 hours |
| **Total Agent Coverage** | 40 agents |

### Critical Path

1. **Days 1-2**: Download and validate all 23 skills from source repositories
2. **Days 3-4**: Refactor Tier 1 (core skills) - highest impact
3. **Days 5-6**: Refactor Tier 2 (important skills) - medium impact
4. **Day 7**: Quality validation, integration testing, and buffer time

### Success Criteria

- ✅ All 23 skills downloaded and validated
- ✅ Core skills (systematic-debugging, test-driven-development) refactored to progressive disclosure format
- ✅ Important skills (webapp-testing, verification) refactored to progressive disclosure format
- ✅ All refactored skills pass validation (<200 lines entry point, 150-300 line references)
- ✅ License attributions generated for all bundled skills
- ✅ Integration tests pass with refactored skills

---

## Priority Tier 1: Core Skills (Download First - Days 1-2)

### Overview
Core skills are used by **10+ agents** and have the highest impact on system functionality. These are mission-critical and should be refactored first.

### Tier 1 Skills (2 skills)

| Skill Name | Agents | Type | Source | Priority | Size Est. |
|------------|--------|------|--------|----------|-----------|
| **systematic-debugging** | 27 | Required by all | Superpowers | CRITICAL | ~15KB |
| **test-driven-development** | 19 | Required by all | Superpowers | CRITICAL | ~12KB |

#### 1. systematic-debugging

**Impact Analysis:**
- **Usage:** 27 agents (67.5% of all agents)
- **Type:** Required by all using agents
- **Categories:** All engineering, ops, DevOps, security agents
- **Impact Score:** 27 × 10 = **270 points**

**Source Information:**
- **Repository:** https://github.com/obra/superpowers-skills
- **Path:** `skills/debugging/systematic-debugging`
- **License:** MIT
- **Maintainer:** Jesse Vincent

**Download Details:**
- **URL:** https://github.com/obra/superpowers-skills/tree/main/skills/debugging/systematic-debugging
- **Expected Files:** SKILL.md, possibly examples/
- **Estimated Size:** 10-20KB
- **Format Status:** Unknown - needs assessment

**Refactoring Approach:**
1. **Assessment Phase** (30 min)
   - Download and read complete skill
   - Identify current structure and line count
   - Map content sections (intro, workflow, examples, anti-patterns)

2. **Progressive Disclosure Design** (1-2 hours)
   - Create entry point (target: 100-150 lines)
   - Design reference structure:
     - `debugging-workflow.md` - Core debugging process
     - `common-pitfalls.md` - Anti-patterns to avoid
     - `debugging-examples.md` - Real-world examples
     - `verification-strategies.md` - How to validate fixes

3. **Refactoring Execution** (2-3 hours)
   - Split content into entry point + references
   - Maintain all original information
   - Create clear navigation map
   - Add progressive disclosure hints

4. **Validation** (30 min)
   - Verify entry point <200 lines
   - Verify references 150-300 lines each
   - Test navigation flow
   - Run validation script

**Estimated Effort:** 4-6 hours

#### 2. test-driven-development

**Impact Analysis:**
- **Usage:** 19 agents (47.5% of all agents)
- **Type:** Required by all using agents
- **Categories:** All engineering, QA, testing agents
- **Impact Score:** 19 × 10 = **190 points**

**Source Information:**
- **Repository:** https://github.com/obra/superpowers-skills
- **Path:** `skills/testing/test-driven-development`
- **License:** MIT
- **Maintainer:** Jesse Vincent

**Download Details:**
- **URL:** https://github.com/obra/superpowers-skills/tree/main/skills/testing/test-driven-development
- **Expected Files:** SKILL.md, examples/
- **Estimated Size:** 8-15KB
- **Format Status:** Likely already in good format (Jesse's skills are well-structured)

**Refactoring Approach:**
1. **Assessment Phase** (30 min)
   - Download and analyze structure
   - Check if already in progressive disclosure format
   - Identify RED/GREEN/REFACTOR sections

2. **Progressive Disclosure Design** (1-2 hours)
   - Create entry point focusing on core TDD cycle
   - Design reference structure:
     - `red-phase.md` - Writing failing tests
     - `green-phase.md` - Making tests pass
     - `refactor-phase.md` - Improving code quality
     - `tdd-patterns.md` - Common TDD patterns
     - `tdd-anti-patterns.md` - What not to do

3. **Refactoring Execution** (2-3 hours)
   - Split into entry point + references
   - Preserve all workflow documentation
   - Create clear phase transitions
   - Add navigation hints

4. **Validation** (30 min)
   - Verify line counts
   - Test progressive disclosure flow
   - Validate against SKILL.md spec

**Estimated Effort:** 4-6 hours

### Tier 1 Summary

| Metric | Value |
|--------|-------|
| **Total Skills** | 2 |
| **Total Agents Covered** | 46 (with overlap) |
| **Unique Agents Covered** | 27 (systematic-debugging covers all) |
| **Download Time** | ~10 minutes |
| **Refactoring Time** | 8-12 hours |
| **Repository** | Superpowers (single source) |
| **License** | MIT (single license) |

**Critical Success Factor:** These two skills must be completed before moving to Tier 2. They impact 67.5% of all agents.

---

## Priority Tier 2: Important Skills (Download Second - Days 3-4)

### Overview
Important skills are used by **5-9 agents** and have significant impact on specific domains (web development, operations).

### Tier 2 Skills (2 skills)

| Skill Name | Agents | Type | Source | Priority | Size Est. |
|------------|--------|------|--------|----------|-----------|
| **webapp-testing** | 7 | Required | Anthropic | HIGH | ~20KB |
| **verification** | 6 | Required | Superpowers | HIGH | ~8KB |

#### 3. webapp-testing

**Impact Analysis:**
- **Usage:** 7 agents (17.5% of agents)
- **Type:** Required by all using agents
- **Categories:** Web development, frontend, QA agents
- **Impact Score:** 7 × 10 = **70 points**
- **Domain:** Critical for web testing workflows

**Source Information:**
- **Repository:** https://github.com/anthropics/skills
- **Path:** `webapp-testing`
- **License:** MIT
- **Maintainer:** Anthropic

**Download Details:**
- **URL:** https://github.com/anthropics/skills/tree/main/webapp-testing
- **Expected Files:** SKILL.md, examples/, possibly scripts/
- **Estimated Size:** 15-25KB (Anthropic skills tend to be comprehensive)
- **Format Status:** Unknown - Anthropic format may differ from Superpowers

**Refactoring Approach:**
1. **Assessment Phase** (45 min)
   - Download complete skill
   - Analyze Anthropic's structure vs. our spec
   - Identify Playwright integration points
   - Map testing workflow sections

2. **Progressive Disclosure Design** (2-3 hours)
   - Create entry point with core testing workflow
   - Design reference structure:
     - `playwright-setup.md` - Browser automation setup
     - `test-patterns.md` - Common web testing patterns
     - `selectors-guide.md` - Finding and interacting with elements
     - `assertions.md` - Validation patterns
     - `debugging-tests.md` - Troubleshooting failed tests

3. **Refactoring Execution** (3-4 hours)
   - Adapt to progressive disclosure format
   - Preserve Playwright-specific guidance
   - Create clear workflow transitions
   - Add troubleshooting sections

4. **Validation** (45 min)
   - Verify format compliance
   - Test with web_qa agent context
   - Validate Playwright examples work

**Estimated Effort:** 6-8 hours

**Special Considerations:**
- May need to verify Playwright version compatibility
- Should test with actual web application examples
- Coordinate with accessibility_specialist requirements

#### 4. verification

**Impact Analysis:**
- **Usage:** 6 agents (15% of agents)
- **Type:** Required by all using agents
- **Categories:** QA, Operations, DevOps, SRE agents
- **Impact Score:** 6 × 10 = **60 points**
- **Domain:** Critical for deployment and testing workflows

**Source Information:**
- **Repository:** https://github.com/obra/superpowers-skills
- **Path:** `skills/debugging/verification`
- **License:** MIT
- **Maintainer:** Jesse Vincent

**Download Details:**
- **URL:** https://github.com/obra/superpowers-skills/tree/main/skills/debugging/verification
- **Expected Files:** SKILL.md, examples/
- **Estimated Size:** 5-10KB (companion to systematic-debugging)
- **Format Status:** Likely well-structured (Superpowers quality)

**Refactoring Approach:**
1. **Assessment Phase** (30 min)
   - Download and analyze
   - Identify verification patterns
   - Check overlap with systematic-debugging

2. **Progressive Disclosure Design** (1-2 hours)
   - Create entry point with verification principles
   - Design reference structure:
     - `verification-checklist.md` - What to verify
     - `test-validation.md` - Ensuring tests prove the fix
     - `regression-prevention.md` - Preventing future bugs
     - `evidence-gathering.md` - Documenting proof

3. **Refactoring Execution** (2-3 hours)
   - Split into entry point + references
   - Maintain verification workflow integrity
   - Cross-reference with systematic-debugging
   - Add deployment-specific guidance

4. **Validation** (30 min)
   - Verify format compliance
   - Test with ops/qa agent contexts
   - Validate workflow completeness

**Estimated Effort:** 4-6 hours

### Tier 2 Summary

| Metric | Value |
|--------|-------|
| **Total Skills** | 2 |
| **Total Agents Covered** | 13 (unique) |
| **Download Time** | ~10 minutes |
| **Refactoring Time** | 10-14 hours |
| **Repositories** | Superpowers (1), Anthropic (1) |
| **Licenses** | MIT (both) |

---

## Priority Tier 3: Specialized Skills (Download Third - Days 5-7)

### Overview
Specialized skills are used by **1-4 agents** each. While lower priority, several of these are required for critical workflows (PM planning, integration work, documentation).

### Tier 3A: Multi-Agent Skills (3-4 agents) - Higher Priority

| Skill Name | Agents | Type | Source | Effort Est. |
|------------|--------|------|--------|-------------|
| **code-review** | 3 | Required/Optional | Superpowers | 4-5 hours |
| **artifacts-builder** | 3 | Required/Optional | Anthropic | 5-6 hours |
| **root-cause-tracing** | 3 | Required/Optional | Superpowers | 4-5 hours |

**Tier 3A Details:**

#### code-review (3 agents)
- **Agents:** engineer, code_analyzer, refactoring_engineer
- **URL:** https://github.com/obra/superpowers-skills/tree/main/skills/collaboration/code-review
- **Estimated Size:** 10-15KB
- **Refactoring Complexity:** Medium - needs structured review workflow
- **Impact:** Critical for code quality workflows
- **Effort:** 4-5 hours

#### artifacts-builder (3 agents)
- **Agents:** typescript_engineer, nextjs_engineer, web_ui
- **URL:** https://github.com/anthropics/skills/tree/main/artifacts-builder
- **Estimated Size:** 20-30KB (likely comprehensive)
- **Refactoring Complexity:** High - complex React/Tailwind integration
- **Impact:** Critical for frontend development
- **Effort:** 5-6 hours

#### root-cause-tracing (3 agents)
- **Agents:** research, code_analyzer, code_search
- **URL:** https://github.com/obra/superpowers-skills/tree/main/skills/debugging/root-cause-tracing
- **Estimated Size:** 8-12KB
- **Refactoring Complexity:** Medium - companion to systematic-debugging
- **Impact:** Important for debugging workflows
- **Effort:** 4-5 hours

### Tier 3B: Dual-Agent Skills (2 agents)

| Skill Name | Agents | Type | Source | Effort Est. |
|------------|--------|------|--------|-------------|
| **git-worktrees** | 2 | Required/Optional | Superpowers | 3-4 hours |
| **defense-in-depth** | 2 | Required/Optional | Community (BehiSecc) | 4-5 hours |
| **file-organizer** | 2 | Optional only | Community (BehiSecc) | 3-4 hours |

**Tier 3B Details:**

#### git-worktrees (2 agents)
- **Agents:** engineer, version_control
- **URL:** https://github.com/obra/superpowers-skills/tree/main/skills/development/git-worktrees
- **Estimated Size:** 10-15KB
- **Refactoring Complexity:** Medium - advanced git workflows
- **Effort:** 3-4 hours

#### defense-in-depth (2 agents)
- **Agents:** qa, security
- **URL:** https://github.com/BehiSecc/awesome-claude-skills/tree/main/defense-in-depth
- **Estimated Size:** 12-18KB
- **Refactoring Complexity:** Medium-High - security patterns
- **Format Risk:** Community skill - unknown quality
- **Effort:** 4-5 hours

#### file-organizer (2 agents)
- **Agents:** memory_manager, project_organizer
- **URL:** https://github.com/BehiSecc/awesome-claude-skills/tree/main/file-organizer
- **Estimated Size:** 8-12KB
- **Refactoring Complexity:** Low-Medium - organizational patterns
- **Effort:** 3-4 hours

### Tier 3C: Single-Agent Skills (1 agent) - Lower Priority

| Skill Name | Agent | Source | Effort Est. | Notes |
|------------|-------|--------|-------------|-------|
| **async-testing** | python_engineer | Superpowers | 3-4 hours | Python async patterns |
| **testing-anti-patterns** | qa | Superpowers | 3-4 hours | QA quality patterns |
| **playwright-browser-automation** | web_qa | Community (Composio) | 4-5 hours | Browser automation |
| **csv-data-summarizer** | data_engineer | Community (Composio) | 3-4 hours | Data analysis |
| **finishing-branches** | version_control | Superpowers | 2-3 hours | Git workflow |
| **brainstorming** | pm | Superpowers | 3-4 hours | Planning workflow |
| **planning** | pm | Superpowers | 3-4 hours | Project planning |
| **parallel-agents** | pm | Superpowers | 4-5 hours | Multi-agent coordination |
| **internal-comms** | documentation | Anthropic | 3-4 hours | Documentation patterns |
| **writing-clearly-and-concisely** | documentation | Superpowers Marketplace | 2-3 hours | Writing style |
| **content-research-writer** | documentation | Community (BehiSecc) | 4-5 hours | Research documentation |
| **mcp-builder** | integration_specialist | Anthropic | 5-6 hours | MCP server creation |
| **skill-creator** | integration_specialist | Anthropic | 4-5 hours | Skill development |

### Tier 3 Summary

| Metric | Value |
|--------|-------|
| **Total Skills** | 19 |
| **Multi-agent (3-4 agents)** | 3 skills |
| **Dual-agent (2 agents)** | 3 skills |
| **Single-agent (1 agent)** | 13 skills |
| **Download Time** | ~15 minutes |
| **Refactoring Time** | 60-80 hours |

**Note:** Tier 3 refactoring will extend into Week 3. Week 2 focus should be on Tier 3A (multi-agent skills) if time permits.

---

## Source Repository Breakdown

### Repository Analysis

| Repository | Skills | License | Download Method | Risk Level |
|------------|--------|---------|-----------------|------------|
| **Superpowers** | 14 | MIT | GitHub API | Low |
| **Anthropic** | 5 | MIT | GitHub API | Low |
| **BehiSecc Community** | 3 | Various | GitHub API | Medium |
| **Composio Community** | 2 | Various | GitHub API | Medium |
| **Superpowers Marketplace** | 1 | MIT | GitHub API | Low |

### Download Priority by Repository

#### 1. Superpowers (14 skills) - HIGHEST PRIORITY
**Base URL:** https://github.com/obra/superpowers-skills/tree/main/skills

**Skills to Download:**
- `testing/test-driven-development` ⭐ (Tier 1)
- `testing/async-testing` (Tier 3C)
- `testing/testing-anti-patterns` (Tier 3C)
- `debugging/systematic-debugging` ⭐ (Tier 1)
- `debugging/root-cause-tracing` (Tier 3A)
- `debugging/verification` ⭐ (Tier 2)
- `collaboration/code-review` (Tier 3A)
- `collaboration/brainstorming` (Tier 3C)
- `collaboration/planning` (Tier 3C)
- `collaboration/parallel-agents` (Tier 3C)
- `development/git-worktrees` (Tier 3B)
- `development/finishing-branches` (Tier 3C)

**Plus Marketplace:**
- `elements-of-style` (aka writing-clearly-and-concisely) (Tier 3C)

**Download Strategy:**
```bash
python scripts/download_skills_api.py \
  --repo obra/superpowers-skills \
  --base-path skills \
  --output src/claude_mpm/skills/bundled
```

**Estimated Time:** 10-15 minutes for all 14 skills

#### 2. Anthropic (5 skills) - HIGH PRIORITY
**Base URL:** https://github.com/anthropics/skills/tree/main

**Skills to Download:**
- `webapp-testing` ⭐ (Tier 2)
- `artifacts-builder` (Tier 3A)
- `mcp-server` (aka mcp-builder) (Tier 3C)
- `skill-creator` (Tier 3C)
- `internal-comms` (Tier 3C)

**Download Strategy:**
```bash
python scripts/download_skills_api.py \
  --repo anthropics/skills \
  --output src/claude_mpm/skills/bundled
```

**Estimated Time:** 5-10 minutes for all 5 skills

**Special Considerations:**
- Anthropic skills may have different structure than Superpowers
- May include additional resources (scripts, examples)
- Verify compatibility with our SKILL.md spec

#### 3. BehiSecc Community (3 skills) - MEDIUM PRIORITY
**Base URL:** https://github.com/BehiSecc/awesome-claude-skills/tree/main

**Skills to Download:**
- `defense-in-depth` (Tier 3B)
- `content-research-writer` (Tier 3C)
- `file-organizer` (Tier 3B)

**Download Strategy:**
```bash
python scripts/download_skills_api.py \
  --repo BehiSecc/awesome-claude-skills \
  --output src/claude_mpm/skills/bundled
```

**Estimated Time:** 5 minutes for all 3 skills

**Risk Factors:**
- Community-maintained (quality may vary)
- License may be "Various" - need to verify each skill
- May need more extensive refactoring
- Format compliance unknown

#### 4. Composio Community (2 skills) - MEDIUM PRIORITY
**Base URL:** https://github.com/ComposioHQ/awesome-claude-skills/tree/main

**Skills to Download:**
- `csv-data-summarizer` (Tier 3C)
- `playwright-browser-automation` (Tier 3C)

**Download Strategy:**
```bash
python scripts/download_skills_api.py \
  --repo ComposioHQ/awesome-claude-skills \
  --output src/claude_mpm/skills/bundled
```

**Estimated Time:** 5 minutes for all 2 skills

**Risk Factors:**
- Community-maintained (quality may vary)
- License verification needed
- Playwright skill may overlap with webapp-testing

---

## Download Plan & Execution

### Phase 1: Environment Setup (Day 1 Morning - 1 hour)

#### Prerequisites
```bash
# 1. Verify Python environment
python3 --version  # Should be 3.8+

# 2. Install dependencies
pip install requests pyyaml

# 3. Verify directory structure
mkdir -p src/claude_mpm/skills/bundled/{testing,debugging,collaboration,development,integration,documentation,security,organization,data}

# 4. Test GitHub API access
curl -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/obra/superpowers-skills/contents/skills
```

#### Rate Limit Considerations
- GitHub API rate limit: 60 requests/hour (unauthenticated)
- With GitHub token: 5000 requests/hour
- Recommended: Use GitHub token for downloads

**Setup GitHub Token:**
```bash
export GITHUB_TOKEN="your_github_token_here"
```

### Phase 2: Download Execution (Day 1 Afternoon - 2-3 hours)

#### Download Order (by priority)

**Batch 1: Tier 1 Skills (CRITICAL)**
```bash
# Download systematic-debugging and test-driven-development
python scripts/download_skills_api.py \
  --repo obra/superpowers-skills \
  --skills debugging/systematic-debugging testing/test-driven-development \
  --output src/claude_mpm/skills/bundled \
  --validate
```
**Time:** 5 minutes
**Critical:** Must succeed before proceeding

**Batch 2: Tier 2 Skills (HIGH PRIORITY)**
```bash
# Download verification (Superpowers)
python scripts/download_skills_api.py \
  --repo obra/superpowers-skills \
  --skills debugging/verification \
  --output src/claude_mpm/skills/bundled \
  --validate

# Download webapp-testing (Anthropic)
python scripts/download_skills_api.py \
  --repo anthropics/skills \
  --skills webapp-testing \
  --output src/claude_mpm/skills/bundled \
  --validate
```
**Time:** 10 minutes

**Batch 3: Tier 3A Skills (IMPORTANT)**
```bash
# Download multi-agent skills
python scripts/download_skills_api.py \
  --repo obra/superpowers-skills \
  --skills collaboration/code-review debugging/root-cause-tracing \
  --output src/claude_mpm/skills/bundled \
  --validate

python scripts/download_skills_api.py \
  --repo anthropics/skills \
  --skills artifacts-builder \
  --output src/claude_mpm/skills/bundled \
  --validate
```
**Time:** 10 minutes

**Batch 4: Tier 3B Skills (DUAL-AGENT)**
```bash
# Download dual-agent skills
python scripts/download_skills_api.py \
  --repo obra/superpowers-skills \
  --skills development/git-worktrees \
  --output src/claude_mpm/skills/bundled \
  --validate

python scripts/download_skills_api.py \
  --repo BehiSecc/awesome-claude-skills \
  --skills defense-in-depth file-organizer \
  --output src/claude_mpm/skills/bundled \
  --validate
```
**Time:** 10 minutes

**Batch 5: Tier 3C Skills (SINGLE-AGENT)**
```bash
# Download all remaining skills
python scripts/download_skills_api.py \
  --repo obra/superpowers-skills \
  --skills testing/async-testing testing/testing-anti-patterns \
           development/finishing-branches \
           collaboration/brainstorming collaboration/planning collaboration/parallel-agents \
  --output src/claude_mpm/skills/bundled \
  --validate

python scripts/download_skills_api.py \
  --repo anthropics/skills \
  --skills mcp-server skill-creator internal-comms \
  --output src/claude_mpm/skills/bundled \
  --validate

python scripts/download_skills_api.py \
  --repo BehiSecc/awesome-claude-skills \
  --skills content-research-writer \
  --output src/claude_mpm/skills/bundled \
  --validate

python scripts/download_skills_api.py \
  --repo ComposioHQ/awesome-claude-skills \
  --skills csv-data-summarizer playwright-browser-automation \
  --output src/claude_mpm/skills/bundled \
  --validate

python scripts/download_skills_api.py \
  --repo obra/superpowers-marketplace \
  --skills elements-of-style \
  --output src/claude_mpm/skills/bundled \
  --validate
```
**Time:** 20 minutes

### Phase 3: Validation & Quality Check (Day 1 Evening - 1-2 hours)

#### Automated Validation
```bash
# Run validation on all downloaded skills
python scripts/validate_skills.py \
  --path src/claude_mpm/skills/bundled \
  --strict \
  --report validation_report.json

# Check for:
# - SKILL.md presence
# - Valid YAML frontmatter
# - Minimum content requirements
# - License files
```

#### Manual Review Checklist
For each downloaded skill:

1. **File Structure Check**
   - [ ] SKILL.md exists
   - [ ] Frontmatter is valid YAML
   - [ ] License file present or identified
   - [ ] No malicious content (scripts, binaries)

2. **Content Assessment**
   - [ ] Line count (estimate refactoring complexity)
   - [ ] Structure (already progressive? needs splitting?)
   - [ ] Quality (clear, actionable content?)
   - [ ] Examples present

3. **License Verification**
   - [ ] License type identified
   - [ ] License compatible with MIT
   - [ ] Attribution requirements noted

4. **Refactoring Estimate**
   - [ ] Complexity: Low / Medium / High
   - [ ] Time estimate: X hours
   - [ ] Priority adjustment if needed

#### Output: Download Report
Generate comprehensive download report:
```bash
python scripts/generate_download_report.py \
  --input src/claude_mpm/skills/bundled \
  --output docs/download_report.md
```

**Report should include:**
- Skills downloaded: 23/23 ✓
- Total size: ~XXX KB
- License breakdown
- Refactoring complexity estimates
- Issues found (if any)

### Download Phase Summary

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Setup | 1 hour | Environment ready |
| Download | 2-3 hours | 23 skills downloaded |
| Validation | 1-2 hours | Quality report |
| **Total** | **4-6 hours** | **All skills validated** |

---

## Refactoring Strategy

### Progressive Disclosure Format Specification

All skills must conform to the following structure:

#### Entry Point (SKILL.md)
- **Line Limit:** <200 lines (target: 100-150 lines)
- **Purpose:** Provide overview and navigation
- **Required Sections:**
  1. **Frontmatter** (YAML metadata)
  2. **Overview** (2-3 paragraphs)
  3. **When to Use** (bullet list)
  4. **Quick Reference** (core workflow/checklist)
  5. **Navigation Map** (links to references)
  6. **Common Patterns** (2-3 examples)

#### Reference Files (references/*.md)
- **Line Limit:** 150-300 lines per file
- **Purpose:** Deep-dive content for specific topics
- **Naming:** Descriptive, lowercase, hyphenated
- **Structure:** Single topic focus

### Refactoring Workflow

For each skill, follow this process:

#### Step 1: Assessment (30-60 min per skill)
```bash
# 1. Read complete skill
cat src/claude_mpm/skills/bundled/{category}/{skill-name}/SKILL.md

# 2. Count lines
wc -l src/claude_mpm/skills/bundled/{category}/{skill-name}/SKILL.md

# 3. Identify sections
# - What's in the overview?
# - What are the core concepts?
# - What are the detailed procedures?
# - What are the examples?

# 4. Create refactoring plan
# - Entry point content (what stays)
# - Reference files needed (what splits out)
# - Navigation strategy
```

#### Step 2: Design Reference Structure (30-60 min per skill)
```markdown
# Example: systematic-debugging refactoring plan

Entry Point (SKILL.md): ~120 lines
- Overview of systematic debugging
- Core principles (5 key principles)
- Quick workflow reference
- Navigation to detailed guides
- 1-2 simple examples

References (references/):
1. debugging-workflow.md (~200 lines)
   - Detailed step-by-step process
   - Reproducing bugs
   - Isolating root cause
   - Fix validation

2. common-pitfalls.md (~180 lines)
   - Random changes anti-pattern
   - Assumption-based debugging
   - Incomplete fixes
   - Lack of verification

3. debugging-examples.md (~250 lines)
   - Real-world debugging scenarios
   - Step-by-step walkthroughs
   - Before/after code samples

4. verification-strategies.md (~200 lines)
   - How to verify fixes work
   - Regression test creation
   - Evidence gathering
   - Documentation practices
```

#### Step 3: Execute Refactoring (2-4 hours per skill)
```bash
# 1. Create references directory
mkdir -p src/claude_mpm/skills/bundled/{category}/{skill-name}/references

# 2. Extract and reorganize content
# Use your preferred editor to:
# - Create entry point with navigation
# - Extract detailed content to references
# - Maintain all information (zero loss)
# - Add cross-references
# - Update frontmatter

# 3. Validate line counts
wc -l src/claude_mpm/skills/bundled/{category}/{skill-name}/SKILL.md
wc -l src/claude_mpm/skills/bundled/{category}/{skill-name}/references/*.md
```

#### Step 4: Validate & Test (30-60 min per skill)
```bash
# 1. Run format validation
python scripts/validate_skills.py \
  --skill {skill-name} \
  --check-progressive-disclosure

# 2. Check line counts
# Entry point: Must be <200 lines
# References: Should be 150-300 lines each

# 3. Verify navigation
# - All references linked from entry point
# - No broken internal links
# - Clear progressive disclosure hints

# 4. Test with agent context
# Load skill in test agent and verify:
# - Entry point provides good overview
# - References accessible when needed
# - Navigation is intuitive
```

### Refactoring Priority Queue

Based on impact analysis:

**Week 2 Target (Realistic):**
1. ✅ systematic-debugging (Tier 1) - 4-6 hours
2. ✅ test-driven-development (Tier 1) - 4-6 hours
3. ✅ verification (Tier 2) - 4-6 hours
4. ✅ webapp-testing (Tier 2) - 6-8 hours
5. 🎯 code-review (Tier 3A) - 4-5 hours (stretch goal)

**Total Week 2 Effort:** 22-31 hours (realistic for 5 work days)

**Week 3 Continuation:**
- Tier 3A remaining skills (2 skills, ~10 hours)
- Tier 3B skills (3 skills, ~11 hours)
- Tier 3C priority skills (PM, integration, documentation)

---

## Refactoring Sequence & Dependencies

### Dependency Analysis

Some skills have natural relationships that affect refactoring order:

#### Debugging Skills Family
```
systematic-debugging (Core)
    ├── verification (Validates fixes)
    └── root-cause-tracing (Advanced debugging)
```
**Strategy:** Refactor systematic-debugging first, use its structure as template for verification and root-cause-tracing.

#### Testing Skills Family
```
test-driven-development (Core)
    ├── async-testing (Python-specific)
    ├── testing-anti-patterns (Quality)
    └── webapp-testing (Web-specific)
```
**Strategy:** Refactor test-driven-development first, ensure webapp-testing complements (not duplicates).

#### Collaboration Skills Family
```
code-review (Independent)
brainstorming (Independent)
planning (Independent)
parallel-agents (Independent)
```
**Strategy:** No dependencies - can refactor in any order.

### Recommended Refactoring Order

**Days 3-4: Core Skills (Tier 1)**
1. **Day 3 Morning:** systematic-debugging (4-6 hours)
2. **Day 3 Afternoon:** test-driven-development (4-6 hours)
3. **Day 4:** Buffer/validation/cleanup

**Days 5-6: Important Skills (Tier 2)**
4. **Day 5 Morning:** verification (4-6 hours) - builds on systematic-debugging
5. **Day 5 Afternoon-Day 6:** webapp-testing (6-8 hours) - complex

**Day 7: Stretch Goals or Week 3 Preview**
6. code-review (4-5 hours) - if time permits
7. Otherwise: Final validation, testing, documentation

---

## DevOps Consolidation Analysis

### Background
The decisions summary mentions "devops consolidation (14 tools → 1 capability)" as Priority #1 for Week 2. However, after analyzing the actual skills registry, this appears to be a **future design goal** rather than a Week 2 task.

### Current State Analysis

**DevOps-Related Agents (from registry):**
1. devops
2. kubernetes
3. terraform
4. ansible
5. docker
6. ci_cd
7. ops
8. sre
9. cloud_architect

**Total:** 9 DevOps-related agents

**Current Skills Assignment:**
- All DevOps agents use: `systematic-debugging` (required)
- Some use: `verification` (required)
- No DevOps-specific skills exist yet

### The "14 Tools" Reference

The "14 tools → 1 capability" likely refers to potential DevOps skills that **could** be created:

1. Docker management
2. Kubernetes deployments
3. Terraform infrastructure
4. Ansible configuration
5. CI/CD pipelines
6. Cloud provider CLIs (AWS, GCP, Azure)
7. Monitoring setup
8. Logging configuration
9. Container orchestration
10. Service mesh configuration
11. Infrastructure as Code patterns
12. Deployment strategies
13. Rollback procedures
14. Incident response

### Week 2 Reality Check

**Issue:** There is no existing "devops" skill to download and consolidate.

**Options:**

#### Option A: Defer DevOps Consolidation (RECOMMENDED)
- **Rationale:** No source skills exist to consolidate
- **Action:** Focus on downloading and refactoring existing skills
- **Timeline:** Defer to Week 4-5 or later as custom skill creation
- **Priority:** Downgrade from Priority #1 to "Future Enhancement"

#### Option B: Create Custom DevOps Capability (AGGRESSIVE)
- **Rationale:** Fill critical gap for 9 DevOps agents
- **Action:** Design and create custom devops skill from scratch
- **Timeline:** Would require 10-15 hours in Week 2
- **Risk:** High - takes time away from existing skill refactoring

#### Option C: Hybrid Approach (BALANCED)
- **Rationale:** Start design, implement later
- **Action:**
  - Week 2: Create design document for DevOps capability
  - Week 2: Identify existing patterns in systematic-debugging applicable to DevOps
  - Week 3-4: Implement custom DevOps skill
- **Timeline:** 2-3 hours design in Week 2, implementation later
- **Risk:** Medium - doesn't impact core refactoring

### Recommendation: Option A (Defer)

**Reasoning:**
1. **No Source Material:** Unlike other skills, we have nothing to download/refactor
2. **Higher Priority Work:** Systematic-debugging and test-driven-development impact MORE agents
3. **Quality First:** Better to create DevOps skill properly later than rush it
4. **Progressive Enhancement:** DevOps agents still get systematic-debugging and verification

**Revised Week 2 Priorities:**
1. ~~Priority #1: DevOps consolidation~~ → Deferred to Week 4+
2. **NEW Priority #1:** Core skills (systematic-debugging, test-driven-development)
3. **Priority #2:** Important skills (webapp-testing, verification)
4. **Priority #3:** Multi-agent skills (code-review, artifacts-builder, root-cause-tracing)

---

## Risk Assessment & Mitigation

### High-Risk Items

#### Risk 1: Download Failures (Likelihood: Low, Impact: High)

**Symptoms:**
- GitHub API rate limiting
- Repository moved/deleted
- Network connectivity issues

**Mitigation:**
1. **Use GitHub token** (5000 requests/hour vs. 60)
2. **Download in batches** with delays between batches
3. **Implement retry logic** in download script (max 3 retries, exponential backoff)
4. **Cache downloads** locally before processing
5. **Manual fallback** - download via git clone if API fails

**Contingency:**
```bash
# If API fails, fall back to git clone
git clone --depth 1 https://github.com/obra/superpowers-skills
cd superpowers-skills
cp -r skills/* /path/to/claude-mpm/src/claude_mpm/skills/bundled/
```

#### Risk 2: Skills Exceed Size Limits (Likelihood: Medium, Impact: Medium)

**Symptoms:**
- Skills are >200 lines and can't be easily split
- Complex examples that need to stay together
- Highly coupled content

**Mitigation:**
1. **Accept larger entry points temporarily** (up to 300 lines) for complex skills
2. **Use external examples** - link to GitHub instead of embedding
3. **Create appendices** - move optional content to separate files
4. **Progressive disclosure** - ensure most important content is in first 150 lines

**Affected Skills (Likely):**
- artifacts-builder (React/Tailwind - complex)
- webapp-testing (Playwright - many patterns)
- mcp-builder (MCP protocol - technical)

#### Risk 3: License Incompatibilities (Likelihood: Low, Impact: High)

**Symptoms:**
- Community skills have restrictive licenses
- Attribution requirements unclear
- Commercial use restrictions

**Mitigation:**
1. **License audit** before bundling
2. **Exclude incompatible skills** from bundle
3. **Document attribution** in LICENSE_ATTRIBUTIONS.md
4. **Legal review** if uncertain (community skills especially)

**Community Skill Licenses to Verify:**
- BehiSecc/awesome-claude-skills (3 skills)
- ComposioHQ/awesome-claude-skills (2 skills)

#### Risk 4: Quality Issues in Community Skills (Likelihood: Medium, Impact: Medium)

**Symptoms:**
- Poor documentation
- Incomplete examples
- Inconsistent format
- Outdated information

**Mitigation:**
1. **Quality gate** - reject skills below threshold
2. **Rewrite if necessary** - use as inspiration, create our own
3. **Mark as experimental** - warn users in frontmatter
4. **Supplement with our own content** - enhance rather than replace

**Higher Risk Skills:**
- defense-in-depth (BehiSecc)
- content-research-writer (BehiSecc)
- file-organizer (BehiSecc)
- csv-data-summarizer (Composio)
- playwright-browser-automation (Composio)

#### Risk 5: Time Overruns (Likelihood: High, Impact: Medium)

**Symptoms:**
- Refactoring takes longer than estimated
- Complex skills need more work than planned
- Week 2 goals not met

**Mitigation:**
1. **Focus on Tier 1 first** - non-negotiable
2. **Accept partial completion** - Tier 3 can extend to Week 3
3. **Parallel work if possible** - simple skills can be done faster
4. **Buffer time** - Day 7 is buffer day
5. **Scope adjustment** - reduce Tier 3 goals if needed

**Time Management:**
- Days 1-2: Download ALL skills (must complete)
- Days 3-4: Tier 1 refactoring (must complete)
- Days 5-6: Tier 2 refactoring (must complete)
- Day 7: Tier 3A or buffer (nice to have)

### Medium-Risk Items

#### Risk 6: Format Inconsistencies (Likelihood: High, Impact: Low)

**Symptoms:**
- Superpowers, Anthropic, Community skills use different formats
- YAML frontmatter varies
- Section structures differ

**Mitigation:**
1. **Normalize during refactoring** - convert all to our spec
2. **Automated format conversion** - script to standardize frontmatter
3. **Template-based refactoring** - use consistent structure

#### Risk 7: Validation Failures (Likelihood: Medium, Impact: Low)

**Symptoms:**
- Skills don't pass validation script
- Line counts exceeded
- Missing required fields

**Mitigation:**
1. **Iterative validation** - check after each refactoring
2. **Fix immediately** - don't batch validation
3. **Learn from failures** - adjust process for next skill

### Low-Risk Items

#### Risk 8: Missing Skills (Likelihood: Low, Impact: Low)

**Symptoms:**
- Skills in registry but not in source repositories
- URLs broken
- Skills renamed/moved

**Mitigation:**
1. **Verify URLs before download** - test all 23 URLs
2. **Search for renamed skills** - check repository for alternatives
3. **Mark as missing** - update registry with status

---

## Week 2 Daily Timeline

### Day 1 (Nov 14): Download & Validation Day

**Morning (9:00 AM - 12:00 PM): Setup & Initial Downloads**
- 9:00-10:00: Environment setup, GitHub token config, script testing
- 10:00-10:30: Batch 1 - Download Tier 1 skills (systematic-debugging, test-driven-development)
- 10:30-11:00: Batch 2 - Download Tier 2 skills (verification, webapp-testing)
- 11:00-12:00: Batch 3 - Download Tier 3A skills (code-review, artifacts-builder, root-cause-tracing)

**Checkpoint 1:** 4 critical skills downloaded and validated

**Afternoon (1:00 PM - 5:00 PM): Complete Downloads**
- 1:00-2:00: Batch 4 - Download Tier 3B skills (git-worktrees, defense-in-depth, file-organizer)
- 2:00-3:30: Batch 5 - Download all Tier 3C skills (13 remaining skills)
- 3:30-4:30: Run automated validation on all downloaded skills
- 4:30-5:00: Review validation report, identify issues

**Checkpoint 2:** All 23 skills downloaded, validation report generated

**Evening (Optional): Manual Review**
- Manual review of high-risk community skills
- License verification for BehiSecc and Composio skills
- Quality assessment notes for refactoring planning

**Day 1 Deliverables:**
- ✅ 23 skills downloaded to `src/claude_mpm/skills/bundled/`
- ✅ Validation report generated
- ✅ License audit complete
- ✅ Quality notes for each skill

---

### Day 2 (Nov 15): Assessment & Planning Day

**Morning (9:00 AM - 12:00 PM): Tier 1 Assessment**
- 9:00-10:00: Deep dive into systematic-debugging
  - Read complete skill
  - Count sections and line count
  - Identify split points
  - Create refactoring plan
- 10:00-11:00: Deep dive into test-driven-development
  - Same assessment process
  - Check for overlap with other testing skills
- 11:00-12:00: Create detailed refactoring plans for both Tier 1 skills

**Checkpoint 3:** Tier 1 refactoring plans complete

**Afternoon (1:00 PM - 5:00 PM): Tier 2 & 3A Assessment**
- 1:00-2:00: Assess verification skill
  - Identify relationship to systematic-debugging
  - Plan complementary structure
- 2:00-3:30: Assess webapp-testing skill
  - Likely complex - detailed planning needed
  - Identify Playwright integration points
- 3:30-4:30: Assess Tier 3A skills (code-review, artifacts-builder, root-cause-tracing)
- 4:30-5:00: Prioritize refactoring order, create detailed schedule

**Checkpoint 4:** Refactoring plans complete for Tiers 1, 2, and 3A

**Day 2 Deliverables:**
- ✅ Detailed refactoring plan for each Tier 1-2 skill
- ✅ Assessment notes for Tier 3A skills
- ✅ Refactoring sequence finalized
- ✅ Time estimates refined

---

### Day 3 (Nov 16): Tier 1 Refactoring Day

**Morning (9:00 AM - 12:00 PM): systematic-debugging**
- 9:00-10:00: Create entry point structure
  - Extract overview and core principles
  - Design navigation map
  - Write quick reference guide
- 10:00-11:30: Create reference files
  - `debugging-workflow.md`
  - `common-pitfalls.md`
  - `debugging-examples.md`
  - `verification-strategies.md`
- 11:30-12:00: Validate, cross-link, test navigation

**Checkpoint 5:** systematic-debugging refactored and validated

**Afternoon (1:00 PM - 5:00 PM): test-driven-development**
- 1:00-2:00: Create entry point structure
  - RED/GREEN/REFACTOR overview
  - Core TDD principles
  - Quick workflow reference
- 2:00-4:00: Create reference files
  - `red-phase.md`
  - `green-phase.md`
  - `refactor-phase.md`
  - `tdd-patterns.md`
  - `tdd-anti-patterns.md`
- 4:00-4:30: Validate, cross-link, test navigation
- 4:30-5:00: Integration testing with Tier 1 agents

**Checkpoint 6:** test-driven-development refactored and validated

**Day 3 Deliverables:**
- ✅ systematic-debugging refactored (<200 line entry point, 4-5 references)
- ✅ test-driven-development refactored (<200 line entry point, 4-5 references)
- ✅ Both skills pass validation
- ✅ Integration tests pass

---

### Day 4 (Nov 17): Buffer & Tier 2 Start

**Morning (9:00 AM - 12:00 PM): Buffer / Tier 1 Completion**
- Option A (if Tier 1 complete): Start verification refactoring
- Option B (if Tier 1 incomplete): Complete remaining Tier 1 work
- Option C (if Tier 1 complete): Generate license attributions

**Recommended: Option A**
- 9:00-11:30: Refactor verification skill
  - Leverage systematic-debugging structure
  - Focus on validation patterns
  - Create complementary references
- 11:30-12:00: Validate and test

**Checkpoint 7:** verification skill refactored

**Afternoon (1:00 PM - 5:00 PM): Tier 2 Continuation or Testing**
- Option A (if ahead): Start webapp-testing refactoring
- Option B (if behind): Complete verification
- Option C (if complete): Comprehensive testing and validation

**Day 4 Deliverables:**
- ✅ verification refactored (if on schedule)
- ✅ Comprehensive test suite run
- ✅ All Tier 1-2 skills validated
- ✅ License attributions in progress

---

### Day 5 (Nov 18): Tier 2 Completion

**Full Day (9:00 AM - 5:00 PM): webapp-testing Refactoring**
- 9:00-10:30: Analyze Anthropic's structure
  - Understand Playwright integration
  - Identify test pattern sections
  - Plan reference split
- 10:30-12:00: Create entry point
  - Overview of web testing
  - Core testing workflow
  - Navigation to patterns
- 1:00-3:00: Create reference files
  - `playwright-setup.md`
  - `test-patterns.md`
  - `selectors-guide.md`
  - `assertions.md`
  - `debugging-tests.md`
- 3:00-4:00: Validate and cross-link
- 4:00-5:00: Integration testing with web_qa and frontend agents

**Checkpoint 8:** webapp-testing refactored and validated

**Day 5 Deliverables:**
- ✅ webapp-testing refactored (complex skill, may need more time)
- ✅ All Tier 2 skills complete
- ✅ Integration tests with web agents pass

---

### Day 6 (Nov 19): Tier 3A or Polish

**Morning (9:00 AM - 12:00 PM): Stretch Goals**
- Option A (if ahead): Refactor code-review
- Option B (if behind): Complete webapp-testing
- Option C (if complete): Start artifacts-builder

**Recommended: Option A**
- 9:00-11:30: Refactor code-review
  - Create entry point with review workflow
  - Split out detailed patterns
- 11:30-12:00: Validate

**Checkpoint 9:** code-review refactored (stretch goal)

**Afternoon (1:00 PM - 5:00 PM): Polish & Documentation**
- 1:00-2:00: Generate license attributions
  ```bash
  python scripts/generate_license_attributions.py \
    --input src/claude_mpm/skills/bundled \
    --output src/claude_mpm/skills/bundled/LICENSE_ATTRIBUTIONS.md
  ```
- 2:00-3:00: Run comprehensive validation suite
- 3:00-4:00: Create refactoring summary document
- 4:00-5:00: Update Week 3 priorities based on progress

**Day 6 Deliverables:**
- ✅ LICENSE_ATTRIBUTIONS.md generated
- ✅ All refactored skills pass validation
- ✅ Refactoring summary document
- ✅ Week 3 plan updated

---

### Day 7 (Nov 20): Testing & Week 3 Preview

**Morning (9:00 AM - 12:00 PM): Integration Testing**
- 9:00-10:00: Test Tier 1 skills with multiple agents
  - Engineer agent with systematic-debugging
  - Python engineer with test-driven-development
  - Verify progressive disclosure works
- 10:00-11:00: Test Tier 2 skills
  - web_qa with webapp-testing
  - ops agent with verification
- 11:00-12:00: Fix any issues found

**Checkpoint 10:** All refactored skills tested in agent contexts

**Afternoon (1:00 PM - 5:00 PM): Week 3 Preparation**
- Option A (if ahead): Start Tier 3A refactoring (artifacts-builder or root-cause-tracing)
- Option B (if behind): Complete pending work
- Option C (if complete): Create Week 3 detailed plan

**Recommended: Option C**
- 1:00-2:00: Review Week 2 accomplishments
- 2:00-3:00: Create detailed Week 3 plan for remaining skills
- 3:00-4:00: Prioritize Tier 3 skills based on learnings
- 4:00-5:00: Update project documentation

**Day 7 Deliverables:**
- ✅ Integration testing complete
- ✅ Week 2 retrospective document
- ✅ Week 3 detailed plan
- ✅ All documentation updated

---

## Success Metrics & Validation

### Week 2 Goals (Minimum)

| Goal | Target | Measurement |
|------|--------|-------------|
| Skills Downloaded | 23/23 | File count |
| Tier 1 Refactored | 2/2 | Validation pass |
| Tier 2 Refactored | 2/2 | Validation pass |
| Entry Point Lines | <200 each | Line count |
| Reference Lines | 150-300 each | Line count |
| License Attributions | Complete | File exists |
| Integration Tests | Pass | Test results |

### Week 2 Goals (Stretch)

| Goal | Target | Measurement |
|------|--------|-------------|
| Tier 3A Refactored | 1-3/3 | Validation pass |
| Code Review Quality | High | Manual review |
| Documentation | Complete | Coverage |

### Validation Criteria

**Per Skill:**
```bash
# Must pass all checks
python scripts/validate_skills.py --skill {skill-name}

# Checks:
# ✓ SKILL.md exists
# ✓ SKILL.md <200 lines
# ✓ Valid YAML frontmatter
# ✓ Required frontmatter fields present
# ✓ References/ directory (if exists)
# ✓ Each reference 150-300 lines
# ✓ All internal links valid
# ✓ No broken references
# ✓ License attribution present
```

**Overall Project:**
```bash
# Must pass
python scripts/validate_skills.py --all

# Checks:
# ✓ All downloaded skills validated
# ✓ All refactored skills validated
# ✓ LICENSE_ATTRIBUTIONS.md complete
# ✓ No duplicate content
# ✓ Consistent frontmatter format
# ✓ All skills_registry.yaml references exist
```

---

## Appendix A: Skill Download URLs Reference

### Complete URL List (23 skills)

#### Superpowers Skills (14 skills)
```yaml
base_url: https://github.com/obra/superpowers-skills/tree/main/skills

testing:
  - test-driven-development: testing/test-driven-development
  - async-testing: testing/async-testing
  - testing-anti-patterns: testing/testing-anti-patterns

debugging:
  - systematic-debugging: debugging/systematic-debugging
  - root-cause-tracing: debugging/root-cause-tracing
  - verification: debugging/verification

collaboration:
  - code-review: collaboration/code-review
  - brainstorming: collaboration/brainstorming
  - planning: collaboration/planning
  - parallel-agents: collaboration/parallel-agents

development:
  - git-worktrees: development/git-worktrees
  - finishing-branches: development/finishing-branches
```

#### Anthropic Skills (5 skills)
```yaml
base_url: https://github.com/anthropics/skills/tree/main

skills:
  - webapp-testing: webapp-testing
  - artifacts-builder: artifacts-builder
  - mcp-server: mcp-server
  - skill-creator: skill-creator
  - internal-comms: internal-comms
```

#### BehiSecc Community Skills (3 skills)
```yaml
base_url: https://github.com/BehiSecc/awesome-claude-skills/tree/main

skills:
  - defense-in-depth: defense-in-depth
  - content-research-writer: content-research-writer
  - file-organizer: file-organizer
```

#### Composio Community Skills (2 skills)
```yaml
base_url: https://github.com/ComposioHQ/awesome-claude-skills/tree/main

skills:
  - csv-data-summarizer: csv-data-summarizer
  - playwright-browser-automation: playwright-browser-automation
```

#### Superpowers Marketplace (1 skill)
```yaml
base_url: https://github.com/obra/superpowers-marketplace/tree/main

skills:
  - elements-of-style: elements-of-style
```

---

## Appendix B: Refactoring Effort Estimates

### Detailed Time Estimates by Skill

| Tier | Skill | Complexity | Assessment | Refactoring | Validation | Total |
|------|-------|------------|------------|-------------|------------|-------|
| 1 | systematic-debugging | Medium | 30 min | 3-4 hrs | 30 min | 4-5 hrs |
| 1 | test-driven-development | Medium | 30 min | 3-4 hrs | 30 min | 4-5 hrs |
| 2 | verification | Low-Medium | 30 min | 2-3 hrs | 30 min | 3-4 hrs |
| 2 | webapp-testing | High | 45 min | 5-6 hrs | 45 min | 6.5-7.5 hrs |
| 3A | code-review | Medium | 30 min | 3-4 hrs | 30 min | 4-5 hrs |
| 3A | artifacts-builder | High | 45 min | 4-5 hrs | 45 min | 5.5-6.5 hrs |
| 3A | root-cause-tracing | Medium | 30 min | 3-4 hrs | 30 min | 4-5 hrs |
| 3B | git-worktrees | Medium | 30 min | 2-3 hrs | 30 min | 3-4 hrs |
| 3B | defense-in-depth | Medium-High | 45 min | 3-4 hrs | 45 min | 4.5-5.5 hrs |
| 3B | file-organizer | Low-Medium | 30 min | 2-3 hrs | 30 min | 3-4 hrs |

**Week 2 Target Total:** 22-31 hours (Tiers 1-2, possibly code-review)

---

## Appendix C: License Information

### License Summary by Source

| Source | License | Attribution Required | Commercial Use | Skills Count |
|--------|---------|---------------------|----------------|--------------|
| Superpowers | MIT | Yes (Jesse Vincent) | Allowed | 14 |
| Anthropic | MIT | Yes (Anthropic) | Allowed | 5 |
| BehiSecc | Various | TBD (need to check) | TBD | 3 |
| Composio | Various | TBD (need to check) | TBD | 2 |
| Marketplace | MIT | Yes (Jesse Vincent) | Allowed | 1 |

### Attribution Template

```markdown
# License Attributions

## Superpowers Skills (14 skills)
**Source:** https://github.com/obra/superpowers-skills
**License:** MIT License
**Copyright:** Jesse Vincent and contributors
**Skills:**
- systematic-debugging, test-driven-development, verification, root-cause-tracing
- code-review, brainstorming, planning, parallel-agents
- git-worktrees, finishing-branches
- async-testing, testing-anti-patterns

## Anthropic Skills (5 skills)
**Source:** https://github.com/anthropics/skills
**License:** MIT License
**Copyright:** Anthropic PBC
**Skills:**
- webapp-testing, artifacts-builder, mcp-server, skill-creator, internal-comms

## Community Skills - BehiSecc (3 skills)
**Source:** https://github.com/BehiSecc/awesome-claude-skills
**License:** [To be determined per skill]
**Skills:**
- defense-in-depth, content-research-writer, file-organizer

## Community Skills - Composio (2 skills)
**Source:** https://github.com/ComposioHQ/awesome-claude-skills
**License:** [To be determined per skill]
**Skills:**
- csv-data-summarizer, playwright-browser-automation

## Superpowers Marketplace (1 skill)
**Source:** https://github.com/obra/superpowers-marketplace
**License:** MIT License
**Copyright:** Jesse Vincent
**Skills:**
- elements-of-style (writing-clearly-and-concisely)
```

---

## Appendix D: Quality Checklist

### Pre-Download Checklist
- [ ] GitHub token configured
- [ ] Download script tested
- [ ] Output directories created
- [ ] Validation script ready

### Post-Download Checklist
- [ ] All 23 skills downloaded
- [ ] No download errors
- [ ] All SKILL.md files present
- [ ] License files identified
- [ ] Quality assessment complete

### Post-Refactoring Checklist (Per Skill)
- [ ] Entry point <200 lines
- [ ] References 150-300 lines each
- [ ] All content preserved
- [ ] Navigation map complete
- [ ] Internal links valid
- [ ] Frontmatter valid
- [ ] Validation passed
- [ ] Integration tested

### Week 2 Completion Checklist
- [ ] Tier 1 skills refactored (2/2)
- [ ] Tier 2 skills refactored (2/2)
- [ ] License attributions generated
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Week 3 plan ready

---

**End of Week 2 Priority Plan**

**Status:** Ready for Execution
**Next Action:** Begin Day 1 download process
**Owner:** Development Team
**Review Date:** Nov 20, 2025 (End of Week 2)
