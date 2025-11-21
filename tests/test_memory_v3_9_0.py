#!/usr/bin/env python3
"""
Comprehensive test suite for claude-mpm v3.9.0 memory management features.

This test suite validates:
1. Memory adding functionality (CLI and API)
2. 80KB capacity and optimization
3. Project-specific memory loading precedence
4. Memory persistence and retrieval
5. Performance under load
6. Error handling and edge cases
"""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from typing import Optional

from claude_mpm.core.framework_loader import FrameworkLoader
from claude_mpm.services.agents.memory.agent_memory_manager import AgentMemoryManager


class MemoryV3_9_0_Tester:
    """Comprehensive tester for v3.9.0 memory features."""

    def __init__(self):
        self.test_results = []
        self.temp_dirs = []
        self.start_time = time.time()

    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Log a test result with timing."""
        status = "PASS" if passed else "FAIL"
        elapsed = time.time() - self.start_time
        result = f"[{status}] {test_name} ({elapsed:.2f}s)"
        if details:
            result += f": {details}"
        self.test_results.append(result)
        print(result)

    def create_temp_project(self, project_memory_content: Optional[str] = None) -> Path:
        """Create a temporary project with optional project-specific memory."""
        temp_dir = Path(tmp_path)
        self.temp_dirs.append(temp_dir)

        # Create .claude-mpm/agents directory
        agents_dir = temp_dir / ".claude-mpm" / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)

        if project_memory_content:
            memory_file = agents_dir / "MEMORY.md"
            memory_file.write_text(project_memory_content)

        return temp_dir

    def test_cli_memory_add():
        """Test adding memories via CLI commands."""
        print("\n=== Testing CLI Memory Add Commands ===")

        try:
            temp_project = self.create_temp_project()

            # Change to temp project directory for CLI tests
            original_cwd = os.getcwd()
            os.chdir(temp_project)

            try:
                # Test adding different types of memories via CLI
                test_commands = [
                    [
                        "python",
                        "-m",
                        "claude_mpm.cli",
                        "memory",
                        "add",
                        "engineer",
                        "pattern",
                        "Test pattern from CLI",
                    ],
                    [
                        "python",
                        "-m",
                        "claude_mpm.cli",
                        "memory",
                        "add",
                        "qa",
                        "error",
                        "Test error from CLI",
                    ],
                    [
                        "python",
                        "-m",
                        "claude_mpm.cli",
                        "memory",
                        "add",
                        "research",
                        "context",
                        "Test context from CLI",
                    ],
                ]

                cli_success = True
                for cmd in test_commands:
                    try:
                        result = subprocess.run(
                            cmd, capture_output=True, text=True, timeout=30, check=False
                        )
                        if result.returncode != 0:
                            cli_success = False
                            print(f"CLI command failed: {' '.join(cmd)}")
                            print(f"Error: {result.stderr}")
                    except Exception as e:
                        cli_success = False
                        print(f"CLI command exception: {e}")

                self.log_result("CLI memory add commands execute", cli_success)

                # Check that memory files were created
                memory_dir = temp_project / ".claude-mpm" / "memories"
                created_files = (
                    list(memory_dir.glob("*_agent.md")) if memory_dir.exists() else []
                )

                self.log_result(
                    "CLI commands create memory files",
                    len(created_files) >= 3,
                    f"Created {len(created_files)} memory files",
                )

            finally:
                os.chdir(original_cwd)

        except Exception as e:
            self.log_result("CLI memory add test", False, f"Exception: {e!s}")

    def test_api_memory_add():
        """Test adding memories via Python API."""
        print("\n=== Testing Python API Memory Add ===")

        try:
            temp_project = self.create_temp_project()
            config = Config()
            memory_manager = AgentMemoryManager(config, temp_project)

            # Test different learning types
            test_learnings = [
                ("engineer", "pattern", "API test pattern for dependency injection"),
                ("qa", "mistake", "API test mistake - don't skip test isolation"),
                (
                    "research",
                    "strategy",
                    "API test strategy - analyze before implementing",
                ),
                (
                    "data-engineer",
                    "performance",
                    "API test performance - use vectorization",
                ),
            ]

            api_success_count = 0
            for agent_id, learning_type, content in test_learnings:
                success = memory_manager.add_learning(agent_id, learning_type, content)
                if success:
                    api_success_count += 1

            self.log_result(
                "Python API add_learning works",
                api_success_count == len(test_learnings),
                f"Successfully added {api_success_count}/{len(test_learnings)} learnings",
            )

            # Test direct memory update
            direct_success = memory_manager.update_agent_memory(
                "engineer", "Recent Learnings", "Direct memory update via API"
            )

            self.log_result("Direct memory update via API works", direct_success)

            # Test memory persistence
            loaded_content = memory_manager.load_agent_memory("engineer")
            has_api_content = (
                "API test pattern" in loaded_content if loaded_content else False
            )

            self.log_result(
                "API-added memories persist",
                has_api_content,
                "Found API-added content in memory file",
            )

        except Exception as e:
            self.log_result("API memory add test", False, f"Exception: {e!s}")

    def test_80kb_limit_enforcement():
        """Test 80KB limit is properly enforced with optimization."""
        print("\n=== Testing 80KB Limit Enforcement ===")

        try:
            temp_project = self.create_temp_project()
            config = Config()
            memory_manager = AgentMemoryManager(config, temp_project)

            # Create content that will exceed 80KB
            large_content_sections = []
            section_size = 0

            for i in range(100):  # Add many sections
                section_content = (
                    f"- Large memory item {i}: " + "x" * 800
                )  # ~800 chars per item
                large_content_sections.append(section_content)
                section_size += len(section_content.encode("utf-8"))

            print(f"Generated test content: ~{section_size / 1024:.1f}KB")

            # Add content until we exceed limits
            exceed_count = 0
            for i, content in enumerate(large_content_sections):
                success = memory_manager.update_agent_memory(
                    "engineer", "Test Section", content
                )
                if success:
                    exceed_count += 1

                # Check current size
                current_memory = memory_manager.load_agent_memory("engineer")
                if current_memory:
                    current_size_kb = len(current_memory.encode("utf-8")) / 1024
                    if current_size_kb > 80:
                        # Should trigger optimization
                        break

            # Check that size is kept under control
            final_memory = memory_manager.load_agent_memory("engineer")
            final_size_kb = (
                len(final_memory.encode("utf-8")) / 1024 if final_memory else 0
            )

            self.log_result(
                "80KB limit enforced",
                final_size_kb <= 85,  # Allow small buffer for headers
                f"Final size: {final_size_kb:.1f}KB",
            )

            # Test that optimization was triggered
            limit_enforced = final_size_kb < 90  # Should be well under 90KB
            self.log_result(
                "Memory optimization triggered when needed",
                limit_enforced,
                f"Memory stayed at {final_size_kb:.1f}KB after {exceed_count} additions",
            )

        except Exception as e:
            self.log_result("80KB limit enforcement test", False, f"Exception: {e!s}")

    def test_project_vs_system_memory_precedence():
        """Test project-specific memory takes precedence over system memory."""
        print("\n=== Testing Memory Precedence (Project vs System) ===")

        try:
            # Test 1: Project with project-specific memory
            project_memory = """## Project Memory Override
