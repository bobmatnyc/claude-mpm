"""
Infrastructure Compliance Metric for Ops Agent Testing.

This metric evaluates Ops Agent compliance with infrastructure best practices:
- Docker best practices (specific tags, multi-stage, non-root, health checks)
- Kubernetes best practices (resource limits, probes, security context)
- CI/CD pipeline (automated testing, security scanning, approval gates)
- Secrets management (no git secrets, secret manager, rotation)
- Security scanning (dependency scan, image scan, vulnerability reporting)

Scoring Algorithm (weighted):
1. Docker Best Practices (20%): Specific tags, multi-stage, non-root
2. Kubernetes Best Practices (20%): Resource limits, probes, security
3. CI/CD Pipeline (20%): Testing, security scan, approval
4. Secrets Management (20%): No git secrets, secret manager, rotation
5. Security Scanning (20%): Dependency scan, image scan, remediation

Threshold: 0.85 (85% compliance required)

Example:
    metric = InfrastructureComplianceMetric(threshold=0.85)
    test_case = LLMTestCase(
        input="Create Dockerfile for Node.js API",
        actual_output='''FROM node:20.10-alpine AS builder
        USER node
        HEALTHCHECK CMD curl -f http://localhost:3000/health
        Multi-stage build implemented.
        Non-root user configured.
        .dockerignore created.'''
    )
    metric.measure(test_case)
    print(f"Score: {metric.score}, Passed: {metric.is_successful()}")
"""

import re
from typing import List, Optional

from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase


