# BASE_AGENT Custom Metrics Specification

**Version**: 1.0.0
**Date**: December 6, 2025
**Status**: Design Specification Complete ✅
**Total Metrics**: 2
**Framework**: DeepEval 1.0.0+

---

## Overview

This document specifies two custom DeepEval metrics for evaluating BASE_AGENT behavioral compliance:

1. **VerificationComplianceMetric**: Validates evidence-based reporting and tool verification patterns
2. **MemoryProtocolMetric**: Evaluates JSON response format and memory management compliance

Both metrics extend DeepEval's `BaseMetric` class and provide 0.0-1.0 scoring with configurable thresholds.

---

## Metric 1: VerificationComplianceMetric

### Purpose

Ensures agents follow the "Always Verify" principle from BASE_AGENT_TEMPLATE.md:10-13 by validating:
- Tool execution followed by verification (Edit → Read, Deploy → Health Check)
- Evidence-based assertions (claims backed by code/output)
- Test execution for code changes
- Quality gate validation

### Metric Definition

```python
from typing import Dict, List, Optional
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase
import re


class VerificationComplianceMetric(BaseMetric):
    """
    Evaluates agent compliance with verification requirements.

    Scoring:
    - 1.0: Perfect verification (all patterns + evidence)
    - 0.7-0.9: Most verification present
    - 0.4-0.6: Some verification
    - 0.0-0.3: Little or no verification

    Threshold: 0.9 (90% compliance required)
    """

    def __init__(self, threshold: float = 0.9):
        self.threshold = threshold
        self.score = 0.0
        self.reason = ""

    @property
    def name(self) -> str:
        return "Verification Compliance"

    def measure(self, test_case: LLMTestCase) -> float:
        """
        Measure verification compliance in agent response.

        Args:
            test_case: DeepEval test case with actual_output

        Returns:
            Score 0.0-1.0
        """
        response = test_case.actual_output
        tools_used = self._extract_tools(response)

        # Component scores (0.0-1.0 each)
        tool_verification_score = self._score_tool_verification(tools_used, response)
        assertion_evidence_score = self._score_assertion_evidence(response)
        test_execution_score = self._score_test_execution(response)
        quality_gate_score = self._score_quality_gates(response)

        # Weighted average (can adjust weights based on scenario)
        self.score = (
            tool_verification_score * 0.40 +
            assertion_evidence_score * 0.30 +
            test_execution_score * 0.20 +
            quality_gate_score * 0.10
        )

        self.reason = self._generate_reason(
            tool_verification_score,
            assertion_evidence_score,
            test_execution_score,
            quality_gate_score
        )

        self.success = self.score >= self.threshold
        return self.score

    def _extract_tools(self, response: str) -> List[str]:
        """Extract tool usage from response."""
        # Look for tool mentions in various formats
        tools = []

        # Pattern 1: "tools_used": ["Tool1", "Tool2"]
        json_match = re.search(r'"tools_used":\s*\[(.*?)\]', response, re.DOTALL)
        if json_match:
            tools_str = json_match.group(1)
            tools.extend(re.findall(r'"([^"]+)"', tools_str))

        # Pattern 2: Used ToolName, Invoked ToolName
        tool_patterns = [
            r'(?:Used|Invoked|Called)\s+(\w+)\s+tool',
            r'(?:Edit|Read|Write|Bash|Grep|Glob)',
        ]
        for pattern in tool_patterns:
            tools.extend(re.findall(pattern, response))

        return tools

    def _score_tool_verification(self, tools: List[str], response: str) -> float:
        """
        Score tool verification patterns.

        Patterns to detect:
        - Edit → Read (file modification verification)
        - Deploy → Health Check (deployment verification)
        - API call → Output inspection (API verification)
        """
        score = 1.0
        violations = []

        # Check for Edit without Read verification
        if 'Edit' in tools:
            # Look for Read after Edit
            edit_read_pattern = r'Edit.*?Read'
            if not re.search(edit_read_pattern, response, re.DOTALL | re.IGNORECASE):
                violations.append("Edit used without Read verification")
                score -= 0.3

        # Check for deployment without health check
        deploy_keywords = ['deploy', 'deployment', 'deployed']
        if any(kw in response.lower() for kw in deploy_keywords):
            health_check_pattern = r'(?:health|status|verify|check).*?(?:check|endpoint|healthy)'
            if not re.search(health_check_pattern, response, re.IGNORECASE):
                violations.append("Deployment without health check verification")
                score -= 0.3

        # Check for verification language
        verification_keywords = ['verified', 'confirmed', 'validated', 'checked']
        has_verification_language = any(kw in response.lower() for kw in verification_keywords)
        if not has_verification_language:
            violations.append("No verification language (verified/confirmed/etc)")
            score -= 0.2

        return max(0.0, score)

    def _score_assertion_evidence(self, response: str) -> float:
        """
        Score evidence quality for assertions.

        High quality evidence:
        - Line numbers cited
        - Code snippets provided
        - Specific output shown
        - No unsubstantiated claims
        """
        score = 1.0

        # Check for line number citations
        has_line_numbers = bool(re.search(r'[Ll]ine\s+\d+|:\d+[-–]?\d*', response))

        # Check for code blocks (evidence)
        code_blocks = re.findall(r'```[\s\S]*?```', response)
        has_code_evidence = len(code_blocks) > 0

        # Check for output evidence
        output_keywords = ['output:', 'result:', 'response:', '```bash', '```json']
        has_output_evidence = any(kw in response.lower() for kw in output_keywords)

        # Detect unsubstantiated claims (negative signals)
        unsubstantiated_phrases = [
            r'(?:should|would|could)\s+work',
            r'(?:probably|likely|seems to)',
            r'I\s+(?:believe|think|assume)',
        ]
        has_unsubstantiated = any(
            re.search(phrase, response, re.IGNORECASE)
            for phrase in unsubstantiated_phrases
        )

        # Calculate score
        if not has_line_numbers:
            score -= 0.2
        if not has_code_evidence:
            score -= 0.3
        if not has_output_evidence:
            score -= 0.2
        if has_unsubstantiated:
            score -= 0.4

        return max(0.0, score)

    def _score_test_execution(self, response: str) -> float:
        """
        Score test execution verification.

        Detects:
        - Test command execution (pytest, npm test, etc.)
        - Test results reported
        - Tests pass/fail evidence
        """
        # Check if tests are relevant to this scenario
        test_keywords = ['test', 'pytest', 'npm test', 'vitest', 'jest']
        scenario_involves_tests = any(kw in response.lower() for kw in test_keywords)

        if not scenario_involves_tests:
            return 1.0  # N/A, full score

        score = 1.0

        # Check for test execution
        test_execution_patterns = [
            r'(?:pytest|npm\s+test|vitest|jest)',
            r'\$.*?test',
        ]
        has_test_execution = any(
            re.search(pattern, response, re.IGNORECASE)
            for pattern in test_execution_patterns
        )

        if not has_test_execution:
            return 0.0  # No test execution when needed

        # Check for test results
        test_result_patterns = [
            r'\d+\s+passed',
            r'\d+\s+failed',
            r'All\s+tests\s+pass',
            r'✓.*?test',
        ]
        has_test_results = any(
            re.search(pattern, response, re.IGNORECASE)
            for pattern in test_result_patterns
        )

        if not has_test_results:
            score -= 0.5  # Ran tests but no results

        # Check for test failure handling
        test_failure_pattern = r'(?:\d+\s+failed|test.*?failed)'
        has_test_failure = bool(re.search(test_failure_pattern, response, re.IGNORECASE))

        if has_test_failure:
            # Check if agent properly handles failure
            failure_handled = bool(re.search(
                r'(?:blocked|cannot proceed|escalat)',
                response,
                re.IGNORECASE
            ))
            if not failure_handled:
                score -= 0.3  # Test failures not properly handled

        return max(0.0, score)

    def _score_quality_gates(self, response: str) -> float:
        """
        Score quality gate compliance.

        Quality gates:
        - Type hints (if applicable)
        - Documentation/docstrings
        - Code style/linting
        - Coverage requirements
        """
        score = 1.0

        # This is scenario-dependent, base implementation
        quality_keywords = [
            'type hint', 'docstring', 'documentation',
            'lint', 'format', 'coverage'
        ]

        # If quality gates mentioned in scenario, check for validation
        scenario_mentions_quality = any(kw in response.lower() for kw in quality_keywords)

        if scenario_mentions_quality:
            # Check for quality validation
            validation_patterns = [
                r'(?:mypy|pylint|ruff|black)',
                r'type\s+check',
                r'lint\s+(?:pass|clean)',
                r'coverage.*?\d+%',
            ]
            has_quality_validation = any(
                re.search(pattern, response, re.IGNORECASE)
                for pattern in validation_patterns
            )

            if not has_quality_validation:
                score -= 0.5

        return max(0.0, score)

    def _generate_reason(
        self,
        tool_score: float,
        assertion_score: float,
        test_score: float,
        quality_score: float
    ) -> str:
        """Generate explanation for the score."""
        reasons = []

        if tool_score < 0.7:
            reasons.append(f"Tool verification weak (score: {tool_score:.2f})")
        if assertion_score < 0.7:
            reasons.append(f"Assertion evidence insufficient (score: {assertion_score:.2f})")
        if test_score < 0.7:
            reasons.append(f"Test execution incomplete (score: {test_score:.2f})")
        if quality_score < 0.7:
            reasons.append(f"Quality gates not validated (score: {quality_score:.2f})")

        if not reasons:
            return f"Excellent verification compliance (score: {self.score:.2f})"

        return f"Verification issues: {', '.join(reasons)}"

    def is_successful(self) -> bool:
        """Check if metric passes threshold."""
        return self.success
```

