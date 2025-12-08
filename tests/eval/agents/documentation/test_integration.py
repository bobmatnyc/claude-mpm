"""
Documentation Agent DeepEval Integration Test Harness.

This test harness validates Documentation Agent behaviors across 12 scenarios in 4 categories:
- Clarity Standards (4 scenarios: DOC-CLARITY-001 to DOC-CLARITY-004)
- Audience Awareness (4 scenarios: DOC-AUDIENCE-001 to DOC-AUDIENCE-004)
- Maintenance Focus (2 scenarios: DOC-MAINT-001 to DOC-MAINT-002)
- Completeness Requirements (2 scenarios: DOC-COMPLETE-001 to DOC-COMPLETE-002)

Each test:
1. Loads scenario from documentation_scenarios.json
2. Creates LLMTestCase with input and mock response
3. Applies appropriate custom metric(s)
4. Asserts compliance using DeepEval's metric evaluation

Usage:
    # Run all Documentation Agent integration tests
    pytest tests/eval/agents/documentation/test_integration.py -v

    # Run specific category
    pytest tests/eval/agents/documentation/test_integration.py::TestDocumentationClarityStandards -v

    # Run specific scenario
    pytest tests/eval/agents/documentation/test_integration.py::TestDocumentationClarityStandards::test_scenario[DOC-CLARITY-001] -v

Test Strategy:
    - Each scenario tests COMPLIANT response (should pass)
    - Metrics validate adherence to Documentation Agent protocols
    - Thresholds calibrated based on metric scoring components
    - Fixture-based scenario loading for maintainability
"""

import json
from pathlib import Path
from typing import Any, Dict

import pytest
from deepeval.test_case import LLMTestCase

# Import Documentation Agent custom metrics
from tests.eval.metrics.documentation import (
    AudienceAwarenessMetric,
    ClarityStandardsMetric,
)

# Path to Documentation scenarios JSON
SCENARIOS_PATH = (
    Path(__file__).parent.parent.parent
    / "scenarios"
    / "documentation"
    / "documentation_scenarios.json"
)


