"""
BASE_AGENT Test Harness.

This module contains DeepEval test cases for BASE_AGENT compliance validation.

Test Modules:
- test_verification_patterns: Verification protocol compliance (VER-001 to VER-008)
- test_memory_protocol: Memory management compliance (MEM-001 to MEM-006)
- test_template_merging: Template inheritance behavior (TPL-001 to TPL-003)
- test_tool_orchestration: Tool orchestration patterns (ORC-001 to ORC-003)

Total Scenarios: 20
Total Tests: 40 (2 per scenario: compliant + non-compliant)
"""

__all__ = [
    "test_verification_patterns",
    "test_memory_protocol",
    "test_template_merging",
    "test_tool_orchestration",
]
