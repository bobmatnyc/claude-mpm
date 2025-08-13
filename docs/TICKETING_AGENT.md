# Ticketing Agent Documentation

## Overview

The Ticketing Agent is Claude MPM's intelligent ticket management specialist, designed to create and manage project tickets through a comprehensive Epic → Issue → Task hierarchy. It provides smart classification, workflow management, and seamless integration with ticketing tools to streamline project management workflows.

### Key Capabilities

- **Intelligent Classification**: Automatically determines whether work should be an Epic, Issue, or Task
- **Hierarchical Management**: Maintains proper relationships between Epics, Issues, and Tasks
- **Workflow Optimization**: Manages status transitions, priorities, and dependencies
- **Integration Ready**: Built to work with ai-trackdown-pytools and other ticketing systems
- **Team Coordination**: Creates tickets for other agents and tracks cross-functional work

### When to Use the Ticketing Agent

**Use the Ticketing Agent when:**
- Breaking down large initiatives into manageable work items
- Creating structured ticket hierarchies for complex projects
- Managing sprint planning and capacity allocation
- Tracking bugs, features, and technical debt systematically
- Coordinating work across multiple team members or agents
- Generating reports and tracking project progress

**Manage tickets manually when:**
- Creating single, simple tasks that don't require classification
- Making quick status updates to existing tickets
- Adding brief comments or updates to ongoing work
- Working on personal or experimental tasks outside the main project workflow

## Epic → Issue → Task Hierarchy

### Understanding the Hierarchy

The Ticketing Agent uses a three-tier hierarchy designed to organize work from strategic initiatives down to concrete implementation tasks:

```
Epic (Strategic Level)
├── Issue 1 (Feature/Problem Level)
│   ├── Task 1.1 (Implementation Level)
│   ├── Task 1.2 (Implementation Level)
│   └── Task 1.3 (Implementation Level)
├── Issue 2 (Feature/Problem Level)
│   ├── Task 2.1 (Implementation Level)
│   └── Task 2.2 (Implementation Level)
└── Issue 3 (Feature/Problem Level)
    └── Task 3.1 (Implementation Level)
```

### Hierarchy Benefits

1. **Strategic Alignment**: Epics connect daily work to business objectives
2. **Scope Management**: Issues provide bounded, deliverable units of work
3. **Task Clarity**: Tasks offer concrete, actionable work items for team members
4. **Progress Tracking**: Hierarchy enables rollup reporting from tasks to epics
5. **Dependency Management**: Clear relationships help identify blocking work

## Ticket Classification System

### Epics: Strategic Initiatives

**Definition**: Large-scale initiatives that span multiple weeks or sprints, typically requiring coordination across teams or significant architectural changes.

**When to create an Epic:**
- Major new features requiring multiple components
- System-wide refactoring or architectural changes
- Cross-team initiatives or integration projects
- Significant infrastructure improvements
- Multi-phase rollouts or migrations

**Epic Structure:**
```markdown
Title: [EPIC] Authentication System Overhaul
Description:
  Business Value: Improve security posture and user experience
  Success Criteria: 
    - 99.9% uptime for auth services
    - <200ms response times
    - Support for 50,000 concurrent users
  Scope: 
    - OAuth2 implementation
    - Multi-factor authentication
    - Session management redesign
  Timeline: Q2 2025 (12 weeks)
  Dependencies: Infrastructure team capacity, security review
```

**Epic Examples:**
- `[EPIC] Migrate from monolithic to microservices architecture`
- `[EPIC] Implement real-time collaborative editing`
- `[EPIC] Add mobile application support`
- `[EPIC] Redesign user onboarding experience`

### Issues: Specific Problems and Features

**Definition**: Discrete problems, features, or improvements that can be completed within a sprint and provide clear business value.

**Issue Types:**
- **Bug**: Defects, errors, or unexpected behavior in existing functionality
- **Feature**: New capabilities or enhancements to existing features
- **Enhancement**: Improvements to existing functionality (performance, UX, etc.)
- **Tech Debt**: Refactoring, optimization, or maintenance work
- **Investigation**: Research, spike work, or exploratory tasks

**When to create an Issue:**
- Specific bugs reported by users or discovered in testing
- Individual user stories or feature requests
- Performance optimizations for specific components
- Security vulnerabilities requiring fixes
- Technical debt in specific modules or functions

**Issue Structure:**
```markdown
Title: [Auth] Implement OAuth2 token refresh mechanism
Type: Feature
Description:
  Current Behavior: Tokens expire after 1 hour with no refresh
  Expected Behavior: Automatic token refresh with 6-hour expiry
  Acceptance Criteria:
    - [ ] Implement refresh token endpoint
    - [ ] Add client-side refresh logic
    - [ ] Handle refresh failures gracefully
    - [ ] Update token storage mechanism
  Technical Notes: Use JWT for refresh tokens, store in httpOnly cookies
Components: [backend, frontend, auth]
Priority: P1 (High)
Severity: Medium
Estimated Effort: 8 points
```

