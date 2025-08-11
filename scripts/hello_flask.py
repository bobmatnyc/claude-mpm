#!/usr/bin/env python3
"""
Simple Hello World Flask application for demonstration purposes.
"""

# Import the Flask class from the flask module
from flask import Flask

# Create an instance of the Flask class
# __name__ helps Flask determine the root path for the application
app = Flask(__name__)

# Define a route for the root URL path ("/")
# The @app.route decorator tells Flask what URL should trigger this function
@app.route('/')
def hello_world():
    """
    Handle requests to the root URL path.
    Returns a simple greeting message.
    """
    return "Hello World!"

# Run the application only if this script is executed directly
# (not imported as a module)
if __name__ == '__main__':
    # Start the Flask development server
    # debug=True enables automatic reloading when code changes
    # host='127.0.0.1' makes the server accessible on localhost only
    # port=5000 is the default Flask port
    app.run(
        debug=True,           # Enable debug mode for development
        host='127.0.0.1',     # Run on localhost (more secure for development)
        port=5000             # Use default Flask port
    )