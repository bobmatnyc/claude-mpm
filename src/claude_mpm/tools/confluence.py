"""Confluence tools module.

WHY: Provides CLI-accessible bulk operations for Confluence API.
Bypasses MCP protocol overhead for batch processing.

USAGE:
    claude-mpm tools confluence <action> [options]

ACTIONS:
    pages-search         - Search and export pages
    pages-batch-export   - Export multiple pages with content
    spaces-list          - List all spaces
    md-import           - Import markdown files as Confluence pages
"""

import os
import time
from pathlib import Path
from typing import Any

import requests

from claude_mpm.tools import register_service
from claude_mpm.tools.base import BaseToolModule, ToolResult


def _load_env_vars() -> tuple[str | None, str | None, str | None]:
    """Load Confluence credentials from environment or .env files."""
    url = os.environ.get("CONFLUENCE_URL")
    email = os.environ.get("CONFLUENCE_EMAIL")
    api_token = os.environ.get("CONFLUENCE_API_TOKEN")

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
            except Exception:  # nosec B110
                pass

    return url, email, api_token


class ConfluenceTools(BaseToolModule):
    """Confluence bulk operations tool module."""

    def __init__(self):
        """Initialize Confluence tools."""
        super().__init__()
        self.url, self.email, self.api_token = _load_env_vars()

        # Ensure URL ends with /wiki/rest/api
        if self.url and not self.url.endswith("/wiki/rest/api"):
            if "/wiki" in self.url:
                self.url = self.url.split("/wiki")[0] + "/wiki/rest/api"
            else:
                self.url = self.url.rstrip("/") + "/wiki/rest/api"

    def get_service_name(self) -> str:
        """Return service name."""
        return "confluence"

    def get_actions(self) -> list[str]:
        """Return list of available actions."""
        return [
            "pages-search",
            "pages-batch-export",
            "spaces-list",
            "md-import",
        ]

    def get_action_help(self, action: str) -> str:
        """Return help text for specific action."""
        help_texts = {
            "pages-search": "Search for pages using CQL",
            "pages-batch-export": "Export multiple pages with full content",
            "spaces-list": "List all Confluence spaces",
            "md-import": "Import markdown files as Confluence pages",
        }
        return help_texts.get(action, "No help available")

    def _get_auth(self) -> tuple[str, str]:
        """Get auth credentials."""
        if not self.email or not self.api_token:
            raise ValueError(
                "CONFLUENCE_EMAIL and CONFLUENCE_API_TOKEN not configured. "
                "Set them in environment or .env.local file."
            )
        return (self.email, self.api_token)

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make authenticated API request to Confluence."""
        if not self.url:
            raise ValueError("CONFLUENCE_URL not configured")

        url = f"{self.url}/{endpoint}"
        auth = self._get_auth()

        try:
            response = requests.request(
                method=method,
                url=url,
                auth=auth,
                params=params,
                json=json_data,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            raise ValueError(
                f"Confluence API error ({e.response.status_code}): {e.response.text}"
            ) from e
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Request error: {e}") from e

    def _pages_search(self, **kwargs) -> ToolResult:
        """Search for pages using CQL."""
        cql = kwargs.get("cql")
        if not cql:
            return ToolResult.error("pages-search", "cql parameter required")

        max_results = int(kwargs.get("max_results", 100))

        try:
            pages = []
            start = 0
            limit = 25

            while len(pages) < max_results:
                result = self._make_request(
                    "GET",
                    "content/search",
                    params={"cql": cql, "limit": limit, "start": start},
                )

                results = result.get("results", [])
                if not results:
                    break

                pages.extend(results)
                start += limit
                time.sleep(0.35)  # Rate limiting

            # Truncate to max_results
            pages = pages[:max_results]

            return ToolResult.success(
                "pages-search",
                {"pages": pages, "cql": cql},
                {"count": len(pages), "max_results": max_results},
            )

        except Exception as e:
            return ToolResult.error("pages-search", str(e))

    def _pages_batch_export(self, **kwargs) -> ToolResult:
        """Export multiple pages with content."""
        page_ids = kwargs.get("page_ids", "").split(",")
        page_ids = [p.strip() for p in page_ids if p.strip()]

        if not page_ids:
            return ToolResult.error("pages-batch-export", "page_ids parameter required")

        try:
            exported_pages = []

            for page_id in page_ids:
                # Get page with content
                page = self._make_request(
                    "GET",
                    f"content/{page_id}",
                    params={"expand": "body.storage,version,space"},
                )

                exported_pages.append(page)
                time.sleep(0.35)  # Rate limiting

            return ToolResult.success(
                "pages-batch-export",
                {"pages": exported_pages},
                {"count": len(exported_pages)},
            )

        except Exception as e:
            return ToolResult.error("pages-batch-export", str(e))

    def _spaces_list(self, **kwargs) -> ToolResult:
        """List all spaces."""
        max_results = int(kwargs.get("max_results", 100))

        try:
            spaces = []
            start = 0
            limit = 25

            while len(spaces) < max_results:
                result = self._make_request(
                    "GET",
                    "space",
                    params={"limit": limit, "start": start},
                )

                results = result.get("results", [])
                if not results:
                    break

                spaces.extend(results)
                start += limit
                time.sleep(0.35)

            spaces = spaces[:max_results]

            return ToolResult.success(
                "spaces-list",
                {"spaces": spaces},
                {"count": len(spaces)},
            )

        except Exception as e:
            return ToolResult.error("spaces-list", str(e))

    def _md_import(self, **kwargs) -> ToolResult:
        """Import markdown files as Confluence pages."""
        files = kwargs.get("files", "").split(",")
        files = [f.strip() for f in files if f.strip()]

        space_key = kwargs.get("space_key")
        if not space_key:
            return ToolResult.error("md-import", "space_key parameter required")

        if not files:
            return ToolResult.error("md-import", "files parameter required")

        try:
            # Import the markdown converter
            from claude_mpm.integrations.confluence import md_to_confluence_storage

            created_pages = []
            failed_files = []

            for file_path in files:
                try:
                    with open(file_path) as f:
                        markdown = f.read()

                    # Convert markdown to Confluence storage format
                    content = md_to_confluence_storage(markdown)

                    # Extract title from first heading or filename
                    title = Path(file_path).stem

                    # Look for # heading in first few lines
                    for line in markdown.split("\n")[:5]:
                        if line.startswith("# "):
                            title = line[2:].strip()
                            break

                    # Create page
                    body = {
                        "type": "page",
                        "title": title,
                        "space": {"key": space_key},
                        "body": {
                            "storage": {"value": content, "representation": "storage"}
                        },
                    }

                    page = self._make_request("POST", "content", json_data=body)

                    created_pages.append(
                        {"file": file_path, "page_id": page.get("id"), "title": title}
                    )

                    time.sleep(0.35)  # Rate limiting

                except Exception as e:  # nosec B110
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
register_service(ConfluenceTools())