**Issue Examples:**
- `[Frontend] Login form validation errors not displaying`
- `[API] Add pagination support to user search endpoint`
- `[Database] Optimize query performance for user dashboard`
- `[Security] Fix SQL injection vulnerability in reports module`

### Tasks: Implementation Work

**Definition**: Concrete, assignable work items that represent specific implementation steps or deliverables within a larger issue.

**When to create a Task:**
- Breaking down issues into assignable work items
- Specific coding, testing, or documentation activities
- Individual team member assignments within a larger effort
- Time-boxed activities with clear start and end points
- Prerequisite work for other tickets

**Task Structure:**
```markdown
Title: [Backend] Create OAuth2 refresh token endpoint
Description:
  Objective: Implement /auth/refresh endpoint for token renewal
  Steps:
    1. Create refresh token model and database schema
    2. Implement refresh token generation and validation
    3. Create REST endpoint with proper error handling
    4. Add rate limiting and security headers
    5. Write unit and integration tests
  Deliverables:
    - Working /auth/refresh endpoint
    - Unit tests with >90% coverage
    - API documentation updated
    - Security review completed
  Estimate: 6 hours
Parent Issue: AUTH-123
Assignee: @backend-developer
Priority: P1
Status: Open
```

**Task Examples:**
- `[Frontend] Create token refresh interceptor for API calls`
- `[Testing] Write integration tests for OAuth2 flow`
- `[Docs] Update API documentation for authentication endpoints`
- `[DevOps] Configure refresh token rotation in production`

## Decision Tree for Ticket Classification

```
Is this work part of a larger strategic initiative lasting >4 weeks?
├── YES → Create or link to EPIC
└── NO ↓

Can this be completed in one sprint by one team?
├── NO → Create EPIC, break into Issues
└── YES ↓

Does this solve a complete user problem or provide standalone value?
├── YES → Create ISSUE
└── NO ↓

Is this a specific implementation step within a larger feature?
├── YES → Create TASK (link to parent Issue)
└── NO → Consider if work is necessary or needs scope clarification
```

### Classification Examples

**Scenario**: "We need to add search functionality to our application"

**Analysis**:
- Large initiative affecting multiple components
- Requires frontend UI, backend API, database indexing
- Will take 6-8 weeks across multiple sprints

**Classification**: **Epic**
```
[EPIC] Add comprehensive search functionality
├── [Issue] Design and implement search UI components
├── [Issue] Create search API with filtering and sorting
├── [Issue] Implement full-text search with Elasticsearch
└── [Issue] Add search analytics and performance monitoring
```

**Scenario**: "Login page shows generic error instead of specific validation messages"

**Analysis**:
- Specific problem affecting user experience
- Can be fixed in one sprint
- Clear acceptance criteria

**Classification**: **Issue**
```
[Issue] Fix login form validation error messages
├── [Task] Update frontend validation to show specific errors
├── [Task] Modify backend API to return detailed error codes
└── [Task] Add automated tests for error scenarios
```

**Scenario**: "Update the user model to include a last_login field"

**Analysis**:
- Specific implementation detail
- Part of larger authentication improvements
- Can be completed in a few hours

**Classification**: **Task** (should be part of a larger Issue)

## Workflow System

### Status Transitions

The Ticketing Agent manages tickets through a standardized workflow that ensures proper progress tracking and team coordination:

```
    Open → In Progress → Review → Done
         ↘              ↗    ↓
           Blocked ←------   Reopened
```

### Status Definitions

**Open**
- **Definition**: Work is ready to begin, all dependencies are resolved
- **Requirements**: Clear acceptance criteria, proper priority assignment
- **Actions**: Can be assigned to team members, moved to In Progress
- **Used for**: New tickets, unblocked work, sprint-ready items

**In Progress**
- **Definition**: Work is actively being developed or implemented
- **Requirements**: Must have assignee, should have estimated completion date
- **Actions**: Regular status updates, may be blocked or moved to review
- **Used for**: Currently active development work

**Blocked**
- **Definition**: Work cannot proceed due to external dependencies or issues
- **Requirements**: Clear blocking reason documented, blocking ticket linked
- **Actions**: Monitor blocking conditions, escalate if needed
- **Used for**: Work waiting on external dependencies, technical roadblocks

**Review**
- **Definition**: Implementation is complete and awaiting approval or testing
- **Requirements**: All deliverables completed, ready for validation
- **Actions**: Conduct code review, testing, stakeholder approval
- **Used for**: Completed work pending verification, QA testing phase

**Done**
- **Definition**: Work is fully complete, tested, and deployed
- **Requirements**: All acceptance criteria met, stakeholders approved
- **Actions**: Close related tasks, update parent tickets
- **Used for**: Successfully completed and delivered work

**Reopened**
- **Definition**: Previously completed work requires additional changes
- **Requirements**: Clear reason for reopening, new acceptance criteria if needed
- **Actions**: Investigate issues, plan additional work
- **Used for**: Bugs found in completed work, new requirements discovered

