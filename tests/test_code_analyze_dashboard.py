#!/usr/bin/env python3
"""Test script for Code Analyze button in dashboard"""

import time
import subprocess
import sys
import os

def test_dashboard_code_analyze():
    """Test the Code Analyze button functionality"""
    print("\n" + "="*60)
    print("Testing Code Analysis Dashboard Button")
    print("="*60 + "\n")
    
    # Check if the dashboard is running
    print("1. Check dashboard at: http://localhost:8765")
    print("2. Navigate to the 'Code' tab")
    print("3. Verify the following:")
    print("   - Analyze button is visible with magnifying glass icon")
    print("   - Cancel button appears when analysis starts")
    print("   - Events display area shows real-time updates")
    print("   - Tree populates with discovered files")
    print("   - Button shows animated state during analysis")
    print("\nExpected behavior:")
    print("  ✓ Click 'Analyze' -> Button becomes '⏳ Analyzing...'")
    print("  ✓ Events area displays discovery messages")
    print("  ✓ Tree shows files and directories")
    print("  ✓ Stats update (files, classes, functions)")
    print("  ✓ Cancel button is functional")
    print("  ✓ Notifications appear for key events")
    
    print("\n" + "-"*60)
    print("Visual elements to verify:")
    print("-"*60)
    print("• Button States:")
    print("  - Normal: Blue gradient background")
    print("  - Analyzing: Orange gradient with pulse animation")
    print("  - Disabled: Gray background")
    print("\n• Events Display:")
    print("  - Shows below tree area")
    print("  - Has timestamp for each event")
    print("  - Different colors for event types")
    print("  - Auto-scrolls to latest")
    print("\n• Tree Visualization:")
    print("  - D3.js interactive tree")
    print("  - Click nodes to expand/collapse")
    print("  - Color coding by file type")
    print("  - Tooltips on hover")
    
    print("\n" + "="*60)
    print("Dashboard should be accessible at http://localhost:8765")
    print("="*60)

if __name__ == "__main__":
    test_dashboard_code_analyze()