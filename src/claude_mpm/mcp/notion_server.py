"""Notion MCP server for claude-mpm.

This MCP server provides tools for interacting with Notion API including:
- Querying database pages
- Getting page content
- Updating page properties
- Creating new pages
- Searching across workspace
- Appending blocks to pages
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

# Notion API configuration
NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _load_env_vars() -> tuple[str | None, str | None]:
    """Load Notion credentials from environment or .env files.

    Checks in order:
    1. Environment variables
    2. .env.local
    3. .env

    Returns:
        Tuple of (api_key, database_id)
    """
    api_key = os.environ.get("NOTION_API_KEY")
    database_id = os.environ.get("NOTION_DATABASE_ID")

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

                            if key == "NOTION_API_KEY" and not api_key:
                                api_key = value
                            elif key == "NOTION_DATABASE_ID" and not database_id:
                                database_id = value
            except Exception as e:
                logger.debug(f"Error reading {env_file}: {e}")

    return api_key, database_id


class NotionServer:
    """MCP server for Notion API operations.

    Provides tools for database queries, page operations, and content management.
    """

    def __init__(self) -> None:
        """Initialize the Notion MCP server."""
        self.server = Server("notion-mcp")
        self.api_key, self.default_database_id = _load_env_vars()

        if not self.api_key:
            logger.warning(
                "NOTION_API_KEY not found in environment or .env files. "
                "Tools will fail until configured."
            )

        self._setup_handlers()

    def _get_headers(self) -> dict[str, str]:
        """Get headers for Notion API requests."""
        if not self.api_key:
            raise RuntimeError(
                "NOTION_API_KEY not configured. "
                "Set it in environment or .env.local file."
            )

        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": NOTION_VERSION,
        }

    async def _notion_request(
        self,
        method: str,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make authenticated request to Notion API.

        Args:
            method: HTTP method (GET, POST, PATCH)
            endpoint: API endpoint (e.g., 'databases/{id}/query')
            json_data: Optional JSON body

        Returns:
            JSON response

        Raises:
            RuntimeError: On API errors
        """
        url = f"{NOTION_API_BASE}/{endpoint}"

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=self._get_headers(),
                json=json_data,
                timeout=30.0,
            )

            if response.status_code >= 400:
                error_detail = response.text
                raise RuntimeError(
                    f"Notion API error ({response.status_code}): {error_detail}"
                )

            return response.json()

    def _setup_handlers(self) -> None:
        """Register MCP tool handlers."""

        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """Return list of available tools."""
            return [
                Tool(
                    name="query_database",
                    description="Query pages from a Notion database with optional filters and pagination",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "database_id": {
                                "type": "string",
                                "description": "Database ID (uses NOTION_DATABASE_ID env var if not provided)",
                            },
                            "filter": {
                                "type": "object",
                                "description": "Optional Notion filter object",
                            },
                            "sorts": {
                                "type": "array",
                                "description": "Optional array of sort objects",
                            },
                            "page_size": {
                                "type": "integer",
                                "description": "Number of results per page (max 100)",
                                "default": 100,
                            },
                            "start_cursor": {
                                "type": "string",
                                "description": "Pagination cursor from previous response",
                            },
                        },
                        "required": [],
                    },
                ),
                Tool(
                    name="get_page",
                    description="Retrieve a page by its ID including properties",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "page_id": {
                                "type": "string",
                                "description": "Page ID",
                            },
                        },
                        "required": ["page_id"],
                    },
                ),
                Tool(
                    name="get_page_content",
                    description="Retrieve all blocks (content) from a page",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "page_id": {
                                "type": "string",
                                "description": "Page ID",
                            },
                        },
                        "required": ["page_id"],
                    },
                ),
                Tool(
                    name="update_page",
                    description="Update page properties",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "page_id": {
                                "type": "string",
                                "description": "Page ID",
                            },
                            "properties": {
                                "type": "object",
                                "description": "Properties to update (Notion property format)",
                            },
                        },
                        "required": ["page_id", "properties"],
                    },
                ),
                Tool(
                    name="create_page",
                    description="Create a new page in a database",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "database_id": {
                                "type": "string",
                                "description": "Parent database ID",
                            },
                            "properties": {
                                "type": "object",
                                "description": "Page properties",
                            },
                            "children": {
                                "type": "array",
                                "description": "Optional array of block children",
                            },
                        },
                        "required": ["database_id", "properties"],
                    },
                ),
                Tool(
                    name="append_blocks",
                    description="Append block children to a page",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "page_id": {
                                "type": "string",
                                "description": "Page ID to append blocks to",
                            },
                            "children": {
                                "type": "array",
                                "description": "Array of block objects to append",
                            },
                        },
                        "required": ["page_id", "children"],
                    },
                ),
                Tool(
                    name="search",
                    description="Search for pages across the workspace",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query text",
                            },
                            "filter": {
                                "type": "object",
                                "description": 'Optional filter (e.g., {"property": "object", "value": "page"})',
                            },
                            "sort": {
                                "type": "object",
                                "description": "Optional sort configuration",
                            },
                            "page_size": {
                                "type": "integer",
                                "description": "Number of results (max 100)",
                                "default": 100,
                            },
                        },
                        "required": ["query"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            """Handle tool execution."""
            try:
                if name == "query_database":
                    return await self._query_database(arguments)
                if name == "get_page":
                    return await self._get_page(arguments)
                if name == "get_page_content":
                    return await self._get_page_content(arguments)
                if name == "update_page":
                    return await self._update_page(arguments)
                if name == "create_page":
                    return await self._create_page(arguments)
                if name == "append_blocks":
                    return await self._append_blocks(arguments)
                if name == "search":
                    return await self._search(arguments)
                raise ValueError(f"Unknown tool: {name}")
            except Exception as e:
                logger.error(f"Error executing {name}: {e}")
                return [TextContent(type="text", text=f"Error: {e!s}")]

    async def _query_database(self, args: dict[str, Any]) -> list[TextContent]:
        """Query database pages."""
        database_id = args.get("database_id") or self.default_database_id
        if not database_id:
            raise ValueError("database_id required (not set in NOTION_DATABASE_ID)")

        # Remove hyphens from database ID if present
        database_id = database_id.replace("-", "")

        body: dict[str, Any] = {}
        if "filter" in args:
            body["filter"] = args["filter"]
        if "sorts" in args:
            body["sorts"] = args["sorts"]
        if "page_size" in args:
            body["page_size"] = args["page_size"]
        if "start_cursor" in args:
            body["start_cursor"] = args["start_cursor"]

        result = await self._notion_request(
            "POST",
            f"databases/{database_id}/query",
            body,
        )

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def _get_page(self, args: dict[str, Any]) -> list[TextContent]:
        """Get page by ID."""
        page_id = args["page_id"].replace("-", "")

        result = await self._notion_request("GET", f"pages/{page_id}")

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def _get_page_content(self, args: dict[str, Any]) -> list[TextContent]:
        """Get all blocks from a page."""
        page_id = args["page_id"].replace("-", "")

        result = await self._notion_request("GET", f"blocks/{page_id}/children")

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def _update_page(self, args: dict[str, Any]) -> list[TextContent]:
        """Update page properties."""
        page_id = args["page_id"].replace("-", "")
        properties = args["properties"]

        body = {"properties": properties}

        result = await self._notion_request("PATCH", f"pages/{page_id}", body)

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def _create_page(self, args: dict[str, Any]) -> list[TextContent]:
        """Create a new page."""
        database_id = args["database_id"].replace("-", "")

        body = {
            "parent": {"database_id": database_id},
            "properties": args["properties"],
        }

        if "children" in args:
            body["children"] = args["children"]

        result = await self._notion_request("POST", "pages", body)

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def _append_blocks(self, args: dict[str, Any]) -> list[TextContent]:
        """Append blocks to a page."""
        page_id = args["page_id"].replace("-", "")
        children = args["children"]

        body = {"children": children}

        result = await self._notion_request(
            "PATCH",
            f"blocks/{page_id}/children",
            body,
        )

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def _search(self, args: dict[str, Any]) -> list[TextContent]:
        """Search workspace."""
        body: dict[str, Any] = {"query": args["query"]}

        if "filter" in args:
            body["filter"] = args["filter"]
        if "sort" in args:
            body["sort"] = args["sort"]
        if "page_size" in args:
            body["page_size"] = args["page_size"]

        result = await self._notion_request("POST", "search", body)

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
    """Entry point for notion-mcp server."""
    server = NotionServer()
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
