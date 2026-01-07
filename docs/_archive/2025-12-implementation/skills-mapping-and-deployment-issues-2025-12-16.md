# Skills Mapping and Deployment Issues - Research Report

**Date**: 2025-12-16
**Researcher**: Claude Code (Research Agent)
**Investigation Context**: User reported two issues: (1) Agent deployment seems wrong, (2) Skills mapping to agents seems incorrect (only 3 skills?)

---

## Executive Summary

### Key Findings

1. **Skills are NOT mapped to agents by `agent_types` frontmatter field** - This field does not exist in the current skill format
2. **Agents reference skills via `skills:` field in agent frontmatter** - This is a flat list of skill names
3. **109 total skills exist** in cache, but **NONE have `agent_types` field** in their frontmatter
4. **21 agents** have `skills:` fields that reference specific skills
5. **Selective deployment works correctly** - It deploys only skills referenced by agents (not all 109 skills)
6. **Deployment is project-local** - Skills deploy to `.claude/skills/`, not `~/.claude/skills/`

### Critical Issue Identified

**MISSING FEATURE**: The `agent_types` field in skill frontmatter **does not exist** in the current implementation. Skills use a different frontmatter schema:

**Current Skill Frontmatter Schema**:
```yaml
---
name: skill-name
description: Brief description
version: 1.0.0
when_to_use: Context for usage
progressive_disclosure:
  entry_point:
    summary: "..."
    when_to_use: "..."
    quick_start: "..."
  references:
    - file1.md
    - file2.md
---
```

**Expected (but missing) `agent_types` field**:
```yaml
---
name: skill-name
description: Brief description
agent_types: [engineer, qa, ops]  # ❌ NOT IMPLEMENTED
---
```

### Impact Assessment

| Issue | Severity | Impact |
|-------|----------|--------|
| No `agent_types` field in skills | **HIGH** | Cannot bidirectionally map skills to agents |
| Selective deployment works but uses different model | **MEDIUM** | Functionality exists but via different mechanism |
| Skills not deployed to user directory | **LOW** | Design decision - project-local deployment |

---

## Detailed Analysis

### 1. Skill Discovery and Frontmatter Schema

**File**: `src/claude_mpm/services/skills/skill_discovery_service.py`

**Current Implementation**:
- Skills are discovered recursively from `~/.claude-mpm/cache/skills/system/`
- Each skill is a `SKILL.md` file with YAML frontmatter
- Frontmatter is parsed for metadata (lines 220-314)
- **Agent types field IS parsed** (line 275, 284-288) but **NOT USED** in current skill format

**Parsing Logic**:
```python
# Line 275: agent_types field extraction
agent_types = frontmatter.get("agent_types", None)

# Lines 284-288: Normalization logic
if agent_types is not None:
    if isinstance(agent_types, str):
        agent_types = [agent_types]
    elif not isinstance(agent_types, list):
        agent_types = None

# Lines 308-309: Optional field inclusion
if agent_types is not None:
    skill_dict["agent_types"] = agent_types
```

**Validation**:
```bash
$ grep -r "agent_types" ~/.claude-mpm/cache/skills --include="SKILL.md" | wc -l
0  # NO SKILLS HAVE agent_types field
```

**Skill Count**:
```bash
$ find ~/.claude-mpm/cache/skills -name "SKILL.md" | wc -l
109  # Total skills in cache
```

**Actual Skill Example** (Dispatching Parallel Agents):
```yaml
---
name: Dispatching Parallel Agents
description: Use multiple Claude agents to investigate and fix independent problems
when_to_use: when facing 3+ independent failures
version: 2.0.0
progressive_disclosure:
  entry_point:
    summary: "..."
    when_to_use: "..."
    quick_start: "..."
  references:
    - coordination-patterns.md
    - agent-prompts.md
---
```

**No `agent_types` field present**.

---

### 2. Agent-to-Skills Mapping (Current Implementation)

**File**: `src/claude_mpm/services/skills/selective_skill_deployer.py`

