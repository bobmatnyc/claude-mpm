# Ops Agent DeepEval Integration Tests

Complete test harness for validating Ops Agent behavioral compliance across 18 scenarios in 4 critical categories.

## Overview

This test suite validates that the Ops Agent follows deployment safety protocols, infrastructure best practices, security standards, and verification requirements.

### Test Coverage

**Total Scenarios**: 18 across 4 categories

1. **Deployment Protocol** (6 scenarios: OPS-DEP-001 to OPS-DEP-006)
   - Environment validation before deployment
   - Rollback plan preparation and testing
   - Health checks after deployment
   - Smoke tests post-deployment
   - Gradual rollout strategies
   - Deployment documentation

2. **Infrastructure Focus** (5 scenarios: OPS-INFRA-001 to OPS-INFRA-005)
   - Docker configuration best practices
   - Kubernetes deployment specifications
   - CI/CD pipeline configuration
   - Infrastructure monitoring setup
   - Resource limit specifications

3. **Security Emphasis** (4 scenarios: OPS-SEC-001 to OPS-SEC-004)
   - Secrets management validation
   - Security scanning requirements
   - Vulnerability assessment protocol
   - Least privilege principle enforcement

4. **Verification Requirements** (3 scenarios: OPS-VER-001 to OPS-VER-003)
   - Manual verification steps documentation
   - Evidence collection requirements
   - Post-deployment verification checklist

### Multi-Step Workflow Tests (5 Integration Tests)

1. **test_ops_deployment_workflow**: End-to-end deployment safety
2. **test_ops_rollback_preparation**: Rollback plan validation
3. **test_ops_security_practices**: Security compliance workflow
4. **test_ops_infrastructure_validation**: Infrastructure best practices
5. **test_ops_monitoring_setup**: Monitoring and alerting configuration

## Quick Start

### Run All Ops Agent Tests

```bash
# From project root
pytest tests/eval/agents/ops/test_integration.py -v
```

### Run Specific Test Categories

```bash
# Deployment Protocol tests
pytest tests/eval/agents/ops/test_integration.py::TestOpsDeploymentProtocol -v

# Infrastructure Focus tests
pytest tests/eval/agents/ops/test_integration.py::TestOpsInfrastructure -v

# Security Emphasis tests
pytest tests/eval/agents/ops/test_integration.py::TestOpsSecurity -v

# Verification Requirements tests
pytest tests/eval/agents/ops/test_integration.py::TestOpsVerification -v

# Workflow integration tests (slower)
pytest tests/eval/agents/ops/test_integration.py::TestOpsWorkflows -v
```

### Run Individual Scenarios

```bash
# Test specific scenario by ID
pytest tests/eval/agents/ops/test_integration.py::TestOpsDeploymentProtocol::test_scenario[OPS-DEP-001] -v

# Test rollback preparation (strict threshold)
pytest tests/eval/agents/ops/test_integration.py::TestOpsDeploymentProtocol::test_scenario_strict[OPS-DEP-002-1.0] -v

# Test security scanning
pytest tests/eval/agents/ops/test_integration.py::TestOpsSecurity::test_scenario[OPS-SEC-002-0.9] -v
```

### Run Workflow Tests

```bash
# Full deployment workflow
pytest tests/eval/agents/ops/test_integration.py::TestOpsWorkflows::test_ops_deployment_workflow -v

# Rollback preparation workflow
pytest tests/eval/agents/ops/test_integration.py::TestOpsWorkflows::test_ops_rollback_preparation -v

# Security practices workflow
pytest tests/eval/agents/ops/test_integration.py::TestOpsWorkflows::test_ops_security_practices -v

# Infrastructure validation workflow
pytest tests/eval/agents/ops/test_integration.py::TestOpsWorkflows::test_ops_infrastructure_validation -v

# Monitoring setup workflow
pytest tests/eval/agents/ops/test_integration.py::TestOpsWorkflows::test_ops_monitoring_setup -v
```

## Test Structure

### Scenario-Based Tests

Each scenario test:
1. Loads scenario from `ops_scenarios.json`
2. Creates `LLMTestCase` with user request and mock compliant response
3. Applies appropriate custom metric (`DeploymentSafetyMetric` or `InfrastructureComplianceMetric`)
4. Asserts compliance using metric threshold

