#!/usr/bin/env python3
"""
Startup Performance Benchmark
=============================

Dedicated benchmark for measuring startup performance across different modes:
- Oneshot mode (single command execution)
- Interactive mode (session preparation)
- Agent deployment startup impact
- Memory initialization impact

Target: <2 seconds startup time (from baseline 3-5 seconds)
"""

import asyncio
import json
import os
import subprocess
import sys
import time
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import argparse
import logging
import statistics
import psutil
from datetime import datetime


@dataclass
class StartupMeasurement:
    """Individual startup measurement."""
    mode: str
    time_seconds: float
    memory_mb: float
    cpu_percent: float
    success: bool
    error_message: Optional[str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat() + "Z"


class StartupBenchmark:
    """Comprehensive startup performance benchmark."""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.project_root = Path(__file__).parent.parent.parent
        self.claude_mpm_script = self.project_root / "scripts" / "claude-mpm"
        
        if not self.claude_mpm_script.exists():
            raise FileNotFoundError(f"claude-mpm script not found at {self.claude_mpm_script}")
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for startup benchmarks."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        return logging.getLogger("startup_benchmark")
    
    def measure_process_startup(self, command: List[str], timeout: int = 15) -> StartupMeasurement:
        """Measure startup time and resource usage for a command."""
        mode = " ".join(command[1:3]) if len(command) > 2 else "unknown"
        
        self.logger.debug(f"Measuring startup for: {' '.join(command)}")
        
        start_time = time.time()
        initial_memory = psutil.virtual_memory().used
        
        try:
            # Start process and monitor it
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={**os.environ, "PYTHONPATH": str(self.project_root / "src")}
            )
            
            # Monitor process until completion
            stdout, stderr = process.communicate(timeout=timeout)
            
            end_time = time.time()
            final_memory = psutil.virtual_memory().used
            
            startup_time = end_time - start_time
            memory_delta = (final_memory - initial_memory) / (1024 * 1024)  # MB
            
            success = process.returncode == 0
            error_msg = stderr.strip() if stderr and not success else None
            
            return StartupMeasurement(
                mode=mode,
                time_seconds=startup_time,
                memory_mb=max(0, memory_delta),  # Avoid negative values
                cpu_percent=0.0,  # Hard to measure for short processes
                success=success,
                error_message=error_msg
            )
            
        except subprocess.TimeoutExpired:
            self.logger.warning(f"Command timed out: {' '.join(command)}")
            try:
                process.kill()
                process.wait(timeout=5)
            except:
                pass
            
            return StartupMeasurement(
                mode=mode,
                time_seconds=timeout,
                memory_mb=0.0,
                cpu_percent=0.0,
                success=False,
                error_message="Process timed out"
            )
        except Exception as e:
            self.logger.error(f"Error measuring startup: {e}")
            return StartupMeasurement(
                mode=mode,
                time_seconds=0.0,
                memory_mb=0.0,
                cpu_percent=0.0,
                success=False,
                error_message=str(e)
            )
    
    def benchmark_oneshot_commands(self, samples: int = 5) -> List[StartupMeasurement]:
        """Benchmark oneshot command performance."""
        self.logger.info("🚀 Benchmarking oneshot command startup...")
        
        commands = [
            ["info", "--version"],
            ["info", "--system"],
            ["agents", "list"],
            ["tickets", "list", "--limit", "5"],
            ["memory", "list", "--limit", "5"]
        ]
        
        measurements = []
        
        for cmd in commands:
            self.logger.info(f"  Testing command: {' '.join(cmd)}")
            
            for i in range(samples):
                full_command = [str(self.claude_mpm_script)] + cmd
                measurement = self.measure_process_startup(full_command)
                measurements.append(measurement)
                
                if measurement.success:
                    self.logger.debug(f"    Sample {i+1}: {measurement.time_seconds:.3f}s")
                else:
                    self.logger.warning(f"    Sample {i+1}: FAILED - {measurement.error_message}")
        
        return measurements
    
    def benchmark_interactive_preparation(self, samples: int = 5) -> List[StartupMeasurement]:
        """Benchmark interactive mode preparation."""
        self.logger.info("🎮 Benchmarking interactive mode preparation...")
        
        measurements = []
        
        for i in range(samples):
            self.logger.info(f"  Testing interactive preparation {i+1}/{samples}")
            
            # Use non-interactive mode with quick exit to test startup preparation
            command = [
                str(self.claude_mpm_script),
                "run",
                "--non-interactive",
                "--input", "exit"
            ]
            
            measurement = self.measure_process_startup(command, timeout=20)
            measurements.append(measurement)
            
            if measurement.success:
                self.logger.debug(f"    Interactive prep {i+1}: {measurement.time_seconds:.3f}s")
            else:
                self.logger.warning(f"    Interactive prep {i+1}: FAILED - {measurement.error_message}")
        
        return measurements
    
    def benchmark_agent_deployment_impact(self, samples: int = 3) -> List[StartupMeasurement]:
        """Benchmark startup with agent deployment."""
        self.logger.info("🤖 Benchmarking startup with agent deployment...")
        
        measurements = []
        
        for i in range(samples):
            self.logger.info(f"  Testing agent deployment startup {i+1}/{samples}")
            
            # Test agent deployment command startup time
            command = [
                str(self.claude_mpm_script),
                "agents",
                "deploy",
                "--quiet"
            ]
            
            measurement = self.measure_process_startup(command, timeout=30)
            measurements.append(measurement)
            
            if measurement.success:
                self.logger.debug(f"    Agent deployment {i+1}: {measurement.time_seconds:.3f}s")
            else:
                self.logger.warning(f"    Agent deployment {i+1}: FAILED - {measurement.error_message}")
        
        return measurements
    
    def benchmark_memory_initialization_impact(self, samples: int = 3) -> List[StartupMeasurement]:
        """Benchmark startup with memory system initialization."""
        self.logger.info("🧠 Benchmarking startup with memory initialization...")
        
        measurements = []
        
        for i in range(samples):
            self.logger.info(f"  Testing memory init startup {i+1}/{samples}")
            
            # Test memory command startup time
            command = [
                str(self.claude_mpm_script),
                "memory",
                "list",
                "--limit", "10"
            ]
            
            measurement = self.measure_process_startup(command, timeout=15)
            measurements.append(measurement)
            
            if measurement.success:
                self.logger.debug(f"    Memory init {i+1}: {measurement.time_seconds:.3f}s")
            else:
                self.logger.warning(f"    Memory init {i+1}: FAILED - {measurement.error_message}")
        
        return measurements
    
    def analyze_results(self, measurements: List[StartupMeasurement]) -> Dict:
        """Analyze startup benchmark results."""
        successful_measurements = [m for m in measurements if m.success]
        
        if not successful_measurements:
            return {
                "total_samples": len(measurements),
                "successful_samples": 0,
                "success_rate": 0.0,
                "error": "No successful measurements"
            }
        
        times = [m.time_seconds for m in successful_measurements]
        memory_usage = [m.memory_mb for m in successful_measurements]
        
        # Group by mode for detailed analysis
        by_mode = {}
        for measurement in successful_measurements:
            if measurement.mode not in by_mode:
                by_mode[measurement.mode] = []
            by_mode[measurement.mode].append(measurement.time_seconds)
        
        mode_stats = {}
        for mode, times_list in by_mode.items():
            mode_stats[mode] = {
                "samples": len(times_list),
                "mean": statistics.mean(times_list),
                "median": statistics.median(times_list),
                "min": min(times_list),
                "max": max(times_list),
                "std_dev": statistics.stdev(times_list) if len(times_list) > 1 else 0.0
            }
        
        return {
            "total_samples": len(measurements),
            "successful_samples": len(successful_measurements),
            "success_rate": len(successful_measurements) / len(measurements) * 100,
            "overall_stats": {
                "mean_time": statistics.mean(times),
                "median_time": statistics.median(times),
                "min_time": min(times),
                "max_time": max(times),
                "std_dev_time": statistics.stdev(times) if len(times) > 1 else 0.0,
                "mean_memory_mb": statistics.mean(memory_usage),
                "target_time": 2.0,
                "meets_target": statistics.mean(times) <= 2.0
            },
            "by_mode": mode_stats,
            "failed_measurements": [
                {
                    "mode": m.mode,
                    "error": m.error_message,
                    "timestamp": m.timestamp
                }
                for m in measurements if not m.success
            ]
        }
    
    async def run_comprehensive_benchmark(self, samples: int = 5) -> Dict:
        """Run comprehensive startup benchmark."""
        self.logger.info("🎯 Starting comprehensive startup benchmark...")
        start_time = time.time()
        
        all_measurements = []
        
        # Run all benchmark categories
        all_measurements.extend(self.benchmark_oneshot_commands(samples))
        all_measurements.extend(self.benchmark_interactive_preparation(samples))
        all_measurements.extend(self.benchmark_agent_deployment_impact(samples))
        all_measurements.extend(self.benchmark_memory_initialization_impact(samples))
        
        execution_time = time.time() - start_time
        
        # Analyze results
        analysis = self.analyze_results(all_measurements)
        
        # Add benchmark metadata
        analysis["benchmark_metadata"] = {
            "total_execution_time": execution_time,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "samples_per_test": samples,
            "target_startup_time": 2.0,
            "baseline_startup_time": 4.0
        }
        
        # Add raw measurements
        analysis["raw_measurements"] = [asdict(m) for m in all_measurements]
        
        self.logger.info(f"📊 Benchmark completed in {execution_time:.2f}s")
        
        return analysis
    
    def save_results(self, results: Dict, output_file: Optional[Path] = None) -> Path:
        """Save benchmark results to JSON file."""
        if output_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = Path(__file__).parent / f"startup_benchmark_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        self.logger.info(f"📁 Results saved to: {output_file}")
        return output_file
    
    def print_summary(self, results: Dict):
        """Print benchmark summary."""
        stats = results.get("overall_stats", {})
        metadata = results.get("benchmark_metadata", {})
        
        print(f"\n{'='*60}")
        print("🚀 STARTUP PERFORMANCE BENCHMARK RESULTS")
        print(f"{'='*60}")
        print(f"Timestamp: {metadata.get('timestamp', 'Unknown')}")
        print(f"Total Samples: {results.get('total_samples', 0)}")
        print(f"Success Rate: {results.get('success_rate', 0):.1f}%")
        print(f"Execution Time: {metadata.get('total_execution_time', 0):.2f}s")
        
        print(f"\n📊 PERFORMANCE METRICS:")
        print(f"{'='*60}")
        print(f"Mean Startup Time:   {stats.get('mean_time', 0):.3f}s")
        print(f"Median Startup Time: {stats.get('median_time', 0):.3f}s")
        print(f"Min Startup Time:    {stats.get('min_time', 0):.3f}s")
        print(f"Max Startup Time:    {stats.get('max_time', 0):.3f}s")
        print(f"Standard Deviation:  {stats.get('std_dev_time', 0):.3f}s")
        print(f"Average Memory:      {stats.get('mean_memory_mb', 0):.1f}MB")
        
        target_met = stats.get('meets_target', False)
        target_time = metadata.get('target_startup_time', 2.0)
        print(f"\n🎯 TARGET VALIDATION:")
        print(f"{'='*60}")
        print(f"Target Time:         {target_time:.1f}s")
        print(f"Actual Time:         {stats.get('mean_time', 0):.3f}s")
        print(f"Target Met:          {'✅ YES' if target_met else '❌ NO'}")
        
        baseline = metadata.get('baseline_startup_time', 4.0)
        improvement = ((baseline - stats.get('mean_time', baseline)) / baseline) * 100
        print(f"Improvement:         {improvement:+.1f}% vs baseline ({baseline:.1f}s)")
        
        # Per-mode breakdown
        if "by_mode" in results:
            print(f"\n📋 BY MODE BREAKDOWN:")
            print(f"{'='*60}")
            for mode, mode_stats in results["by_mode"].items():
                print(f"{mode:20} {mode_stats['mean']:.3f}s (±{mode_stats['std_dev']:.3f}s) [{mode_stats['samples']} samples]")


async def main():
    """Main entry point for startup benchmark."""
    parser = argparse.ArgumentParser(
        description="Claude MPM Startup Performance Benchmark"
    )
    
    parser.add_argument("--samples", type=int, default=5, help="Number of samples per test")
    parser.add_argument("--output", "-o", type=Path, help="Output file for results (JSON)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    benchmark = StartupBenchmark()
    
    # Run comprehensive benchmark
    results = await benchmark.run_comprehensive_benchmark(args.samples)
    
    # Save results
    output_file = benchmark.save_results(results, args.output)
    
    # Print summary
    benchmark.print_summary(results)
    
    # Return exit code based on target achievement
    target_met = results.get("overall_stats", {}).get("meets_target", False)
    return 0 if target_met else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))