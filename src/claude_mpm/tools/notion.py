"""Notion tools module.

WHY: Provides CLI-accessible bulk operations for Notion API.
Bypasses MCP protocol overhead for batch processing.

USAGE:
    claude-mpm tools notion <action> [options]

ACTIONS:
    database-query      - Export pages from a database
    pages-batch-update  - Update multiple pages from JSON
    pages-export        - Export pages with full content
    md-import          - Import markdown files as Notion pages
"""

import json
import os
import time
from pathlib import Path
from typing import Any

import requests

from claude_mpm.tools import register_service
from claude_mpm.tools.base import BaseToolModule, ToolResult


def _load_env_vars() -> tuple[str | None, str | None]:
    """Load Notion credentials from environment or .env files."""
    api_key = os.environ.get("NOTION_API_KEY")
    database_id = os.environ.get("NOTION_DATABASE_ID")

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
            except Exception:  # nosec B110 - Intentional pass on env file errors
                pass

    return api_key, database_id


class NotionTools(BaseToolModule):
    """Notion bulk operations tool module."""

    NOTION_API_BASE = "https://api.notion.com/v1"
    NOTION_VERSION = "2022-06-28"

    def __init__(self):
        """Initialize Notion tools."""
        super().__init__()
        self.api_key, self.default_database_id = _load_env_vars()

    def get_service_name(self) -> str:
        """Return service name."""
        return "notion"

    def get_actions(self) -> list[str]:
        """Return list of available actions."""
        return [
            "database-query",
            "pages-batch-update",
            "pages-export",
            "md-import",
        ]

    def get_action_help(self, action: str) -> str:
        """Return help text for specific action."""
        help_texts = {
            "database-query": "Export pages from a Notion database",
            "pages-batch-update": "Update multiple pages from JSON file",
            "pages-export": "Export pages with full content",
            "md-import": "Import markdown files as Notion pages",
        }
        return help_texts.get(action, "No help available")

    def _get_headers(self) -> dict[str, str]:
        """Get headers for Notion API requests."""
        if not self.api_key:
            raise ValueError(
                "NOTION_API_KEY not found. Set it in environment or .env.local file."
            )

        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Notion-Version": self.NOTION_VERSION,
        }

    def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make authenticated API request to Notion."""
        url = f"{self.NOTION_API_BASE}/{endpoint}"

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self._get_headers(),
                json=json_data,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            raise ValueError(
                f"Notion API error ({e.response.status_code}): {e.response.text}"
            ) from e
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Request error: {e}") from e

    def _database_query(self, **kwargs) -> ToolResult:
        """Export pages from a database."""
        database_id = kwargs.get("database_id") or self.default_database_id
        if not database_id:
            return ToolResult.error(
                "database-query",
                "database_id required (not set in NOTION_DATABASE_ID)",
            )

        database_id = database_id.replace("-", "")
        max_results = int(kwargs.get("max_results", 100))

        pages = []
        has_more = True
        start_cursor = None

        try:
            while has_more and len(pages) < max_results:
                body: dict[str, Any] = {"page_size": min(100, max_results - len(pages))}
                if start_cursor:
                    body["start_cursor"] = start_cursor

                result = self._make_request(
                    "POST",
                    f"databases/{database_id}/query",
                    body,
                )

                pages.extend(result.get("results", []))
                has_more = result.get("has_more", False)
                start_cursor = result.get("next_cursor")

                # Rate limiting
                if has_more:
                    time.sleep(0.35)

            return ToolResult.success(
                "database-query",
                {"pages": pages, "database_id": database_id},
                {"count": len(pages), "max_results": max_results},
            )

        except Exception as e:
            return ToolResult.error("database-query", str(e))

    def _pages_batch_update(self, **kwargs) -> ToolResult:
        """Update multiple pages from JSON file."""
        file_path = kwargs.get("file")
        if not file_path:
            return ToolResult.error("pages-batch-update", "file parameter required")

        try:
            with open(file_path) as f:
                data = json.load(f)

            updates = data.get("updates", [])
            if not updates:
                return ToolResult.error(
                    "pages-batch-update", "No updates found in file"
                )

            success_count = 0
            failed_count = 0

            for update in updates:
                page_id = update.get("page_id", "").replace("-", "")
                properties = update.get("properties", {})

                if not page_id or not properties:
                    failed_count += 1
                    continue

                try:
                    self._make_request(
                        "PATCH",
                        f"pages/{page_id}",
                        {"properties": properties},
                    )
                    success_count += 1
                    time.sleep(0.35)  # Rate limiting
                except Exception:  # nosec B110 - Continue on individual failures
                    failed_count += 1

            return ToolResult.success(
                "pages-batch-update",
                {"updates": updates},
                {
                    "total": len(updates),
                    "success": success_count,
                    "failed": failed_count,
                },
            )

        except Exception as e:
            return ToolResult.error("pages-batch-update", str(e))

    def _pages_export(self, **kwargs) -> ToolResult:
        """Export pages with full content."""
        page_ids = kwargs.get("page_ids", "").split(",")
        page_ids = [p.strip().replace("-", "") for p in page_ids if p.strip()]

        if not page_ids:
            return ToolResult.error("pages-export", "page_ids parameter required")

        try:
            exported_pages = []

            for page_id in page_ids:
                # Get page properties
                page = self._make_request("GET", f"pages/{page_id}")

                # Get page content (blocks)
                blocks = self._make_request("GET", f"blocks/{page_id}/children")

                exported_pages.append(
                    {"page": page, "blocks": blocks.get("results", [])}
                )

                time.sleep(0.35)  # Rate limiting

            return ToolResult.success(
                "pages-export",
                {"pages": exported_pages},
                {"count": len(exported_pages)},
            )

        except Exception as e:
            return ToolResult.error("pages-export", str(e))

    def _md_import(self, **kwargs) -> ToolResult:
        """Import markdown files as Notion pages."""
        files = kwargs.get("files", "").split(",")
        files = [f.strip() for f in files if f.strip()]

        database_id = kwargs.get("database_id") or self.default_database_id
        if not database_id:
            return ToolResult.error(
                "md-import", "database_id required (not set in NOTION_DATABASE_ID)"
            )

        database_id = database_id.replace("-", "")

        if not files:
            return ToolResult.error("md-import", "files parameter required")

        try:
            # Import the md_to_notion_blocks function
            from claude_mpm.integrations.notion import md_to_notion_blocks

            created_pages = []
            failed_files = []

            for file_path in files:
                try:
                    with open(file_path) as f:
                        markdown = f.read()

                    # Convert markdown to Notion blocks
                    blocks = md_to_notion_blocks(markdown)

                    # Extract title from first heading or filename
                    title = Path(file_path).stem
                    for block in blocks:
                        if block.get("type") == "heading_1":
                            title_text = block.get("heading_1", {}).get("rich_text", [])
                            if title_text:
                                title = (
                                    title_text[0].get("text", {}).get("content", title)
                                )
                            break

                    # Create page in database
                    page = self._make_request(
                        "POST",
                        "pages",
                        {
                            "parent": {"database_id": database_id},
                            "properties": {
                                "Name": {"title": [{"text": {"content": title}}]}
                            },
                            "children": blocks[
                                :100
                            ],  # Notion limits to 100 blocks per request
                        },
                    )

                    created_pages.append(
                        {"file": file_path, "page_id": page.get("id"), "title": title}
                    )

                    time.sleep(0.35)  # Rate limiting

                except Exception as e:  # nosec B110 - Continue on individual failures
                    failed_files.append({"file": file_path, "error": str(e)})

            return ToolResult.success(
                "md-import",
                {"created_pages": created_pages, "failed_files": failed_files},
                {
                    "total": len(files),
                    "success": len(created_pages),
                    "failed": len(failed_files),
                },
            )

        except Exception as e:
            return ToolResult.error("md-import", str(e))


# Register the service
register_service(NotionTools())