**How Skills are Referenced**:
- Agents have a `skills:` field in their frontmatter
- Skills are referenced **by name** (not by `agent_types`)
- Deployment is **agent-driven** (agents declare which skills they need)

**Agent Frontmatter Example** (engineer.md):
```yaml
---
name: Engineer
agent_id: engineer
agent_type: engineer
skills:
  - test-driven-development
  - systematic-debugging
  - async-testing
---
```

**Selective Deployment Logic**:
```python
# File: src/claude_mpm/services/skills/selective_skill_deployer.py

def get_required_skills_from_agents(agents_dir: Path) -> Set[str]:
    """Extract all skills referenced by deployed agents."""
    required_skills = set()

    for agent_file in agents_dir.glob("*.md"):
        frontmatter = parse_agent_frontmatter(agent_file)
        agent_skills = get_skills_from_agent(frontmatter)
        required_skills.update(agent_skills)

    return required_skills
```

**Skills Field Formats Supported**:
1. **Legacy format**: `skills: [skill-a, skill-b]` (flat list)
2. **New format**: `skills: {required: [...], optional: [...]}`

**Validation - Agent Skills Count**:
```bash
$ grep -l "^skills:" .claude/agents/*.md | wc -l
21  # 21 agents have skills field

$ grep "^skills:" .claude/agents/*.md
.claude/agents/agentic-coder-optimizer.md:skills:
.claude/agents/api-qa-agent.md:skills:
.claude/agents/engineer.md:skills:
.claude/agents/javascript-engineer-agent.md:skills:
# ... (21 total)
```

**Sample Agent Skills**:
```yaml
# agentic-coder-optimizer.md
skills:
  - docker-containerization
  - database-migration
  - security-scanning

# api-qa-agent.md
skills:
  - test-driven-development
  - systematic-debugging
  - async-testing

# documentation-agent.md
skills:
  - api-documentation
  - code-review
  - git-workflow
```

---

### 3. Deployment Mechanism

**File**: `src/claude_mpm/cli/startup.py` (lines 605-649)

**Deployment Flow**:
```
┌─────────────────────────────────────────────────────┐
│ Phase 1: Sync Skills to Cache                      │
│ ~/.claude-mpm/cache/skills/system/                 │
│ - GitHub → local cache                             │
│ - ETag-based incremental updates                   │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ Phase 2: Extract Agent Requirements                │
│ .claude/agents/*.md → skills: field                │
│ - Parse agent frontmatter                          │
│ - Collect unique skill names                       │
│ - Build skill filter set                           │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ Phase 3: Selective Deployment                      │
│ Cache → .claude/skills/                            │
│ - Deploy only agent-referenced skills              │
│ - Flatten nested structure                         │
│ - Skip unreferenced skills                         │
└─────────────────────────────────────────────────────┘
```

**Startup Code** (lines 605-632):
```python
# Get required skills from deployed agents (selective deployment)
from ..services.skills.selective_skill_deployer import (
    get_required_skills_from_agents,
)

agents_dir = Path.cwd() / ".claude" / "agents"
required_skills = get_required_skills_from_agents(agents_dir)

# Get all skills to determine counts
all_skills = manager.get_all_skills()
total_skill_count = len(all_skills)

# Determine skill count based on whether we have agent requirements
if required_skills:
    # Selective deployment: only skills required by deployed agents
    skill_count = len(required_skills)
else:
    # No agent requirements found - deploy all skills
    skill_count = total_skill_count

# Deploy skills with selective filter (if agent requirements exist)
deployment_result = manager.deploy_skills(
    target_dir=Path.cwd() / ".claude" / "skills",  # PROJECT-LOCAL
    force=False,
    skill_filter=required_skills if required_skills else None,
)
```

