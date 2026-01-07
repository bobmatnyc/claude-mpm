# MPM Skills Manager Agent - Comprehensive Analysis

**Research Date**: 2025-12-11
**Agent**: mpm-skills-manager
**Location**: `~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/claude-mpm/mpm-skills-manager.md`
**Version**: 1.0.0
**Schema**: 1.3.0

---

## Executive Summary

The MPM Skills Manager is a comprehensive autonomous agent responsible for the complete lifecycle of Claude MPM skills, including technology stack detection, skill recommendations, deployment, and PR-based improvements to the skills repository. This agent serves as both a **discovery/recommendation engine** and a **contribution automation system**.

**Key Capabilities**:
- Technology stack detection from project files
- Skill discovery and recommendation matching
- Skill lifecycle management (deploy, update, remove)
- manifest.json management and validation
- Automated PR creation for skill improvements
- Git repository operations with service integration

---

## 1. Agent Definition

### Location and Structure

**Agent Definition Files**:
- **JSON**: `src/claude_mpm/agents/templates/mpm-skills-manager.json` (legacy)
- **Markdown**: `~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/agents/claude-mpm/mpm-skills-manager.md` (active)

**Deployment Location**: `.claude/agents/claude-mpm/mpm-skills-manager.md` (when deployed to projects)

### Agent Metadata

```yaml
name: MPM Skills Manager
agent_id: mpm-skills-manager
agent_type: claude-mpm
version: 1.0.0
schema_version: 1.3.0
model: sonnet
resource_tier: standard
category: claude-mpm
color: green
author: Claude MPM Team
temperature: 0.2
max_tokens: 12288
timeout: 1200
```

### Dependencies

**Python Dependencies**:
- `gitpython>=3.1.0` - Git repository operations
- `pyyaml>=6.0.0` - YAML parsing for manifest and frontmatter
- `jsonschema>=4.17.0` - Manifest validation

**System Dependencies**:
- `python3` - Python runtime
- `git` - Version control operations
- `gh` - GitHub CLI for PR creation

### Capabilities

**Network Access**: `true` (required for git operations, GitHub API, repository sync)

**Optional**: `false` (considered critical infrastructure agent)

---

## 2. Core Responsibilities

### 2.1 Technology Stack Detection

**Purpose**: Analyze project files to identify languages, frameworks, and tools

**Detection Patterns**:

| Language | Detection Files | Framework Indicators |
|----------|----------------|---------------------|
| **Python** | requirements.txt, pyproject.toml, setup.py | fastapi, django, flask, pytest |
| **JavaScript/TypeScript** | package.json, tsconfig.json | react, next, vue, express |
| **Rust** | Cargo.toml | tokio, actix, axum |
| **Go** | go.mod | gin, echo, fiber |
| **Java** | pom.xml, build.gradle | spring-boot, micronaut |
| **Ruby** | Gemfile, *.gemspec | rails, sinatra |

**Confidence Scoring**:
- **High (90%+)**: Explicit dependency in manifest + config file present
- **Medium (70-89%)**: Configuration file present OR single indicator
- **Low (<70%)**: Indirect evidence only, file naming patterns

**Output Format**:
```json
{
  "detected": {
    "languages": ["python", "typescript"],
    "frameworks": ["fastapi", "react"],
    "tools": ["pytest", "vite", "docker"],
    "databases": ["postgresql"]
  },
  "confidence": {
    "python": 0.95,
    "typescript": 0.90,
    "fastapi": 0.95,
    "react": 0.90
  }
}
```

### 2.2 Skill Recommendation Engine

**Purpose**: Match detected technologies to relevant skills from manifest.json

**Recommendation Logic**:

**Step 1: Technology Matching**
- Query manifest.json for all available skills
- Extract tags from each skill entry
- Match skill tags against detected technologies
- Calculate relevance scores

**Step 2: Prioritization**

