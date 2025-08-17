#!/usr/bin/env python3
"""
Simple Flask Hello World Application

This is a basic Flask application that demonstrates:
- Flask app initialization
- Creating a simple route
- Returning a response

Author: Claude
Date: 2025-08-11
"""

# Import Flask class from flask module
from flask import Flask

# Create Flask application instance
# __name__ helps Flask determine the root path of the application
app = Flask(__name__)

# Define a route using the @app.route decorator
# The '/' means this function will handle requests to the root URL
@app.route('/')
def hello_world():
    """
    Handle requests to the root URL and return a greeting message.
    
    Returns:
        str: A simple "Hello World" message
    """
    return 'Hello World'

# Define an additional route to demonstrate multiple endpoints
@app.route('/about')
def about():
    """
    Handle requests to the /about URL.
    
    Returns:
        str: Information about the application
    """
    return 'This is a simple Flask Hello World application!'

# Define a route with a variable part (dynamic routing)
@app.route('/greet/<name>')
def greet(name):
    """
    Handle requests with a name parameter and return a personalized greeting.
    
    Args:
        name (str): The name to greet, extracted from the URL
    
    Returns:
        str: A personalized greeting message
    """
    return f'Hello, {name}! Welcome to Flask!'

# Main execution block
# This ensures the app only runs when the script is executed directly
# (not when imported as a module)
if __name__ == '__main__':
    # Run the Flask development server
    # debug=True enables debug mode with automatic reloading and better error messages
    # host='0.0.0.0' makes the server accessible from any network interface
    # port=5000 is the default Flask port (you can change it if needed)
    app.run(debug=True, host='127.0.0.1', port=5000)