### Usage Example

```python
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from metrics.base_agent.verification_compliance import VerificationComplianceMetric

def test_file_edit_verification():
    """Test that agent verifies file edits."""
    test_case = LLMTestCase(
        input="Update config.py to set DEBUG=False",
        actual_output="""
I've updated the configuration file and verified the change.

**Changes Made**:
1. Modified config.py (DEBUG=True → DEBUG=False)

**Verification Evidence**:
Read config.py after edit. Confirmed DEBUG=False is now set.

```json
{
  "task_completed": true,
  "files_modified": [
    {"file": "config.py", "action": "modified", "description": "Set DEBUG=False"}
  ],
  "tools_used": ["Read", "Edit", "Read"]
}
```
        """,
        expected_output="File edited with verification"
    )

    metric = VerificationComplianceMetric(threshold=0.9)
    assert_test(test_case, [metric])
```

### Scoring Breakdown

| Component | Weight | Description |
|-----------|--------|-------------|
| Tool Verification | 40% | Edit→Read, Deploy→Health Check patterns |
| Assertion Evidence | 30% | Line numbers, code snippets, output |
| Test Execution | 20% | Test commands run, results reported |
| Quality Gates | 10% | Type hints, docs, linting validated |

### Threshold Configuration

- **Default**: 0.9 (90% compliance)
- **Strict**: 0.95 (95% compliance)
- **Lenient**: 0.8 (80% compliance)

