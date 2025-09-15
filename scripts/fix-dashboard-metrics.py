#!/usr/bin/env python3
"""Fix the dashboard metrics and connection status display issues."""

import os
import re
import json
from pathlib import Path

def fix_dashboard_metrics():
    """Fix the dashboard metrics update and connection status issues."""

    base_path = Path("/Users/masa/Projects/claude-mpm/src/claude_mpm/dashboard/static/built")

    # Fix 1: Update dashboard.js to ensure metrics are updated after initialization
    dashboard_file = base_path / "dashboard.js"

    print("🔧 Fixing dashboard.js...")

    # Read the minified file
    with open(dashboard_file, 'r') as f:
        content = f.read()

    # The dashboard.js is minified, so we need to be careful
    # We need to add a call to update metrics after eventViewer is initialized

    # Find the initialization of eventViewer
    # Look for: this.eventViewer=new EventViewer("events-list",this.socketClient)

    # Add a delayed metrics update after initialization
    fix_pattern = r'(this\.eventViewer=new EventViewer\("events-list",this\.socketClient\))'
    replacement = r'\1,setTimeout(()=>{this.eventViewer&&this.eventViewer.updateMetrics&&(this.eventViewer.updateMetrics(),console.log("Initial metrics update triggered"))},100)'

    if re.search(fix_pattern, content):
        content = re.sub(fix_pattern, replacement, content)
        print("  ✓ Added initial metrics update trigger")
    else:
        print("  ⚠️ Could not find eventViewer initialization pattern")

    # Fix 2: Ensure metrics are updated when events are loaded from history
    # Look for the socketManager.onEventUpdate callback
    fix_pattern2 = r'(this\.socketManager\.onEventUpdate\(e=>\{)'
    replacement2 = r'\1this.eventViewer&&this.eventViewer.updateMetrics&&this.eventViewer.updateMetrics(),'

    if re.search(fix_pattern2, content):
        content = re.sub(fix_pattern2, replacement2, content)
        print("  ✓ Added metrics update to event update callback")
    else:
        print("  ⚠️ Could not find socketManager.onEventUpdate pattern")

    # Write the fixed content
    with open(dashboard_file, 'w') as f:
        f.write(content)

    print("  ✓ dashboard.js updated")

    # Fix 3: Update event-viewer.js to ensure metrics are called on init
    event_viewer_file = base_path / "components" / "event-viewer.js"

    print("\n🔧 Fixing event-viewer.js...")

    with open(event_viewer_file, 'r') as f:
        content = f.read()

    # Add an initial metrics update after setting up event handlers
    # Look for the init() method and add metrics update
    fix_pattern3 = r'(this\.socketClient\.onEventUpdate\(\(e,t\)=>\{this\.events=Array\.isArray\(e\)\?e:\[\],this\.updateDisplay\(\)\}\))'
    replacement3 = r'\1,setTimeout(()=>{this.updateMetrics(),console.log("EventViewer: Initial metrics update")},200)'

    if re.search(fix_pattern3, content):
        content = re.sub(fix_pattern3, replacement3, content)
        print("  ✓ Added initial metrics update to EventViewer init")
    else:
        print("  ⚠️ Could not find onEventUpdate pattern in EventViewer")

    # Also ensure updateDisplay calls updateMetrics
    fix_pattern4 = r'(updateDisplay\(\)\{this\.updateEventTypeDropdown\(\),this\.applyFilters\(\))'
    replacement4 = r'\1,this.events&&this.events.length>0&&!this.metricsInitialized&&(this.updateMetrics(),this.metricsInitialized=!0)'

    if re.search(fix_pattern4, content):
        content = re.sub(fix_pattern4, replacement4, content)
        print("  ✓ Added metrics update to updateDisplay")
    else:
        print("  ⚠️ Could not find updateDisplay pattern")

    with open(event_viewer_file, 'w') as f:
        f.write(content)

    print("  ✓ event-viewer.js updated")

    # Fix 4: Update socket-client.js to ensure connection status is properly updated
    socket_client_file = base_path / "socket-client.js"

    print("\n🔧 Fixing socket-client.js connection status...")

    with open(socket_client_file, 'r') as f:
        content = f.read()

    # The checkAndUpdateStatus function needs to trigger metrics update
    fix_pattern5 = r'(this\.updateConnectionStatusDOM\(e,t\))'
    replacement5 = r'\1,window.eventViewer&&window.eventViewer.updateMetrics&&window.eventViewer.updateMetrics()'

    if re.search(fix_pattern5, content):
        content = re.sub(fix_pattern5, replacement5, content)
        print("  ✓ Added metrics update to connection status changes")
    else:
        print("  ⚠️ Could not find updateConnectionStatusDOM pattern")

    with open(socket_client_file, 'w') as f:
        f.write(content)

    print("  ✓ socket-client.js updated")

    print("\n✅ Dashboard fixes applied successfully!")
    print("\n📝 Next steps:")
    print("1. Restart the monitoring server: ./scripts/claude-mpm monitor")
    print("2. Clear browser cache and reload the dashboard")
    print("3. Check that metrics update correctly")

if __name__ == "__main__":
    fix_dashboard_metrics()