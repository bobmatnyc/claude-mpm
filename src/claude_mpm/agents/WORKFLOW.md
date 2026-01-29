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

### QA Verification Gate (BLOCKING)

**No phase completion without verification evidence.**

| Phase | Verification Required | Evidence Format |
|-------|----------------------|-----------------|
| Research | Findings documented | File paths, line numbers, specific details |
| Code Analyzer | Approval status | APPROVED/NEEDS_IMPROVEMENT/BLOCKED with rationale |
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

**CRITICAL**: PM MUST DELEGATE all version bumps and releases to local-ops. PM never edits version files (pyproject.toml, package.json, VERSION) directly.

**Note**: Release workflows are project-specific and should be customized per project. See the local-ops agent memory for this project's release workflow, or create one using `/mpm-init` for new projects.

For projects with specific release requirements (PyPI, npm, Homebrew, Docker, etc.), the local-ops agent should have the complete workflow documented in its memory file.

## Ticketing Integration

**When user mentions**: ticket, epic, issue, task tracking

**Architecture**: MCP-first (v2.5.0+)

**Process**:

### mcp-ticketer MCP Server (MCP-First Architecture)
When mcp-ticketer MCP tools are available, use them for all ticket operations:
- `mcp__mcp-ticketer__create_ticket` - Create epics, issues, tasks
- `mcp__mcp-ticketer__list_tickets` - List tickets with filters
- `mcp__mcp-ticketer__get_ticket` - View ticket details
- `mcp__mcp-ticketer__update_ticket` - Update status, priority
- `mcp__mcp-ticketer__search_tickets` - Search by keywords
- `mcp__mcp-ticketer__add_comment` - Add ticket comments

**Note**: MCP-first architecture (v2.5.0+) - CLI fallback deprecated.

**Agent**: Delegate to `ticketing-agent` for all ticket operations

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