# Structured Questions Examples

**Purpose**: Comprehensive examples of using structured question templates for consistent user interaction
**Usage**: Reference for PM when using AskUserQuestion tool with validation templates
**Related**: validation-templates.md, pr-workflow-examples.md, context-management-examples.md

---

## Project Initialization Workflow

### Complete /mpm-init Example

**Scenario**: User initializes new project with `/mpm-init` command

```
User: "/mpm-init"

Step 1: PM Detects Project Context
PM checks:
- .git directory: exists ✅
- package.json: not found
- requirements.txt: not found
- Project type: unknown
- Language: unknown

Step 2: PM Uses ProjectTypeTemplate
```python
ProjectTypeTemplate(
    existing_files=False,
    detected_language=None
)
```

Step 3: PM Asks User with AskUserQuestion
```json
{
  "questions": [
    {
      "question": "What type of project is this?",
      "header": "Project Type",
      "multiSelect": false,
      "options": [
        {
          "label": "Web Application",
          "description": "Full-stack web app with frontend and backend"
        },
        {
          "label": "API Service",
          "description": "Backend API only (REST or GraphQL)"
        },
        {
          "label": "CLI Tool",
          "description": "Command-line application or script"
        },
        {
          "label": "Library/Package",
          "description": "Reusable library to be published"
        }
      ]
    },
    {
      "question": "What is the primary programming language?",
      "header": "Language",
      "multiSelect": false,
      "options": [
        {
          "label": "JavaScript/TypeScript",
          "description": "Node.js backend or frontend framework"
        },
        {
          "label": "Python",
          "description": "Python application or service"
        },
        {
          "label": "Go",
          "description": "Go application or service"
        },
        {
          "label": "Rust",
          "description": "Rust application or service"
        }
      ]
    }
  ]
}
```

Step 4: User Responds
```
User selections:
- Project Type: "Web Application"
- Language: "JavaScript/TypeScript"
```

Step 5: PM Parses Responses and Continues
```python
project_type = "web_application"
language = "typescript"

# PM now uses DevelopmentWorkflowTemplate
DevelopmentWorkflowTemplate(
    project_type="web_application",
    language="typescript"
)
```

Step 6: PM Asks Development Preferences
```json
{
  "questions": [
    {
      "question": "Which testing framework should we use?",
      "header": "Testing",
      "multiSelect": false,
      "options": [
        {
          "label": "Jest",
          "description": "Industry standard, 70% market share, React ecosystem"
        },
        {
          "label": "Vitest",
          "description": "Modern, Vite-native, faster than Jest"
        },
        {
          "label": "No testing framework",
          "description": "Skip testing setup for now"
        }
      ]
    },
    {
      "question": "Do you want CI/CD configured?",
      "header": "CI/CD",
      "multiSelect": false,
      "options": [
        {
          "label": "GitHub Actions",
          "description": "Set up .github/workflows/ci.yml"
        },
        {
          "label": "GitLab CI",
          "description": "Set up .gitlab-ci.yml"
        },
        {
          "label": "No CI/CD",
          "description": "Skip CI/CD setup"
        }
      ]
    },
    {
      "question": "Which package manager?",
      "header": "Package Manager",
      "multiSelect": false,
      "options": [
        {
          "label": "npm",
          "description": "Default Node.js package manager"
        },
        {
          "label": "pnpm",
          "description": "Faster, disk-efficient alternative"
        },
        {
          "label": "yarn",
          "description": "Popular alternative with workspaces support"
        }
      ]
    }
  ]
}
```

Step 7: User Responds
```
User selections:
- Testing: "Vitest"
- CI/CD: "GitHub Actions"
- Package Manager: "pnpm"
```

Step 8: PM Delegates to Engineer
```
PM → Engineer: "Initialize project with following configuration:

📋 PROJECT SETUP:
- Type: Web Application
- Language: TypeScript
- Testing: Vitest
- CI/CD: GitHub Actions
- Package Manager: pnpm

Tasks:
1. Create package.json with TypeScript + Vitest dependencies
2. Set up tsconfig.json for web application
3. Create vitest.config.ts
4. Set up .github/workflows/ci.yml for GitHub Actions
5. Create basic project structure:
   - src/
   - tests/
   - public/ (if frontend)
6. Create README.md with setup instructions
7. Create .gitignore for Node.js + TypeScript

Use pnpm for all package management operations."

Engineer executes setup...

Engineer → PM: "Project initialized:
- package.json created with TypeScript, Vitest, React
- tsconfig.json configured for React + strict mode
- vitest.config.ts set up with coverage
- GitHub Actions CI configured (lint, test, build)
- Project structure created
- README.md with setup instructions
- .gitignore configured

Ready to start development. Run: pnpm install"
```

Step 9: PM Reports to User
```
PM → User: "✅ Project initialized successfully

Configuration:
- Web Application (TypeScript)
- Testing: Vitest with coverage
- CI/CD: GitHub Actions
- Package Manager: pnpm

Next steps:
1. Run: pnpm install
2. Run: pnpm test (verify setup)
3. Run: pnpm dev (start development server)

Project structure ready for development."
```
```

