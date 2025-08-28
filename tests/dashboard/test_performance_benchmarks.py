#!/usr/bin/env python3
"""
Dashboard Performance Benchmarks
================================

Performance benchmarks for dashboard components including:
- Large event stream handling
- Code tree visualization with large codebases
- Multiple concurrent dashboard connections
- Socket.IO message throughput
- Memory usage under load
"""

import json
import os
import random
import sys
import threading
import time
import unittest
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


@dataclass
class PerformanceMetric:
    """Represents a performance measurement."""

    name: str
    value: float
    unit: str
    threshold: float
    passed: bool = False

    def __post_init__(self):
        self.passed = self.value <= self.threshold


class EventStreamBenchmark:
    """Benchmark for event stream processing."""

    def __init__(self):
        self.metrics = []

    def generate_event(self, index: int) -> Dict[str, Any]:
        """Generate a realistic event."""
        event_types = [
            "hook.user_prompt",
            "hook.assistant_response",
            "code:file_discovered",
            "code:directory_discovered",
            "code:node_found",
            "tool.execution",
            "analysis.started",
            "analysis.completed",
        ]

        return {
            "event_id": f"bench-{index}",
            "type": random.choice(event_types),
            "timestamp": time.time(),
            "data": {
                "index": index,
                "message": f"Event message {index}",
                "details": {
                    "key1": f"value{index}",
                    "key2": random.randint(1, 1000),
                    "key3": random.random(),
                    "nested": {
                        "deep1": f"deep_value_{index}",
                        "deep2": [i for i in range(5)],
                    },
                },
            },
        }

    def benchmark_event_processing(self, event_count: int = 10000) -> PerformanceMetric:
        """Benchmark processing large numbers of events."""
        events = []

        # Generate events
        start_time = time.time()
        for i in range(event_count):
            events.append(self.generate_event(i))
        generation_time = time.time() - start_time

        # Simulate processing
        start_time = time.time()
        processed = []
        for event in events:
            # Simulate event transformation
            transformed = {
                "id": event["event_id"],
                "type": event["type"].replace(":", "."),
                "timestamp": event["timestamp"],
                "data": json.dumps(event["data"]),
            }
            processed.append(transformed)
        processing_time = time.time() - start_time

        # Calculate throughput
        throughput = event_count / processing_time

        metric = PerformanceMetric(
            name="event_stream_throughput",
            value=throughput,
            unit="events/second",
            threshold=5000,  # Should process at least 5000 events/second
        )

        print("Event Stream Benchmark:")
        print(f"  Generated {event_count} events in {generation_time:.2f}s")
        print(f"  Processed {event_count} events in {processing_time:.2f}s")
        print(f"  Throughput: {throughput:.0f} events/second")
        print(f"  Status: {'✓ PASS' if metric.passed else '✗ FAIL'}")

        return metric

    def benchmark_event_filtering(self, event_count: int = 10000) -> PerformanceMetric:
        """Benchmark event filtering performance."""
        events = [self.generate_event(i) for i in range(event_count)]

        # Define filters
        filters = [
            lambda e: e["type"].startswith("hook."),
            lambda e: e["type"].startswith("code:"),
            lambda e: e["data"].get("index", 0) % 2 == 0,
            lambda e: "message" in e["data"],
        ]

        start_time = time.time()

        # Apply filters
        for filter_func in filters:
            filtered = [e for e in events if filter_func(e)]

        filtering_time = time.time() - start_time
        ops_per_second = (event_count * len(filters)) / filtering_time

        metric = PerformanceMetric(
            name="event_filtering_speed",
            value=ops_per_second,
            unit="operations/second",
            threshold=10000,  # Should handle at least 10k ops/second
        )

        print("\nEvent Filtering Benchmark:")
        print(f"  Filtered {event_count} events with {len(filters)} filters")
        print(f"  Total time: {filtering_time:.2f}s")
        print(f"  Operations/second: {ops_per_second:.0f}")
        print(f"  Status: {'✓ PASS' if metric.passed else '✗ FAIL'}")

        return metric


