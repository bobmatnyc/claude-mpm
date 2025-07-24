#!/usr/bin/env python3
"""Demo script showing TODO hijacking in action."""

import json
import time
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from orchestration.todo_hijacker import TodoHijacker
from orchestration.subprocess_orchestrator import SubprocessOrchestrator


def create_sample_todos(todo_dir):
    """Create sample TODO files for demonstration."""
    todo_dir.mkdir(parents=True, exist_ok=True)
    
    # Sample TODOs that would be created by Claude
    sample_todos = {
        "todos": [
            {
                "id": "demo-1",
                "content": "Implement a REST API endpoint for user registration",
                "priority": "high",
                "status": "pending",
                "created_at": "2025-01-23T10:00:00Z"
            },
            {
                "id": "demo-2",
                "content": "Write unit tests for the authentication module",
                "priority": "medium",
                "status": "pending",
                "created_at": "2025-01-23T10:01:00Z"
            },
            {
                "id": "demo-3",
                "content": "Update API documentation with new endpoints",
                "priority": "low",
                "status": "pending",
                "created_at": "2025-01-23T10:02:00Z"
            },
            {
                "id": "demo-4",
                "content": "Research best practices for JWT token refresh",
                "priority": "medium",
                "status": "pending",
                "created_at": "2025-01-23T10:03:00Z"
            }
        ]
    }
    
    # Write TODO file
    todo_file = todo_dir / f"demo_todos_{int(time.time())}.json"
    with open(todo_file, 'w') as f:
        json.dump(sample_todos, f, indent=2)
    
    print(f"Created sample TODO file: {todo_file}")
    return todo_file


def main():
    """Run the TODO hijacker demo."""
    print("=== Claude MPM TODO Hijacker Demo ===\n")
    
    # Use a clean demo directory
    demo_todo_dir = Path.home() / ".claude-mpm" / "demo" / "todos"
    demo_todo_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize TODO hijacker with demo directory
    print("Initializing TODO hijacker with demo directory...")
    hijacker = TodoHijacker(
        todo_dir=demo_todo_dir,
        log_level="INFO"
    )
    hijacker.start_monitoring()
    
    # Create sample TODOs
    print("\nCreating sample TODO file...")
    todo_file = create_sample_todos(demo_todo_dir)
    
    # Give the hijacker time to process
    print("\nWaiting for TODO hijacker to process...")
    time.sleep(1)
    
    # Check for pending delegations
    delegations = hijacker.get_pending_delegations()
    print(f"\nFound {len(delegations)} pending delegations from TODOs:")
    
    for i, delegation in enumerate(delegations, 1):
        print(f"\n{i}. Agent: {delegation['agent']}")
        print(f"   Task: {delegation['task'][:100]}...")
        print(f"   Confidence: {delegation['confidence']:.2f}")
        print(f"   Source: {delegation['source']}")
    
    # Demonstrate monitoring
    print("\n\nNow monitoring for new TODOs (press Ctrl+C to stop)...")
    print(f"Try creating a new JSON file in {demo_todo_dir}")
    
    try:
        # Keep monitoring
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping TODO monitoring...")
    
    # Clean up
    hijacker.stop_monitoring()
    
    print("\nDemo complete!")


if __name__ == "__main__":
    main()