| Priority | Criteria | Examples |
|----------|----------|----------|
| **Critical** | Core language skills, primary frameworks, testing | python-core, fastapi, pytest |
| **High** | Secondary frameworks, best practices | typescript-core, async patterns |
| **Medium** | Optional enhancements, performance | drizzle ORM, condition-based-waiting |
| **Low** | Niche use cases, experimental | Specialized tooling, alternatives |

**Step 3: Filtering**
- Remove already deployed skills (check `~/.claude/skills/` or `.claude-mpm/skills/`)
- Filter conflicting requirements
- Exclude incompatible versions
- Remove deprecated skills

**Output Format**:
```
Based on your project stack (FastAPI + React + PostgreSQL), I recommend:

1. **toolchains-python-frameworks-fastapi** (Critical, 95% match)
   - Why: FastAPI detected in requirements.txt
   - Install: claude-mpm skills install toolchains-python-frameworks-fastapi
   - Description: FastAPI best practices, async patterns, dependency injection

2. **toolchains-typescript-core** (High, 90% match)
   - Why: TypeScript used throughout frontend
   - Install: claude-mpm skills install toolchains-typescript-core
   - Description: TypeScript advanced patterns, strict mode, generics

3. **toolchains-python-testing-pytest** (High, 85% match)
   - Why: pytest in requirements.txt
   - Install: claude-mpm skills install toolchains-python-testing-pytest
   - Description: pytest fixtures, parametrization, mocking

Install all critical skills? (y/n)
Or select specific: 1,2,3
```

### 2.3 Skill Lifecycle Management

**Discovery Operations**:
- List all available skills from manifest.json
- Filter by category, tags, or toolchain
- Search by keyword
- Check deployment status

**Deployment Process**:
1. Validate skill structure (SKILL.md, references/, manifest entry)
2. Check for version conflicts
3. Copy skill files to target directory
4. Update deployment state tracking
5. Report deployment status

**Deployment Targets**:
- **User Level**: `~/.claude/skills/` (available across all projects)
- **Project Level**: `.claude-mpm/skills/` (project-specific)

**Update Process**:
1. Pull latest from git repository
2. Parse manifest.json for version changes
3. List skills with updates available
4. Redeploy updated skills to targets
5. Report update summary

**Removal Process**:
1. Check for dependent skills (requires[] field)
2. Warn if other skills depend on this one
3. Remove skill files from deployment directory
4. Update state tracking
5. Report removal status

### 2.4 Manifest.json Management

**Manifest Structure**:
```json
{
  "version": "1.0.0",
  "last_updated": "2025-12-01T12:00:00Z",
  "skills": [
    {
      "name": "toolchains-python-frameworks-fastapi",
      "path": "toolchains/python/frameworks/fastapi",
      "entry_point": "SKILL.md",
      "version": "1.0.0",
      "category": "toolchains",
      "toolchain": "python",
      "framework": "fastapi",
      "tags": ["python", "fastapi", "api", "async"],
      "description": "FastAPI best practices and patterns",
      "requires": ["toolchains-python-core"],
      "entry_point_tokens": 150,
      "full_tokens": 1200,
      "author": "bobmatnyc"
    }
  ]
}
```

**Operations**:
- **Add New Skill**: Create entry with name, path, version, tags, token counts
- **Update Existing**: Bump version, update tokens, modify tags/requires
- **Validation**: JSON validity, required fields, semantic versioning, path existence

**Token Count Calculation**:
- **entry_point_tokens**: SKILL.md content only (excludes frontmatter)
- **full_tokens**: SKILL.md + all references/ files
- **Approximation**: 1 token ≈ 4 characters

### 2.5 PR Creation Workflow

**4-Phase PR Process**:

**Phase 1: Analysis**
1. Identify target skill (exists in manifest or new)
2. Review existing content if skill exists
3. Draft improvement structure or new skill design

