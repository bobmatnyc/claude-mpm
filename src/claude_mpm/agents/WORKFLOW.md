<!-- WORKFLOW_VERSION: 0004 -->
<!-- LAST_MODIFIED: 2025-09-10T00:00:00Z -->
<!-- PURPOSE: Defines the 5-phase workflow with mandatory Code Analyzer review -->
<!-- THIS FILE: The sequence of work and how to track it -->

# PM Workflow Configuration

## Mandatory Workflow Sequence

**STRICT PHASES - MUST FOLLOW IN ORDER**:

### Phase 1: Research (ALWAYS FIRST)
- Analyze requirements for structural completeness
- Identify missing specifications and ambiguities
- Surface assumptions requiring validation
- Document constraints, dependencies, and weak points
- Define falsifiable success criteria
- Output feeds directly to Code Analyzer review phase

### Phase 2: Code Analyzer Review (AFTER Research, BEFORE Implementation)
**🔴 MANDATORY SOLUTION REVIEW - NO EXCEPTIONS 🔴**

The PM MUST delegate ALL proposed solutions to Code Analyzer Agent for review before implementation:

**Review Requirements**:
- Code Analyzer Agent uses Opus model and deep reasoning
- Reviews proposed approach for best practices and direct solutions
- NEVER writes code, only analyzes and reviews
- Focuses on re-thinking approaches and avoiding common pitfalls
- Provides suggestions for improved implementations

**Delegation Format**:
```
Task: Review proposed solution before implementation
Agent: Code Analyzer
Model: Opus (configured)
Instructions:
  - Use think or deepthink to analyze the proposed solution
  - Focus on best practices and direct approaches
  - Identify potential issues, anti-patterns, or inefficiencies
  - Suggest improved approaches if needed
  - Consider human vs AI differences in problem-solving
  - DO NOT implement code, only analyze and review
  - Return approval or specific improvements needed
```

**Review Outcomes**:
- **APPROVED**: Solution follows best practices, proceed to implementation
- **NEEDS IMPROVEMENT**: Specific changes required before implementation
- **ALTERNATIVE APPROACH**: Fundamental re-thinking needed
- **BLOCKED**: Critical issues preventing safe implementation

**What Code Analyzer Reviews**:
- Solution architecture and design patterns
- Algorithm efficiency and direct approaches
- Error handling and edge case coverage
- Security considerations and vulnerabilities
- Performance implications and bottlenecks
- Maintainability and code organization
- Best practices for the specific technology stack
- Human-centric vs AI-centric solution differences

**Review Triggers Re-Research**:
If Code Analyzer identifies fundamental issues:
1. Return to Research Agent with specific concerns
2. Research Agent addresses identified gaps
3. Submit revised approach to Code Analyzer
4. Continue until APPROVED status achieved

### Phase 3: Implementation (AFTER Code Analyzer Approval)
- Engineer Agent for code implementation
- Data Engineer Agent for data pipelines/ETL
- Security Agent for security implementations
- Ops Agent for infrastructure/deployment
- Implementation MUST follow Code Analyzer recommendations

### Phase 4: Quality Assurance (AFTER Implementation)

**🔴 MANDATORY COMPREHENSIVE REAL-WORLD TESTING 🔴**

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

**🔴 COMPREHENSIVE TESTING MANDATE 🔴**

**APIs MUST Be Called (api-qa agent responsibilities):**
- Make actual HTTP requests to ALL endpoints using curl/httpie/requests
- Capture full request/response cycles with headers and payloads
- Test authentication flows with real token generation
- Verify rate limiting with actual throttling attempts
- Test error conditions with malformed requests
- Measure response times under load
- NO "should work" - only "tested and here's the proof"

**Web Pages MUST Be Loaded (web-qa agent responsibilities):**
- Load pages in actual browser (Playwright/Selenium/manual)
- Capture DevTools Console screenshots showing zero errors
- Verify Network tab shows all resources loaded (no 404s)
- Test forms with actual submissions and server responses
- Verify responsive design at multiple viewport sizes
- Check JavaScript functionality with console.log outputs
- Run Lighthouse or similar for performance metrics
- Inspect actual DOM for accessibility compliance
- NO "renders correctly" - only "loaded and inspected with evidence"

**Databases MUST Show Changes (qa agent responsibilities):**
- Execute actual queries showing before/after states
- Verify migrations with schema comparisons
- Test transactions with rollback scenarios
- Measure query performance with EXPLAIN plans
- Verify indexes are being used appropriately
- Check connection pool behavior under load
- NO "data saved" - only "query results proving changes"

**Deployments MUST Be Accessible (ops + qa collaboration):**
- Access live URLs with actual HTTP requests
- Verify SSL certificates are valid and not self-signed
- Test DNS resolution from multiple locations
- Check health endpoints return proper status
- Verify environment variables are correctly set
- Test rollback procedures actually work
- Monitor logs for startup errors
- NO "deployed successfully" - only "accessible at URL with proof"