def load_scenarios() -> Dict[str, Any]:
    """Load Documentation scenarios from JSON file.

    Returns:
        Dict containing all scenarios and metadata

    Raises:
        FileNotFoundError: If scenarios file doesn't exist
        json.JSONDecodeError: If scenarios file is invalid JSON
    """
    if not SCENARIOS_PATH.exists():
        raise FileNotFoundError(f"Scenarios file not found: {SCENARIOS_PATH}")

    with open(SCENARIOS_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_scenario_by_id(scenario_id: str) -> Dict[str, Any]:
    """Get a specific scenario by its ID.

    Args:
        scenario_id: Scenario identifier (e.g., 'DOC-CLARITY-001')

    Returns:
        Scenario dictionary

    Raises:
        ValueError: If scenario_id not found
    """
    all_scenarios = load_scenarios()
    for scenario in all_scenarios["scenarios"]:
        if scenario["scenario_id"] == scenario_id:
            return scenario
    raise ValueError(f"Scenario not found: {scenario_id}")


@pytest.mark.integration
@pytest.mark.documentation
class TestDocumentationClarityStandards:
    """Integration tests for Clarity Standards (DOC-CLARITY-001 to DOC-CLARITY-004).

    These tests validate that the Documentation Agent follows clarity best practices:
    - Active voice usage (direct, imperative instructions)
    - Jargon handling (acronym definitions, glossary references)
    - Code examples (runnable examples with language hints)
    - Conciseness (avoids redundant phrases, direct language)

    All tests use compliant mock responses and expect metric thresholds to pass.
    """

    @pytest.fixture
    def metric(self) -> ClarityStandardsMetric:
        """Create ClarityStandardsMetric with default threshold (0.85)."""
        return ClarityStandardsMetric(threshold=0.85)

    @pytest.mark.parametrize(
        "scenario_id",
        [
            "DOC-CLARITY-001",  # Active Voice Usage
            "DOC-CLARITY-002",  # Jargon Handling and Definitions
            "DOC-CLARITY-003",  # Code Examples for Complex Concepts
            "DOC-CLARITY-004",  # Concise and Accurate Writing
        ],
    )
    def test_scenario(self, scenario_id: str, metric: ClarityStandardsMetric):
        """Test clarity standards compliance for each scenario.

        Args:
            scenario_id: ID of the scenario to test
            metric: ClarityStandardsMetric instance

        Validates:
            - Compliant response passes metric threshold (≥0.85)
            - Active voice usage
            - Jargon handling
            - Code examples present
            - Concise writing
        """
        scenario = get_scenario_by_id(scenario_id)

        # Create test case with compliant response
        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        # Measure metric score
        score = metric.measure(test_case)

        # Assert compliant response meets threshold
        assert score >= metric.threshold, (
            f"Scenario {scenario_id} failed Clarity Standards metric\n"
            f"Score: {score:.2f} (threshold: {metric.threshold})\n"
            f"Reason: {metric.reason}\n"
            f"Expected: {scenario['success_criteria']}\n"
        )


@pytest.mark.integration
@pytest.mark.documentation
class TestDocumentationAudienceAwareness:
    """Integration tests for Audience Awareness (DOC-AUDIENCE-001 to DOC-AUDIENCE-004).

    These tests validate that the Documentation Agent adapts to audiences:
    - Developer vs user documentation separation
    - Technical depth appropriate to audience
    - Context adaptation (internal vs public)
    - Prerequisite knowledge statements

    All tests use compliant mock responses and expect metric thresholds to pass.
    """

    @pytest.fixture
    def metric(self) -> AudienceAwarenessMetric:
        """Create AudienceAwarenessMetric with default threshold (0.80)."""
        return AudienceAwarenessMetric(threshold=0.80)

    @pytest.mark.parametrize(
        "scenario_id",
        [
            "DOC-AUDIENCE-001",  # Developer vs User Documentation
            "DOC-AUDIENCE-002",  # Technical Depth Adaptation
            "DOC-AUDIENCE-003",  # Context Adaptation (Internal vs Public)
            "DOC-AUDIENCE-004",  # Prerequisite Knowledge Statement
        ],
    )
    def test_scenario(self, scenario_id: str, metric: AudienceAwarenessMetric):
        """Test audience awareness compliance for each scenario.

        Args:
            scenario_id: ID of the scenario to test
            metric: AudienceAwarenessMetric instance

        Validates:
            - Compliant response passes metric threshold (≥0.80)
            - Audience clearly targeted
            - Technical depth appropriate
            - Context adaptation correct
            - Prerequisites stated
        """
        scenario = get_scenario_by_id(scenario_id)

        # Create test case with compliant response
        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        # Measure metric score
        score = metric.measure(test_case)

        # Assert compliant response meets threshold
        assert score >= metric.threshold, (
            f"Scenario {scenario_id} failed Audience Awareness metric\n"
            f"Score: {score:.2f} (threshold: {metric.threshold})\n"
            f"Reason: {metric.reason}\n"
            f"Expected: {scenario['success_criteria']}\n"
        )


@pytest.mark.integration
@pytest.mark.documentation
class TestDocumentationMaintenance:
    """Integration tests for Maintenance Focus (DOC-MAINT-001 to DOC-MAINT-002).

    These tests validate that the Documentation Agent follows maintenance practices:
    - Code synchronization verification (examples match current API)
    - Example update protocol (breaking changes documented)

    All tests use compliant mock responses and expect metric thresholds to pass.
    """

    @pytest.fixture
    def metric(self) -> AudienceAwarenessMetric:
        """Create AudienceAwarenessMetric with default threshold (0.80)."""
        return AudienceAwarenessMetric(threshold=0.80)

    @pytest.mark.parametrize(
        "scenario_id",
        [
            "DOC-MAINT-001",  # Code Synchronization Verification
            "DOC-MAINT-002",  # Example Update Protocol
        ],
    )
    def test_scenario(self, scenario_id: str, metric: AudienceAwarenessMetric):
        """Test maintenance focus compliance for each scenario.

        Args:
            scenario_id: ID of the scenario to test
            metric: AudienceAwarenessMetric instance (includes maintenance bonus)

        Validates:
            - Compliant response passes metric threshold (≥0.80)
            - Version information present
            - Deprecation warnings clear
            - Code examples up-to-date
        """
        scenario = get_scenario_by_id(scenario_id)

        # Create test case with compliant response
        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        # Measure metric score
        score = metric.measure(test_case)

        # Assert compliant response meets threshold
        assert score >= metric.threshold, (
            f"Scenario {scenario_id} failed Audience Awareness metric\n"
            f"Score: {score:.2f} (threshold: {metric.threshold})\n"
            f"Reason: {metric.reason}\n"
            f"Expected: {scenario['success_criteria']}\n"
        )


@pytest.mark.integration
@pytest.mark.documentation
class TestDocumentationCompleteness:
    """Integration tests for Completeness Requirements (DOC-COMPLETE-001 to DOC-COMPLETE-002).

    These tests validate that the Documentation Agent includes complete documentation:
    - Required sections (Overview, Quick Start, Reference, Troubleshooting, Changelog)
    - Troubleshooting coverage (common errors with solutions)

    All tests use compliant mock responses and expect metric thresholds to pass.
    """

    @pytest.fixture
    def metric(self) -> ClarityStandardsMetric:
        """Create ClarityStandardsMetric with default threshold (0.85)."""
        return ClarityStandardsMetric(threshold=0.85)

    @pytest.mark.parametrize(
        "scenario_id",
        [
            "DOC-COMPLETE-001",  # Required Sections Completeness
            "DOC-COMPLETE-002",  # Troubleshooting Coverage
        ],
    )
    def test_scenario(self, scenario_id: str, metric: ClarityStandardsMetric):
        """Test completeness requirements for each scenario.

        Args:
            scenario_id: ID of the scenario to test
            metric: ClarityStandardsMetric instance (includes completeness bonus)

        Validates:
            - Compliant response passes metric threshold (≥0.85)
            - All required sections present
            - Troubleshooting section complete
            - Changelog included
        """
        scenario = get_scenario_by_id(scenario_id)

        # Create test case with compliant response
        test_case = LLMTestCase(
            input=scenario["input"]["user_request"],
            actual_output=scenario["mock_response"]["compliant"],
        )

        # Measure metric score
        score = metric.measure(test_case)

        # Assert compliant response meets threshold
        assert score >= metric.threshold, (
            f"Scenario {scenario_id} failed Clarity Standards metric\n"
            f"Score: {score:.2f} (threshold: {metric.threshold})\n"
            f"Reason: {metric.reason}\n"
            f"Expected: {scenario['success_criteria']}\n"
        )


# ============================================================================
# Scenario File Integrity Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.documentation
class TestScenarioFileIntegrity:
    """Tests to verify documentation_scenarios.json structure and completeness."""

    @pytest.fixture(scope="class")
    def all_scenarios(self) -> Dict[str, Any]:
        """Load all Documentation scenarios for class-level access."""
        return load_scenarios()

    def test_total_scenario_count(self, all_scenarios: Dict[str, Any]):
        """Verify total scenario count matches expected (12)."""
        assert all_scenarios["total_scenarios"] == 12, (
            f"Expected 12 total Documentation scenarios, "
            f"got {all_scenarios['total_scenarios']}"
        )
        assert len(all_scenarios["scenarios"]) == 12, (
            f"Expected 12 scenarios in list, got {len(all_scenarios['scenarios'])}"
        )

    def test_category_counts(self, all_scenarios: Dict[str, Any]):
        """Verify each category has expected scenario count."""
        expected_categories = {
            "clarity_standards": 4,
            "audience_awareness": 4,
            "maintenance_focus": 2,
            "completeness_requirements": 2,
        }

        for category, expected_count in expected_categories.items():
            actual_count = all_scenarios["categories"][category]["count"]
            assert actual_count == expected_count, (
                f"Category '{category}' should have {expected_count} scenarios, "
                f"got {actual_count}"
            )

    def test_scenario_structure(self, all_scenarios: Dict[str, Any]):
        """Verify each scenario has required fields."""
        required_fields = {
            "scenario_id",
            "name",
            "category",
            "priority",
            "description",
            "input",
            "expected_behavior",
            "success_criteria",
            "failure_indicators",
            "metrics",
            "mock_response",
        }

        for scenario in all_scenarios["scenarios"]:
            scenario_id = scenario.get("scenario_id", "UNKNOWN")

            # Check required fields
            missing_fields = required_fields - set(scenario.keys())
            assert not missing_fields, (
                f"Scenario {scenario_id} missing fields: {missing_fields}"
            )

            # Check mock_response has both compliant and non_compliant
            assert "compliant" in scenario["mock_response"], (
                f"Scenario {scenario_id} missing compliant mock response"
            )
            assert "non_compliant" in scenario["mock_response"], (
                f"Scenario {scenario_id} missing non_compliant mock response"
            )

    def test_scenario_ids_unique(self, all_scenarios: Dict[str, Any]):
        """Verify scenario IDs are unique."""
        scenario_ids = [s["scenario_id"] for s in all_scenarios["scenarios"]]
        duplicates = [sid for sid in scenario_ids if scenario_ids.count(sid) > 1]

        assert not duplicates, f"Duplicate scenario IDs found: {set(duplicates)}"

    def test_metric_references(self, all_scenarios: Dict[str, Any]):
        """Verify each scenario references valid metrics."""
        valid_metrics = {
            "ClarityStandardsMetric",
            "AudienceAwarenessMetric",
        }

        for scenario in all_scenarios["scenarios"]:
            scenario_id = scenario["scenario_id"]
            metrics = scenario.get("metrics", {})

            # Check at least one metric is referenced
            assert metrics, f"Scenario {scenario_id} has no metrics defined"

            # Check metric names are valid
            for metric_name in metrics:
                assert metric_name in valid_metrics, (
                    f"Scenario {scenario_id} references invalid metric: {metric_name}"
                )


# ============================================================================
# Multi-Step Workflow Integration Tests (Sprint 6 #112)
# ============================================================================


@pytest.mark.integration
@pytest.mark.documentation
@pytest.mark.slow
class TestDocumentationWorkflows:
    """Integration tests for multi-step Documentation Agent workflows.

    These tests validate complete workflows combining multiple scenarios:
    1. Documentation Clarity Workflow (DOC-CLARITY-001 to DOC-CLARITY-004)
    2. Documentation Audience Workflow (DOC-AUDIENCE-001 to DOC-AUDIENCE-004)
    3. Documentation Maintenance Workflow (DOC-MAINT-001 to DOC-MAINT-002)

    Each workflow test:
    - Combines multiple individual scenarios into realistic multi-step workflow
    - Uses strict metric thresholds for comprehensive compliance
    - Validates end-to-end documentation creation process
    - Ensures consistency and adherence to Documentation Agent protocols
    """

    def test_documentation_clarity_workflow(self):
        """
        Integration test: Complete documentation clarity lifecycle.

        Flow:
        1. Draft initial documentation with active voice
        2. Add jargon definitions and glossary references
        3. Include practical code examples with language hints
        4. Review for conciseness, remove redundant phrases

        Combined scenarios:
        - DOC-CLARITY-001: Active Voice Usage
        - DOC-CLARITY-002: Jargon Handling and Definitions
        - DOC-CLARITY-003: Code Examples for Complex Concepts
        - DOC-CLARITY-004: Concise and Accurate Writing

        Success criteria:
        - Active voice used throughout (>90% of instructions)
        - All acronyms defined on first use
        - Runnable code examples with language hints
        - No redundant phrases ("in order to", "it should be noted")
        - Clear, direct language

        Metrics: ClarityStandardsMetric (threshold 0.85)
        """
        workflow_response = """
# API Authentication Guide

**Version**: 2.0.0
**Last Updated**: December 6, 2025

## Quick Start

Send a POST request to `/v2/auth/login` with your credentials:

```bash
curl -X POST https://api.example.com/v2/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"email": "user@example.com", "password": "secretpass123", "mfaCode": "123456"}'
```

The API returns a JWT (JSON Web Token) for authentication:

```json
{
  "accessToken": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refreshToken": "refresh_abc123...",
  "expiresIn": 3600
}
```

Include the access token in subsequent requests:

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \\
  https://api.example.com/users/me
```

## Key Concepts

- **JWT (JSON Web Token)**: Signed token containing user claims and expiration
- **Access Token**: Short-lived token for API requests (expires in 1 hour)
- **Refresh Token**: Long-lived token for renewing access tokens (expires in 30 days)
- **MFA (Multi-Factor Authentication)**: Required code from authenticator app

See [Authentication RFC 7519](https://tools.ietf.org/html/rfc7519) for JWT specification.

## Token Storage

Store tokens securely in your application. Never store tokens in:
- ❌ LocalStorage (vulnerable to XSS attacks)
- ❌ Cookies without HttpOnly flag
- ❌ URL parameters or GET requests

✅ Store in HttpOnly cookies or secure session storage.

## Refreshing Tokens

Access tokens expire after 1 hour. Refresh them before expiration:

```javascript
// Check token expiration
const tokenExpiry = parseJWT(accessToken).exp * 1000;
const isExpired = Date.now() > tokenExpiry;

if (isExpired) {
  // Refresh token
  const response = await fetch('/v2/auth/refresh', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refreshToken })
  });

  const { accessToken: newToken } = await response.json();
  // Update stored token
}
```

## Error Handling

**HTTP 401 Unauthorized**:
```json
{
  "error": "invalid_credentials",
  "message": "Email or password is incorrect"
}
```

**Solution**: Verify credentials and retry. After 5 failed attempts, account locks for 15 minutes.

**HTTP 403 Forbidden (MFA Required)**:
```json
{
  "error": "mfa_required",
  "message": "Multi-factor authentication code is required"
}
```

**Solution**: Include `mfaCode` field in login request with 6-digit code from authenticator app.

## Security Best Practices

1. **Use HTTPS**: All API calls must use TLS encryption
2. **Rotate refresh tokens**: Automatically rotated on each use
3. **Implement token expiration**: Access tokens expire in 1 hour
4. **Enable MFA**: Required for all production accounts

## Example: Full Authentication Flow

```typescript
// Complete authentication flow with error handling
async function authenticateUser(email: string, password: string, mfaCode?: string) {
  try {
    // 1. Login request
    const response = await fetch('https://api.example.com/v2/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, mfaCode })
    });

    // 2. Handle errors
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message);
    }

    // 3. Store tokens securely
    const { accessToken, refreshToken, expiresIn } = await response.json();

    // Store in secure HttpOnly cookie (server-side)
    document.cookie = `accessToken=${accessToken}; Secure; HttpOnly; SameSite=Strict`;

    return { accessToken, expiresIn };

  } catch (error) {
    console.error('Authentication failed:', error);
    throw error;
  }
}

// Usage
const tokens = await authenticateUser('user@example.com', 'secretpass123', '123456');
console.log('Logged in successfully');
```

## Troubleshooting

### Error: "Token expired"

**Cause**: Access token validity exceeded 1 hour

**Solution**: Use refresh token to get new access token:

```bash
curl -X POST https://api.example.com/v2/auth/refresh \\
  -H "Content-Type: application/json" \\
  -d '{"refreshToken": "refresh_abc123..."}'
```

### Error: "MFA code invalid"

**Cause**: Authenticator app time out of sync

**Solution**: Ensure device time is synchronized with NTP server. MFA codes expire every 30 seconds.

## Changelog

### v2.0.0 (December 15, 2025)

**Breaking Changes**:
- 🔴 Endpoint changed: `/auth/login` → `/v2/auth/login`
- 🔴 MFA required for all accounts (previously optional)

**New Features**:
- ✨ Refresh token rotation for improved security
- ✨ HttpOnly cookie support for token storage

**Migration Guide**: See [v1 to v2 Migration](./migration-v1-v2.md)
"""

        test_case = LLMTestCase(
            input="Create comprehensive authentication documentation with clarity best practices",
            actual_output=workflow_response,
        )

        # Clarity workflow threshold (0.85 - comprehensive compliance)
        metric = ClarityStandardsMetric(threshold=0.85)
        score = metric.measure(test_case)

        assert score >= 0.85, (
            f"Documentation clarity workflow failed\n"
            f"Score: {score:.2f} (threshold: 0.85)\n"
            f"Reason: {metric.reason}\n"
            f"Expected: Active voice → define jargon → add code examples → review conciseness"
        )

    def test_documentation_audience_workflow(self):
        """
        Integration test: Audience-targeted documentation creation.

        Flow:
        1. Identify target audience (developers vs users)
        2. Adapt technical depth to audience expertise
        3. Include prerequisites and assumed knowledge
        4. Verify context appropriateness (internal vs public)

        Combined scenarios:
        - DOC-AUDIENCE-001: Developer vs User Documentation
        - DOC-AUDIENCE-002: Technical Depth Adaptation
        - DOC-AUDIENCE-003: Context Adaptation (Internal vs Public)
        - DOC-AUDIENCE-004: Prerequisite Knowledge Statement

        Success criteria:
        - Clear audience targeting upfront
        - Technical depth matches audience (architecture for devs, steps for users)
        - No internal references in public docs
        - Prerequisites clearly stated with links

        Metrics: AudienceAwarenessMetric (threshold 0.80)
        """
        workflow_response = """
# WebSocket Connection Architecture

**Audience**: Senior Backend Engineers
**Prerequisites**: Familiarity with WebSocket protocol (RFC 6455), event-driven architectures, Node.js concurrency patterns

**Skill Level**: Senior Engineer (3+ years backend experience)

## Quick Self-Check

Before proceeding, ensure you understand:
- ✅ WebSocket protocol basics ([RFC 6455](https://tools.ietf.org/html/rfc6455))
- ✅ Event loop concurrency in Node.js
- ✅ Connection pooling patterns
- ✅ Distributed systems fundamentals

If not familiar, review the [WebSocket Basics Guide](https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API).

---

## Architecture Overview

We chose a **connection pool with heartbeat monitoring** over individual connections
to optimize resource usage and enable graceful degradation under load.

### Design Decision: Connection Pooling

**Why connection pooling?**

**Trade-offs**:
- ✅ Memory efficient: O(pool_size) vs. O(connections)
  - **Concrete impact**: 50K connections = 400MB RAM (pooled) vs. 8GB RAM (individual)
- ✅ Better load distribution across worker processes
- ❌ Added complexity: Pool management logic required (~500 LOC)
- ❌ Higher latency: Queueing overhead (~5ms p99)

**Alternatives considered**:
1. **Individual connections per client**: Rejected due to memory exhaustion at scale (>10K clients)
2. **Redis PubSub for message routing**: Rejected due to 200K msg/s bottleneck
3. **gRPC bidirectional streaming**: Rejected due to HTTP/2 overhead (12% slower than raw WebSocket)

### Heartbeat Strategy

**Implementation**: RFC 6455 Ping/Pong frames every 30 seconds

**Why 30s interval?**
- NAT timeout on most routers: 60-300s (we stay well below minimum)
- TCP keepalive: 2 hours (too slow for real-time detection)
- 30s balances network overhead (2% bandwidth) vs. fast failure detection

**Failure Detection**:
- 3 missed pongs → mark connection as stale
- Stale connections evicted from pool after 90s
- Client automatically reconnects with exponential backoff

```typescript
class ConnectionPool {
  private heartbeatInterval = 30_000; // 30s (RFC 6455 recommendation)
  private missedPongThreshold = 3;
  private staleEvictionTimeout = 90_000; // 90s

  private startHeartbeat(ws: WebSocket): void {
    const intervalId = setInterval(() => {
      if (ws.missedPongs >= this.missedPongThreshold) {
        // Mark as stale, evict from pool
        this.evictConnection(ws);
        clearInterval(intervalId);
        return;
      }

      // Send ping
      ws.ping();
      ws.missedPongs++;
    }, this.heartbeatInterval);

    // Reset counter on pong
    ws.on('pong', () => {
      ws.missedPongs = 0;
    });
  }
}
```

## Performance Characteristics

**Benchmarks** (c5.2xlarge AWS instance: 8 vCPU, 16GB RAM):

| Metric | Value | Target |
|--------|-------|--------|
| Max concurrent connections | 50,000 | 50,000 ✅ |
| Message throughput | 100,000 msg/s | 75,000 ✅ |
| P50 latency | 3ms | <5ms ✅ |
| P95 latency | 8ms | <15ms ✅ |
| P99 latency | 12ms | <25ms ✅ |
| Memory usage (50K conn) | 400MB | <512MB ✅ |

**Bottleneck Analysis**:

1. **Redis PubSub** (critical path):
   - Limit: ~200K msg/s aggregate
   - Current usage: 100K msg/s (50% headroom)
   - **Mitigation**: Shard Redis by topic (planned for Q1 2026)

2. **PostgreSQL state queries** (connection metadata):
   - Limit: Connection pool exhaustion at 10K QPS
   - Current usage: 3K QPS (70% headroom)
   - **Mitigation**: Add read replicas if QPS exceeds 8K

3. **Event loop saturation** (Node.js single-threaded):
   - Limit: ~50K active connections per worker
   - Current: 12.5K avg per worker (4 workers)
   - **Mitigation**: Horizontal scaling with load balancer

## Implementation Details

**Connection Pool Architecture**:

```typescript
class WebSocketConnectionPool {
  private pool: Map<string, WebSocket> = new Map();
  private maxPoolSize: number = 50_000;
  private workerCount: number = 4;

  async acquireConnection(userId: string): Promise<WebSocket> {
    // Check pool first
    let ws = this.pool.get(userId);

    if (ws && ws.readyState === WebSocket.OPEN) {
      return ws; // Reuse existing connection
    }

    // Create new connection if pool not full
    if (this.pool.size < this.maxPoolSize) {
      ws = await this.createConnection(userId);
      this.pool.set(userId, ws);
      return ws;
    }

    // Pool exhausted - queue and wait
    throw new PoolExhaustedError(
      `Connection pool full (${this.maxPoolSize} connections)`
    );
  }

  private async createConnection(userId: string): Promise<WebSocket> {
    const ws = new WebSocket(`wss://ws.example.com?userId=${userId}`);

    // Configure heartbeat monitoring
    this.startHeartbeat(ws);

    // Handle connection lifecycle
    ws.on('close', () => this.releaseConnection(userId));
    ws.on('error', (err) => this.handleError(userId, err));

    return ws;
  }
}
```

**Distributed Coordination** (multi-instance deployment):

- **Service Discovery**: Consul for worker registration
- **Load Balancing**: HAProxy with least-connections algorithm
- **Session Affinity**: Sticky sessions based on userId hash
- **State Synchronization**: Redis for shared connection metadata

**Failure Scenarios and Recovery**:

1. **Worker crash**: Clients reconnect to healthy worker (sticky sessions preserved via Redis)
2. **Redis unavailable**: Fall back to local pool state (degraded mode, no cross-worker coordination)
3. **Network partition**: Detect via heartbeat, clients reconnect with exponential backoff

## References

- [RFC 6455: WebSocket Protocol](https://tools.ietf.org/html/rfc6455)
- [AWS Best Practices: Exponential Backoff and Jitter](https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/)
- [Connection Pooling Patterns (Martin Fowler)](https://martinfowler.com/articles/patterns-of-distributed-systems/connection-pool.html)

**Version**: 2.1.0
**Last Updated**: December 6, 2025
**Tested with**: Node.js 20.x, WebSocket library 8.x
"""

        test_case = LLMTestCase(
            input="Document WebSocket architecture for senior engineers with full technical depth",
            actual_output=workflow_response,
        )

        # Audience workflow threshold (0.80)
        metric = AudienceAwarenessMetric(threshold=0.80)
        score = metric.measure(test_case)

        assert score >= 0.80, (
            f"Documentation audience workflow failed\n"
            f"Score: {score:.2f} (threshold: 0.80)\n"
            f"Reason: {metric.reason}\n"
            f"Expected: Identify audience → adapt depth → add prerequisites → verify context"
        )

    def test_documentation_maintenance_workflow(self):
        """
        Integration test: Documentation update after API change.

        Flow:
        1. Detect breaking API change (endpoint renamed)
        2. Search for all affected code examples using Grep
        3. Update ALL examples consistently (no partial updates)
        4. Add deprecation warnings and migration guide
        5. Verify version info and last updated timestamp

        Combined scenarios:
        - DOC-MAINT-001: Code Synchronization Verification
        - DOC-MAINT-002: Example Update Protocol

        Success criteria:
        - All code examples updated to new API endpoint (100% consistency)
        - Deprecation warnings clearly marked (⚠️ BREAKING)
        - Migration guide with before/after examples
        - Version numbers referenced ("Since v2.0", "Removed in v3.0")
        - Last verified timestamp included
        - Changelog entry created

        Metrics: ClarityStandardsMetric (0.85) + AudienceAwarenessMetric (0.80)
        """
        workflow_response = """
# ⚠️ BREAKING CHANGE: Authentication API v2.0 Migration

**Effective Date**: December 15, 2025
**Migration Deadline**: January 15, 2026
**Last Updated**: December 6, 2025

## What Changed

Authentication endpoint moved from `/auth/login` to `/v2/auth/login` with additional MFA requirement.

### Before (v1.x - Deprecated)

```bash
# ❌ OLD (v1.x) - DO NOT USE
POST /auth/login
Content-Type: application/json

{
  "username": "user",
  "password": "secretpass123"
}
```

### After (v2.0+ - Current)

```bash
# ✅ NEW (v2.0+) - Use this
POST /v2/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "secretpass123",
  "mfaCode": "123456"
}
```

## Migration Guide

### Step 1: Update All API Calls

**Search for old endpoint**:
```bash
# Find all references to old endpoint
grep -r "/auth/login" --include="*.js" --include="*.ts" src/
```

**Update to new endpoint**:

**JavaScript (fetch API)**:
```javascript
// ❌ OLD (v1.x)
fetch('https://api.example.com/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ username: 'user', password: 'pass' })
});

// ✅ NEW (v2.0+)
fetch('https://api.example.com/v2/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'pass',
    mfaCode: '123456'
  })
});
```

**Python (requests library)**:
```python
# ❌ OLD (v1.x)
import requests

response = requests.post(
    'https://api.example.com/auth/login',
    json={'username': 'user', 'password': 'pass'}
)

# ✅ NEW (v2.0+)
import requests

response = requests.post(
    'https://api.example.com/v2/auth/login',
    json={
        'email': 'user@example.com',
        'password': 'pass',
        'mfaCode': '123456'
    }
)
```

**TypeScript (axios library)**:
```typescript
// ❌ OLD (v1.x)
import axios from 'axios';

const response = await axios.post('https://api.example.com/auth/login', {
  username: 'user',
  password: 'pass'
});

// ✅ NEW (v2.0+)
import axios from 'axios';

const response = await axios.post('https://api.example.com/v2/auth/login', {
  email: 'user@example.com',
  password: 'pass',
  mfaCode: '123456'
});
```

### Step 2: Add MFA Support

All accounts now require Multi-Factor Authentication (MFA).

**Set up MFA for users**:
1. Install authenticator app (Google Authenticator, Authy)
2. Scan QR code from account settings
3. Enter 6-digit code on login

**Update login form**:
```html
<!-- ✅ NEW (v2.0+) -->
<form id="login-form">
  <input type="email" name="email" placeholder="Email" required>
  <input type="password" name="password" placeholder="Password" required>
  <input type="text" name="mfaCode" placeholder="MFA Code (6 digits)" required>
  <button type="submit">Login</button>
</form>
```

### Step 3: Update Environment Configuration

**Environment variables** (update `.env` files):

```bash
# ❌ OLD (v1.x)
API_BASE_URL=https://api.example.com
AUTH_ENDPOINT=/auth/login

# ✅ NEW (v2.0+)
API_BASE_URL=https://api.example.com
AUTH_ENDPOINT=/v2/auth/login
API_VERSION=2.0
```

### Step 4: Test Migration

**Verification checklist**:

```bash
# 1. Verify no references to old endpoint
grep -r "/auth/login" --include="*.js" --include="*.ts" src/
# Should return: 0 matches

# 2. Test login with new endpoint
curl -X POST https://api.example.com/v2/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"email": "test@example.com", "password": "testpass", "mfaCode": "123456"}'
# Should return: 200 OK with JWT token

# 3. Verify old endpoint returns deprecation warning
curl -X POST https://api.example.com/auth/login \\
  -H "Content-Type: application/json" \\
  -d '{"username": "test", "password": "pass"}'
# Should return: HTTP 410 Gone (endpoint removed)
```

## Updated Documentation Sections

**All affected endpoints** (verified December 6, 2025):

- ✅ **Login endpoint**: Updated `/auth/login` → `/v2/auth/login` (12 examples updated)
- ✅ **Refresh token endpoint**: Updated `/auth/refresh` → `/v2/auth/refresh` (5 examples updated)
- ✅ **Logout endpoint**: Updated `/auth/logout` → `/v2/auth/logout` (3 examples updated)
- ✅ **User profile endpoint**: No change (still `/users/me`)
- ✅ **Password reset endpoint**: Updated `/auth/reset` → `/v2/auth/reset` (2 examples updated)

**Total examples updated**: 22 code examples across 8 documentation pages

## Rollout Timeline

| Date | Phase | Status |
|------|-------|--------|
| Dec 15, 2025 | v2.0 API released (old endpoint deprecated) | ⚠️ Grace period starts |
| Jan 1, 2026 | Warning messages for old endpoint usage | ⚠️ Warnings active |
| Jan 15, 2026 | Old endpoint removed (HTTP 410 Gone) | 🔴 Enforcement |

## Deprecation Warnings

### v1.x Endpoints (Removed in v2.0)

⚠️ **DEPRECATED**: `/auth/login` (replaced by `/v2/auth/login`)
- **Removed**: January 15, 2026
- **Migration**: Use `/v2/auth/login` with email and MFA code

⚠️ **DEPRECATED**: `/auth/refresh` (replaced by `/v2/auth/refresh`)
- **Removed**: January 15, 2026
- **Migration**: Use `/v2/auth/refresh` with refresh token

⚠️ **DEPRECATED**: `username` field (replaced by `email`)
- **Removed**: January 15, 2026
- **Migration**: Use `email` field instead of `username`

## Changelog

### v2.0.0 (December 15, 2025)

**Breaking Changes**:
- 🔴 **BREAKING**: Endpoint moved `/auth/login` → `/v2/auth/login`
- 🔴 **BREAKING**: MFA required for all accounts (previously optional)
- 🔴 **BREAKING**: `username` field replaced with `email`

**New Features**:
- ✨ Refresh token rotation for improved security
- ✨ Email-based authentication instead of username
- ✨ Mandatory MFA for enhanced account security

**Bug Fixes**:
- 🐛 Fixed session fixation vulnerability in v1.x login flow

**Documentation**:
- 📖 Updated all 22 code examples to v2.0 API
- 📖 Added migration guide with before/after examples
- 📖 Added deprecation timeline and warnings

**Version**: 2.0.0
**API Version**: v2.0
**Last Verified**: December 6, 2025 (all examples tested with API v2.0.0)
"""

        test_case = LLMTestCase(
            input="Update authentication documentation after breaking API change from /auth/login to /v2/auth/login",
            actual_output=workflow_response,
        )

        # Test with both metrics
        clarity_metric = ClarityStandardsMetric(threshold=0.85)
        audience_metric = AudienceAwarenessMetric(threshold=0.80)

        clarity_score = clarity_metric.measure(test_case)
        audience_score = audience_metric.measure(test_case)

        # Both metrics must pass for maintenance workflow
        assert clarity_score >= 0.85, (
            f"Maintenance workflow failed Clarity metric\n"
            f"Score: {clarity_score:.2f} (threshold: 0.85)\n"
            f"Reason: {clarity_metric.reason}\n"
        )

        assert audience_score >= 0.80, (
            f"Maintenance workflow failed Audience Awareness metric\n"
            f"Score: {audience_score:.2f} (threshold: 0.80)\n"
            f"Reason: {audience_metric.reason}\n"
            f"Expected: Detect change → search examples → update all → add warnings → verify"
        )
