# Claude MPM Core Agent Roles Summary

This document provides a clear overview of all 9 core agent types in the Claude MPM framework, their specific responsibilities, boundaries, and collaboration patterns.

## Quick Reference Table

| Agent | Nickname | Primary Role | Key Authority | Forbidden Actions |
|-------|----------|--------------|---------------|-------------------|
| **Documentation** | Documenter | Project documentation & changelogs | ALL documentation operations | Code implementation, testing |
| **Version Control** | Versioner | Git operations & version management | ALL Git operations | Code changes, documentation |
| **QA** | QA | Testing & quality assurance | ALL testing decisions | Writing production code |
| **Research** | Researcher | Investigation & analysis | ALL research decisions | Implementation decisions |
| **Ops** | Ops | Deployment & infrastructure | ALL deployment operations | Code changes, testing |
| **Security** | Security | Security analysis & protection | ALL security decisions | Code implementation |
| **Engineer** | Engineer | Code implementation | ALL code writing | Documentation files, tests |
| **Data Engineer** | Data Engineer | Data stores & AI APIs | ALL data operations | Business logic, UI code |
| **Ticketing** | Ticketing | Ticket management & tracking | ALL ticket operations | Code implementation, testing |

## Detailed Agent Responsibilities

### 1. Documentation Agent (Documenter)
**Role**: Owns all project documentation, maintains documentation health, and generates changelogs.

**Key Responsibilities**:
- Generate changelogs from git commit history
- Analyze commits for semantic versioning impact
- Maintain README files and API documentation
- Create user guides and developer documentation
- Audit documentation for outdated information
- Track documentation coverage metrics

**Concrete Examples**:
- "Generate changelog for v1.3.0 release"
- "Analyze project documentation health"
- "Update API documentation for new endpoints"
- "Create migration guide for v2.0"

**Ticket Integration**: Reports documentation gaps, version recommendations, and changelog updates to PM for ticket comments.

---

### 2. Version Control Agent (Versioner)
**Role**: Manages all Git operations, branches, merges, and version consistency.

**Key Responsibilities**:
- Execute all git commands and workflows
- Manage branches, merges, and tags
- Apply semantic version bumps
- Synchronize version files across the project
- Resolve merge conflicts
- Create annotated release tags

**Concrete Examples**:
- "Create feature branch for authentication"
- "Apply version bump for release v1.3.0"
- "Merge feature/auth-system to main"
- "Create release tag with changelog"

**Ticket Integration**: Updates ticket status based on branch operations, reports merge conflicts and version changes.

---

### 3. QA Agent (QA)
**Role**: Ensures quality through comprehensive testing and validation.

**Key Responsibilities**:
- Execute all test suites (unit, integration, E2E)
- Validate code quality and standards
- Perform regression testing
- Check security vulnerabilities
- Generate coverage reports
- Block releases if quality insufficient

**Concrete Examples**:
- "Execute full regression test suite"
- "Validate new authentication system"
- "Run performance benchmarks"
- "Generate test coverage report"

**Ticket Integration**: Reports test results, creates bug reports for PM to convert to tickets, validates fixes.

---

### 4. Research Agent (Researcher)
**Role**: Investigates technical solutions and provides evidence-based recommendations.

**Key Responsibilities**:
- Research technical solutions and approaches
- Analyze best practices and patterns
- Compare libraries and frameworks
- Use WebSearch for current information
- Provide performance benchmarks
- Create comparative analyses

**Concrete Examples**:
- "Research authentication best practices"
- "Compare React vs Vue for our use case"
- "Investigate Next.js 14 App Router patterns"
- "Research database scaling strategies"

**Ticket Integration**: Provides research findings to support implementation tickets, flags when research reveals need for new features.

---

### 5. Ops Agent (Ops)
**Role**: Handles all deployment, infrastructure, and operational tasks.

**Key Responsibilities**:
- Execute deployments to all environments
- Manage infrastructure and provisioning
- Configure CI/CD pipelines
- Monitor system health and performance
- Handle incident response
- Implement backup and recovery

**Concrete Examples**:
- "Deploy v1.3.0 to npm registry"
- "Initialize project infrastructure"
- "Set up monitoring dashboards"
- "Configure auto-scaling policies"

**Ticket Integration**: Reports deployment status, infrastructure changes, and operational metrics per ticket.

---

### 6. Security Agent (Security)
**Role**: Protects the system through security analysis and vulnerability management.

**Key Responsibilities**:
- Identify and assess vulnerabilities
- Perform security audits
- Review code for security issues
- Ensure compliance with standards
- Guide secure coding practices
- Manage security incidents

**Concrete Examples**:
- "Perform comprehensive security audit"
- "Fix critical authentication vulnerability"
- "Review API security measures"
- "Ensure GDPR compliance"

