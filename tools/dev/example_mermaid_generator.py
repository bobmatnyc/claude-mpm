#!/usr/bin/env python3
"""
Example script demonstrating MermaidGeneratorService usage.

This script shows how to use the MermaidGeneratorService to generate
various types of Mermaid diagrams from code analysis results.
"""

from pathlib import Path

from claude_mpm.services.visualization import (
    DiagramConfig,
    DiagramType,
    MermaidGeneratorService,
)


def main():
    """Run example Mermaid diagram generation."""

    # Initialize the service
    service = MermaidGeneratorService()
    if not service.initialize():
        print("Failed to initialize MermaidGeneratorService")
        return

    print("MermaidGeneratorService initialized successfully\n")

    # Example analysis results (would typically come from Code Analyzer agent)
    analysis_results = {
        "entry_points": {
            "cli": [
                {
                    "file": "src/claude_mpm/cli/main.py",
                    "function": "main",
                    "line": 42,
                },
                {
                    "file": "src/claude_mpm/cli/parser.py",
                    "function": "parse_args",
                    "line": 15,
                },
            ],
            "web": [
                {
                    "file": "src/claude_mpm/dashboard/app.py",
                    "function": "create_app",
                    "line": 25,
                }
            ],
        },
        "dependencies": {
            "claude_mpm.cli.main": [
                "os",
                "sys",
                "claude_mpm.core",
                "claude_mpm.services",
            ],
            "claude_mpm.core": ["logging", "pathlib", "json"],
            "claude_mpm.services": ["claude_mpm.core", "asyncio"],
        },
        "classes": {
            "MermaidGeneratorService": {
                "is_abstract": False,
                "bases": ["SyncBaseService"],
                "attributes": [
                    {"name": "_node_id_counter", "type": "int", "visibility": "-"},
                    {"name": "_node_id_cache", "type": "Dict", "visibility": "-"},
                ],
                "methods": [
                    {
                        "name": "generate_diagram",
                        "parameters": [
                            "diagram_type: DiagramType",
                            "analysis_results: Dict",
                            "config: DiagramConfig",
                        ],
                        "return_type": "str",
                        "visibility": "+",
                    },
                    {
                        "name": "_sanitize_node_id",
                        "parameters": ["identifier: str"],
                        "return_type": "str",
                        "visibility": "-",
                    },
                ],
            },
            "SyncBaseService": {
                "is_abstract": True,
                "attributes": [
                    {"name": "service_name", "type": "str", "visibility": "#"},
                    {"name": "logger", "type": "Logger", "visibility": "#"},
                ],
                "methods": [
                    {
                        "name": "initialize",
                        "parameters": [],
                        "return_type": "bool",
                        "visibility": "+",
                    },
                    {
                        "name": "shutdown",
                        "parameters": [],
                        "return_type": "None",
                        "visibility": "+",
                    },
                ],
            },
            "DiagramConfig": {
                "attributes": [
                    {"name": "title", "type": "Optional[str]"},
                    {"name": "direction", "type": "str"},
                    {"name": "theme", "type": "str"},
                ],
                "methods": [],
            },
        },
        "functions": {
            "main": {
                "calls": ["parse_args", "initialize_services", "run_command"],
                "parameters": [],
                "return_type": "int",
            },
            "parse_args": {
                "calls": ["ArgumentParser.parse_args"],
                "parameters": [],
                "return_type": "Namespace",
            },
            "initialize_services": {
                "calls": ["ServiceContainer.register", "ServiceContainer.resolve"],
                "parameters": ["config: Dict"],
                "return_type": "bool",
            },
            "run_command": {
                "calls": ["CommandHandler.execute"],
                "parameters": ["args: Namespace"],
                "return_type": "int",
            },
        },
        "call_graph": {
            "main": [
                {"function": "parse_args", "count": 1},
                {"function": "initialize_services", "count": 1},
                {"function": "run_command", "count": 1},
            ],
            "initialize_services": [
                {"function": "ServiceContainer.register", "count": 5},
                {"function": "ServiceContainer.resolve", "count": 3},
            ],
        },
    }

    # Generate different types of diagrams
    diagram_types = [
        (DiagramType.ENTRY_POINTS, "Application Entry Points"),
        (DiagramType.MODULE_DEPS, "Module Dependencies"),
        (DiagramType.CLASS_HIERARCHY, "Class Hierarchy"),
        (DiagramType.CALL_GRAPH, "Function Call Graph"),
    ]

    for diagram_type, title in diagram_types:
        print(f"\n{'=' * 60}")
        print(f"Generating {title}")
        print("=" * 60)

        config = DiagramConfig(
            title=title,
            direction="TB",  # Top to Bottom
            show_parameters=True,
            show_return_types=True,
            include_external=False,  # Don't show external modules in deps
        )

        try:
            diagram = service.generate_diagram(diagram_type, analysis_results, config)

            # Validate the generated diagram
            is_valid, error = service.validate_mermaid_syntax(diagram)
            if is_valid:
                print("✓ Valid Mermaid syntax generated")
            else:
                print(f"✗ Invalid syntax: {error}")

            # Show a preview of the diagram
            lines = diagram.split("\n")
            preview_lines = lines[:20] if len(lines) > 20 else lines
            print("\nDiagram preview:")
            print("-" * 40)
            for line in preview_lines:
                print(line)
            if len(lines) > 20:
                print(f"... ({len(lines) - 20} more lines)")

            # Save to file
            output_dir = Path("output/diagrams")
            output_dir.mkdir(parents=True, exist_ok=True)

            output_file = output_dir / f"{diagram_type.value}.mmd"
            output_file.write_text(diagram)
            print(f"\n✓ Saved to: {output_file}")

            # Add metadata
            metadata = {
                "timestamp": "2024-01-01 12:00:00",
                "source": "example_analysis",
                "type": diagram_type.value,
                "stats": {
                    "lines": len(lines),
                    "nodes": diagram.count("[") + diagram.count("{"),
                    "edges": diagram.count("-->") + diagram.count("<|--"),
                },
            }

            diagram_with_metadata = service.format_diagram_with_metadata(
                diagram, metadata
            )

            metadata_file = output_dir / f"{diagram_type.value}_with_metadata.mmd"
            metadata_file.write_text(diagram_with_metadata)
            print(f"✓ Saved with metadata to: {metadata_file}")

        except Exception as e:
            print(f"✗ Error generating diagram: {e}")

    # Shutdown the service
    service.shutdown()
    print("\n✓ Service shutdown complete")

    print("\n" + "=" * 60)
    print("Example complete!")
    print("\nYou can view the generated Mermaid diagrams in:")
    print("  - output/diagrams/*.mmd")
    print("\nTo render these diagrams:")
    print("  1. Copy the content to https://mermaid.live/")
    print("  2. Use a Markdown viewer that supports Mermaid")
    print("  3. Use the Mermaid CLI tool: mmdc -i file.mmd -o file.svg")


if __name__ == "__main__":
    main()