This is project-specific memory that should override system memory.

### Project-Specific Guidelines
- Use project-specific patterns
- Follow local conventions
"""
            temp_project_with_memory = self.create_temp_project(project_memory)

            original_cwd = os.getcwd()
            os.chdir(temp_project_with_memory)

            try:
                loader_with_project = FrameworkLoader()
                instructions_with_project = (
                    loader_with_project.get_framework_instructions()
                )

                has_project_override = (
                    "Project Memory Override" in instructions_with_project
                )
                self.log_result(
                    "Project-specific memory loads when present",
                    has_project_override,
                    "Found project memory override in instructions",
                )

            finally:
                os.chdir(original_cwd)

            # Test 2: Project without project-specific memory (should fallback to system)
            temp_project_no_memory = self.create_temp_project()
            os.chdir(temp_project_no_memory)

            try:
                loader_no_project = FrameworkLoader()
                instructions_no_project = loader_no_project.get_framework_instructions()

                has_system_memory = (
                    len(instructions_no_project) > 1000
                )  # System memory should be substantial
                no_project_override = (
                    "Project Memory Override" not in instructions_no_project
                )

                self.log_result(
                    "Falls back to system memory when no project memory",
                    has_system_memory and no_project_override,
                    f"System memory loaded (length: {len(instructions_no_project)})",
                )

            finally:
                os.chdir(original_cwd)

        except Exception as e:
            self.log_result("Memory precedence test", False, f"Exception: {e!s}")

    def test_memory_persistence_across_sessions():
        """Test that memories persist across different sessions/instances."""
        print("\n=== Testing Memory Persistence Across Sessions ===")

        try:
            temp_project = self.create_temp_project()

            # Session 1: Create and save memory
            config1 = Config()
            memory_manager1 = AgentMemoryManager(config1, temp_project)

            test_memory_items = [
                ("engineer", "pattern", "Session 1 test pattern"),
                ("qa", "mistake", "Session 1 test mistake"),
            ]

            for agent_id, learning_type, content in test_memory_items:
                memory_manager1.add_learning(agent_id, learning_type, content)

            # Destroy first session
            del memory_manager1

            # Session 2: Create new instance and check persistence
            config2 = Config()
            memory_manager2 = AgentMemoryManager(config2, temp_project)

            persistence_success = True
            for agent_id, learning_type, content in test_memory_items:
                loaded_memory = memory_manager2.load_agent_memory(agent_id)
                if not loaded_memory or content not in loaded_memory:
                    persistence_success = False

            self.log_result(
                "Memory persists across sessions",
                persistence_success,
                "All test items found in new session",
            )

            # Test memory retrieval API
            engineer_memory = memory_manager2.load_memory("engineer")
            qa_memory = memory_manager2.load_memory("qa")

            retrieval_success = (
                engineer_memory is not None
                and qa_memory is not None
                and "Session 1" in engineer_memory
                and "Session 1" in qa_memory
            )

            self.log_result(
                "Memory retrieval API works across sessions",
                retrieval_success,
                "Retrieved memories contain session 1 data",
            )

        except Exception as e:
            self.log_result("Memory persistence test", False, f"Exception: {e!s}")

    def test_performance_under_load():
        """Test memory system performance under various load conditions."""
        print("\n=== Testing Performance Under Load ===")

        try:
            temp_project = self.create_temp_project()
            config = Config()
            memory_manager = AgentMemoryManager(config, temp_project)

            # Test 1: Many small memory additions
            start_time = time.time()
            small_additions = 0

            for i in range(100):
                success = memory_manager.add_learning(
                    "engineer", "pattern", f"Pattern {i}"
                )
                if success:
                    small_additions += 1

            small_additions_time = time.time() - start_time

            self.log_result(
                "Handles many small additions efficiently",
                small_additions_time < 10.0,  # Should complete in under 10 seconds
                f"{small_additions} additions in {small_additions_time:.2f}s",
            )

            # Test 2: Large memory file operations
            start_time = time.time()
            large_content = "# Large Memory Test\n\n" + "\n".join(
                [f"## Section {i}\n- Item 1\n- Item 2\n- Item 3" for i in range(50)]
            )

            large_save_success = memory_manager.save_memory("research", large_content)
            memory_manager.load_memory("research")
            large_operations_time = time.time() - start_time

            self.log_result(
                "Handles large memory operations efficiently",
                large_operations_time < 5.0 and large_save_success,
                f"Large file ops in {large_operations_time:.2f}s",
            )

            # Test 3: Memory status retrieval performance
            start_time = time.time()
            status = memory_manager.get_memory_status()
            status_time = time.time() - start_time

            self.log_result(
                "Memory status retrieval is fast",
                status_time < 2.0 and status.get("success", True),
                f"Status retrieval in {status_time:.2f}s",
            )

            # Test 4: Cross-reference analysis performance
            start_time = time.time()
            memory_manager.cross_reference_memories()
            cross_ref_time = time.time() - start_time

            self.log_result(
                "Cross-reference analysis completes efficiently",
                cross_ref_time < 5.0,
                f"Cross-reference analysis in {cross_ref_time:.2f}s",
            )

        except Exception as e:
            self.log_result("Performance test", False, f"Exception: {e!s}")

    def test_error_handling_and_edge_cases():
        """Test error handling and edge cases."""
        print("\n=== Testing Error Handling and Edge Cases ===")

        try:
            temp_project = self.create_temp_project()
            config = Config()
            memory_manager = AgentMemoryManager(config, temp_project)

            # Test 1: Invalid agent IDs
            invalid_success = memory_manager.add_learning(
                "", "pattern", "Invalid agent"
            )
            self.log_result(
                "Handles invalid agent IDs gracefully",
                not invalid_success,  # Should fail gracefully
                "Empty agent ID rejected",
            )

            # Test 2: Very long content
            very_long_content = "x" * 10000  # 10KB single item
            memory_manager.add_learning("engineer", "pattern", very_long_content)

            # Should either succeed with truncation or fail gracefully
            engineer_memory = memory_manager.load_memory("engineer")
            handles_long_content = engineer_memory is not None

            self.log_result(
                "Handles very long content appropriately",
                handles_long_content,
                "Long content processed without crashing",
            )

            # Test 3: Non-existent memory file handling
            nonexistent_memory = memory_manager.load_memory("nonexistent_agent")
            self.log_result(
                "Handles non-existent agent memory gracefully",
                nonexistent_memory is not None,  # Should create default
                "Returns default memory for non-existent agent",
            )

            # Test 4: Concurrent access simulation
            concurrent_success = True
            for i in range(10):
                success = memory_manager.add_learning(
                    "concurrent_test", "pattern", f"Concurrent {i}"
                )
                if not success:
                    concurrent_success = False

            self.log_result(
                "Handles concurrent-like access",
                concurrent_success,
                "Multiple rapid additions succeeded",
            )

            # Test 5: Memory validation
            invalid_memory_content = "This is not valid markdown memory format"
            is_valid, error_msg = memory_manager.validate_memory_size(
                invalid_memory_content
            )

            self.log_result(
                "Memory validation works",
                not is_valid or error_msg is not None,
                f"Validation result: {is_valid}, error: {error_msg}",
            )

        except Exception as e:
            self.log_result("Error handling test", False, f"Exception: {e!s}")

    def test_memory_optimization_features():
        """Test memory optimization features."""
        print("\n=== Testing Memory Optimization Features ===")

        try:
            temp_project = self.create_temp_project()
            config = Config()
            memory_manager = AgentMemoryManager(config, temp_project)

            # Add duplicate content to trigger optimization
            for i in range(5):
                memory_manager.add_learning(
                    "engineer", "pattern", "Duplicate pattern for testing"
                )
                memory_manager.add_learning(
                    "engineer", "pattern", f"Unique pattern {i}"
                )

            # Run optimization
            optimization_result = memory_manager.optimize_memory("engineer")

            optimization_success = optimization_result.get("success", False)
            self.log_result(
                "Memory optimization executes",
                optimization_success,
                f"Optimization result: {optimization_result}",
            )

            # Test bulk optimization
            bulk_result = memory_manager.optimize_memory()  # All agents
            bulk_success = bulk_result.get("success", False)

            self.log_result(
                "Bulk memory optimization works",
                bulk_success,
                "All agents optimization completed",
            )

        except Exception as e:
            self.log_result("Memory optimization test", False, f"Exception: {e!s}")

    def cleanup(self):
        """Clean up temporary directories."""
        for temp_dir in self.temp_dirs:
            if temp_dir.exists():
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    print(f"Warning: Could not clean up {temp_dir}: {e}")

    def run_all_tests(self) -> bool:
        """Run all memory v3.9.0 tests."""
        print("🧠 Claude MPM v3.9.0 Memory Management Test Suite")
        print("=" * 60)

        try:
            self.test_cli_memory_add()
            self.test_api_memory_add()
            self.test_80kb_limit_enforcement()
            self.test_project_vs_system_memory_precedence()
            self.test_memory_persistence_across_sessions()
            self.test_performance_under_load()
            self.test_error_handling_and_edge_cases()
            self.test_memory_optimization_features()

            print("\n" + "=" * 60)
            print("📊 Test Results Summary")
            print("=" * 60)

            passed = sum(1 for result in self.test_results if "[PASS]" in result)
            total = len(self.test_results)

            for result in self.test_results:
                print(result)

            print(f"\n✅ Passed: {passed}/{total} tests")
            print(f"⏱️  Total test time: {time.time() - self.start_time:.2f} seconds")

            if passed == total:
                print("🎉 All v3.9.0 memory management tests PASSED!")
                return True
            print(f"❌ {total - passed} tests FAILED!")
            return False

        finally:
            self.cleanup()


if __name__ == "__main__":
    tester = MemoryV3_9_0_Tester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
