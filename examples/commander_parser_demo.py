#!/usr/bin/env python3
"""Demo of OutputParser functionality for MPM Commander.

This script demonstrates event detection from various tool outputs.
"""

from claude_mpm.commander.events.manager import EventManager
from claude_mpm.commander.parsing import OutputParser


def demo_basic_detection():
    """Demonstrate basic event detection without EventManager."""
    print("=" * 60)
    print("DEMO 1: Basic Event Detection (No EventManager)")
    print("=" * 60)

    parser = OutputParser()

    # Example tool output with multiple event types
    tool_output = """
Analyzing deployment configuration...

FileNotFoundError: deployment.yaml not found in project root

Which deployment strategy would you prefer?
1. Create minimal deployment.yaml
2. Copy from template
3. Skip deployment setup for now

This will overwrite your existing nginx configuration.
Are you sure you want to continue? (y/n)
"""

    results = parser.parse(tool_output, "demo-project", create_events=False)

    print(f"\nDetected {len(results)} events:\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. {result.event_type.value.upper()}")
        print(f"   Title: {result.title}")
        print(f"   Content: {result.content[:80]}...")
        if result.options:
            print(f"   Options: {result.options}")
        if result.context:
            print(f"   Context keys: {list(result.context.keys())}")
        print()


def demo_event_manager_integration():
    """Demonstrate integration with EventManager."""
    print("=" * 60)
    print("DEMO 2: EventManager Integration")
    print("=" * 60)

    # Create manager and parser
    manager = EventManager()
    parser = OutputParser(event_manager=manager)

    # Simulate multiple tool outputs
    outputs = [
        ("git", "Should I create a new branch for this feature? (y/n)"),
        ("pytest", "ValueError: Test configuration invalid"),
        ("docker", "Successfully built image: myapp:latest"),
        (
            "npm",
            """
Which package manager would you prefer?
1. npm
2. yarn
3. pnpm
""",
        ),
    ]

    print("\nProcessing tool outputs...\n")
    for tool, output in outputs:
        results = parser.parse(
            output,
            project_id="demo-project",
            session_id="session_1",
            create_events=True,
        )
        print(f"[{tool}] Detected {len(results)} event(s)")

    # Show inbox
    print("\n" + "=" * 60)
    print("INBOX (sorted by priority)")
    print("=" * 60)

    inbox = manager.get_inbox()
    for event in inbox:
        print(f"\n[{event.priority.value.upper()}] {event.type.value}")
        print(f"  Title: {event.title}")
        print(f"  Project: {event.project_id}")
        if event.options:
            print(f"  Options: {event.options}")
        print(f"  Status: {event.status.value}")


def demo_error_context():
    """Demonstrate error context extraction."""
    print("\n" + "=" * 60)
    print("DEMO 3: Error Context Extraction")
    print("=" * 60)

    parser = OutputParser()

    # Python traceback example
    error_output = """
Running test suite...
test_auth.py::test_login PASSED
test_auth.py::test_logout FAILED

Traceback (most recent call last):
  File "test_auth.py", line 45, in test_logout
    assert response.status_code == 200
AssertionError: assert 500 == 200

test_dashboard.py::test_render PASSED
"""

    results = parser.parse(error_output, "demo-project", create_events=False)

    for result in results:
        if result.event_type.value == "error":
            print(f"\nError detected: {result.title}")
            print("\nSurrounding context:")
            for i, line in enumerate(result.context["surrounding_lines"]):
                marker = ">>>" if i == result.context["error_line_index"] else "   "
                print(f"{marker} {line}")


def demo_code_block_filtering():
    """Demonstrate code block filtering."""
    print("\n" + "=" * 60)
    print("DEMO 4: Code Block Filtering")
    print("=" * 60)

    parser = OutputParser()

    # Output with code examples (should not trigger events)
    output_with_code = """
Here's how to handle errors in your code:

```python
def process_file(path):
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        print("Error: File not found")
        return None
```

This pattern prevents FileNotFoundError from crashing your application.
"""

    results = parser.parse(output_with_code, "demo-project", create_events=False)

    print("\nOutput contains error patterns in code blocks.")
    print(f"Events detected: {len(results)}")
    if len(results) == 0:
        print("✓ Code blocks successfully filtered out!")
    else:
        print("✗ False positive detected:")
        for result in results:
            print(f"  - {result.event_type.value}: {result.title}")


def demo_multiple_decisions():
    """Demonstrate option extraction from various formats."""
    print("\n" + "=" * 60)
    print("DEMO 5: Option Extraction Formats")
    print("=" * 60)

    parser = OutputParser()

    examples = [
        (
            "Numbered list",
            """
Select build target:
1. development
2. staging
3. production
""",
        ),
        (
            "Bullet list",
            """
Choose installation method:
- Install from source
- Use package manager
- Download binary
""",
        ),
        ("Inline options", "Select environment: (dev/staging/prod)"),
        ("Y/n format", "Enable debug mode? [Y/n]"),
    ]

    for name, output in examples:
        results = parser.parse(output, "demo-project", create_events=False)
        if results:
            print(f"\n{name}:")
            print(f"  Input: {output.strip()[:60]}...")
            print(f"  Detected options: {results[0].options}")


if __name__ == "__main__":
    demo_basic_detection()
    demo_event_manager_integration()
    demo_error_context()
    demo_code_block_filtering()
    demo_multiple_decisions()

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)
