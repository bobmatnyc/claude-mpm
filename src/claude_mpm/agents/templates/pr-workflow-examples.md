# PR Workflow Examples

**Purpose**: Comprehensive examples of PR creation workflows and strategy selection
**Usage**: Reference for PM when coordinating PR creation across multiple tickets
**Related**: version-control.md, validation-templates.md

---

## Main-Based PR Examples

### Single Ticket PR

**Scenario**: User requests PR for single independent ticket

```
User: "Create PR for PROJ-123"

PM Analysis:
- Single ticket (1)
- Independent feature (not blocking other work)
- CI configured: Yes
- Strategy: Main-based (default for single ticket)

PM Workflow:
1. Check ticket status
   PM → Ticketing: "Check PROJ-123 status"
   Ticketing: "PROJ-123 is complete, all tests passing"

2. Delegate to version-control
   PM → version-control: "Create PR for PROJ-123
   - Base branch: main
   - PR title: feat: Add OAuth2 authentication (PROJ-123)
   - Draft mode: false
   - Auto-merge: disabled (requires review)"

3. version-control executes
   version-control: "PR created: #42
   - Branch: feature/oauth2
   - Target: main
   - Status: Ready for review
   - CI: Passing ✅
   - URL: https://github.com/org/repo/pull/42"

4. PM reports to user
   PM: "PR #42 created for PROJ-123 and ready for review"
```

**When to use Main-Based**:
- ✅ Single ticket
- ✅ Independent features
- ✅ No dependencies between tickets
- ✅ Parallel development (multiple developers)

---

## Stacked PR Examples

### Dependent Ticket Chain

**Scenario**: User requests PRs for 3 dependent tickets

```
User: "Create PRs for PROJ-101, PROJ-102, PROJ-103"

PM Analysis:
- Multiple tickets (3)
- Dependency chain: PROJ-101 → PROJ-102 → PROJ-103
- CI configured: Yes
- Strategy: Stacked (sequential dependencies)

PM Workflow:
1. Check dependencies
   PM → Ticketing: "Check dependencies for PROJ-101, PROJ-102, PROJ-103"
   Ticketing: "PROJ-102 depends on PROJ-101, PROJ-103 depends on PROJ-102"

2. Use PRWorkflowTemplate
   PM → User: "Detected 3 dependent tickets. Recommend stacked PRs.

   Option A: Main-based PRs (independent, parallel review)
   Option B: Stacked PRs (sequential, preserves dependencies)

   Your tickets have dependencies, recommending Option B."

3. User confirms stacked approach
   User: "Option B - stacked PRs"

4. Delegate to version-control
   PM → version-control: "Create stacked PRs for PROJ-101, PROJ-102, PROJ-103

   PR Strategy: Stacked
   - PR #1: PROJ-101 → main
   - PR #2: PROJ-102 → feature/PROJ-101
   - PR #3: PROJ-103 → feature/PROJ-102

   Merge Order: PR #1 first, then #2, then #3
   Draft mode: false
   Auto-merge: disabled"

5. version-control executes
   version-control: "Stacked PRs created:
   - PR #43: PROJ-101 → main (ready for review)
   - PR #44: PROJ-102 → feature/PROJ-101 (draft, blocked by #43)
   - PR #45: PROJ-103 → feature/PROJ-102 (draft, blocked by #44)

   Merge order enforced via branch targeting"

6. PM reports to user
   PM: "3 stacked PRs created:
   - PR #43 ready for review (merge first)
   - PR #44, #45 waiting on #43 merge

   After #43 merges, version-control will rebase #44 onto main automatically"
```

**When to use Stacked PRs**:
- ✅ Multiple dependent tickets
- ✅ Sequential feature development
- ✅ Phased rollout (stage 1 → stage 2 → stage 3)
- ✅ Large features broken into reviewable chunks

---

## PR Strategy Selection Examples

### 3-Ticket Scenario with CI

**Complete Workflow Example**

