#!/usr/bin/env python3
"""Migration script to update hook_handler to use EventBus.

This script:
1. Backs up the original hook_handler.py
2. Replaces it with the EventBus version
3. Updates the Socket.IO server to use the relay
4. Provides rollback capability
"""

import os
import shutil
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def backup_original_handler():
    """Backup the original hook handler."""
    src_file = Path(__file__).parent.parent / "src/claude_mpm/hooks/claude_hooks/hook_handler.py"
    backup_file = src_file.with_suffix(f".py.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    
    if src_file.exists():
        shutil.copy2(src_file, backup_file)
        print(f"✅ Backed up original to: {backup_file.name}")
        return backup_file
    else:
        print(f"❌ Original hook_handler.py not found at: {src_file}")
        return None


def install_eventbus_handler():
    """Install the EventBus version of hook handler."""
    src_file = Path(__file__).parent.parent / "src/claude_mpm/hooks/claude_hooks/hook_handler_eventbus.py"
    dest_file = Path(__file__).parent.parent / "src/claude_mpm/hooks/claude_hooks/hook_handler.py"
    
    if not src_file.exists():
        print(f"❌ EventBus handler not found at: {src_file}")
        return False
    
    # Copy EventBus version over the original
    shutil.copy2(src_file, dest_file)
    print(f"✅ Installed EventBus hook handler")
    return True


def update_socketio_server():
    """Update Socket.IO server to start the relay."""
    server_file = Path(__file__).parent.parent / "src/claude_mpm/services/socketio/server/core.py"
    
    if not server_file.exists():
        print(f"⚠️ Socket.IO server not found at: {server_file}")
        return False
    
    # Read the current server code
    content = server_file.read_text()
    
    # Check if already updated
    if "from claude_mpm.services.event_bus import SocketIORelay" in content:
        print("ℹ️ Socket.IO server already updated for EventBus")
        return True
    
    # Add import and initialization code
    # This is a simplified approach - in production you'd want more sophisticated patching
    print("⚠️ Manual update needed for Socket.IO server:")
    print("\n  Add to imports:")
    print("    from claude_mpm.services.event_bus import SocketIORelay")
    print("\n  Add to startup:")
    print("    relay = SocketIORelay(port=self.port)")
    print("    relay.start()")
    print("\n  Add to shutdown:")
    print("    relay.stop()")
    
    return True


def verify_installation():
    """Verify the EventBus installation."""
    print("\n🔍 Verifying installation...")
    
    # Check if EventBus can be imported
    try:
        from claude_mpm.services.event_bus import EventBus, SocketIORelay
        print("✅ EventBus module imports successfully")
    except ImportError as e:
        print(f"❌ Failed to import EventBus: {e}")
        return False
    
    # Check if hook handler uses EventBus
    handler_file = Path(__file__).parent.parent / "src/claude_mpm/hooks/claude_hooks/hook_handler.py"
    if handler_file.exists():
        content = handler_file.read_text()
        if "EventBus" in content:
            print("✅ Hook handler uses EventBus")
        else:
            print("❌ Hook handler does not use EventBus")
            return False
    
    # Test EventBus singleton
    try:
        bus1 = EventBus.get_instance()
        bus2 = EventBus()
        if bus1 is bus2:
            print("✅ EventBus singleton working")
        else:
            print("❌ EventBus singleton not working")
            return False
    except Exception as e:
        print(f"❌ EventBus test failed: {e}")
        return False
    
    return True


def rollback(backup_file):
    """Rollback to the original hook handler."""
    if not backup_file or not backup_file.exists():
        print("❌ No backup file to rollback to")
        return False
    
    dest_file = Path(__file__).parent.parent / "src/claude_mpm/hooks/claude_hooks/hook_handler.py"
    shutil.copy2(backup_file, dest_file)
    print(f"✅ Rolled back to original hook handler")
    return True


def main():
    """Main migration process."""
    print("=" * 60)
    print("EventBus Migration Script")
    print("=" * 60)
    
    # Check if already migrated
    handler_file = Path(__file__).parent.parent / "src/claude_mpm/hooks/claude_hooks/hook_handler.py"
    if handler_file.exists():
        content = handler_file.read_text()
        if "EventBus" in content:
            print("\n✅ System already migrated to EventBus")
            verify_installation()
            return 0
    
    print("\nThis script will migrate the hook system to use EventBus.")
    print("A backup will be created before making changes.\n")
    
    response = input("Continue with migration? (y/n): ").lower()
    if response != 'y':
        print("Migration cancelled")
        return 0
    
    # Step 1: Backup
    print("\n📦 Step 1: Creating backup...")
    backup_file = backup_original_handler()
    if not backup_file:
        print("Migration aborted: Could not create backup")
        return 1
    
    # Step 2: Install EventBus handler
    print("\n🔧 Step 2: Installing EventBus handler...")
    if not install_eventbus_handler():
        print("Migration aborted: Could not install EventBus handler")
        rollback(backup_file)
        return 1
    
    # Step 3: Update Socket.IO server
    print("\n🔄 Step 3: Updating Socket.IO server...")
    update_socketio_server()
    
    # Step 4: Verify
    print("\n✓ Step 4: Verification...")
    if verify_installation():
        print("\n" + "=" * 60)
        print("🎉 Migration completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Restart any running claude-mpm processes")
        print("2. Test with: python scripts/test_eventbus_integration.py")
        print(f"3. If issues occur, restore backup: {backup_file.name}")
        return 0
    else:
        print("\n⚠️ Verification failed, but migration completed")
        print(f"You may need to manually check the installation")
        print(f"Backup available at: {backup_file.name}")
        return 1


if __name__ == "__main__":
    sys.exit(main())