**Ticket Integration**: Reports critical vulnerabilities immediately, tracks remediation progress, ensures compliance per ticket.

---

### 7. Engineer Agent (Engineer)
**Role**: Implements all code changes, features, and bug fixes.

**Key Responsibilities**:
- Write all production code
- Implement features and bug fixes
- Create inline documentation
- Refactor and optimize code
- Debug issues
- Ensure code quality standards

**Concrete Examples**:
- "Implement user authentication system"
- "Fix memory leak in agent registry"
- "Refactor database connection pooling"
- "Optimize API response times"

**Ticket Integration**: Reports implementation progress, technical blockers, and completion status per ticket.

---

### 8. Data Engineer Agent (Data Engineer)
**Role**: Manages all data stores, databases, and AI API integrations.

**Key Responsibilities**:
- Design and optimize database schemas
- Manage AI API integrations (OpenAI, Claude)
- Implement data pipelines
- Handle data migrations
- Optimize query performance
- Manage API keys and rate limits

**Concrete Examples**:
- "Configure PostgreSQL for production"
- "Integrate OpenAI GPT-4 API"
- "Optimize database query performance"
- "Implement data backup strategy"

**Ticket Integration**: Reports data operation status, API health, performance metrics, and migration progress.

---

### 9. Ticketing Agent (Ticketing)
**Role**: Manages project visibility through comprehensive ticket tracking.

**Key Responsibilities**:
- Create and organize project tickets
- Update ticket status based on agent reports
- Track dependencies and blockers
- Generate project status reports
- Maintain ticket relationships
- Calculate velocity and burndown

**Concrete Examples**:
- "Organize tickets for Sprint 15"
- "Generate weekly project status report"
- "Track blocked tickets and escalate"
- "Create epic with subtasks for feature"

**Ticket Integration**: Central hub for all ticket operations, coordinates cross-agent ticket updates.

---

## Agent Collaboration Patterns

### Common Multi-Agent Workflows

#### 1. Feature Development Flow
```
PM → Ticketing (create feature ticket)
  → Research (investigate best approach)
  → Engineer (implement feature)
  → QA (test implementation)
  → Documentation (update docs)
  → Version Control (merge to main)
  → Ops (deploy to production)
```

#### 2. Bug Resolution Flow
```
QA (discover bug) → PM → Ticketing (create bug ticket)
  → Engineer (investigate and fix)
  → QA (verify fix)
  → Version Control (merge fix)
  → Ops (hotfix deployment)
```

#### 3. Release Flow ("push" command)
```
PM → Documentation (generate changelog)
  → QA (full regression testing)
  → Data Engineer (validate data integrity)
  → Version Control (version bump and tag)
  → Ops (production deployment)
```

#### 4. Security Incident Flow
```
Security (identify vulnerability) → PM → Ticketing (critical ticket)
  → Engineer (implement patch)
  → QA (security testing)
  → Version Control (emergency merge)
  → Ops (immediate deployment)
```

## Key Boundaries and Rules

### What Agents CANNOT Do

1. **Documentation Agent**: Cannot write code or tests
2. **Version Control Agent**: Cannot modify code content
3. **QA Agent**: Cannot write production code
4. **Research Agent**: Cannot make implementation decisions
5. **Ops Agent**: Cannot change code or write tests
6. **Security Agent**: Cannot implement fixes directly
7. **Engineer Agent**: Cannot create documentation files
8. **Data Engineer Agent**: Cannot write business logic
9. **Ticketing Agent**: Cannot implement or test code

### Authority Boundaries

Each agent has **absolute authority** within their domain:
- Only Documentation Agent decides documentation structure
- Only QA Agent determines if quality is sufficient
- Only Security Agent classifies vulnerability severity
- Only Ops Agent executes deployments
- Only Engineer Agent writes production code

## Ticket Integration Standards

### All Agents Must:
1. Include ticket reference in every task: `**Ticket Reference**: ISS-XXXX`
2. Report progress to PM for ticket updates
3. Flag blockers immediately
4. Provide completion summaries
5. Never create tickets directly (only PM creates tickets)

### Standard Progress Report Format:
```
[Agent Icon] [Agent] Progress Report
- Task: [current task]
- Status: [in progress/completed/blocked]
- Key Results: [specific outcomes]
- Blockers: [if any]
- Next Steps: [if applicable]
```

## Quick Decision Guide

**"Who handles this task?"**

- Writing code? → **Engineer Agent**
- Testing code? → **QA Agent**  
- Deploying code? → **Ops Agent**
- Documenting code? → **Documentation Agent**
- Researching solutions? → **Research Agent**
- Managing Git/versions? → **Version Control Agent**
- Security concerns? → **Security Agent**
- Database/API work? → **Data Engineer Agent**
- Tracking progress? → **Ticketing Agent**

Remember: When in doubt, the PM orchestrates and decides which agent to engage based on the task requirements.