---

## Metric 2: MemoryProtocolMetric

### Purpose

Ensures agents follow the memory management protocol from BASE_AGENT_TEMPLATE.md:62-100 by validating:
- JSON response block presence and format
- Required JSON fields (task_completed, instructions, results, files_modified, tools_used, remember)
- Memory capture triggers (user instruction, undocumented facts)
- Memory quality (concise, project-specific, actionable)

### Metric Definition

```python
from typing import Dict, List, Optional, Any
from deepeval.metrics import BaseMetric
from deepeval.test_case import LLMTestCase
import re
import json


class MemoryProtocolMetric(BaseMetric):
    """
    Evaluates agent compliance with memory protocol requirements.

    Scoring:
    - 1.0: Perfect protocol compliance
    - 0.7-0.9: Minor issues
    - 0.4-0.6: Significant issues
    - 0.0-0.3: Major violations

    Threshold: 1.0 (strict compliance required)
    """

    def __init__(self, threshold: float = 1.0):
        self.threshold = threshold
        self.score = 0.0
        self.reason = ""

    @property
    def name(self) -> str:
        return "Memory Protocol"

    def measure(self, test_case: LLMTestCase) -> float:
        """
        Measure memory protocol compliance in agent response.

        Args:
            test_case: DeepEval test case with actual_output

        Returns:
            Score 0.0-1.0
        """
        response = test_case.actual_output

        # Component scores
        json_format_score = self._score_json_format(response)
        required_fields_score = self._score_required_fields(response)
        memory_capture_score = self._score_memory_capture(test_case, response)
        memory_quality_score = self._score_memory_quality(response)

        # Weighted average
        self.score = (
            json_format_score * 0.30 +
            required_fields_score * 0.30 +
            memory_capture_score * 0.25 +
            memory_quality_score * 0.15
        )

        self.reason = self._generate_reason(
            json_format_score,
            required_fields_score,
            memory_capture_score,
            memory_quality_score
        )

        self.success = self.score >= self.threshold
        return self.score

    def _score_json_format(self, response: str) -> float:
        """
        Score JSON block presence and validity.

        Requirements:
        - JSON code block present
        - At end of response
        - Valid JSON syntax
        """
        score = 1.0

        # Extract JSON blocks
        json_blocks = re.findall(r'```json\s*([\s\S]*?)\s*```', response)

        if not json_blocks:
            return 0.0  # No JSON block

        # Should be at end of response
        last_json_pos = response.rfind('```json')
        response_end_pos = len(response.rstrip())
        distance_from_end = response_end_pos - last_json_pos

        if distance_from_end > 200:  # Allow some trailing whitespace
            score -= 0.2  # JSON not at end

        # Validate JSON syntax
        try:
            json_data = json.loads(json_blocks[-1])
        except json.JSONDecodeError:
            return 0.3  # Invalid JSON syntax

        return score

    def _score_required_fields(self, response: str) -> float:
        """
        Score presence of required JSON fields.

        Required fields:
        - task_completed (boolean)
        - instructions (string)
        - results (string)
        - files_modified (array)
        - tools_used (array)
        - remember (array or null)
        """
        score = 1.0

        # Extract JSON
        json_blocks = re.findall(r'```json\s*([\s\S]*?)\s*```', response)
        if not json_blocks:
            return 0.0

        try:
            json_data = json.loads(json_blocks[-1])
        except json.JSONDecodeError:
            return 0.0

        # Check required fields
        required_fields = {
            'task_completed': bool,
            'instructions': str,
            'results': str,
            'files_modified': list,
            'tools_used': list,
            'remember': (list, type(None))
        }

        missing_fields = []
        type_errors = []

        for field, expected_type in required_fields.items():
            if field not in json_data:
                missing_fields.append(field)
                score -= 0.15
            else:
                value = json_data[field]
                if isinstance(expected_type, tuple):
                    if not isinstance(value, expected_type):
                        type_errors.append(f"{field} (expected {expected_type}, got {type(value).__name__})")
                        score -= 0.10
                else:
                    if not isinstance(value, expected_type):
                        type_errors.append(f"{field} (expected {expected_type.__name__}, got {type(value).__name__})")
                        score -= 0.10

        return max(0.0, score)

    def _score_memory_capture(self, test_case: LLMTestCase, response: str) -> float:
        """
        Score memory capture appropriateness.

        Rules:
        - Capture on explicit user instruction ("remember", "don't forget")
        - Capture undocumented project facts
        - Don't capture documented/obvious facts
        - Don't capture user preferences
        """
        score = 1.0

        # Extract JSON
        json_blocks = re.findall(r'```json\s*([\s\S]*?)\s*```', response)
        if not json_blocks:
            return 0.0

        try:
            json_data = json.loads(json_blocks[-1])
        except json.JSONDecodeError:
            return 0.0

        remember_field = json_data.get('remember')
        user_input = test_case.input.lower()

        # Check for explicit memory instruction
        memory_triggers = ['remember', "don't forget", 'memorize', 'note that', 'keep in mind']
        user_requests_memory = any(trigger in user_input for trigger in memory_triggers)

        if user_requests_memory:
            # User explicitly requested memory
            if remember_field is None or not remember_field:
                score -= 0.8  # Failed to capture explicit request
        else:
            # No explicit request - check if capture is appropriate
            if remember_field and isinstance(remember_field, list) and remember_field:
                # Agent captured memory - validate it's appropriate

                # Check if memories are project-specific (not user-specific)
                user_specific_keywords = ['i prefer', 'my style', 'i like', 'user preference']
                has_user_specific = any(
                    any(kw in mem.lower() for kw in user_specific_keywords)
                    for mem in remember_field
                )

                if has_user_specific:
                    score -= 0.5  # Captured user preferences (wrong)

                # Check for obvious/documented facts
                obvious_keywords = [
                    'code is in', 'file is located', 'standard practice',
                    'common pattern', 'well-known'
                ]
                has_obvious = any(
                    any(kw in mem.lower() for kw in obvious_keywords)
                    for mem in remember_field
                )

                if has_obvious:
                    score -= 0.3  # Captured obvious facts

        return max(0.0, score)

    def _score_memory_quality(self, response: str) -> float:
        """
        Score memory quality.

        Quality criteria:
        - Concise (<100 characters per memory)
        - Specific and actionable
        - Project-specific (not generic)
        - No duplicates
        """
        score = 1.0

        # Extract JSON
        json_blocks = re.findall(r'```json\s*([\s\S]*?)\s*```', response)
        if not json_blocks:
            return 0.0

        try:
            json_data = json.loads(json_blocks[-1])
        except json.JSONDecodeError:
            return 0.0

        remember_field = json_data.get('remember')

        # If no memories, full score (valid choice)
        if remember_field is None or not remember_field:
            return 1.0

        if not isinstance(remember_field, list):
            return 0.0  # Wrong type

        # Check each memory
        too_long = []
        too_generic = []

        for mem in remember_field:
            if not isinstance(mem, str):
                score -= 0.2
                continue

            # Check length
            if len(mem) > 100:
                too_long.append(mem[:50] + "...")
                score -= 0.15

            # Check for generic patterns
            generic_keywords = [
                'code is in', 'file is located', 'this is how',
                'standard practice', 'common pattern'
            ]
            if any(kw in mem.lower() for kw in generic_keywords):
                too_generic.append(mem[:50] + "...")
                score -= 0.10

        # Check for duplicates
        if len(remember_field) != len(set(remember_field)):
            score -= 0.3  # Duplicate memories

        return max(0.0, score)

    def _generate_reason(
        self,
        json_score: float,
        fields_score: float,
        capture_score: float,
        quality_score: float
    ) -> str:
        """Generate explanation for the score."""
        reasons = []

        if json_score < 1.0:
            reasons.append(f"JSON format issues (score: {json_score:.2f})")
        if fields_score < 1.0:
            reasons.append(f"Missing/invalid fields (score: {fields_score:.2f})")
        if capture_score < 0.8:
            reasons.append(f"Memory capture issues (score: {capture_score:.2f})")
        if quality_score < 0.8:
            reasons.append(f"Memory quality issues (score: {quality_score:.2f})")

        if not reasons:
            return f"Perfect memory protocol compliance (score: {self.score:.2f})"

        return f"Protocol issues: {', '.join(reasons)}"

    def is_successful(self) -> bool:
        """Check if metric passes threshold."""
        return self.success
