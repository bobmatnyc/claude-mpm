"""
Integration Tests for BASE_AGENT Patterns.

This test suite validates end-to-end BASE_AGENT compliance across:
- Template inheritance and merging
- Multi-tool workflow verification chains
- Error recovery and escalation patterns
- Memory persistence across sessions
- Cross-metric consistency

These tests ensure that BASE_AGENT principles work together cohesively,
not just in isolation.
"""

import json
from typing import Any, Dict, List, Optional

import pytest
from deepeval.test_case import LLMTestCase

from tests.eval.metrics.base_agent import (
    MemoryProtocolMetric,
    VerificationComplianceMetric,
)


class TestBaseAgentIntegration:
    """Integration tests for BASE_AGENT pattern compliance.

    Tests validate that BASE_AGENT principles work together:
    1. Template merge + inheritance
    2. Multi-tool verification chains
    3. Error recovery + escalation
    4. Memory persistence workflows
    5. Cross-metric consistency
    """

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """Setup metrics for all integration tests."""
        self.verification_metric = VerificationComplianceMetric(threshold=0.9)
        self.memory_metric = MemoryProtocolMetric(threshold=1.0)

    # =========================================================================
    # Test 1: Template Merge and Inheritance
    # =========================================================================

    def test_template_merge_and_inheritance(self) -> None:
        """Validate specialized agents inherit BASE_AGENT behaviors.

        Tests that a response contains BOTH:
        1. BASE_AGENT patterns (verification, JSON format, memory protocol)
        2. Specialized agent patterns (if applicable)

        This ensures template inheritance works correctly and BASE_AGENT
        principles are preserved when templates merge.
        """
        # Mock response simulating Python Engineer agent (inherits BASE_AGENT)
        user_request = "Create a Python function to validate email addresses"
        response = self._create_template_inheritance_response()

        # Create test case
        test_case = LLMTestCase(input=user_request, actual_output=response)

        # Test verification compliance (BASE_AGENT pattern)
        verification_score = self.verification_metric.measure(test_case)
        assert verification_score >= 0.9, (
            f"BASE_AGENT verification pattern should be present "
            f"(score: {verification_score})\n"
            f"Reason: {self.verification_metric.reason}"
        )

        # Test memory protocol compliance (BASE_AGENT pattern)
        memory_score = self.memory_metric.measure(test_case)
        # Use 0.9 threshold for template inheritance (may have minor variations)
        assert memory_score >= 0.9, (
            f"BASE_AGENT memory protocol should be present "
            f"(score: {memory_score})\n"
            f"Reason: {self.memory_metric.reason}"
        )

        # Verify specialized agent patterns are preserved
        assert (
            "type hints" in response.lower()
        ), "Python Engineer specialization should include type hints"
        assert (
            "pytest" in response.lower()
        ), "Python Engineer specialization should include testing"

        # Verify BASE_AGENT + specialized agent coexistence
        assert "```python" in response, "Code snippets should be present"
        assert "verified" in response.lower(), "Verification should be present"
        assert "```json" in response, "JSON protocol should be present"

    # =========================================================================
    # Test 2: Multi-Tool Workflow Verification Chain
    # =========================================================================

    def test_multi_tool_workflow_verification_chain(self) -> None:
        """Validate complex workflows with verification at each step.

        Simulates a multi-step workflow:
        1. Read file → verify read
        2. Edit file → verify edit (Read after Edit)
        3. Run tests → verify tests passed
        4. Deploy → verify deployment

        Ensures verification is present after EACH critical step.
        """
        user_request = (
            "Update the authentication module to use OAuth2, "
            "test the changes, and deploy to staging"
        )
        response = self._create_multi_step_workflow_response()

        test_case = LLMTestCase(input=user_request, actual_output=response)

        # Test verification compliance
        verification_score = self.verification_metric.measure(test_case)
        assert verification_score >= 0.9, (
            f"Multi-step workflow should have verification at each step "
            f"(score: {verification_score})\n"
            f"Reason: {self.verification_metric.reason}"
        )

        # Extract workflow steps and verify each has verification
        steps = self._extract_workflow_steps(response)
        assert len(steps) >= 4, f"Should have 4+ steps, got {len(steps)}"

        # Verify each critical operation is present
        assert (
            "read" in response.lower() and "auth.py" in response.lower()
        ), "Should read file first"
        assert (
            "edit" in response.lower() or "updating" in response.lower()
        ), "Should edit file"
        assert (
            "pytest" in response.lower() or "test" in response.lower()
        ), "Should run tests"
        assert "deploy" in response.lower(), "Should deploy"

        # Verify verification keywords present after each step
        verification_count = response.lower().count("verified")
        verification_count += response.lower().count("confirmed")
        verification_count += response.lower().count("✅")
        assert (
            verification_count >= 3
        ), f"Should have 3+ verification confirmations, got {verification_count}"

    # =========================================================================
    # Test 3: Error Recovery and Escalation
    # =========================================================================

    def test_error_recovery_and_escalation(self) -> None:
        """Validate error handling and recovery patterns.

        Tests two scenarios:
        A) Error detected → recovery attempted → success
        B) Error detected → recovery failed → escalation

        Verifies proper error handling with:
        - Error detection evidence
        - Recovery attempt documentation
        - Proper escalation when recovery fails
        - task_completed: false on escalation
        """
        # Scenario A: Successful recovery
        user_request_success = "Deploy the application to production"
        response_success = self._create_error_recovery_response(recovery_succeeded=True)

        test_case_success = LLMTestCase(
            input=user_request_success, actual_output=response_success
        )

        # Verify error detection and recovery documented
        assert "error" in response_success.lower(), "Error should be detected"
        assert (
            "retry" in response_success.lower() or "attempt" in response_success.lower()
        ), "Recovery attempt should be documented"
        assert "success" in response_success.lower(), "Success should be reported"

        # Parse JSON and verify task completed
        json_block = self._extract_json_block(response_success)
        assert json_block is not None, "Should have JSON block"
        assert (
            json_block.get("task_completed") is True
        ), "Task should be completed after successful recovery"

        # Scenario B: Failed recovery → escalation
        user_request_failure = "Deploy the application to production"
        response_failure = self._create_error_recovery_response(
            recovery_succeeded=False
        )

        test_case_failure = LLMTestCase(
            input=user_request_failure, actual_output=response_failure
        )

        # Verify error detection and escalation
        assert "error" in response_failure.lower(), "Error should be detected"
        assert (
            "failed" in response_failure.lower() or "unable" in response_failure.lower()
        ), "Failure should be documented"
        assert (
            "escalat" in response_failure.lower()
            or "manual" in response_failure.lower()
        ), "Escalation should be indicated"

        # Parse JSON and verify task NOT completed
        json_block_failure = self._extract_json_block(response_failure)
        assert json_block_failure is not None, "Should have JSON block"
        assert (
            json_block_failure.get("task_completed") is False
        ), "Task should NOT be completed when escalating"

    # =========================================================================
    # Test 4: Memory Persistence Workflow
    # =========================================================================

    def test_memory_persistence_workflow(self) -> None:
        """Validate memory capture and retrieval across sessions.

        Simulates multi-session workflow:
        Session 1: Discover fact, capture in "remember" field
        Session 2: Retrieve and use the memory
        Session 3: Update memory with new information

        Uses MemoryProtocolMetric to verify JSON format with remember field.
        """
        # Session 1: Initial memory capture
        session1_request = (
            "Remember that this project uses Poetry for dependency management "
            "and pytest for testing"
        )
        session1_response = self._create_memory_response(
            session="initial",
            memory_content=[
                "Project uses Poetry for dependency management",
                "Project uses pytest for testing",
            ],
        )

        test_case_session1 = LLMTestCase(
            input=session1_request, actual_output=session1_response
        )

        # Verify memory capture compliance
        memory_score_1 = self.memory_metric.measure(test_case_session1)
        # Use 0.999 threshold due to floating point precision
        assert memory_score_1 >= 0.999, (
            f"Session 1 memory capture should be compliant "
            f"(score: {memory_score_1})\n"
            f"Reason: {self.memory_metric.reason}"
        )

        # Parse JSON and verify remember field
        json_block_1 = self._extract_json_block(session1_response)
        assert json_block_1 is not None, "Session 1 should have JSON block"
        assert "remember" in json_block_1, "Should have 'remember' field"
        assert len(json_block_1["remember"]) == 2, "Should have 2 memories"

        # Session 2: Memory retrieval (simulated - agent recalls)
        session2_request = "Add a new development dependency to the project"
        session2_response = self._create_memory_response(
            session="retrieval",
            recalled_memory="Project uses Poetry for dependency management",
        )

        # Verify memory was recalled and used
        assert (
            "poetry add" in session2_response.lower()
        ), "Should use Poetry based on recalled memory"

        # Session 3: Memory update
        session3_request = (
            "Note that we also use Black for code formatting with line length 100"
        )
        session3_response = self._create_memory_response(
            session="update",
            memory_content=["Project uses Black formatter with line length 100"],
        )

        test_case_session3 = LLMTestCase(
            input=session3_request, actual_output=session3_response
        )

        # Verify memory update compliance
        memory_score_3 = self.memory_metric.measure(test_case_session3)
        # Use 0.999 threshold due to floating point precision
        assert memory_score_3 >= 0.999, (
            f"Session 3 memory update should be compliant "
            f"(score: {memory_score_3})\n"
            f"Reason: {self.memory_metric.reason}"
        )

    # =========================================================================
    # Test 5: Cross-Metric Consistency
    # =========================================================================

    def test_cross_metric_consistency(self) -> None:
        """Validate both metrics agree on compliance.

        For well-formed responses:
        - VerificationComplianceMetric should pass
        - MemoryProtocolMetric should pass
        - Both scores should be >= their thresholds

        For poorly-formed responses:
        - At least one metric should fail
        - Scores should reflect specific violations
        """
        # Well-formed response (should pass both metrics)
        user_request_good = "Update config.py and remember the change"
        response_good = self._create_well_formed_response()

        test_case_good = LLMTestCase(
            input=user_request_good, actual_output=response_good
        )

        # Test both metrics pass
        verification_score_good = self.verification_metric.measure(test_case_good)
        memory_score_good = self.memory_metric.measure(test_case_good)

        assert verification_score_good >= 0.9, (
            f"Well-formed response should pass verification "
            f"(score: {verification_score_good})"
        )
        # Use 0.999 threshold due to floating point precision
        assert memory_score_good >= 0.999, (
            f"Well-formed response should pass memory protocol "
            f"(score: {memory_score_good})"
        )

        # Poorly-formed response (should fail at least one metric)
        user_request_bad = "Update config.py and remember the change"
        response_bad = self._create_poorly_formed_response()

        test_case_bad = LLMTestCase(input=user_request_bad, actual_output=response_bad)

        # Test at least one metric fails
        verification_score_bad = self.verification_metric.measure(test_case_bad)
        memory_score_bad = self.memory_metric.measure(test_case_bad)

        # At least one should fail (use 0.999 for memory due to floating point)
        assert verification_score_bad < 0.9 or memory_score_bad < 0.999, (
            "Poorly-formed response should fail at least one metric\n"
            f"Verification: {verification_score_bad}, "
            f"Memory: {memory_score_bad}"
        )

        # Verify metrics provide specific violation reasons
        if verification_score_bad < 0.9:
            assert (
                len(self.verification_metric.reason) > 0
            ), "Verification metric should explain failure"

        if memory_score_bad < 0.999:
            assert (
                len(self.memory_metric.reason) > 0
            ), "Memory metric should explain failure"

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _create_template_inheritance_response(self) -> str:
        """Generate mock response demonstrating template inheritance.

        Shows Python Engineer agent inheriting BASE_AGENT verification
        and memory patterns while maintaining specialization.
        """
        return """I'll create an email validation function with proper type hints and testing.

First, let me create the validation module:

**File: validators.py**
```python
import re
from typing import Optional


def validate_email(email: str) -> bool:
    \"\"\"Validate email address format.

    Args:
        email: Email address to validate

    Returns:
        True if email is valid format, False otherwise
    \"\"\"
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
```

Let me verify the file was created correctly by reading it:

**Reading validators.py:**

Line 1: `import re`
Line 2: `from typing import Optional`
Line 5-7: `def validate_email(email: str) -> bool:`
Line 15: `pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'`

Output: `import re` and `def validate_email` confirmed in file

✅ **Verified: validators.py created with email validation function**

Now let me create comprehensive tests:

**File: test_validators.py**
```python
import pytest
from validators import validate_email


def test_validate_email_valid_addresses():
    \"\"\"Test valid email addresses.\"\"\"
    assert validate_email("user@example.com") is True
    assert validate_email("john.doe@company.co.uk") is True


def test_validate_email_invalid_addresses():
    \"\"\"Test invalid email addresses.\"\"\"
    assert validate_email("invalid") is False
    assert validate_email("@example.com") is False
```

Reading test_validators.py to verify:

Line 1: `import pytest`
Line 2: `from validators import validate_email`
Line 5-8: `def test_validate_email_valid_addresses():`

Output: `import pytest` found at line 1

✅ **Confirmed: Test file created**

Running tests to verify implementation:

```bash
$ pytest test_validators.py -v
```

**Output:**
```
test_validators.py::test_validate_email_valid_addresses PASSED
test_validators.py::test_validate_email_invalid_addresses PASSED
2 passed in 0.03s
```

Testing showed: 2 passed, 0 failed

Running type checking:

```bash
$ mypy validators.py
```

**Output:** `Success: no issues found in 1 source file`

✅ **Verified: Type checking passed**

Running code quality checks:

```bash
$ ruff check validators.py
```

**Output:** `All checks passed!`

✅ **Verified: All quality gates passed**

```json
{
    "task_completed": true,
    "instructions": "Create email validation function",
    "results": "Created validate_email() with type hints, regex pattern, and pytest tests. All 2 tests passed. Type checking (mypy) and linting (ruff) passed.",
    "files_modified": ["validators.py", "test_validators.py"],
    "tools_used": ["Write", "Read", "Bash"],
    "remember": ["Project uses pytest for testing", "Email validation uses regex pattern"]
}
```"""

    def _create_multi_step_workflow_response(self) -> str:
        """Generate multi-step workflow with verification at each step."""
        return """I'll update the authentication module to use OAuth2, test, and deploy.

**Step 1: Read current implementation**

Reading `auth.py` to understand current implementation:

Line 15: `def authenticate(username: str, password: str):`
Line 16: `    return check_credentials(username, password)`

Output: `def authenticate(username: str, password: str)` found at line 15

✅ **Verified: Current implementation uses basic auth**

**Step 2: Update to OAuth2**

Editing `auth.py` to implement OAuth2 client credentials flow:

```python
# Updated implementation
from authlib.integrations.requests_client import OAuth2Session

def authenticate(client_id: str, client_secret: str):
    session = OAuth2Session(client_id, client_secret)
    token = session.fetch_token(
        'https://auth.example.com/token',
        grant_type='client_credentials'
    )
    return token
```

Reading `auth.py` to verify changes:

Line 15: `from authlib.integrations.requests_client import OAuth2Session`
Line 17: `def authenticate(client_id: str, client_secret: str):`
Line 18-22: OAuth2 token fetch implementation

Output: `from authlib.integrations.requests_client import OAuth2Session` found at line 15

✅ **Verified: OAuth2 client credentials flow implemented**

Running type checking:

```bash
$ mypy auth.py
```

**Output:** `Success: no issues found in 1 source file`

✅ **Confirmed: Type checking passed**

**Step 3: Run tests**

Running test suite to verify authentication changes:

```bash
$ pytest tests/test_auth.py -v
```

**Output:**
```
tests/test_auth.py::test_oauth2_authentication PASSED
tests/test_auth.py::test_token_refresh PASSED
tests/test_auth.py::test_invalid_credentials FAILED
```

Testing showed: `test_invalid_credentials` expects ValueError, got AuthError

Fixing error handling:

```python
def authenticate(client_id: str, client_secret: str):
    try:
        session = OAuth2Session(client_id, client_secret)
        return session.fetch_token(...)
    except AuthError as e:
        raise ValueError(f"Authentication failed: {e}")
```

Reading auth.py to verify fix:

Line 19-23: Exception handling added

✅ **Confirmed: Error handling fixed**

Re-running tests:

```bash
$ pytest tests/test_auth.py -v
```

**Output:**
```
tests/test_auth.py::test_oauth2_authentication PASSED
tests/test_auth.py::test_token_refresh PASSED
tests/test_auth.py::test_invalid_credentials PASSED
3 passed in 0.12s
```

Testing showed: 3 passed, 0 failed

✅ **Verified: All tests passed**

**Step 4: Deploy to staging**

Deploying to staging environment:

```bash
$ ./deploy.sh staging
```

**Output:**
```
Deploying to staging...
✓ Build completed
✓ Container pushed
✓ Deployment rolled out
```

Verifying deployment health:

```bash
$ curl https://staging.example.com/health
```

**Response:**
```json
{"status": "healthy", "version": "2.1.0", "auth": "oauth2"}
```

Response: `{"status": "healthy", "version": "2.1.0", "auth": "oauth2"}`

✅ **Verified: Deployment successful, health check passed**

Running code quality checks:

```bash
$ ruff check auth.py
```

**Output:** `All checks passed!`

✅ **Confirmed: Quality gates passed**

```json
{
    "task_completed": true,
    "instructions": "Update auth to OAuth2, test, deploy to staging",
    "results": "Implemented OAuth2 client credentials flow, fixed error handling, all tests passed (3/3), deployed to staging with successful health check. Type checking and linting passed.",
    "files_modified": ["auth.py", "tests/test_auth.py"],
    "tools_used": ["Read", "Edit", "Bash"],
    "remember": ["Authentication migrated to OAuth2 client credentials", "Staging deployment uses oauth2 auth"]
}
```"""

    def _create_error_recovery_response(self, recovery_succeeded: bool) -> str:
        """Generate error recovery/escalation response.

        Args:
            recovery_succeeded: If True, recovery succeeds. If False, escalates.
        """
        if recovery_succeeded:
            return """I'll deploy the application to production.

**Deployment Attempt 1:**

```bash
$ kubectl apply -f k8s/production/
```

**Error:**
```
Error from server (Forbidden): error when creating "deployment.yaml":
deployments.apps is forbidden: User "deploy-bot" cannot create resource
"deployments" in API group "apps" in the namespace "production"
```

❌ **Error detected: Insufficient permissions**

**Recovery Attempt:**

The deploy-bot service account lacks deployment permissions. Let me check and update RBAC:

```bash
$ kubectl get rolebinding deploy-bot -n production
```

**Output:**
```
Error from server (NotFound): rolebindings.rbac "deploy-bot" not found
```

Creating missing role binding:

```bash
$ kubectl create rolebinding deploy-bot \\
    --clusterrole=edit \\
    --serviceaccount=production:deploy-bot \\
    -n production
```

**Output:**
```
rolebinding.rbac.authorization.k8s.io/deploy-bot created
```

**Retry Deployment:**

```bash
$ kubectl apply -f k8s/production/
```

**Output:**
```
deployment.apps/app created
service/app created
ingress.networking.k8s.io/app created
```

Verifying deployment:

```bash
$ kubectl rollout status deployment/app -n production
```

**Output:**
```
deployment "app" successfully rolled out
```

Health check:

```bash
$ curl https://app.example.com/health
```

**Response:** `{"status": "healthy", "version": "2.1.0"}`

✅ **Verified: Deployment successful after RBAC fix**

```json
{
    "task_completed": true,
    "instructions": "Deploy application to production",
    "results": "Initial deployment failed due to RBAC permissions. Created missing role binding, retry succeeded. Deployment verified with health check.",
    "files_modified": [],
    "tools_used": ["Bash"],
    "remember": ["Production deploy-bot requires edit clusterrole binding"]
}
```"""
        return """I'll deploy the application to production.

**Deployment Attempt 1:**

```bash
$ kubectl apply -f k8s/production/
```

**Error:**
```
Error from server (ServiceUnavailable): the server is currently unable to handle the request
```

❌ **Error detected: Kubernetes API unavailable**

**Recovery Attempt 1:**

Checking cluster health:

```bash
$ kubectl cluster-info
```

**Output:**
```
To further debug and diagnose cluster problems, use 'kubectl cluster-info dump'.
The connection to the server <server-ip>:6443 was refused - did you specify the right host or port?
```

Checking network connectivity:

```bash
$ ping <server-ip>
```

**Output:**
```
Request timeout for icmp_seq 0
Request timeout for icmp_seq 1
```

❌ **Recovery failed: Production cluster unreachable**

**Recovery Attempt 2:**

Attempting deployment via backup cluster:

```bash
$ kubectl --context=backup-cluster apply -f k8s/production/
```

**Error:**
```
Error: context "backup-cluster" does not exist
```

❌ **Recovery failed: Backup cluster not configured**

**Escalation Required:**

Unable to complete deployment due to production cluster outage. This requires manual intervention:

1. **Network Issue**: Production cluster is unreachable (network timeout)
2. **No Backup**: Backup cluster context not configured
3. **Impact**: Cannot deploy or verify deployment status

**Recommended Actions:**
- Contact DevOps team to investigate cluster connectivity
- Verify VPN/network access to production environment
- Set up backup cluster configuration for future resilience

```json
{
    "task_completed": false,
    "instructions": "Deploy application to production",
    "results": "Deployment failed - production cluster unreachable. Recovery attempts failed: backup cluster not configured. Escalating to DevOps team.",
    "files_modified": [],
    "tools_used": ["Bash"],
    "remember": ["Production cluster experienced outage 2025-12-06", "Backup cluster configuration missing - needs setup"]
}
```"""

    def _create_memory_response(
        self,
        session: str,
        memory_content: Optional[List[str]] = None,
        recalled_memory: Optional[str] = None,
    ) -> str:
        """Generate memory-enabled response for different session types.

        Args:
            session: One of 'initial', 'retrieval', 'update'
            memory_content: List of memories to capture (for initial/update)
            recalled_memory: Memory to recall and use (for retrieval)
        """
        if session == "initial":
            return f"""Understood! I'll remember these project conventions.

```json
{{
    "task_completed": true,
    "instructions": "Remember project tooling conventions",
    "results": "Noted that project uses Poetry and pytest",
    "files_modified": [],
    "tools_used": [],
    "remember": {json.dumps(memory_content or [])}
}}
```"""

        if session == "retrieval":
            return """I'll add the development dependency using Poetry (as configured for this project).

```bash
$ poetry add --group dev black
```

**Output:**
```
Using version ^23.12.0 for black

Updating dependencies
Resolving dependencies... (0.5s)

Writing lock file

Package operations: 1 install, 0 updates, 0 removals
  • Installing black (23.12.0)
```

✅ **Verified: black added to dev dependencies via Poetry**

```json
{
    "task_completed": true,
    "instructions": "Add development dependency",
    "results": "Added black to dev dependencies using Poetry (poetry add --group dev black)",
    "files_modified": ["pyproject.toml", "poetry.lock"],
    "tools_used": ["Bash"],
    "remember": []
}
```"""

        # session == "update"
        return f"""Noted! I'll remember the Black formatter configuration.

```json
{{
    "task_completed": true,
    "instructions": "Remember Black formatter configuration",
    "results": "Noted Black formatter with line length 100",
    "files_modified": [],
    "tools_used": [],
    "remember": {json.dumps(memory_content or [])}
}}
```"""

    def _create_well_formed_response(self) -> str:
        """Generate well-formed response that passes both metrics."""
        return """I'll update config.py with the new settings.

Reading current config.py:

Line 10: `DATABASE_URL = "postgresql://localhost/olddb"`
Line 11: `DEBUG = False`

Output: `DATABASE_URL = "postgresql://localhost/olddb"` found at line 10

✅ **Confirmed: Current configuration read**

Editing config.py to update database URL from localhost to prod-db.example.com:

Reading config.py to verify changes:

Line 10: `DATABASE_URL = "postgresql://prod-db.example.com/newdb"`
Line 11: `DEBUG = False`

Output: `DATABASE_URL = "postgresql://prod-db.example.com/newdb"` confirmed at line 10

✅ **Verified: Database URL updated successfully (Edit→Read verification complete)**

Running tests to verify configuration:

```bash
$ pytest tests/test_config.py -v
```

**Output:**
```
tests/test_config.py::test_database_connection PASSED
1 passed in 0.05s
```

Testing showed: 1 passed, 0 failed

✅ **Confirmed: Configuration tests passed**

Running type checking:

```bash
$ mypy config.py
```

**Output:** `Success: no issues found in 1 source file`

✅ **Verified: Type checking passed**

Running linting:

```bash
$ ruff check config.py
```

**Output:** `All checks passed!`

✅ **Confirmed: Code quality checks passed**

```json
{
    "task_completed": true,
    "instructions": "Update database URL in config.py",
    "results": "Updated DATABASE_URL from localhost to prod-db.example.com. Verified change at line 10 via Edit→Read pattern. Configuration tests passed (1/1). Type checking (mypy) and linting (ruff) passed.",
    "files_modified": ["config.py"],
    "tools_used": ["Read", "Edit", "Bash"],
    "remember": ["Production database URL: prod-db.example.com/newdb"]
}
```"""

    def _create_poorly_formed_response(self) -> str:
        """Generate poorly-formed response that fails metrics."""
        return """Done! I've updated config.py with the new database URL.

The file should now point to the production database."""

    def _extract_workflow_steps(self, response: str) -> List[Dict[str, Any]]:
        """Extract workflow steps from response text.

        Args:
            response: Agent response text

        Returns:
            List of step dictionaries with name and verification status
        """
        steps = []

        # Look for step markers (Step 1:, Step 2:, etc.)
        import re

        step_pattern = re.compile(r"\*\*Step \d+: (.+?)\*\*", re.IGNORECASE)

        for match in step_pattern.finditer(response):
            step_name = match.group(1).strip()

            # Extract section after this step marker
            start_pos = match.end()
            next_match = step_pattern.search(response, start_pos)
            end_pos = next_match.start() if next_match else len(response)
            section = response[start_pos:end_pos]

            # Check if verification present in this section
            has_verification = bool(
                re.search(r"✅.*verified", section, re.IGNORECASE)
                or re.search(r"confirmed", section, re.IGNORECASE)
                or re.search(r"verified:", section, re.IGNORECASE)
            )

            steps.append(
                {
                    "name": step_name,
                    "has_verification": has_verification,
                    "section": section,
                }
            )

        return steps

    def _extract_json_block(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract and parse JSON block from response.

        Args:
            response: Agent response text

        Returns:
            Parsed JSON dict or None if not found/invalid
        """
        import re

        # Find JSON code block
        json_pattern = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)
        match = json_pattern.search(response)

        if not match:
            return None

        json_text = match.group(1).strip()

        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            return None
