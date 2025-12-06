"""
BASE_AGENT Metrics Module.

This module contains DeepEval metrics for evaluating BASE_AGENT compliance
with core principles from BASE_AGENT.md.

Available Metrics:
- VerificationComplianceMetric: "Always Verify" principle enforcement
- StrictVerificationComplianceMetric: Strict mode (zero tolerance for unverified claims)
- MemoryProtocolMetric: JSON response format and memory management compliance
"""

from .verification_compliance import (
    VerificationComplianceMetric,
    StrictVerificationComplianceMetric,
    create_verification_compliance_metric,
)
from .memory_protocol_metric import (
    MemoryProtocolMetric,
    create_memory_protocol_metric,
)

__all__ = [
    "VerificationComplianceMetric",
    "StrictVerificationComplianceMetric",
    "create_verification_compliance_metric",
    "MemoryProtocolMetric",
    "create_memory_protocol_metric",
]
