#!/usr/bin/env python3
"""Test script to reproduce the cleanup-memory input issue."""

import os
import sys


def test_basic_input():
    """Test basic Python input() function."""
    print("Testing basic input() function...")
    print("stdin.isatty():", sys.stdin.isatty())
    print("stdout.isatty():", sys.stdout.isatty())

    try:
        response = input("Enter 'y' or 'n': ")
        print(f"You entered: '{response}'")
        print(f"Response repr: {repr(response)}")
        print(f"Response stripped: '{response.strip()}'")
        print(f"Response lower: '{response.lower()}'")
    except Exception as e:
        print(f"Error reading input: {e}")


def test_with_flush():
    """Test input with stdout flush."""
    print("\nTesting with stdout flush...")
    sys.stdout.flush()

    try:
        response = input("Enter 'y' or 'n' (with flush): ")
        print(f"You entered: '{response}'")
    except Exception as e:
        print(f"Error reading input: {e}")


def test_readline():
    """Test using sys.stdin.readline()."""
    print("\nTesting sys.stdin.readline()...")

    try:
        print("Enter 'y' or 'n' (readline): ", end="")
        sys.stdout.flush()
        response = sys.stdin.readline()
        print(f"You entered: '{response}'")
        print(f"Response stripped: '{response.strip()}'")
    except Exception as e:
        print(f"Error reading input: {e}")


if __name__ == "__main__":
    print("=== Input Testing Script ===")
    print(f"Python version: {sys.version}")
    print(f"Platform: {sys.platform}")
    print()

    test_basic_input()
    test_with_flush()
    test_readline()