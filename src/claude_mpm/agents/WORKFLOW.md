<!-- PURPOSE: 5-phase workflow execution details -->

# PM Workflow Configuration

## Mandatory 5-Phase Sequence

### Phase 1: Research (ALWAYS FIRST)
**Agent**: Research
**Output**: Requirements, constraints, success criteria, risks
**Template**:
```
Task: Analyze requirements for [feature]
Return: Technical requirements, gaps, measurable criteria, approach
```

### Phase 2: Code Analyzer Review (MANDATORY)
**Agent**: Code Analyzer (Opus model)
**Output**: APPROVED/NEEDS_IMPROVEMENT/BLOCKED
**Template**:
```
Task: Review proposed solution
Use: think/deepthink for analysis
Return: Approval status with specific recommendations
```

**Decision**:
- APPROVED → Implementation
- NEEDS_IMPROVEMENT → Back to Research
- BLOCKED → Escalate to user

### Phase 3: Implementation
**Agent**: Selected via delegation matrix
**Requirements**: Complete code, error handling, basic test proof

### Phase 4: QA (MANDATORY)
**Agent**: api-qa (APIs), web-qa (UI), qa (general)
**Requirements**: Real-world testing with evidence

**Routing**:
```python
if "API" in implementation: use api_qa
elif "UI" in implementation: use web_qa
else: use qa
```

### Phase 5: Documentation
**Agent**: Documentation
**When**: Code changes made
**Output**: Updated docs, API specs, README

## Git Security Review (Before Push)

**Mandatory before `git push`**:
1. Run `git diff origin/main HEAD`
2. Delegate to Security Agent for credential scan
3. Block push if secrets detected

**Security Check Template**:
```
Task: Pre-push security scan
Scan for: API keys, passwords, private keys, tokens
Return: Clean or list of blocked items
```

## Publish and Release Workflow

**Trigger Keywords**: "publish", "release", "deploy to PyPI/npm", "create release", "tag version"

**Agent Responsibility**: Ops (local-ops or platform-specific)

**Mandatory Requirements**: All changes committed, quality gates passed, security scan complete, version incremented

### Process Overview

Publishing and releasing is a **multi-step orchestrated workflow** requiring coordination across multiple agents with mandatory verification at each stage. The PM NEVER executes release commands directly - this is ALWAYS delegated to the appropriate Ops agent.

### Workflow Phases

#### Phase 1: Pre-Release Validation (Research + QA)

**Agent**: Research
**Purpose**: Validate readiness for release
**Template**:
```
Task: Pre-release readiness check
Requirements:
  - Verify all uncommitted changes are tracked
  - Check git status for untracked files
  - Validate all features documented
  - Confirm CHANGELOG updated
Success Criteria: Clean working directory, complete documentation
```

**Decision**:
- Clean → Proceed to Phase 2
- Uncommitted changes → Report to user, request commit approval
- Missing documentation → Delegate to Documentation agent

#### Phase 2: Quality Gate Validation (QA)

**Agent**: QA
**Purpose**: Execute comprehensive quality checks
**Template**:
```
Task: Run pre-publish quality gate
Requirements:
  - Execute: make pre-publish
  - Verify all linters pass (Ruff, Black, isort, Flake8)
  - Confirm test suite passes
  - Validate version consistency
  - Check for debug prints, TODO comments
Evidence Required: Complete quality gate output
```

**Decision**:
- All checks pass → Proceed to Phase 3
- Any failure → BLOCK release, report specific failures to user
- Must provide full quality gate output as evidence

#### Phase 3: Security Scan (Security Agent) - MANDATORY

**Agent**: Security
**Purpose**: Pre-push credential and secrets scan
**Template**:
```
Task: Pre-release security scan
Requirements:
  - Run git diff origin/main HEAD
  - Scan for: API keys, passwords, tokens, private keys, credentials
  - Check environment files (.env, .env.local)
  - Verify no hardcoded secrets in code
Success Criteria: CLEAN scan or BLOCKED with specific secrets identified
Evidence Required: Security scan results
```

**Decision**:
- CLEAN → Proceed to Phase 4
- SECRETS DETECTED → BLOCK release immediately, report violations
- NEVER bypass this step, even for "urgent" releases

#### Phase 4: Version Management (Ops Agent)

**Agent**: local-ops-agent
**Purpose**: Increment version following conventional commits
**Template**:
```
Task: Increment version and commit
Requirements:
  - Analyze recent commits since last release
  - Determine bump type (patch/minor/major):
    * patch: bug fixes (fix:)
    * minor: new features (feat:)
    * major: breaking changes (feat!, BREAKING CHANGE:)
  - Execute: ./scripts/manage_version.py bump {type}
  - Commit version changes with message: "chore: bump version to {version}"
  - Push to origin/main
Minimum Requirement: At least patch version bump
Success Criteria: Version incremented, committed, pushed
Evidence Required: New version number, git commit SHA
```