### Priority Levels

**P0 - Critical**
- **Definition**: System down, data loss, security breach, or complete feature failure
- **Response Time**: Immediate (within 1 hour)
- **Examples**: 
  - Authentication system completely broken
  - Data corruption affecting multiple users
  - Security vulnerability being actively exploited
- **Escalation**: Automatically notify on-call team and management

**P1 - High**
- **Definition**: Major feature broken, significant user impact, or blocking other work
- **Response Time**: Same day (within 8 hours)
- **Examples**:
  - Core feature unusable for all users
  - Performance degradation affecting user experience
  - Blocking dependencies for other high-priority work
- **Escalation**: Notify team lead and prioritize in current sprint

**P2 - Medium**
- **Definition**: Minor feature issue, moderate user impact, workaround available
- **Response Time**: Within current sprint (1-2 weeks)
- **Examples**:
  - Feature works but has usability issues
  - Performance issues affecting some users
  - Nice-to-have enhancements with clear business value
- **Escalation**: Standard sprint planning process

**P3 - Low**
- **Definition**: Cosmetic issues, minor enhancements, or convenience features
- **Response Time**: Next sprint or when capacity allows
- **Examples**:
  - UI polish and minor visual improvements
  - Optional features with minimal user impact
  - Technical debt that doesn't affect functionality
- **Escalation**: Backlog grooming, address when convenient

### Blocking Relationships and Dependencies

**Blocking Types:**

**Technical Dependencies**
```markdown
TASK-123 [Frontend] Create user profile form
└─ BLOCKED BY → TASK-122 [Backend] User profile API endpoint

ISSUE-456 [Mobile] App store submission
└─ BLOCKED BY → ISSUE-455 [Security] Security audit completion
```

**Resource Dependencies**
```markdown
EPIC-789 [Infrastructure] Database migration
└─ BLOCKED BY → Resource availability (DBA team capacity)

ISSUE-234 [Feature] Payment processing
└─ BLOCKED BY → External vendor API documentation
```

**Business Dependencies**
```markdown
TASK-567 [Legal] Update terms of service
└─ BLOCKED BY → Legal review completion

EPIC-890 [Product] New pricing model
└─ BLOCKED BY → Executive decision on pricing strategy
```

### Sprint Planning and Capacity Management

**Sprint Planning Process:**

1. **Epic Review**: Assess progress on active epics, identify issues ready for sprint
2. **Issue Prioritization**: Sort backlog by priority and business value
3. **Capacity Planning**: Estimate team capacity and assign appropriate work
4. **Task Breakdown**: Ensure issues have sufficient task-level detail
5. **Dependency Check**: Verify no blocking dependencies for planned work

**Capacity Management:**

```markdown
Team Capacity: 40 story points per sprint
Current Sprint Allocation:
├── P0/P1 Issues: 24 points (60% - critical work)
├── P2 Issues: 12 points (30% - planned features)
├── P3 Issues: 4 points (10% - polish and tech debt)
└── Buffer: 0 points (fully allocated)

Sprint Health Check:
- ✅ No P0 items outstanding
- ⚠️  2 P1 items at risk (blocked dependencies)
- ✅ P2/P3 balance appropriate for team velocity
```

## ai-trackdown-pytools Integration

The Ticketing Agent is designed to integrate seamlessly with ai-trackdown-pytools, a Python-based toolkit for intelligent ticket management and workflow automation.

### Integration Architecture

```
Claude MPM Ticketing Agent
    ↓ (creates/manages tickets)
ai-trackdown-pytools CLI
    ↓ (synchronizes with)
External Ticketing Systems (Jira, GitHub, Azure DevOps)
    ↓ (provides data to)
Reporting and Analytics Dashboard
```

### Key Integration Features

**Intelligent Ticket Creation**
- Agent analyzes request context and automatically creates appropriately structured tickets
- Pre-fills templates with relevant project information
- Maintains consistent naming and labeling conventions

**Workflow Automation**
- Automatic status transitions based on development events (PR merged, CI passed)
- Smart assignment based on component ownership and team capacity
- Dependency detection and blocking relationship management

**Cross-System Synchronization**
- Bidirectional sync between Claude MPM and external ticketing systems
- Conflict resolution for concurrent updates
- Audit trail maintenance across all systems

### ai-trackdown-pytools Command Examples

**Epic Management:**
```bash
# Create epic with business context
trackdown epic create \
  --title "Authentication System Overhaul" \
  --description "Improve security and user experience" \
  --target-date "2025-06-01" \
  --business-value "high" \
  --components "auth,security,frontend"

# Update epic progress
trackdown epic update EPIC-123 \
  --status "in-progress" \
  --progress 35 \
  --comment "OAuth2 implementation completed, MFA in progress"

# Link issues to epic
trackdown epic link EPIC-123 \
  --issues "ISSUE-456,ISSUE-789,ISSUE-012"
```

