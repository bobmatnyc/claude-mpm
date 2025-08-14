# Ticket Workflow and Best Practices

This guide provides comprehensive workflows and best practices for effective ticket management in claude-mpm.

## Overview

Effective ticket management is crucial for project success. This guide covers proven workflows, naming conventions, and organizational strategies to maximize productivity and maintain clear project visibility.

## Workflow Patterns

### Feature Development Workflow

**Epic → Issue → Task Pattern** for new feature development:

```bash
# 1. Create epic for major initiative
claude-mpm tickets create "User Dashboard Redesign" \
  --type epic \
  --priority high \
  --description "Modernize user dashboard with improved UX and performance"

# 2. Break down into feature issues
claude-mpm tickets create "Dashboard Navigation Enhancement" \
  --type issue \
  --parent-epic EP-0012 \
  --priority high \
  --tags "frontend,ux,navigation"

claude-mpm tickets create "Performance Optimization for Dashboard" \
  --type issue \
  --parent-epic EP-0012 \
  --priority medium \
  --tags "performance,backend,optimization"

# 3. Create implementation tasks
claude-mpm tickets create "Redesign navigation menu component" \
  --type task \
  --parent-issue ISS-0067 \
  --priority high \
  --tags "frontend,react,component"

claude-mpm tickets create "Implement lazy loading for dashboard widgets" \
  --type task \
  --parent-issue ISS-0068 \
  --priority medium \
  --tags "frontend,performance,lazy-loading"
```

**Workflow Progression:**
```
Epic: Planning → In Progress → Review → Done
├── Issue 1: Open → In Progress → Ready → Tested → Done
│   ├── Task A: Open → In Progress → Done
│   └── Task B: Open → In Progress → Done
└── Issue 2: Open → In Progress → Ready → Tested → Done
    └── Task C: Open → In Progress → Done
```

### Bug Fix Workflow

**Direct Issue → Task Pattern** for bug fixes:

```bash
# 1. Create bug issue
claude-mpm tickets create "Login form validation not working" \
  --type bug \
  --priority critical \
  --description "Users can submit empty login forms without validation errors" \
  --tags "frontend,validation,auth"

# 2. Create investigation and fix tasks
claude-mpm tickets create "Investigate validation logic failure" \
  --type task \
  --parent-issue ISS-0069 \
  --priority critical \
  --tags "investigation,debugging"

claude-mpm tickets create "Fix validation component state management" \
  --type task \
  --parent-issue ISS-0069 \
  --priority critical \
  --tags "frontend,react,fix"

claude-mpm tickets create "Add comprehensive validation tests" \
  --type task \
  --parent-issue ISS-0069 \
  --priority high \
  --tags "testing,validation,coverage"
```

### Maintenance and Tech Debt Workflow

**Epic → Issue Pattern** for systematic improvements:

```bash
# 1. Create tech debt epic
claude-mpm tickets create "Code Quality Improvements Q3 2025" \
  --type epic \
  --priority medium \
  --description "Systematic code quality improvements across codebase" \
  --tags "tech-debt,quality,maintenance"

# 2. Create specific improvement issues
claude-mpm tickets create "Refactor monolithic user service" \
  --type issue \
  --parent-epic EP-0013 \
  --priority medium \
  --description "Break down 500-line user service into smaller, focused modules"

claude-mpm tickets create "Update deprecated dependencies" \
  --type issue \
  --parent-epic EP-0013 \
  --priority low \
  --description "Update 12 deprecated npm packages to current versions"
```

## Status Management Best Practices

### Status Progression Rules

**Linear Progression (Recommended):**
```
Open → In Progress → Ready → Tested → Done
```

**Alternative Paths:**
```
Open → In Progress → Blocked → In Progress → Ready → Done
Open → In Progress → Ready → Reopened → In Progress → Done
```

### Status Transition Guidelines

**Moving to In Progress:**
```bash
# Always add assignee and comment when starting work
claude-mpm tickets update TSK-0123 \
  --status in_progress \
  --assign john.doe@company.com

claude-mpm tickets comment TSK-0123 \
  "Started implementation. Estimated completion: 2025-08-16"
```

**Marking as Blocked:**
```bash
# Always specify blocking reason and link to blocker
claude-mpm tickets workflow TSK-0123 blocked \
  --comment "Blocked by TSK-0122 (API endpoint not ready)"

# Create blocking relationship if needed
aitrackdown task link TSK-0123 --blocks TSK-0122
```