**Conventional Commit Detection**:
```python
if "BREAKING CHANGE:" in commits or "feat!" in commits:
    bump_type = "major"
elif "feat:" in commits:
    bump_type = "minor"
else:  # "fix:", "refactor:", "perf:", etc.
    bump_type = "patch"
```

#### Phase 5: Build and Publish (Ops Agent)

**Agent**: local-ops-agent
**Purpose**: Build release artifacts and publish to distribution channels
**Template**:
```
Task: Build and publish release
Requirements:
  - Execute: make safe-release-build (includes quality gate)
  - Publish to PyPI: make release-pypi
  - Publish to npm (if applicable): make release-npm
  - Create GitHub release: gh release create v{version}
  - Tag release in git
Verification Required:
  - Confirm build artifacts created
  - Verify PyPI upload successful (check PyPI page)
  - Verify npm upload successful (if applicable)
  - Confirm GitHub release created
Evidence Required:
  - Build logs
  - PyPI package URL
  - npm package URL (if applicable)
  - GitHub release URL
```

#### Phase 6: Post-Release Verification (Ops Agent) - MANDATORY

**Agent**: Same ops agent that published
**Purpose**: Verify release is accessible and installable
**Template**:
```
Task: Verify published release
Requirements:
  - PyPI: Test installation in clean environment
    * pip install claude-mpm=={version}
    * Verify version: claude-mpm --version
  - npm (if applicable): Test installation
    * npm install claude-mpm@{version}
    * Verify version
  - GitHub: Verify release appears in releases page
  - For hosted projects: Check deployment logs
Success Criteria: Package installable from all channels
Evidence Required: Installation output, version verification
```

**For Hosted Projects** (Vercel, Heroku, etc.):
```
Additional Verification:
  - Check platform deployment logs
  - Verify build status on platform dashboard
  - Test live deployment URL
  - Confirm no errors in server logs
Evidence: Platform logs, HTTP response, deployment status
```

### Agent Routing Matrix

| Task | Primary Agent | Fallback | Verification Agent |
|------|---------------|----------|-------------------|
| Pre-release validation | Research | - | - |
| Quality gate | QA | - | - |
| Security scan | Security | - | - |
| Version increment | local-ops-agent | Ops (generic) | local-ops-agent |
| PyPI publish | local-ops-agent | Ops (generic) | local-ops-agent |
| npm publish | local-ops-agent | Ops (generic) | local-ops-agent |
| GitHub release | local-ops-agent | Ops (generic) | local-ops-agent |
| Vercel deploy | vercel-ops-agent | - | vercel-ops-agent |
| Platform deploy | Ops (generic) | - | Ops (generic) |
| Post-release verification | Same as publisher | - | QA |

### Minimum Requirements Checklist

PM MUST verify these with agents before claiming release complete:

- [ ] All changes committed (Research verification)
- [ ] Quality gate passed (QA evidence: `make pre-publish` output)
- [ ] Security scan clean (Security evidence: scan results)
- [ ] Version incremented (Ops evidence: new version number)
- [ ] Changes pushed to origin (Ops evidence: git push output)
- [ ] Built successfully (Ops evidence: build logs)
- [ ] Published to PyPI (Ops evidence: PyPI URL)
- [ ] Published to npm if applicable (Ops evidence: npm URL)
- [ ] GitHub release created (Ops evidence: release URL)
- [ ] Installation verified (Ops evidence: pip/npm install output)
- [ ] For hosted: Deployment verified (Ops evidence: platform logs + endpoint test)

**If ANY checkbox unchecked → Release is INCOMPLETE**

## Ticketing Integration

**When user mentions**: ticket, epic, issue, task tracking

**Process**:
Use the mcp-ticketer MCP service for ticket management.
Ticketing is handled through the MCP Gateway, not internal CLI commands.

## Structural Delegation Format

```
Task: [Specific measurable action]
Agent: [Selected Agent]
Requirements:
  Objective: [Measurable outcome]
  Success Criteria: [Testable conditions]
  Testing: MANDATORY - Provide logs
  Constraints: [Performance, security, timeline]
  Verification: Evidence of criteria met
```

## Override Commands

User can explicitly state:
- "Skip workflow" - bypass sequence
- "Go directly to [phase]" - jump to phase
- "No QA needed" - skip QA (not recommended)
- "Emergency fix" - bypass research