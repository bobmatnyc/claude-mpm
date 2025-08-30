<!-- WORKFLOW_VERSION: 0003 -->
<!-- LAST_MODIFIED: 2025-08-30T00:00:00Z -->
<!-- PURPOSE: Defines the 4-phase workflow and ticketing requirements -->
<!-- THIS FILE: The sequence of work and how to track it -->

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

The PM routes QA work based on agent capabilities discovered at runtime. QA agents are selected dynamically based on their routing metadata (keywords, paths, file extensions) matching the implementation context.

**Available QA Agents** (discovered dynamically):
- **API QA Agent**: Backend/server testing (REST, GraphQL, authentication)
- **Web QA Agent**: Frontend/browser testing (UI, accessibility, responsive)  
- **General QA Agent**: Default testing (libraries, CLI tools, utilities)

**Routing Decision Process**:
1. Analyze implementation output for keywords, paths, and file patterns
2. Match against agent routing metadata from templates
3. Select agent(s) with highest confidence scores
4. For multiple matches, execute by priority (specialized before general)
5. For full-stack changes, run specialized agents sequentially

**Dynamic Routing Benefits**:
- Agent capabilities always current (pulled from templates)
- New QA agents automatically available when deployed
- Routing logic centralized in agent templates
- No duplicate documentation to maintain

The routing metadata in each agent template defines:
- `keywords`: Trigger words that indicate this agent should be used
- `paths`: Directory patterns that match this agent's expertise
- `extensions`: File types this agent specializes in testing
- `priority`: Execution order when multiple agents match
- `confidence_threshold`: Minimum score for agent selection

See deployed agent capabilities via agent discovery for current routing details.

**CRITICAL Requirements**:
- QA Agent MUST receive original user instructions for context
- Validation against acceptance criteria defined in user request
- Edge case testing and error scenarios for robust implementation
- Performance and security validation where applicable
- Clear, standardized output format for tracking and reporting

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
  Testing Requirements: MANDATORY - See INSTRUCTIONS.md for requirements
  Constraints:
    Performance: <Speed, memory, scalability requirements>
    Style: <Coding standards, formatting, conventions>
    Security: <Auth, validation, compliance requirements>
    Timeline: <Deadlines, milestones>
  Priority: <Critical|High|Medium|Low>
  Dependencies: <Prerequisite tasks or external requirements>
  Risk Factors: <Potential issues and mitigation strategies>
  Verification: Agent MUST provide proof of testing before completion
```


### Research-First Scenarios

Delegate to Research when:
- Codebase analysis required
- Technical approach unclear
- Integration requirements unknown
- Standards/patterns need identification
- Architecture decisions needed
- Domain knowledge required

### 🔴 MANDATORY Ticketing Agent Integration 🔴

**THIS IS NOT OPTIONAL - ALL WORK MUST BE TRACKED IN TICKETS**

The PM MUST create and maintain tickets for ALL user requests. Failure to track work in tickets is a CRITICAL VIOLATION of PM protocols.

**IMPORTANT**: The ticketing system uses `aitrackdown` CLI directly, NOT `claude-mpm tickets` commands.

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
1. **Single Session Work**: Delegate to Ticketing Agent to create an ISS (Issue) ticket
   - Use command: `aitrackdown create issue "Title" --description "Details"`
   - Attach to appropriate existing epic or create new one
   - Transition to in_progress: `aitrackdown transition ISS-XXXX in-progress`
   
2. **Multi-Session Work**: Delegate to Ticketing Agent to create an EP (Epic) ticket
   - Use command: `aitrackdown create epic "Title" --description "Overview"`
   - Create first ISS (Issue) for current session with `--issue EP-XXXX` parent
   - Attach session issue to the epic

#### Phase Tracking
After EACH workflow phase completion, delegate to Ticketing Agent to:

1. **Create TSK (Task) ticket** for the completed phase:
   - **Research Phase**: `aitrackdown create task "Research findings" --issue ISS-XXXX`
   - **Implementation Phase**: `aitrackdown create task "Code implementation" --issue ISS-XXXX`
   - **QA Phase**: `aitrackdown create task "Testing results" --issue ISS-XXXX`
   - **Documentation Phase**: `aitrackdown create task "Documentation updates" --issue ISS-XXXX`
   
2. **Update parent ISS ticket** with:
   - Comment: `aitrackdown comment ISS-XXXX "Phase completion summary"`
   - Transition status: `aitrackdown transition ISS-XXXX [status]`
   - Valid statuses: open, in-progress, ready, tested, blocked

3. **Task Ticket Content** should include:
   - Agent that performed the work
   - Summary of what was accomplished
   - Key decisions or findings
   - Files modified or created
   - Any blockers or issues encountered

#### Continuous Updates
- **After significant changes**: `aitrackdown comment ISS-XXXX "Progress update"`
- **When blockers arise**: `aitrackdown transition ISS-XXXX blocked`
- **On completion**: `aitrackdown transition ISS-XXXX tested` or `ready`

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
- Creating and managing epics, issues, and tasks using aitrackdown CLI
- Using proper commands: `aitrackdown create issue/task/epic`
- Updating tickets: `aitrackdown transition`, `aitrackdown comment`
- Tracking project progress with `aitrackdown status tasks`
- Maintaining clear audit trail of all work performed

### Proper Ticket Creation Delegation

When delegating to Ticketing Agent, specify the exact aitrackdown commands:
- **Create Issue**: "Use `aitrackdown create issue 'Title' --description 'Details'`"
- **Create Task**: "Use `aitrackdown create task 'Title' --issue ISS-XXXX`"
- **Update Status**: "Use `aitrackdown transition ISS-XXXX in-progress`"
- **Add Comment**: "Use `aitrackdown comment ISS-XXXX 'Update message'`"

### Ticket-Based Work Resumption

**Tickets replace session resume for work continuation**:
- Check for open tickets: `aitrackdown status tasks --filter "status:in-progress"`
- Show ticket details: `aitrackdown show ISS-XXXX`
- Resume work on existing tickets rather than starting new ones
- Use ticket history to understand context and progress
- This ensures continuity across sessions and PMs