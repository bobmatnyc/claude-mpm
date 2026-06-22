<!-- PURPOSE: 5-phase workflow execution details -->

# PM Workflow Configuration

## Delivery Workflow (MANDATORY)

No direct commits to `main`. Substantive work lands on `main` only via a squash-merged Pull Request. Do not bypass branch protection with `git push origin main`.

**Substantive work (feature / fix / refactor):**
`prompt → issue → branch → build/test → commit → PR → squash-merge → publish/deploy`
1. **Issue** — create/reference a GitHub issue (intent + acceptance criteria). Delegate to Ticketing / Version Control.
2. **Branch** — feature branch off latest `main` (`feat/<issue>-<slug>`, `fix/<issue>-<slug>`).
3. **Build/test** — implement; run linters + full test suite (show raw output); QA verifies the runtime artifact.
4. **Commit** — ONE FILE PER COMMIT, conventional prefixes, `Closes #N` in the functional commit body.
5. **PR** — open via Version Control agent; link the issue.
6. **Squash-merge** — after CI + QA pass; delete the branch.
7. **Publish/deploy** — release via `make release-*` (Local Ops); verify the published artifact.

**Trivial work (docs / chore / typo):** issue OPTIONAL; branch + PR still REQUIRED (never direct-to-main): `branch → commit → PR → squash-merge`.

**Exemptions (direct-to-main allowed):** release tooling only — `make release-*` version bumps and `chore: update uv.lock` commits. Nothing else.

**Branch hygiene:** delete feature branches after squash-merge; never run parallel agents on the same branch; keep `main` clean (no throwaway commits).

### Worktree Workflow (default)

When `workflow.worktree.enabled: true` (the default), all issue-linked work uses git worktrees:

```
repo/                          ← main, always at HEAD
  .claude/worktrees/
    issue-N-<slug>/            ← git worktree, issue branch
    issue-M-<other-slug>/      ← parallel branch, independent
```

**Steps:**
1. Create GitHub issue → get issue number N
2. `git worktree add .claude/worktrees/issue-N-<slug> -b feat/N-<slug>`
3. Engineer works inside `.claude/worktrees/issue-N-<slug>/`
4. Commits include `Closes #N`
5. `gh pr create` from the worktree branch
6. PR review (trusty-review gate)
7. Squash-merge → main
8. After squash-merge lands on main, run in the source dir:
   ```
   git worktree remove .claude/worktrees/issue-N-<slug>
   git branch -d feat/N-<slug>   # delete the local tracking branch
   git pull                        # advance source dir to HEAD
   ```
   Only run after confirming the squash-merge has landed on main. If the worktree has untracked files git will refuse removal — inspect with `git -C .claude/worktrees/issue-N-<slug> status` first.
   After inspecting: commit or stash any work you want to keep, then retry `git worktree remove`; or use `--force` only if you are certain the files are disposable.

**Rationale:** Source dir stays clean at HEAD; multiple agents can work on separate issues without file conflicts; consistent with the `isolation: "worktree"` pattern on Agent tool calls; eliminates stash/checkout gymnastics.

To opt out: set `workflow.worktree.enabled: false` in `.claude-mpm/config.yaml`.

## Worktree-Based Branch Workflow (CRITICAL)

Feature/fix work uses git worktrees; the PRIMARY checkout stays on the default branch (`main`/HEAD):

### Rules
1. **Per-issue worktree creation** — For each ticketed change, create an isolated worktree:
   ```bash
   git worktree add .claude/worktrees/issue-<N>-<slug> <branch>
   # Or create the branch in one step:
   git worktree add .claude/worktrees/issue-<N>-<slug> -b feat/<N>-<slug>
   ```
   Then do all build, test, commit, and push operations inside the worktree.

2. **Never switch primary checkout for feature work** — Do NOT check out a feature branch in the primary working tree; this causes stash/WIP contention with concurrent agents. When creating a new branch, always create it in a worktree (using `-b` flag above).

3. **No concurrent branch mutations in one tree** — Never run two branch-mutating git operations concurrently in the same working tree (primary or worktree). Serialization prevents ref conflicts.

4. **Parallel agents use worktree isolation** — When delegating to multiple agents that mutate files, each must use its own worktree. File mutations must never be concurrent in the same tree.

5. **Cleanup after merge** — After the feature branch is squash-merged to `main`, remove the worktree from the source dir:
   ```bash
   git worktree remove .claude/worktrees/issue-<N>-<slug>
   git branch -d feat/<N>-<slug>   # delete local tracking branch
   git pull                        # advance source dir to HEAD
   ```
   Only run after confirming squash-merge has landed on main. If the worktree has untracked files, inspect with `git -C .claude/worktrees/issue-<N>-<slug> status` first; commit or stash anything you want to keep, then retry removal (or use `--force` only if files are disposable).

6. **Long-running / background builds MUST commit incrementally** — A background or long-running agent (especially `run_in_background: true` in an isolated worktree) must make a WIP commit as each self-contained layer/component lands, NOT one all-or-nothing commit at the end. Uncommitted work in an ephemeral isolated worktree exists only as loose files on disk; if the session ends, pauses, or the agent is killed, the worktree is torn down and any uncommitted files are lost permanently (committed objects, by contrast, survive as dangling commits recoverable via `git fsck`). Commit early, commit often — each layer gets its own `wip:` or conventional commit so progress is durable in git's object database. Squash into clean conventional commits at PR time.

### Rationale
- **Eliminates checkout contention**: No competing branch switches in the primary tree
- **Enables safe parallelism**: Multiple agents work on separate issues without file-system conflicts
- **Consistent with isolation patterns**: Aligns with the `isolation: "worktree"` pattern on Agent tool calls
- **Keeps stable HEAD**: Primary tree always points to `main` for reliable reference pulls and deployments
- **Durable progress**: Incremental commits survive session end; uncommitted worktree files do not

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

## Ticket Progress & Failure Updates (MANDATORY)

When work is associated with a ticket or GitHub issue (issue number, PROJ-123, or issue/PR URL), the PM MUST post progress updates to that ticket as work progresses — not only at completion:

- **On start**: Post plan, scope, and approach to the ticket
- **At each phase/milestone**: Post when research, code analysis, implementation, or QA completes
- **On ANY failure/blocker/course-correction**: State what failed, impact, and remediation plan promptly
- **At completion**: Post summary, PR link, and merge status

**Rationale**: Ticket visibility prevents stakeholder surprises; failures are reported promptly and recorded for retrospectives.

**Delegation**: All ticket comment operations (including failure reports) are delegated to the Ticketing agent or Version Control for GitHub PR/issue comments. The PM never calls ticketing/gh MCP tools directly.

## Ticketing Integration

**When user mentions**: ticket, epic, issue, task tracking

**Process**: Delegate ALL ticket operations to `Ticketing`. PM never calls `mcp__mcp-ticketer__*` tools directly (Prohibition P7 / CB#6).

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