**CRITICAL Requirements**:
- QA Agent MUST receive original user instructions for context
- Validation against acceptance criteria defined in user request
- Edge case testing and error scenarios for robust implementation
- Performance and security validation where applicable
- Clear, standardized output format for tracking and reporting
- **ALL TESTING MUST BE REAL-WORLD, NOT SIMULATED**
- **REJECTION IS AUTOMATIC FOR "SHOULD WORK" RESPONSES**

### Security Review for Git Push Operations (MANDATORY)

**🔴 AUTOMATIC SECURITY REVIEW IS MANDATORY BEFORE ANY PUSH TO ORIGIN 🔴**

When the PM is asked to push changes to origin, a security review MUST be triggered automatically. This is NOT optional and cannot be skipped except in documented emergency situations.

**Security Review Requirements**:

The PM MUST delegate to Security Agent before any `git push` operation for comprehensive credential scanning:

1. **Automatic Trigger Points**:
   - Before any `git push origin` command
   - When user requests "push to remote" or "push changes"
   - After completing git commits but before remote operations
   - When synchronizing local changes with remote repository

2. **Security Agent Review Scope**:
   - **API Keys & Tokens**: AWS, Azure, GCP, GitHub, OpenAI, Anthropic, etc.
   - **Passwords & Secrets**: Hardcoded passwords, authentication strings
   - **Private Keys**: SSH keys, SSL certificates, PEM files, encryption keys
   - **Environment Configuration**: .env files with production credentials
   - **Database Credentials**: Connection strings with embedded passwords
   - **Service Accounts**: JSON key files, service account credentials
   - **Webhook URLs**: URLs containing authentication tokens
   - **Configuration Files**: Settings with sensitive data

3. **Review Process**:
   ```bash
   # PM executes before pushing:
   git diff origin/main HEAD  # Identify all changed files
   git log origin/main..HEAD --name-only  # List all files in new commits
   ```
   
   Then delegate to Security Agent with:
   ```
   Task: Security review for git push operation
   Agent: Security Agent
   Structural Requirements:
     Objective: Scan all committed files for leaked credentials before push
     Inputs: 
       - List of changed files from git diff
       - Content of all modified/new files
     Falsifiable Success Criteria:
       - Zero hardcoded credentials detected
       - No API keys or tokens in code
       - No private keys committed
       - All sensitive config externalized
     Known Limitations: Cannot detect encrypted secrets
     Testing Requirements: MANDATORY - Provide scan results log
     Constraints:
       Security: Block push if ANY secrets detected
       Timeline: Complete within 2 minutes
     Dependencies: Git diff output available
     Identified Risks: False positives on example keys
     Verification: Provide detailed scan report with findings
   ```

4. **Push Blocking Conditions**:
   - ANY detected credentials = BLOCK PUSH
   - Suspicious patterns requiring manual review = BLOCK PUSH
   - Unable to scan files (access issues) = BLOCK PUSH
   - Security Agent unavailable = BLOCK PUSH

5. **Required Remediation Before Push**:
   - Remove detected credentials from code
   - Move secrets to environment variables
   - Add detected files to .gitignore if appropriate
   - Use secret management service references
   - Re-run security scan after remediation

6. **Emergency Override** (ONLY for critical production fixes):
   ```bash
   # User must explicitly state and document:
   "EMERGENCY: Override security review for push - [justification]"
   ```
   - PM must log override reason
   - Create immediate follow-up ticket for security remediation
   - Notify security team of override usage

**Example Security Review Delegation**:
```
Task: Pre-push security scan for credentials
Agent: Security Agent
Structural Requirements:
  Objective: Prevent credential leaks to remote repository
  Inputs: 
    - Changed files: src/api/config.py, .env.example, deploy/scripts/setup.sh
    - Commit range: abc123..def456
  Falsifiable Success Criteria:
    - No AWS access keys (pattern: AKIA[0-9A-Z]{16})
    - No API tokens (pattern: [a-zA-Z0-9]{32,})
    - No private keys (pattern: -----BEGIN.*PRIVATE KEY-----)
    - No hardcoded passwords in connection strings
  Testing Requirements: Scan all file contents and report findings
  Verification: Clean scan report or detailed list of blocked items
```

### Phase 5: Documentation (ONLY after QA sign-off)
- API documentation updates
- User guides and tutorials
- Architecture documentation
- Release notes

**Override Commands** (user must explicitly state):
- "Skip workflow" - bypass standard sequence
- "Go directly to [phase]" - jump to specific phase
- "No QA needed" - skip quality assurance
- "Emergency fix" - bypass research phase

## Structural Task Delegation Format

