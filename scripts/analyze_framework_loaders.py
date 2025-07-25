#!/usr/bin/env python3
"""Analyze framework loader consolidation."""

print("Framework Loader Analysis:")
print("=" * 50)

print("\nframework_loader.py features:")
print("- Auto-detect framework path")
print("- Load INSTRUCTIONS.md from framework")
print("- Agent registry integration")
print("- Agent definition loading")
print("- Version tracking")
print("- Comprehensive framework content")
print("- File size: ~471 lines")

print("\nminimal_framework_loader.py features:")
print("- Lightweight framework detection")
print("- Minimal hardcoded instructions")
print("- Basic agent list")
print("- Working directory INSTRUCTIONS.md support")
print("- No external dependencies")
print("- File size: ~106 lines")

print("\nConsolidation strategy:")
print("1. Create a single FrameworkLoader class")
print("2. Add 'mode' parameter: 'full' or 'minimal'")
print("3. Share common code (path detection, etc.)")
print("4. Conditionally load features based on mode")
print("5. Keep backwards compatibility")

print("\nEstimated reduction: ~35% (from 577 total lines to ~375 lines)")
print("Single configurable loader with both capabilities.")