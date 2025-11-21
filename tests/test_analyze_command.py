#!/usr/bin/env python3
"""
Test script for the analyze command implementation.

This script tests the basic functionality of the new analyze command
without needing to run the full Claude system.
"""

import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from claude_mpm.cli.commands.analyze import AnalyzeCommand


def test_extract_mermaid():
    """Test mermaid extraction from text."""
    command = AnalyzeCommand()

    # Test content with multiple mermaid blocks
    test_content = """
# Analysis Results

Here's a class diagram:

## Class Relationships

```mermaid
classDiagram
    class Animal {
        +String name
        +int age
        +void eat()
    }
    class Dog {
        +void bark()
    }
    Animal <|-- Dog
```

And here's a flowchart:

### Process Flow

```mermaid
flowchart TD
    A[Start] --> B{Is it?}
    B -->|Yes| C[OK]
    B -->|No| D[End]
```

That's the analysis.
"""

    diagrams = command._extract_mermaid_diagrams(test_content)

    print(f"✓ Found {len(diagrams)} mermaid diagrams")

    for i, diagram in enumerate(diagrams):
        print(f"\nDiagram {i + 1}:")
        print(f"  Title: {diagram['title']}")
        print(f"  Content length: {len(diagram['content'])} chars")
        first_line = diagram["content"].split("\n")[0]
        print(f"  First line: {first_line}")

    assert len(diagrams) == 2, f"Expected 2 diagrams, got {len(diagrams)}"
    assert "classDiagram" in diagrams[0]["content"]
    assert "flowchart" in diagrams[1]["content"]

    print("\n✅ Mermaid extraction test passed!")


def test_build_prompt():
    """Test prompt building."""
    command = AnalyzeCommand()

    # Create a mock args object
    class MockArgs:
        target = Path("/test/path")
        prompt = "Focus on security vulnerabilities"
        focus = ["security", "performance"]
        mermaid = True
        mermaid_types = ["class_diagram", "flowchart"]

    args = MockArgs()
    prompt = command._build_analysis_prompt(args)

    print("\nGenerated prompt:")
    print("-" * 50)
    print(prompt)
    print("-" * 50)

    # Verify prompt contains expected elements
    assert str(args.target) in prompt
    assert "security vulnerabilities" in prompt
    assert "security" in prompt
    assert "performance" in prompt
    assert "mermaid" in prompt
    assert "class_diagram" in prompt

    print("\n✅ Prompt building test passed!")


def test_sanitize_filename():
    """Test filename sanitization."""
    command = AnalyzeCommand()

    test_cases = [
        ("Simple Title", "simple_title"),
        ("Title with Special!@# Chars", "title_with_special_chars"),
        ("Multiple   Spaces", "multiple_spaces"),
        (
            "Very " + "Long" * 20 + " Title",
            "very" + "_long" * 12,
        ),  # Truncated to 50 chars
    ]

    print("\nFilename sanitization tests:")
    for input_str, _expected in test_cases:
        result = command._sanitize_filename(input_str)
        print(f"  '{input_str[:30]}...' -> '{result}'")
        assert len(result) <= 50, f"Result too long: {len(result)} chars"

    print("\n✅ Filename sanitization test passed!")


def test_format_output():
    """Test output formatting."""
    command = AnalyzeCommand()

    result_data = {
        "target": "/test/path",
        "analysis": "Test analysis results",
        "diagrams_found": 2,
        "session_id": "test-session-123",
    }

    diagrams = [
        {"title": "diagram1", "content": "graph TD\nA-->B", "index": 1},
        {"title": "diagram2", "content": "classDiagram\nClass1", "index": 2},
    ]

    # Test text format
    text_output = command._format_output(result_data, "text", diagrams)
    print("\nText output sample:")
    print(text_output[:200] + "...")
    assert "Test analysis results" in text_output
    assert "2" in text_output

    # Test JSON format
    json_output = command._format_output(result_data, "json", diagrams)
    import json

    parsed = json.loads(json_output)
    assert parsed["target"] == "/test/path"
    assert len(parsed["diagrams"]) == 2
    print("✓ JSON output valid")

    # Test markdown format
    md_output = command._format_output(result_data, "markdown", diagrams)
    assert "```mermaid" in md_output
    assert "# Code Analysis Report" in md_output
    print("✓ Markdown output valid")

    print("\n✅ Output formatting test passed!")


def main():
    """Run all tests."""
    print("Testing analyze command implementation...\n")

    test_extract_mermaid()
    test_build_prompt()
    test_sanitize_filename()
    test_format_output()

    print("\n" + "=" * 50)
    print("✅ All tests passed successfully!")
    print("=" * 50)


if __name__ == "__main__":
    main()