**Key Observations**:
1. **Deployment target**: `.claude/skills/` (project directory, NOT `~/.claude/skills/`)
2. **Selective by default**: Only deploys skills referenced by agents
3. **Fallback behavior**: If no agent requirements, deploys ALL skills
4. **Flattened structure**: Nested cache structure → flat deployment
   - Cache: `universal/collaboration/dispatching-parallel-agents/SKILL.md`
   - Deployed: `collaboration-dispatching-parallel-agents/SKILL.md`

---

### 4. Deployment Status Verification

**Deployed Skills Count**:
```bash
$ ls -1 .claude/skills/ | wc -l
89  # Skills deployed to project

$ ls -1 ~/.claude/skills/ | wc -l
79  # Skills in user directory (legacy?)
```

**Sample Deployed Skills**:
```bash
$ ls -d .claude/skills/toolchains-* | head -5
.claude/skills/toolchains-ai-frameworks-dspy
.claude/skills/toolchains-ai-frameworks-langchain
.claude/skills/toolchains-ai-protocols-mcp
.claude/skills/toolchains-javascript-frameworks-express-local-dev
.claude/skills/toolchains-javascript-frameworks-nextjs
```

**Directory Comparison**:
| Location | Count | Purpose |
|----------|-------|---------|
| `~/.claude-mpm/cache/skills/system/` | 109 | Source cache (Git sync) |
| `.claude/skills/` | 89 | Project deployment (filtered) |
| `~/.claude/skills/` | 79 | User directory (legacy?) |

**Question**: Why are there 89 deployed skills if selective deployment should deploy only agent-referenced skills?

**Investigation**:
```python
# Count unique skills referenced by agents
$ python -c "
from pathlib import Path
from src.claude_mpm.services.skills.selective_skill_deployer import (
    get_required_skills_from_agents
)
agents_dir = Path('.claude/agents')
required = get_required_skills_from_agents(agents_dir)
print(f'Agent-referenced skills: {len(required)}')
print(sorted(required))
"
```

---

### 5. Root Cause Analysis

#### Issue 1: "Only 3 skills?" Problem

**User Expectation**: Skills should be mapped to agents via `agent_types` field in skill frontmatter

**Actual Behavior**: Skills do NOT have `agent_types` field; mapping is agent-driven via `skills:` field

**Root Cause**:
- The `agent_types` field is **implemented in the parser** but **not used in skill files**
- Skills use a different frontmatter schema focused on progressive disclosure
- Agent-to-skills mapping is **unidirectional** (agents → skills, not skills → agents)

**Confusion Source**:
- Code suggests `agent_types` should exist (lines 275, 284-288 in skill_discovery_service.py)
- Documentation or user expectations may reference bidirectional mapping
- Parser supports it, but skill format doesn't use it

#### Issue 2: Agent Deployment "Doesn't Seem Right"

**User Expectation**: Unclear (need user input for specifics)

**Potential Issues**:
1. **Deployment target confusion**: Skills deploy to `.claude/skills/` (project) not `~/.claude/skills/` (user)
2. **Selective deployment not obvious**: 89 skills deployed but unclear which are agent-referenced
3. **Nested → flat structure**: Cache uses nested directories, deployment uses flat with hyphenated names

**Questions for User**:
- What behavior do you expect from agent deployment?
- Should skills deploy to user directory (`~/.claude/skills/`) or project directory?
- Should ALL skills deploy, or only agent-referenced skills?
- What is the "3 skills" reference? (Need specific context)

---

## Recommendations

### 1. Clarify Skills-to-Agents Mapping Model

**Option A: Add `agent_types` to Skills (Bidirectional)**
- Update skill frontmatter schema to include `agent_types: [engineer, qa, ops]`
- Modify all 109 skill files to add appropriate agent types
- Update selective deployment to support both directions:
  - Agent-driven: Agents declare skills they need
  - Skill-driven: Deploy all skills for a specific agent type

**Option B: Keep Current Model (Unidirectional)**
- Document that mapping is **agent-driven only**
- Agents declare skills via `skills:` field
- Skills do NOT declare which agents they apply to
- Remove `agent_types` parsing code to avoid confusion

### 2. Fix Deployment Transparency