**Key Flow**:
1. PM asks project type + language
2. PM uses responses to configure development workflow template
3. PM asks testing, CI/CD, package manager preferences
4. PM delegates complete setup to engineer with all context
5. User has fully configured project ready for development

---

## PR Strategy Template Usage

### Multi-Ticket PR Creation

**Scenario**: User requests PRs for multiple tickets

```
User: "Create PRs for PROJ-101, PROJ-102, PROJ-103"

Step 1: PM Analyzes Context
PM checks:
- Ticket count: 3 tickets
- CI configuration: .github/workflows/ci.yml exists ✅
- Dependencies: PROJ-102 depends on PROJ-101

Step 2: PM Uses PRWorkflowTemplate
```python
PRWorkflowTemplate(
    num_tickets=3,
    has_ci=True,
    dependencies_detected=True
)
```

Step 3: PM Asks User with AskUserQuestion
```json
{
  "questions": [
    {
      "question": "How should we create PRs for these 3 tickets? (Dependencies detected: PROJ-102 → PROJ-101)",
      "header": "PR Strategy",
      "multiSelect": false,
      "options": [
        {
          "label": "Main-based PRs (independent)",
          "description": "Each ticket gets its own PR to main. Good for parallel review. ⚠️ May cause conflicts with detected dependencies."
        },
        {
          "label": "Stacked PRs (sequential)",
          "description": "PRs build on each other (PROJ-102 → PROJ-101 → main). Recommended when dependencies exist."
        }
      ]
    },
    {
      "question": "Should PRs be created as drafts?",
      "header": "Draft Mode",
      "multiSelect": false,
      "options": [
        {
          "label": "Draft PRs",
          "description": "Create as drafts for early feedback before formal review"
        },
        {
          "label": "Ready for Review",
          "description": "Create as ready-to-review (recommended if all tests passing)"
        }
      ]
    }
  ]
}
```

Step 4: User Responds
```
User selections:
- PR Strategy: "Stacked PRs (sequential)"
- Draft Mode: "Ready for Review"
```

Step 5: PM Delegates to version-control
```
PM → version-control: "Create stacked PRs for PROJ-101, PROJ-102, PROJ-103

Strategy: Stacked (respects dependencies)
- PR #1: PROJ-101 → main
- PR #2: PROJ-102 → feature/PROJ-101
- PR #3: PROJ-103 → main (independent)

Draft mode: false (ready for review)
```
```

**Template Advantage**: PM automatically detects dependencies and warns user about potential conflicts with main-based strategy.

---

## Scope Validation Template Usage

### Research Discovery Scenario

**Scenario**: Research discovers additional work during ticket implementation

```
User: "Implement TICKET-456: Add payment processing"

Research Agent discovers 8 additional items:
1. PCI compliance requirements (out-of-scope)
2. Webhook handler for payment events (scope-adjacent)
3. Payment retry logic (in-scope)
4. Refund processing (scope-adjacent)
5. Invoice generation (out-of-scope)
6. Currency conversion (out-of-scope)
7. Payment method storage (in-scope)
8. Error handling for payment failures (in-scope)

PM Classifies:
- In-Scope (3): Payment retry logic, payment method storage, error handling
- Scope-Adjacent (2): Webhook handler, refund processing
- Out-of-Scope (3): PCI compliance, invoice generation, currency conversion

PM Uses ScopeValidationTemplate:
```python
ScopeValidationTemplate(
    originating_ticket="TICKET-456",
    ticket_title="Add payment processing",
    in_scope_items=[
        "Payment retry logic",
        "Payment method storage",
        "Error handling for payment failures"
    ],
    scope_adjacent_items=[
        "Webhook handler for payment events",
        "Refund processing"
    ],
    out_of_scope_items=[
        "PCI compliance requirements",
        "Invoice generation",
        "Currency conversion"
    ]
)
```

PM Asks User:
```json
{
  "questions": [
    {
      "question": "Research discovered 8 items during TICKET-456 work. How should we handle scope?",
      "header": "Scope Decision",
      "multiSelect": false,
      "options": [
        {
          "label": "Include all 8 in TICKET-456",
          "description": "Expands ticket scope significantly. Delays completion by ~5 days."
        },
        {
          "label": "Create 3 subtasks, defer 5 to backlog",
          "description": "Subtasks for in-scope items. Defer scope-adjacent and out-of-scope."
        },
        {
          "label": "Create 3 subtasks + 2 follow-up tickets",
          "description": "Subtasks for in-scope. Create tickets for scope-adjacent. Defer out-of-scope."
        }
      ]
    }
  ]
}
```

User chooses: "Create 3 subtasks + 2 follow-up tickets"

PM Delegates to Ticketing:
```
PM → Ticketing: "Based on TICKET-456 scope validation:

1. Create 3 subtasks under TICKET-456:
   - TICKET-456-1: Payment retry logic
   - TICKET-456-2: Payment method storage
   - TICKET-456-3: Error handling for payment failures

2. Create 2 follow-up tickets (same epic):
   - PAYMENT-101: Webhook handler for payment events
   - PAYMENT-102: Refund processing

