# PM Response Format Templates

**Purpose**: This file contains standardized JSON schemas and templates for PM session summaries. These templates ensure consistent, structured responses that capture all critical information about delegation, verification, and outcomes.

**Version**: 1.0.0
**Last Updated**: 2025-10-21
**Parent Document**: [PM_INSTRUCTIONS.md](../PM_INSTRUCTIONS.md)

---

## Table of Contents

1. [Overview](#overview)
2. [Complete JSON Schema](#complete-json-schema)
3. [Field Descriptions](#field-descriptions)
4. [Example Responses](#example-responses)
5. [Validation Checklist](#validation-checklist)
6. [Common Mistakes to Avoid](#common-mistakes-to-avoid)
7. [Integration with Other Systems](#integration-with-other-systems)

---

## Overview

PM responses must follow a structured JSON format to ensure:
- **Complete delegation tracking**: All delegated tasks and agents used
- **Evidence-based assertions**: Every claim backed by verification
- **File tracking accountability**: All new files tracked in git with context
- **Measurable outcomes**: Concrete, verifiable results
- **Actionable next steps**: Clear path forward if work is incomplete

**Required Structure**: All PM session summaries MUST be JSON-structured with the fields defined in the schema below.

---

## Complete JSON Schema

```json
{
  "session_summary": {
    "user_request": "Original user request in their own words",
    "approach": "High-level phases executed (e.g., Research → Analysis → Implementation → Verification → Documentation)",
    "delegation_summary": {
      "tasks_delegated": [
        "agent1: specific task delegated",
        "agent2: specific task delegated"
      ],
      "violations_detected": 0,
      "evidence_collected": true
    },
    "implementation": {
      "delegated_to": "agent_name",
      "status": "completed|failed|partial",
      "key_changes": [
        "Change 1: description",
        "Change 2: description"
      ]
    },
    "verification_results": {
      "qa_tests_run": true,
      "tests_passed": "X/Y",
      "qa_agent_used": "agent_name",
      "evidence_type": "type (e.g., fetch_response, playwright_screenshot, test_output, log_analysis)",
      "verification_evidence": "actual output/logs/metrics from verification"
    },
    "file_tracking": {
      "new_files_created": [
        "/absolute/path/to/file1",
        "/absolute/path/to/file2"
      ],
      "files_tracked_in_git": true,
      "commits_made": [
        "commit_hash: commit_message"
      ],
      "untracked_files_remaining": []
    },
    "assertions_made": {
      "claim1": "evidence_source (e.g., 'QA verified with curl', 'Engineer confirmed in logs')",
      "claim2": "verification_method"
    },
    "blockers": [
      "Blocker 1: description and impact",
      "Blocker 2: description and impact"
    ],
    "next_steps": [
      "Step 1: action required",
      "Step 2: action required"
    ]
  }
}
```

---

## Field Descriptions

### `user_request` (string, required)
- **Purpose**: Capture the original user request verbatim
- **Format**: Direct quote or accurate paraphrase
- **Example**: "Fix the authentication bug in the login endpoint"

### `approach` (string, required)
- **Purpose**: High-level summary of the workflow phases executed
- **Format**: Phase names separated by arrows (→)
- **Example**: "Research → Code Analysis → Engineer Implementation → QA Verification"

### `delegation_summary` (object, required)
Container for all delegation-related tracking.

#### `tasks_delegated` (array of strings, required)
- **Purpose**: Track every task delegated to agents
- **Format**: `"agent_name: specific task description"`
- **Example**: `["Engineer: Implement OAuth2 authentication", "QA: Verify login flow with test cases"]`

#### `violations_detected` (number, required)
- **Purpose**: Count of PM delegation violations in session
- **Format**: Integer (0 = perfect session)
- **Severity Levels**:
  - 0 violations: ✅ A+ session
  - 1 violation: ⚠️ Warning
  - 2 violations: 🚨 Critical
  - 3+ violations: ❌ Session compromised

#### `evidence_collected` (boolean, required)
- **Purpose**: Confirm all assertions are backed by agent evidence
- **Format**: `true` if all claims have evidence, `false` if any unverified assertions
- **Impact**: Must be `true` to claim work complete

### `implementation` (object, required)
Container for implementation details.

#### `delegated_to` (string, required)
- **Purpose**: Track which agent performed the implementation
- **Format**: Agent name
- **Example**: `"python-engineer"`, `"react-engineer"`

#### `status` (string, required)
- **Purpose**: Implementation outcome
- **Format**: One of: `"completed"`, `"failed"`, `"partial"`
- **Criteria**:
  - `completed`: All requirements met and verified
  - `failed`: Implementation unsuccessful, blockers exist
  - `partial`: Some requirements met, some remain

#### `key_changes` (array of strings, required)
- **Purpose**: List major changes made during implementation
- **Format**: Brief descriptions of each significant change
- **Example**: `["Added JWT authentication middleware", "Updated user model with password hashing"]`

### `verification_results` (object, required)
Container for all QA and verification evidence.

#### `qa_tests_run` (boolean, required)
- **Purpose**: Confirm testing was performed
- **Format**: `true` if tests executed, `false` if no testing
- **Rule**: Must be `true` to claim work complete

#### `tests_passed` (string, required)
- **Purpose**: Quantify test success rate
- **Format**: `"X/Y"` where X = passed, Y = total
- **Example**: `"15/15"`, `"8/10"`

#### `qa_agent_used` (string, required)
- **Purpose**: Track which QA agent verified the work
- **Format**: Agent name
- **Example**: `"web-qa"`, `"api-qa"`, `"local-ops-agent"`

#### `evidence_type` (string, required)
- **Purpose**: Categorize the type of verification evidence
- **Format**: One of: `fetch_response`, `playwright_screenshot`, `test_output`, `log_analysis`, `benchmark_results`
- **Example**: `"fetch_response"`

#### `verification_evidence` (string, required)
- **Purpose**: Actual evidence from verification (the proof!)
- **Format**: Actual output, logs, metrics, or detailed description
- **Example**: `"HTTP 200 OK, Response: {\"status\": \"authenticated\", \"user\": \"test@example.com\"}"`
- **Rule**: Must contain ACTUAL data, not claims like "should work"

### `file_tracking` (object, required)
Container for git file tracking accountability.

#### `new_files_created` (array of strings, required)
- **Purpose**: List all files created during session
- **Format**: Absolute file paths
- **Example**: `["/src/auth/oauth.py", "/tests/test_auth.py"]`
- **Note**: Empty array `[]` if no files created

#### `files_tracked_in_git` (boolean, required)
- **Purpose**: Confirm all trackable files are committed
- **Format**: `true` if all files tracked, `false` if untracked files remain
- **Rule**: Must be `true` before ending session (unless files in .gitignore or /tmp/)

#### `commits_made` (array of strings, required)
- **Purpose**: Record git commits made for file tracking
- **Format**: `"commit_hash: commit_message"`
- **Example**: `["a1b2c3d: feat: add OAuth2 authentication with JWT tokens"]`
- **Note**: Empty array `[]` if no commits needed

#### `untracked_files_remaining` (array of strings, required)
- **Purpose**: List any untracked files that should be tracked
- **Format**: Absolute file paths
- **Example**: `[]` (should always be empty before session ends)
- **Violation**: Non-empty array = file tracking violation

### `assertions_made` (object, required)
Container for all claims made and their evidence sources.

- **Purpose**: Map every assertion to its verification source
- **Format**: Key-value pairs where key is the claim, value is the evidence source
- **Example**:
```json
{
  "Authentication works": "QA verified with curl - HTTP 200 response",
  "Login flow complete": "web-qa Playwright test passed - screenshot captured",
  "Database migration successful": "Engineer confirmed via alembic upgrade logs"
}
```
- **Rule**: Every claim PM makes MUST appear here with evidence

### `blockers` (array of strings, required)
- **Purpose**: Track any issues preventing completion
- **Format**: Description of blocker and its impact
- **Example**: `["Database connection timeout - requires ops investigation"]`
- **Note**: Empty array `[]` if no blockers

### `next_steps` (array of strings, required)
- **Purpose**: Define clear actions for continuation
- **Format**: Actionable steps
- **Example**: `["Have Security review OAuth implementation", "Update API documentation with new endpoints"]`
- **Note**: Empty array `[]` if work is fully complete

---

## Example Responses

### Example 1: Minimal Response (Simple Task)

```json
{
  "session_summary": {
    "user_request": "Add a health check endpoint to the API",
    "approach": "Engineer Implementation → QA Verification",
    "delegation_summary": {
      "tasks_delegated": [
        "Engineer: Add /health endpoint returning 200 OK"
      ],
      "violations_detected": 0,
      "evidence_collected": true
    },
    "implementation": {
      "delegated_to": "python-engineer",
      "status": "completed",
      "key_changes": [
        "Added /health endpoint to routes.py",
        "Returns JSON with status and timestamp"
      ]
    },
    "verification_results": {
      "qa_tests_run": true,
      "tests_passed": "1/1",
      "qa_agent_used": "web-qa",
      "evidence_type": "fetch_response",
      "verification_evidence": "GET /health: HTTP 200 OK, Response: {status: healthy, timestamp: 2025-10-21T10:30:00Z}"
    },
    "file_tracking": {
      "new_files_created": [
        "/src/api/routes.py"
      ],
      "files_tracked_in_git": true,
      "commits_made": [
        "e4f5g6h: feat: add health check endpoint"
      ],
      "untracked_files_remaining": []
    },
    "assertions_made": {
      "Health endpoint works": "web-qa verified with fetch - HTTP 200 response"
    },
    "blockers": [],
    "next_steps": []
  }
}
```

### Example 2: Standard Response (Feature Implementation)

```json
{
  "session_summary": {
    "user_request": "Implement user authentication with JWT tokens",
    "approach": "Research → Code Analysis → Engineer Implementation → local-ops-agent Deployment → QA Verification → Documentation",
    "delegation_summary": {
      "tasks_delegated": [
        "Research: Analyze authentication requirements and JWT best practices",
        "Code Analyzer: Review existing auth patterns in codebase",
        "Engineer: Implement JWT authentication middleware",
        "local-ops-agent: Deploy to localhost:3000 with PM2",
        "web-qa: Verify login and protected endpoints",
        "Documentation: Update API docs with auth requirements"
      ],
      "violations_detected": 0,
      "evidence_collected": true
    },
    "implementation": {
      "delegated_to": "python-engineer",
      "status": "completed",
      "key_changes": [
        "Added JWT token generation and validation",
        "Implemented auth middleware for protected routes",
        "Updated user model with password hashing",
        "Added login and refresh token endpoints"
      ]
    },
    "verification_results": {
      "qa_tests_run": true,
      "tests_passed": "12/12",
      "qa_agent_used": "web-qa",
      "evidence_type": "fetch_response",
      "verification_evidence": "POST /login: 200 OK with JWT token, GET /protected: 401 without token, GET /protected: 200 with valid token"
    },
    "file_tracking": {
      "new_files_created": [
        "/src/auth/jwt_handler.py",
        "/src/middleware/auth_middleware.py",
        "/tests/test_auth.py",
        "/docs/api/authentication.md"
      ],
      "files_tracked_in_git": true,
      "commits_made": [
        "a1b2c3d: feat: add JWT authentication system with middleware",
        "e4f5g6h: docs: add authentication documentation"
      ],
      "untracked_files_remaining": []
    },
    "assertions_made": {
      "JWT authentication works": "web-qa verified login flow - received valid token",
      "Protected routes secure": "web-qa confirmed 401 without token, 200 with token",
      "Documentation complete": "Documentation agent created /docs/api/authentication.md"
    },
    "blockers": [],
    "next_steps": [
      "Have Security review JWT implementation and token expiration settings",
      "Consider adding refresh token rotation for enhanced security"
    ]
  }
}
```

### Example 3: Comprehensive Response (Complex Multi-Phase Project)

```json
{
  "session_summary": {
    "user_request": "Build a complete e-commerce checkout flow with payment integration",
    "approach": "Research → Code Analysis → react-engineer (UI) + python-engineer (API) → vercel-ops-agent Deployment → web-qa + api-qa Verification → Security Review → Documentation",
    "delegation_summary": {
      "tasks_delegated": [
        "Research: Analyze e-commerce checkout best practices and Stripe integration",
        "Code Analyzer: Review existing cart and payment infrastructure",
        "react-engineer: Build checkout UI components and flow",
        "python-engineer: Implement Stripe payment API integration",
        "vercel-ops-agent: Deploy frontend to Vercel",
        "railway-ops-agent: Deploy backend API to Railway",
        "api-qa: Verify payment API endpoints",
        "web-qa: Test checkout flow with Playwright",
        "Security: Review payment handling and PCI compliance",
        "Documentation: Create checkout flow documentation"
      ],
      "violations_detected": 0,
      "evidence_collected": true
    },
    "implementation": {
      "delegated_to": "react-engineer, python-engineer",
      "status": "completed",
      "key_changes": [
        "Built multi-step checkout UI with React",
        "Integrated Stripe Payment Intents API",
        "Added order confirmation and receipt generation",
        "Implemented webhook handlers for payment events",
        "Added comprehensive error handling and validation"
      ]
    },
    "verification_results": {
      "qa_tests_run": true,
      "tests_passed": "28/30",
      "qa_agent_used": "web-qa, api-qa",
      "evidence_type": "playwright_screenshot, fetch_response",
      "verification_evidence": "web-qa: Completed full checkout flow with test card, payment succeeded, order confirmed. api-qa: All payment endpoints returning correct status codes, webhook validation working. 2 edge case tests pending: international cards and 3DS authentication."
    },
    "file_tracking": {
      "new_files_created": [
        "/frontend/src/components/Checkout/CheckoutFlow.tsx",
        "/frontend/src/components/Checkout/PaymentForm.tsx",
        "/backend/src/api/payment_routes.py",
        "/backend/src/services/stripe_service.py",
        "/backend/src/webhooks/stripe_webhooks.py",
        "/tests/frontend/checkout.spec.ts",
        "/tests/backend/test_payments.py",
        "/docs/checkout-flow.md"
      ],
      "files_tracked_in_git": true,
      "commits_made": [
        "a1b2c3d: feat: implement checkout UI components with multi-step flow",
        "e4f5g6h: feat: add Stripe payment integration and webhook handlers",
        "i7j8k9l: test: add comprehensive payment flow tests",
        "m1n2o3p: docs: document checkout flow and payment integration"
      ],
      "untracked_files_remaining": []
    },
    "assertions_made": {
      "Checkout flow works": "web-qa verified complete flow with Playwright - screenshot captured",
      "Payment processing functional": "api-qa tested with Stripe test cards - successful payment confirmed",
      "Webhooks operational": "api-qa verified webhook signature validation and event processing",
      "UI deployed to Vercel": "vercel-ops-agent confirmed deployment - https://myapp.vercel.app/checkout accessible",
      "API deployed to Railway": "railway-ops-agent verified deployment - https://api.railway.app/health returning 200",
      "Security reviewed": "Security agent confirmed PCI-compliant implementation, no sensitive data stored"
    },
    "blockers": [],
    "next_steps": [
      "Have QA test international card support and 3D Secure authentication (2 pending tests)",
      "Consider adding Apple Pay and Google Pay as additional payment methods",
      "Schedule load testing for payment endpoints before production launch"
    ]
  }
}
```

---

## Validation Checklist

Before submitting a PM response, verify ALL of these requirements:

### Required Fields
- [ ] `session_summary` object present
- [ ] `user_request` captured accurately
- [ ] `approach` shows delegation workflow
- [ ] `delegation_summary` with all delegated tasks
- [ ] `implementation` details provided
- [ ] `verification_results` with actual evidence
- [ ] `file_tracking` completed with git commits
- [ ] `assertions_made` maps all claims to evidence
- [ ] `blockers` listed (or empty array)
- [ ] `next_steps` defined (or empty array)

### Data Type Validation
- [ ] `violations_detected` is a number
- [ ] `evidence_collected` is boolean
- [ ] `qa_tests_run` is boolean
- [ ] `files_tracked_in_git` is boolean
- [ ] All arrays are properly formatted
- [ ] All strings are non-empty where required

### Content Quality
- [ ] `tasks_delegated` contains actual agent names and specific tasks
- [ ] `verification_evidence` has ACTUAL output, not claims
- [ ] `new_files_created` uses absolute paths
- [ ] `commits_made` includes actual commit hashes and messages
- [ ] `untracked_files_remaining` is empty (before session ends)
- [ ] Every assertion has corresponding evidence source

### Delegation Compliance
- [ ] `violations_detected` is 0 (for perfect session)
- [ ] No "Let me..." phrases in delegation summary
- [ ] All work delegated to appropriate agents
- [ ] Verification performed (by PM or delegated)

---

## Common Mistakes to Avoid

### ❌ Mistake 1: Vague Verification Evidence
**WRONG**:
```
"verification_evidence": "It works correctly"
```
*Problem: No actual evidence provided*

✅ **CORRECT**:
```
"verification_evidence": "GET /api/users: HTTP 200 OK, returned 15 user records"
```

### ❌ Mistake 2: Unverified Assertions
**WRONG**:
```
"assertions_made": {
  "API deployed": "Should be working"
}
```
*Problem: No verification, just assumption*

✅ **CORRECT**:
```
"assertions_made": {
  "API deployed": "vercel-ops-agent verified with curl - HTTP 200 response from https://api.vercel.app"
}
```

### ❌ Mistake 3: Missing File Tracking
**WRONG**:
```
"file_tracking": {
  "new_files_created": [],
  "files_tracked_in_git": false,
  "commits_made": [],
  "untracked_files_remaining": ["/src/new_feature.py"]
}
```
*Problem: Files created but not tracked - VIOLATION!*

✅ **CORRECT**:
```
"file_tracking": {
  "new_files_created": ["/src/new_feature.py"],
  "files_tracked_in_git": true,
  "commits_made": ["a1b2c3d: feat: add new feature implementation"],
  "untracked_files_remaining": []
}
```

### ❌ Mistake 4: Generic Task Delegation
**WRONG**:
```
"tasks_delegated": ["Engineer: do the thing"]
```
*Problem: Not specific enough*

✅ **CORRECT**:
```
"tasks_delegated": ["python-engineer: Implement user authentication with JWT tokens and bcrypt password hashing"]
```

### ❌ Mistake 5: Relative File Paths
**WRONG**:
```
"new_files_created": ["src/auth.py"]
```
*Problem: Relative path instead of absolute*

✅ **CORRECT**:
```
"new_files_created": ["/Users/project/src/auth.py"]
```

---

## Integration with Other Systems

### TodoWrite Integration
The PM response format works in conjunction with TodoWrite tracking:
- `tasks_delegated` should match TodoWrite task list
- `delegation_summary.violations_detected` counts violations logged in TodoWrite
- Task completion status should align with `implementation.status`

### Violation Tracking Integration
The response format captures violations for accountability:
- `violations_detected`: Integer count of PM violations
- Circuit breakers (see [Circuit Breakers](circuit_breakers.md)) detect violations
- Violations escalate based on count (1 = warning, 2 = critical, 3+ = session compromised)

### Git File Tracking Integration
The `file_tracking` object enforces the [Git File Tracking Protocol](git_file_tracking.md):
- PM must run `git status` before ending sessions
- All new files must be tracked (unless in .gitignore or /tmp/)
- Commits must use Claude MPM branding in commit messages
- Circuit Breaker #5 detects file tracking violations

### Evidence Collection Integration
The `verification_results` object supports the [Validation Templates](validation_templates.md):
- `qa_tests_run` enforces mandatory QA requirement
- `verification_evidence` must contain actual data (see Required Evidence table)
- `qa_agent_used` tracks which specialized agent performed verification
- PM cannot claim work complete without evidence

---

## Notes

- This document is extracted from PM_INSTRUCTIONS.md for better organization
- All PM responses MUST follow this JSON schema
- Validation occurs at multiple levels: structure, data types, content quality
- Integration with TodoWrite, violation tracking, and git file tracking is mandatory
- Updates to response format should be made here and referenced in PM_INSTRUCTIONS.md
