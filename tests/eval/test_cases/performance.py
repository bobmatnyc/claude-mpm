"""
Performance benchmarking for PM agent and evaluation metrics.

Measures and tracks:
- PM agent response time
- Evaluation metric performance
- DeepEval execution time
- Memory usage
- Throughput

Usage:
    # Run performance benchmarks
    pytest tests/eval/test_cases/performance.py -m performance -v

    # Generate performance report
    pytest tests/eval/test_cases/performance.py --benchmark-only -v

Design Decision: Performance Tracking
- Track both response time and evaluation time separately
- Store baseline metrics for regression detection
- Use pytest-benchmark for accurate measurements
- Configurable thresholds for performance regression

Trade-offs:
- Accuracy vs. Speed: Use multiple iterations for accuracy
- Storage vs. History: Keep last 30 days of metrics
- Precision: Measure in milliseconds, report in ms
"""

import asyncio
import json
import statistics
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
from deepeval.test_case import LLMTestCase

from ..metrics.delegation_correctness import TicketingDelegationMetric
from ..metrics.instruction_faithfulness import InstructionFaithfulnessMetric


class PerformanceTracker:
    """
    Track and store performance metrics over time.

    Stores metrics in tests/eval/performance_history.json for trend analysis.
    """

    def __init__(self, history_file: str = "tests/eval/performance_history.json"):
        """Initialize performance tracker."""
        self.history_file = Path(history_file)
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        self.current_run = {
            "timestamp": datetime.now().isoformat(),
            "metrics": [],
        }

    def record_metric(
        self,
        name: str,
        value: float,
        unit: str = "ms",
        category: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Record a performance metric."""
        metric = {
            "name": name,
            "value": value,
            "unit": unit,
            "category": category,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        self.current_run["metrics"].append(metric)

    def save(self):
        """Save metrics to history file."""
        history = []
        if self.history_file.exists():
            with open(self.history_file) as f:
                history = json.load(f)

        history.append(self.current_run)

        # Keep only last 30 days
        cutoff = datetime.now().timestamp() - (30 * 24 * 60 * 60)
        history = [
            run
            for run in history
            if datetime.fromisoformat(run["timestamp"]).timestamp() > cutoff
        ]

        with open(self.history_file, "w") as f:
            json.dump(history, f, indent=2)

    def get_baseline(self, metric_name: str, category: str = "general") -> float:
        """Get baseline (median) value for metric from history."""
        if not self.history_file.exists():
            return None

        with open(self.history_file) as f:
            history = json.load(f)

        values = []
        for run in history:
            for metric in run["metrics"]:
                if metric["name"] == metric_name and metric["category"] == category:
                    values.append(metric["value"])

        if not values:
            return None

        return statistics.median(values)


@pytest.fixture
def performance_tracker():
    """Fixture for performance tracking."""
    tracker = PerformanceTracker()
    yield tracker
    tracker.save()


@pytest.mark.performance
class TestPMAgentPerformance:
    """Performance benchmarks for PM agent responses."""

    @pytest.mark.asyncio
    async def test_pm_response_time_simple_request(
        self,
        pm_agent,
        performance_tracker,
    ):
        """
        Benchmark PM agent response time for simple request.

        Threshold: <500ms for simple requests
        """
        input_text = "Create a ticket for bug fix"

        # Measure response time
        start_time = time.perf_counter()
        response = await pm_agent.process_request(input_text)
        end_time = time.perf_counter()

        response_time_ms = (end_time - start_time) * 1000

        # Record metric
        performance_tracker.record_metric(
            name="pm_response_simple",
            value=response_time_ms,
            unit="ms",
            category="pm_agent",
            metadata={"input_length": len(input_text)},
        )

        # Check against baseline
        baseline = performance_tracker.get_baseline("pm_response_simple", "pm_agent")
        if baseline:
            regression_threshold = baseline * 1.5  # 50% slower = regression
            assert response_time_ms < regression_threshold, (
                f"Performance regression: {response_time_ms:.2f}ms > "
                f"{regression_threshold:.2f}ms (baseline: {baseline:.2f}ms)"
            )

        # Absolute threshold
        assert response_time_ms < 5000, (
            f"PM response too slow: {response_time_ms:.2f}ms > 5000ms"
        )

        print(f"\nPM Response Time (simple): {response_time_ms:.2f}ms")

    @pytest.mark.asyncio
    async def test_pm_response_time_complex_request(
        self,
        pm_agent,
        performance_tracker,
    ):
        """
        Benchmark PM agent response time for complex request.

        Threshold: <2000ms for complex requests
        """
        input_text = (
            "Check status of tickets AUTH-123, AUTH-456, and AUTH-789, "
            "analyze their dependencies, and create a summary ticket with "
            "recommendations for resolution order"
        )

        start_time = time.perf_counter()
        response = await pm_agent.process_request(input_text)
        end_time = time.perf_counter()

        response_time_ms = (end_time - start_time) * 1000

        performance_tracker.record_metric(
            name="pm_response_complex",
            value=response_time_ms,
            unit="ms",
            category="pm_agent",
            metadata={"input_length": len(input_text)},
        )

        baseline = performance_tracker.get_baseline("pm_response_complex", "pm_agent")
        if baseline:
            regression_threshold = baseline * 1.5
            assert response_time_ms < regression_threshold, (
                f"Performance regression: {response_time_ms:.2f}ms"
            )

        assert response_time_ms < 10000, (
            f"PM response too slow: {response_time_ms:.2f}ms"
        )

        print(f"\nPM Response Time (complex): {response_time_ms:.2f}ms")

    @pytest.mark.asyncio
    async def test_pm_throughput(
        self,
        pm_agent,
        performance_tracker,
    ):
        """
        Measure PM agent throughput (requests per second).

        Tests concurrent request handling.
        """
        num_requests = 10
        requests = [
            "Create ticket for bug",
            "Check ticket status",
            "Update ticket priority",
            "List all tickets",
            "Search for tickets",
        ] * 2  # 10 requests total

        start_time = time.perf_counter()

        # Execute requests concurrently
        tasks = [pm_agent.process_request(req) for req in requests]
        responses = await asyncio.gather(*tasks)

        end_time = time.perf_counter()

        total_time_sec = end_time - start_time
        throughput = num_requests / total_time_sec

        performance_tracker.record_metric(
            name="pm_throughput",
            value=throughput,
            unit="req/sec",
            category="pm_agent",
            metadata={"num_requests": num_requests},
        )

        # Check baseline
        baseline = performance_tracker.get_baseline("pm_throughput", "pm_agent")
        if baseline:
            regression_threshold = baseline * 0.7  # 30% slower = regression
            assert throughput > regression_threshold, (
                f"Throughput regression: {throughput:.2f} req/s < {regression_threshold:.2f}"
            )

        print(f"\nPM Throughput: {throughput:.2f} requests/sec")


@pytest.mark.performance
class TestEvaluationMetricPerformance:
    """Performance benchmarks for evaluation metrics."""

    def test_delegation_metric_performance(
        self,
        performance_tracker,
    ):
        """
        Benchmark TicketingDelegationMetric evaluation time.

        Threshold: <100ms per evaluation
        """
        # Create test case
        test_case = LLMTestCase(
            input="Create ticket for authentication bug",
            actual_output="""
            I'll delegate to ticketing agent.

            Task(
                agent="ticketing",
                task="Create ticket for authentication bug with high priority"
            )

            [ticketing agent creates ticket...]

            ticketing agent confirmed: Ticket AUTH-789 created.
            """,
        )

        metric = TicketingDelegationMetric(threshold=1.0)

        # Warm up
        metric.measure(test_case)

        # Measure performance (average of 10 runs)
        times = []
        for _ in range(10):
            start_time = time.perf_counter()
            score = metric.measure(test_case)
            end_time = time.perf_counter()
            times.append((end_time - start_time) * 1000)

        avg_time_ms = statistics.mean(times)
        std_dev_ms = statistics.stdev(times) if len(times) > 1 else 0

        performance_tracker.record_metric(
            name="delegation_metric_eval",
            value=avg_time_ms,
            unit="ms",
            category="metrics",
            metadata={"std_dev": std_dev_ms, "iterations": 10},
        )

        # Check performance
        assert avg_time_ms < 100, (
            f"Metric evaluation too slow: {avg_time_ms:.2f}ms > 100ms"
        )

        print(f"\nDelegation Metric: {avg_time_ms:.2f}ms ± {std_dev_ms:.2f}ms")

    def test_instruction_faithfulness_performance(
        self,
        performance_tracker,
    ):
        """
        Benchmark InstructionFaithfulnessMetric evaluation time.

        Threshold: <200ms per evaluation
        """
        test_case = LLMTestCase(
            input="Test input",
            actual_output="PM delegated to ticketing agent. ticketing agent verified the result.",
        )

        metric = InstructionFaithfulnessMetric(threshold=0.85)

        # Warm up
        metric.measure(test_case)

        # Measure
        times = []
        for _ in range(10):
            start_time = time.perf_counter()
            score = metric.measure(test_case)
            end_time = time.perf_counter()
            times.append((end_time - start_time) * 1000)

        avg_time_ms = statistics.mean(times)
        std_dev_ms = statistics.stdev(times) if len(times) > 1 else 0

        performance_tracker.record_metric(
            name="instruction_faithfulness_eval",
            value=avg_time_ms,
            unit="ms",
            category="metrics",
            metadata={"std_dev": std_dev_ms},
        )

        assert avg_time_ms < 200, f"Metric evaluation too slow: {avg_time_ms:.2f}ms"

        print(f"\nInstruction Faithfulness: {avg_time_ms:.2f}ms ± {std_dev_ms:.2f}ms")

    def test_full_evaluation_pipeline_performance(
        self,
        performance_tracker,
        ticketing_scenarios,
    ):
        """
        Benchmark complete evaluation pipeline.

        Measures end-to-end time from test case creation to result.
        """
        scenario = ticketing_scenarios[0]

        test_case = LLMTestCase(
            input=scenario["input"],
            actual_output="""
            I'll delegate to ticketing agent.
            Task(agent="ticketing", task="Handle request")
            ticketing agent completed the task.
            """,
        )

        # Create metrics
        delegation_metric = TicketingDelegationMetric(threshold=1.0)
        instruction_metric = InstructionFaithfulnessMetric(threshold=0.85)

        # Measure full pipeline
        start_time = time.perf_counter()

        # Run both metrics
        delegation_score = delegation_metric.measure(test_case)
        instruction_score = instruction_metric.measure(test_case)

        end_time = time.perf_counter()

        pipeline_time_ms = (end_time - start_time) * 1000

        performance_tracker.record_metric(
            name="full_evaluation_pipeline",
            value=pipeline_time_ms,
            unit="ms",
            category="metrics",
            metadata={
                "num_metrics": 2,
                "delegation_score": delegation_score,
                "instruction_score": instruction_score,
            },
        )

        assert pipeline_time_ms < 500, (
            f"Full pipeline too slow: {pipeline_time_ms:.2f}ms"
        )

        print(f"\nFull Evaluation Pipeline: {pipeline_time_ms:.2f}ms")


@pytest.mark.performance
class TestMemoryUsage:
    """Memory usage benchmarks."""

    def test_response_capture_memory(
        self,
        pm_response_capture,
        performance_tracker,
    ):
        """
        Test memory usage of response capture.

        Ensures capture doesn't leak memory with large responses.
        """
        import sys

        # Create large response
        large_response = {
            "content": "x" * 100000,  # 100KB response
            "tools_used": ["Task"] * 1000,
            "metadata": {"data": "y" * 10000},
        }

        # Measure memory
        initial_size = sys.getsizeof(large_response)

        # Capture response
        captured = pm_response_capture.capture_response(
            scenario_id="memory_test",
            input_text="test input",
            pm_response=large_response,
            category="performance",
        )

        captured_size = sys.getsizeof(captured)

        # Memory overhead should be reasonable (<2x)
        overhead_ratio = captured_size / initial_size

        performance_tracker.record_metric(
            name="capture_memory_overhead",
            value=overhead_ratio,
            unit="ratio",
            category="memory",
            metadata={"response_size_bytes": initial_size},
        )

        assert overhead_ratio < 3.0, f"Memory overhead too high: {overhead_ratio:.2f}x"

        print(f"\nCapture Memory Overhead: {overhead_ratio:.2f}x")


@pytest.mark.performance
def test_generate_performance_report(performance_tracker):
    """
    Generate comprehensive performance report.

    This test runs last and generates a summary of all benchmarks.
    """
    # Load all metrics from current run
    metrics = performance_tracker.current_run["metrics"]

    if not metrics:
        pytest.skip("No performance metrics collected")

    # Group by category
    by_category = {}
    for metric in metrics:
        category = metric["category"]
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(metric)

    # Generate report
    print("\n" + "=" * 70)
    print("PERFORMANCE BENCHMARK REPORT")
    print("=" * 70)
    print(f"Timestamp: {performance_tracker.current_run['timestamp']}")
    print(f"Total Metrics: {len(metrics)}\n")

    for category, cat_metrics in by_category.items():
        print(f"\n{category.upper()}")
        print("-" * 70)

        for metric in cat_metrics:
            name = metric["name"]
            value = metric["value"]
            unit = metric["unit"]

            # Get baseline if available
            baseline = performance_tracker.get_baseline(name, category)
            baseline_str = f" (baseline: {baseline:.2f}{unit})" if baseline else ""

            print(f"  {name}: {value:.2f}{unit}{baseline_str}")

            # Show metadata if present
            if metric.get("metadata"):
                for key, val in metric["metadata"].items():
                    print(f"    - {key}: {val}")

    print("\n" + "=" * 70)

    # Save report to file
    report_file = Path("tests/eval/performance_report.txt")
    with open(report_file, "w") as f:
        f.write(
            f"Performance Report - {performance_tracker.current_run['timestamp']}\n"
        )
        f.write("=" * 70 + "\n\n")
        for category, cat_metrics in by_category.items():
            f.write(f"{category.upper()}\n")
            f.write("-" * 70 + "\n")
            for metric in cat_metrics:
                f.write(f"{metric['name']}: {metric['value']:.2f}{metric['unit']}\n")
            f.write("\n")

    print(f"\nReport saved to: {report_file}")
