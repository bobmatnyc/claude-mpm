"""
Factorial calculation module with both iterative and recursive implementations.
"""

from typing import Union


def factorial_iterative(n: int) -> int:
    """
    Calculate the factorial of a non-negative integer using an iterative approach.
    
    The factorial of a non-negative integer n is the product of all positive integers 
    less than or equal to n. By definition, 0! = 1.
    
    Args:
        n (int): A non-negative integer whose factorial is to be calculated.
        
    Returns:
        int: The factorial of n.
        
    Raises:
        ValueError: If n is negative or not an integer.
        TypeError: If n cannot be converted to an integer.
        
    Examples:
        >>> factorial_iterative(5)
        120
        >>> factorial_iterative(0)
        1
        >>> factorial_iterative(1)
        1
    """
    # Type checking and validation
    if not isinstance(n, (int, float)):
        raise TypeError(f"Input must be a number, got {type(n).__name__}")
    
    # Check if it's a whole number if float
    if isinstance(n, float):
        if n.is_integer():
            n = int(n)
        else:
            raise ValueError(f"Input must be a whole number, got {n}")
    
    # Check for negative numbers
    if n < 0:
        raise ValueError(f"Factorial is not defined for negative numbers, got {n}")
    
    # Handle large numbers that might cause overflow
    if n > 170:  # 171! causes overflow in Python floats
        raise ValueError(f"Input too large. Maximum supported value is 170, got {n}")
    
    # Calculate factorial iteratively
    result = 1
    for i in range(1, n + 1):
        result *= i
    
    return result


def factorial_recursive(n: int) -> int:
    """
    Calculate the factorial of a non-negative integer using a recursive approach.
    
    This implementation uses recursion to calculate n! = n × (n-1)!
    with the base case that 0! = 1.
    
    Args:
        n (int): A non-negative integer whose factorial is to be calculated.
        
    Returns:
        int: The factorial of n.
        
    Raises:
        ValueError: If n is negative or not an integer.
        TypeError: If n cannot be converted to an integer.
        RecursionError: If n is too large (Python has a recursion limit).
        
    Examples:
        >>> factorial_recursive(5)
        120
        >>> factorial_recursive(0)
        1
        >>> factorial_recursive(1)
        1
        
    Note:
        For large values of n, this recursive approach may hit Python's recursion
        limit. Use factorial_iterative() for large numbers or adjust the recursion
        limit using sys.setrecursionlimit() (not recommended).
    """
    # Type checking and validation
    if not isinstance(n, (int, float)):
        raise TypeError(f"Input must be a number, got {type(n).__name__}")
    
    # Check if it's a whole number if float
    if isinstance(n, float):
        if n.is_integer():
            n = int(n)
        else:
            raise ValueError(f"Input must be a whole number, got {n}")
    
    # Check for negative numbers
    if n < 0:
        raise ValueError(f"Factorial is not defined for negative numbers, got {n}")
    
    # Warn about potential recursion limit for large numbers
    if n > 996:  # Python's default recursion limit is ~1000
        raise ValueError(f"Input too large for recursive approach. Use factorial_iterative() for n > 996, got {n}")
    
    # Base case
    if n == 0 or n == 1:
        return 1
    
    # Recursive case
    return n * factorial_recursive(n - 1)


def factorial(n: Union[int, float], method: str = "iterative") -> int:
    """
    Calculate the factorial of a non-negative integer.
    
    This is a wrapper function that can use either iterative or recursive
    implementation based on the method parameter.
    
    Args:
        n (Union[int, float]): A non-negative integer whose factorial is to be calculated.
        method (str, optional): The method to use - "iterative" or "recursive". 
                               Defaults to "iterative".
        
    Returns:
        int: The factorial of n.
        
    Raises:
        ValueError: If n is negative, not an integer, or if method is invalid.
        TypeError: If n cannot be converted to an integer.
        RecursionError: If using recursive method with large n.
        
    Examples:
        >>> factorial(5)
        120
        >>> factorial(5, method="recursive")
        120
        >>> factorial(0)
        1
        >>> factorial(10.0)  # Float that represents whole number
        3628800
    """
    # Validate method parameter
    if method not in ["iterative", "recursive"]:
        raise ValueError(f"Invalid method '{method}'. Choose 'iterative' or 'recursive'.")
    
    # Use appropriate implementation
    if method == "iterative":
        return factorial_iterative(n)
    else:
        return factorial_recursive(n)


# Example usage and demonstration
if __name__ == "__main__":
    # Demonstrate various use cases
    print("Factorial Calculation Examples:")
    print("-" * 40)
    
    # Basic examples
    test_values = [0, 1, 5, 10]
    for n in test_values:
        try:
            result_iter = factorial_iterative(n)
            result_rec = factorial_recursive(n)
            print(f"{n}! = {result_iter} (iterative) = {result_rec} (recursive)")
        except Exception as e:
            print(f"Error calculating {n}!: {e}")
    
    print("\nEdge Cases:")
    print("-" * 40)
    
    # Edge cases
    edge_cases = [-1, 3.14, 5.0, "5", None, 171, 997]
    for test in edge_cases:
        try:
            result = factorial(test)
            print(f"factorial({test}) = {result}")
        except Exception as e:
            print(f"factorial({test}) → {type(e).__name__}: {e}")
    
    print("\nPerformance Note:")
    print("-" * 40)
    print("For large numbers (n > 996), use the iterative method to avoid recursion limits.")
    print("Maximum supported value is 170 due to integer overflow considerations.")