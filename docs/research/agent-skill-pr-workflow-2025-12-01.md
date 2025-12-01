# Agent and Skill PR Workflow Architecture

**Research Date:** 2025-12-01
**Researcher:** Research Agent
**Status:** Complete
**Confidence:** 95%

## Executive Summary

This document provides a comprehensive analysis of the current git integration for agent and skill repositories, and proposes a PR workflow architecture for automated improvements. The research reveals a robust git-based infrastructure with ETag caching, SQLite state tracking, and clear separation between cached repositories and deployed agents.

**Key Findings:**
- Both agent and skill repositories are fully git-enabled with working directory caching
- Current agent-manager is CLI-focused, not an autonomous agent
- No existing PR automation - all changes are manual
- Clear separation: cache (`~/.claude-mpm/cache/`) → deployment (`~/.claude/agents/`)
- Skills use manifest.json for discovery, agents use directory traversal

**Recommendation:** Create two new autonomous agents:
1. **agent-improver-agent**: Monitors agent usage, suggests improvements, creates PRs
2. **skills-manager-agent**: Manages skill lifecycle, suggests skills, creates PRs

---

## 1. Current Architecture Analysis

### 1.1 Git Integration Status

#### Agents Repository
- **Location**: `~/.claude-mpm/cache/remote-agents/bobmatnyc/claude-mpm-agents/`
- **Remote**: `https://github.com/bobmatnyc/claude-mpm-agents.git`
- **Structure**: Nested directory hierarchy by category
  ```
  agents/
  ├── engineer/
  │   ├── backend/python-engineer.md
  │   ├── frontend/react-engineer.md
  │   └── core/engineer.md
  ├── universal/
  │   ├── research.md
  │   └── product-owner.md
  ├── documentation/
  ├── qa/
  ├── ops/
  └── security/
  ```
- **File Format**: Markdown with YAML frontmatter
- **Git Status**: ✅ Fully initialized and working

#### Skills Repository
- **Location**: `~/.claude-mpm/cache/skills/system/`
- **Remote**: `https://github.com/bobmatnyc/claude-mpm-skills.git`
- **Structure**: Nested by toolchain/category with SKILL.md entry points
  ```
  skills/
  ├── universal/
  │   ├── collaboration/git-workflow/SKILL.md
  │   └── security/security-scanning/SKILL.md
  ├── toolchains/
  │   ├── python/fastapi/SKILL.md
  │   └── javascript/react/SKILL.md
  ├── manifest.json (metadata and discovery)
  └── .bundles/ (compiled skill bundles)
  ```
- **File Format**: Markdown with YAML frontmatter + manifest.json
- **Git Status**: ✅ Fully initialized and working

### 1.2 Sync Architecture

#### GitSourceSyncService (Agents)
**File**: `src/claude_mpm/services/agents/sources/git_source_sync_service.py`

**Key Features:**
- Uses `raw.githubusercontent.com` URLs (no API rate limits)
- ETag-based caching for efficient updates
- SQLite state tracking (`AgentSyncState`)
- SHA-256 content hashing for change detection
- Single-threaded sequential download

**Workflow:**
```
1. Check ETag cache for each agent file
2. HTTP HEAD request to check if modified
3. If modified (ETag mismatch): download via raw URL
4. If not modified: skip (use cached)
5. Update SQLite sync state
6. Save to cache directory
```

**Performance Metrics:**
- First sync (10 agents): 5-10 seconds
- Subsequent sync (no changes): 1-2 seconds
- Partial update (2/10 changed): 2-3 seconds

#### GitSkillSourceManager (Skills)
**File**: `src/claude_mpm/services/skills/git_skill_source_manager.py`

**Key Features:**
- Reuses `GitSourceSyncService` for Git operations
- Recursive directory traversal via GitHub Tree API
- **Parallel downloads** with ThreadPoolExecutor
- Multi-source support with priority resolution
- Manifest.json for skill discovery

**Workflow:**
```
1. Fetch GitHub Tree API for repository structure
2. Discover all SKILL.md files recursively
3. Download in parallel (ThreadPoolExecutor)
4. Thread-safe ETag cache updates
5. Generate manifest.json from discovered skills
```

**Performance:**
- Skills sync is **faster** than agents (parallel downloads)
- Supports multiple skill sources (priority-based conflict resolution)

### 1.3 Deployment Workflow

