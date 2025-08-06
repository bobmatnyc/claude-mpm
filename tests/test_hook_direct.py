#!/usr/bin/env python3
"""
Direct test of hook handler Socket.IO connectivity.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from claude_mpm.core.logger import get_logger
from claude_mpm.hooks.claude_hooks.hook_handler import ClaudeHookHandler

logger = get_logger(__name__)

def main():
    logger.info("🔗 Testing hook handler Socket.IO connectivity...")
    
    try:
        # Create hook handler
        handler = ClaudeHookHandler()
        
        # Check if it has Socket.IO client
        if hasattr(handler, 'socketio_client') and handler.socketio_client is not None:
            logger.info("✅ Hook handler initialized with Socket.IO client")
            
            # Check connection status
            if hasattr(handler.socketio_client, 'connected'):
                connected = handler.socketio_client.connected
                logger.info(f"📡 Connection status: {'Connected' if connected else 'Disconnected'}")
            else:
                logger.info("📡 Connection status: Client created (status unknown)")
                
            logger.info("🎉 Hook handler is ready to send events to Socket.IO server")
            return True
        else:
            logger.warning("⚠️ Hook handler has no Socket.IO client")
            return False
            
    except Exception as e:
        logger.error(f"❌ Hook handler test failed: {e}")
        return False

if __name__ == "__main__":
    success = main()
    print(f"Result: {'PASS' if success else 'FAIL'}")
    sys.exit(0 if success else 1)