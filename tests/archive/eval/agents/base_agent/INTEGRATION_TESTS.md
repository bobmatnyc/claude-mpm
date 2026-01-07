# BASE_AGENT Integration Test Plan

**Version**: 1.0.0
**Date**: December 6, 2025
**Status**: Design Specification Complete ✅
**Total Integration Tests**: 5
**Framework**: DeepEval 1.0.0+ with pytest-asyncio

---

## Overview

This document specifies 5 comprehensive integration tests for BASE_AGENT evaluation. These tests validate end-to-end agent behavior, template merging, multi-agent interactions, and cross-cutting concerns.

Unlike unit tests (which test individual scenarios), integration tests validate:
1. **Template Merge Process**: Hierarchical composition of BASE_AGENT + specialized templates
2. **Multi-Tool Workflows**: Complex workflows requiring multiple tool orchestrations
3. **Error Recovery Chains**: Cascading error handling across multiple operations
4. **Memory Persistence**: Memory capture, update, and retrieval across sessions
5. **Cross-Agent Patterns**: Behaviors shared across all agent types

---

## Integration Test 1: Template Merge and Inheritance

### Test Name
`test_base_agent_template_merge_inheritance`

### Objective
Validate that specialized agents correctly inherit BASE_AGENT behaviors while applying specialized overrides.

### Test Architecture

```
BASE_AGENT_TEMPLATE.md
    ↓ (merged with)
BASE_RESEARCH.md
    ↓ (deployed as)
research-agent.md
    ↓ (evaluated)
Agent Response
```

### Test Scenario

**Input**:
```python
test_case = LLMTestCase(
    input="""
Research the authentication implementation in the codebase.
Files: auth/oauth.py (45KB), auth/middleware.py (12KB)
    """,
    expected_output="Research completed with memory-efficient approach and proper verification",
    context={
        "agent_type": "research",
        "template_stack": ["BASE_AGENT_TEMPLATE.md", "BASE_RESEARCH.md"]
    }
)
```

### Expected Behaviors

**From BASE_AGENT_TEMPLATE.md** (inherited):
1. ✅ JSON response block with all required fields
2. ✅ Verification language ("verified", "confirmed")
3. ✅ Evidence-based assertions (no unsubstantiated claims)
4. ✅ Task status indicators (completed/pending/blocked)

**From BASE_RESEARCH.md** (specialized):
1. ✅ File size check before reading (ls -lh or similar)
2. ✅ Document summarizer used for 45KB file
3. ✅ Strategic sampling (3-5 files max)
4. ✅ Memory management protocol (no full reads of large files)

### Validation Logic

```python
def test_base_agent_template_merge_inheritance():
    """Test template inheritance and specialization."""

    # Simulate research agent with merged templates
    agent_response = simulate_research_agent(
        input="Research authentication implementation",
        files={"auth/oauth.py": 45000, "auth/middleware.py": 12000}
    )

    test_case = LLMTestCase(
        input="Research authentication implementation",
        actual_output=agent_response,
        expected_output="Research with BASE_AGENT + research behaviors"
    )

    # Validate BASE_AGENT inheritance
    base_agent_checks = [
        JSONFormatMetric(threshold=1.0),
        VerificationComplianceMetric(threshold=0.9),
    ]

    # Validate research-specific behaviors
    research_checks = [
        FileSizeCheckMetric(threshold=1.0),  # Custom metric
        DocumentSummarizerUsageMetric(threshold=1.0),  # Custom metric
        MemoryEfficiencyMetric(threshold=0.9),
    ]

    # Run all checks
    for metric in base_agent_checks + research_checks:
        score = metric.measure(test_case)
        assert metric.is_successful(), f"{metric.name} failed: {metric.reason}"

    # Verify template merge correctness
    assert_template_behaviors(
        response=agent_response,
        base_behaviors=["verification", "json_format", "evidence"],
        specialized_behaviors=["file_size_check", "document_summarizer", "sampling"]
    )
```

### Success Criteria

- [x] All BASE_AGENT behaviors present
- [x] All research-specific behaviors present
- [x] No conflicts between base and specialized behaviors
- [x] Proper override hierarchy (specialized overrides base when needed)

