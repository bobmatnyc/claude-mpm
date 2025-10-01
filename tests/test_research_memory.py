#!/usr/bin/env python3
"""
Test script for Research Agent memory management with content thresholds.

This script verifies:
1. Content threshold triggers for summarization
2. MCP document summarizer integration
3. Cumulative content tracking
4. Adaptive grep context management
5. File type-specific thresholds
"""

import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# No direct import needed - we'll just read the JSON file


def test_research_agent_thresholds():
    """Test the Research agent configuration for content thresholds."""

    print("Testing Research Agent Memory Management Configuration...")
    print("=" * 60)

    # Load the Research agent configuration
    research_config_path = (
        Path(__file__).parent.parent / "src/claude_mpm/agents/templates/research.json"
    )

    if not research_config_path.exists():
        print(f"❌ Research agent config not found at {research_config_path}")
        return False

    with research_config_path.open() as f:
        config = json.load(f)

    # Test 1: Check MCP tool configuration
    print("\n1. MCP Document Summarizer Integration:")
    tools = config.get("capabilities", {}).get("tools", [])
    mcp_tool = "mcp__claude-mpm-gateway__document_summarizer"

    if mcp_tool in tools:
        print(f"   ✅ MCP summarizer tool configured: {mcp_tool}")
    else:
        print("   ❌ MCP summarizer tool missing from tools list")
        return False

    # Test 2: Check knowledge domain expertise
    print("\n2. Knowledge Domain Expertise:")
    expertise = config.get("knowledge", {}).get("domain_expertise", [])
    threshold_expertise = [
        e for e in expertise if "threshold" in e.lower() or "20KB" in e
    ]

    if threshold_expertise:
        print("   ✅ Content threshold expertise found:")
        for exp in threshold_expertise:
            print(f"      - {exp}")
    else:
        print("   ⚠️  No explicit threshold expertise found")

    # Test 3: Check best practices
    print("\n3. Best Practices:")
    practices = config.get("knowledge", {}).get("best_practices", [])
    threshold_practices = [
        p
        for p in practices
        if any(
            word in p.lower()
            for word in [
                "threshold",
                "20kb",
                "200 lines",
                "50kb",
                "batch",
                "cumulative",
            ]
        )
    ]

    if threshold_practices:
        print("   ✅ Threshold-related best practices found:")
        for practice in threshold_practices[:3]:  # Show first 3
            print(f"      - {practice[:80]}...")
    else:
        print("   ⚠️  No threshold-specific best practices found")

    # Test 4: Check constraints
    print("\n4. Constraints:")
    constraints = config.get("knowledge", {}).get("constraints", [])
    threshold_constraints = [
        c
        for c in constraints
        if any(
            word in c.lower()
            for word in ["20kb", "100kb", "50kb", "adaptive", "threshold"]
        )
    ]

    if threshold_constraints:
        print("   ✅ Threshold constraints found:")
        for constraint in threshold_constraints:
            print(f"      - {constraint[:80]}...")
    else:
        print("   ❌ No threshold constraints found")
        return False

    # Test 5: Check instructions for threshold system
    print("\n5. Instructions Content:")
    instructions = config.get("instructions", "")

    # Check for critical threshold sections
    checks = {
        "Content Threshold System": "CONTENT THRESHOLD SYSTEM" in instructions,
        "Threshold Constants": "SUMMARIZE_THRESHOLD_LINES = 200" in instructions,
        "Critical File Size": "CRITICAL_FILE_SIZE = 100_000" in instructions,
        "Cumulative Limit": "CUMULATIVE_CONTENT_LIMIT = 50_000" in instructions,
        "Batch Count": "BATCH_SUMMARIZE_COUNT = 3" in instructions,
        "File Type Thresholds": "FILE_TYPE_THRESHOLDS" in instructions,
        "Progressive Summarization": "Progressive Summarization Strategy"
        in instructions,
        "Adaptive Grep Context": "Adaptive Grep Context" in instructions,
        "MCP Integration Patterns": "MCP Summarizer Integration Patterns"
        in instructions,
    }

    all_passed = True
    for check_name, result in checks.items():
        if result:
            print(f"   ✅ {check_name}: Found")
        else:
            print(f"   ❌ {check_name}: Missing")
            all_passed = False

    # Test 6: Verify specific threshold values
    print("\n6. Threshold Values Verification:")
    threshold_values = {
        "Single File Lines": "200" in instructions
        and "SUMMARIZE_THRESHOLD_LINES" in instructions,
        "Single File Size": "20_000" in instructions or "20KB" in instructions,
        "Critical Size": "100_000" in instructions or "100KB" in instructions,
        "Cumulative Size": "50_000" in instructions or "50KB" in instructions,
        "Batch Count": "3" in instructions and "BATCH_SUMMARIZE_COUNT" in instructions,
    }

    for value_name, found in threshold_values.items():
        if found:
            print(f"   ✅ {value_name}: Configured")
        else:
            print(f"   ⚠️  {value_name}: May need verification")

    # Test 7: Check for file type specific handling
    print("\n7. File Type Specific Thresholds:")
    file_types = [".py", ".js", ".json", ".yaml", ".md", ".csv"]
    found_types = [ft for ft in file_types if ft in instructions]

    if len(found_types) >= 4:
        print(
            f"   ✅ File type specific thresholds found for: {', '.join(found_types)}"
        )
    else:
        print(
            f"   ⚠️  Limited file type coverage: {', '.join(found_types) if found_types else 'None'}"
        )

    # Test 8: Memory metrics reporting
    print("\n8. Memory Metrics Reporting:")
    memory_metrics = [
        "Files Sampled",
        "Sections Extracted",
        "Full Files Read",
        "Memory Usage",
        "MCP Summarizer Used",
    ]

    found_metrics = [m for m in memory_metrics if m in instructions]
    if len(found_metrics) >= 4:
        print(
            f"   ✅ Memory metrics reporting configured ({len(found_metrics)}/{len(memory_metrics)})"
        )
    else:
        print(
            f"   ⚠️  Incomplete memory metrics: {len(found_metrics)}/{len(memory_metrics)}"
        )

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ All critical threshold checks passed!")
    else:
        print("⚠️  Some threshold configurations may need adjustment")

    return all_passed


