<!-- PURPOSE: 5-phase workflow execution details -->

# PM Workflow Configuration

## Delivery Workflow (MANDATORY)

No direct commits to `main`. Substantive work lands on `main` only via a squash-merged Pull Request. Do not bypass branch protection with `git push origin main`.

**Substantive work (feature / fix / refactor):**
`prompt → issue → branch → build/test → commit → PR → squash-merge → publish/deploy`
1. **Issue** — create/reference a GitHub issue (intent + acceptance criteria). Delegate to ticketing_agent / Version Control.
2. **Branch** — feature branch off latest `main` (`feat/<issue>-<slug>`, `fix/<issue>-<slug>`).
3. **Build/test** — implement; run linters + full test suite (show raw output); QA verifies the runtime artifact.
4. **Commit** — ONE FILE PER COMMIT, conventional prefixes, `Closes #N` in the functional commit body.
5. **PR** — open via Version Control agent; link the issue.
6. **Squash-merge** — after CI + QA pass; delete the branch.
7. **Publish/deploy** — release via `make release-*` (Local Ops); verify the published artifact.

**Trivial work (docs / chore / typo):** issue OPTIONAL; branch + PR still REQUIRED (never direct-to-main): `branch → commit → PR → squash-merge`.

**Exemptions (direct-to-main allowed):** release tooling only — `make release-*` version bumps and `chore: update uv.lock` commits. Nothing else.

**Branch hygiene:** delete feature branches after squash-merge; never run parallel agents on the same branch; keep `main` clean (no throwaway commits).

## Ticket Progress & Failure Updates (MANDATORY)

When work is associated with a ticket or GitHub issue, the PM MUST post progress updates to that ticket as work progresses:

- **On start**: Post plan and scope
- **At each milestone**: Post when phases complete
- **On failure/blocker**: Report within 5 minutes with remediation plan
- **At completion**: Post summary and merge status

**Delegation**: All ticket operations are delegated to the Ticketing agent. PM never calls ticketing/gh MCP tools directly.

## Worktree-Based Branch Workflow (CRITICAL)

Feature/fix work uses git worktrees; the PRIMARY checkout stays on `main`/HEAD:

1. **Create per-issue worktree**: `git worktree add .claude/worktrees/issue-<N>-<slug> -b feat/<N>-<slug>`
2. **Never switch primary checkout for feature work** — causes stash/WIP contention; always use worktrees
3. **No concurrent branch mutations in same tree** — serialization prevents ref conflicts
4. **Parallel agents use worktree isolation** — each gets its own worktree
5. **Cleanup after merge**: `git worktree remove .claude/worktrees/issue-<N>-<slug>` (only after squash-merge lands)

**Rationale**: Eliminates checkout contention, enables safe parallelism, keeps stable HEAD.

## Mandatory 5-Phase Sequence

### Phase 1: Research (CONDITIONAL)
**Agent**: Research
**When Required**: Ambiguous requirements, multiple approaches possible, unfamiliar codebase
**Skip When**: User provides explicit command, task is simple operational (start/stop/build/test)
**Output**: Requirements, constraints, success criteria, risks
**Template**:
```
Task: Analyze requirements for [feature]
Return: Technical requirements, gaps, measurable criteria, approach
```

### Phase 2: Code Analysis Review (CONDITIONAL)
**Skip when**: Change is < 100 lines, no architectural impact, or simple operational task.
**Agent**: Code Analysis (Opus model)
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
**Agent**: API QA (APIs), Web QA (UI), qa (general)
**Requirements**: Real-world testing with evidence

**Routing**:
```python
if "API" in implementation: use "API QA"
elif "UI" in implementation: use "Web QA"
else: use qa
```

### QA Verification Gate (BLOCKING)

**No phase completion without verification evidence.**

The Target → QA Agent → Method routing table is in PM_INSTRUCTIONS.md (QA Verification Gate section).

| Phase | Verification Required | Evidence Format |
|-------|----------------------|-----------------|
| Research | Findings documented | File paths, line numbers, specific details |
| Code Analysis | Approval status | APPROVED/NEEDS_IMPROVEMENT/BLOCKED with rationale |
| Implementation | Tests pass | Test command output, pass/fail counts |
| Deployment | Service running | Health check response, process status, HTTP codes |
| QA | All criteria verified | Test results with specific evidence |

### Forbidden Phrases (All Phases)

These phrases indicate unverified claims and are NOT acceptable:
- "should work" / "should be fixed"
- "appears to be working" / "seems to work"
- "I believe it's working" / "I think it's fixed"
- "looks correct" / "looks good"
- "probably working" / "likely fixed"

### Required Evidence Format

```
Phase: [phase name]
Verification: [command/tool used]
Evidence: [actual output - not assumptions]
Status: PASSED | FAILED
```

### Example

```
Phase: Implementation
Verification: pytest tests/ -v
Evidence:
  ========================= test session starts =========================
  collected 45 items
  45 passed in 2.34s
Status: PASSED
```

### Phase 5: Documentation Agent
**Agent**: Documentation Agent
**When**: Code changes made
**Output**: Updated docs, API specs, README

## Git Security Review (Before Push)

**Mandatory before `git push`**:
1. Run `git diff origin/main HEAD`
2. Delegate to Security for credential scan
3. Block push if secrets detected

**Security Check Template**:
```
Task: Pre-push security scan
Scan for: API keys, passwords, private keys, tokens
Return: Clean or list of blocked items
```

## Publish and Release Workflow

**CRITICAL**: PM MUST DELEGATE all version bumps and releases to Local Ops. PM never edits version files (pyproject.toml, package.json, VERSION) directly.

**Note**: Release workflows are project-specific and should be customized per project. See the Local Ops agent memory for this project's release workflow, or create one using `/mpm-init` for new projects.

For projects with specific release requirements (PyPI, npm, Homebrew, Docker, etc.), the Local Ops agent should have the complete workflow documented in its memory file.

## Ticketing Integration

**When user mentions**: ticket, epic, issue, task tracking

**Process**: Delegate ALL ticket operations to `ticketing_agent`. PM never calls `mcp__mcp-ticketer__*` tools directly (Prohibition P7 / CB#6).

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