**Issue Management:**
```bash
# Create bug report with auto-classification
trackdown issue create \
  --title "Login form validation errors not displaying" \
  --type bug \
  --severity high \
  --component frontend \
  --priority P1 \
  --auto-assign

# Update issue status with workflow validation
trackdown issue update ISSUE-456 \
  --status review \
  --assignee "@qa-team" \
  --comment "Implementation complete, ready for testing"

# Bulk update related issues
trackdown issue bulk-update \
  --query "component:auth AND status:open" \
  --set-priority P2 \
  --add-label "sprint-23"
```

**Task Management:**
```bash
# Create implementation tasks from issue
trackdown task create \
  --parent ISSUE-456 \
  --title "Update validation component to show specific errors" \
  --estimate "4h" \
  --assignee "@frontend-dev"

# Track time and update estimates
trackdown task update TASK-789 \
  --log-time "2.5h" \
  --remaining "1.5h" \
  --status "in-progress"

# Generate task checklist from requirements
trackdown task generate-checklist ISSUE-456 \
  --from-acceptance-criteria \
  --create-tasks
```

### Integration Workflow Examples

**Feature Development Workflow:**
```bash
# 1. Agent creates epic and issues
./claude-mpm run -a ticketing "Create epic for new search functionality"

# 2. Break down into implementation tasks
trackdown issue breakdown EPIC-123 \
  --create-tasks \
  --auto-assign \
  --estimate-hours

# 3. Start development workflow
trackdown workflow start ISSUE-456 \
  --notify-assignee \
  --create-branch \
  --setup-ci

# 4. Track progress automatically
trackdown workflow monitor \
  --epic EPIC-123 \
  --notify-on-blocked \
  --update-on-pr-events
```

## Usage Examples

### Creating an Epic for Major Refactor

**User Request:**
```
"Create an epic for refactoring the monolithic functions in claude_runner.py"
```

**Agent Response:**
```markdown
## Summary
Created epic EPIC-124 for claude_runner.py refactoring initiative with proper scope definition and initial issue breakdown.

## Ticket Actions
- Created Epic: EPIC-124 "Refactor claude_runner.py Monolithic Functions"
- Identified 5 major function groups for individual issues
- Set target completion for end of Q2 2025
- Assigned to Engineering team with Architecture review dependency

## Workflow Status
- Epic Status: Open
- Priority: P1 (High) - Technical debt affecting maintainability
- Components: core, refactoring
- Dependencies: Architecture review, backward compatibility analysis

**EPIC-124: Refactor claude_runner.py Monolithic Functions**

Business Value:
- Improve code maintainability and readability
- Enable better testing and debugging
- Reduce risk of introducing bugs in core functionality
- Facilitate future feature development

Success Criteria:
- [ ] All functions under 50 lines of code
- [ ] Unit test coverage >95% for refactored modules
- [ ] No breaking changes to public APIs
- [ ] Performance regression <5%

Scope:
- Event handling functions (3 functions, ~200 lines)
- Configuration management functions (4 functions, ~150 lines)  
- Agent lifecycle functions (2 functions, ~180 lines)
- Error handling and logging functions (3 functions, ~120 lines)
- Utility and helper functions (5 functions, ~100 lines)

Timeline: 8 weeks (Q2 2025)

Next Steps:
1. Architecture review and design approval
2. Create individual issues for each function group
3. Plan implementation phases to minimize disruption
```

### Breaking Down Epic into Issues

**User Request:**
```
"Break down the refactor epic into specific issues for each function group"
```

**Agent Response:**
```markdown
## Summary
Created 5 issues under EPIC-124, each targeting specific function groups with clear scope and acceptance criteria.

## Ticket Actions
- Created ISSUE-156: Refactor event handling functions
- Created ISSUE-157: Refactor configuration management functions
- Created ISSUE-158: Refactor agent lifecycle functions
- Created ISSUE-159: Refactor error handling and logging functions
- Created ISSUE-160: Refactor utility and helper functions
- All issues linked to parent EPIC-124

## Workflow Status
- Epic: 0% complete (5/5 issues in Open status)
- All issues ready for development after architecture review
- Dependencies mapped between issues to prevent conflicts

**ISSUE-156: Refactor Event Handling Functions**
Type: Tech Debt
Priority: P1
Component: core, events
Estimated Effort: 13 points

Current Behavior: 3 monolithic functions handling event processing (~200 lines)
- handle_agent_events() - 85 lines
- process_workflow_events() - 70 lines  
- manage_lifecycle_events() - 45 lines

Expected Behavior: Modular event handling with clear separation of concerns

Acceptance Criteria:
- [ ] Extract event processing into separate EventHandler class
- [ ] Create specific handlers for each event type
- [ ] Maintain backward compatibility with existing event contracts
- [ ] Add comprehensive unit tests for all event scenarios
- [ ] Update documentation for new event handling architecture

Technical Notes:
- Use observer pattern for event subscription
- Consider async processing for high-volume events
- Maintain existing error handling behavior

**ISSUE-157: Refactor Configuration Management Functions**
Type: Tech Debt
Priority: P2
Component: core, config
Estimated Effort: 8 points

[Similar detailed structure for remaining issues...]
```