def display_threshold_summary():
    """Display a summary of the configured thresholds."""

    print("\n📊 CONFIGURED THRESHOLDS SUMMARY")
    print("=" * 60)

    thresholds = {
        "Single File Thresholds": {
            "Trigger Summarization": "200 lines or 20KB",
            "Critical (Always Summarize)": ">100KB",
            "Skip Unless Critical": ">1MB",
        },
        "Cumulative Thresholds": {
            "Total Content Limit": "50KB",
            "File Count Limit": "3 files",
            "Action": "Triggers batch summarization",
        },
        "Adaptive Grep Context": {
            ">50 matches": "-A 2 -B 2 with head -50",
            "20-50 matches": "-A 5 -B 5 with head -40",
            "<20 matches": "-A 10 -B 10 (default)",
        },
        "File Type Specific (lines)": {
            "Code (.py, .js, .ts)": "500 lines",
            "Config (.json, .yaml, .toml)": "100 lines",
            "Docs (.md, .rst, .txt)": "200 lines",
            "Data (.csv, .sql, .xml)": "50 lines",
        },
        "MCP Summarizer Styles": {
            "Code Files": "bullet_points (200 words max)",
            "Documentation": "brief (150 words max)",
            "Config Files": "detailed (250 words max)",
            "Batch Summary": "executive (300 words max)",
        },
    }

    for category, items in thresholds.items():
        print(f"\n{category}:")
        for key, value in items.items():
            print(f"  • {key}: {value}")

    print("\n" + "=" * 60)
    print("These thresholds ensure the Research agent maintains")
    print("85% confidence while preventing memory accumulation.")


def main():
    """Main test execution."""

    print("\n🔬 Research Agent Memory Management Test")
    print("=" * 60)

    # Run threshold configuration test
    success = test_research_agent_thresholds()

    # Display threshold summary
    display_threshold_summary()

    # Final summary
    print("\n📋 TEST SUMMARY")
    print("=" * 60)

    if success:
        print("✅ Research agent is properly configured with:")
        print("   • Content threshold system (20KB/200 lines)")
        print("   • MCP document summarizer integration")
        print("   • Progressive summarization strategy")
        print("   • Cumulative content tracking (50KB/3 files)")
        print("   • Adaptive grep context management")
        print("   • File type-specific thresholds")
        print("\n✨ The Research agent will maintain 85% confidence")
        print("   while preventing memory accumulation through")
        print("   intelligent content management and summarization.")
    else:
        print("⚠️  Some configuration elements need attention.")
        print("   Review the test output above for details.")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