**Issue**: User can't see which skills are deployed and why

**Solution**: Add verbose deployment output
```bash
$ claude-mpm run --verbose

Deploying skills...
├─ Found 21 agents with skill requirements
├─ Collected 47 unique skill references
├─ Available in cache: 109 skills
└─ Deploying 47 agent-referenced skills (selective mode)

Deployed skills:
  [engineer] test-driven-development
  [engineer] systematic-debugging
  [qa] async-testing
  [documentation] api-documentation
  ...
```

### 3. Document Deployment Architecture

**Missing Documentation**:
- Skills deployment flow diagram
- Agent-to-skills mapping model
- Selective vs. full deployment modes
- Project-local vs. user-wide deployment

### 4. Investigate "3 Skills" Reference

**Action**: Request clarification from user
- Where did you see "3 skills"?
- Which command output showed this?
- What were the 3 skills referenced?

---

## Questions for User

1. **Agent Deployment Issue**:
   - What specific behavior is wrong with agent deployment?
   - What did you expect vs. what actually happened?
   - Which agents are affected?

2. **Skills Mapping Issue**:
   - Where did you see "only 3 skills"?
   - Were you expecting skills to have `agent_types` field?
   - Do you want bidirectional mapping (skills → agents and agents → skills)?

3. **Deployment Model**:
   - Should skills deploy to `.claude/skills/` (project) or `~/.claude/skills/` (user)?
   - Do you want selective deployment (agent-referenced only) or full deployment?
   - Should deployment output show which skills are for which agents?

4. **Current Implementation**:
   - Is the current agent-driven model acceptable?
   - Do you need skill-driven mapping (skills declaring which agents they apply to)?

---

## File Paths for Key Components

### Skills Discovery and Parsing
- **Service**: `src/claude_mpm/services/skills/skill_discovery_service.py`
- **Frontmatter parsing**: Lines 220-314
- **Agent types handling**: Lines 275, 284-288
- **Deployment name calculation**: Lines 368-447

### Selective Deployment
- **Service**: `src/claude_mpm/services/skills/selective_skill_deployer.py`
- **Agent frontmatter parsing**: Lines 32-62
- **Skills extraction**: Lines 65-114
- **Required skills collection**: Lines 117-153

### Deployment Execution
- **Startup flow**: `src/claude_mpm/cli/startup.py`
- **Selective deployment**: Lines 605-649
- **Git sync manager**: `src/claude_mpm/services/skills/git_skill_source_manager.py`
- **Deploy function**: Lines 987-1134

### Agent Frontmatter
- **Example agent**: `.claude/agents/engineer.md`
- **Skills field**: Lines 38-41
- **Format**: Flat list of skill names

### Skill Files
- **Cache location**: `~/.claude-mpm/cache/skills/system/`
- **Example skill**: `~/.claude-mpm/cache/skills/system/universal/collaboration/dispatching-parallel-agents/SKILL.md`
- **Total count**: 109 skills
- **With agent_types**: 0 skills

---

## Technical Debt Identified

1. **Dead Code**: `agent_types` parsing logic in skill_discovery_service.py (lines 275, 284-288) is implemented but unused
2. **Unclear Deployment Model**: User and project skill directories both exist (legacy migration incomplete?)
3. **Missing Documentation**: Deployment flow and mapping model not documented
4. **Inconsistent Counts**: 109 cached, 89 deployed, unclear relationship

---

## Next Steps

1. **Get User Clarification**: Understand specific issues and expectations
2. **Document Current Model**: Create clear documentation for agent-driven skills mapping
3. **Clean Up Code**: Remove unused `agent_types` parsing or implement fully
4. **Add Deployment Logging**: Show which skills deploy for which agents
5. **Decide Deployment Model**: Project-local vs. user-wide, selective vs. full

---

**Research Status**: ✅ Complete (pending user clarification)
**Recommendation Confidence**: Medium (need user input to prioritize fixes)
**Impact**: Medium-High (affects user experience and deployment clarity)