3. Defer to backlog (no tickets yet):
   - PCI compliance requirements
   - Invoice generation
   - Currency conversion"
```
```

**Template Advantage**: Structured approach prevents scope creep while capturing valuable discoveries for future work.

---

## Building Custom Questions Patterns

### Advanced Use Cases Beyond Templates

**Scenario**: PM needs custom questions not covered by standard templates

```
User: "Set up monitoring for our application"

PM Analysis:
- Requires custom questions (not covered by existing templates)
- Multiple decisions: monitoring tool, metrics, alerting
- Need user preferences before delegating to ops

PM Builds Custom Questions:
```json
{
  "questions": [
    {
      "question": "Which monitoring solution should we use?",
      "header": "Monitoring",
      "multiSelect": false,
      "options": [
        {
          "label": "Prometheus + Grafana",
          "description": "Self-hosted, full control, requires infrastructure"
        },
        {
          "label": "Datadog",
          "description": "SaaS, easy setup, costs scale with usage"
        },
        {
          "label": "CloudWatch",
          "description": "AWS native, integrates well if already on AWS"
        }
      ]
    },
    {
      "question": "What should we monitor?",
      "header": "Metrics",
      "multiSelect": true,  // Multiple selections allowed
      "options": [
        {
          "label": "Application metrics",
          "description": "Request rate, error rate, latency (RED metrics)"
        },
        {
          "label": "Infrastructure metrics",
          "description": "CPU, memory, disk usage"
        },
        {
          "label": "Business metrics",
          "description": "User signups, payments, conversions"
        },
        {
          "label": "Database metrics",
          "description": "Query performance, connection pool, locks"
        }
      ]
    },
    {
      "question": "Set up alerting?",
      "header": "Alerting",
      "multiSelect": false,
      "options": [
        {
          "label": "Yes, with PagerDuty",
          "description": "24/7 on-call rotation, escalation policies"
        },
        {
          "label": "Yes, with Slack",
          "description": "Alerts to Slack channel, no on-call"
        },
        {
          "label": "No alerting yet",
          "description": "Just dashboards for now"
        }
      ]
    }
  ]
}
```

User Responds:
```
User selections:
- Monitoring: "Prometheus + Grafana"
- Metrics: ["Application metrics", "Infrastructure metrics", "Database metrics"]
- Alerting: "Yes, with Slack"
```

PM Delegates to ops:
```
PM → ops: "Set up monitoring infrastructure

Configuration:
- Tool: Prometheus + Grafana (self-hosted)
- Metrics to collect:
  - Application: Request rate, error rate, latency (RED)
  - Infrastructure: CPU, memory, disk
  - Database: Query performance, connection pool, locks
- Alerting: Slack integration (no PagerDuty)

Tasks:
1. Deploy Prometheus server
2. Deploy Grafana for dashboards
3. Configure application instrumentation (RED metrics)
4. Set up node_exporter for infrastructure metrics
5. Configure PostgreSQL exporter for database metrics
6. Create Grafana dashboards for each metric category
7. Set up Slack webhook for alerts
8. Configure alert rules (error rate >5%, latency p95 >500ms, DB connections >80%)"
```
```

**Custom Question Benefits**:
- Flexible for any decision-making scenario
- Multi-select support for collecting multiple preferences
- Clear descriptions guide user choices
- PM gets structured data to delegate effectively

---

## Template Selection Decision Tree

**When to use which template?**

```
User Request → PM Analysis → Template Selection

"Create PRs for X tickets"
→ Multiple tickets detected
→ Use PRWorkflowTemplate

"/mpm-init" or "Initialize project"
→ Project setup needed
→ Use ProjectTypeTemplate + DevelopmentWorkflowTemplate

Research discovers additional work
→ Scope boundary clarification needed
→ Use ScopeValidationTemplate

Monitoring, deployment, or custom workflow
→ No standard template fits
→ Build custom questions with AskUserQuestion

Context reaching 70%
→ Token management needed
→ Use ContextManagementTemplate (auto-generated)
```

---

## Success Criteria

**Structured questions are working if**:
- ✅ PM uses templates for common scenarios (PRs, init, scope)
- ✅ PM builds custom questions when templates don't fit
- ✅ User receives clear options with descriptions
- ✅ PM parses responses correctly and delegates with full context
- ✅ Decisions are documented and followed in delegation
- ✅ Multi-select used appropriately (multiple metrics, features, etc.)

**Red Flags**:
- ❌ PM assumes user preferences instead of asking
- ❌ Questions lack clear descriptions
- ❌ Options are not mutually exclusive (unless multi-select)
- ❌ PM doesn't use template responses in delegation
- ❌ User confused by question phrasing
- ❌ PM asks for same information multiple times

---

## Related References

- **Validation Templates**: See [validation-templates.md](validation-templates.md)
- **PR Workflow**: See [pr-workflow-examples.md](pr-workflow-examples.md)
- **Context Management**: See [context-management-examples.md](context-management-examples.md)
- **PM Examples**: See [pm-examples.md](pm-examples.md)

---

**Last Updated**: 2025-12-01
**Phase**: Phase 3 Optimization - Example Extraction
