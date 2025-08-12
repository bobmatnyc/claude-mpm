#!/usr/bin/env python3
"""
Simple Flask "Hello World" Application

This is a basic Flask web application that demonstrates:
- Flask app initialization and configuration
- A single route handler that returns "Hello World"
- Development server setup with debug mode enabled
"""

# Import the Flask class from the flask module
from flask import Flask

# Create an instance of the Flask class
# __name__ is a Python predefined variable set to the name of the module
# This helps Flask know where to look for resources like templates and static files
app = Flask(__name__)

# Define a route using the @app.route decorator
# This tells Flask what URL should trigger our function
@app.route('/')
def hello_world():
    """
    Route handler for the root URL ('/').
    
    Returns a simple "Hello World" message when users visit the home page.
    This function is called whenever someone navigates to the root URL of our application.
    """
    return 'Hello World!'

# Optional: Add another route to demonstrate routing
@app.route('/hello/<name>')
def hello_name(name):
    """
    Route handler with URL parameter.
    
    Demonstrates dynamic routing where <name> is a variable part of the URL.
    For example: /hello/Claude would return "Hello, Claude!"
    """
    return f'Hello, {name}!'

# The main block - this code only runs when the script is executed directly
# (not when imported as a module)
if __name__ == '__main__':
    """
    Start the Flask development server.
    
    - debug=True enables debug mode, which provides detailed error messages
      and automatically reloads the server when code changes are detected
    - host='127.0.0.1' makes the app accessible only from localhost
    - port=5000 is the default Flask port (can be changed if needed)
    """
    print("Starting Flask Hello World application...")
    print("Visit http://127.0.0.1:5000 to see 'Hello World!'")
    print("Visit http://127.0.0.1:5000/hello/YourName to see a personalized greeting")
    print("Press Ctrl+C to stop the server")
    
    app.run(debug=True, host='127.0.0.1', port=5000)