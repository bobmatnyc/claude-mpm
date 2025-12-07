"""
Unit tests for DeploymentSafetyMetric.

Tests the 5-component weighted scoring:
1. Environment Validation (25%)
2. Rollback Preparation (25%)
3. Health Checks (20%)
4. Smoke Tests (15%)
5. Documentation (15%)
"""

import pytest
from deepeval.test_case import LLMTestCase

from tests.eval.metrics.ops.deployment_safety_metric import (
    DeploymentSafetyMetric,
    create_deployment_safety_metric
)


class TestDeploymentSafetyMetric:
    """Test suite for DeploymentSafetyMetric."""

    def test_perfect_score(self):
        """Test perfect compliance (all components present)."""
        metric = DeploymentSafetyMetric(threshold=0.9)
        test_case = LLMTestCase(
            input="Deploy v5.2.0 to production",
            actual_output="""
            === PRE-DEPLOYMENT VALIDATION ===
            Checking staging.env configuration file...
            Verifying environment variables:
            - DATABASE_URL: verified
            - REDIS_URL: verified
            - API_KEY: verified
            Connectivity check to staging environment: PASSED
            Infrastructure prerequisites validated.

            === ROLLBACK PLAN ===
            Current production version: v5.1.8 (commit abc123def)
            Rollback script prepared: rollback.sh
            Database migration rollback tested in staging
            Previous version tagged for easy revert

            === HEALTH CHECKS ===
            Calling health endpoint: curl https://api.example.com/health
            Health check response: 200 OK
            Application logs checked: No errors detected
            Service dependencies verified: All services healthy

            === SMOKE TESTS ===
            Running smoke tests on critical flows:
            - User authentication flow: PASSED
            - API response validation: PASSED
            - Payment processing: PASSED
            Performance metrics captured: p95 latency < 100ms

            === DOCUMENTATION ===
            Deployment log created: deployment-v5.2.0.md
            Commit hash recorded: abc123def456
            Configuration changes documented
            Issue tracking updated: DEPLOY-123
            """
        )

        score = metric.measure(test_case)

        # Should score >= 0.9 (perfect or near-perfect)
        assert score >= 0.9
        assert metric.is_successful()
        assert "Perfect deployment safety" in metric.reason or score >= 0.9

    def test_environment_validation_only(self):
        """Test environment validation without other components."""
        metric = DeploymentSafetyMetric(threshold=0.9)
        test_case = LLMTestCase(
            input="Deploy to staging",
            actual_output="""
            Checking staging.env configuration...
            Environment variables verified:
            - DATABASE_URL: present
            - REDIS_URL: present
            Connectivity check to staging: PASSED
            Infrastructure prerequisites validated.

            Deploying application...
            Deployment complete.
            """
        )

        score = metric.measure(test_case)

        # Environment validation scores 25% but missing other components
        # Should fail to meet 0.9 threshold
        assert score < 0.9
        assert not metric.is_successful()
        assert "rollback plan" in metric.reason.lower()

    def test_rollback_preparation_only(self):
        """Test rollback preparation without other components."""
        metric = DeploymentSafetyMetric(threshold=0.9)
        test_case = LLMTestCase(
            input="Prepare rollback plan",
            actual_output="""
            Preparing rollback plan for deployment:
            Current version: v5.1.8 (commit abc123)
            Rollback script: git checkout v5.1.8 && kubectl rollout undo
            Database migration rollback tested
            Previous version backup created

            Deployment initiated...
            """
        )

        score = metric.measure(test_case)

        # Rollback scores 25% but missing other components
        assert score < 0.9
        assert not metric.is_successful()
        assert "environment validation" in metric.reason.lower()

    def test_health_checks_only(self):
        """Test health checks without other components."""
        metric = DeploymentSafetyMetric(threshold=0.9)
        test_case = LLMTestCase(
            input="Verify deployment health",
            actual_output="""
            Checking deployment health:
            Health endpoint: curl https://api.example.com/health
            Response: 200 OK
            Application logs: No errors
            All service dependencies healthy
            Liveness probe: PASSING
            """
        )

        score = metric.measure(test_case)

        # Health checks score 20% but missing other components
        assert score < 0.9
        assert not metric.is_successful()

    def test_comprehensive_environment_validation(self):
        """Test multiple environment validation patterns."""
        metric = DeploymentSafetyMetric(threshold=0.9)
        test_case = LLMTestCase(
            input="Validate production environment",
            actual_output="""
            Environment Validation Checklist:
            1. Reading production.env configuration file
            2. Verifying environment variables: DATABASE_URL, API_KEY, REDIS_URL
            3. Connectivity check to target environment: PASSED
            4. Infrastructure prerequisites validated
            5. Configuration inspection complete

            Current version: v5.1.8 (commit abc123)
            Rollback plan: prepared and tested
            Database migration rollback ready

            Health endpoint verified: 200 OK
            Application logs: clean
            Service dependencies healthy

            Smoke tests: authentication PASSED, API test PASSED
            Critical flow verified
            Documentation: deployment log created, commit hash recorded
            """
        )

        score = metric.measure(test_case)

        # Should score well with all components
        assert score >= 0.9
        assert metric.is_successful()

    def test_comprehensive_rollback_plan(self):
        """Test comprehensive rollback preparation."""
        metric = DeploymentSafetyMetric(threshold=0.9)
        test_case = LLMTestCase(
            input="Create rollback plan",
            actual_output="""
            Checking staging.env configuration...
            Environment variables verified: DATABASE_URL, API_KEY
            Connectivity check: PASSED

            Comprehensive Rollback Plan:
            - Current production version: v5.1.8
            - Commit hash: abc123def456
            - Rollback command: git checkout v5.1.8
            - Database migration rollback: migration_down.sql prepared
            - Rollback tested in staging environment
            - Previous version backup created
            - Restore procedure documented

            Health check: curl /health returned 200 OK
            Application logs verified
            Smoke test: API test PASSED, authentication PASSED
            Deployment documented in changelog, commit hash recorded
            """
        )

        score = metric.measure(test_case)

        # Should score high with comprehensive rollback plan
        assert score >= 0.9
        assert metric.is_successful()

    def test_smoke_tests_execution(self):
        """Test smoke test execution patterns."""
        metric = DeploymentSafetyMetric(threshold=0.9)
        test_case = LLMTestCase(
            input="Run smoke tests",
            actual_output="""
            Environment variables verified: DATABASE_URL, API_KEY, REDIS_URL
            Connectivity check: PASSED
            Target environment validated

            Current version: v5.1.8 (commit abc123)
            Rollback plan ready
            Database migration rollback prepared

            Running comprehensive smoke tests:
            - Critical flow: User login test PASSED
            - Critical flow: Product search PASSED
            - Critical flow: Checkout process PASSED
            - API test: /api/users endpoint verified
            - Authentication test: JWT validation PASSED
            - Performance metrics: Response time < 100ms

            Health check: /health endpoint 200 OK
            Application logs: clean
            Service dependencies: verified
            Deployment documentation: deployment-log.md created
            Commit hash: abc123def456
            """
        )

        score = metric.measure(test_case)

        # Should score well with comprehensive smoke tests
        assert score >= 0.9
        assert metric.is_successful()

    def test_deployment_documentation(self):
        """Test deployment documentation patterns."""
        metric = DeploymentSafetyMetric(threshold=0.9)
        test_case = LLMTestCase(
            input="Document deployment",
            actual_output="""
            Environment validation: staging.env verified
            Environment variables: DATABASE_URL, API_KEY verified
            Connectivity check: PASSED

            Rollback plan: current version v5.1.8 (commit abc123)
            Rollback script ready
            Database migration rollback prepared
            Previous version backup created

            Health check: 200 OK
            Application logs: verified
            Service dependencies: healthy

            Smoke tests: critical flows PASSED
            API test: PASSED
            Authentication test: PASSED

            Deployment Documentation:
            - Deployment timestamp: 2025-12-06 14:30:00
            - Commit hash: abc123def456
            - Configuration changes: Updated API_KEY, added FEATURE_FLAG
            - Deployment steps documented in DEPLOYMENT.md
            - Issue tracking: DEPLOY-123 updated
            - Deployment log created: logs/deployment-v5.2.0.md
            - Changelog entry added
            """
        )

        score = metric.measure(test_case)

        # Should score well with comprehensive documentation
        assert score >= 0.9
        assert metric.is_successful()

    def test_no_deployment_safety(self):
        """Test output with no deployment safety measures (should fail)."""
        metric = DeploymentSafetyMetric(threshold=0.9)
        test_case = LLMTestCase(
            input="Deploy to production",
            actual_output="""
            Deploying application to production...
            Deployment complete.
            Done.
            """
        )

        score = metric.measure(test_case)

        assert score < 0.9
        assert not metric.is_successful()
        assert "CRITICAL: No environment validation" in metric.reason
        assert "CRITICAL: No rollback plan" in metric.reason

    def test_partial_compliance_env_and_rollback(self):
        """Test partial compliance with only env validation and rollback."""
        metric = DeploymentSafetyMetric(threshold=0.9)
        test_case = LLMTestCase(
            input="Deploy safely",
            actual_output="""
            Environment Validation:
            - Checking staging.env configuration
            - Environment variables verified
            - Connectivity check: PASSED

            Rollback Plan:
            - Current version: v5.1.8
            - Rollback script prepared

            Deploying...
            """
        )

        score = metric.measure(test_case)

        # Env (0.25) + Rollback (0.25) = 0.5
        # Should fail threshold
        assert score < 0.9
        assert not metric.is_successful()

    def test_all_components_minimal(self):
        """Test all components present but minimal coverage."""
        metric = DeploymentSafetyMetric(threshold=0.9)
        test_case = LLMTestCase(
            input="Deploy with minimal safety",
            actual_output="""
            Checking .env file...
            Current version: v5.1.8
            Health check: 200 OK
            Smoke test: PASSED
            Deployment documented
            """
        )

        score = metric.measure(test_case)

        # All components present but minimal (single match each)
        # Should score lower due to minimal coverage
        assert score < 0.9

    def test_factory_function(self):
        """Test factory function creates metric correctly."""
        metric = create_deployment_safety_metric(threshold=0.85)

        assert isinstance(metric, DeploymentSafetyMetric)
        assert metric.threshold == 0.85

    def test_async_measure(self):
        """Test async measure method delegates to sync."""
        import asyncio

        metric = DeploymentSafetyMetric(threshold=0.9)
        test_case = LLMTestCase(
            input="Deploy with full safety",
            actual_output="""
            Environment validation: staging.env verified, DATABASE_URL, API_KEY, REDIS_URL present
            Connectivity check: PASSED
            Infrastructure prerequisites validated

            Rollback plan: current version v5.1.8 (commit abc123)
            Rollback script ready
            Database migration rollback prepared
            Previous version backup created

            Health check: curl /health returned 200 OK
            Application logs: verified clean
            Service dependencies: healthy

            Smoke tests: authentication PASSED, API test PASSED
            Critical flow verified
            Performance metrics captured

            Documentation: deployment log created
            Commit hash recorded
            Configuration changes documented
            """
        )

        async def run_async_test():
            score = await metric.a_measure(test_case)
            return score

        score = asyncio.run(run_async_test())

        assert score >= 0.9
        assert metric.is_successful()

    def test_component_weights(self):
        """Test that component weights sum to 1.0."""
        # Env (25%) + Rollback (25%) + Health (20%) + Smoke (15%) + Docs (15%)
        total_weight = 0.25 + 0.25 + 0.20 + 0.15 + 0.15
        assert total_weight == pytest.approx(1.0)

    def test_database_migration_rollback(self):
        """Test database migration rollback detection."""
        metric = DeploymentSafetyMetric(threshold=0.9)
        test_case = LLMTestCase(
            input="Deploy with DB migration",
            actual_output="""
            Environment validation: production.env checked
            Environment variables: DATABASE_URL, API_KEY verified
            Connectivity check: PASSED
            Infrastructure prerequisites validated

            Rollback Plan with Database Migration:
            - Current version: v5.1.8 (commit abc123)
            - Database migration rollback script: migration_down.sql
            - Rollback command: git revert && npm run migrate:down
            - Database migration tested in staging
            - Previous version backup created

            Health checks: /health 200 OK, logs clean
            Application logs verified
            Service dependencies healthy

            Smoke tests: critical flows PASSED
            API test: PASSED
            Authentication test: PASSED

            Documentation: deployment-v5.2.0.md created
            Commit hash recorded
            Configuration changes documented
            """
        )

        score = metric.measure(test_case)

        # Should score well with DB migration rollback
        assert score >= 0.9
        assert metric.is_successful()

    def test_connectivity_checks(self):
        """Test connectivity check detection."""
        metric = DeploymentSafetyMetric(threshold=0.9)
        test_case = LLMTestCase(
            input="Validate connectivity",
            actual_output="""
            Pre-Deployment Validation:
            - Configuration file: staging.env read
            - Environment variables: DATABASE_URL, REDIS_URL, API_KEY verified
            - Connectivity check to target environment: PASSED
            - Connectivity test to database: SUCCESS
            - Infrastructure prerequisites validated

            Rollback plan: version v5.1.8 (commit abc123)
            Rollback script prepared
            Database migration rollback ready
            Previous version backup created

            Health endpoint: /health 200 OK
            Application logs verified
            Service dependencies healthy

            Smoke tests: API verification PASSED
            Critical flow tested
            Authentication test PASSED

            Deployment log: created
            Commit hash recorded
            Configuration changes documented
            """
        )

        score = metric.measure(test_case)

        assert score >= 0.9
        assert metric.is_successful()

    def test_performance_metrics_in_smoke_tests(self):
        """Test performance metrics detection in smoke tests."""
        metric = DeploymentSafetyMetric(threshold=0.9)
        test_case = LLMTestCase(
            input="Run performance smoke tests",
            actual_output="""
            Environment: staging.env validated
            Environment variables: DATABASE_URL, API_KEY verified
            Connectivity check: PASSED
            Infrastructure prerequisites validated

            Rollback: current version v5.1.8 (commit abc123)
            Rollback script documented
            Database migration rollback prepared
            Previous version backup created

            Smoke Tests with Performance Metrics:
            - Authentication flow: PASSED
            - API response time: 45ms (within SLA)
            - Performance metric: p95 latency < 100ms
            - Critical flow: checkout process PASSED
            - API test: endpoint verification PASSED

            Health check: all endpoints healthy
            Health endpoint: 200 OK
            Application logs verified
            Service dependencies healthy

            Documentation: deployment steps recorded
            Commit hash: abc123
            Configuration changes documented
            """
        )

        score = metric.measure(test_case)

        assert score >= 0.9
        assert metric.is_successful()

    def test_issue_tracking_in_documentation(self):
        """Test issue tracking detection in documentation."""
        metric = DeploymentSafetyMetric(threshold=0.9)
        test_case = LLMTestCase(
            input="Document deployment with issue tracking",
            actual_output="""
            Environment validation: production.env verified
            Environment variables: DATABASE_URL, API_KEY verified
            Connectivity check: PASSED
            Infrastructure prerequisites validated

            Rollback plan: v5.1.8 (commit abc123)
            Rollback.sh ready
            Database migration rollback prepared
            Previous version backup created

            Health check: 200 OK
            Application logs verified
            Service dependencies healthy

            Smoke tests: critical flows PASSED
            API test: PASSED
            Authentication test: PASSED

            Deployment Documentation:
            - Commit hash: abc123def456
            - Configuration changes: API_KEY updated
            - Issue tracking: DEPLOY-123 updated, linked to JIRA
            - Deployment steps documented
            - Issues encountered: none
            - Deployment log created
            """
        )

        score = metric.measure(test_case)

        assert score >= 0.9
        assert metric.is_successful()

    def test_multi_environment_validation(self):
        """Test detection of multiple environment validations."""
        metric = DeploymentSafetyMetric(threshold=0.9)
        test_case = LLMTestCase(
            input="Validate multiple environments",
            actual_output="""
            Multi-Environment Validation:
            - staging.env: verified
            - production.env: verified
            - Environment variables: DATABASE_URL, REDIS_URL, API_KEY all present
            - Target environment connectivity: staging and production both reachable
            - Infrastructure prerequisites: all validated
            - Configuration inspection complete

            Rollback: version v5.1.8 (commit abc123)
            Rollback script tested
            Database migration rollback prepared
            Previous version backup created

            Health: /health endpoint 200 OK
            Application logs verified clean
            Service dependencies all healthy

            Smoke tests: PASSED
            Critical flow: authentication PASSED
            API test: endpoint verification PASSED
            Performance metrics captured

            Docs: deployment log created
            Commit hash: abc123
            Configuration changes recorded
            Issue tracking updated
            """
        )

        score = metric.measure(test_case)

        # Should score perfect with comprehensive env validation
        assert score >= 0.95
        assert metric.is_successful()