**Example**:
```python
def test_scenario(self, scenario_id: str, metric: DeploymentSafetyMetric):
    scenario = get_scenario_by_id(scenario_id)

    test_case = LLMTestCase(
        input=scenario["input"]["user_request"],
        actual_output=scenario["mock_response"]["compliant"],
    )

    score = metric.measure(test_case)
    assert score >= metric.threshold
```

### Workflow Integration Tests

Multi-step workflows combining multiple scenarios:

**Example: Deployment Workflow**
```python
def test_ops_deployment_workflow(self):
    # Flow: Validate env → prepare rollback → deploy → health check → smoke test
    workflow_response = """
    ## Step 1: Environment Validation
    [Checks DATABASE_URL, REDIS_URL, connectivity]

    ## Step 2: Rollback Plan
    [Documents version, prepares scripts, tests in staging]

    ## Step 3: Deployment
    [Gradual rollout with blue-green strategy]

    ## Step 4: Health Checks
    [Verifies service health and metrics]

    ## Step 5: Smoke Tests
    [Tests critical user flows]
    """

    test_case = LLMTestCase(
        input="Deploy v5.2.0 to production with full safety protocol",
        actual_output=workflow_response
    )

    metric = DeploymentSafetyMetric(threshold=0.9)
    score = metric.measure(test_case)
    assert score >= 0.9
```

## Custom Metrics

### DeploymentSafetyMetric

**Purpose**: Validate deployment safety protocols and rollback readiness

**Scoring Components**:
- Environment validation: Configuration checks, connectivity verification
- Rollback plan: Documented plan, tested in staging, timing requirements
- Health checks: Endpoint verification, log analysis, metrics validation
- Documentation: Evidence collection, deployment records

**Thresholds**:
- Standard scenarios: 0.95 (strict deployment safety)
- Rollback preparation: 1.0 (must be perfect)
- Verification requirements: 0.95-1.0 (evidence-based)

### InfrastructureComplianceMetric

**Purpose**: Validate infrastructure configuration and best practices

**Scoring Components**:
- Docker configuration: Multi-stage builds, non-root user, security patches
- Kubernetes specs: Resource limits, health checks, security context
- CI/CD pipeline: Automated testing, security scanning, deployment stages
- Monitoring: Prometheus metrics, alert rules, logging aggregation
- Security: Secrets management, vulnerability scanning, least privilege

**Thresholds**:
- Infrastructure scenarios: 0.85 (comprehensive compliance)
- Security scenarios: 0.9-0.95 (stricter for security)
- Monitoring setup: 0.85 (observability standards)

## Scenario File Integrity Tests

Validates `ops_scenarios.json` structure:

```bash
# Run integrity checks
pytest tests/eval/agents/ops/test_integration.py::TestScenarioFileIntegrity -v
```

**Checks**:
- ✓ Total scenario count: 18
- ✓ Category counts: deployment_protocol(6), infrastructure_focus(5), security_emphasis(4), verification_requirements(3)
- ✓ Required fields: scenario_id, name, category, priority, description, input, expected_behavior, success_criteria, metrics, mock_response
- ✓ Unique scenario IDs
- ✓ Valid metric references

## Expected Test Results

### Compliant Response Behavior

All scenario tests use **compliant** mock responses and should **PASS**:

```bash
# Expected output
tests/eval/agents/ops/test_integration.py::TestOpsDeploymentProtocol::test_scenario[OPS-DEP-001] PASSED
tests/eval/agents/ops/test_integration.py::TestOpsDeploymentProtocol::test_scenario[OPS-DEP-003] PASSED
tests/eval/agents/ops/test_integration.py::TestOpsSecurity::test_scenario[OPS-SEC-001-0.95] PASSED
tests/eval/agents/ops/test_integration.py::TestOpsWorkflows::test_ops_deployment_workflow PASSED
```

### Test Execution Time

- **Individual scenarios**: ~0.1-0.5 seconds each
- **Workflow tests**: ~0.5-1.0 seconds each (marked with `@pytest.mark.slow`)
- **Full test suite**: ~10-15 seconds total

## Troubleshooting

### Common Issues

#### 1. Scenario File Not Found

**Error**:
```
FileNotFoundError: Scenarios file not found: .../ops_scenarios.json
```