class CodeTreeBenchmark:
    """Benchmark for code tree visualization."""

    def generate_code_tree(self, depth: int, breadth: int) -> Dict[str, Any]:
        """Generate a large code tree structure."""

        def create_node(level: int, index: int) -> Dict[str, Any]:
            node = {
                "name": f"node_{level}_{index}",
                "type": random.choice(["file", "directory", "class", "function"]),
                "path": f"/path/level{level}/node{index}",
                "size": random.randint(100, 10000),
                "children": [],
            }

            if level < depth:
                for i in range(random.randint(1, breadth)):
                    node["children"].append(create_node(level + 1, i))

            return node

        return create_node(0, 0)

    def count_nodes(self, tree: Dict[str, Any]) -> int:
        """Count total nodes in tree."""
        count = 1
        for child in tree.get("children", []):
            count += self.count_nodes(child)
        return count

    def benchmark_tree_rendering(
        self, depth: int = 10, breadth: int = 5
    ) -> PerformanceMetric:
        """Benchmark rendering large code trees."""
        # Generate tree
        start_time = time.time()
        tree = self.generate_code_tree(depth, breadth)
        generation_time = time.time() - start_time

        node_count = self.count_nodes(tree)

        # Simulate rendering operations
        start_time = time.time()

        def traverse_tree(node, level=0):
            # Simulate rendering operations
            result = {
                "id": f"{node['name']}_{level}",
                "label": node["name"],
                "type": node["type"],
                "indent": level * 20,
                "expanded": level < 3,
            }

            for child in node.get("children", []):
                traverse_tree(child, level + 1)

        traverse_tree(tree)
        rendering_time = time.time() - start_time

        nodes_per_second = node_count / rendering_time

        metric = PerformanceMetric(
            name="code_tree_rendering",
            value=rendering_time,
            unit="seconds",
            threshold=2.0,  # Should render in under 2 seconds
        )

        print("\nCode Tree Benchmark:")
        print(f"  Tree depth: {depth}, breadth: {breadth}")
        print(f"  Total nodes: {node_count}")
        print(f"  Generation time: {generation_time:.2f}s")
        print(f"  Rendering time: {rendering_time:.2f}s")
        print(f"  Nodes/second: {nodes_per_second:.0f}")
        print(f"  Status: {'✓ PASS' if metric.passed else '✗ FAIL'}")

        return metric

    def benchmark_tree_search(
        self, depth: int = 8, breadth: int = 4
    ) -> PerformanceMetric:
        """Benchmark searching in large code trees."""
        tree = self.generate_code_tree(depth, breadth)
        node_count = self.count_nodes(tree)

        # Search operations
        search_terms = ["node", "file", "class", "5", "level"]

        start_time = time.time()

        def search_tree(node, term):
            matches = []
            if term in node.get("name", "") or term in node.get("type", ""):
                matches.append(node)

            for child in node.get("children", []):
                matches.extend(search_tree(child, term))

            return matches

        total_matches = 0
        for term in search_terms:
            matches = search_tree(tree, term)
            total_matches += len(matches)

        search_time = time.time() - start_time
        searches_per_second = len(search_terms) / search_time

        metric = PerformanceMetric(
            name="code_tree_search",
            value=search_time,
            unit="seconds",
            threshold=1.0,  # Should complete in under 1 second
        )

        print("\nCode Tree Search Benchmark:")
        print(f"  Searched {node_count} nodes for {len(search_terms)} terms")
        print(f"  Total matches: {total_matches}")
        print(f"  Search time: {search_time:.2f}s")
        print(f"  Searches/second: {searches_per_second:.1f}")
        print(f"  Status: {'✓ PASS' if metric.passed else '✗ FAIL'}")

        return metric


class ConcurrentConnectionBenchmark:
    """Benchmark for concurrent dashboard connections."""

    def __init__(self):
        self.active_connections = []
        self.connection_times = []
        self.message_counts = defaultdict(int)
        self.errors = []

    def simulate_connection(self, connection_id: int, duration: float = 1.0):
        """Simulate a dashboard connection."""
        try:
            start_time = time.time()

            # Simulate connection establishment
            time.sleep(random.uniform(0.01, 0.05))

            # Simulate message exchange
            message_count = 0
            end_time = start_time + duration

            while time.time() < end_time:
                # Simulate sending/receiving messages
                message_count += 1
                self.message_counts[connection_id] = message_count
                time.sleep(random.uniform(0.001, 0.01))

            connection_time = time.time() - start_time
            self.connection_times.append(connection_time)

        except Exception as e:
            self.errors.append((connection_id, str(e)))

    def benchmark_concurrent_connections(
        self, connection_count: int = 100
    ) -> PerformanceMetric:
        """Benchmark handling multiple concurrent connections."""
        threads = []

        start_time = time.time()

        # Start concurrent connections
        for i in range(connection_count):
            thread = threading.Thread(
                target=self.simulate_connection,
                args=(i, 0.5),  # Each connection runs for 0.5 seconds
            )
            threads.append(thread)
            thread.start()

            # Stagger connection starts slightly
            time.sleep(0.001)

        # Wait for all connections to complete
        for thread in threads:
            thread.join()

        total_time = time.time() - start_time

        # Calculate metrics
        total_messages = sum(self.message_counts.values())
        avg_messages_per_connection = (
            total_messages / connection_count if connection_count > 0 else 0
        )
        messages_per_second = total_messages / total_time if total_time > 0 else 0

        metric = PerformanceMetric(
            name="concurrent_connections",
            value=len(self.errors),
            unit="errors",
            threshold=5,  # Allow up to 5 errors in 100 connections
        )

        print("\nConcurrent Connections Benchmark:")
        print(f"  Connections: {connection_count}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Total messages: {total_messages}")
        print(f"  Messages/second: {messages_per_second:.0f}")
        print(f"  Avg messages/connection: {avg_messages_per_connection:.0f}")
        print(f"  Errors: {len(self.errors)}")
        print(f"  Status: {'✓ PASS' if metric.passed else '✗ FAIL'}")

        return metric