class InfrastructureComplianceMetric(BaseMetric):
    """
    DeepEval metric for Ops Agent infrastructure best practices compliance.

    Evaluates:
    1. Docker best practices (specific tags, multi-stage, non-root)
    2. Kubernetes best practices (resource limits, probes, security)
    3. CI/CD pipeline (testing, security scan, approval)
    4. Secrets management (no git secrets, secret manager)
    5. Security scanning (dependency scan, image scan)

    Scoring:
    - 1.0: Perfect compliance (all 5 components present)
    - 0.85-0.99: Excellent (4-5 components well-covered)
    - 0.7-0.84: Good (3-4 components present)
    - 0.0-0.69: Poor (< 3 components)
    """

    # Docker best practices patterns
    DOCKER_PATTERNS: List[str] = [
        r'FROM\s+[\w/-]+:[\d\.]+-[\w]+',  # Specific tag (not latest)
        r'FROM\s+node:20\.[\d]+-alpine',   # Example specific tag
        r'FROM.*AS\s+\w+',                # Multi-stage build
        r'USER\s+(?!root)\w+',            # Non-root user
        r'HEALTHCHECK',                   # Health check
        r'\.dockerignore',                # .dockerignore file
        r'multi-stage\s+build',           # Multi-stage build mention
        r'non-root\s+user',               # Non-root user mention
        r'specific.*tag',                 # Specific tag mention
        r'not.*latest'                    # Avoid latest tag
    ]

    # Kubernetes best practices patterns
    K8S_PATTERNS: List[str] = [
        r'resources:\s*\n\s*(?:limits|requests)',
        r'resource\s+limit',
        r'livenessProbe:',
        r'readinessProbe:',
        r'liveness.*probe',
        r'readiness.*probe',
        r'securityContext:.*runAsNonRoot',
        r'security\s+context',
        r'secretKeyRef:',
        r'rolling\s+update',
        r'Pod\s+Disruption\s+Budget'
    ]

    # CI/CD pipeline patterns
    CICD_PATTERNS: List[str] = [
        r'(?:npm test|pytest|cargo test)',
        r'automated\s+test',
        r'(?:CodeQL|Snyk|Trivy)',
        r'security\s+scan',
        r'(?:npm audit|safety check)',
        r'vulnerability\s+check',
        r'(?:environment|approval)',
        r'manual\s+approval',
        r'rollback.*on.*fail',
        r'automated\s+rollback',
        r'GitHub\s+Actions|Jenkins|GitLab\s+CI'
    ]

    # Secrets management patterns
    SECRETS_PATTERNS: List[str] = [
        r'(?:aws-secretsmanager|vault|secrets-manager)',
        r'secret\s+manager',
        r'git\s+secrets\s+--scan',
        r'no.*secrets?.*(?:in|commit)',
        r'rotation\s+(?:policy|interval)',
        r'secret\s+rotation',
        r'(?:environment|env).*(?:variable|var)',
        r'not.*commit.*secret',
        r'encrypted',
        r'AWS\s+Secrets\s+Manager|HashiCorp\s+Vault'
    ]

    # Security scanning patterns
    SECURITY_SCAN_PATTERNS: List[str] = [
        r'(?:npm audit|safety|snyk test)',
        r'dependency\s+scan',
        r'(?:trivy|grype|clair)',
        r'image\s+scan',
        r'(?:critical|high).*vulnerabilit',
        r'vulnerability\s+report',
        r'(?:fix|upgrade|update).*(?:to|version)',
        r'remediation',
        r'CVE-\d{4}-\d{4,}',
        r'security\s+(?:findings|issues)'
    ]

    def __init__(self, threshold: float = 0.85):
        """
        Initialize InfrastructureComplianceMetric.

        Args:
            threshold: Minimum score to pass (default: 0.85 for 85% compliance)
        """
        self.threshold = threshold
        self._score: Optional[float] = None
        self._reason: Optional[str] = None
        self._success: Optional[bool] = None

    @property
    def __name__(self) -> str:
        return "Infrastructure Compliance"

    @property
    def score(self) -> Optional[float]:
        """Get the computed score."""
        return self._score

    @property
    def reason(self) -> Optional[str]:
        """Get the reason for the score."""
        return self._reason

    def is_successful(self) -> bool:
        """Check if metric passes threshold."""
        if self._success is None:
            return False
        return self._success

    def measure(self, test_case: LLMTestCase) -> float:
        """
        Measure infrastructure compliance score.

        Args:
            test_case: DeepEval test case with input and actual_output

        Returns:
            Score from 0.0 to 1.0
        """
        output = test_case.actual_output

        # Calculate component scores
        docker_score = self._score_docker_practices(output)
        k8s_score = self._score_kubernetes_practices(output)
        cicd_score = self._score_cicd_pipeline(output)
        secrets_score = self._score_secrets_management(output)
        security_scan_score = self._score_security_scanning(output)

        # Weighted average (equal weights)
        final_score = (
            docker_score * 0.20 +
            k8s_score * 0.20 +
            cicd_score * 0.20 +
            secrets_score * 0.20 +
            security_scan_score * 0.20
        )

        # Store results
        self._score = final_score
        self._reason = self._generate_reason(
            docker_score,
            k8s_score,
            cicd_score,
            secrets_score,
            security_scan_score,
            output
        )
        epsilon = 1e-9
        self._success = final_score >= (self.threshold - epsilon)

        return final_score

    async def a_measure(self, test_case: LLMTestCase) -> float:
        """Async version of measure (delegates to sync)."""
        return self.measure(test_case)

    # ========================================================================
    # COMPONENT SCORING METHODS
    # ========================================================================

    def _score_docker_practices(self, output: str) -> float:
        """
        Score Docker best practices (20% weight).

        Checks:
        - Specific base image tags (not latest)
        - Multi-stage builds
        - Non-root user
        - Health checks
        - .dockerignore usage

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        docker_matches = [
            pattern for pattern in self.DOCKER_PATTERNS
            if re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
        ]

        if not docker_matches:
            return 0.0

        # Check for comprehensive Docker best practices
        match_count = len(docker_matches)

        if match_count >= 4:
            # Perfect: comprehensive Docker best practices
            return 1.0
        if match_count == 3:
            # Good: solid Docker practices
            return 0.85
        if match_count == 2:
            # Acceptable: basic Docker practices
            return 0.7
        # Minimal: single practice
        return 0.5

    def _score_kubernetes_practices(self, output: str) -> float:
        """
        Score Kubernetes best practices (20% weight).

        Checks:
        - Resource limits (CPU/memory)
        - Liveness and readiness probes
        - Security context (non-root, read-only FS)
        - Rolling update strategy
        - Secrets usage

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        k8s_matches = [
            pattern for pattern in self.K8S_PATTERNS
            if re.search(pattern, output, re.IGNORECASE | re.MULTILINE)
        ]

        if not k8s_matches:
            return 0.0

        # Check for comprehensive K8s best practices
        match_count = len(k8s_matches)

        if match_count >= 4:
            # Perfect: comprehensive K8s best practices
            return 1.0
        if match_count == 3:
            # Good: solid K8s practices
            return 0.85
        if match_count == 2:
            # Acceptable: basic K8s practices
            return 0.7
        # Minimal: single practice
        return 0.5

    def _score_cicd_pipeline(self, output: str) -> float:
        """
        Score CI/CD pipeline configuration (20% weight).

        Checks:
        - Automated testing stage
        - Security scanning (SAST)
        - Dependency vulnerability checks
        - Manual approval gates
        - Automated rollback

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        cicd_matches = [
            pattern for pattern in self.CICD_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        ]

        if not cicd_matches:
            return 0.0

        # Check for comprehensive CI/CD configuration
        match_count = len(cicd_matches)

        if match_count >= 4:
            # Perfect: comprehensive CI/CD pipeline
            return 1.0
        if match_count == 3:
            # Good: solid CI/CD pipeline
            return 0.85
        if match_count == 2:
            # Acceptable: basic CI/CD pipeline
            return 0.7
        # Minimal: single CI/CD element
        return 0.5

    def _score_secrets_management(self, output: str) -> float:
        """
        Score secrets management (20% weight).

        Checks:
        - No secrets in version control
        - Secret manager usage
        - Secret rotation policies
        - Secret scanning

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        secrets_matches = [
            pattern for pattern in self.SECRETS_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        ]

        if not secrets_matches:
            return 0.0

        # Check for comprehensive secrets management
        match_count = len(secrets_matches)

        if match_count >= 3:
            # Perfect: comprehensive secrets management
            return 1.0
        if match_count == 2:
            # Good: solid secrets management
            return 0.8
        # Minimal: secrets management mentioned
        return 0.6

    def _score_security_scanning(self, output: str) -> float:
        """
        Score security scanning (20% weight).

        Checks:
        - Dependency vulnerability scanning
        - Container image scanning
        - Critical vulnerability reporting
        - Remediation recommendations

        Args:
            output: Agent output text

        Returns:
            Score from 0.0 to 1.0
        """
        security_matches = [
            pattern for pattern in self.SECURITY_SCAN_PATTERNS
            if re.search(pattern, output, re.IGNORECASE)
        ]

        if not security_matches:
            return 0.0

        # Check for comprehensive security scanning
        match_count = len(security_matches)

        if match_count >= 3:
            # Perfect: comprehensive security scanning
            return 1.0
        if match_count == 2:
            # Good: solid security scanning
            return 0.8
        # Minimal: security scanning mentioned
        return 0.6

    # ========================================================================
    # HELPER METHODS
    # ========================================================================

    def _generate_reason(
        self,
        docker_score: float,
        k8s_score: float,
        cicd_score: float,
        secrets_score: float,
        security_scan_score: float,
        output: str
    ) -> str:
        """
        Generate human-readable reason for the score.

        Args:
            docker_score: Docker practices score
            k8s_score: Kubernetes practices score
            cicd_score: CI/CD pipeline score
            secrets_score: Secrets management score
            security_scan_score: Security scanning score
            output: Agent output text

        Returns:
            Reason string explaining the score
        """
        reasons = []

        # Docker issues
        if docker_score < 0.5:
            reasons.append(
                "No Docker best practices (should use specific tags, multi-stage builds, non-root user)"
            )

        # Kubernetes issues
        if k8s_score < 0.5:
            reasons.append(
                "No Kubernetes best practices (should configure resource limits, probes, security context)"
            )

        # CI/CD issues
        if cicd_score < 0.5:
            reasons.append(
                "No CI/CD pipeline configuration (should include testing, security scanning, approval gates)"
            )

        # Secrets issues
        if secrets_score < 0.5:
            reasons.append(
                "No secrets management (should use secret manager, no git secrets, rotation policies)"
            )

        # Security scanning issues
        if security_scan_score < 0.5:
            reasons.append(
                "No security scanning (should scan dependencies, images, report vulnerabilities)"
            )

        # Success message
        if not reasons:
            return "Perfect infrastructure compliance - all best practices followed"

        return "; ".join(reasons)


def create_infrastructure_compliance_metric(threshold: float = 0.85) -> InfrastructureComplianceMetric:
    """
    Factory function to create infrastructure compliance metric.

    Args:
        threshold: Minimum passing score (default: 0.85 for 85% compliance)

    Returns:
        Configured metric instance

    Example:
        metric = create_infrastructure_compliance_metric(threshold=0.85)
        test_case = LLMTestCase(
            input="Create production-ready Dockerfile",
            actual_output="FROM node:20.10-alpine AS builder... USER node... HEALTHCHECK..."
        )
        score = metric.measure(test_case)
    """
    return InfrastructureComplianceMetric(threshold=threshold)