**Solution**:
```bash
# Verify scenarios file exists
ls -la tests/eval/scenarios/ops/ops_scenarios.json

# Check from correct directory
cd /Users/masa/Projects/claude-mpm
pytest tests/eval/agents/ops/test_integration.py -v
```

#### 2. Metric Threshold Failures

**Error**:
```
AssertionError: Scenario OPS-DEP-002 failed Deployment Safety metric
Score: 0.85 (threshold: 1.0)
```

**Cause**: Mock response doesn't demonstrate complete rollback preparation

**Solution**: Verify `ops_scenarios.json` compliant response includes:
- Current version documentation
- Rollback script preparation
- Staging rollback testing
- Timing requirements

#### 3. Invalid Metric References

**Error**:
```
AssertionError: Scenario OPS-SEC-001 references invalid metric: SecurityMetric
```

**Solution**: Only use valid metrics:
- `DeploymentSafetyMetric`
- `InfrastructureComplianceMetric`

#### 4. Missing Test Dependencies

**Error**:
```
ModuleNotFoundError: No module named 'deepeval'
```

**Solution**:
```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Or install deepeval directly
pip install deepeval
```

## Integration with CI/CD

### GitHub Actions Workflow

```yaml
name: Ops Agent Tests

on:
  pull_request:
    paths:
      - 'tests/eval/agents/ops/**'
      - 'tests/eval/metrics/ops/**'
      - 'tests/eval/scenarios/ops/**'

jobs:
  test-ops-agent:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r requirements-dev.txt

      - name: Run Ops Agent tests
        run: |
          pytest tests/eval/agents/ops/test_integration.py -v --tb=short

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: ops-agent-test-results
          path: test-results/
```

### Test Coverage Reporting

```bash
# Run with coverage
pytest tests/eval/agents/ops/test_integration.py --cov=tests.eval.metrics.ops --cov-report=html

# View coverage report
open htmlcov/index.html
```

## Contributing

### Adding New Scenarios

1. **Add scenario to `ops_scenarios.json`**:
   ```json
   {
     "scenario_id": "OPS-DEP-007",
     "name": "Canary Deployment Strategy",
     "category": "deployment_protocol",
     "priority": "high",
     "mock_response": {
       "compliant": "...",
       "non_compliant": "..."
     }
   }
   ```

2. **Add test case** (if new category):
   ```python
   @pytest.mark.parametrize("scenario_id", ["OPS-DEP-007"])
   def test_scenario(self, scenario_id: str, metric: DeploymentSafetyMetric):
       # Test implementation
   ```

3. **Update scenario counts**:
   - Update `total_scenarios` in JSON
   - Update category count
   - Update integrity tests

4. **Run tests**:
   ```bash
   pytest tests/eval/agents/ops/test_integration.py -v
   ```

### Adding New Workflow Tests

1. **Identify scenario combinations** (e.g., OPS-DEP-001 + OPS-DEP-002 + OPS-VER-003)

2. **Create workflow test**:
   ```python
   def test_ops_new_workflow(self):
       """
       Integration test: [Workflow name]

       Flow: Step 1 → Step 2 → Step 3
       Combined scenarios: OPS-XXX-001, OPS-XXX-002
       Success criteria: [List criteria]
       Metrics: [Metric name] (threshold X.X)
       """
       workflow_response = """..."""
       test_case = LLMTestCase(input="...", actual_output=workflow_response)
       metric = DeploymentSafetyMetric(threshold=0.9)
       score = metric.measure(test_case)
       assert score >= 0.9
   ```

3. **Mark with `@pytest.mark.slow`** for multi-step workflows

## References

- **Scenarios**: `tests/eval/scenarios/ops/ops_scenarios.json`
- **Metrics**: `tests/eval/metrics/ops/`
- **DeepEval Docs**: https://docs.confident-ai.com/
- **Sprint 5 Epic**: #111 (Ops Agent Test Harness)

## Success Criteria

- ✅ All 18 scenarios have corresponding tests
- ✅ 5 workflow integration tests implemented
- ✅ Scenario file integrity validated
- ✅ Metrics properly applied with correct thresholds
- ✅ Both compliant and non-compliant responses tested
- ✅ Test execution time < 20 seconds for full suite
- ✅ README documentation complete with examples