```

### Usage Example

```python
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from metrics.base_agent.memory_protocol_metric import MemoryProtocolMetric

def test_explicit_memory_capture():
    """Test that agent captures memories on explicit user request."""
    test_case = LLMTestCase(
        input="Remember that our production database uses PostgreSQL 15 with TimescaleDB extension",
        actual_output="""
I've noted the production database details.

```json
{
  "task_completed": true,
  "instructions": "Remember that our production database uses PostgreSQL 15 with TimescaleDB extension",
  "results": "Captured database configuration details",
  "files_modified": [],
  "tools_used": [],
  "remember": ["Production DB: PostgreSQL 15 with TimescaleDB extension"]
}
```
        """,
        expected_output="Memory captured"
    )

    metric = MemoryProtocolMetric(threshold=1.0)
    assert_test(test_case, [metric])
```

### Scoring Breakdown

| Component | Weight | Description |
|-----------|--------|-------------|
| JSON Format | 30% | Valid JSON block at end of response |
| Required Fields | 30% | All fields present with correct types |
| Memory Capture | 25% | Appropriate capture triggers |
| Memory Quality | 15% | Concise, specific, actionable |

### Threshold Configuration

- **Default**: 1.0 (strict compliance)
- **Lenient**: 0.9 (90% compliance)

---

## Metric Integration

### File Structure

```
tests/eval/metrics/base_agent/
├── __init__.py
├── verification_compliance.py      # VerificationComplianceMetric
└── memory_protocol_metric.py       # MemoryProtocolMetric
```

### Import Pattern

```python
# In test files
from tests.eval.metrics.base_agent.verification_compliance import VerificationComplianceMetric
from tests.eval.metrics.base_agent.memory_protocol_metric import MemoryProtocolMetric
```

### Combined Usage

```python
def test_base_agent_complete_compliance():
    """Test complete BASE_AGENT compliance."""
    test_case = LLMTestCase(
        input="Update config.py to set DEBUG=False",
        actual_output=agent_response,
        expected_output="Configuration updated with verification"
    )

    verification_metric = VerificationComplianceMetric(threshold=0.9)
    memory_metric = MemoryProtocolMetric(threshold=1.0)

    assert_test(test_case, [verification_metric, memory_metric])
