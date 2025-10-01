#!/usr/bin/env python3
"""
Performance and Error Scenario Testing for Code Analysis
========================================================

WHY: Tests the performance characteristics and error handling of the code analysis
system under various conditions. Validates that the system performs within acceptable
thresholds and gracefully handles error scenarios.

DESIGN DECISIONS:
- Test with different codebase sizes (small, medium, large)
- Measure event throughput and response times
- Test memory usage during analysis
- Validate error recovery mechanisms
- Test concurrent analysis requests
- Measure UI responsiveness during processing
"""

import gc
import json
import shutil
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict

import psutil

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.socketio.event_normalizer import EventNormalizer
from claude_mpm.tools.code_tree_events import CodeTreeEventEmitter


class CodeAnalysisPerformanceTest:
    """Performance and error scenario testing for code analysis functionality."""

    def __init__(self):
        """Initialize the performance test suite."""
        self.process = psutil.Process()
        self.test_results = {}
        self.performance_metrics = {}
        self.error_scenarios = {}

        # Performance thresholds
        self.thresholds = {
            "max_memory_mb": 500,  # Maximum memory usage in MB
            "min_throughput_eps": 10,  # Minimum events per second
            "max_response_time_ms": 1000,  # Maximum response time in milliseconds
            "max_startup_time_s": 5,  # Maximum startup time in seconds
            "max_analysis_time_s": 30,  # Maximum analysis time for medium codebase
        }

    def create_test_codebase(self, size: str = "small") -> Path:
        """Create a temporary codebase for testing.

        Args:
            size: Size of codebase ('small', 'medium', 'large')

        Returns:
            Path to the temporary codebase directory
        """
        test_dir = Path(tempfile.mkdtemp(prefix=f"code_analysis_test_{size}_"))

        # Define codebase characteristics based on size
        sizes = {
            "small": {
                "files": 5,
                "functions_per_file": 3,
                "classes_per_file": 1,
                "dirs": 2,
            },
            "medium": {
                "files": 25,
                "functions_per_file": 5,
                "classes_per_file": 2,
                "dirs": 5,
            },
            "large": {
                "files": 100,
                "functions_per_file": 8,
                "classes_per_file": 3,
                "dirs": 10,
            },
        }

        config = sizes.get(size, sizes["small"])

        # Create directory structure
        for i in range(config["dirs"]):
            dir_path = test_dir / f"module_{i}"
            dir_path.mkdir()

            # Create files in each directory
            files_per_dir = config["files"] // config["dirs"]
            for j in range(files_per_dir):
                file_path = dir_path / f"file_{j}.py"

                # Generate Python code content
                content = self._generate_python_file(
                    config["classes_per_file"], config["functions_per_file"]
                )

                file_path.write_text(content)

        # Create a main file at root
        main_content = """#!/usr/bin/env python3
\"\"\"Main module for test codebase.\"\"\"

import sys
from pathlib import Path

def main():
    \"\"\"Main entry point.\"\"\"
    print("Test codebase main function")
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""
        (test_dir / "main.py").write_text(main_content)

        return test_dir

    def _generate_python_file(self, num_classes: int, num_functions: int) -> str:
        """Generate a Python file with specified number of classes and functions."""
        content = [
            "#!/usr/bin/env python3",
            '"""Generated test file for performance testing."""',
            "",
            "import os",
            "import sys",
            "from typing import List, Dict, Any",
            "",
        ]

        # Generate classes
        for i in range(num_classes):
            content.extend(
                [
                    f"class TestClass{i}:",
                    f'    """Test class {i} for performance testing."""',
                    "    ",
                    "    def __init__(self):",
                    f'        """Initialize TestClass{i}."""',
                    f"        self.value = {i}",
                    "        self.data = []",
                    "    ",
                    "    def process_data(self, data: List[Any]) -> Dict[str, Any]:",
                    f'        """Process data for TestClass{i}."""',
                    f'        result = {{"processed": len(data), "class_id": {i}}}',
                    "        for item in data:",
                    "            if isinstance(item, (int, float)):",
                    '                result["processed"] += item',
                    "        return result",
                    "    ",
                    "    def get_info(self) -> Dict[str, Any]:",
                    '        """Get class information."""',
                    f'        return {{"class": "TestClass{i}", "value": self.value}}',
                    "",
                ]
            )

        # Generate standalone functions
        for i in range(num_functions):
            content.extend(
                [
                    f'def test_function_{i}(param1: int, param2: str = "default") -> bool:',
                    f'    """Test function {i} for performance testing."""',
                    "    try:",
                    "        result = param1 * len(param2)",
                    f"        if result > {i * 10}:",
                    "            return True",
                    "        return False",
                    "    except Exception as e:",
                    f'        print(f"Error in test_function_{i}: {{e}}")',
                    "        return False",
                    "",
                ]
            )

        # Add a main section
        content.extend(
            [
                "def main():",
                '    """Main function for testing."""',
                '    print("Generated test file main function")',
                "",
                'if __name__ == "__main__":',
                "    main()",
            ]
        )

        return "\n".join(content)

    def cleanup_test_codebase(self, test_dir: Path):
        """Clean up temporary test codebase."""
        if test_dir and test_dir.exists():
            try:
                shutil.rmtree(test_dir)
            except Exception as e:
                print(f"⚠️ Failed to cleanup test directory {test_dir}: {e}")

    def measure_memory_usage(self) -> Dict[str, float]:
        """Measure current memory usage."""
        memory_info = self.process.memory_info()
        return {
            "rss_mb": memory_info.rss / 1024 / 1024,  # Resident Set Size in MB
            "vms_mb": memory_info.vms / 1024 / 1024,  # Virtual Memory Size in MB
            "percent": self.process.memory_percent(),  # Memory percentage
        }

    def test_event_throughput(self, codebase_size: str = "medium") -> Dict[str, Any]:
        """Test event throughput during code analysis."""
        print(f"\n⚡ Testing Event Throughput ({codebase_size} codebase)...")

        test_dir = None
        try:
            # Create test codebase
            test_dir = self.create_test_codebase(codebase_size)

            # Initialize event emitter with stdout mode
            emitter = CodeTreeEventEmitter(
                use_stdout=True, batch_size=5, batch_timeout=0.1
            )

            # Capture events and measure timing
            import contextlib
            import io

            stdout_capture = io.StringIO()
            events_captured = []
            start_time = time.time()

            # Start memory monitoring
            initial_memory = self.measure_memory_usage()

            with contextlib.redirect_stdout(stdout_capture):
                emitter.start()

                # Simulate directory discovery
                for py_file in test_dir.glob("**/*.py"):
                    emitter.emit_file_discovered(
                        str(py_file), "python", py_file.stat().st_size
                    )

                # Simulate file analysis with nodes
                from claude_mpm.tools.code_tree_events import CodeNodeEvent

                node_count = 0
                for py_file in test_dir.glob("**/*.py"):
                    content = py_file.read_text()

                    # Simple parsing to count functions and classes
                    lines = content.split("\n")
                    for i, line in enumerate(lines):
                        if line.strip().startswith("def "):
                            node = CodeNodeEvent(
                                file_path=str(py_file),
                                node_type="function",
                                name=line.split("(")[0].replace("def ", "").strip(),
                                line_start=i + 1,
                                line_end=i + 10,
                                complexity=1,
                            )
                            emitter.emit_node(node)
                            node_count += 1

                        elif line.strip().startswith("class "):
                            node = CodeNodeEvent(
                                file_path=str(py_file),
                                node_type="class",
                                name=line.split("(")[0]
                                .replace("class ", "")
                                .replace(":", "")
                                .strip(),
                                line_start=i + 1,
                                line_end=i + 20,
                                complexity=2,
                            )
                            emitter.emit_node(node)
                            node_count += 1

                    # Emit file completion
                    emitter.emit_file_analyzed(str(py_file), [], 0.1)

                # Emit progress updates
                for i in range(0, 101, 10):
                    emitter.emit_progress(i, 100, f"Processing... {i}%")

                emitter.stop()

            end_time = time.time()
            final_memory = self.measure_memory_usage()

            # Parse captured events
            output_lines = stdout_capture.getvalue().strip().split("\n")
            for line in output_lines:
                if line.strip():
                    try:
                        event_data = json.loads(line)
                        events_captured.append(event_data)
                    except json.JSONDecodeError:
                        continue

            # Calculate metrics
            total_time = end_time - start_time
            throughput = len(events_captured) / total_time if total_time > 0 else 0
            memory_delta = final_memory["rss_mb"] - initial_memory["rss_mb"]

            # Categorize events
            event_types = {}
            for event in events_captured:
                event_type = event.get("type", "unknown")
                event_types[event_type] = event_types.get(event_type, 0) + 1

            success = (
                throughput >= self.thresholds["min_throughput_eps"]
                and final_memory["rss_mb"] <= self.thresholds["max_memory_mb"]
            )

            result = {
                "test_name": f"event_throughput_{codebase_size}",
                "success": success,
                "details": {
                    "codebase_size": codebase_size,
                    "total_events": len(events_captured),
                    "node_events": node_count,
                    "total_time": round(total_time, 3),
                    "throughput_eps": round(throughput, 2),
                    "memory_usage": {
                        "initial_mb": round(initial_memory["rss_mb"], 2),
                        "final_mb": round(final_memory["rss_mb"], 2),
                        "delta_mb": round(memory_delta, 2),
                    },
                    "event_types": event_types,
                    "thresholds": {
                        "min_throughput": self.thresholds["min_throughput_eps"],
                        "max_memory": self.thresholds["max_memory_mb"],
                    },
                },
            }

            if success:
                print(f"✅ Event throughput test passed - {throughput:.1f} events/sec")
            else:
                print(
                    f"❌ Event throughput test failed - {throughput:.1f} events/sec (threshold: {self.thresholds['min_throughput_eps']})"
                )
                if final_memory["rss_mb"] > self.thresholds["max_memory_mb"]:
                    print(
                        f"   Memory usage: {final_memory['rss_mb']:.1f} MB (threshold: {self.thresholds['max_memory_mb']} MB)"
                    )

            return result

        except Exception as e:
            return {
                "test_name": f"event_throughput_{codebase_size}",
                "success": False,
                "details": {"error": str(e)},
            }
        finally:
            if test_dir:
                self.cleanup_test_codebase(test_dir)

    def test_memory_usage_scaling(self) -> Dict[str, Any]:
        """Test memory usage scaling with different codebase sizes."""
        print("\n📊 Testing Memory Usage Scaling...")

        sizes = ["small", "medium", "large"]
        scaling_results = []

        for size in sizes:
            print(f"   Testing {size} codebase...")

            test_dir = None
            try:
                # Force garbage collection before test
                gc.collect()

                test_dir = self.create_test_codebase(size)
                initial_memory = self.measure_memory_usage()

                # Initialize emitter and process files
                emitter = CodeTreeEventEmitter(
                    use_stdout=False
                )  # Reduce output overhead
                emitter.start()

                # Process files
                file_count = 0
                for py_file in test_dir.glob("**/*.py"):
                    emitter.emit_file_discovered(
                        str(py_file), "python", py_file.stat().st_size
                    )
                    file_count += 1

                    # Create some nodes for each file
                    for i in range(5):  # 5 nodes per file
                        from claude_mpm.tools.code_tree_events import CodeNodeEvent

                        node = CodeNodeEvent(
                            file_path=str(py_file),
                            node_type="function",
                            name=f"test_function_{i}",
                            line_start=i * 10,
                            line_end=(i + 1) * 10,
                        )
                        emitter.emit_node(node)

                emitter.stop()

                final_memory = self.measure_memory_usage()
                memory_per_file = (
                    (final_memory["rss_mb"] - initial_memory["rss_mb"]) / file_count
                    if file_count > 0
                    else 0
                )

                scaling_results.append(
                    {
                        "size": size,
                        "file_count": file_count,
                        "initial_memory_mb": round(initial_memory["rss_mb"], 2),
                        "final_memory_mb": round(final_memory["rss_mb"], 2),
                        "memory_delta_mb": round(
                            final_memory["rss_mb"] - initial_memory["rss_mb"], 2
                        ),
                        "memory_per_file_kb": round(memory_per_file * 1024, 2),
                    }
                )

            except Exception as e:
                scaling_results.append({"size": size, "error": str(e)})
            finally:
                if test_dir:
                    self.cleanup_test_codebase(test_dir)

        # Analyze scaling characteristics
        valid_results = [r for r in scaling_results if "error" not in r]
        if len(valid_results) >= 2:
            # Check if memory scaling is reasonable (should be roughly linear)
            small_memory = next(
                (r["memory_delta_mb"] for r in valid_results if r["size"] == "small"), 0
            )
            large_memory = next(
                (r["memory_delta_mb"] for r in valid_results if r["size"] == "large"), 0
            )

            # Memory should not grow exponentially
            scaling_factor = large_memory / small_memory if small_memory > 0 else 0
            reasonable_scaling = (
                scaling_factor < 50
            )  # Less than 50x growth from small to large

            # None of the tests should exceed memory threshold
            memory_within_limits = all(
                r["final_memory_mb"] < self.thresholds["max_memory_mb"]
                for r in valid_results
            )

            success = reasonable_scaling and memory_within_limits
        else:
            success = False

        result = {
            "test_name": "memory_usage_scaling",
            "success": success,
            "details": {
                "scaling_results": scaling_results,
                "valid_tests": len(valid_results),
                "scaling_analysis": {
                    "reasonable_scaling": (
                        reasonable_scaling if len(valid_results) >= 2 else None
                    ),
                    "memory_within_limits": (
                        memory_within_limits if valid_results else False
                    ),
                    "scaling_factor": (
                        scaling_factor if len(valid_results) >= 2 else None
                    ),
                },
                "thresholds": {"max_memory_mb": self.thresholds["max_memory_mb"]},
            },
        }

        if success:
            print(
                f"✅ Memory scaling test passed - reasonable scaling with {len(valid_results)} sizes"
            )
        else:
            print("❌ Memory scaling test failed")
            if len(valid_results) >= 2:
                print(f"   Scaling factor: {scaling_factor:.1f}x")

        return result

    def test_error_recovery_scenarios(self) -> Dict[str, Any]:
        """Test various error scenarios and recovery mechanisms."""
        print("\n🚨 Testing Error Recovery Scenarios...")

        error_tests = []

        # Test 1: Invalid file path handling
        try:
            emitter = CodeTreeEventEmitter(use_stdout=True)
            emitter.start()

            # This should not crash the emitter
            emitter.emit_file_discovered("/nonexistent/path/file.py", "python", 0)
            emitter.emit_error("/nonexistent/path/file.py", "File not found")

            emitter.stop()

            error_tests.append(
                {
                    "test": "invalid_file_path_handling",
                    "success": True,  # Success if no exception thrown
                    "description": "Handled invalid file path without crashing",
                }
            )

        except Exception as e:
            error_tests.append(
                {
                    "test": "invalid_file_path_handling",
                    "success": False,
                    "error": str(e),
                }
            )

        # Test 2: Large node data handling
        try:
            emitter = CodeTreeEventEmitter(use_stdout=True)
            emitter.start()

            from claude_mpm.tools.code_tree_events import CodeNodeEvent

            # Create node with very large data
            large_node = CodeNodeEvent(
                file_path="test.py",
                node_type="function",
                name="x" * 1000,  # Very long name
                line_start=1,
                line_end=10000,  # Large line range
                complexity=999,
                decorators=["decorator"] * 100,  # Many decorators
            )

            emitter.emit_node(large_node)
            emitter.stop()

            error_tests.append(
                {
                    "test": "large_node_data_handling",
                    "success": True,
                    "description": "Handled large node data without issues",
                }
            )

        except Exception as e:
            error_tests.append(
                {"test": "large_node_data_handling", "success": False, "error": str(e)}
            )

        # Test 3: Normalizer error handling
        try:
            normalizer = EventNormalizer()

            # Test with various malformed inputs
            malformed_inputs = [
                None,
                {"type": None},
                {"type": ""},
                {"data": "not a dict"},
                123,  # Not a dict
                [],  # Not a dict
                {"type": "code:invalid:too:many:parts:here"},
            ]

            normalizer_failures = 0
            for malformed_input in malformed_inputs:
                try:
                    normalized = normalizer.normalize(malformed_input)
                    # Should return a valid normalized event even for bad input
                    if not hasattr(normalized, "type") or not hasattr(
                        normalized, "data"
                    ):
                        normalizer_failures += 1
                except Exception:
                    normalizer_failures += 1

            error_tests.append(
                {
                    "test": "normalizer_error_handling",
                    "success": normalizer_failures
                    < len(malformed_inputs) // 2,  # Should handle most inputs
                    "description": f"Handled {len(malformed_inputs) - normalizer_failures}/{len(malformed_inputs)} malformed inputs",
                    "failures": normalizer_failures,
                }
            )

        except Exception as e:
            error_tests.append(
                {"test": "normalizer_error_handling", "success": False, "error": str(e)}
            )

        # Test 4: Resource exhaustion simulation
        try:
            emitter = CodeTreeEventEmitter(
                use_stdout=False, batch_size=1000
            )  # Large batch
            emitter.start()

            # Generate many events quickly
            for i in range(10000):
                emitter.emit_progress(i, 10000, f"Processing {i}")

            emitter.stop()

            error_tests.append(
                {
                    "test": "resource_exhaustion_simulation",
                    "success": True,
                    "description": "Handled high event volume without crashing",
                }
            )

        except Exception as e:
            error_tests.append(
                {
                    "test": "resource_exhaustion_simulation",
                    "success": False,
                    "error": str(e),
                }
            )

        # Calculate overall success
        successful_tests = sum(1 for test in error_tests if test["success"])
        success = successful_tests >= len(error_tests) * 0.75  # 75% success threshold

        result = {
            "test_name": "error_recovery_scenarios",
            "success": success,
            "details": {
                "total_tests": len(error_tests),
                "successful_tests": successful_tests,
                "success_rate": (
                    successful_tests / len(error_tests) if error_tests else 0
                ),
                "test_results": error_tests,
            },
        }

        if success:
            print(
                f"✅ Error recovery test passed - {successful_tests}/{len(error_tests)} scenarios handled"
            )
        else:
            print(
                f"❌ Error recovery test failed - {successful_tests}/{len(error_tests)} scenarios handled"
            )

        return result

    def test_concurrent_processing(self) -> Dict[str, Any]:
        """Test concurrent analysis processing."""
        print("\n🔄 Testing Concurrent Processing...")

        try:
            # Create multiple test codebases
            test_dirs = []
            for _i in range(3):
                test_dir = self.create_test_codebase("small")
                test_dirs.append(test_dir)

            # Process them concurrently
            start_time = time.time()
            initial_memory = self.measure_memory_usage()

            def process_codebase(test_dir):
                """Process a single codebase."""
                emitter = CodeTreeEventEmitter(use_stdout=False)
                emitter.start()

                events_processed = 0
                for py_file in test_dir.glob("**/*.py"):
                    emitter.emit_file_discovered(
                        str(py_file), "python", py_file.stat().st_size
                    )
                    events_processed += 1

                    # Add some nodes
                    from claude_mpm.tools.code_tree_events import CodeNodeEvent

                    for j in range(3):
                        node = CodeNodeEvent(
                            file_path=str(py_file),
                            node_type="function",
                            name=f"func_{j}",
                            line_start=j * 10,
                            line_end=(j + 1) * 10,
                        )
                        emitter.emit_node(node)
                        events_processed += 1

                emitter.stop()
                return events_processed

            # Execute concurrently
            with ThreadPoolExecutor(max_workers=3) as executor:
                future_to_dir = {
                    executor.submit(process_codebase, test_dir): test_dir
                    for test_dir in test_dirs
                }
                results = []

                for future in as_completed(future_to_dir):
                    try:
                        events_processed = future.result()
                        results.append(events_processed)
                    except Exception as e:
                        results.append(f"Error: {e}")

            end_time = time.time()
            final_memory = self.measure_memory_usage()

            # Analyze results
            successful_runs = [r for r in results if isinstance(r, int)]
            total_events = sum(successful_runs)
            total_time = end_time - start_time
            concurrent_throughput = total_events / total_time if total_time > 0 else 0

            # Success criteria: All runs completed and reasonable performance
            success = (
                len(successful_runs) == len(test_dirs)
                and concurrent_throughput
                >= self.thresholds["min_throughput_eps"]
                * 0.5  # Lower threshold for concurrent
                and final_memory["rss_mb"] <= self.thresholds["max_memory_mb"]
            )

            result = {
                "test_name": "concurrent_processing",
                "success": success,
                "details": {
                    "concurrent_runs": len(test_dirs),
                    "successful_runs": len(successful_runs),
                    "total_events": total_events,
                    "total_time": round(total_time, 3),
                    "concurrent_throughput": round(concurrent_throughput, 2),
                    "memory_usage": {
                        "initial_mb": round(initial_memory["rss_mb"], 2),
                        "final_mb": round(final_memory["rss_mb"], 2),
                        "delta_mb": round(
                            final_memory["rss_mb"] - initial_memory["rss_mb"], 2
                        ),
                    },
                    "individual_results": results,
                },
            }

            if success:
                print(
                    f"✅ Concurrent processing test passed - {len(successful_runs)}/{len(test_dirs)} runs successful"
                )
            else:
                print(
                    f"❌ Concurrent processing test failed - {len(successful_runs)}/{len(test_dirs)} runs successful"
                )

        except Exception as e:
            result = {
                "test_name": "concurrent_processing",
                "success": False,
                "details": {"error": str(e)},
            }
        finally:
            # Cleanup test directories
            for test_dir in test_dirs:
                self.cleanup_test_codebase(test_dir)

        return result

    def run_performance_test_suite(self) -> Dict[str, Any]:
        """Run the complete performance and error testing suite."""
        print("⚡ Starting Performance and Error Testing Suite")
        print("=" * 60)

        suite_start_time = time.time()

        # Run performance tests
        test_methods = [
            lambda: self.test_event_throughput("small"),
            lambda: self.test_event_throughput("medium"),
            self.test_memory_usage_scaling,
            self.test_error_recovery_scenarios,
            self.test_concurrent_processing,
        ]

        test_results = []
        for test_method in test_methods:
            try:
                result = test_method()
                test_results.append(result)

                # Print individual results
                test_name = result.get("test_name", "unknown")
                if result.get("success", False):
                    print(f"✅ {test_name} PASSED")
                else:
                    print(f"❌ {test_name} FAILED")

            except Exception as e:
                error_result = {
                    "test_name": getattr(test_method, "__name__", "unknown"),
                    "success": False,
                    "details": {"error": str(e)},
                }
                test_results.append(error_result)
                print(f"💥 Test failed with exception: {e}")

        # Calculate overall results
        successful_tests = sum(
            1 for result in test_results if result.get("success", False)
        )
        suite_success = (
            successful_tests >= len(test_results) * 0.8
        )  # 80% success threshold

        # Gather overall performance metrics
        throughput_tests = [
            r for r in test_results if "throughput" in r.get("test_name", "")
        ]
        avg_throughput = 0
        if throughput_tests:
            throughputs = [
                r["details"].get("throughput_eps", 0)
                for r in throughput_tests
                if r.get("success")
            ]
            avg_throughput = sum(throughputs) / len(throughputs) if throughputs else 0

        memory_tests = [r for r in test_results if "memory" in r.get("test_name", "")]
        max_memory = 0
        if memory_tests:
            memory_values = []
            for r in memory_tests:
                if r.get("success") and "memory_usage" in r.get("details", {}):
                    memory_values.append(
                        r["details"]["memory_usage"].get("final_mb", 0)
                    )
            max_memory = max(memory_values) if memory_values else 0

        performance_summary = {
            "suite_success": suite_success,
            "total_tests": len(test_results),
            "successful_tests": successful_tests,
            "failed_tests": len(test_results) - successful_tests,
            "total_time": time.time() - suite_start_time,
            "performance_metrics": {
                "avg_throughput_eps": round(avg_throughput, 2),
                "max_memory_usage_mb": round(max_memory, 2),
                "thresholds_met": {
                    "throughput": avg_throughput
                    >= self.thresholds["min_throughput_eps"],
                    "memory": max_memory <= self.thresholds["max_memory_mb"],
                },
            },
            "test_results": test_results,
        }

        # Print summary
        print("\n" + "=" * 60)
        print("📊 PERFORMANCE TEST SUMMARY")
        print("=" * 60)
        print(f"Overall Result: {'✅ PASSED' if suite_success else '❌ FAILED'}")
        print(f"Tests Passed: {successful_tests}/{len(test_results)}")
        print(f"Avg Throughput: {avg_throughput:.1f} events/sec")
        print(f"Max Memory Usage: {max_memory:.1f} MB")
        print(f"Total Time: {performance_summary['total_time']:.2f}s")

        return performance_summary


def main():
    """Main performance test function."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Performance and Error Testing for Code Analysis"
    )
    parser.add_argument(
        "--save-results", action="store_true", help="Save results to JSON file"
    )
    args = parser.parse_args()

    print("⚡ Performance and Error Testing for Code Analysis Dashboard")
    print("Testing system performance and error handling under various conditions\n")

    # Run performance test suite
    tester = CodeAnalysisPerformanceTest()
    results = tester.run_performance_test_suite()

    # Save results if requested
    if args.save_results:
        results_file = Path("test_results_performance.json")
        with results_file.open("w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\n📁 Performance test results saved to: {results_file}")

    # Exit with appropriate code
    exit_code = 0 if results.get("suite_success", False) else 1
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
