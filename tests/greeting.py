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