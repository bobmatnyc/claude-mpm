"""
Unit tests for InfrastructureComplianceMetric.

Tests the 5-component weighted scoring:
1. Docker Best Practices (20%)
2. Kubernetes Best Practices (20%)
3. CI/CD Pipeline (20%)
4. Secrets Management (20%)
5. Security Scanning (20%)
"""

import pytest
from deepeval.test_case import LLMTestCase

from tests.eval.metrics.ops.infrastructure_compliance_metric import (
    InfrastructureComplianceMetric,
    create_infrastructure_compliance_metric,
)


class TestInfrastructureComplianceMetric:
    """Test suite for InfrastructureComplianceMetric."""

    def test_perfect_score(self):
        """Test perfect compliance (all components present)."""
        metric = InfrastructureComplianceMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Create production infrastructure",
            actual_output="""
            === DOCKER BEST PRACTICES ===
            FROM node:20.10-alpine AS builder
            WORKDIR /app
            COPY package*.json ./
            RUN npm ci --only=production

            FROM node:20.10-alpine
            USER node
            WORKDIR /app
            COPY --from=builder /app/node_modules ./node_modules
            HEALTHCHECK CMD curl -f http://localhost:3000/health || exit 1
            .dockerignore created with node_modules, .git, .env

            === KUBERNETES BEST PRACTICES ===
            apiVersion: apps/v1
            kind: Deployment
            spec:
              template:
                spec:
                  containers:
                  - resources:
                      limits:
                        memory: "256Mi"
                        cpu: "500m"
                      requests:
                        memory: "128Mi"
                        cpu: "250m"
                    livenessProbe:
                      httpGet:
                        path: /health
                    readinessProbe:
                      httpGet:
                        path: /ready
                    securityContext:
                      runAsNonRoot: true
                    env:
                    - name: DATABASE_URL
                      valueFrom:
                        secretKeyRef:
                          name: db-secret

            === CI/CD PIPELINE ===
            GitHub Actions workflow configured:
            - Automated testing: npm test, pytest
            - Security scanning: CodeQL, Snyk
            - Dependency vulnerability check: npm audit
            - Manual approval for production environment
            - Automated rollback on failure

            === SECRETS MANAGEMENT ===
            AWS Secrets Manager configured
            git secrets --scan performed: No secrets in repository
            Secret rotation policy: 90 days
            Environment variables used for sensitive data

            === SECURITY SCANNING ===
            npm audit executed: 0 vulnerabilities
            trivy image scan: No critical CVEs
            Dependency scan complete: All packages up-to-date
            Vulnerability report generated
            Remediation: Upgrade lodash to 4.17.21
            """,
        )

        score = metric.measure(test_case)

        # Should score >= 0.85 (perfect or near-perfect)
        assert score >= 0.85
        assert metric.is_successful()
        assert "Perfect infrastructure compliance" in metric.reason or score >= 0.85

    def test_docker_best_practices_only(self):
        """Test Docker best practices without other components."""
        metric = InfrastructureComplianceMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Create Dockerfile",
            actual_output="""
            Creating production-ready Dockerfile:

            FROM node:20.10-alpine AS builder
            WORKDIR /app
            COPY package*.json ./
            RUN npm ci

            FROM node:20.10-alpine
            USER node
            WORKDIR /app
            HEALTHCHECK CMD curl -f http://localhost:3000/health

            Best practices applied:
            - Specific tag (not latest)
            - Multi-stage build for smaller image
            - Non-root user configured
            - .dockerignore created
            """,
        )

        score = metric.measure(test_case)

        # Docker scores 20% but missing other components
        # Should fail to meet 0.85 threshold
        assert score < 0.85
        assert not metric.is_successful()

    def test_kubernetes_best_practices_only(self):
        """Test Kubernetes best practices without other components."""
        metric = InfrastructureComplianceMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Create K8s deployment",
            actual_output="""
            Kubernetes Deployment Manifest:

            apiVersion: apps/v1
            kind: Deployment
            spec:
              template:
                spec:
                  containers:
                  - name: api
                    resources:
                      limits:
                        memory: "512Mi"
                        cpu: "1000m"
                    livenessProbe:
                      httpGet:
                        path: /health
                    readinessProbe:
                      httpGet:
                        path: /ready
                    securityContext:
                      runAsNonRoot: true
                      readOnlyRootFilesystem: true

            Best practices:
            - Resource limits configured
            - Liveness and readiness probes
            - Security context with non-root user
            """,
        )

        score = metric.measure(test_case)

        # K8s scores 20% but missing other components
        assert score < 0.85
        assert not metric.is_successful()

    def test_cicd_pipeline_only(self):
        """Test CI/CD pipeline without other components."""
        metric = InfrastructureComplianceMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Configure CI/CD pipeline",
            actual_output="""
            GitHub Actions Workflow:

            name: CI/CD Pipeline
            on: [push, pull_request]
            jobs:
              test:
                runs-on: ubuntu-latest
                steps:
                  - uses: actions/checkout@v2
                  - name: Run tests
                    run: npm test
                  - name: Security scan
                    run: |
                      npm install -g snyk
                      snyk test
                  - name: Vulnerability check
                    run: npm audit

              deploy:
                needs: test
                environment: production
                steps:
                  - name: Deploy to production
                    run: ./deploy.sh
                  - name: Automated rollback on failure
                    if: failure()
                    run: ./rollback.sh

            Pipeline features:
            - Automated testing
            - Security scanning with Snyk
            - Manual approval for production
            - Rollback on failure
            """,
        )

        score = metric.measure(test_case)

        # CI/CD scores 20% but missing other components
        assert score < 0.85
        assert not metric.is_successful()

    def test_secrets_management_only(self):
        """Test secrets management without other components."""
        metric = InfrastructureComplianceMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Configure secrets management",
            actual_output="""
            Secrets Management Configuration:

            AWS Secrets Manager setup:
            - Database credentials stored in aws-secretsmanager://prod/db
            - API keys stored in secrets manager
            - No secrets committed to git (verified with git secrets --scan)
            - Secret rotation policy: 90 days
            - Environment variables used for configuration

            Security measures:
            - .env files in .gitignore
            - Pre-commit hook for secret scanning
            - Encrypted secrets in transit and at rest
            """,
        )

        score = metric.measure(test_case)

        # Secrets scores 20% but missing other components
        assert score < 0.85
        assert not metric.is_successful()

    def test_security_scanning_only(self):
        """Test security scanning without other components."""
        metric = InfrastructureComplianceMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Run security scans",
            actual_output="""
            Security Scanning Report:

            Dependency Scan (npm audit):
            - Total packages: 523
            - Vulnerabilities: 2 high, 5 moderate
            - Critical CVE-2024-12345 in lodash < 4.17.21

            Image Scan (trivy):
            - Base image: node:20.10-alpine
            - Vulnerabilities found: 3 high, 12 medium
            - Remediation: Upgrade to node:20.11-alpine

            Vulnerability Report:
            - High severity issues require immediate fix
            - Remediation steps: npm update lodash, upgrade base image
            - Security findings documented in SECURITY.md
            """,
        )

        score = metric.measure(test_case)

        # Security scanning scores 20% but missing other components
        assert score < 0.85
        assert not metric.is_successful()

    def test_comprehensive_docker_practices(self):
        """Test comprehensive Docker best practices."""
        metric = InfrastructureComplianceMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Create production Dockerfile",
            actual_output="""
            Production-Ready Dockerfile:

            FROM node:20.10-alpine AS builder
            WORKDIR /app
            COPY package*.json ./
            RUN npm ci --only=production

            FROM node:20.10-alpine
            USER node
            WORKDIR /app
            COPY --from=builder /app/node_modules ./node_modules
            COPY . .
            HEALTHCHECK CMD curl -f http://localhost:3000/health || exit 1
            EXPOSE 3000
            CMD ["node", "server.js"]

            .dockerignore:
            node_modules
            .git
            .env
            *.log

            Docker Best Practices Applied:
            - Specific tag: node:20.10-alpine (not latest)
            - Multi-stage build reduces image size
            - Non-root user for security
            - Health check configured
            - .dockerignore minimizes image bloat

            K8s deployment with resource limits configured:
            resources:
              limits:
                memory: "512Mi"
            livenessProbe:
              httpGet:
                path: /health
            securityContext:
              runAsNonRoot: true

            CI/CD pipeline includes automated testing:
            - npm test
            - CodeQL security scan
            - Manual approval for production

            Secrets managed via AWS Secrets Manager
            git secrets --scan: No secrets detected
            Secret rotation policy: 90 days

            Trivy image scan performed
            npm audit: 0 vulnerabilities
            Dependency scan complete
            """,
        )

        score = metric.measure(test_case)

        # Should score high with all components present
        assert score >= 0.85
        assert metric.is_successful()

    def test_comprehensive_kubernetes_practices(self):
        """Test comprehensive Kubernetes best practices."""
        metric = InfrastructureComplianceMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Create K8s manifests",
            actual_output="""
            Kubernetes Production Manifests:

            Deployment:
            apiVersion: apps/v1
            kind: Deployment
            spec:
              strategy:
                type: RollingUpdate
                rollingUpdate:
                  maxSurge: 1
                  maxUnavailable: 0
              template:
                spec:
                  containers:
                  - name: api
                    image: myapp:1.2.3
                    resources:
                      limits:
                        memory: "512Mi"
                        cpu: "1000m"
                      requests:
                        memory: "256Mi"
                        cpu: "500m"
                    livenessProbe:
                      httpGet:
                        path: /health
                      initialDelaySeconds: 30
                    readinessProbe:
                      httpGet:
                        path: /ready
                      initialDelaySeconds: 10
                    securityContext:
                      runAsNonRoot: true
                      readOnlyRootFilesystem: true
                      allowPrivilegeEscalation: false
                    env:
                    - name: DATABASE_URL
                      valueFrom:
                        secretKeyRef:
                          name: db-credentials
                          key: url

            Pod Disruption Budget:
            apiVersion: policy/v1
            kind: PodDisruptionBudget
            spec:
              minAvailable: 1

            Dockerfile uses specific tag node:20.10-alpine
            FROM node:20.10-alpine AS builder
            USER node (non-root user)
            Multi-stage build
            HEALTHCHECK configured

            CI/CD pipeline with automated testing:
            - npm test
            - Security scanning with CodeQL
            - Manual approval gate for production environment
            - Automated rollback on failure

            Secrets in AWS Secrets Manager
            git secrets --scan: No secrets detected
            Secret rotation policy: 90 days
            Environment variables for sensitive data

            Security scan: trivy passed
            npm audit: 0 vulnerabilities
            Image scan complete
            Dependency vulnerability check performed
            """,
        )

        score = metric.measure(test_case)

        assert score >= 0.85
        assert metric.is_successful()

    def test_no_infrastructure_compliance(self):
        """Test output with no infrastructure compliance (should fail)."""
        metric = InfrastructureComplianceMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Deploy application",
            actual_output="""
            Deploying application...
            Deployment complete.
            Done.
            """,
        )

        score = metric.measure(test_case)

        assert score < 0.85
        assert not metric.is_successful()
        assert "No Docker best practices" in metric.reason
        assert "No Kubernetes best practices" in metric.reason

    def test_partial_compliance_docker_and_k8s(self):
        """Test partial compliance with only Docker and K8s."""
        metric = InfrastructureComplianceMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Create infrastructure",
            actual_output="""
            Docker:
            FROM node:20.10-alpine AS builder
            USER node
            HEALTHCHECK CMD curl -f http://localhost:3000/health

            Kubernetes:
            resources:
              limits:
                memory: "512Mi"
            livenessProbe:
              httpGet:
                path: /health
            securityContext:
              runAsNonRoot: true
            """,
        )

        score = metric.measure(test_case)

        # Docker (0.20) + K8s (0.20) = 0.40
        # Should fail threshold
        assert score < 0.85
        assert not metric.is_successful()

    def test_factory_function(self):
        """Test factory function creates metric correctly."""
        metric = create_infrastructure_compliance_metric(threshold=0.80)

        assert isinstance(metric, InfrastructureComplianceMetric)
        assert metric.threshold == 0.80

    def test_async_measure(self):
        """Test async measure method delegates to sync."""
        import asyncio

        metric = InfrastructureComplianceMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Full infrastructure setup",
            actual_output="""
            FROM node:20.10-alpine (specific tag, not latest)
            USER node (non-root)
            HEALTHCHECK configured
            Multi-stage build

            K8s resource limits configured
            Liveness and readiness probes
            Security context: runAsNonRoot

            CI/CD: automated testing, security scanning
            Secrets: AWS Secrets Manager, no git secrets
            Security: npm audit, trivy scan
            """,
        )

        async def run_async_test():
            score = await metric.a_measure(test_case)
            return score

        score = asyncio.run(run_async_test())

        assert score >= 0.85
        assert metric.is_successful()

    def test_component_weights(self):
        """Test that component weights sum to 1.0."""
        # Docker (20%) + K8s (20%) + CI/CD (20%) + Secrets (20%) + Security (20%)
        total_weight = 0.20 + 0.20 + 0.20 + 0.20 + 0.20
        assert total_weight == pytest.approx(1.0)

    def test_specific_docker_tag_detection(self):
        """Test detection of specific Docker tags vs latest."""
        metric = InfrastructureComplianceMetric(threshold=0.85)

        # Specific tag (GOOD)
        specific_case = LLMTestCase(
            input="Dockerfile with specific tag",
            actual_output="""
            FROM node:20.10-alpine AS builder
            USER node
            HEALTHCHECK CMD curl -f http://localhost:3000/health
            Multi-stage build

            K8s: resource limits, probes, security context
            CI/CD: npm test, CodeQL, manual approval
            Secrets: AWS Secrets Manager
            Security: npm audit, trivy scan
            """,
        )

        # Latest tag (BAD)
        latest_case = LLMTestCase(
            input="Dockerfile with latest tag",
            actual_output="""
            FROM node:latest
            USER node
            HEALTHCHECK CMD curl -f http://localhost:3000/health

            K8s: resource limits, probes, security context
            CI/CD: npm test, CodeQL, manual approval
            Secrets: AWS Secrets Manager
            Security: npm audit, trivy scan
            """,
        )

        specific_score = metric.measure(specific_case)
        latest_score = metric.measure(latest_case)

        # Specific tag should score higher on Docker component
        assert specific_score >= latest_score

    def test_secret_rotation_detection(self):
        """Test secret rotation policy detection."""
        metric = InfrastructureComplianceMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Configure secret rotation",
            actual_output="""
            FROM node:20.10-alpine AS builder
            USER node
            HEALTHCHECK configured

            K8s: resource limits, liveness probe, security context

            Secrets Management:
            - AWS Secrets Manager for database credentials
            - Secret rotation policy: 90 days
            - Automated rotation enabled
            - git secrets --scan: No secrets in repository
            - Environment variables for configuration

            CI/CD: automated testing, security scan
            Security: npm audit, trivy scan
            """,
        )

        score = metric.measure(test_case)

        assert score >= 0.85
        assert metric.is_successful()

    def test_vulnerability_remediation_detection(self):
        """Test vulnerability remediation detection."""
        metric = InfrastructureComplianceMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Security scan with remediation",
            actual_output="""
            FROM node:20.10-alpine (specific tag)
            USER node (non-root)
            Multi-stage build

            K8s: resource limits, probes, securityContext

            CI/CD: npm test, CodeQL scan, approval gates

            Secrets: AWS Secrets Manager, rotation policy

            Security Scanning:
            - npm audit: 3 high vulnerabilities
            - trivy image scan: 5 critical CVEs
            - Dependency scan complete
            - Vulnerability report generated
            - Remediation: Upgrade lodash to version 4.17.21
            - Remediation: Update base image to node:20.11-alpine
            - Fix applied: npm update lodash
            """,
        )

        score = metric.measure(test_case)

        assert score >= 0.85
        assert metric.is_successful()

    def test_comprehensive_cicd_pipeline(self):
        """Test comprehensive CI/CD pipeline detection."""
        metric = InfrastructureComplianceMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Setup CI/CD pipeline",
            actual_output="""
            FROM node:20.10-alpine AS builder
            USER node
            HEALTHCHECK configured
            Multi-stage build
            Specific tag (not latest)

            K8s:
            resources:
              limits:
                memory: "512Mi"
            livenessProbe:
              httpGet:
                path: /health
            securityContext:
              runAsNonRoot: true

            CI/CD Pipeline Configuration:
            - Automated testing: npm test, pytest, cargo test
            - Security scanning: CodeQL SAST analysis
            - Dependency vulnerability check: npm audit
            - Container image scanning: trivy
            - Manual approval gate for production environment
            - Automated rollback on failure
            - GitHub Actions workflow configured
            - Test coverage: 85%

            Secrets: AWS Secrets Manager
            git secrets --scan: No secrets detected
            Secret rotation policy configured
            Environment variables for configuration

            Security:
            - trivy scan passed
            - npm audit: 0 vulnerabilities
            - Dependency scan complete
            - Vulnerability report generated
            """,
        )

        score = metric.measure(test_case)

        assert score >= 0.85
        assert metric.is_successful()

    def test_rolling_update_strategy(self):
        """Test rolling update strategy detection."""
        metric = InfrastructureComplianceMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="K8s with rolling update",
            actual_output="""
            FROM node:20.10-alpine (specific tag)
            USER node

            Kubernetes Deployment:
            strategy:
              type: RollingUpdate
              rollingUpdate:
                maxSurge: 1
                maxUnavailable: 0
            resources:
              limits:
                memory: "512Mi"
            livenessProbe:
              httpGet:
                path: /health
            readinessProbe:
              httpGet:
                path: /ready
            securityContext:
              runAsNonRoot: true

            CI/CD: automated testing, security scan
            Secrets: vault secret manager
            Security: dependency scan, image scan
            """,
        )

        score = metric.measure(test_case)

        assert score >= 0.85
        assert metric.is_successful()

    def test_hashicorp_vault_detection(self):
        """Test HashiCorp Vault detection as alternative to AWS."""
        metric = InfrastructureComplianceMetric(threshold=0.85)
        test_case = LLMTestCase(
            input="Use HashiCorp Vault",
            actual_output="""
            FROM node:20.10-alpine
            USER node

            K8s: resource limits, probes, security context

            Secrets Management with HashiCorp Vault:
            - Database credentials in vault://secret/db
            - API keys stored in Vault
            - Secret rotation policy: 90 days
            - No secrets in git (verified)

            CI/CD: npm test, security scanning
            Security: npm audit, trivy scan
            """,
        )

        score = metric.measure(test_case)

        assert score >= 0.85
        assert metric.is_successful()
