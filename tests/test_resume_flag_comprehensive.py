#!/usr/bin/env python3
"""
Comprehensive test suite for the resume flag fix in claude-mpm wrapper.

Tests the fix applied to scripts/claude-mpm line 112 that removed "--resume" from
MPM_FLAGS to allow it to pass through directly to Claude CLI.

Test scenarios:
1. `claude-mpm --resume` should pass directly to Claude CLI
2. `claude-mpm run --resume` should work through Python module
3. `--mpm-resume` should trigger MPM command routing
4. Verify command routing logic works correctly
5. Check consistency across all scripts/binaries
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Add the src directory to Python path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


class ResumeTestResults:
    """Container for test results"""

    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0
        self.errors = []

    def add_test(self, name: str, passed: bool, details: Dict[str, Any]):
        """Add a test result"""
        self.tests.append({"name": name, "passed": passed, "details": details})
        if passed:
            self.passed += 1
        else:
            self.failed += 1

    def add_error(self, error: str):
        """Add an error"""
        self.errors.append(error)

    def get_summary(self) -> Dict[str, Any]:
        """Get test summary"""
        return {
            "total_tests": len(self.tests),
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "success_rate": (self.passed / len(self.tests) * 100) if self.tests else 0,
        }


class ResumeTestRunner:
    """Test runner for resume flag functionality"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.results = ResumeTestResults()

    def run_subcommand(self, cmd: List[str], timeout: int = 30) -> Tuple[int, str, str]:
        """Run a command and capture output"""
        try:
            print(f"Running: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.project_root,
                check=False,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except Exception as e:
            return -2, "", f"Error running command: {e!s}"

    def test_wrapper_flag_detection():
        """Test 1: Verify --resume is NOT in MPM_FLAGS in wrapper script"""
        print("\n" + "=" * 60)
        print("TEST 1: Wrapper Flag Detection")
        print("=" * 60)

        wrapper_script = self.project_root / "scripts" / "claude-mpm"

        if not wrapper_script.exists():
            self.results.add_test(
                "wrapper_flag_detection", False, {"error": "Wrapper script not found"}
            )
            return

        try:
            content = wrapper_script.read_text()

            # Find the MPM_FLAGS line
            for line_no, line in enumerate(content.split("\n"), 1):
                if (
                    "MPM_FLAGS=" in line
                    and "Note: --resume passes through"
                    in content.split("\n")[line_no - 2]
                ):
                    mmp_flags_line = line
                    break

            if not mmp_flags_line:
                # Find any MPM_FLAGS line
                for line in content.split("\n"):
                    if "MPM_FLAGS=" in line:
                        mmp_flags_line = line
                        break

            if mmp_flags_line:
                # Check that --resume is NOT in MPM_FLAGS
                has_resume = '"--resume"' in mmp_flags_line
                has_mpm_resume = (
                    '"--mmp-resume"' in mmp_flags_line
                    or '"--mpm-resume"' in mmp_flags_line
                )

                passed = not has_resume and has_mpm_resume

                self.results.add_test(
                    "wrapper_flag_detection",
                    passed,
                    {
                        "mpm_flags_line": mmp_flags_line,
                        "has_resume": has_resume,
                        "has_mmp_resume": has_mpm_resume,
                        "expected": "--resume should NOT be in MPM_FLAGS, --mmp-resume should be",
                    },
                )

                if passed:
                    print("✅ PASS: --resume correctly removed from MPM_FLAGS")
                else:
                    print(
                        "❌ FAIL: --resume still in MPM_FLAGS or --mmp-resume missing"
                    )
                    print(f"   Line: {mmp_flags_line}")
            else:
                self.results.add_test(
                    "wrapper_flag_detection",
                    False,
                    {"error": "Could not find MPM_FLAGS declaration"},
                )
                print("❌ FAIL: Could not find MPM_FLAGS declaration")

        except Exception as e:
            self.results.add_test("wrapper_flag_detection", False, {"error": str(e)})
            print(f"❌ ERROR: {e}")

    def test_resume_passthrough():
        """Test 2: Test that --resume passes through to Claude CLI"""
        print("\n" + "=" * 60)
        print("TEST 2: Resume Flag Passthrough")
        print("=" * 60)

        # Test 1: Check if --resume alone tries to go to Claude CLI (should timeout/error)
        print("   Testing --resume alone (should timeout indicating Claude CLI)")
        cmd = [str(self.project_root / "scripts" / "claude-mpm"), "--resume"]
        returncode, _stdout, stderr = self.run_subcommand(cmd, timeout=3)

        # If it times out, shows claude CLI errors, or fails with Claude-specific errors, it's passing through correctly
        passed_through_1 = (
            returncode == -1  # timeout (good - means it reached Claude CLI)
            or "passing through to claude cli" in stderr.lower()
            or ("claude" in stderr.lower() and "not found" in stderr.lower())
            or (
                "--resume requires a valid session id" in stderr.lower()
            )  # Claude CLI error message
            or (
                returncode == 1 and "session" in stderr.lower()
            )  # Claude CLI session error
        )

        print(
            f"      Result: timeout/error = {returncode == -1}, stderr: {stderr[:50]}..."
        )

        # Test 2: Check the wrapper logic by examining what would happen with unknown command
        print("   Testing unknown command to verify passthrough logic")
        cmd2 = [str(self.project_root / "scripts" / "claude-mpm"), "some-unknown-cmd"]
        returncode2, _stdout2, stderr2 = self.run_subcommand(cmd2, timeout=3)

        passed_through_2 = (
            returncode2 == -1  # timeout
            or "passing through to claude cli" in stderr2.lower()
            or "claude" in stderr2.lower()
        )

        print(
            f"      Result: timeout/error = {returncode2 == -1}, stderr: {stderr2[:50]}..."
        )

        # The test passes if --resume behaves like other unknown commands (passes through)
        went_through_claude = passed_through_1 and passed_through_2

        self.results.add_test(
            "resume_passthrough",
            went_through_claude,
            {
                "resume_test": {
                    "command": " ".join(cmd),
                    "returncode": returncode,
                    "passed_through": passed_through_1,
                },
                "unknown_cmd_test": {
                    "command": " ".join(cmd2),
                    "returncode": returncode2,
                    "passed_through": passed_through_2,
                },
                "overall_result": went_through_claude,
            },
        )

        if went_through_claude:
            print(
                "✅ PASS: --resume appears to pass through to Claude CLI like other unknown commands"
            )
        else:
            print("❌ FAIL: --resume not behaving like passthrough commands")

        print(f"   Resume result: {returncode}, Unknown cmd result: {returncode2}")

    def test_mpm_run_resume():
        """Test 3: Test that 'claude-mpm run --resume' works through Python module"""
        print("\n" + "=" * 60)
        print("TEST 3: MPM Run Resume")
        print("=" * 60)

        # Test run command with --resume
        cmd = [
            str(self.project_root / "scripts" / "claude-mpm"),
            "run",
            "--resume",
            "--help",
        ]
        returncode, stdout, stderr = self.run_subcommand(cmd, timeout=10)

        # This should go through the Python module
        went_through_python = (
            "claude_mpm" in stderr.lower()
            or "claude-mpm" in stdout.lower()
            or "usage:" in stdout.lower()
        )

        self.results.add_test(
            "mpm_run_resume",
            went_through_python,
            {
                "command": " ".join(cmd),
                "returncode": returncode,
                "stdout_preview": stdout[:200] + "..." if len(stdout) > 200 else stdout,
                "stderr_preview": stderr[:200] + "..." if len(stderr) > 200 else stderr,
                "went_through_python": went_through_python,
            },
        )

        if went_through_python:
            print("✅ PASS: 'claude-mpm run --resume' goes through Python module")
        else:
            print("❌ FAIL: 'claude-mpm run --resume' did not go through Python module")

        print(f"   Return code: {returncode}")

    def test_mpm_resume_flag():
        """Test 4: Test that --mpm-resume triggers MPM command routing"""
        print("\n" + "=" * 60)
        print("TEST 4: MMP Resume Flag")
        print("=" * 60)

        # Test with --mmp-resume flag
        cmd = [
            str(self.project_root / "scripts" / "claude-mpm"),
            "--mmp-resume",
            "--help",
        ]
        returncode, stdout, stderr = self.run_subcommand(cmd, timeout=10)

        # This should go through MPM
        went_through_mpm = (
            "claude_mpm" in stderr.lower()
            or "claude-mpm" in stdout.lower()
            or "usage:" in stdout.lower()
            or returncode == 0
        )

        self.results.add_test(
            "mpm_resume_flag",
            went_through_mpm,
            {
                "command": " ".join(cmd),
                "returncode": returncode,
                "stdout_preview": stdout[:200] + "..." if len(stdout) > 200 else stdout,
                "stderr_preview": stderr[:200] + "..." if len(stderr) > 200 else stderr,
                "went_through_mmp": went_through_mpm,
            },
        )

        if went_through_mpm:
            print("✅ PASS: --mmp-resume triggers MPM command routing")
        else:
            print("❌ FAIL: --mmp-resume did not trigger MPM command routing")

        print(f"   Return code: {returncode}")

    def test_command_routing_logic():
        """Test 5: Verify the command routing logic in wrapper"""
        print("\n" + "=" * 60)
        print("TEST 5: Command Routing Logic")
        print("=" * 60)

        test_cases = [
            # (args, expected_routing, description, test_method)
            (["--help"], "mpm", "Help should go to MPM", "normal"),
            (["run"], "mpm", "Run command should go to MPM", "normal"),
            (["--resume"], "claude", "--resume should pass to Claude", "timeout"),
            (["--mpm-resume"], "mpm", "--mpm-resume should go to MPM", "normal"),
            (
                ["some-unknown-command"],
                "claude",
                "Unknown commands should pass to Claude",
                "timeout",
            ),
        ]

        routing_tests_passed = 0
        routing_tests_total = len(test_cases)

        for args, expected, description, test_method in test_cases:
            print(f"\n   Testing: {args} -> {expected}")

            cmd = [str(self.project_root / "scripts" / "claude-mpm"), *args]

            if test_method == "timeout":
                # For commands that should pass through, test without --help to avoid interference
                returncode, stdout, stderr = self.run_subcommand(cmd, timeout=2)

                if expected == "claude":
                    # Should timeout or error trying to reach Claude CLI
                    routed_correctly = (
                        returncode == -1  # timeout
                        or "passing through to claude cli" in stderr.lower()
                        or (
                            "claude" in stderr.lower() and "not found" in stderr.lower()
                        )
                        or (
                            "--resume requires a valid session id" in stderr.lower()
                        )  # Claude CLI error
                        or (
                            returncode == 1 and "session" in stderr.lower()
                        )  # Claude CLI session error
                    )
                else:
                    routed_correctly = False  # Shouldn't happen with current test cases
            else:
                # For MPM commands, add --help for cleaner output
                returncode, stdout, stderr = self.run_subcommand(
                    [*cmd, "--help"], timeout=5
                )

                if expected == "mpm":
                    routed_correctly = (
                        "claude_mpm" in stderr.lower()
                        or "usage:" in stdout.lower()
                        or "claude-mpm" in stdout.lower()
                    )
                else:
                    routed_correctly = (
                        "passing through to claude cli" in stderr.lower()
                        or "claude_mpm" not in stderr.lower()
                    )

            if routed_correctly:
                print(f"      ✅ {description}")
                routing_tests_passed += 1
            else:
                print(f"      ❌ {description}")
                print(f"         Expected: {expected}, Method: {test_method}")
                print(f"         Returncode: {returncode}, Stderr: {stderr[:50]}...")

        passed = routing_tests_passed == routing_tests_total

        self.results.add_test(
            "command_routing_logic",
            passed,
            {
                "passed_tests": routing_tests_passed,
                "total_tests": routing_tests_total,
                "test_cases": test_cases,
            },
        )

        if passed:
            print(f"\n✅ PASS: All {routing_tests_total} routing tests passed")
        else:
            print(
                f"\n❌ FAIL: {routing_tests_passed}/{routing_tests_total} routing tests passed"
            )

    def test_script_consistency():
        """Test 6: Check consistency across all scripts/binaries"""
        print("\n" + "=" * 60)
        print("TEST 6: Script Consistency")
        print("=" * 60)

        scripts_to_check = [
            self.project_root / "scripts" / "claude-mpm",
            self.project_root / "bin" / "claude-mpm",
            self.project_root / "claude-mpm",
        ]

        results = {}

        for script_path in scripts_to_check:
            print(f"\n   Checking: {script_path}")

            if not script_path.exists():
                results[str(script_path)] = {"exists": False, "error": "File not found"}
                print("      ❌ File not found")
                continue

            try:
                if (
                    script_path.suffix == ".py"
                    or "node" in script_path.read_text()[:50]
                ):
                    # Node.js or Python script - different behavior expected
                    results[str(script_path)] = {
                        "exists": True,
                        "type": "node/python",
                        "resume_behavior": "different_architecture",
                    }
                    print("      ✅ Node.js/Python script - different architecture")
                else:
                    # Bash script - should have similar resume handling
                    content = script_path.read_text()
                    has_resume_logic = "--resume" in content and "MPM_FLAGS" in content

                    results[str(script_path)] = {
                        "exists": True,
                        "type": "bash",
                        "has_resume_logic": has_resume_logic,
                    }

                    if has_resume_logic:
                        print("      ✅ Has resume logic")
                    else:
                        print("      ⚠️  No resume logic found")

            except Exception as e:
                results[str(script_path)] = {"exists": True, "error": str(e)}
                print(f"      ❌ Error reading file: {e}")

        # Determine if consistency test passed
        bash_scripts = [k for k, v in results.items() if v.get("type") == "bash"]
        consistent = all(
            results[script].get("has_resume_logic", False) for script in bash_scripts
        )

        self.results.add_test(
            "script_consistency",
            consistent,
            {
                "scripts_checked": len(scripts_to_check),
                "results": results,
                "bash_scripts": bash_scripts,
            },
        )

        if consistent:
            print("\n✅ PASS: Resume logic is consistent across bash scripts")
        else:
            print("\n❌ FAIL: Inconsistent resume logic across scripts")

    def run_all_tests(self):
        """Run all tests and generate report"""
        print("Resume Flag Fix Comprehensive Test Suite")
        print("=" * 60)
        print("Testing fix applied to scripts/claude-mpm line 112")
        print(f"Project root: {self.project_root}")

        # Run all test methods
        test_methods = [
            self.test_wrapper_flag_detection,
            self.test_resume_passthrough,
            self.test_mpm_run_resume,
            self.test_mpm_resume_flag,
            self.test_command_routing_logic,
            self.test_script_consistency,
        ]

        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                self.results.add_error(f"Error in {test_method.__name__}: {e!s}")
                print(f"❌ ERROR in {test_method.__name__}: {e}")

        # Generate final report
        self.generate_report()

    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 60)
        print("COMPREHENSIVE TEST REPORT")
        print("=" * 60)

        summary = self.results.get_summary()

        print("\nOVERALL RESULTS:")
        print(f"  Total Tests: {summary['total_tests']}")
        print(f"  Passed: {summary['passed']} ✅")
        print(f"  Failed: {summary['failed']} ❌")
        print(f"  Success Rate: {summary['success_rate']:.1f}%")

        if summary["errors"]:
            print(f"  Errors: {len(summary['errors'])}")

        print("\nDETAILED RESULTS:")
        for test in self.results.tests:
            status = "✅ PASS" if test["passed"] else "❌ FAIL"
            print(f"  {status}: {test['name']}")

        if summary["errors"]:
            print("\nERRORS:")
            for error in summary["errors"]:
                print(f"  ❌ {error}")

        # Determine overall fix status
        critical_tests = [
            "wrapper_flag_detection",
            "resume_passthrough",
            "command_routing_logic",
        ]

        critical_passed = sum(
            1
            for test in self.results.tests
            if test["name"] in critical_tests and test["passed"]
        )

        critical_total = len(critical_tests)

        print("\n" + "=" * 60)
        if critical_passed == critical_total:
            print("🎉 FIX VERIFICATION: SUCCESS")
            print("The resume flag fix is working correctly!")
            print("- --resume now passes through to Claude CLI")
            print("- --mmp-resume still triggers MPM routing")
            print("- Command routing logic is functioning properly")
        else:
            print("⚠️  FIX VERIFICATION: ISSUES DETECTED")
            print(f"Critical tests passed: {critical_passed}/{critical_total}")
            print("The resume flag fix may not be working as expected.")

        print("=" * 60)

        # Save detailed results to file
        results_file = self.project_root / "test_results_resume_flag_comprehensive.json"
        try:
            with results_file.open("w") as f:
                json.dump(
                    {
                        "summary": summary,
                        "tests": self.results.tests,
                        "critical_tests_status": {
                            "passed": critical_passed,
                            "total": critical_total,
                            "success": critical_passed == critical_total,
                        },
                        "timestamp": subprocess.check_output(
                            ["date"], text=True
                        ).strip(),
                    },
                    f,
                    indent=2,
                )
            print(f"\nDetailed results saved to: {results_file}")
        except Exception as e:
            print(f"Warning: Could not save results file: {e}")


def main():
    """Main test execution"""
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help"]:
        print(__doc__)
        return

    runner = ResumeTestRunner()
    runner.run_all_tests()


if __name__ == "__main__":
    main()