**Moving to Ready for Review:**
```bash
# Include completion details and review requirements
claude-mpm tickets workflow TSK-0123 ready \
  --comment "Implementation complete. Requires: code review, testing. PR: #456"
```

**Closing as Done:**
```bash
# Include completion summary and verification
claude-mpm tickets close TSK-0123 \
  --resolution "Feature implemented and tested. Deployed in version 1.2.3"
```

## Naming Conventions

### Epic Naming

**Format:** `[Business Context] High-level Initiative`

**Good Examples:**
- `User Authentication System Overhaul`
- `Mobile Application Development`
- `API Performance Optimization Initiative`
- `Q3 2025 Security Enhancements`

**Poor Examples:**
- `Fix things` (too vague)
- `Implement stuff` (no business context)
- `Epic for features` (circular naming)

### Issue Naming

**Format:** `[Component] Specific problem or feature statement`

**Good Examples:**
- `[Auth] Implement OAuth2 token refresh mechanism`
- `[Frontend] Add dark mode toggle to user preferences`
- `[API] Optimize database queries for user dashboard`
- `[Security] Fix SQL injection vulnerability in reports`

**Poor Examples:**
- `Login broken` (no component, too vague)
- `Make it faster` (no specific target)
- `User wants feature` (no technical detail)

### Task Naming

**Format:** `[Action] Specific deliverable or work item`

**Good Examples:**
- `[Implement] OAuth2 refresh token endpoint`
- `[Test] Write integration tests for auth flow`
- `[Document] Update API docs for new endpoints`
- `[Fix] Validation error handling in login form`

**Poor Examples:**
- `Work on auth` (no specific action)
- `Do the thing` (completely vague)
- `Task for login` (circular naming)

## Tag Organization Strategy

### Component Tags
Use consistent component identifiers:
- `frontend`, `backend`, `api`, `database`
- `auth`, `payment`, `search`, `notification`
- `mobile`, `web`, `desktop`

### Type Tags
Classify work by nature:
- `feature`, `bug`, `enhancement`, `refactor`
- `security`, `performance`, `accessibility`
- `documentation`, `testing`, `deployment`

### Priority Tags
Supplement priority field:
- `urgent`, `customer-facing`, `production-down`
- `nice-to-have`, `future-enhancement`
- `technical-debt`, `maintenance`

### Sprint/Release Tags
Track delivery timeline:
- `sprint-23`, `q3-2025`, `v1.3.0`
- `hotfix`, `patch-release`, `major-release`

**Example Tag Usage:**
```bash
claude-mpm tickets create "Implement two-factor authentication" \
  --type feature \
  --priority high \
  --tags "auth,security,frontend,backend,sprint-24,customer-requested"
```

## Priority Assignment Guidelines

### Critical (P0) - Immediate Action Required
**Criteria:**
- System completely down or unusable
- Data loss or corruption
- Active security breaches
- Complete feature failure affecting all users

**Response Time:** Within 1 hour
**Examples:**
- Database server crashed
- Payment processing completely broken
- User data exposed publicly
- Authentication system down

### High (P1) - Same Day Resolution
**Criteria:**
- Major features broken for significant user segment
- Serious performance degradation
- Blocking dependencies for other high-priority work
- Customer-escalated issues

**Response Time:** Within 8 hours
**Examples:**
- Search functionality not working
- Mobile app crashes on startup
- API response times > 10 seconds
- Production deployment blocked

### Medium (P2) - Current Sprint
**Criteria:**
- Minor feature issues with workarounds
- Performance issues affecting some users
- Planned feature development
- Non-blocking technical debt

**Response Time:** 1-2 weeks
**Examples:**
- UI elements misaligned on certain browsers
- Feature enhancement requests
- Code refactoring for maintainability
- Documentation updates

### Low (P3) - Next Sprint or Later
**Criteria:**
- Cosmetic issues
- Nice-to-have features
- Technical debt with no user impact
- Future enhancements

**Response Time:** When capacity allows
**Examples:**
- Color scheme improvements
- Additional configuration options
- Internal tooling improvements
- Experimental features

## Escalation Procedures

### Automatic Escalation Triggers

**Time-Based Escalation:**
```bash
# Set up monitoring for stale tickets
aitrackdown monitor setup \
  --escalate-after "P0:2h,P1:1d,P2:1w,P3:1m" \
  --notify-channel "#dev-team"
```