### Failure Indicators

- ✗ Missing BASE_AGENT behaviors (JSON format, verification)
- ✗ Missing research-specific behaviors (file size checks, summarizer)
- ✗ Research agent reads large files directly (violates specialization)
- ✗ Conflicts between base and specialized instructions

### Execution Mode

**Three-Mode Support** (from Phase 1):
1. **Integration Mode**: Real agent invocation (slow, comprehensive)
2. **Replay Mode**: Captured response replay (fast, regression testing)
3. **Mock Mode**: Simulated response (fastest, development)

---

## Integration Test 2: Multi-Tool Workflow with Verification Chain

### Test Name
`test_multi_tool_workflow_verification_chain`

### Objective
Validate complex workflows requiring multiple tool invocations with proper verification at each step.

### Test Scenario

**Workflow**: Code Change → Build → Test → Deploy → Verify

**Input**:
```python
test_case = LLMTestCase(
    input="""
Fix the bug in calculate_discount() function and deploy to staging.

Steps:
1. Fix the bug in pricing.py
2. Run tests to verify fix
3. Build Docker image
4. Deploy to staging
5. Run health check
    """,
    expected_output="Complete workflow with verification at each step"
)
```

### Expected Verification Chain

```
Step 1: Fix Bug
  ├─ Read pricing.py (before)
  ├─ Edit pricing.py (fix)
  └─ Read pricing.py (verify edit) ✓

Step 2: Run Tests
  ├─ Bash: pytest tests/test_pricing.py
  └─ Verify: Tests pass (8/8) ✓

Step 3: Build Image
  ├─ Bash: docker build -t app:v1.2.3 .
  └─ Verify: Build successful ✓

Step 4: Deploy
  ├─ Bash: ./deploy.sh staging
  └─ Verify: Deployment output ✓

Step 5: Health Check
  ├─ Bash: curl https://staging.app.com/health
  └─ Verify: Service healthy ✓
```

### Validation Logic

```python
def test_multi_tool_workflow_verification_chain():
    """Test complex workflow with verification chain."""

    agent_response = simulate_agent_workflow(
        input="Fix bug and deploy to staging",
        workflow_steps=["fix", "test", "build", "deploy", "healthcheck"]
    )

    test_case = LLMTestCase(
        input="Fix bug and deploy to staging",
        actual_output=agent_response,
        expected_output="Complete workflow with verification"
    )

    # Validate workflow completion
    workflow_metric = WorkflowCompletenessMetric(
        required_steps=["fix", "test", "build", "deploy", "healthcheck"],
        threshold=1.0
    )
    assert workflow_metric.measure(test_case) == 1.0

    # Validate verification at each step
    verification_chain = extract_verification_chain(agent_response)
    expected_verifications = [
        "read_after_edit",
        "test_results",
        "build_success",
        "deploy_output",
        "health_check"
    ]

    for verification in expected_verifications:
        assert verification in verification_chain, \
            f"Missing verification: {verification}"

    # Validate error handling (if any step fails)
    if "failed" in agent_response.lower():
        assert "blocked" in agent_response.lower() or \
               "cannot proceed" in agent_response.lower(), \
            "Agent should block on failure"
```

### Success Criteria

- [x] All 5 workflow steps completed
- [x] Verification present after each step
- [x] Evidence provided for each verification
- [x] Proper error handling if any step fails

### Failure Indicators

- ✗ Missing verification steps
- ✗ Steps completed without evidence
- ✗ Continues after failure without escalation
- ✗ No verification chain documentation

### Test Variants

1. **Happy Path**: All steps succeed
2. **Test Failure**: Tests fail, deployment blocked
3. **Build Failure**: Docker build fails, deployment blocked
4. **Deploy Failure**: Deployment fails, health check skipped
5. **Health Check Failure**: Service unhealthy, rollback initiated

---

## Integration Test 3: Error Recovery and Escalation

### Test Name
`test_error_recovery_and_escalation_chain`

### Objective
Validate proper error detection, recovery attempts, and escalation when recovery fails.