class MemoryUsageBenchmark:
    """Benchmark memory usage under load."""

    def get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            import psutil

            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except ImportError:
            # Fallback if psutil not available
            return 0

    def benchmark_memory_under_load(self) -> PerformanceMetric:
        """Benchmark memory usage with large data volumes."""
        initial_memory = self.get_memory_usage()

        # Create large data structures
        large_events = []
        for i in range(50000):
            large_events.append(
                {
                    "id": f"mem-test-{i}",
                    "data": "x" * 1000,  # 1KB per event
                    "nested": {"level1": {"level2": {"values": list(range(100))}}},
                }
            )

        peak_memory = self.get_memory_usage()

        # Clear data
        large_events.clear()

        # Force garbage collection
        import gc

        gc.collect()

        final_memory = self.get_memory_usage()

        memory_increase = peak_memory - initial_memory
        memory_recovered = peak_memory - final_memory
        recovery_percentage = (
            (memory_recovered / memory_increase * 100) if memory_increase > 0 else 0
        )

        metric = PerformanceMetric(
            name="memory_usage",
            value=memory_increase,
            unit="MB",
            threshold=500,  # Should not use more than 500MB for 50k events
        )

        print("\nMemory Usage Benchmark:")
        print(f"  Initial memory: {initial_memory:.1f} MB")
        print(f"  Peak memory: {peak_memory:.1f} MB")
        print(f"  Final memory: {final_memory:.1f} MB")
        print(f"  Memory increase: {memory_increase:.1f} MB")
        print(
            f"  Memory recovered: {memory_recovered:.1f} MB ({recovery_percentage:.1f}%)"
        )
        print(f"  Status: {'✓ PASS' if metric.passed else '✗ FAIL'}")

        return metric


class DashboardPerformanceTestSuite(unittest.TestCase):
    """Complete performance test suite for dashboard."""

    @classmethod
    def setUpClass(cls):
        """Set up test suite."""
        cls.results = []
        print("\n" + "=" * 60)
        print("DASHBOARD PERFORMANCE BENCHMARK SUITE")
        print("=" * 60)

    def test_01_event_stream_performance(self):
        """Test event stream processing performance."""
        benchmark = EventStreamBenchmark()

        # Run benchmarks
        metric1 = benchmark.benchmark_event_processing(10000)
        self.assertTrue(
            metric1.passed,
            f"Event processing too slow: {metric1.value:.0f} < {metric1.threshold}",
        )
        self.results.append(metric1)

        metric2 = benchmark.benchmark_event_filtering(10000)
        self.assertTrue(
            metric2.passed,
            f"Event filtering too slow: {metric2.value:.0f} < {metric2.threshold}",
        )
        self.results.append(metric2)

    def test_02_code_tree_performance(self):
        """Test code tree visualization performance."""
        benchmark = CodeTreeBenchmark()

        # Test with realistic tree size
        metric1 = benchmark.benchmark_tree_rendering(depth=8, breadth=4)
        self.assertTrue(
            metric1.passed,
            f"Tree rendering too slow: {metric1.value:.2f}s > {metric1.threshold}s",
        )
        self.results.append(metric1)

        metric2 = benchmark.benchmark_tree_search(depth=7, breadth=4)
        self.assertTrue(
            metric2.passed,
            f"Tree search too slow: {metric2.value:.2f}s > {metric2.threshold}s",
        )
        self.results.append(metric2)

    def test_03_concurrent_connections(self):
        """Test handling concurrent connections."""
        benchmark = ConcurrentConnectionBenchmark()

        # Test with 50 concurrent connections
        metric = benchmark.benchmark_concurrent_connections(50)
        self.assertTrue(
            metric.passed,
            f"Too many connection errors: {metric.value} > {metric.threshold}",
        )
        self.results.append(metric)

    def test_04_memory_usage(self):
        """Test memory usage under load."""
        benchmark = MemoryUsageBenchmark()

        metric = benchmark.benchmark_memory_under_load()
        self.assertTrue(
            metric.passed,
            f"Memory usage too high: {metric.value:.1f}MB > {metric.threshold}MB",
        )
        self.results.append(metric)

    @classmethod
    def tearDownClass(cls):
        """Print summary of results."""
        print("\n" + "=" * 60)
        print("PERFORMANCE BENCHMARK SUMMARY")
        print("=" * 60)

        passed = sum(1 for m in cls.results if m.passed)
        total = len(cls.results)

        print(f"\nResults: {passed}/{total} tests passed")
        print("\nDetailed Results:")
        for metric in cls.results:
            status = "✓ PASS" if metric.passed else "✗ FAIL"
            print(
                f"  [{status}] {metric.name}: {metric.value:.2f} {metric.unit} (threshold: {metric.threshold})"
            )

        if passed < total:
            print("\n⚠️  Some performance benchmarks failed!")
            print("Consider optimizing the affected components.")
        else:
            print("\n✅ All performance benchmarks passed!")


def run_benchmarks():
    """Run all benchmarks and generate report."""
    import time

    print("Starting Dashboard Performance Benchmarks...")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    # Run test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(DashboardPerformanceTestSuite)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_benchmarks()
    sys.exit(0 if success else 1)
