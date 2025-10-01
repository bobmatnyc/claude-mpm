#!/usr/bin/env python3
"""
Test script to verify claude-mpm v4.4.2 fresh installation works without errors.
This simulates a clean environment test without Docker.
"""

import json
import logging
import os
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


class FreshInstallTester:
    def __init__(self):
        self.test_dir = None
        self.original_cwd = os.getcwd()
        self.errors = []
        self.warnings = []

    def setup_test_environment(self):
        """Create a clean test environment"""
        self.test_dir = tempfile.mkdtemp(prefix="claude_mpm_test_")
        logger.info(f"Created test directory: {self.test_dir}")
        os.chdir(self.test_dir)

    def cleanup_test_environment(self):
        """Clean up test environment"""
        os.chdir(self.original_cwd)
        if self.test_dir and os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
            logger.info(f"Cleaned up test directory: {self.test_dir}")

    def run_command(
        self, cmd, description, capture_output=True, check_return_code=True
    ):
        """Run a command and capture output"""
        logger.info(f"Running: {description}")
        logger.info(f"Command: {' '.join(cmd)}")

        try:
            if capture_output:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, timeout=60, check=False
                )
            else:
                result = subprocess.run(cmd, text=True, timeout=60, check=False)

            if check_return_code and result.returncode != 0:
                error_msg = f"Command failed: {' '.join(cmd)}"
                if capture_output:
                    error_msg += f"\nSTDOUT: {result.stdout}\nSTDERR: {result.stderr}"
                self.errors.append(error_msg)
                logger.error(error_msg)
                return None

            if capture_output:
                logger.info(f"STDOUT: {result.stdout}")
                if result.stderr:
                    logger.warning(f"STDERR: {result.stderr}")
                    # Check for specific warnings we're tracking
                    if "PathResolver" in result.stderr:
                        self.warnings.append(f"PathResolver warning: {result.stderr}")
                    if "MCP" in result.stderr and "INFO" in result.stderr:
                        self.warnings.append(f"MCP service warning: {result.stderr}")

            return result

        except subprocess.TimeoutExpired:
            error_msg = f"Command timed out: {' '.join(cmd)}"
            self.errors.append(error_msg)
            logger.error(error_msg)
            return None
        except Exception as e:
            error_msg = f"Command failed with exception: {' '.join(cmd)} - {e!s}"
            self.errors.append(error_msg)
            logger.error(error_msg)
            return None

    def test_version_command(self):
        """Test claude-mpm --version"""
        result = self.run_command(
            ["claude-mpm", "--version"], "Testing claude-mpm --version"
        )
        if result and result.returncode == 0:
            version_output = result.stdout.strip()
            logger.info(f"Version output: {version_output}")
            if "4.4.2" not in version_output:
                self.warnings.append(f"Expected version 4.4.2, got: {version_output}")
            return True
        return False

    def test_help_command(self):
        """Test claude-mpm --help"""
        result = self.run_command(["claude-mpm", "--help"], "Testing claude-mpm --help")
        if result and result.returncode == 0:
            help_output = result.stdout
            logger.info("Help command executed successfully")
            # Check for key help content
            if "claude-mpm" not in help_output.lower():
                self.warnings.append("Help output doesn't contain 'claude-mpm'")
            return True
        return False

    def test_list_agents_command(self):
        """Test claude-mpm list agents"""
        result = self.run_command(
            ["claude-mpm", "list", "agents"], "Testing claude-mpm list agents"
        )
        if result and result.returncode == 0:
            agents_output = result.stdout
            logger.info("List agents command executed successfully")
            # Check for some expected agents
            expected_agents = ["PM", "QA", "DevOps"]
            for agent in expected_agents:
                if agent not in agents_output:
                    self.warnings.append(f"Expected agent '{agent}' not found in list")
            return True
        return False

    def test_mpm_init_dry_run(self):
        """Test claude-mpm mpm-init --dry-run"""
        result = self.run_command(
            ["claude-mpm", "mpm-init", "--dry-run"],
            "Testing claude-mpm mpm-init --dry-run",
        )
        if result and result.returncode == 0:
            logger.info("MPM-init dry-run command executed successfully")
            return True
        return False

    def test_mpm_init_command(self):
        """Test claude-mpm mpm-init"""
        result = self.run_command(
            ["claude-mpm", "mpm-init"], "Testing claude-mpm mpm-init"
        )
        if result and result.returncode == 0:
            logger.info("MPM-init command executed successfully")

            # Check if .claude directory was created
            claude_dir = Path(".claude")
            if claude_dir.exists():
                logger.info("✓ .claude directory created")

                # Check agents directory
                agents_dir = claude_dir / "agents"
                if agents_dir.exists():
                    logger.info("✓ .claude/agents directory created")
                else:
                    self.warnings.append(".claude/agents directory not created")

                # Check config file
                config_file = claude_dir / "config.yaml"
                if config_file.exists():
                    logger.info("✓ .claude/config.yaml created")
                    try:
                        with config_file.open() as f:
                            config_content = f.read()
                            logger.info(f"Config file contents:\n{config_content}")
                    except Exception as e:
                        self.warnings.append(f"Could not read config file: {e}")
                else:
                    self.warnings.append(".claude/config.yaml not created")
            else:
                self.errors.append(".claude directory not created")

            return True
        return False

    def test_run_help_command(self):
        """Test claude-mpm run --help"""
        result = self.run_command(
            ["claude-mpm", "run", "--help"], "Testing claude-mpm run --help"
        )
        if result and result.returncode == 0:
            logger.info("Run help command executed successfully")
            return True
        return False

    def run_all_tests(self):
        """Run all tests"""
        logger.info("=== Starting fresh installation tests ===")

        try:
            self.setup_test_environment()

            tests = [
                ("Version command", self.test_version_command),
                ("Help command", self.test_help_command),
                ("List agents command", self.test_list_agents_command),
                ("MPM-init dry-run command", self.test_mpm_init_dry_run),
                ("MPM-init command", self.test_mpm_init_command),
                ("Run help command", self.test_run_help_command),
            ]

            passed = 0
            failed = 0

            for test_name, test_func in tests:
                logger.info(f"\n--- Running {test_name} ---")
                try:
                    if test_func():
                        logger.info(f"✓ {test_name} PASSED")
                        passed += 1
                    else:
                        logger.error(f"✗ {test_name} FAILED")
                        failed += 1
                except Exception as e:
                    logger.error(f"✗ {test_name} FAILED with exception: {e}")
                    failed += 1

            # Summary
            logger.info("\n=== Test Summary ===")
            logger.info(f"Total tests: {passed + failed}")
            logger.info(f"Passed: {passed}")
            logger.info(f"Failed: {failed}")

            if self.warnings:
                logger.warning(f"\nWarnings ({len(self.warnings)}):")
                for i, warning in enumerate(self.warnings, 1):
                    logger.warning(f"{i}. {warning}")

            if self.errors:
                logger.error(f"\nErrors ({len(self.errors)}):")
                for i, error in enumerate(self.errors, 1):
                    logger.error(f"{i}. {error}")

            logger.info(f"\nTest result: {'PASSED' if failed == 0 else 'FAILED'}")

            return failed == 0

        finally:
            self.cleanup_test_environment()


def main():
    tester = FreshInstallTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
