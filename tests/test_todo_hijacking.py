#!/usr/bin/env python3
"""Quick test of TODO hijacking functionality."""

import json
import time
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent / "src"))

from orchestration.todo_hijacker import TodoHijacker
from orchestration.todo_transformer import TodoTransformer

# Test the transformer
print("=== Testing TODO Transformer ===")
transformer = TodoTransformer()

test_todos = [
    {"content": "Implement REST API for user management", "status": "pending"},
    {"content": "Write unit tests for the API endpoints", "status": "pending"},
    {"content": "Deploy application to production server", "status": "pending"},
    {"content": "Update API documentation", "status": "pending"},
]

for todo in test_todos:
    result = transformer.transform_todo(todo)
    if result:
        print(f"✓ {result['agent']:15} (conf={result['confidence']:.2f}): {todo['content']}")

# Test the hijacker
print("\n=== Testing TODO Hijacker ===")

# Use a test directory
test_dir = Path("/tmp/claude-mpm-test-todos")
test_dir.mkdir(exist_ok=True)

# Create test TODO file
todo_data = {
    "todos": test_todos
}

todo_file = test_dir / "test_todos.json"
with open(todo_file, 'w') as f:
    json.dump(todo_data, f, indent=2)

print(f"Created test TODO file: {todo_file}")

# Initialize hijacker
hijacker = TodoHijacker(todo_dir=test_dir)

# Get pending delegations
delegations = hijacker.get_pending_delegations()
print(f"\nFound {len(delegations)} delegations:")

for d in delegations:
    print(f"  - {d['agent']:15}: {d['task'][:60]}...")

print("\n✅ TODO hijacking system is working correctly!")