**Status-Based Escalation:**
- Tickets blocked > 3 days
- Critical issues open > 4 hours
- High priority issues open > 24 hours

### Manual Escalation Process

**Step 1: Update Priority**
```bash
claude-mpm tickets update TSK-0123 --priority critical
```

**Step 2: Add Escalation Comment**
```bash
claude-mpm tickets comment TSK-0123 \
  "ESCALATED: Customer impact increasing. Need immediate attention from team lead."
```

**Step 3: Notify Stakeholders**
```bash
aitrackdown notify send TSK-0123 \
  --to "team-lead@company.com,product-manager@company.com" \
  --urgent
```

## Team Collaboration Patterns

### Sprint Planning Workflow

**Pre-Sprint Preparation:**
```bash
# Review epic progress
claude-mpm tickets list --type epic --status in_progress --verbose

# Identify ready issues for sprint
claude-mpm tickets search "status:open priority:high" --type issue

# Ensure tasks are properly broken down
aitrackdown epic status EP-0012 --show-incomplete-breakdown
```

**Sprint Assignment:**
```bash
# Assign sprint tag to selected items
aitrackdown batch update \
  --query "id:TSK-0123,TSK-0124,ISS-0067" \
  --add-tag "sprint-24" \
  --set-status open

# Balance workload across team
aitrackdown team balance --sprint 24 --capacity-file team_capacity.yaml
```

### Code Review Integration

**Link Tickets to Pull Requests:**
```bash
# In PR description, reference tickets
# Closes TSK-0123
# Addresses ISS-0067 
# Related to EP-0012

# Update ticket status when PR is ready
claude-mpm tickets workflow TSK-0123 ready \
  --comment "Implementation complete. PR #456 ready for review"
```

**Review Completion:**
```bash
# Update status after approval
claude-mpm tickets workflow TSK-0123 tested \
  --comment "Code review passed. PR #456 approved and merged"
```

### Daily Standup Support

**Generate Standup Reports:**
```bash
# Show your current work
claude-mpm tickets list \
  --assignee "$(git config user.email)" \
  --status in_progress \
  --verbose

# Show team progress
aitrackdown report sprint-progress \
  --sprint 24 \
  --format standup
```

**Update Work Status:**
```bash
# Quick status updates during standup
claude-mpm tickets comment TSK-0123 \
  "50% complete. Implementing core logic. No blockers."

claude-mpm tickets comment TSK-0124 \
  "Blocked by API endpoint. Switching to TSK-0125."
```

## Quality Assurance Integration

### Testing Workflow

**Create Testing Tasks:**
```bash
# Link testing tasks to feature development
claude-mpm tickets create "Integration testing for OAuth2 flow" \
  --type task \
  --parent-issue ISS-0067 \
  --tags "testing,integration,auth" \
  --priority high
```

**Test Results Tracking:**
```bash
# Document test outcomes
claude-mpm tickets comment TSK-0125 \
  "Test Results: 
  - Unit Tests: 45/45 passing
  - Integration Tests: 12/12 passing  
  - Performance Tests: within SLA
  - Security Tests: no vulnerabilities found"
```

### Bug Report Workflow

**From Testing to Development:**
```bash
# QA creates bug report
claude-mpm tickets create "Validation errors persist after form reset" \
  --type bug \
  --priority high \
  --description "Steps to reproduce: 1) Submit invalid form 2) Reset form 3) Errors still visible"

# Developer creates fix task
claude-mpm tickets create "Clear validation state on form reset" \
  --type task \
  --parent-issue BUG-0089 \
  --assign developer@company.com
```

## Reporting and Analytics

### Progress Tracking

**Epic Progress Reports:**
```bash
# Generate epic status report
aitrackdown epic status EP-0012 \
  --show-completion-percentage \
  --show-blocking-issues \
  --format report

# Sprint burn-down data
aitrackdown report burndown \
  --sprint 24 \
  --export-csv sprint_24_burndown.csv
```

**Team Performance Metrics:**
```bash
# Individual productivity metrics
aitrackdown report individual \
  --assignee john.doe@company.com \
  --period "last-month" \
  --show-completion-times

# Team velocity analysis
aitrackdown report velocity \
  --team "frontend-team" \
  --last-sprints 5
```

### Retrospective Support

