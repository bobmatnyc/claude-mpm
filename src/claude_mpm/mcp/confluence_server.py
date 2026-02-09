"""Confluence MCP server for claude-mpm.

This MCP server provides tools for interacting with Confluence API including:
- Getting pages by ID or title
- Searching pages and spaces
- Creating and updating pages
- Getting page content
- Listing spaces
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _load_env_vars() -> tuple[str | None, str | None, str | None]:
    """Load Confluence credentials from environment or .env files.

    Returns:
        Tuple of (url, email, api_token)
    """
    url = os.environ.get("CONFLUENCE_URL")
    email = os.environ.get("CONFLUENCE_EMAIL")
    api_token = os.environ.get("CONFLUENCE_API_TOKEN")

    # Check .env files if not in environment
    for env_file in [".env.local", ".env"]:
        env_path = Path.cwd() / env_file
        if env_path.exists():
            try:
                with open(env_path) as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            key, _, value = line.partition("=")
                            key = key.strip()
                            value = value.strip().strip('"').strip("'")

                            if key == "CONFLUENCE_URL" and not url:
                                url = value
                            elif key == "CONFLUENCE_EMAIL" and not email:
                                email = value
                            elif key == "CONFLUENCE_API_TOKEN" and not api_token:
                                api_token = value
            except Exception as e:
                logger.debug(f"Error reading {env_file}: {e}")

    return url, email, api_token


class ConfluenceServer:
    """MCP server for Confluence API operations."""

    def __init__(self) -> None:
        """Initialize the Confluence MCP server."""
        self.server = Server("confluence-mcp")
        self.url, self.email, self.api_token = _load_env_vars()

        if not all([self.url, self.email, self.api_token]):
            logger.warning(
                "Confluence credentials not fully configured. "
                "Tools will fail until CONFLUENCE_URL, CONFLUENCE_EMAIL, and "
                "CONFLUENCE_API_TOKEN are set."
            )

        # Ensure URL ends with /wiki/rest/api
        if self.url and not self.url.endswith("/wiki/rest/api"):
            if "/wiki" in self.url:
                self.url = self.url.split("/wiki")[0] + "/wiki/rest/api"
            else:
                self.url = self.url.rstrip("/") + "/wiki/rest/api"

        self._setup_handlers()

    def _get_auth(self) -> tuple[str, str]:
        """Get Basic Auth credentials."""
        if not self.email or not self.api_token:
            raise RuntimeError(
                "Confluence credentials not configured. "
                "Set CONFLUENCE_EMAIL and CONFLUENCE_API_TOKEN."
            )
        return (self.email, self.api_token)

    async def _confluence_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make authenticated request to Confluence API."""
        if not self.url:
            raise RuntimeError("CONFLUENCE_URL not configured")

        url = f"{self.url}/{endpoint}"
        auth = self._get_auth()

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                auth=auth,
                params=params,
                json=json_data,
                timeout=30.0,
            )

            if response.status_code >= 400:
                error_detail = response.text
                raise RuntimeError(
                    f"Confluence API error ({response.status_code}): {error_detail}"
                )

            return response.json()

    def _setup_handlers(self) -> None:
        """Register MCP tool handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """Return list of available tools."""
            return [
                Tool(
                    name="get_page",
                    description="Get a Confluence page by ID",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "page_id": {
                                "type": "string",
                                "description": "Page ID",
                            },
                            "expand": {
                                "type": "string",
                                "description": "Comma-separated list of properties to expand (e.g., 'body.storage,version')",
                                "default": "body.storage,version",
                            },
                        },
                        "required": ["page_id"],
                    },
                ),
                Tool(
                    name="get_page_by_title",
                    description="Get a page by title and space key",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "space_key": {
                                "type": "string",
                                "description": "Space key (e.g., 'TEAM')",
                            },
                            "title": {
                                "type": "string",
                                "description": "Page title",
                            },
                            "expand": {
                                "type": "string",
                                "description": "Properties to expand",
                                "default": "body.storage,version",
                            },
                        },
                        "required": ["space_key", "title"],
                    },
                ),
                Tool(
                    name="search_pages",
                    description="Search for pages using CQL (Confluence Query Language)",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "cql": {
                                "type": "string",
                                "description": "CQL query (e.g., 'space=TEAM and type=page')",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum results (default: 25)",
                                "default": 25,
                            },
                        },
                        "required": ["cql"],
                    },
                ),
                Tool(
                    name="create_page",
                    description="Create a new Confluence page",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "space_key": {
                                "type": "string",
                                "description": "Space key",
                            },
                            "title": {
                                "type": "string",
                                "description": "Page title",
                            },
                            "content": {
                                "type": "string",
                                "description": "Page content in storage format (HTML-like)",
                            },
                            "parent_id": {
                                "type": "string",
                                "description": "Optional parent page ID",
                            },
                        },
                        "required": ["space_key", "title", "content"],
                    },
                ),
                Tool(
                    name="update_page",
                    description="Update an existing page",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "page_id": {
                                "type": "string",
                                "description": "Page ID",
                            },
                            "title": {
                                "type": "string",
                                "description": "New title (optional)",
                            },
                            "content": {
                                "type": "string",
                                "description": "New content in storage format",
                            },
                            "version_number": {
                                "type": "integer",
                                "description": "Current version number (required for updates)",
                            },
                        },
                        "required": ["page_id", "content", "version_number"],
                    },
                ),
                Tool(
                    name="list_spaces",
                    description="List Confluence spaces",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "Maximum spaces to return (default: 25)",
                                "default": 25,
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="get_space",
                    description="Get space information",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "space_key": {
                                "type": "string",
                                "description": "Space key",
                            },
                        },
                        "required": ["space_key"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool execution."""
            try:
                if name == "get_page":
                    return await self._get_page(arguments)
                if name == "get_page_by_title":
                    return await self._get_page_by_title(arguments)
                if name == "search_pages":
                    return await self._search_pages(arguments)
                if name == "create_page":
                    return await self._create_page(arguments)
                if name == "update_page":
                    return await self._update_page(arguments)
                if name == "list_spaces":
                    return await self._list_spaces(arguments)
                if name == "get_space":
                    return await self._get_space(arguments)
                raise ValueError(f"Unknown tool: {name}")
            except Exception as e:
                logger.error(f"Error executing {name}: {e}")
                return [TextContent(type="text", text=f"Error: {e!s}")]

    async def _get_page(self, args: dict[str, Any]) -> list[TextContent]:
        """Get page by ID."""
        page_id = args["page_id"]
        expand = args.get("expand", "body.storage,version")

        result = await self._confluence_request(
            "GET",
            f"content/{page_id}",
            params={"expand": expand},
        )

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def _get_page_by_title(self, args: dict[str, Any]) -> list[TextContent]:
        """Get page by title and space."""
        space_key = args["space_key"]
        title = args["title"]
        expand = args.get("expand", "body.storage,version")

        result = await self._confluence_request(
            "GET",
            "content",
            params={"spaceKey": space_key, "title": title, "expand": expand},
        )

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def _search_pages(self, args: dict[str, Any]) -> list[TextContent]:
        """Search using CQL."""
        cql = args["cql"]
        limit = args.get("limit", 25)

        result = await self._confluence_request(
            "GET",
            "content/search",
            params={"cql": cql, "limit": limit},
        )

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def _create_page(self, args: dict[str, Any]) -> list[TextContent]:
        """Create a new page."""
        body = {
            "type": "page",
            "title": args["title"],
            "space": {"key": args["space_key"]},
            "body": {
                "storage": {"value": args["content"], "representation": "storage"}
            },
        }

        if "parent_id" in args:
            body["ancestors"] = [{"id": args["parent_id"]}]

        result = await self._confluence_request("POST", "content", json_data=body)

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def _update_page(self, args: dict[str, Any]) -> list[TextContent]:
        """Update an existing page."""
        page_id = args["page_id"]

        body = {
            "version": {"number": args["version_number"] + 1},
            "title": args.get("title", ""),
            "type": "page",
            "body": {
                "storage": {"value": args["content"], "representation": "storage"}
            },
        }

        result = await self._confluence_request(
            "PUT",
            f"content/{page_id}",
            json_data=body,
        )

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def _list_spaces(self, args: dict[str, Any]) -> list[TextContent]:
        """List spaces."""
        limit = args.get("limit", 25)

        result = await self._confluence_request("GET", "space", params={"limit": limit})

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def _get_space(self, args: dict[str, Any]) -> list[TextContent]:
        """Get space info."""
        space_key = args["space_key"]

        result = await self._confluence_request("GET", f"space/{space_key}")

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def run(self) -> None:
        """Run the MCP server."""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options(),
            )


def main() -> None:
    """Entry point for confluence-mcp server."""
    server = ConfluenceServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