### Creating Implementation Tasks

**User Request:**
```
"Create tasks for implementing the event handler extraction pattern"
```

**Agent Response:**
```markdown
## Summary
Created 6 implementation tasks for ISSUE-156 (Event Handler Refactor), following the observer pattern architecture with proper testing and documentation.

## Ticket Actions
- Created TASK-201: Design EventHandler base class architecture
- Created TASK-202: Extract AgentEventHandler from monolithic function
- Created TASK-203: Extract WorkflowEventHandler with async support
- Created TASK-204: Extract LifecycleEventHandler with state management
- Created TASK-205: Implement EventDispatcher and subscription system
- Created TASK-206: Create comprehensive test suite for event handling
- All tasks linked to parent ISSUE-156

## Workflow Status
- Issue 156: 0% complete (6/6 tasks in Open status)
- Tasks properly sequenced with dependencies
- Ready for sprint planning and assignment

**TASK-201: Design EventHandler Base Class Architecture**
Parent: ISSUE-156
Assignee: @senior-architect
Priority: P1
Estimate: 4 hours

Objective: Create foundation classes for the new event handling system

Steps:
1. Define EventHandler abstract base class with required methods
2. Design EventSubscription system for handler registration
3. Create EventContext class for passing event data
4. Document class relationships and interaction patterns
5. Review design with architecture team

Deliverables:
- EventHandler base class specification
- Class diagram showing relationships
- Interface documentation
- Architecture review approval

Dependencies: None (foundational work)

**TASK-202: Extract AgentEventHandler from Monolithic Function**
Parent: ISSUE-156
Assignee: @backend-developer
Priority: P1
Estimate: 6 hours

Objective: Extract agent event handling logic into dedicated class

Steps:
1. Analyze existing handle_agent_events() function (85 lines)
2. Create AgentEventHandler class implementing EventHandler base
3. Extract and modularize event processing logic
4. Implement proper error handling and logging
5. Maintain existing public API contracts
6. Add unit tests for all event scenarios

Deliverables:
- AgentEventHandler class implementation
- Unit tests with >95% coverage
- Migration guide for any API changes
- Performance benchmark comparison

Dependencies: TASK-201 (EventHandler base class)

[Additional tasks follow similar pattern...]
```

## Integration with Other Agents

### Engineer Agent Integration

**Automatic Implementation Ticket Creation:**
```markdown
When Engineer Agent completes architectural analysis:
→ Ticketing Agent creates implementation issues
→ Links to original epic or feature request
→ Includes technical specifications and requirements
→ Assigns appropriate component and priority labels
```

**Example Flow:**
```
1. User: "Implement caching layer for API responses"
2. Engineer Agent: Analyzes requirements, creates technical specification
3. Ticketing Agent: Creates EPIC-125 "API Response Caching Implementation"
   ├── ISSUE-161 "Design cache architecture and storage strategy"
   ├── ISSUE-162 "Implement cache middleware for REST APIs"
   ├── ISSUE-163 "Add cache invalidation and TTL management"
   └── ISSUE-164 "Monitor cache performance and hit rates"
4. Engineer Agent: Begins implementation, updating task status
```

### QA Agent Integration

**Test Planning and Execution Tickets:**
```markdown
When QA Agent receives completed features:
→ Ticketing Agent creates comprehensive test issues
→ Links test tickets to implementation issues
→ Tracks test execution progress and results
→ Creates bug tickets for discovered issues
```

**Example Flow:**
```
1. ISSUE-162 "API Cache Middleware" → Status: Review
2. QA Agent: Reviews implementation, creates test plan
3. Ticketing Agent: Creates testing issues
   ├── TASK-301 "Unit test coverage verification"
   ├── TASK-302 "Integration testing with existing APIs"
   ├── TASK-303 "Performance testing under load"
   └── TASK-304 "Security testing for cache poisoning"
4. QA Agent: Executes tests, reports results
5. Ticketing Agent: Creates bug tickets for any issues found
```

### Security Agent Integration

**Vulnerability and Compliance Tracking:**
```markdown
When Security Agent identifies vulnerabilities:
→ Ticketing Agent creates security issues with appropriate priority
→ Links to affected components and systems
→ Tracks remediation progress and verification
→ Ensures compliance requirements are met
```

**Example Flow:**
```
1. Security Agent: Discovers SQL injection vulnerability
2. Ticketing Agent: Creates ISSUE-199 "Fix SQL injection in user search"
   - Priority: P0 (Critical)
   - Component: backend, database, security
   - Severity: High
   - Security Labels: vulnerability, sql-injection
3. Engineer Agent: Implements fix
4. Security Agent: Verifies remediation
5. Ticketing Agent: Updates status to Done, links verification results
```

### Documentation Agent Integration

**Documentation Tracking and Updates:**
```markdown
When features are developed or changed:
→ Ticketing Agent creates documentation update tickets
→ Links documentation tasks to feature implementation
→ Tracks documentation completeness and accuracy
→ Ensures user guides and technical docs stay current
```

