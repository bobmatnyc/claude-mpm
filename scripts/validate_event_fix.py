#!/usr/bin/env python3
"""Comprehensive validation of the dashboard event parsing fixes."""

import json
import asyncio
import logging
import aiohttp
from datetime import datetime
from pathlib import Path
import sys
import time

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.services.socketio.server.core import SocketIOService
from claude_mpm.services.socketio.server.broadcaster import EventBroadcaster

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EventValidation:
    """Validates that events are correctly parsed and displayed."""
    
    def __init__(self):
        self.socketio_service = SocketIOService()
        self.broadcaster = EventBroadcaster()
        self.validation_results = []
    
    async def start_server(self):
        """Start the SocketIO server."""
        await self.socketio_service.start()
        logger.info(f"SocketIO server started on port {self.socketio_service.port}")
        await asyncio.sleep(2)  # Wait for server to be ready
    
    async def send_test_event(self, event_name, event_data, expected_type, expected_subtype):
        """Send a test event and record expectations."""
        logger.info(f"\nTesting: {event_name}")
        logger.info(f"  Sending: {json.dumps(event_data, indent=2)}")
        logger.info(f"  Expected: type='{expected_type}', subtype='{expected_subtype}'")
        
        # Broadcast the event
        await self.broadcaster.broadcast_event(event_data)
        
        # Record for validation
        self.validation_results.append({
            "name": event_name,
            "sent": event_data,
            "expected_type": expected_type,
            "expected_subtype": expected_subtype
        })
        
        # Small delay between events
        await asyncio.sleep(0.5)
    
    async def run_validation_suite(self):
        """Run comprehensive validation tests."""
        
        await self.start_server()
        
        logger.info("=" * 60)
        logger.info("DASHBOARD EVENT PARSING VALIDATION SUITE")
        logger.info("=" * 60)
        
        # Test Case 1: Hook events with conflicting type/subtype in data
        await self.send_test_event(
            "Hook Event with Type Conflict",
            {
                "type": "hook.pre_tool",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "type": "WRONG_TYPE",  # Should NOT overwrite
                    "subtype": "WRONG_SUBTYPE",  # Should NOT overwrite
                    "tool_name": "Edit",
                    "parameters": {"file_path": "/test/file.py", "old_string": "foo", "new_string": "bar"}
                }
            },
            expected_type="hook",
            expected_subtype="pre_tool"
        )
        
        # Test Case 2: Legacy SubagentStart event
        await self.send_test_event(
            "Legacy SubagentStart Event",
            {
                "event": "SubagentStart",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "agent_type": "Engineer",
                    "task": "Implement authentication system"
                }
            },
            expected_type="subagent",
            expected_subtype="start"
        )
        
        # Test Case 3: Session event with subtype in data
        await self.send_test_event(
            "Session Event with Data Subtype",
            {
                "type": "session",
                "subtype": "started",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "subtype": "conflicting_subtype",
                    "session_id": "sess_12345",
                    "user": "test_user"
                }
            },
            expected_type="session",
            expected_subtype="started"
        )
        
        # Test Case 4: Tool call with timestamp in data
        await self.send_test_event(
            "Tool Call with Timestamp Conflict",
            {
                "type": "hook.post_tool",
                "timestamp": "2024-01-01T10:00:00Z",
                "data": {
                    "timestamp": "2024-01-01T11:00:00Z",  # Different timestamp - should NOT overwrite
                    "tool_name": "MultiEdit",
                    "result": "success",
                    "edits_count": 5
                }
            },
            expected_type="hook",
            expected_subtype="post_tool"
        )
        
        # Test Case 5: UserPrompt legacy event
        await self.send_test_event(
            "Legacy UserPrompt Event",
            {
                "event": "UserPrompt",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "prompt_text": "Fix the authentication bug",
                    "session_id": "test_session"
                }
            },
            expected_type="hook",
            expected_subtype="user_prompt"
        )
        
        # Test Case 6: Dotted type format
        await self.send_test_event(
            "Dotted Type Format Event",
            {
                "type": "memory.operation",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "operation": "store",
                    "key": "user_preferences",
                    "value": {"theme": "dark"}
                }
            },
            expected_type="memory",
            expected_subtype="operation"
        )
        
        # Test Case 7: Event with ID in data
        await self.send_test_event(
            "Event with ID Conflict",
            {
                "type": "test",
                "id": "original_id_123",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "id": "conflicting_id_456",  # Should NOT overwrite
                    "test_name": "validation_test",
                    "status": "passed"
                }
            },
            expected_type="test",
            expected_subtype=""
        )
        
        # Test Case 8: Complex nested hook event
        await self.send_test_event(
            "Complex Hook Event",
            {
                "type": "hook.subagent_stop",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "type": "should_not_override",
                    "event_type": "also_should_not_override",
                    "agent_type": "Research",
                    "reason": "Task completed successfully",
                    "execution_time": 5.234,
                    "files_analyzed": 42
                }
            },
            expected_type="hook",
            expected_subtype="subagent_stop"
        )
        
        logger.info("\n" + "=" * 60)
        logger.info("VALIDATION COMPLETE")
        logger.info("=" * 60)
        
        logger.info("\n📊 VALIDATION SUMMARY:")
        logger.info(f"Total test cases: {len(self.validation_results)}")
        
        logger.info("\n🔍 MANUAL VERIFICATION REQUIRED:")
        logger.info("1. Open http://localhost:8080 in your browser")
        logger.info("2. Check the Events panel")
        logger.info("3. Verify each event shows the correct type (not 'unknown')")
        logger.info("4. Verify protected fields were not overwritten")
        
        logger.info("\n✅ EXPECTED RESULTS:")
        for result in self.validation_results:
            logger.info(f"  • {result['name']}: Should display as '{result['expected_type']}.{result['expected_subtype']}'")
        
        logger.info("\n❌ COMMON ISSUES TO CHECK:")
        logger.info("  • Events showing as 'unknown' type")
        logger.info("  • Hook events showing wrong type (e.g., 'WRONG_TYPE' instead of 'hook')")
        logger.info("  • Timestamps being overwritten by data fields")
        logger.info("  • Legacy events not being transformed correctly")
        
        # Keep server running
        logger.info("\n🚀 Server running. Press Ctrl+C to stop...")
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            await self.socketio_service.stop()

async def main():
    """Main validation entry point."""
    validator = EventValidation()
    await validator.run_validation_suite()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nValidation stopped by user.")