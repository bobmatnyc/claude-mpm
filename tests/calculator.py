"""
A simple calculator module providing basic arithmetic operations.

This module implements add, subtract, multiply, and divide functions
with proper error handling and support for both integers and floats.
"""


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