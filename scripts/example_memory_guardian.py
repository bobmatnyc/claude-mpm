#!/usr/bin/env python3
"""Example usage of MemoryGuardian for monitoring Claude Code.

This script demonstrates how to use the MemoryGuardian service to:
1. Launch Claude Code as a subprocess
2. Monitor its memory usage
3. Automatically restart it when memory thresholds are exceeded
"""

import asyncio
import sys
import signal
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from claude_mpm.services.infrastructure.memory_guardian import MemoryGuardian
from claude_mpm.config.memory_guardian_config import MemoryGuardianConfig


class ClaudeCodeGuardian:
    """Example implementation of MemoryGuardian for Claude Code."""
    
    def __init__(self):
        """Initialize the guardian."""
        # Configure memory thresholds
        config = MemoryGuardianConfig()
        
        # Set thresholds based on your system
        # These are the defaults for a 24GB system
        config.thresholds.warning = 12288  # 12GB
        config.thresholds.critical = 15360  # 15GB
        config.thresholds.emergency = 18432  # 18GB
        
        # Configure monitoring intervals
        config.monitoring.normal_interval = 30  # Check every 30 seconds normally
        config.monitoring.warning_interval = 15  # Check every 15 seconds when warning
        config.monitoring.critical_interval = 5  # Check every 5 seconds when critical
        
        # Configure restart policy
        config.restart_policy.max_attempts = 3  # Max 3 restarts in window
        config.restart_policy.attempt_window = 3600  # 1 hour window
        config.restart_policy.initial_cooldown = 30  # Wait 30s before first restart
        
        # Configure the Claude Code command
        # Replace with actual Claude Code command
        config.process_command = ['claude-code']  # Or the actual command
        config.process_args = []  # Add any arguments
        
        # Enable state persistence
        config.persist_state = True
        config.state_file = Path.home() / '.claude-mpm' / 'memory_guardian_state.json'
        
        # Create the guardian
        self.guardian = MemoryGuardian(config)
        
        # Setup signal handlers for graceful shutdown
        self.setup_signal_handlers()
        
        print("Claude Code Memory Guardian initialized")
        print(f"Memory thresholds: Warning={config.thresholds.warning}MB, "
              f"Critical={config.thresholds.critical}MB, "
              f"Emergency={config.thresholds.emergency}MB")
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            print(f"\nReceived signal {signum}, shutting down...")
            asyncio.create_task(self.shutdown())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start(self):
        """Start the guardian and monitoring."""
        print("\nStarting Claude Code Memory Guardian...")
        
        # Initialize the guardian
        success = await self.guardian.initialize()
        if not success:
            print("Failed to initialize Memory Guardian")
            return False
        
        print("Memory Guardian initialized successfully")
        
        # Add state preservation hooks
        self.guardian.add_state_save_hook(self.on_state_save)
        self.guardian.add_state_restore_hook(self.on_state_restore)
        
        return True
    
    def on_state_save(self, state: dict):
        """Called before process restart to save state."""
        print(f"\n📝 Saving state before restart...")
        print(f"   - Current memory: {state['memory_stats']['current_mb']:.2f}MB")
        print(f"   - Peak memory: {state['memory_stats']['peak_mb']:.2f}MB")
        print(f"   - Total restarts: {state['total_restarts']}")
        
        # Here you could save additional application state
        # For example, save open files, conversation state, etc.
    
    def on_state_restore(self, state: dict):
        """Called after process restart to restore state."""
        print(f"\n📥 Restoring state after restart...")
        print(f"   - Previous peak memory: {state['memory_stats']['peak_mb']:.2f}MB")
        print(f"   - Total restarts: {state['total_restarts']}")
        
        # Here you could restore application state
        # For example, reopen files, restore conversation, etc.
    
    async def monitor_loop(self):
        """Main monitoring loop."""
        print("\n🔍 Starting memory monitoring...")
        print("Press Ctrl+C to stop\n")
        
        last_status_time = 0
        status_interval = 60  # Print status every minute
        
        while True:
            try:
                # Get current status
                status = self.guardian.get_status()
                
                # Print periodic status update
                current_time = asyncio.get_event_loop().time()
                if current_time - last_status_time > status_interval:
                    self.print_status(status)
                    last_status_time = current_time
                
                # Check for critical conditions
                if status['memory']['state'] == 'emergency':
                    print(f"\n🚨 EMERGENCY: Memory at {status['memory']['current_mb']:.2f}MB!")
                elif status['memory']['state'] == 'critical':
                    print(f"\n⚠️  CRITICAL: Memory at {status['memory']['current_mb']:.2f}MB")
                elif status['memory']['state'] == 'warning':
                    if current_time - last_status_time > 30:  # Print warnings less frequently
                        print(f"\n⚡ WARNING: Memory at {status['memory']['current_mb']:.2f}MB")
                        last_status_time = current_time
                
                # Check if process is still running
                if status['process']['state'] != 'running':
                    print(f"\n❌ Process is not running (state: {status['process']['state']})")
                    
                    # Check if we can restart
                    if not status['restarts']['can_restart']:
                        print("❌ Cannot restart - maximum attempts reached")
                        break
                
                await asyncio.sleep(10)  # Check status every 10 seconds
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"\n❌ Error in monitoring loop: {e}")
                await asyncio.sleep(5)
    
    def print_status(self, status: dict):
        """Print formatted status update."""
        print("\n" + "=" * 60)
        print("📊 Memory Guardian Status")
        print("-" * 60)
        
        # Process info
        process = status['process']
        print(f"Process: {process['state']} (PID: {process['pid'] or 'N/A'})")
        if process['uptime_hours'] > 0:
            print(f"Uptime: {process['uptime_hours']:.2f} hours")
        
        # Memory info
        memory = status['memory']
        print(f"\nMemory Usage:")
        print(f"  Current: {memory['current_mb']:.2f}MB")
        print(f"  Peak: {memory['peak_mb']:.2f}MB")
        print(f"  Average: {memory['average_mb']:.2f}MB")
        print(f"  State: {memory['state']}")
        
        # System memory
        system = memory['system']
        if system['total_mb'] > 0:
            used_mb = system['total_mb'] - system['available_mb']
            percent = (used_mb / system['total_mb']) * 100
            print(f"\nSystem Memory:")
            print(f"  Total: {system['total_mb']:.2f}MB")
            print(f"  Used: {used_mb:.2f}MB ({percent:.1f}%)")
            print(f"  Pressure: {system['pressure']}")
        
        # Restart info
        restarts = status['restarts']
        print(f"\nRestarts:")
        print(f"  Total: {restarts['total']}")
        print(f"  Can restart: {'Yes' if restarts['can_restart'] else 'No'}")
        if restarts['consecutive_failures'] > 0:
            print(f"  Consecutive failures: {restarts['consecutive_failures']}")
        
        # Recent restart attempts
        if restarts['recent_attempts']:
            print(f"\nRecent Restart Attempts:")
            for attempt in restarts['recent_attempts'][-3:]:  # Show last 3
                success = '✓' if attempt['success'] else '✗'
                print(f"  {success} {attempt['reason']} ({attempt['memory_mb']:.2f}MB)")
        
        print("=" * 60)
    
    async def shutdown(self):
        """Shutdown the guardian gracefully."""
        print("\n🛑 Shutting down Memory Guardian...")
        
        # Print final status
        status = self.guardian.get_status()
        self.print_status(status)
        
        # Shutdown the guardian
        await self.guardian.shutdown()
        print("\n✅ Memory Guardian shutdown complete")
    
    async def run(self):
        """Run the guardian."""
        try:
            # Start the guardian
            if not await self.start():
                return
            
            # Run monitoring loop
            await self.monitor_loop()
            
        except KeyboardInterrupt:
            print("\n\nReceived interrupt signal")
        finally:
            # Ensure cleanup
            await self.shutdown()


async def main():
    """Main entry point."""
    print("=" * 60)
    print("Claude Code Memory Guardian")
    print("=" * 60)
    print("\nThis service monitors Claude Code memory usage and")
    print("automatically restarts it when memory thresholds are exceeded.")
    print("\nNOTE: Replace 'claude-code' with the actual command to launch Claude Code")
    print("=" * 60)
    
    # Create and run the guardian
    guardian = ClaudeCodeGuardian()
    await guardian.run()


if __name__ == "__main__":
    # Check Python version
    if sys.version_info < (3, 8):
        print("This script requires Python 3.8 or later")
        sys.exit(1)
    
    # Run the guardian
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete")
    except Exception as e:
        print(f"\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)