### Test Scenario

**Scenario**: Deployment fails, agent should detect, attempt recovery, and escalate if recovery fails.

**Input**:
```python
test_case = LLMTestCase(
    input="""
Deploy the application to production.
    """,
    # Simulate deployment failure
    context={
        "deployment_result": "error",
        "error_message": "Docker image not found: app:v1.2.3"
    },
    expected_output="Error detected, recovery attempted, escalation on failure"
)
```

### Expected Error Recovery Chain

```
Step 1: Attempt Deployment
  └─ Error: Docker image not found ✗

Step 2: Diagnose Issue
  ├─ Check: docker images | grep app
  └─ Finding: No image with tag v1.2.3

Step 3: Attempt Recovery
  ├─ Action: Build missing image
  ├─ Bash: docker build -t app:v1.2.3 .
  └─ Result: Build succeeds ✓

Step 4: Retry Deployment
  ├─ Action: ./deploy.sh production
  └─ Result: Deployment succeeds ✓

Alternative: Recovery Fails
Step 3: Attempt Recovery
  └─ Result: Build fails ✗

Step 4: Escalate
  ├─ Status: BLOCKED
  ├─ Reason: Cannot build Docker image
  └─ Action: Escalate to user with error details
```

### Validation Logic

```python
def test_error_recovery_and_escalation_chain():
    """Test error recovery and proper escalation."""

    # Scenario 1: Recovery succeeds
    agent_response_recovery_success = simulate_agent_with_error(
        input="Deploy to production",
        error="Docker image not found",
        recovery_succeeds=True
    )

    test_case_1 = LLMTestCase(
        input="Deploy to production",
        actual_output=agent_response_recovery_success,
        expected_output="Error detected and recovered"
    )

    error_metric_1 = ErrorRecoveryMetric(threshold=1.0)
    score_1 = error_metric_1.measure(test_case_1)

    assert score_1 == 1.0, "Should detect error and recover"
    assert "task_completed\": true" in agent_response_recovery_success
    assert "recovery" in agent_response_recovery_success.lower()

    # Scenario 2: Recovery fails, escalation required
    agent_response_escalation = simulate_agent_with_error(
        input="Deploy to production",
        error="Docker image not found",
        recovery_succeeds=False
    )

    test_case_2 = LLMTestCase(
        input="Deploy to production",
        actual_output=agent_response_escalation,
        expected_output="Error detected, recovery failed, escalated"
    )

    # Validate escalation
    assert "task_completed\": false" in agent_response_escalation
    assert "blocked" in agent_response_escalation.lower() or \
           "escalat" in agent_response_escalation.lower()

    # Validate error details included
    assert "Docker image not found" in agent_response_escalation or \
           "error" in agent_response_escalation.lower()
```

### Success Criteria

- [x] Error detected immediately
- [x] Recovery attempted before escalation
- [x] Escalation triggered if recovery fails
- [x] Error details included in escalation
- [x] task_completed: false when blocked

### Failure Indicators

- ✗ Error not detected
- ✗ No recovery attempted
- ✗ Claims success despite error
- ✗ Escalation without recovery attempt
- ✗ task_completed: true when blocked

---

## Integration Test 4: Memory Persistence Across Sessions

### Test Name
`test_memory_persistence_and_updates`

### Objective
Validate memory capture, persistence, retrieval, and updates across multiple agent interactions.

### Test Scenario

**Session 1**: Agent discovers undocumented fact
**Session 2**: Agent uses previous memory
**Session 3**: Agent updates memory when fact changes

**Input Sequence**:
```python
# Session 1: Discovery
session_1_input = "Debug the webhook authentication issue"
# Agent discovers: "Stripe webhook uses X-Stripe-Signature header in production"

# Session 2: Retrieval
session_2_input = "Document the webhook authentication process"
# Agent should recall: Production webhook header requirement

# Session 3: Update
session_3_input = "The webhook header has changed to Stripe-Signature (no X- prefix)"
# Agent should update: Previous memory with new information
```

### Expected Memory Flow

