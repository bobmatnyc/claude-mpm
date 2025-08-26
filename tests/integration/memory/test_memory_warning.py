#!/usr/bin/env python3
"""
Memory monitoring script for Claude MPM.
Tracks memory usage and provides warnings at various thresholds.
Can be run standalone or imported as a module.
"""

import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import psutil

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("memory_monitor")


class MemoryMonitor:
    """Memory monitoring utility for tracking process memory usage."""

    # Memory thresholds in MB
    WARNING_THRESHOLDS = [1024, 2048, 5120]  # 1GB, 2GB, 5GB

    def __init__(self, process_id: Optional[int] = None, enable_logging: bool = True):
        """
        Initialize memory monitor.

        Args:
            process_id: Process ID to monitor (defaults to current process)
            enable_logging: Whether to enable file logging
        """
        self.process = psutil.Process(process_id or os.getpid())
        self.start_memory = self.get_memory_usage()
        self.peak_memory = self.start_memory
        self.measurements: List[Tuple[datetime, float]] = []
        self.warnings_issued: Dict[int, bool] = dict.fromkeys(
            self.WARNING_THRESHOLDS, False
        )

        if enable_logging:
            self._setup_logging()

    def _setup_logging(self):
        """Setup file logging for memory tracking."""
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)

        file_handler = logging.FileHandler(
            log_dir / f"memory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        )
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(file_handler)

    def get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        try:
            mem_info = self.process.memory_info()
            return mem_info.rss / (1024 * 1024)  # Convert to MB
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return 0.0

    def get_system_memory(self) -> Dict[str, float]:
        """Get system-wide memory statistics."""
        mem = psutil.virtual_memory()
        return {
            "total": mem.total / (1024 * 1024),
            "available": mem.available / (1024 * 1024),
            "percent": mem.percent,
            "used": mem.used / (1024 * 1024),
        }

    def check_thresholds(self, current_memory: float) -> Optional[int]:
        """Check if memory has crossed any warning thresholds."""
        for threshold in self.WARNING_THRESHOLDS:
            if current_memory >= threshold and not self.warnings_issued[threshold]:
                self.warnings_issued[threshold] = True
                return threshold
        return None

    def measure(self, label: str = "") -> Dict[str, float]:
        """
        Take a memory measurement.

        Args:
            label: Optional label for this measurement

        Returns:
            Dictionary with memory statistics
        """
        current_memory = self.get_memory_usage()
        self.peak_memory = max(self.peak_memory, current_memory)
        self.measurements.append((datetime.now(), current_memory))

        # Check thresholds
        threshold_crossed = self.check_thresholds(current_memory)
        if threshold_crossed:
            warning_msg = (
                f"⚠️  MEMORY WARNING: Process memory exceeded {threshold_crossed}MB! "
                f"Current: {current_memory:.2f}MB"
            )
            print(f"\033[93m{warning_msg}\033[0m")  # Yellow warning
            logger.warning(warning_msg)

        stats = {
            "current": current_memory,
            "start": self.start_memory,
            "peak": self.peak_memory,
            "delta": current_memory - self.start_memory,
            "timestamp": datetime.now().isoformat(),
        }

        if label:
            stats["label"] = label

        # Log measurement
        logger.info(
            f"Memory measurement{' - ' + label if label else ''}: {current_memory:.2f}MB"
        )

        return stats

    def report(self, detailed: bool = True) -> str:
        """
        Generate a memory usage report.

        Args:
            detailed: Include detailed statistics

        Returns:
            Formatted report string
        """
        current = self.get_memory_usage()
        system = self.get_system_memory()

        report_lines = [
            "\n" + "=" * 60,
            "MEMORY USAGE REPORT",
            "=" * 60,
            f"Timestamp: {datetime.now().isoformat()}",
            "",
            "PROCESS MEMORY:",
            f"  Current:  {current:>10.2f} MB",
            f"  Start:    {self.start_memory:>10.2f} MB",
            f"  Peak:     {self.peak_memory:>10.2f} MB",
            f"  Delta:    {current - self.start_memory:>+10.2f} MB",
            "",
            "SYSTEM MEMORY:",
            f"  Total:    {system['total']:>10.2f} MB",
            f"  Used:     {system['used']:>10.2f} MB",
            f"  Available:{system['available']:>10.2f} MB",
            f"  Percent:  {system['percent']:>10.1f}%",
        ]

        if detailed and self.measurements:
            report_lines.extend(
                [
                    "",
                    "MEASUREMENT HISTORY:",
                ]
            )
            for timestamp, memory in self.measurements[-10:]:  # Last 10 measurements
                report_lines.append(
                    f"  {timestamp.strftime('%H:%M:%S')} - {memory:>8.2f} MB"
                )

        report_lines.append("=" * 60 + "\n")

        return "\n".join(report_lines)

    def monitor_operation(self, operation_name: str):
        """Context manager for monitoring memory during an operation."""

        class OperationMonitor:
            def __init__(self, monitor: "MemoryMonitor", name: str):
                self.monitor = monitor
                self.name = name
                self.start_stats = None
                self.end_stats = None

            def __enter__(self):
                self.start_stats = self.monitor.measure(f"{self.name} - START")
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                self.end_stats = self.monitor.measure(f"{self.name} - END")
                delta = self.end_stats["current"] - self.start_stats["current"]

                msg = (
                    f"Operation '{self.name}' completed. "
                    f"Memory delta: {delta:+.2f}MB "
                    f"(Current: {self.end_stats['current']:.2f}MB)"
                )

                if delta > 100:  # More than 100MB increase
                    print(f"\033[91m{msg}\033[0m")  # Red for high increase
                elif delta > 50:  # More than 50MB increase
                    print(f"\033[93m{msg}\033[0m")  # Yellow for moderate increase
                else:
                    print(f"\033[92m{msg}\033[0m")  # Green for low increase

                logger.info(msg)

        return OperationMonitor(self, operation_name)

    def continuous_monitor(
        self, interval: float = 1.0, duration: Optional[float] = None
    ):
        """
        Continuously monitor memory usage.

        Args:
            interval: Seconds between measurements
            duration: Total duration to monitor (None for infinite)
        """
        start_time = time.time()

        print("\nStarting continuous memory monitoring...")
        print("Press Ctrl+C to stop\n")

        try:
            while True:
                elapsed = time.time() - start_time

                if duration and elapsed >= duration:
                    break

                stats = self.measure(f"T+{elapsed:.1f}s")

                # Print inline status
                print(
                    f"\rMemory: {stats['current']:.2f}MB "
                    f"(Peak: {self.peak_memory:.2f}MB, "
                    f"Delta: {stats['delta']:+.2f}MB)",
                    end="",
                    flush=True,
                )

                time.sleep(interval)

        except KeyboardInterrupt:
            print("\n\nMonitoring stopped by user")

        print(self.report())


def main():
    """Main entry point for standalone execution."""
    import argparse

    parser = argparse.ArgumentParser(description="Monitor memory usage for Claude MPM")
    parser.add_argument(
        "--continuous", action="store_true", help="Run continuous monitoring"
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Monitoring interval in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        help="Monitoring duration in seconds (default: infinite)",
    )
    parser.add_argument(
        "--pid", type=int, help="Process ID to monitor (default: current process)"
    )
    parser.add_argument(
        "--test", action="store_true", help="Run test memory allocation"
    )

    args = parser.parse_args()

    monitor = MemoryMonitor(process_id=args.pid)

    if args.test:
        print("Running memory allocation test...")

        with monitor.monitor_operation("Small allocation (10MB)"):
            data1 = bytearray(10 * 1024 * 1024)
            time.sleep(0.5)

        with monitor.monitor_operation("Medium allocation (100MB)"):
            data2 = bytearray(100 * 1024 * 1024)
            time.sleep(0.5)

        with monitor.monitor_operation("Large allocation (500MB)"):
            data3 = bytearray(500 * 1024 * 1024)
            time.sleep(0.5)

        # Clear allocations
        del data1, data2, data3

        print(monitor.report())

    elif args.continuous:
        monitor.continuous_monitor(interval=args.interval, duration=args.duration)
    else:
        # Single measurement
        monitor.measure("Manual check")
        print(monitor.report())


if __name__ == "__main__":
    main()