**Phase 2: Modification**
1. Create branch: `skill/{skill-name}-{issue-description}`
2. Create or update skill files (SKILL.md, references/)
3. Update manifest.json (add entry or bump version)
4. Commit changes with conventional commit format

**Phase 3: Submission**
1. Push branch to remote
2. Generate PR description using PRTemplateService
3. Create PR via GitHubCLIService
4. Handle errors gracefully (gh CLI missing, network issues)

**Phase 4: Follow-up**
1. Report PR URL to user
2. Document changes made (version bump, token counts, tags)
3. List next steps (review, merge, sync, deploy)

**Branch Naming Convention**:
- `skill/{skill-name}-{issue-description}`
- Examples: `skill/fastapi-async-patterns`, `skill/new-tailwind-v4`

**Commit Message Format**:
```
feat(skill): add async patterns to FastAPI skill

- Added async/await route handler examples
- Documented background task patterns
- Updated token counts and version

Requested by users needing FastAPI async guidance.
```

---

## 3. Service Integration

### 3.1 GitOperationsManager

**Purpose**: Git repository operations (branch, commit, push)

**Key Methods**:
- `create_branch(branch_name, branch_type, base_branch, switch_to_branch)`
- `is_working_directory_clean()`
- `get_modified_files()`
- `push_to_remote(branch_name, remote, set_upstream)`

**Usage Pattern**:
```python
from claude_mpm.services.version_control.git_operations import GitOperationsManager

git_manager = GitOperationsManager(
    project_root="~/.claude-mpm/cache/skills/system",
    logger=logger
)

result = git_manager.create_branch(
    branch_name="fastapi-async-patterns",
    branch_type="skill",
    base_branch="main",
    switch_to_branch=True
)
```

### 3.2 PRTemplateService

**Purpose**: Generate PR titles and descriptions

**Key Methods**:
- `generate_pr_title(item_name, brief_description, pr_type, commit_type)`
- `generate_skill_pr_body(skill_name, improvements, justification, examples, related_issues)`
- `validate_conventional_commit(message)`

**Usage Pattern**:
```python
from claude_mpm.services.pr import PRTemplateService, PRType

pr_service = PRTemplateService()

title = pr_service.generate_pr_title(
    item_name="fastapi",
    brief_description="add async patterns",
    pr_type=PRType.SKILL,
    commit_type="feat"
)
# Result: "feat(skill): improve fastapi - add async patterns"

body = pr_service.generate_skill_pr_body(
    skill_name="fastapi",
    improvements="Added async patterns, background tasks, streaming",
    justification="Users requested async guidance",
    examples="Async routes, task queues, SSE",
    related_issues=["#203"]
)
```

### 3.3 GitHubCLIService

**Purpose**: GitHub PR creation via gh CLI

**Key Methods**:
- `validate_environment()` - Check gh installed and authenticated
- `is_gh_installed()` - Detect gh CLI presence
- `is_authenticated()` - Check gh auth status
- `create_pr(repo, title, body, base, draft)`
- `check_pr_exists(repo, head, base)`
- `get_pr_status(pr_url)`

**Error Handling**:
- `GitHubCLINotInstalledError` - gh CLI missing
- `GitHubAuthenticationError` - Not authenticated
- Generic exceptions for API errors

**Usage Pattern**:
```python
from claude_mpm.services.github.github_cli_service import GitHubCLIService

gh_service = GitHubCLIService()

# Validate environment
valid, msg = gh_service.validate_environment()
if not valid:
    print(f"GitHub CLI not ready: {msg}")
    return

# Create PR
pr_url = gh_service.create_pr(
    repo="bobmatnyc/claude-mpm-skills",
    title=title,
    body=body,
    base="main",
    draft=False
)
```

---

## 4. Error Handling

### 4.1 gh CLI Not Installed

**Detection**: `gh_service.is_gh_installed() == False`