**Example Flow:**
```
1. EPIC-124 "Claude Runner Refactoring" progresses
2. Documentation Agent: Identifies documentation impact
3. Ticketing Agent: Creates documentation issues
   ├── ISSUE-165 "Update developer guide for new event handling"
   ├── ISSUE-166 "Create migration guide for API changes"
   └── ISSUE-167 "Update troubleshooting docs for refactored components"
4. Documentation Agent: Creates and updates documentation
5. Ticketing Agent: Links docs to original implementation issues
```

### Operations Agent Integration

**Deployment and Infrastructure Tickets:**
```markdown
When Ops Agent manages deployments:
→ Ticketing Agent creates deployment and infrastructure issues
→ Tracks environment-specific configurations
→ Links operational tickets to feature development
→ Monitors production deployment success
```

**Example Flow:**
```
1. ISSUE-162 "API Cache Middleware" → Status: Done
2. Ops Agent: Plans production deployment
3. Ticketing Agent: Creates operational issues
   ├── TASK-401 "Configure Redis cluster for cache storage"
   ├── TASK-402 "Update load balancer for cache headers"
   ├── TASK-403 "Deploy cache middleware to staging"
   └── TASK-404 "Monitor cache performance in production"
4. Ops Agent: Executes deployment tasks
5. Ticketing Agent: Tracks deployment success and issues
```

## Best Practices

### Ticket Naming Conventions

**Epic Naming:**
```
Format: [EPIC] Clear business or technical initiative
✅ [EPIC] User Authentication System Overhaul
✅ [EPIC] Mobile Application Development
✅ [EPIC] Database Performance Optimization
❌ [EPIC] Fix stuff
❌ [EPIC] Improve things
```

**Issue Naming:**
```
Format: [Component] Clear problem or feature statement
✅ [Auth] Implement OAuth2 token refresh mechanism
✅ [Frontend] Add dark mode toggle to user preferences
✅ [API] Optimize database queries for user dashboard
❌ [Bug] Login broken
❌ [Feature] Make it better
```

**Task Naming:**
```
Format: [Action] Specific deliverable or work item
✅ [Backend] Create OAuth2 refresh token endpoint
✅ [Testing] Write integration tests for auth flow
✅ [Docs] Update API documentation for new endpoints
❌ [Work] Do auth stuff
❌ [Task] Fix the thing
```

### Description Templates

**Epic Description Template:**
```markdown
## Executive Summary
[High-level description and business justification]

## Business Value
[Why this matters to users/business]

## Goals & Success Criteria
- Primary goal: [Measurable outcome]
- Secondary goals: [Additional benefits]
- Success metrics: [How to measure success]

## Scope
### In Scope
- [Specific deliverables included]
- [Components to be modified]

### Out of Scope  
- [What's explicitly not included]
- [Future enhancements not in this epic]

## Timeline
- Phase 1: [Date range] - [Deliverables]
- Phase 2: [Date range] - [Deliverables]
- Target completion: [Date]

## Dependencies
- [External dependencies]
- [Team or resource dependencies]
- [Technical prerequisites]

## Risks & Mitigations
- Risk: [Potential issue]
  Mitigation: [How to address it]
```

**Issue Description Template:**
```markdown
## Current Behavior
[What happens now, including problems or limitations]

## Expected Behavior  
[What should happen after this issue is resolved]

## User Impact
[Who is affected and how]

## Acceptance Criteria
- [ ] [Specific, testable requirement]
- [ ] [Another requirement]
- [ ] [Final requirement]

## Technical Notes
[Implementation hints, architectural considerations]

## Dependencies
- Blocked by: [List of blocking issues]
- Blocks: [Issues that depend on this one]
- Related to: [Contextually related tickets]
```

**Task Description Template:**
```markdown
## Objective
[What needs to be accomplished]

## Steps to Complete
1. [Specific action item]
2. [Another action item]
3. [Final action item]

## Deliverables
- [Concrete output or artifact]
- [Testing requirements]
- [Documentation requirements]

## Definition of Done
- [ ] [Code/work completed]
- [ ] [Tests written and passing]
- [ ] [Documentation updated]
- [ ] [Code reviewed and approved]

## Time Estimate
[Hours or story points with confidence level]

## Dependencies
[Other tasks or issues that must complete first]
```

### Acceptance Criteria Format

**GIVEN/WHEN/THEN Format:**
```markdown
## Acceptance Criteria

**Scenario 1: Successful token refresh**
- GIVEN: User has valid refresh token
- WHEN: Access token expires during API call
- THEN: System automatically refreshes token and retries request

**Scenario 2: Invalid refresh token**
- GIVEN: User has expired or invalid refresh token  
- WHEN: Token refresh is attempted
- THEN: User is redirected to login page with appropriate message

**Scenario 3: Network failure during refresh**
- GIVEN: Token refresh is in progress
- WHEN: Network connection fails
- THEN: System queues refresh attempt and retries when connection restored
```

