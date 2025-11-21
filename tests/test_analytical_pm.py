#!/usr/bin/env python3
"""
Test script to validate PM's analytical behavior and removal of affirmative language.

This script verifies that the PM instructions properly implement:
1. Removal of affirmative language patterns
2. Analytical Rigor Protocol implementation
3. Structural merit assessment capabilities
4. Communication precision standards
5. JSON response format requirements
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


class AnalyticalPMValidator:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.instructions_path = (
            self.project_root / "src/claude_mpm/agents/INSTRUCTIONS.md"
        )
        self.base_pm_path = self.project_root / "src/claude_mpm/agents/BASE_PM.md"

        # Forbidden affirmative patterns
        self.forbidden_patterns = [
            r"Excellent!",
            r"Perfect!",
            r"Amazing!",
            r"Great job!",
            r"You're absolutely right",
            r"Exactly as requested",
            r"I appreciate",
            r"Thank you for",
            r"Well done",
            r"Fantastic",
            r"Wonderful",
            r"Outstanding",
            r"Superb",
            r"Brilliant",
        ]

        # Required analytical patterns
        self.required_patterns = [
            r"Analysis indicates",
            r"Structural assessment",
            r"Critical gaps identified",
            r"Assumptions requiring validation",
            r"Weak points in approach",
            r"Missing justification",
            r"Root cause analysis",
            r"Falsifiable criteria",
            r"Structural requirements",
            r"Measurable outcomes",
        ]

        # Required sections in instructions
        self.required_sections = [
            "Analytical Rigor Protocol",
            "Structural Merit Assessment",
            "Cognitive Clarity Enforcement",
            "Weak Link Detection",
            "Communication Precision",
            "Error Handling Protocol",
            "FORBIDDEN Communication Patterns",
            "REQUIRED Communication Patterns",
        ]

        self.validation_results = {
            "forbidden_language_check": {"status": "PENDING", "issues": []},
            "required_patterns_check": {"status": "PENDING", "issues": []},
            "section_presence_check": {"status": "PENDING", "issues": []},
            "json_format_check": {"status": "PENDING", "issues": []},
            "analytical_examples_check": {"status": "PENDING", "issues": []},
            "overall_score": 0,
        }

    def load_files(self) -> Tuple[str, str]:
        """Load instruction files."""
        try:
            with open(self.instructions_path, encoding="utf-8") as f:
                instructions_content = f.read()
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"Instructions file not found: {self.instructions_path}"
            ) from e

        try:
            with open(self.base_pm_path, encoding="utf-8") as f:
                base_pm_content = f.read()
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"Base PM file not found: {self.base_pm_path}"
            ) from e

        return instructions_content, base_pm_content

    def test_forbidden_language_removal(self, content: str) -> Dict[str, Any]:
        """Test that forbidden affirmative language is removed."""
        issues = []

        # Split content into lines for context analysis
        lines = content.split("\n")

        # Check for forbidden patterns, but ignore them in forbidden/negative contexts
        for pattern in self.forbidden_patterns:
            # Find all occurrences with context
            for i, line in enumerate(lines):
                if re.search(pattern, line, re.IGNORECASE):
                    # Check if this is in a forbidden/negative context
                    context_lines = lines[
                        max(0, i - 2) : i + 3
                    ]  # Get surrounding lines
                    context = " ".join(context_lines).lower()

                    # Skip if in forbidden examples or negative contexts
                    forbidden_contexts = [
                        "forbidden communication patterns",
                        "❌",
                        "never",
                        "don't",
                        'not "',
                        "not '",
                        "unacceptable responses",
                        "violation",
                        "examples of what not to",
                        "avoid",
                        "prohibited",
                    ]

                    # Check if this is actually a forbidden usage
                    is_forbidden_context = any(
                        ctx in context for ctx in forbidden_contexts
                    )

                    if not is_forbidden_context:
                        issues.append(
                            f"Found forbidden pattern '{pattern}' in non-context usage: line {i + 1}"
                        )

        # Check specific problem phrases in examples (also with context)
        problem_phrases = [
            "great work",
            "nice job",
            "well implemented",
            "properly done",
        ]

        for phrase in problem_phrases:
            for i, line in enumerate(lines):
                if phrase.lower() in line.lower():
                    # Check context
                    context_lines = lines[max(0, i - 2) : i + 3]
                    context = " ".join(context_lines).lower()

                    forbidden_contexts = [
                        'not "',
                        "not '",
                        "❌",
                        "don't",
                        "never",
                        "avoid",
                        "unacceptable",
                    ]

                    is_forbidden_context = any(
                        ctx in context for ctx in forbidden_contexts
                    )

                    if not is_forbidden_context:
                        issues.append(
                            f"Found problematic phrase '{phrase}' in non-context usage: line {i + 1}"
                        )

        return {
            "status": "PASS" if not issues else "FAIL",
            "issues": issues,
            "forbidden_patterns_found": len(
                [i for i in issues if "forbidden pattern" in i]
            ),
            "total_checks": len(self.forbidden_patterns) + len(problem_phrases),
        }

    def test_required_analytical_patterns(self, content: str) -> Dict[str, Any]:
        """Test that required analytical language patterns are present."""
        issues = []
        found_patterns = []

        for pattern in self.required_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                found_patterns.append(pattern)
            else:
                issues.append(f"Missing required analytical pattern: '{pattern}'")

        coverage = len(found_patterns) / len(self.required_patterns) * 100

        return {
            "status": "PASS" if coverage >= 80 else "FAIL",
            "issues": issues,
            "patterns_found": len(found_patterns),
            "total_patterns": len(self.required_patterns),
            "coverage_percentage": coverage,
        }

    def test_section_presence(self, content: str) -> Dict[str, Any]:
        """Test that required sections are present in instructions."""
        issues = []
        found_sections = []

        for section in self.required_sections:
            if section in content:
                found_sections.append(section)
            else:
                issues.append(f"Missing required section: '{section}'")

        return {
            "status": (
                "PASS" if len(found_sections) == len(self.required_sections) else "FAIL"
            ),
            "issues": issues,
            "sections_found": len(found_sections),
            "total_sections": len(self.required_sections),
        }

    def test_json_format_requirements(self, content: str) -> Dict[str, Any]:
        """Test that JSON response format includes structural analysis."""
        issues = []
        required_json_fields = [
            "structural_analysis",
            "requirements_identified",
            "assumptions_made",
            "gaps_discovered",
            "verification_results",
            "measurable_outcomes",
            "structural_issues",
            "unresolved_requirements",
        ]

        for field in required_json_fields:
            if field not in content:
                issues.append(f"Missing required JSON field in format: '{field}'")

        # Check for proper JSON structure example
        json_blocks = re.findall(r"```json\s*(.*?)\s*```", content, re.DOTALL)
        valid_json_found = False

        for block in json_blocks:
            try:
                parsed = json.loads(block)
                if "structural_analysis" in parsed:
                    valid_json_found = True
                    break
            except json.JSONDecodeError:
                continue

        if not valid_json_found:
            issues.append("No valid JSON example with structural_analysis found")

        return {
            "status": "PASS" if not issues else "FAIL",
            "issues": issues,
            "json_blocks_found": len(json_blocks),
            "valid_structural_json": valid_json_found,
        }

    def test_analytical_examples(self, content: str) -> Dict[str, Any]:
        """Test that examples follow analytical approach."""
        issues = []

        # Find example sections
        example_patterns = [
            r"### ✅ How I Handle.*?```.*?```",
            r"Example.*?delegation.*?```.*?```",
            r"✅.*?```.*?```",
        ]

        examples_found = 0
        analytical_examples = 0

        for pattern in example_patterns:
            matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
            examples_found += len(matches)

            for match in matches:
                # Check if example uses analytical language
                analytical_indicators = [
                    "structural criteria",
                    "falsifiable criteria",
                    "root cause",
                    "verification requirements",
                    "measurable outcomes",
                    "structural requirements",
                ]

                if any(
                    indicator in match.lower() for indicator in analytical_indicators
                ):
                    analytical_examples += 1

        if examples_found == 0:
            issues.append("No examples found in instructions")
        elif analytical_examples / examples_found < 0.7:
            issues.append(
                f"Only {analytical_examples}/{examples_found} examples use analytical approach"
            )

        return {
            "status": "PASS" if not issues else "FAIL",
            "issues": issues,
            "examples_found": examples_found,
            "analytical_examples": analytical_examples,
            "analytical_percentage": (
                (analytical_examples / examples_found * 100)
                if examples_found > 0
                else 0
            ),
        }

    def run_comprehensive_test(self) -> Dict[str, Any]:
        """Run all validation tests."""
        try:
            instructions_content, base_pm_content = self.load_files()
            combined_content = instructions_content + "\n\n" + base_pm_content

            # Run all tests
            self.validation_results["forbidden_language_check"] = (
                self.test_forbidden_language_removal(combined_content)
            )
            self.validation_results["required_patterns_check"] = (
                self.test_required_analytical_patterns(combined_content)
            )
            self.validation_results["section_presence_check"] = (
                self.test_section_presence(combined_content)
            )
            self.validation_results["json_format_check"] = (
                self.test_json_format_requirements(combined_content)
            )
            self.validation_results["analytical_examples_check"] = (
                self.test_analytical_examples(combined_content)
            )

            # Calculate overall score
            passed_tests = sum(
                1
                for test in self.validation_results.values()
                if isinstance(test, dict) and test.get("status") == "PASS"
            )
            total_tests = len(
                [k for k in self.validation_results if k != "overall_score"]
            )
            self.validation_results["overall_score"] = (
                passed_tests / total_tests
            ) * 100

            return self.validation_results

        except Exception as e:
            return {"error": str(e), "status": "ERROR"}

    def generate_report(self) -> str:
        """Generate detailed validation report."""
        results = self.validation_results

        report = [
            "=" * 80,
            "ANALYTICAL PM VALIDATION REPORT",
            "=" * 80,
            "",
            f"Overall Score: {results['overall_score']:.1f}%",
            "",
        ]

        for test_name, test_results in results.items():
            if test_name == "overall_score":
                continue

            report.append(f"## {test_name.replace('_', ' ').title()}")
            report.append(f"Status: {test_results['status']}")

            if test_results.get("issues"):
                report.append("Issues Found:")
                for issue in test_results["issues"]:
                    report.append(f"  - {issue}")
            else:
                report.append("✅ No issues found")

            # Add specific metrics
            for key, value in test_results.items():
                if key not in ["status", "issues"] and not key.endswith("_found"):
                    if isinstance(value, (int, float)):
                        report.append(f"  {key}: {value}")

            report.append("")

        # Add recommendations
        report.append("## RECOMMENDATIONS")
        if results["overall_score"] < 90:
            report.append(
                "❌ CRITICAL: PM instructions need improvement before deployment"
            )

            failed_tests = [
                name
                for name, test in results.items()
                if isinstance(test, dict) and test.get("status") == "FAIL"
            ]

            for test in failed_tests:
                report.append(f"  - Fix issues in: {test}")
        else:
            report.append("✅ PM analytical behavior validation passed")

        report.append("")
        report.append("=" * 80)

        return "\n".join(report)


def main():
    """Main execution function."""
    validator = AnalyticalPMValidator()

    print("Running Analytical PM Validation Tests...")
    print("=" * 50)

    results = validator.run_comprehensive_test()

    if "error" in results:
        print(f"ERROR: {results['error']}")
        sys.exit(1)

    # Generate and display report
    report = validator.generate_report()
    print(report)

    # Save detailed results to file
    output_file = Path(__file__).parent.parent / "test_results_analytical_pm.json"
    with output_file.open("w") as f:
        json.dump(results, f, indent=2)

    print(f"\nDetailed results saved to: {output_file}")

    # Exit with appropriate code
    if results["overall_score"] >= 90:
        print("\n✅ VALIDATION PASSED: PM ready for analytical behavior")
        sys.exit(0)
    else:
        print(f"\n❌ VALIDATION FAILED: Score {results['overall_score']:.1f}% < 90%")
        sys.exit(1)


if __name__ == "__main__":
    main()
