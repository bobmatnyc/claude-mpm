#!/usr/bin/env python3
"""
Simple hello world function for Claude MPM workflow testing.
"""

def hello_world():
    """
    Returns a greeting message for Claude MPM workflow testing.
    
    Returns:
        str: Hello world message
    """
    return "Hello from Claude MPM workflow test!"


if __name__ == "__main__":
    # Test the function
    message = hello_world()
    print(message)