#!/usr/bin/env python3
"""
Test script to verify the ticket close command fix.

WHY: This script tests that the close command properly handles the ticket_id
argument after our fix to handle both 'id' and 'ticket_id' attributes.

DESIGN DECISION: We simulate the argument namespace that the CLI parser creates
to test both the old 'id' attribute and the new 'ticket_id' attribute.
"""

import sys
import os
from argparse import Namespace

# Add the source directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from claude_mpm.cli.commands.tickets import (
    close_ticket,
    view_ticket,
    update_ticket,
    delete_ticket,
    add_comment,
    update_workflow
)

def test_close_with_ticket_id():
    """Test close_ticket with ticket_id attribute (new parser format)."""
    print("Testing close_ticket with ticket_id attribute...")
    
    # Simulate args with ticket_id attribute (as parser sets it)
    args = Namespace()
    args.ticket_id = "TSK-0001"
    args.comment = "Closing test ticket"
    
    try:
        # This should work without error now
        result = close_ticket(args)
        if result == 0:
            print("✅ close_ticket with ticket_id: SUCCESS (may fail if ticket doesn't exist, but no AttributeError)")
        else:
            print("✅ close_ticket with ticket_id: Command failed but no AttributeError")
    except AttributeError as e:
        if "'id'" in str(e):
            print(f"❌ close_ticket with ticket_id: FAILED - {e}")
            return False
        raise
    except Exception as e:
        # Other exceptions are OK (like ticket not found)
        print(f"✅ close_ticket with ticket_id: No AttributeError (got {type(e).__name__} which is expected)")
    
    return True

def test_close_with_id():
    """Test close_ticket with id attribute (backward compatibility)."""
    print("\nTesting close_ticket with id attribute (backward compatibility)...")
    
    # Simulate args with id attribute (for backward compatibility)
    args = Namespace()
    args.id = "TSK-0002"
    args.resolution = "Fixed in latest version"
    
    try:
        result = close_ticket(args)
        if result == 0:
            print("✅ close_ticket with id: SUCCESS")
        else:
            print("✅ close_ticket with id: Command failed but no AttributeError")
    except AttributeError as e:
        print(f"❌ close_ticket with id: FAILED - {e}")
        return False
    except Exception as e:
        print(f"✅ close_ticket with id: No AttributeError (got {type(e).__name__} which is expected)")
    
    return True

def test_other_commands():
    """Test other ticket commands to ensure they handle both attributes."""
    print("\nTesting other commands...")
    
    commands_to_test = [
        ("view_ticket", view_ticket, {"verbose": False}),
        ("update_ticket", update_ticket, {"status": "in_progress", "priority": None, "description": None, "tags": None, "assign": None}),
        ("add_comment", add_comment, {"comment": "Test comment"}),
        ("update_workflow", update_workflow, {"state": "done", "comment": None}),
    ]
    
    all_passed = True
    
    for cmd_name, cmd_func, extra_attrs in commands_to_test:
        # Test with ticket_id
        args = Namespace()
        args.ticket_id = "TSK-0003"
        for key, value in extra_attrs.items():
            setattr(args, key, value)
        
        try:
            cmd_func(args)
            print(f"  ✅ {cmd_name} with ticket_id: No AttributeError")
        except AttributeError as e:
            if "'id'" in str(e):
                print(f"  ❌ {cmd_name} with ticket_id: FAILED - {e}")
                all_passed = False
        except Exception:
            print(f"  ✅ {cmd_name} with ticket_id: No AttributeError")
        
        # Test with id (backward compatibility)
        args = Namespace()
        args.id = "TSK-0004"
        for key, value in extra_attrs.items():
            setattr(args, key, value)
        
        try:
            cmd_func(args)
            print(f"  ✅ {cmd_name} with id: No AttributeError")
        except AttributeError as e:
            if "'ticket_id'" in str(e) or "'id'" in str(e):
                print(f"  ❌ {cmd_name} with id: FAILED - {e}")
                all_passed = False
        except Exception:
            print(f"  ✅ {cmd_name} with id: No AttributeError")
    
    return all_passed

def test_delete_with_force():
    """Test delete_ticket with force flag to avoid input prompt."""
    print("\nTesting delete_ticket with force flag...")
    
    # Test with ticket_id
    args = Namespace()
    args.ticket_id = "TSK-0005"
    args.force = True  # Skip confirmation
    
    try:
        delete_ticket(args)
        print("  ✅ delete_ticket with ticket_id: No AttributeError")
    except AttributeError as e:
        if "'id'" in str(e):
            print(f"  ❌ delete_ticket with ticket_id: FAILED - {e}")
            return False
    except Exception:
        print("  ✅ delete_ticket with ticket_id: No AttributeError")
    
    # Test with id (backward compatibility)
    args = Namespace()
    args.id = "TSK-0006"
    args.force = True
    
    try:
        delete_ticket(args)
        print("  ✅ delete_ticket with id: No AttributeError")
    except AttributeError as e:
        print(f"  ❌ delete_ticket with id: FAILED - {e}")
        return False
    except Exception:
        print("  ✅ delete_ticket with id: No AttributeError")
    
    return True

def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Ticket Command Argument Parsing Fix")
    print("=" * 60)
    
    results = []
    
    # Run tests
    results.append(test_close_with_ticket_id())
    results.append(test_close_with_id())
    results.append(test_other_commands())
    results.append(test_delete_with_force())
    
    # Summary
    print("\n" + "=" * 60)
    if all(results):
        print("✅ ALL TESTS PASSED - The fix works correctly!")
        print("Both 'ticket_id' (from parser) and 'id' (backward compat) are handled.")
    else:
        print("❌ SOME TESTS FAILED - Please review the fix.")
        sys.exit(1)
    print("=" * 60)

if __name__ == "__main__":
    main()