#### Current Process
```
┌─────────────────────────────────────────────────┐
│  1. Sync from Git Repository                    │
│     git pull OR HTTP download via raw URLs      │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  2. Cache in Local Directory                    │
│     ~/.claude-mpm/cache/remote-agents/          │
│     ~/.claude-mpm/cache/skills/system/          │
└──────────────────┬──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│  3. Deploy to Active Directory                  │
│     ~/.claude/agents/*.md                       │
│     .claude/skills/ (project-level)             │
└─────────────────────────────────────────────────┘
```

**Key Insight**: Cache and deployment are **separate**. This enables:
- Preserving nested structure in cache
- Flattening for deployment
- Multiple deployment targets (user, project)
- Safe rollback and versioning

---

## 2. Agent Manager Analysis

### 2.1 What Agent Manager Actually Is

**CRITICAL FINDING**: "agent-manager" is **NOT an autonomous agent** - it's a CLI command.

**File**: `src/claude_mpm/cli/commands/agent_manager.py`
**Type**: CLI command class (`AgentManagerCommand`)
**Purpose**: Interactive agent lifecycle management

**What it does:**
- Creates new agent templates (interactive wizard)
- Deploys agents to project/user tiers
- Lists and validates agents
- Resets claude-mpm authored agents
- Manages local JSON agent templates

**What it does NOT do:**
- Autonomous agent improvement detection
- Automated PR creation
- Git repository modification
- Agent behavior monitoring

### 2.2 Agent Manager Capabilities

**Commands Implemented:**
```python
command_map = {
    "list": self._list_agents,
    "create": self._create_agent,
    "variant": self._create_variant,
    "deploy": self._deploy_agent,
    "customize-pm": self._customize_pm,
    "show": self._show_agent,
    "test": self._test_agent,
    "templates": self._list_templates,
    "reset": self._reset_agents,
    "create-interactive": self._create_interactive,
    "manage-local": self._manage_local_interactive,
    "edit-interactive": self._edit_interactive,
    "test-local": self._test_local_agent,
    "create-local": self._create_local_agent,
    "deploy-local": self._deploy_local_agents,
    "list-local": self._list_local_agents,
    "sync-local": self._sync_local_agents,
    "export-local": self._export_local_agents,
    "import-local": self._import_local_agents,
    "delete-local": self._delete_local_agents,
}
```

### 2.3 Agent Manager Template

**File**: `src/claude_mpm/agents/templates/agent-manager.md`
**Type**: Markdown agent instructions (not JSON)
**Purpose**: System agent for agent lifecycle management

**Key Section: Agent Improvement Workflow** (Lines 359-534)

This section documents the **manual** workflow for improving agents:

```markdown
## Agent Improvement Workflow

### 1. Work on Cached Agent Definition
Location: ~/.claude-mpm/cache/remote-agents/<repo-name>/

### 2. Validate Changes
Run validation before committing

### 3. Version and Push to Git
Copy changes from cache to repo → commit → push

### 4. Re-deploy Agent
claude-mpm agent-source update → deploy --force

### 5. Submit Pull Request (External Contributors)
Fork → clone → edit → commit → push → create PR
```

**Key Insight**: This is a **manual process**. No automation exists.

---

## 3. Skills Management

### 3.1 Current Skills Architecture

**Discovery Mechanism:**
- Skills use `manifest.json` for metadata and discovery
- Manifest contains: name, version, category, tags, token counts
- SkillDiscoveryService scans for `SKILL.md` files
- Builds skill catalog with dependencies

**Example Manifest Entry:**
```json
{
  "name": "git-workflow",
  "version": "0.1.0",
  "category": "universal",
  "toolchain": null,
  "framework": null,
  "tags": ["git", "version-control"],
  "entry_point_tokens": 91,
  "full_tokens": 563,
  "requires": [],
  "author": "bobmatnyc",
  "source_path": "universal/collaboration/git-workflow/SKILL.md"
}
```

### 3.2 Skills vs Agents Differences

| Aspect | Agents | Skills |
|--------|--------|--------|
| **Discovery** | Directory traversal | manifest.json |
| **Structure** | Flat or nested .md files | SKILL.md entry points + references/ |
| **Metadata** | YAML frontmatter only | YAML + manifest.json |
| **Sync** | Sequential download | Parallel download (ThreadPoolExecutor) |
| **Versioning** | Version in frontmatter | Version in manifest + frontmatter |
| **Dependencies** | Optional parent agents | Explicit requires[] in manifest |
| **Token Tracking** | No | Yes (entry_point_tokens, full_tokens) |