**Collect Retrospective Data:**
```bash
# Issues that went well
claude-mpm tickets search "status:done" \
  --period "last-sprint" \
  --tags "went-well"

# Identify improvement areas
claude-mpm tickets search "status:reopened OR priority:critical" \
  --period "last-sprint"

# Process improvement opportunities
aitrackdown report blockers \
  --period "last-sprint" \
  --analyze-patterns
```

## Troubleshooting Common Issues

### Broken Hierarchy Relationships

**Symptoms:**
- Tasks not appearing under parent issues
- Epic progress not calculating correctly
- Orphaned tickets in search results

**Resolution:**
```bash
# Audit current relationships
aitrackdown relationship audit --fix-orphaned

# Manually fix specific relationships
claude-mpm tickets update TSK-0123 --parent-issue ISS-0067

# Rebuild hierarchy cache
aitrackdown admin rebuild-hierarchy
```

### Status Workflow Violations

**Symptoms:**
- Tickets marked done without completion criteria
- Status transitions that skip steps
- Blocked tickets without clear reasons

**Resolution:**
```bash
# Validate workflow compliance
aitrackdown workflow validate --fix-violations

# Reset problematic tickets
claude-mpm tickets update TSK-0123 --status in_progress
claude-mpm tickets comment TSK-0123 "Reopened: completion criteria not met"
```

### Performance Issues with Large Projects

**Symptoms:**
- Slow ticket list loading
- Search timeouts
- Memory issues with epic hierarchies

**Optimization:**
```bash
# Configure pagination
aitrackdown config set query.page_size 50
aitrackdown config set hierarchy.lazy_load true

# Clean up old data
aitrackdown admin archive \
  --older-than "6-months" \
  --status "done,closed"

# Optimize database
aitrackdown admin optimize --rebuild-indices
```

## Advanced Patterns

### Multi-Team Coordination

**Cross-Team Dependencies:**
```bash
# Create coordination epic
claude-mpm tickets create "Backend/Frontend API Integration" \
  --type epic \
  --tags "coordination,backend-team,frontend-team"

# Link dependent issues
aitrackdown issue link ISS-0067 --depends-on ISS-0068
aitrackdown issue link ISS-0068 --blocks ISS-0067
```

**Shared Component Development:**
```bash
# Tag shared components clearly
claude-mpm tickets create "Update shared authentication library" \
  --type issue \
  --tags "shared-component,auth,affects-multiple-teams" \
  --priority high
```

### Release Management

**Release Planning:**
```bash
# Create release epic
claude-mpm tickets create "Version 2.1.0 Release" \
  --type epic \
  --tags "release,v2.1.0,milestone"

# Link all release issues
aitrackdown epic add-issues EP-0015 \
  --issues "ISS-0067,ISS-0068,ISS-0069"

# Track release progress
aitrackdown report release-readiness \
  --epic EP-0015 \
  --check-test-coverage \
  --check-documentation
```

**Hotfix Workflow:**
```bash
# Create hotfix issue
claude-mpm tickets create "Critical security patch for auth module" \
  --type bug \
  --priority critical \
  --tags "hotfix,security,urgent"

# Fast-track workflow
claude-mpm tickets workflow BUG-0090 in_progress
# ... immediate fix and testing ...
claude-mpm tickets close BUG-0090 --resolution "Deployed hotfix v2.0.1"
```

## Integration with Development Tools

### Git Integration

**Branch Naming from Tickets:**
```bash
# Create feature branch from ticket
git checkout -b feature/TSK-0123-oauth2-refresh-tokens

# Commit message templates
git commit -m "TSK-0123: Implement OAuth2 refresh token endpoint

- Add refresh token model and validation
- Create REST endpoint with error handling  
- Add rate limiting and security headers

Addresses TSK-0123"
```

**Automatic Status Updates:**
```bash
# Configure git hooks to update tickets
aitrackdown git hook install \
  --on-commit "add-comment" \
  --on-push "update-status" \
  --on-merge "mark-ready"
```

### CI/CD Integration

**Build Pipeline Updates:**
```bash
# Update tickets from CI/CD
aitrackdown ci update \
  --build-id $BUILD_ID \
  --ticket-pattern "TSK-\d+" \
  --on-success "mark-tested" \
  --on-failure "add-failure-comment"
```

This comprehensive guide provides the foundation for effective ticket management in claude-mpm. Regular application of these patterns and practices will result in better project visibility, improved team coordination, and more predictable delivery timelines.