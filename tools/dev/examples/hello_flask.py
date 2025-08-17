from flask import Flask

# Create Flask application instance
app = Flask(__name__)

# Define root route
@app.route('/')
def hello_world():
    """Return Hello World message at the root endpoint."""
    return 'Hello World'

# Run the application
if __name__ == '__main__':
    # Run in debug mode for development
    # Host 0.0.0.0 makes it accessible externally
    # Port 5000 is Flask's default
    app.run(debug=True, host='0.0.0.0', port=5000)