```
Session 1 (Discovery):
  Input: "Debug webhook auth"
  Discovery: "Prod webhook uses X-Stripe-Signature header"
  Memory Capture:
    remember: ["Stripe webhook: X-Stripe-Signature header in prod"]

Session 2 (Retrieval):
  Input: "Document webhook auth"
  Memory Retrieval: Previous session memory loaded
  Usage: Documentation includes X-Stripe-Signature requirement
  Memory: No change (null)

Session 3 (Update):
  Input: "Header changed to Stripe-Signature (no X-)"
  Memory Update:
    OLD: "Stripe webhook: X-Stripe-Signature header in prod"
    NEW: "Stripe webhook: Stripe-Signature header (no X- prefix)"
  MEMORIES section: Complete updated list
```

### Validation Logic

```python
def test_memory_persistence_and_updates():
    """Test memory capture, retrieval, and updates."""

    # Session 1: Discovery
    response_1 = simulate_agent_session(
        input="Debug webhook authentication issue",
        context={"webhook_auth": "X-Stripe-Signature"}
    )

    # Validate memory capture
    json_1 = extract_json_block(response_1)
    assert json_1["remember"] is not None
    assert any("X-Stripe-Signature" in mem for mem in json_1["remember"])

    captured_memory = json_1["remember"]

    # Session 2: Retrieval
    response_2 = simulate_agent_session(
        input="Document webhook authentication process",
        previous_memories=captured_memory
    )

    # Validate memory usage
    assert "X-Stripe-Signature" in response_2
    json_2 = extract_json_block(response_2)
    assert json_2["remember"] is None or \
           json_2["remember"] == captured_memory  # No change

    # Session 3: Update
    response_3 = simulate_agent_session(
        input="Header changed to Stripe-Signature (no X- prefix)",
        previous_memories=captured_memory
    )

    # Validate memory update
    json_3 = extract_json_block(response_3)
    assert json_3["remember"] is not None
    assert any("Stripe-Signature" in mem for mem in json_3["remember"])
    assert not any("X-Stripe-Signature" in mem for mem in json_3["remember"])

    # Validate MEMORIES section present
    assert "MEMORIES" in response_3 or \
           '"MEMORIES"' in response_3, \
           "Should include MEMORIES section on update"
```

### Success Criteria

- [x] Session 1: Memory captured on discovery
- [x] Session 2: Memory retrieved and used
- [x] Session 3: Memory updated, MEMORIES section included
- [x] No duplicate or conflicting memories

### Failure Indicators

- ✗ Memory not captured on discovery
- ✗ Memory not used in subsequent session
- ✗ Memory update creates duplicates
- ✗ MEMORIES section missing on update

---

## Integration Test 5: Cross-Agent Behavioral Consistency

### Test Name
`test_cross_agent_behavioral_consistency`

### Objective
Validate that all specialized agents (Research, Engineer, QA, Ops, Documentation) maintain consistent BASE_AGENT behaviors.

### Test Scenario

**Test Matrix**: Same task executed by different agent types, all should exhibit BASE_AGENT compliance.

**Task**: "Update the configuration file config.yml to set timeout to 30 seconds"

**Agents Tested**:
- Research Agent
- Engineer Agent
- QA Agent
- Ops Agent
- Documentation Agent

### Expected Consistent Behaviors

**All agents MUST**:
1. ✅ Include JSON response block
2. ✅ Verify file changes (Read after Edit)
3. ✅ Provide evidence for assertions
4. ✅ Use proper task status indicators
5. ✅ Follow memory protocol (remember field)

**Agent-Specific Variations** (acceptable):
- Research: May check file size before reading
- Engineer: May search for existing config patterns first
- QA: May verify config syntax after edit
- Ops: May validate against deployment requirements
- Documentation: May focus on documenting the change

### Validation Logic