### 3.3 Skills Gap in Tooling

**No skills manager exists**. Current skills CLI is basic:
- `claude-mpm skills list` - List available skills
- `claude-mpm skills sync` - Sync from repositories
- `claude-mpm skills deploy` - Deploy to project

**Missing capabilities:**
- Skill recommendation based on project technology
- Skill effectiveness tracking
- Automated skill improvement suggestions
- PR workflow for skill contributions

---

## 4. PR Workflow Architecture Design

### 4.1 Problem Statement

**Current State:**
- Manual agent improvement workflow
- No automated detection of improvement opportunities
- No PR automation for contributions
- Skills have no improvement workflow at all

**Desired State:**
- Autonomous agents detect improvement opportunities
- Automated PR creation with context and rationale
- Community contributions streamlined
- Feedback loop from agent usage to improvements

### 4.2 Proposed Architecture

#### Create Two New Autonomous Agents

##### 1. Agent Improver Agent
**Purpose:** Monitors agent performance and suggests improvements

**Triggers:**
- User feedback (explicit: "this agent didn't work well")
- Error patterns in agent responses
- Circuit breaker violations
- Repeated handoff failures
- Manual request: "improve the research agent"

**Workflow:**
```
┌──────────────────────────────────────────────────┐
│ 1. Detect Improvement Opportunity                │
│    - Error patterns                              │
│    - User feedback                               │
│    - Performance metrics                         │
└───────────────────┬──────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────┐
│ 2. Analyze Agent Definition                      │
│    - Read from cache/remote-agents/              │
│    - Parse YAML frontmatter                      │
│    - Understand current instructions             │
└───────────────────┬──────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────┐
│ 3. Draft Improvements                            │
│    - Propose specific instruction changes        │
│    - Update frontmatter if needed                │
│    - Validate YAML syntax                        │
└───────────────────┬──────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────┐
│ 4. Create Feature Branch                         │
│    cd ~/.claude-mpm/cache/remote-agents/...      │
│    git checkout -b improve/{agent}-{issue}       │
└───────────────────┬──────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────┐
│ 5. Commit Changes                                │
│    git add agents/{agent}.md                     │
│    git commit -m "feat: improve {agent} agent"   │
└───────────────────┬──────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────┐
│ 6. Push Branch                                   │
│    git push -u origin improve/{agent}-{issue}    │
└───────────────────┬──────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────┐
│ 7. Create Pull Request (gh CLI)                 │
│    gh pr create --title "..." --body "..."       │
│    Include: problem, solution, testing           │
└──────────────────────────────────────────────────┘
```

##### 2. Skills Manager Agent
**Purpose:** Manages skill lifecycle and suggests improvements

**Triggers:**
- Technology stack detection (new project dependencies)
- Skill effectiveness tracking (low usage or poor results)
- User requests: "recommend skills for this project"
- Manual skill improvement requests

**Workflow:**
```
┌──────────────────────────────────────────────────┐
│ 1. Detect Opportunity                            │
│    - Project tech stack changes                  │
│    - Missing recommended skills                  │
│    - Skill improvement feedback                  │
└───────────────────┬──────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────┐
│ 2. Technology Stack Analysis                     │
│    - Scan package.json, requirements.txt, etc    │
│    - Identify frameworks and toolchains          │
│    - Compare against manifest.json skills        │
└───────────────────┬──────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────┐
│ 3. Generate Recommendations OR Improvements      │
│    - Recommend: Suggest skills for project       │
│    - Improve: Draft skill content updates        │
└───────────────────┬──────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────┐
│ 4. Create Feature Branch (for improvements)     │
│    cd ~/.claude-mpm/cache/skills/system/         │
│    git checkout -b skill/{name}-{issue}          │
└───────────────────┬──────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────┐
│ 5. Modify Skill Files                            │
│    - Update SKILL.md                             │
│    - Update references/ if needed                │
│    - Regenerate manifest.json                    │
└───────────────────┬──────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────┐
│ 6. Commit and Push                               │
│    git add . && git commit -m "feat: ..."        │
│    git push -u origin skill/{name}-{issue}       │
└───────────────────┬──────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────┐
│ 7. Create Pull Request (gh CLI)                 │
│    gh pr create --title "..." --body "..."       │
└──────────────────────────────────────────────────┘
```

