#!/usr/bin/env python3
"""
Read the Docs API client for claude-mpm documentation management.

This script provides utilities for managing the Read the Docs deployment
programmatically using the API.
"""

import argparse
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List

try:
    import requests
except ImportError:
    print("Error: requests library not installed. Run: pip install requests")
    sys.exit(1)


class ReadTheDocsClient:
    """Client for interacting with Read the Docs API."""

    def __init__(self, api_token: str, project_slug: str = "claude-mpm"):
        """
        Initialize the Read the Docs API client.

        Args:
            api_token: Read the Docs API authentication token
            project_slug: Project identifier on Read the Docs
        """
        self.api_token = api_token
        self.project_slug = project_slug
        self.base_url = "https://readthedocs.org/api/v3"
        self.headers = {
            "Authorization": f"Token {api_token}",
            "Content-Type": "application/json",
        }

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make an API request with error handling."""
        url = f"{self.base_url}/{endpoint}"

        try:
            response = requests.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            if hasattr(e.response, "text"):
                print(f"Response: {e.response.text}")
            raise

    def get_project_info(self) -> Dict[str, Any]:
        """Get project information."""
        return self._make_request("GET", f"projects/{self.project_slug}/")

    def list_versions(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """List all project versions."""
        endpoint = f"projects/{self.project_slug}/versions/"
        params = {"active": "true"} if active_only else {}
        result = self._make_request("GET", endpoint, params=params)
        return result.get("results", [])

    def activate_version(
        self, version_slug: str, active: bool = True
    ) -> Dict[str, Any]:
        """Activate or deactivate a version."""
        endpoint = f"projects/{self.project_slug}/versions/{version_slug}/"
        return self._make_request("PATCH", endpoint, json={"active": active})

    def trigger_build(self, version: str = "latest") -> Dict[str, Any]:
        """Trigger a new build for a specific version."""
        endpoint = f"projects/{self.project_slug}/versions/{version}/builds/"
        return self._make_request("POST", endpoint, json={})

    def get_build_status(self, build_id: int) -> Dict[str, Any]:
        """Get the status of a specific build."""
        endpoint = f"projects/{self.project_slug}/builds/{build_id}/"
        return self._make_request("GET", endpoint)

    def list_builds(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent builds."""
        endpoint = f"projects/{self.project_slug}/builds/"
        result = self._make_request("GET", endpoint, params={"limit": limit})
        return result.get("results", [])

    def wait_for_build(self, build_id: int, timeout: int = 600) -> str:
        """
        Wait for a build to complete.

        Args:
            build_id: Build ID to monitor
            timeout: Maximum time to wait in seconds

        Returns:
            Final build status
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            build = self.get_build_status(build_id)
            status = build.get("state", {}).get("code", "unknown")

            if status in ["finished", "cancelled", "failed"]:
                return status

            print(f"Build {build_id} status: {status}... waiting")
            time.sleep(10)

        return "timeout"

    def get_project_redirects(self) -> List[Dict[str, Any]]:
        """Get project redirects."""
        endpoint = f"projects/{self.project_slug}/redirects/"
        result = self._make_request("GET", endpoint)
        return result.get("results", [])

    def create_redirect(
        self, from_url: str, to_url: str, redirect_type: str = "page"
    ) -> Dict[str, Any]:
        """Create a URL redirect."""
        endpoint = f"projects/{self.project_slug}/redirects/"
        return self._make_request(
            "POST",
            endpoint,
            json={"from_url": from_url, "to_url": to_url, "type": redirect_type},
        )

    def get_project_environment_variables(self) -> List[Dict[str, Any]]:
        """Get project environment variables."""
        endpoint = f"projects/{self.project_slug}/environmentvariables/"
        result = self._make_request("GET", endpoint)
        return result.get("results", [])

    def set_environment_variable(self, name: str, value: str) -> Dict[str, Any]:
        """Set a project environment variable."""
        endpoint = f"projects/{self.project_slug}/environmentvariables/"
        return self._make_request("POST", endpoint, json={"name": name, "value": value})


def format_build_info(build: Dict[str, Any]) -> str:
    """Format build information for display."""
    build_id = build.get("id", "N/A")
    version = build.get("version", "unknown")
    state = build.get("state", {}).get("code", "unknown")
    created = build.get("created", "")
    duration = build.get("duration", 0)

    if created:
        created = datetime.fromisoformat(created.replace("Z", "+00:00"))
        created = created.strftime("%Y-%m-%d %H:%M:%S")

    return (
        f"Build #{build_id}\n"
        f"  Version: {version}\n"
        f"  Status: {state}\n"
        f"  Created: {created}\n"
        f"  Duration: {duration}s"
    )


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="Manage Read the Docs deployment for claude-mpm"
    )

    # Get API token from environment or command line
    default_token = os.environ.get("READTHEDOCS_API_TOKEN")
    parser.add_argument(
        "--token",
        default=default_token,
        help="Read the Docs API token (or set READTHEDOCS_API_TOKEN env var)",
    )

    parser.add_argument(
        "--project", default="claude-mpm", help="Project slug on Read the Docs"
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Project info command
    subparsers.add_parser("info", help="Get project information")

    # Version commands
    version_parser = subparsers.add_parser("versions", help="List project versions")
    version_parser.add_argument(
        "--active", action="store_true", help="Show only active versions"
    )

    activate_parser = subparsers.add_parser("activate", help="Activate a version")
    activate_parser.add_argument("version", help="Version slug to activate")

    deactivate_parser = subparsers.add_parser("deactivate", help="Deactivate a version")
    deactivate_parser.add_argument("version", help="Version slug to deactivate")

    # Build commands
    build_parser = subparsers.add_parser("build", help="Trigger a new build")
    build_parser.add_argument("--version", default="latest", help="Version to build")
    build_parser.add_argument(
        "--wait", action="store_true", help="Wait for build to complete"
    )

    builds_parser = subparsers.add_parser("builds", help="List recent builds")
    builds_parser.add_argument(
        "--limit", type=int, default=10, help="Number of builds to show"
    )

    status_parser = subparsers.add_parser("status", help="Get build status")
    status_parser.add_argument("build_id", type=int, help="Build ID to check")

    # Redirect commands
    subparsers.add_parser("redirects", help="List project redirects")

    redirect_parser = subparsers.add_parser("add-redirect", help="Add a redirect")
    redirect_parser.add_argument("from_url", help="Source URL")
    redirect_parser.add_argument("to_url", help="Target URL")

    # Environment variable commands
    subparsers.add_parser("env", help="List environment variables")

    setenv_parser = subparsers.add_parser("setenv", help="Set environment variable")
    setenv_parser.add_argument("name", help="Variable name")
    setenv_parser.add_argument("value", help="Variable value")

    args = parser.parse_args()

    # Check for API token
    if not args.token:
        print("Error: API token required. Set READTHEDOCS_API_TOKEN or use --token")
        sys.exit(1)

    # Default to info command if none specified
    if not args.command:
        args.command = "info"

    # Initialize client
    client = ReadTheDocsClient(args.token, args.project)

    try:
        # Execute command
        if args.command == "info":
            info = client.get_project_info()
            print(f"Project: {info.get('name', 'N/A')}")
            print(f"Slug: {info.get('slug', 'N/A')}")
            print(f"Repository: {info.get('repository', {}).get('url', 'N/A')}")
            print(f"Language: {info.get('language', {}).get('name', 'N/A')}")
            print(f"Default version: {info.get('default_version', 'N/A')}")
            print(f"Homepage: {info.get('homepage', 'N/A')}")

        elif args.command == "versions":
            versions = client.list_versions(active_only=args.active)
            for version in versions:
                active = "✓" if version.get("active") else "✗"
                print(
                    f"[{active}] {version.get('slug', 'N/A')} - {version.get('ref', 'N/A')}"
                )

        elif args.command == "activate":
            result = client.activate_version(args.version, active=True)
            print(f"Version {args.version} activated")

        elif args.command == "deactivate":
            result = client.activate_version(args.version, active=False)
            print(f"Version {args.version} deactivated")

        elif args.command == "build":
            result = client.trigger_build(args.version)
            build_id = result.get("id")
            print(f"Build #{build_id} triggered for version {args.version}")

            if args.wait:
                print("Waiting for build to complete...")
                final_status = client.wait_for_build(build_id)
                print(f"Build completed with status: {final_status}")

                if final_status == "finished":
                    print(
                        f"Documentation available at: https://claude-mpm.readthedocs.io/en/{args.version}/"
                    )

        elif args.command == "builds":
            builds = client.list_builds(limit=args.limit)
            for build in builds:
                print(format_build_info(build))
                print()

        elif args.command == "status":
            build = client.get_build_status(args.build_id)
            print(format_build_info(build))

        elif args.command == "redirects":
            redirects = client.get_project_redirects()
            if redirects:
                for redirect in redirects:
                    print(
                        f"{redirect.get('from_url')} → {redirect.get('to_url')} ({redirect.get('type')})"
                    )
            else:
                print("No redirects configured")

        elif args.command == "add-redirect":
            result = client.create_redirect(args.from_url, args.to_url)
            print(f"Redirect created: {args.from_url} → {args.to_url}")

        elif args.command == "env":
            env_vars = client.get_project_environment_variables()
            if env_vars:
                for var in env_vars:
                    print(f"{var.get('name')} = {var.get('value')}")
            else:
                print("No environment variables configured")

        elif args.command == "setenv":
            result = client.set_environment_variable(args.name, args.value)
            print(f"Environment variable set: {args.name}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
