"""MPM Commander REST API.

This package provides a FastAPI-based REST API for managing projects,
sessions, and messages in the MPM Commander.

Example:
    Run the API server with uvicorn:

    $ uvicorn claude_mpm.commander.api.app:app --host 127.0.0.1 --port 8000

    Access the API documentation at http://127.0.0.1:8000/docs
"""

from .app import app

__all__ = ["app"]
