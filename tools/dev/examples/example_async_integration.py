#!/usr/bin/env python3
"""
Example integration of async logging with Claude MPM.

Shows how to integrate the optimized async logging and hook system
into the main application for production use.
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.async_session_logger import get_async_logger, LogFormat
from claude_mpm.services.optimized_hook_service import get_optimized_hook_service
from claude_mpm.hooks.base_hook import HookContext, HookResult, HookType, PreDelegationHook, PostDelegationHook
from claude_mpm.core.config import Config


# Example hook implementations
class TimingHook(PreDelegationHook):
    """Example hook that adds timing information."""
    
    def __init__(self):
        super().__init__(name="timing_hook", priority=10)
        self.parallel_safe = True  # Can run in parallel
    
    def execute(self, context: HookContext) -> HookResult:
        """Add timing information to context."""
        import time
        context.data["start_time"] = time.time()
        return HookResult(success=True, data=context.data, modified=True)


class LoggingHook(PostDelegationHook):
    """Example hook that logs responses asynchronously."""
    
    def __init__(self):
        super().__init__(name="logging_hook", priority=90)
        self.logger = get_async_logger()
        self.parallel_safe = True
    
    def execute(self, context: HookContext) -> HookResult:
        """Log the response asynchronously."""
        if "response" in context.data:
            self.logger.log_response(
                request_summary=context.data.get("request_summary", "Unknown request"),
                response_content=context.data["response"],
                metadata={
                    "agent": context.data.get("agent", "unknown"),
                    "duration_ms": context.data.get("duration_ms", 0),
                    "session_id": context.session_id
                }
            )
        return HookResult(success=True)


class ClaudeMPMIntegration:
    """Example integration showing async logging in Claude MPM."""
    
    def __init__(self):
        # Initialize async logger
        self.logger = get_async_logger(
            log_format=LogFormat.JSON,  # Use JSON for structured logging
            enable_async=True
        )
        
        # Initialize optimized hook service
        self.hook_service = get_optimized_hook_service()
        
        # Register hooks
        self.hook_service.register_hook(TimingHook())
        self.hook_service.register_hook(LoggingHook())
        
        print("✓ Initialized async logging and hook system")
        print(f"  Session ID: {self.logger.session_id}")
        print(f"  Registered hooks: {self.hook_service.list_hooks()}")
    
    async def process_request_async(
        self,
        agent: str,
        request: str
    ) -> str:
        """
        Process a request asynchronously with hooks and logging.
        
        This simulates the main Claude MPM request flow.
        """
        # Create hook context
        import time
        from datetime import datetime
        context = HookContext(
            hook_type=HookType.PRE_DELEGATION,
            data={
                "agent": agent,
                "request": request,
                "request_summary": f"Process with {agent}"
            },
            metadata={},
            timestamp=datetime.now(),
            session_id=self.logger.session_id,
            user_id=None
        )
        
        # Execute pre-delegation hooks (adds timing, etc.)
        pre_result = await self.hook_service.execute_pre_delegation_hooks_async(context)
        
        # Simulate agent processing
        import time
        start = time.time()
        await asyncio.sleep(0.01)  # Simulate work
        response = f"Response from {agent}: Processed '{request}'"
        duration_ms = (time.time() - start) * 1000
        
        # Update context with response
        context.hook_type = HookType.POST_DELEGATION
        context.data.update({
            "response": response,
            "duration_ms": duration_ms,
            "success": True
        })
        
        # Execute post-delegation hooks (logs response, etc.)
        post_result = self.hook_service.execute_post_delegation_hooks(context)
        
        return response
    
    def process_request(self, agent: str, request: str) -> str:
        """Synchronous wrapper for async processing."""
        try:
            # Check if we're already in an event loop
            loop = asyncio.get_running_loop()
            # If we get here, we're in an async context, create a task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, self.process_request_async(agent, request))
                return future.result()
        except RuntimeError:
            # No event loop running, create one
            return asyncio.run(self.process_request_async(agent, request))
    
    async def process_batch_async(self, requests: list) -> list:
        """Process multiple requests concurrently."""
        tasks = [
            self.process_request_async(req["agent"], req["request"])
            for req in requests
        ]
        return await asyncio.gather(*tasks)
    
    def shutdown(self):
        """Gracefully shutdown logging and hooks."""
        print("\n📊 Performance Metrics:")
        print(f"  Logger stats: {self.logger.get_stats()}")
        print(f"  Hook metrics: {self.hook_service.get_metrics()}")
        
        # Flush and shutdown
        self.logger.flush(timeout=5.0)
        self.logger.shutdown()
        self.hook_service.shutdown()
        
        print("✓ Shutdown complete")


async def demonstrate_async_performance():
    """Demonstrate the performance benefits of async processing."""
    print("\n=== Async Performance Demonstration ===\n")
    
    app = ClaudeMPMIntegration()
    
    # Single request using async directly
    print("1. Processing single request...")
    response = await app.process_request_async("research", "What is quantum computing?")
    print(f"   Response: {response[:50]}...")
    
    # Batch requests (concurrent)
    print("\n2. Processing batch requests concurrently...")
    requests = [
        {"agent": "research", "request": f"Query {i}"}
        for i in range(10)
    ]
    
    import time
    start = time.time()
    responses = await app.process_batch_async(requests)
    batch_time = time.time() - start
    
    print(f"   Processed {len(responses)} requests in {batch_time:.3f}s")
    print(f"   Average: {batch_time/len(responses)*1000:.1f}ms per request")
    
    # High-throughput simulation
    print("\n3. High-throughput simulation...")
    high_volume_requests = [
        {"agent": f"agent_{i%3}", "request": f"High-volume query {i}"}
        for i in range(100)
    ]
    
    start = time.time()
    responses = await app.process_batch_async(high_volume_requests)
    throughput_time = time.time() - start
    
    print(f"   Processed {len(responses)} requests in {throughput_time:.3f}s")
    print(f"   Throughput: {len(responses)/throughput_time:.1f} requests/sec")
    
    # Check if any logs were dropped
    stats = app.logger.get_stats()
    if stats["dropped"] > 0:
        print(f"   ⚠️  Dropped {stats['dropped']} log entries (queue full)")
    else:
        print(f"   ✓ All {stats['queued']} log entries queued successfully")
    
    # Shutdown
    app.shutdown()


def demonstrate_configuration():
    """Show different configuration options."""
    print("\n=== Configuration Examples ===\n")
    
    # Example 1: JSON logging with compression
    print("1. JSON with compression:")
    from claude_mpm.services.async_session_logger import AsyncSessionLogger
    
    logger1 = AsyncSessionLogger(
        log_format=LogFormat.JSON,
        enable_compression=True
    )
    print(f"   Format: JSON (gzipped)")
    print(f"   Session: {logger1.session_id}")
    
    # Example 2: Syslog for production
    print("\n2. Syslog for production:")
    try:
        logger2 = AsyncSessionLogger(
            log_format=LogFormat.SYSLOG
        )
        print(f"   Format: Syslog (OS-native)")
        print(f"   Ultra-fast kernel-level logging")
    except:
        print("   Syslog not available on this system")
    
    # Example 3: Synchronous for debugging
    print("\n3. Synchronous for debugging:")
    logger3 = AsyncSessionLogger(
        enable_async=False
    )
    print(f"   Format: JSON (synchronous)")
    print(f"   Useful for debugging and testing")
    
    # Cleanup
    for logger in [logger1, logger2, logger3]:
        if logger:
            logger.shutdown()


def main():
    """Main demonstration."""
    print("🚀 Claude MPM Async Logging Integration Example")
    print("="*50)
    
    # Run async demonstration
    asyncio.run(demonstrate_async_performance())
    
    # Show configuration options
    demonstrate_configuration()
    
    print("\n✅ Integration example complete!")
    print("\nKey Integration Points:")
    print("1. Replace ClaudeSessionLogger with async version")
    print("2. Use optimized hook service for better performance")
    print("3. Enable fire-and-forget logging for zero latency")
    print("4. Configure based on deployment requirements")
    print("5. Monitor metrics for production health")


if __name__ == "__main__":
    main()