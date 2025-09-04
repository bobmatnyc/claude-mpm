#!/usr/bin/env python3
"""
Test file to verify that all types of functions are properly detected.
This file should show multiple functions in the AST tree.
"""

import os
from typing import Dict, List

# Module-level constants
VERSION = "1.0.0"
CONFIG = {"debug": True}


def public_function():
    """A regular public function."""
    return "public"


def _private_function():
    """A private function that should be detected."""
    return "private"


def __special_function__():
    """A special function with double underscores."""
    return "special"


async def async_function():
    """An async function."""
    return "async"


def get_value():
    """A getter function."""
    return "value"


def set_value(val):
    """A setter function."""


def handle_event():
    """An event handler that might be filtered."""


def on_click():
    """An event callback that might be filtered."""


def _setup_logging():
    """Setup function - should be detected."""
    import logging

    logging.basicConfig(level=logging.INFO)


def _validate_input(data):
    """Validation function - should be detected."""
    return isinstance(data, dict)


def _internal_helper():
    """Internal helper - should be detected."""
    return "helper"


class TestClass:
    """A test class with various methods."""

    def __init__(self):
        """Constructor."""
        self.value = 0

    def public_method(self):
        """Public method."""
        return "public"

    def _private_method(self):
        """Private method."""
        return "private"

    def __special_method__(self):
        """Special method."""
        return "special"

    @property
    def property_method(self):
        """Property method."""
        return self.value

    @staticmethod
    def static_method():
        """Static method."""
        return "static"

    @classmethod
    def class_method(cls):
        """Class method."""
        return cls()


# Test the functions
if __name__ == "__main__":
    print("Testing function detection...")
    print(f"Public: {public_function()}")
    print(f"Private: {_private_function()}")
    print(f"Special: {__special_function__()}")

    obj = TestClass()
    print(f"Object method: {obj.public_method()}")
    print(f"Property: {obj.property_method}")
    print(f"Static: {TestClass.static_method()}")
    print(f"Class: {TestClass.class_method().public_method()}")

    _setup_logging()
    print(f"Validation: {_validate_input({'test': True})}")
    print(f"Helper: {_internal_helper()}")