```
User: "Create PRs for tickets MPM-101, MPM-102, MPM-103"

Step 1: PM Analyzes Context
PM checks:
- Ticket count: 3 tickets
- CI configuration: .github/workflows/ci.yml exists ✅
- Dependencies: None detected (independent features)

Step 2: PM Uses PRWorkflowTemplate
```python
PRWorkflowTemplate(
    num_tickets=3,
    has_ci=True,
    dependencies_detected=False
)
```

Step 3: PM Asks User with AskUserQuestion
```json
{
  "questions": [
    {
      "question": "How should we create PRs for these 3 tickets?",
      "header": "PR Strategy",
      "multiSelect": false,
      "options": [
        {
          "label": "Main-based PRs (independent)",
          "description": "Each ticket gets its own PR to main. Good for parallel review and independent features."
        },
        {
          "label": "Stacked PRs (sequential)",
          "description": "PRs build on each other (PR2 → PR1 → main). Good for dependent features."
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
    },
    {
      "question": "Enable auto-merge after CI passes and approvals met?",
      "header": "Auto-merge",
      "multiSelect": false,
      "options": [
        {
          "label": "Enable auto-merge",
          "description": "PRs merge automatically when CI passes and required approvals obtained"
        },
        {
          "label": "Manual merge",
          "description": "Require manual merge click (more control)"
        }
      ]
    }
  ]
}
```

Step 4: User Responds
```
User selections:
- PR Strategy: "Main-based PRs (independent)"
- Draft Mode: "Ready for Review"
- Auto-merge: "Manual merge"
```

Step 5: PM Parses Responses
```python
pr_strategy = "main-based"  # from PR Strategy response
draft_mode = False  # from "Ready for Review"
auto_merge = False  # from "Manual merge"
```

Step 6: PM Delegates to version-control
```
PM → version-control: "Create main-based PRs for MPM-101, MPM-102, MPM-103

Configuration:
- Base branch: main (for all 3)
- Draft mode: false (ready for review)
- Auto-merge: disabled (manual merge required)
- CI checks: Required (must pass before merge)

Tickets:
1. MPM-101: Add user authentication
2. MPM-102: Implement caching layer
3. MPM-103: Optimize database queries

All features are independent, parallel review recommended."
```

Step 7: version-control Executes
```
version-control → PM: "3 main-based PRs created:

PR #50: feat: Add user authentication (MPM-101)
- Branch: feature/auth → main
- Status: Ready for review
- CI: Running... ✓ Passed
- URL: https://github.com/org/repo/pull/50

PR #51: feat: Implement caching layer (MPM-102)
- Branch: feature/caching → main
- Status: Ready for review
- CI: Running... ✓ Passed
- URL: https://github.com/org/repo/pull/51

PR #52: perf: Optimize database queries (MPM-103)
- Branch: feature/db-optimization → main
- Status: Ready for review
- CI: Running... ✓ Passed
- URL: https://github.com/org/repo/pull/52

All PRs ready for review. Manual merge required after approval."
```

Step 8: PM Reports to User
```
PM → User: "3 PRs created and ready for review:
- PR #50 (MPM-101): User authentication
- PR #51 (MPM-102): Caching layer
- PR #52 (MPM-103): Database optimization

All CI checks passing ✅
Review these PRs in any order (independent features)
Manual merge after approval"
```
```

**Key Decisions**:
1. **Strategy**: Main-based chosen (independent features, parallel review)
2. **Draft**: Disabled (tests passing, ready for formal review)
3. **Auto-merge**: Disabled (user wants manual control)

---

## Conflict Resolution Examples

### Handling Merge Conflicts in Stacked PRs

**Scenario**: Stacked PR #2 has conflicts after PR #1 merges

```
Initial State:
- PR #43: PROJ-101 → main (merged ✅)
- PR #44: PROJ-102 → feature/PROJ-101 (conflicts ⚠️)
- PR #45: PROJ-103 → feature/PROJ-102 (waiting)

Conflict Detected:
version-control: "PR #44 has merge conflicts with main after #43 merge
Conflicts in: src/auth/login.js, src/api/routes.js"

PM Workflow:
1. Notify user
   PM → User: "PR #44 has merge conflicts after #43 merge
   Conflicts in 2 files. Need to resolve before continuing."

2. Delegate to engineer
   PM → Engineer: "Resolve merge conflicts in PR #44

   Conflicts:
   - src/auth/login.js (both modified)
   - src/api/routes.js (both modified)

   Context: PROJ-101 added new auth flow, PROJ-102 modifying same files

   Steps:
   1. git checkout feature/PROJ-102
   2. git rebase main
   3. Resolve conflicts (preserve both changes)
   4. Run tests: npm test
   5. Force push: git push -f origin feature/PROJ-102"

3. Engineer resolves conflicts
   Engineer: "Conflicts resolved in PR #44
   - Combined auth changes from both PRs
   - Tests passing: 15/15 ✅
   - Force pushed to feature/PROJ-102"

4. PM verifies and continues
   PM → version-control: "Rebase PR #45 onto updated PR #44"
   version-control: "PR #45 rebased successfully, no conflicts"

   PM → User: "Conflicts resolved. PR #44 ready for review, PR #45 updated"
```

**Conflict Prevention**:
- Encourage smaller PRs (less conflict surface)
- Frequent rebases in stacked PRs
- Clear ownership boundaries (different files)
- Early integration testing

---

## CI/CD Integration Examples

### CI Requirement Enforcement

**Scenario**: PR created with CI checks required

```
PM → version-control: "Create PR for PROJ-123 with CI enforcement"

version-control workflow:
1. Create PR: #46 (PROJ-123 → main)
2. Trigger CI checks:
   - Linting: eslint ✅
   - Type checking: tsc ✅
   - Unit tests: jest ✅
   - Integration tests: playwright ✅
   - Build: npm run build ✅

3. Set branch protection:
   - Require CI passing before merge
   - Require 1 approval
   - Require branch up-to-date
   - Block force pushes to main

4. Report status:
   version-control → PM: "PR #46 created with CI enforcement
   - All checks passing ✅
   - Branch protection enabled
   - Ready for review (1 approval required)"

PM → User: "PR #46 ready for review
CI checks: 5/5 passing ✅
Requires 1 approval before merge"
```

**CI Failure Handling**:
```
Scenario: CI check fails

version-control: "PR #46 CI check failed: Unit tests (3 failing)"

PM → User: "PR #46 has failing tests (3/15 failing)
Blocking merge until tests pass"

PM → Engineer: "Fix failing tests in PR #46
Failed tests:
- auth.test.js: Login with invalid email
- auth.test.js: Token refresh expired
- auth.test.js: Logout clears session

Review test output and fix implementation or test expectations"

Engineer fixes tests:
Engineer: "Tests fixed, all 15/15 passing ✅"

version-control: "PR #46 CI checks now passing
Ready for review"
```

---

## Success Criteria

**PR workflow is working if**:
- ✅ PM asks user about PR strategy (main-based vs stacked)
- ✅ PM detects dependencies and recommends stacked PRs
- ✅ Draft mode matches user preference
- ✅ Auto-merge configured per user choice
- ✅ CI enforcement is enabled and respected
- ✅ Conflicts detected and resolved promptly
- ✅ PR status clearly communicated to user

**Red Flags**:
- ❌ PM creates PRs without asking user about strategy
- ❌ Stacked PRs created for independent features
- ❌ Main-based PRs created for dependent features
- ❌ Auto-merge enabled without user confirmation
- ❌ CI checks bypassed or ignored
- ❌ Conflicts not detected or left unresolved

---

## Related References

- **Version Control Agent**: See [version-control.md](version-control.md)
- **Validation Templates**: See [validation-templates.md](validation-templates.md#prworkflowtemplate)
- **Structured Questions**: See [structured-questions-examples.md](structured-questions-examples.md)

---

**Last Updated**: 2025-12-01
**Phase**: Phase 3 Optimization - Example Extraction