**User Message**:
```
GitHub CLI Not Detected

PR creation requires GitHub CLI (gh) to be installed.

Installation Instructions:

macOS:
  brew install gh

Linux:
  # Ubuntu/Debian
  sudo apt install gh

Windows:
  winget install --id GitHub.cli

After installation:
  1. Authenticate: gh auth login
  2. Retry skill improvement

Alternative: Manual PR Creation
Branch has been created: skill/fastapi-async-patterns
Create manually at: https://github.com/bobmatnyc/claude-mpm-skills/compare/skill/fastapi-async-patterns
```

### 4.2 Skill Structure Invalid

**Validation Checks**:
- SKILL.md exists
- SKILL.md has valid YAML frontmatter
- references/ contains only .md files (if present)
- manifest.json has entry for skill

**Error Message**:
```
Skill Structure Validation Failed

Skill: fastapi-async-patterns
Issues found:

1. Missing SKILL.md in skill directory
   Location: toolchains/python/frameworks/fastapi-async/
   Fix: Create SKILL.md with valid YAML frontmatter

2. Invalid file in references/
   File: references/example.txt
   Fix: references/ must contain only .md files

3. Missing manifest.json entry
   Fix: Add skill entry to manifest.json
```

### 4.3 Git Operation Failures

**Uncommitted Changes**:
```
Cannot Create Branch

Issue: Uncommitted changes in skills repository
Modified files:
- toolchains/python/frameworks/fastapi/SKILL.md
- manifest.json

Recovery Steps:
1. Navigate: cd ~/.claude-mpm/cache/skills/system
2. Review changes: git status
3. Options:
   a. Commit changes: git add . && git commit -m "..."
   b. Stash changes: git stash
   c. Discard changes: git reset --hard (CAUTION)
```

**Branch Already Exists**:
```
Branch Already Exists

Branch: skill/fastapi-async-patterns

Options:
1. Use existing branch and continue
2. Delete and recreate branch
3. Rename new branch (skill/fastapi-async-patterns-v2)
```

### 4.4 PR Creation Failures

**Network Timeout**:
```
PR Creation Failed

Error: Network timeout during push to remote

Recovery Steps:
1. Check network: ping github.com
2. Branch committed locally: skill/fastapi-async-patterns
3. Retry push when network stable

Changes are safely committed locally. No data lost.
```

**API Rate Limit**:
```
GitHub API Error

Error: rate limit exceeded (403)

Recovery Steps:
1. Wait for rate limit reset (resets at HH:MM)
2. Branch is pushed: skill/fastapi-async-patterns
3. Create PR manually: https://github.com/bobmatnyc/claude-mpm-skills/compare/...

PR description saved to: /tmp/skill-pr-fastapi-async.md
```

---

## 5. Skill Structure Validation

### Required Structure

```
skills/{category}/{subcategory}/{skill-name}/
├── SKILL.md              ← Entry point (REQUIRED)
├── references/           ← Supporting docs (OPTIONAL)
│   ├── concepts.md
│   ├── patterns.md
│   ├── examples.md
│   └── api-reference.md
└── [manifest.json entry] ← Metadata (REQUIRED)
```

### SKILL.md Requirements

**YAML Frontmatter (REQUIRED)**:
```yaml
---
name: {skill-name}
version: 1.0.0
category: {category}
toolchain: {toolchain-or-null}
framework: {framework-or-null}
tags:
- {tag1}
- {tag2}
description: {brief-description}
requires: []
---
```

**Content Sections (RECOMMENDED)**:
1. **Overview**: What this skill provides
2. **When to Use**: Triggers for using this skill
3. **Core Concepts**: Fundamental concepts
4. **Patterns**: Common patterns and examples
5. **Best Practices**: Do's and don'ts
6. **Anti-Patterns**: What to avoid
7. **References**: External resources

### Validation Checklist

**Before Creating PR**:
- [ ] SKILL.md exists
- [ ] SKILL.md has valid YAML frontmatter
- [ ] All required frontmatter fields present
- [ ] Version follows semantic versioning (X.Y.Z)
- [ ] Tags are lowercase strings
- [ ] references/ contains only .md files (if present)
- [ ] manifest.json has entry for this skill
- [ ] Token counts calculated and added to manifest
- [ ] No circular dependencies in requires[]

