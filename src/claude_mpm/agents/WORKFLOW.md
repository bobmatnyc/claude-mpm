<!-- WORKFLOW_VERSION: 0001 -->
<!-- LAST_MODIFIED: 2025-01-14T00:00:00Z -->

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

### Ticketing Agent Scenarios

**ALWAYS delegate to Ticketing Agent when user mentions:**
- "ticket", "tickets", "ticketing"
- "epic", "epics"  
- "issue", "issues"
- "task tracking", "task management"
- "project documentation"
- "work breakdown"
- "user stories"

The Ticketing Agent specializes in:
- Creating and managing epics, issues, and tasks
- Generating structured project documentation
- Breaking down work into manageable pieces
- Tracking project progress and dependencies