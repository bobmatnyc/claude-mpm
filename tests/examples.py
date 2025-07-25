"""
Simple example functions consolidated from individual modules.

This module contains basic example functions (hello_world, calculator, greeting)
that were previously in separate files. These are used for testing purposes.
Note: More complex examples like factorial remain in their own modules.
"""


def hello_world():
    """Print a simple greeting message.
    
    Prints "Hello, World!" to the console.
    """
    print("Hello, World!")


def greet(name: str) -> str:
    """
    Generate a greeting message for the given name.
    
    Args:
        name (str): The name to greet
        
    Returns:
        str: A greeting message in the format 'Hello, {name}!'
        
    Example:
        >>> greet("Alice")
        'Hello, Alice!'
    """
    return f'Hello, {name}!'


def add(a, b):
    """
    Add two numbers together.
    
    Args:
        a (int or float): The first number
        b (int or float): The second number
        
    Returns:
        int or float: The sum of a and b
    """
    return a + b


def subtract(a, b):
    """
    Subtract the second number from the first.
    
    Args:
        a (int or float): The number to subtract from
        b (int or float): The number to subtract
        
    Returns:
        int or float: The difference of a and b
    """
    return a - b


def multiply(a, b):
    """
    Multiply two numbers together.
    
    Args:
        a (int or float): The first number
        b (int or float): The second number
        
    Returns:
        int or float: The product of a and b
    """
    return a * b


def divide(a, b):
    """
    Divide the first number by the second.
    
    Args:
        a (int or float): The dividend
        b (int or float): The divisor
        
    Returns:
        float: The quotient of a divided by b
        
    Raises:
        ValueError: If b is zero
    """
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b