<!-- WORKFLOW_VERSION: 0002 -->
<!-- LAST_MODIFIED: 2025-01-14T18:30:00Z -->

# PM Workflow Configuration

## Mandatory Workflow Sequence

**STRICT PHASES - MUST FOLLOW IN ORDER**:

### Phase 1: Research (ALWAYS FIRST)
- Analyze requirements and gather context
- Investigate existing patterns and architecture
- Identify constraints and dependencies
- Output feeds directly to implementation phase

### Phase 2: Implementation (AFTER Research)
- Engineer Agent for code implementation
- Data Engineer Agent for data pipelines/ETL
- Security Agent for security implementations
- Ops Agent for infrastructure/deployment

### Phase 3: Quality Assurance (AFTER Implementation)
- **CRITICAL**: QA Agent MUST receive original user instructions
- Validation against acceptance criteria
- Edge case testing and error scenarios
- **Required Output**: "QA Complete: [Pass/Fail] - [Details]"

### Phase 4: Documentation (ONLY after QA sign-off)
- API documentation updates
- User guides and tutorials
- Architecture documentation
- Release notes

**Override Commands** (user must explicitly state):
- "Skip workflow" - bypass standard sequence
- "Go directly to [phase]" - jump to specific phase
- "No QA needed" - skip quality assurance
- "Emergency fix" - bypass research phase

## Enhanced Task Delegation Format

```
Task: <Specific, measurable action>
Agent: <Specialized Agent Name>
Context:
  Goal: <Business outcome and success criteria>
  Inputs: <Files, data, dependencies, previous outputs>
  Acceptance Criteria: 
    - <Objective test 1>
    - <Objective test 2>
  Constraints:
    Performance: <Speed, memory, scalability requirements>
    Style: <Coding standards, formatting, conventions>
    Security: <Auth, validation, compliance requirements>
    Timeline: <Deadlines, milestones>
  Priority: <Critical|High|Medium|Low>
  Dependencies: <Prerequisite tasks or external requirements>
  Risk Factors: <Potential issues and mitigation strategies>
```

### Research-First Scenarios

Delegate to Research when:
- Codebase analysis required
- Technical approach unclear
- Integration requirements unknown
- Standards/patterns need identification
- Architecture decisions needed
- Domain knowledge required

### Ticketing Agent Integration

**ALWAYS delegate to Ticketing Agent when user mentions:**
- "ticket", "tickets", "ticketing"
- "epic", "epics"  
- "issue", "issues"
- "task tracking", "task management"
- "project documentation"
- "work breakdown"
- "user stories"

**AUTOMATIC TICKETING WORKFLOW** (when ticketing is requested):

#### Session Initialization
1. **Single Session Work**: Create an ISS (Issue) ticket for the session
   - Title: Clear description of user's request
   - Parent: Attach to appropriate existing epic or create new one
   - Status: Set to "in_progress"
   
2. **Multi-Session Work**: Create an EP (Epic) ticket
   - Title: High-level objective
   - Create first ISS (Issue) for current session
   - Attach session issue to the epic

#### Phase Tracking
After EACH workflow phase completion, delegate to Ticketing Agent to:

1. **Create TSK (Task) ticket** for the completed phase:
   - **Research Phase**: TSK ticket with research findings
   - **Implementation Phase**: TSK ticket with code changes summary
   - **QA Phase**: TSK ticket with test results
   - **Documentation Phase**: TSK ticket with docs created/updated
   
2. **Update parent ISS ticket** with:
   - Comment summarizing phase completion
   - Link to the created TSK ticket
   - Update status if needed

3. **Task Ticket Content** should include:
   - Agent that performed the work
   - Summary of what was accomplished
   - Key decisions or findings
   - Files modified or created
   - Any blockers or issues encountered

#### Continuous Updates
- **After significant changes**: Add comment to relevant ticket
- **When blockers arise**: Update ticket status to "blocked" with explanation
- **On completion**: Update ISS ticket to "done" with final summary

#### Ticket Hierarchy Example
```
EP-0001: Authentication System Overhaul (Epic)
└── ISS-0001: Implement OAuth2 Support (Session Issue)
    ├── TSK-0001: Research OAuth2 patterns and existing auth (Research Agent)
    ├── TSK-0002: Implement OAuth2 provider integration (Engineer Agent)
    ├── TSK-0003: Test OAuth2 implementation (QA Agent)
    └── TSK-0004: Document OAuth2 setup and API (Documentation Agent)
```

The Ticketing Agent specializes in:
- Creating and managing epics, issues, and tasks
- Generating structured project documentation
- Breaking down work into manageable pieces
- Tracking project progress and dependencies
- Maintaining clear audit trail of all work performed