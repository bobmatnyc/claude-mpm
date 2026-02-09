"""Google Workspace tools module.

WHY: Provides CLI-accessible bulk operations for Google Workspace APIs.
Bypasses MCP protocol overhead for batch processing.

USAGE:
    claude-mpm tools google <action> [options]

ACTIONS:
    gmail-export           - Export emails matching query
    gmail-import           - Import emails from file
    calendar-bulk-create   - Create multiple calendar events
    calendar-export        - Export calendar events
    drive-batch-upload     - Upload multiple files to Drive
    drive-batch-download   - Download multiple files from Drive
"""

import json
from typing import Any, Optional

import requests

from claude_mpm.tools import register_service
from claude_mpm.tools.base import BaseToolModule, ToolResult


class GoogleTools(BaseToolModule):
    """Google Workspace bulk operations tool module."""

    def get_service_name(self) -> str:
        """Return service name."""
        return "google"

    def get_actions(self) -> list[str]:
        """Return list of available actions."""
        return [
            "gmail-export",
            "gmail-import",
            "calendar-bulk-create",
            "calendar-export",
            "drive-batch-upload",
            "drive-batch-download",
        ]

    def get_action_help(self, action: str) -> str:
        """Return help text for specific action."""
        help_texts = {
            "gmail-export": "Export emails matching query to JSON",
            "gmail-import": "Import emails from JSON file",
            "calendar-bulk-create": "Create multiple calendar events from JSON",
            "calendar-export": "Export calendar events to JSON",
            "drive-batch-upload": "Upload multiple files to Google Drive",
            "drive-batch-download": "Download multiple files from Google Drive",
        }
        return help_texts.get(action, "No help available")

    def _get_valid_token(self, service: str = "google-workspace-mpm") -> str:
        """Get valid access token.

        Args:
            service: Service name for token lookup

        Returns:
            Valid access token

        Raises:
            ValueError: If no token found or token is expired
        """
        stored = self.storage.retrieve(service)
        if not stored:
            raise ValueError(
                f"No token found for {service}. Run 'claude-mpm setup oauth google-workspace-mcp' first."
            )

        # Check if token is expired
        if stored.token.is_expired():
            raise ValueError(
                f"Token for {service} is expired. Run 'claude-mpm setup oauth google-workspace-mcp' to re-authenticate."
            )

        return stored.token.access_token

    def _make_request(
        self,
        method: str,
        url: str,
        params: Optional[dict[str, Any]] = None,
        json_data: Optional[dict[str, Any]] = None,
        service: str = "google-workspace-mpm",
    ) -> dict[str, Any]:
        """Make authenticated API request.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL to request
            params: Query parameters
            json_data: JSON body for POST/PUT
            service: Service name for token

        Returns:
            Response JSON

        Raises:
            ValueError: If request fails
        """
        token = self._get_valid_token(service)
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=30,
            )
            response.raise_for_status()
            return response.json() if response.text else {}
        except requests.exceptions.HTTPError as e:
            raise ValueError(
                f"API request failed: {e.response.status_code} {e.response.text}"
            ) from e
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Request error: {e}") from e

    def execute(self, action: str, **kwargs) -> ToolResult:
        """Execute Google Workspace action.

        Args:
            action: Action name
            **kwargs: Action-specific arguments

        Returns:
            ToolResult with operation results
        """
        # Validate action
        self.validate_action(action)

        # Route to action handler
        if action == "gmail-export":
            return self._gmail_export(**kwargs)
        if action == "gmail-import":
            return self._gmail_import(**kwargs)
        if action == "calendar-bulk-create":
            return self._calendar_bulk_create(**kwargs)
        if action == "calendar-export":
            return self._calendar_export(**kwargs)
        if action == "drive-batch-upload":
            return self._drive_batch_upload(**kwargs)
        if action == "drive-batch-download":
            return self._drive_batch_download(**kwargs)
        return ToolResult(
            success=False,
            action=action,
            error=f"Action {action} not implemented yet",
        )

    def _gmail_export(self, **kwargs) -> ToolResult:
        """Export Gmail messages.

        Args:
            query: Gmail search query (default: "")
            max_results: Maximum number of messages to export (default: 100)
            format: Export format - "metadata" or "full" (default: "metadata")

        Returns:
            ToolResult with exported messages
        """
        query = kwargs.get("query", "")
        max_results = int(kwargs.get("max_results", 100))
        export_format = kwargs.get("format", "metadata")

        try:
            # Search for messages
            messages = []
            page_token = None
            base_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"

            while len(messages) < max_results:
                # Build search params
                params = {
                    "q": query,
                    "maxResults": min(max_results - len(messages), 100),
                }
                if page_token:
                    params["pageToken"] = page_token

                # Search messages
                search_result = self._make_request("GET", base_url, params=params)
                message_list = search_result.get("messages", [])

                if not message_list:
                    break

                # Get full message details if requested
                if export_format == "full":
                    for msg in message_list:
                        msg_url = f"{base_url}/{msg['id']}"
                        full_msg = self._make_request(
                            "GET", msg_url, params={"format": "full"}
                        )
                        messages.append(full_msg)
                else:
                    # Just metadata (id and threadId)
                    messages.extend(message_list)

                # Check for next page
                page_token = search_result.get("nextPageToken")
                if not page_token:
                    break

            return ToolResult(
                success=True,
                action="gmail-export",
                data={
                    "messages": messages,
                    "query": query,
                    "format": export_format,
                },
                metadata={
                    "count": len(messages),
                    "max_results": max_results,
                },
            )

        except ValueError as e:
            return ToolResult(
                success=False,
                action="gmail-export",
                error=str(e),
            )
        except Exception as e:
            return ToolResult(
                success=False,
                action="gmail-export",
                error=f"Unexpected error: {e}",
            )

    def _gmail_import(self, **kwargs) -> ToolResult:
        """Import Gmail messages from file.

        Args:
            file: Path to JSON file with messages
            label: Label to apply to imported messages (optional)

        Returns:
            ToolResult with import results
        """
        file_path = kwargs.get("file")
        label = kwargs.get("label")

        if not file_path:
            return ToolResult(
                success=False,
                action="gmail-import",
                error="Required parameter 'file' not provided",
            )

        try:
            # Load messages from file
            with open(file_path) as f:
                data = json.load(f)

            messages = data.get("messages", [])
            if not messages:
                return ToolResult(
                    success=False,
                    action="gmail-import",
                    error="No messages found in file",
                )

            # Import messages
            imported = []
            failed = []
            base_url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"

            for msg in messages:
                try:
                    # Build import request
                    import_data = {"raw": msg.get("raw")}
                    if label:
                        import_data["labelIds"] = [label]

                    # Import message
                    result = self._make_request(
                        "POST",
                        f"{base_url}/import",
                        json_data=import_data,
                    )
                    imported.append(result.get("id"))

                except Exception as e:
                    failed.append({"message_id": msg.get("id"), "error": str(e)})

            return ToolResult(
                success=len(imported) > 0,
                action="gmail-import",
                data={
                    "imported": imported,
                    "failed": failed,
                },
                metadata={
                    "total": len(messages),
                    "imported_count": len(imported),
                    "failed_count": len(failed),
                },
            )

        except FileNotFoundError:
            return ToolResult(
                success=False,
                action="gmail-import",
                error=f"File not found: {file_path}",
            )
        except json.JSONDecodeError as e:
            return ToolResult(
                success=False,
                action="gmail-import",
                error=f"Invalid JSON in file: {e}",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                action="gmail-import",
                error=f"Unexpected error: {e}",
            )

    def _calendar_bulk_create(self, **kwargs) -> ToolResult:
        """Create multiple calendar events (placeholder)."""
        # TODO: Implement in TSK-0003
        return ToolResult(
            success=True,
            action="calendar-bulk-create",
            data={"message": "Calendar bulk create not yet implemented (TSK-0003)"},
            metadata={"count": 0},
        )

    def _calendar_export(self, **kwargs) -> ToolResult:
        """Export calendar events (placeholder)."""
        # TODO: Implement in TSK-0003
        return ToolResult(
            success=True,
            action="calendar-export",
            data={"message": "Calendar export not yet implemented (TSK-0003)"},
            metadata={"count": 0},
        )

    def _drive_batch_upload(self, **kwargs) -> ToolResult:
        """Batch upload files to Drive (placeholder)."""
        # TODO: Implement in TSK-0004
        return ToolResult(
            success=True,
            action="drive-batch-upload",
            data={"message": "Drive batch upload not yet implemented (TSK-0004)"},
            metadata={"count": 0},
        )

    def _drive_batch_download(self, **kwargs) -> ToolResult:
        """Batch download files from Drive (placeholder)."""
        # TODO: Implement in TSK-0004
        return ToolResult(
            success=True,
            action="drive-batch-download",
            data={"message": "Drive batch download not yet implemented (TSK-0004)"},
            metadata={"count": 0},
        )


# Register this service
register_service("google", GoogleTools)
