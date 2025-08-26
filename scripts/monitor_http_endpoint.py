#!/usr/bin/env python3
"""Monitor HTTP endpoint to see if events are being received."""

import json
from datetime import datetime

from flask import Flask, request

app = Flask(__name__)

# Log file
log_file = "/tmp/http-endpoint-monitor.log"


@app.route("/api/events", methods=["POST"])
def handle_event():
    """Log any incoming events."""
    try:
        data = request.get_json()

        with open(log_file, "a") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Source IP: {request.remote_addr}\n")
            f.write(f"Headers: {dict(request.headers)}\n")
            f.write(f"Event data:\n{json.dumps(data, indent=2)}\n")

        print(
            f"[{datetime.now().isoformat()}] Received event: {data.get('event', 'unknown')}"
        )

        return "", 204
    except Exception as e:
        print(f"Error: {e}")
        return str(e), 500


@app.route("/")
def home():
    return "<h1>HTTP Endpoint Monitor Running</h1>"


if __name__ == "__main__":
    print("Starting HTTP endpoint monitor on port 8766")
    print(f"Logging to: {log_file}")
    app.run(host="0.0.0.0", port=8766, debug=False)
