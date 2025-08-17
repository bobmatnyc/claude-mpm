#!/usr/bin/env python3
"""Demonstration script for the advanced health monitoring and recovery system.

This script shows how to use the comprehensive health monitoring and automatic
recovery mechanisms implemented for the claude-mpm Socket.IO server.

Usage:
    python scripts/demo_health_monitoring.py

Features demonstrated:
- Advanced health monitoring with multiple checkers
- Automatic recovery with circuit breaker pattern
- Configuration integration
- Health endpoint simulation
- Recovery event handling
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from claude_mpm.services.health_monitor import (
        AdvancedHealthMonitor, ProcessResourceChecker,
        NetworkConnectivityChecker, ServiceHealthChecker,
        HealthStatus, HealthMetric, HealthCheckResult
    )
    from claude_mpm.services.recovery_manager import (
        RecoveryManager, RecoveryAction, RecoveryEvent
    )
    from claude_mpm.core.config import Config
    HEALTH_MONITORING_AVAILABLE = True
except ImportError as e:
    print(f"Health monitoring not available: {e}")
    print("Please install psutil with: pip install psutil")
    sys.exit(1)


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demonstrate_health_monitoring():
    """Demonstrate basic health monitoring functionality."""
    print("=== Health Monitoring Demonstration ===\n")
    
    # Create configuration
    config = Config()
    health_config = config.get_health_monitoring_config()
    health_config['check_interval'] = 2  # Fast interval for demo
    
    print(f"Health monitoring configuration:")
    print(json.dumps(health_config, indent=2))
    print()
    
    # Create health monitor
    monitor = AdvancedHealthMonitor(health_config)
    
    # Add service health checker with mock stats
    service_stats = {
        'events_processed': 1000,
        'clients_connected': 5,
        'clients_served': 50,
        'errors': 5,  # 0.5% error rate - healthy
        'last_activity': time.time()
    }
    
    service_checker = ServiceHealthChecker(
        service_stats=service_stats,
        max_clients=100,
        max_error_rate=0.1  # 10% threshold
    )
    monitor.add_checker(service_checker)
    
    # Add network checker (will likely fail since no server running)
    network_checker = NetworkConnectivityChecker(
        host="localhost",
        port=8765,
        timeout=1.0
    )
    monitor.add_checker(network_checker)
    
    print("Performing health check...")
    result = await monitor.perform_health_check()
    
    print(f"Overall status: {result.overall_status.value}")
    print(f"Check duration: {result.duration_ms:.2f}ms")
    print(f"Metrics collected: {len(result.metrics)}")
    print()
    
    print("Individual metrics:")
    for metric in result.metrics:
        status_icon = {
            HealthStatus.HEALTHY: "✅",
            HealthStatus.WARNING: "⚠️", 
            HealthStatus.CRITICAL: "❌",
            HealthStatus.UNKNOWN: "❓"
        }.get(metric.status, "?")
        
        print(f"  {status_icon} {metric.name}: {metric.value} ({metric.status.value})")
        if metric.message:
            print(f"      {metric.message}")
    print()


async def demonstrate_recovery_system():
    """Demonstrate automatic recovery system."""
    print("=== Recovery System Demonstration ===\n")
    
    # Create configuration
    config = Config()
    recovery_config = config.get_recovery_config()
    recovery_config['min_recovery_interval'] = 0  # Allow immediate recovery for demo
    
    print(f"Recovery configuration:")
    print(json.dumps(recovery_config, indent=2))
    print()
    
    # Create recovery manager
    recovery_manager = RecoveryManager(recovery_config)
    
    # Setup recovery event callback
    def on_recovery_event(event: RecoveryEvent):
        action_icon = {
            RecoveryAction.LOG_WARNING: "📝",
            RecoveryAction.CLEAR_CONNECTIONS: "🔌",
            RecoveryAction.RESTART_SERVICE: "🔄",
            RecoveryAction.EMERGENCY_STOP: "🛑"
        }.get(event.action, "❓")
        
        status_icon = "✅" if event.success else "❌"
        print(f"  {action_icon} Recovery action: {event.action.value} {status_icon}")
        print(f"      Duration: {event.duration_ms:.2f}ms")
        if event.error_message:
            print(f"      Error: {event.error_message}")
    
    recovery_manager.add_recovery_callback(on_recovery_event)
    
    # Simulate different health scenarios
    scenarios = [
        ("Healthy system", HealthStatus.HEALTHY, []),
        ("Warning condition", HealthStatus.WARNING, [HealthMetric("cpu_usage", 75, HealthStatus.WARNING)]),
        ("Critical condition", HealthStatus.CRITICAL, [HealthMetric("memory_usage", 95, HealthStatus.CRITICAL)]),
    ]
    
    for scenario_name, status, metrics in scenarios:
        print(f"Scenario: {scenario_name}")
        
        # Create health result
        health_result = HealthCheckResult(
            overall_status=status,
            metrics=metrics,
            timestamp=time.time(),
            duration_ms=100.0,
            errors=[]
        )
        
        # Handle with recovery manager
        recovery_task = recovery_manager.handle_health_result(health_result)
        if recovery_task:
            # Wait for recovery to complete
            recovery_event = await recovery_task
            print(f"  Recovery triggered: {recovery_event.action.value}")
        else:
            print("  No recovery needed")
        
        print()
    
    # Show recovery statistics
    print("Recovery Statistics:")
    stats = recovery_manager.get_recovery_status()
    print(f"  Total recoveries: {stats['recovery_stats']['total_recoveries']}")
    print(f"  Successful: {stats['recovery_stats']['successful_recoveries']}")
    print(f"  Failed: {stats['recovery_stats']['failed_recoveries']}")
    print(f"  Circuit breaker state: {stats['circuit_breaker']['state']}")
    print()


async def demonstrate_circuit_breaker():
    """Demonstrate circuit breaker functionality."""
    print("=== Circuit Breaker Demonstration ===\n")
    
    from claude_mpm.services.recovery_manager import CircuitBreaker
    
    # Create circuit breaker with low thresholds for demo
    cb = CircuitBreaker(
        failure_threshold=3,
        timeout_seconds=2,
        success_threshold=2
    )
    
    print("Initial circuit breaker state:")
    status = cb.get_status()
    print(f"  State: {status['state']}")
    print(f"  Can proceed: {status['can_proceed']}")
    print()
    
    # Simulate failures
    print("Simulating failures...")
    for i in range(4):
        cb.record_failure()
        status = cb.get_status()
        print(f"  Failure {i+1}: State = {status['state']}, Can proceed = {status['can_proceed']}")
        
        if status['state'] == 'open':
            print("  Circuit breaker is now OPEN - blocking further operations")
            break
    print()
    
    # Wait for timeout
    print("Waiting for circuit breaker timeout...")
    await asyncio.sleep(2.1)
    
    status = cb.get_status()
    print(f"After timeout: State = {status['state']}, Can proceed = {status['can_proceed']}")
    print()
    
    # Simulate recovery
    print("Simulating successful operations...")
    for i in range(3):
        cb.record_success()
        status = cb.get_status()
        print(f"  Success {i+1}: State = {status['state']}")
        
        if status['state'] == 'closed':
            print("  Circuit breaker is now CLOSED - normal operation resumed")
            break
    print()


async def demonstrate_integrated_scenario():
    """Demonstrate integrated health monitoring and recovery scenario."""
    print("=== Integrated Scenario Demonstration ===\n")
    
    # Create integrated system
    config = Config()
    health_config = config.get_health_monitoring_config()
    health_config['check_interval'] = 1
    
    monitor = AdvancedHealthMonitor(health_config)
    recovery_manager = RecoveryManager(config.get_recovery_config())
    
    # Link them together
    monitor.add_health_callback(recovery_manager.handle_health_result)
    
    # Create a progressively failing service
    service_stats = {
        'events_processed': 100,
        'clients_connected': 10,
        'errors': 0,
        'last_activity': time.time()
    }
    
    service_checker = ServiceHealthChecker(service_stats, max_error_rate=0.1)
    monitor.add_checker(service_checker)
    
    print("Monitoring service with progressively increasing error rate...")
    
    # Simulate increasing errors over time
    for round_num in range(5):
        # Increase error rate each round
        service_stats['errors'] = round_num * 10
        service_stats['events_processed'] = 100  # Keep constant for error rate calc
        
        error_rate = service_stats['errors'] / service_stats['events_processed']
        print(f"\nRound {round_num + 1}: Error rate = {error_rate:.1%}")
        
        # Perform health check
        result = await monitor.perform_health_check()
        
        print(f"  Health status: {result.overall_status.value}")
        
        # Check if recovery was triggered
        recent_recoveries = recovery_manager.get_recovery_history(limit=1)
        if recent_recoveries and recent_recoveries[0].timestamp > time.time() - 2:
            latest_recovery = recent_recoveries[0]
            print(f"  🔄 Recovery action triggered: {latest_recovery.action.value}")
        
        await asyncio.sleep(1)
    
    # Show final statistics
    print("\nFinal System State:")
    aggregated = monitor.get_aggregated_status()
    print(f"  Overall health: {aggregated['overall_status']}")
    print(f"  Total health checks: {aggregated['checks_count']}")
    
    recovery_status = recovery_manager.get_recovery_status()
    print(f"  Total recoveries: {recovery_status['recovery_stats']['total_recoveries']}")
    print(f"  Circuit breaker: {recovery_status['circuit_breaker']['state']}")


async def main():
    """Run all demonstrations."""
    print("🏥 Advanced Health Monitoring and Recovery System Demo")
    print("=" * 60)
    print()
    
    try:
        await demonstrate_health_monitoring()
        await demonstrate_recovery_system()
        await demonstrate_circuit_breaker() 
        await demonstrate_integrated_scenario()
        
        print("✅ Demo completed successfully!")
        print()
        print("Key features demonstrated:")
        print("  • Advanced health monitoring with multiple checkers")
        print("  • Automatic recovery with graduated response")
        print("  • Circuit breaker pattern for failure protection")
        print("  • Configuration integration and validation")
        print("  • Comprehensive metrics and diagnostics")
        print()
        print("For production usage, these systems integrate seamlessly")
        print("with the StandaloneSocketIOServer to provide:")
        print("  • /health - Enhanced health endpoint")
        print("  • /diagnostics - Comprehensive troubleshooting info")
        print("  • /metrics - Monitoring system integration")
        print("  • Automatic recovery on service degradation")
        print("  • Circuit breaker protection against cascading failures")
        
    except Exception as e:
        logger.error(f"Demo failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())