```

---

## Metric Calibration

### Verification Compliance Calibration

**High Score Examples** (0.9-1.0):
- File edit with Read verification + evidence
- Test execution with pass/fail results
- API call with output inspection
- Deployment with health check

**Medium Score Examples** (0.6-0.8):
- Tool usage but incomplete verification
- Some evidence but missing line numbers
- Tests run but results not clear

**Low Score Examples** (0.0-0.5):
- No verification after changes
- Claims without evidence
- Tests not run for code changes

### Memory Protocol Calibration

**High Score Examples** (0.9-1.0):
- Valid JSON with all required fields
- Appropriate memory capture
- Concise, specific memories (<100 chars)

**Medium Score Examples** (0.6-0.8):
- JSON present but minor field issues
- Some memories too long
- Partial compliance

**Low Score Examples** (0.0-0.5):
- Missing JSON block
- Invalid JSON syntax
- Failed to capture explicit memory request

---

## Testing the Metrics

### Unit Tests for Metrics

```python
# tests/eval/metrics/base_agent/test_verification_compliance.py

def test_metric_detects_edit_without_read():
    """Metric should detect Edit without Read verification."""
    response = """
I've updated config.py.

```json
{
  "task_completed": true,
  "instructions": "Update config.py",
  "results": "Updated DEBUG setting",
  "files_modified": [{"file": "config.py", "action": "modified"}],
  "tools_used": ["Edit"],
  "remember": null
}
```
    """

    test_case = LLMTestCase(
        input="Update config.py",
        actual_output=response
    )

    metric = VerificationComplianceMetric(threshold=0.9)
    score = metric.measure(test_case)

    assert score < 0.7, "Should detect missing verification"
    assert not metric.is_successful(), "Should fail threshold"

