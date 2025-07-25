#!/usr/bin/env python3
"""Test script for claude print mode"""

def test_print_functionality():
    print("Testing basic print")
    print("Line 1")
    print("Line 2") 
    print("Line 3")
    
    # Test print with different separators
    print("A", "B", "C", sep=" | ")
    
    # Test print with custom end
    print("No newline", end="")
    print(" - continued on same line")
    
    # Test printing various data types
    print("\nTesting different data types:")
    print("String:", "Hello World")
    print("Integer:", 42)
    print("Float:", 3.14159)
    print("Boolean:", True)
    print("List:", [1, 2, 3])
    print("Dict:", {"key": "value"})
    
    # Test multiline output
    print("\nMultiline output:")
    print("""This is
a multiline
string""")

if __name__ == "__main__":
    test_print_functionality()