#!/usr/bin/env python3
"""
Simple Flask Hello World application.

This module creates a basic Flask web application with a single route
that returns "Hello World" when accessed.
"""

from flask import Flask

# Create Flask application instance
app = Flask(__name__)

# Basic configuration
app.config["DEBUG"] = False  # Set to True for development


@app.route("/")
def hello_world():
    """
    Home page route handler.

    Returns a simple "Hello World" message when the root URL is accessed.

    Returns:
        str: The greeting message
    """
    return "Hello World"


if __name__ == "__main__":
    # Run the Flask development server
    # Host 0.0.0.0 makes it accessible from external IPs (optional)
    # Port 5000 is Flask's default port
    app.run(host="127.0.0.1", port=5000, debug=True)
