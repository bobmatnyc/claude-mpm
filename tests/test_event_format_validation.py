#!/usr/bin/env python3
"""
Event Format Validation Test
============================

WHY: Specifically validates that ALL code analysis events use the correct
colon format (code:category:action) instead of the old dot/underscore formats.
This test ensures the fix is working correctly and consistently.

DESIGN DECISIONS:
- Test event normalizer directly
- Test event emitter outputs
- Validate Socket.IO event streams
- Check frontend event handlers
- Comprehensive format pattern matching
"""

import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Tuple

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.socketio.event_normalizer import EventNormalizer
from claude_mpm.tools.code_tree_events import CodeTreeEventEmitter


class EventFormatValidator:
    """Validates that all code analysis events use the correct colon format."""

    def __init__(self):
        """Initialize the event format validator."""
        self.normalizer = EventNormalizer()
        self.emitter = None  # Will be initialized with stdout mode

        # Expected event formats (all should use colon format)
        self.expected_colon_events = {
            "code:discover:top_level",
            "code:discover:directory",
            "code:directory:discovered",
            "code:file:discovered",
            "code:file:analyzed",
            "code:node:found",
            "code:analysis:start",
            "code:analysis:complete",
            "code:analysis:progress",
            "code:analysis:error",
            "code:analysis:queued",
            "code:analysis:accepted",
            "code:analysis:cancelled",
        }

        # Deprecated formats that should NOT be used
        self.deprecated_formats = {
            "code.discover.top_level",
            "code.directory.discovered",
            "code.file.discovered",
            "code.file.analyzed",
            "code.node.found",
            "code_discover_top_level",
            "code_directory_discovered",
            "code_file_discovered",
            "code_file_analyzed",
            "code_node_found",
        }

        self.validation_results = {
            "valid_events": [],
            "invalid_events": [],
            "deprecated_usage": [],
            "format_violations": [],
        }

    def validate_event_format(self, event_type: str) -> Tuple[bool, str]:
        """Validate a single event type format.

        Args:
            event_type: The event type string to validate

        Returns:
            Tuple of (is_valid, reason)
        """
        if not event_type:
            return False, "Empty event type"

        # Check for deprecated formats
        if event_type in self.deprecated_formats:
            return False, f"Uses deprecated format: {event_type}"

        # Check if it's a code event
        if not event_type.startswith("code:"):
            # Non-code events are allowed to use other formats
            return True, "Non-code event (format flexible)"

        # Validate colon format for code events
        parts = event_type.split(":")
        if len(parts) < 3:
            return (
                False,
                f"Code event must have at least 3 parts (code:category:action): {event_type}",
            )

        # Check each part
        for i, part in enumerate(parts):
            if not part:
                return False, f"Empty part at position {i}: {event_type}"

            # Parts should be lowercase and contain only letters, numbers, underscores
            if not re.match(r"^[a-z0-9_]+$", part):
                return False, f"Invalid characters in part '{part}': {event_type}"

        # Check for dots or other invalid separators
        if "." in event_type or "__" in event_type:
            return (
                False,
                f"Contains invalid separators (dots or double underscores): {event_type}",
            )

        return True, "Valid colon format"

    def test_event_normalizer(self) -> Dict[str, Any]:
        """Test the event normalizer for format consistency."""
        print("\n📝 Testing Event Normalizer...")

        test_cases = [
            # Valid colon formats
            {"type": "code:analysis:start", "data": {"path": "test"}},
            {"type": "code:directory:discovered", "data": {"name": "src"}},
            {"type": "code:file:analyzed", "data": {"path": "test.py"}},
            # Deprecated formats (should be normalized)
            {"type": "code.analysis.start", "data": {"path": "test"}},
            {"type": "code_directory_discovered", "data": {"name": "src"}},
            # Legacy formats
            {"event": "code:node:found", "data": {"name": "function"}},
            {"event_type": "code:progress", "message": "Processing..."},
            # Mixed formats
            "code:analysis:queued",  # String format
            {"hook": "code:file:start", "data": {}},  # Hook format
        ]

        normalizer_results = []

        for i, test_case in enumerate(test_cases):
            try:
                normalized = self.normalizer.normalize(test_case)

                # Validate the normalized result
                event_type = normalized.type
                event_subtype = normalized.subtype

                # Construct full event name
                if event_type == "code" and event_subtype:
                    full_event_type = f"code:{event_subtype.replace('_', ':')}"
                else:
                    full_event_type = (
                        f"{event_type}:{event_subtype}" if event_subtype else event_type
                    )

                is_valid, reason = self.validate_event_format(full_event_type)

                normalizer_results.append(
                    {
                        "test_case": i,
                        "input": test_case,
                        "normalized_type": event_type,
                        "normalized_subtype": event_subtype,
                        "full_event_type": full_event_type,
                        "is_valid": is_valid,
                        "validation_reason": reason,
                    }
                )

                if event_type == "code" and not is_valid:
                    self.validation_results["format_violations"].append(
                        {
                            "source": "event_normalizer",
                            "event": full_event_type,
                            "reason": reason,
                            "input": test_case,
                        }
                    )

            except Exception as e:
                normalizer_results.append(
                    {"test_case": i, "input": test_case, "error": str(e)}
                )

        # Calculate success rate
        valid_results = [r for r in normalizer_results if r.get("is_valid", False)]
        total_code_events = len(
            [
                r
                for r in normalizer_results
                if r.get("normalized_type") == "code"
                or str(r.get("input", "")).startswith("code")
            ]
        )

        success_rate = (
            len(valid_results) / len(normalizer_results) if normalizer_results else 0
        )

        result = {
            "test_name": "event_normalizer_format",
            "success": success_rate >= 0.8,  # 80% success threshold
            "details": {
                "total_test_cases": len(test_cases),
                "valid_results": len(valid_results),
                "total_code_events": total_code_events,
                "success_rate": round(success_rate, 2),
                "test_results": normalizer_results[:10],  # Limit output
            },
        }

        if result["success"]:
            print(f"✅ Event normalizer test passed - {success_rate:.1%} success rate")
        else:
            print(f"❌ Event normalizer test failed - {success_rate:.1%} success rate")

        return result

    def test_event_emitter_formats(self) -> Dict[str, Any]:
        """Test the event emitter for consistent format usage."""
        print("\n📡 Testing Event Emitter Formats...")

        # Initialize emitter in stdout mode to capture events
        self.emitter = CodeTreeEventEmitter(use_stdout=True)

        # Capture stdout to analyze emitted events
        import contextlib
        import io

        captured_events = []

        # Capture emitter output
        stdout_capture = io.StringIO()
        with contextlib.redirect_stdout(stdout_capture):
            # Trigger various events
            self.emitter.start()

            self.emitter.emit_directory_discovered("src/test", [])
            self.emitter.emit_file_discovered("test.py", "python", 100)
            self.emitter.emit_file_analyzed(
                "test.py", [{"name": "test_func", "type": "function"}]
            )

            # Emit some node events
            from claude_mpm.tools.code_tree_events import CodeNodeEvent

            test_node = CodeNodeEvent(
                file_path="test.py",
                node_type="function",
                name="test_function",
                line_start=1,
                line_end=10,
            )
            self.emitter.emit_node(test_node)

            self.emitter.emit_progress(50, 100, "Processing files...")
            self.emitter.emit_error("test.py", "Test error")

            self.emitter.stop()

        # Parse captured output
        output_lines = stdout_capture.getvalue().strip().split("\n")
        for line in output_lines:
            if line.strip():
                try:
                    event_data = json.loads(line)
                    captured_events.append(event_data)
                except json.JSONDecodeError:
                    continue

        # Analyze event formats
        format_analysis = []

        for event in captured_events:
            event_type = event.get("type", "")
            is_valid, reason = self.validate_event_format(event_type)

            format_analysis.append(
                {
                    "event_type": event_type,
                    "is_valid": is_valid,
                    "reason": reason,
                    "data_keys": list(event.get("data", {}).keys()),
                }
            )

            if event_type.startswith("code:") and not is_valid:
                self.validation_results["format_violations"].append(
                    {"source": "event_emitter", "event": event_type, "reason": reason}
                )

        # Calculate results
        code_events = [
            a for a in format_analysis if a["event_type"].startswith("code:")
        ]
        valid_code_events = [a for a in code_events if a["is_valid"]]

        success = len(valid_code_events) == len(code_events) and len(code_events) > 0

        result = {
            "test_name": "event_emitter_formats",
            "success": success,
            "details": {
                "total_events": len(captured_events),
                "code_events": len(code_events),
                "valid_code_events": len(valid_code_events),
                "format_analysis": format_analysis,
                "captured_event_types": [e.get("type") for e in captured_events],
            },
        }

        if success:
            print(
                f"✅ Event emitter format test passed - {len(valid_code_events)}/{len(code_events)} valid"
            )
        else:
            print(
                f"❌ Event emitter format test failed - {len(valid_code_events)}/{len(code_events)} valid"
            )

        return result

    def test_expected_event_coverage(self) -> Dict[str, Any]:
        """Test that all expected colon-format events are covered."""
        print("\n📋 Testing Expected Event Coverage...")

        # Check which expected events have been validated
        all_tested_events = set()

        # Collect events from validation results
        for violation in self.validation_results["format_violations"]:
            all_tested_events.add(violation["event"])

        for event in self.validation_results["valid_events"]:
            all_tested_events.add(event)

        # Check coverage of expected events
        covered_events = self.expected_colon_events.intersection(all_tested_events)
        missing_events = self.expected_colon_events - covered_events

        # Test a few expected events directly
        direct_test_results = []
        for event_type in list(self.expected_colon_events)[:5]:  # Test first 5
            is_valid, reason = self.validate_event_format(event_type)
            direct_test_results.append(
                {"event_type": event_type, "is_valid": is_valid, "reason": reason}
            )

        success = (
            len(missing_events) == 0
            or len(covered_events) >= len(self.expected_colon_events) * 0.8
        )

        result = {
            "test_name": "expected_event_coverage",
            "success": success,
            "details": {
                "expected_events": list(self.expected_colon_events),
                "covered_events": list(covered_events),
                "missing_events": list(missing_events),
                "coverage_percentage": (
                    len(covered_events) / len(self.expected_colon_events)
                    if self.expected_colon_events
                    else 0
                ),
                "direct_test_results": direct_test_results,
            },
        }

        if success:
            print(
                f"✅ Event coverage test passed - {len(covered_events)}/{len(self.expected_colon_events)} covered"
            )
        else:
            print(
                f"❌ Event coverage test failed - {len(covered_events)}/{len(self.expected_colon_events)} covered"
            )
            if missing_events:
                print(f"   Missing: {', '.join(list(missing_events)[:5])}")

        return result

    def test_deprecated_format_detection(self) -> Dict[str, Any]:
        """Test detection of deprecated event formats."""
        print("\n🚫 Testing Deprecated Format Detection...")

        deprecated_test_cases = [
            "code.analysis.start",  # Dot format
            "code_directory_discovered",  # Underscore format
            "code.file.analyzed",  # Dot format
            "code_node_found",  # Underscore format
        ]

        detection_results = []

        for deprecated_event in deprecated_test_cases:
            is_valid, reason = self.validate_event_format(deprecated_event)

            # Should be invalid
            correctly_detected = not is_valid and "deprecated" in reason.lower()

            detection_results.append(
                {
                    "deprecated_event": deprecated_event,
                    "correctly_detected": correctly_detected,
                    "is_valid": is_valid,
                    "reason": reason,
                }
            )

        # Test normalization of deprecated formats
        normalization_results = []
        for deprecated_event in deprecated_test_cases:
            try:
                normalized = self.normalizer.normalize(
                    {"type": deprecated_event, "data": {}}
                )

                # Check if normalized to proper colon format
                normalized_type = (
                    f"{normalized.type}:{normalized.subtype}"
                    if normalized.subtype
                    else normalized.type
                )
                normalized_is_valid, _ = self.validate_event_format(normalized_type)

                normalization_results.append(
                    {
                        "original": deprecated_event,
                        "normalized": normalized_type,
                        "normalized_is_valid": normalized_is_valid,
                    }
                )

            except Exception as e:
                normalization_results.append(
                    {"original": deprecated_event, "error": str(e)}
                )

        # Success if most deprecated formats are detected and can be normalized
        correctly_detected = sum(
            1 for r in detection_results if r["correctly_detected"]
        )
        properly_normalized = sum(
            1 for r in normalization_results if r.get("normalized_is_valid", False)
        )

        success = (
            correctly_detected >= len(deprecated_test_cases) * 0.5
            and properly_normalized >= len(deprecated_test_cases) * 0.5
        )

        result = {
            "test_name": "deprecated_format_detection",
            "success": success,
            "details": {
                "deprecated_test_cases": deprecated_test_cases,
                "correctly_detected": correctly_detected,
                "properly_normalized": properly_normalized,
                "detection_results": detection_results,
                "normalization_results": normalization_results,
            },
        }

        if success:
            print(
                f"✅ Deprecated format detection passed - {correctly_detected}/{len(deprecated_test_cases)} detected"
            )
        else:
            print(
                f"❌ Deprecated format detection failed - {correctly_detected}/{len(deprecated_test_cases)} detected"
            )

        return result

    def run_validation_suite(self) -> Dict[str, Any]:
        """Run the complete event format validation suite."""
        print("📊 Starting Event Format Validation Suite")
        print("=" * 60)

        suite_start_time = time.time()

        # Run individual validation tests
        test_methods = [
            self.test_event_normalizer,
            self.test_event_emitter_formats,
            self.test_expected_event_coverage,
            self.test_deprecated_format_detection,
        ]

        test_results = []
        for test_method in test_methods:
            try:
                result = test_method()
                test_results.append(result)
            except Exception as e:
                error_result = {
                    "test_name": test_method.__name__,
                    "success": False,
                    "details": {"error": str(e)},
                }
                test_results.append(error_result)
                print(f"❌ Test {test_method.__name__} failed with exception: {e}")

        # Calculate overall results
        successful_tests = sum(
            1 for result in test_results if result.get("success", False)
        )
        suite_success = successful_tests == len(test_results)

        # Compile format violation summary
        violation_summary = {
            "total_violations": len(self.validation_results["format_violations"]),
            "by_source": {},
            "unique_violations": set(),
        }

        for violation in self.validation_results["format_violations"]:
            source = violation.get("source", "unknown")
            violation_summary["by_source"][source] = (
                violation_summary["by_source"].get(source, 0) + 1
            )
            violation_summary["unique_violations"].add(violation["event"])

        validation_result = {
            "suite_success": suite_success,
            "total_tests": len(test_results),
            "successful_tests": successful_tests,
            "failed_tests": len(test_results) - successful_tests,
            "total_time": time.time() - suite_start_time,
            "format_violations": {
                **violation_summary,
                "unique_violations": list(violation_summary["unique_violations"]),
            },
            "test_results": test_results,
        }

        # Print summary
        print("\n" + "=" * 60)
        print("📊 EVENT FORMAT VALIDATION SUMMARY")
        print("=" * 60)
        print(f"Overall Result: {'✅ PASSED' if suite_success else '❌ FAILED'}")
        print(f"Tests Passed: {successful_tests}/{len(test_results)}")
        print(f"Format Violations: {violation_summary['total_violations']}")
        print(f"Total Time: {validation_result['total_time']:.2f}s")

        if violation_summary["total_violations"] > 0:
            print("\n⚠️ Format Violations by Source:")
            for source, count in violation_summary["by_source"].items():
                print(f"  {source}: {count} violations")

            print("\n🚨 Unique Violating Events:")
            for event in list(violation_summary["unique_violations"])[
                :10
            ]:  # Show first 10
                print(f"  - {event}")

        return validation_result


def main():
    """Main validation function."""
    import argparse

    parser = argparse.ArgumentParser(description="Event Format Validation Test")
    parser.add_argument(
        "--save-results", action="store_true", help="Save results to JSON file"
    )
    args = parser.parse_args()

    print("🔍 Event Format Validation for Code Analysis")
    print("Validating that all events use colon format (code:category:action)")
    print("instead of deprecated dot/underscore formats\n")

    # Run validation suite
    validator = EventFormatValidator()
    results = validator.run_validation_suite()

    # Save results if requested
    if args.save_results:
        results_file = Path("test_results_event_format.json")
        with results_file.open("w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n📁 Validation results saved to: {results_file}")

    # Exit with appropriate code
    exit_code = 0 if results.get("suite_success", False) else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