---

## 6. Trigger Patterns for PM Delegation

### 6.1 Technology Detection Triggers

**Keywords that should route to mpm-skills-manager**:
- "what skills do I need"
- "recommend skills for this project"
- "detect my tech stack"
- "find skills for [framework]"
- "skill recommendations"

**Pattern**: User asks about skills + project context

### 6.2 Skill Management Triggers

**Keywords**:
- "install skill [name]"
- "deploy skill [name]"
- "update skill [name]"
- "remove skill [name]"
- "list available skills"
- "search for [framework] skill"

**Pattern**: User requests skill lifecycle operations

### 6.3 Skill Improvement Triggers

**Keywords**:
- "improve [skill name]"
- "add [feature] to [skill]"
- "create skill for [technology]"
- "the [skill] is missing [feature]"
- "update [skill] with [pattern]"

**Pattern**: User requests skill content improvements

### 6.4 PR Creation Triggers

**Keywords**:
- "create PR for skill"
- "submit skill improvement"
- "contribute to skills repository"
- "add [technology] skill"

**Pattern**: User explicitly requests PR creation

---

## 7. Agent Routing in PM Instructions

### Current Status: NOT FOUND

**Search Results**: No explicit delegation rules for mpm-skills-manager in current PM instructions

**Implications**:
- PM may not know when to delegate skill-related tasks
- Skills management might be handled ad-hoc
- Technology detection not automatically triggered

**Recommendation**: Add delegation rules to PM instructions

---

## 8. Recommended Delegation Rules

### 8.1 Add to PM Delegation Matrix

```markdown
### Skills Management Delegation

**Trigger Keywords**: "skill", "recommend skills", "detect tech stack", "skill install", "skill update"

**Agent**: mpm-skills-manager

**When to Delegate**:
1. User asks for skill recommendations
2. User requests skill lifecycle operations (install, update, remove)
3. User requests skill improvements or new skill creation
4. User mentions technology stack detection
5. PM detects new project initialization (package.json, requirements.txt created)

**Delegation Template**:
```
Task: [Skill operation: detect/recommend/install/update/improve]
Context: [Project type, detected technologies]
Requirements:
  - Analyze project files for technology stack
  - Query manifest.json for matching skills
  - Provide prioritized recommendations
  - Execute skill operation with validation
Success Criteria: [Specific outcome: skills installed, PR created, recommendations provided]
```

**Example Delegations**:

**Skill Recommendation**:
```
Task: Recommend skills for FastAPI + React project
Context: User initialized new project with requirements.txt (fastapi, pytest) and package.json (react, vite)
Requirements:
  - Detect technologies from project files
  - Query manifest.json for matching skills
  - Prioritize critical skills (fastapi, react, pytest)
  - Provide installation commands
Success Criteria: User receives prioritized skill list with install commands
```

**Skill Improvement PR**:
```
Task: Create PR to add async patterns to FastAPI skill
Context: User reports FastAPI skill missing async/await examples
Requirements:
  - Review existing fastapi skill content
  - Add async patterns section with examples
  - Update manifest.json (version bump, token counts)
  - Create PR with conventional commit
Success Criteria: PR created at bobmatnyc/claude-mpm-skills with async examples
```
```

### 8.2 Add to Circuit Breakers

**Proposed Circuit Breaker #9: Skills Management Boundary**

