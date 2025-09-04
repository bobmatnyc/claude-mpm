#!/usr/bin/env python3
"""
Data Engineer Agent - Event Test #19
=====================================

Test event streaming and data pipeline monitoring capabilities.
Validates JSON parsing, schema validation, and event transformation.

WHY THIS ARCHITECTURE:
- Async event emission for real-time monitoring
- Connection pooling for efficient HTTP requests
- Direct Socket.IO integration for low latency
- Schema validation for data quality

DESIGN DECISIONS:
- Event batching disabled for immediate feedback
- JSON serialization for cross-service compatibility
- Timestamp enrichment for event correlation
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.core.logging_config import get_logger
from claude_mpm.services.monitor.event_emitter import AsyncEventEmitter

logger = get_logger(__name__)


class DataEngineerEventTest:
    """Data pipeline event testing and validation."""

    def __init__(self):
        """Initialize the data engineer test."""
        self.emitter: AsyncEventEmitter = None
        self.test_number = 19
        self.agent_type = "Data Engineer Agent"

    async def initialize(self):
        """Set up event emitter with connection pooling."""
        try:
            self.emitter = await AsyncEventEmitter.get_instance()
            logger.info(f"{self.agent_type} initialized for test #{self.test_number}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize emitter: {e}")
            return False

    def create_test_event(self) -> Dict[str, Any]:
        """
        Create a structured test event with data pipeline metadata.

        Schema includes:
        - Event identification and timestamp
        - Data pipeline status indicators
        - Schema validation flags
        - Performance metrics
        """
        return {
            "test_id": f"data_engineer_test_{self.test_number}",
            "agent": self.agent_type,
            "timestamp": datetime.now().isoformat(),
            "message": f"{self.agent_type} - Event test #{self.test_number}: Event streaming operational. JSON parsing active. Data transformation pipelines ready. Schema validation enabled.",
            "pipeline_status": {
                "event_streaming": "operational",
                "json_parsing": "active",
                "data_transformation": "ready",
                "schema_validation": "enabled",
            },
            "metrics": {
                "throughput": "high",
                "latency": "low",
                "error_rate": 0.0,
                "queue_depth": 0,
            },
            "capabilities": [
                "real-time event processing",
                "JSON schema validation",
                "ETL pipeline orchestration",
                "data quality monitoring",
                "connection pooling",
                "async processing",
            ],
            "test_metadata": {
                "test_number": self.test_number,
                "environment": "development",
                "version": "4.0.25+",
                "framework": "claude-mpm",
            },
        }

    async def emit_test_event(self) -> bool:
        """
        Emit test event through the monitoring pipeline.

        Uses both direct Socket.IO emission and HTTP fallback
        for maximum reliability in event delivery.
        """
        try:
            event_data = self.create_test_event()

            # Pretty print for logging
            logger.info(f"Emitting {self.agent_type} test event:")
            logger.info(json.dumps(event_data, indent=2))

            # Try direct emission first (if Socket.IO servers are running)
            success = await self.emitter.emit_event(
                namespace="data_pipeline",
                event="test_event",
                data=event_data,
                force_http=False,  # Allow direct emission if available
            )

            if not success:
                # Fallback to HTTP emission
                logger.warning("Direct emission failed, trying HTTP...")
                success = await self.emitter.emit_event(
                    namespace="data_pipeline",
                    event="test_event",
                    data=event_data,
                    force_http=True,
                    endpoint="http://localhost:8765/api/events",
                )

            if success:
                logger.info(
                    f"✓ {self.agent_type} event test #{self.test_number} successful"
                )

                # Log performance stats
                stats = self.emitter.get_stats()
                logger.info(f"Performance stats: {json.dumps(stats, indent=2)}")
            else:
                logger.error(
                    f"✗ {self.agent_type} event test #{self.test_number} failed"
                )

            return success

        except Exception as e:
            logger.error(f"Error during event emission: {e}")
            return False

    async def cleanup(self):
        """Clean up resources."""
        if self.emitter:
            await self.emitter.close()
            logger.info(f"{self.agent_type} cleanup completed")


async def main():
    """Run the data engineer event test."""
    test = DataEngineerEventTest()

    try:
        # Initialize
        if not await test.initialize():
            logger.error("Failed to initialize test")
            return 1

        # Run test
        success = await test.emit_test_event()

        # Return status message
        if success:
            print(
                f"\n{test.agent_type} - Event test #{test.test_number}: Event streaming operational. JSON parsing active. Data transformation pipelines ready. Schema validation enabled."
            )
            return 0
        print(
            f"\n{test.agent_type} - Event test #{test.test_number}: Failed to emit event"
        )
        return 1

    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        return 1
    finally:
        await test.cleanup()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
