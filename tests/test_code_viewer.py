#!/usr/bin/env python3
"""
Test file for Code Viewer functionality.

This file contains various Python constructs to test AST parsing:
- Classes
- Functions
- Methods
- Decorators
- Async functions
"""

import asyncio
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class TestDataClass:
    """A test data class for AST parsing."""

    name: str
    value: int
    metadata: Optional[Dict] = None


class TestClass:
    """A test class with various methods."""

    def __init__(self, name: str):
        """Initialize the test class."""
        self.name = name
        self._private_value = 0

    @property
    def private_value(self) -> int:
        """Get the private value."""
        return self._private_value

    @private_value.setter
    def private_value(self, value: int):
        """Set the private value."""
        self._private_value = value

    def public_method(self, param: str) -> str:
        """A public method."""
        return f"Hello {param} from {self.name}"

    def _private_method(self) -> None:
        """A private method."""

    @staticmethod
    def static_method(x: int, y: int) -> int:
        """A static method."""
        return x + y

    @classmethod
    def class_method(cls, name: str) -> "TestClass":
        """A class method."""
        return cls(name)


async def async_function(delay: float = 1.0) -> str:
    """An async function for testing."""
    await asyncio.sleep(delay)
    return "Async operation completed"


def simple_function(a: int, b: int) -> int:
    """A simple function."""
    return a + b


def complex_function(data: List[Dict[str, any]]) -> Dict[str, List[str]]:
    """A more complex function with nested types."""
    result = {}

    for item in data:
        category = item.get("category", "unknown")
        if category not in result:
            result[category] = []

        if "name" in item:
            result[category].append(item["name"])

    return result


def function_with_decorators():
    """Function to test decorator parsing."""

    def decorator(func):
        def wrapper(*args, **kwargs):
            print(f"Calling {func.__name__}")
            return func(*args, **kwargs)

        return wrapper

    @decorator
    def decorated_function():
        return "decorated"

    return decorated_function


# Module-level variables
MODULE_CONSTANT = "test_constant"
module_variable = 42

# List comprehension
squared_numbers = [x**2 for x in range(10)]

# Dictionary comprehension
char_counts = {char: MODULE_CONSTANT.count(char) for char in set(MODULE_CONSTANT)}


if __name__ == "__main__":
    # Test the classes and functions
    test_obj = TestClass("TestInstance")
    print(test_obj.public_method("World"))

    # Test async function
    result = asyncio.run(async_function(0.1))
    print(result)

    # Test complex function
    test_data = [
        {"name": "item1", "category": "A"},
        {"name": "item2", "category": "B"},
        {"name": "item3", "category": "A"},
    ]

    grouped = complex_function(test_data)
    print(grouped)