**Checklist Format:**
```markdown
## Acceptance Criteria

### Functional Requirements
- [ ] OAuth2 refresh endpoint accepts valid refresh tokens
- [ ] New access tokens have 1-hour expiry
- [ ] Refresh tokens are rotated on each use
- [ ] Invalid refresh tokens return 401 with clear error message
- [ ] Rate limiting prevents abuse (10 requests per minute per user)

### Non-Functional Requirements  
- [ ] Response time <200ms for token refresh
- [ ] Endpoint handles 1000 concurrent requests
- [ ] All sensitive data logged appropriately (no token values)
- [ ] HTTPS required for all token operations

### Testing Requirements
- [ ] Unit tests cover all success and error scenarios
- [ ] Integration tests verify end-to-end flow
- [ ] Load testing confirms performance requirements
- [ ] Security testing validates against common attacks
```

### Comment and Update Patterns

**Status Update Comments:**
```markdown
## Progress Update - [Date]

**Work Completed:**
- [Specific accomplishments]
- [Milestones reached]

**Current Status:** In Progress (60% complete)

**Next Steps:**
- [Immediate next actions]
- [Upcoming milestones]

**Blockers/Issues:**
- [Any obstacles encountered]
- [Help or decisions needed]

**ETA:** [Updated completion estimate]
```

**Code Review Comments:**
```markdown
## Code Review - [Date]

**Changes Reviewed:** 
- [Files or components reviewed]
- [Scope of changes]

**Feedback Summary:**
✅ **Approved:** [Aspects that meet requirements]
⚠️ **Minor Issues:** [Non-blocking suggestions]
❌ **Blocking Issues:** [Must be addressed before approval]

**Next Actions:**
- [Required changes]
- [Re-review requirements]
```

**Deployment Comments:**
```markdown
## Deployment Update - [Date]

**Environment:** [Staging/Production]
**Version:** [Release version or commit hash]

**Deployment Status:** ✅ Successful
**Verification Results:**
- [Test results]
- [Performance metrics]
- [User acceptance feedback]

**Monitoring:**
- [Key metrics to watch]
- [Alert conditions]
```

## Troubleshooting

### Common Issues and Solutions

**Issue: Tickets created at wrong hierarchy level**

*Symptoms:*
- Tasks created when Issues are needed
- Issues created when Epics are appropriate
- Confusion about scope and assignments

*Solution:*
```bash
# Review the decision tree criteria
./claude-mpm run -a ticketing "Analyze this work request and recommend appropriate ticket type: [describe work]"

# Reclassify existing tickets
trackdown ticket reclassify TASK-123 --to-issue --reason "Scope too large for single task"
trackdown issue reclassify ISSUE-456 --to-epic --reason "Multi-sprint initiative requiring coordination"
```

*Prevention:*
- Always ask: "Is this strategic (Epic), tactical (Issue), or implementation (Task)?"
- Consider timeline: >4 weeks = Epic, 1-2 weeks = Issue, <1 week = Task
- Evaluate scope: Multiple teams = Epic, One team = Issue, One person = Task

**Issue: Broken ticket relationships**

*Symptoms:*
- Tasks not properly linked to parent Issues
- Issues missing Epic relationships
- Circular dependencies detected

*Solution:*
```bash
# Audit and fix relationships
trackdown relationship audit --fix-orphaned --fix-circular
trackdown relationship validate EPIC-123 --deep-check

# Manually fix specific relationships
trackdown task update TASK-456 --parent ISSUE-789
trackdown issue link ISSUE-789 --epic EPIC-123
```

*Prevention:*
- Always specify parent relationships when creating tickets
- Use `--parent` flag consistently
- Regular relationship audits in sprint reviews

**Issue: Status conflicts and workflow violations**

*Symptoms:*
- Tickets marked "Done" with incomplete acceptance criteria
- Status transitions that skip required steps
- Blocked tickets without clear blocking reasons

*Solution:*
```bash
# Validate workflow compliance
trackdown workflow validate --fix-violations --report

# Fix specific status issues
trackdown issue update ISSUE-456 \
  --status "in-progress" \
  --comment "Reopening: acceptance criteria not fully met"

# Clear blocking relationships
trackdown issue unblock ISSUE-789 \
  --reason "Dependency resolved by ISSUE-788 completion"
```

*Prevention:*
- Always document blocking reasons clearly
- Verify acceptance criteria before marking "Done"
- Use workflow validation hooks in CI/CD

**Issue: Inconsistent labeling and components**

*Symptoms:*
- Similar tickets have different labels
- Components not standardized across project
- Difficulty finding related tickets

*Solution:*
```bash
# Standardize labels across project
trackdown label standardize --from-config labels.yaml
trackdown component audit --fix-duplicates

# Bulk update inconsistent tickets
trackdown ticket bulk-update \
  --query "component:front-end" \
  --set-component "frontend" \
  --add-label "migration-cleanup"
```

