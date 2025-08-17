#!/bin/bash

# Simple Flask app runner script

echo "Starting Flask Hello World application..."
echo "======================================="
echo ""

# Check if virtual environment exists and activate it if present
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Check if Flask is installed
if ! python -c "import flask" 2>/dev/null; then
    echo "Flask not found. Installing dependencies..."
    pip install Flask Werkzeug
fi

# Run the Flask application
echo "Starting Flask app on http://localhost:5000"
echo "Press Ctrl+C to stop the server"
echo ""
python scripts/app.py