```markdown
## Circuit Breaker #9: Skills Management Boundary

### Violation

PM directly executes skill operations instead of delegating to mpm-skills-manager.

### Trigger Conditions

**PM MUST delegate when**:
- User asks "what skills should I use"
- User requests "install skill [name]"
- User says "recommend skills for [technology]"
- User mentions "skill improvements" or "add skill for [framework]"
- PM detects new project files (package.json, requirements.txt) without skills deployed

**Delegation Required**:
- Technology stack detection
- Skill recommendations
- Skill deployment/updates
- Skill PR creation
- manifest.json management

### Examples

**❌ VIOLATION: PM directly reads manifest.json**
```
User: "What FastAPI skills are available?"
PM: [Uses Read tool to read manifest.json and lists skills]
```

**✅ CORRECT: PM delegates to mpm-skills-manager**
```
User: "What FastAPI skills are available?"
PM: [Delegates to mpm-skills-manager for skill discovery]
```

**❌ VIOLATION: PM directly installs skills**
```
User: "Install the FastAPI skill"
PM: [Uses Bash to run skill deployment commands]
```

**✅ CORRECT: PM delegates to mpm-skills-manager**
```
User: "Install the FastAPI skill"
PM: [Delegates to mpm-skills-manager for skill deployment]
```
```

### 8.3 Add to Agent Presets

**Already Present**: `mpm-skills-manager` is included in ALL presets via `CORE_AGENTS` list

**Location**: `src/claude_mpm/config/agent_presets.py` line 30

**Evidence**:
```python
CORE_AGENTS = [
    "claude-mpm/mpm-agent-manager",  # Agent lifecycle management
    "claude-mpm/mpm-skills-manager",  # Skills management  ← PRESENT
    "universal/research",
    "documentation/documentation",
    "engineer/core/engineer",
]
```

**Status**: ✅ No changes needed - agent is already in all presets

---

## 9. Integration Points

### 9.1 With Research Agent

**Scenario**: Research agent detects technology stack, recommends skills

**Current Behavior**:
- Research agent has Claude Code skill gap detection built-in
- Checks `~/.claude/skills/` for deployed skills
- Recommends missing skills based on technology mapping
- Provides installation commands

**Recommendation**: Research should delegate to mpm-skills-manager for:
- Actual skill deployment (not just recommendations)
- Skill updates and version management
- PR creation for skill improvements

### 9.2 With PM Agent

**Scenario**: PM detects project initialization, ensures skills deployed

**Current Behavior**: PM may not automatically trigger skill recommendations

**Recommendation**: PM should delegate to mpm-skills-manager when:
- New project initialized (package.json, requirements.txt created)
- User asks about skills
- Technology stack changes detected

### 9.3 With Engineer Agents

**Scenario**: Engineer completes implementation, identifies skill gaps

**Current Behavior**: Engineers may mention missing skills in output

**Recommendation**: Engineers should delegate to mpm-skills-manager when:
- Pattern used that could be a skill
- Repetitive code that belongs in skill
- Technology used without corresponding skill

---

## 10. Gaps in Agent Instructions

### 10.1 Missing from Agent Definition

**No Explicit Trigger Patterns**: Agent instructions don't specify when PM should delegate

**No User-Facing Examples**: Agent focuses on technical implementation, lacks user interaction examples

**No Integration with Other Agents**: Doesn't document how it works with Research/PM/Engineers

### 10.2 Missing from PM Instructions

**No Delegation Rules**: PM instructions don't mention mpm-skills-manager

**No Circuit Breaker**: No explicit boundary for skills management

**No Workflow Integration**: Skills not part of 5-phase workflow

### 10.3 Missing from Research Instructions

**Skill Deployment Gap**: Research recommends skills but doesn't deploy them

**No Delegation Pattern**: Research doesn't delegate to mpm-skills-manager for actual installation

---

## 11. Recommended Next Steps

### 11.1 Update PM Instructions

**Add Section**: "Skills Management Delegation"

**Location**: After "Ticketing Integration" section in WORKFLOW.md

**Content**:
- Trigger keywords for skill operations
- Delegation template for mpm-skills-manager
- Examples of skill-related tasks
- Circuit breaker for skills boundary

### 11.2 Add Circuit Breaker

**Circuit Breaker #9**: Skills Management Boundary

