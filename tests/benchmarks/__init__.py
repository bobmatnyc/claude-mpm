"""
Claude MPM Performance Benchmarks
=================================

This module contains comprehensive performance benchmarks for validating
TSK-0056 performance optimization targets.

Benchmark Categories:
- Startup Performance: Application launch time optimization
- Agent Deployment: Agent loading and deployment speed
- Memory Operations: Memory query and search performance
- Cache Effectiveness: File operation caching improvements
- Connection Pool: Socket.IO connection reliability

Usage:
    from tests.benchmarks import PerformanceBenchmarks

    benchmarks = PerformanceBenchmarks()
    suite = await benchmarks.run_all_benchmarks()
"""

from .performance_validation_suite import (
    BenchmarkResult,
    BenchmarkSuite,
    PerformanceBenchmarks,
    PerformanceTarget,
)

__all__ = [
    "PerformanceBenchmarks",
    "PerformanceTarget",
    "BenchmarkResult",
    "BenchmarkSuite",
]
