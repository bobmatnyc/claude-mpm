#!/usr/bin/env python3
"""
Test Code Analyzer Script
=========================

WHY: Quick test script to verify the code analyzer functionality
without running the full CLI.

Usage:
    python scripts/test_code_analyzer.py [path]
"""

import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.tools.code_tree_analyzer import CodeTreeAnalyzer
from claude_mpm.tools.code_tree_builder import CodeTreeBuilder


def main():
    # Get path from command line or use current directory
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()

    print(f"Analyzing code in: {path}")
    print("-" * 50)

    # First, build file tree
    print("\n1. Building file tree...")
    builder = CodeTreeBuilder()
    builder.build_tree(
        path, file_extensions=[".py", ".js", ".ts"], use_gitignore=True, max_depth=3
    )

    tree_stats = builder.get_stats()
    print(
        f"   Found {tree_stats['files_found']} files in {tree_stats['directories_scanned']} directories"
    )
    print(f"   Languages: {', '.join(tree_stats['languages'])}")
    print(f"   Total size: {tree_stats['total_size'] / 1024:.1f} KB")

    # Then analyze code structure
    print("\n2. Analyzing code structure...")
    analyzer = CodeTreeAnalyzer(emit_events=False)
    result = analyzer.analyze_directory(path, languages=["python"], max_depth=3)

    stats = result["stats"]
    print(f"   Processed {stats['files_processed']} files in {stats['duration']:.2f}s")
    print("   Found:")
    print(f"     - {stats['classes']} classes")
    print(f"     - {stats['functions']} functions/methods")
    print(f"     - {stats['imports']} imports")
    print(f"   Average complexity: {stats['avg_complexity']:.2f}")

    # Show most complex functions
    if result["nodes"]:
        complex_nodes = sorted(
            [
                n
                for n in result["nodes"]
                if hasattr(n, "complexity") and n.complexity > 5
            ],
            key=lambda x: x.complexity,
            reverse=True,
        )[:5]

        if complex_nodes:
            print("\n3. Most complex functions:")
            for node in complex_nodes:
                print(
                    f"   - {node.name} (complexity: {node.complexity}) in {Path(node.file_path).name}"
                )

    # Optionally save results
    if len(sys.argv) > 2 and sys.argv[2] == "--save":
        output_file = Path("code_analysis.json")
        with output_file.open("w") as f:
            # Convert nodes to dicts for JSON serialization
            result_dict = {
                "stats": stats,
                "tree": result["tree"],
                "nodes": [
                    {
                        "file_path": n.file_path,
                        "node_type": n.node_type,
                        "name": n.name,
                        "line_start": n.line_start,
                        "line_end": n.line_end,
                        "complexity": n.complexity,
                        "has_docstring": n.has_docstring,
                    }
                    for n in result["nodes"]
                ],
            }
            json.dump(result_dict, f, indent=2)
        print(f"\n✓ Results saved to {output_file}")


if __name__ == "__main__":
    main()