*Prevention:*
- Maintain label and component taxonomy documentation
- Use templates with pre-filled standard labels
- Regular cleanup during sprint retrospectives

### Recovery Procedures

**Recovering from Corrupted Ticket Hierarchy:**

1. **Audit Current State:**
```bash
# Generate hierarchy report
trackdown report hierarchy --format json > current_hierarchy.json
trackdown report orphaned --include-tasks > orphaned_tickets.txt
```

2. **Backup Before Recovery:**
```bash
# Create backup of current ticket state  
trackdown backup create --include-relationships --timestamp
```

3. **Reconstruct Relationships:**
```bash
# Fix orphaned tickets
trackdown orphaned fix --strategy "smart-parent-detection"
trackdown relationships rebuild --from-git-history
```

4. **Validate Recovery:**
```bash
# Verify integrity after recovery
trackdown validate --hierarchy --workflows --relationships
trackdown report hierarchy --compare-with current_hierarchy.json
```

**Recovering from Status Conflicts:**

1. **Identify Conflicts:**
```bash
# Find status violations
trackdown status audit --find-violations --output violations.json
```

2. **Reset to Known Good State:**
```bash
# Reset problematic tickets to previous valid status
trackdown status reset --from-backup [backup-id] --tickets-file violations.json
```

3. **Apply Correct Transitions:**
```bash
# Apply proper workflow transitions
trackdown workflow apply --from violations_fixed.yaml --validate-steps
```

### Performance Optimization

**Slow Ticket Queries:**

*Symptoms:*
- Long wait times for ticket searches
- Timeouts when loading epic hierarchies
- Poor dashboard performance

*Solutions:*
```bash
# Optimize database indices
trackdown admin optimize --rebuild-indices --vacuum
trackdown admin cache warm --priority-tickets --user-dashboards

# Configure query pagination
trackdown config set query.max_results 100
trackdown config set query.pagination true
```

**Memory Issues with Large Hierarchies:**

*Symptoms:*
- Out of memory errors when loading epics
- Slow performance with large ticket counts
- Browser crashes on complex hierarchy views

*Solutions:*
```bash
# Enable lazy loading for large hierarchies  
trackdown config set hierarchy.lazy_load true
trackdown config set hierarchy.batch_size 50

# Use streaming for large data exports
trackdown export --stream --batch-size 100 > large_dataset.json
```

## Advanced Usage

### Bulk Operations

**Creating Multiple Related Tickets:**
```bash
# Create epic with auto-generated issues
trackdown epic create-with-issues \
  --title "Q2 Feature Development" \
  --from-template quarterly_template.yaml \
  --auto-assign-teams

# Bulk create tasks from checklist
trackdown task bulk-create \
  --parent ISSUE-456 \
  --from-markdown implementation_checklist.md \
  --estimate-from-history
```

**Batch Status Updates:**
```bash
# Update all tickets in sprint
trackdown batch update \
  --query "sprint:23 AND status:review" \
  --set-status done \
  --add-comment "Sprint 23 completion"

# Mass priority adjustment
trackdown batch update \
  --query "component:security AND priority:P3" \
  --set-priority P2 \
  --reason "Security priority increase"
```

### Custom Workflows

**Defining Project-Specific Workflows:**
```yaml
# .ticketing/workflows.yaml
workflows:
  feature_development:
    states: [planning, development, review, testing, deployment, done]
    transitions:
      planning -> development: [requirements_approved]
      development -> review: [code_complete, tests_passing]
      review -> testing: [code_approved] 
      testing -> deployment: [qa_approved]
      deployment -> done: [deployed_successfully]
    
  bug_fix:
    states: [triage, investigation, fix, verification, closed]
    transitions:
      triage -> investigation: [priority_assigned]
      investigation -> fix: [root_cause_identified]
      fix -> verification: [fix_implemented]
      verification -> closed: [fix_verified]
```

**Applying Custom Workflows:**
```bash
# Set workflow for ticket type
trackdown workflow assign ISSUE-456 --workflow feature_development
trackdown workflow validate --check-transitions --report-violations
```

### Integration Patterns

**Git Integration:**
```bash
# Create branch from ticket
trackdown git create-branch ISSUE-456 --format "feature/ISSUE-{id}-{slug}"

# Auto-update ticket from commits
trackdown git hook install --update-status --time-tracking
```

**CI/CD Integration:**
```bash  
# Update tickets from build pipeline
trackdown cicd update-from-build \
  --build-id ${BUILD_ID} \
  --ticket-pattern "ISSUE-\d+" \
  --on-success "mark-review-ready"
```

**Slack/Teams Integration:**
```bash
# Send notifications for priority tickets
trackdown notify configure \
  --channel "#dev-team" \
  --priority P0,P1 \
  --events created,blocked,completed
```

This comprehensive documentation provides teams with everything needed to effectively use the Ticketing Agent for intelligent project management. The agent's smart classification, workflow management, and integration capabilities help maintain organized, trackable development processes while reducing administrative overhead.

**Remember**: null