### 4.3 Implementation Components

#### Component 1: Git Operations Service
**File:** `src/claude_mpm/services/git/git_operations_service.py` (new)

**Purpose:** Abstraction layer for git operations used by both agents

**Methods:**
```python
class GitOperationsService:
    def create_branch(self, repo_path: Path, branch_name: str) -> bool
    def commit_changes(self, repo_path: Path, message: str, files: List[str]) -> bool
    def push_branch(self, repo_path: Path, branch_name: str) -> bool
    def create_pull_request(self, repo: str, title: str, body: str, base: str = "main") -> str
    def get_current_branch(self, repo_path: Path) -> str
    def has_uncommitted_changes(self, repo_path: Path) -> bool
    def validate_repo(self, repo_path: Path) -> Tuple[bool, str]
```

**Authentication Strategy:**
- Use GitHub CLI (`gh`) for PR creation (inherits auth from gh CLI)
- Fallback to `GITHUB_TOKEN` environment variable
- Error gracefully if neither available

**Dependencies:**
- `gh` CLI (GitHub's official CLI)
- `gitpython` library for git operations
- Subprocess for git commands

#### Component 2: PR Template Service
**File:** `src/claude_mpm/services/pr/pr_template_service.py` (new)

**Purpose:** Generate consistent PR descriptions

**Methods:**
```python
class PRTemplateService:
    def generate_agent_improvement_pr(
        self,
        agent_name: str,
        problem: str,
        solution: str,
        testing_notes: str,
        related_issues: List[str] = None
    ) -> str

    def generate_skill_improvement_pr(
        self,
        skill_name: str,
        improvements: str,
        justification: str,
        examples: str
    ) -> str
```

**PR Template Structure:**
```markdown
## Problem Statement
{clear description of what wasn't working}

## Proposed Solution
{specific changes made to agent/skill}

## Testing Performed
- [ ] Validated YAML frontmatter
- [ ] Tested agent with sample tasks
- [ ] Verified no regression in existing behavior

## Related Issues
Closes #{issue_number}

## Checklist
- [ ] Instructions are clear and unambiguous
- [ ] No conflicting guidance
- [ ] Follows agent architecture best practices
- [ ] Documentation updated if needed

---
🤖 Generated with Claude MPM Agent Improver
```

#### Component 3: Agent Improver Agent Definition
**File:** `src/claude_mpm/agents/templates/agent-improver.md` (new)

**Frontmatter:**
```yaml
---
name: agent_improver
description: Autonomous agent that monitors agent performance and creates PRs for improvements
version: 1.0.0
schema_version: 1.3.0
agent_id: agent-improver
agent_type: system
model: sonnet
resource_tier: high
tags:
  - system
  - meta
  - improvement
  - automation
  - pr-workflow
category: system
color: blue
temperature: 0.2
max_tokens: 16384
timeout: 1800
capabilities:
  network_access: true
dependencies:
  python:
    - gitpython>=3.1.0
    - PyGithub>=2.1.0
  system:
    - python3
    - git
    - gh
  optional: false
---
```

**Key Instructions:**
1. **Improvement Detection**: Monitor agent performance and user feedback
2. **Root Cause Analysis**: Understand why agent instructions failed
3. **Solution Design**: Draft specific, actionable improvements
4. **Git Workflow**: Branch, commit, push, PR creation
5. **PR Quality**: Clear problem statement, solution, and testing
6. **Non-Blocking**: Never block user workflow, report failures gracefully

#### Component 4: Skills Manager Agent Definition
**File:** `src/claude_mpm/agents/templates/skills-manager.md` (new)

**Frontmatter:**
```yaml
---
name: skills_manager
description: Manages skill lifecycle, recommendations, and improvements with PR workflow
version: 1.0.0
schema_version: 1.3.0
agent_id: skills-manager
agent_type: system
model: sonnet
resource_tier: standard
tags:
  - system
  - skills
  - recommendations
  - automation
  - pr-workflow
category: system
color: green
temperature: 0.2
max_tokens: 12288
timeout: 1200
capabilities:
  network_access: true
dependencies:
  python:
    - gitpython>=3.1.0
    - PyGithub>=2.1.0
  system:
    - python3
    - git
    - gh
  optional: false
---
```

**Key Instructions:**
1. **Technology Detection**: Scan project for frameworks and toolchains
2. **Skill Recommendations**: Match tech stack to available skills
3. **Gap Analysis**: Identify missing skills that should exist
4. **Skill Improvement**: Draft updates to existing skills
5. **Manifest Management**: Update manifest.json when creating/modifying skills
6. **PR Workflow**: Same as agent-improver but for skills

### 4.4 Decision Trees

#### When to Create PR (Agent Improver)

```
User provides feedback about agent?
    │
    ├─ YES → Is feedback actionable? (specific issue)
    │         │
    │         ├─ YES → Analyze agent definition
    │         │         │
    │         │         └─ Draft improvement → Create PR
    │         │
    │         └─ NO → Ask clarifying questions → Retry
    │
    └─ NO → Is this a manual improvement request?
              │
              ├─ YES → "improve research agent for X"
              │         │
              │         └─ Analyze + Draft + PR
              │
              └─ NO → Monitor only (no PR)
```

#### When to Create PR (Skills Manager)

```
User requests skill recommendation?
    │
    ├─ YES → Detect tech stack
    │         │
    │         └─ Recommend skills (no PR)
    │
    └─ NO → User requests skill improvement?
              │
              ├─ YES → Analyze skill
              │         │
              │         └─ Draft improvement → Create PR
              │
              └─ NO → Project tech stack changed?
                        │
                        ├─ YES → Missing critical skills?
                        │         │
                        │         ├─ YES → Recommend (no PR)
                        │         │         OR Create new skill (PR)
                        │         │
                        │         └─ NO → No action
                        │
                        └─ NO → No action
```

### 4.5 Branch Naming Conventions

**Agents:**
```
improve/{agent-name}-{short-description}
improve/research-memory-efficiency
improve/engineer-error-handling
improve/qa-test-coverage-detection
```

**Skills:**
```
skill/{skill-name}-{short-description}
skill/git-workflow-rebase-guidance
skill/fastapi-testing-async-patterns
skill/new-rust-cli-development
```

### 4.6 Commit Message Format

**Follow Conventional Commits:**
```
feat(agent): improve research agent memory efficiency

- Add explicit file limit warnings
- Document MCP summarizer integration
- Update strategic sampling guidance

Addresses user feedback about memory exhaustion when
analyzing large codebases.
```

**For Skills:**
```
feat(skill): add async patterns to FastAPI testing skill

- Document pytest-asyncio usage
- Add examples for async client fixtures
- Include database transaction handling

Requested by multiple users working on FastAPI projects.
```

---

## 5. Implementation Strategy

### 5.1 Phase 1: Infrastructure (Week 1)

**Deliverables:**
1. `GitOperationsService` - Git abstraction layer
2. `PRTemplateService` - PR description generation
3. Unit tests for both services
4. Integration tests with test repositories

**Acceptance Criteria:**
- Can create branches programmatically
- Can commit and push changes
- Can create PRs via `gh` CLI
- All tests passing (>85% coverage)

### 5.2 Phase 2: Agent Improver (Week 2)

**Deliverables:**
1. `agent-improver.md` agent definition
2. Agent improvement detection logic
3. Agent analysis and improvement generation
4. End-to-end PR workflow integration
5. User communication for PR status

**Acceptance Criteria:**
- Agent can analyze existing agent definitions
- Agent can detect improvement opportunities
- Agent can create well-formatted PRs
- Graceful error handling for git failures
- Non-blocking behavior (reports but doesn't fail)

### 5.3 Phase 3: Skills Manager (Week 3)

**Deliverables:**
1. `skills-manager.md` agent definition
2. Technology stack detection
3. Skill recommendation engine
4. Skill improvement workflow
5. Manifest.json update logic

**Acceptance Criteria:**
- Agent can detect project technology
- Agent recommends relevant skills
- Agent can improve existing skills
- Agent maintains manifest.json integrity
- Same PR workflow quality as agent-improver

### 5.4 Phase 4: Integration & Polish (Week 4)

**Deliverables:**
1. PM instructions update for new agents
2. CLI commands: `claude-mpm agents improve`, `claude-mpm skills recommend`
3. Documentation and examples
4. Integration tests
5. User acceptance testing

**Acceptance Criteria:**
- Seamless integration with existing workflows
- Clear user communication
- Comprehensive error messages
- Documentation complete
- All tests passing

---

## 6. Files to Modify

### New Files to Create

```
src/claude_mpm/services/git/
├── __init__.py
├── git_operations_service.py      # Git abstraction layer
└── git_auth_manager.py             # GitHub authentication

src/claude_mpm/services/pr/
├── __init__.py
├── pr_template_service.py          # PR description generation
└── pr_workflow_service.py          # End-to-end PR creation

src/claude_mpm/agents/templates/
├── agent-improver.md               # Agent improver agent definition
└── skills-manager.md               # Skills manager agent definition

tests/services/git/
├── test_git_operations_service.py
└── test_git_auth_manager.py

tests/services/pr/
├── test_pr_template_service.py
└── test_pr_workflow_service.py
```

### Existing Files to Modify

```
src/claude_mpm/agents/PM_INSTRUCTIONS.md
- Add agent-improver delegation rules
- Add skills-manager delegation rules
- Document PR workflow

src/claude_mpm/cli/commands/
- agents.py (add 'improve' subcommand)
- skills.py (add 'recommend' subcommand)

src/claude_mpm/cli/parsers/
- agent_manager_parser.py (add improve command)
- skill_manager_parser.py (add recommend command)
```

---

## 7. Authentication Strategy

### GitHub Authentication Options

**Option 1: GitHub CLI (`gh`) - RECOMMENDED**
- **Pros:**
  - Users already authenticate: `gh auth login`
  - Inherits credentials transparently
  - Supports SSO and 2FA
  - No token management in code
- **Cons:**
  - Requires `gh` CLI installed
  - Subprocess call overhead
- **Implementation:**
  ```bash
  gh pr create --title "..." --body "..." --base main
  ```

**Option 2: GitHub Token (Fallback)**
- **Pros:**
  - Direct API access
  - No external dependency
- **Cons:**
  - User must generate token
  - Token storage security concerns
  - Manual token rotation
- **Implementation:**
  ```python
  # Read from ~/.claude-mpm/config.json or env var
  token = os.getenv("GITHUB_TOKEN")
  github = Github(token)
  ```

**Option 3: SSH Keys**
- **Pros:**
  - Already configured for git push
- **Cons:**
  - Cannot create PRs via git alone (needs API)
  - Still requires token for PR creation

**Decision:** Use **GitHub CLI as primary**, with **token as fallback**.

### Authentication Flow

```
┌────────────────────────────────────────────────┐
│ 1. Check for gh CLI                            │
│    command -v gh                               │
└───────────────────┬────────────────────────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │ gh CLI available?    │
         └──────┬───────────────┘
                │
       ┌────────┴────────┐
       │                 │
      YES               NO
       │                 │
       ▼                 ▼
┌──────────────┐  ┌─────────────────────┐
│ Use gh CLI   │  │ Check GITHUB_TOKEN  │
│ gh pr create │  │ env var or config   │
└──────────────┘  └──────────┬──────────┘
                             │
                             ▼
                   ┌──────────────────┐
                   │ Token available? │
                   └─────┬────────────┘
                         │
                ┌────────┴────────┐
                │                 │
               YES               NO
                │                 │
                ▼                 ▼
         ┌──────────────┐  ┌────────────────┐
         │ Use PyGithub │  │ Error: Cannot  │
         │ with token   │  │ authenticate   │
         └──────────────┘  └────────────────┘
```

---

## 8. Risk Assessment

### Risk 1: GitHub Authentication Failure
**Severity:** High
**Likelihood:** Medium
**Impact:** PRs cannot be created

**Mitigation:**
- Clear error messages with setup instructions
- Fallback authentication methods
- Graceful degradation (save PR content locally)
- Documentation with authentication setup steps

### Risk 2: Git Conflicts During PR Creation
**Severity:** Medium
**Likelihood:** Low
**Impact:** PR creation fails, branch in inconsistent state

**Mitigation:**
- Always pull latest before creating branch
- Detect conflicts and report to user
- Never force push
- Provide rollback mechanism

### Risk 3: Invalid Agent/Skill Modifications
**Severity:** High
**Likelihood:** Medium
**Impact:** Broken agent/skill definitions

**Mitigation:**
- YAML validation before commit
- Agent/skill definition schema validation
- Dry-run mode for testing
- PR review by humans before merge
- CI/CD validation in repositories

### Risk 4: Overwhelming Repository with PRs
**Severity:** Medium
**Likelihood:** Medium
**Impact:** Repository maintainer burden

**Mitigation:**
- Rate limiting: max 1 PR per agent per day
- Require user confirmation before PR creation
- Batch related improvements into single PR
- Clear PR quality standards

### Risk 5: Loss of Manual Workflow
**Severity:** Low
**Likelihood:** Low
**Impact:** Users prefer manual control

**Mitigation:**
- Keep manual workflow documented
- Provide opt-out mechanism
- PR creation is opt-in, not automatic
- Maintain backward compatibility

---

## 9. Specific Acceptance Criteria

### Agent Improver Agent

**Must:**
- ✅ Detect improvement opportunities from user feedback
- ✅ Analyze agent markdown files from cache directory
- ✅ Generate valid YAML frontmatter modifications
- ✅ Create feature branches with correct naming
- ✅ Commit with conventional commit messages
- ✅ Push branches to remote repository
- ✅ Create well-formatted PRs with problem/solution/testing
- ✅ Handle authentication failures gracefully
- ✅ Report PR URL or error details to user
- ✅ Never block user workflow (non-blocking errors)

**Should:**
- Batch related improvements into single PR
- Reference related GitHub issues
- Include testing checklist in PR
- Suggest reviewers based on agent category

**Could:**
- Auto-detect improvement opportunities from logs
- Track improvement effectiveness after merge
- Learn from PR review feedback

### Skills Manager Agent

**Must:**
- ✅ Detect project technology stack from config files
- ✅ Recommend relevant skills from manifest.json
- ✅ Analyze skill markdown files
- ✅ Generate skill improvements with examples
- ✅ Update manifest.json when modifying skills
- ✅ Create feature branches with skill/ prefix
- ✅ Follow same PR workflow as agent-improver
- ✅ Validate skill references/ directory integrity
- ✅ Handle missing skills gracefully
- ✅ Report recommendations or PR status

**Should:**
- Track skill effectiveness (usage metrics)
- Suggest skill combinations for workflows
- Detect redundant or overlapping skills
- Propose skill deprecation when obsolete

**Could:**
- Auto-generate skills from project patterns
- Migrate skills between categories
- Create skill bundles for common stacks

---

## 10. Conclusion

### Summary of Findings

1. **Git Integration is Robust**: Both repositories are git-enabled with sophisticated sync mechanisms (ETag caching, SQLite state tracking)

2. **No Existing PR Automation**: All agent/skill improvements are currently manual. The "agent-manager" is a CLI tool, not an autonomous agent.

3. **Clear Architecture**: Separation between cache (`~/.claude-mpm/cache/`) and deployment (`~/.claude/agents/`) enables safe modifications.

4. **Skills Have Better Infrastructure**: Manifest.json, parallel downloads, multi-source support. Agents could benefit from similar patterns.

5. **Authentication is Solvable**: GitHub CLI provides best UX, token fallback ensures reliability.

### Recommended Next Steps

1. **Week 1**: Build git operations and PR template services
2. **Week 2**: Implement agent-improver agent
3. **Week 3**: Implement skills-manager agent
4. **Week 4**: Integration testing and documentation

### Success Metrics

- **Adoption**: >50% of agent improvements come via PR workflow
- **Quality**: >80% of automated PRs approved with minimal changes
- **Efficiency**: PR creation time <30 seconds from detection to submission
- **Reliability**: <5% PR creation failure rate
- **User Satisfaction**: Positive feedback on streamlined contribution process

---

## Appendix A: Example PR Descriptions

### Agent Improvement PR

```markdown
## Problem Statement

The research agent frequently runs out of memory when analyzing codebases with >50 files. Users report Claude Code becoming unresponsive during research tasks.

## Root Cause

Research agent instructions don't enforce hard limits on file reading. The current guidance says "strategically sample" but doesn't specify maximum file counts.

## Proposed Solution

Add explicit memory management rules to research agent:
- Hard limit: Maximum 5 files per research session
- Mandatory MCP document summarizer for files >20KB
- Sequential processing pattern (no batching)
- Clear warnings when approaching limits

## Changes Made

**File:** `agents/universal/research.md`

```diff
+**Memory Management Excellence:**
+
+You will maintain strict memory discipline through:
+- **Hard limit**: Maximum 5 files read per session
+- **Size threshold**: Files >20KB MUST use MCP document summarizer
+- **Sequential processing**: Never load multiple files simultaneously
```

## Testing Performed

- [x] Validated YAML frontmatter syntax
- [x] Tested research agent with 100-file codebase
- [x] Verified memory usage stays under 4GB
- [x] Confirmed no regression in research quality
- [x] Reviewed with 3 sample research tasks

## Related Issues

Closes #157 (Research agent memory exhaustion)
Relates to #142 (MCP summarizer integration)

## Checklist

- [x] Instructions are clear and unambiguous
- [x] No conflicting guidance
- [x] Follows agent architecture best practices
- [x] Tested with real-world scenarios
- [x] Documentation updated

---
🤖 Generated with Claude MPM Agent Improver
Co-Authored-By: agent-improver <noreply@anthropic.com>
```

### Skill Improvement PR

```markdown
## Skill Enhancement

**Skill:** `fastapi-testing`
**Category:** toolchains/python/frameworks/fastapi

## Motivation

FastAPI testing skill lacks guidance on async test patterns. Users working with async endpoints struggle with proper test client usage and database transaction handling.

## Improvements

1. **Async Test Client Usage**
   - Added pytest-asyncio configuration
   - Documented AsyncClient context manager usage
   - Examples for async fixture setup

2. **Database Transaction Handling**
   - Rollback patterns for test isolation
   - Async session management examples
   - Connection pooling best practices

3. **Async Fixtures**
   - Dependency override patterns
   - Mock service examples
   - Event loop management

## Changes Made

**File:** `toolchains/python/frameworks/fastapi/testing/SKILL.md`

Added new section:

```markdown
## Async Testing Patterns

### Async Test Client

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_async_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/async-endpoint")
        assert response.status_code == 200
```
```

**File:** `manifest.json`

Updated token counts and version:
- `entry_point_tokens`: 120 → 145
- `full_tokens`: 850 → 1200
- `version`: 1.0.0 → 1.1.0

## Examples Added

- [x] pytest-asyncio configuration
- [x] AsyncClient usage with context manager
- [x] Database transaction rollback pattern
- [x] Async fixture dependency override
- [x] Event loop management

## Testing

- [x] Validated YAML frontmatter
- [x] Regenerated manifest.json
- [x] Verified token counts accurate
- [x] Tested examples in FastAPI project
- [x] No conflicts with existing skills

## Related Issues

Requested by: Issue #203 (FastAPI async testing guidance)

---
🤖 Generated with Claude MPM Skills Manager
Co-Authored-By: skills-manager <noreply@anthropic.com>
```

---

## Appendix B: Technology Stack to Skills Mapping

### Python Stack Detection

**Detection Files:**
- `pyproject.toml`
- `requirements.txt`
- `setup.py`
- `Pipfile`

**Mappings:**
```python
PYTHON_STACK_SKILLS = {
    "fastapi": ["fastapi-testing", "fastapi-async", "pydantic-validation"],
    "django": ["django-orm", "django-testing", "django-rest-framework"],
    "flask": ["flask-blueprints", "flask-testing"],
    "pytest": ["test-driven-development", "pytest-fixtures"],
    "sqlalchemy": ["sqlalchemy-orm", "database-migrations"],
    "celery": ["async-task-queues", "celery-monitoring"],
    "pandas": ["data-analysis", "dataframe-operations"],
}
```

### JavaScript/TypeScript Stack

**Detection Files:**
- `package.json`
- `tsconfig.json`

**Mappings:**
```python
JS_STACK_SKILLS = {
    "react": ["react-hooks", "react-testing-library", "jsx-patterns"],
    "nextjs": ["nextjs-routing", "nextjs-api-routes", "react-server-components"],
    "express": ["express-middleware", "rest-api-design"],
    "jest": ["jest-testing", "test-driven-development"],
    "typescript": ["typescript-generics", "typescript-strict-mode"],
}
```

### Infrastructure Stack

**Detection Files:**
- `Dockerfile`
- `.github/workflows/*.yml`
- `terraform/*.tf`

**Mappings:**
```python
INFRA_STACK_SKILLS = {
    "docker": ["docker-workflow", "container-optimization"],
    "github-actions": ["ci-cd-pipeline", "github-actions-patterns"],
    "terraform": ["infrastructure-as-code", "terraform-modules"],
    "kubernetes": ["k8s-deployment", "k8s-monitoring"],
}
```

---

**End of Research Document**