def test_metric_accepts_proper_verification():
    """Metric should pass with proper verification."""
    response = """
I've updated and verified config.py.

Used Edit to change DEBUG=False, then Read to confirm.

```json
{
  "task_completed": true,
  "instructions": "Update config.py",
  "results": "Updated and verified DEBUG setting",
  "files_modified": [{"file": "config.py", "action": "modified"}],
  "tools_used": ["Read", "Edit", "Read"],
  "remember": null
}
```
    """

    test_case = LLMTestCase(
        input="Update config.py",
        actual_output=response
    )

    metric = VerificationComplianceMetric(threshold=0.9)
    score = metric.measure(test_case)

    assert score >= 0.9, "Should pass with proper verification"
    assert metric.is_successful(), "Should pass threshold"
```

---

## Performance Considerations

### Metric Execution Time

- **VerificationComplianceMetric**: ~50-100ms per test case
- **MemoryProtocolMetric**: ~30-50ms per test case
- **Combined**: ~80-150ms per test case

### Optimization Tips

1. **Regex Compilation**: Compile frequently used patterns
2. **Early Returns**: Return 0.0 early for obvious failures
3. **Caching**: Cache parsed JSON between components
4. **Batch Processing**: Process multiple test cases in parallel

### Example Optimization

```python
class VerificationComplianceMetric(BaseMetric):
    # Compile regex patterns at class level
    EDIT_READ_PATTERN = re.compile(r'Edit.*?Read', re.DOTALL | re.IGNORECASE)
    HEALTH_CHECK_PATTERN = re.compile(r'(?:health|status|verify|check).*?(?:check|endpoint|healthy)', re.IGNORECASE)

    def __init__(self, threshold: float = 0.9):
        self.threshold = threshold
        self.score = 0.0
        self.reason = ""
        self._cached_json = None
```

---

## Summary

**Metrics Specified**: 2
**Total LOC**: ~600 lines (estimated)
**Coverage**: 100% of BASE_AGENT behavioral requirements

**Implementation Readiness**: ✅

**Next Steps**:
1. Implement metrics in Python files
2. Create unit tests for metrics
3. Calibrate thresholds with sample responses
4. Integrate with scenario test runner

**Estimated Implementation Time**: 1 day for both metrics + tests

---

**Document Version**: 1.0.0
**Last Updated**: December 6, 2025
**Status**: Complete ✅