```python
def test_cross_agent_behavioral_consistency():
    """Test BASE_AGENT consistency across all agent types."""

    task = "Update config.yml to set timeout to 30 seconds"

    agent_types = ["research", "engineer", "qa", "ops", "documentation"]

    base_agent_scores = {}

    for agent_type in agent_types:
        # Simulate agent response
        response = simulate_agent(
            agent_type=agent_type,
            input=task,
            files={"config.yml": 200}  # Small file
        )

        test_case = LLMTestCase(
            input=task,
            actual_output=response,
            expected_output="Config updated"
        )

        # Test BASE_AGENT compliance
        json_metric = JSONFormatMetric(threshold=1.0)
        verification_metric = VerificationComplianceMetric(threshold=0.9)
        memory_metric = MemoryProtocolMetric(threshold=1.0)

        json_score = json_metric.measure(test_case)
        verification_score = verification_metric.measure(test_case)
        memory_score = memory_metric.measure(test_case)

        base_agent_scores[agent_type] = {
            "json": json_score,
            "verification": verification_score,
            "memory": memory_score
        }

        # Assert BASE_AGENT compliance
        assert json_score >= 1.0, \
            f"{agent_type} failed JSON format: {json_metric.reason}"
        assert verification_score >= 0.9, \
            f"{agent_type} failed verification: {verification_metric.reason}"
        assert memory_score >= 1.0, \
            f"{agent_type} failed memory protocol: {memory_metric.reason}"

    # Validate consistency across agents
    for metric_name in ["json", "verification", "memory"]:
        scores = [base_agent_scores[agent][metric_name] for agent in agent_types]
        avg_score = sum(scores) / len(scores)
        std_dev = calculate_std_dev(scores)

        # All agents should be consistently good
        assert std_dev < 0.1, \
            f"Inconsistent {metric_name} scores across agents: {base_agent_scores}"
```

### Success Criteria

- [x] All agents pass BASE_AGENT compliance metrics
- [x] Score variance across agents < 10%
- [x] No agent-specific BASE_AGENT violations
- [x] Consistent JSON format, verification, memory protocol

### Failure Indicators

- ✗ Any agent fails BASE_AGENT metrics
- ✗ High variance in compliance scores
- ✗ Agent-specific BASE_AGENT violations

---

## Integration Test Infrastructure

### Test Execution Framework

```python
# tests/eval/agents/base_agent/integration_tests.py

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from typing import List, Dict, Any

class BaseAgentIntegrationTestSuite:
    """Integration test suite for BASE_AGENT."""

    def __init__(self):
        self.metrics = self._initialize_metrics()
        self.test_results = []

    def _initialize_metrics(self):
        """Initialize all BASE_AGENT metrics."""
        return {
            "json_format": JSONFormatMetric(threshold=1.0),
            "verification": VerificationComplianceMetric(threshold=0.9),
            "memory": MemoryProtocolMetric(threshold=1.0),
        }

    def run_integration_test(
        self,
        test_name: str,
        input: str,
        expected_output: str,
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Run a single integration test.

        Args:
            test_name: Test identifier
            input: Test input
            expected_output: Expected output
            context: Additional context

        Returns:
            Test results with scores and status
        """
        # Simulate agent response (or use real agent)
        agent_response = self._execute_agent(input, context)

        # Create test case
        test_case = LLMTestCase(
            input=input,
            actual_output=agent_response,
            expected_output=expected_output
        )

        # Run metrics
        results = {}
        for metric_name, metric in self.metrics.items():
            score = metric.measure(test_case)
            results[metric_name] = {
                "score": score,
                "passed": metric.is_successful(),
                "reason": metric.reason
            }

        # Store results
        test_result = {
            "test_name": test_name,
            "input": input,
            "output": agent_response,
            "metrics": results,
            "overall_pass": all(r["passed"] for r in results.values())
        }

        self.test_results.append(test_result)
        return test_result

    def _execute_agent(self, input: str, context: Dict[str, Any] = None):
        """Execute agent (mock/replay/integration mode)."""
        # Implementation depends on execution mode
        # Mock mode: Return simulated response
        # Replay mode: Load captured response
        # Integration mode: Invoke real agent
        pass
```

### Test Execution Modes