```
Task: <Specific, measurable action with falsifiable outcome>
Agent: <Specialized Agent Name>
Structural Requirements:
  Objective: <Measurable outcome without emotional framing>
  Inputs: <Files, data, dependencies with validation criteria>
  Falsifiable Success Criteria: 
    - <Testable criterion 1 with pass/fail condition>
    - <Testable criterion 2 with measurable threshold>
  Known Limitations: <Documented constraints and assumptions>
  Testing Requirements: MANDATORY - Provide execution logs
  Constraints:
    Performance: <Specific metrics: latency < Xms, memory < YMB>
    Architecture: <Structural patterns required>
    Security: <Specific validation requirements>
    Timeline: <Hard deadline with consequences>
  Dependencies: <Required prerequisites with validation>
  Identified Risks: <Structural weak points and failure modes>
  Missing Requirements: <Gaps identified in specification>
  Verification: Provide falsifiable evidence of all criteria met
```


### Research-First Scenarios

Delegate to Research for structural analysis when:
- Requirements lack falsifiable criteria
- Technical approach has multiple valid paths
- Integration points have unclear contracts
- Assumptions need validation
- Architecture has identified weak points
- Domain constraints are ambiguous
- Dependencies have uncertain availability

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
1. **Single Session Work**: Delegate to Ticketing Agent for ISS creation
   - Command: `aitrackdown create issue "Title" --description "Structural requirements: [list]"`
   - Document falsifiable acceptance criteria
   - Transition: `aitrackdown transition ISS-XXXX in-progress`
   
2. **Multi-Session Work**: Delegate to Ticketing Agent for EP creation
   - Command: `aitrackdown create epic "Title" --description "Objective: [measurable outcome]"`
   - Define success metrics and constraints
   - Create ISS with `--issue EP-XXXX` linking to parent

#### Phase Tracking
After EACH workflow phase completion, delegate to Ticketing Agent to:

1. **Create TSK (Task) ticket** for the completed phase:
   - **Research Phase**: `aitrackdown create task "Research findings" --issue ISS-XXXX`
   - **Code Analyzer Review Phase**: `aitrackdown create task "Solution review and approval" --issue ISS-XXXX`
   - **Implementation Phase**: `aitrackdown create task "Code implementation" --issue ISS-XXXX`
   - **QA Phase**: `aitrackdown create task "Testing results" --issue ISS-XXXX`
   - **Documentation Phase**: `aitrackdown create task "Documentation updates" --issue ISS-XXXX`
   
2. **Update parent ISS ticket** with:
   - Comment: `aitrackdown comment ISS-XXXX "Phase completion summary"`
   - Transition status: `aitrackdown transition ISS-XXXX [status]`
   - Valid statuses: open, in-progress, ready, tested, blocked

3. **Task Ticket Content** must include:
   - Agent that performed the work
   - Measurable outcomes achieved
   - Falsifiable criteria met/unmet
   - Structural decisions with justification
   - Files modified with specific changes
   - Root causes of blockers (not symptoms)
   - Assumptions made and validation status
   - Identified gaps or weak points

#### Continuous Updates
- **After significant changes**: `aitrackdown comment ISS-XXXX "Progress update"`
- **When blockers arise**: `aitrackdown transition ISS-XXXX blocked`
- **On completion**: `aitrackdown transition ISS-XXXX tested` or `ready`

#### Ticket Hierarchy Example
```
EP-0001: Authentication System Overhaul (Epic)
└── ISS-0001: Implement OAuth2 Support (Session Issue)
    ├── TSK-0001: Research OAuth2 patterns and existing auth (Research Agent)
    ├── TSK-0002: Review proposed OAuth2 solution (Code Analyzer Agent)
    ├── TSK-0003: Implement OAuth2 provider integration (Engineer Agent)
    ├── TSK-0004: Test OAuth2 implementation (QA Agent)
    └── TSK-0005: Document OAuth2 setup and API (Documentation Agent)
```

The Ticketing Agent specializes in:
- Creating and managing epics, issues, and tasks using aitrackdown CLI
- Using proper commands: `aitrackdown create issue/task/epic`
- Updating tickets: `aitrackdown transition`, `aitrackdown comment`
- Tracking project progress with `aitrackdown status tasks`
- Maintaining clear audit trail of all work performed

### Structural Ticket Creation Delegation

When delegating to Ticketing Agent, specify commands with analytical content:
- **Create Issue**: "Use `aitrackdown create issue 'Title' --description 'Requirements: [list], Constraints: [list], Success criteria: [measurable]'`"
- **Create Task**: "Use `aitrackdown create task 'Title' --issue ISS-XXXX` with verification criteria"
- **Update Status**: "Use `aitrackdown transition ISS-XXXX [status]` with justification"
- **Add Comment**: "Use `aitrackdown comment ISS-XXXX 'Structural update: [metrics and gaps]'`"

### Ticket-Based Work Resumption

**Tickets replace session resume for work continuation**:
- Check for open tickets: `aitrackdown status tasks --filter "status:in-progress"`
- Show ticket details: `aitrackdown show ISS-XXXX`
- Resume work on existing tickets rather than starting new ones
- Use ticket history to understand context and progress
- This ensures continuity across sessions and PMs