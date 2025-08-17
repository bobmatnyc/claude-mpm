#!/usr/bin/env python3
"""
Comprehensive QA Test Suite for Memory System Working Directory Fix

This test suite validates that the memory initialization fix correctly uses
the current working directory instead of the project installation directory.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# Add the project source to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


class MemorySystemQATest:
    def __init__(self):
        self.test_results = {}
        self.test_dirs = []
        self.original_cwd = os.getcwd()
        self.mpm_cmd = str(project_root.parent / "claude-mpm")

    def log(self, test_name, status, message="", details=None):
        """Log test results"""
        self.test_results[test_name] = {
            "status": status,
            "message": message,
            "details": details or {},
        }
        print(f"[{status.upper()}] {test_name}: {message}")
        if details:
            for key, value in details.items():
                print(f"  {key}: {value}")

    def cleanup(self):
        """Clean up test directories"""
        os.chdir(self.original_cwd)
        for test_dir in self.test_dirs:
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir, ignore_errors=True)

    def create_test_directory(self, name):
        """Create a temporary test directory"""
        test_dir = tempfile.mkdtemp(prefix=f"mpm_memory_test_{name}_")
        self.test_dirs.append(test_dir)
        return test_dir

    def run_mpm_command(self, args, cwd=None):
        """Run MPM command and return result"""
        if cwd:
            os.chdir(cwd)

        cmd = [self.mpm_cmd] + args
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return {
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {"returncode": -1, "stdout": "", "stderr": "Command timed out"}
        except Exception as e:
            return {"returncode": -1, "stdout": "", "stderr": str(e)}

    def test_memory_init_different_directories(self):
        """Test 1: Memory init from different directories"""
        print("\n=== Test 1: Memory init from different directories ===")

        # Test directory 1: Simple temp directory
        test_dir1 = self.create_test_directory("simple")
        result1 = self.run_mpm_command(["memory", "init"], cwd=test_dir1)

        memory_dir1 = os.path.join(test_dir1, ".claude-mpm", "memories")
        memory_exists1 = os.path.exists(memory_dir1)

        # Test directory 2: Nested directory structure
        test_dir2 = self.create_test_directory("nested")
        nested_dir = os.path.join(test_dir2, "project", "subproject")
        os.makedirs(nested_dir, exist_ok=True)
        result2 = self.run_mpm_command(["memory", "init"], cwd=nested_dir)

        memory_dir2 = os.path.join(nested_dir, ".claude-mpm", "memories")
        memory_exists2 = os.path.exists(memory_dir2)

        # Test directory 3: Directory with spaces
        test_dir3 = self.create_test_directory("with_spaces")
        spaced_dir = os.path.join(test_dir3, "My Project Folder")
        os.makedirs(spaced_dir, exist_ok=True)
        result3 = self.run_mpm_command(["memory", "init"], cwd=spaced_dir)

        memory_dir3 = os.path.join(spaced_dir, ".claude-mpm", "memories")
        memory_exists3 = os.path.exists(memory_dir3)

        success = all(
            [
                result1["returncode"] == 0,
                result2["returncode"] == 0,
                result3["returncode"] == 0,
                memory_exists1,
                memory_exists2,
                memory_exists3,
            ]
        )

        self.log(
            "memory_init_different_directories",
            "PASS" if success else "FAIL",
            f"Memory init tested in {len([test_dir1, nested_dir, spaced_dir])} different directories",
            {
                "simple_dir_success": f"{result1['returncode'] == 0} (memory exists: {memory_exists1})",
                "nested_dir_success": f"{result2['returncode'] == 0} (memory exists: {memory_exists2})",
                "spaced_dir_success": f"{result3['returncode'] == 0} (memory exists: {memory_exists3})",
                "simple_dir_path": memory_dir1,
                "nested_dir_path": memory_dir2,
                "spaced_dir_path": memory_dir3,
            },
        )

        return success, [
            test_dir1,
            nested_dir,
            spaced_dir,
            memory_dir1,
            memory_dir2,
            memory_dir3,
        ]

    def test_memory_directory_location(self):
        """Test 2: Verify .claude-mpm/memories is created in current directory"""
        print("\n=== Test 2: Memory directory location verification ===")

        test_dir = self.create_test_directory("location_check")

        # Initialize memory
        result = self.run_mpm_command(["memory", "init"], cwd=test_dir)

        # Check that memory directory is in the current directory, not installation directory
        expected_memory_dir = os.path.join(test_dir, ".claude-mpm", "memories")
        installation_memory_dir = os.path.join(
            str(project_root), ".claude-mpm", "memories"
        )

        memory_in_current = os.path.exists(expected_memory_dir)
        memory_in_installation = os.path.exists(installation_memory_dir)

        success = result["returncode"] == 0 and memory_in_current

        self.log(
            "memory_directory_location",
            "PASS" if success else "FAIL",
            "Memory directory created in correct location",
            {
                "init_success": result["returncode"] == 0,
                "memory_in_current_dir": memory_in_current,
                "memory_in_installation_dir": memory_in_installation,
                "expected_path": expected_memory_dir,
                "installation_path": installation_memory_dir,
            },
        )

        return success, test_dir

    def test_memory_commands_functionality(self):
        """Test 3: Test memory status, add, and other commands"""
        print("\n=== Test 3: Memory commands functionality ===")

        test_dir = self.create_test_directory("commands_test")

        # Initialize memory
        init_result = self.run_mpm_command(["memory", "init"], cwd=test_dir)

        # Test memory status
        status_result = self.run_mpm_command(["memory", "status"], cwd=test_dir)

        # Test memory add with correct syntax
        test_memory_content = "This is a test memory entry for QA validation"
        add_result = self.run_mpm_command(
            ["memory", "add", "qa", "pattern", test_memory_content], cwd=test_dir
        )

        # Test memory status again to see the added memory
        status_after_add = self.run_mpm_command(["memory", "status"], cwd=test_dir)

        # Test memory view to verify content was added
        view_result = self.run_mpm_command(["memory", "view", "qa"], cwd=test_dir)

        success = all(
            [
                init_result["returncode"] == 0,
                status_result["returncode"] == 0,
                add_result["returncode"] == 0,
                status_after_add["returncode"] == 0,
                view_result["returncode"] == 0,
                "test" in view_result["stdout"].lower(),
            ]
        )

        self.log(
            "memory_commands_functionality",
            "PASS" if success else "FAIL",
            "All memory commands executed successfully",
            {
                "init_success": init_result["returncode"] == 0,
                "status_success": status_result["returncode"] == 0,
                "add_success": add_result["returncode"] == 0,
                "view_success": view_result["returncode"] == 0,
                "view_found_content": "test" in view_result["stdout"].lower(),
                "status_output": status_result["stdout"][:200] + "..."
                if len(status_result["stdout"]) > 200
                else status_result["stdout"],
            },
        )

        return success

    def test_backward_compatibility(self):
        """Test 4: Test backward compatibility"""
        print("\n=== Test 4: Backward compatibility test ===")

        test_dir = self.create_test_directory("backward_compat")

        # Create an existing memory structure to test compatibility
        claude_mpm_dir = os.path.join(test_dir, ".claude-mpm")
        memories_dir = os.path.join(claude_mpm_dir, "memories")
        os.makedirs(memories_dir, exist_ok=True)

        # Create a sample existing memory file
        existing_memory_file = os.path.join(memories_dir, "existing_memory.json")
        with open(existing_memory_file, "w") as f:
            json.dump(
                {
                    "content": "Existing memory content",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "type": "test",
                },
                f,
            )

        # Test that existing memory is preserved
        status_result = self.run_mpm_command(["memory", "status"], cwd=test_dir)

        # Add new memory to test that it works with existing structure
        add_result = self.run_mpm_command(
            [
                "memory",
                "add",
                "qa",
                "context",
                "New memory content for backward compatibility test",
            ],
            cwd=test_dir,
        )

        # Check that both old and new memories are accessible
        view_result = self.run_mpm_command(["memory", "view", "qa"], cwd=test_dir)

        success = all(
            [
                status_result["returncode"] == 0,
                add_result["returncode"] == 0,
                view_result["returncode"] == 0,
                "backward compatibility" in view_result["stdout"].lower(),
                os.path.exists(existing_memory_file),  # Original file still exists
            ]
        )

        self.log(
            "backward_compatibility",
            "PASS" if success else "FAIL",
            "Backward compatibility maintained",
            {
                "status_success": status_result["returncode"] == 0,
                "add_success": add_result["returncode"] == 0,
                "view_success": view_result["returncode"] == 0,
                "content_includes_new": "backward compatibility"
                in view_result["stdout"].lower(),
                "existing_file_preserved": os.path.exists(existing_memory_file),
            },
        )

        return success

    def test_edge_cases(self):
        """Test 5: Edge cases and error conditions"""
        print("\n=== Test 5: Edge cases and error conditions ===")

        # Test 1: Directory without write permissions
        test_dir = self.create_test_directory("no_write_perms")
        try:
            os.chmod(test_dir, 0o444)  # Read-only
            no_write_result = self.run_mpm_command(["memory", "init"], cwd=test_dir)
            os.chmod(test_dir, 0o755)  # Restore permissions for cleanup
        except:
            no_write_result = {"returncode": -1, "stderr": "Permission test failed"}

        # Test 2: Very long path
        long_path_dir = self.create_test_directory("long_path")
        deep_dir = os.path.join(
            long_path_dir, *["very"] * 10, "deep", "directory", "structure"
        )
        try:
            os.makedirs(deep_dir, exist_ok=True)
            long_path_result = self.run_mpm_command(["memory", "init"], cwd=deep_dir)
            long_path_memory_exists = os.path.exists(
                os.path.join(deep_dir, ".claude-mpm", "memories")
            )
        except Exception as e:
            long_path_result = {"returncode": -1, "stderr": str(e)}
            long_path_memory_exists = False

        # Test 3: Memory commands in directory without initialization
        uninit_dir = self.create_test_directory("uninitialized")
        status_uninit = self.run_mpm_command(["memory", "status"], cwd=uninit_dir)
        add_uninit = self.run_mpm_command(
            ["memory", "add", "qa", "pattern", "test"], cwd=uninit_dir
        )

        success = all(
            [
                no_write_result["returncode"] != 0,  # Should fail gracefully
                long_path_result["returncode"] == 0
                and long_path_memory_exists,  # Should work with long paths
                status_uninit["returncode"] == 0,  # Should auto-initialize and succeed
                add_uninit["returncode"] == 0,  # Should auto-initialize and succeed
            ]
        )

        self.log(
            "edge_cases",
            "PASS" if success else "FAIL",
            "Edge cases handled appropriately",
            {
                "no_write_permissions_handled": no_write_result["returncode"] != 0,
                "long_path_works": long_path_result["returncode"] == 0
                and long_path_memory_exists,
                "uninit_status_handled": status_uninit["returncode"] == 0,
                "uninit_add_handled": add_uninit["returncode"] == 0,
            },
        )

        return success

    def test_specific_directory_case(self):
        """Test 6: Specific use case from ~/Clients/Spin.Travel directory"""
        print(
            "\n=== Test 6: Specific directory case (~/Clients/Spin.Travel simulation) ==="
        )

        # Simulate the specific directory structure
        test_dir = self.create_test_directory("clients_simulation")
        spin_travel_dir = os.path.join(test_dir, "Clients", "Spin.Travel")
        os.makedirs(spin_travel_dir, exist_ok=True)

        # Initialize memory in this specific directory
        init_result = self.run_mpm_command(["memory", "init"], cwd=spin_travel_dir)

        # Verify memory directory is created in the correct location
        expected_memory_dir = os.path.join(spin_travel_dir, ".claude-mpm", "memories")
        memory_exists = os.path.exists(expected_memory_dir)

        # Test adding travel-related memory
        add_result = self.run_mpm_command(
            [
                "memory",
                "add",
                "engineer",
                "context",
                "Spin.Travel project configuration and API endpoints",
            ],
            cwd=spin_travel_dir,
        )

        # Test memory operations work in this directory
        status_result = self.run_mpm_command(["memory", "status"], cwd=spin_travel_dir)
        view_result = self.run_mpm_command(
            ["memory", "view", "engineer"], cwd=spin_travel_dir
        )

        success = all(
            [
                init_result["returncode"] == 0,
                memory_exists,
                add_result["returncode"] == 0,
                status_result["returncode"] == 0,
                view_result["returncode"] == 0,
                "spin.travel" in view_result["stdout"].lower(),
            ]
        )

        self.log(
            "specific_directory_case",
            "PASS" if success else "FAIL",
            "Spin.Travel directory simulation successful",
            {
                "init_success": init_result["returncode"] == 0,
                "memory_dir_created": memory_exists,
                "memory_dir_path": expected_memory_dir,
                "add_success": add_result["returncode"] == 0,
                "status_success": status_result["returncode"] == 0,
                "view_success": view_result["returncode"] == 0,
                "content_includes_project": "spin.travel"
                in view_result["stdout"].lower(),
            },
        )

        return success

    def run_all_tests(self):
        """Run all QA tests"""
        print(
            "Starting comprehensive QA testing for Memory System Working Directory Fix"
        )
        print("=" * 80)

        try:
            # Run all tests
            test1_success, test1_data = self.test_memory_init_different_directories()
            test2_success, test2_data = self.test_memory_directory_location()
            test3_success = self.test_memory_commands_functionality()
            test4_success = self.test_backward_compatibility()
            test5_success = self.test_edge_cases()
            test6_success = self.test_specific_directory_case()

            # Calculate overall success
            all_tests_passed = all(
                [
                    test1_success,
                    test2_success,
                    test3_success,
                    test4_success,
                    test5_success,
                    test6_success,
                ]
            )

            # Generate summary
            print("\n" + "=" * 80)
            print("QA TEST SUMMARY")
            print("=" * 80)

            for test_name, result in self.test_results.items():
                status_indicator = "✅" if result["status"] == "PASS" else "❌"
                print(f"{status_indicator} {test_name}: {result['message']}")

            print(f"\nOverall Result: {'✅ PASS' if all_tests_passed else '❌ FAIL'}")
            print(
                f"Tests Passed: {sum(1 for r in self.test_results.values() if r['status'] == 'PASS')}/{len(self.test_results)}"
            )

            return all_tests_passed, self.test_results

        finally:
            self.cleanup()


def main():
    """Run the comprehensive QA test suite"""
    qa_test = MemorySystemQATest()
    success, results = qa_test.run_all_tests()

    # Save detailed results
    results_file = os.path.join(os.getcwd(), "memory_system_qa_results.json")
    with open(results_file, "w") as f:
        json.dump(
            {
                "overall_success": success,
                "timestamp": subprocess.check_output(["date", "-u"]).decode().strip(),
                "test_results": results,
            },
            f,
            indent=2,
        )

    print(f"\nDetailed results saved to: {results_file}")

    # Return appropriate exit code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