```python
# Three execution modes from Phase 1

class ExecutionMode(Enum):
    MOCK = "mock"           # Fastest, development
    REPLAY = "replay"       # Fast, regression testing
    INTEGRATION = "integration"  # Slow, comprehensive

def run_integration_tests(mode: ExecutionMode = ExecutionMode.MOCK):
    """Run all integration tests in specified mode."""
    suite = BaseAgentIntegrationTestSuite()

    # Test 1: Template Merge
    suite.run_integration_test(
        test_name="template_merge_inheritance",
        input="Research authentication implementation",
        expected_output="Research with BASE_AGENT + specialized behaviors"
    )

    # Test 2: Multi-Tool Workflow
    suite.run_integration_test(
        test_name="multi_tool_workflow",
        input="Fix bug and deploy to staging",
        expected_output="Complete workflow with verification"
    )

    # Test 3: Error Recovery
    suite.run_integration_test(
        test_name="error_recovery_escalation",
        input="Deploy to production",
        expected_output="Error detected and handled"
    )

    # Test 4: Memory Persistence
    suite.run_integration_test(
        test_name="memory_persistence",
        input="Debug webhook auth",
        expected_output="Memory captured and persisted"
    )

    # Test 5: Cross-Agent Consistency
    suite.run_integration_test(
        test_name="cross_agent_consistency",
        input="Update config.yml timeout",
        expected_output="Consistent BASE_AGENT compliance"
    )

    return suite.test_results
```

---

## Test Data Management

### Captured Responses

```
tests/eval/agents/base_agent/responses/
├── template_merge_inheritance/
│   ├── research_agent_response.json
│   ├── engineer_agent_response.json
│   └── qa_agent_response.json
├── multi_tool_workflow/
│   ├── happy_path.json
│   ├── test_failure.json
│   └── deploy_failure.json
├── error_recovery/
│   ├── recovery_success.json
│   └── escalation.json
├── memory_persistence/
│   ├── session_1_discovery.json
│   ├── session_2_retrieval.json
│   └── session_3_update.json
└── cross_agent_consistency/
    ├── research_agent.json
    ├── engineer_agent.json
    ├── qa_agent.json
    ├── ops_agent.json
    └── documentation_agent.json
```

### Golden Baselines

```
tests/eval/agents/base_agent/golden_responses/
├── template_merge_inheritance_baseline.json
├── multi_tool_workflow_baseline.json
├── error_recovery_baseline.json
├── memory_persistence_baseline.json
└── cross_agent_consistency_baseline.json
```

---

## CI/CD Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/base_agent_integration_tests.yml

name: BASE_AGENT Integration Tests

on:
  pull_request:
    paths:
      - 'src/claude_mpm/agents/BASE_AGENT_TEMPLATE.md'
      - 'tests/eval/agents/base_agent/**'
  push:
    branches: [main]

jobs:
  integration_tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r requirements-eval.txt

      - name: Run BASE_AGENT integration tests
        run: |
          pytest tests/eval/agents/base_agent/integration_tests.py \
            --mode=replay \
            --capture=no \
            -v

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: integration-test-results
          path: tests/eval/agents/base_agent/test_results/
```

---

## Performance Benchmarks

### Expected Execution Times

| Test | Mock Mode | Replay Mode | Integration Mode |
|------|-----------|-------------|------------------|
| Template Merge | 0.2s | 0.5s | 30s |
| Multi-Tool Workflow | 0.3s | 0.8s | 60s |
| Error Recovery | 0.2s | 0.6s | 45s |
| Memory Persistence | 0.4s | 1.2s | 90s |
| Cross-Agent Consistency | 1.0s | 3.0s | 150s |
| **Total** | **2.1s** | **6.1s** | **375s (6.25min)** |

---

## Summary

**Integration Tests Specified**: 5
**Coverage**: End-to-end BASE_AGENT workflows
**Execution Modes**: 3 (Mock, Replay, Integration)

**Implementation Readiness**: ✅

**Next Steps**:
1. Implement integration test suite
2. Create mock/replay infrastructure
3. Capture golden baseline responses
4. Integrate with CI/CD pipeline

**Estimated Implementation Time**: 2-3 days for all 5 integration tests

---

**Document Version**: 1.0.0
**Last Updated**: December 6, 2025
**Status**: Complete ✅
