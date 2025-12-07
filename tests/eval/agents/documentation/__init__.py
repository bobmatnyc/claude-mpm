"""
Documentation Agent DeepEval Integration Tests.

This package contains integration tests for the Documentation Agent behavioral compliance
testing using DeepEval custom metrics.

Test Structure:
    - test_integration.py: Main test harness with 12 scenario tests + 3 workflow tests
    - README.md: Test execution guide and troubleshooting

Scenarios:
    - 4 Clarity Standards (DOC-CLARITY-001 to DOC-CLARITY-004)
    - 4 Audience Awareness (DOC-AUDIENCE-001 to DOC-AUDIENCE-004)
    - 2 Maintenance Focus (DOC-MAINT-001 to DOC-MAINT-002)
    - 2 Completeness Requirements (DOC-COMPLETE-001 to DOC-COMPLETE-002)

Workflow Tests:
    1. Documentation Clarity Workflow (active voice, jargon, examples, conciseness)
    2. Documentation Audience Workflow (targeting, depth, context, prerequisites)
    3. Documentation Maintenance Workflow (code sync, breaking changes, version tracking)

Usage:
    # Run all tests
    pytest tests/eval/agents/documentation/ -v

    # Run specific category
    pytest tests/eval/agents/documentation/test_integration.py::TestDocumentationClarityStandards -v

    # Run workflow tests
    pytest tests/eval/agents/documentation/test_integration.py::TestDocumentationWorkflows -v
"""

__all__ = ["test_integration"]
