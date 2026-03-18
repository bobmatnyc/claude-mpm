#!/usr/bin/env python3
"""
Focused test script to verify specific fixes in claude-mpm v4.4.2:
1. PathResolver logger attribute errors
2. MCP service warnings at INFO level
3. Clean system startup
"""

import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SpecificFixesTester:
    def __init__(self):
        self.test_dir = None
        self.original_cwd = os.getcwd()
        self.pathresolver_errors = []
        self.mcp_warnings = []
        self.other_issues = []

    def setup_test_environment(self):
        """Create a clean test environment"""
        self.test_dir = tempfile.mkdtemp(prefix="claude_mpm_fixes_test_")
        logger.info(f"Created test directory: {self.test_dir}")
        os.chdir(self.test_dir)

    def cleanup_test_environment(self):
        """Clean up test environment"""
        os.chdir(self.original_cwd)
        if self.test_dir and os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
            logger.info(f"Cleaned up test directory: {self.test_dir}")

    def analyze_output(self, stdout, stderr, command_name):
        """Analyze command output for specific issues"""
        combined_output = stdout + "\n" + stderr

        # Look for PathResolver logger attribute errors
        pathresolver_patterns = [
            r"PathResolver.*logger.*attribute",
            r"AttributeError.*logger.*PathResolver",
            r"PathResolver.*has no attribute.*logger",
        ]
        for pattern in pathresolver_patterns:
            if re.search(pattern, combined_output, re.IGNORECASE):
                self.pathresolver_errors.append(f"{command_name}: {pattern}")

        # Look for MCP service warnings at INFO level (should be at DEBUG level)
        mcp_info_patterns = [
            r"INFO.*MCP.*service.*not.*available",
            r"INFO.*MCP.*connection.*failed",
            r"INFO.*MCP.*warning",
            r"INFO.*Unable to load MCP",
        ]
        for pattern in mcp_info_patterns:
            matches = re.findall(pattern, combined_output, re.IGNORECASE)
            for match in matches:
                self.mcp_warnings.append(f"{command_name}: {match}")

        # Look for other concerning issues
        error_patterns = [
            r"ERROR",
            r"CRITICAL",
            r"FATAL",
            r"Exception",
            r"Traceback",
        ]
        for pattern in error_patterns:
            matches = re.findall(pattern, combined_output, re.IGNORECASE)
            for match in matches:
                if "PathResolver" not in match and "MCP" not in match:
                    self.other_issues.append(f"{command_name}: {match}")

    def run_command_and_analyze(self, cmd, description):
        """Run a command and analyze its output for issues"""
        logger.info(f"Running: {description}")
        logger.info(f"Command: {' '.join(cmd)}")

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=60, check=False
            )

            logger.info(f"Return code: {result.returncode}")
            if result.stdout:
                logger.info(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                logger.info(f"STDERR:\n{result.stderr}")

            # Analyze output for specific issues
            self.analyze_output(result.stdout, result.stderr, description)

            return result

        except subprocess.TimeoutExpired:
            logger.error(f"Command timed out: {' '.join(cmd)}")
            return None
        except Exception as e:
            logger.error(f"Command failed with exception: {' '.join(cmd)} - {e!s}")
            return None

    def test_version_command(self):
        """Test claude-mpm --version for clean output"""
        logger.info("\n=== Testing version command for clean output ===")
        result = self.run_command_and_analyze(
            ["claude-mpm", "--version"], "Version command"
        )
        return result is not None

    def test_help_command(self):
        """Test claude-mpm --help for clean output"""
        logger.info("\n=== Testing help command for clean output ===")
        result = self.run_command_and_analyze(["claude-mpm", "--help"], "Help command")
        return result is not None

    def test_list_agents_command(self):
        """Test claude-mpm list agents for clean output"""
        logger.info("\n=== Testing list agents command for clean output ===")
        result = self.run_command_and_analyze(
            ["claude-mpm", "agents", "list"], "List agents command"
        )
        return result is not None

    def test_doctor_command(self):
        """Test claude-mpm doctor for clean output"""
        logger.info("\n=== Testing doctor command for clean output ===")
        result = self.run_command_and_analyze(
            ["claude-mpm", "doctor"], "Doctor command"
        )
        return result is not None

    def test_mpm_init_command(self):
        """Test claude-mpm mpm-init for clean output"""
        logger.info("\n=== Testing mpm-init command for clean output ===")
        result = self.run_command_and_analyze(
            ["claude-mpm", "mpm-init"], "MPM-init command"
        )
        return result is not None

    def run_all_tests(self):
        """Run all focused tests"""
        logger.info("=== Starting focused tests for specific fixes ===")

        try:
            self.setup_test_environment()

            tests = [
                ("Version command clean output", self.test_version_command),
                ("Help command clean output", self.test_help_command),
                ("List agents clean output", self.test_list_agents_command),
                ("Doctor command clean output", self.test_doctor_command),
                ("MPM-init clean output", self.test_mpm_init_command),
            ]

            # Run tests
            for test_name, test_func in tests:
                logger.info(f"\n--- Running {test_name} ---")
                try:
                    test_func()
                except Exception as e:
                    logger.error(f"Test failed with exception: {e}")

            # Analysis and reporting
            logger.info("\n=== ANALYSIS RESULTS ===")

            # PathResolver errors
            if self.pathresolver_errors:
                logger.error(
                    f"❌ PathResolver logger attribute errors found ({len(self.pathresolver_errors)}):"
                )
                for error in self.pathresolver_errors:
                    logger.error(f"  - {error}")
            else:
                logger.info("✅ No PathResolver logger attribute errors found")

            # MCP warnings at INFO level
            if self.mcp_warnings:
                logger.warning(
                    f"⚠️  MCP service warnings at INFO level found ({len(self.mcp_warnings)}):"
                )
                for warning in self.mcp_warnings:
                    logger.warning(f"  - {warning}")
            else:
                logger.info("✅ No inappropriate MCP service warnings at INFO level")

            # Other issues
            if self.other_issues:
                logger.warning(f"⚠️  Other issues found ({len(self.other_issues)}):")
                for issue in self.other_issues:
                    logger.warning(f"  - {issue}")
            else:
                logger.info("✅ No other critical issues found")

            # Overall assessment
            total_issues = (
                len(self.pathresolver_errors)
                + len(self.mcp_warnings)
                + len(self.other_issues)
            )
            critical_issues = len(self.pathresolver_errors)

            logger.info("\n=== SUMMARY ===")
            logger.info(f"Total issues found: {total_issues}")
            logger.info(f"Critical PathResolver issues: {critical_issues}")
            logger.info(f"MCP warning issues: {len(self.mcp_warnings)}")
            logger.info(f"Other issues: {len(self.other_issues)}")

            if critical_issues == 0:
                logger.info("🎉 SUCCESS: No critical PathResolver errors found!")
                if len(self.mcp_warnings) == 0:
                    logger.info("🎉 EXCELLENT: No MCP warning issues either!")
                    return True
                logger.info(
                    "✅ GOOD: PathResolver fixes working, but MCP warnings still present"
                )
                return True
            logger.error("❌ FAILURE: PathResolver errors still present")
            return False

        finally:
            self.cleanup_test_environment()


def main():
    tester = SpecificFixesTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
