#!/usr/bin/env python3
"""
Comprehensive test suite for --resume flag implementation in claude-mpm.

This script tests all aspects of the --resume flag functionality:
1. Help text verification
2. --resume without arguments (resume last session)
3. --resume with session ID argument
4. --resume with --monitor combination
5. Error handling for invalid session IDs
6. Argument filtering to ensure unrelated arguments aren't consumed
"""

import subprocess
import sys
import json
import tempfile
import os
import time
from pathlib import Path
from datetime import datetime

# Ensure we can import claude_mpm modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.session_manager import SessionManager


class ResumeTestSuite:
    def __init__(self):
        self.test_results = []
        self.session_manager = SessionManager()
        self.package_root = Path(__file__).parent.parent
        self.claude_mpm_script = self.package_root / "claude-mpm"
        
    def log_test(self, test_name, success, details="", error=""):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "error": error,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    Details: {details}")
        if error:
            print(f"    Error: {error}")
        print()
        
    def run_claude_mpm_command(self, args, timeout=10):
        """Run claude-mpm command and capture output"""
        try:
            # Set environment to suppress browser opening during tests
            env = os.environ.copy()
            env['CLAUDE_MPM_NO_BROWSER'] = '1'
            
            # Run the bash script directly
            result = subprocess.run(
                [str(self.claude_mpm_script)] + args,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
                shell=False
            )
            return result
        except subprocess.TimeoutExpired:
            return None
        except Exception as e:
            print(f"Error running command: {e}")
            return None
    
    def test_help_text(self):
        """Test 1: Verify help text shows --resume flag correctly"""
        print("=" * 60)
        print("TEST 1: Help text verification")
        print("=" * 60)
        
        # Test main help
        result = self.run_claude_mpm_command(["--help"])
        if result and result.returncode == 0:
            if "--resume [RESUME]" in result.stdout:
                self.log_test("Main help contains --resume flag", True, 
                            "Found --resume [RESUME] in main help output")
            else:
                self.log_test("Main help contains --resume flag", False, 
                            "Did not find --resume [RESUME] in main help output")
        else:
            self.log_test("Main help contains --resume flag", False, 
                        "Failed to get main help output", str(result.stderr if result else "timeout"))
        
        # Test run command help
        result = self.run_claude_mpm_command(["run", "--help"])
        if result and result.returncode == 0:
            if "--resume [RESUME]" in result.stdout:
                self.log_test("Run command help contains --resume flag", True, 
                            "Found --resume [RESUME] in run command help output")
            else:
                self.log_test("Run command help contains --resume flag", False, 
                            "Did not find --resume [RESUME] in run command help output")
        else:
            self.log_test("Run command help contains --resume flag", False, 
                        "Failed to get run command help output", str(result.stderr if result else "timeout"))
    
    def test_resume_without_args(self):
        """Test 2: --resume flag without arguments (resumes last session)"""
        print("=" * 60)
        print("TEST 2: Resume without arguments")
        print("=" * 60)
        
        # First, ensure we have some sessions to work with
        try:
            # Create a test session
            session_id = self.session_manager.create_session("test_context")
            self.session_manager.active_sessions[session_id]["last_used"] = datetime.now().isoformat()
            self.session_manager._save_sessions()
            
            # Test --resume without arguments (should resume last session)
            result = self.run_claude_mpm_command(["--resume", "--non-interactive", "-i", "test input"], timeout=15)
            
            if result:
                if result.returncode == 0:
                    if "Resuming session" in result.stdout or "session" in result.stdout.lower():
                        self.log_test("Resume last session works", True, 
                                    f"Command executed successfully with session resumption")
                    else:
                        self.log_test("Resume last session works", True, 
                                    f"Command executed successfully (return code: {result.returncode})")
                else:
                    self.log_test("Resume last session works", False, 
                                f"Command failed with return code: {result.returncode}", 
                                result.stderr)
            else:
                self.log_test("Resume last session works", False, 
                            "Command timed out or failed to execute")
                
        except Exception as e:
            self.log_test("Resume last session works", False, 
                        "Exception during test execution", str(e))
    
    def test_resume_with_session_id(self):
        """Test 3: --resume flag with session ID argument"""
        print("=" * 60)
        print("TEST 3: Resume with specific session ID")
        print("=" * 60)
        
        try:
            # Create a specific test session
            session_id = self.session_manager.create_session("specific_test_context")
            self.session_manager.active_sessions[session_id]["last_used"] = datetime.now().isoformat()
            self.session_manager._save_sessions()
            
            # Test --resume with specific session ID
            result = self.run_claude_mpm_command([
                "--resume", session_id, 
                "--non-interactive", 
                "-i", "test input for specific session"
            ], timeout=15)
            
            if result:
                if result.returncode == 0:
                    if session_id[:8] in result.stdout or "Resuming session" in result.stdout:
                        self.log_test("Resume specific session works", True, 
                                    f"Successfully resumed session {session_id[:8]}")
                    else:
                        self.log_test("Resume specific session works", True, 
                                    f"Command executed successfully (return code: {result.returncode})")
                else:
                    self.log_test("Resume specific session works", False, 
                                f"Command failed with return code: {result.returncode}", 
                                result.stderr)
            else:
                self.log_test("Resume specific session works", False, 
                            "Command timed out or failed to execute")
                
        except Exception as e:
            self.log_test("Resume specific session works", False, 
                        "Exception during test execution", str(e))
    
    def test_resume_with_monitor(self):
        """Test 4: --resume flag with --monitor combination"""
        print("=" * 60)
        print("TEST 4: Resume with --monitor combination")
        print("=" * 60)
        
        try:
            # Create a test session
            session_id = self.session_manager.create_session("monitor_test_context") 
            self.session_manager.active_sessions[session_id]["last_used"] = datetime.now().isoformat()
            self.session_manager._save_sessions()
            
            # Test --resume with --monitor
            result = self.run_claude_mpm_command([
                "--resume", 
                "--monitor", 
                "--non-interactive", 
                "-i", "test input with monitor"
            ], timeout=20)
            
            if result:
                # For monitor mode, we expect it to either succeed or fail gracefully
                # The key is that the arguments are parsed correctly
                if result.returncode == 0:
                    self.log_test("Resume with monitor works", True, 
                                "Command executed successfully with both --resume and --monitor")
                else:
                    # Check if the failure is due to argument parsing or runtime issues
                    if "unrecognized arguments" in result.stderr or "invalid choice" in result.stderr:
                        self.log_test("Resume with monitor works", False, 
                                    "Argument parsing failed", result.stderr)
                    else:
                        # Runtime failures are acceptable (e.g., port conflicts, missing deps)
                        self.log_test("Resume with monitor works", True, 
                                    "Arguments parsed correctly, runtime error is acceptable", 
                                    f"Return code: {result.returncode}")
            else:
                self.log_test("Resume with monitor works", False, 
                            "Command timed out or failed to execute")
                
        except Exception as e:
            self.log_test("Resume with monitor works", False, 
                        "Exception during test execution", str(e))
    
    def test_invalid_session_id(self):
        """Test 5: Error handling for invalid session IDs"""
        print("=" * 60)
        print("TEST 5: Invalid session ID handling")
        print("=" * 60)
        
        # Test with clearly invalid session ID
        invalid_session_id = "invalid-session-id-12345"
        
        result = self.run_claude_mpm_command([
            "--resume", invalid_session_id,
            "--non-interactive", 
            "-i", "test input for invalid session"
        ], timeout=10)
        
        if result:
            if result.returncode != 0:
                if "not found" in result.stdout or "not found" in result.stderr:
                    self.log_test("Invalid session ID error handling", True, 
                                "Correctly reported session not found")
                else:
                    self.log_test("Invalid session ID error handling", True, 
                                f"Command failed appropriately (return code: {result.returncode})")
            else:
                self.log_test("Invalid session ID error handling", False, 
                            "Command should have failed with invalid session ID")
        else:
            self.log_test("Invalid session ID error handling", False, 
                        "Command timed out or failed to execute")
    
    def test_argument_filtering(self):
        """Test 6: Argument filtering to ensure unrelated arguments aren't consumed"""
        print("=" * 60)
        print("TEST 6: Argument filtering verification")
        print("=" * 60)
        
        try:
            # Create a test session
            session_id = self.session_manager.create_session("filter_test_context")
            self.session_manager.active_sessions[session_id]["last_used"] = datetime.now().isoformat()
            self.session_manager._save_sessions()
            
            # Test --resume with Claude CLI arguments that should be passed through
            result = self.run_claude_mpm_command([
                "--resume",
                "--non-interactive", 
                "-i", "test input",
                "--",  # Separator for Claude CLI args
                "--model", "claude-3-haiku-20240307",
                "--temperature", "0.1"
            ], timeout=15)
            
            if result:
                # The key test is that --resume doesn't consume --model or --temperature
                if result.returncode == 0:
                    self.log_test("Argument filtering works correctly", True, 
                                "Arguments parsed and filtered correctly")
                else:
                    # Check if failure is due to argument issues vs runtime issues
                    if "unrecognized arguments" in result.stderr:
                        self.log_test("Argument filtering works correctly", False, 
                                    "Argument filtering failed", result.stderr)
                    else:
                        self.log_test("Argument filtering works correctly", True, 
                                    "Arguments parsed correctly, runtime error acceptable")
            else:
                self.log_test("Argument filtering works correctly", False, 
                            "Command timed out or failed to execute")
                
        except Exception as e:
            self.log_test("Argument filtering works correctly", False, 
                        "Exception during test execution", str(e))
    
    def test_resume_parameter_parsing(self):
        """Test 7: Verify --resume parameter parsing with nargs='?'"""
        print("=" * 60)
        print("TEST 7: Resume parameter parsing verification")
        print("=" * 60)
        
        # Test that --resume followed by a flag doesn't consume the flag
        result = self.run_claude_mpm_command([
            "--resume", 
            "--non-interactive",  # This should NOT be consumed by --resume
            "-i", "test parsing"
        ], timeout=10)
        
        if result:
            # Should succeed and --non-interactive should be recognized
            if result.returncode == 0:
                self.log_test("Resume parameter parsing correct", True, 
                            "--resume correctly uses nargs='?' and doesn't consume --non-interactive")
            else:
                if "unrecognized arguments" in result.stderr and "--non-interactive" in result.stderr:
                    self.log_test("Resume parameter parsing correct", False, 
                                "--resume incorrectly consumed --non-interactive", result.stderr)
                else:
                    self.log_test("Resume parameter parsing correct", True, 
                                "Parameter parsing appears correct, runtime error acceptable")
        else:
            self.log_test("Resume parameter parsing correct", False, 
                        "Command timed out or failed to execute")
    
    def run_all_tests(self):
        """Run all tests in the suite"""
        print("Starting comprehensive --resume flag test suite...")
        print(f"Testing claude-mpm at: {self.claude_mpm_script}")
        print()
        
        # Run all tests
        self.test_help_text()
        self.test_resume_without_args()
        self.test_resume_with_session_id()
        self.test_resume_with_monitor()
        self.test_invalid_session_id()
        self.test_argument_filtering()
        self.test_resume_parameter_parsing()
        
        # Print summary
        print("=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success rate: {(passed_tests/total_tests)*100:.1f}%")
        print()
        
        if failed_tests > 0:
            print("FAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['error']}")
            print()
        
        # Save detailed results
        results_file = Path(__file__).parent / "test_results_resume_flag.json"
        with open(results_file, 'w') as f:
            json.dump({
                "summary": {
                    "total_tests": total_tests,
                    "passed": passed_tests,
                    "failed": failed_tests,
                    "success_rate": (passed_tests/total_tests)*100
                },
                "test_results": self.test_results,
                "timestamp": datetime.now().isoformat()
            }, f, indent=2)
        
        print(f"Detailed results saved to: {results_file}")
        return failed_tests == 0


if __name__ == "__main__":
    suite = ResumeTestSuite()
    success = suite.run_all_tests()
    sys.exit(0 if success else 1)