**File**: `src/claude_mpm/agents/templates/circuit-breakers.md`

**Content**: PM must delegate all skill operations to mpm-skills-manager

### 11.3 Update Research Agent

**Modify**: Research agent skill gap detection

**Change**: Instead of just recommending, delegate to mpm-skills-manager for:
- Skill deployment
- Skill updates
- PR creation for missing skills

### 11.4 Test Agent Integration

**Create Test Scenarios**:
1. User asks "what skills do I need" → PM delegates to mpm-skills-manager
2. Research detects tech stack → Delegates to mpm-skills-manager for deployment
3. User requests "improve FastAPI skill" → PM delegates to mpm-skills-manager for PR

---

## 12. Summary

### Agent Capabilities (Complete)

**✅ Technology Detection**: Analyzes project files for languages, frameworks, tools
**✅ Skill Recommendations**: Matches technologies to skills with prioritization
**✅ Skill Lifecycle**: Deploy, update, remove skills with validation
**✅ Manifest Management**: Update manifest.json with version, tags, tokens
**✅ PR Creation**: 4-phase workflow with GitOperationsManager, PRTemplateService, GitHubCLIService
**✅ Error Handling**: Graceful degradation for gh CLI, git operations, network issues
**✅ Skill Validation**: Structure checks, frontmatter validation, token calculation

### Agent Integration (Incomplete)

**❌ PM Delegation Rules**: Not present in PM_INSTRUCTIONS.md or WORKFLOW.md
**❌ Circuit Breaker**: No skills management boundary defined
**⚠️ Research Integration**: Research recommends but doesn't delegate deployment
**✅ Agent Presets**: Already included in all presets via CORE_AGENTS

### Trigger Patterns (Need Documentation)

**User-Facing Keywords**:
- "recommend skills", "what skills", "skill install", "skill update"
- "improve [skill]", "add skill for [tech]", "create skill"
- "detect tech stack", "find skills for [framework]"

**System Triggers**:
- New project initialization (package.json, requirements.txt created)
- Technology stack changes detected
- Skill gaps identified by Research agent

### Recommended Actions

**HIGH PRIORITY**:
1. Add PM delegation rules for skills management
2. Create Circuit Breaker #9: Skills Management Boundary
3. Update WORKFLOW.md with skills delegation section

**MEDIUM PRIORITY**:
4. Update Research agent to delegate skill deployment to mpm-skills-manager
5. Add skill management to PM workflow examples

**LOW PRIORITY**:
6. Create integration tests for PM → mpm-skills-manager delegation
7. Document user-facing skill management workflow

---

## Appendix: Technology-to-Skills Mappings

### Python Stack

```python
PYTHON_STACK_SKILLS = {
    "fastapi": [
        "toolchains-python-frameworks-fastapi",
        "toolchains-python-testing-pytest",
        "toolchains-python-async-asyncio"
    ],
    "django": [
        "toolchains-python-frameworks-django",
        "toolchains-python-testing-pytest"
    ],
    "flask": [
        "toolchains-python-frameworks-flask",
        "toolchains-python-testing-pytest"
    ],
    "pytest": [
        "toolchains-python-testing-pytest",
        "universal-testing-testing-anti-patterns"
    ]
}
```

### JavaScript/TypeScript Stack

```python
JS_STACK_SKILLS = {
    "react": [
        "toolchains-javascript-frameworks-react",
        "toolchains-typescript-core"
    ],
    "nextjs": [
        "toolchains-nextjs-core",
        "toolchains-nextjs-v16"
    ],
    "jest": [
        "toolchains-typescript-testing-jest"
    ],
    "vitest": [
        "toolchains-typescript-testing-vitest"
    ]
}
```

---

**Research Complete**: 2025-12-11
**Findings Saved**: docs/research/mpm-skills-manager-analysis-2025-12-11.md
**Next Steps**: Update PM instructions with skills delegation rules
